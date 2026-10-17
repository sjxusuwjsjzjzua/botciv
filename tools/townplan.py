"""Grow a settlement with the planner (civ/towns.py) and draw it to scale: towns_spec §12.2 gate 2, the owner's look
at each form at 5, 20 and 60 households before the engine is built on it.

    python tools/townplan.py                      # every form at 5, 20, 60 households -> docs/towns_pics/plan/
    python tools/townplan.py --form street --n 20 --out /tmp/plan.png
"""
import argparse
import math
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from PIL import Image, ImageDraw  # noqa: E402

from civ import towns, geom as G  # noqa: E402
from civ.content.towns import TOWNS, zone  # noqa: E402
from civ.world import World, Building, Person, TILE_M, key  # noqa: E402

FORM_PEOPLE = {"street": "river", "waterfront": "shore", "cluster": "hill", "ring": "riders", "scatter": "forest"}
COL = {"bg": (214, 226, 168), "water": (127, 179, 200), "lane": (226, 205, 150), "path": (214, 196, 150), "green": (170, 207, 127),
       "plot": (228, 235, 200), "fence": (138, 107, 69), "burial": (200, 205, 180), "craft": (230, 214, 190),
       "dwelling": (200, 150, 70), "yard": (165, 118, 63), "commons": (140, 110, 176), "edge": (176, 85, 58),
       "water_b": (60, 100, 140), "grave": (141, 141, 134), "strip": [(215, 196, 106), (159, 191, 90), (181, 138, 79)],
       "text": (58, 47, 34), "edgeline": (120, 100, 70)}


def world_for(form, seed):
    w = World({"seed": seed, "width": 7, "height": 7, "format": "towns1"})
    rows = []
    for y in range(7):
        row = ""
        for x in range(7):
            water = (form == "waterfront" and y == 2) or (form == "street" and x == 3 and y == 1)
            row += "~" if water else ("," if (x + y * 3) % 4 == 0 else ".")
        rows.append(row)
    w.terrain = rows
    return w


def grow(form, n, seed=5):
    """A settlement of `form` grown to n households, each with a home, a store and a few things in its yard; a
    potter's kilns at the edge, a well and a shrine on the green, a hall and market at 40+, graves, fields."""
    w = world_for(form, seed)
    people = FORM_PEOPLE[form]
    r = random.Random(seed)
    site = towns.found(w, 3, 3, people, name=form)
    assert not isinstance(site, str), site

    def person(parents=()):
        p = Person(id=w.new_id(), name=f"p{len(w.people)}", x=3, y=3, born=0, lifespan=9999, people=people, parents=list(parents))
        w.people[p.id] = p
        w.place(p, 3, 3)
        return p

    def build(p, kind):
        pl = towns.place(w, p, kind)
        if isinstance(pl, str):
            return pl
        strip = pl.pop("strip", None)
        b = Building(id=w.new_id(), kind=kind, x=0, y=0, owner=p.id, done=True, style=people, **pl)
        w.place_building(b)
        if strip:
            w.fieldmap[key(strip[0], strip[1])]["strips"][strip[2]][4] = b.id
        return b

    heads, refused = [], []
    for k in ("well", "shrine"):
        build(person(), k)
    for i in range(n):
        parents = [r.choice(heads).id] if heads and r.random() < 0.35 else []
        p = person(parents)
        heads.append(p)
        for kind in ["house" if r.random() < 0.6 else "shelter", "store"] + r.sample(["pen", "oven", "loom", "drying_rack", "fire"], 1):
            got = build(p, kind)
            if isinstance(got, str):
                refused.append((kind, got))
        if i % 6 == 3:
            build(p, "kiln")
        if r.random() < 0.7:
            build(p, "farm")
        if i % 3 == 0:
            build(p, "grave")
        if i in (39, 59):
            build(p, "hall" if i == 39 else "market")
    return w, site, refused


