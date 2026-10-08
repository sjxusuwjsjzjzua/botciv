"""c54: a pen holds at most three days of milk (one once held 7,368); a law given again is not listed
twice, and a tablet in hand writes down the spoken one; a thing posted again keeps one price; the account of
what happened says things put away one after another on one line."""
import unittest

from civ.content import BUILDINGS
from civ.engine import Engine
from civ.gen import generate
from civ.prompt import compact_events
from civ.world import Building, Group


def small(seed=4):
    return generate({"seed": seed, "people": 12, "width": 40, "height": 40, "bands": 2, "ai": 0})


def place(w, kind, owner, near):
    x, y = next((x, y) for x, y in w.beside(near.x, near.y, 3)
                if w.passable(x, y) and not w.building_at(x, y) and (x, y) != (near.x, near.y))
    b = Building(id=w.new_id(), kind=kind, x=x, y=y, owner=owner, done=True, hp=BUILDINGS[kind]["hp"])
    w.buildings[b.id] = b
    w.at[f"{x},{y}"] = b.id
    return b


class C54(unittest.TestCase):
    def setUp(self):
        self.w = small()
        self.e = Engine(self.w)
        self.p, self.o = self.w.living()[:2]
        self.p.act = self.o.act = None

    def test_milk_in_a_pen_has_a_bound(self):
        pen = place(self.w, "pen", self.p.id, self.p)
        pen.animals = {"cattle": 2}
        for _ in range(10):
            self.e.pens_day()
        self.assertLessEqual(pen.inv.get("milk", 0), 3 * 4 * 2)

    def test_a_law_once(self):
        w, e, p = self.w, self.e, self.p
        g = Group(id=w.new_id(), name="Oakfolk", founder=p.id, leader=p.id, members=[p.id, self.o.id], founded=w.tick)
        w.groups[g.id] = g
        p.groups.append(g.id)
        self.assertTrue(e.start(p, {"do": "make_law", "group": "Oakfolk", "text": "Share food."})[0])
        ok, why = e.start(p, {"do": "make_law", "group": "Oakfolk", "text": "share food."})
        self.assertFalse(ok)
        self.assertIn("already", why)
        p.inv["tablet"] = 1
        self.assertTrue(e.start(p, {"do": "make_law", "group": "Oakfolk", "text": "Share food."})[0])
        self.assertEqual([(l[1], l[2]) for l in g.laws], [("Share food.", True)])

    def test_one_price_for_a_thing(self):
        st = place(self.w, "store", self.p.id, self.p)
        st.inv = {"plank": 5}
        for price in (2, 3):
            self.e.post_at(self.p, st, {"plank": 1}, {"grain": price})
        self.assertEqual(len(st.trade), 1)

    def test_things_put_away_on_one_line(self):
        ev = [(1, "You put 6 fibre into the store."), (2, "You put 3 seeds into the store."),
              (3, "You took 2 grain from the store.")]
        self.assertEqual([t for _, t in compact_events(ev, "Me")],
                         ["You put 6 fibre, 3 seeds into the store.", "You took 2 grain from the store."])


if __name__ == "__main__":
    unittest.main()


class C57(unittest.TestCase):
    """c57, from the long land (year 319): old milk hoards turn; game comes back to a crowded land."""
    def test_an_old_hoard_of_milk_turns(self):
        w = small()
        e = Engine(w)
        p = w.living()[0]
        pen = place(w, "pen", p.id, p)
        pen.inv["milk"] = 50000                  # no beasts left: none of it can be fresh
        e.pens_day()
        self.assertEqual(pen.inv.get("milk", 0), 0)

    def test_game_comes_back_to_a_crowded_land(self):
        w = generate({"seed": 3, "people": 300, "width": 40, "height": 40, "bands": 12, "ai": 0})
        e = Engine(w)
        w.herds = []
        got = []
        for d in range(40):
            w.tick = (d + 1) * 5 * 12
            got += e.new_herds()
        self.assertGreater(len(got), 0)
        for h in got:
            self.assertFalse(w.near(h["x"], h["y"], 2))
