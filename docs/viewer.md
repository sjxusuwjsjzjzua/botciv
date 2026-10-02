# The viewer: a living 3D window on the world

Status: design, agreed with the owner 2026-10-01 (models generated in code; built between
iterations of the world). This document is the foundation: change it when the design changes,
and build to it. It replaces `civ/viewer.html` (the 2D map) for the civ worlds; the first
world's viewer (`botciv/`) is left as it is.

## 1. What it must be

- **A beautiful, cozy, living world**, in the spirit of Stardew Valley, Animal Crossing and
  A Short Hike: everything in 3D, soft toon light, chunky rounded shapes, a warm palette, and
  everything gently alive (swaying grass and trees, rippling water, drifting smoke, falling
  snow, people who walk, work, chat and sleep).
- **Cute people**: chibi figures (big head, round body), each one recognisable and their own,
  wearing what they really wear and holding what they really carry, doing what they are really
  doing, hour by hour.
- **Truthful**: it shows what the engine recorded, never invents events. Where the record is
  coarse (one position an hour) it fills in only motion (walking the land between two places),
  never deeds.
- **Time is one thing**: the replay's moment *t* drives everything: the 3D scene, the clock,
  and every menu (people, knowledge, groups, chronicle, charts) shows the world **as it was at
  *t***, not as it is now. "Now" is just the last *t*.
- **Built to last**: new content (items, crafts, buildings, animals, verbs) appears in the
  viewer without code changes (sensible defaults by role), the data format is versioned and
  only grows, and the parts (data, world model, scene, menus) are separate so any one can be
  rewritten without touching the others.

## 2. Architecture

```
engine logs (world branch)          site build (Python, civ/site.py)        browser (static, no build step)
 frames: hourly positions + acts ─┐                                        ┌─ store: World-at-t model (pure JS)
 frames: daily snapshot (land v2) ├─► manifest.json, chunks/N.json,  ───►  │    ▲ read by
 events, minds (thoughts)         ┘   index.json (events, lives, firsts)   ├─ scene: 3D (three.js) | 2D fallback
                                                                           └─ ui: journal menus, clock, timeline
```

- **Data** (built by `civ/site.py` from the logs; versioned, documented in section 3).
- **Store** (`viewer/core/`): loads the manifest and chunks lazily, caches a few chunks, and
  answers questions about any moment: `store.at(t)` gives the people where they are and what
  they do, the day's snapshot (buildings, things, skills, groups, goals), events up to *t*,
  thoughts up to *t*. Nothing else touches the files. Pure functions of the data: testable in
  Node without a browser.
- **Scene** (`viewer/scene/`): draws `store.at(t)` in 3D; knows nothing of files or menus.
  A 2D map renderer implements the same small interface for weak devices.
- **UI** (`viewer/ui/`): the journal menus, clock, timeline and cards; reads only the store.
- **Art kit** (`viewer/art/`): the generated models (land, plants, buildings, people, animals,
  items) and the toon materials, as pure builders from parameters and a seed. Data-driven:
  building kind → recipe chosen by role with per-kind touches; item → look by its kind (worn,
  tool, food...); verb → animation. Anything unknown gets the default for its role or class,
  never an error.

No build step: native ES modules served as static files by GitHub Pages. three.js is vendored
(`viewer/vendor/`, MIT, an exact pinned version), so the site never depends on a CDN being up
or a library changing under it. The whole viewer is copied as a folder by `civ/site.py`.

## 3. Data format (v3)

The site build writes, per world:

- `manifest.json`: `format: 3`; the world's meta (name, size, hours per day and year, first and
  last hour); terrain and heights; the content catalogue the art kit needs (each building kind
  with roles and era, each item with class: worn/tool/weapon/food/material and its slot, each
  animal, each terrain and deposit); the static facts of every person who ever lived (name,
  born, died, cause, parents, mind, temperament, wants); the chunk table `[[first hour, last
  hour, file]]`.
