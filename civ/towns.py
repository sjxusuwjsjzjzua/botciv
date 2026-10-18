"""The settlement planner (docs/towns_spec.md §4): pure functions of the world and a seed, called only when something
is founded, settled or built, never every hour. All in metres (x east, y south); a building's angle in degrees, its
front facing (sin a, cos a); a plot's rect is (X, Y, w, d, angle) with its front on its lane (civ/geom.py).

The five forms (§4.2), each a lane skeleton and a rule for where the next plot goes:
  street      (river)  a lane through the centre, gently bending; plots both sides, out from the green; back lanes
  waterfront  (shore)  a lane along the water; plots on the landward side facing the water; a second lane behind
  cluster     (hill)   a ring lane round a fold; plots outside it facing in; rings outward
  ring        (riders) plots as wedges round a horse fold, doors to the fold; rings outward
  scatter     (forest) plots at loose points round a fire-ring, joined by a tree of paths
All share: plots front a lane; nothing overlaps another plot, a lane, the green or water, or leaves its tile (less a
margin). Where a building of each kind goes is its zone (content/towns.py): dwelling and yard on one's plot, commons
round the green, edge on a craft plot downwind (east), water by the water, burial in the burial plot, field on a strip
of a field tile, land anywhere free in the tile.
"""
import math
import random

from . import geom as G
from .content.towns import CELL, footprint, town_of, zone
from .content import BUILDINGS
from .world import TILE_M, Settlement, key

MARGIN = 8 * CELL           # kept clear inside the tile's edge
GAP = 1.0                   # metres between plots
WIND = (1, 0)               # v1: the wind is from the west; what smokes and stinks goes east
DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, 1), (1, -1), (-1, -1)]


def rng_for(w, site_id, n=0):
    """The planner's randomness: the same plan on every machine."""
    return random.Random(f"{w.cfg['seed']}:{site_id}:{n}")


def spacing_ok(w, x, y, apart=3):
    """No settlement within `apart` land tiles (two villages an hour apart are two villages)."""
    return all(max(abs(s.x - x), abs(s.y - y)) >= apart for s in w.sites.values() if s.form != "homestead" or apart <= 1)


