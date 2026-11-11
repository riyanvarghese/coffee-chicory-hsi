"""Spectra figure for the "Why hyperspectral imaging?" slide, with bold band labels.

Usage:  python spectra_bands_figure.py <out.png>
Same data and selection as figure 01 of complete_results.ipynb (samples_out and batch3_out
training_samples.csv, arabica removed): robusta vs 50:50, and the 11 calibration levels.
"""
import os
from pathlib import Path
import sys, numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
B = (os.environ.get("COFFEE_DATA", str(Path(__file__).resolve().parents[2])) + "/")
def load(p, tag=None):
    d = pd.read_csv(p); d = d[d.label != "AB100"].reset_index(drop=True)
    if tag:
        for c in ("scan", "group", "plate"): d[c] = d[c].astype(str) + tag
    return d
COMB = pd.concat([load(B + "samples_out/training_samples.csv"), load(B + "batch3_out/training_samples.csv", "_b3")], ignore_index=True)
wc = [c for c in COMB.columns if c.replace(".", "", 1).isdigit()]
wl_all = np.array([float(c) for c in wc]); BM = (wl_all >= 1000) & (wl_all <= 2450); WL = wl_all[BM]
R_FULL = np.clip(COMB[wc].values.astype(float), 1e-3, None); R_ALL = R_FULL[:, BM]
INK, INK2 = "#2b1810", "#52514e"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.grid": True, "grid.color": "#e6dcd0", "grid.linewidth": .6,
                     "axes.spines.top": False, "axes.spines.right": False, "axes.edgecolor": "#b9a894", "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "figure.facecolor": "white", "axes.facecolor": "white"})
BANDS = [(1450, "O–H  water"), (1730, "C–H  lipid"), (1940, "O–H  water"), (2100, "C–O  carbohydrate"), (2310, "C–H  lipid")]
def bands(ax, ytop):
    for nm, lab in BANDS:
        ax.axvline(nm, color="#6b5b4e", lw=1.1, ls=(0, (2, 2)), zorder=1)
        ax.text(nm - 8, ytop, lab, rotation=90, va="top", ha="right", fontsize=9.5, fontweight="bold", color=INK, zorder=5,
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=.9))
fig, axs = plt.subplots(1, 2, figsize=(9.2, 4.25))
ax = axs[0]
for lab, key, col in [("pure robusta (0 %)", "RB100", "#1f77b4"), ("50:50 robusta : chicory", "RB[50:50]", "#ff7f0e")]:
    s = (COMB.label == key).values; ax.plot(wl_all, R_FULL[s].mean(0), lw=2.2, label=lab, color=col, zorder=3)
ax.axvspan(wl_all[0], 1000, color="crimson", alpha=.10, lw=0); ax.axvspan(2450, wl_all[-1], color="crimson", alpha=.10, lw=0)
ax.set_ylim(0.14, 1.10); bands(ax, 1.085)
ax.set_title("Robusta vs a 50:50 blend", loc="left", fontsize=11, color=INK)
ax.legend(loc="lower left", fontsize=8.5, frameon=False)
ax = axs[1]
cmap = plt.get_cmap("viridis"); cal = (COMB.role == "calibration").values
for lv in sorted(COMB.loc[cal, "chicory_pct"].unique()):
    s = cal & (COMB.chicory_pct.values == lv)
    ax.plot(WL, R_ALL[s].mean(0), lw=1.5, color=cmap(lv / 55), label=f"{lv:.0f} %", zorder=3)
ax.set_ylim(0.14, 1.10); bands(ax, 1.085)
ax.set_title("All 11 levels, 0–50 % chicory", loc="left", fontsize=11, color=INK)
ax.legend(ncol=2, fontsize=7.5, title="chicory", title_fontsize=8, loc="lower left", frameon=False, columnspacing=.8, handlelength=1.4)
for a in axs:
    a.set_xlabel("wavelength (nm)"); a.set_xticks([1000, 1400, 1800, 2200]); a.set_ylabel("reflectance"); a.set_yticks([0.2, 0.4, 0.6, 0.8])
fig.tight_layout(w_pad=1.2)
fig.savefig(sys.argv[1], dpi=220, bbox_inches="tight", pad_inches=.04, facecolor="white")
