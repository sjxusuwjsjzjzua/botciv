# botciv — instructions for Claude sessions

**This repo is public.** Everything committed, and every Actions log, is
readable by anyone.

- **Never write the Gemini API key into any file, commit, log line or
  URL.** In Actions it comes from the repository secret `GEMINIAPI`,
  mapped to the `GEMINI_API_KEY` environment variable. Send it as the
  `x-goog-api-key` header, never as a `?key=` query string.
- The same goes for the Groq key (`GROQ_API_KEY`; in Actions from the
  secret `Djxuzusjsnzja`, in cloud sessions from the environment): bearer
  header only, scrubbed from logs, and the CI key scan catches `gsk_` keys.
- Never add a workflow triggered by `pull_request_target`.
- Nothing personal about the owner goes in this repo.
- [PLAN.md](PLAN.md) is the design. The rule that overrides the others:
  the engine owns world state; the model only chooses actions.
- The people in the world must not learn they are simulated: prompts never
  say simulation, agent, game, turn or tick (a test checks this).
- Status: building, open-ended. **Where things stand and what comes next: [docs/roadmap.md](docs/roadmap.md)**
  (section 5 is the ordered list of next steps). **The grand world** (peoples, lords, merchants, raiders, war,
  AI people in the seats that matter) is planned in [docs/grand.md](docs/grand.md). **Start every session with
  [docs/process.md](docs/process.md)**: the owner's intent, where work
  comes from, the iteration loop, bots, token budget, running the world,
  shipping, and where things stand.
- **Modes.** The owner may say "mode 1" to "mode 4": how many Claude tokens
  to spend (keep alive / periodic / continuous / burn). What each means and
  how to set one: [docs/process.md](docs/process.md) section 0.

## The owner's intent, in brief

The owner is deliberately vague: this is a sandbox that grows, and
deciding what to build is your job. You build **mechanics that make things
possible** (property, credit, feuds, law, markets, dynasties...), never
scripted outcomes; the people decide what happens. Work comes from three
places: the people's `idea`s and refused choices, your own gap analysis
against [docs/mechanics.md](docs/mechanics.md), and failures read from the
live world's dead. Test every mechanic cheaply with bots first
(`tools/balance.py`), think each change through, and keep prompts light:
tokens are the budget, and everything runs on the free tier.

## Layout

- `botciv/` — engine (`engine.py`), world state (`world.py`), the crafts as data (`tech.py`), prompts
  (`prompt.py`), Gemini gateway (`gateway.py`), minds (`minds/`), runner
  (`run.py`), chronicle, viewer builder (`site.py`, `viewer.html`).
- `civ/` — **the second generation** (docs/v2.md, docs/civilization.md): content as data
  (`content/`: 126 items, 45 crafts, 103 recipes, 44 buildings by role, to era 4), large lands
  (`gen.py`), engine and one executor for every mind (`engine.py`, `acts.py`, `society.py`),
  recipe planner (`plan.py`), bot people and async language-model people (`minds/`), prompt
  (`prompt.py`), runner (`run.py`), viewer (`site.py` builds the site, format 3; `viewer/`: the app, docs/viewer.md). `tools/civ_balance.py`
  runs bots-only civ worlds. **One world** runs: `world2` (`world2.yml`, hourly: a 45-minute
  piece on a Kaggle GPU while its weekly hours last, otherwise about 45 minutes on the free
  Gemini/Groq tiers through `tools/advance_civ.py`; one workflow, so the two never overlap).
  The first world (botciv, the `world` branch) and world3 (the `world3` branch) are retired
  (2026-10-02): their workflows are gone, their history stays.
- `tools/bot_stats.py` — the bot farm's read (`bots.yml`, the `bots` branch): bots-only civ worlds
  on fresh seeds, without end, on main's code; by rules version, mean ± error, and the new version
  against the one before. The wide balance read; a session's own 3-seed run is the quick one.
- `tools/tune.py` — bots-only runs for tuning the ecology.
- `tools/balance.py` — bots-only worlds across seeds against balance targets
  (see `docs/balance.md`); run it before and after any rules change. Bot
  runs are the fast loop: most engine refusals the bots hit, the people hit
  too. `--config configs/large.toml` for a 100-person land.
- `tools/health.py` — first look each iteration: who lives, how people die,
  tokens per model, refusals, which rules version is deciding.
- `tools/ideas.py` — what the people want that the world does not offer yet.
- `tools/inspect_world.py` — decisions, thoughts and failures, per person.
- `tools/advance.py` — the long, self-chaining runs of the retired first world.
- `tools/api_probe.py` — a few real prompts per model.
- Tests: `python -m unittest discover -s tests -t .`
- Workflows: `ci.yml` (tests, key scan), `dev.yml` (`[probe]` or `[world]`
  in a commit message on a `claude/*` branch), `world2.yml` (the
  world), `bots.yml` (the bot farm) and `botworld.yml` (the long land, bots only, never reset,
  viewer at /long/; both pause with the repository variable `BOTS_OFF=yes`),
  `pages.yml` (the viewer), `automerge.yml` (merges a tested
  `claude/auto-*` branch into main: how scheduled sessions ship),
  `kaggle-world.yml` (by hand: an hour of the world on a Kaggle GPU).

## Iterating

The full loop is in [docs/process.md](docs/process.md) section 3. In short:

1. Read the live world (`tools/health.py`, `tools/ideas.py`, a rebuilt
   prompt, the last decisions of the dead).
2. Pick the worst failure, the most wanted idea, or the next gap in
   `docs/mechanics.md`. **Think each one through, don't just add it**: does
   the problem exist in the engine, can the people perceive it, does it pay
   off at the right size, can it be measured, what does it cost in tokens?
3. Balance run before; build (engine, rules text, verbs, bots, viewer);
   tests; balance run after. Undo what made things worse.
4. Bump `RULES_VERSION` in `prompt.py` when prompt or rules change; add a
   line to PLAN.md section 6a; record numbers in `docs/balance.md`; add
   people's ideas made real to `botciv/realized.py`.
5. PR to main, merge when CI passes; the running world hands over within
   the hour. Confirm it with `tools/health.py`. Keep the free-tier quota
   fully used.
