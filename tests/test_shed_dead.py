"""The dead a year past keep only their kin in mind (World.shed_the_dead): the saved state stays under GitHub's
100 MB a file (world4, 2026-10-28)."""
import unittest

from civ.realm import generate
from civ.world import TPY


class Shed(unittest.TestCase):
    def test_dead_keep_kin_only(self):
        w = generate({"seed": 5, "people": 40, "width": 32, "height": 32})
        a, b, c = w.living()[:3]
        a.rel = {str(b.id): {"trust": 0.9, "met": 0, "kin": "child"}, str(c.id): {"trust": -0.5, "met": 0}}
        a.ledger, a.known, a.news = [[0, c.id, "theft", "x"]], {"1,1": ["deposit", "clay", 0]}, {"7": [0, 0]}
        a.alive, a.died = False, w.tick
        b.rel = {str(c.id): {"trust": 0.2, "met": 0}}
        w.shed_the_dead()
        self.assertEqual(len(a.rel), 2)                 # dead under a year: kept whole
        w.tick += TPY + 1
        w.shed_the_dead()
        self.assertEqual(list(a.rel), [str(b.id)])
        self.assertEqual((a.ledger, a.known, a.news), ([], {}, {}))
        self.assertEqual(list(b.rel), [str(c.id)])      # the living untouched


if __name__ == "__main__":
    unittest.main()
