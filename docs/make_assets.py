"""Builds the README graphics: docs/assets/demo.gif (a script is typed, built and checked, the circuit appears)
and docs/assets/social-preview.png (the repository card for Settings → Social preview).

    python3 docs/make_assets.py          (from the repository root; needs Pillow, matplotlib, ngspice)
"""
import os, re, sys, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, '.claude', 'skills', 'multisim-scheme', 'scripts')
OUT = os.path.join(ROOT, 'docs', 'assets')

INTER = '/usr/share/fonts/opentype/inter/Inter-%s.otf'
MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
def font(weight, size): return ImageFont.truetype(INTER % weight, size)
def mono(size): return ImageFont.truetype(MONO, size)

# GitHub dark palette
BG, PANEL, BORDER = '#0d1117', '#161b22', '#30363d'
TEXT, MUTED, KEY, STR, NUM, FUNC, GREEN, BLUE = '#e6edf3', '#8b949e', '#ff7b72', '#a5d6ff', '#79c0ff', '#d2a8ff', '#3fb950', '#58a6ff'

CODE = """from scheme import *

S = Scheme('CMOS_inverter')
inv = S.block('cmos_inv', 20, 14)
vdd, g = S.vcc(29, -2), S.gnd(29, 30)
x = S.switch('S1', 10, 14)
y = S.meter('XMM1', 36, 14)
S.wires([[x, inv['IN']], [inv['OUT'], y],
         [vdd, inv['VDD']], [inv['GND'], g]])
S.build()"""

def build_example(tmp):
    """build the example for real: its report goes into the terminal panel, its preview into the card"""
    src = "import sys; sys.path.insert(0, %r)\n" % SCRIPTS + CODE
    path = os.path.join(tmp, 'my_scheme.py'); open(path, 'w').write(src)
    env = dict(os.environ, MSGEN_OUT=tmp, MSGEN_WORK=os.path.join(tmp, '.msgen'))
    out = subprocess.run([sys.executable, path], capture_output=True, text=True, cwd=tmp, env=env).stdout
    keep = [l.strip() for l in out.splitlines() if re.match(r'(==|\s+ID references|\s+overlaps|\s+S1=|\s+ngspice)', l)]
    keep = ['  ' + ('built CMOS_inverter.ms14 (sheet 14×11 in)' if l.startswith('==') else l + ('  ✓' if l.startswith('ngspice') else '')) for l in keep]
    sys.path.insert(0, SCRIPTS); import render
    png = os.path.join(tmp, 'preview.png')
    render.render(os.path.join(tmp, '.msgen', 'CMOS_inverter_out.xml'), png, zoom=True, clean=True)
    return keep, Image.open(png).convert('RGB')

def trim(img, pad=24):
    """crop white margins"""
    g = img.convert('L').point(lambda v: 255 if v < 250 else 0)
    x0, y0, x1, y1 = g.getbbox()
    return img.crop((max(0, x0 - pad), max(0, y0 - pad), min(img.width, x1 + pad), min(img.height, y1 + pad)))

def fit(img, w, h):
    k = min(w / img.width, h / img.height)
    return img.resize((int(img.width * k), int(img.height * k)), Image.LANCZOS)

def highlight(line):
    """(text, colour) runs of a Python line — just enough for the demo"""
    runs = []
    for m in re.finditer(r"('[^']*')|(\b(?:from|import)\b)|(-?\b\d+\b)|(\b[A-Za-z_]\w*(?=\())|(\s+)|(.)", line):
        s, kw, n, fn, ws, ch = m.groups()
        runs.append((m.group(0), STR if s else KEY if kw else NUM if n else FUNC if fn else TEXT))
    return runs

def rounded(d, box, r, fill, outline=None):
    d.rounded_rectangle(box, r, fill=fill, outline=outline, width=1)

