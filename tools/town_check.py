"""Check a towns world (docs/towns_spec.md §11.1): its settlements are sound and its people live as households.

    python tools/town_check.py --days 10                 # a fresh bots-only towns continent, run, then checked
    python tools/town_check.py --state path/state.json.gz

Reports: settlements and their forms; households and dwellings per household (one each, §5.1); buildings overlapping
or off their tile or in the water; people whose position is off their tile; the refusals bots met, by reason; and
the hours someone's doing went wrong (exceptions caught by the engine), by kind. Exits 1 if anything is unsound.
"""
import argparse
import collections
import gzip
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from civ import geom as G, towns  # noqa: E402
from civ.content.towns import zone  # noqa: E402
from civ.world import World  # noqa: E402


def check(w, events=()):
    bad = []
    out = {"sites": len(w.sites), "forms": dict(collections.Counter(s.form for s in w.sites.values()))}
    # households: a dwelling's owner and partner; dwellings per household
    homes = collections.defaultdict(list)
    for b in w.buildings.values():
        if zone(b.kind) == "dwelling" and b.ruin is None and b.done:
            homes[b.owner].append(b.id)              # (two who each had a home and then partnered keep both)
    # two homes of one owner both raised after the founding: what one home a household forbids (a home inherited
    # from kin, or kept from before one partnered, is no fault)
    many = {k: v for k, v in homes.items() if sum(1 for i in v if w.buildings[i].built > 0) > 1}
    out["households"] = len(homes)
    out["households with more than one home"] = len(many)
    if len(many) > max(2, len(homes) * 0.02):
        bad.append(f"{len(many)} households hold more than one home")
    # buildings: on their tile, dry, not on top of each other
    overl = offtile = wet = 0
    for s in w.sites.values():
        bs = [b for b in w.buildings_at(s.x, s.y) if b.pos and b.size and b.kind != "farm" and b.done]
        for i, a in enumerate(bs):
            ra = (a.pos[0], a.pos[1], a.size[0], a.size[1], a.angle)
            if w.tile_of(*a.pos) != (a.x, a.y):
                offtile += 1
            if towns.is_water(w, *a.pos):
                wet += 1
            for b in bs[i + 1:]:
                if G.overlap(ra, (b.pos[0], b.pos[1], b.size[0], b.size[1], b.angle), -0.05):
                    overl += 1
    out["overlapping building pairs"] = overl
    out["buildings off their tile"] = offtile
    out["buildings in water"] = wet
    if overl or offtile or wet:
        bad.append("buildings overlap, stray off their tile or stand in water")
    stray = sum(1 for p in w.living() if p.pos and w.tile_of(*p.pos) != (p.x, p.y))
    out["people off their tile"] = stray
    if stray:
        bad.append(f"{stray} people stand off their tile")
    refused = collections.Counter(e.get("why", "")[:70] for e in events if e.get("kind") == "refused")
    out["refused, top"] = refused.most_common(12)
    wrong = collections.Counter(e.get("why") for e in events if e.get("kind") == "refused" and "went wrong" in e.get("text", ""))
    out["doings that went wrong"] = dict(wrong)
    if sum(wrong.values()):
        bad.append(f"{sum(wrong.values())} doings went wrong (exceptions)")
    return out, bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--state")
    ap.add_argument("--days", type=int, default=5)
    ap.add_argument("--people", type=int, default=600)
    ap.add_argument("--size", type=int, default=96)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--plain", action="store_true", help="the same land without towns, to compare refusals")
    a = ap.parse_args()
    if a.state:
        op = gzip.open if a.state.endswith(".gz") else open
        with op(a.state, "rt") as f:
            w = World.from_dict(json.load(f))
        events = []
    else:
        from civ.realm import generate
        from civ.engine import Engine
        from civ.minds.bot import BotMind
        w = generate({"seed": a.seed, "people": a.people, "width": a.size, "height": a.size, **({} if a.plain else {"format": "towns1"})})
        e = Engine(w)
        mind = BotMind(e)
        t0 = time.time()
        for _ in range(a.days * 12):
            e.tick(mind.decide)
        events = e.log.events
        print(f"{a.days} days in {time.time() - t0:.0f} s")
    out, bad = check(w, events)
    for k, v in out.items():
        print(f"{k}: {v}")
    print("SOUND" if not bad else "UNSOUND: " + "; ".join(bad))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
