"""The world's state, and nothing that decides. Everything here is saved whole as JSON."""
import random
from dataclasses import dataclass, field, asdict

from .content import TERRAIN, PASSABLE, BUILDINGS, TAME
from .content import items as I

TCOST = {c: t["cost"] for c, t in TERRAIN.items()}
TPD = 12            # hours a day; the last NIGHT_FROM.. are night
NIGHT_FROM = 9
DPS = 10            # days a season
TPY = TPD * DPS * 4
SEASONS = ["spring", "summer", "autumn", "winter"]


def key(x, y):
    return f"{x},{y}"


class TileMap(dict):
    """A dict keyed "x,y" (as saved) that also keeps each value in a flat list by tile (`flat[y * w + x]`),
    so the hot loops look a tile up without building its key. Writes go through the dict as before."""
    def __init__(self, w, h, src=None):
        super().__init__()
        self.W, self.H = w, h
        self.flat = [None] * (w * h)
        for k, v in (src or {}).items():
            self[k] = v

    def _i(self, k):
        try:
            x, y = (int(v) for v in k.split(","))
        except (ValueError, AttributeError):
            return None
        return y * self.W + x if 0 <= x < self.W and 0 <= y < self.H else None

    def __setitem__(self, k, v):
        super().__setitem__(k, v)
        i = self._i(k)
        if i is not None:
            self.flat[i] = v

    def __delitem__(self, k):
        super().__delitem__(k)
        i = self._i(k)
        if i is not None:
            self.flat[i] = None

    def pop(self, k, *default):
        if k in self:
            v = dict.__getitem__(self, k)
            del self[k]
            return v
        if default:
            return default[0]
        raise KeyError(k)

    def setdefault(self, k, default=None):
        if k not in self:
            self[k] = default
        return dict.__getitem__(self, k)

    def update(self, *args, **kw):
        for k, v in dict(*args, **kw).items():
            self[k] = v

    def clear(self):
        super().clear()
        self.flat = [None] * (self.W * self.H)

    def popitem(self):
        k, v = super().popitem()
        i = self._i(k)
        if i is not None:
            self.flat[i] = None
        return k, v


class TileSet(set):
    """A set of "x,y" keys (roads) with a flat list of which tiles are in it, and a count of its changes (v)."""
    v = 0

    def __init__(self, w, h, src=()):
        super().__init__()
        self.W, self.H = w, h
        self.flat = [False] * (w * h)
        for k in src:
            self.add(k)

    def _i(self, k):
        return TileMap._i(self, k)

    def add(self, k):
        super().add(k)
        self.v += 1
        i = self._i(k)
        if i is not None:
            self.flat[i] = True

    def discard(self, k):
        super().discard(k)
        self.v += 1
        i = self._i(k)
        if i is not None:
            self.flat[i] = False

    def remove(self, k):
        super().remove(k)
        self.discard(k)


def unkey(k):
    x, y = k.split(",")
    return int(x), int(y)


_TILES = {}


