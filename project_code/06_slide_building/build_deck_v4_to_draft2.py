"""Build v4 to v8 and midsem_coffee_draft2/3 from Additives_in_Coffee_HSI_v3.pptx (each round of slide changes added on top of the last).

Expects, next to this script: un/ (v3 unpacked) and fig/ (preprocessing_figures.py, mask_figure_simple.py,
spectra_bands_figure.py outputs, plus setup_photo.png = the setup photo cropped to pixel rows 300-1280);
prep_folds.csv from ../04_checks.  Writes un_out/, which is zipped into the .pptx.
Shape and notes helpers are loaded from build_deck_v2.py in this folder.
"""
import os
import re, shutil, subprocess, sys
from pathlib import Path
os.environ.setdefault("COFFEE_DATA", str(Path(__file__).resolve().parents[2]))
import pandas as pd
from xml.sax.saxutils import escape
from PIL import Image

W = Path(__file__).parent
SK = Path(os.environ.get("PPTX_SKILL", "/home/riyanvarghese/.claude/skills/synced/589b1784-c188-4996-82fc-5a3c3caf1b58_f24f2714-0d33-4140-a951-c9bcc584ed1f/pptx/scripts"))
BASE, OUT = W / "un", W / "un_out"
shutil.rmtree(OUT, ignore_errors=True)
shutil.copytree(BASE, OUT)
SL = OUT / "ppt" / "slides"
E = 914400

# reuse the shape/notes helpers written for v2
src = (Path(__file__).parent / "build_deck_v2.py").read_text()
helpers = src[src.index("# palette (from the deck)"):src.index("# ------------------------------------------------------------------ data")]
tmpl = sorted((BASE / "ppt" / "notesSlides").glob("notesSlide*.xml"))[0]
helpers = helpers.replace('(BASE / "ppt" / "notesSlides" / "notesSlide4.xml")', f'Path("{tmpl}")')
exec(helpers)
FIG = W / "fig"

def shapes_named(xml, pred):
    out = []
    for m in re.finditer(r'<p:(sp|pic|graphicFrame|cxnSp)>.*?</p:\1>', xml, flags=re.S):
        nm = re.search(r'name="([^"]*)"', m.group(0)).group(1)
        if pred(nm): out.append(m.group(0))
    return out

def keep(n, names):
    x = rd(n)
    return shapes_named(x, lambda nm: nm in names or nm.startswith("Tracker step") or nm == "Pipeline tracker label")

def new_slide_from(src_file):
    r = subprocess.run([sys.executable, str(SK / "add_slide.py"), str(OUT), src_file], capture_output=True, text=True, check=True)
    return int(re.search(r"slide(\d+)\.xml from", r.stdout).group(1))

# ================================================================== structure
NEW = new_slide_from("slide10.xml")                  # "Why the spectra need correcting", tracker copied from step 5
NEW2 = new_slide_from("slide20.xml")                 # "Reflectance and dish masking" (split from the acquisition slide)
pres = OUT / "ppt" / "presentation.xml"
p = pres.read_text()
pairs = re.findall(r'<p:sldId id="(\d+)" (r:id="rId\d+")/>', p)
rel = (OUT / "ppt" / "_rels" / "presentation.xml.rels").read_text()
file_of = {}
for sid, r_ in pairs:
    rid = r_.split('"')[1]
    file_of[sid] = re.search(rf'Id="{rid}"[^>]*Target="slides/(slide\d+)\.xml"|Target="slides/(slide\d+)\.xml"[^>]*Id="{rid}"', rel).group(0)
new_sid, new2_sid = pairs[-2][0], pairs[-1][0]
order = ["256", "257", "277", "274", "260", "259", "278", "276", new2_sid, "280",  # ..., acquisition, NEW reflectance+masking, pixels (261 removed)
         "281", "262", new_sid, "264",                                       # candidates, what each transform does, NEW problem/fix, choosing
         "279", "282", "283", "266", "284", "265",                           # tested, trimming, models, comparison, winner, LV
         "267", "269",                                                       # performance, every blend (268, 270 removed)
         "271", "272", "273"]                                                # literature, conclusions, limitations
ids = dict(pairs)
assert set(order) | {"261", "270", "268"} == set(ids), set(ids) ^ (set(order) | {"261", "270", "268"})
p = re.sub(r"<p:sldIdLst>.*?</p:sldIdLst>", "<p:sldIdLst>" + "".join(f'<p:sldId id="{i}" {ids[i]}/>' for i in order) + "</p:sldIdLst>", p, flags=re.S)
pres.write_text(p)

# ================================================================== new slide: why the spectra need correcting
ids_ = Ids(500)
track = keep(10, set())
sp = [text(ids_, "Title", 0.62, 0.38, 8.3, 0.62, [para(run("Why the spectra need correcting", 32, b=True, color=INK, font="Cambria"))]),
      text(ids_, "Subtitle", 0.62, 1.02, 12.10, 0.40, [para(run(
          "On another scanning day the same powder looks about 15 % brighter; two simple steps cancel that without touching the chicory signal", 14, color=MUTED))])]
sp += track
a = aspect(FIG / "correction_demo.png")
rid = add_media(NEW, FIG / "correction_demo.png")
fh = 12.10 * a
sp.append(pic(ids_, "Correction demo", rid, 0.62, 1.62, 12.10, fh, "A real spectrum and a copy 15 % brighter: apart as recorded, parallel after the log, identical after subtracting the average"))
CARDS = [("1", "The problem", "Packing and sample height change between scanning days, so every wavelength reads about 15 % brighter. "
                              "A model would mistake that for a change in chicory."),
         ("2", "Step 1 · take the log", "The log turns “15 % brighter” into the same small number (0.061) added at every wavelength, "
                                        "so the two curves become exactly parallel."),
         ("3", "Step 2 · subtract the average", "Each spectrum's own average rises by that same number, so subtracting it removes "
                                                "the difference exactly. The shape, where chicory shows, is untouched.")]
cy = 1.62 + fh + 0.22
ch = 1.55
for k, (n_, h_, t_) in enumerate(CARDS):
    x = 0.62 + k * (3.90 + 0.20)
    dark = k == 2
    sp.append(shape(ids_, f"Card {n_}", x, cy, 3.90, ch, fill=INK if dark else CREAM, line=INK if dark else LINE, adj=5000, shadow=not dark))
    sp.append(badge(ids_, f"Card {n_} badge", x + 0.22, cy + 0.18, n_, d=0.30))
    sp.append(text(ids_, f"Card {n_} heading", x + 0.62, cy + 0.16, 3.1, 0.34,
                   [para(run(h_, 14, b=True, color=GOLD_LT if dark else BROWN, font="Cambria"))], anchor="ctr"))
    sp.append(text(ids_, f"Card {n_} text", x + 0.22, cy + 0.62, 3.48, ch - 0.72,
                   [para(run(t_, 11.5, color=ON_DARK2 if dark else INK), lnspc=100)]))
