"""Build Additives_in_Coffee_HSI_v2.pptx from Additives_in_Coffee_HSI.pptx.

Expects, next to this script: un_base/ (the original deck unpacked, with two blank slides already
added by the pptx skill's add_slide.py), fig/ (from deck_result_figures.py) and mask_labelled_base.png
(from mask_figure_labelled.py).  Writes un_out/, which is zipped into the .pptx.
Also holds the shape/notes/table helper functions reused by build_deck_v4_to_v8.py.
"""
import os
import re, shutil, json, sys
from pathlib import Path
from xml.sax.saxutils import escape
import pandas as pd
from PIL import Image

W = Path(__file__).parent
BASE, OUT = W / "un_base", W / "un_out"
RES = Path(os.environ.get("COFFEE_DATA", str(Path(__file__).resolve().parents[2]))) / "final_regression"
shutil.rmtree(OUT, ignore_errors=True)
shutil.copytree(BASE, OUT)
SL = OUT / "ppt" / "slides"
E = 914400

# palette (from the deck)
INK, MUTED, BROWN, GOLD, GOLD_LT, CREAM, CREAM2, LINE = "2B1810", "6B5B4E", "6B4423", "C8964F", "E0B872", "F7F2EC", "FAF6F1", "E6DCD0"
ON_DARK, ON_DARK2 = "F0E4D6", "D9C7B2"


def emu(v): return int(round(v * E))
def rd(n): return (SL / f"slide{n}.xml").read_text()
def wr(n, s): (SL / f"slide{n}.xml").write_text(s)


def sub(s, old, new, count=1):
    n = s.count(old)
    assert n == count, f"expected {count} of {old[:70]!r}, found {n}"
    return s.replace(old, new)


# ------------------------------------------------------------------ shape builders
class Ids:
    def __init__(self, start=2): self.n = start
    def __call__(self):
        self.n += 1
        return self.n


def rpr(sz, b=False, i=False, color=INK, font="Calibri", spc=None):
    sp = f' spc="{spc}"' if spc else ""
    return (f'<a:rPr lang="en-US" sz="{int(round(sz * 100))}" b="{int(b)}" i="{int(i)}" dirty="0"{sp}>'
            f'<a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
            f'<a:latin typeface="{font}"/><a:ea typeface="{font}"/><a:cs typeface="{font}"/></a:rPr>')


def run(text, sz=11, **kw):
    text = text.replace(" %", "\u00a0%")
    return f'<a:r>{rpr(sz, **kw)}<a:t xml:space="preserve">{escape(text)}</a:t></a:r>'


def para(runs, algn="l", lnspc=None, aft=0, bef=0, bullet=None, marL=0, indent=0, endsz=11):
    if isinstance(runs, str): runs = [runs]
    ls = f'<a:lnSpc><a:spcPct val="{int(lnspc * 1000)}"/></a:lnSpc>' if lnspc else ""
    bu = (f'<a:buClr><a:srgbClr val="{bullet}"/></a:buClr><a:buSzPct val="100000"/><a:buFont typeface="Arial"/>'
          f'<a:buChar char="&#8226;"/>') if bullet else "<a:buNone/>"
    return (f'<a:p><a:pPr algn="{algn}" marL="{emu(marL)}" indent="{emu(indent)}">{ls}'
            f'<a:spcBef><a:spcPts val="{int(bef * 100)}"/></a:spcBef><a:spcAft><a:spcPts val="{int(aft * 100)}"/></a:spcAft>'
            f'{bu}</a:pPr>{"".join(runs)}<a:endParaRPr lang="en-US" sz="{int(endsz * 100)}" dirty="0"/></a:p>')


def body(paras, anchor="t", ins=(0, 0, 0, 0), wrap=True):
    l, t, r, b = (emu(v) for v in ins)
    return (f'<p:txBody><a:bodyPr wrap="{"square" if wrap else "none"}" lIns="{l}" tIns="{t}" rIns="{r}" bIns="{b}" '
            f'anchor="{anchor}" rtlCol="0"><a:noAutofit/></a:bodyPr><a:lstStyle/>{"".join(paras) if paras else "<a:p/>"}</p:txBody>')


def xfrm(x, y, w, h, flipH=False, flipV=False):
    f = (' flipH="1"' if flipH else "") + (' flipV="1"' if flipV else "")
    return f'<a:xfrm{f}><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/></a:xfrm>'


def fill_xml(fill, alpha=None):
    if fill is None: return "<a:noFill/>"
    a = f'<a:alpha val="{int(alpha * 1000)}"/>' if alpha is not None else ""
    return f'<a:solidFill><a:srgbClr val="{fill}">{a}</a:srgbClr></a:solidFill>'


def line_xml(line, lw=0.75, dash=None):
    if line is None: return "<a:ln><a:noFill/></a:ln>"
    d = f'<a:prstDash val="{dash}"/>' if dash else ""
    return f'<a:ln w="{int(lw * 12700)}"><a:solidFill><a:srgbClr val="{line}"/></a:solidFill>{d}</a:ln>'


def text(ids, name, x, y, w, h, paras, anchor="t", ins=(0, 0, 0, 0)):
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{ids()}" name="{escape(name)}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr>{xfrm(x, y, w, h)}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
            f'{body(paras, anchor, ins)}</p:sp>')


def shape(ids, name, x, y, w, h, prst="roundRect", fill=CREAM, line=LINE, lw=0.75, dash=None, adj=None,
          paras=None, anchor="t", ins=(0.1, 0.06, 0.1, 0.06), alpha=None, shadow=False):
    av = f'<a:gd name="adj" fmla="val {adj}"/>' if adj is not None else ""
    eff = ('<a:effectLst><a:outerShdw algn="bl" blurRad="88920" dir="5400000" dist="17640" rotWithShape="0">'
           '<a:srgbClr val="B9A894"><a:alpha val="24000"/></a:srgbClr></a:outerShdw></a:effectLst>') if shadow else "<a:effectLst/>"
    return (f'<p:sp><p:nvSpPr><p:cNvPr id="{ids()}" name="{escape(name)}"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr>'
            f'<p:spPr>{xfrm(x, y, w, h)}<a:prstGeom prst="{prst}"><a:avLst>{av}</a:avLst></a:prstGeom>'
            f'{fill_xml(fill, alpha)}{line_xml(line, lw, dash)}{eff}</p:spPr>{body(paras, anchor, ins)}</p:sp>')


