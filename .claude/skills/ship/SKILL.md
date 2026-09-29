---
name: ship
description: Ship a botciv change to main - commit, push, PR, verify, merge, and confirm the living world hands over. Use whenever a botciv change is ready to merge.
---

# Ship

1. On the session's `claude/*` branch, started from current `main` (if its PR was
   merged: `git fetch origin main && git checkout -B <branch> origin/main`).
2. Rules or prompt changed: bump `RULES_VERSION` in `botciv/prompt.py`; add a line to
   PLAN.md 6a; numbers to `docs/balance.md`; update `docs/mechanics.md` and
   `docs/process.md` section 10; people's ideas made real go in `botciv/realized.py`.
3. Commit: what changed, why, and the numbers that justify it. Push.
4. PR to `main` (body: what, why, measured, tests; end with the attribution the session
   gives). Merge when the CI `test` job passes. If GitHub's runners sit queued, run CI's
   own steps on the pushed commit and merge on those:
   - `git grep -nE 'AIza[0-9A-Za-z_-]{30,}' -- .` finds nothing (exit 1)
   - `python -m unittest discover -s tests -t . -q` passes (Python 3.11)
   - merge with `merge_method: merge` and `expectedHeadSha` = that commit.
5. Reset the branch to the new `main` and push it, so nothing is left unpushed.
6. Handover: `world.yml` checks main after each half-hour piece; within about an hour
   `tools/health.py` should show decisions under the new rules version. In mode 2 leave
   that check to the next scheduled session (write it in section 10).

Never write the Gemini key anywhere; never add a `pull_request_target` workflow.
