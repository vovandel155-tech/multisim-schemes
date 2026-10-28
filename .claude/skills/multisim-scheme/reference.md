# The .ms14 format and the generator internals

A reference for changing the core (`scripts/msgen.py`) and for taking Multisim files apart. `SKILL.md` is enough for normal work.

## The .ms14 container
- Header: ASCII `MSMCompressedElectronicsWorkbenchXML` (36 bytes), uint32 — total XML size, uint32 — 0.
- Then chunks: uint32 — unpacked size (≤ 900000), uint32 — compressed size, data.
- The data is PKWARE DCL implode: ASCII literals, 4K dictionary, first bytes `01 06`. The decompressor is a port of `blast.c` (Mark Adler).
- `blast.read_ms(path)` → XML (bytes); `blast.write_ms2(xml, path)` — real compression (`implode_fast`: match search via `bytes.rfind`, no length-2 matches).
- Multisim does **not open** a file made of literals only (`write_ms`).
- Unpacking and compressing again gives a working file (verified on base_5_1a).
- Command line: `python3 scripts/blast.py file.ms14 file.xml` — unpack for study.

## XML
- Attributes may contain line breaks. `msgen.protect()` turns them into `&#10;` before parsing, `serialize()` turns them back. Re-serializing an original gives byte-identical XML. Without this Multisim silently refuses the file.
- Multisim strings: `&ASC<text>` (ASCII) or `&UNI_uc…` (Unicode, hex). Encoded by `msgen.enc`, decoded by `geom.dec`.
- **Graphics:**
  - `CIITSymbolComp` (symbol) → `CIITPinConnectorComp` (pin) → `ConnectList` → wire end point (`CODPinComp` in `ReferencedComponents`) ← `CIITLinkComp` (wire: `Connect1`/`Connect2`, `Points`);
  - a junction dot is a `CODPinComp` in `Objects` with 3 or 4 ends in its `ConnectList`;
  - exactly 1 wire goes to a pin.
- **Electrics:** `CiComponent` / `CiPort` / `CiNode` / `CiModel` / `CiCircuit` (lists `Models`, `Nodes`, `Components`). A `CiComponent` has 53 attribute slots in order. Slot 11 holds `CiaDisplay` (`ShowValues=0` hides the value; this is how `NoValue` works).
- **Grid of 9 units.** Rotations — the `Transformer` matrix of the symbol and of every text.
- **IDs:** integers, unique per file. The generator issues them from 700 000 000 with step 8; GUIDs come from a random generator seeded by the file name.

## What `finalize` cleans up and writes (verified in Multisim)
- Removes the preview (`CMsPreviewExtension`), the net and RefDes lists (`CODProjectExtension`, `CMultisimExtension`), the traces of the sample's hierarchical blocks (`CSheetComponentMSM` groups without instances, their `ViewState`, tree items `(HB…)`). Multisim recreates all of this itself.
- **Does not rename the project** — that breaks the file (`rename=False`).
- **Sheet** (`set_sheet`): in `CircPrefs` — `Sheet Size`=Custom, `Sheet Width/Height In Inch`, `Sheet Width/Height` (96 px per inch); `CIITDiagram` gets `TBSize`=Custom.
- **TMAX** (`set_tmax`): in the sheet `SimState` (`CIITDiagram`) the interactive simulation block is the one with `TSTOP:double{1e+30}`. There `TMAX:string{calculate}` is replaced by `TMAX:double{1e-05}`.
- **Subcircuit net names** (`net_names`), see below.

## Switch (SPDT, «Key = Space»)
- `CIITAnimationSymbolComp`: the animation frames live in `AnimationLayers/…/CIITAnimationLayerComp`; `place()` moves and rotates them together with the symbol.
- `CurIndex` — the current position: 1 — common pin 2 connected to pin 3, 0 — to pin 1.
- `switch()` connects pin 1 to VCC and pin 3 to ground, so right after opening the file the input is 0.

## Subcircuits (Schottky transistor, multi-emitter)
- **Subcircuit definition** — a second project sheet: `SheetContainer` → `DesignSheet Title=<name>` → its own `CIITHierDoc` with elements and `CIITHierConnector` connectors.
- **Instance on the main sheet** — `CIITMacroComponent` (inside `HierBlock/CHierBlock FileName='<name>' Subcircuit='1'`) plus a `CiInstComponent` with ports named as the connectors. SPICE: `x%p %tIO1 %tIO2 …`.
- **Instance group.** Every instance has its own `CSheetComponentMSM` group (`SheetComponentObjectID`) and a tree item `<name>(Q1)`. `Builder._sheetcomp` creates them.
- **The symbol** is stored separately in every instance. `SchottkyLib` draws an npn with «hooks» at the base ends and puts the pins at the npn places. `MultiEmitterLib` draws a base bar with 4 emitters. Both give the macro element an identity matrix, otherwise the labels are not recalculated.
- **Net names.** Multisim names a net at a subcircuit pin by the connector: «Q1_l_C». When pins of two instances share a net, «Resolve Net Name Conflict» appears on opening. The answer is stored in `CDesignNetContainer/NetLabels`:
  - an `Item` with `TreeInstanceProxy` = `{sheet GUID}/{main SheetID}/{instance group GUID}/{subcircuit SheetID}/`;
  - inside, a `CSchDesignNetLabel`: `ID` = Guid of the connector label, `Modifier=16`, `LastOverruleName` = `LastNetName` = the chosen name, `Priority=1` for the overridden ones.

  `net_names()` writes this in advance.
