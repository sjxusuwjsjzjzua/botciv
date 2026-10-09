"""Every thing that can be held, as data. The engine reads hooks, never names.

Fields (all optional but w):
  w       weight in the load
  worth   rough common value (a day's berry picking is about 1), for the viewer's wealth measure
          and as a hint to bots' prices; never shown to people
  food    fullness when eaten;  spoil: chance per hour that one unit carried goes bad
  era     when it first can exist (0 foraging .. 4 classical)
  tool    {use: factor}: the best held tool for a use does the work (wood, stone, fibre, reap, dig,
          butcher, hunt, fish, speed:<craft>)
  uses    a tool or garment wears out after this many uses
  wear    (slot, warmth, fine): worn by carrying it, one per slot (head neck over body wrist feet)
  weapon  added to a blow;  armour: taken off a blow received;  range: can strike this far
  carry   added to the load one can carry (the best one held)
  keep    food carried spoils this much as often (the best one held)
  fuel    hours of fire from one
  float   crosses water;  sail: moves on water this many steps an hour
  mount   walking steps an hour when riding (an animal item? no: a horse is kept in a pen and led)
  record  something written can be set on it (tablet, parchment, book)
  heal    health restored when used, and it ends a sickness
  coin    a unit of money
"""

ITEMS = {
    # ---- food ----
    "berries":       dict(w=0.2, worth=1, food=1, spoil=1 / 60, era=0),
    "dried_berries": dict(w=0.15, worth=1.2, food=1, spoil=1 / 3000, era=0),
    "nuts":          dict(w=0.2, worth=1.5, food=2, spoil=1 / 1500, era=0),
    "grain":         dict(w=0.2, worth=2, food=2, spoil=1 / 1500, era=0),
    "flour":         dict(w=0.2, worth=2, food=1, spoil=1 / 2000, era=1),
    "bread":         dict(w=0.3, worth=6, food=5, spoil=1 / 400, era=1),
    "porridge":      dict(w=0.4, worth=6, food=6, spoil=1 / 60, era=1),
    "meat":          dict(w=0.5, worth=4, food=4, spoil=1 / 70, era=0),
    "cooked_meat":   dict(w=0.5, worth=6, food=6, spoil=1 / 200, era=0),
    "smoked_meat":   dict(w=0.4, worth=5, food=4, spoil=1 / 3000, era=0),
    "salted_meat":   dict(w=0.4, worth=6, food=5, spoil=1 / 6000, era=1),
    "fish":          dict(w=0.5, worth=3, food=3, spoil=1 / 55, era=0),
    "smoked_fish":   dict(w=0.4, worth=4, food=3, spoil=1 / 3000, era=0),
    "milk":          dict(w=0.5, worth=3, food=3, spoil=1 / 30, era=1),
    "cheese":        dict(w=0.3, worth=7, food=5, spoil=1 / 4000, era=1),
    "beer":          dict(w=0.6, worth=5, food=3, spoil=1 / 2000, era=1),
    "honey":         dict(w=0.3, worth=6, food=3, spoil=0, era=0),
    # ---- from the land ----
    "wood":          dict(w=2.0, worth=1, era=0, fuel=3),
    "stone":         dict(w=2.5, worth=1, era=0),
    "fibre":         dict(w=0.4, worth=0.5, era=0),
    "reeds":         dict(w=0.4, worth=0.5, era=0),
    "seeds":         dict(w=0.1, worth=1, era=0),
    "hay":           dict(w=0.5, worth=0.5, era=1),
    "herbs":         dict(w=0.1, worth=2, spoil=1 / 800, era=0),
    "hide":          dict(w=1.0, worth=2, spoil=1 / 900, era=0),
    "bone":          dict(w=0.4, worth=1, era=0),
    "wool":          dict(w=0.4, worth=3, era=1),
    "clay":          dict(w=1.0, worth=1, era=0),
    "flint":         dict(w=0.8, worth=2, era=0),
    "flax":          dict(w=0.3, worth=1, era=1),
    "salt":          dict(w=0.5, worth=4, era=1),
    "sand":          dict(w=1.5, worth=0.5, era=3),
    "limestone":     dict(w=2.5, worth=1, era=3),
    "copper_ore":    dict(w=2.0, worth=3, era=2),
    "tin_ore":       dict(w=2.0, worth=6, era=2),
    "iron_ore":      dict(w=2.0, worth=2, era=3),
    "gold":          dict(w=0.2, worth=40, era=2),
    # ---- worked materials ----
    "rope":          dict(w=0.5, worth=2, era=0),
    "plank":         dict(w=1.5, worth=3, era=1),
    "charcoal":      dict(w=0.4, worth=1.5, era=2, fuel=8),
    "brick":         dict(w=0.8, worth=1.5, era=1),
    "leather":       dict(w=0.8, worth=5, era=1),
    "linen":         dict(w=0.4, worth=5, era=1),
    "woolcloth":     dict(w=0.5, worth=6, era=1),
    "dye":           dict(w=0.2, worth=4, era=1),
    "dyed_cloth":    dict(w=0.5, worth=12, era=1),
    "copper":        dict(w=1.0, worth=10, era=2),
    "tin":           dict(w=1.0, worth=14, era=2),
    "bronze":        dict(w=1.0, worth=16, era=2),
    "iron":          dict(w=1.0, worth=12, era=3),
    "steel":         dict(w=1.0, worth=25, era=3),
    "lime":          dict(w=1.0, worth=3, era=3),
    "mortar":        dict(w=1.5, worth=3, era=3),
    "glass":         dict(w=0.5, worth=15, era=3),
    "parchment":     dict(w=0.1, worth=6, era=4, record=True),
    "ink":           dict(w=0.2, worth=5, era=4),
    # ---- containers and carrying ----
    "basket":        dict(w=0.8, worth=4, era=0, carry=10),
    "leather_bag":   dict(w=0.8, worth=10, era=1, carry=18),
    "pot":           dict(w=2.0, worth=4, era=1, keep=0.5),
    "jar":           dict(w=2.0, worth=5, era=1),
    "cart":          dict(w=6.0, worth=45, era=2, carry=60),
    # ---- tools ----
    "stone_axe":     dict(w=2.0, worth=6, era=0, tool={"wood": 2}, uses=60, weapon=2),
    "flint_axe":     dict(w=1.5, worth=8, era=0, tool={"wood": 2}, uses=150, weapon=2),
    "bronze_axe":    dict(w=1.8, worth=40, era=2, tool={"wood": 3}, uses=900, weapon=3),
    "iron_axe":      dict(w=1.8, worth=35, era=3, tool={"wood": 3}, uses=1500, weapon=3),
    "flint_knife":   dict(w=0.4, worth=5, era=0, tool={"fibre": 2, "butcher": 2}, uses=100),
    "bronze_knife":  dict(w=0.5, worth=20, era=2, tool={"fibre": 2, "butcher": 3}, uses=400, weapon=1),
    "iron_knife":    dict(w=0.5, worth=18, era=3, tool={"fibre": 2, "butcher": 3}, uses=900, weapon=1),
    "spear":         dict(w=1.5, worth=6, era=0, tool={"hunt": 1}, uses=40, weapon=2),
    "flint_spear":   dict(w=1.5, worth=8, era=0, tool={"hunt": 1}, uses=100, weapon=2),
    "bronze_spear":  dict(w=1.6, worth=30, era=2, tool={"hunt": 2}, uses=500, weapon=3),
    "iron_spear":    dict(w=1.6, worth=28, era=3, tool={"hunt": 2}, uses=900, weapon=3),
    "bow":           dict(w=1.0, worth=12, era=1, tool={"hunt": 2, "lone_hunt": 1}, uses=250, weapon=2, range=3),
    "net":           dict(w=1.0, worth=6, era=0, tool={"fish": 3}, uses=60),
    "fishing_line":  dict(w=0.2, worth=4, era=0, tool={"fish": 2}, uses=60),
    "digging_stick": dict(w=0.8, worth=2, era=0, tool={"dig": 1.5}, uses=80),
    "flint_sickle":  dict(w=0.6, worth=6, era=1, tool={"reap": 2}, uses=150),
    "bronze_sickle": dict(w=0.8, worth=30, era=2, tool={"reap": 3}, uses=800),
    "iron_sickle":   dict(w=0.8, worth=26, era=3, tool={"reap": 3}, uses=1400),
    "bronze_pick":   dict(w=2.0, worth=35, era=2, tool={"stone": 2, "dig": 2}, uses=600),
    "iron_pick":     dict(w=2.0, worth=30, era=3, tool={"stone": 3, "dig": 3}, uses=1200),
    "needle":        dict(w=0.05, worth=2, era=0, tool={"speed:hideworking": 1.5, "speed:tailoring": 1.5}, uses=40),
    "mould":         dict(w=1.5, worth=4, era=2, uses=12),
    "hammer":        dict(w=1.5, worth=25, era=2, tool={"speed:smithing": 1.5}, uses=600),
    "potters_wheel": dict(w=8.0, worth=30, era=2, tool={"speed:pottery": 2}),
    "plough":        dict(w=6.0, worth=50, era=2, tool={"plough": 2}, uses=900),
    "iron_plough":   dict(w=6.0, worth=70, era=3, tool={"plough": 2.5}, uses=2000),
    # ---- boats ----
    "canoe":         dict(w=6.0, worth=25, era=1, float=True, sail=1, tool={"fish": 2}),
    "sailboat":      dict(w=10.0, worth=80, era=2, float=True, sail=3, carry=40, tool={"fish": 3}),
    "ship":          dict(w=20.0, worth=300, era=4, float=True, sail=4, carry=150),
    # ---- weapons and armour ----
    "club":          dict(w=1.5, worth=2, era=0, weapon=1, uses=100),
    "bronze_sword":  dict(w=1.5, worth=45, era=2, weapon=4, uses=500),
    "iron_sword":    dict(w=1.5, worth=40, era=3, weapon=4, uses=900),
    "steel_sword":   dict(w=1.4, worth=90, era=3, weapon=5, uses=2000),
    "shield":        dict(w=2.0, worth=10, era=1, armour=1, uses=150),
    "leather_armour": dict(w=3.0, worth=20, era=1, armour=1, uses=300),
    "bronze_armour": dict(w=5.0, worth=90, era=2, armour=2, uses=600),
    "iron_armour":   dict(w=5.0, worth=80, era=3, armour=3, uses=1000),
    # ---- clothes (worn by carrying them, one a slot) ----
    "hat":           dict(w=0.3, worth=3, era=0, wear=("head", 1, 0), uses=300),
    "fur_hat":       dict(w=0.4, worth=6, era=0, wear=("head", 2, 0), uses=400),
    "tunic":         dict(w=1.0, worth=5, era=0, wear=("body", 1, 0), uses=300),
    "linen_tunic":   dict(w=0.6, worth=12, era=1, wear=("body", 1, 1), uses=500),
    "wool_tunic":    dict(w=0.8, worth=14, era=1, wear=("body", 2, 1), uses=500),
    "fine_tunic":    dict(w=0.6, worth=30, era=1, wear=("body", 1, 2), uses=500),
    "cloak":         dict(w=1.5, worth=6, era=0, wear=("over", 2, 0), uses=240),
    "fur_coat":      dict(w=3.0, worth=16, era=0, wear=("over", 3, 0), uses=400),
    "wool_cloak":    dict(w=1.2, worth=20, era=1, wear=("over", 3, 1), uses=600),
    "robe":          dict(w=1.0, worth=40, era=1, wear=("over", 1, 2), uses=600),
    "shoes":         dict(w=0.6, worth=4, era=0, wear=("feet", 1, 0), uses=300),
    "boots":         dict(w=0.8, worth=12, era=1, wear=("feet", 2, 0), uses=500),
    # ---- ornaments and fine things ----
    "necklace":      dict(w=0.1, worth=5, era=0, wear=("neck", 0, 1)),
    "bracelet":      dict(w=0.1, worth=4, era=0, wear=("wrist", 0, 1)),
    "copper_bracelet": dict(w=0.1, worth=14, era=2, wear=("wrist", 0, 2)),
    "bronze_torc":   dict(w=0.3, worth=30, era=2, wear=("neck", 0, 3)),
    "gold_ring":     dict(w=0.05, worth=60, era=2, wear=("wrist", 0, 4)),
    "gold_necklace": dict(w=0.1, worth=120, era=2, wear=("neck", 0, 5)),
    "glass_beads":   dict(w=0.1, worth=30, era=3, wear=("neck", 0, 3)),
    "figurine":      dict(w=0.3, worth=5, era=1),
    "drum":          dict(w=2.0, worth=5, era=0),
    "flute":         dict(w=0.2, worth=6, era=0),
    "glassware":     dict(w=0.8, worth=40, era=3),
    # ---- healing ----
    "poultice":      dict(w=0.2, worth=3, era=0, heal=3, spoil=1 / 300),
    "remedy":        dict(w=0.2, worth=10, era=4, heal=6, spoil=1 / 1500),
    # ---- writing and money ----
    "tablet":        dict(w=1.0, worth=2, era=2, record=True),
    "book":          dict(w=1.0, worth=40, era=4, record=True),
    "coin":          dict(w=0.02, worth=5, era=3, coin=True),
}


