import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Fig. 5.5 — 1/4 SN74ALS00, element placement and wire routing as in the textbook figure (scale: transistor = 8 cells).
# Inputs — pnp Q1, Q2 (2N2907A from sample_pnp.ms14): base — input, emitter — the R1 37k node, collector — ground.
# Transistors with «hooks» on the base (Q3–Q8) — subcircuit SchottkyNPN (2N2222 + 10BQ015) with the textbook symbol.
# Ground — common bus at the bottom (the textbook shows no symbol on it — one is added on the right); input x1 has its own ground, as in the textbook.
# The output is a 4-wire junction. Verified in Multisim.
S=Scheme('fig5_05_sn74als00',outdir=GALLERY)
P=S.part
def pnp(q,ex,ey):       # pnp emitter up: emitter (ex,ey), base (ex-3,ey+4), collector (ex,ey+8)
    P(q,'P','E',ex,ey,rot=180,mirror=True,label='right')
# supply and resistors on top
vcc=S.vcc(4,0)
P('R1','R','1',12,1,value='37k',label='right'); P('R2','R','1',24,1,value='50k',label='right')
P('R3','R','1',30,1,value='14k',label='right'); P('R4','R','1',46,1,value='50',label='right')
# transistors
pnp('Q1',12,15); pnp('Q2',12,43)
for q,x,y in (('Q3',24,9),('Q4',30,28),('Q5',36,8),('Q6',46,14),('Q7',46,34),('Q8',36,47)): P(q,'QS','C',x,y,label='right')
P('R5','R','1',39,24,rot=270,value='5k',label='top')
P('R6','R','1',30,40,value='2.9k',label='right'); P('R7','R','1',36,40,value='5.6k',label='right')
# diodes: D1, D2 — input clamps, D3, D4 — from the Q4 base to the inputs, D5 — from the output to the Q4 collector, D6 — output clamp
P('D1','DS','A',5,33,label='right'); P('D2','DS','A',5,61,label='right')
P('D3','DS','A',23,25,rot=270,label='top'); P('D4','DS','A',23,53,rot=270,label='top')
P('D5','DS','A',40,26,rot=270,label='bottom'); P('D6','DS','A',52,36,label='right')
g1=S.gnd(12,37); g=S.gnd(52,65)
# inputs: switches S1, S2, output — multimeter
x1=S.switch('S1',1,19); x2=S.switch('S2',1,47)
y=S.meter('XMM1',56,26)
S.wires([
 # VCC bus
 [vcc,J(12,0)],[J(12,0),('R1','1')],[J(12,0),J(24,0)],[J(24,0),('R2','1')],[J(24,0),J(30,0)],
 [J(30,0),('R3','1')],[J(30,0),(46,0),('R4','1')],
 # R1 node (37k): emitters of Q1, Q2 and the base of Q3
 [('R1','2'),J(12,13)],[J(12,13),('Q1','E')],[J(12,13),J(16,13)],[J(16,13),('Q3','B')],[J(16,13),(16,41),(12,41),('Q2','E')],
 [('R2','2'),('Q3','C')],
 # input x1: Q1 base, D3 to the Q4 base, clamp D1; the Q1 collector and D1 go to their own ground
 [x1,J(5,19)],[J(5,19),('Q1','B')],[J(5,19),J(5,25)],[J(5,25),('D3','K')],[J(5,25),('D1','K')],
 [('D1','A'),(5,35),J(12,35)],[('Q1','C'),J(12,35)],[J(12,35),g1],
 # input x2
 [x2,J(5,47)],[J(5,47),('Q2','B')],[J(5,47),J(5,53)],[J(5,53),('D4','K')],[J(5,53),('D2','K')],
 # Q3 emitter — Q4 base (together with D3, D4)
 [('Q3','E'),J(24,25)],[('D3','A'),J(24,25)],[J(24,25),J(24,32)],[J(24,32),('Q4','B')],[J(24,32),(24,53),('D4','A')],
 # R3 column (14k): Q5 base, D5, Q4 collector
 [('R3','2'),J(30,12)],[J(30,12),('Q5','B')],[J(30,12),J(30,26)],[J(30,26),('D5','K')],[J(30,26),('Q4','C')],
 # Darlington pair Q5, Q6, R4 (50), R5 (5k)
 [('Q5','C'),J(46,8)],[('R4','2'),J(46,8)],[J(46,8),('Q6','C')],
 [('Q5','E'),J(36,18)],[J(36,18),('Q6','B')],[J(36,18),(36,24),('R5','1')],
 [('Q6','E'),J(46,24)],[('R5','2'),J(46,24)],[J(46,24),J(46,26)],[('D5','A'),J(46,26)],
 # output
 [J(46,26),J(52,26)],[J(46,26),('Q7','C')],[J(52,26),y],[J(52,26),('D6','K')],
 # Q4 emitter: R6 (2.9k), R7 (5.6k), Q7 base; Q8
 [('Q4','E'),J(30,38)],[J(30,38),('R6','1')],[J(30,38),J(36,38)],[J(36,38),('R7','1')],[J(36,38),('Q7','B')],
 [('R7','2'),('Q8','C')],[('R6','2'),(30,51),('Q8','B')],
 # common ground bus
 [('D2','A'),(5,63),J(12,63)],[('Q2','C'),J(12,63)],[J(12,63),J(36,63)],[('Q8','E'),J(36,63)],[J(36,63),J(46,63)],
 [('Q7','E'),J(46,63)],[J(46,63),J(52,63)],[('D6','A'),J(52,63)],[J(52,63),g],
])
S.build()
