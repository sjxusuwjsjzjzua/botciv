// Buildings, generated from a few pieces (walls, roofs, domes, posts, fences...). Each kind is a list of
// parts [geometry, colour name]; one tile is x, z in [-0.5, 0.5]. Kinds not listed take their role's look,
// and anything unknown a small shed: new kinds in the engine always appear as something fitting.
import * as THREE from "three";
import {mergeGeometries} from "three/addons/BufferGeometryUtils.min.js";

export const COLORS = {
  thatch: 0xd8b45e, wood: 0x9a6a3e, dark: 0x6e4a2c, plaster: 0xf1e3c4, stone: 0xb9b2a6, brick: 0xb8673f, clay: 0xc98a5a,
  red: 0xb5562f, slate: 0x6f7a86, soil: 0x8a6440, cloth: 0xeee4cf, dye: 0x9a4a6a, metal: 0x8a8f96, gold: 0xe6b84a,
  hide: 0xb08458, leaf: 0x5f9a3c, water: 0x6fb0d0, ember: 0xffb050, flame: 0xff8a2c, black: 0x3a3430,
};

const box = (w, h, d, x = 0, y = 0, z = 0) => { const g = new THREE.BoxGeometry(w, h, d); g.translate(x, y + h / 2, z); return g; };
const cyl = (r1, r2, h, x = 0, y = 0, z = 0, n = 8) => { const g = new THREE.CylinderGeometry(r1, r2, h, n); g.translate(x, y + h / 2, z); return g; };
const cone = (r, h, x = 0, y = 0, z = 0, n = 8) => { const g = new THREE.ConeGeometry(r, h, n); g.translate(x, y + h / 2, z); return g; };
const dome = (r, x = 0, y = 0, z = 0, squash = 1) => { const g = new THREE.SphereGeometry(r, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2); g.scale(1, squash, 1); g.translate(x, y, z); return g; };
const ball = (r, x, y, z) => { const g = new THREE.IcosahedronGeometry(r, 0); g.translate(x, y, z); return g; };

// a gable roof over w x d, starting at height y, rising h (ridge along x), with a little overhang
function gable(w, d, h, y) {
  const o = 0.06, W = w / 2 + o, D = d / 2 + o;
  const v = new Float32Array([
    -W, y, -D, W, y, -D, W, y + h, 0, -W, y, -D, W, y + h, 0, -W, y + h, 0,     // front slope
    -W, y, D, -W, y + h, 0, W, y + h, 0, -W, y, D, W, y + h, 0, W, y, D,         // back slope
    -W, y, -D, -W, y + h, 0, -W, y, D, W, y, -D, W, y, D, W, y + h, 0,           // gable ends
  ]);
  // each triangle's corners in the other order, so the faces (and their light) look outward
  for (let i = 0; i < v.length; i += 9) for (let j = 0; j < 3; j++) { const a = v[i + 3 + j]; v[i + 3 + j] = v[i + 6 + j]; v[i + 6 + j] = a; }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(v, 3));
  g.computeVertexNormals();
  return g;
}
const posts = (n, r, h, color = "wood") => {
  const gs = [];
  for (let i = 0; i < n; i++) { const a = i / n * Math.PI * 2; gs.push(cyl(0.025, 0.03, h, Math.cos(a) * r, 0, Math.sin(a) * r, 5)); }
  return [mergeGeometries(gs), color];
};
function fence(r = 0.46) {
  const gs = [];
  for (let i = 0; i < 12; i++) {
    const a = i / 12 * Math.PI * 2, x = Math.cos(a) * r, z = Math.sin(a) * r;
    gs.push(cyl(0.018, 0.02, 0.22, x, 0, z, 4));
    const rail = new THREE.BoxGeometry(0.02, 0.02, 2 * r * Math.sin(Math.PI / 12) + 0.02);
    rail.rotateY(-a); rail.translate(Math.cos(a + Math.PI / 12) * r * 0.97, 0.15, Math.sin(a + Math.PI / 12) * r * 0.97);
    gs.push(rail);
  }
  return mergeGeometries(gs.map(g => (g.index ? g.toNonIndexed() : g)));
}

// the kit: kind -> parts
const cottage = (wall, roof, s = 1) => [[box(0.6 * s, 0.34 * s, 0.5 * s), wall], [gable(0.6 * s, 0.5 * s, 0.26 * s, 0.34 * s), roof],
  [box(0.11, 0.2, 0.02, 0.05, 0, 0.25 * s + 0.005), "dark"], [box(0.08, 0.08, 0.02, -0.17 * s, 0.17, 0.25 * s + 0.005), "ember"]];
const shed = (roof = "thatch") => [[box(0.6, 0.04, 0.5), "dark"], posts(4, 0.33, 0.32), [gable(0.68, 0.56, 0.18, 0.32), roof], [box(0.3, 0.08, 0.14, 0, 0.04, 0.05), "wood"]];
const kilnLike = (c, r = 0.26, chimney = 0.18) => [[dome(r, 0, 0, 0, 1.1), c], [cyl(0.05, 0.06, chimney, r * 0.3, r * 0.9, 0, 6), c], [box(0.1, 0.1, 0.02, 0, 0, r - 0.01), "black"]];

