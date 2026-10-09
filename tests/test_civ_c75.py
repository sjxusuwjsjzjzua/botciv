"""c75 (grand world, Phase 5): after the fighting. Two leaders may swear peace between their peoples; a raid on those
one is at peace with breaks it and is remembered. Those who followed a leader to spoils trust them more, to a beating
less, and the kin of the fallen blame the one who led them out. A lord whose sworn are raided while none of the
lord's people stand with them is trusted less. Bots raided seek peace with the raiders' head, bend to a strong
raider, and leave a lord who failed them."""
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.minds.bot import BotMind
from civ.prompt import build_prompt
from civ.world import Building, Group, World, key


class C75(unittest.TestCase):
    def setUp(self):
        self.w = w = generate({"seed": 6, "people": 40, "width": 60, "height": 60, "bands": 2, "ai": 0})
        self.e = Engine(w)
        for g in list(w.groups.values()):
            for m in g.members:
                if m in w.people:
                    w.people[m].groups = []
        w.groups = {}
        ad = [p for p in w.living() if p.adult(w.tick)]
        self.lead, self.men, self.folk, self.lordhead = ad[0], ad[1:7], ad[7:9], ad[9]
        open_ = [(x, y) for y in range(5, 55) for x in range(5, 55) if w.cost(x, y) == 1 and not w.building_at(x, y)]
        self.home = open_[0]
        self.there = next(t for t in open_ if 14 <= max(abs(t[0] - self.home[0]), abs(t[1] - self.home[1])) <= 25
                          and w.reachable(*self.home, *t, True) and w.passable(t[0], t[1] + 1))
        self.raiders = self.group("Raiders", self.lead, self.men)
        self.village = self.group("Greenford", self.folk[0], self.folk[1:])
        for q in [self.lead] + self.men:
            w.place(q, *self.home)
            q.rel[str(self.lead.id)] = {"trust": 0.5, "met": 0}
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

    def group(self, name, head, rest):
        w = self.w
        g = Group(id=w.new_id(), name=name, founder=head.id, leader=head.id, members=[head.id] + [m.id for m in rest])
        w.groups[g.id] = g
        for q in [head] + list(rest):
            q.groups.append(g.id)
        return g

    def raid(self, cut=None):
        e, w = self.e, self.w
        ok, why = e.start(self.lead, {"do": "muster", "hours": 1})
        self.assertTrue(ok, why)
        band = e.band_of(self.lead)
        if cut is not None:
            band["members"] = band["members"][:cut]
        self.lead.act = None
        ok, why = e.start(self.lead, {"do": "raid", "x": self.there[0], "y": self.there[1]})
        self.assertTrue(ok, why)
        for _ in range(80):
            e.tick(lambda people: {})
            if band["state"] == "returning" or band["id"] not in w.bands:
                break
        return band, {x["kind"] for x in e.log.events}

    def test_peace_is_sworn_shown_and_kept(self):
        w, e, a, b = self.w, self.e, self.lead, self.folk[0]
        w.place(b, a.x + 1, a.y)
        ok, why = e.start(a, {"do": "propose", "to": b.name, "kind": "peace", "days": 30})
        self.assertTrue(ok, why)
        offer = max(w.offers.values(), key=lambda x: x["tick"])
        self.assertIn("keep the peace for 30 days", e.offer_text(offer, b))
        self.assertIs(e.close_offer(b, offer), True)
        self.assertGreater(self.raiders.peace[str(self.village.id)], w.tick)
        self.assertTrue(e.peace_between(self.men[0], self.folk[1]))
        b.mind = "llm"
        self.assertIn("At peace with Raiders", build_prompt(e, b))
        self.assertIn(str(self.raiders.id), World.from_dict(w.to_dict()).groups[self.village.id].peace)
        # a bot raider leaves those it is at peace with alone, as it does its own lord's people
        self.assertTrue(e.same_realm(self.men[0], self.lead))
        self.assertFalse(e.same_realm(self.lead, b))

    def test_a_raid_on_those_at_peace_breaks_it(self):
        w, e = self.w, self.e
        self.raiders.peace[str(self.village.id)] = self.village.peace[str(self.raiders.id)] = w.tick + 1000
        band, kinds = self.raid()
        self.assertIn("broke_peace", kinds)
        self.assertNotIn(str(self.village.id), self.raiders.peace)
        self.assertTrue(any(x[2] == "broke_peace" for x in self.folk[0].ledger))

    def test_spoils_bind_followers_and_a_beating_loosens_them(self):
        w = self.w
        before = {m.id: m.rel[str(self.lead.id)]["trust"] for m in self.men}
        band, kinds = self.raid()
        self.assertIn("plunder", kinds)
        came = [w.people[m] for m in band["members"] if w.people[m].alive]
        self.assertTrue(came)
        self.assertTrue(all(q.rel[str(self.lead.id)]["trust"] > before[q.id] for q in came))

    def test_a_beating_loosens_them(self):
        w = self.w
        before = {m.id: m.rel[str(self.lead.id)]["trust"] for m in self.men}
        band, kinds = self.raid(cut=1)
        self.assertIn("repelled", kinds)
        q = w.people[band["members"][0]]
        self.assertLess(q.rel[str(self.lead.id)]["trust"], before[q.id])

    def test_a_lord_who_does_not_stand_by_the_sworn_is_trusted_less(self):
        w = self.w
        lords = self.group("Hillhold", self.lordhead, [])
        self.village.parent = lords.id
        self.folk[0].rel[str(self.lordhead.id)] = {"trust": 0.2, "met": 0}
        band, kinds = self.raid()
        self.assertIn("plunder", kinds)
        self.assertLess(self.folk[0].rel[str(self.lordhead.id)]["trust"], 0.2)
        self.assertTrue(any(x[2] == "unprotected" for x in self.folk[0].ledger))

    def test_the_raided_seek_peace_with_the_raiders_head(self):
        w, e = self.w, self.e
        b = self.folk[0]
        w.place(self.lead, b.x + 5, b.y)
        b.ledger.append([w.tick, self.men[0].id, "raided", "came raiding"])
        bot = BotMind(e)
        goal = None
        for _ in range(60):
            goal = bot.peace_goal(b, self.village)
            if goal:
                break
        self.assertIsNotNone(goal)
        self.assertEqual(goal["plan"][-1]["kind"], "peace")
        self.assertEqual(goal["plan"][-1]["to"], self.lead.name)
        # and a strong raider asking homage of them is readily given it
        self.assertTrue(bot.raided_by(b, self.lead))


if __name__ == "__main__":
    unittest.main()
