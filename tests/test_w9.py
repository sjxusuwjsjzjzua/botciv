"""Rules w9: walking to what you name, smoking and drying food, partners, ideas made real."""
import unittest

from botciv import realized
from botciv.engine import Engine
from botciv.log import NullLog
from botciv.world import Structure
from tests.test_engine import world, open_tile, place


class W9(unittest.TestCase):
    def setUp(self):
        self.w = world(2)
        self.e = Engine(self.w, NullLog())
        self.a, self.b = self.w.living()[:2]
        for ag in self.w.living():
            ag.inventory = {}
        x, y = open_tile(self.w)
        self.x, self.y = x, y
        place(self.w, self.a, x, y)
        place(self.w, self.b, x + 1, y)

    def act(self, agent, action, ticks=1, plan=None):
        self.e.apply_decision(agent, {"action": action, "plan": plan or [], "memory": "m"})
        for _ in range(ticks):
            self.e.step_activities()
            self.e.step_world()

    def structure(self, kind, x, y, owner, **kw):
        s = Structure(id=self.w.new_id(), kind=kind, x=x, y=y, owner=owner, done=True, **kw)
        self.w.structures[s.id] = s
        return s

    def far_spot(self, d=4):
        for dx in range(d, d + 6):
            x = self.x + dx if self.x + dx < self.w.w else self.x - dx
            if self.w.passable(x, self.y):
                return x, self.y
        raise AssertionError("no spot")

    # ---- walking to what you name
    def test_put_walks_to_your_own_store(self):
        sx, sy = self.far_spot()
        store = self.structure("store", sx, sy, self.a.id)
        self.a.inventory = {"berries": 5}
        self.act(self.a, {"verb": "put", "item": "berries", "qty": 5}, ticks=12)
        self.assertEqual(store.inventory.get("berries"), 5)
        self.assertEqual(self.a.inventory.get("berries", 0), 0)

    def test_go_to_a_kind_of_building_or_a_named_place(self):
        sx, sy = self.far_spot()
        self.structure("shelter", sx, sy, self.a.id)
        self.act(self.a, {"verb": "go", "target": "shelter"}, ticks=10)
        self.assertLessEqual(abs(self.a.x - sx) + abs(self.a.y - sy), 1)
        self.w.places.append([self.x, self.y, "Stone Ford", self.b.id, 0])
        self.act(self.a, {"verb": "go", "target": "stone ford"}, ticks=10)
        self.assertEqual((self.a.x, self.a.y), (self.x, self.y))

    def test_take_walks_to_a_pile_a_few_steps_off(self):
        px, py = self.far_spot(3)
        self.e.drop_pile(px, py, {"bone": 2})
        self.act(self.a, {"verb": "take", "target": "ground", "item": "bone", "qty": 2, "x": px, "y": py}, ticks=10)
        self.assertEqual(self.a.inventory.get("bone"), 2)

    def test_continue_with_nothing_is_no_failure(self):
        self.a.activity, self.a.plan = None, []
        self.act(self.a, {"verb": "continue"})
        self.assertFalse(any("could not" in t for _, t in self.a.events))

    # ---- smoking and drying
    def fire_beside(self, who):
        return self.structure("fire", who.x, who.y + 1 if self.w.passable(who.x, who.y + 1) else who.y - 1,
                              who.id, fuel=48)

    def test_someone_who_knows_smokes_fish_that_keeps(self):
        self.fire_beside(self.a)
        self.a.know = ["smoking"]
        self.a.inventory = {"fish": 6}
        self.act(self.a, {"verb": "smoke", "item": "fish"}, ticks=3)
        self.assertEqual(self.a.inventory.get("smoked_fish"), 6)
        self.assertEqual(self.a.inventory.get("fish", 0), 0)

    def test_without_the_knack_food_is_kept_until_worked_out(self):
        self.fire_beside(self.a)
        self.a.inventory = {"berries": 4}
        self.w.rng.seed(3)
        tries = 0
        while "smoking" not in self.a.know and tries < 300:
            self.act(self.a, {"verb": "smoke", "item": "berries"}, ticks=1)
            self.assertEqual(self.a.inventory.get("berries", 0) + self.a.inventory.get("dried_berries", 0), 4)
            tries += 1
        self.assertIn("smoking", self.a.know)

    def test_a_technique_can_be_taught(self):
        self.a.know = ["smoking"]
        self.act(self.a, {"verb": "teach", "target": self.b.name, "text": "smoking fish"})
        self.assertIn("smoking", self.b.know)

    # ---- partners
    def test_partners_share_stores_and_inherit(self):
        self.act(self.a, {"verb": "pledge", "target": self.b.name})
        pid = max(self.w.proposals)
        self.act(self.b, {"verb": "accept", "id": pid})
        self.assertEqual((self.a.partner, self.b.partner), (self.b.id, self.a.id))
        store = self.structure("store", self.x, self.y + 1, self.a.id)
        self.assertTrue(self.w.may_use(self.b, store))
        self.e.kill(self.a, "starved")
        self.assertEqual(store.owner, self.b.id)

    # ---- a road to surplus
    def test_picking_berries_in_summer_sometimes_finds_seeds(self):
        from botciv.world import unkey
        self.w.tick = self.w.tpd() * self.w.cfg["world"]["days_per_season"] + 1
        k = next(iter(self.w.bushes))
        self.a.x, self.a.y = unkey(k)
        seeds = 0
        for _ in range(200):
            self.w.bushes[k]["b"] = 8
            self.a.inventory = {}
            self.act(self.a, {"verb": "gather", "item": "berries", "qty": 1}, ticks=0)
            self.e.step_activities()
            seeds += self.a.inventory.get("seeds", 0)
        self.assertGreater(seeds, 5)

    # ---- ideas made real
    def test_the_first_living_imaginer_is_credited_once(self):
        self.a.ideas = [[50, "a way to keep fish from spoiling"]]
        self.b.ideas = [[10, "smoke meat over the fire"]]
        self.w.realized = []
        got = realized.apply(self.e)
        self.assertIn(("smoking", self.b.name), got)
        self.assertIn("smoking", self.b.know)
        self.assertNotIn("smoking", self.a.know)
        self.assertEqual(realized.apply(self.e), [])
        self.assertEqual(self.a.ideas, [])           # a wish that came true is no longer listed as one
        self.assertEqual(self.b.ideas, [])


if __name__ == "__main__":
    unittest.main()
