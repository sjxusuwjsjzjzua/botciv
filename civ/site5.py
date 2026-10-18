"""world5's viewer for a whole towns world (towns_spec §9, WP5): the land, every settlement and the people hour by hour,
written for `viewer/world5.html` (demo/live.js) to stream: one seamless land in metres, no zones.

    python -m civ.site5 --dir <world dir> --out <site dir>     # writes <out>/world5.html, demo/ and live/

<out>/live/land.json: the land as its tiles (LandTiles), its rivers as curves, every settlement's flat ground, field
strips, tracks between neighbours, and the settlements (name, people, form, middle, box, households, people at home);
live/s/<id>.json: one settlement's lanes, plots, buildings, strips and penned beasts, read when the eye comes near;
live/hours.json: the last hours of the log, each person where they stood in metres (null indoors) and what they did.
Read-only: the world is not changed.
"""
import argparse
import glob
import gzip
import json
import math
import os
import shutil
import sys

from .world import TILE_M, TPD
from .run import load

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from tools.demo_from_world import site_parts, river_chains, chaikin, r1, VERBS  # noqa: E402

HOURS = 36                  # hours of the log the viewer plays (three days)


def rivers_of(w):
    """The thin water of the whole land as curves (as tools/demo_from_world.py's window), pulled to the settlement
    beside a tile, a little wandering."""
    from .land_at import vnoise
    chains, broad = river_chains(w.terrain)
    rows = ["".join("r" if c == "~" and (x, y) not in broad else c for x, c in enumerate(r)) for y, r in enumerate(w.terrain)]
    by_tile = {(s.x, s.y): s for s in w.sites.values()}
    out = []
    for ch in chains:
        pts = []
        for x, y in ch:
            X, Y = (x + 0.5) * TILE_M, (y + 0.5) * TILE_M
            nb = next((by_tile[(x + dx, y + dy)] for dx in (-1, 0, 1) for dy in (-1, 0, 1) if (dx or dy) and (x + dx, y + dy) in by_tile), None)
            if nb:
                cx, cy = nb.centre
                d = math.hypot(cx - X, cy - Y) or 1
                pull = max(0.0, d - 140) / d
                X, Y = X + (cx - X) * pull, Y + (cy - Y) * pull
            j = (vnoise(x * 0.7, y * 0.7, 77) - 0.5) * 260
            pts.append([X + j, Y - j])
        width = min(70, 22 + 4 * len(ch))
        out.append({"pts": [[r1(a), r1(b), width] for a, b in chaikin(pts)]})
    return rows, out


def tracks_of(w):
    """A track from each settlement to its nearest neighbour (the engine's roads come later), out of their lanes' ends."""
    sites = list(w.sites.values())
    if len(sites) < 2:
        return []

    def way_out(s, to):
        ends = [l["pts"][k] for l in s.lanes if l["kind"] in ("lane", "path") for k in (0, -1)]
        return min(ends, key=lambda q: math.hypot(q[0] - to[0], q[1] - to[1])) if ends else s.centre
    pairs = set()
    for s in sites:
        o = min((o for o in sites if o is not s), key=lambda o: math.hypot(o.centre[0] - s.centre[0], o.centre[1] - s.centre[1]))
        if math.hypot(o.centre[0] - s.centre[0], o.centre[1] - s.centre[1]) < 40 * TILE_M:
            pairs.add(tuple(sorted((s.id, o.id))))
    out = []
    for i, j in sorted(pairs):
        si, sj = w.sites[i], w.sites[j]
        a, b = way_out(si, sj.centre), way_out(sj, si.centre)
        mid = [(a[0] + b[0]) / 2 + (b[1] - a[1]) * 0.08, (a[1] + b[1]) / 2 - (b[0] - a[0]) * 0.08]
        out.append({"pts": [[r1(a[0]), r1(a[1])], [r1(mid[0]), r1(mid[1])], [r1(b[0]), r1(b[1])]], "w": 3, "kind": "track", "sites": [i, j]})
    return out


def hours_of(d, w):
    """The last HOURS hours of frames that carry metres: [t, [[id, X, Y, verb] | [id] indoors ...]]."""
    frames = []
    for f in sorted(glob.glob(os.path.join(d, "log", "frames-*.jsonl.gz"))):
        with gzip.open(f, "rt") as fh:
            for line in fh:
                if '"p"' not in line[:40]:
                    continue
                fr = json.loads(line)
                if "p" in fr and fr["p"] and len(fr["p"][0]) > 7:
                    frames.append(fr)
                    frames = frames[-HOURS:]
    out = []
    for fr in frames:
        row = []
        for q in fr["p"]:
            pos = q[7]
            do = q[5]
            verb = "walk" if do in ("go", "walk", "follow") else do if do in VERBS else "rest" if do == "rest" else "talk"
            row.append([q[0], pos[0], pos[1], verb] if pos else [q[0]])
        out.append([fr["t"], row])
    if not out:                 # no log with metres yet: the world as it stands, one hour
        row = [[p.id, round(p.pos[0]), round(p.pos[1]), "rest" if p.rest else "talk"] if p.pos and not p.inside else [p.id]
               for p in w.living()]
        out.append([w.tick, row])
    return out