def arrow(ids, name, x1, y1, x2, y2, color=MUTED, lw=1.25, head=True):
    x, y, w, h = min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)
    tail = '<a:tailEnd type="triangle" w="med" len="med"/>' if head else ""
    return (f'<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="{ids()}" name="{escape(name)}"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>'
            f'<p:spPr>{xfrm(x, y, w, h, flipH=x2 < x1, flipV=y2 < y1)}<a:prstGeom prst="straightConnector1"><a:avLst/></a:prstGeom>'
            f'<a:ln w="{int(lw * 12700)}"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill>{tail}</a:ln></p:spPr></p:cxnSp>')


def pic(ids, name, rid, x, y, w, h, descr=""):
    return (f'<p:pic><p:nvPicPr><p:cNvPr id="{ids()}" name="{escape(name)}" descr="{escape(descr)}"/>'
            f'<p:cNvPicPr><a:picLocks noChangeAspect="1"/></p:cNvPicPr><p:nvPr/></p:nvPicPr>'
            f'<p:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>'
            f'<p:spPr>{xfrm(x, y, w, h)}<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr></p:pic>')


def badge(ids, name, x, y, num, d=0.34, fill=GOLD, color=INK):
    return shape(ids, name, x, y, d, d, prst="ellipse", fill=fill, line=None, ins=(0, 0, 0, 0), anchor="ctr",
                 paras=[para(run(str(num), 11, b=True, color=color), algn="ctr")])


def title_block(ids, title, subtitle, tag=None):
    out = [text(ids, "Title", 0.62, 0.38, 10.4 if tag else 12.10, 0.62, [para(run(title, 32, b=True, color=INK, font="Cambria"))]),
           text(ids, "Subtitle", 0.62, 1.02, 12.10, 0.40, [para(run(subtitle, 14, color=MUTED))])]
    if tag: out.append(step_tag(ids, tag))
    return out


def step_tag(ids, tag):
    return text(ids, "Pipeline step", 10.20, 0.52, 2.52, 0.26, [para(run(tag, 9.5, b=True, color=GOLD, spc=120), algn="r")], anchor="ctr")


SLD_HEAD = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main"><p:cSld><p:spTree>'
            '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>'
            '<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>')
SLD_TAIL = '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>'


def add_tag(n, tag):
    """Insert a step tag into an existing slide (ids well clear of the deck's own)."""
    s = rd(n)
    s = sub(s, "</p:spTree>", step_tag(Ids(9000), tag) + "</p:spTree>")
    wr(n, s)


# ------------------------------------------------------------------ package helpers
CT = OUT / "[Content_Types].xml"
media_n = [max(int(p.stem[5:]) for p in (OUT / "ppt" / "media").glob("image*.png"))]


def add_media(n, src):
    media_n[0] += 1
    name = f"image{media_n[0]}.png"
    shutil.copy(src, OUT / "ppt" / "media" / name)
    rels = SL / "_rels" / f"slide{n}.xml.rels"
    r = rels.read_text()
    ids = [int(i) for i in re.findall(r'Id="rId(\d+)"', r)]
    rid = f"rId{max(ids) + 1}"
    r = r.replace("</Relationships>", f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                  f'relationships/image" Target="../media/{name}"/></Relationships>')
    rels.write_text(r)
    return rid


def retarget_media(n, rid, src):
    """Point an existing image relationship of slide n at a new file (old file stays for other users or is cleaned)."""
    media_n[0] += 1
    name = f"image{media_n[0]}.png"
    shutil.copy(src, OUT / "ppt" / "media" / name)
    rels = SL / "_rels" / f"slide{n}.xml.rels"
    r = rels.read_text()
    r2 = re.sub(rf'(<Relationship [^>]*Id="{rid}"[^>]*Target=")[^"]*(")', rf'\g<1>../media/{name}\2', r)
    if r2 == r:
        r2 = re.sub(rf'(<Relationship [^>]*Target=")[^"]*("[^>]*Id="{rid}")', rf'\g<1>../media/{name}\2', r)
    assert r2 != r, (n, rid)
    rels.write_text(r2)


def aspect(src):
    im = Image.open(src)
    return im.height / im.width


NOTES_TMPL = (BASE / "ppt" / "notesSlides" / "notesSlide4.xml").read_text()
NOTES_PARA = re.search(r'(<p:ph type="body"/>.*?<a:noAutofit/></a:bodyPr>)(.*?)(</p:txBody>)', NOTES_TMPL, flags=re.S)


def notes_para(t):
    return (f'<a:p><a:pPr indent="0"><a:lnSpc><a:spcPct val="100000"/></a:lnSpc><a:buNone/></a:pPr><a:r><a:rPr lang="en-US" '
            f'sz="2000" b="0" u="none" strike="noStrike"><a:solidFill><a:srgbClr val="000000"/></a:solidFill><a:effectLst/>'
            f'<a:uFillTx/><a:latin typeface="Arial"/></a:rPr><a:t>{escape(t)}</a:t></a:r></a:p>')


def notes_xml(t):
    return NOTES_TMPL.replace(NOTES_PARA.group(0), NOTES_PARA.group(1) + notes_para(t) + NOTES_PARA.group(3))


def set_notes(n, t):
    rels = SL / "_rels" / f"slide{n}.xml.rels"
    r = rels.read_text()
    m = re.search(r'Target="\.\./notesSlides/(notesSlide\d+\.xml)"', r)
    if m:
        (OUT / "ppt" / "notesSlides" / m.group(1)).write_text(notes_xml(t))
        return
    nd = OUT / "ppt" / "notesSlides"
    k = max(int(p.stem[10:]) for p in nd.glob("notesSlide*.xml")) + 1
    (nd / f"notesSlide{k}.xml").write_text(notes_xml(t))
    (nd / "_rels" / f"notesSlide{k}.xml.rels").write_text(
        '<?xml version=\'1.0\' encoding=\'UTF-8\' standalone=\'yes\'?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f'<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="../slides/slide{n}.xml"/>'
        '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/notesMaster" Target="../notesMasters/notesMaster1.xml"/></Relationships>')
    ids = [int(i) for i in re.findall(r'Id="rId(\d+)"', r)]
    rels.write_text(r.replace("</Relationships>", f'<Relationship Id="rId{max(ids) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/'
                                                  f'relationships/notesSlide" Target="../notesSlides/notesSlide{k}.xml"/></Relationships>'))
    c = CT.read_text()
    CT.write_text(c.replace("</Types>", f'<Override PartName="/ppt/notesSlides/notesSlide{k}.xml" ContentType="application/'
                                        f'vnd.openxmlformats-officedocument.presentationml.notesSlide+xml"/></Types>'))


