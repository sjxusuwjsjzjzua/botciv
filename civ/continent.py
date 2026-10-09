"""A continent of regions (grand world, docs/grand.md section 6A): land that differs, so that peoples live
differently and need one another.

The land rises from a surrounding sea. Ridges of mountain cross it, broken by passes; rivers run from the high
ground to the sea through valleys of rich soil; the wet coasts are marsh and sand; the far side of the mountains
from the wet wind is dry grass, the steppe; the uplands are hill and moor; the rest is forest and open grass.
Then the land is cut into regions, each with a kind (valley, upland, steppe, forest, coast, mountain) by what
mostly lies in it. Everything is drawn from the world's random stream: one seed, one land."""
from collections import Counter, deque

from .content import PASSABLE
from .gen import value_noise, largest_component

# what share of the land each kind of ground takes, roughly (quantiles of the noise, so every seed is alike in
# its proportions and different in its shape)
SEA = 0.30              # of all tiles
MOUNTAIN = 0.05         # of the land
HILLS = 0.13
FOREST = 0.32           # of what is left once the high ground is taken
STEPPE = 0.30           # the driest of the open land

KINDS = ("valley", "upland", "steppe", "forest", "coast", "mountain")


def quantile(vals, q):
    s = sorted(vals)
    return s[min(len(s) - 1, max(0, int(q * len(s))))]


def terrain(rng, w, h):
    """(rows, the largest walkable component, elevation, moisture)."""
    base = value_noise(rng, w, h, max(w, h) / 2.5)
    detail = value_noise(rng, w, h, max(w, h) / 8)
    ridge_n = value_noise(rng, w, h, max(w, h) / 3.5)
    moist = value_noise(rng, w, h, max(w, h) / 4)
    cx, cy = (w - 1) / 2, (h - 1) / 2
    elev = [[0.0] * w for _ in range(h)]
    ridge = [[0.0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            # a continent: high in the middle, falling to sea at the edges
            d = max(abs(x - cx) / cx, abs(y - cy) / cy) ** 2 * 0.6 + (((x - cx) / cx) ** 2 + ((y - cy) / cy) ** 2) * 0.25
            e = 0.55 * base[y][x] + 0.15 * detail[y][x] + 0.5 * (1 - d)
            r = 1 - abs(2 * ridge_n[y][x] - 1)          # ridges: lines where the noise crosses its middle
            ridge[y][x] = r
            elev[y][x] = e
    sea = quantile([v for row in elev for v in row], SEA)
    land = [(x, y) for y in range(h) for x in range(w) if elev[y][x] > sea]
    # mountains: the highest of the ridges; hills: the rest of the high ground
    height = {(x, y): elev[y][x] + 0.35 * ridge[y][x] ** 3 for x, y in land}
    mount = quantile(list(height.values()), 1 - MOUNTAIN)
    hill = quantile(list(height.values()), 1 - MOUNTAIN - HILLS)
    g = [["~"] * w for _ in range(h)]
    for x, y in land:
        hv = height[(x, y)]
        g[y][x] = "^" if hv >= mount else "h" if hv >= hill else "."
    # wet and dry: the wind comes from the west, so the land east of high ground is drier (the steppe)
    shadow = [[0.0] * w for _ in range(h)]
    for y in range(h):
        acc = 0.0
        for x in range(w):
            acc = acc * 0.93 + (0.12 if g[y][x] in "^h" else 0)
            shadow[y][x] = acc
    wet = {(x, y): moist[y][x] - 0.6 * min(1.0, shadow[y][x]) + 0.25 * (elev[y][x] < sea + 0.04) for x, y in land}
    low = [(x, y) for x, y in land if g[y][x] == "."]
    dry = quantile([wet[t] for t in low], STEPPE)
    leafy = quantile([wet[t] for t in low], 1 - FOREST)
    for x, y in low:
        if wet[(x, y)] >= leafy:
            g[y][x] = "T"
    # coasts: marsh where the low shore is wet, sand where it is not
    for x, y in low:
        if g[y][x] != "." and g[y][x] != "T":
            continue
        shore = any(0 <= x + dx < w and 0 <= y + dy < h and g[y + dy][x + dx] == "~" for dx in (-1, 0, 1) for dy in (-1, 0, 1))
        if shore and elev[y][x] < sea + 0.05:
            g[y][x] = "m" if wet[(x, y)] > leafy - 0.05 and rng.random() < 0.7 else "s"
    rivers(rng, g, elev, w, h, sea)
    passes(rng, g, w, h)
    # banks: rich soil by the rivers in the open land (the valleys; in the dry land too, as by the great rivers),
    # thinning with distance from the water
    for y in range(h):
        for x in range(w):
            if g[y][x] in ".T" and elev[y][x] > sea + 0.02:
                near = min((max(abs(dx), abs(dy)) for dx in range(-3, 4) for dy in range(-3, 4)
                            if 0 <= x + dx < w and 0 <= y + dy < h and g[y + dy][x + dx] == "~"
                            and elev[y + dy][x + dx] > sea), default=9)
                if near <= 3 and rng.random() < (0.9, 0.8, 0.55, 0.25)[near] * (1 if g[y][x] == "." else 0.4):
                    g[y][x] = ","
    comp = largest_component(g, w, h)
    for y in range(h):
        for x in range(w):
            if g[y][x] in PASSABLE and (x, y) not in comp:
                g[y][x] = "^" if g[y][x] in "h^" else "~"
    return ["".join(r) for r in g], comp, elev, wet


def rivers(rng, g, elev, w, h, sea):
    """From springs in the high ground, downhill (wandering a little) to the sea; a few fords where the banks
    are close."""
    springs = sorted(((elev[y][x] + rng.random() * 0.05, x, y) for y in range(h) for x in range(w) if g[y][x] == "h"),
                     reverse=True)
    n = max(6, round(w * h / 1300))
    starts = []
    for _, x, y in springs:
        if all(max(abs(x - sx), abs(y - sy)) > max(w, h) // 10 for sx, sy in starts):
            starts.append((x, y))
        if len(starts) >= n:
            break
    for sx, sy in starts:
        x, y, seen = sx, sy, set()
        for _ in range(w + h):
            seen.add((x, y))
            if g[y][x] == "~" and (x, y) != (sx, sy):
                break
            if g[y][x] != "^":
                g[y][x] = "~"
            opts = [(elev[y + dy][x + dx] + rng.random() * 0.04, x + dx, y + dy)
                    for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0))
                    if 0 <= x + dx < w and 0 <= y + dy < h and (x + dx, y + dy) not in seen]
            if not opts:
                break
            _, x, y = min(opts)
    for y in range(h):
        for x in range(w):
            if g[y][x] == "~" and elev[y][x] > sea and rng.random() < 0.04:
                land = sum(1 for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0))
                           if 0 <= x + dx < w and 0 <= y + dy < h and g[y + dy][x + dx] in PASSABLE)
                if land >= 2:
                    g[y][x] = "s"               # a ford: shallows one can wade


