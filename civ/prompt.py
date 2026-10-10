"""What a person perceives, as text for a language model, and the shape of the answer.

The text never mentions a simulation, a game, agents, ticks or turns. It shows what matters to
this person: their body, their things, their crafts and what is within reach, the land around,
the people they see, what they remember, and what happened since they last thought."""
import re
from collections import Counter

from .content import TERRAIN, DEPOSITS, WILD, TAME, BUILDINGS, CRAFTS, RECIPES
from .content import items as I
from .content.crafts import use_text, tool_options
from .content.crafts import recipes_for, recipe_text
from .content.peoples import PEOPLES, customs_text
from .news import news_text
from .belief import rite_text
from .acts import VERBS, WRONGS, mend_text
from .world import key, unkey, dist, direction, TPD, DPS

RULES_VERSION = "c82"

RULES = """How the world works:
- A day is 12 hours, the last 3 night; a season 10 days; a year 40. Grown at 14; past sixty, weakening from 45.
- Food: 2-3 a day (berries 1, grain 2, fish 3, meat 4, bread 5); hungry, you eat what you carry. Fresh food spoils in days; smoked, dried, salted, grain, cheese, nuts keep, best in a store or jars.
- Winter nights hurt below warmth 3: shelter or house 2-3, a fire beside you 2, clothes (cloak 2, fur coat 3, tunic, hat, shoes 1). Nothing grows in winter.
- Land: forest wood, fibre, hay; hills stone; marsh reeds, clay; water fish (fished hard, a water thins). In places clay, flint, flax, wild grain, berries, nuts, herbs, salt; in hills copper (green), tin (black), iron (red), limestone, gold. Places are worked out; plants grow back. Ways walked often become trails, quicker to walk. Deer, boar, aurochs, goats, sheep, horses roam; hunters together kill more. Goats, sheep, cattle, pigs can be tamed (herding, a rope, a pen): milk, wool, young, meat.
- Crafts: skill (untried, beginner, able, master) comes by trying (a beginner often fails) or being taught; unpractised a season, it grows rusty; masters work faster and waste less. Some need a craft first or a workshop (kiln, loom, oven, tannery, furnace...); some run by themselves once loaded. {eras}
- Fields: sow seeds or grain in a farm, on rich soil best; ripe in 4 days, about 8 a seed, not in winter.
- Buildings take their cost (carried, or from your store beside you) and hours; others can help. Close yours to whom you choose; taking from it is known if seen or tallied in writing. Buildings weather and fall unless mended (one of what they are made of); one in your service may mend yours. What the dead leave to no heir anyone may claim. Things left on the ground are soon lost. A mill grinds grain put in it; at a school a lesson reaches all who sit there; an aqueduct waters fields near it; from a tower one sees far.
- People: propose trades, promises, service, teaching, partnership or a child; promises are remembered kept or broken, a written one owed to whoever holds it, one made at a shrine or temple an oath: broken, infamy among all who hear and share one's gods. A good writer who writes often comes to read at length. Groups have rules, leaders or votes, laws, dues, treasuries. Leaders may order their people, who obey as far as they trust and owe them; a group may swear fealty to another, paying tribute each autumn for protection. A leader may muster a band and lead it to raid; those who live where it falls stand together, the stronger behind a wall, and neighbours bound to them run to help. Spoils bind a band to its leader, beatings and the fallen loosen it; a lord who leaves the sworn undefended loses them. Two leaders may swear peace (a raid then breaks it). A winning band may carry off captives for ransom.
- Blows hurt; the struck hit back. Onlookers judge a blow: just against a known thief or striker, else held against the striker. Word of wrongs spreads; kin remember a killing. Wolves take people alone at night or in winter, away from fire; walls keep them out. Sickness spreads; rest, food, shelter help.
- This land, {w} by {h} steps, is the whole world."""

ERAS = {0: "foraging (cordage, woodworking, knapping, hideworking, cooking, preserving, herbalism, ornament)",
        1: "first farmers (farming, herding, pottery, weaving, tailoring, dairying, brewing, baking, tanning, dyeing, carpentry, boats, bows)",
        2: "bronze (charcoal, smelting copper and tin, alloying bronze, casting, gold, wheels and ploughs, masonry, writing on clay)",
        3: "iron (bloomery iron, smithing, steel, lime and mortar, glass, coins, mills, roads, horses)",
        4: "learning (reading and parchment, books that teach, medicine, the sky, great works, ships, schools and libraries)"}

