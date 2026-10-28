"""High-level scheme assembly: a script only describes the elements and wires, everything else happens here.

    from scheme import *
    S=Scheme('CMOS_inverter')
    S.part('Q1','PMOS','S',10,0,rot=180,mirror=True)     # element: type, anchor pin, cell (x, y)
    x=S.switch('S1',0,12)                                # switch to VCC/ground (pin 2 at (0,12)) → terminal
    S.wire(x,J(6,12),('Q1','G'))                          # wire: terminal/junction J(x,y) … bend (x,y) … terminal
    S.build()

build(): file base by element types → placement → wires → 'auto' labels → sheet size and centering
by the bounding box → finalize → checks (ID references, overlaps, density, PNG preview, truth table in ngspice).
Element types — KINDS; pins and sizes — `python3 <skill>/scripts/scheme.py pins`."""
import sys, os, math, time
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from msgen import *
import geom, validate

J=lambda x,y:('J',x,y)
G=9   # px per cell

_DOCS={}
def doc(name):
    """a sample (unpacked XML) — parsed once per process; '@name' — a derived base (DERIVED)"""
    if name not in _DOCS: _DOCS[name]=Doc(base_path(name))
    return _DOCS[name]

# derived bases: a sample with a subcircuit whose sheet is replaced by the main sheet of another file (a hierarchical block)
# name: (sample, subcircuit name in it, sheet source file, connector renaming)
BLOCK_PINS={'\u0411':'B','\u041a':'C','\u042d1':'E1','\u042d2':'E2'}   # connectors of the hierarchical blocks in the samples (named in Cyrillic) → instance pin names
def _multi(src,nm):
    def make(D): transplant_sheet(D,'MultiNPN4',Doc(sample(src)),rename=BLOCK_PINS,new_title=nm)
    return make
def _schottky_multi(D):
    """two subcircuits in one file: SchottkyNPN (sheet from sample_schottky_subckt) and MultiSchottky2"""
    copy_sheet(D,'MultiNPN4','SchottkyNPN')
    transplant_sheet(D,'SchottkyNPN',sheet_parts(Doc(sample('sample_schottky_subckt')),'SchottkyNPN'))
    _multi('multi_emitter_shotki','MultiSchottky2')(D)
DERIVED={   # name: (base sample, modification)
 'MultiNPN2':('sample_multiemitter',_multi('Multi_emitter_npn','MultiNPN2')),
 'MultiSchottky2':('sample_multiemitter',_multi('multi_emitter_shotki','MultiSchottky2')),
 'SchottkyMulti2':('sample_multiemitter',_schottky_multi),
}
COMBINED={frozenset({'sample_schottky_subckt','@MultiSchottky2'}):'@SchottkyMulti2'}   # several subcircuit kinds in one scheme
def base_path(name):
    """XML path of a base: a sample or ('@name') a derived base — built on first use in a process"""
    if not name.startswith('@'): return sample(name)
    nm=name[1:]; path=os.path.join(CACHE,nm+'.xml')
    if nm not in _DERIVED_DONE:
        smp,make=DERIVED[nm]; D=Doc(sample(smp)); make(D)
        os.makedirs(CACHE,exist_ok=True); open(path,'wb').write(serialize(D.root)); _DERIVED_DONE.add(nm)
    return path
_DERIVED_DONE=set()

