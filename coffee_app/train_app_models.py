"""Train and export the models used by the coffee web app (models.json).

Families (mixture types) supported:
  RBCH  robusta + chicory              PLSR on absorbance + offset                        (0.79 % LOSO)
  ABCH  arabica + chicory              EMSC + PLSR on absorbance + offset                 (0.78 % LOSO)
  ARC   arabica + robusta + chicory    first derivative on 1650-1800 + 2150-2400 nm, PLSR (0.94 % LOSO)
        (assumed composition of the "AR" series: arabica-robusta base + chicory = the label's second number;
         the 13:30 "AR 50-50" dishes are left out)
Classifier: three classes, PCA (15 components) + LDA (three_mixture_classifier.ipynb: balanced accuracy 0.95
leave-one-scan-set-out, 0.96 leave-one-day-out).
Everything exported is linear, so the browser can apply it exactly.

Run:  python train_app_models.py      (reads the project CSVs, writes models.json + validation printout)
"""
import os
import json
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.cross_decomposition import PLSRegression
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.linear_model import LogisticRegression
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from scipy.signal import savgol_filter
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import mean_squared_error

BASE = Path(os.environ.get("COFFEE_DATA", str(Path(__file__).resolve().parents[1])))
OUT = BASE / "coffee_app"
LEVELS = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
WL_MIN, WL_MAX, TRIM_PCT, K_UNIT = 1000.0, 2450.0, 10, 8
LOSO = {"RBCH": dict(mean=0.787, pooled=0.883, source="robusta_chicory_nested_loso.ipynb (PLSR)"),
        "ABCH": dict(mean=0.778, pooled=0.982, source="arabica_advanced_models_nested_loso.ipynb (EMSC + PLSR)")}
_hp = pd.read_csv(BASE / "arabica_robusta_models_excl_1330_5050" / "heldout_predictions.csv")
_hp = _hp[_hp.model == "chemistry bands, derivative + PLSR"].groupby(["fold", "group"]).agg(y=("y", "first"), p=("p", "mean"))
LOSO["ARC"] = dict(mean=float(np.mean([np.sqrt(((g.p - g.y) ** 2).mean()) for _, g in _hp.groupby(level=0)])),
                   pooled=float(np.sqrt(((_hp.p - _hp.y) ** 2).mean())),
                   source="arabica_robusta_models_excl_1330_5050 (chemistry bands, first derivative + PLSR)")


def load(family):
    if family == "RBCH":
        old = pd.read_csv(BASE / "samples_out" / "training_samples.csv")
        new = pd.read_csv(BASE / "batch3_out" / "training_samples.csv")
        for c in ("scan", "group", "plate"):
            new[c] = new[c].astype(str) + "_b3"
        D, sp = pd.concat([old, new], ignore_index=True), ["robusta", "robusta_chicory"]
    elif family == "ARC":
        AR = pd.read_csv(BASE / "arabica_robusta_out" / "training_samples.csv")
        D = AR[(AR.role == "calibration") & ~((AR.day == 2) & (AR.label == "AR[50:50]"))].reset_index(drop=True)
        D["chicory_pct"] = D["robusta_pct"]          # assumed: the label's second number is chicory %
        D["session"] = D["day"].astype(int)
        return D
    else:
        D, sp = pd.read_csv(BASE / "arabica_out" / "arabica_chicory_all_sessions.csv"), ["arabica", "arabica_chicory"]
    D = D[D.species.isin(sp) & (D.role == "calibration") & D.chicory_pct.isin(LEVELS)].reset_index(drop=True)
    D["session"] = D["day"].astype(int)
    return D


def preprocess(R):
    Z = np.log10(1.0 / np.clip(np.asarray(R, float), 1e-3, None))
    return Z - Z.mean(-1, keepdims=True)


_t = pd.read_csv(BASE / "samples_out" / "training_samples.csv", nrows=2)
WC = [c for c in _t.columns if c.replace(".", "", 1).isdigit()]
WL_ALL = np.array([float(c) for c in WC])
BM = (WL_ALL >= WL_MIN) & (WL_ALL <= WL_MAX)
COLS = [c for c, k in zip(WC, BM) if k]
WL = WL_ALL[BM]
LAM = np.linspace(-1, 1, len(WL))
CHEM = ((WL >= 1650) & (WL <= 1800)) | ((WL >= 2150) & (WL <= 2400))
sg1_chem = lambda Z: savgol_filter(np.atleast_2d(Z), 15, 2, deriv=1, axis=1)[:, CHEM]


