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
  or more, each with its own allowance. A model that is not found, or
  rejects three requests in a row, is dropped for that run.
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
  `world` branch after each and writing the chronicle. The hourly
  schedule is a watchdog: while a run is going one waits queued behind it,
  so the next starts the moment the last ends. Full prompts are uploaded
  as a run artifact (kept 30 days) for studying and replaying decisions.
  It stops early when every model is spent, when a local runner holds the
  lock, or when someone else pushes to `world`.
- `pages.yml`: publishes the viewer from `world` every hour.
- `tools/run_local.py` advances the world from any machine and holds a
  lock the Actions runs respect.
- `dev.yml`: `[probe]` or `[world]` in a commit message on a `claude/*`
  branch.
- Logs: gzipped JSONL events (with per-hour position frames) and
  decisions per run. Full prompts are kept only as Actions artifacts.

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
