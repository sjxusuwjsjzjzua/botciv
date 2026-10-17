"""The verbs of a towns world (docs/towns_spec.md §8.3, §5.7): settle takes a plot, found founds a settlement 3 or
more places from any other, clear pulls down a building of one's own with a quarter of its makings back. Each is
told only to those it applies to; worlds without towns refuse them."""
import unittest

from civ.content import BUILDINGS
from civ.engine import Engine
from civ.prompt import steps_text
from civ.realm import generate
from civ.towns import spacing_ok

HOMES = ("cottage", "farmstead", "lord")


def fresh():
    w = generate({"seed": 5, "people": 80, "width": 40, "height": 40, "format": "towns1"})
    return w, Engine(w)


def holds_plot(site, p):
    return any(q["holder"] == p.id and q["kind"] in HOMES for q in site.plots)


class Verbs(unittest.TestCase):
    def setUp(self):
        self.w, self.e = fresh()

    def run_act(self, p, hours=8):
        for _ in range(hours):
            if not p.act:
                break
            status, msg = getattr(self.e, "do_" + p.act["do"])(p, p.act)
            if status != "go":
                p.act = None
                return status, msg
        return None, ""

    def test_settle(self):
        w = self.w
        site = next(iter(w.sites.values()))
        p = next(q for q in w.living() if q.adult(w.tick))
        for q in site.plots:                         # p holds nothing here
            if q["holder"] in (p.id, p.partner):
                q["holder"] = -1
        p.partner = None
        p.x, p.y = site.x, site.y
        self.assertIn("- settle", steps_text(self.e, p))
        ok, why = self.e.start(p, {"do": "settle"})
        self.assertTrue(ok, why)
        self.assertTrue(holds_plot(site, p))
        self.assertNotIn("- settle", steps_text(self.e, p))
        ok, why = self.e.start(p, {"do": "settle"})
        self.assertFalse(ok)
        self.assertIn("already", why)

    def test_found(self):
        w = self.w
        p = next(q for q in w.living() if q.adult(w.tick))
        spot = next(((x, y) for y in range(w.h) for x in range(w.w)
                     if w.passable(x, y) and w.terrain[y][x] != "~" and spacing_ok(w, x, y)
                     and all(max(abs(s.x - x), abs(s.y - y)) > 2 for s in w.sites.values())), None)
        self.assertIsNotNone(spot)
        near = next(iter(w.sites.values()))
        p.x, p.y = near.x + 1, near.y
        ok, why = self.e.start(p, {"do": "found", "name": "Newholm"})
        self.assertFalse(ok)
        self.assertIn("too near", why)
        p.x, p.y = spot
        self.assertIn("- found", steps_text(self.e, p))
        ok, why = self.e.start(p, {"do": "found", "name": "Newholm"})
        self.assertTrue(ok, why)
        site = w.site_of(*spot)
        self.assertEqual(site.name, "Newholm")
        self.assertTrue(holds_plot(site, p))
        ok, why = self.e.start(p, {"do": "found", "name": "newholm"})
        self.assertFalse(ok)

    def test_clear(self):
        w = self.w
        b = next(b for b in w.buildings.values() if b.done and b.owner and b.owner > 0 and b.kind != "farm"
                 and not b.animals and w.people[b.owner].alive and BUILDINGS[b.kind]["cost"])
        p = w.people[b.owner]
        p.x, p.y = b.x, b.y
        self.assertIn("clear:", steps_text(self.e, p))
        other = next(q for q in w.living() if q.id not in (p.id, p.partner) and b.owner not in (q.id, q.partner))
        other.x, other.y = b.x, b.y
        ok, why = self.e.start(other, {"do": "clear", "bid": b.id})
        self.assertFalse(ok)
        ok, why = self.e.start(p, {"do": "clear", "bid": b.id})
        self.assertTrue(ok, why)
        status, msg = self.run_act(p)
        self.assertEqual(status, "done", msg)
        self.assertNotIn(b.id, w.buildings)
        self.assertNotIn(b.id, [x.id for x in w.buildings_at(b.x, b.y)])
        self.assertTrue(all(q.home != b.id for q in w.people.values()))

    def test_market_day(self):
        """Every 5th day, by day, those with goods posted stand at the market, or at the green without one (§7)."""
        import math
        w = self.w
        st = next(b for b in w.buildings.values() if b.done and "store" in BUILDINGS[b.kind]["roles"] and b.owner
                  and w.people[b.owner].alive and w.site_of(b.x, b.y) and w.site_of(b.x, b.y).green)
        p, site = w.people[st.owner], w.site_of(st.x, st.y)
        st.trade = [{"give": {"pot": 1}, "get": {"grain": 2}}]
        p.x, p.y, p.act, p.rest = st.x, st.y, None, False
        g = site.green
        for day, near in ((5, True), (6, False)):
            w.tick, p.pos = day * 12 + 3, list(st.pos)
            self.e.towns_hour()
            self.assertEqual(math.hypot(p.pos[0] - g[0], p.pos[1] - g[1]) < max(g[2], g[3]), near, (day, p.pos, g))

    def test_home_at_dusk(self):
        """At dusk a housed bot out near home is woken and goes home for the night; a mind of its own is not."""
        from civ.minds.bot import BotMind
        from civ.world import NIGHT_FROM
        w = self.w
        b = next(b for b in w.buildings.values() if b.done and b.kind in ("shelter", "house") and w.people.get(b.owner)
                 and w.people[b.owner].alive and w.people[b.owner].adult(w.tick)
                 and w.passable(b.x + 2, b.y) and w.terrain[b.y][b.x + 2] != "~")
        p = w.people[b.owner]
        p.home, p.x, p.y, p.wake, p.held = b.id, b.x + 2, b.y, [], None
        p.intent, p.act = {"goal": "gather", "plan": [{"do": "gather", "item": "berries"}]}, {"do": "wait", "left": 5}
        w.tick = 7 * 12 + NIGHT_FROM - 1
        p.mind = "llm"
        self.e.towns_hour()
        self.assertNotIn("night is falling", p.wake)
        p.mind = "bot"
        self.e.towns_hour()
        self.assertIn("night is falling", p.wake)
        self.assertEqual(BotMind(self.e).one(p)["goal"], "home for the night")


class NotInPlainWorlds(unittest.TestCase):
    def test_refused(self):
        w = generate({"seed": 5, "people": 30, "width": 32, "height": 32})
        e = Engine(w)
        p = next(iter(w.living()))
        for step in ({"do": "settle"}, {"do": "found", "name": "Newholm"}, {"do": "clear", "x": p.x, "y": p.y}):
            ok, why = e.start(p, step)
            self.assertFalse(ok)
        self.assertNotIn("- settle", steps_text(e, p))
        self.assertNotIn("clear:", steps_text(e, p))


if __name__ == "__main__":
    unittest.main()
