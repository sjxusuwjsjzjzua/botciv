"""What an agent perceives, as text for a language model and as a dict for bots.

The text never mentions a simulation, a game, agents, ticks or turns. An hour
is one step of the world; a day is 12 hours, the last 3 of them night.
"""
from collections import Counter

from . import items as I
from .engine import BUILD, VERBS, PLAN_VERBS, TECHNIQUES, STORE_CAP, out_of_world
from .world import SEASONS, TERRAIN_NAME, key, unkey, dist, direction

RULES_VERSION = "w31"

WORLD_TEXT = """How the world works, as far as you know it:
- Everyone must eat. Hunger grows through the day; about 4 worth of food a day keeps a person fed. Food worth: berries 1, grain 2, fish 3, meat 4. Someone who goes without food weakens and dies within days. When you grow hungry you eat from what you carry without stopping to think, what spoils soonest first; to keep food for later or for someone else, put it in a store or give it away.
- A person can carry a load of 20 (a basket adds 15). Wood weighs 2, stone 2.5, a hide 1, fibre and bone 0.4, food a fifth to a half. Someone carrying all they can picks up nothing more, food included, until they drop, put away or give something; but a hungry person eats on the spot the food they cannot carry, whether picked, caught, hunted or taken.
- Carried food spoils: berries and fish within a few days, meat a little slower, grain hardly at all. Food spoils slower inside a store. Fibre, hides and wood left on the ground weather away within days; bone and stone last.
- Berry bushes regrow slowly through spring, summer and autumn, and not at all in winter. A bush picked bare over and over dies.
- Deer herds wander the grass. A hunter alone almost never brings one down. Two hunters at the same herd usually do within a few hours, three almost always. The 8 meat is split among the hunters who were there.
- Fish can be caught beside water: slowly by hand, far better with the right tool.
- Rich soil can be farmed: build a farm there, plant seeds (sometimes found while gathering fibre or berries in summer and autumn), and after about 4 days of growing (it does not grow in winter) it gives 6 grain for every seed. Grain kept back can be sown again as seed. Anyone can gather from a ripe farm, but its owner can open it or close it like a store, and taking from a farm not open to you is remembered by the owner and whoever sees it.
- Wood comes from forest, stone from beside rock, fibre from grass.
- Things can be made by working two things together. Most pairs make nothing (a failed try costs only time); a pair is learned by trying it or being taught.
- Winter nights are cold. Without a shelter, a fire beside you, or warm clothing, the cold hurts.
- Wolves live in the deep forest. They go for people who are alone, most boldly at night and when winter makes them hungry. They keep away from fire and from people standing together, and they can be fought.
- Blows hurt. A person who is struck while awake hits back a little. Several people striking the same person hit harder. Wounds heal slowly when fed, faster resting, fastest resting in a shelter.
- Taking something from a person without asking sometimes works, less often with their own people beside them. They or others may notice, and those who see it remember who did it. Several people standing together (a group, partners, kin, or anyone who has followed that person) can take from someone openly by force; that seldom fails, unless the person has their own people beside them.
- A store, shelter or wall can be closed to everyone except those its owner chooses. Nothing else stops anyone from doing anything.
- A deal can put one person in another's service for some days, for agreed pay. While it lasts they count as each other's people when force is used, the servant may put things into the master's stores, and the master hears daily what the servant did. Ending it early is remembered.
- What someone has built can be handed to another, and anyone can name who should inherit what they have built. Partners can part.
- People get better at what they do often, and others come to know who is good at what.
- People live about three to five years. Two grown people who are both well fed can choose to have a child together: it is born two days later, can help from its first days, is grown within 20 days, and inherits what its parents built. Two people can pledge themselves to each other as partners for life.
- Fish, meat and berries smoked or dried over a fire keep most of a year. Not everyone knows how; it can be taught.
- Each day has 12 hours; the last 3 are night, when you see only a little way.
- This land is the whole world. It is {w} steps across from west to east and {h} from north to south, and there is nothing past its edges. You see only part of it at a time; what lies elsewhere you know only from walking there, remembering, or being told."""

