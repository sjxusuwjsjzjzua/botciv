// The settlement kit in metres (world5; docs/world5_handoff.md §5.5, towns_spec §9.3): long house, store on stilts,
// well, shrine, beehive kiln, grave stone, plank bridge, conical hut, fire, wattle fence, crops (wheat, flax), reeds
// and cattails, trees (broadleaf and conifer). Each builder returns parts [geometry, material name]; the materials
// (toon, with patterns drawn in the shader from the object's own coordinates: thatch in layered courses with cut
// strands, woven wattle, planks, plaster, stone) come from `material(name)`. Data-driven by kind and style, so the
// viewer's step 5 reuses them for every settlement; used by the demo page only until then.
import * as THREE from "three";
import {mergeGeometries, mergeVertices} from "three/addons/BufferGeometryUtils.min.js";
import {toonRamp, living} from "./toon.js";

export const VCOL = {
  thatch: 0xe9bb55, thatchDark: 0xc99a42, plaster: 0xebdfc4, timber: 0x8a5531, dark: 0x5e3a20, plank: 0xa06a3a,
  door: 0x3a2518, plinth: 0x9a8a72, stone: 0xa59e90, grave: 0xaaa69a, clay: 0xc77c4f, water: 0x2e3e48, wattle: 0x8e5a2e,
  post: 0x7a4a28, daub: 0xb89466, ember: 0xff9a3c, lantern: 0xffc060, cloth: 0xd84a3a, hide: 0xc49a68, bark: 0x6a4a30,
};

// ---------- materials ----------
const PATTERNS = {
  // thatch: courses laid in rows up the roof, each catching the light at its lower lip, with short dark cut
  // strokes scattered along them and fine strands running down the slope
  thatch: `
    float course = vObj.y / 0.62 + (pn(vec2(sc * 0.55, floor(vObj.y / 0.62) * 3.1)) - 0.5) * 0.5;
    float fc = fract(course), row = floor(course);
    float strand = pn(vec2(sc * 7.0, vObj.y * 1.3)) * 0.6 + pn(vec2(sc * 19.0, vObj.y * 3.0)) * 0.4;
    vec3 tc = diffuseColor.rgb * (0.86 + 0.24 * smoothstep(0.0, 0.35, fc) - 0.12 * smoothstep(0.75, 1.0, fc));
    tc *= 0.9 + 0.2 * strand;
    float cut = smoothstep(0.58, 0.64, pn(vec2(sc * 0.9 + row * 5.3, row * 1.7))) * (1.0 - smoothstep(0.05, 0.12, abs(fc - 0.25 - 0.12 * sin(sc * 2.2 + row))));
    tc = mix(tc, vec3(0.42, 0.26, 0.1), cut * 0.85);
    diffuseColor.rgb = tc;`,
  // wattle: rods woven over and under stakes, row by row
  wattle: `
    float rowf = vObj.y / 0.075, r = floor(rowf), f = fract(rowf);
    float over = sin((vObj.x / 0.34 + mod(r, 2.0) * 0.5) * 6.2832);
    float rod = sin(f * 3.1416);
    vec3 wc = diffuseColor.rgb * (0.62 + 0.38 * rod * (0.75 + 0.25 * over)) * (0.9 + 0.2 * pn(vec2(r * 3.7, vObj.x * 0.6)));
    diffuseColor.rgb = wc;`,
  // planks, horizontal, with dark joints and a little grain
  plank: `
    float pr = vObj.y / 0.24, pf = fract(pr);
    vec3 pc = diffuseColor.rgb * (0.88 + 0.14 * pn(vec2(floor(pr) * 7.1, sc * 0.4))) * (0.93 + 0.07 * sin(sc * 9.0 + floor(pr) * 4.0));
    pc *= 1.0 - 0.45 * (1.0 - smoothstep(0.0, 0.07, pf)) ;
    diffuseColor.rgb = pc;`,
  plaster: `
    diffuseColor.rgb *= 0.94 + 0.06 * pn(vObj.xy * 1.3 + vObj.z) + 0.04 * pn(vec2(sc * 5.0, vObj.y * 5.0));
    diffuseColor.rgb *= 1.0 - 0.18 * (1.0 - smoothstep(0.0, 0.35, vObj.y));`,
  stone: `
    float sr = vObj.y / 0.24, sfr = fract(sr), scol = fract(sc / 0.42 + floor(sr) * 0.5);
    float joint = (1.0 - smoothstep(0.0, 0.08, sfr)) + (1.0 - smoothstep(0.0, 0.06, scol));
    diffuseColor.rgb *= (0.85 + 0.2 * pn(vec2(floor(sc / 0.42 + floor(sr) * 0.5) * 3.3, floor(sr) * 2.1))) * (1.0 - 0.35 * min(1.0, joint));`,
  clay: `
    diffuseColor.rgb *= 0.93 + 0.1 * pn(vec2(sc * 2.0, vObj.y * 0.7)) - 0.12 * (1.0 - smoothstep(0.0, 0.5, vObj.y));`,
  grain: `diffuseColor.rgb *= 0.9 + 0.18 * pn(vec2(sc * 0.5, vObj.y * 6.0));`,
};

