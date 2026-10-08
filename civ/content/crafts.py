"""Crafts (techniques) and recipes: the known tree, era 0 (foraging) to era 4 (classical).

Everyone knows what exists and what it takes. Knowing how is skill, 0 to 1 a craft, learned by
practice (every try teaches, a failure more than a success) or by being taught, and lost with
the last who had it.

A craft: era; where it is worked (`at`: a building role "workshop" listing it, "hearth", or None
by hand); `pre`: other crafts one must have at least this skill in before trying; `does`: a few
words for people. Some crafts make nothing themselves and are practised by doing (farming,
herding, masonry...): `practice` names what trains it.

A recipe: out, n made, `ins` used up, `tools` needed and worn, `craft`, `hours` of work. A
`process` runs by itself in its workshop once loaded (firing, smelting, tanning, brewing): the
worker loads it and is free; the output waits there.
"""
from .items import ITEMS


CRAFTS = {
    # ---- era 0: foraging ----
    "cordage":      dict(era=0, at=None, pre={}, does="twist fibre into rope, nets and lines; weave baskets"),
    "woodworking":  dict(era=0, at=None, pre={}, does="shape wood into clubs, spears, digging sticks, drums and flutes"),
    "knapping":     dict(era=0, at=None, pre={}, does="knap flint into knives, axes, spears and sickles; bone into needles"),
    "hideworking":  dict(era=0, at=None, pre={}, does="cut and stitch hides into tunics, cloaks, hats, shoes and fur coats"),
    "cooking":      dict(era=0, at="hearth", pre={}, does="cook meat and porridge at a fire"),
    "preserving":   dict(era=0, at="hearth", pre={}, does="smoke meat and fish, dry berries, salt meat, so food keeps"),
    "herbalism":    dict(era=0, at=None, pre={}, does="make poultices from healing herbs"),
    "ornament":     dict(era=0, at=None, pre={}, does="make necklaces, bracelets and figurines"),
    # ---- era 1: the first farmers ----
    "farming":      dict(era=1, at=None, pre={}, does="sow and reap grain and flax (a skilled farmer's field yields more)",
                         practice="sowing and reaping"),
    "herding":      dict(era=1, at=None, pre={}, does="tame wild goats, sheep, cattle and pigs and keep them in pens",
                         practice="taming and tending kept animals"),
    "pottery":      dict(era=1, at="workshop", pre={}, does="fire clay in a kiln: pots, jars, bricks, figurines, moulds, tablets"),
    "weaving":      dict(era=1, at="workshop", pre={"cordage": 0.2}, does="weave flax into linen and wool into cloth on a loom"),
    "tailoring":    dict(era=1, at=None, pre={"hideworking": 0.3}, does="sew cloth and leather into fine clothes, boots, bags and armour"),
    "dairying":     dict(era=1, at="workshop", pre={"herding": 0.1}, does="make cheese that keeps from milk and salt"),
    "brewing":      dict(era=1, at="workshop", pre={"farming": 0.1}, does="brew beer from grain"),
    "baking":       dict(era=1, at="workshop", pre={"farming": 0.1}, does="grind grain to flour and bake bread in an oven"),
    "tanning":      dict(era=1, at="workshop", pre={"hideworking": 0.2}, does="tan hides into leather, which lasts"),
    "dyeing":       dict(era=1, at="workshop", pre={"weaving": 0.2}, does="make dye and dye cloth in colours"),
    "carpentry":    dict(era=1, at=None, pre={"woodworking": 0.3}, does="split planks, make shields, build houses, granaries and workshops"),
    "boatbuilding": dict(era=1, at="workshop", pre={"carpentry": 0.2}, does="hollow canoes, and later build sailboats, at a dock or workshop"),
    "bowyery":      dict(era=1, at=None, pre={"woodworking": 0.3, "cordage": 0.2}, does="make bows, which hunt alone and strike from afar"),
    # ---- era 2: bronze ----
    "charcoal_burning": dict(era=2, at="workshop", pre={"pottery": 0.2}, does="burn wood slowly in a kiln into charcoal"),
    "smelting":     dict(era=2, at="workshop", pre={"charcoal_burning": 0.2}, does="smelt copper and tin from their ores in a furnace"),
    "alloying":     dict(era=2, at="workshop", pre={"smelting": 0.3}, does="melt copper with tin into bronze"),
    "casting":      dict(era=2, at="workshop", pre={"smelting": 0.2, "pottery": 0.3}, does="cast metal in moulds: axes, knives, spears, sickles, picks, swords, hammers, ornaments"),
    "goldsmithing": dict(era=2, at="workshop", pre={"casting": 0.3}, does="work gold into rings and necklaces"),
    "wheelwrighting": dict(era=2, at="workshop", pre={"carpentry": 0.4}, does="make wheels: carts, potter's wheels, ploughs"),
    "masonry":      dict(era=2, at=None, pre={"pottery": 0.3}, does="build in brick and stone: houses, walls, temples",
                         practice="building in brick and stone"),
    "writing":      dict(era=2, at=None, pre={}, does="press clay tablets by hand and write on them: deals, laws, records, letters",
                         practice="writing"),
    # ---- era 3: iron ----
    "ironworking":  dict(era=3, at="workshop", pre={"smelting": 0.4}, does="smelt iron from red stone in a bloomery"),
    "smithing":     dict(era=3, at="workshop", pre={"ironworking": 0.2}, does="forge iron at a smithy: tools, weapons, armour, ploughs"),
    "steelmaking":  dict(era=3, at="workshop", pre={"smithing": 0.4}, does="make steel, and steel swords"),
    "lime_burning": dict(era=3, at="workshop", pre={"pottery": 0.4}, does="burn limestone into lime, and mix mortar"),
    "glassmaking":  dict(era=3, at="workshop", pre={"lime_burning": 0.2}, does="melt sand into glass: beads and vessels"),
    "minting":      dict(era=3, at="workshop", pre={"casting": 0.4}, does="strike coins of bronze"),
    "milling":      dict(era=3, at=None, pre={"carpentry": 0.5, "masonry": 0.3}, does="build water mills that grind grain unattended",
                         practice="building mills"),
    "roadbuilding": dict(era=3, at=None, pre={"masonry": 0.3}, does="build roads and bridges", practice="building roads and bridges"),
    "horsemanship": dict(era=3, at=None, pre={"herding": 0.5}, does="tame and ride horses", practice="taming and riding horses"),
    # ---- era 4: learning and institutions ----
    "literacy":     dict(era=4, at=None, pre={"writing": 0.5}, does="read and write on parchment and in books; teach at a school",
                         practice="reading and writing"),
    "parchment_making": dict(era=4, at="workshop", pre={"tanning": 0.4}, does="make parchment from hide and lime, and ink"),
    "bookmaking":   dict(era=4, at="workshop", pre={"literacy": 0.4}, does="bind books; a book on a craft lets a reader learn it without a teacher"),
    "medicine":     dict(era=4, at="workshop", pre={"herbalism": 0.5, "literacy": 0.2}, does="make remedies; heal the sick at an infirmary"),
    "astronomy":    dict(era=4, at="workshop", pre={"literacy": 0.3}, does="read the sky: a field sown by one who knows yields more",
                         practice="watching the sky"),
    "engineering":  dict(era=4, at=None, pre={"masonry": 0.6, "literacy": 0.2}, does="build halls, aqueducts and great works",
                         practice="building great works"),
    "shipbuilding": dict(era=4, at="workshop", pre={"boatbuilding": 0.5, "smithing": 0.2}, does="build sea-going ships"),
}


