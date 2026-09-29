"""Rules w27: a full store says so, and putting into it is refused at once with what it holds."""
import unittest

from botciv.engine import Engine
from botciv.log import NullLog
from botciv.prompt import build_prompt
from botciv.world import Structure
from tests.test_engine import world, open_tile, place


class W27(unittest.TestCase):
    def test_full_store(self):
        w = world(1)
        e = Engine(w, NullLog())
        a = w.living()[0]
        x, y = open_tile(w)
        place(w, a, x, y)
        sid = w.new_id()
        s = Structure(id=sid, kind="store", x=x, y=y, owner=a.id, done=True)
        s.inventory = {"wood": 30}
        w.structures[sid] = s
        a.inventory = {"wood": 3}
        ok, msg = e.start(a, {"verb": "put", "item": "wood", "qty": 3})
        self.assertFalse(ok)
        self.assertIn("full (it holds wood 30)", msg)
        self.assertIn("(full)", build_prompt(e, a))


if __name__ == "__main__":
    unittest.main()