sp.append(text(ids_, "Demo note", 0.62, cy + ch + 0.14, 12.10, 0.36, [para(run(
    "Demonstration: a real spectrum (RB[70:30], session 2) and a copy made 15 % brighter. No blend was scanned in two sessions, "
    "so the same dish cannot be shown on two real days.", 9.5, i=True, color=MUTED))]))
wr(NEW, SLD_HEAD + "".join(sp) + SLD_TAIL)
(SL / "_rels" / f"slide{NEW}.xml.rels").write_text(re.sub(r'<Relationship [^>]*relationships/image"[^>]*Target="\.\./media/(?!image%d)[^"]*"/>' % media_n[0], "",
                                                          (SL / "_rels" / f"slide{NEW}.xml.rels").read_text()))
set_notes(NEW, "Start with the problem: on a different scanning day the same powder reads about 15 percent brighter at every wavelength, "
               "and a model would read that as chicory. Taking the log turns the brightness factor into the same number added everywhere; "
               "subtracting each spectrum's own average removes it exactly. The chicory information is in the shape of the spectrum, so it "
               "survives. The curves are a demonstration built from one real spectrum, because no blend was scanned on two days.")

# ================================================================== choosing the preprocessing (slide10)
T = pd.read_csv(Path(__file__).parent.parent / "04_checks" / "prep_folds.csv")
M = T.groupby("prep").rmsep.mean()
cur, sg, raw, log_ = M["absorbance + offset (current)"], M["absorbance + SG1"], M["raw reflectance"], M["absorbance"]
ids_ = Ids(500)
title = shapes_named(rd(10), lambda nm: nm == "Text 0")
sp = title + [text(ids_, "Subtitle", 0.62, 1.02, 12.10, 0.40, [para(run(
    "Every correction goes through the same test as the final model: train on two scanning sessions, predict the third", 14, color=MUTED))])]
a = aspect(FIG / "preprocessing_proof.png")
rid = add_media(10, FIG / "preprocessing_proof.png")
w = 7.55; h = w * a
if h > 4.75: h = 4.75; w = h / a
sp.append(pic(ids_, "Preprocessing proof", rid, 0.62, 1.55, w, h, "Average error on an unseen session for each of eight preprocessing options"))
sp.append(text(ids_, "Chart note", 0.62, 1.55 + h + 0.12, 7.55, 0.5, [para(run(
    "Each option ran through the same rounds, trimming and tuning as the final model. Bars: average of the three held-out sessions; "
    "markers: each session.", 9.5, i=True, color=MUTED), lnspc=95)]))
sp.append(shape(ids_, "Takeaway card", 8.42, 1.52, 4.30, 1.55 + h + 0.62 - 1.52, fill=INK, line=INK, adj=4000))
sp.append(text(ids_, "Takeaway heading", 8.72, 1.72, 3.8, 0.34, [para(run("What this shows", 17, b=True, color=GOLD_LT, font="Cambria"))], anchor="ctr"))
TK = [("Correcting brightness more than halves the error. ", f"No correction: {raw:.2f} %. Absorbance + offset: {cur:.2f} %."),
      ("The log alone is not enough. ", f"Absorbance without the offset step gives {log_:.2f} %: the brightness gap is still there."),
      ("The closest rival only ties. ", f"Absorbance + SG1 scores {sg:.2f} %, a statistical tie, and it is worse on the two sessions that hold the blends."),
      ("Chosen first, confirmed here. ", "The correction was picked in advance on physical grounds; this test checks it rather than choosing it.")]
sp.append(text(ids_, "Takeaways", 8.72, 2.30, 3.78, 4.40,
               [para([run(a_, 13, b=True, color=GOLD_LT), run(b_, 13, color=ON_DARK)], bullet=ON_DARK, marL=0.24, indent=-0.24, aft=13, lnspc=100)
                for a_, b_ in TK]))
sp += keep(10, set())
x10 = rd(10)
wr(10, SLD_HEAD + "".join(sp) + SLD_TAIL)
r10 = SL / "_rels" / "slide10.xml.rels"
r10.write_text(re.sub(r'<Relationship [^>]*relationships/image"[^>]*Target="\.\./media/(?!image%d\.png)[^"]*"/>' % media_n[0], "", r10.read_text()))
set_notes(10, f"Each candidate correction was put through exactly the same test as the final model. With no correction the error is "
              f"{raw:.2f} percent; with absorbance plus offset it is {cur:.2f}. The log on its own leaves the brightness gap and scores {log_:.2f}. "
              f"Absorbance plus SG1 is a statistical tie at {sg:.2f}, but worse on the sessions that hold the blends. Be clear that the "
              "correction was chosen beforehand for physical reasons, and this chart confirms it rather than picking it.")

# ================================================================== candidates slide (slide25): how the winner is picked
s = rd(25)
crit = shapes_named(s, lambda nm: nm == "Criterion text")[0]
new_crit = re.sub(r"<a:p>.*</a:p>", lambda _m: para(run(
    "Every transform goes through the same test as the final model: train on two sessions, predict the third, compare the average "
    "error. Transfer decides, because every new sample comes from a new session.", 12, color=INK), lnspc=100), crit, flags=re.S)
wr(25, s.replace(crit, new_crit))

# ================================================================== regression candidates (slide27)
s = rd(27)
ids_ = Ids(600)
sp = shapes_named(s, lambda nm: nm in ("Title", "Subtitle")) + keep(27, set())
LX, LW, RX, RW, TOP, BOT = 0.62, 8.20, 9.07, 3.65, 1.62, 7.04
sp.append(shape(ids_, "Methods card", LX, TOP, LW, BOT - TOP, fill=CREAM, line=LINE, adj=3000, shadow=True))
how = dict(re.findall(r'name="Linear name (\d)".*?<a:t>([^<]*)</a:t>', s, flags=re.S))
lin = []
for k in range(1, 6):
    nm_ = re.search(rf'name="Linear name {k}".*?<a:t>([^<]*)</a:t>', s, flags=re.S).group(1)
    hw = re.search(rf'name="Linear how {k}".*?</p:sp>', s, flags=re.S).group(0)
    lin.append((nm_, "".join(re.findall(r"<a:t[^>]*>([^<]*)</a:t>", hw))))
non = []
for k in range(1, 4):
    nm_ = re.search(rf'name="Nonlinear name {k}".*?<a:t>([^<]*)</a:t>', s, flags=re.S).group(1)
    hw = re.search(rf'name="Nonlinear how {k}".*?</p:sp>', s, flags=re.S).group(0)
    non.append((nm_, "".join(re.findall(r"<a:t[^>]*>([^<]*)</a:t>", hw))))
BX, NX, NW, HX, HW_ = 0.92, 1.30, 1.72, 3.10, 5.48
RP, RH = 0.46, 0.41


def section(y, label, title_, note=None):
    out = [text(ids_, f"{label} label", 0.90, y, 4.0, 0.20, [para(run(label, 9, b=True, color=GOLD, spc=110))], anchor="ctr"),
           text(ids_, f"{label} title", 0.90, y + 0.22, 3.2, 0.32, [para(run(title_, 15, b=True, color=INK, font="Cambria"))], anchor="ctr")]
    if note:
        out.append(text(ids_, f"{label} note", 3.40, y + 0.22, 5.2, 0.32, [para(run(note, 10, i=True, color=BROWN))], anchor="ctr"))
    return out