const mats = new Map();
// name -> toon material; `fade` makes it dither away by distance (near, far) from the eye, for level of detail
export function material(name, {fade = null, instanced = false} = {}) {
  const key = name + (fade ? fade.join("/") : "");
  if (mats.has(key)) return mats.get(key);
  const spec = MAT[name] || {color: VCOL[name] ?? 0xcccccc};
  const m = new THREE.MeshToonMaterial({color: spec.color, gradientMap: toonRamp(), side: spec.side ?? THREE.FrontSide,
    emissive: spec.emissive ?? 0, vertexColors: !!spec.vertexColors});
  const pat = PATTERNS[spec.pattern];
  const wind = spec.wind || 0;
  {
    m.customProgramCacheKey = () => "v5-" + key;
    m.onBeforeCompile = sh => {
      Object.assign(sh.uniforms, living, {uWindAmt: {value: wind}, uEye: EYE});
      sh.vertexShader = sh.vertexShader
        .replace("#include <common>", `#include <common>
          uniform float uTime; uniform float uWind; uniform float uWindAmt; uniform vec3 uEye; varying vec3 vObj; varying vec3 vObjN; varying float vFade;`)
        .replace("#include <begin_vertex>", `#include <begin_vertex>
          vec3 sclv = vec3(1.0);
          vec3 base = vec3(0.0);
          #ifdef USE_INSTANCING
            sclv = vec3(length(instanceMatrix[0].xyz), length(instanceMatrix[1].xyz), length(instanceMatrix[2].xyz));
            base = instanceMatrix[3].xyz;
          #endif
          vObj = position * sclv; vObjN = normal;
          ${wind ? `float sway = uWindAmt * uWind * max(0.0, position.y) * position.y;
            transformed.x += sway * sin(uTime * 1.6 + base.x * 0.35 + base.z * 0.2);
            transformed.z += sway * 0.6 * sin(uTime * 2.1 + base.z * 0.4);` : ""}
          vFade = 1.0;
          ${fade ? `vec3 bw = (modelMatrix * vec4(base, 1.0)).xyz;
            vFade = ${fade[2] === "in" ? "" : "1.0 - "}smoothstep(${fade[0].toFixed(1)}, ${fade[1].toFixed(1)}, distance(bw, uEye));
            if (vFade <= 0.0) transformed = vec3(0.0);` : ""}`);
      sh.fragmentShader = sh.fragmentShader
        .replace("#include <common>", `#include <common>
          varying vec3 vObj; varying vec3 vObjN; varying float vFade; uniform float uSnow;
          float ph(vec2 p) { vec3 p3 = fract(vec3(p.xyx) * .1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
          float pn(vec2 p) { vec2 i = floor(p), f = fract(p); f = f * f * (3.0 - 2.0 * f);
            return mix(mix(ph(i), ph(i + vec2(1, 0)), f.x), mix(ph(i + vec2(0, 1)), ph(i + vec2(1, 1)), f.x), f.y); }
          ${DITHER}`)
        .replace("#include <clipping_planes_fragment>", `#include <clipping_planes_fragment>
          ${fade ? "if (vFade < bayer4()) discard;" : ""}`)
        .replace("#include <color_fragment>", `#include <color_fragment>
          float sc = abs(vObjN.z) > 0.6 ? vObj.x : (abs(vObjN.x) > 0.6 ? vObj.z : vObj.x + vObj.z);
          ${pat || ""}
          if (uSnow > 0.0) diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.93, 0.95, 1.0), uSnow * smoothstep(0.35, 0.75, vObjN.y) * (0.75 + 0.25 * pn(vObj.xz * 3.0)));`);
    };
  }
  mats.set(key, m);
  return m;
}
// where the eye is (the main camera; also in the shadow pass, where three's cameraPosition is the light's)
export const EYE = {value: new THREE.Vector3()};
export const LIVING = living;
export const DITHER = `float bayer4() { vec2 p = mod(floor(gl_FragCoord.xy), 4.0);
  int i = int(p.x) + int(p.y) * 4;
  float m[16] = float[16](0.0, 8.0, 2.0, 10.0, 12.0, 4.0, 14.0, 6.0, 3.0, 11.0, 1.0, 9.0, 15.0, 7.0, 13.0, 5.0);
  return (m[i] + 0.5) / 16.0; }`;

