---
name: world-check
description: Cheap health check of the living botciv world (is it advancing, on which rules, is a run going). Use at the start of every scheduled botciv session, for mode 1, or when asked whether the world is running.
---

# World check (one command; stop as soon as it is healthy)

1. `python tools/health.py` (fetches only the newest commit of `world2`). The first line says
   HEALTHY (a piece within 2 hours) or STALE, then the last piece's report, births, deaths,
   thefts and the people's top refusals of the last 3 world days. Exit code 2 when stale.
2. If stale: list `world2.yml` runs (GitHub MCP `actions_list`, resource `world2.yml`).
   - Queued for a long time: GitHub's runners are stuck; report it.
   - Failed: read the job log (`get_job_logs`, `failed_only`), fix, ship.
   - None running or queued: dispatch `world2.yml` (`actions_run_trigger`, ref `main`).
3. Report in two or three lines: healthy or not, rules version, what you did.
