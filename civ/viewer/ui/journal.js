// The journal: every page shows the world as it was at t (docs/viewer.md, section 8).
import {esc, pretty, goods, skillWord, doing} from "./text.js";

const ERAS = ["Foraging", "The first farmers", "Bronze", "Iron", "Learning"];
const KINDS = {
  "Lives": ["birth", "death", "pledge", "conceive"], "Crafts": ["first", "skill", "craft_lost", "teach", "book", "write"],
  "Building": ["build", "monument", "worked_out", "library", "claim"], "Dealings": ["deal", "trade", "promise_kept", "promise_broken", "hire", "deed", "sign"],
  "Groups and law": ["group", "join", "law", "place"], "Strife": ["attack", "steal", "take_crop"], "Land and beasts": ["hunt", "tame"],
};

export class Journal {
  constructor(root, page, store, hooks) {
    this.root = root; this.page = page; this.store = store; this.hooks = hooks;
    this.tab = "people"; this.personId = null; this.q = ""; this.filter = "alive"; this.kinds = null; this.mindsOnly = false;
    this.key = null;
    root.querySelectorAll(".tabs [data-tab]").forEach(b => b.onclick = () => this.go(b.dataset.tab));
    page.addEventListener("click", e => this.click(e));
    page.addEventListener("input", e => this.input(e));
    page.addEventListener("change", e => this.input(e));
    this.show(!matchMedia("(max-width: 700px)").matches);
  }

  show(on) {
    this.root.hidden = !on;
    document.querySelector("#jopen").hidden = on;
    if (on && this.t != null) { this.html = null; this.refresh(this.t); }    // it does not draw while closed: draw now
  }
  go(tab) {
    this.tab = tab;
    this.root.querySelectorAll(".tabs [data-tab]").forEach(b => b.setAttribute("aria-selected", b.dataset.tab === tab));
    this.page.scrollTop = 0;
    this.refresh(this.t ?? this.store.last);
  }
  openPerson(id, t) {
    this.personId = id;
    const b = this.root.querySelector('[data-tab="person"]');
    b.hidden = false; b.textContent = this.store.person(id)?.name ?? "Person";
    this.t = t; this.go("person");
  }

  // called often while time moves: redraw only when what the page shows has changed
  tick(t) {
    const s = this.store, snap = s.snapshot(t);
    const key = [this.tab, snap?.t, s.eventsUpTo(t, {limit: 1})[0]?.t, this.tab === "person" ? Math.floor(t) : 0, this.hooks.watching?.()].join("|");
    if (key !== this.key) this.refresh(t);
  }

  refresh(t) {
    this.t = t;
    const s = this.store, snap = s.snapshot(t);
    this.key = [this.tab, snap?.t, s.eventsUpTo(t, {limit: 1})[0]?.t, this.tab === "person" ? Math.floor(t) : 0, this.hooks.watching?.()].join("|");
    if (this.root.hidden) return;
    const keepFocus = document.activeElement?.id;
    const html = this[this.tab](t, snap);
    if (html != null && html !== this.html) { this.page.innerHTML = html; this.html = html; }
    if (keepFocus) { const el = this.page.querySelector("#" + keepFocus); if (el) { el.focus(); if (el.setSelectionRange) el.setSelectionRange(el.value.length, el.value.length); } }
  }

  name(id) { return esc(this.store.person(id)?.name ?? "someone"); }
  // a portrait (when the 3D figures are at hand), else a soft disc of the person's colour
  face(id, t, big = false) {
    const url = this.portraits?.of(id, t);
    return url ? `<img class="face${big ? " big" : ""}" src="${url}" alt="">` : `<span class="face${big ? " big" : ""} disc"></span>`;
  }
  link(id) { return `<a href="#" data-person="${id}">${this.name(id)}</a>`; }
  when(t) { const w = this.store.cal.of(t); return `day ${w.day}, ${w.season} of year ${w.year}`; }