STEPS = """Your plan: steps done in order. A step walks to where it acts by itself; go is only for being somewhere. Steps:
- go: x,y | to: person | place: a named place   - gather: item, n (land or ripe field)   - hunt: animal (keep: hide or bone)   - fish: hours
- eat: item   - rest/sleep/wait: hours   - craft: item, n (at its workshop if it needs one)
- build: kind, x,y (a monument also name, text)   - plant: item   - fuel: item (a fire)   - mend: x,y
- put: item, n, x,y (store, pen, workshop)   - take: item, n, x,y (from: "ground" for a pile)   - drop: item, n   - give: to, item, n{herd}{trade}
- propose: to, give/get/promise_give/promise_get [{item,qty}], due_days, hire_days, serve_days, teach, learn, kind ("pledge"|"child"|"fealty": your group swears to theirs, give = tribute each autumn|"homage": theirs to yours, get = tribute|"peace": your people and theirs not to raid each other, days), text   - accept: offer   - refuse: offer
- attack: to   - follow: to, hours   - set_access: x,y, who ("me", "anyone", a group, names)   - claim: x,y (empty building){teach}{write}
- found_group: name, rules, decide ("vote"|"leader")   - invite: to, group   - join: group   - leave: group{groups}
- mark: text (a sign)   - name_place: name   - do: text, hours (anything else)"""

HERD_STEP = """
- tame: animal (a rope, your pen with room)   - slaughter: animal (at your pen)"""
TRADE_STEP = """
- trade: x,y, item, n (a posted trade)   - post: x,y, give [{item,qty}], get [{item,qty}] (at your store)"""
TEACH_STEP = """   - teach: to, craft"""
ORDER_STEP = """
- order: to (one of your people, or "all"), task (gather, hunt, fish, craft, build, mend, plant, put, take, go, follow, fuel) with that step's item, n, kind, x,y, days (they work for you: what they gather or make comes to your store, what they build is yours)
- muster: hours (call your people into a band)   - raid: x,y, take (true: carry off captives to ransom), share ("each" keeps what they carry, "half" or "mine": to your store at home) (lead your band to take what is stored there)   - disband"""
CAPTIVE_STEP = """
- ransom: who (pay their captor what is asked, face to face; they go free)   - release: who (let one you hold go)   - escape (if you are held)"""
WRITE_STEP = """
- write: text, x,y (tablet in hand; x,y of your store to keep a tally) | promise: a name"""

ASK = """Answer with one JSON object: {"thought": one short sentence, "goal": what you work toward, "plan": [up to 8 steps] (leave out to go on), "routine": true to repeat the plan, "say": words aloud (if any), "to": whom, "memory": a short note replacing the old (only if new), "beliefs": {name: what you think}, "life": a line kept for life, "idea": a wish that cannot yet be done (these three rarely)}.
You are asked again when your plan is done or something concerns you."""


MOVED = re.compile(r"^You (put|took) (\d+) (.+?) (into|from) the (\w+)\.$")
HEARD = re.compile(r"^(\w+) \(to (\w+)\): ")


def compact_events(ev, me):
    """What happened, said shortly: things put away or taken one after another on one line ("You put 6 fibre,
    3 seeds into the store."), and of talk between others only the last three (c54: a third of the lines)."""
    out = []
    for tk, text in ev:
        m = MOVED.match(text)
        last = MOVED.match(out[-1][1]) if out and out[-1][1].startswith("You ") else None
        if m and last and (m.group(1), m.group(4), m.group(5)) == (last.group(1), last.group(4), last.group(5)):
            out[-1] = (out[-1][0], f"You {m.group(1)} {last.group(2)} {last.group(3)}, {m.group(2)} {m.group(3)} {m.group(4)} the {m.group(5)}.")
            continue
        out.append((tk, text))
    talk = [i for i, (_, text) in enumerate(out) if (h := HEARD.match(text)) and me not in (h.group(1), h.group(2))]
    drop = set(talk[:-3])
    last = {text: i for i, (_, text) in enumerate(out)}            # the same news twice is said once, the latest
    return [x for i, x in enumerate(out) if i not in drop and last[x[1]] == i]


def market_text(w, p, r):
    """A market one sees or knows: the trades posted at the stores beside it, open to all who stand there (C5)."""
    out = []
    for m in w.buildings.values():
        if not (m.done and "market" in BUILDINGS[m.kind]["roles"]):
            continue
        if dist(p.x, p.y, m.x, m.y) > r and key(m.x, m.y) not in p.known:
            continue
        offers = []
        for b in w.buildings.values():
            if b.trade and b.owner != p.id and dist(m.x, m.y, b.x, b.y) <= 2:
                o = w.people.get(b.owner)
                offers += [f"{o.name if o else 'a store'}'s gives {I.describe(t['give'])} for {I.describe(t['get'])}"
                           for t in b.trade if all(b.inv.get(k, 0) >= n for k, n in t["give"].items())]
        if offers:
            out.append(f"The market at ({m.x},{m.y}), trade there with any of: " + "; ".join(offers[:6]) + ".")
        if len(out) >= 2:
            break
    return out


