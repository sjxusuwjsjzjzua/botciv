// Trees over the land, by its tree cover: near the eye whole trees (instanced, casting shadows), further off a soft
// lit disc for each (an impostor, two triangles), dithered into one another over a band of distance so no tree ever
// pops. Grouped in blocks of 500 m so what is out of view is skipped. Forests thin into scrub and single trees.
import * as THREE from "three";
import * as V from "../art/village.js";
import {vnoise} from "./land.js";

const BLOCK = 500;

export class Flora {
  constructor(scene, land, opts = {}) {
    this.scene = scene; this.land = land;
    this.near = opts.near ?? [170, 250];             // whole trees fade out over this band; impostors fade in
    this.group = new THREE.Group(); this.group.name = "trees"; scene.add(this.group);
    const geos = opts.models ? {broadleaf: opts.models.broadleaf, conifer: opts.models.conifer} : {broadleaf: V.broadleaf(4), conifer: V.conifer()};
    const matMesh = V.material("tree", {fade: this.near});
    const depth = fadeDepth(this.near);
    this.impMat = impostorMaterial(this.near, opts.light);
    this.blocks = new Map();
    const [x0, y0, x1, y1] = opts.box ?? [-1500, -800, 7600, 3800];
    const cell = opts.cell ?? 11;
    let seed = 3, count = 0;
    const r = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
    const keepOff = opts.keepOff || (() => false);
    for (let Y = y0; Y < y1; Y += cell) for (let X = x0; X < x1; X += cell) {
      const x = X + r() * cell, y = Y + r() * cell, u = r(), k = r(), s = r();
      const g = land.ground(x, y);
      if (g.chan < 4) continue;
      const cover = land.treeCover(x, y, g.chan);
      // a little scrub and single trees out in the meadows, in loose groups
      const scrub = cover < 0.15 ? 0.03 * Math.max(0, vnoise(x / 260, y / 260, 51) - 0.45) * 2 : 0;
      if (u > cover + scrub) continue;
      if (keepOff(x, y)) continue;
      const conifer = vnoise(x / 400, y / 400, 52) * 0.8 + k * 0.4 > 0.72;
      const key = Math.floor(x / BLOCK) * 1000 + Math.floor(y / BLOCK);
      let b = this.blocks.get(key);
      if (!b) { b = {broadleaf: [], conifer: [], cx: (Math.floor(x / BLOCK) + 0.5) * BLOCK, cz: (Math.floor(y / BLOCK) + 0.5) * BLOCK}; this.blocks.set(key, b); }
      b[conifer ? "conifer" : "broadleaf"].push([x, g.h - 0.2, y, s * 6.28, 0.75 + s * 0.55]);
      count++;
    }
    for (const [x, y, kind, s] of opts.extra || []) {
      const key = Math.floor(x / BLOCK) * 1000 + Math.floor(y / BLOCK);
      let b = this.blocks.get(key);
      if (!b) { b = {broadleaf: [], conifer: [], cx: (Math.floor(x / BLOCK) + 0.5) * BLOCK, cz: (Math.floor(y / BLOCK) + 0.5) * BLOCK}; this.blocks.set(key, b); }
      b[kind].push([x, land.height(x, y) - 0.2, y, (x * 0.37) % 6.28, s]);
      count++;
    }
    this.count = count;
    const M = new THREE.Matrix4(), q = new THREE.Quaternion(), up = new THREE.Vector3(0, 1, 0), c = new THREE.Color();
    for (const b of this.blocks.values()) {
      b.meshes = [];
      for (const kind of ["broadleaf", "conifer"]) {
        const list = b[kind];
        if (!list.length) continue;
        const m = new THREE.InstancedMesh(geos[kind], matMesh, list.length);
        list.forEach(([x, y, z, a, s], i) => {
          M.compose(new THREE.Vector3(x, y, z), q.setFromAxisAngle(up, a), new THREE.Vector3(s, s * (0.9 + (a % 1) * 0.25), s));
          m.setMatrixAt(i, M); if (opts.models) m.setColorAt(i, c.set(0xffffff)); else m.setColorAt(i, c.setHSL(0.22 + (a % 0.6) * 0.06, 0.4, 0.42 + (s - 0.75) * 0.25).multiplyScalar(2.2));
        });
        m.castShadow = true; m.receiveShadow = true; m.customDepthMaterial = depth;
        m.computeBoundingSphere(); m.visible = false;
        this.group.add(m); b.meshes.push(m);
      }
      // impostors: both kinds in one mesh; the kind and size ride in the instance matrix's scale
      const all = [...b.broadleaf.map(t => [...t, 0]), ...b.conifer.map(t => [...t, 1])];
      const g = new THREE.InstancedBufferGeometry();
      g.setAttribute("position", new THREE.Float32BufferAttribute([-1, -1, 0, 1, -1, 0, 1, 1, 0, -1, 1, 0], 3));
      g.setIndex([0, 1, 2, 0, 2, 3]);
      const off = new Float32Array(all.length * 4), tint = new Float32Array(all.length * 3);
      all.forEach(([x, y, z, a, s, kind], i) => {
        off.set([x, y, z, (kind ? -1 : 1) * s], i * 4);
        c.setHSL(kind ? 0.37 : 0.27 + (a % 0.6) * 0.06, kind ? 0.36 : 0.42, kind ? 0.22 : 0.26 + (s - 0.75) * 0.12);
        tint.set([c.r, c.g, c.b], i * 3);
      });
      g.setAttribute("aOff", new THREE.InstancedBufferAttribute(off, 4));
      g.setAttribute("aTint", new THREE.InstancedBufferAttribute(tint, 3));
      g.instanceCount = all.length;
      g.boundingSphere = new THREE.Sphere(new THREE.Vector3(b.cx, 30, b.cz), BLOCK * 0.75 + 20);
      const imp = new THREE.Mesh(g, this.impMat);
      imp.name = "impostors";
      this.group.add(imp); b.imp = imp;
    }
  }

