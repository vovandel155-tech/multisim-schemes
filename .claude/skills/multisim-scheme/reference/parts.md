# Parts: the catalog, sources, missing parts

Read it when a scheme needs a part by name, a power or signal source, or a part that is not in the catalog.

## Contents
- Catalog parts — any element of the Multisim database
- Any scheme from a picture — the full cycle

## Catalog parts — any element of the Multisim database
The element type in `part()` can be **a part name from the Multisim database** — `'2N3904'`, `'LM358N'`, `'BC184BP'`, `'FGEN'` or
`'FAMILY/NAME'` (`'BJT_NPN/2N3904'`) when it is not in `KINDS`. The element is cloned whole from a donor file saved by
Multisim itself: symbol, model, database data, properties dialog — as if placed by hand. The catalog keeps not the whole
file but the block of the part (`samples/ni/parts.bin` + `parts.idx`, `msgen.PartPack`): a scheme from a block is byte-identical.
- **Is the part there:** `python3 scripts/registry.py --need 2N3904 LM358 1N4007` — «found» / «MISSING … similar: …»;
  the full list — `python3 scripts/registry.py [filter]` or `samples/ni/catalog.txt` (group, family, name, pins).
- **Pins and their places:** `python3 scripts/scheme.py pins 2N3904` (orientation as in the donor; `mirror=True` — mirrored).
- **Value:** `value='10k'` for parts with a value (resistor, capacitor…). Parameters without a value (source amplitude
  etc.) — `subst={'.2':'10'}`: values equal to the old one (numerically too) and the start of the value label are replaced.
- **Power sources** (verified in the netlist and on the label):
  - positive — `S.vcc(x, y, volts=15)` (all VCC of a scheme are one net; **without `volts` it is 5 V** — pass it on every
    circuit that needs another supply, the report line `supply:` shows what the file has) or `DC_POWER` with
    `subst={'12':'15'}` (a separate source, pins 1 «+» and 2 «−»; its current `I(V1)` is available to analyses);
  - negative rail — `VEE` (`S.part('VEE1','VEE','VEE',x,y,rot=180,refdes='VEE',subst={'-15':'-5'})`; the catalog donor
    defaults to −15 V) or `DC_POWER` with its plus to ground;
  - **do not use `DC_INTERACTIVE_VOLTAGE` for a fixed supply**: it is a source with a slider (key A, voltage =
    maximum × slider position), `value`/`subst` do not set its voltage — it gave 0 V in a real chat;
  - signal — `AC_VOLTAGE` (amplitude `.2` → `subst={'.2':'1'}`, label «Vpk»), square wave — `CLOCK_VOLTAGE`,
    pulses — `PULSE_VOLTAGE`.
- **The `build()` report** lists the catalog parts: `from catalog: Q1 BJT_NPN/2N3904 ← donor (RefDes, Multisim version)`.
- **Unknown part** — `build()` does not start: «ERROR: part X is neither … similar: …». Never silently substitute a similar one.
  **A part is missing — offer the user these options, in this order** (one question, before building):
  1. **(recommended) get it from their Multisim automatically:** `python3 scripts/order.py "U1;Analog;OPAMP;TL072|TL072CP"
     "Q1;Transistors;BJT_NPN;BD139" …` writes the request and packs `get_parts.zip`; give the user that zip with three
     steps: unpack it, close Multisim, double-click `get_parts.bat` (needs Python 3 on the PC), then send back the files
     from the `donors_new` folder. About a minute, nothing to place by hand. Placeholders and families — «Any scheme from
     a picture», step 3.
     `order.py` checks every line and packs nothing while one is wrong (NOT ORDERED): one group per line, the placeholder
     of the same kind. Connectors, switches, fuses, ferrite beads, microcontrollers have **no placeholder** — for them
     only option 3 (the user places them by hand), so ask for those in the same question, not after a second round.
  2. an equivalent that is already in the catalog (`registry.py --need`) — say what changes in the circuit;
  3. only if they prefer: they place the parts in an empty Multisim file themselves and send the .ms14.
  When the files come back: `python3 scripts/harvest.py RETURNED_FOLDER -o ./ni_extra`, build with `MSGEN_REGISTRY=./ni_extra`.
- **Instruments** are catalog parts too: `FGEN`, `SCOPE`, `BODE`, `WATTMTR`, `FREQCOUNTER`, `WGEN`, `LOGCONV`, `LOGICAN`,
  `DISTOR`, `SPEC_AN`, `NETAN`, `FGEN_AT`, `MULMETER_AT`, `SCOPE_TK`. Their settings (the `InstrumentsData` entry) are copied
  from the donor under the new RefDes. Pins (by the symbol labels): FGEN 1 «+», 2 COM, 3 «−»; SCOPE 1/4 — A+/A−, 2/5 — B+/B−,
  3/6 — external trigger; BODE 1/2 IN+/IN−, 3/4 OUT+/OUT−; WATTMTR 1/2 — V, 3/4 — I. Example — `examples/instruments_rc.py`.
