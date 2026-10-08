// People in the land: chibi figures (art/figure.js) posed for what they do (art/motion.js), drawn as shared
// instanced parts (scene/batch.js). Each looks like themselves (seeded; children take after their parents),
// wears what they wear, holds what fits the task from what they carry, walks smoothly between the
// recorded hours, faces whom they talk to or strike, and goes indoors to sleep. Far off, simpler.
// .pos: id -> where they stand now (for the camera, picking and words over heads).
import * as THREE from "three";
import {toon} from "../art/toon.js";
import {rng, hash as hashOf} from "../art/look.js";
import * as Fig from "../art/figure.js";
import {pose, held, toolFor} from "../art/motion.js";
import {Batch} from "./batch.js";

const SKIN = [0xf8dcc2, 0xf0c8a0, 0xdcab80, 0xbf8660, 0x95623f, 0x6e4632];
const HAIR = [0x2b2018, 0x4a3020, 0x7a4a26, 0xb07a3e, 0xe0b870, 0x9a4222, 0x1c1c22];
export const CLOTH = {plain: 0xc9a77a, hide: 0xa8784c, linen: 0xefe6d2, wool: 0x8ea3c4, fine: 0xc0503e, fur: 0x8a6446, robe: 0x7a5a9a};

export function looksOf(person) {
  // children take after their parents: each feature from one parent's seed more often than not
  const r = rng("look" + person.id);
  const parents = (person.parents || []).map(id => rng("look" + id));
  const from = arr => { const src = parents.length && r() < 0.65 ? parents[Math.floor(r() * parents.length)] : r; return arr[Math.floor(src() * arr.length)]; };
  return {skin: from(SKIN), hair: from(HAIR), style: Fig.HAIR_STYLES[Math.floor(r() * Fig.HAIR_STYLES.length)],
    height: 0.94 + r() * 0.12, round: 0.92 + r() * 0.16, blush: r() < 0.7, seed: r() * 100};
}

export function dress(inv, cat) {
  const worn = Object.keys(inv || {}).filter(k => cat.items[k]?.class === "worn");
  const has = re => worn.find(k => re.test(k));
  const top = has(/tunic|robe/), over = has(/cloak|coat/);
  const clothOf = k => !k ? CLOTH.plain : /fur/.test(k) ? CLOTH.fur : /wool/.test(k) ? CLOTH.wool : /linen/.test(k) ? CLOTH.linen :
    /fine/.test(k) ? CLOTH.fine : /robe/.test(k) ? CLOTH.robe : CLOTH.hide;
  return {shirt: clothOf(top), cape: over ? clothOf(over) : null, robe: !!has(/robe/), hat: has(/fur_hat/) ? "furHat" : has(/hat/) ? "strawHat" : null,
    shoes: has(/boots/) ? 0x5a3d26 : has(/shoes/) ? 0x7a5534 : null, necklace: !!has(/necklace|torc|beads/)};
}

export const greyed = (hex, f) => { const r = (hex >> 16) & 255, g = (hex >> 8) & 255, b = hex & 255, m = v => Math.round(v + (205 - v) * f);
  return (m(r) << 16) | (m(g) << 8) | m(b); };
// buildings one cannot stand inside of (fields, pens, fires, roads and monuments one can stand on or by)
const walled = roles => !!roles && ["shelter", "store", "workshop", "gathering", "library", "school", "market", "lookout"].some(r => roles.includes(r))
  && !roles.includes("hearth");
export const darker = hex => { const r = (hex >> 16) & 255, g = (hex >> 8) & 255, b = hex & 255; return ((r * 0.72) << 16) | ((g * 0.72) << 8) | (b * 0.72); };

