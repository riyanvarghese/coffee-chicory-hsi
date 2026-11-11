// Pre-computes the example scans shown when the app opens: runs core.js on three real scans and writes
// examples.js (window.COFFEE_EXAMPLES) with a scan preview PNG, the dish geometry and every dish's result.
// usage: node build_examples.js
const fs = require("fs"), path = require("path"), zlib = require("zlib");
const Core = require("./core.js");
const BASE = (process.env.COFFEE_RAW || "/run/media/riyanvarghese/RIYAN HDD");
const models = Core.prepareModels(JSON.parse(fs.readFileSync(path.join(__dirname, "models.json"), "utf8")));

const EXAMPLES = [
  { id: "arabica-chicory", title: "Arabica + chicory blends", date: "8 Sep 2026", hdr: "arabica/batch2stir3_SWIR_384_SN3189_9000us_2026-09-08T123001_raw.hdr",
    labels: ["Arabica 55 : chicory 45", "Arabica 65 : chicory 35", "Arabica 75 : chicory 25", "Arabica 85 : chicory 15", "Arabica 95 : chicory 5"], select: 2 },
  { id: "robusta-chicory", title: "Robusta + chicory blends", date: "4 Sep 2026", hdr: "coffee data/stir1_SWIR_384_SN3189_9000us_2026-09-04T161044_raw_rad_float32.hdr",
    labels: ["Robusta 50 : chicory 50", "Robusta 60 : chicory 40", "Robusta 70 : chicory 30", "Robusta 80 : chicory 20", "Robusta 90 : chicory 10"], select: 3 },
  { id: "arabica-robusta-chicory", title: "Arabica + robusta + chicory blends", date: "7 Sep 2026", hdr: "arabica+robusta/batch1stir1_SWIR_384_SN3189_9000us_2026-09-07T143543_raw.hdr",
    labels: ["Arabica + robusta 55 : chicory 45", "Arabica + robusta 65 : chicory 35", "Arabica + robusta 75 : chicory 25", "Arabica + robusta 85 : chicory 15", "Arabica + robusta 95 : chicory 5"], select: 1 },
  { id: "pure-and-tests", title: "Pure coffees, chicory and test samples", date: "1 Sep 2026", hdr: "coffee data/stir1_SWIR_384_SN3189_9000us_2026-09-01T162127_raw_rad_float32.hdr",
    labels: ["Pure arabica", "Pure chicory", "Pure robusta", "Test sample A", "Test sample B", "Test sample C"], select: 0 },
];

function fileSource(p) {
  const fd = fs.openSync(p, "r");
  return { read: async (a, b) => { const ab = new ArrayBuffer(b - a); fs.readSync(fd, new Uint8Array(ab), 0, b - a, a); return ab; },
           size: fs.statSync(p).size, close: () => fs.closeSync(fd) };
}
const CRC = new Int32Array(256).map((_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c; });
const crc32 = (buf) => { let c = -1; for (const b of buf) c = CRC[(c ^ b) & 255] ^ (c >>> 8); return (c ^ -1) >>> 0; };
function pngGray(w, h, px) {
  const raw = Buffer.alloc((w + 1) * h);
  for (let y = 0; y < h; y++) { raw[y * (w + 1)] = 0; px.copy ? px.copy(raw, y * (w + 1) + 1, y * w, (y + 1) * w) : raw.set(px.subarray(y * w, (y + 1) * w), y * (w + 1) + 1); }
  const chunk = (type, data) => { const len = Buffer.alloc(4); len.writeUInt32BE(data.length); const td = Buffer.concat([Buffer.from(type), data]);
                                  const crc = Buffer.alloc(4); crc.writeUInt32BE(crc32(td)); return Buffer.concat([len, td, crc]); };
  const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(w, 0); ihdr.writeUInt32BE(h, 4); ihdr[8] = 8; ihdr[9] = 0;
  return Buffer.concat([Buffer.from([137, 80, 78, 71, 13, 10, 26, 10]), chunk("IHDR", ihdr), chunk("IDAT", zlib.deflateSync(raw, { level: 9 })), chunk("IEND", Buffer.alloc(0))]);
}
const r4 = (x) => Math.round(x * 1e4) / 1e4, r2 = (x) => Math.round(x * 100) / 100;

