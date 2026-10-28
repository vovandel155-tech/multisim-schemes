# Project notes for Claude Code

This repository is the public home of the **multisim-scheme** skill: Python that writes native NI Multisim 14 `.ms14`
files, packaged as a Claude skill (`.claude/skills/multisim-scheme/`), plus a gallery of verified circuits.

## Language
- **Everything written into the repository is English**: code, comments, docs, commit messages, release notes.
- **Talk to the owner in Russian** (chat replies only).

## Owner and verification
- The owner checks every result by hand: downloads the `.ms14` from GitHub and opens it in **Multisim 14.3** on Windows.
  A new kind of circuit or element counts as working only after that check — build one at a time and wait.
- Do not put personal data into the repository (names, e-mails, local paths). Multisim writes the Windows user name
  and folder paths into saved files: scrub new sample/donor files before committing (see «Samples» below).

## Layout
- `.claude/skills/multisim-scheme/` — the skill: `SKILL.md` (manual and API), `scripts/` (`scheme.py` API, `msgen.py`
  core, `blast.py` compression, `blocks.py` block library, `registry.py`/`harvest.py` part catalog, `spice.py` ngspice
  check, `update.py` self-update and release), `samples/` (Multisim-saved sample files), `samples/ni/` (part catalog:
  `catalog.json`, `catalog.txt`, `parts.bin` + `parts.idx`), `examples/`, `reference.md` (file format and internals).
- `gallery/` — verified circuits (`ttl/`, `cmos/`, `demos/`, each script writes its `.ms14` next to itself) and preview
  images (`images/`); `gallery/experimental/` — not working yet (bridge amplifier: paused, do not resume unless asked).
- `multisim-scheme.zip` — the skill for upload to claude.ai; `get_parts.bat` — wrapper for the skill's part extraction.

## Workflow
1. Read `SKILL.md` first. A circuit is a script on `scheme.py`: `Scheme` → `part`/`block`/`vcc`/`gnd`/`switch`/`meter`
   → `wires` → `build()`. Take coordinates from the picture (grid cells; transistor = 8 cells).
2. Run from the repository root. Read the report: nets, `ID references: OK`, `overlaps: none`, the preview
   `.msgen/preview/<name>_zoom.png` (look at it), the ngspice function.
3. **Regression after any core change:** rebuild every `gallery/{ttl,cmos,demos}/*.py` and compare sha1 with the
   committed files — the build is deterministic, files must match byte for byte (or explain every difference).
4. **Release after any skill change:**
   `python3 .claude/skills/multisim-scheme/scripts/update.py --release --note "what changed" --zip multisim-scheme.zip`
   and commit `version.json` + the zip together. claude.ai copies of the skill update themselves from `main`
   (`version.json`: repo, branch `main`, path) — a change reaches users only when it is on `main`.

## Rules learned in Multisim (do not break)
- Compress only with `blast.write_ms2()` (real implode); a literal-only file is rejected.
- Read/write XML only via `msgen.Doc` / `msgen.serialize` (line breaks inside attributes must survive).
- `finalize(..., rename=False)` — renaming the project inside the file breaks it (this is why sample sheet titles stay).
- Sheet: Custom, at least 14×11 inches; `build()` sizes and centers it — never ask about the sheet size.
- GUIDs unique per object and per file (`renew_guids`); every instrument has its `InstrumentsData` entry.
- Interactive simulation TMAX = 1e-5 s is written into the file (CMOS circuits with no current otherwise refuse to start).
- The ngspice multimeter is a 1 GOhm voltmeter, as in Multisim.
- Layout as in the picture: one common ground bus at the bottom, 4-wire junctions where the figure has crossings with dots,
  wire lengths as in the figure; inputs — switches S1/S2 to VCC/ground, output — multimeter XMM1.
- Schottky transistors (with «hooks» in the figure) — subcircuit SchottkyNPN; pnp — 2N2907A from `sample_pnp`, `rot=180, mirror=True`.
- Fixed supplies: `vcc(volts=…)`, `DC_POWER` with `subst`, `VEE` with `subst` (catalog default −15 V); never `DC_INTERACTIVE_VOLTAGE`.

## Samples and the part catalog
- Samples must be files saved by Multisim itself. After adding one, replace the Windows user name and private folder
  names inside it (they appear as `&UNI_uc…` sequences in `RefDes`, `PathAbs`, `FileName`, `TreeInstancePath`, `User`,
  `OwnerName` attributes) and re-save with `blast.write_ms2`.
- New catalog parts: `python3 .claude/skills/multisim-scheme/scripts/harvest.py DONOR_FOLDER --keep -o .claude/skills/multisim-scheme/samples/ni`
  (old blocks stay untouched; the catalog stores only file names, never local paths).
- claude.ai uploader limits for the skill: ASCII-only paths, at most 200 files, no archives inside the zip.

## Pending checks in Multisim
- `gallery/demos/catalog_sources.ms14` (interactive source reading no longer mirrored).
- `gallery/demos/fzt1049a_switch.ms14`.
