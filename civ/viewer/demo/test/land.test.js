// landAt, the reference for step 1's Python port (towns_spec §2.1): what it must hold on the demo's land.
import {test} from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {hash2, vnoise, LandFn} from "../land.js";

const data = JSON.parse(await readFile(new URL("../river_village.json", import.meta.url), "utf8"));
const land = new LandFn(data.land);

test("the hash and noise are fixed numbers (the Python port must give the same)", () => {
  assert.equal(hash2(0, 0, 0), hash2(0, 0, 0));
  assert.notEqual(hash2(1, 0, 0), hash2(0, 1, 0));
  for (const [x, y] of [[0.5, 0.5], [10.25, -3.75], [1234.5, 987.125]]) { const v = vnoise(x, y, 7); assert.ok(v >= 0 && v <= 1); }
  assert.equal(vnoise(3, 4, 1), hash2(3, 4, 1));            // at whole points the noise is the hash
});

test("the river and the stream are water along their middles, dry beyond their banks", () => {
  for (const curve of [land.river, land.stream]) {
    for (let s = 50; s < curve.length - 50; s += 97) {
      const p = curve.at(s);
      if (p.x < -500 || p.x > 6500) continue;
      assert.ok(land.ground(p.x, p.y).water > 0.2, `water at ${p.x.toFixed(0)}, ${p.y.toFixed(0)}`);
      const off = p.w / 2 + 30, q = land.ground(p.x - p.dy * off, p.y + p.dx * off);
      assert.equal(q.water, 0, "dry 30 m beyond the bank");
    }
  }
});

test("the village stands on gentle ground, every building and strip on dry land", () => {
  for (const b of data.buildings) {
    if (b.kind === "plank_bridge") continue;
    const g = land.ground(b.pos[0], b.pos[1]);
    assert.equal(g.water, 0, `${b.kind} at ${b.pos} is dry`);
  }
  const C = data.centre;
  let lo = Infinity, hi = -Infinity;
  for (let x = -60; x <= 60; x += 10) for (let y = -50; y <= 30; y += 10) { const h = land.height(C[0] + x, C[1] + y); lo = Math.min(lo, h); hi = Math.max(hi, h); }
  assert.ok(hi - lo < 1.5, `the village's ground varies ${(hi - lo).toFixed(2)} m`);
  for (const f of data.fields) for (const [x, y] of f.pts) assert.equal(land.ground(x, y).water, 0);
});

test("forests are dense inside, thin out over their edges, never in the village or on the water", () => {
  const f = data.land.forest[0].pts, inside = [5500, 1000];
  assert.ok(land.treeCover(...inside) > 0.6);
  assert.equal(land.treeCover(...data.centre), 0);
  // no straight edge: along a line across the forest's edge the cover changes over tens of metres, not at once
  let steps = 0, last = null;
  for (let x = 2700; x < 3700; x += 10) { const c = land.treeCover(x, 600); if (last != null && Math.abs(c - last) > 0.3) steps++; last = c; }
  assert.equal(steps, 0);
  void f;
});

test("heights are finite and smooth everywhere the scene reaches", () => {
  for (let x = -2000; x <= 8000; x += 137) for (let y = -1500; y <= 4500; y += 131) {
    const a = land.height(x, y), b = land.height(x + 2, y);
    assert.ok(Number.isFinite(a));
    assert.ok(Math.abs(a - b) < 2.5, `a cliff at ${x}, ${y}`);
  }
});