const MAT = {
  thatch: {color: VCOL.thatch, pattern: "thatch"}, thatchDark: {color: VCOL.thatchDark, pattern: "thatch"},
  hutThatch: {color: 0xc9a050, pattern: "thatch"},
  wattle: {color: VCOL.wattle, pattern: "wattle"}, plank: {color: VCOL.plank, pattern: "plank"},
  plaster: {color: VCOL.plaster, pattern: "plaster"}, stone: {color: VCOL.stone, pattern: "stone"},
  clay: {color: VCOL.clay, pattern: "clay"}, daub: {color: VCOL.daub, pattern: "clay"},
  timber: {color: VCOL.timber, pattern: "grain"}, dark: {color: VCOL.dark, pattern: "grain"}, post: {color: VCOL.post, pattern: "grain"},
  ember: {color: VCOL.ember, emissive: 0xff7a20}, lantern: {color: VCOL.lantern, emissive: 0xffa040},
  wheat: {color: 0xffffff, vertexColors: true, side: THREE.DoubleSide, wind: 0.05},
  flax: {color: 0xffffff, vertexColors: true, side: THREE.DoubleSide, wind: 0.06},
  reed: {color: 0xffffff, vertexColors: true, side: THREE.DoubleSide, wind: 0.025},
  tree: {color: 0xffffff, vertexColors: true},
};

// ---------- shapes ----------
const box = (w, h, d, x = 0, y = 0, z = 0) => { const g = new THREE.BoxGeometry(w, h, d); g.translate(x, y + h / 2, z); return g; };
const cyl = (r1, r2, h, x = 0, y = 0, z = 0, n = 8) => { const g = new THREE.CylinderGeometry(r1, r2, h, n); g.translate(x, y + h / 2, z); return g; };
const flat = gs => mergeGeometries(gs.map(g => { const y = g.index ? g.toNonIndexed() : g; if (y.attributes.uv) y.deleteAttribute("uv"); return y; }));
// a board between two points (in the x-y plane at depth z), w wide, t thick
function board(x0, y0, x1, y1, z, w, t) {
  const L = Math.hypot(x1 - x0, y1 - y0), g = new THREE.BoxGeometry(L, w, t);
  g.rotateZ(Math.atan2(y1 - y0, x1 - x0)); g.translate((x0 + x1) / 2, (y0 + y1) / 2, z);
  return g;
}

// a thick thatched gable roof over walls `w` wide and `d` long (ridge along z), its eaves at `eave`, rising at `pitch`
// degrees, swelling a little, its ridge rounded, its edges soft. Returns the roof and where its ridge stands.
export function thatchRoof({w, d, eave, pitch = 52, over = 0.7, gable = 0.5, thick = 0.5, bulge = 0.18}) {
  const p = pitch * Math.PI / 180, a = w / 2 + over, rise = a * Math.tan(p), top = eave + rise;
  const outer = [], n = 6;
  for (let k = 0; k <= n; k++) {                    // left eave to ridge, swelling outward in the middle
    const f = k / n, x = -a + a * f, y = eave + rise * f, b = Math.sin(Math.PI * f) * bulge;
    outer.push([x - Math.sin(p) * b, y + Math.cos(p) * b]);
  }
  outer.pop(); outer.push([-0.25, top - 0.05], [0, top + 0.12], [0.25, top - 0.05]);   // the rounded ridge
  for (let k = n - 1; k >= 0; k--) { const [x, y] = outer[k]; outer.push([-x, y]); }
  const inner = outer.map(([x, y], i) => {                 // offset inward by the thickness
    const nx = x < -0.3 ? -Math.sin(p) : x > 0.3 ? Math.sin(p) : 0, ny = x < -0.3 || x > 0.3 ? Math.cos(p) : 1;
    return [x - nx * thick, y - ny * thick * (Math.abs(x) <= 0.3 ? 1.3 : 1)];
  });
  const shape = new THREE.Shape();
  shape.moveTo(...outer[0]);
  for (const q of outer.slice(1)) shape.lineTo(...q);
  for (const q of inner.reverse()) shape.lineTo(...q);
  const depth = d + 2 * gable;
  const g = new THREE.ExtrudeGeometry(shape, {depth, bevelEnabled: true, bevelThickness: 0.22, bevelSize: 0.16, bevelSegments: 2, curveSegments: 3});
  g.translate(0, 0, -depth / 2);
  g.deleteAttribute("uv");
  return {geo: g, top, a, rise, depth, eave, p};
}