(async () => {
  const out = [];
  for (const ex of EXAMPLES) {
    const hp = path.join(BASE, ex.hdr), stem = hp.replace(/\.hdr$/, "");
    const dp = [".hyspex", ".img"].map((e) => stem + e).find((p) => fs.existsSync(p));
    const src = fileSource(dp);
    const scan = await Core.openScan(fs.readFileSync(hp, "utf8"), src, src.size, path.basename(dp), models);
    const br = await Core.brightnessImage(scan);
    const strip = Core.findStrip(br, scan.L, scan.S);
    const dishes = Core.findDishes(br, scan.L, scan.S, strip.s1);
    if (dishes.length !== ex.labels.length) throw new Error(`${ex.id}: found ${dishes.length} dishes, expected ${ex.labels.length}`);
    const white = await Core.buildWhite(scan, strip, models.pipeline);
    // preview: rotated so the scan runs left to right (x = line, y = across-track), 2x downsampled, 1-99.5 % stretch
    const lo = Core.percentile(br, 1), hi = Core.percentile(br, 99.5);
    const w = Math.floor(scan.L / 2), h = Math.floor(scan.S / 2), px = new Uint8Array(w * h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      let s = 0, n = 0;
      for (let a = 0; a < 2; a++) for (let b = 0; b < 2; b++) { const v = br[(2 * x + a) * scan.S + 2 * y + b]; if (Number.isFinite(v)) { s += v; n++; } }
      px[y * w + x] = n ? Math.max(0, Math.min(255, Math.round(((s / n - lo) / (hi - lo)) * 255))) : 0;
    }
    const png = pngGray(w, h, Buffer.from(px));
    const results = [];
    for (const d of dishes) {
      const res = await Core.analyseDish(scan, br, white, d, models);
      results.push({ family: res.family, probs: Object.fromEntries(Object.entries(res.probs).map(([k, v]) => [k, r4(v)])), adulterant: r4(res.adulterant), spread: r4(res.spread), domainQ: r4(res.domainQ),
                     domainT2: r4(res.domainT2), nPatches: res.nPatches, nKept: res.nKept, maskPixels: res.maskPixels,
                     meanReflectance: res.meanReflectance.map(r4), dish: d,
                     units: res.units.map((u) => ({ n: u.n, pred: r2(u.pred), patches: u.patches })) });
      console.log(ex.id, results.length, res.family, res.adulterant.toFixed(2));
    }
    out.push({ id: ex.id, title: ex.title, date: ex.date, file: path.basename(dp), raw: scan.raw, L: scan.L, S: scan.S,
               darkLevel: scan.raw ? Math.round(scan.bgMedian) : null, strip, labels: ex.labels, select: ex.select,
               preview: { w, h, scale: 2, lo: r4(lo), hi: r4(hi), png: "data:image/png;base64," + png.toString("base64") },
               white: { repairedColumns: white.repairedColumns, badPixels: white.badPixels }, results });
    src.close();
  }
  const js = "/* Example scans pre-computed with core.js by build_examples.js (real project data). */\nwindow.COFFEE_EXAMPLES = " + JSON.stringify(out) + ";\n";
  fs.writeFileSync(path.join(__dirname, "examples.js"), js);
  fs.writeFileSync(path.join(__dirname, "models.js"),
    "/* Models exported by train_app_models.py. */\nwindow.COFFEE_MODELS = " + fs.readFileSync(path.join(__dirname, "models.json"), "utf8") + ";\n");
  console.log("examples.js", (js.length / 1e3).toFixed(0), "kB");
})().catch((e) => { console.error(e); process.exit(1); });
