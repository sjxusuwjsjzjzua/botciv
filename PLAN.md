# botciv — plan

**Draft 4, 2026-09-28. Building.** How the work is done: `docs/process.md`. Draft 3 was the design brief; this
draft records what was built and what changed. The owner's brief: a
completely open-ended sandbox; the people do not know they are
simulated; the plan is a guideline, not a contract.

## 1. What it is

A persistent world on a 24×24 grid. A dozen or more people live in it,
and there is not enough food for all of them. A language model decides
what each person does, says, notes down and believes. The engine decides
what actually happens. Nothing social is scripted: groups, deals, feuds,
chiefs, laws and betrayals exist only if the people build them out of a
small set of verbs.

The world advances several times a day on GitHub Actions within the
free-tier quota, and the owner reads it on a phone.

## 2. Principles (unchanged in substance)

1. **The engine owns the world; the model only chooses.**
2. **Few verbs, many combinations.** About 30, each working on anything
   it sensibly applies to.
3. **Record everything, enforce almost nothing social.** Promises,
   deals, gifts, thefts and attacks are recorded exactly in each
   person's ledger. Only store, shelter and wall access is enforced.
4. **Partial information.** Sight radius (shorter at night), no view of
   inventories or others' thoughts; theft can go unnoticed; lies are free.
5. **Many roads to power:** strength, stores, farms, knowledge of
   recipes, followers, information.
6. **The rules text is a variable.** It states every outcome evenly
   (probes showed wording moves behaviour a lot) and is versioned
   (`RULES_VERSION` in `prompt.py`, logged with every decision).
7. **The world never ends on its own.** Births, strangers arriving,
   seasons and shocks.
8. **New: the people do not know.** Prompts are written from inside the
   world: hours and days, not ticks; "things you can do", not actions.

## 3. The world as built

- **Time:** an hour per step, 12 hours a day (the last 3 night), 10-day
  seasons, 40-day years. Winter: no berry regrowth, farms stall, cold
  nights hurt anyone without shelter, fire or a cloak.
- **Food:** berry bushes (regrow slowly, weaken when picked bare, spread
  in spring and summer), deer herds (one hunter almost never succeeds,
  two usually do; herds regrow and new ones wander in), fish by water,
  farms on rich soil (seeds, 4 days to grow, 6 grain per seed). Carried
  food spoils; stores slow it.
- **Materials and making:** wood, stone, fibre, hide, bone. A hidden,
  seed-generated recipe table of 14 things (tools, clothing, cooking,
  bread, a necklace and a drum that do nothing useful). Recipes are
  learned by trying pairs or being taught, and are lost when the last
  person who knows dies untaught.
- **Buildings:** store, shelter, wall, farm, fire. Others can help
  build. Owners set access. Buildings can be broken.
- **Life:** ageing (3–5.5 years), children (both parents well fed, both
  agree, a teaching from each), strangers from the edge, inheritance.
- **Shocks:** drought, storms, blight.

## 4. Minds

Each person is asked alone; nothing another person knows enters their
prompt. The prompt holds: the world as they know it, the things they can
do, their body, belongings and knowledge, a local map and lists of what
they see, what happened since they last decided, offers and promises,
their own notes (rewritten each time, 600 characters), their opinions of
others, and the engine's record of what really passed between them.

They reply with a private thought, optional speech (free, alongside
acting), one action, an optional plan of up to 8 steps, rewritten notes
and changed opinions.

They are asked again only when something happens to them: their plan
ends or breaks, they are attacked, robbed, spoken to, given something,
offered a deal, a vote is called, a stranger appears, they grow hungry
or hurt, or a day passes quietly. A hungry person carrying food eats it
without being asked, soonest-spoiling first (rules w7); only hunger with
nothing to eat needs a decision.

Thinking takes time. Each hour the world waits up to 10 seconds for
answers; someone whose answer is slower carries on with what they were
doing and acts when it comes, never more than 3 hours late. What they
heard and saw meanwhile is kept for their next decision.

## 5. Budget (measured)

