"""c80 (grand world, Phase 6): oaths. A promise made at a shrine or temple is an oath; broken, it is news, and
infamy among all who hear of it and share the oath-breaker's gods."""
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.prompt import build_prompt
from civ.world import Building, TPD, key


class C80(unittest.TestCase):
    def test_an_oath_broken_is_infamy_among_those_of_the_same_gods(self):
        w = generate({"seed": 4, "people": 16, "width": 40, "height": 40, "bands": 2, "ai": 0})
        e = Engine(w)
        a, b, c, d = [p for p in w.living() if p.adult(w.tick)][:4]
        for q in (a, b, c, d):
            q.people = "river"
        d.people = "hill"
        x, y = next((x, y) for y in range(5, 35) for x in range(5, 35) if w.cost(x, y) == 1 and not w.building_at(x, y))
        sh = Building(id=w.new_id(), kind="shrine", x=x, y=y, owner=a.id, done=True)
        w.buildings[sh.id] = sh
        w.at[key(x, y)] = sh.id
        w.place(a, x + 1, y)
        w.place(b, x + 1, y + 1)
        for q in w.living():
            if q not in (a, b):
                w.place(q, 2, 38)
        ok, why = e.start(a, {"do": "propose", "to": b.name, "promise_give": {"grain": 5}, "due_days": 1})
        self.assertTrue(ok, why)
        offer = max(w.offers.values(), key=lambda o: o["tick"])
        self.assertIs(e.close_offer(b, offer), True)
        pr = w.promises[-1]
        self.assertIn("shrine", pr["oath"])
        w.tick = pr["due"]
        e.society_tick()
        self.assertIn("oath_broken", {x["kind"] for x in e.log.events})
        nid = max(w.news, key=int)
        c.rel[str(a.id)] = {"trust": 0.0, "met": 0}
        d.rel[str(a.id)] = {"trust": 0.0, "met": 0}
        e.hear(c, nid, b.id)
        e.hear(d, nid, b.id)
        self.assertLess(c.rel[str(a.id)]["trust"], 0.0)       # shares a's gods
        self.assertEqual(d.rel[str(a.id)]["trust"], 0.0)      # does not
        a.mind = "llm"
        self.assertIn("an oath", build_prompt(e, a))


if __name__ == "__main__":
    unittest.main()
