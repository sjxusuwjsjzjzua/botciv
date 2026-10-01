// Smoke: soft puffs rising from fires, from workshops while they work (kilns, furnaces, ovens...), and from
// homes' chimneys in the evening, at night and through the cold. Only near where the camera looks.
import * as THREE from "three";
import {living} from "../art/toon.js";
import {hash as hashId} from "../art/look.js";

const PUFFS = 7, MAX = 140;

export class Smoke {
  constructor(scene, land, store) {
    this.land = land; this.s = store;
    const n = MAX * PUFFS;
    this.pos = new Float32Array(n * 3); this.seed = new Float32Array(n);
    for (let i = 0; i < n; i++) this.seed[i] = (i % PUFFS) / PUFFS + Math.random() * 0.1;
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(this.pos, 3));
    g.setAttribute("aSeed", new THREE.BufferAttribute(this.seed, 1));
    g.setDrawRange(0, 0);
    this.mat = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false,
      uniforms: {uTime: living.uTime, uNight: living.uNight, uScale: {value: 300}},
      vertexShader: `uniform float uTime; uniform float uScale; attribute float aSeed; varying float vAge;
        void main() {
          float age = fract(uTime * 0.22 + aSeed);
          vAge = age;
          vec3 p = position + vec3(sin(aSeed * 40.0 + uTime * 0.7) * 0.12 * age + age * 0.35, age * 1.5, cos(aSeed * 30.0) * 0.1 * age);
          vec4 mv = modelViewMatrix * vec4(p, 1.0);
          gl_Position = projectionMatrix * mv;
          gl_PointSize = uScale * (0.06 + age * 0.22) / -mv.z;
        }`,
      fragmentShader: `uniform float uNight; varying float vAge;
        void main() {
          float d = length(gl_PointCoord - 0.5);
          if (d > 0.5) discard;
          vec3 c = mix(vec3(0.93, 0.92, 0.9), vec3(0.55, 0.56, 0.62), uNight);
          gl_FragColor = vec4(c, (1.0 - d * 2.0) * (1.0 - vAge) * smoothstep(0.0, 0.08, vAge) * 0.5);
        }`,
    });
    this.points = new THREE.Points(g, this.mat);
    this.points.frustumCulled = false;
    scene.add(this.points);
    this.key = "";
  }

  chimney(b) {
    // the cottage's chimney stands at (0.17, -0.06) of the tile, turned with the building (scene/buildings.js)
    const turn = (hashId(b.id) % 4) * Math.PI / 2, x = 0.17, z = -0.06;
    return [x * Math.cos(turn) + z * Math.sin(turn), -x * Math.sin(turn) + z * Math.cos(turn)];
  }

  update(snap, cal, target, h) {
    if (!snap) return;
    const evening = cal.night || cal.part === "evening" || cal.part === "dawn" || cal.season === "winter";
    const key = `${snap.t}|${evening}|${Math.round(target.x / 8)},${Math.round(target.z / 8)}`;
    this.mat.uniforms.uScale.value = h * 0.9;
    if (key === this.key) return;
    this.key = key;
    const cat = this.s.cat.buildings, out = [];
    for (const b of snap.buildings) {
      if (!b.done || Math.hypot(b.x - target.x, b.y - target.z) > 45) continue;
      const roles = cat[b.kind]?.roles || [];
      let top = null;
      if (roles.includes("hearth")) top = 0.2;
      else if (b.working && roles.includes("workshop")) top = 0.55;
      else if (evening && roles.includes("shelter") && b.kind !== "shelter") top = 0.65;
      if (top == null) continue;
      // homes smoke from the chimney (art/buildings.js: cottage), the rest from the middle
      const chim = top === 0.65 ? this.chimney(b) : [0, 0];
      out.push([b.x + 0.5 + chim[0], this.land.groundAt(b.x + 0.5, b.y + 0.5) + top, b.y + 0.5 + chim[1]]);
      if (out.length >= MAX) break;
    }
    let i = 0;
    for (const [x, y, z] of out) for (let k = 0; k < PUFFS; k++, i++) { this.pos[i * 3] = x; this.pos[i * 3 + 1] = y; this.pos[i * 3 + 2] = z; }
    const g = this.points.geometry;
    g.attributes.position.needsUpdate = true;
    g.setDrawRange(0, i);
  }
}
