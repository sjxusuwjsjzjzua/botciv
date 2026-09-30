"""Rules w38: long lives with ageing, easier food, and clothes that are worn and seen.

People are grown at 14 and live past sixty (a year is 40 days); from 45 they carry less, from 55
their bodies hold less health and heal slower. A world saved under older rules keeps each
person's place in life. Clothes are worn by carrying them, one of each kind; warmth adds up."""
import json
import unittest

from botciv import config, items as I
from botciv.engine import Engine
from botciv.log import NullLog
from botciv.prompt import build_prompt
from botciv.world import World
from tests.test_engine import world, place


def years(w, y):
    return int(y * w.ticks_per_year())


class LongLives(unittest.TestCase):
    def setUp(self):
        self.w = world(1)
        self.e = Engine(self.w, NullLog())
        self.a, self.b = self.w.living()[:2]

    def test_new_people_are_grown_and_young(self):
        for a in self.w.living():
            self.assertGreaterEqual(a.years(self.w.cfg), 16)
            self.assertLess(a.years(self.w.cfg), 39)
            self.assertGreaterEqual(a.lifespan, years(self.w, 60))

    def test_age_weakens_slowly(self):
        a, cfg = self.a, self.w.cfg
        a.inventory = {}
        a.age = years(self.w, 30)
        self.assertEqual(a.capacity(cfg), cfg["agent"]["capacity"])
        self.assertEqual(a.max_health(cfg), 10)
        a.age = years(self.w, 55)
        self.assertLess(a.capacity(cfg), cfg["agent"]["capacity"])
        a.age = years(self.w, 70)
        self.assertLessEqual(a.max_health(cfg), 7)
        self.assertGreaterEqual(a.max_health(cfg), 4)
        a.age = years(self.w, 5)
        self.assertLess(a.capacity(cfg), cfg["agent"]["capacity"] * 0.7)

    def test_nobody_dies_of_age_young(self):
        a = self.a
        a.age = years(self.w, 59)
        for _ in range(24):
            self.e.needs()
        self.assertTrue(a.alive)

    def test_the_old_lose_health_they_cannot_hold(self):
        a = self.a
        a.age = years(self.w, 75)
        a.health = 10
        self.e.needs()
        self.assertLessEqual(a.health, a.max_health(self.w.cfg))

    def test_prompt_tells_the_age_and_what_it_does(self):
        self.a.age = years(self.w, 58)
        text = build_prompt(self.e, self.a)
        self.assertIn("You are 58 years old (old:", text)
        self.assertIn(f"/{self.a.max_health(self.w.cfg)})", text)


class OldWorlds(unittest.TestCase):
    def old_world(self):
        w = world(3)
        d = w.to_dict()
        d["cfg"].pop("era")
        d["cfg"]["agent"].update(adult_ticks=240, lifespan_years=[3.0, 5.5], hunger_every=3, starve_every=3)
        tpy = w.ticks_per_year()
        ags = list(d["agents"].values())
        ags[0].update(age=120, lifespan=int(4 * tpy))                          # a child, half grown
        ags[1].update(age=int(3.9 * tpy), lifespan=int(4 * tpy))               # near the old end
        ags[2].update(age=300, lifespan=int(5 * tpy))                          # just grown
        return d

    def test_an_old_world_takes_the_new_rules_and_ages(self):
        d = self.old_world()
        w = World.from_dict(json.loads(json.dumps(d)))
        self.assertEqual(w.cfg["era"], config.ERA)
        self.assertEqual(w.cfg["agent"]["hunger_every"], 4)
        a0, a1, a2 = [w.agents[int(k)] for k in list(d["agents"])[:3]]
        y = lambda a: a.years(w.cfg)
        self.assertAlmostEqual(y(a0), 7, delta=0.5)
        self.assertGreater(y(a1), 50)
        self.assertLess(y(a2), 20)
        self.assertGreaterEqual(y(a2), 16)
        for a in (a0, a1, a2):
            self.assertGreater(a.lifespan, a.age)
            self.assertEqual(a.born, w.tick - a.age)
        self.assertIn("tunic", w.recipes.values())
        # and a world saved under these rules is not moved again
        again = World.from_dict(json.loads(json.dumps(w.to_dict())))
        self.assertEqual(again.agents[a1.id].age, a1.age)


class Clothes(unittest.TestCase):
    def setUp(self):
        self.w = world(1)
        self.e = Engine(self.w, NullLog())
        self.a, self.b = self.w.living()[:2]

    def test_worn_and_warmth(self):
        inv = {"cloak": 2, "hat": 1, "berries": 3}
        self.assertEqual(I.worn(inv), ["hat", "cloak"])
        self.assertEqual(I.warmth(inv), 3)

    def test_every_garment_can_be_made(self):
        for k in ("tunic", "shoes", "hat", "bracelet", "cloak"):
            self.assertIn(k, self.w.recipes.values())

    def test_warm_enough_is_never_bitten(self):
        a = self.a
        a.inventory = {"cloak": 1, "shoes": 1}
        a.health = 10
        a.satiety = 20
        while not (self.w.season() == "winter" and self.w.is_night()):
            self.w.tick += 1
        for _ in range(30):
            self.e.needs()
            a.satiety = 20
        self.assertEqual(a.health, 10)
        self.assertGreater(a.wear.get("cloak", 0), 0)

    def test_others_see_what_you_wear(self):
        place(self.w, self.a, 3, 3)
        place(self.w, self.b, 3, 4)
        self.b.inventory = {"hat": 1, "tunic": 1}
        self.e.perceive()
        text = build_prompt(self.e, self.a)
        self.assertIn("wears hat, tunic", text)
        self.a.inventory = {"shoes": 1}
        self.assertIn("You wear: shoes (warmth 1)", build_prompt(self.e, self.a))


if __name__ == "__main__":
    unittest.main()
