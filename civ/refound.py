"""Re-founding a world as a towns world on the large land (towns_spec §10, world5 step 6, WP6): the land doubled
(civ/upsample.py), each cluster of homes (c87) a settlement laid out by the planner, each household's home, stores,
workshops, pens and strips raised again in it, everyone and everything they are kept: kin, groups, memories, goods,
skills, seats. Deterministic.

    from civ.refound import refound
    w, report = refound(state_dict)

What is kept and what is not (v1):
- Households: those under one roof (an adult without a home joins a partner's or parent's, else is alone). A
  household keeps its best dwelling (the kind it had), stores for its goods (one per 200, at most 3, the goods shared
  among them as they lay), one workshop of each kind it had with what they held, pens for its beasts (8 a pen) with
  what they held, as many strips as it had farms (at most 4 a grown person), crops carried over; posted trades go to
  its first store. Each is raised in its owner's name (a grown child's store and fields stay theirs). What the dead
  left with no heir among a settlement's homes goes to a granary open to all its people.
- Settlements: a cluster of homes split, along its longer side, into parts no larger than its people's way of life
  feeds (CAP: forest folk 8 households, valley folk 48); a part of 3+ households is a settlement near its homes'
  middle, named from the place nearest it as c87 named it; smaller ones join the nearest settlement within 4 old tiles, else are a homestead where they were.
  Each keeps one of each commons building found among its homes (a shrine, a market, a hall...).
- People: everyone to their household's settlement (one far from home in the old land would be twice as far now: a
  first draft left children 40 tiles from their parents, and they starved).
  Plans in hand are dropped (they named old places); memories, beliefs and life lines keep their places, "(x,y)"
  doubled. Seats for minds are kept.
- The dead: each settlement's burial ground takes the latest 40 graves and cairns among its homes, names and carved
  words kept; the rest are counted and dropped.
- Dropped: roads, bridges, tolls, goods lying on the ground, trails and footfall (they
  wear again at the new scale), raiding bands, offers of tenancy; tenancies running keep their strip when it was
  raised again.
"""
import math
import random
import re
from collections import Counter, defaultdict

from .census import clusters
from .content import BUILDINGS
from .content.towns import zone
from .upsample import K, upsample
from .world import World, dist

COORD = re.compile(r"\((\d+),\s*(\d+)\)")
DWELLING_RANK = ("shelter", "house", "brick_house", "stone_house")
GRAVES = 40             # the latest graves and cairns a settlement's burial ground takes
FARMS = 4               # strips a grown person keeps at most
CAP = {"valley": 48, "coast": 24, "steppe": 14, "upland": 12, "forest": 8}     # households a settlement, by homeland


def double_text(s):
    """Places named as (x,y) in a text, at the new scale."""
    return COORD.sub(lambda m: f"({int(m[1]) * K},{int(m[2]) * K})", s) if isinstance(s, str) else s


def dkey(k):
    x, y = k.split(",")
    return f"{int(x) * K},{int(y) * K}"


def roles(kind):
    return BUILDINGS.get(kind, {}).get("roles", {})


def warmth(kind):
    sh = roles(kind).get("shelter") or {}
    return (sh.get("warmth", 0), sh.get("beds", 0), DWELLING_RANK.index(kind) if kind in DWELLING_RANK else -1)


def capacity(kind):
    return (roles(kind).get("store") or {}).get("capacity", 0)


def known_at_scale(known, deposits):
    """What one knows of places, at the new scale: a place's key doubled (a deposit's to where it now lies in its
    block), a herd's last place doubled, the rest as it was."""
    out = {}
    for a, b in (known or {}).items():
        if re.fullmatch(r"\d+,\d+", a):
            x, y = map(int, a.split(","))
            a = next((f"{K * x + i},{K * y + j}" for j in range(K) for i in range(K) if f"{K * x + i},{K * y + j}" in deposits),
                     f"{K * x},{K * y}")
        elif isinstance(b, list) and len(b) >= 5 and b[0] == "herd":
            b = b[:3] + [b[3] * K, b[4] * K] + b[5:]
        out[a] = b
    return out


