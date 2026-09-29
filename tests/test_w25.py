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
