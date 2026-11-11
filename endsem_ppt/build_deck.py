"""Fill the 25-slide skeleton (midsem slides reordered/duplicated) with the end-semester content."""
import copy, json
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Emu, Pt
from PIL import Image

HERE = Path(__file__).parent
FIG = HERE / "figs"
N = json.load(open(HERE / "numbers.json"))
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
RNS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
q = lambda t: f"{{{A}}}{t}"
prs = Presentation(HERE / "struct.pptx")
S = prs.slides

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

# ================================================================== 1 title
s = S[0]
set_text(s, "Text 0", ["END-SEMESTER PROJECT EVALUATION"])
notes(s, "End-semester evaluation. At the midsem we quantified chicory in robusta. Since then the same method has been extended "
         "to arabica and to arabica + robusta blends, a classifier now names the coffee base first, and a final check confirms the chosen models.")

# ================================================================== 2 coffee and additives: both species are now used
s = S[1]
tag = shp(s, "This work tag")
new = copy.deepcopy(tag._element); tag._element.addnext(new)
ids = [int(e.get("id")) for e in s.shapes._spTree.iter() if e.tag.endswith("}cNvPr")]
new.find(".//{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr").set("id", str(max(ids) + 1))
new.find(".//{http://schemas.openxmlformats.org/presentationml/2006/main}cNvPr").set("name", "This work tag arabica")
off = new.find(".//" + q("off")); off.set("x", str(Inches(7.53)))
notes(s, "Two commercial species: arabica and robusta. Both are now used in this work, as is their blend. Chicory is the one additive the law allows, "
         "but only as a declared blend with at least 51 percent coffee. The dish images are illustrative.")

# ================================================================== 3 objectives
s = S[2]
set_text(s, "Objectives list", [
    ["Quantify ", "chicory from 0–50 % by mass in three coffee bases (robusta, arabica and arabica + robusta), spanning the 49 % legal limit."],
    ["Identify ", "the coffee base first, so each blend is measured by the right model."],
    ["Non-destructive: ", "powder is imaged as-is, with no reagents and no preparation."],
    ["Imaging ", "rather than point spectroscopy: every dish gives thousands of spectra, not one."],
    ["Validate ", "by holding out each scanning session in turn, so every model is tested on a day it never saw."]])
notes(s, "The gaps in existing methods are unchanged. The objectives now cover three coffee bases and add one new step: naming the base before measuring chicory.")

# ================================================================== 5 why HSI
s = S[4]
set_text(s, "Why text 1", ["Roasted chicory and coffee look almost the same, so colour alone cannot give the blend ratio."])

# ================================================================== 6 data acquisition (now part of the introduction)
s = S[5]
drop_tracker(s)
t = shp(s, "Table 6").table
for r in range(len(t.rows)):
    if t.cell(r, 0).text == "Sessions": set_cell(t.cell(r, 1), "9: 3 per coffee base, 1–8 Sep")
set_text(s, "Reference note", ["Every scan carries its own reference",
                               "The white strip is imaged with the dishes, so each scan is calibrated on its own."])
notes(s, "The imaging setup is the same as at the midsem: the HySpex SWIR camera above the samples, two halogen lamps and a Spectralon strip "
         "in every scan. Nine sessions were scanned, three for each coffee base, each blend re-stirred and scanned three times.")

# ================================================================== 7 from midsem to endsem (copy of slide 3)
s = S[6]
set_text(s, "Title", ["From midsem to endsem"])
set_text(s, "Subtitle", ["The midsem quantified chicory in robusta; the endsem carries the same method to arabica and to arabica + robusta blends"])
set_text(s, "Heading 1", ["At the midsem"])
set_text(s, "Heading 2", ["Added since the midsem"])
set_text(s, "Disadvantages list", [
    ["Robusta + chicory only: ", "PLSR on absorbance + offset, 0.79 % error on unseen sessions."],
    ["Arabica slipped through: ", "an arabica blend passed every check on the robusta model but read 8–10 points low."],
    ["Eight methods compared ", "with eight preprocessings, on one coffee base."],
    ["Future scope set: ", "calibrate other coffee bases, and gate each sample by its base before regression."]])