def passes(rng, g, w, h):
    """Mountains that cut the land in two are crossed somewhere: join each lesser walkable part to the largest by
    the shortest way through mountain (it becomes hills: a pass)."""
    for _ in range(12):
        comps = components(g, w, h)
        if len(comps) <= 1:
            return
        comps.sort(key=len, reverse=True)
        main = comps[0]
        joined = False
        for c in comps[1:]:
            if len(c) < 30:
                continue
            way = cheapest_through_rock(g, w, h, c, main)
            if way:
                for x, y in way:
                    if g[y][x] == "^":
                        g[y][x] = "h"
                joined = True
        if not joined:
            return


def components(g, w, h):
    seen, out = set(), []
    for y in range(h):
        for x in range(w):
            if g[y][x] in PASSABLE and (x, y) not in seen:
                comp, q = {(x, y)}, deque([(x, y)])
                seen.add((x, y))
                while q:
                    cx, cy = q.popleft()
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            nx, ny = cx + dx, cy + dy
                            if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and g[ny][nx] in PASSABLE:
                                seen.add((nx, ny))
                                comp.add((nx, ny))
                                q.append((nx, ny))
                out.append(comp)
    return out


def cheapest_through_rock(g, w, h, frm, to):
    """The shortest run of mountain tiles from frm to to (water is never crossed), by breadth through rock."""
    q = deque((t, None) for t in frm)
    prev = {t: None for t in frm}
    while q:
        (x, y), _ = q.popleft()
        for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nx, ny = x + dx, y + dy
            if not (0 <= nx < w and 0 <= ny < h) or (nx, ny) in prev:
                continue
            c = g[ny][nx]
            if (nx, ny) in to:
                out, cur = [], (x, y)
                while cur is not None and cur not in frm:
                    out.append(cur)
                    cur = prev[cur]
                return out
            if c == "^":
                prev[(nx, ny)] = (x, y)
                q.append(((nx, ny), None))
    return None


