// Animals in the land: each wild herd as a few beasts grazing about its place (heads down now and then,
// trotting when the herd moves), the tamed in their pens, and wolves slinking in packs. Drawn as batches.
import * as THREE from "three";
import {toon} from "../art/toon.js";
import {rng} from "../art/look.js";
import * as A from "../art/animals.js";
import {Batch} from "./batch.js";

export class Animals {
  constructor(scene, land) {
    this.land = land;
    this.batch = new Batch(scene);
    const skin = toon({color: 0xffffff, snow: false});
    for (const k of Object.keys(A.KINDS)) this.batch.define("beast:" + k, A.body(k), skin, {shadow: true});
    this.batch.define("leg", A.leg(), skin);
    this.spots = new Map();          // a herd's or pen's beasts: their offsets and ways
    this.m = {root: new THREE.Matrix4(), leg: new THREE.Matrix4(), tmp: new THREE.Matrix4(), q: new THREE.Quaternion(), e: new THREE.Euler(),
      v: new THREE.Vector3(), s: new THREE.Vector3(), I: new THREE.Matrix4()};
  }

  mat(out, parent, x, y, z, pitch, yaw, sx, sy, sz) {
    const {q, e, v, s, tmp} = this.m;
    e.set(pitch, yaw, 0, "YXZ"); q.setFromEuler(e);
    tmp.compose(v.set(x, y, z), q, s.set(sx, sy, sz));
    return out.multiplyMatrices(parent, tmp);
  }

  // where each beast of a group stands about its middle, and which way it faces (fixed per group and beast)
  group(key, n, spread) {
    if (!this.spots.has(key) || this.spots.get(key).length < n) {
      const r = rng(key), out = [];
      for (let i = 0; i < n; i++) { const a = r() * Math.PI * 2, d = Math.sqrt(r()) * spread; out.push({dx: Math.cos(a) * d, dz: Math.sin(a) * d, yaw: r() * 6.28, seed: r() * 50}); }
      this.spots.set(key, out);
    }
    return this.spots.get(key);
  }

  beast(kind, x, z, yaw, moving, now, seed, near) {
    const K = A.KINDS[kind] ? kind : "deer", k = A.KINDS[K], M = this.m, sc = k.size / 0.5;
    const y = this.land.groundAt(x, z);
    const graze = !moving && Math.sin(now * 0.4 + seed) > 0.3;
    const bob = moving ? Math.abs(Math.sin(now * 10 + seed)) * 0.02 : 0;
    this.mat(M.root, M.I, x, y + bob, z, graze ? 0.25 : 0, yaw, 1, 1, 1);
    this.batch.push("beast:" + K, M.root, k.color);
    if (!near) return;
    const L = k.legLen * sc;
    for (const [lx, lz, ph] of [[-0.07, 0.13, 0], [0.07, 0.13, Math.PI], [-0.07, -0.13, Math.PI], [0.07, -0.13, 0]]) {
      const swing = moving ? Math.sin(now * 10 + seed + ph) * 0.5 : 0;
      this.mat(M.leg, M.root, lx * sc, L + 0.01, lz * sc, swing, 0, sc, L, sc);
      this.batch.push("leg", M.leg, k.color);
    }
  }

  update(store, t, snap, cam) {
    const a = store.hour(t), b = store.nextHour(t);
    if (!a) return;
    const f = t - Math.floor(t), e = f * f * (3 - 2 * f), now = performance.now() / 1000, B = this.batch;
    const near = (x, z) => !cam || Math.hypot(cam.position.x - x, cam.position.z - z) < 30;
    if (cam) { this.pv ??= new THREE.Matrix4(); this.fr ??= new THREE.Frustum(); this.sp ??= new THREE.Sphere(new THREE.Vector3(), 2);
      this.pv.multiplyMatrices(cam.projectionMatrix, cam.matrixWorldInverse); this.fr.setFromProjectionMatrix(this.pv); }
    this.seen = (x, z) => { if (!cam) return true; this.sp.center.set(x, this.land.groundAt(x, z) + 0.3, z);
      return this.fr.intersectsSphere(this.sp) && cam.position.distanceTo(this.sp.center) < cam.far; };
    B.begin();
    // wild herds
    const next = new Map((b?.herds || []).map(h => [h.id, h]));
    for (const h of a.herds) {
      if (h.n <= 0) continue;
      const q = next.get(h.id) || h, moving = (q.x !== h.x || q.y !== h.y) && f < 0.98;
      const cx = h.x + 0.5 + (q.x - h.x) * e, cz = h.y + 0.5 + (q.y - h.y) * e;
      const way = moving ? Math.atan2(q.x - h.x, q.y - h.y) : null;
      if (!this.seen(cx, cz)) continue;
      for (const s of this.group("herd" + h.id, Math.min(h.n, 7), 1.1)) {
        const x = cx + s.dx, z = cz + s.dz;
        if (this.land.isWater(Math.floor(x), Math.floor(z))) continue;
        this.beast(h.kind, x, z, way ?? s.yaw + Math.sin(now * 0.1 + s.seed) * 0.6, moving, now, s.seed, near(x, z));
      }
    }
    // wolves, in packs
    const nextPack = new Map((b?.packs || []).map(p => [p.id, p]));
    for (const p of a.packs) {
      const q = nextPack.get(p.id) || p, moving = (q.x !== p.x || q.y !== p.y) && f < 0.98;
      const cx = p.x + 0.5 + (q.x - p.x) * e, cz = p.y + 0.5 + (q.y - p.y) * e;
      if (!this.seen(cx, cz)) continue;
      for (const s of this.group("pack" + p.id, Math.min(p.n, 4), 0.7))
        this.beast("wolf", cx + s.dx, cz + s.dz, moving ? Math.atan2(q.x - p.x, q.y - p.y) : s.yaw, moving, now, s.seed, near(cx, cz));
    }
    // the tamed, in their pens: wandering slowly about
    for (const bld of snap?.buildings || []) {
      if (!bld.done || !Object.keys(bld.animals).length || !this.seen(bld.x + 0.5, bld.y + 0.5)) continue;
      let i = 0;
      for (const [kind, n] of Object.entries(bld.animals)) {
        for (const s of this.group(`pen${bld.id}:${kind}`, Math.min(n, 4), 0.3)) {
          const w = now * 0.15 + s.seed, x = bld.x + 0.5 + s.dx + Math.sin(w) * 0.08, z = bld.y + 0.5 + s.dz + Math.cos(w) * 0.08;
          this.beast(kind, x, z, w + Math.PI / 2, false, now, s.seed + i, near(x, z));
        }
        i++;
      }
    }
    B.end();
  }
}
