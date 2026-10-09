"""The long record of a land: one line a season, for a world left to run for a long time (the long land,
botworld.yml). It counts what happened since the last line from the events as they are written, so a
run that keeps no event log (civ.run --no-frames) still knows how the people fared.

    python -m civ.run --dir world --bots --no-frames --history world/history.jsonl --minutes 35
"""
import json
from collections import Counter

from .content import BUILDINGS, CRAFTS
from .world import TPY

COUNTED = ("birth", "trade", "deal", "teach", "steal", "attack", "group", "tame", "hunt", "build", "made", "refused",
           "law", "pledge", "monument")


class Census:
    """Wraps an event log: passes every event on, and keeps the counts for the next census line."""

    def __init__(self, inner=None):
        self.inner = inner
        self.kinds = Counter()
        self.deaths = Counter()
        self.events = inner.events if inner is not None and hasattr(inner, "events") else []

    def write(self, ev):
        k = ev["kind"]
        if k in COUNTED:
            self.kinds[k] += 1
        if k == "death":
            self.deaths[str(ev.get("cause", "?")).split(" by ")[0]] += 1
        if self.inner is not None:
            self.inner.write(ev)

    def close(self):
        if self.inner is not None and hasattr(self.inner, "close"):
            self.inner.close()

    def line(self, w, known):
        """The census as the land stands, and what happened since the last; known: crafts already able
        somewhere (updated), so each line names the crafts first reached since the last."""
        living = w.living()
        top = {}
        for p in living:
            for c, s in p.skills.items():
                if c in CRAFTS:
                    top[c] = max(top.get(c, 0), s)
        able = {c for c, s in top.items() if s >= 0.3}
        firsts, lost = sorted(able - known), sorted(known - able)
        known.clear()
        known.update(able)
        roles = Counter()
        for b in w.buildings.values():
            if b.done:
                for r in BUILDINGS[b.kind]["roles"]:
                    roles[r] += 1
        goods = sorted(sum(v for v in p.inv.values() if isinstance(v, (int, float))) for p in living)
        n = len(goods)
        gini = (sum((2 * i - n + 1) * g for i, g in enumerate(goods)) / (n * sum(goods))) if n and sum(goods) else 0
        out = {"t": w.tick, "year": w.tick // TPY + 1, "season": w.season(), "alive": len(living),
               "ever": len(w.people), "births": self.kinds["birth"], "deaths": dict(self.deaths),
               "era": max((CRAFTS[c]["era"] for c in able), default=0), "able": len(able), "firsts": firsts, "lost": lost,
               "buildings": sum(1 for b in w.buildings.values() if b.done), "roles": dict(roles.most_common()),
               "groups": sum(1 for g in w.groups.values() if g.dissolved is None),
               "herds": len(w.herds), "beasts": sum(h["n"] for h in w.herds), "packs": len(w.packs),
               "gini": round(gini, 3), "counts": {k: self.kinds[k] for k in COUNTED if k != "birth"}}
        self.kinds.clear()
        self.deaths.clear()
        return out


def append(path, line):
    with open(path, "a") as f:
        f.write(json.dumps(line, separators=(",", ":")) + "\n")


# ---- grandeur (docs/grand.md section 9): is the world one of people who need one another? ----
def settlements(w, r=4):
    """Homes in clusters: two homes within r steps share a settlement. Sizes in people, largest first."""
    homes = {}
    for p in w.living():
        b = w.buildings.get(p.home)
        if b:
            homes.setdefault((b.x, b.y), []).append(p.id)
    spots = list(homes)
    parent = list(range(len(spots)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    cells = {}
    for i, (x, y) in enumerate(spots):
        cells.setdefault((x // r, y // r), []).append(i)
    for i, (x, y) in enumerate(spots):
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for j in cells.get((x // r + dx, y // r + dy), ()):
                    if j > i and max(abs(x - spots[j][0]), abs(y - spots[j][1])) <= r:
                        parent[root(i)] = root(j)
    size = Counter()
    for i, s in enumerate(spots):
        size[root(i)] += len(homes[s])
    return sorted(size.values(), reverse=True)


def measures(w, events, years):
    """What docs/grand.md section 9 asks of a world, from its state and the events of the last `years`:
    how many crafts each grown person is able at, how much of each craft's output its top tenth of makers
    make, how much of what is made changes hands, trades a person a year, goods lying on the ground,
    settlement sizes, and the share of deaths at others' hands."""
    from .content import RECIPES
    living = w.living()
    adults = [p for p in living if p.adult(w.tick)]
    able = [sum(1 for c, s in p.skills.items() if c in CRAFTS and s >= 0.3) for p in adults]
    made_by = {}                                    # craft -> Counter(maker -> units)
    made = 0
    outputs = {r["out"] for r in RECIPES}
    moved = 0
    trades = 0
    deaths = Counter()
    for ev in events:
        k = ev["kind"]
        if k == "made" and ev.get("who"):
            made_by.setdefault(ev.get("craft"), Counter())[ev["who"][0]] += ev.get("qty", 1)
            made += ev.get("qty", 1)
        elif k == "give" and ev.get("item") in outputs:
            moved += ev.get("qty", 1)
        elif k in ("trade", "deal"):
            trades += ev.get("times", 1) if k == "trade" else 1
            for side in ("give", "get"):
                moved += sum(n for it, n in (ev.get(side) or {}).items() if it in outputs)
        elif k == "death":
            deaths["violent" if str(ev.get("cause", "")).startswith("killed by") and "wolves" not in str(ev.get("cause")) else "other"] += 1
    top, total = 0, 0
    for c, by in made_by.items():
        units = sorted(by.values(), reverse=True)
        n = max(1, -(-len(units) // 10))
        top += sum(units[:n])
        total += sum(units)
    ground = sum(v for pile in w.piles.values() for v in pile.values() if isinstance(v, (int, float)))
    towns = settlements(w)
    groups = [g for g in w.groups.values() if g.dissolved is None]
    py = max(1, len(living)) * max(years, 1e-9)
    return {"able_per_adult": round(sum(able) / max(1, len(able)), 2),
            "top_tenth_share": round(top / total, 3) if total else None,
            "made": made, "moved_share": round(moved / made, 3) if made else None,
            "trades_per_person_year": round(trades / py, 3),
            "ground_per_person": round(ground / max(1, len(living)), 1),
            "settlements": len([s for s in towns if s >= 12]), "largest": towns[0] if towns else 0,
            "median_settlement": towns[len(towns) // 2] if towns else 0,
            "violent_deaths": deaths["violent"], "deaths": sum(deaths.values()),
            "groups": len(groups), "largest_group": max((len(g.members) for g in groups), default=0)}


def measures_text(m):
    return (f"able crafts per adult {m['able_per_adult']}; top tenth of makers make {m['top_tenth_share']}; "
            f"made goods changing hands {m['moved_share']}; trades a person a year {m['trades_per_person_year']}; "
            f"goods on the ground a person {m['ground_per_person']}; settlements of 12+ {m['settlements']} "
            f"(largest {m['largest']}, median {m['median_settlement']}); deaths at others' hands "
            f"{m['violent_deaths']} of {m['deaths']}; groups {m['groups']} (largest {m['largest_group']})")
