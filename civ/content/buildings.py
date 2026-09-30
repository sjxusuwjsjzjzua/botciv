"""Buildings, as data. The engine reads roles, never kinds.

  cost      what building it uses up (carried, or from a store of one's own beside one)
  hours     work to finish it (more hands finish it sooner)
  hp        how much it takes to break
  era       when it first can be built;  craft: the builder must be at least a beginner at it
  roles     shelter: warmth (a night inside is warmth this much; 3 keeps any winter off)
            store: capacity (load), keep: food inside spoils this much as often
            workshop: crafts worked here
            hearth: burns fuel (it must be fed), warms those beside it, and is a workshop for cooking
            farm: grows grain, flax or hay on rich soil (on: terrain it must stand on)
            pen: how many kept animals it holds
            wall: blocks the way; gate: those allowed pass
            market: posted trades of every store within 2 steps are open to all here
            school: one teacher teaches up to this many at once
            library: books kept here can be read by anyone allowed in
            mill: grinds grain to flour with no one working (must stand beside water)
            road: walking on it is twice as fast;  bridge: stands on water, and can be crossed
            monument: carries a name and carved words;  grave: someone lies here
            gathering: a place people meet (a temple, a hall); what it means is theirs
            dock: a boat can be kept and launched here
"""

BUILDINGS = {
    # ---- era 0 ----
    "fire":      dict(era=0, cost={"wood": 2}, hours=1, hp=5, sym="f",
                      roles={"hearth": {"fuel": 24, "warmth": 2}, "workshop": ["cooking", "preserving"]}),
    "shelter":   dict(era=0, cost={"wood": 5, "fibre": 4}, hours=6, hp=20, sym="H",
                      roles={"shelter": {"warmth": 2, "beds": 4}}),
    "store":     dict(era=0, cost={"wood": 4}, hours=4, hp=20, sym="S",
                      roles={"store": {"capacity": 60, "keep": 0.4}}),
    "drying_rack": dict(era=0, cost={"wood": 3, "rope": 1}, hours=2, hp=10, sym="r",
                      roles={"workshop": ["preserving"]}),
    "grave":     dict(era=0, cost={}, hours=3, hp=40, sym="=", roles={"grave": {}}),
    "cairn":     dict(era=0, cost={"stone": 4}, hours=4, hp=60, sym="^", roles={"monument": {}}),
    # ---- era 1 ----
    "farm":      dict(era=1, cost={"wood": 1}, hours=2, hp=10, sym="F", craft="farming",
                      roles={"farm": {"on": {",": 1.0, ".": 0.6}}}),
    "pen":       dict(era=1, cost={"wood": 6, "rope": 2}, hours=4, hp=25, sym="P", craft="herding",
                      roles={"pen": {"capacity": 8}}),
    "house":     dict(era=1, cost={"wood": 8, "clay": 6, "reeds": 4}, hours=10, hp=50, sym="h", craft="carpentry",
                      roles={"shelter": {"warmth": 3, "beds": 6}, "store": {"capacity": 50, "keep": 0.35}}),
    "granary":   dict(era=1, cost={"wood": 6, "clay": 8}, hours=8, hp=40, sym="g", craft="carpentry",
                      roles={"store": {"capacity": 200, "keep": 0.15}}),
    "kiln":      dict(era=1, cost={"clay": 6, "stone": 3}, hours=5, hp=35, sym="K", craft="pottery",
                      roles={"workshop": ["pottery", "charcoal_burning"]}),
    "loom":      dict(era=1, cost={"wood": 3, "rope": 2}, hours=3, hp=15, sym="L", craft="weaving",
                      roles={"workshop": ["weaving"]}),
    "oven":      dict(era=1, cost={"clay": 5, "stone": 2}, hours=4, hp=30, sym="O", craft="baking",
                      roles={"workshop": ["baking"]}),
    "tannery":   dict(era=1, cost={"wood": 4, "clay": 4}, hours=4, hp=20, sym="t", craft="tanning",
                      roles={"workshop": ["tanning", "dyeing"]}),
    "brewhouse": dict(era=1, cost={"wood": 5, "clay": 4}, hours=4, hp=20, sym="b", craft="brewing",
                      roles={"workshop": ["brewing", "dairying"]}),
    "workshop":  dict(era=1, cost={"wood": 6, "plank": 2}, hours=5, hp=25, sym="W", craft="carpentry",
                      roles={"workshop": ["carpentry", "boatbuilding", "bowyery", "wheelwrighting"]}),
    "palisade":  dict(era=1, cost={"wood": 4}, hours=3, hp=40, sym="#", roles={"wall": {}}),
    "shrine":    dict(era=1, cost={"stone": 4, "wood": 2}, hours=5, hp=40, sym="&", roles={"gathering": {}, "monument": {}}),
    "dock":      dict(era=1, cost={"wood": 6, "plank": 4}, hours=6, hp=30, sym="d", craft="boatbuilding",
                      roles={"dock": {}, "workshop": ["boatbuilding"]}),
    # ---- era 2 ----
    "furnace":   dict(era=2, cost={"brick": 8, "stone": 4}, hours=8, hp=50, sym="U", craft="smelting",
                      roles={"workshop": ["smelting", "casting", "alloying", "goldsmithing"]}),
    "brick_house": dict(era=2, cost={"brick": 20, "plank": 6, "reeds": 4}, hours=16, hp=90, sym="M", craft="masonry",
                      roles={"shelter": {"warmth": 3, "beds": 8}, "store": {"capacity": 90, "keep": 0.3}}),
    "stone_wall": dict(era=2, cost={"stone": 6}, hours=6, hp=120, sym="#", craft="masonry", roles={"wall": {}}),
    "gatehouse": dict(era=2, cost={"stone": 8, "plank": 4}, hours=8, hp=120, sym="n", craft="masonry", roles={"wall": {"gate": True}}),
    "temple":    dict(era=2, cost={"stone": 20, "brick": 10, "plank": 6}, hours=30, hp=200, sym="T", craft="masonry",
                      roles={"gathering": {}, "monument": {}, "store": {"capacity": 60, "keep": 0.3}}),
    "market":    dict(era=2, cost={"plank": 8, "stone": 4}, hours=8, hp=40, sym="$", craft="carpentry", roles={"market": {}}),
    "scribe_house": dict(era=2, cost={"brick": 10, "plank": 4}, hours=8, hp=50, sym="w", craft="writing",
                      roles={"workshop": ["writing"], "store": {"capacity": 30, "keep": 0.5}}),
    # ---- era 3 ----
    "bloomery":  dict(era=3, cost={"brick": 10, "stone": 6, "leather": 2}, hours=10, hp=60, sym="E", craft="ironworking",
                      roles={"workshop": ["ironworking"]}),
    "smithy":    dict(era=3, cost={"stone": 8, "plank": 4, "iron": 4, "leather": 2}, hours=10, hp=60, sym="Y", craft="smithing",
                      roles={"workshop": ["smithing", "steelmaking", "minting"]}),
    "lime_kiln": dict(era=3, cost={"stone": 8, "brick": 6}, hours=8, hp=60, sym="k", craft="lime_burning",
                      roles={"workshop": ["lime_burning"]}),
    "glassworks": dict(era=3, cost={"brick": 12, "stone": 4}, hours=10, hp=50, sym="v", craft="glassmaking",
                      roles={"workshop": ["glassmaking"]}),
    "mill":      dict(era=3, cost={"stone": 10, "plank": 10, "iron": 2}, hours=16, hp=80, sym="Q", craft="milling", near="water",
                      roles={"mill": {"per_day": 40}}),
    "road":      dict(era=3, cost={"stone": 2}, hours=2, hp=200, sym="_", craft="roadbuilding", overlay=True, roles={"road": {}}),
    "bridge":    dict(era=3, cost={"stone": 10, "plank": 8, "mortar": 4}, hours=16, hp=200, sym="=", craft="roadbuilding", on="water",
                      roles={"bridge": {}, "road": {}}),
    "stone_house": dict(era=3, cost={"stone": 24, "mortar": 8, "plank": 8}, hours=20, hp=150, sym="X", craft="masonry",
                      roles={"shelter": {"warmth": 3, "beds": 10}, "store": {"capacity": 120, "keep": 0.25}}),
    "tower":     dict(era=3, cost={"stone": 20, "mortar": 8, "plank": 6}, hours=20, hp=250, sym="I", craft="masonry",
                      roles={"wall": {}, "store": {"capacity": 40, "keep": 0.4}, "lookout": {"sight": 4}}),
    "stables":   dict(era=3, cost={"plank": 10, "stone": 4}, hours=8, hp=40, sym="R", craft="horsemanship", roles={"pen": {"capacity": 12}}),
    # ---- era 4 ----
    "school":    dict(era=4, cost={"stone": 16, "mortar": 6, "plank": 10}, hours=20, hp=100, sym="Z", craft="literacy",
                      roles={"school": {"learners": 6}, "gathering": {}}),
    "library":   dict(era=4, cost={"stone": 20, "mortar": 8, "plank": 12}, hours=24, hp=120, sym="J", craft="literacy",
                      roles={"library": {}, "store": {"capacity": 60, "keep": 0.5}}),
    "scriptorium": dict(era=4, cost={"stone": 12, "mortar": 4, "plank": 8}, hours=14, hp=80, sym="V", craft="bookmaking",
                      roles={"workshop": ["bookmaking", "literacy", "parchment_making"]}),
    "infirmary": dict(era=4, cost={"stone": 14, "mortar": 6, "plank": 8, "linen": 6}, hours=16, hp=80, sym="+", craft="medicine",
                      roles={"shelter": {"warmth": 3, "beds": 8, "heals": 2}, "workshop": ["medicine"]}),
    "observatory": dict(era=4, cost={"stone": 20, "mortar": 8, "glass": 4}, hours=20, hp=100, sym="o", craft="astronomy",
                      roles={"workshop": ["astronomy"], "lookout": {"sight": 6}}),
    "shipyard":  dict(era=4, cost={"plank": 20, "stone": 8, "iron": 6}, hours=24, hp=100, sym="y", craft="shipbuilding",
                      roles={"dock": {}, "workshop": ["shipbuilding", "boatbuilding"]}),
    "aqueduct":  dict(era=4, cost={"stone": 12, "mortar": 8}, hours=12, hp=200, sym="a", craft="engineering", overlay=True,
                      roles={"irrigates": {"radius": 3}}),
    "hall":      dict(era=4, cost={"stone": 30, "mortar": 12, "plank": 16}, hours=36, hp=250, sym="N", craft="engineering",
                      roles={"gathering": {}, "store": {"capacity": 150, "keep": 0.3}, "monument": {}, "treasury": {}}),
}


def roles(kind):
    return BUILDINGS[kind]["roles"]


def has(kind, role):
    return role in BUILDINGS.get(kind, {}).get("roles", {})


def kinds_with(role):
    return [k for k, v in BUILDINGS.items() if role in v["roles"]]
