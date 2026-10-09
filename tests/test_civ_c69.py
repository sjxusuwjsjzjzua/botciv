"""c69 (grand world, Phase 3): ways walked often become trails, quicker to walk; left unwalked they grow over.
The routes people use are worn into the land, and saved with it."""
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.world import World, key


class C69(unittest.TestCase):
    def setUp(self):
        self.w = generate({"seed": 4, "people": 12, "width": 40, "height": 40, "bands": 2, "ai": 0})
        self.e = Engine(self.w)

    def test_a_way_walked_daily_becomes_a_trail_and_grows_over(self):
        w = self.w
        x, y = next((x, y) for y in range(w.h) for x in range(w.w) if w.cost(x, y) == 1 and not w.building_at(x, y))
        i = y * w.w + x
        before = w.cost(x, y)
        for _ in range(25):                      # two passes a day for 25 days (a trail by about the 17th)
            w.foot[i] = w.foot.get(i, 0) + 2
            self.e.trails_day()
        self.assertIn(key(x, y), w.trails)
        self.assertLess(w.cost(x, y), before)
        w2 = World.from_dict(w.to_dict())
        self.assertIn(key(x, y), w2.trails)
        self.assertEqual(w2.cost(x, y), w.cost(x, y))
        for _ in range(20):                      # then no one comes
            self.e.trails_day()
        self.assertNotIn(key(x, y), w.trails)

    def test_walking_wears_the_way(self):
        w = self.w
        p = next(q for q in w.living() if q.adult(w.tick))
        tx, ty = next((x, y) for y in range(w.h) for x in range(w.w) if w.passable(x, y) and abs(x - p.x) + abs(y - p.y) > 6)
        act = {"do": "go"}
        self.assertTrue(self.e.walk(p, act, tx, ty) is not False)
        self.e.step_along(p, act)
        self.assertTrue(w.foot)


if __name__ == "__main__":
    unittest.main()
