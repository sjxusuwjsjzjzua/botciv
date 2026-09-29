"""The engine: the only code that changes the world.

Minds return intents. The engine validates them against what the agent can
see and hold, turns them into activities, runs activities tick by tick, and
tells every agent involved what happened.
"""
import json
import re
from collections import Counter

from . import items as I
from .standing import standing
from .world import (World, Group, Structure, DIRS, PASSABLE, GRASS, FOREST, FERTILE, ROCK,
                    WATER, key, unkey, dist, direction)

BUILD = {
    "store":   {"cost": {"wood": 4}, "ticks": 4, "hp": 20},
    "shelter": {"cost": {"wood": 5, "fibre": 4}, "ticks": 6, "hp": 20},
    "wall":    {"cost": {"stone": 2}, "ticks": 3, "hp": 30},
    "farm":    {"cost": {"wood": 1}, "ticks": 2, "hp": 10},
    "fire":    {"cost": {"wood": 2}, "ticks": 1, "hp": 5},
    "monument": {"cost": {"stone": 3}, "ticks": 5, "hp": 60},
}
STORE_CAP = 60.0
MOVERS = {"go", "follow"}
SOCIAL = {"say"}
ALIASES = {"berry": "berries", "fiber": "fibre", "fibers": "fibre", "fibres": "fibre", "seed": "seeds",
           "woods": "wood", "log": "wood", "logs": "wood", "stones": "stone", "rock": "stone",
           "rocks": "stone", "cooked meat": "cooked_meat", "cookedmeat": "cooked_meat",
           "smoked fish": "smoked_fish", "smoked meat": "smoked_meat", "dried berries": "dried_berries",
           "dried meat": "smoked_meat", "dried fish": "smoked_fish", "jerky": "smoked_meat",
           "fishes": "fish", "ropes": "rope", "spears": "spear", "hides": "hide", "bones": "bone",
           "nets": "net", "pots": "pot", "baskets": "basket", "cloaks": "cloak", "snares": "snare",
           "necklaces": "necklace", "drums": "drum", "grains": "grain", "breads": "bread",
           "venison": "meat", "deer meat": "meat", "axes": "axe", "poultices": "poultice",
           "berry bush": "berries", "berry_bush": "berries", "bush": "berries", "bushes": "berries",
           "tree": "wood", "trees": "wood", "forest": "wood", "branches": "wood", "sticks": "wood",
           "grass": "fibre", "reeds": "fibre", "plant fibre": "fibre", "crop": "grain", "wheat": "grain",
           "farm": "grain", "raw meat": "meat", "deer": "meat"}
VERBS = ["continue", "go", "gather", "fish", "hunt", "eat", "rest", "wait", "craft", "build", "plant",
         "drop", "put", "take", "give", "attack", "follow", "teach", "mark", "do", "tell_story", "name_place",
         "bury", "set_access",
         "found_group", "invite", "join", "leave", "expel", "call_vote", "vote",
         "propose", "accept", "refuse", "ask_child", "smoke", "pledge", "part", "bequeath"]
PLAN_VERBS = ["go", "gather", "fish", "hunt", "eat", "rest", "wait", "craft", "build", "plant",
              "drop", "put", "take", "give", "follow", "smoke"]
TECHNIQUES = {"smoking": "smoke fish and meat and dry berries over a fire, so they keep most of a year"}


def norm_item(s):
    if s is None:
        return None
    s = str(s).strip().lower()
    s = ALIASES.get(s, s)
    s = s.replace(" ", "_")
    s = ALIASES.get(s, s)
    return s


