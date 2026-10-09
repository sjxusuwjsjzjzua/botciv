// TV: the land as something to watch from the sofa (a tab cast to a television, or a screen left on).
// It is the viewer's own watching (app.js, docs/viewer.md section 7c) with the controls out of the way:
// it plays on its own at story speed, and a storyteller chooses whom to watch while you have not. Someone
// awake and doing something (those with minds of their own first, speaking or among others) is watched for
// a while, their story and thoughts told beside the picture; a notable moment elsewhere (a birth, a death,
// a blow, a first, a law...) takes the camera there. Whom you chose to follow stays followed until they
// die or you choose another. Pan the camera away and it comes back to the story by itself after a while.
// Anything can still be clicked: the card and the journal open over the picture as they do outside TV.
// Those you have followed are remembered on the device and chosen more often; one you follow who dies hands
// the watch to their family.
// At the newest hour it plays the last day again while it waits, looks for a newer world every two
// minutes, and carries on from where it was when one comes.
import {esc} from "./text.js";

const NOTABLE = new Set(["birth", "death", "pledge", "attack", "first", "monument", "group", "law", "craft_lost", "book", "steal",
  "fealty", "raid", "plunder", "repelled", "peace", "broke_peace", "captive"]);
const HOLD = 16;                 // hours one is watched before the storyteller looks for another
const STAY = 4;                  // hours at least before a moment elsewhere takes the camera away
const COME_BACK = 20000;         // ms without a touch before a camera moved away goes back to the story
const IDLE = 4000;               // ms without a touch before the controls fade

export class TV {
  constructor(store, side, hooks) {
    this.s = store; this.side = side; this.h = hooks;
    this.on = false; this.since = 0; this.feed = [];
    this.idleT = null; this.lock = null; this.poll = null; this.endT = null;
    side.addEventListener("click", e => {
      if (e.target.closest("#tvexit")) this.stop();
      else if (e.target.closest("#tvfull")) this.full();
      else if (e.target.closest("#tvjournal")) this.h.journal(true);
      else {
        const a = e.target.closest("[data-person]");
        if (a) { e.preventDefault(); this.h.select({type: "person", id: +a.dataset.person}); }
      }
    });
    addEventListener("keydown", e => {
      if (!this.on || e.target.matches?.("input, select, textarea")) return;
      if (e.key === "Escape" && !document.fullscreenElement) { e.preventDefault(); if (!this.h.closeOne()) this.stop(); }
      if (e.key === "f" || e.key === "F") this.full();
    });
    for (const ev of ["pointermove", "pointerdown", "keydown", "wheel"]) addEventListener(ev, () => this.on && this.awake(), {passive: true});
  }

  // watchId: someone you were already following (they stay followed)
  start(at = null, watchId = null) {
    const s = this.s, H = this.h;
    if (!this.on) this.journalWas = this.h.journal(false);     // the picture first; the journal a click away
    this.on = true;
    document.body.classList.add("tv");
    H.view.speed = "story";
    document.querySelector("#speed").value = "story";
    // from where it was asked; following someone, from where one is; else about a day before the newest hour
    const from = at != null ? at : watchId != null && H.view.t < s.last - 1 ? H.view.t : Math.max(s.first, s.last - s.cal.tpd);
    if (Math.abs(from - H.view.t) > 0.5) H.setT(from, true);
    this.feed = [];
    const h = Math.floor(H.view.t);
    if (watchId != null && s.alive(watchId, h)) { H.watch(watchId, "you"); this.since = h; }
    else this.pick(h, "");
    H.setPlay(true);
    this.awake();
    this.wake();
    clearInterval(this.poll);
    this.poll = setInterval(() => this.newer(), 120000);
    try { history.replaceState(null, "", location.pathname + location.search + "#tv"); } catch (e) {}
  }

