# botciv — plan

**Draft 4, 2026-09-28. Building.** Draft 3 was the design brief; this
draft records what was built and what changed. The owner's brief: a
completely open-ended sandbox; the people do not know they are
simulated; the plan is a guideline, not a contract.

## 1. What it is

A persistent world on a 24×24 grid. A dozen or more people live in it,
and there is not enough food for all of them. A language model decides
what each person does, says, notes down and believes. The engine decides
what actually happens. Nothing social is scripted: groups, deals, feuds,
chiefs, laws and betrayals exist only if the people build them out of a
small set of verbs.

The world advances several times a day on GitHub Actions within the
free-tier quota, and the owner reads it on a phone.

## 2. Principles (unchanged in substance)

1. **The engine owns the world; the model only chooses.**
2. **Few verbs, many combinations.** About 30, each working on anything
   it sensibly applies to.
3. **Record everything, enforce almost nothing social.** Promises,
   deals, gifts, thefts and attacks are recorded exactly in each
   person's ledger. Only store, shelter and wall access is enforced.
4. **Partial information.** Sight radius (shorter at night), no view of
   inventories or others' thoughts; theft can go unnoticed; lies are free.
5. **Many roads to power:** strength, stores, farms, knowledge of
   recipes, followers, information.
6. **The rules text is a variable.** It states every outcome evenly
   (probes showed wording moves behaviour a lot) and is versioned
   (`RULES_VERSION` in `prompt.py`, logged with every decision).
7. **The world never ends on its own.** Births, strangers arriving,
   seasons and shocks.
8. **New: the people do not know.** Prompts are written from inside the
   world: hours and days, not ticks; "things you can do", not actions.

## 3. The world as built

- **Time:** an hour per step, 12 hours a day (the last 3 night), 10-day
  seasons, 40-day years. Winter: no berry regrowth, farms stall, cold
  nights hurt anyone without shelter, fire or a cloak.
- **Food:** berry bushes (regrow slowly, weaken when picked bare, spread
  in spring and summer), deer herds (one hunter almost never succeeds,
  two usually do; herds regrow and new ones wander in), fish by water,
  farms on rich soil (seeds, 4 days to grow, 6 grain per seed). Carried
  food spoils; stores slow it.
- **Materials and making:** wood, stone, fibre, hide, bone. A hidden,
  seed-generated recipe table of 14 things (tools, clothing, cooking,
  bread, a necklace and a drum that do nothing useful). Recipes are
  learned by trying pairs or being taught, and are lost when the last
  person who knows dies untaught.
- **Buildings:** store, shelter, wall, farm, fire. Others can help
  build. Owners set access. Buildings can be broken.
- **Life:** ageing (3–5.5 years), children (both parents well fed, both
  agree, a teaching from each), strangers from the edge, inheritance.
- **Shocks:** drought, storms, blight.

## 4. Minds

Each person is asked alone; nothing another person knows enters their
prompt. The prompt holds: the world as they know it, the things they can
do, their body, belongings and knowledge, a local map and lists of what
they see, what happened since they last decided, offers and promises,
their own notes (rewritten each time, 600 characters), their opinions of
others, and the engine's record of what really passed between them.

They reply with a private thought, optional speech (free, alongside
acting), one action, an optional plan of up to 8 steps, rewritten notes
and changed opinions.

They are asked again only when something happens to them: their plan
ends or breaks, they are attacked, robbed, spoken to, given something,
offered a deal, a vote is called, a stranger appears, they grow hungry
or hurt, or a day passes quietly. A hungry person carrying food eats it
without being asked, soonest-spoiling first (rules w7); only hunger with
nothing to eat needs a decision.

Thinking takes time. Each hour the world waits up to 10 seconds for
answers; someone whose answer is slower carries on with what they were
doing and acts when it comes, never more than 3 hours late. What they
heard and saw meanwhile is kept for their next decision.

## 5. Budget (measured)

The key is on the free tier. From AI Studio's rate-limit page:

| Model | RPM | RPD |
|---|---|---|
| Gemini 3.5 Flash-Lite | 15 | 500 |
| Gemini 3.1 Flash-Lite | 15 | 500 |
| Gemini 3.5–3.8 Flash (each) | 5 | 20 |
| Gemma 4 31B | 30 (16K TPM) | 14,400 |

