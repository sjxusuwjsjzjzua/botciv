// Plants and stones, generated: each kind a pair of geometries (wood and leaves, or one stone), built once.
import * as THREE from "three";
import {mergeGeometries, mergeVertices} from "three/addons/BufferGeometryUtils.min.js";

const blob = (r, x, y, z, detail = 1) => { const g = new THREE.IcosahedronGeometry(r, detail); g.translate(x, y, z); return g; };
// merged into one geometry; smooth: shared corners welded so light rolls softly over the shape
const merge = (gs, smooth = false) => {
  let g = mergeGeometries(gs.map(x => { const y = x.index ? x.toNonIndexed() : x; y.deleteAttribute("uv"); return y; }));
  if (smooth) { g.deleteAttribute("normal"); g = mergeVertices(g, 1e-3); }
  g.computeVertexNormals();
  return g;
};

export function roundTree() {
  const trunk = new THREE.CylinderGeometry(0.05, 0.08, 0.55, 6); trunk.translate(0, 0.27, 0);
  const leaves = merge([blob(0.32, 0, 0.72, 0, 0), blob(0.24, 0.17, 0.6, 0.07, 0), blob(0.22, -0.15, 0.62, -0.08, 0), blob(0.2, 0.02, 0.92, 0.04, 0)], true);
  return {wood: trunk, leaves};
}

export function pineTree() {
  const trunk = new THREE.CylinderGeometry(0.04, 0.07, 0.4, 6); trunk.translate(0, 0.2, 0);
  const cones = [];
  [[0.34, 0.45, 0.42], [0.27, 0.4, 0.68], [0.18, 0.34, 0.92]].forEach(([r, h, y]) => { const c = new THREE.ConeGeometry(r, h, 7); c.translate(0, y, 0); cones.push(c); });
  return {wood: trunk, leaves: merge(cones)};
}

export function bush() {
  return {leaves: merge([blob(0.16, 0, 0.12, 0, 0), blob(0.12, 0.12, 0.09, 0.04, 0), blob(0.11, -0.1, 0.08, -0.05, 0)], true)};
}

export function rock(seed = 0) {
  const g = new THREE.DodecahedronGeometry(0.18, 0);
  const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const s = 0.8 + 0.4 * Math.abs(Math.sin(i * 12.9898 + seed * 78.233));
    p.setXYZ(i, p.getX(i) * s, p.getY(i) * s * 0.7, p.getZ(i) * s);
  }
  g.translate(0, 0.06, 0);
  g.computeVertexNormals();
  return {stone: g};
}

export function tuft() {
  const blades = [];
  for (let i = 0; i < 5; i++) {
    const b = new THREE.ConeGeometry(0.025, 0.2 + (i % 3) * 0.05, 3);
    b.translate(0, 0.1, 0);
    b.rotateZ((i - 2) * 0.22); b.rotateY(i * 1.3);
    b.translate((i - 2) * 0.03, 0, (i % 2) * 0.03);
    blades.push(b);
  }
  return {leaves: merge(blades)};
}

export function reeds() {
  const parts = [];
  for (let i = 0; i < 4; i++) {
    const s = new THREE.CylinderGeometry(0.012, 0.015, 0.45, 4); s.translate(0, 0.22, 0);
    const top = new THREE.CylinderGeometry(0.025, 0.025, 0.08, 5); top.translate(0, 0.42, 0);
    const g = merge([s, top]); g.rotateZ((i - 1.5) * 0.08); g.translate((i - 1.5) * 0.05, 0, ((i * 7) % 3 - 1) * 0.04);
    parts.push(g);
  }
  return {leaves: merge(parts)};
}
