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

### Added after the first live days (rules w6)

- **One world.** The land is everything there is; nothing lies past its
  edges. Newcomers are loners who lived apart in its wilds.
- **Skills** (gathering, fishing, hunting, building, fighting, making)
  grow with practice, improve results, and show to others as
  reputations, so specialists and trade have a reason to exist.
- **Stories** are told, remembered by everyone within earshot and retold
  with their first teller kept; children carry their parents' teachings
  as stories. Culture shows when a story outlives its teller.
- **Monuments** with an inscription, **graves** with words for the dead,
  and **named places** outlast the people who made them.
- **Remembered places:** people recall bushes with fruit, buildings,
  graves and named places they have seen.
- **Wolves** hunt deer first and, with none near, people who are alone,
  boldest at night and in winter; fire and company keep them off, and
  they can be fought.

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
or hurt, or a day passes quietly.

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

Bots-only runs use about 4 decisions per world hour, so the world moves
roughly three weeks per real day.

## 6. Running it

- `world.yml`: every 3 hours, up to 150 calls and 40 minutes per run;
  commits state and logs to the `world` branch; writes the chronicle;
  publishes the viewer to GitHub Pages.
- `dev.yml`: `[probe]` or `[world]` in a commit message on a `claude/*`
  branch.
- Logs: gzipped JSONL events (with per-hour position frames) and
  decisions per run. Full prompts are kept only as Actions artifacts.

## 7. Seeing what emerged

- **Chronicle:** one call per finished day turns its events into a short
  history. Every sentence cites event ids; a checker drops sentences
  that cite unknown events or name people absent from them.
- **Viewer:** story feed, replayable map, each person's notes, opinions,
  decisions and ledger, groups.
- Next: detectors (alliance, betrayal, feud, market, chief, law, lost
  knowledge, culture) and a variety count.

## 8. Next

1. First live runs; read decisions; fix prompt and rule problems.
2. Detectors and the variety count.
3. The open door: `attempt`, a free-form action a referee maps onto a
   fixed effect library (draft 3, section 7).
4. Owner as a voice from the sky, or as a person.
5. Gemma or another model as a third kind of mind.
