import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Fig. 5.18a — input and output protection of the CMOS CD4xxxA series, with inverter Q1 (p-MOS), Q2 (n-MOS) inside.
# As in the textbook: VDD bus on top, common ground bus at the bottom (the GND symbol under the inverter — a 4-wire junction);
# input: diode pair D1, D2 — resistor R1 — pair D3, D4 — gates; output: pair D5, D6, on the right D7 between VDD and ground
# (its wire crosses the output line without a connection, as in the textbook). All diodes cathode up.
# Substrates tied to sources. R1 = 1k (input protection resistor; no effect on the logic — the gate current is zero).
S=Scheme('fig5_18a_cd4000a_protection',outdir=GALLERY)
P=S.part
# diodes: upper ones — anode on the line (y = 10), cathode to VDD; lower ones — cathode to the line (y = 18), anode to ground
for n,x in (('D1',10),('D3',24),('D5',51)): P(n,'D','A',x,10)
for n,x in (('D2',10),('D4',24),('D6',51),('D7',63)): P(n,'D','A',x,24)
P('R1','R','1',15,14,rot=270,value='1k')
P('Q1','PMOS','S',42,3,rot=180,mirror=True)      # S (42,3), G (39,6), SUB (44,7), D (42,11)
P('Q2','NMOS','D',42,17)                         # D (42,17), G (39,22), SUB (44,21), S (42,25)
vdd=S.vcc(4,0); g=S.gnd(42,31)
x=S.switch('S1',0,14)
y=S.meter('XMM1',70,14)
S.wires([
 # VDD bus
 [vdd,J(10,0)],[J(10,0),('D1','K')],[J(10,0),J(24,0)],[J(24,0),('D3','K')],[J(24,0),J(42,0)],
 [J(42,0),J(51,0)],[J(51,0),('D5','K')],[J(51,0),(63,0),('D7','K')],
 # input: diodes, resistor, gates
 [x,J(10,14)],[J(10,14),('D1','A')],[J(10,14),('D2','K')],[J(10,14),('R1','1')],
 [('R1','2'),J(24,14)],[J(24,14),('D3','A')],[J(24,14),('D4','K')],[J(24,14),J(33,14)],
 [J(33,14),(33,6),('Q1','G')],[J(33,14),(33,22),('Q2','G')],
 # inverter: Q1 source and substrate to VDD, Q2 to ground
 [('Q1','S'),J(42,1)],[('Q1','SUB'),(44,1),J(42,1)],[J(42,1),J(42,0)],
 [('Q2','S'),J(42,27)],[('Q2','SUB'),(44,27),J(42,27)],[J(42,27),J(42,29)],
 # output
 [('Q1','D'),J(42,14)],[J(42,14),('Q2','D')],[J(42,14),J(51,14)],
 [J(51,14),('D5','A')],[J(51,14),('D6','K')],[J(51,14),y],
 # common ground bus
 [('D2','A'),(10,29),J(24,29)],[('D4','A'),J(24,29)],[J(24,29),J(42,29)],[J(42,29),g],
 [J(42,29),J(51,29)],[('D6','A'),J(51,29)],[J(51,29),(63,29),('D7','A')],
])
S.build()