So about **1,000 decisions a day** from the two Flash-Lite models, which
also make two kinds of mind (half the people use each). At 15 a minute
each, a day's allowance takes about 35 minutes to spend, so **the
per-minute cap is the one that bites**; the gateway paces each model to
it rather than treating a 429 as a failure. Gemma's 16K tokens a minute
is about 7 calls with a 2,200-token prompt, and it timed out on every
live probe; if it becomes reliable it is the way to run a bigger world
for free. The gateway counts calls per model
per Pacific day, backs off on per-minute limits, stops a model on its
daily limit, and saves what it learns in `quota.json`. When the quota is
spent the world pauses; rule-based bots stand in only for a person whose
calls keep failing, and the log marks it.

Measured on the first live days (14 people, 406 decisions): 3.7 decisions
per world hour, prompts of about 2,450 tokens, replies of about 250, 2 s
per call. About a third of decisions answered a failed choice or a plan
that stopped, and a fifth answered hunger; w7 removes the commonest of
both (take with no item, hunger with food in hand) and asks for longer
plans.

**Blitz and backlog.** The world does not need to run at watching speed.
It runs as fast as the quota allows, and the viewer plays the backlog at
a human pace (Story speed: about 50 seconds a world day).

**Every allowance, all the time.** The limits are of two kinds, and they
reward different habits. Flash-Lite's is 500 calls a day per model: it
keeps until the Pacific midnight, so it only has to be spent sometime
that day. Gemma's is tokens a minute (16K, about 6 calls at 2,450
tokens): a minute that passes unused is gone. So:

- Each call goes to the model that can take it soonest: a person's own
  Flash-Lite model if it has room now, otherwise whichever does. Gemma
  works every minute; Flash-Lite still gets spent within the day.
- Each run lists the models the key can reach and adds every Gemma of 4B
  or more and every plain Gemini text model, each with its own allowance.
  A model that is not found, or rejects three requests in a row, is
  dropped for that run; one with no free allowance is refused on its
  first call and skipped for the day. Of two models with room, the one
  that has been answering faster is asked.
- Probe, 2026-09-28: `gemma-4-26b-a4b-it` answers in 5–6 s and
  `gemma-4-31b-it` in 33–43 s, both with valid replies; the key also
  reaches Gemini 2.5 Flash, Flash-Lite and Pro, 3 Flash, 3.1 Flash-Lite
  and Pro previews, and 3.5–3.8 Flash.
- The gateway paces by the prompt tokens the API reports and learns
  request and token limits from any 429; a refused call's tokens are
  given back to the minute.
- The world runs around the clock (section 6).

Which model answered is logged with every decision, so the minds can
still be compared. Gemma's reliability is the open question (it failed
12 of 20 on 2026-09-27).

## 6. Running it

- `world.yml`: one run advances the world for about 5.5 hours in
  half-hour pieces (`tools/advance.py`), committing state and logs to the
  `world` branch after each, writing the chronicle and asking Pages to
  publish. Each run starts the next as it ends; GitHub's schedule proved
  unreliable, so it is only a backstop. A run ends after its current piece
  when newer code reaches main, so a new version takes over within the
  hour. When every model is spent or a local runner holds the lock it
  waits rather than ends. Full prompts are uploaded as a run artifact
  (kept 30 days) for studying and replaying decisions.
- `pages.yml`: publishes the viewer and `ideas.md` from `world`.
- `tools/run_local.py` advances the world from any machine and holds a
  lock the Actions runs respect.
- `dev.yml`: `[probe]` or `[world]` in a commit message on a `claude/*`
  branch.
- Logs: gzipped JSONL events (with per-hour position frames) and
  decisions per run. Full prompts are kept only as Actions artifacts.

## 6a. Where the world goes next: ideas from the people

The owner's brief is open: not a survival game, though surviving comes
first; a world where some thrive, gather wealth and power and others
barely get by, grown in versions. What to add next is decided largely by
the people themselves:

- **They say what they want.** Every decision may carry an optional
  `idea`: something they want to do, make or have that no one knows how to
  do yet (rules w8). It is worded as their own invention, never as a
  request to anyone outside. They remember their last few ideas and can
  talk about them. Ideas are logged as events and shown in the viewer.
- **Two quieter signals.** `do` deeds change nothing by themselves, so a
  deed acted out often marks something the world cannot yet do; and the
  choices the engine refuses (above all unknown verbs) show what people
  tried.
- **Each iteration** reads `tools/ideas.py` (published hourly as
  `ideas.md` on the site), picks what is most wanted and fits the rules,
  and makes it real in the next rules version. An idea made real is first
  worked out by whoever first imagined it, if they are alive.
