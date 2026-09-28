"""Rule-based minds: for tuning the world, as baselines, and as a fallback."""
from .. import items as I
from ..world import unkey, dist
from ..prompt import visible


def food_count(inv):
    return sum(n * I.ITEMS[k]["food"] for k, n in inv.items())


class SimpleBot:
    """Forage, eat, rest. Hunts when another hunter is waiting. Never social."""
    name = "simple"

    def __init__(self, engine):
        self.e = engine
        self.known = {}     # agent id -> set of bush keys seen (bots remember places)

    def decide(self, agents):
        return {a.id: self.one(a) for a in agents}

    def one(self, a):
        e, w = self.e, self.e.w
        cfg = e.cfg["agent"]
        people, things = visible(e, a)
        mem = self.known.setdefault(a.id, set())
        for kind, x, y, obj in things:
            if kind == "bush":
                mem.add((x, y))
        food = [k for k in a.inventory if I.ITEMS[k]["food"] > 0]
        eat = None
        if a.satiety <= cfg["max_satiety"] - 5 and food:
            eat = {"item": max(food, key=lambda k: I.ITEMS[k]["spoil"])}
        d = self.choose(a, people, things, mem)
        if eat:
            d["eat"] = eat
        return d

    def choose(self, a, people, things, mem):
        e, w = self.e, self.e.w
        if a.health <= 5 and a.satiety > 6:
            return {"action": {"verb": "rest", "qty": 4}}
        if w.is_night() and food_count(a.inventory) >= 4:
            return {"action": {"verb": "rest", "qty": 3}}
        # join a hunt already under way
        for kind, x, y, obj in things:
            if kind == "herd":
                ready = [o for o in w.living() if o.activity and o.activity["verb"] == "hunt"
                         and o.activity.get("herd") == obj["id"] and o.id != a.id]
                if ready or self.wants_hunt(a, people, obj):
                    if dist(a.x, a.y, x, y) <= 1:
                        return {"action": {"verb": "hunt", "qty": 6}}
                    return {"action": {"verb": "go", "x": x, "y": y}, "plan": [{"verb": "hunt", "qty": 6}]}
        # grain from a ripe farm, then berries
        for kind, x, y, obj in things:
            if kind == "structure" and obj.kind == "farm" and obj.inventory.get("grain"):
                return self.goto_then(a, x, y, {"verb": "gather", "item": "grain", "qty": 4})
        want = 16 if self.e.w.season() in ("autumn", "winter") else 8
        if food_count(a.inventory) < want:
            for kind, x, y, obj in things:
                if kind == "bush" and obj["b"] > 0:
                    return self.goto_then(a, x, y, {"verb": "gather", "item": "berries", "qty": 6})
            if e.near_water(a):
                return {"action": {"verb": "fish", "qty": 4}}
            for kind, x, y, obj in things:
                if kind == "pile" and any(I.ITEMS[k]["food"] for k in obj):
                    it = next(k for k in obj if I.ITEMS[k]["food"])
                    if dist(a.x, a.y, x, y) <= 1:
                        return {"action": {"verb": "take", "target": "ground", "item": it, "qty": 20, "x": x, "y": y}}
                    return {"action": {"verb": "go", "x": x, "y": y}}
        if food_count(a.inventory) < want:
            far = [(x, y) for (x, y) in mem if dist(a.x, a.y, x, y) > w.sight(a)
                   and w.bushes.get(f"{x},{y}", {}).get("b", 0) > 0 or False]
            mem -= {(x, y) for (x, y) in mem if f"{x},{y}" not in w.bushes}
            if far and w.rng.random() < 0.8:
                x, y = min(far, key=lambda c: dist(a.x, a.y, *c))
                return {"action": {"verb": "go", "x": x, "y": y}}
        if food_count(a.inventory) < 4:
            water = self.find_water(a)
            if water:
                return {"action": {"verb": "go", "x": water[0], "y": water[1]}, "plan": [{"verb": "fish", "qty": 6}]}
        return self.wander(a)

    def find_water(self, a):
        w = self.e.w
        r = w.sight(a)
        best = None
        for y in range(a.y - r, a.y + r + 1):
            for x in range(a.x - r, a.x + r + 1):
                if w.in_bounds(x, y) and w.t(x, y) in (".", "T", ",") and any(
                        w.in_bounds(x + dx, y + dy) and w.t(x + dx, y + dy) == "~" for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
                    if best is None or dist(a.x, a.y, x, y) < dist(a.x, a.y, *best):
                        best = (x, y)
        return best

    def wants_hunt(self, a, people, herd):
        return any(dist(o.x, o.y, herd["x"], herd["y"]) <= 4 for o in people)

    def goto_then(self, a, x, y, step):
        if dist(a.x, a.y, x, y) <= 1:
            return {"action": step}
        return {"action": {"verb": "go", "x": x, "y": y}, "plan": [step]}

    def wander(self, a):
        rng = self.e.w.rng
        d = rng.choice(["north", "south", "east", "west", "northeast", "northwest", "southeast", "southwest"])
        return {"action": {"verb": "go", "dir": d, "qty": rng.randint(2, 5)}}


class ReciprocityBot(SimpleBot):
    """Tit-for-tat on the ledger: shares surplus with those who gave, strikes back at attackers,
    calls neighbours to hunts, and has children when well fed."""
    name = "reciprocity"

    def one(self, a):
        e, w = self.e, self.e.w
        people, _ = visible(e, a)
        adj = [o for o in people if dist(a.x, a.y, o.x, o.y) <= 1]
        score = {}
        for t, oid, kind, _ in a.ledger:
            if oid is None:
                continue
            s = {"gift_in": 1, "hunt": 1, "kept": 2, "taught_me": 1, "attacked": -3, "robbed": -2, "broke": -2}.get(kind, 0)
            score[oid] = score.get(oid, 0) + s
        for p in w.proposals.values():
            if p["to"] == a.id:
                if p["kind"] == "child":
                    ok = a.satiety >= e.cfg["agent"]["child_min_satiety"] and score.get(p["from"], 0) >= 0
                    return {"action": {"verb": "accept" if ok else "refuse", "id": p["id"]}}
                fair = sum(p["give"].values()) + sum(p["pg"].values()) >= sum(p["get"].values()) + sum(p["pr"].values())
                return {"action": {"verb": "accept" if fair and score.get(p["from"], 0) >= 0 else "refuse", "id": p["id"]}}
        for t, oid, kind, _ in reversed(a.ledger[-5:]):
            if kind == "attacked" and w.tick - t < 3:
                o = w.agents.get(oid)
                if o and o.alive and dist(a.x, a.y, o.x, o.y) <= 2 and a.health > 4:
                    return {"action": {"verb": "attack", "target": o.name}}
        food = food_count(a.inventory)
        for o in adj:
            if score.get(o.id, 0) > 0 and food > 12 and e.hunger_word(o) in ("hungry", "very hungry", "starving"):
                it = max((k for k in a.inventory if I.ITEMS[k]["food"]), key=lambda k: I.ITEMS[k]["spoil"])
                return {"action": {"verb": "give", "target": o.name, "item": it, "qty": 2}}
        if (a.age >= e.cfg["agent"]["adult_ticks"] and a.satiety >= 16 and not a.pregnant
                and w.rng.random() < 0.05):
            for o in adj:
                if o.age >= e.cfg["agent"]["adult_ticks"] and score.get(o.id, 0) >= 1:
                    return {"action": {"verb": "ask_child", "target": o.name, "name": ""}}
        d = super().one(a)
        if d["action"]["verb"] in ("go", "hunt") and d.get("plan") and d["plan"][0]["verb"] == "hunt":
            d["speech"] = {"text": "Herd nearby. Hunt with me?"}
        return d


class PlannerBot(ReciprocityBot):
    """Looks ahead: keeps a store and fills it in summer and autumn, farms rich soil,
    smokes surplus meat and fish at a fire so it keeps, eats from the store in winter,
    and pledges itself to someone it trusts. The careful end of the bot population,
    and the one that exercises storing, farming and smoking."""
    name = "planner"

    def one(self, a):
        e, w = self.e, self.e.w
        if a.partner is None and a.age >= e.cfg["agent"]["adult_ticks"] and w.rng.random() < 0.03:
            people, _ = visible(e, a)
            trusted = [o for o in people if dist(a.x, a.y, o.x, o.y) <= 1 and o.partner is None
                       and sum(1 for _, oid, k, _ in a.ledger if oid == o.id and k in ("gift_in", "hunt", "kept")) >= 2]
            if trusted:
                return {"action": {"verb": "pledge", "target": trusted[0].name}}
        return super().one(a)

    def own(self, a, kind, done=True):
        return [s for s in self.e.w.structures.values() if s.owner == a.id and s.kind == kind and (s.done or not done)]

    def choose(self, a, people, things, mem):
        e, w = self.e, self.e.w
        season = w.season()
        food = food_count(a.inventory)
        stores = self.own(a, "store")
        store = min(stores, key=lambda s: dist(a.x, a.y, s.x, s.y)) if stores else None
        in_store = food_count(store.inventory) if store else 0
        if a.health <= 5 and a.satiety > 6:
            return {"action": {"verb": "rest", "qty": 4}}
        # lean times: live off the store
        if store and food < 4 and a.satiety <= 12 and in_store > 0:
            it = max((k for k in store.inventory if I.ITEMS[k]["food"] and store.inventory[k]),
                     key=lambda k: I.ITEMS[k]["spoil"])
            return {"action": {"verb": "take", "target": "store", "item": it, "qty": 6, "x": store.x, "y": store.y}}
        # one's own crop first, before anyone else takes it
        ripe = [f for f in self.own(a, "farm") if f.inventory.get("grain") and dist(a.x, a.y, f.x, f.y) <= 12]
        if ripe:
            f = min(ripe, key=lambda f: dist(a.x, a.y, f.x, f.y))
            return self.goto_then(a, f.x, f.y, {"verb": "gather", "item": "grain", "qty": 12})
        # a crop, and a place for it: seeds found, or grain kept back as seed
        if (a.inventory.get("seeds") or a.inventory.get("grain", 0) >= 3) and season != "winter":
            farms = [f for f in self.own(a, "farm") if f.planted is None and not f.inventory.get("grain")]
            if farms:
                f = farms[0]
                return self.goto_then(a, f.x, f.y, {"verb": "plant", "qty": 8,
                                                     "item": "seeds" if a.inventory.get("seeds") else "grain"})
            soil = self.fertile_spot(a)
            if soil:
                if not a.inventory.get("wood"):
                    return {"action": {"verb": "gather", "item": "wood", "qty": 1}}
                x, y = soil
                if dist(a.x, a.y, x, y) <= 1:
                    return {"action": {"verb": "build", "item": "farm", "x": x, "y": y}}
                return {"action": {"verb": "go", "x": x, "y": y}}
        # smoke what would otherwise rot
        raw = a.inventory.get("meat", 0) + a.inventory.get("fish", 0)
        if raw >= 3 and a.satiety >= 10:
            it = "meat" if a.inventory.get("meat", 0) >= a.inventory.get("fish", 0) else "fish"
            if e.burning_fire(a, w.sight(a)):
                return {"action": {"verb": "smoke", "item": it}}
            if a.inventory.get("wood", 0) >= 2:
                return {"action": {"verb": "build", "item": "fire"}, "plan": [{"verb": "smoke", "item": it}]}
            return {"action": {"verb": "gather", "item": "wood", "qty": 2}}
        # a store of one's own, filled before winter
        if not self.own(a, "store", done=False) and season in ("spring", "summer", "autumn") and a.satiety >= 12:
            if a.inventory.get("wood", 0) >= 4:
                return {"action": {"verb": "build", "item": "store"}}
            return {"action": {"verb": "gather", "item": "wood", "qty": 4 - a.inventory.get("wood", 0)}}
        keepable = [k for k in a.inventory if I.ITEMS[k]["food"] and I.ITEMS[k]["spoil"] < 1 / 500]
        if store and season in ("summer", "autumn") and keepable and food > 10:
            k = keepable[0]
            return {"action": {"verb": "put", "item": k, "qty": a.inventory[k], "x": store.x, "y": store.y}}
        return super().choose(a, people, things, mem)

    def fertile_spot(self, a):
        w = self.e.w
        r = w.sight(a)
        best = None
        for y in range(a.y - r, a.y + r + 1):
            for x in range(a.x - r, a.x + r + 1):
                if w.in_bounds(x, y) and w.t(x, y) == "," and not w.structure_at(x, y):
                    if best is None or dist(a.x, a.y, x, y) < dist(a.x, a.y, *best):
                        best = (x, y)
        return best


class RaiderBot(SimpleBot):
    """Takes rather than makes: steals food from whoever is beside it when hungry (and
    now and then when not), and when desperate breaks into a store that is not its
    own. Tests whether property and wealth can hold against the idle and the hungry."""
    name = "raider"

    def choose(self, a, people, things, mem):
        e, w = self.e, self.e.w
        hungry = a.satiety <= 8
        for o in people:
            if dist(a.x, a.y, o.x, o.y) <= 1 and food_count(o.inventory) >= 6 and (hungry or w.rng.random() < 0.15):
                return {"action": {"verb": "take", "target": o.name, "item": "food", "qty": 3}}
        if a.satiety <= 5 and food_count(a.inventory) < 2:
            for kind, x, y, obj in things:
                if (kind == "structure" and obj.kind == "store" and obj.done and not w.may_use(a, obj)
                        and food_count(obj.inventory) >= 8):
                    if dist(a.x, a.y, x, y) <= 1:
                        return {"action": {"verb": "attack", "x": x, "y": y}}
                    return {"action": {"verb": "go", "x": x, "y": y}}
                if kind == "pile" and any(I.ITEMS[k]["food"] for k in obj) and dist(a.x, a.y, x, y) <= 1:
                    it = next(k for k in obj if I.ITEMS[k]["food"])
                    return {"action": {"verb": "take", "target": "ground", "item": it, "qty": 20, "x": x, "y": y}}
        return super().choose(a, people, things, mem)


class MixedBot:
    """Each person gets one of four minds by their id: a careless forager, a tit-for-tat
    neighbour, a planner, or a raider. The spread is where inequality can come from."""
    name = "mixed"
    KINDS = ("simple", "reciprocity", "planner", "raider")

    def __init__(self, engine):
        self.e = engine
        self.bots = {"simple": SimpleBot(engine), "reciprocity": ReciprocityBot(engine), "planner": PlannerBot(engine),
                     "raider": RaiderBot(engine)}

    def kind(self, a):
        return self.KINDS[a.id % len(self.KINDS)]

    def decide(self, agents):
        return {a.id: self.one(a) for a in agents}

    def one(self, a):
        return self.bots[self.kind(a)].one(a)
