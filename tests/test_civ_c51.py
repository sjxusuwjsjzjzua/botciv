"""c51 (roadmap C2): what writing is for. A promise written down stands past its day, owed to whoever
holds the writing, and is settled when the writing comes back; a law never written dies with its maker."""
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.prompt import build_prompt
from civ.world import Group, TPD


def small(people=20, seed=4):
    return generate({"seed": seed, "people": people, "width": 40, "height": 40, "bands": 2, "ai": 0})


class C51(unittest.TestCase):
    def setUp(self):
        self.w = small()
        self.e = Engine(self.w)
        a, b, c = self.w.living()[:3]
        for q in (a, b, c):
            q.x, q.y = a.x, a.y
            q.skills["pottery"] = 0.5          # writing may be tried
            q.act = None
        self.a, self.b, self.c = a, b, c
        # b promised a 4 grain in 3 days
        self.w.promises.append({"by": b.id, "to": a.id, "goods": {"grain": 4}, "due": self.w.tick + 3 * TPD,
                                "done": False, "made": self.w.tick})
        self.pr = self.w.promises[-1]

    def write(self, p, **kw):
        p.inv["tablet"] = 1
        ok, why = self.e.start(p, dict({"do": "write"}, **kw))
        self.assertTrue(ok, why)

    def test_a_written_promise_outlasts_its_day(self):
        w, e = self.w, self.e
        self.write(self.a, promise=self.b.name)
        deed = self.pr["deed"]
        self.assertTrue(deed.startswith("tablet:"))
        self.assertEqual(self.a.inv.get(deed), 1)
        self.assertIn("owes 4 grain", w.writings[int(deed.split(":")[1])]["text"])
        self.assertIn("written", build_prompt(e, self.a))
        w.tick = self.pr["due"]
        e.society_tick()
        self.assertFalse(self.pr["done"])
        self.assertEqual(self.pr["late"], 1)
        self.assertGreater(self.pr["due"], w.tick)

    def test_an_unwritten_promise_lapses(self):
        self.w.tick = self.pr["due"]
        self.e.society_tick()
        self.assertTrue(self.pr["done"])

    def test_owed_to_whoever_holds_it_and_settled_when_it_comes_back(self):
        w, e = self.w, self.e
        self.write(self.a, promise=self.b.name)
        deed = self.pr["deed"]
        del self.a.inv[deed]
        self.c.inv[deed] = 1                     # a passed it on
        e.society_tick()
        self.assertEqual(self.pr["to"], self.c.id)
        self.c.inv["grain"] = 0
        self.b.inv["grain"] = 4                  # b pays the bearer
        e.society_tick()
        self.assertTrue(self.pr["done"])
        self.assertEqual(self.c.inv.get("grain"), 4)

    def test_the_writing_back_in_the_promisers_hands_settles_it(self):
        self.write(self.a, promise=self.b.name)
        deed = self.pr["deed"]
        del self.a.inv[deed]
        self.b.inv[deed] = 1
        self.e.society_tick()
        self.assertTrue(self.pr["done"])

    def test_the_promiser_writes_and_hands_it_over(self):
        self.write(self.b, promise=self.a.name)
        self.assertEqual(self.a.inv.get(self.pr["deed"]), 1)

    def test_no_promise_no_deed(self):
        self.c.inv["tablet"] = 1
        ok, why = self.e.start(self.c, {"do": "write", "promise": self.a.name})
        self.assertFalse(ok)
        self.assertIn("no unwritten promise", why)

    def test_an_unwritten_law_dies_with_its_maker(self):
        w, e, a = self.w, self.e, self.a
        g = Group(id=w.new_id(), name="Oakfolk", founder=a.id, leader=a.id, members=[a.id, self.b.id, self.c.id], founded=w.tick)
        w.groups[g.id] = g
        for q in (a, self.b, self.c):
            q.groups.append(g.id)
        ok, why = e.start(a, {"do": "make_law", "group": "Oakfolk", "text": "Share food."})
        self.assertTrue(ok, why)
        self.b.inv["tablet"] = 1
        g.leader = self.b.id
        ok, why = e.start(self.b, {"do": "make_law", "group": "Oakfolk", "text": "Ask before taking."})
        self.assertTrue(ok, why)
        self.assertEqual([l[2] for l in g.laws], [False, True])
        g.leader = a.id
        e.die(a, "old age")
        self.assertEqual([l[1] for l in g.laws], ["Ask before taking."])
        self.b.wake = []
        self.assertIn("Ask before taking", build_prompt(e, self.b))


if __name__ == "__main__":
    unittest.main()


class C51Ways(unittest.TestCase):
    """A take that went looking does not walk into a closed store; a far store is still reached."""
    def setUp(self):
        from civ.world import Building
        from civ.content import BUILDINGS
        self.w = small()
        self.e = Engine(self.w)
        self.p, self.o = self.w.living()[:2]
        x, y = next((x, y) for x, y in self.w.beside(self.p.x, self.p.y, 2)
                    if self.w.passable(x, y) and not self.w.building_at(x, y) and (x, y) != (self.p.x, self.p.y))
        b = Building(id=self.w.new_id(), kind="store", x=x, y=y, owner=self.o.id, done=True, hp=BUILDINGS["store"]["hp"])
        b.access = "owner"
        b.inv = {"dried_berries": 5}
        self.w.buildings[b.id] = b
        self.w.at[f"{x},{y}"] = b.id
        self.b = b

    def test_gather_does_not_steal(self):
        ok, why = self.e.start(self.p, {"do": "take", "item": "dried berries"})
        self.assertFalse(ok)
        self.assertIn("closed to you", why)

    def test_naming_the_store_takes_on_purpose(self):
        ok, why = self.e.start(self.p, {"do": "take", "item": "dried berries", "x": self.b.x, "y": self.b.y})
        self.assertTrue(ok, why)

    def test_the_way_across_the_land(self):
        w = self.w
        far = max(((x, y) for x in range(w.w) for y in range(w.h) if w.passable(x, y)),
                  key=lambda t: abs(t[0] - self.p.x) + abs(t[1] - self.p.y))
        self.assertIsNotNone(self.e.path(self.p, *far))
