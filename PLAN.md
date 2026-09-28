# botciv — plan

**Draft 3, 2026-09-27. Planning only; no engine code yet.**

Draft 2 was reviewed adversarially and revised
([docs/review-2026-09-27.md](docs/review-2026-09-27.md)). Draft 3 widens
it from an experiment with a pass line into an open sandbox. The owner's
brief for this draft: very open-ended. Cooperation, alliances,
backstabbing and emergent properties should all be possible, with a
broad range of things that can happen at any moment.

## 1. What it is

A persistent world on a grid. A dozen or more agents live in it, and
there is not enough food for all of them. Gemini decides what each agent
does, says and believes. Code decides what actually happens.

Nothing social is scripted. There is no alliance button, no trade
screen, no war declaration. The engine supplies a small set of physical
and social primitives. Alliances, markets, feuds, chiefs, laws, cults
and betrayals have to be built out of them by the agents, or they don't
appear.

The world keeps running between visits. A scheduled job advances it
every day. The owner opens a page on a phone and reads what happened.

## 2. Design principles

1. **The engine owns the world. Gemini only chooses.** The model never
   writes state. It returns an action, the engine checks it, applies or
   rejects it, and tells the agent what happened. Without this the model
   invents food and forgets debts, and scarcity stops existing.
2. **Few primitives, many combinations.** Every verb works on any target
   it makes sense for. A `take` works on a berry bush, a corpse, a group
   store and an unguarded pile the same way. Breadth comes from
   combinations, not from a long menu of special cases.
3. **Record everything, enforce almost nothing social.** The engine
   records promises, claims and group rules exactly. It enforces only
   physics: a locked store is locked. Whether a promise is kept is up to
   the agents. Betrayal is possible because nothing prevents it.
4. **Information is partial.** Agents see a radius, not the map. They
   don't see inventories, private messages or other agents' thoughts.
   They can lie. Deception needs something to hide behind.
5. **Many roads to power.** Strength, stored food, territory, knowledge
   of recipes, followers and information should all be able to beat each
   other in some situation. If one strategy always wins, the sandbox
   collapses into it.
6. **The rules text is an experimental variable.** The probes (section
   11) show that how the rules are worded moves behaviour a long way.
   Every payoff is stated in the same form and at the same length. The
   text is versioned, and every run logs its version.
7. **The world never ends on its own.** Births, arrivals from the map
   edge, seasons and disasters keep it moving. An empty world restarts
   from its last living snapshot.

## 3. The world

**Grid.** 24×24 to start, sight radius 5. Terrain: grassland, forest,
rock (impassable), water, fertile ground. Size and population are config;
the review found draft 1's 32×32 with 8 agents too sparse for agents to
meet.

**Resources.**

| Resource | Behaviour |
|---|---|
| Berries | Clustered bushes, slow regrowth; a bush stripped bare three times dies |
| Game | Herds that migrate with the seasons. Hunting alone pays little; two or more together pay much more than double |
| Fish | At water; steady, low yield, needs a tool |
| Wood, stone, fibre | Materials for crafting and building |
| Fertile ground | Can be farmed: slow to start, high yield, needs someone to stay near it and defend it |

**Food spoils.** Carried food decays every few ticks. Storage built from
materials slows it. Hoarding costs something, sharing a surplus costs
little, and a well-stocked store is worth raiding.

**Seasons and shocks.** A year of 120 ticks with a lean winter. Rare
events: drought, blight on one food type, a herd migration, a storm that
damages buildings. Shocks break equilibria and force migration, which
forces contact.

**Carrying capacity is tuned with bots before any API call.** Target:
a normal season feeds about 60–70% of the population and winter feeds
less. Bots-only runs must settle there first.

## 4. Agents

**State:** health, satiety, age, inventory (weight-capped), position,
three stats that vary (strength, speed, sight), known recipes, group
memberships, name.

**Temperament.** Each agent is born with a short, random line of values
and appetite for risk: "loyal to family, cautious, curious". It goes in
the prompt. The owner wants a broad range, and one model with the same
prompt plays one character. Temperament is logged, and one arm of the
occasional ablation (section 9) runs without it.

**Mind.** Three things carry across decisions:

- **Memory note.** The agent rewrites it on every call. 600 characters.
- **Beliefs.** One line per known agent, written by the agent: "Tam:
  shared the hunt twice, but eyes my store." Opinions, possibly wrong.
