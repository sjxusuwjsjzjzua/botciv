// LandTiles: the land of a whole towns world in metres, from its tile map (towns_spec §2.1, WP5). The same questions
// as LandFn (ground, height, treeCover, color, at), answered from the engine's tiles of 1 km: each field (height,
// water, forest, the kinds of ground) is a smooth surface through the tiles' centres, sampled through a slow warp so
// that no tile edge survives as a straight line; rivers are curves of a real width cut through their tiles; sea and
// lakes lie below the water level; settlements' ground is kept gentle. Pure: no three.js, runs in Node.
//
// The land: {tiles: [rows of terrain chars; "~" broad water, "r" a river's tile], x0, y0 (metres of the first tile's
// corner), tile (metres, 1000), seed, water_level, rivers: [{pts: [[X, Y, width]...]}], flats: [[X, Y, r]...]}
import {vnoise, smoothstep, Curve, PAL} from "./land.js";

const mix = (a, b, t) => a + (b - a) * t;
const cr = (p0, p1, p2, p3, t) => p1 + 0.5 * t * (p2 - p0 + t * (2 * p0 - 5 * p1 + 4 * p2 - p3 + t * (3 * (p1 - p2) + p3 - p0)));

// the ground's height (metres over the water) at a tile of each kind, before noise
export const BASE = {".": 8, ",": 6, "T": 11, "h": 30, "^": 80, "~": -7, "m": 2.2, "s": 2.4, "r": 4};
const KIND = {rock: "^", hill: "h", sand: "s", marsh: "m", forest: "T", rich: ","};
const hex = h => [((h >> 16) & 255) / 255, ((h >> 8) & 255) / 255, (h & 255) / 255];
const CROP = {wheat: hex(0xc9a040), flax: hex(0x5f8a38), fallow: hex(0x8d5a34), stubble: hex(0xd8bf78), ley: hex(0x93ad4a)};
export const TPAL = {sand: [0.8, 0.73, 0.5], rock: [0.53, 0.51, 0.47], marsh: [0.36, 0.47, 0.3], shore: [0.74, 0.68, 0.48]};

export class LandTiles {
  constructor(L) {
    this.L = L;
    this.W = L.water_level ?? 0;
    this.T = L.tiles; this.ny = L.tiles.length; this.nx = L.tiles[0].length;
    this.x0 = L.x0 ?? 0; this.y0 = L.y0 ?? 0; this.ts = L.tile ?? 1000; this.seed = L.seed ?? 0;
    this.rivers = (L.rivers || []).map(r => new Curve(r.pts.map(p => [p[0], p[1], p[2] ?? r.w ?? 30]), 300));
    const none = new Curve([[-1e7, -1e7, 1], [-1e7 + 1, -1e7, 1]]);
    this.river = this.rivers[0] || none;                 // what the step-0 scene draws as its river and stream
    this.stream = none;
    this.flats = L.flats || [];
    this.clearings = L.clearings || [];
    this.r = {h: 0, water: 0, wet: 0, tree: 0, level: this.W, chan: Infinity, shore: 0};
    // field strips (every settlement's): part of the land's colour, so they show from any height
    this.strips = new Map();
    for (const f of L.strips || []) {
      const xs = f.pts.map(p => p[0]), ys = f.pts.map(p => p[1]);
      for (let i = Math.floor(Math.min(...xs) / 250); i <= Math.floor(Math.max(...xs) / 250); i++)
        for (let j = Math.floor(Math.min(...ys) / 250); j <= Math.floor(Math.max(...ys) / 250); j++) {
          const k = i * 65536 + j;
          (this.strips.get(k) || this.strips.set(k, []).get(k)).push(f);
        }
    }
    this.cache = new Map();
  }

  ch(i, j) { return this.T[Math.max(0, Math.min(this.ny - 1, j))][Math.max(0, Math.min(this.nx - 1, i))]; }

