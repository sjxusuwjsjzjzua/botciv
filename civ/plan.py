"""The recipe-tree planner: the steps to have n of something, from what one holds, sees, remembers
and knows how to do. Bots plan everything with it; a person can name a goal and have it laid out.

It is a helper, not a mind: it never decides what is worth having, only how to get it."""
from .content import TERRAIN, DEPOSITS, WILD, TAME, BUILDINGS, CRAFTS, RECIPES
from .content import items as I
from .content.crafts import recipes_making, tool_options
from .world import dist, key

ANIMAL = {"meat": "hunt", "hide": "hunt", "bone": "hunt", "fish": "fish"}


class Planner:
    def __init__(self, engine):
        self.e = engine
        self.w = engine.w

    def holding(self, p, item):
        return p.inv.get(item, 0) + sum(b.inv.get(item, 0) for b in self.e.stores_beside(p))

    def own_store_with(self, p, item):
        """One's own store, or workshop where a firing left it (bricks in the kiln), holding the item."""
        for b in self.w.buildings.values():
            roles = BUILDINGS[b.kind]["roles"]
            if not (b.done and b.inv.get(item)) or b.process:
                continue
            if (b.owner == p.id and "store" in roles) or ("workshop" in roles and self.w.may_use(p, b)):
                return b                    # one's store, or a workshop one may use where a firing left it
        return None

    def get(self, p, item, n=1, depth=0, seen=None):
        """Steps toward holding n of item, or None if no way is known. [] if already held."""
        e = self.e
        seen = seen or set()
        have = p.inv.get(item, 0)
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
            if e.herds_of(p):
                return [{"do": "hunt"}]
            return None
        if item == "fish":
            return [{"do": "fish", "hours": 6}]
        if item in ("milk", "wool"):
            pen = next((b for b in self.w.buildings.values() if b.owner == p.id and b.inv.get(item)), None)
            return [{"do": "take", "item": item, "n": need, "x": pen.x, "y": pen.y}] if pen else None
        # making it
        best = None
        for r in recipes_making(item):
            steps = self.make(p, r, -(-need // r["n"]), depth, seen)
            if steps is not None and (best is None or len(steps) < len(best)):
                best = steps
        return best

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
        if at and not e.workshop_for(p, r["craft"]):
            kinds = [k for k, v in BUILDINGS.items() if r["craft"] in v["roles"].get("workshop", [])]
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
                steps = self.make(p, r, 1, 0, set())
                if steps is not None:
                    opts.append(steps)
        return min(opts, key=len) if opts else None
