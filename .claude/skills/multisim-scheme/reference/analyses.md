# Analyses (Batched) and expected values

Read it when the user wants analyses in the file or numbers to compare with Multisim.

## Contents
- Analyses (Batched) — `scripts/analyses.py`

## Analyses (Batched) — `scripts/analyses.py`
**Before giving the file away:** every quantity the user asked for is an output variable of some analysis (a gain in
dB — `db(V(out)/V(in))`; a current through a resistor — `(V(a)-V(b))/R`, not `V(a)/R`); every net and source named in
a variable exists — `check.py` reports a variable that names a missing net or source as an ERROR.
Simulate → Analyses and Simulation → **Batched**: a list of analyses saved in the file; the user presses **Run** and
gets one Grapher page per analysis (its title is the page name). The skill writes the list; Batched becomes the
active analysis. Variables — as in the Output tab: `'V(2)'`, `'V(outl)-V(outr)'`, `'I(V1)'`, `'db(V(4)/V(2))'`,
`'(V(a)-V(b))^2/8'`; nets are the net names (the numbers the `build()` report prints, or the names in the file).
- `S.op(vars, title=)` — DC Operating Point.
- `S.phasor(vars, freq=1000, fmt='magph'|'reim', title=)` — Single Frequency AC. Sources take their
  «AC analysis magnitude» (1 V for `AC_VOLTAGE`), not the amplitude on the label.
- `S.ac(vars, fstart=1, fstop=10e6, points=100, sweep='dec'|'oct'|'lin', vscale='db'|'linear'|'log'|'octave', title=)` — AC Sweep.
- `S.tran(vars, tstop, tstart=0, tmax=None, ic='auto_ic'|'dcop'|'zero', title=)` — Transient.
- `S.fourier(vars, freq=1000, harmonics=9, tstop=None, tmax=None, ic=None, vscale=0|1, bars=None, normalized=None, title=)` —
  Fourier (table of harmonics and THD). `vscale=1` — Logarithmic: harmonics 100× smaller stay visible; keep the line
  graph there (`bars=True` on a log scale makes every bar look the same).
- `S.noise('VIN', output, ref='0', fstart=20, fstop=20e3, points=100, spectrum=False, title=)` — Noise referred to source
  `VIN`, output between nets `output` and `ref`; `spectrum=False` — inoise_total/onoise_total, `True` — spectral density.
- `S.param('Uin', 0.2)` — a circuit parameter (Tools → Circuit parameters); a part uses it through
  `subst={'.2':'Uin','UinVpk':'Uin'}` (value and label). `S.psweep(vars, 'Uin', [0.1, 0.2, 0.5], tstart=, tstop=, tmax=, ic=, title=)` —
  Parameter Sweep over it, a Transient for every value, all traces on one plot.
- Every method takes `max_points=` (Analysis options → Maximum number of points; raise to 1000000 for long transients
  with a small step).
- **An existing file** (the user's own circuit): `B = analyses.Batch()`, the same methods (`B.op(...)`, `B.noise(...)`,
  `B.psweep(..., current=value)`), then `analyses.rewrite('in.ms14', 'out.ms14', B)` — replaces the Batched list and
  leaves the circuit untouched. `python3 scripts/analyses.py file.ms14` lists the Batched analyses of any file.
- **Expected values — only from the built file:** `spice.run('out.ms14', 'op; print v(4) i(vv1); ac lin 1 1k 1k; …')`
  (or `python3 scripts/spice.py out.ms14 "op; print all"`) runs ngspice on the netlist of the file itself: its real VCC,
  parts, models and circuit parameters (`params={'Uin': 0.5}` overrides one). **Never** compute the numbers for the user
  from a netlist written by hand — a model once reported 19.5 V results for a file that had the default 5 V supply.
  Commands: `op`, `ac lin 1 1k 1k`, `ac dec 100 1 10meg`, `tran 1u 50m 0 1u` + `fourier 1k v(a,b)`,
  `noise v(a,b) vvin dec 100 20 20k` (`print inoise_total onoise_total` after `setplot noise2`). The user compares them
  with Grapher; the same numbers go into the description.
- **Supply current in the results** needs a source with a branch: `DC_POWER` (`I(V1)`), not the `VCC` symbol.
- **Steps:** Fourier — `tmax` ≤ 1/(100·harmonics·f) (1 us for 1 kHz and 9 harmonics; smaller for THD below 0.1 %);
  AC Sweep — 100 points per decade, so the −3 dB frequencies come out accurate.
- Verified in Multisim 14.3: all of the above (`gallery/demos/batched_op`, `batched_phasor`, `batched_all`, and a real
  coursework circuit rewritten by `rewrite`).
