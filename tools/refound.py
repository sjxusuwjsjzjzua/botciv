"""Re-found a saved world as a towns world on the large land (towns_spec §10, WP6; civ/refound.py), check it, and
write it.

    python tools/refound.py --state <dir with state.json.gz> --out <dir> [--days 2]

Prints the report (households, settlements, the largest by people, buildings kept and removed by kind, goods lost),
runs the new world --days with bots standing in for every mind, and `town_check`s it. Writes <out>/state.json.gz only
when it is sound. Nothing is published: found-world.yml decides that.
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))
from civ.refound import refound  # noqa: E402
from civ.run import load, save  # noqa: E402
from civ.world import TPD  # noqa: E402
import town_check  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state", required=True)
    ap.add_argument("--out", default="")
    ap.add_argument("--days", type=float, default=2)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    t0 = time.time()
    old = load(a.state)
    print(f"read {len(old.living())} people, {len(old.buildings)} buildings, {old.w} x {old.h} in {time.time() - t0:.0f} s")
    t0 = time.time()
    w, rep = refound(old.to_dict(), a.seed)
    del old
    print(f"re-founded in {time.time() - t0:.0f} s")
    print(json.dumps({k: v for k, v in rep.items() if k not in ("kept", "removed")}))
    print("kept:", dict(sorted(rep["kept"].items(), key=lambda kv: -kv[1])))
    print("removed:", dict(sorted(((k, v) for k, v in rep["removed"].items() if v), key=lambda kv: -kv[1])))
    from civ.engine import Engine
    from civ.minds.bot import BotMind
    e = Engine(w)
    mind = BotMind(e)
    seats = {p.id: p.mind for p in w.living()}
    for p in w.living():
        p.mind = "bot"                          # the check runs bots in every seat; the seats are given back after
    t0 = time.time()
    for _ in range(int(a.days * TPD)):
        e.tick(mind.decide)
    for p in w.people.values():
        if p.id in seats:
            p.mind = seats[p.id]
    out, bad = town_check.check(w, e.log.events)
    print(out)
    print(f"{a.days} days in {time.time() - t0:.0f} s; alive {len(w.living())}")
    if bad:
        print("NOT SOUND:", bad[:10])
        return 1
    print("SOUND")
    if a.out:
        os.makedirs(a.out, exist_ok=True)
        save(w, a.out)
        print("written", os.path.join(a.out, "state.json.gz"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
