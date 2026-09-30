"""Build the static viewer (site/index.html + site/data.json) from a world directory.

    python -m botciv.site --dir world --out site
"""
import argparse
import glob
import json
import os

from . import items as I
from .detect import detect, variety
from .log import read
from .standing import standing, gini
from .world import World, unkey
from .engine import out_of_world, BUILD

HERE = os.path.dirname(__file__)
QUIET = {"frame", "census", "fail", "eat", "pickup", "drop", "put", "craft_fail", "herd_leaves", "herd_arrives", "access"}


CHUNK = 120            # replay frames per file: ten days of the world
NOTABLE = {"death", "attack", "steal", "promise_broken", "destroyed", "birth", "conceive", "deal", "group_found",
           "join", "build", "arrive", "craft", "wolf_attack", "wolf_killed", "burial", "story", "name_place", "wolves_come", "realized", "technique", "pledge",
           "hire", "service_left", "dismiss", "post", "trade", "make", "sick", "mend", "claim"}
SPOKEN = {"say", "whisper", "story", "deed"}


def load_logs(d):
    """Events and decisions of the current world, in order. A run that stopped before
    saving is replayed by the next one, so a later record for the same hour or event
    id replaces the earlier; a new world starts the lists over."""
    events, minds = {}, []
    for p in sorted(glob.glob(os.path.join(d, "log", "events-*.jsonl.gz"))):
        for ev in read(p):
            if ev.get("kind") == "world_begins":
                events = {}
            kind = ev.get("kind")
            k = ("f", ev["t"]) if kind == "frame" else ("c", ev["t"]) if kind == "census" else ("e", ev.get("id"))
            events.pop(k, None)
            events[k] = ev
    for p in sorted(glob.glob(os.path.join(d, "log", "minds-*.jsonl.gz"))):
        minds.extend(read(p))
    evs = sorted(events.values(), key=lambda ev: (ev["t"], ev.get("kind") != "frame", ev.get("id") or 0))
    return evs, minds


