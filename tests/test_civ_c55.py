"""c55 (roadmap C5, markets): what is posted at the stores beside a market is told to whoever sees or knows the
market, and bots buy from it without having seen each store."""
import unittest

from civ.content import BUILDINGS
from civ.engine import Engine
from civ.gen import generate
from civ.minds.bot import BotMind
from civ.prompt import build_prompt
from civ.world import Building, key


def small(seed=4):
    return generate({"seed": seed, "people": 12, "width": 40, "height": 40, "bands": 2, "ai": 0})


def put(w, kind, owner, x, y):
    b = Building(id=w.new_id(), kind=kind, x=x, y=y, owner=owner, done=True, hp=BUILDINGS[kind]["hp"])
    w.buildings[b.id] = b
    w.at[f"{x},{y}"] = b.id
    return b


class C55(unittest.TestCase):
    def setUp(self):
        self.w = small()
        self.e = Engine(self.w)
        self.p, self.o = self.w.living()[:2]
        spots = [(x, y) for x in range(self.w.w) for y in range(self.w.h)
                 if self.w.passable(x, y) and not self.w.building_at(x, y) and abs(x - self.p.x) + abs(y - self.p.y) > 14]
        mx, my = spots[0]
        self.market = put(self.w, "market", self.o.id, mx, my)
        sx, sy = next((x, y) for x, y in self.w.beside(mx, my, 2) if (x, y) != (mx, my) and self.w.passable(x, y)
                      and not self.w.building_at(x, y))
        self.store = put(self.w, "store", self.o.id, sx, sy)
        self.store.inv = {"flint_axe": 2}
        self.store.trade = [{"give": {"flint_axe": 1}, "get": {"grain": 3}}]

    def test_a_known_market_tells_its_trades(self):
        p = self.p
        self.assertNotIn("The market at", build_prompt(self.e, p))
        p.known[key(self.market.x, self.market.y)] = ["building", "market", self.w.tick]
        self.assertIn("gives flint axe 1 for grain 3", build_prompt(self.e, p))

    def test_bots_buy_at_a_market_they_know(self):
        p = self.p
        p.known[key(self.market.x, self.market.y)] = ["building", "market", self.w.tick]
        p.inv = {"grain": 5}
        got = BotMind(self.e).trade_goal(p)
        self.assertIsNotNone(got)


if __name__ == "__main__":
    unittest.main()
