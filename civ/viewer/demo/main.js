// world5 step 0: the look, proven in the real viewer's kit (docs/world5_handoff.md §5). One continuous scene in metres:
// a river village laid out as the target picture, the land around it, a track through the forest edge to a hamlet.
// No zones, no tile or chunk edges, detail by distance only.
//   ?tour=1   the fly-down (4 km up to 15 m over the well, about 40 s)
//   ?walk=1   follow one person from their door, over the bridge, out to the strips and along the track
//   ?shot=A..F  set views (A the target view, B 600 m up, C 4 km up, D 15 m over the well, E the walk at the bridge,
//              F as A, a winter night); ?debug=1 frames a second, draw calls, triangles; ?tier=phone the light tier
import * as THREE from "three";
import {LandFn} from "./land.js";
import {Terrain, landMaps} from "./terrain.js";
import {Town, paintDetail} from "./town.js";
import {Flora} from "./flora.js";
import {Folk} from "./folk.js";
import {Rig, Path} from "./camera.js";
import {Post} from "./post.js";
import {living} from "../art/toon.js";
import {EYE, material} from "../art/village.js";

const Q = new URLSearchParams(location.search);
const phone = Q.get("tier") === "phone" || (Q.get("tier") !== "high" && Math.min(innerWidth, innerHeight) < 600);
const say = t => { const el = document.getElementById("load"); if (el) el.textContent = t; };
const tick = () => new Promise(r => setTimeout(r, 0));

