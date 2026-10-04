"""What a person perceives, as text for a language model, and the shape of the answer.

The text never mentions a simulation, a game, agents, ticks or turns. It shows what matters to
this person: their body, their things, their crafts and what is within reach, the land around,
the people they see, what they remember, and what happened since they last thought."""
from collections import Counter

from .content import TERRAIN, DEPOSITS, WILD, TAME, BUILDINGS, CRAFTS, RECIPES
from .content import items as I
from .content.crafts import use_text, tool_options
from .content.crafts import recipes_for, recipe_text
from .acts import VERBS, WRONGS
from .world import key, unkey, dist, direction, TPD, DPS

RULES_VERSION = "c42"

RULES = """How the world works, as far as anyone knows:
- A day: 12 hours, the last 3 night. A season: 10 days; a year: 40. Grown at 14; people live past sixty, weakening from about 45.
- Food: about 2 or 3 a day keeps you fed (berries 1, grain 2, fish 3, meat 4, bread 5); hungry, you eat what you carry. Fresh food spoils in days; smoked, dried, salted, grain, cheese and nuts keep, better in a store, better still in jars.
- Winter nights hurt anyone below warmth 3: a shelter or house (2-3), a fire beside you (2), clothes carried, one of a kind (cloak 2, fur coat 3, tunic, hat, shoes 1). Nothing grows in winter.
- The land: forest gives wood, grass fibre and (summer, autumn) hay; hills and mountains stone; marsh reeds and clay; water fish. In places: clay, flint, wild flax, wild grain, berries, nuts, herbs, salt, and in the hills green stone (copper), black (tin), red (iron), limestone, gold. Places are worked out in time; plants grow back. Deer, boar, aurochs, wild goats, sheep and horses roam; hunters together usually kill one. Goats, sheep, cattle and pigs can be tamed (herding, a rope, a pen): milk, wool, young, meat; they need hay or grain in winter.
- Crafts: anyone can see what can be made and what it takes. Skill (untried, beginner, able, master) comes by trying (a beginner often fails, spoiling half of what went in) or from someone able teaching you (up to able). Some crafts need others first; some need a workshop (kiln, loom, oven, tannery, furnace...); some run by themselves once loaded (firing, smelting, brewing, tanning), leaving their output in the workshop. Era by era: {eras}
- Fields: sow seeds or grain (farming) in a farm on rich soil (grass gives less); ripe in 4 days (not in winter), about 8 grain a seed; a plough and your own ox double it.
- Buildings take their cost (carried, or from your own store beside you) and hours; others can help. A shelter keeps a few things; a store a winter's food. You may close what you build to all but whom you choose; taking from what is closed to you is seen and remembered.
- People: offers (propose) trade goods now, promise goods later, put one in another's service for days, teach a craft, pledge partners or agree to a child; promises are remembered kept or broken. Groups have rules, leaders or votes, laws, dues, treasuries. Writing on tablets or parchment lasts, for those who can read.
- Blows hurt and the struck hit back; armour takes some off. Those who see a blow judge it: against one known to steal or strike it is just, otherwise it is held against the striker. Word of wrongs goes round among friends; kin do not forget a killing. Wolves attack people alone at night or in winter, away from a fire; walls keep them out. Sickness spreads to those beside the sick; rest, food and shelter help.
- This land, {w} steps west to east and {h} north to south, is the whole world."""

ERAS = {0: "foraging (cordage, woodworking, knapping, hideworking, cooking, preserving, herbalism, ornament)",
        1: "first farmers (farming, herding, pottery, weaving, tailoring, dairying, brewing, baking, tanning, dyeing, carpentry, boats, bows)",
        2: "bronze (charcoal, smelting copper and tin, alloying bronze, casting, gold, wheels and ploughs, masonry, writing on clay)",
        3: "iron (bloomery iron, smithing, steel, lime and mortar, glass, coins, mills, roads, horses)",
        4: "learning (reading and parchment, books that teach, medicine, the sky, great works, ships, schools and libraries)"}

