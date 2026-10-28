import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Fig. 5.1a — 1/4 SN7400 (TTL 2-input NAND). Layout as in the textbook.
# Multi-emitter Q1 (VTN) — subcircuit MultiNPN2 inside the file (its sheet comes from Multi_emitter_npn.ms14: two 2N2222
# with a common base and collector), symbol as in the textbook: base bar on top, emitters down-left, collector down-right.
# Q3 — phase splitter (VT1), Q4 — upper output (VT2) with diode D3 (VT3 in the figure), Q5 — lower output;
# D1, D2 — input clamps; C1 — load C_L 15 pF with its own ground, as in the textbook; common ground bus at the bottom.
S=Scheme('fig5_01a_sn7400',outdir=GALLERY)
P=S.part
P('Q1','QM2','B',14,15)                           # B (14,15), bar y=18, E1 (10,20), E2 (12,20), C (17,20)
P('Q3','Q','C',23,16)                             # C (23,16), B (20,20), E (23,24)
P('Q4','Q','C',31,10)                             # C (31,10), B (28,14), E (31,18)
P('Q5','Q','C',31,30)                             # C (31,30), B (28,34), E (31,38)
P('D3','D','A',31,20,rot=180,mirror=True)         # A (31,20), K (31,26)
P('R3','R','1',14,2,value='4k'); P('R1','R','1',23,2,value='1.6k'); P('R5','R','1',31,2,value='130')
P('R2','R','1',23,35,value='1k')
P('D1','D','A',4,34); P('D2','D','A',8,34)        # cathode up: K (x,28), A (x,34)
P('C1','C','1',38,30,value='15p')
vcc=S.vcc(9,0); g=S.gnd(31,43); gc=S.gnd(38,37)
x1=S.switch('S1',-4,20,gnd=1); x2=S.switch('S2',-14,26)
y=S.meter('XMM1',43,28)
S.wires([
 # VCC bus
 [vcc,J(14,0)],[J(14,0),('R3','1')],[J(14,0),J(23,0)],[J(23,0),('R1','1')],[J(23,0),(31,0),('R5','1')],
 # inputs: x1 — emitter E1, x2 — emitter E2; clamps D1, D2 down to the common bus
 [x1,J(4,20)],[J(4,20),('Q1','E1')],[J(4,20),('D1','K')],
 [x2,J(8,26)],[J(8,26),(12,26),('Q1','E2')],[J(8,26),('D2','K')],
 [('R3','2'),('Q1','B')],[('Q1','C'),('Q3','B')],
 # phase splitter Q3: collector — R1 and the base of Q4, emitter — R2 and the base of Q5
 [('R1','2'),J(23,14)],[J(23,14),('Q3','C')],[J(23,14),('Q4','B')],
 [('Q3','E'),J(23,34)],[J(23,34),('Q5','B')],[J(23,34),('R2','1')],
 # output: Q4 — D3 — node — Q5, C1 and the multimeter
 [('R5','2'),('Q4','C')],[('Q4','E'),('D3','A')],[('D3','K'),J(31,28)],[J(31,28),('Q5','C')],[J(31,28),J(38,28)],
 [J(38,28),('C1','1')],[J(38,28),y],[('C1','2'),gc],
 # common ground bus
 [('D1','A'),(4,41),J(8,41)],[('D2','A'),J(8,41)],[J(8,41),J(23,41)],[('R2','2'),J(23,41)],[J(23,41),J(31,41)],
 [('Q5','E'),J(31,41)],[J(31,41),g],
])
S.build()
