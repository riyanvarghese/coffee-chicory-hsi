"""Result figures for the slides (latent-variable curve, method comparison, performance, error per blend).

Usage:  python deck_result_figures.py <out_dir>
Reads final_regression/ (training_validation_curve.csv, outer_folds_all_methods.csv,
method_summary.csv, heldout_predictions_selected.csv), all written by robusta_chicory_nested_loso.ipynb.
"""
import os
import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
D = Path(os.environ.get("COFFEE_DATA", str(Path(__file__).resolve().parents[2]))) / "final_regression"
OUT = Path(sys.argv[1])
INK, INK2, MUTED, GRID = "#2b1810", "#6b5b4e", "#9a8f84", "#e6dcd0"
SC = {1: "#2a78d6", 2: "#eb6834", 3: "#1baf7a"}; SM = {1: "o", 2: "s", 3: "^"}
HL, OTHER = "#6b4423", "#c9bfb2"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": "#b9a894",
    "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "axes.titlecolor": INK,
    "axes.titlesize": 10.5, "axes.grid": True, "grid.color": GRID, "grid.linewidth": .6,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False, "legend.fontsize": 8.5,
    "savefig.transparent": False, "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white", "lines.linewidth": 1.8})
def save(fig, name):
    fig.savefig(OUT / name, dpi=220, bbox_inches="tight", pad_inches=0.04); plt.close(fig); print("saved", name)

# ---- F1: training vs validation curve (LV slide, 12.10 x 3.39 in) ----
cur = pd.read_csv(D / "training_validation_curve.csv")
fig, axs = plt.subplots(1, 4, figsize=(12.1, 3.3), sharey=True)
titles = {"1": "Session 1 held out (0 % only)", "2": "Session 2 held out", "3": "Session 3 held out", "final": "Final model (all sessions)"}
for ax, f in zip(axs, ["1", "2", "3", "final"]):
    c = cur[cur.fold.astype(str) == f].reset_index(drop=True); x = c.param.to_numpy(); k = int(np.flatnonzero(c.chosen)[0])
    ax.plot(x, c.training, color=MUTED, ls="--", marker="o", ms=3.5, lw=1.5, label="training")
    ax.plot(x, c.validation, color=SC[1], marker="o", ms=4, label="validation (inner CV)")
    if c.held_out.notna().any():
        ax.plot(x, c.held_out, color=SC[2], marker="s", ms=4, label="held-out session (test)")
    ax.axvline(x[k], color=INK, ls=":", lw=1.1)
    ax.text(x[k] + .25, .97, f"chosen: {x[k]}", transform=ax.get_xaxis_transform(), va="top", fontsize=9, color=INK)
    ax.set_xticks(x); ax.tick_params(axis="x", labelsize=8); ax.set_xlabel("latent variables"); ax.set_title(titles[f], loc="left")
axs[0].set_yscale("log"); axs[0].set_yticks([0.3, 0.5, 1, 2, 5, 10]); axs[0].set_yticklabels(["0.3", "0.5", "1", "2", "5", "10"])
axs[0].set_ylabel("error per dish (% chicory)"); axs[-1].plot([], [], color=SC[2], marker="s", ms=4, label="held-out session (test)"); axs[-1].legend(loc="upper right", bbox_to_anchor=(1.0, 0.86), frameon=True, facecolor="#faf6f1", edgecolor="none", framealpha=.95)
fig.tight_layout(w_pad=1.2); save(fig, "lv_curve.png")

# ---- F2: method comparison (method slide, 7.60 x 2.14 in) ----
of = pd.read_csv(D / "outer_folds_all_methods.csv")
summ = pd.read_csv(D / "method_summary.csv").set_index("model")
order = summ.sort_values("mean_rmsep").index.tolist()
fig, ax = plt.subplots(figsize=(7.6, 2.3))
y = np.arange(len(order))[::-1]
for yi, m in zip(y, order):
    v = of[of.model == m].sort_values("held_out"); mean = summ.loc[m, "mean_rmsep"]
    col = HL if m == order[0] else "#8a7f74"
    ax.plot([v.rmsep_plate.min(), v.rmsep_plate.max()], [yi, yi], color="#d8cfc4", lw=5, solid_capstyle="round", zorder=1)
    for s_, r in zip(v.held_out, v.rmsep_plate):
        ax.scatter(r, yi, s=16, color=SC[s_], marker=SM[s_], zorder=3, edgecolor="white", linewidth=.4)
    ax.scatter(mean, yi, s=70, marker="|", color=col, linewidth=2.4, zorder=4)
    ax.text(v.rmsep_plate.max() * 1.18, yi, f"{mean:.2f}", va="center", ha="left", fontsize=8.5,
            color=INK if m == order[0] else INK2, fontweight="bold" if m == order[0] else "normal")
ax.set_yticks(y, order, fontsize=8.5); ax.set_xscale("log"); ax.set_xlim(.4, 30)
ax.set_xticks([.5, 1, 2, 5, 10, 20]); ax.set_xticklabels(["0.5", "1", "2", "5", "10", "20"])
ax.set_xlabel("error per dish on the held-out session (% chicory, log scale)", fontsize=9); ax.grid(axis="y", visible=False)
for s_ in (1, 2, 3):
    ax.scatter([], [], color=SC[s_], marker=SM[s_], s=16, label=f"session {s_} held out")
