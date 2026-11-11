"""One small equation image per maths step on the three winner slides (transparent, 2.75 x 0.86 in at 300 dpi)."""
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = Path(__file__).parent / "figs" / "steps"; OUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({"mathtext.fontset": "cm"})
INK = "#2b1b12"
W, H = 2.75, 0.86

X, Xa, w, t, p, y, b = r"\mathbf{x}", r"\mathbf{X}_a", r"\mathbf{w}", r"\mathbf{t}", r"\mathbf{p}", r"\mathbf{y}", r"\mathbf{b}"
PLS_LV = [rf"${w}_a = \arg\max_{{\|{w}\|=1}}\ \mathrm{{cov}}({Xa}{w},\ {y})$",
          rf"${t}_a = {Xa}{w}_a, \quad \mathbf{{X}}_{{a+1}} = {Xa} - {t}_a {p}_a^{{\top}}$"]
PLS_B = [rf"${y} \approx \mathbf{{T}}\mathbf{{q}}$",
         rf"${b} = \mathbf{{W}}(\mathbf{{P}}^{{\top}}\mathbf{{W}})^{{-1}}\mathbf{{q}}$"]
STEPS = {
    "rb": [
        [r"$A_j = \log_{10}(1/R_j)$", r"$x_j = A_j - \frac{1}{266}\sum_{k} A_k$"],
        PLS_LV,
        PLS_B,
        [rf"$\hat{{y}} = \bar{{y}} + ({X} - \bar{{{X}}})^{{\top}} {b}$", r"$a = 1 \ldots 6$ latent variables"],
    ],
    "ab": [
        [rf"${X}_i = a_i + d_i\lambda + e_i\lambda^2 + b_i\,\bar{{{X}}} + h_i\,\mathbf{{k}}$",
         rf"$\mathbf{{k}} = \sum_i (y_i - \bar{{y}})({X}_i - \bar{{{X}}}) \,/\, \sum_i (y_i - \bar{{y}})^2$"],
        [rf"${X}_i^{{\,c}} = \dfrac{{{X}_i - a_i - d_i\lambda - e_i\lambda^2}}{{b_i}}$"],
        [rf"${w}_a = \arg\max\ \mathrm{{cov}}(\mathbf{{X}}^{{c}}_a{w},\ {y})$", rf"${b} = \mathbf{{W}}(\mathbf{{P}}^{{\top}}\mathbf{{W}})^{{-1}}\mathbf{{q}}$"],
        [rf"$\hat{{y}} = \bar{{y}} + ({X}^{{\,c}} - \bar{{{X}}}^{{\,c}})^{{\top}} {b}$", r"$a = 1 \ldots 4$ latent variables"],
    ],
    "arc": [
        [r"$A_j = \log_{10}(1/R_j)$", r"no offset step: the derivative removes it"],
        [r"$x_j = \sum_{m=-7}^{7} c_m\, A_{j+m}$", r"$\sum_m c_m = 0 \;\Rightarrow\; (A_j + c)' = A_j'$"],
        [r"$j \in [1650, 1800] \,\cup\, [2150, 2400]\ \mathrm{nm}$", r"$266 \rightarrow 73$ bands"],
        [rf"$\hat{{y}} = \bar{{y}} + ({X}_{{\mathrm{{sel}}}} - \bar{{{X}}}_{{\mathrm{{sel}}}})^{{\top}} {b}$", r"$a = 1 \ldots 5$ latent variables"],
    ],
}
for key, steps in STEPS.items():
    for i, lines in enumerate(steps, 1):
        fig = plt.figure(figsize=(W, H), dpi=300)
        n = len(lines)
        ys = [.5] if n == 1 else [.72, .28]
        fs = 12.5 if n == 1 else 10.5
        for ln, yy in zip(lines, ys):
            is_math = ln.startswith("$")
            txt = fig.text(.02, yy, ln, fontsize=fs if is_math else 8.6, color=INK if is_math else "#6b625a", va="center", ha="left")
            fig.canvas.draw()
            bb = txt.get_window_extent()
            if bb.width > fig.bbox.width * .97:          # shrink to fit the width
                txt.set_fontsize(txt.get_fontsize() * fig.bbox.width * .96 / bb.width)
        fig.savefig(OUT / f"{key}_{i}.png", dpi=300, transparent=True)
        plt.close(fig)
print(sorted(p.name for p in OUT.iterdir()))
