"""Rules w26: with no berries in sight, the refusal says where the nearest remembered berries are."""
import unittest

from botciv.engine import Engine
from botciv.log import NullLog
from tests.test_engine import world, place


class W26(unittest.TestCase):
    def test_the_refusal_points_to_remembered_berries(self):
        w = world(1)
        e = Engine(w, NullLog())
        a = w.living()[0]
        w.bushes = {}
        place(w, a, 5, 5)
        a.known = {"15,5": ["bush", "berry bush (6 berries then)", w.tick]}
        ok, msg = e.start(a, {"verb": "gather", "item": "berries"})
        self.assertFalse(ok)
        self.assertIn("(15,5), 10 steps away (seen today)", msg)
        a.known = {}
        ok, msg = e.start(a, {"verb": "gather", "item": "berries"})
        self.assertIn("know of no berries", msg)


if __name__ == "__main__":
    unittest.main()
