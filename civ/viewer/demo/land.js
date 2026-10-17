// landAt(X, Y): the land in metres, one deterministic function of the scene's data (towns_spec §2.1): the ground's
// height, the water (river and stream as curves of a real width), wetness (the reed margins), tree cover (forests
// feathered by noise, never a straight edge) and the ground's colour as a smooth blend. Never stored; step 1 ports it
// to Python (civ/land_at.py) and tests both on the same points. Pure: no three.js, runs in Node.
//
// Coordinates: X east, Y south, metres. Heights in metres.

// an integer hash and value noise, the same in any language (step 1 ports these exactly)
export function hash2(i, j, seed = 0) {
  let h = Math.imul(i | 0, 374761393) + Math.imul(j | 0, 668265263) + Math.imul(seed | 0, 2246822519);
  h = Math.imul(h ^ (h >>> 13), 1274126177);
  h ^= h >>> 16;
  return (h >>> 0) / 4294967296;
}
export function vnoise(x, y, seed = 0) {
  const i = Math.floor(x), j = Math.floor(y);
  let u = x - i, v = y - j;
  u = u * u * (3 - 2 * u); v = v * v * (3 - 2 * v);
  const a = hash2(i, j, seed), b = hash2(i + 1, j, seed), c = hash2(i, j + 1, seed), d = hash2(i + 1, j + 1, seed);
  return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v;
}
export const smoothstep = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const mix = (a, b, t) => a + (b - a) * t;

// a polyline with a width at each point, made fast to ask "how far, how wide, how far along" of any point
export class Curve {
  constructor(pts, cell = 200) {
    this.p = pts.map(q => [q[0], q[1], q[2] ?? 0]);
    this.s = [0];
    for (let k = 1; k < this.p.length; k++) this.s.push(this.s[k - 1] + Math.hypot(this.p[k][0] - this.p[k - 1][0], this.p[k][1] - this.p[k - 1][1]));
    this.length = this.s[this.s.length - 1];
    this.maxW = Math.max(...this.p.map(q => q[2]));
    // segments binned in a coarse grid for quick lookups
    this.cell = cell; this.bins = new Map();
    const pad = this.maxW + 120;
    for (let k = 0; k < this.p.length - 1; k++) {
      const [ax, ay] = this.p[k], [bx, by] = this.p[k + 1];
      const x0 = Math.floor((Math.min(ax, bx) - pad) / cell), x1 = Math.floor((Math.max(ax, bx) + pad) / cell);
      const y0 = Math.floor((Math.min(ay, by) - pad) / cell), y1 = Math.floor((Math.max(ay, by) + pad) / cell);
      for (let i = x0; i <= x1; i++) for (let j = y0; j <= y1; j++) {
        const key = i * 65536 + j;
        (this.bins.get(key) || this.bins.set(key, []).get(key)).push(k);
      }
    }
    this.out = {d: Infinity, w: 0, s: 0, k: -1, x: 0, y: 0};
  }
  // the nearest point: distance d, the width there w, how far along s; d = Infinity if beyond the padding
  near(X, Y) {
    const o = this.out; o.d = Infinity; o.k = -1;
    const segs = this.bins.get(Math.floor(X / this.cell) * 65536 + Math.floor(Y / this.cell));
    if (!segs) return o;
    for (const k of segs) {
      const a = this.p[k], b = this.p[k + 1], dx = b[0] - a[0], dy = b[1] - a[1], L2 = dx * dx + dy * dy;
      let t = L2 > 0 ? ((X - a[0]) * dx + (Y - a[1]) * dy) / L2 : 0;
      t = t < 0 ? 0 : t > 1 ? 1 : t;
      const px = a[0] + dx * t, py = a[1] + dy * t, d = Math.hypot(X - px, Y - py);
      if (d < o.d) { o.d = d; o.k = k; o.w = a[2] + (b[2] - a[2]) * t; o.s = this.s[k] + (this.s[k + 1] - this.s[k]) * t; o.x = px; o.y = py; }
    }
    return o;
  }
  // a point (and the direction) at a distance along
  at(s) {
    s = Math.max(0, Math.min(this.length, s));
    let k = 0;
    while (k < this.s.length - 2 && this.s[k + 1] < s) k++;
    const a = this.p[k], b = this.p[k + 1], L = this.s[k + 1] - this.s[k] || 1, t = (s - this.s[k]) / L;
    return {x: a[0] + (b[0] - a[0]) * t, y: a[1] + (b[1] - a[1]) * t, w: a[2] + (b[2] - a[2]) * t, dx: (b[0] - a[0]) / L, dy: (b[1] - a[1]) / L};
  }
}