set_text(s, "Objectives list", [
    ["Arabica + chicory: ", "33 new dishes; EMSC + PLSR, 0.78 % error on unseen sessions."],
    ["Arabica + robusta + chicory: ", "33 dishes; first derivative on the oil bands + PLSR, 0.94 %."],
    ["A base gate: ", "a PCA-LDA classifier names the coffee base first, 95 % correct on unseen days."],
    ["A final check: ", "14 preprocessings × 5 linear models per base; none beats the chosen models."],
    ["A working tool: ", "a browser app reads a scan, finds the dishes and reports base and chicory %."]])
notes(s, "Left is where the midsem ended: one coffee base, and an open failure mode where arabica blends read low. Right is what was added: "
         "two new bases with their own models, the gate the midsem asked for, an exhaustive final check, and the app.")

# ================================================================== 8 dataset
s = S[7]
set_text(s, "Text 1", ["Gravimetric blends of roasted coffee and roasted chicory in three coffee bases, 11 levels and three sessions each"])
set_text(s, "Text 2", ["3"]); set_text(s, "Text 3", ["COFFEE BASES", "robusta · arabica · both"])
set_text(s, "Text 4", ["99"]); set_text(s, "Text 5", ["PLATES", "33 per base, 3 re-stirs"])
set_text(s, "Text 6", ["14 800"]); set_text(s, "Text 7", ["PATCH SPECTRA", "12 × 12 px, averaged"])
set_text(s, "Text 10", ["9"]); set_text(s, "Text 11", ["SESSIONS", "3 per base, over 8 days"])
fill_table(s, "Table 0", [["Robusta (RB)", "1, 4, 8 Sep", "0 · 10–50 · 5–45"],
                          ["Arabica (AB)", "1, 4, 8 Sep", "0 · 10–50 · 5–45"],
                          ["Arabica + robusta (AR)", "4 Sep ×2, 7 Sep", "30–50 · 0–20 · 5–45"]],
           header=["Coffee base", "Sessions", "Chicory levels (%)"], col_w=[1.95, 1.3, 2.1])
set_text(s, "Text 14", ["AR blends: chicory % is the label's second number (assumed); one AR 50:50 set (4 Sep, 13:30) is excluded."])
notes(s, "Three coffee bases, 33 dishes each, so 99 dishes and about 14,800 patch spectra. Each base has three sessions. "
         "For the AR blends the chicory level is read from the label, which is an assumption still to be confirmed from the lab notes.")

# ================================================================== 9 methodology
s = S[8]
set_text(s, "Subtitle", ["Thirteen steps from scan to result, run separately for each coffee base, with every model judged on a session it never saw"])
set_text(s, "Step 1", ["STEP 1", "Data acquisition", "3 bases × 11 blends, 0–50 % chicory, 3 sessions each"])
set_text(s, "Step 2", ["STEP 2", "Counts → reflectance", "Dark signal removed, then calibrated on a Spectralon strip"])
set_text(s, "Step 5", ["STEP 5", "Spectral preprocessing", "14 options; offset, EMSC or SG1, by base"])
set_text(s, "Step 11", ["STEP 11", "Model selection", "Lowest mean held-out error, for each base"])
set_text(s, "Step 12", ["STEP 12", "Final models", "One per base, retrained on all its sessions"])
notes(s, "The pipeline is the midsem pipeline, run once per coffee base. What changed is step 2, where raw-count files first lose their dark signal, "
         "step 5, where the preprocessing is now chosen per base, and steps 11 and 12, which give one final model per base.")

# ================================================================== 10 reflectance and masking
s = S[9]
set_text(s, "Subtitle", ["Camera counts become a property of the powder (raw-count files lose their dark signal first), then only clean powder is kept"])

