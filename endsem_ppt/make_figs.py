"""Figures and numbers for the end-semester deck, in the midsem figures' style and pixel sizes.
Reads the saved held-out results only (no re-training)."""
import os
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, LogNorm

BASE = Path(os.environ.get("COFFEE_DATA", str(Path(__file__).resolve().parents[1])))
OUT = Path(__file__).parent / "figs"; OUT.mkdir(exist_ok=True)
INK, INK2, MUTED, GRID, AXIS = "#0b0b0b", "#52514e", "#898781", "#e8e2d8", "#c3c2b7"
S_COLOR = {1: "#2a78d6", 2: "#eb6834", 3: "#1baf7a"}
S_MARK = {1: "o", 2: "s", 3: "^"}
BAR, BAR_DARK = "#d6cdbf", "#5b3a26"
plt.rcParams.update({
    "font.size": 15, "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "axes.titlecolor": INK, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2, "axes.grid": True, "grid.color": GRID, "grid.linewidth": .9,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False, "axes.titlesize": 17,
    "axes.titlelocation": "left",
})
def save(fig, name, px):
    fig.set_size_inches(px[0] / 100, px[1] / 100)
    fig.savefig(OUT / name, dpi=100)
    plt.close(fig)

NUM = {}

# ------------------------------------------------------------------ inputs
ab_cmp = pd.read_csv(BASE / "arabica_regression/outer_folds_all_methods.csv").pivot(index="model", columns="held_out", values="rmsep_plate")
ab_adv = pd.read_csv(BASE / "arabica_advanced_models/per_session.csv")
em = ab_adv[ab_adv.model == "EMSC + PLSR"].set_index("held_out").rmsep
ab_cmp.loc["EMSC + PLSR"] = [em[1], em[2], em[3]]
ab_cmp["mean"] = ab_cmp[[1, 2, 3]].mean(axis=1)
ab_cmp = ab_cmp.sort_values("mean")
arc_sum = pd.read_csv(BASE / "arabica_robusta_models_excl_1330_5050/model_summary.csv").set_index("model")
arc_cmp = arc_sum.rename(columns={"S1 held out": 1, "S2 held out": 2, "S3 held out": 3})[[1, 2, 3, "mean"]].sort_values("mean")
ARC_BEST = "chemistry bands, derivative + PLSR"
NICE = {ARC_BEST: "Chem. SG1 + PLSR", "first derivative + PLSR": "SG1 + PLSR", "EMSC + PLSR": "EMSC + PLSR"}

ab_pred = pd.read_csv(BASE / "arabica_advanced_models/heldout_predictions_all_models.csv")
ab_pred = ab_pred[ab_pred.model == "EMSC + PLSR"].rename(columns={"fold": "held"})
arc_pred = pd.read_csv(BASE / "arabica_robusta_models_excl_1330_5050/heldout_predictions.csv")
arc_pred = arc_pred[arc_pred.model == ARC_BEST].rename(columns={"fold": "held"})

