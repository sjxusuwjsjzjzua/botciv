"""Making a land: terrain from elevation and moisture, rivers running downhill, deposits by
geology, herds where they live, and the first people in bands by water."""
import math
import random
from collections import deque

from .content import TERRAIN, PASSABLE, DEPOSITS, WILD, CRAFTS
from .names import make_name, temperament, want
from .world import World, Person, key, dist, TPY

DEFAULTS = dict(width=96, height=96, seed=1, people=160, ai=0, bands=10, herds_per_1000=6, packs_per_1000=0.8)


def value_noise(rng, w, h, scale, octaves=4):
    """Smooth noise in 0..1: coarse random grids, blended."""
    out = [[0.0] * w for _ in range(h)]
    amp, total = 1.0, 0.0
    for o in range(octaves):
        s = max(2, int(scale / (2 ** o)))
        gw, gh = w // s + 2, h // s + 2
        grid = [[rng.random() for _ in range(gw)] for _ in range(gh)]
        for y in range(h):
            fy = y / s
            y0 = int(fy)
            ty = fy - y0
            ty = ty * ty * (3 - 2 * ty)
            for x in range(w):
                fx = x / s
                x0 = int(fx)
                tx = fx - x0
                tx = tx * tx * (3 - 2 * tx)
                a = grid[y0][x0] * (1 - tx) + grid[y0][x0 + 1] * tx
                b = grid[y0 + 1][x0] * (1 - tx) + grid[y0 + 1][x0 + 1] * tx
                out[y][x] += amp * (a * (1 - ty) + b * ty)
        total += amp
        amp *= 0.5
    lo = min(min(r) for r in out)
    hi = max(max(r) for r in out)
    return [[(v - lo) / (hi - lo + 1e-9) for v in r] for r in out]


def largest_component(grid, w, h):
    seen, best = set(), set()
    for y in range(h):
        for x in range(w):
            if grid[y][x] in PASSABLE and (x, y) not in seen:
                comp, q = set(), deque([(x, y)])
                seen.add((x, y))
                while q:
                    cx, cy = q.popleft()
                    comp.add((cx, cy))
                    for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and grid[ny][nx] in PASSABLE:
                            seen.add((nx, ny))
                            q.append((nx, ny))
                if len(comp) > len(best):
                    best = comp
    return best


def terrain(rng, w, h):
    elev = value_noise(rng, w, h, max(w, h) / 3)
    moist = value_noise(rng, w, h, max(w, h) / 4)
    g = [["."] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            e, m = elev[y][x], moist[y][x]
            if e > 0.86:
                g[y][x] = "^"
            elif e > 0.70:
                g[y][x] = "h"
            elif e < 0.16:
                g[y][x] = "~"
            elif e < 0.22 and m > 0.55:
                g[y][x] = "m"
            elif m > 0.56:
                g[y][x] = "T"
    # rivers: from high ground, downhill (with a little wander) to water or the edge
    n_rivers = max(2, round(w * h / 2200))
    highs = sorted(((elev[y][x], x, y) for y in range(h) for x in range(w) if 0.72 < elev[y][x] < 0.86), reverse=True)
    starts = []
    for _, x, y in highs:
        if all(dist(x, y, sx, sy) > max(w, h) // 5 for sx, sy in starts):
            starts.append((x, y))
        if len(starts) >= n_rivers:
            break
    for sx, sy in starts:
        x, y, seen = sx, sy, set()
        for _ in range(w + h):
            seen.add((x, y))
            if g[y][x] == "~" and (x, y) != (sx, sy):
                break
            g[y][x] = "~"
            opts = [(elev[y + dy][x + dx] + rng.random() * 0.03, x + dx, y + dy)
                    for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0))
                    if 0 <= x + dx < w and 0 <= y + dy < h and (x + dx, y + dy) not in seen]
            if not opts:
                break
            _, x, y = min(opts)
            if x in (0, w - 1) or y in (0, h - 1):
                g[y][x] = "~"
                break
    # fords, so both banks meet: every so often a river tile becomes shallows (sand)
    for y in range(h):
        for x in range(w):
            if g[y][x] == "~" and rng.random() < 0.025:
                land = sum(1 for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0))
                           if 0 <= x + dx < w and 0 <= y + dy < h and g[y + dy][x + dx] in PASSABLE)
                if land >= 2:
                    g[y][x] = "s"
    # banks: rich soil by fresh water, sand by broad water
    for y in range(h):
        for x in range(w):
            if g[y][x] in ".T":
                wet = sum(1 for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                          if 0 <= x + dx < w and 0 <= y + dy < h and g[y + dy][x + dx] == "~")
                near = wet or any(0 <= x + dx < w and 0 <= y + dy < h and g[y + dy][x + dx] == "~"
                                  for dx in (-2, 0, 2) for dy in (-2, 0, 2))
                if wet >= 4 and rng.random() < 0.4:
                    g[y][x] = "s"
                elif near and g[y][x] == "." and rng.random() < 0.65:
                    g[y][x] = ","
    comp = largest_component(g, w, h)
    for y in range(h):
        for x in range(w):
            if g[y][x] in PASSABLE and (x, y) not in comp:
                g[y][x] = "^"
    return ["".join(r) for r in g], comp


