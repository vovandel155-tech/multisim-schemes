"""PNG preview of a scheme from the result XML: symbols (blue), wires (red), junctions, labels, sheet border (grey).
python3 scripts/render.py .msgen/<scheme>_out.xml out.png [zoom] [clean]   (zoom — the scheme only, enlarged; clean — no axes)"""
import sys, os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from msgen import *
import geom
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse
def render(xmlpath,out,zoom=False,clean=False):
    """zoom=True — only the scheme itself, enlarged (to check label overlaps), without the whole sheet;
    clean=True — no axes and no sheet border (pictures for documentation)"""
    root=ET.fromstring(protect(open(xmlpath,'rb').read()))
    h=root.find('.//CIITHierDoc')
    objs=h.find('.//Components/CODComposite/Objects')
    sc=geom.Scene(objs,sheet_elements(h))
    fig,ax=plt.subplots(figsize=(16,14)); ax.set_aspect('equal'); ax.invert_yaxis()
    texts=[]
    for sy in sc.syms:
        for x0,y0,x1,y1 in sy.segs: ax.plot([x0,x1],[y0,y1],'b-',lw=0.8)
        for cx,cy,r1,r2 in sy.circles: ax.add_patch(Ellipse((cx,cy),2*r1,2*r2,fill=False,color='b',lw=0.8))
        for _,x,y,o in sy.texts: texts.append(ax.text(x,y,o,va='top'))
    for _,pts in sc.wires: ax.plot([p[0] for p in pts],[p[1] for p in pts],'r-',lw=1)
    for x,y,_ in sc.junc: ax.plot(x,y,'ro',ms=3)
    els={e.get('CiID'):e for e in sheet_elements(h)}
    for k in objs:   # probes: the tip is a green diamond, the name next to it
        if k.get('Class')=='CIITProbeExtComponent':
            c=k[0]; x,y=float(c.get('Transformer-M20')),float(c.get('Transformer-M21'))
            ax.plot(x,y,'gD',ms=5); texts.append(ax.text(x+4,y-4,geom.dec(els[c.get('CiProbeExtComp')][0].get('LocalName')),color='g',va='bottom'))
    # sheet border (Sheet Width/Height from CircPrefs)
    st={e.get('Key'):e[0].get('Value') for e in root.find('.//CircPrefs').iter('Element')}
    w,hh=float(st['&ASCSheet Width'][4:]),float(st['&ASCSheet Height'][4:])
    if not clean: ax.plot([0,w,w,0,0],[0,0,hh,hh,0],'-',color='0.6',lw=1)
    else: ax.axis('off')
    if zoom:
        x0,y0,x1,y1=sc.bbox(); m=30
        ax.set_xlim(x0-m,x1+m); ax.set_ylim(y1+m,y0-m)
    for t in texts: t.set_clip_on(True)
    # text at sheet scale: Multisim font ~8 pt at 96 px/inch ≈ 10.7 px
    ax.apply_aspect(); k=(ax.transData.transform((100,0))[0]-ax.transData.transform((0,0))[0])/100*72/fig.dpi
    for t in texts: t.set_fontsize(10.7*k)
    fig.savefig(out,dpi=90,bbox_inches='tight'); plt.close(fig)
if __name__=='__main__': render(sys.argv[1],sys.argv[2],zoom='zoom' in sys.argv[3:],clean='clean' in sys.argv[3:])
