"""Check a finished scheme in ngspice: the netlist is built from the result XML (the same elements, nodes and models
Multisim will see). Logic: switches S* are enumerated, the output is the voltage of multimeter XMM1 (truth
table). With a sine source (VSIN) — transient analysis: peak-to-peak and DC component on the multimeter.
Subcircuits (project sheets) → .subckt; bipolar (C/B/E) and MOS (D/G/S/SUB) transistors, diodes, resistors; elements
without a sample (SpiceLib) — by their template, expanded the way Multisim does it.
python3 scripts/spice.py .msgen/<name>_out.xml
python3 scripts/spice.py FILE.ms14 "op; print all"     # any analyses on a built file (run())"""
import sys, os, re, subprocess, itertools, tempfile
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from msgen import *
from geom import dec

VCC_VOLTS=5
def params(c):
    """component parameters (#0, #1, …) from the first CiaParamList"""
    pl=c.find('.//CiaParamList/parameters')
    return [dec(x.get('Value')) for x in pl] if pl is not None else []
vcc=[VCC_VOLTS]   # VCC voltage — from the scheme's VCC symbol
def emit(el,objs,sw,models,subports):
    """netlist lines of one sheet (main or subcircuit); returns (lines, output node, subcircuit connectors)"""
    byci={e.get('CiID'):e for e in el}; byid={k.get('ID'):k for k in objs}
    conns=[byci[k[0].get('CiComponent')][0] for k in objs if k.get('Class')=='CIITHierConnector']
    out=None; lines=[]
    def nodes(c,nm):
        node={}
        for p in c.find('Ports'):
            pp=byci[p.get('CiID')][0]; ns=[dec(byci[n.get('CiID')][0].get('LocalName')) for n in pp.find('Nodes')]
            node[dec(pp.get('LocalName'))]=ns[0] if ns else 'nc_%s_%s'%(nm,dec(pp.get('LocalName')))
        return node
    for e in el:
        if e.get('Class') not in ('CiComponent','CiInstComponent'): continue
        c=e[0]; nm=dec(c.get('LocalName')); node=nodes(c,nm)
        if any(c is x for x in conns): continue   # hierarchical connector of a subcircuit
        if e.get('Class')=='CiInstComponent':     # subcircuit instance
            sub=dec(byid[c.get('SymCompID')][0].find('HierBlock/CHierBlock').get('FileName'))
            lines.append('X%s %s %s'%(nm,' '.join(node[p] for p in subports[sub]),sub)); continue
        mname=None
        if c.get('Model'):
            for x in byci[c.get('Model')][0].iter():   # model text (may start with comments)
                m=re.search(r'^\s*\.(?:model|subckt)\s+(\S+)',dec(x.get('String') or ''),re.M|re.I)
                if m: mname=m.group(1); models[mname.lower()]=dec(x.get('String')); break
        if nm=='VCC': vcc[0]=float(params(c)[0]); continue
        if nm=='0': continue
        if re.match(r'X[A-Z]',nm) and not nm.startswith('XMM'): continue   # instruments (oscilloscope, Bode…) — skipped in ngspice
        if nm.startswith('XMM'):                  # Multisim voltmeter: 1 GOhm between + and −
            out=(node['1'],node['2']); lines.append('R%s %s %s 1G'%(nm,node['1'],node['2'])); continue
        tp=dec(next((x.get('String') for x in c.iter('CiaSpiceTmpltExprt')),'') or '')
        if tp.startswith(CUSTOM_MARK):            # element without a sample: template, expanded as Multisim does
            pr=params(c); txt=tp[len(CUSTOM_MARK):].replace('%p',nm)
            txt=re.sub(r'%t(\w+)',lambda m:node[m.group(1)],txt)
            txt=re.sub(r'#(\d+)',lambda m:pr[int(m.group(1))],txt)
            lines+=[l for l in txt.split('\n') if l.strip()]; continue
        if re.match(r'\s*x',tp,re.I) and not tp.startswith(CUSTOM_MARK): lines+=expand(tp,nm,node,c,mname)   # subcircuit (Darlington…)
        elif 'D' in node and 'G' in node:         # MOS with a substrate pin
            par=next((dec(x.get('Value')).strip() for x in c.iter() if re.search(r'L=\S+\s+W=',x.get('Value') or '')),'')
            lines.append('M%s %s %s %s %s %s %s'%(nm,node['D'],node['G'],node['S'],node['SUB'],mname,par))
        elif nm.startswith('Q'): lines.append('Q%s %s %s %s %s'%(nm,node['C'],node['B'],node['E'],mname))
        elif nm.startswith('D'): lines.append('D%s %s %s %s'%(nm,node['A'],node['K'],mname))
        elif nm.startswith('R'):
            v=next(dec(x.get('String')) for x in c.iter() if re.fullmatch(r'&ASC[\d.]+[kKmMuUnpG]?',x.get('String') or ''))
            lines.append('R%s %s %s %s'%(nm,node['1'],node['2'],v.replace('M','Meg')))
        elif nm.startswith('S'): lines.append('R%s %s %s 1m'%(nm,node['2'],node['1' if sw[nm] else '3']))
        elif nm.startswith('C'): lines.append('C%s %s %s %s'%(nm,node['1'],node['2'],params(c)[1]))   # capacitor: #1 — capacitance
        elif tp.strip(): lines+=expand(tp,nm,node,c,mname)   # catalog part — by its Multisim template
        else: raise ValueError('unknown element '+nm)
    return lines,out,[(dec(c.get('LocalName')),nodes(c,'')['']) for c in conns]

