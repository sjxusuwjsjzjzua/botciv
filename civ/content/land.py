"""The land: terrain, what it yields, what lies in it, and what lives on it.

Terrain is one character a tile. `cost` is hours to step onto it (0: impassable on foot).
`yields` are gathered from the tile itself or one beside it, without limit (a forest gives wood
forever); `season` limits some. Deposits are finite places placed by the generator on certain
terrain (`on`), some growing back each spring (`renew`)."""

TERRAIN = {
    ".": dict(name="grass", cost=1, yields={"fibre": None, "hay": "summer autumn"}, color="#8fae6a"),
    ",": dict(name="rich soil", cost=1, yields={"fibre": None, "hay": "summer autumn"}, farm=True, color="#7f9c52"),
    "T": dict(name="forest", cost=1, yields={"wood": None}, color="#3f6b3a"),
    "h": dict(name="hills", cost=2, yields={"stone": None}, color="#a39a78"),
    "^": dict(name="mountain", cost=0, yields={"stone": None}, color="#8a8680"),
    "~": dict(name="water", cost=0, water=True, color="#4f7fb0"),
    "m": dict(name="marsh", cost=2, yields={"reeds": None, "clay": None}, color="#6f8f74"),
    "s": dict(name="sand", cost=1, yields={"sand": None}, color="#d9c89a"),
}
PASSABLE = {k for k, v in TERRAIN.items() if v["cost"]}

# Seeds come with fibre on grass in summer and autumn (the first farmers' way to grain).
SEED_CHANCE = 0.2

# kind: where it lies (terrain chars; "bank" = passable beside water), how many per 100 such
# tiles (at least `least`), how much each holds, whether it grows back each spring, whether they
# lie together (`cluster`) and far from another kind (`far`), the map mark, a name people use.
DEPOSITS = {
    "clay":       dict(on="bank", per=16, least=8, size=150, sym=";", name="clay bank"),
    "flint":      dict(on="h^", per=6, least=4, size=40, sym="'", name="flint"),
    "flax":       dict(on=",", per=10, least=4, size=10, renew=True, sym="|", name="wild flax"),
    "herbs":      dict(on="T", per=4, least=4, size=6, renew=True, sym='"', name="healing herbs"),
    "berries":    dict(on=".T", per=6, least=10, size=12, renew="bush", sym="*", name="berry bush"),
    "wild_grain": dict(on=".,", per=4, least=8, size=16, renew=True, gives="grain", sym=":", name="wild grain"),
    "nuts":       dict(on="T", per=2, least=4, size=12, renew="autumn", sym="%", name="nut trees"),
    "honey":      dict(on="T", per=0.8, least=2, size=6, renew=True, sym="`", name="wild bees"),
    "salt":       dict(on="sm", per=3, least=2, size=80, sym="=", name="salt pan"),
    "copper_ore": dict(on="h", per=2.5, least=3, size=80, cluster=True, sym="$", name="green stone (copper ore)"),
    "tin_ore":    dict(on="h", per=0.7, least=1, size=40, cluster=True, far="copper_ore", sym="0", name="black stone (tin ore)"),
    "iron_ore":   dict(on="h", per=5, least=4, size=100, sym="&", name="red stone (iron ore)"),
    "bog_iron":   dict(on="m", per=5, least=2, size=30, gives="iron_ore", sym="&", name="bog iron"),
    "limestone":  dict(on="h^", per=4, least=3, size=120, sym="!", name="limestone"),
    "gold":       dict(on="h", per=0.5, least=1, size=12, near_water=True, sym="o", name="gold in the stream gravel"),
}

# Wild animals. Herds wander their terrain; a hunt needs hunters beside the herd. `tame` names the
# kept animal a herder can lead home from it, and the skill needed.
WILD = {
    "deer":      dict(on=".T,", herd=(5, 9), meat=10, hide=2, bone=2, chance=(0.0, 0.05, 0.5, 0.75, 0.9), sym="d", name="deer"),
    "boar":      dict(on="T", herd=(2, 5), meat=8, hide=1, bone=1, chance=(0.05, 0.25, 0.6, 0.8, 0.9), fierce=2, tame=("pig", 0.3), sym="b", name="wild boar"),
    "aurochs":   dict(on=".,", herd=(4, 8), meat=20, hide=3, bone=3, chance=(0.0, 0.0, 0.3, 0.6, 0.8), fierce=3, tame=("cattle", 0.5), sym="a", name="aurochs"),
    "wild_goat": dict(on="h", herd=(4, 8), meat=6, hide=1, bone=1, chance=(0.05, 0.2, 0.55, 0.8, 0.9), tame=("goat", 0.2), sym="g", name="wild goats"),
    "wild_sheep": dict(on="h.", herd=(5, 10), meat=6, hide=1, bone=1, chance=(0.05, 0.2, 0.55, 0.8, 0.9), tame=("sheep", 0.25), sym="w", name="wild sheep"),
    "wild_horse": dict(on=".", herd=(5, 10), meat=12, hide=2, bone=2, chance=(0.0, 0.05, 0.4, 0.7, 0.85), tame=("horse", 0.5), sym="x", name="wild horses"),
    "wild_ass":  dict(on="h", herd=(3, 7), meat=8, hide=1, bone=1, chance=(0.0, 0.05, 0.45, 0.7, 0.85), tame=("donkey", 0.3), sym="e", name="wild asses", extra=True),   # in the hills, few
}
PREDATORS = {"wolves": dict(on="T", pack=(3, 5), hp=5, bite=2, sym="W")}

# Kept animals, in a pen. Each day (not in winter, when they must be fed hay or grain) they graze
# if their pen stands on grass or rich soil; unfed they sicken and die. Two of a kind in a fed pen
# breed each spring. `gives` is collected from the pen each day (milk) or each spring (wool);
# slaughtering one gives `meat` (and 1 hide, 1 bone). Cattle and horses can pull a plough or cart.
TAME = {
    "goat":   dict(gives={"milk": 2}, meat=6, eats=1, breed=1, era=1),
    "sheep":  dict(gives={"milk": 1}, spring={"wool": 3}, meat=6, eats=1, breed=1, era=1),
    "cattle": dict(gives={"milk": 4}, meat=18, eats=2, breed=1, draught=True, era=1),
    "pig":    dict(gives={}, meat=10, eats=1, breed=3, era=1),
    "horse":  dict(gives={}, meat=12, eats=2, breed=1, draught=True, mount=2, era=3, pack=50),
    "donkey": dict(gives={}, meat=8, eats=1, breed=1, era=1, pack=40),    # led, it carries (c86)
}

SEASONS = ["spring", "summer", "autumn", "winter"]
