"""Is the live world grand? The measures of docs/grand.md section 9, read from a world's state and its event
logs (the last --days world days of them).

    python tools/grandeur.py                     # world2, fetched from its branch (newest commit only)
    python tools/grandeur.py --dir /tmp/w/world  # a world already on disk
"""
import argparse
import glob
import gzip
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from civ.census import measures, measures_text  # noqa: E402
from civ.run import load  # noqa: E402
from civ.world import TPD, TPY  # noqa: E402


def fetch(branch="world2"):
    d = tempfile.mkdtemp(prefix="grand-")
    subprocess.run(["git", "fetch", "-q", "--depth", "1", "origin", branch], check=True)
    files = subprocess.run(["git", "ls-tree", "-r", "--name-only", "FETCH_HEAD", "world/"], capture_output=True,
                           text=True, check=True).stdout.split()
    want = ["world/state.json.gz"] + sorted(f for f in files if "/log/events-" in f)[-30:]
    tar = subprocess.run(["git", "archive", "FETCH_HEAD", *want], capture_output=True, check=True).stdout
    subprocess.run(["tar", "-x", "-C", d], input=tar, check=True)
    return os.path.join(d, "world")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="")
    ap.add_argument("--days", type=float, default=40)
    a = ap.parse_args(argv)
    d = a.dir or fetch()
    w = load(d)
    since = w.tick - a.days * TPD
    events = []
    for f in sorted(glob.glob(os.path.join(d, "log", "events-*.jsonl.gz"))):
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            events += [e for e in map(json.loads, fh) if e.get("t", 0) >= since]
    span = (w.tick - max(since, min((e["t"] for e in events), default=w.tick))) / TPY
    print(f"day {w.day()}, {len(w.living())} alive; events of the last {span * 40:.0f} world days")
    print(measures_text(measures(w, events, span)))


if __name__ == "__main__":
    main()
