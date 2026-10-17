"""civ/land_at.py gives the same land as the viewer's civ/viewer/demo/land.js, point for point (towns_spec §2.1)."""
import json, math, os, random, shutil, subprocess, unittest

from civ.land_at import Land, hash2, vnoise

ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA = os.path.join(ROOT, "civ", "viewer", "demo", "river_village.json")
JS = """
import {readFileSync} from "node:fs";
import {hash2, vnoise, LandFn} from "./civ/viewer/demo/land.js";
const d = JSON.parse(readFileSync("civ/viewer/demo/river_village.json", "utf8"));
const land = new LandFn(d.land), pts = JSON.parse(process.argv[1]);
const out = pts.map(([x, y]) => { const g = land.ground(x, y); return [g.h, g.water, g.wet, g.level, land.treeCover(x, y, g.chan)]; });
const hs = pts.map(([x, y], i) => [hash2(Math.floor(x), Math.floor(y), i), vnoise(x / 37, y / 41, i)]);
console.log(JSON.stringify({out, hs}));
"""


class LandAt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(DATA) as f:
            cls.land = Land(json.load(f)["land"])

    def test_hash_is_32_bit_and_spread(self):
        vals = [hash2(i, j, 3) for i in range(-20, 20) for j in range(-20, 20)]
        self.assertTrue(all(0 <= v < 1 for v in vals))
        self.assertGreater(len(set(vals)), 1590)
        self.assertEqual(vnoise(3, 4, 1), hash2(3, 4, 1))

    def test_water_where_the_river_runs(self):
        for s in range(100, int(self.land.river.length) - 100, 311):
            x, y, w = self.land.river.at(s)
            self.assertGreater(self.land.ground(x, y).water, 0.2)

    def test_same_as_the_viewer(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("no node")
        rng = random.Random(5)
        pts = [[rng.uniform(-1500, 7500), rng.uniform(-1000, 4000)] for _ in range(300)]
        pts += [[self.land.river.at(s)[0] + rng.uniform(-30, 30), self.land.river.at(s)[1]] for s in range(0, 12000, 200)]
        pts += [[self.land.stream.at(s)[0], self.land.stream.at(s)[1] + rng.uniform(-8, 8)] for s in range(0, 1900, 50)]
        r = subprocess.run([node, "--input-type=module", "-e", JS, json.dumps(pts)], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr[-2000:])
        js = json.loads(r.stdout)
        for (x, y), got, (hj, nj) in zip(pts, js["out"], js["hs"]):
            g = self.land.ground(x, y)
            mine = [g.h, g.water, g.wet, g.level, self.land.tree_cover(x, y, g.chan)]
            for a, b in zip(mine, got):
                self.assertTrue(math.isclose(a, b, abs_tol=1e-9), f"{x:.1f},{y:.1f}: {mine} vs {got}")
        for i, ((x, y), (hj, nj)) in enumerate(zip(pts, js["hs"])):
            self.assertEqual(hash2(math.floor(x), math.floor(y), i), hj)
            self.assertTrue(math.isclose(vnoise(x / 37, y / 41, i), nj, abs_tol=1e-12))


if __name__ == "__main__":
    unittest.main()
