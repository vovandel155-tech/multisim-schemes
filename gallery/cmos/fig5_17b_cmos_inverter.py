import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Fig. 5.17b — CMOS inverter. p-MOS on top: source to VDD (VCC), drain — output; n-MOS below: drain — output, source to ground.
# Substrates tied to the sources (as in the textbook: the substrate arrow at pin S). Gates — a common vertical on the left (input V_I),
# drains — a common node on the right (output V_O). MOS transistors from sample_mos.ms14 (MOS_P_4T / MOS_N_4T).
S=Scheme('fig5_17b_cmos_inverter',outdir=GALLERY)
P=S.part
P('Q1','PMOS','S',10,3,rot=180,mirror=True)     # source on top: S (10,3), G (7,6), SUB (12,7), D (10,11)
P('Q2','NMOS','D',10,15)                         # drain on top:  D (10,15), G (7,20), SUB (12,19), S (10,23)
vdd=S.vcc(10,-1); g=S.gnd(10,27)
x=S.switch('S1',0,13)
y=S.meter('XMM1',16,13)
S.wires([
 # VDD — p-MOS source and substrate
 [vdd,J(10,1)],[J(10,1),('Q1','S')],[('Q1','SUB'),(12,1),J(10,1)],
 # output: drains
 [('Q1','D'),J(10,13)],[J(10,13),('Q2','D')],[J(10,13),y],
 # input: gates on a common vertical on the left
 [x,J(4,13)],[J(4,13),(4,6),('Q1','G')],[J(4,13),(4,20),('Q2','G')],
 # ground — n-MOS source and substrate
 [('Q2','S'),J(10,25)],[('Q2','SUB'),(12,25),J(10,25)],[J(10,25),g],
])
S.build()