def write_replay(out_dir, frames, events, census=()):
    """Split the whole history into files of CHUNK hours that the viewer loads as it plays.
    Returns the index kept in data.json: where each hour sits, and the marks for the timeline."""
    rdir = os.path.join(out_dir, "replay")
    os.makedirs(rdir, exist_ok=True)
    for old in glob.glob(os.path.join(rdir, "*.json")):
        os.remove(old)
    idx = {fr["t"]: i for i, fr in enumerate(frames)}
    by_chunk = {}
    for ev in events:
        i = idx.get(ev["t"])
        if i is not None:
            by_chunk.setdefault(i // CHUNK, []).append(ev)
    # what each person had at each hour is logged only when it changed; every file starts
    # from the full picture so the viewer can open any file alone
    known, rows = {}, []
    for fr in frames:
        for r in fr.get("s") or []:
            known[r[0]] = r
        rows.append({p[0]: known[p[0]] for p in fr["p"] if p[0] in known})
    # the land once a day (buildings, bushes, piles), for showing and explaining it as it was;
    # each file starts from the last picture taken before it
    lands = sorted((idx[cs["t"]], cs["world"]) for cs in census if cs.get("world") and cs["t"] in idx)
    for c in range(0, (len(frames) + CHUNK - 1) // CHUNK):
        part = frames[c * CHUNK:(c + 1) * CHUNK]
        snaps = [list(rows[c * CHUNK].values())] + [fr.get("s") or [] for fr in part[1:]] if part else []
        lo, hi = c * CHUNK, (c + 1) * CHUNK
        land = [[i - lo, v] for i, v in lands if lo <= i < hi]
        before = [v for i, v in lands if i < lo]
        if before and (not land or land[0][0] > 0):
            land.insert(0, [0, before[-1]])
        with open(os.path.join(rdir, f"{c}.json"), "w") as f:
            json.dump({"frames": [[fr["t"], fr["p"], fr.get("h", []), fr.get("w", []), snaps[i]] for i, fr in enumerate(part)],
                       "events": by_chunk.get(c, []), "land": land}, f, separators=(",", ":"), ensure_ascii=False)
    marks, talk = [], {}
    for ev in events:
        i = idx.get(ev["t"])
        if i is None:
            continue
        if ev["kind"] in NOTABLE and (ev["kind"] != "craft" or ev.get("discovery")):
            marks.append([i, ev["kind"]])
        if ev["kind"] in SPOKEN or ev["kind"] in NOTABLE:
            talk[i] = talk.get(i, 0) + 1
    # a common kind (theft in a crowded land) would paint the whole timeline one colour:
    # each kind keeps at most 120 marks, spread evenly through the history
    by_kind = {}
    for m in marks:
        by_kind.setdefault(m[1], []).append(m)
    marks = sorted(m for ms in by_kind.values() for m in (ms if len(ms) <= 120 else ms[::len(ms) // 120 + 1]))
    return {"n": len(frames), "chunk": CHUNK, "ticks": [frames[0]["t"], frames[-1]["t"]] if frames else [0, 0],
            "marks": marks, "busy": sorted(talk.items())}


def action_text(a):
    if not isinstance(a, dict):
        return ""
    bits = [str(a.get("verb", "?"))]
    for k in ("target", "item", "item2", "qty", "dir", "name", "group", "id", "choice"):
        if a.get(k) not in (None, "", 0):
            bits.append(f"{k}={a[k]}")
    if a.get("x") is not None and a.get("y") is not None:
        bits.append(f"({a['x']},{a['y']})")
    for k in ("give", "get", "promise_give", "promise_get"):
        if a.get(k):
            bits.append(f"{k}=" + ",".join(f"{e.get('qty')} {e.get('item')}" for e in a[k] if isinstance(e, dict)))
    if a.get("text"):
        bits.append(f"“{a['text']}”")
    return " ".join(bits)


def build(world_dir, out_dir, mind_keep=60, events_keep=6000):
    with open(os.path.join(world_dir, "state.json")) as f:
        w = World.from_dict(json.load(f))
    events, minds = load_logs(world_dir)
    # a model that slipped out of the world (w25) may have left such words in older logs:
    # they are never published
    events = [ev for ev in events if not (out_of_world(ev.get("text")) or out_of_world(ev.get("words")))]
    tpy = w.ticks_per_year()
    frames = [ev for ev in events if ev["kind"] == "frame"]
    pop = []
    for fr in frames:
        if fr["t"] % w.tpd() == 0:
            pop.append([fr["t"], len(fr["p"])])
    census = [ev for ev in events if ev["kind"] == "census"]
    wealth = [[c["t"], gini([x[1] for x in c["c"]]), round(sum(x[1] for x in c["c"]), 1),
               max([x[1] for x in c["c"]] or [0]), c.get("rot")] for c in census]
    ideas = [{"t": ev["t"], "a": ev.get("a"), "text": ev.get("words") or ev["text"]}
             for ev in events if ev["kind"] == "idea"][-400:]
    replay = write_replay(out_dir, frames, [ev for ev in events if ev["kind"] not in QUIET], census)
    story = [ev for ev in events if ev["kind"] not in QUIET][-events_keep:]
    found = detect(events, w)
    by_agent = {}
    for m in minds:
        out = m.get("out") or m.get("bot") or {}
        if m.get("out") and (out_of_world(json.dumps(out, ensure_ascii=False))):
            out = {"thought": "(this answer came from outside the world and was set aside)"}
        rec = {"t": m["t"], "wake": m.get("wake", []), "model": (m.get("meta") or {}).get("model"),
               "thought": out.get("thought", "") if m.get("out") else "(rule-based fallback)" if m.get("bot") else "(no answer)",
               "act": action_text(out.get("action")),
               "plan": [action_text(p) for p in out.get("plan", []) or []][:8],
               "speech": (out.get("speech") or {}).get("text", "") if isinstance(out.get("speech"), dict) else "",
               "to": (out.get("speech") or {}).get("to", "") if isinstance(out.get("speech"), dict) else ""}
        by_agent.setdefault(m["agent"], []).append(rec)
    agents = []
    for a in w.agents.values():
        agents.append({
            "id": a.id, "name": a.name, "alive": a.alive, "x": a.x, "y": a.y, "health": a.health,
            "satiety": a.satiety, "age": round(a.age / tpy, 2), "born": a.born, "died": a.died, "cause": a.cause,
            "temperament": a.temperament, "wants": a.wants,
            "skills": {k: round(v, 2) for k, v in a.skills.items()}, "lore": a.lore, "model": a.model or a.mind, "strength": a.strength, "speed": a.speed,
            "inventory": a.inventory, "recipes": [w.recipes[k] for k in a.recipes],
            "groups": [w.groups[g].name for g in a.groups if g in w.groups],
            "memory": "" if out_of_world(a.memory) else a.memory,
            "beliefs": {k: v for k, v in a.beliefs.items() if not out_of_world(v)},
            "self_view": "" if out_of_world(a.self_view) else a.self_view,
            "life": [x for x in a.life if not out_of_world(x[1])], "parents": a.parents, "children": a.children, "calls": a.calls,
            "siblings": sorted({l[1] for l in a.ledger if l[2] == "kin" and "sibling" in l[3]}),
            "ledger": a.ledger[-25:], "minds": by_agent.get(a.id, [])[-mind_keep:],
            "activity": (a.activity or {}).get("verb"),
            "standing": list(standing(w, a)) if a.alive else [0, 0],
            "ideas": [x for x in a.ideas if not out_of_world(x[1])],
        })
    from .prompt import RULES_VERSION
    data = {
        "meta": {"rules": RULES_VERSION, "tick": w.tick, "when": w.when(), "season": w.season(), "year": w.year() + 1,
                 "population": len(w.living()), "tpd": w.tpd(), "night_from": w.cfg["world"]["night_from"],
                 "days_per_season": w.cfg["world"]["days_per_season"], "seed": w.seed,
                 "adult_years": w.cfg["agent"]["adult_ticks"] / w.ticks_per_year(),
                 "decisions": len(minds)},
        "w": w.w, "h": w.h, "terrain": w.terrain,
        "bushes": [[*unkey(k), b["b"]] for k, b in w.bushes.items()],
        "herds": [[h["x"], h["y"], h["size"]] for h in w.herds],
        "structures": [{"id": s.id, "kind": s.kind, "x": s.x, "y": s.y, "done": s.done, "owner": s.owner,
                        "access": s.allow if s.access == "list" else s.access, "inv": s.inventory if s.kind == "store" else {},
                        "name": s.name, "text": s.text, "built": s.built, "hp": s.hp, "trade": s.trade,
                        "crop": [s.seeds, s.progress, s.inventory.get("grain", 0), s.planted is not None] if s.kind == "farm" else None,
                        "fuel": s.fuel if s.kind == "fire" else None} for s in w.structures.values()],
        "piles": [[*unkey(k), p] for k, p in w.piles.items() if p],
        "hp_max": {k: v["hp"] for k, v in BUILD.items()}, "farm_grow": w.cfg["resources"]["farm_grow_ticks"],
        "signs": [[*unkey(k), [[au, txt, t] for au, txt, t in v]] for k, v in w.signs.items()],
        "groups": [{"id": g.id, "name": g.name, "leader": g.leader, "members": g.members, "rules": g.rules,
                    "decide": g.decide, "founded": g.founded, "ended": g.dissolved} for g in w.groups.values()],
        "agents": agents, "events": story, "replay": replay,
        "places": [[x, y, name, by, t] for x, y, name, by, t in w.places], "pop": pop,
        "wealth": wealth, "ideas": ideas,
        "builds": [[e["t"], e.get("x"), e.get("y"), "grave" if e["kind"] == "burial" else (e.get("what") or ""),
                    "destroyed" if e["kind"] == "destroyed" else "build"]
                   for e in events if e["kind"] in ("build", "destroyed", "burial") and e.get("x") is not None],
        "chronicle": load_chronicle(world_dir),
        "patterns": found[-300:], "variety": variety(found, events),
        "last_run": open(os.path.join(world_dir, "last_run.md")).read() if os.path.exists(os.path.join(world_dir, "last_run.md")) else "",
    }
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "data.json"), "w") as f:
        json.dump(data, f, separators=(",", ":"), ensure_ascii=False)
    with open(os.path.join(HERE, "viewer.html")) as f:
        page = f.read()
    with open(os.path.join(out_dir, "index.html"), "w") as f:
        f.write('<!doctype html>\n<html lang="en">\n<meta charset="utf-8">\n' + page)
    return data


def load_chronicle(d):
    p = os.path.join(d, "chronicle.jsonl")
    if not os.path.exists(p):
        return []
    with open(p) as f:
        return [c for c in (json.loads(l) for l in f if l.strip()) if not out_of_world(json.dumps(c, ensure_ascii=False))][-2000:]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="world")
    ap.add_argument("--out", default="site")
    ap.add_argument("--name", default="", help="this world's name in the header, when there are several")
    ap.add_argument("--link", action="append", default=[], help="another world: 'path|name' (repeatable)")
    args = ap.parse_args(argv)
    d = build(args.dir, args.out)
    if args.name or args.link:
        path = os.path.join(args.out, "data.json")
        with open(path) as f:
            data = json.load(f)
        data["meta"]["name"] = args.name
        data["meta"]["links"] = [dict(zip(("href", "name"), l.split("|", 1))) for l in args.link if "|" in l]
        with open(path, "w") as f:
            json.dump(data, f, separators=(",", ":"))
    print(f"built {args.out}: {len(d['agents'])} people, {len(d['events'])} events, {d['replay']['n']} hours of replay")


if __name__ == "__main__":
    main()
