"""c92: a field named by place may be reaped though it is another's; the fields beside it may not (world4: a bot's harvest
of its own field went on into its neighbours', some 6,000 crops taken in 94 days); go to a kind of place named as
"to"; mending without the material makes or gathers it first."""
import unittest

from civ.acts import mend_stuff
from civ.content import BUILDINGS
from civ.engine import Engine
from civ.gen import generate
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
        b.crop = {"what": "grain", "ripe": True, "yield": 6}
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


if __name__ == "__main__":
    unittest.main()
