"""Circuit description (Tools → Description Box Editor) from simple markup.

In the file the description is a sheet of its own (see put()); its DescData/DescBytes/@BaseSixtyFour holds an RTF
document (RichEdit), base64 in lines of 60 characters separated by CR LF, the RTF ends with a NUL byte.

Markup (as in Markdown): consecutive text lines make one paragraph, a blank line starts a new one;
headings, bullet items and table rows take one line each:
    # Heading               ## Subheading
    a paragraph …           - a bullet item
    | a | table | row |     (a row of dashes |---|---| after the first row makes it bold)
    ![Figure 1 — caption](picture.png){width=12}    a centered PNG/JPEG picture with its caption below;
                                                    width in cm (default: its size at 96 dpi, at most the text width)
inline: **bold**, *italic*, R_{н} subscript, 10^{-3} superscript.
"""
import re, base64

FONT_PT = 14                     # body text, as in Russian coursework (GOST): Times New Roman 14, indent 1.25 cm
INDENT = 709                     # first-line indent, twips (1.25 cm)
TEXT_WIDTH = 9355                # table width, twips (A4 with 3 cm + 1.5 cm margins)

HEADER = (r'{\rtf1\ansi\ansicpg1251\deff0\nouicompat\deflang1049'
          r'{\fonttbl{\f0\froman\fprq2\fcharset204 Times New Roman;}}' '\r\n'
          r'{\colortbl ;\red0\green0\blue0;}' '\r\n'
          r'\viewkind4\uc1 ' '\r\n')


def _text(s):
    """plain text -> RTF: escapes, cp1251 as \\'xx, anything else as \\uN?"""
    out = []
    for ch in s:
        if ch in '\\{}': out.append('\\' + ch)
        elif ord(ch) < 128: out.append(ch)
        else:
            try: out.append("\\'%02x" % ch.encode('cp1251')[0])
            except UnicodeEncodeError: out.append('\\u%d?' % (ord(ch) if ord(ch) < 32768 else ord(ch) - 65536))
    return ''.join(out)


INLINE = re.compile(r'\*\*(.+?)\*\*|\*(.+?)\*|_\{(.+?)\}|\^\{(.+?)\}')


def _inline(s):
    out, pos = [], 0
    for m in INLINE.finditer(s):
        out.append(_text(s[pos:m.start()]))
        b, i, sub, sup = m.groups()
        if b is not None: out.append(r'{\b %s}' % _inline(b))
        elif i is not None: out.append(r'{\i %s}' % _inline(i))
        elif sub is not None: out.append(r'{\sub %s}' % _inline(sub))
        else: out.append(r'{\super %s}' % _inline(sup))
        pos = m.end()
    out.append(_text(s[pos:]))
    return ''.join(out)


def _table(rows):
    """rows of cells; a dash row after the first one makes the first row a bold header"""
    head = len(rows) > 1 and all(re.fullmatch(r':?-{2,}:?', c.strip()) for c in rows[1])
    if head: rows = [rows[0]] + rows[2:]
    n = max(len(r) for r in rows)
    cols = [[r[j].strip() for r in rows if j < len(r)] for j in range(n)]
    char = FONT_PT * 10                                   # an average character, twips
    need = [max((len(w) for c in col for w in c.split()), default=1) * char + 300 for col in cols]   # longest word
    avg = [sum(map(len, col)) / len(col) + 1 for col in cols]
    spare = max(TEXT_WIDTH - sum(need), 0)
    edges, x = [], 0
    for j in range(n):                                    # the longest word fits, the rest follows the average cell
        x += need[j] * min(1, TEXT_WIDTH / sum(need)) + spare * avg[j] / sum(avg); edges.append(round(x))
    border = r'\clbrdrl\brdrw10\brdrs\clbrdrt\brdrw10\brdrs\clbrdrr\brdrw10\brdrs\clbrdrb\brdrw10\brdrs'
    out = []
    for k, r in enumerate(rows):
        r = r + [''] * (n - len(r))
        out.append(r'\trowd\trgaph108\trleft0' + ''.join(r'%s\clvertalc\cellx%d' % (border, edges[j])
                                                        for j in range(n)) + '\r\n')
        bold = head and k == 0
        out.append(''.join(r'\pard\intbl\widctlpar\ql%s %s\cell ' % (r'\b' if bold else r'\b0', _inline(c.strip()))
                           for c in r) + r'\row' + '\r\n')
    out.append(r'\pard\widctlpar\b0' + '\r\n')
    return ''.join(out)


