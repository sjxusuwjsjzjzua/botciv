import json
import os
import tempfile
import unittest

from botciv import site


class ReplaySnapshots(unittest.TestCase):
    def test_every_file_starts_from_the_full_picture(self):
        n = site.CHUNK + 5
        frames = [{"t": t, "kind": "frame", "p": [[1, 0, 0, 10, 10, ""], [2, 1, 1, 10, 10, ""]], "h": [], "w": [],
                   "s": []} for t in range(n)]
        frames[0]["s"] = [[1, {"berries": 2}, 2.0, 0, []], [2, {}, 0.0, 0, []]]
        frames[site.CHUNK + 2]["s"] = [[1, {"berries": 5}, 5.0, 0, [3]]]
        with tempfile.TemporaryDirectory() as d:
            site.write_replay(d, frames, [])
            a = json.load(open(os.path.join(d, "replay", "0.json")))["frames"]
            b = json.load(open(os.path.join(d, "replay", "1.json")))["frames"]
        self.assertEqual(len(a[0][4]), 2)
        self.assertEqual(a[1][4], [])
        self.assertEqual(sorted(r[0] for r in b[0][4]), [1, 2])       # full at the start of a file
        self.assertEqual(b[0][4][0][1], {"berries": 2})
        self.assertEqual(b[2][4], [[1, {"berries": 5}, 5.0, 0, [3]]])  # then only changes


if __name__ == "__main__":
    unittest.main()
