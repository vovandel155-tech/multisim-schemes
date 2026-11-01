# Layout, blocks and build warnings

Read it when placing parts and wires, when the build report has warnings, or when a new element type is needed.

## Contents
- Layout «as in the picture»
- Blocks (`scripts/blocks.py`, `S.block`)
- What the warnings mean
- New element type

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
**Catalog first** ([parts.md](parts.md)): a Multisim database part by name, the donor is a Multisim sample or a file saved
by the user. A type in `KINDS` is needed only for an element with a special symbol (Schottky, multi-emitter) or a special tweak.

**Without a sample — `SpiceLib`** (a last resort: synthesized, not verified in Multisim — a bridge amplifier built with such
elements did not work) (`scripts/msgen.py`), when the element is described by a SPICE line or a subcircuit and has as many pins as a resistor (1, 2), a transistor (C, B, E) or a diode (A, K). That base is taken and the Multisim SPICE template (`%p` — RefDes, `%t<pin>` — node, `#k` — parameter, a subcircuit right in the template), the model (.MODEL), the names (family, type, RefDes prefix), the value unit and the drawing (a `draw` function builds segments, circles and polylines instead of the resistor body — see `draw_vsin`) are changed. The template starts with `* msgen`, and `spice.py` expands it the way Multisim does. Examples — the `VSIN`, `Q3904`, `TIP121` lines in `KINDS`. **Units:** Multisim builds the value label on the sheet and in the properties dialog from the base type (the type code is the first line of the second string list of `CiComponent`: resistor 29, capacitor 31, VCC 26, transistor/diode 46, switch 66), so an element on a resistor base always shows «Ohm» — hide such a value, and if the type exists in the samples (like the capacitor in base_5_1a) take it from there. The first file with such a new element — a separate small test, so that if Multisim refuses it, it is clear which element is to blame.

**With a sample** — more reliable, for elements with another number of pins, instruments and anything a SPICE line cannot describe:
1. A sample file saved by Multisim itself with this element is needed. Put it into `samples/` or the project folder.
2. Add a line to `KINDS`: `'TYPE': lambda: (doc('sample_x'), '&ASC<RefDes in the sample>', <value or None>)`.
3. Check the pins with `scheme.py pins`.
4. Build a test scheme and ask the user to open it in Multisim.

Elements with a non-standard symbol (Schottky, multi-emitter) are subcircuits. How they are stored in the file — see [format.md](format.md). The subcircuit content can be taken from any Multisim file (e.g. a hierarchical block): `transplant_sheet` moves its main sheet in place of the subcircuit sheet of a sample, a derived base is an entry in `DERIVED` (`scheme.py`), see `MultiNPN2`.
