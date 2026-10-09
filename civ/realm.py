"""Founding a world in the middle of history (grand world, docs/grand.md Phase 2): a continent of regions,
peoples in their homelands at the era their land supports, settlements of households with their homes, stores,
fields and pens already standing, and each people's tongue, leanings, skills and customs. Initial conditions,
never outcomes: what the peoples make of the land and of one another is theirs.

    from civ.realm import generate
    w = generate({"seed": 3, "width": 192, "height": 192, "people": 1800})
"""
import random

from .content import BUILDINGS, PASSABLE, TERRAIN
from .content.peoples import PEOPLES, BY_HOMELAND
from .continent import terrain as continent_terrain, regions as continent_regions
from .gen import DEFAULTS, place_deposits, place_herds
from .names import make_name, temperament, want, group_rules
from .world import World, Person, Building, Group, key, dist, TPY

# how many people a region of each kind feeds, against a valley (people for its size)
FEEDS = {"valley": 1.0, "coast": 0.7, "upland": 0.45, "forest": 0.35, "steppe": 0.4}
# households in a settlement, by lifeway's homeland: farmers in villages, herders and riders in camps, foragers in bands
SETTLEMENT = {"valley": (6, 12), "coast": (5, 9), "upland": (3, 6), "steppe": (4, 7), "forest": (3, 5)}
TRAITS = ("industry", "sociability", "boldness", "generosity", "curiosity", "ambition")


def generate(cfg=None):
    cfg = {**DEFAULTS, "width": 192, "height": 192, "people": 1800, "land": "continent", **(cfg or {})}
    wd = World(cfg)
    rng = wd.rng
    rows, comp, elev, wet = continent_terrain(rng, wd.w, wd.h)
    wd.terrain = rows
    reg, regions = continent_regions(rng, rows, comp, wet)
    wd.regions = regions
    wd.region_of = reg
    place_deposits(wd, random.Random(wd.seed * 7919 + 1))
    place_herds(wd, rng, comp)
    settle(wd, rng, comp)
    for r in wd.regions:
        wd.years[str(r["id"])] = "good"
    wd.rebuild_grid()
    return wd


def data_title(people):
    return PEOPLES[people].get("title", "chief")


def choose_peoples(rng, regions):
    """Each people its homeland: the largest region of its kind not yet taken (a valley for the river folk, the
    uplands for the hill clans...). Regions left over are wild: room to grow, land to quarrel over."""
    taken, out = set(), {}
    for kind in ("valley", "coast", "upland", "steppe", "forest"):
        cands = sorted((r for r in regions if r["kind"] == kind and r["id"] not in taken), key=lambda r: -r["size"])
        for people in BY_HOMELAND.get(kind, []):
            if not cands:
                break
            r = cands.pop(0)
            out[people] = r
            taken.add(r["id"])
    return out


def settle(wd, rng, comp):
    homes = choose_peoples(rng, wd.regions)
    weight = {p: r["size"] * FEEDS[r["kind"]] for p, r in homes.items()}
    total = sum(weight.values()) or 1
    wd.peoples = {}
    for people, region in homes.items():
        data = PEOPLES[people]
        own = make_name(rng, set(), data["tongue"])
        wd.peoples[people] = {"name": own, "region": region["id"], "word": data["tongue"]["word"]}
        region["people"] = people
        region["name"] = make_name(rng, set(), data["tongue"]) + ("land" if data["homeland"] != "valley" else "dale")
        n = max(12, round(wd.cfg["people"] * weight[people] / total))
        before = set(wd.groups)
        found_people_of(wd, rng, people, region, n)
        # a people in the middle of its history: its settlements a chiefdom, the greatest at its head and the rest
        # sworn to it, paying what their lifeway yields (c71)
        mine = sorted((wd.groups[g] for g in wd.groups if g not in before), key=lambda g: -len(g.members))
        for g in mine:
            g.title = data_title(people)
        for g in mine[1:]:
            g.parent, g.tribute = mine[0].id, dict(PEOPLES[people].get("tribute", {}))


def sites(wd, region, kind, n, rng):
    """Places for n settlements in a region: good ground for the lifeway, near fresh water, apart from each other."""
    W = wd.w
    tiles = [(x, y) for y in range(wd.h) for x in range(W) if wd.region_of[y * W + x] == region["id"]]
    def good(t):
        x, y = t
        c = wd.t(x, y)
        water = any(wd.inb(x + dx, y + dy) and wd.t(x + dx, y + dy) == "~" for dx in (-3, 0, 3) for dy in (-3, 0, 3))
        want = {"valley": ",.", "coast": ".s,T", "upland": "h.", "steppe": ".,", "forest": "T."}[kind]
        return (c in want) * 2 + water * 2 + (c == ",") + rng.random()
    tiles.sort(key=good, reverse=True)
    gap = max(6, int((len(tiles) / max(1, n)) ** 0.5 * 0.7))
    out = []
    for t in tiles:
        if all(dist(t[0], t[1], s[0], s[1]) >= gap for s in out):
            out.append(t)
        if len(out) >= n:
            break
    return out


def found_people_of(wd, rng, people, region, n):
    data = PEOPLES[people]
    kind = data["homeland"]
    lo, hi = SETTLEMENT[kind]
    per_settlement = 5 * (lo + hi) // 2
    places = sites(wd, region, kind, max(1, round(n / per_settlement)), rng)
    left = n
    for i, (sx, sy) in enumerate(places):
        size = left if i == len(places) - 1 else min(left, max(8, round(n / len(places))))
        left -= size
        found_settlement(wd, rng, people, sx, sy, size)
        if left <= 0:
            break


