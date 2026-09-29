"""Rules w21: taking from the ground without naming a thing takes the food there, not the bone and wood."""
import unittest

from botciv.engine import Engine
from botciv.log import NullLog
from botciv.world import key
from tests.test_engine import world


class W21(unittest.TestCase):
    def setUp(self):
        self.w = world(1)
        self.e = Engine(self.w, NullLog())
        self.a = self.w.living()[0]
        self.a.inventory = {}
        self.a.satiety = 20
        self.w.piles = {}

    def take(self, **act):
        ok, msg = self.e.start(self.a, {"verb": "take", "target": "ground", **act})
        if ok:
            self.e.step_activities()
        return ok, msg

    def test_no_item_takes_only_food(self):
        k = key(self.a.x, self.a.y)
        self.w.piles[k] = {"meat": 3, "bone": 15, "wood": 4, "hide": 2}
        ok, msg = self.take()
        self.assertTrue(ok, msg)
        self.assertEqual(self.a.inventory, {"meat": 3})
        self.assertEqual(self.w.piles[k], {"bone": 15, "wood": 4, "hide": 2})

    def test_no_food_there_takes_what_lies_there(self):
        self.w.piles[key(self.a.x, self.a.y)] = {"seeds": 13, "net": 1}
        ok, msg = self.take()
        self.assertTrue(ok, msg)
        self.assertEqual(self.a.inventory, {"seeds": 13, "net": 1})

    def test_one_kind_in_a_store_is_taken_without_naming_it(self):
        from botciv.world import Structure
        sid = self.w.new_id()
        st = Structure(id=sid, kind="store", x=self.a.x, y=self.a.y, owner=self.a.id, done=True)
        st.inventory = {"seeds": 15}
        self.w.structures[sid] = st
        ok, msg = self.e.start(self.a, {"verb": "take", "target": "store"})
        self.assertTrue(ok, msg)
        self.e.step_activities()
        self.assertEqual(self.a.inventory.get("seeds"), 15)

    def test_a_pile_of_one_kind_is_taken_without_naming_it(self):
        k = key(self.a.x, self.a.y)
        self.w.piles[k] = {"wood": 4}
        ok, msg = self.take()
        self.assertTrue(ok, msg)
        self.assertEqual(self.a.inventory, {"wood": 4})

    def test_food_next_to_you_is_found_past_a_bare_pile(self):
        self.w.piles[key(self.a.x, self.a.y)] = {"bone": 5}
        nx = self.a.x + 1 if self.a.x + 1 < self.w.w else self.a.x - 1
        self.w.piles[key(nx, self.a.y)] = {"berries": 4}
        ok, msg = self.take(item="food")
        self.assertTrue(ok, msg)
        self.assertEqual(self.a.inventory.get("berries"), 4)

    def test_named_item_is_still_taken(self):
        self.w.piles[key(self.a.x, self.a.y)] = {"bone": 15, "meat": 1}
        ok, msg = self.take(item="bone", qty=5)
        self.assertTrue(ok, msg)
        self.assertEqual(self.a.inventory, {"bone": 5})


if __name__ == "__main__":
    unittest.main()
