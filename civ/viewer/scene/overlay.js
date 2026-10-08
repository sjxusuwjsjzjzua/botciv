// Words over heads, as crisp HTML placed where the 3D figures are: what was just said, the names of
// whoever is chosen or followed (and, close up, of everyone near the middle of the view), and the names
// the people have given to places, from the day each was named.
import * as THREE from "three";
import {esc} from "../ui/text.js";

export class Overlay {
  constructor(stage, store, land) {
    this.s = store; this.land = land;
    this.el = document.createElement("div");
    this.el.className = "overlay";
    stage.appendChild(this.el);
    this.v = new THREE.Vector3();
    this.nodes = new Map();
  }

  place(key, html, cls, x, y) {
    let n = this.nodes.get(key);
    if (!n) { n = document.createElement("div"); this.el.appendChild(n); this.nodes.set(key, n); }
    if (n.dataset.html !== html) { n.innerHTML = html; n.dataset.html = html; }
    n.className = cls;
    n.style.transform = `translate(${x.toFixed(1)}px, ${y.toFixed(1)}px) translate(-50%, -100%)`;
    n.dataset.seen = "1";
  }

  update(view, people, cam, w, h) {
    for (const n of this.nodes.values()) n.dataset.seen = "";
    const v = this.v, watched = view.watch?.id ?? view.follow;
    const project = (p, lift) => { v.set(p.x, p.y + lift, p.z).project(cam); return v.z < 1 ? [(v.x + 1) / 2 * w, (1 - v.y) / 2 * h] : null; };
    // names: whom one watches and whom one has chosen; close up, also the few nearest the middle of the view
    const named = new Set([watched, view.sel?.type === "person" ? view.sel.id : null].filter(x => x != null));
    if (cam.position.y < 12) {
      const near = [];
      for (const [id, p] of people.pos) {
        if (named.has(id)) continue;
        const xy = project(p, 0.7);
        if (xy && Math.abs(xy[0] - w / 2) < w * 0.3 && Math.abs(xy[1] - h / 2) < h * 0.3) near.push([Math.hypot(xy[0] - w / 2, xy[1] - h / 2), id]);
      }
      near.sort((a, b) => a[0] - b[0]);
      for (const [, id] of near.slice(0, 5)) named.add(id);
    }
    for (const id of named) {
      const p = people.pos.get(id);
      const xy = p && project(p, 0.72);
      if (xy) this.place("n" + id, esc(this.s.person(id)?.name) + (this.s.isMind(id) ? " ✦" : ""),
        "tagname" + (id === watched || id === view.sel?.id ? " key" : ""), xy[0], xy[1]);
    }
    // places the people have named, once named, over the ground they name: the dozen nearest the middle of the view
    const pls = [];
    for (const pl of Array.isArray(this.s.places) ? this.s.places : []) {
      const [x, y, name, , tick] = pl;
      if (tick != null && tick > view.t) continue;
      const xy = project({x: x + 0.5, y: this.land ? this.land.groundAt(x + 0.5, y + 0.5) : 0, z: y + 0.5}, 1.6);
      if (xy && xy[0] > -40 && xy[0] < w + 40 && xy[1] > 0 && xy[1] < h + 20) pls.push([Math.hypot(xy[0] - w / 2, xy[1] - h / 2), x, y, name, xy]);
    }
    pls.sort((a, b) => a[0] - b[0]);
    for (const [, x, y, name, xy] of pls.slice(0, 12)) this.place("p" + x + "," + y, esc(name), "placename", xy[0], xy[1]);
    // speech
    const newest = new Map();                      // one bubble a person: the newest (two drew one over the other)
    for (const b of view.bubbles) if (!newest.has(b.id) || newest.get(b.id).born < b.born) newest.set(b.id, b);
    for (const b of newest.values()) {
      const p = people.pos.get(b.id);
      if (p && b.id !== watched && cam.position.distanceTo(p) > 60) continue;     // far off, words are too small to matter
      const xy = p && project(p, 0.95);
      if (!xy) continue;
      const text = b.text.length > 90 ? b.text.slice(0, 88) + "…" : b.text;
      this.place("b" + b.id + b.born, esc(text), b.thought ? "bubble thought" : "bubble", xy[0], xy[1]);
    }
    // moments: a little sign rising over the head
    for (const m of view.emotes || []) {
      const p = people.pos.get(m.id), age = (view.now - m.born) / 2600;
      const xy = p && project(p, 0.9 + age * 0.35);
      if (xy) this.place("e" + m.id + m.born + m.icon, m.icon, "emote", xy[0], xy[1]);
    }
    for (const [k, n] of this.nodes) if (!n.dataset.seen) { n.remove(); this.nodes.delete(k); }
  }
}
