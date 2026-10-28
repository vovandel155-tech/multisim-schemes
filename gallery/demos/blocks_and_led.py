import sys, os; GALLERY=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,os.path.join(GALLERY,'..','..','.claude','skills','multisim-scheme','scripts'))
from scheme import *
# Block library demo (scripts/blocks.py): a scheme made almost entirely of blocks and wires.
# Top: S1, S2 → cmos_nand2 → cmos_inv = AND (multimeter XMM1: 5 V only with S1 = S2 = 1).
# Bottom: S3 → npn_switch, led_r in the collector (LED from VCC through 330 Ohm): the LED lights with S3 = 1.
S=Scheme('blocks_and_led',outdir=GALLERY)
n=S.block('cmos_nand2',20,0)                     # VDD (20,0), A (27,34), B (13,46), OUT (34,23), GND (39,51)
i=S.block('cmos_inv',44,23)                      # IN (44,23), OUT (53,23), VDD (53,10), GND (53,36)
k=S.block('npn_switch',13,75)                    # IN (13,75), OUT (26,70), VCC (26,64), GND — emitter
d=S.block('led_r',28,58)                         # IN (28,58), GND — cathode (37,66)
x1=S.switch('S1',5,34); x2=S.switch('S2',-3,46); x3=S.switch('S3',5,75)
y=S.meter('XMM1',60,23)
S.wires([
 [S.vcc(20,-3),n['VDD']],[x1,n['A']],[x2,n['B']],[n['GND'],S.gnd(39,54)],
 [n['OUT'],i['IN']],[S.vcc(53,7),i['VDD']],[i['GND'],S.gnd(53,39)],[i['OUT'],y],
 [x3,k['IN']],[k['GND'],S.gnd(26,82)],
 [S.vcc(26,55),J(26,58)],[J(26,58),k['VCC']],[J(26,58),d['IN']],[d['GND'],(37,70),k['OUT']],
])
S.build()
