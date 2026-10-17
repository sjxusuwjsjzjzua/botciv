"""Re-founding a world as a towns world on the large land (towns_spec §10, civ/refound.py): everyone kept and housed,
households kept together under one roof, kin, groups, skills and seats kept, places in memory doubled, each cluster of
homes a settlement, and the new world runs sound (tools/town_check.py)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import town_check  # noqa: E402

from civ.engine import Engine  # noqa: E402
from civ.minds.bot import BotMind  # noqa: E402
from civ.realm import generate  # noqa: E402
from civ.refound import K, double_text, refound  # noqa: E402


class Refound(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        w = generate({"seed": 4, "people": 160, "width": 64, "height": 64, "ai": 6})
        e = Engine(w)
        m = BotMind(e)
        for _ in range(4 * 12):
            e.tick(m.decide)
        someone = next(p for p in w.living() if p.adult(w.tick))
        someone.memory = "My store is at (10,12)."
        cls.mem = someone.id
        cls.old = w
        cls.w, cls.rep = refound(w.to_dict())

    def test_everyone_kept_and_housed(self):
        old, w = self.old, self.w
        self.assertEqual({p.id for p in old.living()}, {p.id for p in w.living()})
        housed_before = sum(1 for p in old.living() if p.home)
        self.assertGreaterEqual(sum(1 for p in w.living() if p.home), housed_before)
        for p in w.living():
            o = old.people[p.id]
            self.assertEqual((p.partner, p.parents, p.groups, p.skills, p.mind), (o.partner, o.parents, o.groups, o.skills, o.mind))
            self.assertEqual(p.inv, o.inv)

    def test_households_under_one_roof(self):
        old, w = self.old, self.w
        for o in old.living():
            q = old.people.get(o.partner) if o.partner else None
            if q and q.alive and o.home and o.home == q.home:
                self.assertEqual(w.people[o.id].home, w.people[q.id].home)

    def test_the_land_doubled_and_settled(self):
        w = self.w
        self.assertTrue(w.towns)
        self.assertEqual((w.w, w.h), (self.old.w * K, self.old.h * K))
        self.assertGreater(self.rep["settlements"], 0)
        for p in w.living():
            b = w.buildings.get(p.home)
            if b:
                self.assertIsNotNone(b.pos)
                self.assertIsNotNone(w.site_of(b.x, b.y))

    def test_memory_keeps_its_places(self):
        self.assertEqual(self.w.people[self.mem].memory, f"My store is at ({10 * K},{12 * K}).")
        self.assertEqual(double_text("at (3, 4) and (5,6)"), f"at ({3 * K},{4 * K}) and ({5 * K},{6 * K})")

    def test_the_dead_kept(self):
        """The latest graves and cairns among a settlement's homes lie in its burial ground, names kept."""
        old_names = {b.name for b in self.old.buildings.values() if b.kind in ("grave", "cairn")}
        new = [b for b in self.w.buildings.values() if b.kind in ("grave", "cairn")]
        self.assertTrue(all(b.name in old_names for b in new))
        for b in new:
            plot = next((q for q in self.w.sites[b.site].plots if q["id"] == b.plot), None) if b.site in self.w.sites else None
            self.assertTrue(plot is None or plot["kind"] == "burial")

    def test_runs_sound(self):
        w = self.w
        e = Engine(w)
        m = BotMind(e)
        seats = {p.id: p.mind for p in w.living()}
        for p in w.living():
            p.mind = "bot"
        for _ in range(2 * 12):
            e.tick(m.decide)
        for p in w.people.values():
            p.mind = seats.get(p.id, p.mind)
        out, bad = town_check.check(w, e.log.events)
        self.assertEqual(bad, [], out)


if __name__ == "__main__":
    unittest.main()
