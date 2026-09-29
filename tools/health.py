"""A quick health check of a world directory: who is alive, how people die, what the
models cost, and what the world keeps refusing. The first thing to run each iteration.

    git fetch origin world && rm -rf /tmp/w && mkdir -p /tmp/w \
        && git archive origin/world world | tar -x -C /tmp/w
    python tools/health.py /tmp/w/world [--days 10]
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("--days", type=float, default=10, help="how far back 'recent' reaches")
    args = ap.parse_args()
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
    main()