  // ---------- pages ----------
  people(t, snap) {
    const s = this.store, q = this.q.toLowerCase();
    let rows = [...s.people.values()].filter(p => p.born <= t);
    if (this.filter === "alive") rows = rows.filter(p => s.alive(p.id, t));
    if (this.filter === "dead") rows = rows.filter(p => !s.alive(p.id, t));
    if (this.mindsOnly) rows = rows.filter(p => s.isMind(p.id));
    if (q) rows = rows.filter(p => p.name.toLowerCase().includes(q));
    rows.sort((a, b) => (s.alive(b.id, t) - s.alive(a.id, t)) || (s.isMind(b.id) - s.isMind(a.id)) || a.name.localeCompare(b.name));
    const shown = rows.slice(0, 300);
    return `<div class="toolbar"><input type="search" id="pq" placeholder="Find someone" value="${esc(this.q)}">
      <select id="pf" class="btn"><option value="alive"${this.filter === "alive" ? " selected" : ""}>living</option><option value="dead"${this.filter === "dead" ? " selected" : ""}>the dead</option><option value="all"${this.filter === "all" ? " selected" : ""}>everyone</option></select>
      <label class="muted"><input type="checkbox" id="pm"${this.mindsOnly ? " checked" : ""}> ✦ only</label></div>
      <div class="muted">${rows.length} ${this.filter === "dead" ? "dead" : this.filter === "alive" ? "living" : "people"} at ${this.when(t)}</div>
      ${shown.map((p, i) => {
        const d = snap?.people.get(p.id), alive = s.alive(p.id, t);
        const top = d ? Object.entries(d.skills).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([c, v]) => `${pretty(c)}${v >= .7 ? " ★" : ""}`).join(", ") : "";
        return `<div class="row${alive ? "" : " dead"}" data-person="${p.id}">${i < 60 ? this.face(p.id, t) : ""}<b>${esc(p.name)}</b> ${s.isMind(p.id) ? '<span class="tag mind">✦</span>' : ""}
          <span class="muted">${Math.floor(s.age(p.id, t))}${alive ? "" : ` · ${esc(p.cause || "died")}`}</span>
          ${top ? `<div class="muted">${esc(top)}</div>` : ""}${d?.goal ? `<div><i>${esc(d.goal)}</i></div>` : ""}</div>`;
      }).join("")}${rows.length > shown.length ? `<div class="muted">and ${rows.length - shown.length} more; search to find them</div>` : ""}`;
  }

