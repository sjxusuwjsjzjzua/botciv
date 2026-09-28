"""Bots-only runs across seeds: population over time and causes of death.

    python tools/tune.py --years 2 --seeds 1 2 3 --bot reciprocity
"""
import argparse
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from botciv import config  # noqa: E402
from botciv.log import NullLog  # noqa: E402
from botciv.sim import run_bots  # noqa: E402
from botciv.world import World  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=float, default=2)
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3])
    ap.add_argument("--bot", default="reciprocity")
    ap.add_argument("--config")
    args = ap.parse_args()
    for seed in args.seeds:
        cfg = config.load(args.config, {"world": {"seed": seed}})
        w = World(cfg).generate()
        tpy = w.ticks_per_year()
        log = NullLog()
        e, calls, series = run_bots(w, int(args.years * tpy), args.bot, log, stats_every=tpy // 8)
        deaths = Counter(a.cause.split(" by ")[0] for a in w.agents.values() if not a.alive)
        kinds = Counter(ev["kind"] for ev in log.recent)
        print(f"seed {seed}: pop by half-season {[p for _, p in series]}; "
              f"calls/tick {calls / w.tick:.2f}; deaths {dict(deaths)}; births {kinds['birth']}, "
              f"arrivals {kinds['arrive']}, hunts {kinds['hunt']}")


if __name__ == "__main__":
    main()