PICTURE = re.compile(r'!\[(.*?)\]\((.+?)\)(?:\{width=([\d.]+)\})?$')


def _image_size(data):
    """(width, height) in pixels of PNG or JPEG data, and the RTF blip type"""
    import struct
    if data[:8] == b'\x89PNG\r\n\x1a\n': return struct.unpack('>II', data[16:24]) + ('pngblip',)
    if data[:2] == b'\xff\xd8':
        i = 2
        while i < len(data):
            marker, size = data[i + 1], struct.unpack('>H', data[i + 2:i + 4])[0]
            if 0xc0 <= marker <= 0xcf and marker not in (0xc4, 0xc8, 0xcc):
                h, w = struct.unpack('>HH', data[i + 5:i + 9]); return w, h, 'jpegblip'
            i += 2 + size
    raise ValueError('only PNG and JPEG pictures')


def _picture(path, caption, width_cm, fs):
    """a centered picture paragraph (single line spacing — otherwise Multisim leaves a gap under it) and its caption"""
    data = open(path, 'rb').read()
    w, h, blip = _image_size(data)
    goal_w = w * 15                                       # twips at 96 dpi
    if width_cm: goal_w = float(width_cm) / 2.54 * 1440
    goal_w = min(goal_w, TEXT_WIDTH)
    goal_h = goal_w * h / w
    hexs = data.hex()
    hexs = '\r\n'.join(hexs[i:i + 128] for i in range(0, len(hexs), 128))
    pict = (r'{\pict{\*\picprop{\sp{\sn wzDescription}{\sv Image}}}\%s\picw%d\pich%d\picwgoal%d\pichgoal%d' '\r\n'
            % (blip, round(w * 2540 / 96), round(h * 2540 / 96), round(goal_w), round(goal_h)) + hexs + '}')
    out = r'\pard\keepn\widctlpar\sb120\sl240\slmult1\qc ' + pict + r'\par' + '\r\n'
    if caption: out += r'\pard\widctlpar\sa120\qc\fs%d %s\par' % (fs, _inline(caption)) + '\r\n'
    return out


def rtf(markup):
    """markup (see the module docstring) -> RTF text"""
    fs = FONT_PT * 2
    body, table, para = [], [], []

    def flush():
        if para: body.append(r'\pard\widctlpar\fi%d\qj\fs%d %s\par' % (INDENT, fs, _inline(' '.join(para))) + '\r\n')
        del para[:]
    for line in markup.strip('\n').splitlines() + ['']:
        s = line.strip()
        if s.startswith('|'):
            flush(); table.append(s.strip('|').split('|')); continue
        if table: body.append(_table(table)); table = []
        m = re.match(r'(#{1,2})\s+(.*)', s)
        pic = PICTURE.match(s)
        if not s: flush()
        elif pic:
            flush(); body.append(_picture(pic.group(2), pic.group(1), pic.group(3), fs))
        elif m:
            flush()
            style = r'\b' if len(m.group(1)) == 1 else r'\b\i'            # # — bold, ## — bold italic
            body.append(r'\pard\keepn\widctlpar\fi%d\sb240\sa120\qj%s\fs%d %s\b0\i0\par' % (INDENT, style, fs, _inline(m.group(2)))
                        + '\r\n')
        elif re.match(r'[-•]\s+', s):
            flush()
            body.append(r'\pard\widctlpar\fi-357\li%d\qj{\pntext\f0\'95\tab}{\*\pn\pnlvlblt\pnf0\pnindent0{\pntxtb\'95}}'
                        r'\fs%d %s\par' % (INDENT + 357, fs, _inline(s[1:].strip())) + '\r\n')
        else:
            para.append(s)
    return HEADER + r'\f0\fs%d ' % fs + ''.join(body) + '}\r\n'


def desc_bytes(text):
    """RTF text -> the BaseSixtyFour attribute value (the RTF ends with NUL, as RichEdit streams it)"""
    raw = text.rstrip('\x00').encode('latin1') + b'\x00'
    b = base64.b64encode(raw).decode('ascii')
    return ''.join(b[i:i + 60] + '\r\n' for i in range(0, len(b), 60))


