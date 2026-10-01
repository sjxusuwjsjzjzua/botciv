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
import {Overlay} from "./overlay.js";
import {CameraRig} from "./camera.js";
import {living} from "../art/toon.js";

export class World3D {
  constructor(stage, store) {
    this.stage = stage; this.s = store;
    const small = matchMedia("(max-width: 700px)").matches || (navigator.hardwareConcurrency || 4) <= 4;
    this.quality = new URLSearchParams(location.search).get("quality") || (small ? "low" : "high");
    this.renderer = new THREE.WebGLRenderer({antialias: true, powerPreference: "high-performance"});
    this.renderer.setPixelRatio(Math.min(devicePixelRatio || 1, this.quality === "high" ? 2 : 1.5));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFShadowMap;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    stage.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.land = new Land(store.m.terrain, store.meta.name || "land");
    this.scene.add(this.land.mesh(), this.land.water());
    this.flora = new Flora(this.land, this.quality);
    this.scene.add(this.flora.group);
    this.sky = new Sky(this.scene, this.quality);
    this.props = new Props(this.scene, this.land);
    this.buildings = new Buildings(this.scene, this.land, store);
    this.people = new People(this.scene, this.land, store);
    this.overlay = new Overlay(stage, store);
    this.rig = new CameraRig(this.renderer.domElement, this.land,
      () => stage.dispatchEvent(new CustomEvent("panned")), e => this.pick(e));
    this.rig.goalDist = this.rig.dist = 38;
    this.clock = 0;
    this.covered = "";
  }

  focus(id) {
    const p = this.people.pos.get(id);
    if (p) this.rig.glideTo(p.x, p.z, Math.min(this.rig.goalDist, 14));
    else this.rig.goalDist = Math.min(this.rig.goalDist, 14);
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
    this.people.update(view, t, dt);
    if (view.follow != null) {
      const p = this.people.pos.get(view.follow);
      if (p) this.rig.glideTo(p.x, p.z);
    }
    this.rig.update(dt);
    this.sky.update(cal, this.rig.target, this.rig.dist);
    this.renderer.render(this.scene, this.rig.cam);
    this.overlay.update(view, this.people, this.rig.cam, this.w, this.h);
    this.lastT = t;
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
