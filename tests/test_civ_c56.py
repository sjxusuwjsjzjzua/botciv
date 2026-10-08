"""c56: a bot in someone's service works for them: it helps finish the master's building (the master's own
unfinished work is open to one in their service), else brings wood and stone to the master's store."""
import unittest

from civ.content import BUILDINGS
from civ.engine import Engine
from civ.gen import generate
from civ.minds.bot import BotMind
from civ.world import Building


def small(seed=4):
    return generate({"seed": seed, "people": 12, "width": 40, "height": 40, "bands": 2, "ai": 0})


class C56(unittest.TestCase):
    def setUp(self):
        self.w = small()
        self.e = Engine(self.w)
        self.m, self.s = [p for p in self.w.living() if p.adult(self.w.tick)][:2]
        self.s.x, self.s.y = self.m.x, self.m.y
        x, y = next((x, y) for x, y in self.w.beside(self.m.x, self.m.y, 2)
                    if self.w.passable(x, y) and not self.w.building_at(x, y) and (x, y) != (self.m.x, self.m.y))
        self.site = Building(id=self.w.new_id(), kind="shelter", x=x, y=y, owner=self.m.id, done=False,
                             hp=BUILDINGS["shelter"]["hp"])
        self.w.buildings[self.site.id] = self.site
        self.w.at[f"{x},{y}"] = self.site.id

    def test_a_servant_builds_for_the_master(self):
        self.e.begin_service(self.m, self.s, 2)
        got = BotMind(self.e).serve(self.s)
        self.assertEqual(got["plan"][0]["do"], "build")
        ok, why = self.e.start(self.s, {"do": "build", "kind": "shelter", "x": self.site.x, "y": self.site.y})
        self.assertTrue(ok, why)


if __name__ == "__main__":
    unittest.main()
