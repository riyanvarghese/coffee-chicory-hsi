"""Pipeline block diagram for the slides (final_regression/images/09_pipeline_block_diagram.png).

Usage:  python pipeline_block_diagram.py <out.png>
Two rows: data preparation (grey) and model development (blue, with the
leave-one-session-out and per-model loops drawn as frames).
"""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = sys.argv[1]
W, H = 16, 5.35
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#898781"
ACCENT, ACCENT_SOFT = "#2a78d6", "#e7f0fb"
NEUTRAL, NEUTRAL_EDGE = "#f1f0eb", "#c3c2b7"
BG = "#ffffff"

fig = plt.figure(figsize=(W, H), facecolor=BG)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis("off")
FS = 12.5
BH = 0.95

def block(x, yc, w, text, fill, edge, color=INK, weight="normal"):
    ax.add_patch(FancyBboxPatch((x, yc - BH / 2), w, BH, boxstyle="round,pad=0,rounding_size=0.12",
                                fc=fill, ec=edge, lw=1.3, zorder=3))
    ax.text(x + w / 2, yc, text, ha="center", va="center", fontsize=FS, color=color,
            fontweight=weight, linespacing=1.15, zorder=4)

def frame(x0, y0, x1, y1, color, ls, label, lcolor):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0, boxstyle="round,pad=0,rounding_size=0.18",
                                fc="none", ec=color, lw=1.6, ls=ls, zorder=2))
    ax.text(x0 + 0.16, y1 - 0.2, label, ha="left", va="center", fontsize=11.5, color=lcolor,
            fontweight="bold", zorder=4)

def arrow(p0, p1):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=15, color=INK2, lw=1.4,
                                 shrinkA=0, shrinkB=0, zorder=5))

# ---------------- row 1: data acquisition and preparation ----------------
row1 = ["Data\nacquisition", "Radiance →\nreflectance", "Dish\nmasking",
        "Patch\nextraction", "Spectral\npreprocessing"]
w1, g1, y1 = 2.44, 0.6, 4.3
x = (W - (len(row1) * w1 + (len(row1) - 1) * g1)) / 2
xs1 = []
for i, t in enumerate(row1):
    block(x, y1, w1, t, NEUTRAL, NEUTRAL_EDGE)
    xs1.append(x)
    if i: arrow((x - g1, y1), (x, y1))
    x += w1 + g1

# ---------------- row 2: model development and evaluation ----------------
w2, g2, y2 = 1.45, 0.32, 1.45
pin, pout, gap_after = 0.15, 0.18, 0.42
total = 8 * w2 + 6 * g2 + gap_after + 2 * (pin + pout)
x0 = xs1[-1] + w1 - total            # right edge lines up with row 1
b = []
cur = x0 + pout
b.append(cur); cur += w2 + g2                     # trimming
b.append(cur); cur += w2 + g2                     # super-patches
inner_l = cur; cur += pin
for _ in range(3):
    b.append(cur); cur += w2 + g2
cur -= g2
inner_r = cur + pin
outer_r = inner_r + pout
cur = outer_r + gap_after
for _ in range(3):
    b.append(cur); cur += w2 + g2

labels = ["Outlier\ntrimming", "Super-patch\naveraging", "Parameter\ntuning", "Model\ntraining",
          "Held-out\nprediction", "Model\nselection", "Final PLSR\nmodel", "Results"]
inner_b, inner_t = y2 - BH / 2 - pin, y2 + BH / 2 + pin + 0.36
outer_b, outer_t = inner_b - pout, inner_t + pout + 0.2
frame(x0, outer_b, outer_r, outer_t, ACCENT, (0, (5, 3)), "↻  Leave-one-session-out  ×3", ACCENT)
frame(inner_l, inner_b, inner_r, inner_t, MUTED, (0, (1.5, 2)), "↻  For each of 8 models", INK2)

for i, (xb, t) in enumerate(zip(b, labels)):
    if t == "Results":
        block(xb, y2, w2, t, ACCENT, ACCENT, color="#ffffff", weight="bold")
    elif i >= 5:
        block(xb, y2, w2, t, ACCENT_SOFT, ACCENT)
    else:
        block(xb, y2, w2, t, ACCENT_SOFT, "#9cc0ea")
    if i:
        arrow((b[i - 1] + w2, y2), (xb, y2))

# ---------------- connector: end of row 1 -> start of row 2 ----------------
xe = xs1[-1] + w1 / 2
xl = x0 - 0.28
ymid = (y1 - BH / 2 + outer_t) / 2
ax.plot([xe, xe, xl, xl], [y1 - BH / 2, ymid, ymid, y2], color=INK2, lw=1.4, zorder=1,
        solid_capstyle="butt", solid_joinstyle="miter")
arrow((xl, y2), (b[0], y2))

fig.savefig(OUT, dpi=220, facecolor=BG)
print("saved", OUT)
