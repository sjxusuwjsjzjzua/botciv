"""Founding a live world from a bots-only land of peoples (grand.md Phase 8, tools/found_world.py): the land as it
stands, its history kept, minds of their own in the seats, the Kaggle hours spent carried over."""
import json
import os
import tempfile
import unittest

from civ.realm import generate as found_realm
from civ.run import load, save
from tools.found_world import found


class FoundWorld(unittest.TestCase):
    def test_a_land_of_peoples_becomes_a_world_with_minds_seated(self):
        d = tempfile.mkdtemp()
        src, dst = os.path.join(d, "gw"), os.path.join(d, "w4")
        os.makedirs(src)
        w = found_realm({"seed": 3, "width": 64, "height": 64, "people": 120, "ai": 0})
        save(w, src)
        with open(os.path.join(src, "history.jsonl"), "w") as f:
            f.write('{"year": 1}\n')
        usage = os.path.join(d, "usage.json")
        with open(usage, "w") as f:
            json.dump({"runs": [[1, 30]], "failed": 0}, f)
        found(src, dst, 10, usage, "Test world")
        w2 = load(dst)
        minds = [p for p in w2.living() if p.mind == "llm"]
        self.assertEqual(len(minds), 10)
        self.assertEqual(w2.cfg["ai"], 10)
        self.assertEqual(w2.tick, w.tick)
        heads = {g.leader for g in w2.groups.values() if g.dissolved is None}
        self.assertTrue(heads & {p.id for p in minds})
        self.assertTrue(os.path.exists(os.path.join(dst, "history.jsonl")))
        self.assertEqual(json.load(open(os.path.join(dst, "kaggle_usage.json")))["runs"], [[1, 30]])
        self.assertIn("Test world", open(os.path.join(dst, "last_run.md")).read())


if __name__ == "__main__":
    unittest.main()
