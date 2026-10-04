// The land in 3D (docs/viewer.md, sections 4-7). Same interface as the map: new World3D(stage, store);
// frame(view, dt); focus(id); dispatches "pick" and "panned" on the stage. Made of layers that each draw
// one part of the moment (land, water, plants, things, buildings, people, words over heads).
import * as THREE from "three";
import {Land} from "./land.js";
import {Flora} from "./flora.js";
import {Sky} from "./sky.js";
import {Props} from "./props.js";
import {Buildings} from "./buildings.js";
import {People} from "./people.js";
import {Animals} from "./animals.js";
import {Smoke} from "./smoke.js";
import {Overlay} from "./overlay.js";
import {CameraRig} from "./camera.js";
import {living} from "../art/toon.js";

export class World3D {
  constructor(stage, store) {
    this.stage = stage; this.s = store;
    const small = matchMedia("(max-width: 700px)").matches || (navigator.hardwareConcurrency || 4) <= 4;
    this.quality = new URLSearchParams(location.search).get("quality") || (small ? "low" : "high");
    this.renderer = new THREE.WebGLRenderer({antialias: true, powerPreference: "high-performance"});
    // resolution adapts to keep the frame rate (phones first: a Pixel 9 must run it smoothly)
    this.maxRatio = Math.min(devicePixelRatio || 1, this.quality === "high" ? 2 : 1.5);
    this.ratio = this.maxRatio;
    this.renderer.setPixelRatio(this.ratio);
    this.frames = []; this.debug = new URLSearchParams(location.search).has("debug");
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    stage.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.land = new Land(store.m.terrain, store.meta.name || "land");
    this.scene.add(this.land.mesh(this.quality === "high" ? 3 : 2), this.land.water());
    this.flora = new Flora(this.land, this.quality);
    this.scene.add(this.flora.group);
    this.sky = new Sky(this.scene, this.quality);
    this.props = new Props(this.scene, this.land);
    this.buildings = new Buildings(this.scene, this.land, store);
    this.people = new People(this.scene, this.land, store);
    this.animals = new Animals(this.scene, this.land);
    this.smoke = new Smoke(this.scene, this.land, store);
    this.overlay = new Overlay(stage, store, this.land);
    this.rig = new CameraRig(this.renderer.domElement, this.land,
      () => stage.dispatchEvent(new CustomEvent("panned")), e => this.pick(e));
    this.rig.goalDist = this.rig.dist = this.quality === "high" ? 38 : 26;
    this.clock = 0;
    this.covered = "";
  }

  // follow someone: fly to them; from far out, come down close (near already, the zoom is left as it is)
  focus(id) {
    const p = this.people.pos.get(id), dist = this.rig.goalDist > 24 ? 14 : null;
    if (p) this.rig.flyTo(p.x, p.z, dist);
    else if (dist) this.rig.goalDist = dist;
  }

  // go and look at someone, without taking over the camera (the world's story moves it this way)
  show(id) {
    const p = this.people.pos.get(id);
    if (p) this.rig.flyTo(p.x, p.z, Math.min(Math.max(this.rig.goalDist, 16), 30));
  }

  resize() {
    const r = this.stage.getBoundingClientRect();
    if (r.width !== this.w || r.height !== this.h) {
      this.w = r.width; this.h = r.height;
      this.renderer.setSize(r.width, r.height, false);
      this.rig.resize(r.width, r.height);
    }
  }

