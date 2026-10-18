// The settlement as drawn: its ground painted finely into a map laid over the land (lanes with soft worn edges, the
// green, the yards, the strips with their crops and furrows, the burial ground), and on it the buildings, wattle
// fences with gates, crops standing in their strips, reeds at the water, the bridge, smoke. Everything from the
// scene's data in metres (towns_spec §3 shapes); nothing here knows of tiles.
import * as THREE from "three";
import * as V from "../art/village.js";
import {Curve, vnoise} from "./land.js";
import {ribbon, waterMaterial, wayMaterial} from "./water.js";

const deg = a => a * Math.PI / 180;

// ---------- the ground's fine paint ----------
export function paintDetail(data, box, px) {
  const [x0, y0, w, h] = box, W = Math.round(w * px), H = Math.round(h * px);
  const cv = document.createElement("canvas"); cv.width = W; cv.height = H;
  const g = cv.getContext("2d");
  g.setTransform(px, 0, 0, px, -x0 * px, -y0 * px);
  const poly = pts => { g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); for (const p of pts.slice(1)) g.lineTo(p[0], p[1]); g.closePath(); };
  const line = pts => { g.beginPath(); g.moveTo(pts[0][0], pts[0][1]); for (const p of pts.slice(1)) g.lineTo(p[0], p[1]); };
  const blur = m => { g.filter = m > 0 ? `blur(${(m * px).toFixed(1)}px)` : "none"; };
  const rnd = (() => { let a = 99; return () => { a = (a * 1664525 + 1013904223) >>> 0; return a / 4294967296; }; })();

  // yards: a fresher, shorter green, worn by the door and where the sheep stand
  blur(0.8);
  for (const p of data.plots) {
    g.fillStyle = p.use === "burial" ? "rgba(128,150,70,0.75)" : p.use === "pen" ? "rgba(150,132,84,0.65)" : "rgba(140,165,66,0.7)";
    poly(p.pts); g.fill();
  }
  blur(1.6);
  for (const b of data.buildings) {
    const a = deg(b.angle);
    if (b.kind === "long_house") {
      const d = b.size[1] / 2 + 1.5, fx = b.pos[0] + Math.sin(a) * d, fy = b.pos[1] + Math.cos(a) * d;
      g.fillStyle = "rgba(200,160,100,0.75)"; g.beginPath(); g.ellipse(fx, fy, 2.6, 3.4, -a, 0, Math.PI * 2); g.fill();
      g.fillStyle = "rgba(110,120,50,0.45)"; g.beginPath(); g.ellipse(b.pos[0], b.pos[1], b.size[0] / 2 + 1.6, b.size[1] / 2 + 1.6, -a, 0, Math.PI * 2); g.fill();
    } else if (b.kind === "stilt_store") {
      g.fillStyle = "rgba(150,120,70,0.55)"; g.beginPath(); g.arc(b.pos[0], b.pos[1], 2.2, 0, Math.PI * 2); g.fill();
    }
  }
  for (const a of data.animals) { if (rnd() < 0.5) { g.fillStyle = "rgba(170,140,85,0.35)"; g.beginPath(); g.arc(a.pos[0] + 1, a.pos[1], 1.6, 0, 7); g.fill(); } }
  // the kiln yard
  // the green, and its worn ring round the well
  const [gx, gy] = data.green.pos, [grx, gry] = data.green.r;
  blur(0.9); g.fillStyle = "rgba(150,182,78,0.95)"; g.beginPath(); g.ellipse(gx, gy, grx, gry, 0, 0, Math.PI * 2); g.fill();
  const wl = data.buildings.find(b => b.kind === "well"), sh = data.buildings.find(b => b.kind === "shrine");
  if (wl) {
    blur(0.7); g.fillStyle = "rgba(160,150,135,0.95)"; g.beginPath(); g.arc(wl.pos[0], wl.pos[1], 2.1, 0, 7); g.fill();
    blur(1.2); g.strokeStyle = "rgba(205,170,110,0.55)"; g.lineWidth = 1.6; g.beginPath(); g.arc(wl.pos[0], wl.pos[1], 3.6, 0, 7); g.stroke();
  }
  if (sh) { g.fillStyle = "rgba(205,170,110,0.5)"; g.beginPath(); g.ellipse(sh.pos[0], sh.pos[1] + 2.5, 3.4, 2.2, 0, 0, 7); g.fill(); }
  // strips: the crop's ground, furrows along each strip, grass balks between
  for (const f of data.fields) {
    const [a, b, c, d] = f.pts, along = Math.hypot(d[0] - a[0], d[1] - a[1]);
    blur(0.25);
    g.fillStyle = {wheat: "#c9a040", flax: "#5f8a38", fallow: "#8d5a34", stubble: "#d8bf78", ley: "#93ad4a"}[f.crop] || "#8d5a34";
    poly(f.pts); g.fill();
    g.save(); poly(f.pts); g.clip(); blur(0);
    const n = Math.floor(Math.hypot(b[0] - a[0], b[1] - a[1]) / 0.7);
    for (let k = 1; k < n; k++) {
      const t = k / n, p = [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t], q = [d[0] + (c[0] - d[0]) * t, d[1] + (c[1] - d[1]) * t];
      g.strokeStyle = f.crop === "fallow" ? "rgba(70,40,20,0.55)" : f.crop === "stubble" ? "rgba(150,120,60,0.45)" : "rgba(60,50,20,0.28)";
      g.lineWidth = f.crop === "fallow" ? 0.26 : 0.18; line([p, q]); g.stroke();
      if (f.crop === "fallow") { g.strokeStyle = "rgba(190,140,95,0.4)"; g.lineWidth = 0.12; line([[p[0] + 0.25, p[1]], [q[0] + 0.25, q[1]]]); g.stroke(); }
    }
    if (f.reaped_to) {                     // the reaped end: stubble, sheaves lying in rows
      const t = f.reaped_to, e = [a[0] + (d[0] - a[0]) * t, a[1] + (d[1] - a[1]) * t], e2 = [b[0] + (c[0] - b[0]) * t, b[1] + (c[1] - b[1]) * t];
      g.fillStyle = "#d9c07a"; poly([a, b, e2, e]); g.fill();
      g.strokeStyle = "rgba(150,120,60,0.45)"; g.lineWidth = 0.15;
      for (let k = 1; k < n; k++) { const tt = k / n; line([[a[0] + (b[0] - a[0]) * tt, a[1]], [a[0] + (b[0] - a[0]) * tt, e[1]]]); g.stroke(); }
    }
    g.restore();
    void along;
  }
  // lanes: a soft verge, then the packed earth, then wear (lighter in the middle, darker ruts)
  const lanes = data.lanes.filter(l => l.kind !== "track");
  const stroke = (l, extra, style, b) => { blur(b); g.strokeStyle = style; g.lineWidth = l.w + extra; g.lineCap = g.lineJoin = "round"; line(l.pts); if (l.closed) g.closePath(); g.stroke(); };
  for (const l of lanes) stroke(l, 1.6, "rgba(185,160,95,0.55)", 1.2);
  for (const l of lanes) stroke(l, 0, "rgb(212,182,134)", 0.45);
  for (const l of lanes) stroke(l, -l.w * 0.55, "rgba(228,202,158,0.6)", 0.8);
  // speckle: pebbles and tufts over everything painted, kept inside it
  blur(0);
  g.globalCompositeOperation = "source-atop";
  for (let k = 0; k < w * h / 9; k++) {
    const x = x0 + rnd() * w, y = y0 + rnd() * h, r = 0.08 + rnd() * 0.2;
    g.fillStyle = rnd() < 0.5 ? "rgba(90,70,40,0.22)" : "rgba(255,240,200,0.2)";
    g.fillRect(x, y, r, r);
  }
  g.globalCompositeOperation = "source-over";
  const tex = new THREE.CanvasTexture(cv);
  tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8; tex.generateMipmaps = true; tex.flipY = false;
  tex.minFilter = THREE.LinearMipmapLinearFilter; tex.magFilter = THREE.LinearFilter;
  return {tex, box, canvas: cv};
}

