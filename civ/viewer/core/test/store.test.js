// The store against a site built by tests/test_civ_site.py (SITE=its folder).
import {test} from "node:test";
import assert from "node:assert/strict";
import {readFile} from "node:fs/promises";
import {join} from "node:path";
import {Store} from "../store.js";

const SITE = process.env.SITE;
const get = p => readFile(join(SITE, p), "utf8").then(JSON.parse);

test("opens a format 3 site", {skip: !SITE}, async () => {
  const s = await Store.open(SITE, get);
  assert.ok(s.last > s.first);
  assert.ok(s.people.size > 0);
});

test("every hour has its people, and the menus are at that hour", {skip: !SITE}, async () => {
  const s = await Store.open(SITE, get);
  for (const t of [s.first, Math.floor((s.first + s.last) / 2), s.last]) {
    await s.ensure(t);
    const h = s.hour(t);
    assert.ok(h, `hour ${t}`);
    assert.ok(h.t <= t);
    const living = s.living(t).map(p => p.id).sort((a, b) => a - b);
    const here = [...h.people.keys()].sort((a, b) => a - b);
    // who is in the hour's record is who is alive then (born before it, not yet dead)
    for (const id of here) assert.ok(s.alive(id, h.t), `${id} alive at ${h.t}`);
    assert.ok(living.length >= here.length - 1);
    const snap = s.snapshot(t);
    assert.ok(snap && (snap.t <= t || t < s.first + 12), "a snapshot at or before t (or the first, before any)");
    const p = s.personAt(here[0], t);
    assert.equal(p.now.id, here[0]);
    assert.ok(p.life.every(e => e[0] <= t), "a life told only up to t");
    assert.ok(s.eventsUpTo(t).every(e => e.t <= t), "nothing from after t");
    assert.ok(s.population(t).every(x => x[0] <= t));
  }
});

test("knowledge and groups at a moment", {skip: !SITE}, async () => {
  const s = await Store.open(SITE, get);
  await s.ensure(s.last);
  const k = s.knowledgeAt(s.last);
  assert.ok(Object.keys(k).length > 10);
  assert.ok(Object.values(k).some(c => c.able.length || c.masters.length));
  const g = s.groupsAt(s.last);
  assert.equal(g.exact, true);                 // snapshots v2 keep groups
  await s.ensure(s.first);
  assert.ok(Array.isArray(s.groupsAt(s.first).groups));
});

test("keeps only a few chunks in memory", {skip: !SITE}, async () => {
  const s = await Store.open(SITE, get);
  s.keep = 1;
  await s.ensure(s.first);
  await s.ensure(s.last);
  assert.ok(s.chunks.size <= 2);
});
