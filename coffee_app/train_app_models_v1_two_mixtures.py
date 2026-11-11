"""Train and export the models used by the coffee web app (models.json).

Families (mixture types) supported now:
  RBCH  robusta + chicory   PLSR on absorbance + offset           (final robusta model, 0.79 % LOSO)
  ABCH  arabica + chicory   EMSC + PLSR on absorbance + offset    (best arabica model, 0.78 % LOSO)
Classifier: robusta-based vs arabica-based (PLS-DA), validated leave-one-day-out.
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
from sklearn.model_selection import LeaveOneGroupOut
from sklearn.metrics import mean_squared_error

BASE = Path(os.environ.get("COFFEE_DATA", str(Path(__file__).resolve().parents[1])))
OUT = BASE / "coffee_app"
LEVELS = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50]
WL_MIN, WL_MAX, TRIM_PCT, K_UNIT = 1000.0, 2450.0, 10, 8
LOSO = {"RBCH": dict(mean=0.787, pooled=0.883, source="robusta_chicory_nested_loso.ipynb (PLSR)"),
        "ABCH": dict(mean=0.778, pooled=0.982, source="arabica_advanced_models_nested_loso.ipynb (EMSC + PLSR)")}


def load(family):
    if family == "RBCH":
        old = pd.read_csv(BASE / "samples_out" / "training_samples.csv")
        new = pd.read_csv(BASE / "batch3_out" / "training_samples.csv")
        for c in ("scan", "group", "plate"):
            new[c] = new[c].astype(str) + "_b3"
        D, sp = pd.concat([old, new], ignore_index=True), ["robusta", "robusta_chicory"]
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
for F in ("RBCH", "ABCH"):
    D = load(F)
    Z = preprocess(D[COLS].values)
    ZU, UM, trim = units(D, Z)
    y, g = UM.chicory_pct.to_numpy(float), UM.group.to_numpy()
    entry = dict(trim=trim)
    if F == "ABCH":
        m, k = emsc_basis(ZU, y)
        X = emsc_apply(ZU, m, k)
        entry["emsc"] = dict(mean=m.tolist(), chicory_direction=k.tolist())
    else:
        X = ZU
    lv = tune_lv(X, y, g)
    pls = PLSRegression(lv).fit(X, y)
    w, w0 = linear_map(pls, X.shape[1])
    assert np.allclose(X @ w + w0, pls.predict(X).ravel(), atol=1e-8)
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
    entry.update(model=dict(kind="PLSR" if F == "RBCH" else "EMSC + PLSR", latent_variables=lv, w=w.tolist(), w0=w0),
                 domain=dict(pca_mean=pca.mean_.tolist(), components=pca.components_.tolist(),
                             variances=pca.explained_variance_.tolist(), q_ref=float(np.percentile(q, 95)),
                             t2_ref=float(np.percentile(t2, 95))),
                 error=dict(loso_mean_rmsep=LOSO[F]["mean"], loso_pooled_rmsep=LOSO[F]["pooled"], source=LOSO[F]["source"]),
                 calibrated_range=[0, 50], n_dishes=int(len(fit_dish)), n_superpatches=int(len(y)))
    fam[F] = dict(entry=entry, ZU=ZU, UM=UM, D=D, fit=fit_dish.assign(family=F))
    print(f"{F}: {entry['model']['kind']}, {lv} LV, {len(y)} super-patches, {len(fit_dish)} dishes, "
          f"fit RMSE per dish {np.sqrt(((fit_dish.p - fit_dish.y) ** 2).mean()):.2f} %")

# ---------------- classifier: robusta-based (0) vs arabica-based (1), PLS-DA on absorbance + offset
Xc = np.vstack([fam["RBCH"]["ZU"], fam["ABCH"]["ZU"]])
yc = np.r_[np.zeros(len(fam["RBCH"]["ZU"])), np.ones(len(fam["ABCH"]["ZU"]))]
day = np.r_[fam["RBCH"]["UM"].session, fam["ABCH"]["UM"].session]
grp = np.r_[fam["RBCH"]["UM"].group, fam["ABCH"]["UM"].group].astype(str)
lvl = np.r_[fam["RBCH"]["UM"].chicory_pct, fam["ABCH"]["UM"].chicory_pct]
print("\nclassifier, leave-one-day-out (dish = mean score of its super-patches):")
cv = []
for a in (1, 2, 3, 4, 5, 6, 8):
    wrong, n, margins = 0, 0, []
    for d in (1, 2, 3):
        tr, te = day != d, day == d
        p = PLSRegression(a).fit(Xc[tr], yc[tr]).predict(Xc[te]).ravel()
        t = pd.DataFrame(dict(g=grp[te], y=yc[te], p=p)).groupby("g")[["y", "p"]].mean()
        wrong += int(((t.p > .5) != (t.y > .5)).sum()); n += len(t)
        margins += list(np.where(t.y > .5, t.p - .5, .5 - t.p))
    cv.append((a, wrong, n, float(np.min(margins))))
    print(f"  {a} LV: {n - wrong}/{n} dishes correct, smallest margin {np.min(margins):+.3f}")
CV = pd.DataFrame(cv, columns=["a", "wrong", "n", "margin"])
a_cls = int(CV[CV.wrong == CV.wrong.min()].a.min())          # simplest model with the fewest errors
clf = PLSRegression(a_cls).fit(Xc, yc)
wc_, wc0 = linear_map(clf, Xc.shape[1])
s = Xc @ wc_ + wc0
lr = LogisticRegression(C=1e3).fit(s[:, None], yc)                 # score -> probability of "arabica-based"
print(f"classifier: PLS-DA {a_cls} LV; logistic calibration slope {lr.coef_[0, 0]:.2f}, intercept {lr.intercept_[0]:.2f}")

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
    classifier=dict(kind="PLS-DA", latent_variables=a_cls, w=wc_.tolist(), w0=wc0,
                    logistic=[float(lr.coef_[0, 0]), float(lr.intercept_[0])],
                    classes=["RBCH", "ABCH"], validation=CV.to_dict("records")),
    families=dict(
        RBCH=dict(name="Robusta + chicory", base="robusta", adulterant="chicory", **fam["RBCH"]["entry"]),
        ABCH=dict(name="Arabica + chicory", base="arabica", adulterant="chicory", **fam["ABCH"]["entry"]),
        ARRB=dict(name="Arabica + robusta", base="arabica", adulterant="robusta", available=False,
                  note="pending: dish labels of the arabica+robusta scans to be confirmed, 7 Sep scans to be added")),
    references=refs,
)
(OUT / "models.json").write_text(json.dumps(models))
pd.concat([fam[F]["fit"] for F in fam]).rename_axis("group").reset_index().to_csv(OUT / "training_dish_predictions.csv", index=False)
print("wrote", OUT / "models.json", f"({(OUT / 'models.json').stat().st_size / 1e3:.0f} kB)")


# ---------------- reference implementation of the app's decision logic, applied to the training data + extras
def app_predict(Zp, F):
    """Zp: preprocessed patches of one dish (already trimmed + grouped by caller) -> chicory % per unit."""
    e = models["families"][F]
    X = Zp if F == "RBCH" else emsc_apply(Zp, np.array(e["emsc"]["mean"]), np.array(e["emsc"]["chicory_direction"]))
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
        sc_ = float(z @ wc_ + wc0); pa = 1 / (1 + np.exp(-(lr.coef_[0, 0] * sc_ + lr.intercept_[0])))
        F = "ABCH" if pa > .5 else "RBCH"
        print(f"  {lab:6s} P(arabica-based) {pa:.2f} -> {F}: chicory {app_predict(z[None], F)[0]:6.1f} %, "
              f"Q/ref {domain(z, F)[0]:6.2f}, T2/ref {domain(z, F)[1]:6.2f}")
for F in ("RBCH", "ABCH"):
    D = fam[F]["D"]; Zd = preprocess(D[COLS].values)
    qs = [domain(Zd[(D.group == gname).to_numpy()].mean(0), F) for gname in D.group.unique()]
    print(f"  {F} training dishes: Q/ref max {max(q for q, _ in qs):.2f}, T2/ref max {max(t for _, t in qs):.2f}")