def tile_of(k):
    """unkey(k) for a "x,y" key, None for any other (a herd's, a price's); remembered, as people's memories of
    places are read over and over."""
    t = _TILES.get(k)
    if t is None:
        if "," not in k:
            return None
        x, y = k.split(",", 1)
        if not (x.lstrip("-").isdigit() and y.lstrip("-").isdigit()):
            return None                         # "toll3,4": a toll paid there, not a tile (it broke every search, c85-c89)
        t = _TILES[k] = (int(x), int(y))
    return t


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
    led: dict = field(default_factory=dict)         # beasts one leads, carrying for one: {"donkey": 2} (c86)
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
    people: str = ""                    # the people one is of (civ/content/peoples.py), "" in the old lands
    used: dict = field(default_factory=dict)        # craft -> tick last practised (skills fade unused, c68)
    news: dict = field(default_factory=dict)        # news id -> [tick heard, who told (0: saw it)] (c73)
    renown: int = 0                     # how many have heard word of one (c73)
    held: dict = None                   # {"by": captor id, "since": tick, "price": goods}: held for ransom (c76)
    feel: dict = field(default_factory=dict)        # people -> -1..1: what one thinks of that people
    # towns (towns_spec §3.2; only in a towns world, where x, y are derived from pos)
    pos: list = None                    # [X, Y] metres: where one is this hour
    inside: int = None                  # the building one is inside (home at night, a workshop at work)

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
        return round(base + I.best(self.inv, "carry")[0] + sum(TAME[k].get("pack", 0) * n for k, n in self.led.items()), 1)

    def max_health(self, tick):
        past = self.age(tick) - 55
        return max(4, 10 - int(past // 6) - 1) if past >= 0 else 10

    def skill(self, k):
        return self.skills.get(k, 0.0)


OWNERSHIP = [0]     # bumped whenever any building's owner is set
LAND = [0]          # bumped whenever a wall or a bridge is added, removed, finished or changed: who can walk where
KINDS = [0]         # bumped whenever a standing building's kind is changed: Buildings.roles() looks again
ROLE_CELL = 16      # Buildings.roles() keeps buildings by role in cells of 16 by 16 tiles
TILE_M = 1000       # towns (docs/towns_spec.md §2): a land tile is this many metres a side
CELL_M = 4          # ... and a cell of the occupancy index this many


def tags_of(kind):
    """What a building of this kind can be asked for by: its roles, and "workshop:<craft>" for each craft it serves."""
    B = BUILDINGS.get(kind)
    if not B:
        return ()
    roles = B["roles"]
    out = list(roles)
    out += ["workshop:" + c for c in roles.get("workshop", ())]
    if B.get("overlay"):
        out.append("~overlay")
    return out


def _blocks(kind):
    roles = BUILDINGS.get(kind, {}).get("roles", {})
    return "wall" in roles or "bridge" in roles


class Buildings(dict):
    """id -> Building, counting additions and removals (World.owned() keeps its index while nothing changed), and
    keeping the buildings by role and cell (roles()), so a search for a kind of building looks only at that kind."""
    version = 0

    def __setitem__(self, k, v):
        old = self.get(k)
        super().__setitem__(k, v)
        self.version += 1
        if _blocks(getattr(v, "kind", None)) or (old is not None and _blocks(old.kind)):
            LAND[0] += 1
        if self.__dict__.get("_roles") is not None:
            if old is not None:
                self._unindex(old)
            self._index(v)

    def __delitem__(self, k):
        old = self[k]
        super().__delitem__(k)
        self.version += 1
        if _blocks(old.kind):
            LAND[0] += 1
        if self.__dict__.get("_roles") is not None:
            self._unindex(old)

    def roles(self):
        """tag -> (ids, {cell: {id: building}}, {tile (x, y): {id: building}}) for every tag of tags_of()."""
        if self.__dict__.get("_roles") is None or self.__dict__.get("_roles_k") != KINDS[0]:
            self._roles, self._roles_k = {}, KINDS[0]
            for b in self.values():
                self._index(b)
        return self._roles

    def _index(self, b):
        c, t = (b.x // ROLE_CELL, b.y // ROLE_CELL), (b.x, b.y)
        for tag in tags_of(b.kind):
            ids, cells, tiles = self._roles.setdefault(tag, (set(), {}, {}))
            ids.add(b.id)
            cells.setdefault(c, {})[b.id] = b
            tiles.setdefault(t, {})[b.id] = b

    def _unindex(self, b):
        c, t = (b.x // ROLE_CELL, b.y // ROLE_CELL), (b.x, b.y)
        for tag in tags_of(b.kind):
            ids, cells, tiles = self._roles.get(tag, (set(), {}, {}))
            ids.discard(b.id)
            cells.get(c, {}).pop(b.id, None)
            tiles.get(t, {}).pop(b.id, None)

    def pop(self, k, *default):
        if k in self:
            v = self[k]
            del self[k]
            return v
        return super().pop(k, *default)


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
    # towns (towns_spec §3.1; only in a towns world, where x, y are derived from pos)
    pos: list = None                    # [X, Y] metres: its centre
    angle: float = 0.0                  # degrees: its front (door side) faces (sin a, cos a)
    size: list = None                   # [w, d] metres: its footprint, an oriented rectangle
    door: list = None                   # [X, Y]: where one stands to use it or goes in
    site: int = None                    # the settlement it belongs to
    plot: int = None                    # the plot it stands on (None: commons, fields, outlying)
    ruin: int = None                    # the hour it fell to ruin (kept until cleared)
    style: str = ""                     # the people whose way it was built in, for the viewer

    def __setattr__(self, name, value):
        if name == "owner":
            OWNERSHIP[0] += 1                           # who owns what has changed: World.owned() looks again
        elif name in ("done", "kind") and _blocks(value if name == "kind" else self.kind):
            LAND[0] += 1                                # a wall or bridge rose or changed: the ways change
        if name == "kind" and "kind" in self.__dict__:
            KINDS[0] += 1                               # what it is changed: Buildings.roles() looks again
        object.__setattr__(self, name, value)


# fields a towns world adds to people and buildings: left out of saves while at their defaults, so the saves of
# worlds without towns stay as they were
TOWN_FIELDS = {"pos": None, "inside": None, "angle": 0.0, "size": None, "door": None, "site": None, "plot": None,
               "ruin": None, "style": ""}


def slim(d):
    for k, v in TOWN_FIELDS.items():
        if k in d and d[k] == v:
            del d[k]
    return d


@dataclass
class Settlement:
    """A place where homes are laid out together (towns_spec §3.3): its form, lanes, plots and fields, in metres."""
    id: int
    name: str
    x: int                              # its land tile
    y: int
    people: str = ""                    # its people (the founders'; recounted each season as the majority)
    form: str = "street"                # street | waterfront | ring | cluster | scatter
    founded: int = 0
    centre: list = None                 # [X, Y]: where it began
    green: list = None                  # [X, Y, w, h]: the open centre
    lanes: list = field(default_factory=list)       # [{"id", "pts": [[X, Y], ...], "w", "kind"}]
    plots: list = field(default_factory=list)       # [{"id", "rect", "lane", "side", "kind", "holder", "since"}]
    edge: list = field(default_factory=list)        # [[X, Y], ...] round the plots
    walled: bool = False
    burial: int = None                  # the burial plot's id
    fields: list = field(default_factory=list)      # [[x, y]] land tiles whose strips belong to it
    foot: dict = field(default_factory=dict)        # "bx,by" (4 x 4 cell blocks) -> feet this season (§4.3)


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
    parent: int = None                  # the group this one is sworn to (fealty, c71), or None
    tribute: dict = field(default_factory=dict)     # goods owed the parent each season
    title: str = ""                     # what its people call its head (by their custom)
    peace: dict = field(default_factory=dict)       # {str(group id): until tick}: a peace sworn between the two (c75)
    leave: list = field(default_factory=list)       # who may use its land: "p:id", "g:id", "k:people" (c85)


class World:
    def __init__(self, cfg):
        self.cfg = cfg
        self.w = cfg["width"]
        self.h = cfg["height"]
        self.seed = cfg["seed"]
        self.rng = random.Random(self.seed)
        self.tick = 0
        self.terrain = []
        self.deposits = TileMap(self.w, self.h)     # key -> {"kind", "left", "size"}
        self.herds = []         # {"id", "kind", "x", "y", "n"}
        self.packs = []         # wolves {"id", "x", "y", "n", "hunger"}
        self.people = {}
        self.buildings = Buildings()
        self.at = TileMap(self.w, self.h)           # key -> building id (one a tile; roads are separate)
        self.roads = TileSet(self.w, self.h)        # keys
        self.trails = TileSet(self.w, self.h)       # keys: ways worn by feet (c69), quicker to walk
        self.foot = {}          # tile index -> footfall, decaying a tenth a day (c69)
        self.piles = {}         # key -> inv
        self.signs = {}         # key -> [[author, text, tick, written]]
        self.places = []        # [x, y, name, by, tick]
        self.fish = {}          # "cx,cy" (a stretch of water, 8 by 8 tiles) -> fish left in it (M2, c64)
        # the grand world (Phase 2): regions of the land, the peoples, and each region's year
        self.regions = []       # {"id", "kind", "x", "y", "size", "name", "people"}
        self.region_of = None   # flat by tile: the region's id, -1 for none (None in the old lands)
        self.peoples = {}       # people -> {"name", "region", "word"}
        self.years = {}         # region id (str) -> "good" | "lean" | "hard"
        self.prices = {}        # place -> {item: [grain a unit, tick]}: the last price paid there (c70)
        self.groups = {}
        self.offers = {}        # id -> an offer (deal, child, pledge, invite, teach)
        self.promises = []
        self.services = []
        self.tenancies = []     # fields worked for a share of the harvest (c83)
        self.envoys = []        # words carried far by one's people, and the answers carried back (c84)
        self.tolls = {}         # "x,y" -> a toll at a ford or bridge (c85)
        self.held = None        # tile index -> the realm holding it, reckoned each dawn, not saved (c85)
        self.bands = {}         # id -> a band under a leader (raids, Phase 5, c72)
        self.holding = {}       # captor id -> ids of those they hold, rebuilt each hour (not saved; c76)
        self.rites = {}         # people -> today's rite: {"x", "y", "day", "came": [ids]} (c79)
        self.news = {}          # id -> a piece of news: {"t", "text", "x", "y", "kind", "who"} (c73)
        self.votes = {}
        self.writings = {}      # id -> {"text", "by", "tick", "kind"}: what is written on tablets and parchment
        self.lost = {}          # craft -> tick the last who knew it died
        self.firsts = {}        # craft -> [tick, person id]: who first practised it here
        self.next_id = 1
        self.eid = 0
        self.names = set()
        self.grid = {}          # (cx, cy) -> set of person ids (not saved)
        # towns (towns_spec §3): settlements laid out in metres; in worlds without towns these stay empty
        self.sites = {}         # id -> Settlement
        self.site_at = TileMap(self.w, self.h)      # key -> settlement id on that land tile
        self.fieldmap = {}      # key -> {"site": id, "strips": [[X, Y, w, h, building id or 0], ...]}
        self.at_many = {}       # tile index -> [building ids] on settlement and field tiles (rebuilt on load)

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
        if not (0 <= x < self.w and 0 <= y < self.h):
            return 0
        i = y * self.w + x
        bid = self.at.flat[i]
        b = self.buildings.get(bid) if bid else None
        if b and b.done and "bridge" in BUILDINGS[b.kind]["roles"]:
            return 1
        c = TCOST[self.terrain[y][x]]
        if not c:
            return 0
        if b and b.done and "wall" in BUILDINGS[b.kind]["roles"]:
            return 0
        if self.roads.flat[i]:
            return 0.5
        if self.trails.flat[i]:
            return c * 0.75
        return c

    def tile_keys(self):
        """key(x, y) of every tile, flat by tile."""
        keys = self.__dict__.get("_keys")
        if keys is None or len(keys) != self.w * self.h:
            keys = self._keys = [key(i % self.w, i // self.w) for i in range(self.w * self.h)]
        return keys

    def step_costs(self):
        """cost() of every tile, flat by tile, kept until the land, a wall or bridge, a road or a trail changes."""
        tc, roads, trails = self.terrain_costs(), self.roads, self.trails
        stamp = (LAND[0], roads.v, trails.v)
        sc = self.__dict__.get("_sc")
        if sc is None or self._sc_stamp != stamp or self._sc_of[0] is not tc or self._sc_of[1] is not roads \
                or self._sc_of[2] is not trails:
            W = self.w
            sc = list(tc)
            at, buildings, rf, trf = self.at.flat, self.buildings, roads.flat, trails.flat
            for i, c in enumerate(tc):
                bid = at[i]
                b = buildings.get(bid) if bid else None
                roles = BUILDINGS[b.kind]["roles"] if b and b.done else ()
                if "bridge" in roles:
                    sc[i] = 1
                elif not c:
                    continue
                elif "wall" in roles:
                    sc[i] = 0
                elif rf[i]:
                    sc[i] = 0.5
                elif trf[i]:
                    sc[i] = c * 0.75
            assert len(sc) == W * self.h
            self._sc, self._sc_stamp, self._sc_of = sc, stamp, (tc, roads, trails)
        return sc

    def passable(self, x, y):
        return self.cost(x, y) > 0

    def building_at(self, x, y):
        """The one building on a land tile. A settlement or field tile holds many: there it is None, and callers
        ask buildings_at (all) or name the one they mean (towns_spec §5.4)."""
        if self.at_many and (y * self.w + x) in self.at_many:
            return None
        if 0 <= x < self.w and 0 <= y < self.h:
            bid = self.at.flat[y * self.w + x]
            return self.buildings.get(bid) if bid else None
        bid = self.at.get(key(x, y))
        return self.buildings.get(bid) if bid else None

    def terrain_costs(self):
        """The hours to step onto each tile by its land alone, flat by tile (buildings and roads aside)."""
        stamp = tuple(map(id, self.terrain))
        if self.__dict__.get("_tc_stamp") != stamp:
            self._tc = [TCOST[c] for row in self.terrain for c in row]
            self._tc_stamp = stamp
        return self._tc

    def components(self):
        """Each tile's part of the land one can walk within (8 ways round, as the way-finding walks), -1 where one
        cannot stand; kept until the land or a wall or bridge changes."""
        stamp = (LAND[0], tuple(map(id, self.terrain)))
        if self.__dict__.get("_comp_stamp") == stamp:
            return self._comp
        W, H = self.w, self.h
        comp = [-1] * (W * H)
        ok = [self.cost(i % W, i // W) > 0 for i in range(W * H)]
        n = 0
        for s in range(W * H):
            if not ok[s] or comp[s] >= 0:
                continue
            comp[s] = n
            todo = [s]
            while todo:
                i = todo.pop()
                x, y = i % W, i // W
                for ny in (y - 1, y, y + 1):
                    if 0 <= ny < H:
                        for nx in (x - 1, x, x + 1):
                            if 0 <= nx < W:
                                j = ny * W + nx
                                if ok[j] and comp[j] < 0:
                                    comp[j] = n
                                    todo.append(j)
            n += 1
        self._comp, self._comp_stamp = comp, stamp
        return comp

    def reachable(self, sx, sy, tx, ty, adjacent=False):
        """Whether walking (not swimming) can lead from (sx, sy) to (tx, ty), or next to it."""
        W, H = self.w, self.h
        comp = self.components()
        starts = {comp[y * W + x] for y in range(sy - 1, sy + 2) for x in range(sx - 1, sx + 2)
                  if 0 <= x < W and 0 <= y < H and comp[y * W + x] >= 0}
        if not adjacent:
            return 0 <= tx < W and 0 <= ty < H and comp[ty * W + tx] in starts
        return any(0 <= x < W and 0 <= y < H and comp[y * W + x] in starts
                   for y in range(ty - 1, ty + 2) for x in range(tx - 1, tx + 2))

    def owned(self, pid):
        """The buildings a person (or, by -id, a group) owns, in the order of self.buildings; kept until a building
        is added, removed or changes hands."""
        stamp = (OWNERSHIP[0], self.buildings.version, id(self.buildings))
        if self.__dict__.get("_owned_stamp") != stamp:
            idx, over = {}, []
            for b in self.buildings.values():
                idx.setdefault(b.owner, []).append(b)
                if BUILDINGS[b.kind].get("overlay"):
                    over.append(b)
            self._owned, self._overlays, self._owned_stamp = idx, over, stamp
        return self._owned.get(pid, ())

    def buildings_within(self, x, y, r):
        """Buildings within r steps of (x, y), in the order of self.buildings (the earliest built first)."""
        W, at = self.w, self.at.flat
        ids = set()
        for yy in range(max(0, y - r), min(self.h, y + r + 1)):
            base = yy * W
            for xx in range(max(0, x - r), min(W, x + r + 1)):
                if at[base + xx]:
                    ids.add(at[base + xx])
        ids.update(b.id for b in self.overlays() if abs(b.x - x) <= r and abs(b.y - y) <= r)
        return [self.buildings[i] for i in sorted(ids) if i in self.buildings]

    def overlays(self):
        """Buildings that share their tile (roads, aqueducts): not in self.at."""
        self.owned(None)
        return self._overlays

    def region_rows(self):
        """The region map, saved as rows of characters (chr(48 + id); "." for none)."""
        if self.region_of is None:
            return None
        W = self.w
        return ["".join("." if r < 0 else chr(48 + r) for r in self.region_of[y * W:(y + 1) * W]) for y in range(self.h)]

    def region_at(self, x, y):
        """The region a tile lies in (a dict), or None."""
        if self.region_of is None or not (0 <= x < self.w and 0 <= y < self.h):
            return None
        r = self.region_of[y * self.w + x]
        return self.regions[r] if 0 <= r < len(self.regions) else None

    def year_at(self, x, y):
        """The year where a tile lies: good, lean or hard ("" in the old lands)."""
        r = self.region_at(x, y)
        return self.years.get(str(r["id"]), "") if r else ""

    def deposit_at(self, x, y):
        """The deposit on a tile, or None (as deposits.get(key(x, y)))."""
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.deposits.flat[y * self.w + x]
        return self.deposits.get(key(x, y))

    def beside(self, x, y, r=1):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                if self.inb(x + dx, y + dy):
                    yield x + dx, y + dy

    # ---- people ----
    def living(self):
        """The living, in the order they came into the world. The list of those alive when someone last came into
        it is kept: a long land's dead outnumber its living many times over, and this is asked many times an hour."""
        ppl = self.people
        if self.__dict__.get("_alive_of") is not ppl or self._alive_n != len(ppl):
            self._alive, self._alive_of, self._alive_n = [p for p in ppl.values() if p.alive], ppl, len(ppl)
        alive = [p for p in self._alive if p.alive]
        if len(alive) < len(self._alive) // 2:
            self._alive = alive
        return alive

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
                    if p.alive and abs(x - p.x) <= r and abs(y - p.y) <= r:
                        out.append(p)
        return out

    def by_name(self, name):
        """The first living person of that name (in the order they came into the world)."""
        n = str(name or "").strip().lower()
        stamp = (len(self.people), next(reversed(self.people.values())).name if self.people else "")
        if self.__dict__.get("_names_n") != stamp:          # rebuilt when someone is born (and named)
            idx = {}
            for p in self.people.values():
                idx.setdefault(p.name.lower(), []).append(p)
            self._names, self._names_n = idx, stamp
        for p in self._names.get(n, ()):
            if p.alive:
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
        return self.tenant_of(b) == p.id

    def tenancy(self, b):
        """The tenancy a field is worked under, if any (c83)."""
        ts = self.tenancies
        if self.__dict__.get("_ten_of") is not ts or self._ten_n != len(ts):
            idx = {}
            for t in ts:
                idx.setdefault(t["field"], []).append(t)
            self._ten, self._ten_of, self._ten_n = idx, ts, len(ts)
        for t in self._ten.get(b.id, ()):
            if not t["done"]:
                return t
        return None

    def tenant_of(self, b):
        t = self.tenancy(b) if self.tenancies else None
        return t["tenant"] if t else None

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

    # ---- towns (towns_spec §2-§5; all of it only in a towns world) ----
    @property
    def towns(self):
        """A towns world: positions in metres, settlements laid out (cfg format "towns1"). Without it, as ever."""
        return self.cfg.get("format") == "towns1"

    def tile_of(self, X, Y):
        """The land tile a point in metres lies on."""
        return int(X // TILE_M), int(Y // TILE_M)

    def pos_of(self, thing):
        """Where a person or building is, in metres: its pos, else its tile's middle."""
        if getattr(thing, "pos", None):
            return thing.pos
        return [(thing.x + 0.5) * TILE_M, (thing.y + 0.5) * TILE_M]

    def cdist(self, a, b):
        """Metres between two people or buildings (straight line)."""
        pa, pb = self.pos_of(a), self.pos_of(b)
        return ((pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2) ** 0.5

    def site_of(self, x, y):
        """The settlement on a land tile, or None."""
        sid = self.site_at.get(key(x, y))
        return self.sites.get(sid) if sid is not None else None

    def many(self, x, y):
        """Does this land tile hold many buildings (a settlement's or a field layout's)?"""
        return key(x, y) in self.site_at or key(x, y) in self.fieldmap or (y * self.w + x) in self.at_many

    def place_building(self, b):
        """Add a building where it stands: with a pos, its tile is derived from it; on a settlement or field tile
        it joins the many there, elsewhere it is the tile's one (as ever)."""
        if b.pos is not None:
            b.x, b.y = self.tile_of(*b.pos)
        self.buildings[b.id] = b
        if BUILDINGS.get(b.kind, {}).get("overlay"):
            return b
        k, i = key(b.x, b.y), b.y * self.w + b.x
        one = self.at.get(k)
        if self.many(b.x, b.y) or (self.towns and one is not None and one in self.buildings and one != b.id):
            ids = self.at_many.setdefault(i, [])
            if one is not None and one != b.id and one not in ids:      # the tile's one becomes one of many
                ids.append(one)
                del self.at[k]
            ids.append(b.id)
        else:
            self.at[k] = b.id
        return b

    def remove_building(self, bid):
        b = self.buildings.pop(bid, None)
        if b is None:
            return None
        ids = self.at_many.get(b.y * self.w + b.x)
        if ids and bid in ids:
            ids.remove(bid)
            if not ids:
                del self.at_many[b.y * self.w + b.x]
        elif self.at.get(key(b.x, b.y)) == bid:
            del self.at[key(b.x, b.y)]
        return b

    def buildings_at(self, x, y):
        """Every building standing on a land tile (overlays aside)."""
        out = [self.buildings[i] for i in self.at_many.get(y * self.w + x, ()) if i in self.buildings]
        one = self.at.get(key(x, y))
        if one is not None and one in self.buildings and one not in self.at_many.get(y * self.w + x, ()):
            out.append(self.buildings[one])
        return out

    def all_at(self, x, y):
        """The buildings on a land tile as a list: the many of a settlement or field tile, else the one (or none)."""
        if self.at_many and (y * self.w + x) in self.at_many:
            return self.buildings_at(x, y)
        b = self.building_at(x, y)
        return [b] if b else []

    def pick(self, p, x, y, test=None):
        """The building on a land tile that is meant (towns_spec §5.5): where a tile holds one, that one (whatever the
        test: callers test it as ever); where it holds many, of those passing the test one's own, then one's partner's,
        then one may use, then the nearest."""
        if not (self.at_many and (y * self.w + x) in self.at_many):
            return self.building_at(x, y)
        cands = [b for b in self.buildings_at(x, y) if test is None or test(b)]
        if not cands:
            return None
        return min(cands, key=lambda b: (b.owner != p.id, b.owner != p.partner or p.partner is None, not self.may_use(p, b),
                                         self.cdist(p, b), b.id))

    def occupied(self, x, y):
        """Is anything built on the tile (one building, or a settlement or field layout)?"""
        return self.building_at(x, y) is not None or (self.towns and self.many(x, y))

    def rebuild_many(self):
        """The many-buildings index of settlement and field tiles, from where the buildings stand."""
        self.at_many = {}
        count = {}
        if self.towns:
            for b in self.buildings.values():
                if not BUILDINGS.get(b.kind, {}).get("overlay"):
                    count[b.y * self.w + b.x] = count.get(b.y * self.w + b.x, 0) + 1
        for b in self.buildings.values():
            i = b.y * self.w + b.x
            if not BUILDINGS.get(b.kind, {}).get("overlay") and (count.get(i, 0) > 1 or key(b.x, b.y) in self.site_at
                                                                    or key(b.x, b.y) in self.fieldmap):
                self.at_many.setdefault(i, []).append(b.id)
                if self.at.get(key(b.x, b.y)) == b.id:
                    del self.at[key(b.x, b.y)]

    def close(self, p, r_cells, r_tiles=1):
        """Those near enough to be together with p (towns_spec §5.3): within r_tiles by land distance, except that
        on p's own tile, when it is a settlement's, only those within r_cells cells (4 m) of p count."""
        out = []
        settled = self.towns and self.site_of(p.x, p.y) is not None
        for q in self.near(p.x, p.y, r_tiles):
            if q.id == p.id:
                continue
            if settled and q.x == p.x and q.y == p.y and self.cdist(p, q) > r_cells * CELL_M:
                continue
            out.append(q)
        return out

    # ---- saving ----
    def to_dict(self):
        st = self.rng.getstate()
        return {"cfg": self.cfg, "tick": self.tick, "rng": [st[0], list(st[1]), st[2]], "terrain": self.terrain,
                "deposits": self.deposits, "herds": self.herds, "packs": self.packs,
                "people": {str(k): slim(asdict(v)) for k, v in self.people.items()},
                "buildings": {str(k): slim(asdict(v)) for k, v in self.buildings.items()},
                "roads": sorted(self.roads), "trails": sorted(self.trails), "foot": {str(k): round(v, 1) for k, v in self.foot.items()},
                "piles": self.piles, "signs": self.signs, "places": self.places, "fish": self.fish,
                "regions": self.regions, "region_rows": self.region_rows(), "peoples": self.peoples, "years": self.years,
                "prices": self.prices,
                "groups": {str(k): asdict(v) for k, v in self.groups.items()},
                "offers": {str(k): v for k, v in self.offers.items()}, "promises": self.promises,
                "services": self.services, "tenancies": self.tenancies, "envoys": self.envoys, "tolls": self.tolls, "bands": {str(k): v for k, v in self.bands.items()}, "news": self.news, "rites": self.rites, "votes": {str(k): v for k, v in self.votes.items()},
                "writings": {str(k): v for k, v in self.writings.items()}, "lost": self.lost, "firsts": self.firsts,
                "next_id": self.next_id, "eid": self.eid, "names": sorted(self.names),
                **({"sites": {str(k): asdict(v) for k, v in self.sites.items()}, "site_at": dict(self.site_at),
                    "fieldmap": self.fieldmap} if self.sites or self.fieldmap else {})}

    @classmethod
    def from_dict(cls, d):
        w = cls(d["cfg"])
        r = d["rng"]
        w.rng.setstate((r[0], tuple(r[1]), r[2]))
        w.tick = d["tick"]
        w.terrain = d["terrain"]
        w.deposits = TileMap(w.w, w.h, d["deposits"])
        w.herds = d["herds"]
        w.packs = d["packs"]
        w.people = {int(k): Person(**v) for k, v in d["people"].items()}
        w.buildings = Buildings({int(k): Building(**v) for k, v in d["buildings"].items()})
        w.at = TileMap(w.w, w.h, {key(b.x, b.y): b.id for b in w.buildings.values() if not BUILDINGS[b.kind].get("overlay")})
        w.roads = TileSet(w.w, w.h, d["roads"])
        w.trails = TileSet(w.w, w.h, d.get("trails", []))
        w.foot = {int(k): v for k, v in d.get("foot", {}).items()}
        w.piles = d["piles"]
        w.signs = d["signs"]
        w.places = d["places"]
        w.fish = d.get("fish", {})
        w.regions = d.get("regions", [])
        rows = d.get("region_rows")
        w.region_of = [(ord(c) - 48 if c != "." else -1) for row in rows for c in row] if rows else None
        w.peoples = d.get("peoples", {})
        w.years = d.get("years", {})
        w.prices = d.get("prices", {})
        w.groups = {int(k): Group(**v) for k, v in d["groups"].items()}
        w.offers = {int(k): v for k, v in d["offers"].items()}
        w.promises = d["promises"]
        w.services = d["services"]
        w.tenancies = d.get("tenancies", [])
        w.envoys = d.get("envoys", [])
        w.tolls = d.get("tolls", {})
        w.bands = {int(k): v for k, v in d.get("bands", {}).items()}
        w.news = d.get("news", {})
        w.rites = d.get("rites", {})
        w.votes = {int(k): v for k, v in d["votes"].items()}
        w.writings = {int(k): v for k, v in d["writings"].items()}
        w.lost = d["lost"]
        w.firsts = d["firsts"]
        w.next_id = d["next_id"]
        w.eid = d["eid"]
        w.names = set(d["names"])
        w.sites = {int(k): Settlement(**v) for k, v in d.get("sites", {}).items()}
        w.site_at = TileMap(w.w, w.h, d.get("site_at", {}))
        w.fieldmap = d.get("fieldmap", {})
        w.rebuild_many()
        w.rebuild_grid()
        return w
