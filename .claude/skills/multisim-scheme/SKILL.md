---
name: multisim-scheme
description: Builds NI Multisim 14 schematics (.ms14 files) programmatically that open without any dialogs and simulate right away — from a picture, a screenshot or a description, with the layout of the picture. Any part of the Multisim database by name (transistors, op-amps, diodes, LEDs, ICs, sources) from a catalog of real parts; missing parts are extracted from Multisim itself on the user's PC with one .bat file. Instruments (multimeter, oscilloscope, function generator, Bode plotter, counter…) and probes; subcircuits (Schottky, multi-emitter transistors), CMOS with substrate pins; a library of ready blocks. Checks: overlaps, PNG preview, ngspice (truth table or signal swing). Use when the user asks to draw/build/generate a Multisim circuit or a .ms14 file, sends a schematic image to rebuild in Multisim, or asks to unpack/inspect a .ms14 file — in any language.
---

# NI Multisim schematics (.ms14) from Python

A scheme is a short script: elements placed on grid cells, wires, and that is it. `build()` does the rest:
- copies every element whole (symbol, model, database data) from files saved by Multisim itself:
  the samples in `samples/` and the catalog of real parts in `samples/ni/` (≈250 parts, instruments);
- sizes and centers the sheet, places the labels;
- compresses the file into the .ms14 format;
- checks the result: references, overlaps, preview, behaviour in ngspice.

Verified in Multisim 14.3: 18 textbook TTL/Schottky TTL/CMOS gates, catalog parts (op-amps, transistors, Darlingtons,
LEDs), instruments, probes, block library, circuits rebuilt from screenshots — they open without dialogs and the
readings match ngspice.

Talk to the user in their language; everything written into files (scripts, comments) stays in English.

## Step 0 — update the skill (every new chat, before any work)
```bash
python3 <skill folder>/scripts/update.py
```
The script copies the skill to a working folder and downloads from GitHub the files changed since the zip was uploaded
(code, part catalog, blocks, rules). The last line is `SKILL_DIR=<folder>`: **use paths from it from now on**
(`<SKILL_DIR>/scripts`, `<SKILL_DIR>/examples`…). If it prints «SKILL.md changed», read `<SKILL_DIR>/SKILL.md` and follow it.
In the first answer mention the skill version in one short line (e.g. «skill v5, updated from GitHub»). With no network
or closed access the script says so and works with the zip version: tell the user in one line what is needed (network
access to raw.githubusercontent.com in the claude.ai settings) and go on.
Inside a git repository (Claude Code) the script downloads nothing — `git pull` updates it there.

## Quick start
```python
import sys, os; sys.path.insert(0, '<skill folder>/scripts')
from scheme import *
S=Scheme('CMOS_inverter')                        # file name → output/CMOS_inverter.ms14
P=S.part
P('Q1','PMOS','S',10,3,rot=180,mirror=True)     # element, type, anchor pin, cell (x, y): S (10,3), G (7,6), SUB (12,7), D (10,11)
P('Q2','NMOS','D',10,15)                        # D (10,15), G (7,20), SUB (12,19), S (10,23)
vdd=S.vcc(10,-1); g=S.gnd(10,27)               # symbols → terminals for wires
x=S.switch('S1',0,13)                           # switch to VCC/ground, common pin at (0,13) → terminal
y=S.meter('XMM1',16,13)                         # multimeter: «+» at (16,13), «−» goes to ground by itself → terminal
S.wires([
 [vdd,J(10,1)],[J(10,1),('Q1','S')],[('Q1','SUB'),(12,1),J(10,1)],    # J — junction dot, (x,y) — bend
 [('Q1','D'),J(10,13)],[J(10,13),('Q2','D')],[J(10,13),y],
 [x,J(4,13)],[J(4,13),(4,6),('Q1','G')],[J(4,13),(4,20),('Q2','G')],
 [('Q2','S'),J(10,25)],[('Q2','SUB'),(12,25),J(10,25)],[J(10,25),g],
])
S.build()
```
Run from the project folder: `python3 my_scheme.py`. The result is `output/<name>.ms14`, working files go to `.msgen/`
(overridden by `MSGEN_OUT`, `MSGEN_WORK`, `MSGEN_SAMPLES`). Ready examples — `examples/`.

