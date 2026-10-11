"""Profile a 2,000-person, 192x192 continent (the speed gate's land, docs/grand.md Phase 1.3; docs/speed.md):
ten days to settle, then ten days under cProfile. Prints the seconds for the ten days and the top functions.

    python tools/speed_profile.py [--sort tottime|cumulative] [--top 35] [--days 10]
"""
import argparse
import cProfile
import os
import pstats
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from civ.engine import Engine  # noqa: E402
from civ.minds.bot import BotMind  # noqa: E402
from civ.realm import generate as found  # noqa: E402
from civ.world import TPD  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--sort", default="tottime")
ap.add_argument("--top", type=int, default=35)
ap.add_argument("--days", type=int, default=10)
ap.add_argument("--people", type=int, default=2000)
ap.add_argument("--size", type=int, default=192)
a = ap.parse_args()
w = found({"seed": 1, "people": a.people, "width": a.size, "height": a.size})
e = Engine(w)
m = BotMind(e)
for _ in range(TPD * 10):
    e.tick(m.decide)
t0 = time.time()
pr = cProfile.Profile()
pr.enable()
for _ in range(TPD * a.days):
    e.tick(m.decide)
pr.disable()
dt = time.time() - t0
print(f"{a.days} days: {dt:.1f} s ({dt / (TPD * a.days):.3f} s a world hour); alive {len(w.living())}")
pstats.Stats(pr).sort_stats(a.sort).print_stats(a.top)
