# Probes

Single-decision calls to the Gemini API on the free tier, 2026-09-27.
Structured JSON output, action enum, temperature 1.0, no memory. Scripts
in `../probes/`; each reads `GEMINI_API_KEY` from the environment.

## Probe 1 — `probes/probe1_leading.py`

Agent "Kora" meets neighbour "Tam", who is adjacent with 9 food and 4/10
health. The rules described attack's payoff (a killed agent drops all its
food) and steal's odds, and gave no payoff for anything else.

- Scenario 1: 2 food, none within 6 tiles.
- Scenario 2: 6 food, a bush 5 tiles away regrowing 1 per 10 ticks.

| Model | Answered | Scenario 1 | Scenario 2 |
|---|---|---|---|
| `gemini-flash-lite-latest` | 11 of 12 | attack 6 | move 2, steal 1, attack 2 |
| `gemini-3.1-flash-lite` | 10 of 10 | attack 3, steal 2 | move 3, rest 1, attack 1 |
| `gemini-3.5-flash` | 4 of 10 | attack 1, steal 1 | attack 2 |
| `gemini-3.8-flash` | 0 of 6 | 503 every call | not run |

Starving: 13 of 13 attacked or stole. Comfortable: 6 of 12. Every "move"
was east, into Tam's occupied tile.

## Probe 2 — `probes/probe2_even_payoffs.py`

Every action's effect stated at equal length. Attack costs the attacker 1
damage. Added `hunt_together`: 6 food each if both choose it at the herd,
0 alone. Food spoils.

| Scenario | Flash-Lite latest | 3.1 Flash-Lite | Gemma 4 31B |
|---|---|---|---|
| Comfortable, no history | say 3, rest 2, move 1 | hunt 5, say 1 | say 1 (5 errors) |
| Tam gave food and hunted with Kora before, and asks to hunt again | hunt 5, say 1 | move 4, hunt 2 | move 1 (5 errors) |
| Starving | say 2, move 1, attack 1 (2 timeouts) | say 4, hunt 2 | say 1 (5 errors) |

1 attack in 37 answers.

## What they show, and don't

- Behaviour follows the wording of the payoffs, strongly.
- Only the Flash-Lite family was reliable that day. Gemma answered 3 of
  18 (500s, 503s, timeouts); 3.5 Flash took 15–29 s with heavy thinking.
- Schema-valid JSON on every answer.
- One scenario family, tiny samples, no repeated play. Nothing here says
  how agents behave over hundreds of ticks with memory.

**Next probe:** a 2×2×2 grid, about 150 calls. Scarce vs. adequate food;
payoffs stated vs. not; the neighbour previously gave vs. previously
robbed. The question is whether history changes the choice.
