# Towns that look like towns: a plan

Status: **plan, decided by the owner 2026-10-17** (section 9): two scales, re-found world4's people, each people its
own look, world4 keeps running meanwhile. Nothing here is built yet. **The build specification, detailed enough to
build in one pass: [towns_spec.md](towns_spec.md).** It asks for a major change: the
owner's words were "I want towns to form that look like towns rather than a random mishmash of structures that people
just walk on top of ... not a new skin ... major changes". Section 9 lists the decisions the owner needs to make.

## 1. What is wrong today, measured

world4's largest settlement (day 5904, 183 people, 56 homes), drawn tile by tile (h shelter, s store, f field,
p pen, c cairn, k kiln, l loom, * fire, B other; ~ water, . open ground):

```
sssBhcsl*shBsslhhhkschhfffphhhppcl~~~~
BskshsschBBhhhpsh*shlsfffhhphhhphss~~~
shllhlhhhp*hhkHpBph*hphhfphpshhhhhhl~~
ckcllhBhshkc*hslchfshchkphfflf.hfhh*hh
c*hcs*lhch*lpphkshfssflpfhhfflll.fphhf
```

- **1,600 buildings for 183 people**, every tile taken across a box of 45 x 43 tiles: 421 shelters (2.3 for each
  person; old homes are never given up), 266 pens, **245 cairns in the middle of the houses**, 174 fields
  scattered between dwellings, 139 stores, 93 looms, 87 kilns, 70 fires. No street, no square, no edge, no open
  ground.
- **People walk on top of everything.** A building is one tile and every tile but a wall is open to walking.
- **The scale contradicts itself.** A step is an hour's walk (two on a road), so by walking a tile is about a
  kilometre. By building, a tile is one hut. A village of 183 people is spread across 45 km.
- **Nothing is placed for a reason.** A new building goes on the first free tile within 1-3 steps of home
  (`Planner.site`, `Actions.site_ok`): any kind, any direction. Fields go wherever soil is nearest. Graves go where
  the dead lie.
- **People look as if they mill about at random** because they do. Each hour a person is wherever their act put
  them, on any tile, and the viewer walks them across roofs between two hourly points. There is no daily rhythm
  of places: home at night, fields by day, the hearth or the square in the evening.

A new skin cannot fix this: the engine has no streets, no plots, no edge to a settlement, no one house per family,
and no difference between "in the village" and "in the fields". Those have to exist in the engine first.

## 2. The idea in one paragraph

**Two scales, one world.** The land grid stays as it is: a tile is about a kilometre, an hour's walk. It holds
terrain, resources, fields, pastures, woods, territory, travel and war, and nearly every rule we have keeps working on
it. On top of that, **every settlement gets a plan of its own at house scale**: a local grid of cells about 4 m
across, with **streets, plots, a centre, an edge and zones**, laid out by a **town planner in the engine** that grows
the place by rules, the way real villages grew: lanes along the ways people already walk, house plots fronting the
lanes, a green or square where people gather, smoky crafts at the edge or downstream, the burial ground outside,
fields in strips around it. Buildings inside a settlement have **footprints, a facing and a door**. People inside
walk the lanes and go in at doors. **A household has one home, rebuilt in place as it prospers**, and a plot falls
vacant, to ruin and then to someone new when a family dies out. Each people builds its own kind of place: the river
folk's long houses along a waterfront lane, the riders' ring of tents around a horse fold, the hill clans' stone
roundhouses inside a bank. That is the grand plan's own gate ("the owner can tell the peoples apart").

## 3. Why two scales, and the alternatives

| Option | What it means | For | Against |
|---|---|---|---|
| **A. Two scales (recommended)** | land tiles as now; a house-scale plan for each settlement | rules on the land keep working; travel, regions, war, territory stay; the look can be truly real; the cost lands only where people live | the largest change: buildings stop being one per tile; every rule that finds buildings learns about settlements |
| B. One finer grid | tiles 4-10x smaller everywhere, people walk 4-10 tiles an hour | one coordinate system | 16-100x the tiles: speed, memory, prompts full of bigger numbers; the land's rules (seams, herds, regions) all retuned; towns are still one building per tile, so still blocky |
| C. A layout in the viewer only | the engine unchanged; the viewer arranges each tile's buildings into a nicer picture | cheapest | what the owner ruled out: the town would still be a sprawl of 1,600 buildings and people would still mill about; the picture would lie about the record |