The key is on the free tier. From AI Studio's rate-limit page:

| Model | RPM | RPD |
|---|---|---|
| Gemini 3.5 Flash-Lite | 15 | 500 |
| Gemini 3.1 Flash-Lite | 15 | 500 |
| Gemini 3.5–3.8 Flash (each) | 5 | 20 |
| Gemma 4 31B | 30 (16K TPM) | 14,400 |

So about **1,000 decisions a day** from the two Flash-Lite models, which
also make two kinds of mind (half the people use each). At 15 a minute
each, a day's allowance takes about 35 minutes to spend, so **the
per-minute cap is the one that bites**; the gateway paces each model to
it rather than treating a 429 as a failure. Gemma's 16K tokens a minute
is about 7 calls with a 2,200-token prompt, and it timed out on every
live probe; if it becomes reliable it is the way to run a bigger world
for free. The gateway counts calls per model
per Pacific day, backs off on per-minute limits, stops a model on its
daily limit, and saves what it learns in `quota.json`. When the quota is
spent the world pauses; rule-based bots stand in only for a person whose
calls keep failing, and the log marks it.

Measured on the first live days (14 people, 406 decisions): 3.7 decisions
per world hour, prompts of about 2,450 tokens, replies of about 250, 2 s
per call. About a third of decisions answered a failed choice or a plan
that stopped, and a fifth answered hunger; w7 removes the commonest of
both (take with no item, hunger with food in hand) and asks for longer
plans.

**Blitz and backlog.** The world does not need to run at watching speed.
It runs as fast as the quota allows, and the viewer plays the backlog at
a human pace (Story speed: about 50 seconds a world day).

**Every allowance, all the time.** The limits are of two kinds, and they
reward different habits. Flash-Lite's is 500 calls a day per model: it
keeps until the Pacific midnight, so it only has to be spent sometime
that day. Gemma's is tokens a minute (16K, about 6 calls at 2,450
tokens): a minute that passes unused is gone. So:

- Each call goes to the model that can take it soonest: a person's own
  Flash-Lite model if it has room now, otherwise whichever does. Gemma
  works every minute; Flash-Lite still gets spent within the day.
- Each run lists the models the key can reach and adds every Gemma of 4B
  or more and every plain Gemini text model, each with its own allowance.
  A model that is not found, or rejects three requests in a row, is
  dropped for that run; one with no free allowance is refused on its
  first call and skipped for the day. Of two models with room, the one
  that has been answering faster is asked.
- Probe, 2026-09-28: `gemma-4-26b-a4b-it` answers in 5–6 s and
  `gemma-4-31b-it` in 33–43 s, both with valid replies; the key also
  reaches Gemini 2.5 Flash, Flash-Lite and Pro, 3 Flash, 3.1 Flash-Lite
  and Pro previews, and 3.5–3.8 Flash.
- The gateway paces by the prompt tokens the API reports and learns
  request and token limits from any 429; a refused call's tokens are
  given back to the minute.
- The world runs around the clock (section 6).

Which model answered is logged with every decision, so the minds can
still be compared. Gemma's reliability is the open question (it failed
12 of 20 on 2026-09-27).

## 6. Running it

- `world.yml`: one run advances the world for about 5.5 hours in
  half-hour pieces (`tools/advance.py`), committing state and logs to the
  `world` branch after each, writing the chronicle and asking Pages to
  publish. Each run starts the next as it ends; GitHub's schedule proved
  unreliable, so it is only a backstop. A run ends after its current piece
  when newer code reaches main, so a new version takes over within the
  hour. When every model is spent or a local runner holds the lock it
  waits rather than ends. Full prompts are uploaded as a run artifact
  (kept 30 days) for studying and replaying decisions.
- `pages.yml`: publishes the viewer and `ideas.md` from `world`.
- `tools/run_local.py` advances the world from any machine and holds a
  lock the Actions runs respect.
- `dev.yml`: `[probe]` or `[world]` in a commit message on a `claude/*`
  branch.
- Logs: gzipped JSONL events (with per-hour position frames) and
  decisions per run. Full prompts are kept only as Actions artifacts.

