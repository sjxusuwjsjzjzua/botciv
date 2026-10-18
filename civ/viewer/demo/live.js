// world5's viewer of a whole towns world (towns_spec §9, WP5): one seamless land in metres, from the whole land seen
// from 400 km up down to a person at their door, with no zones and no mode switch; detail by distance only. Streamed
// about what is looked at: the land's colour in three maps (the whole land, 48 km and 8 km about the eye, painted by
// a worker), the land's shape by the quadtree, trees in 500 m blocks, every settlement drawn when one comes near and
// let go when far, rivers and lakes in 8 km pieces. The people move hour by hour as the log has them (civ/site5.py
// writes live/), through the day and the night.
//   ?src=<dir>   where land.json and hours.json lie (default live/)
//   ?site=<id>   start over this settlement; ?cam=x,z,dist,pitch,yaw any view; ?h=<hour> start at this hour
//   ?debug=1     frames a second and what is drawn; ?tier=phone|high
import * as THREE from "three";
import {LandTiles} from "./tiles.js";
import {Terrain, mapTexture} from "./terrain.js";
import {Town, paintDetail} from "./town.js";
import {StreamFlora} from "./flora.js";
import {Folk} from "./folk.js";
import {Rig, Path} from "./camera.js";
import {Post} from "./post.js";
import {Curve} from "./land.js";
import {ribbon, waterMaterial} from "./water.js";
import {living} from "../art/toon.js";
import {EYE, material} from "../art/village.js";
import {looksOf} from "../scene/people.js";

const Q = new URLSearchParams(location.search);
const phone = Q.get("tier") === "phone" || (Q.get("tier") !== "high" && Math.min(innerWidth, innerHeight) < 600);
const $ = id => document.getElementById(id);
const say = t => { const el = $("load"); if (el) el.textContent = t; };
const smoothstep = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
const tick = () => new Promise(r => setTimeout(r, 0));
const SRC = (Q.get("src") || "live").replace(/[^a-zA-Z0-9_./-]/g, "");
const PART = ["dawn", "dawn", "morning", "morning", "morning", "afternoon", "afternoon", "afternoon", "evening", "night", "night", "night"];
const HOLDS = {gather: "basket", craft: "hammer", fish: "rod", build: "hammer", plant: "basket"};

// ---------- the painter: the land's colour maps, made in a worker ----------
class Painter {
  constructor(land) {
    this.w = new Worker(new URL("./paint.js", import.meta.url), {type: "module"});
    this.w.postMessage({land});
    this.n = 0; this.wait = new Map();
    this.w.onmessage = e => { const r = this.wait.get(e.data.id); this.wait.delete(e.data.id); r(e.data); };
  }
  paint(box, size, water = true) {
    const id = ++this.n;
    return new Promise(r => { this.wait.set(id, r); this.w.postMessage({id, box, size, water}); });
  }
}

// a map that follows the eye: repainted about it when it has gone `move` from the last middle
class Follow {
  constructor(painter, terrain, name, span, px, move) {
    Object.assign(this, {painter, terrain, name, span, px, move, at: null, busy: false});
  }
  async update(x, z, alt) {
    if (this.busy || alt > this.span * 1.2) return;
    if (this.at && Math.hypot(x - this.at[0], z - this.at[1]) < this.move) return;
    this.busy = true;
    const box = [x - this.span / 2, z - this.span / 2, this.span, this.span];
    const r = await this.painter.paint(box, [this.px, this.px]);
    this.terrain.setMap(this.name, {tex: mapTexture(r.data, r.w, r.h), box});
    this.at = [x, z]; this.busy = false;
  }
}

