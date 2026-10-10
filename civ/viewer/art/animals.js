// Animals, generated: one body (torso, head, ears, tail, horns...) per kind, and legs that move. Wild herds,
// tamed beasts and wolves share the kit; kinds not listed take a plain beast's look.
import * as THREE from "three";
import {mergeGeometries, mergeVertices} from "three/addons/BufferGeometryUtils.min.js";

const smooth = gs => { let g = mergeGeometries(gs.map(x => { const y = x.index ? x.toNonIndexed() : x; y.deleteAttribute("uv"); return y; }));
  g.deleteAttribute("normal"); g = mergeVertices(g, 1e-4); g.computeVertexNormals(); return g; };
const ball = (r, x, y, z, sx = 1, sy = 1, sz = 1, n = 10) => { const g = new THREE.SphereGeometry(r, n, Math.max(6, n - 3)); g.scale(sx, sy, sz); g.translate(x, y, z); return g; };
const horn = (x, y, z, len, tilt, curl = 0) => { const g = new THREE.ConeGeometry(0.018, len, 6); g.translate(0, len / 2, 0); g.rotateZ(tilt); g.rotateX(curl); g.translate(x, y, z); return g; };

// the kinds: size (tiles), body proportions, colour, extras
export const KINDS = {
  deer: {size: 0.5, legLen: 0.2, color: 0xb98a58, belly: 0xe8d2b0, neck: 0.12, extras: "antlers"},
  boar: {size: 0.42, legLen: 0.1, color: 0x7a5e4a, belly: 0x6f5848, neck: 0.02, extras: "tusks"},
  aurochs: {size: 0.62, legLen: 0.16, color: 0x6a4c3a, belly: 0x5a4434, neck: 0.04, extras: "horns"},
  wild_goat: {size: 0.4, legLen: 0.15, color: 0x9a8a78, belly: 0xd8ccb8, neck: 0.07, extras: "goathorns"},
  wild_sheep: {size: 0.42, legLen: 0.12, color: 0xd6c8ae, belly: 0xf0e6d4, neck: 0.04, extras: "fluff"},
  wild_horse: {size: 0.6, legLen: 0.24, color: 0x8a5a36, belly: 0xb08058, neck: 0.16, extras: "mane"},
  wild_ass: {size: 0.5, legLen: 0.2, color: 0x9a8a76, belly: 0xd8d0c4, neck: 0.12, extras: "mane"},
  goat: {size: 0.38, legLen: 0.14, color: 0xeee6da, belly: 0xffffff, neck: 0.07, extras: "goathorns"},
  sheep: {size: 0.4, legLen: 0.11, color: 0xf4efe4, belly: 0xffffff, neck: 0.04, extras: "fluff"},
  cattle: {size: 0.6, legLen: 0.16, color: 0x8a5a3a, belly: 0xefe6d8, neck: 0.04, extras: "horns"},
  pig: {size: 0.4, legLen: 0.08, color: 0xf0b0a8, belly: 0xf6c8c0, neck: 0.0, extras: "snout"},
  horse: {size: 0.6, legLen: 0.24, color: 0x6a4a32, belly: 0x8a6a4a, neck: 0.16, extras: "mane"},
  donkey: {size: 0.5, legLen: 0.2, color: 0x7e7468, belly: 0xc8c0b4, neck: 0.12, extras: "mane"},
  wolf: {size: 0.42, legLen: 0.16, color: 0x7a7c84, belly: 0xc8c8cc, neck: 0.06, extras: "wolf"},
};

// a body: length along +z (the head forward), standing on legs of the kind's length; legs drawn apart
export function body(kind) {
  const k = KINDS[kind] || KINDS.deer, L = k.legLen, fluff = k.extras === "fluff";
  const parts = [ball(0.16, 0, L + 0.13, 0, fluff ? 1.15 : 0.9, fluff ? 1.05 : 0.85, 1.45, 12)];
  const hx = 0, hy = L + 0.2 + k.neck, hz = 0.24;
  if (k.neck > 0.03) { const n = new THREE.CylinderGeometry(0.05, 0.07, k.neck + 0.08, 8); n.rotateX(0.5); n.translate(0, L + 0.17 + k.neck / 2, 0.18); parts.push(n); }
  parts.push(ball(0.085, hx, hy, hz, 0.9, 0.9, 1.2, 10));
  parts.push(ball(0.04, -0.06, hy + 0.06, hz - 0.03, 0.6, 1.4, 0.4, 6), ball(0.04, 0.06, hy + 0.06, hz - 0.03, 0.6, 1.4, 0.4, 6));   // ears
  parts.push(ball(0.035, 0, L + 0.16, -0.23, 0.7, 0.7, 1.4, 6));                                                                        // tail
  if (k.extras === "antlers") parts.push(horn(-0.04, hy + 0.06, hz - 0.03, 0.14, 0.4), horn(0.04, hy + 0.06, hz - 0.03, 0.14, -0.4));
  if (k.extras === "horns") parts.push(horn(-0.07, hy + 0.04, hz, 0.12, 1.1, 0.3), horn(0.07, hy + 0.04, hz, 0.12, -1.1, 0.3));
  if (k.extras === "goathorns") parts.push(horn(-0.03, hy + 0.06, hz - 0.04, 0.1, 0.2, -0.7), horn(0.03, hy + 0.06, hz - 0.04, 0.1, -0.2, -0.7));
  if (k.extras === "tusks") parts.push(horn(-0.04, hy - 0.04, hz + 0.08, 0.05, 0.6, 0.9), horn(0.04, hy - 0.04, hz + 0.08, 0.05, -0.6, 0.9));
  if (k.extras === "snout" || k.extras === "tusks") parts.push(ball(0.04, 0, hy - 0.01, hz + 0.1, 1, 0.8, 0.6, 8));
  if (k.extras === "mane") parts.push(ball(0.04, 0, hy - 0.02, hz - 0.1, 0.6, 1.6, 1.6, 8));
  if (k.extras === "wolf") parts.push(ball(0.035, 0, hy - 0.02, hz + 0.1, 0.9, 0.8, 1.4, 8));
  const g = smooth(parts);
  g.scale(k.size / 0.5, k.size / 0.5, k.size / 0.5);
  return g;
}

// a leg (pivot at the hip, hanging down), shared by every kind (scaled to its length)
export function leg() {
  const g = new THREE.CylinderGeometry(0.022, 0.018, 1, 6);
  g.translate(0, -0.5, 0);
  return g;
}
