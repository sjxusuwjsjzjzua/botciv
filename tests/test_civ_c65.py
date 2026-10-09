"""c65 (grand world, Phase 1.1): surplus goes somewhere. Things left on the ground rot, rust or are carried off
within days (metal slowest); bots gather the land's plain things only while their household runs short, and
otherwise rest; the rules say so."""
import unittest

from civ.content import items as I
from civ.engine import Engine
from civ.gen import generate
from civ.minds.bot import BotMind, STOCK
from civ.prompt import build_prompt
from civ.world import Building, key, TPD


class C65(unittest.TestCase):
    def setUp(self):
        self.w = generate({"seed": 4, "people": 12, "width": 40, "height": 40, "bands": 2, "ai": 0})
        self.e = Engine(self.w)
        self.p = next(q for q in self.w.living() if q.adult(self.w.tick))

    def test_the_ground_keeps_nothing_metal_longest(self):
        self.assertGreater(I.ground_loss("wood"), I.ground_loss("stone"))
        self.assertGreater(I.ground_loss("stone"), I.ground_loss("bronze_axe"))
        self.assertEqual(I.ground_loss("tablet:12"), I.ground_loss("tablet"))
        self.w.piles[key(3, 3)] = {"wood": 200, "fibre": 20, "bronze_axe": 20}
        for _ in range(10):
            self.e.ground_day()
        pile = self.w.piles.get(key(3, 3), {})
        self.assertLess(pile.get("wood", 0), 60)            # 200 * 0.85^10 is about 39
        self.assertGreater(pile.get("bronze_axe", 0), 10)   # 20 * 0.98^10 is about 16
        for _ in range(60):
            self.e.ground_day()
        self.assertNotIn("wood", self.w.piles.get(key(3, 3), {}))

    def test_a_household_with_enough_rests_and_one_short_gathers(self):
        mind = BotMind(self.e)
        p = self.p
        store = Building(id=self.w.new_id(), kind="store", x=p.x, y=p.y, owner=p.id, done=True)
        self.w.buildings[store.id] = store
        store.inv = dict(STOCK)
        p.inv = {"berries": 10}
        self.assertEqual(mind.forage(p)["goal"], "rest")
        store.inv["wood"] = 0
        got = mind.forage(p)
        if self.e.find(p, "wood"):
            self.assertEqual(got["plan"][0], {"do": "gather", "item": "wood", "n": 6})

    def test_the_rules_say_it(self):
        self.assertIn("Things left on the ground are soon lost", build_prompt(self.e, self.p))


if __name__ == "__main__":
    unittest.main()