def build(d, out, name=""):
    w = load(d)
    if w.cfg.get("format") != "towns1":
        raise SystemExit("not a towns world")
    here = os.path.join(os.path.dirname(__file__), "viewer")
    for sub in ("demo", "art", "scene", "vendor"):
        shutil.rmtree(os.path.join(out, sub), ignore_errors=True)
        shutil.copytree(os.path.join(here, sub), os.path.join(out, sub),
                        ignore=shutil.ignore_patterns("test", "*.test.js", "__pycache__", "*.json"))
    shutil.copy(os.path.join(here, "world5.html"), os.path.join(out, "world5.html"))
    live = os.path.join(out, "live")
    shutil.rmtree(live, ignore_errors=True)
    os.makedirs(os.path.join(live, "s"))
    P = lambda X, Y: [r1(X), r1(Y)]
    rows, rivers = rivers_of(w)
    sites, strips, flats = [], [], []
    at_home = {}
    for p in w.living():
        b = w.buildings.get(p.home) if p.home else None
        if b is not None and b.site is not None:
            at_home[b.site] = at_home.get(b.site, 0) + 1
    for s in sorted(w.sites.values(), key=lambda s: s.id):
        got = site_parts(w, s, P, 0, 0)
        del got["people"]
        g = s.green
        got["green"] = {"pos": P(g[0], g[1]), "r": [r1(g[2] / 2), r1(g[3] / 2)]} if g else {"pos": P(*s.centre), "r": [6, 6]}
        got["centre"] = P(*s.centre)
        xs = [q[0] for k in ("plots", "fields") for o in got[k] for q in o["pts"]] + [b["pos"][0] for b in got["buildings"]] + [s.centre[0]]
        ys = [q[1] for k in ("plots", "fields") for o in got[k] for q in o["pts"]] + [b["pos"][1] for b in got["buildings"]] + [s.centre[1]]
        hx = [b["pos"][0] for b in got["buildings"]] + [s.centre[0]]
        hy = [b["pos"][1] for b in got["buildings"]] + [s.centre[1]]
        got["paint"] = [r1(min(hx) - 60), r1(min(hy) - 60), r1(max(hx) - min(hx) + 120), r1(max(hy) - min(hy) + 120)]
        with open(os.path.join(live, "s", f"{s.id}.json"), "w") as f:
            json.dump(got, f, separators=(",", ":"))
        strips += [{"pts": f["pts"], "crop": f["crop"]} for f in got["fields"]]
        flats.append([*P(*s.centre), 260 if s.form != "homestead" else 120])
        sites.append({"id": s.id, "name": s.name, "people": s.people, "form": s.form, "centre": P(*s.centre),
                      "box": [r1(min(xs)), r1(min(ys)), r1(max(xs)), r1(max(ys))], "households": got["households"],
                      "living": at_home.get(s.id, 0)})
    land = {"tiles": rows, "x0": 0, "y0": 0, "tile": TILE_M, "seed": w.seed, "water_level": 0, "rivers": rivers,
            "flats": flats, "box": [0, 0, w.w * TILE_M, w.h * TILE_M], "strips": strips}
    hours = hours_of(d, w)
    people = {str(p.id): [p.name, int(p.age(w.tick)), p.parents[:2]] for p in w.living()}
    with open(os.path.join(live, "land.json"), "w") as f:
        json.dump({"format": "world5-live-1", "units": "metres, x east, y south; angle: degrees, front faces (sin a, cos a)",
                   "name": name, "day": w.tick // TPD, "tick": w.tick, "tpd": TPD, "season": w.season(), "year": w.year() + 1,
                   "land": land, "tracks": tracks_of(w), "sites": sites}, f, separators=(",", ":"))
    with open(os.path.join(live, "hours.json"), "w") as f:
        json.dump({"hours": hours, "people": people}, f, separators=(",", ":"))
    size = sum(os.path.getsize(os.path.join(r, n)) for r, _, ns in os.walk(live) for n in ns)
    print(f"world5 viewer: {len(sites)} settlements, {len(strips)} strips, {len(rivers)} rivers, {len(hours)} hours of "
          f"{len(people)} people; {size // 1024} KB -> {live}")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--name", default="")
    a = ap.parse_args(argv)
    build(a.dir, a.out, a.name)


if __name__ == "__main__":
    main()