  // the warp: where a point samples the tile grid (wanders up to about 0.3 of a tile, slowly)
  warp(X, Y) {
    const s = this.seed, a = 0.3 * this.ts;
    return [X + a * (vnoise(X / 650, Y / 650, s + 41) - 0.5) * 2 + 0.25 * a * (vnoise(X / 170, Y / 170, s + 43) - 0.5) * 2,
            Y + a * (vnoise(X / 650, Y / 650, s + 42) - 0.5) * 2 + 0.25 * a * (vnoise(X / 170, Y / 170, s + 44) - 0.5) * 2];
  }

  // a smooth field over the tiles' centres: f(char) -> number, Catmull-Rom (or bilinear when `soft` is false)
  field(X, Y, f, smooth = true) {
    const fx = (X - this.x0) / this.ts - 0.5, fy = (Y - this.y0) / this.ts - 0.5;
    const i = Math.floor(fx), j = Math.floor(fy), u = fx - i, v = fy - j;
    if (!smooth) {
      const a = f(this.ch(i, j)), b = f(this.ch(i + 1, j)), c = f(this.ch(i, j + 1)), d = f(this.ch(i + 1, j + 1));
      const su = u * u * (3 - 2 * u), sv = v * v * (3 - 2 * v);
      return mix(mix(a, b, su), mix(c, d, su), sv);
    }
    const row = jj => cr(f(this.ch(i - 1, jj)), f(this.ch(i, jj)), f(this.ch(i + 1, jj)), f(this.ch(i + 2, jj)), u);
    return cr(row(j - 1), row(j), row(j + 1), row(j + 2), v);
  }

  // how gentle the ground is kept (1 open land, 0.25 in a settlement)
  flatness(X, Y) {
    let amp = 1;
    for (const [fx, fy, fr] of this.flats) {
      const d = Math.hypot(X - fx, Y - fy);
      if (d < fr * 1.6) amp = Math.min(amp, 0.25 + 0.75 * smoothstep(fr * 0.6, fr * 1.4, d));
    }
    return amp;
  }

  ground(X, Y) {
    const r = this.r, W = this.W;
    const [wx, wy] = this.warp(X, Y);
    const wet = this.field(wx, wy, c => (c === "~" ? 1 : 0), false);          // broad water's share here
    let h = W + this.field(wx, wy, c => BASE[c] ?? 8);
    const amp = this.flatness(X, Y) * (1 - 0.7 * smoothstep(0.2, 0.5, wet));
    const rough = 1 + 2.5 * this.field(wx, wy, c => (c === "h" || c === "^" ? 1 : 0), false);
    h += amp * rough * ((vnoise(X / 170, Y / 170, 11) - 0.5) * 3.2 + (vnoise(X / 55, Y / 55, 12) - 0.5) * 1.1 + (vnoise(X / 19, Y / 19, 13) - 0.5) * 0.3);
    if (wet < 0.3) h = Math.max(h, W + 0.9);                            // no puddles in the open land
    else if (wet > 0.62) h = Math.min(h, W - 1.2);                       // and no islands of noise in the lakes
    r.water = 0; r.wet = 0; r.level = W; r.chan = Infinity;
    r.shore = 1 - smoothstep(0.5, 3, Math.abs(h - W));
    if (h < W) { r.water = W - h; r.chan = -1; }
    for (const rv of this.rivers) {
      const q = rv.near(X, Y);
      if (q.d === Infinity) continue;
      const hw = q.w / 2, edge = W + 0.35;
      let hc;
      if (q.d < hw) hc = edge - (edge - (W - 2.6)) * (1 - (q.d / hw) ** 2);
      else hc = mix(edge, h, smoothstep(hw, hw + 45, q.d));
      if (hc < h) h = hc;
      r.chan = Math.min(r.chan, q.d - hw);
      r.wet = Math.max(r.wet, 1 - smoothstep(hw + 2, hw + 22, q.d));
      if (q.d < hw) r.water = Math.max(r.water, W - h);
    }
    r.wet = Math.max(r.wet, 0.8 * this.field(wx, wy, c => (c === "m" ? 1 : 0), false));
    r.h = h;
    return r;
  }

  height(X, Y) { return this.ground(X, Y).h; }

