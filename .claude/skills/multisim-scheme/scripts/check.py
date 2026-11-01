"""The last gate before a file goes to the user: checks a built or rewritten .ms14 and says READY or NOT READY.

    python3 scripts/check.py out.ms14

Errors (the file must not be given away): broken ID references, overlaps on the sheet, analysis variables that name a
net or a source the circuit does not have, a noise analysis without its source or output net, a parameter sweep over an
undefined circuit parameter, markup left as text in the description (#, **, ![…], |---|, K_U without braces).
Warnings (tell the user): the default 5 V VCC, a Fourier step too coarse for its harmonics, a coarse AC sweep,
a source label with a leftover unit after a circuit parameter («UinVpk»), circuit parameters nobody uses.
Exit code 0 — ready, 1 — not ready.
"""
import os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import blast, msgen, geom, validate, analyses as AN
from geom import dec


def nets_and_parts(D, x):
    """net names (lowercase, as SPICE sees them) and part names (RefDes, lowercase) of the main sheet"""
    nets = {'0'}
    for e in D.el:
        if e.get('Class') == 'CiNode' or (len(e) and e[0].get('Class') == 'CiNode'):
            n = e.get('LocalName') or e[0].get('LocalName')
            if n: nets.add(dec(n).lower())
    for a in ('LastNetName', 'LastOverruleName'):
        nets |= {dec('&' + v).lower() for v in re.findall(a + r'="&amp;([^"]+)"', x)}
    parts = {dec(c.get('LocalName')).lower() for e in D.el for c in e.iter('CiComponent') if c.get('LocalName')}
    return nets, parts


def refs(expr):
    """nets ($n) and source branches (vv1#branch) named in an analysis variable"""
    return re.findall(r'\$([\w]+)(?![\w:])', expr), re.findall(r'\bv(\w+)#branch', expr)


def rtf_paragraphs(r):
    """plain text of the RTF paragraphs (pictures and control words dropped)"""
    r = re.sub(r'\{\\pict.*?\}\s*(?=\\par|\})', '', r, flags=re.S)
    r = re.sub(r"\\'([0-9a-f]{2})", lambda m: bytes([int(m.group(1), 16)]).decode('cp1251'), r)
    r = re.sub(r'\\u(-?\d+)\?', lambda m: chr(int(m.group(1)) % 65536), r)
    out = []
    for p in re.split(r'\\par\b|\\cell\b', r):
        t = re.sub(r'\{\\\*[^{}]*(\{[^{}]*\})*[^{}]*\}', '', p)          # {\*\pn…} list definitions
        t = re.sub(r'\{\\pntext[^{}]*\}', '', t)
        t = re.sub(r'\\[a-z]+-?\d* ?', '', t).replace('{', '').replace('}', '').strip()
        if t: out.append(t)
    return out


