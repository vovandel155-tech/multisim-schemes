"""Geometry of the main sheet in absolute coordinates (px, 9 px = one grid cell): symbol segments, borders, labels,
wires, junctions. Used by the preview (render.py), sheet sizing, automatic label placement and the overlap check."""
import re
from msgen import getT, mul, app

CHAR_W, LINE_H = 7, 13          # Multisim label: Arial, 13 px high; average character width ~7 px

def dec(s):
    """Multisim &ASC / &UNI string → text"""
    if s is None: return ''
    if s.startswith('&ASC'): return s[4:]
    if not s.startswith('&UNI'): return s
    return re.sub(r'_uc(\d)((?:[0-9a-f]{4})+)',
                  lambda m: ''.join(chr(int(m.group(2)[i:i+4],16)) for i in range(0,len(m.group(2)),4)), s[4:])

def text_box(x,y,txt):
    """label rectangle (anchor — top left corner)"""
    lines=txt.rstrip().split('\n')   # a source value spans several lines («10Vpk / 1kHz / 0°»)
    return (x, y, x+CHAR_W*max([1]+[len(l.strip()) for l in lines]), y+LINE_H*len(lines))

class Sym:
    """a symbol on the sheet: name, segments, border, pins, labels"""
    def __init__(s,item,byci):
        c=item[0]; s.item=item; s.cls=c.get('Class')
        ci=byci.get(c.get('CiComponent')) if c.get('CiComponent') else None
        s.name=dec(ci[0].get('LocalName')) if ci is not None else None
        s.segs=[]; s.border=None; s.pins={}; s.texts=[]; s.circles=[]
        def walk(e,t,pin):
            tt=getT(e); tl=mul(tt,t) if tt else t
            cl=e.get('Class') or ''
            if e.get('PinName') is not None: pin=dec(e.get('PinName'))
            if cl=='CODLineComp':
                s.segs.append(app(tl,float(e.get('pt0X')),float(e.get('pt0Y')))+app(tl,float(e.get('pt1X')),float(e.get('pt1Y'))))
            elif cl in ('CODMultiLineComp','CODPolygonComp','CODPolyLineComp'):
                pts=[app(tl,float(p.get('X')),float(p.get('Y'))) for p in e.find('Points')]
                s.segs+=[a+b for a,b in zip(pts,pts[1:])]
            elif cl in ('CODRectComp','CIITSymbolBorderRect'):
                x0,y0,x1,y1=[float(e.get(k)) for k in ('pt0X','pt0Y','pt1X','pt1Y')]
                pts=[app(tl,x,y) for x,y in ((x0,y0),(x1,y0),(x1,y1),(x0,y1))]
                bx=(min(p[0] for p in pts),min(p[1] for p in pts),max(p[0] for p in pts),max(p[1] for p in pts))
                if cl=='CODRectComp': s.segs+=[a+b for a,b in zip(pts,pts[1:]+pts[:1])]
                elif s.border is None: s.border=bx
            elif cl=='CODEllipseComp' and e.get('CenterX') is not None:
                s.circles.append(app(tl,float(e.get('CenterX')),float(e.get('CenterY')))+(float(e.get('Radius1') or 0),float(e.get('Radius2') or 0)))
            elif cl=='CIITPinConnectorComp':
                s.pins[pin]=app(tl,float(e.get('ptCenterX')),float(e.get('ptCenterY')))
            elif cl.startswith('CIITSymTextComp') and cl!='CIITSymTextCompLocation' or cl=='CIITVariableSymText':
                o=dec(e.get('Output'))
                if o and e.get('Hidden')!='1':
                    x,y=app(tl,0,0); s.texts.append((cl[15:] if cl.startswith('CIITSymTextComp') else 'Variable',x,y,o))
            for it in e.findall('Objects/Item'): walk(it[0],tl,pin)
        walk(c,[1,0,0,1,0,0],None)
        if s.border is None and s.segs:          # a switch has no border rectangle — use its segments
            xs=[v for g in s.segs for v in (g[0],g[2])]; ys=[v for g in s.segs for v in (g[1],g[3])]
            s.border=(min(xs),min(ys),max(xs),max(ys))
    def label_boxes(s):
        return [text_box(x,y,o) for _,x,y,o in s.texts]

