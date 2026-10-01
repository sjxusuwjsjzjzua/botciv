// Many small things over the land, drawn as instances in square blocks so that whatever is out of view is
// skipped, and each block can choose its detail by how far it is from where the camera looks.
import * as THREE from "three";

export const BLOCK = 16;

// items: [{x, z, ...}] grouped by block: Map "bx,bz" -> {cx, cz, items}
export function byBlock(items, size = BLOCK) {
  const out = new Map();
  for (const it of items) {
    const bx = Math.floor(it.x / size), bz = Math.floor(it.z / size), k = bx + "," + bz;
    if (!out.has(k)) out.set(k, {cx: (bx + 0.5) * size, cz: (bz + 0.5) * size, items: []});
    out.get(k).items.push(it);
  }
  return out.values();
}

// one instanced mesh of a block's items; place(item, object3d) sets its position, rotation and scale
const tmp = new THREE.Object3D();
export function instanced(geo, mat, items, place, {shadow = false, tint = null} = {}) {
  const g = tint ? geo.clone() : geo;
  if (tint) g.setAttribute("aTint", new THREE.InstancedBufferAttribute(new Float32Array(items.map(tint)), 1));
  const m = new THREE.InstancedMesh(g, mat, items.length);
  items.forEach((it, i) => { place(it, tmp); tmp.updateMatrix(); m.setMatrixAt(i, tmp.matrix); });
  m.computeBoundingSphere();
  m.castShadow = shadow; m.receiveShadow = true;
  return m;
}

// how far a block's middle is from the point the camera looks at (on the ground plane)
export const blockDist = (b, target) => Math.hypot(b.cx - target.x, b.cz - target.z);
