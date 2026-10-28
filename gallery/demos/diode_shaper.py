import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Diode wave shaper (piecewise-linear limiter) rebuilt from a screenshot. Emitter follower Q1 (base —
# divider R11/R12 from V1 10 V) sets a ≈ 4.3 V reference; divider R6–R5–R4 — thresholds ≈ 3.3 and 1.8 V. Input: V2 (sine) →
# R3 2.2k → line; D1 + R1 7.8k, D2 + R2 2.1k, D3 turn on one by one and flatten the positive half-wave.
# U1 — ideal op-amp as a follower (OPAMP_3T_VIRTUAL in Multisim), load R10 1k, XMM1 on the output.
# Q1 in the figure is a BC184BP; if it is not in the catalog — 2N3904 (also a small-signal npn).
QT='BC184BP'
import registry
if not registry.need([QT])[0][1]: QT='2N3904'
S=Scheme('diode_shaper',outdir=GALLERY)
P=S.part
P('V2','AC_VOLTAGE','1',6,25,subst={'.2':'10'},label='left')   # 1 (+) (6,25), 2 (6,31); 10 V amplitude, 1 kHz
P('R8','R','1',13,27,value='2k'); P('R3','R','1',15,25,rot=270,value='2.2k')
P('R4','R','1',15,13,rot=270,value='270'); P('R5','R','1',24,13,rot=270,value='220'); P('R6','R','1',33,13,rot=270,value='160')
P('D1','1N4148','A',22,20,rot=180,mirror=True)   # cathode up: K (22,14)
P('D2','1N4148','A',31,20,rot=180,mirror=True)
P('D3','1N4148','A',40,20,rot=180,mirror=True)
P('R1','R','1',23,20,rot=270,value='7.8k',label='bottom'); P('R2','R','1',32,20,rot=270,value='2.1k',label='bottom')
P('Q1',QT,'B',43,7,mirror=True)                   # base on the right: B (43,7), C (40,3), E (40,11)
P('R11','R','1',45,1,value='1k'); P('R12','R','1',45,9,value='1k')
P('U1','OPAMP_3T_VIRTUAL','IN+',52,25,rot=180,mirror=True,label='bottom')   # IN+ (52,25), IN− (52,21), OUT (62,23)
P('R10','R','1',71,25,value='1k')
v1=S.vcc(54,-1,volts=10)
g0=S.gnd(12,15); g1=S.gnd(6,33); g2=S.gnd(13,34); g3=S.gnd(48,18); g4=S.gnd(71,32)
y=S.meter('XMM1',75,23)
S.wires([
 # input
 [('V2','1'),J(13,25)],[J(13,25),('R8','1')],[J(13,25),('R3','1')],[('V2','2'),g1],[('R8','2'),g2],
 # line
 [('R3','2'),J(28,25)],[J(28,25),J(37,25)],[J(37,25),J(40,25)],[J(40,25),('U1','IN+')],
 # reference ladder: ground — R4 — R5 — R6 — Q1 emitter
 [('R4','1'),(12,13),g0],[('R4','2'),J(22,13)],[J(22,13),('R5','1')],[J(22,13),('D1','K')],
 [('R5','2'),J(31,13)],[J(31,13),('R6','1')],[J(31,13),('D2','K')],
 [('R6','2'),J(40,13)],[J(40,13),('D3','K')],[J(40,13),('Q1','E')],
 # diode branches
 [('D1','A'),('R1','1')],[('R1','2'),J(28,25)],[('D2','A'),('R2','1')],[('R2','2'),J(37,25)],[('D3','A'),J(40,25)],
 # follower Q1
 [('Q1','C'),(40,-1),J(45,-1)],[J(45,-1),('R11','1')],[J(45,-1),v1],
 [('R11','2'),J(45,7)],[J(45,7),('Q1','B')],[J(45,7),('R12','1')],[('R12','2'),(45,16),(48,16),g3],
 # output: op-amp follower
 [('U1','OUT'),J(64,23)],[J(64,23),(64,18),(50,18),(50,21),('U1','IN-')],[J(64,23),J(71,23)],
 [J(71,23),('R10','1')],[J(71,23),y],[('R10','2'),g4],
])
S.build()
