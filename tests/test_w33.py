"""Rules w33: two people agree to have a child; it is conceived the first hour, within the days
allowed, that both are well fed and side by side."""
import json
import unittest

from botciv.engine import Engine
from botciv.log import NullLog
from botciv.prompt import build_prompt
from botciv.world import World
from tests.test_engine import world, place, open_tile


class W33(unittest.TestCase):
    def setUp(self):
        self.w = world(1)
        self.e = Engine(self.w, NullLog())
        self.a, self.b = self.w.living()[:2]
        for p in (self.a, self.b):
            p.age = self.w.cfg["agent"]["adult_ticks"] + 10
        x, y = open_tile(self.w)
        place(self.w, self.a, x, y)
        place(self.w, self.b, x + 1, y)

    def agree(self):
        ok, msg = self.e.start(self.a, {"verb": "ask_child", "target": self.b.name, "name": "Tul"})
        self.assertTrue(ok, msg)
        ok, msg = self.e.start(self.b, {"verb": "accept", "id": max(self.w.proposals)})
        self.assertTrue(ok, msg)

    def test_hungry_now_the_child_comes_when_both_are_fed_and_together(self):
        self.a.satiety, self.b.satiety = 8, 15
        self.agree()
        self.assertFalse(self.a.pregnant or self.b.pregnant)
        self.assertEqual(len(self.w.hopes), 1)
        self.assertIn(f"You and {self.a.name} have agreed to have a child", build_prompt(self.e, self.b))
        place(self.w, self.b, self.a.x + 4, self.a.y)
        self.a.satiety = 16
        self.e.hopes_tick()
        self.assertFalse(self.a.pregnant or self.b.pregnant)      # fed, but apart
        place(self.w, self.b, self.a.x + 1, self.a.y)
        self.e.hopes_tick()
        self.assertTrue(self.a.pregnant or self.b.pregnant)
        self.assertEqual(self.w.hopes, [])
        mother = self.a if self.a.pregnant else self.b
        self.assertEqual(mother.pregnant["name"], "Tul")

    def test_fed_and_together_at_once_conceives_at_once(self):
        self.a.satiety = self.b.satiety = 16
        self.agree()
        self.assertTrue(self.a.pregnant)
        self.assertEqual(self.a.satiety, 16 - self.w.cfg["agent"]["child_cost"])

    def test_the_hope_lapses(self):
        self.a.satiety = self.b.satiety = 5
        self.agree()
        self.w.tick += self.w.cfg["agent"]["child_hope_days"] * self.w.tpd()
        self.e.hopes_tick()
        self.assertEqual(self.w.hopes, [])
        self.assertTrue(any("No child came" in t for _, t in self.a.events))

    def test_old_saves_load(self):
        d = self.w.to_dict()
        del d["hopes"]
        self.assertEqual(World.from_dict(json.loads(json.dumps(d))).hopes, [])


if __name__ == "__main__":
    unittest.main()