def R(out, n, ins, craft, hours, tools=(), process=False):
    return dict(out=out, n=n, ins=dict(ins), tools=list(tools), craft=craft, hours=hours, process=process)


RECIPES = [
    # cordage
    R("rope", 1, {"fibre": 3}, "cordage", 1),
    R("cloak", 1, {"fibre": 6, "rope": 1}, "cordage", 4),     # a cape of plaited grass and rushes: no hide needed
    R("tunic", 1, {"fibre": 5}, "cordage", 3),                # a plaited grass shirt, as above
    R("rope", 1, {"reeds": 3}, "cordage", 1),
    R("net", 1, {"rope": 3}, "cordage", 3),
    R("fishing_line", 1, {"fibre": 2, "bone": 1}, "cordage", 1),
    R("basket", 1, {"reeds": 4}, "cordage", 2),
    R("basket", 1, {"fibre": 6}, "cordage", 3),
    # woodworking
    R("club", 1, {"wood": 1}, "woodworking", 1),
    R("spear", 1, {"wood": 2}, "woodworking", 2),
    R("digging_stick", 1, {"wood": 1}, "woodworking", 1),
    R("drum", 1, {"wood": 2, "hide": 1}, "woodworking", 3),
    R("flute", 1, {"bone": 1}, "woodworking", 2),
    # knapping
    R("flint_knife", 1, {"flint": 1, "wood": 1}, "knapping", 2),
    R("stone_axe", 1, {"stone": 1, "wood": 1, "rope": 1}, "knapping", 2),
    R("flint_axe", 1, {"flint": 2, "wood": 1, "rope": 1}, "knapping", 3),
    R("flint_spear", 1, {"flint": 1, "wood": 2}, "knapping", 2),
    R("flint_sickle", 1, {"flint": 2, "wood": 1}, "knapping", 2),
    R("needle", 3, {"bone": 1}, "knapping", 2, tools=["flint_knife"]),
    # hideworking
    R("tunic", 1, {"hide": 2}, "hideworking", 3),
    R("cloak", 1, {"hide": 3}, "hideworking", 3),
    R("hat", 1, {"fibre": 4}, "hideworking", 2),
    R("fur_hat", 1, {"hide": 2}, "hideworking", 2),
    R("shoes", 1, {"hide": 1, "rope": 1}, "hideworking", 2),
    R("fur_coat", 1, {"hide": 5}, "hideworking", 5, tools=["needle"]),
    # cooking (at a fire)
    R("cooked_meat", 1, {"meat": 1}, "cooking", 1),
    R("porridge", 2, {"grain": 2, "milk": 1}, "cooking", 1),
    # preserving
    R("smoked_meat", 2, {"meat": 2}, "preserving", 3),
    R("smoked_fish", 2, {"fish": 2}, "preserving", 3),
    R("dried_berries", 4, {"berries": 4}, "preserving", 2),
    R("salted_meat", 3, {"meat": 3, "salt": 1}, "preserving", 2),
    # herbalism, ornament
    R("poultice", 1, {"herbs": 2}, "herbalism", 1),
    R("necklace", 1, {"bone": 2, "fibre": 1}, "ornament", 2),
    R("bracelet", 1, {"bone": 1, "fibre": 1}, "ornament", 1),
    R("figurine", 1, {"clay": 1}, "ornament", 2),
    # pottery (kiln)
    R("pot", 1, {"clay": 2, "wood": 1}, "pottery", 6, process=True),
    R("jar", 1, {"clay": 3, "wood": 1}, "pottery", 6, process=True),
    R("brick", 6, {"clay": 4, "wood": 2}, "pottery", 8, process=True),
    R("mould", 1, {"clay": 2, "wood": 1}, "pottery", 6, process=True),
    R("tablet", 4, {"clay": 2, "wood": 1}, "pottery", 6, process=True),
    R("tablet", 1, {"clay": 2}, "writing", 2),        # pressed by hand and dried in the sun (c53)
    # weaving (loom)
    R("linen", 1, {"flax": 3}, "weaving", 3),
    R("woolcloth", 1, {"wool": 3}, "weaving", 3),
    # tailoring
    R("linen_tunic", 1, {"linen": 2}, "tailoring", 3, tools=["needle"]),
    R("wool_tunic", 1, {"woolcloth": 2}, "tailoring", 3, tools=["needle"]),
    R("wool_cloak", 1, {"woolcloth": 3}, "tailoring", 4, tools=["needle"]),
    R("fine_tunic", 1, {"dyed_cloth": 2}, "tailoring", 4, tools=["needle"]),
    R("robe", 1, {"dyed_cloth": 3, "linen": 1}, "tailoring", 5, tools=["needle"]),
    R("boots", 1, {"leather": 2}, "tailoring", 3, tools=["needle"]),
    R("leather_bag", 1, {"leather": 2, "rope": 1}, "tailoring", 3, tools=["needle"]),
    R("leather_armour", 1, {"leather": 4}, "tailoring", 5, tools=["needle"]),
    # dairying, brewing, baking (processes)
    R("cheese", 2, {"milk": 4, "salt": 1}, "dairying", 12, process=True),
    R("beer", 4, {"grain": 3}, "brewing", 24, tools=["jar"], process=True),
    R("flour", 2, {"grain": 2}, "baking", 1, tools=["stone"]),
    R("bread", 3, {"flour": 2, "wood": 1}, "baking", 3, process=True),
    # tanning, dyeing
    R("leather", 2, {"hide": 2, "wood": 1}, "tanning", 24, process=True),
    R("dye", 1, {"berries": 4}, "dyeing", 2),
    R("dye", 1, {"herbs": 2}, "dyeing", 2),
    R("dyed_cloth", 1, {"linen": 1, "dye": 1}, "dyeing", 2),
    R("dyed_cloth", 1, {"woolcloth": 1, "dye": 1}, "dyeing", 2),
    # carpentry, bows, boats
    R("plank", 2, {"wood": 2}, "carpentry", 2, tools=["_axe"]),
    R("shield", 1, {"plank": 2, "hide": 1}, "carpentry", 3),
    R("bow", 1, {"wood": 2, "rope": 1}, "bowyery", 4),
    R("canoe", 1, {"wood": 6}, "boatbuilding", 12, tools=["_axe"]),
    R("sailboat", 1, {"plank": 12, "linen": 4, "rope": 4}, "boatbuilding", 24),
    # era 2 metal
    R("charcoal", 4, {"wood": 5}, "charcoal_burning", 10, process=True),
    R("copper", 1, {"copper_ore": 2, "charcoal": 2}, "smelting", 6, process=True),
    R("tin", 1, {"tin_ore": 2, "charcoal": 2}, "smelting", 6, process=True),
    R("bronze", 3, {"copper": 2, "tin": 1, "charcoal": 1}, "alloying", 6, process=True),
    R("bronze_axe", 1, {"bronze": 2, "charcoal": 1, "wood": 1}, "casting", 4, tools=["mould"]),
    R("bronze_knife", 1, {"bronze": 1, "charcoal": 1}, "casting", 3, tools=["mould"]),
    R("bronze_spear", 1, {"bronze": 1, "charcoal": 1, "wood": 2}, "casting", 3, tools=["mould"]),
    R("bronze_sickle", 1, {"bronze": 1, "charcoal": 1, "wood": 1}, "casting", 3, tools=["mould"]),
    R("bronze_pick", 1, {"bronze": 2, "charcoal": 1, "wood": 1}, "casting", 4, tools=["mould"]),
    R("bronze_sword", 1, {"bronze": 3, "charcoal": 1}, "casting", 5, tools=["mould"]),
    R("bronze_armour", 1, {"bronze": 4, "leather": 2, "charcoal": 2}, "casting", 8, tools=["mould"]),
    R("hammer", 1, {"bronze": 2, "wood": 1, "charcoal": 1}, "casting", 3, tools=["mould"]),
    R("copper_bracelet", 1, {"copper": 1, "charcoal": 1}, "casting", 2),
    R("bronze_torc", 1, {"bronze": 1, "charcoal": 1}, "casting", 3),
    R("gold_ring", 1, {"gold": 1, "charcoal": 1}, "goldsmithing", 3),
    R("gold_necklace", 1, {"gold": 2, "charcoal": 1}, "goldsmithing", 5),
    R("cart", 1, {"plank": 6, "bronze": 1}, "wheelwrighting", 12),
    R("potters_wheel", 1, {"plank": 2, "stone": 2}, "wheelwrighting", 6),
    R("plough", 1, {"plank": 3, "bronze": 2}, "wheelwrighting", 8),
    # era 3 iron
    R("iron", 1, {"iron_ore": 3, "charcoal": 3}, "ironworking", 10, process=True),
    R("iron_axe", 1, {"iron": 2, "charcoal": 1, "wood": 1}, "smithing", 4, tools=["hammer"]),
    R("iron_knife", 1, {"iron": 1, "charcoal": 1}, "smithing", 3, tools=["hammer"]),
    R("iron_spear", 1, {"iron": 1, "charcoal": 1, "wood": 2}, "smithing", 3, tools=["hammer"]),
    R("iron_sickle", 1, {"iron": 1, "charcoal": 1, "wood": 1}, "smithing", 3, tools=["hammer"]),
    R("iron_pick", 1, {"iron": 2, "charcoal": 1, "wood": 1}, "smithing", 4, tools=["hammer"]),
    R("iron_sword", 1, {"iron": 3, "charcoal": 2}, "smithing", 5, tools=["hammer"]),
    R("iron_armour", 1, {"iron": 5, "leather": 2, "charcoal": 2}, "smithing", 10, tools=["hammer"]),
    R("iron_plough", 1, {"iron": 3, "plank": 3, "charcoal": 1}, "smithing", 8, tools=["hammer"]),
    R("steel", 1, {"iron": 2, "charcoal": 2}, "steelmaking", 8, tools=["hammer"]),
    R("steel_sword", 1, {"steel": 2, "charcoal": 1}, "steelmaking", 8, tools=["hammer"]),
    R("lime", 2, {"limestone": 2, "wood": 2}, "lime_burning", 10, process=True),
    R("mortar", 3, {"lime": 1, "sand": 2}, "lime_burning", 1),
    R("glass", 1, {"sand": 3, "lime": 1, "charcoal": 2}, "glassmaking", 10, process=True),
    R("glass_beads", 1, {"glass": 1}, "glassmaking", 2),
    R("glassware", 1, {"glass": 2, "charcoal": 1}, "glassmaking", 4),
    R("coin", 6, {"bronze": 1, "charcoal": 1}, "minting", 2, tools=["hammer"]),
    # era 4 learning
    R("parchment", 4, {"hide": 1, "lime": 1}, "parchment_making", 24, process=True),
    R("ink", 2, {"charcoal": 1, "herbs": 1}, "parchment_making", 1),
    R("book", 1, {"parchment": 8, "ink": 1, "leather": 1}, "bookmaking", 16),
    R("remedy", 2, {"herbs": 3, "beer": 1}, "medicine", 3),
    R("ship", 1, {"plank": 30, "linen": 10, "rope": 10, "iron": 4}, "shipbuilding", 60),
]

