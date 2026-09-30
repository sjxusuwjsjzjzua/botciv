"""Gateway rests after failures (2026-09-30): a quick 500 is a passing fault and rests the model
2 s; a server error still counts its prompt against the minute; a 429 does not."""
import os
import time
import unittest
from unittest import mock

from botciv import gateway as G


def err(code, dt):
    return code, {"error": {"message": "Internal error encountered."}}, dt


class GatewayRest(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-not-real"})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_quick_500s_rest_only_briefly(self):
        gw = G.Gateway(["gemma-4-31b-it"])
        day = gw.today("gemma-4-31b-it")
        for _ in range(6):
            gw.failed("gemma-4-31b-it", day, "500", quick=True)
        self.assertLess(gw.cool["gemma-4-31b-it"] - time.time(), 3)
        for _ in range(6):
            gw.failed("gemma-4-31b-it", day, "503")
        self.assertLessEqual(gw.cool["gemma-4-31b-it"] - time.time(), 61)
        gw.failed("gemma-4-31b-it", day, "timeout")
        self.assertGreater(gw.cool["gemma-4-31b-it"] - time.time(), 60)

    def test_a_500_keeps_its_tokens_in_the_tally(self):
        gw = G.Gateway(["gemma-4-31b-it"])
        with mock.patch.object(G.Gateway, "post", return_value=err(500, 1.0)), \
                mock.patch.object(G.Gateway, "pace", side_effect=lambda m, est: gw.tokens[m].append([time.time(), est]) or gw.tokens[m][-1]):
            gw.generate("x" * 3600, {"type": "OBJECT"})
        self.assertTrue(all(e[1] > 0 for e in gw.tokens["gemma-4-31b-it"]))


if __name__ == "__main__":
    unittest.main()
