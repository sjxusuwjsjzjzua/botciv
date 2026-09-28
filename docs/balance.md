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

## Rounds, later the same day (rules w11 → w12)

| Round | Change | Targets | What it showed |
|---|---|---|---|
| 4 | planners also trade surplus grain, borrow against promises, found a household group, invite kin, open their store to it, teach partner and children; tit-for-tat bots join invitations and repay promises | 4/6 | Planners' edge collapsed (18 vs 16). Not the social logic: the engine kept refusing them. |
| 5 | fix: `plant` used the first farm beside you even when it was planted (121 refusals in two years); `build` with no place named only tried your own tile (77 "already a … there"). Now: the free farm, your own first; the first fitting tile beside you | 6/6 | Planners 52 vs 34, births 4 a year. The live people hit the same refusals ("already a shelter there", 22 in w8). |
| 6 | fix: a walk with no way through was refused outright (167 refusals); now you walk as near as you can get and are told so. Bots stop asking someone already expecting | 5/6 | Planners 96 vs 36, planners starving 26% (was 37%). The hungry-gap dip to 6 remains on one seed. |

## A hundred people (`configs/large.toml`)

A 64×64 land (about seven times the area) with 100 people, 310 bushes, 20
herds and 6 wolf packs. Two things did not scale and were fixed: world
generation drew one river whatever the size (so rich soil, which lies by
water, was scarce: 27 tiles for 100 people) and one wolf pack whatever
`wolf_packs` said. Rivers now scale with the width, and strangers arrive in
proportion to the length of the land's edge. A bot year takes about 25
seconds.

Four years, two seeds, rules w12: 6/6 targets. Population 55–93, starvation
37% of deaths, 3.4 births a year, Gini 0.55, planners worth 68 vs 29 for
foragers. The first winter is the hardest (100 → about 60). In a crowded
land **raiders starve least and live longest** (15% starved, 728 thefts a
run): a theft costs a bot nothing but a line in the victim's memory. Left
as a question for the people: language-model minds remember who robbed
them, and whether they punish it is theirs to decide.

Every Pages publish rebuilds this world under the current rules at
`/botciv/large/`.

**Open:** the population dips to 5–7 in some runs, in the hungry gap from
late winter into spring (starvation after stores run out, before bushes
regrow), and refills within days from strangers. Nothing died out in 60
seed-years. Left as it is: a hard spring is part of the world.

**Not yet exercised by bots:** deals, promises, groups, teaching, wolves
fought on purpose. Bots never trade; the live world's language-model people
do.