def info(k):
    """An item's data; a written thing ("tablet:12", "parchment:3", "book:pottery") is its material."""
    if k in ITEMS:
        return ITEMS[k]
    return ITEMS.get(k.split(":", 1)[0], {"w": 0.5, "worth": 1})


def item(k):
    return info(k)


def food(k):
    return ITEMS[k].get("food", 0)


FOODS = [k for k, v in ITEMS.items() if v.get("food")]
WEARABLE = {k: v["wear"] for k, v in ITEMS.items() if "wear" in v}
SLOTS = ("head", "neck", "over", "body", "wrist", "feet")


def worn(inv):
    """What someone carrying inv wears, head to foot: one a slot, the warmest, then the finest."""
    out = []
    for slot in SLOTS:
        have = [k for k in inv if inv[k] and k in WEARABLE and WEARABLE[k][0] == slot]
        if have:
            out.append(max(have, key=lambda k: (WEARABLE[k][1], WEARABLE[k][2], ITEMS[k]["worth"])))
    return out


def warmth(inv):
    return sum(WEARABLE[k][1] for k in worn(inv))


def finery(inv):
    """How fine someone looks: the sum of what they wear's fineness."""
    return sum(WEARABLE[k][2] for k in worn(inv))


def best_tool(inv, use):
    """(item, factor) of the best held tool for a use, or (None, 1)."""
    best = (None, 1)
    for k in inv:
        if inv[k]:
            f = info(k).get("tool", {}).get(use)
            if f and f > best[1]:
                best = (k, f)
    return best