- `chunks/N.json` (a span of about 20 days): every hour, every person
  `[id, x, y, health, fullness, verb, detail]` (detail: what is gathered, made, built, whom one
  follows or strikes), herds and packs; every daily snapshot in the span (land v2: buildings
  with crop growth, deposits, piles, roads, each person's things, skills, home, partner, groups
  and goal, groups as they stand); the events and thoughts of the span.
- `index.json` (small, loaded at once): every notable event `[t, kind, text, who]` for the
  chronicle and the timeline's marks; lives (births, deaths); firsts and losses of crafts;
  population and era by day.

Rules that keep it future-proof:
- **Append-only lists**: a field is only ever added at the end; readers take what they know and
  ignore the rest. A breaking change bumps `format`, and the viewer says so plainly.
- **Snapshots are whole**: each daily snapshot stands alone (no deltas yet). If size demands it,
  a chunk may later hold a key snapshot and changes from it; the store hides that.
- **History before a field existed**: the store fills what it can from events (groups from
  their founding, joining and laws) and shows nothing rather than something false.

Budgets: index.json under 1 MB, each chunk under 1 MB gzipped, first view under 3 MB in all.

## 4. Art direction

- **Light**: a toon ramp of three soft steps, warm key light from the sun's place in the sky,
  cool fill from the sky, one soft shadow map, a gentle rim on people. Light follows the hour:
  dawn rose, morning gold, afternoon white, evening amber, night blue with warm lit windows,
  fires and lanterns.
- **Seasons**: spring blossom and fresh green; summer deep green; autumn ochre and red leaves
  falling; winter snow on the ground, roofs and boughs, frozen marsh edges, breath and smoke.
- **Shapes**: low-poly but rounded (bevelled boxes, smoothed cylinders, spheres), chunky
  proportions, no sharp realism; a soft outline (inverted hull) on people and buildings.
- **Palette**: earthy and warm; each terrain its own hue family (grass, rich soil, forest,
  hills, mountain, water, marsh, sand); people's clothes from their materials (hide browns,
  linen creams, wool blues and greys, dyed reds); metals catch the light.
- **Motion**: everything breathes: grass and trees sway (in the shader, free), water ripples,
  smoke and sparks drift, people bob as they walk, squash a little as they land and work,
  blink, turn their heads to whom they speak to.

## 5. People

