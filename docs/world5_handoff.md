# world5: handoff (read this first in a new session)

Written 2026-10-17 at the end of a long session, so that a new session can take this work up cold. It holds: what the
owner asked for and decided (with their words), where everything stands, which documents to read in what order, and
the full specification of **step 0, the next thing to do** (§5).

## 1. Read in this order

1. `CLAUDE.md` and `docs/process.md` (as every session).
2. **This file.**
3. [world5.md](world5.md): the frame: a large, continuous, living world; size, wilderness, trade routes, daily life,
   professions, nobility, emergence; the order of steps 0-7 and their gates.
4. [towns_spec.md](towns_spec.md): the detailed build spec: one continuous world in metres (§2, binding), data model,
   settlement planner, engine rules, the call-site audit (Appendices B and C), bots, prompts, viewer, re-founding,
   tests, work packages WP0-WP6 and gates.
5. [towns.md](towns.md): the first plan and its reasoning (why two scales; options rejected; the owner's decisions in
   §9).
6. `docs/towns_pics/`: **`target_river_gemini.jpg`, the look the owner wants**; the to-scale plan sketches of the five
   peoples' forms and world4 today (`0_today` ... `5_forest`, `.png` and `.svg`, made by `tools/townsketch.py`);
   `gemini_prompts.md` (the prompts that made the target picture and others the owner may make).
7. `docs/viewer.md` (the viewer as it is: architecture, art direction, budgets, Pixel 9 as the reference phone).

## 2. What the owner asked for, in their words, and what was decided

All on 2026-10-17, in order:

1. *"We should think about a major change. I want towns to form that look like towns rather than a random mishmash of
   structures that people just walk on top of. Right now it just looks like people milling around doing random
   things. I want it to look much more real. The grid system we have seems to be working as an underlying engine, but
   I want things to be much more real. I'm not just talking about playing a new skin ... major changes. Stop
   iterating, and plan carefully."*
2. Decisions (answers to towns.md §9): **two scales** (land tiles stay for rules; detail below them); **re-found**
   world4's people into the new world (keep people, kin, memories, skills, history; lay their places out afresh);
   **each people its own look** from the start; **world4 keeps running** on today's rules meanwhile, fixed only for
   real failures. Open: whether rulers may lay out planned towns from era 3 (organic growth first either way).
3. *"Let's do some more careful planning so we can try to one shot a massive expansion and update."* -> towns_spec.md.
4. The owner had Gemini paint the river folk's village from `gemini_prompts.md` and said: *"I want it to look this
   good. Should we abandon the grid system?"* Answer given and accepted: no full rewrite; the land rules stay on tiles;
   the look comes from the layout (engine) and the art (viewer); free angles and curves inside settlements.
5. *"I want everything to be continuous. Not that you click on a settlement and the world changes to be inside the
   settlement like a separate zone."* -> **binding principle** (towns_spec §2): one world in metres, no zones, no mode
   switch, the land drawn seamlessly, level of detail by distance only; tiles and cells are bookkeeping, never seen.
6. *"I want the world to be much bigger as well. Right now it's really crowded. I want a real sense of settlements with
   wilderness separating them, trade routes forming, everyone having their daily lives, people specializing
   professions, nobility arising, and lots of emergent behaviors occurring, not just limited to this. I agree with
   keeping the tiles as bookkeeping. It should not look like a tile world; it should look beautiful like the Gemini
   screenshot."* -> world5.md (world4's land at twice the scale: 352 x 352 tiles, about 124,000 km²).
7. *"Yes, do number one"* (step 0, the look proven in the real viewer), then: *"There's a lot of context in this chat.
   I want to do this in a new session, so make sure that this plan and everything is very carefully logged with a full
   spec document of everything."* -> this file.

## 3. Where things stand (2026-10-17)

- **The live world:** world4 (`configs/live_world`), advanced hourly by `world2.yml` (Kaggle GPU, else the free
  Gemini/Groq tiers). Rules **c92** merged to main on 2026-10-17 (PR #188); the first piece under c92 had not yet run
  when this was written: confirm with `python tools/health.py` (it should say `Rules c92`).
- **c92** (shipped): a harvest reaps only the field it names, not the neighbours' beside it (world4: 6,112 crops taken
  in 94 days); `go` to a kind of place named as `to`; mending makes or gathers its rope or stone first; the hungry are
  told where their own food is; bots slaughter from their herd when the pen has no milk, feed hungry kin early, reap a
  ripe field of their own first; a bot not able at a craft buys from a maker's post before making it; ropers; a calling
  crowded nearby is chosen less; world4's history.jsonl records again. Numbers: docs/balance.md "c92", process.md
  "Round 74".
