// People and sheep of the demo, in metres: the viewer's own chibi figures (art/figure.js) posed for their work
// (art/motion.js) and the kit's sheep (art/animals.js), drawn as instanced parts (scene/batch.js), scaled from
// the kit's tile units to metres. People walk their paths continuously; level of detail by distance (full near, plainer
// further, none past about 650 m, where one would be under a pixel).
import * as THREE from "three";
import {toon} from "../art/toon.js";
import * as Fig from "../art/figure.js";
import * as A from "../art/animals.js";
import {pose} from "../art/motion.js";
import {Batch} from "../scene/batch.js";
import {looksOf, CLOTH, greyed, darker} from "../scene/people.js";

export const FIG = 2.8;               // metres to the kit's unit: a grown person stands about 1.75 m
const SHIRTS = [CLOTH.plain, CLOTH.linen, CLOTH.wool, CLOTH.hide, 0xb86a48, 0x9aa86a, CLOTH.linen, 0xc9a77a];
const HOLD = {sickle: "sickle", basket: "basket", hammer: "hammer", rod: "rod", axe: "axe"};

// where along a path one is at a distance s (looping), and which way one faces
function along(path, s, loop) {
  let L = 0;
  const seg = [];
  for (let k = 1; k < path.length; k++) { const l = Math.hypot(path[k][0] - path[k - 1][0], path[k][1] - path[k - 1][1]); seg.push(l); L += l; }
  if (!L) return {x: path[0][0], y: path[0][1], dx: 0, dy: 1, end: true, L};
  let end = false;
  if (loop) s = ((s % L) + L) % L; else if (s >= L) { s = L; end = true; }
  for (let k = 0; k < seg.length; k++) {
    if (s <= seg[k] || k === seg.length - 1) {
      const f = seg[k] ? Math.min(1, s / seg[k]) : 0, a = path[k], b = path[k + 1];
      return {x: a[0] + (b[0] - a[0]) * f, y: a[1] + (b[1] - a[1]) * f, dx: (b[0] - a[0]) / (seg[k] || 1), dy: (b[1] - a[1]) / (seg[k] || 1), end, L};
    }
    s -= seg[k];
  }
}

export class Folk {
  constructor(scene, land, data) {
    this.land = land; this.people = data.people; this.animals = data.animals; this.walker = data.walker;
    this.batch = new Batch(scene);
    const P = Fig.parts(), H = Fig.hairs(), W = Fig.wear(), T = Fig.tools(), LO = Fig.parts(1), B = this.batch;
    const skin = toon({color: 0xffffff}), cloth = toon({color: 0xffffff});
    const dark = new THREE.MeshBasicMaterial({color: 0x2a1e18}), white = new THREE.MeshBasicMaterial({color: 0xffffff});
    B.define("body", P.body, cloth, {shadow: true}); B.define("head", P.head, skin, {shadow: true});
    B.define("body:far", LO.body, cloth); B.define("head:far", LO.head, skin); B.define("hair:far", Fig.hairFar(), toon({color: 0xffffff}));
    B.define("arm", P.arm, cloth); B.define("hand", P.hand, skin); B.define("leg", P.leg, cloth); B.define("foot", P.foot, cloth);
    B.define("eye", P.eye, dark); B.define("shine", P.shine, white);
    for (const [k, g] of Object.entries(H)) B.define("hair:" + k, g, toon({color: 0xffffff}), {shadow: true});
    for (const [k, g] of Object.entries(W)) B.define("wear:" + k, g, toon({color: 0xffffff, side: k === "cape" ? THREE.DoubleSide : THREE.FrontSide}));
    for (const [k, g] of Object.entries(T)) B.define("tool:" + k, g, toon({color: Fig.TOOL_COLOR[k]}));
    B.define("sheep", A.body("sheep"), toon({color: 0xffffff}), {shadow: true});
    B.define("sheep:leg", A.leg(), toon({color: 0xffffff}));
    this.m = {root: new THREE.Matrix4(), body: new THREE.Matrix4(), head: new THREE.Matrix4(), limb: new THREE.Matrix4(), part: new THREE.Matrix4(),
      I: new THREE.Matrix4(), tmp: new THREE.Matrix4(), q: new THREE.Quaternion(), e: new THREE.Euler(), v: new THREE.Vector3(), s: new THREE.Vector3()};
    this.looks = this.people.map(p => ({...looksOf({id: p.id + 7, parents: []}), shirt: SHIRTS[p.id % SHIRTS.length]}));
    this.where = new Map();          // id -> {x, y, z, yaw}
    this.decks = [];                 // what one walks on above the ground: [x, y, half width, half length, angle, top]
  }

