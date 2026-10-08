"""c58: households' rules in their founder's own words, not one sentence for all; old worlds' groups that
were given the one sentence get their founder's words on load."""
import random
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.names import group_rules
from civ.world import Group

OLD = "We share what we gather and stand by each other."


class C58(unittest.TestCase):
    def test_rules_differ(self):
        r = random.Random(3)
        got = {group_rules(r, {k: r.random() for k in ("generosity", "industry", "ambition", "sociability",
                                                     "curiosity", "boldness")}, "Ana") for _ in range(30)}
        self.assertGreater(len(got), 20)

    def test_old_groups_get_their_founders_words(self):
        w = generate({"seed": 4, "people": 12, "width": 40, "height": 40, "bands": 2, "ai": 0})
        p = w.living()[0]
        g = Group(id=w.new_id(), name="Ana's people", founder=p.id, leader=p.id, members=[p.id], founded=0, rules=OLD)
        w.groups[g.id] = g
        Engine(w)
        self.assertNotEqual(g.rules, OLD)
        self.assertTrue(g.rules)


if __name__ == "__main__":
    unittest.main()
