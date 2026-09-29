"""Rules w29: food given to a hungry person who cannot carry it is eaten on the spot."""
import unittest

from botciv.engine import Engine
from botciv.log import NullLog
from tests.test_engine import world, place


class W29(unittest.TestCase):
    def test_a_full_load_does_not_stop_a_starving_person_eating_a_gift(self):
        w = world(1)
        e = Engine(w, NullLog())
        a, o = w.living()[:2]
        place(w, a, 3, 3)
        place(w, o, 3, 4)
        a.inventory = {"berries": 5}
        o.inventory = {"wood": 10}           # a load of 20: nothing more can be carried
        o.satiety = 1
        e.set_act(a, "give", to=o.id, item="berries", qty=5, left=1)
        st, msg = e.do_give(a, a.activity)
        self.assertEqual(st, "done")
        self.assertGreater(o.satiety, 1)
        self.assertEqual(o.inventory.get("berries", 0), 0)


if __name__ == "__main__":
    unittest.main()
