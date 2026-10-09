"""The executor: plan steps carried out, the same for every mind.

A step is a dict {"do": verb, ...}. start_<verb> checks it and sets p.act (returning (False, why)
if it cannot be done); do_<verb> runs an hour of it and returns ("go" | "done" | "fail", message).
Walking to where the work is is part of every step: steps name what, the executor finds where
(the nearest source in sight, else the nearest remembered)."""
from .content import TERRAIN, DEPOSITS, WILD, TAME, BUILDINGS, CRAFTS, RECIPES
from .content import items as I
from .content.crafts import tool_options, recipes_making, recipes_for
from .world import Building, key, unkey, dist, direction, TPD, DPS

# wrongs one knows of, first-hand or heard: what makes striking someone just in one's eyes
WRONGS = ("robbed", "took_crop", "attacked", "kin_killed", "saw_steal", "saw_attack", "heard_wrong")
FIRST_HAND = ("robbed", "took_crop", "attacked", "kin_killed")

ALIASES = {"berry": "berries", "fiber": "fibre", "logs": "wood", "log": "wood", "rock": "stone", "rocks": "stone",
           "stones": "stone", "wheat": "grain", "crop": "grain", "copper ore": "copper_ore", "tin ore": "tin_ore",
           "iron ore": "iron_ore", "green stone": "copper_ore", "black stone": "tin_ore", "red stone": "iron_ore",
           "bog iron": "iron_ore", "goats": "goat", "sheep": "sheep", "cows": "cattle", "cow": "cattle", "ox": "cattle",
           "oxen": "cattle", "pigs": "pig", "horses": "horse", "deer": "deer", "boars": "boar", "linen cloth": "linen",
           "wool cloth": "woolcloth", "planks": "plank", "bricks": "brick", "coins": "coin", "tablets": "tablet"}

LAND_FOODS = {"berries", "nuts", "grain", "honey"}     # foods gathered from the land, any one of which will do when hungry
VERBS = ["go", "gather", "hunt", "fish", "eat", "rest", "sleep", "wait", "craft", "build", "plant", "put", "take", "drop",
         "give", "tame", "slaughter", "teach", "study", "attack", "follow", "trade", "post", "set_access", "propose",
         "accept", "refuse", "write", "found_group", "invite", "join", "leave", "expel", "call_vote", "vote",
         "make_law", "set_dues", "mark", "name_place", "bury", "do", "fuel", "claim", "mend"]


def _names():
    out = {}
    for k, d in DEPOSITS.items():
        out[d["name"].lower()] = d.get("gives", k)
        out[d["name"].lower().split(" (")[0]] = d.get("gives", k)
    for k, v in WILD.items():
        out[v["name"].lower()] = k
    return out


NAMES = _names()


def coords(v):
    """(x, y) from "(31,29)", "31,29", [31, 29] or {"x":..}, else None."""
    import re
    if isinstance(v, (list, tuple)) and len(v) == 2:
        v = f"{v[0]},{v[1]}"
    m = re.search(r"(-?\d+)\s*,\s*(-?\d+)", str(v or "")) or \
        re.search(r"x\s*[:=]?\s*(-?\d+)\D{0,4}y\s*[:=]?\s*(-?\d+)", str(v or "").lower())     # "x:32,y:28"
    return (int(m.group(1)), int(m.group(2))) if m else None


def norm(s):
    if s is None:
        return None
    s = str(s).strip().lower()
    if s in ("none", "nothing", "null", "any", ""):
        return None
    if s in NAMES:
        return NAMES[s]
    if s.startswith("wild ") and s[5:] in I.ITEMS:
        return s[5:]
    s = ALIASES.get(s, s)
    s = s.replace(" ", "_")
    if s.endswith("s") and s[:-1] in I.ITEMS and s not in I.ITEMS:
        s = s[:-1]
    return ALIASES.get(s, s)


def num(v, d=1, lo=1, hi=99):
    try:
        v = int(float(v))
    except (TypeError, ValueError):
        return d
    return max(lo, min(hi, v))


def mend_stuff(b):
    """What a building is mended with: one of what it is made of, the lightest to carry first (wood for a
    shelter, stone for a cairn); a building made of nothing (a grave) with wood."""
    cost = BUILDINGS[b.kind]["cost"]
    return min(cost, key=lambda k: I.info(k).get("w", 1)) if cost else "wood"


def mend_text(b):
    return f"1 {I.pretty(mend_stuff(b))}"


