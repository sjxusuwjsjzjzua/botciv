"""Advance the second world, a larger one that lives only on a Kaggle GPU, by one piece.

    python tools/kaggle_world2.py --worktree wb --minutes 45

Runs in GitHub Actions (world2.yml) with the `world2` branch checked out in --worktree (or an
empty orphan worktree before the world begins). Only that workflow writes the branch, one run
at a time (when Kaggle has no hours left it advances the world on the free API tiers instead,
through tools/advance_civ.py; --room tells it which), so there is no lock: the notebook (tools/kaggle_world_kernel.py) advances the branch's
head commit, or begins the world from --config, and this runner pushes what it brings back.

Kaggle gives a few dozen GPU hours a week. Each piece is recorded in world/kaggle_usage.json,
and a piece only starts when the last 24 hours and the last 7 days leave room, so the world
moves every day rather than spending the week's hours at once and then standing still.
"""
import argparse
import json
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import kaggle_world as K  # noqa: E402
from kaggle_run import credentials, push_and_collect  # noqa: E402

K.BRANCH = "world2"
USAGE = os.path.join("world", "kaggle_usage.json")
SETUP = 12          # minutes a session spends besides advancing: starting, fetching the model, saving


def load_usage(wt):
    try:
        with open(os.path.join(wt, USAGE)) as f:
            return json.load(f).get("runs", [])
    except (OSError, ValueError):
        return []


def room(runs, now, day_hours, week_hours):
    """Minutes a new piece may advance, given the sessions already run ([start, minutes] each)."""
    day = sum(m for t, m in runs if now - t < 86400)
    week = sum(m for t, m in runs if now - t < 7 * 86400)
    return min(day_hours * 60 - day, week_hours * 60 - week) - SETUP


def load_failed(wt):
    """When a Kaggle piece last failed (an error in the run, or nothing came home), or 0."""
    try:
        with open(os.path.join(wt, USAGE)) as f:
            return json.load(f).get("failed", 0)
    except (OSError, ValueError):
        return 0


def write_usage(wt, runs, failed=None):
    os.makedirs(os.path.join(wt, "world"), exist_ok=True)
    keep = [r for r in runs if time.time() - r[0] < 14 * 86400]
    if failed is None:
        failed = load_failed(wt)
    with open(os.path.join(wt, USAGE), "w") as f:
        json.dump({"runs": keep, "failed": failed}, f)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--worktree", default="wb")
    ap.add_argument("--user", default="")
    ap.add_argument("--minutes", type=int, default=45, help="the longest piece")
    ap.add_argument("--parallel", type=int, default=8, help="answers at once (Ollama's slots)")
    ap.add_argument("--model", default="gemma4:26b")
    ap.add_argument("--config", default="configs/world2.toml")
    ap.add_argument("--engine", default="civ", help="civ (the second generation) or botciv")
    ap.add_argument("--people", type=int, default=200)
    ap.add_argument("--ai", type=int, default=48)
    ap.add_argument("--size", type=int, default=96)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--day-hours", type=float, default=3.8)
    ap.add_argument("--week-hours", type=float, default=27)
    ap.add_argument("--accelerator", default="NvidiaTeslaT4")
    ap.add_argument("--restart", action="store_true", help="begin a new world in place of the branch's (its history keeps the old)")
    ap.add_argument("--out", default="kaggle-out")
    ap.add_argument("--room", action="store_true", help="only print the minutes a piece may have now, and start nothing")
    a = ap.parse_args(argv)
    wt = a.worktree
    K.git(wt, "config", "user.name", "botciv")
    K.git(wt, "config", "user.email", "botciv@users.noreply.github.com")
    head = K.git(wt, "rev-parse", "--verify", "-q", "HEAD").stdout.strip()
    go_sha = "" if a.restart else head
    runs = load_usage(wt)
    now = time.time()
    minutes = int(min(a.minutes, room(runs, now, a.day_hours, a.week_hours)))
    if a.room:
        # a piece that failed lately (2026-10-04: a crash on the first prompt, every 12 minutes for an
        # hour of GPU time) hands the next two hours to the free tiers rather than failing again
        print(0 if now - load_failed(wt) < 2 * 3600 else max(0, minutes))
        return 0
    if minutes < 30:
        K.summary(f"## The second world\n\nWaiting for Kaggle's GPU hours: the last day and week leave "
                  f"{max(0, minutes)} minutes. The next scheduled run looks again.")
        return 0
    user = credentials(a.user)
    code = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    settings = {"code": code, "run": "", "minutes": minutes, "parallel": a.parallel, "model": a.model, "wait": 0,
                "branch": K.BRANCH, "sha": go_sha, "config": "" if go_sha else a.config, "engine": a.engine,
                "people": a.people, "ai": a.ai, "size": a.size, "seed": a.seed}
    a.wait = minutes + 90
    K.say("piece of", minutes, "minutes from", go_sha[:8] or "a new world")
    t0 = time.time()
    status = push_and_collect(a, user, "botciv-world2", "kaggle_world_kernel.py", settings, (minutes + 45) / 60)
    used = round((time.time() - t0) / 60)              # the whole wait, a little more than the session
    runs.append([round(t0), used])
    res = {}
    try:
        res = json.load(open(os.path.join(a.out, "world_results.json")))
    except (OSError, ValueError):
        pass
    failed = round(t0) if (res.get("error") or not res.get("run_minutes")) else None
    why_not = K.bring_home(wt, a.out, go_sha, keep=lambda w: write_usage(w, runs, failed), over=head if a.restart else "")
    if why_not and head:
        # nothing came home, but the hours were spent: record them so the budget holds
        head = K.origin_head(wt)
        if head:
            K.git(wt, "reset", "-q", "--hard", head)
            write_usage(wt, runs, round(t0))
            K.push(wt, "Kaggle hours spent on a piece that did not come home")
    lines = ["## The second world, on a Kaggle GPU", "", f"status: {status[-120:]}", "",
             f"- **brought home**: {'yes' if not why_not else 'no: ' + why_not}",
             f"- **piece**: {minutes} minutes asked, {used} minutes of Kaggle time"]
    for k in ("gpu", "world_from", "tick_from", "tick_to", "population", "run_minutes", "total_minutes", "error"):
        if k in res:
            lines.append(f"- **{k}**: `{json.dumps(res[k])[:300]}`")
    if res.get("tick_to") is not None:
        lines.append(f"- **world days advanced**: {(res['tick_to'] - (res.get('tick_from') or 0)) / res.get('ticks_per_day', 12):.1f}")
    if res.get("last_run"):
        lines += ["", res["last_run"]]
    if res.get("trace"):
        lines += ["", "```", res["trace"], "```"]
    K.summary("\n".join(lines))
    return 0 if not why_not else 1


if __name__ == "__main__":
    sys.exit(main())