// ---------- water: rivers as ribbons and lakes as sheets, in 8 km pieces about the eye ----------
const WP = 8000;
class Waters {
  constructor(scene, land, light) {
    Object.assign(this, {scene, land, pieces: new Map(), mat: waterMaterial(light.water), sea: waterMaterial(light.water, {bias: 0.0003, sheet: true})});
    // each river's segments by the piece holding their middle, as runs of distance along it (pieces meet exactly)
    this.runs = new Map();
    land.rivers.forEach(rv => {
      let cur = null;
      for (let k = 0; k < rv.p.length - 1; k++) {
        const key = this.key(Math.floor((rv.p[k][0] + rv.p[k + 1][0]) / 2 / WP), Math.floor((rv.p[k][1] + rv.p[k + 1][1]) / 2 / WP));
        if (cur && cur.key === key) { cur.to = rv.s[k + 1]; continue; }
        cur = {key, rv, from: rv.s[k], to: rv.s[k + 1]};
        (this.runs.get(key) || this.runs.set(key, []).get(key)).push(cur);
      }
    });
  }
  key(i, j) { return i * 10000 + j; }
  piece(i, j) {
    const L = this.land, g = new THREE.Group();
    for (const r of this.runs.get(this.key(i, j)) || []) {
      const m = new THREE.Mesh(ribbon(r.rv, {step: 8, cols: 7, y: () => L.W, from: r.from, to: r.to}), this.mat);
      m.renderOrder = 2; g.add(m);
    }
    // the sheet over broad water, as Town.ways lays it, on this piece's cells
    const c = 125, n = WP / c, x0 = i * WP, y0 = j * WP, wet = new Float32Array((n + 1) * (n + 1));
    let any = false;
    for (let b = 0; b <= n; b++) for (let a = 0; a <= n; a++) { const v = L.broad(x0 + a * c, y0 + b * c); wet[b * (n + 1) + a] = v; any = any || v > 0.12; }
    if (any) {
      const pos = [], uv = [];
      for (let b = 0; b < n; b++) for (let a = 0; a < n; a++) {
        let m = 0;
        for (let db = -1; db <= 2; db++) for (let da = -1; da <= 2; da++) m = Math.max(m, wet[Math.min(n, Math.max(0, b + db)) * (n + 1) + Math.min(n, Math.max(0, a + da))]);
        if (m < 0.12) continue;
        for (const [da, db] of [[0, 0], [0, 1], [1, 0], [1, 0], [0, 1], [1, 1]]) {
          const w = wet[(b + db) * (n + 1) + a + da];
          pos.push(x0 + (a + da) * c, L.W, y0 + (b + db) * c); uv.push(x0 + (a + da) * c, 1.04 - 0.6 * Math.min(1, Math.max(0, (w - 0.36) / 0.26)));
        }
      }
      if (pos.length) {
        const geo = new THREE.BufferGeometry();
        geo.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
        geo.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
        geo.computeBoundingSphere();
        const m = new THREE.Mesh(geo, this.sea); m.renderOrder = 2; g.add(m);
      }
    }
    this.scene.add(g);
    return g;
  }
  update(at, alt, ms = 6) {
    const R = alt > 9000 ? 0 : 15000, i0 = Math.floor(at.x / WP), j0 = Math.floor(at.z / WP), t0 = performance.now();
    for (const [k, g] of this.pieces) {
      const i = Math.floor(k / 10000), j = k % 10000;
      if (Math.hypot((i + 0.5) * WP - at.x, (j + 0.5) * WP - at.z) > R + 9000) { this.scene.remove(g); g.traverse(o => o.geometry?.dispose()); this.pieces.delete(k); }
    }
    const want = [];
    for (let j = j0 - 3; j <= j0 + 3; j++) for (let i = i0 - 3; i <= i0 + 3; i++) {
      const d = Math.hypot((i + 0.5) * WP - at.x, (j + 0.5) * WP - at.z);
      if (i >= 0 && j >= 0 && d < R && !this.pieces.has(this.key(i, j))) want.push([d, i, j]);
    }
    want.sort((a, b) => a[0] - b[0]);
    for (const [, i, j] of want) { if (performance.now() - t0 > ms) break; this.pieces.set(this.key(i, j), this.piece(i, j)); }
  }
}

