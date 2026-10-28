"""Part registry: a catalog of real Multisim elements taken from files saved by Multisim itself.

The generator clones an element whole (symbol, model, database data) from a donor file — so the element is guaranteed
to be the same as in the Multisim database. Donor sources are the sample circuits installed with Multisim (hundreds of parts)
and any of your own files: a part missing from the samples just needs to be placed once on an empty sheet in Multisim
(Place → Component…) and saved.

Run on a PC with Multisim (only Python 3 is needed, no extra packages; Multisim does not have to be running):
    python harvest.py                      — Multisim samples (the Circuit Design Suite */samples folders are found automatically)
    python harvest.py FOLDER_OR_FILE …     — your own files/folders (together with the samples: add --samples)
    --keep                                — add to the current catalog (folder -o): existing parts stay
    -o FOLDER                             — where to put the result (default: ni_donors next to the current folder)
Result: FOLDER/catalog.json (parts: group, family, name, pins, SPICE template, model, donor), FOLDER/catalog.txt
(the same as a list) and FOLDER/parts.bin + parts.idx — the block of each part cut from its donor (symbol, model, pins,
instrument settings), ≈ 3–4 KB per part instead of a whole file.
The generator reads catalogs from <skill>/samples/ni/ (and from the folders in the MSGEN_REGISTRY variable)."""
import sys, os, json, glob, argparse, re
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import blast
from msgen import Doc, CUSTOM_MARK, pack_part, write_packs, read_pack
from geom import dec

CATALOG='catalog.json'
# where Multisim keeps its samples (Circuit Design Suite 14.x, 32- and 64-bit installations)
SAMPLE_GLOBS=[r'C:\Users\Public\Documents\National Instruments\Circuit Design Suite *\samples',
              r'C:\Program Files (x86)\National Instruments\Circuit Design Suite *\samples',
              r'C:\Program Files\National Instruments\Circuit Design Suite *\samples']
EXT=('.ms14','.ms13','.ms12','.ms11','.ms10')

def strings(at):
    """CiaCollString strings (as a list) or []"""
    return [dec(i.get('Value') or '') for i in at[0].iter('Item')] if len(at) and at[0].get('Class')=='CiaCollString' else []

def value_of(at):
    """value (a Multisim string like '4k') and the unit on the sheet ('Ω', 'F', 'V'): a pair of adjacent CiaCString
    «4k» and «4kΩ» (slots 41, 42 for a resistor and a capacitor); (None, None) — no value"""
    cs=[dec(a[0].get('String') or '') if len(a) and a[0].get('Class')=='CiaCString' else None for a in at]
    for i in range(len(cs)-1):
        a,b=cs[i],cs[i+1]
        if a and b and b.startswith(a) and len(b)>len(a): return a,b[len(a):]
    return None,None

def safe_name(n): return re.sub(r'[^A-Za-z0-9._-]+','_',n)

def natural(s): return [int(t) if t.isdigit() else t for t in re.split(r'(\d+)',s)]

def kind_of(sym,typ,prefix,tmpl):
    """element kind and what the generator knows about it (status)"""
    cls=sym.get('Class')
    if cls=='CIITMacroComponent': return 'subcircuit','unsupported: subcircuit/hierarchical block (its sheet must be transplanted)'
    if prefix.startswith('X') and len(prefix)>1: return 'instrument','ok (instrument: settings from the donor InstrumentsData)'
    if cls=='CIITAnimationSymbolComp': return 'interactive','ok (the animation moves together with the symbol)'
    if prefix.startswith('U'): return 'ic','check: ICs may have sections (U1A…) and hidden supply pins'
    return 'element','ok'

def scan_file(path):
    """parts of the main sheet of a file: a list of dicts"""
    xml=blast.read_ms(path)
    m=re.search(rb'<creator [^>]*versionMajor="(\d+)" versionMinor="(\d+)" versionPatch="(\d+)"',xml[:2000])
    if m: ver='.'.join(x.decode() for x in m.groups())
    else:   # files without <history>: program version in a project attribute
        m=re.search(rb'AppVersion="&amp;ASC([\d.]+)"',xml[:3000]); ver=m.group(1).decode() if m else '?'
    if ver[:2].isdigit() and int(ver.split('.')[0])<14:   # older versions use another format; their blocks do not fit 14.x
        raise ValueError('Multisim %s file — open it in Multisim 14 and save it (File → Save), then scan again'%ver)
    D=Doc(xml)
    saved=b'CMsPreviewExtension' in xml   # only files saved by Multisim itself have a preview (the generator removes it)
    res=[]
    for k in D.objs:
        try: p=scan_part(D,k[0],ver,saved)
        except Exception as e: p=None; print('    ! %s: element skipped (%s: %s)'%(os.path.basename(path),type(e).__name__,e))
        if p: res.append(p)
    return res