def units(D, Z, k=K_UNIT):
    """Final notebooks' trimming + super-patches, fitted on all sessions."""
    Y, G = D.chicory_pct.to_numpy(float), D.group.astype(str).to_numpy()
    ref = PLSRegression(n_components=4).fit(Z, Y)
    mu = Z.mean(0)
    T = (Z - mu) @ ref.x_rotations_
    q = np.sum(((Z - mu) - T @ ref.x_loadings_.T) ** 2, axis=1)
    keep = pd.Series(q).groupby(G).rank(pct=True).to_numpy() <= 1 - TRIM_PCT / 100
    idx = []
    for g in pd.unique(G):
        ii = np.where((G == g) & keep)[0]
        if len(ii) < k:
            continue
        n = max(1, len(ii) // k)
        lab = KMeans(n_clusters=n, n_init=5, random_state=0).fit_predict(D.loc[ii, ["patch_row", "patch_col"]].to_numpy(float))
        idx += [ii[lab == c] for c in range(n) if (lab == c).any()]
    ZU = np.array([Z[i].mean(0) for i in idx])
    UM = D.iloc[[i[0] for i in idx]][["session", "label", "group", "chicory_pct"]].reset_index(drop=True)
    trim = dict(mean=mu.tolist(), rotations=ref.x_rotations_.T.tolist(), loadings=ref.x_loadings_.T.tolist(), keep_frac=1 - TRIM_PCT / 100)
    return ZU, UM, trim


def plate_rmse(y, p, g):
    t = pd.DataFrame(dict(g=g, y=y, p=p)).groupby("g")[["y", "p"]].mean()
    return float(np.sqrt(mean_squared_error(t.y, t.p)))


def tune_lv(X, y, g, grid=range(1, 13)):
    rows = []
    for a in grid:
        f = [plate_rmse(y[b], PLSRegression(a).fit(X[t], y[t]).predict(X[b]).ravel(), g[b])
             for t, b in LeaveOneGroupOut().split(X, y, groups=y)]
        rows.append((a, np.mean(f), np.std(f, ddof=1) / np.sqrt(len(f))))
    T = pd.DataFrame(rows, columns=["a", "m", "se"])
    b = T.m.idxmin()
    return int(T.a[np.flatnonzero(T.m.to_numpy() <= T.m[b] + T.se[b])[0]])


def linear_map(model, n):
    """y = X @ w + w0 for any fitted linear sklearn model (exact)."""
    w0 = float(np.ravel(model.predict(np.zeros((1, n))))[0])
    w = np.ravel(model.predict(np.eye(n))) - w0
    return w, w0


def emsc_basis(ZU, y):
    m = ZU.mean(0); yc = y - y.mean()
    k = yc @ (ZU - m) / (yc @ yc)
    return m, k


def emsc_apply(Z, m, k):
    B = np.column_stack([np.ones_like(LAM), m, k, LAM, LAM ** 2])
    a, b, h, d, e = np.linalg.lstsq(B, np.atleast_2d(Z).T, rcond=None)[0]
    return (np.atleast_2d(Z) - a[:, None] - np.outer(d, LAM) - np.outer(e, LAM ** 2)) / b[:, None]


fam = {}
KIND = {"RBCH": "PLSR", "ABCH": "EMSC + PLSR", "ARC": "first derivative (chemistry bands) + PLSR"}
for F in ("RBCH", "ABCH", "ARC"):
    D = load(F)
    Z = preprocess(D[COLS].values)
    ZU, UM, trim = units(D, Z)
    y, g = UM.chicory_pct.to_numpy(float), UM.group.to_numpy()
    entry = dict(trim=trim)
    if F == "ABCH":
        m, k = emsc_basis(ZU, y)
        X = emsc_apply(ZU, m, k)
        entry["emsc"] = dict(mean=m.tolist(), chicory_direction=k.tolist())
    elif F == "ARC":
        X = sg1_chem(ZU)
    else:
        X = ZU
    lv = tune_lv(X, y, g)
    pls = PLSRegression(lv).fit(X, y)
    if F == "ARC":       # derivative + band selection are linear: fold them into one 266-band coefficient vector
        class _Full:
            def predict(self, Zf): return pls.predict(sg1_chem(Zf))
        w, w0 = linear_map(_Full(), ZU.shape[1])
        X = ZU
    else:
        w, w0 = linear_map(pls, X.shape[1])
    assert np.allclose(X @ w + w0, (pls.predict(sg1_chem(ZU)) if F == "ARC" else pls.predict(X)).ravel(), atol=1e-6)
    fit_dish = pd.DataFrame(dict(g=g, y=y, p=X @ w + w0)).groupby("g")[["y", "p"]].mean()
    # applicability domain: PCA (4 components) on the family's dish means. The reference Q and T2 are the 95th
    # percentiles of dishes scored by a PCA fitted WITHOUT their session, so a normal new session scores about 1.
    dm_df = pd.DataFrame(ZU).groupby(g).mean()
    ses = UM.groupby("group").session.first().loc[dm_df.index].to_numpy()
    qh, th = [], []
    for s_ in np.unique(ses):
        p_ = PCA(n_components=4).fit(dm_df.values[ses != s_])
        Xh = dm_df.values[ses == s_]; sh = p_.transform(Xh)
        qh += list(((Xh - p_.inverse_transform(sh)) ** 2).sum(1)); th += list((sh ** 2 / p_.explained_variance_).sum(1))
    pca = PCA(n_components=4).fit(dm_df.values)
    q, t2 = np.array(qh), np.array(th)
    entry.update(model=dict(kind=KIND[F], latent_variables=lv, w=w.tolist(), w0=w0),
                 domain=dict(pca_mean=pca.mean_.tolist(), components=pca.components_.tolist(),
                             variances=pca.explained_variance_.tolist(), q_ref=float(np.percentile(q, 95)),
                             t2_ref=float(np.percentile(t2, 95))),
                 error=dict(loso_mean_rmsep=LOSO[F]["mean"], loso_pooled_rmsep=LOSO[F]["pooled"], source=LOSO[F]["source"]),
                 calibrated_range=[0, 50], n_dishes=int(len(fit_dish)), n_superpatches=int(len(y)))
    fam[F] = dict(entry=entry, ZU=ZU, UM=UM, D=D, fit=fit_dish.assign(family=F))
    print(f"{F}: {entry['model']['kind']}, {lv} LV, {len(y)} super-patches, {len(fit_dish)} dishes, "
          f"fit RMSE per dish {np.sqrt(((fit_dish.p - fit_dish.y) ** 2).mean()):.2f} %")

# ---------------- classifier: three classes, PCA (15) + LDA on absorbance + offset super-patches
CLASSES = ["RBCH", "ABCH", "ARC"]
Xc = np.vstack([fam[F]["ZU"] for F in CLASSES])
yc = np.concatenate([np.full(len(fam[F]["ZU"]), i) for i, F in enumerate(CLASSES)])
pca_c = PCA(n_components=15).fit(Xc)
lda = LinearDiscriminantAnalysis().fit(pca_c.transform(Xc), yc)
Wc = pca_c.components_.T @ lda.coef_.T                           # (bands, 3): class score = z @ Wc + bc
bc = lda.intercept_ - pca_c.mean_ @ Wc
assert np.allclose(Xc @ Wc + bc, lda.decision_function(pca_c.transform(Xc)), atol=1e-6)
_sm = lambda S: np.exp(S - S.max(1, keepdims=True)) / np.exp(S - S.max(1, keepdims=True)).sum(1, keepdims=True)
assert np.allclose(_sm(Xc @ Wc + bc), lda.predict_proba(pca_c.transform(Xc)), atol=1e-6)
grp = np.concatenate([fam[F]["UM"].group.astype(str).to_numpy() for F in CLASSES])
dp = pd.DataFrame(_sm(Xc @ Wc + bc)).groupby(grp).mean().idxmax(axis=1)
dt = pd.Series(yc).groupby(grp).first()
print(f"\nclassifier: PCA-LDA, 15 components; in-sample dish accuracy {(dp == dt.loc[dp.index]).mean():.3f} "
      "(held-out: 0.949 by scan set, 0.960 by day, three_mixture_classifier.ipynb)")

# ---------------- reference spectra for the app's plot (dish-mean reflectance of pure coffees and chicory)
s1 = pd.read_csv(BASE / "samples_out" / "training_samples.csv")
refs = {lab: s1[s1.label == lab][WC].to_numpy().mean(0).round(5).tolist() for lab in ("RB100", "AB100", "CH100")}

# ---------------- Spectralon certificate on the 288 camera bands
cert = []
for line in (BASE / "SRT-MS-050__1_.txt").read_text(errors="ignore").replace("\r", "").split("\n"):
    p = line.strip().split("\t")
    try: cert.append([float(x) for x in p[:2]])
    except ValueError: pass
cert = np.array(cert)
wl_exact = pd.read_csv(BASE / "arabica_out" / "wavelengths.csv")["wavelength_exact_nm"].to_numpy()
R_cert = np.interp(wl_exact, cert[:, 0], cert[:, 1])

models = dict(
    version="2026-11-07",
    wavelengths=wl_exact.round(4).tolist(), band_min=WL_MIN, band_max=WL_MAX, white_certificate=R_cert.round(6).tolist(),
    pipeline=dict(brightness_band_nm=[1500, 1700], strip_inset_rows=8, dish_inset_px=6, erode_px=4, dark_frac=0.55,
                  glare_pct=99.7, patch=12, min_valid=0.92, superpatch=K_UNIT, refl_range=[-0.05, 1.6],
                  bad_column_frac=0.5, bad_pixel_tol=0.5),
    classifier=dict(kind="PCA-LDA", components=15, classes=CLASSES, W=Wc.T.tolist(), b=bc.tolist(),
                    validation=dict(balanced_accuracy_leave_one_scanset_out=0.949, balanced_accuracy_leave_one_day_out=0.960,
                                    source="three_mixture_classifier.ipynb")),
    families=dict(
        RBCH=dict(name="Robusta + chicory", base="robusta", adulterant="chicory", **fam["RBCH"]["entry"]),
        ABCH=dict(name="Arabica + chicory", base="arabica", adulterant="chicory", **fam["ABCH"]["entry"]),
        ARC=dict(name="Arabica + robusta + chicory", base="arabica + robusta", adulterant="chicory",
                 note="assumed composition of the AR series; the arabica : robusta split of the base is not measured",
                 **fam["ARC"]["entry"])),
    references=refs,
)
(OUT / "models.json").write_text(json.dumps(models))
pd.concat([fam[F]["fit"] for F in fam]).rename_axis("group").reset_index().to_csv(OUT / "training_dish_predictions.csv", index=False)
print("wrote", OUT / "models.json", f"({(OUT / 'models.json').stat().st_size / 1e3:.0f} kB)")


# ---------------- reference implementation of the app's decision logic, applied to the training data + extras
def app_predict(Zp, F):
    e = models["families"][F]
    X = emsc_apply(Zp, np.array(e["emsc"]["mean"]), np.array(e["emsc"]["chicory_direction"])) if "emsc" in e else Zp
    return X @ np.array(e["model"]["w"]) + e["model"]["w0"]

def domain(zdish, F):
    d = models["families"][F]["domain"]
    c = np.array(d["components"]); x = zdish - np.array(d["pca_mean"]); sc = c @ x
    return float(((x - sc @ c) ** 2).sum() / d["q_ref"]), float((sc ** 2 / np.array(d["variances"])).sum() / d["t2_ref"])

ext = s1[s1.label.isin(["CH100", "A", "B", "C"])]
print("\nsanity check on samples never trained on (dish means, untrimmed):")
for lab, gg in ext.groupby("label"):
    for grp_, dd in gg.groupby("group"):
        z = preprocess(dd[COLS].values).mean(0)
        pr = _sm((z @ Wc + bc)[None])[0]; F = CLASSES[int(pr.argmax())]
        print(f"  {lab:6s} P = {np.round(pr, 2)} -> {F}: chicory {app_predict(z[None], F)[0]:6.1f} %, "
              f"Q/ref {domain(z, F)[0]:6.2f}, T2/ref {domain(z, F)[1]:6.2f}")
