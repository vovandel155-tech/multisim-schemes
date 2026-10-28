import xml.etree.ElementTree as ET, copy, uuid, random, re, math, sys, os
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import blast

# paths: samples — in the skill's samples/ (or the current folder), results and working files — relative to the current folder;
# overridden by the MSGEN_SAMPLES, MSGEN_OUT, MSGEN_WORK variables
HERE=os.path.dirname(os.path.abspath(__file__))   # <skill>/scripts
REPO=os.getcwd()                                  # project folder (run from it)
SAMPLES=os.environ.get('MSGEN_SAMPLES') or os.path.join(os.path.dirname(HERE),'samples')
CACHE=os.path.abspath(os.environ.get('MSGEN_WORK') or '.msgen')   # unpacked samples, result XML, previews
OUT=os.path.abspath(os.environ.get('MSGEN_OUT') or 'output')      # finished schemes
# sample files in samples/ have ASCII names (the claude.ai skill uploader rejects non-ASCII paths)
def sample(name):
    """path to the unpacked XML of sample <name>.ms14 from the skill's samples/ or the current folder
    (unpacked on first use)"""
    src=next((p for p in (os.path.join(SAMPLES,name+'.ms14'),os.path.abspath(name+'.ms14')) if os.path.exists(p)),None)
    if src is None: raise FileNotFoundError('no sample %s.ms14 in %s or in the current folder'%(name,SAMPLES))
    return unpack(src,name+'.xml')
def unpack(src,cached=None):
    """path to the unpacked XML of file src (.ms14) in the working folder (unpacked again when outdated)"""
    dst=os.path.join(CACHE,cached or os.path.basename(os.path.dirname(os.path.abspath(src)))+'__'+os.path.basename(src)+'.xml')
    if not os.path.exists(dst) or os.path.getmtime(dst)<os.path.getmtime(src):
        os.makedirs(CACHE,exist_ok=True); open(dst,'wb').write(blast.read_ms(src))
    return dst

TA=['M00','M01','M10','M11','M20','M21']
def getT(e):
    if e.get('Transformer-M00') is None: return None
    return [float(e.get('Transformer-'+k)) for k in TA]
def setT(e,t):
    for k,v in zip(TA,t):
        v=0.0 if abs(v)<1e-6 else v
        e.set('Transformer-'+k, ('%d'%round(v)) if abs(v-round(v))<1e-9 else repr(v))
def mul(t1,t2):  # apply t1 then t2 (row vectors): M = M1*M2
    a1,b1,c1,d1,e1,f1=t1; a2,b2,c2,d2,e2,f2=t2
    return [a1*a2+b1*c2, a1*b2+b1*d2, c1*a2+d1*c2, c1*b2+d1*d2, e1*a2+f1*c2+e2, e1*b2+f1*d2+f2]
def app(t,x,y):
    a,b,c,d,e,f=t; return (a*x+c*y+e, b*x+d*y+f)
ID0=[700000000]
def nid():
    ID0[0]+=8; return str(ID0[0])
RNG=random.Random(0)
def guid(): return '{'+str(uuid.UUID(int=RNG.getrandbits(128),version=4)).upper()+'}'
def reset_ids(seed):
    """reproducible build: the same script → the same IDs/GUIDs (the 700M+ range is unused in the samples)"""
    ID0[0]=700000000; RNG.seed(seed)

def _esc(m):   # NUL in binary attribute data (happens in Multisim files) is not allowed in XML — drop it
    return m.group(0).replace(b'\n',b'&#10;').replace(b'\r',b'&#13;').replace(b'\t',b'&#9;').replace(b'\x00',b'')
def protect(raw):
    """line breaks and tabs inside attribute values → &#10; &#13; &#9;, so that the parser keeps them
    (a regex over ="…"; the result is byte-identical to the former char-by-char parser on all samples)"""
    return _SPECIAL.sub(_esc,raw)
_SPECIAL=re.compile(rb'="[^"]*[\n\r\t\x00][^"]*"')   # only attributes with a line break, tab or NUL
def serialize(root):
    xml=ET.tostring(root,encoding='us-ascii',xml_declaration=False)
    xml=xml.replace(b'&#10;',b'\n').replace(b'&#13;',b'\r').replace(b'&#09;',b'\t').replace(b'&#9;',b'\t').replace(b' />',b'/>')
    return b'<?xml version="1.0" encoding="ASCII"?>\n'+xml+b'\n'
def sheet_elements(h):
    """the electrical part of the sheet — Elements with CiCircuit (probes may carry their own Elements earlier in the data)"""
    el=next((e for e in h.iter('Elements') if any(i.get('Class')=='CiCircuit' for i in e)),None)
    return el if el is not None else h.find('.//Elements')

class Doc:
    def __init__(s,path):   # path — unpacked XML (file) or the XML itself (bytes)
        s.root=ET.fromstring(protect(path if isinstance(path,bytes) else open(path,'rb').read()))
        s.h=s.root.find('.//CIITHierDoc')
        s.comp=s.h.find('.//Components/CODComposite')
        s.objs=s.comp.find('Objects'); s.refs=s.comp.find('ReferencedComponents')
        s.el=sheet_elements(s.h)
        s.byci={e.get('CiID'):e for e in s.el}
    def symbol_of(s,name):
        for k in s.objs:
            c=k[0]
            if c.get('CiComponent'):
                ci=s.byci.get(c.get('CiComponent'))
                if ci is not None and ci[0].get('LocalName')==name: return k
    def bundle(s,name):
        sym=s.symbol_of(name)
        if sym is None:
            from geom import dec
            raise KeyError('no element %s in the file'%dec(name))
        ci=s.byci[sym[0].get('CiComponent')]
        ports=[s.byci[p.get('CiID')] for p in ci[0].find('Ports')]
        model=s.byci.get(ci[0].get('Model')) if ci[0].get('Model') else None
        # pin models (digital ICs have input/output models)
        pmod={p[0].get('Model'):s.byci[p[0].get('Model')] for p in ports if p[0].get('Model') in s.byci}
        return dict(sym=sym,ci=ci,ports=ports,model=model,port_models=pmod)

# ---------- compact catalog: the block of one part instead of a whole donor file ----------
import gzip
def pack_part(D,refdes):
    """block of part RefDes from file D (Doc) — symbol, CiComponent, pins, model, pin models and instrument settings
    (InstrumentsData) — as XML (bytes); the generator gets the same from it as from the whole file (PartPack.bundle)"""
    from geom import dec
    b=D.bundle(enc(refdes))
    root=ET.Element('MsgenPart',{'refdes':refdes})
    for tag,items in (('Sym',[b['sym']]),('Ci',[b['ci']]),('Ports',b['ports']),('Model',[b['model']] if b['model'] is not None else []),
                      ('PortModels',list(b['port_models'].values()))):
        ET.SubElement(root,tag).extend(items)
    ins=D.h.find('InstrumentsData')
    n=next((x for x in ins if dec(x.get('CompLongName') or '').startswith(refdes+'#1/')),None) if ins is not None else None
    if n is not None: ET.SubElement(root,'Inst').append(n)
    return ET.tostring(root,encoding='utf-8')
import zlib, json as _json
def _deflate(x):
    c=zlib.compressobj(9,zlib.DEFLATED,-15); return c.compress(x)+c.flush()   # raw deflate: no headers
def write_packs(path,packs):
    """all part blocks in one file parts.bin (compressed blocks back to back) + index parts.idx (JSON: name → [offset,
    length]). Not zip or gzip: the claude.ai skill uploader accepts at most 200 files and no archives inside the archive.
    Order and compression are fixed — writing again gives the same files"""
    idx={}; pos=0
    with open(path,'wb') as f:
        for n in sorted(packs):
            d=_deflate(packs[n]); f.write(d); idx[n]=[pos,len(d)]; pos+=len(d)
    with open(os.path.splitext(path)[0]+'.idx','w',encoding='utf-8') as f: _json.dump(idx,f,indent=0,sort_keys=True)
_PACKS={}
def read_pack(path):
    """block XML: 'parts.bin#name.xml' or a separate *.xml.gz file (older catalog layout)"""
    if '#' in path:
        bp,m=path.split('#',1)
        if bp.endswith('.zip'):   # intermediate catalog layout (parts.zip) — only for conversion to parts.bin
            import zipfile
            with zipfile.ZipFile(bp) as z: return z.read(m)
        if bp not in _PACKS:
            _PACKS[bp]=(open(bp,'rb').read(),_json.load(open(os.path.splitext(bp)[0]+'.idx',encoding='utf-8')))
        data,idx=_PACKS[bp]; o,n=idx[m]
        return zlib.decompress(data[o:o+n],-15)
    return gzip.decompress(open(path,'rb').read())
