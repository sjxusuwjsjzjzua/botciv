"""c84: envoys: an offer carried far by one of one's people, made in one's name on arrival, the answer brought back."""
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.prompt import build_prompt
from civ.world import Group


class C84(unittest.TestCase):
    def setUp(self):
        self.w = w = generate({"seed": 6, "people": 16, "width": 60, "height": 60, "bands": 1, "ai": 0})
        self.e = Engine(w)
        ad = [p for p in w.living() if p.adult(w.tick)]
        self.lord, self.env, self.far, self.fman = ad[0], ad[1], ad[2], ad[3]
        for lead, man, name in ((self.lord, self.env, "Hall"), (self.far, self.fman, "Hill")):
            g = Group(id=w.new_id(), name=name, founder=lead.id, leader=lead.id, members=[lead.id, man.id])
            w.groups[g.id] = g
            for q in (lead, man):
                q.groups = [g.id]
                q.act, q.intent, q.satiety, q.inv = None, {"goal": "", "plan": []}, 16, {}
        w.place(self.lord, 5, 5)
        w.place(self.env, 6, 5)
        w.place(self.far, 40, 40)
        w.place(self.fman, 41, 40)
        self.lord.inv = {"grain": 4}

    def send(self, **kw):
        a = dict({"do": "send", "to": self.far.name, "who": self.env.name, "kind": "peace", "give": {"grain": 2},
                  "text": "No more raiding."}, **kw)
        return self.e.start(self.lord, a)

    def test_too_far_to_propose_says_send(self):
        ok, why = self.e.start(self.lord, {"do": "propose", "to": self.far.name, "kind": "peace"})
        self.assertFalse(ok)
        self.assertIn("send", why)

    def test_the_envoy_carries_the_gift_and_the_offer_and_brings_back_the_answer(self):
        ok, why = self.send()
        self.assertTrue(ok, why)
        self.assertEqual((self.lord.inv.get("grain"), self.env.inv.get("grain")), (2, 2))
        self.assertEqual(self.env.intent["plan"][0], {"do": "go", "to": self.far.name})
        self.assertIn(f"Your envoy {self.env.name} is gone to {self.far.name}", build_prompt(self.e, self.lord))
        self.w.place(self.env, 39, 40)              # arrived
        self.e.envoys_hour()
        x = next(x for x in self.w.offers.values() if x["to"] == self.far.id)
        self.assertEqual((x["from"], x["envoy"], x["kind"]), (self.lord.id, self.env.id, "peace"))
        ok, why = self.e.start(self.far, {"do": "accept", "offer": x["id"]})
        self.assertTrue(ok, why)
        self.assertEqual(self.far.inv.get("grain"), 2)  # the gift, from the envoy's hands
        g1, g2 = self.w.groups[self.lord.groups[0]], self.w.groups[self.far.groups[0]]
        self.assertIn(str(g2.id), g1.peace)
        v = self.w.envoys[-1]
        self.assertEqual(v["state"], "back")
        self.assertFalse(any("accepted" in t for _, t in self.lord.events[-3:]))   # not known at home yet
        self.w.place(self.env, 6, 5)
        self.e.envoys_hour()
        self.assertEqual(v["state"], "done")
        self.assertTrue(any("is back from" in t and "accepted" in t for _, t in self.lord.events[-3:]))

    def test_refused_and_lost(self):
        self.send(give=None)
        self.w.place(self.env, 39, 40)
        self.e.envoys_hour()
        x = next(x for x in self.w.offers.values() if x["to"] == self.far.id)
        self.e.start(self.far, {"do": "refuse", "offer": x["id"]})
        self.assertEqual(self.w.envoys[-1]["answer"], f"{self.far.name} refused")
        self.env.alive = False
        self.e.envoys_hour()
        self.assertEqual(self.w.envoys[-1]["state"], "lost")

    def test_only_ones_own_people_beside_one(self):
        ok, why = self.e.start(self.lord, {"do": "send", "to": self.far.name, "who": self.fman.name, "kind": "peace"})
        self.assertFalse(ok)
        self.w.place(self.env, 20, 20)
        ok, why = self.send()
        self.assertFalse(ok)
        self.assertIn("beside you", why)


if __name__ == "__main__":
    unittest.main()
