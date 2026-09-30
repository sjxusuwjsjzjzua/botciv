"""The crafts beyond two-thing pairs, as data the engine reads (rules w39).

The land holds more than berries, wood, stone and fibre: clay by some banks, flint and odd
stones in some rock, flax on rich soil. Techniques turn them into more: knapping flint,
firing clay, burning charcoal, weaving, sewing, smelting, alloying and casting. Each is worked
out by working a material at the right place (a kiln, loom or furnace, or by hand), with
honest word of how near the attempt came, or is taught by someone who knows, and is lost with
the last who knew. Nothing here says what anyone should do: every step pays on its own (a
sharper blade, a warmer coat, food that keeps, a harder axe, a bright torc).

A tier is added by writing rows here and tests, not by editing the engine.
"""

# Raw things found in the land (engine: gathered from a deposit on or beside you).
# where: the tile a deposit lies on. per: how many deposits for every 100 tiles of that kind
# (at least `least`), each holding `size`; renew: it grows back each spring (flax), else it is
# worked out for good.
DEPOSITS = {
    "clay":        {"where": "bank", "per": 10, "least": 3, "size": 40, "sym": ";", "name": "clay bank"},
    "flint":       {"where": "rock", "per": 12, "least": 3, "size": 25, "sym": "'", "name": "flint in the rock"},
    "flax":        {"where": "soil", "per": 12, "least": 3, "size": 8, "renew": True, "sym": "|", "name": "wild flax"},
    "green_stone": {"where": "rock", "per": 4, "least": 2, "size": 30, "sym": "$", "name": "green stone in the rock",
                    "cluster": True},
    "black_stone": {"where": "rock", "per": 1.5, "least": 1, "size": 16, "sym": "0", "name": "black stone in the rock",
                    "cluster": True, "far": "green_stone"},
}

# Buildings where work is done (added to engine.BUILD). A fire is one too.
STATIONS = {
    "kiln":    {"cost": {"clay": 4, "stone": 2}, "ticks": 4, "hp": 30, "sym": "K"},
    "loom":    {"cost": {"wood": 3, "rope": 2}, "ticks": 3, "hp": 15, "sym": "L"},
    "furnace": {"cost": {"brick": 6, "stone": 2}, "ticks": 6, "hp": 40, "sym": "U"},
}