# ------------------------------------------------------------------ table builder
def table(ids, name, x, y, colw, rows, row_h, header_sz=10.5, sz=10, aligns=None, bold_rows=(), highlight_rows=()):
    aligns = aligns or ["l"] + ["ctr"] * (len(colw) - 1)
    def border():
        return "".join(f'<a:{s} w="6480"><a:solidFill><a:srgbClr val="e6dcd0"/></a:solidFill><a:prstDash val="solid"/></a:{s}>'
                       for s in ("lnL", "lnR", "lnT", "lnB"))
    def cell(t, hdr, al, bold, fillc):
        col = "ffffff" if hdr else INK
        f = f'<a:solidFill><a:srgbClr val="{fillc}"/></a:solidFill>' if fillc else "<a:noFill/>"
        return (f'<a:tc><a:txBody><a:bodyPr anchor="ctr"><a:noAutofit/></a:bodyPr><a:lstStyle/><a:p><a:pPr algn="{al}"/>'
                f'{run(t, header_sz if hdr else sz, b=hdr or bold, color=col)}</a:p></a:txBody>'
                f'<a:tcPr anchor="ctr" marL="91440" marR="91440" marT="36000" marB="36000">{border()}{f}</a:tcPr></a:tc>')
    trs = []
    for i, r in enumerate(rows):
        hdr = i == 0
        fillc = "2b1810" if hdr else ("F0E4D6" if i in highlight_rows else ("FAF6F1" if i % 2 == 0 else None))
        trs.append(f'<a:tr h="{emu(row_h)}">' + "".join(cell(t, hdr, "ctr" if hdr else aligns[j], i in bold_rows, fillc)
                                                      for j, t in enumerate(r)) + "</a:tr>")
    grid = "".join(f'<a:gridCol w="{emu(c)}"/>' for c in colw)
    return (f'<p:graphicFrame><p:nvGraphicFramePr><p:cNvPr id="{ids()}" name="{escape(name)}"/><p:cNvGraphicFramePr>'
            f'<a:graphicFrameLocks noGrp="1"/></p:cNvGraphicFramePr><p:nvPr/></p:nvGraphicFramePr>'
            f'<p:xfrm><a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(sum(colw))}" cy="{emu(row_h * len(rows))}"/></p:xfrm>'
            f'<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/table"><a:tbl><a:tblPr firstRow="1" bandRow="1"/>'
            f'<a:tblGrid>{grid}</a:tblGrid>{"".join(trs)}</a:tbl></a:graphicData></a:graphic></p:graphicFrame>')


def replace_shape(s, name, new_xml):
    pat = re.compile(r'<p:(sp|graphicFrame|pic)>(?:(?!</p:\1>).)*?name="' + re.escape(name) + r'".*?</p:\1>', re.S)
    m = list(pat.finditer(s))
    assert len(m) == 1, (name, len(m))
    return s[:m[0].start()] + new_xml + s[m[0].end():]


def move_shape(s, name, x, y, w, h):
    pat = re.compile(r'(<p:(?:sp|pic|graphicFrame)>(?:(?!</p:(?:sp|pic|graphicFrame)>).)*?name="' + re.escape(name) + r'".*?)'
                     r'<a:off x="\d+" y="\d+"/><a:ext cx="\d+" cy="\d+"/>', re.S)
    s2, k = pat.subn(lambda m: m.group(1) + f'<a:off x="{emu(x)}" y="{emu(y)}"/><a:ext cx="{emu(w)}" cy="{emu(h)}"/>', s, count=1)
    assert k == 1, name
    return s2


# ------------------------------------------------------------------ data
outer = pd.read_csv(RES / "outer_folds_all_methods.csv")
summ = pd.read_csv(RES / "method_summary.csv").set_index("model")
S = json.loads((RES / "summary.json").read_text())
pr = pd.read_csv(RES / "heldout_predictions_selected.csv")
blends = pr.groupby(["fold", "label", "y"], as_index=False)["p"].mean().sort_values("y")
FIG = W / "fig"
def mi(v): return f"{v:+.2f}".replace("-", "−")

# ================================================================== 1. slide order
pres = OUT / "ppt" / "presentation.xml"
p = pres.read_text()
order = [256, 257, 277, 274, 259, 278, 276, 260, 261, 262, 263, 264, 279, 265, 266, 268, 267, 269, 270, 271, 272, 273]
ids_in = dict(re.findall(r'<p:sldId id="(\d+)" (r:id="rId\d+")/>', p))
assert sorted(map(int, ids_in)) == sorted(order)
p = re.sub(r"<p:sldIdLst>.*?</p:sldIdLst>",
           "<p:sldIdLst>" + "".join(f'<p:sldId id="{i}" {ids_in[str(i)]}/>' for i in order) + "</p:sldIdLst>", p, flags=re.S)
pres.write_text(p)

# ================================================================== 2. flowchart slide (slide22)
ids = Ids()
sp = title_block(ids, "Methodology", "Thirteen steps from scan to result, with every model judged on a scanning session it never saw")
DATA = [("Data acquisition", "11 blends, 0–50 % chicory, SWIR-imaged in 3 sessions"),
        ("Radiance → reflectance", "Calibrated per column on a Spectralon white strip"),
        ("Dish masking", "Rim, shadow, glare and edge pixels removed"),
        ("Patch extraction", "12 × 12 px patches, one mean spectrum each"),
        ("Spectral preprocessing", "Absorbance and offset removal cancel session brightness")]
LOOP = [("Outlier trimming", "Noisiest patches in each dish discarded"),
        ("Super-patch averaging", "Neighbouring patches pooled into bulk-like units"),
        ("Parameter tuning", "Settings chosen on the training sessions only"),
        ("Model training", "Linear and nonlinear regressors, trained identically"),
        ("Held-out prediction", "Unseen session predicted and scored per dish")]
END = [("Model selection", "Lowest mean held-out error wins: PLSR"),
       ("Final PLSR model", "Retrained on all sessions for new samples"),
       ("Results", "Accuracy on sessions the model never saw")]


def step_box(num, ttl, desc, x, y, w, h, kind):
    fill, line, tc, dc, nc = {"data": (CREAM, LINE, INK, MUTED, GOLD), "model": ("FFFFFF", GOLD, INK, MUTED, GOLD),
                              "result": (INK, INK, GOLD_LT, ON_DARK2, GOLD_LT)}[kind]
    return shape(ids, f"Step {num}", x, y, w, h, fill=fill, line=line, lw=1, adj=8000, anchor="t", ins=(0.12, 0.10, 0.10, 0.08),
                 shadow=kind == "data", paras=[
                     para(run(f"STEP {num}", 8, b=True, color=nc, spc=100), aft=1),
                     para(run(ttl, 11.5, b=True, color=tc, font="Cambria"), aft=2, lnspc=95),
                     para(run(desc, 10, color=dc), lnspc=95)])


