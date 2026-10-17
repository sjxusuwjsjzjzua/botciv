"""The large land (world5.md §2, step 3): a world's land at twice the scale. Each tile becomes 2 x 2 tiles, so every
distance doubles and the area quadruples, and the land between settlements opens up; coasts, lakes, rivers, forests
and hills keep their shapes and gain detail.

- Broad water (sea, lakes) and every kind of land are sampled through a smooth warp of the coarse map, so their
  borders wander instead of stepping in 2-tile squares, never by more than about a coarse tile.
- Rivers (water one or two tiles across) stay one tile wide: each coarse river tile has a point in its 2 x 2 block,
  and the points are joined along the river's run. (Doubled, a river would be a band of water 2 km across.)
- Regions, named places, deposits, herds, packs and fish go to the doubled places.

Works on the land part of a saved world (the dict of `World.to_dict`): `upsample(d)` returns the new land's keys
(cfg, terrain, deposits, herds, packs, places, fish, regions, region_rows), to be laid over a state dict. Pure:
the same input and seed give the same land.
"""
from .land_at import hash2, vnoise

K = 2                   # the scale
WARP = 0.42             # how far (in coarse tiles) a border may wander
WAVE = 3.2              # the warp's wavelength, in new tiles
N8 = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]


def broad_water(terrain):
    """Water that is wide: within a 3 x 3 all-water block. The rest of the water is river."""
    h, w = len(terrain), len(terrain[0])
    water = lambda x, y: not (0 <= x < w and 0 <= y < h) or terrain[y][x] == "~"
    core = {(x, y) for y in range(h) for x in range(w)
            if all(water(x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1))}
    return {(x + dx, y + dy) for x, y in core for dx in (-1, 0, 1) for dy in (-1, 0, 1)
            if 0 <= x + dx < w and 0 <= y + dy < h}


def point(x, y, seed):
    """A coarse tile's point in its 2 x 2 block: where its river runs, its place stands, its deposit lies."""
    return K * x + int(hash2(x, y, seed + 11) * K), K * y + int(hash2(x, y, seed + 13) * K)


def line(a, b):
    """The new tiles from a to b, a step at a time (8-connected)."""
    (x0, y0), (x1, y1) = a, b
    out = [(x0, y0)]
    while (x0, y0) != (x1, y1):
        x0 += (x1 > x0) - (x1 < x0)
        y0 += (y1 > y0) - (y1 < y0)
        out.append((x0, y0))
    return out


def joined_without(terrain, X, Y):
    """Whether the water around (X, Y) stays one piece without it (within the 3 x 3 about it)."""
    H, W = len(terrain), len(terrain[0])
    wet = [(X + dx, Y + dy) for dx, dy in N8 if 0 <= X + dx < W and 0 <= Y + dy < H and terrain[Y + dy][X + dx] == "~"]
    if not wet:
        return False
    seen, todo = {wet[0]}, [wet[0]]
    while todo:
        cx, cy = todo.pop()
        for q in wet:
            if q not in seen and max(abs(q[0] - cx), abs(q[1] - cy)) == 1:
                seen.add(q)
                todo.append(q)
    return len(seen) == len(wet)


