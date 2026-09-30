"""civ content hangs together: every input can be had, every workshop built, eras only rise."""
import unittest

from civ.content import problems, ITEMS, RECIPES, CRAFTS, BUILDINGS


class Content(unittest.TestCase):
    def test_no_problems(self):
        self.assertEqual(problems(), [])

    def test_big_enough(self):
        self.assertGreaterEqual(len(CRAFTS), 40)
        self.assertGreaterEqual(len(RECIPES), 100)
        self.assertGreaterEqual(len(BUILDINGS), 40)

    def test_every_era_has_crafts(self):
        self.assertEqual({v["era"] for v in CRAFTS.values()}, {0, 1, 2, 3, 4})


if __name__ == "__main__":
    unittest.main()
