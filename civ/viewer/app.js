// The viewer: one moment t drives the scene and every menu (docs/viewer.md).
//
// Watching (section 7c): the heart of it is following someone. view.watch is whom we watch ({id, by:
// "you" or "storyteller", lost}); view.follow is whom the camera follows (the watched one, unless the
// camera was moved away: then a "Back to ..." button brings it back). Selecting anyone or anything opens
// its card and journal page without changing whom we watch. TV is the same, with the chrome out of the
// way; its storyteller only chooses when you have not.
import {Store} from "./core/store.js";
import {Journal} from "./ui/journal.js";
import {Timeline} from "./ui/timeline.js";
import {cardHtml} from "./ui/card.js";
import {esc} from "./ui/text.js";
import {Story} from "./ui/story.js";
import {TV} from "./ui/tv.js";

const $ = s => document.querySelector(s);
const READY_3D = true;
const IDLE_CAMERA = 15000;      // ms after the last touch before the world's story may move the camera
// little signs over heads for moments (the events' kinds)
const EMOTE = {pledge: "❤️", conceive: "💕", birth: "👶", skill: "✨", first: "🌟", steal: "❗", take_crop: "❗", attack: "💥",
  give: "🎁", teach: "📖", deal: "🤝", trade: "🤝", build: "🔨", monument: "🪨", tame: "🐾", hunt: "🍖", promise_broken: "💔"};

