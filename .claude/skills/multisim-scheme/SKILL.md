---
name: multisim-scheme
description: Builds NI Multisim 14 schematics (.ms14) that open without dialogs and simulate at once — from a picture, a screenshot or a description, laid out as in the picture, with real parts from the Multisim database (missing ones are fetched from the user's own Multisim with one .bat file), instruments and probes. Writes Batched analyses into a new or an existing file (operating point, AC, transient, Fourier, noise, parameter sweep) and a formatted circuit description with tables and pictures. Checks every file before it is given away (overlaps, supply, analyses, ngspice). Use when the user asks to draw, build or generate a Multisim circuit or a .ms14 file, sends a schematic to rebuild in Multisim, wants analyses or a description in a Multisim file, or asks to inspect a .ms14 — in any language.
---

# NI Multisim schematics (.ms14)

A scheme is a short Python script on `scripts/scheme.py`: parts on grid cells, wires, `build()`. The skill clones every
part from files saved by Multisim itself, writes the file, checks it and simulates it in ngspice.
**Language: everything the user will read is in the user's language** — the chat, Grapher page titles, the description,
labels you choose, circuit parameter names they gave (`Uвх` works). Scripts and code comments stay in English.

## Step 0 — update the skill (every new chat, before any work)
```bash
python3 <skill folder>/scripts/update.py
```
The last line is `SKILL_DIR=<folder>`: **use paths from it from now on**. If it prints «SKILL.md changed», read
`<SKILL_DIR>/SKILL.md` again. Tell the user the skill version in one short line. Without network the script says so —
tell the user that network access to raw.githubusercontent.com is needed for updates, and go on.

## Workflow — copy this checklist into your answer and tick it as you go
```
Multisim task:
- [ ] 1 Task listed: parts and values, supply, every quantity the user wants to see
- [ ] 2 Parts checked with registry.py --need; missing ones → get_parts offered FIRST
- [ ] 3 Script written: layout as in the picture, one ground bus, supply voltages explicit
- [ ] 4 build() report clean: ID references OK, overlaps none, supply right, preview looked at
- [ ] 5 The circuit really works: spice.run on the built file, every part does its job
- [ ] 6 Analyses (if asked): every quantity from step 1 is an output variable
- [ ] 7 Expected values: spice.run on the built file only
- [ ] 8 Description (if asked): pictures agreed with the user, numbers from step 7
- [ ] 9 check: READY → give the file, the expected values and every WARNING
```
1. **List the task.** Parts with values, nets, the supply (voltages, single or dual), and every quantity the user named
   («gain in times and dB», «quiescent current», «current of each source»…). This list is checked again in step 6.
2. **Check every part:** `python3 scripts/registry.py --need TL072 BD139 …`. A part is **MISSING** → ask the user one
   question with these options, in this order:
   1. **(recommended)** fetch it from their Multisim: `python3 scripts/order.py "U1;Analog;OPAMP;TL072|TL072CP" …`
      makes `get_parts.zip`; the user unpacks it, closes Multisim, double-clicks `get_parts.bat` (Python 3 needed) and
      sends back the files from `donors_new` — about a minute, nothing to place by hand;
   2. an equivalent that is in the catalog — say what changes;
   3. the user places the parts in an empty file and sends it.

   Placeholders, families and what to do with the returned files — [reference/parts.md](reference/parts.md).
3. **Write the script** as in «Quick start». Coordinates from the picture (grid cells; a transistor is 8 cells); ready
   blocks first (`python3 scripts/blocks.py`). Supply: `S.vcc(x, y, volts=12)` for logic (**without `volts` it is 5 V**);
   `DC_POWER` with `subst={'12':'15'}` for analog circuits — it gives the supply current `I(V1)` to analyses.
   Details — [reference/api.md](reference/api.md), [reference/layout.md](reference/layout.md).
4. **Run it and read the whole report.** `ID references: OK`, `overlaps: none`, the `supply:` line, the nets against
   the picture; **look at** the preview `.msgen/preview/<name>_zoom.png`. Every warning is fixed, never called
   «cosmetic» — the user hands the circuit in as it is. Warnings explained — [reference/layout.md](reference/layout.md).
5. **Make sure the circuit works as described**:
   `python3 scripts/spice.py out.ms14 "op; print all"` (and `tran`, `ac` as needed). If it worked only after you turned a
   part around or added one, find out why, tell the user, and check that each part does what the text says about it
   (bias diodes conduct at rest, a bias resistor sets the current…).
6. **Analyses** — [reference/analyses.md](reference/analyses.md). Every quantity from step 1 MUST be an output variable
   (a gain in dB is `db(V(out)/V(in))` in Single Frequency AC, not a formula in the description). In AC Sweep MUST be
   `V(out)/V(in)` with `vscale='db'`: `db(…)` on the Decibel axis is dB of dB (verified: 20.8 dB showed as 26.4). Currents through a resistor are
   `(V(a)-V(b))/R`. A source amplitude set by a circuit parameter: `subst={'.2':'Uin','UinVpk':'Uin'}`.
7. **Expected values MUST come from the built file**: `spice.run('out.ms14', 'op; print v(4) i(vv1); …')` — it uses the
   file's real supply, parts and parameters. Never compute them from a netlist you wrote yourself (a model once reported
   19.5 V results for a file that had a 5 V supply).
