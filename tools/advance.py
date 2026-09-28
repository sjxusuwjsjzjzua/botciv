"""Advance the world for hours in half-hour pieces, committing after each.

    python tools/advance.py --worktree wb --minutes 320 --prompts-out prompts-out

Used by world.yml so the quota is spent all day rather than in hourly bursts:
every piece spends whatever the models have room for, then the world is
committed and pushed to the `world` branch, so the viewer's backlog grows every
half hour and nothing is lost if the job is stopped. Full prompts are moved to
--prompts-out (uploaded as a run artifact, never committed).

Stops early when every model is spent for the day, when a piece fails, when a
local runner holds the lock, or when someone else has pushed to `world` (two
writers would fork the world).
"""
import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from botciv import run as runner  # noqa: E402


def git(wt, *args, check=False):
    return subprocess.run(["git", "-C", wt, *args], capture_output=True, text=True, check=check)


def locked(world):
    p = os.path.join(world, "LOCK")
    try:
        with open(p) as f:
            return json.load(f).get("until", 0) > time.time()
    except (OSError, ValueError):
        return False


def someone_else_pushed(wt):
    """True when origin/world has commits this worktree does not."""
    if git(wt, "fetch", "-q", "origin", "world").returncode != 0:
        return False                                   # no remote branch yet
    r = git(wt, "rev-list", "--count", "HEAD..FETCH_HEAD")
    return r.returncode == 0 and r.stdout.strip() not in ("", "0")


def commit_and_push(wt):
    git(wt, "add", "world")
    head = "botciv"
    try:
        with open(os.path.join(wt, "world", "last_run.md")) as f:
            head = f.readline().strip("# \n") or head
    except OSError:
        pass
    if git(wt, "commit", "-qm", head).returncode != 0:
        return True                                    # nothing new
    for i in range(4):
        if git(wt, "push", "-q", "origin", "HEAD:world").returncode == 0:
            return True
        time.sleep(2 ** (i + 1))
    return False


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--worktree", default="wb")
    ap.add_argument("--minutes", type=float, default=320)
    ap.add_argument("--chunk", type=float, default=30)
    ap.add_argument("--prompts-out", default=None)
    ap.add_argument("--new", action="store_true")
    ap.add_argument("--models", default="auto")
    ap.add_argument("--mind", default="gemini", help="reciprocity or simple to try the loop without the API")
    args = ap.parse_args(argv)

    wt = args.worktree
    world = os.path.join(wt, "world")
    git(wt, "config", "user.name", "botciv")
    git(wt, "config", "user.email", "botciv@users.noreply.github.com")
    end = time.time() + args.minutes * 60
    first = True
    why = "time limit"
    while end - time.time() > 300:
        if locked(world):
            why = "a local runner holds the world"
            break
        if not first and someone_else_pushed(wt):
            why = "someone else pushed to the world branch"
            break
        minutes = min(args.chunk, (end - time.time()) / 60)
        flags = ["--new"] if (args.new and first) else []
        if args.prompts_out:
            flags.append("--prompts")
        first = False
        try:
            runner.main(["--dir", world, "--minutes", f"{minutes:.1f}", "--max-calls", "1000000",
                         "--models", args.models, "--mind", args.mind] + flags)
            ok = True
        except Exception as ex:                        # save what was done, then stop
            print("run failed:", type(ex).__name__, ex)
            ok = False
        if args.prompts_out:
            os.makedirs(args.prompts_out, exist_ok=True)
            for p in glob.glob(os.path.join(world, "prompts", "*")):
                shutil.move(p, os.path.join(args.prompts_out, os.path.basename(p)))
            shutil.rmtree(os.path.join(world, "prompts"), ignore_errors=True)
        if not commit_and_push(wt):
            why = "the push was refused"
            break
        if not ok:
            why = "a run failed"
            break
        try:
            with open(os.path.join(world, "last_run.md")) as f:
                if "every model is spent" in f.read():
                    why = "every model is spent for today"
                    break
        except OSError:
            pass
    print(f"stopped: {why}")
    out = os.environ.get("GITHUB_STEP_SUMMARY")
    if out:
        with open(out, "a") as f:
            f.write(f"\nAdvancing stopped: {why}.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
