"""docs/grand.md section 9: the measures of a grand world, read from a world's state and events."""
import unittest

from civ.census import measures, settlements
from civ.engine import Engine
from civ.gen import generate
from civ.world import Building, key


class Measures(unittest.TestCase):
    def setUp(self):
        self.w = generate({"seed": 3, "people": 20, "width": 40, "height": 40, "bands": 2, "ai": 0})
        self.e = Engine(self.w)

    def test_making_trading_and_the_ground_are_counted(self):
        a, b, c = self.w.living()[:3]
        ev = [{"kind": "made", "who": [a.id], "craft": "pottery", "item": "pot", "qty": 9},
              {"kind": "made", "who": [b.id], "craft": "pottery", "item": "pot", "qty": 1},
              {"kind": "trade", "who": [c.id, a.id], "times": 2, "give": {"pot": 2}, "get": {"grain": 4}},
              {"kind": "give", "who": [a.id, c.id], "item": "pot", "qty": 1},
              {"kind": "death", "who": [b.id], "cause": "killed by Someone"},
              {"kind": "death", "who": [b.id], "cause": "killed by wolves"}]
        self.w.piles[key(1, 1)] = {"wood": 40}
        m = measures(self.w, ev, 1.0)
        self.assertEqual(m["made"], 10)
        self.assertEqual(m["top_tenth_share"], 0.9)        # one maker of two is the top tenth: 9 of 10
        self.assertEqual(m["moved_share"], 0.3)            # 2 traded and 1 given, of 10 made
        self.assertEqual((m["violent_deaths"], m["deaths"]), (1, 2))
        self.assertEqual(m["ground_per_person"], round(40 / len(self.w.living()), 1))
        self.assertGreater(m["able_per_adult"], 0)

    def test_homes_close_together_are_one_settlement(self):
        ps = self.w.living()[:6]
        for i, p in enumerate(ps):
            x, y = (5 + 2 * i, 5) if i < 4 else (30, 30 + i)
            b = Building(id=self.w.new_id(), kind="shelter", x=x, y=y, owner=p.id, done=True)
            self.w.buildings[b.id] = b
            p.home = b.id
        for p in self.w.living()[6:]:
            p.home = None
        self.assertEqual(settlements(self.w), [4, 2])


if __name__ == "__main__":
    unittest.main()
