"""c52: a tablet fired in a kiln is taken out on a later plan; a craft takes what it lacks from one's own store
or the kiln that fired it; the steps people write loosely are understood (do with act, go home, x:..,y:..,
accept naming the offer in choice)."""
import unittest

from civ.content import BUILDINGS
from civ.engine import Engine
from civ.gen import generate
from civ.plan import Planner
from civ.acts import coords
from civ.world import Building


def small(seed=4):
    return generate({"seed": seed, "people": 12, "width": 40, "height": 40, "bands": 2, "ai": 0})


def place(w, kind, owner, near):
    x, y = next((x, y) for x, y in w.beside(near.x, near.y, 3)
                if w.passable(x, y) and not w.building_at(x, y) and (x, y) != (near.x, near.y))
    b = Building(id=w.new_id(), kind=kind, x=x, y=y, owner=owner, done=True, hp=BUILDINGS[kind]["hp"])
    w.buildings[b.id] = b
    w.at[f"{x},{y}"] = b.id
    return b


class C52(unittest.TestCase):
    def setUp(self):
        self.w = small()
        self.e = Engine(self.w)
        self.p = self.w.living()[0]
        self.p.act = None

    def test_a_tablet_fired_is_taken_out_later(self):
        from civ.minds.bot import BotMind
        p = self.p
        p.skills["pottery"] = 0.5
        p.inv.update({"clay": 2, "wood": 1})
        kiln = place(self.w, "kiln", p.id, p)
        get, ready = BotMind(self.e).tablet(p)
        self.assertEqual([s["do"] for s in get], ["craft"])
        self.assertFalse(ready)
        kiln.inv["tablet"] = 4
        p.inv = {}
        get, ready = BotMind(self.e).tablet(p)
        self.assertEqual([s["do"] for s in get], ["take"])
        self.assertTrue(ready)

    def test_a_craft_takes_what_it_lacks_from_the_kiln(self):
        p = self.p
        p.skills.update({"charcoal_burning": 0.5, "smelting": 0.3})
        p.inv["copper_ore"] = 2
        kiln = place(self.w, "kiln", p.id, p)
        kiln.inv["charcoal"] = 4
        place(self.w, "furnace", p.id, p)
        p.intent = {"goal": "", "plan": []}
        ok, why = self.e.start(p, {"do": "craft", "item": "copper"})
        self.assertTrue(ok, why)
        self.assertEqual(p.act["do"], "take")

    def test_loose_steps(self):
        p = self.p
        self.assertEqual(coords("x:32,y:28"), (32, 28))
        ok, why = self.e.start(p, {"do": "do", "act": "look around", "hours": 1})
        self.assertTrue(ok, why)
        ok, why = self.e.start(p, {"do": "do", "hours": 1})
        self.assertTrue(ok, why)
        home = place(self.w, "shelter", p.id, p)
        p.home = home.id
        ok, why = self.e.start(p, {"do": "go", "place": "home"})
        self.assertTrue(ok, why)
        p.act = None
        p.inv["fibre"] = 3
        ok, why = self.e.start(p, {"do": "craft", "item": "cordage"})      # a craft named: its simplest thing
        self.assertTrue(ok, why)
        self.assertEqual(p.act["do"], "craft")


if __name__ == "__main__":
    unittest.main()
