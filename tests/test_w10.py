"""Rules w10: food that rots is noticed; knowing how is rare; strangers fill an empty land."""
import unittest

from botciv.engine import Engine
from botciv.log import NullLog
from botciv.world import Structure
from tests.test_engine import world


class W10(unittest.TestCase):
    def setUp(self):
        self.w = world(2)
        self.e = Engine(self.w, NullLog())
        self.a = self.w.living()[0]

    def test_carried_food_that_rots_is_told_at_dawn(self):
        self.a.inventory = {"fish": 40}
        self.w.tick = 1
        for _ in range(self.w.tpd()):
            self.e.step_world()                    # through to the next dawn
        told = [t for _, t in self.a.events if "went bad" in t]
        self.assertTrue(told, "no word of rot")
        self.assertIn("fish", told[-1])
        self.assertLess(self.a.inventory.get("fish", 0), 40)
        self.assertEqual(self.a.rot, {})

    def test_the_next_person_at_a_store_hears_what_rotted(self):
        s = Structure(id=self.w.new_id(), kind="store", x=self.a.x, y=self.a.y, owner=self.a.id, done=True,
                      inventory={"berries": 1}, rotted={"berries": 3})
        self.w.structures[s.id] = s
        self.a.inventory = {"berries": 2}
        self.e.apply_decision(self.a, {"action": {"verb": "put", "item": "berries", "qty": 2}, "memory": "m"})
        self.e.step_activities()
        self.assertTrue(any("went bad" in t for _, t in self.a.events))
        self.assertEqual(s.rotted, {})

    def test_the_census_counts_the_food_that_rotted(self):
        class L:
            recent = []
            def __init__(self): self.rows = []
            def write(self, obj, *_): self.rows.append(obj)
        log = L()
        e = Engine(self.w, log)
        self.a.inventory = {"fish": 60}
        for _ in range(2 * self.w.tpd()):
            e.step_world()
        census = [r for r in log.rows if r.get("kind") == "census"]
        self.assertTrue(census and max(c["rot"] for c in census) > 0)

    def test_strangers_come_more_often_to_an_empty_land(self):
        def arrivals(keep):
            w = world(5)
            e = Engine(w, NullLog())
            n = 0
            for _ in range(40 * w.tpd()):
                living = w.living()
                for a in living[keep:]:
                    a.alive = False                # hold the population down
                before = len(w.agents)
                e.life_tick()
                n += len(w.agents) - before
            return n
        self.assertGreater(arrivals(3), arrivals(14))

    def test_a_farm_can_be_built_on_rich_soil(self):
        from botciv.world import FERTILE
        spot = next((x, y) for y in range(self.w.h) for x in range(self.w.w) if self.w.t(x, y) == FERTILE)
        self.a.x, self.a.y = spot
        self.a.inventory = {"wood": 1}
        ok, msg = self.e.start(self.a, {"verb": "build", "item": "farm", "x": spot[0], "y": spot[1]})
        self.assertTrue(ok, msg)
        ok, msg = self.e.start(self.a, {"verb": "build", "item": "a small farm"})
        self.assertNotIn("you can build", msg)


if __name__ == "__main__":
    unittest.main()
