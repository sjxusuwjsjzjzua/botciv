"""c68 (grand world, Phase 3): no one keeps ten crafts sharp. A craft unpractised a season grows rusty (an eighth of
the skill above a beginner's), never below a beginner's; masters work faster and often get one more."""
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.prompt import build_prompt
from civ.world import TPD, DPS


class C68(unittest.TestCase):
    def setUp(self):
        self.w = generate({"seed": 4, "people": 12, "width": 40, "height": 40, "bands": 2, "ai": 0})
        self.e = Engine(self.w)
        self.p = next(q for q in self.w.living() if q.adult(self.w.tick))

    def test_unpractised_crafts_grow_rusty_practised_ones_do_not(self):
        p, w = self.p, self.w
        p.skills["pottery"], p.skills["weaving"] = 0.8, 0.8
        self.e.fade()                               # the clock starts
        for _ in range(8):                          # two years
            w.tick += TPD * DPS
            self.e.practise(p, "weaving", 0.0)
            self.e.fade()
        self.assertEqual(p.skills["weaving"], 0.8)
        self.assertLess(p.skills["pottery"], 0.5)
        self.assertGreater(p.skills["pottery"], 0.25)
        for _ in range(40):
            w.tick += TPD * DPS
            self.e.fade()
        self.assertGreaterEqual(p.skills["pottery"], 0.25)

    def test_a_master_is_quicker(self):
        p = self.p

        def hours(skill):
            p.inv = {"fibre": 30}
            p.skills["cordage"] = skill
            p.act = None
            self.assertTrue(self.e.start(p, {"do": "craft", "item": "basket", "n": 1})[0])
            n = 0
            while p.act and n < 50:
                n += 1
                st, _ = self.e.do_craft(p, p.act)
                if st != "go":
                    break
            return n
        self.assertLess(hours(1.0), hours(0.0))

    def test_the_rules_say_it(self):
        self.assertIn("grows rusty", build_prompt(self.e, self.p))


if __name__ == "__main__":
    unittest.main()