def check(path):
    err, warn = [], []
    raw = blast.read_ms(path)
    x = raw.decode('latin1')
    D = msgen.Doc(raw)
    v = validate.check(D.root)
    if v['dup_ids'] or v['dup_ci'] or v['bad']: err.append('broken ID references: %s' % v)
    if 'CMsPreviewExtension' in x:      # saved by Multisim: the user's own drawing, labels placed by Multisim itself
        warn.append('layout not checked: the file was saved by Multisim (only files built by the skill are checked)')
    else:
        sc = geom.Scene(D.objs, D.el)
        import scheme
        for w in scheme.lint(sc):
            err.append('on the sheet: ' + w)
    nets, parts = nets_and_parts(D, x)
    # supply
    import spice
    for e in D.el:
        for c in e.iter('CiComponent'):
            if dec(c.get('LocalName') or '') == 'VCC':
                p = spice.params(c)
                if p and float(p[0]) == 5: warn.append('VCC is 5 V (the default of vcc()): make sure the circuit is meant for 5 V')
                break
    # circuit parameters
    names = [dec('&' + n) for n in re.findall(r'<CircuitParamName NameItem="&amp;([^"]*)"', x)]
    used = {dec('&' + p) for p in re.findall(r'<Item Value="&amp;(?:ASC|UNI)([A-Za-z_][^"]*)"/>', x)}
    for n in names:
        if not any(re.search(r'\b%s\b' % re.escape(n), u) for u in used): warn.append('circuit parameter %s is not used by any part' % n)
        for lab in re.findall(r'Output="&amp;(?:ASC|UNI)(%s[A-Za-z]+)' % re.escape(n), x):
            warn.append('a label reads «%s»: add subst {%r: %r} so it shows the parameter alone' % (lab, lab, n))
    # Batched
    states = AN.sim_states(x)
    if states:
        prefix, root = AN.loads(states[0][2])
        batch = root[0].get('ANALYSES').get('ANALYSIS_LIST').value
        for b in batch:
            t = '«%s»' % AN.text(b['PLOT_TITLE'])
            if not AN.text(b['PLOT_TITLE']).strip(): warn.append('%s analysis without a title (Grapher page name)' % b.key)
            sel = AN.selected(b)
            if not sel: err.append('%s %s has no output variables' % (b.key, t))
            for var in sel:
                ns, srcs = refs(var['NAME'])
                bad = [n for n in ns if n.lower() not in nets] + ['I(%s)' % s.upper() for s in srcs if s.lower() not in parts]
                if bad: err.append('%s %s: %s names %s — not in the circuit (nets: %s)' % (
                    b.key, t, AN.show_var(var['NAME']), ', '.join(bad), ', '.join(sorted(nets, key=lambda s: (len(s), s)))))
            a = b.get('ANALYSIS')
            if b.key == 'FOUR':
                tm, f, n = a.get('Tran')['TMAX'], float(a['FundFreq']), int(a['NumFreqs'])
                if tm == 'calculate' or float(tm) > 1 / (100 * n * f) * 1.0001:
                    warn.append('%s %s: max step %s is coarse for %d harmonics of %g Hz — use tmax ≤ %g' % (
                        b.key, t, tm, n, f, 1 / (100 * n * f)))
            if b.key in ('AC', 'NOISE'):
                fo = a if b.key == 'AC' else a.get('FREQ_OPT')
                if fo['VARIATION'] != 'lin' and float(fo['NPOINTS_PER_VARIATION']) < 50:
                    warn.append('%s %s: %s points per %s — the −3 dB frequencies come out coarse (use 100)' % (
                        b.key, t, fo['NPOINTS_PER_VARIATION'], {'dec': 'decade', 'oct': 'octave'}[fo['VARIATION']]))
            if b.key == 'NOISE':
                src = a['InputRefSource']
                if not src or src[1:].lower() not in parts: err.append('NOISE %s: input source %r is not in the circuit' % (t, src[1:].upper()))
                for k in ('OutputNode', 'ReferenceNode'):
                    n = a[k].lstrip('$').lower()
                    if n and n not in nets: err.append('NOISE %s: %s %s is not a net of the circuit' % (t, k, a[k]))
            if b.key == 'PSWEEP' and a['SweepType'] == '3':
                p = a.get('VariableParamToSweep')['name']
                if p.lower() not in {n.lower() for n in names}: err.append('PSWEEP %s sweeps %s — no such circuit parameter' % (t, p))
    # description
    import describe
    r = describe.read(path)
    if r:
        for p in rtf_paragraphs(r):
            s = p[:60]
            if re.match(r'#{1,6}\s', p): err.append('description: heading left as text «%s»' % s)
            if '**' in p or re.search(r'!\[.*?\]\(', p) or re.search(r'\|\s*-{3,}', p) or '_{' in p or '^{' in p:
                err.append('description: markup left as text «%s»' % s)
            m = re.search(r'(?<![\w$])([A-Za-zА-Яа-я])_([A-Za-zА-Яа-я0-9]{1,3})(?![\w(])', p)
            if m: err.append('description: «%s» — a subscript needs braces: %s_{%s}' % (m.group(0), m.group(1), m.group(2)))
    return err, warn


def main(path):
    err, warn = check(path)
    err, warn = list(dict.fromkeys(err)), list(dict.fromkeys(warn))
    for e in err: print('ERROR   ' + e)
    for w in warn: print('WARNING ' + w)
    if err:
        print('NOT READY — fix every ERROR, rebuild and run check.py again; do not give this file to the user.')
        return 1
    print('READY%s — give the file to the user%s.' % (' with warnings' if warn else '',
                                                       ' and tell them about each WARNING' if warn else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