async function main() {
  say("reading the land…");
  const data = await (await fetch("demo/river_village.json")).json();
  const land = new LandFn(data.land);
  await tick();

  const renderer = new THREE.WebGLRenderer({antialias: false, powerPreference: "high-performance"});
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.info.autoReset = false;
  document.body.appendChild(renderer.domElement);
  const ratio = Math.min(devicePixelRatio || 1, phone ? 1.75 : 2);
  const scene = new THREE.Scene();

  say("painting the ground…");
  await tick();
  const root = 125 * 2 ** 7, origin = [3000 - root / 2, 1500 - root / 2];
  const maps = landMaps(land, [-1200, -1000, 8400, 5200], phone ? [768, 476] : [1280, 792], [origin[0], origin[1], root, root], [256, 256]);
  maps.detail = paintDetail(data, [1080, 1470, 440, 350], phone ? 3.2 : 4.6);
  maps.snow = living.uSnow;

  // the light of a late summer afternoon: warm low sun from the west-south-west, a cool sky
  const sunDir = new THREE.Vector3(-0.74, 0.52, 0.42).normalize();
  const hemi = new THREE.HemisphereLight(0xd8e4ee, 0x8a7a50, 0.85);
  const sun = new THREE.DirectionalLight(0xffdcaa, 2.75);
  sun.castShadow = true;
  sun.shadow.mapSize.set(phone ? 1024 : 2048, phone ? 1024 : 2048);
  sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.04; sun.shadow.radius = 2;
  scene.add(hemi, sun, sun.target);
  scene.fog = new THREE.Fog(0xe9dcc0, 1000, 5000);
  const light = {water: {value: 1}, way: {value: new THREE.Color(1, 1, 1)},
    imp: {uSunV: {value: new THREE.Vector3()}, uSunCol: {value: new THREE.Color()}, uSky: {value: new THREE.Color()}, uGround: {value: new THREE.Color()}}};

  // the sky: a gradient dome, warm at the horizon, and the sun's glow
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

  say("raising the land…");
  await tick();
  const terrain = new Terrain(scene, land, {maps, N: phone ? 32 : 40, K: 1.9, origin});
  say("building the village…");
  await tick();
  const town = new Town(scene, land, data, {tier: phone ? "phone" : "high", light});
  say("growing the forest…");
  await tick();
  const fields = data.fields;
  const inFields = (x, y) => x > 1140 && x < 1470 && y > 1652 && y < 1782;
  const inFieldsOrVillage = (x, y) => inFields(x, y) || Math.hypot(x - data.centre[0], y - data.centre[1]) < 75 || town.track.near(x, y).d < 6;
  const cc0 = Q.get("models") === "cc0" ? await (await import("./cc0.js")).loadKit() : null;
  if (cc0) scatter(scene, land, data, cc0, inFieldsOrVillage);
  const flora = new Flora(scene, land, {cell: 13, extra: data.trees, models: cc0, light: light.imp, near: phone ? [200, 260] : [300, 380],
    keepOff: (x, y) => town.track.near(x, y).d < 7 || inFields(x, y)});
  void fields;
  const folk = new Folk(scene, land, data);
  for (const b of data.buildings.filter(b => b.kind === "plank_bridge"))
    folk.decks.push([b.pos[0], b.pos[1], b.size[0] / 2, b.size[1] / 2 + 0.5, b.angle * Math.PI / 180, town.placeY(b) + 0.1]);
  const smoke = makeSmoke(scene, town.smokes);

  const rig = new Rig(renderer.domElement, land);
  const post = new Post(renderer, {samples: phone ? 2 : 4});
  const C = data.centre, well = data.buildings.find(b => b.kind === "well").pos;
  const walker = data.people.find(p => p.id === data.walker), bridge = data.buildings.find(b => b.kind === "plank_bridge").pos;
  const SPEEDUP = 5;
  // the views
  const VIEWS = {
    A: {x: C[0] + 2, z: C[1] + 20, dist: 132, pitch: 0.72, yaw: 0},
    B: {x: C[0] + 20, z: C[1] + 120, dist: 850, pitch: 0.78, yaw: 0.05},
    C: {x: 3300, z: 1560, dist: 4700, pitch: 1.0, yaw: 0.12},
    D: {x: well[0], z: well[1], dist: 21, pitch: 0.79, yaw: 0.6},
  };
  const tour = new Path([
    {t: 0, x: 3300, z: 1560, dist: 5400, pitch: 1.02, yaw: 0.14},
    {t: 9, x: 2500, z: 1600, dist: 2700, pitch: 0.96, yaw: 0.1},
    {t: 17, x: 1420, z: 1650, dist: 900, pitch: 0.86, yaw: 0.04},
    {t: 25, x: C[0] + 2, z: C[1] + 40, dist: 240, pitch: 0.8, yaw: 0.0},
    {t: 28.5, ...VIEWS.A},
    {t: 31.5, x: C[0] + 1, z: C[1] + 34, dist: 160, pitch: 0.79, yaw: 0.03},
    {t: 41, ...VIEWS.D},
  ]);
  const mode = Q.has("tour") ? "tour" : Q.has("walk") ? "walk" : "free";
  const shot = Q.get("shot");
  let night = shot === "F" || Q.has("night");
  if (shot && VIEWS[shot]) rig.set(VIEWS[shot]);
  else if (shot === "F") rig.set(VIEWS.A);
  else if (mode === "free") rig.set(VIEWS.A);

  // walking: where the one we follow is, and the camera a few metres behind at shoulder height
  const walkLen = (() => { let L = 0; for (let k = 1; k < walker.path.length; k++) L += Math.hypot(walker.path[k][0] - walker.path[k - 1][0], walker.path[k][1] - walker.path[k - 1][1]); return L; })();
  const bridgeS = (() => { let L = 0; for (let k = 1; k < walker.path.length; k++) { L += Math.hypot(walker.path[k][0] - walker.path[k - 1][0], walker.path[k][1] - walker.path[k - 1][1]);
    if (Math.abs(walker.path[k][1] - bridge[1]) < 0.5 && Math.abs(walker.path[k][0] - bridge[0]) < 0.5) return L; } return 0; })();
  const follow = {pos: new THREE.Vector3(), look: new THREE.Vector3(), init: false};
  function walkCam(walkT, dt, snap) {
    const s = walkT * walker.speed, p = folk.place(walker, walkT), ahead = folk.place(walker, walkT + 5 / walker.speed);
    let dx = ahead.x - p.x, dz = ahead.y - p.y; const l = Math.hypot(dx, dz) || 1; dx /= l; dz /= l;
    const g = folk.floor(p.x, p.y);
    const want = new THREE.Vector3(p.x - dx * 6.5 + dz * 1.2, g + 3.8, p.y - dz * 6.5 - dx * 1.2);
    want.y = Math.max(want.y, land.height(want.x, want.z) + 1.6);
    const look = new THREE.Vector3(p.x + dx * 12, g + 0.6, p.y + dz * 12);
    const k = snap || !follow.init ? 1 : 1 - Math.exp(-dt * 3);
    follow.pos.lerp(want, k); follow.look.lerp(look, k); follow.init = true;
    rig.cam.position.copy(follow.pos); rig.cam.lookAt(follow.look);
    rig.cam.near = 0.2; rig.cam.far = 9000; rig.cam.updateProjectionMatrix();
    rig.target.set(p.x, g, p.y); rig.dist = 5;
    void s;
  }

  // the debug line
  const dbg = Q.has("debug") ? document.getElementById("dbg") : null;
  if (dbg) dbg.style.display = "block";
  const frames = [];
  let W = 0, H = 0;
  function resize() {
    if (innerWidth === W && innerHeight === H) return;
    W = innerWidth; H = innerHeight;
    renderer.setPixelRatio(ratio); renderer.setSize(W, H);
    post.setSize(W, H, ratio);
    rig.cam.aspect = W / H; rig.cam.updateProjectionMatrix();
  }

  const clock = {t: Number(Q.get("t") ?? 0), last: performance.now()};
  const frozen = Q.has("t") || !!shot;
  if (shot === "E") clock.t = bridgeS / walker.speed / SPEEDUP;

  function setNight(on) {
    night = on;
    living.uNight.value = on ? 1 : 0;
    living.uSnow.value = on ? 1 : 0;
    hemi.color.set(on ? 0x5a6a9c : 0xd8e4ee); hemi.groundColor.set(on ? 0x2a2838 : 0x8a7a50); hemi.intensity = on ? 0.9 : 0.85;
    sun.color.set(on ? 0x9fb4e8 : 0xffdcaa); sun.intensity = on ? 0.55 : 2.6;
    skyMat.uniforms.uTop.value.set(on ? 0x101a36 : 0x86b4e0); skyMat.uniforms.uHor.value.set(on ? 0x3a4468 : 0xf6dfb4);
    scene.fog.color.set(on ? 0x2a3252 : 0xe9dcc0);
    town.setNight?.(on);
  }
  if (night) setNight(true);

  // one frame at time t (seconds of the demo), dt since the last
  function frame(t, dt, opts = {}) {
    resize();
    living.uTime.value = t;
    let walkT = null;
    if (mode === "tour") rig.set(tour.at(t));
    if (mode === "walk" || shot === "E") { walkT = Math.min(t * SPEEDUP, walkLen / walker.speed); walkCam(walkT, dt, opts.snap); }
    else rig.apply();
    const cam = rig.cam;
    cam.updateMatrixWorld();
    EYE.value.copy(cam.position);
    // sky and haze follow the eye; the haze closes with the height
    sky.position.copy(cam.position); sky.scale.setScalar(cam.far * 0.92);
    const D = Math.max(rig.dist, cam.position.y - land.height(cam.position.x, cam.position.z));
    scene.fog.near = D * 0.9 + 250; scene.fog.far = D * 4.5 + 2600;
    // the sun's shadow follows what is looked at
    const span = Math.min(1600, Math.max(22, D * 0.75));
    sun.position.copy(rig.target).addScaledVector(sunDir, span * 2 + 200);
    sun.target.position.copy(rig.target);
    const sc = sun.shadow.camera; sc.left = sc.bottom = -span; sc.right = sc.top = span; sc.near = 1; sc.far = span * 4 + 400; sc.updateProjectionMatrix();
    // light the hand-written shaders as the toon materials are lit
    light.imp.uSunV.value.copy(sunDir).transformDirection(cam.matrixWorldInverse);
    light.imp.uSunCol.value.copy(sun.color).multiplyScalar(sun.intensity);
    light.imp.uSky.value.copy(hemi.color).multiplyScalar(hemi.intensity);
    light.imp.uGround.value.copy(hemi.groundColor).multiplyScalar(hemi.intensity);
    light.water.value = night ? 0.35 : 1.0;
    light.way.value.setScalar(night ? 0.35 : 1.0);
    terrain.update(cam.position, opts.budget ?? (phone ? 3 : 5));
    flora.update(cam.position);
    town.update(cam.position);
    folk.update(mode === "walk" ? t * SPEEDUP : t, cam, walkT);
    smoke.update(t);
    renderer.info.reset();
    post.render(scene, cam);
  }

  // build ahead what the tour, the walk and the views will need, so no patch is built in flight
  say("readying the views…");
  await tick();
  const warm = [];
  const probe = v => { rig.set(v); rig.apply(); warm.push(rig.cam.position.clone()); };
  if (mode === "tour") for (let t = 0; t <= tour.T; t += 0.25) probe(tour.at(t));
  else if (mode === "walk") for (let t = 0; t <= walkLen / walker.speed / SPEEDUP; t += 0.5) { const p = folk.place(walker, t * SPEEDUP); warm.push(new THREE.Vector3(p.x, land.height(p.x, p.y) + 2.5, p.y)); }
  else probe(shot && VIEWS[shot] ? VIEWS[shot] : VIEWS.A);
  terrain.warm(warm);
  if (shot && VIEWS[shot]) rig.set(VIEWS[shot]); else if (mode === "free" || shot === "F") rig.set(VIEWS.A);
  say("");
  document.getElementById("load")?.remove();

  let fpsT = performance.now(), fpsN = 0, fps = 0;
  function loop() {
    const now = performance.now(), dt = Math.min(0.1, (now - clock.last) / 1000);
    clock.last = now;
    if (!frozen && !window.__demo.manual) clock.t += dt;
    if (!window.__demo.manual) frame(clock.t, dt);
    fpsN++;
    if (now - fpsT > 1000) { fps = fpsN * 1000 / (now - fpsT); fpsN = 0; fpsT = now; }
    if (dbg) dbg.textContent = `${fps.toFixed(0)} fps · ${renderer.info.render.calls} draws · ${(renderer.info.render.triangles / 1e6).toFixed(2)} M tris · ` +
      `${terrain.drawn.length} patches · ${flora.count} trees · cam ${rig.cam.position.y.toFixed(0)} m · ${phone ? "phone" : "high"} tier`;
    requestAnimationFrame(loop);
  }
  window.__demo = {
    ready: true, manual: false, VIEWS, tour, frame, renderer, terrain, flora, town, folk, rig, setNight,
    stats: () => ({calls: renderer.info.render.calls, triangles: renderer.info.render.triangles, patches: terrain.drawn.length,
      built: terrain.stats.built, trees: flora.count, town: town.stats, phone, ratio}),
    // render a moment exactly (for screenshots and the video): time, and enough budget to finish the land
    clock, renderAt(t) { window.__demo.manual = true; frame(t ?? clock.t, 1 / 30, {budget: 400, snap: true}); return window.__demo.stats(); },
  };
  frame(clock.t, 0, {budget: 400, snap: true});
  requestAnimationFrame(loop);
}

