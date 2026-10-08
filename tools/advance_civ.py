"""Advance a civ world on the free API tiers for hours in short pieces, committing after each.

    python tools/advance_civ.py --worktree wb --branch world2 --minutes 45 --piece 22 --ai 48

Used by world2.yml in the hours Kaggle's GPU has none left (world3.yml, retired 2026-10-02, used it
for a world of its own). Each piece runs civ for --piece minutes with every free model the keys reach
(Flash-Lite, Gemma, Groq; civ.run --models auto), then the world is committed and pushed to its
branch and Pages is asked to publish, so the viewer moves every half hour and nothing is lost if
the job stops. Between pieces it stops when newer code is on main (so a change is running within
the hour), and when every model is spent it waits a while and looks again. With --chain it
starts the next run of that workflow as it ends, so the world goes on without the schedule.
"""
import argparse
import os
import shutil
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)


def git(wt, *args):
    return subprocess.run(["git", "-C", wt, *args], capture_output=True, text=True)


def main_sha():
    r = subprocess.run(["git", "ls-remote", "origin", "refs/heads/main"], capture_output=True, text=True, cwd=ROOT)
    return r.stdout.split()[0] if r.returncode == 0 and r.stdout.strip() else ""


def summary(text):
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if path:
        with open(path, "a") as f:
            f.write(text + "\n\n")
    print(text)


def gh(*args):
    if os.environ.get("GH_TOKEN") and shutil.which("gh"):
        subprocess.run(["gh", *args], cwd=ROOT)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--worktree", default="wb")
    ap.add_argument("--branch", default="world2")
    ap.add_argument("--minutes", type=float, default=330, help="how long this run goes on")
    ap.add_argument("--piece", type=float, default=30, help="minutes between commits")
    ap.add_argument("--models", default="auto")
    ap.add_argument("--parallel", type=int, default=8)
    ap.add_argument("--people", type=int, default=200)
    ap.add_argument("--ai", type=int, default=48)
    ap.add_argument("--size", type=int, default=96)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--new", action="store_true", help="begin a new world in place of the branch's")
    ap.add_argument("--chain", default="", help="workflow file to start again as this run ends")
    a = ap.parse_args(argv)
    from civ import run as runner
    wt, d = a.worktree, os.path.join(a.worktree, "world")
    git(wt, "config", "user.name", "botciv")
    git(wt, "config", "user.email", "botciv@users.noreply.github.com")
    started_code = main_sha()
    end = time.time() + a.minutes * 60
    new = a.new or not os.path.exists(os.path.join(d, "state.json.gz"))
    if a.new and os.path.isdir(d):
        git(wt, "rm", "-rq", "world")
    why, pieces = "time limit", 0
    while time.time() < end - 5 * 60:
        if pieces and main_sha() not in ("", started_code):
            why = "a newer version is on main"
            break
        minutes = min(a.piece, (end - time.time()) / 60 - 3)
        args = ["--dir", d, "--minutes", f"{minutes:.1f}", "--models", a.models, "--parallel", str(a.parallel)]
        if new:
            args += ["--new", "--people", str(a.people), "--ai", str(a.ai), "--size", str(a.size), "--seed", str(a.seed)]
        else:
            args += ["--minds", str(a.ai)]           # an existing world keeps this many minds of their own
        try:
            runner.main(args)
        except Exception as ex:                 # the world is saved as it goes: note it, keep what was saved, go on
            import traceback
            summary(f"## {a.branch}: a piece failed\n\n```\n{traceback.format_exc()[-1500:]}\n```")
            why = f"a piece failed ({type(ex).__name__})"
            if not os.path.exists(os.path.join(d, "state.json.gz")):
                break
        new = False
        pieces += 1
        try:
            last = open(os.path.join(d, "last_run.md")).read()
        except OSError:
            last = ""
        head = last.splitlines()[0].strip("# ") if last else "civ"
        compact(d)
        git(wt, "add", "-A", "world")
        git(wt, "commit", "-qm", head)
        if not push(wt, a.branch):
            why = "the push was refused (someone else moved the branch)"
            summary(f"## {a.branch}: stopped\n\n{why}")
            break
        gh("workflow", "run", "pages.yml", "--ref", "main")
        summary(last)
        if "everyone is dead" in last:
            why = "everyone is dead"
            break
        if "spent for now" in last or "not answering" in last:
            # the free allowances refill by the minute and by the day: wait a while, then look again
            time.sleep(min(15 * 60, max(0, end - time.time() - 6 * 60)))
    summary(f"## {a.branch}: {pieces} pieces; ended because {why}")
    if a.chain and why not in ("everyone is dead",):
        # the next run starts even after a refused push: it begins from the branch as it is, and a broken
        # chain left the world still for 8 hours on 2026-10-07 (the hourly schedule seldom fires)
        gh("workflow", "run", a.chain, "--ref", "main")
    return 1 if why.startswith("the push was refused") else 0


def push(wt, branch, tries=4):
    """Push the piece; a refusal is retried (the network, or GitHub, failing for a moment), and only a
    branch moved by someone else gives up."""
    for i in range(tries):
        if git(wt, "push", "-q", "origin", f"HEAD:{branch}").returncode == 0:
            return True
        time.sleep(2 ** (i + 1) * 5)
        if git(wt, "fetch", "-q", "origin", branch).returncode == 0 and \
                git(wt, "merge-base", "--is-ancestor", "FETCH_HEAD", "HEAD").returncode != 0:
            return False                        # the branch moved under us: never overwrite it
    return False


def compact(d):
    """Past days' log chunks merged into one file a kind a day (tools/compact_logs.py)."""
    try:
        sys.path.insert(0, os.path.dirname(__file__))
        from compact_logs import compact as run
        run(os.path.join(d, "log"))
    except Exception as ex:                     # never lose a piece over tidying
        print("compacting the logs failed:", ex)


if __name__ == "__main__":
    sys.exit(main())