- **One instance kind per scheme** unless `COMBINED` has a common base: the file base is the sample of that subcircuit.

## Element models from the samples
- **npn** 2N2222, **diode** 1BH62, **VCC** 5 V, **ground**, **switch**, **multimeter** — from `base_5_1a`; **Schottky** 10BQ015 — from `base_5_1g`.
- **pnp** 2N2907A — from `sample_pnp` (a Multisim model). The value is hidden with `NoValue`: slot 11 is copied from the npn.
- **MOS** — `sample_mos`: MOS_N_4T, MOS_N_4T_DEP, MOS_P_4T, MOS_P_4T_DEP (virtual, 4 pins, L = W = 100u).
  - Models without parameters: in SPICE this is level 1 with VTO = 0, KP = 2e-5. Enough for 0/5 V logic.
  - The on-resistance is around 10 kOhm, so protection diode leakage gives 4.9 V instead of 5.0 V.
- **Samples:** Multisim saves every element whole (symbol, model, database data), so a new type is easiest to take from a file saved by Multisim itself.

## The ngspice check (`spice.py`)
- The netlist comes from the finished XML: elements, `CiNode`, `.MODEL` texts, subcircuits → `.subckt`.
- Switches S* are replaced by 1 mOhm to VCC or to ground; all combinations are enumerated.
- The output is pin 1 of multimeter XMM1; the multimeter is modelled as 1 GOhm.
- Agreement with Multisim is verified: for fig. 5.4 ngspice gives 0.530 / 4.834 V, the Multisim multimeter shows 529.947 mV.

## Elements without a sample (`SpiceLib`)
- Multisim simulates an element by the SPICE template from its `CiComponent` (`CiaSpiceTmpltExprt`, a copy is in the string list):
  resistor `r%p %t1 %t2 #1 …`, npn `q%p %tC %tB %tE %m`, VCC `VCC%p %tVCC 0 dc #0`; `#k` — the k-th item of the
  `parameters` of the first `CiaParamList`, `%m` — the model name (`CiModel`, text `.MODEL <name>__<family>__1 …`).
  The SPDT switch describes a whole subcircuit in its template (`x%p … Switch%p` + `.subckt Switch%p … .ends` with a `.MODEL` inside) —
  TIP121/TIP127 are made the same way.
- `SpiceLib` clones a base and changes: the template (marked `* msgen` on the first line), the model or its absence
  (then the `Model` attribute is removed), the family/type/RefDes prefix strings, value display (`CiaDisplay ShowValues`),
  the value unit («Ω» → «F», «V 1kHz»), the body graphics (the resistor `CODRectComp` → segments/circle/polyline from
  npn stubs with the body matrix).
- Names as in the Multisim database (CAPACITOR / CAPACITOR_VIRTUAL, SIGNAL_VOLTAGE_SOURCES / AC_VOLTAGE, BJT_NPN,
  DARLINGTON_NPN): if Multisim matches the element to the database by name, it finds the real one; otherwise what is written
  in the file works. The properties dialog of such elements comes from the base (a capacitor has a «Resistance» field).
- The element type for Multisim is the code on the first line of the second `CiaCollString` (`29` resistor, `31` capacitor, `26` VCC,
  `12` ground, `46` transistor/diode with a model, `40` multimeter, `66` switch). Multisim builds the value label and the
  properties dialog from it: a capacitor on a resistor base was shown in ohms, so the capacitor is now
  the real one from base_5_1a, and the sine source (resistor base) has its value hidden.
- Verified in Multisim: a file with such elements opens, but a bridge amplifier built on them did not work — use catalog parts instead of synthesis.

## A subcircuit from another file (`transplant_sheet`)
- A subcircuit sheet and the main sheet of any file are built the same way: `CIITHierDoc` → `Components/CODComposite` (graphics) and
  `Elements` (CiComponent, CiPort, CiNode, CiCircuit, CiModel); the pins are `CIITHierConnector` connectors. An instance on the
  main sheet is linked to the sheet by name only (`CHierBlock FileName` = sheet `Title`); sheet IDs do not appear outside.
- `transplant_sheet(D, 'MultiNPN4', src, rename, new_title)` replaces `Components` and `Elements` of the sample sheet with copies of
  the main sheet of `src` with new IDs (own range from 640 000 000), renames the connectors (the Cyrillic block pin names → B/C/E1/E2) and
  the subcircuit in all strings of the file. The derived base is written to `.msgen/<name>.xml` and given to Builder as a sample.
