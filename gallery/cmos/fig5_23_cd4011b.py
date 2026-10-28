import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Fig. 5.23 — 1/4 CD4011B (buffered 2-input NAND): f = NOT(x2 · x1).
# Input inverters Q1, Q2 (x1) and Q3, Q4 (x2); NOR core: p-MOS Q5 — Q6 in series (gates NOT x1, NOT x2),
# n-MOS Q7 ‖ Q8 (node M = x1 · x2); output inverter Q9, Q10. As in the textbook: the first inverter output goes up to the Q5 gate
# and by a long vertical down to Q7; the second one — by a vertical to Q6 and Q8; the VDD vertical (x = 46) — to the Q5 source and
# substrate and the Q6 substrate; wires cross without connections. The common ground bus at the bottom has no symbol in the textbook —
# GND added under Q8 (a 4-wire junction). p-MOS substrates to VDD, n-MOS to their own sources (ground).
S=Scheme('fig5_23_cd4011b',outdir=GALLERY)
P=S.part
def pmos(n,x,y): P(n,'PMOS','S',x,y,rot=180,mirror=True)    # S (x,y), G (x-3,y+3), SUB (x+2,y+4), D (x,y+8)
def nmos(n,x,y): P(n,'NMOS','D',x,y)                        # D (x,y), G (x-3,y+5), SUB (x+2,y+4), S (x,y+8)
pmos('Q1',6,4); nmos('Q2',6,25); pmos('Q3',20,14); nmos('Q4',20,33)
pmos('Q5',42,3); pmos('Q6',42,22); nmos('Q7',31,39); nmos('Q8',42,39)
pmos('Q9',56,20); nmos('Q10',56,39)
vdd=S.vcc(2,0); g=S.gnd(42,53)
x1=S.switch('S1',-6,30); x2=S.switch('S2',-14,38)
y=S.meter('XMM1',62,33)
W=[
 # VDD bus and the x = 46 vertical
 [vdd,J(6,0)],[J(6,0),J(20,0)],[J(20,0),J(46,0)],[J(46,0),(56,0),J(56,18)],
 [J(6,0),J(6,1)],[('Q1','S'),J(6,1)],[('Q1','SUB'),(8,1),J(6,1)],
 [J(20,0),J(20,12)],[('Q3','S'),J(20,12)],[('Q3','SUB'),(22,12),J(20,12)],
 [J(46,0),J(46,3)],[('Q5','S'),J(46,3)],[J(46,3),J(46,7)],[('Q5','SUB'),J(46,7)],[J(46,7),(46,26),('Q6','SUB')],
 [('Q9','S'),J(56,18)],[('Q9','SUB'),(58,18),J(56,18)],
 # input inverters
 [x1,J(0,30)],[J(0,30),('Q2','G')],[J(0,30),(0,7),('Q1','G')],
 [('Q1','D'),J(6,19)],[J(6,19),('Q2','D')],[J(6,19),(10,19),(10,6),J(25,6)],
 [x2,J(14,38)],[J(14,38),('Q4','G')],[J(14,38),(14,17),('Q3','G')],
 [('Q3','D'),J(20,27)],[J(20,27),('Q4','D')],[J(20,27),J(35,27)],
 # core: NOT x1 — Q5, Q7; NOT x2 — Q6, Q8
 [J(25,6),('Q5','G')],[J(25,6),(25,44),('Q7','G')],
 [J(35,27),(35,25),('Q6','G')],[J(35,27),(35,44),('Q8','G')],
 [('Q5','D'),('Q6','S')],
 [('Q6','D'),J(42,33)],[('Q7','D'),(31,33),J(42,33)],[J(42,33),('Q8','D')],[J(42,33),J(49,33)],
 # output inverter
 [J(49,33),(49,23),('Q9','G')],[J(49,33),(49,44),('Q10','G')],
 [('Q9','D'),J(56,33)],[J(56,33),('Q10','D')],[J(56,33),y],
 # common ground bus
 [J(6,35),(6,51),J(20,51)],[J(20,43),J(20,51)],[J(20,51),J(31,51)],[J(31,49),J(31,51)],[J(31,51),J(42,51)],
 [J(42,49),J(42,51)],[J(42,51),g],[J(42,51),(56,51),J(56,49)],
]
for n,x,s in (('Q2',6,35),('Q4',20,43),('Q7',31,49),('Q8',42,49),('Q10',56,49)):   # n-MOS source and substrate
    W+=[[(n,'S'),J(x,s)],[(n,'SUB'),(x+2,s),J(x,s)]]
S.wires(W)
S.build()
