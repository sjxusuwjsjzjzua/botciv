---
name: world-check
description: Cheap health check of the living botciv world (is it advancing, on which rules, is a run going). Use at the start of every scheduled botciv session, for mode 1, or when asked whether the world is running.
---

# World check (a few tool calls; stop as soon as it is healthy)

1. `git fetch -q origin world main && git log origin/world -3 --format='%h %ci %s'`
   Healthy: a commit within the last 2 hours.
2. Rules in use: `git show origin/world:world/last_run.md | head -3`, and if deciding
   anything, `tools/health.py` on an extracted copy (`docs/process.md` section 3, step 1).
3. If stale: list `world.yml` runs (GitHub MCP `actions_list`, resource `world.yml`).
   - Queued for a long time: GitHub's runners are stuck; report it. Only in mode 3 or 4
     carry the world with `tools/run_local.py` (`docs/process.md` section 7, traps included).
   - Failed: read the job log, fix on a `claude/*` branch, ship.
   - None running or queued: dispatch `world.yml` (`actions_run_trigger`).
   - `world/LOCK` on the world branch held by "local" with `until` in the future: a local
     runner has it; if none is alive, the lock lapses by itself within 50 minutes.
4. Report in two or three lines: healthy or not, rules version, what you did.
