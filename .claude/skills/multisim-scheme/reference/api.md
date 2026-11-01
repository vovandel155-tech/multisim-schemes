# Scheme API: parts, wires, probes

Read it when writing a scheme script. Paths are relative to the skill folder (`SKILL_DIR`).

## Contents
- API (`scripts/scheme.py`)
- Element types (`KINDS`), pins at rot=0
- Probes (`S.probe`)
- Dependencies
- Files

## API (`scripts/scheme.py`)
- `Scheme(name, sheet_min=(14,11), margin=0.75, outdir=None, tmax=1e-5)` — `tmax` is the interactive simulation step (see the rules).
- `part(name, kind, pin, x, y, rot=0, mirror=False, value=None, label='auto')` places an element so that pin `pin` lands in cell (x, y).
  - `rot` — 0/90/180/270;
  - `value` — resistor value (`'4k'`, `'130'`, `'1.6k'`);
  - `label` — `'auto'` / `'right'` / `'left'` / `'top'` / `'bottom'` / `None`;
  - `kind` — a type from `KINDS` or a catalog part name (`'2N3904'`, `'LM358N'`, `'FGEN'`); `subst={'.2':'10'}` — parameters.
- `net(name, t)` — name the net of terminal `t` (`('Q1','C')` or `J(x,y)`); Multisim keeps the name, analyses use `V(name)`. MUST for every net an analysis refers to.
- `probe(name, x, y, kind='V', ref=None)` — a probe on a wire (see «Probes» below).
- `vcc(x,y,volts=None)`, `gnd(x,y)` — a VCC symbol (5 V or `volts`; all VCC of a scheme are one net) or a ground with its pin at (x, y); return a terminal.
- `switch(name, x, y, vcc=2, gnd=2, right=False)` — a switch to VCC/ground. Common pin at (x, y), the VCC/ground pins 7 cells to the left (`right=True` — to the right), with their own VCC and GND symbols.
- `meter(name, x, y, gnd=4)` — a multimeter, «+» at (x, y), «−» 2 cells to the right with a ground `gnd` cells below.
- `wire(a, *bends, b)`, `wires([...])` — a wire:
  - ends — a terminal `('Q1','G')` or a junction `J(x,y)`;
  - in between — bends `(x,y)`;
  - 3 or 4 wires at a junction; a junction with 2 wires becomes a bend.
- `block(name, x, y, rot=0, mirror=False, names=None, label='auto', **parameters)` — a block from the library (see «Blocks» in [layout.md](layout.md)); → dict of terminals.
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
- `scripts/analyses.py` — analyses in the file (Batched): reading, writing, `Batch`, `rewrite`, `markup`; the format is in [format.md](format.md).
- `scripts/check.py` — the gate before giving a file away: READY / NOT READY (run by `build()` and the `rewrite` functions).
- `scripts/describe.py` — the circuit description (Description Box): markup → RTF, `put`, `rewrite`, `read`.
- `samples/description_sheet.xml` — the skeleton of the description sheet (from a Multisim-saved file).
- `scripts/update.py` — self-update from GitHub (step 0); `update.py --release --note TEXT --zip PATH` — (in the repository)
  a new `version.json` and skill zip. `version.json` — repository, branch, version number, note, sha1 of the files.
- `scripts/blocks.py` — the block library (`S.block`); `blocks.py` — the list, `blocks.py show NAME` — a block alone.
- `scripts/registry.py` — the part catalog (`samples/ni/`, `MSGEN_REGISTRY`, the skill samples); `--need A B …`.
- `scripts/order.py` — orders missing parts: `donors_request.txt` + `get_parts.zip` for the user.
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
- `reference/` — the details by topic (this file, `parts.md`, `layout.md`, `analyses.md`, `description.md`, `format.md`).