def scan_part(D,sym,ver,saved):
    """one part: a catalog dict or None (not a part / synthesized by the generator)"""
    ci=D.byci.get(sym.get('CiComponent')) if sym.get('CiComponent') else None
    if ci is None or ci.get('Class')!='CiComponent' or sym.get('Class')=='CIITHierConnector': return
    c=ci[0]; at=list(c.find('Attributes')); refdes=dec(c.get('LocalName'))
    s4=strings(at[4]) if len(at)>4 else []; s5=strings(at[5]) if len(at)>5 else []
    typ=s5[0] if s5 else ''; prefix=(s5[4] if len(s5)>4 else '').replace('%d','')
    tmpl=dec(next((e.get('String') for e in c.iter('CiaSpiceTmpltExprt')),'') or '')
    if tmpl.startswith(CUSTOM_MARK): return   # an element synthesized by the generator (SpiceLib) is not a donor
    family=s4[0] if s4 else ''; part=s4[1] if len(s4)>1 else ''
    if sym.get('Class')=='CIITMacroComponent':
        hb=sym.find('HierBlock/CHierBlock'); part=dec(hb.get('FileName')) if hb is not None else refdes; family='SUBCIRCUIT'
    if not part: part=s5[3] if len(s5)>3 and s5[3] else (s5[1] if len(s5)>1 else refdes)   # instruments: MULMETER
    if not family: family=s5[2] if len(s5)>2 and s5[2] else (s5[1] if len(s5)>1 else '')
    model=None
    if c.get('Model') and c.get('Model') in D.byci:
        for e in D.byci[c.get('Model')].iter():
            m=re.search(r'^\s*\.(?:model|subckt)\s+(\S+)',dec(e.get('String') or ''),re.M|re.I)
            if m: model=m.group(1); break
    ports=[dec(D.byci[p.get('CiID')][0].get('LocalName')) for p in c.find('Ports')]
    val,unit=value_of(at)
    kind,status=kind_of(sym,typ,prefix,tmpl)
    group=s4[14] if len(s4)>14 else ''   # Multisim database group (Sources, Basic, Analog, …)
    return dict(key='%s/%s'%(family,part),group=group,family=family,part=part,type=typ,prefix=prefix,kind=kind,status=status,
                pins=sorted(ports,key=natural),value=val,unit=unit,template=tmpl.strip(),model=model,refdes=refdes,
                multisim=ver,saved=saved)

def find_files(args,samples):
    roots=list(args)
    if samples or not roots:
        found=[d for g in SAMPLE_GLOBS for d in sorted(glob.glob(g))]
        if not found and not roots:
            sys.exit('Multisim samples not found (looked in: %s). Give a folder: python harvest.py FOLDER'%'; '.join(SAMPLE_GLOBS))
        roots+=found
    files=[]
    for r in roots:
        if os.path.isfile(r): files.append(r)
        else:
            for d,_,fs in os.walk(r):
                files+=[os.path.join(d,f) for f in sorted(fs) if f.lower().endswith(EXT)]
    return roots,files

def harvest(files,verbose=True):
    """→ (parts by family/name key, read errors); the donor is the smallest file with the part"""
    parts={}; errors=[]; per_file={}
    for i,f in enumerate(files):
        try: found=scan_file(f)
        except Exception as e: errors.append((f,'%s: %s'%(type(e).__name__,e))); continue
        per_file[f]=found
        if verbose: print('  [%d/%d] %s — %d elements'%(i+1,len(files),os.path.basename(f),len(found)))
        for p in found:
            e=parts.setdefault(p['key'],dict(p,files=[]))
            e['files'].append((f,p['refdes']))
    # donor set, greedy: the file with the most parts not yet covered; files saved by Multisim itself come first
    # (their parts are «saved»), on a tie — the smaller one
    left=set(parts); chosen=[]
    saved={f:any(p['saved'] for p in ps) for f,ps in per_file.items()}
    while left:
        f=max(per_file,key=lambda f:(any(p['saved'] for p in per_file[f] if p['key'] in left),
                                     len({p['key'] for p in per_file[f]}&left),-os.path.getsize(f)))
        keys={p['key'] for p in per_file[f]}&left
        if not keys: break
        chosen.append(f); left-=keys
    for k,e in list(parts.items()):
        f,ref=next((f,r) for f in chosen for ff,r in e['files'] if ff==f)
        e['donor']=f; e['refdes']=ref; e['count']=len(e['files']); del e['files']; del e['saved']
        if not saved[f]:   # the part exists only in generator-built files — the generator may have synthesized it; not a donor
            errors.append((f,'part %s skipped: the file was built by the generator and not re-saved in Multisim'%k)); del parts[k]
    chosen=[f for f in chosen if saved[f]]
    return parts,errors,chosen

PARTS='parts.bin'   # part blocks — in one file + parts.idx (claude.ai uploader: ≤ 200 files, no nested archives)
def pack_name(key,taken):
    """block name in the pack: ASCII without spaces, unique"""
    base=safe_name(key.replace('/','__')); n=base+'.xml'; i=2
    while n.lower() in taken: n='%s_%d.xml'%(base,i); i+=1
    taken.add(n.lower()); return n