STEPS = """Your plan is a list of steps, done in order. Every step walks to where it acts by itself (gather, hunt, take, put, build, give, trade...): never put go before one; go is only for being somewhere. Steps:
- go: x,y; or to: a person; or place: a named place
- gather: item, n (from the land where it lies, or a ripe field)   - hunt: animal (keep: hide or bone, to carry it off too)   - fish: hours
- eat: item (food; or a poultice when sick or hurt)   - rest/sleep: hours   - wait: hours
- craft: item, n (at its workshop if it has one; loads it if it runs by itself)
- build: kind, x,y (optional); a monument (cairn, shrine...) also name, text: carved for all who pass, it outlasts you   - plant: item (seeds, grain or flax)   - fuel: item (feed a fire)
- put: item, n, x,y (into a store, pen, workshop or library)   - take: item, n, x,y (from a building; from: "ground")   - drop: item, n
- give: to, item, n   - trade: x,y, item, n (a posted trade)   - post: x,y, give [{item,qty}], get [{item,qty}] (at your store)
- tame: animal (a rope, a pen of yours with room)   - slaughter: animal (at your pen)
- teach: to, craft   - study: craft (a book)   - write: text (a tablet) or craft (a book)
- propose: to, give/get/promise_give/promise_get [{item,qty}], due_days, hire_days, serve_days, teach (a craft you teach them), learn (a craft they teach you), kind ("pledge" or "child"), text, name   - accept: offer   - refuse: offer
- attack: to   - follow: to, hours   - set_access: x,y, who ("me", "anyone", a group, or names)
- found_group: name, rules, decide ("vote" or "leader")   - invite: to, group   - join: group   - leave: group   - expel: to, group
- call_vote: group, text, act (expel, leader, rules, law, dues), to, value   - vote: vote, choice   - make_law: group, text
- set_dues: group, give [{item,qty}] each season, x,y (a store of yours: it becomes the group's, for its members)
- mark: text (a sign)   - name_place: name   - do: text, hours (anything else, seen by those near)"""

ASK = """Answer with one JSON object: {"thought": what you make of things (one short sentence), "goal": what you are working toward, "plan": [steps, up to 8] (leave it out to go on with your plan), "routine": true to repeat the plan until something changes, "say": words spoken aloud (only if you have something to say), "to": who you speak to, "memory": a short line of notes to yourself, only when something new is worth keeping (it replaces the old), "beliefs": {name: what you now think of them} (rarely), "life": a line to keep for life (rarely), "idea": something you wish could be done that cannot yet (rarely)}.
You will be asked again when your plan is done, or when something happens that concerns you."""


def eras_text(w):
    top = 0
    for p in w.living():
        for c, s in p.skills.items():
            if c in CRAFTS and s >= 0.1:
                top = max(top, CRAFTS[c]["era"])
    shown = [f"{ERAS[e]}" for e in range(0, min(4, top + 1) + 1)]
    rest = " Beyond: more than anyone here has seen." if top + 1 < 4 else ""
    return "; then ".join(shown) + "." + rest


def stage(p, tick):
    y = p.age(tick)
    if y < 14:
        return "a child"
    if y < 45:
        return "grown"
    return "no longer young" if y < 55 else "old"


def trust_word(p, o):
    r = p.rel.get(str(o.id))
    if not r:
        return "a stranger"
    t = r.get("trust", 0)
    kin = r.get("kin")
    word = "you trust them" if t > 0.5 else "friendly" if t > 0.15 else "you distrust them" if t < -0.3 else "known to you"
    if t < 0:
        # the wrong one remembers them for, in a few words
        for e in reversed(p.ledger[-60:]):
            if e[1] == o.id and e[2] in WRONGS:
                txt = e[3][len(o.name) + 1:] if e[3].startswith(o.name + " ") else e[3]
                word += ": " + txt[:70]
                break
    return f"your {kin}, {word}" if kin else word


