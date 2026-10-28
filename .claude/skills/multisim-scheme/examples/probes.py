import sys, os; sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),'..','scripts'))
from scheme import *
# Multisim probes (S.probe, templates — sample_probes / sample_probe_vi) on the scheme of catalog_opamp_led.py.
# Catalog parts: the elements are cloned from Multisim samples (samples/ni/, harvest.py), not synthesized.
# Left — op-amp 741 (non-inverting amplifier ×2, supply VCC +5 V / VEE −5 V): S1 → divider R1 40k / R2 10k (1 V) →
# IN+; feedback R3 10k / R4 10k; output — XMM1 (0 or 2 V). Right — a 2N3904 switch: S2 → R5 10k → base,
# a blue LED LED1 with R6 150 from VCC in the collector — lights with S2 = 1
# (the Multisim LED turn-on threshold is Ion = 5 mA: with 330 Ohm it got 4.8 mA and stayed dark).
S=Scheme('probes')
P=S.part
P('U1','741','IN+',20,10)                         # IN+ (20,10), IN- (20,14), VS+ (24,6), VS- (24,18), OUT (32,12)
P('R1','R','1',6,10,rot=270,value='40k'); P('R2','R','1',15,13,value='10k')
P('R3','R','1',21,26,rot=270,value='10k'); P('R4','R','1',18,29,value='10k')
P('VEE1','VEE','VEE',24,21,rot=180,refdes='VEE',subst={'-15':'-5'})   # the catalog VEE donor defaults to -15 V
vcc=S.vcc(24,3); g=S.gnd(18,39)
x1=S.switch('S1',2,10)
y=S.meter('XMM1',38,12)
P('Q1','2N3904','B',62,14)                        # B (62,14), C (65,10), E (65,18)
P('LED1','LED_blue','A',65,2)                     # A (65,2), K (65,8)
P('R5','R','1',55,14,rot=270,value='10k'); P('R6','R','1',65,-5,value='150')
vcc2=S.vcc(65,-7); g2=S.gnd(65,21)
x2=S.switch('S2',52,14)
S.wires([
 [x1,('R1','1')],[('R1','2'),J(15,10)],[J(15,10),('U1','IN+')],[J(15,10),('R2','1')],
 [vcc,('U1','VS+')],[('U1','VS-'),('VEE1','VEE')],
 [('U1','IN-'),(18,14),J(18,26)],[J(18,26),('R3','1')],[J(18,26),('R4','1')],
 [('U1','OUT'),J(34,12)],[J(34,12),y],[J(34,12),(34,26),('R3','2')],
 [('R2','2'),(15,36),J(18,36)],[('R4','2'),J(18,36)],[J(18,36),g],
 [x2,('R5','1')],[('R5','2'),('Q1','B')],
 [vcc2,('R6','1')],[('R6','2'),('LED1','A')],[('LED1','K'),('Q1','C')],[('Q1','E'),g2],
])
# probes of every kind: the tip is in a wire cell (for P — on an element pin)
S.probe('PR1',13,10,'V')                          # op-amp input (1 V)
S.probe('PR2',4,10,'I')                           # current from switch S1 through R1
S.probe('PR3',65,-5,'P')                          # power of R6 (on pin 1)
S.probe('PR4',65,9,'VI')                          # LED — Q1 collector: voltage and current
S.probe('Ref1',19,14,'REF')                       # reference point — input IN−
S.probe('PR5',36,12,'V',ref='Ref1')               # op-amp output relative to IN− (differential)
S.probe('PR6',61,14,'D')                          # digital — Q1 base
S.build()