def write(parts,errors,chosen,out,roots,old=None):
    """catalog out/: catalog.json, catalog.txt and parts.bin + parts.idx — the block of every part (instead of whole donor files).
    old — entries of the previous catalog (--keep): their blocks stay as they are, new parts only under new keys.
    Catalogs of older layouts (whole donors; parts/*.xml.gz) are converted automatically"""
    os.makedirs(out,exist_ok=True)
    old=old or []; packs={}; items={}; taken=set()
    by_donor={}
    for e in old:
        p=e.get('pack')
        if p and '#' in p and os.path.exists(os.path.join(out,p.split('#')[0])):   # already in one file (parts.bin / parts.zip)
            n=p.split('#',1)[1]; packs[n]=read_pack(os.path.join(out,p))
        elif p and os.path.exists(os.path.join(out,p)):                     # a separate file parts/*.xml.gz
            n=pack_name(e['key'],taken); packs[n]=read_pack(os.path.join(out,p))
        elif not p and os.path.exists(os.path.join(out,e['donor'])):        # a whole donor: cut the block from it
            by_donor.setdefault(os.path.join(out,e['donor']),[]).append(e); continue
        else: continue
        taken.add(n.lower()); e=dict(e); e['pack']=PARTS+'#'+n; items[e['key']]=e
    migr={e['key'] for es in by_donor.values() for e in es}
    for k,e in parts.items():
        if k not in items and k not in migr: by_donor.setdefault(e['donor'],[]).append(e)
    for f,es in sorted(by_donor.items()):   # every donor is read once
        D=Doc(blast.read_ms(f))
        for e in es:
            e=dict(e); n=pack_name(e['key'],taken); e['pack']=PARTS+'#'+n; e['donor']=os.path.basename(f)
            packs[n]=pack_part(D,e['refdes']); items[e['key']]=e
    write_packs(os.path.join(out,PARTS),packs)
    for n in os.listdir(out):   # older catalog layouts: whole donors, parts.zip and the parts/ folder are no longer needed
        if n.lower().endswith(EXT) or n=='parts.zip': os.remove(os.path.join(out,n))
    if os.path.isdir(os.path.join(out,'parts')):
        for n in os.listdir(os.path.join(out,'parts')): os.remove(os.path.join(out,'parts',n))
        os.rmdir(os.path.join(out,'parts'))
    items=[items[k] for k in sorted(items,key=lambda k:(items[k]['family'],items[k]['part']))]
    base=lambda f: os.path.basename(os.path.normpath(f))   # only names: local paths (user folders) stay private
    json.dump(dict(sources=list(dict.fromkeys(base(r) for r in roots)),parts=items,errors=[dict(file=base(f),error=x) for f,x in errors]),
              open(os.path.join(out,CATALOG),'w',encoding='utf-8'),ensure_ascii=False,indent=1)
    with open(os.path.join(out,'catalog.txt'),'w',encoding='utf-8') as t:
        t.write('%-16s %-28s %-24s %-6s %-26s %-10s %s\n'%('group','family','part','RefDes','pins','donor','status'))
        for e in items:
            t.write('%-16s %-28s %-24s %-6s %-26s %-10s %s\n'%(e.get('group',''),e['family'],e['part'],e['prefix'],' '.join(e['pins']),
                                                           e['donor'],e['status']))
        for f,x in errors: t.write('! %s: %s\n'%(base(f),x))
    return items

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('paths',nargs='*',help='.ms14 files or folders (default — the Multisim samples)')
    ap.add_argument('--samples',action='store_true',help='add the Multisim samples to the given folders')
    ap.add_argument('-o','--out',default='ni_donors',help='result folder')
    ap.add_argument('--keep',action='store_true',help='keep the parts of the current catalog (its donors are a source too)')
    a=ap.parse_args()
    old=None
    if a.keep and os.path.exists(os.path.join(a.out,CATALOG)):
        cat=json.load(open(os.path.join(a.out,CATALOG),encoding='utf-8')); old=cat['parts']
        if not a.paths and not a.samples and all(e.get('pack') for e in old): sys.exit('Nothing to add: give files or folders')
    roots,files=find_files(a.paths,a.samples)
    print('Sources:',*roots,sep='\n  '); print('Files: %d'%len(files))
    parts,errors,chosen=harvest(files)
    if old is not None: roots=list(dict.fromkeys(cat.get('sources',[])+roots))   # --keep: previous sources are kept
    items=write(parts,errors,chosen,a.out,roots,old)
    fam={}
    for e in items: fam[e['family']]=fam.get(e['family'],0)+1
    size=os.path.getsize(os.path.join(a.out,PARTS))
    print('\nParts: %d in %d families; part blocks — %.1f MB → %s'%(len(items),len(fam),size/1e6,os.path.abspath(a.out)))
    for f,n in sorted(fam.items(),key=lambda x:-x[1]): print('  %-30s %d'%(f,n))
    if errors:
        print('\nSkipped (file not read / part not from Multisim): %d — listed in catalog.txt'%len(errors))