- **Ledger.** Facts written by the engine: who attacked it, who gave it
  what, which promises were kept or broken, with tick numbers. So when
  an agent holds a grudge, the event behind it really happened.

**Life cycle.** Agents age and die. Two agents can have a child if both
choose it and both pay food. The child starts with blank beliefs and a
teaching from each parent, a short text the parent chooses. New arrivals
walk in from the map edge now and then. The population turns over, and
culture passes on only if someone teaches it or writes it down.

## 5. The verbs

An action is one verb with arguments: target, item, quantity, text, and
a tile. The engine validates each argument against what the agent can
actually see and hold.

**Body and world**

| Verb | Does |
|---|---|
| `move(dir or x,y)` | One step, or path toward a tile over several ticks |
| `gather` | Take from the resource underfoot |
| `hunt(herd)` | Stand ready at a herd for up to 5 ticks; resolves when enough hunters are ready |
| `eat(item)` | Eat |
| `rest` | Recover health; the agent is easier to hit while resting |
| `craft(item_a, item_b)` | Combine two items. The recipe table is hidden (section 6) |
| `build(structure, tile)` | Place a structure: store, shelter, wall, farm plot, trap, marker |
| `drop(item, n)` / `take(target, item, n)` | Move items between the agent and the ground, a store, a corpse or another agent. **Taking from another living agent is theft.** It succeeds on a roll weighted by speed and whether the victim is resting, and the victim finds out |

**Between agents**

| Verb | Does |
|---|---|
| `say(text)` | Heard by everyone within 5 tiles |
| `whisper(agent, text)` | Heard by one adjacent agent only |
| `give(agent, item, n)` | Hand over |
| `attack(agent)` | Damage by strength; the attacker takes some back; allies fighting together deal more |
| `propose(agent, terms)` | A deal the engine records: what each side gives now and what each promises by a given tick. **Terms can include future promises, which the engine tracks and does not enforce.** |
| `accept(deal)` / `refuse(deal)` | Answer a proposal |
| `teach(agent, recipe)` | Pass on a known recipe |
| `follow(agent)` | Move with another agent until stopped |

**Groups and claims**

| Verb | Does |
|---|---|
| `found_group(name, rules_text)` | Create a group. The founder writes its rules as text, and they are shown to members |
| `invite` / `join` / `leave` / `expel` | Membership. Who may expel is set by the group's access setting |
| `set_access(structure, who)` | Who may take from a store or pass a wall: owner, group, anyone. **Enforced by the engine**, and the only social rule that is |
| `mark(tile, text)` | Leave a sign anyone passing can read. Claims, warnings, laws and graffiti |
| `vote(group, question, choice)` | If the group's rules say decisions are voted, the engine counts. What a vote *means* is up to the members |

That is about 25 verbs. They are enough to build:

- **Alliances:** a group, a shared store, joint hunts, defence.
- **Backstabbing:** take from the group store you have access to, then
  leave. Or break a promise after the other side has paid. Or whisper
  one thing to two agents.
- **Markets:** repeated deals, and a trusted agent holding a store for
  others.
- **Chiefdoms:** one member controls access to the store, and the
  others follow.
- **Law and punishment:** rules text, signs, expulsion, a group attack
  on whoever broke the rule.
- **Secrets:** a recipe known to one family and never taught.

**The schema only offers what is possible now.** Targets must be
visible, items held, structures in reach. The first probe's agents
walked into an occupied tile 5 times in 12.

## 6. Knowledge and technology

**The recipe table is hidden.** Any two items can be combined, and most
pairs produce nothing. Some make a tool (a spear doubles hunting, a net
makes fishing possible, a pot slows spoilage), and tools unlock further
recipes. Agents discover recipes by trying. A discovery is knowledge the
agent holds. It can be taught, sold, kept in a family, or lost when the
last agent who knows it dies without teaching it.

This gives a tech tree that can be lost as well as gained, and makes
knowledge a thing people want to own. The table is generated from the
seed, so each world has different secrets.

## 7. The one open door: `attempt`

Phase 4. Even 25 verbs will run out. An agent may try something no verb
covers: `attempt("dig a pit on the path and cover it with brush")`.

A **referee** call translates the attempt into engine primitives from a
fixed effect library: place an object, damage, block, hide, reveal,
transform an item, delay. The engine validates the result like any
other action, charges materials and time, and applies it or rejects it.
The referee cannot create food, knowledge or anything outside the effect
library.

