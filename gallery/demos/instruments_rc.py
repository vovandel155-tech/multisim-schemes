import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Catalog instruments (from a file saved by Multisim → samples/ni/Izm.ms14): RC low-pass
# filter R1 1k / C1 1u (cutoff ≈ 159 Hz) driven by function generator XFG1; oscilloscope XSC1 — A input, B output;
# Bode plotter XBP1 — IN input, OUT output; frequency counter XFC1 — output. Instrument pins (by the labels on the symbols):
# XFG1 1 «+», 2 COM, 3 «−»; XSC1 1/4 — A+/A−, 2/5 — B+/B−, 3/6 — external trigger; XBP1 1/2 IN+/IN−, 3/4 OUT+/OUT−.
S=Scheme('instruments_rc',outdir=GALLERY)
P=S.part
P('XFG1','FGEN','1',2,6)                          # + (2,6), COM (4,6), − (6,6)
P('XSC1','SCOPE','1',24,6)                        # A+ (24,6), A− (25,6), B+ (28,6), B− (29,6)
P('XBP1','BODE','1',42,6)                         # IN+ (42,6), IN− (44,6), OUT+ (47,6), OUT− (49,6)
P('XFC1','FREQCOUNTER','1',60,6)
P('R1','R','1',12,14,rot=270,value='1k'); P('C1','C','1',20,16,value='1u')
g1=S.gnd(4,9); g2=S.gnd(20,23); g3=S.gnd(44,9); g4=S.gnd(49,9)
S.wires([
 [('XFG1','1'),(2,14),J(10,14)],[('XFG1','2'),g1],
 [J(10,14),('R1','1')],[J(10,14),(10,10),J(24,10)],[J(24,10),J(24,8)],[J(24,8),('XSC1','1')],
 [('R1','2'),J(20,14)],[J(20,14),('C1','1')],[('C1','2'),g2],
 [J(20,14),(20,12),J(28,12)],[J(28,12),('XSC1','2')],
 [J(24,8),(42,8),('XBP1','1')],[('XBP1','2'),g3],
 [J(28,12),J(47,12)],[J(47,12),('XBP1','3')],[('XBP1','4'),g4],[J(47,12),(60,12),('XFC1','1')],
])
S.build()
