# Toward civilization: the known tree, and a roadmap past bronze

Status: **plan, 2026-09-30**, drafted after w39. It replaces the tech sections (3-4) of
[roadmap.md](roadmap.md). Phases B-D of that roadmap shipped in w39 as a first cut, and this plan
reworks them. Nothing here is built yet.

The owner decided (2026-09-30):

- **Drop the discovery system.** The whole tree is known to everyone. Knowing how is personal:
  it is learned by practice or taught.
- **Expand the tree massively**, with the big picture in view.

## 1. Why the discovery system goes

What the live world did with it, over 436 days and about 11,700 decisions:

- **Almost no crafting.** People chose `craft` 52 times and made 10 discoveries: rope, basket,
  spear, snare, axe and cooked meat.
- **A wish that never came true.** Tolgair wished for a bone needle five times and never found one.
- **Nothing to reason with.** The recipe table is a hidden, random set of pairs, so a language
  model can only guess, and every miss costs a decision. Decisions are the budget.
- **Real discovery isn't possible anyway.** The models already know that fired clay makes pots,
  so "discovering" pottery is theatre. The w39 near-miss texts had to hint at the answer, or no
  one would ever find it.

What is worth keeping is that knowledge is held by some people and not others. That gives
teachers, specialists (the only smith for days around), apprentices, hiring, trade in made
things, and crafts lost when the last person who knew them dies. The known tree keeps all of
that and drops only the guessing.

## 2. The known tree (rules w40)

### Concepts

- **Craft.** A technique such as pottery, weaving, smelting or forging. Each craft has:
  - an era;
  - a workshop, or none if it is done by hand;
  - prerequisites: other crafts at some skill;
  - the recipes it makes.
- **Skill.** Each person has a skill from 0 to 1 in each craft. It is stored with the existing
  skills and shown in words:
  - "untried" at 0;
  - "a beginner" below 0.3;
  - "able" from 0.3 to 0.7;
  - "a master" from 0.7 up.

  Others see who is a master of what, just as skills show today.
- **Everything is visible.** Everyone knows what exists and what it takes.

### Making things

1. **Anyone can try.** `craft item` works for anyone who has the materials and tools, stands at
   the workshop (or is doing it by hand), and meets the prerequisites.
2. **Chance of success** is 0.25 + 0.75 × skill, so a beginner mostly fails and a master rarely
   does.
3. **Failure** costs the hours, and part of the inputs is spoiled: half, rounded down, and never
   the tools. The person is told why ("the pot cracked in the firing"). The skill rises by 0.08.
4. **Success** raises the skill by 0.04 × (1 − skill), so it keeps rising slowly.
5. **Watching** a success from beside the worker adds 0.03.
6. **Being taught** takes a few hours side by side. It brings the learner up to
   min(0.5, teacher's skill − 0.2). The teacher must be at least able. Nobody learns mastery from
   teaching alone; mastery comes from practice.
7. **Prerequisites** are stated plainly, e.g. "alloying needs smelting 0.3". The tree's shape
   comes from prerequisites and materials, not from hidden answers.
8. **Knowledge dies with its holders.** If every master of a craft dies, it becomes hard again:
   anyone can still try, but they start from nothing.

### What each person sees

A tree of more than 200 recipes cannot go into every prompt, so each person sees only what
matters to them.

- **In the rules, one line per era**, naming the crafts and what they need in a few words, for
  example: "Bronze: smelting (green stone + charcoal in a furnace → copper), alloying (copper and
  tin → bronze), casting (metal into moulds)…". This is about 60-120 tokens an era. Only eras up
  to one past the most advanced craft anyone alive has practised are shown; later eras appear as
  one line naming what lies ahead.
- **"Your crafts":**
  - every craft this person has any skill in, with its full recipes and their skill word;
  - crafts "within reach": prerequisites met, and a workshop or material in sight or held;
  - at most about 12 craft lines.
