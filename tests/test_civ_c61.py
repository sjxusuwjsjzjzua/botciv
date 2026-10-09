"""c61 (C5): the learned buildings do what they promise. Writing tablets as a good writer teaches reading and
writing at length (literacy had no way in: only those who had it could practise it); a lesson at a school reaches
all who sit there; a mill grinds grain into flour; an aqueduct waters the fields about it; one sees further from a
tower. Bots keep records, raise schools and teach there; children sit at a school near by."""
import unittest

from civ.content import BUILDINGS
from civ.engine import Engine
from civ.gen import generate
from civ.world import Building, TPD


def place(w, kind, owner, near, r=3, at=None):
    x, y = at or next((x, y) for x, y in w.beside(near.x, near.y, r)
                      if w.passable(x, y) and not w.building_at(x, y) and (x, y) != (near.x, near.y))
    b = Building(id=w.new_id(), kind=kind, x=x, y=y, owner=owner, done=True, hp=BUILDINGS[kind]["hp"])
    w.buildings[b.id] = b
    w.at[f"{x},{y}"] = b.id
    return b


class C61(unittest.TestCase):
    def setUp(self):
        self.w = generate({"seed": 4, "people": 16, "width": 40, "height": 40, "bands": 2, "ai": 0})
        self.e = Engine(self.w)
        self.ps = [q for q in self.w.living() if q.adult(self.w.tick)]
        for q in self.w.living():
            q.act, q.intent = None, {"goal": "", "plan": []}
        self.p = self.ps[0]

    def test_a_good_writer_comes_to_read(self):
        p = self.p
        p.skills["writing"] = 0.6
        for _ in range(4):
            p.inv["tablet"] = 1
            self.assertIs(self.e.start(p, {"do": "write", "text": "Grain 4."})[0], True)
        self.assertGreater(p.skill("literacy"), 0.1)

    def test_a_lesson_at_a_school_reaches_all_who_sit_there(self):
        w, e, p = self.w, self.e, self.p
        school = place(w, "school", p.id, p)
        w.place(p, school.x, school.y)
        p.skills["pottery"] = 0.9
        learners = self.ps[1:5]
        for q in learners:
            w.place(q, school.x, school.y)
            q.skills.pop("pottery", None)
        self.assertIs(e.start(p, {"do": "teach", "to": learners[0].name, "craft": "pottery"})[0], True)
        for _ in range(5):
            if p.act:
                st, msg = e.do_teach(p, p.act)
                if st == "done":
                    break
        self.assertTrue(all(q.skill("pottery") >= 0.5 for q in learners), [q.skill("pottery") for q in learners])

    def test_a_mill_grinds_grain(self):
        mill = place(self.w, "mill", self.p.id, self.p)
        mill.inv = {"grain": 50}
        self.e.mills_day()
        self.assertEqual(mill.inv, {"grain": 10, "flour": 40})

    def test_an_aqueduct_waters_the_fields(self):
        w, e, p = self.w, self.e, self.p
        yields = []
        farm = place(w, "farm", p.id, p)
        for aq in (False, True):
            farm.crop = None
            if aq:
                place(w, "aqueduct", p.id, farm, r=2)
            w.place(p, farm.x, farm.y)
            p.inv["seeds"] = 4
            self.assertIs(e.start(p, {"do": "plant", "item": "seeds", "x": farm.x, "y": farm.y})[0], True)
            while p.act:
                st, _ = e.do_plant(p, p.act)
                if st != "go":
                    p.act = None
            yields.append(farm.crop["yield"])
        self.assertGreater(yields[1], yields[0])

    def test_one_sees_further_from_a_tower(self):
        w, e, p = self.w, self.e, self.p
        while w.is_night():
            w.tick += 1
        before = e.sight(p)
        place(w, "tower", p.id, p, at=(p.x, p.y))
        self.assertGreater(e.sight(p), before)

    def test_a_place_is_not_named_the_same_twice(self):
        self.assertIs(self.e.start(self.p, {"do": "name_place", "name": "Stoush's Rest"})[0], True)
        ok, why = self.e.start(self.p, {"do": "name_place", "name": "stoush's rest"})
        self.assertFalse(ok)
        self.assertEqual(len(self.w.places), 1)

    def test_a_build_waits_for_its_bricks_and_fetches_them(self):
        from civ.plan import Planner
        w, e, p = self.w, self.e, self.p
        p.skills.update({"pottery": 1.0, "charcoal_burning": 0.5})          # a firing that never cracks
        place(w, "kiln", p.id, p)
        st = place(w, "store", p.id, p)
        st.inv = {"stone": 6}
        p.inv.update({"clay": 12, "wood": 6})
        e.adopt(p, {"goal": "a furnace", "plan": Planner(e).build(p, "furnace")})
        for _ in range(TPD * 3):
            e.tick(lambda ps: {})
            p.satiety = 15
            if any(b.kind == "furnace" and b.done for b in w.buildings.values()):
                break
        self.assertTrue(any(b.kind == "furnace" for b in w.buildings.values()), [t for _, t in p.events[-8:]])

    def test_a_hunter_in_a_hunted_out_land_sets_out_for_the_game(self):
        w, e, p = self.w, self.e, self.p
        w.herds = [h for h in w.herds if h["kind"] == "deer"][:1]
        h = w.herds[0]
        x0, y0 = next((x, y) for y in range(w.h) for x in range(6) if w.passable(x, y) and w.passable(x + 27, y))
        w.place(p, x0, y0)
        h["n"], h["x"], h["y"] = 5, x0 + 27, y0                     # beyond a hunt's cast (20), within a trip (30)
        ok = e.start(p, {"do": "hunt", "animal": "deer"})[0]
        self.assertIs(ok, True)
        self.assertEqual(p.act["do"], "go")
        self.assertEqual(p.intent["plan"][0]["do"], "hunt")

    def test_only_readers_are_shown_books(self):
        from civ.prompt import build_prompt
        self.p.skills["writing"] = 0.6
        self.assertNotIn("- study:", build_prompt(self.e, self.p))
        self.p.skills["literacy"] = 0.4
        self.assertIn("- study:", build_prompt(self.e, self.p))


if __name__ == "__main__":
    unittest.main()
