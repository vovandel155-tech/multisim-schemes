import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Analyses: DC Operating Point in Batched (Simulate → Analyses and Simulation → Batched → Run).
# Common-emitter bias: V1 12 V, divider R1 47k / R2 10k sets the base, RC 2.2k, RE 1k.
# Expected (ngspice): V(1) 12 V, V(2) base 2.039 V, V(3) collector 8.913 V, V(4) emitter 1.411 V, V(3)-V(4) 7.502 V,
# I(V1) −1.615 mA (SPICE counts the current flowing into the + pin).
S=Scheme('batched_op',outdir=GALLERY)
P=S.part
P('V1','DC_POWER','1',4,10)                         # 1 «+» (4,10), 2 «−» (4,14)
P('R1','R','1',16,6,value='47k'); P('R2','R','1',16,21,value='10k')
P('RC','R','1',28,5,value='2.2k'); P('RE','R','1',28,23,value='1k')
P('Q1','Q','C',28,12)                               # C (28,12), B (25,16), E (28,20)
g=S.gnd(16,34)
S.wires([
 [('V1','1'),(4,2),J(16,2)],[J(16,2),('R1','1')],[J(16,2),(28,2),('RC','1')],
 [('R1','2'),J(16,16)],[J(16,16),('R2','1')],[J(16,16),('Q1','B')],
 [('RC','2'),('Q1','C')],[('Q1','E'),('RE','1')],
 [('V1','2'),(4,31),J(16,31)],[('R2','2'),J(16,31)],[J(16,31),g],[J(16,31),(28,31),('RE','2')],
])
# nets of this build: 1 — V1+ / R1 / RC, 2 — base, 3 — collector, 4 — emitter
S.op(['V(1)','V(2)','V(3)','V(4)','V(3)-V(4)','I(V1)'],title='Operating point')
S.build()
