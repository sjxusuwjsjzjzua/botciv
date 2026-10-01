// Plants and stones over the land, placed once from the terrain (seeded: always the same), drawn as
// instances in blocks (scene/blocks.js). Each block picks its detail by distance from where the camera
// looks: full shapes near, simple shapes further, the smallest things only close by. What grows on a
// tile that comes to hold a building or road steps aside while it stands.
import * as THREE from "three";
import * as F from "../art/flora.js";
import {toon} from "../art/toon.js";
import {rng} from "../art/look.js";
import {byBlock, instanced, blockDist} from "./blocks.js";

const LEAF = {round: 0x5c9a3c, pine: 0x3f7a45, bush: 0x6aa548, tuft: 0x86b84f, reeds: 0x9aa860};

export class Flora {
  constructor(land, quality = "high") {
    this.land = land;
    this.group = new THREE.Group();
    this.group.name = "flora";
    const r = rng("flora"), lots = quality === "high" ? 1 : 0.6;
    this.near = quality === "high" ? 1 : 0.75;              // phones: detail switches sooner
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
        for (let i = 0; i < 3; i++) if (r() < lots) put("tuft", jx(), jz(), 0.7 + r() * 0.7, tile);
      } else if (ch === "h") {
        if (r() < 0.3) put("rock", jx(), jz(), 0.8 + r() * 1.2, tile);
        if (r() < 0.12) put("pine", jx(), jz(), 0.7 + r() * 0.5, tile);
        for (let i = 0; i < 2; i++) if (r() < lots) put("tuft", jx(), jz(), 0.6 + r() * 0.5, tile);
      } else if (ch === "^") {
        if (r() < 0.55) put("rock", jx(), jz(), 1 + r() * 2, tile);
      } else if (ch === "m") {
        for (let i = 0; i < 3; i++) put("reeds", jx(), jz(), 0.8 + r() * 0.6, tile);
      } else if (ch === "s") {
        if (r() < 0.06) put("rock", jx(), jz(), 0.5 + r() * 0.6, tile);
      }
    }
    // the kinds: near shape, far shape (or none: not drawn far off), how far each shows
    const wood = toon({color: 0x7a5534, wind: 0.02});
    const roundLeaf = toon({color: LEAF.round, wind: 0.05, foliage: true, snow: true});
    const pineLeaf = toon({color: LEAF.pine, wind: 0.035, snow: true});
    const round = F.roundTree(), pine = F.pineTree();
    const farRound = new THREE.IcosahedronGeometry(0.4, 0); farRound.translate(0, 0.72, 0);
    const farPine = new THREE.ConeGeometry(0.33, 0.95, 6); farPine.translate(0, 0.62, 0);
    const kinds = [
      {kind: "round", part: "wood", geo: round.wood, mat: wood, shadow: true, show: 34},
      {kind: "round", part: "leaves", geo: round.leaves, far: farRound, mat: roundLeaf, shadow: true, detail: 30},
      {kind: "pine", part: "wood", geo: pine.wood, mat: wood, shadow: true, show: 34},
      {kind: "pine", part: "leaves", geo: pine.leaves, far: farPine, mat: pineLeaf, shadow: true, detail: 30},
      {kind: "bush", geo: F.bush().leaves, mat: toon({color: LEAF.bush, wind: 0.08, foliage: true, snow: true}), shadow: true, show: 60},
      {kind: "rock", geo: F.rock(1).stone, mat: toon({color: 0x9c968c, snow: true}), shadow: true, show: 90},
      {kind: "tuft", geo: F.tuft().leaves, mat: toon({color: LEAF.tuft, wind: 0.35, foliage: true}), show: 22},
      {kind: "reeds", geo: F.reeds().leaves, mat: toon({color: LEAF.reeds, wind: 0.25}), show: 26},
    ];
    this.blocks = [];
    const place = (s, o) => { o.position.set(s.x, land.groundAt(s.x, s.z) - 0.02, s.z); o.rotation.set(0, s.rot, 0); o.scale.setScalar(s.s); };
    for (const k of kinds) for (const b of byBlock(spots[k.kind])) {
      const tint = s => s.tint;
      const near = instanced(k.geo, k.mat, b.items, place, {shadow: k.shadow, tint});
      const far = k.far ? instanced(k.far, k.mat, b.items, place, {shadow: k.shadow, tint}) : null;
      this.group.add(near);
      if (far) this.group.add(far);
      this.blocks.push({...k, cx: b.cx, cz: b.cz, items: b.items, near, far, hidden: new Set()});
    }
    this.place = place;
  }

  // each block: its detail by how far it is from where the camera looks
  lod(target, dist) {
    const reach = Math.max(1, dist / 26) * this.near;
    for (const b of this.blocks) {
      const d = blockDist(b, target);
      if (b.far) {
        const close = d < b.detail * reach;
        b.near.visible = close; b.far.visible = !close;
      } else b.near.visible = d < b.show * reach;
    }
  }

  // hide what grows on these tiles (index ty * w + tx); show again what is no longer covered
  clear(tiles) {
    const zero = new THREE.Matrix4().makeScale(0, 0, 0), o = new THREE.Object3D();
    for (const b of this.blocks) {
      let changed = false;
      b.items.forEach((s, i) => {
        const hide = tiles.has(s.tile);
        if (hide === b.hidden.has(i)) return;
        changed = true;
        if (hide) b.hidden.add(i); else b.hidden.delete(i);
        if (!hide) { this.place(s, o); o.updateMatrix(); }
        for (const m of [b.near, b.far]) if (m) m.setMatrixAt(i, hide ? zero : o.matrix);
      });
      if (changed) for (const m of [b.near, b.far]) if (m) { m.instanceMatrix.needsUpdate = true; m.computeBoundingSphere(); }
    }
  }
}