export class People {
  constructor(scene, land, store) {
    this.scene = scene; this.land = land; this.s = store;
    this.pos = new Map(); this.face = new Map(); this.looks = new Map(); this.dressed = new Map();
    this.batch = new Batch(scene);
    const P = Fig.parts(), H = Fig.hairs(), W = Fig.wear(), T = Fig.tools();
    const skin = toon({color: 0xffffff}), cloth = toon({color: 0xffffff});
    const dark = new THREE.MeshBasicMaterial({color: 0x2a1e18}), white = new THREE.MeshBasicMaterial({color: 0xffffff});
    const blush = new THREE.MeshBasicMaterial({color: 0xff8a8a, transparent: true, opacity: 0.45, depthWrite: false});
    const B = this.batch;
    B.define("body", P.body, cloth, {shadow: true});
    B.define("head", P.head, skin, {shadow: true});
    // far off: plainer shapes, casting no shadow (too small to see)
    const LO = Fig.parts(1);
    B.define("body:far", LO.body, cloth); B.define("head:far", LO.head, skin); B.define("hair:far", Fig.hairFar(), toon({color: 0xffffff}));
    B.define("arm", P.arm, cloth); B.define("hand", P.hand, skin);
    B.define("leg", P.leg, cloth); B.define("foot", P.foot, cloth);
    B.define("eye", P.eye, dark); B.define("shine", P.shine, white); B.define("blush", P.blush, blush);
    for (const [k, g] of Object.entries(H)) B.define("hair:" + k, g, toon({color: 0xffffff}), {shadow: true});
    for (const [k, g] of Object.entries(W)) B.define("wear:" + k, g, toon({color: 0xffffff, side: k === "cape" || k === "robe" ? THREE.DoubleSide : THREE.FrontSide}));
    for (const [k, g] of Object.entries(T)) B.define("tool:" + k, g, toon({color: Fig.TOOL_COLOR[k]}));
    // scratch, reused every frame
    this.m = {root: new THREE.Matrix4(), body: new THREE.Matrix4(), head: new THREE.Matrix4(), limb: new THREE.Matrix4(),
      part: new THREE.Matrix4(), id: new THREE.Matrix4(), tmp: new THREE.Matrix4(), q: new THREE.Quaternion(), e: new THREE.Euler(),
      pv: new THREE.Matrix4(), frustum: new THREE.Frustum(), sphere: new THREE.Sphere(new THREE.Vector3(), 0.7),
      v: new THREE.Vector3(), s: new THREE.Vector3()};
    this.spare = [];
    this.talkHour = null; this.talking = new Map();
    this.crowds = new Map();
  }

  // several on one tile stand around it, not inside one another (a child beside its parent, a ring at a
  // fire): an offset for each by their place among those there that hour
  crowd(hour) {
    if (!hour) return null;
    let c = this.crowds.get(hour.t);
    if (!c) {
      const at = new Map();
      for (const [id, q] of hour.people) { const k = q.y * this.land.w + q.x; (at.get(k) || at.set(k, []).get(k)).push(id); }
      c = new Map();
      for (const [k, ids] of at) {
        if (ids.length < 2) continue;
        ids.sort((a, b) => a - b);
        const r = Math.min(0.32, 0.16 + 0.03 * ids.length), turn = (k % 7) * 0.9;
        ids.forEach((id, i) => { const an = turn + 2 * Math.PI * i / ids.length; c.set(id, [Math.sin(an) * r, Math.cos(an) * r]); });
      }
      if (this.crowds.size > 8) this.crowds.clear();
      this.crowds.set(hour.t, c);
    }
    return c;
  }

