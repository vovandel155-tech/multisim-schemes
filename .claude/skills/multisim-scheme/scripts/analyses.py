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


def set_tran(t, tstop, tstart=0, tmax=None, ic=None):
    """Transient settings block (TRAN, and Tran inside Fourier / Parameter Sweep): tstart..tstop s, maximum step
    tmax s (None — calculated by Multisim), initial conditions ic 'auto_ic' | 'dcop' | 'zero' (None — keep)"""
    _set(t, 'TSTOP', '%g' % tstop); _set(t, 'TSTART', '%g' % tstart)
    if ic: _set(t, 'IC', ic)
    if tmax:
        m = t.get('TMAX'); m.type, m.value = 'double', '%g' % tmax


def set_fourier(a, freq, harmonics=9, tstop=None, tmax=None, ic=None, vscale=0, bars=None, normalized=None):
    """Fourier: fundamental `freq` Hz, `harmonics` harmonics, transient up to `tstop` s (default 10 periods),
    maximum step `tmax` s (None — Multisim calculates it); vscale — the graph scale index (0 linear),
    bars — bar graph instead of a line (LineGraph 1 — the flag is the bar graph checkbox), normalized — Normalize graphs"""
    tstop = tstop or 10.0 / freq
    _set(a, 'FundFreqSet', '1'); _set(a, 'FundFreq', '%g' % freq); _set(a, 'NumFreqs', str(harmonics))
    _set(a, 'TStop', '%g' % tstop); _set(a, 'Variation', str(vscale))
    if bars is not None: _set(a, 'LineGraph', '1' if bars else '0')
    if normalized is not None: _set(a, 'Normalized', '1' if normalized else '0')
    set_tran(a.get('Tran'), tstop, 0, tmax, ic)


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
    _set(a, 'GroupTraces', '1')
    set_tran(a.get('Tran'), tstop, tstart, tmax, ic)


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


SETTERS = {'OP': None, 'PSWEEP': set_psweep, 'TRAN': set_tran, 'PHASOR': set_phasor, 'AC': set_ac, 'FOUR': set_fourier, 'NOISE': set_noise}


def add_batched(R, items, replace=False):
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
    if replace: batch.value = []
    for it in items:
        b = copy.deepcopy(an.get(it['kind']))
        b.nl = True
        _set(b, 'ANALYSIS_ID', cur.value); cur.value = str(int(cur.value) + 1)
        _set(b, 'PLOT_TITLE', enc(it['title'])[4:])
        _set(b, 'RAWFILE_NAME', '')                            # Multisim assigns the result file on opening
        _set(b.get('NODES'), 'Nodes', [var_record(v) for v in it['vars']])
        if SETTERS[it['kind']]: SETTERS[it['kind']](b.get('ANALYSIS'), **it.get('opts', {}))
        if it.get('max_points'): _set(b, 'MAX_POINTS', str(it['max_points']))
        batch.value.append(b)
    dg.set('SimState', dumps(prefix, root))
    ext = next(x for x in R.iter('Extension') if x.get('Class') == 'CMultisimExtension')
    ext.set('ActiveAnalysis', '&ASCbatched')


