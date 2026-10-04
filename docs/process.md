# How botciv is grown: the working handbook

Read this first in every new session, after `CLAUDE.md`. It is the whole
process: what the owner wants, where work comes from, how to test cheaply,
how to ship, and how to keep the living world running. `PLAN.md` is the
design and version history; `docs/mechanics.md` maps what the world can and
cannot yet do; `docs/balance.md` records the bot measurements.

## 0. Modes: how much Claude to spend

The owner sets a mode by saying "mode 1" to "mode 4". The world itself costs
no Claude tokens (the world advances on its own: `world2.yml` every hour, on Kaggle's GPU
while its weekly hours last and on the free Gemini and Groq tiers otherwise). Claude's tokens go to long sessions (every wake re-reads the
whole conversation), to watching (monitors, check-ins that find nothing),
and to iterating. So in every mode: Actions keeps the world alive; scheduled
Claude work runs in **fresh, short sessions** started by a routine
(`create_trigger` with `create_new_session_on_fire`), never by waking one
long session; no Monitor tails on the world.

**Current mode: 3** (set 2026-10-04, the owner: "make big aggressive changes; you have a ton of new data"): driven from the owner's session, iteration after iteration; no mode routine (the mode-2 routine "botciv mode 2 pass" is disabled: routine sessions here cannot attach the repository, so they cannot push). The world runs as before: world2 hourly on Kaggle while its GPU hours last, on the free Gemini/Groq tiers otherwise; the bot farm (`bots.yml`) and the long land (`botworld.yml`) run without end. World 1 and world3 are retired.

| Mode | The world | Iteration | Scheduled sessions |
|---|---|---|---|
| 1 keep alive | Actions only | none | one a day: health check only |
| 2 periodic | Actions only | one change per session | every 6 hours |
| 3 continuous | Actions; `tools/run_local.py` only if Actions is stuck | back to back, bot worlds for every rules change | none: the session the owner opened keeps driving |
| 4 burn | as 3 | parallel: several mechanics at once in worktrees or sibling sessions, wide bot sweeps, `[world]` dev trials | as 3, plus parallel agents |

- **Mode 1.** Check only: `git log origin/world2 -1` moved within about two hours (it should
  never rest now: the free tiers take the hours Kaggle has not). If it is stale, find why from its
  last workflow run and report; otherwise end at once. Read no decisions, change no code.
