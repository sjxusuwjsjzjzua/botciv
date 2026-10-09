"""c78 (grand world, Phase 7): a ruler's view. One who leads a group sees their realm (their people, the groups
sworn to them, who can fight, how long the stores would feed them) and the neighbouring peoples' chiefs (where,
how many, how they stand toward one, a peace sworn); their own people, told above, are only numbered on the map.
A ruler's prompt keeps within its station's budget."""
import unittest

from civ.engine import Engine
from civ.prompt import build_prompt
from civ.realm import generate as found_realm

RULER_BUDGET = 12000


class C78(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = found_realm({"seed": 2, "width": 96, "height": 96, "people": 300, "ai": 20})
        cls.e = Engine(cls.w)

    def test_a_ruler_sees_their_realm_and_their_neighbours(self):
        w, e = self.w, self.e
        heads = [w.people[g.leader] for g in w.groups.values() if g.parent is None and g.dissolved is None and g.leader in w.people]
        seen = 0
        for p in heads:
            text = build_prompt(e, p)
            if "Peoples and chiefs around you:" in text:
                seen += 1
                self.assertIn("Your realm:", text)
        self.assertGreater(seen, 0)

    def test_peace_is_shown_with_the_neighbour(self):
        w, e = self.w, self.e
        heads = [(w.people[g.leader], g) for g in w.groups.values() if g.parent is None and g.dissolved is None and g.leader in w.people]
        (a, ga) = heads[0]
        (b, gb) = min(heads[1:], key=lambda t: abs(t[0].x - a.x) + abs(t[0].y - a.y))
        ga.peace[str(gb.id)] = gb.peace[str(ga.id)] = w.tick + 400
        self.assertIn("at peace with you until day", build_prompt(e, a))

    def test_rulers_keep_within_their_budget(self):
        w, e = self.w, self.e
        sizes = sorted(len(build_prompt(e, p)) for p in w.living() if p.mind == "llm")
        self.assertLessEqual(sizes[-1], RULER_BUDGET)


if __name__ == "__main__":
    unittest.main()
