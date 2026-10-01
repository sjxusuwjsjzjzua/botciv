// What the land holds that changes day by day: deposits (berry bushes, wild grain, flax, herbs, clay banks,
// flint, salt, ores, hives...), worn roads, and things left lying on the ground. Rebuilt when the day changes.
import * as THREE from "three";
import * as F from "../art/flora.js";
import {toon} from "../art/toon.js";
import {rng} from "../art/look.js";
import {byBlock, instanced, blockDist} from "./blocks.js";

const blob = (r, x, y, z) => { const g = new THREE.IcosahedronGeometry(r, 0); g.translate(x, y, z); return g; };

// each deposit kind: a body and, optionally, little accents (berries, flowers, glints); unknown kinds: a stone
function looks() {
  const tuft = F.tuft().leaves, bush = F.bush().leaves, rock = F.rock(3).stone;
  const mound = new THREE.SphereGeometry(0.28, 10, 6, 0, Math.PI * 2, 0, Math.PI / 2); mound.scale(1, 0.4, 1);
  const crystal = new THREE.OctahedronGeometry(0.08, 0); crystal.scale(0.7, 1.4, 0.7); crystal.translate(0, 0.08, 0);
  const hive = new THREE.CylinderGeometry(0.07, 0.11, 0.18, 8); hive.translate(0, 0.32, 0);
  const stump = new THREE.CylinderGeometry(0.1, 0.12, 0.22, 7); stump.translate(0, 0.11, 0);
  const dots = (n, r, spread, y) => { const gs = []; for (let i = 0; i < n; i++) gs.push(blob(r, Math.sin(i * 2.4) * spread, y + (i % 3) * 0.03, Math.cos(i * 2.4) * spread)); return gs; };
  return {
    berries: {body: [bush, 0x4f8f3a, true], accent: [dots(7, 0.03, 0.13, 0.14), 0xc0304a]},
    wild_grain: {body: [tuft, 0xd9b24c, true]},
    flax: {body: [tuft, 0x7fa860, true], accent: [dots(4, 0.025, 0.06, 0.22), 0x6f8fe0]},
    herbs: {body: [tuft, 0x5fb85a, true], accent: [dots(4, 0.022, 0.07, 0.18), 0xf4f0ff]},
    nuts: {body: [bush, 0x6f8a3c, true], accent: [dots(5, 0.03, 0.12, 0.12), 0x8a5a2b]},
    clay: {body: [mound, 0xb86b3c]},
    flint: {body: [rock, 0xd8d6d0]},
    salt: {body: [crystal, 0xf6f6f6]},
    limestone: {body: [rock, 0xe0d8c4]},
    copper_ore: {body: [rock, 0x7f8f7a], accent: [dots(3, 0.035, 0.08, 0.12), 0x3fae7a]},
    tin_ore: {body: [rock, 0x55565a], accent: [dots(3, 0.03, 0.08, 0.12), 0x22252a]},
    iron_ore: {body: [rock, 0x8a6a5a], accent: [dots(3, 0.035, 0.08, 0.12), 0xa3452e]},
    bog_iron: {body: [mound, 0x7a5a3a], accent: [dots(3, 0.035, 0.1, 0.06), 0xa3452e]},
    gold: {body: [rock, 0x9c968c], accent: [dots(3, 0.03, 0.08, 0.13), 0xf0c230]},
    honey: {body: [stump, 0x7a5534], accent: [[hive], 0xe8b52a]},
  };
}

export class Props {
  constructor(scene, land) {
    this.scene = scene; this.land = land;
    this.group = new THREE.Group(); this.group.name = "props";
    scene.add(this.group);
    this.looks = looks();
    this.mats = new Map();
    this.day = null;
  }

  mat(color, wind) {
    const k = color + ":" + wind;
    if (!this.mats.has(k)) this.mats.set(k, toon({color, wind: wind ? 0.2 : 0, snow: true}));
    return this.mats.get(k);
  }

  update(snap) {
    if (!snap || snap.t === this.day) return;
    this.day = snap.t;
    for (const c of [...this.group.children]) { this.group.remove(c); c.dispose?.(); }
    const by = new Map(), r = rng("props");
    for (const d of snap.deposits) {
      if (d.left <= 0) continue;
      const look = this.looks[d.kind] || {body: [F.rock(5).stone, 0x9c968c]};
      if (!by.has(d.kind)) by.set(d.kind, {look, spots: []});
      const n = d.left > 20 ? 3 : d.left > 6 ? 2 : 1;
      for (let i = 0; i < n; i++) {
        const x = d.x + 0.2 + ((i * 0.37 + (d.x * 7 + d.y * 13) % 10 / 10) % 1) * 0.6, z = d.y + 0.2 + ((i * 0.61 + (d.x * 11 + d.y * 5) % 10 / 10) % 1) * 0.6;
        by.get(d.kind).spots.push([x, z, 0.8 + ((d.x + d.y + i) % 5) * 0.12, (d.x * 3 + d.y + i) % 6]);
      }
    }
    for (const {look, spots} of by.values()) {
      this.instances(look.body[0], this.mat(look.body[1], look.body[2]), spots, true);
      if (look.accent) for (const g of look.accent[0]) this.instances(g, this.mat(look.accent[1], false), spots, false, false, 28);
    }
    // roads: flat stones along the way
    const roads = snap.roads.map(k => k.split(",").map(Number));
    if (roads.length) {
      this.stone ??= new THREE.CylinderGeometry(0.42, 0.45, 0.04, 8);
      this.instances(this.stone, this.mat(0xc8b48a, false), roads.map(([x, y]) => [x + 0.5, y + 0.5, 1, 0]), false, true);
    }
    // things left on the ground: a little bundle
    const piles = Object.keys(snap.piles || {}).map(k => k.split(",").map(Number));
    if (piles.length) {
      if (!this.sack) { this.sack = new THREE.SphereGeometry(0.12, 8, 6); this.sack.scale(1, 0.75, 1); this.sack.translate(0, 0.08, 0); }
      this.instances(this.sack, this.mat(0xc9a66b, false), piles.map(([x, y]) => [x + 0.5 + r() * 0.2, y + 0.5 + r() * 0.2, 1, 0]), true);
    }
  }

  // spots: [x, z, scale, turn]; in blocks, so what is out of view or far is skipped (lod below)
  instances(geo, mat, spots, shadow, flat = false, show = 70) {
    const place = (s, o) => { o.position.set(s[0], this.land.groundAt(s[0], s[1]) + (flat ? 0.01 : -0.01), s[1]); o.rotation.set(0, s[3] * 1.05, 0); o.scale.setScalar(s[2]); };
    let last = null;
    for (const b of byBlock(spots.map(s => Object.assign(s, {x: s[0], z: s[1]})))) {
      const m = instanced(geo, mat, b.items, place, {shadow});
      m.userData = {cx: b.cx, cz: b.cz, show};
      this.group.add(m);
      last = m;
    }
    return last;
  }

  // far off, the little accents (berries, flowers, glints) and then the rest are not worth drawing
  lod(target, dist) {
    const reach = Math.max(1, dist / 26);
    for (const m of this.group.children) m.visible = blockDist(m.userData, target) < m.userData.show * reach;
  }
}