# Techniques: what one knows how to do. try: the materials that, worked at `at` (None: by hand),
# may teach it; need: what must also be at hand for it to come right (else only a near miss);
# chance: per hour of work. The texts are what the worker is told.
TECHS = {
    "knapping": {"does": "knap flint into blades, axe heads and spear points", "at": None, "try": ["flint"],
                 "need": {}, "chance": 0.15,
                 "near": "You struck the flint; sharp flakes came away but broke. Struck with care, it might be shaped.",
                 "learned": "Striking the flint with care, you learned to knap it into sharp blades and heads."},
    "pottery": {"does": "fire clay in a kiln into pots, jars, bricks and moulds", "at": "kiln", "try": ["clay"],
                "need": {"wood": 1}, "chance": 0.15,
                "near": "The clay dried and cracked at the edges; it wants a steady heat around it, fed with wood.",
                "learned": "Fired steady in the kiln, the clay rang hard as stone: you learned to make pots, jars, bricks and moulds."},
    "charcoal": {"does": "burn wood slowly in a kiln into charcoal, which burns far hotter than wood", "at": "kiln",
                 "try": ["wood"], "need": {"wood": 3}, "chance": 0.15,
                 "near": "The wood smouldered black in the closed kiln; more of it, starved of air a while longer, might become something new.",
                 "learned": "Starved of air in the kiln, the wood became light black lumps that burn far hotter: charcoal."},
    "weaving": {"does": "weave flax (or, coarsely, fibre) into cloth on a loom", "at": "loom", "try": ["flax", "fibre"],
                "need": {}, "chance": 0.15,
                "near": "The threads slipped and tangled on the loom; spun finer and held taut, they might hold together.",
                "learned": "Held taut on the loom, the threads locked together: you learned to weave cloth."},
    "sewing": {"does": "sew hides and cloth into coats, boots, hats, tunics and robes with a needle", "at": None,
               "try": ["hide", "cloth"], "need": {"needle": 1}, "chance": 0.2,
               "near": "You tried to join the pieces, but nothing pierced them cleanly; a fine point of bone would carry a thread.",
               "learned": "With a needle and thread you learned to sew: coats, boots, hats, tunics and robes."},
    "smelting": {"does": "smelt green stone into copper and black stone into tin in a furnace with charcoal",
                 "at": "furnace", "try": ["green_stone", "black_stone"], "need": {"charcoal": 2}, "chance": 0.12,
                 "near": "The stone blackened and cracked in the furnace, but wood does not burn hot enough to melt it; something burning far hotter might.",
                 "learned": "In the charcoal's white heat, beads of shining metal ran from the stone: you learned to smelt."},
    "casting": {"does": "cast metal in the furnace into tools, blades and ornaments, in fired clay moulds",
                "at": "furnace", "try": ["copper", "bronze"], "need": {"charcoal": 1, "mould": 1}, "chance": 0.15,
                "near": "The metal ran soft in the heat but spread and cooled shapeless; poured into a fired clay mould it would take a shape.",
                "learned": "Poured into the mould, the metal cooled into the shape: you learned to cast tools, blades and ornaments."},
    "alloying": {"does": "melt copper with tin in a furnace into bronze, harder than either", "at": "furnace",
                 "try": ["copper", "tin"], "need": {"copper": 1, "tin": 1, "charcoal": 1}, "chance": 0.12,
                 "near": "The copper melted, but alone it stays soft; another metal melted into it might harden it.",
                 "learned": "Copper and tin melted together into a golden metal harder than either: bronze."},
}

# What each technique makes: out, how many, inputs used up, tools needed but kept, hours.
# The station is the technique's.
RECIPES = [
    {"out": "flint_knife", "n": 1, "in": {"flint": 1, "wood": 1}, "tech": "knapping", "hours": 2},
    {"out": "flint_axe", "n": 1, "in": {"flint": 2, "wood": 1, "rope": 1}, "tech": "knapping", "hours": 3},
    {"out": "flint_spear", "n": 1, "in": {"flint": 1, "wood": 2}, "tech": "knapping", "hours": 2},
    {"out": "needle", "n": 3, "in": {"bone": 1}, "tools": ["flint_knife"], "tech": "knapping", "hours": 2},
    {"out": "pot", "n": 1, "in": {"clay": 2, "wood": 1}, "tech": "pottery", "hours": 3},
    {"out": "jar", "n": 1, "in": {"clay": 3, "wood": 1}, "tech": "pottery", "hours": 3},
    {"out": "brick", "n": 4, "in": {"clay": 3, "wood": 1}, "tech": "pottery", "hours": 3},
    {"out": "mould", "n": 1, "in": {"clay": 2, "wood": 1}, "tech": "pottery", "hours": 3},
    {"out": "charcoal", "n": 3, "in": {"wood": 4}, "tech": "charcoal", "hours": 4},
    {"out": "cloth", "n": 1, "in": {"flax": 3}, "tech": "weaving", "hours": 3},
    {"out": "cloth", "n": 1, "in": {"fibre": 6}, "tech": "weaving", "hours": 4},
    {"out": "fur_coat", "n": 1, "in": {"hide": 4}, "tools": ["needle"], "tech": "sewing", "hours": 5},
    {"out": "boots", "n": 1, "in": {"hide": 2, "rope": 1}, "tools": ["needle"], "tech": "sewing", "hours": 3},
    {"out": "fur_hat", "n": 1, "in": {"hide": 2}, "tools": ["needle"], "tech": "sewing", "hours": 2},
    {"out": "linen_tunic", "n": 1, "in": {"cloth": 2}, "tools": ["needle"], "tech": "sewing", "hours": 3},
    {"out": "robe", "n": 1, "in": {"cloth": 3}, "tools": ["needle"], "tech": "sewing", "hours": 4},
    {"out": "copper", "n": 1, "in": {"green_stone": 2, "charcoal": 2}, "tech": "smelting", "hours": 4},
    {"out": "tin", "n": 1, "in": {"black_stone": 2, "charcoal": 2}, "tech": "smelting", "hours": 4},
    {"out": "bronze", "n": 3, "in": {"copper": 2, "tin": 1, "charcoal": 1}, "tech": "alloying", "hours": 4},
    {"out": "copper_axe", "n": 1, "in": {"copper": 2, "charcoal": 1, "wood": 1}, "tools": ["mould"], "tech": "casting", "hours": 3},
    {"out": "copper_knife", "n": 1, "in": {"copper": 1, "charcoal": 1}, "tools": ["mould"], "tech": "casting", "hours": 2},
    {"out": "copper_bracelet", "n": 1, "in": {"copper": 1, "charcoal": 1}, "tech": "casting", "hours": 2},
    {"out": "bronze_axe", "n": 1, "in": {"bronze": 2, "charcoal": 1, "wood": 1}, "tools": ["mould"], "tech": "casting", "hours": 3},
    {"out": "bronze_sickle", "n": 1, "in": {"bronze": 1, "charcoal": 1, "wood": 1}, "tools": ["mould"], "tech": "casting", "hours": 3},
    {"out": "bronze_sword", "n": 1, "in": {"bronze": 3, "charcoal": 1}, "tools": ["mould"], "tech": "casting", "hours": 4},
    {"out": "bronze_torc", "n": 1, "in": {"bronze": 1, "charcoal": 1}, "tech": "casting", "hours": 2},
]

