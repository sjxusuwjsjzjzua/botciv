"""Is the world in balance? Bots-only runs across seeds, measured against targets.

    python tools/balance.py                      # 6 seeds, 4 years, mixed bots
    python tools/balance.py --seeds 1 2 3 --years 6 --bot mixed --set resources.farm_max_seeds=6

Mixed bots give each person one of three minds (careless forager, tit-for-tat
neighbour, planner), so the runs show whether care pays: whether planners end
up richer and live longer, which is where inequality should come from.

Targets (a world worth watching, not a solved one):
- the people never die out, and the population stays about 8-22 across years;
- starvation is common but not nearly every death;
- children are born, and strangers still arrive;
- wealth is unequal (Gini of worth about 0.3-0.6) and planners hold more than foragers;
- farms, stores and smoking are used when someone plans.
--set changes any setting for the run, for trying a change before making it.
"""
import argparse
import os
import statistics as st
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from botciv import config  # noqa: E402
from botciv.engine import Engine  # noqa: E402
from botciv.sim import make_bot  # noqa: E402
from botciv.standing import gini, standing  # noqa: E402
from botciv.world import World  # noqa: E402


class Collect:
    """A log that keeps events and the daily census, not position frames."""

    def __init__(self):
        self.recent, self.census = [], []

    def write(self, obj, *_):
        k = obj.get("kind")
        if k == "census":
            self.census.append(obj)
        elif k != "frame":
            self.recent.append(obj)

    def close(self):
        pass


def parse_sets(sets):
    over = {}
    for s in sets or []:
        path, val = s.split("=", 1)
        try:
            val = eval(val, {}, {})          # numbers, lists, dicts written as Python
        except Exception:
            pass
        d = over
        keys = path.split(".")
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = val
    return over


