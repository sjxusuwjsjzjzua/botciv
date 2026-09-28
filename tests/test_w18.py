"""Rules w18: sowing where no farm stands makes the field first; seeds said to be for sowing."""
import unittest

from botciv.engine import Engine
from botciv.log import NullLog
from botciv.world import FERTILE, GRASS
from tests.test_engine import world, open_tile, place


class W18(unittest.TestCase):
    def setUp(self):
        self.w = world(1)
        self.e = Engine(self.w, NullLog())
        self.a = self.w.living()[0]
        self.x, self.y = open_tile(self.w)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if self.w.in_bounds(self.x + dx, self.y + dy):
                    self.set_t(self.x + dx, self.y + dy, GRASS)
        self.w.structures = {k: s for k, s in self.w.structures.items()
                             if max(abs(s.x - self.x), abs(s.y - self.y)) > 1}
        place(self.w, self.a, self.x, self.y)
        self.set_t(self.x, self.y, FERTILE)
        self.a.inventory = {"seeds": 3, "wood": 1}
        self.a.satiety = 20
        self.w.tick = self.w.tpd() * 30                     # not winter

    def set_t(self, x, y, t):
        row = self.w.terrain[y]
        self.w.terrain[y] = row[:x] + t + row[x + 1:]

    def test_plant_on_rich_soil_builds_the_farm_then_sows(self):
        self.e.apply_decision(self.a, {"action": {"verb": "plant", "qty": 3}, "memory": "m"})
        for _ in range(4):
            self.e.step_activities()
        farm = self.w.structure_at(self.x, self.y)
        self.assertIsNotNone(farm)
        self.assertEqual(farm.kind, "farm")
        self.assertTrue(farm.done)
        self.assertEqual(farm.seeds, 3)
        self.assertEqual(self.a.inventory.get("seeds", 0), 0)

    def test_without_wood_it_says_what_is_needed(self):
        self.a.inventory = {"seeds": 3}
        ok, msg = self.e.start(self.a, {"verb": "plant"})
        self.assertFalse(ok)
        self.assertIn("1 wood", msg)

    def test_seeds_are_not_food_but_for_sowing(self):
        ok, msg = self.e.start(self.a, {"verb": "eat", "item": "seeds"})
        self.assertFalse(ok)
        self.assertIn("sown", msg)


if __name__ == "__main__":
    unittest.main()
