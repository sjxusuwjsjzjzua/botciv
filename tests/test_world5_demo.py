"""world5 step 0's demo scene (docs/world5_handoff.md §5): the data is what tools/demo_village.py makes, laid out sanely
(in metres, nothing in the water, houses inside their plots, the walk reaching the track), and landAt holds in Node
(civ/viewer/demo/test), when Node is at hand."""
import json, math, os, shutil, subprocess, sys, unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "tools"))
import demo_village  # noqa: E402

DATA = os.path.join(ROOT, "civ", "viewer", "demo", "river_village.json")


def inside(pts, x, y):
    c = False
    for i in range(len(pts)):
        (ax, ay), (bx, by) = pts[i - 1], pts[i]
        if (ay > y) != (by > y) and x < ax + (y - ay) / (by - ay) * (bx - ax):
            c = not c
    return c


class Demo(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(DATA) as f:
            cls.d = json.load(f)

    def test_committed_data_is_the_generators(self):
        self.assertEqual(json.loads(json.dumps(demo_village.build(), separators=(",", ":"))), self.d)

    def test_every_house_in_its_plot_facing_the_green(self):
        plots = {p["household"]: p for p in self.d["plots"] if "household" in p}
        cx, cy = self.d["centre"]
        houses = [b for b in self.d["buildings"] if b["kind"] == "long_house"]
        self.assertTrue(8 <= len(houses) <= 14)
        for b in houses:
            x, y = b["pos"]
            self.assertTrue(inside(plots[b["household"]]["pts"], x, y))
            a = math.radians(b["angle"])
            front = (math.sin(a), math.cos(a))
            to_green = (cx - x, cy - y)
            self.assertGreater(front[0] * to_green[0] + front[1] * to_green[1], 0, "the door faces the lane and the green")

    def test_the_walk_reaches_the_track(self):
        walker = next(p for p in self.d["people"] if p["id"] == self.d["walker"])
        track = next(l for l in self.d["lanes"] if l["kind"] == "track")
        self.assertIn(track["pts"][0], walker["path"])
        L = sum(math.dist(walker["path"][k - 1], walker["path"][k]) for k in range(1, len(walker["path"])))
        self.assertGreater(L, 4000, "door to the hamlet, 4-5 km")

    def test_land_at_in_node(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("no node")
        r = subprocess.run([node, "--test", os.path.join(ROOT, "civ", "viewer", "demo", "test", "land.test.js")],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout[-2000:] + r.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
