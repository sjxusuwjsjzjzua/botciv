// The camera: one continuous view from kilometres up to a person's shoulder. Free orbit (drag to pan, right-drag or
// two fingers to turn and tilt, wheel or pinch to zoom, toward the pointer), the fly-down tour (one smooth path
// through key views, Catmull-Rom in position, log-distance, tilt and turn, eased at its ends) and the walk (following
// one person at ground level).
import * as THREE from "three";

export class Rig {
  constructor(canvas, land) {
    this.cam = new THREE.PerspectiveCamera(35, 1, 0.3, 30000);
    this.land = land;
    this.target = new THREE.Vector3(1300, 12, 1600);
    this.dist = 170; this.pitch = 0.785; this.yaw = 0;
    this.input(canvas);
  }

  set({x, z, dist, pitch, yaw}) {
    if (x != null) { this.target.x = x; this.target.z = z; }
    if (dist != null) this.dist = dist;
    if (pitch != null) this.pitch = pitch;
    if (yaw != null) this.yaw = yaw;
  }

  apply() {
    const t = this.target;
    t.y = this.land.height(t.x, t.z);
    const cp = Math.cos(this.pitch), sp = Math.sin(this.pitch);
    const c = this.cam.position.set(t.x + Math.sin(this.yaw) * cp * this.dist, t.y + sp * this.dist, t.z + Math.cos(this.yaw) * cp * this.dist);
    const g = this.land.height(c.x, c.z) + 1.2;          // never under the ground
    if (c.y < g) c.y = g;
    this.cam.lookAt(t);
    const alt = c.y - this.land.height(c.x, c.z);
    this.cam.near = Math.max(0.25, Math.min(alt, this.dist) * 0.02);
    this.cam.far = Math.max(2000, this.dist * 8 + 6000);
    this.cam.updateProjectionMatrix();
  }

  input(el) {
    const ptrs = new Map();
    let last = null;
    el.addEventListener("contextmenu", e => e.preventDefault());
    el.addEventListener("pointerdown", e => { el.setPointerCapture(e.pointerId); ptrs.set(e.pointerId, {x: e.clientX, y: e.clientY, b: e.button}); last = null; this.user = true; });
    el.addEventListener("pointerup", e => { ptrs.delete(e.pointerId); last = null; });
    el.addEventListener("pointercancel", e => { ptrs.delete(e.pointerId); last = null; });
    el.addEventListener("pointermove", e => {
      const p = ptrs.get(e.pointerId);
      if (!p) return;
      const dx = e.clientX - p.x, dy = e.clientY - p.y;
      p.x = e.clientX; p.y = e.clientY;
      if (ptrs.size === 2) {
        const [a, b] = [...ptrs.values()], d = Math.hypot(a.x - b.x, a.y - b.y), mid = (a.y + b.y) / 2;
        if (last) { this.zoom(last.d / d); this.yaw -= (e.clientX - e.clientX) * 0; this.pitch = clamp(this.pitch + (mid - last.mid) * 0.004, 0.08, 1.5);
          const ang = Math.atan2(b.y - a.y, b.x - a.x); this.yaw += ang - last.ang; }
        last = {d, mid, ang: Math.atan2(b.y - a.y, b.x - a.x)};
        return;
      }
      if (p.b === 2 || e.shiftKey) { this.yaw -= dx * 0.005; this.pitch = clamp(this.pitch + dy * 0.004, 0.08, 1.5); return; }
      // pan: the ground under the pointer stays under it
      const k = this.dist * 2 * Math.tan(this.cam.fov * Math.PI / 360) / el.clientHeight;
      const s = Math.sin(this.yaw), c = Math.cos(this.yaw);
      this.target.x -= (dx * c + dy * s / Math.max(0.3, Math.sin(this.pitch))) * k;
      this.target.z -= (-dx * s + dy * c / Math.max(0.3, Math.sin(this.pitch))) * k;
    });
    el.addEventListener("wheel", e => { e.preventDefault(); this.user = true; this.zoom(Math.exp(e.deltaY * 0.0012)); }, {passive: false});
  }

  zoom(f) { this.dist = clamp(this.dist * f, 4, this.maxDist ?? 9000); }
}
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

// a smooth path through keys {t, x, z, dist, pitch, yaw}: Catmull-Rom by time, distance in logs
export class Path {
  constructor(keys) { this.k = keys; this.T = keys.at(-1).t; }
  at(t) {
    const K = this.k;
    t = clamp(t, 0, this.T);
    let i = 0;
    while (i < K.length - 2 && K[i + 1].t <= t) i++;
    const a = K[Math.max(0, i - 1)], b = K[i], c = K[i + 1], d = K[Math.min(K.length - 1, i + 2)];
    let u = (t - b.t) / (c.t - b.t);
    if (i === 0) u = u * u * (3 - 2 * u) * 0.5 + u * 0.5;
    if (i === K.length - 2) u = 1 - (1 - u) * (1 - u) * 0.5 - (1 - u) * 0.5 + (1 - u) * (1 - u) * 0.5 - (1 - u) * (1 - u) * 0.5;
    // Catmull-Rom with uneven times (tangents by the neighbours' times)
    const f = key => {
      const p0 = val(a, key), p1 = val(b, key), p2 = val(c, key), p3 = val(d, key);
      const t0 = a.t, t1 = b.t, t2 = c.t, t3 = d.t, h = t2 - t1;
      const m1 = t2 - t0 > 0 ? (p2 - p0) / (t2 - t0) * h : 0, m2 = t3 - t1 > 0 ? (p3 - p1) / (t3 - t1) * h : 0;
      const u2 = u * u, u3 = u2 * u;
      return (2 * u3 - 3 * u2 + 1) * p1 + (u3 - 2 * u2 + u) * m1 + (-2 * u3 + 3 * u2) * p2 + (u3 - u2) * m2;
    };
    return {x: f("x"), z: f("z"), dist: Math.exp(f("ld")), pitch: f("pitch"), yaw: f("yaw")};
  }
}
const val = (k, key) => key === "ld" ? Math.log(k.dist) : k[key];
