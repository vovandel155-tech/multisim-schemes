import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Fig. 5.22b — 1/4 MC14011B (buffered 2-input NAND): f = NOT(x2 · x1).
# The left part as in 5.22a: p-MOS Q1 (x2) ‖ Q2 (x1), n-MOS Q3 (x1) — Q4 (x2); then two inverters Q5, Q6 and Q7, Q8.
# As in the textbook: VDD bus on top, common ground bus at the bottom with the GND symbol under the Q3, Q4 substrates (a 4-wire junction),
# input verticals cross lines without connections. p-MOS substrates to their sources, inverter n-MOS to their sources,
# Q3, Q4 — to a common vertical to ground.
S=Scheme('fig5_22b_mc14011b',outdir=GALLERY)
P=S.part
def pmos(n,x): P(n,'PMOS','S',x,3,rot=180,mirror=True)     # S (x,3), G (x-3,6), SUB (x+2,7), D (x,11)
def nmos(n,x,y): P(n,'NMOS','D',x,y)                       # D (x,y), G (x-3,y+5), SUB (x+2,y+4), S (x,y+8)
pmos('Q1',7); pmos('Q2',21); nmos('Q3',21,29); nmos('Q4',21,41)
pmos('Q5',37); nmos('Q6',37,29); pmos('Q7',49); nmos('Q8',49,29)
vdd=S.vcc(2,0); g=S.gnd(26,53)
x1=S.switch('S1',-6,34); x2=S.switch('S2',-14,46)
y=S.meter('XMM1',56,23)
W=[
 # VDD bus
 [vdd,J(7,0)],[J(7,0),J(7,1)],[J(7,0),J(21,0)],[J(21,0),J(21,1)],[J(21,0),J(37,0)],[J(37,0),J(37,1)],
 [J(37,0),(49,0),J(49,1)],
 # NAND: Q1 output down and right — a 4-wire junction
 [('Q1','D'),(7,23),J(21,23)],[('Q2','D'),J(21,23)],[J(21,23),('Q3','D')],[J(21,23),J(30,23)],
 [x1,J(14,34)],[J(14,34),('Q3','G')],[J(14,34),(14,6),('Q2','G')],
 [x2,J(0,46)],[J(0,46),('Q4','G')],[J(0,46),(0,6),('Q1','G')],
 [('Q3','S'),('Q4','D')],
 [('Q3','SUB'),(26,33),J(26,45)],[('Q4','SUB'),J(26,45)],[J(26,45),J(26,51)],[('Q4','S'),(21,51),J(26,51)],
 # inverters
 [J(30,23),(30,6),('Q5','G')],[J(30,23),(30,34),('Q6','G')],
 [('Q5','D'),J(37,23)],[J(37,23),('Q6','D')],[J(37,23),J(42,23)],
 [J(42,23),(42,6),('Q7','G')],[J(42,23),(42,34),('Q8','G')],
 [('Q7','D'),J(49,23)],[J(49,23),('Q8','D')],[J(49,23),y],
 # common ground bus
 [J(26,51),g],[J(26,51),J(37,51)],[J(37,51),(49,51),J(49,39)],[J(37,39),J(37,51)],
]
for p,x in (('Q1',7),('Q2',21),('Q5',37),('Q7',49)):
    W+=[[(p,'S'),J(x,1)],[(p,'SUB'),(x+2,1),J(x,1)]]
for n,x in (('Q6',37),('Q8',49)):
    W+=[[(n,'S'),J(x,39)],[(n,'SUB'),(x+2,39),J(x,39)]]
S.wires(W)
S.build()
