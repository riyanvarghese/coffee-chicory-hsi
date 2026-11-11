"""Figures for the preprocessing slides: the brightness-correction demonstration and the 8-option comparison.

Usage:  python preprocessing_figures.py <out_dir> <path to prep_folds.csv>
prep_folds.csv comes from ../04_checks/preprocessing_check_nested_loso.py.  The demonstration uses
one real spectrum (RB[70:30], session 2) and a copy made 15 % brighter.
"""
import os
import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
OUT = Path(sys.argv[1]); SP = Path(sys.argv[2])
INK, INK2, MUTED, GRID, BROWN, GOLD = "#2b1810", "#6b5b4e", "#9a8f84", "#e6dcd0", "#6b4423", "#c8964f"
SC = {1: "#2a78d6", 2: "#eb6834", 3: "#1baf7a"}; SM = {1: "o", 2: "s", 3: "^"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": "#b9a894", "axes.labelcolor": INK2,
    "xtick.color": INK2, "ytick.color": INK2, "axes.titlecolor": INK, "axes.titlesize": 11, "axes.grid": True,
    "grid.color": GRID, "grid.linewidth": .6, "axes.spines.top": False, "axes.spines.right": False,
    "legend.frameon": False, "legend.fontsize": 9, "figure.facecolor": "white", "axes.facecolor": "white",
    "savefig.facecolor": "white", "lines.linewidth": 2})
def save(fig, n): fig.savefig(OUT / n, dpi=220, bbox_inches="tight", pad_inches=.04); plt.close(fig); print("saved", n)

# ---------- demonstration: same spectrum, 15 % brighter ----------
d = pd.read_csv(os.path.join(os.environ.get("COFFEE_DATA", str(Path(__file__).resolve().parents[2])), "samples_out/training_samples.csv"))
wc = [c for c in d.columns if c.replace(".", "", 1).isdigit()]
wl = np.array([float(c) for c in wc]); m = (wl >= 1000) & (wl <= 2450)
sel = (d.label == "RB[70:30]") & (d.day == 2)
R = d.loc[sel, np.array(wc)[m]].to_numpy(float).mean(0); wl = wl[m]
A, B = R, R * 1.15
fig, axs = plt.subplots(1, 3, figsize=(12.1, 2.95))
MARKS = [1310, 1660, 2050, 2400]
def gapmark(ax, y1, y2, fmt):
    for wv in MARKS:
        k = int(np.argmin(np.abs(wl - wv)))
        lo, hi = min(y1[k], y2[k]), max(y1[k], y2[k])
        ax.plot([wl[k], wl[k]], [lo, hi], color=INK, lw=1.3, solid_capstyle="butt", zorder=4)
        for yy in (lo, hi): ax.plot([wl[k] - 14, wl[k] + 14], [yy, yy], color=INK, lw=1.3, zorder=4)
        right = wv < 2300
        ax.text(wl[k] + (22 if right else -22), (lo + hi) / 2, fmt(hi - lo), ha="left" if right else "right", va="center",
                fontsize=8.5, color=INK, fontweight="bold", zorder=5,
                bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=.85))
ax = axs[0]
ax.fill_between(wl, A, B, color=GOLD, alpha=.28, lw=0)
ax.plot(wl, A, color=BROWN, label="real spectrum (RB[70:30])"); ax.plot(wl, B, color=GOLD, ls="--", label="same spectrum, 15 % brighter")
gapmark(ax, A, B, lambda g: f"{g:.2f}")
ax.text(.97, .97, "multiplied, not shifted:\nthe gap is wider where\nthe powder is brighter", transform=ax.transAxes, ha="right", va="top", fontsize=8.5, color=INK)
ax.set_title("As recorded: the gap changes", loc="left"); ax.set_ylabel("reflectance"); ax.legend(loc="lower left", fontsize=8.5)
ax = axs[1]
la, lb = np.log10(1 / A), np.log10(1 / B)
ax.fill_between(wl, lb, la, color=GOLD, alpha=.28, lw=0)
ax.plot(wl, la, color=BROWN); ax.plot(wl, lb, color=GOLD, ls="--")
gapmark(ax, la, lb, lambda g: f"{g:.3f}")
ax.text(.97, .05, f"the same gap, {np.log10(1.15):.3f},\nat every wavelength", transform=ax.transAxes, ha="right", va="bottom", fontsize=8.5, color=INK)
ax.set_title("Step 1 · take the log: exactly parallel", loc="left"); ax.set_ylabel("absorbance")
ax = axs[2]
ca, cb = la - la.mean(), lb - lb.mean()
ax.plot(wl, ca, color=BROWN, lw=4.5, alpha=.35); ax.plot(wl, cb, color=GOLD, ls="--", lw=1.8)
ax.text(.97, .05, "identical: the brightness\ndifference is gone", transform=ax.transAxes, ha="right", va="bottom", fontsize=9, color=INK)
ax.set_title("Step 2 · subtract each curve's average", loc="left"); ax.set_ylabel("corrected absorbance")
for a in axs: a.set_xlabel("wavelength (nm)"); a.set_xticks([1000, 1500, 2000, 2400])
fig.tight_layout(w_pad=1.6); save(fig, "correction_demo.png")

# ---------- proof: every preprocessing through the final model's test ----------
T = pd.read_csv(SP)
S = T.groupby("prep").rmsep.mean().sort_values()
label = {"absorbance + offset (current)": "Absorbance + offset (chosen)", "absorbance + SG1": "Absorbance + SG1 derivative",
         "SNV": "SNV", "MSC": "MSC", "SG1": "SG1 derivative", "absorbance": "Absorbance only (log)",
         "SG2": "SG2 derivative", "raw reflectance": "No correction (raw)"}
fig, ax = plt.subplots(figsize=(7.55, 4.45))
y = np.arange(len(S))[::-1]
for yi, (nm, v) in zip(y, S.items()):
    chosen = "current" in nm; tie = nm == "absorbance + SG1"
    ax.barh(yi, v, color=BROWN if chosen else ("#d9c3a5" if tie else "#d8d1c7"), height=.66, zorder=2)
    for s in (1, 2, 3):
        r = T[(T.prep == nm) & (T.held == s)].rmsep.iloc[0]
        ax.scatter(r, yi, s=15, color=SC[s], marker=SM[s], zorder=3, edgecolor="white", linewidth=.4)
    ax.text(3.05, yi, f"{v:.2f} %" + ("   tie with chosen" if tie else ""), va="center", fontsize=9.5,
            color=INK if chosen else INK2, fontweight="bold" if chosen else "normal")
ax.set_yticks(y, [label[n] for n in S.index], fontsize=9.5)
for t in ax.get_yticklabels():
    if "chosen" in t.get_text(): t.set_fontweight("bold"); t.set_color(INK)
ax.set_xlim(0, 4.3); ax.set_xticks([0, .5, 1, 1.5, 2, 2.5, 3])
ax.set_xlabel("bar: average error on a scanning session the model never saw (% chicory)"); ax.grid(axis="y", visible=False)
for s in (1, 2, 3): ax.scatter([], [], color=SC[s], marker=SM[s], s=15, label=f"session {s} held out")
ax.legend(loc="lower left", bbox_to_anchor=(0, 1.0), ncol=3, fontsize=8.5, handletextpad=.2, borderaxespad=.2)
fig.tight_layout(); save(fig, "preprocessing_proof.png")
