import os
import tempfile
import unittest

from botciv import config
from botciv.chronicle import check, write_days
from botciv.engine import Engine
from botciv.gateway import OutOfBudget
from botciv.log import Log, NullLog
from botciv.minds.bots import ReciprocityBot
from botciv.minds.gemini import GeminiMind
from botciv.world import World


class FakeGateway:
    """Answers like a model would, using a bot for the choice."""

    def __init__(self, engine, fail_every=0, budget=None):
        self.bot = ReciprocityBot(engine)
        self.e = engine
        self.n = 0
        self.fail_every = fail_every
        self.budget = budget
        self.calls = 0

    def generate(self, prompt, schema, prefer=None, temperature=1.0):
        self.n += 1
        self.calls += 1
        if self.budget is not None and self.n > self.budget:
            raise OutOfBudget("spent")
        if self.fail_every and self.n % self.fail_every == 0:
            return None, {"error": "503"}
        if "chronicle" in prompt:
            return {"title": "A day", "sentences": [{"text": "Things happened.", "cites": []}]}, {"model": "fake"}
        name = prompt.split("You are ", 1)[1].split(".", 1)[0]
        a = self.e.w.by_name(name)
        d = self.bot.one(a)
        d.update({"thought": "fake thought", "memory": f"note {self.n}",
                  "beliefs": [{"name": o.name, "belief": "seems fine"} for o in list(self.e.w.living())[:1] if o.id != a.id]})
        return d, {"model": "fake", "s": 0.1}


class TestGeminiMind(unittest.TestCase):
    def test_runs_with_failures_and_logs(self):
        w = World(config.load(overrides={"world": {"seed": 9}})).generate()
        e = Engine(w, NullLog())
        gw = FakeGateway(e, fail_every=7)
        mind = GeminiMind(e, gw, NullLog(), parallel=3)
        for _ in range(120):
            e.tick(mind.decide)
        self.assertGreater(mind.model_decisions, 50)
        self.assertTrue(any(a.memory.startswith("note") for a in w.living()))

    def test_out_of_budget_stops_before_the_tick(self):
        w = World(config.load(overrides={"world": {"seed": 9}})).generate()
        e = Engine(w, NullLog())
        mind = GeminiMind(e, FakeGateway(e, budget=5), NullLog())
        with self.assertRaises(OutOfBudget):
            for _ in range(50):
                e.tick(mind.decide)
        t = w.tick
        self.assertEqual(t, w.tick)


class TestChronicle(unittest.TestCase):
    def test_checker_drops_unsupported_sentences(self):
        by_id = {1: {"text": "Tam attacked Kora for 3 damage"}, 2: {"text": "Ilo said: \"hello\""}}
        names = ["Tam", "Kora", "Ilo", "Vesh"]
        kept, dropped = check([
            {"text": "Tam struck Kora.", "cites": [1]},
            {"text": "Vesh watched Tam.", "cites": [1]},     # Vesh is not in the cited event
            {"text": "Ilo greeted everyone.", "cites": [9]},  # no such event
            {"text": "Ilo spoke.", "cites": [2]},
        ], by_id, names)
        self.assertEqual([k["text"] for k in kept], ["Tam struck Kora.", "Ilo spoke."])
        self.assertEqual(dropped, 2)

    def test_write_days_appends(self):
        with tempfile.TemporaryDirectory() as d:
            w = World(config.load(overrides={"world": {"seed": 2}})).generate()
            os.makedirs(os.path.join(d, "log"))
            log = Log(os.path.join(d, "log", "events-1.jsonl.gz"))
            e = Engine(w, log)
            bot = ReciprocityBot(e)
            for _ in range(40):
                e.tick(bot.decide)
            log.close()
            n = write_days(d, w, FakeGateway(e))
            self.assertGreaterEqual(n, 1)
            self.assertTrue(os.path.exists(os.path.join(d, "chronicle.jsonl")))


if __name__ == "__main__":
    unittest.main()