class Scene:
    """the whole main sheet"""
    def __init__(s,objs,el):
        byci={e.get('CiID'):e for e in el}
        s.syms=[]; s.wires=[]; s.junc=[]
        for k in objs:
            cl=k.get('Class')
            if cl=='CIITLinkComp':
                pts=[(float(p.get('X')),float(p.get('Y'))) for p in k[0].find('Points')]
                s.wires.append((k[0].get('Node'),pts))
            elif cl=='CODPinComp':
                s.junc.append((float(k[0].get('CenterX')),float(k[0].get('CenterY')),len(k[0].find('ConnectList'))))
            elif cl in ('CIITSymbolComp','CIITAnimationSymbolComp','CIITMacroComponent'):
                s.syms.append(Sym(k,byci))
    def segments(s):
        """all wire segments: (node, x0,y0,x1,y1)"""
        return [(n,)+a+b for n,pts in s.wires for a,b in zip(pts,pts[1:])]
    def bbox(s):
        xs=[];ys=[]
        for sy in s.syms:
            for g in sy.segs: xs+=[g[0],g[2]]; ys+=[g[1],g[3]]
            for b in sy.label_boxes()+([sy.border] if sy.border else []): xs+=[b[0],b[2]]; ys+=[b[1],b[3]]
        for _,pts in s.wires:
            for x,y in pts: xs.append(x); ys.append(y)
        return min(xs),min(ys),max(xs),max(ys)

# ---------- intersections ----------
def rect_overlap(a,b,pad=0):
    return a[0]<b[2]-pad and b[0]<a[2]-pad and a[1]<b[3]-pad and b[1]<a[3]-pad
def seg_hits_rect(g,r,pad=1):
    """segment (x0,y0,x1,y1) crosses rectangle r (shrunk inwards by pad)"""
    x0,y0,x1,y1=g; r=(r[0]+pad,r[1]+pad,r[2]-pad,r[3]-pad)
    if max(x0,x1)<r[0] or min(x0,x1)>r[2] or max(y0,y1)<r[1] or min(y0,y1)>r[3]: return False
    if x0==x1 or y0==y1: return True            # wires are horizontal/vertical
    for t in [i/20 for i in range(21)]:         # slanted ones (symbol graphics) — by sampling points
        x=x0+(x1-x0)*t; y=y0+(y1-y0)*t
        if r[0]<=x<=r[2] and r[1]<=y<=r[3]: return True
    return False
def on_segment(p,g,inner=True):
    """point p lies on a horizontal/vertical segment g (inner — not at its ends)"""
    x,y=p; x0,y0,x1,y1=g
    if x0==x1==x and min(y0,y1)<=y<=max(y0,y1): return not inner or (y!=y0 and y!=y1)
    if y0==y1==y and min(x0,x1)<=x<=max(x0,x1): return not inner or (x!=x0 and x!=x1)
    return False
def through_body(g,sy):
    """wire g (horizontal/vertical) runs over the body of symbol sy: touches its lines or circle away from its pins"""
    x0,y0,x1,y1=g; pins=list(sy.pins.values())
    near_pin=lambda x,y: any(abs(x-px)<=2 and abs(y-py)<=2 for px,py in pins)
    def on_wire(x,y):
        return min(x0,x1)-1<=x<=max(x0,x1)+1 and min(y0,y1)-1<=y<=max(y0,y1)+1 and \
               (abs(x-x0)<=1 if x0==x1 else abs(y-y0)<=1)
    for a,b,c,d in sy.segs:
        for t in [i/20 for i in range(21)]:
            x=a+(c-a)*t; y=b+(d-b)*t
            if on_wire(x,y) and not near_pin(x,y): return True
    for cx,cy,r1,r2 in sy.circles:
        r=min(r1,r2)
        if r<4 or any((px-cx)**2+(py-cy)**2<=r*r for px,py in pins): continue   # a terminal circle with the pin inside
        if x0==x1: dx,dy=abs(x0-cx),(0 if min(y0,y1)<=cy<=max(y0,y1) else min(abs(y0-cy),abs(y1-cy)))
        else: dx,dy=(0 if min(x0,x1)<=cx<=max(x0,x1) else min(abs(x0-cx),abs(x1-cx))),abs(y0-cy)
        if dx*dx+dy*dy<(r*0.8)**2: return True
    return False
