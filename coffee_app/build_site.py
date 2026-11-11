"""Compose the redesigned Coffee Adulterant Detector page from the current index.html:
reuses the three article bodies, the scan view and the analysis JS; new design system, home, learn hub, article pages."""
import os
import re, sys
from pathlib import Path

APP = Path(os.environ.get("COFFEE_DATA", str(Path(__file__).resolve().parents[1]))) / "coffee_app"
cur = (APP / "index_v6_beans_home.html").read_text()
L = cur.split("\n")

def between(start_pat, end_pat, after=0):
    a = cur.index(start_pat, after); b = cur.index(end_pat, a); return cur[a:b]

# ---------------------------------------------------------------- reused pieces
def part_inner(pid):
    s = cur.index(f'<section class="part" id="{pid}">'); s = cur.index(">", s) + 1
    e = cur.index("</section>", s)
    body = cur[s:e]
    body = re.sub(r'\s*<div class="part-label">.*?</div>', "", body, count=1, flags=re.S)
    return body
p1, p2, p3 = part_inner("part1"), part_inner("part2"), part_inner("part3")
p2 = p2.replace('<svg viewBox="0 0 420 300" role="img" aria-label="A hyperspectral data cube', '<svg viewBox="0 0 456 300" role="img" aria-label="A hyperspectral data cube')
assert "0 0 456 300" in p2
p3 = re.sub(r'\s*<div class="card endcta">.*?</a>\s*</div>', "", p3, count=1, flags=re.S)
p1 = p1.replace('<div class="ingredients">', '<div class="ingredients" data-toc="Arabica, robusta and chicory">', 1)
p3 = p3.replace('<div class="card">', '<div class="card" data-toc="Six techniques compared">', 1)
assert p1.count("data-toc") == 1 and p3.count("data-toc") == 1
assert "endcta" not in p3
scan_view = between("  <!-- =========================================================== SCAN -->", '  <div class="wrap" id="siteFooter">')
old_css = between("/* ---------------- learn: blog */", "</style>")
js = between("<script>\n(() => {", "</script>")[len("<script>\n"):]

def words(html): return len(re.sub(r"<[^>]+>", " ", html).split())
mins = {k: max(2, round(words(v) / 220)) for k, v in (("coffee", p1), ("hsi", p2), ("methods", p3))}

# ---------------------------------------------------------------- JS edits
a = js.index("  // ---------------------------------------------------------------- pages")
b = js.index("  // ---------------------------------------------------------------- learn: legal scale")
js = js[:a] + "@@ROUTER@@\n" + js[b:]
js = js.replace('const rerender = () => { if (!$("viewLearn").hidden) drawLearnChart();',
                'const rerender = () => { if (!$("viewHsi").hidden) drawLearnChart(); bean.redraw(); for (const w of Object.values(WIRES)) w.redraw();')
assert "w.redraw()" in js
js = js.replace("  route();\n})();", "  route();\n})();")

