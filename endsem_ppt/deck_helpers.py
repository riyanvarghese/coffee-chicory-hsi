import copy
from pptx.util import Inches, Emu, Pt
from PIL import Image
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
RNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
q = lambda t: f"{{{A}}}{t}"
def shp(slide, name, nth=0):
    found = [s for s in slide.shapes if s.name == name]
    assert len(found) > nth, (name, [s.name for s in slide.shapes])
    return found[nth]

def set_text(slide, name, items, cycle=1, nth=0):
    """Rewrite a text box paragraph by paragraph, reusing its own paragraph and run formatting.
    items: list of paragraphs; a paragraph is a string or a list of run strings (run k styled like template run k)."""
    sh = shp(slide, name, nth); tb = sh.text_frame._txBody
    ps = tb.findall(q("p"))
    content = [p for p in ps if any((t.text or "").strip() for t in p.iter(q("t")))]
    spacers = [p for p in ps if p not in content]
    use_spacer = len(content) > 1 and len(spacers) >= len(content) - 1 and ps[1] in spacers
    spacer = spacers[0] if spacers else None
    for p in ps: tb.remove(p)
    for j, item in enumerate(items):
        runs = [item] if isinstance(item, str) else item
        tpl = content[j % cycle] if cycle > 1 else content[min(j, len(content) - 1)]
        p = copy.deepcopy(tpl)
        rts = p.findall(q("r"))
        for r in rts: p.remove(r)
        for br in p.findall(q("br")): p.remove(br)
        end = p.find(q("endParaRPr"))
        for k, txt in enumerate(runs):
            r = copy.deepcopy(rts[min(k, len(rts) - 1)]); r.find(q("t")).text = txt
            (end.addprevious(r) if end is not None else p.append(r))
        if use_spacer and j > 0: tb.append(copy.deepcopy(spacer))
        tb.append(p)

def set_cell(cell, text):
    tf = cell.text_frame; p = tf.paragraphs[0]; runs = p.runs
    if runs:
        runs[0].text = text
        for r in runs[1:]: r._r.getparent().remove(r._r)
    else:
        p.text = text
    for extra in tf.paragraphs[1:]: extra._p.getparent().remove(extra._p)

def fill_table(slide, name, rows, header=None, row_h=None, font_pt=None, col_w=None):
    gf = shp(slide, name); tbl = gf.table; t = tbl._tbl
    while len(t.tr_lst) - 1 < len(rows): t.append(copy.deepcopy(t.tr_lst[-1]))
    while len(t.tr_lst) - 1 > len(rows): t.remove(t.tr_lst[-1])
    if header:
        for j, v in enumerate(header): set_cell(tbl.cell(0, j), v)
    for i, row in enumerate(rows):
        for j, v in enumerate(row): set_cell(tbl.cell(i + 1, j), v)
    if col_w:
        for c, w in zip(tbl.columns, col_w): c.width = Inches(w)
    if font_pt:
        for i in range(len(tbl.rows)):
            for j in range(len(tbl.columns)):
                for p in tbl.cell(i, j).text_frame.paragraphs:
                    for r in p.runs: r.font.size = Pt(font_pt)
                c = tbl.cell(i, j); c.margin_top = c.margin_bottom = Inches(0.02)
    if row_h:
        for r in tbl.rows: r.height = Inches(row_h)
        gf.height = Inches(row_h * len(tbl.rows))

def swap_image(slide, name, path, keep="width"):
    pic = shp(slide, name)
    _, rId = slide.part.get_or_add_image_part(str(path))
    pic._element.find(".//" + q("blip")).set(f"{{{RNS}}}embed", rId)
    src = pic._element.find(".//" + q("srcRect"))
    if src is not None: src.attrib.clear()
    w, h = Image.open(path).size
    if keep == "width": pic.height = int(pic.width * h / w)
    else: pic.width = int(pic.height * w / h)

def drop(slide, *names, prefix=None):
    for sh in list(slide.shapes):
        if sh.name in names or (prefix and sh.name.startswith(prefix)):
            sh._element.getparent().remove(sh._element)

def drop_tracker(slide):
    drop(slide, "Pipeline tracker label", prefix="Tracker step")

def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text

def fmt(v): return f"{v:+.2f}".replace("-", "−")