  person(t, snap) {
    const s = this.store, id = this.personId, p = id != null ? s.personAt(id, t) : null;
    if (!p) return `<p class="muted">Pick someone on the land or in People.</p>`;
    if (p.born > t) return `<h2>${esc(p.name)}</h2><p class="muted">Not yet born at ${this.when(t)}; born ${this.when(p.born)}.</p>
      <button class="btn" data-jump="${p.born}">Go to their birth</button>`;
    const d = p.day, nameOf = i => s.person(i)?.name ?? "someone";
    const kids = [...s.people.values()].filter(c => c.parents?.includes(id) && c.born <= t);
    const groups = d ? s.groupsAt(t).groups.filter(g => g.members.includes(id)) : [];
    let h = `${this.face(id, t, true)}<h2>${esc(p.name)} ${s.isMind(id) ? '<span class="tag mind">✦ own mind</span>' : ""}</h2>
      <div class="muted">${Math.floor(p.age)} years · ${esc(p.temperament)}${p.wants ? ` · wants ${esc(p.wants)}` : ""}</div>`;
    if (p.self) h += `<div class="quote">${esc(p.self)}</div>`;
    if (!p.alive) h += `<div class="note">Died ${this.when(p.died)}: ${esc(p.cause || "")}</div>`;
    else if (p.now) h += `<div>${esc(doing(p.now, nameOf))}</div><div class="chips"><span class="tag">health ${p.now.health}</span><span class="tag">fullness ${p.now.fullness}</span></div>`;
    h += `<div class="toolbar"><button class="btn" data-follow="${id}">${this.hooks.watching?.() === id ? "Stop following" : "Follow on the land"}</button><button class="btn" data-jump="${p.born}">Their birth</button>${p.died != null ? `<button class="btn" data-jump="${p.died}">Their death</button>` : ""}</div>`;
    h += `<h3>Family</h3><div>${p.parents?.length ? "Child of " + p.parents.map(i => this.link(i)).join(" and ") : "Of the first people"}</div>`;
    if (d?.partner) h += `<div>Partner: ${this.link(d.partner)}</div>`;
    if (kids.length) h += `<div>Children: ${kids.map(c => this.link(c.id)).join(", ")}</div>`;
    if (groups.length) h += `<div>Belongs to ${groups.map(g => `<b>${esc(g.name)}</b>${g.leader === id ? " (leads it)" : ""}`).join(", ")}</div>`;
    if (d) {
      if (d.goal) h += `<h3>Working toward</h3><div>${esc(d.goal)}</div>`;
      const sk = Object.entries(d.skills).sort((a, b) => b[1] - a[1]);
      if (sk.length) h += `<h3>Crafts</h3>${sk.map(([c, v]) => `<div>${esc(pretty(c))} <span class="muted">${skillWord(v)}</span><div class="bar"><i style="width:${Math.round(v * 100)}%"></i></div></div>`).join("")}`;
      h += `<h3>Carries</h3><div>${esc(goods(d.inv) || "nothing")}</div>`;
      const owns = snap ? snap.buildings.filter(b => b.owner === id) : [];
      if (owns.length) h += `<h3>Owns</h3><div>${owns.map(b => `${esc(pretty(b.kind))} <span class="muted">(${b.x},${b.y})</span>`).join(", ")}</div>`;
    }
    if (p.life.length) h += `<h3>Their life</h3>${p.life.slice(-12).reverse().map(([lt, text]) => `<div class="row" data-jump="${lt}"><span class="muted">${this.when(lt)}</span> ${esc(text)}</div>`).join("")}`;
    const ev = s.eventsUpTo(t, {who: id, limit: 15});
    if (ev.length) h += `<h3>Lately</h3>${ev.map(e => `<div class="row" data-jump="${e.t}"><span class="muted">${this.when(e.t)}</span> ${esc(e.text)}</div>`).join("")}`;
    if (s.isMind(id)) {
      h += `<h3>Their thoughts</h3><div id="thoughts" class="muted">…</div>`;
      s.thoughts(id, t).then(ds => {
        const el = this.page.querySelector("#thoughts");
        if (!el || this.personId !== id) return;
        el.classList.remove("muted");
        el.innerHTML = ds.slice(-8).reverse().map(x => `<div class="row" data-jump="${x.t}"><span class="muted">${this.when(x.t)}</span>
          <div class="quote">${esc(x.thought)}</div>${x.goal ? `<div class="muted">Goal: ${esc(x.goal)}</div>` : ""}${x.say ? `<div>Said: “${esc(x.say)}”</div>` : ""}</div>`).join("") || "None yet.";
      });
    }
    return h;
  }

  knowledge(t) {
    const k = this.store.knowledgeAt(t);
    return `<p class="muted">What is known at ${this.when(t)}: who is a master (★) or able at each craft, when it was first practised, and what was lost.</p>` +
      craftTree(k) +
      ERAS.map((name, e) => {
        const cs = Object.values(k).filter(c => c.era === e);
        const known = cs.filter(c => c.masters.length || c.able.length).length;
        return `<h3>${e}. ${name} <span class="muted">${known}/${cs.length}</span></h3>` + cs.map(c => `<div class="row" ${c.first ? `data-jump="${c.first.t}"` : ""}>
          <b>${esc(pretty(c.craft))}</b> <span class="muted">${esc(c.does)}</span><br>
          ${c.masters.length ? "★ " + c.masters.slice(0, 6).map(i => this.name(i)).join(", ") + (c.masters.length > 6 ? ` +${c.masters.length - 6}` : "") : ""}
          ${c.able.length ? `<span class="muted">able: ${c.able.length}</span>` : ""}${!c.masters.length && !c.able.length ? '<span class="muted">no one yet</span>' : ""}
          ${c.first ? ` · <span class="muted">first ${this.when(c.first.t)}</span>` : ""}${c.lost ? ` · <b style="color:var(--bad)">lost ${this.when(c.lost.t)}</b>` : ""}</div>`).join("");
      }).join("");
  }