ROUTER = r'''  // ---------------------------------------------------------------- pages (hash routes)
  const ROUTES = { home: "viewHome", learn: "viewLearn", coffee: "viewCoffee", hsi: "viewHsi", methods: "viewMethods", scan: "viewScan" };
  const NAVKEY = { home: "home", learn: "learn", coffee: "learn", hsi: "learn", methods: "learn", scan: "scan" };
  const TITLES = { home: "Coffee Adulterant Detector", learn: "Learn · Coffee Adulterant Detector",
                   coffee: "Coffee and what gets mixed into it", hsi: "Seeing chemistry with HSI", methods: "How adulteration is detected",
                   scan: "Scan a sample · Coffee Adulterant Detector" };
  const menuBtn = $("menuBtn"), navMenu = $("navMenu");
  const closeMenu = () => { document.body.classList.remove("menu-open"); menuBtn.setAttribute("aria-expanded", "false"); };
  menuBtn.addEventListener("click", () => { const o = document.body.classList.toggle("menu-open"); menuBtn.setAttribute("aria-expanded", String(o)); });
  function route() {
    const h = (location.hash || "#home").slice(1), v = h in ROUTES ? h : "home";
    for (const [k, id] of Object.entries(ROUTES)) $(id).hidden = k !== v;
    document.body.dataset.view = v; document.title = TITLES[v];
    document.querySelectorAll("[data-nav]").forEach((x) => { if (x.dataset.nav === NAVKEY[v]) x.setAttribute("aria-current", "page"); else x.removeAttribute("aria-current"); });
    closeMenu();
    if (v === "home") { fitWordmark(); bean.start(); } else bean.stop();
    for (const [k, w] of Object.entries(WIRES)) { if (k === v) w.start(); else w.stop(); }
    fitWords();
    if (v === "coffee") drawLegal();
    if (v === "hsi") drawLearnChart();
    if (v === "learn") drawCovers();
    if (v === "scan") { drawScan(); if (S && S.selected !== null && !$("resultCard").hidden) renderResult(S.selected); }
    readProgress();
  }
  window.addEventListener("hashchange", () => { route(); window.scrollTo(0, 0); });

  // ---------------------------------------------------------------- reading progress on article pages
  const readbar = $("readbar");
  function readProgress() {
    const v = document.body.dataset.view;
    if (!["coffee", "hsi", "methods"].includes(v)) { readbar.style.width = "0"; return; }
    const max = document.documentElement.scrollHeight - innerHeight;
    readbar.style.width = `${max > 0 ? Math.min(100, (scrollY / max) * 100) : 100}%`;
  }
  addEventListener("scroll", readProgress, { passive: true });

  // ---------------------------------------------------------------- home: giant wordmark sized to the width
  function fitWordmark() {
    const el = $("wordmark"); if (!el || $("viewHome").hidden) return;
    el.style.fontSize = "100px";
    const w = el.scrollWidth, avail = el.parentElement.clientWidth * 0.985;
    el.style.fontSize = `${(100 * avail) / w}px`;
    bean.redraw();
  }
  addEventListener("resize", fitWordmark);
  document.fonts && document.fonts.ready.then(fitWordmark);

  // ---------------------------------------------------------------- home: wireframe coffee bean swept by a push-broom scan line
  // The readout cycles through the app's real outputs on three scanned dishes (training_dish_predictions.csv).
  const DEMO = [["ROBUSTA + CHICORY", "30.9", "30"], ["ARABICA + CHICORY", "24.8", "25"], ["ARABICA + ROBUSTA + CHICORY", "44.5", "45"]];
  function beanMesh(NU, NV) {                          // ellipsoid with a flat face and an S-shaped crease
    const P = [], GROOVE = [], A = 0.74, B = 0.56;
    for (let i = 0; i <= NU; i++) {
      const u = (i / NU) * Math.PI, row = [];
      for (let j = 0; j < NV; j++) {
        const v = (j / NV) * 2 * Math.PI, s = Math.sin(u);
        let x = A * s * Math.cos(v), y = B * s * Math.sin(v);
        const z = Math.cos(u) * 1.02;
        if (y > 0) {
          y *= 0.5;
          const cx = 0.16 * Math.sin(2 * u) * A, w = 0.12 * A;
          y -= 0.17 * s * Math.exp(-((x - cx) ** 2) / (w * w));
        }
        const wob = 1 + 0.03 * Math.sin(3 * v + 2 * u) + 0.025 * Math.sin(5 * u + v);
        row.push([x * wob, y * wob, z * wob]);
      }
      P.push(row);
    }
    for (let i = 0; i <= 40; i++) {                    // the bottom of the crease, drawn as a bold centre line
      const u = Math.PI * (0.09 + 0.82 * i / 40), s = Math.sin(u), cx = 0.16 * Math.sin(2 * u) * A;
      const r = Math.min(0.99, Math.abs(cx / (A * s)));
      GROOVE.push([cx, 0.5 * B * s * Math.sqrt(1 - r * r) - 0.17 * s, Math.cos(u) * 1.02]);
    }
    return { P, GROOVE };
  }
  const bean = (() => {
    const cv = $("beanCanvas"), ctx = cv.getContext("2d");
    const NU = 46, NV = 52, { P, GROOVE } = beanMesh(NU, NV);
    let clock = 0, tx = 0, ty = 0, mx = 0, my = 0, raf = 0, running = false, last = 0, phase = 0, demo = 0, box = null;
    const SWEEP = 3800, HOLD = 3000, CYCLE = SWEEP + HOLD;
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (reduce) phase = SWEEP + 1;                          // still frame: fully scanned, readout showing
    addEventListener("pointermove", (e) => { mx = (e.clientX / innerWidth - 0.5); my = (e.clientY / innerHeight - 0.5); }, { passive: true });
    function frame(t) {
      const dt = last ? Math.min(50, t - last) : 16; last = t;
      clock += dt; phase += dt;
      if (phase >= CYCLE) { phase -= CYCLE; demo = (demo + 1) % DEMO.length; }
      tx += (mx * 0.5 - tx) * 0.05; ty += (my * 0.4 - ty) * 0.05;
      draw();
      if (running && !reduce) raf = requestAnimationFrame(frame);
    }
    function draw() {
      const dpr = devicePixelRatio || 1, W = cv.clientWidth, H = cv.clientHeight;
      if (!W) return;
      if (cv.width !== Math.round(W * dpr) || cv.height !== Math.round(H * dpr)) { cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); box = null; }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
      // face-on to the crease, rocking gently so the S-groove stays in view
      const roll = 0.5 * Math.sin(clock * 0.00045), turn = 0.3 * Math.sin(clock * 0.00029 + 1);
      const cr = Math.cos(roll), sr = Math.sin(roll), ax = -1.15 + ty, ay = turn + tx, az = 0.6;
      const cax = Math.cos(ax), sax = Math.sin(ax), cay = Math.cos(ay), say = Math.sin(ay), caz = Math.cos(az), saz = Math.sin(az);
      const sc = Math.min(W * 0.36, (H - 130) / 2.6), ox = W / 2, oy = H / 2 - 18;
      const project = (x, y, z) => {
        const xa = x * cr - y * sr, ya = x * sr + y * cr;                  // roll about the bean's long axis
        const yb = ya * cax - z * sax, zb = ya * sax + z * cax;            // tilt towards the viewer
        const xc = xa * cay + zb * say, zc = -xa * say + zb * cay;         // turn
        const xd = xc * caz - yb * saz, yd = xc * saz + yb * caz;          // lean on the page
        const f = 3.4 / (3.4 + zc);
        return [ox + xd * f * sc, oy + yd * f * sc, zc];
      };
      let x0 = 1e9, x1_ = -1e9, y0 = 1e9, y1_ = -1e9;
      const Q = P.map((row) => row.map(([x, y, z]) => {
        const q = project(x, y, z), X = q[0], Y = q[1];
        if (X < x0) x0 = X; if (X > x1_) x1_ = X; if (Y < y0) y0 = Y; if (Y > y1_) y1_ = Y;
        return q;
      }));
      const k = box ? 0.08 : 1;                                             // ease the frame so it does not jitter as the bean rolls
      box = box ? box.map((v, i) => v + ([x0, y0, x1_, y1_][i] - v) * k) : [x0, y0, x1_, y1_];
      const [bx0, by0, bx1, by1] = box, pad = 16;
      const scanning = phase < SWEEP, s = scanning ? phase / SWEEP : 1;
      const ease = s < 0.5 ? 2 * s * s : 1 - (-2 * s + 2) ** 2 / 2;
      const lineY = by0 - pad + ease * (by1 - by0 + 2 * pad);
      const paths = { back: new Path2D(), front: new Path2D(), backS: new Path2D(), frontS: new Path2D(), hot: new Path2D() };
      const seg = (a, b) => {
        const my_ = (a[1] + b[1]) / 2, isBack = a[2] + b[2] > 0;
        const p = scanning && Math.abs(my_ - lineY) < 9 && !isBack ? paths.hot
                : (scanning ? my_ < lineY : true) ? (isBack ? paths.backS : paths.frontS) : (isBack ? paths.back : paths.front);
        p.moveTo(a[0], a[1]); p.lineTo(b[0], b[1]);
      };
      for (let i = 0; i <= NU; i++) for (let j = 0; j < NV; j++) {
        const a = Q[i][j], r = Q[i][(j + 1) % NV];
        if (i > 0 && i < NU) seg(a, r);
        if (i < NU) { seg(a, Q[i + 1][j]); if (i % 2 === 0) seg(a, Q[i + 1][(j + 1) % NV]); }
      }
      const acc = css("--accent"), ink = css("--ink"), roast = css("--coffee-2"), mut = css("--muted");
      const st = (p, col, a, w) => { ctx.strokeStyle = col; ctx.globalAlpha = a; ctx.lineWidth = w; ctx.stroke(p); };
      st(paths.back, acc, 0.22, 0.6); st(paths.front, acc, 0.85, 0.75);       // not yet scanned: roast-orange wireframe
      st(paths.backS, roast, 0.16, 0.6); st(paths.frontS, ink, 0.62, 0.7);    // scanned: espresso
      st(paths.hot, acc, 1, 1.6);
      ctx.globalAlpha = 1; ctx.lineCap = "round";                       // the S-shaped centre cut, drawn bold so it reads as a coffee bean
      const G = GROOVE.map(([x, y, z]) => project(x, y, z));
      for (let i = 1; i < G.length; i++) {
        const a = G[i - 1], b = G[i], done = !scanning || (a[1] + b[1]) / 2 < lineY;
        ctx.strokeStyle = done ? ink : acc; ctx.lineWidth = 2.4; ctx.beginPath(); ctx.moveTo(a[0], a[1]); ctx.lineTo(b[0], b[1]); ctx.stroke();
      }
      ctx.globalAlpha = 1;
      if (scanning) {                                                         // the illuminated line under the camera
        const lx0 = bx0 - pad - 26, lx1 = bx1 + pad + 26, g = ctx.createLinearGradient(0, lineY - 34, 0, lineY);
        g.addColorStop(0, acc + "00"); g.addColorStop(1, acc);
        ctx.globalAlpha = 0.14; ctx.fillStyle = g; ctx.fillRect(lx0, lineY - 34, lx1 - lx0, 34);
        ctx.globalAlpha = 1; ctx.fillStyle = acc; ctx.fillRect(lx0, lineY - 0.75, lx1 - lx0, 1.5);
      }
      ctx.fillStyle = ink;                                                    // selection handles around the dish
      for (const [hx, hy] of [[bx0 - pad, by0 - pad], [bx1 + pad, by0 - pad], [bx0 - pad, by1 + pad], [bx1 + pad, by1 + pad]]) ctx.fillRect(hx - 4, hy - 4, 8, 8);
      const fs = Math.max(10.5, Math.min(13, W / 46));
      const text = (str, x, y, size, weight, col, wide) => {
        ctx.font = `${weight} ${size}px Archivo, "Helvetica Neue", Arial, sans-serif`;
        if ("fontStretch" in ctx) ctx.fontStretch = wide ? "expanded" : "normal";
        if ("letterSpacing" in ctx) ctx.letterSpacing = wide ? "0.06em" : "0px";
        const w = ctx.measureText(str).width, X = Math.max(4, Math.min(W - w - 4, x));
        ctx.fillStyle = col; ctx.fillText(str, X, y); return w;
      };
      ctx.textBaseline = "alphabetic";
      text(scanning ? `SCANNING  ${Math.round(s * 100)} %` : "SCAN COMPLETE", bx0 - pad - 4, by0 - pad - 14 - fs * 1.45, fs, 700, ink, true);
      text("SWIR · 1000–2450 nm · 288 bands", bx0 - pad - 4, by0 - pad - 12, fs, 500, mut, false);
      if (!scanning) {
        const [type, val, lab] = DEMO[demo], y = by1 + pad + 18 + fs, fade = reduce ? 1 : Math.min(1, (phase - SWEEP) / 350);
        ctx.globalAlpha = fade;
        text(type, bx0 - pad - 4, y, fs, 700, ink, true);
        const w = text(`chicory ${val} %`, bx0 - pad - 4, y + fs * 2.3, fs * 1.9, 750, acc, false);
        text(`dish labelled ${lab} %`, bx0 - pad - 4 + w + 12, y + fs * 2.3, fs, 500, mut, false);
        ctx.globalAlpha = 1;
      }
    }
    return { start() { if (!running) { running = true; last = 0; raf = requestAnimationFrame(frame); } },
             stop() { running = false; cancelAnimationFrame(raf); }, redraw: draw };
  })();
  addEventListener("resize", () => bean.redraw());


  // ---------------------------------------------------------------- inner pages: a small wireframe object per page, swept once by the scan line
  // Segments flagged "true" stay roast-orange after the sweep, like chicory showing up on the app's map.
  const REDUCE = matchMedia("(prefers-reduced-motion: reduce)").matches;
  function gridSegs(P) {
    const pts = [], segs = [], NV = P[0].length, NU = P.length - 1, id = (i, j) => i * NV + j;
    P.forEach((row) => row.forEach((q) => pts.push(q)));
    for (let i = 0; i <= NU; i++) for (let j = 0; j < NV; j++) {
      if (i > 0 && i < NU) segs.push([id(i, j), id(i, (j + 1) % NV)]);
      if (i < NU) { segs.push([id(i, j), id(i + 1, j)]); if (i % 2 === 0) segs.push([id(i, j), id(i + 1, (j + 1) % NV)]); }
    }
    return { pts, segs };
  }
  const MODELS = {
    bean(mixed) {
      const { P, GROOVE } = beanMesh(30, 34), m = gridSegs(P);
      for (const sg of m.segs) { const q = m.pts[sg[0]]; sg.push(mixed && Math.sin(4.1 * q[0] + 2 * q[1] + 0.7) * Math.cos(3.3 * q[2] + 1) > 0.42); }
      const g0 = m.pts.length; GROOVE.forEach((q) => m.pts.push(q));
      m.bold = GROOVE.slice(1).map((_, i) => [g0 + i, g0 + i + 1]);
      return m;
    },
    dish() {                                           // a petri dish of powder with a few chicory-rich patches
      const pts = [], segs = [], bold = [], add = (q) => pts.push(q) - 1;
      const spot = (q) => Math.sin(3.1 * q[0] + 1.3) * Math.cos(2.7 * q[2] - 0.4) > 0.45;
      const ring = (r, y, n, isBold) => {
        const ids = [];
        for (let j = 0; j < n; j++) { const a = (2 * Math.PI * j) / n; ids.push(add([r * Math.cos(a), y, r * Math.sin(a)])); }
        for (let j = 0; j < n; j++) { const sg = [ids[j], ids[(j + 1) % n]]; if (isBold) bold.push(sg); else segs.push([...sg, r < 0.97 && spot(pts[ids[j]])]); }
        return ids;
      };
      const top = ring(1, -0.14, 72, true), bot = ring(1, 0.14, 72, false);
      for (let j = 0; j < 72; j += 4) segs.push([top[j], bot[j], false]);
      const rings = [];
      for (let r = 0.12; r < 0.95; r += 0.118) rings.push(ring(r, 0.02, 48, false));
      for (let j = 0; j < 48; j += 2) for (let q = 0; q < rings.length - 1; q++) segs.push([rings[q][j], rings[q + 1][j], spot(pts[rings[q][j]])]);
      return { pts, segs, bold };
    },
  };
  function wire(id, model, o) {
    const cv = $(id), ctx = cv.getContext("2d");
    let clock = 0, last = 0, raf = 0, running = false, phase = 0;
    const SWEEP = o.sweep || 2200, HOLD = o.hold || 0;
    function frame(t) {
      const dt = last ? Math.min(50, t - last) : 16; last = t; clock += dt; phase += dt;
      if (o.loop && phase > SWEEP + HOLD) phase = 0;
      draw();
      if (running && !REDUCE) raf = requestAnimationFrame(frame);
    }
    function draw() {
      const dpr = devicePixelRatio || 1, W = cv.clientWidth, H = cv.clientHeight;
      if (!W || !H) return;
      if (cv.width !== Math.round(W * dpr) || cv.height !== Math.round(H * dpr)) { cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
      const sp = (o.spin0 || 0) + clock * (o.spin || 0), rk = (o.rock || 0) * Math.sin(clock * 0.00045);
      const c1 = Math.cos(sp), s1 = Math.sin(sp), c2 = Math.cos(rk), s2 = Math.sin(rk);
      const c3 = Math.cos(o.ax), s3 = Math.sin(o.ax), c4 = Math.cos(o.az || 0), s4 = Math.sin(o.az || 0);
      const sc = Math.min(W, H) * o.scale, ox = W / 2, oy = H / 2;
      let x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
      const Q = model.pts.map(([x, y, z]) => {
        const xa = x * c1 + z * s1, za = -x * s1 + z * c1;              // turntable spin about the object's own axis
        const xb = xa * c2 - y * s2, yb = xa * s2 + y * c2;              // gentle rock
        const yc = yb * c3 - za * s3, zc = yb * s3 + za * c3;            // tilt towards the viewer
        const xd = xb * c4 - yc * s4, yd = xb * s4 + yc * c4;            // lean on the page
        const f = 3.6 / (3.6 + zc), X = ox + xd * f * sc, Y = oy + yd * f * sc;
        if (X < x0) x0 = X; if (X > x1) x1 = X; if (Y < y0) y0 = Y; if (Y > y1) y1 = Y;
        return [X, Y, zc];
      });
      const pad = 12, scanning = !REDUCE && phase < SWEEP, s = scanning ? phase / SWEEP : 1;
      const e = s < 0.5 ? 2 * s * s : 1 - (-2 * s + 2) ** 2 / 2, lineY = y0 - pad + e * (y1 - y0 + 2 * pad);
      const acc = css("--accent"), ink = css("--ink"), roast = css("--coffee-2");
      const P = { uB: new Path2D(), uF: new Path2D(), sB: new Path2D(), sF: new Path2D(), fB: new Path2D(), fF: new Path2D(), hot: new Path2D() };
      for (const [a, b, fl] of model.segs) {
        const A = Q[a], B = Q[b], my = (A[1] + B[1]) / 2, back = A[2] + B[2] > 0, done = !scanning || my < lineY;
        const k = scanning && !back && Math.abs(my - lineY) < 7 ? "hot" : !done ? (back ? "uB" : "uF") : fl ? (back ? "fB" : "fF") : (back ? "sB" : "sF");
        P[k].moveTo(A[0], A[1]); P[k].lineTo(B[0], B[1]);
      }
      const st = (path, col, al, w) => { ctx.strokeStyle = col; ctx.globalAlpha = al; ctx.lineWidth = w; ctx.stroke(path); };
      st(P.uB, acc, 0.2, 0.6); st(P.uF, acc, 0.8, 0.75); st(P.sB, roast, 0.14, 0.6); st(P.sF, ink, 0.58, 0.7);
      st(P.fB, acc, 0.3, 0.7); st(P.fF, acc, 1, 1.3); st(P.hot, acc, 1, 1.6);
      ctx.lineCap = "round";
      for (const [a, b] of model.bold || []) {
        const A = Q[a], B = Q[b], done = !scanning || (A[1] + B[1]) / 2 < lineY;
        ctx.strokeStyle = done ? ink : acc; ctx.globalAlpha = A[2] + B[2] > 0 ? 0.3 : 1; ctx.lineWidth = o.boldW || 1.8;
        ctx.beginPath(); ctx.moveTo(A[0], A[1]); ctx.lineTo(B[0], B[1]); ctx.stroke();
      }
      ctx.globalAlpha = 1;
      if (scanning) {
        const lx0 = x0 - pad - 18, lx1 = x1 + pad + 18, g = ctx.createLinearGradient(0, lineY - 28, 0, lineY);
        g.addColorStop(0, acc + "00"); g.addColorStop(1, acc);
        ctx.globalAlpha = 0.14; ctx.fillStyle = g; ctx.fillRect(lx0, lineY - 28, lx1 - lx0, 28);
        ctx.globalAlpha = 1; ctx.fillStyle = acc; ctx.fillRect(lx0, lineY - 0.75, lx1 - lx0, 1.5);
      }
      ctx.fillStyle = ink;
      for (const [hx, hy] of [[x0 - pad, y0 - pad], [x1 + pad, y0 - pad], [x0 - pad, y1 + pad], [x1 + pad, y1 + pad]]) ctx.fillRect(hx - 3.5, hy - 3.5, 7, 7);
    }
    return { start() { if (running) return; running = true; phase = 0; last = 0; raf = requestAnimationFrame(frame); },
             stop() { running = false; cancelAnimationFrame(raf); }, redraw: draw };
  }

  // ---------------------------------------------------------------- HSI article head: the three measured spectra drawn by a moving wavelength cursor
  function spectraDraw(id) {
    const cv = $(id), ctx = cv.getContext("2d");
    const SER = [["Arabica", "AB100", "--s-arabica"], ["Robusta", "RB100", "--s-robusta"], ["Chicory", "CH100", "--s-chicory"]];
    const IDX = WL.map((w, i) => [w, i]).filter(([w]) => w >= 1000 && w <= 2450);
    let lo = Infinity, hi = -Infinity;
    for (const [, k] of SER) for (const [, i] of IDX) { lo = Math.min(lo, REF[k][i]); hi = Math.max(hi, REF[k][i]); }
    const pad = (hi - lo) * 0.06; lo -= pad; hi += pad;
    const DRAW = 2800, HOLD = 5200;
    let last = 0, raf = 0, running = false, phase = 0;
    function frame(t) {
      const dt = last ? Math.min(50, t - last) : 16; last = t; phase += dt;
      if (phase > DRAW + HOLD) phase = 0;
      draw();
      if (running && !REDUCE) raf = requestAnimationFrame(frame);
    }
    function draw() {
      const dpr = devicePixelRatio || 1, W = cv.clientWidth, H = cv.clientHeight;
      if (!W || !H) return;
      if (cv.width !== Math.round(W * dpr) || cv.height !== Math.round(H * dpr)) { cv.width = Math.round(W * dpr); cv.height = Math.round(H * dpr); }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
      const ink = css("--ink"), mut = css("--muted"), acc = css("--accent"), line = css("--line");
      const x0 = 14, x1 = W - 74, y0 = 42, y1 = H - 30;
      const X = (w) => x0 + ((w - 1000) / 1450) * (x1 - x0), Y = (v) => y1 - ((v - lo) / (hi - lo)) * (y1 - y0);
      const s = REDUCE ? 1 : Math.min(1, phase / DRAW), e = s < 0.5 ? 2 * s * s : 1 - (-2 * s + 2) ** 2 / 2, wCut = 1000 + e * 1450;
      const after = REDUCE ? 1 : Math.max(0, Math.min(1, (phase - DRAW) / 500));
      ctx.font = `500 10.5px Archivo, "Helvetica Neue", Arial, sans-serif`;
      if ("letterSpacing" in ctx) ctx.letterSpacing = "0px";
      ctx.strokeStyle = line; ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(x0, y1 + 0.5); ctx.lineTo(x1, y1 + 0.5); ctx.stroke();
      ctx.fillStyle = mut; ctx.textBaseline = "top";
      for (const w of [1000, 1500, 2000]) { ctx.fillRect(X(w), y1, 1, 4); ctx.fillText(String(w), X(w) - (w === 1000 ? 0 : 11), y1 + 7); }
      ctx.fillText("nm", X(2450) - 12, y1 + 7);
      if (after > 0) {                                   // the two coffee-oil bands, where chicory dips least
        ctx.globalAlpha = after; ctx.setLineDash([3, 4]); ctx.strokeStyle = mut;
        for (const w of [1730, 2310]) { ctx.beginPath(); ctx.moveTo(X(w) + 0.5, y0 - 6); ctx.lineTo(X(w) + 0.5, y1); ctx.stroke(); }
        ctx.setLineDash([]); ctx.textBaseline = "bottom"; ctx.fillStyle = mut;
        ctx.fillText("oil", X(1730) - 7, y0 - 8); ctx.fillText("oil", X(2310) - 7, y0 - 8);
        ctx.globalAlpha = 1;
      }
      const ends = [];
      ctx.lineJoin = "round"; ctx.lineCap = "round";
      for (const [name, k, tok] of SER) {
        const col = css(tok); let px = 0, py = 0, prev = null;
        ctx.strokeStyle = col; ctx.lineWidth = 1.9; ctx.beginPath();
        for (const [w, i] of IDX) {
          let ww = w, v = REF[k][i];
          if (w > wCut) { if (!prev) break; const f = (wCut - prev[0]) / (w - prev[0]); ww = wCut; v = prev[1] + f * (v - prev[1]); }
          px = X(ww); py = Y(v);
          if (!prev) ctx.moveTo(px, py); else ctx.lineTo(px, py);
          prev = [w, REF[k][i]];
          if (w > wCut) break;
        }
        ctx.stroke();
        if (s < 1) { ctx.fillStyle = col; ctx.beginPath(); ctx.arc(px, py, 3.2, 0, 2 * Math.PI); ctx.fill(); }
        ends.push([name, col, py]);
      }
      if (s < 1) {                                       // the wavelength cursor, like the scan line on the home page
        const cx = X(wCut), g = ctx.createLinearGradient(cx - 30, 0, cx, 0);
        g.addColorStop(0, acc + "00"); g.addColorStop(1, acc);
        ctx.globalAlpha = 0.13; ctx.fillStyle = g; ctx.fillRect(cx - 30, y0 - 10, 30, y1 - y0 + 10);
        ctx.globalAlpha = 1; ctx.fillStyle = acc; ctx.fillRect(cx - 0.75, y0 - 10, 1.5, y1 - y0 + 10);
        ctx.font = `700 10.5px Archivo, "Helvetica Neue", Arial, sans-serif`; ctx.textBaseline = "bottom"; ctx.fillStyle = ink;
        const lab = `λ ${Math.round(wCut)} nm`, lw = ctx.measureText(lab).width;
        ctx.fillText(lab, Math.min(W - lw - 2, Math.max(0, cx - lw / 2)), y0 - 12);
      } else {                                           // names at the line ends, nudged apart so they never overlap
        ends.sort((a, b) => a[2] - b[2]);
        for (let i = 1; i < ends.length; i++) if (ends[i][2] - ends[i - 1][2] < 14) ends[i][2] = ends[i - 1][2] + 14;
        ctx.font = `600 11.5px Archivo, "Helvetica Neue", Arial, sans-serif`; ctx.textBaseline = "middle";
        for (const [name, col, y] of ends) { ctx.fillStyle = col; ctx.fillText(name, x1 + 8, y); }
      }
      ctx.fillStyle = ink;
      for (const [hx, hy] of [[x0 - 8, 9], [W - 6, 9], [x0 - 8, y1 + 22], [W - 6, y1 + 22]]) ctx.fillRect(hx - 3.5, hy - 3.5, 7, 7);
    }
    return { start() { if (running) return; running = true; phase = 0; last = 0; raf = requestAnimationFrame(frame); },
             stop() { running = false; cancelAnimationFrame(raf); }, redraw: draw };
  }
  const WIRES = {
    learn: wire("wireLearn", MODELS.bean(false), { ax: -1.15, az: 0.6, rock: 0.5, scale: 0.34, boldW: 2.2 }),
    coffee: wire("wireCoffee", MODELS.bean(true), { ax: -1.15, az: -0.55, rock: 0.5, scale: 0.34, boldW: 2.2 }),
    hsi: spectraDraw("wireHsi"),
    methods: wire("wireMethods", MODELS.dish(), { ax: 0.95, spin: 0.00018, scale: 0.41 }),
    scan: wire("wireScan", MODELS.dish(), { ax: 0.95, spin: 0.00018, scale: 0.41, loop: true, sweep: 2600, hold: 1800 }),
  };

  // ---------------------------------------------------------------- inner pages: giant wordmark sized to the width
  function fitWords() {
    document.querySelectorAll(".view:not([hidden]) .pw").forEach((el) => {
      el.style.fontSize = "100px";
      const box = el.parentElement, cs = getComputedStyle(box);
      const avail = (box.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight)) * 0.99;
      el.style.fontSize = `${Math.min(innerHeight * (parseFloat(el.dataset.cap) || 0.3), (100 * avail) / el.offsetWidth)}px`;
    });
  }
  addEventListener("resize", () => { fitWords(); for (const w of Object.values(WIRES)) w.redraw(); });
  document.fonts && document.fonts.ready.then(fitWords);

  // ---------------------------------------------------------------- article pages: contents rail, section in view highlighted
  document.querySelectorAll(".abody").forEach((ab) => {
    const list = ab.querySelector(".toc"), items = [];
    for (const b of ab.querySelector(".amain").children) {
      if (b.classList.contains("art-end")) continue;
      const label = b.dataset.toc || (b.querySelector("h3") && b.querySelector("h3").textContent.trim());
      if (!label) continue;
      const li = document.createElement("li"), btn = document.createElement("button");
      btn.type = "button"; btn.textContent = label;
      btn.addEventListener("click", () => b.scrollIntoView({ behavior: REDUCE ? "auto" : "smooth", block: "start" }));
      li.append(btn); list.append(li); items.push([b, btn]);
    }
    const io = new IntersectionObserver((ents) => ents.forEach((en) => {
      if (en.isIntersecting) items.forEach(([b, btn]) => btn.setAttribute("aria-current", String(b === en.target)));
    }), { rootMargin: "-22% 0px -68% 0px" });
    items.forEach(([b]) => io.observe(b));
  });

  // ---------------------------------------------------------------- learn: cover art (drawn from real data)
  let coversDone = false;
  function drawCovers() {
    if (coversDone) return; coversDone = true;
    // 01: beans on espresso, one row of chicory roots
    let s1 = `<rect width="400" height="320" fill="#2a1a12"/>`;
    let seed = 3; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    for (let r = 0; r < 6; r++) for (let c = 0; c < 8; c++) {
      const x = 28 + c * 50 + (r % 2) * 25, y = 26 + r * 54, rot = Math.round(rnd() * 360);
      const chic = r === 3 && c % 2 === 0;
      s1 += chic ? `<g transform="translate(${x} ${y}) rotate(${rot})"><path d="M0 -18 C 7 -8, 6 6, 0 18 C -6 6, -7 -8, 0 -18 Z" fill="#e8571f"/><path d="M0 -12 V12" stroke="#2a1a12" stroke-width="1.6"/></g>`
                 : `<g transform="translate(${x} ${y}) rotate(${rot})"><ellipse rx="13" ry="18" fill="${rnd() < 0.5 ? "#8a5a36" : "#6b4423"}"/><path d="M-3 -15 C 6 -5, -6 5, 3 15" stroke="#f3e2cf" stroke-width="1.8" fill="none" opacity=".8"/></g>`;
    }
    // 02: stacked spectra of pure arabica, robusta and chicory, offset like a waterfall
    let s2 = `<defs><linearGradient id="g2" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stop-color="#1a110c"/><stop offset="1" stop-color="#3a1d12"/></linearGradient></defs><rect width="400" height="320" fill="url(#g2)"/>`;
    const sets = [REF.AB100, REF.RB100, REF.CH100];
    for (let k = 0; k < 14; k++) {
      const v = sets[k % 3], pts = [];
      const sel = WL.map((w, i) => [w, v[i]]).filter(([w]) => w >= 1000 && w <= 2450);
      const lo = Math.min(...sel.map((p) => p[1])), hi = Math.max(...sel.map((p) => p[1]));
      for (const [w, r] of sel) pts.push(`${(24 + ((w - 1000) / 1450) * 352).toFixed(1)},${(70 + k * 15 - ((r - lo) / (hi - lo)) * 46).toFixed(1)}`);
      const col = k % 3 === 2 ? "#e8571f" : `rgba(255,255,255,${(0.35 + 0.04 * k).toFixed(2)})`;
      s2 += `<polyline points="${pts.join(" ")}" fill="none" stroke="${col}" stroke-width="${k % 3 === 2 ? 1.6 : 1}"/>`;
    }
    // 03: a sheet of instrument glyphs
    const ink = "#111114";
    const g = [
      `<circle cx="0" cy="-6" r="14" fill="none" stroke="${ink}" stroke-width="3"/><path d="M10 4 L22 16" stroke="${ink}" stroke-width="4" stroke-linecap="round"/>`,
      `<path d="M-24 14 H24 M-20 14 C -16 14, -14 -14, -10 14 M -2 14 C 1 14, 3 -4, 6 14 M 10 14 C 13 14, 15 -18, 18 14" fill="none" stroke="${ink}" stroke-width="2.6"/>`,
      `<path d="M-10 -20 C 10 -10, -10 10, 10 20 M10 -20 C -10 -10, 10 10, -10 20 M-6 -12 H6 M-6 0 H6 M-6 12 H6" fill="none" stroke="${ink}" stroke-width="2.6"/>`,
      `<path d="M-24 16 H24 M-22 16 C -10 16, -4 -22, 0 -22 C 4 -22, 10 16, 22 16" fill="none" stroke="${ink}" stroke-width="2.6"/>`,
      `<rect x="-20" y="-14" width="40" height="28" rx="3" fill="none" stroke="${ink}" stroke-width="2.6"/><circle r="7" fill="none" stroke="${ink}" stroke-width="2.6"/>`,
      `<path d="M-14 -14 h28 v28 h-28 Z M-8 -20 h28 v28 M-2 -26 h28 v28" fill="none" stroke="#e8571f" stroke-width="2.6"/>`,
    ];
    let s3 = `<rect width="400" height="320" fill="#f2efe9"/>`;
    g.forEach((d, i) => { const x = 80 + (i % 3) * 120, y = 100 + Math.floor(i / 3) * 120;
      s3 += `<rect x="${x - 46}" y="${y - 46}" width="92" height="92" fill="none" stroke="#d9d4cc"/><g transform="translate(${x} ${y})">${d}</g>`; });
    const svg = (inner, label) => `<svg viewBox="0 0 400 320" preserveAspectRatio="xMidYMid slice" role="img" aria-label="${label}">${inner}</svg>`;
    $("art1").innerHTML = svg(s1, "Coffee beans with a row of chicory roots");
    $("art2").innerHTML = svg(s2, "Stacked spectra of arabica, robusta and chicory");
    $("art3").innerHTML = svg(s3, "Glyphs for microscopy, chromatography, DNA, NMR, spectroscopy and hyperspectral imaging");
  }
'''
js = js.replace("@@ROUTER@@\n", ROUTER)

