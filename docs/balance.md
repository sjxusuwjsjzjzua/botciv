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

## Sowing understood (rules w18)

Engine-only (refusals turned into what was meant). Bots, both seed sets:
identical to w17 (5/6 and 5/6), since bots build their farms first. Its
measure is the live world: plantings and grain eaten by the people.

## Idle while thinking (rules w19)

Live world, w14–w15 decisions (229): lag from question to answer applied
was 0 h for 95, 1 h for 31, 2 h for 24, 3 h for 79; "you are not doing
anything" was the commonest reason to decide (73). About 1.4 idle hours per
decision, with two to four decisions a person a day. The world now waits
for an idle person's answer after 1 hour (`idle_lag`), a busy person's
after 3. Measure: the same lag table for idle people under w19, and world
hours per piece (56 hours a piece before, on Gemma alone).

First w19 piece (local runner, 22:36–23:03, Gemma alone): 91 decisions,
52 world hours, about 3.4 calls a minute (before: about 3.5, 56 hours).
Lag 0 h 45%, 1 h 24%, 2 h 10%, 3 h 21% (before 41 / 14 / 10 / 34). The
3-hour answers left are people busy with a task. Throughput unchanged; no
one died in the five days since w16; the first hearsay was spoken
("Feathsa told what they know of Bith: stole from Feathsa").

## Things left out weather away (rules w20)

Live world under w19: 36% of decisions were take or drop, juggling 42
ground piles. Bots, three seed sets (1–6 / 7–12 / 13–18), before → after:
targets 5/6 → 4/6, 5/6 → 5/6, 5/6 → 6/6; starvation 40 → 50%, 41 → 38%,
24 → 19%; births 2.4 → 1.7, 1.8 → 2.0, 1.6 → 2.0 a year. Over 18 seeds,
neutral (starvation 35% vs 36%, births 1.9 vs 1.9); the first set alone
would have said worse, the third alone better. Measure in the live world:
the share of take and drop decisions, and the number of piles.

## Taking from the ground means food (rules w21)

