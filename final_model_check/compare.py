"""Compare every preprocessing x model combination with each mixture's current model.

For each mixture: mean plate error over the held-out sessions, per-session errors, and a paired bootstrap
(dishes resampled within each held-out session, 2000 draws) of the difference to the current model.
A combination is called BETTER only if the 95 % interval of the difference lies below zero AND it beats the
current model in at least two of the three held-out sessions; WORSE if the interval lies above zero; else TIE.
Outputs: summary_<F>.csv, decision.json, 01_grid_all_mixtures.png."""
import os
import json, pickle
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, LogNorm

OUT = Path(os.environ.get("COFFEE_DATA", str(Path(__file__).resolve().parents[1]))) / "final_model_check"
NAMES = {"RBCH": "Robusta + chicory", "ABCH": "Arabica + chicory", "ARC": "Arabica + robusta + chicory"}
REF = {"RBCH": ("absorbance + offset", "PLSR"), "ABCH": ("absorbance + offset + EMSC", "PLSR"),
       "ARC": ("chemistry bands: absorbance + SG1", "PLSR")}
MODELS = ["PLSR", "PCR", "Ridge", "ElasticNet", "SVR (linear)"]
B = 2000

decision, tables = {}, {}
for F in REF:
    T = pd.read_csv(OUT / f"{F}_per_session.csv")
    dish = pickle.load(open(OUT / f"{F}_dish_predictions.pkl", "rb"))
    sess = sorted(T.held.unique())
    ref = REF[F]
    rng = np.random.default_rng(0)

    def boot(key):
        d = np.zeros(B)
        for s in sess:
            a = dish[(*ref, s)]; b = dish[(*key, s)].loc[a.index]
            ea, eb = ((a.p - a.y) ** 2).to_numpy(), ((b.p - b.y) ** 2).to_numpy()
            ii = rng.integers(0, len(ea), size=(B, len(ea)))
            d += (np.sqrt(eb[ii].mean(1)) - np.sqrt(ea[ii].mean(1))) / len(sess)
        return np.percentile(d, [2.5, 97.5])

    S = T.groupby(["prep", "model"]).agg(mean=("rmsep", "mean"), worst=("rmsep", "max"),
                                         max_bias=("bias", lambda v: v.abs().max())).reset_index()
    per = T.pivot_table(index=["prep", "model"], columns="held", values="rmsep").rename(columns=lambda s: f"S{s}")
    S = S.merge(per.reset_index(), on=["prep", "model"])
    scols = [f"S{s}" for s in sess]
    ref_s = S[(S.prep == ref[0]) & (S.model == ref[1])][scols].to_numpy().ravel()
    verd, ci, wins = [], [], []
    for _, r in S.iterrows():
        if (r.prep, r.model) == ref:
            verd.append("current model"); ci.append(""); wins.append(np.nan); continue
        w = int((r[scols].to_numpy(float) < ref_s - 1e-9).sum())
        lo, hi = boot((r.prep, r.model))
        verd.append("BETTER" if (hi < 0 and w >= 2) else "worse" if lo > 0 else "tie")
        ci.append(f"{lo:+.2f} to {hi:+.2f}"); wins.append(w)
    S["sessions_beating_current"], S["verdict"], S["diff_95ci"] = wins, verd, ci
    S = S.sort_values("mean").reset_index(drop=True)
    S.to_csv(OUT / f"summary_{F}.csv", index=False)
    tables[F] = S
    cur = S[S.verdict == "current model"].iloc[0]
    better = S[S.verdict == "BETTER"]
    decision[F] = dict(
        mixture=NAMES[F], current=f"{ref[0]} + {ref[1]}", current_mean=round(float(cur["mean"]), 3),
        current_rank=int(S.index[S.verdict == "current model"][0]) + 1, combinations=len(S),
        lowest=f"{S.iloc[0].prep} + {S.iloc[0].model}", lowest_mean=round(float(S.iloc[0]["mean"]), 3),
        lowest_verdict=S.iloc[0].verdict, lowest_ci=S.iloc[0].diff_95ci,
        n_better=int(len(better)), n_tie=int((S.verdict == "tie").sum()), n_worse=int((S.verdict == "worse").sum()),
        better=[dict(combo=f"{r.prep} + {r.model}", mean=round(float(r["mean"]), 3), ci=r.diff_95ci,
                     sessions=[round(float(r[c]), 2) for c in scols]) for _, r in better.iterrows()],
        reference_check=json.load(open(OUT / f"{F}_reference_check.json")))
    pd.set_option("display.width", 230)
    print(f"\n=== {NAMES[F]}: current = {ref[0]} + {ref[1]}, mean {cur['mean']:.2f} % "
          f"(rank {decision[F]['current_rank']} of {len(S)})")
    print(S.head(12)[["prep", "model", *scols, "mean", "verdict", "diff_95ci"]].round(2).to_string(index=False))
    print(f"better: {len(better)} | tie: {decision[F]['n_tie']} | worse: {decision[F]['n_worse']}")

json.dump(decision, open(OUT / "decision.json", "w"), indent=1)

# ---------------------------------------------------------------- figure: one heat map per mixture
SEQ = LinearSegmentedColormap.from_list("seq", ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"])
fig, axs = plt.subplots(1, 3, figsize=(20, 7.4), facecolor="#fcfcfb")
for ax, F in zip(axs, REF):
    S = tables[F]
    order = S.groupby("prep")["mean"].min().sort_values().index.tolist()
    M = S.pivot(index="prep", columns="model", values="mean").loc[order, MODELS]
    V = S.set_index(["prep", "model"]).verdict
    lo_, hi_ = max(M.min().min(), .3), M.max().max()
    im = ax.imshow(M.to_numpy(), cmap=SEQ, norm=LogNorm(vmin=lo_, vmax=hi_), aspect="auto")
    for i, pn in enumerate(order):
        for j, mn in enumerate(MODELS):
            v = M.iat[i, j]; dark = np.log(v / lo_) > .55 * np.log(hi_ / lo_)
            mark = " ★" if V[(pn, mn)] == "BETTER" else ""
            ax.text(j, i, f"{v:.2f}{mark}", ha="center", va="center", fontsize=8.6, color="white" if dark else "#0b0b0b")
    r0, c0 = order.index(REF[F][0]), MODELS.index(REF[F][1])
    ax.add_patch(plt.Rectangle((c0 - .5, r0 - .5), 1, 1, fill=False, ec="#0b0b0b", lw=2.4))
    ax.set_xticks(range(len(MODELS)), MODELS, rotation=20, ha="right"); ax.set_yticks(range(len(order)), order, fontsize=9)
    ax.tick_params(length=0)
    for s_ in ax.spines.values(): s_.set_visible(False)
    d = decision[F]
    ax.set_title(f"{NAMES[F]}\ncurrent (box) {d['current_mean']:.2f} %, rank {d['current_rank']}/{d['combinations']}; "
                 f"significantly better: {d['n_better']}", loc="left", fontsize=10.5)
    cb = fig.colorbar(im, ax=ax, fraction=.04, pad=.02); cb.outline.set_visible(False)
fig.suptitle("Mean chicory error per dish on unseen sessions (%), every preprocessing x linear model. "
             "★ = significantly better than the current model (95 % bootstrap interval below 0 and better in ≥2 sessions)",
             x=.01, ha="left", fontsize=11.5)
plt.tight_layout(); plt.savefig(OUT / "01_grid_all_mixtures.png", dpi=150, bbox_inches="tight")
print("\nsaved", OUT / "01_grid_all_mixtures.png")