def draw(w, site, path, title):
    S = 1.0                                     # px a metre: the tile is 1000 px
    X0, Y0 = site.centre[0] - 500, site.centre[1] - 500     # the drawing centred on the settlement
    im = Image.new("RGB", (1000, 1060), COL["bg"])
    g = ImageDraw.Draw(im)
    P = lambda X, Y: ((X - X0) * S, (Y - Y0) * S + 60)
    for y in range(site.y - 1, site.y + 2):
        for x in range(site.x - 1, site.x + 2):
            if w.terrain[y][x] == "~":
                a, b = P(x * TILE_M, y * TILE_M), P((x + 1) * TILE_M, (y + 1) * TILE_M)
                g.rectangle([a, b], fill=COL["water"])
    fm = w.fieldmap.get(key(site.x, site.y))
    if fm:
        for i, st in enumerate(fm["strips"]):
            c = COL["strip"][i % 3] if st[4] else (200, 214, 160)
            g.polygon([P(*q) for q in G.corners((st[0], st[1], st[2], st[3], 0.0))], fill=c, outline=(150, 140, 100))
    if site.edge:
        g.polygon([P(*q) for q in site.edge], outline=COL["edgeline"])
    for l in site.lanes:
        g.line([P(*q) for q in l["pts"]], fill=COL["path" if l["kind"] == "path" else "lane"], width=max(1, int(l["w"] * S)), joint="curve")
    g.polygon([P(*q) for q in G.corners(tuple(site.green))], fill=COL["green"])
    for p in site.plots:
        fill = COL["burial"] if p["kind"] == "burial" else COL["craft"] if p["kind"] == "craft" else COL["plot"]
        g.polygon([P(*q) for q in G.corners(tuple(p["rect"]))], fill=fill, outline=COL["fence"])
    for b in w.buildings_at(site.x, site.y):
        if not (b.pos and b.size) or b.kind == "farm":
            continue
        z = zone(b.kind)
        c = COL["grave"] if z == "burial" else COL.get(z, (120, 120, 120))
        g.polygon([P(*q) for q in G.corners((b.pos[0], b.pos[1], b.size[0], b.size[1], b.angle))], fill=c, outline=(60, 45, 30))
        if b.door and z in ("dwelling", "commons"):
            dx, dy = P(*b.door)
            g.ellipse([dx - 1.5, dy - 1.5, dx + 1.5, dy + 1.5], fill=(40, 30, 20))
    g.rectangle([0, 0, 1000, 60], fill=(247, 239, 220))
    homes = sum(1 for b in w.buildings_at(site.x, site.y) if zone(b.kind) == "dwelling")
    g.text((12, 10), title, fill=COL["text"])
    g.text((12, 32), f"{homes} homes, {len([p for p in site.plots if p['kind'] != 'burial'])} plots, {len(site.lanes)} lanes; "
                     f"one land tile, 1 km a side (1 px = 1 m); fields on {len(site.fields)} tiles", fill=COL["text"])
    g.line([(880, 40), (980, 40)], fill=COL["text"], width=3)
    g.text((900, 22), "100 m", fill=COL["text"])
    im.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--form")
    ap.add_argument("--n", type=int)
    ap.add_argument("--out")
    a = ap.parse_args()
    out_dir = os.path.join(os.path.dirname(__file__), "..", "docs", "towns_pics", "plan")
    os.makedirs(out_dir, exist_ok=True)
    forms = [a.form] if a.form else list(FORM_PEOPLE)
    ns = [a.n] if a.n else [5, 20, 60]
    for f in forms:
        for n in ns:
            w, site, refused = grow(f, n)
            path = a.out or os.path.join(out_dir, f"{f}_{n}.png")
            draw(w, site, path, f"{f} ({FORM_PEOPLE[f]}), {n} households")
            print(path, "refused:", len(refused), refused[:3])


if __name__ == "__main__":
    main()
