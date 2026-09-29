import os
import unittest
from unittest import mock

from botciv import gateway
from botciv.gateway import Gateway, compact

SCHEMA = {"type": "OBJECT", "properties": {
    "thought": {"type": "STRING"},
    "action": {"type": "OBJECT", "properties": {"verb": {"type": "STRING", "enum": ["go", "rest"]},
                                                 "give": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
                                                     "item": {"type": "STRING"}, "qty": {"type": "INTEGER"}}}}}}}}
M = "groq:openai/gpt-oss-120b"
FAKE = "gsk_" + "a1B2c3D4" * 5          # built in pieces so the key scan never sees a whole one


class Fake(Gateway):
    def __init__(self, replies):
        with mock.patch.dict(os.environ, {"GEMINI_API_KEY": "x", "GROQ_API_KEY": FAKE}):
            super().__init__([M])
        self.replies, self.sent = list(replies), []

    def post_groq(self, m, body):
        self.sent.append(body)
        return self.replies.pop(0)


def ok(text, hdr=None):
    return 200, {"model": "openai/gpt-oss-120b", "choices": [{"message": {"content": text}}],
                 "usage": {"prompt_tokens": 3300, "completion_tokens": 120}, "_headers": hdr or {}}, 0.4


class GroqTests(unittest.TestCase):
    def test_compact_schema(self):
        c = compact(SCHEMA)
        self.assertIn('"verb": one of go|rest', c)
        self.assertIn('"give": [{"item": string, "qty": integer}]', c)
        self.assertLess(len(c), 400)

    def test_reply_is_parsed_and_limits_learned(self):
        g = Fake([ok('{"thought": "hi", "action": {"verb": "rest"}}', {"x-ratelimit-limit-tokens": "10000"})])
        out, meta = g.generate("a prompt", SCHEMA)
        self.assertEqual(out["action"]["verb"], "rest")
        self.assertEqual((meta["model"], meta["in"], meta["out"]), (M, 3300, 120))
        self.assertEqual(g.tpm[M], 9000)
        body = g.sent[0]
        self.assertEqual(body["model"], "openai/gpt-oss-120b")
        self.assertEqual(body["reasoning_effort"], "low")
        self.assertEqual(body["messages"][1]["content"], "a prompt")
        self.assertNotIn("simulat", body["messages"][0]["content"].lower())

    def test_per_day_429_marks_spent_and_per_minute_rests(self):
        day = (429, {"error": {"message": "Rate limit reached ... on tokens per day (TPD): try again in 3h2m1.5s"},
                     "_headers": {}}, 0.1)
        g = Fake([day])
        out, meta = g.generate("p", SCHEMA)
        self.assertIsNone(out)
        self.assertTrue(g.today(M)["spent"])
        minute = (429, {"error": {"message": "Rate limit reached ... on tokens per minute (TPM): Please try again in 200ms"},
                        "_headers": {}}, 0.1)
        g = Fake([minute, ok('{"thought": "x"}')])
        out, meta = g.generate("p", SCHEMA)
        self.assertEqual(out["thought"], "x")
        self.assertFalse(g.today(M)["spent"])

    def test_key_never_appears_in_errors(self):
        bad = (401, {"error": {"message": f"Invalid API Key {FAKE}"}, "_headers": {}}, 0.1)
        g = Fake([bad] * 3)
        out, meta = g.generate("p", SCHEMA)
        self.assertIsNone(out)
        self.assertNotIn(FAKE, str(meta))

    def test_discovery_takes_chat_models_largest_first(self):
        from botciv.run import discover_groq
        listed = ["canopylabs/orpheus-v1-english", "openai/gpt-oss-safeguard-20b", "whisper-large-v3-turbo",
                  "allam-2-7b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b", "openai/gpt-oss-120b",
                  "meta-llama/llama-prompt-guard-2-86m"]
        g = Fake([])
        g.list_groq = lambda: listed
        found = discover_groq(g)
        self.assertEqual(found, ["groq:openai/gpt-oss-120b", "groq:qwen/qwen3.8-27b", "groq:openai/gpt-oss-20b"])
        self.assertEqual(g.body_for(found[1], "p", SCHEMA, 1.0)["reasoning_effort"], "none")

    def test_groq_models_are_never_a_persons_home(self):
        from botciv.run import assign_models
        from botciv import config
        from botciv.world import World
        w = World(config.load()).generate()
        assign_models(w, ["gemini-3.5-flash-lite", M, "gemma-4-31b-it"])
        self.assertTrue(all(a.model == "gemini-3.5-flash-lite" for a in w.agents.values() if a.mind == "gemini"))


if __name__ == "__main__":
    unittest.main()
