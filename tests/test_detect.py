import unittest

from botciv.detect import detect, variety


def ev(i, t, kind, a=None, b=None, **kw):
    e = {"id": i, "t": t, "kind": kind, "text": kw.pop("text", kind)}
    if a is not None:
        e["a"] = a
    if b is not None:
        e["b"] = b
    e.update(kw)
    return e


class TestDetect(unittest.TestCase):
    def test_betrayal_after_gift(self):
        found = detect([ev(1, 10, "give", 1, 2), ev(2, 20, "attack", 2, 1)])
        self.assertEqual([f["kind"] for f in found], ["betrayal"])
        self.assertIn(1, found[0]["ids"])

    def test_no_betrayal_between_strangers(self):
        self.assertEqual(detect([ev(1, 20, "attack", 2, 1)]), [])

    def test_feud_and_war(self):
        evs = [ev(1, 0, "group_found", 1, text="A founded the group Reds. Rules: x", group=10),
               ev(2, 0, "group_found", 2, text="B founded the group Blues. Rules: y", group=20)]
        evs += [ev(3 + i, 5 + i, "attack", 1, 2) for i in range(3)]
        kinds = [f["kind"] for f in detect(evs)]
        self.assertIn("feud", kinds)
        self.assertIn("war", kinds)

    def test_alliance_needs_three_members_and_time(self):
        evs = [ev(1, 0, "group_found", 1, text="A founded the group Kin. Rules: share", group=5),
               ev(2, 1, "join", 2, group=5), ev(3, 2, "join", 3, group=5), ev(4, 60, "say", 1)]
        kinds = [f["kind"] for f in detect(evs)]
        self.assertIn("alliance", kinds)
        self.assertEqual(variety(detect(evs), evs)["pattern_count"], 1)


if __name__ == "__main__":
    unittest.main()
