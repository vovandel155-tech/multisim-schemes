import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Fig. 5.1d — 1/4 SN74S00 (Schottky TTL 2-input NAND), as in the textbook.
# Transistors drawn with «hooks» are Schottky: Q1 (VTN, two emitters) — subcircuit MultiSchottky2 (its sheet comes from
# multi_emitter_shotki.ms14), Q3, Q4, Q5, Q6 — subcircuit SchottkyNPN; Q7 (upper output, no hooks) — a plain npn 2N2222.
# Both subcircuits live in one file (derived base SchottkyMulti2). Darlington pair Q4–Q7 with R7 3.5k to its own ground, as in the textbook;
# R2 500 / R6 250 / Q6 network at the Q5 base; the «R2 — Q6 base» node is tied to the common ground bus — as in the figure.
# Inputs — switches S1, S2 with Schottky diodes D1, D2 to the common bus, output — multimeter XMM1.
S=Scheme('fig5_01d_sn74s00',outdir=GALLERY)
P=S.part
P('Q1','QMS2','B',12,13)                          # B (12,13), bar y=16, E1 (8,18), E2 (10,18), C (15,18)
P('Q3','QS','C',21,14)                            # C (21,14), B (18,18), E (21,22)
P('Q4','QS','C',29,8)                             # C (29,8), B (26,12), E (29,16)
P('Q7','Q','C',37,14)                             # C (37,14), B (34,18), E (37,22)
P('Q5','QS','C',37,28)                            # C (37,28), B (34,32), E (37,36)
P('Q6','QS','C',29,41)                            # C (29,41), B (26,45), E (29,49)
P('R3','R','1',12,2,value='2.8k'); P('R1','R','1',21,2,value='900'); P('R5','R','1',37,1,value='50')
P('R7','R','1',29,20,value='3.5k'); g7=S.gnd(29,27)
P('R2','R','1',21,35,value='500'); P('R6','R','1',29,34,value='250')
P('D1','DS','A',3,36); P('D2','DS','A',7,36)      # cathode up: K (x,30), A (x,36)
vcc=S.vcc(8,0); g=S.gnd(37,53)
x1=S.switch('S1',-4,18,gnd=1); x2=S.switch('S2',-14,24)
y=S.meter('XMM1',42,25)
S.wires([
 # VCC bus
 [vcc,J(12,0)],[J(12,0),('R3','1')],[J(12,0),J(21,0)],[J(21,0),('R1','1')],[J(21,0),(37,0),('R5','1')],
 # inputs: x1 — emitter E1, x2 — emitter E2; Schottky diodes D1, D2 down to the common bus
 [x1,J(3,18)],[J(3,18),('Q1','E1')],[J(3,18),('D1','K')],
 [x2,J(7,24)],[J(7,24),(10,24),('Q1','E2')],[J(7,24),('D2','K')],
 [('R3','2'),('Q1','B')],[('Q1','C'),('Q3','B')],
 # phase splitter Q3: collector — R1 and the base of Q4
 [('R1','2'),J(21,12)],[J(21,12),('Q3','C')],[J(21,12),('Q4','B')],
 # Darlington pair Q4–Q7: collectors to R5, the Q4 emitter — R7 to its own ground and the base of Q7
 [('R5','2'),J(37,8)],[('Q4','C'),J(37,8)],[J(37,8),('Q7','C')],
 [('Q4','E'),J(29,18)],[J(29,18),('R7','1')],[J(29,18),('Q7','B')],[('R7','2'),g7],
 # output: Q7 emitter — Q5 collector — multimeter
 [('Q7','E'),J(37,25)],[J(37,25),('Q5','C')],[J(37,25),y],
 # Q3 emitter: the base of Q5, R6 250 — Q6 collector, R2 500 — the base of Q6 (the node goes to the common bus, as in the textbook)
 [('Q3','E'),J(21,32)],[J(21,32),J(29,32)],[J(21,32),('R2','1')],[J(29,32),('Q5','B')],[J(29,32),('R6','1')],
 [('R6','2'),('Q6','C')],[('R2','2'),J(21,45)],[J(21,45),('Q6','B')],
 # common ground bus
 [('D1','A'),(3,51),J(7,51)],[('D2','A'),J(7,51)],[J(7,51),J(21,51)],[J(21,45),J(21,51)],[J(21,51),J(29,51)],
 [('Q6','E'),J(29,51)],[J(29,51),J(37,51)],[('Q5','E'),J(37,51)],[J(37,51),g],
])
S.build()