def expand(tp,nm,node,c,mname):
    """Multisim SPICE template → netlist lines: %p — RefDes, %t<pin> — node, #k — k-th parameter, %S<k> — k-th string
    of the parameter list, %m — model, %v<k>?<yes>%v:<no>%v; — condition «parameter k is not 0»; comment lines
    (the interactive part of switches, «* !!!BEGIN-INTERACT») are dropped"""
    pl=c.find('.//CiaParamList'); pr=params(c)
    st=[dec(x.get('Value') or '') for x in pl.find('strings')] if pl is not None and pl.find('strings') is not None else []
    on=lambda k:k<len(pr) and pr[k].strip() not in ('','0','0.0')
    txt=re.sub(r'%v(\d+)\?(.*?)%v:(.*?)%v;',lambda m:m.group(2) if on(int(m.group(1))) else m.group(3),tp,flags=re.S)
    txt=txt.replace('%p',nm).replace('%m',mname or '')
    pins='|'.join(re.escape(k) for k in sorted(node,key=len,reverse=True))   # pins may be «IN+», «~CLR»
    txt=re.sub(r'%t('+pins+')',lambda m:node[m.group(1)],txt)
    txt=re.sub(r'%S(\d+)',lambda m:st[int(m.group(1))] if int(m.group(1))<len(st) else '',txt)
    txt=re.sub(r'#(\d+)',lambda m:pr[int(m.group(1))].replace('M','Meg') if int(m.group(1))<len(pr) else '',txt)
    return [l for l in txt.split('\n') if l.strip() and not l.lstrip().startswith('*')]

# the unit «ampere» after a number in Multisim models (IEE 10 4 DC 1.516e-005A, Is=8e-016A): Multisim ignores it,
# but ngspice reads «a» as the atto prefix (1e-18) — an op-amp without bias current stays silent. Strip the letter from number tokens.
AMPS=re.compile(r'(?<![\w.])(\d[\d.]*(?:[eE][-+]?\d+)?)[aA](?=[\s)]|$)')

