"""Advance the long land: a bots-only civ world that is never reset, run as fast as it goes (botworld.yml).

    python tools/advance_long.py --worktree lw --minutes 35
    python tools/advance_long.py --worktree gw --branch grandworld --realm --people 1200 --size 176 --seed 5 --name "The grand land"

The point is to see where a land ends up when it is left alone for a long time, under the rules on main.
Each run has two parts:
1. as fast as it goes, keeping no frames or event logs, one census line a season appended to
   world/history.jsonl (civ/census.py): the long record;
2. the last few days (--window, 20 by default) with every hour kept, so the viewer shows the land
   as it stands now.
The branch holds only the newest state: each run replaces it with a single commit (a force push of an
orphan commit), so it never grows; history.jsonl carries everything that came before. Only this
workflow writes the branch. No keys, no language model.
"""
import argparse
import os
import shutil
import subprocess
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def git(wt, *args, check=False):
    r = subprocess.run(["git", "-C", wt, *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--worktree", default="lw")
    ap.add_argument("--branch", default="botworld")
    ap.add_argument("--minutes", type=float, default=35, help="the fast part")
    ap.add_argument("--window", type=int, default=20, help="days kept hour by hour for the viewer")
    ap.add_argument("--people", type=int, default=200)
    ap.add_argument("--size", type=int, default=96)
    ap.add_argument("--seed", type=int, default=21)
    ap.add_argument("--realm", action="store_true", help="a new land is a continent of peoples (the grand land, grandworld.yml)")
    ap.add_argument("--name", default="The long land", help="what the summary line calls the land")
    ap.add_argument("--no-push", action="store_true")
    a = ap.parse_args(argv)
    from civ import run as runner
    from civ.world import TPD
    wt = a.worktree
    d = os.path.join(wt, "world")
    hist = os.path.join(d, "history.jsonl")
    new = not os.path.exists(os.path.join(d, "state.json.gz"))
    base = ["--dir", d, "--bots", "--history", hist]
    if new:
        os.makedirs(d, exist_ok=True)
        base_new = ["--new", "--people", str(a.people), "--size", str(a.size), "--seed", str(a.seed)] + (["--realm"] if a.realm else [])
    else:
        base_new = []
    # 1. as fast as it goes, keeping only the census
    shutil.rmtree(os.path.join(d, "log"), ignore_errors=True)
    runner.main(base + base_new + ["--no-frames", "--minutes", str(a.minutes)])
    # 2. the last days, hour by hour, for the viewer
    shutil.rmtree(os.path.join(d, "log"), ignore_errors=True)
    runner.main(base + ["--ticks", str(a.window * TPD), "--minutes", "15"])
    last = ""
    try:
        with open(hist) as f:
            lines = f.read().splitlines()
        import json
        h = json.loads(lines[-1])
        first = json.loads(lines[0])
        last = (f"{a.name}: year {h['year']}, {h['alive']} alive ({h['ever']} have lived), era {h['era']}, "
                f"{h['able']} crafts known, {h['buildings']} buildings, {h['groups']} groups; "
                f"{len(lines)} seasons recorded since year {first['year']}.\n\n")
        p = os.path.join(d, "last_run.md")
        with open(p) as f:
            body = f.read()
        with open(p, "w") as f:
            f.write(last + body)
    except (OSError, ValueError, IndexError):
        pass
    print(last.strip())
    if a.no_push:
        return 0
    # the branch holds only the newest state: one orphan commit, replacing the last
    git(wt, "config", "user.name", "botciv")
    git(wt, "config", "user.email", "botciv@users.noreply.github.com")
    git(wt, "checkout", "-q", "--orphan", "next", check=True)
    git(wt, "add", "-A", "world", check=True)
    git(wt, "commit", "-qm", (last.split(";")[0] or a.name).strip(), check=True)
    git(wt, "push", "-q", "-f", "origin", f"next:{a.branch}", check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