- **c93 set aside** (not on main): "a want that finds no seller is heard nearby, and makers able at its craft make it
  and post it". A probe showed purchases 62 -> 112 in 1.5 bot years; never measured on the standard runs. The patch is
  `docs/patches/c93_wants_heard.patch` (`git apply` it to revive). world5.md §6 keeps the idea.
- **Mode:** 3 (continuous, driven by the owner's session; `docs/process.md` §0). No scheduled tasks for botciv exist
  (the "botciv mode 2" one was deleted). The owner said **stop iterating** on world4: fix only real failures; all
  effort to world5.
- **Nothing of world5 is built.** Docs, sketches and `tools/townsketch.py` only.

## 4. The whole plan in one screen

| Step | What | Spec | Sessions |
|---|---|---|---|
| **0** | **The look, proven in the real viewer** (§5 below) | this file §5 | 2-3 |
| 1 | Foundations: positions in metres, `land_at`, data model, `cfg.towns` | towns_spec §2-§3, WP0 | 1-2 |
| 2 | Settlements and the engine: planner, engine rules, bots, minds | towns_spec §4-§8, WP1-WP4 | 7-10 (3-4 if parallel) |
| 3 | A large land: world4's land upsampled 2x, `land_at` rivers, blends, heights | world5 §2, towns_spec §2.1 | 1-2 |
| 4 | Life between settlements: journeys, camps, inns, outlaws, specialists buying food, apprenticeship, strips as property, forfeit, feasts, houses | world5 §3-§7 | 4-6 |
| 5 | The viewer: one streamed scene, LOD by distance, five peoples' looks, continuous walking | towns_spec §9, WP5 | 4-6 |
| 6 | Re-found world4 onto the large land; 30-50 years bots-only settling-in | towns_spec §10, WP6; world5 §9 | 2 + runner time |
| 7 | Launch: minds seated, a dev week, `configs/live_world` -> world5 | grand.md Phase 8 | 1 |

Gates: world5.md §10 and towns_spec §12.2. Rollback: everything behind `cfg.towns`; world4 untouched.

## 5. Step 0: the look, proven (the next work)

### 5.1 Purpose

Before 20+ sessions of engine work, find out **how close the real viewer (three.js in a browser, on a Pixel 9) can come
to `docs/towns_pics/target_river_gemini.jpg`**, and **prove the continuous world**: one scene from kilometres up down
to one person, no zones, no tile edges. The owner judges the result and says go or changes course. Nothing in the
engine changes in step 0.

### 5.2 What the target shows (the checklist the screenshots are compared against)

From `target_river_gemini.jpg` (high three-quarter view, about 45 degrees down, warm late-afternoon light):
- a broad river across the top with reed and cattail margins and grassy banks; a smaller stream across the lower middle
  with reeds, crossed by a **plank bridge** on posts;
- a curving **packed-earth lane** (warm tan, soft edges) that bends round the green and forks to the bridge;
- about 9 **long houses** in **fenced plots fanning along the curve**: deep golden thatch with visible layered texture
  and a ridge, **crossed gable finials**, timber framing, plastered lower walls, a dark door in the gable end facing the
  lane; plots divided by **wattle fences** (woven, posts) with gates on the lane;
- behind most houses a small **store on stilts** (timber, thatch, a ladder); **sheep** in several yards;
- the **green**: an oval of short grass, a round **stone well**, a small timber **shrine** with a lantern, people
  standing and talking, children;
- three **beehive clay kilns** at the east edge, each with a thin wisp of **smoke**;
- a fenced **burial ground** at the west with rows of rounded **grave stones**;
- **field strips** in the foreground: ripe golden **wheat** (dense, swaying stalks), green **flax** with small blue
  flowers, brown **ploughed fallow** with furrows; **people reaping** with sickles, carrying sheaves and baskets;
- scattered **conifers and broadleaf trees** at the corners; soft shadows; chunky rounded shapes; a gentle dark outline.

### 5.3 The scene (one stretch of land, about 6 x 3 km)

- **The river village** of the target (laid out as the target and `1_river.png`: 8-14 households along a curving lane,
  green with well and shrine, kilns east, burial ground west, strips south; the stream and bridge between village and
  fields), placed on the inside of a bend of a wide river.
- **The land around it**, continuous: meadow, a **forest edge** 1-2 km off thinning into scrub (no straight edge), a
  gentle hill, the river running on across the scene with reed margins.
- **A track** (worn path) from the village 4-5 km across meadow and through the forest edge to a **second hamlet** of
  3-4 houses (forest folk's conical huts in a clearing, `5_forest.png`), so the fly-down and the walk show distance and
  wilderness between places.
- **People:** 20-40 chibi figures (the existing `art/figure.js`) at the target's tasks: reaping, carrying sheaves,
  talking on the green, a child with sheep, a woman spinning by a door, one walking the track.

### 5.4 Data: written in metres, as world5 will hold it

`civ/viewer/demo/river_village.json`, hand-authored or generated by extending `tools/townsketch.py` (preferred: it then
doubles as the planner's first fixture), in towns_spec §3's shapes, metres, y south:
- `land`: `{size: [6000, 3000], seed, heights: coarse grid of 250 m points, river: [[X, Y, width], ...],
  stream: [...], forest: polygon(s) with density, hill: ...}`;
- `lanes`: `[{pts: [[X, Y], ...], w: 3 | 6 | 12 (metres), kind}]` (the village lane, the fork to the bridge, the track);
- `plots`: `[{pos, angle, w, d, fence: "wattle"}]`; `buildings`: `[{kind, pos, angle, size, style}]` (long house,
  store on stilts, well, shrine, kiln, conical hut, grave stones, bridge);
- `fields`: `[{pts (quad), crop: wheat | flax | fallow, stage}]`;
- `people`: `[{id, pos, verb, holds, path?}]`; `animals`: sheep `[pos]`.

### 5.5 Code: a demo page beside the viewer, sharing its art kit

- `civ/viewer/demo.html` (static, not linked from the viewer, like `gallery.html`; uses the vendored three.js r186 and
  the importmap as gallery.html does) and `civ/viewer/demo/*.js`. No build step, no CDN (viewer.md §2).
- `demo/land.js`: `landAt(X, Y)` prototype: height (bilinear from the coarse grid plus 2-3 octaves of noise), water
  (distance to the river and stream polylines vs their width), wetness (reed margin 5-25 m), tree cover (forest polygon,
  noise-feathered over 50-150 m), terrain colour as a smooth blend (meadow, rich soil, forest floor, mud, sand). This
  becomes the reference for towns_spec §2.1's Python `land_at` (step 1 ports it and tests both on the same points).
- `demo/terrain.js`: chunks of 250 x 250 m, each a grid mesh whose resolution falls with distance (e.g. 2 m near, 8 m
  middle, 32 m far), vertex colours from `landAt`, skirts or matched edges so **no seam shows between chunks or detail
  levels**; the river surface as its own mesh (toon water, gentle ripple, shoreline foam line).
- `demo/town.js`: lanes as smooth ribbons along Catmull-Rom curves (soft alpha edges, worn texture), plots' wattle fences
  instanced along their edges with gates, the green, the burial ground.
- `art/` additions (shared with the viewer, data-driven by kind and style, so step 5 reuses them): **long house** (thatch
  as a thick rounded roof with layered strands in the texture or geometry, ridge, crossed finials, timber frame, door),
  **store on stilts**, **well**, **shrine**, **beehive kiln**, **grave stone**, **plank bridge**, **conical hut**,
  **wattle fence**, **reeds/cattails**, **wheat** (instanced stalks swaying in the shader), **flax**, **furrows**,
  **sheep**, **trees** (broadleaf, conifer, with impostors far off), **smoke** (soft sprites).
- **Look:** the existing toon ramp (`art/toon.js`), warm sun and cool sky fill, one soft shadow map following the
  camera, inverted-hull outlines on buildings and people, distance haze; late-afternoon light as the target; colours
  sampled from the target (thatch, lane, grass, water, fences).
- **Two ways to models, both tried:** (a) code-made, as the kit does now; (b) ready-made **CC0 only** (Kenney,
  Quaternius, Poly Pizza items marked CC0), committed under `civ/viewer/vendor/models/` with their licence notes,
  restyled with the toon materials. Step 0 ends with a recommendation between them (or a mix), written into viewer.md.
- **Level of detail by distance, faded (no popping):** near (under about 600 m) everything; middle (to about 5 km)
  merged simplified buildings, crop as texture, tree impostors, no people; far: terrain and roof clusters.

### 5.6 The camera and the walk (what the owner will see)

- **Fly-down** (`demo.html?tour=1`): from about 4 km up over the whole stretch (both settlements, the river, the
  forest, the track visible), down past 600 m, to the **target view** (about 120 m up, 45 degrees, framed like the
  picture), then down to 15 m over the well; one smooth path of about 40 s with eased speed; no cut, no reload.
- **The walk** (`?walk=1`): the camera follows one person from their door, down the lane, across the green, over the
  bridge, out to the strips, then along the track toward the hamlet, at ground level (3-4 m behind), for 30-60 s.
- Free orbit, pan and zoom by mouse and touch, for the owner to explore.

### 5.7 Deliverables

1. Screenshots (Playwright with `/opt/pw-browsers/chromium`; `tools/demo_shots.js` or `.py`), each at 1600 x 900 and
   at Pixel 9 size (412 x 915 CSS px, device scale 2.625):
   - **A, the target view** framed like `target_river_gemini.jpg`, side by side with it in one image;
   - **B** 600 m up (the village, its fields, the river bend); **C** 4 km up (both settlements and the wilderness
     between); **D** 15 m over the well; **E** the walk, at the bridge; **F** the same as A at night in winter (lit
     doors, snow), if time allows.
2. A short **video** of the fly-down (Playwright's video recording, or frames to an mp4 with the installed ffmpeg).
3. **Numbers:** frames a second and draw calls and triangles at A-D (`?debug=1`), desktop headless and a phone-sized
   render; against viewer.md §9's budget.
4. **A written comparison** (in this file's §7, or `docs/towns_pics/step0.md`): what matches the target, what falls
   short and why, the model recommendation (code-made, CC0, mix), what step 5 must add.
5. All sent to the owner (SendUserFile, the comparison image first).

### 5.8 Acceptance

- The owner looks at A beside the target, the fly-down and the walk, and says go (or what to change).
- No tile or chunk edge visible in any view; no popping visible in the fly-down at normal speed.
- Phone-sized render holds viewer.md's budget at B and D (or the written comparison says what tier it needs).

### 5.9 Not in step 0

No engine change, no new rules, no world data from a real world (the scene is hand-made data), no change to the live
viewer's behaviour (art kit additions are new builders, used by the demo only until step 5).

## 6. Open questions for the owner (none blocks step 0)

- Planned towns laid out by rulers from era 3, beside organic growth (towns.md §9.5).
- How many minds' seats in world5 (48 now; world5.md §2 suggests 48-64 within the free tiers' budget).
- Whether to revive c93 (makers answering wants) for world5 or rebuild it in step 4.

## 7. Step 0's results

Done 2026-10-17; full write-up, pictures and numbers in [towns_pics/step0.md](towns_pics/step0.md). In short:
- `civ/viewer/demo.html` (`?tour=1`, `?walk=1`, `?shot=A..F`, `?debug=1`, `?models=cc0`), data in metres from
  `tools/demo_village.py`, `landAt` in `civ/viewer/demo/land.js` (tested in Node; the reference for step 1's port).
- One seamless land from 4 km up to the ground: a geomorphing quadtree for shape, colour read from maps laid over the
  world by position, so no tile or chunk edge shows at any distance and changes of detail do not pop.
- The village as the target: the form, thatch, finials, wattle, stores on stilts, green, well, shrine, kilns, graves,
  stream and bridge, strips with standing crops, reeds, people at work; a winter night.
- Every view under the phone budget (0.16-0.49 M triangles on the phone tier, 0.24-0.62 M on desktop). Frames a second
  must be read on the Pixel 9 itself (no GPU here).
- Short of the target: true scale makes the houses smaller in the same frame; surfaces plainer than paint; light
  cooler. Recommendation: code-made models, CC0 only for small scatter.
- Merged to main (PR #190). The owner said to keep going without waiting: step 1 (WP0 and `land_at` in Python)
  followed the same day (towns_spec §12.1a).

## 8. Step 2 so far (2026-10-17)

- **WP1** (PR #192): the planner `civ/towns.py` (forms street, waterfront, cluster, ring, scatter, homestead; plots,
  lanes, commons, burial, field strips 40 x 200 m), `tools/townplan.py` drawings in `docs/towns_pics/plan/`.
- **WP2/WP3** (PR #193): `cfg["format"] == "towns1"` founds settlements laid out in metres; the engine places,
  upgrades and removes buildings by plot; one home a household; people positioned each hour; speech, sickness,
  learning, sight and word at dawn reach by metres (`World.together`); bots find their own building among many on a
  tile. `tools/town_check.py` checks a towns world sound (one home a household, no overlaps, none off its tile or in
  water, no doing gone wrong); `tools/speed.py --towns`. Balance, 3 seeds x 600 people x 3 years: towns alive 711 vs
  plain 662, births 174 vs 141, starved 41 vs 54, refusals 1706 vs 2290. Worlds without towns unchanged (speed hash).
- **WP4** (first part, PR #193): settlements and their lanes named in the people's tongue; the prompt tells one's
  settlement by name (home and its lane, what stands behind it, workshops, the green, others' workshops and posts,
  fields); a step may name a building in words ("my store", "Nath's oven", "the well"). `tests/test_towns_prompt.py`.
- **A real settlement in the viewer** (WP5's first piece): `tools/demo_from_world.py` writes a towns world's
  settlement in the demo's format; `civ/viewer/demo.html?data=world_village` draws what the engine built. It showed two
  faults, fixed: a craft plot was a whole home plot deep and every person had their own (a village of 13 households had
  25, most holding one kiln); now they are half as deep and the household's. Field strips are taken nearest the
  settlement first. The evening hour: those with nothing pressing stand about the green.
- **The verbs and the day** (WP3/WP4): `settle` (a plot in the settlement here), `found: name` (a new settlement 3+
  places from any other), `clear: place` (pull down a building of one's own, a quarter of its makings back), each told
  only to whom it applies and refused in worlds without towns (`tests/test_towns_verbs.py`). Bots already went home at
  night; the evening at the green; a market day every 5th day (those with goods posted stand at the market or the
  green). A household under one roof works at its workshops (not its stores or pens), and its craft plots number 2
  and one a grown member (to 8), each at least 24 m deep (half a hill folk's plot held one pen): the household's
  plots had made "craft plots full" and "no kiln free" the bots' top refusals. Balance (3 seeds x 600 x 3 years):
  alive 712/712/720 (before 711/712/711), starved 39/43/29 (41/53/29), refusals 2233/2526/2063 (1540/2067/1512: more
  crafting, so more "needs wood" and "can carry no more"); `town_check` sound over 40 days.
- **The viewer's long houses** had their ridge roll set off by half its length (a 9 m pole out of one gable, in the
  step 0 village too); the well's windlass and the fire's logs likewise. Centred.
- **Step 3, the large land:** `civ/upsample.py` doubles a land (borders through a smooth warp, sea and lakes
  doubled, rivers kept one tile wide, regions, places, deposits, herds and fish to their doubled places);
  `tools/upsample_land.py` checks it on a saved world and draws it (`docs/towns_pics/land/`: world4's land, SOUND);
  `generate({"upsample": 2, ...})` founds a world on a continent made at half size and doubled (600 people: 18
  settlements, nearest neighbour 28 km median against 13.5 km undoubled). Tests `tests/test_upsample.py`. The
  viewer's `land_at` rivers as curves through the water tiles come with WP5 (the viewer reading a whole land).
- **Step 4 begun: the measures.** `tools/world5_measures.py` runs a bots towns world on the large land and reports
  by year what world5.md §4-§7 aim at. Baseline (600 people, 192 x 192 doubled, seed 5, years 1-3): home at night
  0.36-0.43 (aim 0.9), at the green in the evening 0.24-0.26, adults 10+ km from home some hour 305-315 (traders 7-11),
  trades between homes 10+ km apart 37-83 a year of 1,286-2,248, top tenth of makers' share 0.26-0.33 (aim 0.6),
  no settlement of 50+ yet (specialists unmeasured), strip Gini 0.34-0.36, no tenants. What keeps people out at night
  is food: "food for the store" and hunting trips 5-12 km out on the doubled land, not a rule of the night.
  First mechanic: **dusk** (towns worlds): bots out within 4 km of home turn home at dusk (minds choose for
  themselves; never woken for it), and one's home is one's to sleep in (grown children under a parent's roof could
  not). Balance (3 seeds x 600 x 3 years, 96 x 96): alive 725/738/714 (712/712/720), starved 37/55/46 (39/43/29),
  refusals 1444/1841/997 (2233/2526/2063).
- **WP5 begun: a window of the large land in the viewer.** `demo/tiles.js` (`LandTiles`) draws a towns world's land
  from its tiles with no tile edge left (fields through the tiles' centres sampled through a slow warp), rivers as
  curves, sea and lakes as a sheet faded at the shore, every settlement's strips in the land's colour;
  `tools/demo_from_world.py --window 32` writes 32 x 32 km with every settlement in it and tracks between
  neighbours (`demo.html?data=world_land`); the scene sizes itself from the land's box. Node tests in CI. Still to
  do: the whole land streamed (not a window), people walking between settlements, the five peoples' looks, forests
  thick enough to read from high up, ground colour with more life at a distance.
- **Step 2 is done** but for ruins as such (a fallen building is removed and its plot goes vacant, which serves) and
  the session trial of gate 5 (seated minds in a towns draft). Cairns and graves already go to the burial plot. Next:
  step 3 (the large land) and WP5 (the viewer reading format 4).
