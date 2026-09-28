"""Rules w13: what keeps theft in check can emerge. Witnesses remember; people who
stand together can take by force, openly; a person's own people beside them resist."""
import unittest

from botciv.engine import Engine
from botciv.log import NullLog
from botciv.prompt import build_prompt
from tests.test_engine import world, open_tile, place


class W13(unittest.TestCase):
    def setUp(self):
        self.w = world(2)
        self.e = Engine(self.w, NullLog())
        self.a, self.b, self.c, self.d = self.w.living()[:4]
        for ag in self.w.living():
            ag.inventory = {}
            ag.x, ag.y = 0, 0
        x, y = open_tile(self.w)
        place(self.w, self.a, x, y)
        place(self.w, self.b, x + 1, y)
        place(self.w, self.c, x + 2, y)

    def steal(self, thief, victim, times=40):
        for _ in range(times):
            victim.inventory = {"berries": 10}
            thief.activity = {"verb": "steal", "victim": victim.id, "item": "berries", "qty": 3, "n": 0, "left": 1}
            self.e.do_steal(thief, thief.activity)

    def test_witnesses_remember_who_stole(self):
        self.w.tick = 1                     # daylight
        self.steal(self.a, self.b)
        self.assertTrue(any(k == "saw_steal" and oid == self.a.id for _, oid, k, _ in self.c.ledger))
        self.c.wake = ["x"]
        self.assertIn("you have seen them steal", build_prompt(self.e, self.c))

    def test_people_standing_together_take_by_force(self):
        self.a.partner, self.c.partner = self.c.id, self.a.id       # c is with a, beside b
        self.b.inventory = {"berries": 10}
        self.a.activity = {"verb": "steal", "victim": self.b.id, "item": "berries", "qty": 3, "n": 0, "left": 1}
        took = 0
        for _ in range(20):
            self.b.inventory = {"berries": 10}
            self.e.do_steal(self.a, self.a.activity)
            took += 10 - self.b.inventory.get("berries", 0)
        self.assertGreater(took, 20 * 3 * 0.7)
        self.assertTrue(any(k == "forced" for _, _, k, _ in self.b.ledger))
        self.assertFalse(any(k == "stole" for _, _, k, _ in self.a.ledger))

    def test_ones_own_people_beside_you_resist(self):
        self.a.partner, self.c.partner = self.c.id, self.a.id
        self.d.x, self.d.y = self.b.x, self.b.y + 1 if self.w.passable(self.b.x, self.b.y + 1) else self.b.y - 1
        self.b.children.append(self.d.id)                  # d stands by b
        self.assertTrue(self.e.backers(self.b, self.a))
        self.assertTrue(self.e.backers(self.a, self.b))
        # one backer each: no force, it is a plain attempt again
        self.b.inventory = {"berries": 10}
        act = {"verb": "steal", "victim": self.b.id, "item": "berries", "qty": 3, "n": 0, "left": 1}
        self.e.do_steal(self.a, act)
        self.assertFalse(any(k == "forced" for _, _, k, _ in self.b.ledger))


if __name__ == "__main__":
    unittest.main()
