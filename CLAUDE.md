# botciv — instructions for Claude sessions

**This repo is public.** Everything committed, and every Actions log, is
readable by anyone.

- **Never write the Gemini API key into any file, commit, log line or
  URL.** In Actions it comes from the repository secret `GEMINIAPI`,
  mapped to the `GEMINI_API_KEY` environment variable. Send it as the
  `x-goog-api-key` header, never as a `?key=` query string.
- Never add a workflow triggered by `pull_request_target`.
- Nothing personal about the owner goes in this repo.
- [PLAN.md](PLAN.md) is the design. The rule that overrides the others:
  the engine owns world state; the model only chooses actions.
- The people in the world must not learn they are simulated: prompts never
  say simulation, agent, game, turn or tick (a test checks this).
- Status: building. The owner gave broad latitude to change the design.

## Layout

- `botciv/` — engine (`engine.py`), world state (`world.py`), prompts
  (`prompt.py`), Gemini gateway (`gateway.py`), minds (`minds/`), runner
  (`run.py`), chronicle, viewer builder (`site.py`, `viewer.html`).
- `tools/tune.py` — bots-only runs for tuning the ecology.
- `tools/ideas.py` — what the people want that the world does not offer yet.
- `tools/advance.py` — the long, self-chaining world runs used by `world.yml`.
- `tools/api_probe.py` — a few real prompts per model.
- Tests: `python -m unittest discover -s tests -t .`
- Workflows: `ci.yml` (tests, key scan), `dev.yml` (`[probe]` or `[world]`
  in a commit message on a `claude/*` branch), `world.yml` (the living
  world, always running, `world` branch), `pages.yml` (the viewer).

## Iterating

The owner wants an open-ended world where some people thrive and gather
wealth and power while others barely get by, grown version by version, and
leaves the choices to you. Each iteration:

1. Read the live world: `git fetch origin world`, then
   `python tools/ideas.py --dir <checkout>/world` and the viewer data.
2. Build what the people want most (their `idea`s, repeated deeds, refused
   choices) when it fits the rules; add your own depth too. Bump
   `RULES_VERSION` in `prompt.py` when the prompt or rules change.
   **Think each one through, don't just add it.** For every feature, new or
   old, check the whole chain: does the problem it answers exist in the
   engine (smoking only matters if food rots)? Can the people perceive it
   (rot was silent until w10)? Does it pay off at the right size (discovery
   so easy no one needs teaching makes knowledge worthless)? Can the viewer
   or the logs measure whether it changed anything? Measure before and
   after with `tools/tune.py` or the live logs, and fix the weakest link,
   even when no one asked for it.
3. When an idea becomes real, add it to `botciv/realized.py`: the world
   credits it once, to whoever alive imagined it first, inside the world.
   Add a line to the version log in PLAN.md (section 6a).
4. Merge to main: the running world hands over to the new code within the
   hour. Keep the free-tier quota fully used.
