"""Who a person becomes: a line on themselves, and a few things they keep for life."""
import unittest

from botciv.engine import Engine
from botciv.log import NullLog
from botciv.prompt import build_prompt, response_schema, VERB_HELP
from tests.test_engine import world


class Self(unittest.TestCase):
    def setUp(self):
        self.w = world(1)
        self.e = Engine(self.w, NullLog())
        self.a = self.w.living()[0]

    def decide(self, **kw):
        if "who" in kw:
            kw["self"] = kw.pop("who")
        self.e.apply_decision(self.a, {"action": {"verb": "wait"}, "memory": "m", **kw})

    def test_self_view_is_kept_and_shown(self):
        self.decide(who="Hardened by hunger, I trust only my kin now.")
        self.assertIn("Who you have become, in your own words: Hardened by hunger", build_prompt(self.e, self.a))
        self.decide()                                   # left out: unchanged
        self.assertTrue(self.a.self_view.startswith("Hardened"))

    def test_one_line_a_day_and_the_first_is_never_dropped(self):
        tpd = self.w.tpd()
        self.decide(remember="The winter my mother died, I learned to keep a store.")
        self.decide(remember="Something else the same day.")
        self.assertEqual(len(self.a.life), 1)          # the same day's line replaced
        for d in range(1, 10):
            self.w.tick += tpd
            self.decide(remember=f"A thing that changed me on day {d}.")
        self.assertEqual(len(self.a.life), self.e.cfg["agent"]["life_lines"])
        self.assertEqual(self.a.life[0][1], "Something else the same day.")
        self.assertIn("day 9", self.a.life[-1][1])
        p = build_prompt(self.e, self.a)
        self.assertIn("What you will never forget", p)
        self.assertIn("of year 1]", p)

    def test_repeats_are_not_kept_twice(self):
        self.decide(remember="I swore to protect Tam.")
        self.w.tick += self.w.tpd()
        self.decide(remember="I swore to protect Tam.")
        self.assertEqual(len(self.a.life), 1)

    def test_schema_offers_both(self):
        props = response_schema(list(VERB_HELP))["properties"]
        self.assertIn("remember", props)
        self.assertIn("self", props)


if __name__ == "__main__":
    unittest.main()