// ---------- the people, hour by hour ----------
class LiveFolk extends Folk {
  constructor(scene, land, H) {
    const ids = Object.keys(H.people).map(Number).sort((a, b) => a - b);
    const people = ids.map((pid, i) => ({id: i, pid, age: H.people[pid][1], name: H.people[pid][0], pos: [0, 0], verb: "rest", speed: 1.3}));
    super(scene, land, {people, animals: [], walker: -1});
    this.all = people;
    this.looks = people.map(p => ({...looksOf({id: p.pid, parents: H.people[p.pid][2] || []}), shirt: this.looks[p.id].shirt}));
    const at = new Map(ids.map((pid, i) => [pid, i]));
    this.hours = H.hours.map(h => h[0]);
    this.t0 = this.hours[0]; this.T = this.hours.length;
    // where each stood each hour (NaN indoors or not yet born) and what they did
    this.X = new Float32Array(people.length * this.T).fill(NaN); this.Y = new Float32Array(people.length * this.T).fill(NaN);
    this.V = new Array(people.length * this.T).fill("rest");
    H.hours.forEach(([, rows], k) => { for (const r of rows) { const i = at.get(r[0]); if (i == null || r.length < 4) continue;
      this.X[i * this.T + k] = r[1]; this.Y[i * this.T + k] = r[2]; this.V[i * this.T + k] = r[3]; } });
    this.wt = this.t0;
  }
  // where someone is at world time this.wt (hours): walking from the last hour's place to this one's at a walker's pace,
  // then at their work; out of doors from a while after they left home, in again a while after they reached it
  place(p) {
    const T = this.T, k = Math.max(0, Math.min(T - 1, Math.floor(this.wt - this.t0))), f = Math.min(1, Math.max(0, this.wt - this.t0 - k));
    const i = p.id * T, k2 = Math.min(T - 1, k + 1);
    let ax = this.X[i + k], ay = this.Y[i + k], bx = this.X[i + k2], by = this.Y[i + k2];
    const yaw0 = (p.id * 1.7) % 6.28;
    p.verb = this.V[i + (f > 0.5 ? k2 : k)]; p.holds = HOLDS[p.verb];
    if (isNaN(ax) && isNaN(bx)) return null;
    if (isNaN(ax)) return f < 0.15 ? null : {x: bx, y: by, yaw: yaw0, moving: false};
    if (isNaN(bx)) return f > 0.6 ? null : {x: ax, y: ay, yaw: yaw0, moving: false};
    const d = Math.hypot(bx - ax, by - ay);
    if (d < 3) return {x: ax + (bx - ax) * f, y: ay + (by - ay) * f, yaw: yaw0, moving: false};
    const ft = Math.min(0.95, d / 4500), u = Math.min(1, f / ft);
    return {x: ax + (bx - ax) * u, y: ay + (by - ay) * u, yaw: Math.atan2(bx - ax, by - ay), moving: u < 1};
  }
  near(cam, R = 700) {
    const out = [], c = cam.position;
    if (c.y - this.land.height(c.x, c.z) > R) return out;
    for (const p of this.all) {
      const q = this.place(p);
      if (q && Math.abs(q.x - c.x) < R && Math.abs(q.y - c.z) < R) { p.q = q; out.push(p); }
    }
    return out;
  }
  update(t, cam) {
    const near = this.near(cam);
    this.people = near;
    this.count = near.length;
    const place = this.place;
    this.place = p => p.q;
    super.update(t, cam);
    this.place = place;
  }
}