// the crossed boards at a gable's peak: along the roof's edges from the eaves, crossing above the ridge
function finials(R, z, ext = 1.1, w = 0.26, t = 0.12) {
  const gs = [];
  for (const s of [-1, 1]) {
    const x0 = s * R.a, y0 = R.eave + 0.25, x1 = 0, y1 = R.top + 0.08, L = Math.hypot(x1 - x0, y1 - y0);
    const ux = (x1 - x0) / L, uy = (y1 - y0) / L;
    gs.push(board(x0, y0, x1 + ux * ext, y1 + uy * ext, z, w, t));
  }
  return gs;
}

// a long house: plastered walls in a timber frame on a low plinth, a deep thatch, boards in the gable, crossed
// finials, the door in the front gable (local +z)
export function longHouse({w = 7, d = 15, wall = 2.1, pitch = 52} = {}) {
  const parts = [];
  parts.push([box(w + 0.4, 0.35, d + 0.4, 0, -0.2), "plinth"]);
  parts.push([box(w, wall, d), "plaster"]);
  const frame = [];
  const nSide = Math.max(2, Math.round(d / 2.6));
  for (let k = 0; k <= nSide; k++) for (const s of [-1, 1]) frame.push(box(0.24, wall, 0.24, s * (w / 2 + 0.02), 0, -d / 2 + d * k / nSide));
  for (const s of [-1, 1]) frame.push(box(0.26, 0.24, d + 0.3, s * (w / 2 + 0.03), wall - 0.24), box(0.26, 0.2, d + 0.3, s * (w / 2 + 0.03), 0));
  for (const s of [-1, 1]) for (const x of [-w / 2, -w / 4, w / 4, w / 2]) frame.push(box(0.24, wall, 0.24, x, 0, s * (d / 2 + 0.02)));
  for (const s of [-1, 1]) frame.push(box(w + 0.3, 0.24, 0.26, 0, wall - 0.24, s * (d / 2 + 0.03)));
  parts.push([flat(frame), "timber"]);
  const R = thatchRoof({w, d, eave: wall - 0.3, pitch, over: 0.75, gable: 0.55, thick: 0.55});
  parts.push([R.geo, "thatch"]);
  // the gable's triangle of boards, set back under the thatch's edge
  const tri = new THREE.Shape(), ty = R.top - 0.75, tx = (ty - wall) / Math.tan(R.p);
  tri.moveTo(-tx - 0.2, wall); tri.lineTo(tx + 0.2, wall); tri.lineTo(0, ty);
  for (const s of [-1, 1]) {
    const g = new THREE.ExtrudeGeometry(tri, {depth: 0.16, bevelEnabled: false}); g.deleteAttribute("uv");
    g.translate(0, 0, s > 0 ? d / 2 + 0.06 : -d / 2 - 0.22);
    parts.push([g, "plank"]);
  }
  const zf = d / 2 + 0.55 + 0.24;
  parts.push([flat([...finials(R, zf), ...finials(R, -zf)]), "timber"]);
  parts.push([cyl(0.32, 0.32, d + 1.3, 0, 0, 0, 10).rotateX(Math.PI / 2).translate(0, R.top - 0.08, 0), "thatchDark"]);
  // the door and its frame, in the front gable
  parts.push([box(1.25, 1.95, 0.1, 0, 0, d / 2 + 0.05), "door"]);
  parts.push([flat([box(0.18, 2.1, 0.2, -0.72, 0, d / 2 + 0.08), box(0.18, 2.1, 0.2, 0.72, 0, d / 2 + 0.08), box(1.7, 0.2, 0.22, 0, 2.0, d / 2 + 0.08)]), "dark"]);
  return {parts, height: R.top, door: [0, d / 2 + 0.3]};
}