## Workflow
1. **Analyse the scheme.** List the elements and nets. With a picture, take the coordinates from it: grid cells (1 cell = 9 Multisim px), scale — a transistor (drain–source, collector–emitter) = 8 cells.
2. **Look up the pins:** `python3 <skill>/scripts/scheme.py pins` prints the pin offsets of all types for the main orientations;
   `scheme.py pins 2N3904 FGEN` — catalog parts. For missing parts see «Any scheme from a picture».
3. **Write the script** following `examples/`. One functional group — one comment. Route the wires as in the picture.
   First look for ready blocks in the picture (`python3 <skill>/scripts/blocks.py` lists them): CMOS inverter, 2-input NAND/NOR,
   input protection, transistor switch, push-pull follower, divider, RC filters, LED with resistor — place them with
   `S.block` and only the rest as single parts (see «Blocks»).
4. **Run it and read the report:**
   - nets — compare with the source scheme;
   - `ID references: OK`;
   - `overlaps: none` — otherwise fix them, see «What the warnings mean»;
   - preview `.msgen/preview/<name>_zoom.png` — always look at it;
   - the truth table and the function name from ngspice (with a sine source — peak-to-peak and mean on the multimeter).
5. **Give the file to the user** to check in Multisim. New schemes one at a time: each check may reveal a rule worth keeping.

## API (`scripts/scheme.py`)
- `Scheme(name, sheet_min=(14,11), margin=0.75, outdir=None, tmax=1e-5)` — `tmax` is the interactive simulation step (see the rules).
- `part(name, kind, pin, x, y, rot=0, mirror=False, value=None, label='auto')` places an element so that pin `pin` lands in cell (x, y).
  - `rot` — 0/90/180/270;
  - `value` — resistor value (`'4k'`, `'130'`, `'1.6k'`);
  - `label` — `'auto'` / `'right'` / `'left'` / `'top'` / `'bottom'` / `None`;
  - `kind` — a type from `KINDS` or a catalog part name (`'2N3904'`, `'LM358N'`, `'FGEN'`); `subst={'.2':'10'}` — parameters.
- `probe(name, x, y, kind='V', ref=None)` — a probe on a wire (see «Probes»).
- `vcc(x,y,volts=None)`, `gnd(x,y)` — a VCC symbol (5 V or `volts`; all VCC of a scheme are one net) or a ground with its pin at (x, y); return a terminal.
- `switch(name, x, y, vcc=2, gnd=2, right=False)` — a switch to VCC/ground. Common pin at (x, y), the VCC/ground pins 7 cells to the left (`right=True` — to the right), with their own VCC and GND symbols.
- `meter(name, x, y, gnd=4)` — a multimeter, «+» at (x, y), «−» 2 cells to the right with a ground `gnd` cells below.
- `wire(a, *bends, b)`, `wires([...])` — a wire:
  - ends — a terminal `('Q1','G')` or a junction `J(x,y)`;
  - in between — bends `(x,y)`;
  - 3 or 4 wires at a junction; a junction with 2 wires becomes a bend.
- `block(name, x, y, rot=0, mirror=False, names=None, label='auto', **parameters)` — a block from the library (see «Blocks»); → dict of terminals.
- `pos(t)` — the cell of a terminal or a junction before the build (e.g. to put a ground right below a block terminal).
- `build(checks=True)` — two passes: size, then sheet and centering. Then `finalize`, then the checks.

