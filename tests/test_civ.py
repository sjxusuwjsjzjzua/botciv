"""civ: the world runs, bots live, the language-model path works with a stand-in model, prompts
stay within budget and never speak of simulations."""
import json
import random
import re
import time
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.minds.bot import BotMind
from civ.minds.llm import LLMMind
from civ.prompt import build_prompt
from civ.world import World, TPD
from civ.content import TERRAIN, DEPOSITS, WILD, BUILDINGS


class FakeGateway:
    """Answers like a model would, after a moment."""
    def __init__(self, delay=0.01, bad=0.0):
        self.delay, self.bad, self.n = delay, bad, 0

    def generate(self, prompt, schema, **kw):
        time.sleep(self.delay)
        self.n += 1
        if random.random() < self.bad:
            return None, {"error": "bad"}
        return {"thought": "I should gather food and wood.", "goal": "provide for myself",
                "plan": [{"do": "gather", "item": "wild grain", "n": 6}, {"do": "gather", "item": "wood", "n": 4},
                         {"do": "build", "kind": "shelter"}], "say": "Good day to you.", "memory": "Build a shelter soon."}, \
               {"model": "fake", "s": self.delay, "in": len(prompt) // 4, "out": 60}


def small(ai=0, people=30, seed=4):
    return generate({"seed": seed, "people": people, "width": 44, "height": 44, "bands": 3, "ai": ai})


class CivWorld(unittest.TestCase):
    def test_saves_and_loads(self):
        w = small()
        e = Engine(w)
        m = BotMind(e)
        for _ in range(TPD * 3):
            e.tick(m.decide)
        again = World.from_dict(json.loads(json.dumps(w.to_dict())))
        self.assertEqual(len(again.living()), len(w.living()))
        self.assertEqual(again.tick, w.tick)

    def test_bots_live_a_season(self):
        w = small(people=40)
        e = Engine(w)
        m = BotMind(e)
        for _ in range(TPD * 10):
            e.tick(m.decide)
        self.assertGreater(len(w.living()), 30)
        self.assertTrue(any(b.done for b in w.buildings.values()))

    def test_llm_minds_answer_and_the_world_goes_on(self):
        w = small(ai=5)
        e = Engine(w)
        bots = BotMind(e)
        llm = LLMMind(e, FakeGateway(), parallel=5)

        def decide(ps):
            out = bots.decide([p for p in ps if p.mind == "bot"])
            out.update(llm.decide([p for p in ps if p.mind == "llm"]))
            return out
        for _ in range(TPD * 2):
            e.tick(decide)
        llm.close()
        ai = [p for p in w.living() if p.mind == "llm"]
        self.assertEqual(len(ai), 5)
        self.assertGreaterEqual(llm.calls, 5)
        self.assertEqual(llm.fails, 0)
        self.assertTrue(any(p.memory == "Build a shelter soon." for p in ai))

    def test_failing_model_falls_back_to_a_bot(self):
        w = small(ai=3)
        e = Engine(w)
        llm = LLMMind(e, FakeGateway(bad=1.0), parallel=3)
        for _ in range(TPD):
            e.tick(lambda ps: llm.decide([p for p in ps if p.mind == "llm"]))
        llm.close()
        self.assertGreater(llm.fallbacks, 0)

    def test_prompt_budget_and_words(self):
        w = small(ai=5, people=40)
        e = Engine(w)
        m = BotMind(e)
        for _ in range(TPD * 6):
            e.tick(m.decide)
        for p in w.living()[:20]:
            text = build_prompt(e, p)
            self.assertLess(len(text), 15000, p.name)
            self.assertIsNone(re.search(r"\b(simulat\w*|agents?|game|turns?|ticks?|bots?|llm|language model)\b", text, re.I),
                              re.findall(r"\b(simulat\w*|agents?|game|turns?|ticks?|bots?|llm|language model)\b", text, re.I)[:3])

    def test_local_models_are_not_paced_like_the_api(self):
        from botciv.gateway import limits_for
        self.assertEqual(limits_for("ollama:gemma4:26b")["rpm"], 100000)
        self.assertEqual(limits_for("gemma-4-31b-it")["rpm"], 28)

    def test_the_land_keeps_its_minds_while_they_answer(self):
        w = small(ai=4)
        e = Engine(w)
        llm = LLMMind(e, FakeGateway(), parallel=2)
        for p in [p for p in w.living() if p.mind == "llm"][:2]:
            e.die(p, "died of old age")
        llm.keep_minds()                                # the model has not shown it answers yet
        self.assertEqual(sum(1 for p in w.living() if p.mind == "llm"), 2)
        llm.calls = 30
        llm.keep_minds()
        llm.close()
        self.assertEqual(sum(1 for p in w.living() if p.mind == "llm"), 4)

    def test_a_slow_model_neither_starves_its_people_nor_floods_the_server(self):
        w = small(ai=12, people=30)
        e = Engine(w)
        bots = BotMind(e)
        llm = LLMMind(e, FakeGateway(delay=0.4), parallel=2, patience=0.2)

        def decide(ps):
            out = bots.decide([p for p in ps if p.mind == "bot"])
            out.update(llm.decide([p for p in ps if p.mind == "llm"]))
            self.assertLessEqual(len(llm.pending), llm.in_flight)
            return out
        for _ in range(TPD * 4):
            e.tick(decide)
        llm.close()
        self.assertGreater(llm.stopgaps, 0)
        self.assertGreater(llm.calls, 0)
        self.assertEqual(sum(1 for p in w.people.values() if p.mind == "llm" and not p.alive), 0)

    def test_asking_to_learn_gets_a_lesson(self):
        w = small()
        e = Engine(w)
        a, b = w.living()[0], w.living()[1]
        b.x, b.y = a.x, a.y
        b.skills["pottery"], a.skills["pottery"] = 0.8, 0.0
        e.start(a, {"do": "propose", "to": b.name, "learn": "pottery"})
        x = next(x for x in w.offers.values() if x["from"] == a.id)
        self.assertIn(f"{b.name} teaches {a.name} pottery", e.offer_text(x, None))
        self.assertTrue(e.start(b, {"do": "accept", "offer": x["id"]})[0])
        for _ in range(8):
            e.run_person(b)
            e.run_person(a)
        self.assertGreaterEqual(a.skill("pottery"), 0.3)

    def test_map_symbols_are_unique(self):
        syms = list(TERRAIN) + [v["sym"] for k, v in DEPOSITS.items() if k != "bog_iron"] + [v["sym"] for v in WILD.values()] + \
            [v["sym"] for v in BUILDINGS.values()]
        self.assertEqual(len(syms), len(set(syms)))


if __name__ == "__main__":
    unittest.main()