def upsample(d, seed=None):
    cfg = d["cfg"]
    seed = cfg.get("seed", 0) if seed is None else seed
    t0 = d["terrain"]
    h, w = len(t0), len(t0[0])
    H, W = h * K, w * K
    broad = broad_water(t0)
    river = {(x, y) for y in range(h) for x in range(w) if t0[y][x] == "~" and (x, y) not in broad}

    # the land under a river: what lies beside it most
    base = [list(r) for r in t0]
    for x, y in river:
        near = [t0[y + dy][x + dx] for dx, dy in N8 if 0 <= x + dx < w and 0 <= y + dy < h and t0[y + dy][x + dx] != "~"]
        base[y][x] = max(set(near), key=lambda c: (near.count(c), c)) if near else "m"

    # every new tile samples the coarse map through a smooth warp
    src = [[None] * W for _ in range(H)]
    for Y in range(H):
        for X in range(W):
            u = (X + 0.5) / K + WARP * 2 * (vnoise(X / WAVE, Y / WAVE, seed + 1) - 0.5)
            v = (Y + 0.5) / K + WARP * 2 * (vnoise(X / WAVE, Y / WAVE, seed + 2) - 0.5)
            src[Y][X] = (min(w - 1, max(0, int(u))), min(h - 1, max(0, int(v))))
    terrain = [[base[sy][sx] for sx, sy in row] for row in src]

    # rivers, one tile wide, joined along their run (a diagonal step only where no square one joins the two)
    wet = lambda x, y: 0 <= x < w and 0 <= y < h and t0[y][x] == "~"
    for x, y in sorted(river):
        for dx, dy in N8:
            nx, ny = x + dx, y + dy
            if not wet(nx, ny) or (dx and dy and (wet(x + dx, y) or wet(x, y + dy))):
                continue
            for X, Y in line(point(x, y, seed), point(nx, ny, seed)):
                terrain[Y][X] = "~"
        X, Y = point(x, y, seed)
        terrain[Y][X] = "~"
    for x, y in sorted(river):                          # a bend's block filled by both its runs: back to one wide
        P = point(x, y, seed)
        for j in range(K):
            for i in range(K):
                X, Y = K * x + i, K * y + j
                if (X, Y) != P and terrain[Y][X] == "~" and all(terrain[K * y + b][K * x + a] == "~" for a in range(K) for b in range(K)) \
                        and joined_without(terrain, X, Y):
                    terrain[Y][X] = base[y][x]
    for Y in range(H):                                  # no broad water lost to the warp where its block is all water
        for X in range(W):
            if (X // K, Y // K) in broad and all(t0[Y // K + dy][X // K + dx] == "~" for dx, dy in N8
                                                   if 0 <= X // K + dx < w and 0 <= Y // K + dy < h):
                terrain[Y][X] = "~"

    # regions follow the warped land; a river's tiles keep its region
    rows = d.get("region_rows")
    region = [[rows[sy][sx] for sx, sy in row] for row in src] if rows else None
    if region:
        for Y in range(H):
            for X in range(W):
                if (X // K, Y // K) in river and terrain[Y][X] == "~":
                    region[Y][X] = rows[Y // K][X // K]

    def land_near(x, y, want=None):
        """A dry new tile in coarse tile (x, y)'s block, its point first (one of `want`'s terrain if any)."""
        px, py = point(x, y, seed)
        block = [(px, py)] + [(K * x + i, K * y + j) for j in range(K) for i in range(K) if (K * x + i, K * y + j) != (px, py)]
        dry = [(X, Y) for X, Y in block if terrain[Y][X] != "~"]
        return next((q for q in dry if want and terrain[q[1]][q[0]] == want), dry[0] if dry else (px, py))

    deposits = {}
    for k, v in d.get("deposits", {}).items():
        x, y = map(int, k.split(","))
        X, Y = land_near(x, y, t0[y][x])
        deposits[f"{X},{Y}"] = dict(v)
    places = []
    for pl in d.get("places", []):
        X, Y = land_near(pl[0], pl[1])
        places.append([X, Y] + list(pl[2:]))
    herds = [dict(hd, x=land_near(hd["x"], hd["y"])[0], y=land_near(hd["x"], hd["y"])[1]) for hd in d.get("herds", [])]
    packs = [dict(pk, x=land_near(pk["x"], pk["y"])[0], y=land_near(pk["x"], pk["y"])[1]) for pk in d.get("packs", [])]
    fish = {}
    for k, n in d.get("fish", {}).items():               # a stretch of 8 x 8 tiles is now four
        cx, cy = map(int, k.split(","))
        for j in range(K):
            for i in range(K):
                fish[f"{K * cx + i},{K * cy + j}"] = n
    regions = [dict(r, x=K * r["x"], y=K * r["y"], size=r["size"] * K * K) for r in d.get("regions", [])]
    out = {"cfg": dict(cfg, width=W, height=H, scale=cfg.get("scale", 1) * K), "terrain": ["".join(r) for r in terrain],
           "deposits": deposits, "herds": herds, "packs": packs, "places": places, "fish": fish, "regions": regions}
    if region:
        out["region_rows"] = ["".join(r) for r in region]
    return out


def downsample(terrain):
    """The new land seen at the old scale: each 2 x 2 block's most common terrain (water wins a tie: rivers)."""
    H, W = len(terrain), len(terrain[0])
    out = []
    for y in range(H // K):
        row = []
        for x in range(W // K):
            cs = [terrain[K * y + j][K * x + i] for j in range(K) for i in range(K)]
            row.append(max(set(cs), key=lambda c: (cs.count(c), c == "~", c)))
        out.append("".join(row))
    return out


def components(terrain, ch="~"):
    """The 8-connected areas of one terrain: a list of sets of (x, y)."""
    H, W = len(terrain), len(terrain[0])
    seen, out = set(), []
    for y in range(H):
        for x in range(W):
            if terrain[y][x] != ch or (x, y) in seen:
                continue
            comp, todo = set(), [(x, y)]
            seen.add((x, y))
            while todo:
                cx, cy = todo.pop()
                comp.add((cx, cy))
                for dx, dy in N8:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < W and 0 <= ny < H and terrain[ny][nx] == ch and (nx, ny) not in seen:
                        seen.add((nx, ny))
                        todo.append((nx, ny))
            out.append(comp)
    return out