## Element types (`KINDS`), pins at rot=0
| type | what it is | pins (cells) |
|---|---|---|
| `R` | resistor, `value` | 1 (0,0), 2 (0,5); `rot=270` — horizontal: 2 (5,0) |
| `Q` | npn 2N2222 | C (0,0), B (−3,4), E (0,8) |
| `P` | pnp 2N2907A (value hidden) | as `Q`; `rot=180, mirror=True` — emitter on top |
| `QS` | Schottky npn — subcircuit (2N2222 + 10BQ015), symbol with «hooks» | as `Q` |
| `QM` | 4-emitter npn — subcircuit | B (0,0), E1–E4 (−8,5) (−6,5) (−4,5) (−2,5), C (3,5) |
| `QM2`, `QMS2` | 2-emitter npn / 2-emitter Schottky (with «hooks») — subcircuit, sheet from a hierarchical block file | B (0,0), E1 (−4,5), E2 (−2,5), C (3,5) |
| `D`, `DS` | diode 1BH62 / Schottky 10BQ015 | A (0,0), K (0,−6) — cathode up |
| `NMOS`, `PMOS` (`_DEP`) | MOS with a substrate pin | D (0,0), G (−3,5), S (0,8), SUB (2,4); p-MOS source up — `rot=180, mirror=True` |
| `VCC`, `GND`, `SW`, `XMM` | via `vcc()`, `gnd()`, `switch()`, `meter()`; a multimeter between two nodes — `part('XMM1','XMM','1',x,y)`: «+» (0,0), «−» (2,0) | |
| `C` | capacitor (virtual), `value='200p'`, `'0.33u'` | as `R` |
| **without a sample** (`SpiceLib`, synthesized — did not work in Multisim; use catalog parts `AC_VOLTAGE`, `2N3904`, `2N3906`, `TIP121G`, `TIP127G`, `1N4148` instead): | | |
| `VSIN`, `Q3904`, `P3906`, `TIP121`, `TIP127`, `D4148x4` | sine source, 2N3904/2N3906 (LTspice), Darlingtons, 4×1N4148 | as `R` / `Q` / `P` / `D` |

`mirror=True` flips an element horizontally: the gate or base ends up on the right. Several subcircuit kinds in one scheme are possible only when `COMBINED` (`scheme.py`) has a common base for the set; currently `QS` + `QMS2` (base `@SchottkyMulti2`, the second sheet is added by `copy_sheet`).

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
  - positive — `S.vcc(x, y, volts=15)` (all VCC of a scheme are one net) or `DC_POWER` with `subst={'12':'15'}` (a separate
    source, pins 1 «+» and 2 «−»);
  - negative rail — `VEE` (`S.part('VEE1','VEE','VEE',x,y,rot=180,refdes='VEE',subst={'-15':'-5'})`; the catalog donor
    defaults to −15 V) or `DC_POWER` with its plus to ground;
  - **do not use `DC_INTERACTIVE_VOLTAGE` for a fixed supply**: it is a source with a slider (key A, voltage =
    maximum × slider position), `value`/`subst` do not set its voltage — it gave 0 V in a real chat;
  - signal — `AC_VOLTAGE` (amplitude `.2` → `subst={'.2':'1'}`, label «Vpk»), square wave — `CLOCK_VOLTAGE`,
    pulses — `PULSE_VOLTAGE`.
- **The `build()` report** lists the catalog parts: `from catalog: Q1 BJT_NPN/2N3904 ← donor (RefDes, Multisim version)`.
- **Unknown part** — `build()` does not start: «ERROR: part X is neither … similar: …». Never silently substitute a similar one:
  order it (below) or suggest an equivalent and tell the user.
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
   `samples/template_replace.ms14`). Multisim groups/families: Transistors (BJT_NPN, BJT_PNP, DARLINGTON_NPN/PNP,
   MOS_ENH_N/P, POWER_MOS_N/P, JFET_N/P), Diodes (DIODE, ZENER, LED, SWITCHING_DIODE, SCHOTTKY_DIODE, FWB),
   Analog (OPAMP, COMPARATOR), TTL (74STD, 74LS), CMOS (CMOS_5V), Mixed (TIMER), Power (VOLTAGE_REGULATOR).
   Ask the user to close Multisim and run `get_parts.bat`: `scripts/donors.vbs` (COM `ReplaceComponent`,
   database 0 = Master Database, multi-section parts — section A) → `scripts/harvest.py --keep` (catalog `samples/ni/`).
   - **Git project** (the skill lives in a repository): the bat runs `git pull` before and `git push` after; then `git pull`,
     the log is `samples/ni/donors_log.txt`.
   - **Chat without git:** pack the skill's `get_parts.bat`, `donors_request.txt`, `scripts/` and `samples/` into a zip for the
     user; the user sends back the files from `donors_new` and `samples/ni/donors_log.txt`; add them to a catalog:
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

