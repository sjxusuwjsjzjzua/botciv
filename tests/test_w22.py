"""Rules w22: how long people live and what a child is; asking can be part of a plan, but is not repeated."""
import unittest

from botciv import config
from botciv.engine import Engine
from botciv.log import NullLog
from botciv.prompt import build_prompt
from tests.test_engine import world, place


class W22(unittest.TestCase):
    def setUp(self):
        self.w = world(1)
        self.e = Engine(self.w, NullLog())
        self.a, self.b = self.w.living()[:2]
        for p in (self.a, self.b):
            p.age = self.w.cfg["agent"]["adult_ticks"] + 10
            p.satiety = 20
            p.activity, p.plan, p.routine = None, [], []

    def test_the_rules_say_what_is_true(self):
        c = config.load()
        tpd = c["world"]["ticks_per_day"]
        self.assertEqual(c["agent"]["gestation_ticks"] // tpd, 2)
        tpy = tpd * c["world"]["days_per_season"] * 4
        self.assertEqual(c["agent"]["adult_ticks"] // tpy, 14)                  # rules w38
        self.assertGreaterEqual(c["agent"]["lifespan_years"][0], 60)
        text = build_prompt(self.e, self.a)
        self.assertIn("grown at 14 and live past sixty", text)
        self.assertIn("born two days later", text)

    def test_a_plan_can_end_by_asking(self):
        place(self.w, self.a, 2, 2)
        place(self.w, self.b, 2, 3)
        self.e.apply_decision(self.a, {"action": {"verb": "wait", "qty": 1},
                                       "plan": [{"verb": "ask_child", "target": self.b.name, "name": "Tam"}],
                                       "memory": "m"})
        for _ in range(3):
            self.e.step_activities()
        asks = [p for p in self.w.proposals.values() if p["kind"] == "child" and p["from"] == self.a.id]
        self.assertEqual(len(asks), 1)

    def test_asking_is_not_repeated(self):
        place(self.w, self.a, 2, 2)
        place(self.w, self.b, 2, 3)
        self.e.apply_decision(self.a, {"action": {"verb": "pledge", "target": self.b.name},
                                       "plan": [{"verb": "wait", "qty": 1}], "repeat": True, "memory": "m"})
        self.assertEqual([p["verb"] for p in self.a.routine], ["wait"])


if __name__ == "__main__":
    unittest.main()