BASE_5_1A='base_5_1a'
# models for elements without a sample (LTspice standard.bjt / standard.dio without parameters SPICE3 lacks)
MODEL_2N3904='npn\n+IS=1e-14 VAF=100 BF=300 IKF=0.4 XTB=1.5 BR=4 CJC=4e-12 CJE=8e-12\n+RB=20 RC=0.1 RE=0.1 TR=250e-9 TF=350e-12 ITF=1 VTF=2 XTF=3'
MODEL_2N3906='pnp\n+IS=1e-14 VAF=100 BF=200 IKF=0.4 XTB=1.5 BR=4 CJC=4.5e-12 CJE=10e-12\n+RB=20 RC=0.1 RE=0.1 TR=250e-9 TF=350e-12 ITF=1 VTF=2 XTF=3'
MODEL_1N4148X4='D\n+IS=2.52e-9 RS=2.272 N=7.008 CJO=1e-12 M=0.4 TT=20e-9 BV=300'   # 4 × 1N4148 in series
# Darlington transistors — a subcircuit right in the template: pins C B E, inside — as in the LTspice drawing:
# two transistors, 8 kOhm base–emitter of the input one, 120 Ohm base–emitter of the output one, reverse diode emitter–collector
SUBCKT_TIP121=('x%p %tC %tB %tE TIP121_%p\n.subckt TIP121_%p 1 2 3\nq1 1 2 4 QD%p\nq2 1 4 3 QO%p\nr1 2 4 8k\nr2 4 3 120\n'
  'd1 3 1 DD%p\n.model QD%p npn(IS=1e-13 BF=150 VAF=100 RB=10 RC=1 CJE=30p CJC=15p TF=1n TR=100n)\n'
  '.model QO%p npn(IS=5e-12 BF=60 VAF=100 IKF=4 RB=2 RC=0.05 RE=0.02 CJE=300p CJC=150p TF=20n TR=1u)\n'
  '.model DD%p d(IS=1e-12 RS=0.05 BV=100)\n.ends\n')
SUBCKT_TIP127=('x%p %tC %tB %tE TIP127_%p\n.subckt TIP127_%p 1 2 3\nq1 1 2 4 QD%p\nq2 1 4 3 QO%p\nr1 2 4 8k\nr2 4 3 120\n'
  'd1 1 3 DD%p\n.model QD%p pnp(IS=1e-13 BF=150 VAF=100 RB=10 RC=1 CJE=30p CJC=15p TF=1n TR=100n)\n'
  '.model QO%p pnp(IS=5e-12 BF=60 VAF=100 IKF=4 RB=2 RC=0.05 RE=0.02 CJE=300p CJC=150p TF=20n TR=1u)\n'
  '.model DD%p d(IS=1e-12 RS=0.05 BV=100)\n.ends\n')