def is_water(w, X, Y):
    x, y = int(X // TILE_M), int(Y // TILE_M)
    if not w.inb(x, y):
        return True
    return w.terrain[y][x] in "~"


def water_side(w, x, y):
    """The side (dx, dy) of a tile that water lies beside, or None."""
    for dx, dy in DIRS[:4]:
        if w.inb(x + dx, y + dy) and w.terrain[y + dy][x + dx] == "~":
            return dx, dy
    return None


# ---------- founding ----------

def found(w, x, y, people, by=None, name=None, form=None):
    """Found a settlement on land tile (x, y) for a people; returns it, or a reason (str) why not (§4.1)."""
    if not w.inb(x, y) or not w.passable(x, y) or w.terrain[y][x] == "~":
        return "not on open land"
    if w.site_of(x, y) is not None:
        return "a settlement is already here"
    if form != "homestead" and not spacing_ok(w, x, y):
        return "too near another settlement"
    sid = w.new_id()
    r = rng_for(w, sid)
    t = town_of(people)
    form = form or t["form"]
    ws = water_side(w, x, y)
    if form == "waterfront" and not ws:
        form = "street"
    X0, Y0 = x * TILE_M, y * TILE_M
    cx, cy = X0 + TILE_M / 2, Y0 + TILE_M / 2
    if ws:                                              # beside water: near the water's side (a waterfront hard by it)
        inset = (16 if form == "waterfront" else 30) * CELL
        cx = X0 + TILE_M / 2 + ws[0] * (TILE_M / 2 - inset)
        cy = Y0 + TILE_M / 2 + ws[1] * (TILE_M / 2 - inset)
    jit = 20 * CELL if form != "waterfront" else 6 * CELL
    cx += r.uniform(-jit, jit) * (0 if ws and ws[0] else 1)
    cy += r.uniform(-jit, jit) * (0 if ws and ws[1] else 1)
    site = Settlement(id=sid, name=name or "", x=x, y=y, people=people, form=form, founded=w.tick, centre=[round(cx, 1), round(cy, 1)])
    lw = t["lane"] * CELL
    if form in ("street", "homestead"):
        ax = axis_for(w, x, y, ws, r)
        site.green = [cx, cy, 7 * CELL, 6 * CELL, G.facing(*ax)]
        site.lanes.append({"id": 1, "pts": bent(cx, cy, ax, 120 if form == "street" else 40, r), "w": lw, "kind": "lane", "main": True})
    elif form == "waterfront":
        along = (-ws[1], ws[0])
        gx, gy = cx + ws[0] * 4 * CELL, cy + ws[1] * 4 * CELL
        site.green = [gx, gy, 8 * CELL, 6 * CELL, G.facing(*ws)]
        site.lanes.append({"id": 1, "pts": straight(cx - ws[0] * 6 * CELL, cy - ws[1] * 6 * CELL, along, 140), "w": lw,
                           "kind": "lane", "main": True, "landward": [-ws[0], -ws[1]]})
    elif form in ("cluster", "ring"):
        side = 10 if form == "cluster" else 13
        site.green = [cx, cy, side * CELL, side * CELL, 0.0]
        rad = side * CELL * 0.72 + lw / 2 + 2
        site.lanes.append({"id": 1, "pts": circle(cx, cy, rad), "w": lw, "kind": "ring", "ring": 0, "r": rad, "main": True})
    elif form == "scatter":
        site.green = [cx, cy, 7 * CELL, 7 * CELL, 0.0]
    w.sites[sid] = site
    w.site_at[key(x, y)] = sid
    for l in site.lanes:
        name_lane(w, site, l)
    if not site.name:
        from .content.peoples import PEOPLES
        from .names import make_name
        site.name = make_name(rng_for(w, sid, 999), {s.name for s in w.sites.values()}, PEOPLES.get(people, {}).get("tongue"))
    burial_plot(w, site, r)
    recompute_edge(site)
    w.rebuild_many()
    return site


def axis_for(w, x, y, ws, r):
    """The main lane's way: toward the neighbour tile walked into most (c69 footfall), else along the water, else
    the seed's choice."""
    best, most = None, 0
    for dx, dy in DIRS:
        if w.inb(x + dx, y + dy):
            f = w.foot.get((y + dy) * w.w + x + dx, 0)
            if f > most:
                best, most = (dx, dy), f
    if best:
        l = math.hypot(*best)
        return best[0] / l, best[1] / l
    if ws:
        return -ws[1], ws[0]
    a = r.choice([0, 45, 90, 135]) * math.pi / 180
    return math.cos(a), math.sin(a)


SUFFIX = {"street": "Street", "homestead": "Lane", "waterfront": "Row", "cluster": "Ring", "ring": "Ring", "scatter": "Path"}


def name_lane(w, site, lane):
    """A lane's name: a word in its people's tongue and what kind of way it is (Selvan Street, the Shore Row...)."""
    from .content.peoples import PEOPLES
    from .names import make_name
    r = rng_for(w, site.id, 1000 + lane["id"])
    tongue = PEOPLES.get(site.people, {}).get("tongue")
    taken = {l.get("name", "").split(" ")[0] for l in site.lanes}
    kind = "Lane" if lane["kind"] == "back" else "Path" if lane["kind"] == "path" else SUFFIX.get(site.form, "Lane")
    lane["name"] = f"{make_name(r, taken, tongue)} {kind}"
    return lane


def straight(cx, cy, d, half):
    return [[round(cx - d[0] * half, 1), round(cy - d[1] * half, 1)], [round(cx + d[0] * half, 1), round(cy + d[1] * half, 1)]]


def bent(cx, cy, d, half, r, step=20):
    """A lane through (cx, cy) along d, `half` metres each way, bending gently (as lanes worn by feet do)."""
    nx, ny = -d[1], d[0]
    amp, ph = r.uniform(6, 16), r.uniform(0, math.tau)
    pts = []
    n = int(half * 2 / step)
    for k in range(n + 1):
        s = -half + k * step
        o = amp * math.sin(s / 160 * math.pi + ph) - amp * math.sin(ph)
        pts.append([round(cx + d[0] * s + nx * o, 1), round(cy + d[1] * s + ny * o, 1)])
    return pts


def circle(cx, cy, rad, n=32):
    return [[round(cx + rad * math.cos(k / n * math.tau), 1), round(cy + rad * math.sin(k / n * math.tau), 1)] for k in range(n + 1)]


# ---------- what is taken ----------

def obstacles(w, site, skip_plot=None):
    """Every rect on the site's tile that a new plot or building must keep off: plots, lanes, the green, buildings
    outside plots."""
    out = [tuple(p["rect"]) for p in site.plots if p["id"] != skip_plot]
    out.append(("lanes", lane_points(site)))
    if site.green:
        out.append(tuple(site.green))
    for b in w.buildings_at(site.x, site.y):
        if b.pos and b.size and b.plot is None and not BUILDINGS.get(b.kind, {}).get("overlay"):
            out.append((b.pos[0], b.pos[1], b.size[0], b.size[1], b.angle))
    return out


def lane_points(site, step=2.0):
    """Every lane as points 2 m apart, each with its half width: what a plot or building must keep off."""
    key_ = (len(site.lanes), sum(len(l["pts"]) for l in site.lanes))
    cache = site.__dict__.get("_lanepts")
    if cache and cache[0] == key_:
        return cache[1]
    pts = []
    for l in site.lanes:
        L = G.length(l["pts"])
        n = max(1, int(L / step))
        for k in range(n + 1):
            (X, Y), _ = G.at(l["pts"], L * k / n)
            pts.append((X, Y, l["w"] / 2))
    object.__setattr__(site, "_lanepts", (key_, pts))
    return pts


def fits(w, site, rect, obs, gap=GAP):
    """Inside the site's tile (less the margin), on dry land, clear of everything in obs (rects, and the lanes)."""
    x0, y0 = site.x * TILE_M + MARGIN, site.y * TILE_M + MARGIN
    x1, y1 = x0 + TILE_M - 2 * MARGIN, y0 + TILE_M - 2 * MARGIN
    for X, Y in G.corners(rect) + [(rect[0], rect[1])]:
        if not (x0 <= X <= x1 and y0 <= Y <= y1) or is_water(w, X, Y):
            return False
    reach = math.hypot(rect[2], rect[3]) / 2 + 8
    for o in obs:
        if o[0] == "lanes":
            for X, Y, hw in o[1]:
                if abs(X - rect[0]) < reach and abs(Y - rect[1]) < reach and \
                        G.inside((rect[0], rect[1], rect[2] + 2 * hw + 0.5, rect[3] + 2 * hw + 0.5, rect[4]), X, Y):
                    return False
        elif G.overlap(rect, o, gap):
            return False
    return True


# ---------- plots ----------

def plot_size(site, kind):
    t = town_of(site.people)
    pw, pd = t["plot"][0] * CELL, t["plot"][1] * CELL
    if kind == "farmstead":
        pd *= 1.5
    elif kind == "lord":
        pw, pd = pw * 2, pd * 1.5
    elif kind == "craft":                                   # a working yard, not a home's: half as deep, 24 m at least
        pd = max(pd * 0.5, 6 * CELL)                        # (a pen or a loom and its room; hill folk's plots are small)
    return pw, pd


def frontage(site, lane, pw, pd, sides=(1, -1), step=None):
    """Candidate plots along a lane: (rect, s) facing it, both sides (or those given)."""
    pts, lw = lane["pts"], lane["w"]
    L = G.length(pts)
    step = step or (pw + GAP) / 2
    s = pw / 2
    while s <= L - pw / 2:
        (X, Y), (dx, dy) = G.at(pts, s)
        nx, ny = -dy, dx
        for side in sides:
            off = lw / 2 + 0.8 + pd / 2
            cx, cy = X + nx * side * off, Y + ny * side * off
            yield (round(cx, 2), round(cy, 2), pw, pd, G.facing(-nx * side, -ny * side)), s
        s += step


def plot_for(w, site, holder, kind="cottage"):
    """The next free plot for a household (§4.4), or a reason: a vacant plot first; else the next frontage by the
    form's rule, nearest the holder's kin, then nearest the green (a craft plot: at the downwind end). The form's
    lanes grow when the frontage is full."""
    for p in site.plots:
        if p.get("vacant") and p["kind"] in (kind, "cottage"):
            p.update(holder=holder, since=w.tick, vacant=False)
            return p
    pw, pd = plot_size(site, kind)
    kin = kin_plots(w, site, holder)
    for attempt in range(6):
        best = None
        obs = obstacles(w, site)
        for rect, lane in candidates(w, site, pw, pd):
            if not fits(w, site, rect, obs):
                continue
            score = score_for(site, rect, kind, kin)
            if best is None or score < best[0]:
                best = (score, rect, lane)
        if best:
            _, rect, lane = best
            plot = {"id": next_plot_id(site), "rect": [round(v, 2) for v in rect], "lane": lane["id"], "side": 1,
                    "kind": kind, "holder": holder, "since": w.tick}
            site.plots.append(plot)
            if site.form == "scatter" and kind != "burial":
                join_by_path(site, plot)
            recompute_edge(site)
            return plot
        if not grow(w, site, max(pd, plot_size(site, "cottage")[1])):     # new lanes spaced for homes
            break
    return "no room left in the settlement"


def join_by_path(site, plot):
    """A scatter plot is joined by a path from its front to the nearest plot already joined, or to the fire-ring."""
    X, Y = G.to_world(tuple(plot["rect"]), 0, plot["rect"][3] / 2 + 2)
    gx, gy = site.green[0], site.green[1]
    best = (math.hypot(X - gx, Y - gy) - site.green[2] / 2, [gx, gy])
    for q in site.plots:
        if q is plot or q["kind"] == "burial":
            continue
        fx, fy = G.to_world(tuple(q["rect"]), 0, q["rect"][3] / 2 + 2)
        d = math.hypot(X - fx, Y - fy)
        if d < best[0]:
            best = (d, [fx, fy])
    site.lanes.append({"id": len(site.lanes) + 1, "pts": [[round(X, 1), round(Y, 1)], [round(best[1][0], 1), round(best[1][1], 1)]],
                       "w": 0.75 * CELL, "kind": "path"})


def next_plot_id(site):
    return max([p["id"] for p in site.plots], default=0) + 1


def kin_plots(w, site, holder):
    p = w.people.get(holder)
    if p is None:
        return []
    kin = set(p.parents) | set(p.children)
    for par in p.parents:
        q = w.people.get(par)
        if q:
            kin |= set(q.children)
    kin.discard(holder)
    return [pl["rect"] for pl in site.plots if pl["holder"] in kin]


def score_for(site, rect, kind, kin):
    cx, cy = site.green[0], site.green[1]
    d = math.hypot(rect[0] - cx, rect[1] - cy)
    if kind == "craft":
        return -(rect[0] - cx) * 2 + d * 0.3              # downwind: east
    if kin:
        return min(math.hypot(rect[0] - k[0], rect[1] - k[1]) for k in kin) * 0.6 + d * 0.4
    return d


def candidates(w, site, pw, pd):
    """Where the form offers plots: (rect, lane)."""
    for lane in site.lanes:
        if lane["kind"] == "path":
            continue
        if site.form in ("cluster", "ring"):
            if lane["kind"] != "ring":
                continue
            for rect, s in frontage(site, lane, pw if site.form == "cluster" else pw * 0.9, pd, sides=(-1,), step=pw * 0.5):
                yield rect, lane
        elif site.form == "waterfront":
            lx, ly = lane.get("landward", [0, 0])
            for rect, s in frontage(site, lane, pw, pd):
                fx, fy = math.sin(math.radians(rect[4])), math.cos(math.radians(rect[4]))
                if fx * lx + fy * ly < -0.5:                  # its front to the water: the landward side only
                    yield rect, lane
        elif site.form == "scatter":
            continue
        else:
            for rect, s in frontage(site, lane, pw, pd):
                yield rect, lane
    if site.form == "scatter":
        yield from scatter_points(w, site, pw, pd)


def scatter_points(w, site, pw, pd):
    """Loose points 14-22 cells apart within 70 cells of the fire-ring, each a plot facing the fire."""
    r = rng_for(w, site.id, len(site.plots) + 100)
    cx, cy = site.green[0], site.green[1]
    taken = [(p["rect"][0], p["rect"][1]) for p in site.plots if p["kind"] != "burial"] or []
    reach = (70 + max(0, len(taken) - 30) * 2) * CELL          # a large hamlet spreads further into the trees
    for _ in range(400):
        a, d = r.uniform(0, math.tau), r.uniform(10 * CELL, reach)
        X, Y = cx + math.cos(a) * d, cy + math.sin(a) * d
        if any(math.hypot(X - tx, Y - ty) < 14 * CELL for tx, ty in taken):
            continue
        rect = (X, Y, pw, pd, G.facing(cx - X, cy - Y))
        yield rect, {"id": 0}


def grow(w, site, pd):
    """Make more frontage when the form's is full: the street's lane runs on (to 90 cells each way), then back lanes
    parallel to it; the waterfront's a second lane behind; a ring the next ring out. False when it cannot."""
    t = town_of(site.people)
    lw = t["lane"] * CELL
    main = next((l for l in site.lanes if l.get("main")), None)
    if main is None:
        return False
    if site.form in ("street", "homestead"):
        L = G.length(main["pts"])
        if L < 2 * 90 * CELL:
            (x0, y0), (x1, y1) = main["pts"][0], main["pts"][1]
            d0 = (x0 - x1, y0 - y1)
            (xa, ya), (xb, yb) = main["pts"][-1], main["pts"][-2]
            d1 = (xa - xb, ya - yb)
            l0, l1 = math.hypot(*d0) or 1, math.hypot(*d1) or 1
            main["pts"] = [[round(x0 + d0[0] / l0 * 40, 1), round(y0 + d0[1] / l0 * 40, 1)]] + main["pts"] + \
                          [[round(xa + d1[0] / l1 * 40, 1), round(ya + d1[1] / l1 * 40, 1)]]
            return True
        backs = [l for l in site.lanes if l["kind"] == "back"]
        if len(backs) < 2:
            side = 1 if not backs else -1
            off = lw / 2 + GAP + pd + GAP + lw / 2
            pts = []
            for k in range(len(main["pts"])):
                (X, Y), (dx, dy) = G.at(main["pts"], G.length(main["pts"][:k + 1]))
                pts.append([round(X - dy * side * off, 1), round(Y + dx * side * off, 1)])
            site.lanes.append(name_lane(w, site, {"id": len(site.lanes) + 1, "pts": pts, "w": lw, "kind": "back"}))
            return True
        return False
    if site.form == "waterfront":
        L = G.length(main["pts"])
        if L < 120 * CELL:                              # along the shore first, then a lane behind
            (x0, y0), (x1, y1) = main["pts"][0], main["pts"][-1]
            l = math.hypot(x1 - x0, y1 - y0) or 1
            dx, dy = (x1 - x0) / l, (y1 - y0) / l
            main["pts"] = [[round(x0 - dx * 40, 1), round(y0 - dy * 40, 1)], [round(x1 + dx * 40, 1), round(y1 + dy * 40, 1)]]
            return True
        if len([l for l in site.lanes if l["kind"] == "lane"]) < 3:
            lx, ly = main["landward"]
            off = (pd + 2 * GAP + lw) * len(site.lanes)
            off = (pd + 2 * GAP + lw) * len([l for l in site.lanes if l["kind"] == "lane"])
            pts = [[round(X + lx * off, 1), round(Y + ly * off, 1)] for X, Y in main["pts"]]
            site.lanes.append(name_lane(w, site, {"id": len(site.lanes) + 1, "pts": pts, "w": lw, "kind": "lane", "landward": [lx, ly]}))
            return True
        return False
    if site.form in ("cluster", "ring"):
        rings = [l for l in site.lanes if l["kind"] == "ring"]
        if len(rings) < 8:
            rad = rings[-1]["r"] + pd + 2 * GAP + lw
            cx, cy = site.green[0], site.green[1]
            site.lanes.append(name_lane(w, site, {"id": len(site.lanes) + 1, "pts": circle(cx, cy, rad, 48), "w": lw, "kind": "ring",
                                                  "ring": len(rings), "r": rad}))
            return True
        return False
    return False


# ---------- the burial ground and the edge ----------

def burial_plot(w, site, r=None):
    """A burial plot at the settlement's quiet side: the first free spot on a ring round it, upwind first."""
    r = r or rng_for(w, site.id, 7)
    cx, cy = site.green[0], site.green[1]
    obs = obstacles(w, site)
    angs = sorted(range(0, 360, 15), key=lambda a: (abs(((a - 180 + 180) % 360) - 180), a))   # west (upwind) first
    for rad in (110, 140, 170, 220, 270):
        for a in angs:
            X, Y = cx + math.cos(math.radians(a)) * rad, cy + math.sin(math.radians(a)) * rad
            rect = (X, Y, 8 * CELL, 6 * CELL, G.facing(cx - X, cy - Y))
            if fits(w, site, rect, obs, gap=12):
                plot = {"id": next_plot_id(site), "rect": [round(v, 2) for v in rect], "lane": 0, "side": 0, "kind": "burial",
                        "holder": 0, "since": w.tick}
                site.plots.append(plot)
                site.burial = plot["id"]
                return plot
    return None


def recompute_edge(site):
    pts = []
    for p in site.plots:
        pts += G.corners(tuple(p["rect"]))
    if site.green:
        pts += G.corners(tuple(site.green))
    site.edge = G.grow(G.hull(pts), 2 * CELL) if pts else []


# ---------- placing a building ----------

def place(w, p, kind, near=None):
    """Where a building of `kind` goes for p (§4.5): {"pos", "angle", "size", "door", "site", "plot"}, or a reason (str)."""
    if near is not None and tuple(near) != (p.x, p.y) and w.inb(*near):
        p = _At(p, *near)                       # the place named: its settlement, its ground
    z = zone(kind)
    size = footprint(kind, p.people)
    if z == "field":
        return place_strip(w, p)
    site = settlement_for(w, p, z)
    if isinstance(site, str):
        return site
    if site is None or size is None or z == "land":
        return place_land(w, p, kind, size, site)
    if z == "dwelling":
        plot = own_plot(w, site, p, "cottage")
        if isinstance(plot, str):
            return plot
        spot = on_plot(w, site, plot, kind, size, front=True)
        if spot is None and plot["holder"] == p.id and not any(zone(b.kind) == "dwelling" and b.plot == plot["id"]
                                                               for b in w.buildings_at(site.x, site.y)):
            spot = on_plot(w, site, plot, kind, size, front=False)
        if spot is None:                            # the frontage is taken: a plot of one's own
            fresh = plot_for(w, site, p.id, "cottage")
            if isinstance(fresh, str):
                return fresh
            spot = on_plot(w, site, fresh, kind, size, front=True)
        return spot or "your plot has no room for it"
    if z == "yard":
        plot = own_plot(w, site, p, None)
        if isinstance(plot, str):
            return plot
        spot = on_plot(w, site, plot, kind, size, front=False)
        if spot:
            return spot
        # a full yard spills to a craft plot of the household's at the edge (another when those are full)
        crafts = craft_plots(site, p)
        for q in crafts:
            if spot := on_plot(w, site, q, kind, size, front=False):
                return spot
        if len(crafts) < craft_cap(w, site, p):
            craft = plot_for(w, site, household_of(site, p), "craft")
            if isinstance(craft, str):
                return "your yard is full, and the settlement has no room for another plot"
            if spot := on_plot(w, site, craft, kind, size, front=False):
                return spot
        return "your yard and your craft plots are full"
    if z == "edge":
        crafts = craft_plots(site, p)
        craft = crafts[0] if crafts else None
        if craft is None:
            craft = plot_for(w, site, household_of(site, p), "craft")
            if isinstance(craft, str):
                return craft
        spot = on_plot(w, site, craft, kind, size, front=True) or on_plot(w, site, craft, kind, size, front=False)
        if spot:
            return spot
        crafts = craft_plots(site, p)
        for q in crafts:
            if q is not craft and (spot := on_plot(w, site, q, kind, size, front=False)):
                return spot
        if len(crafts) < craft_cap(w, site, p):                                 # a full craft plot: another beside the edge
            more = plot_for(w, site, household_of(site, p), "craft")
            if not isinstance(more, str):
                return on_plot(w, site, more, kind, size, front=True) or "your craft plots are full"
        return "your craft plots are full"
    if z == "commons":
        return place_commons(w, site, kind, size)
    if z == "water":
        return place_water(w, site, kind, size) or place_land(w, p, kind, size, site)
    if z == "burial":
        return place_burial(w, site, kind, size)
    return place_land(w, p, kind, size, site)


class _At:
    """A person as if standing on another tile (a building named at a place one is not at)."""
    def __init__(self, p, x, y):
        self.__dict__.update(p.__dict__)
        self.x, self.y = x, y


def settlement_for(w, p, z):
    """The settlement a building of zone z goes in: the one on p's tile; for a dwelling the nearest within 2 tiles,
    else a homestead founded on p's own tile."""
    site = w.site_of(p.x, p.y)
    if site is None and z != "land":                # in one's settlement's fields: built in the settlement
        fm = w.fieldmap.get(key(p.x, p.y))
        site = w.sites.get(fm["site"]) if fm else None
    if site is None and z in ("yard", "edge") and p.home in w.buildings:
        site = w.sites.get(w.buildings[p.home].site)    # what goes in one's yard goes to one's home's yard
    if site or z not in ("dwelling",):
        return site
    near = [s for s in w.sites.values() if max(abs(s.x - p.x), abs(s.y - p.y)) <= 2]
    if near:
        return min(near, key=lambda s: max(abs(s.x - p.x), abs(s.y - p.y)))
    made = found(w, p.x, p.y, p.people, by=p.id, form="homestead" if town_of(p.people)["form"] == "street" else None)
    return made if not isinstance(made, str) else found(w, p.x, p.y, p.people, by=p.id, form="homestead")


CRAFT_PLOTS = 2          # a household's craft plots at most, and one more for each of its grown people (to 8)


def craft_cap(w, site, p):
    """How many craft plots p's household may hold: CRAFT_PLOTS and one for each grown person working for it."""
    h = household_of(site, p)
    grown = sum(1 for q in w.living() if q.adult(w.tick) and (q.id == h or q.partner == h or h in (q.parents or ()))
                and max(abs(q.x - site.x), abs(q.y - site.y)) <= 2)
    return min(8, CRAFT_PLOTS + grown)


def household_of(site, p):
    """Whose household p works for in the settlement: the holder of their own, partner's or a parent's home plot."""
    for who in (p.id, p.partner, *(p.parents or [])):
        if who is not None and any(q["holder"] == who and q["kind"] in ("cottage", "farmstead", "lord") for q in site.plots):
            return who
    return p.id


def craft_plots(site, p):
    """The craft plots of p's household (one's own, one's partner's, the household's)."""
    hs = {p.id, p.partner, household_of(site, p)} - {None}
    return [q for q in site.plots if q["holder"] in hs and q["kind"] == "craft"]


def own_plot(w, site, p, kind):
    """p's household's plot in the settlement (one's own, one's partner's, a parent's), else a new one."""
    for who in (p.id, p.partner, *(() if kind == "cottage" else (p.parents or []))):
        if who is None:
            continue
        pl = next((q for q in site.plots if q["holder"] == who and q["kind"] in ("cottage", "farmstead", "lord")), None)
        if pl:
            return pl
    if kind is None:
        kind = "cottage"
    return plot_for(w, site, p.id, kind)


def in_plot(w, site, plot, skip=None):
    """The rects of the buildings standing on a plot (but `skip`)."""
    return [(b.pos[0], b.pos[1], b.size[0], b.size[1], b.angle) for b in w.buildings_at(site.x, site.y)
            if b.plot == plot["id"] and b.pos and b.size and b.id != skip]


def upgrade_spot(w, old, kind, people):
    """Where a better home goes (§5.1): on its plot, the old one's place counted free, front first; None if the plot
    cannot hold it."""
    site = w.sites.get(old.site)
    plot = next((q for q in site.plots if q["id"] == old.plot), None) if site else None
    size = footprint(kind, people)
    if plot is None or size is None:
        return None
    return on_plot(w, site, plot, kind, size, front=True, skip=old.id) or on_plot(w, site, plot, kind, size, front=False, skip=old.id)


def on_plot(w, site, plot, kind, size, front, skip=None):
    """A free spot on a plot: the frontage (centred, set back a little, door on the lane) or the yard behind, packed
    from the back; turned with the plot."""
    rect = tuple(plot["rect"])
    pw, pd = rect[2], rect[3]
    bw, bd = size
    if bw > pw - 2 or bd > pd - 2:
        bw, bd = min(bw, pw - 2), min(bd, pd - 2)
    taken = in_plot(w, site, plot, skip)
    spots = []
    if front:
        spots.append((0.0, pd / 2 - bd / 2 - 1.5))
    else:
        # packed from the back, then across: every 1.5 m both ways
        vmax, umax = pd / 2 - bd / 2 - 0.6, pw / 2 - bw / 2 - 0.6
        v = -vmax
        while v <= vmax + 1e-6:
            u = 0.0
            spots.append((0.0, v))
            while u + 1.5 <= umax + 1e-6:
                u += 1.5
                spots += [(-u, v), (u, v)]
            v += 1.5
    for u, v in spots:
        X, Y = G.to_world(rect, u, v)
        r = (X, Y, bw, bd, rect[4])
        if any(G.overlap(r, t, 0.8) for t in taken):
            continue
        a = math.radians(rect[4])
        door = [round(X + math.sin(a) * (bd / 2 + 1), 2), round(Y + math.cos(a) * (bd / 2 + 1), 2)]
        return {"pos": [round(X, 2), round(Y, 2)], "angle": round(rect[4], 2), "size": [bw, bd], "door": door,
                "site": site.id, "plot": plot["id"]}
    return None


def place_commons(w, site, kind, size):
    """On or round the green, door to the green: the small inside it, the large on its rim; then along the main lane."""
    gx, gy, gw, gh, ga = site.green
    obs = obstacles(w, site)
    small = max(size) <= 3 * CELL
    rings = [(min(gw, gh) * 0.25, 0.3)] if small else []
    rings += [(max(gw, gh) / 2 + max(size) / 2 + 3, 0.0), (max(gw, gh) / 2 + max(size) + 10, 0.0)]
    taken_in_green = [(b.pos[0], b.pos[1], b.size[0], b.size[1], b.angle) for b in w.buildings_at(site.x, site.y)
                      if b.pos and b.size and b.plot is None]
    for rad, _ in rings:
        for k in range(24):
            a = k / 24 * math.tau
            X, Y = gx + math.cos(a) * rad, gy + math.sin(a) * rad
            r = (X, Y, size[0], size[1], G.facing(gx - X, gy - Y) if rad > 1 else 0.0)
            inside_green = G.inside(tuple(site.green), X, Y)
            ob = [o for o in obs if not (inside_green and o == tuple(site.green))]
            if inside_green:
                ob = [o for o in ob if o not in taken_in_green] + taken_in_green
            if fits(w, site, r, ob):
                fa = math.radians(r[4])
                door = [round(X + math.sin(fa) * (size[1] / 2 + 1), 2), round(Y + math.cos(fa) * (size[1] / 2 + 1), 2)]
                return {"pos": [round(X, 2), round(Y, 2)], "angle": round(r[4], 2), "size": list(size), "door": door,
                        "site": site.id, "plot": None}
    return "no room round the green"


def place_water(w, site, kind, size):
    ws = water_side(w, site.x, site.y)
    if not ws:
        return None
    obs = obstacles(w, site)
    bx, by = (site.x + 0.5) * TILE_M + ws[0] * (TILE_M / 2 - MARGIN - max(size) / 2 - 1), (site.y + 0.5) * TILE_M + ws[1] * (TILE_M / 2 - MARGIN - max(size) / 2 - 1)
    along = (-ws[1], ws[0])
    for k in range(40):
        s = (k // 2 + 1) * (max(size) + 4) * (1 if k % 2 == 0 else -1)
        X, Y = bx + along[0] * s, by + along[1] * s
        r = (X, Y, size[0], size[1], G.facing(*ws))
        if fits(w, site, r, obs):
            door = [round(X - ws[0] * (size[1] / 2 + 1), 2), round(Y - ws[1] * (size[1] / 2 + 1), 2)]
            return {"pos": [round(X, 2), round(Y, 2)], "angle": round(r[4], 2), "size": list(size), "door": door,
                    "site": site.id, "plot": None}
    return None


def place_burial(w, site, kind, size):
    """The next place in the burial plot's rows; a new burial plot when it is full."""
    for _ in range(2):
        plot = next((q for q in site.plots if q["id"] == site.burial), None) or burial_plot(w, site)
        if plot is None:
            return "no room for the dead"
        spot = on_plot(w, site, plot, kind, size, front=False)
        if spot:
            return spot
        site.burial = None
        burial_plot(w, site)
    return "no room for the dead"


def place_land(w, p, kind, size, site=None):
    """Free ground in p's tile: the first free square spiralling out from the tile's middle, clear of any settlement
    and field layout (as today's free placement, in metres)."""
    size = size or (TILE_M, TILE_M)
    x, y = p.x, p.y
    cx, cy = (x + 0.5) * TILE_M, (y + 0.5) * TILE_M
    if size[0] >= TILE_M:
        return {"pos": [cx, cy], "angle": 0.0, "size": list(size), "door": [cx, cy], "site": None, "plot": None}
    obs = []
    s = w.site_of(x, y)
    if s:
        obs = obstacles(w, s)
        if s.edge:
            xs, ys = [q[0] for q in s.edge], [q[1] for q in s.edge]
            obs.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(xs) - min(xs), max(ys) - min(ys), 0.0))
    for st in w.fieldmap.get(key(x, y), {}).get("strips", []):
        obs.append((st[0], st[1], st[2], st[3], 0.0))
    for b in w.buildings_at(x, y):
        if b.pos and b.size:
            obs.append((b.pos[0], b.pos[1], b.size[0], b.size[1], b.angle))
    probe = Settlement(id=-1, name="", x=x, y=y)
    for ring in range(0, 12):
        for k in range(max(1, ring * 8)):
            a = k / max(1, ring * 8) * math.tau
            X, Y = cx + math.cos(a) * ring * 36, cy + math.sin(a) * ring * 36
            r = (X, Y, size[0], size[1], 0.0)
            if fits(w, probe, r, obs, gap=3):
                return {"pos": [round(X, 2), round(Y, 2)], "angle": 0.0, "size": list(size),
                        "door": [round(X, 2), round(Y + size[1] / 2 + 1, 2)], "site": None, "plot": None}
    return "no free ground here"


