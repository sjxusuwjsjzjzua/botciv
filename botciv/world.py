"""World state: terrain, resources, structures, agents, groups, deals.

Everything here is plain data so a world can be saved to JSON and loaded
back exactly. Rules that change state live in engine.py.
"""
import random
from collections import deque
from dataclasses import dataclass, field, asdict

from . import items as I
from .names import make_name, make_temperament, make_want

GRASS, FOREST, ROCK, WATER, FERTILE = ".", "T", "^", "~", ","
PASSABLE = {GRASS, FOREST, FERTILE}
TERRAIN_NAME = {GRASS: "grass", FOREST: "forest", ROCK: "rock", WATER: "water", FERTILE: "rich soil"}
DIRS = {"north": (0, -1), "south": (0, 1), "east": (1, 0), "west": (-1, 0),
        "northeast": (1, -1), "northwest": (-1, -1), "southeast": (1, 1), "southwest": (-1, 1)}
SEASONS = ["spring", "summer", "autumn", "winter"]


def key(x, y):
    return f"{x},{y}"


def unkey(k):
    x, y = k.split(",")
    return int(x), int(y)


def dist(ax, ay, bx, by):
    return max(abs(ax - bx), abs(ay - by))


def direction(fx, fy, tx, ty):
    dx, dy = tx - fx, ty - fy
    if dx == 0 and dy == 0:
        return "here"
    ns = "north" if dy < 0 else "south" if dy > 0 else ""
    ew = "east" if dx > 0 else "west" if dx < 0 else ""
    if ns and ew and (abs(dx) > 2 * abs(dy)):
        ns = ""
    if ns and ew and (abs(dy) > 2 * abs(dx)):
        ew = ""
    return ns + ew


@dataclass
class Agent:
    id: int
    name: str
    x: int
    y: int
    age: int
    lifespan: int
    strength: int
    speed: int
    sight: int
    temperament: str
    wants: str = ""
    health: int = 10
    satiety: int = 14
    inventory: dict = field(default_factory=dict)
    wear: dict = field(default_factory=dict)       # item -> uses spent on the unit in hand
    recipes: list = field(default_factory=list)     # pair keys known
    groups: list = field(default_factory=list)
    memory: str = ""
    beliefs: dict = field(default_factory=dict)     # name -> text
    ledger: list = field(default_factory=list)      # [tick, other_id, kind, text]
    events: list = field(default_factory=list)      # [tick, text] since last decision
    activity: dict = None
    plan: list = field(default_factory=list)
    routine: list = field(default_factory=list)     # a plan the person chose to repeat
    wake: list = field(default_factory=list)        # reasons to ask the mind now
    last_decided: int = -999
    last_speech_wake: int = -999
    seen: dict = field(default_factory=dict)        # other id -> last tick seen
    health_band: int = 0
    hunger_band: int = 0
    alive: bool = True
    died: int = None
    cause: str = ""
    born: int = 0
    parents: list = field(default_factory=list)
    children: list = field(default_factory=list)
    teachings: list = field(default_factory=list)   # [from_name, text]
    mind: str = "gemini"
    model: str = ""
    failures: int = 0
    calls: int = 0
    resting: bool = False
    pregnant: dict = None                           # {due, partner, name, teachings}
    hunts: int = 0

    def carrying(self):
        return I.weight(self.inventory)

    def capacity(self, cfg):
        return cfg["agent"]["capacity"] + (15 if self.inventory.get("basket") else 0)


@dataclass
class Group:
    id: int
    name: str
    founder: int
    leader: int
    members: list
    rules: str
    join: str = "invite"        # invite | open
    decide: str = "leader"      # leader | vote
    invited: list = field(default_factory=list)
    founded: int = 0
    dissolved: int = None


@dataclass
class Structure:
    id: int
    kind: str
    x: int
    y: int
    owner: int
    access: str = "owner"       # owner | group:<id> | anyone | list
    allow: list = field(default_factory=list)   # agent ids when access == list
    hp: int = 20
    inventory: dict = field(default_factory=dict)
    fuel: int = 0               # fire
    seeds: int = 0              # farm
    planted: int = None
    progress: int = 0           # build ticks done
    done: bool = False
    built: int = 0