ICON_ARROW = '<svg class="chev" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h13M13 6l6 6-6 6" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="square"/></svg>'
ICON_BACK = '<svg class="chev" viewBox="0 0 24 24" aria-hidden="true"><path d="M19 12H6M11 6l-6 6 6 6" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="square"/></svg>'
MARK = '<svg viewBox="0 0 32 32" aria-hidden="true"><ellipse cx="16" cy="16" rx="10.5" ry="14" transform="rotate(32 16 16)" fill="currentColor"/><path d="M12 4.6 C 20 11.5, 12.5 20.5, 20.5 27.4" stroke="var(--bg)" stroke-width="2.6" fill="none" stroke-linecap="round"/></svg>'

GRID = '<div class="gridlines" aria-hidden="true"><i></i><i></i><i></i></div>'

def phead(canvas_id, k, v, title, lede, extra=""):
    return f"""
    <header class="phead">
      <div class="ph-obj">
        <div class="ph-canvas" aria-hidden="true"><canvas id="{canvas_id}"></canvas></div>
        <div class="readout"><span class="ro-k">{k}</span><span class="ro-v">{v}</span>{extra}</div>
      </div>
      <div class="ph-text">
        <h1 class="ph-title">{title}</h1>
        <p class="ph-lede">{lede}</p>
      </div>
    </header>"""

