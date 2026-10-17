"""world5's measures (world5.md §4-§7, gate of step 4): what life between settlements, daily life, professions and
land look like in a bots-only towns world, by year. Run before and after each step-4 mechanic.

    python tools/world5_measures.py [--years 3] [--people 600] [--size 192] [--upsample 2] [--seed 5]

Per year:
  far        adults who were 10+ km from home at some hour (a journey), and traders among them
  far_trade  trades and deals between people whose homes are 10+ km apart; all trades and deals
  home       share of the housed at their home's tile at night (aim 90%+)
  green      share of those in a settlement at its green in the evening
  special    in settlements of 50+: share of adults who made 5+ things and sowed or reaped nothing (aim 40%+ in towns)
  top_tenth  share of all things made by the top tenth of makers (aim 60%+)
  strips     households holding fields; the most held; land Gini over housed households; holding 10+
  tenants    tenancies running
"""
import argparse
import collections
import math
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from civ.engine import Engine  # noqa: E402
from civ.minds.bot import BotMind  # noqa: E402
from civ.realm import generate  # noqa: E402
from civ.world import NIGHT_FROM, TPD, TPY, dist  # noqa: E402

FAR = 10        # km: a day's walk and more


def gini(xs):
    xs = sorted(xs)
    n, s = len(xs), sum(xs)
    if not n or not s:
        return 0.0
    return sum((2 * i - n + 1) * x for i, x in enumerate(xs)) / (n * s)


class Measures:
    def __init__(self, e):
        self.e, self.w = e, e.w
        self.year = None
        self.reset()

    def reset(self):
        self.far, self.night, self.home, self.eve, self.green = set(), 0, 0, 0, 0
        self.farmers = set()
        self.ev_from = len(self.e.log.events) if hasattr(self.e.log, "events") else 0

    def home_tile(self, p):
        b = self.w.buildings.get(p.home)
        return (b.x, b.y) if b else None

    def hour(self):
        w = self.w
        hr = w.hour()
        for p in w.living():
            act = (p.act or {}).get("do")
            if act in ("plant", "reap") or (act == "gather" and (p.act or {}).get("item") == "grain"):
                self.farmers.add(p.id)
            h = self.home_tile(p)
            if h is None or not p.adult(w.tick):
                continue
            if dist(p.x, p.y, *h) >= FAR:
                self.far.add(p.id)
            if hr == NIGHT_FROM + 1:
                self.night += 1
                self.home += (p.x, p.y) == h
        if hr == NIGHT_FROM - 1 and w.sites:
            greens = {(s.x, s.y): s for s in w.sites.values() if s.green}
            for p in w.living():
                s = greens.get((p.x, p.y))
                if s and p.pos:
                    self.eve += 1
                    self.green += math.hypot(p.pos[0] - s.green[0], p.pos[1] - s.green[1]) < max(s.green[2], s.green[3])

    def report(self):
        w, e = self.w, self.e
        evs = e.log.events[self.ev_from:] if hasattr(e.log, "events") else []
        made = collections.Counter()
        trades = far_trades = 0
        for ev in evs:
            k = ev.get("kind")
            who = ev.get("who") or []
            if k == "made" and who:
                made[who[0]] += ev.get("qty", 1) or 1
            if k in ("trade", "deal", "give") and len(who) >= 2:
                a, b = w.people.get(who[0]), w.people.get(who[1])
                ha, hb = a and self.home_tile(a), b and self.home_tile(b)
                trades += 1
                far_trades += bool(ha and hb and dist(*ha, *hb) >= FAR)
        tops = sorted(made.values(), reverse=True)
        top = sum(tops[:max(1, len(tops) // 10)]) / max(1, sum(tops))
        # settlements of 50+: residents by their home's settlement
        res = collections.defaultdict(list)
        for p in w.living():
            b = w.buildings.get(p.home)
            if b is not None and b.site is not None and p.adult(w.tick):
                res[b.site].append(p)
        big = [p for s, ps in res.items() if len(ps) >= 35 for p in ps]       # 35 adults is a settlement of 50+
        special = sum(1 for p in big if made[p.id] >= 5 and p.id not in self.farmers)
        held = collections.Counter()
        for b in w.buildings.values():
            if b.kind == "farm" and b.owner and b.owner > 0:
                o = w.people.get(b.owner)
                held[o.home if o and o.home else -b.owner] += 1
        housed = {p.home for p in w.living() if p.home}
        out = {
            "year": round(w.tick / TPY, 1), "alive": len(w.living()), "sites": len(w.sites),
            "far": len(self.far), "far_traders": sum(1 for i in self.far if w.people[i].vocation == "trader"),
            "far_trade": far_trades, "trades": trades,
            "home": round(self.home / max(1, self.night), 3), "green": round(self.green / max(1, self.eve), 3),
            "special": round(special / max(1, len(big)), 3), "in_big": len(big), "top_tenth": round(top, 3),
            "strips": len(held), "most": max(held.values(), default=0),
            "gini": round(gini([held.get(h, 0) for h in housed]), 3), "ten_plus": sum(v >= 10 for v in held.values()),
            "tenants": sum(1 for t in w.tenancies if not t["done"]),
        }
        self.reset()
        return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--years", type=float, default=3)
    ap.add_argument("--people", type=int, default=600)
    ap.add_argument("--size", type=int, default=192)
    ap.add_argument("--upsample", type=int, default=2)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--state", help="a saved towns world's directory (a re-founded one): every seat a bot")
    a = ap.parse_args()
    if a.state:
        from civ.run import load
        w = load(a.state)
        for p in w.living():
            p.mind = "bot"
    else:
        w = generate({"seed": a.seed, "people": a.people, "width": a.size, "height": a.size, "upsample": a.upsample,
                      "format": "towns1"})
    e = Engine(w)
    mind = BotMind(e)
    m = Measures(e)
    t0 = time.time()
    for i in range(int(a.years * TPY)):
        e.tick(mind.decide)
        m.hour()
        if (i + 1) % TPY == 0:
            print(m.report(), f"{time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
