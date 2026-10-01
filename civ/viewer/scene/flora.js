// Plants and stones over the land, placed once from the terrain (seeded, so always the same), drawn as
// instances. Those on a tile that comes to hold a building step aside (hidden) while it stands.
import * as THREE from "three";
import * as F from "../art/flora.js";
import {toon} from "../art/toon.js";
import {rng} from "../art/look.js";

const LEAF = {round: 0x5c9a3c, pine: 0x3f7a45, bush: 0x6aa548, tuft: 0x86b84f, reeds: 0x9aa860};

export class Flora {
  constructor(land, quality = "high") {
    this.land = land;
    this.group = new THREE.Group();
    this.group.name = "flora";
    const r = rng("flora"), lots = quality === "high" ? 1 : 0.5;
    const spots = {round: [], pine: [], bush: [], rock: [], tuft: [], reeds: []};
    const put = (kind, x, z, s, tile) => spots[kind].push({x, z, s, rot: r() * Math.PI * 2, tint: r(), tile});
    for (let ty = 0; ty < land.h; ty++) for (let tx = 0; tx < land.w; tx++) {
      const ch = land.at(tx, ty), tile = ty * land.w + tx;
      const jx = () => tx + 0.15 + r() * 0.7, jz = () => ty + 0.15 + r() * 0.7;
      if (ch === "T") {
        const n = 2 + (r() < 0.4 ? 1 : 0);
        const pineish = land.at(tx + 1, ty) === "h" || land.at(tx - 1, ty) === "h" || land.at(tx, ty + 1) === "h" || land.at(tx, ty - 1) === "h";
        for (let i = 0; i < n; i++) put(r() < (pineish ? 0.65 : 0.25) ? "pine" : "round", jx(), jz(), 0.75 + r() * 0.6, tile);
        if (r() < 0.5) put("bush", jx(), jz(), 0.8 + r() * 0.5, tile);
      } else if (ch === "." || ch === ",") {
        if (r() < 0.035) put("round", jx(), jz(), 0.8 + r() * 0.5, tile);
        if (r() < 0.08) put("bush", jx(), jz(), 0.7 + r() * 0.5, tile);
        for (let i = 0; i < Math.round(3 * lots); i++) put("tuft", jx(), jz(), 0.7 + r() * 0.7, tile);
      } else if (ch === "h") {
        if (r() < 0.3) put("rock", jx(), jz(), 0.8 + r() * 1.2, tile);
        if (r() < 0.12) put("pine", jx(), jz(), 0.7 + r() * 0.5, tile);
        for (let i = 0; i < Math.round(2 * lots); i++) put("tuft", jx(), jz(), 0.6 + r() * 0.5, tile);
      } else if (ch === "^") {
        if (r() < 0.55) put("rock", jx(), jz(), 1 + r() * 2, tile);
      } else if (ch === "m") {
        for (let i = 0; i < 3; i++) put("reeds", jx(), jz(), 0.8 + r() * 0.6, tile);
      } else if (ch === "s") {
        if (r() < 0.06) put("rock", jx(), jz(), 0.5 + r() * 0.6, tile);
      }
    }
    this.sets = [];
    const add = (kind, geo, mat, list, shadow) => {
      if (!list.length) return;
      const g = geo.clone();
      g.setAttribute("aTint", new THREE.InstancedBufferAttribute(new Float32Array(list.map(s => s.tint)), 1));
      const m = new THREE.InstancedMesh(g, mat, list.length);
      const o = new THREE.Object3D();
      list.forEach((s, i) => {
        o.position.set(s.x, land.groundAt(s.x, s.z) - 0.02, s.z);
        o.rotation.set(0, s.rot, 0);
        o.scale.setScalar(s.s);
        o.updateMatrix();
        m.setMatrixAt(i, o.matrix);
      });
      m.castShadow = shadow; m.receiveShadow = true;
      m.userData = {kind, list, hidden: new Set()};
      this.group.add(m);
      this.sets.push(m);
    };
    const wood = toon({color: 0x7a5534, wind: 0.02});
    const round = F.roundTree(), pine = F.pineTree();
    add("round", round.wood, wood, spots.round, true);
    add("round", round.leaves, toon({color: LEAF.round, wind: 0.05, foliage: true, snow: true}), spots.round, true);
    add("pine", pine.wood, wood, spots.pine, true);
    add("pine", pine.leaves, toon({color: LEAF.pine, wind: 0.035, snow: true}), spots.pine, true);
    add("bush", F.bush().leaves, toon({color: LEAF.bush, wind: 0.08, foliage: true, snow: true}), spots.bush, true);
    add("rock", F.rock(1).stone, toon({color: 0x9c968c, snow: true}), spots.rock, true);
    add("tuft", F.tuft().leaves, toon({color: LEAF.tuft, wind: 0.35, foliage: true}), spots.tuft, false);
    add("reeds", F.reeds().leaves, toon({color: LEAF.reeds, wind: 0.25}), spots.reeds, false);
  }

  // hide what grows on these tiles (index ty * w + tx); show again what is no longer covered
  clear(tiles) {
    const zero = new THREE.Matrix4().makeScale(0, 0, 0), o = new THREE.Object3D();
    for (const m of this.sets) {
      const {list, hidden} = m.userData;
      let changed = false;
      list.forEach((s, i) => {
        const hide = tiles.has(s.tile);
        if (hide === hidden.has(i)) return;
        changed = true;
        if (hide) { hidden.add(i); m.setMatrixAt(i, zero); }
        else {
          hidden.delete(i);
          o.position.set(s.x, this.land.groundAt(s.x, s.z) - 0.02, s.z); o.rotation.set(0, s.rot, 0); o.scale.setScalar(s.s); o.updateMatrix();
          m.setMatrixAt(i, o.matrix);
        }
      });
      if (changed) m.instanceMatrix.needsUpdate = true;
    }
  }
}