## Probes (`S.probe`)
`S.probe('PR1', x, y, kind)` — a Multisim probe (Place → Probe) with its tip in cell (x, y) of a wire:
`'V'` voltage, `'I'` current, `'VI'` voltage and current, `'P'` power (tip on an element pin), `'D'` digital,
`'REF'` reference point; `S.probe('PR5', x, y, 'V', ref='Ref1')` — voltage relative to the reference probe.
Names as in Multisim: `PR1…`, `Ref1…`. A probe is cloned from the samples (`sample_probes`, `sample_probe_vi`);
in the file it lives in three places: the symbol `CIITProbeExtComponent` (position, `Direction` along the wire:
horizontal 3, vertical 5, pin 0), `CiProbeExtComp` in the `ProbeExts` list and an `InstrumentsData` entry
(key — `FileDataPackageID`). The kind is a code at the end of `NI_EWB_DATABASEDATA_EXT` (1 V, 2 I, 3 VI, 4 P, 5 D, 6 REF).
No wire in the cell — a build error. In the preview — a green diamond with the name. Probes are skipped in ngspice.
The overlap check does not look at probe labels yet — keep probes away from element labels.

## Rules (found by checking in Multisim — do not break them)
- **Compress only with `blast.write_ms2()`** (a real PKWARE implode). Multisim does not open a literal-only file.
- **Read and write XML only via `msgen.Doc` / `msgen.serialize`.** They keep line breaks inside attributes; without them Multisim silently refuses the file.
- **`finalize(..., rename=False)`.** Renaming the project inside the file breaks it. `Scheme` already does this.
- **Custom sheet ≥ 14×11 inches.** The standard 960×720 is too small. `build()` picks the size and centers the scheme; do not ask the user about the sheet size.
- **The interactive simulation step TMAX is set manually (1e-5 s).** With an «automatic» step a CMOS scheme where no source delivers current (output 0) does not start: «This circuit has no power sources…».
- **Subcircuits.** The symbol is stored in every instance, and `SchottkyLib`/`MultiEmitterLib` draw it themselves. Net name conflicts between subcircuits (the «Resolve Net Name Conflict» dialog) are resolved in advance by `finalize` (`net_names`).
- **Switches.** Animation frames move together with the symbol (`place()`), otherwise the switch «jumps» when pressed.
- **GUIDs are unique and different in every file.** Every wire, pin and instance has its own GUID (as in Multisim files), and `finalize` replaces all GUIDs of the document with new ones derived from the file name (`renew_guids`). Multisim confuses schemes with identical GUIDs (e.g. built on one base) when they are open at the same time: the multimeter stops the simulation, readings freeze, opening hangs.
- **Instrument data.** Every instrument has an entry in the main sheet `InstrumentsData` «XMM1#1/<sheet name>:» (`instruments`), as in Multisim files; without it the multimeter stopped the simulation.
- **Deterministic build.** Running again gives the same file. Handy for regression: rebuild and compare sha1.

## Layout «as in the picture»
- **Ground — one common bus at the bottom** with a GND symbol. A separate ground only where the picture has one.
- **Junctions.** 3 or 4 wires at a junction; where 4 wires meet in the picture — one `J` junction with 4 wires (Multisim supports it). Crossing wires without a dot are not connected. Put such crossings where the picture has them.
- **MOS substrate.** A loop from SUB to the source: `[('Q1','SUB'),(x+2,y),J(x,y)]`, then the junction to the bus.
- **Distances:**
  - switches of neighbouring inputs — 13–14 cells apart vertically, otherwise the VCC label of the lower switch runs into the ground of the upper one; if the inputs are close, move a switch to the left (`switch('S2',-14,…)`);
  - parallel wires and ends of neighbouring wires — at least 2 cells apart: on adjacent cells they look like one wire.
- **Do not add extra «air»:** 100–150 cells² per element is normal (the report prints the density). Wire lengths — as in the picture.
- **Choose values missing from the picture so that the scheme works.** E.g. CMOS protection resistors — 1k: the gate current is zero, no effect on the logic.

