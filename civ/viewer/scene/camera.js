// The camera: looks at a point on the land from a distance, turned (yaw) and tilted (pitch, which follows
// the distance: close views are low and cinematic, far views look down like a map). Pans, zooms, turns
// by mouse, touch and keys; glides smoothly to where it is asked to go.
import * as THREE from "three";

export class CameraRig {
  constructor(canvas, land, onPanned, onTap) {
    this.cam = new THREE.PerspectiveCamera(32, 1, 0.1, 600);
    this.land = land;
    this.target = new THREE.Vector3(land.w / 2, 0, land.h / 2);
    this.goal = this.target.clone();
    this.dist = Math.max(land.w, land.h) * 0.9; this.goalDist = this.dist;
    this.yaw = -0.6; this.goalYaw = this.yaw;
    this.minDist = 3.5; this.maxDist = Math.max(land.w, land.h) * 1.4;
    this.input(canvas, onPanned, onTap);
  }

  pitchFor(d) {   // radians above the ground
    const f = Math.min(1, Math.max(0, (d - this.minDist) / (60 - this.minDist)));
    return 0.42 + f * 0.62;
  }

  glideTo(x, z, dist = null) { this.goal.set(x, 0, z); if (dist != null) this.goalDist = dist; }
  jumpTo(x, z) { this.goal.set(x, 0, z); this.target.copy(this.goal); }

  update(dt) {
    const k = 1 - Math.exp(-dt * 5);
    this.target.x += (this.goal.x - this.target.x) * k;
    this.target.z += (this.goal.z - this.target.z) * k;
    this.dist += (this.goalDist - this.dist) * k;
    this.yaw += (this.goalYaw - this.yaw) * k;
    this.target.x = Math.max(0, Math.min(this.land.w, this.target.x));
    this.target.z = Math.max(0, Math.min(this.land.h, this.target.z));
    const ground = this.land.groundAt(this.target.x, this.target.z);
    this.target.y += (ground - this.target.y) * k;
    const p = this.pitchFor(this.dist);
    this.cam.position.set(
      this.target.x + Math.sin(this.yaw) * Math.cos(p) * this.dist,
      this.target.y + Math.sin(p) * this.dist,
      this.target.z + Math.cos(this.yaw) * Math.cos(p) * this.dist);
    // never under the hills
    const under = this.land.groundAt(this.cam.position.x, this.cam.position.z) + 1;
    if (this.cam.position.y < under) this.cam.position.y = under;
    this.cam.lookAt(this.target);
    // see no further than the haze lets one (sky.js: fog ends at 2.6 x the distance): beyond, nothing is drawn
    const far = Math.max(55, this.dist * 2.6 + 6);
    if (Math.abs(far - this.cam.far) > 2) { this.cam.far = far; this.cam.updateProjectionMatrix(); }
  }

  resize(w, h) { this.cam.aspect = w / Math.max(1, h); this.cam.updateProjectionMatrix(); }

  // a point on the land under a screen position (by marching the ray to the ground)
  groundUnder(ndcX, ndcY) {
    const ray = new THREE.Raycaster();
    ray.setFromCamera(new THREE.Vector2(ndcX, ndcY), this.cam);
    const o = ray.ray.origin, d = ray.ray.direction, p = new THREE.Vector3();
    for (let s = 0; s < 800; s += 0.25) {
      p.copy(o).addScaledVector(d, s);
      if (p.y <= this.land.groundAt(p.x, p.z)) return p;
    }
    return null;
  }

  input(cv, onPanned, onTap) {
    const P = new Map();
    let drag = null;
    const panBy = (dx, dy) => {
      const s = this.dist / cv.clientHeight * 1.1, c = Math.cos(this.yaw), n = Math.sin(this.yaw);
      this.goal.x -= (dx * c + dy * n) * s;
      this.goal.z -= (-dx * n + dy * c) * s;
      onPanned();
    };
    cv.addEventListener("contextmenu", e => e.preventDefault());
    cv.addEventListener("pointerdown", e => {
      cv.setPointerCapture(e.pointerId);
      P.set(e.pointerId, [e.clientX, e.clientY]);
      drag = {x: e.clientX, y: e.clientY, moved: false, d: null, a: null, turn: e.button === 2 || e.shiftKey};
    });
    cv.addEventListener("pointermove", e => {
      if (!P.has(e.pointerId) || !drag) return;
      const prev = P.get(e.pointerId);
      P.set(e.pointerId, [e.clientX, e.clientY]);
      if (P.size === 2) {
        const [a, b] = [...P.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]), ang = Math.atan2(b[1] - a[1], b[0] - a[0]);
        if (drag.d) this.goalDist = Math.max(this.minDist, Math.min(this.maxDist, this.goalDist * drag.d / d));
        if (drag.a != null) this.goalYaw += ang - drag.a;
        drag.d = d; drag.a = ang; drag.moved = true;
        return;
      }
      if (Math.abs(e.clientX - drag.x) + Math.abs(e.clientY - drag.y) > 6) drag.moved = true;
      if (!drag.moved) return;
      if (drag.turn) this.goalYaw -= (e.clientX - prev[0]) * 0.006;
      else panBy(e.clientX - prev[0], e.clientY - prev[1]);
    });
    cv.addEventListener("pointerup", e => {
      P.delete(e.pointerId);
      if (drag && !drag.moved && !P.size) onTap(e);
      if (!P.size) drag = null;
    });
    cv.addEventListener("wheel", e => {
      e.preventDefault();
      this.goalDist = Math.max(this.minDist, Math.min(this.maxDist, this.goalDist * Math.exp(e.deltaY * 0.0012)));
    }, {passive: false});
    addEventListener("keydown", e => {
      if (e.target.matches?.("input, select, textarea")) return;
      const step = 40;
      if (e.key === "w") panBy(0, step); if (e.key === "s") panBy(0, -step);
      if (e.key === "a") panBy(step, 0); if (e.key === "d") panBy(-step, 0);
      if (e.key === "q") this.goalYaw += 0.3; if (e.key === "e") this.goalYaw -= 0.3;
      if (e.key === "+" || e.key === "=") this.goalDist = Math.max(this.minDist, this.goalDist / 1.3);
      if (e.key === "-") this.goalDist = Math.min(this.maxDist, this.goalDist * 1.3);
    });
  }
}