## 6a. Where the world goes next: ideas from the people

The owner's brief is open: not a survival game, though surviving comes
first; a world where some thrive, gather wealth and power and others
barely get by, grown in versions. What to add next is decided largely by
the people themselves:

- **They say what they want.** Every decision may carry an optional
  `idea`: something they want to do, make or have that no one knows how to
  do yet (rules w8). It is worded as their own invention, never as a
  request to anyone outside. They remember their last few ideas and can
  talk about them. Ideas are logged as events and shown in the viewer.
- **Two quieter signals.** `do` deeds change nothing by themselves, so a
  deed acted out often marks something the world cannot yet do; and the
  choices the engine refuses (above all unknown verbs) show what people
  tried.
- **Each iteration** reads `tools/ideas.py` (published hourly as
  `ideas.md` on the site), picks what is most wanted and fits the rules,
  and makes it real in the next rules version. An idea made real is first
  worked out by whoever first imagined it, if they are alive.
- **Wealth and power are measured, never shown to the people.** Once a day
  the engine logs a census: each person's worth (food, materials and made
  things carried or stored, buildings owned) and how many they lead. The
  viewer ranks people, shows what share the richest fifth hold, and
  charts inequality (Gini) by day.

### Versions

- **w8** (2026-09-28 07:50): ideas, the census. By day 122, year 4:
  27 people had lived and 5 were alive, 20 of the dead starved (12 in
  winter), no one was born, no farm was ever built. Inequality (Gini)
  swung 0.2–0.5. 34 ideas: most wanted was keeping food through winter
  (smoking fish, preserving berries), then tools already in the hidden
  recipes, then family ("propose to Toth and start a family"), and wealth
  ("to be the richest person in the land"). Refused choices: putting
  into a store not beside you (83), naming a place instead of
  coordinates (42), taking from a pile a few steps off (50).
- **w9**: made real: smoking and drying at a fire (credited to Breszai,
  the earliest living imaginer), and pledging as partners for life
  (partners share stores and shelters and inherit from each other).
  Techniques are knowledge like recipes: known, taught, worked out by
  trying, picked up by watching. Seeds now also come from berries, and a
  farm takes 8 seeds (48 grain that keeps): a road to surplus. People
  walk to the store, pile or named place they mean. Models the service
  is struggling with rest longer each failure in a row.
- **w10**, from thinking w9 through: food rotted but silently, so no one
  could see why smoking mattered. Measured with bots over a year, a fifth
  to two fifths of all food gathered rots (15–45 food worth a day against
  60–75 eaten). Now people hear each dawn what they carried went bad, and
  the next person at a store hears what rotted in it; the census logs rot
  and the viewer shows it. Working out smoking by trying was so easy (15%
  an hour) that knowing it was worth nothing; now 5%, so teaching, and
  refusing to teach, matter. With 4 people left there was no society to
  be unequal in: strangers now come up to four times as often to an
  emptied land (bots over two years: 7–19 people instead of down to 4).
- **w11**, from bot balance runs (`docs/balance.md`): building a farm was
  impossible (the word "farm" was read as grain), which is why no one ever
  farmed. Fixed, and grain kept back can be sown again, so a harvest can
  grow into a surplus. With mixed bots (careless, tit-for-tat, planner,
  raider) over 10 seeds × 6 years: never extinct, starvation 43% of
  deaths, planners worth about 2.5 times foragers, Gini 0.47, raiders
  second-richest. Outcomes now depend on behaviour.
- **w12**, from bot rounds with trade, credit, households and teaching,
  and a 100-person land: sowing uses the free farm beside you (your own
  first), building with no place named uses the first fitting tile beside
  you, and a walk with no way through goes as near as it can. Larger lands
  get rivers (and rich soil) and wolf packs in proportion, and strangers in
  proportion to the edge. 100 bots on 64×64 hold 55–93 people over four
  years; in a crowd, theft pays best for bots. `configs/large.toml`;
  `/botciv/large/` on the site.