def person_line(e, p, o):
    w = e.w
    d = dist(p.x, p.y, o.x, o.y)
    where = "beside you" if d <= 1 else f"{d} steps {direction(p.x, p.y, o.x, o.y)}"
    bits = [f"{o.name} ({int(o.age(w.tick))}, {where}, {trust_word(p, o)})"]
    if p.partner == o.id:
        bits.append("your partner")
    act = o.act["do"] if o.act else ("resting" if o.rest else "idle")
    doing = {"gather": f"gathering {o.act.get('item', '') if o.act else ''}", "craft": "making something", "build": "building",
             "hunt": "hunting", "fish": "fishing", "attack": "fighting", "go": "walking", "teach": "teaching"}.get(act, act)
    bits.append(doing)
    worn = I.worn(o.inv)
    if worn:
        bits.append("wears " + ", ".join(I.pretty(k) for k in worn))
    tools = [I.pretty(k) for k in o.inv if I.info(k).get("weapon", 0) >= 3 or k in ("bow", "cart")][:3]
    if tools:
        bits.append("carries " + ", ".join(tools))
    masters = [c.replace("_", " ") for c, s in o.skills.items() if c in CRAFTS and s >= 0.7 and str(o.id) in p.rel]
    if masters:
        bits.append("a master at " + ", ".join(masters[:3]))
    if o.health <= 4:
        bits.append("looks badly hurt")
    if o.satiety <= 3:
        bits.append("looks starved")
    return "- " + "; ".join(bits)


def small_map(e, p, r=5):
    w = e.w
    syms = {"people": {}}
    grid = {}
    for y in range(p.y - r, p.y + r + 1):
        for x in range(p.x - r, p.x + r + 1):
            if not w.inb(x, y):
                continue
            ch = w.t(x, y)
            k = key(x, y)
            if k in w.roads:
                ch = "_"
            d = w.deposits.get(k)
            if d and d["left"] > 0:
                ch = DEPOSITS[d["kind"]]["sym"]
            b = w.building_at(x, y)
            if b:
                ch = BUILDINGS[b.kind]["sym"] if b.done else "?"
            grid[(x, y)] = ch
    for h in w.herds:
        if dist(p.x, p.y, h["x"], h["y"]) <= r:
            grid[(h["x"], h["y"])] = WILD[h["kind"]]["sym"]
    near = sorted((o for o in w.near(p.x, p.y, e.sight(p)) if o.id != p.id), key=lambda o: dist(p.x, p.y, o.x, o.y))
    for i, o in enumerate(near):
        if dist(p.x, p.y, o.x, o.y) <= r:
            grid[(o.x, o.y)] = str(i + 1) if i < 8 else "9"
    grid[(p.x, p.y)] = "@"
    xs = range(p.x - r, p.x + r + 1)
    lines = ["    " + "".join(f"{x % 100:>3}" for x in xs)]
    for y in range(p.y - r, p.y + r + 1):
        if 0 <= y < w.h:
            lines.append(f"{y:>3} " + "".join(f"{grid.get((x, y), ' '):>3}" for x in xs))
    used = set(grid.values())
    legend = ["@ you", "1-8 the people listed below, 9 others"]
    legend += [f"{c} {v['name']}" for c, v in TERRAIN.items() if c in used]
    legend += [f"{v['sym']} {v['name']}" for v in DEPOSITS.values() if v["sym"] in used]
    legend += [f"{v['sym']} {k.replace('_', ' ')}" for k, v in BUILDINGS.items() if v["sym"] in used and any(
        b.kind == k for b in (w.building_at(x, y) for (x, y) in grid) if b)]
    legend += [f"{v['sym']} {v['name']}" for v in WILD.values() if v["sym"] in used]
    if "?" in used:
        legend.append("? unfinished building")
    return "\n".join(lines), "; ".join(dict.fromkeys(legend))