# type: (sample, element name in it, value template, base subcircuit or None)
KINDS={
 'R':   lambda: (doc(BASE_5_1A),'&ASCR3','4k'),                     # resistor (vertical: 1 on top, 2 below)
 'Q':   lambda: (doc(BASE_5_1A),'&ASCQ3',None),                     # npn 2N2222
 'D':   lambda: (doc(BASE_5_1A),'&ASCD1',None),                     # diode 1BH62
 'DS':  lambda: (doc('base_5_1g'),'&ASCD4',None),                   # Schottky diode 10BQ015
 'QS':  lambda: (SchottkyLib(doc('sample_schottky_subckt'),'&ASCSC1',(doc(BASE_5_1A),'&ASCQ3')),'QS',None),
 'QM':  lambda: (MultiEmitterLib(doc('sample_multiemitter'),'&ASCSC1',(doc(BASE_5_1A),'&ASCQ3')),'QM',None),
 'QM2': lambda: (MultiEmitterLib(doc('@MultiNPN2'),'&ASCSC1',(doc(BASE_5_1A),'&ASCQ3'),n=2),'QM2',None),
 'QMS2':lambda: (MultiEmitterLib(doc('@MultiSchottky2'),'&ASCSC1',(doc(BASE_5_1A),'&ASCQ3'),n=2,hooks=True),'QMS2',None),
 'P':   lambda: (NoValue(doc('sample_pnp'),(doc(BASE_5_1A),'&ASCQ3')),'&ASCQ1',None),   # pnp 2N2907A
 'NMOS':lambda: (doc('sample_mos'),'&ASCQ1',None),                  # n-MOS with a substrate pin (enhancement)
 'NMOS_DEP':lambda: (doc('sample_mos'),'&ASCQ2',None),
 'PMOS':lambda: (doc('sample_mos'),'&ASCQ3',None),                  # p-MOS with a substrate pin (enhancement)
 'PMOS_DEP':lambda: (doc('sample_mos'),'&ASCQ4',None),
 'VCC': lambda: (doc(BASE_5_1A),'&ASCVCC','5.0','V'),             # voltage — vcc(x, y, volts)
 # --- without a sample (SpiceLib: a base from a sample + own SPICE template/model/drawing); verify in Multisim ---
 'C':   lambda: (doc(BASE_5_1A),'&ASCC1','15p','F'),              # capacitor (virtual, from base_5_1a), pins as for R
 # Multisim labels the value in the units of the element type (ohms for a resistor base), so the source value is hidden
 'VSIN':lambda: (SpiceLib((NoValue(doc(BASE_5_1A),(doc(BASE_5_1A),'&ASCQ3')),'&ASCR3'),
                          template='v%p %t1 %t2 dc 0 ac 1 sin(0 #1 1k)\n',draw=draw_vsin,rename={'RESISTOR':'SIGNAL_VOLTAGE_SOURCES','RESISTOR_VIRTUAL':'AC_VOLTAGE',
                                  'VIRTUAL_RESISTANCE':'AC_VOLTAGE','Resistor':'AC voltage source','Basic':'Sources',
                                  'R%d':'V%d'}),'VSIN','4k'),     # 1 kHz sine, value — amplitude, V; 1 (+) on top, 2 below
 'Q3904':lambda: (SpiceLib((doc(BASE_5_1A),'&ASCQ3'),model=('2N3904__BJT_NPN__1',MODEL_2N3904),show='2N3904',
                          rename={'2N2222':'2N3904'}),'Q3904',None),
 'P3906':lambda: (SpiceLib((doc('sample_pnp'),'&ASCQ1'),model=('2N3906__BJT_PNP__1',MODEL_2N3906),show='2N3906',
                          rename={'2N2907A':'2N3906'}),'P3906',None),
 'D4148x4':lambda: (SpiceLib((doc(BASE_5_1A),'&ASCD1'),model=('1N4148X4__DIODE__1',MODEL_1N4148X4),show='1N4148 N=4',
                          rename={'1BH62':'1N4148'}),'D4148x4',None),   # 4 × 1N4148 in series (N=4 in LTspice)
 'TIP121':lambda: (SpiceLib((doc(BASE_5_1A),'&ASCQ3'),template=SUBCKT_TIP121,model=False,show='TIP121',
                          rename={'2N2222':'TIP121','BJT_NPN':'DARLINGTON_NPN'}),'TIP121',None),
 'TIP127':lambda: (SpiceLib((doc('sample_pnp'),'&ASCQ1'),template=SUBCKT_TIP127,model=False,show='TIP127',
                          rename={'2N2907A':'TIP127','BJT_PNP':'DARLINGTON_PNP'}),'TIP127',None),
 'GND': lambda: (doc(BASE_5_1A),'&ASC0',None),
 'SW':  lambda: (doc(BASE_5_1A),'&ASCS1',None),
 'XMM': lambda: (doc(BASE_5_1A),'&ASCXMM1',None),
}
SUBCKT_BASE={'QS':'sample_schottky_subckt','QM':'sample_multiemitter','QM2':'@MultiNPN2','QMS2':'@MultiSchottky2'}   # the subcircuit lives in the base file
FIXED_LABEL=('VCC','GND','SW','XMM')   # these have their own labels, not moved
_TPL={}
def tpl(kind):
    if kind not in _TPL: _TPL[kind]=KINDS[kind]() if kind in KINDS else from_registry(kind)
    return _TPL[kind]
