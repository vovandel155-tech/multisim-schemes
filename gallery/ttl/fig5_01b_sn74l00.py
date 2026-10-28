import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Fig. 5.1b — 1/4 SN74L00 (low-power TTL 2-input NAND).
# Layout as in the textbook (the same as 5.1a; the figure has no input diodes and no C_L).
# Multi-emitter Q1 (VTN) — subcircuit MultiNPN2 inside the file (its sheet comes from Multi_emitter_npn.ms14: two 2N2222
# with a common base and collector), symbol as in the textbook: base bar on top, emitters down-left, collector down-right.
# Q3 — phase splitter (VT1), Q4 — upper output (VT2) with diode D3 (VT3 in the figure), Q5 — lower output;
# common ground bus at the bottom.
S=Scheme('fig5_01b_sn74l00',outdir=GALLERY)
P=S.part
P('Q1','QM2','B',14,15)                           # B (14,15), bar y=18, E1 (10,20), E2 (12,20), C (17,20)
P('Q3','Q','C',23,16)                             # C (23,16), B (20,20), E (23,24)
P('Q4','Q','C',31,10)                             # C (31,10), B (28,14), E (31,18)
P('Q5','Q','C',31,30)                             # C (31,30), B (28,34), E (31,38)
P('D3','D','A',31,20,rot=180,mirror=True)         # A (31,20), K (31,26)
P('R3','R','1',14,2,value='40k'); P('R1','R','1',23,2,value='20k'); P('R5','R','1',31,2,value='500')
P('R2','R','1',23,35,value='12k')
vcc=S.vcc(9,0); g=S.gnd(31,43)
x1=S.switch('S1',-4,20,gnd=1); x2=S.switch('S2',-14,26)
y=S.meter('XMM1',38,28)
S.wires([
 # VCC bus
 [vcc,J(14,0)],[J(14,0),('R3','1')],[J(14,0),J(23,0)],[J(23,0),('R1','1')],[J(23,0),(31,0),('R5','1')],
 # inputs: x1 — emitter E1, x2 — emitter E2
 [x1,('Q1','E1')],[x2,(12,26),('Q1','E2')],
 [('R3','2'),('Q1','B')],[('Q1','C'),('Q3','B')],
 # phase splitter Q3: collector — R1 and the base of Q4, emitter — R2 and the base of Q5
 [('R1','2'),J(23,14)],[J(23,14),('Q3','C')],[J(23,14),('Q4','B')],
 [('Q3','E'),J(23,34)],[J(23,34),('Q5','B')],[J(23,34),('R2','1')],
 # output: Q4 — D3 — node — Q5, C1 and the multimeter
 [('R5','2'),('Q4','C')],[('Q4','E'),('D3','A')],[('D3','K'),J(31,28)],[J(31,28),('Q5','C')],[J(31,28),y],
 # common ground bus
 [('R2','2'),(23,41),J(31,41)],
 [('Q5','E'),J(31,41)],[J(31,41),g],
])
S.build()
