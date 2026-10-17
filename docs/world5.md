# world5: a large, continuous, living world

Status: **plan, 2026-10-17**, from the owner's words: *"I want the world to be much bigger as well. Right now it's
really crowded. I want a real sense of settlements with wilderness separating them, trade routes forming, everyone
having their daily lives, people specializing professions, nobility arising, and lots of emergent behaviors occurring,
not just limited to this. ... It should not look like a tile world; it should look beautiful like the Gemini
screenshot"* (docs/towns_pics/, the river village). Decided before it: two scales with tiles as bookkeeping, one
continuous world in metres, re-found world4's people, each people its own look, world4 runs on meanwhile.

This document is the frame. [towns_spec.md](towns_spec.md) is the detailed build specification for settlements, the
continuous world and the viewer; this adds what makes the world large and alive, and puts it all in one order.

## 1. Why world4 feels crowded, measured

- 176 x 176 tiles, about 21,000 of them land; **15,914 hold a building**: three quarters of the land is built over,
  because each building takes a whole 1 km tile. The largest village of 183 people covers about 1,900 km².
- So there is no wilderness to cross, no distance for trade to bridge, and every settlement runs into the next.

The towns spec's compression alone changes this: a village of 180 fits in 250 x 250 m and its fields in 2-3 km² around
it. On world4's land as it is, 1,900 people would occupy under 300 of 21,000 land tiles. **Then the land is made
bigger too** (§2), so that settlements sit 5-20 km apart with forest, moor and steppe between them.

## 2. The size of the world

| | world4 | world5 at founding | world5 grown (aim) |
|---|---|---|---|
| Land | 176 x 176 tiles (31,000 km²) | **352 x 352 tiles (124,000 km², about England's size)** | same |
| People | 1,909 | 1,909 (world4's, re-founded) | 5,000-10,000 |
| Settlements of 12+ | 46 (sprawls) | 40-60 | 100-200, a few towns of 500+ |
| Typical spacing | none (touching) | 8-20 km | 5-15 km, wilderness between |
| Land built or farmed | about 75% of land tiles | under 1% | 2-5% |
| Peoples | 5 | 5 | 5 plus any that split off |
| Seats for minds | 48 | 48 | 48-64 (§7) |

**How the land grows without losing world4's history:** world5's land is world4's land at **twice the scale**: each
tile becomes 2 x 2 tiles, its terrain and heights upsampled with noise so coasts, rivers, forests and hills keep their
shapes and gain detail; regions, peoples' homelands and named places keep their places (at doubled coordinates). Every
distance doubles, the area quadruples. Re-founding (towns_spec §10) then lays each settlement out on the new land where
its people lived. The peoples' memories of places stay true in shape; the land between them opens up.

**Speed:** world4 runs about 1 s a world hour for 1,900 people; the live pace is one world year (480 hours) a real day,
which leaves minutes a world hour. 10,000 people at a few seconds an hour fits; the speed gate (tools/speed.py) measures
it at each phase, and the bots' prehistory (§9) needs about a day of runner time for 50 years.

## 3. Wilderness

Wilderness is what lies between: it must be worth crossing and worth fearing.
- **Land:** forest, moor, marsh, steppe and mountain from `land_at` (towns_spec §2.1), drawn in full; game herds,
  wolves, wild fruit, seams of ore, timber, salt springs, all where the tiles put them today, now far from most homes.
- **Danger:** wolves take the lone at night (as now); a night out in the open needs a fire; winter journeys are hard.
  **Outlaws** (new): one cast out (by law, infamy or a feud lost) can no longer live in a settlement; they live in the
  wild and may waylay travellers. Nothing is scripted: casting out is a law the people can make; waylaying is a choice.
- **Travel takes days:** 10-20 km between villages is a day's walk (10 hours a day of travel, 1 km an hour); a trade
  journey between regions is a week or more. People carry food, camp with a fire, travel in company when they can.

## 4. Trade routes

Most of the parts exist (c69-c70 trails and price news, c86 pack beasts, c70 merchants, c92 buying from makers); what
was missing is distance and difference, which §2-§3 give. Added:
- **Journeys:** a trader plans a journey of several days: food for the way, a pack beast, company if the way is long;
  sleeps at waystations or camps (`camp`: a fire and a night outside).
- **Waystations and inns** (new building `inn`, era 1: beds and a hearth for paying guests; an innkeeper vocation sells
  food and a night's rest). They appear where routes are walked.
- **Roads from feet:** footfall already wears trails (c69); a trail walked enough becomes a road when someone builds it
  (`road`, era 3) or, earlier, a beaten track. Drawn as worn paths in the land: the trade routes are visible.
- **Markets where routes meet:** a settlement on a busy route grows (newcomers prefer busy places; craftsmen move to
  where buyers are, grand.md §6C); a market day draws its district.
- **Regional difference** is the reason to trade: copper and tin in the hills, salt on the coast, horses on the steppe,
  grain in the valleys, furs in the forest, and each people's own crafts (lifeways). Prices differ by place and are
  carried as news.
- **Measure:** goods carried more than 10 km from maker to user each season; distinct routes walked by traders; roads
  and tracks by length; prices' spread between regions.

## 5. Daily life

towns_spec §5.2 and §7: one home a household, places in the plan, a day's rhythm (home at night, out to fields and
workshops by day, the green, well and alehouse in the evening), market days, festivals at the shrine. Added here:
- **Meals at home**, cooked at the household's hearth from its store (households eat together; a household's food is
  shared by right, as kin feed kin today).
- **Children** follow a parent at work, play on the green, go to school where there is one, become apprentices.
- **Work has a place:** a smith at the smithy, a potter at the kiln, a farmer in the strips, a herder with the flock on
  the common, a fisher at the jetty. The viewer shows it (towns_spec §9).
- **Measure:** share of people at home at night (90%+), at the commons in the evening, at their work place by day.

## 6. Professions

The Phase 3 gate (grand.md) is unmet: the top tenth of makers make 40% of output (aim 60%+), 6% of made goods change
hands (aim 40%+). Distance and density change the arithmetic: in a compact village the smith is a minute away, the
next village's smith a day away. Added:
- **A household lives by a trade:** a vocation becomes the household's living (farmer, herder, fisher, smith, potter,
  weaver, miller, baker, brewer, carpenter, mason, trader, innkeeper...). It keeps its skill sharp by use (c68 rust),
  works faster and finer (c68 mastery), and sells at its door, its stall on market day, or to traders.