## Blocks (`scripts/blocks.py`, `S.block`)
Frequent fragments, ready and verified: parts and wires inside are already placed; named terminals stick out.
Faster and more reliable than placing every part: fewer coordinates, fewer wiring mistakes.
```python
inv=S.block('cmos_inv',33,14)                         # block anchor cell (for the inverter — input IN) → (33,14)
S.wires([[x,inv['IN']],[inv['OUT'],y],[vdd,inv['VDD']],[inv['GND'],g]])
n=S.block('cmos_nand2',7,0,names={'Q_p1':'Q1','Q_p2':'Q2','Q_n1':'Q3','Q_n2':'Q4'})   # own part names
k=S.block('npn_switch',13,75,q='2N3904',rb='4.7k',rc='1k')                          # block parameters
```
- The list of blocks, their parameters, terminals with coordinates and sizes: `python3 scripts/blocks.py`.
- `python3 scripts/blocks.py show NAME [param=value …]` — a block alone with switches, supply and a multimeter: preview and ngspice.
- `rot`/`mirror` — as for a part, around the anchor cell (left-right mirror first, then rotation); all 8 variants are verified.
- Block parts get the first free names (Q1, Q2, D1…), so place parts with your own names **before** the blocks
  or pass `names`.
- A block terminal is a part terminal or a junction `J` inside where 2 block wires already meet: the external wire is the third
  (a fourth is possible too).
- The blocks were taken from verified textbook schemes: 5.19a (`cmos_inv`), 5.22a (`cmos_nand2`) and 5.21 (`cmos_protect`) built
  from blocks match the originals cell for cell.
- **New block:** a function `f(B, parameters…)` with `@block` in `blocks.py`. Inside — `B.part` / `B.wire` / `B.J` in local cells
  (the anchor is (0,0)), as in a scheme script. It returns a dict of terminals. A fragment of a good scheme is moved over by
  subtracting the anchor cell. Geometry that depends on the part — via `B.offs(type, anchor_pin, rot, mirror)` (see `npn_switch`, `push_pull`).
  Check — `blocks.py show`, then the rotations (no «slanted wire»).

## What the warnings mean
- `element X has no pin Y; available: …` — a typo in the pin name (see `scheme.py pins`).
- `junction without 3–4 wires` — 1 or more than 4 wires meet at a junction. A junction with 2 wires is a bend.
- `overlapping wires` / `wire bend lies on another wire` — two wires run along one line. Put a junction `J` at the touching point and split the wire, or move it aside.
- `wire runs through the body of X` — the wire crosses the element drawing (a source circle, a resistor body, a multimeter):
  in Multisim it looks like a connection or a shifted element. Bring the wire to the pin from outside, go around the body.
- `slanted wire` — a bend is not in the pin cell (a coordinate typo or the wrong anchor pin): the wire goes diagonally.
- `wire passes through pin` — the wire runs over an element pin: it looks like a connection, but there is none. Go around.
- `label … touches …` — give the label another side (`label='left'` etc.).
- `ngspice: not in the list` — the function is not a standard one (NOT, AND, OR, NAND, NOR, XOR). Look at the table. An open output shows ~0 V: the Multisim voltmeter is 1 GOhm.

## New element type
**Catalog first** (section «Catalog parts»): a Multisim database part by name, the donor is a Multisim sample or a file saved
by the user. A type in `KINDS` is needed only for an element with a special symbol (Schottky, multi-emitter) or a special tweak.

**Without a sample — `SpiceLib`** (a last resort: synthesized, not verified in Multisim — a bridge amplifier built with such
elements did not work) (`scripts/msgen.py`), when the element is described by a SPICE line or a subcircuit and has as many pins as a resistor (1, 2), a transistor (C, B, E) or a diode (A, K). That base is taken and the Multisim SPICE template (`%p` — RefDes, `%t<pin>` — node, `#k` — parameter, a subcircuit right in the template), the model (.MODEL), the names (family, type, RefDes prefix), the value unit and the drawing (a `draw` function builds segments, circles and polylines instead of the resistor body — see `draw_vsin`) are changed. The template starts with `* msgen`, and `spice.py` expands it the way Multisim does. Examples — the `VSIN`, `Q3904`, `TIP121` lines in `KINDS`. **Units:** Multisim builds the value label on the sheet and in the properties dialog from the base type (the type code is the first line of the second string list of `CiComponent`: resistor 29, capacitor 31, VCC 26, transistor/diode 46, switch 66), so an element on a resistor base always shows «Ohm» — hide such a value, and if the type exists in the samples (like the capacitor in base_5_1a) take it from there. The first file with such a new element — a separate small test, so that if Multisim refuses it, it is clear which element is to blame.

