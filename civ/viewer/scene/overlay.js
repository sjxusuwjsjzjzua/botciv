// Words over heads, as crisp HTML placed where the 3D figures are: what was just said, and the names of
// whoever is chosen or followed (and, close up, of everyone near the middle of the view).
import * as THREE from "three";
import {esc} from "../ui/text.js";

export class Overlay {
  constructor(stage, store) {
    this.s = store;
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
    const v = this.v, close = cam.position.distanceTo(people.pos.get(view.follow) ?? cam.position) < 14;
    const project = (p, lift) => { v.set(p.x, p.y + lift, p.z).project(cam); return v.z < 1 ? [(v.x + 1) / 2 * w, (1 - v.y) / 2 * h] : null; };
    // names
    const named = new Set([view.follow, view.sel?.type === "person" ? view.sel.id : null].filter(x => x != null));
    if (cam.position.y < 12) {
      for (const [id, p] of people.pos) {
        const xy = project(p, 0.7);
        if (xy && Math.abs(xy[0] - w / 2) < w * 0.35 && Math.abs(xy[1] - h / 2) < h * 0.35) named.add(id);
      }
    }
    for (const id of named) {
      const p = people.pos.get(id);
      const xy = p && project(p, 0.72);
      if (xy) this.place("n" + id, esc(this.s.person(id)?.name) + (this.s.isMind(id) ? " ✦" : ""),
        "tagname" + (id === view.follow || id === view.sel?.id ? " key" : ""), xy[0], xy[1]);
    }
    // speech
    for (const b of view.bubbles) {
      const p = people.pos.get(b.id);
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
    void close;
  }
}
