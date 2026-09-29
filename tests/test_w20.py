"""Rules w20: fibre, hides and wood left on the ground weather away; bone and stone last."""
import unittest

from botciv.engine import Engine
from botciv.log import NullLog
from botciv.prompt import build_prompt
from botciv.world import key
from tests.test_engine import world, open_tile


class W20(unittest.TestCase):
    def test_left_out_it_weathers_but_bone_and_stone_last(self):
        w = world(1)
        e = Engine(w, NullLog())
        x, y = open_tile(w)
        w.piles = {key(x, y): {"fibre": 40, "wood": 20, "bone": 10, "stone": 5}}
        for _ in range(w.tpd() * 7):
            e.resources()
            w.tick += 1
        p = w.piles.get(key(x, y), {})
        self.assertLess(p.get("fibre", 0), 25)
        self.assertLess(p.get("wood", 0), 20)
        self.assertEqual(p.get("bone"), 10)
        self.assertEqual(p.get("stone"), 5)

    def test_the_rules_say_so(self):
        w = world(1)
        e = Engine(w, NullLog())
        self.assertIn("weather away", build_prompt(e, w.living()[0]))


if __name__ == "__main__":
    unittest.main()