def writings_text(w, p):
    """What the writings one carries say, to one who can read them (at most three)."""
    out = []
    for k in p.inv:
        if ":" in k and k.split(":")[0] in ("tablet", "parchment"):
            wr = w.writings.get(int(k.split(":")[1])) if k.split(":")[1].isdigit() else None
            if wr:
                can = p.skill("literacy" if wr["on"] == "parchment" else "writing") >= 0.1 or p.skill("literacy") >= 0.2
                out.append(f"{k} says \"{wr['text'][:80]}\"" if can else f"{k} bears marks you cannot read")
    return (". Written: " + "; ".join(out[:3])) if out else ""


def tried_again(e, p):
    """Steps refused for the same reason twice or more these last days (engine.refused keeps three
    days), said back plainly, so a hunter in a hunted-out land stops asking for deer."""
    seen = {}
    for t, step, why in e.refused.get(p.id, []):
        k = (step.get("do"), why.split(":")[0][:70])
        seen.setdefault(k, [0, why])[0] += 1
    out = [f"{do} ({n} times): {why[:110]}" for (do, _), (n, why) in seen.items() if n >= 2]
    return out[:2]


GROUP_STEPS = """   - expel: to, group   - renounce: group (its fealty)   - join_band: to (a leader who calls you)
- call_vote: group, text, act (expel, leader, rules, law, dues), to, value   - vote: vote, choice   - make_law: group, text (a tablet in hand writes it down)"""
DUES_STEP = """
- set_dues: group, give [{item,qty}] each season, x,y (a store of yours: it becomes the group's, for its members)"""
LETTERS_STEP = """
- study: craft (a book, or one in a library)   - write: craft (a blank book: a book that teaches the craft)"""


def steps_text(e, p):
    """The steps, each only for those who can use it: a group's business for its members and leaders, herding
    for those with a pen or the craft, trade for store keepers or at a market, teaching for the able, writing for
    those who can write: what one cannot use costs a decision's worth of words (P1)."""
    w = e.w
    mine = [w.groups[g] for g in p.groups if w.groups.get(g) and w.groups[g].dissolved is None]
    extra = (GROUP_STEPS if mine else "") + (DUES_STEP if any(g.leader == p.id for g in mine) else "")
    own = [b for b in w.buildings.values() if b.owner in (p.id, p.partner) and b.done]
    roles = [BUILDINGS[b.kind]["roles"] for b in own]
    herd = p.skill("herding") > 0 or any("pen" in r for r in roles) or any(
        WILD[h["kind"]].get("tame") and dist(p.x, p.y, h["x"], h["y"]) <= 10 for h in w.herds)
    trade = any("store" in r for r in roles) or any(b.trade and dist(p.x, p.y, b.x, b.y) <= 8 for b in w.buildings.values())
    letters = p.skill("writing") > 0 or p.skill("reading") > 0 or any(k.split(":")[0] in ("tablet", "book", "parchment") for k in p.inv)
    s = (STEPS.replace("{groups}", extra).replace("{herd}", HERD_STEP if herd else "")
         .replace("{trade}", TRADE_STEP if trade else "")
         .replace("{teach}", TEACH_STEP if any(c in CRAFTS and v >= 0.3 for c, v in p.skills.items()) else "")
         .replace("{write}", WRITE_STEP if letters else ""))
    if e.followers(p):                               # a leader or a master: one's people work at one's word (Phase 1.4)
        s += ORDER_STEP
    if p.held or w.holding.get(p.id) or any(str(q) in p.rel for qs in w.holding.values() for q in qs):
        s += CAPTIVE_STEP                            # captives and their ransom (c76)
    if p.skill("literacy") >= 0.3:                   # reading at length: books (c61: "you cannot read" 50 times)
        s += LETTERS_STEP
    return s


