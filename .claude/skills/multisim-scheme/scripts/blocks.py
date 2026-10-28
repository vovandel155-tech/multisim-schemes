"""Block library — frequent scheme fragments (CMOS inverter, 2-input NAND, input protection, transistor switch, divider, RC…),
ready and verified: the parts and wires inside a block are already placed; named terminals stick out.

    inv=S.block('cmos_inv',33,14)                    # block: name, anchor cell (x, y) = cell of the block's anchor terminal
    S.wires([[x,inv['IN']],[inv['OUT'],y],[vdd,inv['VDD']],[inv['GND'],g]])
    S.block('cmos_inv',60,14,rot=90,mirror=True,names={'Q_p':'Q7','Q_n':'Q8'},label='left')

rot (0/90/180/270) and mirror — as for a part: they rotate and mirror the whole block around the anchor cell (left-right
mirror first, then rotation). Parts get free names (Q1, Q2… in order) — or your own: names=
{local name: name on the scheme}; local names are given in the block description ('Q_p' → first free Q…, 'R1' → R…). Block parameters (values, part types) are keyword arguments, see the list:
    python3 scripts/blocks.py            — blocks, their parameters and terminals
    python3 scripts/blocks.py show NAME  — build a block alone (preview and ngspice), see .msgen/preview/
A block terminal is a part terminal or a junction J(x,y) inside (2 block wires already meet there; an external wire is the third).

New block: a function f(B, parameters…) decorated with @block — inside, B.part/B.wire/B.J in local cells
(the anchor cell is (0,0)), just like in a scheme script; it returns a dict of terminals. A fragment of a good scheme is moved
here by shifting coordinates (subtract the anchor cell)."""
import sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))

BLOCKS={}
def block(f):
    BLOCKS[f.__name__]=f; return f

# ---------- geometry: left-right mirror first, then rotation (the way Multisim rotates parts) ----------
def xform(rot,mirror,x,y):
    if mirror: x=-x
    return {0:(x,y),90:(-y,x),180:(-x,-y),270:(y,-x)}[rot%360]

def compose(rot,mirror,prot,pmirror):
    """orientation of a part (prot, pmirror) inside a block rotated by (rot, mirror) → orientation on the scheme"""
    return ((rot+(-prot if mirror else prot))%360, bool(pmirror)!=bool(mirror))

_OFFS={}
def pin_offsets(kind,ref,rot=0,mirror=False):
    """offsets of the pins of part kind relative to pin ref at orientation (rot, mirror), in cells"""
    k=(kind,ref,rot,mirror)
    if k not in _OFFS:
        import scheme, geom
        b=scheme.Builder(scheme.sample(scheme.BASE_5_1A),[],tpl=scheme.doc(scheme.BASE_5_1A))
        p=b.place('X',scheme.tpl(kind),ref,50,50,rot=rot,mirror=mirror,label=None)
        _OFFS[k]={geom.dec(pn):(round(v[1][0]/scheme.G-50),round(v[1][1]/scheme.G-50)) for pn,v in p['pins'].items()}
    return _OFFS[k]

