"""Build the viewer's site for a civ world (data format 3; docs/viewer.md, section 3):

    manifest.json   the world's meta, terrain, the content catalogue, everyone who ever lived, the chunk table
    index.json      notable events, lives, firsts and losses, population and era by day (loaded at once)
    chunks/N.json   a span of hours: every hour's people, herds and packs; the daily snapshots; its speech and deeds
    minds/ID.json   the thoughts of one person with a mind of their own (loaded when looked at)
    index.html ...  the viewer itself (civ/viewer/), copied as it is

    python -m civ.site --dir world2 --out site/world2 --name "The wide land" --link "../other/|Another land"
"""
import argparse
import glob
import gzip
import json
import os
import shutil

from .content import TERRAIN, DEPOSITS, WILD, TAME, BUILDINGS, CRAFTS, ITEMS
from .run import load
from .world import TPD, TPY, DPS

FORMAT = 3
CHUNK = 240                 # hours in a chunk (20 days)
# kept in the index (always loaded): the deeds a chronicle and a timeline are made of
INDEX = {"monument", "birth", "death", "pledge", "group", "join", "law", "first", "skill", "craft_lost", "teach", "deal",
         "attack", "write", "book", "build", "tame", "trade", "steal", "conceive", "deed", "sign", "place", "promise_kept",
         "promise_broken", "hire", "take_crop", "worked_out", "library", "hunt", "claim",
         # lords and war (grand world, c71-c77)
         "fealty", "renounce", "tribute_unpaid", "muster", "raid", "plunder", "repelled", "rally", "peace", "broke_peace",
         "captive", "ransomed", "released", "escaped", "festival", "oath_broken"}
# kept in the chunks too (everyday doings, for the scene and a person's own record)
LOCAL = INDEX | {"say", "made", "give", "offer", "post", "ripe", "sick", "ruin"}
DATA = ("craft", "group", "level", "cause", "building", "item", "qty", "child", "age", "written", "x", "y", "name", "said", "size")


def ev(e):
    """An event as the site keeps it: [t, kind, text, who, {its facts}] (append-only)."""
    return [e["t"], e["kind"], e["text"], e.get("who", []), {k: e[k] for k in DATA if k in e}]


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


def dump(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, separators=(",", ":"))


def catalogue():
    """What the viewer's art kit needs to know of the content, by kind; unknown kinds get defaults there."""
    items = {}
    for k, v in ITEMS.items():
        cls = "worn" if "wear" in v else "weapon" if v.get("weapon") else "tool" if v.get("tool") else \
            "food" if v.get("food") else "material"
        items[k] = {"class": cls, "w": v.get("w", 1), "era": v.get("era", 0), "wear": list(v.get("wear", [])),
                    "tool": sorted(v.get("tool", {})), "weapon": v.get("weapon", 0), "food": v.get("food", 0)}
    return {"buildings": {k: {"roles": sorted(v["roles"]), "era": v["era"], "sym": v["sym"]} for k, v in BUILDINGS.items()},
            "items": items,
            "crafts": {k: {"era": v["era"], "does": v["does"], "pre": v["pre"], "at": v["at"]} for k, v in CRAFTS.items()},
            "terrain": {k: {"name": v["name"], "color": v["color"], "water": bool(v.get("water"))} for k, v in TERRAIN.items()},
            "deposits": {k: {"name": v["name"], "sym": v["sym"]} for k, v in DEPOSITS.items()},
            "wild": {k: {"name": v["name"]} for k, v in WILD.items()},
            "tame": sorted(TAME)}