sp.append(text(ids, "Row label", 0.62, 1.52, 6, 0.22, [para(run("DATA PREPARATION", 9, b=True, color=GOLD, spc=150))]))
BW, BG, R1Y, BH = 2.14, 0.35, 1.80, 1.15
for i, (t_, d_) in enumerate(DATA):
    x = 0.62 + i * (BW + BG)
    sp.append(step_box(i + 1, t_, d_, x, R1Y, BW, BH, "data"))
    if i: sp.append(arrow(ids, f"Arrow {i}", x - BG + 0.03, R1Y + BH / 2, x - 0.03, R1Y + BH / 2))
# loop frames
OX0, OX1, OY0, OY1 = 0.62, 12.72, 3.30, 5.24
IX0, IX1, IY0, IY1 = 5.514, 12.57, 3.52, 5.10
w2, g2, R2Y = 2.072, 0.30, 3.82
sp.append(shape(ids, "Leave-one-session-out frame", OX0, OY0, OX1 - OX0, OY1 - OY0, fill=None, line=GOLD, lw=1.25, dash="dash", adj=4000))
sp.append(shape(ids, "Per-model frame", IX0, IY0, IX1 - IX0, IY1 - IY0, fill=None, line="B9A894", lw=1.0, dash="sysDot", adj=5000))
sp.append(text(ids, "Loop label", 6.0, OY0 + 0.04, 6.57, 0.22, [para([run("↻  LEAVE-ONE-SESSION-OUT  ", 9, b=True, color=BROWN, spc=100),
                                                                       run("repeated with each session held out in turn", 9, color=MUTED)], algn="r")]))
sp.append(text(ids, "Inner loop label", IX0 + 0.12, IY0 + 0.05, 4, 0.22, [para([run("↻  FOR EACH REGRESSION MODEL", 9, b=True, color=MUTED, spc=100)])]))
xs = [0.77, 0.77 + w2 + g2, 5.634, 5.634 + w2 + g2, 5.634 + 2 * (w2 + g2)]
for i, ((t_, d_), x) in enumerate(zip(LOOP, xs)):
    sp.append(step_box(i + 6, t_, d_, x, R2Y, w2, BH, "model"))
    if i: sp.append(arrow(ids, f"Arrow {i + 5}", xs[i - 1] + w2 + 0.03, R2Y + BH / 2, x - 0.03, R2Y + BH / 2))
# row-1 -> row-2 elbow
xe, xs0, ym = 0.62 + 4 * (BW + BG) + BW / 2, xs[0] + w2 / 2, 3.12
sp += [arrow(ids, "Link a", xe, R1Y + BH, xe, ym, head=False), arrow(ids, "Link b", xe, ym, xs0, ym, head=False),
       arrow(ids, "Link c", xs0, ym, xs0, R2Y - 0.03)]
# row 3
R3Y = 5.66
x3 = [0.77, 0.77 + w2 + g2, 0.77 + 2 * (w2 + g2)]
sp.append(arrow(ids, "Loop exit", xs0, OY1, xs0, R3Y - 0.03))
sp.append(text(ids, "Loop exit label", xs0 + 0.10, OY1 + 0.06, 3.2, 0.3,
               [para(run("after every session has been held out", 9, i=True, color=MUTED))], anchor="ctr"))
for i, ((t_, d_), x) in enumerate(zip(END, x3)):
    sp.append(step_box(i + 11, t_, d_, x, R3Y, w2, BH, "result" if i == 2 else "model"))
    if i: sp.append(arrow(ids, f"Arrow {i + 10}", x3[i - 1] + w2 + 0.03, R3Y + BH / 2, x - 0.03, R3Y + BH / 2))
sp.append(shape(ids, "Why this order", 7.95, R3Y, 4.77, BH, fill=CREAM2, line=LINE, adj=8000, ins=(0.18, 0.12, 0.16, 0.1), anchor="ctr",
                paras=[para(run("Why this order matters", 12, b=True, color=BROWN, font="Cambria"), aft=3),
                       para(run("Trimming, tuning and training never see the held-out session, so the reported error "
                                "is the one a new day of scanning would give.", 10.5, color=INK), lnspc=100)]))
wr(22, SLD_HEAD + "".join(sp) + SLD_TAIL)
set_notes(22, "This is the whole pipeline. The top row turns a raw scan into clean, comparable spectra. Everything inside the dashed "
              "frame is repeated with each session held out in turn, and the dotted frame runs once for every regression method, so no "
              "choice ever sees the session being tested. After all three rounds the best method is picked and retrained on everything.")

# ================================================================== 3. testing slide (slide23)
ids = Ids()
sp = title_block(ids, "How the model is tested",
                 "Leave-one-session-out: every result comes from a scanning session the model never saw", "STEPS 6–10 OF 13")
sp.append(text(ids, "Rounds heading", 0.62, 1.60, 6.0, 0.34, [para(run("Three rounds, one per session", 15, b=True, color=INK, font="Cambria"))], anchor="ctr"))
CX, CW, CG = [1.72, 3.40, 5.08], 1.58, 0.10
heads = [("Session 1", "1 Sep · 0 %"), ("Session 2", "4 Sep · 10–50 %"), ("Session 3", "8 Sep · 5–45 %")]
for (h1, h2), x in zip(heads, CX):
    sp.append(text(ids, f"Header {h1}", x, 2.04, CW, 0.46, [para(run(h1, 11, b=True, color=INK), algn="ctr"),
                                                          para(run(h2, 9.5, color=MUTED), algn="ctr")], anchor="ctr"))
notes_r = ["0 % only: checks bias", "50 % slightly extrapolated", "all within the trained range"]
for r in range(3):
    y = 2.60 + r * 0.72
    sp.append(text(ids, f"Round {r + 1}", 0.62, y, 1.0, 0.62, [para(run(f"Round {r + 1}", 12, b=True, color=BROWN, font="Cambria"))], anchor="ctr"))
    for c, x in enumerate(CX):
        if c == r:
            sp.append(shape(ids, f"R{r + 1} S{c + 1} test", x, y, CW, 0.62, fill=INK, line=INK, adj=10000, anchor="ctr", ins=(0.06, 0.03, 0.06, 0.03),
                            paras=[para(run("HELD OUT · TEST", 9, b=True, color=GOLD_LT, spc=60), algn="ctr"),
                                   para(run(notes_r[r], 8.5, color=ON_DARK2), algn="ctr")]))
        else:
            sp.append(shape(ids, f"R{r + 1} S{c + 1} train", x, y, CW, 0.62, fill=CREAM, line=LINE, adj=10000, anchor="ctr",
                            paras=[para(run("Train", 10.5, b=True, color=INK), algn="ctr")]))
