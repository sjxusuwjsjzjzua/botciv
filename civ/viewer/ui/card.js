// The small card for what was picked on the land, as it was at t.
import {esc, pretty, goods, skillWord, doing} from "./text.js";

export function cardHtml(store, sel, t, followId) {
  if (sel.type === "person") {
    const p = store.personAt(sel.id, t);
    if (!p) return "";
    const nameOf = id => store.person(id)?.name ?? "someone";
    let h = `<h3>${esc(p.name)} ${store.isMind(p.id) ? '<span class="tag mind">✦ own mind</span>' : ""}</h3>`;
    h += `<div class="muted">${Math.floor(p.age)} years · ${esc(p.temperament)}</div>`;
    if (!p.alive) h += `<div>${p.died != null && p.died <= t ? `Died: ${esc(p.cause || "")}` : "Not yet born"}</div>`;
    if (p.now) h += `<div>${esc(doing(p.now, nameOf))} · health ${p.now.health} · fullness ${p.now.fullness}</div>`;
    if (p.day) {
      if (p.day.goal) h += `<div class="muted">Working toward: ${esc(p.day.goal)}</div>`;
      const top = Object.entries(p.day.skills).sort((a, b) => b[1] - a[1]).slice(0, 4);
      if (top.length) h += `<div>${top.map(([c, v]) => `${esc(pretty(c))} <span class="muted">${skillWord(v)}</span>`).join(" · ")}</div>`;
      h += `<div class="muted">Carries: ${esc(goods(p.day.inv) || "nothing")}</div>`;
    }
    h += `<div class="toolbar"><button class="btn" data-act="follow">${followId === p.id ? "Stop following" : "Follow"}</button>`
      + `<button class="btn" data-act="journal">Their journal page</button><button class="btn" data-act="close">Close</button></div>`;
    return h;
  }
  if (sel.type === "building") {
    const s = store.snapshot(t), b = s && s.buildings.find(q => q.id === sel.id);
    if (!b) return `<div class="toolbar"><button class="btn" data-act="close">Close</button></div>`;
    const owner = b.owner < 0 ? "a group" : store.person(b.owner)?.name ?? "no one";
    let h = `<h3>${esc(pretty(b.kind))}</h3><div class="muted">${b.done ? "" : "being built · "}owner: ${esc(owner)} · (${b.x},${b.y})</div>`;
    if (Object.keys(b.inv).length) h += `<div>Holds: ${esc(goods(b.inv))}</div>`;
    if (Object.keys(b.animals).length) h += `<div>Animals: ${esc(goods(b.animals))}</div>`;
    if (b.crop) h += `<div>Growing: ${esc(pretty(b.crop))}${b.growth?.ripe ? " (ripe)" : ""}</div>`;
    if (b.working) h += `<div>Working</div>`;
    return h + `<div class="toolbar"><button class="btn" data-act="close">Close</button></div>`;
  }
  const ter = store.cat.terrain[store.m.terrain[sel.y]?.[sel.x]]?.name ?? "land";
  const s = store.snapshot(t), d = s && s.deposits.find(q => q.x === sel.x && q.y === sel.y);
  let h = `<h3>${esc(d ? store.cat.deposits[d.kind]?.name ?? pretty(d.kind) : ter)}</h3><div class="muted">${esc(ter)} · (${sel.x},${sel.y})</div>`;
  if (d) h += `<div>${d.left} left to gather</div>`;
  return h + `<div class="toolbar"><button class="btn" data-act="close">Close</button></div>`;
}
