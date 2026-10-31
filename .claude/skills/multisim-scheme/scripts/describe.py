"""Circuit description (Tools → Description Box Editor) from simple markup.

In the file the description is the DescData element inside the SubSheet of the main sheet: DescBytes/@BaseSixtyFour holds
an RTF document (RichEdit), base64 in lines of 60 characters separated by CR LF, the RTF ends with a NUL byte.

Markup (as in Markdown): consecutive text lines make one paragraph, a blank line starts a new one;
headings, bullet items and table rows take one line each:
    # Heading               ## Subheading
    a paragraph …           - a bullet item
    | a | table | row |     (a row of dashes |---|---| after the first row makes it bold)
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
    w = TEXT_WIDTH // n
    border = r'\clbrdrl\brdrw10\brdrs\clbrdrt\brdrw10\brdrs\clbrdrr\brdrw10\brdrs\clbrdrb\brdrw10\brdrs'
    out = []
    for k, r in enumerate(rows):
        r = r + [''] * (n - len(r))
        out.append(r'\trowd\trgaph108\trleft0' + ''.join(r'%s\clvertalc\cellx%d' % (border, w * (j + 1))
                                                        for j in range(n)) + '\r\n')
        bold = head and k == 0
        out.append(''.join(r'\pard\intbl\widctlpar\ql%s %s\cell ' % (r'\b' if bold else r'\b0', _inline(c.strip()))
                           for c in r) + r'\row' + '\r\n')
    out.append(r'\pard\widctlpar\b0' + '\r\n')
    return ''.join(out)


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
        if not s: flush()
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
    raw = text.encode('ascii') + b'\x00'
    b = base64.b64encode(raw).decode('ascii')
    return ''.join(b[i:i + 60] + '\r\n' for i in range(0, len(b), 60))


def put(R, markup):
    """write the description into the main sheet of document root R (replacing an existing one)"""
    import xml.etree.ElementTree as ET
    sub = next(R.iter('SubSheet'))
    for d in sub.findall('DescData'): sub.remove(d)
    d = ET.SubElement(sub, 'DescData', {'Class': 'CDescriptionData', 'ShowBar': '0', 'FloatBar': '0', 'BarLeft': '450',
                                        'BarTop': '550', 'BarRight': '1000', 'BarBottom': '700', 'HorzScroll': '0',
                                        'VertScroll': '0', 'Version': '2', 'Wrap': '2', 'Unit': '0', 'WordSel': '0'})
    ET.SubElement(d, 'DescBytes', {'BaseSixtyFour': desc_bytes(rtf(markup))})
    ET.SubElement(ET.SubElement(d, 'TotalLabelInfo'), 'LabelArray', {'Class': 'CTotalLabelInfo'})
    q = ET.SubElement(d, 'TotalQuestions', {'Class': 'CTotalQuestions', 'Heading': '', 'Instruction': '', 'ViaEmail': '0',
                                            'MailTo': '', 'MailSubject': '', 'MailBody': '', 'ShowMsg': '0', 'Message': ''})
    f = ET.SubElement(q, 'TesteeFields')
    for n in ('Name', 'Position', 'Organization', 'Date'): ET.SubElement(f, 'Field', {'Name': '&ASC' + n, 'Value': ''})


def read(path):
    """RTF text of the description of a .ms14 file (None if it has none)"""
    import blast, html
    x = blast.read_ms(path).decode('latin1')
    m = re.search(r'<DescBytes BaseSixtyFour="([^"]*)"', x)
    if not m: return None
    return base64.b64decode(re.sub(r'\s', '', html.unescape(m.group(1)))).rstrip(b'\x00').decode('latin1')


def rewrite(src, dst, markup):
    """put the description into an existing Multisim file `src` (replacing its own) and write `dst`"""
    import blast, msgen
    R = msgen.Doc(blast.read_ms(src)).root
    put(R, markup)
    blast.write_ms2(msgen.serialize(R), dst)
