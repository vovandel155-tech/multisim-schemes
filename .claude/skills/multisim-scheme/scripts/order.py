"""Order missing parts from the user's Multisim in one step: write donors_request.txt and pack get_parts.zip for the user.

    python3 scripts/order.py "U1;Analog;OPAMP;TL072|TL072CP" "Q1;Transistors;BJT_NPN;BD139" "Q2;Transistors;BJT_PNP;BD140"

Each line: placeholder;group;family;part — variants of family and part separated by '|' (database names often have a
suffix). Placeholders of the template: Q1 npn, Q2 pnp, M1 n-MOSFET, M2 p-MOSFET, J1 n-JFET, D1 diode, Z1 LED,
R1 resistor, C1 capacitor, L1 inductor, U1 opamp 5 pins, U2 opamp 7 pins, U3 digital IC, U4 timer 555, U5 regulator.
Parts already in the catalog are dropped with a note. The zip (default ./get_parts.zip) holds the skill's get_parts.bat,
the request, scripts/ and samples/: the user unpacks it, closes Multisim, double-clicks get_parts.bat and sends back the
files from donors_new (and samples/ni/donors_log.txt). Then:
    python3 scripts/harvest.py RETURNED_FOLDER -o ./ni_extra      and build with  MSGEN_REGISTRY=./ni_extra
"""
import sys, os, zipfile, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import registry

SKILL = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
PLACEHOLDERS = {'Q1': 'npn', 'Q2': 'pnp', 'M1': 'n-MOSFET', 'M2': 'p-MOSFET', 'J1': 'n-JFET', 'D1': 'diode', 'Z1': 'LED',
                'R1': 'resistor', 'C1': 'capacitor', 'L1': 'inductor', 'U1': 'opamp 5 pins', 'U2': 'opamp 7 pins',
                'U3': 'digital IC', 'U4': 'timer 555', 'U5': 'regulator'}
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
    keep = []
    for line in a.lines:
        f = [x.strip() for x in line.split(';')]
        if len(f) != 4 or not all(f): sys.exit('bad line %r: need placeholder;group;family;part' % line)
        if f[0] not in PLACEHOLDERS: sys.exit('unknown placeholder %s: one of %s' % (f[0], ', '.join(PLACEHOLDERS)))
        have = [n for n, e, _ in registry.need(f[3].split('|')) if e]
        if have: print('already in the catalog: %s — not ordered' % have[0]); continue
        keep.append(';'.join(f))
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
