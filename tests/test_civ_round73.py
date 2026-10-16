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

    def test_ended_service_and_the_long_dead_are_let_go(self):
        w, e, a, b = self.w, self.e, self.lord, self.man
        w.services = [{"master": a.id, "servant": b.id, "end": 0, "done": True, "terms": "", "log": {}} for _ in range(150)]
        w.services.append({"master": a.id, "servant": b.id, "end": 10 ** 6, "done": False, "terms": "", "log": {}})
        w.tick = 40 * 12 * 2
        e.society_tick()
        self.assertEqual(len(w.services), 1)
        dead = next(p for p in w.living() if p not in (a, b))
        friend = next(p for p in w.living() if p not in (a, b, dead))
        a.rel[str(dead.id)] = {"trust": 0.1, "met": 0}
        a.rel[str(friend.id)] = {"trust": 0.1, "met": 0}
        dead.alive, dead.died = False, 0
        e.forget_the_dead()
        self.assertNotIn(str(dead.id), a.rel)
        self.assertIn(str(friend.id), a.rel)

    def test_a_raid_with_no_band_musters_first(self):
        w, e, lord, man = self.w, self.e, self.lord, self.man
        g = Group(id=w.new_id(), name="Hall", founder=lord.id, leader=lord.id, members=[lord.id, man.id])
        w.groups[g.id] = g
        lord.groups.append(g.id)
        man.groups.append(g.id)
        w.place(man, lord.x, lord.y)
        ok, why = e.start(lord, {"do": "raid", "x": lord.x + 5, "y": lord.y})
        self.assertTrue(ok, why)
        self.assertEqual(lord.intent["plan"][0]["do"], "raid")
        self.assertTrue(lord.intent["plan"][0]["mustered"])
        self.assertIsNotNone(e.band_of(lord))

    def test_release_meant_as_reaping_or_waiting(self):
        from civ.prompt import build_prompt
        p = self.lord
        self.assertNotIn("release: who", build_prompt(self.e, p))
        ok, why = self.e.start(p, {"do": "release", "hours": 1})
        self.assertTrue(ok, why)
        self.assertEqual(p.act["do"], "wait")
        ok, why = self.e.start(p, {"do": "release", "text": "free them"})
        self.assertFalse(ok)
        self.assertIn("you hold no one", why)

    def test_go_to_a_kind_of_place(self):
        p = self.lord
        ok, why = self.e.start(p, {"do": "go", "place": "hills"})
        if self.e.place_of_kind(p, "hills") is None:
            self.skipTest("no hills in sight")
        self.assertTrue(ok, why)
        self.assertIsNone(self.e.place_of_kind(p, "the land of nowhere"))
        from civ.acts import norm
        self.assertEqual(norm("herb"), "herbs")

    def test_mend_makes_its_rope_from_fibre_carried(self):
        from civ.acts import mend_stuff
        w, p = self.w, self.lord
        x, y = self.open_tile(p.x, p.y)
        b = Building(id=w.new_id(), kind="pen", x=x, y=y, owner=p.id, done=True, hp=3)
        w.buildings[b.id] = b
        w.at[key(x, y)] = b.id
        self.assertEqual(mend_stuff(b), "rope")
        p.inv = {"fibre": 6}
        ok, why = self.e.start(p, {"do": "mend", "x": x, "y": y})
        self.assertTrue(ok, why)
        self.assertEqual(p.act["do"], "craft")
        self.assertEqual(p.intent["plan"][0]["do"], "mend")
        p.inv, p.act, p.intent = {}, None, {"goal": "", "plan": []}
        ok, why = self.e.start(p, {"do": "mend", "x": x, "y": y})
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
