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
        self.told = set()   # (teller, wrongdoer, when): wrongs already told

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
        d = self.serve(a, people) or self.market(a, things) or self.choose(a, people, things, mem)
        if eat:
            d["eat"] = eat
        return d

    def market(self, a, things):
        """Spare berries turned into food that keeps, at a store in sight that trades so."""
        e, w = self.e, self.e.w
        if a.inventory.get("berries", 0) < 6 or a.satiety < 10 or w.rng.random() < 0.5:
            return None
        for kind, x, y, obj in things:
            if (kind == "structure" and obj.kind == "store" and obj.trade and obj.owner != a.id
                    and obj.trade["get"].keys() == {"berries"}
                    and all(I.ITEMS[k]["food"] and I.ITEMS[k]["spoil"] < 1 / 100 for k in obj.trade["give"])
                    and all(obj.inventory.get(k, 0) >= q for k, q in obj.trade["give"].items())):
                n = min(3, (a.inventory["berries"] - 2) // obj.trade["get"]["berries"])
                if n > 0:
                    return {"action": {"verb": "trade", "x": x, "y": y, "qty": n}}
        return None

    def serve(self, a, people):
        """In someone's service: go to the master's side when a stranger is close to them (a
        guard), and bring food beyond one's own needs to the master's store. Hungry, one feeds
        oneself first."""
        e, w = self.e, self.e.w
        svc = e.serving(a)
        if not svc or a.satiety <= 8:
            return None
        m = w.agents.get(svc["master"])
        if not m or not m.alive:
            return None
        if food_count(a.inventory) >= 16 and a.satiety >= 12:
            store = e.usable_store(a, put=True)
            if store and store.owner == m.id:
                it = max((k for k in a.inventory if I.ITEMS[k]["food"]), key=lambda k: a.inventory[k] * I.ITEMS[k]["food"])
                n = min(a.inventory[it], int((food_count(a.inventory) - 10) / I.ITEMS[it]["food"]))
                if n > 0:
                    return {"action": {"verb": "put", "item": it, "qty": n, "x": store.x, "y": store.y}}
        # a guard goes to the master's side when someone not of the master's people is close to them
        near = [o for o in w.living() if o.id not in (a.id, m.id) and dist(o.x, o.y, m.x, m.y) <= 2
                and not e.bound(o, m)]
        if m in people and near and dist(a.x, a.y, m.x, m.y) > 1:
            return {"action": {"verb": "follow", "target": m.name, "qty": 3}}
        return None

    def choose(self, a, people, things, mem):
        e, w = self.e, self.e.w
        if (a.health <= 5 or a.sick) and a.satiety > 6:
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
        d = self.act(a)
        # a fresh wrong done to one: speak of it while doing whatever one does. What hearsay
        # should change is left to the people; bots acting on it cost births and deterred no one
        w = self.e.w
        for t, oid, kind, _ in reversed(a.ledger[-12:]):
            if (kind in ("robbed", "forced", "took_crop", "killed_kin") and w.tick - t < 3 * w.tpd()
                    and (a.id, oid, t) not in self.told and not d.get("speech")):
                o = w.agents.get(oid)
                if o and o.alive and any(x.id not in (a.id, o.id) and dist(a.x, a.y, x.x, x.y) <= 6 for x in w.living()):
                    self.told.add((a.id, oid, t))                      # each wrong told once
                    d["speech"] = {"text": f"Beware {o.name}.", "of": o.name}
                    break
        return d

    def act(self, a):
        e, w = self.e, self.e.w
        people, _ = visible(e, a)
        adj = [o for o in people if dist(a.x, a.y, o.x, o.y) <= 1]
        score = {}
        for t, oid, kind, _ in a.ledger:
            if oid is None:
                continue
            s = {"gift_in": 1, "hunt": 1, "kept": 2, "taught_me": 1, "attacked": -3, "robbed": -2, "broke": -2,
                 "forced": -3, "saw_steal": -1, "saw_attack": -1, "took_crop": -2, "killed_kin": -6,
                 "saw_smash": -1, "got_building": 3}.get(kind, 0)
            score[oid] = score.get(oid, 0) + s
        for p in w.proposals.values():
            if p["to"] == a.id:
                if p["kind"] == "child":
                    ok = a.satiety >= e.cfg["agent"]["child_min_satiety"] and score.get(p["from"], 0) >= 0
                    return {"action": {"verb": "accept" if ok else "refuse", "id": p["id"]}}
                pay = sum(p["give"].values()) + sum(p["pg"].values())
                cost = sum(p["get"].values()) + sum(p["pr"].values())
                if p.get("hire"):
                    # a day's work for at least a day's berry picking, and never while already bound
                    fair = pay >= cost + p["hire"] and not e.serving(a)
                elif p.get("serve"):
                    fair = False
                else:
                    fair = pay >= cost
                return {"action": {"verb": "accept" if fair and score.get(p["from"], 0) >= 0 else "refuse", "id": p["id"]}}
        # join a group one was invited into by someone not an enemy
        for g in w.groups.values():
            if g.dissolved is None and a.id in g.invited and a.id not in g.members and score.get(g.leader, 0) >= 0:
                return {"action": {"verb": "join", "group": g.name}}
        # pay what one promised, when the one owed is at hand and the thing is in hand
        for p in w.promises:
            if not p["done"] and p["from"] == a.id and p["paid"] < p["qty"] and a.inventory.get(p["item"]):
                o = w.agents.get(p["to"])
                if o and o.alive and dist(a.x, a.y, o.x, o.y) <= 1:
                    return {"action": {"verb": "give", "target": o.name, "item": p["item"],
                                       "qty": min(p["qty"] - p["paid"], a.inventory[p["item"]])}}
        # a thief at hand: take back with one's people beside, or strike if strong enough
        for t, oid, kind, _ in reversed(a.ledger[-12:]):
            if kind in ("robbed", "forced", "saw_steal", "took_crop", "killed_kin") and w.tick - t < 3 * w.tpd():
                o = w.agents.get(oid)
                if o and o.alive and dist(a.x, a.y, o.x, o.y) <= 1 and food_count(o.inventory) > 0:
                    if e.backers(a, o):
                        return {"action": {"verb": "take", "target": o.name, "item": "food", "qty": 6}}
                    if kind == "killed_kin" and a.health > 5 and a.strength >= o.strength:
                        return {"action": {"verb": "attack", "target": o.name}}     # blood for blood; goods for goods
        for t, oid, kind, _ in reversed(a.ledger[-5:]):
            if kind == "attacked" and w.tick - t < 3:
                o = w.agents.get(oid)
                if o and o.alive and dist(a.x, a.y, o.x, o.y) <= 2 and a.health > 4:
                    return {"action": {"verb": "attack", "target": o.name}}
        food = food_count(a.inventory)
        # stay beside one's own when they are sick, fed enough to spare the hours
        for o in adj:
            if o.sick and not a.sick and a.satiety > 9 and (o.id == a.partner or o.id in a.children or o.id in a.parents):
                return {"action": {"verb": "rest", "qty": 2}}
        for o in adj:
            if score.get(o.id, 0) > 0 and food > 12 and e.hunger_word(o) in ("hungry", "very hungry", "starving"):
                it = max((k for k in a.inventory if I.ITEMS[k]["food"]), key=lambda k: I.ITEMS[k]["spoil"])
                return {"action": {"verb": "give", "target": o.name, "item": it, "qty": 2}}
        if (a.age >= e.cfg["agent"]["adult_ticks"] and a.satiety >= 14 and not a.pregnant
                and w.rng.random() < 0.08):
            for o in sorted(adj, key=lambda o: o.id != a.partner):          # one's partner first
                if o.age >= e.cfg["agent"]["adult_ticks"] and not o.pregnant and (o.id == a.partner or score.get(o.id, 0) >= 1):
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

    def social(self, a):
        """Households, teaching, trade and credit: the ways a careful person builds more
        than a full store. Returns a decision, or None."""
        e, w = self.e, self.e.w
        people, _ = visible(e, a)
        adj = [o for o in people if dist(a.x, a.y, o.x, o.y) <= 1]
        kin = [c for c in a.children if w.agents[c].alive] + ([a.partner] if a.partner is not None else [])
        # a household: found it once there is kin, invite them, open the store to it
        mine = [w.groups[g] for g in a.groups if g in w.groups and w.groups[g].leader == a.id]
        if kin and not a.groups and w.rng.random() < 0.2:
            return {"action": {"verb": "found_group", "name": f"House of {a.name}",
                               "text": "We share one store and stand together."}}
        for g in mine:
            for o in people:
                if o.id in kin and o.id not in g.members and o.id not in g.invited:
                    return {"action": {"verb": "invite", "target": o.name, "group": g.name}}
            for s in self.own(a, "store") + self.own(a, "farm"):
                if s.access != f"group:{g.id}" and len(g.members) > 1 and dist(a.x, a.y, s.x, s.y) <= 1:
                    return {"action": {"verb": "set_access", "x": s.x, "y": s.y, "text": g.name}}
        # name an heir once there is kin to inherit
        if kin and a.heir is None and any(s.owner == a.id for s in w.structures.values()):
            eldest = min(kin, key=lambda i: w.agents[i].born)
            return {"action": {"verb": "bequeath", "target": w.agents[eldest].name}}
        # teach one's partner and children what one knows
        for o in adj:
            if o.id in kin:
                t = next((t for t in a.know if t not in o.know), None)
                if t:
                    return {"action": {"verb": "teach", "target": o.name, "text": t}}
                rk = next((k for k in a.recipes if k not in o.recipes), None)
                if rk:
                    return {"action": {"verb": "teach", "target": o.name, "item": w.recipes[rk]}}
        # more food than one can eat: take someone into one's service for a few days, paid in food
        if not e.servants(a) and w.rng.random() < 0.15 and not any(p["from"] == a.id for p in w.proposals.values()):
            stock = dict(a.inventory)
            for s in self.own(a, "store"):
                for k, n in s.inventory.items():
                    stock[k] = stock.get(k, 0) + n
            if food_count(stock) >= 30:
                it = max((k for k in a.inventory if I.ITEMS[k]["food"] and I.ITEMS[k]["spoil"] < 1 / 100),
                         key=lambda k: a.inventory[k], default=None)
                hands = [o for o in people if dist(a.x, a.y, o.x, o.y) <= 5 and not e.serving(o) and o.id != a.partner
                         and not e.servants(o)]
                if it and a.inventory[it] >= 4 and hands:
                    o = min(hands, key=lambda o: dist(a.x, a.y, o.x, o.y))
                    days = 3
                    return {"action": {"verb": "propose", "target": o.name, "hire_days": days,
                                       "promise_give": [{"item": it, "qty": max(days, round(2 * days / I.ITEMS[it]["food"]))}],
                                       "due_day": days, "text": "Work for me, and stand with me."}}
        # a standing trade at one's store: grain that keeps, for berries to eat now
        if w.season() in ("summer", "autumn"):
            for st in self.own(a, "store"):
                if not st.trade and st.inventory.get("grain", 0) >= 12 and dist(a.x, a.y, st.x, st.y) <= 1:
                    return {"action": {"verb": "post", "x": st.x, "y": st.y, "give": [{"item": "grain", "qty": 1}],
                                       "get": [{"item": "berries", "qty": 3}]}}
        # a token of one's household, made from spare bone: things that mean what people make of them
        spare = next((m for m in ("bone", "stone", "wood") if a.inventory.get(m, 0) >= 3), None)
        if spare and w.rng.random() < 0.1:
            return {"action": {"verb": "make", "name": f"{a.name} token", "text": f"a {spare} token with a mark",
                               "item": spare, "qty": 1}}
        # trade surplus grain for meat or fish
        if a.inventory.get("grain", 0) >= 10 and w.rng.random() < 0.3:
            for o in adj:
                want = next((k for k in ("meat", "fish", "smoked_meat") if o.inventory.get(k, 0) >= 2), None)
                if want and not any(p["from"] == a.id for p in w.proposals.values()):
                    return {"action": {"verb": "propose", "target": o.name, "give": [{"item": "grain", "qty": 3}],
                                       "get": [{"item": want, "qty": 1}]}}
        # in want, borrow against a promise
        if a.satiety <= 6 and food_count(a.inventory) < 2 and w.rng.random() < 0.5:
            for o in adj:
                it = next((k for k in o.inventory if I.ITEMS[k]["food"] and o.inventory[k] >= 6), None)
                if it and not any(p["from"] == a.id for p in w.proposals.values()):
                    return {"action": {"verb": "propose", "target": o.name, "get": [{"item": it, "qty": 2}],
                                       "promise_give": [{"item": it, "qty": 3}], "due_day": 4}}
        return None

    def one(self, a):
        e, w = self.e, self.e.w
        if w.rng.random() < 0.5:
            d = self.social(a)
            if d:
                return d
        if a.partner is None and a.age >= e.cfg["agent"]["adult_ticks"] and w.rng.random() < 0.03:
            people, _ = visible(e, a)
            trusted = [o for o in people if dist(a.x, a.y, o.x, o.y) <= 1 and o.partner is None
                       and sum(1 for _, oid, k, _ in a.ledger if oid == o.id and k in ("gift_in", "hunt", "kept")) >= 1]
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
            empty = [t for k, x, y, t in things if k == "structure" and t.kind == "store" and e.abandoned(t)]
            if empty and a.inventory.get("wood"):
                t = empty[0]
                if (a.x, a.y) == (t.x, t.y) or dist(a.x, a.y, t.x, t.y) <= 1:
                    return {"action": {"verb": "build", "item": "store", "x": t.x, "y": t.y}}
                return {"action": {"verb": "go", "x": t.x, "y": t.y}}
            if a.inventory.get("wood", 0) >= 4:
                return {"action": {"verb": "build", "item": "store"}}
            return {"action": {"verb": "gather", "item": "wood", "qty": 4 - a.inventory.get("wood", 0)}}
        # hides and bones left where a deer fell: worth picking up to make things
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                pile = w.piles.get(f"{a.x + dx},{a.y + dy}") or {}
                got = [k for k in ("hide", "bone") if pile.get(k)]
                if got and a.carrying() + 1 < a.capacity(e.cfg) and a.satiety >= 8:
                    return {"action": {"verb": "take", "target": "ground", "item": got[0], "qty": 2}}
        # dressed for winter: make warm clothes one knows how to make, from what one holds
        if season in ("summer", "autumn") and a.satiety >= 12 and I.warmth(a.inventory) < 3:
            for rk in a.recipes:
                prod = w.recipes.get(rk)
                if prod in I.WEAR and I.WEAR[prod][1] and not a.inventory.get(prod):
                    x, y = rk.split("+")
                    need = {x: 2} if x == y else {x: 1, y: 1}
                    if all(a.inventory.get(k, 0) >= n for k, n in need.items()):
                        return {"action": {"verb": "craft", "item": x, "item2": y}}
                    short = [k for k, n in need.items() if a.inventory.get(k, 0) < n and k in ("fibre", "wood", "stone")]
                    if short:
                        return {"action": {"verb": "gather", "item": short[0], "qty": 2}}
        # now and then, fed, try two things together to see what comes of it
        mats = sorted(k for k in a.inventory if not I.ITEMS[k]["food"] and k in ("fibre", "hide", "bone", "wood", "stone", "rope"))
        if a.satiety >= 14 and len(mats) >= 1 and w.rng.random() < 0.02:
            x, y = w.rng.choice(mats), w.rng.choice(mats)
            if I.pair(x, y) not in a.recipes and (x != y or a.inventory.get(x, 0) >= 2):
                return {"action": {"verb": "craft", "item": x, "item2": y}}
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
            # the friendless first: someone with their people beside them may take it back
            if (dist(a.x, a.y, o.x, o.y) <= 1 and food_count(o.inventory) >= 6 and (hungry or w.rng.random() < 0.15)
                    and not self.e.backers(o, a)):
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
