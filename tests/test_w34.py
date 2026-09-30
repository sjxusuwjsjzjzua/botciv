"""Rules w34: things of one's own making. Named, described, made from what one carries; they do
nothing by themselves and are carried, given, traded and inherited like anything else."""
import json
import unittest

from botciv import items as I
from botciv.engine import Engine
from botciv.log import NullLog
from botciv.prompt import build_prompt
from botciv.standing import worth
from botciv.world import World
from tests.test_engine import world, place, open_tile


class W34(unittest.TestCase):
    def setUp(self):
        self.w = world(1)
        self.e = Engine(self.w, NullLog())
        self.a, self.b = self.w.living()[:2]
        x, y = open_tile(self.w)
        place(self.w, self.a, x, y)
        place(self.w, self.b, x + 1, y)

    def make(self, **kw):
        ok, msg = self.e.start(self.a, {"verb": "make", **kw})
        self.assertTrue(ok, msg)
        while self.a.activity:
            st, msg = self.e.do_make(self.a, self.a.activity)
            if st != "go":
                self.a.activity = None
        return msg

    def test_make_name_and_carry(self):
        self.a.inventory = {"bone": 5, "fibre": 3}
        msg = self.make(name="Sun token", text="a bone disc carved with a sun", item="bone", item2="fibre", qty=3)
        self.assertIn("3 Sun token", msg)
        self.assertEqual(self.a.inventory, {"bone": 2, "sun_token": 3})
        self.assertTrue(I.is_good("sun_token"))
        self.assertIn("Sun token (\"a bone disc carved with a sun\"; first made by", build_prompt(self.e, self.a))
        self.assertIn("carries Sun token", build_prompt(self.e, self.b))
        self.assertGreater(worth({"sun_token": 1}), 0)

    def test_given_and_named_in_deals(self):
        self.a.inventory = {"bone": 2}
        self.make(name="Crown of reeds", item="bone")
        ok, msg = self.e.start(self.a, {"verb": "give", "target": self.b.name, "item": "crown of reeds"})
        self.assertTrue(ok, msg)
        self.e.do_give(self.a, self.a.activity)
        self.assertEqual(self.b.inventory.get("crown_of_reeds"), 1)

    def test_what_does_something_is_crafted_not_made(self):
        self.a.inventory = {"bone": 2, "wood": 2}
        for name in ("spear", "store"):
            ok, msg = self.e.start(self.a, {"verb": "make", "name": name, "item": "bone"})
            self.assertFalse(ok)
        ok, msg = self.e.start(self.a, {"verb": "make", "name": "cake", "item": "berries"})
        self.assertFalse(ok)
        ok, msg = self.e.start(self.a, {"verb": "make", "name": "big idol", "item": "wood", "qty": 5})
        self.assertIn("you need 5 wood", msg)

    def test_saved_goods_come_back(self):
        self.a.inventory = {"stone": 1}
        self.make(name="Hearth stone", item="stone")
        d = json.loads(json.dumps(self.w.to_dict()))
        del I.ITEMS["hearth_stone"]
        w2 = World.from_dict(d)
        self.assertIn("hearth_stone", I.ITEMS)
        self.assertEqual(w2.goods["hearth_stone"]["name"], "Hearth stone")
        d.pop("goods")
        self.assertEqual(World.from_dict(d).goods, {})


if __name__ == "__main__":
    unittest.main()