def eras_text(w):
    top = 0
    for p in w.living():
        for c, s in p.skills.items():
            if c in CRAFTS and s >= 0.1:
                top = max(top, CRAFTS[c]["era"])
    now, nxt = ERAS[top], ERAS.get(top + 1)
    return f"The age you live in: {now}." + (f" Then: {nxt.split(' (')[0]}." if nxt else "")


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
    folk = f"{PEOPLES[o.people]['folk'].split()[0]}, " if o.people and o.people != p.people and o.people in PEOPLES else ""
    bits = [f"{o.name} ({folk}{int(o.age(w.tick))}, {where}, {trust_word(p, o)})"]
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
        bits.append("a master at " + ", ".join(masters[:2]))
    fame = getattr(w, "fame", None)
    if fame and o.renown >= max(5, fame[0]):
        bits.append("known far and wide" if o.renown >= fame[1] else "much spoken of")
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
            elif k in w.trails:
                ch = "+"
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
    legend = ["@ you", "1-8 people below, 9 others"]
    legend += [f"{c} {v['name']}" for c, v in TERRAIN.items() if c in used]
    legend += [f"{v['sym']} {v['name']}" for v in DEPOSITS.values() if v["sym"] in used]
    legend += [f"{v['sym']} {k.replace('_', ' ')}" for k, v in BUILDINGS.items() if v["sym"] in used and any(
        b.kind == k for b in (w.building_at(x, y) for (x, y) in grid) if b)]
    legend += [f"{v['sym']} {v['name']}" for v in WILD.values() if v["sym"] in used]
    if "?" in used:
        legend.append("? unfinished building")
    if "+" in used:
        legend.append("+ trail")
    return "\n".join(lines), "; ".join(dict.fromkeys(legend))


def crafts_text(e, p):
    w = e.w
    L = []
    mine = sorted(((s, c) for c, s in p.skills.items() if c in CRAFTS and s > 0), reverse=True)
    for i, (s, c) in enumerate(mine[:8]):
        at = CRAFTS[c]["at"]
        rs = recipes_for(c)
        place = ""
        if at:
            kinds = [k for k, v in BUILDINGS.items() if c in v["roles"].get("workshop", [])]
            place = f" at a {' or '.join(kinds)}"
        line = f"- {c.replace('_', ' ')}: {e.skill_word(s)}{place}"
        if s >= 0.1 and rs and i < 5:                           # the five best crafts in full (P1)
            line += ": " + "; ".join(short_recipes(rs, 4 if s >= 0.3 else 3))
        elif not rs and CRAFTS[c].get("practice"):
            line += f" (practised by {CRAFTS[c]['practice']})"
        L.append(line)
    reach = [c for c, v in CRAFTS.items() if p.skill(c) <= 0 and not e.can_try(p, c)
             and v["era"] <= 1 + max([CRAFTS[x]["era"] for s, x in mine if s >= 0.3] or [0])]
    if reach:
        L.append("Crafts you could take up (untried): " + ", ".join(c.replace("_", " ") for c in reach[:6]) + ".")
    near = [c for c, v in CRAFTS.items() if e.can_try(p, c) and v["era"] <= 2]
    return L


def short_recipes(rs, most):
    """Recipes in few words, those making the same thing on one line: "rope = fibre 3 | reeds 3"."""
    by = {}
    for r in rs:
        ins = " + ".join(f"{k.replace('_', ' ')} {n}" for k, n in r["ins"].items())
        tools = [("an axe" if t == "_axe" else "a " + t.replace("_", " ")) for t in r["tools"]]
        if tools:
            ins += " with " + " and ".join(tools)
        if r["process"]:
            ins += " (unattended)"
        head = r["out"].replace("_", " ") + (f" x{r['n']}" if r["n"] > 1 else "") + use_text(r["out"])
        by.setdefault(head, []).append(ins)
    return [f"{head} = {' | '.join(ins)}" for head, ins in list(by.items())[:most]]


def recipes_for_goal(e, p, words):
    """Full recipes for the crafts a person's goal or plan names, so they can plan the next step."""
    out, named = [], set()
    low = (words or "").lower()
    for c in CRAFTS:
        if c.replace("_", " ") in low and p.skill(c) < 0.1:
            named.add(c)
            out += [f"{c.replace('_', ' ')}: " + "; ".join(recipe_text(r) for r in recipes_for(c)[:6])]
    for r in RECIPES:
        if r["out"].replace("_", " ") in low and p.skill(r["craft"]) < 0.1 and r["craft"] not in named:
            out.append(recipe_text(r) + f" ({r['craft'].replace('_', ' ')})")
    return list(dict.fromkeys(out))[:6]


def holdings(e, p):
    w = e.w
    L = []
    bare = {}
    for b in w.buildings.values():
        if b.owner != p.id and b.owner != p.partner:
            continue
        full = BUILDINGS[b.kind]["hp"]
        worn = b.done and b.hp <= full * 0.5 and "monument" not in BUILDINGS[b.kind]["roles"]
        if b.done and not worn and not (b.inv or b.crop or b.animals or b.process or b.trade) and b.access == "owner":
            bare.setdefault(b.kind, []).append(f"({b.x},{b.y})")
            continue
        roles = BUILDINGS[b.kind]["roles"]
        bits = [f"{b.kind} at ({b.x},{b.y})" + ("" if b.done else " (unfinished)")
                + (f" ({'falling apart' if b.hp <= full * 0.3 else 'worn'}: mend it with {mend_text(b)})" if worn else "")]
        if b.inv:
            top = dict(sorted(b.inv.items(), key=lambda kv: -kv[1])[:4])
            bits.append("holds " + I.describe(top) + (" and more" if len(b.inv) > 4 else ""))
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
        names = ', '.join(w.people[i].name for i in b.allow if i in w.people)
        if b.access != "owner" and (b.access != "list" or names):
            bits.append(f"open to {b.access if b.access != 'list' else names}")
        L.append("- " + "; ".join(bits))
    L += [f"- {k}{'s' if len(at) > 1 else ''} at {', '.join(at[:8])}" + (f" and {len(at) - 8} more" if len(at) > 8 else "")
          for k, at in bare.items()]
    return L[:9]


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
    return L[:5]


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


