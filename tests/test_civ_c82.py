"""c82: the division of spoils: the raid's leader says how the plunder is shared at home, and followers trust them
as they kept their share."""
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.prompt import STEP
from civ.war import share_of
from civ.world import Building


class C82(unittest.TestCase):
    def setUp(self):
        self.w = w = generate({"seed": 6, "people": 16, "width": 40, "height": 40, "bands": 1, "ai": 0})
        self.e = Engine(w)
        adults = [p for p in w.living() if p.adult(w.tick)]
        self.lead, self.men = adults[0], adults[1:3]
        for q in [self.lead] + self.men:
            w.place(q, self.lead.x, self.lead.y)
            q.inv = {}
        self.store = Building(id=w.new_id(), kind="store", x=self.lead.x, y=self.lead.y, owner=self.lead.id, done=True)
        w.buildings[self.store.id] = self.store

    def band(self, share):
        for m in self.men:
            m.inv = {"grain": 6}
            m.rel[str(self.lead.id)] = {"trust": 0.3, "met": 0}
        return {"id": 1, "leader": self.lead.id, "members": [m.id for m in self.men], "home": [self.lead.x, self.lead.y],
                "share": share, "spoils": {str(m.id): {"grain": 6} for m in self.men}}

    def test_each_keeps_their_own(self):
        self.e.divide(self.band("each"), self.lead)
        self.assertEqual([m.inv.get("grain") for m in self.men], [6, 6])
        self.assertFalse(self.store.inv.get("grain"))
        self.assertAlmostEqual(self.men[0].rel[str(self.lead.id)]["trust"], 0.36, places=2)

    def test_half_to_the_leaders_store(self):
        self.e.divide(self.band("half"), self.lead)
        self.assertEqual([m.inv.get("grain") for m in self.men], [3, 3])
        self.assertEqual(self.store.inv.get("grain"), 6)

    def test_all_taken_is_resented(self):
        self.e.divide(self.band("mine"), self.lead)
        self.assertEqual(self.store.inv.get("grain"), 12)
        self.assertLess(self.men[0].rel[str(self.lead.id)]["trust"], 0.3)
        self.assertTrue(any(e[2] == "took_spoils" for e in self.men[0].ledger))
        ev = [x for x in self.e.log.events if x["kind"] == "spoils"][-1]
        self.assertEqual(ev["share"], "mine")

    def test_what_was_eaten_or_lost_on_the_way_is_not_owed(self):
        b = self.band("mine")
        self.men[0].inv = {"grain": 2}
        self.e.divide(b, self.lead)
        self.assertEqual(self.store.inv.get("grain"), 8)

    def test_the_word_and_the_shape(self):
        self.assertEqual([share_of(v) for v in ("Mine", "all", "half", None, "even")], ["mine", "mine", "half", "each", "each"])
        self.assertIn("share", STEP["properties"])


if __name__ == "__main__":
    unittest.main()
