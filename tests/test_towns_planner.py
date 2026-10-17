"""The settlement planner (docs/towns_spec.md §4, WP1): every form grows to 60 households with nothing on top of
anything, nothing in the water or off its tile, doors on lanes, fields in strips, and the same plan every time."""
import json
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import townplan  # noqa: E402

from civ import geom as G, towns  # noqa: E402
from civ.content.towns import zone  # noqa: E402
from civ.world import TILE_M, key  # noqa: E402


def rect(b):
    return (b.pos[0], b.pos[1], b.size[0], b.size[1], b.angle)


class Planner(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.grown = {f: townplan.grow(f, 60) for f in townplan.FORM_PEOPLE}

    def test_every_household_has_a_home(self):
        for f, (w, site, refused) in self.grown.items():
            homes = [b for b in w.buildings.values() if zone(b.kind) == "dwelling"]
            self.assertEqual(len(homes), 60, f)
            self.assertFalse([r for r in refused if zone(r[0]) == "dwelling"], f)

    def test_nothing_on_top_of_anything(self):
        for f, (w, site, _) in self.grown.items():
            plots = [tuple(p["rect"]) for p in site.plots]
            for i, a in enumerate(plots):
                for b in plots[i + 1:]:
                    self.assertFalse(G.overlap(a, b), f"{f}: plots overlap")
            bs = [b for b in w.buildings_at(site.x, site.y) if b.pos and b.size]
            for i, a in enumerate(bs):
                for b in bs[i + 1:]:
                    self.assertFalse(G.overlap(rect(a), rect(b)), f"{f}: {a.kind} and {b.kind} overlap")
                if a.plot is not None:
                    pl = next(p for p in site.plots if p["id"] == a.plot)
                    for X, Y in G.corners(rect(a)):
                        self.assertTrue(G.inside((*pl["rect"][:2], pl["rect"][2] + 0.1, pl["rect"][3] + 0.1, pl["rect"][4]), X, Y),
                                        f"{f}: {a.kind} outside its plot")

    def test_dry_and_on_its_tile(self):
        for f, (w, site, _) in self.grown.items():
            for p in site.plots:
                for X, Y in G.corners(tuple(p["rect"])):
                    self.assertEqual((int(X // TILE_M), int(Y // TILE_M)), (site.x, site.y), f)
                    self.assertFalse(towns.is_water(w, X, Y), f)

    def test_doors_on_lanes(self):
        for f, (w, site, _) in self.grown.items():
            if f == "scatter":
                continue
            pts = towns.lane_points(site)
            for b in w.buildings_at(site.x, site.y):
                if zone(b.kind) == "dwelling":
                    d = min(math.hypot(b.door[0] - X, b.door[1] - Y) - hw for X, Y, hw in pts)
                    self.assertLess(d, 4.5, f"{f}: a door {d:.1f} m from the lane")

    def test_fields_in_strips(self):
        for f, (w, site, _) in self.grown.items():
            farms = [b for b in w.buildings.values() if b.kind == "farm"]
            self.assertGreater(len(farms), 20, f)
            for x, y in site.fields:
                strips = w.fieldmap[key(x, y)]["strips"]
                for i, a in enumerate(strips):
                    self.assertIn(w.terrain[y][x], ",.")
                    for b in strips[i + 1:]:
                        self.assertFalse(G.overlap((a[0], a[1], a[2], a[3], 0), (b[0], b[1], b[2], b[3], 0)))

    def test_same_plan_every_time(self):
        w, site, _ = townplan.grow("street", 20)
        w2, site2, _ = townplan.grow("street", 20)
        self.assertEqual(json.dumps(site.plots), json.dumps(site2.plots))
        self.assertEqual(json.dumps(site.lanes), json.dumps(site2.lanes))

    def test_spacing_and_homesteads(self):
        w, site, _ = townplan.grow("street", 2)
        self.assertEqual(towns.found(w, 4, 4, "river"), "too near another settlement")


if __name__ == "__main__":
    unittest.main()
