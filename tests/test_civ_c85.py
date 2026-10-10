"""c85: land held by realms, trespass, leave and tolls."""
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.prompt import build_prompt
from civ.world import Building, Group


class C85(unittest.TestCase):
    def setUp(self):
        self.w = w = generate({"seed": 6, "people": 16, "width": 60, "height": 60, "bands": 1, "ai": 0})
        self.e = Engine(w)
        ad = [p for p in w.living() if p.adult(w.tick)]
        self.head, self.men, self.stranger = ad[0], ad[1:4], ad[5]
        g = Group(id=w.new_id(), name="Hall", founder=self.head.id, leader=self.head.id, members=[self.head.id] + [m.id for m in self.men])
        w.groups[g.id] = g
        self.g = g
        for q in [self.head] + self.men:
            q.groups = [g.id]
        self.stranger.groups = []
        self.home = Building(id=w.new_id(), kind="shelter", x=20, y=20, owner=self.head.id, done=True)
        w.buildings[self.home.id] = self.home
        w.at["20,20"] = self.home.id
        self.head.home = self.home.id
        self.e.reckon_land()

    def test_the_land_about_a_home_is_the_realms(self):
        self.assertIs(self.e.holder_at(22, 21), self.g)
        self.assertIsNone(self.e.holder_at(40, 40))
        self.assertTrue(self.e.may_use_land(self.men[0], self.g))
        self.assertFalse(self.e.may_use_land(self.stranger, self.g))

    def test_trespass_is_remembered_when_seen_and_leave_ends_it(self):
        self.w.place(self.men[0], 21, 20)
        self.w.place(self.stranger, 22, 20)
        self.e.trespass(self.stranger, 22, 20, "felling")
        self.assertTrue(any(x[2] == "trespass" for x in self.men[0].ledger))
        self.assertIn("here without leave is trespass", build_prompt(self.e, self.stranger))
        ok, why = self.e.start(self.head, {"do": "grant", "to": self.stranger.name})
        self.assertTrue(ok, why)
        self.assertTrue(self.e.may_use_land(self.stranger, self.g))
        self.assertNotIn("here without leave is trespass", build_prompt(self.e, self.stranger))

    def test_unseen_trespass_is_not_known(self):
        for m in [self.head] + self.men:
            self.w.place(m, 50, 50)
        self.w.place(self.stranger, 22, 20)
        self.e.trespass(self.stranger, 22, 20, "felling")
        self.assertFalse(any(x[2] == "trespass" for m in self.men for x in m.ledger))

    def test_a_toll_at_a_ford_is_paid_on_crossing(self):
        row = self.w.terrain[21]
        self.w.terrain[21] = row[:22] + "s" + row[23:]
        self.e.reckon_land()
        self.w.place(self.head, 20, 21)
        ok, why = self.e.start(self.head, {"do": "toll", "x": 22, "y": 21, "get": [{"item": "grain", "qty": 1}]})
        self.assertTrue(ok, why)
        self.stranger.inv = {"grain": 3}
        held = lambda: self.head.inv.get("grain", 0) + sum(b.inv.get("grain", 0) for b in self.w.owned(self.head.id))
        had = held()
        self.e.crossing(self.stranger, 22, 21)
        self.assertEqual(self.stranger.inv["grain"], 2)
        self.assertEqual(held(), had + 1)                       # into the head's store (or hands)
        self.e.crossing(self.stranger, 22, 21)          # once a day
        self.assertEqual(self.stranger.inv["grain"], 2)
        self.assertIn("Tolls: (22,21)", build_prompt(self.e, self.head))

    def test_a_toll_only_at_a_crossing_on_ones_land(self):
        ok, why = self.e.start(self.head, {"do": "toll", "x": 22, "y": 21, "get": {"grain": 1}})
        self.assertFalse(ok)
        self.assertIn("ford", why)


if __name__ == "__main__":
    unittest.main()
