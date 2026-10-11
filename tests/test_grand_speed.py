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

    def test_reachable_agrees_with_walking_and_follows_walls(self):
        w = self.w

        def walk(sx, sy, tx, ty, adjacent):
            seen, todo = {(sx, sy)}, [(sx, sy)]
            while todo:
                x, y = todo.pop()
                if (x, y) == (tx, ty) or (adjacent and dist(x, y, tx, ty) <= 1):
                    return True
                for nx in (x - 1, x, x + 1):
                    for ny in (y - 1, y, y + 1):
                        if (nx, ny) not in seen and w.cost(nx, ny) > 0:
                            seen.add((nx, ny))
                            todo.append((nx, ny))
            return False
        rng = random.Random(3)
        for _ in range(300):
            sx, sy = rng.randrange(w.w), rng.randrange(w.h)
            if w.cost(sx, sy) <= 0:
                continue
            tx, ty, adj = rng.randrange(w.w), rng.randrange(w.h), rng.random() < 0.5
            if dist(sx, sy, tx, ty) <= 1:
                continue
            self.assertEqual(w.reachable(sx, sy, tx, ty, adj), walk(sx, sy, tx, ty, adj), (sx, sy, tx, ty, adj))
        # a ring of finished walls shuts a tile in
        cx, cy = next((x, y) for y in range(5, w.h - 5) for x in range(5, w.w - 5)
                      if all(w.cost(i, j) > 0 and not w.building_at(i, j) for i, j in w.beside(x, y, 2)))
        ox, oy = cx + 2, cy + 2
        self.assertTrue(w.reachable(cx, cy, ox + 1, oy + 1))
        for i, j in w.beside(cx, cy, 1):
            if (i, j) != (cx, cy):
                b = Building(id=w.new_id(), kind="palisade", x=i, y=j, owner=0, done=False)
                w.buildings[b.id] = b
                w.at[key(i, j)] = b.id
                b.done = True
        self.assertFalse(w.reachable(cx, cy, ox + 1, oy + 1))
        self.assertIsNone(self.e.path(next(iter(w.living())), cx, cy) if w.cost(cx, cy) > 0 else None)


class Indexes(unittest.TestCase):
    """The speed gate's second round: buildings by role, the land's step costs kept, the living and tenancies kept;
    each gives what the plain scan gave."""
    @classmethod
    def setUpClass(cls):
        cls.w = generate({"seed": 7, "people": 60, "width": 48, "height": 48, "bands": 4, "ai": 0})
        cls.e = Engine(cls.w)
        mind = BotMind(cls.e)
        for _ in range(12 * 40):                    # a season of bots
            cls.e.tick(mind.decide)

    def test_role_search_is_the_plain_search(self):
        w, e = self.w, self.e
        crafts = sorted({c for B in BUILDINGS.values() for c in B["roles"].get("workshop", ())})
        rng = random.Random(2)
        n = 0
        for p in w.living():
            for craft in rng.sample(crafts, 4):
                test = (lambda c: lambda b: c in BUILDINGS[b.kind]["roles"].get("workshop", []))(craft)
                r = rng.choice([None, 5, 20])
                self.assertIs(e.building_near(p, test, r=r, role="workshop:" + craft), e.building_near(p, test, r=r))
                n += 1
            test = lambda b: "store" in BUILDINGS[b.kind]["roles"]
            self.assertIs(e.building_near(p, test, r=20, usable=False, role="store"), e.building_near(p, test, r=20, usable=False))
        self.assertGreater(n, 100)

    def test_role_index_follows_building_and_ruin(self):
        w, e = self.w, self.e
        p = w.living()[0]
        kind = next(k for k, B in BUILDINGS.items() if "workshop" in B["roles"] and not B.get("overlay"))
        craft = BUILDINGS[kind]["roles"]["workshop"][0]
        x, y = next((x, y) for x, y in w.beside(p.x, p.y, 3) if w.cost(x, y) > 0 and not w.building_at(x, y))
        b = Building(id=w.new_id(), kind=kind, x=x, y=y, owner=p.id, done=True)
        w.buildings[b.id] = b
        w.at[key(x, y)] = b.id
        test = lambda b: craft in BUILDINGS[b.kind]["roles"].get("workshop", [])
        self.assertIs(e.building_near(p, test, role="workshop:" + craft), e.building_near(p, test))
        self.assertIsNotNone(e.building_near(p, test, role="workshop:" + craft))
        del w.buildings[b.id]
        del w.at[key(x, y)]
        self.assertIs(e.building_near(p, test, role="workshop:" + craft), e.building_near(p, test))

    def test_step_costs_are_cost_and_follow_changes(self):
        w = self.w

        def same():
            sc = w.step_costs()
            for y in range(w.h):
                for x in range(w.w):
                    self.assertEqual(sc[y * w.w + x], w.cost(x, y), (x, y))
        same()
        x, y = next((x, y) for y in range(w.h) for x in range(w.w) if w.cost(x, y) > 0 and not w.building_at(x, y))
        w.trails.add(key(x, y))
        same()
        w.roads.add(key(x, y))
        same()
        b = Building(id=w.new_id(), kind="palisade", x=x, y=y, owner=0, done=False)
        w.buildings[b.id] = b
        w.at[key(x, y)] = b.id
        same()
        b.done = True
        same()
        del w.buildings[b.id]
        del w.at[key(x, y)]
        w.roads.discard(key(x, y))
        w.trails.discard(key(x, y))
        same()

    def test_living_and_tenancy_are_the_scans(self):
        w = self.w
        self.assertEqual(w.living(), [p for p in w.people.values() if p.alive])
        p = w.living()[0]
        p.alive = False                             # a death the kept list was not told of
        self.assertEqual(w.living(), [p for p in w.people.values() if p.alive])
        p.alive = True
        fields = [b for b in w.buildings.values() if b.kind == "farm"][:2] or [Building(id=w.new_id(), kind="farm", x=1, y=1, owner=p.id)]
        f = fields[0]
        w.tenancies.append({"field": f.id, "tenant": p.id, "done": True})
        self.assertIsNone(w.tenancy(f))
        w.tenancies.append({"field": f.id, "tenant": p.id, "done": False})
        self.assertIs(w.tenancy(f), w.tenancies[-1])
        w.tenancies = [t for t in w.tenancies if not t["done"]]
        self.assertIs(w.tenancy(f), w.tenancies[-1])
        w.tenancies[-1]["done"] = True
        self.assertIsNone(w.tenancy(f))
        w.tenancies = []


if __name__ == "__main__":
    unittest.main()