def deck(D,sw={},title='scheme'):
    """the circuit part of the netlist (no analyses): (lines, multimeter nodes or None). VCC — from the file's symbol.
    Subcircuits (other project sheets, CIITHierDoc) — .subckt by sheet name; pins — hierarchical connectors."""
    models={}; subs=[]; subports={}
    for h in D.root.iter('CIITHierDoc'):
        if h is D.h: continue
        ds=next(x for x in D.root.iter('DesignSheet') if h in set(x.iter()))
        name=dec(ds.get('Title'))
        comp=h.find('.//Components/CODComposite'); el=h.find('.//Elements')
        body,_,conns=emit(el,comp.find('Objects'),sw,models,subports)
        subports[name]=[n for n,_ in conns]
        subs+=['.subckt %s %s'%(name,' '.join(nd for _,nd in conns))]+body+['.ends']
    vcc[0]=VCC_VOLTS
    lines,out,_=emit(D.el,D.objs,sw,models,subports)
    lines=['* '+title,'Vcc VCC 0 dc %g'%vcc[0]]+subs+lines+list(models.values())
    lines=[AMPS.sub(r'\1',l) for l in lines]
    if any(re.search(r'\bpi\b',l) for l in lines): lines.insert(1,'.param pi=3.14159265358979')   # Multisim op-amp models: {2*pi*…}
    return lines,out

def netlist(D,sw,title='scheme',tran=None):
    """sw: {'S1':1,...} — 1: common pin 2 to pin 1 (VCC), 0: to pin 3 (ground). Returns (text, output node)."""
    lines,out=deck(D,sw,title)
    if tran:   # peak-to-peak and mean on the multimeter over the last 10 ms
        a,b=out; v='v(%s)'%a+('-v(%s)'%b if b!='0' else '')
        lines+=['.control','tran %g %g'%(tran[0],tran[1]),'let vo=%s'%v,
                'meas tran vmax MAX vo from=%g to=%g'%(tran[1]-10e-3,tran[1]),'meas tran vmin MIN vo from=%g to=%g'%(tran[1]-10e-3,tran[1]),
                'meas tran vavg AVG vo from=%g to=%g'%(tran[1]-10e-3,tran[1]),'.endc','.end']
    else:
        lines+=['.control','op','print v(%s)'%out[0],'.endc','.end']
    return '\n'.join(lines)+'\n',out

def run(path,commands,params=None,show=False):
    """expected values for a built file: ngspice `commands` (a list or a ';'-separated string of .control lines:
    'op', 'print v(4) i(vv1)', 'ac lin 1 1k 1k', 'tran 1u 50m', 'fourier 1k v(4)', 'noise v(4) vvin dec 100 20 20k') on
    the netlist of the .ms14 (or unpacked .xml) file itself — its real VCC, parts, models and circuit parameters.
    Never compute the values the user will compare with Multisim from a netlist written by hand.
    params — override circuit parameters, e.g. {'Uin': 0.5}. Returns ngspice's output."""
    import blast
    raw=blast.read_ms(path) if path.endswith('.ms14') else open(path,'rb').read()
    D=Doc(raw); x=raw.decode('latin1')
    lines,_=deck(D,{},os.path.basename(path))
    names=[dec('&'+n) for n in re.findall(r'<CircuitParamName NameItem="&amp;([^"]*)"',x)]
    vals=[dec('&'+v) for v in re.findall(r'<CircuitParamValue ValueItem="&amp;([^"]*)"',x)]
    cp=dict(zip(names,vals)); cp.update({k:'%g'%v for k,v in (params or {}).items()})
    if cp:       # a part parameter that is a circuit parameter name becomes {name}
        rx=re.compile(r'(?<![\w{])(%s)(?![\w}])'%'|'.join(map(re.escape,cp)))
        lines=[lines[0]]+['.param %s=%s'%kv for kv in cp.items()]+[l if l.startswith(('*','.')) else rx.sub(r'{\1}',l) for l in lines[1:]]
    if isinstance(commands,str): commands=[c.strip() for c in commands.split(';') if c.strip()]
    text='\n'.join(lines+['.control']+list(commands)+['.endc','.end'])+'\n'
    with tempfile.NamedTemporaryFile('w',suffix='.cir',delete=False) as f: f.write(text)
    r=subprocess.run(['ngspice','-b',f.name],capture_output=True,text=True)
    os.unlink(f.name)
    out=r.stdout+r.stderr
    if show: print(out)
    return out