// ---------- the things standing on the land ----------
export class Town {
  constructor(scene, land, data, opts = {}) {
    this.scene = scene; this.land = land; this.data = data;
    this.tier = opts.tier || "high";
    // the streamed world (demo/live.js): the land's water drawn by it, reeds only in `box`, crops made when near
    this.opts = {water: true, box: null, lazy: false, ...opts};
    this.group = new THREE.Group(); this.group.name = "town"; scene.add(this.group);
    this.smokes = []; this.reedBlocks = [];
    this.stats = {};
    this.buildings();
    this.fences();
    this.crops();
    this.reeds();
    this.ways(opts.light);
  }

  add(geo, mat, n, each, {shadow = true, receive = true, depth = null} = {}) {
    const m = new THREE.InstancedMesh(geo, mat, n), M = new THREE.Matrix4(), c = new THREE.Color();
    let i = 0;
    each((pos, yaw, scale = [1, 1, 1], color = null) => {
      M.compose(new THREE.Vector3(...pos), new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), yaw), new THREE.Vector3(...scale));
      m.setMatrixAt(i, M); if (color != null) m.setColorAt(i, c.set(color)); i++;
    });
    m.count = i; m.castShadow = shadow; m.receiveShadow = receive;
    if (depth) m.customDepthMaterial = depth;
    m.computeBoundingSphere();
    this.group.add(m);
    return m;
  }

  ground(x, y) { return this.land.height(x, y); }

  buildings() {
    const byKind = new Map();
    for (const b of this.data.buildings) (byKind.get(b.kind) || byKind.set(b.kind, []).get(b.kind)).push(b);
    for (const [kind, list] of byKind) {
      // one shape per kind and size (long houses come in two lengths)
      const bySize = new Map();
      for (const b of list) { const k = (b.size || []).join("x"); (bySize.get(k) || bySize.set(k, []).get(k)).push(b); }
      for (const group of bySize.values()) {
        const made = V.buildingParts(kind, group[0]);
        for (const [geo, matName] of made.parts) {
          this.add(geo, V.material(matName), group.length, put => {
            for (const b of group) put([b.pos[0], this.placeY(b), b.pos[1]], deg(b.angle));
          }, {shadow: kind !== "grave_stone"});
        }
        if (made.smoke) for (const b of group) if (b.lit) {
          const a = deg(b.angle), [sx, sy, sz] = made.smoke;
          this.smokes.push([b.pos[0] + sx * Math.cos(a) + sz * Math.sin(a), this.placeY(b) + sy, b.pos[1] - sx * Math.sin(a) + sz * Math.cos(a), kind === "fire" ? 1.4 : 1]);
        }
      }
    }
    // hearth smoke through the thatch of a few houses
    for (const b of this.data.buildings.filter(b => b.kind === "long_house" && b.household % 3 === 1))
      this.smokes.push([b.pos[0], this.placeY(b) + 7.3, b.pos[1], 0.6]);
  }

  placeY(b) {
    if (b.kind === "plank_bridge") {
      const a = deg(b.angle), L = b.size[1] / 2;
      return Math.max(this.ground(b.pos[0] + Math.sin(a) * L, b.pos[1] + Math.cos(a) * L), this.ground(b.pos[0] - Math.sin(a) * L, b.pos[1] - Math.cos(a) * L)) + 0.12;
    }
    if (b.kind === "long_house" || b.kind === "conical_hut") {
      const a = deg(b.angle), hw = b.size[0] / 2, hd = b.size[1] / 2;
      let lo = Infinity;
      for (const [u, v] of [[-hw, -hd], [hw, -hd], [hw, hd], [-hw, hd], [0, 0]]) lo = Math.min(lo, this.ground(b.pos[0] + u * Math.cos(a) + v * Math.sin(a), b.pos[1] - u * Math.sin(a) + v * Math.cos(a)));
      return lo + 0.12;
    }
    return this.ground(b.pos[0], b.pos[1]) - 0.03;
  }

  fences() {
    const panels = [], posts = [];
    for (const p of this.data.plots) {
      const pts = p.pts;
      for (let e = 0; e < pts.length; e++) {
        const a = pts[e], b = pts[(e + 1) % pts.length], L = Math.hypot(b[0] - a[0], b[1] - a[1]);
        const dx = (b[0] - a[0]) / L, dy = (b[1] - a[1]) / L;
        // the gate: a gap in the middle of the gate edge, with a post either side
        const spans = e === (p.gate ?? -1) ? [[0, L / 2 - 1.6], [L / 2 + 1.6, L]] : [[0, L]];
        for (const [s0, s1] of spans) {
          const n = Math.max(1, Math.round((s1 - s0) / 2.2));
          for (let k = 0; k < n; k++) {
            const u0 = s0 + (s1 - s0) * k / n, u1 = s0 + (s1 - s0) * (k + 1) / n;
            const x = a[0] + dx * u0, y = a[1] + dy * u0, xm = a[0] + dx * (u0 + u1) / 2, ym = a[1] + dy * (u0 + u1) / 2;
            panels.push([x, this.ground(xm, ym) - 0.05, y, Math.atan2(-dy, dx), u1 - u0]);
            posts.push([x, this.ground(x, y) - 0.05, y]);
          }
          posts.push([a[0] + dx * s1, this.ground(a[0] + dx * s1, a[1] + dy * s1) - 0.05, a[1] + dy * s1]);
        }
      }
    }
    this.add(V.wattlePanel(), V.material("wattle"), panels.length, put => { for (const [x, y, z, yaw, l] of panels) put([x, y, z], yaw, [l, 1, 1]); });
    this.add(V.fencePost(), V.material("post"), posts.length, put => { posts.forEach(([x, y, z], i) => put([x, y, z], i, [1, 0.9 + (i * 7 % 5) * 0.05, 1])); });
    this.stats.fencePanels = panels.length;
  }

  // crops standing in their strips. Three levels of detail, each dithered into the next: close by, tufts of real
  // stalks and ears (instanced, one batch a strip, only strips near the eye drawn); further, the strip as stacked shells,
  // each a layer of the crop cut by a pattern of stalks (dense and cheap: a few triangles a strip); far, only the
  // strip's paint beneath (the same colour)
  crops() {
    const phone = this.tier === "phone", sp = 0.9, near = [32, 48], far = [520, 700];
    const tuftGeo = {wheat: V.wheatTuft(9, 1), flax: V.flaxTuft(10, 2)};
    const sheaves = [];
    let seed = 7;
    const r = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
    this.cropBlocks = [];
    let tufts = 0;
    for (const crop of ["wheat", "flax"]) {
      const tint = crop === "wheat" ? [0xffffff, 0xfff0d8, 0xf8e6c0] : [0xffffff, 0xe8f0e0, 0xf0f8ff];
      const strips = this.data.fields.filter(f => f.crop === crop);
      for (const f of strips) {
        if (this.opts.lazy) {
          const [a, , c] = f.pts;
          this.cropBlocks.push({f, crop, tint, mesh: null, cx: (a[0] + c[0]) / 2, cy: (a[1] + c[1]) / 2,
            r: Math.hypot(c[0] - a[0], c[1] - a[1]) / 2});
          continue;
        }
        const spots = [];
        const [a, b, c, d] = f.pts, wid = Math.hypot(b[0] - a[0], b[1] - a[1]), len = Math.hypot(d[0] - a[0], d[1] - a[1]);
        const nu = Math.max(1, Math.round((wid - 0.8) / sp)), nv = Math.max(1, Math.round((len - 0.8) / sp));
        for (let j = 0; j < nv; j++) for (let i = 0; i < nu; i++) {
          const u = (i + 0.5 + (r() - 0.5) * 0.7) / nu * (wid - 0.8) / wid + 0.4 / wid, v = (j + 0.5 + (r() - 0.5) * 0.7) / nv * (len - 0.8) / len + 0.4 / len;
          if (f.reaped_to && v < f.reaped_to) { if (r() < 0.06) sheaves.push([a[0] + (b[0] - a[0]) * u, a[1] + (d[1] - a[1]) * v, r() * 6.28]); continue; }
          const x = (a[0] * (1 - u) + b[0] * u) * (1 - v) + (d[0] * (1 - u) + c[0] * u) * v;
          const y = (a[1] * (1 - u) + b[1] * u) * (1 - v) + (d[1] * (1 - u) + c[1] * u) * v;
          spots.push([x, this.ground(x, y) - 0.02, y, r() * 6.28, 0.9 + r() * 0.25, r()]);
        }
        const m = this.add(tuftGeo[crop], V.material(crop, {fade: near}), spots.length, put => {
          for (const [x, y, z, yaw, s, t] of spots) put([x, y, z], yaw, [s, s * (0.95 + t * 0.1), s], tint[Math.floor(t * 3)]);
        }, {shadow: false});
        m.visible = false;
        const cx = (a[0] + c[0]) / 2, cy = (a[1] + c[1]) / 2;
        this.cropBlocks.push({mesh: m, cx, cy, r: Math.hypot(wid, len) / 2});
        tufts += spots.length;
      }
      // the shells
      const S = phone ? 7 : 11;
      const pos = [], lay = [], idx = [];
      for (const f of strips) {
        const [a, b, c, d] = f.pts, v0 = f.reaped_to || 0, len = Math.hypot(d[0] - a[0], d[1] - a[1]);
        const nv = Math.max(2, Math.ceil(len * (1 - v0) / 12));
        for (let k = 0; k < S; k++) {
          const base = pos.length / 3;
          for (let j = 0; j <= nv; j++) for (let i = 0; i <= 1; i++) {
            const u = i ? 0.995 : 0.005, v = v0 + (1 - v0) * j / nv;
            const x = (a[0] * (1 - u) + b[0] * u) * (1 - v) + (d[0] * (1 - u) + c[0] * u) * v;
            const y = (a[1] * (1 - u) + b[1] * u) * (1 - v) + (d[1] * (1 - u) + c[1] * u) * v;
            pos.push(x, this.ground(x, y), y); lay.push((k + 1) / S);
          }
          for (let j = 0; j < nv; j++) { const p = base + j * 2; idx.push(p, p + 2, p + 1, p + 1, p + 2, p + 3); }
        }
      }
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
      g.setAttribute("aLayer", new THREE.Float32BufferAttribute(lay, 1));
      g.setIndex(idx); g.computeBoundingSphere();
      const sm = new THREE.Mesh(g, shellMaterial(crop, near, far));
      sm.receiveShadow = true; sm.name = crop + " shells";
      this.group.add(sm);
    }
    this.stats.tufts = tufts;
    this.tuftGeo = tuftGeo; this.near = near;
    // sheaves lying where the reapers have been, and stooks standing
    const sheaf = new THREE.CylinderGeometry(0.13, 0.17, 0.8, 7); sheaf.rotateZ(Math.PI / 2); sheaf.translate(0, 0.14, 0);
    this.add(sheaf, V.material("thatch"), sheaves.length, put => { for (const [x, y, a] of sheaves) put([x, this.ground(x, y), y], a); });
    const stook = new THREE.ConeGeometry(0.7, 1.4, 7); stook.translate(0, 0.65, 0);
    const reap = this.data.fields.find(f => f.reaped_to);
    if (reap) {
      const [a, b, , d] = reap.pts, st = [0.3, 0.7].map(u => [a[0] + (b[0] - a[0]) * u, a[1] + (d[1] - a[1]) * reap.reaped_to * 0.45]);
      this.add(stook, V.material("thatch"), st.length, put => { for (const [x, y] of st) put([x, this.ground(x, y), y], x); });
    }
  }

  // one strip's tufts (the streamed world's, made when near): seeded by the strip, so the same each time
  tufts(blk) {
    const {f, crop, tint} = blk, sp = 0.9, spots = [];
    let seed = Math.floor(Math.abs(f.pts[0][0] * 7 + f.pts[0][1] * 13)) + 7;
    const r = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
    const [a, b, c, d] = f.pts, wid = Math.hypot(b[0] - a[0], b[1] - a[1]), len = Math.hypot(d[0] - a[0], d[1] - a[1]);
    const nu = Math.max(1, Math.round((wid - 0.8) / sp)), nv = Math.max(1, Math.round((len - 0.8) / sp));
    for (let j = 0; j < nv; j++) for (let i = 0; i < nu; i++) {
      const u = (i + 0.5 + (r() - 0.5) * 0.7) / nu * (wid - 0.8) / wid + 0.4 / wid, v = (j + 0.5 + (r() - 0.5) * 0.7) / nv * (len - 0.8) / len + 0.4 / len;
      const x = (a[0] * (1 - u) + b[0] * u) * (1 - v) + (d[0] * (1 - u) + c[0] * u) * v;
      const y = (a[1] * (1 - u) + b[1] * u) * (1 - v) + (d[1] * (1 - u) + c[1] * u) * v;
      spots.push([x, this.ground(x, y) - 0.02, y, r() * 6.28, 0.9 + r() * 0.25, r()]);
    }
    return this.add(this.tuftGeo[crop], V.material(crop, {fade: this.near}), spots.length, put => {
      for (const [x, y, z, yaw, s, t] of spots) put([x, y, z], yaw, [s, s * (0.95 + t * 0.1), s], tint[Math.floor(t * 3)]);
    }, {shadow: false});
  }

  // let go of everything this settlement drew (the shared materials stay)
  dispose() {
    this.scene.remove(this.group);
    this.group.traverse(o => {
      if (o.geometry) o.geometry.dispose();
      if (o.isInstancedMesh) o.dispose();
      if (o.material && /shells|river|sea|track/.test(o.name)) o.material.dispose();
    });
  }

  // a winter night: no standing crops, doors and the lantern lit
  setNight(on) {
    this.winter = on;
    for (const m of this.group.children) if (/shells/.test(m.name)) m.visible = !on;
    V.material("door").emissive.set(on ? 0xc87830 : 0x000000);
    V.material("lantern").emissive.set(on ? 0xffb050 : 0xffa040);
  }

  update(eye) {
    for (const b of this.cropBlocks) {
      const show = !this.winter && Math.hypot(eye.x - b.cx, eye.z - b.cy) - b.r < 52 && eye.y - (this.opts.lazy ? this.ground(b.cx, b.cy) : 0) < 80;
      if (this.opts.lazy) {                    // made as the eye comes near, let go when it is well away
        if (show && !b.mesh) b.mesh = this.tufts(b);
        else if (b.mesh && !show && Math.hypot(eye.x - b.cx, eye.z - b.cy) - b.r > 160) { this.group.remove(b.mesh); b.mesh.dispose(); b.mesh = null; }
      }
      if (b.mesh) b.mesh.visible = show;
    }
    for (const b of this.reedBlocks) b.mesh.visible = Math.hypot(eye.x - b.cx, eye.y - 10, eye.z - b.cy) - b.r < 460;
  }

  // reeds and cattails along the banks, in clumps, kept off the bridge and the landing
  reeds() {
    const spots = [], lanes = this.data.lanes.filter(l => l.kind !== "track").map(l => new Curve(l.pts.map(p => [p[0], p[1], l.w])));
    const box = this.opts.box || [-800, -300, 7600, 3400];
    let seed = 11;
    const r = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
    const ways = this.opts.box ? (this.land.rivers || []).map(c => [c, 1.3, [-0.5, 5.5]])
      : [[this.land.river, 1.3, [-0.5, 5.5]], [this.land.stream, 1.1, [0.0, 2.2]]];
    for (const [curve, step, off] of ways) {
      // in the streamed world, only the stretch of a curve that passes through the box
      let s0 = 0, s1 = curve.length;
      if (this.opts.box) {
        s0 = Infinity; s1 = -Infinity;
        for (let k = 0; k < curve.p.length; k++) {
          const [x, y] = curve.p[k];
          if (x >= box[0] - 200 && x <= box[2] + 200 && y >= box[1] - 200 && y <= box[3] + 200) { s0 = Math.min(s0, curve.s[k]); s1 = Math.max(s1, curve.s[k]); }
        }
        s0 = Math.max(0, s0 - 200); s1 = Math.min(curve.length, s1 + 200);
      }
      for (let s = s0; s < s1; s += step) {
        const p = curve.at(s);
        if (p.x < box[0] || p.x > box[2] || p.y < box[1] || p.y > box[3]) continue;
        for (const side of [-1, 1]) {
          if (vnoise(s / 22, side * 5, 41) < 0.42 || r() < 0.15) continue;
          const o = p.w / 2 + off[0] + r() * (off[1] - off[0]);
          const x = p.x - p.dy * o * side + (r() - 0.5) * 1.5, y = p.y + p.dx * o * side + (r() - 0.5) * 1.5;
          if (lanes.some(c => c.near(x, y).d < 7)) continue;
          const gr = this.land.ground(x, y);
          if (gr.water > 0.6) continue;
          spots.push([x, Math.max(gr.h, this.land.W) - 0.05, y, r() * 6.28, 1.3 + r() * 0.6]);
        }
      }
    }
    const geo = V.reedClump(3), mat = V.material("reed", {fade: [330, 450]}), blocks = new Map();
    for (const q of spots) { const k = Math.floor(q[0] / 200) * 1000 + Math.floor(q[2] / 200); (blocks.get(k) || blocks.set(k, []).get(k)).push(q); }
    for (const list of blocks.values()) {
      const m = this.add(geo, mat, list.length, put => { for (const [x, y, z, a, s] of list) put([x, y, z], a, [s, s * 0.9, s]); }, {shadow: false});
      m.visible = false;
      this.reedBlocks.push({mesh: m, cx: m.boundingSphere.center.x, cy: m.boundingSphere.center.z, r: m.boundingSphere.radius});
    }
    this.stats.reeds = spots.length;
  }

  ways(light) {
    const L = this.land;
    this.waterMat = waterMaterial(light.water);
    for (const [k, rv] of (this.opts.water ? L.rivers || [L.river] : []).entries()) {
      const river = new THREE.Mesh(ribbon(rv, {step: 8, cols: 9, y: () => L.W}), this.waterMat);
      river.renderOrder = 2; river.name = "river" + (k || "");
      this.group.add(river);
    }
    if (L.streamLevel && this.opts.water) {
      const smat = waterMaterial(light.water); smat.uniforms.uWidth.value = 7;
      const stream = new THREE.Mesh(ribbon(L.stream, {step: 2.5, cols: 5, y: (x, y, t, s) => L.streamLevel(s)}), smat);
      stream.renderOrder = 2; stream.name = "stream";
      this.group.add(stream);
    }
    if (L.T && this.opts.water) {             // sea and lakes: a sheet at the water's level over broad water only
      const [bx, by, bw, bh] = L.L.box, c = 125, nx = Math.ceil(bw / c), ny = Math.ceil(bh / c);
      const wet = new Float32Array((nx + 1) * (ny + 1));
      for (let j = 0; j <= ny; j++) for (let i = 0; i <= nx; i++) wet[j * (nx + 1) + i] = L.broad(bx + i * c, by + j * c);
      const pos = [], uv = [];
      for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
        const k = j * (nx + 1) + i;
        let m = 0;                            // this cell or one beside it has some broad water: the land hides the rest
        for (let dj = -1; dj <= 2; dj++) for (let di = -1; di <= 2; di++) {
          const ii = Math.min(nx, Math.max(0, i + di)), jj = Math.min(ny, Math.max(0, j + dj));
          m = Math.max(m, wet[jj * (nx + 1) + ii]);
        }
        if (m < 0.12) continue;
        const x0 = bx + i * c, y0 = by + j * c;
        // the shader's "across" (uv.y) fades the sheet out where broad water gives way to land: its edge is the shore
        for (const [di, dj] of [[0, 0], [0, 1], [1, 0], [1, 0], [0, 1], [1, 1]]) {
          const w = wet[(j + dj) * (nx + 1) + i + di];
          pos.push(x0 + di * c, L.W, y0 + dj * c); uv.push(x0 + di * c, 1.04 - 0.6 * Math.min(1, Math.max(0, (w - 0.36) / 0.26)));
        }
      }
      if (pos.length) {
        const g = new THREE.BufferGeometry();
        g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
        g.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
        g.computeBoundingSphere();
        const sea = new THREE.Mesh(g, waterMaterial(light.water, {bias: 0.0003, sheet: true}));
        sea.renderOrder = 2; sea.name = "sea";
        this.group.add(sea);
      }
    }
    const trs = this.data.lanes.filter(l => l.kind === "track");
    this.track = new Curve([[-1e7, -1e7, 1], [-1e7 + 1, -1e7, 1]]);
    for (const [k, tr] of trs.entries()) {
      const tc = new Curve(tr.pts.map(p => [p[0], p[1], tr.w]));
      if (!k) this.track = tc;
      const track = new THREE.Mesh(ribbon(tc, {step: 3, cols: 5, y: (x, y) => L.height(x, y) + 0.04}), wayMaterial(light.way));
      track.renderOrder = 1; track.name = "track";
      this.group.add(track);
    }
  }
}