# why whole sessions
sp.append(shape(ids, "Why card", 0.62, 4.86, 6.04, 2.10, fill=CREAM, line=LINE, adj=4000, shadow=True))
sp.append(text(ids, "Why heading", 0.86, 4.98, 5.6, 0.32, [para(run("Why a whole session is held out", 13, b=True, color=INK, font="Cambria"))], anchor="ctr"))
WHY = [("Random patches", "Neighbours from the same dish stay in training: near-perfect, meaningless scores", False),
       ("One dish", "The other stirs of the same powder stay in training: still flattering", False),
       ("Whole session", "No data from that day in training: the error a new day would give", True)]
for k, (a_, b_, hl) in enumerate(WHY):
    y = 5.40 + k * 0.50
    sp.append(text(ids, f"Split {k + 1}", 0.86, y, 1.45, 0.44, [para(run(a_, 10.5, b=True, color=BROWN if hl else INK))], anchor="ctr"))
    sp.append(text(ids, f"Split {k + 1} effect", 2.34, y, 4.15, 0.44, [para(run(b_, 10, b=hl, color=INK if hl else MUTED), lnspc=95)], anchor="ctr"))
# nested tuning card
sp.append(shape(ids, "Nested card", 7.00, 1.62, 5.72, 3.06, fill=INK, line=INK, adj=4000))
sp.append(badge(ids, "Nested badge", 7.28, 1.82, "↻", fill=GOLD))
sp.append(text(ids, "Nested heading", 7.74, 1.82, 4.8, 0.34, [para(run("Nested tuning, inside every round", 15, b=True, color=GOLD_LT, font="Cambria"))], anchor="ctr"))
NEST = ["Each method's settings (latent variables, alpha, C …) are chosen on the two training sessions only.",
        "Inner loop: hold out one concentration level at a time.",
        "Pick the simplest setting within one standard error of the best.",
        "Patch trimming and super-patches are rebuilt from the training sessions too.",
        "The held-out session is touched once, at the end of the round, to score the prediction."]
sp.append(text(ids, "Nested list", 7.32, 2.34, 5.15, 2.25, [para(run(t_, 12, color=ON_DARK), bullet=ON_DARK, marL=0.24, indent=-0.24, aft=8, lnspc=100)
                                                             for t_ in NEST]))
# after the rounds
sp.append(shape(ids, "After card", 7.00, 4.86, 5.72, 2.10, fill=CREAM2, line=LINE, adj=4000, shadow=True))
sp.append(text(ids, "After heading", 7.26, 4.98, 5.2, 0.32, [para(run("After the three rounds", 13, b=True, color=INK, font="Cambria"))], anchor="ctr"))
AFTER = ["Average the three held-out errors, each session counting once",
         "Rank the methods and keep the lowest mean error",
         "Retrain the winner on all three sessions as the final model"]
for k, t_ in enumerate(AFTER):
    y = 5.42 + k * 0.48
    sp.append(badge(ids, f"After {k + 1}", 7.26, y + 0.04, k + 1, d=0.30))
    sp.append(text(ids, f"After {k + 1} text", 7.70, y, 4.8, 0.38, [para(run(t_, 11, color=INK))], anchor="ctr"))
wr(23, SLD_HEAD + "".join(sp) + SLD_TAIL)
set_notes(23, "Three rounds, one per session. Each round trains on two sessions and predicts the third. Inside every round the method "
              "settings are tuned on the training sessions alone, by leaving one concentration out at a time, and the trimming is rebuilt "
              "too. Random or per-dish splits would leak neighbouring patches into training and give flattering numbers.")

# ================================================================== 4. data acquisition slide (slide20)
s20 = rd(20)
tbl = re.search(r"<p:graphicFrame>.*?</p:graphicFrame>", s20, flags=re.S).group(0)
row_h = 4.06 / 11
tbl = re.sub(r'<p:xfrm>.*?</p:xfrm>', f'<p:xfrm><a:off x="{emu(2.52)}" y="{emu(2.28)}"/><a:ext cx="{emu(4.60)}" cy="{emu(4.06)}"/></p:xfrm>', tbl, flags=re.S)
tbl = tbl.replace('<a:tr h="374904">', f'<a:tr h="{emu(row_h)}">')
tbl = sub(tbl, '<a:gridCol w="1554480"/><a:gridCol w="2560320"/>', f'<a:gridCol w="{emu(1.55)}"/><a:gridCol w="{emu(3.05)}"/>')
mask_rid = "rId3"
retarget_media(20, mask_rid, W / "mask_labeled_base.png")
ids = Ids(100)
sp = title_block(ids, "Data acquisition, reflectance and masking",
                 "The first three pipeline steps: image the powder, calibrate it, keep only clean powder pixels", "STEPS 1–3 OF 13")
# 1 acquisition
sp += [badge(ids, "Badge 1", 0.62, 1.80, 1),
       text(ids, "Heading 1", 1.06, 1.80, 5.5, 0.34, [para(run("Data acquisition", 15, b=True, color=INK, font="Cambria"))], anchor="ctr"),
       pic(ids, "Scan", "rId2", 0.62, 2.28, 4.06 * 516 / 1275, 4.06, "One SWIR scan: reference strip at the top, dishes below"),
       tbl,
       text(ids, "Scan caption", 0.62, 6.44, 1.85, 0.26, [para(run("One scan", 12, b=True, color=BROWN, font="Cambria"))]),
       text(ids, "Scan caption text", 0.62, 6.70, 1.85, 0.40, [para(run("Reference strip at the top, plates in a row below", 9.5, color=MUTED), lnspc=95)])]
# 2 reflectance
sp += [shape(ids, "Reflectance card", 7.42, 1.62, 5.30, 1.80, fill=INK, line=INK, adj=5000),
       badge(ids, "Badge 2", 7.66, 1.80, 2),
       text(ids, "Heading 2", 8.10, 1.80, 4.4, 0.34, [para(run("Radiance → reflectance", 15, b=True, color=GOLD_LT, font="Cambria"))], anchor="ctr"),
       text(ids, "Formula", 7.66, 2.27, 4.8, 0.30, [para(run("R  =  L / W(column)  ×  R_certified", 13, b=True, color="FFFFFF", font="Consolas"))], anchor="ctr"),
       text(ids, "Reflectance text", 7.66, 2.66, 4.84, 0.70, [para(run(
           "The white reference is taken per across-track column, so lens vignetting and the lamp profile cancel. The certified "
           "curve falls 0.99 → 0.95 across the range, so treating it as flat would bias the long-wavelength bands.", 10.5, color=ON_DARK2), lnspc=100)])]