def run(seed, years, bot, over, config_path=None):
    cfg = config.load(config_path, config.deep_merge(over, {"world": {"seed": seed}}))
    w = World(cfg).generate()
    log = Collect()
    e = Engine(w, log)
    mind = make_bot(bot, e)
    kind = mind.kind if hasattr(mind, "kind") else (lambda a: bot)
    tpy = w.ticks_per_year()
    pops, seasons = [], defaultdict(list)
    for _ in range(int(years * tpy)):
        e.tick(mind.decide)
        if w.tick % w.tpd() == 0:
            pops.append(len(w.living()))
            seasons[w.season()].append(len(w.living()))
    ev = Counter(x["kind"] for x in log.recent)
    deaths = Counter("wolves" if "wolves" in x.get("cause", "") else x.get("cause", "?").split(" by ")[0]
                     for x in log.recent if x["kind"] == "death")
    builds = Counter(x.get("what") or x["text"].split(" built a ")[-1].split(" ")[0]
                     for x in log.recent if x["kind"] == "build")
    ginis = [gini([c[1] for c in row["c"]]) for row in log.census[w.tpd() * 0:]]
    rot = [row.get("rot", 0) for row in log.census]
    by_kind = defaultdict(lambda: {"worth": [], "lived": [], "starved": 0, "n": 0})
    for a in w.agents.values():
        k = kind(a)
        by_kind[k]["n"] += 1
        end = a.died if a.died is not None else w.tick
        by_kind[k]["lived"].append((end - a.born) / w.tpd())
        if a.cause == "starved":
            by_kind[k]["starved"] += 1
        if a.alive:
            by_kind[k]["worth"].append(standing(w, a)[0])
    return {"seed": seed, "pop": pops, "seasons": {s: st.mean(v) for s, v in seasons.items()},
            "extinct": any(p == 0 for p in pops), "deaths": deaths, "births": ev["birth"], "arrivals": ev["arrive"],
            "gini": st.mean(ginis[len(ginis) // 4:]) if ginis else 0, "rot": st.mean(rot) if rot else 0,
            "builds": builds, "plant": ev["plant"], "smoke": ev["smoke"], "technique": ev["technique"],
            "pledge": ev["pledge"], "deal": ev["deal"], "steal": ev["steal"] + ev["steal_fail"], "seize": ev["seize"],
            "crop": ev["take_crop"], "handed": ev["give_building"], "heirs": ev["bequeath"],
            "group": ev["group_found"], "join": ev["join"], "teach": ev["teach"], "tell_of": ev["tell_of"],
            "kept": ev["promise_kept"], "broken": ev["promise_broken"],
            "attack": ev["attack"], "hire": ev["hire"], "served": ev["service_end"],
            "left": ev["service_left"] + ev["dismiss"], "post": ev["post"], "trade": ev["trade"],
            "by_kind": by_kind, "years": years}


def verdict(rs, cfg=None):
    cfg = cfg or config.load()
    lo = max(8, round(0.55 * cfg["world"]["agents"]))      # the land should hold most of its people...
    hi = cfg["world"]["max_population"]                    # ...and not overflow
    pops = [p for r in rs for p in r["pop"][len(r["pop"]) // 4:]]
    deaths = sum((r["deaths"] for r in rs), Counter())
    starved = deaths["starved"] / max(1, sum(deaths.values()))
    years = sum(r["years"] for r in rs)
    worth = defaultdict(list)
    for r in rs:
        for k, v in r["by_kind"].items():
            worth[k] += v["worth"]
    checks = [
        ("never dies out", not any(r["extinct"] for r in rs), "extinct in " + ", ".join(str(r["seed"]) for r in rs if r["extinct"])),
        (f"population {lo}-{hi} after the first year", lo <= min(pops) and max(pops) <= hi if pops else False,
         f"ranged {min(pops) if pops else '-'}-{max(pops) if pops else '-'}"),
        ("starvation under 70% of deaths", starved < 0.7, f"{starved:.0%}"),
        ("children born (2+ a year)", sum(r["births"] for r in rs) / years >= 2, f"{sum(r['births'] for r in rs) / years:.1f} a year"),
        ("unequal (Gini 0.3-0.6)", 0.3 <= st.mean(r["gini"] for r in rs) <= 0.6, f"{st.mean(r['gini'] for r in rs):.2f}"),
    ]
    if worth.get("planner") and worth.get("simple"):
        p, s = st.mean(worth["planner"]), st.mean(worth["simple"])
        checks.append(("planners hold more than foragers", p > s * 1.3, f"planner {p:.0f} vs forager {s:.0f}"))
    return checks


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, nargs="+", default=[1, 2, 3, 4, 5, 6])
    ap.add_argument("--years", type=float, default=4)
    ap.add_argument("--bot", default="mixed")
    ap.add_argument("--set", action="append", help="setting=value, e.g. resources.farm_max_seeds=6")
    ap.add_argument("--config", default=None, help="a settings file, e.g. configs/large.toml")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)
    over = parse_sets(args.set)
    rs = [run(s, args.years, args.bot, over, args.config) for s in args.seeds]
    if not args.quiet:
        for r in rs:
            yearly = [min(r["pop"][i:i + 40]) for i in range(0, len(r["pop"]), 40)]
            print(f"seed {r['seed']}: lowest each year {yearly}; season means "
                  + ", ".join(f"{k} {v:.0f}" for k, v in r["seasons"].items())
                  + f"; births {r['births']}, arrivals {r['arrivals']}; deaths {dict(r['deaths'])}")
    n = len(rs)
    tot = lambda k: sum(r[k] for r in rs) / n
    print(f"\nper run: builds {dict(sum((r['builds'] for r in rs), Counter()))}; plantings {tot('plant'):.0f}, "
          f"smoked {tot('smoke'):.0f}, worked out smoking {tot('technique'):.0f}, pledges {tot('pledge'):.1f}, "
          f"deals {tot('deal'):.0f} (promises kept {tot('kept'):.0f}, broken {tot('broken'):.0f}), "
          f"groups {tot('group'):.1f} (joins {tot('join'):.0f}), teachings {tot('teach'):.0f}, "
          f"told of others {tot('tell_of'):.0f}, thefts {tot('steal'):.0f}, taken back by force {tot('seize'):.0f}, crops taken {tot('crop'):.0f}, "
          f"heirs named {tot('heirs'):.0f}, attacks {tot('attack'):.0f}, "
          f"hired {tot('hire'):.0f} (served out {tot('served'):.0f}, ended early {tot('left'):.0f}), "
          f"trades posted {tot('post'):.0f} (traded {tot('trade'):.0f}); "
          f"rot {st.mean(r['rot'] for r in rs):.1f} food worth a day")
    kinds = defaultdict(lambda: {"worth": [], "lived": [], "starved": 0, "n": 0})
    for r in rs:
        for k, v in r["by_kind"].items():
            kinds[k]["worth"] += v["worth"]
            kinds[k]["lived"] += v["lived"]
            kinds[k]["starved"] += v["starved"]
            kinds[k]["n"] += v["n"]
    for k, v in sorted(kinds.items()):
        print(f"  {k:12s} people {v['n']:3d}; worth of the living {st.mean(v['worth']) if v['worth'] else 0:5.1f}; "
              f"days lived {st.mean(v['lived']):5.1f}; starved {v['starved'] / max(1, v['n']):.0%}")
    print()
    ok = 0
    cfg = config.load(args.config)
    for name, good, detail in verdict(rs, cfg):
        ok += good
        print(f"  [{'x' if good else ' '}] {name}: {detail}")
    print(f"\n{ok}/{len(verdict(rs, cfg))} targets met")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
