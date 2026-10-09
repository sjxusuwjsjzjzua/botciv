"""c64 (M2): waters that can be fished out. Each stretch of water (8 by 8 tiles) holds fish, so many a water tile;
catches draw it down, bites come slower as it thins, and it breeds back over weeks. One fishing there hears so,
and sees it."""
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.prompt import build_prompt
from civ.world import TPD


class C64(unittest.TestCase):
    def setUp(self):
        self.w = generate({"seed": 4, "people": 12, "width": 40, "height": 40, "bands": 2, "ai": 0})
        self.e = Engine(self.w)
        self.p = next(q for q in self.w.living() if q.adult(self.w.tick))
        x, y = next((x, y) for y in range(self.w.h) for x in range(self.w.w)
                    if self.w.passable(x, y) and any(self.w.t(i, j) == "~" for i, j in self.w.beside(x, y)))
        self.w.place(self.p, x, y)
        self.p.act, self.p.intent = None, {"goal": "", "plan": []}

    def test_a_water_fished_down_bites_less_and_says_so(self):
        cell, bite = self.e.fish_here(self.p)
        self.assertEqual(bite, 1.0)
        self.w.fish[cell] = self.w.fish_cap(cell) * 0.1
        self.assertLess(self.e.fish_here(self.p)[1], 0.5)
        self.assertIn("fished thin", build_prompt(self.e, self.p))

    def test_catches_draw_it_down_and_it_breeds_back(self):
        cell, _ = self.e.fish_here(self.p)
        self.p.skills["fish"] = 1.0
        self.p.inv["net"] = 1
        self.assertIs(self.e.start(self.p, {"do": "fish", "hours": 12})[0], True)
        while self.p.act:
            st, _ = self.e.do_fish(self.p, self.p.act)
            if st != "go":
                self.p.act = None
        self.assertLess(self.w.fish_left(cell), self.w.fish_cap(cell))
        self.w.fish[cell] = self.w.fish_cap(cell) / 2
        before = self.w.fish[cell]
        self.e.fish_day()
        self.assertGreater(self.w.fish[cell], before)

    def test_old_saves_load(self):
        from civ.world import World
        d = self.w.to_dict()
        d.pop("fish")
        self.assertEqual(World.from_dict(d).fish, {})


if __name__ == "__main__":
    unittest.main()