# 3 masking
IMX, IMY, IMS = 7.66, 4.22, 2.62
sc = IMS / 1024
sp += [shape(ids, "Masking card", 7.42, 3.58, 5.30, 3.42, fill=CREAM, line=LINE, adj=5000),
       badge(ids, "Badge 3", 7.66, 3.76, 3),
       text(ids, "Heading 3", 8.10, 3.76, 4.4, 0.34, [para(run("Dish masking", 15, b=True, color=INK, font="Cambria"))], anchor="ctr"),
       pic(ids, "Mask", mask_rid, IMX, IMY, IMS, IMS, "Real mask of dish RB[70:30], session 2: kept powder and masked rim, shadow, edge, glare")]


def img_tag(name, px, py, w, words, kept=False):
    cx, cy = IMX + px * sc, IMY + py * sc
    x = min(max(cx - w / 2, IMX + 0.03), IMX + IMS - w - 0.03)
    y = min(max(cy - 0.12, IMY + 0.03), IMY + IMS - 0.27)
    a, b = words
    return shape(ids, name, x, y, w, 0.24, fill="FFFFFF" if kept else INK, line=None, adj=30000, alpha=92 if kept else 88,
                 anchor="ctr", ins=(0.04, 0, 0.04, 0),
                 paras=[para([run(a, 7.5, b=True, color=BROWN if kept else GOLD_LT, spc=60), run("  " + b, 8, b=True, color=INK if kept else "FFFFFF")], algn="ctr")])


sp += [img_tag("Tag kept", 512, 470, 1.22, ("KEPT", "clean powder"), kept=True),
       img_tag("Tag shadow", 512, 40, 1.42, ("MASKED", "shadow crescent")),
       img_tag("Tag rim", 230, 905, 1.08, ("MASKED", "dish rim"))]
LEG = [("F4F1EC", "Kept", "clean powder surface"),
       ("E0B872", "Masked", "4 px trimmed off the outline edge"),
       ("3B8DD9", "Masked", "glare specks, brightest 0.3 %"),
       ("A83B2A", "Masked", "dark specks, below 55 % of the dish median"),
       ("3B2B23", "Masked", "everything outside the drawn outline: rim, shadow, table")]
for k, (c_, a_, b_) in enumerate(LEG):
    y = 4.22 + k * 0.44
    sp.append(shape(ids, f"Swatch {k + 1}", 10.48, y + 0.04, 0.17, 0.17, prst="rect", fill=c_, line="B9A894", lw=0.5, ins=(0, 0, 0, 0)))
    sp.append(text(ids, f"Legend {k + 1}", 10.74, y, 1.86, 0.42,
                   [para([run(a_ + " ", 9, b=True, color=BROWN if k == 0 else INK), run(b_, 9, color=MUTED)], lnspc=92)]))
sp.append(text(ids, "Mask caption", 10.48, 6.46, 2.12, 0.44, [para(run(
    "About 90 % of each outlined dish is kept, then cut into 12 × 12 px patches.", 9, i=True, color=MUTED), lnspc=92)]))
wr(20, SLD_HEAD + "".join(sp) + SLD_TAIL)
set_notes(20, "Three steps on one slide. Acquisition: the HySpex SWIR camera scans the dishes with a certified Spectralon strip in every "
              "scan. Reflectance: each across-track column is divided by its own white reference. Masking, shown on a real dish: the drawn "
              "outline leaves out the rim and the shadow crescent; inside it a 4-pixel edge, glare specks and dark specks are removed, "
              "which keeps about 90 percent of the powder.")

# ================================================================== 5. text edits on existing slides
# --- slide 21: objectives
s = rd(21)
s = sub(s, "<a:t>on independent samples measured in a separate session.</a:t>",
        "<a:t>by holding out each scanning session in turn, so the model is always tested on a day it never saw.</a:t>")
wr(21, s)

# --- slide 5: dataset
s = rd(5)
s = sub(s, "<a:t>7 083</a:t>", f"<a:t>{S['data']['patches']:,}</a:t>".replace(",", " "))
s = sub(s, "<a:t>Sessions 1–2 built the model; session 3 was held out as an independent test set, then folded in.</a:t>",
        "<a:t>Each session is held out in turn to test the model; the final model is trained on all three.</a:t>")
wr(5, s)

# --- step tags on the existing pipeline slides
for n, tag in [(8, "STEP 5 OF 13"), (9, "STEP 5 OF 13"), (10, "STEP 5 OF 13"), (11, "STEP 8 OF 13"),
               (12, "STEPS 9–11 OF 13"), (14, "STEP 12 OF 13"), (13, "STEP 13 OF 13"), (15, "STEP 13 OF 13")]:
    add_tag(n, tag)

# --- slide 11: latent variables
s = rd(11)
s = sub(s, "<a:t>Calibration error always falls; validation error is the honest curve</a:t>",
        "<a:t>Training error levels off; validation error, computed without the test session, is lowest at the chosen setting</a:t>")
a = aspect(FIG / "lv_curve.png")
s = move_shape(s, "Image 0", 0.62, 1.58, 12.10, 12.10 * a)
s = sub(s, "<a:t>Left</a:t>", "<a:t>Training error</a:t>")
s = sub(s, "<a:t>RMSEC falls monotonically — it is scored on the data it fits. RMSECV flattens after six components.</a:t>",
        "<a:t>Scored on the dishes the model was fitted to, so it keeps falling or levels off. It cannot choose the number of components.</a:t>")
s = sub(s, "<a:t>Centre</a:t>", "<a:t>Validation error</a:t>")
s = sub(s, "<a:t>The gap between them is the overfitting margin. It reaches its minimum at six, then widens as extra components describe noise.</a:t>",
        "<a:t>One concentration level held out at a time, on the training sessions only. Its minimum sets the components in each round.</a:t>")
s = sub(s, "<a:t>Right</a:t>", "<a:t>Chosen in every round</a:t>")
s = sub(s, "<a:t>Session transfer, the constraint the usual picture omits. Six components sits on the flat part of both curves.</a:t>",
        "<a:t>The rounds chose 6, 7 and 6 without seeing the test session, and the held-out error follows validation. The final model uses 6.</a:t>")
wr(11, s)
retarget_media(11, re.search(r'r:embed="(rId\d+)"', s).group(1), FIG / "lv_curve.png")
set_notes(11, "Each panel is one round of leave-one-session-out, plus the final model. Training error is always optimistic. The validation "
              "curve, computed without the test session, picks 6 or 7 components, and the held-out session follows it. Session 3 alone "
              "would have preferred 4 components; the procedure had no way to know that, which is why it is an honest test.")

