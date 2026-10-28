import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Donors made by donors.vbs (ReplaceComponent): Darlington TIP121G (npn) and TIP127G (pnp) — a push-pull
# emitter follower. S1 → R1 1k → bases; TIP121G: collector to VCC, TIP127G: collector to ground; the emitters are the output
# into load R2 100 Ohm and multimeter XMM1. S1 = 1 — TIP121G is on (output ≈ VCC − 1.3 V), S1 = 0 — output near 0.
S=Scheme('darlington_tip121_tip127',outdir=GALLERY)
P=S.part
P('Q1','TIP121G','B',14,8)                        # B (14,8), C (19,4), E (19,13)
P('Q2','TIP127G','B',14,21)                       # B (14,21), E (19,16), C (19,25)
P('R1','R','1',4,13,rot=270,value='1k'); P('R2','R','1',28,16,value='100')
vcc=S.vcc(19,1); g=S.gnd(19,28); g2=S.gnd(28,24)
x1=S.switch('S1',0,13)
y=S.meter('XMM1',33,14)
S.wires([
 [x1,('R1','1')],[('R1','2'),J(11,13)],[J(11,13),(11,8),('Q1','B')],[J(11,13),(11,21),('Q2','B')],
 [vcc,('Q1','C')],[('Q2','C'),g],
 [('Q1','E'),J(19,14)],[('Q2','E'),J(19,14)],[J(19,14),J(28,14)],[J(28,14),('R2','1')],[J(28,14),y],[('R2','2'),g2],
])
S.build()