VERB_HELP = {
    "continue": "continue: keep doing what you are doing and follow your plan.",
    "go": "go: walk. Give x,y; or dir (north, southeast, ...) with qty steps; or target (a person you see).",
    "gather": "gather: item is berries, wood, stone, fibre or grain; qty is how many you want (leave it out to gather until the source is bare or you are full). You walk to the nearest one you can see: a berry bush, forest, rock, grass, or a ripe farm.",
    "fish": "fish: walk to the nearest water you can see and fish for qty hours.",
    "hunt": "hunt: walk to the nearest herd you can see and stand ready for up to qty hours (6); it resolves when enough hunters are ready at that herd.",
    "eat": "eat: eat item (qty pieces, or until full), yours or on the ground beside you.",
    "rest": "rest: rest for qty hours. You heal faster but are easier to rob or hurt.",
    "wait": "wait: do nothing for qty hours.",
    "craft": "craft: work item and item2 together (2 hours). If nothing comes of it, you keep both.",
    "build": "build: build item at your tile or x,y next to you. " + "; ".join(
        f"{k} needs {', '.join(f'{n} {m}' for m, n in v['cost'].items())}" for k, v in BUILD.items())
        + ". A monument takes name and text (words carved into it that everyone who passes can read). Others can help finish a building by building the same thing at the same place.",
    "plant": "plant: sow qty seeds, or grain kept back from a harvest (item grain), up to 8, in a farm next to you.",
    "drop": "drop: put item (qty) on the ground. Wood dropped on a fire feeds it; a snare dropped on grass or forest is set.",
    "put": "put: put item (qty) into a store next to you that is open to you.",
    "take": "take: target \"ground\" picks up item from the ground next to you, target \"store\" from a store open to you (no item: food); target a person's name tries to take item (up to 3, or \"food\") from them without asking (you walk to them first); if your own people stand beside them too, you take openly, by force.",
    "give": "give: give item (qty) to target (you walk to them first if you see them). item can also be a building you own (store, shelter, wall, farm, fire, monument; x,y to say which), which becomes theirs.",
    "attack": "attack: strike target (a person within 2 steps), or target \"wolves\" when a pack is next to you. Or give x,y to break a structure next to you.",
    "follow": "follow: follow target for qty hours.",
    "teach": "teach: teach target (you walk to them first) how to make item.",
    "mark": "mark: leave a sign with text where you stand. Anyone passing can read it.",
    "tell_story": "tell_story: tell a story (text) to everyone who can hear you; they will remember it and can tell it on. Or retell a story you know by its number as id.",
    "name_place": "name_place: give the place where you stand a name (name). Those who see it will call it so.",
    "bury": "bury: bury the remains on or next to you, with words for the grave (text). The grave stays.",
    "do": "do: do anything else you can describe in text (a ceremony, a burial, a dance, a gesture toward target, a vow). It takes qty hours (1 to 6) and changes nothing by itself, but those who see it will know.",
    "set_access": "set_access: choose who may use your store, shelter, wall or farm at x,y. text is \"me\", \"anyone\", a group name, or names separated by commas.",
    "found_group": "found_group: start a group called name with text as its rules. choice \"members vote\" makes decisions by vote; otherwise you lead it.",
    "invite": "invite: invite target into group.",
    "join": "join: join group (you must have been invited).",
    "leave": "leave: leave group; with no group named, leave the service you are in.",
    "expel": "expel: remove target from group (leader only; in voting groups, call a vote), or send target away from your service.",
    "call_vote": "call_vote: ask your group a question (text). choice \"expel\" or \"leader\" with a target, or \"rules\" with the new rules as text, is carried out if it passes in a voting group.",
    "vote": "vote: answer vote number id with choice \"yes\" or \"no\".",
    "propose": "propose: offer target (within 5 steps) a deal. give = things you hand over now, get = things they hand over now, promise_give / promise_get = things to be handed over within due_day days, text = any other terms. Lists are [{item, qty}]. hire_days = days they will work for you; serve_days = days you will work for them. Handing over happens when they accept, if you stand next to each other. Promises are remembered by both of you, and whether they are kept.",
    "accept": "accept: accept offer number id.",
    "refuse": "refuse: refuse offer number id.",
    "ask_child": "ask_child: ask target (you walk to them first), your partner or anyone, to have a child with you. name = the child's name, text = what you would teach the child.",
    "smoke": "smoke: beside a burning fire (you walk to one you see), smoke fish or meat, or dry berries (item, qty), so they keep most of a year. Someone who knows how does it well; others can be taught, or may work it out by trying.",
    "pledge": "pledge: ask target (you walk to them first) to be your partner for life: partners share their stores and shelters, and each inherits the other's when one dies.",
    "part": "part: end your partnership with your partner.",
    "bequeath": "bequeath: name target to inherit everything you have built when you die (before your partner or children).",
}

SYM = {"grass": ".", "forest": "T", "rock": "^", "water": "~", "rich soil": ","}


