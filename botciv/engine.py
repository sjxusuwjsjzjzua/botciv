"""The engine: the only code that changes the world.

Minds return intents. The engine validates them against what the agent can
see and hold, turns them into activities, runs activities tick by tick, and
tells every agent involved what happened.
"""
import json

from . import items as I
from .world import (World, Group, Structure, DIRS, PASSABLE, GRASS, FOREST, FERTILE, ROCK,
                    WATER, key, unkey, dist, direction)

BUILD = {
    "store":   {"cost": {"wood": 4}, "ticks": 4, "hp": 20},
    "shelter": {"cost": {"wood": 5, "fibre": 4}, "ticks": 6, "hp": 20},
    "wall":    {"cost": {"stone": 2}, "ticks": 3, "hp": 30},
    "farm":    {"cost": {"wood": 1}, "ticks": 2, "hp": 10},
    "fire":    {"cost": {"wood": 2}, "ticks": 1, "hp": 5},
}
STORE_CAP = 60.0
MOVERS = {"go", "follow"}
SOCIAL = {"say"}
ALIASES = {"berry": "berries", "fiber": "fibre", "fibers": "fibre", "fibres": "fibre", "seed": "seeds",
           "woods": "wood", "log": "wood", "logs": "wood", "stones": "stone", "rock": "stone",
           "rocks": "stone", "cooked meat": "cooked_meat", "cookedmeat": "cooked_meat",
           "fishes": "fish", "ropes": "rope", "spears": "spear", "hides": "hide", "bones": "bone",
           "nets": "net", "pots": "pot", "baskets": "basket", "cloaks": "cloak", "snares": "snare",
           "necklaces": "necklace", "drums": "drum", "grains": "grain", "breads": "bread",
           "venison": "meat", "deer meat": "meat", "axes": "axe", "poultices": "poultice",
           "berry bush": "berries", "berry_bush": "berries", "bush": "berries", "bushes": "berries",
           "tree": "wood", "trees": "wood", "forest": "wood", "branches": "wood", "sticks": "wood",
           "grass": "fibre", "reeds": "fibre", "plant fibre": "fibre", "crop": "grain", "wheat": "grain",
           "farm": "grain", "raw meat": "meat", "deer": "meat"}
VERBS = ["continue", "go", "gather", "fish", "hunt", "eat", "rest", "wait", "craft", "build", "plant",
         "drop", "put", "take", "give", "attack", "follow", "teach", "mark", "do", "set_access",
         "found_group", "invite", "join", "leave", "expel", "call_vote", "vote",
         "propose", "accept", "refuse", "ask_child"]
PLAN_VERBS = ["go", "gather", "fish", "hunt", "eat", "rest", "wait", "craft", "build", "plant",
              "drop", "put", "take", "give", "follow"]


def norm_item(s):
    if s is None:
        return None
    s = str(s).strip().lower()
    s = ALIASES.get(s, s)
    s = s.replace(" ", "_")
    s = ALIASES.get(s, s)
    return s


def as_int(v, default=None, lo=None, hi=None):
    try:
        v = int(v)
    except (TypeError, ValueError):
        return default
    if lo is not None:
        v = max(lo, v)
    if hi is not None:
        v = min(hi, v)
    return v


def item_list(v):
    """[{item, qty}] -> {item: qty}, ignoring junk."""
    out = {}
    if isinstance(v, list):
        for e in v:
            if isinstance(e, dict):
                it = norm_item(e.get("item"))
                q = as_int(e.get("qty"), 1, 1, 99)
                if it in I.ITEMS:
                    out[it] = out.get(it, 0) + q
    return out