# A tool named "_axe" means any axe (the best one held is used).
ANY = {"_axe": ["iron_axe", "bronze_axe", "flint_axe", "stone_axe"]}


def recipes_for(craft):
    return [r for r in RECIPES if r["craft"] == craft]


def recipes_making(item):
    return [r for r in RECIPES if r["out"] == item]


def tool_options(t):
    return ANY.get(t, [t])


def use_text(item):
    """What a made thing is good for, in a few words: (wood x2), (warmth 2), (food 4, keeps)."""
    v = ITEMS.get(item, {})
    bits = []
    for u, f in (v.get("tool") or {}).items():
        if u.startswith("speed:"):
            bits.append("faster " + u[6:].replace("_", " "))
        elif f > 1:
            bits.append(f"{u} x{f:g}")
    if v.get("wear"):
        slot, warm = v["wear"][0], v["wear"][1]
        bits.append(f"warmth {warm}" if warm else "worn")
    if v.get("food"):
        bits.append(f"food {v['food']}" + (", keeps" if v.get("spoil", 1) < 1 / 500 else ""))
    if v.get("weapon") and not any(f > 1 for f in (v.get("tool") or {}).values()):
        bits.append(f"weapon {v['weapon']}")
    if v.get("carry"):
        bits.append(f"carry +{v['carry']}")
    if v.get("heal"):
        bits.append("heals")
    return f" ({', '.join(bits)})" if bits else ""


def recipe_text(r):
    ins = " + ".join(f"{k.replace('_', ' ')} {n}" for k, n in r["ins"].items())
    tools = [("an axe" if t == "_axe" else "a " + t.replace("_", " ")) for t in r["tools"]]
    out = r["out"].replace("_", " ") + (f" x{r['n']}" if r["n"] > 1 else "") + use_text(r["out"])
    return f"{out} = {ins}" + (f" with {' and '.join(tools)}" if tools else "") + f" ({r['hours']}h{', unattended' if r['process'] else ''})"