- **w13**, what keeps wrongdoing in check, made possible rather than
  scripted: witnesses of theft and attacks remember who did it (and see it
  when they meet them), and people standing together take from someone
  openly by force, which seldom fails unless that person has their own
  people beside them. Retaliation, restitution, fines and group enforcement
  can now emerge, and so can robbing the friendless. With bots that use
  them, thefts fell from about 180 to 49 a run and raiders went from second
  richest to poorest.
- **w14**, from a whole-world map of what emergence needs
  (`docs/mechanics.md`): a farm's owner can close it, and taking from a
  closed farm is remembered; buildings can be handed over; anyone who owns
  a building can name an heir; partners can part; kin remember who killed
  their kin; witnesses remember a breaking; a leader of several is seen as
  one. Bots that answer theft with theft and only blood with blood keep
  thefts in check without killing. And the live world's hunger, read from
  its dead: people filled their load with wood and could not pick a berry
  (15 of 23 starvations). The rules now say what things weigh, a full load
  is named, and a hungry person eats on the spot what they cannot carry;
  people in sight are walked to before giving, taking or teaching.
- **w15**, a self that can change, kept light: besides their notes, a
  person may write, only when it changes, one sentence on who they have
  become (shown beside the temperament they were born with), and keep a
  line for life when something changes them (one a day at most, six in
  all, the first never dropped). Both optional; the instructions were
  tightened so a prompt with neither is no longer than before (+13
  characters on ~13,100), and a full life costs about 200 tokens.
- **w16**, food at one's feet, read from the live world's dead again: a
  starving person stood on 5 meat with a load full of wood and was refused
  both "take meat" (full) and "eat meat" (none carried). Now a hungry
  person eats on the spot the food they cannot carry wherever it comes
  from (the ground, a store, their share of a hunt; from another's store it
  is still recorded as taking), and `eat` reaches food on the ground at or
  beside them. The rules add that a failed craft costs only time, and the
  `idea` hint says to try two things first: people wished for a cloak of
  hide and fibre (a recipe) instead of trying it; 27 crafts in the whole
  world. +108 characters a prompt.
- **w17**, hearsay. Speech may carry `of` = a name: the speaker passes on
  what they themselves have seen or suffered of that person (thefts,
  blows, broken or kept promises, gifts), and those who hear remember it
  as told by them ("Tam told you they stole from Tam"), recalled on
  meeting. First-hand only and one hop; the engine passes on only the
  true record, and lying stays free in the words. Free like speech: as a
  verb costing an hour, bots that told after every wrong starved more
  (a control that only waited an hour did the same). The `of` clause is
  offered only to those with something to tell (+13 characters on
  average). Bots speak of fresh wrongs but do not act on what they hear:
  bots that did lowered births and deterred no more.
- **w18**, the engine understands sowing: "plant" where no farm stands,
  on or beside rich soil and carrying wood, builds the farm and then sows
  (it was refused, "there is no finished farm"); trying to eat seeds is
  answered with what seeds are for. From the live world's refusals: people
  carried 8 to 15 seeds beside rich soil through a starving winter. No
  prompt change; bots never hit it (balance identical).
- **w19**, no one stands idle waiting for their own thoughts. Answers
  arrive late when the models are slow, and the world waited only when one
  was 3 hours late: in the w14–w15 logs 58% of decisions came 1–3 hours
  late and a third the full 3, while the commonest reason to decide was
  "you are not doing anything", so people stood about for hours of a
  12-hour day beside food. Now the world waits for someone idle after 1
  hour; someone busy may still run 3 hours behind. The world clock runs
  slower when models are slow, not the people. Mind only; bots unaffected.
- **w20**, things left out weather away. Under w19, 90 of 250 decisions
  (36%) were take and drop: people with full loads dropping fibre to lift
  wood and dropping bone to lift fibre beside the same piles. The land held
  42 piles (104 fibre, 96 wood, 48 bone), mostly left by the dead, and
  nothing but food ever left the ground. Now each day on the ground fibre
  loses 15%, hides 10%, wood 7%; bone and stone last; the rules say so.
  What is worth keeping goes into a store.