- **"Who knows what":** the people this person has seen at work, e.g. "Tis is a master potter".
  Most of this already exists as skills shown to others; it becomes an index of teachers and
  suppliers.

**Budget:** the 95th-percentile prompt must stay at or under 3,500 tokens, enforced by a test on
generated worlds at every era.

### Verbs

- `craft item [qty]` makes, or tries to make, anything visible. The old pair form (item plus
  item2) is removed.
- `work` (w39) is removed: practice is learning, so it adds nothing. That is one fewer verb.
- `teach target item|craft` teaches a craft.

### Migration

- The world's random pair table is retired. The 18 pair products become ordinary recipes under
  era 0 crafts:
  - cordage: rope, net, snare, basket;
  - woodworking: spear, stone axe, drum;
  - leatherwork: cloak, tunic, shoes, hat;
  - cooking: cooked meat, flour, bread;
  - herb lore: poultice;
  - ornament: necklace, bracelet.
- A person who knew a pair starts at skill 0.5 in its craft. Each w39 technique a person knows
  becomes skill 0.6.
- Everyone starts era 0 crafts at a random 0.1-0.4: everyone can try, and nobody is sure to
  succeed.

## 3. Are we ready for a massive tree? Not yet: what blocks it

Items are mostly data already. The item names that are hard-coded appear only a few times each,
and w39's `tech.py` shows content can be data. The blockers are elsewhere:

| Blocker | Now | Why it blocks a big tree |
|---|---|---|
| **Buildings are code** | about 120 checks on building kinds, e.g. `store` 44 references and `farm` 39 | Houses, granaries, pens, workshops, forts and temples each touch dozens of places. |
| **Every craft hour is a person's hour** | You stand at the kiln for the whole firing | Long chains (bronze is about 40 steps) eat the decision budget, and no work runs unattended. |
| **The prompt cannot list the tree** | The rules are about 1,200 tokens and the verb help about 1,000 | 200+ recipes need the per-person view in §2. |
| **Bots are hand-written ladders** | w39's `climb()` is written step by step | Every new tier would need new bot code before it could be tested. |
| **The viewer draws each thing by hand** | One hand-written function each | 25+ buildings and 150+ items would need a generic sprite system. |
| **Small populations** | The live world has 8 people | Specialisation needs 30 or more; the Kaggle world is where the tree can live. |
| **Capacity** | Live about 6 world days an hour; Kaggle to be measured by the sweep | A civilisation takes years of world time, so decisions must be spent on choices, not on steps. |

So the answer is **yes, after one or two sessions of foundations (§4, F)**. After that, content
is rows in data files plus tests, a session per era, and each era is tried by bots first.

## 4. The roadmap

### F. Foundations (w40-w41), required before the big expansion

1. **w40, the known tree (§2).** Crafts, skill, prerequisites, visibility and teaching. The pair
   table is retired and the world migrated. Content moves into a `botciv/content/` package, with
   one module per era plus schema checks.
2. **Buildings as data, with roles.** A building is a list of roles, and the engine checks roles,
   never kinds. Roles:
   - `shelter` (warmth, rest)
   - `store` (capacity, spoil factor)
   - `workshop` (which crafts run there)
   - `farm` (what grows)
   - `pen` (animals)
   - `wall` (blocks, has hp)
   - `hearth` (fuel)
   - `monument` (text)
   - `grave`

   A house is `shelter + store`. The roughly 120 kind checks become role checks. The live world
   loads unchanged.
3. **Processes.** Some recipes are batches that run unattended in a workshop:
   - "load the kiln" is one decision; the firing takes 8 hours while the owner does other things;
   - the output waits in the workshop for anyone allowed to take it.

   This saves decisions and creates capital: one owner, many hired hands. Smelting, firing,
   tanning, brewing and charcoal work this way; knapping and sewing stay by hand.