- **Mode 2.** One pass of the loop and end: `python tools/civ_round.py --versions 2` and
  `python tools/bot_stats.py --versions 2` (the bot farm's read of the last change), then one
  change: the dominant failure, or the next step in [roadmap.md](roadmap.md) section 5. Build, test,
  bots before and after when rules change (`tools/civ_balance.py`, 3 seeds x 3 years; 6 if
  borderline), record a "Loop, round N" paragraph, and ship (a `claude/auto-<name>` branch from the
  latest main; `automerge.yml` merges it when ci passes).
- **Mode 3.** Driven, not scheduled (the owner, 2026-09-29: "don't do it
  with a routine; mode 3 means you actively drive and iterate"). The
  session the owner opened keeps working; delete any mode routine.
  Sections 3–8 in full, iteration after iteration; two or three
  seed sets and the 100-person land when crowds matter; confirm each
  handover.
- **Mode 4.** Mode 3, and split independent work across worktree agents or
  sibling sessions (one mechanic each, proven on bots in its own
  worktree); merge one at a time, re-running balance after each merge.

Skills in `.claude/skills/` carry the procedures: `mode` (set a mode, or do one
scheduled session), `world-check` (the cheap health check), `ship`.

**Setting a mode** (the session the owner tells): write it on the "Current
mode" line above and ship that; list the routines (`list_triggers`), delete
those of the old mode; for modes 1 and 2 create the new mode's routine as a
fresh-session routine whose prompt is "Read CLAUDE.md and docs/process.md
and do one mode-N session", stop any local runner (`touch .world-stop`)
and end the session. For modes 3 and 4 create no routine: start iterating
in this session.

## 1. What the owner wants

- **A sandbox that grows.** Not a survival game, though surviving comes
  first. A world where, over time, some people thrive and gather wealth and
  power while others barely get by, and where alliances, feuds, markets,
  chiefs, laws, dynasties and faiths *can* appear.
- **Instructions are vague on purpose.** The owner will not say what to
  build. Deciding is the job. Nothing is ever scripted: you build
  **mechanics that make things possible**, and the people (language models)
  decide whether any of it happens. The question is never "how do I make
  a market happen" but "what must be possible, perceivable and remembered
  for a market to happen on its own?"
- **Free.** Only the Gemini free tier and GitHub Actions. Never pay.
- **Light.** Tokens are the budget. Every prompt addition costs
  decisions per day (see section 6).
- **Watchable.** The owner reads the world on a phone through the viewer
  (GitHub Pages): replay, story, chronicle, each person's page.
- **The people never learn they are simulated** (see `CLAUDE.md`).

## 2. Where the work comes from

Three sources, used together each iteration:

1. **The people's own wishes.** Each reply may carry an `idea`, something
   they want that the world does not allow yet. `do` deeds that change
   nothing, and choices the engine refuses, are quieter signals.
   `python tools/ideas.py --dir <world>` groups them. Often the wish
   already exists as a hidden recipe (spear, net, cloak, poultice); then the
   problem is discovery or perception, not a missing feature.
2. **Your own gap analysis.** `docs/mechanics.md` lists, per area (land,
   property, exchange, family, reputation, conflict, governance, culture,
   knowledge, people, minds), what emergence needs and whether the world
   has it (✓ / ◐ / ✗). Keep it current and work down its "Next" list.
   Think like a historian: what did real people need before X could exist?
3. **Failures read from the live world.** The dead and the refused are the
   best teachers. `python tools/health.py <world>` shows deaths by cause,
   refusals and setbacks; `python tools/inspect_world.py <world> --agent
   NAME` shows one person's decisions. Example (w14): 23 of 25 deaths were
   starvation beside full bushes. Reading the last decisions of the dead
   showed people had filled their load with wood and could not pick a
   berry, and the world never said why. No one would have wished for that
   fix; it came from reading the dead.

## 3. The loop, one iteration

1. **Read the world.**
   ```
   git fetch origin world
   rm -rf /tmp/w && mkdir -p /tmp/w && git archive origin/world world | tar -x -C /tmp/w
   python tools/health.py /tmp/w/world --days 10
   python tools/ideas.py --dir /tmp/w/world
   python tools/inspect_world.py /tmp/w/world --agent NAME
   ```
   Also rebuild a real prompt to see what a person actually sees:
   ```python
   import json; from botciv.world import World; from botciv.engine import Engine
   from botciv.prompt import build_prompt
   w = World.from_dict(json.load(open("/tmp/w/world/state.json"))); e = Engine(w)
   print(build_prompt(e, next(a for a in w.living() if a.name == "NAME")))
   ```
2. **Choose** one to three changes: the worst failure first, then the
   most wanted idea, then the next gap from `mechanics.md`. Run each
   through the checklist in section 4.
3. **Measure before.** `python tools/balance.py --seeds 1 2 3 4 5 6
   --years 4` (a few minutes; repeat with `--seeds 7 8 9 10 11 12` before
   believing a small difference, six seeds are noisy) and, when crowds matter, `--config
   configs/large.toml --seeds 1 2` (about ten minutes, run it in the
   background).
4. **Build** in the engine, the rules text (`WORLD_TEXT` and `VERB_HELP` in
   `prompt.py`), `available_verbs`, the ledger labels, the viewer if it
   should show, and **the bots** (section 5): a mechanic no bot uses is
   untested.
5. **Test.** Add a `tests/test_<version>.py`; run
   `python -m unittest discover -s tests -t .` (about 10 s).
6. **Measure after** with the same balance runs. Compare. Undo what made
   things worse, even if it was your favourite idea.
7. **Record.** Bump `RULES_VERSION` in `prompt.py` when prompt or rules
   change. Add a line to PLAN.md section 6a (Versions); results to
   `docs/balance.md`; update `docs/mechanics.md`. When a person's idea
   became real, add it to `botciv/realized.py` (the world credits it once,
   inside the world, to whoever alive imagined it first).
8. **Ship** (section 8), then **verify the handover**: within about an
   hour `tools/health.py` should show decisions under the new rules
   version.

## 4. Think each change through

For every feature, new or old, check the whole chain. The weakest link is
where the work is, even when no one asked for it.

- **Does the problem exist in the engine?** Smoking food only matters if
  food rots.
- **Can the people perceive it?** Rot was silent until w10; the load limit
  was silent until w14. If the prompt does not show it, it does not exist
  for them.
- **Does it pay off at the right size?** Discovery so easy that no one
  needs teaching makes knowledge worthless; a theft that costs nothing
  makes raiding the best life.
- **Is it possible without being scripted?** Give capabilities (take by
  force together, remember who wronged you), never outcomes (no "thieves
  are punished").
- **Is it recorded?** Social things are enforced by people, so the world
  must remember truthfully (ledger, witnesses) and let others see it.
- **Can we measure it?** Add a metric to `tools/balance.py`, a census
  field or an event kind, so before and after can be compared.
- **What does it cost in tokens?** Section 6.
- **Does any wording reveal the simulation?** A test checks the words.

## 5. Bots: the cheap loop

Bot minds (`botciv/minds/bots.py`) play the world with no API calls, so
a four-year world takes seconds. Most engine refusals the bots hit, the
people hit too. Use bots to prove mechanics work and to find balance, not
to predict what the language-model people will do.

- `MixedBot` gives each person one of four minds by `id % 4`: `simple`
  (careless forager), `reciprocity` (tit for tat: repays, joins, takes back
  what was stolen when their people stand beside the thief, answers only
  killing with blood), `planner` (farms, stores, smokes, forms a
  household, teaches, lends, names an heir), `raider` (steals from the
  friendless).
- `tools/balance.py` targets: never extinct; population in range; starving
  under 70% of deaths; 2+ births a year; Gini 0.3–0.6; planners worth more
  than foragers. It also counts builds, plantings, deals, groups,
  teachings, thefts, force, crops taken, heirs, attacks and killings.
- **When you add a mechanic, teach a bot to use it**, or the balance run
  says nothing about it.
- **Do not over-tune bots.** They are a test harness. Example: bots that
  beat thieves once caused feuds (friends joined in, kin avenged the dead,
  4–5 killings a run); it was dropped. What the real people do with
  violence is theirs.
- Bots cannot tell you: whether the prompt is clear, whether people notice
  something, how they talk. Only the live world shows that.

## 6. Keeping it light

- A decision's prompt is about 3,000–3,500 input tokens and 200–300
  output. Gemma models are limited by tokens per minute (about 16K), so
  every 100 tokens added costs about 3% of Gemma's decisions. Flash-Lite
  models are limited by requests per day (about 500 each), where tokens do
  not matter.
- Measure a prompt change: build prompts for every living person from a
  live `state.json` before and after (`git stash` to compare).
- Rules for additions: optional reply fields written only when something
  changes (like `idea`, `remember`, `self`); hard caps in characters and
  count (in `config.py`); offset new instruction text by tightening old
  text; engine-kept facts over model-written prose.
- Don't grow what isn't full: notes average 210 of their 600 characters,
  so making them longer would buy nothing.

## 7. Running the world

- **`world.yml`** advances the world for about 5.5 hours in half-hour
  pieces (`tools/advance.py --chain`), committing state and logs to the
  `world` branch after each and asking `pages.yml` to publish. When a run
  ends it starts the next itself: GitHub's cron rarely fires, so the hourly
  schedule is only a backstop. After each piece it checks main; newer code
  there ends the run, and the next run starts on the new code. That is the
  handover, within about an hour of a merge.
- When every model is spent or resting it waits instead of ending. The
  gateway (`gateway.py`) routes each call to the model with room soonest,
  paces by real token counts, backs off failing models (capped at 10
  minutes) and waits at most 90 s for any model to have room. A person
  whose answer is late keeps doing what they were doing, and the answer
  applies when it comes (up to 3 world hours late, 1 for someone idle); only after repeated
  failures does a tit-for-tat bot decide for them once.
- **`pages.yml`** publishes the viewer, `ideas.md` and a 100-bot world at
  `/large/` under the current rules. Its **watchdog** cancels and restarts a
  world run if the `world` branch has not moved in 90 minutes.
- **`ci.yml`** runs the tests and a key scan on pushes and PRs.
  **`dev.yml`** runs `[probe]` (real prompts per model) or `[world]` (a
  short live run to `dev-world`) when the commit message says so, on
  `claude/*` branches.
- **`tools/run_local.py`** advances the world from any machine with a key;
  it holds a lock the Actions runs respect. Cloud sessions have
  `GEMINI_API_KEY` set, so when Actions runs sit queued for want of a
  runner (it happened 21:46–00:30 on 2026-09-28), a session can carry the
  world: `setsid nohup python tools/run_local.py --hours 5 >> log &`.
  It runs the code of its own checkout, so after a merge stop it and start
  it again; `touch .world-stop` stops it between chunks and releases the
  lock, and a leftover `.world-stop` makes the next start quit at once, so
  remove it first. A container restart or an archived session kills it
  (its unpushed chunk is lost; the lock lapses within 50 minutes and
  Actions resumes). To wait for it to exit, wait on its process id: `pgrep
  -f run_local` inside a watcher matches the watcher itself. Only in mode
  3 or 4 (section 0).
- **Is it healthy?** `git log origin/world -3` should show a commit in the
  last hour; `world/last_run.md` on that branch says how the last piece
  went (calls per model, why it stopped); `tools/health.py` shows which
  rules version decided. A run that failed shows red in Actions.
- **A new world** (only when the old one cannot recover or the rules
  changed too much to continue): run `world.yml` by hand with `new_world`.
  So far every change has been made to carry over (missing config keys are
  filled from defaults on load, new agent fields have defaults).
- Cloud sessions have no `gh` CLI: use the GitHub MCP tools for PRs,
  checks and workflow runs.

## 8. Shipping

1. Work on the session's `claude/*` branch, started from current `main`.
   If the branch's PR was merged, reset it:
   `git fetch origin main && git checkout -B <branch> origin/main`.
2. Run the tests. Commit with a message that says what changed and why,
   with the numbers that justify it.
3. Push, open a PR to `main` (body: what, why, measured, tests), wait for
   the CI `test` job to pass, merge (merge commit). If GitHub's runners sit
   queued, run CI's own steps on the pushed commit instead (the key scan
   `git grep -nE 'AIza[0-9A-Za-z_-]{30,}' -- .` finds nothing, and
   `python -m unittest discover -s tests -t . -q` passes under Python 3.11)
   and merge with `expectedHeadSha` set to that commit.
4. Check within the hour that the world runs the new rules version.

## 9. Lessons learned the hard way

- Bugs hide where no one looks: the farm could not be built for eight
  versions because "farm" was an alias for grain; seeds from berries never
  came because the branch was unreachable. A metric at zero is a question.
- A silent limit kills: rot, load, weight. Say it in the rules, show it in
  the prompt, name it in the refusal, with what to do about it.
- Refusals waste whole decisions. When people keep asking for X in a way
  the engine refuses, make the engine understand them (walk to the person,
  "take from store" means food, "farm" builds a farm).
- A run that failed must show red, and a hung run must be restarted
  (watchdog); otherwise the world stops and no one notices.
- Old saves must load under new code (defaults for new fields and keys).
- Deterrence emerges when wrongs are remembered by victims, kin and
  witnesses, and when people standing together can act; not from rules
  against wrongdoing.
- Look where the decisions go, not only at what is refused. The two
  biggest wastes of 2026-09-28 were never refused: people standing idle
  while their late answer was out (w19), and a third of all choices spent
  lifting and dropping things beside the same piles (w20).
  `tools/health.py` prints both (choices by verb, answers late by hours).
- A bot that spends an hour on something new can wreck the balance on its
  own (w17: telling cost 15 points of starvation; a bot that merely waited
  the same hour did the same). Talk should be free, like speech.

## 10. Where things stand (2026-09-30, 07:30 UTC)

> **Superseded for the civ worlds:** the current state, the tracks and the ordered next steps are in
> [roadmap.md](roadmap.md) (2026-10-02). This section describes the first world (botciv), now paused.

- **Heavy session opened by the owner on 2026-09-30** (the mode line above
  still says paused; the owner asked for this one session). Merged: w31
  service (hire_days / serve_days in a deal; servants count as the master's
  people, may put into the master's stores, daily account to the master;
  leaving early remembered; a thief seldom gets past the victim's people),
  w32 standing trades at stores (`post`, `trade`) and `plant` that walks to
  a free farm one knows or rich soil in sight. Numbers in docs/balance.md.
- **Live world at day 329 (w30)**: 16 alive, 69 ever; 45 of 53 deaths
  starved; no births ever (5 `ask_child`, 1 pledge); 8 proposals, 4 deals;
  stores hold 467 seeds, 370 wood, 235 fibre and under 100 food worth;
  take/put/drop are a third of all choices. Gemma carries most decisions
  (4,200 input tokens a prompt).
- **w33** (merged after w32): an accepted `ask_child` is an agreement for 10
  days; the child is conceived the first hour both are well fed and side by
  side. Watch `agree_child`, `conceive`, `birth`.
- **w34-w36** (merged after w33): `make` things of one's own design and
  naming (they do nothing by themselves: tokens, crowns, heirlooms, money);
  sickness that spreads to those beside the sick, eased by rest, food,
  shelter and company, carers remembered, a poultice ends it; buildings
  with no living owner fall apart in about 20 days unless someone claims
  them by building the same thing on them. Watch `make`, `sick`, `mend`,
  `claim`, and whether the abandoned stores are claimed or lost.
- **w37** (roadmap Phase A, capacity): prompts about 19% shorter; fewer
  wake-ups (familiar faces, passing plan steps, busy listeners); gateway
  rests quick gemma 500s for 2 s. Measure: decisions per person per world
  day (2.4 before), gemma-4-31b ok vs errors, world days an hour (5.5
  before).
- **Kaggle GPU trial** (`kaggle-trial.yml`, run by hand): the first run
  proved login, push, two T4s and output collection; it stopped at the
  Ollama install (needs zstd, fixed). Run 2: gemma4:26b on two T4s, 200 of
  200 valid, 479 decisions an hour (the API tier: about 200). Next: 8 at a
  time, then run the real world there (roadmap section 8).
- **Kaggle world run** (`kaggle-world.yml`, run by hand; `tools/kaggle_world.py`
  drives, `tools/kaggle_world_kernel.py` runs on Kaggle): the notebook starts
  Ollama while the workflow takes `world/LOCK`; the Actions world run keeps
  the piece it was advancing (rebased onto the lock-only commit), then
  waits and says so in the LOCK (`"ack"`); only then does the workflow set
  `"go"` in the LOCK, the notebook advances that
  commit with `ollama:<model>` for everyone, and the workflow pushes it back
  only if the world branch did not move, then removes the lock. The waiting
  run pulls it and goes on. The Pages watchdog leaves a locked world alone.
  First real run (2026-09-30 18:00-19:00 UTC, 9 people): day 422 afternoon
  to day 429 afternoon (85 hours, 7.1 days) in 56 minutes, 211 decisions,
  all valid, came home cleanly. That is the API's pace, not double: with
  9 people a mean of 2.8 decide at once, each hour of the world waits for
  its slowest answer (12.7 s mean on the T4s), so 3 of 4 slots sit idle.
  The trial's 479/h is throughput with 4 always in flight. Kaggle pays off
  with many people (world 2), not with this world; run it alongside the API
  only if the world is split, never on the same world. The first run gave
  the go too early (a new world run was mid-piece; cancelled by hand); the
  world run now acknowledges the lock (`"ack"`) and Kaggle waits for that.
- **Open at the end of the 2026-09-30 session**: confirm w37 is deciding
  live (decisions per person-day, gemma-4-31b errors, world days an hour);
  watch hire/trade/make/sick/claim/conceive events; the hoarding loop.
- **Viewer overhaul (2026-09-30)**: the replay map pinches, drags, wheel- and
  button-zooms; tapping anything opens a card (a building's owner, who may
  use it, contents, posted trade, crop, fuel, ruin; a person's doing,
  health, load and buildings; bushes, piles, herds, wolves, signs, named
  places). The engine now logs once a day, with the census, every building,
  bush and pile (viewer only), so the replay shows the land as it was;
  earlier days fall back to "as it is now", labelled so. The legend is drawn
  with the map's own functions. TV mode's timeline can be dragged.
  Tested in headless Chromium (`playwright` with the preinstalled browser).
- **Hoarding, read closely (day 332)**: the loop is opportunistic: things
  seen on the ground are picked up "to be efficient", loads sit at the cap,
  then several decisions go to making room (Hardri: about 20 in a row at
  34.9 of 35, against full stores of the dead). No fix yet that is not a
  nudge; see first whether posted trades give hoarded things a use.
- **Watch after the handover**: `hire`, `service_*`, `post`, `trade`,
  `plant` events and deals per day; whether a master with servants takes by
  force; whether anyone posts a trade that pays for work (grain for wood);
  sowings now that `plant` walks to the abandoned open farms at (16,5) and
  (22,5).
- **The long road** (owner, 2026-09-30): many more resources, a tech tree
  to the Bronze Age, and many more people. Plan and gates in
  [roadmap.md](roadmap.md); its Phase A (content as data, process
  buildings, smaller prompts, capacity) comes before any new era.
- **Next, in order**: (1) the junk hoarding (wood, seeds, bone filling loads
  and stores while people starve): look for a perception fix, not a nudge;
  (2) births, once w33 is live; (3) docs/mechanics.md: dependent children
  once births happen, sickness, fish that deplete.
- **Kept from before**: the world is fastest just after 07:00 UTC, when
  Gemini's daily quotas reset; after that gemma-4-26b carries it at about 4
  world days an hour. Groq (gpt-oss-120b/20b, qwen3.8-27b) adds calls until
  its daily token limit. The owner's other repo (evosim) shares the Actions
  runners, capped at 3/4 of them; if botciv jobs queue, check its load
  first. Not usable: GitHub Models (retired), Kaggle (no chat API). TV mode:
  the viewer's 📺 button or `…/#tv`.

## 11. The second generation (civ), from 2026-09-30

The owner: treat v1 as a trial, build big and ambitious, fill most of a large world with general
bots so AI people have a society to act in. `civ/` is that rebuild (design: docs/v2.md; content
plan: docs/civilization.md). The Kaggle sweep (2026-09-30) settled capacity: two T4s serve about
680 decisions an hour whatever the parallelism (4 slots best; 16+ worse), prompts about 2,800
tokens. civ's AI people decide about twice a world day and never hold the world up, so one GPU
carries about 50-80 of them; world2 starts with 200 people, 48 AI. Bots-only civ worlds: 100
people stable over 3 years, era 2 reached. `botciv/` keeps the first world (the API world)
running until civ proves itself; then that world moves too.

**The first civ piece (2026-09-30, rules c1) taught three things.** (1) The gateway matched
"gemma" inside "ollama:gemma4:26b" and paced the local GPU like the free API (15,000 tokens a
minute), so every call gave up as out of budget, and the bots ran the land alone for 34 years in
the hour. `limits_for` now lets a service prefix decide first (a test holds it), the runner stops a
piece when most answers fail ("the model is not answering"), and failed decisions log their error.
(2) Newborns are bots, so the AI people died out; the land now keeps `cfg["ai"]` minds, a grown
child of a dead one first (`Engine.keep_minds`). (3) "Teach me X?" offers meant the asker teaches:
offers now have `teach` (I teach you) and `learn` (you teach me). Rules c2 also made poultices
usable (`eat`), and the bots now draw goals by weight (taming, leading and trade get their turn),
feed their beasts, and keep their trades stocked. world2 was restarted (`restart: yes` on
world2.yml) after the fix; the 34-year bot world stays in the branch's history.

**The second civ piece (2026-10-01, c2) died out in 16 minutes.** gemma4:26b on two T4s writes
about 4.5 tokens a second per slot, so an answer takes about a minute. 48 people asking at once
queued past the 240 s patience, and since patience was judged on the oldest answer, the world
stopped waiting for good and raced 29 years. The AI people starved before any answer came, and
`keep_minds` turned bot after bot into minds that were never answered, until no one was left.
Now: at most 2 x parallel asks are out at once (urgent first, then longest without); patience is
per answer; whoever waits their turn idle or hungry gets a bot's stopgap (their reasons to think
are kept); the AI share is topped up by `LLMMind.keep_minds` only while the model answers well, at
most 3 a day. Against an 8-slot stub (8 s an answer): 219 answers in 4 minutes, none lost, no AI
deaths. Expect about 440 answers an hour on Kaggle, and about 10 world days an hour. Bots alone on
the 200-person land (6 years): 202 -> 208 people, 118 births, era 2, 41 tamed, 90 trades.

**The third civ piece (2026-10-01, c2, 120 minutes) worked.** 842 answers (about 420 an hour),
1 failed, 16 too slow to wait for; an answer takes 66 s (3,060 tokens in, 293 out); 18 world days
passed (about 9 an hour); 197 of 200 alive, 7 births, 25 groups; the AI people talk, trade, teach
and pledge. But all 9 who starved were AI people, and many of the rest went hungry (satiety 0-3;
bots averaged 13). A person who adopts a plan while hungry is not woken by hunger again until fed,
and an AI plan that forgets food was never interrupted. c3: a hunger reflex (at satiety 4, carrying
no food, with no food in what one is doing or about to do, the bot's food plan, keeping the reasons
to think), with a test that starves without it. `take` also walks to a pile further off (the AI
people's most refused step after "you carry no berries").

**Two civ worlds side by side (2026-10-01, the owner: iterate faster, in parallel).** The first
world (botciv, `world.yml`) is paused; its free-tier capacity (Flash-Lite, every Gemma big enough,
Groq's chat models) runs world3 (`world3.yml`, `tools/advance_civ.py`): 200 people, 48 AI, seed 11,
half-hour pieces that commit and publish, hand over to newer code within the hour, and wait when
every model is spent. world2 on Kaggle now runs 45-minute pieces, checked hourly, under the same
GPU budget. A change merged to main is running in world3 within the hour and in world2 at its
next piece; compare the two at /botciv/world2/ and /botciv/world3/.

**Bots that answer (2026-10-01, c4).** In world2 the AI people said 12 things each in 18 days
and the bots 0.33; the AI people spoke to bots by name ("Drir, can we trade some flax for your
grain?") and got nothing back. `civ/minds/talk.py`: the engine keeps what each person lately heard;
a bot reads words spoken to it for what they ask (food, a trade, a lesson, a hand, a place in a
group) and acts through ordinary steps (give, propose, teach, follow, invite, join), or answers in
its own voice (how it fares, what it is doing); it remarks on its work now and then and asks for
food when hungry. No endless bot-to-bot chatter (once in half a day per pair; to a bot only when
asked). Bots also make promises when they have no gift for a lesson and keep them (a give of
promised goods now counts; a promiser is reminded two days before it is due), and the desperate,
bold and ungenerous may take from a stranger's store. eat of a food one lacks eats what one has.
Bots-only, 2 seeds x 1 year: alive 123/144 (was 114/139), speech about 4x, promises kept 52 vs
broken 50 (were never made).
The 30-minute Kaggle piece on c3: 171 answers (about 340 an hour), 0 failed, 4.7 world days, 1 AI
person starved (was 9 in 18 days), AI satiety mean 10.

**Reading the Kaggle world (2026-10-01, 274 hours, 1,012 AI answers) -> c5.** The AI people's
hours: go 28%, gather 26%, idle 25%, craft under 1% (bots: gather 42%, idle 20%, build 7%); AI
satiety 10 vs bots 13; 26% of AI steps refused. What the refusals and the dead showed:
- a gather at night could round to nothing and say "can carry no more", ending it: a starving
  man beside berry bushes gave up. A slow hour now just goes on.
- accept/refuse named offers by misremembered numbers (37); they now find the offer by who made
  it, or the only one there is. refuse could remove someone else's offer: fixed.
- put "into" a shelter (people keep things at home) or a step off a pen: a shelter now keeps 15
  things, and a building one step from the place named is found.
- one starved among picked-clean bushes because a plan that "sought food" never let the reflex
  in: at satiety 2 or less the reflex takes over whatever the plan; bots with plenty give a little
  to the starving who ask.
- idle while their answer was thought out: a stopgap now fills the wait (not at night when fed).
- answers average 293 tokens out and output sets the pace on the GPU (about 60 s of the 66 s an
  answer takes): thought is one short sentence, memory and beliefs only when they change.

**Monuments that carry words (c6, from the people's ideas).** Of nine ideas the AI people wrote in
world2, five were about lasting: "carve my name in stone", "record my deeds for all to see". The
design said a monument "carries a name and carved words", but nothing did. Now build of a cairn,
shrine or other monument takes name and text; whoever passes sees it, with who raised it, after
its maker is gone; it goes in the chronicle (event "monument"). Bots raise one about once a year at
most: for kin they have lost ("Here we remember ..."), for their group (its rules), or, the
ambitious, for themselves. Bots-only, 2 seeds x 1 year: alive 121/140, 5 monuments a year.

**The c5 piece on Kaggle (30 minutes):** 185 answers, 0 failed, 52 hours, no deaths, 79 things
made; AI steps refused fell from 26% to 9%; AI satiety 10.7 (bots 12.7). Answers stayed long (281
tokens out, 74 s): the visible fields are about 130 tokens, so memory and beliefs take the rest.
c7: memory "a short line, only when something new is worth keeping", beliefs rarely; the plan
rules say every step walks by itself (never go before one), and a go just before a step at the
same place is dropped; the decision log records memory and belief sizes (mem, bel).

**Heavy read of world2 at day 28 (326 hours, about 1,370 AI answers) -> c8.**
- *Winter:* stores hold 1.6 food a person and 13 of 48 AI people have a home, but played by bots
  from that very state the world came through its first winter with 4 deaths (hunting and fishing
  carry it). The risk is the AI people: they now see their warmth for a winter night in autumn and
  winter ("warmth 1 of 3 ... Below 3 the cold hurts").
- *Plans never finished:* 58 AI answers aimed at pottery (gather clay, wood, craft a pot), yet only
  4 people ever tried it. Any wake replaced the plan with a new one, and the commonest wake was
  being spoken to (280 of the decisions, more than plans ending: 187); the prompt did not show the
  steps left, so each answer started over and crafting (the last step) was under 1% of AI hours.
  Now the prompt shows "Your plan, still to do: ...", an answer without a plan goes on with it
  (words, notes, the work continues), being spoken to is no longer urgent (the 3-hour gap holds),
  and a bot's reply or remark in passing does not wake an AI listener (bots still wake each other:
  quieting them cost births, 45 vs 66 over 4 seeds, through fewer choices).
- *Crops taken without meaning to:* 138 take_crop (102 by bots): gather grain went to the nearest
  ripe field, anyone's. Now only fields one may use, unless one names a stranger's field by place
  (meant, seen and remembered); a starving bot may do that. With fields open to all again, seed 1
  fell to 90 alive (27 starved): the rule helps.
- *Pottery, the gateway (it opens 5 crafts),* had 4 learners: bots now weigh crafts by how many
  others they open. Pottery learners in a bots-only year: 4 -> 16.
- Rules text tightened about 10% (same facts).
Bots-only, 4 seeds x 1 year: alive 129/136/125/127 (main 127/140/136/132), one seed at era 2.

**Loop, round 1 (c8 piece on Kaggle, 30 min): 206 answers (was 185), 235 tokens out (was 281),
67 s each; memory 63 chars an answer; walking 17% of AI hours (was 28%); crafting 1.2%; no deaths.
Now refusals were the commonest reason to be asked again (about 100 of 206): c9 skips one refused
step and goes on with the plan (a second in a row wakes), eat with nothing to eat is quiet, gather
of what lies on the ground in sight picks it up, and refusals say what to do. With it went bot work
from three-year runs: the land carries its herds (they were hunted to 3 of a kind), farms are
reused and sown (41-50 of 73 lay empty while people held 150 seeds), seed is kept from harvests,
children are housed and fed from their parents' stores, kin are fed from stores, and word of rare
deposits spreads between people who spend time together. 4 seeds x 2 years: alive mean 126.5,
era 2 on three. Prospecting trips were tried and dropped (they cost lives).

**Loop, round 2 (c9 piece, 30 min, into the first winter): 207 answers, 212 tokens out, 66 s;
refused steps 10% (was 15%); asked again after a refusal about 40 times (was about 100), and 45%
of decisions now come from a plan finished; no AI deaths (day 38, winter); AI satiety 7.4. c10:
"take shelter" goes in under one's own roof or the nearest one may use; "None"/"nothing" as an item
means none; fuel walks to a fire within 10 (or the one named) and says what burns.

**Less struggle to stay alive (c11, the owner's wish, measured in the AI people's own words).**
In the first winter 162 of 207 AI decisions spoke of warmth, 151 of food, 107 of hunger, and 14
of pottery, building, learning, farming or trade together. Two bot bugs fed the struggle: most bots
who starved had 28-172 food in their own store a step away but full hands ("You can carry no more"),
so a hungry person now eats their fill at a store they may use or a pile, and bots put things away
when their load passes 80% (4 seeds x 2 years: 126.5 -> 151 alive, starved about 50 -> 7). Then the
rules: hunger every 5 hours instead of 4 (about 2.5 food a day), and the cold below warmth 3 bites
half as often. 4 seeds x 2 years: 165/171/172/169 alive, almost no deaths; 4 years: 120 -> 170
and 120 -> 231, growth flattening, no crash; era 2 on all.

**The road to bronze (c12, bots-only diagnosis).** Five bots-only years never smelted. Traced link by
link: (1) clay ran out: 7 banks of 60 on the whole land were dug out by pottery in three years
(people knowing any clay: 78 -> 21); now twice the banks at 150, and marshes yield clay;
(2) the planner could not get bricks for a furnace, then fired them in someone else's kiln and
never fetched them: it now looks in any workshop one may use; (3) bots took on learning plans of
at most 8 steps and smelting needs 9: 10 for era 2 and later; (4) a smelting run's materials
(about 9 wood, 8 clay, 4 stone, 2 ore) could not be carried at a load of 20, and the bot then put
away the clay and ore it had gathered: load 30, and what the plan or the craft being learned needs
stays in hand. Result: furnaces built and smelting tried by year 2.5 (a beginner fails most
tries); seed 1 reached era 3 (lime burning) in three years. Word of the land works: people knowing
of copper rose from 4 to 63 in two years.

**Loop, round 4 (c11 piece, spring of year 2): AI satiety 11.9 (was 8.9), no AI deaths, warmth in
39 of 209 decisions (was 162); but AI crafting stayed under 1% of hours: of 1,015 steps planned,
14 were crafts (go 341, take 160, gather 156, eat 91, drop 52). The prompt listed recipes as bare
formulas and never said what a thing is for or that one could make it now. c13: recipes say what
things are good for ("flint axe (wood x2)", "cloak (warmth 2)", "smoked meat x2 (food 4, keeps)",
"basket (carry +10)"), and "You could make now, with what you carry or keep: ..." lists up to four
useful things one could make at once (47 of 48 AI people had some). take of what comes from the
land gathers it.

**Loop, round 5 (c13 piece, summer of year 2): crafting took hold.** Craft steps planned 14 -> 42,
things made by AI people 5 -> 20 (fishing lines, digging sticks, a basket, a sickle, tunics), all
things made 57 -> 149, AI hours crafting 0.8% -> 1.8%; refused AI steps 5.6% (was 12%); 178 tokens
out; 59% of decisions follow a plan finished; 8 births, no deaths. c14: offers last two days (AI
people answer about 16 hours later on average, and a day's offers lapsed unanswered), gather of
hide, meat or bone says to hunt or slaughter, and consecutive go steps collapse into the last.
Bots-only, seed 1, four years: smelting able and lime burning (era 3), 163 alive.

**Loop, round 6 (c14 piece, summer of year 2): crafting kept rising**: craft steps 42 -> 60, things
made by AI people 20 -> 31 (needles, tunics, fishing lines, baskets, shoes), AI hours crafting 2.4%;
57.5 s an answer; no deaths, 4 births; a first quarrel over grain ("Yoth, stop! That is my grain!").
Refusals rose to 10%, mostly grain (17: no field of one's own and no wild grain known; honest) and
give written as a list of goods (8: now read). c15 also brings groups with common stores (set_dues,
treasuries, vote act dues; bots join groups they are invited to; leaders of 3+ set dues).

**A crash, and the guard against the next one (c15 hotfix).** world3 stopped at 10:25: a go with x
and no y crashed the c14 code that collapses walking (comparing None), and a crashed run does not
chain. The comparison now checks all four numbers, and the engine never lets one person's odd
answer, step or act stop the world: a bad answer becomes a short wait, a step that throws is a
refusal ("that step made no sense"), and a person whose doing throws loses only their plan.

**Loop, round 7 (c15 piece, autumn of year 2): no crash (the hotfix came after it started, and
nothing tripped it); AI people made 33 things (cloaks, linen, tunics, hats, baskets), 23 joins into
groups, 4 monuments, 7 thefts, no deaths, 33 of 48 AI people housed. Nearly half the refusals were
grain (46 of 100): the places one remembers listed every farm as "farm", whoever's it was. c16:
remembered buildings say "of yours", "open to you" or "(someone else's)".

**Loop, round 8 (c16 piece, winter of year 2): 101 things made, 19 teachings, 7 births, no deaths;
but grain refusals rose (40 "no grain to gather", 27 "you carry no grain" in a put after it): in
winter no field bears, and 15 of the 40 had grain in their own store. c17: gather of what the land
does not give now, but one's store (within 20) holds, takes it from the store; in winter the
refusal says nothing is ripe and grain is had from stores or by trade; put of what one does not
carry is a quiet note (no refusal, no asking again).

**Loop, round 9 (c17 piece, deep winter of year 2): grain refusals fell from 67 to 23; trades 12,
teachings 24, 9 births, no deaths. The new top refusal: "carry nothing to burn" (22), feeding fires
in winter with no wood in hand. c18: fuel fetches wood (or charcoal) from one's own or an open store
within 10 first, once.

**Loop, round 10 (c18 piece, spring of year 3): refused AI steps 7% (71 of 1,007), no AI deaths, AI
satiety 10.9; the rest are mostly honest ("nothing is ripe in winter"). About half of what the AI
people do is still the bots' stopgap while their answer is thought out (192 stopgaps, 203 answers):
the GPU gives about 200 answers a half hour to 48 people. c19: give with nothing named gives food.

**Loop, round 11 (c19 piece, spring of year 3): world2 reached era 2.** Refused AI steps 5.1%, 69%
of decisions follow a plan finished, 167 tokens out, 60 s an answer, 7 births, no deaths. c20: a
gather named at a place one cannot reach goes to the nearest reachable one instead.
The GPU is now the limit: 8 slots at 3.5-6 tokens a second each, about 400 answers an hour for 48
people, so about half of what the AI people do is still the bots' stopgap. A smaller model (e.g.
gemma4 e4b, perhaps 3-4x the answers), fewer AI people, or shorter plans would change that; the
owner's call.

**Loop, round 12 (c20 piece, summer of year 3): refused 4.7%, 23 teachings, 23 gifts, no deaths;
but AI crafting stays near 1% of hours (bots 3.8%) and "hungry" is in 90 of 209 decisions though
satiety averages 11.9. The prompt listed a store's contents but never how long the food would last.
c21: "Food: you carry about N days; your stores hold about M days" (or none).

**Loop, round 13 (c21 piece, summer of year 3): with food shown in days, the AI people planned
ahead: "winter" in 58 decisions (was 24), "store" in 39, 65 put steps; no deaths, 36 of 48 housed.
Crafting stays low, which in a summer spent laying by for winter is no fault. The top refusal is
again grain (25), gathered while one's own field is still growing: c22 says when it will be ripe.

**Loop, round 14 (c22 piece, autumn of year 3, 257 people): the first killing for a cause.** Pakroun
reaped Drikyal's field six times; Drikyal thought "Pakroun is stealing my grain and I must stop him
before winter", said "Stop taking my grain!" and struck him dead. But the engine judged that blow
like any other: onlookers held it against Drikyal as much as a murder, the dead man's kin were only
told he died, and the prompt said "you distrust them" without saying why. c23, known wrongs: a
blow against one the onlooker knows to have stolen or struck (or that the striker's friends know
wronged them) is seen as just; the reason for a grudge shows beside a name ("you distrust them:
took 3 grain from your store"); kin hold a killing against the killer; word of wrongs goes round
among friends each morning. Bots warn off whoever robs them, and the bold strike if it goes on.
Bots-only 4 seeds, 2 years: alive 658 (base 656), attacks 8 (0), killed 3 (2).
c24 (bots' refusals, while the first gemma4:e4b piece runs): `post` now walks to one's store like
every other step (it was the one that did not, refused about 150 times a seed); fishing is planned
only with water at hand and a tool that makes a day's catch likely (smoked fish had been refused
180-480 times a seed); a hunt can keep its hide or bone (`keep`), taken up where the beast falls, and
the hunt's message says where they lie. Bots-only 4 seeds, 2 years: alive 664 (c23 658).
Bots: children with their arms full (12 clubs, 21 fibre) went on gathering and making, refused
again and again ("club needs 1 wood": they could carry no more); now they hand the most of it to a
parent, or put it in the family's store, or set it down. Bots-only 4 seeds, 2 years: alive 691
(c24 664); club, hat and rope refusals gone.

**Loop, round 15 (c23 piece, first on gemma4:e4b, 12 slots; winter of year 3): twice the answers
(426 in the piece, was 210), 41 s each, none failed or too slow, AI crafting 3.1% of hours (was
about 1%); but 25% of AI steps refused (was 7%): grain in winter, a named beast not about, fuel
with no wood, "gather hide". Four killed: three orphaned bot children by wolves, alone at the
land's edge in winter, and Zusa (AI) by Vouk, a bot, struck again and again for 4 grain: c23's
guard went too far. c25: a bot strikes a thief once, never the starving; orphaned children keep
near a grown-up at night and in winter; gather hide/meat/bone hunts (keeping it), gather fish
fishes, a hunt for a beast not about goes after the game there is, and fuel with no wood
gathers some nearby first. Bots-only 4 seeds, 2 years: alive 681 (691).

**Loop, round 16 (c25 piece on gemma4:e4b, spring of year 4): 417 answers, 43 s each; refused AI
steps 23% (25%); AI crafting 4.0% of hours (3.1%); deaths: 2 of sickness, 1 to wolves, and one
feud: Yiryis took a grain from Therrur's store, Therrur reaped 12 of Yiryis's field, Yiryis struck
him dead ("This grain is mine; you will cease reaping it immediately"). A people's choice. But
bot guards struck after one theft (the warning and the blow answered the same theft). c26: a bot
strikes only for a fresh theft after its warning; a hunt with no game known casts about for tracks
within 20 steps (the top refusal, "no deer nearby", 35); a craft short only of what the land
close by gives gathers it first; take falls back to a store one may use, and a bare field says
why; gather tries the next nearest spot when one cannot be reached. Bots-only 8 seeds, 2 years:
alive 1331 (c25 1346, noise).
The owner chose the smaller model (2026-10-01): `world2.yml` now defaults to `gemma4:e4b` with 12 slots, scheduled pieces included.

**Loop, round 17 (c26 piece, summer of year 4): refused AI steps 20% (23%), 267 made (186), 33
built (20), no deaths. c27: being too laden says what weighs one down and where one's store is
(hoarders carrying 39 flax and 32 grain were refused again and again); the daily snapshot (v2,
append-only) keeps groups as they stand, each person's goal, and how far a crop has grown, for
the new viewer's menus that show the world as it was at the replay's moment (docs/viewer.md).

**Loop, round 18 (c27 piece, autumn of year 4): 403 answers, refused 21%, no deaths, 205 made.
c28: a craft short of fish fishes first, short of meat, hide or bone hunts first (as it already
gathered what the land gives); a hunt casts about for tracks 40 steps out; dropping or giving what one
does not carry is noted quietly. Bots-only 4 seeds: alive 634 (c26 643 on the same seeds).

**Loop, round 19 (c28 piece, winter of year 4): 342 answers, refused 17% (21%), one old man to
wolves. "put did not work out" woke people 36 times and wiped their plans: a store not open to them,
or full. c29: put goes to one's own store with room instead, and a full or closed store is told
plainly without undoing the plan. Bots-only 4 seeds: alive 636 (c28 634).
Bots: when every kiln (or other self-running workshop) one may use is busy firing, the planner picks
another task instead of planning a firing that will be refused. Bots-only: seeds 1-4 alive 670 (636),
seeds 5-8 658 (665); kiln refusals gone.

**The bot farm (2026-10-02, the owner: keep spare Actions capacity busy with bot worlds).** `bots.yml`
runs four shards for about 40 minutes each: bots-only civ worlds on fresh random seeds, on main's code
(three on the balance land, 120 people, 80 wide, 3 years; one on the world2 land, 200 people, 96 wide).
One line per world goes to `results/<rules>.jsonl` on the `bots` branch, and the run starts the next.
`tools/bot_stats.py` reads it by rules version and land, with the standard error, and sets the newest
version against the one before. A rules change is judged there once each side has a dozen worlds or
so (seed 1 alone swings ±15 alive); a session's own 3-seed run stays the quick check before shipping.
Pause it with the repository variable `BOTS_OFF=yes`.

**The long land (2026-10-02, the owner: one world left to run for a long time, watchable).**
`botworld.yml` advances a bots-only world that is never reset, as fast as it goes (about 40 world
years a run at 200 people), under main's rules. `tools/advance_long.py`: about 35 minutes keeping only
a census line a season (`civ/census.py`, `world/history.jsonl`: people, births, deaths by cause, era,
crafts known and first reached, buildings, groups, beasts, Gini), then the last 20 days hour by hour,
then the `botworld` branch is replaced by one commit (it never grows). The viewer is at /botciv/long/:
the land as it stands, and the journal's Measures page charts the whole run ("The long run").

## The two-world loop (2026-10-01, the owner: iterate as fast as can be)

**Ended 2026-10-02: one world.** The owner put every resource on one world. world3 is retired (its
workflow is gone, the `world3` branch keeps its history, the site shows only world2). world2.yml now
runs every hour: a Kaggle piece when the GPU budget leaves 30 minutes or more
(`tools/kaggle_world2.py --room`), otherwise about 45 minutes on the free tiers
(`tools/advance_civ.py --branch world2 --ai 48`). One workflow and one concurrency group, so the two
runners never write the branch at once. Each run starts the next as it ends (`gh workflow run world2.yml`;
`advance_civ.py --chain`): GitHub ran only 5 of the hourly schedule's runs in 31 hours, so the
schedule is just a backstop for a broken chain. The free tiers are limited by the minute and the day, so
giving Kaggle its 3.8 hours a day costs them little; with 48 minds the world waits on their answers,
so free-tier hours move fewer world days (a 3-minute trial on a copy: 39 answers, 12 world hours, 0
failed, 14.7% refused) but each person thinks as often per world hour. Each person now thinks with
whichever model is running; `civ_round.py` splits by model, which now compares the models on the
same land. The rest of this section is history.

Two civ worlds always run the newest rules from main, side by side, on different models:
- **world2** (Kaggle GPU, gemma4:e4b, 48 minds): the main signal, about 400 answers in a half-hour
  piece, dispatched by hand right after each merge (`world2.yml`, the week's Kaggle hours permitting).
- **world3** (free Gemini, Gemma and Groq tiers, 16 minds since round 20): runs on its own,
  continuously, in half-hour pieces, and starts again on new code within a piece of each merge. With
  16 minds rather than 48 each thinks three times as often on the same free allowance, and the land moves
  faster.

Each round: merge, dispatch world2, and while it runs work on the bots and the viewer; when it lands,
**`python tools/civ_round.py`** reads both worlds and pools them by rules version (answers, refused
steps and why, what woke people, what they made, deaths, by world and by model). Read it so:
- a failure in **both** worlds is the rules' or the prompt's: fix it;
- a failure in **one** is likely that model's way (e4b is clumsier than the 26-31B models: under c28
  it had 17% of steps refused, world3's models 8%): prefer forgiving the step (do what was meant) over
  telling the rules again;
- a version is judged on the pooled numbers, as soon as both have a piece under it.
Bots-only balance runs (`tools/civ_balance.py`, 4 or 8 seeds) stay the fast check of any change before
it ships.

**Loop, round 20 (c29 piece, spring of year 5): refused 17.5%; "put did not work out" gone (36 to 6
wakes). The game is being hunted out: 49 herds and 369 beasts at the start, 14 and 125 now (a herd
hunted to nothing is gone; the rest grow back a quarter each spring). Left so: it is the people's own
doing, and it presses toward herding and farming. Three to wolves (two bot children), one killing.
Tried: children without a home sleep under a parent's roof: alive 638 against 670, reverted. c31: a
field near ripeness says "later today" or "by tomorrow" (it said "in 0 days"), a ripe one "reap it".

**Loop, round 21 (c31; first read of both worlds with tools/civ_round.py): world2 no deaths, 275
made (190), 41 taught, refused 18%; world3 (16 minds, c30) 19%, mostly one person's full shelter (13).
Both worlds: sowing refused for want of an empty field. c32: a field of one's own that still holds a
harvest is reaped first, then sown; with nowhere to store, the refusal says build a store or drop
things. world3 with 16 minds gives about 40 answers a piece (73 with 48): it was waiting on answers,
not the quota; watch whether the land now moves faster. Bots-only 4 seeds: alive 669 (670).

**Loop, round 22 (c32): world2 no deaths, 51 taught, 25 deals, refused 18%; world3 (c31) 32%, nearly
all a full shelter tried again and again (32 refusals; world2 15). In both: one's only store full,
nothing else with room, the advice to build a store not taken. c33: what does not fit in one's own
full store is set down beside it, where anyone passing may take it (said so). Bots-only: 666 (669).

**Loop, round 23 (c33): the full-shelter refusals are gone (overflow set down beside it). World2: one
to wolves, 38 taught, refused 18%. Top now: crafts short of meat, hide or fish (47), "give to whom?"
(9). c34: a craft short of what the land does not give says where it comes from (a hunt, your pen,
trade, fishing); a gift with no one named goes to whoever is beside one, the most trusted. Bots-only:
659 (666).

**Loop, round 24 (c34): world2 refused 18%, "give to whom" gone; world3 (c33) 12.5% (32% before:
the full-shelter overflow worked). In both: sowing in winter (14), berries picked bare in spring (18).
c35: those refusals say when: "spring comes in N days"; the bushes "fill again a few a day".

**Loop, round 25 (c35): world2 refused 17.7%, no deaths; the winter-sowing refusals are gone. Top now:
no game known (16). The land holds 14 herds (127 beasts) for 325 people; half of them live 59 steps or
more from the nearest herd (game wanders back only where people are few). Left as the people's doing.
A hunt that followed tracks up to 40 steps off ran out of hours on the way: c36 follows tracks only as
far as a hunt can go (20), and beyond, the refusal says where the nearest herd is ("hunted out; about
N steps north-east, where people are few") or that game is gone. Longer hunting trips were tried and
undone: bots starved far from home (3-year bots: 512 alive against 548). Kept: 3-year bots 543 (548).

**Loop, round 26 (c36): world2 refused 17.3%, no deaths; hunting refusals 16 to 10 (they now say where
herds are). Thefts 7 to 24. Top now: grain: sowing with none carried (13), none to gather (11), no free
field (10). c37: sowing with no seed carried takes it from one's own store (or one open to one) when
there is a free field to sow; otherwise it says to keep some back from a harvest or trade for seeds.
3-year bots: 540 (543).

**Loop, round 27 (c37): world2 refused 17.7%, no deaths; the sowing refusals are gone. Crops taken
from others' fields rose 3, 23, 34 a piece: harvest time and talk of winter, nearly all minds of their
own reaping strangers' fields by name. Their own doing, and it works as meant: Brosh confronted Tho,
who apologised and paid the grain back over the next days. Left alone. c38: "slaughter" of a wild
beast one does not keep (9, "you keep no deer") hunts it; of a tame kind one does not keep, says what
one keeps. 1-year bots: 421 (413).

**Loop, round 28 (c38): winter; world2 refused 18.6%; four killed by wolves, all bots in one corner,
one resting alone at home. c39: walls keep wolves out (a finished shelter's tile is out of their
reach; said in the rules line). Bots that kept company or went home when a pack was near were tried
and undone (3-year bots 520 against 540: the running cost them work, and wolves kill few bots). Kept:
3-year bots, 6 seeds, 1105 (1108).

**Loop, round 29 (c39): world2 refused 16.0%, the lowest yet; one killed by wolves (four before).
Top: smoked fish short of fish (16), game hunted out (27 deer and boar). A craft short of fish went
fishing for 8 hours whatever was needed: bare-handed that brings about one, the recipe wants two, so
the craft failed after the trip. c40: the trip is as long as the catch is likely to take, within a day,
else none; and with no line or net the refusal says bare hands catch about one a day. Bots: unchanged.

**Loop, round 30 (c40): the smoked-fish refusals are gone; world2 refused 21.9% (a new season). Top:
flint sickle short of flint (19): a craft fetched what the land gives only from in sight, and flint
lies in few places. c41: a craft short of it goes to a remembered place up to 30 steps off and
gathers it there. 3-year bots: 541 (527).

**Loop, round 31 (c42): the first round on one world. world2 refused 11.0% under c41 (1,579 answers,
mostly the free tiers while Kaggle's day was spent). Top: "there is no way to the stone at (41, 48)"
(175 on 2026-10-02): find() offered stone in the heart of a mountain, tiles ringed by impassable land,
and the retries picked others like it. c42: find() offers only tiles one can stand on or beside; when no
stone lies within the usual search, the refusal names the nearest reachable one and its distance
("gather with that x and y to walk there, or trade for it"); the people there live 26-35 steps from any.
3-year bots, 6 seeds: 1089 (1109), seeds 4-6 level (571 against 568), 1 and 3 lower: kept as noise, to
be judged on the bot farm's wider read (tools/bot_stats.py), its first use.

**Loop, round 32 (c43, mode 3): the first round read from the long land and the bot farm.** The long
land (bots only, never reset) grew to 684 by year 55, then shrank to 156 by year 156: births fell to
about none from year 40 while deaths were old age. Not food: a housing lock. Of 124 adults, 107 had no
home of their own (the bots' rule for a child), most living in a parent's shelter, and a couple settled
for the partner's home even when that was the partner's parent's; every attempt to build failed with
"no fitting place beside you" in settlements packed with 5,831 buildings, 3,015 of them the dead's
with no heir, locked for ever. Game also never came back: a new herd needed a tile 12 steps from
everyone, and none was left once 600 people spread out (beasts 0 from year 55 to 80). c43: what the
dead leave to no heir stands empty, anyone may claim it (`claim`, shown in the surroundings as "empty
since X died: claim it"), and left empty it weathers 3 a season and falls to ruin, its goods on the
ground and its place free (monuments never); a build with no room beside one looks up to 6 steps off;
a couple's home must be one of theirs; bots claim an empty shelter or field before building one; a new
herd comes to the wildest of 60 places, at least 5 steps from anyone; a cloak can be plaited from 6
fibre and a rope (cordage), for the hide that runs out (the farm's top refusal, 171,565 "cloak needs 3
hide" in 1,996 worlds); and a refusal met twice in three days is said back plainly ("Tried more than
once lately, and it could not be done: hunt (3 times): ..."). The long land's year-156 state run a year
under c43: homeless adults 107 to 8, births 68 (about none before), alive 156 to 219, 1,384 empty
buildings fallen. A crash found on the way: a model's go step with x and no y broke every world2 piece
for 21 hours (hotfix #130); Kaggle pieces that fail now hand two hours to the free tiers rather than
retrying every 12 minutes (that loop spent about an hour of the week's GPU on nothing).