def rows(y0, items, tag, start=1, rp=RP, rh=RH, nsz=12.5):
    out = []
    for k, (n_, h_) in enumerate(items):
        y = y0 + k * rp
        out.append(shape(ids_, f"{tag} row {k + 1}", 0.80, y, 7.84, rh, fill="FFFFFF", line=LINE, adj=8000, ins=(0, 0, 0, 0)))
        out.append(shape(ids_, f"{tag} number {k + 1}", BX, y + (rh - 0.26) / 2, 0.26, 0.26, prst="ellipse", fill=GOLD, line=None,
                         ins=(0, 0, 0, 0), anchor="ctr", paras=[para(run(str(start + k), 10, b=True, color=INK), algn="ctr")]))
        out.append(text(ids_, f"{tag} name {k + 1}", NX, y, NW, rh, [para(run(n_, nsz, b=True, color=INK, font="Cambria"))], anchor="ctr"))
        out.append(text(ids_, f"{tag} how {k + 1}", HX, y, HW_, rh, [para(run(h_, 10.5, color=INK), lnspc=95)], anchor="ctr"))
    return out


sp += section(1.76, "LINEAR · 5 METHODS", "One weight per band, summed")
sp += [text(ids_, "Col METHOD", BX, 2.38, NW, 0.18, [para(run("METHOD", 8.5, b=True, color=MUTED, spc=100))], anchor="ctr"),
       text(ids_, "Col HOW IT WORKS", HX, 2.38, HW_, 0.18, [para(run("HOW IT WORKS", 8.5, b=True, color=MUTED, spc=100))], anchor="ctr")]
sp += rows(2.62, lin, "Linear")
sp += section(4.99, "NONLINEAR · 3 METHODS", "Free to bend the fit", "included to test whether the relation needs a curved fit")
sp += rows(5.61, non, "Nonlinear", start=6)
# rules card on the right
rules = []
for k in range(1, 5):
    rr = re.search(rf'name="Rule {k}".*?</p:sp>', s, flags=re.S).group(0)
    rules.append("".join(re.findall(r"<a:t[^>]*>([^<]*)</a:t>", rr)))
sp.append(shape(ids_, "Rules card", RX, TOP, RW, BOT - TOP, fill=CREAM, line=LINE, adj=4000, shadow=True))
sp.append(text(ids_, "Rules heading", RX + 0.26, TOP + 0.20, RW - 0.5, 0.62, [para(run("Same rules for every method", 15, b=True, color=INK, font="Cambria"), lnspc=95)]))
for k, r_ in enumerate(rules):
    y = TOP + 0.88 + k * 1.05
    sp.append(shape(ids_, f"Rule tick {k + 1}", RX + 0.28, y + 0.04, 0.26, 0.26, prst="ellipse", fill=GOLD, line=None, ins=(0, 0, 0, 0), anchor="ctr",
                    paras=[para(run("✓", 9.5, b=True, color=INK), algn="ctr")]))
    sp.append(text(ids_, f"Rule {k + 1}", RX + 0.68, y, RW - 0.95, 0.80, [para(run(r_, 11.5, color=INK), lnspc=100)]))
sp.append(text(ids_, "Rules footnote", RX + 0.28, BOT - 0.82, RW - 0.55, 0.62, [para(run(
    "So any difference in error comes from the method, not from how it was tested.", 10.5, i=True, color=BROWN), lnspc=100)]))
wr(27, SLD_HEAD + "".join(sp) + SLD_TAIL)

# ================================================================== LV slide (slide11) now sits after "PLSR is the winner": step 12
s11 = rd(11)
old = shapes_named(s11, lambda nm: nm.startswith("Tracker step") or nm == "Pipeline tracker label")
new = shapes_named(rd(14), lambda nm: nm.startswith("Tracker step") or nm == "Pipeline tracker label")
assert len(old) == len(new) == 14
lab = [x for x in new if 'name="Pipeline tracker label"' in x][0]
lab2 = re.sub(r"<a:t>[^<]*</a:t>", "<a:t>STEP 12 OF 13 · FINAL PLSR MODEL</a:t>", lab, count=1)
cnt = iter(range(9100, 9200))
new_txt = re.sub(r'<p:cNvPr id="\d+"', lambda _m: f'<p:cNvPr id="{next(cnt)}"', "".join(new).replace(lab, lab2))
for o in old: s11 = s11.replace(o, "")
s11 = s11.replace("</p:spTree>", new_txt + "</p:spTree>")
wr(11, s11)

# ================================================================== backup slide (slide8)

# ================================================================== v8: "why hyperspectral imaging?" (was the spectral basis, slide6)
retarget_media(6, "rId1", FIG / "spectra_bands.png")
s6 = rd(6)
fa = aspect(FIG / "spectra_bands.png")
FW = 8.85; FH = FW * fa
s6 = move_shape(s6, "Image 0", 0.62, 1.50, FW, FH)
img6 = shapes_named(s6, lambda nm: nm == "Image 0")[0]
ids_ = Ids(700)
sp = [text(ids_, "Title", 0.62, 0.38, 12.10, 0.62, [para(run("Why hyperspectral imaging?", 32, b=True, color=INK, font="Cambria"))]),
      text(ids_, "Subtitle", 0.62, 1.02, 12.10, 0.40, [para(run(
          "The powders look alike to the eye, but their chemistry shows in the infrared, and imaging captures it across the whole dish", 14, color=MUTED))]),
      img6]
CHEM = [("1730 nm · C–H", "Coffee oil absorbs strongly; chicory has almost none"),
        ("2310 nm · C–H", "Coffee oil again"),
        ("2100 nm · C–O", "Chicory's sugars (inulin) absorb here"),
        ("1450 and 1940 nm · O–H", "Water: tracks moisture, not the blend")]
CX = 0.62 + FW + 0.20
sp.append(shape(ids_, "Chemistry card", CX, 1.50, 12.72 - CX, FH, fill=INK, line=INK, adj=4000))
sp.append(text(ids_, "Chemistry heading", CX + 0.24, 1.68, 12.72 - CX - 0.4, 0.36, [para(run("What absorbs where", 15, b=True, color=GOLD_LT, font="Cambria"))], anchor="ctr"))
paras = []
for h_, t_ in CHEM:
    paras.append(para(run(h_, 13, b=True, color=GOLD_LT), aft=2, lnspc=100))
    paras.append(para(run(t_, 12, color=ON_DARK), aft=20, lnspc=100))
sp.append(text(ids_, "Chemistry list", CX + 0.24, 2.22, 12.72 - CX - 0.42, FH - 0.85, paras))
WHY = [("The eye sees two brown powders", "Roasted chicory and robusta look almost the same, so colour alone cannot give the blend ratio."),
       ("The infrared sees the chemistry", "Each ingredient absorbs at its own wavelengths, so the blend ratio changes the shape of the spectrum."),
       ("An image, not a single spot", "Every pixel has a spectrum, so rim and glare can be masked and thousands of points averaged.")]