# The best of what one holds does the work: (item, factor), best first.
TOOLS = {
    "wood": [("bronze_axe", 3), ("copper_axe", 3), ("flint_axe", 2), ("axe", 2)],
    "fibre": [("copper_knife", 2), ("flint_knife", 2)],
    "flax": [("copper_knife", 2), ("flint_knife", 2)],
    "grain": [("bronze_sickle", 2)],
    "hunt": [("flint_spear", 1), ("spear", 1)],             # each hunter with one adds to the chance
    "butcher": [("copper_knife", 2), ("flint_knife", 2)],   # meat more from a kill, per hunter with one
    "fight": [("bronze_sword", 4), ("copper_axe", 2), ("bronze_axe", 2), ("flint_spear", 2), ("spear", 2)],
}

# items: weight, worth (for the viewer's measure of wealth), uses (tools and clothes wear out)
ITEMS = {
    "clay": {"w": 1.0, "worth": 1}, "flint": {"w": 0.8, "worth": 2}, "flax": {"w": 0.3, "worth": 1},
    "green_stone": {"w": 2.0, "worth": 3}, "black_stone": {"w": 2.0, "worth": 5},
    "charcoal": {"w": 0.4, "worth": 1.5}, "cloth": {"w": 0.5, "worth": 4}, "brick": {"w": 0.8, "worth": 1.5},
    "copper": {"w": 1.0, "worth": 10}, "tin": {"w": 1.0, "worth": 14}, "bronze": {"w": 1.0, "worth": 16},
    "jar": {"w": 2.0, "worth": 5},
    "flint_knife": {"w": 0.4, "worth": 5, "uses": 100}, "flint_axe": {"w": 1.5, "worth": 8, "uses": 150},
    "flint_spear": {"w": 1.5, "worth": 8, "uses": 100}, "needle": {"w": 0.05, "worth": 2, "uses": 40},
    "mould": {"w": 1.5, "worth": 4, "uses": 12},
    "copper_axe": {"w": 1.8, "worth": 25, "uses": 350}, "copper_knife": {"w": 0.5, "worth": 15, "uses": 300},
    "bronze_axe": {"w": 1.8, "worth": 40, "uses": 900}, "bronze_sword": {"w": 1.5, "worth": 45, "uses": 500},
    "bronze_sickle": {"w": 0.8, "worth": 30, "uses": 800},
    "fur_coat": {"w": 3.0, "worth": 16, "uses": 400}, "boots": {"w": 0.8, "worth": 8, "uses": 400},
    "fur_hat": {"w": 0.4, "worth": 6, "uses": 400}, "linen_tunic": {"w": 0.6, "worth": 12, "uses": 500},
    "robe": {"w": 1.0, "worth": 18, "uses": 500},
    "copper_bracelet": {"w": 0.1, "worth": 14}, "bronze_torc": {"w": 0.3, "worth": 30},
}

