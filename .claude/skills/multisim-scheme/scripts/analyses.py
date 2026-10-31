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
NOISE_VARS = {'inoise_spectrum': '5', 'onoise_total': '6', 'onoise_spectrum': '7', 'inoise_total': '8'}
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
    elif name in NOISE_VARS: typ = NOISE_VARS[name]
    else: typ = '14'
    return Node('NODE', 'list', [Node('GROUP', 'long', SELECTED), Node('PLOTDEVICETYPE', 'long', '0'),
                                 Node('TYPE', 'long', typ), Node('NAME', 'string', name),
                                 Node('DESCRIPTION', 'string', ''), Node('INI_VALUE', 'double', '0')])


def _set(block, key, value):
    block.get(key).value = value


def set_phasor(a, freq, fmt='magph', freq_column=True):
    """Single Frequency AC: one frequency, result format 'magph' (magnitude/phase) or 'reim' (real/imaginary).
    Written as Multisim 14.3 writes it after the dialog: FREQ_OPT without the hrange pair."""
    f = a.get('FREQ_OPT')
    f.value = [n for n in f.value if n.key != 'hrange']
    _set(f, 'FSTART', '%g' % freq); _set(f, 'FSTOP', '%g' % freq)
    _set(a, 'NUMBER_FORMAT', fmt); _set(a, 'SHOW_FREQ_COLUMN', '1' if freq_column else '0')


SWEEPS = ('dec', 'oct', 'lin')
VSCALES = {'linear': 0, 'log': 1, 'db': 2, 'octave': 3}   # Vertical scale of the dialog, in its order


def set_ac(a, fstart, fstop, points=100, sweep='dec', vscale='db'):
    """AC Sweep: fstart..fstop Hz, `points` per decade/octave (sweep 'dec'/'oct') or in total ('lin');
    vscale — the graph's vertical scale: 'linear', 'log', 'db', 'octave'"""
    assert sweep in SWEEPS, sweep
    _set(a, 'VARIATION', sweep); _set(a, 'NPOINTS_PER_VARIATION', '%g' % points)
    _set(a, 'FSTART', '%g' % fstart); _set(a, 'FSTOP', '%g' % fstop)
    _set(a, 'vscale', str(VSCALES[vscale]))
    hr = a.all('hrange')
    hr[0].value, hr[1].value = '%g' % fstart, '%g' % fstop


def _freq(f, fstart, fstop, points, sweep, vscale):
    """FREQ_OPT-style block (AC Sweep, Noise): sweep, points, range, vertical scale, graph range (hrange pair)"""
    set_ac(f, fstart, fstop, points, sweep, vscale)


def set_fourier(a, freq, harmonics=9, tstop=None, tmax=None, vscale=0):
    """Fourier: fundamental `freq` Hz, `harmonics` harmonics, transient up to `tstop` s (default 10 periods),
    maximum step `tmax` s (None — Multisim calculates it); vscale — the graph scale index (0 linear)"""
    tstop = tstop or 10.0 / freq
    _set(a, 'FundFreqSet', '1'); _set(a, 'FundFreq', '%g' % freq); _set(a, 'NumFreqs', str(harmonics))
    _set(a, 'TStop', '%g' % tstop); _set(a, 'Variation', str(vscale))
    t = a.get('Tran')
    _set(t, 'TSTOP', '%g' % tstop)
    if tmax:
        m = t.get('TMAX'); m.type, m.value = 'double', '%g' % tmax


def set_noise(a, source, output, ref='0', fstart=20, fstop=20e3, points=100, sweep='dec', vscale='log',
              spectrum=False):
    """Noise: input-referred to source `source` (RefDes, e.g. 'VIN'), output voltage between nodes `output` and `ref`
    (net names, '0' — ground); spectrum=False — integrated noise over the range (inoise_total, onoise_total),
    True — spectral density at every point (inoise_spectrum, onoise_spectrum)"""
    _set(a, 'InputRefSource', 'v' + source.lower()); _set(a, 'OutputNode', '$' + str(output).lower())
    _set(a, 'ReferenceNode', '$' + str(ref).lower())
    _set(a, 'SetPointsPerSummary', '1' if spectrum else '0')
    _freq(a.get('FREQ_OPT'), fstart, fstop, points, sweep, vscale)


