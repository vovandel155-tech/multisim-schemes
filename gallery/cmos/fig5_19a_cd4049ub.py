import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Fig. 5.19a — 1/6 CD4049UB (unbuffered inverter): input diodes to ground only (D1 — R1 — D2), then the gates
# of inverter Q1 (p-MOS), Q2 (n-MOS); on the right D3 between VDD and ground (its wire crosses the output line without
# a connection, as in the textbook). VDD bus on top, common ground bus at the bottom (the GND symbol under the inverter — a 4-wire junction).
# Diodes cathode up. Substrates tied to sources. R1 = 1k (no value in the textbook; the gate current is zero).
S=Scheme('fig5_19a_cd4049ub',outdir=GALLERY)
P=S.part
for n,x in (('D1',10),('D2',24),('D3',48)): P(n,'D','A',x,24)    # cathode (x,18), anode (x,24)
P('R1','R','1',15,14,rot=270,value='1k')
P('Q1','PMOS','S',42,3,rot=180,mirror=True)      # S (42,3), G (39,6), SUB (44,7), D (42,11)
P('Q2','NMOS','D',42,17)                         # D (42,17), G (39,22), SUB (44,21), S (42,25)
vdd=S.vcc(34,0); g=S.gnd(42,31)
x=S.switch('S1',0,14)
y=S.meter('XMM1',54,14)
S.wires([
 # VDD bus: Q1 source and substrate, D3
 [vdd,J(42,0)],[J(42,0),(48,0),('D3','K')],
 [('Q1','S'),J(42,1)],[('Q1','SUB'),(44,1),J(42,1)],[J(42,1),J(42,0)],
 # input: D1 — R1 — D2 — gates
 [x,J(10,14)],[J(10,14),('D1','K')],[J(10,14),('R1','1')],
 [('R1','2'),J(24,14)],[J(24,14),('D2','K')],[J(24,14),J(33,14)],
 [J(33,14),(33,6),('Q1','G')],[J(33,14),(33,22),('Q2','G')],
 # output
 [('Q1','D'),J(42,14)],[J(42,14),('Q2','D')],[J(42,14),y],
 # Q2 source and substrate, common ground bus
 [('Q2','S'),J(42,27)],[('Q2','SUB'),(44,27),J(42,27)],[J(42,27),J(42,29)],
 [('D1','A'),(10,29),J(24,29)],[('D2','A'),J(24,29)],[J(24,29),J(42,29)],[J(42,29),g],
 [J(42,29),(48,29),('D3','A')],
])
S.build()
