// Story: time that lingers where something happens and hurries through the rest, and the story lines.
// Following someone, it is their story: what they set out to do, what they and those near them say, what
// befalls them, and (for minds of their own) what they think as they decide. Following no one, it is the
// world's story: it lingers on its notable moments and the camera goes to each.
import {esc, doing} from "./text.js";

const NOTABLE = new Set(["birth", "death", "pledge", "attack", "first", "monument", "group", "law", "craft_lost", "steal", "take_crop",
  "teach", "deal", "trade", "book", "tame", "conceive", "promise_broken", "promise_kept", "skill", "build",
  "fealty", "renounce", "muster", "raid", "plunder", "repelled", "rally", "peace", "broke_peace", "captive", "ransomed", "escaped"]);
const WORLD = new Set(["birth", "death", "pledge", "attack", "first", "monument", "group", "law", "craft_lost", "book",
  "fealty", "renounce", "raid", "plunder", "repelled", "peace", "broke_peace", "captive"]);

export class Story {
  constructor(store, el) {
    this.s = store; this.el = el;
    this.lines = [];               // [{t, html, kind}]
    this.cache = new Map();        // "focus:hour" -> seconds the hour stays on screen
    this.focus = undefined;
  }

  // what happened in hour h that matters to the one followed (or to the world)
  moments(h, focus) {
    const s = this.s, out = [];
    const a = s.hour(h), prev = s.hour(h - 1);
    if (focus != null) {
      const me = a?.people.get(focus), was = prev?.people.get(focus);
      if (me && was && (me.verb !== was.verb || me.detail !== was.detail) && me.verb && me.verb !== "go")
        out.push({kind: "act", w: 0.8, html: `${this.name(focus)} ${esc(this.phrase(me))}`});
      for (const e of s.localEvents(h, h)) {
        const mine = e.who.includes(focus);
        let near = false;
        if (!mine && e.kind === "say" && me) {
          const sp = a?.people.get(e.who[0]);
          near = sp && Math.abs(sp.x - me.x) + Math.abs(sp.y - me.y) <= 5;
        }
        if (mine || near) out.push({kind: e.kind, w: e.kind === "say" ? (mine ? 2 : 1) : NOTABLE.has(e.kind) ? 3 : 1.2, html: this.link(e.text)});
      }
      const ch = s.chunkAt(h);
      for (const th of ch ? ch.thoughts : []) if (th.t === h && th.id === focus && th.thought)
        out.push({kind: "thought", w: 2.5, html: `<i>✦ ${this.name(focus)} thinks: “${esc(th.thought)}”</i>`, thought: th.thought});
    } else {
      for (const e of s.localEvents(h, h)) if (WORLD.has(e.kind)) out.push({kind: e.kind, w: 3, html: this.link(e.text), who: e.who});
    }
    return out;
  }

  // seconds an hour stays on screen at story speed
  dwell(h, focus) {
    const k = focus + ":" + h;
    if (this.cache.has(k)) return this.cache.get(k);
    if (!this.s.ready(h)) return 0.35;
    const m = this.moments(h, focus), busy = m.reduce((a, x) => a + x.w, 0);
    let secs;
    if (focus != null) {
      const me = this.s.hour(h)?.people.get(focus);
      const asleep = me && (me.verb === "sleep" || (me.verb === "rest" && this.s.cal.of(h).night));
      secs = busy ? Math.min(6, 1.1 + 1.3 * busy) : asleep ? 0.12 : 0.4;
    } else secs = busy ? Math.min(6, 2 + busy) : 0.06;
    if (this.cache.size > 5000) this.cache.clear();
    this.cache.set(k, secs);
    return secs;
  }

  // a new hour has come: its story lines; returns the moments (for bubbles and the camera)
  hour(h, focus) {
    if (focus !== this.focus) { this.focus = focus; this.lines = []; }
    const m = this.moments(h, focus);
    for (const x of m) this.lines.push({t: h, html: x.html, kind: x.kind});
    this.lines = this.lines.slice(-5);
    return m;
  }

  clear() { this.lines = []; }
  // a line from the viewer itself (caught up, gone...), told once
  note(t, html) {
    if (this.lines.at(-1)?.html === html) return;
    this.lines.push({t: Math.floor(t), html, kind: "note"});
    this.lines = this.lines.slice(-5);
  }

  // the lines as HTML (for the TV's side panel)
  linesHtml() {
    return this.lines.map(l => `<div class="line ${l.kind}"><span class="when">${this.s.cal.of(l.t).part}</span> ${l.html}</div>`).join("");
  }

  render(show) {
    const el = this.el;
    if (!show || !this.lines.length) { el.hidden = true; return; }
    const html = this.lines.map((l, i) => `<div class="line ${l.kind}" style="opacity:${0.45 + 0.55 * (i + 1) / this.lines.length}">
      <span class="when">${this.s.cal.of(l.t).part}</span> ${l.html}</div>`).join("");
    if (html !== el.dataset.html) { el.innerHTML = html; el.dataset.html = html; }
    el.hidden = false;
  }

  phrase(now) {
    const d = doing(now, id => this.s.person(id)?.name ?? "someone");
    return now.verb === "sleep" ? "lies down to sleep" : now.verb === "rest" ? "rests" : `sets to ${d}`;
  }
  name(id) { return `<a href="#" data-person="${id}">${esc(this.s.person(id)?.name ?? "someone")}</a>`; }
  // names in an event's words become links
  link(text) {
    let h = esc(text);
    for (const p of this.namesIn(text)) h = h.replace(new RegExp(`\\b${p.name}\\b`), `<a href="#" data-person="${p.id}">${p.name}</a>`);
    return h;
  }
  namesIn(text) {
    if (!this.byName) { this.byName = new Map(); for (const p of this.s.people.values()) this.byName.set(p.name, p); }
    return [...new Set(text.match(/\b[A-Z][a-z]+\b/g) || [])].map(n => this.byName.get(n)).filter(Boolean);
  }
}
