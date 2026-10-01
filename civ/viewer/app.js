// The viewer: one moment t drives the scene and every menu (docs/viewer.md).
import {Store} from "./core/store.js";
import {Journal} from "./ui/journal.js";
import {Timeline} from "./ui/timeline.js";
import {cardHtml} from "./ui/card.js";
import {esc} from "./ui/text.js";
import {Story} from "./ui/story.js";

const $ = s => document.querySelector(s);
const READY_3D = true;
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
  // the scene: 3D where it can run, else the map (both draw the same moment from the same store)
  const stage = $("#stage");
  const Scene = await pickScene();
  const scene = new Scene(stage, store);
  window.__scene = scene;                       // for tests and ?debug
  // a switch between the land in 3D and the map (the map for weak devices, or for an overview)
  const is3d = !(scene instanceof (await import("./scene/map2d.js")).Map2D);
  const sw = $("#viewswitch");
  sw.textContent = is3d ? "Map" : "3D";
  sw.onclick = () => { const q = new URLSearchParams(location.search); q.set("view", is3d ? "map" : "3d"); location.search = q.toString(); };

  const view = {t: store.last, playing: false, speed: "story", sel: null, follow: null, bubbles: [], emotes: [], lastHour: null};
  const story = new Story(store, $("#story"));
  const journal = new Journal($("#journal"), $("#page"), store, {
    jump: t => setT(t), select: sel => select(sel), follow: id => follow(id),
  });
  const timeline = new Timeline($("#scrub"), $("#marks"), store, t => setT(t, true));

  // header
  const meta = store.meta;
  if (meta.name || meta.links.length)
    $("#worlds").innerHTML = (meta.name ? `<b>${esc(meta.name)}</b>` : "") + meta.links.map(l => `<a href="${esc(l.href)}">${esc(l.name)}</a>`).join("");
  document.title = meta.name ? `${meta.name} · civ` : "civ";

  function setT(t, scrubbing = false) {
    view.t = store.clamp(t);
    if (scrubbing) { view.bubbles = []; view.emotes = []; story.clear(); }
    store.ensure(view.t).then(() => journal.refresh(view.t)).catch(() => {});
  }
  function select(sel) {
    view.sel = sel;
    if (sel && sel.type === "person") journal.openPerson(sel.id, view.t);
    showCard();
  }
  function follow(id) {
    view.follow = id;
    if (id != null) { scene.focus?.(id); view.sel = {type: "person", id}; showCard(); }
  }
  function showCard() {
    const el = $("#card");
    if (!view.sel) { el.hidden = true; return; }
    const html = cardHtml(store, view.sel, view.t, view.follow);
    if (html !== el.dataset.html) { el.innerHTML = html; el.dataset.html = html; }   // unchanged: leave it, so a click lands
    el.hidden = false;
  }
  $("#card").addEventListener("click", e => {
    const b = e.target.closest("[data-act]");
    if (!b) return;
    const act = b.dataset.act;
    if (act === "close") { view.sel = null; showCard(); }
    if (act === "follow") follow(view.follow === view.sel.id ? null : view.sel.id);
    if (act === "journal") { journal.openPerson(view.sel.id, view.t); journal.show(true); }
  });

  // names in the story lines open that person
  $("#story").addEventListener("click", e => {
    const a = e.target.closest("[data-person]");
    if (!a) return;
    e.preventDefault();
    select({type: "person", id: +a.dataset.person});
  });

  // pointer on the scene: pick what is there
  stage.addEventListener("pick", e => select(e.detail));
  stage.addEventListener("panned", () => { view.follow = null; });

  // controls
  const setPlay = on => { view.playing = on; $("#play").textContent = on ? "❚❚" : "▶"; $("#play").setAttribute("aria-label", on ? "Pause" : "Play"); };
  $("#play").onclick = () => { if (!view.playing && view.t >= store.last) setT(store.first); setPlay(!view.playing); };
  $("#speed").onchange = e => { view.speed = e.target.value === "story" ? "story" : +e.target.value; };
  $("#now").onclick = () => { setPlay(false); setT(store.last, true); };
  $("#jclose").onclick = () => journal.show(false);
  $("#jopen").onclick = () => journal.show(true);
  addEventListener("keydown", e => {
    if (e.target.matches("input, select, textarea")) return;
    if (e.key === " ") { e.preventDefault(); $("#play").click(); }
    if (e.key === "ArrowRight") setT(view.t + (e.shiftKey ? store.cal.tpd : 1), true);
    if (e.key === "ArrowLeft") setT(view.t - (e.shiftKey ? store.cal.tpd : 1), true);
    if (e.key === "Escape") { view.sel = null; showCard(); }
  });

  // the loop: time moves, the scene draws, the clock and menus follow
  let last = performance.now(), lastUi = 0;
  function loop(now) {
    const dt = Math.min(0.25, (now - last) / 1000);
    last = now;
    if (view.playing && store.ready(view.t)) {
      // story speed: each hour stays as long as what happens in it deserves; otherwise hours a second
      const rate = view.speed === "story" ? 1 / story.dwell(Math.floor(view.t), view.follow) : view.speed;
      view.t = Math.min(store.last, view.t + dt * rate);
      if (view.t >= store.last) setPlay(false);
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
        const storied = view.follow != null || view.speed === "story";
        if (storied) for (const m of story.hour(hr, view.follow)) {
          if (m.thought) view.bubbles.push({id: view.follow, text: m.thought, born: now, thought: true});
          // the world's story: the camera goes to each moment
          if (view.follow == null && view.playing && m.who?.length) scene.show?.(m.who[0]);
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
      const living = store.living(view.t).length, minds = store.living(view.t).filter(p => p.mind === "llm").length;
      const era = store.eras(view.t).at(-1)?.[1] ?? 0;
      $("#headline").innerHTML = `<b>${living}</b> living · ${minds} ✦ minds of their own · era ${era}`;
      timeline.show(view.t);
      journal.tick(view.t);
      if (view.sel) showCard();
      story.render(view.follow != null || (view.speed === "story" && view.playing));
    }
    requestAnimationFrame(loop);
  }
  await store.ensure(view.t);
  journal.refresh(view.t);
  requestAnimationFrame(loop);
}

async function pickScene() {
  // the 3D land is the default once it is whole (docs/viewer.md, section 10); until then ?view=3d
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
