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

**Current mode: 2** (set 2026-09-29).

| Mode | The world | Iteration | Scheduled sessions |
|---|---|---|---|
| 1 keep alive | Actions only | none | one a day: health check only |
| 2 periodic | Actions only | one change per session | every 6 hours |
| 3 continuous | Actions; `tools/run_local.py` only if Actions is stuck | back to back, bot worlds for every rules change | every 1–2 hours, or one working session |
| 4 burn | as 3 | parallel: several mechanics at once in worktrees or sibling sessions, wide bot sweeps, `[world]` dev trials | as 3, plus parallel agents |

- **Mode 1.** Check only: `git log origin/world -1` within 2 hours, a
  `world.yml` run in progress or queued. If stale, dispatch `world.yml`
  (or find why it fails) and report; otherwise end at once. Read no
  decisions, change no code.
- **Mode 2.** One pass of the loop (section 3) and end: `tools/health.py`,
  `tools/ideas.py`, pick the single worst failure (or nothing, if nothing is
  failing), build, test, one balance seed set when rules change (a second
  only if the result is borderline), ship, record, update section 10.
- **Mode 3.** Sections 3–8 in full, iteration after iteration; two or three
  seed sets and the 100-person land when crowds matter; confirm each
  handover.
- **Mode 4.** Mode 3, and split independent work across worktree agents or
  sibling sessions (one mechanic each, proven on bots in its own
  worktree); merge one at a time, re-running balance after each merge.

**Setting a mode** (the session the owner tells): write it on the "Current
mode" line above and ship that; list the routines (`list_triggers`), delete
those of the old mode, create the new mode's routine as a fresh-session
routine whose prompt is "Read CLAUDE.md and docs/process.md and do one
mode-N session", and stop any local runner (`touch .world-stop`) unless in
mode 3 or 4 with Actions stuck. Then end the session.

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
  it holds a lock the Actions runs respect.
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
   the CI `test` job to pass, merge (merge commit).
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

## 10. Where things stand (2026-09-28)

- Rules: w14 took over at 20:48 UTC (confirmed: 94 of the last 130
  decisions under w14); w15 (a self that changes, lines kept for life)
  merged at 21:23; w16 (food at one's feet, crafts worth trying) merged at
  22:07; w17 (hearsay carried by speech) merged at 22:30; w18 (sowing
  where no farm stands builds one) merged at 22:28; w19 (no one idle for
  hours waiting on their own answer) merged at 22:33 and runs; w20 (things
  left on the ground weather away) follows. GitHub's runners were stuck in
  queue from 21:46, so the world is being advanced by `tools/run_local.py`
  from a cloud session (it holds the lock; Actions stands aside).
  **First job of the next session: confirm with `tools/health.py` that
  decisions are under the newest rules version, and fix the handover if
  not.** (A piece's decisions are committed when the piece ends, so the
  new version appears in the logs about half an hour after a run starts.)
- The live world: summer of year 5, 13 people, no deaths in the ten days
  since w16 (26 of 29 deaths ever were starvation). Under w19 the new
  waste was take and drop (36% of decisions); w20 answers it. No births
  yet, and no one has ever pledged or asked for a child. Strangers keep arriving.
- Balance (bots, 6 seeds × 4 years): 5/6 targets; no killings;
  population dips to 7 in the hungry gap.
- In crowds (100 bots) raiders do as well as foragers: taking back needs
  one's people beside the thief. Groups could change that; bots don't form
  them.
- Six seeds are noisy (one extra random draw moved planners' worth 123 →
  66): check a second seed set (7–12) before believing a difference.
- Fish are 2% of the people's choices, so overfishing can wait. No one
  has smoked or planted much; the people's winter is the thing to watch.
- Next, in order (`docs/mechanics.md`): children who depend on their
  parents; fish that can be overfished; sickness; standing offers at a place (markets). The
  people's recurring wishes: bone needle and clothing, spears, nets (these
  exist as hidden recipes; check whether discovery is too hard), healing,
  a proper home for a family.