def pword(word, sup, cap=0.24):
    inner = f"{word}<sup>{sup}</sup>"
    return f"""
    <div class="pword" aria-hidden="true"><div class="pw" data-cap="{cap}"><span class="pw-out">{inner}</span><span class="pw-fill">{inner}</span><i class="pw-line"></i></div></div>"""

def article(vid, key, no, word, canvas_id, title, lede, body, nxt):
    nxt_html = (f'<a class="nextcard" href="#{nxt[0]}"><span class="muted">Next read</span><b>{nxt[1]}</b>{ICON_ARROW}</a>' if nxt else
                f'<a class="nextcard" href="#scan"><span class="muted">You have read all three</span><b>Now scan a sample</b>{ICON_ARROW}</a>')
    back = f'<a class="back" href="#learn">{ICON_BACK}All articles</a>'
    return f"""
  <section class="view inner-view" id="{vid}" aria-label="{title}" hidden>
    {GRID}{phead(canvas_id, f"Article {no} / 03", f"{mins[key]} min read" + (" · arabica, robusta and chicory, as measured" if key == "hsi" else ""), title, lede, back)}{pword(word, no)}
    <div class="abody">
      <aside class="rail" aria-label="In this article"><div class="rail-in"><span class="ro-k">In this article</span><ol class="toc"></ol>{back}</div></aside>
      <div class="amain">{body}
        <div class="art-end">{nxt_html}</div>
      </div>
    </div>
  </section>"""

