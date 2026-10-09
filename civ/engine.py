"""The world's rules, hour by hour. Minds choose intentions (a goal and a plan of steps); the
executor (acts.py) carries the steps out for everyone alike; the systems here keep bodies, land,
animals, farms, workshops and knowledge moving. Nothing here chooses for anyone."""
import json
import heapq
import math

from .content import TERRAIN, DEPOSITS, WILD, TAME, BUILDINGS, CRAFTS, RECIPES, PREDATORS
from .content import items as I
from .content.crafts import tool_options
from .names import group_rules
from .acts import mend_text
from .world import key, unkey, dist, direction, TPD, TPY, DPS
from .acts import Acts, WRONGS, FIRST_HAND
from .society import Society


class Log:
    """Where events go: a list kept in memory (and written out by run.py)."""
    def __init__(self):
        self.events = []

    def write(self, ev):
        self.events.append(ev)



# what fields and wild plants bear in a region's year, against an ordinary one (grand world)
YEAR_BEARS = {"good": 1.15, "lean": 0.7, "hard": 0.4, "": 1.0}

# deposits worth remembering and telling of: what is rare and far
RARE = {"clay", "flint", "salt", "copper_ore", "tin_ore", "iron_ore", "bog_iron", "limestone", "gold", "flax", "herbs"}


