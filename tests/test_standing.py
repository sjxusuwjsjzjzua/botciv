import unittest

from botciv import config
from botciv.engine import Engine
from botciv.log import Log
from botciv.log import read
from botciv.standing import gini, standing, worth
from botciv.world import World, Structure, Group


class TestStanding(unittest.TestCase):
    def test_gini(self):
        self.assertEqual(gini([5, 5, 5, 5]), 0.0)
        self.assertGreater(gini([0, 0, 0, 100]), 0.7)
        self.assertEqual(gini([]), 0.0)

    def test_worth_counts_goods_stores_buildings_and_followers(self):
        w = World(config.load(overrides={"world": {"seed": 2}})).generate()
        a, b, c = w.living()[:3]
        a.inventory = {"berries": 4, "spear": 1}
        self.assertEqual(worth(a.inventory), 10)
        w.structures[900] = Structure(id=900, kind="store", x=0, y=0, owner=a.id, done=True, inventory={"meat": 2})
        w.groups[901] = Group(id=901, name="Kin", founder=a.id, leader=a.id, members=[a.id, b.id, c.id], rules="")
        wealth, followers = standing(w, a)
        self.assertEqual((wealth, followers), (10 + 5 + 8, 2))

    def test_census_is_logged_once_a_day(self):
        import tempfile, os
        w = World(config.load(overrides={"world": {"seed": 2}})).generate()
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "events.jsonl.gz")
            log = Log(p)
            e = Engine(w, log)
            for _ in range(2 * w.tpd()):
                e.tick(lambda ask: {})
            log.close()
            census = [ev for ev in read(p) if ev["kind"] == "census"]
        self.assertEqual(len(census), 2)
        self.assertEqual(len(census[0]["c"]), len(w.living()))
        self.assertFalse(any(ev["kind"] == "census" for ev in log.recent))


if __name__ == "__main__":
    unittest.main()