**With a sample** — more reliable, for elements with another number of pins, instruments and anything a SPICE line cannot describe:
1. A sample file saved by Multisim itself with this element is needed. Put it into `samples/` or the project folder.
2. Add a line to `KINDS`: `'TYPE': lambda: (doc('sample_x'), '&ASC<RefDes in the sample>', <value or None>)`.
3. Check the pins with `scheme.py pins`.
4. Build a test scheme and ask the user to open it in Multisim.

Elements with a non-standard symbol (Schottky, multi-emitter) are subcircuits. How they are stored in the file — see `reference.md`. The subcircuit content can be taken from any Multisim file (e.g. a hierarchical block): `transplant_sheet` moves its main sheet in place of the subcircuit sheet of a sample, a derived base is an entry in `DERIVED` (`scheme.py`), see `MultiNPN2`.

## Dependencies
- Python 3 (standard library only) — to build the file.
- `matplotlib` — for the preview.
- `ngspice` — for the truth table (switches S*) or the transient analysis (sine source: peak-to-peak and mean on the multimeter).

Without the last two the file is still built, and the report says what is missing.

## Files
- `scripts/scheme.py` — the API above, labels, overlap check, report; `scheme.py pins [PARTS]` — pins.
- `scripts/msgen.py` — the core: element cloning, wires, junctions, subcircuits, probes, sheet, instruments, `finalize`.
- `scripts/blast.py` — unpacking and compressing .ms14 (`read_ms`, `write_ms2`); `python3 scripts/blast.py f.ms14 f.xml`.
- `scripts/geom.py`, `scripts/render.py`, `scripts/validate.py` — geometry, PNG preview, ID reference check.
- `scripts/spice.py` — netlist from the file and the check in ngspice.
- `scripts/update.py` — self-update from GitHub (step 0); `update.py --release --note TEXT --zip PATH` — (in the repository)
  a new `version.json` and skill zip. `version.json` — repository, branch, version number, note, sha1 of the files.
- `scripts/blocks.py` — the block library (`S.block`); `blocks.py` — the list, `blocks.py show NAME` — a block alone.
- `scripts/registry.py` — the part catalog (`samples/ni/`, `MSGEN_REGISTRY`, the skill samples); `--need A B …`.
- `scripts/harvest.py` — a catalog from Multisim files (`--keep` — add to the current one, `--samples` — the Multisim samples).
- `scripts/donor_template.py` — the placeholder template for `donors.vbs`.
- For the user's PC (Windows, Multisim 14, nothing to install): `get_parts.bat` + `donors_request.txt` — part
  extraction; `scripts/donors.vbs`, `scripts/resave.vbs` (re-saving old files as .ms14), `scripts/dbprobe.vbs`.
- `samples/` — sample files saved by Multisim: `base_5_1a` (the base; R, Q 2N2222, D, C, VCC, GND, SW, XMM), `base_5_1g`
  (Schottky 10BQ015), `sample_pnp`, `sample_mos`, `sample_schottky_subckt`, `sample_multiemitter`, `Multi_emitter_npn`,
  `multi_emitter_shotki` (hierarchical blocks — the sheets of `QM2`, `QMS2`), `sample_probes`, `sample_probe_vi`,
  `template_replace` (the template for `donors.vbs`).
- **File names in the skill — only ASCII letters, digits, `._-`**: the claude.ai uploader rejects other characters in paths.
- `samples/ni/` — the catalog of real parts: `catalog.json`, `catalog.txt` and `parts.bin` + `parts.idx` — the block of every part
  cut from its donor (symbol, CiComponent, pins, model, pin models, instrument settings; ≈ 4 KB per part).
- `examples/` — verified schemes: CMOS inverter, CMOS NAND, Schottky TTL NAND (Schottky subcircuit), TTL with multi-emitter
  transistors, diode shaper from a screenshot, TIP121G/TIP127G push-pull follower, RC filter with instruments, probes, a scheme of blocks (`blocks_and_led`).
- `reference.md` — the .ms14 format and the internals: read it to change the core or to take apart someone else's file.