COVER = lambda key, art, no, title, teaser: f"""
      <a class="cover" href="#{key}">
        <div class="cover-top"><span class="cover-no">{no}</span><span>{mins[key]} min read</span></div>
        <div class="cover-art"><div class="cover-img" id="{art}"></div></div>
        <h2>{title}</h2>
        <p class="muted">{teaser}</p>
        <span class="cover-foot"><span>Read the article</span>{ICON_ARROW}</span>
      </a>"""

a = scan_view.index('<section class="view" id="viewScan"'); b = scan_view.index('      <div class="stack">')
scan_view = (scan_view[:a] + '<section class="view inner-view" id="viewScan" aria-label="Scan a sample" hidden>\n    ' + GRID
             + phead("wireScan", "Workbench", "SWIR push-broom scans · nothing is uploaded", "Scan a sample",
                     "Add the scan's two files. The app reads them in your browser, finds the white strip and every petri dish, and analyses the dish you click.")
             + pword("SCAN", "SWIR", 0.18) + '\n    <div class="inner">\n' + scan_view[b:])
assert scan_view.count('<div class="inner">') == 1

INNER_CSS = r'''
/* ---------------- inner pages: the home page's grid, readouts, handles and scan line */
body { background: var(--bg) linear-gradient(105deg, var(--bg) 30%, var(--glow) 100%) fixed; }
.inner-view { position: relative; }
.inner-view > :not(.gridlines) { position: relative; z-index: 1; }
.phead { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.ph-obj { grid-column: 1; display: grid; gap: 10px; padding: 20px 3vw 26px; align-content: end; }
.ph-canvas { position: relative; height: 280px; }
.ph-canvas canvas { position: absolute; inset: 0; width: 100%; height: 100%; }
.readout { display: grid; gap: 4px; justify-items: start; }
.ro-k { font-stretch: 125%; font-weight: 700; font-size: .78rem; letter-spacing: .07em; text-transform: uppercase; color: var(--ink); }
.ro-v { font-size: .84rem; color: var(--muted); }
.readout .back { margin-top: 10px; display: none; }
.ph-text { grid-column: 2 / 4; align-self: end; padding: 40px 3vw 30px; display: grid; gap: 16px; }
.ph-title { font-stretch: 125%; font-weight: 700; text-transform: uppercase; font-size: clamp(1.9rem, 3.2vw, 3.1rem); line-height: 1.03; max-width: 22ch; }
.ph-lede { max-width: 56ch; color: var(--muted); font-size: 1.1rem; }

.pword { overflow: hidden; padding: 0 .5vw .5vw; border-bottom: 1px solid var(--line); }
.pw { position: relative; width: max-content; font-family: var(--display); font-stretch: 125%; font-weight: 900; line-height: .76; letter-spacing: -.02em;
      white-space: nowrap; user-select: none; }
.pw sup { font-size: .085em; font-weight: 600; vertical-align: top; position: relative; top: .25em; margin-left: .15em; letter-spacing: 0; }
.pw-out { display: block; color: transparent; -webkit-text-stroke: 1.2px color-mix(in srgb, var(--ink) 45%, transparent); }
.pw-out sup { -webkit-text-stroke: 0; }
.pw-fill { position: absolute; inset: 0; background: linear-gradient(95deg, color-mix(in srgb, var(--ink) 72%, var(--bg)) 0%, var(--ink) 55%);
           -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; animation: pwfill 1.7s cubic-bezier(.55,0,.3,1) .2s both; }
.pw-fill sup { -webkit-text-fill-color: var(--ink); }
.pw-line { position: absolute; left: 0; right: 0; top: 0; height: 2px; background: var(--accent); opacity: 0;
           box-shadow: 0 -12px 26px color-mix(in srgb, var(--accent) 50%, transparent); animation: sweepY 1.7s cubic-bezier(.55,0,.3,1) .2s both; }
@keyframes pwfill { from { clip-path: inset(0 0 100% 0); } to { clip-path: inset(0 0 0 0); } }
@keyframes sweepY { 0% { top: 0; opacity: 1; } 92% { top: 100%; opacity: 1; } 100% { top: 100%; opacity: 0; } }

/* selection handles, as around the bean on the home page */
.card, .cover-art, .drop { position: relative; }
.card::after, .cover-art::after, .drop::after { content: ""; position: absolute; inset: -5px; pointer-events: none; z-index: 2;
  background: linear-gradient(var(--ink), var(--ink)) left top / 8px 8px no-repeat, linear-gradient(var(--ink), var(--ink)) right top / 8px 8px no-repeat,
              linear-gradient(var(--ink), var(--ink)) left bottom / 8px 8px no-repeat, linear-gradient(var(--ink), var(--ink)) right bottom / 8px 8px no-repeat;
  opacity: 0; transform: scale(1.015); transition: opacity .25s, transform .3s cubic-bezier(.2,.8,.2,1); }
.card:hover::after, .cover:hover .cover-art::after, .drop::after { opacity: 1; transform: none; }
.card { border-radius: 2px; background: color-mix(in srgb, var(--surface) 90%, transparent); }
.drop { border: 1px solid var(--line); border-radius: 2px; background: color-mix(in srgb, var(--surface) 72%, transparent); }
.drop:hover { border-color: color-mix(in srgb, var(--ink) 35%, var(--line)); }
.drop.over { border-style: solid; border-color: var(--accent); }
.drop::before { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 2px; background: var(--accent); opacity: 0;
                box-shadow: 0 -12px 26px color-mix(in srgb, var(--accent) 50%, transparent); }
.drop.over::before { animation: sweepY 1.2s cubic-bezier(.55,0,.3,1) infinite; }
.drop .big { font-stretch: 112%; font-weight: 650; color: var(--ink); }
.empty { border-radius: 2px; }
.inner { padding: 30px 3vw 24px; }
.sitefoot .wrap { max-width: none; padding-inline: 3vw; }

/* learn: three covers, one per grid column */
.covers { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); border-bottom: 1px solid var(--line); }
.cover { display: grid; gap: 14px; align-content: start; padding: 26px 3vw 30px; color: var(--ink); text-decoration: none; transition: background .3s; }
.cover:hover { background: color-mix(in srgb, var(--surface) 50%, transparent); }
.cover-top { display: flex; justify-content: space-between; align-items: baseline; color: var(--muted); font-size: .9rem; }
.cover-no { font-stretch: 125%; font-weight: 800; color: var(--accent); font-size: 1rem; }
.cover-art { aspect-ratio: 5 / 4; }
.cover-img { position: absolute; inset: 0; overflow: hidden; background: var(--tint-2); }
.cover-img svg { width: 100%; height: 100%; display: block; transition: transform .8s cubic-bezier(.2,.8,.2,1); }
.cover:hover .cover-img svg { transform: scale(1.05); }
.cover-img::after { content: ""; position: absolute; left: 0; right: 0; top: 0; height: 2px; background: var(--accent); opacity: 0;
                    box-shadow: 0 -12px 26px color-mix(in srgb, var(--accent) 60%, transparent); }
.cover:hover .cover-img::after { animation: sweepY 1.1s cubic-bezier(.55,0,.3,1) both; }
.cover h2 { font-stretch: 112%; font-size: 1.5rem; font-weight: 700; line-height: 1.15; }
.cover-foot { display: flex; justify-content: space-between; align-items: center; border-top: 1px solid var(--line); padding-top: 12px; font-weight: 600; }

/* articles: contents rail in the first column, the text across the other two */
.abody { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); }
.rail { grid-column: 1; padding: 36px 3vw 40px; }
.rail-in { position: sticky; top: 92px; display: grid; gap: 14px; justify-items: start; }
.toc { list-style: none; margin: 0; padding: 0; counter-reset: toc; border-bottom: 1px solid var(--line); width: 100%; }
.toc li { counter-increment: toc; }
.toc button { font: inherit; font-size: .95rem; line-height: 1.35; text-align: left; width: 100%; display: grid; grid-template-columns: 2.4em minmax(0, 1fr); gap: 6px;
              padding: 9px 0; background: none; border: 0; border-top: 1px solid var(--line); color: var(--muted); cursor: pointer; transition: color .2s; }
.toc button::before { content: counter(toc, decimal-leading-zero); font-stretch: 125%; font-weight: 700; font-size: .78rem; padding-top: .2em; }
.toc button:hover { color: var(--ink); }
.toc button[aria-current="true"] { color: var(--ink); font-weight: 600; }
.toc button[aria-current="true"]::before { color: var(--accent); }
.amain { grid-column: 2 / 4; padding: 36px 3vw 64px; display: grid; gap: 22px; min-width: 0; align-content: start; }
.amain > * { scroll-margin-top: 92px; }
.art-end { display: grid; gap: 18px; padding-top: 10px; }

@media (max-width: 860px) {
  .inner-view .gridlines { display: none; }
  .phead, .abody, .covers { grid-template-columns: minmax(0, 1fr); }
  .ph-obj { grid-row: 1; padding: 16px 20px 4px; }
  .ph-text { grid-column: 1; grid-row: 2; padding: 12px 20px 24px; }
  .ph-canvas { height: 210px; }
  .readout .back { display: inline-flex; }
  .pword { padding: 0 20px 6px; }
  .rail { display: none; }
  .amain { grid-column: 1; padding: 26px 20px 50px; }
  .cover { padding: 24px 20px 28px; border-top: 1px solid var(--line); }
  .cover:first-child { border-top: 0; }
  .inner { padding: 24px 20px 10px; }
  .sitefoot .wrap { padding-inline: 20px; }
}
'''

