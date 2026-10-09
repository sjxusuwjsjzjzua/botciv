"""c60 (P1): the prompt within its budget. Rules and step help said shortly; steps shown only to those who can
use them (herding, trade, teaching, writing); the news of one time of day on one line, the same news once.
(W1) A tablet pressed by hand when no kiln is free; a routine leaves out a step refused twice running.
(C4) A craft waits for one's own firing (copper, then tin, then bronze in one furnace)."""
import unittest

from civ.content import BUILDINGS
from civ.engine import Engine
from civ.gen import generate
from civ.minds.bot import BotMind
from civ.prompt import build_prompt, compact_events
from civ.world import TPD, Building


def place(w, kind, owner, near, r=3):
    x, y = next((x, y) for x, y in w.beside(near.x, near.y, r)
                if w.passable(x, y) and not w.building_at(x, y) and (x, y) != (near.x, near.y))
    b = Building(id=w.new_id(), kind=kind, x=x, y=y, owner=owner, done=True, hp=BUILDINGS[kind]["hp"])
    w.buildings[b.id] = b
    w.at[f"{x},{y}"] = b.id
    return b


class C60(unittest.TestCase):
    def test_p95_of_a_grown_land_within_budget(self):
        # world2's prompts run about 3 characters a token: 10,500 characters is the 3,500-token budget
        w = generate({"seed": 7, "people": 80, "width": 64, "height": 64, "bands": 4, "ai": 0})
        e = Engine(w)
        m = BotMind(e)
        for _ in range(TPD * 30):
            e.tick(m.decide)
        n = sorted(len(build_prompt(e, p)) for p in w.living() if p.adult(w.tick))
        self.assertLessEqual(n[int(len(n) * 0.95) - 1], 10500)
        self.assertLessEqual(n[-1], 12000)

    def test_steps_only_for_those_who_can_use_them(self):
        w = generate({"seed": 4, "people": 12, "width": 40, "height": 40, "bands": 2, "ai": 0})
        e = Engine(w)
        p = next(q for q in w.living() if q.adult(w.tick))
        w.herds = []
        p.skills.pop("herding", None)
        text = build_prompt(e, p)
        self.assertNotIn("- tame:", text)
        place(w, "pen", p.id, p)
        self.assertIn("- tame:", build_prompt(e, p))
        self.assertNotIn("- post:", build_prompt(e, p))
        place(w, "store", p.id, p)
        self.assertIn("- post:", build_prompt(e, p))

    def test_news_of_one_hour_on_one_line_and_said_once(self):
        ev = [(5, "Lorus is reaping your field at 41,20."), (5, "Lorus is reaping your field at 41,20."), (6, "Brer gave you 2 berries.")]
        self.assertEqual(len(compact_events(ev, "Tath")), 2)
        w = generate({"seed": 4, "people": 12, "width": 40, "height": 40, "bands": 2, "ai": 0})
        e = Engine(w)
        p = next(q for q in w.living() if q.adult(w.tick))
        p.events = [(w.tick, "Brer gave you 2 berries."), (w.tick, "Mearrea gave you 11 wood.")]
        self.assertIn("Brer gave you 2 berries. Mearrea gave you 11 wood.", build_prompt(e, p))


    def small(self):
        w = generate({"seed": 4, "people": 12, "width": 40, "height": 40, "bands": 2, "ai": 0})
        e = Engine(w)
        p = next(q for q in w.living() if q.adult(w.tick))
        p.act, p.intent = None, {"goal": "", "plan": []}
        return w, e, p

    def test_a_tablet_by_hand_when_no_kiln_is_free(self):
        w, e, p = self.small()
        p.skills["pottery"] = 0.5
        p.inv.update({"clay": 4, "wood": 2})
        self.assertIs(e.start(p, {"do": "craft", "item": "tablet"})[0], True)
        self.assertEqual(p.act["do"], "craft")

    def test_a_routine_leaves_out_a_step_refused_twice(self):
        w, e, p = self.small()
        w.herds = []
        e.adopt(p, {"goal": "hunt", "plan": [{"do": "hunt", "animal": "deer"}, {"do": "wait", "hours": 1}], "routine": True})
        for _ in range(12):
            e.run_person(p)
            if p.act and p.act["do"] == "wait":
                p.act = None
        self.assertEqual([s["do"] for s in p.intent["orig"]], ["wait"])

    def test_a_craft_waits_for_ones_own_firing(self):
        w, e, p = self.small()
        p.skills.update({"pottery": 0.5, "charcoal_burning": 0.5, "smelting": 0.9})
        f = place(w, "furnace", p.id, p)
        f.process = {"recipe": next(i for i, r in enumerate(__import__("civ.content", fromlist=["RECIPES"]).RECIPES) if r["out"] == "copper"),
                     "done_at": w.tick + 4, "by": p.id, "runs": 1, "ok": True}
        p.inv.update({"tin_ore": 2, "charcoal": 2})
        p.intent = {"goal": "", "plan": []}
        self.assertIs(e.start(p, {"do": "craft", "item": "tin"})[0], True)
        self.assertEqual(p.act["do"], "wait")
        self.assertEqual(p.intent["plan"][0]["item"], "tin")


if __name__ == "__main__":
    unittest.main()
