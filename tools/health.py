"""A quick health check of a world: who is alive, how people die, what the models cost, and what the
world keeps refusing. The first thing to run each iteration.

    python tools/health.py                 # the living civ world (world2), fetched: mode 1 in one command
    python tools/health.py --civ DIR       # a civ world folder already on disk
    python tools/health.py /tmp/w/world [--days 10]   # the retired first world (botciv)
"""
import argparse
import glob
import json
import os
import statistics
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from botciv.log import read  # noqa: E402
from botciv.world import World  # noqa: E402


def civ(d=None, branch="world2", days=3):
    """The civ world: is it moving, on which rules, who lives and dies, what the people are refused."""
    import subprocess
    import tempfile
    import time
    from collections import Counter as C
    sys.path.insert(0, os.path.dirname(__file__))
    from civ_round import fetch, read as rd
    from civ.run import load
    from civ.world import TPD
    age = None
    if d is None:
        d = fetch(branch, os.path.join(tempfile.mkdtemp(), branch))
        if not d:
            print(f"{branch}: no such branch (or no network)")
            return 1
        r = subprocess.run(["git", "log", "-1", "--format=%ct", f"origin/{branch}"], capture_output=True, text=True)
        age = (time.time() - int(r.stdout.strip())) / 3600 if r.stdout.strip() else None
    w = load(d)
    last = open(os.path.join(d, "last_run.md")).read().splitlines() if os.path.exists(os.path.join(d, "last_run.md")) else []
    from civ.prompt import RULES_VERSION
    verdict = "" if age is None else ("HEALTHY" if age < 2 else "STALE") + f": last piece {age:.1f} hours ago. "
    print(f"{verdict}{branch} at {w.when()}; {len(w.living())} alive, {sum(1 for p in w.living() if p.mind == 'llm')} "
          f"with minds of their own, {len(w.people)} ever; rules in this checkout {RULES_VERSION}")
    for line in last[1:4]:
        print("  " + line)
    since = w.tick - days * TPD
    ev, mi = [], []
    for f in sorted(glob.glob(os.path.join(d, "log", "events-*.jsonl.gz")))[-40:]:
        ev += [e for e in rd(f) if e.get("t", 0) >= since]
    for f in sorted(glob.glob(os.path.join(d, "log", "minds-*.jsonl.gz")))[-40:]:
        mi += [m for m in rd(f) if m.get("t", 0) >= since]
    llm = {p.id for p in w.people.values() if p.mind == "llm"}
    k = C(e["kind"] for e in ev)
    print(f"last {days:g} days: births {k['birth']}, deaths {dict(C(e.get('cause', '?') for e in ev if e['kind'] == 'death'))}, "
          f"thefts {k['steal']}, blows {k['attack']}, deals {k['deal']}, writings {k['write']}")
    steps = sum(len(m.get("plan") or []) for m in mi)
    ref = [e for e in ev if e["kind"] == "refused" and (e.get("who") or [None])[0] in llm]
    print(f"  {len(mi)} answers (rules {dict(C(m.get('rules', '?') for m in mi))}); refused {len(ref)} of {steps} steps "
          f"({100 * len(ref) / max(1, steps):.1f}%): " + "; ".join(f"{why} ({n})" for why, n in C(e.get('why', '')[:60] for e in ref).most_common(4)))
    return 0 if age is None or age < 2 else 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", nargs="?")
    ap.add_argument("--civ", action="store_true", help="the dir is a civ world")
    ap.add_argument("--days", type=float, default=10, help="how far back 'recent' reaches")
    args = ap.parse_args()
    if args.dir is None or args.civ:
        return civ(args.dir, days=min(args.days, 3) if args.dir is None else args.days)
    with open(os.path.join(args.dir, "state.json")) as f:
        w = World.from_dict(json.load(f))
    since = w.tick - args.days * w.tpd()
    from botciv.prompt import RULES_VERSION
    print(f"# {w.when()}, {w.season()} of year {w.year() + 1}; code rules {RULES_VERSION}")
    living = w.living()
    print(f"alive {len(living)}; ever lived {len(w.agents)}")
    for a in living:
        print(f"  {a.name:10} health {a.health:>2} fullness {a.satiety:>2} load {a.carrying():4.1f} "
              f"age {a.age / w.ticks_per_year():.1f}  {a.self_view[:60]}")

    dead = [a for a in w.agents.values() if not a.alive]
    print("\ndeaths, all time:", dict(Counter((a.cause or "?").split(" by ")[0] for a in dead).most_common()))
    recent = sorted((a.died, a.name, a.cause) for a in dead if a.died is not None and a.died >= since)
    print(f"deaths in the last {args.days:g} days:", ", ".join(f"{n} ({c}, {w.when(t)})" for t, n, c in recent) or "none")

    minds = []
    for p in sorted(glob.glob(os.path.join(args.dir, "log", "minds-*.jsonl.gz"))):
        minds.extend(m for m in read(p) if m.get("t", 0) >= since)
    by = defaultdict(list)
    rules = Counter()
    for m in minds:
        me = m.get("meta") or {}
        rules[m.get("rules")] += 1
        if me.get("in"):
            by[me.get("model")].append((me["in"], me.get("out") or 0))
    print(f"\ndecisions in the last {args.days:g} days: {len(minds)}; by rules version {dict(rules)}; "
          f"no answer {sum(1 for m in minds if not m.get('out'))}")
    for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
        print(f"  {k:32} {len(v):5} calls, tokens in {statistics.mean(x[0] for x in v):6.0f}, "
              f"out {statistics.mean(x[1] for x in v):4.0f}")

    # where the decisions go: a verb eating a third of them is a failure no one wished to report
    verbs = Counter(((m.get("out") or {}).get("action") or {}).get("verb") for m in minds if m.get("out"))
    total = max(1, sum(verbs.values()))
    print("  choices: " + ", ".join(f"{v} {n * 100 // total}%" for v, n in verbs.most_common(8)))
    # how late answers land; someone idle while waiting loses those hours
    lag = Counter(min(3, m.get("applied", m["t"]) - m["t"]) for m in minds if "t" in m)
    print("  answers late by hours: " + ", ".join(f"{h}h {lag[h] * 100 // max(1, len(minds))}%" for h in range(4))
          + f"; asked while idle: {sum(1 for m in minds if 'you are not doing anything' in m.get('wake', []))}")

    refused = Counter()
    for p in sorted(glob.glob(os.path.join(args.dir, "log", "events-*.jsonl.gz")))[-12:]:
        for e in read(p):
            if e.get("kind") == "fail" and e.get("t", 0) >= since:
                refused[e["text"].split("could not: ", 1)[-1][:90]] += 1
    print(f"\nmost refused choices in the last {args.days:g} days:")
    for why, n in refused.most_common(12):
        print(f"  {n:4} x {why}")
    wakes = Counter(wk[:70] for m in minds for wk in m.get("wake", []) if "could not" in wk or "failed" in wk
                    or "cannot" in wk or "stopped" in wk)
    print("\nmost common setbacks people were told of:")
    for why, n in wakes.most_common(8):
        print(f"  {n:4} x {why}")


if __name__ == "__main__":
    sys.exit(main())
