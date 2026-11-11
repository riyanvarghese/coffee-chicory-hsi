"""Detailed dish-mask figure (every masked pixel class coloured) used in the v2 deck.

Usage:  python mask_figure_labelled.py <out.png>
Re-runs the masking code of reflectance_training_samples.ipynb on dish RB[70:30], session 2, stir 1,
reading the raw radiance cube and samples_out/rois.json.  Prints the share of each pixel class.
"""
import os
import json, re, sys
from pathlib import Path
os.environ.setdefault("COFFEE_DATA", str(Path(__file__).resolve().parents[2]))  # lets notebook cells run from any folder
import numpy as np, cv2
from PIL import Image

BASE = Path(os.environ.get("COFFEE_DATA", str(Path(__file__).resolve().parents[2])))
nb = json.load(open(BASE / "reflectance_training_samples.ipynb"))
src = "".join(nb["cells"][3]["source"])
exec(src.split("def load_white_cert")[0])                       # parse_envi_header, Cube
exec("".join(nb["cells"][13]["source"]).split("def build_white")[0].replace("erode=ERODE_PX", "erode=4"))  # shape_mask, clean_mask

KEY, LAB = "stir1_SWIR_384_SN3189_9000us_2026-09-04T161044_raw_rad_float32", "RB[70:30]"
sh = json.load(open(BASE / "samples_out" / "rois.json"))[KEY][LAB]
cube = Cube(BASE / f"{KEY}.hdr")
H, Wd = cube.shape[0], cube.shape[1]
br = cube.brightness(step=1)

raw = shape_mask(sh, H, Wd)
er = cv2.erode(raw.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))).astype(bool)
med = np.nanmedian(br[er])
dark = er & ~(br > 0.55 * med)
after_dark = er & ~dark
hi = np.nanpercentile(br[after_dark], 99.7)
spec = after_dark & cv2.dilate((br > hi).astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
kept = clean_mask(raw, br, kind="ellipse")
assert np.array_equal(kept, after_dark & ~spec)
edge = raw & ~er

cy, cx, R = int(round(sh["cy"])), int(round(sh["cx"])), 128
r0, r1, c0, c1 = max(cy - R, 0), min(cy + R, H), max(cx - R, 0), min(cx + R, Wd)
g = br[r0:r1, c0:c1]
lo, hi_ = np.nanpercentile(g, 1), np.nanpercentile(g, 99.5)
g = np.clip((g - lo) / (hi_ - lo), 0, 1)
rgb = np.repeat(g[..., None], 3, axis=2)
def crop(m): return m[r0:r1, c0:c1]
outside = ~crop(raw)
rgb[outside] = rgb[outside] * 0.35 + np.array([0.17, 0.09, 0.06]) * 0.65      # dimmed, brown-tinted
for m, col, a in [(crop(edge), (0.878, 0.722, 0.447), 0.85),      # E0B872 gold
                  (crop(dark), (0.659, 0.231, 0.165), 0.85),      # A83B2A red
                  (crop(spec), (0.231, 0.553, 0.851), 1.0)]:      # 3B8DD9 blue
    rgb[m] = rgb[m] * (1 - a) + np.array(col) * a
img = Image.fromarray((rgb * 255).astype(np.uint8)).resize(((c1 - c0) * 4, (r1 - r0) * 4), Image.NEAREST)
img.save(sys.argv[1])
n = raw.sum()
print(json.dumps(dict(shape_px=int(n), kept=round(kept.sum() / n * 100, 1), edge=round(edge.sum() / n * 100, 1),
                      dark=round(dark.sum() / n * 100, 1), spec=round(spec.sum() / n * 100, 1),
                      crop=[r0, r1, c0, c1], size=img.size)))
