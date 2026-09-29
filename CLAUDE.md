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
- Status: building, open-ended. **Start every session with
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

- `botciv/` — engine (`engine.py`), world state (`world.py`), prompts
  (`prompt.py`), Gemini gateway (`gateway.py`), minds (`minds/`), runner
  (`run.py`), chronicle, viewer builder (`site.py`, `viewer.html`).
- `tools/tune.py` — bots-only runs for tuning the ecology.
- `tools/balance.py` — bots-only worlds across seeds against balance targets
  (see `docs/balance.md`); run it before and after any rules change. Bot
  runs are the fast loop: most engine refusals the bots hit, the people hit
  too. `--config configs/large.toml` for a 100-person land.
- `tools/health.py` — first look each iteration: who lives, how people die,
  tokens per model, refusals, which rules version is deciding.
- `tools/ideas.py` — what the people want that the world does not offer yet.
- `tools/inspect_world.py` — decisions, thoughts and failures, per person.
- `tools/advance.py` — the long, self-chaining world runs used by `world.yml`.
- `tools/api_probe.py` — a few real prompts per model.
- Tests: `python -m unittest discover -s tests -t .`
- Workflows: `ci.yml` (tests, key scan), `dev.yml` (`[probe]` or `[world]`
  in a commit message on a `claude/*` branch), `world.yml` (the living
  world, always running, `world` branch), `pages.yml` (the viewer).

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