# catalog parts (registry.py): the element type is the Multisim database part name ('2N3904', 'BJT_NPN/2N3904'); the element
# is cloned from a donor file saved by Multisim (Multisim samples → scripts/harvest.py → samples/ni/)
REG={}   # type → registry entry
def reg_entry(kind):
    if kind not in REG:
        import registry
        try: REG[kind]=registry.find(kind)
        except KeyError as e: raise SystemExit('ERROR: '+e.args[0])
    return REG[kind]
INST={}   # type → InstrumentsData entry of the donor (instrument settings: oscilloscope, generator, Bode…)
def from_registry(kind):
    e=reg_entry(kind)
    if '#' in e['path'] or e['path'].endswith('.xml.gz'):   # compact catalog: a part block
        D=PartPack(e['path'])
        if D.inst is not None: INST[kind]=D.inst
    else:                               # a whole file (skill samples, older catalog layouts)
        D=Doc(unpack(e['path'])); ins=D.h.find('InstrumentsData')
        if ins is not None:
            from geom import dec
            n=next((x for x in ins if dec(x.get('CompLongName') or '').startswith(e['refdes']+'#1/')),None)
            if n is not None: INST[kind]=n
    t=(D,enc(e['refdes']),e['value'])
    return t+(e['unit'],) if e['unit'] else t

SHEET_MIN=(14,11)   # 14×11 inch sheet — verified in Multisim; larger only when the scheme does not fit
MARGIN_IN=0.75      # margins around the scheme, inches
TMAX=1e-5           # interactive simulation step, s (instead of «automatic» — see msgen.set_tmax); None — Multisim default

