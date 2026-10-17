"""The speed gate's measure (grand.md section 8, Phase 1.3): seconds a world hour for a bots-only land, by season,
and a hash of everything that happened, so a change meant only for speed can be shown to leave the world as it was.

    PYTHONHASHSEED=0 python tools/speed.py --years 1                    # 2,000 people on a 192x192 continent
    PYTHONHASHSEED=0 python tools/speed.py --days 60 --old              # the old kind of land
    PYTHONHASHSEED=0 python tools/speed.py --days 150 --save w150.pkl   # keep the land at its end ...
    PYTHONHASHSEED=0 python tools/speed.py --load w150.pkl --days 5     # ... and time a later stretch of it
    ... --profile out.prof                                              # cProfile the timed stretch

Run with PYTHONHASHSEED=0: two runs of the same code then give the same hash, and a speed change must too.
"""
import argparse
import cProfile
import hashlib
import json
import os
import pickle
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from civ.engine import Engine  # noqa: E402
from civ.minds.bot import BotMind  # noqa: E402
from civ.world import TPD, DPS, SEASONS  # noqa: E402


def found(seed, people, size, old, towns=False):
    if towns:
        from civ.realm import generate
        return generate({"seed": seed, "people": people, "width": size, "height": size, "format": "towns1"})
    if old:
        from civ.gen import generate
        return generate({"seed": seed, "people": people, "width": size, "height": size, "bands": max(4, people // 16)})
    from civ.realm import generate
    return generate({"seed": seed, "people": people, "width": size, "height": size})


def digest(e, w, h=None):
    """A running hash of the events since the last call, and of where everyone stands."""
    h = h or hashlib.md5()
    ev = e.log.events
    start = getattr(e, "_speed_seen", 0)
    for x in ev[start:]:
        h.update(json.dumps(x, sort_keys=True, default=str).encode())
    e._speed_seen = len(ev)
    return h


def state_hash(w):
    people = [(p.id, p.alive, p.x, p.y, round(p.satiety, 6), sorted((k, v) for k, v in p.inv.items() if isinstance(v, (int, float))))
              for p in w.people.values()]
    return hashlib.md5(json.dumps([w.tick, people, len(w.buildings)], default=str).encode()).hexdigest()[:12]


class _MapLoad(dict):
    """Stands in for world.TileMap while unpickling (its __setitem__ needs attributes pickle sets only afterwards)."""


class _SetLoad(set):
    def __init__(self, *a):
        super().__init__(a[0] if a and not isinstance(a[0], int) else ())


class _Unpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if module == "civ.world" and name in ("TileMap", "TileSet"):
            return _MapLoad if name == "TileMap" else _SetLoad
        return super().find_class(module, name)


def load(path):
    """An engine and its minds as pickled by --save, with the world's tile maps and sets made whole again."""
    from civ.world import TileMap, TileSet
    with open(path, "rb") as f:
        e, mind = _Unpickler(f).load()
    w = e.w
    for k, v in list(w.__dict__.items()):
        if isinstance(v, _MapLoad):
            setattr(w, k, TileMap(w.w, w.h, dict(v)))
        elif isinstance(v, _SetLoad):
            setattr(w, k, TileSet(w.w, w.h, set(v)))
    return e, mind


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--people", type=int, default=2000)
    ap.add_argument("--size", type=int, default=192)
    ap.add_argument("--old", action="store_true", help="the old kind of land (civ/gen.py), not a continent")
    ap.add_argument("--towns", action="store_true", help="a towns world (docs/towns_spec.md): settlements laid out in metres")
    ap.add_argument("--years", type=float, default=0)
    ap.add_argument("--days", type=int, default=0)
    ap.add_argument("--save", help="pickle the land, its engine and minds at the end")
    ap.add_argument("--load", help="go on from a pickled land")
    ap.add_argument("--profile", help="cProfile the run to this file")
    a = ap.parse_args()
    if os.environ.get("PYTHONHASHSEED") != "0":
        print("note: PYTHONHASHSEED is not 0, so the hash is not comparable between runs")
    if a.load:
        e, mind = load(a.load)
        w = e.w
        e._speed_seen = len(e.log.events)
    else:
        w = found(a.seed, a.people, a.size, a.old, a.towns)
        e = Engine(w)
        mind = BotMind(e)
    hours = int(a.days * TPD + a.years * TPD * DPS * 4)
    h = hashlib.md5()
    pr = cProfile.Profile() if a.profile else None
    total, part, part_t = 0.0, 0, time.time()
    if pr:
        pr.enable()
    for i in range(hours):
        t0 = time.time()
        e.tick(mind.decide)
        total += time.time() - t0
        part += 1
        if w.tick % (TPD * DPS) == 0 or i == hours - 1:
            day = w.tick // TPD
            print(f"day {day:4d} ({SEASONS[(day // DPS - (1 if w.tick % (TPD * DPS) == 0 else 0)) % 4]:6s}) "
                  f"{(time.time() - part_t) / part:.3f} s/hour, alive {len(w.living())}, buildings {len(w.buildings)}", flush=True)
            part, part_t = 0, time.time()
        if len(e.log.events) > 20000:          # hash as we go, and keep memory flat on long runs
            digest(e, w, h)
    if pr:
        pr.disable()
        pr.dump_stats(a.profile)
    digest(e, w, h)
    print(f"{hours} hours: {total / max(1, hours):.3f} s/hour, {total:.0f} s; events {h.hexdigest()[:12]}, state {state_hash(w)}")
    if a.save:
        with open(a.save, "wb") as f:
            pickle.dump((e, mind), f, protocol=pickle.HIGHEST_PROTOCOL)


if __name__ == "__main__":
    main()