// a little store on posts, with a ladder to its door
export function stiltStore({s = 2.6} = {}) {
  const parts = [], lift = 1.25, b = s - 0.35;
  const posts = [];
  for (const x of [-1, 1]) for (const z of [-1, 1]) posts.push(box(0.2, lift, 0.2, x * (b / 2 - 0.05), 0, z * (b / 2 - 0.05)));
  parts.push([flat(posts), "dark"]);
  parts.push([box(s, 0.16, s, 0, lift), "timber"]);
  parts.push([box(b, 1.55, b, 0, lift + 0.16), "plank"]);
  const R = thatchRoof({w: b, d: b, eave: lift + 1.55, pitch: 50, over: 0.35, gable: 0.3, thick: 0.32, bulge: 0.08});
  parts.push([R.geo, "thatch"]);
  const zf = b / 2 + 0.3 + 0.24;
  parts.push([flat([...finials(R, zf, 0.6, 0.18, 0.1), ...finials(R, -zf, 0.6, 0.18, 0.1)]), "timber"]);
  const tri = new THREE.Shape(), ty = R.top - 0.4, tx = (ty - (lift + 1.71)) / Math.tan(R.p);
  tri.moveTo(-tx, lift + 1.71); tri.lineTo(tx, lift + 1.71); tri.lineTo(0, ty);
  const g = new THREE.ExtrudeGeometry(tri, {depth: 0.1, bevelEnabled: false}); g.deleteAttribute("uv"); g.translate(0, 0, b / 2);
  parts.push([g, "plank"]);
  parts.push([box(0.7, 1.1, 0.08, 0, lift + 0.2, b / 2 + 0.04), "door"]);
  // the ladder, leaning from the ground to the door
  const z0 = b / 2 + 1.0, z1 = b / 2 + 0.15;
  const rail = x => { const L = Math.hypot(lift + 0.25, z0 - z1), gg = new THREE.BoxGeometry(0.07, L, 0.07);
    gg.rotateX(Math.atan2(z0 - z1, lift + 0.25)); gg.translate(x, (lift + 0.25) / 2, (z0 + z1) / 2); return gg; };
  const rungs = [];
  for (let k = 1; k <= 4; k++) { const f = k / 5; rungs.push(box(0.5, 0.05, 0.06, 0, f * (lift + 0.25), z0 + (z1 - z0) * f)); }
  parts.push([flat([rail(-0.25), rail(0.25), ...rungs]), "timber"]);
  return {parts, height: R.top};
}

// a stone well with a frame, a beam and a bucket
export function well() {
  const prof = [[0.68, 0], [1.02, 0], [1.08, 0.2], [1.06, 0.72], [0.98, 0.82], [0.72, 0.82], [0.68, 0.7]].map(([x, y]) => new THREE.Vector2(x, y));
  const ring = new THREE.LatheGeometry(prof, 14); ring.deleteAttribute("uv");
  const parts = [[ring, "stone"], [cyl(0.7, 0.7, 0.05, 0, 0.42, 0, 14), "water"]];
  parts.push([flat([box(0.16, 2.1, 0.16, -1.0, 0.2, 0), box(0.16, 2.1, 0.16, 1.0, 0.2, 0), cyl(0.08, 0.08, 2.3, 0, 0, 0, 6).rotateZ(Math.PI / 2).translate(0, 2.05, 0)]), "timber"]);
  parts.push([flat([cyl(0.015, 0.015, 0.9, 0, 1.2, 0, 4)]), "dark"]);
  parts.push([cyl(0.17, 0.14, 0.26, 0, 0.98, 0, 8), "plank"]);
  return {parts, height: 2.3};
}

// a small timber shrine on a stone footing, a lantern by it and bright offerings at its door
export function shrine() {
  const parts = [[box(2.8, 0.35, 2.6), "stone"], [box(1.7, 1.55, 1.5, 0, 0.35), "plank"]];
  const R = thatchRoof({w: 1.7, d: 1.5, eave: 1.75, pitch: 50, over: 0.38, gable: 0.32, thick: 0.28, bulge: 0.06});
  parts.push([R.geo, "thatch"]);
  const zf = 0.75 + 0.32 + 0.24;
  parts.push([flat([...finials(R, zf, 0.55, 0.16, 0.09), ...finials(R, -zf, 0.55, 0.16, 0.09)]), "timber"]);
  parts.push([box(0.8, 1.05, 0.06, 0, 0.4, 0.77), "door"]);
  parts.push([flat([box(0.12, 1.4, 0.12, 1.15, 0.35, 0.95), box(0.5, 0.08, 0.08, 0.95, 1.7, 0.95)]), "dark"]);
  parts.push([box(0.26, 0.32, 0.26, 0.75, 1.32, 0.95), "lantern"]);
  parts.push([flat([new THREE.SphereGeometry(0.13, 8, 6).translate(-0.5, 0.48, 1.05), new THREE.SphereGeometry(0.11, 8, 6).translate(-0.2, 0.46, 1.1)]), "cloth"]);
  parts.push([new THREE.SphereGeometry(0.12, 8, 6).translate(0.25, 0.47, 1.08), "lantern"]);
  return {parts, height: R.top};
}

