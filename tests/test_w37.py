"""w37: lighter prompts and fewer decisions. A plan is not dropped for eating what is already
eaten or lifting a pile already gone; a familiar face returning is told, not a reason to decide."""
import unittest

from botciv.engine import Engine
from botciv.log import NullLog
from botciv.prompt import build_prompt
from tests.test_engine import world, place, open_tile


class W37(unittest.TestCase):
    def setUp(self):
        self.w = world(1)
        self.e = Engine(self.w, NullLog())
        self.a, self.b = self.w.living()[:2]
        x, y = open_tile(self.w)
        place(self.w, self.a, x, y)
        place(self.w, self.b, x + 10, y)

    def test_a_passing_step_is_skipped(self):
        self.a.inventory = {}
        self.a.plan = [{"verb": "eat", "item": "berries"}, {"verb": "take", "target": "ground", "item": "wood"},
                       {"verb": "wait", "qty": 2}]
        self.assertTrue(self.e.next_plan_step(self.a))
        self.assertEqual(self.a.activity["verb"], "wait")
        self.assertEqual(self.a.wake, [])

    def test_a_real_failure_still_stops_the_plan(self):
        self.a.inventory = {}
        self.a.plan = [{"verb": "give", "target": "Nobody", "item": "wood"}, {"verb": "wait", "qty": 2}]
        self.assertFalse(self.e.next_plan_step(self.a))
        self.assertTrue(self.a.wake)

    def test_a_familiar_face_is_told_not_woken(self):
        self.a.seen[str(self.b.id)] = self.w.tick - 5 * self.w.tpd() - 1
        self.w.tick += 5 * self.w.tpd()
        place(self.w, self.b, self.a.x + 1, self.a.y)
        self.a.wake = []
        self.e.perceive()
        self.assertFalse(any(self.b.name in r for r in self.a.wake))
        self.assertTrue(any("first time in days" in t for _, t in self.a.events))

    def test_bushes_on_one_line(self):
        p = build_prompt(self.e, self.a)
        self.assertNotIn("- berry bush at", p)


if __name__ == "__main__":
    unittest.main()
