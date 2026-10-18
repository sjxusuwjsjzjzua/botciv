// The land drawn as one seamless surface from kilometres up down to one's feet (towns_spec §9.2): a quadtree of
// patches, each the same grid of N x N cells, finer near the camera (a leaf 125 m: 2.6 m cells) and coarser far
// (up to 16 km). Each vertex also knows the height the next coarser patch would give it, and slides there as it
// nears the end of its patch's range (geomorphing), so a patch changing detail changes nothing on screen: no
// popping, no seams (skirts close any crack between neighbours). The ground's colour is not in the mesh at all: it
// is read from maps laid over the world by position (the land's blend, and the settlement's lanes, green and strips
// painted finely), so it is the same at every level of detail and no tile or chunk edge can show.
import * as THREE from "three";
import {toonRamp} from "../art/toon.js";

export class Terrain {
  constructor(scene, land, opts = {}) {
    this.scene = scene; this.land = land;
    this.N = opts.N ?? 48;
    this.leaf = opts.leaf ?? 125;
    this.levels = opts.levels ?? 7;                       // root = leaf * 2^levels (16 km)
    this.K = opts.K ?? 2.3;                               // a patch of size S serves out to K * S (its range)
    const root = this.leaf * 2 ** this.levels;
    this.origin = opts.origin ?? [3000 - root / 2, 1500 - root / 2];
    this.budget = opts.budget ?? 3;                       // patches built a frame (more when warming)
    this.nodes = new Map();                               // key -> {geo, mesh, minH, maxH}
    this.group = new THREE.Group(); this.group.name = "terrain";
    scene.add(this.group);
    this.maps = opts.maps;                                // {color: {tex, box}, far: {tex, box}, detail: {tex, box}, mid?}
    // the maps' uniforms, shared by every level's material, so a map swapped (setMap) changes them all
    const maps = this.maps, mid = maps.mid || maps.far;
    this.U = {
      uColor: {value: maps.color.tex}, uColorBox: {value: new THREE.Vector4(...maps.color.box)},
      uMid: {value: mid.tex}, uMidBox: {value: new THREE.Vector4(...mid.box)},
      uFar: {value: maps.far.tex}, uFarBox: {value: new THREE.Vector4(...maps.far.box)},
      uDetail: {value: maps.detail.tex}, uDetailBox: {value: new THREE.Vector4(...maps.detail.box)},
      uSnow: maps.snow,
    };
    this.mats = [];
    for (let L = 0; L <= this.levels; L++) this.mats.push(this.material(this.range(L)));
    this.drawn = [];
    this.stats = {built: 0};
  }

  range(L) { return this.leaf * 2 ** L * this.K; }

  // lay a new map (color, mid, far or detail) over the land: {tex, box}; the old texture is let go
  setMap(name, {tex, box}) {
    const U = {color: ["uColor", "uColorBox"], mid: ["uMid", "uMidBox"], far: ["uFar", "uFarBox"], detail: ["uDetail", "uDetailBox"]}[name];
    const old = this.U[U[0]].value;
    this.U[U[0]].value = tex; this.U[U[1]].value.set(...box);
    if (old && old !== tex && !Object.values(this.U).some(u => u.value === old)) old.dispose();
  }

  material(range) {
    const m = new THREE.MeshToonMaterial({color: 0xffffff, gradientMap: toonRamp()});
    const uni = {uRange: {value: range}, ...this.U};
    m.customProgramCacheKey = () => "terrain5";
    m.onBeforeCompile = sh => {
      Object.assign(sh.uniforms, uni);
      sh.vertexShader = sh.vertexShader
        .replace("#include <common>", `#include <common>
          attribute float aMorph; uniform float uRange; varying vec3 vW;`)
        .replace("#include <begin_vertex>", `#include <begin_vertex>
          vec3 w0 = (modelMatrix * vec4(position, 1.0)).xyz;
          float morph = smoothstep(uRange * 0.62, uRange * 0.95, distance(cameraPosition, w0));
          transformed.y += aMorph * morph;
          vW = w0 + vec3(0.0, aMorph * morph, 0.0);`);
      sh.fragmentShader = sh.fragmentShader
        .replace("#include <common>", `#include <common>
          uniform sampler2D uColor; uniform vec4 uColorBox; uniform sampler2D uFar; uniform vec4 uFarBox;
          uniform sampler2D uMid; uniform vec4 uMidBox;
          uniform sampler2D uDetail; uniform vec4 uDetailBox; uniform float uSnow; varying vec3 vW;
          float th(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
          float tn(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
            return mix(mix(th(i), th(i + vec2(1, 0)), f.x), mix(th(i + vec2(0, 1)), th(i + vec2(1, 1)), f.x), f.y); }`)
        .replace("#include <color_fragment>", `#include <color_fragment>
          vec2 cuv = (vW.xz - uColorBox.xy) / uColorBox.zw;
          vec3 base = texture2D(uFar, (vW.xz - uFarBox.xy) / uFarBox.zw).rgb;
          vec2 muv = (vW.xz - uMidBox.xy) / uMidBox.zw, me = min(muv, 1.0 - muv);
          base = mix(base, texture2D(uMid, muv).rgb, smoothstep(0.0, 0.03, min(me.x, me.y)));
          vec2 ce = min(cuv, 1.0 - cuv);
          float inMain = smoothstep(0.0, 0.03, min(ce.x, ce.y));
          base = mix(base, texture2D(uColor, cuv).rgb, inMain);
          vec2 duv = (vW.xz - uDetailBox.xy) / uDetailBox.zw;
          if (duv.x > 0.0 && duv.y > 0.0 && duv.x < 1.0 && duv.y < 1.0) { vec4 d = texture2D(uDetail, duv); base = mix(base, d.rgb, d.a); }
          // close up, the ground is never flat paint: mottling and fine grain, fading with distance
          float dist = distance(cameraPosition, vW);
          float near = 1.0 - smoothstep(60.0, 420.0, dist);
          float mott = (tn(vW.xz / 7.0) - 0.5) * 0.12 + (tn(vW.xz / 1.6) - 0.5) * 0.08 * (1.0 - smoothstep(20.0, 120.0, dist));
          base *= 1.0 + mott * near + (tn(vW.xz / 60.0) - 0.5) * 0.08;
          if (uSnow > 0.0) base = mix(base, vec3(0.93, 0.95, 1.0), uSnow * smoothstep(0.35, 0.6, tn(vW.xz / 4.0) * 0.4 + 0.6 * uSnow));
          diffuseColor.rgb = base;`);
    };
    return m;
  }

