"""Final model check: the same preprocessing x model grid for all three mixtures, under the same nested
leave-one-session-out test that produced the current numbers.

    python run.py RBCH|ABCH|ARC        one mixture -> <F>_per_session.csv, <F>_dish_predictions.pkl
    python compare.py                  bootstrap verdicts against each current model, summary + figure

Data, trimming, super-patches, inner tuning (leave-one-concentration-out, one-standard-error rule) and the
plate-level error are executed straight from the notebooks behind the current models, so the reference
rows must reproduce their published per-session errors (checked at the end of each run)."""
import os
import json, pickle, sys, time
from pathlib import Path
os.environ.setdefault("COFFEE_DATA", str(Path(__file__).resolve().parents[1]))  # lets notebook cells run from any folder
import numpy as np
import pandas as pd
from scipy.signal import savgol_filter

BASE = Path(os.environ.get("COFFEE_DATA", str(Path(__file__).resolve().parents[1])))
OUT = BASE / "final_model_check"
F = sys.argv[1]
cell = lambda nb, i: "".join(nb["cells"][i]["source"])

# ---------------------------------------------------------------- data + building blocks, from the source notebooks
import matplotlib; matplotlib.use("Agg")
ns = {}
if F in ("RBCH", "ABCH"):
    nb = json.loads((BASE / ("robusta_chicory_nested_loso.ipynb" if F == "RBCH" else "arabica_chicory_nested_loso.ipynb")).read_text())
    for i in (2, 4, 6):
        exec(cell(nb, i), ns)
else:   # arabica + robusta + chicory: the AR series, 13:30 AR 50:50 excluded, label's second number = chicory %
    nb = json.loads((BASE / "arabica_robusta_models_and_classifier.ipynb").read_text())
    setup = cell(nb, 2).replace('DATA = AR[AR.role == "calibration"].reset_index(drop=True)',
                                'DATA = AR[(AR.role == "calibration") & ~((AR.day == 2) & (AR.label == "AR[50:50]"))].reset_index(drop=True)')
    assert setup != cell(nb, 2)
    exec(setup, ns)
DATA, COLS, WL, SESSION = ns["DATA"], ns["COLS"], ns["WL"], ns["SESSION"]
R = np.clip(DATA[COLS].values.astype(float), 1e-3, None)
SESSIONS = sorted(int(s) for s in np.unique(SESSION))
print(f"{F}: {len(DATA)} patches, {DATA.group.nunique()} dishes, sessions {SESSIONS}, {len(WL)} bands", flush=True)

# ---------------------------------------------------------------- preprocessings
CHEM = ((WL >= 1650) & (WL <= 1800)) | ((WL >= 2150) & (WL <= 2400))
def snv(A): return (A - A.mean(-1, keepdims=True)) / (A.std(-1, keepdims=True) + 1e-12)
def msc(A, ref):
    M = np.column_stack([ref, np.ones_like(ref)]); c = np.linalg.pinv(M) @ A.T
    return (A - c[1][:, None]) / np.where(np.abs(c[0]) > 1e-9, c[0], 1e-9)[:, None]
sg = lambda A, d: savgol_filter(A, 15, 2, deriv=d, axis=1)
absb = lambda A: np.log10(1.0 / A)
off = lambda A: A - A.mean(-1, keepdims=True)

# name -> (patch-level transform, EMSC after super-patching?, wavelengths kept)
PREP = {
    "absorbance + offset":                   (lambda A, tr: off(absb(A)), False, None),
    "absorbance + offset + EMSC":            (lambda A, tr: off(absb(A)), True, None),
    "absorbance":                            (lambda A, tr: absb(A), False, None),
    "raw reflectance":                       (lambda A, tr: A, False, None),
    "SNV":                                   (lambda A, tr: snv(A), False, None),
    "MSC":                                   (lambda A, tr: msc(A, A[tr].mean(0)), False, None),
    "absorbance + SNV + SG1":                (lambda A, tr: sg(snv(absb(A)), 1), False, None),
    "absorbance + SG1":                      (lambda A, tr: sg(absb(A), 1), False, None),
    "SG1":                                   (lambda A, tr: sg(A, 1), False, None),
    "SG2":                                   (lambda A, tr: sg(A, 2), False, None),
    "chemistry bands: absorbance + offset":  (lambda A, tr: off(absb(A))[:, CHEM], False, CHEM),
    "chemistry bands: absorbance + SG1":     (lambda A, tr: sg(absb(A), 1)[:, CHEM], False, CHEM),
    "chemistry bands: absorbance + SG2":     (lambda A, tr: sg(absb(A), 2)[:, CHEM], False, CHEM),
    "chemistry bands: EMSC":                 (lambda A, tr: off(absb(A))[:, CHEM], True, CHEM),
}
MODELS = ["PLSR", "PCR", "Ridge", "ElasticNet", "SVR (linear)"]