A is the only one where the record itself is a town.

## 4. The engine design

### 4.1 Settlements become things

Today a settlement is reckoned each dawn from clusters of homes and forgotten (`settlements_day`, c87). It becomes
a saved object:

- **Founded** when three or more households settle within a land tile of one another, or when a leader founds one
  (a new verb: `found: name`). It sits on **one land tile** (a city may take up to 3x3).
- **Holds:** its name, its people (the majority), its holder (the polity whose land it is), its **plan** (4.2),
  its households and their plots, its commons (green or square, well, shrine, market, burial ground) and its field
  land (4.5).
- **Size by households, not by tiles.** Hamlet (3-11), village (12-60), town (60+, with 40% not farming), city
  (300+). A town of 180 measures about 250 x 250 m, not 45 km.

### 4.2 The plan: a grid of cells inside the settlement

- **Cells** about 4 m across; a plan starts at 48 x 48 cells (about 200 m) and grows by bands as the place grows,
  up to 256 x 256 (about 1 km, the whole land tile) for a city. Stored compactly (one byte a cell for its use, plus
  lists of plots, streets and buildings), so a world of 50 settlements adds well under a megabyte to the save.
- **What a cell is:** street, plot (a household's or the commons'), open ground, water, field edge, wall.
- **Streets** are a graph of lanes with widths (path 1 cell, lane 2, street 3, high street 4). They are laid where
  people walk: the existing footfall that wears trails on the land (c69) is kept inside the plan too, and a way
  walked often enough becomes a lane. The first lanes run from the centre toward water, the fields and the ways to
  other settlements. Lanes follow the lie of the land (slopes, the riverbank) instead of a grid, unless a ruler lays
  out a planned town (a later verb, era 3+).
- **Plots** are rectangles fronting a lane, deep behind it: a cottage plot 5 x 8 cells, a farmstead 8 x 12, a
  lord's 12 x 16. A household asks for a plot when it settles (`settle`), gets the next free frontage on the lane
  nearest its kin, and builds on it. The plot is its property: given, sold, inherited, let, taken in war.
- **The centre** is where the place began: the first hearth, the well or the shrine, and it becomes the green or the
  square. The market, the shrine or temple, the hall and the well stand on it. Where trade is brisk, the square
  widens.
- **The edge** is where plots stop. A palisade or wall, when built, follows the edge, with gates where lanes leave.

### 4.3 Buildings get a footprint, a facing and a door

- Content gains, for each building kind: **size in cells** (shelter 2 x 2, house 3 x 4, longhouse 3 x 8, hall
  6 x 10, store 2 x 2, kiln 2 x 2, pen 3 x 4 fenced, market as a space of stalls), **where it goes** (dwelling;
  yard: store, pen, small workshops; commons: well, shrine, market, hall; edge: kiln, furnace, tannery, lime kiln,
  smithy; outside: burial ground, mill on the water, fields, pasture) and **nuisance** (smoke, stink, noise: kept
  from dwellings or downwind).
- A building on a plot takes the plot's frontage first (the dwelling faces the lane, door on the lane), then the yard
  behind. Footprints block walking; people go in at the door.
- **One home per household**, upgraded in place: a shelter is pulled down and a house raised on its footprint, the
  materials of the old counted toward the new. Building a second dwelling is refused unless it is for a grown child
  setting up (who then takes a plot of their own).
- **Things wear and are given up.** A household that dies out leaves its plot to an heir; with none, the plot stands
  empty, its buildings fall to ruin over a season or two (the c59 weathering, sped up when no one mends), and a
  ruin can be cleared (stone and timber gained) and the plot taken. Today's 421 shelters for 183 people cannot happen.
- **Graves and cairns go to the burial ground**, outside the edge on the way out of town. One cairn a person (c89)
  becomes one grave a person, with a stone for the notable.

### 4.4 Inside and outside: where people are

- On the land a person is still on a land tile. **In a settlement they also have a place in its plan**: at home, in
  their yard, at a building (working), on a lane, at the square, at the well.