class Scheme:
    def __init__(s,name,sheet_min=SHEET_MIN,margin=MARGIN_IN,outdir=None,tmax=TMAX):
        s.name=name; s.sheet_min=sheet_min; s.margin=margin; s.outdir=outdir or OUT; s.tmax=tmax
        s.parts=[]; s.W=[]; s.cnt={}; s.probes=[]
    # ---------- description ----------
    def part(s,name,kind,pin,x,y,rot=0,mirror=False,value=None,label='auto',refdes=None,glob=None,subst=None):
        """element `kind` placed so that its pin `pin` lands in cell (x, y); label: 'auto' | right/left/top/bottom | None"""
        if kind not in KINDS: reg_entry(kind)   # not a generator type — look it up in the registry (KeyError with similar names)
        assert all(p['name']!=name for p in s.parts),'duplicate name '+name
        s.parts.append(dict(name=name,kind=kind,pin=pin,x=x,y=y,rot=rot,mirror=mirror,value=value,
                            label=None if kind in FIXED_LABEL else label,refdes=refdes,glob=glob,subst=subst))
        return name
    def _auto(s,prefix):
        s.cnt[prefix]=s.cnt.get(prefix,0)+1; return '%s%d'%(prefix,s.cnt[prefix])
    def vcc(s,x,y,volts=None):
        """VCC symbol, pin at (x, y); volts — voltage (5 V by default; all VCC of a scheme are one net); → terminal"""
        n=s._auto('VCC'); s.part(n,'VCC','VCC',x,y,refdes='VCC',glob='VCC',value=None if volts is None else '%g'%volts)
        return (n,'VCC')
    def gnd(s,x,y):
        """ground symbol, pin at (x, y); → terminal"""
        n=s._auto('GND'); s.part(n,'GND','1',x,y,refdes='0',glob='0'); return (n,'1')
    def switch(s,name,x,y,vcc=2,gnd=2,right=False):
        """switch to VCC/ground: common pin 2 at (x, y), pins 1 (VCC) and 3 (ground) 7 cells to the left
        (right=True — to the right), VCC `vcc` cells above pin 1, ground `gnd` cells below pin 3.
        Occupies x−8…x (x…x+8), y−2−vcc−6…y+1+gnd+1"""
        d=7 if right else -7
        s.part(name,'SW','2',x,y,mirror=not right)
        s.wire((name,'1'),s.vcc(x+d,y-2-vcc)); s.wire((name,'3'),s.gnd(x+d,y+1+gnd))
        return (name,'2')
    def meter(s,name,x,y,gnd=4):
        """multimeter: pin 1 (+) at (x, y), pin 2 (−) 2 cells to the right, ground from it `gnd` cells down"""
        s.part(name,'XMM','1',x,y); s.wire((name,'2'),s.gnd(x+2,y+gnd))
        return (name,'1')
    def probe(s,name,x,y,kind='V',ref=None):
        """Multisim probe with its tip at cell (x, y) of a wire: kind 'V' voltage, 'I' current, 'VI' voltage and current,
        'P' power (tip on an element pin), 'D' digital, 'REF' reference point; ref='Ref1' — voltage
        relative to the reference probe (differential)"""
        assert kind in PROBES and kind!='VREF',kind; assert not ref or kind=='V','ref — only for a voltage probe'
        s.probes.append(dict(name=name,x=x,y=y,kind=kind,ref=ref)); return name
    def block(s,name,x,y,rot=0,mirror=False,names=None,label='auto',**params):
        """a block from the library (scripts/blocks.py): a ready fragment — parts and wires; the block anchor cell goes to (x, y),
        rot/mirror — as for a part; → dict of block terminals (terminals and J junctions), wire them as usual"""
        import blocks
        return blocks.place(s,name,x,y,rot=rot,mirror=mirror,names=names,label=label,**params)
    def free_name(s,prefix):
        """first free name prefix1, prefix2…"""
        used={p['name'] for p in s.parts}; n=1
        while '%s%d'%(prefix,n) in used: n+=1
        return '%s%d'%(prefix,n)
    def pos(s,t):
        """cell of a terminal ('element','pin') or a junction J(x,y) — before the build"""
        if t[0]=='J': return t[1:]
        import blocks
        p=next(p for p in s.parts if p['name']==t[0])
        o=blocks.pin_offsets(p['kind'],p['pin'],p['rot'],p['mirror'])[t[1]]
        return (p['x']+o[0],p['y']+o[1])
    def wire(s,*pts):
        """wire: the first and last items are a terminal ('element','pin') or a junction J(x,y); in between — bends (x,y).
        3–4 wires at a junction; a junction with 2 wires becomes a bend."""
        assert len(pts)>=2; s.W.append(list(pts))
    def wires(s,lst):
        for w in lst: s.wire(*w)
    # ---------- build ----------
    def _base(s):
        need={SUBCKT_BASE[p['kind']] for p in s.parts if p['kind'] in SUBCKT_BASE}
        if len(need)>1:
            assert frozenset(need) in COMBINED,'no common base for the subcircuits %s (see COMBINED)'%need
            return COMBINED[frozenset(need)]
        return need.pop() if need else BASE_5_1A
    def _build(s,origin):
        b=Builder(base_path(s._base()),[],origin=origin,tpl=doc(BASE_5_1A))
        for p in s.parts:
            b.place(p['name'],tpl(p['kind']),p['pin'],p['x'],p['y'],rot=p['rot'],mirror=p['mirror'],value=p['value'],
                    label=None if p['label']=='auto' else p['label'],refdes=p['refdes'],glob=p['glob'],subst=p['subst'])
            b.parts[p['name']]['kind']=p['kind']
            if p['kind'] in INST: b.parts[p['name']]['inst']=INST[p['kind']]
        b.wires(s.W)
        for p in s.probes: b.probe(p['name'],p['kind'],p['x'],p['y'],ref=p['ref'])
        autolabel(b,[p for p in s.parts if p['label']=='auto'])
        return b
    def build(s,checks=True):
        t0=time.time()
        b=s._build((0,0))                                          # 1st pass — size only
        x0,y0,x1,y1=geom.Scene(b.D.objs,b.D.el).bbox()
        dpi=96; m=s.margin*dpi
        W=max(s.sheet_min[0],math.ceil((x1-x0+2*m)/dpi)); H=max(s.sheet_min[1],math.ceil((y1-y0+2*m)/dpi))
        ox=round(((W*dpi-(x1-x0))/2-x0)/G); oy=round(((H*dpi-(y1-y0))/2-y0)/G)
        b=s._build((ox,oy)); s.origin=(ox,oy)                     # 2nd pass — centered on a W×H sheet
        os.makedirs(s.outdir,exist_ok=True)
        out=os.path.join(s.outdir,s.name+'.ms14')
        xml=finalize(b,s.name,out,rename=False,sheet=(W,H),tmax=s.tmax)
        xp=os.path.join(CACHE,s.name+'_out.xml'); open(xp,'wb').write(xml)
        s.b=b; s.xml=xp; s.sheet=(W,H)
        print('== %s: sheet %d×%d inches, built in %.1f s → %s'%(s.name,W,H,time.time()-t0,os.path.relpath(out,REPO)))
        for n in b.nets: print('   net %-4s'%n['name'],', '.join('%s.%s'%(m[0],dec_pin(m[1])) for m in sorted(n['mem']) if m[0]!='J'))
        for p in s.parts:
            if p['kind'] in REG:
                e=REG[p['kind']]; print('   from catalog: %-5s %s ← %s (%s, Multisim %s)'%(p['name'],e['key'],os.path.basename(e['path']),e['refdes'],e['multisim']))
        for p in s.probes: print('   probe %-5s %-3s (%d,%d)%s'%(p['name'],p['kind'],p['x'],p['y'],' from '+p['ref'] if p['ref'] else ''))
        if checks: s.check()
        return s
    def check(s):
        v=validate.check(ET.fromstring(protect(open(s.xml,'rb').read())))
        ok=not v['dup_ids'] and not v['dup_ci'] and not v['bad']
        print('   ID references:','OK' if ok else 'ERROR %s'%v)
        sc=geom.Scene(s.b.D.objs,s.b.D.el)
        st=density(sc); print('   density: %d elements, %.0f×%.0f cells, %.0f cells² per element, longest segment %d cells'%st)
        warn=lint(sc,s.sheet,s.origin)
        print('   overlaps:','none' if not warn else '%d'%len(warn))
        for w in warn: print('     ! '+w)
        try:   # the file is already written: a preview or ngspice failure must not stop the build
            import render
            pr=os.path.join(CACHE,'preview'); os.makedirs(pr,exist_ok=True)
            render.render(s.xml,os.path.join(pr,s.name+'.png')); render.render(s.xml,os.path.join(pr,s.name+'_zoom.png'),zoom=True)
            print('   preview:',os.path.relpath(os.path.join(pr,s.name+'_zoom.png'),REPO))
        except ImportError: print('   preview: no matplotlib (pip install matplotlib)')
        except Exception as e: print('   preview: failed (%s: %s)'%(type(e).__name__,e))
        try:
            import spice
            r=spice.analyze(s.xml,verbose=True)
            print('   ngspice:',r['func'] if r else 'no S* switches or multimeter')
        except FileNotFoundError: print('   ngspice: not installed (apt-get install ngspice)')
        except (Exception,SystemExit) as e: print('   ngspice: not computed (%s)'%(e or type(e).__name__))
        s.warnings=warn; s.valid=ok
        return s