CY = 1.50 + FH + 0.16
CH = 7.00 - CY
for k, (h_, t_) in enumerate(WHY):
    x = 0.62 + k * (3.90 + 0.20)
    sp.append(shape(ids_, f"Why card {k + 1}", x, CY, 3.90, CH, fill=CREAM, line=LINE, adj=6000, shadow=True))
    sp.append(badge(ids_, f"Why badge {k + 1}", x + 0.18, CY + 0.14, k + 1, d=0.28))
    sp.append(text(ids_, f"Why heading {k + 1}", x + 0.56, CY + 0.12, 3.2, 0.32, [para(run(h_, 13, b=True, color=BROWN, font="Cambria"))], anchor="ctr"))
    sp.append(text(ids_, f"Why text {k + 1}", x + 0.20, CY + 0.52, 3.52, CH - 0.58, [para(run(t_, 12, color=INK), lnspc=100)]))
wr(6, SLD_HEAD + "".join(sp) + SLD_TAIL)
set_notes(6, "Why hyperspectral imaging. Roasted chicory and robusta are both dark brown, so colour cannot give the ratio. In the infrared each "
             "ingredient absorbs at its own wavelengths: coffee oil at 1730 and 2310 nm, chicory's sugars near 2100 nm, and water at 1450 and "
             "1940 nm, which follows moisture rather than the blend. Imaging gives a spectrum at every pixel, so the rim and glare can be "
             "removed and thousands of points averaged.")

# ================================================================== v7: limitations and future scope (slide19)
s19 = rd(19)
for a_, b_ in [("<a:t>Limitations and next steps</a:t>", "<a:t>Limitations and future scope</a:t>"),
               ("<a:t>Stated plainly — each has a known, inexpensive fix</a:t>", "<a:t>Stated plainly, with the work that would remove each limit and widen the method</a:t>"),
               ("<a:t>Next steps</a:t>", "<a:t>Future scope</a:t>"),
               ("<a:t>Press samples into tablets</a:t>", "<a:t>Extend to other coffee blends</a:t>"),
               ("<a:t>Removes packing and surface-relief variation at source rather than correcting for it numerically.</a:t>",
                "<a:t>Calibrate arabica + chicory and arabica + robusta + chicory mixtures, so blends beyond robusta can be quantified too.</a:t>")]:
    s19 = sub(s19, a_, b_)
wr(19, s19)

# ================================================================== v6: simpler dish masking (slide20)
s20 = rd(20)
for nm in ["Tag kept", "Tag shadow", "Tag rim", "Mask caption"] + [f"Swatch {k}" for k in range(1, 6)] + [f"Legend {k}" for k in range(1, 6)]:
    s20 = replace_shape(s20, nm, "")
IMX, IMY, IMS = 7.66, 4.22, 2.62
sc = IMS / 1024
mpt = (IMX + 509.6 * sc, IMY + 513.6 * sc)
rpt = (IMX + 850 * sc, IMY + 779 * sc)
ids_ = Ids(800)
add20 = [
    shape(ids_, "Mask swatch", 10.60, 4.47, 0.20, 0.20, prst="rect", fill="E0B872", line="C8964F", lw=1.25, ins=(0, 0, 0, 0)),
    text(ids_, "Mask label", 10.90, 4.36, 1.75, 1.05, [para(run("Mask", 14, b=True, color=BROWN, font="Cambria"), aft=2),
                                                        para(run("powder pixels the model uses, about 90 % of the dish", 10.5, color=INK), lnspc=100)]),
    arrow(ids_, "Mask arrow", 10.52, 4.57, mpt[0] + 0.05, mpt[1] - 0.02, color=INK, lw=1.75),
    text(ids_, "Dish label", 10.90, 5.62, 1.75, 1.05, [para(run("Petri dish", 14, b=True, color=INK, font="Cambria"), aft=2),
                                                        para(run("left out: rim, wall and shadow", 10.5, color=INK), lnspc=100)]),
    arrow(ids_, "Dish arrow", 10.82, 5.84, rpt[0] + 0.03, rpt[1], color=INK, lw=1.75),
    text(ids_, "Mask note", 10.60, 6.50, 2.05, 0.42, [para(run("The mask is then cut into 12 × 12 px patches.", 9.5, i=True, color=MUTED), lnspc=95)]),
]
s20 = s20.replace("</p:spTree>", "".join(add20) + "</p:spTree>")
wr(20, s20)
retarget_media(20, "rId3", FIG / "mask_simple.png")

# ================================================================== v6: preprocessing candidates in the regression-candidates layout (slide25)
s = rd(25)
names = {k: re.search(rf'name="Technique {k} name".*?<a:t[^>]*>([^<]*)</a:t>', s, flags=re.S).group(1) for k in range(1, 9)}
descs = {k: "".join(re.findall(r"<a:t[^>]*>([^<]*)</a:t>", re.search(rf'name="Technique {k} desc".*?</p:sp>', s, flags=re.S).group(0))) for k in range(1, 9)}
ids_ = Ids(900)
sp = shapes_named(s, lambda nm: nm == "Title") + [text(ids_, "Subtitle", 0.62, 1.02, 12.10, 0.40, [para(run(
    "Eight transforms aimed at one problem: the three sessions differ by a uniform brightness factor of about 1.15", 14, color=MUTED))])]
sp += keep(25, set())
sp.append(shape(ids_, "Transforms card", LX, TOP, LW, BOT - TOP, fill=CREAM, line=LINE, adj=3000, shadow=True))
sp += [text(ids_, "Col TRANSFORM", BX, 1.80, NW, 0.18, [para(run("TRANSFORM", 8.5, b=True, color=MUTED, spc=100))], anchor="ctr"),
       text(ids_, "Col WHAT IT DOES", HX, 1.80, HW_, 0.18, [para(run("WHAT IT DOES", 8.5, b=True, color=MUTED, spc=100))], anchor="ctr")]
GROUPS = [("BASELINE", [1]), ("LOG TRANSFORM", [2, 3]), ("SCATTER CORRECTION", [4, 5]), ("DERIVATIVES", [6, 7, 8])]
y = 2.04
for lab_, ks in GROUPS:
    sp.append(text(ids_, f"{lab_} header", 0.90, y, 7.6, 0.24, [para(run(lab_, 9, b=True, color=GOLD, spc=110))], anchor="ctr"))
    y += 0.26
    sp += rows(y, [(names[k], descs[k]) for k in ks], f"Transform {lab_.title()}", start=ks[0], rp=0.45, rh=0.40, nsz=12)
    y += 0.45 * len(ks) + 0.08
assert y - 0.08 - 0.05 <= BOT - 0.10, y
TEST = ["Applied to every spectrum before any model is fitted", "Same patches, trimmed and pooled the same way",
        "Same model, PLSR, with the same tuning rule", "Scored on a scanning session the model never saw"]
