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
