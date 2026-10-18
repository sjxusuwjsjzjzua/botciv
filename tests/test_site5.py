"""world5's viewer of a whole towns world (civ/site5.py): the hourly frames carry where each person stands in metres
(null indoors), and the site holds the whole land, every settlement and the hours, in metres inside the land."""
import gzip
import json
import os
import tempfile
import unittest

from civ import run, site5
from civ.engine import Engine
from civ.minds.bot import BotMind
from civ.realm import generate
from civ.world import TILE_M


class Site5(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = cls.d = os.path.join(cls.tmp.name, "world")
        os.makedirs(os.path.join(d, "log"))
        w = cls.w = generate({"seed": 5, "people": 80, "width": 40, "height": 40, "format": "towns1"})
        e = Engine(w)
        mind = BotMind(e)
        cls.frames = []
        for _ in range(4):
            e.tick(mind.decide)
            cls.frames.append(run.frame(w))
        with gzip.open(os.path.join(d, "log", "frames-0.jsonl.gz"), "wt") as f:
            for fr in cls.frames:
                f.write(json.dumps(fr) + "\n")
        run.save(w, d)
        cls.out = os.path.join(cls.tmp.name, "site")
        site5.build(d, cls.out, "test")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_frames_carry_metres(self):
        rows = self.frames[-1]["p"]
        self.assertTrue(all(len(r) == 8 for r in rows))
        out = [r for r in rows if r[7]]
        self.assertTrue(out)
        for r in out:                       # where one stands lies on one's tile
            self.assertEqual((int(r[7][0] // TILE_M), int(r[7][1] // TILE_M)), (r[1], r[2]))

    def test_site(self):
        live = os.path.join(self.out, "live")
        with open(os.path.join(live, "land.json")) as f:
            L = json.load(f)
        with open(os.path.join(live, "hours.json")) as f:
            H = json.load(f)
        self.assertEqual(L["format"], "world5-live-1")
        self.assertEqual(len(L["land"]["tiles"]), self.w.h)
        self.assertEqual({s["id"] for s in L["sites"]}, set(self.w.sites))
        for s in L["sites"]:
            self.assertTrue(os.path.exists(os.path.join(live, "s", f"{s['id']}.json")))
        self.assertEqual([h[0] for h in H["hours"]], [fr["t"] for fr in self.frames])
        W, Hh = L["land"]["box"][2], L["land"]["box"][3]
        for _, row in H["hours"]:
            for r in row:
                if len(r) > 1:
                    self.assertTrue(0 <= r[1] < W and 0 <= r[2] < Hh)
        self.assertEqual(set(H["people"]), {str(p.id) for p in self.w.living()})
        self.assertTrue(os.path.exists(os.path.join(self.out, "world5.html")))
        self.assertTrue(os.path.exists(os.path.join(self.out, "demo", "live.js")))


if __name__ == "__main__":
    unittest.main()
