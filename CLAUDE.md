# botciv — instructions for Claude sessions

**This repo is public.** Everything committed, and every Actions log, is
readable by anyone.

- **Never write the Gemini API key into any file, commit, log line or
  URL.** The code reads `GEMINI_API_KEY` from the environment. In Actions
  that is set from the secret `GEMINIAPI`. Send it as
  the `x-goog-api-key` header, never as a `?key=` query string.
- Never add a workflow triggered by `pull_request_target`.
- Nothing personal about the owner goes in this repo.
- [PLAN.md](PLAN.md) is the design. The rule that overrides the others:
  the engine owns world state; the model only chooses actions.
- Status: planning. Build nothing until the owner says to start.