def recent_ledger_summary(w, a):
    """Per-person counts of what really happened between a and others."""
    kinds = {}
    last = {}
    for t, oid, kind, _ in a.ledger:
        if oid is None:
            continue
        kinds.setdefault(oid, Counter())[kind] += 1
        last[oid] = t
    label = {"gift_in": "gave you things", "gift_out": "you gave them things", "hunt": "hunted together",
             "attacked": "attacked you", "attacked_them": "you attacked them", "robbed": "stole or tried to steal from you",
             "stole": "you stole from them", "kept": "kept promises to you", "broke": "broke promises to you",
             "kept_mine": "you kept promises to them", "broke_mine": "you broke promises to them",
             "deal": "deals made", "taught_me": "taught you", "taught": "you taught them", "help": "helped build",
             "store_out": "took from your store", "store_in": "put into your store", "smash": "damaged your things",
             "kin": "kin", "child": "child together", "saw_steal": "you saw them steal", "saw_attack": "you saw them attack someone",
             "forced": "took from you by force", "forced_them": "you took from them by force",
             "saw_force": "you saw them take by force", "took_crop": "took from your farm",
             "took_crop_them": "you took from their farm", "saw_smash": "you saw them break a building",
             "killed_kin": "killed your kin", "gave_building": "you gave them a building",
             "got_building": "gave you a building", "heir": "you named them your heir",
             "heir_of": "named you their heir", "parted": "parted", "pledge": "pledged to you",
             "heard_wrong": "you were told of wrongs they did", "heard_good": "you were told good of them",
             "hired": "went into your service", "hired_by": "you went into their service",
             "served_me": "served you as agreed", "served": "you served them as agreed",
             "left_service": "left your service early", "left_service_mine": "you left their service early",
             "dismissed": "sent you away from their service early", "dismissed_them": "you sent them away early"}
    rows = []
    for oid in sorted(kinds, key=lambda o: -last[o])[:10]:
        o = w.agents.get(oid)
        if not o:
            continue
        c = kinds[oid]
        parts = [("kin" if k == "kin" else f"{label.get(k, k)} {n}x") for k, n in c.items() if k in label]
        dead = "" if o.alive else " (dead)"
        rows.append(f"- {o.name}{dead}: " + ", ".join(parts))
    return rows


def visible(e, a):
    w = e.w
    r = w.sight(a)
    people, things = [], []
    for o in w.living():
        if o.id != a.id and dist(a.x, a.y, o.x, o.y) <= r:
            people.append(o)
    for k, b in w.bushes.items():
        x, y = unkey(k)
        if dist(a.x, a.y, x, y) <= r:
            things.append(("bush", x, y, b))
    for h in w.herds:
        if h["size"] > 0 and dist(a.x, a.y, h["x"], h["y"]) <= r:
            things.append(("herd", h["x"], h["y"], h))
    for s in w.structures.values():
        if dist(a.x, a.y, s.x, s.y) <= r:
            things.append(("structure", s.x, s.y, s))
    for k, p in w.piles.items():
        x, y = unkey(k)
        if dist(a.x, a.y, x, y) <= r:
            things.append(("pile", x, y, p))
    for k, sg in w.signs.items():
        x, y = unkey(k)
        if dist(a.x, a.y, x, y) <= r:
            things.append(("sign", x, y, sg))
    for k, c in w.corpses.items():
        x, y = unkey(k)
        if dist(a.x, a.y, x, y) <= r:
            things.append(("corpse", x, y, c))
    for p in w.wolves:
        if dist(a.x, a.y, p["x"], p["y"]) <= r:
            things.append(("wolves", p["x"], p["y"], p))
    for k, owner in w.snares.items():
        x, y = unkey(k)
        if dist(a.x, a.y, x, y) <= min(r, 2):
            things.append(("snare", x, y, owner))
    people.sort(key=lambda o: dist(a.x, a.y, o.x, o.y))
    things.sort(key=lambda t: dist(a.x, a.y, t[1], t[2]))
    return people, things


LEGEND = [(".", "grass"), ("T", "forest"), ("^", "rock"), ("~", "water"), (",", "rich soil"), ("*", "berry bush"),
          ("o", "bare bush"), ("D", "deer herd"), ("S", "store"), ("H", "shelter"), ("#", "wall"), ("F", "farm"),
          ("f", "fire"), ("&", "monument"), ("=", "grave"), ("?", "unfinished building"), ("!", "sign"),
          ("%", "things on the ground"), ("+", "remains"), ("s", "snare"), ("W", "wolves")]


def ascii_map(e, a, people, things):
    w = e.w
    r = w.sight(a)
    grid = {}
    for y in range(a.y - r, a.y + r + 1):
        for x in range(a.x - r, a.x + r + 1):
            if w.in_bounds(x, y):
                grid[(x, y)] = SYM[TERRAIN_NAME[w.t(x, y)]]
    marks = {"bush": "*", "herd": "D", "pile": "%", "sign": "!", "corpse": "+", "snare": "s", "wolves": "W"}
    smark = {"store": "S", "shelter": "H", "wall": "#", "farm": "F", "fire": "f", "monument": "&", "grave": "="}
    for kind, x, y, obj in reversed(things):
        if kind == "structure":
            grid[(x, y)] = smark[obj.kind] if obj.done else "?"
        elif kind == "bush":
            grid[(x, y)] = "*" if obj["b"] > 0 else "o"
        else:
            grid[(x, y)] = marks[kind]
    letters = {}
    for o in people:
        ch = o.name[0].lower()
        grid[(o.x, o.y)] = ch
        letters.setdefault(ch, []).append(o.name)
    grid[(a.x, a.y)] = "@"
    xs = list(range(a.x - r, a.x + r + 1))
    head = ("     " + " ".join(f"{x % 100:>2}"[-2:] if w.in_bounds(x, 0) else "  " for x in xs)).rstrip()
    lines = [head]
    for y in range(a.y - r, a.y + r + 1):
        if not (0 <= y < w.h):
            continue
        row = " ".join(f"{grid.get((x, y), ' '):>2}" for x in xs)
        lines.append(f"{y:>3}  {row}".rstrip())
    shown = set(grid.values())
    legend = "; ".join(["@ you"] + (["letters = people (first letter of name)"] if letters else [])
                       + [f"{k} {v}" for k, v in LEGEND if k in shown])
    return "\n".join(lines), legend