sp.append(shape(ids_, "Test card", RX, TOP, RW, BOT - TOP, fill=CREAM, line=LINE, adj=4000, shadow=True))
sp.append(text(ids_, "Test heading", RX + 0.26, TOP + 0.20, RW - 0.5, 0.62, [para(run("Same test for every transform", 15, b=True, color=INK, font="Cambria"), lnspc=95)]))
for k, r_ in enumerate(TEST):
    yy = TOP + 0.88 + k * 1.05
    sp.append(shape(ids_, f"Test tick {k + 1}", RX + 0.28, yy + 0.04, 0.26, 0.26, prst="ellipse", fill=GOLD, line=None, ins=(0, 0, 0, 0), anchor="ctr",
                    paras=[para(run("✓", 9.5, b=True, color=INK), algn="ctr")]))
    sp.append(text(ids_, f"Test {k + 1}", RX + 0.68, yy, RW - 0.95, 0.80, [para(run(r_, 11.5, color=INK), lnspc=100)]))
sp.append(text(ids_, "Test footnote", RX + 0.28, BOT - 0.82, RW - 0.55, 0.62, [para(run(
    "So any difference in error comes from the transform alone.", 10.5, i=True, color=BROWN), lnspc=100)]))
wr(25, SLD_HEAD + "".join(sp) + SLD_TAIL)


# ================================================================== v9 helpers
def line2(ids, name, x1, y1, x2, y2, color=MUTED, lw=1.25, head="med", dash=None):
    x, y, w, h = min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1)
    tail = f'<a:tailEnd type="triangle" w="{head}" len="{head}"/>' if head else ""
    d = f'<a:prstDash val="{dash}"/>' if dash else ""
    return (f'<p:cxnSp><p:nvCxnSpPr><p:cNvPr id="{ids()}" name="{escape(name)}"/><p:cNvCxnSpPr/><p:nvPr/></p:nvCxnSpPr>'
            f'<p:spPr>{xfrm(x, y, w, h, flipH=x2 < x1, flipV=y2 < y1)}<a:prstGeom prst="straightConnector1"><a:avLst/></a:prstGeom>'
            f'<a:ln w="{int(lw * 12700)}" cap="flat"><a:solidFill><a:srgbClr val="{color}"/></a:solidFill>{d}<a:round/>{tail}</a:ln></p:spPr></p:cxnSp>')


def path(ids, name, pts, **kw):
    """Poly-line made of straight connectors; only the last segment carries the arrowhead."""
    out = []
    for i in range(len(pts) - 1):
        last = i == len(pts) - 2
        out.append(line2(ids, f"{name} {i + 1}", *pts[i], *pts[i + 1], **{**kw, "head": kw.get("head", "med") if last else None}))
    return out


def set_tracker(xml, current, label):
    lo = min(current)
    def restyle(m):
        sp_ = m.group(0); k = int(m.group(1))
        state = "cur" if k in current else ("done" if k < lo else "fut")
        fill, ln, col, b = {"cur": ("C8964F", "C8964F", "2B1810", "1"), "done": ("EADFCD", "EADFCD", "6B5B4E", "0"),
                            "fut": ("FFFFFF", "D9CBB8", "A99A8A", "0")}[state]
        sp_ = re.sub(r'(<p:spPr>.*?<a:solidFill><a:srgbClr val=")\w+(")', rf'\g<1>{fill}\2', sp_, count=1, flags=re.S)
        sp_ = re.sub(r'(<a:ln w="\d+"><a:solidFill><a:srgbClr val=")\w+(")', rf'\g<1>{ln}\2', sp_, count=1)
        sp_ = re.sub(r'(<a:rPr [^>]*?) b="\d"', rf'\1 b="{b}"', sp_, count=1)
        sp_ = re.sub(r'(<a:rPr [^>]*>\s*<a:solidFill><a:srgbClr val=")\w+(")', rf'\g<1>{col}\2', sp_, count=1)
        return sp_
    xml = re.sub(r'<p:sp>(?:(?!</p:sp>).)*?name="Tracker step (\d+)".*?</p:sp>', restyle, xml, flags=re.S)
    xml = re.sub(r'(name="Pipeline tracker label".*?<a:t>)[^<]*(</a:t>)', rf'\g<1>{label}\2', xml, count=1, flags=re.S)
    return xml


def prune_image_rels(n):
    rels = SL / "_rels" / f"slide{n}.xml.rels"; r = rels.read_text(); x = rd(n)
    used = set(re.findall(r'r:embed="(rId\d+)"', x))
    r = re.sub(r'<Relationship Id="(rId\d+)" Type="[^"]*/image"[^>]*/>', lambda m: m.group(0) if m.group(1) in used else "", r)
    rels.write_text(r)


# ================================================================== v9: methodology slide with a flow you can follow (slide22)
ids_ = Ids(100)
sp = [text(ids_, "Title", 0.62, 0.38, 12.10, 0.62, [para(run("Methodology", 32, b=True, color=INK, font="Cambria"))]),
      text(ids_, "Subtitle", 0.62, 1.02, 12.10, 0.40, [para(run(
          "Thirteen steps from scan to result, with every model judged on a scanning session it never saw", 14, color=MUTED))]),
      text(ids_, "Row label", 0.62, 1.52, 6, 0.22, [para(run("DATA PREPARATION", 9, b=True, color=GOLD, spc=150))])]
DATA9 = [("Data acquisition", "11 blends, 0–50 % chicory, SWIR-imaged in 3 sessions"),
         ("Radiance → reflectance", "Calibrated per column on a Spectralon white strip"),
         ("Dish masking", "Rim, shadow, glare and edge pixels removed"),
         ("Patch extraction", "12 × 12 px patches, one mean spectrum each"),
         ("Spectral preprocessing", "Absorbance and offset removal cancel session brightness")]
LOOP9 = [("Outlier trimming", "Noisiest patches in each dish discarded"),
         ("Super-patch averaging", "Neighbouring patches pooled into bulk-like units"),
         ("Parameter tuning", "Settings chosen on the training sessions only"),
         ("Model training", "Linear and nonlinear regressors, trained identically"),
         ("Held-out prediction", "Unseen session predicted and scored per dish")]
END9 = [("Model selection", "Lowest mean held-out error wins: PLSR"),
        ("Final PLSR model", "Retrained on all sessions for new samples"),
        ("Results", "Accuracy on sessions the model never saw")]


def box9(num, ttl, desc, x, y, w, h, kind):
    fill, line, tc, dc, nc = {"data": (CREAM, LINE, INK, MUTED, GOLD), "model": ("FFFFFF", GOLD, INK, MUTED, GOLD),
                              "result": (INK, INK, GOLD_LT, ON_DARK2, GOLD_LT)}[kind]
    return shape(ids_, f"Step {num}", x, y, w, h, fill=fill, line=line, lw=1, adj=8000, anchor="t", ins=(0.12, 0.08, 0.10, 0.06),
                 shadow=kind == "data", paras=[para(run(f"STEP {num}", 8.5, b=True, color=nc, spc=100), aft=1),
                                               para(run(ttl, 11.5, b=True, color=tc, font="Cambria"), aft=2, lnspc=95),
                                               para(run(desc, 10, color=dc), lnspc=95)])