8. **Description** — [reference/description.md](reference/description.md). Before inserting pictures, ask the user:
   graphs computed in ngspice, or their own Multisim screenshots. Subscripts need braces: `K_{U}`, not `K_U`.
9. **Gate:** `build()` ends with `check: READY` / `NOT READY`; for a rewritten file run `python3 scripts/check.py out.ms14`.
   **NOT READY → fix, rebuild, check again; never give such a file away.** With READY give the file, the expected
   values and each WARNING in plain words. New kinds of circuits one at a time: the user checks each in Multisim.

## Rules (MUST)
- Never silently substitute a part, a value or a supply: say what changed and why.
- Never give away a file that `check` calls NOT READY, and never hide a WARNING.
- Numbers for the user only from `spice.run` on the very file you give.
- Missing parts: `get_parts` (`order.py`) is offered first.
- Read and write `.ms14` only through the skill's scripts (`Scheme`, `analyses.rewrite`, `describe.rewrite`): the format
  breaks silently otherwise — [reference/format.md](reference/format.md).

## Quick start
```python
import sys; sys.path.insert(0, '<SKILL_DIR>/scripts')
from scheme import *
S = Scheme('ce_stage')                                   # → output/ce_stage.ms14
P = S.part
P('V1', 'DC_POWER', '1', 0, 10)                           # 12 V source: 1 «+» (0,10), 2 «−» (0,14)
P('R1', 'R', '1', 16, 6, value='47k'); P('R2', 'R', '1', 16, 21, value='10k')
P('RC', 'R', '1', 28, 4, value='2.2k'); P('RE', 'R', '1', 28, 23, value='1k')
P('Q1', 'Q', 'C', 28, 12)                                # C (28,12), B (25,16), E (28,20)
g = S.gnd(16, 34)
S.wires([
 [('V1','1'), (0,2), J(16,2)], [J(16,2), ('R1','1')], [J(16,2), (28,2), ('RC','1')],     # J — junction, (x,y) — bend
 [('R1','2'), J(16,16)], [J(16,16), ('R2','1')], [J(16,16), ('Q1','B')],
 [('RC','2'), ('Q1','C')], [('Q1','E'), ('RE','1')],
 [('V1','2'), (0,31), J(16,31)], [('R2','2'), J(16,31)], [J(16,31), g], [J(16,31), (28,31), ('RE','2')],
])
S.op(['V(2)', 'V(3)', 'V(3)-V(4)', 'I(V1)'], title='1 Operating point')   # Batched analyses — reference/analyses.md
S.build()                                                # report + check: READY / NOT READY
```
Run from the project folder: `python3 my_scheme.py`. Pin offsets: `python3 scripts/scheme.py pins [PART…]`.
Verified scripts — `examples/`.

## Where to read more (one file per topic)
| Task | Read |
|---|---|
| Script API, element types, probes, files of the skill | [reference/api.md](reference/api.md) |
| A part by name, power and signal sources, missing parts, a scheme from a picture | [reference/parts.md](reference/parts.md) |
| Layout as in the picture, blocks, build warnings, a new element type | [reference/layout.md](reference/layout.md) |
| Batched analyses, circuit parameters, expected values | [reference/analyses.md](reference/analyses.md) |
| Circuit description (Description Box) | [reference/description.md](reference/description.md) |
| The .ms14 format, rules learned in Multisim, the generator internals | [reference/format.md](reference/format.md) |

## Scripts (run them, do not read them)
`scheme.py` (API, `pins`) · `registry.py --need` · `order.py` (missing parts → `get_parts.zip`) · `blocks.py` ·
`spice.py FILE "commands"` · `check.py FILE` · `analyses.py FILE` (list Batched) · `describe.py` · `update.py`
