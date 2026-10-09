"""c79 (grand world, Phase 6): rites. Each people keeps a rite on a day of its festival season, at a shrine or
temple of its own near its head's home, or else at that home; word goes round at dawn; those there through the
day have kept it, and trust one another and their host more; food in the store there is shared as a feast. Bots
of the people mostly go. The prompt says when it falls and where."""
import unittest

from civ.content.peoples import PEOPLES
from civ.engine import Engine
from civ.minds.bot import BotMind
from civ.prompt import build_prompt
from civ.realm import generate as found_realm
from civ.world import DPS, TPD, World


class C79(unittest.TestCase):
    def setUp(self):
        self.w = found_realm({"seed": 2, "width": 96, "height": 96, "people": 300, "ai": 0})
        self.e = Engine(self.w)
        self.k = next(k for k in self.w.peoples if PEOPLES[k].get("rite"))
        name, day = PEOPLES[self.k]["rite"]
        season = ["spring", "summer", "autumn", "winter"].index(PEOPLES[self.k]["festival"])
        self.w.tick = (season * DPS + day) * TPD          # dawn of the rite's day, year 0

    def test_a_rite_is_called_kept_and_bonds_those_who_came(self):
        w, e, k = self.w, self.e, self.k
        e.rites_dawn()
        r = w.rites[k]
        folk = [p for p in w.living() if p.people == k and p.adult(w.tick)][:6]
        for p in folk:
            w.place(p, r["x"], r["y"])
            p.act, p.intent = {"do": "wait", "left": 12}, {"goal": "", "plan": []}
        a = folk[0]
        before = sum(r.get("trust", 0) for r in a.rel.values())
        for _ in range(9):
            e.tick(lambda people: {})
        self.assertTrue(r.get("done"))
        self.assertIn("festival", {x["kind"] for x in e.log.events})
        self.assertGreater(sum(r.get("trust", 0) for r in a.rel.values()), before)
        self.assertIn(k, World.from_dict(w.to_dict()).rites)

    def test_bots_go_and_the_prompt_tells_of_it(self):
        w, e, k = self.w, self.e, self.k
        e.rites_dawn()
        r = w.rites[k]
        p = next(p for p in w.living() if p.people == k and p.adult(w.tick) and 3 < max(abs(p.x - r["x"]), abs(p.y - r["y"])) <= 25)
        p.traits["sociability"] = 1.0
        p.satiety = 15
        bot = BotMind(e)
        goals = [bot.rite(p) for _ in range(5)]
        self.assertTrue(any(g and g["plan"][0]["do"] == "go" for g in goals))
        p.mind = "llm"
        self.assertIn(f"Today is {r['name']}", build_prompt(e, p))
        w.tick -= 3 * TPD
        w.rites = {}
        self.assertIn("is in 3 days", build_prompt(e, p))


if __name__ == "__main__":
    unittest.main()