class Frame:
    """local block cells → scheme cells; local part names → names on the scheme"""
    def __init__(s,S,x,y,rot=0,mirror=False,names=None,label='auto'):
        assert rot%90==0,'rot — 0/90/180/270'
        s.S=S; s.x=x; s.y=y; s.rot=rot%360; s.mirror=mirror; s.names=dict(names or {}); s.label=label; s.map={}
    def pt(s,x,y):
        dx,dy=xform(s.rot,s.mirror,x,y); return (s.x+dx,s.y+dy)
    def J(s,x,y): return ('J',x,y)          # local junction; term() converts it to scheme cells
    def name(s,local):
        if local not in s.map:
            pre=local.split('_')[0] if '_' in local else local.rstrip('0123456789')   # 'Q_p' → Q, 'R1' → R
            n=s.names.get(local) or s.S.free_name(pre)
            s.map[local]=n
        return s.map[local]
    def part(s,local,kind,pin,x,y,rot=0,mirror=False,**kw):
        r,m=compose(s.rot,s.mirror,rot,mirror)
        kw.setdefault('label',s.label)
        return s.S.part(s.name(local),kind,pin,*s.pt(x,y),rot=r,mirror=m,**kw)
    def term(s,t):
        if isinstance(t,tuple) and len(t)==3 and t[0]=='J': return ('J',)+s.pt(t[1],t[2])
        if isinstance(t,tuple) and len(t)==2 and isinstance(t[0],str): return (s.name(t[0]),t[1])
        return s.pt(*t)
    def wire(s,*pts): s.S.wire(*[s.term(p) for p in pts])
    def wires(s,lst):
        for w in lst: s.wire(*w)
    def offs(s,kind,ref,rot=0,mirror=False): return pin_offsets(kind,ref,rot,mirror)   # in local cells

def place(S,name,x,y,rot=0,mirror=False,names=None,label='auto',**params):
    if name not in BLOCKS: raise KeyError('no block %s; available: %s'%(name,', '.join(sorted(BLOCKS))))
    B=Frame(S,x,y,rot,mirror,names,label)
    ports=BLOCKS[name](B,**params)
    return {k:B.term(v) for k,v in ports.items()}

# =====================================================================================================
# CMOS (PMOS/NMOS parts with a substrate pin; substrates tied to sources, as in the textbook)
# =====================================================================================================
@block
def cmos_inv(B):
    """CMOS inverter (fig. 5.17b, 5.19a): p-MOS Q_p on top, n-MOS Q_n below. Anchor — input IN (a junction, vertical wires
    to the gates). Terminals: IN (0,0), OUT (9,0), VDD (9,−13), GND (9,13). Occupies 0…11 × −13…13."""
    B.part('Q_p','PMOS','S',9,-11,rot=180,mirror=True)     # S (9,−11), G (6,−8), SUB (11,−7), D (9,−3)
    B.part('Q_n','NMOS','D',9,3)                           # D (9,3), G (6,8), SUB (11,7), S (9,11)
    B.wires([
     [B.J(0,0),(0,-8),('Q_p','G')],[B.J(0,0),(0,8),('Q_n','G')],
     [('Q_p','S'),B.J(9,-13)],[('Q_p','SUB'),(11,-13),B.J(9,-13)],
     [('Q_p','D'),B.J(9,0)],[B.J(9,0),('Q_n','D')],
     [('Q_n','S'),B.J(9,13)],[('Q_n','SUB'),(11,13),B.J(9,13)],
    ])
    return dict(IN=B.J(0,0),OUT=B.J(9,0),VDD=B.J(9,-13),GND=B.J(9,13))

@block
def cmos_nand2(B):
    """CMOS 2-input NAND (fig. 5.22a): p-MOS Q_p1 (gate B) ‖ Q_p2 (gate A) from VDD to the output, n-MOS Q_n1 (A) — Q_n2 (B)
    in series to ground. Anchor — VDD (0,0). Terminals: A (7,34) and B (−7,46) — come from the left, OUT (14,23),
    GND (19,51). The B vertical crosses the A line without a connection (as in the textbook). Occupies −7…19 × 0…51."""
    B.part('Q_p1','PMOS','S',0,3,rot=180,mirror=True)      # S (0,3), G (−3,6), SUB (2,7), D (0,11)
    B.part('Q_p2','PMOS','S',14,3,rot=180,mirror=True)
    B.part('Q_n1','NMOS','D',14,29)                        # D (14,29), G (11,34), SUB (16,33), S (14,37)
    B.part('Q_n2','NMOS','D',14,41)
    B.wires([
     [B.J(0,0),B.J(0,1)],[B.J(0,0),(14,0),B.J(14,1)],
     [('Q_p1','S'),B.J(0,1)],[('Q_p1','SUB'),(2,1),B.J(0,1)],[('Q_p2','S'),B.J(14,1)],[('Q_p2','SUB'),(16,1),B.J(14,1)],
     [('Q_p1','D'),(0,23),B.J(14,23)],[('Q_p2','D'),B.J(14,23)],[B.J(14,23),('Q_n1','D')],
     [B.J(7,34),('Q_n1','G')],[B.J(7,34),(7,6),('Q_p2','G')],
     [B.J(-7,46),('Q_n2','G')],[B.J(-7,46),(-7,6),('Q_p1','G')],
     [('Q_n1','S'),('Q_n2','D')],
     [('Q_n1','SUB'),(19,33),B.J(19,45)],[('Q_n2','SUB'),B.J(19,45)],[B.J(19,45),B.J(19,51)],
     [('Q_n2','S'),(14,51),B.J(19,51)],
    ])
    return dict(VDD=B.J(0,0),A=B.J(7,34),B=B.J(-7,46),OUT=B.J(14,23),GND=B.J(19,51))

