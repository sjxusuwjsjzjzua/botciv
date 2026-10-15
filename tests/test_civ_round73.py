"""Round 73: world2's commonest refusals made into ways forward. A leader whose people are all out of earshot goes to
the nearest and then orders; one with clay and no tablet presses one and then writes; a bot reaps its ripe field
where it stands, out of sight or not."""
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.minds.bot import BotMind
from civ.world import Building, Group, key


class Round73(unittest.TestCase):
    def setUp(self):
        self.w = w = generate({"seed": 6, "people": 16, "width": 60, "height": 60, "bands": 1, "ai": 0})
        self.e = Engine(w)
        adults = [p for p in w.living() if p.adult(w.tick)]
        self.lord, self.man = adults[0], adults[1]
        for q in (self.lord, self.man):
            q.act, q.intent, q.satiety = None, {"goal": "", "plan": []}, 16

    def open_tile(self, x0, y0):
        w = self.w
        return next((x, y) for r in range(0, 30) for x, y in w.beside(x0, y0, r) if w.cost(x, y) > 0 and not w.building_at(x, y))

    def test_out_of_earshot_the_leader_goes_and_then_orders(self):
        w, e, lord, man = self.w, self.e, self.lord, self.man
        g = Group(id=w.new_id(), name="Hall", founder=lord.id, leader=lord.id, members=[lord.id, man.id])
        w.groups[g.id] = g
        lord.groups.append(g.id)
        man.groups.append(g.id)
        far = next(((x, y) for y in range(w.h) for x in range(w.w) if 25 <= max(abs(x - lord.x), abs(y - lord.y)) <= 40
                    and w.cost(x, y) > 0 and w.reachable(lord.x, lord.y, x, y)), None)
        if far is None:
            self.skipTest("no reachable tile at that distance")
        w.place(man, *far)
        ok, why = e.start(lord, {"do": "order", "to": "all", "task": {"do": "gather", "item": "wood"}})
        self.assertTrue(ok, why)
        self.assertEqual(lord.act["do"], "go")
        self.assertEqual(lord.intent["plan"][0]["do"], "order")
        self.assertTrue(lord.intent["plan"][0]["sought"])
        # once sought, a second time out of earshot is refused, with who is nearest
        ok, why = e.start(lord, {"do": "order", "to": "all", "task": {"do": "gather", "item": "wood"}, "sought": True})
        self.assertFalse(ok)
        self.assertIn(man.name, why)

    def test_clay_in_hand_presses_a_tablet_then_writes(self):
        p = self.lord
        p.inv["clay"] = 3
        p.skills["writing"] = 0.3
        ok, why = self.e.start(p, {"do": "write", "text": "Our field is by the river"})
        self.assertTrue(ok, why)
        self.assertEqual(p.act["do"], "craft")
        self.assertEqual(p.intent["plan"][0]["do"], "write")
        p.inv.pop("clay")
        ok, why = self.e.start(p, {"do": "write", "text": "again"})
        self.assertFalse(ok)
        self.assertIn("no clay tablet", why)

    def test_a_ripe_field_is_reaped_where_it_stands(self):
        w, p = self.w, self.man
        p.skills["farming"] = 0.5
        x, y = self.open_tile(p.x + 20 if p.x + 20 < w.w else p.x - 20, p.y)
        f = Building(id=w.new_id(), kind="farm", x=x, y=y, owner=p.id, done=True, inv={"grain": 30})
        w.buildings[f.id] = f
        w.at[key(x, y)] = f.id
        got = BotMind(self.e).farm_goal(p)
        step = got["plan"][0]
        self.assertEqual((step["do"], step["item"], step["x"], step["y"]), ("gather", "grain", x, y))
        ok, why = self.e.start(p, dict(step))
        self.assertTrue(ok, why)

    def test_a_toll_remembered_breaks_no_search_and_no_prompt(self):
        from civ.prompt import build_prompt
        from civ.world import tile_of
        p = self.lord
        p.known["toll3,4"] = ["toll", 1, 0]
        self.assertIsNone(tile_of("toll3,4"))
        self.assertEqual(tile_of("3,4"), (3, 4))
        self.e.building_near(p, lambda b: True, r=20)
        self.e.workshop_for(p, "pottery")
        self.assertIn("How the world works", build_prompt(self.e, p))


if __name__ == "__main__":
    unittest.main()