PSWEEP_INNER = {'tran': '2'}   # Analysis to sweep -> AnalysisType (Transient = 2, as in a real file)


def set_psweep(a, param, values, current=None, inner='tran', tstop=1e-3, tstart=0, tmax=None, ic='auto_ic'):
    """Parameter Sweep of circuit parameter `param` over the list `values`; for each value the analysis `inner`
    ('tran' — Transient from tstart to tstop s, maximum step tmax, initial conditions ic: 'auto_ic', 'dcop', 'zero')"""
    assert inner in PSWEEP_INNER, inner
    _set(a, 'SweepType', '3'); _set(a, 'AnalysisType', PSWEEP_INNER[inner])
    v = a.get('VarParamSweep')
    _set(v, 'Variation', '3')                                  # 3 — list of values
    _set(v, 'Start', '%g' % values[0]); _set(v, 'Stop', '%g' % values[-1]); _set(v, 'NumItems', '1')
    _set(v, 'List', [Node('-', '-', '%g' % x) for x in values])
    _set(a, 'VariableParamToSweep', [Node('name', 'string', param.lower()), Node('value', 'string', '%g' % (values[0] if current is None else current)),
                                      Node('paramtype', 'long', '4')])
    t = a.get('Tran')
    _set(t, 'TSTOP', '%g' % tstop); _set(t, 'TSTART', '%g' % tstart); _set(t, 'IC', ic)
    if tmax:
        m = t.get('TMAX'); m.type, m.value = 'double', '%g' % tmax


def circuit_params(R, params, title):
    """Circuit parameters (Tools → Circuit parameters) on the main sheet: {'Uin': 0.2}. A component parameter whose
    value is a parameter name ('Uin' put in by `subst`) is marked as an expression (paramindicators = 0)."""
    import xml.etree.ElementTree as ET
    from msgen import enc
    grp = next(g for g in R.iter('Group') if g.get('Class') == 'CSheetComponent')
    sh = next(ds for ds in R.iter('DesignSheet') if ds.get('SheetID'))
    data = next(R.iter('CCircuitParamSheetGroupExtension')).find('CircuitParamData')
    names = data.find('CircuitParamNameList')
    for k in params: ET.SubElement(names, 'CircuitParamName', {'NameItem': enc(k), 'CommentItem': ''})
    from geom import dec
    path = '/%s.ms14/%s.ms14//%s/%s/' % (title, title, dec(grp.get('SheetName')), dec(sh.get('PageName')))
    vl = ET.SubElement(data, 'CircuitParamValueList', {'CircuitParamTreeInstancePath': enc(path),
                       'CircuitParamTreeInstanceGUIDPath': '&ASC%s/%s/' % (grp.get('GUID'), sh.get('SheetID'))})
    for v in params.values(): ET.SubElement(vl, 'CircuitParamValue', {'ValueItem': enc('%g' % v)})
    keys = {enc(k) for k in params}
    for pl in R.iter('CiaParamList'):
        ps, ind = pl.find('parameters'), pl.find('paramindicators')
        if ps is None or ind is None: continue
        for k, it in enumerate(ps):
            if it.get('Value') in keys: ind[k].set('Value', '0')


SETTERS = {'OP': None, 'PSWEEP': set_psweep, 'PHASOR': set_phasor, 'AC': set_ac, 'FOUR': set_fourier, 'NOISE': set_noise}


def add_batched(R, items):
    """append analyses to Batched on the main sheet and make Batched the active analysis.
    items: dicts kind ('OP', 'PHASOR'), title, vars (as in Multisim's Output tab), opts (settings of the kind).
    Each entry is a copy of the file's own settings block of that kind with its id, title, settings and
    selected variables replaced."""
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
        if SETTERS[it['kind']]: SETTERS[it['kind']](b.get('ANALYSIS'), **it.get('opts', {}))
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