def free_spot(wd, x, y, r=6, want=None):
    for rr in range(r + 1):
        for bx, by in wd.beside(x, y, rr):
            if max(abs(bx - x), abs(by - y)) == rr and wd.passable(bx, by) and not wd.building_at(bx, by) \
                    and key(bx, by) not in wd.deposits and (not want or wd.t(bx, by) in want):
                return bx, by
    return None


def raise_building(wd, kind, owner, x, y):
    b = Building(id=wd.new_id(), kind=kind, x=x, y=y, owner=owner, hp=BUILDINGS[kind]["hp"], done=True, built=wd.tick)
    wd.buildings[b.id] = b
    wd.at[key(x, y)] = b.id
    return b


def person_of(wd, rng, people, x, y, age, parents=()):
    data = PEOPLES[people]
    lean = data["leanings"]
    p = Person(id=wd.new_id(), name=make_name(rng, wd.names, data["tongue"]), x=x, y=y, born=wd.tick - int(age * TPY),
               lifespan=int(rng.uniform(62, 88) * TPY),
               traits={t: round(min(1, max(0, rng.gauss(lean.get(t, 0.5), 0.18))), 2) for t in TRAITS},
               temperament=temperament(rng), wants=want(rng), strength=rng.randint(1, 3), parents=list(parents))
    p.people = people
    p.skills[f"tongue:{people}"] = 1.0
    for g in ("gather", "hunt", "fish", "fight", "build"):
        p.skills[g] = round(rng.random() * 0.3, 2)
    grown = min(1.0, age / 20)
    for c, (a, b) in data["lifeway"]["crafts"].items():
        p.skills[c] = round(rng.uniform(a, b) * grown, 2)
    for c, (a, b) in data["lifeway"].get("skills", {}).items():
        p.skills[c] = round(rng.uniform(a, b) * grown, 2)
    wd.people[p.id] = p
    return p


def found_settlement(wd, rng, people, sx, sy, size):
    """Households of kin (two grown, their children, sometimes an elder), each with a home, the farmers' fields and
    the herders' pens, a store and a fire to share; one household leads, by the people's custom."""
    data = PEOPLES[people]
    life = data["lifeway"]
    homes_kind = life["builds"][0]
    heads = []
    made = []
    while size > 0:
        hx, hy = free_spot(wd, sx, sy, 8) or (sx, sy)
        n = min(size, rng.randint(3, 6))
        size -= n
        a = person_of(wd, rng, people, hx, hy, rng.uniform(22, 45))
        fam = [a]
        if n >= 2:
            b = person_of(wd, rng, people, hx, hy, max(16, a.age(wd.tick) + rng.uniform(-6, 6)))
            a.partner, b.partner = b.id, a.id
            fam.append(b)
        for _ in range(n - len(fam)):
            c = person_of(wd, rng, people, hx, hy, rng.uniform(1, min(20, a.age(wd.tick) - 15)), parents=[x.id for x in fam[:2]])
            for par in fam[:2]:
                par.children.append(c.id)
            fam.append(c)
        home = raise_building(wd, homes_kind, a.id, hx, hy)
        for q in fam:
            q.home = home.id
            q.inv = dict(life.get("kit", {})) if q.adult(wd.tick) else {"berries": 2}
        if "store" in life["builds"]:
            s = free_spot(wd, hx, hy, 3)
            if s:
                raise_building(wd, "store", a.id, *s)
        if "farm" in life["builds"]:
            for _ in range(2):
                f = free_spot(wd, hx, hy, 5, ",.")
                if f:
                    raise_building(wd, "farm", a.id, *f)
        if life.get("beasts") and "pen" in life["builds"] or life.get("beasts") and rng.random() < 0.5:
            pspot = free_spot(wd, hx, hy, 4, ".,h")
            if pspot:
                pen = raise_building(wd, "pen", a.id, *pspot)
                pen.animals = {k: v for k, v in life["beasts"].items()}
        heads.append(a)
        made += fam
    fire = free_spot(wd, sx, sy, 3)
    if fire:
        raise_building(wd, "fire", heads[0].id, *fire).fuel = 24
    # who leads, by custom: the eldest head (blood), the boldest (the clans and riders), or by choosing (a vote)
    lead = data["customs"]["lead"]
    if lead == "boldest":
        leader = max(heads, key=lambda q: q.traits["boldness"] + q.skill("fight"))
    elif lead == "blood":
        leader = max(heads, key=lambda q: q.age(wd.tick))
    else:
        leader = rng.choice(heads)
    g = Group(id=wd.new_id(), name=f"{leader.name}'s people", founder=leader.id, leader=leader.id,
              members=[q.id for q in made if q.adult(wd.tick)], rules=group_rules(rng, leader.traits, leader.name),
              decide="vote" if lead == "vote" else "leader")
    wd.groups[g.id] = g
    for q in made:
        if q.adult(wd.tick):
            q.groups.append(g.id)
    # kin within a household trust each other; a settlement knows its own; a people its own, a little
    for q in made:
        for o in made:
            if q.id != o.id:
                same = q.home == o.home
                q.rel[str(o.id)] = {"trust": 0.5 if same else 0.25, "met": 0, **({"kin": "kin"} if same else {})}
        for x, y in wd.beside(q.x, q.y, 14):
            d = wd.deposits.get(key(x, y))
            if d:
                q.known[key(x, y)] = ["deposit", d["kind"], 0]
