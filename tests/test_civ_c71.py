"""c71 (grand world, Phase 4): fealty and tribute. A group's leader may swear the group to another (fealty) or ask
another to swear to theirs (homage); the sworn pay tribute each season, from treasury, store or hand, and a
shortfall is a broken promise both know of; a lord may order the people of the groups sworn to them; word of a
blow against the sworn reaches the lord; a leader may renounce, and the lord remembers. A land of peoples begins
with each people's settlements sworn to its greatest."""
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.prompt import build_prompt
from civ.realm import generate as found_realm
from civ.world import Building, Group


class C71(unittest.TestCase):
    def setUp(self):
        self.w = w = generate({"seed": 6, "people": 16, "width": 40, "height": 40, "bands": 1, "ai": 0})
        self.e = Engine(w)
        ad = [p for p in w.living() if p.adult(w.tick)]
        self.lord, self.chief, self.man = ad[0], ad[1], ad[2]
        self.big = Group(id=w.new_id(), name="Hall", founder=self.lord.id, leader=self.lord.id, members=[self.lord.id])
        self.small = Group(id=w.new_id(), name="Croft", founder=self.chief.id, leader=self.chief.id, members=[self.chief.id, self.man.id])
        for g, ms in ((self.big, [self.lord]), (self.small, [self.chief, self.man])):
            w.groups[g.id] = g
            for m in ms:
                m.groups.append(g.id)
        for q in (self.lord, self.chief, self.man):
            w.place(q, self.lord.x, self.lord.y)
            q.act, q.intent = None, {"goal": "", "plan": []}
        self.hall = Building(id=w.new_id(), kind="store", x=self.lord.x, y=self.lord.y, owner=self.lord.id, done=True)
        self.croft = Building(id=w.new_id(), kind="store", x=self.chief.x, y=self.chief.y, owner=self.chief.id, done=True)
        for b in (self.hall, self.croft):
            w.buildings[b.id] = b

    def swear(self):
        ok, why = self.e.start(self.chief, {"do": "propose", "to": self.lord.name, "kind": "fealty", "give": {"grain": 3}})
        self.assertTrue(ok, why)
        x = next(x for x in self.w.offers.values() if x["kind"] == "fealty")
        self.e.close_offer(self.lord, x)

    def test_fealty_sworn_and_tribute_paid_each_season_or_missed(self):
        self.swear()
        self.assertEqual(self.small.parent, self.big.id)
        self.croft.inv = {"grain": 4}
        self.e.tribute_season()
        self.assertEqual(self.hall.inv.get("grain"), 3)
        self.e.tribute_season()                 # 1 left: short
        self.assertTrue(any(e[2] == "tribute_unpaid" for e in self.lord.ledger))

    def test_homage_asked_and_the_lord_may_order_the_sworn(self):
        ok, why = self.e.start(self.lord, {"do": "propose", "to": self.chief.name, "kind": "homage", "get": {"grain": 2}})
        self.assertTrue(ok, why)
        x = next(x for x in self.w.offers.values() if x["kind"] == "homage")
        self.e.close_offer(self.chief, x)
        self.assertEqual(self.small.parent, self.big.id)
        self.assertIn(self.man.id, self.e.followers(self.lord))
        self.lord.mind = "llm"
        text = build_prompt(self.e, self.lord)
        self.assertIn("Sworn to you: Croft", text)
        self.chief.mind = "llm"
        self.assertIn("Sworn to Hall", build_prompt(self.e, self.chief))

    def test_no_circles_and_renouncing_is_remembered(self):
        self.swear()
        ok, why = self.e.start(self.lord, {"do": "propose", "to": self.chief.name, "kind": "fealty", "give": {"grain": 1}})
        self.assertFalse(ok)
        ok, why = self.e.start(self.chief, {"do": "renounce", "group": "Croft"})
        self.assertTrue(ok, why)
        self.assertIsNone(self.small.parent)
        self.assertTrue(any(e[2] == "renounced" for e in self.lord.ledger))

    def test_a_lord_hears_of_a_blow_against_the_sworn(self):
        self.swear()
        stranger = next(p for p in self.w.living() if p.adult(self.w.tick) and p.id not in (self.lord.id, self.chief.id, self.man.id))
        self.w.place(stranger, self.man.x, self.man.y)
        self.lord.events = []
        self.e.start(stranger, {"do": "attack", "to": self.man.name})
        self.e.do_attack(stranger, stranger.act)
        self.assertTrue(any("sworn to you" in t for _, t in self.lord.events))

    def test_a_land_of_peoples_begins_as_chiefdoms(self):
        w = found_realm({"seed": 2, "width": 96, "height": 96, "people": 300})
        heads = [g for g in w.groups.values() if g.parent is None]
        sworn = [g for g in w.groups.values() if g.parent is not None]
        self.assertTrue(heads and sworn)
        self.assertTrue(all(g.title for g in w.groups.values()))


if __name__ == "__main__":
    unittest.main()
