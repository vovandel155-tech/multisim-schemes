# Skill evaluations

Scenarios taken from real failures of a weaker model (Claude Haiku in claude.ai). Run them after every change of the
skill, with the model that is most likely to skip instructions, and record what it missed.

How to run one:
1. Start a new chat in claude.ai with the `multisim-scheme` skill enabled (it updates itself from `main`).
2. Send the `query` (in any language) and attach the `files`, if any; answer its questions as the scenario says.
3. Score every line of `expected_behavior` as done / missed; run `python3 .claude/skills/multisim-scheme/scripts/check.py`
   on every file the model gave and open it in Multisim 14.3.
4. A missed line becomes a fix of the skill: a checklist step in `SKILL.md`, a rule in `reference/`, or a test in
   `check.py` — then run the scenario again.

| Scenario | What it caught before |
|---|---|
| `bridge_amp.json` | the default 5 V supply under a 19.5 V design, values from a hand-written netlist, `###` in the description, overlaps called cosmetic |
| `audio_amp_tl072.json` | `get_parts` not offered, bias diodes turned around, gain in dB missing from the analyses, `K_U`, a «UinVpk» label |
| `cmos_nor_gate.json` | layout rules: one ground bus, input switches, multimeter, the truth table |