  mat(out, parent, x, y, z, pitch = 0, yaw = 0, roll = 0, sx = 1, sy = 1, sz = 1) {
    const {q, e, v, s, tmp} = this.m;
    e.set(pitch, yaw, roll, "YXZ"); q.setFromEuler(e);
    tmp.compose(v.set(x, y, z), q, s.set(sx, sy, sz));
    return out.multiplyMatrices(parent, tmp);
  }

  // where someone is at time t (seconds): on their path, or where they stand
  place(p, t) {
    if (p.path) {
      const loop = p.path.length > 2 && Math.hypot(p.path[0][0] - p.path.at(-1)[0], p.path[0][1] - p.path.at(-1)[1]) < 1;
      let s = t * p.speed;
      if (!loop && p.id !== this.walker) { const L = along(p.path, 0, false).L; s = s % (L + 20); }    // the carriers go round again
      const q = along(p.path, s, loop);
      return {x: q.x, y: q.y, yaw: Math.atan2(q.dx, q.dy), moving: !q.end};
    }
    const f = p.face ? Math.atan2(p.face[0] - p.pos[0], p.face[1] - p.pos[1]) : (p.id * 1.7) % 6.28;
    return {x: p.pos[0], y: p.pos[1], yaw: f, moving: false};
  }

  // the ground under one's feet, or a bridge's deck
  floor(x, y) {
    let h = this.land.height(x, y);
    for (const [bx, by, hw, hl, a, top] of this.decks) {
      const dx = x - bx, dy = y - by, u = dx * Math.cos(a) - dy * Math.sin(a), v = dx * Math.sin(a) + dy * Math.cos(a);
      if (Math.abs(u) < hw && Math.abs(v) < hl) h = Math.max(h, top);
    }
    return h;
  }