def describe_person(e, a, o):
    w = e.w
    d = dist(a.x, a.y, o.x, o.y)
    where = "next to you" if d <= 1 else f"{d} steps {direction(a.x, a.y, o.x, o.y)}"
    bits = [f"{o.name} at ({o.x},{o.y}), {where}"]
    age_y = o.age / w.ticks_per_year()
    bits.append("a child" if o.age < e.cfg["agent"]["adult_ticks"] else ("old" if o.age > 0.8 * o.lifespan else "grown"))
    if a.partner == o.id:
        bits.append("your partner")
    hw = e.health_word(o)
    if hw != "healthy":
        bits.append(f"looks {hw}")
    if e.hunger_word(o) in ("very hungry", "starving"):
        bits.append("looks gaunt")
    carried = [k for k in ("spear", "axe", "net", "basket", "cloak", "necklace", "drum") if o.inventory.get(k)]
    if carried:
        bits.append("carries " + ", ".join(carried))
    load = o.carrying()
    if load > 10:
        bits.append("heavily laden")
    if o.activity:
        v = o.activity["verb"]
        doing = {"gather": f"gathering {o.activity.get('item', '')}", "hunt": "hunting", "fish": "fishing",
                 "rest": "resting", "build": "building", "craft": "making something", "go": "walking",
                 "follow": "following someone", "attack": "fighting", "steal": "reaching toward someone"}.get(v)
        if doing:
            bits.append(doing)
    best = max(((v, k) for k, v in o.skills.items()), default=(0, None))
    if best[0] >= 2:
        bits.append(f"known as a {e.skill_level(best[0])} {e.SKILL_ROLE[best[1]]}")
    leads = [w.groups[g].name for g in o.groups if g in w.groups and w.groups[g].leader == o.id
             and w.groups[g].decide != "vote" and len(w.groups[g].members) > 1]
    gs = [w.groups[g].name for g in o.groups if g in w.groups and w.groups[g].name not in leads]
    svc = e.serving(o)
    if svc and svc["master"] == a.id:
        bits.append("in your service")
    elif svc and w.agents.get(svc["master"]):
        bits.append(f"in {w.agents[svc['master']].name}'s service")
    mine = e.serving(a)
    if mine and mine["master"] == o.id:
        bits.append("you are in their service")
    n = len(e.servants(o))
    if n:
        bits.append(f"has {n} in their service")
    if leads:
        bits.append("leads " + ", ".join(leads))
    if gs:
        bits.append("of " + ", ".join(gs))
    known = {k for _, oid, k, _ in a.ledger if oid == o.id}
    wrongs = [t for k, t in (("killed_kin", "killed your kin"), ("robbed", "has stolen from you"), ("attacked", "has attacked you"),
                             ("took_crop", "has taken from your farm"), ("saw_smash", "you have seen them break a building"),
                             ("forced", "has taken from you by force"), ("saw_steal", "you have seen them steal"),
                             ("saw_attack", "you have seen them attack someone")) if k in known]
    if wrongs:
        bits.append(wrongs[0])
    else:
        told = [t for _, oid, k, t in a.ledger if oid == o.id and k == "heard_wrong"]
        if told:
            bits.append(told[-1])
    if o.id in a.parents:
        bits.append("your parent")
    elif o.id in a.children:
        bits.append("your child")
    elif o.name not in a.beliefs and str(o.id) not in a.seen and not any(l[1] == o.id for l in a.ledger):
        bits.append("a stranger")
    elif any(l[1] == o.id and l[2] == "kin" for l in a.ledger):
        bits.append("your kin")
    return "- " + "; ".join(bits)