// a beehive kiln of clay: a swelling dome with its vent on top and its mouth at the front
export function kiln() {
  const prof = [[0.01, 2.95], [0.32, 2.95], [0.36, 2.86], [0.62, 2.72], [1.1, 2.35], [1.5, 1.75], [1.74, 1.05], [1.8, 0.45], [1.72, 0]].reverse()
    .map(([x, y]) => new THREE.Vector2(x, y));
  const dome = new THREE.LatheGeometry(prof, 16); dome.deleteAttribute("uv");
  const vent = new THREE.TorusGeometry(0.3, 0.09, 6, 12); vent.rotateX(Math.PI / 2); vent.translate(0, 2.95, 0);
  const mouth = new THREE.CylinderGeometry(0.42, 0.42, 0.5, 10, 1, false, 0, Math.PI); mouth.rotateZ(Math.PI / 2); mouth.rotateY(Math.PI / 2); mouth.translate(0, 0.62, 1.62);
  const logs = [];
  for (let k = 0; k < 4; k++) logs.push(cyl(0.09, 0.09, 1.0, 0, 0, 0, 6).rotateZ(Math.PI / 2).translate(1.9 + (k % 2) * 0.05, 0.1 + Math.floor(k / 2) * 0.17, 0.9 + (k % 2) * 0.19 - Math.floor(k / 2) * 0.1));
  return {parts: [[flat([dome, vent]), "clay"], [flat([mouth, box(0.84, 0.62, 0.5, 0, 0, 1.62)]), "door"], [flat(logs), "timber"]], height: 3, smoke: [0, 3.0, 0]};
}

export function graveStone() {
  const s = new THREE.Shape();
  s.moveTo(-0.4, 0); s.lineTo(0.4, 0); s.lineTo(0.4, 0.7); s.absarc(0, 0.7, 0.4, 0, Math.PI, false); s.lineTo(-0.4, 0);
  const g = new THREE.ExtrudeGeometry(s, {depth: 0.24, bevelEnabled: true, bevelThickness: 0.06, bevelSize: 0.06, bevelSegments: 2, curveSegments: 6});
  g.translate(0, -0.15, -0.12); g.deleteAttribute("uv");
  return {parts: [[g, "grave"]], height: 1.1};
}

// a bridge of planks on two stringers and posts, its length along local z
export function plankBridge({w = 3, len = 13} = {}) {
  const planks = [], n = Math.round(len / 0.42);
  for (let k = 0; k < n; k++) {
    const z = -len / 2 + (k + 0.5) * len / n, j = Math.sin(k * 12.9898) * 0.06;
    planks.push(box(w + j, 0.1, len / n - 0.05, j * 0.5, 0, z));
  }
  const frame = [box(0.22, 0.28, len, -w / 2 + 0.35, -0.28), box(0.22, 0.28, len, w / 2 - 0.35, -0.28)];
  const posts = [];
  for (const z of [-len / 2 + 0.3, -len / 6, len / 6, len / 2 - 0.3]) for (const x of [-1, 1]) posts.push(cyl(0.13, 0.15, 2.4, x * (w / 2 + 0.1), -1.8, z, 7));
  return {parts: [[flat(planks), "plank"], [flat(frame), "dark"], [flat(posts), "post"]], height: 0.6};
}

// a conical hut of the forest folk: a low wall of daub and a tall thatch cone
export function conicalHut({r = 2.7} = {}) {
  const prof = [[r + 0.55, 0.85], [r + 0.62, 1.0], [r * 0.55, 3.0], [0.5, 4.6], [0.22, 5.0], [0.01, 5.05]].map(([x, y]) => new THREE.Vector2(x, y));
  const inner = [[0.01, 4.5], [r * 0.5, 2.8], [r + 0.05, 0.85]].map(([x, y]) => new THREE.Vector2(x, y));
  const roof = new THREE.LatheGeometry([...inner, ...prof], 14); roof.deleteAttribute("uv");
  const parts = [[cyl(r, r + 0.1, 1.15, 0, 0, 0, 14), "daub"], [roof, "hutThatch"], [box(0.95, 1.5, 0.3, 0, 0, r - 0.05), "door"]];
  parts.push([flat([cyl(0.05, 0.05, 1.1, -0.2, 4.6, 0, 5).rotateZ(0.3), cyl(0.05, 0.05, 1.1, 0.2, 4.6, 0, 5).rotateZ(-0.3)]), "dark"]);
  return {parts, height: 5.2};
}

export function fire() {
  const ring = [];
  for (let i = 0; i < 9; i++) { const a = i / 9 * Math.PI * 2, g = new THREE.DodecahedronGeometry(0.18, 0); g.translate(Math.cos(a) * 0.75, 0.1, Math.sin(a) * 0.75); ring.push(g); }
  const logs = [0, 1, 2].map(i => cyl(0.08, 0.08, 1.0, 0, 0, 0, 6).rotateZ(Math.PI / 2 - 0.25).rotateY(i * 2.1).translate(0, 0.18, 0));
  const flame = [new THREE.ConeGeometry(0.32, 0.9, 6).translate(0, 0.55, 0), new THREE.ConeGeometry(0.2, 0.6, 5).translate(0.15, 0.4, 0.1)];
  return {parts: [[flat(ring), "stone"], [flat(logs), "bark"], [flat(flame), "ember"]], height: 1, smoke: [0, 1.2, 0]};
}