Live world under w20, 721 decisions: take 21%, drop 15% (36%, as before
w20): weathering did not reduce the juggling. 123 of 150 takes named no
item and lifted whole piles. w21 makes no item mean food. Bots name what
they take, so seeds 1–6 × 4 years are unchanged (4/6: population 3–20,
births 1.7 a year; starvation 50%). Measure in the live world: take and
drop as a share of choices, and loads at the cap ("could not pick any of
it up" setbacks).

## What a life and a child are (rules w22)

Rules text and plans only; bots unchanged (seeds 1–6: 4/6, identical).
Live under w21: 0 `pledge`, 0 `ask_child`, 0 births in 4,171 decisions.
Measure: `ask_pledge`, `ask_child`, `pledge`, `conceive` and `birth` events.

## Tried and undone: gathering walks to a remembered bush (2026-09-29)

Live world, days 208-219: six starved, five of them on the same few tiles in
the north-east corner, where 66 bushes had died from picking since day 190,
while the south-east held 177 berries. Their plans kept stopping with "you see
no berries within sight". Tried: with nothing to eat in sight, `gather` walks
to the nearest remembered bush that had berries. Bots, seeds 1-6 x 4 years
against main (35% of deaths starved, planners worth 177): within 14 steps,
starved 59%, planners 48; within 8 steps and seen in the last 2 days, starved
41%, planners 49. Worse both times, so not shipped. The trap is real; the fix
is not this one. Ideas not yet tried: make "no berries within sight" say
where the nearest remembered berries are (perception, not a walk), or let the
people see that a place has been picked bare.

## Service, standing trades, sowing walks (rules w31-w32, 2026-09-30)

Live world at day 329 (w30): 69 people ever, 45 of 53 deaths starved, no
births, 8 proposals and 4 deals in 9,112 decisions; 467 seeds idle in
stores and only 20 sowings, though `plant` appeared in about 270 plans
(most stopped at "no farm next to you").

Bots, 18 seeds (1-18) x 4 years, main -> w32:
starvation 27% -> 36% of deaths; births 1.6 -> 1.8 a year; Gini 0.42 ->
0.47; lowest population 9/7/10 -> 7/7/5 (by seed set); planners' worth
160 -> 144; deals 3 -> 12 a run; thefts 548 -> 452 a run; hired about 9 a
run (nearly all served out), trades posted 4 (traded 28). Targets 14/18 ->
12/18 (population floor fails more, in boom-bust seeds).
Isolated: w31 with the hiring bots switched off (engine only) gave
starvation 35%, births 2.0: a thief who seldom gets past the victim's own
people leaves more food with families, more children, harder busts.
`combat.watched` 0.1 instead of 0.2: starvation 36%, no difference; kept
at 0.2. An earlier servant bot that trailed its master all day starved
itself (46%); it now guards only when a stranger is near the master.
100-person land, seeds 1-2 x 2 years: starvation 58% -> 63%, births 4.5
-> 6.0 a year, lowest 62 -> 52.
Prompt: +135 tokens a person on the live state (about 4%).
Measure live: `hire`, `service_end`, `service_left`, `dismiss`, `post`,
`trade` and `plant` events; deals per day.

## A child agreed on comes when the parents can (rules w33, 2026-09-30)

Live world: no births in 332 days; 5 asks; the one pledged couple were both
well fed and side by side 14 of 482 hours together. Bots, 18 seeds x 4
years, w32 -> w33: births 1.8 -> 2.5 a year (target met in all three sets);
starvation 36% -> 42% of deaths (more mouths); Gini 0.47 -> 0.47; lowest
population 7/7/5 -> 7/7/5; targets 12/18 -> 15/18. Prompt +14 tokens.
Measure live: `agree_child`, `conceive` and `birth` events.

## Things of one's own making, sickness and care, abandoned buildings (rules w34-w36, 2026-09-30)

Live world (day 332): 16 of 22 stores and all 13 shelters belong to the
dead, open to anyone and full of junk, still called by their dead owners'
names. Bots, 18 seeds x 4 years, w33 -> w36: targets 15/18 -> 16/18;
starvation 42% -> 37% of deaths; births 2.5 -> 2.3 a year; Gini 0.47 ->
0.47; lowest population 7/7/5 -> 8/6/8. About 40 sicknesses a run (a
person about once every two years), 9 deaths from sickness in 18 runs
(about 2% of deaths); at the first rate tried (`sickness.chance`
0.00025) it was 13 a run and killed no one, so it was raised to 0.0008.
Things made 3-4 a run (planners' tokens); claims 0 (planners build their
own store before anything is abandoned; the unit tests cover claiming).
100-person land, seeds 1-2 x 2 years: 6/6 (starvation 57%, births 4.8 a
year, 13 hired and 16 deals a run). Prompt: +170 tokens a person against
w33 on the live state (about 4%).
Measure live: `make`, `sick`, `mend`, `claim`, `destroyed` events.

## Lighter prompts, fewer decisions, gateway rests (rules w37, 2026-09-30)

Live world (w30, 3,128 decisions): what woke people: plan stopped 15%,
nothing to do 15%, spoken to 12%, whispered to 9%, choice failed 9%, a
familiar face after days 7%, a stranger 7%. Prompts 4,150 -> 3,350 tokens
(by characters, all living, same state). Bots (18 seeds x 4 years, w36 ->
w37; bots do not read prompts or wake reasons, so this is mostly noise
from the plan-step change): targets 16/18 -> 14/18, starvation 37% -> 30%,
births 2.3 -> 1.9 a year. Measure live: decisions per person per world
day (2.4 under w30), gemma-4-31b answers against 500/503/429 in quota.json.

## Long lives, easier food, clothes (rules w38, 2026-09-30)

Six seeds, four years (a person's four years of age), mixed bots:

| | before (w37) | after (w38) |
|---|---|---|
| targets | 6/6 | 5/6 (births 1.2 a year: the land is full and nobody dies of age) |
| population after the first year | 9-21 | 16-22 |
| starvation share of deaths | 28% | 10% (5 starved in all six runs) |
| deaths from age | 65 | 0 (nobody is near sixty yet) |
| planners' worth vs foragers | 109 vs 26 | 354 vs 104 |

With easier food and no deaths from age, a land fills to its limit and stays there: births then
come only as fast as people die, so the births target (set when people lived three to five years)
no longer measures what it did. Planner bots made and wore clothes once they picked up the hides
and bones hunts leave (two seeds, two years: 17 and 12 things made, shoes and cloaks most).

## The crafts to bronze (rules w39, 2026-09-30)

Six seeds, four years, mixed bots (a quarter are planners, who climb the crafts once their store
holds 12 food): 5/6 targets (births 1.5 a year, as under w38: a full land). Starvation 3% of deaths;
population 16-22; Gini 0.36; planners 171 vs foragers 100. Kilns 7 a run. The first try, with
planners climbing whenever fed, cost them their lead (124 vs 98): they spent the time and stuff a
reserve is built from, so the ladder now waits for one. Planner-only worlds, four seeds, four
years: every seed knapped, fired pottery, burned charcoal and sewed fur coats; three built furnaces
and learned to smelt; one cast a copper axe. Bronze needs the one black-stone place and was not
reached by bots in four years.

## civ c2 (2026-10-01): bots-only, `tools/civ_balance.py --seeds 1 2 --years 1`

| | c1 (main) | c2 |
|---|---|---|
| alive after a year (of 120) | 111, 126 | 111, 144 |
| births | 5, 7 | 9, 25 |
| tamed / trades / groups | 0 / 0 / 0-1 | 5 / 7-11 / 23-26 |
| teachings | 0, 8 | 5, 41 |
| able crafts | 10-12 | 12-13 (farming, herding) |

Starvation on seed 1 rose (9 to 15); seed 2 had none. Era 1 in both after one year.

## civ c23 (2026-10-01): known wrongs, `tools/civ_balance.py --seeds 1 2 3 4 --years 2`

| | alive | attacks | killed | thefts |
|---|---|---|---|---|
| c22 | 141, 174, 168, 173 (656) | 0 | 2 | 7 |
| c23 | 155, 168, 163, 172 (658) | 8 | 3 | 10 |
| c24 | 147, 187, 156, 174 (664) | | | |
| c24 + children unburden | 156, 183, 162, 190 (691) | | | |
| c25 | 146, 188, 165, 182 (681) | 9 | 1 | 14 |
| c26 (8 seeds) | 147, 175, 148, 173, 166, 176, 172, 174 (1331) | 5 | 6 | |

## The civ lands' noise floor, and a fix that costs births (rules c83, 2026-10-10)

Old lands (`tools/civ_balance.py --seeds 1..12 --years 3`, default 120 people), sums over 12 seeds:

| run | alive | births | starved |
|---|---|---|---|
| main (c80) | 2,284 | 889 | 27 |
| c83 as shipped (F) | 2,276 | 876 | 22 |
| F with one extra random draw at the start (no rule change) | 2,240 | 835 | 19 |
| F + an aimed gather reaps only the field named (G) | 2,208 | 812 | 28 |
| G + the stubble open to gleaners for two days (H) | 2,182 | 788 | 25 |

One random draw moves births by 5%: a difference under about 5% in 12 seeds x 3 years is noise, and a 6-seed
difference under about 8%. G and H are past it, but not far; both stay out. Only 3-5% of the grain reaped came from
neighbours' fields when an aimed gather reached them, so the births G costs are not plainly hunger.
