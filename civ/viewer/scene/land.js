// The land: a smooth height field over the tile grid, coloured by terrain with soft blends, and its water.
// heightAt(x, z) is the ground everything stands on (people, plants, buildings). One unit = one tile;
// tile (tx, ty) covers x in [tx, tx+1], z in [ty, ty+1].
import * as THREE from "three";
import {terrainOf, WATER_LEVEL} from "../art/palette.js";
import {toon, living} from "../art/toon.js";
import {rng} from "../art/look.js";

const RES = 3;                      // vertices per tile edge

export class Land {
  constructor(terrain, seed = "land") {
    this.terrain = terrain;
    this.h = terrain.length; this.w = terrain[0].length;
    const r = rng(seed);
    // a height at each tile's centre: by its terrain, with gentle noise; hills and mountains rise unevenly
    this.base = new Float32Array(this.w * this.h);
    const noise = makeNoise(r);
    for (let y = 0; y < this.h; y++) for (let x = 0; x < this.w; x++) {
      const ch = this.at(x, y), t = terrainOf(ch);
      let v = t.height + (noise(x * 0.18, y * 0.18) - 0.5) * 0.08;
      if (ch === "h") v += noise(x * 0.35 + 9, y * 0.35) * 0.55;
      if (ch === "^") v += noise(x * 0.3 + 3, y * 0.3 + 7) * 1.4 + noise(x * 0.9, y * 0.9) * 0.35;
      this.base[y * this.w + x] = v;
    }
    // mountains rise with how far in they are; water deepens away from shore
    for (let pass = 0; pass < 2; pass++) for (let y = 0; y < this.h; y++) for (let x = 0; x < this.w; x++) {
      const ch = this.at(x, y);
      if (ch !== "^" && ch !== "~") continue;
      let same = 0;
      for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) same += this.at(x + dx, y + dy) === ch ? 1 : 0;
      if (ch === "^") this.base[y * this.w + x] = (this.base[y * this.w + x] - 0.75) * (0.35 + 0.65 * same / 9) + 0.75 + (same - 5) * 0.05;
      else this.base[y * this.w + x] -= (same - 5) * 0.04;
    }
  }

  at(x, y) {
    x = Math.max(0, Math.min(this.w - 1, x | 0)); y = Math.max(0, Math.min(this.h - 1, y | 0));
    return this.terrain[y][x];
  }
  baseAt(x, y) {
    x = Math.max(0, Math.min(this.w - 1, x)); y = Math.max(0, Math.min(this.h - 1, y));
    return this.base[y * this.w + x];
  }
  isWater(x, y) { return this.at(x, y) === "~"; }

  // the ground at a point: smooth interpolation of the tile centres around it
  heightAt(x, z) {
    const fx = x - 0.5, fz = z - 0.5, x0 = Math.floor(fx), z0 = Math.floor(fz);
    let u = fx - x0, v = fz - z0;
    u = u * u * (3 - 2 * u); v = v * v * (3 - 2 * v);
    const a = this.baseAt(x0, z0), b = this.baseAt(x0 + 1, z0), c = this.baseAt(x0, z0 + 1), d = this.baseAt(x0 + 1, z0 + 1);
    return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v;
  }
  // where one stands: never below the water's face
  groundAt(x, z) { return Math.max(this.heightAt(x, z), WATER_LEVEL); }

  mesh() {
    const W = this.w * RES + 1, H = this.h * RES + 1;
    const pos = new Float32Array(W * H * 3), col = new Float32Array(W * H * 3);
    const c = new THREE.Color(), tmp = new THREE.Color(), r = rng("tint");
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
      const x = i / RES, z = j / RES, k = (j * W + i) * 3;
      pos[k] = x; pos[k + 1] = this.heightAt(x, z); pos[k + 2] = z;
      // colour: blend of the four tiles around, by nearness; a little variation
      const fx = x - 0.5, fz = z - 0.5, x0 = Math.floor(fx), z0 = Math.floor(fz), u = fx - x0, v = fz - z0;
      c.setRGB(0, 0, 0);
      for (const [dx, dz, wgt] of [[0, 0, (1 - u) * (1 - v)], [1, 0, u * (1 - v)], [0, 1, (1 - u) * v], [1, 1, u * v]]) {
        tmp.setHex(terrainOf(this.at(x0 + dx, z0 + dz)).color);
        c.r += tmp.r * wgt; c.g += tmp.g * wgt; c.b += tmp.b * wgt;
      }
      const jit = 0.94 + r() * 0.1;
      // high ground pales toward rock
      const hgt = pos[k + 1];
      if (hgt > 1.2) c.lerp(tmp.setHex(0xb7b0a6), Math.min(1, (hgt - 1.2) / 1.2));
      col[k] = c.r * jit; col[k + 1] = c.g * jit; col[k + 2] = c.b * jit;
    }
    const idx = [];
    for (let j = 0; j < H - 1; j++) for (let i = 0; i < W - 1; i++) {
      const a = j * W + i, b = a + 1, d = a + W, e = d + 1;
      idx.push(a, d, b, b, d, e);
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    g.setAttribute("color", new THREE.BufferAttribute(col, 3));
    g.setIndex(idx);
    g.computeVertexNormals();
    const m = new THREE.Mesh(g, toon({vertexColors: true, snow: true}));
    m.receiveShadow = true;
    m.name = "land";
    return m;
  }

  // water: one sheet at the water's level, its depth and the shore read from a small texture of the land
  water() {
    const data = new Uint8Array(this.w * this.h * 4);
    for (let y = 0; y < this.h; y++) for (let x = 0; x < this.w; x++) {
      const depth = Math.max(0, Math.min(1, (WATER_LEVEL - this.baseAt(x, y)) / 0.6));
      const k = (y * this.w + x) * 4;
      data[k] = depth * 255; data[k + 3] = 255;
    }
    const tex = new THREE.DataTexture(data, this.w, this.h, THREE.RGBAFormat);
    tex.magFilter = tex.minFilter = THREE.LinearFilter;
    tex.needsUpdate = true;
    const g = new THREE.PlaneGeometry(this.w + 40, this.h + 40, this.w + 40, this.h + 40);
    g.rotateX(-Math.PI / 2);
    g.translate(this.w / 2, WATER_LEVEL, this.h / 2);
    const mat = new THREE.ShaderMaterial({
      transparent: true, depthWrite: false, fog: true,
      uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, {
        uDepth: {value: tex}, uSize: {value: new THREE.Vector2(this.w, this.h)},
        uShallow: {value: new THREE.Color(0x7fd0c8)}, uDeep: {value: new THREE.Color(0x2f7fa6)},
        uSky: {value: new THREE.Color(0xd6e8f8)}, uSun: {value: new THREE.Color(0xffffff)}, uLight: {value: 1},
        uSunDir: {value: new THREE.Vector3(0.3, 0.8, 0.2)},
      }]),
      vertexShader: `
        uniform float uTime; varying vec3 vW; varying vec2 vUv2;
        #include <fog_pars_vertex>
        void main() {
          vec3 p = position;
          p.y += sin(p.x * 1.3 + uTime * 1.1) * 0.025 + sin(p.z * 1.7 - uTime * 0.9) * 0.02;
          vW = p;
          vec4 mvPosition = modelViewMatrix * vec4(p, 1.0);
          gl_Position = projectionMatrix * mvPosition;
          #include <fog_vertex>
        }`,
      fragmentShader: `
        uniform sampler2D uDepth; uniform vec2 uSize; uniform vec3 uShallow; uniform vec3 uDeep; uniform vec3 uSky; uniform vec3 uSun;
        uniform float uLight; uniform float uTime; uniform vec3 uSunDir; varying vec3 vW;
        #include <fog_pars_fragment>
        void main() {
          vec2 uv = vW.xz / uSize;
          float d = texture2D(uDepth, uv).r;
          if (uv.x < 0.0 || uv.y < 0.0 || uv.x > 1.0 || uv.y > 1.0) d = 1.0;
          vec3 col = mix(uShallow, uDeep, smoothstep(0.05, 0.7, d));
          // ripples of light
          float rip = sin(vW.x * 4.0 + uTime * 1.6 + sin(vW.z * 3.0 + uTime)) * sin(vW.z * 4.5 - uTime * 1.3);
          col += uSun * smoothstep(0.86, 0.99, rip) * 0.35;
          // foam at the shore
          float foam = smoothstep(0.12, 0.02, d) * (0.6 + 0.4 * sin(uTime * 2.0 + vW.x * 3.0 + vW.z * 2.0));
          col = mix(col, vec3(1.0), foam * 0.8);
          col = mix(col, uSky, 0.18) * uLight;
          gl_FragColor = vec4(col, mix(0.72, 0.92, smoothstep(0.0, 0.5, d)) + foam * 0.2);
          #include <fog_fragment>
        }`,
    });
    mat.uniforms.uTime = living.uTime;
    const m = new THREE.Mesh(g, mat);
    m.renderOrder = 2;
    m.name = "water";
    return m;
  }
}

// smooth value noise in [0, 1]
function makeNoise(r) {
  const P = new Float32Array(256 * 256);
  for (let i = 0; i < P.length; i++) P[i] = r();
  const at = (x, y) => P[((y & 255) << 8) | (x & 255)];
  return (x, y) => {
    const xi = Math.floor(x), yi = Math.floor(y);
    let u = x - xi, v = y - yi;
    u = u * u * (3 - 2 * u); v = v * v * (3 - 2 * v);
    return (at(xi, yi) * (1 - u) + at(xi + 1, yi) * u) * (1 - v) + (at(xi, yi + 1) * (1 - u) + at(xi + 1, yi + 1) * u) * v;
  };
}