def good_ground(w, x0, y0, r=6):
    """Tiles near (x0, y0) to found a settlement on, the most land to sow about them first (rich soil and grass within
    3 tiles, as its strips may lie), then the nearest: the doubled land puts the fields world4's people had twice as
    far from their homes, and a village set down in the forest has none."""
    on = BUILDINGS["farm"]["roles"]["farm"]["on"]
    def sow(x, y):
        return sum(on.get(w.terrain[y + j][x + i], 0) for i in range(-3, 4) for j in range(-3, 4) if w.inb(x + i, y + j))
    cands = [(x, y) for x in range(x0 - r, x0 + r + 1) for y in range(y0 - r, y0 + r + 1)
             if w.inb(x, y) and w.passable(x, y) and w.terrain[y][x] != "~"]
    return sorted(cands, key=lambda t: (-round(sow(*t)), max(abs(t[0] - x0), abs(t[1] - y0)), t))


def people_dict(d, deposits):
    """The saved people at the new scale: positions doubled, plans dropped, places in their minds doubled."""
    out = {}
    for k, v in d["people"].items():
        v = dict(v)
        v["x"], v["y"] = v["x"] * K, v["y"] * K
        v.update(home=None, act=None, inside=None, pos=None, intent=None)
        v["known"] = known_at_scale(v.get("known"), deposits)
        v["memory"] = double_text(v.get("memory", ""))
        v["self_view"] = double_text(v.get("self_view", ""))
        v["beliefs"] = {a: double_text(b) for a, b in (v.get("beliefs") or {}).items()}
        v["life"] = [[t, double_text(x)] for t, x in (v.get("life") or [])]
        v["events"] = []
        v["wake"] = []
        out[k] = v
    return out