  stop() {
    if (!this.on) return;
    this.on = false;
    document.body.classList.remove("tv", "idle");
    this.h.journal(!!this.journalWas);
    clearInterval(this.poll); clearTimeout(this.endT); clearTimeout(this.idleT); this.endT = null;
    if (this.lock) { this.lock.release().catch(() => {}); this.lock = null; }
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    // whom the storyteller chose is let go; whom you chose stays followed
    if (this.h.view.watch?.by !== "you") this.h.watch(null);
    try { history.replaceState(null, "", location.pathname + location.search); } catch (e) {}
  }

  full() {
    if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    else document.documentElement.requestFullscreen?.().catch(() => {});
  }

  async wake() { try { if (navigator.wakeLock) this.lock = await navigator.wakeLock.request("screen"); } catch (e) {} }

  // the cursor and the controls fade when nothing has moved for a while
  awake() {
    document.body.classList.remove("idle");
    clearTimeout(this.idleT);
    this.idleT = setTimeout(() => this.on && document.body.classList.add("idle"), IDLE);
  }

  // you chose whom to watch (and they are still alive): the storyteller keeps out of it. One you followed who has
  // died hands the watch to their family: a living child (the eldest), else a parent, else a brother or sister
  yours(h) {
    const w = this.h.view.watch;
    if (w && w.by === "you" && !this.s.alive(w.id, h)) {
      const kin = this.family(w.id, h);
      if (kin != null) { this.since = h; this.h.watch(kin, "you", `family of ${this.s.person(w.id)?.name || "the one you followed"}`); }
    }
    const now = this.h.view.watch;
    return now && now.by === "you" && this.s.alive(now.id, h);
  }

  family(id, h) {
    const s = this.s, me = s.person(id), living = s.living(h);
    const kids = living.filter(p => (p.parents || []).includes(id)).sort((a, b) => a.born - b.born);
    const parents = (me?.parents || []).filter(q => s.alive(q, h));
    const sibs = living.filter(p => p.id !== id && (p.parents || []).some(q => (me?.parents || []).includes(q)));
    return kids[0]?.id ?? parents[0] ?? sibs[0]?.id ?? null;
  }

  // those you have followed, remembered on this device: the storyteller turns to them more often
  favourites() {
    if (!this.favs) {
      try { this.favs = new Set(JSON.parse(localStorage.getItem(this.favKey()) || "[]")); } catch (e) { this.favs = new Set(); }
    }
    return this.favs;
  }
  favKey() { return "civ-favs:" + (this.s.meta.name || location.pathname); }
  remember(id) {
    const f = this.favourites();
    if (f.has(id)) return;
    f.add(id);
    try { localStorage.setItem(this.favKey(), JSON.stringify([...f].slice(-40))); } catch (e) {}
  }

  // who is worth watching in hour h: awake, doing something; minds of their own, speaking, among others
  pick(h, why) {
    const s = this.s, hour = s.hour(h);
    if (!hour || this.yours(h)) return;
    const was = this.h.view.watch?.id;
    const speaking = new Set(s.localEvents(h - 2, h).filter(e => e.kind === "say").map(e => e.who[0]));
    const night = s.cal.of(h).night, all = [...hour.people.values()];
    let best = null, bs = -1;
    for (const q of all) {
      if (q.id === was) continue;
      const asleep = q.verb === "sleep" || (q.verb === "rest" && night);
      if (asleep || !s.alive(q.id, h)) continue;
      let score = (s.isMind(q.id) ? 3 : 0) + (speaking.has(q.id) ? 3 : 0) + (q.verb && q.verb !== "wait" ? 1 : 0)
        + (this.favourites().has(q.id) ? 2.5 : 0);
      for (const o of all) if (o !== q && Math.abs(o.x - q.x) + Math.abs(o.y - q.y) <= 3) score += 0.4;
      score += ((q.id * 2654435761 + h * 40503) % 1000) / 1000 * 2.5;     // a little chance, the same on every replay
      if (score > bs) { bs = score; best = q.id; }
    }
    if (best == null) return;
    this.since = h;
    this.h.watch(best, "storyteller", why || (speaking.has(best) ? "in conversation" : "at work"));
  }

