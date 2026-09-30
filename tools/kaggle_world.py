"""Advance the living world on a Kaggle GPU for about an hour, then bring it home.

    python tools/kaggle_world.py --worktree wb --minutes 55

Runs in GitHub Actions (kaggle-world.yml), with the world branch checked out in --worktree:

1. push tools/kaggle_world_kernel.py as a private Kaggle notebook; it starts the model server
   and fetches the model while the rest happens;
2. take the world's lock (world/LOCK), so the Actions world run waits instead of advancing;
3. wait until that run has pushed the piece it was advancing, then say go in the LOCK: that
   commit is the world the notebook advances;
4. wait for the notebook, bring the advanced world back, and push it, but only if nothing else
   moved the world branch meanwhile (two writers would fork the world);
5. give the lock back, whatever happened.

The Kaggle credential is the KAGGLE_SECRET environment variable (see kaggle_run.py). Nothing on
Kaggle can write to this repository: the notebook reads the public repository and leaves the
world in its output, and this runner pushes it.
"""
import argparse
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tarfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
BRANCH = "world"        # the branch this world lives on; kaggle_world2.py sets "world2"
sys.path.insert(0, HERE)
from kaggle_run import credentials, fill_settings, run  # noqa: E402


def git(wt, *args):
    return subprocess.run(["git", "-C", wt, *args], capture_output=True, text=True)