def describe_thing(e, a, t):
    w = e.w
    kind, x, y, obj = t
    d = dist(a.x, a.y, x, y)
    where = "here" if d == 0 else ("next to you" if d == 1 else f"{d} steps {direction(a.x, a.y, x, y)}")
    at = f"({x},{y}) {where}"
    if kind == "bush":
        return f"- berry bush at {at}: {obj['b']} berries" if obj["b"] else f"- bare berry bush at {at}"
    if kind == "herd":
        return f"- deer herd of {obj['size']} at {at}"
    if kind == "wolves":
        return f"- a pack of {obj['size']} wolves at {at}"
    if kind == "pile":
        return f"- on the ground at {at}: {I.describe(obj)}"
    if kind == "sign":
        out = []
        for aid, text, t0 in obj:
            au = w.agents.get(aid)
            out.append(f"- sign at {at}: \"{text}\" (left by {au.name if au else 'someone'}, {w.when(t0)})")
        return "\n".join(out)
    if kind == "corpse":
        return f"- the remains of {obj[0]} at {at}"
    if kind == "snare":
        o = w.agents.get(obj)
        return f"- a snare at {at}" + (f" (set by {o.name})" if o and o.id != a.id else " (yours)" if obj == a.id else "")
    s = obj
    o = w.agents.get(s.owner)
    if s.kind == "grave":
        return f"- the grave of {s.name} at {at}" + (f": \"{s.text}\"" if s.text else "") + (f" (buried by {o.name})" if o else "")
    if s.kind == "monument" and s.done:
        by = "you" if s.owner == a.id else o.name if o else "someone long gone"
        return f"- a monument{(' called ' + s.name) if s.name else ''} at {at}, raised by {by}" + (f", carved with: \"{s.text}\"" if s.text else "")
    owner = "yours" if s.owner == a.id else f"{o.name}'s" if o else "abandoned"
    if not s.done:
        return f"- unfinished {s.kind} ({owner}) at {at}"
    extra = ""
    if s.kind in ("store", "shelter", "wall"):
        extra = f", open to {e.access_text(s)}"
        if s.kind == "store" and (w.may_use(a, s) or d <= 1):
            extra += (f"; holds {I.describe(s.inventory)}" + (" (full)" if I.weight(s.inventory) > STORE_CAP - 1 else "")
                      if w.may_use(a, s) else "")
    if s.kind == "farm":
        if s.inventory.get("grain"):
            extra = f", ripe: {s.inventory['grain']} grain"
        elif s.planted is not None:
            left = max(0, e.cfg["resources"]["farm_grow_ticks"] - s.progress)
            extra = f", growing, ripe in about {left // w.tpd() + 1} days"
        else:
            extra = ", unplanted"
    if s.kind == "fire":
        extra = f", burning ({s.fuel} hours of fuel)"
    if s.hp < 10 and s.kind != "farm":
        extra += ", damaged"
    return f"- {s.kind} ({owner}) at {at}{extra}"


def available_verbs(e, a):
    w = e.w
    vs = []
    for v in VERBS:
        if v == "continue" and not (a.activity or a.plan):
            continue
        if v in ("accept", "refuse") and not any(p["to"] == a.id for p in w.proposals.values()):
            continue
        if v in ("invite", "call_vote") and not a.groups:
            continue
        if v == "leave" and not (a.groups or e.serving(a)):
            continue
        if v == "expel" and not (a.groups or e.servants(a)):
            continue
        if v == "vote" and not any(not x["done"] and w.groups.get(x["group"]) and a.id in w.groups[x["group"]].members
                                   for x in w.votes.values()):
            continue
        if v == "join" and not any(a.id in g.invited or g.join == "open" for g in w.groups.values() if g.dissolved is None):
            continue
        if v == "teach" and not a.recipes:
            continue
        if v == "set_access" and not any(s.owner == a.id and s.kind in ("store", "shelter", "wall", "farm") for s in w.structures.values()):
            continue
        if v == "part" and a.partner is None:
            continue
        if v == "bequeath" and not any(s.owner == a.id for s in w.structures.values()):
            continue
        if v == "ask_child" and a.age < e.cfg["agent"]["adult_ticks"]:
            continue
        if v == "plant" and not (a.inventory.get("seeds") or a.inventory.get("grain")):
            continue
        if v == "bury" and not any(key(a.x + dx, a.y + dy) in w.corpses for dx in (-1, 0, 1) for dy in (-1, 0, 1)):
            continue
        vs.append(v)
    return vs


def activity_text(e, a):
    if not a.activity:
        return "nothing"
    act = a.activity
    v = act["verb"]
    w = e.w
    if v == "go":
        if "follow" in act:
            return f"walking toward {w.agents[act['follow']].name}"
        return f"walking to ({act['x']},{act['y']})"
    if v == "gather":
        return f"gathering {act['item']} ({act.get('got', 0)} so far)"
    if v == "hunt":
        return "waiting at the herd, ready to hunt"
    if v == "follow":
        return f"following {w.agents[act['follow']].name}"
    if v == "build":
        s = w.structures.get(act["sid"])
        return f"building a {s.kind}" if s else "building"
    return {"rest": "resting", "wait": "waiting", "fish": "fishing", "craft": "making something"}.get(v, v)


