"""How much each person has and commands, for watching wealth and power form.

Nothing here reaches the people: it is measured from the world's true state,
logged once a day as a census, and shown in the viewer. Worth is a rough
common scale, one unit about a day's berry picking: food counts what it feeds,
materials what they take to gather, made things more.
"""
from . import items as I

WORTH = {"wood": 1, "stone": 1, "fibre": 0.5, "hide": 2, "bone": 1, "seeds": 1, "rope": 2, "spear": 6,
         "axe": 6, "net": 6, "basket": 4, "pot": 4, "cloak": 6, "snare": 2, "necklace": 5, "drum": 5,
         "poultice": 2, "flour": 1}
BUILDING = {"store": 5, "shelter": 9, "wall": 2, "farm": 2, "fire": 1, "monument": 4}


def worth(inv):
    return sum(n * WORTH.get(k, I.ITEMS.get(k, {}).get("worth", I.ITEMS.get(k, {}).get("food", 0))) for k, n in inv.items())


def standing(w, a):
    """(wealth, followers): what a person carries, holds in stores and has built,
    and how many others are in groups they lead or in their service."""
    wealth = worth(a.inventory)
    for s in w.structures.values():
        if s.owner == a.id and s.done:
            wealth += BUILDING.get(s.kind, 0) + (worth(s.inventory) if s.kind == "store" else 0)
            if s.kind == "farm" and s.seeds:
                wealth += s.seeds * 2
    followers = sum(len(g.members) - 1 for g in w.groups.values()
                    if g.dissolved is None and g.leader == a.id)
    followers += sum(1 for s in getattr(w, "services", []) if not s["done"] and s["master"] == a.id)
    return round(wealth, 1), followers


def gini(values):
    """0 when everyone has the same, near 1 when one has everything."""
    v = sorted(x for x in values if x >= 0)
    n, total = len(v), sum(v)
    if n < 2 or total <= 0:
        return 0.0
    cum = sum((i + 1) * x for i, x in enumerate(v))
    return round((2 * cum) / (n * total) - (n + 1) / n, 3)