- Walking inside a settlement takes minutes, not hours: an act at a building in the same settlement starts the same
  hour. The engine routes along the lanes (a small path search on the plan's graph, kept per plan) and records each
  person's cell at the hour, so the viewer walks them along streets and in at doors, never over roofs.
- **A day has places.** Night at home. Morning out to the fields or the workshop. Midday meals at home or in the
  field. Evening at the hearth, the well, the square or the alehouse. A market day draws the district to the square;
  a festival (c79) fills the shrine's green. Bots follow this rhythm when nothing else presses, and minds may too:
  "go to the square" is a place, not a coordinate. This, more than any model, is what makes the picture read as life
  instead of milling.

### 4.5 Fields, pasture and the land around

- Around a settlement, the land tiles within an hour or two are its **field land**. A field stops being a one-tile
  "building" and becomes **strips in a field** on a land tile: a land tile of rich soil holds, say, 40 strips; each
  household holds strips in two or three fields, near the village first. Sowing, ripening, reaping and tenancy work as
  now on strips. Commons (meadow, pasture, wood) are open to all of the settlement and shared out by custom or law.
- **Pens** in the yard for a few beasts; a herd grazes the pasture by day and is folded at night.
- This keeps farming's balance close to today's: the yield and the work per strip match today's field, and walking
  to the strips takes the hour it takes today.

### 4.6 What the people perceive

- Coordinates stay for the land. **Inside a settlement, places have names**: "your house on Mill Lane", "the
  square", "the well", "Hrodna's smithy at the east gate", "your strips in the east field". The prompt shows one's
  settlement as a short list of named places with minutes to each, not as (x, y). This should make prompts shorter,
  not longer (P1's budget holds: a CI assertion as now).
- New verbs, few and plain: `settle` (take a plot), `found` (a new settlement), and `build` taking "on my plot" or
  "at the square". `go` already takes a kind of place (c91, c92); it takes a place in the plan the same way.
- Nothing in the prompt says simulation, grid or cell (the test that checks this extends to the new text).

### 4.7 Bots

- Bots settle near kin, ask for a plot, build one home and upgrade it, put workshops in the yard or at the edge as the
  plan says, keep the day's rhythm, take strips, and clear ruins. A mechanic no bot uses is untested (process.md §5).

## 5. The viewer

- **Up close, a settlement is drawn from its plan**: lanes as worn earth, then gravel, then cobbles as traffic grows;
  plots with fences, hedges or walls by people; houses facing the lane with doors and yards behind; the green with
  its well; market stalls on market days; smoke from the edge's kilns; the burial ground with its stones; strips of
  crop around the place, each at its stage.
- **Each people builds in its own style** (§6B of grand.md): long houses, round houses, stone houses, tents, timber
  halls; colours and roofs by people (the "peoples' looks" piece, already planned).
- **People walk the lanes** between their recorded cells and go in at doors; at night they are home with a lit
  window.
- **From afar** a settlement is a cluster of roofs at land scale, sized by households; the atlas draws towns as
  towns. The phone budget (viewer.md) holds because only the settlement the camera is in, and its neighbours, are
  drawn at house scale.
- The data format grows (v4): each settlement's plan once a day (cells, lanes, plots, buildings with footprints)
  and each person's place in the plan in the hourly frames.

## 6. Moving the world over

world4 is a land of 1,909 people with 7,434 lives of history, 48 minds and five peoples. Three ways:

| Way | What happens | For | Against |
|---|---|---|---|
| **Re-found (recommended)** | keep every person, kinship, memory, skill, group, oath, feud, debt, renown, region and herd; **lay their settlements out afresh** from each settlement's households, keeping their stores' goods and beasts | the people and their history are what matter, and they carry over; the built land is the part that is wrong | the land "changes" under them once; we tell no one in the world (they simply live in their village) |
| Migrate in place | convert each existing building to a footprint somewhere in a plan | nothing is lost | 1,600 buildings for 183 people do not fit any real plan; we would encode today's mess |
| A new world | a new prehistory from bots, a new launch | cleanest | throws away 148 years and the peoples' grudges, which took weeks of runs to grow |

During the build, world4 keeps running on today's rules (as world2 did during world4's build). The change ships as a
new world founded by `found-world.yml` (world5) from world4's people when the gate (§8) is met.

## 7. Building it, in phases

Each phase ships to main behind a world setting (`cfg.towns`), so bots worlds can run it while the live world does
not, until launch.

| Phase | What | Sessions | Gate |
|---|---|---|---|
| **T1. Settlements and plans** | the saved settlement; the plan grid; the planner (centre, lanes from footfall, plots on frontage, edge); content gains footprints, zones, nuisance; an **ASCII and SVG drawing of a plan** (`tools/townplan.py`) so the owner can judge the look before any 3D work | 3-4 | bots worlds grow settlements whose drawings read as villages: every building fronts a lane or sits in a yard, a centre, an edge, no building on a lane |
| **T2. One home, plots, ruin** | settle, plots as property, one dwelling a household upgraded in place, vacancy, ruin and clearing, the burial ground | 2-3 | buildings per household 1.5-4 (today 9); dwellings per household 1.0-1.2 (today 7.5) |
| **T3. Places and the day** | people's place in the plan, walking the lanes, the day's rhythm, market days at the square | 2-3 | no one on a building cell they are not inside; at night 90% of people at home |
| **T4. Strips and commons** | fields as strips on the land tiles around, pasture and commons, pens in yards | 2-3 | births, starvation and era in bots worlds within the noise of today's (balance.md) |
| **T5. Minds** | named places in the prompt, `settle`, `found`, building "on my plot"; the CI prompt budget | 1-2 | refused steps of minds no worse than c92's; prompt p95 within budget |
| **T6. Viewer** | settlement plans drawn at house scale; peoples' building styles; walking lanes; from-afar clusters; data v4 | 3-5 | the owner, watching, sees towns; phone budget holds |
| **T7. Re-founding** | world4's people into planned settlements (world5), a dev trial week, launch | 1-2 | a week live, no collapse; the owner can tell the peoples apart |
| T8. Later | walls and gates on the edge, a planned town laid out by a ruler, quarters by craft, high streets and inns on the roads between towns, bridges and mills placed by the plan, a city of several land tiles | open | |

About 15-22 sessions to launch. In mode 3 that is days, not weeks; T1's drawings come first and early, so the owner
can redirect before anything expensive.

## 8. Measures

Added to `civ/census.py` and `tools/grandeur.py`, read in bots worlds before each phase ships and in the live world
after:

| Measure | world4 now | aim |
|---|---|---|
| Buildings per household in settlements | about 29 (1,600 / 56) | 2-5 |
| Dwellings per household | 7.5 | 1.0-1.2 |
| Buildings fronting a lane or in a yard behind one | 0% (no lanes) | 95%+ |
| People standing on a building they are not inside, at the hour | most | 0 |
| Settlement footprint for 180 people | 45 x 43 km | about 0.25 x 0.25 km |
| People at home at night | (to measure) | 90%+ |
| Settlements with a centre (green, square) and an edge | 0 | all of 12+ |
| Graves inside the houses | 245 in the largest | 0 |
| Births, starvation, era (bots) | balance.md c92 | within noise |
| Seconds a world hour (speed gate) | tools/speed.py | no worse than +20% |

## 9. Decisions for the owner

**Decided 2026-10-17:** 1 two scales (A); 2 re-found; 3 each people its own look; 4 world4 keeps running on
today's rules, fixed only for real failures. 5 is open (organic growth first either way).

1. **Two scales (A)**, or a finer single grid (B)? Recommended: A.
2. **Re-found world4's people into new settlements**, migrate the buildings in place, or start a new world?
   Recommended: re-found.
3. **The look:** one look for all, or each people its own? Recommended: each its own, from the start of T6.
4. **The live world while this is built:** keep world4 running on today's rules and stop iterating on it except for
   real failures? Recommended: yes.
5. **How towns grow:** organically only (lanes where people walk, recommended for eras 1-2), or also laid out on a
   plan by rulers from era 3 (a grid town, a market town with a high street)?

## 10. Risks

- **Every rule that finds a building** (stores, workshops, theft seen, walls, territory, prompts, bots) assumes one
  building on one tile. T1 introduces the settlement as the place buildings live and keeps `building_at` and
  `building_near` answering in land terms for the land, so most rules do not change; the rest are found by the test
  suite and the bots' refusals, as every change is.
- **Balance**: putting 180 people on one land tile concentrates gathering on the tiles around it. That is real (it is
  why villages farm), but it will move births and hunger. T4 is its own phase with its own gate for that reason.
- **Speed**: the planner runs when someone settles or builds, not every hour; walking inside a plan is a short search
  on a small graph. The speed gate is part of every phase's check.
- **The viewer's budget** on phones: only nearby settlements drawn at house scale.
- **Token cost**: named places should shorten prompts, but a CI assertion holds the budget as now.