- **Wealth and power are measured, never shown to the people.** Once a day
  the engine logs a census: each person's worth (food, materials and made
  things carried or stored, buildings owned) and how many they lead. The
  viewer ranks people, shows what share the richest fifth hold, and
  charts inequality (Gini) by day.

### Versions

- **w8** (2026-09-28 07:50): ideas, the census. By day 122, year 4:
  27 people had lived and 5 were alive, 20 of the dead starved (12 in
  winter), no one was born, no farm was ever built. Inequality (Gini)
  swung 0.2–0.5. 34 ideas: most wanted was keeping food through winter
  (smoking fish, preserving berries), then tools already in the hidden
  recipes, then family ("propose to Toth and start a family"), and wealth
  ("to be the richest person in the land"). Refused choices: putting
  into a store not beside you (83), naming a place instead of
  coordinates (42), taking from a pile a few steps off (50).
- **w9**: made real: smoking and drying at a fire (credited to Breszai,
  the earliest living imaginer), and pledging as partners for life
  (partners share stores and shelters and inherit from each other).
  Techniques are knowledge like recipes: known, taught, worked out by
  trying, picked up by watching. Seeds now also come from berries, and a
  farm takes 8 seeds (48 grain that keeps): a road to surplus. People
  walk to the store, pile or named place they mean. Models the service
  is struggling with rest longer each failure in a row.
- **w10**, from thinking w9 through: food rotted but silently, so no one
  could see why smoking mattered. Measured with bots over a year, a fifth
  to two fifths of all food gathered rots (15–45 food worth a day against
  60–75 eaten). Now people hear each dawn what they carried went bad, and
  the next person at a store hears what rotted in it; the census logs rot
  and the viewer shows it. Working out smoking by trying was so easy (15%
  an hour) that knowing it was worth nothing; now 5%, so teaching, and
  refusing to teach, matter. With 4 people left there was no society to
  be unequal in: strangers now come up to four times as often to an
  emptied land (bots over two years: 7–19 people instead of down to 4).
- **w11**, from bot balance runs (`docs/balance.md`): building a farm was
  impossible (the word "farm" was read as grain), which is why no one ever
  farmed. Fixed, and grain kept back can be sown again, so a harvest can
  grow into a surplus. With mixed bots (careless, tit-for-tat, planner,
  raider) over 10 seeds × 6 years: never extinct, starvation 43% of
  deaths, planners worth about 2.5 times foragers, Gini 0.47, raiders
  second-richest. Outcomes now depend on behaviour.
- **w12**, from bot rounds with trade, credit, households and teaching,
  and a 100-person land: sowing uses the free farm beside you (your own
  first), building with no place named uses the first fitting tile beside
  you, and a walk with no way through goes as near as it can. Larger lands
  get rivers (and rich soil) and wolf packs in proportion, and strangers in
  proportion to the edge. 100 bots on 64×64 hold 55–93 people over four
  years; in a crowd, theft pays best for bots. `configs/large.toml`;
  `/botciv/large/` on the site.
- **w13**, what keeps wrongdoing in check, made possible rather than
  scripted: witnesses of theft and attacks remember who did it (and see it
  when they meet them), and people standing together take from someone
  openly by force, which seldom fails unless that person has their own
  people beside them. Retaliation, restitution, fines and group enforcement
  can now emerge, and so can robbing the friendless. With bots that use
  them, thefts fell from about 180 to 49 a run and raiders went from second
  richest to poorest.

## 7. Seeing what emerged

- **Chronicle:** one call per finished day turns its events into a short
  history. Every sentence cites event ids; a checker drops sentences
  that cite unknown events or name people absent from them.
- **Viewer:** story feed, replayable map, each person's notes, opinions,
  decisions and ledger, groups. The replay covers the whole history,
  loaded ten days at a time; it remembers where you stopped on that
  device, and its Story speed lingers on speech and events and hurries
  through quiet hours.
- Next: detectors (alliance, betrayal, feud, market, chief, law, lost
  knowledge, culture) and a variety count.

## 8. Next

1. First live runs; read decisions; fix prompt and rule problems.
2. Detectors and the variety count.
3. The open door: `attempt`, a free-form action a referee maps onto a
   fixed effect library (draft 3, section 7).
4. Owner as a voice from the sky, or as a person.
5. Gemma or another model as a third kind of mind.
