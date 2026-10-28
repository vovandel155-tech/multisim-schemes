import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Part FZT1049A (obtained with get_parts.bat in a claude.ai chat): npn switch. S1 → R1 1k → base, collector — R2 1k to VCC,
# emitter to ground; multimeter XMM1 on the collector. S1 = 1 — the transistor is on (≈ 0 V), S1 = 0 — the output is ≈ VCC.
S=Scheme('fzt1049a_switch',outdir=GALLERY)
P=S.part
P('Q1','FZT1049A','B',14,13)                      # B (14,13), C (17,9), E (17,17)
P('R1','R','1',4,13,rot=270,value='1k'); P('R2','R','1',17,2,value='1k')
vcc=S.vcc(17,0); g=S.gnd(17,21)
x1=S.switch('S1',0,13)
y=S.meter('XMM1',26,8)
S.wires([
 [x1,('R1','1')],[('R1','2'),('Q1','B')],
 [vcc,('R2','1')],[('R2','2'),J(17,8)],[J(17,8),('Q1','C')],[J(17,8),y],
 [('Q1','E'),g],
])
S.build()
