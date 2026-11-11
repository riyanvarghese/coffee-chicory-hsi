"""Re-test the 8 preprocessing options under the final model's nested leave-one-session-out.

Usage (from this folder):  python preprocessing_check_nested_loso.py
Reads the code of ../03_final_model/robusta_chicory_nested_loso.ipynb (setup, data and building
blocks are executed from the notebook in the project folder), swaps only the preprocessing, and
for each option runs PLSR with the same trimming, super-patches and inner tuning per round.
Writes prep_folds.csv (one row per option and held-out session) and prints the mean errors and a
paired bootstrap of each option against absorbance + offset.  Read-only on the project data.
"""
import os
from pathlib import Path
os.environ.setdefault("COFFEE_DATA", str(Path(__file__).resolve().parents[2]))  # lets notebook cells run from any folder
import json, numpy as np, pandas as pd
from scipy.signal import savgol_filter
nb = json.load(open(os.path.join(os.environ.get("COFFEE_DATA", str(Path(__file__).resolve().parents[2])), "robusta_chicory_nested_loso.ipynb")))
code = lambda i: "".join(nb["cells"][i]["source"])
ns = {}
exec(code(2).replace('OUT.mkdir(exist_ok=True, parents=True)', ''), ns)   # setup (no writes)
exec(code(4), ns)                                                          # data -> DATA, COLS, SESSION, GROUP, Y
exec(code(6), ns)                                                          # units(), tune(), make(), plate_rmse()
DATA, COLS, SESSION, Y = ns["DATA"], ns["COLS"], ns["SESSION"], ns["Y"]
R = np.clip(DATA[COLS].values.astype(float), 1e-3, None)

def snv(A): return (A - A.mean(-1, keepdims=True)) / (A.std(-1, keepdims=True) + 1e-12)
def msc(A, ref):
    M = np.column_stack([ref, np.ones_like(ref)]); c = np.linalg.pinv(M) @ A.T
    return (A - c[1][:, None]) / np.where(np.abs(c[0]) > 1e-9, c[0], 1e-9)[:, None]
sg = lambda A, d: savgol_filter(A, 15, 2, deriv=d, axis=1)
absb = lambda A: np.log10(1.0 / A)
off = lambda A: A - A.mean(-1, keepdims=True)
PREP = {"absorbance + offset (current)": lambda A, tr: off(absb(A)),
        "absorbance": lambda A, tr: absb(A),
        "raw reflectance": lambda A, tr: A,
        "SNV": lambda A, tr: snv(A),
        "MSC": lambda A, tr: msc(A, A[tr].mean(0)),          # reference from training sessions only
        "absorbance + SG1": lambda A, tr: sg(absb(A), 1),
        "SG1": lambda A, tr: sg(A, 1),
        "SG2": lambda A, tr: sg(A, 2)}

rows, plates = [], {}
for name, f in PREP.items():
    for held in (1, 2, 3):
        train = [s for s in (1, 2, 3) if s != held]
        ns["Z"] = f(R, np.isin(SESSION, train)); ns["_UNITS"].clear()
        ZU, UM = ns["units"](train)
        us, y, g = UM.session.to_numpy(), UM.chicory_pct.to_numpy(float), UM.group.to_numpy()
        tr, te = np.isin(us, train), us == held
        lv, _ = ns["tune"]("PLSR", ZU[tr], y[tr], g[tr])
        p = ns["predict"](ns["make"]("PLSR", lv).fit(ZU[tr], y[tr]), ZU[te])
        pl = pd.DataFrame(dict(g=g[te], y=y[te], p=p)).groupby("g")[["y", "p"]].mean()
        plates[(name, held)] = pl
        rows.append(dict(prep=name, held=held, lv=lv, rmsep=float(np.sqrt(((pl.p - pl.y) ** 2).mean())),
                         bias=float((pl.p - pl.y).mean())))
    print("done", name, flush=True)
T = pd.DataFrame(rows)
T.to_csv("prep_folds.csv", index=False)
S = T.groupby("prep").agg(mean=("rmsep", "mean"), worst=("rmsep", "max"),
                          max_bias=("bias", lambda v: v.abs().max())).sort_values("mean")
piv = T.pivot(index="prep", columns="held", values="rmsep").rename(columns=lambda s: f"S{s}")
lvs = T.pivot(index="prep", columns="held", values="lv").astype(int).astype(str).agg("/".join, axis=1).rename("LV per round")
out = S.join(piv).join(lvs).loc[S.index]
print(out.round(2).to_string())

# paired bootstrap of mean RMSEP: each alternative vs the current choice (plates resampled within each session)
rng = np.random.default_rng(0); B = 2000; cur = "absorbance + offset (current)"
def boot(name):
    d = np.zeros(B)
    for s in (1, 2, 3):
        a, b = plates[(cur, s)], plates[(name, s)].loc[plates[(cur, s)].index]
        ea, eb = ((a.p - a.y) ** 2).to_numpy(), ((b.p - b.y) ** 2).to_numpy()
        ii = rng.integers(0, len(ea), size=(B, len(ea)))
        d += (np.sqrt(eb[ii].mean(1)) - np.sqrt(ea[ii].mean(1))) / 3
    return np.percentile(d, [2.5, 97.5])
print("\nalternative minus current, 95 % CI of the mean-error difference:")
for nm in S.index:
    if nm != cur:
        lo, hi = boot(nm); print(f"  {nm:22s} {S.loc[nm,'mean']-S.loc[cur,'mean']:+.2f}  [{lo:+.2f}, {hi:+.2f}]  -> {'tie' if lo < 0 < hi else ('worse' if lo > 0 else 'better')}")
