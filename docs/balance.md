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

## What keeps theft in check (rules w13)

In the 100-bot world raiding paid best: a theft cost a bot nothing but a line
in the victim's memory. In life what stops it is the fear of retaliation, by
the one wronged, their friends, or whoever enforces a rule. The world should
not script that, but it must make it possible. Tracing the chain found two
gaps: **witnesses forgot** what they saw (only the victim remembered), and
**taking from a person was always the stealth roll**, recorded as theft, so a
group could not take back, fine or confiscate. Now witnesses remember, a
person's description says "has stolen from you" / "you have seen them
steal", and people standing together (a group, partners, kin, or anyone who
followed the target) take openly by force, seldom failing unless the target
has their own people beside them. The rules text says so. Whether a taking
is justice or robbery is left to the people.

Bots to test it: robbed tit-for-tat bots take back when their people are
beside the thief, strike back when as strong, and punish thieves they saw;
raiders pick targets with no one beside them.

| World | Before | After |
|---|---|---|
| small, 6 seeds × 4 years | about 180 thefts a run | 49 thefts, 26 taken back by force, 31 attacks; one seed four years without a death by hunger |
| 100 people, 2 seeds × 4 years | raiders second richest, starved least, lived 122 days | raiders poorest (worth 13 vs 35), lived 77 days; starvation 22% of deaths |

Deterrence emerged from the capabilities, not a rule against theft. With
language-model people, whether they use them is theirs to decide.

**Open:** the population dips to 5–7 in some runs, in the hungry gap from
late winter into spring (starvation after stores run out, before bushes
regrow), and refills within days from strangers. Nothing died out in 60
seed-years. Left as it is: a hard spring is part of the world.

**Not yet exercised by bots:** wolves fought on purpose. Planner bots now
form households, teach, lend grain on promises and name heirs; tit-for-tat
bots join and repay.

## Crops, heirs and feuds (rules w14)

A whole-world pass over what must be possible for property, family and
deterrence to emerge ([mechanics.md](mechanics.md)) found six gaps, all
closed in w14:

- **Crops as property.** A ripe farm was anyone's harvest and no one
  remembered who took it. Now its owner can open or close it like a store,
  and taking from a farm not open to you is remembered by the owner and
  anyone who sees it.
- **Buildings change hands** (`give` a store, farm or shelter): sale,
  dowry, tribute, a keeper's office.
- **Heirs by choice** (`bequeath`), before partner and children.
- **Partners can part.**
- **Kin remember a killer** (the feud, the oldest deterrent). Before, they
  were told and forgot.
- **Witnesses of breaking** remember it; a person seen leading a group of
  several is described as its leader.

The first bot run showed the danger of the feud: tit-for-tat bots struck
back for every theft, strikes killed, and each killing made new avengers
(7–22 people killed by people per run). Bots were changed to answer in
kind — goods taken are taken back, only blood is answered with blood. The
language-model people choose their own measure; the world only remembers.

| 6 seeds × 4 years | w13 bots | w14, blood for blood only |
|---|---|---|
| killed by people | a few a run | 0 |
| attacks | 31 | 0 |
| thefts / taken back by force | 49 / 26 | 615 / 426 |
| crops taken from closed farms | — | 910 |
| heirs named | — | 6 |
| starvation, share of deaths | 43% | 34% |
| planner vs forager worth | — | 77 vs 46; raiders 40 |

Thefts rose because crops and stores are now worth taking, and a taking is
mostly answered by taking back rather than by a blow. A middle way (one
beating per theft, never to the death) was tried and dropped: beaten
thieves' friends joined in, blows killed, and kin avenged the dead, 4 to 5
killings a run.

In the 100-person land (2 seeds × 4 years) taking back needs one's own
people beside the thief, and among strangers they seldom are: 37 of 480
thefts were taken back and raiders did as well as foragers (25 vs 26).
There, deterrence would have to come from groups. The capabilities exist;
the bots do not organise one.

## The load that starved people (rules w14)

In the live world 23 of 25 deaths were starvation, with 110 bushes and 756
berries on the land for five people. Reading the last decisions of the
dead: people picked up piles of wood (2 a piece, so ten fill a load of 20),
then could not pick a single berry. The world said only "There is nothing
there you can carry" (223 times in the log) and the prompt never said what
things weigh. 15 of the 23 who starved had hit their load in their last
four days. Now:

- the rules say what a person can carry and what things weigh, and the
  prompt says when a load is full;
- a refusal names the load and the heaviest things in it and what to do;
- a hungry person picking berries or grain, or catching fish, eats on the
  spot what they cannot carry, as anyone would;
- "take from the store" without naming a thing means food, and giving,
  taking, teaching, pledging or asking someone in sight but not beside you
  walks over to them first (these were refused by the hundred).

## Food at one's feet (rules w16)

Live world, day 157 of year 4: 26 of 29 deaths starvation. Bith, starving
(fullness 0), stood on 5 meat from their own hunt with a load of 35 of 35
(8 wood, 22 fibre); "take meat" was refused as too heavy and "eat meat"
as none carried. Now what a hungry person cannot carry they eat on the
spot, from the ground, a store or a hunt, and `eat` reaches food on the
ground beside them.

Bots, 6 seeds × 4 years, before → after: 5/6 targets both; starvation 34%
→ 35% of deaths; births 2.8 → 3.0 a year; planners' worth 77 → 123;
seed 5's lowest population 10 → 15. Bots seldom fill a load with wood, so
this mostly matters to the people; watch starvation in the live world.

## Hearsay (rules w17), and how noisy six seeds are

First, the noise: the w16 baseline with one extra random draw at the start
(nothing else changed) moved planners' worth 123 → 66, starvation 35% →
41% and births 3.0 → 2.5 a year. Differences smaller than that are not
evidence; use seeds 7–12 as a second set before believing a change.

| 6 seeds × 4 years | targets | starved | births/yr | planner worth | taken back |
|---|---|---|---|---|---|
| w16, seeds 1–6 | 5/6 | 35% | 3.0 | 123 | 458 |
| w16, seeds 7–12 | 6/6 | 37% | 2.1 | 105 | 224 |
| tell_of as a verb (1 h), bots tell once per wrong | 3/6 | 50% | 1.8 | 30 | 40 |
| control: bots wait 1 h instead of telling | 4/6 | 52% | 1.8 | 64 | – |
| hearsay in speech, bots act on it, 1–6 / 7–12 | 5/6, 4/6 | 43%, 42% | 2.0, 1.5 | 154, 117 | 375, 214 |
| **hearsay in speech, bots only pass it on**, 1–6 / 7–12 | 5/6, 5/6 | 40%, 41% | 2.4, 1.8 | 146, 63 | 369, 328 |

The engine change alone (bots never telling) reproduced w16 exactly. A
tit-for-tat bot pausing an hour after being wronged, with people about,
costs the ecology a great deal, so passing things on had to be as free as
speech. Bots that weighed hearsay (trusting less, taking back from those
they had heard of) had fewer children and did not take back more; what
hearsay should change is left to the people. In the 100-person land
(2 seeds) raiders' worth stayed level with foragers' (34 vs 35); taking
back by force stayed rare (30 → 38): hearsay alone does not organise
people against a thief.