class Acts:
    # ================= starting a step =================
    def start(self, p, step):
        verb = str(step.get("do", "")).strip().lower()
        if verb not in VERBS:
            return False, f"'{verb}' is not something one can do"
        lighten = self.lighten(p, step) if verb in ("gather", "take") else None
        if lighten:
            return lighten
        res = getattr(self, "start_" + verb)(p, dict(step))
        if res is True or res is None:
            return True, ""
        if isinstance(res, str):
            return False, res
        return res

    def lighten(self, p, step):
        """Laden too full to carry even one more of what is wanted, with a store of one's own near: put
        the bulkiest of the rest there first, then take up the step again (c46: 'you can carry no more'
        was the commonest refusal of a take from one's own store)."""
        item = norm(step.get("item"))
        if not item or item not in I.ITEMS or step.get("lightened") or self.room(p, item) >= 1:
            return None
        rest = [k for k in p.inv if k != item and isinstance(p.inv[k], (int, float)) and p.inv[k] > 0
                and not I.info(k).get("wear") and not I.info(k).get("tool")]
        if not rest:
            return None
        bulky = max(rest, key=lambda k: p.inv[k] * I.info(k).get("w", 1))
        st = self.building_near(p, lambda b: b.done and "store" in BUILDINGS[b.kind]["roles"] and b.owner in (p.id, p.partner)
                                and self.has_room(b, bulky), r=10)
        if not st:
            return None
        if p.intent is not None:
            p.intent.setdefault("plan", []).insert(0, dict(step, lightened=True))
        res = self.start_put(p, {"item": bulky, "n": p.inv[bulky], "x": st.x, "y": st.y})
        if res is True or res is None:
            self.tell(p, f"Laden full, you went to set down your {I.pretty(bulky)} in your store at ({st.x},{st.y}) first.")
            return True, ""
        if p.intent is not None and p.intent.get("plan"):
            p.intent["plan"].pop(0)
        return None

    def set(self, p, verb, **kw):
        p.act = {"do": verb, **kw}
        return True

    def walk(self, p, act, x, y, adjacent=False):
        """Set the way to (x, y); an act with a way first walks it."""
        path = self.path(p, x, y, adjacent)
        if path is None:
            return False
        act["path"] = path
        act["dest"] = [x, y, adjacent]
        return True

    def walking(self, p, act):
        """Walk an hour if not there yet: True while walking."""
        if act.get("dest") and act.get("path") is None:
            x, y, adj = act["dest"]
            if not self.walk(p, act, x, y, adj):
                return "fail"
        if act.get("path"):
            self.step_along(p, act)
            return True
        return False

    # ================= where things are =================
    def sources(self, item):
        """What yields an item: ('terrain', chars) and/or ('deposit', kinds), or ('farm',)."""
        out = []
        ter = [c for c, t in TERRAIN.items() if item in t.get("yields", {})]
        if ter:
            out.append(("terrain", ter))
        deps = [k for k, d in DEPOSITS.items() if d.get("gives", k) == item]
        if deps:
            out.append(("deposit", deps))
        if item in ("grain", "flax", "hay"):
            out.append(("farm", None))
        return out

    def yield_here(self, p, item, x, y, theirs=False):
        """Can item be gathered from tile (x, y) now? Returns the source kind or None. Someone else's
        field counts only when one means to reap it (theirs=True: named by place)."""
        w = self.w
        b = w.building_at(x, y)
        if b and b.done and b.inv.get(item) and "farm" in BUILDINGS[b.kind]["roles"]:
            return "farm" if theirs or w.may_use(p, b) else None
        d = w.deposits.get(key(x, y))
        if d and d["left"] > 0 and DEPOSITS[d["kind"]].get("gives", d["kind"]) == item:
            return "deposit"
        t = TERRAIN[w.t(x, y)]
        season = t.get("yields", {}).get(item, "")
        if item in t.get("yields", {}) and (season is None or w.season() in season) and not (b and b.done and not BUILDINGS[b.kind].get("overlay")):
            return "terrain"
        return None

    def find(self, p, item, far=True):
        """Nearest tile that yields item now, in sight; else the nearest remembered. (x, y) or None."""
        w = self.w
        r = self.sight(p)
        best = None
        cut = {k for k, t in self.unreachable.get(p.id, {}).items() if w.tick - t < TPD * 10}

        def edge(x, y):
            # one can stand on it or beside it: the heart of a mountain or a lake is never offered
            return w.passable(x, y) or any(w.passable(i, j) for i, j in w.beside(x, y))
        for x, y in w.beside(p.x, p.y, r):
            if key(x, y) not in cut and self.yield_here(p, item, x, y) and edge(x, y):
                d = dist(p.x, p.y, x, y)
                if best is None or d < best[0]:
                    best = (d, x, y)
        if best:
            return best[1], best[2]
        if not far:
            return None
        for k, v in sorted(p.known.items(), key=lambda kv: dist(p.x, p.y, *unkey(kv[0])) if "," in kv[0] else 999):
            if "," not in k:
                continue
            x, y = unkey(k)
            if k in cut or not edge(x, y):
                continue
            if v[0] == "deposit" and DEPOSITS.get(v[1], {}).get("gives", v[1]) == item and self.yield_here(p, item, x, y):
                return x, y
            if v[0] == "building" and item in ("grain", "flax") and self.yield_here(p, item, x, y):
                return x, y
        # plain terrain further than sight: search a wider ring (each ring only past the one before). A search
        # that found nothing is remembered for the neighbourhood a few hours: in a crowded, worked-out land the
        # same empty rings were searched again and again (half of an hour's work in the long land, c57)
        if any(s[0] == "terrain" for s in self.sources(item)):
            memo = self.__dict__.setdefault("_far_none", {})
            nk = (item, p.x // 4, p.y // 4)
            if w.tick - memo.get(nk, -99) < 6:
                return None
            inner = r
            for rr in (10, 16, 24):
                for x, y in w.beside(p.x, p.y, rr):
                    if dist(p.x, p.y, x, y) <= inner:
                        continue
                    if key(x, y) not in cut and self.yield_here(p, item, x, y) == "terrain" and edge(x, y):
                        return x, y
                inner = rr
            if len(memo) > 5000:
                memo.clear()
            memo[nk] = w.tick
        return None

    def far_terrain(self, p, item, r=48):
        """The nearest tile beyond the usual search whose land yields item and that one can stand on or beside:
        ((x, y), steps) or None. Only for telling a person where it is to be had."""
        w = self.w
        if not any(s[0] == "terrain" for s in self.sources(item)):
            return None
        best = None
        for x, y in w.beside(p.x, p.y, r):
            if self.yield_here(p, item, x, y) == "terrain" and (w.passable(x, y) or any(w.passable(i, j) for i, j in w.beside(x, y))):
                d = dist(p.x, p.y, x, y)
                if best is None or d < best[1]:
                    best = ((x, y), d)
        return best

    def building_near(self, p, test, r=None, usable=True):
        """Nearest finished building passing test(b) that p may use, in sight or remembered."""
        w = self.w
        r = r or self.sight(p)
        cands = [b for b in w.buildings.values() if b.done and test(b) and (not usable or w.may_use(p, b))
                 and (dist(p.x, p.y, b.x, b.y) <= r or key(b.x, b.y) in p.known or b.owner == p.id)]
        return min(cands, key=lambda b: dist(p.x, p.y, b.x, b.y)) if cands else None

    def stores_beside(self, p):
        return [b for b in (self.w.building_at(x, y) for x, y in self.w.beside(p.x, p.y))
                if b and b.done and "store" in BUILDINGS[b.kind]["roles"] and self.w.may_use(p, b)]

    def have(self, p, item, n, stores=None):
        return p.inv.get(item, 0) + sum(b.inv.get(item, 0) for b in (stores or [])) >= n

    def use_up(self, p, item, n, stores=None):
        n -= I.remove(p.inv, item, n)
        for b in stores or []:
            if n > 0:
                n -= I.remove(b.inv, item, n)

    def full_text(self, p):
        """What weighs one down, and where it could be put."""
        heavy = sorted(p.inv, key=lambda k: -p.inv[k] * I.info(k).get("w", 1))[:3]
        st = self.building_near(p, lambda b: b.done and "store" in BUILDINGS[b.kind]["roles"] and b.owner in (p.id, p.partner), r=30)
        return (f"you can carry no more: your load is {p.load():.0f} of {p.capacity(self.w.tick):.0f}, most of it "
                + ", ".join(f"{p.inv[k]} {I.pretty(k)}" for k in heavy)
                + (f"; put some in your store at ({st.x},{st.y}) or drop it" if st else "; drop some, or build a store"))

    def room(self, p, item):
        free = p.capacity(self.w.tick) - p.load()
        return int(free / max(0.01, I.info(item)["w"]))

    # ================= go, rest, wait =================
    def start_go(self, p, a):
        w = self.w
        x, y = a.get("x"), a.get("y")
        if a.get("to") and not coords(a.get("to")):
            o = w.by_name(a["to"])
            if not o:
                return f"no one called {a['to']} is known to be alive"
            x, y = o.x, o.y
            adj = True
        else:
            adj = False
        if a.get("place"):
            name = str(a["place"]).lower()
            hit = next((pl for pl in w.places if pl[2].lower() == name), None)
            home = w.buildings.get(p.home) if p.home else None
            if hit:
                x, y = hit[0], hit[1]
            elif coords(a["place"]):
                x, y = coords(a["place"])
            elif home and name in ("home", "my home", "my house", "my shelter", "the shelter", "house", "shelter"):
                x, y = home.x, home.y
        if (x is None or y is None) and coords(a.get("to") or a.get("text")):
            x, y = coords(a.get("to") or a.get("text"))
        try:
            x, y = int(x), int(y)
        except (TypeError, ValueError):
            return "go where? give x and y, a person (to) or a named place"
        if not w.inb(x, y):
            return "that is beyond the land"
        act = {"do": "go"}
        if not self.walk(p, act, x, y, adj or not w.passable(x, y)):
            return f"there is no way to ({x},{y}) from here"
        p.act = act
        return True

    def do_go(self, p, a):
        if self.walking(p, a) is True:
            return "go", ""
        return "done", ""

    def start_rest(self, p, a):
        return self.set(p, "rest", left=num(a.get("hours"), 6, 1, 12))

    start_sleep = start_rest

    def do_rest(self, p, a):
        p.rest = True
        a["left"] -= 1
        return ("go", "") if a["left"] > 0 else ("done", "")

    do_sleep = do_rest

    def start_wait(self, p, a):
        return self.set(p, "wait", left=num(a.get("hours"), 2, 1, 12))

    def do_wait(self, p, a):
        a["left"] -= 1
        return ("go", "") if a["left"] > 0 else ("done", "")

    # ================= gathering =================
    def start_gather(self, p, a):
        item = norm(a.get("item"))
        if item == "seeds":
            item = "fibre"
        if item in I.ITEMS and not self.sources(item) and any(pile.get(item) for k, pile in self.w.piles.items()
                                                             if dist(p.x, p.y, *unkey(k)) <= self.sight(p)):
            return self.start_take(p, dict(a, item=item, gathering=True))   # it lies on the ground in sight: pick it up
        if item in ("hide", "meat", "bone"):
            return self.start_hunt(p, {"keep": item if item != "meat" else None})    # what the land gives by hunting: hunt
        if item == "fish" and self.water_near(p):
            return self.start_fish(p, {"hours": 6})
        if item in ("hide", "meat", "bone", "fish", "milk", "wool"):
            return f"{I.pretty(item)} is not gathered: " + ("hunt (animal) or slaughter at your pen" if item in ("hide", "meat", "bone")
                                                            else "fish (hours)" if item == "fish" else "take it from your pen")
        if not item:
            return "gather what? (item: berries, nuts, wood, stone, fibre, reeds, clay, flint, herbs, grain from a ripe field...)"
        if item not in I.ITEMS or not self.sources(item):
            return f"{item} is not gathered from the land (gather: berries, nuts, wood, stone, fibre, reeds, hay, sand, herbs, honey, clay, flint, flax, salt, copper_ore, tin_ore, iron_ore, limestone, gold, grain from a ripe field)"
        hint = coords([a["x"], a["y"]]) if a.get("x") is not None and a.get("y") is not None else coords(a.get("at"))
        far = self.unreachable.get(p.id, {})
        aimed = bool(hint and self.w.inb(*hint) and key(*hint) not in far and self.yield_here(p, item, *hint, theirs=True))
        spot = hint if aimed else self.find(p, item)
        if not spot:
            # not to be had from the land now, but in one's own store: take it from there
            st = self.building_near(p, lambda b: b.done and "store" in BUILDINGS[b.kind]["roles"] and b.inv.get(item)
                                    and (b.owner in (p.id, p.partner) or self.w.may_use(p, b)), r=20)
            if st:
                return self.start_take(p, {"item": item, "n": a.get("n"), "x": st.x, "y": st.y})
            # a food the land does not give here now, but another it does: gather that instead
            if item in LAND_FOODS and not a.get("instead"):
                for alt in sorted(LAND_FOODS - {item}, key=lambda k: -I.info(k).get("food", 0)):
                    spot2 = self.find(p, alt, far=False) or (self.find(p, alt) if alt != "grain" else None)
                    if spot2 and dist(p.x, p.y, *spot2) <= 15:
                        if self.start_gather(p, dict(a, item=alt, x=spot2[0], y=spot2[1], instead=True)) is True:
                            self.tell(p, f"There was no {I.pretty(item)} to be had near you; you went to gather {I.pretty(alt)} instead.")
                            return True
            if item in ("grain", "flax", "hay") and self.w.season() == "winter":
                return f"nothing is ripe in winter: {I.pretty(item)} is had from stores, or by trade"
            growing = [b for b in self.w.buildings.values() if b.owner in (p.id, p.partner) and b.crop and b.crop.get("what") == item
                       and not b.crop.get("ripe")]
            if growing:
                b = min(growing, key=lambda b: b.crop["ripe_at"])
                return f"your {item} at ({b.x},{b.y}) is not ripe yet (about {max(1, -(-(b.crop['ripe_at'] - self.w.tick) // TPD))} days)"
            if DEPOSITS.get(item, {}).get("renew") == "bush":
                return f"you know of no {I.pretty(item)} left to gather: the bushes near you are picked bare (they fill again a few a day" + \
                    (", from spring)" if self.w.season() == "winter" else ")")
            off = self.far_terrain(p, item)
            if off:
                return f"no {I.pretty(item)} you can reach lies near: the nearest is at {off[0]} ({off[1]} steps away; " \
                       f"gather with that x and y to walk there, or trade for it)"
            return f"you know of no {I.pretty(item)} to gather" + (" in this season" if item in ("hay",) else "") + \
                (" (ripe fields of your own or open to you, or wild grain)" if item in ("grain", "flax") else "")
        act = {"do": "gather", "item": item, "want": num(a.get("n"), 99, 1, 99), "got": 0, "left": 16, "spot": list(spot),
               "theirs": aimed}
        if not self.walk(p, act, spot[0], spot[1], adjacent=not self.w.passable(*spot) or self.w.building_at(*spot) is not None):
            # remembered as out of reach for a while, so the next look finds another
            self.unreachable.setdefault(p.id, {})[key(*spot)] = self.w.tick
            for _ in range(3):                  # the place cannot be reached: the nearest that can
                other = self.find(p, item)
                if not other:
                    return f"there is no way to the {I.pretty(item)} at {spot}"
                if self.walk(p, act, other[0], other[1], adjacent=not self.w.passable(*other) or self.w.building_at(*other) is not None):
                    break
                self.unreachable[p.id][key(*other)] = self.w.tick
            else:
                return f"there is no way to the {I.pretty(item)} at {spot}"
            act["spot"], act["theirs"] = list(other), False
        p.act = act
        return True

    def do_gather(self, p, a):
        w = self.w
        wk = self.walking(p, a)
        if wk == "fail":
            return "fail", "The way was blocked."
        if wk:
            return "go", ""
        item = a["item"]
        spot = None
        for x, y in w.beside(p.x, p.y):
            if self.yield_here(p, item, x, y, theirs=a.get("theirs", False)):
                spot = (x, y)
                break
        if not spot:
            nxt = self.find(p, item, far=False)
            if nxt and a["left"] > 2:
                self.walk(p, a, nxt[0], nxt[1], adjacent=not w.passable(*nxt) or w.building_at(*nxt) is not None)
                a["left"] -= 1
                return "go", ""
            return "done", f"You gathered {a['got']} {I.pretty(item)}; there is no more here."
        src = self.yield_here(p, item, *spot, theirs=a.get("theirs", False))
        use = {"wood": "wood", "stone": "stone", "fibre": "fibre", "reeds": "fibre", "flax": "fibre", "hay": "reap",
               "grain": "reap", "clay": "dig", "copper_ore": "stone", "tin_ore": "stone", "iron_ore": "stone",
               "limestone": "stone", "salt": "dig", "sand": "dig", "gold": "dig"}.get(item)
        n = 1.0
        if use:
            n *= self.use_tool(p, use)
        if item == "grain":
            n *= 3
        if src == "farm":
            n *= 2                              # a sown field is reaped faster than wild grass is picked
        if w.is_night():
            n *= 0.5
        n += 1 if w.rng.random() < p.skill("gather") / 3 else 0
        n = int(n) + (1 if w.rng.random() < n - int(n) else 0)
        if src == "deposit":
            d = w.deposits[key(*spot)]
            n = min(n, d["left"])
        elif src == "farm":
            b = w.building_at(*spot)
            n = min(n, b.inv.get(item, 0))
        found = n
        n = min(n, max(0, self.room(p, item)) if not I.ITEMS[item].get("food") else n)
        if n <= 0:
            if found > 0:
                return "done", f"You gathered {a['got']} {I.pretty(item)}, and {self.full_text(p)}."
            a["left"] -= 1                      # a slow hour (the dark, bad luck): keep at it
            return ("go", "") if a["left"] > 0 else ("done", f"You gathered {a['got']} {I.pretty(item)}.")
        if src == "deposit":
            d = w.deposits[key(*spot)]
            d["left"] -= n
            if d["left"] <= 0 and not DEPOSITS[d["kind"]].get("renew"):
                del w.deposits[key(*spot)]
                self.see(spot[0], spot[1], f"The {DEPOSITS[d['kind']]['name']} at {spot[0]},{spot[1]} is worked out.")
                self.event("worked_out", f"The {DEPOSITS[d['kind']]['name']} at ({spot[0]},{spot[1]}) was worked out", p)
        elif src == "farm":
            b = w.building_at(*spot)
            I.remove(b.inv, item, n)
            if b.owner != p.id and not w.may_use(p, b):
                o = w.people.get(b.owner)
                if o:
                    self.trust(o, p, -0.15, ("took_crop", f"{p.name} reaped {n} {item} from your field"))
                    self.tell(o, f"{p.name} is reaping your field at {b.x},{b.y}.")
                    self.wake(o, f"{p.name} is taking your crop")
                self.event("take_crop", f"{p.name} reaped {n} {item} from {o.name if o else 'someone'}'s field", p, o)
            if item in ("grain", "flax"):
                self.practise(p, "farming", 0.01)
        I.add(p.inv, item, n)
        if item == "fibre" and w.season() in ("summer", "autumn") and w.rng.random() < 0.2:
            I.add(p.inv, "seeds", 1)
        if item == "grain" and src in ("deposit", "farm") and w.rng.random() < 0.3:
            I.add(p.inv, "seeds", 1)             # some of what is reaped is kept back as seed for sowing
        a["got"] += n
        self.practise(p, "gather", 0.002)
        a["left"] -= 1
        if a["got"] >= a["want"] or a["left"] <= 0:
            return "done", f"You gathered {a['got']} {I.pretty(item)}."
        return "go", ""

    # ================= hunting and fishing =================
    def herds_of(self, p, kind=None, far=True):
        w = self.w
        seen = [h for h in w.herds if h["n"] > 0 and (kind is None or h["kind"] == kind)
                and dist(p.x, p.y, h["x"], h["y"]) <= self.sight(p)]
        if not seen and far:
            ids = {int(k[4:]) for k, v in p.known.items() if k.startswith("herd") and (kind is None or v[1] == kind)}
            seen = [h for h in w.herds if h["id"] in ids and h["n"] > 0]
        return sorted(seen, key=lambda h: dist(p.x, p.y, h["x"], h["y"]))

    def start_hunt(self, p, a):
        kind = norm(a.get("animal") or a.get("item"))
        keep = norm(a.get("keep")) or (kind if kind in ("hide", "bone") else None)
        if kind in ("any", "animals", "", None, "food", "meat", "hide", "bone"):
            kind = None
        if kind and kind not in WILD:
            return f"{kind} are not hunted here (" + ", ".join(k.replace('_', ' ') for k in WILD) + ")"
        herds = self.herds_of(p, kind)
        if not herds and kind and self.herds_of(p):
            # none of that kind about, but other game is: hunt what there is
            herds = self.herds_of(p)
            self.tell(p, f"You know of no {kind.replace('_', ' ')} nearby; you went after the {WILD[herds[0]['kind']]['name']} instead.")
        if not herds:
            # none in sight or remembered: cast about for tracks a little further off (as far as a hunt can go)
            herds = sorted((h for h in self.w.herds if h["n"] > 0 and dist(p.x, p.y, h["x"], h["y"]) <= 20),
                           key=lambda h: (kind is not None and h["kind"] != kind, dist(p.x, p.y, h["x"], h["y"])))
            if herds:
                self.tell(p, f"You found the tracks of {WILD[herds[0]['kind']]['name']} {direction(p.x, p.y, herds[0]['x'], herds[0]['y'])}.")
        if not herds:
            what = kind.replace('_', ' ') if kind else 'animals to hunt'
            rest = [h for h in self.w.herds if h["n"] > 0]
            if not rest:
                return f"you know of no {what} nearby: the game is gone from the land (keep a pen, fish, or trade for meat)"
            h = min(rest, key=lambda h: dist(p.x, p.y, h["x"], h["y"]))
            return (f"you know of no {what} nearby: the game around here is hunted out; the nearest herd is about "
                    f"{dist(p.x, p.y, h['x'], h['y'])} steps {direction(p.x, p.y, h['x'], h['y'])}, where people are few "
                    "(go there to hunt, or keep a pen, fish, or trade for meat)")
        h = herds[0]
        act = {"do": "hunt", "herd": h["id"], "left": num(a.get("hours"), 8, 1, 12), "ready": False}
        if keep in ("hide", "bone"):
            act["keep"] = keep                  # take it up from where the beast falls
        p.act = act
        return True

    def do_hunt(self, p, a):
        w = self.w
        h = next((h for h in w.herds if h["id"] == a["herd"] and h["n"] > 0), None)
        if not h:
            return "done", "The herd is gone."
        if a.get("caught"):
            return "done", a["caught"]
        if dist(p.x, p.y, h["x"], h["y"]) > 1:
            a["ready"] = False
            if not a.get("path") or a.get("dest", [None, None])[:2] != [h["x"], h["y"]]:
                if not self.walk(p, a, h["x"], h["y"], True):
                    return "fail", "You cannot reach the herd."
            self.step_along(p, a)
            a["left"] -= 0.5
            return ("go", "") if a["left"] > 0 else ("done", "The herd kept away from you.")
        a["ready"] = True
        a["left"] -= 1
        return ("go", "") if a["left"] > 0 else ("done", "The hunt came to nothing.")

    def resolve_hunts(self):
        w = self.w
        for h in w.herds:
            if h["n"] <= 0:
                continue
            hunters = [p for p in w.near(h["x"], h["y"], 1) if p.act and p.act["do"] == "hunt"
                       and p.act.get("herd") == h["id"] and p.act.get("ready")]
            if not hunters:
                continue
            v = WILD[h["kind"]]
            k = len(hunters)
            chance = v["chance"][min(k, len(v["chance"]) - 1)]
            if k == 1 and I.best_tool(hunters[0].inv, "lone_hunt")[0]:
                chance = max(chance, 0.25)
            bonus = sum(0.08 * self.use_tool(o, "hunt") - 0.08 for o in hunters) + 0.04 * sum(o.skill("hunt") for o in hunters)
            if chance <= 0 or w.rng.random() >= min(0.95, chance + max(0, bonus)):
                continue
            h["n"] -= 1
            meat = v["meat"] + sum(self.use_tool(o, "butcher") - 1 for o in hunters)
            share, rem = divmod(int(meat), k)
            for i, o in enumerate(sorted(hunters, key=lambda o: o.id)):
                got = share + (1 if i < rem else 0)
                I.add(o.inv, "meat", got)
                self.practise(o, "hunt", 0.02)
                o.act["caught"] = f"The hunt succeeded: {got} meat for you" + (f", hunting with {', '.join(x.name for x in hunters if x.id != o.id)}" if k > 1 else "") + \
                    f". Its hide and bones lie where it fell ({h['x']},{h['y']}): take them."
                for x in hunters:
                    if x.id != o.id:
                        self.trust(o, x, 0.05, ("hunt", f"hunted with {x.name}"))
            pile = w.piles.setdefault(key(h["x"], h["y"]), {})
            I.add(pile, "hide", v["hide"])
            I.add(pile, "bone", v["bone"])
            for o in hunters:
                k = o.act.get("keep")
                n = min(pile.get(k, 0), max(0, self.room(o, k))) if k else 0
                if n > 0:
                    I.remove(pile, k, n)
                    I.add(o.inv, k, n)
                    o.act["caught"] = o.act["caught"].replace(": take them.", f"; you took up {n} {k}.")
            if not pile:
                del w.piles[key(h["x"], h["y"])]
            fierce = v.get("fierce", 0)
            if fierce and w.rng.random() < 0.3:
                o = w.rng.choice(hunters)
                dmg = max(0, fierce - I.best(o.inv, "armour")[0])
                o.health -= dmg
                self.tell(o, f"The {v['name']} gored you (lost {dmg} health).")
                if o.health <= 0:
                    self.die(o, f"killed by {v['name']}")
            self.event("hunt", f"{', '.join(o.name for o in hunters)} killed a {v['name'].rstrip('s')}", *hunters, animal=h["kind"])

    def water_near(self, p):
        w = self.w
        return any(TERRAIN[w.t(x, y)].get("water") for x, y in w.beside(p.x, p.y))

    def start_fish(self, p, a):
        w = self.w
        act = {"do": "fish", "left": num(a.get("hours"), 6, 1, 12), "got": 0}
        if not self.water_near(p):
            spot = None
            for rr in (self.sight(p), 12, 20):
                cands = [(x, y) for x, y in w.beside(p.x, p.y, rr) if TERRAIN[w.t(x, y)].get("water")]
                if cands:
                    spot = min(cands, key=lambda t: dist(p.x, p.y, *t))
                    break
            if not spot or not self.walk(p, act, spot[0], spot[1], True):
                return "you know of no water to fish in"
        p.act = act
        return True

    def do_fish(self, p, a):
        wk = self.walking(p, a)
        if wk == "fail":
            return "fail", "The way was blocked."
        if wk:
            return "go", ""
        if not self.water_near(p):
            return "fail", "There is no water beside you."
        chance = 0.12 * self.use_tool(p, "fish") + 0.1 * p.skill("fish")
        if self.w.rng.random() < min(0.8, chance):
            I.add(p.inv, "fish", 1)
            a["got"] += 1
            self.practise(p, "fish", 0.01)
        a["left"] -= 1
        if a["left"] <= 0:
            return "done", f"You caught {a['got']} fish."
        return "go", ""

    # ================= eating =================
    def start_eat(self, p, a):
        item = norm(a.get("item"))
        foods = [k for k in p.inv if I.info(k).get("food")]
        if item and p.inv.get(item) and I.info(item).get("heal"):
            # a remedy: taken, it mends the body and may drive out a sickness
            I.remove(p.inv, item, 1)
            p.health = min(p.max_health(self.w.tick), p.health + I.info(item)["heal"])
            if p.sick and self.w.rng.random() < 0.6:
                p.sick = None
                self.tell(p, "The sickness has passed.")
            return self.set(p, "rest", left=1)
        if item and item not in foods:
            if not foods:
                self.tell(p, "You had nothing to eat.")
                return self.set(p, "wait", left=1)  # nothing came of the gathering before it: no need to think again
            item = None                     # not that, but there is other food: eat what one has
        if not foods:
            return self.set(p, "wait", left=1)     # nothing left to eat: nothing to do
        return self.set(p, "eat", item=item or None, n=num(a.get("n"), 99, 1, 99))

    def do_eat(self, p, a):
        eaten = 0
        while p.satiety < 20 and eaten < a["n"]:
            foods = [k for k in p.inv if I.info(k).get("food") and (a["item"] in (None, k))]
            if not foods:
                break
            k = max(foods, key=lambda k: I.info(k).get("spoil", 0))
            I.remove(p.inv, k, 1)
            p.satiety = min(20, p.satiety + I.ITEMS[k]["food"])
            eaten += 1
        return "done", f"You ate {eaten}." if eaten else "You ate nothing."

    # ================= crafting =================
    def workshop_for(self, p, craft, want_free=False):
        return self.building_near(p, lambda b: craft in BUILDINGS[b.kind]["roles"].get("workshop", [])
                                  and (not want_free or not b.process), r=20)

    def pick_recipe(self, p, item, stores):
        rs = recipes_making(item)
        if not rs:
            return None, rs

        def ready(r):
            return all(self.have(p, k, n, stores) for k, n in r["ins"].items()) and all(
                any(p.inv.get(o) for o in tool_options(t)) or (t == "stone" and self.have(p, "stone", 1, stores)) for t in r["tools"])
        ok = [r for r in rs if ready(r)]
        return (ok[0] if ok else None), rs

    def short_text(self, p, r, stores):
        # what the land does not give, with where it comes from
        whence = {"meat": "a hunt, your pen or trade", "hide": "a hunt or trade", "bone": "a hunt or trade", "fish": "fishing",
                  "milk": "your pen", "wool": "your pen"}
        if not I.best_tool(p.inv, "fish")[0]:
            whence["fish"] = "fishing: bare hands catch about one a day, a line or net several; or trade"
        miss = [f"{n} {I.pretty(k)}" + (f" (from {whence[k]})" if k in whence else "") for k, n in r["ins"].items() if not self.have(p, k, n, stores)]
        miss += [("an axe" if t == "_axe" else "a " + I.pretty(t)) for t in r["tools"]
                 if not any(p.inv.get(o) for o in tool_options(t))]
        return ", ".join(miss)

    def start_craft(self, p, a):
        item = norm(a.get("item"))
        if not item:
            return "make what? (item)"
        if item not in I.ITEMS and item in CRAFTS:
            # a craft named, not a thing: its simplest thing that one could make (craft: cordage -> rope)
            rs = sorted(recipes_for(item), key=lambda r: (len(r["ins"]) + len(r["tools"]), r["hours"]))
            if rs:
                item = rs[0]["out"]
        if item not in I.ITEMS:
            return f"{item} is not a thing that can be made"
        stores = self.stores_beside(p)
        r, rs = self.pick_recipe(p, item, stores)
        if not rs:
            return f"{I.pretty(item)} is not made; it is found or gathered"
        if not r:
            # short only of what the land close by gives: gather that first, then make it
            for x in ([] if int(a.get("fetched") or 0) >= 2 or p.intent is None else rs):
                if self.can_try(p, x["craft"]) or not all(any(p.inv.get(o) for o in tool_options(t)) or t == "stone"
                                                          for t in x["tools"]):
                    continue
                miss = {k: n - p.inv.get(k, 0) - sum(b.inv.get(k, 0) for b in stores)
                        for k, n in x["ins"].items() if not self.have(p, k, n, stores)}
                def fetch(k, n):
                    # how to come by what is missing nearby: from one's own store or a workshop where a firing
                    # left it (charcoal in the kiln: c52), from the land, by fishing, or by a hunt
                    st = self.building_near(p, lambda b: b.done and b.inv.get(k) and not b.process and (
                        (b.owner in (p.id, p.partner) and "store" in BUILDINGS[b.kind]["roles"])
                        or "workshop" in BUILDINGS[b.kind]["roles"]), r=10)
                    if st and dist(p.x, p.y, st.x, st.y) <= 10:     # close by: a long walk for a part costs more
                        return {"do": "take", "item": k, "n": n, "x": st.x, "y": st.y}
                    if self.sources(k):
                        if self.find(p, k, far=False):
                            return {"do": "gather", "item": k, "n": n}
                        spot = self.find(p, k)              # remembered further off: worth the walk, within reason
                        if spot and dist(p.x, p.y, *spot) <= 30:
                            return {"do": "gather", "item": k, "n": n, "x": spot[0], "y": spot[1]}
                    if k == "fish" and self.water_near(p):
                        # as long as it is likely to take to catch them, within a day
                        rate = min(0.8, 0.12 * I.best_tool(p.inv, "fish")[1] + 0.1 * p.skill("fish"))
                        hours = -(-n // rate) if rate else 99
                        return {"do": "fish", "hours": int(hours)} if hours <= 12 else None
                    if k in ("meat", "hide", "bone") and self.herds_of(p):
                        return {"do": "hunt", "keep": k if k != "meat" else None}
                    # made, not found (the rope a cloak takes): make it first, if one can and its makings
                    # are to be had from the land or in hand; that craft fetches them in its turn
                    for r2 in recipes_making(k):
                        if r2["process"] or self.can_try(p, r2["craft"]) or r2["tools"]:
                            continue
                        if all(self.have(p, k2, n2 * n, stores) or self.sources(k2) for k2, n2 in r2["ins"].items()):
                            return {"do": "craft", "item": k, "n": max(1, -(-n // r2["n"]))}
                    return None
                gets = [fetch(k, n) for k, n in miss.items()]
                if miss and all(gets):
                    # two rounds at most: making a part (a rope) can use up what the whole still needs (fibre)
                    p.intent.setdefault("plan", [])[:0] = gets[1:] + [dict(a, fetched=int(a.get("fetched") or 0) + 1)]
                    return getattr(self, "start_" + gets[0]["do"])(p, gets[0])
            return f"to make {I.pretty(item)} you need " + " or ".join(self.short_text(p, x, stores) for x in rs[:2])
        why = self.can_try(p, r["craft"])
        if why:
            return f"{r['craft'].replace('_', ' ')} {why}"
        idx = RECIPES.index(r)
        act = {"do": "craft", "recipe": idx, "want": num(a.get("n"), 1, 1, 20), "made": 0, "left": None}
        at = CRAFTS[r["craft"]]["at"]
        if at:
            b = self.workshop_for(p, r["craft"], want_free=r["process"])
            if not b:
                kinds = [k for k, v in BUILDINGS.items() if r["craft"] in v["roles"].get("workshop", [])]
                return f"{I.pretty(item)} is made at a {' or '.join(kinds)}, and you know of none free that you may use"
            act["at"] = b.id
            if dist(p.x, p.y, b.x, b.y) > 1 and not self.walk(p, act, b.x, b.y, True):
                return f"there is no way to the {b.kind} at ({b.x},{b.y})"
        p.act = act
        return True

    def do_craft(self, p, a):
        w = self.w
        wk = self.walking(p, a)
        if wk == "fail":
            return "fail", "The way was blocked."
        if wk:
            return "go", ""
        r = RECIPES[a["recipe"]]
        out = I.pretty(r["out"])
        b = w.buildings.get(a.get("at")) if a.get("at") else None
        if a.get("at") and (not b or dist(p.x, p.y, b.x, b.y) > 1):
            return "fail", "The workshop is not beside you."
        stores = self.stores_beside(p)
        if r["process"]:
            if b.process:
                return "fail", f"The {b.kind} is already working."
            runs = 0
            while runs < a["want"] and all(self.have(p, k, n * (runs + 1), stores) for k, n in r["ins"].items()):
                runs += 1
            if not runs:
                return "fail", f"You need {self.short_text(p, r, stores)}."
            for k, n in r["ins"].items():
                self.use_up(p, k, n * runs, stores)
            ok = self.attempt(p, r["craft"])
            if runs > 1:                        # a load of several charges teaches more than one (c52)
                self.practise(p, r["craft"], 0.03 * (1 - p.skill(r["craft"])) * min(3, runs - 1))
            b.process = {"recipe": a["recipe"], "done_at": w.tick + r["hours"], "by": p.id, "runs": runs, "ok": ok}
            return "done", f"You set the {b.kind} to work: {runs * r['n']} {out}, ready in {r['hours']} hours, to be taken from it."
        if a["left"] is None:
            speed = I.best_tool(p.inv, f"speed:{r['craft']}")[1]
            a["left"] = max(1, round(r["hours"] / speed))
        a["left"] -= 1
        if a["left"] > 0:
            return "go", ""
        if not (all(self.have(p, k, n, stores) for k, n in r["ins"].items())):
            return "done", f"You made {a['made']} {out}; you ran out of what it takes."
        ok = self.attempt(p, r["craft"])
        for t in r["tools"]:
            k = next((o for o in tool_options(t) if p.inv.get(o)), None)
            if k and k != "stone":
                self.wear_out(p, k)
        if ok:
            for k, n in r["ins"].items():
                self.use_up(p, k, n, stores)
            I.add(p.inv, r["out"], r["n"])
            a["made"] += r["n"]
            self.event("made", f"{p.name} made {r['n']} {out}", p, item=r["out"], qty=r["n"], craft=r["craft"])
        else:
            for k, n in r["ins"].items():
                self.use_up(p, k, n // 2, stores)
            self.tell(p, f"Your {out} came out wrong ({self.fail_text(r)}); some of what went into it is spoiled.")
        if a["made"] < a["want"] * r["n"] and all(self.have(p, k, n, stores) for k, n in r["ins"].items()):
            a["left"] = None
            return "go", ""
        return "done", f"You made {a['made']} {out}."

    # ================= building =================
    def site_ok(self, p, kind, x, y):
        w = self.w
        B = BUILDINGS[kind]
        if not w.inb(x, y):
            return "that is beyond the land"
        if B.get("on") == "water":
            return None if TERRAIN[w.t(x, y)].get("water") else "a bridge stands on water"
        if not w.passable(x, y):
            return "the ground there will not take it"
        if B.get("overlay"):
            return "there is already a road there" if key(x, y) in w.roads else None
        if w.building_at(x, y):
            return f"there is already a {w.building_at(x, y).kind} there"
        farm = B["roles"].get("farm")
        if farm and w.t(x, y) not in farm["on"]:
            return "a field needs rich soil or grass"
        if B.get("near") == "water" and not any(TERRAIN[w.t(a, b)].get("water") for a, b in w.beside(x, y)):
            return "it must stand beside water"
        return None

    def start_build(self, p, a):
        w = self.w
        kind = norm(a.get("kind") or a.get("item"))
        if kind not in BUILDINGS:
            return "build what? (" + ", ".join(BUILDINGS) + ")"
        B = BUILDINGS[kind]
        if B.get("craft"):
            why = self.can_try(p, B["craft"])
            if why:
                return f"building a {kind} takes {B['craft'].replace('_', ' ')}, and {why}"
        x, y = a.get("x"), a.get("y")
        # an unfinished one of the same kind beside: help finish it
        for bx, by in w.beside(p.x, p.y):
            b = w.building_at(bx, by)
            if b and b.kind == kind and not b.done:
                return self.set(p, "build", bid=b.id)
        if x is None or y is None:
            spots = [(bx, by) for bx, by in w.beside(p.x, p.y) if not self.site_ok(p, kind, bx, by)]
            spots.sort(key=lambda t: (t != (p.x, p.y) if not B["roles"].get("wall") else t == (p.x, p.y)))
            if not spots:
                # crowded here: the nearest fitting place a little way off
                far = [(dist(p.x, p.y, bx, by), bx, by) for r in (2, 3, 4, 6) for bx, by in w.beside(p.x, p.y, r)
                       if dist(p.x, p.y, bx, by) == r and not self.site_ok(p, kind, bx, by)]
                if not far:
                    return f"there is no fitting place for a {kind} within 6 steps of you" + \
                        ("; an empty building near you may be claimed" if any(w.empty(c) for c in w.buildings.values()
                                                                             if dist(p.x, p.y, c.x, c.y) <= 8) else "")
                spots = [min(far)[1:]]
            x, y = spots[0]
        else:
            x, y = int(x), int(y)
            there = w.building_at(x, y) if w.inb(x, y) else None
            if there and there.kind == kind and not there.done and (self.w.may_use(p, there) or self.serving_owner(p, there)):
                act = {"do": "build", "bid": there.id}          # one's own unfinished work: go on with it
                if dist(p.x, p.y, x, y) > 1 and not self.walk(p, act, x, y, True):
                    return f"there is no way to ({x},{y})"
                p.act = act
                return True
            if self.site_ok(p, kind, x, y):
                # the place was taken since: the nearest free one around it
                near = [(dist(x, y, bx, by), bx, by) for r in (1, 2, 3) for bx, by in w.beside(x, y, r)
                        if not self.site_ok(p, kind, bx, by)]
                if near:
                    _, x, y = min(near)
        why = self.site_ok(p, kind, x, y)
        if why:
            return why
        act = {"do": "build", "kind": kind, "x": x, "y": y, "bid": None}
        if "monument" in B["roles"]:
            # what is carved on it, for all who pass, long after its maker
            act["name"] = " ".join(str(a.get("name") or "").split())[:40]
            act["text"] = " ".join(str(a.get("text") or a.get("words") or "").split())[:200]
        if dist(p.x, p.y, x, y) > 1 and not self.walk(p, act, x, y, True):
            return f"there is no way to ({x},{y})"
        p.act = act
        return True

    def do_build(self, p, a):
        w = self.w
        wk = self.walking(p, a)
        if wk == "fail":
            return "fail", "The way was blocked."
        if wk:
            return "go", ""
        b = w.buildings.get(a["bid"]) if a.get("bid") else None
        if not b:
            kind, x, y = a["kind"], a["x"], a["y"]
            why = self.site_ok(p, kind, x, y)
            if why:
                return "fail", why
            stores = self.stores_beside(p)
            cost = BUILDINGS[kind]["cost"]
            short = [f"{n} {I.pretty(k)}" for k, n in cost.items() if not self.have(p, k, n, stores)]
            if short:
                return "fail", f"A {kind} takes " + ", ".join(f"{n} {I.pretty(k)}" for k, n in cost.items()) + f"; you lack {', '.join(short)}."
            for k, n in cost.items():
                self.use_up(p, k, n, stores)
            B = BUILDINGS[kind]
            b = Building(id=w.new_id(), kind=kind, x=x, y=y, owner=p.id, hp=B["hp"], built=w.tick,
                         name=a.get("name", ""), text=a.get("text", ""))
            w.buildings[b.id] = b
            if B.get("overlay"):
                pass
            else:
                w.at[key(x, y)] = b.id
            a["bid"] = b.id
        if dist(p.x, p.y, b.x, b.y) > 1:
            return "fail", "You are no longer at the building."
        if b.done:
            return "done", f"The {b.kind} is finished."
        b.progress += 1 + p.skill("build")
        self.practise(p, "build", 0.005)
        B = BUILDINGS[b.kind]
        if b.progress >= B["hours"]:
            b.done = True
            if B.get("overlay") and "road" in B["roles"]:
                w.roads.add(key(b.x, b.y))
            if "hearth" in B["roles"]:
                b.fuel = B["roles"]["hearth"]["fuel"]
            c = B.get("craft")
            if c and CRAFTS[c].get("practice"):
                self.practise(p, c, 0.06 * (1 - p.skill(c)))
            owner = w.people.get(b.owner)
            self.event("build", f"{owner.name if owner else p.name} built a {b.kind} at ({b.x},{b.y})", p, building=b.kind, x=b.x, y=b.y)
            if "monument" in B["roles"] and (b.name or b.text):
                self.event("monument", f"{owner.name if owner else p.name} raised a {b.kind} at ({b.x},{b.y})"
                           + (f" called {b.name}" if b.name else "") + (f", carved: \"{b.text}\"" if b.text else ""),
                           p, building=b.kind, name=b.name, said=b.text)
            self.see(b.x, b.y, f"A {b.kind} was finished at ({b.x},{b.y}).", exclude={p.id})
            if owner and owner.id != p.id:
                self.trust(owner, p, 0.1, ("helped", f"{p.name} helped build your {b.kind}"))
            if b.owner == p.id and "shelter" in B["roles"] and not p.home:
                p.home = b.id
            return "done", f"You finished the {b.kind} at ({b.x},{b.y})."
        return "go", ""

    def start_claim(self, p, a):
        """Take as one's own an empty building: one whose owner is dead and left no heir."""
        w = self.w
        b = None
        if a.get("x") is not None and a.get("y") is not None:
            b = self.target_building(p, a, w.empty) or self.target_building(p, a, lambda b: b.done)
            if b and not w.empty(b):
                o = w.people.get(b.owner)
                return (f"the {b.kind} at ({b.x},{b.y}) is not empty: it is "
                        + ("yours" if b.owner in (p.id, p.partner) else f"{o.name}'s" if o else "a group's"))
        if not b:
            want = norm(a.get("kind") or a.get("item"))
            homeless = not self.has_own_home(p)
            cands = [c for c in w.buildings.values() if w.empty(c) and (not want or c.kind == want)
                     and dist(p.x, p.y, c.x, c.y) <= max(self.sight(p), 12)]
            if not cands:
                return "there is no empty building near you to claim (an empty one's owner is dead and left no heir)"
            cands.sort(key=lambda c: (not (homeless and "shelter" in BUILDINGS[c.kind]["roles"]), dist(p.x, p.y, c.x, c.y)))
            b = cands[0]
        act = {"do": "claim", "bid": b.id}
        if dist(p.x, p.y, b.x, b.y) > 1 and not self.walk(p, act, b.x, b.y, True):
            return f"there is no way to the {b.kind} at ({b.x},{b.y})"
        p.act = act
        return True

    # ================= upkeep (c59) =================
    def may_mend(self, p, b):
        """One's own or one's partner's; a group's one belongs to; one's master's (in service: the work one is
        hired for); and a monument, anyone's to tend."""
        w = self.w
        if "monument" in BUILDINGS[b.kind]["roles"] or b.owner in (p.id, p.partner) or self.serving_owner(p, b):
            return True
        g = w.groups.get(-b.owner) if b.owner and b.owner < 0 else None
        return bool(g and p.id in g.members)

    def start_mend(self, p, a):
        w = self.w
        worn = lambda b: b.done and b.hp < BUILDINGS[b.kind]["hp"] and self.may_mend(p, b)
        if a.get("x") is not None and a.get("y") is not None:
            b = self.target_building(p, a, lambda b: b.done)
            if not b:
                return "there is no building there to mend"
            if not self.may_mend(p, b):
                o = self.w.people.get(b.owner)
                return f"the {b.kind} at ({b.x},{b.y}) is {o.name + chr(39) + 's' if o else 'not yours'}: only its owner, or one in their service, mends it"
            if b.hp >= BUILDINGS[b.kind]["hp"]:
                return f"the {b.kind} at ({b.x},{b.y}) is whole; it needs no mending"
        else:
            cands = sorted((b for b in w.buildings.values() if worn(b) and dist(p.x, p.y, b.x, b.y) <= 15),
                           key=lambda b: b.hp / BUILDINGS[b.kind]["hp"])
            if not cands:
                return "nothing of yours near you needs mending"
            b = cands[0]
        stuff = mend_stuff(b)
        if not p.inv.get(stuff):
            st = self.building_near(p, lambda s: s.done and s.inv.get(stuff) and s.owner in (p.id, p.partner)
                                    and "store" in BUILDINGS[s.kind]["roles"], r=15)
            if st and not a.get("fetched") and p.intent is not None:
                p.intent.setdefault("plan", []).insert(0, dict(a, x=b.x, y=b.y, fetched=True))
                return self.start_take(p, {"item": stuff, "n": 1, "x": st.x, "y": st.y})
            return f"mending the {b.kind} at ({b.x},{b.y}) takes 1 {I.pretty(stuff)}, and you carry none"
        act = {"do": "mend", "bid": b.id, "left": 2}
        if dist(p.x, p.y, b.x, b.y) > 1 and not self.walk(p, act, b.x, b.y, True):
            return f"there is no way to the {b.kind} at ({b.x},{b.y})"
        p.act = act
        return True

    def do_mend(self, p, a):
        wk = self.walking(p, a)
        if wk:
            return ("fail", "The way was blocked.") if wk == "fail" else ("go", "")
        b = self.w.buildings.get(a["bid"])
        if not b or dist(p.x, p.y, b.x, b.y) > 1:
            return "fail", "It is not beside you."
        a["left"] -= 1
        if a["left"] > 0:
            return "go", ""
        stuff = mend_stuff(b)
        if not p.inv.get(stuff):
            return "fail", f"You had no {I.pretty(stuff)} left to mend it with."
        I.remove(p.inv, stuff, 1)
        b.hp = BUILDINGS[b.kind]["hp"]
        o = self.w.people.get(b.owner) if b.owner and b.owner > 0 else None
        if o and o.id != p.id and o.alive:
            self.tell(o, f"{p.name} mended your {b.kind} at ({b.x},{b.y}).")
        self.event("mend", f"{p.name} mended {(o.name + chr(39) + 's') if o and o.id != p.id else 'their'} {b.kind}", p, o,
                   building=b.kind, x=b.x, y=b.y)
        return "done", f"You mended the {b.kind}; it is whole again."

    def has_own_home(self, p):
        h = self.w.buildings.get(p.home)
        return bool(h and h.done and h.owner in (p.id, p.partner))

    def do_claim(self, p, a):
        wk = self.walking(p, a)
        if wk:
            return ("fail", "The way was blocked.") if wk == "fail" else ("go", "")
        w = self.w
        b = w.buildings.get(a["bid"])
        if not b or not w.empty(b):
            return "fail", "Someone had already claimed it." if b else "It had fallen down."
        was = w.people.get(b.owner)
        b.owner, b.access, b.allow = p.id, "owner", []
        b.hp = max(b.hp, BUILDINGS[b.kind]["hp"] // 2)
        if "shelter" in BUILDINGS[b.kind]["roles"] and not self.has_own_home(p):
            p.home = b.id
        self.event("claim", f"{p.name} claimed the empty {b.kind} at ({b.x},{b.y})"
                   + (f" that was {was.name}'s" if was else ""), p, building=b.kind, x=b.x, y=b.y)
        return "done", f"The {b.kind} at ({b.x},{b.y}) is yours now" + (", and your home." if p.home == b.id else ".")

    def start_fuel(self, p, a):
        fire = lambda b: "hearth" in BUILDINGS[b.kind]["roles"] and b.done
        b = self.target_building(p, a, fire) if a.get("x") is not None else None
        b = b or self.building_near(p, fire, r=2, usable=False) or self.building_near(p, fire, r=10)
        if not b:
            return "there is no fire near you to feed (build a fire: wood)"
        fuel = norm(a.get("item")) or ("charcoal" if p.inv.get("charcoal") else "wood")
        if fuel not in I.ITEMS or not I.ITEMS[fuel].get("fuel"):
            fuel = "wood"
        if not p.inv.get(fuel):
            # fetch it from one's store first, then feed the fire
            st = self.building_near(p, lambda s: s.done and "store" in BUILDINGS[s.kind]["roles"] and s.inv.get(fuel)
                                    and (s.owner in (p.id, p.partner) or self.w.may_use(p, s)), r=10)
            if a.get("fetched"):
                return "you carry nothing to burn (wood or charcoal; gather wood in a forest)"
            if st:
                fetch = {"item": fuel, "n": num(a.get("n"), 3, 1, 20), "x": st.x, "y": st.y}
            elif fuel == "wood" and self.find(p, "wood", far=False):
                fetch = None                    # no wood laid by: gather some nearby first
            else:
                return "you carry nothing to burn (wood or charcoal; gather wood in a forest)"
            if p.intent is not None:
                p.intent.setdefault("plan", []).insert(0, dict(a, item=fuel, fetched=True))
            if fetch is None:
                return self.start_gather(p, {"item": "wood", "n": num(a.get("n"), 3, 1, 20)})
            return self.start_take(p, fetch)
        act = {"do": "fuel", "bid": b.id, "item": fuel, "n": min(p.inv[fuel], num(a.get("n"), 2, 1, 20))}
        if dist(p.x, p.y, b.x, b.y) > 1 and not self.walk(p, act, b.x, b.y, True):
            return "there is no way to the fire"
        p.act = act
        return True

    def do_fuel(self, p, a):
        wk = self.walking(p, a)
        if wk:
            return ("fail", "The way was blocked.") if wk == "fail" else ("go", "")
        b = self.w.buildings.get(a["bid"])
        n = min(a["n"], p.inv.get(a["item"], 0))
        if not b or n <= 0:
            return "done", "There was nothing to burn, or no fire."
        I.remove(p.inv, a["item"], n)
        b.fuel += n * I.ITEMS[a["item"]]["fuel"] * 4
        b.hp = BUILDINGS[b.kind]["hp"]                  # a fire fed is a fire kept up
        return "done", f"The fire burns with your {I.pretty(a['item'])}."

    # ================= farming =================
    def start_plant(self, p, a):
        w = self.w
        what = norm(a.get("item")) or ("flax" if p.inv.get("flax") and not (p.inv.get("seeds") or p.inv.get("grain")) else "grain")
        if what in ("seeds", "grain", "wheat"):
            what = "grain"
            seed = "seeds" if p.inv.get("seeds") else "grain"
        elif what == "flax":
            seed = "flax"
        else:
            return "one sows grain (seeds or grain kept back) or flax"
        n = min(p.inv.get(seed, 0), num(a.get("n"), 8, 1, 8))
        if n <= 0:
            # none carried: from a store of one's own (or open to one), if there is a field to sow
            keep = ("seeds", "grain") if what == "grain" else ("flax",)
            st = None if a.get("fetched") or p.intent is None or w.season() == "winter" else self.building_near(
                p, lambda b: b.done and "store" in BUILDINGS[b.kind]["roles"] and any(b.inv.get(k) for k in keep)
                and (b.owner in (p.id, p.partner) or w.may_use(p, b)), r=20)
            field = st and self.building_near(p, lambda b: "farm" in BUILDINGS[b.kind]["roles"] and not b.crop and not b.inv, r=20)
            if st and field:
                k = next(k for k in keep if st.inv.get(k))
                p.intent.setdefault("plan", []).insert(0, dict(a, item=what, fetched=True))
                return self.start_take(p, {"item": k, "n": num(a.get("n"), 8, 1, 8), "x": st.x, "y": st.y})
            return f"you carry no {seed} to sow" + (" (keep some back from a harvest, or trade for seeds)" if what == "grain" else "")
        why = self.can_try(p, "farming")
        if why:
            return why
        if w.season() == "winter":
            return f"nothing grows if sown in winter; spring comes in {DPS - w.day() % DPS} days"
        b = self.building_near(p, lambda b: "farm" in BUILDINGS[b.kind]["roles"] and not b.crop and not b.inv, r=20)
        if not b and not a.get("reaped") and p.intent is not None:
            # one's own field still holds a harvest: reap it first, then sow
            full = self.building_near(p, lambda b: "farm" in BUILDINGS[b.kind]["roles"] and b.owner in (p.id, p.partner)
                                      and b.inv.get("grain") and (not b.crop or b.crop.get("ripe")), r=20)
            if full:
                p.intent.setdefault("plan", []).insert(0, dict(a, reaped=True))
                return self.start_gather(p, {"item": "grain", "x": full.x, "y": full.y})
        if not b:
            return "you know of no empty field you may sow (build a farm)"
        act = {"do": "plant", "bid": b.id, "what": what, "seed": seed, "n": n}
        if dist(p.x, p.y, b.x, b.y) > 1 and not self.walk(p, act, b.x, b.y, True):
            return "there is no way to the field"
        p.act = act
        return True

    def do_plant(self, p, a):
        w = self.w
        wk = self.walking(p, a)
        if wk == "fail":
            return "fail", "The way was blocked."
        if wk:
            return "go", ""
        b = w.buildings.get(a["bid"])
        if not b or b.crop or dist(p.x, p.y, b.x, b.y) > 1:
            return "fail", "The field is not free."
        n = min(a["n"], p.inv.get(a["seed"], 0))
        if n <= 0:
            return "fail", "You have nothing left to sow."
        I.remove(p.inv, a["seed"], n)
        soil = BUILDINGS[b.kind]["roles"]["farm"]["on"].get(w.t(b.x, b.y), 0.6)
        per = 8 if a["what"] == "grain" else 5
        f = soil * (0.7 + 0.6 * p.skill("farming"))
        # a plough drawn by an ox or horse of one's own doubles it
        plough, pf = I.best_tool(p.inv, "plough")
        if plough and any(bb.owner == p.id and (bb.animals.get("cattle") or bb.animals.get("horse")) for bb in w.buildings.values()):
            f *= pf
            self.wear_out(p, plough)
        if p.skill("astronomy") >= 0.3:
            f *= 1.25
        yld = max(1, int(n * per * f))
        b.crop = {"what": a["what"], "n": n, "sown": w.tick, "ripe_at": w.tick + TPD * 4, "yield": yld, "by": p.id}
        b.hp = BUILDINGS[b.kind]["hp"]                  # a field sown is a field kept up
        self.practise(p, "farming", 0.03 * (1 - p.skill("farming")))
        return "done", f"You sowed {n} {a['seed']}; in about 4 days the field will give about {yld} {a['what']}."

    # ================= putting and taking =================
    def target_building(self, p, a, test):
        w = self.w
        if a.get("x") is not None and a.get("y") is not None:
            x, y = int(a["x"]), int(a["y"])
            b = w.building_at(x, y)
            if b and test(b):
                return b
            # a step off: the one that fits beside the place named
            near = [w.building_at(bx, by) for bx, by in w.beside(x, y)]
            return next((b for b in near if b and test(b)), None)
        cands = [w.building_at(x, y) for x, y in w.beside(p.x, p.y)]
        cands = [b for b in cands if b and b.done and test(b)]
        return cands[0] if cands else self.building_near(p, test, usable=False)

    def start_put(self, p, a):
        item = norm(a.get("item"))
        if not item:
            return "put what? (item, n)"
        if not p.inv.get(item):
            self.tell(p, f"You had no {I.pretty(item)} to put away.")
            return self.set(p, "wait", left=1)  # what was to be put came to nothing before: no need to think again
        w = self.w
        holds = lambda b: any(r in BUILDINGS[b.kind]["roles"] for r in ("store", "pen", "workshop", "hearth", "library"))
        ok = lambda b: (w.may_use(p, b) or self.serving_owner(p, b)) and self.has_room(b, item)
        b = self.target_building(p, a, holds)
        if b and not ok(b):
            # not open to one, or full: one's own (or one open to one) with room instead
            other = self.building_near(p, lambda c: c.done and "store" in BUILDINGS[c.kind]["roles"] and c.owner in (p.id, p.partner) and ok(c), r=30)
            if other:
                b = other
            elif not w.may_use(p, b):
                return f"the {b.kind} at ({b.x},{b.y}) is not open to you, and you have no store with room (build a store)"
            # one's own, full, and no other with room: what does not fit is set down beside it (anyone may pick it up)
        if not b:
            return "there is no store, pen or workshop to put it in"
        act = {"do": "put", "bid": b.id, "item": item, "n": num(a.get("n"), p.inv[item], 1, 999)}
        if dist(p.x, p.y, b.x, b.y) > 1 and not self.walk(p, act, b.x, b.y, True):
            return "there is no way there"
        p.act = act
        return True

    def do_put(self, p, a):
        w = self.w
        wk = self.walking(p, a)
        if wk:
            return ("fail", "The way was blocked.") if wk == "fail" else ("go", "")
        if a.get("pile"):
            pile = w.piles.get(a["pile"]) or {}
            if I.info(a["item"]).get("food") and p.satiety < 14:
                while p.satiety < 17 and pile.get(a["item"]):        # hungry: eat there
                    I.remove(pile, a["item"], 1)
                    p.satiety = min(20, p.satiety + I.ITEMS[a["item"]]["food"])
            n = min(a["n"], pile.get(a["item"], 0), max(0, self.room(p, a["item"])))
            if n <= 0:
                return "done", "There was nothing there to take." if not pile.get(a["item"]) else self.full_text(p).capitalize() + "."
            I.remove(pile, a["item"], n)
            I.add(p.inv, a["item"], n)
            if not pile:
                w.piles.pop(a["pile"], None)
            return "done", f"You took {n} {I.pretty(a['item'])}."
        b = w.buildings.get(a["bid"])
        if not b or dist(p.x, p.y, b.x, b.y) > 1:
            return "fail", "It is not beside you."
        roles = BUILDINGS[b.kind]["roles"]
        if not w.may_use(p, b) and not self.serving_owner(p, b):
            return "done", f"The {b.kind} is not open to you; you kept your things."
        item = a["item"]
        n = min(a["n"], p.inv.get(item, 0))
        if "hearth" in roles and I.ITEMS.get(item, {}).get("fuel"):
            I.remove(p.inv, item, n)
            b.fuel += n * I.ITEMS[item]["fuel"] * 4
            return "done", f"You fed the fire {n} {I.pretty(item)}."
        if item.startswith("book:") and "library" in roles:
            I.remove(p.inv, item, n)
            b.books += [item[5:]] * n
            self.event("library", f"{p.name} gave a book on {item[5:]} to the library", p)
            return "done", "You put the book in the library, where anyone let in may read it."
        cap = roles.get("store", {}).get("capacity", 30)
        free = cap - I.weight(b.inv)
        n = min(n, int(free / max(0.01, I.info(item)["w"])))
        if n <= 0:
            if b.owner in (p.id, p.partner) and p.inv.get(item):
                # full: set down beside it, where anyone passing may take it
                k = min(a["n"], p.inv.get(item, 0))
                I.remove(p.inv, item, k)
                I.add(w.piles.setdefault(key(b.x, b.y), {}), item, k)
                return "done", f"The {b.kind} is full; you set {k} {I.pretty(item)} down beside it (anyone passing may take them; a store holds more)."
            return "done", f"The {b.kind} is full; you kept your {I.pretty(item)}."
        I.remove(p.inv, item, n)
        I.add(b.inv, item, n)
        if b.owner != p.id and w.people.get(b.owner):
            self.trust(w.people[b.owner], p, 0.03, ("store_in", f"{p.name} put {n} {item} into your {b.kind}"))
        return "done", f"You put {n} {I.pretty(item)} into the {b.kind}."

    def has_room(self, b, item):
        roles = BUILDINGS[b.kind]["roles"]
        if "store" not in roles:
            return True
        cap = roles.get("store", {}).get("capacity", 30)
        return cap - I.weight(b.inv) >= I.info(item).get("w", 1)

    def serving_owner(self, p, b):
        return any(not s["done"] and s["servant"] == p.id and s["master"] == b.owner for s in self.w.services)

    def start_take(self, p, a):
        w = self.w
        item = norm(a.get("item"))
        if item in BUILDINGS and "shelter" in BUILDINGS[item]["roles"]:
            # "take shelter": go in under a roof one may use, one's own first
            home = w.buildings.get(p.home)
            b = home if home and home.done and w.may_use(p, home) else \
                self.building_near(p, lambda b: "shelter" in BUILDINGS[b.kind]["roles"] and b.done, r=20)
            if not b:
                return "there is no shelter near that you may use (build a shelter: wood 5, fibre 4)"
            act = {"do": "go", "dest": [b.x, b.y, False]}
            if (p.x, p.y) != (b.x, b.y) and not self.walk(p, act, b.x, b.y, False):
                return "there is no way to the shelter"
            p.act = act
            return True
        if a.get("from") in ("ground", None) and item:
            for x, y in w.beside(p.x, p.y):
                pile = w.piles.get(key(x, y))
                if pile and pile.get(item):
                    n = min(pile[item], num(a.get("n"), pile[item], 1, 999), max(0, self.room(p, item)))
                    if n <= 0:
                        return self.full_text(p)
                    I.remove(pile, item, n)
                    I.add(p.inv, item, n)
                    if not pile:
                        del w.piles[key(x, y)]
                    return self.set(p, "wait", left=1)
            # a pile further off, named by its place or seen: walk to it
            at = coords([a["x"], a["y"]]) if a.get("x") is not None and a.get("y") is not None else coords(a.get("at"))
            spots = [at] if at else []
            spots += sorted((unkey(k) for k, pile in w.piles.items() if pile.get(item)
                             and dist(p.x, p.y, *unkey(k)) <= self.sight(p)), key=lambda t: dist(p.x, p.y, *t))
            for x, y in spots:
                if w.piles.get(key(x, y), {}).get(item) and not w.building_at(x, y):
                    act = {"do": "take", "pile": key(x, y), "item": item, "n": num(a.get("n"), 99, 1, 999)}
                    if self.walk(p, act, x, y, False):
                        p.act = act
                        return True
        if item in ("grain", "flax"):
            field = self.target_building(p, a, lambda b: "farm" in BUILDINGS[b.kind]["roles"] and b.inv.get(item))
            if field:
                return self.start_gather(p, dict(a, x=field.x, y=field.y))   # what stands in a field is reaped
        b = self.target_building(p, a, lambda b: (b.inv or b.animals) and (not item or b.inv.get(item)))
        if not b and item and self.sources(item) and self.find(p, item):
            return self.start_gather(p, a)                  # it comes from the land: gather it
        if not b and item:
            # not where named: from a store of one's own (or open to one) that holds it, if any
            b = self.building_near(p, lambda s: s.done and "store" in BUILDINGS[s.kind]["roles"] and s.inv.get(item)
                                   and (s.owner in (p.id, p.partner) or w.may_use(p, s)), r=20)
            if not b:
                named = w.building_at(int(a["x"]), int(a["y"])) if a.get("x") is not None and a.get("y") is not None else None
                if named:
                    return f"the {named.kind} at ({named.x},{named.y}) holds no {I.pretty(item)}" + (
                        (" (bare; nothing grows in winter: grain is had from stores, or by trade)" if w.season() == "winter"
                         else " (bare or not yet ripe: sow it, and reap it when ripe)")
                        if "farm" in BUILDINGS[named.kind]["roles"] else "")
        if b and not w.may_use(p, b) and not self.serving_owner(p, b):
            # closed to one: taken only on purpose, the building named by its place; a take that merely went
            # looking (or a gather) uses what is open to one instead (world2 under c50: 295 thefts by the
            # people, many a "gather" of berries that walked into a neighbour's shelter)
            here = a.get("x") is not None and a.get("y") is not None and dist(int(a["x"]), int(a["y"]), b.x, b.y) <= 1
            if a.get("gathering") or not here:
                o = w.people.get(b.owner)
                alt = self.building_near(p, lambda s: s.done and (s.inv.get(item) if item else s.inv)
                                         and (s.owner in (p.id, p.partner) or w.may_use(p, s)), r=20) if item else None
                if alt:
                    b = alt
                else:
                    return (f"the {I.pretty(item) if item else 'goods'} near you are in {o.name + chr(39) + 's' if o else 'someone' + chr(39) + 's'} "
                            f"{b.kind} at ({b.x},{b.y}), closed to you: taking from it is theft (to do it anyway, take naming its x,y)")
        if not b:
            return f"you see no {I.pretty(item) if item else 'thing'} to take"
        act = {"do": "take", "bid": b.id, "item": item, "n": num(a.get("n"), 99, 1, 999)}
        if dist(p.x, p.y, b.x, b.y) > 1 and not self.walk(p, act, b.x, b.y, True):
            return "there is no way there"
        p.act = act
        return True

    def do_take(self, p, a):
        w = self.w
        wk = self.walking(p, a)
        if wk:
            return ("fail", "The way was blocked.") if wk == "fail" else ("go", "")
        if a.get("pile"):
            pile = w.piles.get(a["pile"]) or {}
            if I.info(a["item"]).get("food") and p.satiety < 14:
                while p.satiety < 17 and pile.get(a["item"]):        # hungry: eat there
                    I.remove(pile, a["item"], 1)
                    p.satiety = min(20, p.satiety + I.ITEMS[a["item"]]["food"])
            n = min(a["n"], pile.get(a["item"], 0), max(0, self.room(p, a["item"])))
            if n <= 0:
                return "done", "There was nothing there to take." if not pile.get(a["item"]) else self.full_text(p).capitalize() + "."
            I.remove(pile, a["item"], n)
            I.add(p.inv, a["item"], n)
            if not pile:
                w.piles.pop(a["pile"], None)
            return "done", f"You took {n} {I.pretty(a['item'])}."
        b = w.buildings.get(a["bid"])
        if not b or dist(p.x, p.y, b.x, b.y) > 1:
            return "fail", "It is not beside you."
        item = a["item"] or next((k for k in b.inv if I.info(k).get("food")), None) or next(iter(b.inv), None)
        if not item or not b.inv.get(item):
            return "done", "There was nothing to take."
        ate = 0
        if I.info(item).get("food") and p.satiety < 14 and w.may_use(p, b):
            # hungry at one's own store: eat one's fill there, no need to carry it
            while p.satiety < 17 and b.inv.get(item):
                I.remove(b.inv, item, 1)
                p.satiety = min(20, p.satiety + I.ITEMS[item]["food"])
                ate += 1
        n = min(a["n"], b.inv.get(item, 0), max(0, self.room(p, item)))
        if n <= 0:
            return "done", (f"You ate {ate} {I.pretty(item)} there." if ate else self.full_text(p).capitalize() + ".")
        if not w.may_use(p, b):
            # taking from what is closed to you: known by name to whoever saw it, to the owner if near in daylight,
            # or by the tally a written tablet kept in it (c50: what writing is first for); else only found missing
            o = w.people.get(b.owner)
            seen = [x for x in w.near(b.x, b.y, 4) if x.id not in (p.id, b.owner)] if not w.is_night() else []
            tally = any(str(k).startswith("tablet:") or str(k).startswith("parchment:") for k in b.inv)
            known = bool(seen) or tally or (o and o.alive and not w.is_night() and dist(o.x, o.y, b.x, b.y) <= 6)
            if o and known:
                self.trust(o, p, -0.3, ("robbed", f"{p.name} took {n} {item} from your {b.kind}"))
                self.tell(o, f"{p.name} took {n} {I.pretty(item)} from your {b.kind} at ({b.x},{b.y})"
                          + (" (your tally shows it)." if tally and not seen else "."))
                self.wake(o, f"{p.name} took from your {b.kind}")
            elif o:
                self.tell(o, f"Someone took {n} {I.pretty(item)} from your {b.kind} at ({b.x},{b.y}); you do not know who.")
                self.wake(o, f"someone took from your {b.kind}")
            for x in seen:
                self.trust(x, p, -0.1, ("saw_steal", f"you saw {p.name} take from {o.name if o else 'someone'}'s {b.kind}"))
            self.event("steal", f"{p.name} took {n} {I.pretty(item)} from {o.name if o else 'someone'}'s {b.kind}", p, o, item=item, qty=n)
        I.remove(b.inv, item, n)
        I.add(p.inv, item, n)
        if not w.may_use(p, b):
            o = w.people.get(b.owner)
            return "done", f"You took {n} {I.pretty(item)} from {o.name + chr(39) + 's' if o else 'someone' + chr(39) + 's'} {b.kind}, which is closed to you."
        return "done", f"You took {n} {I.pretty(item)} from the {b.kind}."

    def start_drop(self, p, a):
        item = norm(a.get("item"))
        if not p.inv.get(item):
            self.tell(p, f"You had no {I.pretty(item)} to set down.")
            return self.set(p, "wait", left=1)  # nothing to drop: nothing lost, no need to think again
        n = min(p.inv[item], num(a.get("n"), p.inv[item], 1, 999))
        I.remove(p.inv, item, n)
        I.add(self.w.piles.setdefault(key(p.x, p.y), {}), item, n)
        return self.set(p, "wait", left=1)

    # ================= giving =================
    def near_person(self, p, a, verb):
        o = self.w.by_name(a.get("to") or a.get("target"))
        if not o or o.id == p.id:
            return None, f"{verb} whom?"
        return o, None

    def start_give(self, p, a):
        o, why = self.near_person(p, a, "give to")
        if why and not (a.get("to") or a.get("target")):
            # no one named: whoever is beside one, the most trusted first
            near = [x for x in self.w.near(p.x, p.y, 1) if x.id != p.id]
            if near:
                o, why = max(near, key=lambda x: p.rel.get(str(x.id), {}).get("trust", 0)), None
        if why:
            return why
        item = norm(a.get("item"))
        if not item and a.get("give"):
            from .society import goods
            g = goods(a.get("give"))            # written as a list of goods: give the first, as many as named
            if g:
                item = next(iter(g))
                a = dict(a, n=g[item])
        if not item:
            foods = sorted((k for k in p.inv if I.info(k).get("food")), key=lambda k: -p.inv[k])
            if not foods:
                return "give what? (item, n)"
            item = foods[0]                     # a gift with no thing named: food, of what one has most
        if item in TAME:
            # beasts from one's pen, led into theirs: young for a neighbour, a breeding pair for one's child
            mine, theirs = self.pen_of(p, item), self.pen_of(o, room=True)
            if not mine:
                return f"you keep no {item} in a pen of yours"
            if not theirs:
                return f"{o.name} has no pen with room for a {item}"
            return self.set_kw(p, {"do": "give", "to": o.id, "item": item, "n": num(a.get("n"), 1, 1, 8), "beasts": True})
        if not p.inv.get(item):
            self.tell(p, f"You had no {I.pretty(item)} to give {o.name}.")
            return self.set(p, "wait", left=1)
        return self.set_kw(p, {"do": "give", "to": o.id, "item": item, "n": num(a.get("n"), 1, 1, 999)})

    def pen_of(self, p, kind=None, room=False):
        """A pen of p's (or p's partner's): holding kind, or with room for more."""
        for b in self.w.buildings.values():
            if b.done and b.owner in (p.id, p.partner) and "pen" in BUILDINGS[b.kind]["roles"]:
                cap = BUILDINGS[b.kind]["roles"]["pen"]["capacity"]
                if (kind and b.animals.get(kind)) or (room and sum(b.animals.values()) < cap):
                    return b
        return None

    def set_kw(self, p, act):
        p.act = act
        return True

    def chase(self, p, a, o):
        """Walk toward someone who may be moving; True while not yet beside them."""
        if dist(p.x, p.y, o.x, o.y) <= 1:
            return False
        if not a.get("path") or a.get("dest", [0, 0])[:2] != [o.x, o.y]:
            if not self.walk(p, a, o.x, o.y, True):
                return None
        self.step_along(p, a)
        a["tries"] = a.get("tries", 0) + 1
        return a["tries"] < 24

    def do_give(self, p, a):
        w = self.w
        o = w.people.get(a["to"])
        if not o or not o.alive:
            return "fail", "They are gone."
        c = self.chase(p, a, o)
        if c:
            return "go", ""
        if c is None or dist(p.x, p.y, o.x, o.y) > 1:
            return "fail", f"You could not reach {o.name}."
        if a.get("beasts"):
            mine, theirs = self.pen_of(p, a["item"]), self.pen_of(o, room=True)
            if not mine or not theirs:
                return "fail", "There was no beast to give, or no room for it."
            cap = BUILDINGS[theirs.kind]["roles"]["pen"]["capacity"]
            n = min(a["n"], mine.animals[a["item"]], cap - sum(theirs.animals.values()))
            mine.animals[a["item"]] -= n
            mine.animals = {k: v for k, v in mine.animals.items() if v > 0}
            theirs.animals[a["item"]] = theirs.animals.get(a["item"], 0) + n
            self.tell(o, f"{p.name} gave you {n} {a['item']}, now in your pen at ({theirs.x},{theirs.y}).")
            self.wake(o, f"{p.name} gave you beasts")
            self.trust(o, p, 0.1 + 0.05 * n, ("gift_in", f"{p.name} gave you {n} {a['item']}"))
            self.trust(p, o, 0.02, ("gift_out", f"you gave {o.name} {n} {a['item']}"))
            self.event("give", f"{p.name} gave {o.name} {n} {a['item']}", p, o, item=a["item"], qty=n)
            return "done", f"You gave {o.name} {n} {a['item']}."
        n = min(a["n"], p.inv.get(a["item"], 0))
        if n <= 0:
            return "fail", "You no longer have it."
        I.remove(p.inv, a["item"], n)
        I.add(o.inv, a["item"], n)
        self.tell(o, f"{p.name} gave you {n} {I.pretty(a['item'])}.")
        self.wake(o, f"{p.name} gave you something")
        self.trust(o, p, 0.05 + 0.02 * min(10, n * I.info(a["item"])["worth"]), ("gift_in", f"{p.name} gave you {n} {a['item']}"))
        self.trust(p, o, 0.02, ("gift_out", f"you gave {o.name} {n} {a['item']}"))
        self.event("give", f"{p.name} gave {o.name} {n} {I.pretty(a['item'])}", p, o, item=a["item"], qty=n)
        # what was promised, handed over, counts toward the promise
        left = n
        for pr in w.promises:
            if left <= 0:
                break
            if not pr["done"] and pr["by"] == p.id and pr["to"] == o.id and pr["goods"].get(a["item"]):
                paid = min(left, pr["goods"][a["item"]])
                pr["goods"][a["item"]] -= paid
                left -= paid
                pr["goods"] = {k: q for k, q in pr["goods"].items() if q > 0}
                if not pr["goods"]:
                    pr["done"] = True
                    self.trust(o, p, 0.2, ("kept", f"{p.name} kept a promise"))
                    self.tell(o, f"{p.name} kept their promise.")
                    self.event("promise_kept", f"{p.name} kept a promise to {o.name}", p, o)
        return "done", f"You gave {o.name} {n} {I.pretty(a['item'])}."

    # ================= animals =================
    def start_tame(self, p, a):
        kind = norm(a.get("animal") or a.get("item"))
        wild = {k: v for k, v in WILD.items() if v.get("tame")}
        if kind in TAME:
            kind = next((k for k, v in wild.items() if v["tame"][0] == kind), kind)
        if kind not in wild:
            return "one can tame: " + ", ".join(v["name"] for v in wild.values())
        tame_as, need = wild[kind]["tame"]
        craft = "horsemanship" if tame_as == "horse" else "herding"
        why = self.can_try(p, craft)
        if why:
            return why
        if not p.inv.get("rope"):
            # the makings of one in hand: twist the rope first, then go after them
            if not a.get("roped") and not self.can_try(p, "cordage") and (p.inv.get("fibre", 0) >= 3 or p.inv.get("reeds", 0) >= 3):
                if p.intent is not None:
                    p.intent.setdefault("plan", []).insert(0, dict(a, roped=True))
                return self.start_craft(p, {"item": "rope", "n": 1})
            return "you need a rope to lead an animal home (rope: 3 fibre or reeds, cordage)"
        pen = self.building_near(p, lambda b: "pen" in BUILDINGS[b.kind]["roles"] and b.owner == p.id and
                                 sum(b.animals.values()) < BUILDINGS[b.kind]["roles"]["pen"]["capacity"], r=30)
        if not pen:
            return "you have no pen with room (build a pen)"
        herds = self.herds_of(p, kind)
        if not herds:
            # none in sight or remembered: cast about for tracks, as a hunter does
            herds = sorted((h for h in self.w.herds if h["n"] > 0 and h["kind"] == kind and dist(p.x, p.y, h["x"], h["y"]) <= 20),
                           key=lambda h: dist(p.x, p.y, h["x"], h["y"]))
            if herds:
                self.tell(p, f"You found the tracks of {wild[kind]['name']} {direction(p.x, p.y, herds[0]['x'], herds[0]['y'])}.")
        if not herds:
            rest = [h for h in self.w.herds if h["n"] > 0 and h["kind"] == kind]
            if not rest:
                return f"you know of no {wild[kind]['name']} anywhere: tame another kind, or get young from someone's pen"
            h = min(rest, key=lambda h: dist(p.x, p.y, h["x"], h["y"]))
            return (f"you know of no {wild[kind]['name']} nearby: the nearest are about {dist(p.x, p.y, h['x'], h['y'])} steps "
                    f"{direction(p.x, p.y, h['x'], h['y'])}, where people are few (go there, then tame)")
        return self.set(p, "tame", herd=herds[0]["id"], pen=pen.id, as_=tame_as, craft=craft, left=10)

    def do_tame(self, p, a):
        w = self.w
        h = next((h for h in w.herds if h["id"] == a["herd"] and h["n"] > 0), None)
        if not h:
            return "done", "The herd is gone."
        if dist(p.x, p.y, h["x"], h["y"]) > 1:
            if not a.get("path") or a.get("dest", [0, 0])[:2] != [h["x"], h["y"]]:
                if not self.walk(p, a, h["x"], h["y"], True):
                    return "fail", "You cannot reach them."
            self.step_along(p, a)
            a["walk"] = a.get("walk", 0) + 1
            return ("go", "") if a["walk"] < 30 else ("done", "They kept away from you.")
        a["left"] -= 1
        s = p.skill(a["craft"])
        if w.rng.random() < 0.15 + 0.35 * s - 0.03 * WILD[h["kind"]].get("fierce", 0):
            pen = w.buildings.get(a["pen"])
            if not pen:
                return "fail", "Your pen is gone."
            h["n"] -= 1
            I.remove(p.inv, "rope", 1)
            pen.animals[a["as_"]] = pen.animals.get(a["as_"], 0) + 1
            self.practise(p, a["craft"], 0.06 * (1 - s))
            self.event("tame", f"{p.name} tamed a {a['as_']} and led it to their pen", p, animal=a["as_"])
            return "done", f"You tamed a {a['as_']}; it is in your pen at ({pen.x},{pen.y})."
        self.practise(p, a["craft"], 0.02 * (1 - s))
        return ("go", "") if a["left"] > 0 else ("done", "The animals would not be led.")

    def start_slaughter(self, p, a):
        kind = norm(a.get("animal") or a.get("item"))
        pen = self.target_building(p, a, lambda b: b.animals.get(kind) and b.owner == p.id)
        if not pen:
            if kind in WILD:                        # a wild beast is not slaughtered but hunted
                return self.start_hunt(p, {"animal": kind, "keep": a.get("keep")})
            kept = sorted({k for b in self.w.buildings.values() if b.owner == p.id for k, n in b.animals.items() if n > 0})
            return f"you keep no {kind}" + (f" (you keep {', '.join(kept)})" if kept else " (wild beasts are hunted; tame ones kept in a pen)")
        act = {"do": "slaughter", "bid": pen.id, "kind": kind}
        if dist(p.x, p.y, pen.x, pen.y) > 1 and not self.walk(p, act, pen.x, pen.y, True):
            return "there is no way to the pen"
        p.act = act
        return True

    def do_slaughter(self, p, a):
        wk = self.walking(p, a)
        if wk:
            return ("fail", "The way was blocked.") if wk == "fail" else ("go", "")
        pen = self.w.buildings.get(a["bid"])
        if not pen or not pen.animals.get(a["kind"]):
            return "fail", "It is not there."
        pen.animals[a["kind"]] -= 1
        meat = TAME[a["kind"]]["meat"] + int(self.use_tool(p, "butcher") - 1)
        I.add(p.inv, "meat", meat)
        I.add(p.inv, "hide", 1)
        I.add(p.inv, "bone", 1)
        pen.animals = {k: v for k, v in pen.animals.items() if v > 0}
        return "done", f"You slaughtered a {a['kind']}: {meat} meat, a hide and a bone."

    # ================= knowledge =================
    def start_teach(self, p, a):
        o, why = self.near_person(p, a, "teach")
        if why:
            return why
        craft = norm(a.get("craft") or a.get("item"))
        if craft not in CRAFTS:
            r = recipes_making(craft) if craft else []
            craft = r[0]["craft"] if r else None
        if not craft:
            return "teach which craft?"
        if p.skill(craft) < 0.3:
            return f"you are not able enough at {craft.replace('_', ' ')} to teach it"
        return self.set_kw(p, {"do": "teach", "to": o.id, "craft": craft, "left": 3})

    def do_teach(self, p, a):
        w = self.w
        o = w.people.get(a["to"])
        if not o or not o.alive:
            return "fail", "They are gone."
        c = self.chase(p, a, o)
        if c:
            return "go", ""
        if c is None or dist(p.x, p.y, o.x, o.y) > 1:
            return "fail", f"You could not reach {o.name}."
        a["left"] -= 1
        if a["left"] > 0:
            return "go", ""
        craft = a["craft"]
        to = min(0.5, p.skill(craft) - 0.2)
        before = o.skill(craft)
        if to > before:
            o.skills[craft] = round(to, 3)
        self.tell(o, f"{p.name} taught you {craft.replace('_', ' ')}: you are now {self.skill_word(o.skill(craft))} at it.")
        self.wake(o, f"{p.name} taught you")
        self.trust(o, p, 0.15, ("taught_me", f"{p.name} taught you {craft}"))
        self.trust(p, o, 0.03, ("taught", f"you taught {o.name} {craft}"))
        self.event("teach", f"{p.name} taught {o.name} {craft.replace('_', ' ')}", p, o, craft=craft)
        return "done", f"You taught {o.name} {craft.replace('_', ' ')}."

    def start_study(self, p, a):
        """Read a book on a craft (held, or in a library one may use) to learn it up to able."""
        craft = norm(a.get("craft") or a.get("item"))
        if p.skill("literacy") < 0.3:
            return "you cannot read"
        held = craft and p.inv.get("book:" + craft)
        lib = None if held else self.building_near(p, lambda b: craft in b.books, r=20)
        if not held and not lib:
            return f"you know of no book on {craft}"
        act = {"do": "study", "craft": craft, "left": 6}
        if lib and dist(p.x, p.y, lib.x, lib.y) > 1 and not self.walk(p, act, lib.x, lib.y, True):
            return "there is no way to the library"
        p.act = act
        return True

    def do_study(self, p, a):
        wk = self.walking(p, a)
        if wk:
            return ("fail", "The way was blocked.") if wk == "fail" else ("go", "")
        a["left"] -= 1
        if a["left"] > 0:
            return "go", ""
        c = a["craft"]
        if p.skill(c) < 0.3:
            p.skills[c] = round(min(0.3, p.skill(c) + 0.15), 3)
        self.practise(p, "literacy", 0.01)
        return "done", f"You read the book on {c.replace('_', ' ')}: you are {self.skill_word(p.skill(c))} at it."

    # ================= force =================
    def start_attack(self, p, a):
        o, why = self.near_person(p, a, "attack")
        if why:
            return why
        return self.set_kw(p, {"do": "attack", "to": o.id})

    def do_attack(self, p, a):
        w = self.w
        o = w.people.get(a["to"])
        if not o or not o.alive:
            return "done", "They are gone."
        reach = max(1, I.best(p.inv, "range")[0])
        if dist(p.x, p.y, o.x, o.y) > reach:
            c = self.chase(p, a, o)
            return ("go", "") if c else ("fail", f"{o.name} got away.")
        weapon = I.best(p.inv, "weapon")
        dmg = 1 + p.strength + weapon[0] + int(p.skill("fight") * 2) - I.best(o.inv, "armour")[0]
        if o.rest:
            dmg += 1
        dmg = max(1, dmg) if p.adult(w.tick) else 1
        if weapon[1]:
            self.wear_out(p, weapon[1])
        o.health -= dmg
        self.practise(p, "fight", 0.02)
        self.trust(o, p, -0.6, ("attacked", f"{p.name} attacked you"))
        self.trust(p, o, -0.2, ("attacked_them", f"you attacked {o.name}"))
        # striking one who wronged the striker, or whom the onlooker knows to have done wrong, is seen as just
        cause = self.wrong_known(p, o, 30, FIRST_HAND)
        for x in w.near(p.x, p.y, 4):
            if x.id not in (p.id, o.id):
                if self.wrong_known(x, o) or (cause and x.rel.get(str(p.id), {}).get("trust", 0) > 0):
                    self.tell(x, f"You saw {p.name} strike {o.name}, who had wronged " + ("them." if cause else "others."))
                else:
                    self.trust(x, p, -0.15, ("saw_attack", f"you saw {p.name} attack {o.name}"))
                    self.tell(x, f"You saw {p.name} attack {o.name}.")
        self.tell(o, f"{p.name} struck you (lost {dmg} health)!")
        self.wake(o, f"{p.name} attacked you")
        self.event("attack", f"{p.name} struck {o.name}", p, o, dmg=dmg)
        if o.health <= 0:
            self.die(o, "killed", by=p)
            return "done", f"You killed {o.name}."
        # the struck strike back
        if dist(p.x, p.y, o.x, o.y) <= 1 and o.health > 3:
            back = max(1, 1 + o.strength // 2 + I.best(o.inv, "weapon")[0] // 2 - I.best(p.inv, "armour")[0])
            p.health -= back
            self.tell(p, f"{o.name} struck back (you lost {back} health).")
            if p.health <= 0:
                self.die(p, "killed", by=o)
        return "done", f"You struck {o.name} ({dmg})."

    def start_follow(self, p, a):
        o, why = self.near_person(p, a, "follow")
        if why:
            return why
        return self.set_kw(p, {"do": "follow", "to": o.id, "left": num(a.get("hours"), 6, 1, 24)})

    def do_follow(self, p, a):
        o = self.w.people.get(a["to"])
        if not o or not o.alive:
            return "done", "They are gone."
        a["left"] -= 1
        if dist(p.x, p.y, o.x, o.y) > 1:
            self.chase(p, a, o)
            a["tries"] = 0
        return ("go", "") if a["left"] > 0 else ("done", "")

    # ================= marks, places, rites =================
    def start_mark(self, p, a):
        text = str(a.get("text") or "").strip()[:200]
        if not text:
            return "a sign needs words"
        self.w.signs.setdefault(key(p.x, p.y), []).append([p.id, text, self.w.tick, False])
        self.event("sign", f"{p.name} left a sign: \"{text}\"", p, said=text)
        return self.set(p, "wait", left=1)

    def start_name_place(self, p, a):
        name = " ".join(str(a.get("name") or "").split())[:30]
        if len(name) < 2:
            return "give the place a name"
        self.w.places.append([p.x, p.y, name, p.id, self.w.tick])
        self.event("place", f"{p.name} named the place at ({p.x},{p.y}) {name}", p, name=name)
        return self.set(p, "wait", left=1)

    def start_bury(self, p, a):
        return "no one lies here to bury" if not a else self.set(p, "wait", left=3)

    def start_do(self, p, a):
        text = str(a.get("text") or a.get("act") or a.get("value") or "").strip()[:200]
        if not text:
            return self.set(p, "wait", left=num(a.get("hours"), 1, 1, 6))   # a deed of no words: a pause
        self.see(p.x, p.y, f"{p.name}: {text}", exclude={p.id})
        self.event("deed", f"{p.name}: {text}", p, said=text)
        return self.set(p, "wait", left=num(a.get("hours"), 1, 1, 6))