W1, G1, Y1, BH9 = 2.06, 0.45, 1.78, 1.0
x1s = [0.62 + i * (W1 + G1) for i in range(5)]
W2, G2, Y2 = 1.976, 0.42, 3.80
x2s = [0.77, 0.77 + W2 + G2]; x2s += [x2s[1] + W2 + G2 + 0.12 + i * (W2 + G2) for i in range(3)]
IX0, IX1 = x2s[2] - 0.12, x2s[4] + W2 + 0.12
Y3 = 5.78
x3s = [0.77, 0.77 + W2 + G2, 0.77 + 2 * (W2 + G2)]
OUTF = (0.62, 3.25, 12.72, 5.38); INF = (IX0, 3.47, IX1, 5.14)
shapes_bg = [shape(ids_, "Leave-one-session-out frame", OUTF[0], OUTF[1], OUTF[2] - OUTF[0], OUTF[3] - OUTF[1], fill=None, line=GOLD, lw=1.25, dash="dash", adj=4000),
             shape(ids_, "Per-model frame", INF[0], INF[1], INF[2] - INF[0], INF[3] - INF[1], fill=None, line="B9A894", lw=1.0, dash="sysDot", adj=5000),
             text(ids_, "Loop label", 6.0, OUTF[1] + 0.04, 6.57, 0.22, [para([run("↻  LEAVE-ONE-SESSION-OUT  ", 9, b=True, color=BROWN, spc=100),
                                                                              run("repeated with each session held out in turn", 9, color=MUTED)], algn="r")]),
             text(ids_, "Inner loop label", IX0 + 0.12, INF[1] + 0.05, 4, 0.22, [para(run("↻  FOR EACH REGRESSION MODEL", 9, b=True, color=MUTED, spc=100))])]
sp += shapes_bg
flow = []
# row 1 arrows
for i in range(1, 5):
    flow.append(line2(ids_, f"Arrow {i}", x1s[i - 1] + W1 + 0.04, Y1 + BH9 / 2, x1s[i] - 0.04, Y1 + BH9 / 2))
# row 1 -> step 6
c5, c6 = x1s[4] + W1 / 2, x2s[0] + W2 / 2
flow += path(ids_, "Into the loop", [(c5, Y1 + BH9), (c5, 3.06), (c6, 3.06), (c6, Y2 - 0.03)])
# row 2 arrows
for i in range(1, 5):
    flow.append(line2(ids_, f"Arrow {i + 5}", x2s[i - 1] + W2 + 0.04, Y2 + BH9 / 2, x2s[i] - 0.04, Y2 + BH9 / 2))
# repeat arrows (dashed): next model 10 -> 8, next session 10 -> 6
x10 = x2s[4]
flow += path(ids_, "Next model", [(x10 + 0.50, Y2 + BH9), (x10 + 0.50, 4.98), (x2s[2] + 0.50, 4.98), (x2s[2] + 0.50, Y2 + BH9 + 0.02)],
             color=MUTED, lw=1.25, head="med", dash="dash")
flow += path(ids_, "Next session", [(x10 + 1.00, Y2 + BH9), (x10 + 1.00, 5.26), (x2s[0] + 1.00, 5.26), (x2s[0] + 1.00, Y2 + BH9 + 0.02)],
             color=BROWN, lw=1.25, head="med", dash="dash")
# leave the loop from step 10 to step 11
c11 = x3s[0] + W2 / 2
flow += path(ids_, "Out of the loop", [(x10 + 1.55, Y2 + BH9), (x10 + 1.55, 5.57), (c11, 5.57), (c11, Y3 - 0.03)])
for i in range(1, 3):
    flow.append(line2(ids_, f"Arrow {i + 10}", x3s[i - 1] + W2 + 0.04, Y3 + BH9 / 2, x3s[i] - 0.04, Y3 + BH9 / 2))
sp += flow
def tag9(name, cx, cy, w, t_, color):
    return text(ids_, name, cx - w / 2, cy - 0.10, w, 0.20, [para(run(t_, 8.5, b=True, i=True, color=color), algn="ctr")], anchor="ctr")
sp += [shape(ids_, "Next model tag bg", (x2s[2] + x10) / 2 + 0.5 - 0.48, 4.88, 0.96, 0.20, prst="rect", fill="FFFFFF", line=None, ins=(0, 0, 0, 0)),
       tag9("Next model tag", (x2s[2] + x10) / 2 + 0.5, 4.98, 0.96, "next model", MUTED),
       shape(ids_, "Next session tag bg", 3.6 - 0.55, 5.16, 1.10, 0.20, prst="rect", fill="FFFFFF", line=None, ins=(0, 0, 0, 0)),
       tag9("Next session tag", 3.6, 5.26, 1.10, "next session", BROWN),
       shape(ids_, "Exit tag bg", 6.6 - 1.25, 5.47, 2.50, 0.20, prst="rect", fill="FFFFFF", line=None, ins=(0, 0, 0, 0)),
       tag9("Exit tag", 6.6, 5.57, 2.50, "after all three sessions", BROWN)]
for i, ((t_, d_), x) in enumerate(zip(DATA9, x1s)): sp.append(box9(i + 1, t_, d_, x, Y1, W1, BH9, "data"))
for i, ((t_, d_), x) in enumerate(zip(LOOP9, x2s)): sp.append(box9(i + 6, t_, d_, x, Y2, W2, BH9, "model"))
for i, ((t_, d_), x) in enumerate(zip(END9, x3s)): sp.append(box9(i + 11, t_, d_, x, Y3, W2, BH9, "result" if i == 2 else "model"))
sp.append(shape(ids_, "Why this order", 7.95, Y3, 4.77, BH9, fill=CREAM2, line=LINE, adj=8000, ins=(0.18, 0.08, 0.16, 0.06), anchor="ctr",
                paras=[para(run("Why this order matters", 12, b=True, color=BROWN, font="Cambria"), aft=2),
                       para(run("Trimming, tuning and training never see the held-out session, so the reported error "
                                "is the one a new day of scanning would give.", 10.5, color=INK), lnspc=100)]))
wr(22, SLD_HEAD + "".join(sp) + SLD_TAIL)

# ================================================================== v9: data acquisition with the setup photo (slide20)
s20 = rd(20)
tbl = shapes_named(s20, lambda nm: nm == "Table 6")[0]
scan = shapes_named(s20, lambda nm: nm == "Scan")[0]
track = shapes_named(s20, lambda nm: nm.startswith("Tracker step") or nm == "Pipeline tracker label")
PX0, PY0, PH = 0.62, 1.55, 5.40
PW = PH * 960 / 980
rid_photo = add_media(20, FIG / "setup_photo.png")
ids_ = Ids(300)
sp = [text(ids_, "Title", 0.62, 0.38, 8.3, 0.62, [para(run("Data acquisition", 32, b=True, color=INK, font="Cambria"))]),
      text(ids_, "Subtitle", 0.62, 1.02, 12.10, 0.40, [para(run(
          "Push-broom SWIR imaging of loose powder under halogen light, referenced to a certified Spectralon target", 14, color=MUTED))]),
      pic(ids_, "Setup photo", rid_photo, PX0, PY0, PW, PH, "The imaging setup: SWIR camera on a tripod arm, two halogen lamps, samples and white reference on a black background")]
