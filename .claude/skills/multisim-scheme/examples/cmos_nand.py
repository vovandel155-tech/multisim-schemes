import sys, os; sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','scripts'))
# Example: CMOS 2-input NAND (fig. 5.22a) — two inputs, gate verticals crossing without connections.
from scheme import *
# Fig. 5.22a — 1/4 MC14011UB (unbuffered 2-input NAND): f = NOT(x2 · x1).
# p-MOS Q1 (gate x2) and Q2 (gate x1) in parallel from VDD to the output; n-MOS Q3 (x1) and Q4 (x2) in series
# from the output to ground. As in the textbook: the x2 vertical on the left to the Q1 gate crosses the x1 line, the Q1 output goes down and right,
# crossing the x1 vertical; Q3, Q4 substrates to a common vertical to ground (GND symbol bottom right), p-MOS to their sources.
S=Scheme('cmos_nand')
P=S.part
P('Q1','PMOS','S',7,3,rot=180,mirror=True)       # S (7,3), G (4,6), SUB (9,7), D (7,11)
P('Q2','PMOS','S',21,3,rot=180,mirror=True)      # S (21,3), G (18,6), SUB (23,7), D (21,11)
P('Q3','NMOS','D',21,29)                         # D (21,29), G (18,34), SUB (23,33), S (21,37)
P('Q4','NMOS','D',21,41)                         # D (21,41), G (18,46), SUB (23,45), S (21,49)
vdd=S.vcc(2,0); g=S.gnd(26,53)
x1=S.switch('S1',-6,34); x2=S.switch('S2',-14,46)
y=S.meter('XMM1',30,23)
S.wires([
 # VDD: p-MOS sources and substrates
 [vdd,J(7,0)],[J(7,0),J(7,1)],[J(7,0),(21,0),J(21,1)],
 [('Q1','S'),J(7,1)],[('Q1','SUB'),(9,1),J(7,1)],[('Q2','S'),J(21,1)],[('Q2','SUB'),(23,1),J(21,1)],
 # output
 [('Q1','D'),(7,23),J(21,23)],[('Q2','D'),J(21,23)],[J(21,23),('Q3','D')],[J(21,23),y],
 # inputs: x1 — Q3 and (by a vertical) Q2; x2 — Q4 and (by a vertical on the left) Q1
 [x1,J(14,34)],[J(14,34),('Q3','G')],[J(14,34),(14,6),('Q2','G')],
 [x2,J(0,46)],[J(0,46),('Q4','G')],[J(0,46),(0,6),('Q1','G')],
 # n-MOS in series; substrates and the Q4 source to ground
 [('Q3','S'),('Q4','D')],
 [('Q3','SUB'),(26,33),J(26,45)],[('Q4','SUB'),J(26,45)],[J(26,45),J(26,51)],
 [('Q4','S'),(21,51),J(26,51)],[J(26,51),g],
])
S.build()