  // a new hour: notable moments take the camera; the watched one, asleep or long watched, gives way
  hour(h) {
    if (!this.on) return;
    const s = this.s, H = this.h, w = H.view.watch;
    if (w?.by === "you") this.remember(w.id);
    const moments = s.localEvents(h, h).filter(e => NOTABLE.has(e.kind) && e.who.length);
    for (const e of moments) this.feed.push({t: h, text: e.text, who: e.who[0]});
    this.feed = this.feed.slice(-6);
    // the camera moved away by hand: it stays there while hands are on it, then comes back to the story
    if (w?.lost) {
      if (performance.now() - H.view.touched < COME_BACK) return;
      H.back();
    }
    if (this.yours(h)) return;
    if (h - this.since >= STAY) {
      const m = moments.find(e => !e.who.includes(w?.id) && s.alive(e.who[0], h));
      if (m) { this.since = h; H.watch(m.who[0], "storyteller", m.text); return; }
    }
    const me = w && s.hour(h)?.people.get(w.id);
    const asleep = me && (me.verb === "sleep" || (me.verb === "rest" && s.cal.of(h).night));
    if (!me || !s.alive(w.id, h) || asleep || h - this.since >= HOLD) this.pick(h, "");
  }

  // at the newest hour: the last day again, while a newer world is awaited
  atEnd() {
    if (!this.on || this.endT) return;
    this.endT = setTimeout(async () => {
      this.endT = null;
      if (!this.on) return;
      if (!(await this.newer())) {
        this.h.setT(Math.max(this.s.first, this.s.last - this.s.cal.tpd), true);
        this.h.setPlay(true);
        if (!this.yours(Math.floor(this.h.view.t))) this.pick(Math.floor(this.h.view.t), "");
      }
    }, 12000);
  }

  async newer() {
    try {
      const m = await (await fetch("manifest.json", {cache: "no-store"})).json();
      if (m.meta.last > this.s.last) {
        const q = new URLSearchParams(location.search), v = this.h.view;
        q.delete("t");
        q.set("at", String(Math.floor(v.t >= this.s.last - 1 ? this.s.last : v.t)));
        if (v.watch?.by === "you") q.set("watch", String(v.watch.id)); else q.delete("watch");
        location.href = location.pathname + "?" + q.toString() + "#tv";
        return true;
      }
    } catch (e) {}
    return false;
  }

  // the side panel, in large type
  render(storyLines, portrait) {
    if (!this.on) return;
    const s = this.s, v = this.h.view, t = v.t, w = s.cal.of(t), p = v.watch ? s.person(v.watch.id) : null;
    const living = s.living(t).length;
    const why = v.watch?.by === "you" ? "followed by you" : v.watch?.why || "";
    const html = `<div class="tvwhen">Day ${w.day} · ${w.part}</div><div class="tvsub">${w.season}, year ${w.year} · ${living} living</div>
      ${p ? `<a class="tvwho" href="#" data-person="${p.id}">${portrait ? `<img class="face big" src="${portrait}" alt="">` : ""}<div><b>${esc(p.name)}</b>${s.isMind(p.id) ? " ✦" : ""}
        <div class="tvsub">${Math.floor(s.age(p.id, t))} years · ${esc(why)}</div></div></a>` : ""}
      <h3>Their story</h3><div class="tvfeed">${storyLines || '<div class="tvsub">…</div>'}</div>
      ${this.feed.length ? `<h3>In the land</h3><div class="tvnews">${this.feed.slice(-3).reverse().map(f => `<div><a href="#" data-person="${f.who}">${esc(f.text)}</a></div>`).join("")}</div>` : ""}
      <div id="tvbar"><button class="pill" id="tvjournal">Journal</button><button class="pill" id="tvfull">Full screen (F)</button><button class="pill" id="tvexit">Leave TV (Esc)</button></div>`;
    if (html !== this.side.dataset.html) { this.side.innerHTML = html; this.side.dataset.html = html; }
  }
}