  key(L, i, j) { return L * 1e8 + i * 1e4 + j; }

  // a patch: N x N cells over its square, plus a skirt hanging from its edges
  build(L, i, j) {
    const N = this.N, S = this.leaf * 2 ** L, h = S / N, x0 = this.origin[0] + i * S, y0 = this.origin[1] + j * S;
    const P = N + 3, hs = new Float32Array(P * P);           // heights with a one-cell margin (for normals)
    // a coarse patch cannot hold a channel narrower than its cells: there, ground near the water is lowered under
    // it, so the river ribbon (drawn at its true width) is never covered by the coarse land far off
    const dip = Math.max(0, h * 0.7 - 4);
    for (let b = 0; b < P; b++) for (let a = 0; a < P; a++) {
      const g = this.land.ground(x0 + (a - 1) * h, y0 + (b - 1) * h);
      hs[b * P + a] = g.chan < dip ? Math.min(g.h, g.level - 0.6) : g.h;
    }
    const H = (a, b) => hs[(b + 1) * P + a + 1];
    const V = (N + 1) * (N + 1), E = 4 * (N + 1);
    const pos = new Float32Array((V + E) * 3), nor = new Float32Array((V + E) * 3), mor = new Float32Array(V + E);
    let minH = Infinity, maxH = -Infinity;
    for (let b = 0; b <= N; b++) for (let a = 0; a <= N; a++) {
      const k = b * (N + 1) + a, y = H(a, b);
      pos[k * 3] = x0 + a * h; pos[k * 3 + 1] = y; pos[k * 3 + 2] = y0 + b * h;
      const nx = H(a - 1, b) - H(a + 1, b), nz = H(a, b - 1) - H(a, b + 1), ny = 2 * h, l = Math.hypot(nx, ny, nz);
      nor[k * 3] = nx / l; nor[k * 3 + 1] = ny / l; nor[k * 3 + 2] = nz / l;
      // the height the coarser grid (every other vertex, same diagonals) gives here
      let c;
      const ao = a & 1, bo = b & 1;
      if (!ao && !bo) c = y;
      else if (ao && !bo) c = (H(a - 1, b) + H(a + 1, b)) / 2;
      else if (!ao && bo) c = (H(a, b - 1) + H(a, b + 1)) / 2;
      else c = (H(a + 1, b - 1) + H(a - 1, b + 1)) / 2;
      mor[k] = c - y;
      minH = Math.min(minH, y); maxH = Math.max(maxH, y);
    }
    // skirt: a copy of the edge ring, hanging down
    const ring = [];
    for (let a = 0; a <= N; a++) ring.push([a, 0]);
    for (let b = 0; b <= N; b++) ring.push([N, b]);
    for (let a = N; a >= 0; a--) ring.push([a, N]);
    for (let b = N; b >= 0; b--) ring.push([0, b]);
    const drop = Math.max(1.5, h * 0.6);
    ring.forEach(([a, b], e) => {
      const s = b * (N + 1) + a, k = V + e;
      pos[k * 3] = pos[s * 3]; pos[k * 3 + 1] = pos[s * 3 + 1] - drop; pos[k * 3 + 2] = pos[s * 3 + 2];
      nor[k * 3] = nor[s * 3]; nor[k * 3 + 1] = nor[s * 3 + 1]; nor[k * 3 + 2] = nor[s * 3 + 2];
      mor[k] = mor[s];
    });
    const idx = [];
    for (let b = 0; b < N; b++) for (let a = 0; a < N; a++) {
      const p = b * (N + 1) + a, q = p + 1, r = p + N + 1, s = r + 1;
      idx.push(p, r, q, q, r, s);                             // diagonal q-r, as the morph assumes
    }
    for (let e = 0; e < ring.length - 1; e++) {
      const [a1, b1] = ring[e], [a2, b2] = ring[e + 1];
      const s1 = b1 * (N + 1) + a1, s2 = b2 * (N + 1) + a2, k1 = V + e, k2 = V + e + 1;
      idx.push(s1, k1, s2, s2, k1, k2, s1, s2, k1, s2, k2, k1);   // both faces: cheap, and never a hole from behind
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    g.setAttribute("normal", new THREE.BufferAttribute(nor, 3));
    g.setAttribute("aMorph", new THREE.BufferAttribute(mor, 1));
    g.setIndex(idx);
    g.boundingSphere = new THREE.Sphere(new THREE.Vector3(x0 + S / 2, (minH + maxH) / 2, y0 + S / 2), Math.hypot(S / 2, S / 2, (maxH - minH) / 2 + 3));
    const m = new THREE.Mesh(g, this.mats[L]);
    m.receiveShadow = true; m.castShadow = false;
    m.matrixAutoUpdate = false;
    this.stats.built++;
    return {mesh: m, minH, maxH, L, i, j};
  }

  node(L, i, j, build) {
    const k = this.key(L, i, j);
    let n = this.nodes.get(k);
    if (!n && build && this.left > 0 && performance.now() < this.deadline) { this.left--; n = this.build(L, i, j); this.nodes.set(k, n); }
    return n;
  }

  // the patches to draw for a camera at p: a patch is split while the camera is within its children's range
  select(p, out, L = this.levels, i = 0, j = 0) {
    const S = this.leaf * 2 ** L, x0 = this.origin[0] + i * S, y0 = this.origin[1] + j * S;
    const n = this.node(L, i, j, true);
    const lo = n ? n.minH : 0, hi = n ? n.maxH : 60;
    const dx = Math.max(x0 - p.x, 0, p.x - x0 - S), dz = Math.max(y0 - p.z, 0, p.z - y0 - S), dy = Math.max(lo - p.y, 0, p.y - hi);
    const d = Math.hypot(dx, dy, dz);
    if (L > 0 && d < this.range(L - 1)) {
      // all four children ready: draw them; otherwise this patch stands in for them until they are
      const kids = [[0, 0], [1, 0], [0, 1], [1, 1]].map(([a, b]) => this.node(L - 1, i * 2 + a, j * 2 + b, true));
      if (kids.every(Boolean)) { for (const [a, b] of [[0, 0], [1, 0], [0, 1], [1, 1]]) this.select(p, out, L - 1, i * 2 + a, j * 2 + b); return; }
    }
    if (n) out.push(n);
  }

  update(camPos, budget = this.budget, ms = Infinity) {
    this.left = budget; this.deadline = performance.now() + ms;
    const out = [];
    this.select(camPos, out);
    for (const n of this.drawn) n.mesh.visible = false;
    for (const n of out) { if (!n.mesh.parent) this.group.add(n.mesh); n.mesh.visible = true; }
    this.drawn = out;
    return out.length;
  }

  // build ahead what a list of camera positions will need (the tour), so nothing is built while flying
  warm(positions) {
    for (const p of positions) for (let pass = 0; pass < 8; pass++) { this.left = 1e9; this.deadline = Infinity; const out = []; this.select(p, out); }
  }

  // the ground as drawn is the land's height; kept here so objects ask one place
  heightAt(X, Y) { return this.land.height(X, Y); }
}

// The maps laid over the land: the land's own blend over the scene (and a coarse one beyond), built from landAt
export function landMaps(land, box, size, farBox, farSize) {
  const make = (bx, [w, h]) => {
    const data = new Uint8Array(w * h * 4), c = [0, 0, 0];
    for (let j = 0; j < h; j++) for (let i = 0; i < w; i++) {
      land.color(bx[0] + (i + 0.5) / w * bx[2], bx[1] + (j + 0.5) / h * bx[3], c);
      const k = (j * w + i) * 4;
      data[k] = Math.min(255, c[0] * 255); data[k + 1] = Math.min(255, c[1] * 255); data[k + 2] = Math.min(255, c[2] * 255); data[k + 3] = 255;
    }
    return mapTexture(data, w, h);
  };
  return {color: {tex: make(box, size), box}, far: {tex: make(farBox, farSize), box: farBox}};
}

// a map's texture from its pixels (RGBA, row by row from the box's corner): what landMaps and the painting worker make
export function mapTexture(data, w, h) {
  const t = new THREE.DataTexture(data, w, h, THREE.RGBAFormat);
  t.colorSpace = THREE.SRGBColorSpace; t.magFilter = THREE.LinearFilter; t.minFilter = THREE.LinearMipmapLinearFilter;
  t.generateMipmaps = true; t.anisotropy = 4; t.wrapS = t.wrapT = THREE.ClampToEdgeWrapping; t.needsUpdate = true;
  return t;
}