def dec_pin(p): return geom.dec(p)

# ---------- labels ----------
def autolabel(b,parts):
    """for elements with label='auto' — the label side (right/left/top/bottom) where the name and value do not touch
    wires, symbols, junctions or other labels; on a tie — in this element's order of preference"""
    if not parts: return
    sc=geom.Scene(b.D.objs,b.D.el)
    segs=[g[1:] for g in sc.segments()]
    by={sy.name:sy for sy in sc.syms}
    auto={p['name'] for p in parts}
    names={p['name']:b.parts[p['name']]['refdes'] for p in parts}
    taken=[bx for sy in sc.syms if sy.name not in {names[n] for n in auto} for bx in sy.label_boxes()]
    borders=[(sy.name,sy.border) for sy in sc.syms if sy.border]
    dots=[(x-3,y-3,x+3,y+3) for x,y,_ in sc.junc]
    for p in parts:
        n=p['name']; bp=b.parts[n]
        if bp['T'] is None: continue
        refdes=bp['refdes']; sy=by.get(refdes)
        val=next((o for c,_,_,o in (sy.texts if sy else []) if c=='Value'),'')
        var=next((o for c,_,_,o in (sy.texts if sy else []) if c=='Variable'),'')   # reading of an interactive source
        tx,ty=bp['T']
        loc=bp['loc']; horiz=max(v[0] for v in loc.values())-min(v[0] for v in loc.values())>max(v[1] for v in loc.values())-min(v[1] for v in loc.values())
        order=('top','bottom','right','left') if horiz else ('right','left','top','bottom')
        best=None
        for k,side in enumerate(order):
            lx,ly=b.label_pos(n,side,b.label_texts(n)); lx+=tx; ly+=ty
            boxes=[geom.text_box(lx,ly,refdes)]+([geom.text_box(lx,ly+15,val)] if val else [])
            if var: boxes.append(geom.text_box(lx,ly+15+(15*len(val.rstrip().split('\n')) if val.strip() else 0),var))
            score=0
            for bx in boxes:
                score+=3*sum(geom.seg_hits_rect(g,bx) for g in segs)
                score+=3*sum(geom.rect_overlap(bx,br,2) for nm,br in borders if nm!=refdes)
                score+=2*sum(geom.rect_overlap(bx,t) for t in taken)
                score+=sum(geom.rect_overlap(bx,d) for d in dots)
            if best is None or score<best[0]: best=(score,side,boxes)
        b.set_label(n,best[1]); taken+=best[2]

