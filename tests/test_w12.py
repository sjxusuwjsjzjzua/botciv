"""Rules w12: found in bot runs. Build where it fits, sow the farm that is free,
walk as near as you can get."""
import unittest

from botciv.engine import Engine
from botciv.log import NullLog
from botciv.world import Structure, FERTILE
from tests.test_engine import world


class W12(unittest.TestCase):
    def setUp(self):
        self.w = world(2)
        self.e = Engine(self.w, NullLog())
        self.a = self.w.living()[0]

    def farm(self, x, y, owner, **kw):
        s = Structure(id=self.w.new_id(), kind="farm", x=x, y=y, owner=owner, done=True, **kw)
        self.w.structures[s.id] = s
        return s

    def test_building_with_no_place_named_uses_a_free_tile_beside_you(self):
        s = Structure(id=self.w.new_id(), kind="store", x=self.a.x, y=self.a.y, owner=99, done=True)
        self.w.structures[s.id] = s
        self.a.inventory = {"wood": 4}
        ok, msg = self.e.start(self.a, {"verb": "build", "item": "store"})
        self.assertTrue(ok, msg)

    def test_sowing_picks_the_free_farm_not_the_first_one(self):
        cells = [(x, y) for y in range(self.w.h) for x in range(self.w.w - 1)
                 if self.w.t(x, y) == FERTILE and self.w.t(x + 1, y) == FERTILE]
        (x, y) = cells[0]
        self.a.x, self.a.y = x, y
        self.farm(x, y, owner=99, planted=0, seeds=2)
        free = self.farm(x + 1, y, owner=self.a.id)
        self.a.inventory = {"seeds": 3}
        ok, msg = self.e.start(self.a, {"verb": "plant", "qty": 3})
        self.assertTrue(ok, msg)
        self.assertEqual(self.a.activity["sid"], free.id)

    def test_a_walk_with_no_way_through_goes_as_near_as_it_can(self):
        w = self.w
        boxed = [(x, y) for y in range(1, w.h - 1) for x in range(1, w.w - 1)
                 if all(not w.passable(x + dx, y + dy, self.a) for dx in (-1, 0, 1) for dy in (-1, 0, 1))]
        if not boxed:
            self.skipTest("nothing walled in on this map")
        x, y = max(boxed, key=lambda c: abs(c[0] - self.a.x) + abs(c[1] - self.a.y))
        ok, msg = self.e.start(self.a, {"verb": "go", "x": x, "y": y})
        self.assertTrue(ok, msg)
        self.assertIn("as near as you can get", self.a.events[-1][1])


if __name__ == "__main__":
    unittest.main()