  groups(t) {
    const {exact, groups} = this.store.groupsAt(t);
    const g = groups.sort((a, b) => b.members.length - a.members.length);
    return (exact ? "" : `<div class="note">Groups were not yet recorded day by day here; this is pieced together from what was told of them.</div>`) +
      `<div class="muted">${g.length} groups at ${this.when(t)}</div>` +
      g.map(x => `<div class="row"><b>${esc(x.name)}</b> <span class="muted">${x.members.length} member${x.members.length === 1 ? "" : "s"} · led by ${this.name(x.leader)}${x.decide === "vote" ? " · decides by vote" : ""}</span>
        ${Object.keys(x.dues || {}).length ? `<div>Dues: ${esc(goods(x.dues))} a season</div>` : ""}
        ${x.rules ? `<div class="muted">${esc(x.rules)}</div>` : ""}
        ${(x.laws || []).map(l => `<div class="quote">${esc(l[1])}</div>`).join("")}
        <div class="chips">${x.members.slice(0, 24).map(i => `<a href="#" class="tag" data-person="${i}">${this.name(i)}</a>`).join("")}</div></div>`).join("");
  }

  chronicle(t) {
    const s = this.store;
    const kinds = this.kinds ? new Set(KINDS[this.kinds]) : null;
    let ev = s.eventsUpTo(t, {kinds, limit: this.mindsOnly ? 2000 : 300});
    if (this.mindsOnly) ev = ev.filter(e => e.who.some(i => s.isMind(i))).slice(0, 300);
    return `<div class="toolbar"><select id="ck" class="btn"><option value="">everything</option>${Object.keys(KINDS).map(k => `<option${this.kinds === k ? " selected" : ""}>${k}</option>`).join("")}</select>
      <label class="muted"><input type="checkbox" id="pm"${this.mindsOnly ? " checked" : ""}> ✦ only</label></div>` +
      ev.map(e => `<div class="row" data-jump="${e.t}"><span class="muted">${this.when(e.t)}</span><br>${esc(e.text)}</div>`).join("") ||
      `<p class="muted">Nothing yet.</p>`;
  }

  measures(t) {
    const s = this.store, pop = s.pop, era = s.era;
    const deaths = {};
    for (const e of s.eventsUpTo(t, {kinds: new Set(["death"]), limit: 1e9})) {
      const c = (e.data.cause || e.text.replace(/^.*?\(/, "").replace(/\).*$/, "")).split(" by ")[0];
      deaths[c] = (deaths[c] || 0) + 1;
    }
    return `<h3>People</h3>${chart(pop, s, t)}<h3>Era reached</h3>${chart(era, s, t, 4)}
      <h3>Deaths up to now</h3>${Object.entries(deaths).sort((a, b) => b[1] - a[1]).map(([c, n]) => `<div>${esc(c)}: <b>${n}</b></div>`).join("") || '<p class="muted">None yet.</p>'}` +
      this.longRun();
  }