// signed distance to a polygon (negative inside)
function polySD(poly, X, Y) {
  let d = Infinity, inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const [ax, ay] = poly[j], [bx, by] = poly[i], dx = bx - ax, dy = by - ay;
    const t = Math.max(0, Math.min(1, ((X - ax) * dx + (Y - ay) * dy) / (dx * dx + dy * dy)));
    d = Math.min(d, Math.hypot(X - ax - dx * t, Y - ay - dy * t));
    if ((ay > Y) !== (by > Y) && X < ax + (Y - ay) / (by - ay) * dx) inside = !inside;
  }
  return inside ? -d : d;
}

// Catmull-Rom on four values: a smooth surface through the coarse heights (no creases at the 250 m lines)
const cr = (p0, p1, p2, p3, t) => p1 + 0.5 * t * (p2 - p0 + t * (2 * p0 - 5 * p1 + 4 * p2 - p3 + t * (3 * (p1 - p2) + p3 - p0)));

export const PAL = {
  meadow: [0.49, 0.6, 0.29], meadow2: [0.57, 0.62, 0.31], lush: [0.44, 0.56, 0.26], wet: [0.44, 0.58, 0.27],
  forest: [0.2, 0.33, 0.17], forestFloor: [0.33, 0.43, 0.21], bank: [0.78, 0.66, 0.43], mud: [0.55, 0.45, 0.3],
  dry: [0.66, 0.65, 0.38], bed: [0.42, 0.48, 0.42],
};

export class LandFn {
  constructor(L) {
    this.L = L;
    this.W = L.water_level;
    const H = L.heights;
    this.hg = H;
    this.river = new Curve(L.river);
    this.stream = new Curve(L.stream);
    this.forests = L.forest.map(f => ({pts: f.pts, density: f.density, box: bbox(f.pts, 400)}));
    this.clearings = L.clearings || [];
    this.flat = L.flat || null;             // [x, y, r]: ground kept gentle (a settlement)
    this.r = {h: 0, water: 0, wet: 0, tree: 0, level: 0, chan: 0};
  }

  coarse(X, Y) {
    const H = this.hg, fx = (X - H.x0) / H.step, fy = (Y - H.y0) / H.step;
    const i = Math.floor(fx), j = Math.floor(fy), u = fx - i, v = fy - j;
    const g = (a, b) => H.h[Math.max(0, Math.min(H.ny - 1, b))][Math.max(0, Math.min(H.nx - 1, a))];
    const row = jj => cr(g(i - 1, jj), g(i, jj), g(i + 1, jj), g(i + 2, jj), u);
    return cr(row(j - 1), row(j), row(j + 1), row(j + 2), v);
  }

  // the natural ground, before the water cuts it
  natural(X, Y) {
    let h = this.coarse(X, Y);
    let amp = 1;
    if (this.flat) amp = 0.25 + 0.75 * smoothstep(this.flat[2] * 0.6, this.flat[2] * 1.4, Math.hypot(X - this.flat[0], Y - this.flat[1]));
    h += amp * ((vnoise(X / 170, Y / 170, 11) - 0.5) * 3.2 + (vnoise(X / 55, Y / 55, 12) - 0.5) * 1.1 + (vnoise(X / 19, Y / 19, 13) - 0.5) * 0.3);
    return Math.max(h, this.W + 1.3);
  }

  // the stream's water level along it: it comes down to the river's at its mouth
  streamLevel(s) { return this.W + 0.1 + 0.45 * smoothstep(0, 320, this.stream.length - s); }

  // everything at a point; returns a shared object (copy what you keep)
  at(X, Y) {
    const r = this.ground(X, Y);
    r.tree = this.treeCover(X, Y, r.chan);
    return r;
  }

