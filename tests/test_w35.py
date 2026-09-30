"""Rules w35: sickness. It comes now and then, passes to those beside the sick, wears the sick
down instead of letting them heal, and passes sooner with rest, food, shelter and company. Those
who stayed by the sick are remembered for it; a poultice ends it."""
import json
import unittest

from botciv.engine import Engine
from botciv.log import NullLog
from botciv.prompt import build_prompt
from botciv.world import World
from tests.test_engine import world, place, open_tile


class W35(unittest.TestCase):
    def setUp(self):
        self.w = world(1)
        self.e = Engine(self.w, NullLog())
        self.a, self.b = self.w.living()[:2]
        x, y = open_tile(self.w)
        place(self.w, self.a, x, y)
        place(self.w, self.b, x + 1, y)

    def test_falling_sick_is_seen_and_told(self):
        self.w.cfg["sickness"]["chance"] = 1.0
        self.assertTrue(self.e.falls_sick(self.a))
        self.assertIn("You are sick", build_prompt(self.e, self.a))
        self.assertIn("looks sick", build_prompt(self.e, self.b))

    def test_it_passes_to_those_beside(self):
        self.w.cfg["sickness"]["chance"] = 0.0
        self.w.cfg["sickness"]["catch"] = 1.0
        self.a.sick = {"since": 0, "carers": []}
        self.assertTrue(self.e.falls_sick(self.b))
        place(self.w, self.b, self.a.x + 3, self.a.y)
        self.b.sick = None
        self.assertFalse(self.e.falls_sick(self.b))

    def test_carers_are_remembered_when_it_passes(self):
        self.w.cfg["sickness"]["mend"] = 1.0
        self.a.sick = {"since": 0, "carers": []}
        self.e.sickness(self.a, False)
        self.assertIsNone(self.a.sick)
        self.assertTrue(any(k == "cared" and oid == self.b.id for _, oid, k, _ in self.a.ledger))
        _, goods = self.e.tellable(self.a, self.b)
        self.assertTrue(any("sickness" in g for g in goods))

    def test_the_sick_weaken_and_can_die(self):
        self.w.cfg["sickness"].update(mend=0.0, lose=1.0)
        place(self.w, self.b, self.a.x + 5, self.a.y)
        self.a.sick = {"since": 0, "carers": []}
        self.a.health = 1
        self.assertTrue(self.e.sickness(self.a, False))
        self.assertEqual(self.a.cause, "died of sickness")

    def test_a_poultice_ends_it(self):
        self.a.sick = {"since": 0, "carers": []}
        self.a.inventory = {"poultice": 1}
        self.e.do_eat(self.a, {"item": "poultice", "qty": 1})
        self.assertIsNone(self.a.sick)

    def test_no_healing_while_sick(self):
        self.w.cfg["sickness"].update(mend=0.0, lose=0.0, chance=0.0)
        self.a.sick = {"since": 0, "carers": []}
        self.a.health, self.a.satiety = 5, 18
        for _ in range(12):
            self.e.needs()
            self.w.tick += 1
        self.assertEqual(self.a.health, 5)

    def test_old_saves_load(self):
        d = self.w.to_dict()
        for v in d["agents"].values():
            v.pop("sick", None)
        w2 = World.from_dict(json.loads(json.dumps(d)))
        self.assertIsNone(next(iter(w2.agents.values())).sick)


if __name__ == "__main__":
    unittest.main()