# --- slide 12: regression method
s = rd(12)
s = sub(s, "<a:t>Nine methods, identical data and identical splits — accuracy and session transfer both scored</a:t>",
        "<a:t>Eight methods, identical folds and identical tuning — each scored on sessions it never saw</a:t>")
a = aspect(FIG / "method_comparison.png")
h = min(2.14, 7.60 * a); w = h / a
s = move_shape(s, "Image 0", 0.62 + (7.60 - w) / 2, 1.50, w, h)
order_m = summ.sort_values("mean_rmsep").index.tolist()
rows = [["Method", "Session 1 out", "Session 2 out", "Session 3 out", "Mean error %"]]
for m in order_m:
    v = outer[outer.model == m].set_index("held_out").rmsep_plate
    rows.append([("PLSR (chosen)" if m == "PLSR" else m)] + [f"{v[k]:.2f}" for k in (1, 2, 3)] + [f"{summ.loc[m, 'mean_rmsep']:.2f}"])
s = replace_shape(s, "Table 0", table(Ids(8000), "Table 0", 0.62, 3.76, [2.20, 1.30, 1.30, 1.30, 1.50], rows, 0.268,
                                       bold_rows=(1,), highlight_rows=(1,)))
lo, hi_ = S["runner_up"]["difference_ci95"]
s = sub(s, "<a:t>Plate RMSECV of the four linear methods differs by less than the uncertainty: a paired bootstrap over the 33 plates puts PLSR − PCR at +0.007 pp (95 % CI −0.19 to +0.19). They tie on accuracy.</a:t>",
        f"<a:t>Error per dish on each held-out session. A bootstrap over dishes puts PLSR − SVR (linear) at "
        f"{mi(S['loso']['mean_rmsep'] - S['runner_up']['mean_rmsep'])} pp (95 % CI {mi(lo)} to {mi(hi_)}): the top two tie.</a:t>")
s = sub(s, "<a:t>The nonlinear methods are three times worse. </a:t>", "<a:t>The nonlinear methods are 4–10 times worse. </a:t>")
s = sub(s, "<a:t>With 11 levels and 33 plates they have enough freedom to recognise individual plates rather than learn composition — leave-one-level-out exposes it. This is the substantive result on this slide.</a:t>",
        "<a:t>With 11 levels and 33 dishes they have enough freedom to memorise dishes rather than learn composition, and a held-out session exposes it.</a:t>")
s = sub(s, "<a:t>The four linear methods tie. </a:t>", "<a:t>The five linear methods are close. </a:t>")
s = sub(s, "<a:t>PCR 0.70 against PLSR 0.71 is well inside the bootstrap interval; no method here is measurably more accurate than another.</a:t>",
        f"<a:t>All land between {summ.loc[order_m[0], 'mean_rmsep']:.2f} and {summ.loc[order_m[4], 'mean_rmsep']:.2f} % mean error, and PLSR and linear SVR are statistically tied.</a:t>")
s = sub(s, "<a:t>PLSR is chosen on transfer. </a:t>", "<a:t>PLSR is chosen on the lowest mean error. </a:t>")
s = sub(s, "<a:t>At 8.9 % session bias it is the lowest of the accurate linear methods, and every sample worth predicting comes from a different session than most of the calibration.</a:t>",
        "<a:t>Every method was trimmed, tuned and scored inside the same three rounds, so the ranking reflects the methods, not the bookkeeping.</a:t>")
wr(12, s)
retarget_media(12, re.search(r'r:embed="(rId\d+)"', s).group(1), FIG / "method_comparison.png")
set_notes(12, "All eight methods go through the same nested leave-one-session-out, with the same folds and the same tuning rule. PLSR has the "
              "lowest mean error, but the bootstrap interval spans zero against linear SVR, so say plainly that they tie. The real finding is "
              "that the nonlinear methods fail badly on 11 concentration levels.")

# --- slide 13: performance on unseen sessions
s = rd(13)
lo_ = S["loso"]
s = sub(s, "<a:t>Calibration performance</a:t>", "<a:t>Performance on unseen sessions</a:t>")
s = sub(s, "<a:t>Leave-one-concentration-out: every unit of a level held out, then predicted</a:t>",
        "<a:t>Nested leave-one-session-out: each session predicted by a model that never saw it</a:t>")
a = aspect(FIG / "performance_unseen.png")
s = move_shape(s, "Image 0", 0.62, 1.55, 12.10, 12.10 * a)
s = sub(s, "<a:t>0.71 %</a:t>", f"<a:t>{lo_['mean_rmsep']:.2f} %</a:t>")
s = sub(s, "<a:t>PLATE RMSECV</a:t>", "<a:t>MEAN ERROR</a:t>")
s = sub(s, "<a:t>per-sample error</a:t>", f"<a:t>per dish, ± {lo_['sd_rmsep']:.2f} across sessions</a:t>")
s = sub(s, "<a:t>1.71 %</a:t>", f"<a:t>{lo_['pooled_rmsep']:.2f} %</a:t>")
s = sub(s, "<a:t>UNIT RMSECV</a:t>", "<a:t>POOLED ERROR</a:t>")
s = sub(s, "<a:t>per super-patch</a:t>", "<a:t>all 33 held-out dishes</a:t>")
s = sub(s, "<a:t>0.988</a:t>", f"<a:t>{lo_['pooled_r2']:.3f}</a:t>")
s = sub(s, "<a:t>R² (cross-validated)</a:t>", "<a:t>R² (held out)</a:t>")
s = sub(s, "<a:t>11 levels, 33 plates</a:t>", f"<a:t>RPD {lo_['rpd']:.1f}</a:t>")
mb = max(abs(v["bias"]) for v in lo_["per_held_out_session"].values())
s = sub(s, "<a:t>&lt; 1.3 %</a:t>", f"<a:t>{mb:.2f} %</a:t>")
s = sub(s, "<a:t>at any level</a:t>", "<a:t>worst session</a:t>")
s = sub(s, "<a:t>Left: measured against predicted. Centre: bias at each level, orange marks the third session. Right: residuals show no across-track gradient (−0.4 % over the full swath), so illumination is properly corrected.</a:t>",
        "<a:t>Left: every super-patch and dish mean, coloured by the session that was held out. Centre: error on each held-out session. "
        "Right: systematic offset per session. Session 1 holds only pure robusta, so it checks bias alone.</a:t>")
