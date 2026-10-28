"""Part registry for the generator: harvest.py catalogs (<skill>/samples/ni/catalog.json and folders from MSGEN_REGISTRY,
separated by os.pathsep) plus the skill's own samples (samples/*.ms14; that catalog is built automatically and cached in .msgen).

    find('2N3904') / find('BJT_NPN/2N3904') → catalog entry (donor, RefDes in it, pins, value, status)
    An unknown part raises KeyError with similar names (instead of producing a broken file).
python3 scripts/registry.py [filter]  — list the registry parts."""
import sys, os, json, difflib
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from msgen import SAMPLES, CACHE
import harvest

def dirs():
    d=[os.path.join(SAMPLES,'ni')]+[p for p in os.environ.get('MSGEN_REGISTRY','').split(os.pathsep) if p]
    return [p for p in d if os.path.exists(os.path.join(p,harvest.CATALOG))]

def _own():
    """catalog of the skill's samples — rebuilt when the samples change"""
    files=sorted(os.path.join(SAMPLES,f) for f in os.listdir(SAMPLES) if f.endswith('.ms14'))
    stamp=[[os.path.basename(f),os.path.getmtime(f)] for f in files]
    path=os.path.join(CACHE,'own_samples_registry.json')
    try:
        c=json.load(open(path,encoding='utf-8'))
        if c['stamp']==stamp: return c['parts']
    except (OSError,ValueError,KeyError): pass
    parts,_,_=harvest.harvest(files,verbose=False)
    for e in parts.values(): e['donor']=os.path.basename(e['donor'])
    os.makedirs(CACHE,exist_ok=True)
    json.dump(dict(stamp=stamp,parts=list(parts.values())),open(path,'w',encoding='utf-8'),ensure_ascii=False)
    return list(parts.values())

_ALL=None
def parts():
    """all parts: [(entry, donor folder)]; harvest.py catalogs take precedence over the skill samples (they come first)"""
    global _ALL
    if _ALL is None:
        _ALL=[]
        for d in dirs():
            _ALL+=[(e,d) for e in json.load(open(os.path.join(d,harvest.CATALOG),encoding='utf-8'))['parts']]
        _ALL+=[(e,SAMPLES) for e in _own()]
    return _ALL

def find(name):
    """part by name ('2N3904') or key 'FAMILY/NAME', case-insensitive → entry with field path (the donor file)"""
    q=name.upper(); P=parts()
    hit=[(e,d) for e,d in P if e['key'].upper()==q] or [(e,d) for e,d in P if e['part'].upper()==q]
    keys=list(dict.fromkeys(e['key'] for e,_ in hit))
    if len(keys)>1: raise KeyError('part %s exists in several families: %s — use FAMILY/NAME'%(name,', '.join(keys)))
    if not hit:
        names=sorted({e['part'] for e,_ in P}|{e['key'] for e,_ in P})
        near=difflib.get_close_matches(name,names,n=6,cutoff=0.5)
        raise KeyError('part %s is neither a generator type nor in the registry (%d parts%s)%s'%(name,len({e['key'] for e,_ in P}),
            '' if dirs() else '; no harvester catalog — run scripts/harvest.py on a PC with Multisim',
            '; similar: '+', '.join(near) if near else ''))
    e,d=hit[0]
    if e['status'].startswith('unsupported'): raise KeyError('part %s: %s'%(name,e['status']))
    return dict(e,path=os.path.join(d,e.get('pack') or e['donor']))   # part block (parts.bin#…xml) or a whole file

def need(names):
    """are the parts in the registry: [(name, entry or None, message)]"""
    res=[]
    for n in names:
        try: res.append((n,find(n),''))
        except KeyError as e: res.append((n,None,e.args[0]))
    return res

if __name__=='__main__' and sys.argv[1:2]==['--need']:   # registry.py --need 2N3904 TIP121 LM358 …
    for n,e,msg in need(sys.argv[2:]):
        print(('found   %-14s %s/%s ← %s'%(n,e['group'],e['key'],e['donor'])) if e else ('MISSING %-14s %s'%(n,msg)))
elif __name__=='__main__':
    f=(sys.argv[1] if len(sys.argv)>1 else '').upper()
    for e,d in parts():
        if f in e['key'].upper():
            print('%-26s %-22s %-24s %-7s %s ← %s'%(e['family'],e['part'],' '.join(e['pins']),
                  (e['value'] or '')+(e['unit'] or ''),e['status'],os.path.relpath(os.path.join(d,e.get('pack') or e['donor']))))
