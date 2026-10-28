"""Check the references between objects of the main sheet (ID / CiID): duplicates and unresolved references.
python3 scripts/validate.py .msgen/<scheme>_out.xml"""
import sys, os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from msgen import *
from collections import Counter
def check(path_or_root):
    """→ dict(dup_ids, dup_ci, bad, n_ids, n_ci); no errors when dup_* and bad are empty"""
    r=path_or_root if not isinstance(path_or_root,str) else ET.fromstring(protect(open(path_or_root,'rb').read()))
    h=r.find('.//CIITHierDoc')
    ids=Counter(); cis=Counter()
    for e in h.iter('Item'):
        if e.get('ID') and len(e): ids[e.get('ID')]+=1
        if e.get('CiID') and len(e): cis[e.get('CiID')]+=1
    bad=Counter()
    for e in h.iter():
        for a in ('Connect1','Connect2','NodeText'):
            if e.get(a) and e.get(a) not in ids: bad[a]+=1
        for a in ('CiComponent','CiProbeExtComp','PortID','Component','Node','Model','SymCompID'):
            v=e.get(a)
            if v and v!='0':
                if a=='SymCompID':
                    if v not in ids: bad[a]+=1
                elif v not in cis: bad[a]+=1
        if e.tag in('ConnectList','Links'):
            for it in e:
                if it.get('ID') not in ids: bad[e.tag]+=1
        if e.tag in('Nodes','Ports','Components','Models','ProbeExts'):
            for it in e:
                if it.get('CiID') and it.get('CiID') not in cis: bad[e.tag]+=1
    return dict(dup_ids=[k for k,v in ids.items() if v>1][:5],dup_ci=[k for k,v in cis.items() if v>1][:5],
                bad=dict(bad),n_ids=len(ids),n_ci=len(cis))
if __name__=='__main__':
    c=check(sys.argv[1])
    print('dup IDs',c['dup_ids'],'dup CiIDs',c['dup_ci'])
    print('unresolved',c['bad'],'n ids',c['n_ids'],'n ci',c['n_ci'])
