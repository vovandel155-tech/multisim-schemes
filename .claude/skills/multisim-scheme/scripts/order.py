"""Order missing parts from the user's Multisim in one step: write donors_request.txt and pack get_parts.zip for the user.

    python3 scripts/order.py "U1;Analog;OPAMP;TL072|TL072CP" "Q1;Transistors;BJT_NPN;BD139" "Q2;Transistors;BJT_PNP;BD140"

Each line: placeholder;group;family;part — variants of family and part separated by '|' (database names often have a
suffix). Placeholders of the template: Q1 npn, Q2 pnp, M1 n-MOSFET, M2 p-MOSFET, J1 n-JFET, D1 diode, Z1 LED,
R1 resistor, C1 capacitor, L1 inductor, U1 opamp 5 pins, U2 opamp 7 pins, U3 digital IC, U4 timer 555, U5 regulator.
Every line is checked before anything is packed (a wrong line wastes the user's round trip through Multisim):
the group is ONE Multisim group (variants only in family and part), and the placeholder can take that group/family —
ReplaceComponent swaps a part only for one of the same kind (a resistor only for R/L/C). Connectors, switches, fuses,
ferrite beads, microcontrollers and other kinds have no placeholder: the user places them in an empty file (option 3).
Parts already in the catalog are dropped with a note. The zip (default ./get_parts.zip) holds the skill's get_parts.bat,
the request, scripts/ and samples/: the user unpacks it, closes Multisim, double-clicks get_parts.bat and sends back the
files from donors_new (and samples/ni/donors_log.txt). Then:
    python3 scripts/harvest.py RETURNED_FOLDER -o ./ni_extra      and build with  MSGEN_REGISTRY=./ni_extra
"""
import sys, os, re, zipfile, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry

SKILL = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
PLACEHOLDERS = {'Q1': 'npn', 'Q2': 'pnp', 'M1': 'n-MOSFET', 'M2': 'p-MOSFET', 'J1': 'n-JFET', 'D1': 'diode', 'Z1': 'LED',
                'R1': 'resistor', 'C1': 'capacitor', 'L1': 'inductor', 'U1': 'opamp 5 pins', 'U2': 'opamp 7 pins',
                'U3': 'digital IC', 'U4': 'timer 555', 'U5': 'regulator'}
# placeholder → (its group, family regex): what ReplaceComponent can put in its place (same kind and pin count)
ACCEPTS = {'Q1': ('Transistors', r'BJT_NPN|DARLINGTON_NPN|BJT_NRES'), 'Q2': ('Transistors', r'BJT_PNP|DARLINGTON_PNP|BJT_PRES'),
           'M1': ('Transistors', r'\w*MOS\w*_N'), 'M2': ('Transistors', r'\w*MOS\w*_P'), 'J1': ('Transistors', r'JFET_N'),
           'D1': ('Diodes', r'(?!LED$|FWB$|SCR$|DIAC$|TRIAC$|BRIDGE)\w+'), 'Z1': ('Diodes', r'LED'),
           'R1': ('Basic', r'RESISTOR|CAPACITOR|CAP_ELECTROLIT|INDUCTOR'),
           'C1': ('Basic', r'RESISTOR|CAPACITOR|CAP_ELECTROLIT|INDUCTOR'),
           'L1': ('Basic', r'RESISTOR|CAPACITOR|CAP_ELECTROLIT|INDUCTOR'),
           'U1': ('Analog', r'\w+'), 'U2': ('Analog', r'\w+'), 'U3': ('TTL|CMOS', r'\w+'),
           'U4': ('Mixed', r'TIMER'), 'U5': ('Power', r'VOLTAGE_REGULATOR|VOLTAGE_REFERENCE')}
NO_PLACEHOLDER = ('no placeholder can become %s/%s (ReplaceComponent keeps the kind of part). Ask the user to place '
                  'such parts in an empty Multisim file and send it (option 3), or use a catalog part')


def check_line(f):
    """reasons why the order line [placeholder, group, family, part] cannot work; [] when it is fine"""
    ph, grp, fam = f[0], f[1], f[2]
    if '|' in grp: return ['group %r: ONE Multisim group — variants go into family and part only' % grp]
    bad = []
    fits = [p for p, (g, rx) in ACCEPTS.items() if re.fullmatch(g, grp, re.I)
            and all(re.fullmatch(rx, x.strip(), re.I) for x in fam.split('|'))]
    g, rx = ACCEPTS[ph]
    if not re.fullmatch(g, grp, re.I):
        bad.append('placeholder %s (%s) takes group %s, not %s' % (ph, PLACEHOLDERS[ph], g.replace('|', ' or '), grp))
    else:
        bad += ['placeholder %s (%s) cannot become family %s' % (ph, PLACEHOLDERS[ph], x.strip())
                for x in fam.split('|') if not re.fullmatch(rx, x.strip(), re.I)]
    if bad:
        bad.append('use placeholder %s' % ' or '.join(fits) if fits else NO_PLACEHOLDER % (grp, fam))
    return bad


HEADER = '''# Parts requested by Claude for the next scheme (filled in by Claude, then run get_parts.bat).
# placeholder;group;family;part   - family and part may list variants: A|B
# placeholders: Q1 npn, Q2 pnp, M1 n-MOSFET, M2 p-MOSFET, J1 n-JFET, D1 diode, Z1 LED, R1 resistor, C1 capacitor,
#               L1 inductor, U1 opamp 5 pins, U2 opamp 7 pins, U3 digital IC, U4 timer 555, U5 regulator
'''


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('lines', nargs='+', help='placeholder;group;family;part')
    ap.add_argument('-o', default='get_parts.zip', help='the zip for the user')
    a = ap.parse_args()
    keep, errors = [], []
    for line in a.lines:
        f = [x.strip() for x in line.split(';')]
        if len(f) != 4 or not all(f): errors.append('%s\n    need placeholder;group;family;part' % line); continue
        if f[0] not in PLACEHOLDERS:
            errors.append('%s\n    unknown placeholder %s: one of %s' % (line, f[0], ', '.join(PLACEHOLDERS))); continue
        bad = check_line(f)
        if bad: errors.append(line + ''.join('\n    ' + b for b in bad)); continue
        have = [n for n, e, _ in registry.need(f[3].split('|')) if e]
        if have: print('already in the catalog: %s — not ordered' % have[0]); continue
        keep.append(';'.join(f))
    if errors:
        print('NOT ORDERED — fix these lines (nothing was packed, the user has nothing to run yet):')
        for e in errors: print('  ' + e)
        sys.exit(1)
    if not keep: print('nothing to order'); return
    req = os.path.join(SKILL, 'donors_request.txt')
    open(req, 'w', newline='\r\n').write(HEADER + '\n'.join(keep) + '\n')
    with zipfile.ZipFile(a.o, 'w', zipfile.ZIP_DEFLATED) as z:
        for top in ('get_parts.bat', 'donors_request.txt', 'scripts', 'samples'):
            p = os.path.join(SKILL, top)
            files = [p] if os.path.isfile(p) else [os.path.join(d, n) for d, _, ns in os.walk(p) for n in ns
                                                   if '__pycache__' not in d]
            for f in sorted(files): z.write(f, os.path.join('multisim-parts', os.path.relpath(f, SKILL)))
    print('ordered:'); [print('  ' + k) for k in keep]
    print('package for the user: %s (%d KB)' % (os.path.abspath(a.o), os.path.getsize(a.o) // 1024))


if __name__ == '__main__':
    main()