- **Generated from the person**: the seed is the person's id; skin, hair (style and colour),
  eyes and face come from it, and children take after their parents (their colours drawn from
  the parents'). Height and build come from age: children small and round, elders a little
  stooped and grey. Every person always looks the same.
- **Dressed by the record**: worn items choose the outfit layers (tunic, cloak, fur coat, robe,
  hat, shoes, jewellery); the best tool or weapon carried is in hand, chosen for what they do
  (sickle when reaping, spear when hunting, hammer when building).
- **Doing what they do**: each verb has an animation: walk, gather (stoop and pick), hunt
  (spear raised, in a party), fish (rod, line, splash), craft (hammering or working at the
  workshop), build (hammer at the frame), plant (sowing), eat, rest and sleep (inside if at
  home, zzz), talk (bubble, face the listener), teach (gesturing), give/trade (hand over a
  bundle), attack (swing, the struck flinch), follow, tame (rope). Unknown verbs: idle.
- **Moving truthfully**: positions come once an hour; between them the viewer walks the person
  along a path over the land (never across water), arriving in time, then does the hour's
  work in place.
- **Moments**: speech bubbles from what was said; small emotes for a pledge (heart), a new
  skill (sparkle), a theft (!), a blow (anger), a birth (a baby in arms), a death (they lie
  down and fade; a grave if one is dug).
- **Many at once**: one shared mesh per body part for everyone (instanced), each person a set
  of transforms and colours computed each frame; far off, a single simple figure.
- **Own minds**: those who think for themselves are marked in the menus and cards (✦), not in
  the world, which is theirs to live in like anyone.

## 6. The land, buildings and animals

- **Land**: a height field (hills and mountains rise, water and marsh lie low, shores slope),
  tiles blended at their edges; a water surface with gentle waves and foam at shores; forests of
  instanced trees (several species by place, size varied), grass tufts, reeds on marsh, rocks
  on hills, berry bushes, flax, herbs and grain where deposits are, clay banks, flint and ore
  showing on hillsides; roads as worn paths.
- **Buildings by role**, every kind recognisable: shelter (lean-to), house, brick and stone
  houses (cottages of their materials), store and granary (on stilts), fire (stones and flame),
  kiln and furnace and bloomery (domes with smoke and glow while working), loom, oven,
  tannery, brewhouse, workshop, smithy (open sheds with their tools), farm (tilled rows whose
  crop sprouts, grows and turns gold, by the snapshot's growth), pen and stables (fences with
  the animals in them), palisade, walls, gatehouse, tower, dock, shipyard, mill (turning), road,
  bridge, aqueduct, shrine, temple, hall, market, school, library, scriptorium, infirmary,
  observatory, cairn and grave (with their carved names). Unfinished: a frame and scaffold.
  Owned by a group: its banner colour. Things in a store: a few crates or sacks to show it.
- **Animals**: deer, boar, aurochs, wild goats, sheep and horses in herds that graze and drift;
  tamed goats, sheep, cattle, pigs and horses in pens; wolves at night, slinking.

## 7. Camera and controls

A tilted three-quarter view (perspective, narrow angle, a little tilt-shift softness at the
edges) that pans, zooms and turns by mouse, touch and keys; zoomed far out it eases into a map
view. Click anyone or anything for its card. Follow a person (the camera keeps them centred
and their card open). A storyteller camera may drift to what is happening (speech, births,
fights, firsts). Time: play, pause, speeds, a timeline with marks for births, deaths, firsts,
fights and monuments; jump to a person's birth or death; "now".

## 7a. Story

Story is a speed, and the default. Following someone, it is their story: each hour stays as long as
what happens in it to them deserves (what they set out to do, what they say and is said near them,
what befalls them, and for minds of their own what they think as they decide), and their sleep and
long work hurry by; story lines along the bottom tell it as it unfolds, and their thoughts rise over
their heads as clouds. Following no one, it is the world's story: it lingers on its notable moments
(births, deaths, fights, firsts, monuments, laws) and the camera goes to each. Names in the lines open
that person. (`ui/story.js`.)

## 7b. TV

For watching from the sofa (a tab cast to a television, a screen left on): the 📺 TV button, or `#tv`
in the address to start at once. It plays on its own at story speed. While you have not chosen anyone,
a storyteller chooses whom to watch (awake and doing something: minds of their own first, speaking or
among others, the same choice on every replay), follows them for up to 16 hours, gives way when they
sleep, and, after at least 4 hours with them, cuts to a notable moment elsewhere (a birth, a death, a
blow, a first, a law, a monument) and whoever is in it. Someone you follow (before TV, or with Follow on
a card in TV) stays followed until they die. A side panel in large type (at the bottom on a phone) gives
the day, whom we watch and why, with their portrait, their story lines and thoughts, and what happened
in the land; the picture shifts so the watched one is in the open part. Everything can still be
clicked: people and buildings in the picture, the names in the panel, its Journal button; the card and
journal open over the picture, Esc closes them first, then leaves TV. Panning away lets the camera go;
untouched for 20 seconds, it goes back to the story. The panel's buttons and the cursor fade after four
seconds untouched; F for full screen; the screen is kept awake. At the newest hour it plays the last day
again, looks for a newer world every two minutes, and carries on from where it was (`?at=`, `?watch=`).
(`ui/tv.js`.)

## 7c. Watching someone

The way it is meant to be watched: find someone, Follow, and watch what happens. Watching is one state
in `app.js` (`view.watch = {id, by: "you" | "storyteller", lost}`), shared by the ordinary view and TV:

- **Follow** (on a card or the journal page) starts watching and plays at story speed (from a day back
  at the newest hour, so there is something to see). From far out the camera flies down to them; close
  already, it keeps its zoom. Follow again on the same card ("Stop following") stops.
- **Clicking anyone or anything while watching** opens its card and journal page; whom you watch does not
  change, and their story goes on.
- **Zooming and turning** keep following. **Panning** lets the camera go: a "↩ Back to …" pill (or B)
  flies back; its × stops following.
- **Their death** is told in the story lines; outside TV, watching stops there.
- Switching between map and 3D, and a newer world (offered by a pill every two minutes; TV takes it by
  itself), keep the moment and whom you watch.
- People walk evenly through each hour, from doorstep to doorstep, so the camera that follows them never
  stops and starts; a far jump of the camera is an eased flight that rises a little on the way. Names
  over heads: whom you watch and have chosen, and close up only the five nearest the middle.

## 8. The journal (menus at *t*)

Panels styled as a field journal, all showing the world at *t*:
- **People**: who is alive at *t* (with the dead of before), their portrait (rendered from
  their 3D figure), age at *t*, crafts and skill at *t*, what they carry, their goal, and for
  those with minds of their own their thoughts up to *t*.
- **A person**: their life so far: family tree, partner, children, home, groups, skills and
  belongings at *t*, what they said and did up to *t*, their thoughts up to *t*.
- **Knowledge**: the craft tree by era; who is able or a master at *t*; first practised and lost
  up to *t*.
- **Groups**: as they stood at *t*: leader, members, laws, dues, treasury.
- **Chronicle**: everything notable up to *t*, newest first; click to jump there.
- **Measures**: population, era, deaths by cause, up to *t*, with the cursor.

## 9. Quality and testing

- **Store** (pure JS): tested in Node (`node --test viewer/core`) against a small built site.
- **Site build**: Python tests check the format (version, append-only lists, budgets).
- **Looks**: a screenshot script (Playwright with the installed Chromium) renders set views
  (dawn over a village, a winter night, a crowded market, a close-up of one person) after each
  change; they are looked at, and sent to the owner at each phase.
- **Performance**: the reference phone is a **Pixel 9** (the owner's): smooth (30+ frames a second, 60
  where it can) with 300 people and 1000 buildings; 60 on a laptop. How: resolution adapts to the frame
  time; phones get a lighter tier (coarser terrain, fewer tufts, smaller shadow map); everything small
  is drawn in blocks that are skipped out of view and choose their detail by distance; the view ends
  where the haze does; no shadow pass when zoomed out to the map's view; nothing allocated per frame.
  Budget at the default phone view: about 0.55 M triangles in the main pass, about 0.95 M with
  shadows (measured with `?debug=1`, which also shows frames a second and draw calls).
- **Accessibility**: reduced motion honoured, keyboard reachable, readable labels.

## 10. Phases (each shipped on its own; the 2D map stays as fallback until the 3D one is whole)

1. Data format v3, the store, and menus at *t* (in the current 2D viewer first).
2. The 3D land: terrain, water, plants, sky, day and night, seasons, camera.
3. Buildings: the kit for every role, construction, crops, pens, fires and smoke.
4. People and animals: the figure generator, dress and tools, animations, paths, bubbles,
   emotes; herds and wolves.
5. The journal UI and polish: portraits, timeline, storyteller camera, phones, speed.

Where it stands (2026-10-01): 1, 2 and 4 in; 3 in a first form (every kind has a look; smoke, glow,
group banners and finer shapes to come); 3D is the default (the map is a switch away, and the fallback
where 3D cannot run). Trees between the camera and what it watches sink smoothly into the ground, each whole (no speckle). Phone budget holds with
the figures in: about 0.4 M triangles in the main pass, 0.72 M with shadows.