  // the long record of a land left to run: every season since it began, not only the hours kept
  longRun() {
    const h = this.store.history;
    if (!h.length) return "";
    const first = h[0], last = h.at(-1);
    const series = k => h.map(x => [x.t, x[k] ?? 0]);
    const deaths = {};
    for (const x of h) for (const [c, n] of Object.entries(x.deaths || {})) deaths[c] = (deaths[c] || 0) + n;
    const births = h.reduce((a, x) => a + (x.births || 0), 0);
    const marks = h.filter(x => (x.firsts || []).length || (x.lost || []).length).slice(-40).reverse()
      .map(x => `<div><span class="muted">year ${x.year}, ${esc(x.season)}</span> ${(x.firsts || []).map(c => `first able at ${esc(c.replace(/_/g, " "))}`).concat((x.lost || []).map(c => `<i>${esc(c.replace(/_/g, " "))} lost</i>`)).join("; ")}</div>`).join("");
    return `<h3>The long run: year ${first.year} to ${last.year}</h3>
      <p class="muted">${h.length} seasons recorded. ${births} born, ${Object.values(deaths).reduce((a, n) => a + n, 0)} died, ${last.ever} have lived.</p>
      <h4>People</h4>${spanChart(series("alive"))}<h4>Era reached</h4>${spanChart(series("era"), 4)}
      <h4>Crafts known</h4>${spanChart(series("able"))}<h4>Buildings standing</h4>${spanChart(series("buildings"))}
      <h4>Groups</h4>${spanChart(series("groups"))}<h4>Wild beasts</h4>${spanChart(series("beasts"))}
      <h4>Inequality of goods (Gini)</h4>${spanChart(series("gini"), 1)}
      <h4>Deaths over the whole run</h4>${Object.entries(deaths).sort((a, b) => b[1] - a[1]).map(([c, n]) => `<div>${esc(c)}: <b>${n}</b></div>`).join("") || '<p class="muted">None.</p>'}
      <h4>Crafts first reached and lost</h4>${marks || '<p class="muted">None yet.</p>'}`;
  }

  about() {
    return `<p>A land where people live, work, trade, learn crafts from one another and build what they choose. Those marked ✦ think for
      themselves with a language model; the rest are simpler minds living the same life by the same rules. Nothing that happens is scripted.</p>
      <p class="muted">Everything in this journal is shown as it was at the moment the land below is showing. Press Now for the present.</p>
      <pre style="white-space:pre-wrap;font-size:12px">${esc(this.store.lastRun)}</pre>`;
  }

  // ---------- input ----------
  click(e) {
    const a = e.target.closest("[data-person],[data-jump],[data-follow]");
    if (!a) return;
    e.preventDefault();
    if (a.dataset.person) { this.openPerson(+a.dataset.person, this.t); this.hooks.select({type: "person", id: +a.dataset.person}); }
    else if (a.dataset.follow) this.hooks.follow(+a.dataset.follow);
    else if (a.dataset.jump) this.hooks.jump(+a.dataset.jump);
  }
  input(e) {
    const id = e.target.id;
    if (id === "pq") this.q = e.target.value;
    else if (id === "pf") this.filter = e.target.value;
    else if (id === "pm") this.mindsOnly = e.target.checked;
    else if (id === "ck") this.kinds = e.target.value || null;
    else return;
    this.refresh(this.t);
  }
}