class Batch:
    """a Batched list being described: Scheme uses one for a new circuit, rewrite() — for an existing file.
    Variables as in the Output tab of the dialog: 'V(2)', 'I(V1)', 'V(outl)-V(outr)', 'db(...)'.
    max_points — Maximum number of points of the analysis (Analysis options; Multisim default 128000)."""

    def __init__(self):
        self.items = []

    def _add(self, kind, title, variables, max_points=None, **opts):
        self.items.append(dict(kind=kind, title=title, vars=list(variables), opts=opts, max_points=max_points))

    def op(self, variables, title='DC Operating Point', max_points=None):
        """DC Operating Point"""
        self._add('OP', title, variables, max_points)

    def phasor(self, variables, freq=1000, fmt='magph', freq_column=True, title='Single Frequency AC', max_points=None):
        """Single Frequency AC at `freq` Hz; fmt 'magph' (magnitude/phase) or 'reim'; sources take their AC magnitude"""
        self._add('PHASOR', title, variables, max_points, freq=freq, fmt=fmt, freq_column=freq_column)

    def ac(self, variables, fstart=1, fstop=10e6, points=100, sweep='dec', vscale='db', title='AC Sweep', max_points=None):
        """AC Sweep fstart..fstop Hz, `points` per decade/octave or in total ('lin'); vscale linear | log | db | octave"""
        self._add('AC', title, variables, max_points, fstart=fstart, fstop=fstop, points=points, sweep=sweep, vscale=vscale)

    def tran(self, variables, tstop, tstart=0, tmax=None, ic='auto_ic', title='Transient', max_points=None):
        """Transient tstart..tstop s, maximum step tmax s, initial conditions ic 'auto_ic' | 'dcop' | 'zero'"""
        self._add('TRAN', title, variables, max_points, tstop=tstop, tstart=tstart, tmax=tmax, ic=ic)

    def fourier(self, variables, freq=1000, harmonics=9, tstop=None, tmax=None, ic=None, vscale=0, bars=None,
                normalized=None, title='Fourier', max_points=None):
        """Fourier: harmonics of `freq` Hz (and THD) after a transient of `tstop` s (default 10 periods)"""
        self._add('FOUR', title, variables, max_points, freq=freq, harmonics=harmonics, tstop=tstop, tmax=tmax, ic=ic,
                  vscale=vscale, bars=bars, normalized=normalized)

    def noise(self, source, output, ref='0', fstart=20, fstop=20e3, points=100, spectrum=False, variables=None,
              title='Noise', max_points=None):
        """Noise input-referred to source `source` (its name), output between nets `output` and `ref` ('0' — ground);
        spectrum=False — integrated (inoise_total, onoise_total), True — spectral density (inoise/onoise_spectrum)"""
        kind = 'spectrum' if spectrum else 'total'
        self._add('NOISE', title, variables or ['inoise_' + kind, 'onoise_' + kind], max_points, source=source,
                  output=output, ref=ref, fstart=fstart, fstop=fstop, points=points, spectrum=spectrum)

    def psweep(self, variables, param, values, current=None, tstop=1e-3, tstart=0, tmax=None, ic='auto_ic',
               title='Parameter Sweep', max_points=None):
        """Parameter Sweep of circuit parameter `param` over `values`, a Transient tstart..tstop s for each"""
        self._add('PSWEEP', title, variables, max_points, param=param, values=list(values), current=current,
                  tstop=tstop, tstart=tstart, tmax=tmax, ic=ic)


def rewrite(src, dst, batch):
    """replace the Batched list of an existing Multisim file `src` with `batch` and write `dst`;
    the circuit itself is not touched"""
    import blast, msgen
    R = msgen.Doc(blast.read_ms(src)).root
    add_batched(R, batch.items, replace=True)
    blast.write_ms2(msgen.serialize(R), dst)


KIND_NAMES = {'OP': 'DC Operating Point', 'PHASOR': 'Single Frequency AC', 'AC': 'AC Sweep', 'TRAN': 'Transient',
              'FOUR': 'Fourier', 'NOISE': 'Noise', 'PSWEEP': 'Parameter Sweep', 'DC_SWEEP': 'DC Sweep',
              'TSWEEP': 'Temperature Sweep', 'DISTO': 'Distortion', 'TF': 'Transfer Function', 'SENS': 'Sensitivity',
              'PZ': 'Pole Zero', 'MONTE': 'Monte Carlo', 'WORST': 'Worst Case', 'NOISE_FIGURE': 'Noise Figure'}


