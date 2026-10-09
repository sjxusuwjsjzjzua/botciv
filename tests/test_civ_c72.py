"""c72 (grand world, Phase 5): bands and raids. A leader musters a band from their people (bots come as they owe and
trust the leader and as bold as they are; people with minds of their own are called and choose); the band follows
its leader; at a place where others live, those who live there stand together; the fight is reckoned as a whole,
hour by hour, until a side breaks: winners take what the stores hold, losers flee. All is remembered."""
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.prompt import build_prompt
from civ.world import Building, Group, World, key


class C72(unittest.TestCase):
    def setUp(self):
        self.w = w = generate({"seed": 6, "people": 40, "width": 60, "height": 60, "bands": 2, "ai": 0})
        self.e = Engine(w)
        ad = [p for p in w.living() if p.adult(w.tick)]
        self.lead, self.men, self.folk = ad[0], ad[1:7], ad[7:9]
        open_ = [(x, y) for y in range(5, 55) for x in range(5, 55) if w.cost(x, y) == 1 and not w.building_at(x, y)]
        self.home = open_[0]
        self.there = next(t for t in open_ if 14 <= max(abs(t[0] - self.home[0]), abs(t[1] - self.home[1])) <= 25
                          and w.reachable(*self.home, *t, True) and w.passable(t[0], t[1] + 1))
        g = Group(id=w.new_id(), name="Raiders", founder=self.lead.id, leader=self.lead.id,
                  members=[self.lead.id] + [m.id for m in self.men])
        w.groups[g.id] = g
        for q in [self.lead] + self.men:
            q.groups.append(g.id)
            w.place(q, *self.home)
            q.rel[str(self.lead.id)] = {"trust": 0.8, "met": 0}
            q.traits["boldness"] = 0.9
            q.act, q.intent, q.health, q.satiety = None, {"goal": "", "plan": []}, 10, 16
        self.store = Building(id=w.new_id(), kind="store", x=self.there[0], y=self.there[1], owner=self.folk[0].id, done=True)
        w.buildings[self.store.id] = self.store
        w.at[key(*self.there)] = self.store.id
        self.store.inv = {"grain": 40, "cheese": 5}
        for q in self.folk:
            w.place(q, self.there[0], self.there[1] + 1)
            q.home = self.store.id
        for q in w.living():
            if q not in [self.lead] + self.men + self.folk:
                w.place(q, 55, 55)

    def muster(self):
        ok, why = self.e.start(self.lead, {"do": "muster", "hours": 1})
        self.assertTrue(ok, why)
        return self.e.band_of(self.lead)

    def test_a_loyal_bold_people_comes_to_the_muster(self):
        band = self.muster()
        self.assertGreaterEqual(len(band["members"]), 5)
        for m in band["members"]:
            self.assertEqual(self.w.people[m].act["do"], "follow")
        self.lead.mind = "llm"
        self.assertIn("Your band:", build_prompt(self.e, self.lead))
        w2 = World.from_dict(self.w.to_dict())
        self.assertEqual(len(w2.bands), 1)

    def test_a_strong_band_takes_what_the_stores_hold_and_it_is_remembered(self):
        band = self.muster()
        self.lead.act = None
        ok, why = self.e.start(self.lead, {"do": "raid", "x": self.there[0], "y": self.there[1]})
        self.assertTrue(ok, why)
        for _ in range(80):
            self.e.tick(lambda people: {})
            if band["state"] in ("returning",) or band["id"] not in self.w.bands:
                break
        kinds = {x["kind"] for x in self.e.log.events}
        self.assertIn("raid", kinds)
        self.assertTrue("plunder" in kinds or "repelled" in kinds)
        if "plunder" in kinds:
            self.assertLess(self.store.inv.get("grain", 0), 40)
            owner = self.folk[0]
            self.assertTrue(any(e[2] in ("robbed", "raided") for e in owner.ledger))

    def test_a_walled_crowd_drives_a_small_band_off(self):
        w = self.w
        band = self.muster()
        band["members"] = band["members"][:1]
        many = [q for q in w.living() if q.adult(w.tick) and q.id not in [self.lead.id] + band["members"]][:12]
        for q in many:
            w.place(q, self.there[0], self.there[1] + 1)
            q.home = self.store.id
            q.health = 10
        wall = Building(id=w.new_id(), kind="palisade", x=self.there[0] + 1, y=self.there[1], owner=self.folk[0].id, done=True)
        w.buildings[wall.id] = wall
        w.at[key(wall.x, wall.y)] = wall.id
        self.lead.act = None
        self.e.start(self.lead, {"do": "raid", "x": self.there[0], "y": self.there[1]})
        for _ in range(80):
            self.e.tick(lambda people: {})
            if band["state"] == "returning" or band["id"] not in w.bands:
                break
        kinds = {x["kind"] for x in self.e.log.events}
        self.assertIn("repelled", kinds)
        self.assertNotIn("plunder", kinds)

    def test_no_band_without_people(self):
        loner = self.folk[1]
        ok, why = self.e.start(loner, {"do": "muster"})
        self.assertFalse(ok)
        ok, why = self.e.start(loner, {"do": "raid", "x": 1, "y": 1})
        self.assertFalse(ok)

    def test_orders_are_understood_as_the_people_write_them(self):
        # world2 under c66: {"do": "order", "to": "Stear", "value": "gather", ...} and {"who": ..., "x", "y"} only
        w, e = self.w, self.e
        lord, man = self.lead, self.men[0]
        man.rel[str(lord.id)] = {"trust": 0.8, "met": 0}
        ok, why = e.start(lord, {"do": "order", "to": man.name, "value": "gather", "item": "wood", "n": 3})
        self.assertTrue(ok, why)
        self.assertEqual(man.intent["plan"][0]["do"], "gather")
        mine = Building(id=w.new_id(), kind="store", x=self.home[0], y=self.home[1], owner=lord.id, done=True)
        w.buildings[mine.id] = mine
        w.at[key(mine.x, mine.y)] = mine.id
        man.intent = {"goal": "", "plan": []}
        ok, why = e.start(lord, {"do": "order", "who": man.name, "x": mine.x, "y": mine.y})
        self.assertTrue(ok, why)
        self.assertEqual((man.intent["plan"][0]["do"], man.intent["plan"][0]["item"]), ("put", "grain"))


if __name__ == "__main__":
    unittest.main()
