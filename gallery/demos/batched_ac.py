import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Analyses: AC Sweep in Batched (Simulate → Analyses and Simulation → Batched → Run).
# The batched_phasor stage with C1 1u at the input (low cut-off) and CL 10n on the collector (high cut-off).
S=Scheme('batched_ac',outdir=GALLERY)
P=S.part
P('V1','DC_POWER','1',0,10)                         # 1 «+» (0,10), 2 «−» (0,14)
P('VIN','AC_VOLTAGE','1',8,19)                      # 1 (8,19), 2 (8,25)
P('C1','C','1',8,16,rot=270,value='1u')             # 1 (8,16), 2 (13,16)
P('R1','R','1',16,6,value='47k'); P('R2','R','1',16,21,value='10k')
P('RC','R','1',28,4,value='2.2k'); P('RE','R','1',28,23,value='1k')
P('Q1','Q','C',28,12)                               # C (28,12), B (25,16), E (28,20)
P('CL','C','1',40,14,value='10n')                   # 1 (40,14), 2 (40,19)
g=S.gnd(16,34)
S.wires([
 [('V1','1'),(0,2),J(16,2)],[J(16,2),('R1','1')],[J(16,2),(28,2),('RC','1')],
 [('VIN','1'),('C1','1')],[('C1','2'),J(16,16)],
 [('R1','2'),J(16,16)],[J(16,16),('R2','1')],[J(16,16),('Q1','B')],
 [('RC','2'),J(28,10)],[J(28,10),('Q1','C')],[J(28,10),(40,10),('CL','1')],[('Q1','E'),('RE','1')],
 [('V1','2'),(0,31),J(8,31)],[('VIN','2'),J(8,31)],[J(8,31),J(16,31)],
 [('R2','2'),J(16,31)],[J(16,31),g],[J(16,31),J(28,31)],[J(28,31),('RE','2')],[J(28,31),(40,31),('CL','2')],
])
# nets of this build: 2 — input (VIN +, AC magnitude 1 V), 4 — collector (output). V(4) is the gain itself.
# Expected (ngspice, 1 Hz…10 MHz, 100 points/decade, 701 points): maximum 6.57 dB near 380 Hz, 6.51 dB at 1 kHz,
# −3 dB at 20.3 Hz (C1 with the input resistance) and 7.29 kHz (CL with RC). Vertical scale — Decibel.
S.ac(['V(4)'],fstart=1,fstop=10e6,points=100,vscale='db',title='Frequency response')
S.build()