ax.scatter([], [], marker="|", color="#8a7f74", s=70, linewidth=2.4, label="mean of the three (value at right)")
ax.legend(loc="upper left", bbox_to_anchor=(1.0, 1.0), fontsize=7.5, handletextpad=.3)
fig.tight_layout(); save(fig, "method_comparison.png")

# ---- F3: performance on unseen sessions (12.10 x 3.44 in) ----
pr = pd.read_csv(D / "heldout_predictions_selected.csv")
pl = pr.groupby(["fold", "group", "y"], as_index=False)["p"].agg(["mean", "std"]).reset_index()
fo = of[of.model == "PLSR"].set_index("held_out")
fig, axs = plt.subplots(1, 3, figsize=(12.1, 3.35), gridspec_kw=dict(width_ratios=[1.35, 1, 1]))
ax = axs[0]
for s in (1, 2, 3):
    u = pr[pr.fold == s]; ax.scatter(u.y + np.random.default_rng(s).normal(0, .35, len(u)), u.p, s=5, color=SC[s], alpha=.18, lw=0)
    q = pl[pl.fold == s]
    ax.errorbar(q.y, q["mean"], yerr=q["std"], fmt=SM[s], color=SC[s], ms=5.5, mec="white", mew=.6, capsize=2.5, lw=1,
                label=f"session {s} held out — {fo.loc[s, 'rmsep_plate']:.2f} %")
ax.plot([-3, 54], [-3, 54], color=INK, ls="--", lw=1)
ax.set_xlim(-3, 54); ax.set_ylim(-4, 56); ax.set_xlabel("true chicory (%)"); ax.set_ylabel("predicted chicory (%)")
ax.set_title("Each session predicted by a model that never saw it", loc="left"); ax.legend(loc="upper left")
ax = axs[1]
v = [fo.loc[s, "rmsep_plate"] for s in (1, 2, 3)]
b = ax.bar([1, 2, 3], v, color=[SC[s] for s in (1, 2, 3)], width=.6, zorder=2)
for xi, vi in zip([1, 2, 3], v): ax.text(xi, vi + .03, f"{vi:.2f}", ha="center", va="bottom", fontsize=9.5, color=INK)
mean = float(summ.loc["PLSR", "mean_rmsep"]); ax.axhline(mean, color=INK, ls="--", lw=1.1)
ax.text(.45, mean + .03, f"mean {mean:.2f} %", fontsize=9, color=INK, va="bottom")
ax.set_xticks([1, 2, 3], ["session 1", "session 2", "session 3"]); ax.set_ylim(0, 1.35); ax.set_xlim(.4, 3.6)
ax.set_ylabel("error per dish (% chicory)"); ax.set_title("Error on each held-out session", loc="left"); ax.grid(axis="x", visible=False)
ax = axs[2]
v = [fo.loc[s, "bias"] for s in (1, 2, 3)]
ax.bar([1, 2, 3], v, color=[SC[s] for s in (1, 2, 3)], width=.6, zorder=2); ax.axhline(0, color=INK, lw=.9)
for xi, vi in zip([1, 2, 3], v): ax.text(xi, vi + (.02 if vi >= 0 else -.02), f"{vi:+.2f}".replace("-", "−"), ha="center", va="bottom" if vi >= 0 else "top", fontsize=9.5, color=INK)
ax.set_xticks([1, 2, 3], ["session 1", "session 2", "session 3"]); ax.set_ylim(-.45, .7); ax.set_xlim(.4, 3.6)
ax.set_ylabel("mean bias (% chicory)"); ax.set_title("Systematic offset per session", loc="left"); ax.grid(axis="x", visible=False)
fig.tight_layout(w_pad=1.5); save(fig, "performance_unseen.png")

# ---- F4: error per blend (6.6 x 3.6 in) ----
bl = pr.groupby(["fold", "label", "y"], as_index=False)["p"].mean().sort_values("y")
bl["err"] = bl.p - bl.y
fig, ax = plt.subplots(figsize=(6.6, 3.55))
ax.bar(bl.y, bl.err, width=3.4, color=[SC[f] for f in bl.fold], zorder=2); ax.axhline(0, color=INK, lw=.9)
for yv, e in zip(bl.y, bl.err):
    ax.text(yv, e + (.05 if e >= 0 else -.05), f"{e:+.2f}".replace("-", "−"), ha="center", va="bottom" if e >= 0 else "top", fontsize=8, color=INK2)
ax.set_xticks(bl.y, [f"{int(v)}" for v in bl.y]); ax.set_xlabel("chicory in the blend (%)")
ax.set_ylabel("predicted − true (% chicory)"); ax.set_ylim(-2.05, 1.4); ax.grid(axis="x", visible=False)
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=SC[s], label=f"session {s} held out") for s in (1, 2, 3)], loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, borderaxespad=.2)
fig.tight_layout(); save(fig, "error_per_blend.png")
