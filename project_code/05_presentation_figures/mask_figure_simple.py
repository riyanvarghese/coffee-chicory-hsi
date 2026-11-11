"""Simple mask-versus-petri-dish figure used on the "Data acquisition" slide (v6 onwards).

Usage:  python mask_figure_simple.py <out.png>
Same dish and masking code as mask_figure_labelled.py; tints the kept pixels and prints the
image coordinates the slide arrows point to.
"""
import os
import json, sys, re
from pathlib import Path
os.environ.setdefault("COFFEE_DATA", str(Path(__file__).resolve().parents[2]))  # lets notebook cells run from any folder
import numpy as np, cv2
from PIL import Image
BASE = Path(os.environ.get("COFFEE_DATA", str(Path(__file__).resolve().parents[2])))
nb = json.load(open(BASE / "reflectance_training_samples.ipynb"))
exec("".join(nb["cells"][3]["source"]).split("def load_white_cert")[0])
exec("".join(nb["cells"][13]["source"]).split("def build_white")[0].replace("erode=ERODE_PX", "erode=4"))
KEY, LAB = "stir1_SWIR_384_SN3189_9000us_2026-09-04T161044_raw_rad_float32", "RB[70:30]"
sh = json.load(open(BASE / "samples_out" / "rois.json"))[KEY][LAB]
cube = Cube(BASE / f"{KEY}.hdr"); H, Wd = cube.shape[0], cube.shape[1]
br = cube.brightness(step=1)
raw = shape_mask(sh, H, Wd); kept = clean_mask(raw, br, kind="ellipse")
cy, cx, R, S = int(round(sh["cy"])), int(round(sh["cx"])), 128, 4
r0, r1, c0, c1 = max(cy - R, 0), min(cy + R, H), max(cx - R, 0), min(cx + R, Wd)
g = br[r0:r1, c0:c1]; lo, hi = np.nanpercentile(g, 1), np.nanpercentile(g, 99.5)
g = np.clip((g - lo) / (hi - lo), 0, 1)
rgb = np.repeat(g[..., None], 3, axis=2)
k = kept[r0:r1, c0:c1]
gold = np.array([0.878, 0.722, 0.447])
rgb[k] = rgb[k] * 0.45 + gold * 0.55
img = (np.clip(rgb, 0, 1) * 255).astype(np.uint8)
img = cv2.resize(img, (img.shape[1] * S, img.shape[0] * S), interpolation=cv2.INTER_NEAREST)
# outline of the drawn (eroded) mask region
er = cv2.erode(raw.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))[r0:r1, c0:c1]
er = cv2.resize(er, (er.shape[1] * S, er.shape[0] * S), interpolation=cv2.INTER_NEAREST)
cnts, _ = cv2.findContours(er, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
cv2.drawContours(img, cnts, -1, (200, 150, 79), 7)
Image.fromarray(img).save(sys.argv[1])
# arrow targets, in output-image pixels
ys, xs = np.nonzero(k); mask_pt = (float(xs.mean() * S + S / 2), float(ys.mean() * S + S / 2))
# petri dish rim: bright pixels just outside the drawn outline, lower-right quadrant
dish = (g > 0.35) & ~raw[r0:r1, c0:c1]
yy, xx = np.mgrid[0:g.shape[0], 0:g.shape[1]]
ccy, ccx = cy - r0, cx - c0
ang = np.degrees(np.arctan2(yy - ccy, xx - ccx)); rad = np.hypot((yy - ccy) / sh["ay"], (xx - ccx) / sh["ax"])
sel = dish & (ang > 25) & (ang < 55) & (rad > 1.0) & (rad < 1.2)
rim_pt = (float(np.median(xx[sel]) * S + S / 2), float(np.median(yy[sel]) * S + S / 2))
print(json.dumps(dict(size=img.shape[1::-1], mask_pt=mask_pt, rim_pt=rim_pt, rim_n=int(sel.sum()), kept_pct=round(kept.sum() / raw.sum() * 100, 1))))