  // the ground and water only (no tree cover): what heights need
  ground(X, Y) {
    const r = this.r;
    let h = this.natural(X, Y);
    r.water = 0; r.wet = 0; r.level = this.W; r.chan = Infinity;
    // the river: a bed under its width, banks rising over 40 m to the meadow
    const rv = this.river.near(X, Y);
    if (rv.d < Infinity) {
      const hw = rv.w / 2, edge = this.W + 0.35;
      let hc;
      if (rv.d < hw) hc = edge - (edge - (this.W - 2.6)) * (1 - (rv.d / hw) ** 2);
      else hc = mix(edge, h, smoothstep(hw, hw + 45, rv.d));
      if (hc < h) h = hc;
      r.chan = rv.d - hw;
      r.wet = Math.max(r.wet, 1 - smoothstep(hw + 2, hw + 22, rv.d));
      if (rv.d < hw) { r.water = this.W - h; r.level = this.W; }
    }
    const st = this.stream.near(X, Y);
    if (st.d < Infinity) {
      const hw = st.w / 2, lv = this.streamLevel(st.s), edge = lv + 0.25;
      let hc;
      if (st.d < hw) hc = edge - (edge - (lv - 0.9)) * (1 - (st.d / hw) ** 2);
      else hc = mix(edge, h, smoothstep(hw, hw + 14, st.d));
      if (hc < h) h = hc;
      r.chan = Math.min(r.chan, st.d - hw);
      r.wet = Math.max(r.wet, 1 - smoothstep(hw + 1, hw + 7, st.d));
      if (st.d < hw) { r.water = Math.max(r.water, lv - h); r.level = lv; }
    }
    r.h = h;
    return r;
  }

  height(X, Y) { return this.ground(X, Y).h; }

  treeCover(X, Y, chan = Infinity) {
    let cover = 0;
    for (const f of this.forests) {
      if (X < f.box[0] || X > f.box[2] || Y < f.box[1] || Y > f.box[3]) continue;
      const sd = polySD(f.pts, X, Y) + (vnoise(X / 140, Y / 140, 21) - 0.5) * 170 + (vnoise(X / 40, Y / 40, 22) - 0.5) * 40;
      cover = Math.max(cover, f.density * (1 - smoothstep(-90, 70, sd)));
    }
    for (const [cx, cy, cr] of this.clearings) cover *= smoothstep(cr * 0.75, cr * 1.35, Math.hypot(X - cx, Y - cy));
    if (this.flat) cover *= smoothstep(this.flat[2] * 0.9, this.flat[2] * 1.6, Math.hypot(X - this.flat[0], Y - this.flat[1]));
    return cover * smoothstep(3, 25, chan);
  }

  // the ground's colour (linear 0..1 RGB, written into out) as a smooth blend of the land's kinds
  color(X, Y, out = [0, 0, 0]) {
    const r = this.at(X, Y);
    const n1 = vnoise(X / 90, Y / 90, 31), n2 = vnoise(X / 23, Y / 23, 32);
    for (let c = 0; c < 3; c++) {
      let v = mix(PAL.meadow[c], PAL.meadow2[c], smoothstep(0.35, 0.75, n1));
      v = mix(v, PAL.lush[c], smoothstep(0.55, 0.8, n2) * 0.5);
      // higher ground drier, yellower
      v = mix(v, PAL.dry[c], smoothstep(this.W + 14, this.W + 40, r.h) * 0.6);
      v = mix(v, PAL.wet[c], r.wet * 0.75);
      v = mix(v, PAL.forestFloor[c], smoothstep(0.05, 0.4, r.tree));
      v = mix(v, PAL.forest[c], smoothstep(0.35, 0.85, r.tree));
      // banks: a strip of warm earth at the water's edge, then the bed
      v = mix(v, PAL.bank[c], (1 - smoothstep(0.5, 3.5, r.chan)) * 0.85);
      if (r.water > 0) v = mix(PAL.mud[c], PAL.bed[c], smoothstep(0, 1.2, r.water));
      out[c] = v * (0.94 + 0.12 * n2);
    }
    return out;
  }
}

function bbox(pts, pad = 0) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const [x, y] of pts) { x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x); y1 = Math.max(y1, y); }
  return [x0 - pad, y0 - pad, x1 + pad, y1 + pad];
}
