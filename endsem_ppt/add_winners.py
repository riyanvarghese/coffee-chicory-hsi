"""Turn the 25-slide endsem deck into one with a dedicated winner + maths slide per mixture.
Robusta recap (slide 14) becomes the robusta winner slide; copies of it go after the arabica and the three-way
'choosing the method' slides; the combined maths slide is dropped (its content now lives on the three winner slides)."""
import os
import copy, json, re, shutil, subprocess, sys, zipfile
from pathlib import Path
os.environ.setdefault("COFFEE_DATA", str(Path(__file__).resolve().parents[1]))
from pptx import Presentation
from pptx.util import Inches, Pt

HERE = Path(__file__).parent
SK = Path(os.environ.get("PPTX_SKILL", "/home/riyanvarghese/.claude/skills/synced/589b1784-c188-4996-82fc-5a3c3caf1b58_f24f2714-0d33-4140-a951-c9bcc584ed1f/pptx"))
SRC, UN, MID, OUT = HERE / "endsem_coffee.pptx", HERE / "un2", HERE / "struct2.pptx", HERE / "endsem_coffee_v2.pptx"
N = json.load(open(HERE / "numbers.json"))

# ------------------------------------------------------------------ structure
shutil.rmtree(UN, ignore_errors=True); zipfile.ZipFile(SRC).extractall(UN)
pres, rels = UN / "ppt/presentation.xml", UN / "ppt/_rels/presentation.xml.rels"
def order():
    rx = rels.read_text()
    rid2file = {}
    for m in re.finditer(r"<Relationship [^>]*>", rx):
        tag = m.group(0); rid = re.search(r'Id="(rId\d+)"', tag).group(1); tg = re.search(r'Target="([^"]+)"', tag).group(1)
        if tg.startswith("slides/"): rid2file[rid] = tg.split("/")[-1]
    x = pres.read_text(); lst = re.search(r"<p:sldIdLst>(.*?)</p:sldIdLst>", x, re.S)
    items = re.findall(r"<p:sldId [^>]*/>", lst.group(1))
    return x, lst, items, [rid2file[re.search(r'r:id="(rId\d+)"', it).group(1)] for it in items]
_, _, _, files = order()
rb_file, maths_file = files[13], files[21]
for _ in range(2):
    out = subprocess.run([sys.executable, str(SK / "scripts/add_slide.py"), str(UN), rb_file], capture_output=True, text=True, check=True).stdout
    print(out.strip().splitlines()[0])
x, lst, items, files = order()
new_files = files[-2:]                             # the two copies, appended at the end
byfile = dict(zip(files, items))
base = [f for f in files[:25] if f != maths_file]  # 24 slides
base.insert(base.index(files[14]) + 1, new_files[0])       # after arabica 'choosing the method'
base.insert(base.index(files[17]) + 1, new_files[1])       # after three-way 'choosing the method'
x = x[:lst.start(1)] + "".join(byfile[f] for f in base) + x[lst.end(1):]
pres.write_text(x)
subprocess.run([sys.executable, str(SK / "scripts/clean.py"), str(UN)], check=True, capture_output=True)
MID.unlink(missing_ok=True)
subprocess.run(["zip", "-qXrD", str(MID), "."], cwd=UN, check=True)

# ------------------------------------------------------------------ content
sys.path.insert(0, str(HERE))
prs = Presentation(MID)
S = prs.slides
print(len(S), "slides")
exec(open(HERE / "deck_helpers.py").read())        # set_text, shp, notes, set_cell ... (shared with build_deck.py)

def winner(s, mix, title, subtitle, pill, name, name_pt, desc, stat, ranking, heading, steps, eq_key, note):
    set_text(s, "Title", [title]); set_text(s, "Subtitle", [subtitle])
    set_text(s, "Winner pill", [pill]); set_text(s, "Winner name", [name])
    shp(s, "Winner pill").width = Inches(3.35)
    if name_pt:
        for p in shp(s, "Winner name").text_frame.paragraphs:
            for r in p.runs: r.font.size = Pt(name_pt)
    set_text(s, "Winner desc", [desc]); set_text(s, "Winner stat", [stat])
    set_text(s, "Ranking label", [ranking[0]])
    for i, (nm, v) in enumerate(ranking[1], 1):
        set_text(s, f"Rank name {i}", [nm]); set_text(s, f"Rank value {i}", [f"{v:.2f}"])
        shp(s, f"Rank bar {i}").width = Inches(max(.06, min(1.45, v * 0.179)))
    set_text(s, "Reasons heading", [heading])
    for i, (ttl, txt) in enumerate(steps, 1):
        set_text(s, f"Reason {i} title", [ttl]); set_text(s, f"Reason {i} text", [txt])
        for nm in (f"Reason {i} title", f"Reason {i} text"): shp(s, nm).width = Inches(3.55)
        card = shp(s, f"Reason {i} card")
        pic = s.shapes.add_picture(str(HERE / "figs/steps" / f"{eq_key}_{i}.png"), Inches(9.88), card.top + Inches(.12),
                                   width=Inches(2.75), height=Inches(.86))
        pic.name = f"Step {i} equation"
    notes(s, note)