def build(d, out, name="", links=()):
    w = load(d)
    events = read(os.path.join(d, "log", "events-*.jsonl.gz"))
    frames = read(os.path.join(d, "log", "frames-*.jsonl.gz"))
    minds = read(os.path.join(d, "log", "minds-*.jsonl.gz"))
    os.makedirs(out, exist_ok=True)
    # the viewer: a folder copied whole (stale files of an older build removed first)
    here = os.path.join(os.path.dirname(__file__), "viewer")
    for sub in ("chunks", "minds", "core", "ui", "scene", "art", "vendor"):
        shutil.rmtree(os.path.join(out, sub), ignore_errors=True)
    shutil.copytree(here, out, dirs_exist_ok=True, ignore=shutil.ignore_patterns("test", "*.test.js", "__pycache__", "package.json"))

    hours = sorted((f for f in frames if "p" in f), key=lambda f: f["t"])
    lands = sorted((f for f in frames if f.get("kind") == "land"), key=lambda f: f["t"])
    local = {}
    for e in events:
        if e["kind"] in LOCAL:
            local.setdefault(e["t"], []).append(ev(e))

    # chunks: a span of hours, with the snapshot in force at its start and those within it
    os.makedirs(os.path.join(out, "chunks"))
    table = []
    for c in range(0, (len(hours) + CHUNK - 1) // CHUNK):
        part = hours[c * CHUNK:(c + 1) * CHUNK]
        t0, t1 = part[0]["t"], part[-1]["t"]
        ls = [l for l in lands if t0 <= l["t"] <= t1]
        before = [l for l in lands if l["t"] < t0]
        if before and (not ls or ls[0]["t"] > t0):
            ls.insert(0, before[-1])
        thoughts = [[m["t"], m["id"], m.get("thought", ""), m.get("goal", ""), m.get("say")] for m in minds if t0 <= m["t"] <= t1]
        dump(os.path.join(out, "chunks", f"{c}.json"),
             {"t0": t0, "t1": t1,
              "hours": [[h["t"], h["p"], h.get("h", []), h.get("k", [])] for h in part],
              "land": ls,
              "events": [e for t in range(t0, t1 + 1) for e in local.get(t, [])],
              "thoughts": thoughts})
        table.append([t0, t1, f"chunks/{c}.json"])

    # the thoughts of each mind of its own, whole, for its page
    os.makedirs(os.path.join(out, "minds"))
    by = {}
    for m in minds:
        by.setdefault(m["id"], []).append([m["t"], m.get("thought", ""), m.get("goal", ""), m.get("plan", []), m.get("say"),
                                           m.get("to"), m.get("model")])
    for pid, ms in by.items():
        dump(os.path.join(out, "minds", f"{pid}.json"), ms)

    # measures by day, from the snapshots
    pop, era = [], []
    for l in lands:
        people = l.get("people", {})
        pop.append([l["t"], len(people)])
        top = {}
        for v in people.values():
            for c, s in v[1].items():
                top[c] = max(top.get(c, 0), s)
        era.append([l["t"], max((CRAFTS[c]["era"] for c, s in top.items() if s >= 0.3 and c in CRAFTS), default=0)])

    people = [{"id": p.id, "name": p.name, "born": p.born, "died": p.died, "cause": p.cause, "mind": p.mind,
               "parents": p.parents, "temperament": p.temperament, "wants": p.wants, "self": p.self_view,
               "life": p.life, "strength": p.strength, **({"people": p.people} if p.people else {})} for p in w.people.values()]
    t_first = hours[0]["t"] if hours else w.tick
    t_last = hours[-1]["t"] if hours else w.tick
    manifest = {
        "format": FORMAT,
        "meta": {"name": name, "links": [dict(zip(("href", "name"), l.split("|", 1))) for l in links if "|" in l],
                 "w": w.w, "h": w.h, "tpd": TPD, "tpy": TPY, "dps": DPS, "first": t_first, "last": t_last,
                 "night_from": TPD - 3, "built": w.tick},
        "terrain": w.terrain,
        "catalogue": catalogue(),
        "people": people,
        "minds": sorted(by),
        "chunks": table,
    }
    if w.regions:
        # the grand world (Phase 2): the regions, their map, and the peoples, for the journal's atlas
        from .content.peoples import PEOPLES
        manifest["realm"] = {"regions": w.regions, "rows": w.region_rows(),
                             "peoples": {k: {**v, "folk": PEOPLES[k]["folk"], "colours": PEOPLES[k]["colours"]}
                                         for k, v in w.peoples.items() if k in PEOPLES}}
    index = {
        "format": FORMAT,
        "events": [ev(e) for e in events if e["kind"] in INDEX],
        "pop": pop, "era": era,
        "places": w.places,
        "history": history(d),
        "last_run": open(os.path.join(d, "last_run.md")).read() if os.path.exists(os.path.join(d, "last_run.md")) else "",
    }
    dump(os.path.join(out, "manifest.json"), manifest)
    dump(os.path.join(out, "index.json"), index)
    return manifest, index


def history(d):
    """The long record (civ/census.py: a census line a season), when the land keeps one: whole, for the
    journal's long-run charts, which span every year the land has lived and not just the hours kept."""
    p = os.path.join(d, "history.jsonl")
    if not os.path.exists(p):
        return []
    out = []
    with open(p) as f:
        for line in f:
            try:
                h = json.loads(line)
            except ValueError:
                continue
            out.append({k: h.get(k) for k in ("t", "year", "season", "alive", "ever", "births", "deaths", "era", "able",
                                              "firsts", "lost", "buildings", "groups", "beasts", "packs", "gini")})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="world2")
    ap.add_argument("--out", default="site")
    ap.add_argument("--name", default="")
    ap.add_argument("--link", action="append", default=[])
    a = ap.parse_args(argv)
    m, i = build(a.dir, a.out, a.name, a.link)
    print(f"built {a.out}: {len(m['people'])} people, {len(m['chunks'])} chunks, {len(i['events'])} notable events, "
          f"hours {m['meta']['first']}..{m['meta']['last']}")


if __name__ == "__main__":
    main()