4. **Effects as hooks.** Items name the effect they have, and the engine knows a fixed set of
   hooks: `tool:<use>` (wood, fibre, grain, stone, fish, hunt, butcher, dig), `weapon`, `armour`,
   `warmth`, `carry`, `keep` (slows spoiling), `heal`, `light`, `move` (faster walking, a cart's
   load), `float` (crossing water), `fuel`, `record` (writing). New content chooses hooks; only a
   new hook needs engine code.
5. **Terrain and deposits.** Hills (where ore lies, slower to cross), marsh (reeds, bog iron),
   sand (glass) and shore. The live world gains them by a migration that converts land at rock
   edges and by the water.
6. **A generic planning bot.** Given a goal item, it expands the recipe tree down to what it has,
   what it sees and what it remembers; it gathers, builds, crafts and practises in order, and asks
   masters to teach it. Every new tier becomes testable with no new bot code. Balance adds:
   - the highest era reached;
   - days to each craft;
   - specialists (sole masters);
   - teachings;
   - made things traded.
7. **The viewer.** Sprites from data (a shape, a colour and an emblem for each building and item
   family), and a "Knowledge" panel: the tree coloured by who knows what, masters named, crafts
   lost.
8. **The prompt budget test** (§2) runs in CI.

**Gate F:**
- the live world plays on under roles and hooks with no loss;
- a prompt at the 95th percentile is at most 3,500 tokens;
- the generic bot reaches bronze in at least 4 of 6 seeds within 6 years;
- the w39 content runs through the new schema unchanged.

### Eras of content (one or two sessions each, bots first)

Each era lists its crafts and what they pay. Every step pays on its own.

**E1. Neolithic, completed (w42).** Food secure, animals kept, houses, the first boats.
- Herding: pens, with goats, sheep and cattle tamed from wild flocks. They give milk every day,
  wool, meat on demand (a living larder) and manure (farm yield).
- Dairying: cheese keeps.
- Brewing: beer from grain in a jar, a process.
- Baking: an oven, where bread is made more efficiently.
- The quern: flour.
- Wattle-and-daub and mud-brick houses (shelter + store), and granaries (a large store that keeps
  well).
- Tanning (a process) makes leather, which lasts longer than hide.
- Dyeing, from plants: coloured cloth is prestige.
- Archery: a bow and arrows hunt at range, and alone.
- The dugout canoe: fish from open water and cross rivers.
- Wells: water where there is none.

**E2. Bronze Age, completed (w43).** Surplus, transport, records, force.
- The potter's wheel: pots faster.
- The wheel and cart: a large load, with roads to come.
- The plough with oxen: farm yield ×2, which means estates and hired hands.
- Bellows: better smelting.
- Bronze arms and armour (the `armour` hook).
- Scales and ingots: a standard of value, the first money.
- **Writing on clay tablets:**
  - a written deal is kept by the engine and can be read by anyone who holds the tablet;
  - a written law can be posted;
  - a ledger is kept at a store.
- Fortified walls and gates.
- The temple (a monument where people gather; the meaning is theirs).
- The sailing boat.

**E3. Iron Age (w44-45).** Stronger tools for everyone.
- Bog iron and hill ore are common; bronze's tin was scarce.
- The bloomery (hotter; skill-heavy), then the smithy and forging (a process at an anvil), then
  steel by quenching.
- Iron tools, weapons, ploughshare and nails.
- The lime kiln makes mortar, which allows stone masonry: stone houses, halls and towers.
- Glass from sand and ash: beads and vessels.
- **Coinage:** a mint turns metal into coin, and coin is the medium the trade and deal systems
  understand.
- The water mill: flour without labour.
- Roads: built tiles that make walking faster.

**E4. Classical institutions (w46-48).** The civilization layer.
- **Literacy:** reading and writing, taught like any craft. Written signs, letters carried
  person to person, contracts.
- **Books:** a written craft lets a reader learn it up to 0.3 without a teacher, so knowledge
  outlives its masters. Libraries follow.
- **Schools:** one teacher, many learners.
- **Markets:** a marketplace building gathers the posted trades of every stall in it.
- **Treasuries and taxes:** a group store with dues its rules set; engine support for group
  property.
