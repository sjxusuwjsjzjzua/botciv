# Speed: handover for the session that takes it on

Written 2026-10-10 at the end of the long mode-3 session (process.md rounds 61-71), for the next session, which the
owner opened to do the speed work.

## Why it matters

The prehistory (grand.md Phase 8: 50-100 bot years of world4 before the minds are seated) needs the Phase 1.3
**speed gate**: a 2,000-person, 192x192 continent advances **a year in 3 minutes or less** on an Actions runner.
A year is 40 days = 480 world hours, so the gate is **0.375 s a world hour**.

## Where it stands (main at a40566b, rules c88)

- `python tools/speed_profile.py` in a cloud session: **10 days in 115.8 s, 0.965 s a world hour**, about
  **2.6x short** of the gate. Actions runners may be a little faster than this container, so measure on a runner too
  before believing the gap: run `speed_profile.py` in a workflow once (e.g. a `[probe]`-style step in `dev.yml`).
- Round 67 took it from 138.6 s with no change to results:
  - `riding()` asked every building in the land on each step anyone walked (12 s): now `w.owned(p.id)`.
  - `by_name` scanned everyone ever born: now a name index, rebuilt when someone is born.
  - `remember` checked every herd for every person: now herds by 16x16 cell, visited in w.herds order.
- Tried and dropped, no gain: an index of the tiles in sight that hold a deposit or building (most tiles in sight
  hold something); integer keys in the A* path search (`x * H + y` keeps tie order; 0.2 s).

## The profile now (10 days, sorted by own time; cumulative in brackets)

| Where | Own s | Notes |
|---|---|---|
| `dict.get` (54 M calls) | 10.9 | spread through find, building_near, remember, path |
| `engine.path` (A*, 39 k calls) | 9.9 (15.0) | already hand-inlined; the searches themselves are long |
| `engine.remember` | 6.9 (18.0) | every 3 hours, every person scans their sight square, then prunes `known` to 160 with heapq.nsmallest (4 M key calls) |
| `world.near` (237 k calls) | 6.5 (8.9) | 8x8 grid of sets; called from everywhere |
| `acts.find` (73 k calls) | 6.5 (14.8) | scans the sight square for a tile yielding an item, then remembered places |
| `acts.building_near` (17 k calls) | 5.7 (13.3) | scans the sight square **and parses every key of p.known with unkey()** each call |
| bot `decide` / `one` | (47) | the bot minds as a whole: 40% of the time |
| `run_person` | (44) | doing acts |

By area: bot decisions ~40%, acting ~38% (walking, gathering), remember ~15%.

## Where a structural gain could come from (ideas, not tested)

1. **Think less often.** A bot re-chooses only when its plan ends or something wakes it, but the urgent checks in
   `BotMind.one` (answer, danger, guard, hunger, night...) run every time. Profile `one` by goal; cache what
   does not change within a day (vocation goals, stores known).
2. **Remember less often or less.** `remember` every 3 hours for everyone: every 6 for the idle, or only for
   those who moved since the last time; prune `known` with hysteresis (to 140 when over 160) instead of every
   call. This changes results: measure it on the bot farm, not with the hash.
3. **p.known as tile indices.** `building_near` and `find` parse `"x,y"` keys again on every call (3.6 M unkey
   calls). Keep a per-person set of remembered tile indices beside `known`, updated where `known` is written.
4. **Fewer, shorter path searches.** Cache paths per (start, goal) for the hour; bound the search by
   the straight-line distance times a factor before falling back to the whole land; or path on a coarser grid
   for long walks.
5. **Run seeds in parallel** for the bot farm and civ_balance (multiprocessing): no gain for one world, but the
   prehistory could run several candidate worlds at once and keep the best.
6. **PyPy** for the bots-only prehistory, if the code runs under it unchanged (no numpy in civ/): often 3-5x on
   loops like these. Cheap to try first: `pypy3 tools/speed_profile.py`.

## How to check a change

- **Same results** (pure speed changes): `python tools/same_world.py` before and after (or pass another checkout
  as the argument); both hashes must match. Baseline on main a40566b: `d1c04fbf26c8 alive 122 | e6c617858e08 alive 543`.
  Bot worlds are deterministic; the continent is deterministic across processes since round 67 fixed fishing's
  choice of water (`max()` over a set of strings). If a hash differs, find the first hour two runs part
  (dump `w.to_dict()` each hour and diff, as in round 67).
- **Changed results** (thinking or remembering less): the bot farm and `tools/civ_balance.py`, 12 old-land seeds x 3
  years and 4 continent seeds (`--realm --people 1200 --size 176`) x 3 years. The noise floor (balance.md): one extra
  random draw moves births 5% in 12 seeds, so read smaller differences as noise.
- **Speed**: `python tools/speed_profile.py` (and `--sort cumulative`).
- `python -m unittest discover -s tests -t .`; the prompt-budget test (`test_civ_c60`, p95 10,500 characters) moves
  with world generation, so a change to generation can fail it without touching prompts.

## Other state worth knowing (the rest of the long session)

- Rules c81-c88 shipped: order tasks (and the answer schema's fields ordered verb first: Gemini wrote them
  alphabetically), spoils divided, tenancy, envoys, territory (trespass between peoples, leave, tolls), pack beasts,
  settlements, the war leader's and trader's views, model by seat; the atlas draws realms' borders.
- Mode 3 is set (process.md section 0); no routine runs. world2 hands over to new rules within the hour.
- Open questions recorded in process.md rounds 62-66: an aimed gather reaps any ripe field beside the reaper
  (fixing it costs 7% of births, unexplained); money in metal waits until bots make metal (5-48 copper a world).
- Roadmap §5: what remains before world4 is this speed gate (Phase 8's prehistory) and the week of dev pieces with
  minds seated (Phase 7's gate: an alliance, treaty or war decided by an AI person).
