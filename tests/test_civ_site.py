"""The viewer's site (format 3): built from a short bots-only run, then read by the viewer's own store
in Node (civ/viewer/core/test), when Node is at hand."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from civ import run, site


class TestSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp()
        cls.world = os.path.join(cls.tmp, "world")
        run.main(["--dir", cls.world, "--new", "--bots", "--size", "48", "--people", "40", "--ticks", "300", "--minutes", "5"])
        cls.out = os.path.join(cls.tmp, "site")
        cls.m, cls.i = site.build(cls.world, cls.out, "Test land")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_format_and_files(self):
        self.assertEqual(self.m["format"], 3)
        for f in ("manifest.json", "index.json", "index.html"):
            self.assertTrue(os.path.exists(os.path.join(self.out, f)), f)
        self.assertGreaterEqual(len(self.m["chunks"]), 2)
        for t0, t1, f in self.m["chunks"]:
            with open(os.path.join(self.out, f)) as fh:
                c = json.load(fh)
            self.assertEqual((c["t0"], c["t1"]), (t0, t1))
            self.assertTrue(c["land"] and c["land"][0]["t"] <= t0 + site.TPD)
            self.assertEqual(len(c["hours"][0][1][0]), 7)          # [id, x, y, health, fullness, verb, detail]

    def test_everyone_who_lived_is_known(self):
        ids = {p["id"] for p in self.m["people"]}
        for t0, t1, f in self.m["chunks"]:
            with open(os.path.join(self.out, f)) as fh:
                for h in json.load(fh)["hours"]:
                    self.assertTrue({q[0] for q in h[1]} <= ids)

    def test_the_viewers_store_reads_it(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("no node")
        here = os.path.join(os.path.dirname(__file__), "..", "civ", "viewer", "core", "test", "store.test.js")
        r = subprocess.run([node, "--test", here], env=dict(os.environ, SITE=self.out), capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout[-3000:] + r.stderr[-2000:])


if __name__ == "__main__":
    unittest.main()
