---
name: mode
description: Set or run a botciv working mode. Use when the owner says "mode 1", "mode 2", "mode 3" or "mode 4" (keep alive / periodic / continuous / burn), asks to spend fewer or more tokens, or when a scheduled session is told to "do one mode-N session".
---

# Modes

The modes are defined in `docs/process.md` section 0; read it first. This is the procedure.

## Setting a mode (the owner said "mode N")

1. Write `**Current mode: N**` on the line in section 0, and ship it (use the `ship` skill).
2. `list_triggers`: delete the routines of the old mode (names start with "botciv mode").
3. Create the new mode's routine with `create_trigger`, `create_new_session_on_fire: true`,
   named "botciv mode N", prompt: "Read CLAUDE.md and docs/process.md, then do one
   mode-N session (the mode skill)." Cron (UTC, jittered minutes):
   - mode 1: `47 6 * * *` (daily)
   - mode 2: `47 */6 * * *`
   - mode 3: `47 */2 * * *` (or keep working in the session the owner opened)
   - mode 4: as mode 3; parallelise inside the session.
4. If a local runner is going and the mode is 1 or 2: `touch .world-stop`.
5. Tell the owner what is scheduled, then end. Do not stay to watch.

## Doing one scheduled session

- mode 1: the `world-check` skill, then end. No code, no reading decisions.
- mode 2: `world-check`; if healthy, one pass of the loop (`docs/process.md` section 3):
  `tools/health.py` and `tools/ideas.py`, pick the single worst failure or nothing, build,
  test, one balance seed set if rules change (a second only if borderline), ship, update
  section 10 with what you measured and what is next. Then end.
- mode 3/4: sections 3–8 in full, repeatedly; mode 4 splits independent mechanics across
  worktree agents and merges one at a time.

Never add Monitors or wake-ups inside a long session to wait for the world; the next
scheduled session will look.
