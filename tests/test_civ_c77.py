"""c77 (grand world, Phase 5): the alarm goes round. When a band falls on a place, grown people a short run away who
share a group, a lord or kinship with those attacked come running (bots as bold and loyal as they are; people with
minds of their own are told and choose); captives stand for no one."""
import unittest

from tests import test_civ_c75 as base


class Rally(unittest.TestCase):
    def setUp(self):
        self.t = base.C75("test_peace_is_sworn_shown_and_kept")
        self.t.setUp()
        self.w, self.e = self.t.w, self.t.e

    def test_kin_and_group_come_running(self):
        w, e, t = self.w, self.e, self.t
        tx, ty = t.there
        spot = next((x, y) for x in range(tx - 7, tx + 8) for y in range(ty - 7, ty + 8)
                    if 5 <= max(abs(x - tx), abs(y - ty)) <= 7 and w.cost(x, y) == 1 and w.reachable(x, y, tx, ty, True))
        helpers = [q for q in w.living() if q.adult(w.tick) and q not in [t.lead] + t.men + t.folk + [t.lordhead]][:8]
        for q in helpers:
            w.place(q, *spot)
            q.groups.append(t.village.id)
            t.village.members.append(q.id)
            q.traits["boldness"] = 1.0
            q.act, q.intent, q.health = None, {"goal": "", "plan": []}, 10
        far = helpers[-1]
        far.groups.remove(t.village.id)
        t.village.members.remove(far.id)          # no bond to those attacked: does not come
        e.start(t.lead, {"do": "muster", "hours": 1})
        band = e.band_of(t.lead)
        band["target"], band["state"] = list(t.there), "fighting"
        e.alarm(band)
        running = [q for q in helpers if q.act and q.act.get("do") == "go"]
        self.assertGreaterEqual(len(running), 2)
        self.assertNotIn(far, running)
        self.assertIn("rally", {x["kind"] for x in e.log.events})

    def test_captives_stand_for_no_one(self):
        t = self.t
        q = t.folk[1]
        q.held = {"by": t.lead.id, "since": 0, "price": {"grain": 12}}
        self.assertNotIn(q, self.e.defenders_at(*t.there))


if __name__ == "__main__":
    unittest.main()
