"""Peoples (grand world, docs/grand.md section 6B), as data: who lives where, how, and by what customs.

Each people has a tongue (the sounds its names are made of; those who do not know it hear only that it is
spoken), a homeland (the kind of region it begins in), a lifeway (the crafts and skills its people grow up
with, the beasts they keep, what they carry, the era their land supports), leanings (the traits its children
are born near), customs (how a leader is chosen, how the dead's things pass, whether a guest is sacred, whether
a raid on strangers is honour or theft), gods, and colours for the viewer.

These are initial conditions, never outcomes: what the peoples make of their land and of one another is theirs.
A world draws as many peoples as it has room for, in this order of preference by the regions it has."""

PEOPLES = {
    "river": dict(
        folk="river folk", homeland="valley",
        tongue=dict(onsets=["l", "m", "n", "s", "v", "r", "th", "d", "y", "el", "an"], vowels=["a", "e", "i", "ia", "ae", "o", "ei"],
                    codas=["", "", "n", "l", "s", "th", "ra", "na"], word="the river tongue"),
        lifeway=dict(era=2, crafts={"farming": (0.4, 0.7), "pottery": (0.3, 0.6), "weaving": (0.3, 0.6), "carpentry": (0.2, 0.5),
                                    "smelting": (0.0, 0.35), "casting": (0.0, 0.3), "writing": (0.0, 0.3), "baking": (0.2, 0.5)},
                     beasts={"cattle": 2, "sheep": 2}, kit={"grain": 8, "flint_sickle": 1}, builds=["house", "store", "farm"]),
        leanings=dict(industry=0.65, sociability=0.6, boldness=0.35, generosity=0.5, curiosity=0.6, ambition=0.5),
        customs=dict(lead="blood", inherit="eldest", guest=True, raid_honour=False),
        gods=["the River Mother", "the Sower"], festival="spring",
        colours=["#c9a227", "#e8dcc0"]),
    "hill": dict(
        folk="hill clans", homeland="upland",
        tongue=dict(onsets=["g", "k", "br", "dr", "gr", "kh", "t", "b", "m", "c"], vowels=["a", "o", "u", "ai", "ao"],
                    codas=["ch", "rn", "k", "g", "d", "rr", "", "n"], word="the hill tongue"),
        lifeway=dict(era=1, crafts={"herding": (0.4, 0.7), "hideworking": (0.3, 0.6), "knapping": (0.3, 0.6), "dairying": (0.2, 0.5),
                                    "cordage": (0.3, 0.5)},
                     skills={"fight": (0.3, 0.6), "hunt": (0.3, 0.6)},
                     beasts={"sheep": 3, "goat": 2}, kit={"spear": 1, "cheese": 4}, builds=["shelter", "pen"]),
        leanings=dict(industry=0.45, sociability=0.55, boldness=0.75, generosity=0.55, curiosity=0.35, ambition=0.6),
        customs=dict(lead="boldest", inherit="shared", guest=True, raid_honour=True),
        gods=["the Old One of the Crag", "Thunder"], festival="autumn",
        colours=["#7a4b2a", "#5d7f3a"]),
    "riders": dict(
        folk="horse riders", homeland="steppe",
        tongue=dict(onsets=["t", "k", "q", "s", "b", "ch", "z", "y", "ul", "ar"], vowels=["a", "u", "i", "e", "ai"],
                    codas=["n", "r", "k", "t", "z", "", "an", "ai"], word="the horse tongue"),
        lifeway=dict(era=1, crafts={"herding": (0.4, 0.7), "horsemanship": (0.4, 0.7), "hideworking": (0.3, 0.6), "bowyery": (0.2, 0.5),
                                    "cordage": (0.3, 0.5)},
                     skills={"fight": (0.3, 0.6), "hunt": (0.3, 0.6)},
                     beasts={"horse": 3, "sheep": 2}, kit={"bow": 1}, builds=["shelter", "pen"]),
        leanings=dict(industry=0.4, sociability=0.5, boldness=0.7, generosity=0.5, curiosity=0.45, ambition=0.65),
        customs=dict(lead="boldest", inherit="eldest", guest=True, raid_honour=True),
        gods=["the Sky Father", "the Mare"], festival="summer",
        colours=["#b5552d", "#d9b44a"]),
    "forest": dict(
        folk="forest folk", homeland="forest",
        tongue=dict(onsets=["w", "h", "f", "l", "sh", "n", "t", "wy", "a", "i"], vowels=["i", "e", "o", "ee", "iu", "a"],
                    codas=["", "", "w", "n", "l", "sh", "th"], word="the forest tongue"),
        lifeway=dict(era=0, crafts={"herbalism": (0.4, 0.7), "woodworking": (0.4, 0.7), "cordage": (0.3, 0.6), "preserving": (0.3, 0.6),
                                    "knapping": (0.3, 0.5)},
                     skills={"hunt": (0.4, 0.7), "gather": (0.4, 0.7)},
                     beasts={}, kit={"poultice": 1, "dried_berries": 6}, builds=["shelter"]),
        leanings=dict(industry=0.5, sociability=0.45, boldness=0.35, generosity=0.65, curiosity=0.45, ambition=0.25),
        customs=dict(lead="vote", inherit="shared", guest=True, raid_honour=False),
        gods=["the Green Man", "the Deer Mother"], festival="spring",
        colours=["#2f5d3a", "#9b7b4f"]),
    "shore": dict(
        folk="shore folk", homeland="coast",
        tongue=dict(onsets=["s", "p", "m", "v", "h", "n", "sk", "k", "o"], vowels=["a", "e", "o", "u", "oa", "ea"],
                    codas=["", "n", "s", "k", "rd", "lf", "m"], word="the sea tongue"),
        lifeway=dict(era=1, crafts={"boatbuilding": (0.3, 0.6), "cordage": (0.4, 0.7), "preserving": (0.3, 0.6), "weaving": (0.2, 0.5),
                                    "woodworking": (0.3, 0.5)},
                     skills={"fish": (0.4, 0.7)},
                     beasts={"goat": 2}, kit={"net": 1, "smoked_fish": 6, "salt": 2}, builds=["house", "store"]),
        leanings=dict(industry=0.55, sociability=0.65, boldness=0.55, generosity=0.5, curiosity=0.6, ambition=0.55),
        customs=dict(lead="vote", inherit="eldest", guest=True, raid_honour=False),
        gods=["the Grey Lady of the Waves", "the Net Weaver"], festival="summer",
        colours=["#2d6f73", "#c9c3b0"]),
    "miners": dict(
        folk="mountain miners", homeland="upland",
        tongue=dict(onsets=["d", "b", "g", "kr", "st", "h", "r", "dw", "o"], vowels=["u", "o", "a", "ou", "e"],
                    codas=["rk", "m", "n", "st", "nd", "r", ""], word="the stone tongue"),
        lifeway=dict(era=2, crafts={"knapping": (0.3, 0.6), "charcoal_burning": (0.3, 0.6), "smelting": (0.3, 0.6), "casting": (0.2, 0.5),
                                    "masonry": (0.2, 0.5), "pottery": (0.2, 0.4)},
                     skills={"build": (0.3, 0.6)},
                     beasts={"goat": 2}, kit={"copper": 2, "charcoal": 4}, builds=["house", "store"]),
        leanings=dict(industry=0.75, sociability=0.4, boldness=0.45, generosity=0.4, curiosity=0.55, ambition=0.5),
        customs=dict(lead="blood", inherit="eldest", guest=False, raid_honour=False),
        gods=["the Smith Below", "the Mountain"], festival="winter",
        colours=["#5b5f66", "#a8742f"]),
    "lake": dict(
        folk="lake folk", homeland="valley",
        tongue=dict(onsets=["p", "t", "k", "h", "ts", "w", "m", "n", "e"], vowels=["a", "i", "u", "e", "ae", "ui"],
                    codas=["", "", "t", "k", "p", "n", "l"], word="the lake tongue"),
        lifeway=dict(era=1, crafts={"farming": (0.3, 0.6), "pottery": (0.3, 0.6), "weaving": (0.3, 0.6), "boatbuilding": (0.2, 0.4),
                                    "dyeing": (0.2, 0.5)},
                     skills={"fish": (0.3, 0.5)},
                     beasts={"pig": 2, "goat": 2}, kit={"grain": 6, "pot": 1}, builds=["house", "store", "farm"]),
        leanings=dict(industry=0.6, sociability=0.6, boldness=0.4, generosity=0.55, curiosity=0.5, ambition=0.55),
        customs=dict(lead="vote", inherit="shared", guest=True, raid_honour=False),
        gods=["the Still Water", "the Harvest Twins"], festival="autumn",
        colours=["#6b4a8c", "#e2c98f"]),
}

# when a land's regions are many of one kind, the peoples who could have them, in order
BY_HOMELAND = {}
for _k, _v in PEOPLES.items():
    BY_HOMELAND.setdefault(_v["homeland"], []).append(_k)


LEAD = {"blood": "the eldest of the leading house leads", "boldest": "the boldest leads", "vote": "leaders are chosen by all"}
INHERIT = {"eldest": "the eldest child inherits", "shared": "children share what the dead leave"}


def customs_text(people):
    """A people's ways, in a few words, for those who live by them."""
    c = PEOPLES[people]["customs"]
    out = [LEAD[c["lead"]], INHERIT[c["inherit"]]]
    if c.get("guest"):
        out.append("a guest is sacred")
    if c.get("raid_honour"):
        out.append("what is taken from strangers by daring is no shame")
    return "; ".join(out)
