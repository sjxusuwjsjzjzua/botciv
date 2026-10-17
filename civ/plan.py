"""The recipe-tree planner: the steps to have n of something, from what one holds, sees, remembers
and knows how to do. Bots plan everything with it; a person can name a goal and have it laid out.

It is a helper, not a mind: it never decides what is worth having, only how to get it."""
from .content import TERRAIN, DEPOSITS, WILD, TAME, BUILDINGS, CRAFTS, RECIPES
from .content import items as I
from .content.crafts import recipes_making, tool_options
from .world import dist, key, TPD

ANIMAL = {"meat": "hunt", "hide": "hunt", "bone": "hunt", "fish": "fish"}


class Planner:
    def __init__(self, engine):
        self.e = engine
        self.w = engine.w
        self.extra = {}

    def holding(self, p, item):
        return p.inv.get(item, 0) + sum(b.inv.get(item, 0) for b in self.e.stores_beside(p))

    def holders(self):
        """This hour's buildings that hold anything: stores by owner, and workshops (rebuilt each hour; a scan of
        every building per question was a fifth of an hour's work in the long land's 8,000 buildings, c57)."""
        w = self.w
        if getattr(self, "_holders_t", None) != w.tick:
            stores, shops = {}, []
            for b in w.buildings.values():
                if not b.done or not b.inv or b.process:
                    continue
                roles = BUILDINGS[b.kind]["roles"]
                if "store" in roles:
                    stores.setdefault(b.owner, []).append(b)
                if "workshop" in roles:
                    shops.append(b)
            self._holders, self._holders_t = (stores, shops), w.tick
        return self._holders

    def own_store_with(self, p, item):
        """One's own store, or workshop where a firing left it (bricks in the kiln), holding the item."""
        stores, shops = self.holders()
        for b in stores.get(p.id, []):
            if b.inv.get(item):
                return b
        # the workshops holding the item (one list per item while minds choose, when nothing changes)
        for b in self.e.shared(("shops", item), lambda: [b for b in shops if b.inv.get(item)]):
            if b.inv.get(item) and self.w.may_use(p, b):
                return b                    # a workshop one may use where a firing left it
        return None

    def get(self, p, item, n=1, depth=0, seen=None):
        """Steps toward holding n of item, or None if no way is known. [] if already held."""
        if depth == 0:
            self.extra = {}                     # what the plan's own earlier steps make beyond their need
        saved = dict(self.extra)
        out = self._get(p, item, n, depth, seen)
        if out is None:
            self.extra = saved                  # a way not taken uses nothing up
        return out

    def _get(self, p, item, n, depth, seen):
        e = self.e
        seen = seen or set()
        have = p.inv.get(item, 0)
        if have >= n:
            return []
        # made already by an earlier step of this plan, beyond what that step needed (a burn of charcoal gives 4)
        spare = min(self.extra.get(item, 0), n - have)
        if spare:
            self.extra[item] -= spare
            have += spare
            if have >= n:
                return []
        need = n - have
        if depth > 6 or item in seen:
            return None
        seen = seen | {item}
        # one's own store
        st = self.own_store_with(p, item)
        if st:
            return [{"do": "take", "item": item, "n": need, "x": st.x, "y": st.y}]
        # the land
        spot = e.find(p, item) if e.sources(item) else None
        if spot:
            extra = 4 if I.info(item).get("food") and depth > 0 else 0     # some is eaten on the way
            step = {"do": "gather", "item": item, "n": need + extra}
            if dist(p.x, p.y, *spot) > 8:
                step.update(x=spot[0], y=spot[1])       # far off: later steps may start from elsewhere
            return [step]
        if item == "seeds" and e.find(p, "fibre"):
            return [{"do": "gather", "item": "fibre", "n": 12}]
        if item in ("meat", "hide", "bone"):
            if not e.herds_of(p):
                return None
            if item == "meat":
                return [{"do": "hunt"}]
            # hide and bone are left where the beast fell: hunt keeping them, as often as it takes
            return [{"do": "hunt", "keep": item}] * min(3, -(-need // 2))
        if item == "fish":
            # only where there is water at hand, and only as many as a day's fishing is likely to bring
            w = self.w
            if not (e.water_near(p) or any(TERRAIN[w.t(x, y)].get("water") for x, y in w.beside(p.x, p.y, 10))):
                return None
            rate = (0.12 * I.best_tool(p.inv, "fish")[1] + 0.1 * p.skill("fish")) * (e.fish_here(p)[1] if e.water_near(p) else 1)
            hours = -(-need // max(0.01, rate))
            return [{"do": "fish", "hours": int(hours)}] if hours <= 12 else None
        if item in ("milk", "wool"):
            pen = next((b for b in self.w.buildings.values() if b.owner == p.id and b.inv.get(item)), None)
            return [{"do": "take", "item": item, "n": need, "x": pen.x, "y": pen.y}] if pen else None
        # bought from a maker who sells it, by one not able at its craft (grand.md Phase 3: each household made its own
        # rope, cloaks and nets, and a tenth of made goods changed hands)
        bought = self.buy(p, item, need)
        if bought:
            return bought
        # making it (each way tried from the same footing; the shortest kept, with what it leaves over)
        best, after, start = None, None, dict(self.extra)
        for r in recipes_making(item):
            self.extra = dict(start)
            runs = -(-need // r["n"])
            steps = self.make(p, r, runs, depth, seen)
            if steps is not None and (best is None or len(steps) < len(best)):
                best, after = steps, dict(self.extra)
                after[item] = after.get(item, 0) + r["n"] * runs - need
        self.extra = after if best is not None else start
        return best

    def sellers(self, item):
        """This hour's stores that post the item for sale and hold it: [(store, trade)]."""
        w = self.w
        if getattr(self, "_sellers_t", None) != w.tick:
            by = {}
            for b in w.buildings.values():
                if b.trade and b.done:
                    for t in b.trade:
                        for k, n in t["give"].items():
                            if b.inv.get(k, 0) >= n:
                                by.setdefault(k, []).append((b, t))
            self._sellers, self._sellers_t = by, w.tick
        return self._sellers.get(item, [])

    def note_want(self, p, item):
        """A want that found no one selling: heard where it was felt, for makers near to answer (c93). Kept five days,
        by cells of 16 steps."""
        cells = self.e.__dict__.setdefault("wants", {})
        heard = cells.setdefault((p.x // 16, p.y // 16), {})
        heard.setdefault(item, []).append(self.w.tick)
        if len(heard[item]) > 40:
            del heard[item][:-40]

    def wanted_near(self, p, days=5):
        """What people within about a cell of one have wanted and found no one selling, lately: Counter(item)."""
        from collections import Counter
        out, cut = Counter(), self.w.tick - days * TPD
        cells = self.e.__dict__.get("wants", {})
        cx, cy = p.x // 16, p.y // 16
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for item, ticks in cells.get((cx + dx, cy + dy), {}).items():
                    out[item] += sum(1 for t in ticks if t >= cut)
        return +out

    def buy(self, p, item, need):
        """Steps to buy need of a made thing at the nearest store that sells it and that one knows (within 20 steps,
        remembered, or beside a market one knows), paid from what one carries or one's own store; None if one is able
        at its craft (a maker makes their own), knows no seller, or cannot pay and still keep food in hand."""
        makers = {r["craft"] for r in recipes_making(item)}
        if not makers or any(p.skill(c) >= 0.3 for c in makers):
            return None
        best = None
        for b, t in self.sellers(item):
            if b.owner in (p.id, p.partner):
                continue
            d = dist(p.x, p.y, b.x, b.y)
            if d > 20 and key(b.x, b.y) not in p.known or d > 60:
                continue
            runs = -(-need // t["give"][item])
            if b.inv.get(item, 0) < runs * t["give"][item]:
                continue
            if best is None or d < best[0]:
                best = (d, b, t, runs)
        if not best:
            self.note_want(p, item)
            return None
        _, b, t, runs = best
        steps = []
        for k, n in t["get"].items():
            short = n * runs - p.inv.get(k, 0)
            food = I.info(k).get("food")
            if short <= 0 and not (food and p.inv.get(k, 0) - n * runs < 4):
                continue
            st = next((s for s in self.holders()[0].get(p.id, []) if s.inv.get(k, 0) >= max(short, 0) + (4 if food else 0)), None)
            if not st:
                return None
            steps.append({"do": "take", "item": k, "n": max(short, 0) + (4 if food else 0), "x": st.x, "y": st.y})
        return steps + [{"do": "trade", "x": b.x, "y": b.y, "item": item, "n": runs}]

    def make(self, p, r, runs, depth, seen):
        e = self.e
        if e.can_try(p, r["craft"]):
            return None
        steps = []
        for k, q in r["ins"].items():
            sub = self.get(p, k, q * runs, depth + 1, seen)
            if sub is None:
                return None
            steps += sub
        for t in r["tools"]:
            if not any(p.inv.get(o) for o in tool_options(t)):
                opts = tool_options(t)
                sub = None
                for o in reversed(opts):
                    sub = self.get(p, o, 1, depth + 1, seen)
                    if sub is not None:
                        break
                if sub is None:
                    return None
                steps += sub
        at = CRAFTS[r["craft"]]["at"]
        if at and r["process"] and e.workshop_for(p, r["craft"]) and not e.workshop_for(p, r["craft"], want_free=True):
            return None                      # the workshops are all busy firing: another task for now
        kinds = [k for k, v in BUILDINGS.items() if r["craft"] in v["roles"].get("workshop", [])] if at else []
        if at and not e.workshop_for(p, r["craft"]) and not any(self.extra.get("@" + k) for k in kinds):
            # (one this plan already builds serves again: a school's mortar fired twice built two lime kilns, c63)
            sub = None
            for kind in sorted(kinds, key=lambda k: BUILDINGS[k]["era"]):
                sub = self.build(p, kind, depth + 1, seen)
                if sub is not None:
                    break
            if sub is None:
                return None
            steps += sub
        steps.append({"do": "craft", "item": r["out"], "n": runs})
        return steps

    def build(self, p, kind, depth=0, seen=None):
        e = self.e
        if depth == 0:
            self.extra = {}
        B = BUILDINGS[kind]
        if B.get("craft") and e.can_try(p, B["craft"]):
            return None
        steps = []
        for k, q in B["cost"].items():
            sub = self.get(p, k, q, depth + 1, seen or set())
            if sub is None:
                return None
            steps += sub
        step = {"do": "build", "kind": kind}
        spot = self.site(p, kind)
        if spot is None:
            return None
        if spot:
            step.update(x=spot[0], y=spot[1])
        steps.append(step)
        self.extra["@" + kind] = 1                  # built by this plan: its later steps may use it
        return steps

    def site(self, p, kind):
        """Where to build: near home if there is one, on the right ground. {} = beside wherever one stands."""
        w = self.w
        B = BUILDINGS[kind]
        home = w.buildings.get(p.home) if p.home else None
        cx, cy = (home.x, home.y) if home else (p.x, p.y)
        need_soil = B["roles"].get("farm") or B["roles"].get("pen")      # a pen on grass feeds its beasts
        near_water = B.get("near") == "water" or B.get("on") == "water"
        if not need_soil and not near_water:
            for r in (1, 2, 3):
                for x, y in w.beside(cx, cy, r):
                    if not self.e.site_ok(p, kind, x, y):
                        return (x, y)
            return {}
        best = None
        for x, y in w.beside(cx, cy, 10):
            if not self.e.site_ok(p, kind, x, y):
                d = dist(cx, cy, x, y) - (2 if need_soil and w.t(x, y) == "," else 0) + \
                    (6 if B["roles"].get("pen") and w.t(x, y) not in ".," else 0)
                if best is None or d < best[0]:
                    best = (d, x, y)
        return (best[1], best[2]) if best else None

    def practise(self, p, craft):
        """Steps that practise a craft once: make its cheapest thing that one can make."""
        opts = []
        for r in RECIPES:
            if r["craft"] == craft:
                self.extra = {}
                steps = self.make(p, r, 1, 0, set())
                if steps is not None:
                    opts.append(steps)
        return min(opts, key=len) if opts else None