# ------------------------------------------------------------------ figure: method comparison (midsem image15, 1641 x 454)
def comparison(C, winner, fname, nice=lambda s: s):
    fig, ax = plt.subplots()
    rows = list(C.index)[::-1]
    for i, m in enumerate(rows):
        v = C.loc[m, [1, 2, 3]].to_numpy(float)
        ax.plot([v.min(), v.max()], [i, i], color=BAR, lw=7, solid_capstyle="round", zorder=1)
        for s in (1, 2, 3):
            ax.scatter(v[s - 1], i, color=S_COLOR[s], marker=S_MARK[s], s=46, zorder=3, edgecolor="white", lw=.6)
        mu = C.loc[m, "mean"]
        ax.plot([mu, mu], [i - .3, i + .3], color=BAR_DARK if m == winner else "#7d7a73", lw=3.2, zorder=4)
        ax.text(v.max() * 1.12, i, f"{mu:.2f}", va="center", fontsize=14, fontweight="bold" if m == winner else "normal",
                color=INK if m == winner else INK2)
    ax.set_xscale("log"); ax.set_yticks(range(len(rows)), [nice(m) for m in rows])
    for lab in ax.get_yticklabels():
        if lab.get_text() == nice(winner): lab.set_fontweight("bold"); lab.set_color(INK)
    ax.set_xticks([.3, .5, 1, 2, 5, 10, 20], ["0.3", "0.5", "1", "2", "5", "10", "20"])
    ax.set_xlim(.25, 40); ax.grid(axis="y", visible=False)
    ax.set_xlabel("error per dish on the held-out session (% chicory, log scale)")
    h = [plt.Line2D([], [], color=S_COLOR[s], marker=S_MARK[s], ls="", ms=8, label=f"session {s} held out") for s in (1, 2, 3)]
    h.append(plt.Line2D([], [], color="#7d7a73", marker="|", ls="", ms=14, mew=3, label="mean of the three (value at right)"))
    ax.legend(handles=h, loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=13)
    fig.subplots_adjust(left=.17, right=.7, top=.97, bottom=.17)
    save(fig, fname, (1641, 454))

comparison(ab_cmp, "EMSC + PLSR", "ab_compare.png")
comparison(arc_cmp, ARC_BEST, "arc_compare.png", nice=lambda s: NICE.get(s, s))

# ------------------------------------------------------------------ figure: fit on unseen sessions (midsem image17, 2613 x 688)
def per_dish(P):
    return P.groupby(["held", "group", "label"], as_index=False).agg(y=("y", "first"), p=("p", "mean"))

def fit(P, fname, key):
    D = per_dish(P)
    err = D.groupby("held").apply(lambda g: float(np.sqrt(((g.p - g.y) ** 2).mean())), include_groups=False)
    bias = D.groupby("held").apply(lambda g: float((g.p - g.y).mean()), include_groups=False)
    pooled = float(np.sqrt(((D.p - D.y) ** 2).mean()))
    r2 = 1 - ((D.p - D.y) ** 2).sum() / ((D.y - D.y.mean()) ** 2).sum()
    rpd = float(D.y.std(ddof=1) / pooled)
    fig, axs = plt.subplots(1, 3, gridspec_kw=dict(width_ratios=[1.35, 1, 1]))
    ax = axs[0]
    for s in (1, 2, 3):
        p_ = P[P.held == s]; d_ = D[D.held == s]
        ax.scatter(p_.y + np.random.default_rng(s).normal(0, .25, len(p_)), p_.p, s=9, alpha=.25, color=S_COLOR[s], lw=0)
        g = d_.groupby("y").p.agg(["mean", "min", "max"]).reset_index()
        ax.errorbar(g.y, g["mean"], yerr=[g["mean"] - g["min"], g["max"] - g["mean"]], fmt=S_MARK[s], color=S_COLOR[s],
                    ms=8, capsize=3, lw=1.4, label=f"session {s} held out — {err[s]:.2f} %")
    ax.plot([-3, 53], [-3, 53], ls="--", color=INK, lw=1.3); ax.set_xlim(-3, 53); ax.set_ylim(-5, 56)
    ax.set_xlabel("true chicory (%)"); ax.set_ylabel("predicted chicory (%)")
    ax.set_title("Each session predicted by a model that never saw it"); ax.legend(loc="upper left", fontsize=13)
    ax = axs[1]
    b = ax.bar([1, 2, 3], [err[s] for s in (1, 2, 3)], color=[S_COLOR[s] for s in (1, 2, 3)], width=.6)
    for s in (1, 2, 3): ax.text(s, err[s] + .03, f"{err[s]:.2f}", ha="center", va="bottom", fontsize=14)
    m = float(np.mean(err)); ax.axhline(m, ls="--", color=INK, lw=1.4); ax.text(.62, m + .03, f"mean {m:.2f} %", fontsize=14)
    ax.set_xticks([1, 2, 3], ["session 1", "session 2", "session 3"]); ax.set_ylim(0, max(err) * 1.25)
    ax.set_ylabel("error per dish (% chicory)"); ax.set_title("Error on each held-out session"); ax.grid(axis="x", visible=False)
    ax = axs[2]
    ax.bar([1, 2, 3], [bias[s] for s in (1, 2, 3)], color=[S_COLOR[s] for s in (1, 2, 3)], width=.6)
    lim = max(abs(bias)) * 1.45
    for s in (1, 2, 3):
        ax.text(s, bias[s] + (.04 * lim if bias[s] >= 0 else -.04 * lim), f"{bias[s]:+.2f}".replace("-", "−"), ha="center",
                va="bottom" if bias[s] >= 0 else "top", fontsize=14)
    ax.axhline(0, color=INK, lw=1.2); ax.set_ylim(-lim, lim)
    ax.set_xticks([1, 2, 3], ["session 1", "session 2", "session 3"]); ax.set_ylabel("mean bias (% chicory)")
    ax.set_title("Systematic offset per session"); ax.grid(axis="x", visible=False)
    fig.subplots_adjust(left=.045, right=.99, top=.9, bottom=.14, wspace=.28)
    save(fig, fname, (2613, 688))
    NUM[key] = dict(err={int(s): round(float(err[s]), 2) for s in (1, 2, 3)}, mean=round(m, 2), sd=round(float(np.std(err.values, ddof=1)), 2),
                    pooled=round(pooled, 2), r2=round(float(r2), 3), rpd=round(rpd, 1),
                    bias={int(s): round(float(bias[s]), 2) for s in (1, 2, 3)}, max_bias=round(float(abs(bias).max()), 2))
    return D

