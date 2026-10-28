import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Fig. 5.21 — 1/4 CD4001B (buffered 2-input NOR): f = NOT(x2 + x1).
# Each input: diode pair — R — diode pair (upper ones — cathode to the line from VDD, lower ones — anode to the ground line),
# then input inverter Q1, Q2 (x1) / Q3, Q4 (x2). Their outputs drive a NAND core: p-MOS Q5 ‖ Q6, n-MOS Q7 — Q8
# in series (node M = x1 + x2), output inverter Q9, Q10. As in the textbook: VDD bus on top with supply verticals
# (x = 30 — to the diodes, x = 49 — to the Q1, Q3 sources), ground verticals (x = 33, x = 53), common ground bus at the bottom
# with the GND symbol under Q8 (a 4-wire junction); wires cross without connections. p-MOS substrates to their sources (VDD),
# n-MOS to their own sources (Q7 — to the node between Q7 and Q8, as in the textbook). R1, R2 = 1k (no values in the textbook).
S=Scheme('fig5_21_cd4001b',outdir=GALLERY)
P=S.part
def pmos(n,x,y): P(n,'PMOS','S',x,y,rot=180,mirror=True)    # S (x,y), G (x-3,y+3), SUB (x+2,y+4), D (x,y+8)
def nmos(n,x,y): P(n,'NMOS','D',x,y)                        # D (x,y), G (x-3,y+5), SUB (x+2,y+4), S (x,y+8)
for k,r in ((0,19),(1,53)):                       # input protection for x1 (row 19) and x2 (row 53)
    P('D%d'%(4*k+1),'D','A',10,r-5); P('D%d'%(4*k+2),'D','A',10,r+11)       # at x = 10: K (10,r-11) / K (10,r+5)
    P('D%d'%(4*k+3),'D','A',24,r-5); P('D%d'%(4*k+4),'D','A',24,r+11)
    P('R%d'%(k+1),'R','1',15,r,rot=270,value='1k')
pmos('Q1',42,4); nmos('Q2',42,26); pmos('Q3',42,38); nmos('Q4',42,60)        # input inverters
pmos('Q5',63,4); pmos('Q6',76,4); nmos('Q7',76,26); nmos('Q8',76,48)         # NAND core
pmos('Q9',88,4); nmos('Q10',88,26)                                           # output inverter
vdd=S.vcc(6,0); g=S.gnd(76,75)
x1=S.switch('S1',0,19); x2=S.switch('S2',0,53)
y=S.meter('XMM1',96,19)
W=[
 # VDD bus and supply verticals
 [vdd,J(30,0)],[J(30,0),J(49,0)],[J(49,0),J(63,0)],[J(63,0),J(76,0)],[J(76,0),(88,0),J(88,1)],
 [J(30,0),J(30,5)],[J(49,0),J(49,4)],[J(49,4),J(49,8)],[J(49,8),J(49,38)],[J(49,38),(49,42),('Q3','SUB')],
 [('Q1','S'),J(49,4)],[('Q1','SUB'),J(49,8)],[('Q3','S'),J(49,38)],
 # input protection: cathode lines to VDD (x = 30), anode lines to ground (x = 33)
 [('D1','K'),(10,5),J(24,5)],[('D3','K'),J(24,5)],[J(24,5),J(30,5)],
 [('D5','K'),(10,39),J(24,39)],[('D7','K'),J(24,39)],[J(24,39),(30,39),J(30,5)],
 [('D2','A'),(10,34),J(24,34)],[('D4','A'),J(24,34)],[J(24,34),(33,34),J(33,68)],
 [('D6','A'),(10,68),J(24,68)],[('D8','A'),J(24,68)],[J(24,68),J(33,68)],[J(33,68),(33,73),J(53,73)],
 [x1,J(10,19)],[J(10,19),('D1','A')],[J(10,19),('D2','K')],[J(10,19),('R1','1')],
 [('R1','2'),J(24,19)],[J(24,19),('D3','A')],[J(24,19),('D4','K')],[J(24,19),J(37,19)],
 [x2,J(10,53)],[J(10,53),('D5','A')],[J(10,53),('D6','K')],[J(10,53),('R2','1')],
 [('R2','2'),J(24,53)],[J(24,53),('D7','A')],[J(24,53),('D8','K')],[J(24,53),J(37,53)],
 # input inverters
 [J(37,19),(37,7),('Q1','G')],[J(37,19),(37,31),('Q2','G')],
 [('Q1','D'),J(42,19)],[J(42,19),('Q2','D')],[J(42,19),J(57,19)],
 [('Q2','SUB'),(53,30),J(53,34)],[('Q2','S'),J(53,34)],[J(53,34),J(53,64)],
 [J(37,53),(37,41),('Q3','G')],[J(37,53),(37,65),('Q4','G')],
 [('Q3','D'),J(42,53)],[J(42,53),('Q4','D')],[J(42,53),J(68,53)],
 [('Q4','SUB'),J(53,64)],[J(53,64),J(53,68)],[('Q4','S'),J(53,68)],[J(53,68),J(53,73)],
 # NAND core: NOT x1 — gates of Q5, Q7; NOT x2 — gates of Q6, Q8
 [J(57,19),(57,7),('Q5','G')],[J(57,19),(57,31),('Q7','G')],
 [J(68,53),(68,7),('Q6','G')],[J(68,53),('Q8','G')],
 [('Q5','D'),(63,19),J(76,19)],[('Q6','D'),J(76,19)],[J(76,19),('Q7','D')],[J(76,19),J(82,19)],
 [('Q7','S'),J(76,35)],[('Q7','SUB'),(78,35),J(76,35)],[J(76,35),('Q8','D')],
 [('Q8','S'),J(76,57)],[('Q8','SUB'),(78,57),J(76,57)],[J(76,57),J(76,73)],
 # output inverter
 [J(82,19),(82,7),('Q9','G')],[J(82,19),(82,31),('Q10','G')],
 [('Q9','D'),J(88,19)],[J(88,19),('Q10','D')],[J(88,19),y],
 [('Q10','S'),J(88,36)],[('Q10','SUB'),(90,36),J(88,36)],
 # common ground bus
 [J(53,73),J(76,73)],[J(76,73),g],[J(76,73),(88,73),J(88,36)],
]
for q,x in (('Q5',63),('Q6',76),('Q9',88)):      # sources and substrates of the upper p-MOS to the VDD bus
    W+=[[(q,'S'),J(x,1)],[(q,'SUB'),(x+2,1),J(x,1)]]+([[J(x,1),J(x,0)]] if x!=88 else [])
S.wires(W)
S.build()
