import sys, os; sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','scripts'))
# Example: TTL 2-4 AND-2 OR-INVERT (fig. 5.14) — multi-emitter transistors as a subcircuit (QM), one switch per input group.
from scheme import *
# Fig. 5.14 — 1/2 K155LR4 (4-4 AND-2 OR-INVERT with expansion), without the K155LD1 expander (right half only).
# Element placement and wire routing as in the textbook figure (input line pitch — 4 cells).
# Q1 (TX), Q2 (TY) — multi-emitter: subcircuit MultiNPN4 from sample_multiemitter.ms14 with the textbook symbol.
# Inputs X1–X4 (and Y1–Y4) are bracketed in the figure — one switch per group: S1 = X, S2 = Y, f = NOT(X + Y).
# The expansion pins C-C and E-E are unused without the expander — no lines are drawn to them.
# Q7: its base is tied to the common bus, as in the textbook (the transistor is off, R5 acts as a resistor to ground).
# Verified in Multisim.
S=Scheme('ttl_multiemitter')
P=S.part
# supply and resistors on top: bases of Q1, Q2, the phase splitter collectors, the Q5 collector
vcc=S.vcc(10,0)
P('R1','R','1',28,2,value='4k',label='left'); P('R2','R','1',46,2,value='4k',label='left')
P('R3','R','1',66,2,value='1.6k',label='left'); P('R4','R','1',83,2,value='130',label='left')
# multi-emitter Q1 (X), Q2 (Y): base pin B, emitters E1–E4 5 cells lower, collector C on the right
P('Q1','QM','B',28,15,label='right'); P('Q2','QM','B',46,31,label='right')
# phase splitters Q3, Q4, output stage Q5 (upper), D9, Q6 (lower), Q7 with R5, R6
for q,x,y in (('Q3',54,16),('Q4',66,16),('Q5',83,9),('Q6',83,35),('Q7',74,48)): P(q,'Q','C',x,y,label='right')
P('D9','D','A',83,19,rot=180,mirror=True,label='right')
P('R5','R','1',66,41,value='1k',label='left'); P('R6','R','1',74,41,value='1k',label='right')
# input clamp diodes (cathode to the input, anode to the common bus)
for i,x in enumerate((3,9,15,21,27,33,39,46)): P('D%d'%(i+1),'D','A',x,58,label='right')
g=S.gnd(83,62)
# switches: S1 — group X, S2 — group Y; multimeter on output f
x=S.switch('S1',-3,26); y=S.switch('S2',-3,42)
f=S.meter('XMM1',88,27)
S.wires([
 # VCC bus
 [vcc,J(28,0)],[J(28,0),('R1','1')],[J(28,0),J(46,0)],[J(46,0),('R2','1')],[J(46,0),J(66,0)],
 [J(66,0),('R3','1')],[J(66,0),(83,0),('R4','1')],
 # group X: switch S1 to a common vertical, inputs X1–X4 to the Q1 emitters as a «ladder», a diode down from each input
 [x,J(0,26)],[J(0,26),J(0,24)],[J(0,26),J(0,28)],
 [J(0,24),(0,20),J(3,20)],[J(3,20),('Q1','E1')],[J(3,20),('D1','K')],
 [J(0,24),J(9,24)],[J(9,24),(22,24),('Q1','E2')],[J(9,24),('D2','K')],
 [J(0,28),J(15,28)],[J(15,28),(24,28),('Q1','E3')],[J(15,28),('D3','K')],
 [J(0,28),(0,32),J(21,32)],[J(21,32),(26,32),('Q1','E4')],[J(21,32),('D4','K')],
 # group Y
 [y,J(0,42)],[J(0,42),J(0,40)],[J(0,42),J(0,44)],
 [J(0,40),(0,36),J(27,36)],[J(27,36),('Q2','E1')],[J(27,36),('D5','K')],
 [J(0,40),J(33,40)],[J(33,40),(40,40),('Q2','E2')],[J(33,40),('D6','K')],
 [J(0,44),J(39,44)],[J(39,44),(42,44),('Q2','E3')],[J(39,44),('D7','K')],
 [J(0,44),(0,48),J(44,48)],[J(44,48),('Q2','E4')],[J(44,48),(46,48),('D8','K')],
 # Q1, Q2 bases from R1, R2; collectors to the bases of phase splitters Q3, Q4
 [('R1','2'),('Q1','B')],[('R2','2'),('Q2','B')],
 [('Q1','C'),('Q3','B')],[('Q2','C'),(58,36),(58,20),('Q4','B')],
 # Q3, Q4 collectors (line C-C) — R3 and the Q5 base
 [('Q3','C'),(54,13),J(66,13)],[('R3','2'),J(66,13)],[J(66,13),('Q4','C')],[J(66,13),('Q5','B')],
 [('R4','2'),('Q5','C')],[('Q5','E'),('D9','A')],
 # output f
 [('D9','K'),J(83,27)],[J(83,27),f],[J(83,27),('Q6','C')],
 # Q3, Q4 emitters (line E-E) — Q6 base, R5, R6
 [('Q3','E'),(54,28),J(66,28)],[('Q4','E'),J(66,28)],[J(66,28),J(66,39)],
 [J(66,39),J(74,39)],[J(66,39),('R5','1')],[J(74,39),('R6','1')],[J(74,39),('Q6','B')],
 [('R6','2'),('Q7','C')],[('R5','2'),J(66,52)],[J(66,52),('Q7','B')],
 # common ground bus (diodes, Q7 base and emitter, Q6 emitter)
 [('D1','A'),(3,60),J(9,60)],[('D2','A'),J(9,60)],[J(9,60),J(15,60)],[('D3','A'),J(15,60)],[J(15,60),J(21,60)],
 [('D4','A'),J(21,60)],[J(21,60),J(27,60)],[('D5','A'),J(27,60)],[J(27,60),J(33,60)],[('D6','A'),J(33,60)],
 [J(33,60),J(39,60)],[('D7','A'),J(39,60)],[J(39,60),J(46,60)],[('D8','A'),J(46,60)],[J(46,60),J(66,60)],
 [J(66,52),J(66,60)],[J(66,60),J(74,60)],[('Q7','E'),J(74,60)],[J(74,60),J(83,60)],[('Q6','E'),J(83,60)],
 [J(83,60),g],
])
S.build()
