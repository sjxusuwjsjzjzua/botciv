"""Towns, as data (docs/towns_spec.md §3.5, §3.6, §5.10, Appendix A): each building kind's footprint, the zone of a
settlement it goes in, and its nuisance; each people's town form; the well. Read only in a towns world.

  size      [w, d] cells of 4 m before facing ("people": by the builder's people, see TOWNS[...]["dwelling"])
  zone      dwelling | yard | commons | edge | water | burial | field | land (where in a settlement it goes)
  nuisance  0 none, 1 smoke or noise, 2 smoke and stink (kept apart from homes, downwind)
"""

CELL = 4            # metres a cell

KINDS = {
    "fire": ((1, 1), "yard", 1), "shelter": ("people", "dwelling", 0), "store": ((1, 1), "yard", 0),
    "drying_rack": ((1, 0.5), "yard", 0), "grave": ((0.5, 1), "burial", 0), "cairn": ((1, 1), "burial", 0),
    "farm": ((25, 50), "field", 0), "pen": ((3, 3), "yard", 1), "house": ("people", "dwelling", 0),
    "granary": ((2, 2.5), "yard", 0), "kiln": ((1, 1.25), "edge", 2), "loom": ((1.5, 2), "yard", 0),
    "oven": ((1, 1), "yard", 1), "tannery": ((2.5, 3), "edge", 2), "brewhouse": ((2.5, 3), "yard", 1),
    "workshop": ((3, 4), "yard", 1), "palisade": ((1, 4), "edge", 0), "shrine": ((1, 1), "commons", 0),
    "dock": ((2, 5), "water", 0), "furnace": ((1.5, 1.5), "edge", 2), "hall": ((6, 10), "commons", 0),
    "brick_house": ((3, 5), "dwelling", 0), "stone_wall": ((1, 4), "edge", 0), "gatehouse": ((3, 3), "edge", 0),
    "temple": ((6, 9), "commons", 0), "market": ((8, 8), "commons", 1), "scribe_house": ((3, 4), "commons", 0),
    "bloomery": ((1.5, 2), "edge", 2), "smithy": ((3, 4), "edge", 1), "lime_kiln": ((2, 2), "edge", 2),
    "glassworks": ((3, 4), "edge", 2), "mill": ((3, 4), "water", 1), "road": (None, "land", 0),
    "bridge": (None, "land", 0), "stone_house": ((4, 6), "dwelling", 0), "tower": ((2.5, 2.5), "edge", 0),
    "stables": ((4, 7), "yard", 1), "school": ((5, 7), "commons", 0), "library": ((5, 7), "commons", 0),
    "scriptorium": ((4, 5), "commons", 0), "infirmary": ((5, 7), "commons", 0), "observatory": ((3, 3), "land", 0),
    "shipyard": ((6, 12), "water", 1), "aqueduct": (None, "land", 0), "well": ((0.75, 0.75), "commons", 0),
}
# Sizes follow the step 0 village (docs/towns_pics/step0.md: a long house 7 x 15 m, a lane 5 m, a store 3 m), the
# look the owner accepted; Appendix A's first numbers (12 x 32 m long houses, 12 m lanes) were twice too large.
DEFAULT = ((4, 5), "yard", 1)        # a kind not listed: a workshop's size, in the yard

# the well (§5.10): where people meet by day, as the green is in the evening. Joins the building kinds in a towns
# world only (the engine's WP2), so worlds without towns are as they were.
WELL = dict(era=0, cost={"stone": 4}, hours=4, hp=60, sym="o", roles={"gathering": {}})

# each people's town (§3.6): its form, its plot (w x d cells), its lane's width (cells), how plots are bounded,
# its dwellings' shapes and sizes (cells: shelter, house)
TOWNS = {
    "river": dict(form="street", plot=(5, 12), lane=1.25, bounds="fence", shape="long_house",
                  dwelling={"shelter": (1.75, 3.5), "house": (2, 4)}),
    "shore": dict(form="waterfront", plot=(5, 10), lane=1.25, bounds="none", shape="long_house",
                  dwelling={"shelter": (1.75, 3), "house": (2, 3.5)}),
    "hill": dict(form="cluster", plot=(6, 6), lane=1, bounds="bank", shape="round_house",
                 dwelling={"shelter": (2.5, 2.5), "house": (3, 3)}),
    "riders": dict(form="ring", plot=(5, 5), lane=1, bounds="none", shape="tent",
                   dwelling={"shelter": (2, 2), "house": (2.5, 2.5)}),
    "forest": dict(form="scatter", plot=(7, 7), lane=0.75, bounds="none", shape="conical_hut",
                   dwelling={"shelter": (1.75, 1.75), "house": (2.5, 3)}),
}
TOWN_DEFAULT = dict(form="street", plot=(5, 10), lane=1.25, bounds="fence", shape="square",
                    dwelling={"shelter": (2, 3), "house": (2.5, 3.5)})


def town_of(people):
    return TOWNS.get(people, TOWN_DEFAULT)


def footprint(kind, people=""):
    """(w, d) in metres of a kind built by one of a people; None for overlays and what spans a tile."""
    size = KINDS.get(kind, DEFAULT)[0]
    if size == "people":
        size = town_of(people)["dwelling"].get(kind, (4, 5))
    return None if size is None else (size[0] * CELL, size[1] * CELL)


def zone(kind):
    return KINDS.get(kind, DEFAULT)[1]


def nuisance(kind):
    return KINDS.get(kind, DEFAULT)[2]
