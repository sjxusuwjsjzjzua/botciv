"""c92: a field named by place may be reaped though it is another's; the fields beside it may not (world4: a bot's harvest
of its own field went on into its neighbours', some 6,000 crops taken in 94 days); go to a kind of place named as
"to"; mending without the material makes or gathers it first."""
import unittest

from civ.acts import mend_stuff
from civ.content import BUILDINGS
from civ.engine import Engine
from civ.gen import generate
from civ.plan import Planner
from civ.world import Building


class C92(unittest.TestCase):
    def setUp(self):
        self.w = w = generate({"seed": 6, "people": 16, "width": 40, "height": 40, "bands": 1, "ai": 0})
        self.e = Engine(w)
        adults = [p for p in w.living() if p.adult(w.tick)]
        self.me, self.them = adults[0], next(p for p in adults[1:] if p.id != adults[0].partner)
        x, y = self.me.x, self.me.y
        for q in (self.me, self.them):
            q.inv, q.act, q.intent, q.satiety = {}, None, {"goal": "", "plan": []}, 16
        w.place(self.me, x, y)
        w.place(self.them, x + 10, y + 10)
        self.mine = self.field(x + 1, y, self.me)
        self.theirs = self.field(x - 1, y, self.them)

    def field(self, x, y, owner):
        b = Building(id=self.w.new_id(), kind="farm", x=x, y=y, owner=owner.id, done=True, inv={"grain": 6})
        b.crop = {"what": "grain", "ripe": True, "yield": 6, "ripe_at": self.w.tick}
        self.w.buildings[b.id] = b
        self.w.at[f"{x},{y}"] = b.id
        return b

    def reap(self, x, y):
        ok, why = self.e.start(self.me, {"do": "gather", "item": "grain", "n": 60, "x": x, "y": y})
        self.assertTrue(ok, why)
        for _ in range(16):
            if not self.me.act:
                break
            r, _ = self.e.do_gather(self.me, self.me.act)
            if r == "done":
                break

    def test_ones_own_field_reaped_and_the_neighbours_left(self):
        self.assertFalse(self.w.may_use(self.me, self.theirs))
        self.reap(self.mine.x, self.mine.y)
        self.assertFalse(self.mine.inv.get("grain"))
        self.assertEqual(self.theirs.inv.get("grain"), 6)
        self.assertFalse(any(e["kind"] == "take_crop" for e in self.e.log.events))

    def test_a_field_named_by_place_is_still_reaped_knowingly(self):
        self.reap(self.theirs.x, self.theirs.y)
        self.assertLess(self.theirs.inv.get("grain", 0), 6)
        self.assertTrue(any(e["kind"] == "take_crop" for e in self.e.log.events))

    def test_go_to_a_kind_of_place_named_as_to(self):
        st = Building(id=self.w.new_id(), kind="store", x=self.me.x + 3, y=self.me.y + 2, owner=self.me.id, done=True)
        self.w.buildings[st.id] = st
        self.w.at[f"{st.x},{st.y}"] = st.id
        for to in ("store", "my store"):
            self.me.act = None
            ok, why = self.e.start(self.me, {"do": "go", "to": to})
            self.assertTrue(ok, why)
            self.assertEqual(self.me.act["dest"][:2], [st.x, st.y])
        ok, why = self.e.start(self.me, {"do": "go", "to": "Nobodyatall"})
        self.assertFalse(ok)
        self.assertIn("no one called Nobodyatall", why)

    def test_mending_without_rope_makes_it_from_fibre_first(self):
        pen = next(k for k in ("pen", "loom") if k in BUILDINGS)
        b = Building(id=self.w.new_id(), kind=pen, x=self.me.x, y=self.me.y + 1, owner=self.me.id, done=True, hp=1)
        self.w.buildings[b.id] = b
        self.w.at[f"{b.x},{b.y}"] = b.id
        stuff = mend_stuff(b)
        if stuff != "rope":
            self.skipTest(f"a {pen} is mended with {stuff}")
        self.me.inv = {"fibre": 6}
        self.me.intent = {"goal": "mend", "plan": []}
        ok, why = self.e.start(self.me, {"do": "mend", "x": b.x, "y": b.y})
        self.assertTrue(ok, why)
        self.assertEqual(self.me.act["do"], "craft")
        self.assertEqual(self.me.intent["plan"][-1]["do"], "mend")


    def seller_with(self, item, n=4, price=2):
        st = Building(id=self.w.new_id(), kind="store", x=self.me.x + 4, y=self.me.y, owner=self.them.id, done=True,
                      inv={item: n})
        st.trade = [{"give": {item: 1}, "get": {"grain": price}}]
        self.w.buildings[st.id] = st
        self.w.at[f"{st.x},{st.y}"] = st.id
        return st

    def test_one_not_able_at_a_craft_buys_from_a_maker_who_sells(self):
        st = self.seller_with("rope")
        self.me.skills.pop("cordage", None)
        self.me.inv = {"grain": 12, "fibre": 6}
        steps = Planner(self.e).get(self.me, "rope", 2)
        self.assertEqual(steps, [{"do": "trade", "x": st.x, "y": st.y, "item": "rope", "n": 2}])
        ok, why = self.e.start(self.me, steps[0])
        self.assertTrue(ok, why)
        for _ in range(12):
            if self.e.do_trade(self.me, self.me.act)[0] == "done":
                break
        self.assertEqual(self.me.inv.get("rope"), 2)
        self.assertEqual(st.inv.get("grain"), 4)

    def test_a_maker_makes_their_own_and_no_one_pays_with_their_last_food(self):
        self.seller_with("rope")
        self.me.skills["cordage"] = 0.5
        self.me.inv = {"grain": 12, "fibre": 6}
        self.assertNotIn("trade", [s["do"] for s in Planner(self.e).get(self.me, "rope", 1)])
        self.me.skills["cordage"] = 0.0
        self.me.inv = {"grain": 3, "fibre": 6}
        self.assertNotIn("trade", [s["do"] for s in Planner(self.e).get(self.me, "rope", 1) or []])


    def test_a_season_split_over_pieces_is_counted_whole(self):
        import os
        import tempfile
        from civ.census import Census
        path = os.path.join(tempfile.mkdtemp(), "history.jsonl")
        a = Census()
        a.write({"kind": "birth"})
        a.write({"kind": "death", "cause": "starved"})
        a.keep(path)
        b = Census()
        b.resume(path)
        b.write({"kind": "birth"})
        line = b.line(self.w, set())
        self.assertEqual((line["births"], line["deaths"]), (2, {"starved": 1}))


    def test_the_hungry_are_told_where_their_own_food_is(self):
        from civ.prompt import build_prompt
        pen = Building(id=self.w.new_id(), kind="pen", x=self.me.x + 2, y=self.me.y + 2, owner=self.me.id, done=True,
                       inv={"milk": 30}, animals={"goat": 4})
        self.w.buildings[pen.id] = pen
        self.w.at[f"{pen.x},{pen.y}"] = pen.id
        self.me.satiety, self.me.inv = 3, {}
        self.assertIn(f"nearest: milk 30 in your pen at ({pen.x},{pen.y})", build_prompt(self.e, self.me))
        pen.inv = {}
        self.assertIn(f"your pen at ({pen.x},{pen.y}) has goat to slaughter", build_prompt(self.e, self.me))


    def test_the_starving_slaughter_from_their_own_herd_when_there_is_no_milk(self):
        from unittest import mock
        from civ.minds.bot import BotMind
        pen = Building(id=self.w.new_id(), kind="pen", x=self.me.x + 2, y=self.me.y + 2, owner=self.me.id, done=True,
                       animals={"pig": 5})
        self.w.buildings[pen.id] = pen
        self.w.at[f"{pen.x},{pen.y}"] = pen.id
        bot = BotMind(self.e)
        with mock.patch.object(self.e, "find", return_value=None), mock.patch.object(self.e, "herds_of", return_value=[]), \
                mock.patch.object(self.e, "water_near", return_value=False), mock.patch.object(self.w, "t", return_value="."):
            plan = bot.food_plan(self.me)
        self.assertEqual(plan[0], {"do": "slaughter", "animal": "pig", "x": pen.x, "y": pen.y})


if __name__ == "__main__":
    unittest.main()
