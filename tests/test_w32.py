"""Rules w32: standing trades. A store's owner posts what it gives for what is put in; anyone
may trade there, even when it is closed to them and the owner is away, while it holds enough."""
import json
import unittest

from botciv import items as I

from botciv.engine import Engine, Structure
from botciv.log import NullLog
from botciv.prompt import build_prompt, available_verbs
from botciv.world import World, key
from tests.test_engine import world, place, open_tile


class W32(unittest.TestCase):
    def setUp(self):
        self.w = world(1)
        self.e = Engine(self.w, NullLog())
        self.o, self.b = self.w.living()[:2]
        x, y = open_tile(self.w)
        place(self.w, self.o, x, y)
        place(self.w, self.b, x + 2, y)
        self.st = Structure(id=self.w.new_id(), kind="store", x=x + 1, y=y, owner=self.o.id, done=True, access="owner",
                            inventory={"grain": 5})
        self.w.structures[self.st.id] = self.st

    def post(self):
        ok, msg = self.e.start(self.o, {"verb": "post", "give": [{"item": "grain", "qty": 1}],
                                        "get": [{"item": "berries", "qty": 3}]})
        self.assertTrue(ok, msg)

    def test_post_and_trade_at_a_closed_store(self):
        self.post()
        self.assertEqual(self.st.trade, {"give": {"grain": 1}, "get": {"berries": 3}})
        self.b.inventory = {"berries": 10}
        self.assertIn("trade", available_verbs(self.e, self.b))
        self.assertIn("gives grain 1 for berries 3 (has 5 grain)", build_prompt(self.e, self.b))
        ok, msg = self.e.start(self.b, {"verb": "trade", "qty": 5})
        self.assertTrue(ok, msg)
        st, msg = self.e.do_trade(self.b, self.b.activity)
        self.assertEqual(st, "done", msg)
        self.assertEqual(self.b.inventory, {"berries": 1, "grain": 3})         # three times: berries ran short
        self.assertEqual(self.st.inventory, {"grain": 2, "berries": 9})
        self.assertTrue(any(k == "traded_in" for _, oid, k, _ in self.o.ledger if oid == self.b.id))

    def test_taking_from_a_closed_store_points_to_its_trade(self):
        self.post()
        ok, msg = self.e.start(self.b, {"verb": "take", "target": "store", "x": self.st.x, "y": self.st.y})
        self.assertFalse(ok)
        self.assertIn("but it trades: gives grain 1 for berries 3 (use trade)", msg)

    def test_refusals_say_what_is_short(self):
        self.post()
        self.b.inventory = {}
        ok, msg = self.e.start(self.b, {"verb": "trade"})
        self.assertIn("you do not have 3 berries", msg)
        self.b.inventory = {"berries": 3}
        self.st.inventory = {}
        ok, msg = self.e.start(self.b, {"verb": "trade"})
        self.assertIn("holds too little grain", msg)

    def test_only_ones_own_store_and_both_sides(self):
        ok, msg = self.e.start(self.b, {"verb": "post", "give": [{"item": "grain", "qty": 1}], "get": [{"item": "berries", "qty": 1}]})
        self.assertFalse(ok)
        ok, msg = self.e.start(self.o, {"verb": "post", "give": [{"item": "grain", "qty": 1}]})
        self.assertFalse(ok)
        self.post()
        ok, _ = self.e.start(self.o, {"verb": "post"})
        self.assertTrue(ok)
        self.assertIsNone(self.st.trade)

    def test_a_remembered_trade_is_walked_to(self):
        self.post()
        self.e.remember_places(self.b)
        self.assertIn("(it gives grain 1 for berries 3)", self.b.known[key(self.st.x, self.st.y)][1])
        place(self.w, self.b, self.st.x + 4, self.st.y)
        self.b.inventory = {"berries": 3}
        ok, msg = self.e.start(self.b, {"verb": "trade"})
        self.assertTrue(ok, msg)
        self.assertEqual(self.b.activity["verb"], "go")

    def test_a_full_store_or_load_limits_the_trade(self):
        self.st.trade = {"give": {"grain": 1}, "get": {"wood": 2}}
        self.st.inventory = {"grain": 5, "stone": 21}       # room for only a trade or two of wood
        self.b.inventory = {"wood": 8}
        self.e.set_act(self.b, "trade", sid=self.st.id, times=4, left=1)
        st, msg = self.e.do_trade(self.b, self.b.activity)
        self.assertEqual(st, "done", msg)
        self.assertLess(self.b.inventory.get("grain"), 4)
        self.assertLessEqual(I.weight(self.st.inventory), 60)

    def test_plant_walks_to_a_free_farm_one_knows(self):
        f = Structure(id=self.w.new_id(), kind="farm", x=self.st.x + 5, y=self.st.y, owner=self.o.id, done=True,
                      access="anyone")
        self.w.structures[f.id] = f
        self.e.remember_places(self.b)
        self.b.known[key(f.x, f.y)] = ["structure", "a farm", self.w.tick]
        self.b.inventory = {"seeds": 4}
        self.b.plan = []
        ok, msg = self.e.start(self.b, {"verb": "plant", "qty": 4})
        self.assertTrue(ok, msg)
        self.assertEqual(self.b.activity["verb"], "go")
        self.assertEqual(self.b.plan[0]["verb"], "plant")
        f.access = "owner"                                   # closed to them: not theirs to sow
        self.b.plan, self.b.activity = [], None
        ok, msg = self.e.start(self.b, {"verb": "plant", "qty": 4})
        self.assertFalse(ok and self.b.activity and self.b.activity.get("x") == f.x)

    def test_old_saves_load(self):
        d = self.w.to_dict()
        for v in d["structures"].values():
            v.pop("trade", None)
        w2 = World.from_dict(json.loads(json.dumps(d)))
        self.assertIsNone(w2.structures[self.st.id].trade)


if __name__ == "__main__":
    unittest.main()