@block
def cmos_nor2(B):
    """CMOS 2-input NOR: p-MOS Q_p1 (gate A) — Q_p2 (B) in series from VDD, n-MOS Q_n1 (A) ‖ Q_n2 (B) to ground.
    Anchor — VDD (0,0). Terminals: A (−6,34) and B (−9,16) — come from the left, OUT (12,25), GND (0,44). The gate lines
    cross without a connection. p-MOS substrates to VDD, n-MOS substrates to their sources. Occupies −9…14 × 0…44."""
    B.part('Q_p1','PMOS','S',0,3,rot=180,mirror=True)      # S (0,3), G (−3,6), SUB (2,7), D (0,11)
    B.part('Q_p2','PMOS','S',0,13,rot=180,mirror=True)     # S (0,13), G (−3,16), SUB (2,17), D (0,21)
    B.part('Q_n1','NMOS','D',0,29)                         # D (0,29), G (−3,34), SUB (2,33), S (0,37)
    B.part('Q_n2','NMOS','D',12,29)                        # D (12,29), G (9,34), SUB (14,33), S (12,37)
    B.wires([
     [B.J(0,0),B.J(0,1)],[('Q_p1','S'),B.J(0,1)],[('Q_p1','SUB'),(2,1),B.J(0,1)],
     [B.J(0,0),(5,0),(5,17),('Q_p2','SUB')],
     [('Q_p1','D'),('Q_p2','S')],
     [('Q_p2','D'),B.J(0,25)],[B.J(0,25),('Q_n1','D')],[B.J(0,25),B.J(12,25)],[B.J(12,25),('Q_n2','D')],
     [B.J(-6,34),('Q_n1','G')],[B.J(-6,34),(-6,6),('Q_p1','G')],
     [B.J(-9,16),('Q_p2','G')],[B.J(-9,16),(-9,42),(6,42),(6,34),('Q_n2','G')],
     [('Q_n1','S'),B.J(0,39)],[('Q_n1','SUB'),(2,39),B.J(0,39)],[B.J(0,39),B.J(0,44)],
     [('Q_n2','S'),B.J(12,39)],[('Q_n2','SUB'),(14,39),B.J(12,39)],[B.J(12,39),(12,44),B.J(0,44)],
    ])
    return dict(VDD=B.J(0,0),A=B.J(-6,34),B=B.J(-9,16),OUT=B.J(12,25),GND=B.J(0,44))

