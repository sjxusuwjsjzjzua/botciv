"""Items, their properties, and the hidden recipe table."""

# weight, nutrition, spoil chance per unit per tick when carried (0 = keeps)
ITEMS = {
    "berries":     {"w": 0.2, "food": 1, "spoil": 1 / 60},
    "meat":        {"w": 0.5, "food": 4, "spoil": 1 / 70},
    "fish":        {"w": 0.5, "food": 3, "spoil": 1 / 55},
    "grain":       {"w": 0.2, "food": 2, "spoil": 1 / 1500},
    "cooked_meat": {"w": 0.5, "food": 6, "spoil": 1 / 200},
    "bread":       {"w": 0.3, "food": 5, "spoil": 1 / 500},
    "flour":       {"w": 0.2, "food": 1, "spoil": 1 / 2000},
    "seeds":       {"w": 0.1, "food": 0, "spoil": 0},
    "wood":        {"w": 2.0, "food": 0, "spoil": 0},
    "stone":       {"w": 2.5, "food": 0, "spoil": 0},
    "fibre":       {"w": 0.4, "food": 0, "spoil": 0},
    "hide":        {"w": 1.0, "food": 0, "spoil": 1 / 900},
    "bone":        {"w": 0.4, "food": 0, "spoil": 0},
    # made things
    "rope":        {"w": 0.5, "food": 0, "spoil": 0},
    "spear":       {"w": 1.5, "food": 0, "spoil": 0, "uses": 40},
    "axe":         {"w": 2.0, "food": 0, "spoil": 0, "uses": 50},
    "net":         {"w": 1.0, "food": 0, "spoil": 0, "uses": 60},
    "basket":      {"w": 0.8, "food": 0, "spoil": 0},
    "pot":         {"w": 2.0, "food": 0, "spoil": 0},
    "cloak":       {"w": 1.5, "food": 0, "spoil": 0, "uses": 240},
    "snare":       {"w": 0.5, "food": 0, "spoil": 0},
    "necklace":    {"w": 0.1, "food": 0, "spoil": 0},
    "drum":        {"w": 2.0, "food": 0, "spoil": 0},
    "poultice":    {"w": 0.2, "food": 0, "spoil": 1 / 300},
}

FOODS = [k for k, v in ITEMS.items() if v["food"] > 0]
TOOLS = [k for k, v in ITEMS.items() if "uses" in v]

# What each made thing does. Shown to an agent once it knows the recipe
# (or holds the thing), in the same short form for every item.
EFFECTS = {
    "rope": "needed to build a shelter; used in other things",
    "spear": "hunting succeeds more often; your blows hit harder",
    "axe": "you cut twice as much wood",
    "net": "fishing succeeds far more often",
    "basket": "you can carry 15 more",
    "pot": "food you carry spoils half as fast",
    "cloak": "keeps winter cold off you",
    "snare": "drop it on grass or forest; now and then it catches meat",
    "necklace": "does nothing; people may like it",
    "drum": "does nothing but make a sound people hear far off when you speak",
    "poultice": "eat it to heal 3 health",
    "cooked_meat": "food worth 6, keeps for days",
    "flour": "food worth 1; keeps almost forever",
    "bread": "food worth 5, keeps long",
}

# Each product has plausible ingredient pairs; the seed picks one per product,
# with no pair used twice. So reasoning helps, but only trying proves it.
CANDIDATES = {
    "rope": [("fibre", "fibre"), ("fibre", "hide")],
    "spear": [("stone", "wood"), ("bone", "wood")],
    "axe": [("stone", "wood"), ("rope", "stone"), ("bone", "stone")],
    "net": [("fibre", "rope"), ("rope", "rope"), ("rope", "wood")],
    "basket": [("fibre", "wood"), ("fibre", "rope")],
    "pot": [("stone", "stone"), ("fibre", "stone")],
    "cloak": [("fibre", "hide"), ("hide", "hide"), ("hide", "rope")],
    "snare": [("rope", "wood"), ("fibre", "wood"), ("bone", "rope")],
    "necklace": [("bone", "fibre"), ("bone", "rope"), ("fibre", "stone")],
    "drum": [("hide", "wood"), ("hide", "stone")],
    "poultice": [("berries", "fibre"), ("berries", "hide"), ("berries", "seeds")],
    "cooked_meat": [("meat", "wood")],
    "flour": [("grain", "stone")],
    "bread": [("flour", "wood"), ("flour", "grain")],
}


def pair(a, b):
    return "+".join(sorted((a, b)))


def make_recipes(rng):
    """Return {"a+b": product}. Backtracks so every product gets a unique pair."""
    products = list(CANDIDATES)
    rng.shuffle(products)
    options = {p: rng.sample(CANDIDATES[p], len(CANDIDATES[p])) for p in products}

    def solve(i, used, out):
        if i == len(products):
            return out
        p = products[i]
        for a, b in options[p]:
            k = pair(a, b)
            if k not in used:
                r = solve(i + 1, used | {k}, {**out, k: p})
                if r is not None:
                    return r
        return None

    res = solve(0, frozenset(), {})
    assert res is not None
    return res


def weight(inv):
    return sum(ITEMS[k]["w"] * n for k, n in inv.items())


def add(inv, item, n=1):
    if n > 0:
        inv[item] = inv.get(item, 0) + n


def remove(inv, item, n=1):
    have = inv.get(item, 0)
    n = min(n, have)
    if n <= 0:
        return 0
    if have - n == 0:
        del inv[item]
    else:
        inv[item] = have - n
    return n


def describe(inv):
    if not inv:
        return "nothing"
    return ", ".join(f"{k} {v}" for k, v in sorted(inv.items()))
