// Pictures of world5's viewer of a whole towns world (civ/viewer/world5.html, demo/live.js) from a site built by
// civ/site5.py, with the installed Chromium (software WebGL in a container: frame rates here are not a phone's).
//   node tools/live_shots.mjs <site dir> [out] [query...]   each query one picture, e.g. "h=4&cam=x,z,dist,pitch,yaw"
// With no query: the largest settlement close (150 m), from 1 km and 12 km, the whole land, and at night.
// Needs playwright where Node finds it: in a cloud session ln -s /opt/node22/lib/node_modules tools/node_modules.
import {chromium} from "playwright";
import {createServer} from "node:http";
import {readFile, mkdir} from "node:fs/promises";
import path from "node:path";

const [ROOT = "site/world5", out = "/tmp/live5", ...queries] = process.argv.slice(2);
const TYPES = {".html": "text/html", ".js": "text/javascript", ".json": "application/json", ".png": "image/png"};
const server = createServer(async (req, res) => {
  const p = path.join(path.resolve(ROOT), decodeURIComponent(new URL(req.url, "http://x").pathname));
  try { const b = await readFile(p); res.writeHead(200, {"content-type": TYPES[path.extname(p)] || "application/octet-stream"}); res.end(b); }
  catch { res.writeHead(404); res.end(); }
}).listen(0);
const port = server.address().port;
const browser = await chromium.launch({executablePath: process.env.CHROMIUM || "/opt/pw-browsers/chromium",
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist", "--enable-webgl"]});

const ctx = await browser.newContext({viewport: {width: 1400, height: 860}});
const errs = [];
let page = null;
async function fresh() {          // each picture on a page of its own (the last may still be busy streaming)
  if (page) await page.close();
  page = await ctx.newPage();
  page.setDefaultTimeout(600000);
  page.on("console", m => { if (m.type() === "error" || m.type() === "warning") errs.push(m.text()); });
  page.on("pageerror", e => errs.push(String(e)));
}
await mkdir(out, {recursive: true});

async function shot(query, name) {
  const t0 = Date.now();
  await fresh();
  await page.goto(`http://localhost:${port}/world5.html?still=1&debug=1&${query}`);
  await page.waitForFunction(() => window.__live?.ready || document.getElementById("load")?.textContent.startsWith("could not"), null, {timeout: 900000});
  const failed = await page.evaluate(() => document.getElementById("load")?.textContent || "");
  if (failed.startsWith("could not")) throw new Error(failed + "\n" + errs.join("\n"));
  await page.evaluate(() => window.__live.settle(8));
  const stats = await page.evaluate(() => window.__live.stats());
  await page.screenshot({path: path.join(out, name + ".png"), timeout: 300000});
  console.log(name, JSON.stringify(stats), `${((Date.now() - t0) / 1000).toFixed(0)} s`);
}

if (queries.length) for (const [i, q] of queries.entries()) await shot(q, `q${i}`);
else {
  await fresh();
  await page.goto(`http://localhost:${port}/world5.html?still=1`);
  await page.waitForFunction(() => window.__live?.ready, null, {timeout: 900000});
  const [x, z, b] = await page.evaluate(() => [window.__live.rig.target.x, window.__live.rig.target.z, window.__live.box]);
  await shot(`h=3&cam=${x},${z},150,0.7,0.3`, "close");
  await shot(`h=5&cam=${x},${z},1000,0.8,0.3`, "1km");
  await shot(`h=5&cam=${x},${z},12000,0.9,0.2`, "12km");
  await shot(`h=5&cam=${b[0] + b[2] / 2},${b[1] + b[3] * 0.6},${Math.max(b[2], b[3]) * 1.05},1.2,0`, "whole");
  await shot(`h=10&cam=${x},${z},220,0.7,0.3`, "night");
}
if (errs.length) console.log("console:", [...new Set(errs)].slice(0, 12).join("\n"));
await browser.close();
server.close();