@block
def cmos_protect(B,r='1k'):
    """CMOS input protection (fig. 5.18, 5.21): diodes D1/D2 — resistor R — diodes D3/D4; upper diodes — cathode to VDD,
    lower ones — anode to ground. Anchor — input IN (0,0). Terminals: IN (0,0), OUT (14,0), VDD (14,−14), GND (14,15).
    Occupies 0…14 × −14…15."""
    B.part('D1','D','A',0,-5); B.part('D2','D','A',0,11)        # cathodes (0,−11) and (0,5)
    B.part('D3','D','A',14,-5); B.part('D4','D','A',14,11)
    B.part('R1','R','1',5,0,rot=270,value=r)                    # 1 (5,0), 2 (10,0)
    B.wires([
     [B.J(0,0),('D1','A')],[B.J(0,0),('D2','K')],[B.J(0,0),('R1','1')],
     [('R1','2'),B.J(14,0)],[B.J(14,0),('D3','A')],[B.J(14,0),('D4','K')],
     [('D1','K'),(0,-14),B.J(14,-14)],[('D3','K'),B.J(14,-14)],
     [('D2','A'),(0,15),B.J(14,15)],[('D4','A'),B.J(14,15)],
    ])
    return dict(IN=B.J(0,0),OUT=B.J(14,0),VDD=B.J(14,-14),GND=B.J(14,15))

# =====================================================================================================
# Bipolar and passive
# =====================================================================================================
@block
def npn_switch(B,q='Q',rb='1k',rc='1k'):
    """npn switch (type q: 'Q' = 2N2222, '2N3904', 'BC547B', 'FZT1049A'…): R1 (rb) into the base, R2 (rc) from the collector
    to the supply, emitter to ground. Anchor — input IN = R1.1 (0,0). Terminals: IN, OUT (junction above the collector),
    VCC (R2.1, top), GND (emitter, bottom). The height follows the transistor pins."""
    o=B.offs(q,'B'); cx,cy=10+o['C'][0],o['C'][1]
    B.part('R1','R','1',0,0,rot=270,value=rb)                   # 2 (5,0)
    B.part('Q1',q,'B',10,0)
    B.part('R2','R','1',cx,cy-7,value=rc)                       # 2 (cx, cy−2)
    B.wires([[('R1','2'),('Q1','B')],[('R2','2'),B.J(cx,cy-1)],[B.J(cx,cy-1),('Q1','C')]])
    return dict(IN=('R1','1'),OUT=B.J(cx,cy-1),VCC=('R2','1'),GND=('Q1','E'))

@block
def push_pull(B,npn='Q',pnp='P'):
    """push-pull emitter follower: npn Q1 on top (collector to VCC), pnp Q2 below (collector to VEE/ground),
    bases from the input, emitters are the output. Types: npn 'Q'/'2N3904'/'TIP121G'…, pnp 'P'/'2N3906'/'TIP127G'… (the pnp
    is placed emitter-up automatically). Anchor — input IN (0,0). Terminals: IN, OUT (junction at the emitters), VCC, VEE."""
    on=B.offs(npn,'B')
    pr,pm=next((r,m) for r,m in ((0,False),(180,True)) if B.offs(pnp,'B',r,m)['E'][1]<B.offs(pnp,'B',r,m)['C'][1])
    op=B.offs(pnp,'B',pr,pm)
    b1=(3,-1-on['E'][1]); b2=(3,1-op['E'][1])                   # emitters on rows −1 and +1
    e1=(b1[0]+on['E'][0],-1); e2=(b2[0]+op['E'][0],1); xo=max(e1[0],e2[0])
    B.part('Q1',npn,'B',*b1)
    B.part('Q2',pnp,'B',*b2,rot=pr,mirror=pm)
    B.wires([[B.J(0,0),(0,b1[1]),('Q1','B')],[B.J(0,0),(0,b2[1]),('Q2','B')]])
    for q,e in (('Q1',e1),('Q2',e2)):
        B.wire((q,'E'),*([] if e[0]==xo else [(e[0],0)]),B.J(xo,0))
    return dict(IN=B.J(0,0),OUT=B.J(xo,0),VCC=('Q1','C'),VEE=('Q2','C'))

