# Python port of zlib contrib/blast.c (PKWARE DCL explode)
import struct, sys
class Huff:
    def __init__(self, rep):
        lengths=[]
        for r in rep:
            l=r&15; n=(r>>4)+1
            lengths += [l]*n
        self.count=[0]*14
        for l in lengths: self.count[l]+=1
        offs=[0]*14
        for i in range(1,13): offs[i+1]=offs[i]+self.count[i]
        self.symbol=[0]*len(lengths)
        for s,l in enumerate(lengths):
            if l: self.symbol[offs[l]]=s; offs[l]+=1
class St:
    def __init__(s,data): s.d=data; s.p=0; s.bitbuf=0; s.bitcnt=0
    def bits(s,need):
        val=s.bitbuf
        while s.bitcnt<need:
            val|=s.d[s.p]<<s.bitcnt; s.p+=1; s.bitcnt+=8
        s.bitbuf=val>>need; s.bitcnt-=need
        return val&((1<<need)-1)
    def decode(s,h):
        code=first=index=0; bitbuf=s.bitbuf; left=s.bitcnt; length=1
        while True:
            while left:
                code|=(bitbuf&1)^1; bitbuf>>=1
                count=h.count[length]
                if code<first+count:
                    s.bitbuf=bitbuf; s.bitcnt=(s.bitcnt-length)&7
                    return h.symbol[index+(code-first)]
                index+=count; first+=count; first<<=1; code<<=1; length+=1; left-=1
            left=(13)-length
            if left==0: raise ValueError('ran out of codes')
            bitbuf=s.d[s.p]; s.p+=1
            if left>8: left=8
LITLEN=[11,124,8,7,28,7,188,13,76,4,10,8,12,10,12,10,8,23,8,9,7,6,7,8,7,6,55,8,23,24,12,11,7,9,11,12,6,7,22,5,7,24,6,11,9,6,7,22,7,11,38,7,9,8,25,11,8,11,9,12,8,12,5,38,5,38,5,11,7,5,6,21,6,10,53,8,7,24,10,27,44,253,253,253,252,252,252,13,12,45,12,45,12,61,12,45,44,173]
LENLEN=[2,35,36,53,38,23]
DISTLEN=[2,20,53,230,247,151,248]
BASE=[3,2,4,5,6,7,8,9,10,12,16,24,40,72,136,264]
EXTRA=[0,0,0,0,0,0,0,0,1,2,3,4,5,6,7,8]
HLIT=Huff(LITLEN); HLEN=Huff(LENLEN); HDIST=Huff(DISTLEN)
def explode(data):
    s=St(data); out=bytearray()
    lit=s.bits(8); dictb=s.bits(8)
    assert lit in (0,1) and 4<=dictb<=6
    while True:
        if s.bits(1):
            sym=s.decode(HLEN); ln=BASE[sym]+s.bits(EXTRA[sym])
            if ln==519: break
            sym=2 if ln==2 else dictb
            dist=s.decode(HDIST)<<sym; dist+=s.bits(sym); dist+=1
            for _ in range(ln): out.append(out[-dist])
        else:
            sym=s.decode(HLIT) if lit else s.bits(8)
            out.append(sym)
    return bytes(out), s.p
def read_ms(path):
    b=open(path,'rb').read()
    magic=b'MSMCompressedElectronicsWorkbenchXML'
    assert b.startswith(magic)
    total,zero=struct.unpack('<II',b[36:44]); p=44; out=bytearray()
    while len(out)<total:
        usz,csz=struct.unpack('<II',b[p:p+8]); p+=8
        chunk,_=explode(b[p:p+csz]); assert len(chunk)==usz,(len(chunk),usz); out+=chunk; p+=csz
    return bytes(out)
if __name__=='__main__':
    x=read_ms(sys.argv[1]); open(sys.argv[2],'wb').write(x); print(len(x))

# ---- literal-only implode encoder (valid PKWARE DCL stream, binary literals) ----
def _codes(h):
    # canonical codes as used by blast decode (MSB-first, inverted bits on the wire)
    codes={}; first=0; index=0
    for ln in range(1,14):
        cnt=h.count[ln]
        for j in range(cnt):
            codes[h.symbol[index+j]]=(first+j,ln)
        index+=cnt; first=(first+cnt)<<1
    return codes
class BW:
    def __init__(s): s.out=bytearray(); s.acc=0; s.n=0
    def put(s,val,n):  # LSB-first
        s.acc|=val<<s.n; s.n+=n
        while s.n>=8: s.out.append(s.acc&255); s.acc>>=8; s.n-=8
    def flush(s):
        if s.n: s.out.append(s.acc&255); s.acc=0; s.n=0
def implode_literal(data):
    w=BW(); w.put(0,8); w.put(6,8)
    for b in data: w.put(b<<1,9)   # flag 0 then 8 bits
    w.put(1,1)
    code,ln=_codes(HLEN)[15]
    for i in range(ln-1,-1,-1): w.put(((code>>i)&1)^1,1)
    w.put(255,8)
    w.flush(); return bytes(w.out)
def write_ms(xml,path,chunk=900000):
    out=bytearray(b'MSMCompressedElectronicsWorkbenchXML')
    out+=struct.pack('<II',len(xml),0)
    for i in range(0,len(xml),chunk):
        part=xml[i:i+chunk]; c=implode_literal(part)
        out+=struct.pack('<II',len(part),len(c))+c
    open(path,'wb').write(out)