  // broad water's share at a point (sea and lakes, not rivers): where the viewer lays its sheet of water
  broad(X, Y) {
    const [wx, wy] = this.warp(X, Y);
    return this.field(wx, wy, c => (c === "~" ? 1 : 0), false);
  }

  treeCover(X, Y, chan = Infinity) {
    const [wx, wy] = this.warp(X, Y);
    const f = this.field(wx, wy, c => (c === "T" ? 1 : c === "h" ? 0.12 : c === "m" ? 0.08 : 0), false);
    let cover = smoothstep(0.3, 0.7, f + (vnoise(X / 140, Y / 140, 21) - 0.5) * 0.35 + (vnoise(X / 40, Y / 40, 22) - 0.5) * 0.12);
    for (const [cx, cy, cr2] of this.clearings) cover *= smoothstep(cr2 * 0.75, cr2 * 1.35, Math.hypot(X - cx, Y - cy));
    for (const [fx, fy, fr] of this.flats) {
      const d = Math.hypot(X - fx, Y - fy);
      if (d < fr * 1.7) cover *= smoothstep(fr * 0.9, fr * 1.6, d);
    }
    return chan < 0 ? 0 : cover * smoothstep(3, 25, chan);
  }

  at(X, Y) {
    const r = this.ground(X, Y);
    r.tree = this.treeCover(X, Y, r.chan);
    return r;
  }

  // the strip a point lies in, if any
  strip(X, Y) {
    const list = this.strips.get(Math.floor(X / 250) * 65536 + Math.floor(Y / 250));
    if (!list) return null;
    for (const f of list) {
      let inside = false;
      const p = f.pts;
      for (let i = 0, j = p.length - 1; i < p.length; j = i++)
        if ((p[i][1] > Y) !== (p[j][1] > Y) && X < p[i][0] + (Y - p[i][1]) / (p[j][1] - p[i][1]) * (p[j][0] - p[i][0])) inside = !inside;
      if (inside) return f;
    }
    return null;
  }

  color(X, Y, out = [0, 0, 0]) {
    const r = this.at(X, Y), W = this.W;
    const st = this.strips.size ? this.strip(X, Y) : null;
    const [wx, wy] = this.warp(X, Y);
    const k = {};
    for (const [name, c] of Object.entries(KIND)) k[name] = this.field(wx, wy, t => (t === c ? 1 : 0), false);
    const n1 = vnoise(X / 90, Y / 90, 31), n2 = vnoise(X / 23, Y / 23, 32);
    for (let c = 0; c < 3; c++) {
      let v = mix(PAL.meadow[c], PAL.meadow2[c], smoothstep(0.35, 0.75, n1));
      v = mix(v, PAL.lush[c], Math.min(1, smoothstep(0.55, 0.8, n2) * 0.5 + smoothstep(0.3, 0.8, k.rich) * 0.55));
      v = mix(v, PAL.dry[c], Math.min(1, smoothstep(W + 18, W + 45, r.h) * 0.6 + k.hill * 0.35));
      v = mix(v, TPAL.rock[c], smoothstep(0.3, 0.8, k.rock + (n1 - 0.5) * 0.3) * 0.85);
      v = mix(v, TPAL.sand[c], smoothstep(0.3, 0.7, k.sand) * 0.8);
      v = mix(v, TPAL.marsh[c], smoothstep(0.25, 0.7, k.marsh) * 0.7);
      v = mix(v, PAL.wet[c], r.wet * 0.75);
      v = mix(v, PAL.forestFloor[c], smoothstep(0.05, 0.4, r.tree));
      v = mix(v, PAL.forest[c], smoothstep(0.35, 0.85, r.tree));
      v = mix(v, TPAL.shore[c], r.shore * 0.8);
      v = mix(v, PAL.bank[c], (1 - smoothstep(0.5, 3.5, r.chan)) * 0.85 * (r.chan > -1 ? 1 : 0));
      if (r.water > 0) v = mix(PAL.mud[c], PAL.bed[c], smoothstep(0, 1.5, r.water));
      if (st) v = mix(v, (CROP[st.crop] || CROP.fallow)[c], 0.92);
      out[c] = v * (0.94 + 0.12 * n2);
    }
    return out;
  }
}
