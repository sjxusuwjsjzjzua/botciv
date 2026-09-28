"""Advance the world for hours in half-hour pieces, committing after each.

    python tools/advance.py --worktree wb --minutes 320 --prompts-out prompts-out

Used by world.yml so the quota is spent all day rather than in hourly bursts:
every piece spends whatever the models have room for, then the world is
committed and pushed to the `world` branch, so the viewer's backlog grows every
half hour and nothing is lost if the job is stopped. Full prompts are moved to
--prompts-out (uploaded as a run artifact, never committed).

When every model is spent, or a local runner holds the lock, it waits and
looks again rather than ending. It stops early when a piece fails or someone
else has pushed to `world` (two writers would fork the world), and between
pieces when a newer version of the code is on main. With --chain it starts
the next world run as it ends (unless something broke) and asks Pages to
publish after every piece, so the world keeps going without the schedule.
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


def code_version():
    r = subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True)
    return r.stdout.strip()


def newer_code(started):
    """True when main has moved on since this run's code was checked out."""
    r = subprocess.run(["git", "-C", ROOT, "ls-remote", "origin", "refs/heads/main"], capture_output=True, text=True)
    head = r.stdout.split()[0] if r.returncode == 0 and r.stdout.strip() else ""
    return bool(head) and bool(started) and head != started


def dispatch(workflow):
    """Start a workflow on main (Actions only: needs GH_TOKEN with actions: write)."""
    if not os.environ.get("GH_TOKEN"):
        return False
    r = subprocess.run(["gh", "workflow", "run", workflow, "--ref", "main"], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"could not start {workflow}:", r.stderr.strip()[:200])
    return r.returncode == 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--worktree", default="wb")
    ap.add_argument("--minutes", type=float, default=320)
    ap.add_argument("--chunk", type=float, default=30)
    ap.add_argument("--prompts-out", default=None)
    ap.add_argument("--new", action="store_true")
    ap.add_argument("--models", default="auto")
    ap.add_argument("--mind", default="gemini", help="reciprocity or simple to try the loop without the API")
    ap.add_argument("--chain", action="store_true",
                    help="when done, start the next world run (and publish after each piece)")
    ap.add_argument("--idle", type=float, default=300, help="seconds to wait before looking again when blocked")
    args = ap.parse_args(argv)

    wt = args.worktree
    world = os.path.join(wt, "world")
    git(wt, "config", "user.name", "botciv")
    git(wt, "config", "user.email", "botciv@users.noreply.github.com")
    started = code_version()
    end = time.time() + args.minutes * 60
    first = True
    why = "time limit"
    spent = False
    while end - time.time() > 300:
        if not first and newer_code(started):
            why = "a newer version is on main"
            break
        if locked(world) or spent:
            # a local runner is advancing the world, or every model is spent for now:
            # wait here rather than end, so the run never needs restarting by hand
            print("waiting:", "a local runner holds the world" if not spent else "every model is spent")
            time.sleep(min(args.idle, max(1, end - time.time() - 300)))
            spent = False
            if not locked(world):
                git(wt, "pull", "-q", "--ff-only", "origin", "world")
            continue
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
        if args.chain:
            dispatch("pages.yml")
        if not ok:
            why = "a run failed"
            break
        try:
            with open(os.path.join(world, "last_run.md")) as f:
                spent = "every model is spent" in f.read()
        except OSError:
            pass
    print(f"stopped: {why}")
    out = os.environ.get("GITHUB_STEP_SUMMARY")
    if out:
        with open(out, "a") as f:
            f.write(f"\nAdvancing stopped: {why}.\n")
    broken = why in ("a run failed", "the push was refused", "someone else pushed to the world branch")
    if args.chain and not broken:
        dispatch("world.yml")                          # queues behind this run and starts when it ends
    return 1 if why in ("a run failed", "the push was refused") else 0     # show breakage as a red run


if __name__ == "__main__":
    raise SystemExit(main())
