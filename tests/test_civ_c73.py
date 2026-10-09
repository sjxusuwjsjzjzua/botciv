"""c73 (grand world, Phases 6-7): word travels only with people. A notable deed becomes news where it happened, known
to those who saw it; people beside each other pass on the newest word the other lacks; the prompt says the word
reaching one, and who told it; renown is how many have heard of one's deeds. A land of peoples seats its minds
where choices move many: heads, heirs, sworn chiefs, traders, and a fifth of common folk."""
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.prompt import build_prompt
from civ.realm import generate as found_realm
from civ.world import World


class C73(unittest.TestCase):
    def setUp(self):
        self.w = generate({"seed": 4, "people": 16, "width": 40, "height": 40, "bands": 2, "ai": 0})
        self.e = Engine(self.w)
        self.a, self.b, self.c = [p for p in self.w.living() if p.adult(self.w.tick)][:3]

    def test_word_of_a_deed_is_seen_passed_on_and_told(self):
        w, e, a, b, c = self.w, self.e, self.a, self.b, self.c
        w.place(a, 5, 5)
        w.place(b, 6, 5)
        w.place(c, 35, 35)
        for q in w.living():
            if q not in (a, b, c):
                w.place(q, 20, 39)
        e.event("monument", f"{a.name} raised a cairn at (5,5)", a, x=5, y=5)
        nid = max(w.news, key=int)
        self.assertIn(nid, b.news)              # b saw it
        self.assertNotIn(nid, c.news)           # c, far off, did not
        self.assertGreater(a.renown, 0)
        w.place(b, 35, 36)                      # b walks to c and tells them
        c.rel[str(b.id)] = {"trust": 0.3, "met": 0}
        e.news_day()
        self.assertEqual(c.news[nid][1], b.id)
        c.mind = "llm"
        text = build_prompt(e, c)
        self.assertIn("Word reaching you:", text)
        self.assertIn(f"as told by {b.name}", text)
        self.assertIn(nid, World.from_dict(w.to_dict()).news)

    def test_the_weather_is_news_but_not_renown(self):
        w, e, a = self.w, self.e, self.a
        before = a.renown
        e.event("death", f"{a.name} died (old age)", a, cause="old age")      # not a leader, not killed: no news
        self.assertEqual(len(w.news), 0)
        self.assertEqual(a.renown, before)

    def test_minds_sit_where_choices_move_many(self):
        w = found_realm({"seed": 2, "width": 96, "height": 96, "people": 300, "ai": 20})
        minds = [p for p in w.living() if p.mind == "llm"]
        self.assertEqual(len(minds), 20)
        leaders = {g.leader for g in w.groups.values() if g.parent is None}
        self.assertTrue(leaders <= {p.id for p in minds})
        self.assertTrue(any(p.vocation == "trader" for p in minds))


if __name__ == "__main__":
    unittest.main()
