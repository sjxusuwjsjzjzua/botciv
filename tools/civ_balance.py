"""Bots-only civ worlds across seeds: does the society live, and how far does it climb?

    python tools/civ_balance.py --seeds 1 2 --years 1 --people 120

Reports per seed and overall: population by year, deaths by cause, births, the highest era with a
craft practised to able (0.3), the crafts reached, buildings, things made, trades, teachings,
groups and pledges, and the most common refusals (steps the engine would not do)."""
import argparse
import os
import statistics as st
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from civ.content import CRAFTS  # noqa: E402
from civ.engine import Engine  # noqa: E402
from civ.gen import generate  # noqa: E402
from civ.minds.bot import BotMind  # noqa: E402
from civ.world import TPY, TPD  # noqa: E402


def run(seed, years, people, size):
    w = generate({"seed": seed, "people": people, "width": size, "height": size, "bands": max(4, people // 16)})
    e = Engine(w)
    mind = BotMind(e)
    pops = []
    t0 = time.time()
    for i in range(int(years * TPY)):
        e.tick(mind.decide)
        if w.tick % (TPY // 4) == 0:
            pops.append(len(w.living()))
    ev = e.log.events
    kinds = Counter(x["kind"] for x in ev)
    reached = {c: max((p.skill(c) for p in w.people.values()), default=0) for c in CRAFTS}
    able = [c for c, s in reached.items() if s >= 0.3]
    era = max((CRAFTS[c]["era"] for c in able), default=0)
    return {"seed": seed, "pop": pops, "alive": len(w.living()), "secs": time.time() - t0,
            "deaths": Counter(x.get("cause", "?").split(" by ")[0] for x in ev if x["kind"] == "death"),
            "births": kinds["birth"], "era": era, "able": sorted(able, key=lambda c: (CRAFTS[c]["era"], c)),
            "builds": Counter(x.get("building") for x in ev if x["kind"] == "build"),
            "made": Counter(x.get("item") for x in ev if x["kind"] == "made"),
            "kinds": kinds, "refused": Counter(x.get("why", "")[:70] for x in ev if x["kind"] == "refused"),
            "tpd": TPD}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2])
    ap.add_argument("--years", type=float, default=1)
    ap.add_argument("--people", type=int, default=120)
    ap.add_argument("--size", type=int, default=80)
    a = ap.parse_args()
    rs = []
    for s in a.seeds:
        r = run(s, a.years, a.people, a.size)
        rs.append(r)
        print(f"seed {s}: population by season {r['pop']}, alive {r['alive']}, births {r['births']}, "
              f"deaths {dict(r['deaths'])}; era {r['era']}; {r['secs']:.0f}s")
        print(f"  able at: {', '.join(r['able'])}")
        print(f"  built: {dict(r['builds'].most_common(12))}")
        print(f"  made: {dict(r['made'].most_common(14))}")
        k = r["kinds"]
        print(f"  hunts {k['hunt']}, tamed {k['tame']}, trades {k['trade']}, posts {k['post']}, teachings {k['teach']}, "
              f"deals {k['deal']}, pledges {k['pledge']}, groups {k['group']}, thefts {k['steal']}, attacks {k['attack']}, "
              f"kept {k['promise_kept']}, broken {k['promise_broken']}, crafts lost {k['craft_lost']}")
        print(f"  refused: {dict(r['refused'].most_common(6))}")
    print(f"\nall: era reached {[r['era'] for r in rs]}, alive {[r['alive'] for r in rs]}, "
          f"mean seconds a year {st.mean(r['secs'] for r in rs) / a.years:.0f}")


if __name__ == "__main__":
    main()
