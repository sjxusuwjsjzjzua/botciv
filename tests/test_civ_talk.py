"""Bot people answer what is said to them, and act on it."""
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.minds.bot import BotMind


def pair():
    w = generate({"seed": 3, "people": 12, "width": 32, "height": 32, "bands": 2, "ai": 0})
    e = Engine(w)
    a, b = [p for p in w.living() if p.adult(w.tick)][:2]
    w.place(b, a.x + 1, a.y)
    a.mind = "llm"
    a.inv.clear()
    b.inv.clear()
    b.satiety = 18
    return w, e, BotMind(e), a, b


class BotsAnswer(unittest.TestCase):
    def hear(self, e, m, a, b, words):
        e.speak(a, words, b.name)
        return m.one(b)

    def test_a_trade_asked_for_is_offered(self):
        w, e, m, a, b = pair()
        b.inv["grain"] = 10
        a.inv["flax"] = 6
        got = self.hear(e, m, a, b, "Can we trade some flax for your grain?")
        step = got["plan"][0]
        self.assertEqual(step["do"], "propose")
        self.assertIn("grain", step["give"])
        self.assertIn("flax", step["get"])
        self.assertIn("grain", got["say"])

    def test_the_hungry_are_fed_or_told_why_not(self):
        w, e, m, a, b = pair()
        b.inv["smoked_meat"] = 8
        b.traits["generosity"] = 1.0
        got = self.hear(e, m, a, b, "I am starving, could you spare some food?")
        self.assertEqual(got["plan"][0]["do"], "give")
        w, e, m, a, b = pair()
        got = self.hear(e, m, a, b, "I am starving, could you spare some food?")
        self.assertTrue(got["say"])
        self.assertFalse(got.get("replace", True))         # words only: what one was doing goes on

    def test_a_lesson_asked_for_is_given(self):
        w, e, m, a, b = pair()
        b.skills["pottery"], a.skills["pottery"] = 0.8, 0.0
        got = self.hear(e, m, a, b, "Will you teach me to make pots?")
        self.assertEqual(got["plan"][0], {"do": "teach", "to": a.name, "craft": "pottery"})

    def test_bots_do_not_chatter_forever(self):
        w, e, m, a, b = pair()
        a.mind = "bot"
        said = 0
        e.speak(a, "How do you fare?", b.name)
        for _ in range(12):
            for p, o in ((b, a), (a, b)):
                got = m.talk.converse(p)
                if got and got.get("say"):
                    said += 1
                    e.speak(p, got["say"], got.get("to"))
        self.assertLessEqual(said, 2)


if __name__ == "__main__":
    unittest.main()
