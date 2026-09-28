"""A full load: hungry people eat as they pick, and the world says why nothing more fits."""
import unittest

from botciv.engine import Engine
from botciv.log import NullLog
from botciv.prompt import build_prompt
from botciv.world import key
from tests.test_engine import world, open_tile, place


class Load(unittest.TestCase):
    def setUp(self):
        self.w = world(1)
        self.e = Engine(self.w, NullLog())
        self.a = self.w.living()[0]
        for ag in self.w.living():
            ag.inventory = {}
            ag.x, ag.y = 0, 0
        self.x, self.y = open_tile(self.w)
        place(self.w, self.a, self.x, self.y)
        self.w.bushes = {key(self.x, self.y): {"b": 8, "strips": 0, "regrow": 0}}
        self.w.tick = 1                                   # day, not night
        self.a.inventory = {"wood": 10}                   # 20 of 20

    def gather(self, hours):
        self.e.apply_decision(self.a, {"action": {"verb": "gather", "item": "berries"}, "memory": "m"})
        for _ in range(hours):
            self.e.step_activities()

    def test_hungry_and_full_eats_off_the_bush(self):
        self.a.satiety = 2
        self.gather(3)
        self.assertGreater(self.a.satiety, 2)
        self.assertLess(self.w.bushes[key(self.x, self.y)]["b"], 8)
        self.assertEqual(self.a.inventory.get("berries", 0), 0)

    def test_fed_and_full_is_told_why(self):
        self.a.satiety = 20
        self.gather(2)
        told = " ".join(str(x) for x in self.a.events)
        self.assertIn("carry all you can", told)
        self.assertIn("wood", told)

    def test_prompt_says_full(self):
        self.assertIn("full, you can pick up nothing more", build_prompt(self.e, self.a))
        self.assertIn("carry a load of 20", build_prompt(self.e, self.a))

    def test_fed_with_room_keeps_what_they_pick(self):
        self.a.inventory = {}
        self.a.satiety = 20
        self.gather(2)
        self.assertGreater(self.a.inventory.get("berries", 0), 0)


class Reach(unittest.TestCase):
    """What a person means when they name someone a little way off, or a store without a thing."""
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

    def test_give_to_someone_in_sight_walks_there_first(self):
        tiles = [(self.x + dx, self.y + dy) for dx in range(-3, 4) for dy in range(-3, 4)
                 if abs(dx) + abs(dy) >= 2 and self.w.in_bounds(self.x + dx, self.y + dy)
                 and self.w.passable(self.x + dx, self.y + dy, self.b)]
        place(self.w, self.b, *tiles[0])
        self.a.inventory = {"wood": 2}
        self.e.apply_decision(self.a, {"action": {"verb": "give", "target": self.b.name, "item": "wood"}, "memory": "m"})
        for _ in range(8):
            self.e.step_activities()
        self.assertEqual(self.b.inventory.get("wood"), 1)

    def test_take_from_store_without_a_thing_means_food(self):
        from botciv.world import Structure
        s = Structure(id=self.w.new_id(), kind="store", x=self.x, y=self.y, owner=self.a.id, done=True,
                      inventory={"wood": 8, "berries": 20})
        self.w.structures[s.id] = s
        self.e.apply_decision(self.a, {"action": {"verb": "take", "target": "store"}, "memory": "m"})
        self.e.step_activities()
        self.assertEqual(self.a.inventory.get("berries"), 8)
        self.assertFalse(self.a.inventory.get("wood"))


if __name__ == "__main__":
    unittest.main()