- **Not everyone farms:** a specialist household buys its food with its goods (bots buy food at market; the c92 buying
  path extended to food). Towns are where 40%+ do not farm (grand.md §6C).
- **Apprenticeship:** a child of 12-16 is put to a master (a deal: service for teaching, c31 service plus c-teach);
  crafts pass down families and spread by apprenticeship, so villages gain reputations (the potters of X).
- **Supply follows want:** c93's idea (a want with no seller is heard nearby and makers answer it), kept for world5.
- **Measure:** the Phase 3 gate (top tenth 60%+, 40%+ changing hands, 2-4 able crafts an adult), non-farming share in
  towns, trades a person a year (aim 5+).

## 7. Nobility

The pieces exist: groups and leaders, fealty, homage and tribute (c71-c73), titles, succession by custom, war bands and
raids (c72-c76), tenancy (c83), territory and tolls (c85). What lets nobility *arise* in world5:
- **Land worth holding:** field strips (towns_spec §4.6) are property: bought, sold, inherited, granted, let to tenants
  (c83), forfeit for an unpaid written debt (c51: a promise owed past its day may be taken as its pledge, new). A family
  that gathers strips lives off rents; the landless become tenants or labourers (c31 service).
- **The lord's household:** a lord plot (towns_spec §4.4) with a hall, retainers in service, a larger store; the lord
  feasts (grand.md §6D: feasts and gifts turn surplus into renown, to build).
- **Houses:** a family with a title becomes a named house (`Ysolde's house`), with heraldry colours in the viewer,
  marriages between houses as alliances (partnership offers carrying a promise), inheritance of title by the people's
  custom.
- **Manors:** villages sworn to a lord pay tribute (as now) and their vacant plots and strips are the lord's to grant
  (towns_spec §8.3 `grant plot`).