# ================================================================== 11 preprocessing candidates
s = S[10]
set_text(s, "Subtitle", ["Fourteen transforms in four families, each tried with five linear models on every coffee base"])
set_text(s, "Transform Log Transform how 2", ["A minus its own mean, spectrum by spectrum: removes the brightness offset. Chosen for robusta."])
set_text(s, "Transform Scatter Correction name 1", ["SNV / MSC"])
set_text(s, "Transform Scatter Correction how 1", ["Centre and scale each spectrum (SNV), or remove offset and slope against the mean (MSC)."])
set_text(s, "Transform Scatter Correction name 2", ["EMSC"])
set_text(s, "Transform Scatter Correction how 2", ["Removes baseline, tilt, curvature and scale; keeps the chicory direction. Chosen for arabica."])
set_text(s, "DERIVATIVES header", ["DERIVATIVES AND BAND SELECTION"])
set_text(s, "Transform Derivatives name 1", ["SG1 / SG2"])
set_text(s, "Transform Derivatives how 1", ["Savitzky–Golay first or second derivative: removes offsets and tilts, sharpens bands."])
set_text(s, "Transform Derivatives name 2", ["Log + derivative"])
set_text(s, "Transform Derivatives how 2", ["Absorbance, then SG1, with or without SNV first."])
set_text(s, "Transform Derivatives name 3", ["Chemistry bands"])
set_text(s, "Transform Derivatives how 3", ["Only 1650–1800 and 2150–2400 nm (oil, C–H); the SG1 version is chosen for the three-way blend."])
set_text(s, "Test 3", ["Same five linear models, with the same tuning rule"])
notes(s, "Fourteen transforms in four families. Two are new since the midsem: EMSC, which ends up chosen for arabica, and chemistry-band selection, "
         "whose first-derivative version is chosen for the three-way blend. Robusta keeps absorbance plus offset.")

# ================================================================== 12 how the model is tested
s = S[11]
set_text(s, "Subtitle", ["Leave-one-session-out, run for each coffee base: every result comes from a scanning session the model never saw"])
set_text(s, "Header Session 1", ["Session 1", "RB, AB 0 % · AR 30–50 %"])
set_text(s, "Header Session 2", ["Session 2", "RB, AB 10–50 % · AR 0–20 %"])
set_text(s, "Header Session 3", ["Session 3", "all bases 5–45 %"])
set_text(s, "R1 S1 test", ["HELD OUT · TEST", "RB, AB: bias at 0 %"])
set_text(s, "R2 S2 test", ["HELD OUT · TEST", "RB, AB: up to 50 %"])
set_text(s, "R3 S3 test", ["HELD OUT · TEST", "levels never trained on"])
notes(s, "The test is the same as at the midsem, applied to each base on its own three sessions. Inside every round the settings are tuned on the "
         "training sessions only, so the held-out session is touched once, to score the prediction.")

# ================================================================== 13 models tried
s = S[12]
set_text(s, "Subtitle", ["Eight core methods on every coffee base, plus literature extensions — all tuned and scored inside the same leave-one-session-out rounds"])
set_text(s, "Rules heading", ["Also tried since the midsem"])
set_text(s, "Rule 1", ["EMSC + PLSR and EMSC + SVR (scatter-corrected)"])
set_text(s, "Rule 2", ["EPO-PLSR, di-PLS and a joint robusta + arabica PLSR (transfer)"])
set_text(s, "Rule 3", ["VIP band selection, SO-PLS and model ensembles (selection, fusion)"])
set_text(s, "Rule 4", ["Mixing models (absorbance, Kubelka–Munk) and GPR on PLS scores"])
set_text(s, "Rules footnote", ["Same rounds, same tuning, same per-dish scoring as the core eight."])
notes(s, "The eight core methods from the midsem were run on every base. On the robusta and arabica blends we also tried the methods the literature "
         "suggests for this kind of data: scatter correction, transfer methods, band selection, ensembles, physical mixing models and a Gaussian process. "
         "Only EMSC + PLSR improved anything, and only for arabica.")

# ================================================================== 14 robusta recap (copy of the midsem winner slide)
s = S[13]
set_text(s, "Title", ["Robusta + chicory: PLSR (midsem result)"])
set_text(s, "Subtitle", ["Recap of the midsem model; the final check keeps it, with every lower-scoring alternative a statistical tie"])
set_text(s, "Winner pill", ["MIDSEM · ROBUSTA"])
notes(s, "A one-slide recap of the midsem result for robusta: PLSR on absorbance plus offset, 0.79 percent. The final check later in the deck tested it again "
         "against 69 alternatives and none was significantly better, so it stays.")

# ================================================================== 15–17 arabica + chicory
NICE = {"chemistry bands, derivative + PLSR": "Chem. SG1 + PLSR", "first derivative + PLSR": "SG1 + PLSR"}
def cmp_rows(d, winner):
    rows = []
    for m, v in d.items():
        name = NICE.get(m, m) + (" (winner)" if m == winner else "")
        rows.append([name] + [f"{x:.2f}" for x in v])
    return rows

