import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Analyses: a full Batched list (Simulate → Analyses and Simulation → Batched → Run).
# The batched_phasor stage with C1 1u at the input (low cut-off) and CL 10n on the collector (high cut-off).
S=Scheme('batched_all',outdir=GALLERY)
P=S.part
P('V1','DC_POWER','1',0,10)                         # 1 «+» (0,10), 2 «−» (0,14)
P('VIN','AC_VOLTAGE','1',8,19,subst={'.2':'Uin','UinVpk':'Uin'})   # 1 (8,19), 2 (8,25); amplitude = circuit parameter Uin
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
# nets of this build: 1 — V1+, 2 — input (VIN +, AC magnitude 1 V, 0.2 Vpk 1 kHz sine), 3 — base, 4 — collector
# (output), 5 — emitter. VIN amplitude is the circuit parameter Uin = 0.2 V. Expected (ngspice):
#  1: V(1) 12, V(2) 0, V(3) 2.039, V(4) 8.913, V(5) 1.411, V(4)-V(5) 7.502 V, I(V1) −1.615 mA;
#  2: |V(4)| = gain 2.117 (6.515 dB), |V(2)/I(VIN)| 7.825 kOhm;
#  3: maximum 6.57 dB near 380 Hz, −3 dB at 20.3 Hz and 7.29 kHz, 701 points;
#  4: DC 8.914 V, 1st harmonic 0.423 V (VIN 0.2 Vpk), THD ≈ 0.035 %;
#  5: inoise_total 0.751 uV, onoise_total 1.067 uV (20 Hz…20 kHz); 6: the same as spectral density, 301 points;
#  7: V(4) over 45…50 ms, max/min: Uin 0.1 — 9.125/8.702 V, 0.2 — 9.337/8.490, 0.5 — 9.972/7.857, 1 — 11.024/6.807,
#     2 — 12.000/4.745 V (the top is clipped at V1: the transistor cuts off).
S.op(['V(1)','V(2)','V(3)','V(4)','V(5)','V(4)-V(5)','I(V1)'],title='1 Operating point')
S.phasor(['V(4)','V(4)/V(2)','db(V(4)/V(2))','V(2)/I(VIN)'],freq=1000,title='2 Gain at 1 kHz')
S.ac(['V(4)'],fstart=1,fstop=10e6,points=100,vscale='db',title='3 Frequency response')
S.fourier(['V(4)'],freq=1000,harmonics=9,tstop=0.05,tmax=1e-6,title='4 Harmonics')
S.noise('VIN',4,0,fstart=20,fstop=20e3,points=100,title='5 Total noise')
S.noise('VIN',4,0,fstart=20,fstop=20e3,points=100,spectrum=True,title='6 Noise spectrum')
S.param('Uin',0.2)                                  # VIN amplitude, V (peak)
S.psweep(['V(4)'],'Uin',[0.1,0.2,0.5,1,2],tstart=0.045,tstop=0.05,tmax=1e-6,ic='dcop',title='7 Output clipping')
S.build()
