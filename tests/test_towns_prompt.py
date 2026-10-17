"""The prompt in a towns world (docs/towns_spec.md §8, WP4): one's settlement told by name, lanes named, within
budget, and never a word of the bookkeeping beneath (grid, cells, tiles, footprints, coordinates)."""
import re
import unittest

from civ.engine import Engine
from civ.minds.bot import BotMind
from civ.prompt import build_prompt
from civ.realm import generate

WORDS = r"\b(simulat\w*|agents?|game|turns?|ticks?|bots?|llm|language model|grid|cells?|tiles?|footprints?|coordinates?)\b"


class TownsPrompt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = generate({"seed": 3, "people": 160, "width": 56, "height": 56, "format": "towns1"})
        cls.e = Engine(cls.w)
        mind = BotMind(cls.e)
        for _ in range(4 * 12):
            cls.e.tick(mind.decide)

    def test_settlements_and_lanes_named(self):
        for s in self.w.sites.values():
            self.assertTrue(s.name and "'s place" not in s.name, s.name)
            self.assertTrue(all(l.get("name") for l in s.lanes if l["kind"] != "path"), s.name)

    def test_budget_words_and_settlement(self):
        told = 0
        for p in [q for q in self.w.living() if q.adult(self.w.tick)][:30]:
            text = build_prompt(self.e, p)
            lord = bool(self.e.followers(p))                  # a lord's prompt orders people: in the plain world too it runs to 11,400
            self.assertLess(len(text), 12600 if lord else 12000, p.name)
            self.assertIsNone(re.search(WORDS, text, re.I), re.findall(WORDS, text, re.I)[:3])
            told += "You live in " in text
        self.assertGreater(told, 20)

    def test_a_building_named_in_words(self):
        w, exe = self.w, self.e
        p = next(q for q in w.living() if q.home in w.buildings and w.buildings[q.home].done)
        home = w.buildings[p.home]
        self.assertIs(exe.building_named(p, "my house"), home)
        self.assertIs(exe.building_named(p, f"{p.name}'s {home.kind}"), home)
        self.assertIsNone(exe.building_named(p, "my dragon"))


if __name__ == "__main__":
    unittest.main()
