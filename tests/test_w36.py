"""Rules w36: a building with no living owner falls apart within about 20 days, spilling what it
holds, unless someone claims it by building the same thing on it."""
import unittest

from botciv.engine import Engine, Structure
from botciv.log import NullLog
from botciv.prompt import build_prompt
from tests.test_engine import world, place, open_tile


class W36(unittest.TestCase):
    def setUp(self):
        self.w = world(1)
        self.e = Engine(self.w, NullLog())
        self.a, self.dead = self.w.living()[:2]
        x, y = open_tile(self.w)
        place(self.w, self.a, x, y)
        self.st = Structure(id=self.w.new_id(), kind="store", x=x + 1, y=y, owner=self.dead.id, done=True,
                            access="anyone", hp=20, inventory={"stone": 3, "grain": 2})
        self.w.structures[self.st.id] = self.st
        self.dead.alive = False

    def test_it_falls_apart_and_spills(self):
        for _ in range(20):
            self.w.tick = (self.w.tick // 12 + 1) * 12
            self.e.structures_tick()
        self.assertNotIn(self.st.id, self.w.structures)
        self.assertEqual(self.w.piles.get(f"{self.st.x},{self.st.y}"), {"stone": 3, "grain": 2})

    def test_seen_as_abandoned(self):
        self.st.hp = 8
        p = build_prompt(self.e, self.a)
        self.assertIn(f"abandoned, once {self.dead.name}'s", p)
        self.assertIn("falling apart", p)

    def test_claimed_by_mending(self):
        self.a.inventory = {"wood": 1}
        ok, msg = self.e.start(self.a, {"verb": "build", "item": "store", "x": self.st.x, "y": self.st.y})
        self.assertTrue(ok, msg)
        self.assertEqual((self.st.owner, self.st.access, self.st.hp), (self.a.id, "owner", 20))
        self.assertEqual(self.a.inventory, {})
        self.w.tick = 12
        self.e.structures_tick()
        self.assertEqual(self.st.hp, 20)                     # owned again: no longer falls apart

    def test_a_living_owners_building_is_not_claimed(self):
        self.dead.alive = True
        self.a.inventory = {"wood": 5}
        ok, msg = self.e.start(self.a, {"verb": "build", "item": "store", "x": self.st.x, "y": self.st.y})
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
