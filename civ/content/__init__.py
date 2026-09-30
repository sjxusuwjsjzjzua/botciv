"""All content, and the checks that it hangs together (run by tests/test_civ_content.py)."""
from .items import ITEMS
from .land import TERRAIN, DEPOSITS, WILD, TAME, PASSABLE, PREDATORS
from .buildings import BUILDINGS
from .crafts import CRAFTS, RECIPES, ANY


def raw_sources():
    """Everything obtained without a recipe: from terrain, deposits, animals and farms."""
    out = set()
    for t in TERRAIN.values():
        out |= set(t.get("yields", {}))
    out |= {d.get("gives", k) for k, d in DEPOSITS.items()}
    out |= {"meat", "hide", "bone", "fish", "seeds", "grain", "flax", "hay", "milk", "wool"}
    return out


def problems():
    """Every way the content does not hang together, as words (empty when all is well)."""
    bad = []
    have = raw_sources()
    for k in have:
        if k not in ITEMS:
            bad.append(f"source {k} is not an item")
    # what can be made, by rounds, from sources
    made = set(have)
    changed = True
    while changed:
        changed = False
        for r in RECIPES:
            if r["out"] in made:
                continue
            tools_ok = all(any(o in made for o in ANY.get(t, [t])) for t in r["tools"])
            if all(k in made for k in r["ins"]) and tools_ok:
                made.add(r["out"])
                changed = True
    for r in RECIPES:
        for k in list(r["ins"]) + [o for t in r["tools"] for o in ANY.get(t, [t])]:
            if k not in ITEMS:
                bad.append(f"recipe {r['out']}: {k} is not an item")
        if r["out"] not in ITEMS:
            bad.append(f"recipe makes unknown {r['out']}")
        if r["craft"] not in CRAFTS:
            bad.append(f"recipe {r['out']}: unknown craft {r['craft']}")
        if r["out"] not in made:
            bad.append(f"{r['out']} can never be made")
    for k, v in ITEMS.items():
        if k not in made:
            bad.append(f"item {k} can never be had")
    workshops = {c for b in BUILDINGS.values() for c in b["roles"].get("workshop", [])}
    for c, v in CRAFTS.items():
        for p in v["pre"]:
            if p not in CRAFTS:
                bad.append(f"craft {c}: unknown prerequisite {p}")
        if v["at"] and c not in workshops:
            bad.append(f"craft {c} is worked at a workshop, but no building lists it")
        if not [r for r in RECIPES if r["craft"] == c] and not v.get("practice"):
            bad.append(f"craft {c} makes nothing and has no practice")
    for k, b in BUILDINGS.items():
        for m in b["cost"]:
            if m not in made:
                bad.append(f"building {k} needs {m}, which can never be had")
        if b.get("craft") and b["craft"] not in CRAFTS:
            bad.append(f"building {k}: unknown craft {b['craft']}")
    # prerequisite chains have no loops and eras only rise
    for c, v in CRAFTS.items():
        for p in v["pre"]:
            if CRAFTS.get(p, {}).get("era", 9) > v["era"]:
                bad.append(f"craft {c} (era {v['era']}) needs {p} of a later era")
    return bad
