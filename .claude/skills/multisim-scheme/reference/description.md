# Circuit description (Description Box)

Read it when the user wants a description (Tools → Description Box Editor) in the file.

## Contents
- Circuit description (Description Box) — `scripts/describe.py`

## Circuit description (Description Box) — `scripts/describe.py`
Tools → Description Box Editor: a formatted text saved in the file (in the Design Toolbox it is the sheet
«<title>-Description»). Write it in the user's language.
- `S.description(markup)` for a new circuit; `describe.rewrite('in.ms14', 'out.ms14', markup)` replaces the description
  of an existing file, `append=True` adds to its end (the old text and pictures stay).
- Markup (as in Markdown): consecutive lines make one paragraph, a blank line starts a new one; `# Heading` (bold),
  `## Subheading` (bold italic), `###`/`####` (italic), `- bullet`, `| table | rows |` (a `|---|---|` row after the first makes it a bold
  header), `**bold**`, `*italic*`, `R_{н}` subscript, `10^{-3}` superscript,
  `![Рисунок 1 — Схема](file.png){width=12}` — a centered PNG/JPEG picture with its caption, width in cm (default:
  the text width at most). Body text: Times New Roman 14, first-line indent 1.25 cm, justified (Russian coursework style).
- **Subscripts and superscripts need braces:** `K_{U}`, `U_{вх m}`, `10^{-3}`. `K_U` stays as text (names such as
  `inoise_total` must survive), and `check.py` reports it.
- **The description describes this file:** the parts, values and supply that are in it, numbers from `spice.run` on it;
  nothing from an earlier variant or from another netlist.
- **Before putting pictures in, ask the user** which ones they want: graphs computed by the skill in ngspice (plotted
  with matplotlib — ready at once, but they are not Multisim's own windows) or their own screenshots from Multisim
  (Grapher, the circuit — what a teacher expects to see; ask them to send the files). Mixing is fine. The circuit
  itself can always come from the preview (`.msgen/preview/<name>.png` after `build()`).
- `analyses.markup('file.ms14')` — an English draft of a section about the Batched list (a table: Grapher page,
  analysis and its settings, variables); translate it to the user's language, then put it with `rewrite(..., append=True)`.