def people_lines(e, p):
    """One's people, tongue, ways and gods; the land one is in and its year; what one thinks of other peoples
    (grand world, Phase 2). Nothing in the old lands."""
    w = e.w
    out = []
    if p.people and p.people in PEOPLES:
        d = PEOPLES[p.people]
        own = (w.peoples.get(p.people) or {}).get("name", "")
        tongues = [PEOPLES[k]["tongue"]["word"] for k in PEOPLES if k != p.people and p.skill(f"tongue:{k}") >= 0.5]
        out.append(f"You are of the {own} ({d['folk']}) and speak {d['tongue']['word']}" + (", " + ", ".join(tongues) if tongues else "")
                   + f". Your people's ways: {customs_text(p.people)}. Your gods: {' and '.join(d['gods'])}.")
        out += rite_text(e, p)
    r = w.region_at(p.x, p.y)
    if r:
        yr = w.years.get(str(r["id"]), "")
        held = (w.peoples.get(r.get("people")) or {}).get("name")
        out.append(f"You are in {r.get('name') or 'the wilds'} ({r['kind']}" + (f", the {held}'s land" if held else ", no people's land") + ")"
                   + {"hard": "; a hard year here: fields and wild plants bear little, herds do not grow.",
                      "lean": "; a lean year here: fields and wild plants bear less."}.get(yr, "."))
    strong = [(k, v) for k, v in p.feel.items() if abs(v) >= 0.3 and k in w.peoples]
    if strong:
        out.append("What you think of other peoples: " + "; ".join(
            f"the {w.peoples[k]['name']} ({PEOPLES[k]['folk']}): {'you think well of them' if v > 0 else 'you distrust them' if v > -0.6 else 'you hate them'}"
            for k, v in sorted(strong, key=lambda kv: kv[1])[:3]) + ".")
    return out


