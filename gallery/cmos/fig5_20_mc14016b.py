import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Fig. 5.20 — 1/4 MC14016B: bidirectional switch DI (In/Out) ↔ DO (Out/In), control OE.
# OE goes through R1 and protection diodes D1 (to VDD), D2 (to ground) to inverter Q1, Q2 (output N1 = NOT OE).
# The switch — p-MOS Q3 (gate N1, substrate VDD) and n-MOS Q5 (gate OE — the wire goes around the scheme at the bottom, as in the textbook).
# Q5 substrate (node X): with OE = 1 it connects to DO through p-MOS Q4 (gate N1), with OE = 0 to ground through n-MOS Q6.
# As in the textbook: VDD bus on top, common ground bus with the GND symbol under the inverter, the DO line at the bottom, wires cross
# without connections. Input DI — switch S1, OE — switch S2, DO — multimeter XMM1: DO = DI with OE = 1, otherwise the switch is open.
# R1 = 1k (no value in the textbook; the gate current is zero).
S=Scheme('fig5_20_mc14016b',outdir=GALLERY)
P=S.part
P('R1','R','1',-6,33,rot=270,value='1k')
P('D1','D','A',10,29); P('D2','D','A',10,43)                      # D1: K (10,23); D2: K (10,37)
P('Q1','PMOS','S',23,3,rot=180,mirror=True)      # S (23,3), G (20,6), SUB (25,7), D (23,11)
P('Q2','NMOS','D',23,28)                         # D (23,28), G (20,33), SUB (25,32), S (23,36)
P('Q3','PMOS','D',32,20)                         # D (32,20), G (29,25), SUB (34,24), S (32,28)
P('Q4','PMOS','D',44,29)                         # D (44,29), G (41,34), SUB (46,33), S (44,37)
P('Q6','NMOS','D',55,28)                         # D (55,28), G (52,33), SUB (57,32), S (55,36)
P('Q5','NMOS','D',62,20,mirror=True)             # D (62,20), G (65,25), SUB (60,24), S (62,28)
vdd=S.vcc(6,0); g=S.gnd(23,45)
di=S.switch('S1',-14,16)
oe=S.switch('S2',-8,33)
do=S.meter('XMM1',72,47)
S.wires([
 # VDD bus: D1, Q1 source and substrate, Q3, Q4 substrates
 [vdd,J(10,0)],[J(10,0),('D1','K')],[J(10,0),J(23,0)],[J(23,0),J(35,0)],
 [('Q1','S'),J(23,1)],[('Q1','SUB'),(25,1),J(23,1)],[J(23,1),J(23,0)],
 [('Q3','SUB'),(35,24),J(35,0)],[J(35,0),(47,0),(47,33),('Q4','SUB')],
 # OE: R1, diodes, inverter gates; the loop at the bottom — to the Q5 gate
 [oe,('R1','1')],[('R1','2'),J(3,33)],[J(3,33),J(10,33)],[J(10,33),('D1','A')],[J(10,33),('D2','K')],
 [J(10,33),J(16,33)],[J(16,33),(16,6),('Q1','G')],[J(16,33),('Q2','G')],
 [J(3,33),(3,51),(67,51),(67,25),('Q5','G')],
 # inverter: output N1 — Q3 gate and the Q4, Q6 gate line
 [('Q1','D'),J(23,25)],[J(23,25),('Q2','D')],[J(23,25),J(27,25)],[J(27,25),('Q3','G')],
 [J(27,25),(27,40),J(39,40)],[J(39,40),(39,34),('Q4','G')],[J(39,40),(50,40),(50,33),('Q6','G')],
 # DI: to the Q3 and Q5 drains
 [di,(39,16),J(39,20)],[('Q3','D'),J(39,20)],[J(39,20),('Q5','D')],
 # node X — substrate of Q5, Q4, Q6
 [('Q5','SUB'),J(55,24)],[J(55,24),(44,24),('Q4','D')],[J(55,24),('Q6','D')],
 # DO: sources of Q3, Q4, Q5 — multimeter
 [('Q3','S'),(32,47),J(44,47)],[('Q4','S'),J(44,47)],[J(44,47),J(62,47)],[('Q5','S'),J(62,47)],[J(62,47),do],
 # Q2, Q6 source and substrate; common ground bus
 [('Q2','S'),J(23,38)],[('Q2','SUB'),(25,38),J(23,38)],[J(23,38),J(23,43)],
 [('Q6','S'),J(55,38)],[('Q6','SUB'),(57,38),J(55,38)],
 [('D2','A'),J(23,43)],[J(23,43),g],[J(23,43),(55,43),J(55,38)],
])
S.build()
