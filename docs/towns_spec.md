# Towns: the build specification

Status: **build spec, 2026-10-17**, for the plan the owner decided in [towns.md](towns.md). **Binding principle: one
continuous world (§2)**: no zones, positions in metres everywhere, the land drawn seamlessly; tiles and cells are
bookkeeping, never seen. (Decided: land rules on 1 km tiles, detail in metres; re-found world4's people, each people its own look, world4 runs on meanwhile). This document is meant to be built from in one
pass: every data structure, rule, algorithm, call site, test and gate is decided here, so that the work can be split
across parallel hands and put together without design questions coming back. Where a choice was hard it says why;
where a number is a guess it says how it will be checked.

Contents: 1 the target · 2 one continuous world · 3 data model · 4 the planner · 5 engine rules · 6 the call-site
audit · 7 bots · 8 the minds' prompt and verbs · 9 the viewer · 10 re-founding world4 as world5 · 11 tools, tests,
measures · 12 the one-shot build: work packages, order, gates · 13 risks and fallbacks · appendices.

---

## 1. The target, as acceptance tests

The build is done when all of these hold. They are written as checks a script can make (`tools/town_check.py`, §11),
plus the owner's eye on the drawings and the viewer.

0. **One continuous world**: one scene from the whole land to a person; no zone, mode or screen change anywhere; no
   tile or cell edge visible on the ground; people walk from house to field to the next village in one unbroken walk.
1. **A settlement is a place**: every dwelling belongs to a settlement; a settlement of 180 people fits in about
   250 x 250 m on one land tile (today 45 x 43 tiles).
2. **Plans read as villages and towns**: every building is inside a plot or on the commons, every plot fronts a lane,
   every lane connects to the centre, no footprints overlap, nothing stands on a lane, the burial ground lies outside
   the edge, edge trades (kilns, furnaces, tanneries) stand at the edge or downwind.
3. **One home a household**: dwellings per household 1.0-1.2; buildings per household 2-5 in settlements (today 7.5
   and 29).
4. **People are where they would be**: no one stands inside a footprint they are not using; at night 90% of people
   are inside their own dwelling; in the evening the green or square has people on it.
5. **Peoples look different**: the river folk's street village of long houses, the hill clans' ring of round houses
   in a bank, the riders' tents round a horse fold, the forest folk's scattered huts in a clearing, the shore folk's
   waterfront row (drawn by `tools/townplan.py`, judged by the owner).
6. **Balance holds**: bot worlds (24 old lands, 4 continents, 3 years) within the noise of c92 for births, starvation,
   era reached and crafts able (balance.md: about 5% of births in 12 seeds).
7. **Speed holds**: seconds a world hour (`tools/speed.py`) no more than 20% over c92's.
8. **The minds cope**: in a dev trial of world5 with minds seated, refused steps no worse than world4's under c92,
   prompt p95 within the station budget (CI holds it).
9. **The viewer shows it**: at house scale, lanes, plots, fences, houses by people, fields in strips, people walking
   lanes and going in at doors; phone budget held (viewer.md).
10. **Nothing in the world is told**: no prompt says simulation, grid, cell, tile (the existing test, extended).

---

## 2. One continuous world: scale and coordinates

**The binding principle (the owner, 2026-10-17): everything is continuous.** There are no zones, no "inside a
settlement" mode, no screen that changes when one clicks a place. One world, one coordinate system, drawn as one
scene from the whole land down to one person at work. A settlement is only where buildings and people happen to be
dense; its lanes run on as paths into the fields and as roads to the next village. Nothing of the land's bookkeeping
(tiles, cells) is ever visible: not as squares on the ground, not as straight edges between forest and meadow, not as
a jump when someone crosses a line.

- **Position in metres, everywhere.** Every person and every building has a position `(X, Y)` in metres on the land
  (floats; x east, y south), not only in settlements. Buildings also have an angle (any, in degrees) and a size in
  metres. Lanes, paths, roads, field strips, walls and rivers are curves (polylines of metre points, drawn smooth).
- **The tile is a bin, not a place.** The land's rules (terrain, what grows and yields, deposits, herds, regions,
  territory, an hour's walk) keep working on tiles of about 1 km: a thing's tile is `(floor(X / 1000), floor(Y /
  1000))`, so `(x, y)` stays available to every rule that uses it today, derived, never set apart from `(X, Y)`. That is
  why the 12,500 lines of land rules do not change: they ask the tile, and the tile is always where the thing is.
- **The cell is an index, not a place.** A grid of 4 m cells, kept only where something is built (an occupancy index
  rebuilt on load, never saved), answers "is this spot free" and "who is close" fast. Footprints at any angle mark the
  cells they cover. Nothing is drawn from it.
- **Moving.** An hour on open ground still carries one about 1 km (a tile's worth), two on a road (`TCOST`,
  `step_along` keep their costs; what changes is that the hour's end is a point in metres along the way, not a tile's
  centre). Within a settlement, short goings (house to well to workshop) take minutes and are done within the hour;
  their route is drawn, not timed (§9.4).
- **Distance.** `dist` (tiles, Chebyshev) stays for land rules; `mdist` (metres, straight line) decides closeness
  (§5.3), sight within a settlement, and the nearest of many buildings.

**Reading the rest of this spec:** where a later section gives a size or a distance in cells (plots, footprints,
Appendix A, `close` radii), read 4 m to a cell; every position is in metres, every footprint an oriented rectangle at
any angle, every lane a smooth curve. `cx, cy` in §3-§10 mean a position in metres.

### 2.1 The land in metres

The tile map stays the engine's record of the land, but the land is drawn and used in metres from it, by one
deterministic function `land_at(X, Y)` (terrain blend, height, water depth, wetness, tree cover), computed from the tile
map and the world's seed, never stored:
- **Rivers and lakes** are curves of a real width (a stream 4-10 m, a river 20-80 m by how many water tiles feed it)
  running through the chain of water tiles, with reed margins and wet meadow beside them. A water tile's rules are
  unchanged (it is crossed by boat, ford or bridge; it is fished); `land_at` says the channel is water and the margins
  marsh, and no building or field is placed in either. Settlements of the shore and river folk stand on the dry land
  nearest the channel, so a waterfront is truly on the water.
- **Terrain types blend** over 50-150 m with noise at their borders: forest thins into scrub then meadow, hills rise
  smoothly; no straight tile edge survives.
- **Trees** stand by tree cover (forest dense, scrub sparse, single trees in meadows), cleared where something is built
  or farmed.
- **Heights** come from the tile heights, smoothed and roughened with noise: gentle rises in the meadows, real slopes in
  the hills.

---

## 3. Data model

All saved as JSON in `state.json.gz` (world format bumps `cfg.format` to `towns1`; a world without it loads as today
and runs as today: `cfg.towns` false).

### 3.1 `Building` gains (all defaulted, so old saves load)

| field | type | meaning |
|---|---|---|
| `pos` | `[X, Y]` metres or `None` | its centre (its tile `x, y` derived from it); `None` only in worlds without towns |
| `angle` | float degrees | which way it faces (its door side), any angle: plots fan along a curving lane |
| `size` | `[w, d]` metres | its footprint (an oriented rectangle; a round house's is its circle's square) |
| `door` | `[X, Y]` or `None` | where one stands to use it / goes in |
| `site` | int or `None` | the settlement it belongs to |
| `plot` | int or `None` | the plot it stands on (`None` for commons, fields, outlying) |
| `ruin` | int or `None` | the hour it fell to ruin (kept as a ruin until cleared) |
| `style` | str | the people whose way it was built in (`river`, `hill`...), for the viewer |

### 3.2 `Person` gains

| field | type | meaning |
|---|---|---|
| `pos` | `[X, Y]` metres | where one is at this hour (`x, y` derived) |
| `inside` | int or `None` | id of the building one is inside (home at night, a workshop at work) |

### 3.3 New: `Settlement` (`w.sites: {id: Settlement}`, and `w.site_at: TileMap` land tile -> id)

| field | type | meaning |
|---|---|---|
| `id`, `name` | int, str | name as today (c87: a named place among its homes), or given by `found` |
| `x`, `y` | int | its land tile (a city may later hold up to 3 x 3; v1 holds one) |
| `people` | str | its people (the founders'; recounted each season as the majority) |
| `form` | str | `street`, `waterfront`, `ring`, `cluster`, `scatter` (from its people, §4.2) |
| `founded` | int | hour |
| `centre` | `[cx, cy]` | where it began (the first hearth, well or shrine) |
| `green` | `[cx, cy, w, h]` | the open centre: green, square, fold or fire-ring |
| `lanes` | list of `{id, pts: [[cx, cy], ...], w: 1-4, kind}` | polylines; `kind`: path, lane, street, high street, ring |
| `plots` | list of `{id, rect, lane, side, kind, holder, since}` | `kind`: cottage, farmstead, lord, craft, commons, burial |
| `edge` | `[[cx, cy], ...]` | polygon round the plots (recomputed when a plot is added) |
| `walled` | bool | an enclosing palisade or wall stands on the edge (v1: recorded; §5.9) |
| `burial` | int | the burial plot's id |
| `fields` | list of `[x, y]` | land tiles whose strips belong to it |

Plots and lanes are small lists; a village of 40 households is about 40 plots and 6-12 lanes: under 5 KB saved. A
world of 60 settlements adds well under 1 MB.

### 3.4 New: field tiles (`w.fieldmap: {key(x, y): {"site": id, "strips": [[cx, cy, w, h, bid or 0], ...]}}`)

A land tile of farmland is laid out once, when its first strip is wanted: **furlongs** of strips 25 x 50 cells
(100 x 200 m, about 2 ha) running across the slope (v1: along the axis away from the settlement), with a headland
path. A tile holds up to 40 strips (less where the settlement or water takes room). A `farm` building is one strip:
its `rect` is the strip; all its crop rules are as now.

### 3.5 Content gains (`civ/content/buildings.py`): size, zone, nuisance

Every kind gets `size=(w, h)` in cells (before facing), `zone`, `nuisance` (0 none, 1 smoke or noise, 2 smoke and
stink), and optionally `shape` (the viewer's default form). The table (Appendix A) gives every one of the 44 kinds.
Zones:

- `dwelling`: on a plot's frontage (shelter, house, brick_house, stone_house; the lord's hall on a lord plot)
- `yard`: behind the dwelling on its plot (store, granary, drying_rack, fire, loom, oven, brewhouse, workshop, pen,
  stables, scribe_house)
- `commons`: on or round the green (shrine, temple, market, hall, school, library, scriptorium, infirmary, well (new,
  §5.10), granary when owned by a group)
- `edge`: on craft plots at the ends of lanes or the downwind side (kiln, furnace, bloomery, smithy, lime_kiln,
  glassworks, tannery)
- `water`: on the water side of the tile, or the tile edge facing water (dock, shipyard, mill)
- `burial`: in the burial plot (grave, cairn)
- `field`: strips on field tiles (farm)
- `land`: outlying, placed freely in the tile (cairn on a height, shrine in the wild, tower, palisade and wall
  outside settlements, road and aqueduct as overlays, bridge spanning a water tile)

### 3.6 Peoples gain a town (`civ/content/peoples.py`, each people's `town=dict(...)`)

| people | form | plot (w x d cells) | lane w | bounds | dwelling shapes | notes |
|---|---|---|---|---|---|---|
| river | street | 8 x 14 | 3 | fence | long house 3 x 8 (shelter), 4 x 10 (house) | gable to the lane; fields in long strips |
| shore | waterfront | 7 x 12 | 3 | none | long house 3 x 7, stilts where wet | one-sided row facing the water; docks and racks on the shore |
| hill | cluster | 8 x 8 | 2 | bank round the whole | round house 4 x 4 (shelter), 5 x 5 (house) | central fold; short winding ways; a bank and ditch on the edge |
| riders | ring | 7 x 7 (wedges) | 2 (ring) | none | tent 3 x 3 round (shelter), 4 x 4 (house) | tents ring a horse fold; doors face the fold |
| forest | scatter | 9 x 9 | 1 (paths) | none | conical hut 3 x 3, timber house 4 x 5 | huts among trees round a fire-green; trees left standing between |

Later peoples (and any people without `town`) take `street` with square houses. Stone, brick and later dwellings keep
their people's form and take the size of Appendix A.

---

## 4. The planner (`civ/towns.py`, new; pure functions of the world and a seed)

The planner is called only when something is founded, settled or built, never every hour. All randomness comes from
`Random(hash((w.cfg["seed"], site.id, n)))` so a plan is the same on every machine.

### 4.1 Founding

`found(w, x, y, people, by, name=None) -> Settlement`:
1. The tile must be passable land, hold no settlement, and lie 3+ tiles from any other settlement's tile (two villages
   an hour apart are two villages; nearer than that, one joins the other).
2. `centre`: if a water tile is beside the tile, 30 cells in from that side (the waterfront); else the tile's centre;
   jittered by up to 20 cells.
3. `green` by form: street: 12 x 8 across the lane at the centre; waterfront: 10 x 8 by the water; cluster: a fold
   14 x 14; ring: a fold 18 x 18 (the horse fold); scatter: a fire-ring 10 x 10.
4. **First lanes** (§4.3) and the **burial plot** (§4.5).
5. Event `found` (news: "X was founded by Y").

### 4.2 Forms

Each form is a lane skeleton and a rule for where the next plot goes. All forms share: plots front a lane; a plot is
never placed over another plot, a lane, the green, water, or outside the tile with a margin of 8 cells.

- **street** (river, default): a main lane through the centre along the axis that leads toward the most-walked
  neighbour tile (footfall, §4.3), else toward water; plots on both sides, outward from the green alternating ends;
  when the main lane reaches 90 cells each way, a **back lane** parallel at plot depth + lane width, then cross lanes
  at its ends.
- **waterfront** (shore): a lane parallel to the water edge; plots on the landward side only; when 120 cells long, a
  second lane behind, joined by cross lanes.
- **cluster** (hill): a ring lane of radius r = 14 around the fold; plots on its outer side, each fronting the ring;
  a full ring adds the next at r + plot depth + 2; short spokes join rings. The **bank** follows the outermost ring
  plus 4 cells.
- **ring** (riders): plots as wedges on a ring lane round the horse fold, doors to the fold; a full ring opens the
  next.
- **scatter** (forest): plots at Poisson-disc points 14-22 cells apart within 70 cells of the fire-ring, each joined
  to the nearest plot already joined or to the green by a path (a tree of paths). Trees on the tile stay between plots
  (the viewer keeps them where no footprint or path is).

### 4.3 Lanes from feet

The c69 footfall (`w.foot`, land scale) decides which way the first lanes run: toward the neighbour tiles walked
into most. Inside the plan, people walking between doors (§5.2) wear `site.foot[(cx // 4, cy // 4)]`; once a block
of 4 x 4 cells outside any plot is walked 200 times in a season it becomes a **path**, and a path walked 1,000 times
a lane. New lanes are only ever laid on open ground. This is how the forms bend to the life lived in them.

### 4.4 Plots

`plot_for(w, site, household, kind) -> plot`: the next free frontage by the form's rule, nearest the household's kin
(parents', siblings' plots) first, then nearest the green. Plot size by kind: cottage (the people's plot), farmstead
(1.5 x depth, for a household with 8+ beasts), lord (2 x 1.5, for the head of a group of 8+), craft (the people's plot
at the edge). The plot's holder is the household's head (the owner of its dwelling, as `Building.owner` today).
Plots change hands as buildings do (inheritance, `give`, sale in deals, taking in war: §5.6).

### 4.5 Placing a building

`place(w, p, kind, near=None) -> (x, y, rect, door, facing, site, plot)` or a reason why not:
- `dwelling`: on one's plot's frontage, door on the lane. With no plot: `plot_for` in the settlement on one's tile,
  or within 1 tile; with none within 2 tiles, **found** a homestead (a settlement of one household, form of one's
  people) on one's tile.
- `yard`: on one's own plot behind the dwelling, packed from the back; a full plot spills to the edge of a craft plot
  of one's own; refused if none ("your yard is full: a craft plot at the edge").
- `commons`: on the green's rim, door to the green; when the rim is full, along the main lane next to the green.
- `edge`: a craft plot of one's own at the far end of a lane on the downwind side (east: v1 wind is from the west), or
  across water from the dwellings; a tannery beside water if any.
- `water`: on the cells along the water side.
- `burial`: the next cell row in the burial plot (graves 1 x 2 in rows, a cairn 2 x 2 at the row's end).
- `field`: a free strip on a field tile of one's settlement (§4.6).
- `land`: free cells in the tile (any 8 x 8 free square), as today's free placement.

A footprint is rotated to its facing. Packing is first-fit in the plot's own grid; the test is "no overlap with
footprints, lanes, the green, water cells".

### 4.6 Fields

`strip_for(w, p, site)`: the tile chosen is, in order: the tile one stands on if it is field land of one's settlement
with a free strip on the right soil; the settlement's field tiles nearest it with one free; a new field tile: the
nearest tile within 2 of the settlement on rich soil or grass (the c-farm `on`) with no settlement on it. A settlement's
own tile gives strips too, outside its edge (an infield). The tile's furlongs are laid out on first use (§3.4).

### 4.7 Growing, shrinking, and the edge

- `edge` is recomputed as the convex hull of all plots plus 2 cells, smoothed (for the bank, the palisade line and
  the viewer's outline).
- An empty plot (no living holder, no heir: §5.6) keeps its buildings as they weather to ruin; once its dwelling is a
  ruin and a season has passed, the plot is **vacant** and is offered first by `plot_for`; its ruins are cleared by the
  newcomer (`clear`, §5.7).

---

## 5. Engine rules

### 5.1 One home a household

- A household is a dwelling's owner, their partner, their children not yet settled, and anyone whose `home` it is.
- Building a dwelling when one's household has one is an **upgrade**: allowed only to a kind with more warmth or beds;
  it is placed on the old one's footprint (grown on the plot if bigger); the old one stands while the new is built and
  is taken down when it is finished, giving back a quarter of its cost to the household's store.
- A second dwelling is refused ("your household has its home; to raise a better one, build it and it takes the old
  one's place") unless the builder is a grown child (16+) whose home is their parents' and who is partnered or 20+:
  they take a plot of their own.
- **Today's 421 shelters for 183 people cannot happen**: checked by `town_check` (dwellings per household).

### 5.2 Where people are in a tile

`Engine.place_in(p, b=None, inside=False, spot=None)` sets `p.cell` (and `p.inside`):
- at a building: its door (outside), or a cell inside its footprint when `inside` (sleeping, resting, working at a
  workshop that is inside: loom, oven, scribe_house, school, library, infirmary, hall, temple);
- entering a tile from a neighbour: the cell on the shared side nearest the lane that leaves that way (or the side's
  middle);
- gathering, hunting, herding, fishing on a tile: a cell of open ground, field strip or the water side fitting the act
  (deterministic from the person and the hour);
- idle in a settlement: the green in the evening (§7), else one's yard.

Called by: `World.place` for every land move (the entry cell), `Engine.run_person` after each act's hour, and the acts
that use a building (`start_*` that resolve a building). One rule more: **no cell inside someone else's footprint
unless one is inside it with leave** (`may_use`) or it is a ruin.

Within an hour, a person's walk from their last cell to this one along lanes is not simulated; the viewer draws it
(§9.4). The planner's lane footfall (§4.3) is counted from the pair (last door, this door) by the shortest lane route,
computed only every 6th hour per person (cheap enough; an estimate is all it needs).

### 5.3 Close, near, and who notices

`World.near(x, y, r)` stays the land-scale query. New `World.close(p, r_cells, r_tiles=1)`: the people within
`r_tiles` by land distance, **except** that those on p's own tile, when that tile is a settlement's, count only within
`r_cells` cells of p's cell. Every site that is about **two people being together** uses `close`; every site about the
land (herds, crowds at a resource, armies) keeps `near`. Appendix B classifies all 49 sites. The headline ones:
sickness passing (1 tile -> 3 cells, and housemates), learning by watching (1 tile -> 4 cells, same workshop), theft
and blows seen (4 tiles -> 30 cells by day, 10 by night, nobody through walls), speech heard (4 tiles -> 25 cells,
night 8), company against wolves (1 tile -> the settlement counts as company), talk and asking for food (3-6 tiles ->
30 cells). Without this, a town of 180 on one tile would catch every sickness and learn every craft from every attempt.

### 5.4 Finding buildings

- `World.at` keeps "the one building on a land tile" **only for tiles without a settlement or field layout**
  (outlying buildings). Settlement and field tiles hold many: new `World.at_many: {tile index: [ids]}`.
- `World.building_at(x, y)` keeps its meaning where a tile has one building; on a settlement or field tile it returns
  `None` (no single answer) and callers that need one use `buildings_at(x, y)` (all) or `target_building` (§5.5).
  Appendix C lists all 35 `building_at` sites and what each becomes.
- `World.buildings_within(x, y, r)` and `Actions.building_near(p, test, r)` include the many-tiles' buildings and,
  when ties in land distance arise (all of a village is at distance 0), break them by cell distance from p's cell.
- `World.cost(x, y)` (passability) is unchanged for land tiles: a settlement tile is passable; walls on the edge are
  §5.9.

### 5.5 Naming a building

`Actions.target_building(p, a, test)` resolves, in order: `a["bid"]` (bots always pass it); a name in `a["at"]` or
`a["place"]` ("my store", "Hrodna's kiln", "the market", "the well", "the burial ground", a lane name: §8.2); the
x, y of an outlying building; on a settlement or field tile named by x, y: the matching building there that is one's
own, then one's partner's, then one may use, then the nearest by cells. The prompt names buildings so that a mind
need not give coordinates for anything in its own settlement.

### 5.6 Holding and passing on

Plots pass with the dwelling (the c-inheritance that passes buildings today: partner, then by the people's custom).
A household that dies out leaves the plot `holder = 0`; its buildings weather twice as fast (c59: unmended), fall to
ruin (`ruin = tick`, kept in place, no roles work), and the plot is vacant a season after its dwelling falls. Taking a
settlement in war (c75-c76 submission, plunder) does not move plots; a ruler may `grant` a vacant plot (§8.3).

### 5.7 Clearing

New act `clear` (x, y or "at"): at a ruin or one's own building, 4 hours, gives a quarter of its cost to one's store
(or the ground) and frees its cells. Bots clear ruins on a plot they take. The ruins of others' plots are left to
their holder or the vacant rule.

### 5.8 The dead

A grave or cairn goes to the burial plot of the settlement of the dead's home (or the nearest within 3 tiles); a
death far from any settlement leaves a grave where they lie, as now. The burial plot grows in rows as it fills; one
cairn a person (c89) stays the rule.

### 5.9 Walls and gates (v1)

A palisade or stone wall built **by a settlement's member on its tile** goes on the edge as segments (a wall's 4-cell
length a build), with gates where lanes cross the edge (a gatehouse where one is built). When the edge is closed
(80% walled), the settlement is `walled`: in war (c72 raids, c75 sieges' later work), a walled settlement counts as the
wall did (raiders must breach); for movement, its tile stays passable to members and those with leave, and costs
strangers 3 hours to enter (the gate, asked). Walls outside settlements are as now (a whole tile).

### 5.10 The well (new kind)

`well`: era 0, cost stone 4, hours 4, size 2 x 2, zone commons, roles `{"gathering": {}}`. It is where people meet by
day, as the green is in the evening (§7). No new rule rides on water.

### 5.11 What does not change

Gathering, hunting, fishing, crafts, recipes, skills, offers and deals, promises and writing, groups, fealty, tribute,
territory and tolls (land scale), war (land scale; a settlement's walls as §5.9), news, rites (at the shrine on the
green), herds and wolves (land), prices and markets (a market's reach is its settlement, not 2 tiles), speech's tongues.

---

## 6. The call-site audit (what changes where)

Counted on main at c92 (`grep`): `building_at` 35, `building_near` 33, `buildings_within` 12, `w.near` 49,
`owned(` 33, `site_ok` 10, `w.at` direct 15, bot plan steps carrying `b.x, b.y` 76. The rule for each family:

| family | rule |
|---|---|
| `w.at` direct (15) | world.py, acts.py, engine.py, realm.py: go through `World.place_building(b)` / `World.remove_building(b)` which keep `at`, `at_many`, `site_at`, `fieldmap` right. No other code writes them. |
| `building_at` (35) | Appendix C, one line each: most become `buildings_at` with a test or `target_building`; those on tiles that can hold only one (water, outlying) stay; prompt.py's become the settlement block (§8). |
| `building_near` (33) | unchanged calls; the function breaks ties by cells. |
| `buildings_within` (12) | unchanged calls; the function includes `at_many`. |
| `w.near` (49) | Appendix B, one line each: those about two people being together become `close`; those about the land stay. |
| `owned` (33) | unchanged. |
| `site_ok` (10) | becomes `towns.place(...)`'s reason when `cfg.towns`; unchanged otherwise. |
| bot steps with `b.x, b.y` (76) | add `"bid": b.id` to each (one helper, `Bot.at(b)`, returns `{"x", "y", "bid"}`). |
| `Planner.site` | `towns.place` when `cfg.towns`. |
| `settlements_day` (c87) | reads `w.sites` (and keeps the c87 census for worlds without towns). |
| `census.clusters` | unchanged for old worlds; `w.sites` for towns. |

Every change is behind `w.cfg.get("towns")`, so the 400+ existing tests run unchanged on worlds without towns, and the
same suite runs again with towns on (§11.3).

---

## 7. Bots

- **Settling**: a bot without a home builds a dwelling; `place` puts it on a plot in the settlement on its tile, in its
  kin's settlement if within 3 tiles (it walks there first), else founds a homestead. Grown children settle at 20 or
  when partnered, near their parents.
- **Upgrading**: `home_goal` raises a better dwelling when it can (the upgrade rule), never a second.
- **Yards and edges**: workshops by the zone rules; a bot at its craft goes to its own or a usable workshop as now.
- **Fields**: `farm_goal` asks `strip_for`; reaping and sowing as now (c92's rules). Herds fold in the yard pen or the
  people's fold.
- **The day** (new `rhythm` step, after hunger and danger, before goals): night (hours 9-11): home and inside; dawn
  (0): out to the day's work; evening (8): if nothing presses and one is in one's settlement, an hour at the green or
  the well, talking (`talk.converse` there). Rites gather at the shrine (c79 as now). A market day every 5th day: the
  settlement's traders and those with posts stand at the market by day.
- **Clearing**: a bot that takes a vacant plot clears its ruins first.
- **The dead's place**: kin raising a cairn put it in the burial plot.

---

## 8. The minds: prompt and verbs

### 8.1 The settlement block (replaces coordinates of one's own buildings)

```
You live in Greenford, a village of 34 households (river folk), on the river side of (46,60). Your house fronts
Mill Lane; behind it your store (grain 22), your pen (4 sheep) and your loom. The green with the well and the shrine
is a short walk. In Greenford: Hrodna's smithy at the east end; Aelis's market stall on the green (posts: pot 1 for
grain 2); the burial ground by the north way. Your strips: 2 in the east field (47,60), ripe; 1 in the south field
(46,61), sown 3 days ago.
```

- Own buildings by name and what they hold; others' only when they matter (workshops one needs, posted trades, the
  commons, kin's homes).
- Coordinates only for land tiles (fields, places outside).
- Budget: the block replaces "What is yours" lines that today carry one coordinate each; a household with 9 buildings
  had 9 lines and now has 2-3. CI's p95 assertion stays the gate.

### 8.2 Names inside a settlement

Lanes are named when laid (from the people's tongue plus a word for what they lead to: Mill Lane, Shore Way, the
High Street; `civ/names.py`); the green, the well, the burial ground and the commons are named by kind; a building by
its owner and kind ("Hrodna's smithy"). `go`, `take`, `put`, `craft at`, `mend`, `trade` accept `at: <name>`
(target_building, §5.5). Bare `go: market` already works (c91, c92) and now resolves inside the plan.

### 8.3 New verbs (help text one line each)

- `settle`: take a plot in the settlement here (or join your kin's); builds nothing.
- `found: name`: found a new settlement here (3+ tiles from any other).
- `clear: at`: pull down a ruin or a building of yours (a quarter of its makings back).
- `grant` gains `plot` (a ruler gives a vacant plot to a person).

Shown only when they apply (the c90 rule: a verb shown to those who can use it).

### 8.4 What the people never hear

The forbidden words test (`tests/` checks prompts for simulation, agent, game, turn, tick) gains grid, cell, tile,
plan, footprint, coordinate.

---

## 9. The viewer

### 9.1 Data (format 4; v3 readers say plainly it is newer)

- `manifest.json` adds the scale (`tile_m: 1000`), the seed and parameters of `land_at`, and, per people, its town look
  (form, colours, roof).
- Daily snapshot adds `sites`: `[id, name, x, y, people, form, centre, green, lanes, plots, edge, walled]`; each
  building adds `[pos, angle, size, door, site, plot, ruin, style]` at the end of its list (append-only); `fields`: the
  furlongs of each field tile.
- Hourly frames add `X, Y, inside` to each person (append-only).
- Budgets: a village's plan about 3 KB; a day's sites under 200 KB for 60 settlements; chunks stay under 1 MB gzipped.

### 9.2 One scene, level of detail by distance

- **No zones, no mode switch.** One scene for the whole land; the camera moves and zooms smoothly from the whole
  continent to a person's hands. What is drawn, and how finely, depends only on distance from the camera, faded in and
  out (no popping), never on which settlement one is "in".
- One scene unit = one metre. The land (176 km) is streamed in chunks of 250 m: terrain from `land_at` (same function,
  ported to JS and tested against Python's on a grid of sample points), at finer mesh near the camera and coarser far.
- **Near** (within about 600 m): everything: buildings at full detail, fences, lanes, crops, reeds, animals, people
  walking and working, smoke.
- **Middle** (to about 5 km): buildings as simplified meshes merged per chunk, fields as textured strips, trees as
  impostors, people as moving dots or not at all.
- **Far**: terrain, rivers, forests as texture, settlements as clusters of roofs sized by households (the atlas look
  emerges from the same scene seen from high up).
- The 2D map (§9.5) stays as a light fallback for weak devices, drawn from the same data.

### 9.3 Art (`viewer/art/`)

- `town.js` (new): lanes as ribbons following their polylines (earth, gravel, cobbles by footfall), the green (grass
  with a worn ring), plot bounds by the people's `bounds` (fence, hedge, wall, bank, none), the burial ground's stones
  in rows, the edge's palisade or bank.
- `buildings.js` gains footprint-sized builders by shape: long house (river, shore), round house (hill), tent (riders),
  conical hut (forest), square (default); later kinds (brick, stone) keep the people's shape in their material. Doors
  on the facing side, a lit window at night when someone is inside.
- `fields.js` (new): strips with crop stages, furrows along the strip, headland paths.

### 9.4 People walk continuously

- Each hour's frame gives each person's position in metres. Between two, a person walks the shortest route along
  lanes, paths, roads and open ground (A* on the settlement's lane graph plus doors near home, on a coarse walk-cost
  field of `land_at` out in the land; `core/paths.js`, pure, testable in Node), going in at doors and coming out of
  them, never through a footprint, a river (fords and bridges only) or a field's crop when a headland path is there.
- Crossing from the village into the fields and on to the next village is one walk; there is no edge anywhere.

### 9.5 The 2D map

`map2d.js` draws a settlement's plan when zoomed in (lanes, plots, footprints by zone colour), else a dot by size: the
same drawing `tools/townplan.py` makes, so what the owner judges in T1 is what the 2D map shows.

---

## 10. Re-founding world4 as world5 (`tools/refound.py`)

Input: world4's state. Output: world5's state with `cfg.towns` true. Deterministic; prints a report.

1. **Households**: each living person's home's owner household (owner, partner, their children without a home of
   their own, others whose `home` it is). Adults without a home join their parents' or partner's household; else form
   one alone.
2. **Settlements**: c87 clusters of homes. Each cluster of 3+ households becomes a settlement on the passable land
   tile nearest its homes' centre (rich soil or grass preferred, not water, 3+ tiles from another settlement's tile);
   a cluster over 90 households splits along its largest gap into two settlements 3+ tiles apart. Clusters under 3
   households join the nearest settlement within 4 tiles of their homes, else become homesteads on their homes' tile.
   Names: the cluster's c87 name; unnamed ones from the people's tongue.
3. **People**: each to their household's settlement tile (cell: home's door); those more than 4 tiles from home (on
   the road, at war, herding far) keep their land position and walk home.
4. **What each household keeps, laid out by the planner**: its best dwelling (most warmth, then beds); one store per
   200 of goods it holds across its stores (at most 3), goods moved into them by kind (food first), the rest to a
   granary on the commons for its people's head, or lost; one workshop per craft a member is able at that the
   household owned a workshop for; pens for its beasts (8 a pen; riders' beasts to the fold); strips: as many as it
   owned farms, at most 2 a working adult, crops carried over with their stage.
5. **The commons**: each settlement keeps one of each commons kind found among its homes' cluster (market, shrine,
   temple, hall, school, library, scriptorium, infirmary), owners kept; and gains a well.
6. **The dead**: graves and cairns of the last 300 dead whose homes were in the cluster go to the burial plot, names
   and carved words kept; older monuments with words are kept as outlying cairns on the nearest height.
7. **Outlying**: roads, bridges, mills (moved to the water side of the nearest settlement's tile), docks, towers,
   walls and shrines outside any cluster are kept where they are; everything else is removed.
8. **Recomputed**: territory (c85: from homes and fields), tolls (kept if their ford or bridge stands), tenancies (kept
   if their strip exists), posts (kept on their stores), `p.known` entries naming removed buildings dropped, `w.foot`
   kept, `w.trails` kept.
9. **Minds**: the same 48 seats (`seat_minds`), their memories kept. Their next prompt shows their settlement block;
   nothing tells them the land changed (they simply live in their village).
10. **Report**: households, settlements by size and people, buildings kept and removed by kind, goods lost, the
    `town_check` result. It must pass before `found-world.yml` publishes world5.

---

## 11. Tools, tests, measures

### 11.1 Tools

- `tools/townplan.py`: draws a settlement as text (one character per 2 x 2 cells) and as SVG (lanes, plots, footprints
  by zone, people as dots), from a world dir or a bots world after N years. The owner's first look (T1 gate).
- `tools/town_check.py`: the invariants (1-4 of §1) on any world: overlaps, plots fronting lanes, lanes connected,
  footprints off lanes, burial outside the edge, nuisance placement, dwellings per household, people in foreign
  footprints, night at home. Exit 1 on failure; CI runs it on a 1-year bots world.
- `tools/civ_balance.py --towns`: the same runs with `cfg.towns`; prints the town measures (§11.4).
- `tools/refound.py` (§10), with `--check` to run town_check on its output.

### 11.2 Unit tests (`tests/test_towns_*.py`)

Planner: founding spacing; each form's first 30 plots readable (snapshot of the text drawing per form, seeded);
plots never overlap; every plot fronts a lane; lanes connect; growth adds back lanes and rings; vacancy offered first.
Placement: each zone goes where it should; a yard full refuses; upgrade replaces in place and refunds; a second
dwelling refused; a grown child settles. Fields: furlong layout; strip capacity; crops on strips as on farms.
People: cells after moves and acts; no foreign footprints; inside at night. Close: sickness and watching limited to
cells in a town, unchanged outside. Names: target_building by bid, by name, by x, y on a busy tile. Prompt: the
settlement block; verbs shown when they apply; forbidden words. Re-found: a small world4-like save re-founded passes
town_check; people, kin, skills, goods totals within the rules of §10. Viewer: `core/paths.js` routes along lanes
never through footprints (Node tests as the store's).

### 11.3 The suite twice

`tests/` runs as now; a second CI job sets `BOTCIV_TOWNS=1`, which makes `generate` and `found_realm` turn `cfg.towns`
on, and runs the suite again (tests that depend on one-building-per-tile mark themselves `@skip_if_towns` with a
reason; the count is reported).

### 11.4 Measures (census, grandeur)

Buildings and dwellings per household; footprint area of each settlement; share of plots fronting lanes; people inside
foreign footprints; at home at night; at the green in the evening; settlement sizes ranked; ruins and vacant plots;
strips per household; and the old measures (births, deaths by cause, era, crafts, trades).

---

## 12. The one-shot build

### 12.1 Order and parallel work

Six work packages. **WP0 goes first and alone**: it freezes the interfaces every other package builds against. Then
WP1-WP5 can go in parallel (separate worktrees, separate files), each with its own tests against WP0's interfaces and
a fake planner where it needs one. Integration is one package at a time onto WP0, tests and `town_check` after each.

| WP | What | Files (new or changed) | Depends | Size |
|---|---|---|---|---|
| **WP0 interfaces** | data model (§3) with defaults and save/load; `World.place_building / remove_building / buildings_at / at_many / site_at / close / cdist`; `Engine.place_in` stub (centre cell); `cfg.towns` flag; content sizes, zones, nuisance, the well, peoples' `town`; `towns.py` signatures returning a trivial plan (everything on the tile's centre row) | world.py, content/buildings.py, content/peoples.py, towns.py (stubs), tests/test_towns_model.py | none | 1 session |
| **WP1 planner** | §4 in full: founding, the five forms, lanes from feet, plots, placement by zone, fields and furlongs, edge, vacancy; `tools/townplan.py` | towns.py, names.py, tools/townplan.py, tests/test_towns_planner.py | WP0 | 2-3 |
| **WP2 engine** | §5: one home, place_in and cells, close (Appendix B), building lookups (Appendix C), target_building, holding and ruin, clear, the dead, walls v1, prices' reach; `town_check` | acts.py, engine.py, society.py, territory.py, war.py, news.py, belief.py, plan.py, census.py, tools/town_check.py, tests | WP0 (WP1 for real plans; a fake meanwhile) | 3 |
| **WP3 bots** | §7: settle, upgrade, zones, strips, rhythm, clearing, `Bot.at(b)` bids in the 76 steps | minds/bot.py, minds/talk.py, tests | WP0, WP2's verbs | 1-2 |
| **WP4 minds** | §8: settlement block, names, new verbs, help text, budget, forbidden words | prompt.py, acts.py (verbs), names.py, tests | WP0, WP2 | 1-2 |
| **WP5 viewer** | §9: format 4 in `run.land/frame` and `site.py`; store, paths, town, buildings by shape, fields, LOD, 2D map; gallery page of the five forms | run.py, site.py, viewer/**, docs/viewer.md | WP0 (format), WP1 (real plans to look at) | 3-5 |
| **WP6 re-found** | §10, `tools/refound.py`, a found-world.yml path for world5 | tools/refound.py, found_world.py, .github/workflows/found-world.yml | WP1-WP4 | 1-2 |

Then **integration and balance** (1-2 sessions): bots worlds with towns on against c92 (24 old lands, 4 continents, 3
years), `town_check` on every one, speed gate; fix what moved; owner looks at `townplan` drawings and the gallery.
Then **the dev trial**: world5 re-founded from world4's newest state, minds seated, a week of dev pieces (`[world]`
on a claude branch), then launch: one line in `configs/live_world`.

About 13-19 sessions of work; with WP1-WP5 in parallel, about 6-9 sessions of elapsed time.

### 12.1a Built (where the code is)

- **WP0, 2026-10-17:** `civ/world.py` (Building and Person gain the §3 fields, left out of saves at their defaults;
  `Settlement`; `w.sites`, `w.site_at`, `w.fieldmap`, `w.at_many` rebuilt on load; `World.towns`, `tile_of`, `pos_of`,
  `cdist`, `site_of`, `many`, `place_building`, `remove_building`, `buildings_at`, `rebuild_many`, `close`;
  `building_at` gives None on a tile of many), `civ/content/towns.py` (Appendix A sizes, zones and nuisance; the
  peoples' towns of §3.6; the well), `civ/towns.py` (`found`, `plot_for`, `place`, `strip_for` with a trivial plan),
  `Engine.place_in`, `civ/land_at.py` (landAt, the same numbers as the viewer's), tests `test_towns_model.py`,
  `test_land_at.py`. Gate 1 passed: suite untouched, round trip, `tools/speed.py --days 8` hash unchanged
  (events 317e75050276, state cb4412f7c7ec).
  Three choices differ from the text above: the flag is `cfg["format"] == "towns1"` read as `World.towns` (cfg's
  `towns` key was already the c87 list of towns seen); the peoples' town table lives in `content/towns.py`, not in
  `peoples.py`; the well joins the building kinds in WP2, when the engine can keep it to towns worlds.

### 12.2 Gates (each must pass before the next step)

1. WP0: the existing suite passes untouched; save/load round-trips the new fields; worlds without towns hash the same
   as c92 in `tools/speed.py` (no behaviour change).
2. WP1: `townplan` drawings of each form at 5, 20 and 60 households, seeded; **the owner looks at them** (the one
   point where the owner's eye decides before more is built).
3. WP2+WP3: a bots world with towns runs 3 years with no exceptions, `town_check` clean, the twice-run suite passes.
4. Balance: §1.6 and §1.7.
5. WP4: prompt p95 within budget; a session trial (as round 73's): 16+ answers from seated minds in a world5 draft,
   refused steps no worse than c92.
6. WP5: the viewer on a phone-sized render (Playwright screenshot), the five forms visible; Node tests pass.
7. WP6: re-found report clean; `town_check` passes on world5.
8. The dev week: no collapse, refused steps and starvation within world4's; the owner watching can tell the peoples
   apart.

### 12.3 Rollback

Every step is behind `cfg.towns`; world4 runs on as it is, on main's code, untouched (its `cfg` has no `towns`). world5
lives on its own branch; going back is the one line in `configs/live_world`.

---

## 13. Risks and fallbacks

| risk | sign | fallback |
|---|---|---|
| Births or starvation move past the noise because 180 people now gather from one tile's surroundings | balance gate | gathering's `find` already ranges over sight; if hunger rises, strips' yield or the infield ring are the knobs, not the plan |
| Speed: `close` and `place_in` on every move | speed gate | `close` indexes people by tile and cell block (8 x 8 cells), rebuilt per hour; `place_in` is O(1) |
| Saves grow | state size | plans are vectors; `at_many` is rebuilt on load, not saved |
| The minds lose their way without coordinates | refused steps | coordinates stay accepted for land; names are extra, never required |
| A form looks wrong | T1 drawings | the forms are data; their numbers change without code |
| The viewer at 250x the scale is heavy on phones | gate 6 | middle and far LOD; house scale only in the camera's 3 x 3 tiles |
| Something deep assumes one building a tile and is missed by the audit | an exception in bots runs or tests | the twice-run suite and three-year bots runs flush these out; each is a one-line fix to `buildings_at` |
| world4's history does not lay out (e.g. a cluster of 300 homes) | refound report | split rule (§10.2), and homesteads for the scattered |

Open (towns.md §9.5, not needed for v1): rulers laying out planned towns (a grid, a market town's high street) from
era 3. The forms are data, so a `planned` form can be added later without touching the rest.

---

## Appendix A. Building sizes, zones and nuisance (cells: 4 m)

| kind | size | zone | nuisance | | kind | size | zone | nuisance |
|---|---|---|---|---|---|---|---|---|
| fire | 2x2 | yard (or green) | 1 | | brick_house | 5x7 | dwelling | 0 |
| shelter | by people (3x3-3x8) | dwelling | 0 | | stone_wall | 1x4 segment | edge / land | 0 |
| store | 2x3 | yard | 0 | | gatehouse | 3x3 | edge | 0 |
| drying_rack | 1x2 | yard | 0 | | temple | 8x12 | commons | 0 |
| grave | 1x2 | burial | 0 | | market | 10x10 (open) | commons | 1 |
| cairn | 2x2 | burial (or land) | 0 | | scribe_house | 4x5 | commons | 0 |
| farm | 25x50 strip | field | 0 | | bloomery | 3x4 | edge | 2 |
| pen | 4x4 | yard | 1 | | smithy | 4x5 | edge | 1 |
| house | by people (4x4-4x10) | dwelling | 0 | | lime_kiln | 3x3 | edge | 2 |
| granary | 3x4 | yard / commons | 0 | | glassworks | 4x5 | edge | 2 |
| kiln | 2x3 | edge | 2 | | mill | 4x5 | water | 1 |
| loom | 2x3 | yard (inside) | 0 | | road | lane overlay | land | 0 |
| oven | 2x2 | yard | 1 | | bridge | spans its water tile | land | 0 |
| tannery | 3x4 | edge (by water) | 2 | | stone_house | 6x8 | dwelling | 0 |
| brewhouse | 3x4 | yard | 1 | | tower | 3x3 | edge / land | 0 |
| workshop | 4x5 | yard | 1 | | stables | 5x8 | yard | 1 |
| palisade | 1x4 segment | edge / land | 0 | | school | 6x8 | commons | 0 |
| shrine | 3x3 | commons | 0 | | library | 6x8 | commons | 0 |
| dock | 3x6 | water | 0 | | scriptorium | 5x6 | commons | 0 |
| furnace | 3x3 | edge | 2 | | infirmary | 6x8 | commons | 0 |
| hall | 10x14 | commons / lord plot | 0 | | observatory | 4x4 | land | 0 |
| well (new) | 2x2 | commons | 0 | | shipyard | 8x14 | water | 1 |
| | | | | | aqueduct | overlay | land | 0 |

## Appendix B. `w.near` sites (49): `close` or keep

`close(p, cells)` in a settlement tile; land radius as today elsewhere.

| site | what | verdict |
|---|---|---|
| engine.py:96 `see` | who sees a place | close 40 by day, 10 at night (inside: no) |
| engine.py:463 | tongues heard | close 25 |
| engine.py:571, 576 | sickness: mending in company, passing on | close 3 (and housemates) |
| engine.py:869 | a new seam noticed | keep (land) |
| engine.py:941-947 | herds and packs placed away from people | keep |
| engine.py:963-964 | wolves: company | close 30; anyone in a settlement tile counts as in company |
| engine.py:1127 `attempt` | learning by watching | close 4 (same workshop) |
| engine.py:1215 | who one has seen lately | close 60 |
| engine.py:1229 | word of the land at dawn | close 30 |
| society.py:73 | speech heard | close 25 by day, 8 at night |
| society.py:710 | prices seen | keep (the market's people; in towns its settlement) |
| acts.py:770 | hunters at a herd | keep |
| acts.py:1753 | taking from a store seen | close 30 by day; none at night or inside |
| acts.py:1798 | give to whoever is beside | close 3 |
| acts.py:2147 | learners at a school | close (inside the school) |
| acts.py:2215 | onlookers judge a blow | close 30 |
| territory.py:129, 235 | eyes on trespass | keep (land) |
| belief.py:70 | who comes to a rite | keep (land; the rite is at the shrine) |
| news.py:39 | news heard where it happens | close 40 in a settlement, land 5 elsewhere |
| news.py:80 | news passed on | close 30 |
| war.py:343 | watch over captives | close 10 |
| war.py:430, 467 | defenders rally | keep (land) |
| prompt.py:272, 800 | who one sees, listed | close 40, then by cells; the list's cap stays |
| talk.py:166 | someone to talk to | close 25 |
| bot.py:257 | foes attacking | close 6 |
| bot.py:303 | someone fed to ask | close 6 |
| bot.py:324, 337, 340 | crowds at a resource, hunters, fishers | keep |
| bot.py:355 | watchers of a store | close 30 |
| bot.py:443 | a grown-up to keep close to | keep (land), then cells |
| bot.py:612 | tenancy candidates | keep |
| bot.py:742 | hiring candidates | keep |
| bot.py:840 | who one sees (pledges) | keep |
| bot.py:899 | callings nearby | keep (land 15: a district's trades) |
| bot.py:987, 1005, 1022 | teaching, feeding kin, social | close 20 |
| bot.py:1256, 1337 | followers near, orders | keep |
| bot.py:1371 | learners at a school | close (inside) |

## Appendix C. `building_at` sites (35)

| site | becomes |
|---|---|
| world.py:508 (def) | as §5.4 |
| acts.py:178 `yield_here` | the strip or deposit at the person's cell (fields: `buildings_at` filtered to strips with the item) |
| acts.py:378 `stores_beside` | `buildings_at` on own and neighbour tiles, own and usable |
| acts.py:582, 589, 617 | "adjacent" walking: a tile with any building -> walk to the tile (doors are §5.2) |
| acts.py:640, 659, 681 | the strip being reaped: `a["bid"]` |
| acts.py:1114-1115 `site_ok` | `towns.place` reason |
| acts.py:1165 | help finish a building of the same kind: `buildings_at` unfinished of the kind |
| acts.py:1183 | the tile named for a build: `towns.place` with `near` |
| acts.py:1472 | the field named to sow: `target_building` |
| acts.py:1531, 1535, 1537 `target_building` | as §5.5 |
| acts.py:1669 | piles not under a building: piles keep land scale (a pile is on the tile) |
| acts.py:1686 | a named building to take from: `target_building` |
| society.py:163, 788 | a named store or post: `target_building` |
| territory.py:188 | a toll's ford or bridge: keep (one a water tile) |
| engine.py:108 | up a tower: `p.inside` |
| engine.py:522 | sheltered: `p.inside` (shelter role) |
| engine.py:584 | a building at a place seen: `buildings_at` |
| engine.py:857 | free tiles for seams: tiles with no building and no settlement |
| engine.py:890, 939 | herds and packs keep off built tiles: also off settlement tiles |
| engine.py:965 | inside against wolves: `p.inside` |
| prompt.py:265, 287, 399, 816 | the settlement block and the land view (§8.1) |
| realm.py:160 | founding a realm's homes: `towns.found` + `place` when `cfg.towns` |
| bot.py:1242 | the leader's field: `bid` |