def realm_text(e, p):
    """A ruler's view (grand world, Phase 7, c78): one's realm (one's own people, the groups sworn to one, who can
    fight, how long the stores would feed them) and the neighbouring peoples' chiefs (where, how many, how they
    stand toward one): what a ruler must know to choose peace, homage or a raid. Only for those who lead a group of eight or more, or
    have groups sworn to them."""
    w = e.w
    g = e.group_of(p, None, lead=True)
    if not g:
        return []
    sworn = e.sworn_to(g)
    if not sworn and len(g.members) < 8:
        return []                                   # a household's head: their group line says enough
    folk = [w.people[i] for i in e.followers(p)] + [p]
    fight = sum(1 for q in folk if q.adult(w.tick) and q.health > 5 and not q.held)
    food = 0
    for q in folk:
        for b in w.owned(q.id):
            if b.done and "store" in BUILDINGS[b.kind]["roles"]:
                food += sum(I.info(k).get("food", 0) * n for k, n in b.inv.items() if isinstance(n, (int, float)))
    days = int(food / max(1, 2.5 * len(folk)))
    out = [f"Your realm: {len(folk)} people" + (" (" + ", ".join(f"{h.name} {len(h.members)}" for h in sworn[:5]) + " sworn to you)" if sworn else "")
                   + f"; about {fight} who can fight; food in their stores for about {days} days."]
    mine_ids = {h.id for h in e.realms(p)} | {h.id for h in sworn}
    home = w.buildings.get(p.home)
    hx, hy = (home.x, home.y) if home else (p.x, p.y)
    near = []
    for h in w.groups.values():
        if h.dissolved is not None or h.parent or h.id in mine_ids or h.leader not in w.people:
            continue
        lead = w.people[h.leader]
        lh = w.buildings.get(lead.home)
        x, y = (lh.x, lh.y) if lh else (lead.x, lead.y)
        d = dist(hx, hy, x, y)
        pk = e.peace_between(p, lead)
        if (d <= 45 and len(h.members) >= 4) or pk:
            near.append((d, h, lead, x, y, pk))
    near.sort(key=lambda t: t[0])
    if near:
        out.append("Peoples and chiefs around you:")
        for d, h, lead, x, y, pk in near[:4]:
            size = len(h.members) + sum(len(k.members) for k in e.sworn_to(h))
            folk_of = PEOPLES.get(lead.people, {}).get("folk", "")
            r = p.rel.get(str(lead.id), {}).get("trust")
            feel = p.feel.get(lead.people, 0) if lead.people != p.people else 0
            stance = "at peace with you until day " + str(max(pk[0].peace.get(str(pk[1].id), 0), 0) // TPD + 1) if pk else \
                "hostile" if (r is not None and r < -0.3) or feel < -0.5 else "friendly" if (r or 0) > 0.3 else "known to you" if r is not None else "strangers to you"
            out.append(f"- {h.name}" + (f" ({folk_of})" if folk_of else "") + f", {lead.name}" + (f" its {h.title}" if h.title else " leading")
                       + f", {d} steps {direction(hx, hy, x, y)} at ({x},{y}): about {size} people; {stance}.")
    return out


def band_text(e, p):
    """The band one leads or is in (c72)."""
    b = e.band_of(p)
    if not b:
        return []
    w = e.w
    lead = w.people.get(b["leader"])
    where = {"gathering": "gathering", "marching": f"marching on ({b['target'][0]},{b['target'][1]})" if b["target"] else "marching",
             "fighting": "fighting", "returning": "on the way home"}[b["state"]]
    return [f"{'Your band' if b['leader'] == p.id else lead.name + chr(39) + 's band, yours'}: {len(b['members']) + 1} strong, {where}."]


def held_text(e, p):
    """Captives (c76): one held sees by whom and the price; a captor sees whom they hold; kin see who is held."""
    w = e.w
    out = []
    if p.held:
        cap = w.people.get(p.held["by"])
        out.append(f"You are held captive by {cap.name if cap else 'strangers'} since {w.when(p.held['since'])}; they ask "
                   f"{I.describe(p.held['price'])} for you. You may only eat, rest, talk, deal, ransom yourself, or try to escape.")
    mine = [w.people[q] for q in w.holding.get(p.id, ()) if q in w.people]
    if mine:
        out.append("You hold captive: " + ", ".join(f"{q.name} ({I.describe(q.held['price'])} asked)" for q in mine if q.held) + ".")
    for cid, qs in w.holding.items():
        for q in qs:
            if str(q) in p.rel and q in w.people and w.people[q].held and cid in w.people:
                o = w.people[q]
                out.append(f"{o.name} is held captive by {w.people[cid].name}, who asks {I.describe(o.held['price'])}.")
    return out[:4]


def prices_text(p, w):
    """The prices one knows, newest first (c70): what a thing fetched where, in grain."""
    ps = sorted((v for k, v in p.known.items() if v[0] == "price"), key=lambda v: -v[2])[:4]
    if not ps:
        return []
    return ["Prices you know: " + "; ".join(f"{I.pretty(v[1])} {v[3]:g} grain at {v[4]} ({w.when(v[2]).split(' ')[0]} {v[2] // 12 + 1})"
                                             for v in ps) + "."]


def people_text(e, p):
    """A leader's or master's own people (grand world, Phase 1.4): where each is, what they do, how they stand
    toward one; up to ten, nearest first. They are one's to order."""
    w = e.w
    mine = e.followers(p)
    if len(mine) < 2:
        return []
    out = ["Your people (yours to order):"]
    for o in sorted((w.people[i] for i in mine), key=lambda o: dist(p.x, p.y, o.x, o.y))[:8]:
        d = dist(p.x, p.y, o.x, o.y)
        r = o.rel.get(str(p.id), {})
        kin = p.rel.get(str(o.id), {}).get("kin")
        goal = (o.intent or {}).get("goal") or ""
        doing = "doing your order" if (o.intent or {}).get("order") == p.id else \
            (o.act["do"] if o.act else "resting" if o.rest else "idle")
        stand = "loyal" if r.get("trust", 0) > 0.4 else "willing" if r.get("trust", 0) > 0 else "grudging"
        out.append(f"- {o.name} ({int(o.age(w.tick))}{', your ' + kin if kin else ''}{', serves you' if mine[o.id] == 'servant' else ''}), "
                   f"{'beside you' if d <= 1 else f'{d} steps {direction(p.x, p.y, o.x, o.y)}'}: {doing}"
                   f"{'; hungry' if o.satiety <= 6 else ''}; {stand}")
    return out


def build_prompt(e, p):
    w = e.w
    t = w.tick
    L = [RULES.format(eras=eras_text(w), w=w.w, h=w.h), "", steps_text(e, p), "", "=" * 20]
    L.append(f"You are {p.name}, {int(p.age(t))} years old ({stage(p, t)}). By nature you are {p.temperament}. "
             f"What you want most in life: {p.wants}." + (f" Who you have become: {p.self_view}" if p.self_view else ""))
    lines = list(dict.fromkeys(line for _, line in p.life))[-2:]      # each kept once: the same words are often kept again
    if lines:
        L.append("Kept for life: " + " | ".join(lines))
    L += people_lines(e, p)
    nxt = ["summer", "autumn", "winter", "spring"][["spring", "summer", "autumn", "winter"].index(w.season())]
    L.append(f"It is {w.when()} of {w.season()}, year {w.year() + 1}. {nxt.capitalize()} comes in {DPS - w.day() % DPS} days."
             + (" It is dark." if w.is_night() else ""))
    fullness = "starving" if p.satiety <= 0 else "very hungry" if p.satiety <= 4 else "hungry" if p.satiety <= 8 else "fed" if p.satiety < 17 else "full"
    L.append(f"Your body: health {int(p.health)}/{p.max_health(t)}, {fullness} ({int(p.satiety)}/20)"
             + ("; you are sick" if p.sick else "") + (f"; expecting a child in {max(0, p.pregnant['due'] - t)} hours" if p.pregnant else "") + ".")
    worn = I.worn(p.inv)
    L.append(f"You carry: {I.describe(p.inv)[:400]}{writings_text(w, p)} (load {p.load():.0f} of {p.capacity(t):.0f})."
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
            lord = w.groups.get(g.parent) if g.parent else None
            sworn = e.sworn_to(g) if g.leader == p.id else []
            L.append(f"You belong to {g.name} ({'members vote' if g.decide == 'vote' else 'led by ' + lead + (', its ' + g.title if g.title else '')}; {len(g.members)} members)."
                     + (f" Sworn to {lord.name} (led by {w.people[lord.leader].name}), paying {I.describe(g.tribute)} each autumn." if lord and lord.leader in w.people else "")
                     + (" Sworn to you: " + ", ".join(f"{h.name} ({I.describe(h.tribute) or 'no tribute'})" for h in sworn[:5]) + "." if sworn else "")
                     + "".join(f" At peace with {w.groups[int(k)].name} until day {u // TPD + 1}." for k, u in list(g.peace.items())[:4]
                               if u > t and int(k) in w.groups)
                     + f" Rules: \"{g.rules}\""
                     + ("".join(f" Law{' (written)' if l[2] else ''}: \"{l[1]}\"" for l in g.laws[-3:]) if g.laws else "")
                     + (f" Dues: {I.describe(g.dues)} a season." if g.dues else ""))
    L += people_text(e, p)
    L += realm_text(e, p)
    L += band_text(e, p)
    L += held_text(e, p)
    L += prices_text(p, w)
    L += news_text(e, p)
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
                     + (" (hand it over beside them)" if pr["by"] == p.id else "")
                     + (f"; written ({pr['deed']}), owed to whoever holds it" if pr.get("deed") else "") + ".")
    L.append("")
    L.append("Your crafts:")
    L += crafts_text(e, p) or ["- none yet"]
    now = makeable_now(e, p)
    if now:
        L.append("You could make now: " + "; ".join(now) + ".")
    extra = recipes_for_goal(e, p, (p.intent or {}).get("goal", "") + " " + p.memory)
    if extra:
        L.append("What the things you have in mind take: " + " | ".join(extra))
    L.append("")
    r = e.sight(p)
    # a leader's people are listed above, each with where they are: the map near them can be smaller
    mp, legend = small_map(e, p, min(r, 3 if len(e.followers(p)) >= 2 else 5))
    L.append(f"Around you (x grows east, y south; you are at ({p.x},{p.y}) on {TERRAIN[w.t(p.x, p.y)]['name']}):")
    L.append(mp)
    L.append("Key: " + legend)
    near = sorted((o for o in w.near(p.x, p.y, r) if o.id != p.id), key=lambda o: dist(p.x, p.y, o.x, o.y))
    if near:
        L.append("People you see:")
        # one's own people are told above: here only their number on the map (c78)
        mine = e.followers(p)
        told = {o.id for o in sorted((w.people[i] for i in mine), key=lambda o: dist(p.x, p.y, o.x, o.y))[:8]} if len(mine) >= 2 else set()
        L += [f"{i + 1}. {o.name}, of your people (above)" if o.id in told else person_line(e, p, o).replace("- ", f"{i + 1}. ", 1)
              for i, o in enumerate(near[:8])]
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
        elif b and w.empty(b):
            o = w.people.get(b.owner)
            things.append((dist(p.x, p.y, x, y), f"- {b.kind} at ({x},{y}), empty since {o.name if o else 'its maker'} died: "
                           f"claim it to make it yours" + (f"; inside: {I.describe(b.inv)[:60]}" if b.inv else "")))
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
            things.append((dist(p.x, p.y, x, y), f"- on the ground at ({x},{y}): {I.describe(pile)[:80]}"))
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
    if e.water_near(p):
        cell, bite = e.fish_here(p)
        if bite < 0.5:
            things.append((0, "- the water beside you is fished thin: few bite, and it fills again only over weeks"))
    if things:
        L.append("Things you see:")
        L += list(dict.fromkeys(t for _, t in sorted(things)))[:7]
    L += market_text(w, p, r)
    places = list({(pl[0], pl[1], pl[2]): pl for pl in w.places if dist(p.x, p.y, pl[0], pl[1]) <= r + 6}.values())
    if places:
        L.append("Named places near you: " + "; ".join(f"{pl[2]} at ({pl[0]},{pl[1]})" for pl in places[:6]) + ".")
    home = w.buildings.get(p.home)
    if home and any(w.groups.get(g) and w.groups[g].leader == p.id for g in p.groups) \
            and not any(dist(home.x, home.y, pl[0], pl[1]) <= 8 for pl in w.places):
        L.append("The place where your people live has no name yet (name_place, standing there).")
    mem = remembered(e, p, seen)
    if mem:
        L.append("Places you know of:")
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
    ev = compact_events(p.events[-20:], p.name)[-11:]
    if len(p.events) > 20:
        L.append(f"- ({len(p.events) - 20} earlier things left out)")
    by_when = []                                                   # one line a time of day (P1)
    for tk, text in ev:
        if by_when and by_when[-1][0] == w.when(tk):
            by_when[-1][1].append(text)
        else:
            by_when.append((w.when(tk), [text]))
    L += [f"- [{when}] " + " ".join(texts) for when, texts in by_when] or ["- nothing of note"]
    again = tried_again(e, p)
    if again:
        L.append("Tried more than once lately, and it could not be done: " + "; ".join(again) + ". Do something else instead.")
    if p.wake:
        L.append("Why you are deciding now: " + "; ".join(p.wake[:4]) + ".")
    if p.intent and p.intent.get("goal"):
        L.append(f"Your goal until now: {p.intent['goal']}" + (" (a routine)" if p.intent.get("routine") else "") + ".")
    doing_now = ([step_text(p.act)] if p.act else []) + [step_text(st) for st in (p.intent or {}).get("plan") or []]
    if doing_now:
        L.append("Your plan, still to do: " + "; ".join(doing_now[:8]) + ".")
    if p.memory:
        L.append(f"Your notes to yourself: {p.memory}")
    if p.beliefs:
        L.append("What you think of people: " + "; ".join(f"{k}: {v}" for k, v in list(p.beliefs.items())[-8:]))
    L.append("")
    L.append(ASK)
    return "\n".join(L)


# The answer's shape (Gemini-style types; the gateway turns it into plain JSON Schema for others).
GOODS = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {"item": {"type": "STRING"}, "qty": {"type": "INTEGER"}}}}
# what an order may set one's people to (society.Society.ORDERABLE; a test keeps the two alike)
ORDERABLE = ("gather", "hunt", "fish", "craft", "build", "mend", "plant", "put", "take", "go", "follow", "fuel")
STEP = {"type": "OBJECT", "properties": {
    "do": {"type": "STRING", "enum": VERBS},
    **{k: {"type": "STRING"} for k in ("item", "to", "animal", "kind", "craft", "text", "name", "group", "place", "from",
                                         "who", "choice", "act", "value", "rules", "decide", "promise", "share")},
    "task": {"type": "STRING", "enum": list(ORDERABLE)}, "keep": {"type": "STRING"}, "take": {"type": "BOOLEAN"},
    **{k: {"type": "INTEGER"} for k in ("n", "x", "y", "hours", "days", "offer", "vote", "due_days", "hire_days", "serve_days")},
    **{k: GOODS for k in ("give", "get", "promise_give", "promise_get")},
    "teach": {"type": "STRING"}, "learn": {"type": "STRING"}}, "required": ["do"]}
SCHEMA = {"type": "OBJECT", "properties": {
    "thought": {"type": "STRING"}, "goal": {"type": "STRING"},
    "plan": {"type": "ARRAY", "items": STEP}, "routine": {"type": "BOOLEAN"},
    "say": {"type": "STRING"}, "to": {"type": "STRING"}, "memory": {"type": "STRING"},
    "beliefs": {"type": "OBJECT", "properties": {}}, "life": {"type": "STRING"}, "idea": {"type": "STRING"}},
    "required": ["thought", "goal"]}