def crafts_text(e, p):
    w = e.w
    L = []
    mine = sorted(((s, c) for c, s in p.skills.items() if c in CRAFTS and s > 0), reverse=True)
    for s, c in mine[:10]:
        at = CRAFTS[c]["at"]
        rs = recipes_for(c)
        place = ""
        if at:
            kinds = [k for k, v in BUILDINGS.items() if c in v["roles"].get("workshop", [])]
            place = f" at a {' or '.join(kinds)}"
        line = f"- {c.replace('_', ' ')}: {e.skill_word(s)}{place}"
        if s >= 0.1 and rs:
            line += ": " + "; ".join(recipe_text(r) for r in rs[:6])
        elif not rs and CRAFTS[c].get("practice"):
            line += f" (practised by {CRAFTS[c]['practice']})"
        L.append(line)
    reach = [c for c, v in CRAFTS.items() if p.skill(c) <= 0 and not e.can_try(p, c)
             and v["era"] <= 1 + max([CRAFTS[x]["era"] for s, x in mine if s >= 0.3] or [0])]
    if reach:
        L.append("Crafts you could take up (untried): " + ", ".join(c.replace("_", " ") for c in reach[:14]) + ".")
    near = [c for c, v in CRAFTS.items() if e.can_try(p, c) and v["era"] <= 2]
    return L


def recipes_for_goal(e, p, words):
    """Full recipes for the crafts a person's goal or plan names, so they can plan the next step."""
    out = []
    low = (words or "").lower()
    for c in CRAFTS:
        if c.replace("_", " ") in low and p.skill(c) < 0.1:
            out += [f"{c.replace('_', ' ')}: " + "; ".join(recipe_text(r) for r in recipes_for(c)[:6])]
    for r in RECIPES:
        if r["out"].replace("_", " ") in low and p.skill(r["craft"]) < 0.1:
            out.append(recipe_text(r) + f" ({r['craft'].replace('_', ' ')})")
    return list(dict.fromkeys(out))[:6]


def holdings(e, p):
    w = e.w
    L = []
    for b in w.buildings.values():
        if b.owner != p.id and b.owner != p.partner:
            continue
        roles = BUILDINGS[b.kind]["roles"]
        bits = [f"{b.kind} at ({b.x},{b.y})" + ("" if b.done else " (unfinished)")]
        if b.inv:
            bits.append("holds " + I.describe(b.inv)[:160])
        if b.crop:
            c = b.crop
            left = c["ripe_at"] - w.tick
            when = f"in {-(-left // TPD)} days" if left > TPD else "by tomorrow" if left > TPD // 2 else "later today"
            bits.append(f"{c['what']} not yet ripe (about {c['yield']}, ripe {when})" if not c.get("ripe") else f"{c['what']} ripe: reap it")
        if b.animals:
            bits.append("animals: " + ", ".join(f"{n} {k}" for k, n in b.animals.items()))
        if b.process:
            r = RECIPES[b.process["recipe"]]
            bits.append(f"working: {I.pretty(r['out'])}, done in {max(0, b.process['done_at'] - w.tick)} hours")
        if b.trade:
            bits.append("posted: " + "; ".join(f"gives {I.describe(t['give'])} for {I.describe(t['get'])}" for t in b.trade))
        if b.access != "owner":
            bits.append(f"open to {b.access if b.access != 'list' else ', '.join(w.people[i].name for i in b.allow if i in w.people)}")
        L.append("- " + "; ".join(bits))
    return L[:12]