FUNCS={1:{'NOT':lambda st:int(not st[0]),'BUFFER':lambda st:int(st[0])},
       2:{'NAND':lambda st:int(not all(st)),'NOR':lambda st:int(not any(st)),'AND':lambda st:int(all(st)),
          'OR':lambda st:int(any(st)),'XOR':lambda st:int(st[0]!=st[1])}}
def function_of(res,lo=0.8,hi=2.4):
    """name of the logic function from the table {switch states: volts} (TTL levels by default)"""
    if any(lo<=v<=hi for v in res.values()): return 'a level between %g and %g V (an error for logic, normal for an analog scheme)'%(lo,hi)
    lvl={st:int(v>hi) for st,v in res.items()}
    n=len(next(iter(res)))
    for name,f in FUNCS.get(n,{}).items():
        if all(lvl[st]==f(st) for st in lvl): return name
    return 'not in the list — check the table'

def analyze(path,verbose=True):
    """truth table over all switches S* → dict(inputs, table, func); None when there are no switches or no multimeter"""
    D=Doc(path)
    names=sorted((dec(e[0].get('LocalName')) for e in D.el if e.get('Class')=='CiComponent'
                  and re.fullmatch(r'S\d+',dec(e[0].get('LocalName')))),key=lambda n:int(n[1:]))
    if not any(dec(e[0].get('LocalName')).startswith('XMM') for e in D.el if e.get('Class')=='CiComponent'): return None
    srcs=[e for e in D.el if e.get('Class')=='CiComponent' and 'sin(' in dec(next((x.get('String') for x in e[0].iter('CiaSpiceTmpltExprt')),'') or '')]
    if not names and srcs: return analyze_tran(D,path,srcs,verbose)
    if not names: return None
    res={}
    for st in itertools.product((0,1),repeat=len(names)):
        txt,out=netlist(D,dict(zip(names,st)),os.path.basename(path))
        with tempfile.NamedTemporaryFile('w',suffix='.cir',delete=False) as f: f.write(txt)
        r=subprocess.run(['ngspice','-b',f.name],capture_output=True,text=True); os.unlink(f.name)
        m=re.search(r'v\(%s\) = ([-+0-9.e]+)'%re.escape(out[0].lower()),r.stdout.lower())
        if not m: print(r.stdout[-2000:],r.stderr[-2000:]); raise SystemExit('ngspice: no result')
        res[st]=float(m.group(1))
        if verbose: print('  '+' '.join('%s=%d'%(n,v) for n,v in zip(names,st)),'→ Y = %.3f V'%res[st])
    return dict(inputs=names,table=res,func=function_of(res))

def analyze_tran(D,path,srcs,verbose=True,t=(5e-6,40e-3)):
    """sine source: 40 ms transient analysis, peak-to-peak and mean on the multimeter over the last 10 ms"""
    txt,out=netlist(D,{},os.path.basename(path),tran=t)
    with tempfile.NamedTemporaryFile('w',suffix='.cir',delete=False) as f: f.write(txt)
    r=subprocess.run(['ngspice','-b',f.name],capture_output=True,text=True); os.unlink(f.name)
    val={k:float(v) for k,v in re.findall(r'^(vmax|vmin|vavg)\s*=\s*([-+0-9.e]+)',r.stdout,re.M)}
    if len(val)<3: print(r.stdout[-3000:],r.stderr[-3000:]); raise SystemExit('ngspice: no result')
    amp=dec(srcs[0][0].find('.//CiaParamList/parameters')[1].get('Value'))
    pp=val['vmax']-val['vmin']
    func='input sine %s V → multimeter %.2f V p-p (%.2f V amplitude, %.2f V rms), mean %.3f V'%(
        amp,pp,pp/2,pp/2/2**0.5,val['vavg'])
    if verbose: print('  '+func)
    return dict(inputs=[],table={},func='amplifier, gain %.1f'%(pp/2/float(amp)),tran=val)

if __name__=='__main__':
    if len(sys.argv)>2: run(sys.argv[1],sys.argv[2],show=True); sys.exit()
    r=analyze(sys.argv[1])
    print('Function:',r['func'] if r else 'no S* switches or XMM1 multimeter')
