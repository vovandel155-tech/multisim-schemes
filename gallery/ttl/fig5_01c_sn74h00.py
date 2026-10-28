import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Fig. 5.1c — 1/4 SN74H00 (high-speed TTL 2-input NAND), as in the textbook (R5 = 58 Ohm).
# Multi-emitter Q1 — subcircuit MultiNPN2 (its sheet comes from Multi_emitter_npn.ms14), symbol as in the textbook.
# Q3 — phase splitter, Q4–Q6 — upper output (Darlington pair, R6 4k to ground), Q5 — lower output;
# D1, D2 — input clamps; common ground bus at the bottom. The Q3 emitter line to the Q5 base crosses the R6 line without a connection.
S=Scheme('fig5_01c_sn74h00',outdir=GALLERY)
P=S.part
P('Q1','QM2','B',14,15)                           # B (14,15), bar y=18, E1 (10,20), E2 (12,20), C (17,20)
P('Q3','Q','C',23,16)                             # C (23,16), B (20,20), E (23,24)
P('Q4','Q','C',31,10)                             # C (31,10), B (28,14), E (31,18)
P('Q6','Q','C',39,16)                             # C (39,16), B (36,20), E (39,24)
P('Q5','Q','C',39,28)                             # C (39,28), B (36,32), E (39,36)
P('R3','R','1',14,2,value='2.8k'); P('R1','R','1',23,2,value='760'); P('R5','R','1',39,2,value='58')
P('R6','R','1',31,34,value='4k'); P('R2','R','1',23,35,value='470')
P('D1','D','A',4,34); P('D2','D','A',8,34)        # cathode up: K (x,28), A (x,34)
vcc=S.vcc(9,0); g=S.gnd(39,43)
x1=S.switch('S1',-4,20,gnd=1); x2=S.switch('S2',-14,26)
y=S.meter('XMM1',45,26)
S.wires([
 # VCC bus
 [vcc,J(14,0)],[J(14,0),('R3','1')],[J(14,0),J(23,0)],[J(23,0),('R1','1')],[J(23,0),(39,0),('R5','1')],
 # inputs: x1 — emitter E1, x2 — emitter E2; clamps D1, D2 down to the common bus
 [x1,J(4,20)],[J(4,20),('Q1','E1')],[J(4,20),('D1','K')],
 [x2,J(8,26)],[J(8,26),(12,26),('Q1','E2')],[J(8,26),('D2','K')],
 [('R3','2'),('Q1','B')],[('Q1','C'),('Q3','B')],
 # phase splitter Q3: collector — R1 and the base of Q4, emitter — R2 and the base of Q5
 [('R1','2'),J(23,14)],[J(23,14),('Q3','C')],[J(23,14),('Q4','B')],
 [('Q3','E'),J(23,32)],[J(23,32),('Q5','B')],[J(23,32),('R2','1')],
 # Darlington pair Q4–Q6: collectors to R5, the Q4 emitter — the base of Q6 and R6 to ground
 [('R5','2'),J(39,9)],[J(39,9),(31,9),('Q4','C')],[J(39,9),('Q6','C')],
 [('Q4','E'),J(31,20)],[J(31,20),('Q6','B')],[J(31,20),('R6','1')],
 # output: Q6 emitter — Q5 collector — multimeter
 [('Q6','E'),J(39,26)],[J(39,26),('Q5','C')],[J(39,26),y],
 # common ground bus
 [('D1','A'),(4,41),J(8,41)],[('D2','A'),J(8,41)],[J(8,41),J(23,41)],[('R2','2'),J(23,41)],[J(23,41),J(31,41)],
 [('R6','2'),J(31,41)],[J(31,41),J(39,41)],[('Q5','E'),J(39,41)],[J(39,41),g],
])
S.build()