  frame(view, dt) {
    this.resize();
    const s = this.s, t = view.t;
    this.clock += dt;
    living.uTime.value = this.clock;
    const cal = s.cal.of(t), snap = s.snapshot(t);
    // what stands where: plants step aside for buildings and roads
    if (snap && snap.t !== this.snapT) {
      this.snapT = snap.t;
      const covered = new Set();
      for (const b of snap.buildings) covered.add(b.y * this.land.w + b.x);
      for (const k of snap.roads) { const [x, y] = k.split(",").map(Number); covered.add(y * this.land.w + x); }
      this.flora.clear(covered);
    }
    this.props.update(snap);
    this.buildings.update(snap, t, cal);
    this.people.update(view, t, dt, this.rig.cam, this.buildings.byTile);
    this.animals.update(s, t, snap, this.rig.cam);
    if (view.follow != null) {
      const p = this.people.pos.get(view.follow);
      if (p) this.rig.glideTo(p.x, p.z);
    }
    this.rig.update(dt);
    this.flora.lod(this.rig.target, this.rig.dist);
    living.uFade.value = 1.4 + this.rig.dist * 0.04;   // the tube in which trees sink away: what the camera looks at stays in view
    living.uTarget.value.copy(this.rig.target).y += 0.4;
    this.props.lod(this.rig.target, this.rig.dist);
    // shadows close up; far out (a map's view) they are too small to see, and the pass is costly
    this.sky.sun.castShadow = this.rig.dist < 70;
    this.sky.update(cal, this.rig.target, this.rig.dist);
    this.smoke.update(snap, cal, this.rig.target, this.h || 800);
    // on TV a panel covers the right (or, on a phone, the bottom): the picture shifts so its middle is in the open part
    const tv = document.body.classList.contains("tv");
    if (tv) {
      const phone = this.w <= 700, panel = phone ? 0 : Math.min(this.w * 0.34, 560);
      this.rig.cam.setViewOffset(this.w, this.h, panel / 2, phone ? this.h * 0.21 : 0, this.w, this.h);
    } else if (this.rig.cam.view?.enabled) this.rig.cam.clearViewOffset();
    this.renderer.render(this.scene, this.rig.cam);
    this.adapt(dt);
    this.overlay.update(view, this.people, this.rig.cam, this.w, this.h);
    this.lastT = t;
  }

  // hold the frame rate: below about 40 a second, draw fewer pixels; with room to spare, more again
  adapt(dt) {
    this.frames.push(dt);
    if (this.frames.length < 45) return;
    const avg = this.frames.reduce((a, b) => a + b, 0) / this.frames.length;
    this.frames.length = 0;
    const was = this.ratio;
    if (avg > 1 / 40 && this.ratio > 0.6) this.ratio = Math.max(0.6, this.ratio - 0.15);
    else if (avg < 1 / 55 && this.ratio < this.maxRatio) this.ratio = Math.min(this.maxRatio, this.ratio + 0.1);
    if (this.ratio !== was) { this.renderer.setPixelRatio(this.ratio); this.w = 0; }
    if (this.debug) {
      const i = this.renderer.info.render;
      this.stats ??= Object.assign(document.createElement("div"), {className: "pill", style: "position:absolute;left:12px;top:56px;font:12px monospace"});
      if (!this.stats.isConnected) this.stage.appendChild(this.stats);
      this.stats.textContent = `${Math.round(1 / avg)} fps · ${i.calls} draws · ${Math.round(i.triangles / 1000)}k tris · ×${this.ratio.toFixed(2)} · ${this.quality}`;
    }
  }

  pick(e) {
    const r = this.renderer.domElement.getBoundingClientRect();
    const sx = e.clientX - r.left, sy = e.clientY - r.top;
    // a person under the pointer (nearest on screen, within reach)
    const v = new THREE.Vector3();
    let best = null, bd = 28;
    for (const [id, p] of this.people.pos) {
      v.set(p.x, p.y + 0.45, p.z).project(this.rig.cam);
      if (v.z > 1) continue;
      const d = Math.hypot((v.x + 1) / 2 * r.width - sx, (1 - v.y) / 2 * r.height - sy);
      if (d < bd) { bd = d; best = id; }
    }
    let sel = null;
    if (best != null) sel = {type: "person", id: best};
    else {
      const g = this.rig.groundUnder(sx / r.width * 2 - 1, -(sy / r.height) * 2 + 1);
      if (g) {
        const x = Math.floor(g.x), y = Math.floor(g.z);
        const b = this.s.snapshot(this.lastT ?? this.s.last)?.buildings.find(q => q.x === x && q.y === y);
        sel = b ? {type: "building", id: b.id} : {type: "tile", x, y};
      }
    }
    if (sel) this.stage.dispatchEvent(new CustomEvent("pick", {detail: sel}));
  }
}
