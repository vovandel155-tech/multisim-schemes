import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Catalog sources: DC_INTERACTIVE_VOLTAGE turned plus-down (rot=180, mirror=True) — its reading «0.7V»
# (CIITVariableSymText) is only moved, never rotated, and sits under the value. AC_VOLTAGE — the wire from C1 reaches pin 1
# from above, not through the body.
# VIN → C1 → R1 to ground; V2 — plus to ground, minus to load R2 and multimeter XMM1 (shows −V2).
S=Scheme('catalog_sources',outdir=GALLERY)
S.part('VIN','AC_VOLTAGE','1',4,10)                         # 1 (4,10), 2 (4,16)
S.part('C1','C','1',10,10,rot=270,value='10n')              # 1 (10,10), 2 (15,10)
S.part('R1','R','1',20,12,value='10k')
S.part('V2','DC_INTERACTIVE_VOLTAGE','1',36,22,rot=180,mirror=True)   # 1 (36,22) «+» at the bottom, 2 (36,16)
S.part('R2','R','1',44,13,value='1k')
g=S.gnd(20,27)
y=S.meter('XMM1',50,8)
S.wires([
 [('VIN','1'),('C1','1')],[('C1','2'),(20,10),('R1','1')],[('VIN','2'),(4,24),J(20,24)],[('R1','2'),J(20,24)],[J(20,24),g],
 [J(20,24),J(36,24)],[('V2','1'),J(36,24)],[('R2','2'),(44,24),J(36,24)],
 [('V2','2'),J(36,13)],[J(36,13),('R2','1')],[J(36,13),(36,8),y],
])
S.build()
