import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Fig. 5.19b — 1/6 CD4050B (buffer, y = x): input diodes to ground only (D1 — R1 — D2), then two inverters
# in a row: Q1, Q2 and Q3, Q4 (the first output goes straight to the second gates); on the right D3 between VDD and ground (its wire
# crosses the output line without a connection, as in the textbook). VDD bus on top, common ground bus at the bottom (the GND symbol under
# the second inverter — a 4-wire junction, as in the textbook). Diodes cathode up. Substrates tied to sources. R1 = 1k.
S=Scheme('fig5_19b_cd4050b',outdir=GALLERY)
P=S.part
for n,x in (('D1',10),('D2',24),('D3',63)): P(n,'D','A',x,24)    # cathode (x,18), anode (x,24)
P('R1','R','1',15,14,rot=270,value='1k')
for p,n,x in (('Q1','Q2',42),('Q3','Q4',57)):
    P(p,'PMOS','S',x,3,rot=180,mirror=True)      # S (x,3), G (x-3,6), SUB (x+2,7), D (x,11)
    P(n,'NMOS','D',x,17)                         # D (x,17), G (x-3,22), SUB (x+2,21), S (x,25)
vdd=S.vcc(34,0); g=S.gnd(57,31)
x=S.switch('S1',0,14)
y=S.meter('XMM1',69,14)
W=[
 # VDD bus
 [vdd,J(42,0)],[J(42,0),J(57,0)],[J(57,0),(63,0),('D3','K')],
 # input: D1 — R1 — D2 — gates of the first inverter
 [x,J(10,14)],[J(10,14),('D1','K')],[J(10,14),('R1','1')],
 [('R1','2'),J(24,14)],[J(24,14),('D2','K')],[J(24,14),J(33,14)],
 [J(33,14),(33,6),('Q1','G')],[J(33,14),(33,22),('Q2','G')],
 # first inverter output — gates of the second one
 [('Q1','D'),J(42,14)],[J(42,14),('Q2','D')],[J(42,14),J(48,14)],
 [J(48,14),(48,6),('Q3','G')],[J(48,14),(48,22),('Q4','G')],
 # output
 [('Q3','D'),J(57,14)],[J(57,14),('Q4','D')],[J(57,14),y],
 # common ground bus
 [('D1','A'),(10,29),J(24,29)],[('D2','A'),J(24,29)],[J(24,29),J(42,29)],[J(42,29),J(57,29)],[J(57,29),g],
 [J(57,29),(63,29),('D3','A')],
]
for p,n,x in (('Q1','Q2',42),('Q3','Q4',57)):    # sources and substrates to the buses
    W+=[[(p,'S'),J(x,1)],[(p,'SUB'),(x+2,1),J(x,1)],[J(x,1),J(x,0)],
        [(n,'S'),J(x,27)],[(n,'SUB'),(x+2,27),J(x,27)],[J(x,27),J(x,29)]]
S.wires(W)
S.build()
