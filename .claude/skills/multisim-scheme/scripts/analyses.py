"""Analysis settings of a Multisim file (Simulate > Analyses and Simulation).

They live in the SimState attribute of each CIITDiagram (one per sheet) as a text tree:
    KEY:type{value}  items separated by newlines; type is long, double, string, flag, list or double[];
    list / double[] hold nested items; strings use Multisim's _ucN<hex> escapes for non-ASCII text.
SIMULATION_INFO > ANALYSES holds one settings block per analysis (OP, AC, PHASOR, TRAN, ...) and
ANALYSIS_LIST - the analyses of Batched, in order. The active analysis is the ActiveAnalysis attribute
of the CMultisimExtension element (e.g. 'batched').

    python3 analyses.py FILE.ms14      # list the batched analyses with their settings and variables

Writing: Scheme.op(...) collects analyses, finalize() calls add_batched() for them.
"""
import os, re, sys, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SCALAR = re.compile(r'([^:{}\n]*):([^{}\n]*)\{')


class Node:
    """one KEY:type{value} item; value is a str or a list of Node"""
    __slots__ = ('key', 'type', 'value', 'nl')

    def __init__(self, key, type, value, nl=True):
        self.key, self.type, self.value, self.nl = key, type, value, nl

    @property
    def is_list(self):
        return isinstance(self.value, list)

    def get(self, key, default=None):
        return next((n for n in self.value if n.key == key), default)

    def all(self, key):
        return [n for n in self.value if n.key == key]

    def __getitem__(self, key):
        n = self.get(key)
        if n is None: raise KeyError(key)
        return n.value if not n.is_list else n

    def __repr__(self):
        return '%s:%s{%s}' % (self.key, self.type, '...' if self.is_list else self.value)


def parse(s, i=0):
    """items of s from position i up to the closing '}' (or the end): (list of Node, end position).
    Each item is normally followed by a newline (not the last one at the top level); an empty line
    (Multisim writes one in place of a parameter with no value) is kept as a Node with key None."""
    out, n = [], len(s)
    while True:
        if i >= n or s[i] == '}': return out, i
        if s[i] == '\n':
            out.append(Node(None, None, '')); i += 1; continue
        m = SCALAR.match(s, i)
        if not m: raise ValueError('SimState: bad item at %d: %r' % (i, s[i:i + 60]))
        key, typ, i = m.group(1), m.group(2), m.end()
        if typ == 'list' or typ.endswith('[]'):
            value, i = parse(s, i)
        else:
            depth, j = 0, i
            while s[j] != '}' or depth:
                depth += {'{': 1, '}': -1}.get(s[j], 0); j += 1
            value, i = s[i:j], j
        if s[i:i + 1] != '}': raise ValueError('SimState: no closing brace at %d' % i)
        node = Node(key, typ, value); i += 1
        node.nl = s[i:i + 1] == '\n'
        if node.nl: i += 1
        out.append(node)


def dump(nodes):
    """inverse of parse(): the exact text Multisim writes"""
    return ''.join('\n' if n.key is None else
                   '%s:%s{%s}%s' % (n.key, n.type, dump(n.value) if n.is_list else n.value, '\n' if n.nl else '')
                   for n in nodes)


def loads(attr):
    """SimState attribute value (unescaped XML) -> (prefix, root nodes); prefix is &UNI or &ASC"""
    prefix, body = attr[:4], attr[4:]
    nodes, end = parse(body)
    if end != len(body): raise ValueError('SimState: trailing text at %d' % end)
    return prefix, nodes


def dumps(prefix, nodes):
    return prefix + dump(nodes)


def text(s):
    """decode Multisim _ucN<hex> escapes (N is one hex digit: the number of characters)"""
    def run(m):
        n, h = int(m.group(1), 16), m.group(2)
        return ''.join(chr(int(h[k:k + 4], 16)) for k in range(0, 4 * n, 4)) + h[4 * n:]
    return re.sub(r'_uc([0-9a-f])((?:[0-9a-f]{4})*)', run, s)


# variable record in NODES > Nodes: GROUP 768 marks "Selected variables for analysis"
SELECTED = '768'
VAR_TYPES = {'3': 'V', '4': 'I', '14': 'expr', '5': 'noise', '6': 'noise', '7': 'noise', '8': 'noise'}


def variables(analysis):
    """all variable records of an analysis block, as dicts"""
    nodes = analysis.get('NODES')
    lst = nodes.get('Nodes') if nodes else None
    return [{c.key: c.value for c in v.value if c.key} for v in (lst.value if lst else []) if v.is_list]