# ---------- checks ----------
def density(sc):
    pts=[p for _,ps in sc.wires for p in ps] or [(0,0)]   # a scheme without wires (the donor template)
    w=(max(x for x,_ in pts)-min(x for x,_ in pts))/G; h=(max(y for _,y in pts)-min(y for _,y in pts))/G
    seg=[(abs(g[1]-g[3])+abs(g[2]-g[4]))/G for g in sc.segments()]
    n=len([sy for sy in sc.syms if sy.name])
    return n,w,h,w*h/max(1,n),max(seg,default=0)

def lint(sc,sheet=None,origin=(0,0)):
    """overlaps that must not be on the sheet (each one is a warning line; coordinates are script cells)"""
    warn=[]; segs=sc.segments()
    cell=lambda x,y:'(%d, %d)'%(round(x/G)-origin[0],round(y/G)-origin[1])
    named=[sy for sy in sc.syms if sy.name]
    # labels
    for sy in named:
        for c,x,y,o in sy.texts:
            bx=geom.text_box(x,y,o)
            hit=[g for g in segs if geom.seg_hits_rect(g[1:],bx,2)]
            if hit: warn.append('label «%s» (%s) touches a wire'%(o,sy.name))
            if any(geom.seg_hits_rect(g,bx,2) for g in sy.segs) or \
               any(geom.rect_overlap(bx,(cx-r1,cy-r2,cx+r1,cy+r2),2) for cx,cy,r1,r2 in sy.circles):
                warn.append('label «%s» on its own symbol %s'%(o,sy.name))
            for s2 in named:
                if s2 is not sy and s2.border and geom.rect_overlap(bx,s2.border,2): warn.append('label «%s» (%s) on symbol %s'%(o,sy.name,s2.name))
                if s2 is not sy:
                    for c2,x2,y2,o2 in s2.texts:
                        if geom.rect_overlap(bx,geom.text_box(x2,y2,o2),1) and (sy.name,o)<(s2.name,o2):
                            warn.append('labels «%s» (%s) and «%s» (%s) overlap'%(o,sy.name,o2,s2.name))
    # a wire through a foreign pin (looks like a connection, but there is none)
    pins=[(sy.name,pn,xy) for sy in named for pn,xy in sy.pins.items()]
    for nm,pn,(x,y) in pins:
        if any(geom.on_segment((round(x),round(y)),g[1:],inner=True) for g in segs):
            warn.append('wire passes through pin %s.%s'%(nm,pn))
    # a wire over an element body (through a resistor, a source circle…) — looks like a connection or an error on the sheet
    for sy in named:
        if any(geom.through_body(g[1:],sy) for g in segs if g[1]==g[3] or g[2]==g[4]):
            warn.append('wire runs through the body of %s — route around it'%sy.name)
    # slanted wire (bends not aligned with the pin cells)
    for g in segs:
        if g[1]!=g[3] and g[2]!=g[4]: warn.append('slanted wire at %s'%cell(g[1],g[2]))
    # overlapping wires
    for i,a in enumerate(segs):
        for bb in segs[i+1:]:
            if a[1]==a[3]==bb[1]==bb[3] and max(min(a[2],a[4]),min(bb[2],bb[4]))<min(max(a[2],a[4]),max(bb[2],bb[4])) or \
               a[2]==a[4]==bb[2]==bb[4] and max(min(a[1],a[3]),min(bb[1],bb[3]))<min(max(a[1],a[3]),max(bb[1],bb[3])):
                warn.append('overlapping wires at %s'%cell(a[1],a[2]))
    # a wire bend lying on another wire — looks like a connection without a dot
    for _,pts in sc.wires:
        for p in pts[1:-1]:
            if any(geom.on_segment(p,g[1:],inner=True) for g in segs):
                warn.append('wire bend lies on another wire at %s'%cell(*p))
    # symbols on top of each other
    for i,a in enumerate(named):
        for c in named[i+1:]:
            if a.border and c.border and geom.rect_overlap(a.border,c.border,4): warn.append('symbols %s and %s overlap'%(a.name,c.name))
    # off the sheet
    if sheet:
        x0,y0,x1,y1=sc.bbox()
        if x0<0 or y0<0 or x1>sheet[0]*96 or y1>sheet[1]*96: warn.append('scheme goes off the sheet')
    return sorted(set(warn),key=warn.index)

