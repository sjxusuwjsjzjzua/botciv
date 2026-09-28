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
from .world import World, unkey

HERE = os.path.dirname(__file__)
QUIET = {"frame", "fail", "pickup", "drop", "put", "craft_fail", "herd_leaves", "herd_arrives", "access"}


def load_logs(d):
    events, minds = [], []
    for p in sorted(glob.glob(os.path.join(d, "log", "events-*.jsonl.gz"))):
        events.extend(read(p))
    for p in sorted(glob.glob(os.path.join(d, "log", "minds-*.jsonl.gz"))):
        minds.extend(read(p))
    return events, minds


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


def build(world_dir, out_dir, frames_keep=2400, mind_keep=60, events_keep=6000):
    with open(os.path.join(world_dir, "state.json")) as f:
        w = World.from_dict(json.load(f))
    events, minds = load_logs(world_dir)
    tpy = w.ticks_per_year()
    frames = [ev for ev in events if ev["kind"] == "frame"]
    pop = []
    for fr in frames:
        if fr["t"] % w.tpd() == 0:
            pop.append([fr["t"], len(fr["p"])])
    frames = frames[-frames_keep:]
    story = [ev for ev in events if ev["kind"] not in QUIET][-events_keep:]
    found = detect(events, w)
    by_agent = {}
    for m in minds:
        out = m.get("out") or m.get("bot") or {}
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
            "temperament": a.temperament, "wants": a.wants, "model": a.model or a.mind, "strength": a.strength, "speed": a.speed,
            "inventory": a.inventory, "recipes": [w.recipes[k] for k in a.recipes],
            "groups": [w.groups[g].name for g in a.groups if g in w.groups], "memory": a.memory,
            "beliefs": a.beliefs, "parents": a.parents, "children": a.children, "calls": a.calls,
            "siblings": sorted({l[1] for l in a.ledger if l[2] == "kin" and "sibling" in l[3]}),
            "ledger": a.ledger[-25:], "minds": by_agent.get(a.id, [])[-mind_keep:],
            "activity": (a.activity or {}).get("verb"),
        })
    data = {
        "meta": {"tick": w.tick, "when": w.when(), "season": w.season(), "year": w.year() + 1,
                 "population": len(w.living()), "tpd": w.tpd(), "night_from": w.cfg["world"]["night_from"],
                 "days_per_season": w.cfg["world"]["days_per_season"], "seed": w.seed,
                 "decisions": len(minds)},
        "w": w.w, "h": w.h, "terrain": w.terrain,
        "bushes": [[*unkey(k), b["b"]] for k, b in w.bushes.items()],
        "herds": [[h["x"], h["y"], h["size"]] for h in w.herds],
        "structures": [{"kind": s.kind, "x": s.x, "y": s.y, "done": s.done, "owner": s.owner,
                        "access": s.access, "inv": s.inventory if s.kind == "store" else {}} for s in w.structures.values()],
        "signs": [[*unkey(k), [[au, txt, t] for au, txt, t in v]] for k, v in w.signs.items()],
        "groups": [{"name": g.name, "leader": g.leader, "members": g.members, "rules": g.rules,
                    "decide": g.decide, "founded": g.founded, "ended": g.dissolved} for g in w.groups.values()],
        "agents": agents, "events": story, "frames": [[fr["t"], fr["p"], fr.get("h", [])] for fr in frames], "pop": pop,
        "builds": [[e["t"], e.get("x"), e.get("y"), e.get("what") or e.get("kind2", ""), e["kind"]]
                   for e in events if e["kind"] in ("build", "destroyed") and e.get("x") is not None],
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
        return [json.loads(l) for l in f if l.strip()][-60:]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="world")
    ap.add_argument("--out", default="site")
    args = ap.parse_args(argv)
    d = build(args.dir, args.out)
    print(f"built {args.out}: {len(d['agents'])} people, {len(d['events'])} events, {len(d['frames'])} frames")


if __name__ == "__main__":
    main()