# ---- real implode encoder (ASCII literals, 4K dictionary), LZ77 greedy w/ hash chains ----
def implode(data, maxchain=48):
    litc=_codes(HLIT); lenc=_codes(HLEN); distc=_codes(HDIST)
    w=BW(); w.put(1,8); w.put(6,8)
    def huff(code_ln):
        code,ln=code_ln
        for i in range(ln-1,-1,-1): w.put(((code>>i)&1)^1,1)
    lensym=[]
    for L in range(2,519):
        for sym in range(16):
            if BASE[sym]<=L<BASE[sym]+(1<<EXTRA[sym]): lensym.append((sym,L-BASE[sym])); break
    n=len(data); i=0; heads={}
    def insert(p):
        if p+2<n:
            k=data[p:p+3]; lst=heads.get(k)
            if lst is None: heads[k]=[p]
            else:
                lst.append(p)
                if len(lst)>maxchain*2: del lst[:len(lst)-maxchain]
    while i<n:
        best=0; bd=0
        if i+2<n:
            lst=heads.get(data[i:i+3])
            if lst:
                for p in reversed(lst[-maxchain:]):
                    d=i-p
                    if d>4096: break
                    L=3; mx=min(518,n-i)
                    while L<mx and data[p+L]==data[i+L]: L+=1
                    if L>best: best=L; bd=d
                    if L==mx: break
        if best<3 and i+1<n:
            # try length-2 match within 256
            for d in range(1,min(256,i)+1):
                if data[i-d]==data[i] and data[i-d+1]==data[i+1]: best=2; bd=d; break
        if best>=2:
            w.put(1,1); sym,ex=lensym[best-2]; huff(lenc[sym])
            if EXTRA[sym]: w.put(ex,EXTRA[sym])
            sh=2 if best==2 else 6
            dv=bd-1; huff(distc[dv>>sh]); w.put(dv&((1<<sh)-1),sh)
            for p in range(i,i+best): insert(p)
            i+=best
        else:
            w.put(0,1); huff(litc[data[i]]); insert(i); i+=1
    w.put(1,1); huff(lenc[15]); w.put(255,8); w.flush()
    return bytes(w.out)
# ---- fast implode: match search via bytes.rfind (C), Huffman codes pre-expanded for BW.put ----
def _lsb(codes):
    """canonical code (MSB-first, bits inverted) → (value for BW.put in LSB-first order, length)"""
    out={}
    for sym,(code,ln) in codes.items():
        v=0
        for k in range(ln): v|=(((code>>(ln-1-k))&1)^1)<<k
        out[sym]=(v,ln)
    return out
_FAST=None
def implode_fast(data):
    global _FAST
    if _FAST is None:
        lit=_lsb(_codes(HLIT)); ln=_lsb(_codes(HLEN)); dist=_lsb(_codes(HDIST))
        litw=[((v<<1),l+1) for v,l in (lit[b] for b in range(256))]          # flag 0 + literal
        lenw={}
        for L in range(3,519):
            sym=next(k for k in range(16) if BASE[k]<=L<BASE[k]+(1<<EXTRA[k]))
            v,l=ln[sym]; lenw[L]=(1|(v<<1)|((L-BASE[sym])<<(l+1)), 1+l+EXTRA[sym])   # flag 1 + length + extra bits
        distw=[]
        for d in range(4096):
            v,l=dist[d>>6]; distw.append((v|((d&63)<<l), l+6))
        _FAST=(litw,lenw,distw,ln[15])
    litw,lenw,distw,end=_FAST
    w=BW(); w.put(1,8); w.put(6,8)
    n=len(data); i=0; find=data.rfind
    while i<n:
        L=0
        if i+3<=n:
            ws=i-4096 if i>4096 else 0
            p=find(data[i:i+3],ws,i+2)                  # match start — strictly before i
            if p>=0:
                mx=min(518,n-i)
                while True:
                    lo=3 if L==0 else L+1               # the longest match at this p (overlap allowed)
                    hi=mx
                    if data[p:p+lo]!=data[i:i+lo]: break
                    while lo<hi:
                        mid=(lo+hi+1)//2
                        if data[p:p+mid]==data[i:i+mid]: lo=mid
                        else: hi=mid-1
                    L=lo; bp=p
                    if L>=mx: break
                    q=find(data[i:i+L+1],ws,i+L)           # is there a longer one (closer to the window start)?
                    if q<0: break
                    p=q
        if L>=3:
            v,l=lenw[L]; w.put(v,l); v,l=distw[i-bp-1]; w.put(v,l); i+=L
        else:
            v,l=litw[data[i]]; w.put(v,l); i+=1
    w.put(1|(end[0]<<1),1+end[1]); w.put(255,8); w.flush()
    return bytes(w.out)

def write_ms2(xml,path,chunk=900000,fast=True):
    out=bytearray(b'MSMCompressedElectronicsWorkbenchXML')
    out+=struct.pack('<II',len(xml),0)
    for i in range(0,len(xml),chunk):
        part=xml[i:i+chunk]; c=(implode_fast if fast else implode)(part)
        out+=struct.pack('<II',len(part),len(c))+c
    open(path,'wb').write(out)