# ---------- fields ----------

def furlongs(w, x, y, site):
    """Lay out a field tile once (§3.4): strips 25 x 50 cells, their long way pointing away from the settlement, clear
    of water and of the settlement's own plots."""
    k = key(x, y)
    if k in w.fieldmap:
        return w.fieldmap[k]
    sw, sl = 10 * CELL, 50 * CELL           # a strip 40 x 200 m (open-field strips were long and narrow)
    vertical = abs(y - site.y) >= abs(x - site.x) if (x, y) != (site.x, site.y) else True
    w_, h_ = (sw, sl) if vertical else (sl, sw)
    probe = Settlement(id=-1, name="", x=x, y=y)
    obs = obstacles(w, site) if (x, y) == (site.x, site.y) else []
    if (x, y) == (site.x, site.y) and site.edge:
        xs, ys = [q[0] for q in site.edge], [q[1] for q in site.edge]
        obs.append(((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, max(xs) - min(xs) + 16, max(ys) - min(ys) + 16, 0.0))
    strips = []
    X0, Y0 = x * TILE_M + MARGIN, y * TILE_M + MARGIN
    for j in range(int((TILE_M - 2 * MARGIN) // (h_ + 4))):
        for i in range(int((TILE_M - 2 * MARGIN) // (w_ + 2))):
            X, Y = X0 + i * (w_ + 2) + w_ / 2, Y0 + j * (h_ + 4) + h_ / 2
            r = (X, Y, w_, h_, 0.0)
            if fits(w, probe, r, obs, gap=2) and len(strips) < 80:
                strips.append([round(X, 1), round(Y, 1), w_, h_, 0])
    # the nearest the settlement first: strips are taken in order, so its fields spread out from its edge
    cx, cy = site.centre if site.centre else ((site.x + 0.5) * TILE_M, (site.y + 0.5) * TILE_M)
    strips.sort(key=lambda q: (math.hypot(q[0] - cx, q[1] - cy), q[0], q[1]))
    fm = {"site": site.id, "strips": strips}
    w.fieldmap[k] = fm
    if [x, y] not in site.fields:
        site.fields.append([x, y])
    w.rebuild_many()
    return fm


def strip_for(w, p, site):
    """A free strip for p (§4.6): (tile x, tile y, index) or a reason. One's own tile if it is the settlement's field
    land; then the settlement's field tiles nearest; then a new field tile on rich soil or grass within 3 tiles."""
    on = BUILDINGS["farm"]["roles"]["farm"]["on"]
    def free(x, y):
        fm = w.fieldmap.get(key(x, y))
        if not fm or fm["site"] != site.id:
            return None
        return next((i for i, s in enumerate(fm["strips"]) if s[4] == 0), None)
    if (i := free(p.x, p.y)) is not None:
        return p.x, p.y, i
    for x, y in sorted(site.fields, key=lambda t: max(abs(t[0] - p.x), abs(t[1] - p.y))):
        if (i := free(x, y)) is not None:
            return x, y, i
    tiles = [(site.x + dx, site.y + dy) for dx in range(-3, 4) for dy in range(-3, 4)]      # fields an hour or so out
    tiles.sort(key=lambda t: (max(abs(t[0] - site.x), abs(t[1] - site.y)) == 0, max(abs(t[0] - p.x), abs(t[1] - p.y))))
    for x, y in tiles:
        if not w.inb(x, y) or key(x, y) in w.fieldmap or w.terrain[y][x] not in on:
            continue
        if w.site_of(x, y) is not None and (x, y) != (site.x, site.y):
            continue
        fm = furlongs(w, x, y, site)
        if fm["strips"]:
            return x, y, 0
    return "no free strip of good land near the settlement"


def place_strip(w, p):
    site = w.site_of(p.x, p.y) or next((s for s in w.sites.values() if [p.x, p.y] in s.fields), None)
    if site is None:
        near = [s for s in w.sites.values() if max(abs(s.x - p.x), abs(s.y - p.y)) <= 2]
        site = min(near, key=lambda s: max(abs(s.x - p.x), abs(s.y - p.y))) if near else None
    if site is None and p.home in w.buildings:                  # one's home's settlement, wherever one is
        site = w.sites.get(w.buildings[p.home].site)
    if site is None:                                            # out in the land: a homestead and its fields
        site = settlement_for(w, p, "dwelling")
        if isinstance(site, str):
            site = None
    if site is None:
        return "no settlement's fields here"
    got = strip_for(w, p, site)
    if isinstance(got, str):
        return got
    x, y, i = got
    st = w.fieldmap[key(x, y)]["strips"][i]
    st[4] = -p.id                                   # reserved until the farm stands (the engine puts its id)
    return {"pos": [st[0], st[1]], "angle": 0.0, "size": [st[2], st[3]], "door": [st[0], st[1] - st[3] / 2],
            "site": site.id, "plot": None, "strip": [x, y, i]}


# ---------- feet (§4.3) ----------

def wear(site, X, Y, n=1):
    """Feet passing a 4 x 4 cell block of the settlement this season."""
    k = f"{int(X // (4 * CELL))},{int(Y // (4 * CELL))}"
    site.foot[k] = site.foot.get(k, 0) + n


def lay_paths(w, site, path_at=200):
    """At a season's end: blocks walked `path_at` times outside any plot become paths, each joined to the nearest
    lane point; the count starts again."""
    laid = []
    obs = [tuple(p["rect"]) for p in site.plots]
    for k, n in sorted(site.foot.items()):
        if n < path_at:
            continue
        bx, by = (int(v) for v in k.split(","))
        X, Y = (bx + 0.5) * 4 * CELL, (by + 0.5) * 4 * CELL
        if any(G.inside(o, X, Y) for o in obs):
            continue
        best = None
        for l in site.lanes:
            for q in l["pts"]:
                d = math.hypot(q[0] - X, q[1] - Y)
                if best is None or d < best[0]:
                    best = (d, q)
        if best and best[0] > 4 * CELL:
            site.lanes.append({"id": len(site.lanes) + 1, "pts": [[round(X, 1), round(Y, 1)], list(best[1])], "w": CELL, "kind": "path"})
            laid.append(k)
    site.foot = {}
    return laid