def remembered(e, p, seen):
    w = e.w
    by_kind = {}
    for k, v in p.known.items():
        if k in seen or "," not in k:
            continue
        x, y = unkey(k)
        label = v[1] if v[0] != "deposit" else DEPOSITS.get(v[1], {}).get("name", v[1])
        if v[0] == "building":
            b = w.building_at(x, y)
            if not b:
                continue
            label = b.kind + (" of yours" if b.owner in (p.id, p.partner) else " open to you" if w.may_use(p, b) else " (someone else's)")
        d = dist(p.x, p.y, x, y)
        if v[0] == "deposit":
            dep = w.deposits.get(k)
            if not dep or dep["left"] <= 0:
                continue
        by_kind.setdefault((v[0], label), []).append((d, x, y))
    L = []
    for (kind, label), spots in sorted(by_kind.items(), key=lambda kv: min(s[0] for s in kv[1])):
        spots.sort()
        d, x, y = spots[0]
        L.append(f"- {label}: nearest at ({x},{y}), {d} steps {direction(p.x, p.y, x, y)}" + (f" (and {len(spots) - 1} more)" if len(spots) > 1 else ""))
    herds = [v for k, v in p.known.items() if k.startswith("herd")]
    if herds:
        c = Counter(v[1] for v in herds)
        L.append("- herds seen lately: " + ", ".join(f"{WILD[k]['name']} ({n})" for k, n in c.items()))
    return L[:14]


def makeable_now(e, p, most=4):
    """Things one could make at once: a craft one may try, the inputs in hand or in one's own store,
    the tools held, and its workshop near if it needs one. The most worth first."""
    w = e.w
    mine = [b for b in w.buildings.values() if b.done and b.owner in (p.id, p.partner) and "store" in BUILDINGS[b.kind]["roles"]]
    have = Counter(p.inv)
    for b in mine:
        have.update(b.inv)
    out = []
    for r in RECIPES:
        c = r["craft"]
        if e.can_try(p, c) or (p.skill(c) <= 0 and CRAFTS[c]["era"] > 0) or r["out"] in [o for _, _, o in out]:
            continue
        if not all(have.get(k, 0) >= n for k, n in r["ins"].items()):
            continue
        if any(not any(p.inv.get(o) for o in tool_options(t)) for t in r["tools"]):
            continue
        if CRAFTS[c]["at"] and not e.workshop_for(p, c):
            continue
        useful = bool(use_text(r["out"]))
        out.append((useful, I.info(r["out"]).get("worth", 1) * r["n"], r["out"]))
    out.sort(reverse=True)
    return [o.replace("_", " ") + use_text(o) for _, _, o in out[:most]]


def step_text(st):
    """A step in a few words: "gather clay 5", "craft pot", "go (31,29)"."""
    d = st.get("do", "")
    bits = [d]
    for k in ("item", "kind", "craft", "animal"):
        if st.get(k):
            bits.append(str(st[k]).replace("_", " "))
            break
    if isinstance(st.get("n"), int) and st["n"] > 1:
        bits.append(str(st["n"]))
    to = st.get("to")
    if to is not None:
        bits.append("to " + (str(to) if not isinstance(to, int) else "someone"))
    if d == "go" and st.get("x") is not None and st.get("y") is not None:
        bits.append(f"({st['x']},{st['y']})")
    if st.get("hours") and d in ("rest", "sleep", "wait", "fish", "follow"):
        bits.append(f"{st['hours']}h")
    return " ".join(bits)


