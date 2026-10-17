"""A settlement of a real towns world drawn by step 0's viewer (docs/world5_handoff.md §8, towns_spec §9): runs a
bots-only towns world (or reads a saved one), takes one settlement and the land about it, and writes it in the demo's
data format, so `civ/viewer/demo.html?data=<name>` shows what the engine built: its lanes, plots, houses, workshops,
green, well, burial ground, field strips and people where they stand.

    python tools/demo_from_world.py --days 20                      # writes civ/viewer/demo/world_village.json
    python tools/demo_from_world.py --state s.json.gz --site 12 --out other

The land is still tiles in the engine (step 3 brings `land_at` rivers): heights come from each tile's ground, the
longest run of water tiles nearby becomes the river, forest tiles become forest. The settlement's tile is shifted so
the scene sits where the demo's cameras look (its land tile spans 1000-2000 m in x and y).
"""
import argparse
import collections
import gzip
import json
import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from civ import geom as G  # noqa: E402
from civ.content.towns import zone, town_of  # noqa: E402
from civ.world import World, TILE_M  # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), "..", "civ", "viewer", "demo")
WATER = 10.0
GROUND = {"~": 12.0, "m": 11.6, "s": 12.4, ",": 14.0, ".": 16.0, "T": 19.0, "h": 30.0, "^": 52.0}
CROPS = {"flax": "flax"}
VERBS = {"gather", "talk", "craft", "take", "plant", "tame", "fish", "build", "rest", "walk"}
STORE = {"store", "granary"}
FIRE = {"kiln", "oven", "furnace", "bloomery", "lime_kiln", "glassworks"}


def r1(v):
    return round(v, 1)


def shape_of(b, people):
    """The demo's kind for an engine building: the people's house shape for a dwelling, else the nearest in the kit."""
    if zone(b.kind) == "dwelling":
        return "conical_hut" if town_of(people)["shape"] in ("conical_hut", "round_house", "tent") else "long_house"
    if b.kind in STORE:
        return "stilt_store"
    if b.kind in FIRE:
        return "kiln"
    if b.kind in ("grave", "cairn"):
        return "grave_stone"
    if b.kind in ("fire", "well", "shrine", "drying_rack"):
        return b.kind
    return "long_house"                                    # a workshop, hall or loom shed: a plain house of its size


def river_from(w, tiles):
    """The longest run of 4-connected water tiles among `tiles`, as a polyline through their middles."""
    water = {t for t in tiles if w.inb(*t) and w.terrain[t[1]][t[0]] == "~"}
    best = []
    seen = set()
    for start in sorted(water):
        if start in seen:
            continue
        comp, todo = {start}, [start]
        while todo:
            x, y = todo.pop()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if n in water and n not in comp:
                    comp.add(n)
                    todo.append(n)
        seen |= comp

        def far(a):
            prev, q, i = {a: None}, [a], 0
            while i < len(q):
                x, y = q[i]
                i += 1
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (x + dx, y + dy)
                    if n in comp and n not in prev:
                        prev[n] = (x, y)
                        q.append(n)
            return q[-1], prev
        a, _ = far(min(comp))
        b, prev = far(a)
        path = [b]
        while prev[path[-1]] is not None:
            path.append(prev[path[-1]])
        if len(path) > len(best):
            best = path
    return best