- **Seats for minds go where choices are** (grand.md §7): heads of houses, lords of several villages, great traders,
  war leaders; seats move as power moves.
- **Measure:** land Gini; households holding 10+ strips; titles held; polities three levels deep; marriages between
  houses; tenants' share of farmers.

## 8. Emergence

Nothing above is scripted: each is a mechanic, a reason (need, difference, distance, danger, ambition) and a way for
people to see and choose it. What emerges is measured and shown, not forced:
- **Detectors** (PLAN.md's list, extended): a route (the same pair of places traded between 5+ times), a market town, a
  feud between houses, an alliance by marriage, a rebellion, an outlaw band, a famine, a migration, a new people
  (a settlement far from its people whose tongue drifts), a guild (makers of one craft in one town acting together).
- **The chronicle** tells them as history; the viewer's TV mode prefers them.
- **The people's own ideas** (`idea`) and refusals stay the main source of new mechanics (process.md).

## 9. Getting there: one order

| Step | What | Where specified | Sessions |
|---|---|---|---|
| **0. The look, proven** | in the real viewer, one stretch of land in metres: the river village of the Gemini picture with its strips, the river and a bridge, a forest edge, a track to a hamlet 5 km off; fly from high above down to a person at the well and walk them out to the fields; compare with the picture; choose code-made or ready-made models | towns_spec §9 | 2-3 |
| 1. Foundations | towns_spec WP0: positions in metres, `land_at`, data model, flags | towns_spec §2-§3, §12 | 1-2 |
| 2. Settlements and the engine | WP1 planner, WP2 engine, WP3 bots, WP4 minds | towns_spec §4-§8 | 7-10 (parallel: 3-4) |
| 3. A large land | the 2x upsampling of world4's land; `land_at` rivers, blends, heights | this doc §2, towns_spec §2.1 | 1-2 |
| 4. Life between settlements | journeys, camps, inns, outlaws, food bought, apprenticeship, strips as property, forfeit, feasts, houses | this doc §3-§7 | 4-6 |
| 5. The viewer | WP5: one streamed scene, LOD by distance, the five peoples' looks, people walking continuously | towns_spec §9 | 4-6 |
| 6. Re-founding and a settling-in | WP6 re-found world4 onto the large land; then **30-50 years bots-only** so villages grow, routes and roads form and houses rise before minds take their seats | towns_spec §10 | 2 + runner time |
| 7. Launch | minds seated, a dev week, `configs/live_world` -> world5 | grand.md Phase 8 | 1 |

About 22-32 sessions; with parallel work packages, 12-18 of elapsed time. Step 0 first because it decides whether the
picture is reachable and how, before anything else is built; the engine work does not depend on its outcome, but the
owner's confidence does.

## 10. Gates

- Step 0: the owner compares the viewer's screenshots with the Gemini picture and says go (or how to change course).
- Steps 1-2: towns_spec §12.2.
- Step 3: the upsampled land keeps world4's coasts, rivers and regions (overlay check); no tile edge visible.
- Step 4: bots worlds on the large land, 10 years: traders cross 10+ km every season; specialists 30%+ of adults in
  settlements of 50+; at least one lord holding land worked by tenants; balance within noise.
- Step 5: phone budget; the five forms and the continuous fly-down on a phone-sized render.
- Step 6: after the settling-in, the measures of §4-§7 moving the right way; town_check clean.
- Launch: a week live, no collapse; the owner, watching, sees settlements in wilderness, routes, daily life, trades and
  lords.

## 11. Risks

| risk | answer |
|---|---|
| The picture's quality is not reachable in a browser on a phone | step 0 finds out first; fallbacks: ready-made low-poly models, a lower detail tier for phones, desktop as the showcase |
| A world 4x larger runs too slowly | speed gate each phase; people stay where they live, so cost grows with people, not land; land rules already scan near people only |
| Sparse land at founding: villages too far apart to trade or wed | re-founding keeps world4's clusters together; the settling-in decades grow them; spacing is a parameter of the upsampling |
| Emergence does not come | each mechanic is tested on bots first with its measure; detectors make what happens visible; no outcome is forced |
| Too much at once | every step ships behind flags to main; world4 runs on untouched; world5 launches only when its gates pass |
