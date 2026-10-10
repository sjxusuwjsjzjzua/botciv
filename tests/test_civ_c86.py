"""c86: pack beasts: a donkey or horse led from one's pen carries for one, and must graze or be fed."""
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.prompt import build_prompt
from civ.world import Building, TPD


class C86(unittest.TestCase):
    def setUp(self):
        self.w = w = generate({"seed": 6, "people": 12, "width": 40, "height": 40, "bands": 1, "ai": 0})
        self.e = Engine(w)
        self.p = p = next(q for q in w.living() if q.adult(w.tick))
        p.act, p.intent, p.inv = None, {"goal": "", "plan": []}, {}
        x, y = next((x, y) for x, y in w.beside(p.x, p.y) if w.passable(x, y) and not w.building_at(x, y))
        self.pen = Building(id=w.new_id(), kind="pen", x=x, y=y, owner=p.id, done=True, animals={"donkey": 2})
        w.buildings[self.pen.id] = self.pen
        w.at[f"{x},{y}"] = self.pen.id

    def lead(self, n=1):
        ok, why = self.e.start(self.p, {"do": "lead", "animal": "donkey", "n": n})
        self.assertTrue(ok, why)
        while self.p.act:
            res = self.e.do_lead(self.p, self.p.act)
            if res[0] != "go":
                self.p.act = None
        return res

    def test_a_led_donkey_carries(self):
        before = self.p.capacity(self.w.tick)
        self.lead()
        self.assertEqual(self.p.led, {"donkey": 1})
        self.assertEqual(self.pen.animals, {"donkey": 1})
        self.assertEqual(self.p.capacity(self.w.tick), before + 40)
        self.assertIn("with 1 donkey you lead", build_prompt(self.e, self.p))

    def test_put_back_in_the_pen(self):
        self.lead(2)
        ok, why = self.e.start(self.p, {"do": "put", "item": "donkey", "n": 2})
        self.assertTrue(ok, why)
        self.assertEqual((self.p.led, self.pen.animals), ({}, {"donkey": 2}))

    def test_unfed_three_days_one_dies(self):
        self.lead()
        row = self.w.terrain[self.p.y]
        self.w.terrain[self.p.y] = row[:self.p.x] + "~" + row[self.p.x + 1:]   # no grass where they stand
        for _ in range(3):
            self.e.led_day()
        self.assertEqual(self.p.led, {})
        self.assertGreater(self.p.inv.get("meat", 0), 0)

    def test_fed_from_hay(self):
        self.lead()
        row = self.w.terrain[self.p.y]
        self.w.terrain[self.p.y] = row[:self.p.x] + "~" + row[self.p.x + 1:]
        self.p.inv = {"hay": 5}
        for _ in range(3):
            self.e.led_day()
        self.assertEqual((self.p.led, self.p.inv["hay"]), ({"donkey": 1}, 2))


if __name__ == "__main__":
    unittest.main()
