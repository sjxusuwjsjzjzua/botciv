"""Rules w31: service. By a deal one person works for another for some days: they count as each
other's people when force is used, the servant may put into the master's stores, the master hears
each day what the servant did, and leaving or sending away early is remembered."""
import json
import re
import unittest

from botciv.engine import Engine, Structure
from botciv.log import NullLog
from botciv.prompt import build_prompt
from botciv.standing import standing
from botciv.world import World
from tests.test_engine import world, place, open_tile


def hire(e, master, servant, days=3, **extra):
    """master offers, servant accepts: servant works for master."""
    ok, msg = e.start(master, {"verb": "propose", "target": servant.name, "hire_days": days, **extra})
    assert ok, msg
    pid = max(e.w.proposals)
    ok, msg = e.start(servant, {"verb": "accept", "id": pid})
    assert ok, msg
    return e.serving(servant)


class W31(unittest.TestCase):
    def setUp(self):
        self.w = world(1)
        self.e = Engine(self.w, NullLog())
        self.m, self.s, self.x = self.w.living()[:3]
        x, y = open_tile(self.w)
        place(self.w, self.m, x, y)
        place(self.w, self.s, x + 1, y)
        place(self.w, self.x, x + 2, y)

    def test_a_deal_puts_one_into_the_others_service(self):
        svc = hire(self.e, self.m, self.s, 2, text="Guard me.")
        self.assertEqual((svc["master"], svc["servant"], svc["days"]), (self.m.id, self.s.id, 2))
        self.assertTrue(self.e.bound(self.s, self.m) and self.e.bound(self.m, self.s))
        self.assertEqual(standing(self.w, self.m)[1], 1)
        p = build_prompt(self.e, self.s)
        self.assertIn(f"You are in {self.m.name}'s service for 2 more days", p)
        self.assertIn(f"In your service: {self.s.name}", build_prompt(self.e, self.m))

    def test_serve_days_offers_oneself(self):
        ok, _ = self.e.start(self.s, {"verb": "propose", "target": self.m.name, "serve_days": 4})
        self.assertTrue(ok)
        pid = max(self.w.proposals)
        self.assertIn("works for you for 4 days", self.e.deal_text(self.w.proposals[pid], self.m))
        self.e.start(self.m, {"verb": "accept", "id": pid})
        self.assertEqual(self.e.serving(self.s)["master"], self.m.id)

    def test_one_service_at_a_time(self):
        hire(self.e, self.m, self.s)
        self.e.start(self.x, {"verb": "propose", "target": self.s.name, "hire_days": 2})
        pid = max(self.w.proposals)
        ok, msg = self.e.start(self.s, {"verb": "accept", "id": pid})
        self.assertFalse(ok)
        self.assertIn("already in", msg)

    def test_servant_puts_into_masters_closed_store(self):
        st = Structure(id=self.w.new_id(), kind="store", x=self.s.x, y=self.s.y + 1, owner=self.m.id, done=True, access="owner")
        self.w.structures[st.id] = st
        self.s.inventory = {"berries": 6}
        ok, msg = self.e.start(self.s, {"verb": "put", "item": "berries", "qty": 6})
        self.assertFalse(ok)                 # not yet in service: closed to them
        hire(self.e, self.m, self.s)
        self.s.activity = None
        ok, msg = self.e.start(self.s, {"verb": "put", "item": "berries", "qty": 6})
        self.assertTrue(ok, msg)
        self.e.do_put(self.s, self.s.activity)
        self.assertEqual(st.inventory.get("berries"), 6)
        ok, msg = self.e.start(self.s, {"verb": "take", "target": "store", "item": "berries"})
        self.assertFalse(ok)                 # putting in, not taking out

    def test_the_master_hears_what_the_servant_did(self):
        svc = hire(self.e, self.m, self.s, 3)
        self.m.events = []
        self.s.activity = {"verb": "gather", "item": "berries", "n": 0}
        for _ in range(self.w.tpd()):
            self.e.service_tick()
            self.w.tick += 1
        text = " ".join(t for _, t in self.m.events)
        self.assertIn(f"{self.s.name}'s last 12 hours in your service: gathering berries 12 hours", text)
        self.assertIn("beside you 12 hours", text)
        self.assertEqual(svc["hours"], 0)

    def test_service_ends_when_its_days_are_done(self):
        svc = hire(self.e, self.m, self.s, 1)
        for _ in range(self.w.tpd() + 1):
            self.e.service_tick()
            self.w.tick += 1
        self.assertTrue(svc["done"])
        self.assertEqual(svc["how"], "served")
        self.assertTrue(any(k == "served_me" for _, _, k, _ in self.m.ledger))
        self.assertIsNone(self.e.serving(self.s))

    def test_leaving_early_is_remembered(self):
        hire(self.e, self.m, self.s, 5)
        ok, _ = self.e.start(self.s, {"verb": "leave"})
        self.assertTrue(ok)
        self.assertIsNone(self.e.serving(self.s))
        self.assertTrue(any(k == "left_service" for _, oid, k, _ in self.m.ledger if oid == self.s.id))
        wrongs, _ = self.e.tellable(self.m, self.s)
        self.assertTrue(any("left" in x for x in wrongs))

    def test_sending_away(self):
        hire(self.e, self.m, self.s, 5)
        ok, _ = self.e.start(self.m, {"verb": "expel", "target": self.s.name})
        self.assertTrue(ok)
        self.assertIsNone(self.e.serving(self.s))
        self.assertTrue(any(k == "dismissed" for _, _, k, _ in self.s.ledger))

    def test_a_guard_at_the_masters_side_stands_with_the_master(self):
        """Following one's master used to count as coming after them; a servant beside their
        master is the master's people, so a lone thief cannot take by force."""
        hire(self.e, self.m, self.s)
        self.s.activity = {"verb": "follow", "follow": self.m.id, "n": 0}
        self.assertEqual(self.e.backers(self.x, self.m), [])
        place(self.w, self.x, self.m.x, self.m.y - 1)
        self.assertEqual([o.id for o in self.e.backers(self.m, self.x)], [self.s.id])

    def test_master_and_servant_take_together(self):
        hire(self.e, self.m, self.s)
        v = self.x
        place(self.w, v, self.m.x + 1, self.m.y + 1)          # beside both
        self.assertEqual([o.id for o in self.e.backers(self.m, v)], [self.s.id])

    def test_old_saves_load(self):
        d = self.w.to_dict()
        del d["services"]
        w2 = World.from_dict(json.loads(json.dumps(d)))
        self.assertEqual(w2.services, [])

    def test_words(self):
        hire(self.e, self.m, self.s)
        banned = re.compile(r"\b(simulat\w*|agents?|ticks?|game|players?|AI|language model|LLM|turns?)\b", re.I)
        for a in (self.m, self.s, self.x):
            self.assertIsNone(banned.search(build_prompt(self.e, a)))


if __name__ == "__main__":
    unittest.main()