SC = PW / 960
def ph(px, py):  # photo pixel (original 960 x 1280 coordinates) -> slide inches
    return PX0 + px * SC, PY0 + (py - 300) * SC
TAGS = [("SWIR camera", (330, 400), (372, 548)), ("Halogen lamp", (115, 500), (130, 652)), ("Halogen lamp", (700, 420), (772, 536)),
        ("Laptop", (575, 660), (452, 745)), ("White reference", (760, 912), (612, 962)), ("Samples", (300, 1112), (468, 1018)),
        ("Black background", (720, 1162), (640, 1082)), ("Tripod", (80, 960), (178, 902))]
arrows_, tags_ = [], []
for k, (t_, (tx, ty), (ax_, ay_)) in enumerate(TAGS):
    w = 0.068 * len(t_) + 0.24
    cx, cy = ph(tx, ty); ex, ey = ph(ax_, ay_)
    arrows_.append(line2(ids_, f"Callout {k + 1} casing", cx, cy, ex, ey, color=INK, lw=4.0, head="med"))
    arrows_.append(line2(ids_, f"Callout {k + 1} arrow", cx, cy, ex, ey, color="FFFFFF", lw=1.9, head="med"))
    tags_.append(shape(ids_, f"Callout {k + 1}", cx - w / 2, cy - 0.13, w, 0.26, fill=INK, line="FFFFFF", lw=0.75, adj=30000, alpha=92,
                       anchor="ctr", ins=(0.05, 0, 0.05, 0), paras=[para(run(t_, 9.5, b=True, color="FFFFFF"), algn="ctr")]))
sp += arrows_ + tags_
# scan strip and parameter table
SX, SH = 6.15, 4.00
scan = re.sub(r'<a:off x="\d+" y="\d+"/><a:ext cx="\d+" cy="\d+"/>', f'<a:off x="{emu(SX)}" y="{emu(PY0)}"/><a:ext cx="{emu(SH * 516 / 1275)}" cy="{emu(SH)}"/>', scan, count=1)
TX, TW = 8.00, 12.72 - 8.00
tbl = re.sub(r'<p:xfrm>.*?</p:xfrm>', f'<p:xfrm><a:off x="{emu(TX)}" y="{emu(PY0)}"/><a:ext cx="{emu(TW)}" cy="{emu(SH)}"/></p:xfrm>', tbl, flags=re.S)
tbl = re.sub(r'<a:tr h="\d+">', f'<a:tr h="{emu(SH / 11)}">', tbl)
tbl = re.sub(r'<a:tblGrid>.*?</a:tblGrid>', f'<a:tblGrid><a:gridCol w="{emu(1.62)}"/><a:gridCol w="{emu(TW - 1.62)}"/></a:tblGrid>', tbl, flags=re.S)
sp += [scan, tbl,
       text(ids_, "Scan caption", SX, PY0 + SH + 0.12, 1.75, 0.26, [para(run("One scan", 12, b=True, color=BROWN, font="Cambria"))]),
       text(ids_, "Scan caption text", SX, PY0 + SH + 0.40, 1.75, 0.60, [para(run("White strip at the top, dishes in a row below", 9.5, color=MUTED), lnspc=95)]),
       shape(ids_, "Reference note", TX, PY0 + SH + 0.18, TW, 1.22, fill=CREAM, line=LINE, adj=8000, ins=(0.18, 0.10, 0.16, 0.10), anchor="ctr",
             paras=[para(run("Every scan carries its own reference", 12, b=True, color=BROWN, font="Cambria"), aft=3),
                    para(run("The white strip is imaged with the dishes, so each scan is calibrated on its own: see the next slide.", 11, color=INK), lnspc=100)])]
sp += track
x20 = SLD_HEAD + "".join(sp) + SLD_TAIL
wr(20, set_tracker(x20, {1}, "STEP 1 OF 13 · DATA ACQUISITION"))
prune_image_rels(20)
set_notes(20, "The imaging setup. The HySpex SWIR camera sits on a tripod arm looking down at the samples, which lie on a black background "
              "next to a white Spectralon reference. Two halogen lamps light the scene, and the laptop runs the acquisition. The camera records "
              "one line at a time across the samples. Every scan includes the white strip, which the next slide uses to turn camera counts "
              "into reflectance. Each blend was re-stirred and scanned three times, over three sessions.")

# ================================================================== v9: reflectance and dish masking (new slide NEW2)
ids_ = Ids(300)
sp = [text(ids_, "Title", 0.62, 0.38, 8.3, 0.62, [para(run("Reflectance and dish masking", 32, b=True, color=INK, font="Cambria"))]),
      text(ids_, "Subtitle", 0.62, 1.02, 12.10, 0.40, [para(run(
          "Turn camera counts into a property of the powder, then keep only clean powder pixels", 14, color=MUTED))])]
LX2, LW2, RX2, RW2, TOP2, BOT2 = 0.62, 6.05, 6.92, 5.80, 1.58, 6.98
sp += [shape(ids_, "Reflectance card", LX2, TOP2, LW2, BOT2 - TOP2, fill=CREAM, line=LINE, adj=4000, shadow=True),
       badge(ids_, "Badge 2", LX2 + 0.24, TOP2 + 0.18, 2),
       text(ids_, "Heading 2", LX2 + 0.68, TOP2 + 0.18, 5.0, 0.34, [para(run("Radiance → reflectance", 15, b=True, color=INK, font="Cambria"))], anchor="ctr")]
def eq_run(t_, sz, it=False, sub=False, color=INK, b=False):
    base = ' baseline="-25000"' if sub else ""
    return (f'<a:r><a:rPr lang="en-US" sz="{int(sz * 100)}" b="{int(b)}" i="{int(it)}" dirty="0"{base}><a:solidFill><a:srgbClr val="{color}"/></a:solidFill>'
            f'<a:latin typeface="Cambria"/><a:ea typeface="Cambria"/><a:cs typeface="Cambria"/></a:rPr><a:t xml:space="preserve">{escape(t_)}</a:t></a:r>')
IX = LX2 + 0.26; IW = LW2 - 0.52
# A. what radiance is, and why we want reflectance
AY, AH, AW = TOP2 + 0.64, 1.10, 2.22
sp += [shape(ids_, "Radiance card", IX, AY, AW, AH, fill="FFFFFF", line=LINE, adj=8000, anchor="t", ins=(0.14, 0.08, 0.12, 0.06),
             paras=[para(run("Radiance", 13, b=True, color=INK, font="Cambria"), aft=0),
                    para(run("WHAT THE CAMERA RECORDS", 7.5, b=True, color=GOLD, spc=80), aft=3),
                    para(run("The raw light reaching the camera. It changes with the lamp, the camera and the day.", 10, color=INK), lnspc=98)]),
       shape(ids_, "Reflectance card small", IX + IW - AW, AY, AW, AH, fill=INK, line=INK, adj=8000, anchor="t", ins=(0.14, 0.08, 0.12, 0.06),
             paras=[para(run("Reflectance", 13, b=True, color=GOLD_LT, font="Cambria"), aft=0),
                    para(run("WHAT THE MODEL NEEDS", 7.5, b=True, color=GOLD, spc=80), aft=3),
                    para(run("The fraction of light the powder sends back, 0 to 1. Only the powder changes it.", 10, color=ON_DARK), lnspc=98)]),
       line2(ids_, "Convert arrow", IX + AW + 0.08, AY + AH / 2, IX + IW - AW - 0.08, AY + AH / 2, color=BROWN, lw=1.5, head="med"),
       text(ids_, "Convert label", IX + AW, AY + AH / 2 - 0.36, IW - 2 * AW, 0.30, [para(run("÷ white tile", 10, b=True, i=True, color=BROWN), algn="ctr")], anchor="ctr")]
