import sys, os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from scheme import *
# Template for donors.vbs: placeholders of different kinds, no wires — ReplaceComponent replaces a placeholder with a part
# of the same kind from the Multisim database and the file is saved as a donor. Placeholders (RefDes — for the donor list):
#   Q1 npn (2N3904), Q2 pnp (2N3906), M1 n-MOS (IRFD110), M2 p-MOS (NTA4151PT1G), J1 n-JFET (2N5484),
#   D1 diode (1N4148), Z1 LED (LED_red), R1 resistor, C1 capacitor, L1 inductor,
#   U1 5-pin op-amp (LM324AD), U2 7-pin op-amp (741), U3 digital IC (7404N), U4 timer (LM555CM), U5 regulator (LM317K)
S=Scheme('template_replace',outdir=SAMPLES)   # samples/template_replace.ms14
P=S.part
P('Q1','2N3904','B',0,0); P('Q2','2N3906','B',14,0); P('M1','IRFD110','G',28,0); P('M2','NTA4151PT1G','G',42,0)
P('J1','2N5484','G',62,0)
P('D1','1N4148','A',0,20); P('Z1','LED_red','A',12,20); P('R1','R','1',24,20,value='1k')
P('C1','C','1',34,20,value='1u'); P('L1','INDUCTOR_VIRTUAL','1',44,20)
P('U1','LM324AD','1IN+',8,40); P('U2','741','IN+',30,40); P('U3','7404N','1A',50,40)
P('U4','LM555CM','CON',8,70); P('U5','LM317K','IN',36,70)
S.build()
