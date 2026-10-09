"""c66 (grand world, Phase 1.4): the first lords. A leader or master may order their people; bots obey as far as
they trust and owe them, others are told and choose; what the ordered gather or make goes to the leader's store,
what they build is the leader's; a leader sees their people in the prompt and the order step."""
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.prompt import build_prompt
from civ.world import Building, Group, TPD


class C66(unittest.TestCase):
    def setUp(self):
        self.w = w = generate({"seed": 6, "people": 16, "width": 40, "height": 40, "bands": 1, "ai": 0})
        self.e = Engine(w)
        adults = [p for p in w.living() if p.adult(w.tick)]
        self.lord, self.men = adults[0], adults[1:4]
        g = Group(id=w.new_id(), name="Hall", founder=self.lord.id, leader=self.lord.id,
                  members=[self.lord.id] + [m.id for m in self.men])
        w.groups[g.id] = g
        for q in [self.lord] + self.men:
            q.groups.append(g.id)
            w.place(q, self.lord.x, self.lord.y)
            q.act, q.intent, q.satiety = None, {"goal": "", "plan": []}, 16
        self.store = Building(id=w.new_id(), kind="store", x=self.lord.x, y=self.lord.y, owner=self.lord.id, done=True)
        w.buildings[self.store.id] = self.store

    def trust_all(self, t):
        for m in self.men:
            m.rel[str(self.lord.id)] = {"trust": t, "met": 0}

    def test_trusting_bots_obey_and_bring_it_to_the_lords_store(self):
        self.trust_all(0.6)
        ok, why = self.e.start(self.lord, {"do": "order", "to": "all", "task": {"do": "gather", "item": "wood", "n": 3}, "days": 1})
        self.assertTrue(ok, why)
        for m in self.men:
            self.assertEqual(m.intent["order"], self.lord.id)
            self.assertEqual(m.intent["plan"][-1]["do"], "put")
            self.assertEqual((m.intent["plan"][-1]["x"], m.intent["plan"][-1]["y"]), (self.store.x, self.store.y))
        ev = [x for x in self.e.log.events if x["kind"] == "order"][-1]
        self.assertEqual(ev["obeyed"], 3)

    def test_the_distrustful_refuse_and_it_is_remembered(self):
        self.trust_all(-0.8)
        self.e.start(self.lord, {"do": "order", "to": "all", "task": "gather", "item": "wood"})
        ev = [x for x in self.e.log.events if x["kind"] == "order"][-1]
        self.assertEqual(ev["refused"], 3)
        self.assertTrue(any(e[2] == "refused_order" for e in self.lord.ledger))

    def test_only_ones_own_people_and_only_sensible_tasks(self):
        stranger = next(p for p in self.w.living() if p not in self.men and p is not self.lord and p.adult(self.w.tick))
        ok, why = self.e.start(self.lord, {"do": "order", "to": stranger.name, "task": {"do": "gather", "item": "wood"}})
        self.assertFalse(ok)
        self.assertIn("not one of your people", why)
        ok, why = self.e.start(self.lord, {"do": "order", "to": "all", "task": {"do": "attack", "to": stranger.name}})
        self.assertFalse(ok)
        ok, why = self.e.start(self.men[0], {"do": "order", "to": "all", "task": {"do": "gather", "item": "wood"}})
        self.assertFalse(ok)

    def test_ordered_work_ends_and_what_is_built_is_the_lords(self):
        self.trust_all(0.6)
        m = self.men[0]
        self.e.start(self.lord, {"do": "order", "to": m.name, "task": {"do": "build", "kind": "shelter"}, "days": 1})
        step = m.intent["plan"][0]
        self.assertEqual(step["for"], self.lord.id)
        m.inv["fibre"] = 20
        m.inv["wood"] = 20
        ok, why = self.e.start(m, dict(step))
        self.assertTrue(ok, why)
        for _ in range(40):
            if not m.act:
                break
            st, _ = self.e.do_build(m, m.act)
            if st != "go":
                m.act = None
        built = [b for b in self.w.buildings.values() if b.kind == "shelter"]
        self.assertTrue(built and built[-1].owner == self.lord.id)
        m.intent = {"goal": "x", "plan": [], "until": self.w.tick, "order": self.lord.id}
        m.act = None
        self.e.run_person(m)
        self.assertIsNone(m.intent)

    def test_people_with_minds_of_their_own_are_told_and_choose(self):
        m = self.men[1]
        m.mind = "llm"
        self.trust_all(0.6)
        self.e.start(self.lord, {"do": "order", "to": m.name, "task": {"do": "fish", "hours": 4}})
        self.assertTrue(any("ordered you" in why for why in m.wake))
        self.assertNotEqual((m.intent or {}).get("order"), self.lord.id)

    def test_the_leader_sees_their_people_and_the_step(self):
        self.lord.mind = "llm"
        text = build_prompt(self.e, self.lord)
        self.assertIn("Your people (yours to order):", text)
        self.assertIn("- order: to", text)
        self.assertNotIn("- order: to", build_prompt(self.e, self.men[0]))


if __name__ == "__main__":
    unittest.main()
