"""Phase 1.3 (docs/grand.md): the engine's tile indexes and spatial lookups give exactly what the plain scans gave."""
import random
import unittest

from civ.content import BUILDINGS
from civ.engine import Engine
from civ.gen import generate
from civ.minds.bot import BotMind
from civ.world import World, Building, key, dist


class TileIndex(unittest.TestCase):
    def setUp(self):
        self.w = generate({"seed": 5, "people": 40, "width": 48, "height": 48, "bands": 3, "ai": 0})
        self.e = Engine(self.w)

    def test_flat_lists_follow_every_write(self):
        w = self.w
        w.at[key(3, 4)] = 77
        self.assertEqual(w.at.flat[4 * w.w + 3], 77)
        del w.at[key(3, 4)]
        self.assertIsNone(w.at.flat[4 * w.w + 3])
        d = w.deposits.setdefault(key(5, 6), {"kind": "clay", "left": 3, "size": 3})
        self.assertIs(w.deposit_at(5, 6), d)
        self.assertIs(w.deposits.pop(key(5, 6)), d)
        self.assertIsNone(w.deposit_at(5, 6))
        w.roads.add(key(1, 1))
        self.assertTrue(w.roads.flat[w.w + 1])
        w.roads.discard(key(1, 1))
        self.assertFalse(w.roads.flat[w.w + 1])

    def test_saved_and_loaded_the_indexes_are_rebuilt(self):
        self.w.roads.add(key(2, 2))
        w2 = World.from_dict(self.w.to_dict())
        for y in range(w2.h):
            for x in range(w2.w):
                self.assertEqual(w2.building_at(x, y), self.w.building_at(x, y))
                self.assertEqual(w2.deposit_at(x, y), self.w.deposits.get(key(x, y)))
                self.assertEqual(w2.cost(x, y), self.w.cost(x, y))

    def test_owned_follows_changes_of_hands(self):
        w = self.w
        a, b = w.living()[:2]
        bd = Building(id=w.new_id(), kind="store", x=10, y=10, owner=a.id, done=True)
        w.buildings[bd.id] = bd
        self.assertIn(bd, w.owned(a.id))
        bd.owner = b.id
        self.assertNotIn(bd, w.owned(a.id))
        self.assertIn(bd, w.owned(b.id))
        del w.buildings[bd.id]
        self.assertNotIn(bd, w.owned(b.id))

    def test_building_near_is_what_scanning_every_building_finds(self):
        w, e = self.w, self.e
        mind = BotMind(e)
        for _ in range(12 * 40):                    # a season of bots: buildings, stores, fields, fires
            e.tick(mind.decide)
        rng = random.Random(1)
        tests = [lambda b: "store" in BUILDINGS[b.kind]["roles"], lambda b: "hearth" in BUILDINGS[b.kind]["roles"],
                 lambda b: True, lambda b: "farm" in BUILDINGS[b.kind]["roles"]]

        def scan(p, test, r, usable):
            cands = [b for b in w.buildings.values() if b.done and test(b) and (not usable or w.may_use(p, b))
                     and (dist(p.x, p.y, b.x, b.y) <= r or key(b.x, b.y) in p.known or b.owner == p.id)]
            return min(cands, key=lambda b: dist(p.x, p.y, b.x, b.y)) if cands else None
        n = 0
        for p in w.living():
            for test in tests:
                r = rng.choice([None, 5, 20])
                usable = rng.random() < 0.7
                self.assertIs(e.building_near(p, test, r=r, usable=usable), scan(p, test, r or e.sight(p), usable))
                n += 1
        self.assertGreater(n, 100)
        self.assertTrue(w.buildings)


if __name__ == "__main__":
    unittest.main()
