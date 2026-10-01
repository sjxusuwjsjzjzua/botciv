"""How a bot person answers words spoken to it, and what it says unprompted.

The people with minds of their own talk a great deal, to bots as much as to each other ("Drir,
can we trade some flax for your grain?"). A bot reads such words for what they ask (food, a
trade, a lesson, a hand, a place in a group), answers in kind, and acts on it through the same
steps anyone has: give, propose, teach, invite, join, follow. Anything else gets a short answer
in its own voice, often about what it is doing. It is a reading of words, not understanding:
enough that speaking to a bot is not speaking to a wall."""
import re

from ..content import CRAFTS, ITEMS
from ..content import items as I

FOOD = re.compile(r"\b(hungry|starv\w*|food|eat|famished|spare)\b")
TRADE = re.compile(r"\b(trade|swap|exchange|barter|buy|sell|for your|in return|give you)\b")
LEARN = re.compile(r"\b(teach|learn|show me|how to|how do)\b")
OFFER_TEACH = re.compile(r"\b(i can teach|i'll teach|i will teach|let me teach|let me show|i can show)\b")
GROUP = re.compile(r"\b(join|fellowship|our people|our group|band together|household|clan|tribe)\b")
HELP = re.compile(r"\b(help|together|with me|come with|follow me)\b")
FARE = re.compile(r"\b(how do you fare|how are you|how goes it|are you well)\b")
GREET = re.compile(r"\b(hello|greetings|good day|well met|morning|evening)\b")

# item and craft names as people say them, longest first, so "wild grain" is not read as "grain"
NAMES = sorted({**{I.pretty(k): k for k in ITEMS}, **{k.replace("_", " "): k for k in ITEMS}}.items(), key=lambda kv: -len(kv[0]))
CRAFT_NAMES = sorted(((c.replace("_", " "), c) for c in CRAFTS), key=lambda kv: -len(kv[0]))
KEEP = {"wood": 4, "stone": 2, "fibre": 4}


def mentioned(low, table):
    found, used = [], low
    for name, k in table:
        if re.search(r"\b" + re.escape(name) + r"s?\b", used):
            found.append(k)
            used = re.sub(r"\b" + re.escape(name) + r"s?\b", " ", used)
    return found


def doing(goal):
    """What one is about, in a few words, from a bot's goal."""
    g = (goal or "").lower()
    for key, words in (("my craft: ", "making {}"), ("learn ", "learning {}"), ("teach ", "teaching {}")):
        if g.startswith(key):
            return words.format(g[len(key):].split(" from ")[0])
    table = [("home", "building a home"), ("store", "laying food by"), ("food", "looking for food"), ("field", "working my field"),
             ("sow", "sowing"), ("harvest", "bringing in the harvest"), ("beast", "seeing to my beasts"), ("pen", "building a pen"),
             ("hay", "cutting hay for my beasts"), ("winter", "getting ready for winter"), ("warm", "getting ready for winter"),
             ("trade", "trading"), ("buy", "trading"), ("pledge", "looking for a partner"), ("child", "thinking of a family")]
    for key, words in table:
        if key in g:
            return words
    return "about my work"