// the crafts as a tree: one column an era, a line from each craft to those it opens, each craft coloured
// by how it stands at the moment shown (masters gold, able green, no one yet hollow, lost red)
function craftTree(k) {
  const cs = Object.values(k), cols = [0, 1, 2, 3, 4].map(e => cs.filter(c => c.era === e));
  const rowH = 22, colW = 124, H = Math.max(...cols.map(c => c.length)) * rowH + 12, W = colW * 5;
  const at = {};
  cols.forEach((col, e) => col.forEach((c, i) => { at[c.craft] = [e * colW + 6, 8 + i * rowH]; }));
  const lines = [];
  for (const c of cs) for (const pre of Object.keys(c.pre || {})) {
    const a = at[pre], b = at[c.craft];
    if (!a || !b) continue;
    const x1 = a[0] + 112, y1 = a[1] + 8, x2 = b[0], y2 = b[1] + 8, mx = (x1 + x2) / 2;
    lines.push(`<path d="M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}" fill="none" stroke="var(--muted)" stroke-opacity=".45" stroke-width="1"/>`);
  }
  const nodes = cs.map(c => {
    const [x, y] = at[c.craft];
    const state = c.lost && !c.masters.length && !c.able.length ? "lost" : c.masters.length ? "master" : c.able.length ? "able" : "none";
    const fill = {master: "#d9a441", able: "#6fae4a", lost: "var(--bad)", none: "transparent"}[state];
    const ink = state === "none" ? "var(--muted)" : "#fff";
    const n = c.masters.length + c.able.length;
    return `<g${c.first ? ` data-jump="${c.first.t}" style="cursor:pointer"` : ""}><title>${esc(pretty(c.craft))}: ${c.masters.length} masters, ${c.able.length} able${c.lost ? ", lost once" : ""}</title>
      <rect x="${x}" y="${y}" width="112" height="16" rx="8" fill="${fill}" stroke="${state === "none" ? "var(--muted)" : fill}" stroke-opacity="${state === "none" ? ".5" : "1"}"/>
      <text x="${x + 8}" y="${y + 12}" font-size="10" fill="${ink}">${esc(pretty(c.craft)).slice(0, 15)}${n ? ` · ${n}` : ""}</text></g>`;
  });
  return `<div class="tree" style="overflow-x:auto"><svg viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" role="img" aria-label="the crafts as a tree">
    ${lines.join("")}${nodes.join("")}</svg>
    <div class="muted" style="font-size:12px">● gold: masters · ● green: able · ○ no one yet · ● red: lost · the number is how many know it</div></div>`;
}

// a line over the series' own span (the long run), with its last value marked
function spanChart(series, max) {
  if (series.length < 2) return '<p class="muted">Not yet.</p>';
  const W = 600, H = 120, t0 = series[0][0], t1 = Math.max(t0 + 1, series.at(-1)[0]);
  const m = max || Math.max(...series.map(p => p[1])) || 1;
  const X = x => ((x - t0) / (t1 - t0) * W).toFixed(1), Y = y => (H - 6 - y / m * (H - 18)).toFixed(1);
  const d = series.map((p, i) => `${i ? "L" : "M"}${X(p[0])},${Y(p[1])}`).join("");
  const now = series.at(-1);
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="now ${now[1]}">
    <path d="${d}" fill="none" stroke="var(--accent)" stroke-width="2.5" vector-effect="non-scaling-stroke"/>
    <text x="4" y="12" font-size="11" fill="var(--muted)">${m}</text><text x="${W - 40}" y="${Math.max(12, +Y(now[1]) - 4)}" font-size="12" fill="var(--ink)">${now[1]}</text></svg>`;
}

// a line over the whole span, drawn up to t, with a mark at t
function chart(series, s, t, max) {
  if (!series.length) return '<p class="muted">Not yet.</p>';
  const W = 600, H = 120, t0 = s.first, t1 = Math.max(s.first + 1, s.last), m = max || Math.max(...series.map(p => p[1])) || 1;
  const X = x => ((x - t0) / (t1 - t0) * W).toFixed(1), Y = y => (H - 6 - y / m * (H - 18)).toFixed(1);
  const upto = series.filter(p => p[0] <= t);
  const d = upto.map((p, i) => `${i ? "L" : "M"}${X(p[0])},${Y(p[1])}`).join("");
  const now = upto.at(-1);
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" role="img" aria-label="up to ${now ? now[1] : 0}">
    <path d="${d}" fill="none" stroke="var(--accent)" stroke-width="2.5" vector-effect="non-scaling-stroke"/>
    <line x1="${X(t)}" x2="${X(t)}" y1="0" y2="${H}" stroke="var(--muted)" stroke-dasharray="3 3" vector-effect="non-scaling-stroke"/>
    <text x="4" y="12" font-size="11" fill="var(--muted)">${m}</text>${now ? `<text x="${Math.min(W - 40, +X(now[0]) + 4)}" y="${Math.max(12, +Y(now[1]) - 4)}" font-size="12" fill="var(--ink)">${now[1]}</text>` : ""}</svg>`;
}