export const KIT = {
  shelter: () => [[gable(0.62, 0.62, 0.42, 0), "thatch"], [box(0.12, 0.2, 0.02, 0, 0, 0.3), "dark"], posts(2, 0.3, 0.46, "wood")],
  house: () => cottage("plaster", "thatch"),
  brick_house: () => cottage("brick", "red", 1.1),
  stone_house: () => cottage("stone", "slate", 1.15),
  store: () => [[box(0.46, 0.3, 0.4), "wood"], [gable(0.46, 0.4, 0.16, 0.3), "thatch"], [cyl(0.07, 0.07, 0.14, 0.27, 0, 0.12), "dark"]],
  granary: () => [posts(4, 0.2, 0.14, "dark"), [cyl(0.22, 0.22, 0.26, 0, 0.14, 0, 10), "clay"], [cone(0.3, 0.24, 0, 0.4, 0, 10), "thatch"]],
  fire: () => { const ring = []; for (let i = 0; i < 7; i++) { const a = i / 7 * Math.PI * 2; ring.push(ball(0.05, Math.cos(a) * 0.14, 0.03, Math.sin(a) * 0.14)); }
    return [[mergeGeometries(ring), "stone"], [cone(0.07, 0.2, 0, 0.02, 0, 6), "flame"], [cone(0.04, 0.12, 0, 0.02, 0, 5), "ember"]]; },
  drying_rack: () => [posts(4, 0.22, 0.34, "wood"), [box(0.4, 0.02, 0.02, 0, 0.32, 0), "wood"], [box(0.34, 0.12, 0.01, 0, 0.18, 0), "hide"]],
  grave: () => [[dome(0.2, 0, 0, 0, 0.45), "soil"], [box(0.1, 0.18, 0.04, 0, 0, -0.18), "stone"]],
  cairn: () => { const gs = []; [[0.16, 0], [0.12, 0.1], [0.09, 0.19], [0.06, 0.26]].forEach(([r, y]) => gs.push(ball(r, 0, y + r * 0.6, 0))); return [[mergeGeometries(gs), "stone"]]; },
  farm: () => [[box(0.9, 0.03, 0.9), "soil"]],
  pen: () => [[fence(), "wood"]],
  kiln: () => kilnLike("clay"),
  oven: () => kilnLike("clay", 0.2, 0.12),
  furnace: () => kilnLike("brick", 0.28, 0.3),
  bloomery: () => [[cyl(0.18, 0.24, 0.42, 0, 0, 0, 8), "clay"], [box(0.1, 0.1, 0.02, 0, 0.02, 0.22), "black"]],
  lime_kiln: () => [[cyl(0.26, 0.3, 0.3, 0, 0, 0, 10), "stone"], [cyl(0.16, 0.16, 0.06, 0, 0.3, 0, 10), "black"]],
  glassworks: () => [...kilnLike("brick", 0.22, 0.24), [box(0.3, 0.2, 0.2, 0.2, 0, -0.18), "wood"]],
  loom: () => [posts(4, 0.2, 0.36), [box(0.34, 0.24, 0.01, 0, 0.08, 0), "cloth"], [box(0.4, 0.02, 0.04, 0, 0.34, 0), "wood"]],
  tannery: () => [...shed(), [cyl(0.1, 0.1, 0.1, -0.22, 0, 0.22), "dark"], [box(0.2, 0.15, 0.01, 0.2, 0.08, 0.22), "hide"]],
  brewhouse: () => [...cottage("wood", "thatch"), [cyl(0.07, 0.07, 0.14, 0.3, 0, 0.2), "dark"], [cyl(0.07, 0.07, 0.14, 0.3, 0, 0.05), "dark"]],
  workshop: () => shed(),
  smithy: () => [...shed("slate"), [box(0.12, 0.08, 0.06, -0.1, 0.12, 0.05), "metal"], [cyl(0.06, 0.08, 0.3, 0.22, 0.3, -0.18, 6), "stone"]],
  scribe_house: () => [...cottage("plaster", "red"), [box(0.02, 0.18, 0.12, 0.31, 0.18, 0), "dye"]],
  scriptorium: () => [...cottage("stone", "red", 1.1), [box(0.02, 0.18, 0.12, 0.34, 0.18, 0), "dye"]],
  palisade: () => { const gs = []; for (let i = 0; i < 7; i++) gs.push(cone(0.04, 0.12, -0.42 + i * 0.14, 0.38, 0, 5), cyl(0.04, 0.04, 0.38, -0.42 + i * 0.14, 0, 0, 5));
    return [[mergeGeometries(gs.map(g => (g.index ? g.toNonIndexed() : g))), "wood"]]; },
  stone_wall: () => [[box(1, 0.36, 0.2), "stone"], [box(1, 0.05, 0.24, 0, 0.36, 0), "slate"]],
  gatehouse: () => [[box(0.28, 0.6, 0.3, -0.33, 0, 0), "stone"], [box(0.28, 0.6, 0.3, 0.33, 0, 0), "stone"], [box(0.94, 0.14, 0.3, 0, 0.46, 0), "stone"]],
  tower: () => [[cyl(0.2, 0.24, 0.9, 0, 0, 0, 10), "stone"], [cone(0.27, 0.3, 0, 0.9, 0, 10), "slate"]],
  shrine: () => [posts(4, 0.18, 0.3, "wood"), [cone(0.3, 0.2, 0, 0.3, 0, 4), "thatch"], [box(0.14, 0.12, 0.1), "stone"]],
  temple: () => { const cols = []; for (let i = 0; i < 6; i++) cols.push(cyl(0.035, 0.035, 0.4, -0.3 + i * 0.12, 0.06, 0.2, 8), cyl(0.035, 0.035, 0.4, -0.3 + i * 0.12, 0.06, -0.2, 8));
    return [[box(0.84, 0.06, 0.56), "stone"], [mergeGeometries(cols), "plaster"], [gable(0.84, 0.56, 0.2, 0.46), "red"]]; },
  hall: () => [[box(0.86, 0.36, 0.5), "wood"], [gable(0.86, 0.5, 0.3, 0.36), "thatch"], [box(0.14, 0.22, 0.02, 0, 0, 0.255), "dark"], [box(0.02, 0.2, 0.14, 0.44, 0.24, 0), "dye"]],
  market: () => { const parts = []; [[-0.22, "red"], [0.22, "cloth"]].forEach(([x, c]) => { parts.push(posts(4, 0.13, 0.28)); parts[parts.length - 1][0].translate(x, 0, 0);
    const aw = gable(0.3, 0.3, 0.08, 0.28); aw.translate(x, 0, 0); parts.push([aw, c]); }); parts.push([box(0.7, 0.1, 0.16, 0, 0, 0.05), "wood"]); return parts; },
  school: () => [...cottage("stone", "red", 1.25), [cyl(0.03, 0.03, 0.2, 0.3, 0.55, 0, 5), "dark"]],
  library: () => [[box(0.8, 0.42, 0.56), "stone"], [gable(0.8, 0.56, 0.24, 0.42), "slate"], [box(0.16, 0.26, 0.02, 0, 0, 0.285), "dark"]],
  infirmary: () => [...cottage("plaster", "thatch", 1.15), [box(0.12, 0.12, 0.02, 0.18, 0.2, 0.29), "cloth"]],
  observatory: () => [[cyl(0.22, 0.24, 0.5, 0, 0, 0, 10), "stone"], [dome(0.24, 0, 0.5, 0), "metal"]],
  dock: () => [posts(4, 0.3, 0.16, "dark"), [box(0.8, 0.04, 0.5, 0, 0.16, 0), "wood"]],
  shipyard: () => [posts(4, 0.34, 0.16, "dark"), [box(0.9, 0.04, 0.6, 0, 0.16, 0), "wood"], [cyl(0.1, 0.02, 0.5, 0, 0.2, 0, 6).rotateZ(Math.PI / 2), "dark"]],
  mill: () => [...cottage("stone", "thatch"), [box(0.04, 0.7, 0.06, 0, 0.35, 0.3), "wood"], [box(0.7, 0.04, 0.06, 0, 0.7, 0.3), "wood"]],
  bridge: () => [[box(1, 0.05, 0.5, 0, 0.12, 0), "wood"], posts(4, 0.4, 0.14, "dark")],
  aqueduct: () => [[box(0.24, 0.6, 0.3, -0.35, 0, 0), "stone"], [box(0.24, 0.6, 0.3, 0.35, 0, 0), "stone"], [box(1, 0.14, 0.3, 0, 0.6, 0), "stone"], [box(1, 0.03, 0.16, 0, 0.74, 0), "water"]],
  stables: () => [...shed(), [fence(0.45), "wood"]],
  road: () => [],
};
// by role, for kinds not in the kit
const ROLE = {shelter: "house", store: "store", workshop: "workshop", hearth: "fire", monument: "cairn", gathering: "hall",
  wall: "stone_wall", pen: "pen", farm: "farm", dock: "dock", lookout: "tower", school: "school", library: "library", market: "market"};
// a building going up: a frame of poles
export const SCAFFOLD = () => [posts(6, 0.3, 0.4, "wood"), [box(0.62, 0.02, 0.62, 0, 0.4, 0), "wood"], [box(0.5, 0.05, 0.5), "soil"]];

export function parts(kind, roles = []) {
  const make = KIT[kind] || KIT[ROLE[roles.find(r => ROLE[r])]] || KIT.workshop;
  return make();
}
