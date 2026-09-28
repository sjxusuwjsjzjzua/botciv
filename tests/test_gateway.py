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

    def test_a_busy_preferred_model_hands_the_call_to_one_with_room(self):
        gw = G.Gateway(["gemini-3.1-flash-lite", "gemma-4-31b-it"])
        gw.stamps["gemini-3.1-flash-lite"] = [G.time.time()] * 20          # its minute is full
        calls = []
        def post(self_, m, body):
            calls.append(m)
            return reply(2000)
        with mock.patch.object(G.Gateway, "post", post):
            gw.generate("x" * 8000, {"type": "OBJECT"}, prefer="gemini-3.1-flash-lite")
        self.assertEqual(calls, ["gemma-4-31b-it"])

    def test_a_free_preferred_model_is_kept(self):
        gw = G.Gateway(["gemini-3.1-flash-lite", "gemma-4-31b-it"])
        calls = []
        with mock.patch.object(G.Gateway, "post", lambda s_, m, b: calls.append(m) or reply(2000)):
            gw.generate("x" * 8000, {"type": "OBJECT"}, prefer="gemma-4-31b-it")
        self.assertEqual(calls, ["gemma-4-31b-it"])

    def test_a_missing_model_is_dropped_and_another_answers(self):
        gw = G.Gateway(["gemma-9-nope", "gemma-4-31b-it"])
        missing = (404, {"error": {"status": "NOT_FOUND", "message": "no such model"}}, 0.1)
        with mock.patch.object(G.Gateway, "post", side_effect=[missing, reply(2000)]):
            out, meta = gw.generate("x" * 8000, {"type": "OBJECT"}, prefer="gemma-9-nope")
        self.assertEqual(meta["model"], "gemma-4-31b-it")
        self.assertIn("gemma-9-nope", gw.dropped)

    def test_a_spent_model_is_skipped_until_every_model_is(self):
        gw = G.Gateway(["gemini-3.1-flash-lite"])
        gw.today("gemini-3.1-flash-lite").update(spent=True, spent_at=G.time.time())
        with self.assertRaises(G.OutOfBudget):
            gw.generate("x", {"type": "OBJECT"})


if __name__ == "__main__":
    unittest.main()
