// TV: the land as something to watch from the sofa (a tab cast to a television, or a screen left on).
// It plays on its own at story speed. A storyteller chooses whom to watch: someone awake and doing
// something (those with minds of their own first, speaking or among others), followed for a while, their
// story and thoughts told beside the picture; any notable moment elsewhere (a birth, a death, a blow, a
// first, a law...) takes the camera there. At the newest hour it plays the last day again while it waits,
// looks for a newer world every two minutes, and carries on from where it was when one comes.
import {esc} from "./text.js";

const NOTABLE = new Set(["birth", "death", "pledge", "attack", "first", "monument", "group", "law", "craft_lost", "book", "steal"]);
const HOLD = 16;                 // hours one is watched before the storyteller looks for another

export class TV {
  constructor(store, side, hooks) {
    this.s = store; this.side = side; this.h = hooks;
    this.on = false; this.subject = null; this.since = 0; this.why = ""; this.feed = [];
    this.idleT = null; this.lock = null; this.poll = null; this.endT = null;
    side.addEventListener("click", e => { if (e.target.closest("#tvexit")) this.stop(); if (e.target.closest("#tvfull")) this.full(); });
    addEventListener("keydown", e => {
      if (!this.on) return;
      if (e.key === "Escape" && !document.fullscreenElement) this.stop();
      if (e.key === "f" || e.key === "F") this.full();
    });
    for (const ev of ["pointermove", "pointerdown", "keydown"]) addEventListener(ev, () => this.on && this.awake());
  }

  start(at = null) {
    const s = this.s, H = this.h;
    this.on = true;
    document.body.classList.add("tv");
    H.view.speed = "story";
    document.querySelector("#speed").value = "story";
    // from where it was asked, else about a day before the newest hour
    H.setT(at != null ? at : Math.max(s.first, s.last - s.cal.tpd), true);
    this.subject = null; this.feed = []; this.pick(Math.floor(H.view.t), "");
    H.setPlay(true);
    this.awake();
    this.wake();
    clearInterval(this.poll);
    this.poll = setInterval(() => this.newer(), 120000);
    try { history.replaceState(null, "", location.pathname + location.search + "#tv"); } catch (e) {}
  }

  stop() {
    this.on = false;
    document.body.classList.remove("tv", "idle");
    clearInterval(this.poll); clearTimeout(this.endT);
    if (this.lock) { this.lock.release().catch(() => {}); this.lock = null; }
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    this.h.follow(null);
    try { history.replaceState(null, "", location.pathname + location.search); } catch (e) {}
  }

  full() {
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    else document.documentElement.requestFullscreen?.().catch(() => {});
  }

  async wake() { try { if (navigator.wakeLock) this.lock = await navigator.wakeLock.request("screen"); } catch (e) {} }

  // the cursor and the buttons hide when nothing has moved for a while
  awake() {
    document.body.classList.remove("idle");
    clearTimeout(this.idleT);
    this.idleT = setTimeout(() => this.on && document.body.classList.add("idle"), 3000);
  }

  // who is worth watching in hour h: awake, doing something; minds of their own, speaking, among others
  pick(h, why) {
    const s = this.s, hour = s.hour(h);
    if (!hour) return;
    const speaking = new Set(s.localEvents(h - 2, h).filter(e => e.kind === "say").map(e => e.who[0]));
    const night = s.cal.of(h).night, all = [...hour.people.values()];
    let best = null, bs = -1;
    for (const q of all) {
      if (q.id === this.subject) continue;
      const asleep = q.verb === "sleep" || (q.verb === "rest" && night);
      if (asleep || !s.alive(q.id, h)) continue;
      let score = (s.isMind(q.id) ? 3 : 0) + (speaking.has(q.id) ? 3 : 0) + (q.verb && q.verb !== "wait" ? 1 : 0);
      for (const o of all) if (o !== q && Math.abs(o.x - q.x) + Math.abs(o.y - q.y) <= 3) score += 0.4;
      score += ((q.id * 2654435761 + h * 40503) % 1000) / 1000 * 2.5;     // a little chance, the same on every replay
      if (score > bs) { bs = score; best = q.id; }
    }
    if (best == null) return;
    this.subject = best; this.since = h;
    this.why = why || (speaking.has(best) ? "in conversation" : "at work");
    this.h.follow(best);
  }

  // a new hour: notable moments take the camera; the watched one, asleep or long watched, gives way
  hour(h) {
    if (!this.on) return;
    const s = this.s, moments = s.localEvents(h, h).filter(e => NOTABLE.has(e.kind) && e.who.length);
    for (const e of moments) this.feed.push({t: h, text: e.text});
    this.feed = this.feed.slice(-6);
    const m = moments.find(e => !e.who.includes(this.subject));
    if (m) {
      this.subject = m.who[0]; this.since = h; this.why = m.text;
      this.h.follow(m.who[0]);
      return;
    }
    const me = s.hour(h)?.people.get(this.subject);
    const asleep = me && (me.verb === "sleep" || (me.verb === "rest" && s.cal.of(h).night));
    if (!me || asleep || h - this.since >= HOLD) this.pick(h, "");
  }

  // at the newest hour: the last day again, while a newer world is awaited
  atEnd() {
    if (!this.on || this.endT) return;
    this.endT = setTimeout(async () => {
      this.endT = null;
      if (!(await this.newer())) { this.h.setT(Math.max(this.s.first, this.s.last - this.s.cal.tpd), true); this.h.setPlay(true); }
    }, 12000);
  }

  async newer() {
    try {
      const m = await (await fetch("manifest.json", {cache: "no-store"})).json();
      if (m.meta.last > this.s.last) {
        const q = new URLSearchParams(location.search);
        q.set("at", String(Math.floor(this.h.view.t >= this.s.last - 1 ? this.s.last : this.h.view.t)));
        location.href = location.pathname + "?" + q.toString() + "#tv";
        return true;
      }
    } catch (e) {}
    return false;
  }

  // the side panel, in large type
  render(storyLines, portrait) {
    if (!this.on) return;
    const s = this.s, t = this.h.view.t, w = s.cal.of(t), p = this.subject != null ? s.person(this.subject) : null;
    const living = s.living(t).length;
    const html = `<div class="tvwhen">Day ${w.day} · ${w.part}</div><div class="tvsub">${w.season}, year ${w.year} · ${living} living</div>
      ${p ? `<div class="tvwho">${portrait ? `<img class="face big" src="${portrait}" alt="">` : ""}<div><b>${esc(p.name)}</b>${s.isMind(p.id) ? " ✦" : ""}
        <div class="tvsub">${Math.floor(s.age(p.id, t))} years · ${esc(this.why)}</div></div></div>` : ""}
      <h3>Their story</h3><div class="tvfeed">${storyLines || '<div class="tvsub">…</div>'}</div>
      ${this.feed.length ? `<h3>In the land</h3><div class="tvnews">${this.feed.slice(-3).reverse().map(f => `<div>${esc(f.text)}</div>`).join("")}</div>` : ""}
      <div id="tvbar"><button class="pill" id="tvfull">Full screen (F)</button><button class="pill" id="tvexit">Leave TV (Esc)</button></div>`;
    if (html !== this.side.dataset.html) { this.side.innerHTML = html; this.side.dataset.html = html; }
  }
}