  // a fire (a hearth) on or beside a tile, if any: where people sit in the evening
  fireBeside(tx, ty, byTile) {
    if (!byTile) return null;
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
      const b = byTile.get((ty + dy) * this.land.w + tx + dx);
      if (b && b.done && (this.s.cat.buildings[b.kind]?.roles || []).includes("hearth")) return b;
    }
    return null;
  }

  // where one stands on a tile: its middle, or on a walled building's tile, its doorstep (scene/buildings.js
  // turns each building by its id; the door faces its +z), so no one stands inside the walls
  spot(tx, ty, byTile) {
    const b = byTile?.get(ty * this.land.w + tx);
    if (b && b.done && walled(this.s.cat.buildings[b.kind]?.roles)) {
      const turn = (hashOf(b.id) % 4) * Math.PI / 2;
      return [tx + 0.5 + Math.sin(turn) * 0.46, ty + 0.5 + Math.cos(turn) * 0.46];
    }
    return [tx + 0.5, ty + 0.5];
  }

  // out = parent x translate(x, y, z) x rotate(yaw about y, then pitch about x, then roll about z) x scale
  mat(out, parent, x, y, z, pitch = 0, yaw = 0, roll = 0, sx = 1, sy = 1, sz = 1) {
    const {q, e, v, s, tmp} = this.m;
    e.set(pitch, yaw, roll, "YXZ"); q.setFromEuler(e);
    tmp.compose(v.set(x, y, z), q, s.set(sx, sy, sz));
    return out.multiplyMatrices(parent, tmp);
  }

  update(view, t, dt, cam, buildingsByTile) {
    const s = this.s, a = s.hour(t), b = s.nextHour(t);
    if (!a) return;
    const snap = s.snapshot(t), f = t - Math.floor(t), now = performance.now() / 1000, B = this.batch, M = this.m;
    const hr = Math.floor(t);
    if (hr !== this.talkHour) {           // who speaks this hour, and to whom
      this.talkHour = hr; this.talking.clear();
      for (const e of s.localEvents(hr, hr)) if (e.kind === "say" && e.who.length) this.talking.set(e.who[0], e.who[1] ?? null);
    }
    if (snap && snap.t !== this.dressDay) { this.dressDay = snap.t; this.dressed.clear(); }
    const night = s.cal.of(t).night, I = M.id.identity();
    // only those in view are drawn
    if (cam) { M.pv.multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse); M.frustum.setFromProjectionMatrix(M.pv); }
    for (const v of this.pos.values()) this.spare.push(v);
    this.pos.clear();
    B.begin();
    for (const [id, p] of a.people) {
      const person = s.person(id);
      if (!person) continue;
      const q = b?.people.get(id) || p;
      if (!this.looks.has(id)) this.looks.set(id, looksOf(person));
      const look = this.looks.get(id);
      // walking evenly through the hour (a step or two an hour; hour after hour, never stopping between them),
      // from doorstep to doorstep
      let [ax, az] = this.spot(p.x, p.y, buildingsByTile), [bx, bz] = this.spot(q.x, q.y, buildingsByTile);
      const oa = this.crowd(a)?.get(id), ob = b ? this.crowd(b)?.get(id) : oa;
      if (oa) { ax += oa[0]; az += oa[1]; }
      if (ob) { bx += ob[0]; bz += ob[1]; }
      const way = Math.hypot(bx - ax, bz - az), u = f;
      const x = ax + (bx - ax) * u, z = az + (bz - az) * u;
      const moving = way > 0.05, y = this.land.groundAt(x, z);
      this.pos.set(id, (this.spare.pop() || new THREE.Vector3()).set(x, y, z));
      const asleep = p.verb === "sleep" || (p.verb === "rest" && night);
      // asleep at home: indoors, out of sight
      const home = buildingsByTile?.get(p.y * this.land.w + p.x);
      if (asleep && home && home.done && (s.cat.buildings[home.kind]?.roles || []).includes("shelter")) continue;
      if (cam) { M.sphere.center.set(x, y + 0.4, z); if (!M.frustum.intersectsSphere(M.sphere) || cam.position.distanceTo(M.sphere.center) > cam.far) continue; }
      // facing: the way they walk, or whom they speak to, strike, teach, follow (turning smoothly)
      let yaw = this.face.get(id) ?? (look.seed % 6.28);
      const other = this.talking.get(id) ?? (typeof p.detail === "number" ? p.detail : null);
      const op = other != null ? a.people.get(other) : null;
      // idle or resting by a fire: sit facing it
      const idle = !moving && (p.verb === "rest" || p.verb === "wait" || !p.verb) && !asleep;
      const fire = idle ? this.fireBeside(p.x, p.y, buildingsByTile) : null;
      if (moving) yaw = Math.atan2(bx - ax, bz - az);
      else if (op && Math.abs(op.x - p.x) + Math.abs(op.y - p.y) <= 3 && (op.x !== p.x || op.y !== p.y)) yaw = Math.atan2(op.x - p.x, op.y - p.y);
      else if (fire) yaw = Math.atan2(fire.x + 0.5 - x, fire.y + 0.5 - z);
      else if (op && op.x === p.x && op.y === p.y && oa && this.crowd(a)?.get(other)) {
        const o2 = this.crowd(a).get(other); yaw = Math.atan2(o2[0] - oa[0], o2[1] - oa[1]);   // the same tile: face them
      }
      const cur = this.face.get(id) ?? yaw;
      let d = yaw - cur; d = Math.atan2(Math.sin(d), Math.cos(d));
      yaw = cur + d * Math.min(1, dt * 8);
      this.face.set(id, yaw);
      // size by age: children small with big heads; the old a little bent
      const age = s.age(id, t), grown = Math.min(1, 0.5 + age / 15 * 0.5), sc = grown * look.height;
      const headScale = 1 + (1 - grown) * 0.35, old = age > 50 ? Math.min(0.2, (age - 50) * 0.01) : 0;
      if (!this.dressed.has(id)) {
        const day = snap?.people.get(id), inv = day?.inv || {};
        // what is carried and not worn, by weight: a pack on the back from about a third of a full load
        let load = 0;
        for (const [k, n] of Object.entries(inv)) { const it = s.cat.items[k]; if (it && it.class !== "worn") load += (it.w ?? 1) * n; }
        this.dressed.set(id, {wear: dress(inv, s.cat), have: held(inv), load});
      }
      const {wear, have, load} = this.dressed.get(id);
      const laden = age >= 8 && load > 10 ? Math.min(1, (load - 10) / 25) : 0;
      const P = pose(fire && !p.verb ? "rest" : p.verb, moving, now, look.seed, this.talking.has(id), p.detail, laden);
      // detail by distance from the camera
      const far = cam ? cam.position.distanceTo(this.pos.get(id)) : 0;
      const lod = far < 18 ? 0 : far < 50 ? 1 : 2;
      // root: standing (or lying down, asleep under the sky)
      if (P.lie) this.mat(M.root, I, x, y + 0.07 * sc, z, -Math.PI / 2, yaw, 0, sc, sc, sc);
      else this.mat(M.root, I, x, y + P.lift * sc, z, 0, yaw, 0, sc * look.round, sc, sc * look.round);
      // body (pivot at the hips), head on it
      this.mat(M.body, M.root, 0, Fig.JOINT.hip, 0, P.lean + old, 0, P.roll, 1, P.squash, 1);
      const lo = lod > 0 ? ":far" : "";
      B.push("body" + lo, M.body, wear.shirt);
      this.mat(M.head, M.body, 0, Fig.JOINT.neck - Fig.JOINT.hip, 0, P.headPitch, P.headYaw, 0, headScale, headScale, headScale);
      B.push("head" + lo, M.head, look.skin);
      B.push(lod > 0 ? "hair:far" : "hair:" + look.style, M.head, age > 48 ? greyed(look.hair, Math.min(1, (age - 48) / 15)) : look.hair);
      if (wear.hat) B.push("wear:" + wear.hat, M.head, wear.hat === "furHat" ? CLOTH.fur : 0xe2c27a);
      if (lod === 2) continue;
      // arms (and what the right hand holds)
      const tool = lod === 0 ? toolFor(p.verb, p.detail, have) : null;
      for (const side of [-1, 1]) {
        const pitch = side < 0 ? P.armL : P.armR, spread = (side < 0 ? P.spreadL : P.spreadR) * side;
        this.mat(M.limb, M.body, side * Fig.JOINT.armX, Fig.JOINT.shoulder - Fig.JOINT.hip, 0, pitch, 0, spread);
        B.push("arm", M.limb, wear.cape ?? wear.shirt);
        if (lod === 0) {
          B.push("hand", M.limb, look.skin);
          if (side > 0 && tool) B.push("tool:" + tool, M.limb);
        }
      }
      // legs
      for (const side of [-1, 1]) {
        this.mat(M.limb, M.root, side * Fig.JOINT.legX, Fig.JOINT.hip, 0, side < 0 ? P.legL : P.legR);
        B.push("leg", M.limb, wear.robe ? CLOTH.robe : darker(wear.shirt));
        if (lod === 0) B.push("foot", M.limb, wear.shoes ?? look.skin);
      }
      if (lod === 0) {
        // the face: eyes that blink now and then, a shine in them, rosy cheeks
        const blink = Math.sin(now * 0.9 + look.seed * 3) > 0.985 ? 0.1 : 1;
        for (const side of [-1, 1]) {
          this.mat(M.part, M.head, side * 0.066, 0.158, 0.15, 0, 0, 0, 1, blink, 1);
          B.push("eye", M.part);
          if (blink > 0.5) { this.mat(M.part, M.head, side * 0.066 + 0.01, 0.176, 0.166); B.push("shine", M.part); }
          if (look.blush) { this.mat(M.part, M.head, side * 0.105, 0.115, 0.135, 0, side * 0.5); B.push("blush", M.part); }
        }
        if (wear.cape) { this.mat(M.part, M.body, 0, Fig.JOINT.shoulder - Fig.JOINT.hip, 0, moving ? 0.25 : 0.08); B.push("wear:cape", M.part, wear.cape); }
        if (wear.robe) B.push("wear:robe", M.body, CLOTH.robe);
        if (laden && !P.lie && !P.sit) { const k = 0.75 + laden * 0.6; this.mat(M.part, M.body, 0, Fig.JOINT.shoulder - Fig.JOINT.hip, 0, 0, 0, 0, k, k, k); B.push("wear:pack", M.part, 0xa88a5c); }
        if (wear.necklace) { this.mat(M.part, M.body, 0, Fig.JOINT.shoulder - Fig.JOINT.hip - 0.02, 0.02); B.push("wear:necklace", M.part, 0xe6b84a); }
      }
    }
    B.end();
  }
}