class PartPack:
    """a part from the compact catalog (samples/ni/parts.bin): bundle() — as for Doc"""
    def __init__(s,path):
        s.root=ET.fromstring(read_pack(path))
        i=s.root.find('Inst'); s.inst=i[0] if i is not None and len(i) else None
    def bundle(s,name=None):
        r=s.root; m=r.find('Model')
        return dict(sym=r.find('Sym')[0],ci=r.find('Ci')[0],ports=list(r.find('Ports')),model=m[0] if len(m) else None,
                    port_models={p.get('CiID'):p for p in r.find('PortModels')})

def pin_connectors(symitem):
    """yield (pinname, connector_elem, local position in symbol coords incl. symbol T?)"""
    res=[]
    def walk(e,t,pin):
        tt=getT(e)
        tloc=mul(tt,t) if tt else t
        if e.get('PinName') is not None: pin=e
        if e.get('Class')=='CIITPinConnectorComp':
            x,y=float(e.get('ptCenterX')),float(e.get('ptCenterY'))
            res.append((e,app(tloc,x,y),pin))
        for it in e.findall('Objects/Item'):
            walk(it[0],tloc,pin)
    sc=symitem[0]
    st=getT(sc) or [1,0,0,1,0,0]
    for it in sc.findall('Objects/Item'):
        walk(it[0],st,None)
    return res

ROT={0:[1,0,0,1,0,0],90:[0,1,-1,0,0,0],180:[-1,0,0,-1,0,0],270:[0,-1,1,0,0,0]}
MIRX=[-1,0,0,1,0,0]   # mirror left-right
TEXT_CLASSES=('CIITSymTextCompName','CIITSymTextCompValue','CIITSymTextCompLocation','CODTextComp','CIITVariableSymText')   # text is never rotated — only moved
def enc(s):
    """encode text into Multisim &ASC / &UNI string"""
    if all(ord(c)<128 for c in s): return '&ASC'+s
    out=''; i=0
    while i<len(s):
        if ord(s[i])<128: out+=s[i]; i+=1
        else:
            j=i
            while j<len(s) and ord(s[j])>=128: j+=1
            run=s[i:j]
            while run:
                part=run[:9]; run=run[9:]
                out+='_uc%d'%len(part)+''.join('%04x'%ord(c) for c in part)
            i=j
    return '&UNI'+out

class NoValue:
    """wrapper over a sample: hide the value (as for the npn in base_5_1a). CiComponent attributes — 53 slots in order;
    the npn has CiaDisplay ShowValues=0 in a slot, the pnp of sample_pnp has that slot empty — copy it from ref."""
    def __init__(s,lib,ref): s.lib=lib; s.ref=ref   # ref=(Doc, name) — an element with a hidden value
    def bundle(s,name):
        b=s.lib.bundle(name)
        b=dict(sym=copy.deepcopy(b['sym']),ci=copy.deepcopy(b['ci']),ports=b['ports'],model=b['model'])
        rat=list(s.ref[0].bundle(s.ref[1])['ci'][0].find('Attributes'))
        i=next(i for i,it in enumerate(rat) if len(it) and it[0].get('Class')=='CiaDisplay')
        at=b['ci'][0].find('Attributes'); assert len(at)==len(rat) and not len(at[i])
        at.remove(at[i]); at.insert(i,copy.deepcopy(rat[i]))
        for e in b['sym'].iter('CIITSymTextCompValue'):
            if e.get('Output'): e.set('Output','')
        return b

GRAPHIC=('CIITSymbolBorderRect','CODRectComp','CODEllipseComp','CODLineComp','CODMultiLineComp','CODPolygonComp','CODPolyLineComp')
SCHOTTKY_HOOKS=[(53,51,55,51),(55,51,55,53),(53,75,51,75),(51,75,51,73)]   # hooks at the base ends: top right-down, bottom left-up
class SchottkyLib:
    """instance of subcircuit SchottkyNPN (2N2222 + 10BQ015) from sample_schottky_subckt.ms14, symbol as in the textbook:
    npn 2N2222 graphics + hooks on the base, pins at the npn places (C top, B left, E bottom), pin names and value hidden.
    The subcircuit symbol is stored separately in every instance (CIITMacroComponent)."""
    def __init__(s,lib,inst,npn): s.lib=lib; s.inst=inst; s.npn=npn   # npn=(Doc, name) — 2N2222 from base_5_1a
    def bundle(s,name):
        b=s.lib.bundle(s.inst)
        b=dict(sym=copy.deepcopy(b['sym']),ci=copy.deepcopy(b['ci']),ports=b['ports'],model=None)
        q=s.npn[0].bundle(s.npn[1]); qs=q['sym'][0]; m=b['sym'][0]
        objs=m.find('Objects')
        for it in list(objs):
            if it[0].get('Class') in GRAPHIC: objs.remove(it)
        first_pin=next(i for i,it in enumerate(objs) if it[0].get('Class')=='CIITPinSymbolComp')
        gr=[copy.deepcopy(it) for it in qs.findall('Objects/Item') if it[0].get('Class') in GRAPHIC]
        line=next(it for it in gr if it[0].get('Class')=='CODLineComp')
        for x0,y0,x1,y1 in SCHOTTKY_HOOKS:
            h=copy.deepcopy(line)
            for k,v in zip(('pt0X','pt0Y','pt1X','pt1Y'),(x0,y0,x1,y1)): h[0].set(k,str(v))
            gr.append(h)
        for it in gr:
            it.set('ID',nid()); setT(it[0],[1,0,0,1,0,0]) if getT(it[0]) else None
            objs.insert(first_pin,it); first_pin+=1
        # pins — at the npn pin places, names/numbers hidden
        qpins={p[0].get('PinName'):p[0] for p in qs.findall('Objects/Item') if p[0].get('Class')=='CIITPinSymbolComp'}
        for p in objs:
            ps=p[0]
            if ps.get('Class')!='CIITPinSymbolComp': continue
            qp=qpins[ps.get('PinName')]
            for k in ('ShowName','ShowNumber','ShowNameUser','ShowNumberUser'): ps.set(k,'0')
            for it in ps.findall('Objects/Item'):
                cl=it[0].get('Class'); src=next(x[0] for x in qp.findall('Objects/Item') if x[0].get('Class')==cl)
                for k in ('ptCenterX','ptCenterY','pt0X','pt0Y','pt1X','pt1Y'):
                    if src.get(k) is not None: it[0].set(k,src.get(k))
                if cl in('CIITPinSymTextCompName','CIITPinSymTextCompNumber'): setT(it[0],getT(src))
        # labels — npn font and colour; the value («SchottkyNPN») hidden
        for tag in ('CIITSymTextCompName','CIITSymTextCompValue'):
            src=next(e for e in qs.iter(tag) if e.get('Class')); dst=next(e for e in m.iter(tag) if e.get('Class'))
            for k,v in src.attrib.items():
                if k.startswith('Font') or k in('PenColor','FgColor','HorizontalAlign'): dst.set(k,v)
            if tag=='CIITSymTextCompValue': dst.set('Output','')
        for k in ('PenColor','FgColor'):
            if (qs.get(k) or m.get(k)) is not None: m.set(k,qs.get(k) or m.get(k))
        rat=list(q['ci'][0].find('Attributes')); i=next(i for i,it in enumerate(rat) if len(it) and it[0].get('Class')=='CiaDisplay')
        at=b['ci'][0].find('Attributes'); assert not len(at[i])
        at.remove(at[i]); at.insert(i,copy.deepcopy(rat[i]))
        return b

