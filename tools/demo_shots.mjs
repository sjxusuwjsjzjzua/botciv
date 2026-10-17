// Screenshots, numbers and the fly-down video of world5's step 0 demo (civ/viewer/demo.html), with the installed
// Chromium (software WebGL in a container: frame rates here are not a phone's; draw calls and triangles are).
//   node tools/demo_shots.mjs shots [out]       A-F at 1600x900 and Pixel 9 size (412x915 CSS px at 2.625)
//   node tools/demo_shots.mjs video [out] [fps] the fly-down as frames, then an mp4 with ffmpeg
//   node tools/demo_shots.mjs walk [out] [fps]  the walk, the same way
//   node tools/demo_shots.mjs one A [out] [query] one view at 1600x900 (quick looks while working)
// Needs the playwright package: in a cloud session NODE_PATH=/opt/node22/lib/node_modules.
import {chromium} from "playwright";
import {createServer} from "node:http";
import {readFile, mkdir} from "node:fs/promises";
import {execFileSync} from "node:child_process";
import path from "node:path";

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), "../civ/viewer");
const TYPES = {".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".png": "image/png", ".glb": "model/gltf-binary"};
const argv = process.argv.slice(2), cmd = argv[0] || "shots";
const one = cmd === "one" ? argv.splice(1, 1)[0] || "A" : null;
const [, out = "/tmp/demo5", a3, a4] = argv;

const server = createServer(async (req, res) => {
  const p = path.join(ROOT, decodeURIComponent(new URL(req.url, "http://x").pathname));
  try { const b = await readFile(p); res.writeHead(200, {"content-type": TYPES[path.extname(p)] || "application/octet-stream"}); res.end(b); }
  catch { res.writeHead(404); res.end(); }
}).listen(0);
const port = server.address().port;

const browser = await chromium.launch({executablePath: process.env.CHROMIUM || "/opt/pw-browsers/chromium",
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--enable-webgl"]});

async function open(query, {width = 1600, height = 900, scale = 1, mobile = false} = {}) {
  const ctx = await browser.newContext({viewport: {width, height}, deviceScaleFactor: scale, isMobile: mobile, hasTouch: mobile});
  const page = await ctx.newPage();
  const errs = [];
  page.on("console", m => { if (m.type() === "error" || m.type() === "warning") errs.push(m.text()); });
  page.on("pageerror", e => errs.push(String(e)));
  await page.goto(`http://localhost:${port}/demo.html?${query}`);
  await page.waitForFunction(() => window.__demo?.ready || document.getElementById("load")?.textContent.startsWith("could not"), null, {timeout: 600000});
  const failed = await page.evaluate(() => document.getElementById("load")?.textContent || "");
  if (failed.startsWith("could not")) throw new Error(failed + "\n" + errs.join("\n"));
  return {page, ctx, errs};
}

// render a moment, then measure the frame: draw calls and triangles of the scene pass, and the time a frame takes
async function shoot(page, file, t = null) {
  const stats = await page.evaluate(t => { const s = window.__demo.renderAt(t); return s; }, t);
  const ms = await page.evaluate(t => { const d = window.__demo, n = 5, a = performance.now();
    for (let i = 0; i < n; i++) { d.frame(t ?? d.clock.t, 1 / 30); d.renderer.getContext().readPixels(0, 0, 1, 1, 0x1908, 0x1401, new Uint8Array(4)); }
    return (performance.now() - a) / n; }, t);
  await page.evaluate(t => window.__demo.renderAt(t), t);
  await page.screenshot({path: file});
  return {...stats, ms: Math.round(ms)};
}

await mkdir(out, {recursive: true});
const rows = [];
if (cmd === "one") {
  const v = one;
  const extra = argv[2] || "";
  const {page, errs} = await open(`shot=${v}&debug=1${extra ? "&" + extra : ""}`);
  const s = await shoot(page, `${out}/${v}${extra ? "_" + extra.replace(/[=&]/g, "") : ""}.png`);
  console.log(v, JSON.stringify(s)); if (errs.length) console.log(errs.slice(0, 10).join("\n"));
} else if (cmd === "shots") {
  for (const [tier, opt] of [["desktop", {}], ["phone", {width: 412, height: 915, scale: 2.625, mobile: true}]]) {
    for (const v of ["A", "B", "C", "D", "E", "F"]) {
      const {page, ctx, errs} = await open(`shot=${v}${tier === "phone" ? "&tier=phone" : ""}`, opt);
      const s = await shoot(page, `${out}/${v}_${tier}.png`);
      rows.push({view: v, tier, ...s});
      console.log(v, tier, JSON.stringify(s));
      if (errs.length) console.log(errs.slice(0, 5).join("\n"));
      await ctx.close();
    }
  }
  console.log(JSON.stringify(rows));
} else if (cmd === "video" || cmd === "walk") {
  const fps = Number(a3 || 15), W = Number(a4 || 1280), H = Math.round(W * 9 / 16);
  const {page, errs} = await open(cmd === "video" ? "tour=1" : "walk=1", {width: W, height: H});
  const T = cmd === "video" ? await page.evaluate(() => window.__demo.tour.T) : 60;
  await mkdir(`${out}/${cmd}`, {recursive: true});
  const n = Math.round(T * fps);
  for (let i = 0; i <= n; i++) {
    await page.evaluate(t => window.__demo.renderAt(t), i / fps);
    await page.screenshot({path: `${out}/${cmd}/f${String(i).padStart(4, "0")}.png`});
    if (i % 50 === 0) console.log("frame", i, "/", n);
  }
  if (errs.length) console.log(errs.slice(0, 5).join("\n"));
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-framerate", String(fps), "-i", `${out}/${cmd}/f%04d.png`, "-c:v", "libx264", "-pix_fmt", "yuv420p",
    "-crf", "20", `${out}/${cmd === "video" ? "flydown" : "walk"}.mp4`]);
  console.log("wrote", `${out}/${cmd === "video" ? "flydown" : "walk"}.mp4`);
}
await browser.close();
server.close();