def _si(v, unit):
    """1000 -> '1 kHz', 1e-7 -> '0.1 us'"""
    v = float(v)
    if v == 0: return '0 ' + unit
    for k, p in ((1e9, 'G'), (1e6, 'M'), (1e3, 'k'), (1, ''), (1e-3, 'm'), (1e-6, 'u'), (1e-9, 'n')):
        if abs(v) >= k or k == 1e-9: return '%g %s%s' % (v / k, p, unit)


def settings_text(b, names={}):
    """the main settings of one analysis block, in words (English); names — circuit parameters by lowercase name"""
    a, k = b.get('ANALYSIS'), b.key
    def tran(t):
        tm = t['TMAX']
        return '%s…%s, max step %s, initial conditions %s' % (_si(t['TSTART'], 's'), _si(t['TSTOP'], 's'),
            'auto' if tm == 'calculate' else _si(tm, 's'), {'dcop': 'DC operating point', 'auto_ic': 'automatic',
                                                           'zero': 'zero'}.get(t['IC'], t['IC']))
    def freq(f):
        return '%s…%s, %s points%s' % (_si(f['FSTART'], 'Hz'), _si(f['FSTOP'], 'Hz'),
                                        f['NPOINTS_PER_VARIATION'], '' if f['VARIATION'] == 'lin' else ' per ' +
                                            {'dec': 'decade', 'oct': 'octave'}[f['VARIATION']])
    if k == 'OP': return '—'
    if k == 'PHASOR':
        return 'f = %s, %s' % (_si(a.get('FREQ_OPT')['FSTART'], 'Hz'),
                               {'magph': 'magnitude/phase', 'reim': 'real/imaginary'}.get(a['NUMBER_FORMAT'], ''))
    if k == 'AC': return freq(a)
    if k == 'TRAN': return tran(a)
    if k == 'FOUR':
        return 'fundamental %s, %s harmonics, transient %s' % (_si(a['FundFreq'], 'Hz'), a['NumFreqs'], tran(a.get('Tran')))
    if k == 'NOISE':
        ref = a['ReferenceNode']
        return 'input source %s, output %s%s, %s, %s' % (a['InputRefSource'][1:].upper(), show_var(a['OutputNode']),
            '' if ref in ('', '$0') else ' relative to ' + show_var(ref), freq(a.get('FREQ_OPT')),
            'spectral density' if a['SetPointsPerSummary'] == '1' else 'integrated over the range')
    if k == 'PSWEEP' and a['SweepType'] == '3':
        v = a.get('VarParamSweep'); p = a.get('VariableParamToSweep')
        return 'circuit parameter %s = %s; for each: Transient %s' % (names.get(p['name'], p['name']), ', '.join(n.value for n in v.get('List').value),
                                                                     tran(a.get('Tran')))
    return ''


def markup(path, heading='Analyses (Batched)'):
    """an English draft of the description section about the Batched list of a .ms14 file (describe.py markup):
    one table row per analysis — its Grapher page, the analysis with its settings, the output variables.
    Translate it to the user's language before putting it into the description."""
    import blast
    xml = blast.read_ms(path).decode('latin1')
    prefix, root = loads(sim_states(xml)[0][2])
    from geom import dec
    names = {dec('&' + n).lower(): dec('&' + n) for n in re.findall(r'<CircuitParamName NameItem="&amp;([^"]*)"', xml)}
    rows = ['# ' + heading,
            'All results are produced by **Batched** (Simulate → Analyses and Simulation): press Run, every analysis '
            'opens its own Grapher page.',
            '| Page | Analysis and settings | Output |', '|---|---|---|']
    for b in root[0].get('ANALYSES').get('ANALYSIS_LIST').value:
        cell = lambda t: t.replace('|', '/')
        st = settings_text(b, names)
        rows.append('| %s | %s | %s |' % (cell(text(b['PLOT_TITLE'])), cell(KIND_NAMES.get(b.key, b.key) +
                    (': ' + st if st and st != '—' else '')), cell(', '.join(show_var(v['NAME']) for v in selected(b)))))
    return '\n'.join(rows) + '\n'


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