class MultiEmitterLib:
    """instance of subcircuit MultiNPN4 (4×2N2222: common base and collector, emitters E1–E4) from sample_multiemitter.ms14.
    Symbol as in the textbook (fig. 5.14): a horizontal base bar, base on top, 4 emitters down-left with arrows,
    collector down-right. Pins (in cells from base pin B): B (0,0), bar at y=3, E1–E4 (−8,5) (−6,5) (−4,5) (−2,5),
    C (3,5). Pin names and value hidden (as for the npn).
    n=2 — two emitters (subcircuit from a derived base, see transplant_sheet): E1 (−4,5), E2 (−2,5); the extra ports E3, E4
    of the sample instance are removed. hooks=True — Schottky «hooks» at the bar ends (as in the textbook)."""
    def __init__(s,lib,inst,npn,n=4,hooks=False): s.lib=lib; s.inst=inst; s.npn=npn; s.n=n; s.hooks=hooks
    def bundle(s,name):
        b=s.lib.bundle(s.inst)
        drop={enc('E%d'%k) for k in range(s.n+1,5)}
        b=dict(sym=copy.deepcopy(b['sym']),ci=copy.deepcopy(b['ci']),ports=[p for p in b['ports'] if p[0].get('LocalName') not in drop],model=None)
        keep={p.get('CiID') for p in b['ports']}
        pl=b['ci'][0].find('Ports')
        for it in list(pl):
            if it.get('CiID') not in keep: pl.remove(it)
        mo=b['sym'][0].find('Objects')
        for it in list(mo):
            if it[0].get('Class')=='CIITPinSymbolComp' and it[0].get('PinName') in drop: mo.remove(it)
        q=s.npn[0].bundle(s.npn[1]); qs=q['sym'][0]; m=b['sym'][0]; objs=m.find('Objects')
        setT(m,[1,0,0,1,0,0])   # the sample macro element has no own matrix — give it one (as SchottkyNPN), everything inside is local
        for it in objs:
            if it[0].get('Class') in TEXT_CLASSES and getT(it[0]) is not None: setT(it[0],[1,0,0,1,0,0])
        for it in list(objs):
            if it[0].get('Class') in GRAPHIC: objs.remove(it)
        line=next(copy.deepcopy(it) for it in qs.findall('Objects/Item') if it[0].get('Class')=='CODLineComp')
        arrow=next(copy.deepcopy(it) for it in qs.findall('Objects/Item') if it[0].get('Class')=='CODMultiLineComp')
        B=27; g=[]   # coordinates in px (9 per cell), origin — the base pin
        def L(x0,y0,x1,y1):
            h=copy.deepcopy(line)
            for k,v in zip(('pt0X','pt0Y','pt1X','pt1Y'),(x0,y0,x1,y1)): h[0].set(k,'%g'%v)
            g.append(h)
        EX=(-72,-54,-36,-18)[4-s.n:]; x0=EX[0]-8
        L(x0,B,8,B)                                   # base bar
        if s.hooks: L(x0,B,x0,B+2); L(x0,B+2,x0+2,B+2); L(8,B,8,B-2); L(8,B-2,6,B-2)   # Schottky hooks at the bar ends
        for x in EX:                                  # emitters: from the bar down-left, arrow outwards
            L(x+8,B,x,B+12)
            a=copy.deepcopy(arrow); pts=a[0].find('Points')
            for p,(px,py) in zip(pts,((x+4.9,B+8.5),(x+1.2,B+10.2),(x+1.3,B+6.1))): p.set('X','%g'%px); p.set('Y','%g'%py)
            g.append(a)
        L(0,B,18,B+18)                                # collector
        br=next(copy.deepcopy(it) for it in qs.findall('Objects/Item') if it[0].get('Class')=='CIITSymbolBorderRect')
        for k,v in zip(('pt0X','pt0Y','pt1X','pt1Y'),(x0-1,0,27,45)): br[0].set(k,str(v))
        g.insert(0,br)
        first=next(i for i,it in enumerate(objs) if it[0].get('Class')=='CIITPinSymbolComp')
        for it in g:
            it.set('ID',nid()); setT(it[0],[1,0,0,1,0,0]); objs.insert(first,it); first+=1
        pins={'B':((0,0),(0,0,0,B)),'C':((27,45),(18,B+18,27,45))}
        for k,x in enumerate(EX): pins['E%d'%(k+1)]=((x,45),(x,B+12,x,45))
        for p in objs:
            ps=p[0]
            if ps.get('Class')!='CIITPinSymbolComp': continue
            (cx,cy),ln=pins[ps.get('PinName')[4:]]
            setT(ps,[1,0,0,1,0,0])
            for k in ('ShowName','ShowNumber','ShowNameUser','ShowNumberUser'): ps.set(k,'0')
            for it in ps.findall('Objects/Item'):
                e=it[0]; cl=e.get('Class')
                if getT(e) is not None: setT(e,[1,0,0,1,0,0])
                if cl=='CIITPinConnectorComp': e.set('ptCenterX',str(cx)); e.set('ptCenterY',str(cy))
                elif cl=='CODLineComp':
                    for k,v in zip(('pt0X','pt0Y','pt1X','pt1Y'),ln): e.set(k,str(v))
                elif getT(e) is not None: setT(e,[1,0,0,1,cx,cy])
        for tag in ('CIITSymTextCompName','CIITSymTextCompValue'):
            src=next(e for e in qs.iter(tag) if e.get('Class')); dst=next(e for e in m.iter(tag) if e.get('Class'))
            for k,v in src.attrib.items():
                if k.startswith('Font') or k in('PenColor','FgColor','HorizontalAlign'): dst.set(k,v)
            if tag=='CIITSymTextCompValue': dst.set('Output','')
        for k in ('PenColor','FgColor'):
            if (qs.get(k) or m.get(k)) is not None: m.set(k,qs.get(k) or m.get(k))
        rat=list(q['ci'][0].find('Attributes')); i=next(i for i,it in enumerate(rat) if len(it) and it[0].get('Class')=='CiaDisplay')
        at=b['ci'][0].find('Attributes'); assert not len(at[i])
        at.remove(at[i]); at.insert(i,copy.deepcopy(rat[i]))
        return b

# ---------- a subcircuit from a separate file (e.g. a hierarchical block) ----------
_TID=[640000000]   # own ID range: a derived base is made before Builder, which starts at 700 000 000
def transplant_sheet(D,title,src,rename=None,new_title=None):
    """Replace subcircuit sheet `title` in D (Doc of the base) with the content of the main sheet of src (Doc of another file, e.g.
    a hierarchical block): graphics (Components) and electrics (Elements) with new IDs; CIITHierConnector connectors
    renamed (rename — {old name: new}); the subcircuit named new_title (all strings with its name in the file).
    An instance on the main sheet is linked to the sheet only by name; sheet IDs are not used outside."""
    ds=next(x for x in D.root.iter('DesignSheet') if x.get('Title')==enc(title))
    h=ds.find('.//CIITHierDoc'); par={c:p for p in h.iter() for c in p}
    comp=h.find('.//Components/CODComposite'); el=h.find('.//Elements')
    sc,se=(src.comp,src.el) if isinstance(src,Doc) else src      # src — Doc (main sheet) or (Components, Elements)
    nc=copy.deepcopy(sc); ne=copy.deepcopy(se)
    ids={}
    for r in (nc,ne):
        for e in r.iter('Item'):
            for a in ('ID','CiID'):
                v=e.get(a)
                if v and e.get('Class') and v not in ids: _TID[0]+=8; ids[v]=str(_TID[0])
    rep=dict(ids); rep.update({enc(k):enc(v) for k,v in (rename or {}).items()})
    for r in (nc,ne):
        for e in r.iter():
            for a,v in e.attrib.items():
                if v in rep: e.set(a,rep[v])
    for old,new in ((comp,nc),(el,ne)):
        p=par[old]; i=list(p).index(old); p.remove(old); p.insert(i,new)
    if new_title:
        for e in D.root.iter():
            for a,v in e.attrib.items():
                if title in v: e.set(a,v.replace(title,new_title))

def sheet_parts(D,title):
    """(Components/CODComposite, Elements) of subcircuit sheet `title` — a source for transplant_sheet"""
    h=next(x for x in D.root.iter('DesignSheet') if x.get('Title')==enc(title)).find('.//CIITHierDoc')
    return h.find('.//Components/CODComposite'),h.find('.//Elements')

