// The map: the land from above, for devices without 3D (and as ?view=map). Same interface as the 3D scene:
// new Scene(stage, store); scene.frame(view, dt); scene.focus(personId); it dispatches "pick" and "panned" on stage.
import {hue} from "../art/look.js";

export class Map2D {
  constructor(stage, store) {
    this.stage = stage; this.s = store;
    this.cv = document.createElement("canvas");
    stage.appendChild(this.cv);
    this.g = this.cv.getContext("2d");
    this.zoom = 1; this.cx = store.meta.w / 2; this.cy = store.meta.h / 2;
    this.land = this.paintLand();
    this.input();
  }

  paintLand() {
    const T = 8, s = this.s, c = document.createElement("canvas");
    c.width = s.meta.w * T; c.height = s.meta.h * T;
    const x = c.getContext("2d");
    for (let y = 0; y < s.meta.h; y++) for (let X = 0; X < s.meta.w; X++) {
      const ch = s.m.terrain[y][X];
      x.fillStyle = s.cat.terrain[ch]?.color ?? "#888";
      x.fillRect(X * T, y * T, T, T);
      if (ch === "T") { x.fillStyle = "rgba(20,50,20,.35)"; x.beginPath(); x.arc(X * T + 4, y * T + 4, 3, 0, 7); x.fill(); }
    }
    return c;
  }

  cam() {
    const r = this.cv.getBoundingClientRect(), dpr = devicePixelRatio || 1;
    if (this.cv.width !== Math.round(r.width * dpr) || this.cv.height !== Math.round(r.height * dpr)) {
      this.cv.width = Math.round(r.width * dpr); this.cv.height = Math.round(r.height * dpr);
    }
    const tile = Math.min(r.width / this.s.meta.w, r.height / this.s.meta.h) * this.zoom;
    return {tile, ox: r.width / 2 - this.cx * tile, oy: r.height / 2 - this.cy * tile, dpr, w: r.width, h: r.height, r};
  }

  // where someone is at t: between this hour's place and the next, walked smoothly
  where(id, t) {
    const a = this.s.hour(t), b = this.s.nextHour(t);
    const p = a?.people.get(id);
    if (!p) return null;
    const q = b?.people.get(id), f = t - Math.floor(t);
    return q ? {x: p.x + (q.x - p.x) * f, y: p.y + (q.y - p.y) * f, p} : {x: p.x, y: p.y, p};
  }

  show(id) { const w = this.where(id, this.lastT ?? this.s.last); if (w) { this.cx = w.x + .5; this.cy = w.y + .5; if (this.zoom < 3) this.zoom = 3; } }

  lookAt(x, y) { this.cx = x + .5; this.cy = y + .5; if (this.zoom < 3) this.zoom = 3; }
  focus(id) { this.followId = id; if (this.zoom < 4) this.zoom = 4; }