def demo_gif(report, preview):
    W, H = 1200, 660
    CODE_BOX, TERM_BOX, CARD = (20, 64, 610, 392), (20, 404, 610, 640), (630, 64, 1180, 640)
    fc, ft, fs = mono(17), mono(14), font('Medium', 15)
    lines = CODE.split('\n')
    total = len(CODE)
    pic = fit(trim(preview), CARD[2] - CARD[0] - 40, CARD[3] - CARD[1] - 96)

    def frame(chars, nterm, reveal, done):
        im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
        # window bar
        for i, c in enumerate(('#ff5f57', '#febc2e', '#28c840')): d.ellipse((24 + 22 * i, 22, 36 + 22 * i, 34), fill=c)
        d.text((W // 2, 28), 'Claude builds a Multisim circuit', fill=MUTED, font=fs, anchor='mm')
        # code
        rounded(d, CODE_BOX, 10, PANEL, BORDER)
        d.text((CODE_BOX[0] + 16, CODE_BOX[1] + 10), 'my_scheme.py', fill=MUTED, font=font('Medium', 13))
        left, y = chars, CODE_BOX[1] + 40
        for ln in lines:
            if left < 0: break
            shown = ln[:left]; left -= len(ln) + 1
            x = CODE_BOX[0] + 18
            for t, col in highlight(shown):
                d.text((x, y), t, fill=col, font=fc); x += fc.getlength(t)
            if 0 <= left < len(ln) + 1 and chars < total: d.rectangle((x + 1, y + 2, x + 9, y + 20), fill=BLUE)   # caret
            y += 27
        # terminal
        rounded(d, TERM_BOX, 10, '#010409', BORDER)
        d.text((TERM_BOX[0] + 16, TERM_BOX[1] + 12), '$ python3 my_scheme.py', fill=GREEN if nterm else MUTED, font=ft)
        y = TERM_BOX[1] + 40
        for l in report[:nterm]:
            col = GREEN if ('OK' in l or 'none' in l or 'NOT' in l) else TEXT
            d.text((TERM_BOX[0] + 16, y), l, fill=col, font=ft); y += 26
        # preview card
        rounded(d, CARD, 12, '#ffffff', BORDER)
        if reveal > 0:
            px, py = CARD[0] + (CARD[2] - CARD[0] - pic.width) // 2, CARD[1] + 24
            w = int(pic.width * min(1, reveal))
            im.paste(pic.crop((0, 0, w, pic.height)), (px, py))
        else:
            d.text(((CARD[0] + CARD[2]) // 2, (CARD[1] + CARD[3]) // 2), 'CMOS_inverter.ms14', fill='#c9d1d9', font=font('Medium', 22), anchor='mm')
        if done:
            bx = (CARD[0] + 24, CARD[3] - 60, CARD[2] - 24, CARD[3] - 20)
            rounded(d, bx, 20, '#dafbe1', '#2da44e')
            d.text(((bx[0] + bx[2]) // 2, (bx[1] + bx[3]) // 2), '✓  Opens in Multisim 14 and simulates right away',
                   fill='#116329', font=font('SemiBold', 17), anchor='mm')
        return im

    frames, durs = [], []
    def add(im, ms): frames.append(im); durs.append(ms)
    add(frame(0, 0, 0, False), 700)
    step = 9
    for c in range(step, total + step, step): add(frame(min(c, total), 0, 0, False), 45)
    add(frame(total, 0, 0, False), 500)
    for n in range(1, len(report) + 1): add(frame(total, n, 0, False), 380)
    for r in range(1, 11): add(frame(total, len(report), r / 10, False), 60)
    add(frame(total, len(report), 1, True), 4500)
    # one shared palette from the busiest frame keeps the GIF small and flicker-free
    pal = frames[-1].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    q = [f.quantize(palette=pal, dither=Image.Dither.NONE) for f in frames]
    path = os.path.join(OUT, 'demo.gif')
    q[0].save(path, save_all=True, append_images=q[1:], duration=durs, loop=0, optimize=True, disposal=1)
    frames[-1].save(os.path.join(OUT, 'demo-final.png'))
    return path

def social_preview():
    W, H = 1280, 640
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    for y in range(H):   # soft vertical gradient
        k = y / H; d.line((0, y, W, y), fill=(int(13 + 10 * k), int(17 + 14 * k), int(23 + 30 * k)))
    d.text((72, 92), 'Multisim Scheme', fill=TEXT, font=font('Bold', 70))
    d.text((74, 186), 'A Claude skill that turns a schematic picture', fill='#c9d1d9', font=font('Medium', 30))
    d.text((74, 226), 'into a native NI Multisim .ms14 file', fill='#c9d1d9', font=font('Medium', 30))
    y = 310
    for t in ('Real Multisim parts: ~250 built in, more on demand',
              'Instruments, probes, Schottky & multi-emitter transistors',
              'Checked before you open it: layout lint + ngspice',
              '26 circuits verified in Multisim 14.3'):
        d.ellipse((76, y + 9, 88, y + 21), fill=GREEN); d.text((104, y), t, fill=TEXT, font=font('Regular', 23)); y += 46
    d.text((74, 548), 'github.com/vovandel155-tech/multisim-schemes', fill=BLUE, font=font('Medium', 22))
    card = (790, 70, 1220, 570); rounded(d, card, 18, '#ffffff')
    pic = fit(trim(Image.open(os.path.join(ROOT, 'gallery', 'images', 'fig5_04_sn74ls00.png')).convert('RGB')), card[2] - card[0] - 36, card[3] - card[1] - 36)
    im.paste(pic, (card[0] + (card[2] - card[0] - pic.width) // 2, card[1] + (card[3] - card[1] - pic.height) // 2))
    path = os.path.join(OUT, 'social-preview.png'); im.save(path, optimize=True)
    return path

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        report, preview = build_example(tmp)
        print(demo_gif(report, preview))
    print(social_preview())