wr(13, s)
retarget_media(13, re.search(r'r:embed="(rId\d+)"', s).group(1), FIG / "performance_unseen.png")
set_notes(13, "Every number here comes from a session the model never saw: its trimming, its tuning and its training all excluded that "
              "session. Session 3 is the hardest at 1.11 percent. Session 1 contains only pure robusta, so that round checks bias rather "
              "than slope. The mean over the three rounds, 0.79 percent, is the headline.")

# --- slide 15: every blend
s = rd(15)
s = sub(s, "<a:t>External validation</a:t>", "<a:t>Every blend, predicted blind</a:t>")
s = sub(s, "<a:t>Five independent blends, a separate session, no retraining and no correction</a:t>",
        "<a:t>All 11 blends, each predicted by the round that held its session out — no retraining, no correction</a:t>")
a = aspect(FIG / "error_per_blend.png")
w = 6.70; h = w * a
s = move_shape(s, "Image 0", 0.62, 1.55, w, h)
rows = [["Blend", "Session", "True chicory %", "Predicted %", "Error (pp)"]]
for _, r in blends.iterrows():
    rows.append([r.label, str(int(r.fold)), f"{r.y:.0f}", f"{r.p:.2f}", mi(r.p - r.y)])
s = replace_shape(s, "Table 0", table(Ids(8000), "Table 0", 7.62, 1.55, [1.25, 0.85, 1.05, 1.0, 0.95], rows, 0.385,
                                       aligns=["l", "ctr", "ctr", "ctr", "ctr"]))
errs = blends.p - blends.y
s = move_shape(s, "Shape 2", 0.62, 1.55 + h + 0.22, w, 6.98 - (1.55 + h + 0.22))
cy = 1.55 + h + 0.22
s = move_shape(s, "Text 3", 0.86, cy + 0.14, w - 0.5, 0.46)
s = move_shape(s, "Text 4", 0.86, cy + 0.66, w - 0.5, 6.98 - cy - 0.76)
k = int(errs.abs().idxmax())
s = sub(s, "<a:t>RMSEP  1.16 %</a:t>", f"<a:t>Largest miss  {mi(errs[k])} pp</a:t>")
pb = lo_["per_held_out_session"]
s = sub(s, "<a:t>R² = 0.9932     bias = −0.03 %</a:t>", f"<a:t>All 11 blends within ±{errs.abs().max():.1f} pp of the weighed value</a:t>")
s = sub(s, "<a:t>slope 0.934      intercept +1.62</a:t>",
        "<a:t>Bias by session   " + "  ·  ".join(mi(pb[k_]["bias"]) for k_ in ("1", "2", "3")) + " pp</a:t>")
s = sub(s, "<a:t>RPD = 13.6       RER = 34.4</a:t>",
        f"<a:t>Slope   {pb['2']['slope']:.3f} (session 2)  ·  {pb['3']['slope']:.3f} (session 3)</a:t>")
wr(15, s)
retarget_media(15, re.search(r'r:embed="(rId\d+)"', s).group(1), FIG / "error_per_blend.png")
set_notes(15, "Each of these is a blind prediction: the blend's session was left out of trimming, tuning and training. The largest miss is "
              "the 45 percent blend at minus 1.7 points. The errors change sign along the range rather than drifting one way, and the "
              "slopes stay close to one.")

# --- slide 16: permutation test label
s = rd(16)
s = sub(s, "<a:t>Concentrations shuffled across whole plates, model refitted, 300 times. Chance gives ~19 % error; the real model gives 1.71 %. p = 0.0033.</a:t>",
        "<a:t>Earlier leave-one-concentration-out check: concentrations shuffled across whole plates, model refitted 300 times. "
        "Chance gives ~19 % error, the real model 1.71 %. p = 0.0033.</a:t>")
wr(16, s)

# --- slide 17: literature
s = rd(17)
s = sub(s, "<a:t>1.16</a:t>", f"<a:t>{lo_['mean_rmsep']:.2f}</a:t>")
s = sub(s, "<a:t>1.16 % external error, against 3.94 % for the most recent published NIR study — which needed 20 latent variables to get there, where this model uses 6.</a:t>",
        f"<a:t>{lo_['mean_rmsep']:.2f} % error on sessions the model never saw, against 3.94 % for the most recent published NIR study — which needed 20 latent variables, where this model uses 6.</a:t>")
s = sub(s, "<a:t>Harohally reached 1.29 % using roughly 40 separately weighed blends. This model reaches 1.16 % from 11 levels, because imaging yields thousands of spectra per dish.</a:t>",
        f"<a:t>Harohally reached 1.29 % using roughly 40 separately weighed blends. This model reaches {lo_['mean_rmsep']:.2f} % from 11 levels, because imaging yields thousands of spectra per dish.</a:t>")
wr(17, s)
rer = 50 / lo_["pooled_rmsep"]
set_notes(17, f"RPD {lo_['rpd']:.1f} and RER {rer:.1f} are both far above the thresholds of 3.5 and 12 that this literature uses for high "
              "predictive capacity. Our test is also stricter than most: whole scanning sessions are held out, not random samples.")

# --- slide 18: conclusions
s = rd(18)
s = sub(s, "<a:t>SWIR imaging plus PLS regression gives 1.16 % external prediction error over 50–100 % robusta, validated on independent blends from a separate session.</a:t>",
        f"<a:t>SWIR imaging plus PLS regression gives {lo_['mean_rmsep']:.2f} ± {lo_['sd_rmsep']:.2f} % error over 50–100 % robusta, measured on scanning sessions the model never saw (nested leave-one-session-out).</a:t>")
s = sub(s, "<a:t>PLS matches or beats Ridge, SVR, Random Forest and Gradient Boosting, and the nonlinear methods are three times worse — 11 concentration levels do not support them.</a:t>",
        "<a:t>PLS ties with linear SVR and edges the other linear methods; Random Forest, Gradient Boosting and RBF SVR are 4–10 times worse — 11 concentration levels do not support them.</a:t>")
wr(18, s)

# --- slide 19: limitations
s = rd(19)
s = sub(s, "<a:t>No concentration appears in more than one sitting, so a session effect and a concentration effect remain formally indistinguishable.</a:t>",
        f"<a:t>No concentration appears in more than one sitting, so a session effect and a concentration effect remain formally indistinguishable. Three sessions also mean three test rounds, so the mean error carries ± {lo_['sd_rmsep']:.2f} %.</a:t>")
s = sub(s, "<a:t>Each blend was weighed out once; the effective sample size is 33 plates, not 7 000 spectra.</a:t>",
        "<a:t>Each blend was weighed out once; the effective sample size is 33 plates, not ~4 900 spectra. Preprocessing, trimming and super-patch size were fixed from earlier work rather than tuned inside each round.</a:t>")
wr(19, s)

print("built", OUT)