def copy_sheet(D,title,new_title):
    """A second subcircuit kind in one file: a copy of sheet `title` named new_title with everything Multisim and Builder
    link to a sheet — the sheet (new SheetID, ObjectID), the instance group CSheetComponentMSM, the SheetGroupInfo entry,
    the project tree item «name(SC1)» and the instance on the main sheet (Builder finds the group by it; it is removed itself).
    The content of the copy is then replaced by transplant_sheet."""
    R=D.root; par={c:p for p in R.iter() for c in p}
    ds=next(x for x in R.iter('DesignSheet') if x.get('Title')==enc(title))
    top=max(int(x.get('ObjectID')) for x in R.iter() if (x.get('ObjectID') or '').isdigit())
    ds2=copy.deepcopy(ds); ds2.set('Title',enc(new_title)); ds2.set('ObjectID',str(top+1)); ds2.set('SheetID',guid())
    if ds2.get('SaveID'): ds2.set('SaveID',guid())
    p=par[ds]; p.insert(list(p).index(ds)+1,ds2)
    g=next(x for x in R.iter('Group') if x.get('Class')=='CSheetComponentMSM' and x.get('SheetName')==enc(title))
    g2=copy.deepcopy(g); goid=str(top+2); g2.set('SheetName',enc(new_title)); g2.set('ObjectID',goid); g2.set('GUID',guid())
    par[g].append(g2)
    for x in list(R.iter('SheetGroupInfo')):
        if x.get('FirstSheetComponentObjectID')==g.get('ObjectID'):
            x2=copy.deepcopy(x); x2.set('FirstSheetComponentObjectID',goid); par[x].append(x2)
    inst=next(k for k in D.objs if k[0].get('SheetComponentObjectID')==g.get('ObjectID'))
    i2=copy.deepcopy(inst); i2[0].set('SheetComponentObjectID',goid); i2.find('.//CHierBlock').set('FileName',enc(new_title))
    D.objs.append(i2)
    t=next(x for x in R.iter('SWsTreeItem') if x.get('Name','').startswith(enc(title)+'('))
    t2=copy.deepcopy(t); t2.set('Name',t.get('Name').replace(enc(title),enc(new_title),1)); par[t].append(t2)

# ---------- elements without a sample: a base element from a sample with another SPICE template, model, names, drawing ----------
CUSTOM_MARK='* msgen\n'   # first template line of such an element (a SPICE comment): spice.py expands it itself
class SpiceLib:
    """An element missing from the samples. A base with the same number and names of pins is taken (resistor 1/2, npn or pnp C/B/E,
    diode A/K) and changed:
      template — Multisim SPICE template: %p — RefDes, %t<pin> — node, #k — k-th parameter (the value is #1 for a resistor base);
                 a subcircuit can be described right in the template (.subckt …%p … .ends — this is how the Multisim SPDT switch works);
      model    — (name, .MODEL text) instead of the base model; model=False — no model (everything is in the template);
      rename   — exact string replacements (family, type, RefDes prefix «R%d» → «C%d», description);
      show     — show the type on the sheet (as the value), e.g. '2N3904';
      unit     — value unit instead of «Ω» in the file strings (Multisim still builds the label on the sheet
                 in the units of the base type — ohms for a resistor, so the value of such an element is better hidden);
      draw     — function (symbol, body matrix, graphics stubs) → list of new graphic elements
                 instead of the resistor body rectangle."""
    def __init__(s,base,template=None,model=None,rename=None,show=None,unit=None,draw=None):
        s.base=base; s.template=template; s.model=model; s.rename=rename or {}; s.show=show; s.draw=draw
        if unit: s.unit=unit
    def bundle(s,_):
        src=s.base[0].bundle(s.base[1])
        b=dict(sym=copy.deepcopy(src['sym']),ci=copy.deepcopy(src['ci']),ports=src['ports'],
               model=copy.deepcopy(src['model']) if src['model'] is not None else None)
        c=b['ci'][0]; sc=b['sym'][0]
        rep={'&ASC'+k:'&ASC'+v for k,v in s.rename.items()}
        unit=getattr(s,'unit',None)
        if unit:      # resistor value «4kΩ» → «4k<unit>»
            rep[enc('4kΩ')]=enc('4k'+unit)
        old=next(e.get('String') for e in c.iter('CiaSpiceTmpltExprt'))
        if s.template is not None:
            new='&ASC'+CUSTOM_MARK+s.template
            for e in c.iter():   # the template and its copy in the string list (without the trailing newline)
                for a,v in e.attrib.items():
                    if v.rstrip('\n')==old.rstrip('\n'): e.set(a,new if v.endswith('\n') else new.rstrip('\n'))
        if s.model is False:
            b['model']=None
            if 'Model' in c.attrib: del c.attrib['Model']
            for e in c.iter():
                for a,v in e.attrib.items():
                    if v.startswith('&ASC.MODEL'): e.set(a,'')
        elif s.model:
            name,text=s.model; m=b['model']; m[0].set('LocalName','&ASC'+name)
            for e in m.iter():
                if (e.get('String') or '').startswith('&ASC.MODEL'): e.set('String','&ASC.MODEL '+name+' '+text)
            short=name.split('__')[0]
            for e in c.iter():
                for a,v in e.attrib.items():
                    if v.startswith('&ASC.MODEL'): e.set(a,'&ASC.MODEL '+short+' '+text)
        for e in list(c.iter())+list(sc.iter())+(list(b['model'].iter()) if b['model'] is not None else []):
            for a,v in e.attrib.items():
                if v in rep: e.set(a,rep[v])
        if s.show:
            for e in sc.iter('CIITSymTextCompValue'):
                if e.get('Class'): e.set('Output',enc(s.show))
            for d in c.iter('CiaDisplay'): d.set('ShowValues','1')
        if s.draw:
            objs=sc.find('Objects'); body=next(it for it in objs if it[0].get('Class')=='CODRectComp')
            T=getT(body[0]); i=list(objs).index(body); objs.remove(body)
            for it in s.draw(T):
                it.set('ID',nid()); setT(it[0],T); objs.insert(i,it); i+=1
        return b

_PROTO={}
def proto(cls):
    """graphics stub (segment, circle, polyline) — from the npn 2N2222 symbol of base_5_1a"""
    if not _PROTO:
        q=Doc(sample('base_5_1a')).bundle('&ASCQ3')['sym'][0]
        for it in q.findall('Objects/Item'): _PROTO.setdefault(it[0].get('Class'),it)
    return copy.deepcopy(_PROTO[cls])
def g_line(x0,y0,x1,y1):
    it=proto('CODLineComp')
    for k,v in zip(('pt0X','pt0Y','pt1X','pt1Y'),(x0,y0,x1,y1)): it[0].set(k,'%g'%v)
    return it
def g_circle(cx,cy,r):
    it=proto('CODEllipseComp')
    for k,v in zip(('CenterX','CenterY','Radius1','Radius2'),(cx,cy,r,r)): it[0].set(k,'%g'%v)
    return it
def g_poly(pts):
    it=proto('CODMultiLineComp'); P=it[0].find('Points'); tpl=P[0]
    for p in list(P): P.remove(p)
    for x,y in pts:
        p=copy.deepcopy(tpl); p.set('X','%g'%x); p.set('Y','%g'%y); P.append(p)
    return it
# drawings in the resistor body coordinate system: pin axis — x (pin 1 — x=36, pin 2 — x=81), y=54 — middle,
# the body took x 45…72, y 49…59; the body matrix turns this vertical (pin 1 on top)
def draw_vsin(T):
    wave=[(58-4*math.sin(2*math.pi*k/8),47+1.75*k) for k in range(9)]
    return [g_circle(58,54,13),g_line(71,54,72,54),g_poly(wave),g_line(40,39,40,45),g_line(37,42,43,42)]

def _subst(sym,comp,subst):
    """parameters of a part without a value (source amplitude etc.): {'old': 'new'} — values equal to the old one
    (numerically too: '.2' = '0.2') and the start of the value label on the sheet ('.2Vpk …' → '10Vpk …')"""
    from geom import dec
    def num(v):
        try: return float(v)
        except ValueError: return None
    for old,new in subst.items():
        n=num(old)
        for e in list(sym.iter())+list(comp.iter()):
            for a,v in e.attrib.items():
                if not v.startswith('&'): continue
                d=dec(v)
                if d==old or (a=='Value' and n is not None and num(d)==n): e.set(a,enc(new))
                elif a=='Output' and d.startswith(old) and not d[len(old):len(old)+1].isdigit(): e.set(a,enc(new+d[len(old):]))