s = S[14]
set_text(s, "Text 0", ["Arabica + chicory: choosing the method"])
set_text(s, "Text 1", ["Eight core methods plus EMSC + PLSR, identical folds and tuning — each scored on sessions it never saw"])
swap_image(s, "Image 0", FIG / "ab_compare.png")
fill_table(s, "Table 0", cmp_rows(N["ab_cmp"], "EMSC + PLSR"), row_h=0.24)
set_text(s, "Text 2", ["Error per dish on each held-out session. A bootstrap over dishes puts EMSC + PLSR − SVR (linear) at −0.15 pp "
                       "(95 % CI −0.28 to +0.00): a tie, broken by the lower error in two of three sessions."])
set_text(s, "Text 5", [
    ["Plain PLSR fails on arabica. ", "2.61 %, almost all from session 1: pure arabica scanned on a new day reads 4.4 points low."],
    ["Scatter correction fixes it. ", "EMSC removes the day-to-day baseline and scale; EMSC + PLSR falls to 0.78 %, the lowest of all."],
    ["Linear SVR is close behind. ", "0.93 %, a statistical tie; EMSC + PLSR is lower in two of three sessions and has one setting."],
    ["Nonlinear methods are 6–11 times worse. ", "Random forest, boosting and RBF-SVR: 4.59–8.42 %."]])
notes(s, "Arabica, same eight methods plus EMSC. Plain PLSR fails here because on a new day pure arabica reads 4 points low: arabica's "
         "baseline and scale shift between sessions. EMSC removes exactly that, and EMSC + PLSR becomes the best at 0.78 percent. "
         "Linear SVR is a statistical tie.")

ab = N["ABCH"]
s = S[15]
set_text(s, "Text 0", ["Arabica + chicory: unseen sessions"])
set_text(s, "Text 1", ["EMSC + PLSR, 4 latent variables: each session predicted by a model that never saw it"])
swap_image(s, "Image 0", FIG / "ab_fit.png")
set_text(s, "Text 2", [f"{ab['mean']:.2f} %"]); set_text(s, "Text 3", ["MEAN ERROR", f"per dish, ± {ab['sd']:.2f} across sessions"])
set_text(s, "Text 4", [f"{ab['pooled']:.2f} %"]); set_text(s, "Text 5", ["POOLED ERROR", "all 33 held-out dishes"])
set_text(s, "Text 6", [f"{ab['r2']:.3f}"]); set_text(s, "Text 7", ["R² (held out)", f"RPD {ab['rpd']:.1f}"])
set_text(s, "Text 8", [f"{ab['max_bias']:.2f} %"]); set_text(s, "Text 9", ["MAX BIAS", "worst session"])
set_text(s, "Text 10", ["Left: every super-patch and dish mean, coloured by the session that was held out. Centre: error on each held-out session. "
                        "Right: systematic offset per session. Session 1 holds only pure arabica, so it checks bias alone."])
notes(s, f"Every number comes from a session the model never saw. Session 2 is the hardest at {ab['err']['2']:.2f} percent. "
         f"The mean over the three rounds, {ab['mean']:.2f} percent, matches robusta.")

def blind_rows(key):
    return [[r["label"], str(r["session"]), f"{r['y']:.0f}", f"{r['p']:.2f}", fmt(r["e"])] for r in N[key]["rows"]]

b = N["ABCH_blind"]
s = S[16]
set_text(s, "Text 0", ["Arabica + chicory: every blend, blind"])
set_text(s, "Text 1", ["All 11 arabica blends, each predicted by the round that held its session out — no retraining, no correction"])
swap_image(s, "Image 0", FIG / "ab_blind.png")
fill_table(s, "Table 0", blind_rows("ABCH_blind"))
set_text(s, "Text 3", [f"Largest miss  {fmt(b['worst']['e'])} pp"])
bias = ab["bias"]
set_text(s, "Text 4", [f"All 11 blends within ±{b['max_abs'] + 0.005:.1f} pp of the weighed value",
                       f"Bias by session   {fmt(bias['1'])}  ·  {fmt(bias['2'])}  ·  {fmt(bias['3'])} pp",
                       f"Slope   {b['slopes']['2']:.3f} (session 2)  ·  {b['slopes']['3']:.3f} (session 3)"])