Dab = fit(ab_pred, "ab_fit.png", "ABCH")
Darc = fit(arc_pred, "arc_fit.png", "ARC")

# ------------------------------------------------------------------ figure: every blend predicted blind (midsem image18, 1404 x 730)
def blind(D, fname, key):
    B = D.groupby(["label", "held"], as_index=False).agg(y=("y", "first"), p=("p", "mean")).sort_values("y")
    B["e"] = B.p - B.y
    fig, ax = plt.subplots()
    x = np.arange(len(B))
    ax.bar(x, B.e, color=[S_COLOR[s] for s in B.held], width=.62)
    lim = max(abs(B.e)) * 1.3
    for i, e in zip(x, B.e):
        ax.text(i, e + (.03 * lim if e >= 0 else -.03 * lim), f"{e:+.2f}".replace("-", "−"), ha="center", va="bottom" if e >= 0 else "top", fontsize=12, color=INK2)
    ax.axhline(0, color=INK, lw=1.2); ax.set_ylim(-lim, lim)
    ax.set_xticks(x, [f"{y:.0f}" for y in B.y]); ax.set_xlabel("chicory in the blend (%)"); ax.set_ylabel("predicted − true (% chicory)")
    ax.grid(axis="x", visible=False)
    h = [plt.Rectangle((0, 0), 1, 1, color=S_COLOR[s], label=f"session {s} held out") for s in (1, 2, 3)]
    ax.legend(handles=h, ncol=3, loc="lower left", bbox_to_anchor=(0, 1.0), fontsize=13)
    fig.subplots_adjust(left=.09, right=.99, top=.9, bottom=.13)
    save(fig, fname, (1404, 730))
    slopes = {}
    for s in (1, 2, 3):
        d = D[D.held == s]
        if d.y.nunique() > 1: slopes[int(s)] = round(float(np.polyfit(d.y, d.p, 1)[0]), 3)
    worst = B.iloc[int(np.argmax(abs(B.e)))]
    NUM[key + "_blind"] = dict(rows=[dict(label=r.label, session=int(r.held), y=float(r.y), p=round(float(r.p), 2), e=round(float(r.e), 2))
                                     for r in B.itertuples()], worst=dict(label=worst.label, e=round(float(worst.e), 2)),
                               max_abs=round(float(abs(B.e).max()), 2), slopes=slopes)