def regions(rng, rows, comp, wet, n=None):
    """Cut the walkable land into regions round seeds spread over it (each tile to the nearest seed, by walking),
    each named by kind from what mostly lies in it. Returns (region of each tile, flat; -1 off the land or in
    rock and water, and a list of {"id", "kind", "x", "y", "size"})."""
    h, w = len(rows), len(rows[0])
    land = sorted(comp)
    n = n or max(6, round(len(land) / 2200))
    seeds = []
    pool = land[:]
    rng.shuffle(pool)
    gap = int((len(land) / n) ** 0.5 * 0.8)
    for t in pool:
        if all(max(abs(t[0] - s[0]), abs(t[1] - s[1])) >= gap for s in seeds):
            seeds.append(t)
        if len(seeds) >= n:
            break
    reg = [-1] * (w * h)
    q = deque()
    for i, (x, y) in enumerate(seeds):
        reg[y * w + x] = i
        q.append((x, y))
    while q:
        x, y = q.popleft()
        r = reg[y * w + x]
        for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and reg[ny * w + nx] < 0 and rows[ny][nx] in PASSABLE:
                reg[ny * w + nx] = r
                q.append((nx, ny))
    out, scores = [], []
    for i, (sx, sy) in enumerate(seeds):
        tiles = [(x, y) for (x, y) in land if reg[y * w + x] == i]
        out.append({"id": i, "kind": region_kind(rows, tiles, w, h, wet), "x": sx, "y": sy, "size": len(tiles)})
        scores.append(kind_scores(rows, tiles, w, h, wet))
    # every kind of land a people may call home is somewhere: a missing kind takes the region most like it among
    # those of a kind there are several of
    for kind in ("valley", "upland", "coast", "steppe", "forest"):
        if len(out) >= 5 and not any(r["kind"] == kind for r in out):
            many = Counter(r["kind"] for r in out)
            spare = [r for r in out if many[r["kind"]] > 1]
            if spare:
                best = max(spare, key=lambda r: scores[r["id"]][kind])
                best["kind"] = kind
    return reg, out


def kind_scores(rows, tiles, w, h, wet):
    c = Counter(rows[y][x] for x, y in tiles)
    n = max(1, len(tiles))
    shore = sum(1 for x, y in tiles if any(0 <= x + dx < w and 0 <= y + dy < h and rows[y + dy][x + dx] == "~"
                                           for dx in (-1, 0, 1) for dy in (-1, 0, 1))) / n
    damp = sum(wet.get(t, 0) for t in tiles) / n
    return {"upland": (c["h"] + c["^"]) / n, "valley": c[","] / n, "coast": shore + (c["m"] + c["s"]) / n,
            "forest": c["T"] / n, "steppe": c["."] / n * (1 - damp)}


def region_kind(rows, tiles, w, h, wet):
    """What a region mostly is: high ground (upland), river land (valley), shore and marsh (coast), woods
    (forest), or dry open grass (steppe)."""
    c = Counter(rows[y][x] for x, y in tiles)
    n = max(1, len(tiles))
    share = {k: c.get(k, 0) / n for k in ".,Thm^s"}
    shore = sum(1 for x, y in tiles if any(0 <= x + dx < w and 0 <= y + dy < h and rows[y + dy][x + dx] == "~"
                                           for dx in (-1, 0, 1) for dy in (-1, 0, 1))) / n
    damp = sum(wet.get(t, 0) for t in tiles) / n
    if share["h"] + share["^"] > 0.3:
        return "upland"
    if share[","] > 0.10:
        return "valley"
    if share["m"] + share["s"] > 0.05 or shore > 0.18:
        return "coast"
    if share["T"] > 0.38:
        return "forest"
    return "steppe" if damp < 0.45 else "forest" if share["T"] > 0.2 else "valley"