  // whole trees only in blocks near the eye
  update(eye) {
    for (const b of this.blocks.values()) {
      const d = Math.hypot(eye.x - b.cx, eye.z - b.cz) - BLOCK * 0.71;
      const near = d < this.near[1] + 20 && eye.y < this.near[1] + 200;
      for (const m of b.meshes) m.visible = near;
    }
  }
}

// a shadow for the whole trees that fades with them (in the light's pass the eye is the main camera's)
function fadeDepth([n, f]) {
  const m = new THREE.MeshDepthMaterial({depthPacking: THREE.RGBADepthPacking});
  m.onBeforeCompile = sh => {
    sh.uniforms.uEye = V.EYE;
    sh.vertexShader = sh.vertexShader.replace("#include <common>", "#include <common>\nuniform vec3 uEye;")
      .replace("#include <begin_vertex>", `#include <begin_vertex>
        #ifdef USE_INSTANCING
          if (smoothstep(${n.toFixed(1)}, ${f.toFixed(1)}, distance((modelMatrix * vec4(instanceMatrix[3].xyz, 1.0)).xyz, uEye)) > 0.5) transformed = vec3(0.0);
        #endif`);
  };
  return m;
}

// the far tree: a disc (a broadleaf's round crown) or a spire (a conifer) facing the eye, lit as a ball by the sun
// with the toon steps, its edge ruffled; seen from high above, every crown rounds into a disc
function impostorMaterial([n, f], light) {
  const m = new THREE.ShaderMaterial({
    fog: true,
    uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, {}]),
    vertexShader: `
      attribute vec4 aOff; attribute vec3 aTint; uniform vec3 uEye;
      varying vec2 vQ; varying vec3 vTint; varying float vKind; varying float vFade; varying float vTop;
      #include <fog_pars_vertex>
      void main() {
        float kind = aOff.w < 0.0 ? 1.0 : 0.0, s = abs(aOff.w);
        vec3 c = aOff.xyz + vec3(0.0, (kind > 0.5 ? 6.2 : 5.6) * s, 0.0);
        float far = 1.0 + smoothstep(700.0, 3500.0, distance(c, uEye)) * 0.7;      // far off, crowns close into a canopy
        vec2 size = (kind > 0.5 ? vec2(3.2, 5.6) : vec2(3.5, 3.4)) * s * far;
        vec4 mv = modelViewMatrix * vec4(c, 1.0);
        vec3 toEye = normalize(uEye - c);
        vTop = smoothstep(0.55, 0.95, toEye.y);
        size.y = mix(size.y, size.x, vTop);
        mv.xy += position.xy * size;
        vQ = position.xy; vTint = aTint; vKind = kind;
        vFade = smoothstep(${n.toFixed(1)}, ${f.toFixed(1)}, distance(c, uEye));
        vec4 mvPosition = mv;
        gl_Position = projectionMatrix * mv;
        if (vFade <= 0.0) gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
        #include <fog_vertex>
      }`,
    fragmentShader: `
      uniform vec3 uSunV; uniform vec3 uSunCol; uniform vec3 uSky; uniform vec3 uGround;
      varying vec2 vQ; varying vec3 vTint; varying float vKind; varying float vFade; varying float vTop;
      #include <fog_pars_fragment>
      ${V.DITHER}
      void main() {
        if (vFade <= 1.0 - bayer4()) discard;
        vec2 q = vQ;
        float a = atan(q.y, q.x);
        float r = length(q);
        float edge = 0.86 + 0.08 * sin(a * 7.0 + vTint.r * 40.0) + 0.05 * sin(a * 13.0);
        // a conifer from the side: a spire, narrowing upward
        float spire = abs(q.x) - (1.0 - (q.y * 0.5 + 0.5)) * 0.95 - 0.04 * sin(q.y * 18.0);
        float inside = mix(r - edge, mix(spire, r - edge, vTop), vKind);
        if (inside > 0.0) discard;
        vec3 nrm = normalize(vec3(q * 0.9, sqrt(max(0.05, 1.0 - r * r))));
        float d = dot(nrm, uSunV);
        float ramp = d < 0.0 ? 0.43 : d < 0.45 ? 0.73 : 1.0;
        vec3 col = vTint * (uSunCol * ramp + mix(uGround, uSky, 0.5 + 0.5 * nrm.y)) / 3.14159;
        col *= 0.92 + 0.12 * sin(q.x * 9.0 + q.y * 7.0 + vTint.g * 30.0);
        gl_FragColor = vec4(col, 1.0);
        #include <tonemapping_fragment>
        #include <colorspace_fragment>
        #include <fog_fragment>
      }`,
  });
  m.uniforms.uEye = V.EYE;
  Object.assign(m.uniforms, light);
  return m;
}