export function dryingRack() {
  return {parts: [[flat([box(0.12, 1.8, 0.12, -1.3, 0, 0), box(0.12, 1.8, 0.12, 1.3, 0, 0), box(2.9, 0.1, 0.1, 0, 1.7, 0)]), "dark"],
    [flat([box(0.9, 0.9, 0.03, -0.6, 0.75, 0), box(0.8, 1.0, 0.03, 0.55, 0.65, 0)]), "hide"]], height: 1.8};
}

export const BUILD = {long_house: longHouse, stilt_store: stiltStore, well, shrine, kiln, grave_stone: graveStone,
  plank_bridge: plankBridge, conical_hut: conicalHut, fire, drying_rack: dryingRack};
export function buildingParts(kind, b = {}) {
  const f = BUILD[kind] || (() => longHouse({w: 5, d: 7}));
  if (kind === "long_house") return f({w: b.size?.[0] ?? 7, d: b.size?.[1] ?? 15});
  if (kind === "plank_bridge") return f({w: b.size?.[0] ?? 3, len: b.size?.[1] ?? 13});
  return f();
}

// ---------- fences ----------
// a wattle panel one metre long and one high (scaled along x to its length), and its post
export function wattlePanel() { const g = new THREE.BoxGeometry(1, 1.1, 0.16, 1, 1, 1); g.translate(0.5, 0.55, 0); g.deleteAttribute("uv"); return g; }
export function fencePost() {
  const g = flat([new THREE.CylinderGeometry(0.1, 0.11, 1.3, 6).translate(0, 0.65, 0), new THREE.SphereGeometry(0.1, 6, 4, 0, Math.PI * 2, 0, Math.PI / 2).translate(0, 1.3, 0)]);
  g.computeVertexNormals(); return g;
}

// ---------- plants (vertex-coloured, instanced) ----------
function coloured(g, c) {
  const n = g.attributes.position.count, col = new Float32Array(n * 3), cc = new THREE.Color(c);
  for (let i = 0; i < n; i++) { col[i * 3] = cc.r; col[i * 3 + 1] = cc.g; col[i * 3 + 2] = cc.b; }
  g.setAttribute("color", new THREE.BufferAttribute(col, 3));
  return g;
}
// a blade: a thin triangle from the ground, leaning, with colours from root to tip; normals up and out (soft light)
function blade(x, z, h, w, yaw, lean, c0, c1, gs) {
  const ca = new THREE.Color(c0), cb = new THREE.Color(c1);
  const dx = Math.cos(yaw) * w / 2, dz = Math.sin(yaw) * w / 2, tx = Math.sin(yaw) * lean, tz = -Math.cos(yaw) * lean;
  const pos = [x - dx, 0, z - dz, x + dx, 0, z + dz, x + tx, h, z + tz];
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("normal", new THREE.Float32BufferAttribute([x * 0.6, 1, z * 0.6, x * 0.6, 1, z * 0.6, x * 0.3, 1, z * 0.3].map((v, i) => i % 3 === 1 ? 1 : v), 3));
  g.setAttribute("color", new THREE.Float32BufferAttribute([ca.r, ca.g, ca.b, ca.r, ca.g, ca.b, cb.r, cb.g, cb.b], 3));
  gs.push(g);
  return [x + tx, h, z + tz];
}
// an ear (or a flower, a seed head): a small diamond facing two ways at a point
function ear(x, y, z, w, h, c0, c1, yaw, gs) {
  const ca = new THREE.Color(c0), cb = new THREE.Color(c1);
  for (const yy of [yaw, yaw + Math.PI / 2]) {
    const dx = Math.cos(yy) * w / 2, dz = Math.sin(yy) * w / 2;
    const pos = [x, y, z, x + dx, y + h * 0.45, z + dz, x, y + h, z, x, y, z, x, y + h, z, x - dx, y + h * 0.45, z - dz];
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute("normal", new THREE.Float32BufferAttribute([0, 1, 0.3, 0.3, 1, 0, 0, 1, 0, 0, 1, 0.3, 0, 1, 0, -0.3, 1, 0], 3));
    g.setAttribute("color", new THREE.Float32BufferAttribute([ca.r, ca.g, ca.b, cb.r, cb.g, cb.b, cb.r, cb.g, cb.b, ca.r, ca.g, ca.b, cb.r, cb.g, cb.b, cb.r, cb.g, cb.b], 3));
    gs.push(g);
  }
}
const rnd = seed => { let a = seed >>> 0; return () => { a = (a + 0x6D2B79F5) >>> 0; let t = a; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; }; };