class Talk:
    def __init__(self, mind):
        self.m = mind
        self.e = mind.e
        self.w = mind.w
        self.last = {}              # (who, to whom) -> tick last answered

    def converse(self, p):
        """Answer the latest words spoken to one, if any came lately."""
        w = self.w
        heard = [h for h in self.e.heard.pop(p.id, []) if h[3] and w.tick - h[0] <= 6]
        if not heard:
            return None
        _, sid, text, _ = heard[-1]
        o = w.people.get(sid)
        if not o or not o.alive or max(abs(o.x - p.x), abs(o.y - p.y)) > 6:
            return None
        # no endless back and forth: once in half a day to the same person, and to another bot
        # only when asked something
        if w.tick - self.last.get((p.id, o.id), -99) < 6:
            return None
        low = text.lower()
        if o.mind == "bot" and "?" not in text and not (FOOD.search(low) or TRADE.search(low) or LEARN.search(low)):
            return None
        self.last[(p.id, o.id)] = w.tick
        return self.reply(p, o, text)

    def keep_on(self, p, say, o):
        """Words only: what one was doing goes on."""
        plan = [dict(s) for s in (p.intent or {}).get("plan") or []]
        return {"goal": (p.intent or {}).get("goal", ""), "plan": plan, "say": say, "to": o.name, "replace": False, "quiet": True,
                "routine": bool((p.intent or {}).get("routine"))}

    def reply(self, p, o, text):
        w, m = self.w, self.m
        low = text.lower()
        rel = p.rel.get(str(o.id), {})
        trust, kin = rel.get("trust", 0), bool(rel.get("kin"))
        items = mentioned(low, NAMES)
        crafts = mentioned(low, CRAFT_NAMES)
        for k in items:                                 # "teach me to make pots": the craft that makes them
            for c in CRAFTS:
                if c not in crafts and any(r["out"] == k for r in m.recipes_of(c)):
                    crafts.append(c)
        # a lesson asked for, or offered
        if crafts and (LEARN.search(low) or OFFER_TEACH.search(low)):
            c = crafts[0]
            if OFFER_TEACH.search(low) and o.skill(c) >= 0.3 and p.skill(c) < 0.3:
                return m.intent(f"learn {c} from {o.name}", [{"do": "propose", "to": o.name, "learn": c}],
                                f"I would like that. Teach me {c.replace('_', ' ')}?", o.name)
            if p.skill(c) >= 0.3 and o.skill(c) < 0.3 and (trust > -0.2 or kin):
                return m.intent(f"teach {c} to {o.name}", [{"do": "teach", "to": o.name, "craft": c}],
                                w.rng.choice([f"Gladly. Watch how I do the {c.replace('_', ' ')}.", "Come, I'll show you.",
                                              "Stay close and watch my hands."]), o.name)
            if p.skill(c) < 0.3:
                return self.keep_on(p, f"I don't know {c.replace('_', ' ')} well enough to teach it.", o)
        # food asked for
        if FOOD.search(low) and not TRADE.search(low):
            spare = m.food_worth(p.inv) - (12 if p.satiety < 12 else 6)
            food = next((k for k in sorted(p.inv, key=lambda k: -I.info(k).get("spoil", 0)) if I.info(k).get("food")), None)
            if food and spare >= 4 and w.rng.random() < 0.3 + p.traits["generosity"] + (0.3 if kin else 0) + trust * 0.5:
                n = max(1, min(p.inv[food], int(spare // max(1, I.info(food)["food"])), 4))
                return m.intent(f"feed {o.name}", [{"do": "give", "to": o.name, "item": food, "n": n}],
                                w.rng.choice(["Here, eat.", "Take this, you need it more than I do.", f"Have some {I.pretty(food)}."]), o.name)
            return self.keep_on(p, w.rng.choice(["I've barely enough myself.", "I have nothing to spare, I'm sorry.",
                                                 "Try the berry bushes by the water."]), o)
        # a trade
        if TRADE.search(low) or (items and " for " in low):
            mine = [k for k in items if p.inv.get(k, 0) > KEEP.get(k, 1)]
            theirs = [k for k in items if o.inv.get(k) and k not in mine]
            if mine:
                k = mine[0]
                n = max(1, min(3, p.inv[k] - KEEP.get(k, 1)))
                want = theirs[0] if theirs else next((x for x in sorted(o.inv, key=lambda x: -I.info(x).get("worth", 0))
                                                      if not p.inv.get(x) and o.inv[x] > 0), None)
                if want:
                    q = max(1, min(o.inv[want], round(n * I.info(k)["worth"] / max(0.5, I.info(want)["worth"]))))
                    return m.intent(f"trade with {o.name}", [{"do": "propose", "to": o.name, "give": {k: n}, "get": {want: q}}],
                                    f"I can let you have {n} {I.pretty(k)} for {q} {I.pretty(want)}.", o.name)
            if items:
                return self.keep_on(p, f"I have no {I.pretty(items[0])} to spare.", o)
        # a place in a group
        if GROUP.search(low):
            theirs = next((g for g in w.groups.values() if g.dissolved is None and p.id in g.invited and o.id in g.members), None)
            if theirs and not p.groups and (trust >= 0 or kin):
                return m.intent(f"join {theirs.name}", [{"do": "join", "group": theirs.name}], "I'll join you.", o.name)
            mine = next((w.groups[g] for g in p.groups if w.groups.get(g) and w.groups[g].leader == p.id), None)
            if mine and o.id not in mine.members and trust > -0.2:
                return m.intent(f"invite {o.name}", [{"do": "invite", "to": o.name, "group": mine.name}],
                                f"You'd be welcome among {mine.name}.", o.name)
        # a hand asked for
        if HELP.search(low) and (trust >= 0.1 or kin) and w.rng.random() < 0.3 + 0.5 * p.traits["generosity"]:
            return m.intent(f"help {o.name}", [{"do": "follow", "to": o.name, "hours": 4}], "Alright, I'll come with you.", o.name)
        # anything else: a few words in one's own voice
        if FARE.search(low):
            say = w.rng.choice(["Hungry, truth be told.", "Hungry. Food is hard to come by."]) if p.satiety < 8 else \
                w.rng.choice([f"Well enough. I'm {doing((p.intent or {}).get('goal'))}.", "Well, thank you. And you?",
                              "Tired, but well."]) if p.health >= 6 else w.rng.choice(["Poorly.", "Not well, I'm afraid."])
        elif "?" in text:
            say = f"I'm {doing((p.intent or {}).get('goal'))}." if w.rng.random() < 0.6 else w.rng.choice(
                ["I couldn't say.", "Ask me again later.", "Perhaps."])
        elif GREET.search(low):
            say = w.rng.choice(["Good day to you.", "Well met.", f"Hello, {o.name}."])
        else:
            say = w.rng.choice(["Hm.", "So it is.", "I'll think on it.", "Aye.", f"I'm {doing((p.intent or {}).get('goal'))}."])
        return self.keep_on(p, say, o)

    def remark(self, p, intent):
        """Now and then, tell someone nearby what one is about, or ask for what one needs."""
        w = self.w
        if w.is_night() or intent.get("say") or w.rng.random() > 0.1 + 0.25 * p.traits["sociability"]:
            return intent
        near = [o for o in w.near(p.x, p.y, 4) if o.id != p.id and o.adult(w.tick)]
        if not near:
            return intent
        o = max(near, key=lambda o: p.rel.get(str(o.id), {}).get("trust", 0) + w.rng.random() * 0.3)
        what = doing(intent.get("goal"))
        intent["say"] = w.rng.choice([f"Back to {what}.", f"{o.name}, I'm {what} today.", f"Busy {what}, {o.name}.",
                                      f"How do you fare, {o.name}? I'm {what}."])
        intent["to"] = o.name
        intent["quiet"] = "?" not in intent["say"]      # a remark in passing; a question asks for an answer
        return intent