blind(Dab, "ab_blind.png", "ABCH")
blind(Darc, "arc_blind.png", "ARC")

# ------------------------------------------------------------------ figure: final check over every preprocessing x model (midsem image14, 1648 x 928)
FC = BASE / "final_model_check"
dec = json.load(open(FC / "decision.json"))
ORDER = ["absorbance + offset", "absorbance + offset + EMSC", "absorbance", "raw reflectance", "SNV", "MSC",
         "absorbance + SNV + SG1", "absorbance + SG1", "SG1", "SG2", "chemistry bands: absorbance + offset",
         "chemistry bands: absorbance + SG1", "chemistry bands: absorbance + SG2", "chemistry bands: EMSC"]
SHORT = {"chemistry bands: absorbance + offset": "chem. bands: abs. + offset", "chemistry bands: absorbance + SG1": "chem. bands: abs. + SG1",
         "chemistry bands: absorbance + SG2": "chem. bands: abs. + SG2", "chemistry bands: EMSC": "chem. bands: EMSC",
         "absorbance + offset + EMSC": "absorbance + offset + EMSC", "absorbance + SNV + SG1": "absorbance + SNV + SG1"}
MODELS = ["PLSR", "PCR", "Ridge", "ElasticNet", "SVR (linear)"]
MSHORT = ["PLSR", "PCR", "Ridge", "ENet", "SVR lin."]
REF = {"RBCH": ("absorbance + offset", "PLSR"), "ABCH": ("absorbance + offset + EMSC", "PLSR"), "ARC": ("chemistry bands: absorbance + SG1", "PLSR")}
TITLE = {"RBCH": "Robusta + chicory", "ABCH": "Arabica + chicory", "ARC": "Arabica + robusta + chicory"}
SEQ = LinearSegmentedColormap.from_list("seq", ["#f6efe4", "#e8d3b4", "#d4ac7c", "#b07a4a", "#7a4a2a", "#3d2416"])
fig, axs = plt.subplots(1, 3, sharey=True)
for ax, F in zip(axs, ["RBCH", "ABCH", "ARC"]):
    S = pd.read_csv(FC / f"summary_{F}.csv")
    M = S.pivot(index="prep", columns="model", values="mean").loc[ORDER, MODELS]
    V = S.set_index(["prep", "model"]).verdict
    im = ax.imshow(M.to_numpy(), cmap=SEQ, norm=LogNorm(vmin=.6, vmax=5), aspect="auto")
    for i, pn in enumerate(ORDER):
        for j, mn in enumerate(MODELS):
            v = M.iat[i, j]; ver = V[(pn, mn)]
            ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=9.5,
                    color="white" if v > 1.6 else INK, fontweight="bold" if ver == "current model" else "normal")
            if ver == "tie":
                ax.add_patch(plt.Rectangle((j - .5, i - .5), 1, 1, fill=False, ec="#2a78d6", lw=1.2, ls=":"))
    r0, c0 = ORDER.index(REF[F][0]), MODELS.index(REF[F][1])
    ax.add_patch(plt.Rectangle((c0 - .5, r0 - .5), 1, 1, fill=False, ec=INK, lw=2.6))
    ax.set_xticks(range(5), MSHORT, fontsize=9.5); ax.tick_params(length=0, pad=2); ax.grid(False)
    ax.set_yticks(range(len(ORDER)), [SHORT.get(o, o) for o in ORDER], fontsize=9.5)
    for s_ in ax.spines.values(): s_.set_visible(False)
    d = dec[F]
    ax.set_title(f"{TITLE[F]}\nchosen {d['current_mean']:.2f} %, rank {d['current_rank']}/70", fontsize=10.5)