ab, ac = N["ab_cmp"], N["arc_cmp"]
top = lambda d, k=8: sorted(d.items(), key=lambda kv: kv[1][3])[:k]
NICE = {"chemistry bands, derivative + PLSR": "Chem. SG1 + PLSR", "first derivative + PLSR": "SG1 + PLSR"}

winner(S[13], "RB", "Robusta + chicory winner: PLSR", "Lowest error on unseen sessions; on the right, the four steps that turn a spectrum into a chicory %",
       "WINNER · ROBUSTA + CHICORY", "PLSR", None, "Absorbance + offset, then PLSR · 6 latent variables", "0.79 %",
       ("RANKING · MEAN ERROR %", [("PLSR", .79), ("SVR (linear)", .83), ("PCR", .85), ("Ridge", .89), ("ElasticNet", .89),
                                   ("Random Forest", 3.76), ("Gradient Boosting", 4.12), ("SVR (RBF)", 8.09)]),
       "How it works",
       [("Absorbance, then offset removal", "Log makes absorbance proportional to content; subtracting each spectrum's mean cancels the day-to-day brightness factor."),
        ("Latent variables", "Each weight vector w maximises the covariance between the projected spectra and chicory %; X is then deflated and the next found."),
        ("Regression on the scores", "Chicory % is fitted on the 6 scores t, then folded back into one weight per band, b."),
        ("Prediction", "Every super-patch gets ŷ and the dish mean is reported; 6, 7 and 6 latent variables were chosen in the three rounds.")],
       "rb",
       "The robusta winner, now with how it works. Absorbance plus offset removal cancels the session brightness. PLSR then builds latent variables, "
       "the band combinations that covary most with chicory, fits chicory on those scores, and folds everything back into one weight per band.")

winner(S[15], "AB", "Arabica + chicory winner: EMSC + PLSR", "Lowest error on unseen sessions; on the right, how EMSC cleans each spectrum before PLSR",
       "WINNER · ARABICA + CHICORY", "EMSC + PLSR", 40, "EMSC correction, then PLSR · 4 latent variables", "0.78 %",
       ("RANKING · MEAN ERROR % (TOP 8 OF 9)", [(NICE.get(m, m), v[3]) for m, v in top(ab)]),
       "How it works",
       [("Model each spectrum", "Baseline, tilt and curvature, a scaled mean spectrum, and the chicory direction k learnt from the training sessions, fitted by least squares."),
        ("Correct it", "Remove the baseline terms and divide by the scale bᵢ: packing and brightness vanish, while the chicory term hᵢ·k stays."),
        ("PLSR on the corrected spectra", "Same latent-variable regression as robusta, now on spectra freed of arabica's day-to-day scatter."),
        ("Prediction", "4 latent variables in the final model (3, 5 and 4 in the three rounds); dish mean of the super-patches.")],
       "ab",
       "Why EMSC matters for arabica: plain PLSR read pure arabica 4 points low on a new day, because arabica's scatter changes between sessions. "
       "EMSC writes each spectrum as a baseline plus a scaled mean spectrum plus the chicory direction, solves for those terms, and removes all but the chemistry. "
       "PLSR on the corrected spectra then gives 0.78 percent.")

winner(S[19], "ARC", "Three-way blend winner: SG1 + PLSR", "Arabica + robusta + chicory: lowest error on unseen sessions; on the right, the derivative and band selection before PLSR",
       "WINNER · ARABICA + ROBUSTA + CHICORY", "SG1 + PLSR", 40, "SG1 on chemistry bands + PLSR · 5 latent variables", "0.94 %",
       ("RANKING · MEAN ERROR % (TOP 8 OF 11)", [(NICE.get(m, m), v[3]) for m, v in top(ac)]),
       "How it works",
       [("Absorbance", "Log of 1/R, as for the other bases; no offset step is needed because the derivative removes offsets."),
        ("Savitzky–Golay first derivative", "Slope of a quadratic fitted over 15 bands (about 80 nm): offsets between bases cancel and overlapping bands sharpen."),
        ("Keep the chemistry bands", "Only 1650–1800 nm (C–H first overtone, oil) and 2150–2400 nm (C–H combination, oil): 73 of 266 bands."),
        ("PLSR and prediction", "5 latent variables; every step is linear, so the model folds into one weight vector on the 266-band spectrum.")],
       "arc",
       "For the three-way blend the coffee base itself varies, which shifts the baseline from dish to dish. The first derivative removes that shift, "
       "and keeping only the oil and C–H bands focuses the model on what chicory lacks. PLSR on those 73 derivative bands gives 0.94 percent.")

prs.save(OUT)
print("saved", OUT, len(prs.slides), "slides")
