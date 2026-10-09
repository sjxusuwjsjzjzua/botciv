"""c70 (grand world, Phase 3): prices one can know. A trade of one kind of thing for grain (or coin) fixes a price
where it was made; those who made it and saw it remember it, and pass it on as word of the land; the prompt shows
the prices one knows."""
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.prompt import build_prompt


class C70(unittest.TestCase):
    def setUp(self):
        self.w = generate({"seed": 4, "people": 12, "width": 40, "height": 40, "bands": 1, "ai": 0})
        self.e = Engine(self.w)
        self.a, self.b = [p for p in self.w.living() if p.adult(self.w.tick)][:2]
        self.w.place(self.b, self.a.x, self.a.y)

    def test_a_deal_for_grain_fixes_a_price_known_to_those_there(self):
        a, b = self.a, self.b
        a.inv = {"basket": 2}
        b.inv = {"grain": 6}
        self.e.note_price(a.x, a.y, {"basket": 2}, {"grain": 6}, (a, b))
        place = self.e.place_name(a.x, a.y)
        self.assertEqual(self.w.prices[place]["basket"][0], 3.0)
        self.assertTrue(any(v[0] == "price" and v[1] == "basket" for v in b.known.values()))
        self.assertIn("Prices you know: basket 3 grain", build_prompt(self.e, b))
        self.e.note_price(a.x, a.y, {"basket": 1}, {"wood": 2}, (a, b))       # no grain, no price
        self.assertEqual(list(self.w.prices[place]), ["basket"])

    def test_word_of_a_price_goes_round(self):
        a, b = self.a, self.b
        self.e.note_price(a.x, a.y, {"basket": 1}, {"grain": 4}, (a,))
        for k in [k for k, v in b.known.items() if v[0] == "price"]:
            del b.known[k]
        b.rel[str(a.id)] = {"trust": 0.5, "met": 0}
        while self.w.tick % 12 != 6:
            self.w.tick += 1
        self.w.tick -= self.w.tick % 3          # remember runs on hours divisible by 3
        self.w.tick += 6 - self.w.tick % 12
        for o in self.w.living():
            if o.id not in (a.id, b.id):
                self.w.place(o, 0, 0)
        self.e.remember()
        self.assertTrue(any(v[0] == "price" and v[1] == "basket" for v in b.known.values()))

    def test_a_trader_carries_from_cheap_to_dear(self):
        from civ.minds.bot import BotMind
        from civ.world import Building
        w, mind = self.w, BotMind(self.e)
        a, b = self.a, self.b
        others = [p for p in w.living() if p.adult(w.tick) and p.id not in (a.id, b.id)]
        t = others[0]
        t.vocation, t.inv = "trader", {"grain": 20}
        s1 = Building(id=w.new_id(), kind="store", x=t.x + 2, y=t.y, owner=a.id, done=True)
        s2 = Building(id=w.new_id(), kind="store", x=t.x - 2, y=t.y, owner=b.id, done=True)
        for s_ in (s1, s2):
            w.buildings[s_.id] = s_
        s1.inv, s1.trade = {"basket": 5}, [{"give": {"basket": 1}, "get": {"grain": 2}}]
        s2.inv, s2.trade = {"grain": 30}, [{"give": {"grain": 5}, "get": {"basket": 1}}]
        got = mind.merchant_goal(t)
        self.assertIsNotNone(got)
        self.assertEqual([st["do"] for st in got["plan"]][-2:], ["trade", "trade"])
        self.assertEqual((got["plan"][-2]["x"], got["plan"][-1]["x"]), (s1.x, s2.x))
        s2.owner = a.id                         # never back to the hand it came from
        self.assertIsNone(mind.merchant_goal(t))


if __name__ == "__main__":
    unittest.main()
