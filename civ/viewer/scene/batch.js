// A batch of instanced parts: each frame, things push (part, matrix, colour) and the batch draws every part
// in one call. Parts can be added any time (new kinds of hats, tools...), counts grow as needed.
import * as THREE from "three";

export class Batch {
  constructor(scene) {
    this.scene = scene;
    this.parts = new Map();          // name -> {geo, mat, mesh, n, cap, shadow}
    this.c = new THREE.Color();
  }

  define(name, geo, mat, {shadow = false} = {}) {
    if (!this.parts.has(name)) this.parts.set(name, {geo, mat, mesh: null, n: 0, cap: 0, shadow});
  }

  begin() { for (const p of this.parts.values()) p.n = 0; }

  push(name, matrix, color = null) {
    const p = this.parts.get(name);
    if (!p) return;
    if (p.n >= p.cap) this.grow(p, Math.max(32, Math.ceil(p.cap * 1.5)));
    p.mesh.setMatrixAt(p.n, matrix);
    if (color != null) p.mesh.setColorAt(p.n, this.c.setHex(color));
    p.n++;
  }

  grow(p, cap) {
    const old = p.mesh, m = new THREE.InstancedMesh(p.geo, p.mat, cap);
    m.castShadow = p.shadow; m.receiveShadow = true; m.frustumCulled = false;
    if (old) {
      m.instanceMatrix.array.set(old.instanceMatrix.array.subarray(0, p.n * 16));
      if (old.instanceColor) { m.setColorAt(0, this.c.set(0xffffff)); m.instanceColor.array.set(old.instanceColor.array.subarray(0, p.n * 3)); }
      this.scene.remove(old); old.dispose();
    }
    p.mesh = m; p.cap = cap;
    this.scene.add(m);
  }

  end() {
    for (const p of this.parts.values()) {
      if (!p.mesh) continue;
      p.mesh.count = p.n;
      p.mesh.visible = p.n > 0;
      p.mesh.instanceMatrix.needsUpdate = true;
      if (p.mesh.instanceColor) p.mesh.instanceColor.needsUpdate = true;
    }
  }
}
