"""Rules w14: crops as property, handing over and bequeathing buildings, parting,
kin who remember a killer, leaders seen as leaders."""
import unittest

from botciv.engine import Engine
from botciv.log import NullLog
from botciv.prompt import build_prompt, describe_person
from botciv.world import Structure, Group
from tests.test_engine import world, open_tile, place


class W14(unittest.TestCase):
    def setUp(self):
        self.w = world(2)
        self.e = Engine(self.w, NullLog())
        self.a, self.b, self.c = self.w.living()[:3]
        for ag in self.w.living():
            ag.inventory = {}
            ag.x, ag.y = 0, 0
        x, y = open_tile(self.w)
        self.x, self.y = x, y
        place(self.w, self.a, x, y)
        place(self.w, self.b, x + 1, y)
        place(self.w, self.c, x + 2, y)
        self.w.tick = 1

    def building(self, kind, owner, x=None, y=None, **kw):
        s = Structure(id=self.w.new_id(), kind=kind, x=self.x if x is None else x, y=self.y if y is None else y,
                      owner=owner.id, done=True, **kw)
        self.w.structures[s.id] = s
        return s

    def test_taking_from_a_closed_farm_is_remembered(self):
        farm = self.building("farm", self.b, inventory={"grain": 12}, planted=0, seeds=2)
        self.e.apply_decision(self.a, {"action": {"verb": "gather", "item": "grain", "qty": 3}, "memory": "m"})
        for _ in range(3):
            self.e.step_activities()
        self.assertGreater(self.a.inventory.get("grain", 0), 0)
        self.assertTrue(any(k == "took_crop" and oid == self.a.id for _, oid, k, _ in self.b.ledger))

    def test_an_open_farm_is_not_taking(self):
        farm = self.building("farm", self.b, inventory={"grain": 12}, planted=0, seeds=2, access="anyone")
        self.e.apply_decision(self.a, {"action": {"verb": "gather", "item": "grain", "qty": 3}, "memory": "m"})
        self.e.step_activities()
        self.assertFalse(any(k == "took_crop" for _, _, k, _ in self.b.ledger))

    def test_a_building_can_be_handed_over(self):
        s = self.building("store", self.a)
        ok, msg = self.e.start(self.a, {"verb": "give", "target": self.b.name, "item": "store"})
        self.assertTrue(ok, msg)
        self.assertEqual(s.owner, self.b.id)

    def test_a_named_heir_inherits_before_the_partner(self):
        s = self.building("shelter", self.a)
        self.a.partner, self.b.partner = self.b.id, self.a.id
        ok, msg = self.e.start(self.a, {"verb": "bequeath", "target": self.c.name})
        self.assertTrue(ok, msg)
        self.e.kill(self.a, "starved")
        self.assertEqual(s.owner, self.c.id)

    def test_partners_can_part(self):
        self.a.partner, self.b.partner = self.b.id, self.a.id
        ok, msg = self.e.start(self.a, {"verb": "part"})
        self.assertTrue(ok, msg)
        self.assertIsNone(self.a.partner)
        self.assertIsNone(self.b.partner)

    def test_kin_remember_who_killed_their_kin(self):
        self.b.children.append(self.c.id)
        self.c.parents.append(self.b.id)
        self.e.kill(self.b, f"killed by {self.a.name}", by=self.a)
        self.assertTrue(any(k == "killed_kin" and oid == self.a.id for _, oid, k, _ in self.c.ledger))
        self.assertIn("killed your kin", describe_person(self.e, self.c, self.a))

    def test_a_leader_is_seen_as_one(self):
        g = Group(id=self.w.new_id(), name="House of Stone", founder=self.a.id, leader=self.a.id,
                  members=[self.a.id, self.b.id], rules="")
        self.w.groups[g.id] = g
        self.a.groups.append(g.id)
        self.assertIn("leads House of Stone", describe_person(self.e, self.c, self.a))


if __name__ == "__main__":
    unittest.main()
