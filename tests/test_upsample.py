"""The large land (world5.md §2, step 3): a land at twice the scale keeps its coasts, lakes, rivers and regions (the
overlay check), its rivers one tile wide, its places, deposits and beasts on dry land where they were; the same seed
gives the same land."""
import unittest

from civ.realm import generate
from civ.upsample import K, broad_water, components, downsample, upsample


class Upsample(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = generate({"seed": 4, "people": 60, "width": 64, "height": 64}).to_dict()
        cls.u = upsample(cls.d)

    def test_size(self):
        self.assertEqual(len(self.u["terrain"]), 64 * K)
        self.assertTrue(all(len(r) == 64 * K for r in self.u["terrain"]))
        self.assertEqual((self.u["cfg"]["width"], self.u["cfg"]["height"]), (128, 128))

    def test_overlay(self):
        """Seen at the old scale, the new land is the old land (borders wander, nothing moves)."""
        t0, ds = self.d["terrain"], downsample(self.u["terrain"])
        same = sum(a == b for r0, r1 in zip(t0, ds) for a, b in zip(r0, r1))
        self.assertGreater(same / (64 * 64), 0.95)

    def test_water_whole(self):
        """Every body of water is still one (rivers unbroken), and none appears."""
        self.assertEqual(len(components(self.d["terrain"])), len(components(self.u["terrain"])))

    def test_rivers_one_wide(self):
        t0, t1 = self.d["terrain"], self.u["terrain"]
        broad = broad_water(t0)
        rivers = [(x, y) for y in range(64) for x in range(64) if t0[y][x] == "~" and (x, y) not in broad]
        self.assertTrue(rivers)
        for x, y in rivers:
            wet = sum(t1[K * y + j][K * x + i] == "~" for j in range(K) for i in range(K))
            self.assertLess(wet, K * K, (x, y))

    def test_things_in_place(self):
        t1 = self.u["terrain"]
        self.assertEqual(len(self.u["deposits"]), len(self.d["deposits"]))
        for k in self.u["deposits"]:
            X, Y = map(int, k.split(","))
            self.assertNotEqual(t1[Y][X], "~", k)
        for old, new in zip(self.d["places"], self.u["places"]):
            self.assertEqual((new[0] // K, new[1] // K), (old[0], old[1]))
            self.assertEqual(new[2:], old[2:])
        for old, new in zip(self.d["herds"], self.u["herds"]):
            self.assertEqual((new["x"] // K, new["y"] // K), (old["x"], old["y"]))
        for old, new in zip(self.d["regions"], self.u["regions"]):
            self.assertEqual((new["x"], new["y"], new.get("name")), (old["x"] * K, old["y"] * K, old.get("name")))

    def test_regions_follow(self):
        rows0, rows1 = self.d.get("region_rows"), self.u.get("region_rows")
        if not rows0:
            self.skipTest("a land without regions")
        same = sum(rows1[Y][X] == rows0[Y // K][X // K] for Y in range(64 * K) for X in range(64 * K))
        self.assertGreater(same / (64 * K) ** 2, 0.95)

    def test_same_seed_same_land(self):
        self.assertEqual(upsample(self.d)["terrain"], self.u["terrain"])
        self.assertNotEqual(upsample(self.d, seed=99)["terrain"], self.u["terrain"])


class LargeLand(unittest.TestCase):
    def test_founded_on_the_doubled_land(self):
        """generate(upsample=2): the continent made at half size and doubled; peoples settle it, everyone on land."""
        from civ.content import PASSABLE
        w = generate({"seed": 6, "people": 80, "width": 96, "height": 96, "upsample": 2, "format": "towns1"})
        self.assertEqual((len(w.terrain), len(w.terrain[0]), len(w.region_of)), (96, 96, 96 * 96))
        self.assertTrue(w.sites)
        for p in w.living():
            self.assertIn(w.terrain[p.y][p.x], PASSABLE)
        for r in w.regions:
            self.assertEqual(w.region_of[r["y"] * w.w + r["x"]], r["id"])


if __name__ == "__main__":
    unittest.main()