  frame(view) {
    const s = this.s, c = this.cam(), T = c.tile, g = this.g, t = view.t;
    g.setTransform(c.dpr, 0, 0, c.dpr, 0, 0);
    g.clearRect(0, 0, c.w, c.h);
    if (view.follow != null) { const w = this.where(view.follow, t); if (w) { this.cx = w.x + .5; this.cy = w.y + .5; } }
    const h = s.hour(t), snap = s.snapshot(t);
    g.imageSmoothingEnabled = false;
    g.drawImage(this.land, c.ox, c.oy, s.meta.w * T, s.meta.h * T);
    g.save(); g.translate(c.ox, c.oy);
    if (snap) {
      g.fillStyle = "#a89a7c";
      for (const k of snap.roads) { const [x, y] = k.split(",").map(Number); g.fillRect(x * T + T * .1, y * T + T * .35, T * .8, T * .3); }
      for (const b of snap.buildings) {
        const roles = s.cat.buildings[b.kind]?.roles ?? [];
        g.globalAlpha = b.done ? 1 : .5;
        g.fillStyle = roles.includes("workshop") ? "#8a4a2f" : roles.includes("shelter") ? "#b0773f" : roles.includes("farm") ? (b.growth?.ripe ? "#d8b45a" : "#9c7a44") :
          roles.includes("pen") ? "#7c6a4a" : roles.includes("monument") ? "#8d8a86" : "#8b5a2b";
        g.fillRect(b.x * T + T * .12, b.y * T + T * .12, T * .76, T * .76);
        g.globalAlpha = 1;
      }
    }
    if (h) {
      for (const hd of h.herds) { g.fillStyle = "#8a6a44"; g.beginPath(); g.ellipse((hd.x + .5) * T, (hd.y + .5) * T, T * .3, T * .16, 0, 0, 7); g.fill(); }
      for (const pk of h.packs) { g.fillStyle = "#4b4f57"; g.beginPath(); g.ellipse((pk.x + .5) * T, (pk.y + .5) * T, T * .25, T * .12, 0, 0, 7); g.fill(); }
      const r = Math.max(2.5, T * .3);
      for (const id of h.people.keys()) {
        const w = this.where(id, t), a = s.person(id);
        if (!w || !a) continue;
        const X = (w.x + .5) * T, Y = (w.y + .5) * T;
        g.fillStyle = `hsl(${hue(a.name)} 60% ${w.p.health <= 4 ? 45 : 62}%)`;
        g.beginPath(); g.arc(X, Y, r, 0, 7); g.fill();
        g.lineWidth = s.isMind(id) ? 2 : 1; g.strokeStyle = s.isMind(id) ? "#fff" : "rgba(0,0,0,.4)"; g.stroke();
        if ((view.sel?.type === "person" && view.sel.id === id) || view.follow === id) {
          g.strokeStyle = "#b5562f"; g.lineWidth = 2.5; g.beginPath(); g.arc(X, Y, r + 3, 0, 7); g.stroke();
        }
        if (T >= 14) { g.fillStyle = "rgba(255,250,240,.9)"; g.font = `600 ${Math.min(13, T * .3)}px sans-serif`; g.textAlign = "center"; g.fillText(a.name, X, Y + r + 12); }
      }
      g.font = `${Math.max(11, Math.min(14, T * .3))}px sans-serif`; g.textAlign = "center";
      for (const b of view.bubbles) {
        const w = this.where(b.id, t);
        if (!w) continue;
        const text = b.text.length > 60 ? b.text.slice(0, 58) + "…" : b.text, tw = g.measureText(text).width + 14, X = (w.x + .5) * T, Y = w.y * T - 6;
        g.fillStyle = "rgba(255,252,244,.96)"; g.beginPath(); g.roundRect(X - tw / 2, Y - 24, tw, 22, 9); g.fill();
        g.fillStyle = "#3b2f22"; g.fillText(text, X, Y - 9);
      }
    }
    g.restore();
    const cal = s.cal.of(t);
    if (cal.night) { g.fillStyle = "rgba(10,20,50,.35)"; g.fillRect(0, 0, c.w, c.h); }
    if (cal.season === "winter") { g.fillStyle = "rgba(235,245,255,.15)"; g.fillRect(0, 0, c.w, c.h); }
    this.lastT = t;
  }

  // ---------- pan, pinch, wheel, pick ----------
  input() {
    const cv = this.cv, P = new Map();
    let drag = null;
    cv.addEventListener("pointerdown", e => { cv.setPointerCapture(e.pointerId); P.set(e.pointerId, [e.clientX, e.clientY]); drag = {x: e.clientX, y: e.clientY, moved: false, d: null}; });
    cv.addEventListener("pointermove", e => {
      if (!P.has(e.pointerId) || !drag) return;
      const prev = P.get(e.pointerId); P.set(e.pointerId, [e.clientX, e.clientY]);
      const c = this.cam();
      if (P.size === 2) {
        const [a, b] = [...P.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]);
        if (drag.d) this.zoom = Math.max(1, Math.min(14, this.zoom * d / drag.d));
        drag.d = d; drag.moved = true; return;
      }
      if (Math.abs(e.clientX - drag.x) + Math.abs(e.clientY - drag.y) > 6) drag.moved = true;
      if (drag.moved) { this.cx -= (e.clientX - prev[0]) / c.tile; this.cy -= (e.clientY - prev[1]) / c.tile; this.stage.dispatchEvent(new CustomEvent("panned")); }
    });
    cv.addEventListener("pointerup", e => { P.delete(e.pointerId); if (drag && !drag.moved && !P.size) this.pick(e); if (!P.size) drag = null; });
    cv.addEventListener("wheel", e => { e.preventDefault(); this.zoom = Math.max(1, Math.min(14, this.zoom * Math.exp(-e.deltaY * .002))); }, {passive: false});
  }

  pick(e) {
    const c = this.cam(), wx = (e.clientX - c.r.left - c.ox) / c.tile, wy = (e.clientY - c.r.top - c.oy) / c.tile;
    const t = this.lastT ?? this.s.last, h = this.s.hour(t);
    let best = null, bd = .8;
    for (const id of h ? h.people.keys() : []) {
      const w = this.where(id, t), d = w && Math.hypot(w.x + .5 - wx, w.y + .5 - wy);
      if (w && d < bd) { bd = d; best = id; }
    }
    const x = Math.floor(wx), y = Math.floor(wy), b = this.s.snapshot(t)?.buildings.find(q => q.x === x && q.y === y);
    const sel = best != null ? {type: "person", id: best} : b ? {type: "building", id: b.id} : {type: "tile", x, y};
    this.stage.dispatchEvent(new CustomEvent("pick", {detail: sel}));
  }
}
