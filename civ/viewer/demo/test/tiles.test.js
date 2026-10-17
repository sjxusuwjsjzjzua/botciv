// LandTiles: a whole towns world's land from its tiles (towns_spec §2.1): water where the map has water and dry land
// where it has land, rivers wet along their middles only, forest where the forest tiles are, and no tile edge left
// as a straight line.
import {test} from "node:test";
import assert from "node:assert/strict";
import {LandTiles} from "../tiles.js";

// 12 x 10 tiles: sea along the west, a forest block, hills, a river running east-west through row 6
const rows = [
  "~~~~........",
  "~~~.....TTTT",
  "~~~.....TTTT",
  "~~......TTTT",
  "~~.....hhh..",
  "~~.....hhh..",
  "~~rrrrrrrrrr",
  "~~,,,,,,,,,,",
  "~~~.........",
  "~~~~........",
];
const T = 1000;
const river = [];
for (let i = 2; i <= 12; i++) river.push([i * T, 6.5 * T, 40]);
const land = new LandTiles({tiles: rows, x0: 0, y0: 0, tile: T, seed: 3, water_level: 0,
  rivers: [{pts: river}], flats: [[5500, 8500, 120]]});
const centre = (i, j) => [(i + 0.5) * T, (j + 0.5) * T];

test("broad water is water at its tiles' middles; land tiles are dry", () => {
  for (let j = 0; j < rows.length; j++) for (let i = 0; i < 12; i++) {
    const c = rows[j][i], [X, Y] = centre(i, j);
    const g = land.ground(X, Y);
    if (c === "~" && (rows[j][i + 1] === "~" || i === 0)) assert.ok(g.water > 0.5, `water at ${i},${j}`);
    if (c !== "~" && c !== "r" && rows[j][i - 1] !== "~" && rows[j][i + 1] !== "~" && j !== 5 && j !== 7)
      assert.equal(g.water, 0, `dry at ${i},${j}`);
  }
});

test("a river is water along its middle and dry 40 m beyond its banks", () => {
  for (let X = 3500; X < 11500; X += 731) {
    assert.ok(land.ground(X, 6.5 * T).water > 0.2, `water at ${X}`);
    assert.equal(land.ground(X, 6.5 * T + 60).water, 0, `dry beyond at ${X}`);
  }
});

test("forest stands on the forest tiles, not on the meadow", () => {
  assert.ok(land.treeCover(...centre(10, 2)) > 0.7);
  assert.ok(land.treeCover(...centre(4, 2)) < 0.05);
});

test("no tile edge survives: where forest meets meadow, the edge wanders", () => {
  // the forest's west edge is the line X = 8000 on the map; along it, find where cover crosses one half
  const xs = [];
  for (let Y = 1400; Y < 3600; Y += 150) {
    let X = 7000;
    while (X < 9000 && land.treeCover(X, Y) < 0.5) X += 10;
    xs.push(X);
  }
  const spread = Math.max(...xs) - Math.min(...xs);
  assert.ok(spread > 80, `the edge wanders ${spread} m`);
  assert.ok(Math.max(...xs) < 9000 && Math.min(...xs) > 7000, "and stays near where the map puts it");
});

test("hills stand higher than the meadow; a settlement's ground is gentle; heights are finite", () => {
  assert.ok(land.height(...centre(8, 4)) > land.height(...centre(4, 8)) + 10);
  let lo = Infinity, hi = -Infinity;
  for (let x = -60; x <= 60; x += 10) for (let y = -60; y <= 60; y += 10) {
    const h = land.height(5500 + x, 8500 + y); lo = Math.min(lo, h); hi = Math.max(hi, h);
  }
  assert.ok(hi - lo < 2.5, `the settlement's ground varies ${(hi - lo).toFixed(2)} m`);
  for (let X = -500; X < 12500; X += 377) for (let Y = -500; Y < 10500; Y += 377) assert.ok(Number.isFinite(land.height(X, Y)));
});

test("colours are in range everywhere", () => {
  const c = [0, 0, 0];
  for (let X = 0; X < 12000; X += 613) for (let Y = 0; Y < 10000; Y += 613) {
    land.color(X, Y, c);
    for (const v of c) assert.ok(v >= 0 && v <= 1.2, `colour ${v} at ${X},${Y}`);
  }
});