- **ICs:** multi-section ICs are placed as one section (A); LM358N has a rectangle symbol with pins 1 cell apart.
  Digital IC pin models are copied. The first scheme with a new kind of IC — send it to the user to check in Multisim.
- **ngspice** expands the SPICE template of any part the way Multisim does (`spice.expand`); models with comments,
  subcircuits (`x%p …`), `{2*pi*…}` (a `.param pi` is added), the unit «A» after numbers (`1.5e-5A` is «atto» for ngspice,
  stripped) are handled. Instruments (except the multimeter) and probes are skipped in ngspice.
- **Not taken into the catalog:** parts from files built by the generator and not re-saved in Multisim (they have no
  `CMsPreviewExtension` preview) and parts synthesized with `SpiceLib`.

## Any scheme from a picture — the full cycle
The user sends a scheme (screenshot, textbook figure, LTspice, Micro-Cap…). Only the user has Multisim, so extracting the
missing parts is the user's only step: a double click on `get_parts.bat` (in the skill folder; in a git project — also in
the project root).
1. **Analyse the picture:** elements with names and values, nets, coordinates (grid cells; transistor = 8 cells).
   An «Input» port without a source — add a source (sine `AC_VOLTAGE` with the needed amplitude, a switch to VCC/ground for
   logic) and tell the user what was chosen. An ideal op-amp «IDEAL» — `OPAMP_3T_VIRTUAL` (±12 V saturation).
2. **Check the parts:** `registry.py --need …`. R, C, L, VCC, ground, switch, multimeter, sources are always there.
3. **Order the missing ones** as lines in `donors_request.txt` (skill folder): `placeholder;group;family;part`,
   variants separated by `|` — database names often have a suffix (`TIP121|TIP121G`, `BC547|BC547B`, `LM358|LM358N|LM358AD`).
   The template placeholder must be of the same kind: Q1 npn, Q2 pnp, M1/M2 MOS n/p, J1 JFET, D1 diode, Z1 LED, R1, C1, L1,
   U1 5-pin op-amp, U2 7-pin op-amp, U3 digital IC, U4 555 timer, U5 regulator (`scripts/donor_template.py` →
   `samples/template_replace.ms14`). The group is one name (no `|`); a resistor placeholder becomes only R/L/C — `order.py`
   refuses other lines and names the right placeholder. Multisim groups/families: Transistors (BJT_NPN, BJT_PNP, DARLINGTON_NPN/PNP,
   MOS_ENH_N/P, POWER_MOS_N/P, JFET_N/P), Diodes (DIODE, ZENER, LED, SWITCHING_DIODE, SCHOTTKY_DIODE, FWB),
   Analog (OPAMP, COMPARATOR), TTL (74STD, 74LS), CMOS (CMOS_5V), Mixed (TIMER), Power (VOLTAGE_REGULATOR).
   Ask the user to close Multisim and run `get_parts.bat`: `scripts/donors.vbs` (COM `ReplaceComponent`,
   database 0 = Master Database, multi-section parts — section A) → `scripts/harvest.py --keep` (catalog `samples/ni/`).
   - **Git project** (the skill lives in a repository): the bat runs `git pull` before and `git push` after; then `git pull`,
     the log is `samples/ni/donors_log.txt`.
   - **Chat without git:** `python3 scripts/order.py LINE…` does both — writes `donors_request.txt` and packs
     `get_parts.zip` (the bat, the request, `scripts/`, `samples/`) to hand to the user; the user sends back the files from
     `donors_new` and `samples/ni/donors_log.txt`; add them to a catalog:
     `python3 scripts/harvest.py FOLDER_WITH_FILES -o ./ni_extra` and build with `MSGEN_REGISTRY=./ni_extra`.
4. **Log:** `ok` — the part was obtained; «cannot be found» — another name; «Invalid Family/Group» — another family.
5. **Build the scheme** (`Scheme` → `part(...)` → `wires` → `build()`), report and preview as usual. Give the file to the
   user to check in Multisim.
Examples: `examples/diode_shaper.py` (a scheme from a screenshot), `examples/darlington_push_pull.py` (TIP121G/TIP127G
obtained with `donors.vbs`).

**Other donor sources** (on the user's PC): the samples installed with Multisim
(`C:\Users\Public\Documents\National Instruments\Circuit Design Suite 14.x\samples` — `harvest.py` without arguments
finds them), own files with parts placed (`harvest.py FILE_OR_FOLDER --keep -o samples\ni`), schemes of older
versions (.ms8–.ms13, e.g. from textbooks) — re-save them in a batch first with `scripts/resave.vbs` (32-bit
`C:\Windows\SysWOW64\cscript.exe //nologo resave.vbs FOLDER`). The Multisim component database (`MSCOMP_S.PRD`) is a
password-protected Access file: do not read or break into it.