async function boot() {
  let store;
  try {
    store = await Store.open(".");
  } catch (e) {
    $("#clock").textContent = `This land could not be opened: ${e.message}`;
    return;
  }
  const url = new URLSearchParams(location.search);
  // the scene: 3D where it can run, else the map (both draw the same moment from the same store)
  const stage = $("#stage");
  const Scene = await pickScene();
  const scene = new Scene(stage, store);
  window.__scene = scene;                       // for tests and ?debug
  const is3d = !(scene instanceof (await import("./scene/map2d.js")).Map2D);

  const view = {t: store.last, playing: false, speed: "story", rate: 1, sel: null, follow: null, watch: null,
    bubbles: [], emotes: [], lastHour: null, touched: 0, now: 0};
  window.__view = view;                         // for tests
  const story = new Story(store, $("#story"));
  const journal = new Journal($("#journal"), $("#page"), store, {
    jump: t => setT(t, true), select: sel => select(sel), follow: id => { if (view.watch?.id === id) unwatch(); else watch(id); },
    watching: () => view.watch?.id ?? null,
    fly: (x, y) => { if (view.watch) unwatch(); scene.lookAt?.(x, y); },
  });
  if (is3d) { try { const {Portraits} = await import("./art/portrait.js"); journal.portraits = new Portraits(store); } catch (e) { console.warn("no portraits:", e); } }
  const tv = new TV(store, $("#tvside"), {view, setT: (t, s) => setT(t, s), setPlay: on => setPlay(on), watch: (id, by, why) => watch(id, by, why),
    back: () => back(), select: sel => select(sel), journal: on => { const was = !$("#journal").hidden; journal.show(on); return was; }, closeOne: () => closeOne()});
  const timeline = new Timeline($("#scrub"), $("#marks"), store, t => setT(t, true));

  // header
  const meta = store.meta;
  if (meta.name || meta.links.length)
    $("#worlds").innerHTML = (meta.name ? `<b>${esc(meta.name)}</b>` : "") + meta.links.map(l => `<a href="${esc(l.href)}">${esc(l.name)}</a>`).join("");
  document.title = meta.name ? `${meta.name} · civ` : "civ";

  // ---------- time ----------
  function setT(t, scrubbing = false) {
    view.t = store.clamp(t);
    if (scrubbing) { view.bubbles = []; view.emotes = []; story.clear(); view.lastHour = null; }
    store.ensure(view.t).then(() => journal.refresh(view.t)).catch(() => {});
  }
  const setPlay = on => { view.playing = on; $("#play").textContent = on ? "❚❚" : "▶"; $("#play").setAttribute("aria-label", on ? "Pause" : "Play"); };

  // ---------- watching and choosing ----------
  function watch(id, by = "you", why = "") {
    if (id == null) return unwatch();
    const again = view.watch && view.watch.id === id && !view.watch.lost;
    view.watch = {id, by, lost: false, why};
    view.follow = id;
    if (!again) scene.focus?.(id);
    if (by === "you") {
      view.sel = {type: "person", id};
      showCard();
      // to watch is to play: from a day back if we are at the newest hour, so there is something to see
      if (!view.playing) {
        if (view.t >= store.last - 1) setT(Math.max(store.first, store.last - store.cal.tpd), true);
        setPlay(true);
      }
    }
    backButton();
  }
  function unwatch() {
    view.watch = null; view.follow = null;
    backButton();
    showCard();
  }
  // the camera moved away by hand: the one watched stays watched (their story goes on), the camera is free
  function release() {
    if (view.watch && !view.watch.lost) { view.watch.lost = true; view.follow = null; backButton(); }
  }
  function back() {
    if (!view.watch) return;
    view.watch.lost = false; view.follow = view.watch.id;
    scene.focus?.(view.watch.id);
    backButton();
  }
  function backButton() {
    const b = $("#back"), w = view.watch;
    b.hidden = !(w && w.lost);
    if (w) b.innerHTML = `↩ Back to ${esc(store.person(w.id)?.name ?? "them")}<span class="x" data-x="1" aria-label="Stop following">×</span>`;
  }
  $("#back").addEventListener("click", e => { if (e.target.closest("[data-x]")) unwatch(); else back(); });

  function select(sel) {
    view.sel = sel;
    if (sel && sel.type === "person") journal.openPerson(sel.id, view.t);
    showCard();
  }
  // Escape: the card, else the journal (true if something was closed)
  function closeOne() {
    if (view.sel) { view.sel = null; showCard(); return true; }
    if (!$("#journal").hidden) { journal.show(false); return true; }
    return false;
  }
  function showCard() {
    const el = $("#card");
    if (!view.sel) { el.hidden = true; return; }
    const html = cardHtml(store, view.sel, view.t, view.watch?.id ?? null);
    if (html !== el.dataset.html) { el.innerHTML = html; el.dataset.html = html; }   // unchanged: leave it, so a click lands
    el.hidden = false;
  }
  $("#card").addEventListener("click", e => {
    const b = e.target.closest("[data-act]");
    if (!b) return;
    const act = b.dataset.act;
    if (act === "close") { view.sel = null; showCard(); }
    if (act === "follow") { if (view.watch?.id === view.sel.id) unwatch(); else watch(view.sel.id); }
    if (act === "journal") { journal.openPerson(view.sel.id, view.t); journal.show(true); }
  });
  // names in the story lines open that person
  $("#story").addEventListener("click", e => {
    const a = e.target.closest("[data-person]");
    if (!a) return;
    e.preventDefault();
    select({type: "person", id: +a.dataset.person});
  });

  // pointer on the scene: pick what is there; a hand on the camera holds off the world's story
  stage.addEventListener("pick", e => select(e.detail));
  stage.addEventListener("panned", () => release());
  for (const ev of ["pointerdown", "wheel"]) stage.addEventListener(ev, () => { view.touched = performance.now(); }, {passive: true});

  // ---------- controls ----------
  $("#play").onclick = () => { if (!view.playing && view.t >= store.last) setT(Math.max(store.first, store.last - store.cal.tpd), true); setPlay(!view.playing); };
  $("#speed").onchange = e => { view.speed = e.target.value === "story" ? "story" : +e.target.value; };
  $("#now").onclick = () => { setPlay(false); setT(store.last, true); };
  const MARKS = new Set(["birth", "death", "first", "attack", "monument", "group", "law", "pledge", "craft_lost", "book"]);
  const jumpMark = dir => {
    const t = Math.floor(view.t), ev = store.events;
    let best = null;
    for (const e of ev) if (MARKS.has(e.kind) && (dir > 0 ? e.t > t : e.t < t)) { if (dir > 0) { best = e; break; } best = e; }
    if (best) { setT(best.t, true); if (best.who.length && !view.follow) scene.show?.(best.who[0]); }
  };
  $("#prev").onclick = () => jumpMark(-1);
  $("#next").onclick = () => jumpMark(1);
  $("#tvgo").onclick = () => tv.start(null, view.watch?.by === "you" ? view.watch.id : null);
  // the map and the land in 3D: switching keeps one's place (the moment, whom one watches, TV)
  const placeUrl = extra => {
    const q = new URLSearchParams(location.search);
    q.set("t", String(Math.floor(view.t)));
    q.delete("at");
    if (view.watch) q.set("watch", String(view.watch.id)); else q.delete("watch");
    for (const [k, v] of Object.entries(extra)) q.set(k, v);
    return location.pathname + "?" + q.toString() + (tv.on ? "#tv" : "");
  };
  const sw = $("#viewswitch");
  sw.textContent = is3d ? "Map" : "3D";
  sw.onclick = () => { location.href = placeUrl({view: is3d ? "map" : "3d"}); };
  // where one stopped watching, remembered on this device (per land)
  const keyOf = "civ-watched:" + (store.meta.name || location.pathname);
  let saved = null;
  try { saved = +localStorage.getItem(keyOf) || null; } catch (e) {}
  if (saved && saved > store.first && saved < store.last - 2 && !url.get("t")) {
    $("#resume").hidden = false;
    $("#resume").onclick = () => { $("#resume").hidden = true; setT(saved, true); };
  }
  setInterval(() => { try { localStorage.setItem(keyOf, String(Math.floor(view.t))); } catch (e) {} }, 5000);
  // a newer world: offered, keeping one's place (TV takes it by itself)
  setInterval(async () => {
    if (tv.on) return;
    try {
      const m = await (await fetch("manifest.json", {cache: "no-store"})).json();
      if (m.meta.last > store.last) { $("#newer").hidden = false; $("#newer").onclick = () => { location.href = placeUrl({}); }; }
    } catch (e) {}
  }, 120000);
  $("#jclose").onclick = () => journal.show(false);
  $("#jopen").onclick = () => journal.show(true);
  addEventListener("keydown", e => {
    if (e.target.matches("input, select, textarea")) return;
    if (e.key === " ") { e.preventDefault(); $("#play").click(); }
    if (e.key === "ArrowRight") setT(view.t + (e.shiftKey ? store.cal.tpd : 1), true);
    if (e.key === "ArrowLeft") setT(view.t - (e.shiftKey ? store.cal.tpd : 1), true);
    if (e.key === "Escape" && !tv.on && !e.defaultPrevented) closeOne();
    if (e.key === "[") jumpMark(-1);
    if (e.key === "]") jumpMark(1);
    if ((e.key === "b" || e.key === "B") && view.watch?.lost) back();
  });

  // ---------- the loop: time moves, the scene draws, the clock and menus follow ----------
  let last = performance.now(), lastUi = 0;
  function loop(now) {
    const dt = Math.min(0.25, (now - last) / 1000);
    last = now;
    const subject = view.watch?.id ?? null;
    if (view.playing && store.ready(view.t)) {
      // story speed: each hour stays as long as what happens in it deserves (the pace changes gently)
      const want = view.speed === "story" ? 1 / story.dwell(Math.floor(view.t), subject) : view.speed;
      view.rate += (want - view.rate) * Math.min(1, dt * (want < view.rate ? 6 : 2));
      view.t = Math.min(store.last, view.t + dt * view.rate);
      if (view.t >= store.last) {
        setPlay(false);
        if (tv.on) tv.atEnd();
        else if (view.watch) story.note(view.t, "Caught up with the present: more comes as the world goes on.");
      }
      store.ensure(view.t);
    }
    // a new hour: its speech rises over the speakers, and its story is told
    const hr = Math.floor(view.t);
    if (hr !== view.lastHour) {
      if (view.lastHour != null && hr === view.lastHour + 1) {
        for (const e of store.localEvents(hr, hr)) {
          if (e.kind === "say" && e.who.length) view.bubbles.push({id: e.who[0], text: e.text.replace(/^[^:]+: /, ""), born: now});
          const icon = EMOTE[e.kind];
          if (icon && e.who.length) {
            view.emotes.push({id: e.who[0], icon, born: now});
            if (e.kind === "attack" && e.who[1] != null) view.emotes.push({id: e.who[1], icon: "💢", born: now});
            if ((e.kind === "pledge" || e.kind === "deal" || e.kind === "teach") && e.who[1] != null) view.emotes.push({id: e.who[1], icon, born: now});
          }
        }
        tv.hour(hr);                          // TV's storyteller (only when you have not chosen)
        const sub = view.watch?.id ?? null;
        if (sub != null || view.speed === "story") for (const m of story.hour(hr, sub)) {
          if (m.thought) view.bubbles.push({id: sub, text: m.thought, born: now, thought: true});
          // the world's story: the camera goes to each moment, unless a hand is on it
          if (sub == null && view.playing && m.who?.length && (tv.on || now - view.touched > IDLE_CAMERA)) scene.show?.(m.who[0]);
        }
        // the one watched has died: the storyteller (TV) or nobody takes over
        if (view.watch && !store.alive(view.watch.id, hr)) {
          story.note(hr, `${esc(store.person(view.watch.id)?.name ?? "They")} is gone.`);
          if (tv.on) tv.pick(hr, ""); else unwatch();
        }
      }
      view.lastHour = hr;
    }
    view.bubbles = view.bubbles.filter(b => now - b.born < 4500).slice(-10);
    view.emotes = view.emotes.filter(b => now - b.born < 2600).slice(-24);
    view.now = now;
    scene.frame(view, dt);
    if (now - lastUi > 200) {
      lastUi = now;
      $("#clock").textContent = store.cal.label(view.t);
      const living = store.living(view.t), minds = living.filter(p => p.mind === "llm").length;
      const era = store.eras(view.t).at(-1)?.[1] ?? 0;
      $("#headline").innerHTML = `<b>${living.length}</b> living · ${minds} ✦ minds of their own · era ${era}`;
      timeline.show(view.t);
      journal.tick(view.t);
      if (view.sel) showCard();
      story.render(!tv.on && (view.watch != null || (view.speed === "story" && view.playing)));
      tv.render(story.linesHtml(), view.watch ? journal.portraits?.of(view.watch.id, view.t) : null);
    }
    requestAnimationFrame(loop);
  }

  // ---------- start: from the place in the address, if any ----------
  const at = +url.get("t") || +url.get("at") || null;
  if (at) setT(at, true);
  await store.ensure(view.t);
  journal.refresh(view.t);
  requestAnimationFrame(loop);
  const w = +url.get("watch");
  if (location.hash === "#tv") tv.start(at, w || null);
  else if (w && store.person(w)) { watch(w); }
}

async function pickScene() {
  const want = new URLSearchParams(location.search).get("view") || (READY_3D ? "3d" : "map");
  if (want === "3d") {
    try {
      const gl = document.createElement("canvas").getContext("webgl2");
      if (gl) {
        const m = await import("./scene/world3d.js");
        if (m.World3D) return m.World3D;
      }
    } catch (e) { console.warn("3D view unavailable, using the map:", e); }
  }
  return (await import("./scene/map2d.js")).Map2D;
}

boot();