**Risks, before building it:** the referee will tend to be generous,
and costs creep up; each attempt costs a second call; and results may
be inconsistent across attempts. Mitigations: a fixed cost table, the
referee sees the same materials rule every time, and every approved
attempt is logged so its ruling can be reused. It ships only if phase
3's world is still interesting enough to be worth widening.

## 8. How an agent decides

**What it sees on each call:**

- the rules text, and its temperament;
- its status and an ASCII map of its sight radius;
- visible agents (appearance, not inventory), structures, signs, herds;
- events since its last call, the last 10 in full plus counts;
- messages and deals received;
- its memory note, beliefs and ledger.

**What it returns:** a private `thought`, one action, an optional plan,
an updated memory note and any changed beliefs.

**A plan is a queue of steps in a fixed grammar:** `move_to`, `gather`,
`hunt`, `eat`, `give`, `drop`, `wait`. The engine runs it tick by tick
without calling the model. It drops the plan at the first step that
fails.

**The model is asked again only on an interrupt:**

- plan finished or broken;
- attacked or robbed;
- a deal proposed or due;
- spoken or whispered to;
- a new agent in sight;
- satiety crossing the hunger line;
- 30 quiet ticks.

Interrupts fire once, on the change, never every tick a condition holds.
Speech wakes a listener at most once per 5 ticks, or one conversation
cascades through everyone in earshot.

**Tick order.** Collect every intent. Resolve moves, then interactions
against the new positions, each in seeded random order. An attack on
someone who walked away fails, and both are told.

## 9. Seeing what emerged

The sandbox has no pass line. The owner wants a broad range of things
to happen, so the job is to **notice and name what happened**.

**Detectors.** Code reads the log and flags patterns, each with the
line IDs that prove it:

| Pattern | Detected when |
|---|---|
| Alliance | A group with 3+ members lasts 50+ ticks |
| Betrayal | An agent attacks, robs or breaks a promise to someone who gave to it, dealt with it, or shared its group within the last 30 ticks |
| Feud | Repeated attacks between two agents or groups |
| War | Two groups with 3+ attacks between them |
| Market | A set of agents doing repeated deals |
| Chief | One member controls a group store's access and receives most of the gifts |
| Law | A group rule or sign followed by an expulsion or group attack on whoever broke it |
| Innovation | A recipe discovered |
| Lost knowledge | The last holder of a recipe dies without teaching it |
| Culture | A teaching or sign quoted by an agent born after its author died |
| Migration, famine, extinction | From positions and population |

**Variety counter.** Each run reports how many distinct detector types
fired and how many different verbs were used. That is the measure of
"open-ended": a world where only hunting and fighting ever happen is
failing.

**Daily chronicle.** One call turns the day's detected events into a
page of history. Every sentence must cite line IDs. A checker confirms
each cited line shows the actor, verb and target the sentence claims.
Otherwise the chronicle becomes fiction about the simulation.

**Does the LLM matter?** Now and then, on the same seed, run:

- Gemini, full;
- Gemini with speech off and memory blank;
- a reciprocity bot (tit-for-tat on the ledger, shares surplus, joins
  hunts and group fights);
- Gemini without temperament.

If full Gemini produces no more variety than the bot, the language model
is decoration. This is a check, not the goal.

## 10. Running it

**Stack.** Python 3.11, the `google-genai` SDK, TOML config, JSONL logs,
no database.

**Gateway.** Every API call goes through one place. It has:

- a rate limiter and a 20 s timeout;
- one retry;
- Flash-Lite as primary and 3.1 Flash-Lite as fallback;
- a daily budget that counts retries.

A failed call makes the agent wait a tick and ask again. Only then does
a bot decide, and the log marks it. A run with more than 5% bot
decisions is flagged, so a bad API day can't pass for a Gemini world.

**Log.** One JSONL line per event, each with an ID. It records the
prompt, raw response, exact model version, tokens, latency, action,
outcome and rules-text version. Replays, stats, detectors and the viewer
read the log.

**Controllers** share one interface: `GeminiAgent`, `ReciprocityBot`,
`SimpleBot` (for tuning), `ReplayAgent` (free replays), `HumanAgent`
(the owner plays).

