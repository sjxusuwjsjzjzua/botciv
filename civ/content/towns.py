"""Towns, as data (docs/towns_spec.md §3.5, §3.6, §5.10, Appendix A): each building kind's footprint, the zone of a
settlement it goes in, and its nuisance; each people's town form; the well. Read only in a towns world.

  size      [w, d] cells of 4 m before facing ("people": by the builder's people, see TOWNS[...]["dwelling"])
  zone      dwelling | yard | commons | edge | water | burial | field | land (where in a settlement it goes)
  nuisance  0 none, 1 smoke or noise, 2 smoke and stink (kept apart from homes, downwind)
"""

CELL = 4            # metres a cell

KINDS = {
    "fire": ((2, 2), "yard", 1), "shelter": ("people", "dwelling", 0), "store": ((2, 3), "yard", 0),
    "drying_rack": ((1, 2), "yard", 0), "grave": ((1, 2), "burial", 0), "cairn": ((2, 2), "burial", 0),
    "farm": ((25, 50), "field", 0), "pen": ((4, 4), "yard", 1), "house": ("people", "dwelling", 0),
    "granary": ((3, 4), "yard", 0), "kiln": ((2, 3), "edge", 2), "loom": ((2, 3), "yard", 0),
    "oven": ((2, 2), "yard", 1), "tannery": ((3, 4), "edge", 2), "brewhouse": ((3, 4), "yard", 1),
    "workshop": ((4, 5), "yard", 1), "palisade": ((1, 4), "edge", 0), "shrine": ((3, 3), "commons", 0),
    "dock": ((3, 6), "water", 0), "furnace": ((3, 3), "edge", 2), "hall": ((10, 14), "commons", 0),
    "brick_house": ((5, 7), "dwelling", 0), "stone_wall": ((1, 4), "edge", 0), "gatehouse": ((3, 3), "edge", 0),
    "temple": ((8, 12), "commons", 0), "market": ((10, 10), "commons", 1), "scribe_house": ((4, 5), "commons", 0),
    "bloomery": ((3, 4), "edge", 2), "smithy": ((4, 5), "edge", 1), "lime_kiln": ((3, 3), "edge", 2),
    "glassworks": ((4, 5), "edge", 2), "mill": ((4, 5), "water", 1), "road": (None, "land", 0),
    "bridge": (None, "land", 0), "stone_house": ((6, 8), "dwelling", 0), "tower": ((3, 3), "edge", 0),
    "stables": ((5, 8), "yard", 1), "school": ((6, 8), "commons", 0), "library": ((6, 8), "commons", 0),
    "scriptorium": ((5, 6), "commons", 0), "infirmary": ((6, 8), "commons", 0), "observatory": ((4, 4), "land", 0),
    "shipyard": ((8, 14), "water", 1), "aqueduct": (None, "land", 0), "well": ((2, 2), "commons", 0),
}
DEFAULT = ((4, 5), "yard", 1)        # a kind not listed: a workshop's size, in the yard

# the well (§5.10): where people meet by day, as the green is in the evening. Joins the building kinds in a towns
# world only (the engine's WP2), so worlds without towns are as they were.
WELL = dict(era=0, cost={"stone": 4}, hours=4, hp=60, sym="o", roles={"gathering": {}})

# each people's town (§3.6): its form, its plot (w x d cells), its lane's width (cells), how plots are bounded,
# its dwellings' shapes and sizes (cells: shelter, house)
TOWNS = {
    "river": dict(form="street", plot=(8, 14), lane=3, bounds="fence", shape="long_house",
                  dwelling={"shelter": (3, 8), "house": (4, 10)}),
    "shore": dict(form="waterfront", plot=(7, 12), lane=3, bounds="none", shape="long_house",
                  dwelling={"shelter": (3, 7), "house": (4, 8)}),
    "hill": dict(form="cluster", plot=(8, 8), lane=2, bounds="bank", shape="round_house",
                 dwelling={"shelter": (4, 4), "house": (5, 5)}),
    "riders": dict(form="ring", plot=(7, 7), lane=2, bounds="none", shape="tent",
                   dwelling={"shelter": (3, 3), "house": (4, 4)}),
    "forest": dict(form="scatter", plot=(9, 9), lane=1, bounds="none", shape="conical_hut",
                   dwelling={"shelter": (3, 3), "house": (4, 5)}),
}
TOWN_DEFAULT = dict(form="street", plot=(8, 12), lane=3, bounds="fence", shape="square",
                    dwelling={"shelter": (3, 4), "house": (4, 5)})


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
