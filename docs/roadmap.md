# Roadmap: many resources, a tech tree to the Bronze Age, many more people

Written 2026-09-30 (rules w36) at the owner's request. The three goals:

1. **A much wider variety of resources**, found in particular places.
2. **A tech tree that reaches the Bronze Age**, discovered by the people,
   not handed to them.
3. **Many more language-model people**: 16 today, 100 or more later, all
   on the free tier.

The rules that govern everything else still hold: the engine owns the
world and the model only chooses; mechanics make things possible and never
script outcomes; everything is perceivable, recorded and measurable; the
people never learn they are simulated; free tier only. This roadmap is the
order in which to do it, and the gates that say when a step is done.

## 1. Where things stand

| | Today (day 335, w36) |
|---|---|
| People | 16 alive on a 24 x 24 land (69 have lived) |
| Resources | berries, wood, stone, fibre, deer (meat, hide, bone), fish, seeds and grain |
| Made things | 14 hidden two-item recipes (rope, spear, axe, net, basket, pot, cloak, snare, necklace, drum, poultice, cooked meat, flour, bread), one technique (smoking), six buildings, and own-design things (w34) |
| Decisions a day | about 4,700 successful calls (29 Sep): gemma-4-26b 2,800, gemma-4-31b 800 (and about 2,000 server errors), Flash-Lite 3 x ~300-500, Groq about 40 per model |
| Prompt | about 4,200 input tokens, 72% of it fixed rules, verb list and instructions |
| Pace | about 5.5 world days an hour, about 2.4 decisions per person per world day |

What the live world teaches about the models (read before designing a
tech tree for them): they plan poorly over many steps (270 planned sowings
became 20), juggle loads endlessly, rarely act on long chains, and do what
the engine makes easy. Every step of a tech tree must therefore be
**short, useful on its own, and made easy by the engine**, or it will never
be climbed.

## 2. The binding constraint: decisions

Everything else is engineering; this is arithmetic. With `D` decisions a
day, `N` people and `d` decisions per person per world day:

    world days per real day = D / (N x d)

| People | d = 2.4 (today) | d = 1.5 (longer plans) | A world year (40 days) takes |
|---|---|---|---|
| 16 | 122 | 196 | 8 hours |
| 40 | 49 | 78 | 20 hours / 12 hours |
| 100 | 20 | 31 | 2 days / 1.3 days |
| 200 | 10 | 16 | 4 days / 2.5 days |

(D = 4,700.) So 100 people are affordable **today** if a world year every
day or two is acceptable to watch. Three levers make it better, and each is
a work item below:

- **Raise D.** gemma-4-31b failed more often than it answered (500/503);
  gemma is limited by tokens per minute (16,000 each), not requests, so
  **every token cut from the prompt is more decisions** (a 3,000-token
  prompt instead of 4,200 is 40% more gemma calls). Other free providers
  can be added through the existing OpenAI-style adapter (see section 8;
  Cerebras is no longer free, only a 30-day trial credit).
- **Lower d.** Long routines, process buildings that work while people do
  other things, fewer wake-ups.
- **Keep prompts flat as the world grows.** A bigger land with more people
  and more things in sight makes prompts grow unless perception is summarised.

## 3. Principles for the tech tree

1. **Resources live somewhere.** Clay by rivers, flint in chalk, copper in
   the hills, tin in one far place. Geography makes territory, trade and
   war matter; tin scarcity is what drove the real Bronze Age trade network.
2. **Deposits run out** (a vein is worked out; a clay bank is dug away), so
   control of places matters and people must move or trade.
3. **Processes run in buildings, over time**, like farms do now: put ore and
   charcoal into a furnace, and it smelts over hours while the owner does
   other things. This keeps decisions few (the budget) and makes capital:
   a furnace owner can hire miners and charcoal burners (w31) and sell
   metal at a posted trade (w32).