class World:
    def __init__(self, cfg):
        self.cfg = cfg
        self.w = cfg["world"]["width"]
        self.h = cfg["world"]["height"]
        self.seed = cfg["world"]["seed"]
        self.rng = random.Random(self.seed)
        self.tick = 0
        self.terrain = []
        self.bushes = {}        # key -> {"b": berries, "strips": n, "regrow": t}
        self.herds = []         # {"id", "x", "y", "size", "grow"}
        self.structures = {}    # id -> Structure
        self.piles = {}         # key -> inventory
        self.signs = {}         # key -> [[author_id, text, tick]]
        self.corpses = {}       # key -> [name, tick]
        self.snares = {}        # key -> owner id
        self.agents = {}        # id -> Agent
        self.groups = {}        # id -> Group
        self.proposals = {}     # id -> dict
        self.promises = []      # dicts
        self.votes = {}         # id -> dict
        self.recipes = {}
        self.next_id = 1
        self.names_taken = set()
        self.eid = 0            # event counter for log ids

    # ---------- ids and lookups ----------
    def new_id(self):
        i = self.next_id
        self.next_id += 1
        return i

    def living(self):
        return [a for a in self.agents.values() if a.alive]

    def by_name(self, name):
        if not name:
            return None
        n = str(name).strip().lower()
        for a in self.agents.values():
            if a.name.lower() == n:
                return a
        return None

    def agents_at(self, x, y):
        return [a for a in self.living() if a.x == x and a.y == y]

    def structure_at(self, x, y):
        for s in self.structures.values():
            if s.x == x and s.y == y:
                return s
        return None

    def group_by_name(self, name):
        if not name:
            return None
        n = str(name).strip().lower()
        for g in self.groups.values():
            if g.dissolved is None and g.name.lower() == n:
                return g
        return None

    def in_bounds(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def t(self, x, y):
        return self.terrain[y][x]

    def passable(self, x, y, agent=None):
        if not self.in_bounds(x, y) or self.t(x, y) not in PASSABLE:
            return False
        s = self.structure_at(x, y)
        if s and s.done and s.kind in ("wall", "shelter") and agent is not None:
            return self.may_use(agent, s)
        if s and s.done and s.kind == "wall" and agent is None:
            return False
        return True

    def may_use(self, agent, s):
        if s.owner == agent.id or s.access == "anyone":
            return True
        if s.access.startswith("group:"):
            gid = int(s.access.split(":")[1])
            g = self.groups.get(gid)
            return bool(g and g.dissolved is None and agent.id in g.members)
        if s.access == "list":
            return agent.id in s.allow
        return False

    # ---------- time ----------
    def tpd(self):
        return self.cfg["world"]["ticks_per_day"]

    def day(self):
        return self.tick // self.tpd()

    def hour(self):
        return self.tick % self.tpd()

    def season(self):
        d = self.cfg["world"]["days_per_season"]
        return SEASONS[(self.day() // d) % 4]

    def year(self):
        return self.day() // (self.cfg["world"]["days_per_season"] * 4)

    def is_night(self):
        return self.hour() >= self.cfg["world"]["night_from"]

    def ticks_per_year(self):
        return self.tpd() * self.cfg["world"]["days_per_season"] * 4

    def when(self, tick=None):
        t = self.tick if tick is None else tick
        tpd = self.tpd()
        d = t // tpd
        h = t % tpd
        return f"day {d + 1} {hour_name(h, self.cfg)}"

    def sight(self, a):
        base = self.cfg["agent"]["sight_night"] if self.is_night() else a.sight
        return base

    # ---------- generation ----------
    def generate(self):
        rng = self.rng
        w, h = self.w, self.h
        elev = smooth_noise(rng, w, h, 4)
        moist = smooth_noise(rng, w, h, 3)
        grid = [[GRASS] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                e, m = elev[y][x], moist[y][x]
                if e > 0.80:
                    grid[y][x] = ROCK
                elif e < 0.14:
                    grid[y][x] = WATER
                elif m > 0.58:
                    grid[y][x] = FOREST
        # a river: a meandering walk from one edge to the other
        if rng.random() < 0.8:
            vertical = rng.random() < 0.5
            pos = rng.randrange(w // 4, 3 * w // 4)
            length = h if vertical else w
            for i in range(length):
                x, y = (pos, i) if vertical else (i, pos)
                grid[y][x] = WATER
                if rng.random() < 0.3:
                    pos = max(2, min((w if vertical else h) - 3, pos + rng.choice([-1, 1])))
                    x, y = (pos, i) if vertical else (i, pos)
                    grid[y][x] = WATER
            # a couple of fords so the two banks meet
            for _ in range(2):
                i = rng.randrange(2, length - 2)
                for p in range(max(0, pos - 2), min(w if vertical else h, pos + 3)):
                    x, y = (p, i) if vertical else (i, p)
                    if grid[y][x] == WATER:
                        grid[y][x] = GRASS
        # fertile ground by water
        share = self.cfg["world"]["fertile_share"]
        for y in range(h):
            for x in range(w):
                if grid[y][x] == GRASS and any(
                        0 <= x + dx < w and 0 <= y + dy < h and grid[y + dy][x + dx] == WATER
                        for dx in (-1, 0, 1) for dy in (-1, 0, 1)) and rng.random() < share:
                    grid[y][x] = FERTILE
        # keep only the largest walkable region
        comp = largest_component(grid, w, h)
        for y in range(h):
            for x in range(w):
                if grid[y][x] in PASSABLE and (x, y) not in comp:
                    grid[y][x] = ROCK
        self.terrain = ["".join(r) for r in grid]
        self.recipes = I.make_recipes(rng)
        cells = sorted(comp)
        rng.shuffle(cells)
        # bushes on grass and forest
        n = 0
        for (x, y) in cells:
            if n >= self.cfg["world"]["bushes"]:
                break
            if self.t(x, y) in (GRASS, FOREST):
                self.bushes[key(x, y)] = {"b": rng.randint(3, self.cfg["resources"]["bush_max"]), "strips": 0, "regrow": 0}
                n += 1
        grass = [c for c in cells if self.t(*c) == GRASS]
        for i in range(self.cfg["world"]["herds"]):
            x, y = rng.choice(grass)
            lo, hi = self.cfg["world"]["herd_size"]
            self.herds.append({"id": i + 1, "x": x, "y": y, "size": rng.randint(lo, hi), "grow": 0})
        # people: a few sibling pairs, the rest alone
        spots = [c for c in cells if self.t(*c) != WATER]
        count = self.cfg["world"]["agents"]
        made = []
        while len(made) < count:
            x, y = rng.choice(spots)
            a = self.make_agent(x, y)
            made.append(a)
            if len(made) < count and rng.random() < 0.3:
                nx, ny = self.free_near(x, y)
                b = self.make_agent(nx, ny)
                made.append(b)
                self.add_ledger(a, b.id, "kin", f"{b.name} is your sibling; you grew up together")
                self.add_ledger(b, a.id, "kin", f"{a.name} is your sibling; you grew up together")
                a.beliefs[b.name] = "my sibling; we grew up together"
                b.beliefs[a.name] = "my sibling; we grew up together"
        return self

    def free_near(self, x, y):
        for r in range(1, 4):
            opts = [(x + dx, y + dy) for dx in range(-r, r + 1) for dy in range(-r, r + 1)
                    if self.passable(x + dx, y + dy)]
            if opts:
                return self.rng.choice(opts)
        return x, y

    def make_agent(self, x, y, age=None, parents=None):
        rng = self.rng
        cfg = self.cfg["agent"]
        tpy = self.ticks_per_year()
        name = make_name(rng, self.names_taken)
        self.names_taken.add(name)
        lo, hi = cfg["lifespan_years"]
        if age is None:
            a0, a1 = cfg["start_age_years"]
            age = int(rng.uniform(a0, a1) * tpy)
        a = Agent(
            id=self.new_id(), name=name, x=x, y=y, age=age,
            lifespan=int(rng.uniform(lo, hi) * tpy),
            strength=rng.randint(1, 3), speed=rng.randint(1, 3), sight=rng.choice([4, 5, 5, 6]),
            temperament=make_temperament(rng), wants=make_want(rng), satiety=cfg["start_satiety"],
            health=cfg["max_health"], born=self.tick - age, parents=parents or [])
        if a.lifespan <= a.age:
            a.lifespan = a.age + tpy
        if parents is None and rng.random() < 0.5:
            a.recipes.append(rng.choice(sorted(self.recipes)))
        if parents is None and self.tick == 0:
            a.inventory = {"berries": rng.randint(3, 6)}
        self.agents[a.id] = a
        return a

    def add_ledger(self, a, other_id, kind, text):
        a.ledger.append([self.tick, other_id, kind, text])
        if len(a.ledger) > 200:
            a.ledger = a.ledger[-200:]

    # ---------- save / load ----------
    def to_dict(self):
        st = self.rng.getstate()
        return {
            "cfg": self.cfg, "tick": self.tick, "rng": [st[0], list(st[1]), st[2]],
            "terrain": self.terrain, "bushes": self.bushes, "herds": self.herds,
            "structures": {str(k): asdict(v) for k, v in self.structures.items()},
            "piles": self.piles, "signs": self.signs, "corpses": self.corpses, "snares": self.snares,
            "agents": {str(k): asdict(v) for k, v in self.agents.items()},
            "groups": {str(k): asdict(v) for k, v in self.groups.items()},
            "proposals": {str(k): v for k, v in self.proposals.items()},
            "promises": self.promises, "votes": {str(k): v for k, v in self.votes.items()},
            "recipes": self.recipes, "next_id": self.next_id,
            "names_taken": sorted(self.names_taken), "eid": self.eid,
        }

    @classmethod
    def from_dict(cls, d):
        w = cls(d["cfg"])
        r = d["rng"]
        w.rng.setstate((r[0], tuple(r[1]), r[2]))
        w.tick = d["tick"]
        w.terrain = d["terrain"]
        w.bushes = d["bushes"]
        w.herds = d["herds"]
        w.structures = {int(k): Structure(**v) for k, v in d["structures"].items()}
        w.piles = d["piles"]
        w.signs = d["signs"]
        w.corpses = d["corpses"]
        w.snares = d["snares"]
        w.agents = {int(k): Agent(**v) for k, v in d["agents"].items()}
        w.groups = {int(k): Group(**v) for k, v in d["groups"].items()}
        w.proposals = {int(k): v for k, v in d["proposals"].items()}
        w.promises = d["promises"]
        w.votes = {int(k): v for k, v in d["votes"].items()}
        w.recipes = d["recipes"]
        w.next_id = d["next_id"]
        w.names_taken = set(d["names_taken"])
        w.eid = d["eid"]
        return w

    # ---------- pathing ----------
    def path(self, agent, tx, ty, adjacent_ok=False):
        """BFS from agent to (tx, ty). Returns list of steps or None."""
        start = (agent.x, agent.y)
        if start == (tx, ty) or (adjacent_ok and dist(agent.x, agent.y, tx, ty) <= 1):
            return []
        goal_ok = (lambda x, y: dist(x, y, tx, ty) <= 1) if adjacent_ok else (lambda x, y: (x, y) == (tx, ty))
        prev = {start: None}
        q = deque([start])
        while q:
            cx, cy = q.popleft()
            if goal_ok(cx, cy):
                out = []
                c = (cx, cy)
                while c != start:
                    out.append(c)
                    c = prev[c]
                return out[::-1]
            for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0), (1, -1), (1, 1), (-1, 1), (-1, -1)):
                nx, ny = cx + dx, cy + dy
                if (nx, ny) not in prev and self.passable(nx, ny, agent):
                    prev[(nx, ny)] = (cx, cy)
                    q.append((nx, ny))
        return None


def hour_name(h, cfg):
    night = cfg["world"]["night_from"]
    if h >= night:
        return "night"
    if h == 0:
        return "dawn"
    if h <= 2:
        return "morning"
    if h <= 4:
        return "midday"
    if h <= 6:
        return "afternoon"
    return "evening"


def smooth_noise(rng, w, h, passes):
    g = [[rng.random() for _ in range(w)] for _ in range(h)]
    for _ in range(passes):
        n = [[0.0] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                s = c = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        xx, yy = x + dx, y + dy
                        if 0 <= xx < w and 0 <= yy < h:
                            s += g[yy][xx]
                            c += 1
                n[y][x] = s / c
        g = n
    lo = min(min(r) for r in g)
    hi = max(max(r) for r in g)
    return [[(v - lo) / (hi - lo + 1e-9) for v in r] for r in g]


def largest_component(grid, w, h):
    seen = set()
    best = set()
    for y in range(h):
        for x in range(w):
            if grid[y][x] in PASSABLE and (x, y) not in seen:
                comp = set()
                q = deque([(x, y)])
                seen.add((x, y))
                while q:
                    cx, cy = q.popleft()
                    comp.add((cx, cy))
                    for dx, dy in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in seen and grid[ny][nx] in PASSABLE:
                            seen.add((nx, ny))
                            q.append((nx, ny))
                if len(comp) > len(best):
                    best = comp
    return best
