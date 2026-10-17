"""The settlement planner (docs/towns_spec.md §4): pure functions of the world and a seed, called only when something
is founded, settled or built, never every hour. All in metres (x east, y south); a building's angle in degrees, its
front facing (sin a, cos a).

WP0 (this file's first form) fixes the interfaces the engine, bots, minds and viewer build against, with a trivial
plan: a settlement is its tile's middle, plots stand in one row along a straight lane through it, every building on
its plot's frontage. WP1 replaces the bodies with the five forms (street, waterfront, cluster, ring, scatter), lanes
from feet, plots by kin, placement by zone, fields and furlongs, the edge and vacancy; the signatures stay.
"""
import math
import random

from .content.towns import CELL, footprint, town_of, zone
from .world import TILE_M, Settlement, key


def rng_for(w, site_id, n=0):
    """The planner's randomness: the same plan on every machine."""
    return random.Random(f"{w.cfg['seed']}:{site_id}:{n}")


def spacing_ok(w, x, y, apart=3):
    """No settlement within `apart` land tiles (two villages an hour apart are two villages)."""
    return all(max(abs(s.x - x), abs(s.y - y)) >= apart for s in w.sites.values())


def found(w, x, y, people, by=None, name=None):
    """Found a settlement on land tile (x, y) for a people; returns it, or a reason (str) why not (§4.1)."""
    if not w.inb(x, y) or not w.passable(x, y):
        return "not on open land"
    if w.site_of(x, y) is not None:
        return "a settlement is already here"
    if not spacing_ok(w, x, y):
        return "too near another settlement"
    sid = w.new_id()
    t = town_of(people)
    cx, cy = (x + 0.5) * TILE_M, (y + 0.5) * TILE_M
    lane_w = t["lane"] * CELL
    site = Settlement(id=sid, name=name or "", x=x, y=y, people=people, form=t["form"], founded=w.tick,
                      centre=[cx, cy], green=[cx, cy, 12 * CELL, 8 * CELL],
                      lanes=[{"id": 1, "pts": [[cx - 360, cy], [cx + 360, cy]], "w": lane_w, "kind": "lane"}])
    w.sites[sid] = site
    w.site_at[key(x, y)] = sid
    w.rebuild_many()
    return site


def plot_for(w, site, holder, kind="cottage"):
    """The next free plot (§4.4): here, the next frontage along the lane, alternating sides out from the green."""
    t = town_of(site.people)
    pw, pd = t["plot"][0] * CELL, t["plot"][1] * CELL
    n = len([p for p in site.plots if p["kind"] != "burial"])
    side = 1 if n % 2 == 0 else -1
    along = (n // 2) * pw + site.green[2] / 2 + pw / 2
    lane = site.lanes[0]
    cx, cy = site.centre
    half = lane["w"] / 2
    x = cx + along * (1 if (n // 2) % 2 == 0 else -1)
    y = cy + side * (half + pd / 2)
    plot = {"id": len(site.plots) + 1, "rect": [x, y, pw, pd, 0 if side > 0 else 180], "lane": lane["id"],
            "side": side, "kind": kind, "holder": holder, "since": w.tick}
    site.plots.append(plot)
    return plot


def place(w, p, kind, near=None):
    """Where a building of `kind` goes for p (§4.5): {"pos", "angle", "size", "door", "site", "plot"}, or a reason.
    Trivial plan: on the holder's plot's frontage in the settlement of p's tile (a plot taken if p has none there);
    elsewhere, the middle of p's tile."""
    size = footprint(kind, p.people)
    site = w.site_of(p.x, p.y)
    if site is None or size is None or zone(kind) in ("land", "field"):
        X, Y = (p.x + 0.5) * TILE_M, (p.y + 0.5) * TILE_M
        return {"pos": [X, Y], "angle": 0.0, "size": list(size or (TILE_M, TILE_M)), "door": [X, Y + (size or (0, 0))[1] / 2],
                "site": site.id if site else None, "plot": None}
    plot = next((q for q in site.plots if q["holder"] == p.id and q["kind"] != "burial"), None) or plot_for(w, site, p.id)
    x, y, pw, pd, ang = plot["rect"]
    front = -plot["side"]                       # the front faces the lane
    X, Y = x, y + front * (pd / 2 - size[1] / 2 - CELL)
    angle = 0.0 if front > 0 else 180.0
    a = math.radians(angle)
    door = [X + math.sin(a) * (size[1] / 2 + 1), Y + math.cos(a) * (size[1] / 2 + 1)]
    return {"pos": [X, Y], "angle": angle, "size": list(size), "door": door, "site": site.id, "plot": plot["id"]}


def strip_for(w, p, site):
    """A field strip for p (§4.6): (land tile, strip index) or a reason. Laid out in WP1."""
    return "fields are laid out later (WP1)"
