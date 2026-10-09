"""Bounded world branches (roadmap O2): past days' log chunks merged, a piece that passes no hour
leaves no files."""
import gzip
import json
import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))
from compact_logs import compact  # noqa: E402
from civ.site import read  # noqa: E402


def put(path, rows):
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, separators=(",", ":")) + "\n")


class TestCompact(unittest.TestCase):
    def test_days_merged_in_order_and_snapshots_once(self):
        with tempfile.TemporaryDirectory() as d:
            put(f"{d}/frames-20261003-100000.jsonl.gz", [{"t": 5, "kind": "land"}, {"t": 5, "p": []}])
            put(f"{d}/frames-20261003-100010.jsonl.gz", [{"t": 5, "kind": "land"}])     # an empty piece
            put(f"{d}/frames-20261003-120000.jsonl.gz", [{"t": 5, "kind": "land"}, {"t": 6, "p": []}])
            put(f"{d}/events-20261003-100000.jsonl.gz", [{"t": 5, "kind": "say"}])
            put(f"{d}/events-20261003-100010.jsonl.gz", [])
            put(f"{d}/minds-20261003-100010.jsonl.gz", [])
            put(f"{d}/frames-20261004-010000.jsonl.gz", [{"t": 7, "p": []}])
            put(f"{d}/frames-20261005-010000.jsonl.gz", [{"t": 9, "p": []}])           # today: untouched
            before = read(f"{d}/frames-*.jsonl.gz")
            compact(d, today="20261005")
            self.assertEqual(sorted(os.listdir(d)), ["events-20261003.jsonl.gz", "frames-20261003.jsonl.gz",
                                                     "frames-20261004.jsonl.gz", "frames-20261005-010000.jsonl.gz"])
            after = read(f"{d}/frames-*.jsonl.gz")
            self.assertEqual([f["t"] for f in after], [5, 5, 6, 7, 9])
            self.assertEqual(len([f for f in before if f.get("kind") == "land"]), 3)
            self.assertEqual(len([f for f in after if f.get("kind") == "land"]), 1)
            compact(d, today="20261005")                                             # a second time: nothing
            self.assertEqual(len(os.listdir(d)), 4)

    def test_old_days_keep_one_land_in_four(self):
        with tempfile.TemporaryDirectory() as d:
            rows = [r for day in range(12) for r in ({"t": day * 12, "kind": "land"}, {"t": day * 12 + 1, "p": []})]
            put(f"{d}/frames-20261001.jsonl.gz", rows)
            put(f"{d}/frames-20261008.jsonl.gz", rows)                                # within three days: whole
            compact(d, today="20261009")
            old = read(f"{d}/frames-20261001.jsonl.gz")
            self.assertEqual([f["t"] // 12 for f in old if f.get("kind") == "land"], [0, 4, 8])
            self.assertEqual(len([f for f in old if "p" in f]), 12)
            self.assertEqual(len([f for f in read(f"{d}/frames-20261008.jsonl.gz") if f.get("kind") == "land"]), 12)
            stamp = os.path.getmtime(f"{d}/frames-20261001.jsonl.gz")
            time.sleep(0.05)
            compact(d, today="20261009")                                             # nothing more to drop: untouched
            self.assertEqual(os.path.getmtime(f"{d}/frames-20261001.jsonl.gz"), stamp)


class TestEmptyPiece(unittest.TestCase):
    def test_no_hour_no_files(self):
        from civ import run
        with tempfile.TemporaryDirectory() as d:
            run.main(["--dir", d, "--new", "--bots", "--people", "12", "--size", "30", "--ticks", "2"])
            n = len(os.listdir(os.path.join(d, "log")))
            self.assertEqual(n, 3)
            time.sleep(1.1)                                                        # a log of its own
            run.main(["--dir", d, "--bots", "--ticks", "0"])
            self.assertEqual(len(os.listdir(os.path.join(d, "log"))), n)


if __name__ == "__main__":
    unittest.main()
