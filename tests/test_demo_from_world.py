"""A real towns world's settlement exported for step 0's viewer (tools/demo_from_world.py): the demo's data format,
only kinds the art kit draws, people numbered as folk.js reads them, the scene where the demo's cameras look."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
import demo_from_world as D  # noqa: E402

from civ.engine import Engine  # noqa: E402
from civ.minds.bot import BotMind  # noqa: E402
from civ.realm import generate  # noqa: E402

KIT = {"long_house", "stilt_store", "well", "shrine", "kiln", "grave_stone", "plank_bridge", "conical_hut", "fire", "drying_rack"}


class Export(unittest.TestCase):
    def test_a_settlement_as_the_demo_reads_it(self):
        w = generate({"seed": 3, "people": 160, "width": 56, "height": 56, "format": "towns1"})
        e = Engine(w)
        m = BotMind(e)
        for _ in range(3 * 12):
            e.tick(m.decide)
        site = max(w.sites.values(), key=lambda s: len(s.plots))
        d = D.export(w, site)
        for k in ("land", "lanes", "plots", "buildings", "fields", "people", "animals", "green", "walker", "centre"):
            self.assertIn(k, d)
        self.assertTrue(set(b["kind"] for b in d["buildings"]) <= KIT)
        self.assertEqual(sum(b["kind"] == "well" for b in d["buildings"]), 1)
        self.assertEqual([p["id"] for p in d["people"]], list(range(len(d["people"]))))
        self.assertEqual(sum(l["kind"] == "track" for l in d["lanes"]), 1)
        cx, cy = d["centre"]
        self.assertTrue(1000 <= cx <= 2000 and 1000 <= cy <= 2000, d["centre"])
        H = d["land"]["heights"]
        self.assertEqual((len(H["h"]), len(H["h"][0])), (H["ny"], H["nx"]))


if __name__ == "__main__":
    unittest.main()
