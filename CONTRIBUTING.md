# Contributing

Thanks for helping! Everything in the repository is written in English.

## Ground rules
- **Every new kind of circuit or element is checked in Multisim** (14.x) before it is called working. Say in the pull
  request what you opened and what you saw.
- **The build is deterministic.** After touching `scripts/`, rebuild every `gallery/{ttl,cmos,demos}/*.py` and compare
  the sha1 of the `.ms14` files with the committed ones; explain every difference.
- **No personal data.** Multisim writes your Windows user name and folder paths into saved files — scrub donor and
  sample files before committing (see `CLAUDE.md`, «Samples and the part catalog»).
- File names inside the skill: ASCII only (the claude.ai uploader rejects anything else).

## Adding parts
1. Put the part name into `.claude/skills/multisim-scheme/donors_request.txt` (`placeholder;group;family;part`).
2. Close Multisim and run `get_parts.bat` — it saves donors and runs `harvest.py --keep`.
3. Commit `samples/ni/` (the catalog keeps file names only, never local paths) and add a small demo to `gallery/demos/`.

## Adding a block
Write a function with `@block` in `scripts/blocks.py` (local cells, anchor at (0,0), returns the terminals), then check
it with `python3 .claude/skills/multisim-scheme/scripts/blocks.py show NAME` and in all 8 orientations (no «slanted wire»).

## Releasing
`python3 .claude/skills/multisim-scheme/scripts/update.py --release --note "what changed" --zip multisim-scheme.zip`,
commit `version.json` and the zip together. Installed copies in claude.ai update themselves from `main`.

## Graphics
`python3 docs/make_assets.py` regenerates `docs/assets/demo.gif` and `docs/assets/social-preview.png`.