notes(s, f"Blind predictions for every arabica blend. The largest miss is {b['worst']['label']} at {fmt(b['worst']['e'])} points; "
         "the errors change sign along the range and the slopes stay close to one.")

# ================================================================== 18–20 arabica + robusta + chicory
s = S[17]
set_text(s, "Text 0", ["Three-way blend: choosing the method"])
set_text(s, "Text 1", ["Arabica + robusta + chicory: eleven models on the AR blends, read as a coffee base plus chicory, with identical folds and tuning"])
swap_image(s, "Image 0", FIG / "arc_compare.png")
fill_table(s, "Table 0", cmp_rows(N["arc_cmp"], "chemistry bands, derivative + PLSR"), row_h=0.205, font_pt=9)
set_text(s, "Text 2", ["Error per dish on each held-out session. Chicory % is the label's second number (assumed); the 13:30 AR 50:50 set is excluded."])
set_text(s, "Text 5", [
    ["Read as arabica vs robusta, the AR blends defeated every model. ", "Errors of 20–30 %: the component that varies behaves like chicory."],
    ["Read as coffee base + chicory, the error falls below 1 %. ", "SG1 on the oil and C–H bands + PLSR: 0.94 %, the lowest of eleven."],
    ["The correction matters most here. ", "Plain PLSR 1.71 %, EMSC 2.38 %: the derivative removes the shift between bases."],
    ["Nonlinear methods are 4–9 times worse. ", "3.96–8.35 %."]])
notes(s, "The AR series first failed as an arabica versus robusta problem: every model was off by 20 to 30 percent, and the oil bands followed the label "
         "the way chicory does. Read as a coffee base plus chicory, it works. Here the preprocessing decides: the first derivative on the oil and C–H bands "
         "removes the baseline shift between bases, and PLSR on it gives 0.94 percent.")

ac = N["ARC"]
s = S[18]
set_text(s, "Text 0", ["Three-way blend: unseen sessions"])
set_text(s, "Text 1", ["Arabica + robusta + chicory, SG1 on the chemistry bands + PLSR (5 latent variables): each session predicted by a model that never saw it"])
swap_image(s, "Image 0", FIG / "arc_fit.png")
set_text(s, "Text 2", [f"{ac['mean']:.2f} %"]); set_text(s, "Text 3", ["MEAN ERROR", f"per dish, ± {ac['sd']:.2f} across sessions"])
set_text(s, "Text 4", [f"{ac['pooled']:.2f} %"]); set_text(s, "Text 5", ["POOLED ERROR", "all 33 held-out dishes"])
set_text(s, "Text 6", [f"{ac['r2']:.3f}"]); set_text(s, "Text 7", ["R² (held out)", f"RPD {ac['rpd']:.1f}"])
set_text(s, "Text 8", [f"{ac['max_bias']:.2f} %"]); set_text(s, "Text 9", ["MAX BIAS", "worst session"])
set_text(s, "Text 10", ["Left: every super-patch and dish mean, coloured by the session held out. Centre: error per held-out session. Right: offset per session. "
                        "Session 1 (4 Sep, noon) holds 30–50 %, session 2 (4 Sep, 13:30) 0–20 %, session 3 (7 Sep) 5–45 %."])
notes(s, f"The three-way blend is the most even of the three bases across sessions: {ac['err']['1']:.2f}, {ac['err']['2']:.2f} and {ac['err']['3']:.2f} percent.")

b = N["ARC_blind"]; bias = ac["bias"]
s = S[19]
set_text(s, "Text 0", ["Three-way blend: every blend, blind"])
set_text(s, "Text 1", ["All 11 arabica + robusta + chicory blends, each predicted by the round that held its session out — no retraining"])
swap_image(s, "Image 0", FIG / "arc_blind.png")
fill_table(s, "Table 0", blind_rows("ARC_blind"), header=["Blend", "Session", "Label chicory %", "Predicted %", "Error (pp)"])
set_text(s, "Text 3", [f"Largest miss  {fmt(b['worst']['e'])} pp"])
set_text(s, "Text 4", [f"All 11 blends within ±{b['max_abs'] + 0.005:.1f} pp of the labelled value",
                       f"Bias by session   {fmt(bias['1'])}  ·  {fmt(bias['2'])}  ·  {fmt(bias['3'])} pp",
                       f"Slope   {b['slopes']['1']:.3f} (S1)  ·  {b['slopes']['2']:.3f} (S2)  ·  {b['slopes']['3']:.3f} (S3)"])