HTML = f'''<title>Coffee Adulterant Detector</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:ital,wdth,wght@0,62..125,100..900;1,62..125,100..900&display=swap">
<style>
/* Layout: Fabric-style grid. A wireframe coffee bean over a giant wordmark (home); three tilting "covers" (learn);
   one article per page; the scan workbench. One family (Archivo): wide for display, normal for reading.
   Palette: cool paper fading to infrared violet, black ink, roast orange as the only accent. */
:root {{
  --bg: #f6f1ea; --surface: #fffdfa; --tint: #faf6f0; --tint-2: #efe6da; --ink: #1e1410; --muted: #74665b; --line: #e4d9cc; --track: #ece3d7;
  --accent: #d2501a; --glow: #ecd9c4;
  --coffee: #3b2418; --coffee-2: #a8441a; --crema: #e3a172; --on-coffee: #ffffff;
  --metal: #ddd9d4; --metal-2: #a39c95; --wood: #9a6640; --wood-2: #6b4423; --glass: #eef3f6;
  --ok: #2f6b45; --ok-bg: #e5f0e8; --warn: #8a5a00; --warn-bg: #f8edd6; --bad: #a3321f; --bad-bg: #f8e1dc;
  --s-robusta: #a84a12; --s-arabica: #0079a8; --s-chicory: #b98318;
  --shadow: 0 24px 50px -24px rgb(17 17 20 / .35);
  --display: "Archivo", "Helvetica Neue", Arial, sans-serif; --body: "Archivo", "Helvetica Neue", Arial, sans-serif;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #120d0a; --surface: #1b1410; --tint: #16100d; --tint-2: #241a14; --ink: #f4ece3; --muted: #ab9b8e; --line: #30251e; --track: #281e18;
  --accent: #ff7a3d; --glow: #2e1b10;
  --coffee: #f0dcc8; --coffee-2: #ff9a66; --crema: #c8693d; --on-coffee: #120d0a;
  --metal: #8d847c; --metal-2: #6c645d; --wood: #8a5a36; --wood-2: #5e3c22; --glass: #2b3940;
  --ok: #7cc296; --ok-bg: #1d2e23; --warn: #e3b45c; --warn-bg: #3a2c15; --bad: #f08a76; --bad-bg: #3d1d17;
  --s-robusta: #cf733b; --s-arabica: #2a9bc4; --s-chicory: #b98a24; --shadow: 0 24px 50px -24px rgb(0 0 0 / .7); color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg: #120d0a; --surface: #1b1410; --tint: #16100d; --tint-2: #241a14; --ink: #f4ece3; --muted: #ab9b8e; --line: #30251e; --track: #281e18;
  --accent: #ff7a3d; --glow: #2e1b10;
  --coffee: #f0dcc8; --coffee-2: #ff9a66; --crema: #c8693d; --on-coffee: #120d0a;
  --metal: #8d847c; --metal-2: #6c645d; --wood: #8a5a36; --wood-2: #5e3c22; --glass: #2b3940;
  --ok: #7cc296; --ok-bg: #1d2e23; --warn: #e3b45c; --warn-bg: #3a2c15; --bad: #f08a76; --bad-bg: #3d1d17;
  --s-robusta: #cf733b; --s-arabica: #2a9bc4; --s-chicory: #b98a24; --shadow: 0 24px 50px -24px rgb(0 0 0 / .7); color-scheme: dark; }}

* {{ box-sizing: border-box; }}
[hidden] {{ display: none !important; }}
body {{ margin: 0; background: var(--bg); color: var(--ink); font-family: var(--body); font-size: 16.5px; line-height: 1.6; }}
body::before {{ content: ""; position: fixed; inset: 0 0 auto; height: env(safe-area-inset-top, 0px); z-index: 30; background: var(--bg); }}
.wrap {{ max-width: 1240px; margin: 0 auto; padding-left: max(20px, env(safe-area-inset-left, 0px)); padding-right: max(20px, env(safe-area-inset-right, 0px)); }}
h1, h2, h3 {{ font-family: var(--display); color: var(--ink); text-wrap: balance; margin: 0; font-weight: 650; letter-spacing: -0.01em; }}
h2 {{ font-size: clamp(1.4rem, 2.4vw, 1.9rem); line-height: 1.15; }}
h3 {{ font-size: 1.15rem; line-height: 1.3; }}
p {{ margin: 0; }}
a {{ color: var(--coffee-2); }}
.muted {{ color: var(--muted); }}
.num {{ font-variant-numeric: tabular-nums; }}
.measure {{ max-width: 66ch; }}
.eyebrow {{ font-size: .85rem; color: var(--muted); font-weight: 600; }}
.chev {{ width: 22px; height: 22px; flex: none; transition: transform .25s cubic-bezier(.2,.8,.2,1); }}
:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 3px; }}
.btn {{ font: inherit; font-weight: 600; border-radius: 999px; padding: 11px 20px; border: 1px solid var(--ink); background: var(--ink); color: var(--bg);
        cursor: pointer; text-decoration: none; display: inline-flex; gap: 10px; align-items: center; transition: transform .2s, box-shadow .2s; }}
.btn:hover {{ transform: translateY(-2px); box-shadow: var(--shadow); }}
.btn:active {{ transform: scale(.97); }}
.btn.ghost {{ background: transparent; color: var(--ink); }}
.view[hidden] {{ display: none !important; }}
.view {{ animation: viewIn .6s cubic-bezier(.2,.7,.2,1) both; }}
@keyframes viewIn {{ from {{ opacity: 0; transform: translateY(14px); }} to {{ opacity: 1; transform: none; }} }}
#readbar {{ position: fixed; top: env(safe-area-inset-top, 0px); left: 0; height: 3px; width: 0; background: var(--accent); z-index: 40; transition: width .08s linear; }}

/* top bar */
.topbar {{ position: sticky; top: env(safe-area-inset-top, 0px); z-index: 20; background: color-mix(in srgb, var(--bg) 88%, transparent);
           backdrop-filter: blur(10px); border-bottom: 1px solid var(--line); }}
.tb {{ display: grid; grid-template-columns: auto 1fr auto; align-items: stretch; min-height: 62px;
       padding-left: max(20px, env(safe-area-inset-left, 0px)); padding-right: max(20px, env(safe-area-inset-right, 0px)); }}
.brand {{ display: flex; align-items: center; gap: 10px; color: var(--ink); text-decoration: none; font-family: var(--display);
          font-stretch: 125%; font-weight: 800; font-size: 1.02rem; letter-spacing: -0.01em; padding-right: 20px; }}
.brand svg {{ width: 28px; height: 28px; color: var(--ink); transition: transform .5s cubic-bezier(.3,1.5,.5,1); }}
.brand:hover svg {{ transform: rotate(-30deg) scale(1.1); }}
.nav {{ display: flex; justify-content: center; align-items: stretch; }}
.nav a {{ display: flex; align-items: center; padding: 0 22px; color: var(--ink); text-decoration: none; font-size: 1.05rem; border-left: 1px solid var(--line);
          position: relative; transition: background .2s; }}
.nav a:last-child {{ border-right: 1px solid var(--line); }}
.nav a::after {{ content: ""; position: absolute; left: 22px; right: 22px; bottom: 14px; height: 1.5px; background: var(--accent); transform: scaleX(0);
                 transform-origin: left; transition: transform .3s cubic-bezier(.2,.8,.2,1); }}
.nav a:hover::after, .nav a[aria-current="page"]::after {{ transform: scaleX(1); }}
.cta {{ align-self: center; display: inline-flex; gap: 10px; align-items: center; padding: 9px 14px 9px 16px; border: 1px solid var(--line); background: var(--surface);
         color: var(--ink); text-decoration: none; font-weight: 600; border-radius: 4px; transition: border-color .2s, transform .2s; }}
.cta:hover {{ border-color: var(--ink); transform: translateY(-1px); }}
.cta svg {{ width: 20px; height: 20px; transition: transform .5s cubic-bezier(.3,1.5,.5,1); }}
.cta:hover svg {{ transform: rotate(90deg); }}
.menu-btn {{ display: none; font: inherit; font-weight: 600; background: none; border: 1px solid var(--line); color: var(--ink); border-radius: 4px; padding: 6px 12px; align-self: center; cursor: pointer; }}

/* home */
.hero {{ position: relative; min-height: calc(100vh - 63px); min-height: calc(100dvh - 63px); overflow: hidden; display: grid;
         grid-template-columns: repeat(3, minmax(0, 1fr)); grid-template-rows: 1fr auto auto;
         }}
.gridlines {{ position: absolute; inset: 0; display: grid; grid-template-columns: repeat(3, 1fr); pointer-events: none; }}
.gridlines i {{ border-left: 1px solid var(--line); }}
.gridlines i:first-child {{ border-left: 0; }}
.bean-wrap {{ grid-column: 1; grid-row: 1 / 3; position: relative; z-index: 3; min-height: 0; margin-right: -2.5vw; pointer-events: none; }}
#beanCanvas {{ position: absolute; inset: 0; width: 100%; height: 100%; }}
.hero-copy {{ grid-column: 2 / 4; grid-row: 1; align-self: end; padding: 0 3vw 34px; z-index: 4; display: grid; gap: 18px; }}
.hero-title {{ font-stretch: 125%; font-weight: 700; text-transform: uppercase; font-size: clamp(2rem, 3.8vw, 3.6rem); line-height: 1.02; letter-spacing: .005em; }}
.hero-sub {{ max-width: 48ch; color: var(--muted); font-size: 1.08rem; }}
.hero-stats {{ display: grid; grid-template-columns: repeat(3, minmax(0, max-content)); gap: 0; margin: 4px 0 0; }}
.hero-stats div {{ padding: 2px 26px 2px 14px; border-left: 1px solid var(--line); }}
.hero-stats div:first-child {{ padding-left: 0; border-left: 0; }}
.hero-stats dt {{ font-size: .8rem; color: var(--muted); }}
.hero-stats dd {{ margin: 0; font-stretch: 112%; font-weight: 700; font-size: 1.15rem; }}
.hero-links {{ grid-column: 2 / 4; grid-row: 2; display: grid; grid-template-columns: 1fr 1fr; gap: 18px; padding: 0 3vw 24px; z-index: 4; }}
.rowlink {{ display: flex; justify-content: space-between; align-items: center; gap: 16px; padding: 14px 14px 14px 22px; border-radius: 4px;
            border: 1px solid color-mix(in srgb, var(--ink) 28%, transparent); background: color-mix(in srgb, var(--surface) 78%, transparent);
            backdrop-filter: blur(6px); color: var(--ink); text-decoration: none; cursor: pointer;
            box-shadow: 0 1px 0 color-mix(in srgb, var(--ink) 10%, transparent), 0 10px 24px -18px rgb(30 20 16 / .45);
            transition: background .25s, color .25s, border-color .25s, transform .25s cubic-bezier(.2,.8,.2,1), box-shadow .25s; }}
.rl-text {{ display: grid; gap: 3px; min-width: 0; }}
.rl-text small {{ font-stretch: 125%; font-weight: 700; font-size: .7rem; letter-spacing: .09em; text-transform: uppercase; opacity: .62; }}
.rl-text b {{ font-weight: 600; font-size: clamp(1.05rem, 1.45vw, 1.28rem); line-height: 1.2; }}
.rl-go {{ flex: none; width: 46px; height: 46px; border-radius: 50%; display: grid; place-items: center; background: var(--ink); color: var(--bg);
          transition: background .25s, color .25s, transform .35s cubic-bezier(.3,1.5,.5,1); }}
.rowlink.primary {{ background: var(--ink); color: var(--bg); border-color: var(--ink); }}
.rowlink.primary .rl-go {{ background: var(--accent); color: #fff; }}
.rowlink:hover {{ transform: translateY(-3px); border-color: var(--ink); box-shadow: var(--shadow); background: var(--ink); color: var(--bg); }}
.rowlink:hover .rl-go {{ background: var(--accent); color: #fff; transform: rotate(-45deg); }}
.rowlink.primary:hover {{ background: var(--accent); border-color: var(--accent); color: #fff; }}
.rowlink.primary:hover .rl-go {{ background: #fff; color: var(--accent); }}
.rowlink:active {{ transform: translateY(-1px) scale(.985); }}
.rowlink .rl-go .chev, .rowlink:hover .rl-go .chev {{ transform: none; }}
.rowlink:hover .chev, .cover:hover .chev, .nextcard:hover .chev {{ transform: translateX(6px); }}
.wordmark {{ grid-column: 1 / 4; grid-row: 3; font-family: var(--display); font-stretch: 125%; font-weight: 900; line-height: .76; letter-spacing: -.02em;
             white-space: nowrap; padding: 0 0 .5vw .5vw; justify-self: start; width: max-content; z-index: 2; color: var(--ink);
             background: linear-gradient(95deg, color-mix(in srgb, var(--ink) 72%, var(--bg)) 0%, var(--ink) 55%); -webkit-background-clip: text; background-clip: text;
             -webkit-text-fill-color: transparent; user-select: none; }}
.wordmark sup {{ font-size: .085em; font-weight: 600; vertical-align: top; position: relative; top: .25em; margin-left: .15em; letter-spacing: 0; -webkit-text-fill-color: var(--ink); }}

/* article end */
.back {{ display: inline-flex; gap: 8px; align-items: center; color: var(--muted); text-decoration: none; font-weight: 600; width: fit-content; }}
.back:hover {{ color: var(--ink); }}
.back:hover .chev {{ transform: translateX(-5px); }}
.nextcard {{ display: grid; grid-template-columns: 1fr auto; gap: 4px 16px; align-items: center; padding: 26px 28px; border: 1px solid var(--line);
             background: color-mix(in srgb, var(--surface) 88%, transparent); text-decoration: none; color: var(--ink); transition: border-color .25s, transform .25s, box-shadow .25s; }}
.nextcard b {{ font-stretch: 125%; text-transform: uppercase; font-size: clamp(1.1rem, 1.8vw, 1.5rem); font-weight: 700; grid-column: 1; }}
.nextcard .chev {{ grid-column: 2; grid-row: 1 / 3; width: 30px; height: 30px; }}
.nextcard:hover {{ border-color: var(--ink); transform: translateY(-2px); box-shadow: var(--shadow); }}

/* footer */
.sitefoot {{ border-top: 1px solid var(--line); padding: 0; margin-top: 0; font-size: inherit; }}
.ft {{ display: flex; flex-wrap: wrap; gap: 14px 30px; justify-content: space-between; align-items: center; padding-block: 22px 30px; color: var(--muted); font-size: .92rem; }}
.ft nav {{ display: flex; gap: 20px; }}
.ft a {{ color: var(--ink); text-decoration: none; }}
.ft a:hover {{ color: var(--accent); }}
body[data-view="home"] .sitefoot {{ display: none; }}

{old_css}
/* the reused components, squared off to match */
.card {{ border-radius: 4px; }}
.drop, .empty, .scanbox, #mapCanvas, .fact {{ border-radius: 6px; }}
.part-label, .partnav {{ display: none; }}
.scanhead {{ padding-block: 46px 22px; }}
{INNER_CSS}

@media (max-width: 480px) {{
  .brand {{ font-stretch: 100%; font-size: .98rem; }}
  .hero-stats {{ grid-template-columns: minmax(0, 1fr); gap: 8px; }}
  .hero-stats div {{ border-left: 0; padding: 0; }}
}}
@media (max-width: 980px) {{
}}
@media (max-width: 860px) {{
  .tb {{ grid-template-columns: 1fr auto; }}
  .menu-btn {{ display: inline-block; }}
  .cta {{ display: none; }}
  .nav {{ display: none; grid-column: 1 / -1; flex-direction: column; padding-bottom: 10px; }}
  body.menu-open .nav {{ display: flex; }}
  .nav a {{ border-left: 0; border-top: 1px solid var(--line); padding: 14px 4px; }}
  .nav a:last-child {{ border-right: 0; }}
  .nav a::after {{ left: 4px; right: auto; width: 40px; bottom: 8px; }}
  .hero {{ grid-template-columns: minmax(0, 1fr); grid-template-rows: auto auto auto auto; }}
  .gridlines {{ display: none; }}
  .bean-wrap {{ grid-row: 1; width: min(100%, 520px); aspect-ratio: 1 / 1.08; justify-self: center; margin-right: 0; }}
  .hero-stats div {{ padding-right: 14px; }}
  .hero-copy {{ grid-column: 1; grid-row: 2; padding: 0 20px 26px; }}
  .hero-links {{ grid-column: 1; grid-row: 3; grid-template-columns: minmax(0, 1fr); gap: 10px; padding: 0 20px 26px; }}
  .wordmark {{ grid-column: 1; grid-row: 4; }}
}}
</style>

<div id="readbar" aria-hidden="true"></div>
<header class="topbar">
  <div class="tb">
    <a class="brand" href="#home" aria-label="Coffee Adulterant Detector, home">{MARK}<span>Coffee Adulterant Detector</span></a>
    <nav class="nav" id="navMenu" aria-label="Pages">
      <a href="#home" data-nav="home">Home</a>
      <a href="#learn" data-nav="learn">Learn</a>
      <a href="#scan" data-nav="scan">Scan</a>
    </nav>
    <button class="menu-btn" id="menuBtn" type="button" aria-expanded="false" aria-controls="navMenu">Menu</button>
    <a class="cta" href="#scan">Scan a sample{MARK}</a>
  </div>
</header>

<main>
  <section class="view home" id="viewHome" aria-label="Coffee Adulterant Detector">
    <div class="hero">
      <div class="gridlines" aria-hidden="true"><i></i><i></i><i></i></div>
      <div class="bean-wrap" aria-hidden="true"><canvas id="beanCanvas"></canvas></div>
      <div class="hero-copy">
        <h1 class="hero-title">Coffee<br>adulterant<br>detector</h1>
        <p class="hero-sub">Is there chicory in your coffee, and how much? One short-wave infrared scan of the ground powder tells you the blend type and the chicory content of every dish.</p>
      </div>
      <div class="hero-links">
        <a class="rowlink" href="#learn"><span class="rl-text"><small>01 · Read</small><b>Learn about coffee &amp; HSI</b></span><span class="rl-go">{ICON_ARROW}</span></a>
        <a class="rowlink primary" href="#scan"><span class="rl-text"><small>02 · Analyse</small><b>Scan a sample</b></span><span class="rl-go">{ICON_ARROW}</span></a>
      </div>
      <div class="wordmark" id="wordmark" aria-hidden="true">COFFEE<sup>SWIR</sup></div>
    </div>
  </section>

  <section class="view inner-view" id="viewLearn" aria-label="Learn" hidden>
    {GRID}{phead("wireLearn", "Index · 3 articles", f"about {sum(mins.values())} minutes of reading", "What's in your cup, and how a camera can tell", "Three short reads on what goes into ground coffee, how a hyperspectral camera sees it, and how laboratories catch adulteration. Pick one.")}{pword("LEARN", "3 READS")}
    <div class="covers">{COVER("coffee", "art1", "01", "Coffee and what gets mixed into it", "Arabica, robusta and chicory, the fillers found in ground coffee, what they do to the cup, and what the law allows.")}{COVER("hsi", "art2", "02", "Seeing chemistry with hyperspectral imaging", "A spectrum at every pixel: which bonds absorb where in coffee, and why chicory shows up so clearly.")}{COVER("methods", "art3", "03", "How coffee adulteration is detected", "Microscopy, chromatography, DNA, NMR, spectroscopy and imaging, compared on speed, cost and what they can see.")}
    </div>
  </section>
{article("viewCoffee", "coffee", "01", "BLENDS", "wireCoffee", "Coffee and what gets mixed into it", "Coffee powder looks the same whether it is pure arabica, cheap robusta or a third chicory. Here is what each ingredient is and what mixing does to the cup.", p1, ("hsi", "Seeing chemistry with hyperspectral imaging"))}
{article("viewHsi", "hsi", "02", "SPECTRA", "wireHsi", "Seeing chemistry with hyperspectral imaging", "A hyperspectral camera records a full spectrum at every pixel. Those spectra carry the chemistry of the powder, band by band.", p2, ("methods", "How coffee adulteration is detected"))}
{article("viewMethods", "methods", "03", "METHODS", "wireMethods", "How coffee adulteration is detected", "From a microscope slide to a camera that sees chemistry: six ways to check what is really in a pack of coffee.", p3, None)}
{scan_view}
  <footer class="sitefoot"><div class="wrap ft">
    <span><b style="color:var(--ink)">Coffee Adulterant Detector</b>, a SWIR hyperspectral imaging project at NIT Calicut</span>
    <nav aria-label="Footer"><a href="#home">Home</a><a href="#learn">Learn</a><a href="#scan">Scan</a></nav>
  </div></footer>
</main>

<script src="core.js"></script>
<script src="models.js"></script>
<script>
{js}</script>
'''
out = Path(sys.argv[1]); out.write_text(HTML)
print("wrote", out, f"{len(HTML) / 1e3:.0f} kB; reading times", mins)