class Builder:
    def __init__(s,base,libs,origin=(0,0),tpl=None):
        """tpl — Doc to take wire/junction templates from (when base has none, e.g. a base with a subcircuit)"""
        reset_ids(os.path.basename(base))
        s.D=Doc(base); s.libs=libs
        s.ox,s.oy=origin   # shift of the whole scheme on the sheet, in cells
        D=s.D; W=tpl or D
        # templates for wiring objects
        s.t_link=copy.deepcopy(next(k for k in W.objs if k.get('Class')=='CIITLinkComp'))
        s.t_junc=copy.deepcopy(next(k for k in W.objs if k.get('Class')=='CODPinComp'))
        s.t_ntext=copy.deepcopy(next(k for k in W.objs if k.get('Class')=='CODNodeTextComp'))
        s.t_end=copy.deepcopy(next(k for k in W.refs if k.get('Class')=='CODPinComp'))
        s.t_node=copy.deepcopy(next(k for k in W.el if k.get('Class')=='CiNode'))
        # subcircuits: every instance has its own CSheetComponentMSM group and project tree item — templates and removal of the old ones
        R=D.root; par={c:p for p in R.iter() for c in p}
        main_ids={k[0].get('SheetComponentObjectID') for k in D.objs if k.get('Class')=='CIITMacroComponent'}
        s.sc_groups={}; s.sc_store=None; s.sc_tree={}; s.sc_first={}; s.sc_gone=[]; s.sc_next=1110332908; s.skip=set()
        for g in list(R.iter('Group')):
            if g.get('Class')=='CSheetComponentMSM' and g.get('ObjectID') in main_ids:
                s.sc_groups.setdefault(g.get('SheetName'),copy.deepcopy(g)); s.sc_store=par[g]; par[g].remove(g); s.sc_gone.append(g.get('GUID'))
                s.sc_first.setdefault(g.get('SheetName'),[]).extend(x for x in R.iter('SheetGroupInfo') if x.get('FirstSheetComponentObjectID')==g.get('ObjectID'))
        for it in list(R.iter('Item')):   # net labels and views inside removed instances (as for HB in finalize)
            tp=it.get('TreeInstanceProxy')
            if tp and any(g in tp for g in s.sc_gone): par[it].remove(it)
        P=R.find('Project')
        for vs in list(P.findall('ViewState')):
            if any(pe.get('ID') in main_ids for pe in vs.iter('PathElement')): P.remove(vs)
        for it in list(R.iter('SWsTreeItem')):
            m=re.match(r'^(&ASC.+)\((.+)\)$',it.get('Name',''))
            if m and m.group(1) in s.sc_groups:
                s.sc_tree.setdefault(m.group(1),(par[it],copy.deepcopy(it))); par[it].remove(it)
        s.circ=next(k for k in D.el if k.get('Class')=='CiCircuit')
        s.cid=s.circ.get('CiID')
        for k in list(D.objs): D.objs.remove(k)
        for k in list(D.refs): D.refs.remove(k)
        for k in list(D.el):
            if k is not s.circ: D.el.remove(k)
        c=s.circ[0]
        for tag in ('Models','Nodes','Components'):
            for k in list(c.find(tag)): c.find(tag).remove(k)
        s.models={}   # LocalName -> CiID
        s.parts={}    # name -> dict(sym,comp,ports,pins)
        s.order=[]
    def _model(s,m):
        nm=m[0].get('LocalName')
        if nm in s.models: return s.models[nm]
        mm=copy.deepcopy(m); new=nid(); mm.set('CiID',new); mm[0].set('Scope',s.cid)
        s.D.el.append(mm); s.models[nm]=new
        ET.SubElement(s.circ[0].find('Models'),'Item',{'CiID':new})
        return new
    def place(s,name,tpl,ref_pin,x,y,rot=0,mirror=False,value=None,label='right',refdes=None,glob=None,g=9,subst=None):
        x,y=(x+s.ox)*g,(y+s.oy)*g
        refdes=refdes or name
        lib,tname,tval=tpl[:3]
        unit=tpl[3] if len(tpl)>3 else getattr(lib,'unit','Ω')   # value unit on the sheet
        b=lib.bundle(tname)
        sym=copy.deepcopy(b['sym']); comp=copy.deepcopy(b['ci']); ports=[copy.deepcopy(p) for p in b['ports']]
        sid=nid(); cid=nid(); pmap={p.get('CiID'):nid() for p in ports}
        sym.set('ID',sid)
        for it in sym.iter('Item'):
            if it is not sym and it.get('ID'): it.set('ID',nid())
        for e in sym.iter():    # pin label GUIDs (ModifierInfo) — unique per copy, as for elements from Multisim
            if e.get('Guid'): e.set('Guid',guid())
        for e in sym.iter():
            if e.get('CiComponent'): e.set('CiComponent',cid)
            if e.get('PortID') in pmap: e.set('PortID',pmap[e.get('PortID')])
            if e.get('Class')=='CIITPinConnectorComp':
                cl=e.find('ConnectList')
                if cl is not None:
                    for k in list(cl): cl.remove(k)
        comp.set('CiID',cid); c=comp[0]
        c.set('SymCompID',sid); c.set('InstanceID',guid()); c.set('Circuit',s.cid); c.set('LocalName',enc(refdes))
        if b['model'] is not None: c.set('Model',s._model(b['model']))
        for it in c.find('Ports'): it.set('CiID',pmap[it.get('CiID')])
        for p in ports:
            p.set('CiID',pmap[p.get('CiID')]); p[0].set('Component',cid)
            pm=b.get('port_models',{}).get(p[0].get('Model'))
            if pm is not None: p[0].set('Model',s._model(pm))
            for k in list(p[0].find('Nodes')): p[0].find('Nodes').remove(k)
        # name & value
        for e in sym.iter('CIITSymTextCompName'):
            if e.get('Output'): e.set('Output',enc(refdes))
        if value is not None and tval is not None:
            ov_uni=enc(tval+unit); nv_uni=enc(value+unit)
            rep={'&ASC'+tval:'&ASC'+value, ov_uni:nv_uni}
            for e in list(sym.iter())+list(comp.iter()):
                for a,v in e.attrib.items():
                    if v in rep: e.set(a,rep[v])
        if subst: _subst(sym,comp,subst)
        # geometry: rotation/mirror applied to direct inner objects
        R=ROT[rot]
        if mirror: R=mul(MIRX,R)
        sc=sym[0]
        st=getT(sc)
        LAYER='AnimationLayers/CODComposite/Objects/Item/CIITAnimationLayerComp/Objects/Item'
        inner=sc.findall('Objects/Item')+sc.findall(LAYER)
        for it in inner:
            e=it[0]; t=getT(e)
            if t is None: continue
            if e.get('Class') in TEXT_CLASSES:
                nx,ny=app(R,t[4],t[5]); setT(e,[t[0],t[1],t[2],t[3],nx,ny])
            else:
                setT(e,mul(t,R))
        if st is not None: setT(sc,[1,0,0,1,0,0])
        pins=pin_connectors(sym)
        loc={p.get('PinName'):(px,py) for e,(px,py),p in pins}
        key=enc(ref_pin) if not ref_pin.startswith('&') else ref_pin
        if key not in loc: raise ValueError('element %s has no pin %s; available: %s'%(name,ref_pin,', '.join(sorted(k[4:] for k in loc))))
        px,py=loc[key]
        tx,ty=x-px,y-py
        if st is not None: setT(sc,[1,0,0,1,tx,ty])
        else:
            # animation symbol: no own transformer -> shift inner objects
            for it in inner:
                e=it[0]; t=getT(e)
                if t is not None: setT(e,t[:4]+[t[4]+tx,t[5]+ty])
        if sc.get('Class')=='CIITMacroComponent': s._sheetcomp(sc,refdes)
        s.D.objs.append(sym); s.D.el.append(comp)
        for p in ports: s.D.el.append(p)
        ET.SubElement(s.circ[0].find('Components'),'Item',{'CiID':cid})
        pins=pin_connectors(sym)
        s.parts[name]=dict(refdes=refdes,sym=sym,comp=comp,ports={p[0].get('LocalName'):p for p in ports},
                           pins={p.get('PinName'):(e,(round(px),round(py))) for e,(px,py),p in pins},
                           loc=loc,T=(tx,ty) if st is not None else None,extent=local_extent(sym,tx,ty) if st is not None else None)
        s.order.append(name)
        if glob: s.parts[name]['global']=glob
        if label: s.set_label(name,label)
        return s.parts[name]
    LABEL_SIDES=('right','left','top','bottom')
    def label_pos(s,name,side,texts=None):
        """label position (name; the value 15 px lower) in symbol coordinates: right/left/top/bottom of
        the rectangle around the pins and the symbol drawing (a transistor — its circle). texts — label lines
        (for «left»: the label is pushed to the symbol by the estimated text width)"""
        p=s.parts[name]; loc=p['loc']
        xs=[v[0] for v in loc.values()]; ys=[v[1] for v in loc.values()]
        if p.get('extent'): bx=p['extent']; xs+=[bx[0],bx[2]]; ys+=[bx[1],bx[3]]
        x0,x1,y0,y1=min(xs),max(xs),min(ys),max(ys)
        lines=[l for t in (texts or ['', '']) for l in t.rstrip().split('\n')] or ['']   # a value may span several lines
        h=13+15*(max(1,len(lines))-1)          # block height: 1 line (name) or 2 (name + value) and more
        if side=='right': return x1+5,(y0+y1)/2-h/2
        if side=='left':
            w=max([7.5*len(t.strip()) for t in lines]+[30])
            return x0-6-w,(y0+y1)/2-h/2
        if side=='top': return (x0+x1)/2-12,y0-4-h
        return (x0+x1)/2-12,y1+4
    def label_texts(s,name):
        """visible label lines of an element (name, value; for interactive sources also the reading «0.7V»)"""
        out=[]
        for e in s.parts[name]['sym'][0].findall('Objects/Item'):
            if e[0].get('Class') in ('CIITSymTextCompName','CIITSymTextCompValue','CIITVariableSymText') and e[0].get('Output'):
                from geom import dec
                out.append(dec(e[0].get('Output')))
        return out
    def set_label(s,name,side):
        p=s.parts[name]
        if p['T'] is None: return        # a switch (no own matrix) — its label is not moved
        lx,ly=s.label_pos(name,side,s.label_texts(name)); sc=p['sym'][0]; p['label']=side
        from geom import dec
        val=next((dec(e[0].get('Output')) for e in sc.findall('Objects/Item') if e[0].get('Class')=='CIITSymTextCompValue'),'')
        for cls,dy in (('CIITSymTextCompName',0),('CIITSymTextCompValue',15),
                       ('CIITVariableSymText',15+15*len(val.rstrip().split('\n')) if val.strip() else 15)):   # the reading — below the value
            for e in sc.findall('Objects/Item'):
                if e[0].get('Class')==cls:
                    t=getT(e[0]); setT(e[0],t[:4]+[round(lx),round(ly+dy)]); e[0].set('HorizontalAlign','0')
    def _sheetcomp(s,sc,refdes):
        """a subcircuit instance gets its own CSheetComponentMSM group (+ a project tree item)"""
        name=sc.find('HierBlock/CHierBlock').get('FileName')
        g=copy.deepcopy(s.sc_groups[name]); oid=str(s.sc_next); s.sc_next+=1
        g.set('ObjectID',oid); g.set('GUID',guid()); s.sc_store.append(g); sc.set('SheetComponentObjectID',oid)
        s.sc_inst=getattr(s,'sc_inst',{}); s.sc_inst[refdes]=(name,g.get('GUID'))
        for x in s.sc_first.pop(name,[]): x.set('FirstSheetComponentObjectID',oid)   # the subcircuit sheet group — from the first instance
        if name in s.sc_tree:
            parent,t=s.sc_tree[name]; t=copy.deepcopy(t); t.set('Name',name+'('+refdes+')'); parent.append(t)
    def pin(s,name,pin):
        if name not in s.parts: raise ValueError('wire to an unknown element %s'%name)
        pins=s.parts[name]['pins']
        if enc(pin) not in pins:
            raise ValueError('element %s has no pin %s; available: %s'%(name,pin,', '.join(sorted(k[4:] if k.startswith('&ASC') else k for k in pins))))
        return pins[enc(pin)][1]
    # ---------- wiring ----------
    def wires(s,polys,g=9):
        """polys: list of lists; first/last element = terminal ('part','pin') or ('J',x,y); middle = (x,y) bends"""
        ox,oy=s.ox,s.oy
        polys=[[ (t if (t[0]!='J' and isinstance(t[0],str) and len(t)==2) else (('J',(t[1]+ox)*g,(t[2]+oy)*g) if t[0]=='J' else ((t[0]+ox)*g,(t[1]+oy)*g))) for t in pl] for pl in polys]
        D=s.D
        def tpos(t):
            if t[0]=='J': return (t[1],t[2])
            return s.pin(t[0],t[1])
        # wires to skipped elements (s.skip, e.g. the Schottky diode when the transistor is a subcircuit) are dropped,
        # a junction left with 2 wires becomes a bend of one wire (a junction has 3 or 4 wires)
        polys=[pl for pl in polys if not any(t[0] in s.skip for t in (pl[0],pl[-1]))]
        for pl in polys:                     # all wire ends are existing pins (a clear error right away)
            for t in (pl[0],pl[-1]):
                if t[0]!='J': s.pin(t[0],t[1])
        while True:
            deg={}
            for i,pl in enumerate(polys):
                for t in (pl[0],pl[-1]):
                    if t[0]=='J': deg.setdefault(t,[]).append(i)
            bad={t:v for t,v in deg.items() if len(v) not in (3,4)}
            if any(len(v)!=2 for v in bad.values()): raise ValueError('junction without 3–4 wires: %s'%[(t[1]//g-ox,t[2]//g-oy,len(v)) for t,v in bad.items()])
            if not bad: break
            t,(i,j)=next(iter(bad.items()))
            a,b=polys[i],polys[j]
            if a[-1]!=t: a=a[::-1]
            if b[0]!=t: b=b[::-1]
            pts=a[:-1]+[(t[1],t[2])]+b[1:]
            pos=[tpos(x) if isinstance(x[0],str) else x for x in pts]
            keep=[pts[0]]+[pts[k] for k in range(1,len(pts)-1)
                           if not (pos[k-1][0]==pos[k][0]==pos[k+1][0] or pos[k-1][1]==pos[k][1]==pos[k+1][1])]+[pts[-1]]
            polys=[pl for k,pl in enumerate(polys) if k not in (i,j)]+[keep]
        # union-find on terminals
        par={}
        def f(a):
            par.setdefault(a,a)
            while par[a]!=a: par[a]=par[par[a]]; a=par[a]
            return a
        def key(t): return ('J',t[1],t[2]) if t[0]=='J' else (t[0],t[1])
        for pl in polys:
            a,b=key(pl[0]),key(pl[-1]); par[f(a)]=f(b)
        # also nets named
        groups={}
        for pl in polys:
            for t in (pl[0],pl[-1]): groups.setdefault(f(key(t)),set()).add(key(t))
        # junction objects
        junc={}
        for pl in polys:
            for t in (pl[0],pl[-1]):
                if t[0]=='J' and key(t) not in junc:
                    j=copy.deepcopy(s.t_junc); jid=nid(); j.set('ID',jid)
                    j[0].set('CenterX',str(t[1])); j[0].set('CenterY',str(t[2]))
                    cl=j[0].find('ConnectList')
                    for k in list(cl): cl.remove(k)
                    junc[key(t)]=j; D.objs.append(j)
        # nets
        nets=[]; netid={}; num=[0]
        for root_,mem in groups.items():
            names=set()
            for m in mem:
                if m[0]!='J' and s.parts[m[0]].get('global'): names.add(s.parts[m[0]]['global'])
            if {'VCC','0'}<=names:
                raise ValueError('short circuit VCC — ground: %s'%', '.join(sorted('%s.%s'%(m[0],m[1]) for m in mem if m[0]!='J')))
            if 'VCC' in names: nm='VCC'
            elif '0' in names: nm='0'
            else: num[0]+=1; nm=str(num[0])
            node=copy.deepcopy(s.t_node); nidn=nid(); node.set('CiID',nidn)
            node[0].set('LocalName','&ASC'+nm); node[0].set('Circuit',s.cid)
            pl_=node[0].find('Ports')
            for k in list(pl_): pl_.remove(k)
            nt=copy.deepcopy(s.t_ntext); ntid=nid(); nt.set('ID',ntid)
            ll=nt[0].find('Links')
            for k in list(ll): ll.remove(k)
            nets.append(dict(node=node,nt=nt,name=nm,mem=mem,ntpos=None))
            netid[root_]=nets[-1]
            D.el.append(node); ET.SubElement(s.circ[0].find('Nodes'),'Item',{'CiID':nidn})
            for m in sorted(mem,key=str):            # order does not depend on string hashes — the build is reproducible
                if m[0]!='J':
                    port=s.parts[m[0]]['ports'][enc(m[1])]
                    ET.SubElement(port[0].find('Nodes'),'Item',{'CiID':nidn})
                    ET.SubElement(pl_,'Item',{'CiID':port.get('CiID')})
        # links
        for pl in polys:
            net=netid[f(key(pl[0]))]
            ends=[]
            for t in (pl[0],pl[-1]):
                e=copy.deepcopy(s.t_end); eid=nid(); e.set('ID',eid)
                x,y=tpos(t); e[0].set('CenterX',str(x)); e[0].set('CenterY',str(y))
                cl=e[0].find('ConnectList')
                for k in list(cl): cl.remove(k)
                if t[0]=='J':
                    ET.SubElement(cl,'Item',{'ID':junc[key(t)].get('ID'),'Class':'CODPinComp'})
                    ET.SubElement(junc[key(t)][0].find('ConnectList'),'Item',{'ID':eid,'Class':'CODPinComp'})
                else:
                    conn=s.parts[t[0]]['pins'][enc(t[1])][0]
                    ET.SubElement(cl,'Item',{'ID':conn_id(s,t[0],t[1]),'Class':'CIITPinConnectorComp'})
                    ET.SubElement(conn.find('ConnectList'),'Item',{'ID':eid,'Class':'CODPinComp'})
                D.refs.append(e); ends.append(e)
            L=copy.deepcopy(s.t_link); lid=nid(); L.set('ID',lid)
            c=L[0]; c.set('Connect1',ends[0].get('ID')); c.set('Connect2',ends[1].get('ID'))
            c.set('Node',net['node'].get('CiID')); c.set('NodeText',net['nt'].get('ID'))
            pts=c.find('Points')
            for k in list(pts): pts.remove(k)
            coords=[tpos(pl[0])]+[tuple(p) for p in pl[1:-1]]+[tpos(pl[-1])]
            for (x,y) in coords: ET.SubElement(pts,'Item',{'X':str(x),'Y':str(y)})
            for g in c.iter('Item'):
                if g.get('Guid'): g.set('Guid',guid())   # every wire has its own label (as in Multisim files)
            ET.SubElement(net['nt'][0].find('Links'),'Item',{'ID':lid,'Class':'CIITLinkComp'})
            if net['ntpos'] is None: net['ntpos']=coords[0]
            D.objs.append(L)
        for net in nets:
            x,y=net['ntpos']; t=getT(net['nt'][0]); setT(net['nt'][0],t[:4]+[x+3,y-14])
            D.objs.append(net['nt'])
        s.nets=nets

def local_extent(sym,tx,ty):
    """extent of the symbol drawing (segments and circles, without labels) in symbol coordinates"""
    import geom
    sy=geom.Sym(sym,{})
    xs=[v for g in sy.segs for v in (g[0],g[2])]+[c[0]+d*c[2] for c in sy.circles for d in (-1,1)]
    ys=[v for g in sy.segs for v in (g[1],g[3])]+[c[1]+d*c[3] for c in sy.circles for d in (-1,1)]
    return (min(xs)-tx,min(ys)-ty,max(xs)-tx,max(ys)-ty) if xs else None

def conn_id(b,part,pin):
    # find the Item ID wrapping the connector element
    conn=b.parts[part]['pins'][enc(pin)][0]
    for it in b.parts[part]['sym'].iter('Item'):
        if len(it) and it[0] is conn: return it.get('ID')
    raise KeyError

# Custom 14×11 inch sheet = 1344×1056 px — taken from a file saved by Multisim after enlarging the sheet
SHEET=(14,11)
def set_sheet(R,w,h):
    """sheet size in inches: TBSize of CIITDiagram and Sheet Size/Width/Height in CircPrefs"""
    dg=next(e for e in R.iter('CIITDiagram') if e.get('TBSize') is not None)
    st={e.get('Key')[4:]:e for e in dg.find('CircPrefs').iter('Element')}
    dpi=float(st['Sheet Width Pixels In Inch'][0].get('Value')[4:])
    vals={'Sheet Size':'Custom','Sheet Width In Inch':'%g'%w,'Sheet Height In Inch':'%g'%h,
          'Sheet Width':'%d'%round(w*dpi),'Sheet Height':'%d'%round(h*dpi)}
    dg.set('TBSize','&ASCCustom')
    for k,v in vals.items(): st[k][0].set('Value','&ASC'+v)

def set_tmax(R,tmax):
    """Set the interactive simulation TMAX manually (Simulate → Interactive Simulation Settings). The default is
    «calculate»: Multisim picks the step itself and, when no source delivers current (CMOS at rest, output 0),
    does not start: «This circuit has no power sources: unable to determine the simulation timestep automatically».
    Interactive settings — the block with TSTOP=1e+30 in the sheet SimState."""
    n=0
    for dg in R.iter('CIITDiagram'):
        st=dg.get('SimState')
        if not st: continue
        st,k=re.subn(r'(TSTOP:double\{1e\+30\}\nTSTART:double\{0\}\nTMAX:)string\{calculate\}',
                     lambda m:m.group(1)+'double{%g}'%tmax,st)
        if k: dg.set('SimState',st); n+=k
    assert n,'Interactive Simulation Settings block (TMAX) not found'

def net_names(b):
    """A net where pins of two or more subcircuits meet makes Multisim ask for a name on opening (connector names
    inside instances «Q1_l_C», «Q2_l_B»). Write the choice in advance the way Multisim does after the answer:
    NetLabels/Item[TreeInstanceProxy=main sheet/instance/subcircuit sheet]/Items/CSchDesignNetLabel with ID = Guid
    of the connector label, Modifier=16; LastOverruleName = the chosen name for all, Priority=1 for the other connectors."""
    inst=getattr(b,'sc_inst',{})
    if not inst: return
    R=b.D.root; nl=R.find('.//CDesignNetContainer/NetLabels')
    main_sc=next(g.get('GUID') for g in R.iter('Group') if g.get('Class')=='CSheetComponent')
    main_sh=next(ds.get('SheetID') for ds in R.iter('DesignSheet') if b.D.h in set(ds.iter()))
    subs={}
    for ds in R.iter('DesignSheet'):
        h=ds.find('.//CIITHierDoc')
        if h is None or h is b.D.h or ds.get('Title') is None: continue
        conn={}
        for k in h.find('.//Components/CODComposite/Objects'):
            if k.get('Class')!='CIITHierConnector': continue
            nm=next(e.get('Output') for e in k.iter('CIITSymTextCompName') if e.get('Output'))
            g=next(e.get('Guid') for e in k.iter('Item') if e.get('Guid'))
            conn[nm]=g
        subs[ds.get('Title')]=(ds.get('SheetID'),conn)
    items={}   # instance -> Items (one entry per instance)
    for net in b.nets:
        if net['name'] in ('VCC','0'): continue
        ports=sorted(m for m in net['mem'] if m[0]!='J' and b.parts[m[0]]['sym'][0].get('Class')=='CIITMacroComponent')
        if len(ports)<2: continue
        win=enc(b.parts[ports[0][0]]['refdes']+'_l_'+ports[0][1])
        for k,(part,pin) in enumerate(ports):
            sub,gg=inst[b.parts[part]['refdes']]; sid,conn=subs[sub]
            if gg not in items:
                it=ET.SubElement(nl,'Item',{'TreeInstanceProxy':'&ASC%s/%s/%s/%s/'%(main_sc,main_sh,gg,sid)})
                items[gg]=ET.SubElement(it,'Items')
            ET.SubElement(items[gg],'CSchDesignNetLabel',{'Class':'CSchDesignNetLabel','Modifier':'16','Value':'',
                'ID':conn[enc(pin)],'Priority':'1' if k else '0','LastOverruleName':win,'LastNetName':win,'LastLocalName':enc(pin)})

GUID_RE=re.compile(r'\{[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\}')
def renew_guids(R,seed):
    """All GUIDs of the document (project, sheets, subcircuit groups, instances, pin labels) — new and consistent: the same
    old value gets the same new one everywhere (references like TreeInstanceProxy «{project}/{sheet}/{group}» stay valid).
    Without this all schemes on one base had identical GUIDs — among themselves and with the sample file;
    Multisim, with several such files open, mixed them up (the multimeter stopped the simulation, readings froze,
    opening hung). New GUIDs depend on the file name — the build stays reproducible."""
    rng=random.Random('guid:'+seed); new={}
    def sub(m):
        k=m.group(0).upper()
        if k not in new: new[k]='{'+str(uuid.UUID(int=rng.getrandbits(128),version=4)).upper()+'}'
        return new[k]
    for e in R.iter():
        for a,v in e.attrib.items():
            if '{' in v and GUID_RE.search(v): e.set(a,GUID_RE.sub(sub,v))

_XMM_DATA=[]
def instruments(b):
    """Instrument settings (InstrumentsData of the main sheet): every multimeter has its own entry
    «<RefDes>#1/<main sheet name>:», as in Multisim files (template — XMM1 from base_5_1a); entries without an instrument are removed."""
    ins=b.D.h.find('InstrumentsData')
    if ins is None: return
    if not _XMM_DATA:
        _XMM_DATA.append(copy.deepcopy(Doc(sample('base_5_1a')).h.find('InstrumentsData')[0]))
    title=next(ds.get('Title') for ds in b.D.root.iter('DesignSheet') if b.D.h in set(ds.iter()))
    from geom import dec
    meters=[p['refdes'] for p in b.parts.values() if 'inst' not in p and p['comp'][0].find('.//CiaCollString') is not None
            and any((x.get('Value') or '')=='&ASCXMM%d' for x in p['comp'][0].iter())]
    for x in list(ins): ins.remove(x)
    for r in meters:
        n=copy.deepcopy(_XMM_DATA[0]); n.set('CompLongName',enc('%s#1/%s:'%(r,dec(title))))
        for e in n.iter('Element'):
            if e.get('Key')=='&ASCNI_EWB_CURRENTDISPLAYDATA_VALUE': e[0].set('Data','&ASC0 V')
        ins.append(n)
    for p in b.parts.values():   # catalog instruments: the donor entry, keyed by own RefDes
        if 'inst' in p:
            n=copy.deepcopy(p['inst']); n.set('CompLongName',enc('%s#1/%s:'%(p['refdes'],dec(title)))); ins.append(n)
    for n in getattr(b,'probe_data',[]): ins.append(n)   # probe data (Builder.probe)

# ---------- probes (Place → Probe) ----------
# The probe kind is a code at the end of NI_EWB_DATABASEDATA_EXT (1 V, 2 I, 3 V and I, 4 P, 5 digital, 6 reference) and in
# the high digits of NI_EWB_REALTED_ANALYSIS_DATA; a probe is tied to a net only by the position of its tip (Transformer-M20/M21)
# on a wire (a power probe — on an element pin). Samples — probes placed in Multisim by hand.
PROBES={'V':('sample_probes','PR1'),'I':('sample_probes','PR2'),'P':('sample_probes','PR3'),
        'D':('sample_probes','PR5'),'REF':('sample_probes','Ref1'),'VREF':('sample_probes','PR4'),
        'VI':('sample_probe_vi','PR2')}
_PROBE_TPL={}
def probe_tpl(kind):
    """(symbol, CiProbeExtComp, InstrumentsData entry) of a probe of kind `kind` from the sample"""
    if kind not in _PROBE_TPL:
        f,nm=PROBES[kind]; D=Doc(sample(f))
        sym=next(k for k in D.objs if k.get('Class')=='CIITProbeExtComponent'
                 and D.byci[k[0].get('CiProbeExtComp')][0].get('LocalName')==enc(nm))
        ci=D.byci[sym[0].get('CiProbeExtComp')]
        ins=next(n for n in D.h.find('InstrumentsData') if n.get('CompLongName')==sym[0].get('FileDataPackageID'))
        _PROBE_TPL[kind]=(sym,ci,ins)
    return [copy.deepcopy(x) for x in _PROBE_TPL[kind]]

def _probe(b,name,kind,x,y,ref=None,g=9):
    """probe kind ('V','I','VI','P','D','REF'; ref — name of the REF probe for the voltage relative to it)
    with its tip in cell (x, y): on a wire (current direction as for a Multisim probe by default) or, for P, on
    an element pin"""
    px,py=(x+b.ox)*g,(y+b.oy)*g
    where=None
    for k in b.D.objs:
        if k.get('Class')!='CIITLinkComp': continue
        pts=[(float(p.get('X')),float(p.get('Y'))) for p in k[0].find('Points')]
        for (x0,y0),(x1,y1) in zip(pts,pts[1:]):
            if y0==y1==py and min(x0,x1)<=px<=max(x0,x1): where=where or 'H'
            if x0==x1==px and min(y0,y1)<=py<=max(y0,y1): where=where or 'V'
    if kind=='P' and any(xy==(px,py) for p in b.parts.values() for _,xy in p['pins'].values()): where='pin'
    if where is None: raise ValueError('probe %s: cell (%d,%d) has no wire%s'%(name,x,y,' or pin' if kind=='P' else ''))
    sym,ci,ins=probe_tpl('VREF' if ref else kind)
    sid=nid(); cid=nid(); c=sym[0]; sym.set('ID',sid)
    c.set('Transformer-M20','%g'%px); c.set('Transformer-M21','%g'%py); c.set('CiProbeExtComp',cid)
    d={'H':c.get('Direction_perfer_H'),'V':c.get('Direction_perfer_V'),'pin':'0'}[where]
    for a in ('Direction','Direction_original','Direction_latest'): c.set(a,d)
    c.set('InfoBoxText',''); b.probe_n=getattr(b,'probe_n',0)+1; c.set('UniqueID',str(100+b.probe_n))
    pkg=enc('X_%08x'%(0x70000000+b.probe_n)); c.set('FileDataPackageID',pkg); ins.set('CompLongName',pkg)
    for e in list(c.iter('Element'))+list(ins.iter('Element')):
        if e.get('Key')=='&ASCNI_EWB_COMPHANDLE_EXT': e[0].set('Data',sid)
        if ref and e.get('Key')=='&ASCNI_EWB_DATABASEDATA_EXT': e[0].set('Data',e[0].get('Data').replace('[]_Ref1[]_','[]_%s[]_'%ref))
    ci.set('CiID',cid); ci[0].set('LocalName',enc(name)); ci[0].set('SymCompID',sid); ci[0].set('InstanceID',guid())
    ci[0].set('Circuit',b.cid)
    b.D.objs.append(sym); b.D.el.append(ci)
    ET.SubElement(b.circ[0].find('ProbeExts'),'Item',{'CiID':cid})
    b.probe_data=getattr(b,'probe_data',[])+[ins]
Builder.probe=_probe

def finalize(b,title,outpath,rename=False,hb=True,preview=True,netext=True,msext=True,sheet=SHEET,tmax=None):
    D=b.D; R=D.root
    P=R.find('Project')
    if sheet: set_sheet(R,*sheet)
    if tmax: set_tmax(R,tmax)
    parent={c:pp for pp in R.iter() for c in pp}
    if rename:
        P.set('Name',enc(title))
        for ds in R.iter('DesignSheet'):
            if ds.get('Title'): ds.set('Title',enc(title))
        for it in R.iter('SWsTreeItem'):
            if it.get('Name','').startswith('&UNI_uc5042104450435043c0430_5.1'): it.set('Name',enc(title))
    if hb:
        hb_ids=set(); hb_guids=set()
        used={e.get('SheetComponentObjectID') for e in R.iter() if e.get('SheetComponentObjectID')}   # subcircuit instances
        for g in list(R.iter('Group')):
            if g.get('Class')=='CSheetComponentMSM' and g.get('ObjectID') not in used:
                hb_ids.add(g.get('ObjectID')); hb_guids.add(g.get('GUID')); parent[g].remove(g)
        for vs in list(P.findall('ViewState')):
            if any(pe.get('ID') in hb_ids for pe in vs.iter('PathElement')): P.remove(vs)
        for it in list(R.iter('SWsTreeItem')):
            if re.search(r'\(HB\d+\)$',it.get('Name','')): parent[it].remove(it)
        for it in list(R.iter('Item')):
            tp=it.get('TreeInstanceProxy')
            if tp and any(g in tp for g in hb_guids): parent[it].remove(it)
    ext=P.find('Extensions')
    for x in list(ext):
        cl=x.get('Class')
        if cl=='CMsPreviewExtension' and preview: ext.remove(x)
        if cl=='CODProjectExtension' and netext:
            for items in x.iter('Items'):
                for k in list(items): items.remove(k)
            for md in x.iter('MapData'):
                for k in list(md): md.remove(k)
        if cl=='CMultisimExtension' and msext:
            for tag in ('ComponentPins','RefDesInfoContainers','RefDesPrefixUsageMap','RefDesGUIDsForSave'):
                for e in x.iter(tag):
                    for k in list(e): e.remove(k)
    net_names(b)
    instruments(b)
    renew_guids(R,os.path.basename(outpath))
    xml=serialize(R)
    blast.write_ms2(xml,outpath)
    return xml
