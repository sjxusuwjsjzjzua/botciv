"""c87: settlements recognised: hamlets, villages and towns, named from the places among them."""
import unittest

from civ.census import clusters, settlements
from civ.engine import Engine
from civ.gen import generate
from civ.prompt import build_prompt
from civ.world import Building


class C87(unittest.TestCase):
    def setUp(self):
        self.w = w = generate({"seed": 5, "people": 40, "width": 60, "height": 60, "bands": 1, "ai": 0})
        self.e = Engine(w)
        self.folk = [p for p in w.living()][:32]
        for i, p in enumerate(self.folk):
            b = Building(id=w.new_id(), kind="shelter", x=20 + i % 6, y=20 + i // 6, owner=p.id, done=True)
            w.buildings[b.id] = b
            w.at[f"{b.x},{b.y}"] = b.id
            p.home = b.id
        w.places.append([22, 22, "Wadeby", self.folk[0].id, 0])

    def test_clusters_agree_with_the_old_sizes(self):
        self.assertEqual(sorted((len(c["people"]) for c in clusters(self.w)), reverse=True), settlements(self.w))

    def test_a_village_named_and_seen_at_home(self):
        self.e.settlements_day()
        s = self.w.settlement_of[self.folk[3].id]
        self.assertEqual((s["name"], s["kind"]), ("Wadeby", "town"))      # 32 people, none farming
        self.assertIn("in Wadeby, a town of", build_prompt(self.e, self.folk[3]))
        self.assertTrue(any(ev["kind"] == "town" for ev in self.e.log.events))
        self.e.settlements_day()
        self.assertEqual(sum(1 for ev in self.e.log.events if ev["kind"] == "town"), 1)   # news once


if __name__ == "__main__":
    unittest.main()