def build_prompt(e, a):
    w = e.w
    c = e.cfg
    tpy = w.ticks_per_year()
    people, things = visible(e, a)
    L = []
    L.append(WORLD_TEXT.format(w=w.w, h=w.h))
    L.append("")
    L.append("Things you can do (one each time you decide; speaking and eating are free and can go alongside):")
    verbs = available_verbs(e, a)
    for v in verbs:
        L.append("- " + VERB_HELP[v])
    L.append("")
    L.append("=" * 20)
    L.append(f"You are {a.name}. By nature you are {a.temperament}." + (f" What you want most in life: {a.wants}." if a.wants else "")
             + (f" Who you have become, in your own words: {a.self_view}" if a.self_view and not out_of_world(a.self_view) else ""))
    age = a.age / tpy
    stage = "a child" if a.age < c["agent"]["adult_ticks"] else ("growing old" if a.age > 0.8 * a.lifespan else "grown")
    L.append(f"You are {age:.1f} years old ({stage}). Strength {a.strength}/3, speed {a.speed}/3.")
    practised = sorted(((v, k) for k, v in a.skills.items() if e.skill_level(v)), reverse=True)
    if practised:
        L.append("You are practised at: " + ", ".join(f"{e.SKILL_WORD[k]} ({e.skill_level(v)})" for v, k in practised) + ".")
    days_left = c["world"]["days_per_season"] - (w.day() % c["world"]["days_per_season"])
    nxt = ["summer", "autumn", "winter", "spring"][["spring", "summer", "autumn", "winter"].index(w.season())]
    L.append(f"It is {w.when()} of {w.season()}, year {w.year() + 1}. {nxt.capitalize()} comes in {days_left} days.")
    if w.is_night():
        L.append("It is dark.")
    L.append(f"Your body: {e.health_word(a)} (health {a.health}/{c['agent']['max_health']}), "
             f"{e.hunger_word(a)} (fullness {a.satiety}/{c['agent']['max_satiety']}).")
    if a.pregnant:
        L.append(f"You are expecting a child, due in about {max(0, a.pregnant['due'] - w.tick)} hours.")
    free = a.capacity(c) - a.carrying()
    full = ": full, you can pick up nothing more" if free < 0.2 else ": nearly full" if free < 2 else ""
    L.append(f"You carry: {I.describe(a.inventory)} (load {a.carrying():.1f} of {a.capacity(c):.0f}{full}).")
    worn = [f"{k} ({I.ITEMS[k]['uses'] - a.wear.get(k, 0)} uses left)" for k in a.inventory if I.ITEMS[k].get("uses") and a.wear.get(k)]
    if worn:
        L.append("Wear: " + ", ".join(worn) + ".")
    held = [k for k in a.inventory if k in I.EFFECTS]
    if held:
        L.append("What your things do: " + "; ".join(f"{k}: {I.EFFECTS[k]}" for k in held) + ".")
    if a.recipes:
        L.append("You know how to make: " + "; ".join(
            f"{w.recipes[k]} from {k.replace('+', ' and ')} ({I.EFFECTS.get(w.recipes[k], '')})" for k in a.recipes))
    else:
        L.append("You know how to make nothing yet.")
    for t in a.know:
        L.append(f"You know how to {TECHNIQUES[t]}.")
    if a.partner is not None and w.agents.get(a.partner):
        p = w.agents[a.partner]
        L.append(f"Your partner is {p.name}." if p.alive else f"Your partner {p.name} is dead.")
    svc = e.serving(a)
    if svc:
        left = max(1, -(-(svc["end"] - w.tick) // w.tpd()))
        L.append(f"You are in {w.agents[svc['master']].name}'s service for {left} more day{'s' if left > 1 else ''}"
                 + (f" (terms: \"{svc['terms']}\")" if svc.get("terms") else "") + ".")
    mine = e.servants(a)
    if mine:
        L.append("In your service: " + ", ".join(
            f"{w.agents[x['servant']].name} ({max(1, -(-(x['end'] - w.tick) // w.tpd()))} more days)" for x in mine) + ".")
    for gid in a.groups:
        g = w.groups[gid]
        lead = "you" if g.leader == a.id else w.agents[g.leader].name
        mem = ", ".join(w.agents[m].name for m in g.members)
        how = "members vote" if g.decide == "vote" else f"led by {lead}"
        L.append(f"You belong to {g.name} ({how}; members: {mem}). Its rules: \"{g.rules}\"")
    for gid, g in w.groups.items():
        if a.id in g.invited and g.dissolved is None:
            L.append(f"You are invited to join {g.name}. Its rules: \"{g.rules}\"")
    if a.teachings and a.age < 2 * c["agent"]["adult_ticks"]:
        for who, text in a.teachings:
            L.append(f"{who} taught you when you were small: \"{text}\"")
    L.append("")
    r = w.sight(a)
    L.append(f"Around you (you can see {r} steps; x grows to the east, y grows to the south; you stand at ({a.x},{a.y}) on {TERRAIN_NAME[w.t(a.x, a.y)]}):")
    m, legend = ascii_map(e, a, people, things)
    L.append(m)
    L.append(f"Key: {legend}")
    if people:
        L.append("People you see:")
        L.extend(describe_person(e, a, o) for o in people)
    else:
        L.append("You see no one.")
    if things:
        bare = [t for t in things if t[0] == "bush" and t[3]["b"] <= 0]
        rest = [t for t in things if not (t[0] == "bush" and t[3]["b"] <= 0)]
        L.append("Things you see:")
        L.extend(describe_thing(e, a, t) for t in rest[:24])
        if bare:
            L.append("- bare berry bushes at " + ", ".join(f"({t[1]},{t[2]})" for t in bare[:12]))
    places = [p for p in w.places if dist(a.x, a.y, p[0], p[1]) <= r + 3]
    if places:
        L.append("Named places near you: " + "; ".join(
            f"{p[2]} at ({p[0]},{p[1]})" + (" (here)" if dist(a.x, a.y, p[0], p[1]) <= 1 else "") for p in places) + ".")
    if e.near_water(a):
        L.append("You are beside water.")
    vis = {key(t[1], t[2]) for t in things}
    far = [(dist(a.x, a.y, *unkey(k)), k, v) for k, v in a.known.items() if k not in vis]
    if far:
        far.sort()
        L.append("Places you remember that are out of sight now:")
        for d, k, (kind, label, t0) in far[:10]:
            x, y = unkey(k)
            ago = (w.tick - t0) // w.tpd()
            when_seen = "today" if ago == 0 else "yesterday" if ago == 1 else f"{ago} days ago"
            L.append(f"- {label} at ({x},{y}), {d} steps {direction(a.x, a.y, x, y)} (seen {when_seen})")
    h = e.herd_near(a, 1)
    if h:
        hunters = [o.name for o in w.living() if o.activity and o.activity["verb"] == "hunt" and o.activity.get("herd") == h["id"] and o.id != a.id]
        if hunters:
            L.append("Ready to hunt at this herd already: " + ", ".join(hunters) + ".")
    L.append("")
    ev = a.events
    L.append(f"What happened since you last decided ({w.when(a.last_decided) if a.last_decided >= 0 else 'the start'} until now):")
    if not ev:
        L.append("- nothing of note")
    else:
        n_full = c["mind"]["events_full"]
        if len(ev) > n_full:
            L.append(f"- ({len(ev) - n_full} earlier things you only half remember)")
        for t, text in ev[-n_full:]:
            L.append(f"- [{w.when(t)}] {text}")
    offers = [p for p in w.proposals.values() if p["to"] == a.id]
    if offers:
        L.append("Offers waiting for your answer:")
        for p in offers:
            L.append(f"- #{p['id']} from {w.agents[p['from']].name}: {e.deal_text(p, a)}")
    mine = [p for p in w.promises if not p["done"] and a.id in (p["from"], p["to"])]
    if mine:
        L.append("Promises outstanding:")
        for p in mine:
            left = max(0, p["due"] - w.tick) // w.tpd()
            if p["from"] == a.id:
                L.append(f"- you owe {w.agents[p['to']].name} {p['qty']} {p['item']} (handed {p['paid']}), due in {left} days")
            else:
                L.append(f"- {w.agents[p['from']].name} owes you {p['qty']} {p['item']} (handed {p['paid']}), due in {left} days")
    votes = [v for v in w.votes.values() if not v["done"] and w.groups.get(v["group"]) and a.id in w.groups[v["group"]].members]
    for v in votes:
        mine_v = "yes" if a.id in v["yes"] else "no" if a.id in v["no"] else "not yet"
        L.append(f"Open vote #{v['id']} in {w.groups[v['group']].name}: \"{v['q']}\" (your vote: {mine_v})")
    L.append("")
    L.append("Your own notes from before (you wrote these):")
    L.append(a.memory if a.memory and not out_of_world(a.memory) else "(none yet)")
    if a.life:
        L.append("What you will never forget (you chose to keep these):")
        dps = c["world"]["days_per_season"]
        L.extend(f"- [{SEASONS[t // w.tpd() // dps % 4]} of year {t // w.tpd() // (4 * dps) + 1}] {text}" for t, text in a.life if not out_of_world(text))
    if a.ideas:
        L.append("Ideas you have had for things no one here knows how to do yet:")
        L.extend(f"- \"{text}\"" for _, text in a.ideas[-3:])
    if a.lore:
        L.append("Stories you know (retell by number):")
        for i, (origin, text, first, teller) in enumerate(a.lore, 1):
            src = "your own" if origin == a.name else f"first told by {origin}" + ("" if teller == origin else f", heard from {teller}")
            L.append(f"#{i} ({src}): \"{text[:300]}\"")
    known = [(n, b) for n, b in a.beliefs.items() if not out_of_world(b)]
    if known:
        L.append("What you think of people:")
        vis = {o.name for o in people}
        known.sort(key=lambda nb: (nb[0] not in vis, nb[0]))
        for n, b in known[:14]:
            L.append(f"- {n}: {b}")
    rel = recent_ledger_summary(w, a)
    if rel:
        L.append("What has really passed between you and others:")
        L.extend(rel)
    led = a.ledger[-c["mind"]["ledger_recent"]:]
    if led:
        L.append("Recent facts you remember clearly:")
        for t, oid, kind, text in led:
            L.append(f"- [{w.when(t)}] {text}")
    L.append("")
    L.append(f"Right now you are {activity_text(e, a)}." + (
        " Then your plan: " + ", ".join(step_text(s) for s in a.plan) + "." if a.plan else "") + (
        " You are repeating: " + ", ".join(step_text(s) for s in a.routine) + "." if a.routine else ""))
    L.append("You are deciding now because: " + "; ".join(a.wake or ["it is time to decide"]) + ".")
    L.append("")
    known = any(oid is not None and (k in e.TELLABLE or k in e.TELLABLE_GOOD) for _, oid, k, _ in a.ledger)
    of = ("; of = a name, to pass on what you yourself have seen or suffered of them; hearers remember you told them"
          if known else "")
    L.append("Decide what you do next. Reply with: thought (private, brief); speech (optional: text, to = a name or empty, whisper true only for someone next to you"
             + of + "); "
             "eat (optional: item and qty to eat right now, alongside whatever else you do); "
             "action (one verb with its fields); plan (optional: up to 8 later steps like actions, using only: "
             + ", ".join(PLAN_VERBS) + "); repeat (optional: true starts action and plan over each time they finish, until something happens to you or a day passes); "
             "memory (rewrite your notes: what matters, what you intend, what you owe and are owed; at most 600 characters); "
             "beliefs (only people whose opinion changed: name and a short belief). "
             "Without a plan you are asked again as soon as your action is done; with one, when it ends or something happens to you. "
             "Most people give a plan of 3 to 8 steps, and repeat for steady work such as gathering, fishing or hunting. "
             "Optional and rare: idea (something you truly want to do, make or have that no one here knows how to do, or that the things you can do do not allow: what, and what for; if two things might make it, try crafting them); "
             "remember (one line to keep for the rest of your life, only when something changes you); "
             "self (who you have become, one sentence, only when that changes).")
    return "\n".join(L)


def step_text(s):
    v = s.get("verb", "?")
    bits = [v]
    for k in ("target", "item", "item2", "qty", "dir"):
        if s.get(k) not in (None, ""):
            bits.append(str(s[k]))
    if s.get("x") is not None and s.get("y") is not None:
        bits.append(f"({s['x']},{s['y']})")
    return " ".join(bits)


ITEMS_SCHEMA = {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
    "item": {"type": "STRING"}, "qty": {"type": "INTEGER"}}, "required": ["item", "qty"]}}