4. **Knowledge is discovered by working the materials**, and the world gives
   honest feedback on near misses ("the green stone blackened in the kiln,
   and a few beads of red metal lay in the ash"). It is not a blind search
   over hundreds of pairs, and not a list of answers. It is taught, and lost
   with the last who knew.
5. **Every step pays off on its own**: more food, more carried, more
   warmth, more strength, or more prestige. A step that only unlocks the
   next step will not be taken.
6. **Show only what a person knows, holds or sees.** Rules for smelting
   appear to someone who has seen ore or a furnace, not to everyone. This
   keeps prompts small and keeps discovery real.
7. **Content is data, not code.** Items, deposits, recipes, stations and
   techniques live in one table the engine reads, so a tier is added by
   writing rows plus tests, not by editing the engine.
8. **Bots climb the tree first.** A planner bot that follows the tree proves
   each tier is reachable and pays; a balance metric records the highest
   tier reached per run.

## 4. Phases

Each phase ends at a gate. Phases A and S run alongside the others.

### Phase A: foundations (3-4 sessions)

The engine work that everything else needs. No new era yet.

1. **Content as data** (`botciv/content/` or one TOML): items (weight, food,
   spoil, uses, worth), raw resources and where they are found, recipes
   (any number of inputs with quantities, optional station, optional
   technique, hours, outputs), stations, techniques. The 14 recipes and six
   buildings move into it unchanged (a test proves the old world loads and
   plays the same).
2. **General crafting**: `craft` with inputs, at a station if the recipe
   needs one; near-miss feedback; a failed try still costs only time.
   Keep today's two-item discovery as the simple case.
3. **Process buildings**: a station holds inputs and fuel, works over hours,
   and holds the output for its owner or those it is open to (store access
   rules, posted trades, and service all apply as they do now).
4. **Deposits in the land**: new terrain (hills) and finite deposits placed
   by the generator; gathering depletes them; remembered like bushes.
5. **Progressive rules text**: rules sections tagged by what they concern;
   the prompt carries the core plus only the sections the person has
   reason to know. Target: a prompt of 3,000-3,500 tokens today, and no
   growth per tier.
6. **Scale plumbing**: a spatial grid for sight and neighbour queries (today
   every hour compares every pair of people); logs rotated out of the
   `world` branch (monthly archives), and viewer data in chunks.
7. **Capacity**: find why gemma-4-31b returns 500/503 more often than
   answers (pacing, concurrency, prompt size); add one more free provider.

**Gate A**: the old world plays unchanged from data; prompt at 3,500
tokens or less; D at least 6,000 a day; the 100-bot land runs a year in
under 10 minutes.

### Phase B: the late Stone Age and the Neolithic (3-4 sessions)

| New | Where or how | Pays off by |
|---|---|---|
| clay | river and lake banks, finite banks | pots, bricks, moulds later |
| flint | some rock (chalk) tiles, finite | blades and axes better than stone |
| flax | wild on rich soil; can be sown | linen: warmth, rope, trade |
| wild goats or sheep | hills, in small flocks | tamed in a pen: milk daily, wool, meat on demand (a walking larder) |
| kiln (station) | clay + stone | fires pots (food keeps; carry water) and burns charcoal |
| loom (station) | wood + rope | cloth from flax or wool: clothes (cold), status, trade |
| quern (station) | stone | grain to flour faster (bread already exists) |
| pen (building) | wood | keeps tamed animals; they breed if fed |
| house (building) | clay bricks + wood | shelter and store in one; lasts; a household's seat |
| techniques | pottery, weaving, taming, charcoal burning | taught; lost with the last who knew |

This is the tier that should end the hunger that dominates today: tamed
flocks and kept food turn subsistence into surplus, and surplus is what
hiring, trade and rank run on.

**Gate B**: bots reach pottery and taming in most seeds, and starvation
falls; in the live world, at least one of pottery, weaving or taming is
worked out without help within a few real days of the tier going live.

### Phase C: copper (2-3 sessions)

| New | Where or how | Pays off by |
|---|---|---|
| copper ore (green stone) | a few hill deposits, finite | the first metal |
| charcoal | wood burned in a kiln | the only fuel hot enough to smelt |
| furnace (station) | clay + stone | ore + charcoal smelt to copper over hours |
| moulds | fired clay | cast tools: an axe, knife, sickle or awl, longer-lived than stone |
| copper ornaments | cast or hammered | prestige, gifts and money (worth much, weighs little) |
| techniques | smelting, casting | the first real specialists: smiths, known for it (skills already show) |

**Gate C**: bots smelt in most seeds; live people mine, burn charcoal and
smelt, and someone other than the smith owns something made of copper
(trade or service happened).

### Phase D: bronze (2-3 sessions)

| New | Where or how | Pays off by |
|---|---|---|
| tin ore | one far corner or a single stream, very finite | the reason for trade routes, and for wars over them |
| bronze | copper + tin in a furnace (alloying technique) | tools and weapons clearly better than copper |
| bronze weapons | cast | force: raids, defence, rule (a bronze-armed band beats an unarmed crowd) |
| wheel and cart | wood + bronze fittings | +carry: trade over distance |
| plough | bronze share, needs a tamed ox | doubles a farm's yield: large surplus, large estates, hired hands |
| draught animals | aurochs tamed in a pen | pull plough and cart |

What the Bronze Age should look like when it works (none of it scripted):
tin controlled by a few, carried by traders, paid for in grain and tokens;
smiths in service to chiefs; ploughed estates worked by hired hands;
bronze-armed groups taking and holding.

**Gate D**: bots reach bronze in some seeds within a few years; in the live
world bronze is made at least once, with tin that crossed the land by trade
or force.

### Track S: more people (alongside A-D)

| Step | People | Land | Needs first |
|---|---|---|---|
| S1 | 24-30 | 32 x 32 | spatial grid; prompt summaries of far people ("and 5 others to the east") |
| S2 | 40-50 | 40 x 40 | Gate A (smaller prompts, more capacity) |
| S3 | 70-100 | 56 x 56 or 64 x 64 | D and d measured to give at least 20 world days a day |
| S4 | 150+ | 64 x 64 or more | more providers; only if the owner accepts a slower world |

Each step is a new, larger land. **The current world cannot grow into these
sizes** (the land is fixed at generation), so a bigger world is a new world.
Recommendation: keep the current world running through Phase A, then start
**World 2** on the new map (hills, deposits, rivers) with 30 people when
Phase B content is in, and grow its population by arrivals as capacity
allows.

Engineering per step: people listed near to far with the far ones summed
up; the events list capped by importance; groups and markets summarised;
viewer and replay tested at the new size; the engine at 100+ people
profiled (the bot land already runs 100 bots).

## 5. Order of work

| Session | Work | Gate |
|---|---|---|
| 1 | Content as data (move the 14 recipes and buildings), tests that the old world plays the same | - |
| 2 | General crafting, near-miss feedback, process buildings | - |
| 3 | Progressive rules text; prompt target; gemma-31b errors | prompt at 3,500 tokens or less |
| 4 | Deposits, hills, spatial grid, logs out of git | Gate A |
| 5-6 | Neolithic content, bots that climb it | - |
| 7 | World 2: new map, 30 people; S1 | Gate B (bots) |
| 8-9 | Copper, then measure live discovery | Gate C |
| 10-11 | Bronze, carts, plough; S2 | Gate D (bots) |
| 12+ | S3 when capacity allows; tune by what the dead teach | - |

Each session still runs the loop in `docs/process.md` (read the world, bot
runs before and after, tests, ship, confirm the handover). Content is
added one tier at a time, and a tier goes live only once bots prove it
reachable and it pays.

## 6. Risks

- **The models may never climb.** They barely farm today. Mitigations:
  every step pays on its own, stations do the multi-step work, near-miss
  feedback, teaching, and people's own ideas credited when made real. If a
  tier sits undiscovered for days of live play, tune discovery (more
  feedback, a higher chance), never script it.
- **Prompt growth eats the budget.** Mitigation: progressive rules, and a
  token check on every change (`docs/process.md` section 6).
- **Free capacity can change** (models retired, limits lowered: GitHub
  Models went on 2026-07-30). Mitigation: several providers, and the world
  waits rather than failing.
- **A bigger world is harder to watch.** Mitigation: the viewer follows
  groups and places, not only people; the chronicle summarises regions.
- **Balance breaks per tier** (a flock may end hunger entirely, or bronze
  weapons may make raiding the only life). Mitigation: bots before live,
  and tier rows are data, so they are cheap to tune.

## 7. Decisions (owner, 2026-09-30)

1. **World 2**: left to Claude. Decided: start a new, larger world when the
   Neolithic content is ready; keep the current world until then.
2. **Pace**: a world year every one to two real days is **too slow**.
   Target: at least one world year (40 days) a real day at 100 people,
   which needs about 6,000 decisions a day at 1.5 decisions per person per
   world day (or 9,600 at today's 2.4).
3. **More free capacity**: see section 8.

## 8. Free capacity, best first (checked 2026-09-30)

1. **Inside the project, no new accounts** (Phase A): prompts from 4,200
   to about 3,000 tokens (gemma is limited by tokens per minute: about +40%
   gemma calls); gemma-4-31b's errors (on 29 Sep 801 answers and 1,985
   errors, mostly 500/503: pacing and retries, to be found); fewer
   decisions per person per world day (2.4 to about 1.5: longer routines,
   process buildings, fewer wake-ups). Together roughly 2 to 3 times the
   people per real day.
2. **Kaggle notebooks with a GPU** (the owner already has an account and a
   `kaggleapi` secret): about 30 GPU hours a week. Run the whole world
   inside a notebook with an open model served locally (the gemma family
   the world already uses), then push the state to the `world` branch with
   a token kept in Kaggle's secrets; `world.yml` starts the notebook through
   the Kaggle API. No per-minute limits during those hours, and the shared
   rules prefix can be cached. Throughput to be measured with one trial
   before building on it.
3. **Mistral's free tier** (one account; requires opting in to data being
   used for training; limits shown only in its console, reported around 2
   requests a minute, i.e. up to about 2,900 decisions a day). Another
   adapter entry like Groq.
4. **Small extras**: more Groq models (bounded by about 6,000 tokens a
   minute each), OpenRouter free models (50 requests a day without a
   purchase: negligible), Cloudflare Workers AI (a small daily allowance).

Not to do: several Google projects or accounts to multiply the free
quota (against the spirit of the terms, and it risks the key the world
depends on); heavy model inference on GitHub Actions runners (GitHub's
terms forbid use unrelated to the software project and disproportionate
burden, and losing Actions would stop the world).

## 9. Decisions still open

- Which accounts to add (Kaggle token for pushing state; Mistral).

