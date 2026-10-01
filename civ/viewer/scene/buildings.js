// Buildings as they stood on the day: one instanced mesh per part of each kind (so a thousand buildings
// cost a few dozen draws); those going up stand in scaffolding; fields show their crop as it grows.
import * as THREE from "three";
import {parts, SCAFFOLD, COLORS} from "../art/buildings.js";
import {toon} from "../art/toon.js";
import {hash} from "../art/look.js";

export class Buildings {
  constructor(scene, land, store) {
    this.land = land; this.s = store;
    this.group = new THREE.Group(); this.group.name = "buildings";
    scene.add(this.group);
    this.models = new Map();     // kind -> parts
    this.mats = new Map();
    this.day = null;
    this.byTile = new Map();
    const crop = new THREE.ConeGeometry(0.05, 0.22, 4); crop.translate(0, 0.11, 0);
    this.cropGeo = crop;
  }

  mat(name) {
    if (!this.mats.has(name)) {
      const c = COLORS[name] ?? 0xcccccc;
      const ember = name === "ember" || name === "flame";
      this.mats.set(name, toon({color: c, snow: !ember, emissive: ember ? 0xff7a2a : 0x000000, glow: ember, flicker: name === "flame",
        side: ["thatch", "red", "slate"].includes(name) ? THREE.DoubleSide : THREE.FrontSide}));
    }
    return this.mats.get(name);
  }

  model(kind, done) {
    const key = done ? kind : "~scaffold";
    if (!this.models.has(key)) this.models.set(key, done ? parts(kind, this.s.cat.buildings[kind]?.roles ?? []) : SCAFFOLD());
    return this.models.get(key);
  }

  // the ground a building stands on: the lowest of its corners, so it never floats
  base(x, y) {
    const L = this.land;
    return Math.min(L.groundAt(x + 0.1, y + 0.1), L.groundAt(x + 0.9, y + 0.1), L.groundAt(x + 0.1, y + 0.9), L.groundAt(x + 0.9, y + 0.9));
  }

  update(snap, t) {
    if (!snap || snap.t === this.day) return;
    this.day = snap.t;
    for (const c of [...this.group.children]) { this.group.remove(c); c.dispose?.(); }
    this.byTile.clear();
    const groups = new Map();
    for (const b of snap.buildings) {
      if (b.kind === "road") continue;
      const key = (b.done ? "" : "~") + b.kind;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(b);
      this.byTile.set(b.y * this.land.w + b.x, b);
    }
    const o = new THREE.Object3D();
    for (const [key, list] of groups) {
      const ps = this.model(key.replace(/^~/, ""), !key.startsWith("~"));
      for (const [geo, color] of ps) {
        const m = new THREE.InstancedMesh(geo, this.mat(color), list.length);
        list.forEach((b, i) => {
          o.position.set(b.x + 0.5, this.base(b.x, b.y), b.y + 0.5);
          o.rotation.set(0, (hash(b.id) % 4) * Math.PI / 2, 0);
          o.scale.setScalar(1);
          o.updateMatrix();
          m.setMatrixAt(i, o.matrix);
        });
        m.castShadow = true; m.receiveShadow = true;
        m.userData.kind = key;
        this.group.add(m);
      }
    }
    // the crops in the fields: green shoots that grow and turn gold
    const fields = snap.buildings.filter(b => b.done && b.crop);
    if (fields.length) {
      const m = new THREE.InstancedMesh(this.cropGeo, this.mat("crop"), fields.length * 9), c = new THREE.Color();
      let i = 0;
      for (const b of fields) {
        const g = b.growth, f = g ? (g.ripe ? 1 : Math.max(0.1, Math.min(1, (t - g.sown) / Math.max(1, g.ripeAt - g.sown)))) : 0.5;
        const col = b.crop === "flax" ? c.setHex(0x6f9a5a).lerp(new THREE.Color(0x7f9ae0), f * 0.6) : c.setHex(0x6fae4a).lerp(new THREE.Color(0xe2bf55), f);
        for (let k = 0; k < 9; k++) {
          o.position.set(b.x + 0.2 + (k % 3) * 0.3, this.base(b.x, b.y) + 0.03, b.y + 0.2 + Math.floor(k / 3) * 0.3);
          o.rotation.set(0, k, 0);
          o.scale.set(1.4, 0.4 + f * 1.4, 1.4);
          o.updateMatrix();
          m.setMatrixAt(i, o.matrix);
          m.setColorAt(i, col);
          i++;
        }
      }
      m.castShadow = true;
      this.group.add(m);
    }
  }
}
