"""Rules w24: speech wakes someone busy with a task less often than someone standing idle."""
import unittest

from botciv.engine import Engine
from botciv.log import NullLog
from tests.test_engine import world


class W24(unittest.TestCase):
    def setUp(self):
        self.w = world(1)
        self.e = Engine(self.w, NullLog())
        self.o = self.w.living()[0]
        self.o.last_speech_wake, self.o.last_decided, self.o.wake = -99, -99, []
        self.w.tick = 100

    def woken_at(self, ticks):
        out = []
        for t in ticks:
            self.w.tick = t
            self.o.wake = []
            self.e.speech_wake(self.o, "X spoke to you")
            out.append(bool(self.o.wake))
        return out

    def test_idle_listener_every_three_hours(self):
        self.o.activity = None
        self.assertEqual(self.woken_at([100, 103, 106]), [True, True, True])

    def test_busy_listener_every_six_hours(self):
        self.o.activity = {"verb": "gather", "left": 20}
        self.assertEqual(self.woken_at([100, 103, 106]), [True, False, True])


if __name__ == "__main__":
    unittest.main()