**GitHub Actions: the living world.** The repo is public. Standard
Actions minutes and GitHub Pages are free for public repos (unconfirmed
for this account's plan; check on the first run).

- A **scheduled workflow** advances the world once a day until its call
  budget is spent. It commits the snapshot and log to a `world` branch
  and rebuilds the viewer.
- **A `concurrency` group** stops two runs forking the same world.
- **`workflow_dispatch`** starts a run or a new world by hand, from the
  GitHub mobile app.
- **GitHub Pages** hosts the viewer: the map scrubbed tick by tick, the
  chronicle, and each agent's life. It opens on a phone.
- The job summary page shows the day's numbers even if Pages is down.

**Because the repo is public:**

- The key lives only in the repo's Actions secret `GEMINIAPI`. Workflows
  map it to the environment variable the code reads:
  `GEMINI_API_KEY: ${{ secrets.GEMINIAPI }}`. It
  is never in a file, a log line or a URL. Code sends it as a header,
  never as `?key=`, because URLs get printed in errors.
- Workflows trigger only on `schedule`, `workflow_dispatch` and `push`
  to `main`. **Never `pull_request_target`**: it runs with secrets on
  code from strangers' forks.
- A CI step fails on any string shaped like a Google API key, and
  GitHub's secret scanning should be on.
- Logs, prompts and chronicles are public. They contain nothing but the
  simulation.
- If the key leaks, revoke it in Google AI Studio and make a new one.

**Budget.** Daily free-tier request caps per model are **unconfirmed**.
Read them from the key's rate-limit page in AI Studio before phase 1.
Phase 0's bots count the calls a day of world would cost, before any
call is made. If the free cap allows under one useful day of world,
billing with a hard spending cap is the better ratio. The reviewer's
guess was under $1 per run at Flash-Lite prices. That is unconfirmed.

## 11. Evidence so far

Two probes on the free tier, 2026-09-27. Detail in
[docs/probes.md](docs/probes.md); scripts in `probes/`.

- **Wording decides behaviour.** Probe 1 described only attack's payoff.
  Starving agents attacked or stole 13 times in 13. Probe 2 stated every
  payoff evenly and added a joint hunt: 1 attack in 37 answers.
- **Only the Flash-Lite models answered reliably.** Larger Flash models
  and Gemma mostly returned 503s, 500s or timeouts that day.
- **JSON matched the schema on every answer that arrived.**

One-shot answers say little about repeated play. The next probe tests
whether agents treat a neighbour who helped them differently from one
who robbed them.

## 12. Phases

| Phase | Builds | Gate to move on |
|---|---|---|
| **0** | Engine with the body verbs, `say`, `give`, `attack`; both bots; ASCII view; log; would-call counter | Bots-only population settles within ±20% of the tuned capacity on 8 of 10 seeds. Calls per world-day recorded |
| **1** | Gemini agents, gateway, beliefs and ledger, the Actions workflow with the job summary | Bot fallbacks under 5%; a world-day fits the measured quota; a replay reproduces a run exactly |
| **2** | The rest of the social verbs: whisper, deals, groups, access, signs, theft; detectors; chronicle | Across 5 seeds, at least one alliance **and** one betrayal detected, and at least 6 detector types fire in total |
| **3** | Living world: daily schedule, `world` branch, Pages viewer, life cycle, arrivals, crafting with hidden recipes, teaching, building, seasons and shocks | A world runs 30 days unattended, and at least one culture or lost-knowledge event is detected |
| **4** | `attempt` with the referee; god-mode events from the owner; the owner as an agent; a second model as a second species | Open |

Claude writes the code, so phase 0 is one or two sessions and phase 1
about a weekend. Later phases depend on what the earlier ones show.

## 13. Known risks

- **Free-tier capacity moves daily.** The gateway and resume exist for
  this.
- **Model aliases drift.** `flash-lite-latest` changes under us; the log
  keeps the exact version.
- **One model, one mind.** Temperament, stats, position and history are
  the only diversity until a second model is reliable.
- **Prompt size grows with the verb list.** 25 verbs, beliefs and a
  ledger could make a prompt several thousand tokens. Token limits are
  not expected to bind; latency and cost might. Measure in phase 1.
- **A dominant strategy.** If one approach always wins, variety dies.
  The variety counter shows it; the fix is in the payoffs.
- **The rules text steers everything.** Principle 6 makes it a variable
  to study, not a flaw to hide.

## 14. Open questions

- Do agents know they are in a simulation? Draft 3 says yes, flatly.
- Should the owner be able to speak to agents, as a voice from the sky?
  (Phase 4 god mode.)
- One persistent world, or several worlds with different rules texts
  running side by side for comparison?