- **Astronomy and the calendar:** knowing when spring comes, so sowing is well timed.
- **Medicine:** herbs, setting bones, less death from sickness.
- **Engineering:** aqueducts, bridges and ships that cross the sea. New land is a possible later
  map feature.
- **Luxury crafts:** jewellery, fine cloth, glassware, and instruments.

**E5 and beyond, left open.** For example: horses and riding (fast travel, herding at range),
stirrups, windmills, paper, printing, the compass. The content system should make these rows
plus a hook or two; whether to go there is for later.

**Scale:** about 45-60 crafts, 180-250 recipes, 150-200 items and 25-30 buildings by E4. The
rules grow by about 100 tokens an era, and each person sees perhaps 10-15 craft lines.

## 5. The worlds

- **World 1**, the live world on the API with 8 people, gets every version by migration. It is
  the small-group testbed; it cannot specialise far.
- **World 2**, on the Kaggle GPU, larger, is where civilisation can happen. The sweep settles its
  size. It should begin with w39 now, so its history starts, and take F and each era by migration
  like world 1. Its founding people get only era 0 skills.
- **Later, a world 3**, bigger (100 or more) and started fresh on the finished era map, once
  capacity allows it (a second Kaggle account is not allowed; faster models or more free
  providers are the way).

## 6. Measuring success (for each era, in bots and then live)

- **Reach:** the highest era practised, and days to each first craft.
- **Specialisation:**
  - the number of crafts with one to three masters;
  - the share of made things owned by someone other than their maker, which shows trade or
    service happened.
- **Knowledge flow:** teachings a day; crafts lost and regained.
- **Civilisation:**
  - settlements, meaning clusters of houses;
  - groups with rules and treasuries;
  - written deals and laws;
  - trade volume.
- **Cost:**
  - tokens per decision at the 95th percentile;
  - decisions per person-day, which should fall as processes and routines carry the work.

## 7. Risks

- **Prompt bloat:** handled by the per-person view and the CI budget. If it bites, era lines
  collapse further.
- **The decision budget:** long chains on too few decisions. Processes, routines and hiring are
  the answer, and gates measure days to each tier.
- **Abundance kills drama:** each era should create new scarcities (tin, iron skill, land for
  ploughs, labour) that invite trade, hiring and conflict, not only comfort.
- **Model confusion with 200 names:** real historical names (which the models know), aliases,
  and refusals that name the right item.
- **Balance drift:** bots first, before and after every era, as now.
- **Content errors:** schema checks (every input obtainable, every workshop buildable, every era
  reachable) as tests.

## 8. Order of work and effort

| Session | Rules | What | Gate |
|---|---|---|---|
| 1 | w40 | The known tree, skill, teaching, migration, content package | tests, bots, live check |
| 2 | w41 | Building roles, processes, hooks, terrain, the generic bot, prompt budget test | Gate F |
| 3 | - | Viewer: sprites from data, Knowledge panel | phone check |
| 4 | w42 | E1 Neolithic completed | bots reach herding and houses |
| 5 | w43 | E2 Bronze completed | bots reach bronze in 4 of 6 seeds |
| 6-7 | w44-45 | E3 Iron | bots reach iron |
| 8-10 | w46-48 | E4 Classical institutions | books, markets and treasuries used by bots, then people |

After each session: balance before and after, the live worlds hand over, and results go in
`balance.md` and `process.md`.

## 9. Decisions for the owner

1. **How far:** plan to E4 (classical institutions) and design so it can go on (recommended), or
   stop at iron?
2. **Books that preserve knowledge (E4):** they soften "lost with the last who knew".
   Recommended: yes, but only up to beginner level, so masters still matter.
3. **World 2's start:** now on w39, taking the rest by migration (recommended), or wait until
   after F so it starts on the new map features.
4. **Failure costs:** spoiling half the inputs on a failed try makes practice costly, which gives
   masters value. Or is that too harsh for the people?
