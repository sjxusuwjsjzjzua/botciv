"""Towns in the engine (docs/towns_spec.md §5, WP2): a bots-only towns world is founded with its settlements laid out
on one tile each, runs, and stays sound (tools/town_check.py): one home a household, nothing on top of anything,
everyone where their tile is, no doing gone wrong."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import town_check  # noqa: E402

from civ.engine import Engine  # noqa: E402
from civ.minds.bot import BotMind  # noqa: E402
from civ.realm import generate  # noqa: E402
from civ.content.towns import zone  # noqa: E402


class TownsWorld(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.w = generate({"seed": 3, "people": 240, "width": 64, "height": 64, "format": "towns1"})
        cls.e = Engine(cls.w)
        mind = BotMind(cls.e)
        for _ in range(8 * 12):
            cls.e.tick(mind.decide)

    def test_founded_as_settlements(self):
        self.assertGreater(len(self.w.sites), 3)
        for s in self.w.sites.values():
            homes = [b for b in self.w.buildings_at(s.x, s.y) if zone(b.kind) == "dwelling"]
            self.assertTrue(homes, s.name)
            self.assertTrue(all(b.pos and b.site == s.id for b in homes))

    def test_sound_after_days(self):
        out, bad = town_check.check(self.w, self.e.log.events)
        self.assertEqual(bad, [], out)

    def test_people_in_metres(self):
        for p in self.w.living():
            self.assertIsNotNone(p.pos)
            self.assertEqual(self.w.tile_of(*p.pos), (p.x, p.y))


if __name__ == "__main__":
    unittest.main()
