import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Analyses: Single Frequency AC in Batched (Simulate → Analyses and Simulation → Batched → Run).
# The bias circuit of batched_op plus input VIN → C1 10u → base; the output is the collector.
S=Scheme('batched_phasor',outdir=GALLERY)
P=S.part
P('V1','DC_POWER','1',0,10)                         # 1 «+» (0,10), 2 «−» (0,14)
P('VIN','AC_VOLTAGE','1',8,19)                      # 1 (8,19), 2 (8,25)
P('C1','C','1',8,16,rot=270,value='10u')            # 1 (8,16), 2 (13,16)
P('R1','R','1',16,6,value='47k'); P('R2','R','1',16,21,value='10k')
P('RC','R','1',28,5,value='2.2k'); P('RE','R','1',28,23,value='1k')
P('Q1','Q','C',28,12)                               # C (28,12), B (25,16), E (28,20)
g=S.gnd(16,34)
S.wires([
 [('V1','1'),(0,2),J(16,2)],[J(16,2),('R1','1')],[J(16,2),(28,2),('RC','1')],
 [('VIN','1'),('C1','1')],[('C1','2'),J(16,16)],
 [('R1','2'),J(16,16)],[J(16,16),('R2','1')],[J(16,16),('Q1','B')],
 [('RC','2'),('Q1','C')],[('Q1','E'),('RE','1')],
 [('V1','2'),(0,31),J(8,31)],[('VIN','2'),J(8,31)],[J(8,31),J(16,31)],
 [('R2','2'),J(16,31)],[J(16,31),g],[J(16,31),(28,31),('RE','2')],
])
# nets of this build: 2 — input (VIN +), 3 — base, 4 — collector (output), 5 — emitter.
# VIN: AC analysis magnitude 1 V, phase 0. Expected at 1 kHz (ngspice): V(2) 1 V ∠0°, V(4) 2.138 V ∠−179.9°,
# gain V(4)/V(2) 2.138 ∠−179.9° = 6.598 dB, I(VIN) 127.8 uA ∠−179.8°, V(2)/I(VIN) 7.822 kOhm ∠179.8°
# (the sign: SPICE counts the current flowing into the + pin, so the input impedance comes out at 180°).
S.phasor(['V(2)','V(4)','V(4)/V(2)','db(V(4)/V(2))','I(VIN)','V(2)/I(VIN)'],freq=1000,title='Gain at 1 kHz')
S.build()
