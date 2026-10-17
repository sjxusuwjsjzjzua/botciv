"""Towns, WP0 (docs/towns_spec.md §3, §12.1): the data model and the interfaces the rest is built against. A world
without towns is as it was; a towns world saves and loads its settlements, plots and positions in metres."""
import json
import unittest

from civ.content.towns import KINDS, TOWNS, footprint, zone
from civ.content import BUILDINGS
from civ.engine import Engine
from civ.world import World, Building, Person, TILE_M
from civ import towns


def small(fmt=None):
    cfg = {"seed": 7, "width": 12, "height": 12}
    if fmt:
        cfg["format"] = fmt
    w = World(cfg)
    w.terrain = ["." * 12 for _ in range(12)]
    return w


def person(w, x, y, people="river"):
    p = Person(id=w.new_id(), name=f"p{x}{y}", x=x, y=y, born=0, lifespan=9999, people=people)
    w.people[p.id] = p
    w.place(p, x, y)
    return p


class Model(unittest.TestCase):
    def test_every_kind_has_a_size_and_zone(self):
        for k in BUILDINGS:
            self.assertIn(k, KINDS, k)
        for people in TOWNS:
            self.assertEqual(len(footprint("house", people)), 2)
        self.assertEqual(zone("kiln"), "edge")
        self.assertIsNone(footprint("road"))

    def test_without_towns_saves_are_as_before(self):
        w = small()
        p = person(w, 3, 3)
        b = Building(id=w.new_id(), kind="store", x=3, y=3, owner=p.id)
        w.place_building(b)
        d = w.to_dict()
        for k in ("pos", "inside"):
            self.assertNotIn(k, d["people"][str(p.id)])
        for k in ("pos", "angle", "size", "door", "site", "plot", "ruin", "style"):
            self.assertNotIn(k, d["buildings"][str(b.id)])
        self.assertNotIn("sites", d)
        self.assertFalse(w.towns)
        self.assertIs(w.building_at(3, 3), b)
        e = Engine(w)
        e.place_in(p, b)
        self.assertIsNone(p.pos)                    # nothing in metres without towns

    def test_found_place_save_load(self):
        w = small("towns1")
        self.assertTrue(w.towns)
        p = person(w, 5, 5)
        site = towns.found(w, 5, 5, "river", by=p.id, name="Elmere")
        self.assertEqual(site.form, "street")
        self.assertEqual(towns.found(w, 6, 6, "river"), "too near another settlement")
        spots = []
        for kind in ("house", "store"):
            q = person(w, 5, 5)
            pl = towns.place(w, q, kind)
            b = Building(id=w.new_id(), kind=kind, x=0, y=0, owner=q.id, **pl)
            w.place_building(b)
            self.assertEqual((b.x, b.y), (5, 5))
            spots.append(b)
        # many on one tile: building_at has no single answer, buildings_at has them all
        self.assertIsNone(w.building_at(5, 5))
        self.assertEqual({b.id for b in w.buildings_at(5, 5)}, {b.id for b in spots})
        a, b = spots
        self.assertGreater(w.cdist(a, b), 0)
        self.assertLess(w.cdist(a, b), TILE_M)
        e = Engine(w)
        e.place_in(p, a)
        self.assertEqual(p.pos, a.door)
        e.place_in(p, a, inside=True)
        self.assertEqual(p.inside, a.id)
        # round trip, through JSON as the runner saves
        w2 = World.from_dict(json.loads(json.dumps(w.to_dict())))
        self.assertEqual(w2.sites[site.id].name, "Elmere")
        self.assertEqual(w2.sites[site.id].plots, w.sites[site.id].plots)
        self.assertEqual(w2.site_of(5, 5).id, site.id)
        self.assertEqual({b.id for b in w2.buildings_at(5, 5)}, {b.id for b in spots})
        self.assertEqual(w2.buildings[a.id].pos, a.pos)
        self.assertEqual(w2.people[p.id].inside, a.id)
        # removing one leaves the other
        w2.remove_building(a.id)
        self.assertEqual([x.id for x in w2.buildings_at(5, 5)], [b.id])

    def test_close_counts_cells_in_a_settlement(self):
        w = small("towns1")
        towns.found(w, 5, 5, "river")
        a, b, c = person(w, 5, 5), person(w, 5, 5), person(w, 6, 5)
        a.pos, b.pos = [5500, 5500], [5500 + 200, 5500]
        self.assertNotIn(b.id, [q.id for q in w.close(a, 25)])        # 200 m apart in the village: not together
        b.pos = [5520, 5500]
        self.assertIn(b.id, [q.id for q in w.close(a, 25)])
        self.assertIn(c.id, [q.id for q in w.close(a, 25)])           # the next tile: land scale, as ever


if __name__ == "__main__":
    unittest.main()
