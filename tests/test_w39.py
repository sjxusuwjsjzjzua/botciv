"""Rules w39: the crafts beyond pairs. Clay, flint, flax and odd stones lie in the land; kilns, looms
and furnaces are built; a technique is worked out by working a material where it belongs (with
word of how near one came), or taught; what one knows how to make is then made with craft."""
import json
import unittest

from botciv import items as I, tech as T
from botciv.engine import Engine, BUILD
from botciv.log import NullLog
from botciv.prompt import build_prompt, available_verbs
from botciv.world import World, Structure, key, unkey, dist
from tests.test_engine import world, place


def run(e, a, act, hours=12):
    ok, msg = e.start(a, act)
    assert ok, msg
    out = []
    for _ in range(hours):
        before = list(a.events)
        e.step_activities()
        out += [t for _, t in a.events[len(before):]] if len(a.events) >= len(before) else []
        if not a.activity:
            break
    return out


def station(w, kind, x, y, owner):
    s = Structure(id=w.new_id(), kind=kind, x=x, y=y, owner=owner, hp=30, done=True)
    w.structures[s.id] = s
    return s


class Land(unittest.TestCase):
    def test_every_world_holds_the_deposits(self):
        w = world(1)
        kinds = {d["kind"] for d in w.deposits.values()}
        self.assertEqual(kinds, set(T.DEPOSITS))
        for k, d in w.deposits.items():
            x, y = unkey(k)
            where = T.DEPOSITS[d["kind"]]["where"]
            self.assertEqual(w.t(x, y) == "^", where == "rock")

    def test_an_old_world_gets_them_and_keeps_its_land(self):
        w = world(2)
        d = w.to_dict()
        d.pop("deposits")
        again = World.from_dict(json.loads(json.dumps(d)))
        self.assertEqual(again.terrain, w.terrain)
        self.assertEqual(set(again.deposits), set(w.deposits))

    def test_gathering_uses_a_deposit_up(self):
        w = world(1)
        e = Engine(w, NullLog())
        a = w.living()[0]
        k, dep = next((k, d) for k, d in w.deposits.items() if d["kind"] == "flint")
        x, y = unkey(k)
        spot = next((x + dx, y + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if w.passable(x + dx, y + dy))
        place(w, a, *spot)
        a.inventory = {}
        dep["left"] = 2
        run(e, a, {"verb": "gather", "item": "flint", "qty": 5})
        self.assertEqual(a.inventory.get("flint"), 2)
        self.assertNotIn(k, w.deposits)                      # worked out for good


class Crafts(unittest.TestCase):
    def setUp(self):
        self.w = world(1)
        self.e = Engine(self.w, NullLog())
        self.a, self.b = self.w.living()[:2]
        self.a.inventory = {}
        for x in range(2, 20):
            if self.w.passable(x, 2) and self.w.passable(x + 1, 2) and not self.w.structure_at(x + 1, 2):
                break
        place(self.w, self.a, x, 2)
        self.spot = (x + 1, 2)

    def test_work_teaches_with_a_near_miss_first(self):
        a, w = self.a, self.w
        station(w, "kiln", *self.spot, a.id)
        a.inventory = {"clay": 3}                        # no wood to fire it: only a near miss
        msgs = run(self.e, a, {"verb": "work", "item": "clay", "qty": 3})
        self.assertNotIn("pottery", a.know)
        self.assertTrue(any("steady heat" in m for m in msgs), msgs)
        a.inventory = {"clay": 3, "wood": 2}
        for _ in range(40):
            if "pottery" in a.know:
                break
            run(self.e, a, {"verb": "work", "item": "clay", "qty": 6})
        self.assertIn("pottery", a.know)
        self.assertEqual(a.inventory.get("clay"), 3)       # working to learn uses nothing up

    def test_craft_makes_what_one_knows_at_its_place(self):
        a, w = self.a, self.w
        a.know.append("pottery")
        a.inventory = {"clay": 6, "wood": 2}
        ok, msg = self.e.start(a, {"verb": "craft", "item": "jar"})
        self.assertFalse(ok)
        self.assertIn("kiln", msg)
        station(w, "kiln", *self.spot, a.id)
        run(self.e, a, {"verb": "craft", "item": "jar", "qty": 2})
        self.assertEqual(a.inventory.get("jar"), 2)
        self.assertEqual(a.inventory.get("clay"), 0 if "clay" in a.inventory else None)

    def test_one_must_know_how(self):
        a = self.a
        a.inventory = {"flint": 2, "wood": 2}
        ok, msg = self.e.start(a, {"verb": "craft", "item": "flint_knife"})
        self.assertFalse(ok)
        self.assertIn("knap", msg)

    def test_teaching_a_technique(self):
        a, b = self.a, self.b
        place(self.w, b, a.x, a.y + 1 if self.w.passable(a.x, a.y + 1) else a.y)
        a.know.append("knapping")
        run(self.e, a, {"verb": "teach", "target": b.name, "item": "flint_axe"})
        self.assertIn("knapping", b.know)

    def test_tools_do_the_work(self):
        a = self.a
        a.inventory = {"bronze_axe": 1}
        self.assertEqual(self.e.best_tool(a, "wood"), ("bronze_axe", 3))
        a.inventory = {"axe": 1, "flint_axe": 1}
        self.assertEqual(self.e.best_tool(a, "wood")[0], "flint_axe")

    def test_the_whole_road_to_bronze_is_there(self):
        # every recipe's inputs come from the land or another recipe, and every station can be built
        made = {r["out"] for r in T.RECIPES} | set(T.DEPOSITS) | {"wood", "stone", "fibre", "bone", "hide", "rope"}
        for r in T.RECIPES:
            for k in list(r["in"]) + r.get("tools", []):
                self.assertIn(k, made, (r["out"], k))
        for st in T.STATIONS.values():
            for k in st["cost"]:
                self.assertIn(k, made)
        self.assertIn("bronze", {r["out"] for r in T.RECIPES})

    def test_prompt_shows_what_is_known_and_seen(self):
        a, w = self.a, self.w
        a.know.append("pottery")
        a.inventory = {"flint": 1}
        text = build_prompt(self.e, a)
        self.assertIn("jar = clay 3 + wood 1 (3h)", text)
        self.assertIn("work", available_verbs(self.e, a))
        k = next(iter(w.deposits))
        a.x, a.y = next((x, y) for x, y in [unkey(k)] + [(unkey(k)[0] + dx, unkey(k)[1] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
                        if w.passable(x, y))
        self.assertIn(T.DEPOSITS[w.deposits[k]["kind"]]["name"], build_prompt(self.e, a))

    def test_worn_clothes_are_not_load(self):
        a = self.a
        a.inventory = {"fur_coat": 1, "wood": 2}
        self.assertEqual(a.carrying(), 4.0)
        a.inventory = {"fur_coat": 2}
        self.assertEqual(a.carrying(), 3.0)

    def test_building_from_a_store_beside(self):
        a, w = self.a, self.w
        st = station(w, "store", *self.spot, a.id)
        st.inventory = {"clay": 4, "stone": 2}
        a.inventory = {}
        ok, msg = self.e.start(a, {"verb": "build", "item": "kiln"})
        self.assertTrue(ok, msg)
        self.assertFalse(st.inventory)


if __name__ == "__main__":
    unittest.main()
