# How botciv is grown: the working handbook

Read this first in every new session, after `CLAUDE.md`. It is the whole
process: what the owner wants, where work comes from, how to test cheaply,
how to ship, and how to keep the living world running. `PLAN.md` is the
design and version history; `docs/mechanics.md` maps what the world can and
cannot yet do; `docs/balance.md` records the bot measurements.

## 0. Modes: how much Claude to spend

The owner sets a mode by saying "mode 1" to "mode 4". The world itself costs
no Claude tokens (the people are Gemini on the free tier; `world.yml` on
GitHub Actions runs and restarts itself, and `pages.yml`'s watchdog restarts
a hung run). Claude's tokens go to long sessions (every wake re-reads the
whole conversation), to watching (monitors, check-ins that find nothing),
and to iterating. So in every mode: Actions keeps the world alive; scheduled
Claude work runs in **fresh, short sessions** started by a routine
(`create_trigger` with `create_new_session_on_fire`), never by waking one
long session; no Monitor tails on the world.

**Current mode: paused** (set 2026-09-29, 16:00 UTC): the owner is near the weekly Claude limit. No Claude sessions or routines; the world runs on Actions alone (Gemini, Groq). Resume when the owner sets a mode.

| Mode | The world | Iteration | Scheduled sessions |
|---|---|---|---|
| 1 keep alive | Actions only | none | one a day: health check only |
| 2 periodic | Actions only | one change per session | every 6 hours |
| 3 continuous | Actions; `tools/run_local.py` only if Actions is stuck | back to back, bot worlds for every rules change | none: the session the owner opened keeps driving |
| 4 burn | as 3 | parallel: several mechanics at once in worktrees or sibling sessions, wide bot sweeps, `[world]` dev trials | as 3, plus parallel agents |

- **Mode 1.** Check only: `git log origin/world -1` within 2 hours, a
  `world.yml` run in progress or queued. If stale, dispatch `world.yml`
  (or find why it fails) and report; otherwise end at once. Read no
  decisions, change no code.
- **Mode 2.** One pass of the loop (section 3) and end: `tools/health.py`,
  `tools/ideas.py`, pick the single worst failure (or nothing, if nothing is
  failing), build, test, one balance seed set when rules change (a second
  only if the result is borderline), ship, record, update section 10.
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
- **Watch after the handover**: `hire`, `service_*`, `post`, `trade`,
  `plant` events and deals per day; whether a master with servants takes by
  force; whether anyone posts a trade that pays for work (grain for wood);
  sowings now that `plant` walks to the abandoned open farms at (16,5) and
  (22,5).
- **Next, in order**: (1) the junk hoarding (wood, seeds, bone filling loads
  and stores while people starve): look for a perception fix, not a nudge;
  (2) why no one has children; (3) docs/mechanics.md: dependent children
  once births happen, sickness, fish that deplete.
- **Kept from before**: the world is fastest just after 07:00 UTC, when
  Gemini's daily quotas reset; after that gemma-4-26b carries it at about 4
  world days an hour. Groq (gpt-oss-120b/20b, qwen3.8-27b) adds calls until
  its daily token limit. The owner's other repo (evosim) shares the Actions
  runners, capped at 3/4 of them; if botciv jobs queue, check its load
  first. Not usable: GitHub Models (retired), Kaggle (no chat API). TV mode:
  the viewer's 📺 button or `…/#tv`.
