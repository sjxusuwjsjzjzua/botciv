"""Rules w17: hearsay. Speaking, a person can pass on what they themselves have seen or
suffered of someone; those who hear remember who told them, and recall it on meeting."""
import unittest

from botciv.engine import Engine
from botciv.log import NullLog
from botciv.prompt import build_prompt, describe_person
from tests.test_engine import world, open_tile, place


class W17(unittest.TestCase):
    def setUp(self):
        self.w = world(4)
        self.e = Engine(self.w, NullLog())
        self.a, self.b, self.c, self.far = self.w.living()[:4]
        for ag in self.w.living():
            ag.inventory = {}
            ag.ledger = []
            ag.x, ag.y = 0, 0
        x, y = open_tile(self.w)
        place(self.w, self.a, x, y)
        place(self.w, self.b, x + 1, y)
        self.far.x, self.far.y = (23 if x < 12 else 0), (23 if y < 12 else 0)
        self.w.tick = 1

    def speak_of(self, **sp):
        self.e.apply_decision(self.a, {"speech": {"text": "Listen.", "of": self.c.name, **sp},
                                       "action": {"verb": "wait", "qty": 1}, "memory": "m"})

    def test_nothing_to_pass_on_leaves_only_words(self):
        self.speak_of()
        self.assertFalse(any(l[2].startswith("heard") for l in self.b.ledger))
        self.assertIn("nothing", " ".join(str(x) for x in self.a.events))

    def test_a_wrong_travels_to_those_who_hear(self):
        self.w.add_ledger(self.a, self.c.id, "robbed", f"{self.c.name} stole from you")
        self.speak_of()
        heard = [l for l in self.b.ledger if l[1] == self.c.id and l[2] == "heard_wrong"]
        self.assertEqual(len(heard), 1)
        self.assertIn(self.a.name, heard[0][3])
        self.assertIn("stole", heard[0][3])
        self.assertFalse(any(l[2] == "heard_wrong" for l in self.far.ledger))

    def test_passing_on_costs_no_time(self):
        self.w.add_ledger(self.a, self.c.id, "robbed", "stole from you")
        self.speak_of()
        self.assertEqual(self.a.activity["verb"], "wait")

    def test_hearsay_is_recalled_on_meeting(self):
        self.w.add_ledger(self.a, self.c.id, "saw_steal", "you saw them steal")
        self.speak_of()
        self.assertIn(f"{self.a.name} told you they stole", describe_person(self.e, self.b, self.c))

    def test_told_twice_is_remembered_once(self):
        self.w.add_ledger(self.a, self.c.id, "kept", "kept a promise")
        self.speak_of()
        self.speak_of()
        self.assertEqual(sum(1 for l in self.b.ledger if l[2] == "heard_good"), 1)

    def test_offered_only_with_something_to_tell(self):
        self.assertNotIn("of = a name", build_prompt(self.e, self.a))
        self.w.add_ledger(self.a, self.c.id, "robbed", "stole from you")
        self.assertIn("of = a name", build_prompt(self.e, self.a))


if __name__ == "__main__":
    unittest.main()