def say(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


def origin_head(wt):
    if git(wt, "fetch", "-q", "origin", BRANCH).returncode != 0:
        return ""
    return git(wt, "rev-parse", "FETCH_HEAD").stdout.strip()


def push(wt, msg):
    git(wt, "add", "-A", "world")
    if git(wt, "commit", "-qm", msg).returncode != 0:
        return True
    return git(wt, "push", "-q", "origin", f"HEAD:{BRANCH}").returncode == 0


def set_lock(wt, lock, msg):
    """Write world/LOCK (or remove it when lock is None) on top of origin/world and push it."""
    for i in range(5):
        head = origin_head(wt)
        if head:
            git(wt, "reset", "-q", "--hard", head)
        p = os.path.join(wt, "world", "LOCK")
        if lock is None:
            if not os.path.exists(p):
                return True
            os.remove(p)
        else:
            with open(p, "w") as f:
                json.dump(lock, f)
        if push(wt, msg):
            return True
        time.sleep(2 ** (i + 1))
    return False


def our_lock(wt, run_id):
    r = git(wt, "show", "FETCH_HEAD:world/LOCK")
    try:
        return json.loads(r.stdout).get("run") == run_id
    except ValueError:
        return False


def world_run_busy():
    """True while a world.yml run is advancing (not merely waiting on the lock or a spent quota)."""
    r = subprocess.run(["gh", "run", "list", "--workflow", "world.yml", "--status", "in_progress",
                        "--json", "databaseId", "-q", ".[0].databaseId"], capture_output=True, text=True)
    return r.returncode == 0 and bool(r.stdout.strip())


def lock_acknowledged(wt):
    r = git(wt, "show", "FETCH_HEAD:world/LOCK")
    try:
        return bool(json.loads(r.stdout).get("ack"))
    except ValueError:
        return False


def wait_for_quiet(wt, limit):
    """Wait until no world.yml run is going, or the one going has said in the LOCK that it
    has stopped advancing (after pushing the piece it was in the middle of)."""
    end = time.time() + limit * 60
    while time.time() < end:
        origin_head(wt)
        if lock_acknowledged(wt):
            return "the world run has stopped and says so"
        if not world_run_busy():
            return "no world run is going"
        say("waiting for the world run to finish its piece")
        time.sleep(60)
    return None


def push_kernel(user, slug, a, run_id, code):
    d = os.path.join(os.getcwd(), "kaggle-kernel")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    src = open(os.path.join(HERE, "kaggle_world_kernel.py")).read()
    settings = {"code": code, "run": run_id, "minutes": a.minutes, "parallel": a.parallel, "model": a.model,
                "wait": a.quiet + 10}
    src = fill_settings(src, settings)
    with open(os.path.join(d, "world.py"), "w") as f:
        f.write(src)
    meta = {"id": f"{user}/{slug}", "title": slug, "code_file": "world.py", "language": "python",
            "kernel_type": "script", "is_private": True, "enable_gpu": True, "enable_internet": True,
            "machine_shape": a.accelerator, "dataset_sources": [], "competition_sources": [],
            "kernel_sources": [], "model_sources": []}
    with open(os.path.join(d, "kernel-metadata.json"), "w") as f:
        json.dump(meta, f, indent=1)
    say("pushing", meta["id"], "on", a.accelerator)
    print(run(["kaggle", "kernels", "push", "-p", d, "--accelerator", a.accelerator,
               "-t", str((a.minutes + a.quiet + 60) * 60)])[-600:], flush=True)


def wait_kernel(ref, limit):
    end = time.time() + limit * 60
    status = ""
    time.sleep(60)
    while time.time() < end:
        status = run(["kaggle", "kernels", "status", ref], check=False)
        say(status[-160:])
        if re.search(r"complete|error|cancel", status, re.I):
            break
        time.sleep(60)
    return status


def summary(text):
    print(text, flush=True)
    out = os.environ.get("GITHUB_STEP_SUMMARY")
    if out:
        with open(out, "a") as f:
            f.write(text + "\n")


def bring_home(wt, out, go_sha, keep=None):
    """Put the advanced world on the branch. Returns why not, or None when pushed. go_sha "" means
    a new world (the branch must still not exist). keep(wt) runs on the new world before the commit."""
    tar = os.path.join(out, "world.tar.gz")
    if not os.path.exists(tar):
        return "the notebook left no world"
    head = origin_head(wt)
    if go_sha:
        moved = [n for n in git(wt, "diff", "--name-only", go_sha, head).stdout.split() if n]
        if not head or any(n != "world/LOCK" for n in moved):
            return f"the world branch moved while the notebook ran ({go_sha[:8]} -> {head[:8]}): not pushing"
        git(wt, "reset", "-q", "--hard", head)      # only the lock changed since the go (a waiting run said so)
    elif head:
        return "the branch was started by someone else while the notebook ran: not pushing"
    tmp = os.path.join(out, "unpacked")
    shutil.rmtree(tmp, ignore_errors=True)
    with tarfile.open(tar) as t:
        t.extractall(tmp, filter="data")
    if not any(os.path.exists(os.path.join(tmp, "world", f)) for f in ("state.json", "state.json.gz")):
        return "the notebook's world has no state"
    shutil.rmtree(os.path.join(wt, "world"), ignore_errors=True)
    shutil.move(os.path.join(tmp, "world"), os.path.join(wt, "world"))
    lock = os.path.join(wt, "world", "LOCK")
    if os.path.exists(lock):
        os.remove(lock)
    if keep:
        keep(wt)
    head = "botciv"
    try:
        with open(os.path.join(wt, "world", "last_run.md")) as f:
            head = f.readline().strip("# \n") or head
    except OSError:
        pass
    if not push(wt, head + " (on a Kaggle GPU)"):
        return "the push was refused"
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--worktree", default="wb")
    ap.add_argument("--user", default="")
    ap.add_argument("--minutes", type=int, default=55, help="minutes the notebook advances the world")
    ap.add_argument("--parallel", type=int, default=4)
    ap.add_argument("--model", default="gemma4:26b")
    ap.add_argument("--accelerator", default="NvidiaTeslaT4")
    ap.add_argument("--quiet", type=int, default=40, help="minutes to wait for the world run's piece")
    ap.add_argument("--out", default="kaggle-out")
    a = ap.parse_args()
    wt = a.worktree
    git(wt, "config", "user.name", "botciv")
    git(wt, "config", "user.email", "botciv@users.noreply.github.com")
    user = credentials(a.user)
    code = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    run_id = secrets.token_hex(6)
    ref = f"{user}/botciv-world"
    push_kernel(user, "botciv-world", a, run_id, code)

    until = time.time() + (a.quiet + a.minutes + 45) * 60
    lock = {"by": "kaggle", "run": run_id, "until": until}
    if not set_lock(wt, lock, "A Kaggle GPU takes the world for a while"):
        summary("## Kaggle world run\n\nCould not take the world's lock; the notebook will time out waiting.")
        return 1
    pushed = False
    try:
        why = wait_for_quiet(wt, a.quiet)
        if not why:
            summary("## Kaggle world run\n\nThe world run did not finish its piece in time; nothing was run.")
            return 1
        say("quiet:", why)
        lock.update(go=True, ack=True)
        if not set_lock(wt, lock, "The Kaggle GPU starts on the world"):
            summary("## Kaggle world run\n\nCould not hand the world over.")
            return 1
        go_sha = git(wt, "rev-parse", "HEAD").stdout.strip()
        say("go at", go_sha[:8])
        status = wait_kernel(ref, a.quiet + a.minutes + 60)
        os.makedirs(a.out, exist_ok=True)
        print(run(["kaggle", "kernels", "output", ref, "-p", a.out, "-o"], check=False)[-600:], flush=True)
        res = {}
        try:
            res = json.load(open(os.path.join(a.out, "world_results.json")))
        except (OSError, ValueError):
            pass
        why_not = bring_home(wt, a.out, go_sha)
        pushed = why_not is None
        lines = ["## Kaggle world run", "", f"status: {status[-120:]}", "",
                 f"- **brought home**: {'yes' if pushed else 'no: ' + why_not}"]
        for k in ("gpu", "pull_seconds", "ready_minutes", "waited_for_go_minutes", "world_from", "tick_from",
                  "tick_to", "run_minutes", "total_minutes", "error"):
            if k in res:
                lines.append(f"- **{k}**: `{json.dumps(res[k])[:300]}`")
        if res.get("tick_from") is not None and res.get("tick_to") is not None:
            lines.append(f"- **world days advanced**: {(res['tick_to'] - res['tick_from']) / res.get('ticks_per_day', 12):.1f}")
        if res.get("last_run"):
            lines += ["", res["last_run"]]
        if res.get("trace"):
            lines += ["", "```", res["trace"], "```"]
        summary("\n".join(lines))
        return 0 if pushed else 1
    finally:
        if not pushed:
            origin_head(wt)
            if our_lock(wt, run_id):
                set_lock(wt, None, "The Kaggle GPU gives the world back")


if __name__ == "__main__":
    sys.exit(main())
