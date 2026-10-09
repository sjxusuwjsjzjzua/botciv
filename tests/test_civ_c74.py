"""c74: a bot standing in for a person with a mind of their own (while their answer is out, or after the model
fails) does only the obvious and the daily work; offers, orders, raids, trade, partners and children are theirs."""
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.minds.bot import BotMind
from civ.world import Group


class C74(unittest.TestCase):
    def test_the_stand_in_leaves_a_persons_own_choices_to_them(self):
        w = generate({"seed": 6, "people": 20, "width": 40, "height": 40, "bands": 1, "ai": 0})
        e, mind = Engine(w), None
        mind = BotMind(e)
        ad = [p for p in w.living() if p.adult(w.tick)]
        lord = ad[0]
        g = Group(id=w.new_id(), name="Hall", founder=lord.id, leader=lord.id, members=[q.id for q in ad[:6]])
        w.groups[g.id] = g
        for q in ad[:6]:
            q.groups.append(g.id)
            w.place(q, lord.x, lord.y)
        lord.traits.update(ambition=1.0, boldness=1.0, sociability=1.0)
        lord.satiety = 16
        x = {"id": w.new_id(), "from": ad[1].id, "to": lord.id, "kind": "pledge", "tick": w.tick, "text": "", "give": {}, "get": {},
             "promise_give": {}, "promise_get": {}, "due": 5, "hire_days": 0, "serve_days": 0, "teach": None, "learn": None, "name": ""}
        w.offers[x["id"]] = x
        lord.mind = "llm"
        for _ in range(60):
            got = mind.one(lord)
            self.assertNotEqual(got["goal"], "answer offers")
            self.assertFalse(any(s.get("do") in ("order", "muster", "raid", "propose", "accept", "post", "trade") for s in got["plan"]),
                             got)
        lord.mind = "bot"
        self.assertEqual(mind.one(lord)["goal"], "answer offers")


if __name__ == "__main__":
    unittest.main()
