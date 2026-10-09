// The world at any moment: the only reader of the site's files (docs/viewer.md, section 2).
// Everything the scene and the menus show comes from here, for a time t (hours, may be fractional).
// Pure: no DOM; the fetcher is passed in, so it runs in Node for tests.
import * as S from "./schema.js";
import {Calendar} from "./time.js";

const lastAtOrBefore = (arr, t, key = x => x) => {
  // index of the last element whose key <= t, or -1
  let lo = 0, hi = arr.length - 1, best = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (key(arr[mid]) <= t) { best = mid; lo = mid + 1; } else hi = mid - 1;
  }
  return best;
};

export class Store {
  static async open(base, fetchJson) {
    const get = fetchJson || (p => fetch(`${base}/${p}`, {cache: "no-cache"}).then(r => {
      if (!r.ok) throw new Error(`${p}: ${r.status}`);
      return r.json();
    }));
    const [manifest, index] = await Promise.all([get("manifest.json"), get("index.json")]);
    if (manifest.format !== S.FORMAT) throw new Error(`this site is format ${manifest.format}; the viewer reads format ${S.FORMAT}`);
    return new Store(manifest, index, get);
  }

  constructor(manifest, index, get) {
    this.m = manifest;
    this.meta = manifest.meta;
    this.cal = new Calendar(manifest.meta);
    this.cat = manifest.catalogue;
    this.get = get;
    this.people = new Map(manifest.people.map(p => [p.id, p]));
    this.minds = new Set(manifest.minds);
    this.events = index.events.map(S.event);            // notable, whole history, by time
    this.pop = index.pop;
    this.era = index.era;
    this.places = index.places || {};
    this.realm = manifest.realm || null;           // the grand world: regions, their map, the peoples (else null)
    this.lastRun = index.last_run || "";
    this.history = index.history || [];       // the long record, a census a season (a land left to run long)
    this.chunks = new Map();                            // chunk number -> decoded chunk
    this.loading = new Map();                           // chunk number -> promise
    this.mindCache = new Map();
    this.keep = 6;                                      // chunks kept in memory
  }

  get first() { return this.meta.first; }
  get last() { return this.meta.last; }
  clamp(t) { return Math.max(this.first, Math.min(this.last, t)); }

  // ---------- chunks ----------
  chunkOf(t) { return Math.max(0, lastAtOrBefore(this.m.chunks, t, c => c[0])); }

  ensure(t) {
    const c = this.chunkOf(this.clamp(t));
    const p = this.load(c);
    if (c + 1 < this.m.chunks.length) this.load(c + 1);          // the next, ahead of need
    return p;
  }

  ready(t) { return this.chunks.has(this.chunkOf(this.clamp(t))); }

  load(c) {
    if (this.chunks.has(c)) return Promise.resolve(this.chunks.get(c));
    if (this.loading.has(c)) return this.loading.get(c);
    const p = this.get(this.m.chunks[c][2]).then(raw => {
      const ch = {
        t0: raw.t0, t1: raw.t1, hours: raw.hours, land: raw.land,
        events: raw.events.map(S.event), thoughts: (raw.thoughts || []).map(S.thought), decoded: new Map(),
      };
      this.chunks.set(c, ch);
      this.loading.delete(c);
      while (this.chunks.size > this.keep) {                     // forget the one furthest away
        const far = [...this.chunks.keys()].sort((a, b) => Math.abs(b - c) - Math.abs(a - c))[0];
        this.chunks.delete(far);
      }
      return ch;
    }).catch(e => { this.loading.delete(c); throw e; });
    this.loading.set(c, p);
    return p;
  }

  chunkAt(t) { return this.chunks.get(this.chunkOf(this.clamp(t))) || null; }

  // ---------- an hour: where everyone is and what they do ----------
  hour(t) {
    const ch = this.chunkAt(t);
    if (!ch) return null;
    const i = lastAtOrBefore(ch.hours, Math.floor(this.clamp(t)), h => h[0]);
    if (i < 0) return null;
    const key = "h" + i;
    if (!ch.decoded.has(key)) {
      const [ht, ps, hs, ks] = ch.hours[i];
      const people = new Map(ps.map(a => { const q = S.hourPerson(a); return [q.id, q]; }));
      ch.decoded.set(key, {t: ht, people, herds: hs.map(S.herd), packs: ks.map(S.pack)});
    }
    return ch.decoded.get(key);
  }

  // the hour after t's (for smooth motion between them), or null at the end
  nextHour(t) {
    const h = this.hour(t);
    return h && h.t + 1 <= this.last ? this.hour(h.t + 1) : null;
  }