@block
def divider(B,r1='10k',r2='10k'):
    """voltage divider: R1 on top, R2 below. Anchor — top TOP = R1.1 (0,0). Terminals: TOP, MID (0,6) —
    the junction between the resistors, BOT = R2.2 (0,12)."""
    B.part('R1','R','1',0,0,value=r1); B.part('R2','R','1',0,7,value=r2)
    B.wires([[('R1','2'),B.J(0,6)],[B.J(0,6),('R2','1')]])
    return dict(TOP=('R1','1'),MID=B.J(0,6),BOT=('R2','2'))

@block
def rc_lowpass(B,r='1k',c='100n'):
    """RC low-pass filter: R1 horizontal, C1 down to ground. Anchor — input IN = R1.1 (0,0).
    Terminals: IN, OUT (8,0) — a junction, GND = C1.2 (8,7)."""
    B.part('R1','R','1',0,0,rot=270,value=r); B.part('C1','C','1',8,2,value=c)
    B.wires([[('R1','2'),B.J(8,0)],[B.J(8,0),('C1','1')]])
    return dict(IN=('R1','1'),OUT=B.J(8,0),GND=('C1','2'))

@block
def rc_highpass(B,r='10k',c='100n'):
    """RC high-pass filter: C1 horizontal, R1 down to ground. Anchor — input IN = C1.1 (0,0).
    Terminals: IN, OUT (8,0) — a junction, GND = R1.2 (8,7)."""
    B.part('C1','C','1',0,0,rot=270,value=c); B.part('R1','R','1',8,2,value=r)
    B.wires([[('C1','2'),B.J(8,0)],[B.J(8,0),('R1','1')]])
    return dict(IN=('C1','1'),OUT=B.J(8,0),GND=('R1','2'))

@block
def led_r(B,led='LED_red',r='330'):
    """LED with a current-limiting resistor: R1 horizontal, the LED down (anode on top).
    Anchor — input IN = R1.1 (0,0). Terminals: IN, GND = cathode (9,8). Multisim LED threshold — Ion ≈ 5 mA:
    at 5 V use r ≤ 330 Ohm (green/blue — less, 150 Ohm)."""
    B.part('R1','R','1',0,0,rot=270,value=r)                   # 2 (5,0)
    B.part('LED1',led,'A',9,2)                                  # K (9,8)
    B.wire(('R1','2'),(9,0),('LED1','A'))
    return dict(IN=('R1','1'),GND=('LED1','K'))

# =====================================================================================================
def _show(name,**params):
    """a block alone: each terminal goes to a switch/supply/ground/multimeter by its name (for the preview and ngspice)"""
    from scheme import Scheme
    S=Scheme('Block_'+name,outdir=os.environ.get('MSGEN_OUT') or os.path.join(os.environ.get('TMPDIR','/tmp'),'msgen_blocks'))
    p=S.block(name,30,30,**params)
    k=0; ins=[S.pos(t)[0] for n,t in p.items() if n not in ('VDD','VCC','TOP','GND','VEE','BOT','OUT','MID')]
    for n,t in p.items():
        x,y=S.pos(t)
        if n in ('VDD','VCC','TOP'): S.wire(S.vcc(x,y-5),t)
        elif n in ('GND','VEE','BOT'): S.wire(t,S.gnd(x,y+3))
        elif n in ('OUT','MID'): S.wire(t,S.meter('XMM1',x+6,y))
        else:   # input switches left of the leftmost input, so that no block line runs through them
            k+=1; S.wire(S.switch('S%d'%k,min(ins)-6-10*(k-1),y),t)
    S.build()
    return S

if __name__=='__main__':
    import inspect
    if sys.argv[1:2]==['show']:
        _show(sys.argv[2],**dict(a.split('=',1) for a in sys.argv[3:]))
    else:
        for n,f in BLOCKS.items():
            sig=inspect.signature(f); ps=', '.join('%s=%r'%(k,v.default) for k,v in list(sig.parameters.items())[1:])
            print('%s(%s)\n    %s\n'%(n,ps,' '.join(f.__doc__.split())))
