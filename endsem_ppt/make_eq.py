"""The maths slide's equation panel: three columns typeset with matplotlib mathtext, 2420 x 556 px (slot 12.10 x 2.78 in)."""
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

OUT = Path(__file__).parent / "figs"
plt.rcParams.update({"mathtext.fontset": "cm", "font.family": "DejaVu Sans"})
INK, BROWN, GOLD, MUTED, CARD = "#2b1b12", "#5b3a26", "#b07a2a", "#6b625a", "#f6f1ea"
fig = plt.figure(figsize=(24.2, 5.56), dpi=100)
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 24.2); ax.set_ylim(0, 5.56); ax.axis("off")

cols = [
    ("PLSR", "all three models  ·  6, 4 and 5 latent variables", [
        (r"$\hat{y} \;=\; b_0 + \mathbf{w}^{\top}\mathbf{x}$", 30),
        (r"$\mathbf{w}_a = \arg\max_{\|\mathbf{w}\|=1}\; \mathrm{cov}(\mathbf{X}_a\mathbf{w},\, \mathbf{y})$", 21),
        (r"$\mathbf{t}_a = \mathbf{X}_a\mathbf{w}_a,\;\; \mathbf{X}_{a+1} = \mathbf{X}_a - \mathbf{t}_a\mathbf{p}_a^{\top}$", 21),
        (r"$\mathbf{w} = \mathbf{W}(\mathbf{P}^{\top}\mathbf{W})^{-1}\mathbf{q}$", 21),
    ]),
    ("EMSC", "arabica + chicory  ·  then PLSR", [
        (r"$\mathbf{x}_i = a_i + d_i\lambda + e_i\lambda^2 + b_i\,\bar{\mathbf{x}} + h_i\,\mathbf{k} + \boldsymbol{\varepsilon}_i$", 21),
        (r"$\mathbf{x}_i^{\,\mathrm{corr}} = \dfrac{\mathbf{x}_i - a_i - d_i\lambda - e_i\lambda^2}{b_i}$", 24),
        (r"$\bar{\mathbf{x}}$: mean spectrum    $\mathbf{k}$: chicory direction (kept)", 17),
    ]),
    ("SG first derivative + band selection", "arabica + robusta + chicory  ·  then PLSR", [
        (r"$A_j = \log_{10}(1/R_j)$", 24),
        (r"$x_j = \sum_{m=-7}^{7} c_m\, A_{j+m}, \qquad \sum_m c_m = 0$", 21),
        (r"$j \in [1650, 1800] \cup [2150, 2400]\ \mathrm{nm}$", 21),
        (r"an offset added to every $A_j$ cancels: $x_j$ unchanged", 17),
    ]),
]
W = 24.2 / 3
for k, (title, sub, lines) in enumerate(cols):
    x0 = k * W + .12
    ax.add_patch(FancyBboxPatch((x0, .12), W - .24, 5.3, boxstyle="round,pad=0,rounding_size=.12", fc=CARD, ec="#e4d9cc", lw=1.5))
    ax.text(x0 + .35, 4.92, title, fontsize=23, fontweight="bold", color=BROWN, va="center")
    ax.text(x0 + .35, 4.40, sub, fontsize=16, color=GOLD, va="center", fontweight="bold")
    y = 3.55
    step = 3.2 / (len(lines) - .3)
    for text, fs in lines:
        ax.text(x0 + .35, y, text, fontsize=fs * 1.18, color=INK if fs > 18 else MUTED, va="center")
        y -= step
fig.savefig(OUT / "equations.png", dpi=100, facecolor="white")
print("saved", OUT / "equations.png")
