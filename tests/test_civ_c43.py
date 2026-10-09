"""c43: what the dead leave can be claimed and falls to ruin; game comes back to a crowded land; a cloak
of plaited fibre; refusals said back when repeated; couples seek a home of their own."""
import unittest

from civ.content import BUILDINGS
from civ.engine import Engine
from civ.gen import generate
from civ.minds.bot import BotMind
from civ.prompt import build_prompt
from civ.world import Building, TPD


def small(people=30, seed=4):
    return generate({"seed": seed, "people": people, "width": 44, "height": 44, "bands": 3, "ai": 0})


def place(w, kind, owner, near):
    x, y = next((x, y) for x, y in w.beside(near.x, near.y, 3)
                if w.passable(x, y) and not w.building_at(x, y) and (x, y) != (near.x, near.y))
    b = Building(id=w.new_id(), kind=kind, x=x, y=y, owner=owner, done=True, hp=BUILDINGS[kind]["hp"])
    w.buildings[b.id] = b
    w.at[f"{x},{y}"] = b.id
    return b


class C43(unittest.TestCase):
    def setUp(self):
        self.w = small()
        self.e = Engine(self.w)
        self.p, self.dead = self.w.living()[0], self.w.living()[1]

    def test_the_dead_leave_an_empty_shelter_that_can_be_claimed(self):
        w, e, p = self.w, self.e, self.p
        b = place(w, "shelter", self.dead.id, p)
        self.assertFalse(w.empty(b))
        self.dead.alive = False
        self.assertTrue(w.empty(b))
        self.assertIn("claim it", build_prompt(e, p))
        ok, why = e.start(p, {"do": "claim", "x": b.x, "y": b.y})
        self.assertTrue(ok, why)
        for _ in range(20):
            if not p.act:
                break
            e.tick(lambda people: {})
        self.assertEqual(b.owner, p.id)
        self.assertEqual(p.home, b.id)
        self.assertFalse(w.empty(b))

    def test_a_living_owners_building_cannot_be_claimed(self):
        b = place(self.w, "shelter", self.dead.id, self.p)
        ok, why = self.e.start(self.p, {"do": "claim", "x": b.x, "y": b.y})
        self.assertFalse(ok)
        self.assertIn("not empty", why)

    def test_empty_buildings_fall_to_ruin_and_free_the_place(self):
        w, e = self.w, self.e
        b = place(w, "shelter", self.dead.id, self.p)
        b.inv = {"wood": 3}
        monument = place(w, "cairn", self.dead.id, self.p)
        self.dead.alive = False
        for _ in range(12):
            e.ruin()
        self.assertNotIn(b.id, w.buildings)
        self.assertIsNone(w.building_at(b.x, b.y))
        self.assertEqual(w.piles.get(f"{b.x},{b.y}", {}).get("wood"), 3)
        self.assertIn(monument.id, w.buildings)          # a monument keeps its maker's name

    def test_game_comes_back_to_a_land_full_of_people(self):
        w, e = self.w, self.e
        w.herds = []
        w.tick = TPD * 5
        got = []
        for i in range(10):
            w.tick = TPD * 5 * (i + 1)
            got += e.new_herds()
        self.assertTrue(got)
        for h in got:
            self.assertFalse(w.near(h["x"], h["y"], 5))

    def test_a_cloak_can_be_plaited_from_fibre(self):
        from civ.content.crafts import recipes_making
        self.assertTrue(any(set(r["ins"]) == {"fibre", "rope"} for r in recipes_making("cloak")))
        self.assertTrue(any(set(r["ins"]) == {"fibre"} for r in recipes_making("tunic")))

    def test_repeated_refusals_are_said_back(self):
        e, p = self.e, self.p
        e.refused[p.id] = [(self.w.tick, {"do": "hunt", "animal": "deer"}, "you know of no deer nearby: the game around here is hunted out")] * 3
        text = build_prompt(e, p)
        self.assertIn("Tried more than once lately", text)
        self.assertIn("hunt (3 times)", text)

    def test_a_couple_in_a_parents_house_seeks_its_own(self):
        from civ.world import TPY
        w, e = self.w, self.e
        m = BotMind(e)
        a, b, parent = [q for q in w.living() if q.adult(w.tick)][:3]
        a.partner, b.partner = b.id, a.id
        a.born = b.born = w.tick - 25 * TPY
        h = place(w, "shelter", parent.id, a)
        b.home = a.home = h.id
        self.assertFalse(m.has_home(a))
        got = m.home_goal(a)            # it used to settle for the partner's (here a parent's) home
        self.assertIsNotNone(got)
        self.assertEqual(got["goal"], "a home")
    def test_the_dead_leave_their_groups_and_an_empty_group_ends(self):
        from civ.world import Group
        w, e, p, d = self.w, self.e, self.p, self.dead
        g = Group(id=w.new_id(), name="Hearth", founder=d.id, leader=d.id, members=[d.id, p.id])
        w.groups[g.id] = g
        d.groups.append(g.id)
        p.groups.append(g.id)
        st = place(w, "store", -g.id, p)
        e.die(d, "died of old age")
        self.assertEqual(g.members, [p.id])
        self.assertEqual(g.leader, p.id)
        e.die(p, "died of old age")
        self.assertIsNotNone(g.dissolved)
        self.assertTrue(w.empty(st))          # the ended group's store can be claimed

    def test_beasts_can_be_given_from_pen_to_pen(self):
        w, e, p = self.w, self.e, self.p
        o = self.dead                       # alive here: a neighbour
        w.tick = 5                          # off a season's start: no spring births in the middle of it
        mine = place(w, "pen", p.id, p)
        mine.animals = {"goat": 6}
        theirs = place(w, "pen", o.id, p)
        o.x, o.y = p.x, p.y + 1 if w.passable(p.x, p.y + 1) else p.y
        ok, why = e.start(p, {"do": "give", "to": o.name, "item": "goat", "n": 2})
        self.assertTrue(ok, why)
        for _ in range(10):
            if not p.act:
                break
            e.tick(lambda people: {})
        self.assertEqual(mine.animals["goat"], 4)
        self.assertEqual(theirs.animals["goat"], 2)
        ok, why = e.start(p, {"do": "give", "to": o.name, "item": "sheep"})
        self.assertFalse(ok)
        self.assertIn("keep no sheep", why)

    def test_gathering_a_food_that_is_not_there_gathers_one_that_is(self):
        w, e, p = self.w, self.e, self.p
        if not e.find(p, "berries") and not e.find(p, "nuts"):
            self.skipTest("no berries or nuts near this person in this land")
        ok, why = e.start(p, {"do": "gather", "item": "honey"})
        if e.find(p, "honey", far=False):
            self.skipTest("honey is here after all")
        self.assertTrue(ok, why)
        self.assertIn(p.act["item"], {"berries", "nuts", "grain"})
        self.assertTrue(any("instead" in t for _, t in p.events[-2:]))

    def test_a_full_load_is_set_down_in_ones_own_store_first(self):
        w, e, p = self.w, self.e, self.p
        w.tick = 5
        st = place(w, "store", p.id, p)
        st.inv = {"stone": 6}
        p.inv = {"wood": int(p.capacity(w.tick) / 1.0) + 5}
        from civ.content import items as I
        while self.e.room(p, "stone") >= 1:
            p.inv["wood"] += 5
        p.intent = {"goal": "", "plan": []}
        ok, why = e.start(p, {"do": "take", "item": "stone", "n": 4, "x": st.x, "y": st.y})
        self.assertTrue(ok, why)
        self.assertEqual(p.act["do"], "put")
        self.assertEqual(p.intent["plan"][0]["do"], "take")
        for _ in range(30):
            if not p.act and p.intent["plan"]:
                step = p.intent["plan"].pop(0)
                e.start(p, step)
            if not p.act and not p.intent["plan"]:
                break
            e.tick(lambda people: {})
        self.assertGreater(st.inv.get("wood", 0), 0)
        self.assertGreater(p.inv.get("stone", 0), 0)

    def test_a_craft_makes_the_part_it_lacks_first(self):
        # c48: a cloak of fibre takes a rope; with only fibre in hand, the rope is made first
        w, e, p = self.w, self.e, self.p
        w.tick = 5
        p.skills["cordage"] = 0.9
        p.inv = {"fibre": 6}
        p.intent = {"goal": "", "plan": []}
        ok, why = e.start(p, {"do": "craft", "item": "cloak"})
        self.assertTrue(ok, why)
        for _ in range(300):
            if not p.act:
                if not p.intent["plan"]:
                    break
                e.start(p, p.intent["plan"].pop(0))
            e.tick(lambda people: {})
        self.assertEqual(p.inv.get("cloak"), 1)

    def test_writing_fetches_a_tablet_from_ones_store(self):
        w, e, p = self.w, self.e, self.p
        p.skills["writing"] = 0.5
        p.intent = {"goal": "", "plan": []}
        ok, why = e.start(p, {"do": "write", "text": "Grain owed to Thor: 4"})
        self.assertFalse(ok)
        self.assertIn("pressed by hand", why)
        st = place(w, "store", p.id, p)
        st.inv = {"tablet": 2}
        ok, why = e.start(p, {"do": "write", "text": "Grain owed to Thor: 4"})
        self.assertTrue(ok, why)
        self.assertEqual(p.act["do"], "take")
        self.assertEqual(p.intent["plan"][0]["do"], "write")

    def test_leaders_name_the_place_their_people_live(self):
        from civ.gen import generate
        from civ.world import TPY
        w = generate({"seed": 2, "people": 120, "width": 80, "height": 80, "bands": 7})
        e = Engine(w)
        m = BotMind(e)
        for _ in range(int(2.5 * TPY)):                 # the first naming falls between 0.8 and 2 years by seed and Python
            e.tick(m.decide)
        self.assertTrue(w.places, "no place named in two and a half years")
        names = [pl[2] for pl in w.places]
        self.assertEqual(len(names), len(set(names)))
        for a in w.places:          # no two within 8 steps of each other
            self.assertFalse(any(b is not a and abs(a[0] - b[0]) <= 8 and abs(a[1] - b[1]) <= 8 for b in w.places), names)

    def test_a_theft_unseen_is_known_only_by_a_tally(self):
        from civ.world import TPD
        w, e, thief, owner = self.w, self.e, self.p, self.dead
        st = place(w, "store", owner.id, thief)
        st.inv = {"grain": 10}
        owner.x, owner.y = (thief.x + 20) % w.w, thief.y          # far off
        for o in w.living():                                        # and no one else near
            if o.id not in (thief.id, owner.id) and abs(o.x - st.x) <= 6 and abs(o.y - st.y) <= 6:
                o.x, o.y = (st.x + 25) % w.w, (st.y + 25) % w.h
        w.tick = TPD - 1                                            # night
        def steal():
            ok, why = e.start(thief, {"do": "take", "item": "grain", "n": 2, "x": st.x, "y": st.y})
            self.assertTrue(ok, why)
            for _ in range(10):
                if not thief.act:
                    break
                e.tick(lambda people: {})
        steal()
        self.assertTrue(any("you do not know who" in t for _, t in owner.events[-3:]))
        self.assertIsNone(e.wrong_known(owner, thief))
        st.inv["tablet:1"] = 1                                      # a tally kept in the store
        w.tick = 2 * TPD - 1
        steal()
        self.assertTrue(any(thief.name in t and "tally" in t for _, t in owner.events[-3:]))
        self.assertIsNotNone(e.wrong_known(owner, thief))


if __name__ == "__main__":
    unittest.main()
