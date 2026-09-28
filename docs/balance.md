# Balance with bots

`python tools/balance.py` runs bots-only worlds across seeds and checks them
against targets for a world worth watching: the people never die out, the
population holds about 8–22, starvation is common but not nearly every
death, children are born, wealth is unequal (Gini 0.3–0.6), and planning
pays (planners hold more than careless foragers). Bots are not the people:
they test that the world is stable and that its features work and matter.
The interesting behaviour comes from the language-model runs.

Mixed bots give each person one of four minds: a careless forager, a
tit-for-tat neighbour, a planner (keeps a store, farms, sows grain kept
back, smokes surplus, pledges), and a raider (steals from neighbours when
hungry, breaks into stores when desperate).

## Rounds, 2026-09-28 (rules w10 → w11)

| Round | Change | Targets | What it showed |
|---|---|---|---|
| 0 | baseline, 6 seeds × 4 years | 2/6 | Planners starved most (75%) and were poorest: 85 stores built, **no farm ever built**. |
| 1 | fix: `build farm` was read as "build grain" (the gather alias), so no one, bots or people, could ever build a farm | 3/6 | 73 farms, but farms yielded little: seeds are scarce and a harvest gave no seed back. |
| 2 | grain kept back can be sown again; planner keeps seed grain and harvests its own crop first | 6/6 | Starvation 71% → 45% of deaths, births 3.5 a year, planners worth 70 vs 41 for foragers. |
| 2b | 10 seeds × 6 years, each mind alone | — | Foragers alone fall to 3 people and have no children; tit-for-tat alone starves 72%; planners alone thrive (5/5). Outcomes depend on behaviour, as they should. |
| 3 | raiders join the mix (10 seeds × 6 years) | 5/6 | 278 thefts a run; planners still richest (42 vs 17), raiders second (22) and longest-lived: property mostly holds, taking partly pays. |

**Open:** the population dips to 5–7 in some runs, in the hungry gap from
late winter into spring (starvation after stores run out, before bushes
regrow), and refills within days from strangers. Nothing died out in 60
seed-years. Left as it is: a hard spring is part of the world.

**Not yet exercised by bots:** deals, promises, groups, teaching, wolves
fought on purpose. Bots never trade; the live world's language-model people
do.