# B. the equation, each term coloured and labelled underneath
EY = AY + AH + 0.22
COLS = {"Rp": "6B4423", "Lp": "B5651D", "Lw": "5E7385", "Rw": "C8964F"}
TERMS = [("Rp", "R", "powder", 1.18, "reflectance of the powder: what we want"),
         ("op", "=", None, 0.36, None),
         ("Lp", "L", "powder", 1.18, "radiance from the powder"),
         ("op", "÷", None, 0.36, None),
         ("Lw", "L", "white", 1.08, "radiance from the white tile, same scan and column"),
         ("op", "×", None, 0.36, None),
         ("Rw", "R", "white", 1.08, "the white tile's known reflectance, 0.99"),]
tot = sum(t[3] for t in TERMS); x = IX + (IW - tot) / 2
for key, sym, subs, w, lab in TERMS:
    if key == "op":
        sp.append(text(ids_, f"Operator {sym}", x, EY, w, 0.50, [f'<a:p><a:pPr algn="ctr"/>{eq_run(sym, 22, color=INK)}</a:p>'], anchor="ctr"))
    else:
        col = COLS[key]
        sp.append(text(ids_, f"Term {key}", x, EY, w, 0.50, [f'<a:p><a:pPr algn="ctr"/>{eq_run(sym, 24, it=True, b=True, color=col)}{eq_run(subs, 13, it=True, sub=True, b=True, color=col)}</a:p>'], anchor="ctr"))
        sp.append(shape(ids_, f"Term {key} bar", x + 0.12, EY + 0.52, w - 0.24, 0.045, prst="rect", fill=col, line=None, ins=(0, 0, 0, 0)))
        lw_ = w + 0.30
        sp.append(text(ids_, f"Term {key} label", x + w / 2 - lw_ / 2, EY + 0.62, lw_, 0.70, [para(run(lab, 9.5, b=key == "Rp", color=col), algn="ctr", lnspc=95)]))
    x += w
# C. the proof: brighter lamp, same reflectance
TY = EY + 1.42
rows = [["", "Powder radiance", "White radiance", "Reflectance"],
        ["Normal lamp", "1200", "3000", "0.40"],
        ["Lamp 10 % brighter", "1320", "3300", "0.40"]]
sp.append(table(Ids(8500), "Lamp example", IX, TY, [1.62, 1.29, 1.29, IW - 4.20], rows, 0.31, header_sz=9.5, sz=10.5,
                aligns=["l", "ctr", "ctr", "ctr"], bold_rows=(), highlight_rows=()))
sp.append(text(ids_, "Lamp example note", IX, TY + 1.12, IW, 0.62, [
    para([run("The radiance moved by 10 %; the reflectance did not. ", 10.5, b=True, color=BROWN),
          run("That is why the model is trained on reflectance. It is computed for each of the 384 pixel columns, so uneven lighting across the image cancels too. (Illustrative counts.)", 10, color=INK)], lnspc=100)]))
# dish masking, as before
IMS2 = 3.30; IMX2, IMY2 = RX2 + 0.24, TOP2 + 0.70
sc2 = IMS2 / 1024
mpt2 = (IMX2 + 509.6 * sc2, IMY2 + 513.6 * sc2); rpt2 = (IMX2 + 850 * sc2, IMY2 + 779 * sc2)
rid_mask = add_media(NEW2, FIG / "mask_simple.png")
LBX = IMX2 + IMS2 + 0.40
sp += [shape(ids_, "Masking card", RX2, TOP2, RW2, BOT2 - TOP2, fill=CREAM, line=LINE, adj=4000, shadow=True),
       badge(ids_, "Badge 3", RX2 + 0.24, TOP2 + 0.18, 3),
       text(ids_, "Heading 3", RX2 + 0.68, TOP2 + 0.18, 4.5, 0.34, [para(run("Dish masking", 15, b=True, color=INK, font="Cambria"))], anchor="ctr"),
       pic(ids_, "Mask", rid_mask, IMX2, IMY2, IMS2, IMS2, "Real mask of dish RB[70:30], session 2: kept powder pixels tinted, petri dish left out"),
       shape(ids_, "Mask swatch", LBX, IMY2 + 0.42, 0.20, 0.20, prst="rect", fill="E0B872", line="C8964F", lw=1.25, ins=(0, 0, 0, 0)),
       text(ids_, "Mask label", LBX + 0.30, IMY2 + 0.30, RX2 + RW2 - LBX - 0.45, 1.10, [para(run("Mask", 14, b=True, color=BROWN, font="Cambria"), aft=2),
                                                                                 para(run("powder pixels the model uses, about 90 % of the dish", 10.5, color=INK), lnspc=100)]),
       line2(ids_, "Mask arrow", LBX - 0.08, IMY2 + 0.52, mpt2[0] + 0.05, mpt2[1] - 0.02, color=INK, lw=1.75, head="med"),
       text(ids_, "Dish label", LBX + 0.30, IMY2 + 1.85, RX2 + RW2 - LBX - 0.45, 1.10, [para(run("Petri dish", 14, b=True, color=INK, font="Cambria"), aft=2),
                                                                                para(run("left out: rim, wall and shadow", 10.5, color=INK), lnspc=100)]),
       line2(ids_, "Dish arrow", LBX + 0.22, IMY2 + 2.07, rpt2[0] + 0.03, rpt2[1], color=INK, lw=1.75, head="med"),
       text(ids_, "Mask note", IMX2, IMY2 + IMS2 + 0.18, RW2 - 0.48, 0.40, [para(run(
           "The mask is then cut into 12 × 12 px patches, one mean spectrum each.", 10.5, i=True, color=MUTED), lnspc=95)])]
sp += track
xn = SLD_HEAD + "".join(sp) + SLD_TAIL
wr(NEW2, set_tracker(xn, {2, 3}, "STEPS 2–3 OF 13 · REFLECTANCE AND MASKING"))
prune_image_rels(NEW2)
set_notes(NEW2, "Step 2. The camera gives raw counts that depend on the lamp and the camera itself. Dividing the powder's signal by the white "
                "strip's signal, column by column, cancels both; multiplying by the strip's certified reflectance gives the true fraction of "
                "light the powder reflects. If the lamp were ten percent brighter, both signals would rise together and the ratio would not "
                "change. Step 3. Only the powder inside the drawn outline is kept, about 90 percent of each dish; the rim, wall and shadow of "
                "the petri dish are left out.")

print("built; new slide =", NEW, "sid", new_sid)