- **Viewer, hourly snapshots** (no rules change): each replay frame carries what a person holds, is worth and belongs to (written only when it changed; every replay file starts full). Once the replay playhead has been moved, the Story, People and World tabs show that hour, with a banner and Back to now. History before this has no holdings ("not recorded"). Skills, recipes, notes and opinions are shown as now.
- **Groq in the pool** (no rules change): with `GROQ_API_KEY` set (repository secret `Djxuzusjsnzja`), the gateway adds the Groq models llama-3.3-70b-versatile, llama-4-scout and llama-3.1-8b-instant as `groq:<name>`, like Gemma: extra capacity, never a person's home model. Groq gets the reply shape in a short system line; its per-minute limit is read from reply headers and a per-day 429 marks the model spent. Untried against the live API when merged: check `tools/health.py` for `groq:` calls and their failures. GitHub Models is retired (July 2026) and Kaggle has no hosted API, so neither is used.
- **Groq models by family** (no rules change): tried live on 2026-09-29, the key works but all three Llamas had been retired, so Groq gave the world nothing. Discovery now takes Groq's general chat models by family (`openai/gpt-oss-*`, `qwen/qwen3*`, Llamas if they return), largest first, skipping guard, speech and TTS models; gpt-oss is sent `reasoning_effort: low`, Qwen 3 `none`. A Groq-only world ran 23 decisions with no errors, about 1 s each. Free limits per model: 8000 tokens a minute (about one call), 1000 requests a day, and a daily token cap.
- **w21**, taking from the ground without naming a thing takes the food. Under w20, take and drop were still 36% of 721 decisions (take 21%, drop 15%): 123 of the 150 takes were `take ground` with no item, which lifted everything on the tile, bone and wood included, until the load was full; the next choice dropped wood or fibre onto the same tile, and the next took it back. Now no item (or "food") takes only the food there, from whichever tile beside the person has some; with none, the refusal says what lies there and asks for the item by name. A named item is taken as before. Bots always name items, so bot balance is identical (4/6, seeds 1–6).
- **w22**, what a life and a child are. In 4,171 live decisions no one ever used `pledge` or `ask_child`, though the engine allows both (bots pledge and bear children) and grown, well-fed pairs stand together often. People want it: Yas meant to ask Toth for days, always after one more chore, until Toth died; others wrote it as an `idea`, as if it were impossible. The rules said only "people live a few years" and nothing of what a child is. Now they say people live about three to five years (most living people are 2 to 3), and that a child is born two days later, helps from its first days, is grown within 20 days and inherits what its parents built. `pledge` and `ask_child` may be plan steps ("go to Toth, then ask"), never repeated. About 40 more prompt tokens.
- **Viewer, TV mode** (no rules change): `#tv` or the 📺 TV button turns the replay into a full-screen show for a television (a cast Chrome tab): map and a side panel in large type (day, the latest words and happenings, the living with their mood and work), dark theme, auto-play at Story speed, the last day replayed while waiting, a newer world picked up within about 2 minutes of publishing. Replay files are fetched per data version, so a grown last file is never read stale from cache.
- **w23**, a pile of one kind is taken without naming it. The first 99 decisions under w22: take 25%, drop 9% (drop down from 15%). 16 of 29 takes still named no item, mostly people wanting the wood or fibre on the ground to build a shelter; next to a pile of only wood the w21 refusal ("no food here; name the item") cost them a decision for nothing. Now with no item named: the food there; else, if the pile holds one kind of thing, that; only a mixed pile is refused with a list. Engine only; bots name items, so bot balance is unchanged.
- **w24**, people at work are woken by speech less often. The world's pace is the free tier's decisions: Gemma allows 16,000 input tokens a minute, about four decisions, and gemma-4-26b answers most of them. In 602 decisions of 2026-09-29, 167 (28%) were asked only because someone spoke to the person, often an acknowledgement ("Let's do it." "Alright."). A listener busy with a task is now woken by speech at most once in 6 hours (idle listeners still every 3); what was said still reaches them at their next decision. Measure: decisions per world hour, and world days per real hour.
- **w25**, words from outside the world are never kept. On day 215 Bigear's line on who they have become read "I am an efficient assistant capable of writing and executing web scraping logic", written by a model that had slipped into answering "the user"; that line went back into every later prompt, and two decisions later Bigear's thought was about the history of a real country. In 5,091 decisions, 4 were such slips (3 of them Bigear). Now an answer whose thought speaks as an assistant (the user, assistant, language model, as an AI) or whose speech uses words from outside the world is set aside whole (the person carries on; a `mind_slip` event records it), and notes, self-lines, beliefs, lines to remember and ideas with such words (also prompt, simulation, model names) are never kept or shown; what slipped in before is left out of the prompt.
- **w26**, a refusal says where the berries one remembers are. Days 208-219: six starved, five on the same few tiles of the north-east corner, where 66 bushes had died from picking since day 190, while the south-east held 177 berries; their plans kept stopping with "you see no berries within sight". Now that refusal adds "the nearest you remember are at (x,y), N steps away (seen D days ago)" or "you know of no berries anywhere". Walking them there instead was tried and made bots worse (docs/balance.md); saying it leaves the choice to the person. Bots unchanged (seeds 1-6: 5/6, identical to main).
- **w27**, a full store says so. On day 237 the world slowed to about 5 decisions per world hour; "The store is full." was the most common reason people were asked (26 of 147, 18 of them alone): people put wood into stores already full (60 weight), were told after the fact, and tried again. A usable store's line now ends "(full)" when it is, and `put` into a full store is refused at once with what it holds and what else can be done (take something out, another store, build one, drop what is not needed). Bots unchanged (seeds 1-6: 5/6, identical to main).
- **w28**, a refusal that people only repeat is dropped. Day 240: 27 of 72 decisions followed a failed choice, most of them the same `take` sent again beside a pile or store without food, whose refusal ("no food here; name the item to take", from w21/w23) the models ignored up to five times in a row. With no item named, `take ground` still takes the food first where there is any; with none, it takes what lies there as far as one can carry (as before w21). `take store` with no item and no food inside takes the one kind of thing a store holds. Bots unchanged.
- **w29**, a gift of food feeds a hungry person who cannot carry it. The rules have long said a hungry person eats on the spot the food they cannot carry, whether picked, caught, hunted or taken; a gift was the exception: what did not fit fell at their feet. In the famine at the end of winter of year 6 (seven starved on days 241-244; bushes bare, no food stored, the one store with grain closed), Brearkal gave berries to a starving Gel whose load was full, and Gel died. Now a gift works like picking. Bots unchanged (seeds 1-6: 5/6).
- **w30**, out-of-world words, wider, and never published. The owner saw Bigear "talking about the People's Republic of China and automating data extraction" on the viewer: slips from before w25 (the last at hour 2663, day 222; none since), still in the logs and shown on Bigear's page. Many used no word w25 knew ("Automate data extraction from web pages using Node.js and Cheerio", "repeat the README.md file"), and a third person had one (Hikton: "package.json, src/index.js"). The list now also holds computing and real-world words (json, readme, node.js, api, html, web pages, scraping, data extraction, China, republic of, ...); on the whole log it catches 8 answers, all real slips, and nothing else. Every such answer is set aside, and the viewer build (site.py) drops such text from thoughts, speech, notes, self-lines, beliefs, remembered lines, ideas, events and the chronicle, so nothing from before is published either. Security check: no key in any branch, history or log; key-holding workflows run only on schedule, by hand or on pushes to claude/* branches.
- **w31**, service: work for hire, guards and enforcers. The owner asked whether people could hire others to work or guard. They could not in any way the world recorded: a deal with a promise was possible, but no one could verify work except by what was handed over, and a guard following their employer counted as coming after them, on the thief's side. Live world at day 329: 69 people ever, 8 proposals and 4 deals in 9,112 decisions, no births. Now a deal can carry `hire_days` (the other works for you) or `serve_days` (you work for them). While it lasts master and servant count as each other's people when force is used (a guard at the master's side stops a lone thief taking by force; a master with servants beside a victim can take together), the servant may put things into the master's stores (not take), and every 12 hours the master is told what the servant was seen doing and handed over. Leaving (`leave`) or sending away (`expel`) early is recorded, and leaving early can be told on as a wrong. One service at a time as servant; masters can have many; it shows on people ("in Dam's service", "has 2 in their service") and counts toward command in the census. Separately, a stealthy theft's chance falls by `combat.watched` for each of the victim's own people beside the thief. Bots: planners with 30+ food take a neighbour into service for 3 days paid in grain; reciprocity bots accept a day's pay per day's work; servants bring surplus food to the master's store and go to the master's side when a stranger is near.
- **w32**, standing trades: markets that outlast a conversation. A store's owner can `post` what the store gives for what is put in (e.g. 1 grain for 2 wood); anyone may `trade` there, even when the store is closed to them and the owner is away, while it holds enough and has room. The owner is told of every trade and it goes in both ledgers. Stores show their trade and stock to passers-by and are remembered with it, so a person can walk to a known trade; taking or putting at a closed store that trades says so. A posted trade is also piece-work: a store that gives grain for wood is a standing job. Bots: planners with 12+ grain post 1 grain for 3 berries in summer and autumn; anyone with spare berries buys grain that keeps.
- **w33**, a child agreed on comes when the parents can. No child had been born in 9 years (days 1-332), though people wrote that they wanted families. A child needed both parents well fed (12 of 20) at the very hour one accepted the other's ask, next to each other, within 6 hours of the asking. Answers come 1-3 hours late, and the one pledged couple (Brimtol and Kemfu) were both well fed *and* side by side for 14 of their 482 hours together; their third ask was refused: "one of you is too hungry". Now accepting (within 5 steps) is an agreement: the child is conceived the first hour, within 10 days (`agent.child_hope_days`), that both are well fed and side by side; both are told what it waits on, and see it in their prompt until then. The cost and the conditions are unchanged; only the timing is no longer a matter of the hour.
- **w34**, things of one's own making. The world's things were a closed list of fourteen hidden recipes; nothing else could exist, though people wished for needles, clothing, bread and more. Now anyone can `make` a thing of their own design and naming from what they carry (`name`, `text`, one or two materials per piece, `qty` pieces). It does nothing by itself: it is carried, given, traded, stolen, stored and inherited like anything else, others see it carried, and it keeps its first maker and description. Tokens, crowns, idols, tally sticks, heirlooms and money become possible; what they mean is for the people. Things that do something stay behind the hidden recipes (`make spear` is refused and pointed to crafting), and food is not made into things. Bots: planners with spare bone make household tokens.
- **w35**, sickness and care. Sickness comes now and then (about once or twice a person a year, twice as often starving or in winter) and passes to those who stay beside the sick. The sick weaken instead of healing until it passes; rest, food, shelter and someone well staying beside them help it pass sooner, so caring for the sick is a real choice with a real risk. Those who stayed by someone are remembered for it (and can be spoken of for it); a poultice (a hidden recipe) ends it, so healers can matter. Bots: the sick rest; kin stay beside a sick partner, parent or child.
- **w37**, lighter prompts and fewer decisions (roadmap Phase A: capacity). The rules, the list of what one can do and the closing instructions (two thirds of every prompt) were rewritten to about half their length, keeping every capability and number; berry bushes in sight and remembered are listed on one line each instead of one line per bush. Prompts on the live state went from about 4,150 to 3,350 tokens by characters (Gemma counts 3,900-4,800 with the reply schema), about 19% fewer, which on Gemma (limited by tokens a minute) is about 24% more calls. Fewer decisions: a familiar face returning is told, not a reason to decide (7% of decisions under w30); a plan step that eats what is already eaten or lifts a pile already gone is skipped instead of dropping the plan; a busy person is woken by speech at most every 9 hours (6 before). The gateway: gemma-4-31b's quick 500s (about half its calls on 29 Sep, returned within 1-2 s whatever was sent) now rest it 2 s instead of doubling up to 10 minutes; 503s double up to a minute; a failed call's prompt stays in the per-minute tally, since the model with the most 500s also had the most 429s. Real Gemma (26b) answered 6 of 6 with valid actions and plans.
- **w38**, long lives and clothes (the owner's major update, part 1 of 3: less of a struggle, ageing, clothes seen on people; the tech tree follows). A year is 40 days and a year of age: people are grown at 14 and die of age only past sixty (lifespan 62-88); from 45 they carry 2% less a year (never below 40%), from 55 their most health falls 1 every 6 years (never below 4) and they heal half as fast; children carry 35% of a load growing to all of it. Easier food: hunger 3 a day (was 4), starving loses health half as fast, bushes hold 10 and regrow faster, a seed gives 8 grain, a deer 10 meat and leaves 2 hides and 2 bones. Clothes are worn by carrying them, one of each kind, and seen by others: hat, tunic, shoes (warmth 1), cloak (2), necklace, bracelet; warmth 3 keeps a winter night's cold off, less lessens it, and warm clothes wear on cold nights. The live world is moved by an era table (config.ERA_CHANGES): each person keeps their place in life (a child as far through childhood, a grown person as far toward their old end, mapped to 16-60), and new garments get a pair no other recipe in that world uses. Planner bots pick up hides and bones, make warm clothes they know and now and then try a pair. The replay draws what each person wears and names everyone at every zoom (a tag that would cover another is left out).
- **w39**, the crafts to bronze (the owner's major update, part 2: technology and civilization over subsistence; roadmap phases B-D in one step, as data in `botciv/tech.py`). The land holds clay by some banks, flint and green and black stones in some rock (few, clustered, the black far from the green), wild flax on rich soil that grows back each spring; each deposit is worked out for good. Kilns (clay, stone), looms (wood, rope) and furnaces (bricks, stone) are built. Eight techniques (knapping, pottery, charcoal, weaving, sewing, smelting, casting, alloying) are found by working a material where it belongs (`work`), each hour a chance once what it needs is at hand (wood for the kiln's heat, charcoal for smelting, a mould for casting, a needle for sewing), with honest word of how near it came; watchers may learn it; it is taught like smoking. What one knows is made with `craft item` (26 recipes: flint knives, axes and spears, needles, pots, jars, bricks, moulds, charcoal, cloth, fur coats, boots, fur hats, linen tunics, robes, copper, tin, bronze, copper and bronze axes, a bronze sickle and sword, a copper bracelet, a bronze torc). Tools pay on their own (wood x2-x3, fibre and flax x2, more meat from a kill, grain x2, harder blows); a jar halves spoiling in a store; warm new clothes (fur coat 3, boots and fur hat 2). A store beside a builder supplies what the builder does not carry; worn clothes are not load. Deposits are seen on the map, remembered, drawn in the replay with the three workshops. Planner bots climb the ladder once their store holds a reserve; in planner-only worlds they reach furnaces and copper axes within four years. Two of the live people's ideas made real: Tolgair's bone needle (sewing) and Dek's food kept through winter (pottery: jars).

## 7. Seeing what emerged

- **Chronicle:** one call per finished day turns its events into a short
  history. Every sentence cites event ids; a checker drops sentences
  that cite unknown events or name people absent from them.
- **Viewer:** story feed, replayable map, each person's notes, opinions,
  decisions and ledger, groups. The replay covers the whole history,
  loaded ten days at a time; it remembers where you stopped on that
  device, and its Story speed lingers on speech and events and hurries
  through quiet hours.
- Next: detectors (alliance, betrayal, feud, market, chief, law, lost
  knowledge, culture) and a variety count.

## 8. Next

The working list lives in `docs/mechanics.md` ("Next") and the state of
play in `docs/process.md` section 10. In order: children who depend on
their parents; fish that can be overfished; hearsay recorded; sickness;
standing offers at a place (markets); then detectors for what emerged
(alliance, betrayal, feud, market, chief, law) in the viewer.
