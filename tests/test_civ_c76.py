"""c76 (grand world, Phase 5): captives and ransom (docs/grand.md §13: hostages and ransom only). A band that wins
may carry off the weakest of those who stood against it; one held follows their captor and may only eat, rest,
talk, deal, buy their freedom, or try to escape; their kin and their leader are told the price and may pay it face
to face; a bot captor lets them go after a season and a half; a captive whose captor is gone is free."""
import unittest

from civ.minds.bot import BotMind
from civ.prompt import build_prompt
from civ.world import World, TPD
from tests import test_civ_c75 as base




class Captives(unittest.TestCase):
    def setUp(self):
        self.t = base.C75("test_peace_is_sworn_shown_and_kept")
        self.t.setUp()
        self.w, self.e = self.t.w, self.t.e

    def take(self):
        t = self.t
        ok, why = self.e.start(t.lead, {"do": "muster", "hours": 1})
        band = self.e.band_of(t.lead)
        t.lead.act = None
        ok, why = self.e.start(t.lead, {"do": "raid", "x": t.there[0], "y": t.there[1], "take": True})
        self.assertTrue(ok, why)
        for _ in range(80):
            self.e.tick(lambda people: {})
            if band["state"] == "returning" or band["id"] not in self.w.bands:
                break
        return [q for q in t.folk if q.held]

    def test_a_winning_band_carries_off_a_captive(self):
        w, e, t = self.w, self.e, self.t
        held = self.take()
        self.assertTrue(1 <= len(held) <= 2)          # a band of seven carries off at most two
        q = held[0]
        self.assertEqual(q.held["by"], t.lead.id)
        ok, why = e.start(q, {"do": "gather", "item": "wood"})
        self.assertFalse(ok)
        self.assertIn("held by", why)
        e.tick(lambda people: {})
        self.assertIn(q.id, w.holding[t.lead.id])
        self.assertEqual(q.act["do"], "follow")
        q.mind = "llm"
        self.assertIn("You are held captive by", build_prompt(e, q))
        self.assertIn("- ransom: who", build_prompt(e, q))
        t.lead.mind = "llm"
        self.assertIn("You hold captive:", build_prompt(e, t.lead))
        self.assertTrue(World.from_dict(w.to_dict()).people[q.id].held)
        self.assertNotIn(q.id, e.followers(t.folk[0]))

    def test_ransom_paid_face_to_face_frees_them(self):
        w, e, t = self.w, self.e, self.t
        q = self.take()[0]
        payer = next(o for o in t.folk if o is not q)
        payer.held = None
        w.place(payer, t.lead.x + 1, t.lead.y)
        price = q.held["price"]
        payer.inv.update({k: n for k, n in price.items()})
        before = t.lead.inv.get("grain", 0)
        ok, why = e.start(payer, {"do": "ransom", "who": q.name})
        self.assertTrue(ok, why)
        self.assertIsNone(q.held)
        self.assertEqual(t.lead.inv.get("grain", 0), before + price["grain"])
        self.assertIn("ransomed", {x["kind"] for x in e.log.events})

    def test_bots_ransom_their_own_and_let_captives_go(self):
        w, e, t = self.w, self.e, self.t
        q = self.take()[0]
        e.held_hour()
        bot = BotMind(e)
        kin = next(o for o in t.folk if o is not q)
        kin.held = None
        kin.rel[str(q.id)] = {"trust": 0.8, "met": 0, "kin": "child"}
        kin.inv["grain"] = 40
        goal = bot.ransom_goal(kin)
        self.assertIsNotNone(goal)
        self.assertEqual(goal["plan"][-1], {"do": "ransom", "who": q.name})
        self.assertIsNone(bot.captor(t.lead))
        q.held["since"] -= 16 * TPD
        self.assertEqual(bot.captor(t.lead)["plan"][0]["do"], "release")

    def test_a_captive_whose_captor_is_gone_is_free(self):
        e, t = self.e, self.t
        q = self.take()[0]
        e.die(t.lead, "old age")
        e.held_hour()
        self.assertIsNone(q.held)


if __name__ == "__main__":
    unittest.main()