# ---------- pin reference ----------
def pins_table(kinds=()):
    """pins of every element type (or of catalog parts kinds) relative to the anchor (first) pin, in cells,
    for the main orientations"""
    b=Builder(sample(BASE_5_1A),[],tpl=doc(BASE_5_1A))
    ref={'R':'1','Q':'C','D':'A','DS':'A','QS':'C','QM':'B','P':'C','NMOS':'D','NMOS_DEP':'D','PMOS':'D','PMOS_DEP':'D',
         'VCC':'VCC','GND':'1','SW':'2','XMM':'1'}
    if kinds: ref={k:reg_entry(k)['pins'][0] for k in kinds}
    for k,rp in ref.items():
        if k in SUBCKT_BASE: continue
        for rot,mir in ((0,False),(90,False),(270,False),(180,True),(0,True)):
            if k in ('VCC','GND','XMM') and (rot or mir): continue
            n='%s_%d_%d'%(k.replace('/','_'),rot,mir)
            p=b.place(n,tpl(k),rp,50,50,rot=rot,mirror=mir,label=None)
            print('%-9s rot=%-3d mirror=%-5s'%(k,rot,mir),{geom.dec(pn):(round(v[1][0]/G-50),round(v[1][1]/G-50)) for pn,v in p['pins'].items()})
    if not kinds: print('QS (Schottky transistor) — as Q; QM (4 emitters): B (0,0), E1–E4 (−8,5) (−6,5) (−4,5) (−2,5), C (3,5)')

if __name__=='__main__' and sys.argv[1:2]==['pins']: pins_table(sys.argv[2:])
