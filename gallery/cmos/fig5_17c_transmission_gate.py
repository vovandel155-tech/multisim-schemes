import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Fig. 5.17c — CMOS switch (transmission gate): p-MOS Q1 and n-MOS Q2 in parallel between In/Out and Out/In.
# As in the textbook: the upper bus goes to In/Out (up and left), the lower one to Out/In (down and right), the Q1 substrate up
# to VDD, the Q2 substrate down to its own ground; gate Gp on the left, Gn on the right. Substrate wires cross the buses without a connection.
# Input In/Out — switch S1, gates — switches S2 (Gp) and S3 (Gn), set opposite (Gn = NOT Gp; two switches instead of an
# inverter): S3 = 1, S2 = 0 — the gate is on, Out = In; S3 = 0, S2 = 1 — off (0 V on the voltmeter).
S=Scheme('fig5_17c_transmission_gate',outdir=GALLERY)
P=S.part
P('Q1','PMOS','S',10,0,rot=180,mirror=True)      # S (10,0), G (7,3), SUB (12,4), D (10,8)
P('Q2','NMOS','D',26,0,mirror=True)              # D (26,0), G (29,5), SUB (24,4), S (26,8)
vdd=S.vcc(12,-12); gs=S.gnd(24,20)
x=S.switch('S1',-6,-8)
gp=S.switch('S2',3,3)
gn=S.switch('S3',32,5,right=True)
y=S.meter('XMM1',40,16)
S.wires([
 # upper bus — In/Out
 [('Q1','S'),J(18,0)],[J(18,0),('Q2','D')],[J(18,0),(18,-8),x],
 # lower bus — Out/In
 [('Q1','D'),J(18,8)],[J(18,8),('Q2','S')],[J(18,8),(18,16),y],
 # substrates: Q1 to VDD, Q2 to ground
 [('Q1','SUB'),vdd],[('Q2','SUB'),gs],
 # gates
 [gp,('Q1','G')],[('Q2','G'),gn],
])
S.build()