class Engine:
    def __init__(self, world: World, log=None):
        self.w = world
        self.cfg = world.cfg
        self.log = log
        self.ally_hits = {}     # target id -> attackers this tick
        self.in_loop = False

    # ================= events =================
    def event(self, kind, text, a=None, b=None, **data):
        w = self.w
        w.eid += 1
        ev = {"id": w.eid, "t": w.tick, "kind": kind, "text": text}
        if a is not None:
            ev["a"] = a.id if hasattr(a, "id") else a
        if b is not None:
            ev["b"] = b.id if hasattr(b, "id") else b
        ev.update(data)
        if self.log:
            self.log.write(ev)
        return w.eid

    def tell(self, agent, text):
        agent.events.append([self.w.tick, text])
        if len(agent.events) > 80:
            agent.events = agent.events[-80:]

    def can_see(self, agent, x, y):
        return dist(agent.x, agent.y, x, y) <= self.w.sight(agent)

    def witnesses(self, x, y, text, exclude=(), chance=1.0):
        seen = []
        for o in self.w.living():
            if o.id in exclude or not self.can_see(o, x, y):
                continue
            if chance < 1.0 and self.w.rng.random() >= chance:
                continue
            self.tell(o, text)
            seen.append(o.id)
        return seen

    def wake(self, agent, reason):
        if agent.alive and reason not in agent.wake:
            agent.wake.append(reason)

    def ledger(self, agent, other, kind, text):
        self.w.add_ledger(agent, other.id if other is not None else None, kind, text)

    # ================= main loop =================
    def needs_decision(self, a):
        if not a.alive:
            return False
        if a.wake:
            return True
        if a.activity is None and not a.plan:
            a.wake.append("you are not doing anything")
            return True
        if self.w.tick - a.last_decided >= self.cfg["mind"]["quiet_ticks"]:
            a.wake.append("some time has passed")
            return True
        return False

    def apply_decision(self, a, d):
        """d: dict with keys action, speech, plan, memory, beliefs, thought."""
        w = self.w
        if isinstance(d, dict) and d.get("retry"):
            # the mind could not be reached: hesitate a moment, keep what it has to hear
            a.activity = {"verb": "wait", "n": 0, "left": 1, "quiet": True}
            a.plan = []
            return
        a.last_decided = w.tick
        a.events = []
        a.wake = []
        for o in w.living():
            if o.id != a.id and self.can_see(a, o.x, o.y):
                a.seen[str(o.id)] = w.tick
        if not isinstance(d, dict):
            d = {}
        mem = d.get("memory")
        if isinstance(mem, str) and mem.strip():
            a.memory = mem.strip()[: self.cfg["agent"]["memory_chars"]]
        bel = d.get("beliefs")
        if isinstance(bel, list):
            for b in bel:
                if isinstance(b, dict) and b.get("name") and isinstance(b.get("belief"), str):
                    o = w.by_name(b["name"])
                    if o and o.id != a.id:
                        a.beliefs[o.name] = b["belief"].strip()[: self.cfg["agent"]["belief_chars"]]
        ea = d.get("eat")
        if isinstance(ea, dict) and ea.get("item"):
            self.eat_now(a, norm_item(ea.get("item")), as_int(ea.get("qty"), 99, 1, 99))
        sp = d.get("speech")
        if isinstance(sp, dict) and isinstance(sp.get("text"), str) and sp["text"].strip():
            self.speak(a, sp["text"].strip()[:400], sp.get("to"), bool(sp.get("whisper")))
        act = d.get("action") if isinstance(d.get("action"), dict) else {"verb": "wait"}
        verb = str(act.get("verb", "wait")).strip().lower()
        if verb == "continue" and (a.activity or a.plan):
            if a.activity is None and a.plan:
                self.next_plan_step(a)
            return
        plan = d.get("plan") if isinstance(d.get("plan"), list) else []
        a.plan = [p for p in plan if isinstance(p, dict) and str(p.get("verb", "")).lower() in PLAN_VERBS][:8]
        a.activity = None
        ok, msg = self.start(a, act)
        if not ok:
            self.tell(a, f"You could not {verb}: {msg}")
            self.event("fail", f"{a.name} tried to {verb} but could not: {msg}", a, verb=verb)
            a.plan = []
            a.activity = {"verb": "wait", "left": 1, "quiet": True}
            a.failures += 1
            self.wake(a, f"your last choice failed ({msg})")

    def next_plan_step(self, a):
        while a.plan:
            step = a.plan.pop(0)
            ok, msg = self.start(a, step)
            if ok:
                return True
            self.tell(a, f"Your plan stopped: could not {step.get('verb')}: {msg}")
            a.plan = []
            self.wake(a, f"your plan stopped ({msg})")
            return False
        return False

    def step_activities(self):
        w = self.w
        self.ally_hits = {}
        order = sorted(w.living(), key=lambda a: a.id)
        w.rng.shuffle(order)
        self.in_loop = True
        for phase in (0, 1):
            for a in order:
                if not a.alive or a.activity is None or a.activity.get("fresh"):
                    continue
                mover = a.activity["verb"] in MOVERS
                if (phase == 0) != mover:
                    continue
                act = a.activity
                a.resting = act["verb"] == "rest"
                status, msg = getattr(self, "do_" + act["verb"])(a, act)
                if status != "go":
                    self.finish(a, act, status, msg)
        self.resolve_hunts()
        for a in order:
            act = a.activity
            if a.alive and act and act["verb"] == "hunt" and act.get("ready"):
                if act.get("caught"):
                    self.finish(a, act, "done", act["caught"])
                elif act["left"] <= 0:
                    self.finish(a, act, "done", "You waited and hunted, but caught nothing.")
        self.in_loop = False
        for a in order:
            if a.activity:
                a.activity.pop("fresh", None)

    def finish(self, a, act, status, msg):
        a.activity = None
        a.resting = False
        if not a.alive:
            return
        if status == "fail":
            self.tell(a, msg)
            a.plan = []
            self.wake(a, msg)
            return
        if msg:
            self.tell(a, msg)
        if a.plan:
            self.next_plan_step(a)
        elif not act.get("quiet"):
            self.wake(a, f"you finished: {msg}" if msg else "you finished what you were doing")
        else:
            self.wake(a, "you are not doing anything")

    def step_world(self):
        if self.log:
            self.log.write({"t": self.w.tick, "kind": "frame",
                            "p": [[a.id, a.x, a.y, a.health, a.satiety] for a in self.w.living()]})
        self.needs()
        self.resources()
        self.structures_tick()
        self.social_tick()
        self.life_tick()
        self.perceive()
        self.w.tick += 1

    # ================= starting an action =================
    def start(self, a, act):
        verb = str(act.get("verb", "")).strip().lower()
        fn = getattr(self, "start_" + verb, None)
        if fn is None or verb not in VERBS:
            return False, f"'{verb}' is not something you can do"
        res = fn(a, act)
        if res is True or res is None:
            return True, ""
        if isinstance(res, str):
            return False, res
        return res

    def set_act(self, a, verb, **kw):
        a.activity = {"verb": verb, "n": 0, **kw}
        if self.in_loop:
            a.activity["fresh"] = True
        return True

    # ---- body ----
    def start_wait(self, a, act):
        return self.set_act(a, "wait", left=as_int(act.get("qty"), 2, 1, 12))

    def start_rest(self, a, act):
        return self.set_act(a, "rest", left=as_int(act.get("qty"), 6, 1, 12))

    def start_go(self, a, act):
        w = self.w
        tgt = w.by_name(act.get("target")) if act.get("target") else None
        if tgt and tgt.alive and tgt.id != a.id:
            if not self.can_see(a, tgt.x, tgt.y):
                return f"you cannot see {tgt.name}"
            return self.set_act(a, "go", follow=tgt.id, left=40)
        d = str(act.get("dir") or "").lower().replace("-", "").replace(" ", "")
        if d in DIRS:
            n = as_int(act.get("qty"), 1, 1, 20)
            dx, dy = DIRS[d]
            x = max(0, min(w.w - 1, a.x + dx * n))
            y = max(0, min(w.h - 1, a.y + dy * n))
        else:
            x, y = as_int(act.get("x")), as_int(act.get("y"))
            if x is None or y is None:
                return "say where: x and y, a direction, or a person"
        if not w.in_bounds(x, y):
            return f"({x},{y}) is beyond the edge of the land"
        if (x, y) == (a.x, a.y):
            return "you are already there"
        adj = not w.passable(x, y, a)
        p = w.path(a, x, y, adjacent_ok=adj)
        if p is None:
            return f"you see no way to reach ({x},{y})"
        return self.set_act(a, "go", x=x, y=y, adjacent=adj, left=60)

    def start_follow(self, a, act):
        tgt = self.w.by_name(act.get("target"))
        if not tgt or not tgt.alive or tgt.id == a.id or not self.can_see(a, tgt.x, tgt.y):
            return "you do not see them"
        return self.set_act(a, "follow", follow=tgt.id, left=as_int(act.get("qty"), 24, 1, 48))

    def gather_source(self, a, want=None):
        """Find something to gather on or next to the agent's tile."""
        w = self.w
        here = w.t(a.x, a.y)
        opts = []
        s = w.structure_at(a.x, a.y)
        for dx in (0, -1, 1):
            for dy in (0, -1, 1):
                x, y = a.x + dx, a.y + dy
                if not w.in_bounds(x, y):
                    continue
                b = w.bushes.get(key(x, y))
                if b and b["b"] > 0:
                    opts.append(("berries", x, y))
                st = w.structure_at(x, y)
                if st and st.kind == "farm" and st.done and st.inventory.get("grain"):
                    opts.append(("grain", x, y))
                t = w.t(x, y)
                if t == FOREST:
                    opts.append(("wood", x, y))
                if t == ROCK:
                    opts.append(("stone", x, y))
        if here in (GRASS, FERTILE) and not (s and s.kind == "farm"):
            opts.append(("fibre", a.x, a.y))
        if want:
            opts = [o for o in opts if o[0] == want]
        return opts[0] if opts else None

    def start_gather(self, a, act):
        want = norm_item(act.get("item"))
        if want in ("food", "any", "", None):
            want = None
        if want == "seeds":
            want = "fibre"
        qty = as_int(act.get("qty"), 0, 0, 99)
        src = self.gather_source(a, want)
        if src:
            return self.set_act(a, "gather", item=src[0], want=qty or 99, left=12)
        far = self.find_source(a, want)
        if not far:
            what = want or "anything to gather"
            return f"you see no {what} within sight"
        item, x, y, adj = far
        return self.set_act(a, "gather", item=item, want=qty or 99, left=12, walk=[x, y, adj])

    def find_source(self, a, want):
        """Nearest visible thing to gather: (item, x, y, stand_adjacent)."""
        w = self.w
        r = w.sight(a)
        best = None
        for y in range(a.y - r, a.y + r + 1):
            for x in range(a.x - r, a.x + r + 1):
                if not w.in_bounds(x, y):
                    continue
                t = w.t(x, y)
                cands = []
                b = w.bushes.get(key(x, y))
                if b and b["b"] > 0:
                    cands.append(("berries", True))
                st = w.structure_at(x, y)
                if st and st.kind == "farm" and st.done and st.inventory.get("grain"):
                    cands.append(("grain", True))
                if t == FOREST:
                    cands.append(("wood", True))
                if t == ROCK:
                    cands.append(("stone", True))
                if t in (GRASS, FERTILE) and not st:
                    cands.append(("fibre", False))
                for item, adj in cands:
                    if want and item != want:
                        continue
                    if not want and I.ITEMS[item]["food"] == 0:
                        continue
                    d = dist(a.x, a.y, x, y)
                    if best is None or d < best[0]:
                        best = (d, item, x, y, adj)
        if best is None:
            return None
        _, item, x, y, adj = best
        if w.path(a, x, y, adjacent_ok=adj) is None:
            return None
        return item, x, y, adj

    def start_fish(self, a, act):
        left = as_int(act.get("qty"), 6, 1, 12)
        if self.near_water(a):
            return self.set_act(a, "fish", left=left)
        w = self.w
        r = w.sight(a)
        spots = sorted(((dist(a.x, a.y, x, y), x, y) for y in range(a.y - r, a.y + r + 1) for x in range(a.x - r, a.x + r + 1)
                        if w.in_bounds(x, y) and w.t(x, y) == WATER), key=lambda s: s[0])
        for d, x, y in spots[:6]:
            if w.path(a, x, y, adjacent_ok=True) is not None:
                return self.set_act(a, "fish", left=left, walk=[x, y, True])
        return "you see no water you can reach"

    def herd_near(self, a, r=1):
        best = None
        for h in self.w.herds:
            if h["size"] > 0 and dist(a.x, a.y, h["x"], h["y"]) <= r:
                if best is None or dist(a.x, a.y, h["x"], h["y"]) < dist(a.x, a.y, best["x"], best["y"]):
                    best = h
        return best

    def start_hunt(self, a, act):
        h = self.herd_near(a, self.w.sight(a))
        if not h:
            return "you see no herd"
        return self.set_act(a, "hunt", herd=h["id"], left=as_int(act.get("qty"), 6, 1, 8))

    def near_water(self, a):
        w = self.w
        return any(w.in_bounds(a.x + dx, a.y + dy) and w.t(a.x + dx, a.y + dy) == WATER
                   for dx in (-1, 0, 1) for dy in (-1, 0, 1))

    def herd_near(self, a, r=1):
        best = None
        for h in self.w.herds:
            if h["size"] > 0 and dist(a.x, a.y, h["x"], h["y"]) <= r:
                if best is None or dist(a.x, a.y, h["x"], h["y"]) < dist(a.x, a.y, best["x"], best["y"]):
                    best = h
        return best

    def start_hunt(self, a, act):
        h = self.herd_near(a, 1)
        if not h:
            return "no herd is next to you; go next to one first"
        return self.set_act(a, "hunt", herd=h["id"], left=as_int(act.get("qty"), 6, 1, 8))

    def start_eat(self, a, act):
        it = norm_item(act.get("item"))
        if it in (None, "", "food", "any"):
            foods = sorted((k for k in a.inventory if I.ITEMS[k]["food"] > 0 or k == "poultice"),
                           key=lambda k: I.ITEMS[k]["spoil"], reverse=True)
            if not foods:
                return "you carry no food"
            it = foods[0]
        if it not in a.inventory:
            return f"you have no {it}"
        if I.ITEMS[it]["food"] <= 0 and it != "poultice":
            return f"{it} is not food"
        return self.set_act(a, "eat", item=it, qty=as_int(act.get("qty"), 99, 1, 99))

    def start_craft(self, a, act):
        x, y = norm_item(act.get("item")), norm_item(act.get("item2"))
        if x not in I.ITEMS or y not in I.ITEMS:
            return "name two things you carry, as item and item2"
        need = {x: 1}
        need[y] = need.get(y, 0) + 1
        for k, n in need.items():
            if a.inventory.get(k, 0) < n:
                return f"you do not have {n} {k}"
        return self.set_act(a, "craft", item=x, item2=y, left=2)

    def target_tile(self, a, act):
        x, y = as_int(act.get("x")), as_int(act.get("y"))
        if x is None or y is None:
            return a.x, a.y
        return x, y

    def start_build(self, a, act):
        w = self.w
        kind = norm_item(act.get("item") or act.get("text"))
        if kind not in BUILD:
            return f"you can build: {', '.join(BUILD)}"
        x, y = self.target_tile(a, act)
        if dist(a.x, a.y, x, y) > 1 or not w.in_bounds(x, y):
            return "you can only build on your tile or one next to it"
        if w.t(x, y) not in PASSABLE:
            return "the ground there will not take it"
        s = w.structure_at(x, y)
        if s:
            if s.kind == kind and not s.done:
                return self.set_act(a, "build", sid=s.id)
            return f"there is already a {s.kind} there"
        if kind == "farm" and w.t(x, y) != FERTILE:
            return "a farm needs rich soil"
        if kind in ("wall", "shelter") and w.agents_at(x, y) and (x, y) != (a.x, a.y):
            return "someone is standing there"
        cost = BUILD[kind]["cost"]
        for k, n in cost.items():
            if a.inventory.get(k, 0) < n:
                return f"a {kind} needs " + ", ".join(f"{n} {k}" for k, n in cost.items())
        for k, n in cost.items():
            I.remove(a.inventory, k, n)
        s = Structure(id=w.new_id(), kind=kind, x=x, y=y, owner=a.id, hp=BUILD[kind]["hp"], built=w.tick)
        w.structures[s.id] = s
        return self.set_act(a, "build", sid=s.id)

    def start_plant(self, a, act):
        w = self.w
        farm = self.adjacent_structure(a, "farm")
        if not farm:
            return "there is no finished farm on or next to your tile"
        if farm.planted is not None or farm.inventory.get("grain"):
            return "that farm is already planted"
        n = min(as_int(act.get("qty"), 4, 1, 99), self.cfg["resources"]["farm_max_seeds"], a.inventory.get("seeds", 0))
        if n <= 0:
            return "you have no seeds"
        return self.set_act(a, "plant", sid=farm.id, qty=n, left=1)

    def adjacent_structure(self, a, kind, x=None, y=None):
        w = self.w
        best = None
        for s in w.structures.values():
            if s.kind == kind and s.done and dist(a.x, a.y, s.x, s.y) <= 1:
                if x is not None and (s.x, s.y) != (x, y):
                    continue
                if best is None or (s.x, s.y) == (a.x, a.y):
                    best = s
        return best

    def start_drop(self, a, act):
        it = norm_item(act.get("item"))
        if not a.inventory.get(it):
            return f"you have no {it}"
        return self.set_act(a, "drop", item=it, qty=as_int(act.get("qty"), 1, 1, 999), left=1)

    def start_put(self, a, act):
        it = norm_item(act.get("item"))
        if not a.inventory.get(it):
            return f"you have no {it}"
        s = self.adjacent_structure(a, "store", *self.opt_xy(act))
        if not s:
            return "there is no finished store on or next to your tile"
        if not self.w.may_use(a, s):
            return "that store is closed to you"
        return self.set_act(a, "put", item=it, sid=s.id, qty=as_int(act.get("qty"), 1, 1, 999), left=1)

    def opt_xy(self, act):
        x, y = as_int(act.get("x")), as_int(act.get("y"))
        return (x, y) if x is not None and y is not None else (None, None)

    def start_take(self, a, act):
        w = self.w
        tgt = str(act.get("target") or "ground").strip().lower()
        it = norm_item(act.get("item"))
        qty = as_int(act.get("qty"), 1, 1, 999)
        other = w.by_name(tgt)
        if other and other.id != a.id:
            if not other.alive:
                return f"{other.name} is dead; take from the ground where they fell"
            if dist(a.x, a.y, other.x, other.y) > 1:
                return f"{other.name} is not next to you"
            return self.set_act(a, "steal", victim=other.id, item=it, qty=min(qty, 3), left=1)
        if tgt == "store":
            s = self.adjacent_structure(a, "store", *self.opt_xy(act))
            if not s:
                return "there is no finished store on or next to your tile"
            if not w.may_use(a, s):
                return "that store is closed to you"
            if not s.inventory.get(it):
                return f"the store holds no {it}"
            return self.set_act(a, "take", sid=s.id, item=it, qty=qty, left=1)
        # ground: own tile or adjacent pile
        x, y = self.opt_xy(act)
        spots = [(x, y)] if x is not None else [(a.x + dx, a.y + dy) for dx in (0, -1, 1) for dy in (0, -1, 1)]
        for sx, sy in spots:
            if sx is None or dist(a.x, a.y, sx, sy) > 1:
                continue
            pile = w.piles.get(key(sx, sy), {})
            if it in pile or (it == "snare" and key(sx, sy) in w.snares):
                return self.set_act(a, "pickup", x=sx, y=sy, item=it, qty=qty, left=1)
        return f"there is no {it} on the ground next to you"

    def start_give(self, a, act):
        other = self.w.by_name(act.get("target"))
        it = norm_item(act.get("item"))
        if not other or not other.alive or other.id == a.id:
            return "give to whom?"
        if dist(a.x, a.y, other.x, other.y) > 1:
            return f"{other.name} is not next to you"
        if not a.inventory.get(it):
            return f"you have no {it}"
        return self.set_act(a, "give", to=other.id, item=it, qty=as_int(act.get("qty"), 1, 1, 999), left=1)

    def start_attack(self, a, act):
        w = self.w
        other = w.by_name(act.get("target"))
        if other and other.alive and other.id != a.id:
            if dist(a.x, a.y, other.x, other.y) > 2:
                return f"{other.name} is too far away to strike"
            return self.set_act(a, "attack", victim=other.id, left=1)
        x, y = self.opt_xy(act)
        if x is not None:
            s = w.structure_at(x, y)
            if s and dist(a.x, a.y, x, y) <= 1:
                return self.set_act(a, "smash", sid=s.id, left=1)
            return "there is nothing there to break, or it is not next to you"
        return "attack whom? name a person, or give x and y of a structure"

    def start_teach(self, a, act):
        w = self.w
        other = w.by_name(act.get("target"))
        prod = norm_item(act.get("item"))
        if not other or not other.alive or dist(a.x, a.y, other.x, other.y) > 1:
            return "teach whom? they must be next to you"
        rk = next((k for k in a.recipes if w.recipes.get(k) == prod), None)
        if not rk:
            return f"you do not know how to make {prod}"
        return self.set_act(a, "teach", to=other.id, recipe=rk, left=1)

    def start_mark(self, a, act):
        text = str(act.get("text") or "").strip()
        if not text:
            return "a sign needs words"
        return self.set_act(a, "mark", text=text[:200], left=1)

    def start_do(self, a, act):
        text = str(act.get("text") or "").strip()
        if not text:
            return "say in text what you do"
        other = self.w.by_name(act.get("target")) if act.get("target") else None
        return self.set_act(a, "do", text=text[:300], to=other.id if other else None,
                            left=as_int(act.get("qty"), 1, 1, 6))

    def start_set_access(self, a, act):
        w = self.w
        x, y = self.opt_xy(act)
        cands = [s for s in w.structures.values() if s.owner == a.id and s.kind in ("store", "shelter", "wall")
                 and (dist(a.x, a.y, s.x, s.y) <= 1 if x is None else (s.x, s.y) == (x, y))]
        if not cands:
            return "you own no store, shelter or wall there"
        s = cands[0]
        text = str(act.get("text") or act.get("target") or act.get("group") or "").strip()
        low = text.lower()
        if low in ("me", "owner", "only me", "myself", "nobody"):
            s.access, s.allow = "owner", []
        elif low in ("anyone", "everyone", "all", "open"):
            s.access, s.allow = "anyone", []
        else:
            g = w.group_by_name(act.get("group") or text.replace("group", "").strip())
            if g:
                s.access, s.allow = f"group:{g.id}", []
            else:
                names = [n.strip() for n in text.replace(" and ", ",").split(",") if n.strip()]
                ids = [o.id for o in (w.by_name(n) for n in names) if o]
                if not ids:
                    return "say who may use it: me, anyone, a group name, or names"
                s.access, s.allow = "list", ids
        desc = self.access_text(s)
        self.tell(a, f"Your {s.kind} at ({s.x},{s.y}) is now open to {desc}.")
        self.event("access", f"{a.name} opened their {s.kind} at ({s.x},{s.y}) to {desc}", a, sid=s.id, access=s.access)
        return self.set_act(a, "wait", left=1, quiet=True)

    def access_text(self, s):
        w = self.w
        if s.access == "owner":
            o = w.agents.get(s.owner)
            return f"{o.name} only" if o else "no one"
        if s.access == "anyone":
            return "anyone"
        if s.access.startswith("group:"):
            g = w.groups.get(int(s.access.split(":")[1]))
            return f"members of {g.name}" if g else "no one"
        return ", ".join(w.agents[i].name for i in s.allow if i in w.agents)

    # ---- groups ----
    def start_found_group(self, a, act):
        w = self.w
        name = str(act.get("name") or act.get("group") or "").strip()[:40]
        if not name:
            return "a group needs a name"
        if w.group_by_name(name):
            return f"there is already a group called {name}"
        rules = str(act.get("text") or "").strip()[:500]
        decide = "vote" if "vote" in str(act.get("choice") or "").lower() else "leader"
        g = Group(id=w.new_id(), name=name, founder=a.id, leader=a.id, members=[a.id], rules=rules,
                  decide=decide, founded=w.tick)
        w.groups[g.id] = g
        a.groups.append(g.id)
        self.tell(a, f"You founded {name}. " + ("Members vote on decisions." if decide == "vote" else "You lead it."))
        self.event("group_found", f"{a.name} founded the group {name}. Rules: {rules}", a, group=g.id)
        self.witnesses(a.x, a.y, f"{a.name} declared a new group: {name}.", exclude={a.id})
        return self.set_act(a, "wait", left=1, quiet=True)

    def my_group(self, a, name):
        g = self.w.group_by_name(name)
        if g is None and len(a.groups) == 1 and not name:
            g = self.w.groups.get(a.groups[0])
        if g is None or a.id not in g.members:
            return None
        return g

    def start_invite(self, a, act):
        w = self.w
        g = self.my_group(a, act.get("group"))
        other = w.by_name(act.get("target"))
        if not g:
            return "you are not in that group"
        if not other or not other.alive or not self.can_see(a, other.x, other.y):
            return "you do not see them"
        if other.id in g.members:
            return f"{other.name} is already a member"
        if other.id not in g.invited:
            g.invited.append(other.id)
        self.tell(other, f"{a.name} invited you to join {g.name}. Its rules: \"{g.rules}\"")
        self.wake(other, f"{a.name} invited you to join {g.name}")
        self.tell(a, f"You invited {other.name} to {g.name}.")
        self.event("invite", f"{a.name} invited {other.name} to {g.name}", a, other, group=g.id)
        return self.set_act(a, "wait", left=1, quiet=True)

    def start_join(self, a, act):
        w = self.w
        g = w.group_by_name(act.get("group") or act.get("name") or act.get("target"))
        if not g:
            return "there is no such group"
        if a.id in g.members:
            return "you are already a member"
        if g.join != "open" and a.id not in g.invited:
            return f"you have not been invited to {g.name}"
        g.members.append(a.id)
        if a.id in g.invited:
            g.invited.remove(a.id)
        a.groups.append(g.id)
        self.tell(a, f"You joined {g.name}. Its rules: \"{g.rules}\"")
        for m in g.members:
            if m != a.id:
                self.tell(w.agents[m], f"{a.name} joined {g.name}.")
        self.event("join", f"{a.name} joined {g.name}", a, group=g.id)
        return self.set_act(a, "wait", left=1, quiet=True)

    def start_leave(self, a, act):
        g = self.my_group(a, act.get("group") or act.get("name"))
        if not g:
            return "you are not in that group"
        self.remove_member(g, a, f"{a.name} left {g.name}.")
        self.event("leave", f"{a.name} left {g.name}", a, group=g.id)
        return self.set_act(a, "wait", left=1, quiet=True)

    def remove_member(self, g, a, text):
        w = self.w
        if a.id in g.members:
            g.members.remove(a.id)
        if g.id in a.groups:
            a.groups.remove(g.id)
        self.tell(a, text)
        for m in g.members:
            self.tell(w.agents[m], text)
        if not g.members:
            g.dissolved = w.tick
            self.event("group_end", f"{g.name} has no members left and is gone", group=g.id)
        elif g.leader == a.id:
            g.leader = g.members[0]
            nl = w.agents[g.leader]
            for m in g.members:
                self.tell(w.agents[m], f"{nl.name} now leads {g.name}.")
            self.wake(nl, f"you now lead {g.name}")
            self.event("leader", f"{nl.name} now leads {g.name}", nl, group=g.id)

    def start_expel(self, a, act):
        w = self.w
        g = self.my_group(a, act.get("group"))
        other = w.by_name(act.get("target"))
        if not g:
            return "you are not in that group"
        if not other or other.id not in g.members:
            return "they are not a member"
        if g.decide == "vote":
            return "in this group members vote to expel; use call_vote"
        if g.leader != a.id:
            return f"only the leader of {g.name} can expel"
        self.remove_member(g, other, f"{a.name} expelled {other.name} from {g.name}.")
        self.wake(other, f"you were expelled from {g.name}")
        self.event("expel", f"{a.name} expelled {other.name} from {g.name}", a, other, group=g.id)
        return self.set_act(a, "wait", left=1, quiet=True)

    def start_call_vote(self, a, act):
        w = self.w
        g = self.my_group(a, act.get("group"))
        if not g:
            return "you are not in that group"
        q = str(act.get("text") or "").strip()[:300]
        kind = str(act.get("choice") or "other").lower()
        kind = kind if kind in ("expel", "leader", "rules") else "other"
        tgt = w.by_name(act.get("target"))
        if kind in ("expel", "leader") and (not tgt or tgt.id not in g.members):
            return "name the member the vote is about as target"
        if not q:
            q = {"expel": f"Expel {tgt.name}?" if tgt else "", "leader": f"Make {tgt.name} leader?" if tgt else "",
                 "rules": "Adopt new rules?"}.get(kind, "")
        if not q:
            return "a vote needs a question in text"
        vid = w.new_id()
        w.votes[vid] = {"id": vid, "group": g.id, "caller": a.id, "q": q, "kind": kind,
                        "target": tgt.id if tgt else None, "rules": q if kind == "rules" else "",
                        "closes": w.tick + w.tpd(), "yes": [a.id], "no": [], "done": False}
        for m in g.members:
            if m != a.id:
                self.tell(w.agents[m], f"{a.name} called vote #{vid} in {g.name}: \"{q}\" (answer with vote)")
                self.wake(w.agents[m], f"a vote was called in {g.name}")
        self.tell(a, f"You called vote #{vid}: \"{q}\". You voted yes.")
        self.event("vote_call", f"{a.name} called a vote in {g.name}: {q}", a, tgt, group=g.id, vote=vid)
        return self.set_act(a, "wait", left=1, quiet=True)

    def start_vote(self, a, act):
        v = self.w.votes.get(as_int(act.get("id"), -1))
        if not v or v["done"]:
            return "there is no open vote with that number"
        g = self.w.groups.get(v["group"])
        if not g or a.id not in g.members:
            return "you are not a member of that group"
        yes = "yes" in str(act.get("choice") or "").lower()
        for side in ("yes", "no"):
            if a.id in v[side]:
                v[side].remove(a.id)
        v["yes" if yes else "no"].append(a.id)
        self.tell(a, f"You voted {'yes' if yes else 'no'} on #{v['id']}.")
        return self.set_act(a, "wait", left=1, quiet=True)

    # ---- deals ----
    def start_propose(self, a, act):
        w = self.w
        other = w.by_name(act.get("target"))
        if not other or not other.alive or other.id == a.id:
            return "propose to whom?"
        if dist(a.x, a.y, other.x, other.y) > 5:
            return f"{other.name} is too far away to hear you"
        give, get = item_list(act.get("give")), item_list(act.get("get"))
        pg, pr = item_list(act.get("promise_give")), item_list(act.get("promise_get"))
        text = str(act.get("text") or "").strip()[:300]
        if not (give or get or pg or pr or text):
            return "an offer needs something in it"
        for k, n in give.items():
            if a.inventory.get(k, 0) < n:
                return f"you do not have {n} {k} to give"
        due = as_int(act.get("due_day"), 3, 1, 30)
        pid = w.new_id()
        w.proposals[pid] = {"id": pid, "kind": "deal", "from": a.id, "to": other.id, "give": give, "get": get,
                            "pg": pg, "pr": pr, "text": text, "due_days": due, "made": w.tick,
                            "expires": w.tick + 6}
        desc = self.deal_text(w.proposals[pid], other)
        self.tell(other, f"{a.name} offers you deal #{pid}: {desc}")
        self.wake(other, f"{a.name} made you an offer")
        self.tell(a, f"You offered {other.name} deal #{pid}: {self.deal_text(w.proposals[pid], a)}")
        self.event("propose", f"{a.name} offered {other.name} a deal: {self.deal_text(w.proposals[pid], None)}", a, other, deal=pid)
        return self.set_act(a, "wait", left=1, quiet=True)

    def deal_text(self, p, viewer):
        w = self.w
        A, B = w.agents[p["from"]], w.agents[p["to"]]

        def who(x):
            return "you" if viewer is not None and x.id == viewer.id else x.name
        parts = []
        if p["kind"] == "child":
            parts.append(f"{who(A)} and {who(B)} have a child together, named {p.get('name') or '(unnamed)'}")
        if p.get("give"):
            parts.append(f"{who(A)} hands over {I.describe(p['give'])} now")
        if p.get("get"):
            parts.append(f"{who(B)} hands over {I.describe(p['get'])} now")
        if p.get("pg"):
            parts.append(f"{who(A)} promise{'' if who(A) == 'you' else 's'} {I.describe(p['pg'])} within {p['due_days']} days")
        if p.get("pr"):
            parts.append(f"{who(B)} promise{'' if who(B) == 'you' else 's'} {I.describe(p['pr'])} within {p['due_days']} days")
        if p.get("text"):
            parts.append(f"terms: \"{p['text']}\"")
        return "; ".join(parts)

    def start_accept(self, a, act):
        w = self.w
        p = w.proposals.get(as_int(act.get("id"), -1))
        if not p or p["to"] != a.id:
            return "there is no offer to you with that number"
        other = w.agents[p["from"]]
        if not other.alive:
            del w.proposals[p["id"]]
            return f"{other.name} is dead"
        if p["kind"] == "child":
            return self.accept_child(a, other, p, act)
        if (p["give"] or p["get"]) and dist(a.x, a.y, other.x, other.y) > 1:
            return f"you must be next to {other.name} to exchange"
        for k, n in p["give"].items():
            if other.inventory.get(k, 0) < n:
                del w.proposals[p["id"]]
                self.tell(other, f"Deal #{p['id']} fell through: you no longer had {n} {k}.")
                return f"{other.name} no longer has {n} {k}; the deal falls through"
        for k, n in p["get"].items():
            if a.inventory.get(k, 0) < n:
                return f"you do not have {n} {k}"
        for k, n in p["give"].items():
            I.remove(other.inventory, k, n)
            I.add(a.inventory, k, n)
        for k, n in p["get"].items():
            I.remove(a.inventory, k, n)
            I.add(other.inventory, k, n)
        due = w.tick + p["due_days"] * w.tpd()
        for debtor, creditor, stuff in ((other, a, p["pg"]), (a, other, p["pr"])):
            for k, n in stuff.items():
                w.promises.append({"id": w.new_id(), "deal": p["id"], "from": debtor.id, "to": creditor.id,
                                   "item": k, "qty": n, "made": w.tick, "due": due, "paid": 0, "done": False})
        del w.proposals[p["id"]]
        text = self.deal_text(p, None)
        self.ledger(a, other, "deal", f"you accepted {other.name}'s deal: {self.deal_text(p, a)}")
        self.ledger(other, a, "deal", f"{a.name} accepted your deal: {self.deal_text(p, other)}")
        self.tell(other, f"{a.name} accepted deal #{p['id']}.")
        self.wake(other, f"{a.name} accepted your offer")
        self.tell(a, f"You accepted deal #{p['id']} from {other.name}.")
        self.event("deal", f"{a.name} accepted {other.name}'s deal: {text}", other, a, deal=p["id"],
                   give=p["give"], get=p["get"], pg=p["pg"], pr=p["pr"], terms=p["text"])
        return self.set_act(a, "wait", left=1, quiet=True)

    def start_refuse(self, a, act):
        w = self.w
        p = w.proposals.get(as_int(act.get("id"), -1))
        if not p or p["to"] != a.id:
            return "there is no offer to you with that number"
        other = w.agents[p["from"]]
        del w.proposals[p["id"]]
        self.tell(other, f"{a.name} refused your offer #{p['id']}.")
        self.wake(other, f"{a.name} refused your offer")
        self.event("refuse", f"{a.name} refused {other.name}'s offer", a, other, deal=p["id"])
        return self.set_act(a, "wait", left=1, quiet=True)

    def start_ask_child(self, a, act):
        w = self.w
        other = w.by_name(act.get("target"))
        if not other or not other.alive or other.id == a.id:
            return "ask whom?"
        if dist(a.x, a.y, other.x, other.y) > 1:
            return f"{other.name} must be next to you"
        if a.age < self.cfg["agent"]["adult_ticks"]:
            return "you are too young"
        pid = w.new_id()
        w.proposals[pid] = {"id": pid, "kind": "child", "from": a.id, "to": other.id,
                            "name": str(act.get("name") or "").strip()[:12], "teaching": str(act.get("text") or "")[:300],
                            "give": {}, "get": {}, "pg": {}, "pr": {}, "text": "", "due_days": 0,
                            "made": w.tick, "expires": w.tick + 6}
        self.tell(other, f"{a.name} asks you to have a child together (offer #{pid}). Accept or refuse.")
        self.wake(other, f"{a.name} asked you to have a child together")
        self.tell(a, f"You asked {other.name} to have a child with you (#{pid}).")
        self.event("ask_child", f"{a.name} asked {other.name} to have a child", a, other, deal=pid)
        return self.set_act(a, "wait", left=1, quiet=True)

    def accept_child(self, a, other, p, act):
        w = self.w
        c = self.cfg["agent"]
        if dist(a.x, a.y, other.x, other.y) > 1:
            return f"you must be next to {other.name}"
        if a.age < c["adult_ticks"] or other.age < c["adult_ticks"]:
            return "one of you is too young"
        if a.pregnant or other.pregnant:
            return "a child is already on the way"
        if a.satiety < c["child_min_satiety"] or other.satiety < c["child_min_satiety"]:
            return "one of you is too hungry to have a child"
        expecting = sum(1 for x in w.living() if x.pregnant)
        if len(w.living()) + expecting >= w.cfg["world"]["max_population"]:
            return "no child comes, though you try (the land is too crowded)"
        a.satiety -= c["child_cost"]
        other.satiety -= c["child_cost"]
        teach = [[other.name, p.get("teaching", "")], [a.name, str(act.get("text") or "")[:300]]]
        other.pregnant = {"due": w.tick + c["gestation_ticks"], "partner": a.id,
                          "name": p.get("name") or "", "teachings": teach}
        del w.proposals[p["id"]]
        for x, y in ((a, other), (other, a)):
            self.ledger(x, y, "child", f"you and {y.name} are having a child")
            self.tell(x, f"You and {y.name} will have a child in about {c['gestation_ticks'] // w.tpd()} days.")
        self.wake(other, f"{a.name} agreed to have a child with you")
        self.event("conceive", f"{other.name} and {a.name} are expecting a child", other, a)
        return self.set_act(a, "wait", left=1, quiet=True)

    # ---- speech ----
    def speak(self, a, text, to=None, whisper=False):
        w = self.w
        target = w.by_name(to) if to else None
        if whisper:
            if not target or dist(a.x, a.y, target.x, target.y) > 1:
                self.tell(a, "You could not whisper: they are not next to you.")
                return
            self.tell(target, f"{a.name} whispered to you: \"{text}\"")
            self.speech_wake(target, f"{a.name} whispered to you")
            self.event("whisper", f"{a.name} whispered to {target.name}: \"{text}\"", a, target, words=text)
            return
        loud = 12 if a.inventory.get("drum") else 6
        heard = []
        for o in w.living():
            if o.id == a.id or dist(a.x, a.y, o.x, o.y) > loud:
                continue
            heard.append(o.id)
            if target and o.id == target.id:
                self.tell(o, f"{a.name} said to you: \"{text}\"")
                self.speech_wake(o, f"{a.name} spoke to you")
            elif target:
                self.tell(o, f"{a.name} said to {target.name}: \"{text}\"")
            else:
                self.tell(o, f"{a.name} said: \"{text}\"")
                if dist(a.x, a.y, o.x, o.y) <= 2:
                    self.speech_wake(o, f"{a.name} spoke nearby")
        if target and target.id not in heard and target.id != a.id:
            self.tell(a, f"{target.name} is too far away to hear you.")
        self.event("say", f"{a.name} said{' to ' + target.name if target else ''}: \"{text}\"", a, target,
                   words=text, heard=heard)

    def speech_wake(self, o, reason):
        gap = self.cfg["mind"]["speech_wake_gap"]
        if self.w.tick - o.last_speech_wake >= gap and self.w.tick - o.last_decided >= 1:
            o.last_speech_wake = self.w.tick
            self.wake(o, reason)

    # ================= activities, one tick each =================
    def step_toward(self, a, tx, ty, adjacent_ok=False):
        p = self.w.path(a, tx, ty, adjacent_ok)
        if p is None:
            return False
        if p:
            a.x, a.y = p[0]
        return True

    def do_wait(self, a, act):
        act["left"] -= 1
        return ("go", "") if act["left"] > 0 else ("done", "")

    def do_rest(self, a, act):
        act["left"] -= 1
        if act["left"] <= 0:
            return "done", "You finished resting."
        return "go", ""

    def do_go(self, a, act):
        w = self.w
        act["left"] -= 1
        if "follow" in act:
            t = w.agents.get(act["follow"])
            if not t or not t.alive or not self.can_see(a, t.x, t.y):
                return "fail", "You lost sight of the one you were going to."
            if dist(a.x, a.y, t.x, t.y) <= 1:
                return "done", f"You reached {t.name}."
            if not self.step_toward(a, t.x, t.y, True):
                return "fail", f"You found no way to reach {t.name}."
            return ("done", f"You reached {t.name}.") if dist(a.x, a.y, t.x, t.y) <= 1 else ("go", "")
        tx, ty = act["x"], act["y"]
        if not self.step_toward(a, tx, ty, act.get("adjacent", False)):
            return "fail", f"Your way to ({tx},{ty}) is blocked."
        arrived = (a.x, a.y) == (tx, ty) or (act.get("adjacent") and dist(a.x, a.y, tx, ty) <= 1)
        if arrived:
            return "done", f"You arrived at ({a.x},{a.y})."
        if act["left"] <= 0:
            return "fail", "You gave up on the long walk."
        return "go", ""

    def do_follow(self, a, act):
        t = self.w.agents.get(act["follow"])
        act["left"] -= 1
        if not t or not t.alive or not self.can_see(a, t.x, t.y):
            return "fail", "You lost sight of the one you were following."
        if dist(a.x, a.y, t.x, t.y) > 1:
            self.step_toward(a, t.x, t.y, True)
        return ("go", "") if act["left"] > 0 else ("done", f"You stopped following {t.name}.")

    def room(self, a, item, n):
        free = a.capacity(self.cfg) - a.carrying()
        return max(0, min(n, int(free / I.ITEMS[item]["w"] + 1e-9)))

    def walk_first(self, a, act):
        """For activities that start with a walk. Returns None when arrived, else a status."""
        wk = act.get("walk")
        if not wk:
            return None
        x, y, adj = wk
        if (adj and dist(a.x, a.y, x, y) <= 1) or (a.x, a.y) == (x, y):
            act.pop("walk")
            return None
        act["walked"] = act.get("walked", 0) + 1
        if act["walked"] > 25 or not self.step_toward(a, x, y, adj):
            return ("fail", f"You could not get to ({x},{y}).")
        if (adj and dist(a.x, a.y, x, y) <= 1) or (a.x, a.y) == (x, y):
            act.pop("walk")
        return ("go", "")

    def do_gather(self, a, act):
        w = self.w
        r = self.cfg["resources"]
        item = act["item"]
        walking = self.walk_first(a, act)
        if walking:
            return walking
        src = self.gather_source(a, item)
        if not src:
            return "done", f"There is no more {item} here. You gathered {act.get('got', 0)}."
        _, x, y = src
        n = 1
        if item == "wood" and a.inventory.get("axe"):
            n = 2
            self.use_tool(a, "axe")
        if item == "grain":
            n = 3
        if self.w.is_night() and item != "grain":
            n = 1 if w.rng.random() < 0.5 else 0
        n = self.room(a, item, n)
        if n == 0 and self.room(a, item, 1) == 0:
            return "done", f"You cannot carry more. You gathered {act.get('got', 0)} {item}."
        if item == "berries":
            b = w.bushes[key(x, y)]
            n = min(n, b["b"])
            b["b"] -= n
            if b["b"] == 0:
                b["strips"] += 1
                if w.rng.random() < r["bush_die_chance"] * b["strips"]:
                    del w.bushes[key(x, y)]
                    self.witnesses(x, y, f"The berry bush at ({x},{y}) has been stripped too often and died.")
                    self.event("bush_dies", f"The berry bush at ({x},{y}) died from overpicking", x=x, y=y)
        elif item == "grain":
            farm = w.structure_at(x, y)
            n = min(n, farm.inventory.get("grain", 0))
            I.remove(farm.inventory, "grain", n)
            if not farm.inventory.get("grain"):
                farm.planted = None
                farm.progress = 0
                farm.seeds = 0
            if farm.owner != a.id:
                o = w.agents.get(farm.owner)
                if o and o.alive and self.can_see(o, x, y):
                    self.tell(o, f"{a.name} is harvesting grain from your farm at ({x},{y}).")
                    self.wake(o, f"{a.name} is harvesting your farm")
        elif item == "fibre":
            s = w.season()
            if s in ("summer", "autumn") and w.rng.random() < r["seed_chance"]:
                I.add(a.inventory, "seeds", 1)
                act["seeds"] = act.get("seeds", 0) + 1
        I.add(a.inventory, item, n)
        act["got"] = act.get("got", 0) + n
        act["left"] -= 1
        if act["left"] <= 0 or act["got"] >= act.get("want", 99):
            extra = f" and {act['seeds']} seeds" if act.get("seeds") else ""
            return "done", f"You gathered {act['got']} {item}{extra}."
        return "go", ""

    def do_fish(self, a, act):
        w = self.w
        r = self.cfg["resources"]
        walking = self.walk_first(a, act)
        if walking:
            return walking
        if not self.near_water(a):
            return "fail", "You are no longer by the water."
        p = r["fish_chance"]
        if a.inventory.get("net"):
            p = r["fish_chance_net"]
            self.use_tool(a, "net")
        elif a.inventory.get("spear"):
            p = r["fish_chance_spear"]
        if w.rng.random() < p and self.room(a, "fish", 1):
            I.add(a.inventory, "fish", 1)
            act["got"] = act.get("got", 0) + 1
        act["left"] -= 1
        if act["left"] <= 0:
            return "done", f"You fished and caught {act.get('got', 0)}."
        return "go", ""

    def do_hunt(self, a, act):
        w = self.w
        h = next((h for h in w.herds if h["id"] == act["herd"] and h["size"] > 0), None)
        if not h:
            return "fail", "The herd is gone."
        if dist(a.x, a.y, h["x"], h["y"]) > 1:
            act["ready"] = False
            act["walked"] = act.get("walked", 0) + 1
            if act["walked"] > 12 or not self.step_toward(a, h["x"], h["y"], True):
                return "fail", "You could not reach the herd."
            return "go", ""
        act["ready"] = True
        act["left"] -= 1
        return "go", ""

    def resolve_hunts(self):
        """After activities: each herd with ready hunters may yield an animal."""
        w = self.w
        r = self.cfg["resources"]
        for h in w.herds:
            if h["size"] <= 0:
                continue
            hunters = [a for a in w.living() if a.activity and a.activity["verb"] == "hunt"
                       and a.activity.get("herd") == h["id"] and a.activity.get("ready")
                       and dist(a.x, a.y, h["x"], h["y"]) <= 1]
            if not hunters:
                continue
            k = len(hunters)
            p = r["hunt_chance"][min(k, len(r["hunt_chance"]) - 1)]
            spears = [a for a in hunters if a.inventory.get("spear")]
            p = min(0.95, p + r["spear_bonus"] * len(spears)) if p > 0 else 0
            for a in spears:
                self.use_tool(a, "spear")
            if w.rng.random() >= p:
                continue
            h["size"] -= 1
            meat = r["hunt_meat"]
            share, rem = divmod(meat, k)
            order = sorted(hunters, key=lambda a: a.id)
            w.rng.shuffle(order)
            names = ", ".join(x.name for x in hunters)
            for i, a in enumerate(order):
                got = share + (1 if i < rem else 0)
                room = self.room(a, "meat", got)
                I.add(a.inventory, "meat", room)
                if got > room:
                    self.drop_pile(a.x, a.y, {"meat": got - room})
                a.hunts += 1
                others = [x.name for x in hunters if x.id != a.id]
                msg = f"The hunt succeeded! You got {got} meat" + (f", hunting with {', '.join(others)}." if others else ".")
                if got > room:
                    msg += f" You could not carry {got - room}; it lies on the ground."
                a.activity["caught"] = msg
                for o in hunters:
                    if o.id != a.id:
                        self.ledger(a, o, "hunt", f"hunted with {o.name} and got {got} meat")
            self.drop_pile(h["x"], h["y"], {"hide": 1, "bone": 1})
            self.event("hunt", f"{names} killed a deer ({k} hunter{'s' if k > 1 else ''})", hunters[0],
                       hunters=[x.id for x in hunters], herd=h["id"])
            self.witnesses(h["x"], h["y"], f"{names} brought down a deer.", exclude={x.id for x in hunters})

    def eat_now(self, a, item, qty):
        if item in (None, "", "food", "any"):
            foods = sorted((k for k in a.inventory if I.ITEMS[k]["food"] > 0), key=lambda k: I.ITEMS[k]["spoil"], reverse=True)
            if not foods:
                return
            item = foods[0]
        if item not in a.inventory or (I.ITEMS[item]["food"] <= 0 and item != "poultice"):
            self.tell(a, f"You could not eat {item}: you have none, or it is not food.")
            return
        status, msg = self.do_eat(a, {"item": item, "qty": qty})
        if msg:
            self.tell(a, msg)

    def do_eat(self, a, act):
        c = self.cfg["agent"]
        it = act["item"]
        info = I.ITEMS[it]
        eaten = 0
        if it == "poultice":
            if I.remove(a.inventory, it, 1):
                a.health = min(c["max_health"], a.health + 3)
                return "done", "You ate the poultice and feel better."
            return "done", ""
        while eaten < act["qty"] and a.inventory.get(it) and a.satiety + info["food"] <= c["max_satiety"] + max(0, info["food"] - 2):
            I.remove(a.inventory, it, 1)
            a.satiety = min(c["max_satiety"], a.satiety + info["food"])
            eaten += 1
        if eaten == 0:
            return "done", "You are too full to eat."
        return "done", f"You ate {eaten} {it}. {self.hunger_word(a).capitalize()}."

    def do_craft(self, a, act):
        w = self.w
        act["left"] -= 1
        if act["left"] > 0:
            return "go", ""
        x, y = act["item"], act["item2"]
        need = {x: 1}
        need[y] = need.get(y, 0) + 1
        for k, n in need.items():
            if a.inventory.get(k, 0) < n:
                return "fail", f"You no longer have {k}."
        pk = I.pair(x, y)
        prod = w.recipes.get(pk)
        if not prod:
            self.event("craft_fail", f"{a.name} tried combining {x} and {y}; nothing came of it", a, pair=pk)
            return "done", f"You worked {x} and {y} together, but nothing useful came of it. You still have both."
        for k, n in need.items():
            I.remove(a.inventory, k, n)
        I.add(a.inventory, prod, 1)
        new = pk not in a.recipes
        if new:
            a.recipes.append(pk)
        first = new and not any(pk in o.recipes for o in w.agents.values() if o.id != a.id)
        self.event("craft", f"{a.name} made a {prod} from {x} and {y}", a, item=prod, pair=pk,
                   discovery=new, first=first)
        if new:
            self.witnesses(a.x, a.y, f"{a.name} made something new: a {prod}.", exclude={a.id}, chance=0.7)
            return "done", f"You discovered how to make a {prod} from {x} and {y}! ({I.EFFECTS.get(prod, '')})"
        return "done", f"You made a {prod}."

    def do_build(self, a, act):
        w = self.w
        s = w.structures.get(act["sid"])
        if not s or dist(a.x, a.y, s.x, s.y) > 1:
            return "fail", "You are no longer at the building site."
        if s.done:
            return "done", f"The {s.kind} at ({s.x},{s.y}) is finished."
        s.progress += 1
        if s.progress >= BUILD[s.kind]["ticks"]:
            s.done = True
            if s.kind == "fire":
                s.fuel = self.cfg["resources"]["fire_ticks"]
            owner = w.agents.get(s.owner)
            self.event("build", f"{owner.name if owner else a.name} built a {s.kind} at ({s.x},{s.y})", a,
                       sid=s.id, what=s.kind, x=s.x, y=s.y, owner=s.owner)
            self.witnesses(s.x, s.y, f"A {s.kind} was finished at ({s.x},{s.y}).", exclude={a.id})
            if owner and owner.id != a.id:
                self.ledger(owner, a, "help", f"{a.name} helped build your {s.kind}")
                self.ledger(a, owner, "help", f"you helped {owner.name} build a {s.kind}")
            return "done", f"You finished the {s.kind} at ({s.x},{s.y})."
        return "go", ""

    def do_plant(self, a, act):
        w = self.w
        farm = w.structures.get(act["sid"])
        if not farm or farm.planted is not None:
            return "fail", "The farm is no longer free to plant."
        n = I.remove(a.inventory, "seeds", act["qty"])
        farm.seeds, farm.planted, farm.progress = n, w.tick, 0
        self.event("plant", f"{a.name} planted {n} seeds at ({farm.x},{farm.y})", a, sid=farm.id)
        return "done", f"You planted {n} seeds. The crop should be ripe in about {self.cfg['resources']['farm_grow_ticks'] // w.tpd()} days, if winter does not stop it."

    def drop_pile(self, x, y, stuff):
        p = self.w.piles.setdefault(key(x, y), {})
        for k, n in stuff.items():
            I.add(p, k, n)
        if not p:
            del self.w.piles[key(x, y)]

    def do_drop(self, a, act):
        w = self.w
        it = act["item"]
        n = I.remove(a.inventory, it, act["qty"])
        if not n:
            return "fail", f"You have no {it}."
        s = w.structure_at(a.x, a.y)
        if it == "wood" and s and s.kind == "fire" and s.done:
            s.fuel += 12 * n
            return "done", f"You fed {n} wood to the fire."
        if it == "snare" and w.t(a.x, a.y) in (GRASS, FOREST) and key(a.x, a.y) not in w.snares:
            w.snares[key(a.x, a.y)] = a.id
            if n > 1:
                self.drop_pile(a.x, a.y, {"snare": n - 1})
            self.event("snare", f"{a.name} set a snare at ({a.x},{a.y})", a)
            return "done", f"You set a snare at ({a.x},{a.y})."
        self.drop_pile(a.x, a.y, {it: n})
        self.event("drop", f"{a.name} left {n} {it} on the ground at ({a.x},{a.y})", a, item=it, qty=n)
        return "done", f"You put down {n} {it}."

    def do_put(self, a, act):
        w = self.w
        s = w.structures.get(act["sid"])
        if not s or dist(a.x, a.y, s.x, s.y) > 1 or not w.may_use(a, s):
            return "fail", "You cannot reach that store."
        it = act["item"]
        free = STORE_CAP - I.weight(s.inventory)
        n = min(act["qty"], a.inventory.get(it, 0), int(free / I.ITEMS[it]["w"] + 1e-9))
        if n <= 0:
            return "fail", "The store is full." if free < 1 else f"You have no {it}."
        I.remove(a.inventory, it, n)
        I.add(s.inventory, it, n)
        self.event("put", f"{a.name} put {n} {it} into the store at ({s.x},{s.y})", a, sid=s.id, item=it, qty=n,
                   owner=s.owner)
        if s.owner != a.id and s.owner in w.agents:
            self.ledger(w.agents[s.owner], a, "store_in", f"{a.name} put {n} {it} into your store")
        return "done", f"You put {n} {it} into the store."

    def do_take(self, a, act):
        w = self.w
        s = w.structures.get(act["sid"])
        if not s or dist(a.x, a.y, s.x, s.y) > 1 or not w.may_use(a, s):
            return "fail", "You cannot reach that store."
        it = act["item"]
        n = min(act["qty"], s.inventory.get(it, 0))
        n = self.room(a, it, n)
        if n <= 0:
            return "fail", f"There is no {it} in the store, or you cannot carry it."
        I.remove(s.inventory, it, n)
        I.add(a.inventory, it, n)
        self.event("take_store", f"{a.name} took {n} {it} from the store at ({s.x},{s.y})", a, sid=s.id, item=it,
                   qty=n, owner=s.owner)
        owner = w.agents.get(s.owner)
        if owner and owner.id != a.id and owner.alive:
            self.ledger(owner, a, "store_out", f"{a.name} took {n} {it} from your store at ({s.x},{s.y})")
            if self.can_see(owner, s.x, s.y):
                self.tell(owner, f"{a.name} took {n} {it} from your store.")
        self.witnesses(s.x, s.y, f"{a.name} took {it} from the store at ({s.x},{s.y}).", exclude={a.id}, chance=0.5)
        return "done", f"You took {n} {it} from the store."

    def do_pickup(self, a, act):
        w = self.w
        k = key(act["x"], act["y"])
        it = act["item"]
        if it == "snare" and k in w.snares:
            owner = w.snares.pop(k)
            I.add(a.inventory, "snare", 1)
            if owner != a.id and owner in w.agents:
                self.event("take_snare", f"{a.name} took {w.agents[owner].name}'s snare", a, owner, x=act["x"], y=act["y"])
            return "done", "You picked up the snare."
        pile = w.piles.get(k, {})
        n = self.room(a, it, min(act["qty"], pile.get(it, 0)))
        if n <= 0:
            return "fail", f"There is no {it} there, or you cannot carry it."
        I.remove(pile, it, n)
        if not pile:
            del w.piles[k]
        I.add(a.inventory, it, n)
        self.event("pickup", f"{a.name} picked up {n} {it} at ({act['x']},{act['y']})", a, item=it, qty=n)
        return "done", f"You picked up {n} {it}."

    def do_steal(self, a, act):
        w = self.w
        v = w.agents.get(act["victim"])
        if not v or not v.alive or dist(a.x, a.y, v.x, v.y) > 1:
            return "fail", "They slipped out of reach."
        it = act.get("item")
        if it in (None, "", "food", "any"):
            cands = [k for k in v.inventory if (I.ITEMS[k]["food"] > 0 or it == "any")]
            it = w.rng.choice(sorted(cands)) if cands else None
        p = 0.45 + 0.1 * (a.speed - v.speed) + (0.3 if v.resting else 0) + (0.15 if w.is_night() else 0)
        p = max(0.05, min(0.9, p))
        success = it is not None and v.inventory.get(it) and w.rng.random() < p
        if success:
            n = I.remove(v.inventory, it, min(act["qty"], self.room(a, it, act["qty"])))
            I.add(a.inventory, it, n)
            noticed = w.rng.random() < 0.6
            if noticed:
                self.tell(v, f"{a.name} stole {n} {it} from you!")
                self.ledger(v, a, "robbed", f"{a.name} stole {n} {it} from you")
                self.wake(v, f"{a.name} robbed you")
            else:
                self.tell(v, f"Some of your {it} is gone. You did not see who took it.")
                self.ledger(v, None, "missing", f"{n} {it} went missing while {a.name} was near")
                self.wake(v, "something of yours went missing")
            self.event("steal", f"{a.name} stole {n} {it} from {v.name}", a, v, item=it, qty=n, noticed=noticed)
            self.witnesses(a.x, a.y, f"You saw {a.name} steal from {v.name}.", exclude={a.id, v.id},
                           chance=0 if w.is_night() else 0.5)
            self.ledger(a, v, "stole", f"you stole {n} {it} from {v.name}" + ("" if noticed else " unseen"))
            return "done", f"You stole {n} {it} from {v.name}." + ("" if noticed else " They did not notice.")
        self.tell(v, f"{a.name} tried to steal from you and failed.")
        self.ledger(v, a, "robbed", f"{a.name} tried to steal from you")
        self.wake(v, f"{a.name} tried to rob you")
        self.event("steal_fail", f"{a.name} tried to steal from {v.name} and was caught", a, v)
        self.witnesses(a.x, a.y, f"You saw {a.name} try to steal from {v.name}.", exclude={a.id, v.id})
        what = "" if it else " They had nothing like that."
        return "done", f"You tried to steal from {v.name} and they caught you.{what}"

    def do_give(self, a, act):
        w = self.w
        o = w.agents.get(act["to"])
        if not o or not o.alive or dist(a.x, a.y, o.x, o.y) > 1:
            return "fail", "They are no longer next to you."
        it = act["item"]
        n = I.remove(a.inventory, it, act["qty"])
        if not n:
            return "fail", f"You have no {it}."
        room = self.room(o, it, n)
        I.add(o.inventory, it, room)
        if n > room:
            self.drop_pile(o.x, o.y, {it: n - room})
        self.tell(o, f"{a.name} gave you {n} {it}." + (f" You could not carry {n - room}; it fell at your feet." if n > room else ""))
        self.wake(o, f"{a.name} gave you something")
        self.ledger(o, a, "gift_in", f"{a.name} gave you {n} {it}")
        self.ledger(a, o, "gift_out", f"you gave {o.name} {n} {it}")
        for p in w.promises:
            if not p["done"] and p["from"] == a.id and p["to"] == o.id and p["item"] == it:
                p["paid"] += n
        self.event("give", f"{a.name} gave {o.name} {n} {it}", a, o, item=it, qty=n)
        self.witnesses(a.x, a.y, f"{a.name} gave {o.name} some {it}.", exclude={a.id, o.id}, chance=0.6)
        return "done", f"You gave {o.name} {n} {it}."

    def damage(self, a, v):
        c = self.cfg["combat"]
        d = c["base_damage"] + a.strength
        if a.inventory.get("spear"):
            d += c["spear_damage"]
            self.use_tool(a, "spear")
        if v.resting:
            d += c["resting_bonus"]
        d += c["ally_damage"] * len(self.ally_hits.get(v.id, []))
        if a.age < self.cfg["agent"]["adult_ticks"] // 2:
            d = max(1, d - 2)
        return d

    def do_attack(self, a, act):
        w = self.w
        c = self.cfg["combat"]
        v = w.agents.get(act["victim"])
        if not v or not v.alive:
            return "fail", "Your target is gone."
        if dist(a.x, a.y, v.x, v.y) > 1:
            self.step_toward(a, v.x, v.y, True)
        if dist(a.x, a.y, v.x, v.y) > 1:
            self.tell(v, f"{a.name} lunged at you, but you were out of reach.")
            self.wake(v, f"{a.name} tried to attack you")
            self.event("attack_miss", f"{a.name} went for {v.name} but could not reach them", a, v)
            return "fail", f"{v.name} was out of reach."
        d = self.damage(a, v)
        allies = self.ally_hits.setdefault(v.id, [])
        allies.append(a.id)
        v.health -= d
        back = c["retaliation"] if not v.resting and v.health > 0 else 0
        a.health -= back
        self.tell(v, f"{a.name} attacked you! You lost {d} health.")
        self.ledger(v, a, "attacked", f"{a.name} attacked you ({d} damage)")
        self.ledger(a, v, "attacked_them", f"you attacked {v.name}")
        self.wake(v, f"{a.name} attacked you")
        self.event("attack", f"{a.name} attacked {v.name} for {d} damage", a, v, dmg=d, allies=list(allies[:-1]))
        self.witnesses(a.x, a.y, f"{a.name} attacked {v.name}!", exclude={a.id, v.id})
        msg = f"You struck {v.name} ({d} damage)" + (f" and took {back} in return." if back else ".")
        if v.health <= 0:
            self.kill(v, f"killed by {a.name}", a)
            msg += f" {v.name} is dead."
        if a.health <= 0:
            self.kill(a, f"died fighting {v.name}", v)
        return "done", msg

    def do_smash(self, a, act):
        w = self.w
        s = w.structures.get(act["sid"])
        if not s or dist(a.x, a.y, s.x, s.y) > 1:
            return "fail", "It is not there."
        d = 1 + a.strength + (2 if a.inventory.get("axe") else 0)
        s.hp -= d
        owner = w.agents.get(s.owner)
        if owner and owner.alive and owner.id != a.id:
            if self.can_see(owner, s.x, s.y):
                self.tell(owner, f"{a.name} is breaking your {s.kind} at ({s.x},{s.y})!")
                self.wake(owner, f"{a.name} is breaking your {s.kind}")
            self.ledger(owner, a, "smash", f"{a.name} damaged your {s.kind}")
        self.event("smash", f"{a.name} struck the {s.kind} at ({s.x},{s.y})", a, owner, sid=s.id)
        if s.hp <= 0:
            self.destroy(s, f"{a.name} broke down the {s.kind} at ({s.x},{s.y})")
            return "done", f"You broke the {s.kind} apart."
        return "done", f"You damaged the {s.kind}."

    def destroy(self, s, text):
        w = self.w
        if s.inventory and s.kind != "farm":
            self.drop_pile(s.x, s.y, s.inventory)
        del w.structures[s.id]
        self.event("destroyed", text, sid=s.id, what=s.kind, x=s.x, y=s.y, owner=s.owner)
        self.witnesses(s.x, s.y, text + ".")

    def do_teach(self, a, act):
        w = self.w
        o = w.agents.get(act["to"])
        if not o or not o.alive or dist(a.x, a.y, o.x, o.y) > 1:
            return "fail", "They are no longer beside you."
        rk = act["recipe"]
        prod = w.recipes[rk]
        a_, b_ = rk.split("+")
        if rk not in o.recipes:
            o.recipes.append(rk)
        self.tell(o, f"{a.name} taught you to make a {prod} from {a_} and {b_}.")
        self.wake(o, f"{a.name} taught you something")
        self.ledger(o, a, "taught_me", f"{a.name} taught you to make {prod}")
        self.ledger(a, o, "taught", f"you taught {o.name} to make {prod}")
        self.event("teach", f"{a.name} taught {o.name} how to make {prod}", a, o, item=prod, pair=rk)
        return "done", f"You taught {o.name} to make {prod}."

    def do_do(self, a, act):
        w = self.w
        if not act.get("shown"):
            act["shown"] = True
            o = w.agents.get(act["to"]) if act.get("to") else None
            line = f"{a.name}: {act['text']}"
            self.event("deed", line, a, o, words=act["text"])
            self.witnesses(a.x, a.y, f"You see {line}", exclude={a.id} | ({o.id} if o else set()))
            if o and o.alive:
                self.tell(o, f"{a.name}, toward you: {act['text']}")
                if self.can_see(o, a.x, a.y):
                    self.speech_wake(o, f"{a.name} did something toward you")
        act["left"] -= 1
        return ("go", "") if act["left"] > 0 else ("done", "You did it.")

    def do_mark(self, a, act):
        w = self.w
        k = key(a.x, a.y)
        signs = w.signs.setdefault(k, [])
        signs.append([a.id, act["text"], w.tick])
        if len(signs) > 3:
            signs.pop(0)
        self.event("mark", f"{a.name} left a sign at ({a.x},{a.y}): \"{act['text']}\"", a, words=act["text"], x=a.x, y=a.y)
        return "done", "You left a sign."

    # ================= world upkeep =================
    def use_tool(self, a, item):
        uses = I.ITEMS[item].get("uses")
        if not uses:
            return
        a.wear[item] = a.wear.get(item, 0) + 1
        if a.wear[item] >= uses:
            a.wear[item] = 0
            I.remove(a.inventory, item, 1)
            self.tell(a, f"Your {item} broke.")
            self.event("tool_breaks", f"{a.name}'s {item} broke", a, item=item)

    def hunger_word(self, a):
        s = a.satiety
        m = self.cfg["agent"]["max_satiety"]
        if s <= 0:
            return "starving"
        if s <= 4:
            return "very hungry"
        if s <= 8:
            return "hungry"
        if s < m - 3:
            return "fed"
        return "full"

    def health_word(self, a):
        h = a.health
        if h >= 9:
            return "healthy"
        if h >= 6:
            return "a little hurt"
        if h >= 3:
            return "badly hurt"
        return "near death"

    def needs(self):
        w = self.w
        c = self.cfg["agent"]
        r = self.cfg["resources"]
        t = w.tick
        winter_night = w.season() == "winter" and w.is_night()
        fires = [s for s in w.structures.values() if s.kind == "fire" and s.done and s.fuel > 0]
        for a in w.living():
            a.age += 1
            if (t + a.id) % c["hunger_every"] == 0 and a.satiety > 0:
                a.satiety -= 1
            if a.satiety <= 0 and (t + a.id) % c["starve_every"] == 0:
                a.health -= 1
                if a.health <= 0:
                    self.kill(a, "starved")
                    continue
            s = w.structure_at(a.x, a.y)
            sheltered = bool(s and s.kind == "shelter" and s.done)
            if a.satiety >= 6 and a.health < c["max_health"]:
                every = c["heal_every_resting"] if a.resting else c["heal_every"]
                if a.resting and sheltered:
                    every = 1
                if (t + a.id) % every == 0:
                    a.health += 1
            if winter_night and not sheltered and not any(dist(a.x, a.y, f.x, f.y) <= 1 for f in fires):
                if a.inventory.get("cloak"):
                    self.use_tool(a, "cloak")
                elif w.rng.random() < r["cold_chance"]:
                    a.health -= 1
                    self.tell(a, "The winter cold bites you (lost 1 health).")
                    if a.health <= 0:
                        self.kill(a, "froze")
                        continue
            if a.age >= a.lifespan:
                self.kill(a, "died of old age")
                continue
            self.spoil(a.inventory, 0.5 if a.inventory.get("pot") else 1.0)
            if a.pregnant and w.tick >= a.pregnant["due"]:
                self.birth(a)

    def spoil(self, inv, factor):
        rng = self.w.rng
        for k in list(inv):
            p = I.ITEMS[k]["spoil"] * factor
            if p <= 0:
                continue
            n = inv[k]
            lost = sum(1 for _ in range(n) if rng.random() < p)
            if lost:
                I.remove(inv, k, lost)

    def resources(self):
        w = self.w
        r = self.cfg["resources"]
        season = w.season()
        tpd = w.tpd()
        day_start = w.hour() == 0
        season_start = day_start and w.day() % self.cfg["world"]["days_per_season"] == 0
        regrow = r["bush_regrow"][season]
        if w.cfg.get("_drought_until", -1) > w.tick and regrow:
            regrow *= 2
        for k, b in list(w.bushes.items()):
            if season_start and season == "winter":
                b["b"] -= b["b"] // 4
            if season_start:
                b["strips"] = max(0, b["strips"] - 1)
            if regrow:
                b["regrow"] += 1
                slow = 2 if b["b"] < 3 and b["strips"] >= 2 else 1   # an overpicked bush recovers slowly
                if b["regrow"] >= regrow * slow:
                    b["regrow"] = 0
                    b["b"] = min(r["bush_max"], b["b"] + 1)
                if season in ("spring", "summer") and w.rng.random() < r["bush_spread_chance"]:
                    x, y = unkey(k)
                    nx, ny = x + w.rng.randint(-2, 2), y + w.rng.randint(-2, 2)
                    if w.in_bounds(nx, ny) and w.t(nx, ny) in (GRASS, FOREST) and key(nx, ny) not in w.bushes \
                            and not w.structure_at(nx, ny):
                        w.bushes[key(nx, ny)] = {"b": 1, "strips": 0, "regrow": 0}
        # herds wander and grow
        for h in w.herds:
            if h["size"] <= 0:
                continue
            if (w.tick + h["id"]) % r["herd_move_every"] == 0:
                hunted = any(a.activity and a.activity["verb"] == "hunt" and a.activity.get("herd") == h["id"]
                             for a in w.living())
                if not hunted or w.rng.random() < 0.3:
                    dx, dy = w.rng.choice(list(DIRS.values()))
                    nx, ny = h["x"] + dx, h["y"] + dy
                    if w.passable(nx, ny) and w.t(nx, ny) != FERTILE or (w.passable(nx, ny) and w.rng.random() < 0.3):
                        h["x"], h["y"] = nx, ny
            if day_start and season != "winter" and h["size"] >= 2:
                h["grow"] += 1
                if h["grow"] >= r["herd_grow_every_days"]:
                    h["grow"] = 0
                    h["size"] = min(r["herd_max"], h["size"] + 1)
            if day_start and h["size"] == 1:
                h["size"] = 0
                self.event("herd_leaves", f"The last deer of a herd wandered away from ({h['x']},{h['y']})",
                           x=h["x"], y=h["y"])
        w.herds = [h for h in w.herds if h["size"] > 0]
        if season_start and len(w.herds) < self.cfg["world"]["herds"]:
            self.herd_arrives()
        # snares
        for k, owner in list(w.snares.items()):
            if w.rng.random() < r["snare_chance"] and w.piles.get(k, {}).get("meat", 0) < 3:
                x, y = unkey(k)
                self.drop_pile(x, y, {"meat": 1})
        # piles spoil on the ground, twice as fast
        for k in list(w.piles):
            self.spoil(w.piles[k], 2.0)
            if not w.piles[k]:
                del w.piles[k]
        for k in list(w.corpses):
            if w.tick - w.corpses[k][1] > 5 * tpd:
                del w.corpses[k]
        if day_start:
            self.shocks()

    def herd_arrives(self):
        w = self.w
        edge = [(x, y) for x in range(w.w) for y in (0, w.h - 1)] + [(x, y) for y in range(w.h) for x in (0, w.w - 1)]
        edge = [c for c in edge if w.t(*c) == GRASS]
        if not edge:
            return
        x, y = w.rng.choice(edge)
        hid = max([h["id"] for h in w.herds] + [0]) + 1 + w.tick
        lo, hi = self.cfg["world"]["herd_size"]
        w.herds.append({"id": hid, "x": x, "y": y, "size": w.rng.randint(lo, hi), "grow": 0})
        self.event("herd_arrives", f"A new deer herd wandered in at ({x},{y})", x=x, y=y)

    def shocks(self):
        w = self.w
        rng = w.rng
        season = w.season()
        roll = rng.random()
        if season == "summer" and roll < 0.02:
            w.cfg["_drought_until"] = w.tick + 8 * w.tpd()
            self.event("drought", "A drought began; bushes regrow slowly")
            for a in w.living():
                self.tell(a, "The ground is dry and hard; the bushes are not fruiting well.")
        elif roll < 0.035:
            hit = [s for s in w.structures.values() if s.kind in ("store", "shelter", "wall", "fire")]
            for s in hit:
                s.hp -= rng.randint(2, 8)
                if s.hp <= 0:
                    self.destroy(s, f"A storm wrecked the {s.kind} at ({s.x},{s.y})")
            self.event("storm", "A storm swept over the land")
            for a in w.living():
                self.tell(a, "A violent storm passed over.")
        elif roll < 0.045 and w.bushes:
            x0, y0 = unkey(rng.choice(sorted(w.bushes)))
            gone = [k for k in w.bushes if dist(x0, y0, *unkey(k)) <= 4]
            for k in gone:
                del w.bushes[k]
            self.event("blight", f"A blight killed {len(gone)} berry bushes around ({x0},{y0})", x=x0, y=y0)
            self.witnesses(x0, y0, "The berry bushes around here are withering and dying.")

    def structures_tick(self):
        w = self.w
        r = self.cfg["resources"]
        for s in list(w.structures.values()):
            if s.kind == "fire" and s.done:
                s.fuel -= 1
                if s.fuel <= 0:
                    del w.structures[s.id]
            elif s.kind == "store" and s.done:
                self.spoil(s.inventory, 0.4)
            elif s.kind == "farm" and s.done and s.planted is not None and not s.inventory.get("grain"):
                if w.season() != "winter":
                    s.progress += 1
                if s.progress >= r["farm_grow_ticks"]:
                    s.inventory["grain"] = s.seeds * r["grain_per_seed"]
                    self.event("ripe", f"The crop at ({s.x},{s.y}) is ripe", sid=s.id, owner=s.owner)
                    o = w.agents.get(s.owner)
                    if o and o.alive:
                        self.tell(o, f"Your crop at ({s.x},{s.y}) is ripe.")
                        self.wake(o, "your crop is ripe")
            elif not s.done and w.tick - s.built > 10 * w.tpd():
                del w.structures[s.id]   # abandoned site

    def social_tick(self):
        w = self.w
        for pid, p in list(w.proposals.items()):
            if w.tick >= p["expires"]:
                del w.proposals[pid]
                a = w.agents.get(p["from"])
                if a and a.alive:
                    self.tell(a, f"Your offer #{pid} to {w.agents[p['to']].name} went unanswered.")
        for p in w.promises:
            if p["done"]:
                continue
            a, b = w.agents.get(p["from"]), w.agents.get(p["to"])
            if p["paid"] >= p["qty"]:
                p["done"], p["kept"] = True, True
            elif w.tick >= p["due"] or not a.alive or not b.alive:
                p["done"], p["kept"] = True, False
            else:
                continue
            what = f"{p['qty']} {p['item']}"
            if not a.alive or not b.alive:
                continue
            if p["kept"]:
                self.ledger(b, a, "kept", f"{a.name} kept a promise to give you {what}")
                self.ledger(a, b, "kept_mine", f"you kept your promise of {what} to {b.name}")
                self.event("promise_kept", f"{a.name} kept a promise of {what} to {b.name}", a, b, promise=p["id"])
            else:
                self.ledger(b, a, "broke", f"{a.name} broke a promise to give you {what}")
                self.ledger(a, b, "broke_mine", f"you broke your promise of {what} to {b.name}")
                self.tell(b, f"{a.name} did not deliver the {what} promised by now.")
                self.tell(a, f"The {what} you promised {b.name} is overdue; you broke that promise.")
                self.wake(b, f"{a.name} broke a promise to you")
                self.event("promise_broken", f"{a.name} broke a promise of {what} to {b.name}", a, b, promise=p["id"])
        w.promises = [p for p in w.promises if not p["done"] or w.tick - p["due"] < 3 * w.tpd()]
        for vid, v in list(w.votes.items()):
            if v["done"]:
                continue
            g = w.groups.get(v["group"])
            if not g or g.dissolved is not None:
                v["done"] = True
                continue
            voters = set(v["yes"]) | set(v["no"])
            if w.tick < v["closes"] and not set(g.members) <= voters:
                continue
            v["done"] = True
            passed = len(v["yes"]) > len(v["no"])
            res = f"Vote #{vid} in {g.name} ({v['q']}): {'passed' if passed else 'failed'}, {len(v['yes'])} yes, {len(v['no'])} no."
            for m in g.members:
                self.tell(w.agents[m], res)
            self.event("vote_result", res, group=g.id, vote=vid, passed=passed)
            if passed and g.decide == "vote":
                tgt = w.agents.get(v["target"]) if v["target"] else None
                if v["kind"] == "expel" and tgt and tgt.id in g.members:
                    self.remove_member(g, tgt, f"{g.name} voted to expel {tgt.name}.")
                    self.wake(tgt, f"you were voted out of {g.name}")
                    self.event("expel", f"{g.name} voted {tgt.name} out", None, tgt, group=g.id)
                elif v["kind"] == "leader" and tgt and tgt.id in g.members:
                    g.leader = tgt.id
                    self.event("leader", f"{tgt.name} was voted leader of {g.name}", tgt, group=g.id)
                elif v["kind"] == "rules":
                    g.rules = v["rules"]
        w.votes = {k: v for k, v in w.votes.items() if not v["done"] or w.tick - v["closes"] < 2 * w.tpd()}

    def life_tick(self):
        w = self.w
        cw = self.cfg["world"]
        pop = len(w.living())
        if pop < cw["arrival_below"] and w.rng.random() < 1 / (cw["arrival_every_days"] * w.tpd()):
            self.arrival()
        elif pop == 0:
            self.arrival()

    def arrival(self):
        w = self.w
        edge = [(x, y) for x in range(w.w) for y in (0, w.h - 1)] + [(x, y) for y in range(w.h) for x in (0, w.w - 1)]
        edge = [c for c in edge if w.passable(*c)]
        x, y = w.rng.choice(edge)
        a = w.make_agent(x, y)
        a.born = w.tick - a.age
        a.inventory = {"berries": w.rng.randint(0, 4)}
        if w.rng.random() < 0.7:
            rk = w.rng.choice(sorted(w.recipes))
            if rk not in a.recipes:
                a.recipes.append(rk)
        self.tell(a, "You have walked a long way from lands to the far side of the edge, and arrived here with little.")
        self.wake(a, "you have just arrived in this land")
        self.event("arrive", f"A stranger, {a.name}, walked in at ({x},{y})", a, x=x, y=y)
        return a

    def birth(self, carrier):
        w = self.w
        preg = carrier.pregnant
        carrier.pregnant = None
        partner = w.agents.get(preg["partner"])
        x, y = w.free_near(carrier.x, carrier.y)
        child = w.make_agent(x, y, age=0, parents=[carrier.id, preg["partner"]])
        if preg.get("name") and preg["name"].capitalize() not in w.names_taken:
            w.names_taken.discard(child.name)
            child.name = preg["name"].strip().capitalize()
            w.names_taken.add(child.name)
        child.born = w.tick
        child.strength = 1
        child.satiety = 12
        child.teachings = [t for t in preg["teachings"] if t[1]]
        for p in (carrier, partner):
            if p is None:
                continue
            p.children.append(child.id)
            self.ledger(child, p, "kin", f"{p.name} is your parent")
            self.ledger(p, child, "kin", f"{child.name} is your child")
            if p.alive:
                self.tell(p, f"Your child {child.name} was born at ({x},{y}).")
                self.wake(p, f"your child {child.name} was born")
        self.tell(child, "You were born. Your parents are " + " and ".join(p.name for p in (carrier, partner) if p) + ".")
        self.wake(child, "you were just born and are old enough to act")
        self.event("birth", f"{child.name} was born to {carrier.name}" + (f" and {partner.name}" if partner else ""),
                   child, carrier, partner=preg["partner"])

    def kill(self, a, cause, by=None):
        w = self.w
        if not a.alive:
            return
        a.alive = False
        a.died = w.tick
        a.cause = cause
        a.activity = None
        a.plan = []
        if a.inventory:
            self.drop_pile(a.x, a.y, a.inventory)
            a.inventory = {}
        w.corpses[key(a.x, a.y)] = [a.name, w.tick]
        self.event("death", f"{a.name} {cause}" if cause.startswith(("died", "starved", "froze")) else f"{a.name} was {cause}",
                   a, by, cause=cause, age=a.age, x=a.x, y=a.y,
                   knew=[w.recipes[k] for k in a.recipes])
        self.witnesses(a.x, a.y, f"{a.name} has died ({cause}).", exclude={a.id})
        for rk in a.recipes:
            if not any(rk in o.recipes for o in w.living()):
                self.event("lost_knowledge", f"With {a.name} died the only knowledge of how to make {w.recipes[rk]}",
                           a, item=w.recipes[rk], pair=rk)
        for gid in list(a.groups):
            g = w.groups.get(gid)
            if g:
                self.remove_member(g, a, f"{a.name} of {g.name} is dead.")
        for s in w.structures.values():
            if s.owner == a.id:
                heir = next((w.agents[c] for c in a.children if w.agents[c].alive), None)
                if heir:
                    s.owner = heir.id
                    self.tell(heir, f"You inherited {a.name}'s {s.kind} at ({s.x},{s.y}).")
                elif s.access.startswith("group:"):
                    g = w.groups.get(int(s.access.split(":")[1]))
                    if g and g.members:
                        s.owner = g.leader
                        self.tell(w.agents[g.leader], f"{a.name}'s {s.kind} at ({s.x},{s.y}) passes to you as leader of {g.name}.")
                else:
                    s.access = "anyone"
        for c in a.children + a.parents:
            o = w.agents.get(c)
            if o and o.alive:
                self.tell(o, f"Your kin {a.name} has died ({cause}).")
                self.wake(o, f"{a.name}, your kin, died")
        for k in list(w.snares):
            if w.snares[k] == a.id:
                w.snares[k] = -1

    def perceive(self):
        """Notice new faces and crossing hunger/health lines."""
        w = self.w
        quiet = self.cfg["mind"]["quiet_ticks"]
        living = w.living()
        for a in living:
            for o in living:
                if o.id == a.id or not self.can_see(a, o.x, o.y):
                    continue
                last = a.seen.get(str(o.id))
                known = last is not None or o.name in a.beliefs
                if not known:
                    self.wake(a, f"a stranger, {o.name}, came into view")
                elif last is None or w.tick - last > 3 * w.tpd():
                    self.wake(a, f"{o.name} came into view after a long time")
                elif w.tick - last > 1:
                    self.tell(a, f"{o.name} came into view.")
                a.seen[str(o.id)] = w.tick
            hb = 0 if a.satiety > 8 else 1 if a.satiety > 4 else 2 if a.satiety > 0 else 3
            if hb > a.hunger_band:
                self.wake(a, f"you are {self.hunger_word(a)}")
            a.hunger_band = hb
            lb = 0 if a.health >= 9 else 1 if a.health >= 6 else 2 if a.health >= 3 else 3
            if lb > a.health_band:
                self.wake(a, f"you are {self.health_word(a)}")
            a.health_band = lb

    # ================= a whole tick =================
    def tick(self, decide):
        """decide(list_of_agents) -> {agent_id: decision}. Minds are asked in one batch."""
        w = self.w
        ask = [a for a in sorted(w.living(), key=lambda a: a.id) if self.needs_decision(a)]
        decisions = decide(ask) if ask else {}
        for a in ask:
            self.apply_decision(a, decisions.get(a.id))
        self.step_activities()
        self.step_world()
        return ask