def _num(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


class Engine(Acts, Society):
    def __init__(self, world, log=None):
        self.w = world
        self.log = log or Log()
        self.watch = {}             # pid -> [(craft, tick)] seen practised beside them this hour
        self.refused = {}           # pid -> [(tick, step, why)]: what each could not do lately (not saved)
        self.unreachable = {}       # pid -> {key: tick}: places found to be out of reach (not saved)
        self.heard = {}             # pid -> [(tick, speaker id, words, to them)]: lately heard (not saved)
        self.tidy_groups()

    def tidy_groups(self):
        """Worlds saved before c43 kept the dead in their groups (and dead leaders at their head):
        take them out quietly, as death now does."""
        w = self.w
        for g in w.groups.values():
            if g.dissolved is not None:
                continue
            g.members = [m for m in g.members if w.people.get(m) and w.people[m].alive]
            if not g.members:
                g.dissolved = w.tick
            elif g.leader not in g.members:
                g.leader = g.members[0]
            if (g.rules or "").strip() == "We share what we gather and stand by each other.":
                # the one sentence every bot household was given (c58): its founder's own words instead
                f = w.people.get(g.founder) or w.people.get(g.leader)
                g.rules = group_rules(w.rng, f.traits if f else {}, f.name if f else g.name)

    # ================= telling =================
    def event(self, _kind, _text, *who, **data):
        w = self.w
        w.eid += 1
        ev = {**data, "id": w.eid, "t": w.tick, "kind": _kind, "text": _text, "who": [p.id for p in who if p]}
        self.log.write(ev)
        return ev

    def tell(self, p, text):
        if p.alive:
            p.events.append([self.w.tick, text])
            if len(p.events) > 60:
                del p.events[:-60]

    def wake(self, p, why):
        if p.alive and why not in p.wake:
            p.wake.append(why)

    def see(self, x, y, text, exclude=(), r=None):
        """Those who see a place are told what happens there."""
        seen = []
        for o in self.w.near(x, y, r or self.sight(None)):
            if o.id not in exclude and dist(o.x, o.y, x, y) <= self.sight(o):
                self.tell(o, text)
                seen.append(o)
        return seen

    def sight(self, p):
        w = self.w
        base = 2 if w.is_night() else 5
        if p is not None and w.t(p.x, p.y) == "h":
            base += 1
        if p is not None and not w.is_night():
            b = w.building_at(p.x, p.y)                 # up a tower or an observatory one sees further (c61)
            look = BUILDINGS[b.kind]["roles"].get("lookout") if b and b.done else None
            if look:
                base += look["sight"]
        return base

    # ================= relations =================
    def rel(self, p, o):
        r = p.rel.get(str(o.id))
        if r is None:
            # a stranger is met with what one thinks of their people (grand world, Phase 2)
            first = round(0.5 * p.feel.get(o.people, 0), 2) if o.people and o.people != p.people and p.feel else 0.0
            r = p.rel[str(o.id)] = {"trust": first, "met": self.w.tick}
        return r

    def trust(self, p, o, d, why=None):
        r = self.rel(p, o)
        r["trust"] = max(-1.0, min(1.0, r["trust"] + d))
        if why and o.people and p.people and o.people != p.people:
            # what one of a people does to one colours what one thinks of all of them
            p.feel[o.people] = round(max(-1.0, min(1.0, p.feel.get(o.people, 0) + 0.25 * d)), 3)
        if why:
            p.ledger.append([self.w.tick, o.id, why[0], why[1]])
            if len(p.ledger) > 120:
                del p.ledger[:-120]

    def wrong_known(self, p, o, days=60, kinds=WRONGS):
        """The latest wrong p knows o did, within the last days: a ledger entry, or None."""
        since = self.w.tick - days * TPD
        for e in reversed(p.ledger):
            if e[0] < since:
                break
            if e[1] == o.id and e[2] in kinds:
                return e
        return None

    # ================= movement =================
    def path(self, p, tx, ty, adjacent=False, limit=None):
        """Cheapest way (A*, hours as cost) to a tile, or next to it. A list of steps, [] if there, None if none.
        The search may cover the whole land (it once stopped at 4,000 tiles, and one's own store 70 steps
        off was "no way there": world2's commonest refusal under c50)."""
        w = self.w
        W, H = w.w, w.h
        limit = limit or W * H
        if (p.x, p.y) == (tx, ty) or (adjacent and dist(p.x, p.y, tx, ty) <= 1):
            return []
        fl = self.floats(p)
        if not fl and not w.reachable(p.x, p.y, tx, ty, adjacent):
            return None                     # no way on foot: what searching the whole land would find, at once
        start = (p.x, p.y)
        ride = self.riding(p)
        sail = 1 / max(1, I.best(p.inv, "sail")[0]) if fl else 0
        tcost, at, roads, buildings, terrain = w.terrain_costs(), w.at.flat, w.roads.flat, w.buildings, w.terrain
        openq = [(0, 0, start)]
        came = {start: None}
        cost = {start: 0}
        n = 0
        while openq and n < limit:
            _, c, cur = heapq.heappop(openq)
            n += 1
            if cur == (tx, ty) or (adjacent and max(abs(cur[0] - tx), abs(cur[1] - ty)) <= 1):
                out = []
                while cur != start:
                    out.append(cur)
                    cur = came[cur]
                return out[::-1]
            for dx in (-1, 0, 1):
                nx = cur[0] + dx
                if not 0 <= nx < W:
                    continue
                for dy in (-1, 0, 1):
                    if not dx and not dy:
                        continue
                    ny = cur[1] + dy
                    if not 0 <= ny < H:
                        continue
                    # what World.cost says, without the call
                    i = ny * W + nx
                    bid = at[i]
                    b = buildings.get(bid) if bid else None
                    roles = BUILDINGS[b.kind]["roles"] if b and b.done else ()
                    if "bridge" in roles:
                        step = 1
                    else:
                        step = tcost[i]
                        if step:
                            if "wall" in roles:
                                step = 0
                            elif roads[i]:
                                step = 0.5
                    if not step:
                        if not (fl and TERRAIN[terrain[ny][nx]].get("water")):
                            continue
                        step = sail
                    if ride:
                        step /= 2
                    nc = c + step * (1.4 if dx and dy else 1)
                    if nc < cost.get((nx, ny), 1e9):
                        cost[(nx, ny)] = nc
                        came[(nx, ny)] = cur
                        heapq.heappush(openq, (nc + max(abs(nx - tx), abs(ny - ty)), nc, (nx, ny)))
        return None

    def floats(self, p):
        return any(p.inv.get(k) and I.ITEMS[k].get("float") for k in p.inv if k in I.ITEMS)

    def riding(self, p):
        if p.skill("horsemanship") < 0.3:
            return False
        return any(b.owner == p.id and b.animals.get("horse") for b in self.w.buildings.values())

    def step_along(self, p, act):
        """Move one hour along act["path"]. True when arrived."""
        w = self.w
        path = act.get("path") or []
        budget = act.get("carry", 0) + 1.0
        while path:
            nx, ny = path[0]
            c = w.cost(nx, ny)
            if not c:
                if self.floats(p) and TERRAIN[w.t(nx, ny)].get("water"):
                    c = 1 / max(1, I.best(p.inv, "sail")[0])
                else:
                    act["path"] = None       # blocked: find a new way next hour
                    return False
            if self.riding(p):
                c /= 2
            if c > budget + 1e-9:
                break
            budget -= c
            w.place(p, nx, ny)
            path.pop(0)
        act["carry"] = budget if path else 0
        return not path

    # ================= the hour =================
    def tick(self, decide):
        w = self.w
        if w.hour() == 0:
            self.dawn()
        # minds choose for those who need to (in one batch: a language model's answers come in parallel)
        need = [p for p in w.living() if self.needs_mind(p)]
        if need:
            for pid, intent in (decide(need) or {}).items():
                p = w.people.get(pid)
                if p and p.alive and intent is not None:
                    try:
                        self.adopt(p, intent)
                    except Exception as ex:          # one mind's odd answer never stops the world
                        self.event("refused", f"{p.name}'s plan could not be taken up", p, step={}, why=type(ex).__name__)
                        p.intent, p.act = {"goal": "", "plan": [{"do": "wait", "hours": 1}]}, None
        self.watch = {}
        for p in sorted(w.living(), key=lambda p: p.id):
            try:
                self.run_person(p)
            except Exception as ex:                 # never let one person's odd act stop the world
                self.event("refused", f"{p.name}'s doing went wrong", p, step=dict(p.act or {}), why=type(ex).__name__)
                p.act = None
                if p.intent:
                    p.intent["plan"] = []
        self.bodies()
        self.nature()
        self.workshops()
        self.society_tick()
        self.remember()
        w.tick += 1

    def needs_mind(self, p):
        # hunger with nothing to eat interrupts whatever one is doing (once, until fed)
        if p.satiety <= 6 and not any(I.info(k).get("food") for k in p.inv) and not (p.intent or {}).get("hungry"):
            self.wake(p, "you are hungry and carry no food")
        if p.wake:
            return True
        if p.intent is None or (not p.intent.get("plan") and p.act is None):
            return True
        return False

    def adopt(self, p, intent):
        """A mind's choice: a goal, a plan of steps, and whether to repeat it."""
        plan = [s for s in (intent.get("plan") or []) if isinstance(s, dict) and s.get("do")]
        # goes one after another: only where one ends up matters (the way is found anyway)
        plan = [s for i, s in enumerate(plan) if not (s.get("do") == "go" and i + 1 < len(plan) and plan[i + 1].get("do") == "go")]
        # a go straight before a step that names the same place is walking twice: the step walks there itself
        def same_place(a, b):
            xs = [_num(a.get("x")), _num(a.get("y")), _num(b.get("x")), _num(b.get("y"))]
            return None not in xs and abs(xs[0] - xs[2]) <= 1 and abs(xs[1] - xs[3]) <= 1
        plan = [s for i, s in enumerate(plan) if not (
            s.get("do") == "go" and i + 1 < len(plan) and plan[i + 1].get("do") != "go" and same_place(s, plan[i + 1]))]
        p.intent = {"goal": str(intent.get("goal", ""))[:200], "plan": plan[:16], "routine": bool(intent.get("routine")),
                    "orig": plan[:16] if intent.get("routine") else None, "since": self.w.tick,
                    "hungry": p.satiety <= 6}
        if not intent.get("keep_wake"):             # a stopgap while a mind thinks leaves the reasons standing
            p.wake = []
            p.last_decided = self.w.tick
            p.events = p.events[intent.get("events_seen", len(p.events)):]
        if intent.get("now") and isinstance(intent["now"], dict) and intent["now"].get("do"):
            p.act = None
            p.intent["plan"].insert(0, intent["now"])
        elif intent.get("replace", True):
            p.act = None
        for k in ("memory", "self_view"):
            if intent.get(k):
                setattr(p, k, str(intent[k])[:600 if k == "memory" else 200])
        if intent.get("say"):
            self.speak(p, intent["say"], intent.get("to"), wake=not intent.get("quiet"))
        if intent.get("idea"):
            p.ideas.append([self.w.tick, str(intent["idea"])[:200]])
            p.ideas = p.ideas[-10:]
        if intent.get("life"):
            p.life.append([self.w.tick, str(intent["life"])[:160]])
            p.life = p.life[:1] + p.life[1:][-5:]
        for name, text in (intent.get("beliefs") or {}).items():
            if isinstance(text, str) and self.w.by_name(name):
                p.beliefs[name] = text[:160]

    def routine_miss(self, p, step):
        """A routine's step refused twice running is left out of the routine, and the person told: a hunter's round
        in a hunted-out land asked for deer every round, for days (c60)."""
        orig = p.intent.get("orig") if p.intent.get("routine") else None
        if not orig:
            return
        k = json.dumps({a: b for a, b in step.items() if a != "fetched"}, sort_keys=True, default=str)
        miss = p.intent.setdefault("rmiss", {})
        miss[k] = miss.get(k, 0) + 1
        if miss[k] < 2:
            return
        keep = [s for s in orig if json.dumps({a: b for a, b in s.items() if a != "fetched"}, sort_keys=True, default=str) != k]
        if len(keep) < len(orig):
            p.intent["orig"] = keep or None
            if not keep:
                p.intent["routine"] = False
            self.tell(p, f"You leave {step.get('do')} out of your round of work; it could not be done twice running.")

    def run_person(self, p):
        w = self.w
        self.auto_eat(p)
        if p.act is None and p.intent and p.intent.get("until") is not None and w.tick >= p.intent["until"]:
            lord = w.people.get(p.intent.get("order"))
            self.tell(p, f"The work {lord.name if lord else 'you were given'} {'set you' if lord else ''} is done.".replace("  ", " "))
            p.intent = None                         # ordered work, its days done: one's own life again
            return
        if p.act is None:
            if p.intent and p.intent.get("plan"):
                step = p.intent["plan"].pop(0)
                try:
                    ok, msg = self.start(p, step)
                except Exception as ex:             # a step written in a way that makes no sense
                    ok, msg = False, f"that step made no sense ({type(ex).__name__})"
                    p.act = None
                if not ok:
                    self.tell(p, f"Could not {step.get('do')}: {msg}.")
                    self.event("refused", f"{p.name} could not {step.get('do')}: {msg}", p, step=step, why=msg)
                    self.refused[p.id] = ([r for r in self.refused.get(p.id, []) if w.tick - r[0] < TPD * 3] + [(w.tick, step, msg)])[-8:]
                    p.act = None
                    self.routine_miss(p, step)
                    p.intent["misses"] = p.intent.get("misses", 0) + 1
                    if p.intent["plan"] and p.intent["misses"] < 2:
                        return                  # one step would not do: the rest of the plan goes on
                    p.intent["plan"] = []
                    self.wake(p, f"could not {step.get('do')}")
                    return
                p.intent["misses"] = 0
                if p.intent.get("rmiss"):
                    p.intent["rmiss"].pop(json.dumps({a: b for a, b in step.items() if a != "fetched"}, sort_keys=True, default=str), None)
            elif p.intent and p.intent.get("routine") and p.intent.get("orig"):
                p.intent["plan"] = [dict(s) for s in p.intent["orig"]]
                return
            else:
                if w.is_night():
                    p.rest = True              # nothing to do at night: sleep
                return
        act = p.act
        p.rest = act["do"] in ("rest", "sleep")
        status, msg = getattr(self, "do_" + act["do"])(p, act)
        if status == "go":
            return
        p.act = None
        if msg:
            self.tell(p, msg)
        if status == "fail":
            if p.intent:
                p.intent["plan"] = []
            self.wake(p, f"{act['do']} did not work out")

    # ================= bodies =================
    def dawn(self):
        w = self.w
        for p in w.living():
            p.rest = False
        self.ground_day()
        if w.regions:
            self.tongues_day()
        if w.day() % DPS == 0:
            self.season_start()
        self.pens_day()
        self.farms_day()
        self.mills_day()
        self.fish_day()
        for b in list(w.buildings.values()):
            if b.done and "hearth" in BUILDINGS[b.kind]["roles"] and b.fuel <= 0 and w.tick - b.built > TPD * 3:
                pass

    def tongues_day(self):
        """Living among speakers of another tongue, one comes to know it: a grown person in about three years, a child
        in one (grand world, Phase 2)."""
        w = self.w
        for p in w.living():
            heard = {}
            for o in w.near(p.x, p.y, 4):
                if o.people and o.people != p.people and p.skill(f"tongue:{o.people}") < 1:
                    heard[o.people] = heard.get(o.people, 0) + 1
            if heard:
                k, n = max(heard.items(), key=lambda kv: (kv[1], kv[0]))
                if n >= 2:
                    s = f"tongue:{k}"
                    p.skills[s] = round(min(1.0, p.skill(s) + (0.015 if not p.adult(w.tick) else 0.004)), 3)

    def ground_day(self):
        """Nothing keeps on the ground (grand world, Phase 1.1): each day a share of what lies there rots, rusts,
        is scattered or carried off (items.ground_loss). Surplus left lying is lost, not hoarded."""
        w = self.w
        rng = w.rng
        for k in list(w.piles):
            pile = w.piles[k]
            for it in list(pile):
                n = pile[it]
                if not isinstance(n, (int, float)) or n <= 0:
                    continue
                rate = I.ground_loss(it)
                lost = sum(1 for _ in range(int(n)) if rng.random() < rate) if n <= 30 else int(n * rate + rng.random())
                if lost:
                    I.remove(pile, it, lost)
            if not pile:
                del w.piles[k]

    def bodies(self):
        w = self.w
        winter_night = w.season() == "winter" and w.is_night()
        for p in w.living():
            if (w.tick + p.id) % 5 == 0 and p.satiety > 0:        # about 2.5 food a day
                p.satiety -= 1
            if p.satiety <= 0 and (w.tick + p.id) % 6 == 0:
                p.health -= 1
                if p.health <= 0:
                    self.die(p, "starved")
                    continue
            top = p.max_health(w.tick)
            p.health = min(p.health, top)
            b = w.building_at(p.x, p.y)
            shelter = BUILDINGS[b.kind]["roles"].get("shelter") if b and b.done and w.may_use(p, b) else None
            if p.sick:
                if self.sickness(p, shelter):
                    continue
            elif w.rng.random() < 0.0006 * (2 if p.satiety <= 3 else 1) * (2 if w.season() == "winter" else 1):
                p.sick = {"since": w.tick}
                self.tell(p, "You feel sick.")
                self.event("sick", f"{p.name} fell sick", p)
            if p.satiety >= 6 and p.health < top and not p.sick:
                every = 6 if not p.rest else 2
                if p.rest and shelter:
                    every = 1
                if p.age(w.tick) >= 55:
                    every *= 2
                if (w.tick + p.id) % every == 0:
                    p.health = min(top, p.health + 1)
            if winter_night:
                warm = I.warmth(p.inv) + (shelter["warmth"] if shelter else 0)
                if self.hearth_near(p):
                    warm += 2
                for k in I.worn(p.inv):
                    if I.WEARABLE[k][1]:
                        self.wear_out(p, k)
                if w.rng.random() < 0.12 * max(0.0, 1 - warm / 3):
                    p.health -= 1
                    self.tell(p, "The winter cold bites you (lost 1 health).")
                    if p.health <= 0:
                        self.die(p, "froze")
                        continue
            if w.tick - p.born >= p.lifespan:
                self.die(p, "died of old age")
                continue
            keep = I.best(p.inv, "keep")[0] or 1.0
            self.spoil(p.inv, keep)
            if p.pregnant and w.tick >= p.pregnant["due"]:
                self.birth(p)

    def sickness(self, p, shelter):
        w = self.w
        lose = 0.06 * (0.5 if p.rest else 1) * (0.5 if shelter else 1)
        if shelter and shelter.get("heals"):
            lose *= 0.3
        if w.rng.random() < lose:
            p.health -= 1
            if p.health <= 0:
                self.die(p, "died of sickness")
                return True
        mend = 0.015 + (0.02 if p.rest else 0) + (0.02 if p.satiety >= 8 else 0) + (0.02 if shelter else 0)
        if w.near(p.x, p.y, 1) and len(w.near(p.x, p.y, 1)) > 1:
            mend += 0.01
        if w.rng.random() < mend:
            p.sick = None
            self.tell(p, "The sickness has passed.")
        for o in w.near(p.x, p.y, 1):
            if o.id != p.id and not o.sick and w.rng.random() < 0.01:
                o.sick = {"since": w.tick}
                self.tell(o, f"You caught {p.name}'s sickness.")
        return False

    def hearth_near(self, p):
        for x, y in self.w.beside(p.x, p.y):
            b = self.w.building_at(x, y)
            if b and b.done and "hearth" in BUILDINGS[b.kind]["roles"] and b.fuel > 0:
                return b
        return None

    def spoil(self, inv, factor=1.0):
        rng = self.w.rng
        for k in list(inv):
            it = I.info(k)
            p = it.get("spoil", 0) * factor
            if p <= 0:
                continue
            n = inv[k]
            lost = sum(1 for _ in range(n) if rng.random() < p) if n <= 60 else int(n * p + rng.random())
            if lost:
                I.remove(inv, k, lost)

    def wear_out(self, p, k):
        uses = I.ITEMS.get(k, {}).get("uses")
        if not uses:
            return
        p.wear[k] = p.wear.get(k, 0) + 1
        if p.wear[k] >= uses:
            p.wear[k] = 0
            I.remove(p.inv, k, 1)
            self.tell(p, f"Your {I.pretty(k)} {'wore out' if k in I.WEARABLE else 'broke'}.")

    def use_tool(self, p, use):
        k, f = I.best_tool(p.inv, use)
        if k:
            self.wear_out(p, k)
        return f

    def auto_eat(self, p):
        """Hungry people eat what they carry, what spoils soonest first."""
        if p.satiety > 12:
            return
        foods = sorted((k for k in p.inv if I.info(k).get("food")), key=lambda k: -I.info(k).get("spoil", 0))
        while foods and p.satiety <= 16:
            k = foods[0]
            I.remove(p.inv, k, 1)
            p.satiety = min(20, p.satiety + I.ITEMS[k]["food"])
            if not p.inv.get(k):
                foods.pop(0)

    # ================= births and deaths =================
    def birth(self, carrier):
        w = self.w
        from .gen import make_person
        info = carrier.pregnant
        carrier.pregnant = None
        other = w.people.get(info.get("with"))
        x, y = carrier.x, carrier.y
        c = make_person(w, w.rng, x, y, 0, parents=[carrier.id] + ([other.id] if other else []))
        if info.get("name") and info["name"] not in w.names:
            w.names.discard(c.name)
            c.name = str(info["name"])[:12]
            w.names.add(c.name)
        c.satiety = 14
        c.mind = "bot"
        c.home = carrier.home                   # a child sleeps under its mother's roof
        if carrier.people:
            # a child of the mother's people, named in her tongue; it grows up speaking both parents' tongues, and
            # learns from them what to think of other peoples (grand world, Phase 2)
            from .content.peoples import PEOPLES
            from .names import make_name
            c.people = carrier.people
            if not info.get("name") and carrier.people in PEOPLES:
                w.names.discard(c.name)
                c.name = make_name(w.rng, w.names, PEOPLES[carrier.people]["tongue"])
            for par in (carrier, other):
                if par and par.people:
                    c.skills[f"tongue:{par.people}"] = 1.0
                    for k, v in par.feel.items():
                        c.feel[k] = round(c.feel.get(k, 0) + 0.35 * v, 2)
        for par in (carrier, other):
            if par:
                par.children.append(c.id)
                c.rel[str(par.id)] = {"trust": 0.8, "met": w.tick, "kin": "parent"}
                par.rel[str(c.id)] = {"trust": 0.8, "met": w.tick, "kin": "child"}
        w.people[c.id] = c
        w.place(c, x, y)
        self.tell(carrier, f"Your child {c.name} was born.")
        if other:
            self.tell(other, f"Your child {c.name} was born.")
        self.event("birth", f"{c.name} was born to {carrier.name}" + (f" and {other.name}" if other else ""), carrier, other, child=c.id)

    def die(self, p, cause, by=None):
        w = self.w
        p.alive = False
        p.died = w.tick
        p.cause = cause if not by else f"{cause} by {by.name}"
        w.grid.get(w.cell(p.x, p.y), set()).discard(p.id)
        if p.inv:
            pile = w.piles.setdefault(key(p.x, p.y), {})
            for k, n in p.inv.items():
                I.add(pile, k, n)
            p.inv = {}
        heir = w.people.get(p.heir) if p.heir else None
        if not (heir and heir.alive):
            heir = w.people.get(p.partner) if p.partner else None
        if not (heir and heir.alive):
            kids = [w.people[c] for c in p.children if w.people.get(c) and w.people[c].alive]
            heir = max(kids, key=lambda c: w.tick - c.born) if kids else None
        for b in w.buildings.values():
            if b.owner == p.id:
                b.owner = heir.id if heir else 0
        if heir:
            self.tell(heir, f"{p.name} is dead; what they built is now yours.")
        # the dead leave their groups: the next member leads, and a group with no one left is ended
        for gid in list(p.groups):
            g = w.groups.get(gid)
            if g and g.dissolved is None and p.id in g.members:
                self.remove_member(g, p, f"{p.name}, of {g.name}, is dead.")
        # a law never written down lives in its maker's word, and dies with them (C2)
        for g in w.groups.values():
            gone = [l for l in g.laws if len(l) > 3 and l[3] == p.id and not l[2]]
            if gone:
                g.laws = [l for l in g.laws if l not in gone]
                for m in g.members:
                    o = w.people.get(m)
                    if o and o.alive:
                        self.tell(o, f"With {p.name} dead, the law they gave {g.name} and never wrote down is forgotten: "
                                     + "; ".join(f'"{l[1][:60]}"' for l in gone))
        for o in w.living():
            if str(p.id) in o.rel and o.rel[str(p.id)].get("kin"):
                self.tell(o, f"Your {o.rel[str(p.id)]['kin']} {p.name} is dead ({p.cause}).")
                self.wake(o, f"{p.name} died")
                if by and by.alive and by.id != o.id:
                    self.trust(o, by, -0.7, ("kin_killed", f"{by.name} killed your {o.rel[str(p.id)]['kin']} {p.name}"))
        self.see(p.x, p.y, f"{p.name} died ({p.cause}).", exclude={p.id})
        self.event("death", f"{p.name} died ({p.cause}) at {int(p.age(w.tick))}", p, by, cause=cause, age=round(p.age(w.tick), 1))
        # knowledge held by few: is a craft lost with them?
        for c, s in p.skills.items():
            if c in CRAFTS and s >= 0.5 and not any(o.skill(c) >= 0.3 for o in w.living()):
                w.lost[c] = w.tick
                self.event("craft_lost", f"With {p.name} died the last who knew {c.replace('_', ' ')} well", p, craft=c)
        if p.partner and w.people.get(p.partner):
            w.people[p.partner].partner = None

    # ================= land and animals =================
    def roll_years(self):
        """Each region's year, drawn each spring (grand world, Phase 2): good, lean or hard, a year like the last as
        often as not, and the high moors and the dry grass go hard more often than the river land. Shocks by
        region are what sends the hungry to their neighbours."""
        w = self.w
        for r in w.regions:
            k = str(r["id"])
            prev = w.years.get(k, "good")
            if prev and w.rng.random() < 0.45:
                now = prev
            else:
                hard = 0.22 if r["kind"] in ("upland", "steppe") else 0.1
                x = w.rng.random()
                now = "hard" if x < hard else "lean" if x < hard + 0.3 else "good"
            w.years[k] = now
            if now != prev and now in ("hard", "lean"):
                self.event("year", f"A {now} year begins in {r.get('name') or 'the ' + r['kind']}", region=r["id"], year=now)

    def season_start(self):
        w = self.w
        s = w.season()
        if s == "spring" and w.regions:
            self.roll_years()
        for k, d in w.deposits.items():
            dd = DEPOSITS[d["kind"]]
            bear = YEAR_BEARS[w.year_at(*unkey(k))] if w.regions else 1
            if dd.get("renew") is True and s == "spring":
                d["left"] = max(1, int(d["size"] * min(1, bear)))
            elif dd.get("renew") == "autumn" and s == "autumn":
                d["left"] = max(1, int(d["size"] * min(1, bear)))
            elif dd.get("renew") == "bush" and s == "winter":
                d["left"] -= d["left"] // 4
        for h in w.herds:
            if s == "spring" and h["n"] > 1 and w.year_at(h["x"], h["y"]) != "hard":
                lo, hi = WILD[h["kind"]]["herd"]
                grow = max(1, h["n"] // 4) if w.year_at(h["x"], h["y"]) != "lean" else max(1, h["n"] // 8)
                h["n"] = min(hi + 4, h["n"] + grow)
        if s == "spring":
            self.pens_spring()
        self.ruin()

    def ruin(self):
        """Every building weathers (c59): a little each season, faster when it stands empty (its owner dead,
        no heir), slower for a monument; mended (step mend: one of what it is made of) it is whole again, and
        a field sown or a fire fed is kept up by that. At nothing it falls, its goods on the ground and its
        place free. A pen with beasts in it does not fall while they live. (Before, only the heirless decayed,
        so estates passed down whole for centuries: in the long land three heirs held 2,900 buildings.)"""
        w = self.w
        odd = (w.day() // DPS) % 2
        for b in list(w.buildings.values()):
            if not b.done:
                continue
            full = BUILDINGS[b.kind]["hp"]
            if "monument" in BUILDINGS[b.kind]["roles"]:
                loss = 1 if odd else 0
            else:
                loss = 2 if w.empty(b) else 1
            before = b.hp
            b.hp -= loss
            o = w.people.get(b.owner) if b.owner and b.owner > 0 else None
            if b.hp > 0 or b.animals:
                b.hp = max(1, b.hp)
                if o and o.alive and before > full * 0.3 >= b.hp:
                    self.tell(o, f"Your {b.kind} at ({b.x},{b.y}) is falling apart: mend it ({mend_text(b)}) or it will fall.")
                continue
            k = key(b.x, b.y)
            if b.inv:
                pile = w.piles.setdefault(k, {})
                for item, n in b.inv.items():
                    I.add(pile, item, n)
            del w.buildings[b.id]
            if w.at.get(k) == b.id:
                del w.at[k]
            for p in w.living():
                if p.home == b.id:
                    p.home = None
            if o and o.alive:
                self.tell(o, f"Your {b.kind} at ({b.x},{b.y}) fell down for want of mending.")
            self.event("ruin", f"The {'empty ' if not (o and o.alive) else ''}{b.kind} at ({b.x},{b.y}) fell into ruin",
                       building=b.kind, x=b.x, y=b.y)

    def nature(self):
        w = self.w
        s = w.season()
        # berry bushes regrow in the growing seasons
        if s != "winter" and w.tick % 3 == 0:
            for k, d in w.deposits.items():
                if DEPOSITS[d["kind"]].get("renew") == "bush" and d["left"] < d["size"]:
                    if w.regions and w.tick % 6 and w.year_at(*unkey(k)) == "hard":
                        continue                    # a hard year: bushes come back at half the pace
                    d["left"] += 1
        # herds wander their ground
        if w.tick % 3 == 0:
            for h in w.herds:
                if h["n"] <= 0:
                    continue
                nx, ny = h["x"] + w.rng.randint(-1, 1), h["y"] + w.rng.randint(-1, 1)
                if w.passable(nx, ny) and w.t(nx, ny) in WILD[h["kind"]]["on"] + "," and not w.building_at(nx, ny):
                    h["x"], h["y"] = nx, ny
        w.herds = [h for h in w.herds if h["n"] > 0] + self.new_herds()
        # hearths burn their fuel
        for b in w.buildings.values():
            if b.done and "hearth" in BUILDINGS[b.kind]["roles"] and b.fuel > 0:
                b.fuel -= 1
                if b.inv.get("wood") and b.fuel < 6:
                    I.remove(b.inv, "wood", 1)
                    b.fuel += I.ITEMS["wood"]["fuel"] * 4
        # stores keep food, some better than others
        if w.tick % 3 == 0:
            for b in w.buildings.values():
                st = BUILDINGS[b.kind]["roles"].get("store")
                if st and b.inv:
                    keep = st["keep"] * (0.5 if b.inv.get("jar") else 1)
                    self.spoil(b.inv, keep * 3)
            for k in list(w.piles):
                self.spoil(w.piles[k], 3.0)
                if not w.piles[k]:
                    del w.piles[k]
        self.wolves()
        self.resolve_hunts()

    def new_herds(self):
        """Now and then a herd wanders in where there are too few of its kind."""
        w = self.w
        if w.tick % (TPD * 5):
            return []
        out = []
        counts = {}
        for h in w.herds:
            counts[h["kind"]] = counts.get(h["kind"], 0) + 1
        # the land carries as many herds as it has held at most; below that, game wanders in from
        # the wilder parts, away from people (hunting near home still empties the land around it)
        held = w.cfg.setdefault("herds_held", {})
        for kind, n in counts.items():
            held[kind] = max(held.get(kind, 0), n)
        for kind, v in WILD.items():
            room = max(3, held.get(kind, 3)) - counts.get(kind, 0)
            if room > 0 and w.rng.random() < min(0.9, 0.15 + 0.1 * room):
                # the wildest of a few places: far from people where the land allows, and in a crowded
                # land at least out of sight of anyone (it used to be 12 steps or nothing, so once people
                # filled the land the game never came back)
                # In a land full of people (the long land: 800 on 96 x 96, no herd for 80 years) the emptiest of
                # the places looked at will do, so long as no one stands within 2 steps.
                best = None
                for _ in range(60):
                    x, y = w.rng.randrange(w.w), w.rng.randrange(w.h)
                    if not (w.passable(x, y) and w.t(x, y) in v["on"]) or w.building_at(x, y):
                        continue
                    if not w.near(x, y, 12):
                        best = (99, 0, x, y)
                        break
                    if w.near(x, y, 2):
                        continue
                    gap = next((r for r in (5, 8, 10) if w.near(x, y, r)), 12)
                    crowd = -len(w.near(x, y, 5))
                    if best is None or (gap, crowd) > best[:2]:
                        best = (gap, crowd, x, y)
                if best:
                    best = (best[0], best[2], best[3])
                if best:
                    lo, hi = v["herd"]
                    out.append({"id": w.new_id(), "kind": kind, "x": best[1], "y": best[2], "n": w.rng.randint(lo, hi), "grow": 0})
        return out

    def wolves(self):
        w = self.w
        for pk in w.packs:
            if w.tick % 2:
                continue
            target = None
            for o in w.near(pk["x"], pk["y"], 5):
                company = len(w.near(o.x, o.y, 1))
                inside = w.building_at(o.x, o.y)
                if inside and inside.done and "shelter" in BUILDINGS[inside.kind]["roles"]:
                    continue                    # behind walls, out of reach
                if company <= 1 and not self.hearth_near(o) and (w.is_night() or w.season() == "winter"):
                    target = o
                    break
            if target:
                step = [(pk["x"] + dx, pk["y"] + dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                        if w.passable(pk["x"] + dx, pk["y"] + dy)]
                if step:
                    pk["x"], pk["y"] = min(step, key=lambda t: dist(t[0], t[1], target.x, target.y))
                if dist(pk["x"], pk["y"], target.x, target.y) <= 1 and w.rng.random() < 0.3:
                    dmg = max(0, 2 - I.best(target.inv, "armour")[0])
                    target.health -= dmg
                    self.tell(target, f"Wolves bit you (lost {dmg} health)!")
                    self.wake(target, "wolves attacked you")
                    if target.health <= 0:
                        self.die(target, "killed by wolves")
            else:
                nx, ny = pk["x"] + w.rng.randint(-1, 1), pk["y"] + w.rng.randint(-1, 1)
                if w.passable(nx, ny) and w.t(nx, ny) in "T.h":
                    pk["x"], pk["y"] = nx, ny

    # ================= farms =================
    def farms_day(self):
        w = self.w
        for b in w.buildings.values():
            c = b.crop
            if not c or not b.done:
                continue
            if c.get("ripe_at") and w.tick >= c["ripe_at"] and not c.get("ripe"):
                if w.season() == "winter":
                    c["ripe_at"] += TPD
                    continue
                c["ripe"] = True
                if w.regions:                       # the year where the field lies (grand world)
                    c["yield"] = max(1, int(c["yield"] * YEAR_BEARS[w.year_at(b.x, b.y)]))
                b.inv[c["what"]] = b.inv.get(c["what"], 0) + c["yield"]
                o = w.people.get(b.owner)
                if o and o.alive:
                    self.tell(o, f"Your {c['what']} at ({b.x},{b.y}) is ripe: {c['yield']} to reap.")
                self.event("ripe", f"A field at ({b.x},{b.y}) is ripe with {c['yield']} {c['what']}", o, x=b.x, y=b.y)
            elif c.get("ripe") and b.inv.get(c["what"], 0) * 4 <= c.get("yield", 0):
                # reaped (the last gleanings are left in the stubble): the field is free to sow again
                b.inv.pop(c["what"], None)
                b.crop = None

    def fish_day(self):
        """Fish breed back in waters fished down: quickest at half full, slower in winter; full again, forgotten (M2)."""
        w = self.w
        r = 0.05 if w.season() == "winter" else 0.1
        for k in list(w.fish):
            cap = w.fish_cap(k)
            left = w.fish[k] + r * w.fish[k] * (1 - w.fish[k] / max(1, cap)) + 1
            if left >= cap:
                del w.fish[k]
            else:
                w.fish[k] = round(left, 2)

    def mills_day(self):
        """A mill grinds the grain put in it into flour, so much a day, for whoever put it there to take (c61)."""
        for b in self.w.buildings.values():
            mill = BUILDINGS[b.kind]["roles"].get("mill")
            if b.done and mill and b.inv.get("grain"):
                n = min(b.inv["grain"], mill["per_day"])
                I.remove(b.inv, "grain", n)
                I.add(b.inv, "flour", n)

    # ================= pens =================
    def pens_day(self):
        w = self.w
        for b in w.buildings.values():
            if b.inv.get("milk") and "pen" in BUILDINGS[b.kind]["roles"]:
                # milk past three days' worth has turned (old hoards from before the bound included: c56)
                bound = sum(TAME[k]["gives"].get("milk", 0) * n for k, n in b.animals.items()) * 3
                if b.inv["milk"] > bound:
                    I.remove(b.inv, "milk", b.inv["milk"] - bound)
            if not b.done or not b.animals:
                continue
            pasture = any(w.t(x, y) in ".," for x, y in [(b.x, b.y)] + list(w.beside(b.x, b.y)))
            grass = pasture and w.season() != "winter"
            for kind, n in list(b.animals.items()):
                if n <= 0:
                    continue
                t = TAME[kind]
                need = t["eats"] * n
                if not grass:
                    have = b.inv.get("hay", 0) + b.inv.get("grain", 0)
                    if have >= need:
                        for f in ("hay", "grain"):
                            take = min(need, b.inv.get(f, 0))
                            I.remove(b.inv, f, take)
                            need -= take
                    elif w.rng.random() < (0.08 if pasture else 0.3):     # winter grass is thin, but it is something
                        b.animals[kind] = n - 1
                        o = w.people.get(b.owner)
                        if o and o.alive:
                            self.tell(o, f"A {kind} in your pen at ({b.x},{b.y}) died unfed.")
                        continue
                if w.season() != "winter":
                    for k, q in t["gives"].items():
                        # milk not taken is never there: a pen holds at most three days of it (it once held 7,368)
                        room = q * n * 3 - b.inv.get(k, 0) if k == "milk" else q * n
                        if room > 0:
                            I.add(b.inv, k, min(q * n, room))
            b.animals = {k: v for k, v in b.animals.items() if v > 0}

    def pens_spring(self):
        w = self.w
        for b in w.buildings.values():
            if not b.animals:
                continue
            cap = BUILDINGS[b.kind]["roles"].get("pen", {}).get("capacity", 0)
            for kind, n in list(b.animals.items()):
                t = TAME[kind]
                for k, q in t.get("spring", {}).items():
                    I.add(b.inv, k, q * n)
                room = cap - sum(b.animals.values())
                born = min(room, (n // 2) * t["breed"])
                if born > 0:
                    b.animals[kind] = n + born
                    o = w.people.get(b.owner)
                    if o and o.alive:
                        self.tell(o, f"{born} young {kind} were born in your pen at ({b.x},{b.y}).")

    # ================= workshops =================
    def workshops(self):
        w = self.w
        for b in w.buildings.values():
            pr = b.process
            if not pr or w.tick < pr["done_at"]:
                continue
            r = RECIPES[pr["recipe"]]
            by = w.people.get(pr["by"])
            if pr["ok"]:
                I.add(b.inv, r["out"], r["n"] * pr.get("runs", 1))
                msg = f"The {I.pretty(r['out'])} in the {b.kind} at ({b.x},{b.y}) is done: {r['n'] * pr.get('runs', 1)} waiting there."
                self.event("made", f"{by.name if by else 'Someone'} made {r['n'] * pr.get('runs', 1)} {I.pretty(r['out'])} in a {b.kind}",
                           by, item=r["out"], qty=r["n"] * pr.get("runs", 1), craft=r["craft"])
            else:
                msg = f"The work in the {b.kind} at ({b.x},{b.y}) came to nothing ({self.fail_text(r)})."
            b.process = None
            owner = w.people.get(b.owner)
            for o in [by] + ([owner] if owner is not by else []):
                if o and o.alive:
                    self.tell(o, msg)

    # ================= knowledge =================
    def can_try(self, p, craft):
        """None if p may try a craft, else why not."""
        c = CRAFTS[craft]
        miss = [f"{pc.replace('_', ' ')} {int(lv * 100)}%" for pc, lv in c["pre"].items() if p.skill(pc) < lv]
        return ("it needs some skill first in " + ", ".join(miss)) if miss else None

    def attempt(self, p, craft):
        """Does a try at a craft come right? Every try teaches; a failure more than a success."""
        s = p.skill(craft)
        ok = self.w.rng.random() < 0.25 + 0.75 * s
        self.practise(p, craft, 0.04 * (1 - s) if ok else 0.08 * (1 - s))
        for o in self.w.near(p.x, p.y, 1):
            if o.id != p.id and ok:
                self.practise(o, craft, 0.03 * (1 - o.skill(craft)), quiet=True)
        return ok

    def practise(self, p, craft, amount, quiet=False):
        before = p.skill(craft)
        p.skills[craft] = round(min(1.0, before + amount), 3)
        if craft in CRAFTS and craft not in self.w.firsts and before == 0 and not quiet:
            self.w.firsts[craft] = [self.w.tick, p.id]
            self.event("first", f"{p.name} is the first here to practise {craft.replace('_', ' ')}", p, craft=craft)
        for lv, word in ((0.3, "able"), (0.7, "a master")):
            if before < lv <= p.skills[craft] and craft in CRAFTS:
                self.tell(p, f"You have become {word} at {craft.replace('_', ' ')}.")
                self.event("skill", f"{p.name} became {word} at {craft.replace('_', ' ')}", p, craft=craft, level=lv)

    @staticmethod
    def fail_text(r):
        return {"pottery": "it cracked in the firing", "smelting": "the ore would not give its metal",
                "casting": "the metal cooled flawed", "alloying": "the metals would not blend",
                "ironworking": "the bloom crumbled", "smithing": "the iron split", "brewing": "it soured",
                "tanning": "the hides rotted", "weaving": "the threads tangled", "glassmaking": "the glass clouded and broke",
                }.get(r["craft"], "it came out wrong")

    @staticmethod
    def skill_word(s):
        return "untried" if s <= 0 else "a beginner" if s < 0.3 else "able" if s < 0.7 else "a master"

    # ================= memory of places =================
    def remember(self):
        w = self.w
        if w.tick % 3:
            return
        W, at, dep, buildings = w.w, w.at.flat, w.deposits.flat, w.buildings
        for p in w.living():
            r = self.sight(p)
            for y in range(max(0, p.y - r), min(w.h, p.y + r + 1)):
                base = y * W
                for x in range(max(0, p.x - r), min(W, p.x + r + 1)):
                    d, bid = dep[base + x], at[base + x]
                    if not (d or bid):
                        continue
                    k = key(x, y)
                    if d:
                        p.known[k] = ["deposit", d["kind"], w.tick]
                    b = buildings.get(bid) if bid else None
                    if b and b.done:
                        p.known[k] = ["building", b.kind, w.tick]
            for h in w.herds:
                if abs(p.x - h["x"]) <= r and abs(p.y - h["y"]) <= r:
                    p.known[f"herd{h['id']}"] = ["herd", h["kind"], w.tick, h["x"], h["y"]]
            for o in w.near(p.x, p.y, r):
                if o.id != p.id:
                    rr = self.rel(p, o)
                    rr["seen"] = w.tick
            if len(p.known) > 160:
                # the commonplace is forgotten first; a seam of ore or a clay bank far off is remembered
                for k in heapq.nsmallest(len(p.known) - 160, p.known,
                                         key=lambda k: (p.known[k][0] == "deposit" and p.known[k][1] in RARE, p.known[k][2])):
                    del p.known[k]
        # word of the land: people who spend time together tell each other of places one knows and the other not
        if w.hour() == 6:
            for p in w.living():
                if not p.adult(w.tick):
                    continue
                for o in w.near(p.x, p.y, 2):
                    if o.id == p.id or p.rel.get(str(o.id), {}).get("trust", 0) < 0:
                        continue
                    news = [k for k, v in o.known.items() if v[0] == "deposit" and v[1] in RARE and k not in p.known and k in w.deposits]
                    if news:
                        k = w.rng.choice(news)
                        p.known[k] = ["deposit", o.known[k][1], w.tick]
                        self.tell(p, f"{o.name} told you of {DEPOSITS[o.known[k][1]]['name']} at ({k}).")
                    # and of wrongs done them: word of who steals and strikes goes round among friends
                    if p.rel.get(str(o.id), {}).get("trust", 0) > 0.15:
                        for e in reversed(o.ledger[-30:]):
                            q = w.people.get(e[1])
                            if e[2] in FIRST_HAND and w.tick - e[0] <= 20 * TPD and q and q.alive and q.id != p.id \
                                    and not self.wrong_known(p, q, 20):
                                self.trust(p, q, -0.1, ("heard_wrong", f"{o.name} told you {e[3].replace('your', 'their').replace('you', o.name)}"))
                                break
                    break
