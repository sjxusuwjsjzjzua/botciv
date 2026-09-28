"""A quick bots-only smoke test of the whole world: every kind of mind for a year
across two seeds, with the features the careful and the greedy use actually used."""
import unittest

from tools.balance import run


class Smoke(unittest.TestCase):
    def test_a_mixed_world_runs_a_year_and_uses_its_features(self):
        for seed in (1, 2):
            r = run(seed, 1, "mixed", {})
            self.assertFalse(r["extinct"], f"seed {seed} died out")
            self.assertGreater(r["builds"].get("farm", 0), 0, "no farm was built")
            self.assertGreater(r["plant"], 0, "nothing was sown")
            self.assertGreater(r["steal"], 0, "no one stole")
            self.assertGreater(r["builds"].get("store", 0), 0, "no store was built")


if __name__ == "__main__":
    unittest.main()