def put(R, markup):
    """write the description into document root R, replacing an existing one. In Multisim the description is a sheet of
    its own (Design Toolbox: «<title>-Description»): a CDescEditSubSheet in UniqueSheets/SheetInfos holding DescData,
    a CSheetComponent next to the main one, a SheetGroupInfo entry and a project tree item.
    The skeleton is samples/description_sheet.xml (taken from a Multisim-saved file)."""
    import os, copy, xml.etree.ElementTree as ET
    from msgen import Doc, enc, guid
    from geom import dec
    old = [d for d in R.iter('DesignSheet') if d.get('Class') == 'CDescEditSubSheet']
    if old:                                                   # replace the text of an existing description
        _fill(old[0].find('Sheet/SubSheet/DescData'), markup); return
    main = next(g for g in R.iter('Group') if g.get('Class') == 'CSheetComponent')
    name = dec(main.get('SheetName')) + '-Description'
    skel = ET.fromstring(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'samples',
                                           'description_sheet.xml'), 'rb').read())
    cont, comp = copy.deepcopy(skel[0]), copy.deepcopy(skel[1])
    sheet = cont.find('Sheet/Variable/DesignSheet')
    n = max(int(e.get('ObjectID')) for e in R.iter() if (e.get('ObjectID') or '').isdigit()) + 1
    sheet.set('ObjectID', str(n)); comp.find('Group/Store/DataTreeContainer/Rectangle').set('ObjectID', str(n + 1))
    cont.set('ObjectID', str(n + 2)); comp.set('ObjectID', str(n + 4))           # the same numbering as Multisim's
    sheet.set('Title', enc(name)); sheet.set('SheetID', guid())
    comp.set('SheetName', enc(name)); comp.set('GUID', guid())
    _fill(sheet.find('Sheet/SubSheet/DescData'), markup)
    R.find('Project/UniqueSheets/SheetInfos').append(cont)
    par = {c: p for p in R.iter() for c in p}
    par[main].append(comp)
    ET.SubElement(ET.SubElement(R.find('Project/UniqueSheetGroups'), 'SheetGroupInfo',
                                {'FirstSheetComponentObjectID': str(n + 4)}), 'Extensions')
    tree = next(x for x in R.iter('Extension') if x.get('Class') == 'CPrjTreeCtrlExtension').find('SWsTreeItem/Children')
    ET.SubElement(ET.SubElement(tree, 'SWsTreeItem', {'Class': 'SWsTreeItem', 'Name': enc(name)}), 'Children')


def _fill(desc, markup):
    """DescData: the RTF goes first, before TotalLabelInfo"""
    import xml.etree.ElementTree as ET
    for k in desc.findall('DescBytes'): desc.remove(k)
    b = ET.Element('DescBytes', {'BaseSixtyFour': desc_bytes(rtf(markup))})
    desc.insert(0, b)


def read(path):
    """RTF text of the description of a .ms14 file (None if it has none)"""
    import blast, html
    x = blast.read_ms(path).decode('latin1')
    m = re.search(r'<DescBytes BaseSixtyFour="([^"]*)"', x)
    if not m: return None
    return base64.b64decode(re.sub(r'\s', '', html.unescape(m.group(1)))).rstrip(b'\x00').decode('latin1')


def append_rtf(old, markup):
    """RTF `old` with the blocks of `markup` added at its end (character formatting reset first)"""
    body = rtf(markup)[len(HEADER):]
    end = old.rstrip('\x00\r\n').rindex('}')
    return old[:end] + r'\pard\plain' + body[:-len('}\r\n')] + old[end:]


def rewrite(src, dst, markup, append=False):
    """put the description into an existing Multisim file `src` and write `dst`: replace its own description,
    or with append=True add `markup` at the end of it (pictures and formatting of the old text stay)"""
    import blast, msgen, html
    R = msgen.Doc(blast.read_ms(src)).root
    old = next((d for d in R.iter('DescBytes')), None) if append else None
    if old is None: put(R, markup)
    else:
        raw = base64.b64decode(re.sub(r'\s', '', old.get('BaseSixtyFour'))).decode('latin1')
        old.set('BaseSixtyFour', desc_bytes(append_rtf(raw, markup)))
    blast.write_ms2(msgen.serialize(R), dst)
