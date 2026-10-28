import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# EXPERIMENTAL: elements without a sample (SpiceLib) — sine source, capacitor, VCC 19.5 V, 1N4148×4, TIP121, TIP127.
# Left — RC network: V1 (1 V, 1 kHz) → C1 1µ → R1 1k to ground, multimeter XMM1 on R1 (AC mode: ≈ 0.7 V).
# Right — push-pull follower: bias R2 — D1 (1N4148×4) — R3, Darlington Q1 (TIP121) and Q2 (TIP127), load R4.
S=Scheme('spicelib_elements',outdir=GALLERY)
P=S.part
P('V1','VSIN','1',0,4,value='1'); g1=S.gnd(0,11)                 # 1 (+) (0,4), 2 (0,9)
P('C1','C','1',3,2,rot=270,value='1u')                             # 1 (3,2), 2 (8,2)
P('R1','R','1',12,4,value='1k'); g2=S.gnd(12,11)
y=S.meter('XMM1',16,2)
vcc=S.vcc(24,0,volts=19.5)
P('R2','R','1',30,1,value='3k')                                    # 1 (30,1), 2 (30,6)
P('D1','D4148x4','A',30,9,rot=180,mirror=True)                     # A (30,9), K (30,15)
P('R3','R','1',30,19,value='3k'); g3=S.gnd(30,26)
P('Q1','TIP121','C',40,3)                                          # C (40,3), B (37,7), E (40,11)
P('Q2','TIP127','E',40,13,rot=180,mirror=True)                     # E (40,13), B (37,17), C (40,21)
P('R4','R','1',46,14,value='1k'); g4=S.gnd(46,21); g5=S.gnd(40,23)
S.wires([
 [('V1','1'),(0,2),('C1','1')],[('C1','2'),J(12,2)],[J(12,2),('R1','1')],[J(12,2),y],[('V1','2'),g1],[('R1','2'),g2],
 [vcc,J(30,0)],[J(30,0),('R2','1')],[J(30,0),(40,0),('Q1','C')],
 [('R2','2'),J(30,7)],[J(30,7),('D1','A')],[J(30,7),('Q1','B')],
 [('D1','K'),J(30,17)],[J(30,17),('R3','1')],[J(30,17),('Q2','B')],[('R3','2'),g3],
 [('Q1','E'),J(40,12)],[J(40,12),('Q2','E')],[J(40,12),(46,12),('R4','1')],[('R4','2'),g4],[('Q2','C'),g5],
])
S.build()
