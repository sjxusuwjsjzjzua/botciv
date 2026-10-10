"""c81: an order's task can be written in the answer at last, and one written where the people put it is read."""
import unittest

from botciv.gateway import compact, plain_schema
from civ.engine import Engine
from civ.gen import generate
from civ.prompt import ORDERABLE, SCHEMA, STEP
from civ.society import Society
from civ.world import Building, Group, TPD


class C81(unittest.TestCase):
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
            if q is not self.lord:
                q.rel[str(self.lord.id)] = {"trust": 0.9, "met": 0}
        store = Building(id=w.new_id(), kind="store", x=self.lord.x, y=self.lord.y, owner=self.lord.id, done=True)
        w.buildings[store.id] = store

    def test_the_answer_shape_carries_every_field_the_steps_name(self):
        props = STEP["properties"]
        for k in ("task", "days", "take", "keep"):
            self.assertIn(k, props)
        self.assertEqual(tuple(ORDERABLE), Society.ORDERABLE)
        self.assertEqual(plain_schema(SCHEMA)["properties"]["plan"]["items"]["properties"]["take"]["type"], "boolean")
        self.assertIn('"task": one of gather|', compact(SCHEMA))

    def ordered(self, a):
        ok, why = self.e.start(self.lord, dict({"do": "order", "to": "all"}, **a))
        self.assertTrue(ok, why)
        return self.men[0].intent["plan"][0]

    def test_a_task_written_as_kind(self):
        step = self.ordered({"kind": "gather", "item": "wood", "n": 2})
        self.assertEqual((step["do"], step["item"]), ("gather", "wood"))
        self.assertNotIn("kind", step)

    def test_a_task_written_as_teach_with_the_item_as_learn(self):
        step = self.ordered({"teach": "gathering", "learn": "wood"})
        self.assertEqual((step["do"], step["item"]), ("gather", "wood"))
        self.assertNotIn("teach", step)

    def test_a_build_keeps_its_kind(self):
        step = self.ordered({"task": "build", "kind": "shelter"})
        self.assertEqual((step["do"], step["kind"]), ("build", "shelter"))

    def test_days_as_due_days(self):
        self.ordered({"task": "gather", "item": "wood", "due_days": 3})
        m = self.men[0]
        self.assertEqual(m.intent["until"] - m.intent["since"], 3 * TPD)

    def test_a_word_that_is_no_task_is_still_refused(self):
        ok, why = self.e.start(self.lord, {"do": "order", "to": "all", "kind": "preserving"})
        self.assertFalse(ok)
        self.assertIn("to do what", why)


if __name__ == "__main__":
    unittest.main()