  update(t, cam, walkT = null) {
    const B = this.batch, M = this.m, I = M.I.identity(), cp = cam.position;
    B.begin();
    for (const p of this.people) {
      const look = this.looks[p.id];
      const pl = this.place(p, p.id === this.walker && walkT != null ? walkT : t);
      const ground = this.floor(pl.x, pl.y);
      const dist = Math.hypot(cp.x - pl.x, cp.y - ground, cp.z - pl.y);
      this.where.set(p.id, {x: pl.x, y: ground, z: pl.y, yaw: pl.yaw});
      if (dist > 650) continue;
      const lod = dist < 35 ? 0 : dist < 130 ? 1 : 2;
      const child = p.age < 14, grown = Math.min(1, 0.5 + p.age / 15 * 0.5), sc = grown * look.height * FIG;
      const headScale = 1 + (1 - grown) * 0.35;
      const verb = pl.moving ? "walk" : p.verb;
      const tt = p.id === this.walker && walkT != null ? walkT : t;
      const P = pose(verb, pl.moving, tt * (pl.moving ? Math.max(1, p.speed / 1.3) : 1), look.seed, p.verb === "talk", p.detail, p.holds === "sheaf" || p.holds === "pack" ? 0.6 : 0);
      if (P.lie) this.mat(M.root, I, pl.x, ground + 0.07 * sc, pl.y, -Math.PI / 2, pl.yaw, 0, sc, sc, sc);
      else this.mat(M.root, I, pl.x, ground + P.lift * sc, pl.y, 0, pl.yaw, 0, sc * look.round, sc, sc * look.round);
      this.mat(M.body, M.root, 0, Fig.JOINT.hip, 0, P.lean, 0, P.roll, 1, P.squash, 1);
      const lo = lod > 0 ? ":far" : "";
      B.push("body" + lo, M.body, look.shirt);
      this.mat(M.head, M.body, 0, Fig.JOINT.neck - Fig.JOINT.hip, 0, P.headPitch, P.headYaw, 0, headScale, headScale, headScale);
      B.push("head" + lo, M.head, look.skin);
      B.push(lod > 0 ? "hair:far" : "hair:" + look.style, M.head, p.age > 48 ? greyed(look.hair, Math.min(1, (p.age - 48) / 15)) : look.hair);
      if (!child && p.verb === "gather" && p.holds === "sickle") B.push("wear:strawHat", M.head, 0xe2c27a);
      if (lod === 2) continue;
      const tool = lod === 0 && !pl.moving ? HOLD[p.holds] : null;
      for (const side of [-1, 1]) {
        this.mat(M.limb, M.body, side * Fig.JOINT.armX, Fig.JOINT.shoulder - Fig.JOINT.hip, 0, side < 0 ? P.armL : P.armR, 0, (side < 0 ? P.spreadL : P.spreadR) * side);
        B.push("arm", M.limb, look.shirt);
        if (lod === 0) { B.push("hand", M.limb, look.skin); if (side > 0 && tool) B.push("tool:" + tool, M.limb); }
      }
      for (const side of [-1, 1]) {
        this.mat(M.limb, M.root, side * Fig.JOINT.legX, Fig.JOINT.hip, 0, side < 0 ? P.legL : P.legR);
        B.push("leg", M.limb, darker(look.shirt));
        if (lod === 0) B.push("foot", M.limb, 0x7a5534);
      }
      if (p.holds === "sheaf" || p.holds === "pack") {
        this.mat(M.part, M.body, 0, Fig.JOINT.shoulder - Fig.JOINT.hip, 0, 0, 0, 0, 1.1, 1.2, 1.1);
        B.push("wear:pack", M.part, p.holds === "sheaf" ? 0xe8bc52 : 0xa88a5c);
      }
      if (lod === 0) {
        const blink = Math.sin(t * 0.9 + look.seed * 3) > 0.985 ? 0.1 : 1;
        for (const side of [-1, 1]) {
          this.mat(M.part, M.head, side * 0.066, 0.158, 0.15, 0, 0, 0, 1, blink, 1);
          B.push("eye", M.part);
          if (blink > 0.5) { this.mat(M.part, M.head, side * 0.066 + 0.01, 0.176, 0.166); B.push("shine", M.part); }
        }
      }
    }
    // sheep: grazing, now and then lifting their heads
    const k = A.KINDS.sheep, ss = k.size / 0.5;
    for (const [i, a] of this.animals.entries()) {
      const g = this.land.height(a.pos[0], a.pos[1]);
      const dist = Math.hypot(cp.x - a.pos[0], cp.y - g, cp.z - a.pos[1]);
      if (dist > 650) continue;
      const graze = Math.sin(t * 0.4 + i * 1.7) > -0.2, yaw = a.angle * Math.PI / 180 + Math.sin(t * 0.05 + i) * 0.3;
      this.mat(M.root, I, a.pos[0], g, a.pos[1], graze ? 0.25 : 0, yaw, 0, FIG, FIG, FIG);
      B.push("sheep", M.root, i % 7 === 3 ? 0x8a7a6a : 0xf4efe4);
      if (dist > 120) continue;
      const L = k.legLen * ss;
      for (const [lx, lz] of [[-0.07, 0.13], [0.07, 0.13], [-0.07, -0.13], [0.07, -0.13]]) {
        this.mat(M.limb, M.root, lx * ss, L + 0.01, lz * ss, 0, 0, 0, ss, L, ss);
        B.push("sheep:leg", M.limb, 0x4a3a30);
      }
    }
    B.end();
  }
}
