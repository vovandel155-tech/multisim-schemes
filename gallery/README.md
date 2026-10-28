# Gallery

Every circuit here is a short Python script next to the `.ms14` file it produces. All of them were opened and run in
NI Multisim 14.3: no dialogs on opening, readings equal to the ngspice check printed by `build()`.

Rebuild any of them from the repository root, e.g. `python3 gallery/ttl/fig5_04_sn74ls00.py` — the file is written
next to the script, the build is deterministic.

Inputs are switches to VCC/ground (press the key shown on the switch), the output is multimeter XMM1.

## TTL gates (layout and wiring as in the textbook figures)

| Circuit | Function | Preview |
|---|---|---|
| [Fig. 5.1a — SN7400](ttl/fig5_01a_sn7400.py) · [.ms14](ttl/fig5_01a_sn7400.ms14) | NAND, multi-emitter input | <img src="images/fig5_01a_sn7400.png" width="260"> |
| [Fig. 5.1b — SN74L00](ttl/fig5_01b_sn74l00.py) · [.ms14](ttl/fig5_01b_sn74l00.ms14) | NAND, low power | <img src="images/fig5_01b_sn74l00.png" width="260"> |
| [Fig. 5.1c — SN74H00](ttl/fig5_01c_sn74h00.py) · [.ms14](ttl/fig5_01c_sn74h00.ms14) | NAND, high speed, Darlington output | <img src="images/fig5_01c_sn74h00.png" width="260"> |
| [Fig. 5.1d — SN74S00](ttl/fig5_01d_sn74s00.py) · [.ms14](ttl/fig5_01d_sn74s00.ms14) | NAND, Schottky TTL | <img src="images/fig5_01d_sn74s00.png" width="260"> |
| [Fig. 5.4 — SN74LS00](ttl/fig5_04_sn74ls00.py) · [.ms14](ttl/fig5_04_sn74ls00.ms14) | NAND, low-power Schottky | <img src="images/fig5_04_sn74ls00.png" width="260"> |
| [Fig. 5.5 — SN74ALS00](ttl/fig5_05_sn74als00.py) · [.ms14](ttl/fig5_05_sn74als00.ms14) | NAND, pnp inputs | <img src="images/fig5_05_sn74als00.png" width="260"> |
| [Fig. 5.14 — K155LR4](ttl/fig5_14_k155lr4.py) · [.ms14](ttl/fig5_14_k155lr4.ms14) | AND-OR-INVERT, 4-emitter transistors | <img src="images/fig5_14_k155lr4.png" width="260"> |

## CMOS gates

| Circuit | Function | Preview |
|---|---|---|
| [Fig. 5.17b — CMOS inverter](cmos/fig5_17b_cmos_inverter.py) · [.ms14](cmos/fig5_17b_cmos_inverter.ms14) | NOT | <img src="images/fig5_17b_cmos_inverter.png" width="260"> |
| [Fig. 5.17c — transmission gate](cmos/fig5_17c_transmission_gate.py) · [.ms14](cmos/fig5_17c_transmission_gate.ms14) | analog switch | <img src="images/fig5_17c_transmission_gate.png" width="260"> |
| [Fig. 5.18a — CD4xxxA protection](cmos/fig5_18a_cd4000a_protection.py) · [.ms14](cmos/fig5_18a_cd4000a_protection.ms14) | NOT with input/output diodes | <img src="images/fig5_18a_cd4000a_protection.png" width="260"> |
| [Fig. 5.18b — CD4xxxB protection](cmos/fig5_18b_cd4000b_protection.py) · [.ms14](cmos/fig5_18b_cd4000b_protection.ms14) | NOT with input/output diodes | <img src="images/fig5_18b_cd4000b_protection.png" width="260"> |
| [Fig. 5.19a — CD4049UB](cmos/fig5_19a_cd4049ub.py) · [.ms14](cmos/fig5_19a_cd4049ub.ms14) | NOT, unbuffered | <img src="images/fig5_19a_cd4049ub.png" width="260"> |
| [Fig. 5.19b — CD4050B](cmos/fig5_19b_cd4050b.py) · [.ms14](cmos/fig5_19b_cd4050b.ms14) | buffer | <img src="images/fig5_19b_cd4050b.png" width="260"> |
| [Fig. 5.20 — MC14016B](cmos/fig5_20_mc14016b.py) · [.ms14](cmos/fig5_20_mc14016b.ms14) | bilateral switch | <img src="images/fig5_20_mc14016b.png" width="260"> |
| [Fig. 5.21 — CD4001B](cmos/fig5_21_cd4001b.py) · [.ms14](cmos/fig5_21_cd4001b.ms14) | NOR, buffered | <img src="images/fig5_21_cd4001b.png" width="260"> |
| [Fig. 5.22a — MC14011UB](cmos/fig5_22a_mc14011ub.py) · [.ms14](cmos/fig5_22a_mc14011ub.ms14) | NAND, unbuffered | <img src="images/fig5_22a_mc14011ub.png" width="260"> |
| [Fig. 5.22b — MC14011B](cmos/fig5_22b_mc14011b.py) · [.ms14](cmos/fig5_22b_mc14011b.ms14) | NAND, buffered | <img src="images/fig5_22b_mc14011b.png" width="260"> |
| [Fig. 5.23 — CD4011B](cmos/fig5_23_cd4011b.py) · [.ms14](cmos/fig5_23_cd4011b.ms14) | NAND, buffered (NOR core) | <img src="images/fig5_23_cd4011b.png" width="260"> |

## Demos

| Circuit | What it shows | Preview |
|---|---|---|
| [Diode shaper](demos/diode_shaper.py) · [.ms14](demos/diode_shaper.ms14) | a circuit rebuilt from a screenshot; sine source, ideal op-amp | <img src="images/diode_shaper.png" width="260"> |
| [Op-amp and LED](demos/catalog_opamp_led.py) · [.ms14](demos/catalog_opamp_led.ms14) | catalog parts: 741, 2N3904, blue LED, VEE | <img src="images/catalog_opamp_led.png" width="260"> |
| [Probes](demos/probes.py) · [.ms14](demos/probes.ms14) | all probe kinds: V, I, VI, P, digital, differential | <img src="images/probes.png" width="260"> |
| [Instruments](demos/instruments_rc.py) · [.ms14](demos/instruments_rc.ms14) | function generator, oscilloscope, Bode plotter, counter | <img src="images/instruments_rc.png" width="260"> |
| [TIP121G / TIP127G](demos/darlington_tip121_tip127.py) · [.ms14](demos/darlington_tip121_tip127.ms14) | parts extracted from Multisim with `get_parts.bat` | <img src="images/darlington_tip121_tip127.png" width="260"> |
| [FZT1049A switch](demos/fzt1049a_switch.py) · [.ms14](demos/fzt1049a_switch.ms14) | a part obtained from a claude.ai chat | <img src="images/fzt1049a_switch.png" width="260"> |
| [Blocks: AND + LED](demos/blocks_and_led.py) · [.ms14](demos/blocks_and_led.ms14) | a circuit made of library blocks | <img src="images/blocks_and_led.png" width="260"> |
| [Sources](demos/catalog_sources.py) · [.ms14](demos/catalog_sources.ms14) | AC source, interactive DC source turned upside down | <img src="images/catalog_sources.png" width="260"> |

## Experimental

[`experimental/`](experimental/) — scripts kept for reference, **not working in Multisim yet**: a bridge (BTL) power
amplifier and a test of synthesized elements (`SpiceLib`). Use catalog parts for new work.