# Worn: slot and warmth (one per slot is worn, the warmest then the finest).
WEAR = {"fur_hat": ("head", 2), "fur_coat": ("over", 3), "robe": ("over", 1), "linen_tunic": ("body", 1),
        "boots": ("feet", 2), "copper_bracelet": ("wrist", 0), "bronze_torc": ("neck", 0)}

EFFECTS = {
    "clay": "fired in a kiln by those who know pottery; a kiln is built of it",
    "flint": "knapped by hand into knives, axe heads and spear points",
    "flax": "woven on a loom into cloth",
    "green_stone": "an odd stone; some say fire changes it",
    "black_stone": "a heavy dark stone; some say fire changes it",
    "charcoal": "burns far hotter than wood: a furnace needs it",
    "cloth": "sewn into tunics and robes",
    "brick": "fired clay: a furnace is built of it",
    "copper": "a soft red metal, cast into tools and ornaments",
    "tin": "a soft white metal; melted with copper it makes bronze",
    "bronze": "a hard golden metal, cast into the best tools and blades",
    "jar": "in a store: the food in it spoils half as fast",
    "mould": "fired clay a metal is cast in (a tool: wears out)",
    "needle": "for sewing (a tool: wears out)",
    "flint_knife": "gather fibre and flax twice as fast; more meat from a kill",
    "flint_axe": "cut twice as much wood; lasts longer than a stone axe",
    "flint_spear": "hunting succeeds more often; your blows hit harder",
    "copper_axe": "cut three times as much wood; a blow with it hurts",
    "copper_knife": "gather fibre and flax twice as fast; more meat from a kill; lasts long",
    "bronze_axe": "cut three times as much wood; lasts very long; a blow with it hurts",
    "bronze_sickle": "reap grain twice as fast",
    "bronze_sword": "your blows hit far harder",
    "fur_coat": "worn: warmth 3",
    "boots": "worn: warmth 2",
    "fur_hat": "worn: warmth 2",
    "linen_tunic": "worn: warmth 1; fine cloth",
    "robe": "worn over: warmth 1; fine cloth",
    "copper_bracelet": "worn; shines; people may prize it",
    "bronze_torc": "worn at the neck; gleams; people may prize it",
}

TOOL_ITEMS = {"flint_knife", "flint_axe", "flint_spear", "needle", "mould", "copper_axe", "copper_knife",
              "bronze_axe", "bronze_sword", "bronze_sickle"}


def recipes_for(tech):
    return [r for r in RECIPES if r["tech"] == tech]


def recipe_text(r):
    ins = " + ".join(f"{k.replace('_', ' ')} {n}" for k, n in r["in"].items())
    tools = f", with a {' and '.join(t.replace('_', ' ') for t in r.get('tools', []))}" if r.get("tools") else ""
    out = r["out"].replace("_", " ") + (f" x{r['n']}" if r["n"] > 1 else "")
    return f"{out} = {ins}{tools} ({r['hours']}h)"


def tries(material):
    """The techniques a material may teach when worked."""
    return [t for t, v in TECHS.items() if material in v["try"]]
