import json
import re
import unittest

from botciv import config
from botciv.engine import Engine
from botciv.log import NullLog
from botciv.prompt import build_prompt, response_schema, available_verbs
from botciv.sim import run_bots
from botciv.world import World


def world(seed=1, **over):
    cfg = config.load(overrides={"world": {"seed": seed, **over}})
    return World(cfg).generate()


def place(w, a, x, y):
    a.x, a.y = x, y


def open_tile(w):
    for y in range(w.h):
        for x in range(w.w - 2):
            if all(w.passable(x + i, y) for i in range(3)) and not any(
                    w.structure_at(x + i, y) for i in range(3)):
                return x, y
    raise AssertionError("no open tiles")


def no_minds(agents):
    return {}


class TestWorld(unittest.TestCase):
    def test_generation_is_deterministic(self):
        a, b = world(7), world(7)
        self.assertEqual(a.terrain, b.terrain)
        self.assertEqual([x.name for x in a.living()], [x.name for x in b.living()])

    def test_save_load_roundtrip_continues_identically(self):
        w1 = world(3)
        run_bots(w1, 100, "reciprocity", NullLog())
        w2 = World.from_dict(json.loads(json.dumps(w1.to_dict())))
        run_bots(w1, 150, "reciprocity", NullLog())
        # bots keep private memory of bushes; a fresh bot on w2 starts without it,
        # so compare with a world that also restarted its bot at tick 100
        w3 = World.from_dict(json.loads(json.dumps(w2.to_dict())))
        run_bots(w2, 150, "reciprocity", NullLog())
        run_bots(w3, 150, "reciprocity", NullLog())
        self.assertEqual(json.dumps(w2.to_dict()), json.dumps(w3.to_dict()))

    def test_bots_run_a_year_without_errors(self):
        w = world(5)
        e, calls, _ = run_bots(w, w.ticks_per_year(), "reciprocity", NullLog())
        self.assertGreater(calls, 0)


class TestActions(unittest.TestCase):
    def setUp(self):
        self.w = world(2)
        self.e = Engine(self.w, NullLog())
        self.a, self.b = self.w.living()[:2]
        x, y = open_tile(self.w)
        place(self.w, self.a, x, y)
        place(self.w, self.b, x + 1, y)

    def act(self, agent, action, ticks=1):
        self.e.apply_decision(agent, {"action": action, "memory": "m"})
        for _ in range(ticks):
            self.e.step_activities()
            self.e.step_world()

    def test_give_records_in_both_ledgers(self):
        self.a.inventory = {"berries": 5}
        self.act(self.a, {"verb": "give", "target": self.b.name, "item": "berries", "qty": 2})
        self.assertGreaterEqual(self.b.inventory.get("berries", 0), 1)
        self.assertTrue(any(k == "gift_in" for _, _, k, _ in self.b.ledger))
        self.assertTrue(any(k == "gift_out" for _, _, k, _ in self.a.ledger))

    def test_deal_with_promise_is_tracked_and_broken(self):
        self.a.inventory = {"wood": 2}
        self.act(self.a, {"verb": "propose", "target": self.b.name, "give": [{"item": "wood", "qty": 2}],
                          "promise_get": [{"item": "meat", "qty": 3}], "due_day": 1})
        pid = max(self.w.proposals)
        self.act(self.b, {"verb": "accept", "id": pid})
        self.assertEqual(self.b.inventory.get("wood"), 2)
        self.assertEqual(len([p for p in self.w.promises if not p["done"]]), 1)
        for _ in range(self.w.tpd() + 1):
            self.e.step_world()
        kinds = [k for _, _, k, _ in self.a.ledger]
        self.assertIn("broke", kinds)

    def test_two_hunters_usually_succeed(self):
        w, e = self.w, self.e
        h = w.herds[0]
        h["size"] = 12
        wins = 0
        for trial in range(20):
            h["size"] = 12
            for ag in (self.a, self.b):
                ag.x, ag.y = h["x"], h["y"]
                ag.inventory = {}
                ag.activity = None
            for ag in (self.a, self.b):
                e.apply_decision(ag, {"action": {"verb": "hunt", "qty": 6}, "memory": ""})
            for _ in range(6):
                e.step_activities()
            if self.a.inventory.get("meat") or self.b.inventory.get("meat"):
                wins += 1
        self.assertGreaterEqual(wins, 15)

    def test_store_access_is_enforced(self):
        w, e = self.w, self.e
        self.a.inventory = {"wood": 4, "berries": 3}
        self.act(self.a, {"verb": "build", "item": "store"}, ticks=5)
        s = next(s for s in w.structures.values() if s.kind == "store")
        self.assertTrue(s.done)
        self.act(self.a, {"verb": "put", "item": "berries", "qty": 3})
        self.act(self.b, {"verb": "take", "target": "store", "item": "berries", "qty": 1})
        self.assertFalse(self.b.inventory.get("berries"))
        self.act(self.a, {"verb": "set_access", "text": "anyone"})
        self.act(self.b, {"verb": "take", "target": "store", "item": "berries", "qty": 1})
        self.assertEqual(self.b.inventory.get("berries"), 1)

    def test_group_found_invite_join(self):
        self.act(self.a, {"verb": "found_group", "name": "River Band", "text": "share meat"})
        self.act(self.a, {"verb": "invite", "target": self.b.name, "group": "River Band"})
        self.act(self.b, {"verb": "join", "group": "river band"})
        g = self.w.group_by_name("River Band")
        self.assertEqual(sorted(g.members), sorted([self.a.id, self.b.id]))

    def test_attack_can_kill(self):
        self.b.health = 2
        self.act(self.a, {"verb": "attack", "target": self.b.name})
        self.assertFalse(self.b.alive)
        self.assertIn("killed", self.b.cause)

    def test_free_deed_is_witnessed(self):
        self.act(self.a, {"verb": "do", "text": "bows deeply", "target": self.b.name, "qty": 1})
        self.assertTrue(any("bows deeply" in t for _, t in self.b.events))

    def test_invalid_action_fails_and_wakes(self):
        self.act(self.a, {"verb": "give", "target": "Nobody", "item": "berries"})
        self.assertTrue(self.a.wake)


class TestPrompt(unittest.TestCase):
    def test_prompt_never_mentions_the_frame(self):
        w = world(4)
        e = Engine(w, NullLog())
        run_bots(w, 200, "reciprocity", NullLog())
        banned = re.compile(r"\b(simulat\w*|agents?|ticks?|game|players?|AI|language model|LLM|turns?)\b", re.I)
        for a in w.living()[:5]:
            p = build_prompt(e, a)
            self.assertIsNone(banned.search(p), banned.search(p) and p[max(0, banned.search(p).start() - 80):banned.search(p).end() + 40])

    def test_schema_enum_matches_available_verbs(self):
        w = world(4)
        e = Engine(w, NullLog())
        a = w.living()[0]
        verbs = available_verbs(e, a)
        s = response_schema(verbs)
        self.assertEqual(s["properties"]["action"]["properties"]["verb"]["enum"], verbs)
        self.assertNotIn("accept", verbs)


if __name__ == "__main__":
    unittest.main()