notes(s, f"Every AR blend predicted blind; the largest miss is {b['worst']['label']} at {fmt(b['worst']['e'])} points. "
         "These errors are against the labelled chicory level, which is the assumption to confirm.")

# ================================================================== 21 final check (copy of 'Choosing the preprocessing')
fc = N["final_check"]
s = S[20]
drop_tracker(s)
set_text(s, "Text 0", ["Final check: every preprocessing × model"])
set_text(s, "Subtitle", ["Fourteen preprocessings × five linear models for each coffee base, under the same nested test: 210 combinations"])
swap_image(s, "Preprocessing proof", FIG / "final_grid.png")
set_text(s, "Chart note", ["Mean error per dish on unseen sessions (%). Black box: the chosen model. Dotted blue: a statistical tie with it. "
                           "Every other cell is significantly worse."])
set_text(s, "Takeaways", [
    ["Nothing is significantly better. ", "None of the 69 alternatives beats the chosen model for any base (paired bootstrap, 95 %)."],
    ["Arabica + robusta + chicory: ", f"the chosen model ranks {fc['ARC']['current_rank']}st of 70."],
    ["Arabica + chicory: ", f"{fc['ABCH']['current_rank']}nd of 70; only EMSC + PCR is lower ({fc['ABCH']['lowest_mean']:.2f} %), a tie."],
    ["Robusta + chicory: ", f"{fc['RBCH']['current_rank']}th of 70; eight are lower (down to {fc['RBCH']['lowest_mean']:.2f} %), all ties, with less even errors across days."],
    ["Reproduced first: ", "the chosen models' published errors came out exactly, so the grid compares like with like."]])
notes(s, "The final check. For each base, every one of fourteen preprocessings with every one of five linear models went through the same nested test, "
         "210 combinations in all. The chosen models were reproduced exactly first. None of the alternatives is significantly better for any base; "
         "the few with a slightly lower mean are statistical ties.")

# ================================================================== 22 the maths (copy of 'Why the spectra need correcting')
s = S[21]
drop_tracker(s)
set_text(s, "Title", ["The maths behind the chosen models"])
set_text(s, "Subtitle", ["Each final model is one linear equation in the corrected spectrum; the three bases differ only in how the spectrum is corrected"])
swap_image(s, "Correction demo", FIG / "equations.png")
set_text(s, "Card 1 heading", ["PLSR · all three bases"])
set_text(s, "Card 1 text", ["Builds a few latent variables, the band combinations that covary most with chicory %, and regresses on them: 266 correlated bands become 4–6 stable numbers."])
set_text(s, "Card 2 heading", ["EMSC · arabica"])
set_text(s, "Card 2 text", ["Fits each spectrum as baseline, tilt, curvature and scale around the mean, keeping the chicory direction; dividing out the scale removes the packing effect."])
set_text(s, "Card 3 heading", ["SG1 + bands · three-way blend"])
set_text(s, "Card 3 text", ["A 15-point quadratic fit gives the slope at each band, so offsets cancel; keeping 1650–1800 and 2150–2400 nm leaves the oil and C–H bands."])
set_text(s, "Demo note", ["x: preprocessed spectrum, ŷ: predicted chicory %. Every correction is linear or per-spectrum, so each model collapses to ŷ = b₀ + wᵀx, the form the app runs."])
notes(s, "PLSR, used in all three models, finds weight vectors that maximise the covariance between the projected spectra and chicory, deflates, and repeats; "
         "the final regression vector is W(PᵀW)⁻¹q. EMSC models each arabica spectrum as a polynomial baseline plus a scaled mean spectrum plus the chicory "
         "direction, and removes everything except chemistry. The Savitzky–Golay first derivative is a fixed weighted sum of neighbouring bands whose "
         "weights add to zero, so any offset cancels; band selection keeps only the oil and C–H regions.")