def best(inv, field):
    """The largest value of a field among held things (carry, keep is smallest), with its item."""
    vals = [(info(k)[field], k) for k in inv if inv[k] and field in info(k)]
    if not vals:
        return 0, None
    return (min(vals) if field == "keep" else max(vals))


def weight(inv):
    return sum(info(k)["w"] * n for k, n in inv.items())


def worth(inv):
    return sum(info(k)["worth"] * n for k, n in inv.items())


def add(inv, k, n=1):
    if n > 0:
        inv[k] = inv.get(k, 0) + n


def remove(inv, k, n=1):
    have = inv.get(k, 0)
    n = min(n, have)
    if n <= 0:
        return 0
    if have == n:
        del inv[k]
    else:
        inv[k] = have - n
    return n


def describe(inv):
    return ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in sorted(inv.items()) if v) or "nothing"


def pretty(k):
    if k.startswith("book:"):
        return f"a book on {k[5:].replace('_', ' ')}"
    if ":" in k:
        return f"a written {k.split(':')[0]}"
    return k.replace("_", " ")


# ---- what lies on the ground (grand world, Phase 1.1): nothing keeps there. Wood, fibre, cloth, leather and
# food rot or are carried off within days; stone, clay, pottery and ore are scattered and buried more slowly;
# metal rusts and is picked up over a season or two. A share lost each day:
GROUND_LOSS = {"metal": 0.02, "mineral": 0.05, "rest": 0.15}
_METAL = ("copper", "tin", "bronze", "iron", "steel", "gold", "coin")
_MINERAL = {"stone", "clay", "flint", "sand", "limestone", "bone", "brick", "glass", "glass_beads", "glassware", "pot",
            "jar", "tablet", "mould", "figurine"}


def ground_loss(k):
    base = str(k).split(":")[0]
    if base.endswith("_ore") or base in _MINERAL:
        return GROUND_LOSS["mineral"]
    if any(m in base for m in _METAL):
        return GROUND_LOSS["metal"]
    return GROUND_LOSS["rest"]
