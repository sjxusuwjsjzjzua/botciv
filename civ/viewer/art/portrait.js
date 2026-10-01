// Portraits for the journal: a person's own figure (the same kit as on the land), head and shoulders,
// as they looked on a given day, drawn once into a small picture and kept.
import * as THREE from "three";
import {toon} from "./toon.js";
import * as Fig from "./figure.js";
import {looksOf, dress, CLOTH, greyed} from "../scene/people.js";

export class Portraits {
  constructor(store, size = 96) {
    this.s = store; this.size = size; this.cache = new Map();
    this.canvas = document.createElement("canvas");
    this.r = new THREE.WebGLRenderer({canvas: this.canvas, antialias: true, alpha: true, preserveDrawingBuffer: true});
    this.r.setPixelRatio(1); this.r.setSize(size, size, false);
    this.r.outputColorSpace = THREE.SRGBColorSpace;
    this.scene = new THREE.Scene();
    this.scene.add(new THREE.HemisphereLight(0xfff4e0, 0x806a50, 1.6));
    const sun = new THREE.DirectionalLight(0xffffff, 1.6); sun.position.set(1, 2, 3); this.scene.add(sun);
    this.cam = new THREE.PerspectiveCamera(26, 1, 0.1, 10);
    this.cam.position.set(0, 0.58, 1.55); this.cam.lookAt(0, 0.5, 0);
    this.P = Fig.parts(); this.H = Fig.hairs(); this.W = Fig.wear();
    this.mat = c => toon({color: c});
    this.dark = new THREE.MeshBasicMaterial({color: 0x2a1e18}); this.white = new THREE.MeshBasicMaterial({color: 0xffffff});
    this.pink = new THREE.MeshBasicMaterial({color: 0xff8a8a, transparent: true, opacity: 0.45});
  }

  // a data: URL of the portrait of person id as of time t (kept per person and day)
  of(id, t) {
    const day = this.s.snapshot(t), key = id + ":" + (day ? day.t : 0);
    if (this.cache.has(key)) return this.cache.get(key);
    const person = this.s.person(id);
    if (!person) return "";
    const look = looksOf(person), wear = dress(day?.people.get(id)?.inv, this.s.cat), age = this.s.age(id, t);
    const g = new THREE.Group(), add = (geo, mat, x = 0, y = 0, z = 0, sx = 1, sy = 1, sz = 1, parent = g, ry = 0) => {
      const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); m.scale.set(sx, sy, sz); m.rotation.y = ry; parent.add(m); return m; };
    const body = add(this.P.body, this.mat(wear.shirt), 0, Fig.JOINT.hip);
    const head = new THREE.Group(); head.position.set(0, Fig.JOINT.neck, 0); g.add(head);
    add(this.P.head, this.mat(look.skin), 0, 0, 0, 1, 1, 1, head);
    add(this.H[look.style], this.mat(age > 48 ? greyed(look.hair, Math.min(1, (age - 48) / 15)) : look.hair), 0, 0, 0, 1, 1, 1, head);
    if (wear.hat) add(this.W[wear.hat], this.mat(wear.hat === "furHat" ? CLOTH.fur : 0xe2c27a), 0, 0, 0, 1, 1, 1, head);
    for (const s of [-1, 1]) {
      add(this.P.eye, this.dark, s * 0.066, 0.158, 0.15, 1, 1, 1, head);
      add(this.P.shine, this.white, s * 0.066 + 0.01, 0.176, 0.166, 1, 1, 1, head);
      if (look.blush) add(this.P.blush, this.pink, s * 0.105, 0.115, 0.135, 1, 1, 1, head, s * 0.5);
    }
    if (wear.cape) add(this.W.cape, new THREE.MeshToonMaterial({color: wear.cape, side: THREE.DoubleSide}), 0, Fig.JOINT.shoulder - Fig.JOINT.hip, 0, 1, 1, 1, body);
    if (wear.necklace) add(this.W.necklace, this.mat(0xe6b84a), 0, Fig.JOINT.shoulder - Fig.JOINT.hip - 0.02, 0.02, 1, 1, 1, body);
    g.rotation.y = -0.35;
    this.scene.add(g);
    this.r.render(this.scene, this.cam);
    const url = this.canvas.toDataURL("image/png");
    this.scene.remove(g);
    g.traverse(o => { if (o.material && o.material !== this.dark && o.material !== this.white && o.material !== this.pink) o.material.dispose(); });
    if (this.cache.size > 600) this.cache.clear();
    this.cache.set(key, url);
    return url;
  }
}