def selected(analysis):
    return [v for v in variables(analysis) if v['GROUP'] == SELECTED]


def show_var(name):
    """Multisim's display form: $n -> V(n), vv1#branch -> I(V1)"""
    name = re.sub(r'\bv([a-z]\w*)#branch', lambda m: 'I(%s)' % m.group(1).upper(), name)
    return re.sub(r'\$([\w:]+)', r'V(\1)', name)


def var_record(expr):
    """variable as written in Multisim's dialog -> NODE record: V(n) -> $n, I(V1) -> vv1#branch, anything else
    (V(a)-V(b), V(n)/0.4, db(...)) is an expression"""
    e = expr.strip()
    name = re.sub(r'\bI\(\s*V(\w+)\s*\)', lambda m: 'vv%s#branch' % m.group(1).lower(), e, flags=re.I)
    name = re.sub(r'\bV\(\s*([\w:]+)\s*\)', lambda m: '$' + m.group(1).lower(), name, flags=re.I)
    if re.fullmatch(r'\$[\w:]+', name): typ = '3'
    elif re.fullmatch(r'vv\w+#branch', name): typ = '4'
    else: typ = '14'
    return Node('NODE', 'list', [Node('GROUP', 'long', SELECTED), Node('PLOTDEVICETYPE', 'long', '0'),
                                 Node('TYPE', 'long', typ), Node('NAME', 'string', name),
                                 Node('DESCRIPTION', 'string', ''), Node('INI_VALUE', 'double', '0')])


def _set(block, key, value):
    block.get(key).value = value


def add_batched(R, items):
    """append analyses to Batched on the main sheet and make Batched the active analysis.
    items: dicts kind ('OP'), title, vars (as in Multisim's Output tab). Each entry is a copy of the file's own
    settings block of that kind with its id, title and selected variables replaced."""
    import copy
    from msgen import enc
    dg = next(d for d in R.iter('CIITDiagram') if d.get('SimState'))
    prefix, root = loads(dg.get('SimState'))
    an = root[0].get('ANALYSES')
    batch, cur = an.get('ANALYSIS_LIST'), an.get('CURRENT_ID')
    for it in items:
        b = copy.deepcopy(an.get(it['kind']))
        b.nl = True
        _set(b, 'ANALYSIS_ID', cur.value); cur.value = str(int(cur.value) + 1)
        _set(b, 'PLOT_TITLE', enc(it['title'])[4:])
        _set(b.get('NODES'), 'Nodes', [var_record(v) for v in it['vars']])
        batch.value.append(b)
    dg.set('SimState', dumps(prefix, root))
    ext = next(x for x in R.iter('Extension') if x.get('Class') == 'CMultisimExtension')
    ext.set('ActiveAnalysis', '&ASCbatched')


def sim_states(xml):
    """(start, end, unescaped value) of every SimState attribute in the unpacked file text"""
    return [(m.start(1), m.end(1), html.unescape(m.group(1))) for m in re.finditer(r'SimState="([^"]*)"', xml)]


def outline(nodes, depth=0, skip=('NODES', 'ASYS_OPT', 'ModelToSweep', 'InstToSweep')):
    for n in nodes:
        if n.key is None: continue
        if n.is_list:
            print('  ' * depth + '%s (%d)' % (n.key, len(n.value)))
            if n.key not in skip: outline(n.value, depth + 1, skip)
        else:
            print('  ' * depth + '%s = %s' % (n.key, text(n.value)))


def main(path):
    import blast
    xml = blast.read_ms(path).decode('latin1')
    m = re.search(r'ActiveAnalysis="([^"]*)"', xml)
    print('active analysis:', html.unescape(m.group(1))[4:] if m else '-')
    for k, (a, b, attr) in enumerate(sim_states(xml)):
        prefix, root = loads(attr)
        assert dumps(prefix, root) == attr, 'SimState round trip'
        info = root[0]
        an = info.get('ANALYSES')
        batch = an.get('ANALYSIS_LIST').value
        print('\nsheet %d: %d batched analyses' % (k, len(batch)))
        for b in batch:
            print('\n== %s  id %s  "%s"' % (b.key, b['ANALYSIS_ID'], text(b['PLOT_TITLE'])))
            print('   variables:', ', '.join(show_var(v['NAME']) for v in selected(b)) or '-')
            outline(b['ANALYSIS'].value, 2)


if __name__ == '__main__':
    main(sys.argv[1])
