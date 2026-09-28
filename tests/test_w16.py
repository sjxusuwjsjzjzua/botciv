"""Rules w16: a hungry person with a full load eats the food they cannot carry, wherever it
comes from (the ground, a store, a hunt), and can eat what lies at their feet."""
import unittest

from botciv.engine import Engine
from botciv.log import NullLog
from botciv.prompt import build_prompt
from botciv.world import Structure, key
from tests.test_engine import world, open_tile, place


class W16(unittest.TestCase):
    def setUp(self):
        self.w = world(2)
        self.e = Engine(self.w, NullLog())
        self.a, self.b = self.w.living()[:2]
        for ag in self.w.living():
            ag.inventory = {}
            ag.x, ag.y = 0, 0
        self.x, self.y = open_tile(self.w)
        place(self.w, self.a, self.x, self.y)
        self.w.tick = 1
        self.a.inventory = {"wood": 10}                   # 20 of 20: full
        self.w.piles = {key(self.x, self.y): {"meat": 5}}

    def run_act(self, action, hours=2):
        self.e.apply_decision(self.a, {"action": action, "memory": "m"})
        for _ in range(hours):
            self.e.step_activities()

    def test_eat_reaches_the_ground(self):
        self.a.satiety = 0
        self.run_act({"verb": "eat", "item": "meat"})
        self.assertGreaterEqual(self.a.satiety, 12)
        self.assertLess(self.w.piles.get(key(self.x, self.y), {}).get("meat", 0), 5)

    def test_eat_alongside_reaches_the_ground(self):
        self.a.satiety = 0
        self.e.apply_decision(self.a, {"eat": {"item": "food"}, "action": {"verb": "wait", "qty": 1}, "memory": "m"})
        self.assertGreater(self.a.satiety, 0)

    def test_hungry_and_full_eats_what_they_take_from_the_ground(self):
        self.a.satiety = 2
        self.run_act({"verb": "take", "target": "ground", "item": "meat"})
        self.assertGreater(self.a.satiety, 2)
        self.assertEqual(self.a.inventory.get("meat", 0), 0)

    def test_fed_and_full_is_still_refused(self):
        self.a.satiety = 20
        self.run_act({"verb": "take", "target": "ground", "item": "meat"})
        self.assertEqual(self.w.piles[key(self.x, self.y)]["meat"], 5)
        self.assertIn("carry all you can", " ".join(str(x) for x in self.a.events))

    def test_eating_from_anothers_store_is_still_taking(self):
        self.w.piles = {}
        s = Structure(id=self.w.new_id(), kind="store", x=self.x, y=self.y, owner=self.b.id, done=True,
                      inventory={"berries": 10}, access="anyone")
        self.w.structures[s.id] = s
        self.a.satiety = 2
        self.run_act({"verb": "take", "target": "store", "item": "berries", "qty": 6})
        self.assertGreater(self.a.satiety, 2)
        self.assertLess(s.inventory.get("berries", 0), 10)
        self.assertTrue(any(k == "store_out" and oid == self.a.id for _, oid, k, _ in self.b.ledger))

    def test_rules_say_so(self):
        p = build_prompt(self.e, self.a)
        self.assertIn("on the ground beside you", p)
        self.assertIn("whether picked, caught, hunted or taken", p)


if __name__ == "__main__":
    unittest.main()
