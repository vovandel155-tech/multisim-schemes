import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Fig. 5.4 — 1/4 SN74LS00, element placement and wire routing as in the textbook figure (scale: transistor = 8 cells).
# Schottky transistors (Q1, Q2, Q4, Q5) — subcircuit SchottkyNPN (2N2222 + 10BQ015) with the textbook symbol.
# Ground — one common bus at the bottom (GND symbol on the right, as in the textbook). Textbook «crosses» are 4-wire junctions.
# Verified in Multisim.
S=Scheme('fig5_04_sn74ls00',outdir=GALLERY)
P=S.part
# supply and resistors on top
vcc=S.vcc(4,0)
P('R1','R','1',19,2,value='20k',label='left'); P('R2','R','1',28,2,value='8k',label='right'); P('R3','R','1',52,2,value='120',label='left')
# transistors: Q2, Q3 — Darlington pair, Q1 — phase splitter, Q4 — output, Q5 — «squaring» transistor
P('Q2','QS','C',42,12,label='right'); P('Q3','Q','C',52,20,label='right'); P('Q1','QS','C',28,35,label='right')
P('Q4','QS','C',52,44,label='right'); P('Q5','QS','C',38,58,label='right')
P('R4','R','1',42,26,value='4k',label='left'); P('R5','R','1',19,42,value='12k',label='right')
P('R6','R','1',28,50,value='1.5k',label='left'); P('R7','R','1',38,50,value='3k',label='right')
# diodes: D1, D2 — input, D3, D4 — clamps, D5, D6 — from the output to the Q1 collector
P('D1','DS','A',16,33,rot=270,label='top'); P('D2','DS','A',16,39,rot=270,label='top')
P('D3','DS','A',0,51,label='right'); P('D4','DS','A',7,51,label='right')
P('D5','DS','A',37,24,rot=270,label='top'); P('D6','DS','A',37,33,rot=270,label='top')
g=S.gnd(52,73)
# inputs: switches S1, S2 (S2 further left so their VCC/GND do not collide), output — multimeter
x1=S.switch('S1',-4,33,gnd=1); x2=S.switch('S2',-14,39)
y=S.meter('XMM1',59,33)
S.wires([
 # VCC bus
 [vcc,J(19,0)],[J(19,0),('R1','1')],[J(19,0),J(28,0)],[J(28,0),('R2','1')],[J(28,0),(52,0),('R3','1')],
 # inputs x1, x2: clamps D3, D4 down to the common bus, diodes D1, D2 to the R1 column
 [x1,J(0,33)],[J(0,33),('D1','K')],[J(0,33),('D3','K')],
 [x2,J(7,39)],[J(7,39),('D2','K')],[J(7,39),('D4','K')],
 # R1 column (20k): D1, D2, Q1 base, R5 (12k)
 [('R1','2'),J(19,33)],[J(19,33),('D1','A')],[J(19,33),J(19,39)],[J(19,39),('D2','A')],[J(19,39),('Q1','B')],[J(19,39),('R5','1')],
 # R2 column (8k): Q2 base, D5, D6, Q1 collector
 [('R2','2'),J(28,16)],[J(28,16),('Q2','B')],[J(28,16),J(28,24)],[J(28,24),('D5','K')],[J(28,24),J(28,33)],
 [J(28,33),('D6','K')],[J(28,33),('Q1','C')],
 # Q2, Q3, R3 (120), R4 (4k)
 [('Q2','C'),(42,9),J(52,9)],[('R3','2'),J(52,9)],[J(52,9),('Q3','C')],
 [('Q2','E'),J(42,24)],[J(42,24),('Q3','B')],[J(42,24),('D5','A')],[J(42,24),('R4','1')],
 [('R4','2'),J(42,33)],[('D6','A'),J(42,33)],[J(42,33),J(52,33)],
 # output
 [('Q3','E'),J(52,33)],[J(52,33),y],[J(52,33),('Q4','C')],
 # Q1 emitter: R5, R6 (1.5k), R7 (3k), Q4 base; Q5
 [('R5','2'),(19,48),J(28,48)],[('Q1','E'),J(28,48)],[J(28,48),('R6','1')],[J(28,48),J(38,48)],
 [J(38,48),('R7','1')],[J(38,48),('Q4','B')],
 [('R7','2'),('Q5','C')],[('R6','2'),(28,62),('Q5','B')],
 # common ground bus
 [('D3','A'),(0,71),J(7,71)],[('D4','A'),J(7,71)],[J(7,71),J(38,71)],[('Q5','E'),J(38,71)],[J(38,71),J(52,71)],
 [('Q4','E'),J(52,71)],[J(52,71),g],
])
S.build()