// a crop as stacked shells: each layer keeps only where a stalk (or, near its top, an ear or flower) stands in a fine
// pattern of cells, so from above and aslant the strip reads as dense standing grain; lit like the toon materials
function shellMaterial(crop, [n0, n1], [f0, f1]) {
  const wheat = crop === "wheat";
  const m = new THREE.MeshToonMaterial({color: 0xffffff, gradientMap: V.material("thatch").gradientMap, side: THREE.DoubleSide});
  m.customProgramCacheKey = () => "shell-" + crop;
  m.onBeforeCompile = sh => {
    Object.assign(sh.uniforms, {uEye: V.EYE, uTime: {value: 0}, uWind: {value: 1}});
    sh.uniforms.uTime = V.LIVING.uTime; sh.uniforms.uWind = V.LIVING.uWind;
    sh.vertexShader = sh.vertexShader
      .replace("#include <common>", `#include <common>
        attribute float aLayer; uniform vec3 uEye; uniform float uTime; uniform float uWind; varying float vLayer; varying vec2 vXZ; varying float vFade; varying float vDist;`)
      .replace("#include <beginnormal_vertex>", `#include <beginnormal_vertex>
        objectNormal = vec3(0.0, 1.0, 0.0);`)
      .replace("#include <begin_vertex>", `#include <begin_vertex>
        float hgt = ${wheat ? "1.05" : "0.78"};
        vLayer = aLayer; vXZ = position.xz;
        transformed.y += aLayer * hgt;
        float sway = aLayer * aLayer * 0.09 * uWind;
        transformed.x += sway * sin(uTime * 1.6 + position.x * 0.35 + position.z * 0.2);
        transformed.z += sway * 0.6 * sin(uTime * 2.1 + position.z * 0.4);
        float de = distance(position, uEye); vDist = de;
        vFade = smoothstep(${n0.toFixed(1)}, ${n1.toFixed(1)}, de) * (1.0 - smoothstep(${f0.toFixed(1)}, ${f1.toFixed(1)}, de));
        if (vFade <= 0.0) transformed = vec3(0.0);`);
    sh.fragmentShader = sh.fragmentShader
      .replace("#include <common>", `#include <common>
        varying float vLayer; varying vec2 vXZ; varying float vFade; varying float vDist;
        float sh1(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
        ${V.DITHER}`)
      .replace("#include <clipping_planes_fragment>", `#include <clipping_planes_fragment>
        if (vFade < bayer4()) discard;
        // tufts on a jittered metre grid, each a dome of stalks: dense in the middle, lower at its rim
        vec2 tc = vXZ / 0.95, ti = floor(tc);
        vec2 tcen = ti + 0.5 + (vec2(sh1(ti + 3.0), sh1(ti + 5.0)) - 0.5) * 0.35;
        float td = length(tc - tcen) * 2.0;                       // 0 at the tuft's middle, 1 at its rim
        float rnd = sh1(ti);
        float top = (0.82 + 0.18 * sh1(ti + 17.0)) * (1.0 - 0.32 * td * td);
        vec2 cell = vXZ / ${wheat ? "0.17" : "0.15"};
        vec2 ci = floor(cell), cf = fract(cell) - 0.5;
        float rr = length(cf - (vec2(sh1(ci + 3.0), sh1(ci + 5.0)) - 0.5) * 0.35);
        float earZone = smoothstep(top - ${wheat ? "0.28" : "0.12"}, top - ${wheat ? "0.2" : "0.08"}, vLayer);
        float rad = mix(${wheat ? "0.14" : "0.11"}, ${wheat ? "0.5" : "0.4"}, earZone) * (1.0 - smoothstep(top - 0.04, top, vLayer));
        rad *= mix(1.0, 1.35, smoothstep(80.0, 300.0, vDist));
        if (td > 1.15 || vLayer > top || rr > rad) discard;`)
      .replace("#include <color_fragment>", `#include <color_fragment>
        vec3 stem = ${wheat ? "vec3(0.62, 0.47, 0.17)" : "vec3(0.25, 0.43, 0.15)"};
        vec3 earc = ${wheat ? "mix(vec3(0.86, 0.6, 0.16), vec3(0.97, 0.78, 0.36), smoothstep(0.6, 1.0, vLayer))" : "(rnd < 0.4 ? vec3(0.42, 0.58, 0.95) : vec3(0.36, 0.58, 0.22))"};
        diffuseColor.rgb = mix(stem, earc, earZone) * (0.5 + 0.5 * smoothstep(0.0, 0.8, vLayer)) * (0.88 + 0.24 * rnd) * (1.0 - 0.25 * td * td);`);
  };
  return m;
}