def build_prompt(e, p):
    w = e.w
    t = w.tick
    L = [RULES.format(eras=eras_text(w), w=w.w, h=w.h), "", STEPS, "", "=" * 20]
    L.append(f"You are {p.name}, {int(p.age(t))} years old ({stage(p, t)}). By nature you are {p.temperament}. "
             f"What you want most in life: {p.wants}." + (f" Who you have become: {p.self_view}" if p.self_view else ""))
    for tk, line in p.life[:6]:
        L.append(f"Kept for life ({w.when(tk)}): {line}")
    nxt = ["summer", "autumn", "winter", "spring"][["spring", "summer", "autumn", "winter"].index(w.season())]
    L.append(f"It is {w.when()} of {w.season()}, year {w.year() + 1}. {nxt.capitalize()} comes in {DPS - w.day() % DPS} days."
             + (" It is dark." if w.is_night() else ""))
    fullness = "starving" if p.satiety <= 0 else "very hungry" if p.satiety <= 4 else "hungry" if p.satiety <= 8 else "fed" if p.satiety < 17 else "full"
    L.append(f"Your body: health {int(p.health)}/{p.max_health(t)}, {fullness} ({int(p.satiety)}/20)"
             + ("; you are sick" if p.sick else "") + (f"; expecting a child in {max(0, p.pregnant['due'] - t)} hours" if p.pregnant else "") + ".")
    worn = I.worn(p.inv)
    L.append(f"You carry: {I.describe(p.inv)[:400]} (load {p.load():.0f} of {p.capacity(t):.0f})."
             + (f" You wear: {', '.join(I.pretty(k) for k in worn)} (warmth {I.warmth(p.inv)})." if worn else " You wear nothing warm."))
    home = w.buildings.get(p.home)
    if home:
        L.append(f"Your home: the {home.kind} at ({home.x},{home.y}).")
    # how long one's food would last (about 2.5 a day), so a full larder reads as one
    worth = lambda inv: sum(I.info(k).get("food", 0) * n for k, n in inv.items())
    carried = worth(p.inv)
    kept = sum(worth(b.inv) for b in w.buildings.values() if b.done and b.owner in (p.id, p.partner)
               and "store" in BUILDINGS[b.kind]["roles"])
    days = lambda f: "none" if f < 1 else f"about {max(1, round(f / 2.5))} day{'s' if round(f / 2.5) > 1 else ''}"
    L.append(f"Food: you carry {days(carried)}" + (f"; your stores hold {days(kept)}" if kept else "; you keep none in store") + ".")
    if w.season() in ("autumn", "winter"):
        # a winter night as it would find you: clothes, and the shelter of your home if you sleep there
        sh = BUILDINGS[home.kind]["roles"].get("shelter", {}).get("warmth", 0) if home and home.done else 0
        have = I.warmth(p.inv) + sh
        L.append(f"A winter night would find you with warmth {have} of 3 ("
                 + (f"clothes {I.warmth(p.inv)}, " if I.warmth(p.inv) else "no warm clothes, ")
                 + (f"your {home.kind} {sh}" if sh else "no shelter of your own") + "; a fire beside you adds 2)."
                 + (" Below 3 the cold hurts." if have < 3 else ""))
    hold = holdings(e, p)
    if hold:
        L.append("What is yours:")
        L += hold
    if p.partner and w.people.get(p.partner):
        o = w.people[p.partner]
        L.append(f"Your partner: {o.name}" + ("" if o.alive else " (dead)") + ".")
    kids = [w.people[c] for c in p.children if c in w.people and w.people[c].alive]
    if kids:
        L.append("Your children: " + ", ".join(f"{k.name} ({int(k.age(t))})" for k in kids) + ".")
    for gid in p.groups:
        g = w.groups.get(gid)
        if g and g.dissolved is None:
            lead = "you" if g.leader == p.id else w.people[g.leader].name
            L.append(f"You belong to {g.name} ({'members vote' if g.decide == 'vote' else 'led by ' + lead}; {len(g.members)} members). Rules: \"{g.rules}\""
                     + ("".join(f" Law: \"{text}\"" for _, text, _ in g.laws[-3:]) if g.laws else "")
                     + (f" Dues: {I.describe(g.dues)} a season." if g.dues else ""))
    for s in w.services:
        if not s["done"] and p.id in (s["master"], s["servant"]):
            other = w.people[s["servant"] if s["master"] == p.id else s["master"]]
            left = max(1, (s["end"] - t) // TPD)
            L.append(f"{'In your service: ' + other.name if s['master'] == p.id else 'You serve ' + other.name} for {left} more days"
                     + (f" (terms: \"{s['terms']}\")" if s.get("terms") else "") + ".")
    for pr in w.promises:
        if not pr["done"] and p.id in (pr["by"], pr["to"]):
            other = w.people[pr["to"] if pr["by"] == p.id else pr["by"]]
            days = max(0, (pr["due"] - t) // TPD)
            L.append(f"{'You promised ' + other.name if pr['by'] == p.id else other.name + ' promised you'} {I.describe(pr['goods'])} within {days} days"
                     + (" (hand it over beside them)" if pr["by"] == p.id else "") + ".")
    L.append("")
    L.append("Your crafts:")
    L += crafts_text(e, p) or ["- none yet"]
    now = makeable_now(e, p)
    if now:
        L.append("You could make now, with what you carry or keep: " + "; ".join(now) + ".")
    extra = recipes_for_goal(e, p, (p.intent or {}).get("goal", "") + " " + p.memory)
    if extra:
        L.append("What the things you have in mind take: " + " | ".join(extra))
    L.append("")
    r = e.sight(p)
    mp, legend = small_map(e, p, min(r, 5))
    L.append(f"Around you (x grows east, y south; you are at ({p.x},{p.y}) on {TERRAIN[w.t(p.x, p.y)]['name']}):")
    L.append(mp)
    L.append("Key: " + legend)
    near = sorted((o for o in w.near(p.x, p.y, r) if o.id != p.id), key=lambda o: dist(p.x, p.y, o.x, o.y))
    if near:
        L.append("People you see:")
        L += [person_line(e, p, o).replace("- ", f"{i + 1}. ", 1) for i, o in enumerate(near[:8])]
        if len(near) > 8:
            dirs = Counter(direction(p.x, p.y, o.x, o.y) for o in near[8:])
            L.append(f"- and {len(near) - 8} more: " + ", ".join(f"{n} {d}" for d, n in dirs.items()))
    seen = set()
    things = []
    for x, y in w.beside(p.x, p.y, r):
        k = key(x, y)
        b = w.building_at(x, y)
        if b and b.done and "monument" in BUILDINGS[b.kind]["roles"] and (b.name or b.text):
            o = w.people.get(b.owner)
            things.append((dist(p.x, p.y, x, y), f"- a {b.kind} at ({x},{y})" + (f" called {b.name}" if b.name else "")
                           + f", raised by {o.name if o else 'someone long gone'}" + (f"; carved: \"{b.text}\"" if b.text else "")))
            seen.add(k)
        elif b and b.owner not in (p.id, p.partner):
            o = w.people.get(b.owner)
            extra = ""
            if b.trade:
                extra = "; posted: " + "; ".join(f"gives {I.describe(t['give'])} for {I.describe(t['get'])}" for t in b.trade)
            if b.process:
                extra += "; working"
            things.append((dist(p.x, p.y, x, y), f"- {b.kind} at ({x},{y}), {o.name + chr(39) + 's' if o else 'no one' + chr(39) + 's'}"
                           + ("" if b.done else " (unfinished)") + ("; open to you" if w.may_use(p, b) and b.owner != p.id else "") + extra))
            seen.add(k)
        pile = w.piles.get(k)
        if pile:
            things.append((dist(p.x, p.y, x, y), f"- on the ground at ({x},{y}): {I.describe(pile)[:120]}"))
        sg = w.signs.get(k)
        if sg:
            for au, text, tk, written in sg[-2:]:
                who = w.people.get(au)
                things.append((dist(p.x, p.y, x, y), f"- a sign at ({x},{y}) by {who.name if who else 'someone'}: \"{text}\""))
        d = w.deposits.get(k)
        if d:
            seen.add(k)
    for h in w.herds:
        if dist(p.x, p.y, h["x"], h["y"]) <= r:
            things.append((dist(p.x, p.y, h["x"], h["y"]), f"- {h['n']} {WILD[h['kind']]['name']} at ({h['x']},{h['y']})"))
    for pk in w.packs:
        if dist(p.x, p.y, pk["x"], pk["y"]) <= r:
            things.append((0, f"- a pack of {pk['n']} wolves at ({pk['x']},{pk['y']})!"))
    if things:
        L.append("Things you see:")
        L += [t for _, t in sorted(things)[:12]]
    places = [pl for pl in w.places if dist(p.x, p.y, pl[0], pl[1]) <= r + 6]
    if places:
        L.append("Named places near you: " + "; ".join(f"{pl[2]} at ({pl[0]},{pl[1]})" for pl in places[:6]) + ".")
    mem = remembered(e, p, seen)
    if mem:
        L.append("Places you know of (out of sight or nearby):")
        L += mem
    offers = [x for x in w.offers.values() if x["to"] == p.id]
    if offers:
        L.append("Offers to you:")
        L += [f"- offer {x['id']} from {w.people[x['from']].name}: {e.offer_text(x, p)}" for x in offers]
    votes = [v for v in w.votes.values() if not v["done"] and w.groups.get(v["group"]) and p.id in w.groups[v["group"]].members]
    for v in votes:
        L.append(f"Vote {v['id']} open in {w.groups[v['group']].name}: \"{v['question']}\" ({len(v['yes'])} yes, {len(v['no'])} no).")
    L.append("")
    L.append(f"What happened since you last decided ({w.when(p.last_decided) if p.last_decided >= 0 else 'the start'}):")
    ev = p.events[-14:]
    if len(p.events) > 14:
        L.append(f"- ({len(p.events) - 14} earlier things left out)")
    L += [f"- [{w.when(tk)}] {text}" for tk, text in ev] or ["- nothing of note"]
    if p.wake:
        L.append("Why you are deciding now: " + "; ".join(p.wake[:4]) + ".")
    if p.intent and p.intent.get("goal"):
        L.append(f"Your goal until now: {p.intent['goal']}" + (" (a routine)" if p.intent.get("routine") else "") + ".")
    doing_now = ([step_text(p.act)] if p.act else []) + [step_text(st) for st in (p.intent or {}).get("plan") or []]
    if doing_now:
        L.append("Your plan, still to do: " + "; ".join(doing_now[:8]) + ". (Leave plan out to go on with it.)")
    if p.memory:
        L.append(f"Your notes to yourself: {p.memory}")
    if p.beliefs:
        L.append("What you think of people: " + "; ".join(f"{k}: {v}" for k, v in list(p.beliefs.items())[-8:]))
    L.append("")
    L.append(ASK)
    return "\n".join(L)


# The answer's shape (Gemini-style types; the gateway turns it into plain JSON Schema for others).
GOODS = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"item": {"type": "STRING"}, "qty": {"type": "INTEGER"}}}}
STEP = {"type": "OBJECT", "properties": {
    "do": {"type": "STRING", "enum": VERBS},
    **{k: {"type": "STRING"} for k in ("item", "to", "animal", "kind", "craft", "text", "name", "group", "place", "from",
                                         "who", "choice", "act", "value", "rules", "decide")},
    **{k: {"type": "INTEGER"} for k in ("n", "x", "y", "hours", "offer", "vote", "due_days", "hire_days", "serve_days")},
    **{k: GOODS for k in ("give", "get", "promise_give", "promise_get")},
    "teach": {"type": "STRING"}, "learn": {"type": "STRING"}}, "required": ["do"]}
SCHEMA = {"type": "OBJECT", "properties": {
    "thought": {"type": "STRING"}, "goal": {"type": "STRING"},
    "plan": {"type": "ARRAY", "items": STEP}, "routine": {"type": "BOOLEAN"},
    "say": {"type": "STRING"}, "to": {"type": "STRING"}, "memory": {"type": "STRING"},
    "beliefs": {"type": "OBJECT", "properties": {}}, "life": {"type": "STRING"}, "idea": {"type": "STRING"}},
    "required": ["thought", "goal"]}
