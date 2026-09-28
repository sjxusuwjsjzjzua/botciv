"""Advance the living world from this machine instead of GitHub Actions.

    GEMINI_API_KEY=... python tools/run_local.py --hours 3

Checks out the `world` branch into .world/, holds a lock there so the
hourly Actions runs stand aside (they still publish the viewer), and
advances the world in chunks, committing and pushing after each. Stops at
the time limit or when every model's daily quota is spent. The key is read
from the environment by the gateway and never written anywhere.
"""
import argparse
import json
import os
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from botciv import run as runner  # noqa: E402

WT = os.path.join(ROOT, ".world")


def git(*args, cwd=WT, check=True):
    return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True)


def checkout():
    if os.path.isdir(WT):
        git("fetch", "-q", "origin", "world", cwd=ROOT, check=False)
        git("reset", "-q", "--hard", "origin/world", check=False)
        return
    if git("fetch", "-q", "origin", "world", cwd=ROOT, check=False).returncode == 0:
        git("worktree", "add", "-q", "-B", "world", WT, "origin/world", cwd=ROOT)
    else:
        git("worktree", "add", "-q", "--orphan", "-b", "world", WT, cwd=ROOT)


def lock(minutes):
    os.makedirs(os.path.join(WT, "world"), exist_ok=True)
    with open(os.path.join(WT, "world", "LOCK"), "w") as f:
        json.dump({"by": "local", "until": int(time.time() + minutes * 60)}, f)


def push(msg):
    git("config", "user.name", "botciv")
    git("config", "user.email", "botciv@users.noreply.github.com")
    git("add", "-A", "world")
    if git("commit", "-qm", msg, check=False).returncode != 0:
        return True
    for i in range(4):
        r = git("push", "-q", "origin", "HEAD:world", check=False)
        if r.returncode == 0:
            return True
        time.sleep(2 ** (i + 1))
    print("push failed:", r.stderr.strip()[:300])
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hours", type=float, default=2)
    ap.add_argument("--chunk", type=int, default=150, help="calls per commit")
    ap.add_argument("--new", action="store_true")
    args = ap.parse_args()
    if not os.environ.get("GEMINI_API_KEY"):
        sys.exit("GEMINI_API_KEY is not set")
    checkout()
    deadline = time.time() + args.hours * 3600
    first = True
    while time.time() < deadline:
        lock(50)
        push("local runner holds the world")
        flags = ["--new"] if (args.new and first) else []
        first = False
        runner.main(["--dir", os.path.join(WT, "world"), "--minutes", "35", "--max-calls", str(args.chunk)] + flags)
        with open(os.path.join(WT, "world", "last_run.md")) as f:
            head = f.readline().strip("# \n")
            stats = f.read()
        if not push(head):
            break
        if "every model is spent" in stats:
            print("every model's daily quota is spent; stopping")
            break
    os.remove(os.path.join(WT, "world", "LOCK"))
    push("local runner done")


if __name__ == "__main__":
    main()
