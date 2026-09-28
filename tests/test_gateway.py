import os
import unittest
from unittest import mock

from botciv import gateway as G


def reply(n_in):
    return 200, {"candidates": [{"content": {"parts": [{"text": "{\"ok\": true}"}]}}],
                 "usageMetadata": {"promptTokenCount": n_in, "candidatesTokenCount": 10}}, 0.1


class TestGateway(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"GEMINI_API_KEY": "test-key-not-real"})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_pacing_counts_the_real_prompt_tokens(self):
        gw = G.Gateway(["gemma-4-31b-it"])
        with mock.patch.object(G.Gateway, "post", return_value=reply(2500)):
            out, meta = gw.generate("x" * 10000, {"type": "OBJECT"})
        self.assertEqual(out, {"ok": True})
        self.assertEqual(gw.tokens["gemma-4-31b-it"][0][1], 2500)
        self.assertGreater(gw.cpt["gemma-4-31b-it"], 3.6)       # 4 characters a token: the estimate moves up
        self.assertLess(gw.cpt["gemma-4-31b-it"], 4.0)

    def test_token_limit_is_learned_from_a_429(self):
        gw = G.Gateway(["gemma-4-31b-it"])
        limited = (429, {"error": {"status": "RESOURCE_EXHAUSTED", "details": [
            {"@type": "type.googleapis.com/google.rpc.QuotaFailure",
             "violations": [{"quotaId": "GenerateContentInputTokensPerModelPerMinute-FreeTier", "quotaValue": "16000"}]},
            {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "0s"}]}}, 0.1)
        with mock.patch.object(G.Gateway, "post", side_effect=[limited, reply(2000)]), mock.patch.object(G.time, "sleep"):
            out, _ = gw.generate("x" * 8000, {"type": "OBJECT"})
        self.assertEqual(out, {"ok": True})
        self.assertEqual(gw.tpm["gemma-4-31b-it"], 15200)


if __name__ == "__main__":
    unittest.main()
