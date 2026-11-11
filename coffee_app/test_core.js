// Runs core.js on real scans from the HDD and compares with the Python models' dish predictions.
// usage: node test_core.js            (prints a table; writes test_results.json)
const fs = require("fs"), path = require("path");
const Core = require("./core.js");
const BASE = (process.env.COFFEE_RAW || "/run/media/riyanvarghese/RIYAN HDD");
const models = Core.prepareModels(JSON.parse(fs.readFileSync(path.join(__dirname, "models.json"), "utf8")));

function fileSource(p) {
  const fd = fs.openSync(p, "r");
  return { read: async (a, b) => { const ab = new ArrayBuffer(b - a); fs.readSync(fd, new Uint8Array(ab), 0, b - a, a); return ab; },
           size: fs.statSync(p).size, close: () => fs.closeSync(fd) };
}

const SCANS = [
  // [hdr path, dish labels from the strip down, python group key prefix]
  ["coffee data/stir1_SWIR_384_SN3189_9000us_2026-09-01T162127_raw_rad_float32.hdr", ["AB100", "CH100", "RB100", "A", "B", "C"]],
  ["coffee data/stir1_SWIR_384_SN3189_9000us_2026-09-04T161044_raw_rad_float32.hdr", ["RB[50:50]", "RB[60:40]", "RB[70:30]", "RB[80:20]", "RB[90:10]"]],
  ["coffee data/batch3_rad/batch3stir2_SWIR_384_SN3189_9000us_2026-09-08T131543_raw_rad_float32.hdr", ["RB[55:45]", "RB[65:35]", "RB[75:25]", "RB[85:15]", "RB[95:5]"]],
  ["arabica/stir1_SWIR_384_SN3189_9000us_2026-09-04T151627_raw.hdr", ["AB[50:50]", "AB[60:40]", "AB[70:30]", "AB[80:20]", "AB[90:10]"]],
  ["arabica/batch2stir3_SWIR_384_SN3189_9000us_2026-09-08T123001_raw.hdr", ["AB[55:45]", "AB[65:35]", "AB[75:25]", "AB[85:15]", "AB[95:5]"]],
  ["arabica+robusta/batch1stir2_SWIR_384_SN3189_9000us_2026-09-07T144314_raw.hdr", ["AR[55:45]", "AR[65:35]", "AR[75:25]", "AR[85:15]", "AR[95:5]"]],
  ["arabica+robusta/stir2_SWIR_384_SN3189_9000us_2026-09-04T120652_raw.hdr", ["J", "K", "L", "AR[50:50]", "AR[60:40]", "AR[70:30]"]],
  ["arabica+robusta/stir1_SWIR_384_SN3189_9000us_2026-09-04T132731_raw.hdr", ["AR[80:20]", "AR[90:10]", "AR[50:50] (excluded)", "AR100"]],
];
const PY = fs.readFileSync(path.join(__dirname, "training_dish_predictions.csv"), "utf8").trim().split("\n").slice(1)
  .map((l) => { const [g, y, p, f] = l.split(","); return { g, y: +y, p: +p, f }; });

(async () => {
  const rows = [];
  for (const [hdr, labels] of SCANS) {
    const hp = path.join(BASE, hdr);
    const stem = hp.replace(/\.hdr$/, "");
    const dataPath = [".hyspex", ".img"].map((e) => stem + e).find((p) => fs.existsSync(p));
    const src = fileSource(dataPath);
    const t0 = Date.now();
    const scan = await Core.openScan(fs.readFileSync(hp, "utf8"), src, src.size, path.basename(dataPath), models);
    const br = await Core.brightnessImage(scan);
    const t1 = Date.now();
    const strip = Core.findStrip(br, scan.L, scan.S);
    const dishes = Core.findDishes(br, scan.L, scan.S, strip.s1, { minScore: 0 , maxN: labels.length + 2 });
    const t2 = Date.now();
    const white = await Core.buildWhite(scan, strip, models.pipeline);
    console.log(`\n${path.basename(dataPath)}  (${scan.raw ? "raw counts, dark " + scan.bgMedian.toFixed(0) : "radiance"})  read ${((t1 - t0) / 1e3).toFixed(1)} s, dishes ${((t2 - t1) / 1e3).toFixed(1)} s`);
    console.log(`  strip rows ${strip.s0}-${strip.s1}; white repaired cols ${white.repairedColumns}, bad pixels ${white.badPixels}`);
    console.log("  dish scores: " + dishes.map((d) => `(${d.cx},${d.cy},r${d.r}) ${d.score.toFixed(3)}`).join("  "));
    const real = dishes.slice().sort((a, b) => b.score - a.score).slice(0, labels.length).sort((a, b) => a.cy - b.cy);
    for (let i = 0; i < labels.length; i++) {
      const t3 = Date.now();
      const res = await Core.analyseDish(scan, br, white, real[i], models);
      const it = Core.interpret(res, models);
      const key = path.basename(stem) + "|" + labels[i];
      const py = PY.find((r) => r.g === key || r.g === key + "_b3");
      rows.push({ scan: path.basename(stem), label: labels[i], family: res.family, p: Math.max(...Object.values(res.probs)), adulterant: res.adulterant, python: py ? py.p : null,
                  truth: py ? py.y : null, q: res.domainQ, t2: res.domainT2, patches: res.nPatches, units: res.units.length, spread: res.spread, type: it.typeLabel });
      const r = rows[rows.length - 1];
      console.log(`  ${labels[i].padEnd(10)} ${it.typeLabel.padEnd(18)} ${res.family.padEnd(4)} conf ${r.p.toFixed(2)}  app ${r.adulterant.toFixed(2).padStart(6)} %` +
                  (py ? `  python ${py.p.toFixed(2).padStart(6)}  (true ${py.y})  diff ${(r.adulterant - py.p).toFixed(2)}` : "") +
                  `  dom Q ${r.q.toFixed(2)} T2 ${r.t2.toFixed(2)}  patches ${r.patches}  units ${r.units}  spread ${r.spread.toFixed(2)}  ${((Date.now() - t3) / 1e3).toFixed(1)} s` +
                  (it.warnings.length ? "  ! " + it.warnings.map((w) => w.text.slice(0, 40)).join(" | ") : ""));
    }
    src.close();
  }
  const cmp = rows.filter((r) => r.python !== null);
  const d = cmp.map((r) => r.adulterant - r.python);
  console.log(`\napp vs python on ${cmp.length} training dishes: mean diff ${(d.reduce((a, b) => a + b, 0) / d.length).toFixed(3)}, max |diff| ${Math.max(...d.map(Math.abs)).toFixed(3)}`);
  const e = cmp.map((r) => r.adulterant - r.truth);
  console.log(`app vs truth: RMSE ${Math.sqrt(e.reduce((a, b) => a + b * b, 0) / e.length).toFixed(3)} (in-sample)`);
  fs.writeFileSync(path.join(__dirname, "test_results.json"), JSON.stringify(rows, null, 1));
})().catch((e) => { console.error(e); process.exit(1); });