def export(w, site, name="world_village"):
    sx, sy = site.x, site.y
    OX, OY = (sx - 1) * TILE_M, (sy - 1) * TILE_M          # world metres -> the scene's
    P = lambda X, Y: [r1(X - OX), r1(Y - OY)]
    tx0, ty0 = sx - 4, sy - 4                               # the land drawn: 12 x 9 tiles about the settlement

    def ground_at(X, Y):
        x, y = int((X + OX) // TILE_M), int((Y + OY) // TILE_M)
        return GROUND.get(w.terrain[y][x], 16.0) if w.inb(x, y) else 24.0
    # heights every 250 m, each the mean of the ground over 750 m about it (tiles blend, no step at their edges)
    H = {"x0": -3000, "y0": -3000, "step": 250, "nx": 49, "ny": 37}
    H["h"] = [[r1(sum(ground_at(-3000 + i * 250 + u, -3000 + j * 250 + v) for u in (-375, 0, 375) for v in (-375, 0, 375)) / 9)
               for i in range(H["nx"])] for j in range(H["ny"])]
    tiles = [(x, y) for y in range(ty0, ty0 + 9) for x in range(tx0, tx0 + 12)]
    run = river_from(w, tiles)
    far = [[-9000, -9000, 10], [-8000, -9000, 10]]          # no river (or stream): a curve far off
    river = [[*P((x + 0.5) * TILE_M, (y + 0.5) * TILE_M), 920] for x, y in run] if len(run) > 1 else far
    forest = [{"pts": [P(x * TILE_M, y * TILE_M), P((x + 1) * TILE_M, y * TILE_M), P((x + 1) * TILE_M, (y + 1) * TILE_M),
                       P(x * TILE_M, (y + 1) * TILE_M)], "density": 0.85}
              for x, y in tiles if w.inb(x, y) and w.terrain[y][x] == "T"]
    cx, cy = P(*site.centre)
    land = {"size": [6000, 3000], "seed": 5, "water_level": WATER, "heights": H, "river": river, "stream": far,
            "forest": forest, "clearings": [], "flat": [cx, cy, 320]}

    lanes = [{"pts": [P(*q) for q in l["pts"]], "w": l["w"], "kind": "lane" if l["kind"] != "path" else "path",
              **({"closed": True} if l["kind"] == "ring" else {})} for l in site.lanes]
    # the track: out from the main lane's end toward the nearest other settlement (or on along the lane)
    main = next((l for l in site.lanes if l.get("main")), site.lanes[0] if site.lanes else None)
    others = sorted((math.hypot(o.centre[0] - site.centre[0], o.centre[1] - site.centre[1]), o) for o in w.sites.values() if o is not site)
    end = P(*main["pts"][-1]) if main else [cx, cy]
    to = P(*others[0][1].centre) if others and others[0][0] < 4000 else [end[0] + 1500, end[1]]
    lanes.append({"pts": [end, [r1((end[0] + to[0]) / 2), r1((end[1] + to[1]) / 2 + 40)], to], "w": 3, "kind": "track"})

    bounds = {"fence": "wattle", "hedge": "wattle", "wall": "wattle"}.get(town_of(site.people)["bounds"])
    plots = []
    for q in site.plots:
        if q["kind"] == "burial" or bounds:
            plots.append({"pts": [P(*c) for c in G.corners(tuple(q["rect"]))], "fence": bounds or "none", "gate": 2,
                          "household": q.get("holder") or 0, **({"use": "burial"} if q["kind"] == "burial" else {})})

    here = [b for b in w.buildings_at(sx, sy) if b.pos and b.size and b.kind not in ("farm", "pen")
            and b.done and b.ruin is None]
    buildings = []
    for b in here:
        k = shape_of(b, site.people)
        out = {"kind": k, "pos": P(*b.pos), "angle": r1(b.angle), "size": [r1(b.size[0]), r1(b.size[1])],
               "household": b.owner if b.owner and b.owner > 0 else 0, "engine": b.kind}
        if k == "long_house":
            out["style"] = site.people or "river"
        if b.kind == "fire" or (b.kind in FIRE and b.process):
            out["lit"] = True
        buildings.append(out)
    gx, gy = P(site.green[0], site.green[1]) if site.green else (cx, cy)
    if not any(b["kind"] == "well" for b in buildings):     # every demo village draws its well; the green has one
        buildings.append({"kind": "well", "pos": [gx, gy], "angle": 0, "size": [2.2, 2.2]})

    fields = []
    for b in w.buildings.values():
        if b.kind != "farm" or not b.pos or not b.size or abs(b.x - sx) > 4 or abs(b.y - sy) > 4:
            continue
        c = b.crop
        crop = (CROPS.get(c["what"], "wheat") if c else "stubble" if b.inv else "fallow")
        fields.append({"pts": [P(*q) for q in G.corners((b.pos[0], b.pos[1], b.size[0], b.size[1], b.angle))], "crop": crop,
                       "stage": "ripe" if c and c.get("ripe") else "growing" if c else "bare"})

    people, animals = [], []
    for p in w.living():
        if not p.pos or p.inside or abs(p.x - sx) > 4 or abs(p.y - sy) > 4:
            continue
        do = (p.act or {}).get("do")
        verb = "walk" if do in ("go", "walk", "follow") else do if do in VERBS else "rest" if p.rest else "talk"
        people.append({"id": len(people), "pid": p.id, "pos": P(*p.pos), "verb": verb, "age": int(p.age(w.tick))})
    for b in w.buildings_at(sx, sy):
        if b.kind == "pen" and b.pos and b.animals:
            n = 0
            for kind, k in b.animals.items():
                for i in range(min(k, 6)):
                    a = (b.id * 7 + n * 2.39) % 6.283
                    animals.append({"kind": "sheep", "pos": [r1(b.pos[0] - OX + math.cos(a) * 3), r1(b.pos[1] - OY + math.sin(a) * 3)],
                                    "angle": int(a * 57.3) % 360})
                    n += 1
    walker = 0                                              # the demo numbers its people 0..n-1 (folk.js looks them up so)
    if people:
        w0 = people[0]
        w0["path"] = [w0["pos"], [gx, gy], to]
        w0["speed"] = 1.3
        w0["verb"] = "walk"
    xs = [q[0] for pl in plots for q in pl["pts"]] + [b["pos"][0] for b in buildings]
    ys = [q[1] for pl in plots for q in pl["pts"]] + [b["pos"][1] for b in buildings]
    paint = [r1(min(xs) - 40), r1(min(ys) - 40), r1(max(xs) - min(xs) + 80), r1(max(ys) - min(ys) + 80)] if xs else [cx - 220, cy - 175, 440, 350]
    fx = [q[0] for f in fields for q in f["pts"]]
    fy = [q[1] for f in fields for q in f["pts"]]
    return {"format": "world5-demo-1", "units": "metres, x east, y south; angle: degrees, front faces (sin a, cos a)",
            "from": {"site": site.id, "name": site.name, "people": site.people, "form": site.form, "tile": [sx, sy],
                     "day": w.tick // 12, "households": sum(1 for b in here if zone(b.kind) == "dwelling")},
            "land": land, "trees": [], "lanes": lanes, "plots": plots, "buildings": buildings, "fields": fields,
            "people": people, "animals": animals, "green": {"pos": [gx, gy], "r": [r1(site.green[2] / 2), r1(site.green[3] / 2)] if site.green else [10, 10]},
            "walker": walker, "centre": [cx, cy], "paint": paint,
            "fieldsBox": [min(fx), min(fy), max(fx), max(fy)] if fx else [0, 0, 0, 0]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state")
    ap.add_argument("--days", type=int, default=20)
    ap.add_argument("--people", type=int, default=400)
    ap.add_argument("--size", type=int, default=64)
    ap.add_argument("--seed", type=int, default=3)
    ap.add_argument("--site", type=int, help="a settlement's id (default: the one with most households)")
    ap.add_argument("--out", default="world_village")
    a = ap.parse_args()
    if a.state:
        op = gzip.open if a.state.endswith(".gz") else open
        with op(a.state, "rt") as f:
            w = World.from_dict(json.load(f))
    else:
        from civ.realm import generate
        from civ.engine import Engine
        from civ.minds.bot import BotMind
        w = generate({"seed": a.seed, "people": a.people, "width": a.size, "height": a.size, "format": "towns1"})
        e = Engine(w)
        mind = BotMind(e)
        t0 = time.time()
        for _ in range(a.days * 12):
            e.tick(mind.decide)
        print(f"{a.days} days in {time.time() - t0:.0f} s")
    homes = collections.Counter(b.site for b in w.buildings.values() if zone(b.kind) == "dwelling" and b.site is not None)
    site = w.sites[a.site] if a.site else w.sites[homes.most_common(1)[0][0]]
    d = export(w, site, a.out)
    path = os.path.join(OUT, a.out + ".json")
    with open(path, "w") as f:
        json.dump(d, f, separators=(",", ":"))
    print(f"{site.name} ({site.people}, {site.form}): {d['from']['households']} households, {len(d['buildings'])} buildings, "
          f"{len(d['fields'])} strips, {len(d['people'])} people; {os.path.getsize(path) // 1024} KB -> {path}")


if __name__ == "__main__":
    main()
