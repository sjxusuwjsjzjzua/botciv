# Roadmap: where botciv stands and how it gets where it is going

Written 2026-10-02 (rules c41) as a handover, at the owner's request before archiving a long
session. It replaces the first-generation roadmap of 2026-09-30, which is in git history and was
superseded by [civilization.md](civilization.md). Read this after [process.md](process.md)
section 0 (the mode decides how much of it to attempt).

The rules that bind everything below:

- **The engine owns the world.** The model only chooses actions.
- **Mechanics, never scripted outcomes.** The people decide what happens.
- **Nothing hidden.** Everything is perceivable by the people, recorded, and measurable.
- **The people never learn they are simulated.** No "simulation, agent, game, turn or tick" in a
  prompt; a test checks this.
- **Free tiers only.** Gemini, Groq and Kaggle's GPU.
- **This repo is public.** Keys are only ever sent as headers, and never written anywhere.

---

## 1. Where we want to be

The owner's intent, in their words and in measures:

1. **A sandbox that grows into a civilisation of its own making.** The people farm, herd, trade,
   feud, make law, found dynasties, write, and build, because the world makes those things
   possible and worth doing. None of it is scripted.
2. **A society big enough to specialise.** That means hundreds of people: most of them cheap bots,
   with a few dozen language-model people at the centre who think, talk and remember.
3. **Eras reached by the people themselves.** The content runs from foraging (E0) to classical
   institutions (E4): writing, books, schools, markets, treasuries. Each step pays off on its own.
4. **Something beautiful to watch.** A 3D world on a par with Stardew Valley, Animal Crossing or
   A Short Hike. It runs on a Pixel 9 phone. The best way to watch is to find someone, Follow,
   and let the story unfold; TV mode does that from the sofa.
5. **It runs itself, cheaply.** The worlds advance on GitHub Actions and Kaggle. Claude's tokens
   are spent only on improving the world, at the rate the owner's mode allows.

**North-star measures**, read from `tools/civ_round.py`, `tools/civ_balance.py` and the world
state:

| Measure | Now (2026-10-02) | Target |
|---|---|---|
| Steps refused (world2, e4b model) | 16-22% per piece | under 10% |
| Steps refused (world2, the free-tier models) | 9-16% (in world3, retired) | under 8% |
| Highest era practised by many (5+ able) | E1, with E2 just begun (smelting: 5 able) | E2 broadly by year 8, E3 by year 12 |
| Crafts with able people (of 45) | world2 27, world3 24 | 35+ |
| Writings in the world | 0 in both | used: deals, laws, ledgers |
| Named places | world2 0, world3 1 | many: a geography of their own |
| Tamed and herded (able at herding) | 2-3 people | a herding economy (20+) |
| Prompt, 95th percentile | about 4,600 tokens | 3,500 (the CI budget test) |
| Deaths a piece (world2) | 0-4, mostly wolves in winter | low, and from choices, not confusion |

---

## 2. Where we are

### 2a. The systems

