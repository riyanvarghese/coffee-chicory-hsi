/* CoffeeCore — reads HySpex SWIR-384 scans (raw .hyspex or radiance .img + ENVI .hdr) and applies the coffee models.
   Runs in the browser (global CoffeeCore) and in Node (require). Mirrors the project notebooks:
   arabica_reflectance_samples.ipynb (reflectance, masks, patches) and train_app_models.py (models).
   Nothing is uploaded: a "source" only needs read(start, end) -> Promise<ArrayBuffer>. */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.CoffeeCore = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  const DTYPES = { 1: [Uint8Array, 1], 2: [Int16Array, 2], 3: [Int32Array, 4], 4: [Float32Array, 4],
                   5: [Float64Array, 8], 12: [Uint16Array, 2], 13: [Uint32Array, 4] };
  const UNSIGNED = new Set([1, 12, 13]);
  const SE9 = [[0,0,0,0,1,0,0,0,0],[0,1,1,1,1,1,1,1,0],[0,1,1,1,1,1,1,1,0],[1,1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1,1],
               [1,1,1,1,1,1,1,1,1],[0,1,1,1,1,1,1,1,0],[0,1,1,1,1,1,1,1,0],[0,0,0,0,1,0,0,0,0]];   // cv2 MORPH_ELLIPSE 9x9

  // ------------------------------------------------------------------ small numeric helpers
  function percentile(arr, q) {                       // numpy default (linear), NaNs removed
    const a = Float64Array.from(arr).filter(Number.isFinite).sort();
    if (!a.length) return NaN;
    const pos = (q / 100) * (a.length - 1), lo = Math.floor(pos), hi = Math.min(lo + 1, a.length - 1);
    return a[lo] + (a[hi] - a[lo]) * (pos - lo);
  }
  const nanmedian = (arr) => percentile(arr, 50);
  function isqrt(v) { if (v < 0) return -1; let w = Math.floor(Math.sqrt(v)); while ((w + 1) * (w + 1) <= v) w++; while (w * w > v) w--; return w; }
  const fmtMB = (b) => `${(b / 1e6).toFixed(1)} MB`;

  // ------------------------------------------------------------------ ENVI header
  function parseHeader(text) {
    text = String(text).replace(/\r/g, "");
    if (!/^\s*ENVI/.test(text)) throw new Error("This header file doesn't start with 'ENVI'. Choose the .hdr file that came with the scan.");
    const body = text.slice(text.indexOf("\n") + 1), n = body.length, out = {};
    let i = 0;
    while (i < n) {
      const eq = body.indexOf("=", i);
      if (eq < 0) break;
      const key = body.slice(i, eq).trim().toLowerCase();
      let j = eq + 1;
      while (j < n && (body[j] === " " || body[j] === "\t")) j++;
      let val;
      if (body[j] === "{") { let e = body.indexOf("}", j); if (e < 0) e = n; val = body.slice(j + 1, e); i = e + 1; }
      else { let e = body.indexOf("\n", j); if (e < 0) e = n; val = body.slice(j, e); i = e + 1; }
      out[key] = val.trim();
      while (i < n && /\s/.test(body[i])) i++;
    }
    const int = (k) => (k in out ? parseInt(parseFloat(out[k]), 10) : undefined);
    const h = { samples: int("samples"), lines: int("lines"), bands: int("bands"), headerOffset: int("header offset") || 0,
                dataType: int("data type"), byteOrder: int("byte order") || 0,
                interleave: (out["interleave"] || "bsq").trim().toLowerCase(),
                ignore: "data ignore value" in out ? parseFloat(out["data ignore value"]) : null,
                description: out["description"] || "" };
    h.wavelength = out["wavelength"] ? out["wavelength"].split(",").map((s) => parseFloat(s)).filter(Number.isFinite) : [];
    return h;
  }

  // ------------------------------------------------------------------ opening a scan
  async function openScan(hdrText, src, size, name, models) {
    const h = parseHeader(hdrText);
    const L = h.lines, S = h.samples, B = h.bands;
    if (!(L > 0 && S > 0 && B > 0)) throw new Error("The header is missing lines, samples or bands.");
    if (h.interleave !== "bil") throw new Error(`The scan is stored as '${h.interleave.toUpperCase()}'; this app reads band-interleaved-by-line (BIL) files, the HySpex format.`);
    if (h.byteOrder !== 0) throw new Error("The scan is big-endian; HySpex files are little-endian. Check the header's 'byte order'.");
    const dt = DTYPES[h.dataType];
    if (!dt) throw new Error(`Data type ${h.dataType} isn't supported.`);
    const [Arr, bpe] = dt;
    const nb = L * S * B * bpe, dec = h.headerOffset;
    let off;
    if (size === dec + nb) off = dec;
    else if (size === nb) off = 0;
    else if (size > nb && size - nb < 1e7) off = size - nb;
    else throw new Error(`The data file is ${fmtMB(size)} but the header describes ${fmtMB(nb + dec)}. Check that the .hdr and the data file belong to the same scan.`);
    const wl = h.wavelength;
    if (models) {
      const mw = models.wavelengths;
      if (wl.length !== mw.length || wl.some((w, k) => Math.abs(w - mw[k]) > 0.5))
        throw new Error(`This scan has ${wl.length} bands (${wl[0] ? wl[0].toFixed(0) : "?"}–${wl.length ? wl[wl.length - 1].toFixed(0) : "?"} nm). The models were trained on the HySpex SWIR-384: 288 bands, 952–2517 nm.`);
    }
    const scan = { name, h, L, S, B, Arr, bpe, off, src, size, wl, ignore: h.ignore, raw: UNSIGNED.has(h.dataType),
                   bg: new Float32Array(B * S), bgOffset: null };
    if (scan.raw) {
      const head = await src.read(0, Math.min(off, 20016));
      const dv = new DataView(head);
      let found = -1;
      for (let o = 0; o + 16 <= dv.byteLength; o++) {
        if (Math.abs(dv.getFloat64(o, true) - wl[0]) < 1e-3 && Math.abs(dv.getFloat64(o + 8, true) - wl[1]) < 1e-3) { found = o; break; }
      }
      if (found < 0) throw new Error("This is a raw (camera-count) scan, but its binary header has no background (dark) frame the app can find. Use the radiance file exported by the HySpex software instead.");
      const bgOff = found + 2 * B * 8 + B * S * 8;
      const bdv = new DataView(await src.read(bgOff, bgOff + B * S * 8));
      for (let k = 0; k < B * S; k++) scan.bg[k] = bdv.getFloat64(8 * k, true);
      const med = nanmedian(scan.bg);
      if (!(med > 100 && med < 60000)) throw new Error(`The dark frame found in the header looks wrong (median ${med.toFixed(0)} counts).`);
      scan.bgOffset = bgOff; scan.bgMedian = med;
    }
    return scan;
  }

  // read rows [r0, r1) and columns [c0, c1) of all bands: Float32Array [row][band][col], dark removed, ignore -> NaN
  async function readBlock(scan, r0, r1, c0, c1, onProgress) {
    const { S, B, Arr, bpe, off, bg, ignore } = scan, W = c1 - c0, lineBytes = S * B * bpe;
    const out = new Float32Array((r1 - r0) * B * W);
    const step = Math.max(1, Math.floor(8e6 / lineBytes));
    for (let r = r0; r < r1; r += step) {
      const re = Math.min(r1, r + step);
      const v = new Arr(await scan.src.read(off + r * lineBytes, off + re * lineBytes));
      for (let rr = r; rr < re; rr++) {
        const base = (rr - r) * B * S, ob = (rr - r0) * B * W;
        for (let b = 0; b < B; b++) {
          const lb = base + b * S, o2 = ob + b * W, gb = b * S;
          for (let c = c0; c < c1; c++) {
            const x = v[lb + c];
            out[o2 + c - c0] = (ignore !== null && x === ignore) ? NaN : x - bg[gb + c];
          }
        }
      }
      if (onProgress) onProgress((re - r0) / (r1 - r0));
    }
    return out;
  }

  // mean of the first 8 bands within 1500-1700 nm, dark removed: the image used for strip, dishes and masks
  async function brightnessImage(scan, onProgress) {
    const { L, S, B, Arr, bpe, off, bg, ignore, wl } = scan;
    const idx = []; for (let b = 0; b < B && idx.length < 8; b++) if (wl[b] >= 1500 && wl[b] <= 1700) idx.push(b);
    const i0 = idx[0], nbands = idx[idx.length - 1] - i0 + 1, lineBytes = S * B * bpe;
    const br = new Float32Array(L * S);
    const batch = 48;
    for (let l0 = 0; l0 < L; l0 += batch) {
      const lines = [];
      for (let l = l0; l < Math.min(L, l0 + batch); l++) {
        const a = off + l * lineBytes + i0 * S * bpe;
        lines.push(scan.src.read(a, a + nbands * S * bpe).then((buf) => [l, new Arr(buf)]));
      }
      for (const [l, v] of await Promise.all(lines)) {
        for (let c = 0; c < S; c++) {
          let s = 0, n = 0;
          for (const b of idx) { const x = v[(b - i0) * S + c]; if (ignore !== null && x === ignore) continue; s += x - bg[b * S + c]; n++; }
          br[l * S + c] = n ? s / n : NaN;
        }
      }
      if (onProgress) onProgress(Math.min(1, (l0 + batch) / L));
    }
    return br;
  }

  // ------------------------------------------------------------------ white strip and dishes
  function findStrip(br, L, S) {
    const top = [], cEnd = Math.min(364, S);
    for (let r = 0; r < Math.min(450, L); r++) top.push(nanmedian(br.subarray(r * S + 20, r * S + cEnd)));
    const thr = 0.5 * (percentile(top, 95) + percentile(top, 40));
    let best = null, start = -1;
    for (let r = 0; r <= top.length; r++) {
      const hi = r < top.length && top[r] > thr;
      if (hi && start < 0) start = r;
      if (!hi && start >= 0) { if (!best || r - start > best[1] - best[0] + 1) best = [start, r - 1]; start = -1; }
    }
    if (!best || best[1] - best[0] < 40) throw new Error("Couldn't find the white reference strip in the first 450 lines of the scan. The app needs the Spectralon strip at the start of every scan.");
    return { s0: best[0], s1: best[1] };
  }

  function findDishes(br, L, S, stripEnd, opts = {}) {
    const minScore = opts.minScore ?? 0.25, maxN = opts.maxN ?? 8, minSep = 230;
    const radii = []; for (let r = 88; r < 116; r += 3) radii.push(r);
    const below = stripEnd + 12;
    const tail = []; for (let k = below * S; k < L * S; k++) tail.push(Number.isFinite(br[k]) ? br[k] : 0);
    const p99 = percentile(tail, 99), med = percentile(tail, 50) / p99;
    const P = new Float64Array(L * (S + 1));                       // row prefix sums of the normalised image
    for (let r = 0; r < L; r++) {
      let acc = 0; P[r * (S + 1)] = 0;
      for (let c = 0; c < S; c++) { const v = r < below ? med : (Number.isFinite(br[r * S + c]) ? br[r * S + c] / p99 : 0); acc += v; P[r * (S + 1) + c + 1] = acc; }
    }
    const disc = (cx, cy, R, strict) => {                         // zero-padded sum over d <= R (or d < R)
      let s = 0;
      for (let dy = -R; dy <= R; dy++) {
        const y = cy + dy; if (y < 0 || y >= L) continue;
        const v = R * R - dy * dy, w = strict ? (v >= 1 ? isqrt(v - 1) : -1) : isqrt(v);
        if (w < 0) continue;
        const a = Math.max(0, cx - w), b = Math.min(S, cx + w + 1);
        if (b > a) s += P[y * (S + 1) + b] - P[y * (S + 1) + a];
      }
      return s;
    };
    const count = (R, strict) => { let n = 0; for (let dy = -R; dy <= R; dy++) { const v = R * R - dy * dy; const w = strict ? (v >= 1 ? isqrt(v - 1) : -1) : isqrt(v); if (w >= 0) n += 2 * w + 1; } return n; };
    const K = radii.map((r) => ({ r, na: count(r - 8, false), nb: count(r + 12, false) - count(r + 2, true) }));
    const resp = (cx, cy) => {
      let best = -Infinity, rb = 0;
      for (const k of K) {
        const v = disc(cx, cy, k.r - 8, false) / k.na - (disc(cx, cy, k.r + 12, false) - disc(cx, cy, k.r + 2, true)) / k.nb;
        if (v > best) { best = v; rb = k.r; }
      }
      return [best, rb];
    };
    const coarse = [];
    for (let cy = below + 60; cy < L; cy += 4) for (let cx = 0; cx < S; cx += 4) coarse.push([resp(cx, cy)[0], cx, cy]);
    coarse.sort((a, b) => b[0] - a[0]);
    const found = [];
    for (const [, x0, y0] of coarse) {
      if (found.length >= maxN) break;
      if (found.some((d) => (d.cx - x0) ** 2 + (d.cy - y0) ** 2 < minSep * minSep)) continue;
      let best = [-Infinity, 0, 0, 0];
      for (let cy = Math.max(below + 60, y0 - 6); cy <= Math.min(L - 1, y0 + 6); cy++)
        for (let cx = Math.max(0, x0 - 6); cx <= Math.min(S - 1, x0 + 6); cx++) {
          const [v, r] = resp(cx, cy); if (v > best[0]) best = [v, cx, cy, r];
        }
      if (found.some((d) => (d.cx - best[1]) ** 2 + (d.cy - best[2]) ** 2 < minSep * minSep)) continue;
      if (best[0] < minScore) break;
      found.push({ cx: best[1], cy: best[2], r: best[3], score: best[0] });
    }
    return found.sort((a, b) => a.cy - b.cy);
  }

  // ------------------------------------------------------------------ white reference (per across-track column)
  async function buildWhite(scan, strip, pipe, onProgress) {
    const { L, S, B } = scan;
    const cx = (S - 1) / 2, cy = (strip.s0 + strip.s1) / 2, ax = (S - 1) / 2 - 1, ay = (strip.s1 - strip.s0) / 2 - pipe.strip_inset_rows;
    const r0 = Math.max(0, Math.trunc(cy - ay)), r1 = Math.min(L, Math.trunc(cy + ay));
    const c0 = Math.max(0, Math.trunc(cx - ax)), c1 = Math.min(S, Math.trunc(cx + ax));
    const blk = await readBlock(scan, r0, r1, c0, c1, onProgress), W = c1 - c0, R = r1 - r0;
    const Wt = new Float64Array(S * B).fill(NaN);                  // [col][band]
    const col = new Float64Array(R);
    for (let b = 0; b < B; b++) for (let c = 0; c < W; c++) {
      for (let r = 0; r < R; r++) col[r] = blk[(r * B + b) * W + c];
      Wt[(c0 + c) * B + b] = nanmedian(col);
    }
    // whole columns far below the rest are repaired from their neighbours
    const ref = new Float64Array(B);
    for (let b = 0; b < B; b++) { const v = []; for (let c = c0; c < c1; c++) v.push(Wt[c * B + b]); ref[b] = nanmedian(v); }
    const bad = [], good = [];
    for (let c = 0; c < S; c++) {
      const v = []; for (let b = 0; b < B; b++) v.push(Wt[c * B + b] / Math.max(ref[b], 1e-9));
      const lvl = nanmedian(v);
      (!Number.isFinite(lvl) || lvl < pipe.bad_column_frac ? bad : good).push(c);
    }
    if (bad.length && good.length > 2) for (let b = 0; b < B; b++) for (const c of bad) {
      let v;
      if (c <= good[0]) v = Wt[good[0] * B + b];
      else if (c >= good[good.length - 1]) v = Wt[good[good.length - 1] * B + b];
      else { let k = 1; while (good[k] < c) k++; const g0 = good[k - 1], g1 = good[k];
             v = Wt[g0 * B + b] + (Wt[g1 * B + b] - Wt[g0 * B + b]) * (c - g0) / (g1 - g0); }
      Wt[c * B + b] = v;
    }
    // single detector pixels that disagree with their column neighbours (median of 9, edges repeated)
    const badpix = new Uint8Array(S * B);
    const win = new Float64Array(9);
    for (let b = 0; b < B; b++) for (let c = 0; c < S; c++) {
      for (let k = -4; k <= 4; k++) { const cc = Math.min(S - 1, Math.max(0, c + k)); const x = Wt[cc * B + b]; win[k + 4] = Number.isFinite(x) ? x : 0; }
      const local = Float64Array.from(win).sort()[4], w = Wt[c * B + b];
      if (!Number.isFinite(w) || w <= 0 || Math.abs(w / Math.max(local, 1e-9) - 1) > pipe.bad_pixel_tol) badpix[c * B + b] = 1;
    }
    let nb = 0; for (const x of badpix) nb += x;
    return { W: Wt, badpix, rows: [r0, r1], cols: [c0, c1], repairedColumns: bad.length, badPixels: nb };
  }

  // ------------------------------------------------------------------ dish mask (same rules as the notebooks)
  function dishMask(br, L, S, dish, pipe) {
    const R0 = dish.r - pipe.dish_inset_px, cx = Math.round(dish.cx), cy = Math.round(dish.cy);
    const pad = R0 + 2, y0 = Math.max(0, cy - pad), y1 = Math.min(L, cy + pad + 1), x0 = Math.max(0, cx - pad), x1 = Math.min(S, cx + pad + 1);
    const H = y1 - y0, Wd = x1 - x0;
    const raw = new Uint8Array(H * Wd);
    for (let y = 0; y < H; y++) for (let x = 0; x < Wd; x++) { const dx = x0 + x - cx, dy = y0 + y - cy; raw[y * Wd + x] = dx * dx + dy * dy < (R0 + 0.5) ** 2 ? 1 : 0; }
    const m = new Uint8Array(H * Wd);                               // erosion with the 9x9 ellipse
    for (let y = 0; y < H; y++) for (let x = 0; x < Wd; x++) {
      let ok = raw[y * Wd + x];
      for (let i = 0; ok && i < 9; i++) for (let j = 0; j < 9; j++) {
        if (!SE9[i][j]) continue;
        const yy = y + i - 4, xx = x + j - 4, iy = y0 + yy, ix = x0 + xx;
        if (iy < 0 || iy >= L || ix < 0 || ix >= S) continue;      // like cv2.erode: outside the image counts as set
        if (yy < 0 || yy >= H || xx < 0 || xx >= Wd || !raw[yy * Wd + xx]) { ok = 0; break; }
      }
      m[y * Wd + x] = ok;
    }
    const at = (y, x) => br[(y0 + y) * S + x0 + x];
    const vals = []; for (let k = 0; k < H * Wd; k++) if (m[k]) vals.push(at(Math.floor(k / Wd), k % Wd));
    if (vals.length >= 30) {
      const thr = pipe.dark_frac * nanmedian(vals);
      for (let k = 0; k < H * Wd; k++) if (m[k] && !(at(Math.floor(k / Wd), k % Wd) > thr)) m[k] = 0;
      const v2 = []; for (let k = 0; k < H * Wd; k++) if (m[k]) v2.push(at(Math.floor(k / Wd), k % Wd));
      if (v2.length > 50) {
        const hi = percentile(v2, pipe.glare_pct);
        const glare = (y, x) => { const yy = y0 + y, xx = x0 + x; return yy >= 0 && yy < L && xx >= 0 && xx < S && br[yy * S + xx] > hi; };
        const kill = [];
        for (let y = 0; y < H; y++) for (let x = 0; x < Wd; x++) if (m[y * Wd + x]) {
          outer: for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (glare(y + dy, x + dx)) { kill.push(y * Wd + x); break outer; }
        }
        for (const k of kill) m[k] = 0;
      }
    }
    let n = 0, nraw = 0; for (let k = 0; k < H * Wd; k++) { n += m[k]; nraw += raw[k]; }
    return { m, y0, x0, H, W: Wd, n, keep: n / Math.max(nraw, 1) };
  }

  // ------------------------------------------------------------------ models
  function prepareModels(models) {
    const wl = models.wavelengths, sel = [];
    wl.forEach((w, i) => { const r = Math.round(w); if (r >= models.band_min && r <= models.band_max) sel.push(i); });
    const n = sel.length, lam = Float64Array.from({ length: n }, (_, i) => -1 + (2 * i) / (n - 1));
    for (const F of Object.values(models.families)) {
      if (!F.emsc) continue;
      const cols = [new Float64Array(n).fill(1), Float64Array.from(F.emsc.mean), Float64Array.from(F.emsc.chicory_direction), lam, lam.map((x) => x * x)];
      const G = cols.map((a) => cols.map((b) => a.reduce((s, x, i) => s + x * b[i], 0)));   // 5x5 normal matrix
      const inv = invert(G);
      F._pinv = inv.map((row) => Float64Array.from({ length: n }, (_, k) => row.reduce((s, g, j) => s + g * cols[j][k], 0)));
      F._lam = lam;
    }
    models._sel = sel; models._n = n;
    return models;
  }
  function invert(A) {
    const n = A.length, M = A.map((r, i) => [...r, ...Array.from({ length: n }, (_, j) => (i === j ? 1 : 0))]);
    for (let c = 0; c < n; c++) {
      let p = c; for (let r = c + 1; r < n; r++) if (Math.abs(M[r][c]) > Math.abs(M[p][c])) p = r;
      [M[c], M[p]] = [M[p], M[c]];
      const d = M[c][c]; for (let j = 0; j < 2 * n; j++) M[c][j] /= d;
      for (let r = 0; r < n; r++) if (r !== c) { const f = M[r][c]; for (let j = 0; j < 2 * n; j++) M[r][j] -= f * M[c][j]; }
    }
    return M.map((r) => r.slice(n));
  }
  const dot = (a, b) => { let s = 0; for (let i = 0; i < a.length; i++) s += a[i] * b[i]; return s; };
  function emsc(z, F) {
    const c = F._pinv.map((row) => dot(row, z)), lam = F._lam;   // a, b, h, d, e
    return z.map((x, i) => (x - c[0] - c[3] * lam[i] - c[4] * lam[i] * lam[i]) / c[1]);
  }
  function predictUnit(z, F) {
    const x = F.emsc ? emsc(z, F) : z;
    return dot(x, F.model.w) + F.model.w0;
  }

  // ------------------------------------------------------------------ one dish, end to end
  async function analyseDish(scan, br, white, dish, models, onProgress) {
    const pipe = models.pipeline, { S, B, L } = scan, sel = models._sel, n = models._n, Rc = models.white_certificate;
    const mk = dishMask(br, L, S, dish, pipe);
    if (mk.n < 500) throw new Error("Too little clean powder in this dish to analyse (check that the dish is in focus and well lit).");
    let ys0 = Infinity, ys1 = -1, xs0 = Infinity, xs1 = -1;
    for (let y = 0; y < mk.H; y++) for (let x = 0; x < mk.W; x++) if (mk.m[y * mk.W + x]) { ys0 = Math.min(ys0, y); ys1 = Math.max(ys1, y); xs0 = Math.min(xs0, x); xs1 = Math.max(xs1, x); }
    const r0 = mk.y0 + ys0, r1 = mk.y0 + ys1 + 1, c0 = mk.x0 + xs0, c1 = mk.x0 + xs1 + 1, H = r1 - r0, Wd = c1 - c0;
    const blk = await readBlock(scan, r0, r1, c0, c1, onProgress);
    const mask = (y, x) => mk.m[(r0 - mk.y0 + y) * mk.W + (c0 - mk.x0 + x)];
    const P = pipe.patch, patches = [];
    const [lo, hi] = pipe.refl_range;
    for (let i = 0; i + P <= H; i += P) for (let j = 0; j + P <= Wd; j += P) {
      let nm = 0; for (let y = i; y < i + P; y++) for (let x = j; x < j + P; x++) nm += mask(y, x);
      if (nm / (P * P) < pipe.min_valid) continue;
      const spec = new Float64Array(B); let ok = true;
      for (let b = 0; b < B && ok; b++) {
        let s = 0, cnt = 0;
        for (let y = i; y < i + P; y++) for (let x = j; x < j + P; x++) {
          if (!mask(y, x)) continue;
          const c = c0 + x;
          if (white.badpix[c * B + b]) continue;
          const w = white.W[c * B + b];
          if (!Number.isFinite(w)) continue;
          const R = blk[(y * B + b) * Wd + x] / Math.max(w, 1e-9) * Rc[b];
          if (!(R >= lo && R <= hi)) continue;
          s += R; cnt++;
        }
        if (!cnt) ok = false; else spec[b] = s / cnt;
      }
      if (ok) patches.push({ gi: i / P, gj: j / P, row: r0 + i + P / 2, col: c0 + j + P / 2, R: spec });
    }
    if (patches.length < 10) throw new Error("Fewer than 10 clean 12×12-pixel patches in this dish; the app needs more powder surface to give a result.");
    // absorbance + offset on 1000-2450 nm
    for (const p of patches) {
      const z = new Float64Array(n); let m = 0;
      for (let k = 0; k < n; k++) { z[k] = Math.log10(1 / Math.max(p.R[sel[k]], 1e-3)); m += z[k]; }
      m /= n; for (let k = 0; k < n; k++) z[k] -= m;
      p.z = z;
    }
    // 1. mixture type: PCA-LDA class scores on 3 x 3 blocks of patches, softmax, averaged over the dish
    const C = models.classifier, K = C.classes.length;
    const cblocks = new Map();
    for (const p of patches) { const key = `${Math.floor(p.gi / 3)},${Math.floor(p.gj / 3)}`; if (!cblocks.has(key)) cblocks.set(key, []); cblocks.get(key).push(p); }
    const pm = new Float64Array(K);
    for (const ps of cblocks.values()) {
      const z = new Float64Array(n); for (const p of ps) for (let k = 0; k < n; k++) z[k] += p.z[k] / ps.length;
      const sc = C.W.map((w, k) => dot(w, z) + C.b[k]), mx = Math.max(...sc);
      const ex = sc.map((v) => Math.exp(v - mx)), tot = ex.reduce((a, b) => a + b, 0);
      ex.forEach((v, k) => { pm[k] += v / tot / cblocks.size; });
    }
    const probs = {}; C.classes.forEach((c, k) => { probs[c] = pm[k]; });
    const famKey = C.classes[pm.indexOf(Math.max(...pm))];
    const F = models.families[famKey];
    // 2. trim the 10 % least typical patches (residual of the family's 4-component reference)
    const T = F.trim, mu = T.mean;
    for (const p of patches) {
      const x = p.z.map((v, k) => v - mu[k]);
      const t = T.rotations.map((r) => dot(r, x));
      let q = 0; for (let k = 0; k < n; k++) { let rec = 0; for (let a = 0; a < t.length; a++) rec += t[a] * T.loadings[a][k]; q += (x[k] - rec) ** 2; }
      p.q = q;
    }
    const order = patches.map((p, i) => [p.q, i]).sort((a, b) => a[0] - b[0]);
    order.forEach(([, i], r) => { patches[i].kept = (r + 1) / patches.length <= T.keep_frac; });
    const kept = patches.filter((p) => p.kept);
    // 3. super-patches: 3 x 3 blocks of neighbouring patches, the model's input scale (~8 patches)
    const blocks = new Map();
    for (const p of kept) { const key = `${Math.floor(p.gi / 3)},${Math.floor(p.gj / 3)}`; if (!blocks.has(key)) blocks.set(key, []); blocks.get(key).push(p); }
    const units = [];
    for (const [key, ps] of blocks) {
      const z = new Float64Array(n); for (const p of ps) for (let k = 0; k < n; k++) z[k] += p.z[k] / ps.length;
      units.push({ key, n: ps.length, row: ps.reduce((s, p) => s + p.row, 0) / ps.length, col: ps.reduce((s, p) => s + p.col, 0) / ps.length,
                   patches: ps.map((p) => [p.row, p.col]), pred: predictUnit(z, F) });
    }
    const wsum = units.reduce((s, u) => s + u.n, 0);
    const adulterant = units.reduce((s, u) => s + u.n * u.pred, 0) / wsum;
    const big = units.filter((u) => u.n >= 5).map((u) => u.pred);
    const mean = big.reduce((s, v) => s + v, 0) / Math.max(big.length, 1);
    const spread = big.length > 2 ? Math.sqrt(big.reduce((s, v) => s + (v - mean) ** 2, 0) / (big.length - 1)) : NaN;
    // 4. does the dish look like the training dishes of this family?
    const zbar = new Float64Array(n); for (const p of kept) for (let k = 0; k < n; k++) zbar[k] += p.z[k] / kept.length;
    const D = F.domain, xd = zbar.map((v, k) => v - D.pca_mean[k]), sc = D.components.map((c) => dot(c, xd));
    let qd = 0; for (let k = 0; k < n; k++) { let rec = 0; for (let a = 0; a < sc.length; a++) rec += sc[a] * D.components[a][k]; qd += (xd[k] - rec) ** 2; }
    const t2 = sc.reduce((s, v, a) => s + (v * v) / D.variances[a], 0);
    const meanR = new Float64Array(B); for (const p of kept) for (let b = 0; b < B; b++) meanR[b] += p.R[b] / kept.length;
    return { family: famKey, probs, adulterant, spread, units,
             domainQ: qd / D.q_ref, domainT2: t2 / D.t2_ref, nPatches: patches.length, nKept: kept.length,
             maskPixels: mk.n, maskKeep: mk.keep, meanReflectance: Array.from(meanR), dish };
  }

  // ------------------------------------------------------------------ result wording: composition, limits, warnings
  function interpret(res, models) {
    const F = models.families[res.family], rm = F.error.loso_pooled_rmsep, lod = 2 * rm, pm = 2 * rm;
    const conf = Math.max(...Object.values(res.probs)), a = res.adulterant;
    const pct = Math.min(100, Math.max(0, a));
    const mixedBase = F.base.includes("+");                      // arabica + robusta base: split not measured
    const comp = { robusta: 0, arabica: 0, chicory: 0, coffee: 100 - pct };
    comp[F.adulterant] = pct; if (!mixedBase) comp[F.base] = 100 - pct;
    const detected = a >= lod;
    const typeLabel = detected ? F.name : (mixedBase ? "Arabica + robusta, no chicory" : `Pure ${F.base}`);
    const warnings = [];
    if (conf < 0.8) warnings.push({ level: "warn", text: `Mixture type is uncertain (${(conf * 100).toFixed(0)} % confident). The sample may be a mixture the app doesn't model.` });
    if (a > 50 + lod) warnings.push({ level: "warn", text: `Above the calibrated range: the models were trained on 0–50 % ${F.adulterant}, so ${pct.toFixed(0)} % is an extrapolation.` });
    if (a < -lod) warnings.push({ level: "warn", text: `Below zero (${a.toFixed(1)} %): the spectrum doesn't fit this mixture well.` });
    const dom = Math.max(res.domainQ, res.domainT2);
    if (dom > 5) warnings.push({ level: "bad", text: `This sample looks unlike every dish the models were trained on (score ${dom.toFixed(1)}; typical dishes stay below 2). Treat the numbers as indicative only.` });
    else if (dom > 2) warnings.push({ level: "warn", text: `This sample is somewhat unusual compared with the training dishes (score ${dom.toFixed(1)}; typical dishes stay below 2).` });
    return { typeLabel, familyName: F.name, confidence: conf, composition: comp, adulterantName: F.adulterant, baseName: F.base,
             mixedBase, detected, lod, plusMinus: pm, rmsep: rm, warnings, model: F.model, rangeTop: 50 };
  }

  return { parseHeader, openScan, readBlock, brightnessImage, findStrip, findDishes, buildWhite, dishMask, prepareModels,
           analyseDish, interpret, percentile };
});