// a tuft of wheat about a metre across: golden stalks crowned with ears
export function wheatTuft(n = 11, seed = 1) {
  const r = rnd(seed), gs = [];
  for (let k = 0; k < n; k++) {
    const a = r() * Math.PI * 2, d = Math.sqrt(r()) * 0.5, x = Math.cos(a) * d, z = Math.sin(a) * d, h = 0.85 + r() * 0.3, yaw = r() * 3.14;
    const [tx, ty, tz] = blade(x, z, h, 0.05, yaw, 0.04 + r() * 0.08, 0x9a7a30, 0xd8a840, gs);
    ear(tx, ty - 0.04, tz, 0.075, 0.26, 0xe8b444, 0xf8dc88, yaw, gs);
  }
  return flat(gs);
}
// flax: slender green stems, small blue flowers on some
export function flaxTuft(n = 12, seed = 2) {
  const r = rnd(seed), gs = [];
  for (let k = 0; k < n; k++) {
    const a = r() * Math.PI * 2, d = Math.sqrt(r()) * 0.45, x = Math.cos(a) * d, z = Math.sin(a) * d, h = 0.6 + r() * 0.25, yaw = r() * 3.14;
    const [tx, ty, tz] = blade(x, z, h, 0.06, yaw, 0.05 + r() * 0.06, 0x3f6e2a, 0x7aa64a, gs);
    if (r() < 0.45) ear(tx, ty - 0.02, tz, 0.11, 0.08, 0x8ab0f0, 0x5f86e0, yaw, gs);
  }
  return flat(gs);
}
// reeds and cattails at the water's edge
export function reedClump(seed = 3) {
  const r = rnd(seed), gs = [];
  for (let k = 0; k < 16; k++) {
    const a = r() * Math.PI * 2, d = Math.sqrt(r()) * 0.55;
    blade(Math.cos(a) * d, Math.sin(a) * d, 0.9 + r() * 0.9, 0.14, a + 1.2, 0.15 + r() * 0.35, 0x7d9a3a, 0xd6c060, gs);
  }
  for (let k = 0; k < 4; k++) {
    const x = (r() - 0.5) * 0.6, z = (r() - 0.5) * 0.6, h = 1.5 + r() * 0.5;
    const [tx, ty, tz] = blade(x, z, h, 0.04, r() * 3, 0.05, 0x7a9040, 0x8aa048, gs);
    ear(tx, ty - 0.45, tz, 0.11, 0.38, 0x6a3a1e, 0x7a4626, r() * 3, gs);
  }
  return flat(gs);
}

// trees in metres: a broadleaf (soft round crowns) and a conifer (stacked cones), vertex-coloured trunk and leaves
export function broadleaf(seed = 4) {
  const r = rnd(seed), trunk = coloured(new THREE.CylinderGeometry(0.22, 0.34, 4.2, 6).translate(0, 2.1, 0), 0x6e4c30);
  const blobs = [];
  const parts = [[0, 5.6, 0, 2.9], [1.5, 4.9, 0.6, 2.1], [-1.4, 5.0, -0.5, 2.2], [0.3, 6.9, -0.2, 2.0], [-0.4, 5.2, 1.4, 1.8]];
  for (const [x, y, z, s] of parts) blobs.push(new THREE.IcosahedronGeometry(s * (0.9 + r() * 0.2), 1).translate(x, y, z));
  let crown = mergeGeometries(blobs); crown.deleteAttribute("normal"); crown.deleteAttribute("uv"); crown = mergeVertices(crown, 0.01); crown.computeVertexNormals();
  crown = crown.toNonIndexed();
  // a little light on the upper side of the crown, shade below, baked in the colour
  const p = crown.attributes.position, col = new Float32Array(p.count * 3), c = new THREE.Color();
  for (let i = 0; i < p.count; i++) { const t = Math.min(1, Math.max(0, (p.getY(i) - 3.2) / 5)); c.setHex(0x4f7f2e).lerp(new THREE.Color(0x8fb44a), t);
    col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b; }
  crown.setAttribute("color", new THREE.BufferAttribute(col, 3));
  return flat([trunk.toNonIndexed(), crown]);
}
export function conifer() {
  const trunk = coloured(new THREE.CylinderGeometry(0.18, 0.28, 3, 6).translate(0, 1.5, 0), 0x5e4030);
  const cones = [[3.0, 4.6, 3.6], [2.4, 4.0, 6.0], [1.7, 3.4, 8.2], [1.0, 2.4, 10.0]].map(([rr, h, y], k) =>
    coloured(new THREE.ConeGeometry(rr, h, 8).translate(0, y, 0), [0x2f5a32, 0x386a38, 0x40743c, 0x4a7e40][k]));
  return flat([trunk, ...cones].map(g => g.index ? g.toNonIndexed() : g));
}
export const TREE_HEIGHT = {broadleaf: 8.5, conifer: 11.2};