def refound(d, seed=None):
    old = World.from_dict(d)
    rep = {"kept": Counter(), "removed": Counter(), "lost_goods": 0, "graves": 0}

    # ---- households (old) ----
    home_of = {}
    for p in old.living():
        b = old.buildings.get(p.home) if p.home else None
        if b is not None and b.done and zone(b.kind) == "dwelling":
            home_of[p.id] = b.id
    for p in old.living():
        if p.id not in home_of:
            for o in (p.partner, *(p.parents or [])):
                if o in home_of:
                    home_of[p.id] = home_of[o]
                    break
            else:
                home_of[p.id] = -p.id                   # alone
    households = defaultdict(list)
    for pid, h in home_of.items():
        households[h].append(pid)

    def where(h):
        b = old.buildings.get(h) if h > 0 else None
        p = old.people[-h] if h < 0 else None
        return (b.x, b.y) if b is not None else (p.x, p.y)

    # clusters of homes (c87), each split into settlements its people's way of life can feed from the land about
    # them: forest folk lived spread over many tiles' foraging; packed onto one they starve (a first draft of world5
    # lost a fifth of its forest folk in half a year)
    from .content.peoples import PEOPLES
    cl = []
    for c in clusters(old):
        tiles = set(c["homes"])
        hs = sorted(h for h in households if where(h) in tiles)
        folk = Counter(old.people[pid].people for pid in c["people"] if old.people[pid].people).most_common(1)
        cap = CAP.get(PEOPLES.get(folk[0][0], {}).get("homeland") if folk else None, 24)
        todo = [hs]
        while todo:
            part = todo.pop()
            if len(part) <= cap:
                pts = [where(h) for h in part]
                cl.append({"homes": sorted(set(pts)), "people": [pid for h in part for pid in households[h]],
                           "households": part, "name_from": c["homes"]})
                continue
            pts = [where(h) for h in part]
            xs, ys = [x for x, _ in pts], [y for _, y in pts]
            axis = 0 if max(xs) - min(xs) >= max(ys) - min(ys) else 1
            part = sorted(part, key=lambda h: (where(h)[axis], where(h)[1 - axis], h))
            todo += [part[:len(part) // 2], part[len(part) // 2:]]
    hh_cl = {h: i for i, c in enumerate(cl) for h in c["households"]}

    # ---- the new world: the land doubled, people kept, buildings to be raised again ----
    u = upsample(d, seed)
    nd = dict(d)
    nd["cfg"] = dict(d["cfg"], format="towns1", width=u["cfg"]["width"], height=u["cfg"]["height"],
                     scale=u["cfg"].get("scale", K))
    for k in ("terrain", "deposits", "herds", "packs", "places", "fish", "regions", "region_rows"):
        if k in u:
            nd[k] = u[k]
    nd.update(buildings={}, roads=[], trails=[], foot={}, piles={}, tolls={}, bands={}, rites={}, sites={}, site_at={},
              fieldmap={})
    rep["lost_goods"] += sum(sum(v.values()) for v in d.get("piles", {}).values())
    nd["signs"] = {dkey(k): v for k, v in d.get("signs", {}).items()}
    nd["people"] = people_dict(d, u["deposits"])
    nd["news"] = {k: dict(v, x=v.get("x", 0) * K, y=v.get("y", 0) * K, text=double_text(v.get("text", "")))
                  for k, v in d.get("news", {}).items()}
    nd["offers"] = {k: v for k, v in d.get("offers", {}).items() if str(v.get("kind")) != "tenancy"}
    nd["tenancies"] = []
    nd["groups"] = {k: dict(g, treasury=None) for k, g in d["groups"].items()}
    w = World.from_dict(nd)
    rng = random.Random((w.seed or 0) * 31 + 7)
    from . import towns
    from .realm import found_site, raise_placed

    # ---- settlements ----
    site_of_cl = {}
    for i in sorted(range(len(cl)), key=lambda i: (-len(cl[i]["people"]), i)):
        hs = cl[i]["households"]
        if len(hs) < 3:
            continue
        c = cl[i]
        cx = sum(x for x, _ in c["homes"]) / len(c["homes"])
        cy = sum(y for _, y in c["homes"]) / len(c["homes"])
        folk = Counter(old.people[pid].people for pid in c["people"] if old.people[pid].people).most_common(1)
        site = None
        for x, y in good_ground(w, int(cx * K) + 1, int(cy * K) + 1):
            site = towns.found(w, x, y, folk[0][0] if folk else "")
            if not isinstance(site, str):
                break
            site = None
        if site is None:
            site = found_site(w, rng, folk[0][0] if folk else "", int(cx * K) + 1, int(cy * K) + 1)
        if site is None:
            continue
        near = [pl for pl in d.get("places", []) if min(max(abs(pl[0] - x), abs(pl[1] - y)) for x, y in c["homes"]) <= 6]
        if near:
            name = min(near, key=lambda pl: dist(cx, cy, pl[0], pl[1]))[2]
            if name and not any(s.name == name for s in w.sites.values()):
                site.name = name
        site_of_cl[i] = site

    def home_site(h):
        i = hh_cl.get(h)
        if i in site_of_cl:
            return site_of_cl[i]
        x, y = where(h)
        near = [s for s in w.sites.values() if s.form != "homestead" and max(abs(s.x - x * K), abs(s.y - y * K)) <= 4 * K]
        if near:
            return min(near, key=lambda s: (max(abs(s.x - x * K), abs(s.y - y * K)), s.id))
        folk = next((old.people[pid].people for pid in households[h] if old.people[pid].people), "")
        for r in range(0, 4):
            for nx, ny in sorted(w.beside(x * K, y * K, r), key=lambda t: t):
                if max(abs(nx - x * K), abs(ny - y * K)) != r:
                    continue
                if w.site_of(nx, ny) is not None:
                    s = w.site_of(nx, ny)
                    return s
                s = towns.found(w, nx, ny, folk, form="homestead")
                if not isinstance(s, str):
                    return s
        return None

    # ---- households laid out ----
    new_farm = {}                                       # old farm id -> new
    new_store = {}                                      # head id -> first new store
    for h in sorted(households, key=lambda h: (hh_cl.get(h) is None, h)):
        members = [w.people[pid] for pid in households[h]]
        site = home_site(h)
        if site is None:
            continue
        oh = old.buildings.get(h) if h > 0 else None
        head = w.people.get(oh.owner) if oh is not None and oh.owner in households[h] else None
        head = head or max(members, key=lambda p: (p.adult(w.tick), -p.born, -p.id))
        for p in members:                               # everyone home: on the doubled land a child foraging 20
            p.x, p.y = site.x, site.y                   # tiles out would be 40 from its parents (a draft starved them)
        kind = oh.kind if oh is not None and zone(oh.kind) == "dwelling" else "shelter"
        home = raise_placed(w, kind, head) or (raise_placed(w, "shelter", head) if kind != "shelter" else None)
        if home is not None:
            rep["kept"][home.kind] += 1
            if oh is not None:
                home.inv = dict(oh.inv)
            for p in members:
                p.home = home.id
        # each member's stores, workshops, pens and strips, raised again in their own name (a grown child's food and
        # fields stay theirs: a household shares its workshops, not its stores)
        for o in sorted(members, key=lambda p: (p is not head, p.id)):
            owned = [ob for ob in old.buildings.values() if ob.owner == o.id and ob.done and ob.id != h]
            if not owned:
                continue
            was = (o.x, o.y)
            o.x, o.y = site.x, site.y
            lay_out(w, o, owned, home if o is head else None, rep, new_farm, new_store)
            o.x, o.y = was

    # ---- the commons: one of each kind found among a settlement's homes ----
    for i, site in site_of_cl.items():
        tiles = set(cl[i]["homes"])
        near = [ob for ob in old.buildings.values() if ob.done and zone(ob.kind) == "commons"
                and any(max(abs(ob.x - x), abs(ob.y - y)) <= 1 for x, y in tiles)]
        here = [p for p in w.living() if (p.x, p.y) == (site.x, site.y)]
        if not here:
            continue
        for k in sorted({ob.kind for ob in near}):
            ob = next(o for o in near if o.kind == k)
            by = w.people.get(ob.owner) if ob.owner and ob.owner > 0 and w.people.get(ob.owner) in here else here[0]
            b = raise_placed(w, k, by)
            if b is not None:
                b.owner, b.inv = ob.owner, dict(ob.inv)
                rep["kept"][k] += 1
        # what the dead left with no heir among its homes: a granary open to all its people, kept by its largest
        # household's head (towns_spec §10.4; world4's heirless pens alone held some 15,000 food)
        left = Counter()
        for ob in old.buildings.values():
            if old.empty(ob) and any(max(abs(ob.x - x), abs(ob.y - y)) <= 1 for x, y in tiles):
                left.update(ob.inv)
        if sum(left.values()) >= 20:
            homes = Counter(w.buildings[p.home].owner for p in here if p.home in w.buildings)
            keeper = w.people.get(homes.most_common(1)[0][0]) if homes else here[0]
            b = raise_placed(w, "granary", keeper if keeper in here else here[0]) or raise_placed(w, "store", here[0])
            if b is not None:
                b.inv, b.access = dict(left), "anyone"
                rep["kept"][b.kind] += 1
                rep["heirless_goods"] = rep.get("heirless_goods", 0) + sum(left.values())
        # the dead: the latest graves and cairns among its homes go to its burial ground, names and words kept
        dead = sorted((ob for ob in old.buildings.values() if ob.kind in ("grave", "cairn") and ob.done
                       and any(max(abs(ob.x - x), abs(ob.y - y)) <= 2 for x, y in tiles)), key=lambda ob: (-ob.built, ob.id))
        for ob in dead[:GRAVES]:
            b = raise_placed(w, ob.kind, here[0])
            if b is None:
                break
            b.owner, b.name, b.text, b.built = ob.owner, ob.name, ob.text, ob.built
            rep["kept"][ob.kind] += 1

    # ---- what refers to buildings ----
    for t in d.get("tenancies", []):
        if not t.get("done") and t.get("field") in new_farm:
            w.tenancies.append(dict(t, field=new_farm[t["field"]]))
    for g in w.groups.values():
        st = new_store.get(g.leader)
        g.treasury = st.id if st is not None and g.dissolved is None else None
    for b in old.buildings.values():
        if b.kind in ("grave", "cairn"):
            rep["graves"] += 1
    kept = sum(rep["kept"].values())
    for k, n in Counter(b.kind for b in old.buildings.values()).items():
        rep["removed"][k] += max(0, n - rep["kept"].get(k, 0))
    w.rebuild_many()
    w.rebuild_grid()
    sizes = Counter(s.id for p in w.living() for s in [w.site_of(p.x, p.y)] if s is not None)
    rep.update(households=len(households), settlements=sum(1 for s in w.sites.values() if s.form != "homestead"),
               homesteads=sum(1 for s in w.sites.values() if s.form == "homestead"), buildings=kept,
               housed=sum(1 for p in w.living() if p.home), people=len(w.living()),
               largest=sorted(sizes.values(), reverse=True)[:8], size=[w.w, w.h])
    return w, rep

def lay_out(w, o, owned, home, rep, new_farm, new_store):
    """One person's buildings raised again where the planner puts them, in their name: stores holding the goods of
    their stores and other roofs, one workshop of each kind with what they held, pens for their beasts, strips."""
    from .realm import raise_placed
    stores = sorted((ob for ob in owned if capacity(ob.kind) and zone(ob.kind) == "yard"), key=lambda ob: -capacity(ob.kind))
    goods = Counter()
    for ob in stores:
        goods.update(ob.inv)
    for ob in owned:                                    # what their other roofs held comes too
        if zone(ob.kind) == "dwelling":
            goods.update(ob.inv)
    n = min(3, len(stores), max(1, math.ceil(sum(goods.values()) / 200))) if stores else 0
    made = [b for b in (raise_placed(w, ob.kind, o) for ob in stores[:n]) if b is not None]
    # shared among the new stores as they lay (a store may hold more than it takes, as the old ones did); with no
    # store raised, into the home
    into = made or ([home] if home is not None else [])
    for item in sorted(goods):
        each, extra = divmod(goods[item], len(into)) if into else (0, 0)
        for j, b in enumerate(into):
            if each + (j < extra):
                b.inv[item] = b.inv.get(item, 0) + each + (j < extra)
    if not into:
        rep["lost_goods"] += sum(goods.values())
    if made:
        made[0].trade = [t for ob in stores for t in (ob.trade or [])][:6]
        new_store[o.id] = made[0]
    for b in made:
        rep["kept"][b.kind] += 1
    for k in sorted({ob.kind for ob in owned if "workshop" in roles(ob.kind) and zone(ob.kind) in ("yard", "edge")}):
        b = raise_placed(w, k, o)
        held = Counter()
        for ob in owned:
            if ob.kind == k:
                held.update(ob.inv)
        if b is not None:
            rep["kept"][k] += 1
            b.inv = dict(held)
        else:
            rep["lost_goods"] += sum(held.values())
    beasts, held = Counter(), Counter()
    pens = [ob for ob in owned if "pen" in roles(ob.kind)]
    for ob in pens:
        beasts.update(ob.animals or {})
        held.update(ob.inv)
    raised = []
    for i in range(max(1, math.ceil(sum(beasts.values()) / 8)) if pens else 0):
        b = raise_placed(w, pens[min(i, len(pens) - 1)].kind, o)
        if b is None:
            break
        raised.append(b)
        rep["kept"][b.kind] += 1
        if i == 0:
            b.inv, held = dict(held), Counter()
        for a in list(beasts):
            take = min(beasts[a], 8 - sum(b.animals.values()))
            if take > 0:
                b.animals[a] = b.animals.get(a, 0) + take
                beasts[a] -= take
    for a, n in beasts.items():                         # no room for another pen: crowded in, not lost
        if n > 0 and raised:
            raised[-1].animals[a] = raised[-1].animals.get(a, 0) + n
        elif n > 0:
            rep["beasts_lost"] = rep.get("beasts_lost", 0) + n
    rep["lost_goods"] += sum(held.values())
    farms = [ob for ob in owned if ob.kind == "farm"]
    want = farms[:FARMS if o.adult(w.tick) else 0]
    rep["farms_wanted"] = rep.get("farms_wanted", 0) + len(want)
    rep["farms_over_cap"] = rep.get("farms_over_cap", 0) + len(farms) - len(want)
    for ob in want:
        b = raise_placed(w, "farm", o)
        if b is None:
            rep["farms_no_room"] = rep.get("farms_no_room", 0) + 1
            site = w.site_of(o.x, o.y)
            rep.setdefault("no_room_at", Counter())[f"{site.form if site else 'none'} on {w.terrain[o.y][o.x]}"] += 1
            continue
        b.crop = dict(ob.crop) if ob.crop else None
        b.inv = dict(ob.inv)
        new_farm[ob.id] = b.id
        rep["kept"]["farm"] += 1