def action_schema(verbs):
    return {"type": "OBJECT", "properties": {
        "verb": {"type": "STRING", "enum": verbs},
        "target": {"type": "STRING"}, "item": {"type": "STRING"}, "item2": {"type": "STRING"},
        "qty": {"type": "INTEGER"}, "x": {"type": "INTEGER"}, "y": {"type": "INTEGER"},
        "dir": {"type": "STRING"}, "text": {"type": "STRING"}, "name": {"type": "STRING"},
        "group": {"type": "STRING"}, "id": {"type": "INTEGER"}, "choice": {"type": "STRING"},
        "give": ITEMS_SCHEMA, "get": ITEMS_SCHEMA, "promise_give": ITEMS_SCHEMA, "promise_get": ITEMS_SCHEMA,
        "due_day": {"type": "INTEGER"}, "hire_days": {"type": "INTEGER"}, "serve_days": {"type": "INTEGER"},
    }, "required": ["verb"]}


def response_schema(verbs):
    return {"type": "OBJECT", "properties": {
        "thought": {"type": "STRING"},
        "speech": {"type": "OBJECT", "properties": {
            "text": {"type": "STRING"}, "to": {"type": "STRING"}, "whisper": {"type": "BOOLEAN"}, "of": {"type": "STRING"}}},
        "eat": {"type": "OBJECT", "properties": {"item": {"type": "STRING"}, "qty": {"type": "INTEGER"}}},
        "action": action_schema(verbs),
        "plan": {"type": "ARRAY", "items": action_schema(PLAN_VERBS)},
        "repeat": {"type": "BOOLEAN"},
        "memory": {"type": "STRING"},
        "beliefs": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
            "name": {"type": "STRING"}, "belief": {"type": "STRING"}}, "required": ["name", "belief"]}},
        "idea": {"type": "STRING"},
        "remember": {"type": "STRING"},
        "self": {"type": "STRING"},
    }, "required": ["thought", "action", "memory"],
        "propertyOrdering": ["thought", "speech", "eat", "action", "plan", "repeat", "memory", "beliefs", "idea", "remember", "self"]}