| Part | State |
|---|---|
| **botciv/** (generation 1, the first API world) | **Retired** (2026-10-02, §6.3). `world.yml` is gone; the `world` branch keeps its history and `botciv/` stays in the tree, unmaintained. |
| **civ/** (generation 2: content, engine, minds) | **The live system.** See below. |
| **world2** | Kaggle T4 GPUs, model `gemma4:e4b`, 12 parallel slots. **290 alive** (335 ever), 48 language-model minds. Day 256, year 7, rules c41. The hourly schedule caps it at 3.8 GPU hours a day and 27 a week. |
| **world3** | **Retired** (2026-10-02, §6.6): `world3.yml` is gone, the `world3` branch keeps its history (282 alive, day 106). Its free-tier capacity now advances world2 whenever Kaggle has no hours. |
| **Viewer** (`civ/viewer/`) | Generated 3D, three.js r186, with no build step. Published at <https://sjxusuwjsjzjzua.github.io/botciv/world2/>. |
| **Tooling** | `civ_round.py` (read the world by rules version and model), `civ_balance.py` (bots-only worlds), `kaggle_world2.py`, `advance_civ.py`. Tests: **254**, all passing. |
| **Process** | **Mode 2, every 12 hours.** The routine `trig_019d2ZWv6HLKCoPCRND7WobZ` starts a fresh session at 05:47 and 17:47 UTC for one pass of the loop. It ships by pushing a `claude/auto-<name>` branch; `automerge.yml` merges it into main once ci passes (§6.4). |

**The content of civ/** is data, under `civ/content/`:
- 126 items;
- 45 crafts, each with skill levels, prerequisites and teaching;
- 103 recipes;
- 44 buildings, defined by their roles (shelter, store, workshop, farm, pen, hearth, monument…);
- process buildings that work unattended (kiln, tannery, furnace, oven, brewhouse);
- effects as hooks;
- terrain and deposits;
- a generic recipe planner (`civ/plan.py`), which the bots use to climb.

Foundations F from civilization.md are done, and so is the content of eras E0 to E4. What remains
is getting the people to *use* the later eras.

### 2b. The live worlds in numbers (2026-10-02)

| | world2 | world3 |
|---|---|---|
| Buildings | 972: 236 farms, 180 stores, 153 shelters, 90 fires, 56 looms, 52 cairns, 45 houses, 40 kilns, 39 tanneries, 39 pens, 22 workshops, 14 furnaces, 3 ovens, 2 brewhouses | 897, a similar mix, with 67 kilns and 2 furnaces |
| Groups | 55 living groups | 54 living groups |
| Crafts in use | Foraging and Neolithic crafts broadly. Charcoal 40, boatbuilding 9, smelting 5, casting 1, goldsmithing 1 | Similar; wheelwrighting 2 |
| Game | 15 herds and 113 beasts, down from 49 herds and 369 beasts. Hunted out near people; herds return only in wild land | 29 herds, 217 beasts |
| Wolf packs | 7 | 6 |
| Refused steps, latest pieces | 16-22% | 9-16% |
| Deaths | Few; mostly wolves in winter | Few |
| Prompt | median 4,285 tokens, p95 4,613; about 210 tokens out | similar in, about 250 out |

### 2c. What the long iteration session (2026-10-01/02) did

**Rules c23 to c41**, about one change per Kaggle round. Most were forgiving steps or truthful
refusals; each was balanced with bots before shipping:

| Rules | Change |
|---|---|
| c23 | Known wrongs |
| c24 | Fishing gated |
| c25 | The guard warns, then strikes once |
| c26 | Tracks, gathering for crafts, the next-nearest spot |
| c27 | Load text |
| c28 | Crafts fetch fish and game |
| c29 | Putting into one's own store with room |
| c30 | "gather what?" |
| c31 | Crop wording |
| c32 | Reap, then sow |
| c33 | Overflow pile beside a full store |
| c34 | Where things come from; gift default |
| c35 | Winter and berry timing |
| c36 | Hunting: tracks only within reach; says where herds are left |
| c37 | Sowing fetches seed from one's store |
| c38 | Slaughtering a wild beast hunts it |
| c39 | Walls keep wolves out |
| c40 | Fishing for a craft lasts as long as the catch takes |
| c41 | Crafts fetch materials from remembered places up to 30 steps away |
| c42 | Stone is never sought in the heart of a mountain; the refusal names the nearest reachable stone |
| c43 | What the dead leave can be claimed and falls to ruin; couples seek a home of their own; game returns to a crowded land; cloaks of plaited fibre; repeated refusals said back |
| c44 | Beasts can be given from pen to pen; herders give breeding pairs to kin and friends |
| c45 | A gather of a food that is not there gathers one that is, and says so |
| c46 | Laden full, one sets the bulkiest load down in one's own store first; viewer: buildings rise as built, the dead's stand grey |
| c47 | The prompt cut by a seventh (median about 4,200 to 3,600 tokens): duplicates, bare buildings, recipe hours and steps one cannot use left out |

**The two-world loop** (ended 2026-10-02, §6.6). world2 and world3 ran side by side; `civ_round.py` pools them by rules
version.

**The viewer, from scratch**, in 3D:
- **Land:** terrain, water, flora with seasons and snow; sky with day and night.
- **Buildings and animals:** buildings by role, animals, smoke.
- **People:** chibi people with looks inherited from their parents, clothes from what they wear,
  and tools for the task.
- **Words over heads:** bubbles, thoughts and emotes.
- **Menus at the moment shown:** the journal (people, knowledge, groups, chronicle, measures),
  portraits, the timeline, story speed.
- **TV mode.**
- **Phone budget:** about 0.4-0.7 M triangles. The 2D map remains the fallback.

**Watching, made seamless** (viewer.md section 7c):
- Follow, then click anything without losing whom you watch.
- Pan away, then "Back to…".
- In TV, the storyteller only chooses when you have not.
- People walk evenly between hours.
- The camera flies between distant people.
- Trees in the way sink whole into the ground; there is no more speckle.

### 2d. What is weak (an honest list)

1. **The small model stumbles.** e4b has 16-22% of steps refused against 9-16% for the larger
   models. Most refusals are now *true* (the game is hunted out, no fish caught, no field free),
   but the model keeps asking for the same thing, such as "hunt deer" in a hunted-out land.
   - Forgiving steps have reached diminishing returns.
   - The next gains come from:
     - memory of what was refused;
     - the prompt showing only what is possible;
     - a bigger model when the GPU allows.
2. **Later eras are reached but not lived.** World2 has 14 furnaces but 5 smelters, 39 pens but
   2 herders, 0 writings and 0 named places. The content exists; the *reasons* and the *paths*
   for the language-model people to use it are thin, and bots climb only what their goal weights
   favour.
3. **The ecology runs one way.** Game is hunted out near people (by their own doing, which is
   fine), but the alternatives are not yet taken up widely: herding has 2 able people, and fish
   are hard bare-handed. Food security now rests on farms.
4. **The prompt is over budget.** p95 is about 4,600 tokens against the 3,500 target in
   civilization.md Gate F. Every token cut is more decisions on the free tiers.
5. **Mechanics gaps** (mechanics.md, "Next"):
   - children who depend on their parents (families as economic units);
   - shores that are fished out;
   - groups that act on reputation;
   - treasuries and taxes, used;
   - markets that gather posted trades, used.
6. **The viewer's open ends:**
   - Phase 3 (buildings) is in a first form: finer shapes, construction stages and group banners
     everywhere are still to come.
   - Phase 5 (journal polish) is open: a Knowledge tree view and measures charts.
   - Animations are simple.
   - No sound.
7. **Operations:**
   - World branches grow without bound.
   - Kaggle is the only GPU, at 27 hours a week.
   - (Fixed 2026-10-02: scheduled sessions now merge through `automerge.yml`, and world 1 is
     retired.)

---

## 3. Constraints that shape the plan

- **Claude tokens are the scarcest budget.** The owner sets the mode (process.md section 0).
  Most of the plan below is sized as one-session steps, so mode 2 (one change a session) can
  carry it. Bigger steps are marked **[mode 3]**.
- **Decisions are the world's budget.** Kaggle T4s give about 400-700 answers an hour, and the
  free APIs a few thousand a day. Every token cut from the prompt is more decisions; every
  process building and longer plan means fewer decisions needed.
- **Kaggle allows 27 GPU hours a week**, and the hourly schedule spends it by itself. **Do not
  dispatch extra runs in mode 1 or 2.**
- **Bots first.** No rule ships without `tools/civ_balance.py` before and after, at 3 seeds × 3
  years. Run 6 seeds when the result is borderline: seed 1 swings ±15 alive on its own. Undo what
  makes things worse.

---

## 4. The roadmap

There are six tracks. Within each, the steps are in order. Each step is about one session unless
marked. The **gate** says when a track step is done.

### Track W: world health (the loop; never finished)

This is what every mode-2 session does (process.md section 3): measure, pick the dominant failure,
make one change, test it with bots, ship it.

- **W1. Refusals under 12% in world2.** In order:
  1. **Repeated refusals.** When a person's last 3 steps were refused for the same reason, put that
     reason in the next prompt as "you tried X and could not: <reason>". It already exists in part
     as wake reasons; make it explicit and short. This targets "hunt deer" asked again and again.
  2. **"Writing needs a clay tablet…".** A writing step with no tablet (the refusal is in
     `civ/society.py`) should make one when the person can, as crafts now fetch their inputs.
  3. **Cloak and tunic short of hide.** Say where hide can be had (trade, a pen's slaughter), or
     offer a fibre or wool cloth recipe if the content lacks one.
  - **Gate:** three consecutive world2 pieces under 12% refused.
- **W2. Deaths stay rare and meaningful.** Watch wolves in winter (c39 made walls safe) and
  starvation in a hunted-out land.
  - **Gate:** no piece with more than 2 deaths from confusion, meaning a refused step loop before
    a death.

### Track C: civilisation content in use (the heart of the owner's goal)

The content to E4 exists; the work is making each era *worth reaching* for the people and
*reachable* for the bots. Do one era at a time, bots first, each with a measurable uptake.

- **C1. Herding (E1) as the answer to the hunted-out land.**
  - The pieces exist: pens, taming, milk and wool, and slaughter on demand. 39 pens but only 2
    herders means taming is too hard, too hidden, or not worth it.
  - Steps:
    1. Read the bots' `herd_goal` and the taming refusals.
    2. Make taming a short path: a herd within sight and a pen of one's own leads to "tame".
    3. Have the refusal for a hunted-out land name herding as the lasting answer.
  - **Gate:** bots average 20+ able herders by year 4; world2 herders rise piece over piece.
- **C2. Writing (E2) used at all.**
  - Zero writings in two worlds of 280+ people.
  - Make the payoff real and visible:
    - a written deal is kept by the engine and readable by whoever holds it;
    - a written law posts at a place;
    - a store keeps a ledger.
  - Make the path short: clay tablet, stylus, the writing craft.
  - The bots' `legacy_goal` and `lead_goal` should write laws and deals when they can.
  - **Gate:** bots write in 4 of 6 seeds by year 6; any writing in a live world.
- **C3. Places named, and a geography of their own.** A `name_place` verb exists (places: 1 in
  world3). Prompt the people with unnamed landmarks they live near ("the hill north of your house
  has no name"). The bots name the place of their group's founding.
  - **Gate:** 10+ named places in world2 within a week.
- **C4. Metal (E2 to E3) as an economy.**
  - 14 furnaces and 5 smelters exist; tin is scarce by design.
  - Checks:
    - Does anyone trade for tin?
    - Does a furnace owner hire?
    - Do bronze tools pay (the tool hooks)?
  - Fix the thinnest link the bots reveal.
  - **Gate:** bots reach bronze tools in 4 of 6 seeds within 6 years; world2 makes its first
    bronze.
- **C5. Institutions (E4)** **[mode 3, several sessions]**:
  - books (learning up to beginner level without a teacher);
  - schools;
  - markets gathering posted trades;
  - treasuries and dues;
  - the calendar;
  - medicine.

  Each is a role or hook that exists in content. Make each one *used* by bots, then watch the
  people.
  - **Gate:** civilization.md section 6 measures, era by era.

### Track M: mechanics the people can build on (from mechanics.md)

Build these only when the live world shows the need. Think each one through (process.md section
4): does the problem exist in the engine, can the people perceive it, does it pay off at the
right size, can it be measured, what does it cost in tokens?

- **M1. Dependent children.** Children eat from the family's store, and parents feel the cost.
  Families become economic units, and inheritance matters. Try it with bots first: an earlier
  attempt, children sleeping under a parent's roof, cost 638 alive against 670 and was undone.
- **M2. Shores that are fished out.** A second commons to ruin or to manage, now that game is
  hunted out.
- **M3. Reputation acting in crowds.** Taking back from a thief still needs one's people beside
  one. Watch whether groups organise before building anything.
- **M4. Groups' property, used.** Treasuries, dues, and a group store the leader controls. These
  exist partly; measure their use first.

### Track P: prompt and capacity (more decisions for the same free tiers)

- **P1. The prompt to the 3,500-token budget.**
  - Measure what takes the tokens (rules about 1,200, verb help about 1,000, the rest
    perception).
  - Cut:
    - rules sections the person has no reason to know (the per-person view in civilization.md
      section 2);
    - verb help for verbs they cannot use;
    - long holdings lists.
  - The CI test `test_prompt_budget_and_words` should assert the 95th percentile at 3,500 on a
    large generated world.
  - **Gate:** world2 p95 at or under 3,500. That is about 30% more decisions on the token-limited
    free models.
- **P2. A bigger model on Kaggle when the GPU allows.**
  - e4b was chosen for decisions per hour; gemma4:26b refuses far less but answers slowly on two
    T4s.
  - Retry 26b with fewer slots once P1 shrinks prompts.
  - Alternatively, run more minds on e4b and accept the refusals.
  - Measure with `civ_round.py` for one piece each.
- **P3. More free providers** through the OpenAI-style adapter, if any are truly free. Check the
  terms; never use trial credit.

### Track V: the viewer (between iterations; mode 3 for the larger pieces)

- **V1. Phase 3, buildings, finished:**
  - construction stages: frame, then walls, then roof;
  - group banners on every building a group owns;
  - finer shapes for the E2-E4 kinds: furnace glow, market stalls, temple, library;
  - fields that show their crop at each stage.
- **V2. Phase 5, the journal:**
  - a Knowledge view drawn as the tree, coloured by who knows what, with masters and lost crafts;
  - Measures charts (population, eras, trade, deaths by cause) at the moment shown;
  - a Places page once places are named.
- **V3. Watching:**
  - **Live check first:** the owner reported the TV glitches and the tree speckle, both fixed on
    2026-10-02. Confirm on the phone.
  - Smaller follow-ups:
    - ease the story speed around speech;
    - "follow the family" (cycle to kin);
    - the storyteller prefers people the owner has followed before (remembered on the device).
- **V4. Life in the picture:**
  - richer animations: work cycles per craft, carrying loads, sitting at a fire, a child following
    a parent;
  - weather (rain, wind in the trees);
  - ambient sound (optional, off by default).
- **V5. Performance on the Pixel 9:**
  - keep about 0.7 M triangles with shadows;
  - measure with `?debug=1` on a real phone after each art change.

### Track O: operations (keep it running with no one watching)

- **O1. The routine can merge.** **Done 2026-10-02** through `automerge.yml` (§6.4): routines
  here cannot carry the GitHub connector, so a scheduled session pushes a `claude/auto-<name>`
  branch and the repository merges it once ci passes.
- **O2. Bound the world branches.**
  - Logs grow every piece; move minds and events logs older than about 30 days into monthly
    archives (or drop them from the branch).
  - The viewer reads chunks, so the site stays small.
- **O3. Retire world 1.** **Done 2026-10-02** (§6.3): `world.yml` deleted, the site builds only
  the civ worlds, the `world` branch kept as history.
- **O5. The bot farm.** **Done 2026-10-02:** `bots.yml` runs bots-only worlds without end on spare
  Actions capacity; `tools/bot_stats.py` reads them by rules version. The long land (`botworld.yml`,
  /botciv/long/): one bots-only world never reset, its whole history charted in the journal.
- **O4. Health in one command.** `tools/civ_round.py` reads the world by rules version and model.
  Teach `tools/health.py` the civ worlds, so that mode 1 is one command.

---

## 5. The next ten steps, in order

These are for whoever picks this up: a mode-2 session takes the first one not done. Following the
owner's decision (§6.1), they favour **polish of what exists** over pushing into later eras: smooth
play with fewer refusals, the eras already reached made lived and visible, and a beautiful viewer.
C4 and C5 wait until this list is done.

1. **W1.1** Repeated refusals said back to the person (the "hunt deer" loop).
2. **C1** Herding as the answer to the hunted-out land (bots first).
3. **P1** The prompt to 3,500 tokens (cut per-person rules and verb help; a CI assertion).
4. **W1.2 and W1.3** Writing without a tablet, and cloaks short of hide.
5. **V1** Buildings finished: construction stages, group banners, crops at each stage (viewer;
   check on a phone-sized render).
6. **C3** Named places (a nudge from unnamed landmarks; bots name their founding place), and a
   Places page in the journal.
7. **V2** The Knowledge view and Measures charts in the journal.
8. **C2** Writing used: deals and laws kept, the short path to tablets, bots writing.
9. **O4** Health for the civ worlds in one command (mode 1 becomes one command).
10. **V4** Life in the picture: work cycles per craft, carried loads, sitting at a fire, children
    following a parent.

Done since this was written: **W1.1** (c43: a refusal met twice in three days is said back plainly),
part of **W1.3** (c43: a cloak can be plaited from fibre, no hide needed), and outside the list the
housing lock and the game that never came back, both found in the long land (c43, process.md round 32),
and **C1**'s bot gate (c43: taming follows tracks like hunting; bots reach 25+ able herders by year 4).
Also **O1** (scheduled sessions merge through `automerge.yml`; this line
was itself shipped that way, as its first check) and **O3** (world 1 retired), both on 2026-10-02.

---

## 6. The owner's decisions (2026-10-02)

1. **Polish before later eras.** "Don't push too hard to later ages; we need to do a lot of
   polishing." E1-E2 are made lived, smooth and good to watch first; E3-E4 content stays as it is
   (it exists and the bots may reach it) but no work goes into pushing the people there yet.
2. **Keep the smaller models for now.** (Since §6.6, world3's free-tier models think in world2 in the hours Kaggle has none.) world2 stays on `gemma4:e4b` with 12 slots; world3 keeps
   its free-tier models with 16 minds. Refusals are met by polish (W1, P1), not by a bigger model.
3. **World 1 is retired.** `world.yml` is deleted; the site no longer builds the first land or its
   large bot land, and its root leads to the civ worlds. The `world` branch keeps its history and
   `botciv/` stays in the tree (its tests still run) but is no longer maintained.
4. **The routine merges its own changes.** Connectors cannot be attached to routines in this
   organization, so the repository merges for it: a scheduled session pushes a
   `claude/auto-<name>` branch made from the latest main, ci.yml tests it, and `automerge.yml`
   merges it into main when the tests pass (a branch that does not merge cleanly is left, and the
   run says so). Sessions with GitHub tools may still use a PR.
5. **Still open: a fresh world later.** world2 and world3 carry years of history and every rules
   change by migration. At some point a fresh world on the finished rules (a "world 4", 100+ minds
   when capacity allows) gives a clean read of what the rules produce from the start.
6. **One world (2026-10-02).** "We will focus all our resources on one world. Any time Kaggle isn't
   running on its world, we will use Gemini / Groq to keep it moving forward." world2 is that world;
   world3 is retired like world 1 (workflow gone, branch kept, off the site). `world2.yml` runs every
   hour: a Kaggle piece while the GPU budget allows, otherwise about 45 minutes on the free tiers
   with the same 48 minds. One workflow, so the two never write the branch at once.

---

## 7. How to work: a handover from the long session

- **Start.** Read [process.md](process.md) section 0 (the mode) and the latest "Loop, round N"
  paragraphs at its end; then run `python tools/civ_round.py --versions 2`.
- **The loop.** Measure, pick the dominant failure, think it through, balance before, build, test,
  balance after, bump `RULES_VERSION` in `civ/prompt.py`, add a "Loop, round N" paragraph, ship
  (a PR to main merged when CI passes; or, without GitHub tools, a `claude/auto-<name>` branch from
  the latest main, which `automerge.yml` merges when CI passes).
- **The viewer.**
  - Its design is [viewer.md](viewer.md); section 7c covers watching.
  - Test it with Playwright on the pre-installed Chromium: executable
    `/opt/pw-browsers/chromium-1194/chrome-linux/chrome`, with swiftshader flags
    (`--use-gl=angle --use-angle=swiftshader --enable-unsafe-swiftshader`).
  - Build a site with `civ/site.py`, or copy `civ/viewer/*` over a fetched world site, and serve it
    with `python -m http.server`.
  - `window.__view` and `window.__scene` are exposed for tests.
  - Swiftshader runs at a few frames a second: check logic by state and by sampling functions,
    not by frame rate.
- **Gotchas learned the hard way:**
  - Do not stash files while a background balance run imports them: one comparison was run on the
    wrong code that way.
  - Seed 1 of the balance is volatile; use 6 seeds when a result is within about 2%.
  - A test should fail without the change it guards; check it once.
  - `rm -rf` on a shell variable is refused by the safety check; use fresh directories or
    `"${S:?}"`.
  - Background shell commands time out at 30 minutes unless `timeout` is raised (up to 2 hours).
  - Most refusals are now *true*: prefer telling the truth well (where, when, how much) over
    forgiving a step that would mislead.
- **Where the history is:**
  - process.md, from section 11 and the two-world loop onward: every round with its numbers;
  - [balance.md](balance.md): bot numbers;
  - PLAN.md section 6a: the people's ideas;
  - [civilization.md](civilization.md): content and eras;
  - [v2.md](v2.md): the civ design;
  - [mechanics.md](mechanics.md): the gap analysis.
