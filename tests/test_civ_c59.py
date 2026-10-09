"""c59: buildings weather and fall unless mended; anyone in the owner's service may mend; a field sown or a fire
fed is kept up; bots mend what is theirs, and with more worn than they can keep up, hire a neighbour."""
import unittest

from civ.content import BUILDINGS
from civ.engine import Engine
from civ.gen import generate
from civ.minds.bot import BotMind
from civ.prompt import build_prompt
from civ.world import Building


def small(seed=4):
    return generate({"seed": seed, "people": 12, "width": 40, "height": 40, "bands": 2, "ai": 0})


def place(w, kind, owner, near, r=3):
    x, y = next((x, y) for x, y in w.beside(near.x, near.y, r)
                if w.passable(x, y) and not w.building_at(x, y) and (x, y) != (near.x, near.y))
    b = Building(id=w.new_id(), kind=kind, x=x, y=y, owner=owner, done=True, hp=BUILDINGS[kind]["hp"])
    w.buildings[b.id] = b
    w.at[f"{x},{y}"] = b.id
    return b


class C59(unittest.TestCase):
    def setUp(self):
        self.w = small()
        self.e = Engine(self.w)
        self.p, self.o = [q for q in self.w.living() if q.adult(self.w.tick)][:2]
        self.p.act = self.o.act = None

    def test_an_owned_building_falls_unless_mended(self):
        b = place(self.w, "shelter", self.p.id, self.p)
        for _ in range(BUILDINGS["shelter"]["hp"] - 1):
            self.e.ruin()
        self.assertIn(b.id, self.w.buildings)
        self.assertIn("mend it", build_prompt(self.e, self.p))
        self.e.ruin()
        self.assertNotIn(b.id, self.w.buildings)

    def test_mending_makes_it_whole(self):
        b = place(self.w, "shelter", self.p.id, self.p, r=1)
        b.hp = 3
        self.p.x, self.p.y = b.x, b.y
        self.p.inv["fibre"] = 1
        ok, why = self.e.start(self.p, {"do": "mend", "x": b.x, "y": b.y})
        self.assertTrue(ok, why)
        for _ in range(3):
            self.e.tick(lambda people: {})
        self.assertEqual(b.hp, BUILDINGS["shelter"]["hp"])

    def test_only_the_owner_or_one_in_their_service_mends(self):
        b = place(self.w, "shelter", self.p.id, self.o)
        b.hp = 3
        self.o.inv["fibre"] = 1
        ok, why = self.e.start(self.o, {"do": "mend", "x": b.x, "y": b.y})
        self.assertFalse(ok)
        self.e.begin_service(self.p, self.o, 1)
        ok, why = self.e.start(self.o, {"do": "mend", "x": b.x, "y": b.y})
        self.assertTrue(ok, why)

    def test_bots_mend_and_hire_menders(self):
        p, o = self.p, self.o
        worn = [place(self.w, "shelter", p.id, p) for _ in range(4)]
        for b in worn:
            b.hp = 2
        p.inv = {"smoked_meat": 12, "wood": 3}
        o.inv = {}
        o.x, o.y = p.x, p.y
        got = BotMind(self.e).upkeep_goal(p)
        self.assertEqual(got["plan"][0]["do"], "propose")
        self.e.begin_service(p, o, 1)
        o.inv = {"fibre": 2}
        got = BotMind(self.e).serve(o)
        self.assertEqual(got["plan"][-1]["do"], "mend")


if __name__ == "__main__":
    unittest.main()
