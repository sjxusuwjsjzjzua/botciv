"""Bots-only civ worlds across seeds: does the society live, and how far does it climb?

    python tools/civ_balance.py --seeds 1 2 --years 1 --people 120
    python tools/civ_balance.py --random --minutes 40 --years 4 --json out.jsonl   # the bots.yml farm

Reports per seed and overall: population by year, deaths by cause, births, the highest era with a
craft practised to able (0.3), the crafts reached, buildings, things made, trades, teachings,
groups and pledges, and the most common refusals (steps the engine would not do).
--json appends one compact line per world (rules version, code, seed, outcome) for tools/bot_stats.py;
--random with --minutes runs fresh seeds until the time is spent."""
import argparse
import json
import os
import random
import subprocess
import statistics as st
import sys
import time
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from civ.census import measures, measures_text  # noqa: E402
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
            "tpd": TPD, "grand": measures(w, ev, years), "ev_orders": [x for x in ev if x["kind"] == "order"]}


METALS = ("copper", "tin", "bronze", "iron", "steel", "gold")


def record(r, a):
    """One world, compact: what tools/bot_stats.py reads."""
    from civ.prompt import RULES_VERSION
    code = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                          cwd=os.path.dirname(os.path.abspath(__file__))).stdout.strip()
    k = r["kinds"]
    return {"rules": RULES_VERSION, "code": code, "seed": r["seed"], "years": a.years, "people": a.people,
            "size": a.size, "alive": r["alive"], "pop": r["pop"], "births": r["births"], "deaths": dict(r["deaths"]),
            "era": r["era"], "able": len(r["able"]), "secs": round(r["secs"]),
            "built": sum(r["builds"].values()), "made": sum(r["made"].values()),
            "counts": {x: k[x] for x in ("hunt", "tame", "trade", "teach", "deal", "group", "steal", "attack", "write", "refused", "order")},
            "obeyed": sum(x.get("obeyed", 0) for x in r["ev_orders"]), "refused_orders": sum(x.get("refused", 0) for x in r["ev_orders"]),
            "refused": dict(r["refused"].most_common(8)),
            "metal": sum(v for k, v in r["made"].items() if any(m in k for m in METALS)), "grand": r["grand"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2])
    ap.add_argument("--years", type=float, default=1)
    ap.add_argument("--people", type=int, default=120)
    ap.add_argument("--size", type=int, default=80)
    ap.add_argument("--json", default="", help="append one compact line per world to this file")
    ap.add_argument("--random", action="store_true", help="fresh random seeds in place of --seeds")
    ap.add_argument("--minutes", type=float, default=0, help="with --random: start worlds until this is spent")
    a = ap.parse_args()
    rs = []
    t0 = time.time()
    seeds = iter(a.seeds) if not a.random else iter(lambda: random.SystemRandom().randrange(10 ** 6, 10 ** 9), None)
    for s in seeds:
        if a.random and a.minutes and rs and (time.time() - t0) + st.mean(r["secs"] for r in rs) > a.minutes * 60:
            break
        r = run(s, a.years, a.people, a.size)
        rs.append(r)
        if a.json:
            with open(a.json, "a") as f:
                f.write(json.dumps(record(r, a)) + "\n")
        print(f"seed {s}: population by season {r['pop']}, alive {r['alive']}, births {r['births']}, "
              f"deaths {dict(r['deaths'])}; era {r['era']}; {r['secs']:.0f}s")
        print(f"  able at: {', '.join(r['able'])}")
        print(f"  built: {dict(r['builds'].most_common(12))}")
        print(f"  made: {dict(r['made'].most_common(14))}")
        k = r["kinds"]
        print(f"  hunts {k['hunt']}, tamed {k['tame']}, trades {k['trade']}, posts {k['post']}, teachings {k['teach']}, "
              f"deals {k['deal']}, pledges {k['pledge']}, groups {k['group']}, thefts {k['steal']}, attacks {k['attack']}, "
              f"kept {k['promise_kept']}, broken {k['promise_broken']}, crafts lost {k['craft_lost']}, writings {k['write']}, laws {k['law']}, markets {r['builds'].get('market', 0)}, schools {r['builds'].get('school', 0)}, fished thin {k['fished_thin']}, hired {k['hire']}, mended {k['mend']}, fell {k['ruin']}")
        orders = r["ev_orders"]
        print(f"  orders {len(orders)}: obeyed {sum(x.get('obeyed', 0) for x in orders)}, refused {sum(x.get('refused', 0) for x in orders)}")
        metal = {k: v for k, v in r["made"].items() if any(m in k for m in METALS)}
        print(f"  metal made: {metal or 'none'}")
        print(f"  refused: {dict(r['refused'].most_common(6))}")
        print(f"  grandeur: {measures_text(r['grand'])}")
    print(f"\nall: era reached {[r['era'] for r in rs]}, alive {[r['alive'] for r in rs]}, "
          f"mean seconds a year {st.mean(r['secs'] for r in rs) / a.years:.0f}")


if __name__ == "__main__":
    main()
