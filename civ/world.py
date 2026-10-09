"""The world's state, and nothing that decides. Everything here is saved whole as JSON."""
import random
from dataclasses import dataclass, field, asdict

from .content import TERRAIN, PASSABLE, BUILDINGS
from .content import items as I

TPD = 12            # hours a day; the last NIGHT_FROM.. are night
NIGHT_FROM = 9
DPS = 10            # days a season
TPY = TPD * DPS * 4
SEASONS = ["spring", "summer", "autumn", "winter"]


def key(x, y):
    return f"{x},{y}"


def unkey(k):
    x, y = k.split(",")
    return int(x), int(y)


def dist(x1, y1, x2, y2):
    return max(abs(x1 - x2), abs(y1 - y2))


def direction(x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    ns = "south" if dy > 0 else "north" if dy < 0 else ""
    ew = "east" if dx > 0 else "west" if dx < 0 else ""
    if ns and ew and abs(dx) > 2 * abs(dy):
        ns = ""
    if ns and ew and abs(dy) > 2 * abs(dx):
        ew = ""
    return ns + ew or "here"


@dataclass
class Person:
    id: int
    name: str
    x: int
    y: int
    born: int
    lifespan: int
    mind: str = "bot"                   # bot | llm
    model: str = ""
    traits: dict = field(default_factory=dict)      # industry, sociability, boldness, generosity, curiosity, ambition 0..1
    temperament: str = ""
    wants: str = ""
    vocation: str = ""                  # what a bot drifts toward (farmer, potter, smith...), never shown
    strength: int = 2
    health: float = 10.0
    satiety: float = 16.0
    sick: dict = None
    inv: dict = field(default_factory=dict)
    wear: dict = field(default_factory=dict)        # item -> uses spent on the one in use
    skills: dict = field(default_factory=dict)      # craft or general skill -> 0..1
    home: int = None                    # a building id where they sleep
    intent: dict = None                 # {"goal", "plan": [steps], "routine": bool, "since"}
    act: dict = None                    # the step being done now
    rest: bool = False
    memory: str = ""
    self_view: str = ""
    life: list = field(default_factory=list)        # [tick, text] kept for life
    beliefs: dict = field(default_factory=dict)     # name -> text
    known: dict = field(default_factory=dict)       # key -> [kind, label, tick]: places remembered
    rel: dict = field(default_factory=dict)         # other id (str) -> {"trust": -1..1, "met": tick, "kin": str}
    ledger: list = field(default_factory=list)      # [tick, other_id, kind, text]
    events: list = field(default_factory=list)      # [tick, text] since last decision (llm)
    wake: list = field(default_factory=list)
    last_decided: int = -999
    partner: int = None
    parents: list = field(default_factory=list)
    children: list = field(default_factory=list)
    heir: int = None
    groups: list = field(default_factory=list)
    pregnant: dict = None
    ideas: list = field(default_factory=list)
    alive: bool = True
    died: int = None
    cause: str = ""
    calls: int = 0
    failures: int = 0

    def age(self, tick):
        return (tick - self.born) / TPY

    def adult(self, tick):
        return self.age(tick) >= 14

    def load(self):
        return max(0.0, I.weight(self.inv) - sum(I.ITEMS[k]["w"] for k in I.worn(self.inv)))

    def capacity(self, tick):
        y = self.age(tick)
        base = 30.0                     # what one carries in arms, basket and pack
        if y < 14:
            base *= 0.35 + 0.65 * y / 14
        elif y > 45:
            base *= max(0.4, 1 - 0.02 * (y - 45))
        return round(base + I.best(self.inv, "carry")[0], 1)

    def max_health(self, tick):
        past = self.age(tick) - 55
        return max(4, 10 - int(past // 6) - 1) if past >= 0 else 10

    def skill(self, k):
        return self.skills.get(k, 0.0)


@dataclass
class Building:
    id: int
    kind: str
    x: int
    y: int
    owner: int                          # a person id, or -gid for a group's
    access: str = "owner"               # owner | anyone | group:<id> | list
    allow: list = field(default_factory=list)
    hp: int = 20
    done: bool = False
    progress: float = 0
    built: int = 0
    inv: dict = field(default_factory=dict)
    fuel: int = 0
    crop: dict = None                   # farm: {"what", "n", "sown", "ripe", "yield"}
    animals: dict = field(default_factory=dict)     # pen: kind -> count
    fed: int = 0                        # pen: days of fodder in hand (hay/grain put in)
    process: dict = None                # workshop: {"recipe", "done_at", "by", "runs"}
    trade: list = field(default_factory=list)       # posted: [{"give": {}, "get": {}}]
    name: str = ""
    text: str = ""
    books: list = field(default_factory=list)       # library: craft names of books kept


@dataclass
class Group:
    id: int
    name: str
    founder: int
    leader: int
    members: list
    rules: str = ""
    decide: str = "leader"              # leader | vote
    join: str = "invite"                # invite | open
    invited: list = field(default_factory=list)
    dues: dict = field(default_factory=dict)        # {"item": n} each season, into the treasury
    treasury: int = None                # a building id
    laws: list = field(default_factory=list)        # [tick, text, written(bool)]
    founded: int = 0
    dissolved: int = None


class World:
    def __init__(self, cfg):
        self.cfg = cfg
        self.w = cfg["width"]
        self.h = cfg["height"]
        self.seed = cfg["seed"]
        self.rng = random.Random(self.seed)
        self.tick = 0
        self.terrain = []
        self.deposits = {}      # key -> {"kind", "left", "size"}
        self.herds = []         # {"id", "kind", "x", "y", "n"}
        self.packs = []         # wolves {"id", "x", "y", "n", "hunger"}
        self.people = {}
        self.buildings = {}
        self.at = {}            # key -> building id (one a tile; roads are separate)
        self.roads = set()      # keys
        self.piles = {}         # key -> inv
        self.signs = {}         # key -> [[author, text, tick, written]]
        self.places = []        # [x, y, name, by, tick]
        self.fish = {}          # "cx,cy" (a stretch of water, 8 by 8 tiles) -> fish left in it (M2, c64)
        self.groups = {}
        self.offers = {}        # id -> an offer (deal, child, pledge, invite, teach)
        self.promises = []
        self.services = []
        self.votes = {}
        self.writings = {}      # id -> {"text", "by", "tick", "kind"}: what is written on tablets and parchment
        self.lost = {}          # craft -> tick the last who knew it died
        self.firsts = {}        # craft -> [tick, person id]: who first practised it here
        self.next_id = 1
        self.eid = 0
        self.names = set()
        self.grid = {}          # (cx, cy) -> set of person ids (not saved)

    # ---- ids, time ----
    def new_id(self):
        self.next_id += 1
        return self.next_id - 1

    def hour(self):
        return self.tick % TPD

    def day(self):
        return self.tick // TPD

    def season(self):
        return SEASONS[(self.day() // DPS) % 4]

    def year(self):
        return self.day() // (DPS * 4)

    def is_night(self):
        return self.hour() >= NIGHT_FROM

    def when(self, t=None):
        t = self.tick if t is None else t
        h = t % TPD
        part = "dawn" if h < 2 else "morning" if h < 5 else "afternoon" if h < 8 else "evening" if h < 9 else "night"
        return f"day {t // TPD + 1} {part}"

    # ---- land ----
    def inb(self, x, y):
        return 0 <= x < self.w and 0 <= y < self.h

    def t(self, x, y):
        return self.terrain[y][x]

    def cost(self, x, y):
        """Hours to step onto a tile, 0 if one cannot."""
        if not self.inb(x, y):
            return 0
        b = self.building_at(x, y)
        if b and b.done and "bridge" in BUILDINGS[b.kind]["roles"]:
            return 1
        c = TERRAIN[self.t(x, y)]["cost"]
        if not c:
            return 0
        if b and b.done and "wall" in BUILDINGS[b.kind]["roles"]:
            return 0
        if key(x, y) in self.roads:
            return 0.5
        return c

    def passable(self, x, y):
        return self.cost(x, y) > 0

    def building_at(self, x, y):
        bid = self.at.get(key(x, y))
        return self.buildings.get(bid) if bid else None

    def beside(self, x, y, r=1):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if self.inb(x + dx, y + dy):
                    yield x + dx, y + dy

    # ---- people ----
    def living(self):
        return [p for p in self.people.values() if p.alive]

    def cell(self, x, y):
        return (x // 8, y // 8)

    def place(self, p, x, y):
        old = self.cell(p.x, p.y)
        s = self.grid.get(old)
        if s is not None:
            s.discard(p.id)
        p.x, p.y = x, y
        if p.alive:
            self.grid.setdefault(self.cell(x, y), set()).add(p.id)

    def rebuild_grid(self):
        self.grid = {}
        for p in self.living():
            self.grid.setdefault(self.cell(p.x, p.y), set()).add(p.id)

    def near(self, x, y, r):
        """Living people within r steps."""
        out = []
        for cy in range((y - r) // 8, (y + r) // 8 + 1):
            for cx in range((x - r) // 8, (x + r) // 8 + 1):
                for pid in self.grid.get((cx, cy), ()):
                    p = self.people[pid]
                    if p.alive and dist(x, y, p.x, p.y) <= r:
                        out.append(p)
        return out

    def by_name(self, name):
        n = str(name or "").strip().lower()
        for p in self.people.values():
            if p.name.lower() == n and p.alive:
                return p
        return None

    def empty(self, b):
        """A finished building whose owner is no living person and no group: the dead left it with no
        heir. Anyone may claim it; left empty it falls to ruin. Monuments are never empty: they keep
        their maker's name."""
        if not b.done or "monument" in BUILDINGS[b.kind]["roles"]:
            return False
        if b.owner < 0:                                   # a group's: empty once the group is no more
            g = self.groups.get(-b.owner)
            return not g or g.dissolved is not None
        o = self.people.get(b.owner)
        return not (o and o.alive)

    def may_use(self, p, b):
        if b.owner == p.id or b.access == "anyone":
            return True
        if b.owner < 0:                                   # a group's
            g = self.groups.get(-b.owner)
            return bool(g and g.dissolved is None and p.id in g.members and b.access in ("owner", "members"))
        if p.partner is not None and p.partner == b.owner:
            return True
        if b.owner in p.parents and not p.adult(self.tick):
            return True                                   # a child eats at home
        if b.access.startswith("group:"):
            g = self.groups.get(int(b.access.split(":")[1]))
            return bool(g and g.dissolved is None and p.id in g.members)
        if b.access == "list":
            return p.id in b.allow
        for s in self.services:
            if not s["done"] and s["servant"] == p.id and s["master"] == b.owner:
                return True
        return False

    # ---- fish: each stretch of water (8 by 8 tiles) holds a stock, drawn down by catches, regrowing ----
    FISH_PER_TILE = 15
    FISH_CELL = 8

    def fish_cell(self, x, y):
        return f"{x // self.FISH_CELL},{y // self.FISH_CELL}"

    def fish_cap(self, k):
        cache = self.__dict__.setdefault("_fish_caps", {})
        if k not in cache:
            cx, cy = (int(v) for v in k.split(","))
            n = sum(1 for y in range(cy * self.FISH_CELL, min(self.h, (cy + 1) * self.FISH_CELL))
                    for x in range(cx * self.FISH_CELL, min(self.w, (cx + 1) * self.FISH_CELL)) if self.terrain[y][x] in "~")
            cache[k] = n * self.FISH_PER_TILE
        return cache[k]

    def fish_left(self, k):
        return self.fish.get(k, self.fish_cap(k))

    # ---- saving ----
    def to_dict(self):
        st = self.rng.getstate()
        return {"cfg": self.cfg, "tick": self.tick, "rng": [st[0], list(st[1]), st[2]], "terrain": self.terrain,
                "deposits": self.deposits, "herds": self.herds, "packs": self.packs,
                "people": {str(k): asdict(v) for k, v in self.people.items()},
                "buildings": {str(k): asdict(v) for k, v in self.buildings.items()},
                "roads": sorted(self.roads), "piles": self.piles, "signs": self.signs, "places": self.places, "fish": self.fish,
                "groups": {str(k): asdict(v) for k, v in self.groups.items()},
                "offers": {str(k): v for k, v in self.offers.items()}, "promises": self.promises,
                "services": self.services, "votes": {str(k): v for k, v in self.votes.items()},
                "writings": {str(k): v for k, v in self.writings.items()}, "lost": self.lost, "firsts": self.firsts,
                "next_id": self.next_id, "eid": self.eid, "names": sorted(self.names)}

    @classmethod
    def from_dict(cls, d):
        w = cls(d["cfg"])
        r = d["rng"]
        w.rng.setstate((r[0], tuple(r[1]), r[2]))
        w.tick = d["tick"]
        w.terrain = d["terrain"]
        w.deposits = d["deposits"]
        w.herds = d["herds"]
        w.packs = d["packs"]
        w.people = {int(k): Person(**v) for k, v in d["people"].items()}
        w.buildings = {int(k): Building(**v) for k, v in d["buildings"].items()}
        w.at = {key(b.x, b.y): b.id for b in w.buildings.values() if not BUILDINGS[b.kind].get("overlay")}
        w.roads = set(d["roads"])
        w.piles = d["piles"]
        w.signs = d["signs"]
        w.places = d["places"]
        w.fish = d.get("fish", {})
        w.groups = {int(k): Group(**v) for k, v in d["groups"].items()}
        w.offers = {int(k): v for k, v in d["offers"].items()}
        w.promises = d["promises"]
        w.services = d["services"]
        w.votes = {int(k): v for k, v in d["votes"].items()}
        w.writings = {int(k): v for k, v in d["writings"].items()}
        w.lost = d["lost"]
        w.firsts = d["firsts"]
        w.next_id = d["next_id"]
        w.eid = d["eid"]
        w.names = set(d["names"])
        w.rebuild_grid()
        return w