// smoke: soft puffs rising and spreading from the kilns, the hamlet's fire and a few hearths
function makeSmoke(scene, sources) {
  const PUFFS = 10, n = sources.length * PUFFS;
  const g = new THREE.InstancedBufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute([-1, -1, 0, 1, -1, 0, 1, 1, 0, -1, 1, 0], 3));
  g.setIndex([0, 1, 2, 0, 2, 3]);
  const src = new Float32Array(n * 3), seed = new Float32Array(n * 2);
  sources.forEach(([x, y, z, s], i) => { for (let k = 0; k < PUFFS; k++) { src.set([x, y, z], (i * PUFFS + k) * 3); seed.set([k / PUFFS + i * 0.37, s], (i * PUFFS + k) * 2); } });
  g.setAttribute("aSrc", new THREE.InstancedBufferAttribute(src, 3));
  g.setAttribute("aSeed", new THREE.InstancedBufferAttribute(seed, 2));
  g.instanceCount = n;
  const m = new THREE.ShaderMaterial({transparent: true, depthWrite: false, fog: true,
    uniforms: THREE.UniformsUtils.merge([THREE.UniformsLib.fog, {}]),
    vertexShader: `attribute vec3 aSrc; attribute vec2 aSeed; uniform float uTime; varying float vAge; varying vec2 vQ;
      #include <fog_pars_vertex>
      void main() {
        float age = fract(uTime * 0.08 + aSeed.x), k = aSeed.y, sd = aSeed.x * 17.0;
        vAge = age; vQ = position.xy;
        vec3 c = aSrc + vec3(age * 6.0 + sin(sd + uTime * 0.3) * age * 1.5, age * 12.0 * k, cos(sd) * age * 1.5);
        vec4 mvPosition = modelViewMatrix * vec4(c, 1.0);
        mvPosition.xy += position.xy * (0.45 + age * 3.0) * k;
        gl_Position = projectionMatrix * mvPosition;
        #include <fog_vertex>
      }`,
    fragmentShader: `uniform float uNight; varying float vAge; varying vec2 vQ;
      #include <fog_pars_fragment>
      void main() {
        float d = length(vQ);
        if (d > 1.0) discard;
        vec3 c = mix(vec3(0.95, 0.93, 0.9), vec3(0.45, 0.48, 0.58), uNight);
        gl_FragColor = vec4(c, (1.0 - d) * (1.0 - vAge) * smoothstep(0.0, 0.1, vAge) * 0.42);
        #include <colorspace_fragment>
        #include <fog_fragment>
      }`});
  m.uniforms.uTime = living.uTime; m.uniforms.uNight = living.uNight;
  const mesh = new THREE.Mesh(g, m);
  mesh.frustumCulled = false; mesh.renderOrder = 3;
  scene.add(mesh);
  return {update() {}};
}

