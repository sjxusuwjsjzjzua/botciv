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
- `tools/api_probe.py` — a few real prompts per model.
- Tests: `python -m unittest discover -s tests -t .`
- Workflows: `ci.yml` (tests, key scan), `dev.yml` (`[probe]` or `[world]`
  in a commit message on a `claude/*` branch), `world.yml` (the living
  world: schedule and manual runs, `world` branch, Pages).