def emsc(ZU, tr, y, wl):
    lam = (wl - wl.min()) / (wl.max() - wl.min()) * 2 - 1
    m = ZU[tr].mean(0); yc = y[tr] - y[tr].mean(); k = yc @ (ZU[tr] - m) / (yc @ yc)
    B = np.column_stack([np.ones_like(lam), m, k, lam, lam ** 2])
    a, b, h, d, e = np.linalg.lstsq(B, ZU.T, rcond=None)[0]
    return (ZU - a[:, None] - np.outer(d, lam) - np.outer(e, lam ** 2)) / b[:, None]

# ---------------------------------------------------------------- nested leave-one-session-out over the whole grid
REF = {"RBCH": ("absorbance + offset", "PLSR"), "ABCH": ("absorbance + offset + EMSC", "PLSR"),
       "ARC": ("chemistry bands: absorbance + SG1", "PLSR")}[F]
ORDER = [REF[0]] + [k for k in PREP if k != REF[0]]          # the current model's preprocessing first: early sanity check
rows, dish, t0 = [], {}, time.time()
for pname in ORDER:
    f, use_emsc, keep = PREP[pname]
    wl = WL if keep is None else WL[keep]
    for held in SESSIONS:
        train = [s for s in SESSIONS if s != held]
        ns["Z"] = f(R, np.isin(SESSION, train)); ns["_UNITS"].clear()
        ZU, UM = ns["units"](train)
        us, y, g = UM.session.to_numpy(), UM.chicory_pct.to_numpy(float), UM.group.to_numpy()
        tr, te = np.isin(us, train), us == held
        if use_emsc:
            ZU = emsc(ZU, tr, y, wl)
        for m in MODELS:
            prm, _ = ns["tune"](m, ZU[tr], y[tr], g[tr])
            p = ns["predict"](ns["make"](m, prm).fit(ZU[tr], y[tr]), ZU[te])
            pl = pd.DataFrame(dict(g=g[te], y=y[te], p=p)).groupby("g")[["y", "p"]].mean()
            dish[(pname, m, held)] = pl
            rows.append(dict(prep=pname, model=m, held=held, param=prm,
                             rmsep=float(np.sqrt(((pl.p - pl.y) ** 2).mean())), bias=float((pl.p - pl.y).mean())))
    pd.DataFrame(rows).to_csv(OUT / f"{F}_per_session.csv", index=False)      # checkpoint after every preprocessing
    pickle.dump(dish, open(OUT / f"{F}_dish_predictions.pkl", "wb"))
    print(f"  {pname:40s} done  ({(time.time() - t0) / 60:.1f} min)", flush=True)
    if pname == REF[0]:
        print("    current model, per held-out session:",
              [round(r["rmsep"], 2) for r in rows if r["prep"] == REF[0] and r["model"] == REF[1]], flush=True)

# ---------------------------------------------------------------- reproduce the current model's published per-session errors
T = pd.DataFrame(rows)
mine = T[(T.prep == REF[0]) & (T.model == REF[1])].sort_values("held").rmsep.round(2).tolist()
if F == "RBCH":
    o = pd.read_csv(BASE / "final_regression" / "outer_folds_all_methods.csv")
    pub = o[o.model == "PLSR"].sort_values("held_out").rmsep_plate.round(2).tolist()
elif F == "ABCH":
    a = pd.read_csv(BASE / "arabica_preprocessing" / "all_combinations_per_session.csv")
    pub = a[(a.prep == "absorbance + offset + EMSC") & (a.model == "PLSR")].sort_values("held").rmsep.round(2).tolist()
else:
    s_ = pd.read_csv(BASE / "arabica_robusta_models_excl_1330_5050" / "model_summary.csv").set_index("model")
    pub = s_.loc["chemistry bands, derivative + PLSR", ["S1 held out", "S2 held out", "S3 held out"]].round(2).tolist()
print(f"reference check {REF}: this run {mine} | published {pub} | {'MATCH' if mine == pub else 'DIFFERENT'}", flush=True)
json.dump(dict(family=F, ref=REF, this_run=mine, published=pub, match=mine == pub, minutes=(time.time() - t0) / 60),
          open(OUT / f"{F}_reference_check.json", "w"), indent=1)