def item_in_text(s):
    """The first thing named in free words ("take the bone and hide" -> bone), or None."""
    if not s:
        return None
    it = norm_item(s)
    if it in I.ITEMS:
        return it
    words = [w.strip(".,;:!?\"'()") for w in str(s).lower().split()]
    for n in (2, 1):
        for i in range(len(words) - n + 1):
            it = norm_item(" ".join(words[i:i + n]))
            if it in I.ITEMS:
                return it
    return None


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
        if isinstance(d, dict) and d.get("pending"):
            # still thinking: carry on with what they were doing, keep what they have to hear
            if a.activity is None:
                if not (a.plan and self.next_plan_step(a)):
                    a.activity = {"verb": "wait", "n": 0, "left": 1, "quiet": True}
            return
        if isinstance(d, dict) and d.get("retry"):
            # the mind could not be reached: hesitate a moment, keep what it has to hear
            a.activity = {"verb": "wait", "n": 0, "left": 1, "quiet": True}
            a.plan = []
            return
        asked = d.get("asked") if isinstance(d, dict) and isinstance(d.get("asked"), dict) else None
        if asked:
            # an answer that arrives hours after the question: what happened since it was
            # asked was not in the prompt, so it stays for the next one
            a.last_decided = asked["t"]
            a.events = [ev for ev in a.events if ev[0] >= asked["t"]]
            a.wake = [r for r in a.wake if r not in asked.get("wake", [])]
        else:
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
        sv = d.get("self")
        if isinstance(sv, str) and len(sv.strip()) >= 8:
            a.self_view = sv.strip()[: self.cfg["agent"]["self_chars"]]
        rem = d.get("remember")
        if isinstance(rem, str) and len(rem.strip()) >= 8:
            self.remember(a, rem.strip()[: self.cfg["agent"]["life_chars"]])
        bel = d.get("beliefs")
        if isinstance(bel, list):
            for b in bel:
                if isinstance(b, dict) and b.get("name") and isinstance(b.get("belief"), str):
                    o = w.by_name(b["name"])
                    if o and o.id != a.id:
                        a.beliefs[o.name] = b["belief"].strip()[: self.cfg["agent"]["belief_chars"]]
        idea = d.get("idea")
        if isinstance(idea, str) and len(idea.strip()) >= 8 and not any(
                idea.strip()[:300] == t for _, t in a.ideas):
            # something they want that the world does not offer yet; later versions of
            # the world make the most wanted ones real, first for whoever imagined them
            text = idea.strip()[:300]
            a.ideas = (a.ideas + [[w.tick, text]])[-6:]
            self.event("idea", f"{a.name} imagined: {text}", a, words=text)
        ea = d.get("eat")
        if isinstance(ea, dict) and ea.get("item"):
            self.eat_now(a, norm_item(ea.get("item")), as_int(ea.get("qty"), 99, 1, 99))
        sp = d.get("speech")
        if isinstance(sp, dict) and isinstance(sp.get("text"), str) and sp["text"].strip():
            self.speak(a, sp["text"].strip()[:400], sp.get("to"), bool(sp.get("whisper")))
        if isinstance(sp, dict) and isinstance(sp.get("of"), str) and sp["of"].strip():
            self.pass_on(a, sp["of"].strip(), sp.get("to"), bool(sp.get("whisper")))
        act = d.get("action") if isinstance(d.get("action"), dict) else {"verb": "wait"}
        verb = str(act.get("verb", "wait")).strip().lower()
        if verb == "continue" and (a.activity or a.plan):
            if a.activity is None and a.plan:
                self.next_plan_step(a)
            return
        if verb == "continue":
            # nothing under way: take up the plan given now, or pause a little
            plan = d.get("plan") if isinstance(d.get("plan"), list) else []
            a.plan = [p for p in plan if isinstance(p, dict) and str(p.get("verb", "")).lower() in PLAN_VERBS][:8]
            if not (a.plan and self.next_plan_step(a)):
                a.activity = {"verb": "wait", "n": 0, "left": 2, "quiet": True}
            return
        plan = d.get("plan") if isinstance(d.get("plan"), list) else []
        a.plan = [p for p in plan if isinstance(p, dict) and str(p.get("verb", "")).lower() in PLAN_VERBS][:8]
        a.routine = []
        if d.get("repeat") and verb in PLAN_VERBS:
            a.routine = [dict(act)] + [dict(p) for p in a.plan]
        a.activity = None
        ok, msg = self.start(a, act)
        if not ok:
            self.tell(a, f"You could not {verb}: {msg}")
            self.event("fail", f"{a.name} tried to {verb} but could not: {msg}", a, verb=verb)
            a.plan = []
            a.activity = {"verb": "wait", "left": 1, "quiet": True}
            a.failures += 1
            self.wake(a, f"your last choice failed ({msg})")

    def remember(self, a, text):
        """A line the person chose to keep for the rest of their life. At most one a day
        (another the same day replaces it), and a few in all: when there are too many the
        second oldest goes, so the first thing that ever changed them stays."""
        w = self.w
        if any(text[:40].lower() == t[:40].lower() for _, t in a.life):
            return
        if a.life and a.life[-1][0] // w.tpd() == w.tick // w.tpd():
            a.life[-1] = [w.tick, text]
            return
        a.life.append([w.tick, text])
        if len(a.life) > self.cfg["agent"]["life_lines"]:
            del a.life[1]

    def next_plan_step(self, a):
        while a.plan:
            step = a.plan.pop(0)
            ok, msg = self.start(a, step)
            if ok:
                return True
            self.tell(a, f"Your plan stopped: could not {step.get('verb')}: {msg}")
            a.plan = []
            a.routine = []
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
            a.routine = []
            self.wake(a, msg)
            return
        if msg:
            self.tell(a, msg)
        if not a.plan and a.routine and not a.wake:
            a.plan = [dict(p) for p in a.routine]
        if a.plan:
            self.next_plan_step(a)
        elif not act.get("quiet"):
            self.wake(a, f"you finished: {msg}" if msg else "you finished what you were doing")
        else:
            self.wake(a, "you are not doing anything")

    def step_world(self):
        if self.log:
            self.log.write({"t": self.w.tick, "kind": "frame",
                            "p": [[a.id, a.x, a.y, a.health, a.satiety, (a.activity or {}).get("verb", "")]
                                  for a in self.w.living()],
                            "h": [[h["id"], h["x"], h["y"], h["size"]] for h in self.w.herds],
                            "w": [[p["id"], p["x"], p["y"], p["size"]] for p in self.w.wolves]})
            if self.w.tick % self.w.tpd() == 0:
                # once a day, what each person has and commands (for the viewer, never the people)
                self.log.write({"t": self.w.tick, "kind": "census", "rot": round(self.w.rot_worth, 1),
                                "c": [[a.id, *standing(self.w, a)] for a in self.w.living()]})
            if self.w.tick % self.w.tpd() == 0:
                self.w.rot_worth = 0.0
        self.needs()
        self.resources()
        self.wolves_tick()
        self.structures_tick()
        self.social_tick()
        self.life_tick()
        self.perceive()
        self.w.tick += 1

    # ================= starting an action =================
    def start(self, a, act):
        verb = str(act.get("verb", "")).strip().lower()
        if not act.get("item") and verb in ("gather", "eat", "drop", "put", "give", "take", "craft", "build", "teach"):
            alt = act.get("choice") or act.get("text")
            if verb == "build" and alt:
                act = {**act, "item": alt}
            elif item_in_text(alt):
                act = {**act, "item": item_in_text(alt)}   # some minds put the item under choice or text
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
                spot = self.resolve_place(a, act.get("target")) or self.resolve_place(a, act.get("text"))
                if not spot:
                    return "say where: x and y, a direction, a person, a named place, or a kind of building"
                x, y = spot
        edge = not w.in_bounds(x, y)
        x, y = max(0, min(w.w - 1, x)), max(0, min(w.h - 1, y))
        if (x, y) == (a.x, a.y):
            note = " This is the edge of the world; there is nothing past it." if edge else ""
            self.tell(a, f"You are already at ({x},{y}).{note}")
            return self.set_act(a, "wait", left=1, quiet=True)
        adj = not w.passable(x, y, a)
        p = w.path(a, x, y, adjacent_ok=adj)
        if p is None:
            # no way there: walk to the nearest place one can reach, as a person would
            nx, ny = w.nearest_reachable(a, x, y)
            if (nx, ny) == (a.x, a.y) or dist(nx, ny, x, y) > dist(a.x, a.y, x, y) - 1:
                return f"you see no way to reach ({x},{y})"
            self.tell(a, f"There is no way through to ({x},{y}); you make for ({nx},{ny}), as near as you can get.")
            x, y, adj = nx, ny, False
        return self.set_act(a, "go", x=x, y=y, adjacent=adj, left=60)

    PLACE_WORDS = {"store": "store", "stores": "store", "storehouse": "store", "shelter": "shelter", "home": "shelter",
                   "house": "shelter", "hut": "shelter", "camp": "shelter", "fire": "fire", "campfire": "fire",
                   "hearth": "fire", "farm": "farm", "field": "farm", "wall": "wall", "monument": "monument",
                   "grave": "grave"}

    def resolve_place(self, a, words):
        """Where a person means when they name a place in words: coordinates written
        out, a named place, a kind of building (their own first), or water."""
        if not words or not isinstance(words, str):
            return None
        w = self.w
        text = words.strip().lower()
        m = re.search(r"(-?\d+)\s*,\s*(-?\d+)", text)
        if m:
            return int(m.group(1)), int(m.group(2))
        for x, y, name, *_ in w.places:
            n = name.lower()
            if n == text or (len(n) > 3 and (n in text or text in n)):
                return x, y
        kind = next((k for word, k in self.PLACE_WORDS.items() if re.search(rf"\b{word}\b", text)), None)
        if kind:
            mine = [s for s in w.structures.values() if s.kind == kind and s.owner == a.id]
            usable = [s for s in w.structures.values() if s.kind == kind and s.done and w.may_use(a, s)]
            seen = [s for s in w.structures.values() if s.kind == kind and self.can_see(a, s.x, s.y)]
            for group in (mine, usable, seen):
                if group:
                    s = min(group, key=lambda s: dist(a.x, a.y, s.x, s.y))
                    return s.x, s.y
            return None
        if re.search(r"\b(water|lake|river|stream|pond|shore)\b", text):
            r = w.sight(a)
            spots = [(dist(a.x, a.y, x, y), x, y) for y in range(a.y - r, a.y + r + 1) for x in range(a.x - r, a.x + r + 1)
                     if w.in_bounds(x, y) and w.t(x, y) == WATER]
            if spots:
                _, x, y = min(spots)
                return x, y
        return None

    def walk_then(self, a, act, x, y):
        """Walk to (x, y), then try the same thing again from there, once."""
        if act.get("walked_to"):
            return None
        a.plan.insert(0, dict(act, x=x, y=y, walked_to=True))
        res = self.start_go(a, {"x": x, "y": y})
        if res is not True and res is not None:
            a.plan.pop(0)
            return None
        return True

    def walk_to(self, a, act, other):
        """Someone in sight but not beside you: walk over to them, then try the same thing
        again there, once. Returns None when that cannot be done."""
        if act.get("walked_to") or not self.can_see(a, other.x, other.y):
            return None
        a.plan.insert(0, dict(act, walked_to=True))
        if self.start_go(a, {"target": other.name}) is not True:
            a.plan.pop(0)
            return None
        return True

    def usable_store(self, a, x=None, y=None):
        """A finished store this person may use: the one at (x, y) if given, else their
        own nearest, else the nearest open to them, within a day's walk."""
        w = self.w
        stores = [s for s in w.structures.values() if s.kind == "store" and s.done and w.may_use(a, s)
                  and dist(a.x, a.y, s.x, s.y) <= 24]
        if x is not None:
            at = [s for s in stores if (s.x, s.y) == (x, y)]
            if at:
                return at[0]
        own = [s for s in stores if s.owner == a.id]
        pool = own or stores
        return min(pool, key=lambda s: dist(a.x, a.y, s.x, s.y)) if pool else None

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

    def food_at_feet(self, a, item=None):
        """Food lying on the ground where a stands or next to them: (pile key, item) or None."""
        for dx in (0, -1, 1):
            for dy in (0, -1, 1):
                k = key(a.x + dx, a.y + dy)
                pile = self.w.piles.get(k) or {}
                foods = [t for t in pile if pile[t] > 0 and I.ITEMS[t]["food"] > 0 and (item in (None, t))]
                if foods:
                    return k, max(foods, key=lambda t: I.ITEMS[t]["spoil"])
        return None

    def start_eat(self, a, act):
        it = norm_item(act.get("item"))
        if it in (None, "", "food", "any"):
            foods = sorted((k for k in a.inventory if I.ITEMS[k]["food"] > 0 or k == "poultice"),
                           key=lambda k: I.ITEMS[k]["spoil"], reverse=True)
            if not foods:
                ground = self.food_at_feet(a)
                if not ground:
                    return "you carry no food"
                return self.set_act(a, "eat", item=ground[1], pile=ground[0], qty=as_int(act.get("qty"), 99, 1, 99))
            it = foods[0]
        if it not in a.inventory:
            ground = self.food_at_feet(a, it) if it in I.ITEMS else None
            if ground:
                return self.set_act(a, "eat", item=it, pile=ground[0], qty=as_int(act.get("qty"), 99, 1, 99))
            return f"you have no {it}"
        if I.ITEMS[it]["food"] <= 0 and it != "poultice":
            if it == "seeds":
                return "seeds are not food, but sown in a farm on rich soil each gives 6 grain"
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

    def build_spot(self, a, kind):
        """Your own tile if a building of this kind can go there, else a free tile next to
        you that fits (rich soil for a farm), else None."""
        w = self.w
        for dx, dy in ((0, 0), (0, -1), (1, 0), (0, 1), (-1, 0), (1, -1), (1, 1), (-1, 1), (-1, -1)):
            x, y = a.x + dx, a.y + dy
            if not w.in_bounds(x, y) or w.t(x, y) not in PASSABLE or w.structure_at(x, y):
                continue
            if kind == "farm" and w.t(x, y) != FERTILE:
                continue
            if kind in ("wall", "shelter") and w.agents_at(x, y) and (x, y) != (a.x, a.y):
                continue
            return x, y
        return None

    def target_tile(self, a, act):
        x, y = as_int(act.get("x")), as_int(act.get("y"))
        if x is None or y is None:
            return a.x, a.y
        return x, y

    def start_build(self, a, act):
        w = self.w
        raw = str(act.get("item") or act.get("text") or "").strip().lower()
        kind = raw if raw in BUILD else norm_item(raw)       # "farm" is an alias for grain when gathering
        if kind not in BUILD:
            kind = next((k for k in BUILD if re.search(rf"\b{k}\b", raw)), kind)
        if kind not in BUILD:
            return f"you can build: {', '.join(BUILD)}"
        if act.get("x") is None or act.get("y") is None:
            site = next((s for s in w.structures.values() if s.kind == kind and not s.done
                         and dist(a.x, a.y, s.x, s.y) <= 1), None)
            if site:
                return self.set_act(a, "build", sid=site.id)
        x, y = self.target_tile(a, act)
        if act.get("x") is None or act.get("y") is None:
            spot = self.build_spot(a, kind)          # no place named: the first fitting spot at hand
            if spot:
                x, y = spot
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
        if kind == "monument":
            s.name = str(act.get("name") or "").strip()[:40]
            s.text = str(act.get("text") or "").strip()[:240]
        w.structures[s.id] = s
        return self.set_act(a, "build", sid=s.id)

    def start_plant(self, a, act):
        w = self.w
        x, y = self.opt_xy(act)
        farms = [s for s in w.structures.values() if s.kind == "farm" and s.done and dist(a.x, a.y, s.x, s.y) <= 1
                 and (x is None or (s.x, s.y) == (x, y))]
        if not farms:
            # sowing where no farm stands means making the field first, as anyone would mean
            if (a.inventory.get("seeds") or a.inventory.get("grain")) and self.build_spot(a, "farm"):
                site = next((s for s in w.structures.values() if s.kind == "farm" and not s.done
                             and dist(a.x, a.y, s.x, s.y) <= 1), None)
                if site or a.inventory.get("wood", 0) >= BUILD["farm"]["cost"].get("wood", 0):
                    res = self.start_build(a, {"item": "farm"})
                    if res is True or res is None:
                        a.plan.insert(0, {k: v for k, v in act.items() if k not in ("x", "y")})
                    return res
                return "there is no farm beside you; a farm on rich soil needs 1 wood, then you can sow"
            return "there is no finished farm on or next to your tile; build one on rich soil first"
        # the one meant: a free one, one's own first
        free = sorted((f for f in farms if f.planted is None and not f.inventory.get("grain")),
                      key=lambda f: (f.owner != a.id, dist(a.x, a.y, f.x, f.y)))
        if not free:
            return "that farm is already planted" if len(farms) == 1 else "every farm beside you is already planted"
        farm = free[0]
        # grain is seed too: a harvest kept back can be sown again
        words = " ".join(str(act.get(k) or "") for k in ("item", "text", "choice")).lower()
        seed = "grain" if ("grain" in words or not a.inventory.get("seeds")) and a.inventory.get("grain") else "seeds"
        n = min(as_int(act.get("qty"), 4, 1, 99), self.cfg["resources"]["farm_max_seeds"], a.inventory.get(seed, 0))
        if n <= 0:
            return "you have no seeds or grain to sow"
        return self.set_act(a, "plant", sid=farm.id, qty=n, seed=seed, left=1)

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
        if not s or not self.w.may_use(a, s):
            far = self.usable_store(a, *self.opt_xy(act))
            if far and far is not s and self.walk_then(a, act, far.x, far.y):
                return True
        if not s:
            return "there is no finished store you may use on or next to your tile, and none you know of nearby"
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
                return self.walk_to(a, act, other) or f"{other.name} is not next to you and you cannot see them"
            return self.set_act(a, "steal", victim=other.id, item=it, qty=min(qty, 3), left=1)
        if tgt == "store":
            s = self.adjacent_structure(a, "store", *self.opt_xy(act))
            if not s or not w.may_use(a, s):
                far = self.usable_store(a, *self.opt_xy(act))
                if far and far is not s and self.walk_then(a, act, far.x, far.y):
                    return True
            if not s:
                return "there is no finished store you may use on or next to your tile, and none you know of nearby"
            if not w.may_use(a, s):
                return "that store is closed to you"
            foods = [k for k, n in s.inventory.items() if n and I.ITEMS[k]["food"] > 0]
            if it in (None, "food") and foods:
                # a hungry person reaching into a store without naming a thing means food:
                # what spoils soonest, about two days' worth unless they said how much
                it = max(foods, key=lambda k: (I.ITEMS[k]["spoil"], s.inventory[k]))
                if act.get("qty") is None:
                    qty = max(1, round(8 / I.ITEMS[it]["food"]))
            if not s.inventory.get(it):
                held = ", ".join(f"{n} {k}" for k, n in sorted(s.inventory.items()) if n) or "nothing"
                return f"the store holds no {it or 'such thing'} (it holds {held}); name the item to take"
            return self.set_act(a, "take", sid=s.id, item=it, qty=qty, left=1)
        # ground: own tile or adjacent pile; a pile a little way off is walked to first
        x, y = self.opt_xy(act)
        if (x is not None and dist(a.x, a.y, x, y) > 1 and dist(a.x, a.y, x, y) <= w.sight(a) + 2
                and (key(x, y) in w.piles or key(x, y) in w.snares) and self.walk_then(a, act, x, y)):
            return True
        spots = [(x, y)] if x is not None else [(a.x + dx, a.y + dy) for dx in (0, -1, 1) for dy in (0, -1, 1)]
        for sx, sy in spots:
            if sx is None or dist(a.x, a.y, sx, sy) > 1:
                continue
            pile = w.piles.get(key(sx, sy), {})
            if it in pile or (it == "snare" and key(sx, sy) in w.snares):
                return self.set_act(a, "pickup", x=sx, y=sy, item=it, qty=qty, left=1)
            if not it and pile:                        # no item named: take what lies there
                return self.set_act(a, "pickup", x=sx, y=sy, item=None, qty=999, left=1)
        return f"there is no {it or 'thing'} on the ground next to you"

    def start_give(self, a, act):
        other = self.w.by_name(act.get("target"))
        it = norm_item(act.get("item"))
        if not other or not other.alive or other.id == a.id:
            return "give to whom?"
        if dist(a.x, a.y, other.x, other.y) > 1:
            return self.walk_to(a, act, other) or f"{other.name} is not next to you and you cannot see them"
        raw = str(act.get("item") or "").strip().lower()
        if raw in BUILD or raw == "grave":
            return self.give_building(a, other, raw, *self.opt_xy(act))
        if not a.inventory.get(it):
            return f"you have no {it}"
        return self.set_act(a, "give", to=other.id, item=it, qty=as_int(act.get("qty"), 1, 1, 999), left=1)

    def give_building(self, a, other, kind, x=None, y=None):
        """Hand over something one has built: a sale, a gift, a dowry, a tribute."""
        w = self.w
        mine = [s for s in w.structures.values() if s.owner == a.id and s.kind == kind
                and ((s.x, s.y) == (x, y) if x is not None else True)]
        if not mine:
            return f"you own no {kind}" + (f" at ({x},{y})" if x is not None else "")
        s = min(mine, key=lambda s: dist(a.x, a.y, s.x, s.y))
        s.owner = other.id
        if s.access == "list":
            s.allow = [i for i in s.allow if i != other.id]
        self.ledger(a, other, "gave_building", f"you gave {other.name} your {kind} at ({s.x},{s.y})")
        self.ledger(other, a, "got_building", f"{a.name} gave you their {kind} at ({s.x},{s.y})")
        self.tell(other, f"{a.name} gave you their {kind} at ({s.x},{s.y}). It is yours now.")
        self.wake(other, f"{a.name} gave you something")
        self.event("give_building", f"{a.name} gave {other.name} their {kind} at ({s.x},{s.y})", a, other,
                   sid=s.id, what=kind, x=s.x, y=s.y)
        self.witnesses(a.x, a.y, f"{a.name} handed their {kind} at ({s.x},{s.y}) to {other.name}.",
                       exclude={a.id, other.id})
        return self.set_act(a, "wait", left=1, quiet=True)

    # ---- partners parting, heirs ----
    def start_part(self, a, act):
        w = self.w
        p = w.agents.get(a.partner) if a.partner is not None else None
        if not p:
            return "you have no partner"
        a.partner = None
        if p.partner == a.id:
            p.partner = None
        self.ledger(a, p, "parted", f"you parted from {p.name}")
        if p.alive:
            self.ledger(p, a, "parted", f"{a.name} parted from you")
            self.tell(p, f"{a.name} has parted from you; you are partners no longer.")
            self.wake(p, f"{a.name} parted from you")
        self.event("part", f"{a.name} parted from {p.name}", a, p)
        return self.set_act(a, "wait", left=1, quiet=True)

    def start_bequeath(self, a, act):
        w = self.w
        o = w.by_name(act.get("target"))
        if not o or not o.alive or o.id == a.id:
            return "name the living person who should inherit what you have built"
        a.heir = o.id
        self.ledger(a, o, "heir", f"you named {o.name} to inherit what you have built")
        if self.can_see(o, a.x, a.y):
            self.tell(o, f"{a.name} named you to inherit what they have built.")
            self.ledger(o, a, "heir_of", f"{a.name} named you to inherit what they have built")
        self.event("bequeath", f"{a.name} named {o.name} to inherit what they have built", a, o)
        return self.set_act(a, "wait", left=1, quiet=True)

    def start_attack(self, a, act):
        w = self.w
        if str(act.get("target") or "").strip().lower() in ("wolves", "wolf", "the wolves", "pack"):
            p = self.pack_near(a, 1)
            if not p:
                return "no wolves are next to you"
            return self.set_act(a, "fight_wolves", pack=p["id"], left=1)
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
        if not other or not other.alive or other.id == a.id:
            return "teach whom? they must be next to you"
        if dist(a.x, a.y, other.x, other.y) > 1:
            return self.walk_to(a, act, other) or f"{other.name} must be next to you, and you cannot see them"
        words = " ".join(str(act.get(k) or "") for k in ("item", "text", "choice")).lower()
        tech = next((t for t in a.know if t in words or t.rstrip("ing") in words or
                     (t == "smoking" and any(x in words for x in ("smok", "dry", "dried", "preserv")))), None)
        if tech:
            return self.set_act(a, "teach", to=other.id, technique=tech, left=1)
        rk = next((k for k in a.recipes if w.recipes.get(k) == prod), None)
        if not rk:
            return f"you do not know how to make {prod}"
        return self.set_act(a, "teach", to=other.id, recipe=rk, left=1)

    def start_mark(self, a, act):
        text = str(act.get("text") or "").strip()
        if not text:
            return "a sign needs words"
        return self.set_act(a, "mark", text=text[:200], left=1)

    # ---- techniques: things known how to do, taught or worked out, not made from pairs ----
    def learn(self, a, tech, how, teacher=None):
        if tech in a.know:
            return "done", ""
        a.know.append(tech)
        self.tell(a, how)
        if teacher is not None:
            self.wake(a, f"{teacher.name} taught you something")
            self.ledger(a, teacher, "taught_me", f"{teacher.name} taught you how to {TECHNIQUES[tech]}")
            self.ledger(teacher, a, "taught", f"you taught {a.name} how to {TECHNIQUES[tech]}")
            self.event("teach", f"{teacher.name} taught {a.name} how to {TECHNIQUES[tech]}", teacher, a, technique=tech)
            return "done", f"You taught {a.name} how to {TECHNIQUES[tech]}."
        first = not any(tech in o.know for o in self.w.living() if o.id != a.id)
        self.event("technique", f"{a.name} worked out how to {TECHNIQUES[tech]}", a, technique=tech, first=first)
        return "done", how

    def burning_fire(self, a, r):
        fires = [s for s in self.w.structures.values() if s.kind == "fire" and s.done and s.fuel > 0
                 and dist(a.x, a.y, s.x, s.y) <= r]
        return min(fires, key=lambda s: dist(a.x, a.y, s.x, s.y)) if fires else None

    def start_smoke(self, a, act):
        it = norm_item(act.get("item")) or item_in_text(act.get("text") or act.get("choice"))
        if it in (None, "", "food", "any"):
            it = next((k for k in ("fish", "meat", "berries") if a.inventory.get(k)), None)
        if it not in I.SMOKED:
            return "only fish, meat and berries can be smoked or dried"
        if not a.inventory.get(it):
            return f"you have no {it}"
        f = self.burning_fire(a, 1)
        if not f:
            far = self.burning_fire(a, self.w.sight(a))
            if not far:
                return "you need a burning fire beside you; build a fire and feed it wood"
            return self.set_act(a, "smoke", item=it, qty=as_int(act.get("qty"), 99, 1, 99),
                                left=as_int(act.get("qty"), 4, 1, 8), walk=[far.x, far.y, True])
        return self.set_act(a, "smoke", item=it, qty=as_int(act.get("qty"), 99, 1, 99), left=4)

    def do_smoke(self, a, act):
        walking = self.walk_first(a, act)
        if walking:
            return walking
        if not self.burning_fire(a, 1):
            return "fail", "There is no burning fire beside you."
        it, out = act["item"], I.SMOKED[act["item"]]
        act["left"] -= 1
        if "smoking" not in a.know:
            # without the knack the food only chars and is kept; now and then someone works it out
            if self.w.rng.random() < 0.05:                # rare: knowing how is worth something
                self.learn(a, "smoking", "As you worked at the fire, you worked out how to smoke and dry food so it keeps.")
            elif act["left"] <= 0:
                return "done", f"You held the {it} over the fire, but it only charred at the edges; you have not worked out how to make it keep. You still have it."
            else:
                return "go", ""
        n = min(4, a.inventory.get(it, 0), act["qty"] - act.get("done", 0))
        if n > 0:
            I.remove(a.inventory, it, n)
            I.add(a.inventory, out, n)
            act["done"] = act.get("done", 0) + n
            for o in self.w.living():               # someone beside you may pick up the knack by watching
                if o.id != a.id and "smoking" not in o.know and dist(a.x, a.y, o.x, o.y) <= 1 and self.w.rng.random() < 0.15:
                    self.learn(o, "smoking", f"Watching {a.name} at the fire, you saw how to smoke and dry food so it keeps.")
        if act["left"] <= 0 or not a.inventory.get(it) or act.get("done", 0) >= act["qty"]:
            done = act.get("done", 0)
            if done:
                self.event("smoke", f"{a.name} smoked {done} {it}" if it != "berries" else f"{a.name} dried {done} berries",
                           a, item=out, qty=done)
            return "done", f"You now have {done} {out.replace('_', ' ')}, which will keep most of a year." if done else "Nothing was smoked."
        return "go", ""

    # ---- partners ----
    def start_pledge(self, a, act):
        w = self.w
        other = w.by_name(act.get("target"))
        if not other or not other.alive or other.id == a.id:
            return "pledge yourself to whom?"
        if dist(a.x, a.y, other.x, other.y) > 1:
            return self.walk_to(a, act, other) or f"{other.name} must be next to you, and you cannot see them"
        if a.partner is not None and w.agents.get(a.partner) and w.agents[a.partner].alive:
            return f"you are already pledged to {w.agents[a.partner].name}"
        pid = w.new_id()
        w.proposals[pid] = {"id": pid, "kind": "pledge", "from": a.id, "to": other.id, "give": {}, "get": {},
                            "pg": {}, "pr": {}, "text": str(act.get("text") or "")[:200], "due_days": 0,
                            "made": w.tick, "expires": w.tick + 12}
        self.tell(other, f"{a.name} asks you to be partners for life (offer #{pid}): to share stores and shelters, "
                         f"and each to inherit from the other. Accept or refuse.")
        self.wake(other, f"{a.name} asked you to be partners")
        self.tell(a, f"You asked {other.name} to be your partner (#{pid}).")
        self.event("ask_pledge", f"{a.name} asked {other.name} to be partners", a, other, deal=pid)
        return self.set_act(a, "wait", left=1, quiet=True)

    def accept_pledge(self, a, other, p):
        w = self.w
        del w.proposals[p["id"]]
        for x in (a, other):
            if x.partner is not None and w.agents.get(x.partner) and w.agents[x.partner].alive:
                return f"{x.name} is already pledged to another"
        a.partner, other.partner = other.id, a.id
        self.ledger(a, other, "pledge", f"you and {other.name} pledged yourselves to each other")
        self.ledger(other, a, "pledge", f"you and {a.name} pledged yourselves to each other")
        self.tell(other, f"{a.name} accepted: you are partners now.")
        self.wake(other, f"{a.name} accepted your offer")
        self.event("pledge", f"{other.name} and {a.name} pledged themselves to each other", other, a)
        self.witnesses(a.x, a.y, f"{other.name} and {a.name} pledged themselves to each other.", exclude={a.id, other.id})
        return self.set_act(a, "wait", left=1, quiet=True)

    def start_do(self, a, act):
        text = str(act.get("text") or "").strip()
        if not text:
            return "say in text what you do"
        other = self.w.by_name(act.get("target")) if act.get("target") else None
        return self.set_act(a, "do", text=text[:300], to=other.id if other else None,
                            left=as_int(act.get("qty"), 1, 1, 6))

    # ---- stories, graves, places ----
    def start_tell_story(self, a, act):
        idx = as_int(act.get("id"))
        text = str(act.get("text") or "").strip()
        if idx is not None and 1 <= idx <= len(a.lore) and not text:
            origin, text, first = a.lore[idx - 1][0], a.lore[idx - 1][1], a.lore[idx - 1][2]
        elif text:
            same = next((l for l in a.lore if l[1] == text), None)
            origin, first = (same[0], same[2]) if same else (a.name, self.w.tick)
        else:
            return "tell a story in text, or retell one you know by its number as id"
        return self.set_act(a, "story", text=text[:500], origin=origin, first=first, left=2)

    def remember_story(self, o, origin, text, first, teller):
        if any(l[1] == text for l in o.lore):
            return
        o.lore.append([origin, text, first, teller])
        if len(o.lore) > 8:
            o.lore.pop(0)

    def do_story(self, a, act):
        w = self.w
        if act["left"] == 2:
            loud = 12 if a.inventory.get("drum") else 6
            heard = []
            for o in w.living():
                if o.id != a.id and dist(a.x, a.y, o.x, o.y) <= loud:
                    self.tell(o, f"{a.name} told a story: \"{act['text']}\"")
                    self.remember_story(o, act["origin"], act["text"], act["first"], a.name)
                    heard.append(o.id)
            self.remember_story(a, act["origin"], act["text"], act["first"], a.name)
            retold = act["origin"] != a.name
            self.event("story", f"{a.name} {'retold' if retold else 'told'} a story" + (f" first told by {act['origin']}" if retold else "")
                       + f": \"{act['text']}\"", a, words=act["text"], origin=act["origin"], heard=heard)
        act["left"] -= 1
        return ("go", "") if act["left"] > 0 else ("done", "You told your story.")

    # what one has seen or suffered of someone, as the listener will hear it ({t}: the teller)
    TELLABLE = {"robbed": "stole from {t}", "attacked": "attacked {t}", "forced": "took from {t} by force",
                "took_crop": "took from {t}'s farm", "broke": "broke promises to {t}", "killed_kin": "killed {t}'s kin",
                "smash": "damaged {t}'s things", "saw_steal": "stole, as {t} saw", "saw_attack": "attacked someone, as {t} saw",
                "saw_force": "took by force, as {t} saw", "saw_smash": "broke a building, as {t} saw"}
    TELLABLE_GOOD = {"kept": "kept promises to {t}", "gift_in": "gave {t} things", "taught_me": "taught {t}"}

    def tellable(self, a, o):
        """What a can truly tell of o from their own record: (wrongs, goods), each a list of phrases."""
        wrongs, goods = Counter(), Counter()
        for _, oid, k, _ in a.ledger:
            if oid == o.id:
                if k in self.TELLABLE:
                    wrongs[self.TELLABLE[k].format(t=a.name)] += 1
                elif k in self.TELLABLE_GOOD:
                    goods[self.TELLABLE_GOOD[k].format(t=a.name)] += 1
        say = lambda c: [p + (f" {n} times" if n > 1 else "") for p, n in c.items()]
        return say(wrongs), say(goods)

    def pass_on(self, a, name, to=None, whisper=False):
        """Speaking of someone, one passes on what one truly knows of them first-hand; those who
        hear remember who told them. Free, like speech."""
        o = self.w.by_name(name)
        if not o or o.id == a.id:
            return
        wrongs, goods = self.tellable(a, o)
        if not wrongs and not goods:
            self.tell(a, f"You have seen or suffered nothing of {o.name} to pass on; only your words were heard.")
            return
        what = ", ".join(wrongs + goods)
        t = self.w.by_name(to) if to else None
        if whisper and t and dist(a.x, a.y, t.x, t.y) <= 1:
            hearers = [t]
        else:
            loud = 12 if a.inventory.get("drum") else 6
            hearers = [x for x in self.w.living() if x.id != a.id and dist(a.x, a.y, x.x, x.y) <= loud]
        for x in hearers:
            if x.id == o.id:
                self.tell(x, f"{a.name} told what they know of you: {what}.")
                continue
            self.tell(x, f"{a.name} told you what they know of {o.name}: {what}.")
            for kind, said in (("heard_wrong", wrongs), ("heard_good", goods)):
                text = f"{a.name} told you they " + ", ".join(said)
                if said and not any(l[1] == o.id and l[2] == kind and l[3] == text for l in x.ledger):
                    self.ledger(x, o, kind, text)
        self.event("tell_of", f"{a.name} told what they know of {o.name}: {what}", a, o,
                   heard=[x.id for x in hearers], wrongs=len(wrongs), goods=len(goods))

    def start_bury(self, a, act):
        w = self.w
        spot = next(((a.x + dx, a.y + dy) for dx in (0, -1, 1) for dy in (0, -1, 1)
                     if key(a.x + dx, a.y + dy) in w.corpses), None)
        if not spot:
            return "there are no remains here or next to you"
        if w.structure_at(*spot):
            return "something already stands there"
        return self.set_act(a, "bury", x=spot[0], y=spot[1], text=str(act.get("text") or "").strip()[:200], left=2)

    def do_bury(self, a, act):
        w = self.w
        act["left"] -= 1
        if act["left"] > 0:
            return "go", ""
        k = key(act["x"], act["y"])
        c = w.corpses.pop(k, None)
        if not c:
            return "fail", "The remains are gone."
        s = Structure(id=w.new_id(), kind="grave", x=act["x"], y=act["y"], owner=a.id, hp=50, built=w.tick,
                      done=True, name=c[0], text=act["text"])
        w.structures[s.id] = s
        self.event("burial", f"{a.name} buried {c[0]}" + (f": \"{act['text']}\"" if act["text"] else ""), a,
                   x=act["x"], y=act["y"], dead=c[0], words=act["text"])
        self.witnesses(act["x"], act["y"], f"{a.name} buried {c[0]}.", exclude={a.id})
        return "done", f"You buried {c[0]}."

    def start_name_place(self, a, act):
        name = str(act.get("name") or act.get("text") or "").strip()[:40]
        if not name:
            return "give the place a name"
        return self.set_act(a, "name_place", name=name, left=1)

    def do_name_place(self, a, act):
        w = self.w
        old = next((p for p in w.places if dist(p[0], p[1], a.x, a.y) <= 1), None)
        if old:
            was = old[2]
            old[2], old[3], old[4] = act["name"], a.id, w.tick
            text = f"{a.name} renamed {was} to {act['name']}"
        else:
            w.places.append([a.x, a.y, act["name"], a.id, w.tick])
            text = f"{a.name} named the place at ({a.x},{a.y}) {act['name']}"
        self.event("name_place", text, a, x=a.x, y=a.y, name=act["name"])
        self.witnesses(a.x, a.y, f"{a.name} called this place {act['name']}.", exclude={a.id})
        return "done", f"You named this place {act['name']}."

    def start_set_access(self, a, act):
        w = self.w
        x, y = self.opt_xy(act)
        cands = [s for s in w.structures.values() if s.owner == a.id and s.kind in ("store", "shelter", "wall", "farm")
                 and (dist(a.x, a.y, s.x, s.y) <= 1 if x is None else (s.x, s.y) == (x, y))]
        if not cands:
            return "you own no store, shelter, wall or farm there"
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
        if p["kind"] == "pledge":
            return self.accept_pledge(a, other, p)
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
            return self.walk_to(a, act, other) or f"{other.name} must be next to you, and you cannot see them"
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
                if re.search(rf"\b{re.escape(o.name)}\b", text, re.I):
                    self.speech_wake(o, f"{a.name} spoke to you")
        if target and target.id not in heard and target.id != a.id:
            self.tell(a, f"{target.name} is too far away to hear you.")
        self.event("say", f"{a.name} said{' to ' + target.name if target else ''}: \"{text}\"", a, target,
                   words=text, heard=heard)

    def speech_wake(self, o, reason):
        gap = self.cfg["mind"]["speech_wake_gap"]
        if self.w.tick - o.last_speech_wake >= gap and self.w.tick - o.last_decided >= 1:
            o.last_speech_wake = self.w.tick
            self.wake(o, reason)


    # ---- skill ----
    SKILL_WORD = {"gather": "gathering", "fish": "fishing", "hunt": "hunting", "build": "building",
                  "fight": "fighting", "craft": "making things"}
    SKILL_ROLE = {"gather": "gatherer", "fish": "fisher", "hunt": "hunter", "build": "builder",
                  "fight": "fighter", "craft": "maker"}

    @staticmethod
    def skill_level(v):
        return "masterly" if v >= 3.5 else "good" if v >= 2 else "some" if v >= 1 else ""

    def skill(self, a, k):
        return a.skills.get(k, 0.0)

    def practice(self, a, k, amount=1.0):
        s = a.skills.get(k, 0.0)
        new = round(min(5.0, s + 0.12 * amount * (1 - s / 5.5)), 3)
        a.skills[k] = new
        before, after = self.skill_level(s), self.skill_level(new)
        if after != before:
            self.tell(a, f"You have become {after} at {self.SKILL_WORD[k]}.")
            if after in ("good", "masterly"):
                self.event("skill", f"{a.name} became {after} at {self.SKILL_WORD[k]}", a, skill=k, level=after)

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

    def full_note(self, a):
        """Why nothing more can be carried, in words that say what to do about it."""
        heavy = sorted(((I.ITEMS[k]["w"] * n, k, n) for k, n in a.inventory.items() if n), reverse=True)[:2]
        what = " and ".join(f"{n} {k} weigh {wt:g}" for wt, k, n in heavy)
        return (f"you carry all you can (load {a.carrying():.1f} of {a.capacity(self.cfg):.0f}"
                + (f"; {what}" if what else "") + "); drop, put away or give something first")

    @staticmethod
    def ate_note(act):
        return f" (and ate {act['ate']} as you picked)" if act.get("ate") else ""

    def pick_food(self, a, item, n):
        """What a person picks they keep if they can carry it; a hungry person eats on the
        spot what they cannot carry. Returns (eaten, kept)."""
        c = self.cfg["agent"]
        food = I.ITEMS[item]["food"]
        kept = self.room(a, item, n)
        ate = 0
        while food and ate < n - kept and a.satiety < c["max_satiety"] - 4:
            a.satiety = min(c["max_satiety"], a.satiety + food)
            ate += 1
        return ate, kept

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
        if n and item != "grain" and w.rng.random() < self.skill(a, "gather") / 10:
            n += 1
        if item == "berries":
            n = min(n, w.bushes[key(x, y)]["b"])
        elif item == "grain":
            n = min(n, w.structure_at(x, y).inventory.get("grain", 0))
        ate, kept = self.pick_food(a, item, n)
        hungry = I.ITEMS[item]["food"] and a.satiety < self.cfg["agent"]["max_satiety"] - 4
        if ate + kept == 0 and self.room(a, item, 1) == 0 and not hungry:
            return "done", f"You gathered {act.get('got', 0)} {item}{self.ate_note(act)}, and can take no more: {self.full_note(a)}."
        if ate:
            act["ate"] = act.get("ate", 0) + ate
        n = ate + kept
        if item == "berries":
            b = w.bushes[key(x, y)]
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
            if n and not w.may_use(a, farm):
                # anyone can gather from a ripe farm, but from one not open to you it is taking,
                # and the owner and whoever sees it remember
                o = w.agents.get(farm.owner)
                if o and o.alive and self.can_see(o, x, y):
                    self.tell(o, f"{a.name} is taking grain from your farm at ({x},{y}).")
                    self.wake(o, f"{a.name} is taking from your farm")
                    self.ledger(o, a, "took_crop", f"{a.name} took {n} grain from your farm")
                if o:
                    self.ledger(a, o, "took_crop_them", f"you took {n} grain from {o.name}'s farm")
                    for oid in self.witnesses(x, y, f"You saw {a.name} take grain from {o.name}'s farm.",
                                              exclude={a.id, o.id}, chance=0 if w.is_night() else 0.5):
                        self.ledger(w.agents[oid], a, "saw_steal", f"you saw {a.name} take grain from {o.name}'s farm")
                self.event("take_crop", f"{a.name} took {n} grain from {o.name if o else 'someone'}'s farm", a, o,
                           qty=n, x=x, y=y)
        if item in ("fibre", "berries") and n:
            chance = r["seed_chance"] if item == "fibre" else r.get("seed_chance_berries", 0)
            if w.season() in ("summer", "autumn") and w.rng.random() < chance:
                I.add(a.inventory, "seeds", 1)
                act["seeds"] = act.get("seeds", 0) + 1
        I.add(a.inventory, item, n - ate)
        act["got"] = act.get("got", 0) + n - ate
        if n:
            self.practice(a, "gather", 0.5)
        act["left"] -= 1
        if act["left"] <= 0 or act["got"] >= act.get("want", 99):
            extra = f" and {act['seeds']} seeds" if act.get("seeds") else ""
            return "done", f"You gathered {act['got']} {item}{extra}{self.ate_note(act)}."
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
        p = min(0.9, p * (1 + 0.15 * self.skill(a, "fish")))
        self.practice(a, "fish", 0.4)
        if w.rng.random() < p:
            ate, kept = self.pick_food(a, "fish", 1)
            I.add(a.inventory, "fish", kept)
            act["got"] = act.get("got", 0) + kept
            act["ate"] = act.get("ate", 0) + ate
            if not ate + kept:
                return "done", f"You caught a fish and could not keep it: {self.full_note(a)}."
        act["left"] -= 1
        if act["left"] <= 0:
            return "done", f"You fished and caught {act.get('got', 0)}{self.ate_note(act).replace('picked', 'caught them')}."
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
            if p > 0:
                p = min(0.95, p + 0.03 * sum(self.skill(a, "hunt") for a in hunters))
            for a in hunters:
                self.practice(a, "hunt", 0.3)
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
                ate, room = self.pick_food(a, "meat", got)
                I.add(a.inventory, "meat", room)
                if got > ate + room:
                    self.drop_pile(a.x, a.y, {"meat": got - ate - room})
                a.hunts += 1
                others = [x.name for x in hunters if x.id != a.id]
                msg = f"The hunt succeeded! You got {got} meat" + (f", hunting with {', '.join(others)}." if others else ".")
                if ate:
                    msg += f" You ate {ate} there and then."
                if got > ate + room:
                    msg += f" You could not carry {got - ate - room}; it lies on the ground."
                a.activity["caught"] = msg
                for o in hunters:
                    if o.id != a.id:
                        self.ledger(a, o, "hunt", f"hunted with {o.name} and got {got} meat")
            self.drop_pile(h["x"], h["y"], {"hide": 1, "bone": 1})
            self.event("hunt", f"{names} killed a deer ({k} hunter{'s' if k > 1 else ''})", hunters[0],
                       hunters=[x.id for x in hunters], herd=h["id"])
            self.witnesses(h["x"], h["y"], f"{names} brought down a deer.", exclude={x.id for x in hunters})

    def eat_now(self, a, item, qty):
        pile = None
        if item in (None, "", "food", "any"):
            foods = sorted((k for k in a.inventory if I.ITEMS[k]["food"] > 0), key=lambda k: I.ITEMS[k]["spoil"], reverse=True)
            if foods:
                item = foods[0]
            else:
                ground = self.food_at_feet(a)
                if not ground:
                    return
                pile, item = ground
        elif item not in a.inventory and item in I.ITEMS:
            ground = self.food_at_feet(a, item)
            if ground:
                pile = ground[0]
        if (item not in a.inventory and not pile) or item not in I.ITEMS or (I.ITEMS[item]["food"] <= 0 and item != "poultice"):
            self.tell(a, f"You could not eat {item}: you have none, and there is none on the ground beside you, or it is not food.")
            return
        status, msg = self.do_eat(a, {"item": item, "qty": qty, "pile": pile})
        if msg:
            self.tell(a, msg)

    def eat_when_hungry(self, a):
        """A hungry person carrying food eats it without stopping to think, first what
        spoils soonest, until fed. Only hunger with nothing to eat needs a decision."""
        c = self.cfg["agent"]
        before = a.satiety
        eaten = []
        while a.satiety < c["max_satiety"] - 4:
            foods = sorted((k for k in a.inventory if I.ITEMS[k]["food"] > 0 and a.inventory[k] > 0
                            and a.satiety + I.ITEMS[k]["food"] <= c["max_satiety"]),
                           key=lambda k: (-I.ITEMS[k]["spoil"], -I.ITEMS[k]["food"]))
            if not foods:
                break
            k = foods[0]
            I.remove(a.inventory, k, 1)
            a.satiety = min(c["max_satiety"], a.satiety + I.ITEMS[k]["food"])
            eaten.append(k)
        if not eaten:
            return False
        what = ", ".join(f"{n} {k}" for k, n in sorted({k: eaten.count(k) for k in eaten}.items()))
        self.tell(a, f"You grew hungry and ate {what} from what you carry.")
        self.event("eat", f"{a.name} ate {what}", a, auto=True)
        return a.satiety > before

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
        src = a.inventory
        if act.get("pile"):                            # food lying on the ground beside one
            src = self.w.piles.get(act["pile"]) or {}
        while eaten < act["qty"] and src.get(it) and a.satiety + info["food"] <= c["max_satiety"] + max(0, info["food"] - 2):
            I.remove(src, it, 1)
            a.satiety = min(c["max_satiety"], a.satiety + info["food"])
            eaten += 1
        if act.get("pile") and not src:
            self.w.piles.pop(act["pile"], None)
        if eaten == 0:
            return "done", "You are too full to eat." if src.get(it) else f"There is no {it} there now."
        where = " from the ground" if act.get("pile") else ""
        return "done", f"You ate {eaten} {it}{where}. {self.hunger_word(a).capitalize()}."

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
        self.practice(a, "craft", 1.0)
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
        s.progress += 1 + (1 if w.rng.random() < self.skill(a, "build") / 8 else 0)
        self.practice(a, "build", 0.6)
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
        seed = act.get("seed", "seeds")
        n = I.remove(a.inventory, seed, act["qty"])
        farm.seeds, farm.planted, farm.progress = n, w.tick, 0
        what = "seeds" if seed == "seeds" else "grain"
        self.event("plant", f"{a.name} sowed {n} {what} at ({farm.x},{farm.y})", a, sid=farm.id, qty=n, seed=seed)
        return "done", f"You sowed {n} {what}. The crop should be ripe in about {self.cfg['resources']['farm_grow_ticks'] // w.tpd()} days, if winter does not stop it."

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
        self.store_news(a, s)
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
        self.store_news(a, s)
        it = act["item"]
        ate, kept = self.pick_food(a, it, min(act["qty"], s.inventory.get(it, 0)))
        n = ate + kept
        if n <= 0:
            return "fail", f"You cannot carry {it}: {self.full_note(a)}." if s.inventory.get(it) else f"There is no {it} in the store now."
        I.remove(s.inventory, it, n)
        I.add(a.inventory, it, kept)
        self.event("take_store", f"{a.name} took {n} {it} from the store at ({s.x},{s.y})", a, sid=s.id, item=it,
                   qty=n, owner=s.owner, ate=ate)
        owner = w.agents.get(s.owner)
        if owner and owner.id != a.id and owner.alive:
            self.ledger(owner, a, "store_out", f"{a.name} took {n} {it} from your store at ({s.x},{s.y})")
            if self.can_see(owner, s.x, s.y):
                self.tell(owner, f"{a.name} took {n} {it} from your store.")
        self.witnesses(s.x, s.y, f"{a.name} took {it} from the store at ({s.x},{s.y}).", exclude={a.id}, chance=0.5)
        return "done", f"You took {n} {it} from the store" + (f" and ate {ate} of it there." if ate else ".")

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
        if it is None:                                 # everything there, as much as can be carried
            got = []
            for thing in sorted(pile, key=lambda t: -I.ITEMS[t]["food"]):
                ate, n = self.pick_food(a, thing, pile.get(thing, 0))
                if ate + n > 0:
                    I.remove(pile, thing, ate + n)
                    I.add(a.inventory, thing, n)
                    got.append(f"{ate + n} {thing}" + (f" (eating {ate} there)" if ate else ""))
            if not pile:
                w.piles.pop(k, None)
            if not got:
                return "fail", f"You could not pick any of it up: {self.full_note(a)}." if pile else "There is nothing there now."
            self.event("pickup", f"{a.name} picked up {', '.join(got)} at ({act['x']},{act['y']})", a)
            return "done", f"You picked up {', '.join(got)}."
        ate, n = self.pick_food(a, it, min(act["qty"], pile.get(it, 0)))
        if ate + n <= 0:
            return "fail", f"You cannot carry {it}: {self.full_note(a)}." if pile.get(it) else f"There is no {it} there now."
        I.remove(pile, it, ate + n)
        if not pile:
            del w.piles[k]
        I.add(a.inventory, it, n)
        self.event("pickup", f"{a.name} picked up {ate + n} {it} at ({act['x']},{act['y']})", a, item=it, qty=ate + n,
                   ate=ate)
        if ate:
            return "done", f"You ate {ate} {it} there" + (f" and picked up {n}." if n else ".")
        return "done", f"You picked up {n} {it}."

    def backers(self, a, v):
        """Who stands by a against v: people next to v who are with a (a group they share,
        partner, parent or child) or who came after v on purpose (following v)."""
        w = self.w
        out = []
        for o in w.living():
            if o.id in (a.id, v.id) or dist(o.x, o.y, v.x, v.y) > 1:
                continue
            with_a = (set(o.groups) & set(a.groups) or o.id == a.partner or o.id in a.children
                      or o.id in a.parents)
            after_v = o.activity and o.activity.get("follow") == v.id
            if with_a or after_v:
                out.append(o)
        return out

    def do_steal(self, a, act):
        w = self.w
        v = w.agents.get(act["victim"])
        if not v or not v.alive or dist(a.x, a.y, v.x, v.y) > 1:
            return "fail", "They slipped out of reach."
        it = act.get("item")
        if it in (None, "", "food", "any"):
            cands = [k for k in v.inventory if (I.ITEMS[k]["food"] > 0 or it == "any")]
            it = w.rng.choice(sorted(cands)) if cands else None
        mine, theirs = self.backers(a, v), self.backers(v, a)
        if mine and len(mine) + 1 > len(theirs) + 1:
            return self.take_by_force(a, v, it, act, mine, theirs)
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
            for oid in self.witnesses(a.x, a.y, f"You saw {a.name} steal from {v.name}.", exclude={a.id, v.id},
                                      chance=0 if w.is_night() else 0.5):
                self.ledger(w.agents[oid], a, "saw_steal", f"you saw {a.name} steal {it} from {v.name}")
            self.ledger(a, v, "stole", f"you stole {n} {it} from {v.name}" + ("" if noticed else " unseen"))
            return "done", f"You stole {n} {it} from {v.name}." + ("" if noticed else " They did not notice.")
        self.tell(v, f"{a.name} tried to steal from you and failed.")
        self.ledger(v, a, "robbed", f"{a.name} tried to steal from you")
        self.wake(v, f"{a.name} tried to rob you")
        self.event("steal_fail", f"{a.name} tried to steal from {v.name} and was caught", a, v)
        for oid in self.witnesses(a.x, a.y, f"You saw {a.name} try to steal from {v.name}.", exclude={a.id, v.id}):
            self.ledger(w.agents[oid], a, "saw_steal", f"you saw {a.name} try to steal from {v.name}")
        what = "" if it else " They had nothing like that."
        return "done", f"You tried to steal from {v.name} and they caught you.{what}"

    def take_by_force(self, a, v, it, act, mine, theirs):
        """Several standing together take openly: it seldom fails, and everyone sees.
        Whether it is justice or robbery is for the people to say; the record says who."""
        w = self.w
        names = ", ".join(o.name for o in mine)
        if not it or not v.inventory.get(it):
            self.tell(v, f"{a.name}, with {names} beside them, came to take from you, but you had nothing like that.")
            return "done", f"With {names} beside you, you went to take from {v.name}, but they had nothing like that."
        if w.rng.random() > 0.9 - 0.15 * len(theirs):
            self.tell(v, f"{a.name}, with {names} beside them, tried to take your {it} by force; you held on.")
            self.ledger(v, a, "forced", f"{a.name} and {names} tried to take your {it} by force")
            self.wake(v, f"{a.name} tried to take from you by force")
            return "done", f"{v.name} held on to their {it}."
        n = I.remove(v.inventory, it, min(max(act["qty"], 3), 6, self.room(a, it, 6)))
        I.add(a.inventory, it, n)
        self.tell(v, f"{a.name}, with {names} beside them, took {n} {it} from you by force.")
        self.ledger(v, a, "forced", f"{a.name}, backed by {names}, took {n} {it} from you by force")
        self.ledger(a, v, "forced_them", f"you, backed by {names}, took {n} {it} from {v.name} by force")
        for o in mine:
            self.ledger(o, v, "forced_them", f"you stood with {a.name} as they took {n} {it} from {v.name}")
        self.wake(v, f"{a.name} took from you by force")
        self.event("seize", f"{a.name}, backed by {names}, took {n} {it} from {v.name} by force", a, v,
                   item=it, qty=n, backers=[o.id for o in mine])
        for oid in self.witnesses(a.x, a.y, f"You saw {a.name}, backed by {names}, take {n} {it} from {v.name} by force.",
                                  exclude={a.id, v.id} | {o.id for o in mine}):
            self.ledger(w.agents[oid], a, "saw_force", f"you saw {a.name} and {names} take {it} from {v.name} by force")
        return "done", f"Backed by {names}, you took {n} {it} from {v.name}."

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
        d = c["base_damage"] + a.strength + int(self.skill(a, "fight") / 2.5)
        self.practice(a, "fight", 1.0)
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
        for oid in self.witnesses(a.x, a.y, f"{a.name} attacked {v.name}!", exclude={a.id, v.id}):
            self.ledger(self.w.agents[oid], a, "saw_attack", f"you saw {a.name} attack {v.name}")
        msg = f"You struck {v.name} ({d} damage)" + (f" and took {back} in return." if back else ".")
        if v.health <= 0:
            self.kill(v, f"killed by {a.name}", a)
            msg += f" {v.name} is dead."
        if a.health <= 0:
            self.kill(a, f"died fighting {v.name}", v)
        return "done", msg

    def do_fight_wolves(self, a, act):
        p = next((p for p in self.w.wolves if p["id"] == act["pack"]), None)
        if not p or dist(a.x, a.y, p["x"], p["y"]) > 1:
            return "fail", "The wolves are no longer next to you."
        return "done", self.strike_wolves(a, p)

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
        if not act.get("witnessed") and owner and owner.id != a.id:
            act["witnessed"] = True             # once per breaking, not each blow
            for oid in self.witnesses(s.x, s.y, f"You saw {a.name} break at {owner.name}'s {s.kind}.",
                                      exclude={a.id, owner.id}):
                self.ledger(w.agents[oid], a, "saw_smash", f"you saw {a.name} break at {owner.name}'s {s.kind}")
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
        if act.get("technique"):
            t = act["technique"]
            return self.learn(o, t, f"{a.name} taught you how to {TECHNIQUES[t]}.", a)
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
            self.spoil(a.inventory, 0.5 if a.inventory.get("pot") else 1.0, a.rot)
            if a.pregnant and w.tick >= a.pregnant["due"]:
                self.birth(a)

    def spoil(self, inv, factor, into=None):
        """Things go bad, each on its own chance. What was lost is added to `into`
        (so the owner can be told) and its food worth to the day's tally."""
        rng = self.w.rng
        for k in list(inv):
            p = I.ITEMS[k]["spoil"] * factor
            if p <= 0:
                continue
            n = inv[k]
            lost = sum(1 for _ in range(n) if rng.random() < p)
            if lost:
                I.remove(inv, k, lost)
                self.w.rot_worth += lost * I.ITEMS[k]["food"]
                if into is not None:
                    into[k] = into.get(k, 0) + lost

    @staticmethod
    def rot_text(lost):
        return ", ".join(f"{n} {k.replace('_', ' ')}" for k, n in sorted(lost.items()))

    def tell_rot(self):
        """Once a day, people learn what went bad: what they carried, and what sat in
        their stores if they can see them. A store's losses are otherwise told to the
        next person who uses it."""
        w = self.w
        for a in w.living():
            if a.rot:
                self.tell(a, f"Since yesterday, some of what you carry went bad: {self.rot_text(a.rot)}.")
                a.rot = {}
        for s in w.structures.values():
            if s.kind == "store" and s.rotted:
                o = w.agents.get(s.owner)
                if o and o.alive and self.can_see(o, s.x, s.y):
                    self.tell(o, f"In your store at ({s.x},{s.y}), some things went bad: {self.rot_text(s.rotted)}.")
                    s.rotted = {}

    def store_news(self, a, s):
        if s.rotted:
            self.tell(a, f"While they sat in the store at ({s.x},{s.y}), some things went bad: {self.rot_text(s.rotted)}.")
            s.rotted = {}

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
                self.event("herd_leaves", f"The last deer of a herd was lost from sight at ({h['x']},{h['y']})",
                           x=h["x"], y=h["y"])
        w.herds = [h for h in w.herds if h["size"] > 0]
        if season_start and len(w.herds) < self.cfg["world"]["herds"]:
            self.herd_arrives()
        # snares
        for k, owner in list(w.snares.items()):
            if w.rng.random() < r["snare_chance"] and w.piles.get(k, {}).get("meat", 0) < 3:
                x, y = unkey(k)
                self.drop_pile(x, y, {"meat": 1})
        # piles spoil on the ground, twice as fast; fibre, hides and wood left out weather away
        weather = r.get("weather", {}) if day_start else {}
        for k in list(w.piles):
            self.spoil(w.piles[k], 2.0)
            for it, p in weather.items():
                n = w.piles[k].get(it, 0)
                lost = sum(1 for _ in range(n) if w.rng.random() < p)
                if lost:
                    I.remove(w.piles[k], it, lost)
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
        self.event("herd_arrives", f"A deer herd came out of the far grass at ({x},{y})", x=x, y=y)

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
                self.spoil(s.inventory, 0.4, s.rotted)
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
        # strangers come more often to a land that has emptied (as seldom as every
        # arrival_every_days when nearly full, as often as a quarter of that when few are
        # left), and to a larger land in proportion to the length of its edge
        every = cw["arrival_every_days"] * max(0.25, pop / cw["arrival_below"]) * 24 / max(24, w.w, w.h)
        if pop < cw["arrival_below"] and w.rng.random() < 1 / (every * w.tpd()):
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
        self.tell(a, "You have always lived alone in the wild reaches of the land, apart from everyone. "
                     "Now you have come down to where others live, carrying little.")
        self.wake(a, "you have come down from the wilds to where people live")
        self.event("arrive", f"{a.name}, who had always lived alone in the wilds, came among the others at ({x},{y})",
                   a, x=x, y=y)
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
        for who, text in child.teachings:
            self.remember_story(child, who, text, w.tick, who)
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
        a.routine = []
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
        partner = w.agents.get(a.partner) if a.partner is not None else None
        partner = partner if partner is not None and partner.alive else None
        named = w.agents.get(a.heir) if a.heir is not None else None
        named = named if named is not None and named.alive else None
        if partner:
            self.tell(partner, f"Your partner {a.name} has died ({cause}).")
            self.wake(partner, f"your partner {a.name} died")
        for s in w.structures.values():
            if s.owner == a.id:
                heir = named or partner or next((w.agents[c] for c in a.children if w.agents[c].alive), None)
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
                if by is not None and by.id != o.id:
                    self.ledger(o, by, "killed_kin", f"{by.name} killed your kin {a.name}")
        if partner and by is not None and by.id != partner.id:
            self.ledger(partner, by, "killed_kin", f"{by.name} killed your partner {a.name}")
        for k in list(w.snares):
            if w.snares[k] == a.id:
                w.snares[k] = -1

    def remember_places(self, a):
        """What a person has seen stays with them: bushes, buildings, graves, named places."""
        w = self.w
        r = w.sight(a)
        for k, b in w.bushes.items():
            x, y = unkey(k)
            if dist(a.x, a.y, x, y) <= r:
                if b["b"] >= 2:
                    a.known[k] = ["bush", f"berry bush ({b['b']} berries then)", w.tick]
                else:
                    a.known.pop(k, None)
        for s in w.structures.values():
            if dist(a.x, a.y, s.x, s.y) <= r and s.done:
                o = w.agents.get(s.owner)
                label = (f"the grave of {s.name}" if s.kind == "grave" else
                         f"monument {s.name}".strip() if s.kind == "monument" else
                         f"{'your' if s.owner == a.id else (o.name + chr(39) + 's') if o else 'an abandoned'} {s.kind}")
                a.known[key(s.x, s.y)] = ["structure", label, w.tick]
        for x, y, name, _, _ in w.places:
            if dist(a.x, a.y, x, y) <= r:
                a.known[key(x, y)] = ["place", name, w.tick]
        for k in list(a.known):
            if k in w.bushes or w.structure_at(*unkey(k)) or any(key(p[0], p[1]) == k for p in w.places):
                continue
            if a.known[k][0] != "place":
                del a.known[k]        # gone, and they will find out when they get there
        if len(a.known) > 80:
            for k in sorted(a.known, key=lambda k: a.known[k][2])[:len(a.known) - 80]:
                del a.known[k]

    # ---- wolves ----
    def spawn_wolves(self):
        w = self.w
        r = self.cfg["resources"]
        forest = [(x, y) for y in range(w.h) for x in range(w.w) if w.t(x, y) == FOREST
                  and all(dist(x, y, a.x, a.y) > 6 for a in w.living())]
        if not forest:
            return
        x, y = w.rng.choice(forest)
        lo, hi = r["wolf_pack_size"]
        size = w.rng.randint(lo, hi)
        pack = {"id": w.new_id(), "x": x, "y": y, "size": size, "hp": size * r["wolf_hp"], "hunger": 0}
        w.wolves.append(pack)
        self.event("wolves_come", f"A pack of {size} wolves came down out of the deep forest at ({x},{y})", x=x, y=y)

    def pack_near(self, a, r=1):
        return next((p for p in self.w.wolves if dist(a.x, a.y, p["x"], p["y"]) <= r), None)

    def wolves_tick(self):
        w = self.w
        r = self.cfg["resources"]
        night = w.is_night()
        fires = [s for s in w.structures.values() if s.kind == "fire" and s.done and s.fuel > 0]
        for p in list(w.wolves):
            p["hunger"] += 2 if w.season() == "winter" else 1
            living = w.living()

            def alone(a):
                return (not any(o.id != a.id and dist(o.x, o.y, a.x, a.y) <= 1 for o in living)
                        and not any(dist(f.x, f.y, a.x, a.y) <= 2 for f in fires))
            herd = min((h for h in w.herds if h["size"] > 0), key=lambda h: dist(h["x"], h["y"], p["x"], p["y"]), default=None)
            deer_near = herd is not None and dist(herd["x"], herd["y"], p["x"], p["y"]) <= 8
            if not night and not (deer_near and p["hunger"] > 12) and (w.tick + p["id"]) % 2:
                continue
            hungry = p["hunger"] > 12
            bold = not deer_near and ((night and p["hunger"] > 24) or p["hunger"] > 96)
            prey = [a for a in living if dist(a.x, a.y, p["x"], p["y"]) <= 5 and alone(a) and bold]
            near_fire = any(dist(f.x, f.y, p["x"], p["y"]) <= 2 for f in fires)
            crowd = sum(1 for a in living if dist(a.x, a.y, p["x"], p["y"]) <= 1)
            if near_fire or crowd >= 2:
                tx, ty = p["x"] + w.rng.choice([-2, 2]), p["y"] + w.rng.choice([-2, 2])     # back away
            elif hungry and deer_near:
                if dist(herd["x"], herd["y"], p["x"], p["y"]) <= 1:
                    if w.rng.random() < 0.3:
                        herd["size"] -= 1
                        p["hunger"] = 0
                        self.event("wolves_hunt", f"Wolves brought down a deer at ({herd['x']},{herd['y']})",
                                   x=herd["x"], y=herd["y"])
                    continue
                tx, ty = herd["x"], herd["y"]
            elif prey:
                v = min(prey, key=lambda a: dist(a.x, a.y, p["x"], p["y"]))
                if dist(v.x, v.y, p["x"], p["y"]) <= 1:
                    if w.rng.random() < r["wolf_bite_chance"]:
                        d = r["wolf_damage"] + (1 if night else 0)
                        v.health -= d
                        self.tell(v, f"Wolves are on you! You lost {d} health.")
                        self.ledger(v, None, "wolves", f"wolves attacked you ({d} damage)")
                        self.wake(v, "wolves attacked you")
                        self.event("wolf_attack", f"Wolves attacked {v.name} ({d} damage)", v, dmg=d, x=v.x, y=v.y)
                        self.witnesses(v.x, v.y, f"Wolves attacked {v.name}!", exclude={v.id})
                        if v.health <= 0:
                            self.kill(v, "killed by wolves")
                            p["hunger"] = 0
                    continue
                tx, ty = v.x, v.y
            else:
                tx, ty = p["x"] + w.rng.randint(-1, 1), p["y"] + w.rng.randint(-1, 1)
            dx = (tx > p["x"]) - (tx < p["x"])
            dy = (ty > p["y"]) - (ty < p["y"])
            nx, ny = p["x"] + dx, p["y"] + dy
            if w.passable(nx, ny) and not w.structure_at(nx, ny):
                p["x"], p["y"] = nx, ny
        # packs come back out of the deep forest at the turn of a season
        if w.hour() == 0 and w.day() % self.cfg["world"]["days_per_season"] == 0 and w.day() > 0 \
                and len(w.wolves) < r["wolf_packs"]:
            self.spawn_wolves()

    def strike_wolves(self, a, pack):
        """A person strikes the pack. Returns a message."""
        w = self.w
        r = self.cfg["resources"]
        d = self.damage(a, a)
        before = -(-pack["hp"] // r["wolf_hp"])
        pack["hp"] -= d
        a.health -= 1
        after = max(0, -(-pack["hp"] // r["wolf_hp"]))
        msg = f"You struck at the wolves ({d}) and were bitten (1)."
        if after < before:
            pack["size"] = after
            self.drop_pile(pack["x"], pack["y"], {"meat": 3 * (before - after), "hide": before - after})
            self.event("wolf_killed", f"{a.name} killed a wolf", a, x=pack["x"], y=pack["y"])
            self.witnesses(a.x, a.y, f"{a.name} killed a wolf.", exclude={a.id})
            msg += " A wolf is dead; its meat and hide lie on the ground."
        if pack["size"] <= 1:
            if pack in w.wolves:
                w.wolves.remove(pack)
            self.event("wolves_flee", f"The wolves fled into the deep forest from {a.name}", a)
            msg += " The rest of the pack fled into the deep forest."
        if a.health <= 0:
            self.kill(a, "killed by wolves")
        return msg

    def perceive(self):
        """Notice new faces and crossing hunger/health lines, and each dawn what went bad."""
        w = self.w
        if w.hour() == 0:
            self.tell_rot()
        quiet = self.cfg["mind"]["quiet_ticks"]
        living = w.living()
        for a in living:
            if (w.tick + a.id) % 3 == 0:
                self.remember_places(a)
            p = self.pack_near(a, w.sight(a))
            if p and a.seen.get(f"w{p['id']}", -999) < w.tick - w.tpd():
                self.wake(a, "you see wolves")
            if p:
                a.seen[f"w{p['id']}"] = w.tick
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
            if hb > a.hunger_band and self.eat_when_hungry(a):
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
        asked = {a.id for a in ask}
        for a in ask:
            self.apply_decision(a, decisions.get(a.id))
        for aid in sorted(set(decisions) - asked):          # a late answer for someone not asking now
            a = w.agents.get(aid)
            if a is not None and a.alive:
                self.apply_decision(a, decisions[aid])
        self.step_activities()
        self.step_world()
        return ask