// the ready-made kit's small things: bushes and rocks along the forest edge and in the meadows, stumps where wood
// was cut, log stacks by some houses (only with ?models=cc0)
function scatter(scene, land, data, kit, keepOff) {
  let seed = 21;
  const r = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
  const spots = {bush: [], rock: [], stump: [], logs: []};
  for (let k = 0; k < 9000 && spots.bush.length < 700; k++) {
    const x = 700 + r() * 5200, y = 1100 + r() * 1300, g = land.ground(x, y), cover = land.treeCover(x, y, g.chan);
    if (g.chan < 3 || keepOff(x, y)) continue;
    const edge = cover > 0.05 && cover < 0.6, u = r();
    if (edge && u < 0.5) spots.bush.push([x, g.h, y]);
    else if (edge && u < 0.62) spots.stump.push([x, g.h, y]);
    else if (cover < 0.05 && u < 0.035) spots.rock.push([x, g.h - 0.2, y]);
    else if (cover < 0.05 && u < 0.08) spots.bush.push([x, g.h, y]);
  }
  for (const b of data.buildings.filter(b => b.kind === "long_house" && b.household % 2 === 0)) {
    const a = b.angle * Math.PI / 180, x = b.pos[0] - Math.cos(a) * 4.6, y = b.pos[1] + Math.sin(a) * 4.6;
    spots.logs.push([x, land.height(x, y), y]);
  }
  const M = new THREE.Matrix4(), q = new THREE.Quaternion(), up = new THREE.Vector3(0, 1, 0);
  for (const [k, list] of Object.entries(spots)) {
    const m = new THREE.InstancedMesh(kit[k], material("tree"), list.length);
    list.forEach(([x, y, z], i) => { const s = 0.8 + r() * 0.5; M.compose(new THREE.Vector3(x, y, z), q.setFromAxisAngle(up, r() * 6.28), new THREE.Vector3(s, s, s)); m.setMatrixAt(i, M); });
    m.castShadow = m.receiveShadow = true; m.computeBoundingSphere();
    scene.add(m);
  }
}

main().catch(e => { say("could not draw the scene: " + e.message); console.error(e); });
