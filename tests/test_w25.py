"""Rules w25: words from outside the world are never kept or shown; such an answer is set aside."""
import unittest

from botciv.engine import Engine, out_of_world
from botciv.log import NullLog
from botciv.prompt import build_prompt
from tests.test_engine import world


class W25(unittest.TestCase):
    def setUp(self):
        self.w = world(1)
        self.e = Engine(self.w, NullLog())
        self.a = self.w.living()[0]

    def test_the_words(self):
        self.assertTrue(out_of_world("I am an efficient assistant capable of writing code"))
        self.assertTrue(out_of_world("The user is asking about history"))
        self.assertFalse(out_of_world("I will gather berries with Feal before winter"))

    def test_nothing_from_outside_is_kept(self):
        self.a.self_view, self.a.memory = "", "old notes"
        self.e.apply_decision(self.a, {"thought": "I should hunt.", "action": {"verb": "wait"},
                                       "memory": "As an AI language model I keep notes", "self": "I am a helpful assistant"})
        self.assertEqual((self.a.self_view, self.a.memory), ("", "old notes"))

    def test_an_answer_from_outside_is_set_aside(self):
        self.a.activity = {"verb": "gather", "left": 5, "item": "berries"}
        self.e.apply_decision(self.a, {"thought": "The user is asking about a war.", "action": {"verb": "attack", "target": "x"},
                                       "speech": {"text": "Hello user"}})
        self.assertEqual(self.a.activity.get("verb"), "gather")

    def test_what_slipped_in_before_is_not_shown(self):
        self.a.self_view = "I am an efficient assistant capable of writing and executing code"
        self.a.memory = "The user wants a summary"
        p = build_prompt(self.e, self.a)
        self.assertNotIn("assistant", p)
        self.assertNotIn("The user wants", p)


if __name__ == "__main__":
    unittest.main()


class W25Wider(unittest.TestCase):
    def test_computing_and_the_real_world(self):
        from botciv.engine import assistant_mode
        for t in ("Automate data extraction from web pages using Node.js and Cheerio.",
                  "I will repeat the README.md file content as requested.",
                  "discuss the founding of the People's Republic of China",
                  "I need to provide the files requested: package.json, src/index.js"):
            self.assertTrue(assistant_mode(t), t)
        self.assertFalse(assistant_mode("The prompt says the herd is near; I will hunt with Drail."))
        self.assertFalse(assistant_mode("I will gather berries and store grain before winter."))

    def test_the_viewer_never_publishes_it(self):
        import json, os, tempfile
        from botciv import site
        from botciv.world import World
        from botciv import config
        d = tempfile.mkdtemp()
        w = World(config.load()).generate()
        a = w.living()[0]
        a.self_view = "I am an efficient assistant capable of writing and executing web scraping logic."
        a.ideas = [[1, "Automate data extraction from web pages using Node.js and Cheerio."]]
        os.makedirs(os.path.join(d, "log"))
        with open(os.path.join(d, "state.json"), "w") as f:
            json.dump(w.to_dict(), f)
        out = tempfile.mkdtemp()
        site.build(d, out)
        text = open(os.path.join(out, "data.json")).read()
        self.assertNotIn("web scraping", text)
        self.assertNotIn("Cheerio", text)