# ================================================================== 23 why linear wins (copy of 'Why hyperspectral imaging?')
s = S[22]
set_text(s, "Title", ["Why linear models win, in every case"])
set_text(s, "Subtitle", ["In all three coffee bases the best linear model is 4–11 times more accurate than any nonlinear one"])
swap_image(s, "Image 0", FIG / "linear_vs_nonlinear.png")
set_text(s, "Chemistry heading", ["The physics is linear"])
set_text(s, "Chemistry list", ["Beer–Lambert", "Each compound adds its band in proportion to its amount",
                               "Blend = weighted sum", "A = (1−c)·A_coffee + c·A_chicory: a line in c",
                               "Corrections stay linear", "Offset, EMSC and SG1 keep that line",
                               "The rest is noise", "Day shifts and stirring, not a curve"], cycle=2)
set_text(s, "Why heading 1", ["Few levels, many bands"])
set_text(s, "Why text 1", ["11 levels and 33 dishes per base against 266 bands: flexible models memorise dishes, and a new session exposes it."])
set_text(s, "Why heading 2", ["Trees predict in steps"])
set_text(s, "Why text 2", ["A held-out session holds levels never trained on (5, 15 … 45 %); trees return training averages, a line interpolates."])
set_text(s, "Why heading 3", ["RBF kernels misread a new day"])
set_text(s, "Why text 3", ["A new session shifts every spectrum, so an RBF kernel finds no close neighbours: up to 17.5 % error on session 1."])
notes(s, "Why linear models win everywhere. Absorbance is linear in concentration, so a blend's spectrum is a weighted sum of its ingredients and chicory "
         "percent is a straight line in the spectrum. The corrections we apply are linear too. What remains is session shift and stirring noise, which "
         "nonlinear models cannot learn from 33 dishes. Trees can only output averages of training dishes, and RBF kernels lose their neighbours when a new "
         "day shifts the spectra.")

# ================================================================== 24 conclusions
s = S[23]
lv = N["linear_vs_nonlinear"]
set_text(s, "Text 3", ["Chicory is quantifiable in three coffee bases"])
set_text(s, "Text 4", ["0.79 % (robusta), 0.78 % (arabica) and 0.94 % (arabica + robusta) mean error per dish over 0–50 % chicory, on scanning sessions the models never saw."])
set_text(s, "Text 7", ["Each base needs its own correction, not its own model type"])
set_text(s, "Text 8", ["Offset removal for robusta, EMSC for arabica, a first derivative on the oil and C–H bands for the three-way blend; all three end in PLSR."])
set_text(s, "Text 11", ["Linear models win every time"])
set_text(s, "Text 12", ["The best linear model is 4–11 times more accurate than random forest, boosting or RBF-SVR in every base, as the Beer–Lambert law predicts."])
set_text(s, "Text 15", ["The choice is final"])
set_text(s, "Text 16", ["Fourteen preprocessings × five linear models per base (210 combinations): none is significantly better than the models chosen."])
notes(s, "Four conclusions: chicory is measurable in all three bases to under one percent; what differs between bases is the correction, not the model; "
         "linear beats nonlinear everywhere, for physical reasons; and an exhaustive check found nothing better.")

# ================================================================== 25 limitations and future scope
s = S[24]
set_text(s, "Text 4", [
    ["AR composition assumed. ", "The AR blends were read as coffee base + chicory at the label's second number; the arabica : robusta split is not measured."],
    ["Three sessions per base. ", "Each mean error rests on three held-out days, so it carries ±0.09 to ±0.46 % across sessions."],
    ["Sessions confounded with levels. ", "Within a base, no level appears in more than one sitting, so day and level effects cannot be fully separated."],
    ["0–50 % chicory only. ", "Above 50 % chicory can be flagged but not quantified; commercial packs have not been tested yet."]])
set_text(s, "Text 9", ["Confirm the AR blend recipes"])
set_text(s, "Text 10", ["The lab notes on how the AR blends were made settle the chicory assumption."])
set_text(s, "Text 13", ["Repeat levels across days"])
set_text(s, "Text 14", ["Two repeated levels per base break the session confound cheaply."])
set_text(s, "Text 17", ["Scan market coffee–chicory powders"])
set_text(s, "Text 18", ["Test the gate and the models on commercial packs with declared ratios."])
set_text(s, "Text 21", ["Add blends above 50 % chicory"])
set_text(s, "Text 22", ["Extends quantification across the full range, in all three bases."])
notes(s, "The main open point is the AR composition, which rests on the labels until the lab notes confirm it. The rest are about data, not models: "
         "more sessions, repeated levels, and commercial samples.")

prs.save(HERE / "endsem_coffee.pptx")
print("saved", len(prs.slides), "slides")