- This is how `QM2` (from `Multi_emitter_npn.ms14`) and `QMS2` (from `multi_emitter_shotki.ms14`) are made for figs. 5.1a–d.
- A second subcircuit kind in the same file — `copy_sheet(D, 'MultiNPN4', 'SchottkyNPN')`: a copy of the sheet (new SheetID, ObjectID),
  of the instance group `CSheetComponentMSM`, of the `UniqueSheetGroups/SheetGroupInfo` entries, of the tree item «name(SC1)» and of the instance
  on the main sheet (Builder finds the group by it); then `transplant_sheet` fills the copy with a sheet from another sample
  (`sheet_parts`). Fig. 5.1d is built this way (SchottkyNPN + MultiSchottky2).

## Part registry (`harvest.py`, `registry.py`)
- Where the database data sits in `CiComponent` (slots of the `Attributes` list): 4 — `CiaCollString` [family, part name, family,
  model/virtual name, …] (`BJT_NPN`, `2N2222`; `RESISTOR`, `RESISTOR_VIRTUAL`); 5 — [type code, «Product», family, instrument
  kind (`MULMETER`), RefDes prefix `Q%d`, SPICE template, package, …]; value — a pair of adjacent `CiaCString` «4k» / «4kΩ»
  (slots 41, 42), giving the value and the unit on the sheet; index 14 of slot 4 — the database group. The template is `CiaSpiceTmpltExprt`,
  the model — `CiModel` by the `Model` attribute (`.MODEL` or `.SUBCKT`). The Multisim version — `<creator versionMajor/Minor/Patch>` at the start of the XML.
- A file was saved by Multisim itself when it has the `CMsPreviewExtension` preview (`finalize` removes it).
- The donor set is a greedy cover: Multisim-saved files first, then by the number of parts not yet covered, on a tie —
  the smaller file. A part key is `family/name`; the catalog stores the RefDes of the part in the donor, pins, value, template, model.
- In the generator a registry part is an ordinary sample: `(Doc(donor), RefDes, value, unit)`, like a `KINDS` line; cloning
  from another file into the base_5_1a base is verified (pnp, MOS, Schottky — from their own samples).
- Check: fig. 5.17b built with `MOS_P_4T`/`MOS_N_4T` from the registry instead of `PMOS`/`NMOS` matched the earlier file byte for byte.

## Instruments, probes, donors via COM
- **Instruments** (oscilloscope, generator, Bode…): an ordinary element (`CiComponent`, prefix `X…`) + a settings entry in the
  main sheet `InstrumentsData`, `CompLongName` = «XSC1#1/<sheet name>:» (`instruments`, `scheme.INST`).
- **Probes:** the symbol `CIITProbeExtComponent` (tip — `Transformer-M20/M21`, exactly on a wire; `Direction` 3 —
  horizontal wire, 5 — vertical, 0 — element pin), `CiProbeExtComp` in the net's `ProbeExts`, an
  `InstrumentsData` entry by `FileDataPackageID`. The kind is the tail of `NI_EWB_DATABASEDATA_EXT` (1 V, 2 I, 3 VI, 4 P, 5 D, 6 Ref),
  differential — V with a reference to the name of the reference probe. The probe data contains its own `Elements` — find the sheet
  electrics by `CiCircuit` (`sheet_elements`).
- **COM (Automation API, 32-bit — `SysWOW64\\cscript.exe`):** `MultisimInterface.MultisimApp` → `Connect`,
  `OpenFile(path)` (closes the previous one), `circuit.SaveAs(path)` (re-saves .ms8–.ms13 as .ms14),
  `circuit.ReplaceComponent(RefDes, Section, Database, Group, Family, Component, Model)` — Database 0 = Master
  Database; errors are in `LastErrorMessage`; multi-section parts need a section («A»); the new part gets its own RefDes.
  New parts or wires cannot be placed through COM — hence the placeholder template.
- **Multisim files with NUL** inside binary attribute data — `protect` drops it (otherwise a ParseError).
- **Compact catalog:** `harvest.write` cuts the part block out of the donor (`msgen.pack_part`: `MsgenPart` → `Sym`, `Ci`,
  `Ports`, `Model`, `PortModels`, `Inst`) and writes all of them into one file `parts.bin` (deflate blocks back to back) with the index `parts.idx` (JSON: name →
  [offset, length]); not zip/gzip — the claude.ai uploader accepts at most 200 files and no archives inside the archive; `msgen.PartPack.bundle()` returns the same as `Doc.bundle()` of the donor. `--keep` leaves the existing blocks
  as they are and adds only new keys; a catalog of the old layout (whole donors) is converted automatically. Verified: 5 schemes from
  blocks and from whole donors matched byte for byte; the catalog went from 14 MB to 1.1 MB.