def place_deposits(wd, rng):
    w, h = wd.w, wd.h
    wet = lambda x, y: any(wd.inb(x + dx, y + dy) and wd.t(x + dx, y + dy) == "~" for dx in (-1, 0, 1) for dy in (-1, 0, 1))
    walk = lambda x, y: any(wd.inb(x + dx, y + dy) and wd.t(x + dx, y + dy) in PASSABLE for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy)
    placed = {}
    for kind, d in DEPOSITS.items():
        if d["on"] == "bank":
            pool = [(x, y) for y in range(h) for x in range(w) if wd.t(x, y) in PASSABLE and wet(x, y)]
        else:
            pool = [(x, y) for y in range(h) for x in range(w) if wd.t(x, y) in d["on"]
                    and (wd.t(x, y) in PASSABLE or walk(x, y)) and (not d.get("near_water") or wet(x, y))]
        pool = [t for t in pool if key(*t) not in wd.deposits]
        if not pool:
            continue
        n = min(len(pool), max(d["least"], round(len(pool) * d["per"] / 100)))
        if d.get("cluster"):
            far = placed.get(d.get("far"))
            groups = max(1, n // 5)
            chosen = []
            for _ in range(groups):
                if far:
                    cx = sum(x for x, _ in far) / len(far)
                    cy = sum(y for _, y in far) / len(far)
                    cand = sorted(pool, key=lambda t: -dist(t[0], t[1], cx, cy))[:max(1, len(pool) // 4)]
                else:
                    cand = pool
                seed = rng.choice(cand)
                chosen += sorted(pool, key=lambda t: (dist(t[0], t[1], *seed), rng.random()))[:max(1, n // groups)]
            chosen = list(dict.fromkeys(chosen))[:n]
        else:
            chosen = rng.sample(pool, n)
        placed[kind] = chosen
        for x, y in chosen:
            size = d["size"] if d.get("renew") != "bush" else rng.randint(4, d["size"])
            wd.deposits[key(x, y)] = {"kind": kind, "left": size, "size": d["size"]}


def place_herds(wd, rng, comp):
    cells = list(comp)
    per = wd.cfg.get("herds_per_1000", 6)
    kinds = [k for k in WILD if not WILD[k].get("extra")]
    n_total = max(len(kinds), round(len(cells) * per / 1000))
    # kinds that are no one's food (wild asses, c86) come besides the game, a few, not in its place
    extra = [k for k in WILD if WILD[k].get("extra")]
    for i in range(n_total + len(extra) * max(1, n_total // 12)):
        if i >= n_total:
            kind = extra[(i - n_total) % len(extra)]
            spots = [c for c in rng.sample(cells, min(400, len(cells))) if wd.t(*c) in WILD[kind]["on"]]
            if spots:
                lo, hi = WILD[kind]["herd"]
                wd.herds.append({"id": wd.new_id(), "kind": kind, "x": spots[0][0], "y": spots[0][1], "n": rng.randint(lo, hi), "grow": 0})
            continue
        kind = kinds[i % len(kinds)] if i < len(kinds) * 2 else rng.choice(kinds)
        spots = [c for c in rng.sample(cells, min(400, len(cells))) if wd.t(*c) in WILD[kind]["on"]]
        if not spots:
            continue
        x, y = spots[0]
        lo, hi = WILD[kind]["herd"]
        wd.herds.append({"id": wd.new_id(), "kind": kind, "x": x, "y": y, "n": rng.randint(lo, hi), "grow": 0})
    for _ in range(max(1, round(len(cells) * wd.cfg.get("packs_per_1000", 0.8) / 1000))):
        spots = [c for c in rng.sample(cells, min(400, len(cells))) if wd.t(*c) == "T"]
        if spots:
            x, y = spots[0]
            wd.packs.append({"id": wd.new_id(), "x": x, "y": y, "n": rng.randint(3, 5), "hunger": 0})


def traits(rng):
    return {k: round(rng.random(), 2) for k in ("industry", "sociability", "boldness", "generosity", "curiosity", "ambition")}


def make_person(wd, rng, x, y, age_years, parents=None):
    p = Person(id=wd.new_id(), name=make_name(rng, wd.names), x=x, y=y, born=wd.tick - int(age_years * TPY),
               lifespan=int(rng.uniform(62, 88) * TPY), traits=traits(rng), temperament=temperament(rng),
               wants=want(rng), strength=rng.randint(1, 3), parents=list(parents or []))
    for g in ("gather", "hunt", "fish", "fight", "build"):
        p.skills[g] = round(rng.random() * 0.3, 2)
    return p


def found_people(wd, rng, comp):
    """Bands of kin by water and food, a few days' walk apart. Everyone has some skill in the
    foraging crafts, and each has a knack or two."""
    n, bands = wd.cfg["people"], wd.cfg["bands"]
    cells = [c for c in comp if wd.t(*c) in ".,T"]
    good = [c for c in cells if any(wd.inb(c[0] + dx, c[1] + dy) and wd.t(c[0] + dx, c[1] + dy) == "~"
                                     for dx in (-2, 0, 2) for dy in (-2, 0, 2))] or cells
    rng.shuffle(good)
    sites = []
    for c in good:
        if all(dist(c[0], c[1], s[0], s[1]) >= max(wd.w, wd.h) // 5 for s in sites):
            sites.append(c)
        if len(sites) >= bands:
            break
    while len(sites) < bands:
        sites.append(rng.choice(cells))
    era0 = [c for c, v in CRAFTS.items() if v["era"] == 0]
    made = []
    for i in range(n):
        sx, sy = sites[i % len(sites)]
        spot = [(sx + dx, sy + dy) for dx in range(-3, 4) for dy in range(-3, 4) if wd.passable(sx + dx, sy + dy)]
        x, y = rng.choice(spot) if spot else (sx, sy)
        p = make_person(wd, rng, x, y, rng.uniform(16, 50) if i % 5 else rng.uniform(4, 13))
        for c in era0:
            p.skills[c] = round(rng.uniform(0.05, 0.35), 2)
        for c in rng.sample(era0, 2):
            p.skills[c] = round(rng.uniform(0.45, 0.7), 2)
        p.inv = {"berries": rng.randint(2, 6)}
        wd.people[p.id] = p
        made.append((i % len(sites), p))
    # people know the ground they grew up on: what lies within a day's walk of home
    for _, p in made:
        for x, y in wd.beside(p.x, p.y, 12):
            d = wd.deposits.get(key(x, y))
            if d:
                p.known[key(x, y)] = ["deposit", d["kind"], 0]
        for h in wd.herds:
            if dist(p.x, p.y, h["x"], h["y"]) <= 14:
                p.known[f"herd{h['id']}"] = ["herd", h["kind"], 0, h["x"], h["y"]]
    # kin: each band are relatives, who start trusting one another
    by_band = {}
    for b, p in made:
        by_band.setdefault(b, []).append(p)
    # a band is a few families: kin within a family, known and trusted within the band
    for members in by_band.values():
        fams = [members[i:i + 4] for i in range(0, len(members), 4)]
        for fam in fams:
            for a in members:
                for o in members:
                    if a.id == o.id:
                        continue
                    same = a in fam and o in fam
                    a.rel[str(o.id)] = {"trust": 0.5 if same else 0.25, "met": 0, **({"kin": "kin"} if same else {})}
    # who is asked by a language model: spread across bands, grown people first
    ai = wd.cfg.get("ai", 0)
    order = sorted(wd.people.values(), key=lambda p: (p.age(0) < 16, rng.random()))
    for p in order[:ai]:
        p.mind = "llm"
    wd.rebuild_grid()


def generate(cfg=None):
    cfg = {**DEFAULTS, **(cfg or {})}
    wd = World(cfg)
    rng = wd.rng
    wd.terrain, comp = terrain(rng, wd.w, wd.h)
    place_deposits(wd, random.Random(wd.seed * 7919 + 1))
    place_herds(wd, rng, comp)
    found_people(wd, rng, comp)
    return wd
