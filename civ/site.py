"""Build the viewer's data for a civ world: data.json (the world now: land, people, knowledge,
notable events, measures over time) and replay/N.json (hour by hour, in chunks the viewer loads
as it plays).

    python -m civ.site --dir world2 --out site/world2 --name "The wide land" --link "../|The first land"
"""
import argparse
import glob
import gzip
import json
import os
import shutil
from collections import Counter

from .content import TERRAIN, DEPOSITS, WILD, BUILDINGS, CRAFTS, RECIPES, ITEMS
from .content import items as I
from .run import load
from .world import TPD, TPY

CHUNK = 240
NOTABLE = {"monument", "birth", "death", "pledge", "group", "law", "first", "skill", "craft_lost", "teach", "deal", "attack", "say",
           "write", "book", "build", "tame", "trade", "steal", "join", "conceive", "deed", "sign", "place", "promise_kept",
           "promise_broken", "hire", "hunt", "made", "take_crop", "worked_out", "library"}


def read(pattern):
    out = []
    for f in sorted(glob.glob(pattern)):
        try:
            with gzip.open(f, "rt", encoding="utf-8") as fh:
                for line in fh:
                    try:
                        out.append(json.loads(line))
                    except ValueError:
                        break
        except (OSError, EOFError):
            continue
    return out


def build(d, out, name="", links=()):
    w = load(d)
    events = read(os.path.join(d, "log", "events-*.jsonl.gz"))
    frames = read(os.path.join(d, "log", "frames-*.jsonl.gz"))
    minds = read(os.path.join(d, "log", "minds-*.jsonl.gz"))
    os.makedirs(out, exist_ok=True)
    here = os.path.dirname(__file__)
    shutil.copy(os.path.join(here, "viewer.html"), os.path.join(out, "index.html"))
    # replay chunks: positions every hour, the land each day
    rdir = os.path.join(out, "replay")
    shutil.rmtree(rdir, ignore_errors=True)
    os.makedirs(rdir)
    hours = [f for f in frames if "p" in f]
    lands = [f for f in frames if f.get("kind") == "land"]
    by_t = {}
    for e in events:
        if e["kind"] in NOTABLE:
            by_t.setdefault(e["t"], []).append([e["kind"], e["text"], e.get("who", [])])
    for c in range(0, (len(hours) + CHUNK - 1) // CHUNK):
        part = hours[c * CHUNK:(c + 1) * CHUNK]
        t0, t1 = part[0]["t"], part[-1]["t"]
        ls = [l for l in lands if t0 <= l["t"] <= t1]
        before = [l for l in lands if l["t"] < t0]
        if before and (not ls or ls[0]["t"] > t0):
            ls.insert(0, before[-1])
        with open(os.path.join(rdir, f"{c}.json"), "w") as f:
            json.dump({"hours": [[h["t"], h["p"], h.get("h", []), h.get("k", [])] for h in part],
                       "land": ls, "events": {t: by_t[t] for t in range(t0, t1 + 1) if t in by_t}}, f, separators=(",", ":"))
    # measures over time, once a day
    pop, era = [], []
    for l in lands:
        people = l.get("people", {})
        pop.append([l["t"], len(people)])
        top = {}
        for inv, skills, *_ in people.values():
            for c, s in skills.items():
                top[c] = max(top.get(c, 0), s)
        era.append([l["t"], max((CRAFTS[c]["era"] for c, s in top.items() if s >= 0.3 and c in CRAFTS), default=0)])
    # knowledge: every craft, who is able or a master, when it was first practised, lost
    know = []
    for c, v in CRAFTS.items():
        holders = sorted(((p.skill(c), p.id) for p in w.living() if p.skill(c) >= 0.3), reverse=True)
        know.append({"craft": c, "era": v["era"], "does": v["does"], "pre": v["pre"],
                     "masters": [pid for s, pid in holders if s >= 0.7], "able": [pid for s, pid in holders if s < 0.7],
                     "first": w.firsts.get(c), "lost": w.lost.get(c)})
    people = []
    for p in w.people.values():
        people.append({"id": p.id, "name": p.name, "alive": p.alive, "born": p.born, "died": p.died, "cause": p.cause,
                       "mind": p.mind, "age": round(p.age(p.died if p.died is not None else w.tick), 1),
                       "temperament": p.temperament, "wants": p.wants, "self": p.self_view,
                       "partner": p.partner, "parents": p.parents, "children": p.children, "groups": p.groups,
                       "skills": {c: round(s, 2) for c, s in p.skills.items() if c in CRAFTS and s > 0},
                       "inv": p.inv if p.alive else {}, "worn": I.worn(p.inv) if p.alive else [],
                       "worth": round(I.worth(p.inv) + sum(I.worth(b.inv) for b in w.buildings.values() if b.owner == p.id), 1),
                       "goal": (p.intent or {}).get("goal", ""), "memory": p.memory, "life": p.life,
                       "x": p.x, "y": p.y})
    decisions = {}
    for m in minds[-3000:]:
        decisions.setdefault(m["id"], []).append({"t": m["t"], "thought": m.get("thought", ""), "goal": m.get("goal", ""),
                                                  "plan": m.get("plan", []), "say": m.get("say"), "model": m.get("model")})
    data = {
        "meta": {"name": name, "links": [dict(zip(("href", "name"), l.split("|", 1))) for l in links if "|" in l],
                 "tick": w.tick, "when": w.when(), "season": w.season(), "year": w.year() + 1, "tpd": TPD, "tpy": TPY,
                 "w": w.w, "h": w.h, "alive": len(w.living()), "ai": sum(1 for p in w.living() if p.mind == "llm"),
                 "chunk": CHUNK, "chunks": (len(hours) + CHUNK - 1) // CHUNK, "t0": hours[0]["t"] if hours else w.tick,
                 "hours": len(hours)},
        "terrain": w.terrain,
        "legend": {"terrain": {k: [v["name"], v["color"]] for k, v in TERRAIN.items()},
                   "deposits": {k: [v["name"], v["sym"]] for k, v in DEPOSITS.items()},
                   "wild": {k: v["name"] for k, v in WILD.items()},
                   "buildings": {k: [v["sym"], v["era"], list(v["roles"])] for k, v in BUILDINGS.items()},
                   "wear": {k: list(v["wear"]) for k, v in ITEMS.items() if "wear" in v}},
        "people": people, "knowledge": know,
        "groups": [{"id": g.id, "name": g.name, "leader": g.leader, "members": g.members, "rules": g.rules, "laws": g.laws,
                    "decide": g.decide, "dissolved": g.dissolved} for g in w.groups.values()],
        "places": w.places,
        "events": [[e["t"], e["kind"], e["text"], e.get("who", [])] for e in events if e["kind"] in NOTABLE][-4000:],
        "pop": pop, "era": era, "decisions": decisions,
        "last_run": open(os.path.join(d, "last_run.md")).read() if os.path.exists(os.path.join(d, "last_run.md")) else "",
    }
    with open(os.path.join(out, "data.json"), "w") as f:
        json.dump(data, f, separators=(",", ":"))
    return data


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="world2")
    ap.add_argument("--out", default="site")
    ap.add_argument("--name", default="")
    ap.add_argument("--link", action="append", default=[])
    a = ap.parse_args(argv)
    d = build(a.dir, a.out, a.name, a.link)
    print(f"built {a.out}: {d['meta']['alive']} alive, {len(d['people'])} people, {d['meta']['hours']} hours of replay")


if __name__ == "__main__":
    main()
