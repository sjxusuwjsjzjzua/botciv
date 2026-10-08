"""Past days' log chunks, one file a kind a day (roadmap O2: bound the world branches).

    python tools/compact_logs.py world2/log            # every day before today (UTC)
    python tools/compact_logs.py world2/log --dry-run

Each piece of a world writes its own events-, frames- and minds- files (civ/run.py), so a world
branch gathers hundreds of small files a day (and on 2026-10-03, 20,000 from a loop of empty
pieces, each with the same day's snapshot). A day that is over never changes again: its files
are merged, in order, into `<kind>-<YYYYMMDD>.jsonl.gz`; a day's snapshot (`"kind": "land"`) seen
again at the same hour is kept once, and empty files are dropped. Readers (civ/site.py,
tools/civ_round.py) read `<kind>-*.jsonl.gz` in name order, which this keeps."""
import argparse
import gzip
import json
import os
import re
import sys
from datetime import datetime, timezone

NAME = re.compile(r"^(events|frames|minds)-(\d{8})(-\d{6})?\.jsonl\.gz$")


def lines(path):
    """The whole lines of a gz file (a file cut short keeps what came before the cut)."""
    out = []
    try:
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            for line in fh:
                if line.endswith("\n"):
                    out.append(line)
    except (OSError, EOFError):
        pass
    return out


def compact(log, today=None, dry=False):
    """Merge every past day's files; returns (files before, files after) for the days touched."""
    today = today or datetime.now(timezone.utc).strftime("%Y%m%d")
    if not os.path.isdir(log):
        return 0, 0
    days = {}
    for f in sorted(os.listdir(log)):
        m = NAME.match(f)
        if m and m.group(2) < today:
            days.setdefault((m.group(1), m.group(2)), []).append(f)
    before = after = 0
    for (kind, day), files in sorted(days.items()):
        if len(files) == 1 and not NAME.match(files[0]).group(3):
            continue                            # already one file for the day
        out, seen = [], set()
        for f in files:                         # name order is time order
            for line in lines(os.path.join(log, f)):
                if kind == "frames" and '"kind":"land"' in line:
                    try:
                        t = json.loads(line).get("t")
                    except ValueError:
                        continue
                    if t in seen:
                        continue                # the same day's snapshot again
                    seen.add(t)
                out.append(line)
        before += len(files)
        if dry:
            after += 1 if out else 0
            continue
        target = os.path.join(log, f"{kind}-{day}.jsonl.gz")
        if out:
            tmp = target + ".tmp"
            with gzip.open(tmp, "wt", encoding="utf-8") as fh:
                fh.writelines(out)
            for f in files:
                os.remove(os.path.join(log, f))
            os.replace(tmp, target)
            after += 1
        else:
            for f in files:
                os.remove(os.path.join(log, f))
    return before, after


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("log")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args(argv)
    b, n = compact(a.log, dry=a.dry_run)
    print(f"{a.log}: {b} files of past days into {n}")


if __name__ == "__main__":
    sys.exit(main())