  // ---------- a day: buildings, deposits, things, skills, groups ----------
  snapshot(t) {
    const ch = this.chunkAt(t);
    if (!ch || !ch.land.length) return null;
    // the day in force at t; before any was kept, the first one after it (snapshot.t > t says so)
    const i = Math.max(0, lastAtOrBefore(ch.land, this.clamp(t), l => l.t));
    const key = "l" + i;
    if (!ch.decoded.has(key)) {
      const l = ch.land[i];
      const people = new Map(Object.entries(l.people || {}).map(([id, a]) => [+id, S.snapPerson(a)]));
      ch.decoded.set(key, {
        t: l.t, v: l.v || 1,
        buildings: (l.b || []).map(S.building), deposits: (l.d || []).map(S.deposit),
        piles: l.g || {}, roads: l.r || [], people,
        groups: l.gr ? l.gr.map(S.group) : null, years: l.yr || null, trails: l.tr || [],
      });
    }
    return ch.decoded.get(key);
  }

  // ---------- people ----------
  person(id) { return this.people.get(id) || null; }
  isMind(id) { return this.minds.has(id) || this.person(id)?.mind === "llm"; }
  alive(id, t) { const p = this.person(id); return !!p && p.born <= t && (p.died == null || p.died > t); }
  age(id, t) { const p = this.person(id); return p ? Math.max(0, this.cal.years((p.died != null && p.died < t ? p.died : t) - p.born)) : 0; }
  living(t) { return [...this.people.values()].filter(p => this.alive(p.id, t)); }

  // everything known of a person at t
  personAt(id, t) {
    const p = this.person(id);
    if (!p) return null;
    const h = this.hour(t), s = this.snapshot(t);
    return {
      ...p, alive: this.alive(id, t), age: this.age(id, t),
      now: h ? h.people.get(id) || null : null,
      day: s ? s.people.get(id) || null : null,
      life: (p.life || []).filter(e => e[0] <= t),
    };
  }

  // ---------- what happened ----------
  eventsUpTo(t, {kinds = null, who = null, limit = 500} = {}) {
    const end = lastAtOrBefore(this.events, t, e => e.t);
    const out = [];
    for (let i = end; i >= 0 && out.length < limit; i--) {
      const e = this.events[i];
      if ((!kinds || kinds.has(e.kind)) && (who == null || e.who.includes(who))) out.push(e);
    }
    return out;                                          // newest first
  }

  // everyday doings (speech, making...) in the loaded chunk around t, within [t0, t1]
  localEvents(t0, t1) {
    const ch = this.chunkAt(t1);
    return ch ? ch.events.filter(e => e.t >= t0 && e.t <= t1) : [];
  }

  async thoughts(id, t) {
    if (!this.minds.has(id)) return [];
    if (!this.mindCache.has(id)) this.mindCache.set(id, this.get(`minds/${id}.json`).then(a => a.map(S.decision)).catch(() => []));
    const all = await this.mindCache.get(id);
    return all.filter(d => d.t <= t);
  }

  // ---------- measures and knowledge ----------
  upTo(series, t) { return series.slice(0, lastAtOrBefore(series, t, x => x[0]) + 1); }
  population(t) { return this.upTo(this.pop, t); }
  eras(t) { return this.upTo(this.era, t); }

  knowledgeAt(t) {
    const s = this.snapshot(t), crafts = this.cat.crafts;
    const firsts = {}, lost = {};
    for (const e of this.eventsUpTo(t, {kinds: new Set(["first", "craft_lost"]), limit: 1e9})) {
      const craft = e.data.craft;
      if (!craft) continue;
      if (e.kind === "first") firsts[craft] = e; else if (!(craft in lost)) lost[craft] = e;
    }
    const out = {};
    for (const [c, info] of Object.entries(crafts)) out[c] = {craft: c, ...info, masters: [], able: [], first: firsts[c] || null, lost: lost[c] || null};
    if (s) for (const [id, d] of s.people) for (const [c, v] of Object.entries(d.skills)) {
      if (!out[c]) continue;
      if (v >= 0.7) out[c].masters.push(id); else if (v >= 0.3) out[c].able.push(id);
    }
    return out;
  }

  // groups as they stood at t: from the day's snapshot, or (before snapshots kept them) pieced together
  // from what was told of their founding, joining and laws, and marked so
  groupsAt(t) {
    const s = this.snapshot(t);
    if (s && s.groups) return {exact: true, groups: s.groups.filter(g => g.founded <= t && (g.dissolved == null || g.dissolved > t))};
    const groups = new Map();
    const ev = this.eventsUpTo(t, {kinds: new Set(["group", "join", "law"]), limit: 1e9}).reverse();
    for (const e of ev) {
      const gid = e.data.group ?? null;
      if (e.kind === "group") {
        const name = e.text.replace(/^.*? founded /, "");
        groups.set(gid ?? name, {id: gid ?? name, name, leader: e.who[0], members: [e.who[0]], laws: [], founded: e.t, dissolved: null, dues: {}});
      } else {
        const g = groups.get(gid) || [...groups.values()].find(g => e.text.includes(g.name));
        if (!g) continue;
        if (e.kind === "join" && !g.members.includes(e.who[0])) g.members.push(e.who[0]);
        if (e.kind === "law") g.laws.push([e.t, e.text, !!e.data.written]);
      }
    }
    if (s) for (const g of groups.values()) g.members = g.members.filter(id => s.people.has(id));
    return {exact: false, groups: [...groups.values()]};
  }
}
