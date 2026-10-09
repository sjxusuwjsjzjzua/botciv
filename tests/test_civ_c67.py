"""c67 (grand world, Phase 2): a land of difference. A continent of regions, peoples in their homelands with their
own tongues, ways and lifeways; speech in a tongue one does not know is heard but not followed (unless someone
beside puts it into one's tongue); what members of a people do colours what one thinks of all of them, and a
stranger is met with it; onlookers judge by their own people's customs; each region has its year."""
import unittest

from civ.content.peoples import PEOPLES
from civ.engine import Engine
from civ.prompt import build_prompt
from civ.realm import generate
from civ.world import World, Building, key, TPD


class C67(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = generate({"seed": 2, "width": 96, "height": 96, "people": 300})

    def setUp(self):
        self.w = World.from_dict(self.base.to_dict())
        self.e = Engine(self.w)

    def two_peoples(self):
        ks = list(self.w.peoples)
        a = next(p for p in self.w.living() if p.people == ks[0] and p.adult(self.w.tick))
        b = next(p for p in self.w.living() if p.people == ks[1] and p.adult(self.w.tick))
        return a, b

    def test_a_continent_of_peoples_that_saves_and_loads(self):
        w = self.w
        self.assertGreaterEqual(len(w.peoples), 3)
        kinds = {r["kind"] for r in w.regions}
        self.assertGreaterEqual(len(kinds), 3)
        for k, v in w.peoples.items():
            ps = [p for p in w.living() if p.people == k]
            self.assertTrue(ps, k)
            self.assertTrue(all(p.skill(f"tongue:{k}") == 1.0 for p in ps))
            home = w.regions[v["region"]]
            self.assertEqual(home["kind"], PEOPLES[k]["homeland"])
        p = w.living()[0]
        self.assertEqual(w.region_at(p.x, p.y), self.base.region_at(p.x, p.y))
        self.assertEqual(w.region_of, self.base.region_of)

    def test_a_strange_tongue_is_heard_not_followed_unless_put_into_ones_own(self):
        a, b = self.two_peoples()
        self.w.place(b, a.x, a.y)
        b.events = []
        self.e.speak(a, "Give me your grain.", to=b.name)
        self.assertIn("you catch none of it", b.events[-1][1])
        self.assertNotIn(b.id, self.e.heard)
        # someone beside who knows both tongues puts it into b's
        c = next(p for p in self.w.living() if p.people == a.people and p.id != a.id and p.adult(self.w.tick))
        c.skills[f"tongue:{b.people}"] = 0.8
        self.w.place(c, a.x, a.y)
        b.events = []
        self.e.speak(a, "Give me your grain.", to=b.name)
        self.assertIn("puts it into your tongue", b.events[-1][1])
        # one who knows the other's tongue speaks it to them
        a.skills[f"tongue:{b.people}"] = 0.6
        self.w.place(c, 0, 0)
        b.events = []
        self.e.speak(a, "Well met.", to=b.name)
        self.assertIn('"Well met."', b.events[-1][1])

    def test_what_one_of_a_people_does_colours_all_of_them(self):
        a, b = self.two_peoples()
        self.e.trust(a, b, -0.6, ("attacked", f"{b.name} attacked you"))
        self.assertLess(a.feel[b.people], 0)
        stranger = next(p for p in self.w.living() if p.people == b.people and p.id != b.id and str(p.id) not in a.rel)
        self.assertLess(self.e.rel(a, stranger)["trust"], 0)
        a.feel[b.people] = -0.7
        text = build_prompt(self.e, a)
        self.assertIn("What you think of other peoples", text)
        self.assertIn("You are of the", text)

    def test_onlookers_judge_by_their_own_customs(self):
        honour = next(k for k in self.w.peoples if PEOPLES[k]["customs"]["raid_honour"]) if any(
            PEOPLES[k]["customs"]["raid_honour"] for k in self.w.peoples) else None
        if not honour:
            self.skipTest("no raiding people in this land")
        a = next(p for p in self.w.living() if p.people == honour and p.adult(self.w.tick))
        x = next(p for p in self.w.living() if p.people == honour and p.id != a.id and p.adult(self.w.tick))
        o = next(p for p in self.w.living() if p.people != honour and p.adult(self.w.tick))
        self.assertTrue(self.e.daring(x, a, o))
        self.assertFalse(self.e.daring(o, a, x))

    def test_a_hard_year_bears_little(self):
        w = self.w
        p = next(q for q in w.living() if w.region_at(q.x, q.y))
        farm = Building(id=w.new_id(), kind="farm", x=p.x, y=p.y, owner=p.id, done=True)
        w.buildings[farm.id] = farm
        r = w.region_at(farm.x, farm.y)
        w.years[str(r["id"])] = "hard"
        farm.crop = {"what": "grain", "n": 2, "sown": w.tick, "ripe_at": w.tick, "yield": 20, "by": farm.owner}
        w.tick = max(w.tick, 1)
        while w.season() == "winter":
            w.tick += TPD
        farm.crop["ripe_at"] = w.tick
        self.e.farms_day()
        self.assertEqual(farm.inv.get("grain"), 8)
        self.assertIn("a hard year here", build_prompt(self.e, p))

    def test_a_child_is_of_its_mothers_people_and_speaks_its_parents_tongues(self):
        a, b = self.two_peoples()
        a.feel[b.people] = -0.5
        a.pregnant = {"due": self.w.tick, "with": b.id, "name": ""}
        self.e.birth(a)
        c = self.w.people[max(self.w.people)]
        self.assertEqual(c.people, a.people)
        self.assertEqual(c.skill(f"tongue:{b.people}"), 1.0)
        self.assertLess(c.feel.get(b.people, 0), 0)


if __name__ == "__main__":
    unittest.main()