fig.subplots_adjust(left=.2, right=.995, top=.9, bottom=.045, wspace=.05)
save(fig, "final_grid.png", (1140, 642))
NUM["final_check"] = {F: {k: dec[F][k] for k in ("current_mean", "current_rank", "lowest", "lowest_mean", "n_better", "n_tie", "n_worse")} for F in dec}

# ------------------------------------------------------------------ figure: linear vs nonlinear, every mixture (midsem image6 slot, 1977 x 886)
rb = pd.read_csv(BASE / "final_regression/method_summary.csv").set_index("model").mean_rmsep
lin = {"Robusta + chicory": rb.loc[["PLSR", "PCR", "Ridge", "ElasticNet", "SVR (linear)"]].min(),
       "Arabica + chicory": ab_cmp.loc[["EMSC + PLSR", "SVR (linear)", "ElasticNet", "Ridge", "PLSR", "PCR"], "mean"].min(),
       "Arabica + robusta\n+ chicory": arc_cmp.loc[[ARC_BEST, "ElasticNet", "first derivative + PLSR", "Ridge", "PCR", "SVR (linear)", "PLSR", "EMSC + PLSR"], "mean"].min()}
nl = {}
for name, src in (("Robusta + chicory", rb), ("Arabica + chicory", ab_cmp["mean"]), ("Arabica + robusta\n+ chicory", arc_cmp["mean"])):
    nl[name] = {m: float(src.loc[m]) for m in ("Random Forest", "Gradient Boosting", "SVR (RBF)")}
fig, ax = plt.subplots()
x = np.arange(3); w = .2
cols = ["#5b3a26", "#c9a27a", "#a7a39a", "#7d7a73"]
labels = ["best linear model", "Random Forest", "Gradient Boosting", "SVR (RBF)"]
for k, lab in enumerate(labels):
    vals = [lin[n] if k == 0 else nl[n][lab] for n in lin]
    bars = ax.bar(x + (k - 1.5) * w, vals, w * .92, color=cols[k], label=lab)
    for xi, v in zip(x + (k - 1.5) * w, vals):
        ax.text(xi, v * 1.08, f"{v:.2f}", ha="center", va="bottom", fontsize=21, fontweight="bold" if k == 0 else "normal")
ax.set_yscale("log"); ax.set_yticks([.5, 1, 2, 5, 10], ["0.5", "1", "2", "5", "10"]); ax.set_ylim(.4, 20)
ax.set_xticks(x, list(lin), fontsize=22); ax.tick_params(axis="y", labelsize=20)
ax.set_ylabel("mean error on unseen sessions\n(% chicory, log scale)", fontsize=20); ax.grid(axis="x", visible=False)
ax.legend(ncol=4, loc="lower left", bbox_to_anchor=(0, 1.0), fontsize=21)
fig.subplots_adjust(left=.11, right=.99, top=.86, bottom=.17)
save(fig, "linear_vs_nonlinear.png", (1977, 886))
NUM["linear_vs_nonlinear"] = {n.replace("\n", " "): dict(best_linear=round(float(lin[n]), 2), **{k: round(v, 2) for k, v in nl[n].items()}) for n in lin}
NUM["ab_cmp"] = {m: [round(float(ab_cmp.loc[m, s]), 2) for s in (1, 2, 3)] + [round(float(ab_cmp.loc[m, "mean"]), 2)] for m in ab_cmp.index}
NUM["arc_cmp"] = {m: [round(float(arc_cmp.loc[m, s]), 2) for s in (1, 2, 3)] + [round(float(arc_cmp.loc[m, "mean"]), 2)] for m in arc_cmp.index}
json.dump(NUM, open(Path(__file__).parent / "numbers.json", "w"), indent=1)
print(json.dumps({k: v for k, v in NUM.items() if not k.endswith("_blind")}, indent=1))
for k in ("ABCH_blind", "ARC_blind"):
    print(k, NUM[k]["worst"], NUM[k]["slopes"], [(r["label"], r["session"], r["p"], r["e"]) for r in NUM[k]["rows"]])