async function main() {
  say("reading the land…");
  const [W, H] = await Promise.all([fetch(`${SRC}/land.json`).then(r => r.json()), fetch(`${SRC}/hours.json`).then(r => r.json())]);
  const land = new LandTiles(W.land);
  const box = W.land.box, levels = Math.max(7, Math.ceil(Math.log2(Math.max(box[2], box[3]) / 125)));
  const root = 125 * 2 ** levels, origin = [box[0] + box[2] / 2 - root / 2, box[1] + box[3] / 2 - root / 2];
  const sites = W.sites, byId = new Map(sites.map(s => [s.id, s]));
  // the tracks between settlements: each drawn with the first of its two, and kept clear of trees
  const tracks = W.tracks.map(t => ({...t, curve: new Curve(t.pts.map(p => [p[0], p[1], t.w]))}));
  const tbins = new Map();
  tracks.forEach(t => { const xs = t.pts.map(p => p[0]), ys = t.pts.map(p => p[1]);
    for (let i = Math.floor(Math.min(...xs) / 1000) - 1; i <= Math.floor(Math.max(...xs) / 1000) + 1; i++)
      for (let j = Math.floor(Math.min(...ys) / 1000) - 1; j <= Math.floor(Math.max(...ys) / 1000) + 1; j++) {
        const k = i * 65536 + j; (tbins.get(k) || tbins.set(k, []).get(k)).push(t.curve); } });
  const nearTrack = (x, y) => (tbins.get(Math.floor(x / 1000) * 65536 + Math.floor(y / 1000)) || []).some(c => c.near(x, y).d < 7);

  const renderer = new THREE.WebGLRenderer({antialias: false, powerPreference: "high-performance", logarithmicDepthBuffer: false});
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.info.autoReset = false;
  document.body.prepend(renderer.domElement);
  const ratio = Math.min(devicePixelRatio || 1, phone ? 1.75 : 2);
  const scene = new THREE.Scene();

  say("painting the land…");
  const painter = new Painter(W.land);
  const farSize = phone ? 512 : 768;
  const far = await painter.paint(box, [farSize, farSize]);
  const farTex = mapTexture(far.data, far.w, far.h);
  const blank = document.createElement("canvas"); blank.width = blank.height = 2;
  const none = {tex: new THREE.CanvasTexture(blank), box: [-1e7, -1e7, 1, 1]};
  const maps = {far: {tex: farTex, box}, mid: {tex: farTex, box}, color: {tex: farTex, box}, detail: none, snow: living.uSnow};

  // the light: the sun's way over the sky through the day, a cool sky, night falling
  const hemi = new THREE.HemisphereLight(0xd8e4ee, 0x8a7a50, 0.85);
  const sun = new THREE.DirectionalLight(0xffdcaa, 2.75);
  sun.castShadow = true;
  sun.shadow.mapSize.set(phone ? 1024 : 2048, phone ? 1024 : 2048);
  sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.04; sun.shadow.radius = 2;
  scene.add(hemi, sun, sun.target);
  scene.fog = new THREE.Fog(0xe9dcc0, 1000, 5000);
  const light = {water: {value: 1}, way: {value: new THREE.Color(1, 1, 1)},
    imp: {uSunV: {value: new THREE.Vector3()}, uSunCol: {value: new THREE.Color()}, uSky: {value: new THREE.Color()}, uGround: {value: new THREE.Color()}}};
  const sunDir = new THREE.Vector3(-0.74, 0.52, 0.42).normalize();
  const skyMat = new THREE.ShaderMaterial({side: THREE.BackSide, depthWrite: false, fog: false,
    uniforms: {uTop: {value: new THREE.Color(0x86b4e0)}, uHor: {value: new THREE.Color(0xf6dfb4)}, uSun: {value: sunDir}, uNight: living.uNight},
    vertexShader: `varying vec3 vD; void main() { vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }`,
    fragmentShader: `uniform vec3 uTop; uniform vec3 uHor; uniform vec3 uSun; uniform float uNight; varying vec3 vD;
      float h(vec3 p) { return fract(sin(dot(p, vec3(12.9898, 78.233, 37.719))) * 43758.5453); }
      void main() { float y = clamp(vD.y, 0.0, 1.0); vec3 c = mix(uHor, uTop, pow(y, 0.55));
        c += vec3(1.0, 0.85, 0.6) * pow(max(0.0, dot(vD, uSun)), 24.0) * 0.5 * (1.0 - uNight);
        c += step(0.9975, h(floor(vD * 220.0))) * smoothstep(0.05, 0.3, vD.y) * uNight;
        gl_FragColor = vec4(c, 1.0);
        #include <colorspace_fragment>
      }`});
  const sky = new THREE.Mesh(new THREE.SphereGeometry(1, 32, 16), skyMat);
  sky.frustumCulled = false; sky.renderOrder = -1;
  scene.add(sky);
  const DAY = {hemi: new THREE.Color(0xd8e4ee), ground: new THREE.Color(0x8a7a50), sun: new THREE.Color(0xffdcaa), top: new THREE.Color(0x86b4e0), hor: new THREE.Color(0xf6dfb4), fog: new THREE.Color(0xe9dcc0)};
  const DUSK = {sun: new THREE.Color(0xffa060), hor: new THREE.Color(0xf0b890)};
  const NIGHT = {hemi: new THREE.Color(0x5a6a9c), ground: new THREE.Color(0x2a2838), sun: new THREE.Color(0x9fb4e8), top: new THREE.Color(0x101a36), hor: new THREE.Color(0x3a4468), fog: new THREE.Color(0x2a3252)};
  const tmp = new THREE.Color();
  // hour h of the 12 (0-1 dawn ... 8 evening, 9-11 night): the sun rises at the start of dawn and sets in the evening
  function daylight(h) {
    const th = Math.PI * (h + 0.3) / 9.4, el = Math.sin(th);
    const night = 1 - smoothstep(-0.12, 0.12, el), dusk = (1 - smoothstep(0.1, 0.45, el)) * (1 - night);
    sunDir.set(Math.cos(th) * 0.85, Math.max(0.12, el) * 0.9, 0.42).normalize();
    living.uNight.value = night;
    hemi.color.copy(DAY.hemi).lerp(NIGHT.hemi, night); hemi.groundColor.copy(DAY.ground).lerp(NIGHT.ground, night);
    hemi.intensity = 0.85 + 0.05 * night;
    sun.color.copy(DAY.sun).lerp(DUSK.sun, dusk).lerp(NIGHT.sun, night); sun.intensity = 2.7 * (1 - night) * (1 - 0.35 * dusk) + 0.55 * night;
    skyMat.uniforms.uTop.value.copy(DAY.top).lerp(NIGHT.top, night);
    skyMat.uniforms.uHor.value.copy(DAY.hor).lerp(DUSK.hor, dusk).lerp(NIGHT.hor, night);
    scene.fog.color.copy(DAY.fog).lerp(tmp.copy(DUSK.hor), dusk * 0.5).lerp(NIGHT.fog, night);
    light.water.value = 1 - 0.65 * night; light.way.value.setScalar(1 - 0.65 * night);
    material("door").emissive.set(night > 0.5 ? 0xc87830 : 0x000000);
    return night;
  }
  living.uSnow.value = W.season === "winter" ? 1 : 0;

  say("raising the land…");
  await tick();
  const terrain = new Terrain(scene, land, {maps, N: phone ? 32 : 40, K: 1.9, origin, levels});
  const near = new Follow(painter, terrain, "color", 8000, phone ? 768 : 1024, 1800);
  const mid = new Follow(painter, terrain, "mid", 48000, phone ? 768 : 1024, 11000);
  const waters = new Waters(scene, land, light);
  const flora = new StreamFlora(scene, land, {light: light.imp, near: phone ? [200, 260] : [300, 380], radius: phone ? 1800 : 2600,
    keepOff: (x, y) => nearTrack(x, y) || !!land.strip(x, y)});
  const folk = new LiveFolk(scene, land, H);
  const rig = new Rig(renderer.domElement, land);
  rig.maxDist = Math.max(box[2], box[3]) * 1.3;
  const post = new Post(renderer, {samples: phone ? 2 : 4});

  // ---------- settlements, drawn when near ----------
  const towns = new Map();          // id -> {town, data, detail} | "loading"
  let detailOf = null;
  async function bringIn(s) {
    towns.set(s.id, "loading");
    const data = await (await fetch(`${SRC}/s/${s.id}.json`)).json();
    data.lanes = data.lanes.concat(tracks.filter(t => t.sites[0] === s.id));
    data.people = []; data.walker = -1;
    const b = s.box, town = new Town(scene, land, data, {tier: phone ? "phone" : "high", light, water: false, lazy: true,
      box: [b[0] - 300, b[1] - 300, b[2] + 300, b[3] + 300]});
    town.winter = W.season === "winter";
    towns.set(s.id, {town, data, s});
    folk.animals = [...towns.values()].filter(t => t.data).flatMap(t => t.data.animals);
  }
  function letGo(id) {
    const t = towns.get(id);
    if (t && t.town) { t.town.dispose(); if (t.detail) t.detail.tex.dispose(); }
    towns.delete(id);
    if (detailOf === id) { terrain.setMap("detail", none); detailOf = null; }
    folk.animals = [...towns.values()].filter(t => t.data).flatMap(t => t.data.animals);
  }
  const distTo = (s, x, z) => Math.hypot(Math.max(s.box[0] - x, 0, x - s.box[2]), Math.max(s.box[1] - z, 0, z - s.box[3]));
  function settle(at, alt) {
    for (const [id, t] of towns) if (t !== "loading" && (distTo(t.s, at.x, at.z) > 9000 || alt > 9000)) letGo(id);
    if (alt < 6000 && ![...towns.values()].includes("loading")) {
      const next = sites.filter(s => !towns.has(s.id) && distTo(s, at.x, at.z) < 5000).sort((a, b) => distTo(a, at.x, at.z) - distTo(b, at.x, at.z))[0];
      if (next) bringIn(next);
    }
    // the fine paint of the ground: the nearest settlement's, within 1.5 km
    let best = null, bd = 1500;
    for (const t of towns.values()) if (t.data) { const d = distTo(t.s, at.x, at.z); if (d < bd) { bd = d; best = t; } }
    if (best && detailOf !== best.s.id) {
      best.detail = best.detail || paintDetail(best.data, best.data.paint, phone ? 3.2 : 4.6);
      terrain.setMap("detail", best.detail); detailOf = best.s.id;
    }
  }

  // ---------- where to look first ----------
  const biggest = [...sites].sort((a, b) => b.living - a.living)[0];
  const first = byId.get(Number(Q.get("site"))) || biggest;
  const startView = s => ({x: s.centre[0] + 10, z: s.centre[1] + 40, dist: 420, pitch: 0.72, yaw: 0.2});
  rig.set(startView(first));
  const cam = (Q.get("cam") || "").split(",").map(Number);
  if (cam.length === 5 && cam.every(Number.isFinite)) rig.set({x: cam[0], z: cam[1], dist: cam[2], pitch: cam[3], yaw: cam[4]});
  rig.apply();
  say("drawing the settlement…");
  await near.update(rig.target.x, rig.target.z, 0);
  await mid.update(rig.target.x, rig.target.z, 0);
  const s0 = sites.filter(s => distTo(s, rig.target.x, rig.target.z) < 5000).sort((a, b) => distTo(a, rig.target.x, rig.target.z) - distTo(b, rig.target.x, rig.target.z))[0];
  if (s0) await bringIn(s0);
  settle(rig.target, 0);
  terrain.warm([rig.cam.position.clone()]);

  // ---------- the clock: world hours, played ----------
  const clock = {wt: folk.t0 + Math.min(folk.T - 1, Math.max(0, Number(Q.get("h") ?? 0))), rate: Q.has("still") ? 0 : 1 / 30};
  const RATES = [[0, "❚❚"], [1 / 30, "▶"], [1 / 8, "▶▶"], [1 / 2, "▶▶▶"]];
  let fly = null;

  // ---------- the panel ----------
  $("name").textContent = W.name || "world5";
  const sel = $("sites");
  for (const s of [...sites].filter(s => s.form !== "homestead").sort((a, b) => b.living - a.living))
    sel.add(new Option(`${s.name} (${s.living})`, s.id));
  const hs = [...sites].filter(s => s.form === "homestead");
  if (hs.length) { const g = document.createElement("optgroup"); g.label = `homesteads (${hs.length})`; for (const s of hs) g.append(new Option(`${s.name} (${s.living})`, s.id)); sel.append(g); }
  sel.value = first.id;
  sel.onchange = () => {
    const s = byId.get(Number(sel.value)), from = {x: rig.target.x, z: rig.target.z, dist: rig.dist, pitch: rig.pitch, yaw: rig.yaw};
    const to = startView(s), d = Math.hypot(to.x - from.x, to.z - from.z), T = 2 + Math.min(6, d / 30000);
    const up = Math.max(from.dist, to.dist, d * 0.6);
    fly = {path: new Path([{t: 0, ...from}, {t: T * 0.5, x: (from.x + to.x) / 2, z: (from.z + to.z) / 2, dist: up, pitch: 0.95, yaw: (from.yaw + to.yaw) / 2}, {t: T, ...to}]), t: 0};
  };
  $("whole").onclick = () => {
    const from = {x: rig.target.x, z: rig.target.z, dist: rig.dist, pitch: rig.pitch, yaw: rig.yaw};
    fly = {path: new Path([{t: 0, ...from}, {t: 4, x: box[0] + box[2] / 2, z: box[1] + box[3] / 2 + box[3] * 0.1, dist: Math.max(box[2], box[3]) * 1.05, pitch: 1.2, yaw: 0}]), t: 0};
  };
  const play = $("play");
  let ri = Q.has("still") ? 0 : 1;
  play.onclick = () => { ri = (ri + 1) % RATES.length; clock.rate = RATES[ri][0]; play.textContent = RATES[ri][1]; };
  play.textContent = RATES[ri][1];
  const scrub = $("scrub");
  scrub.max = String(folk.T - 1); scrub.step = "0.01";
  scrub.oninput = () => { clock.wt = folk.t0 + Number(scrub.value); };

  const dbg = Q.has("debug") ? $("dbg") : null;
  if (dbg) dbg.style.display = "block";
  let Wd = 0, Hd = 0;
  function resize() {
    if (innerWidth === Wd && innerHeight === Hd) return;
    Wd = innerWidth; Hd = innerHeight;
    renderer.setPixelRatio(ratio); renderer.setSize(Wd, Hd);
    post.setSize(Wd, Hd, ratio);
    rig.cam.aspect = Wd / Hd; rig.cam.updateProjectionMatrix();
  }

  let t = 0, last = performance.now(), fpsT = last, fpsN = 0, fps = 0, shown = "";
  function frame(dt, opts = {}) {
    resize();
    t += dt;
    living.uTime.value = t;
    if (fly) { fly.t += dt; rig.set(fly.path.at(fly.t)); if (fly.t >= fly.path.T) fly = null; }
    clock.wt += dt * clock.rate;
    if (clock.wt > folk.t0 + folk.T - 1) clock.wt = folk.t0;          // the newest hour reached: round again
    folk.wt = clock.wt;
    rig.apply();
    const cam = rig.cam;
    cam.updateMatrixWorld();
    EYE.value.copy(cam.position);
    const alt = cam.position.y - land.height(cam.position.x, cam.position.z);
    const night = daylight(clock.wt % W.tpd);
    sky.position.copy(cam.position); sky.scale.setScalar(cam.far * 0.92);
    const D = Math.max(rig.dist, alt);
    scene.fog.near = D * 0.9 + 250; scene.fog.far = D * 4.5 + 2600;
    const span = Math.min(1600, Math.max(22, D * 0.75));
    sun.position.copy(rig.target).addScaledVector(sunDir, span * 2 + 200);
    sun.target.position.copy(rig.target);
    const sc = sun.shadow.camera; sc.left = sc.bottom = -span; sc.right = sc.top = span; sc.near = 1; sc.far = span * 4 + 400; sc.updateProjectionMatrix();
    light.imp.uSunV.value.copy(sunDir).transformDirection(cam.matrixWorldInverse);
    light.imp.uSunCol.value.copy(sun.color).multiplyScalar(sun.intensity);
    light.imp.uSky.value.copy(hemi.color).multiplyScalar(hemi.intensity);
    light.imp.uGround.value.copy(hemi.groundColor).multiplyScalar(hemi.intensity);
    // what is streamed about the point looked at
    terrain.update(cam.position, opts.budget ?? 64, opts.budget ? Infinity : 7);
    near.update(rig.target.x, rig.target.z, alt);
    mid.update(rig.target.x, rig.target.z, alt);
    waters.update(rig.target, alt, opts.budget ? Infinity : 4);
    flora.update(cam.position, rig.target, opts.budget ? 1e9 : 5);
    settle(rig.target, alt);
    for (const tw of towns.values()) if (tw.town) tw.town.update(cam.position);
    folk.update(t, cam);
    renderer.info.reset();
    post.render(scene, cam);
    // the panel's line: when it is, and who is about
    const h = Math.floor(clock.wt) % W.tpd, day = Math.floor(clock.wt / W.tpd) + 1;
    const line = `day ${day}, ${PART[h]} · ${W.season}, year ${W.year}`;
    if (line !== shown) { $("when").textContent = line; shown = line; }
    if (document.activeElement !== scrub) scrub.value = String(clock.wt - folk.t0);
    void night;
  }
  say("");
  $("load")?.remove();
  function loop() {
    const now = performance.now(), dt = Math.min(0.1, (now - last) / 1000);
    last = now;
    frame(dt);
    fpsN++;
    if (now - fpsT > 1000) {
      fps = fpsN * 1000 / (now - fpsT); fpsN = 0; fpsT = now;
      const busy = [...towns.values()].filter(t => t.town).length;
      $("about").textContent = `${folk.count} people near · ${busy} settlement${busy === 1 ? "" : "s"} drawn`;
    }
    if (dbg) dbg.textContent = `${fps.toFixed(0)} fps · ${renderer.info.render.calls} draws · ${(renderer.info.render.triangles / 1e6).toFixed(2)} M tris · ` +
      `${terrain.drawn.length} patches · ${flora.count} trees · ${waters.pieces.size} water · cam ${rig.cam.position.y.toFixed(0)} m · ${phone ? "phone" : "high"}`;
    requestAnimationFrame(loop);
  }
  window.__live = {ready: true, frame, rig, clock, folk, towns, terrain, flora, renderer, box,
    // render one moment fully (for pictures): enough budget to finish what is streamed
    async settle(n = 6) { for (let k = 0; k < n; k++) { frame(0, {budget: 4000}); await new Promise(r => setTimeout(r, 300)); } frame(0, {budget: 4000}); return true; },
    stats: () => ({calls: renderer.info.render.calls, triangles: renderer.info.render.triangles, patches: terrain.drawn.length, trees: flora.count, people: folk.count})};
  frame(0, {budget: 4000});
  requestAnimationFrame(loop);
}

main().catch(e => { say("could not draw the world: " + e.message); console.error(e); });
