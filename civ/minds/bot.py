"""Bot people: minds without a language model, meant to live like the people who have one.

A bot has traits (industry, sociability, boldness, generosity, curiosity, ambition, 0..1) and a
vocation it drifts toward by aptitude. Each time its plan runs out, it weighs what matters now
(hunger, winter, a home, its craft, its kin, its standing), picks a goal, and lays out the steps
with the planner. It answers offers by what it gains and how far it trusts the one asking,
remembers who helped and wronged it, teaches its children, and trades what it makes. It speaks
only a little. Everything it does goes through the same executor as everyone else."""
import math
import re

from ..content import BUILDINGS, CRAFTS, DEPOSITS, RECIPES, TAME, WILD
from ..content import items as I
from ..content.crafts import recipes_for, recipes_making
from ..acts import mend_stuff
from ..names import group_rules
from ..plan import Planner
from .talk import Talk
from ..world import dist, key, DPS, TPD, TPY

# the metal crafts: a long road (ore, charcoal, a furnace, firings that fail) that a learner keeps to (c63)
METAL = {"smelting", "alloying", "casting", "ironworking", "smithing"}
WARM = ["fur_coat", "wool_cloak", "cloak", "wool_tunic", "tunic", "fur_hat", "hat", "boots", "shoes"]
VOCATIONS = {
    # vocation: (the craft it lives by, what it makes to trade, what it wants in return)
    "potter": ("pottery", ["jar", "pot", "brick"], None),
    "weaver": ("weaving", ["linen", "woolcloth"], None),
    "tailor": ("tailoring", ["wool_tunic", "linen_tunic", "boots", "leather_bag"], None),
    "tanner": ("tanning", ["leather"], None),
    "knapper": ("knapping", ["flint_knife", "flint_axe", "flint_spear", "flint_sickle"], None),
    "carpenter": ("carpentry", ["plank", "shield"], None),
    "brewer": ("brewing", ["beer"], None),
    "baker": ("baking", ["bread", "flour"], None),
    "smelter": ("smelting", ["copper", "tin"], None),
    "bronzesmith": ("casting", ["bronze_axe", "bronze_knife", "bronze_sickle", "bronze_spear", "copper_bracelet"], None),
    "alloyer": ("alloying", ["bronze"], None),
    "charcoal_burner": ("charcoal_burning", ["charcoal"], None),
    "ironworker": ("ironworking", ["iron"], None),
    "smith": ("smithing", ["iron_axe", "iron_sickle", "iron_knife", "iron_spear", "iron_plough"], None),
    "mason": ("lime_burning", ["lime", "mortar"], None),
    "glassmaker": ("glassmaking", ["glass", "glass_beads"], None),
    "hideworker": ("hideworking", ["fur_coat", "cloak", "tunic", "shoes", "fur_hat"], None),
    "cook": ("preserving", ["smoked_meat", "smoked_fish", "dried_berries", "salted_meat"], None),
    "herbalist": ("herbalism", ["poultice"], None),
    "wheelwright": ("wheelwrighting", ["cart", "plough", "potters_wheel"], None),
    "boatwright": ("boatbuilding", ["canoe", "sailboat"], None),
    "bowyer": ("bowyery", ["bow"], None),
}
LINES = {
    "offer": ["Here, for your trouble.", "A fair trade, I think.", "Take it; I'll need the other.", "What do you say?"],
    "thanks": ["My thanks.", "That is good of you.", "I won't forget it."],
    "greet": ["Good day.", "Well met.", "The land is kind today.", "Cold coming soon."],
    "angry": ["You'll regret that.", "I remember what you did.", "Keep away from me."],
    "teach": ["Watch how I do it.", "Like this, see?", "You'll have it soon enough."],
}


# what a household keeps by it of the land's plain things (carried and stored); more is gathered only for a use
STOCK = {"wood": 20, "fibre": 12, "stone": 8, "reeds": 6, "herbs": 3}
# what a bot leader gives its people as law (the people's own laws are theirs to word)
LAWS = ["Share food with the hungry among us.", "Take nothing from a neighbour's store unasked.",
        "Every household brings grain to the common store.", "A promise broken is paid back twice.",
        "No one strikes one of us without answer."]
# how many crafts each one opens (pottery: charcoal, casting, masonry, writing, lime...)
UNLOCKS = {}
for _c, _v in CRAFTS.items():
    for _pre in _v["pre"]:
        UNLOCKS[_pre] = UNLOCKS.get(_pre, 0) + 1


def food_worth(inv):
    return sum(I.info(k).get("food", 0) * n for k, n in inv.items())


class BotMind:
    def __init__(self, engine):
        self.e = engine
        self.w = engine.w
        self.planner = Planner(engine)
        self.talk = Talk(self)

    @staticmethod
    def food_worth(inv):
        return food_worth(inv)

    @staticmethod
    def recipes_of(craft):
        return recipes_for(craft)

    def decide(self, people):
        out = {}
        for p in people:
            if p.mind != "bot":
                continue
            try:
                out[p.id] = self.one(p)
            except Exception as ex:           # a bot never stops the world
                out[p.id] = {"goal": "rest", "plan": [{"do": "wait", "hours": 2}], "err": str(ex)[:80]}
        return out

    # ================= choosing =================
    def one(self, p):
        w = self.w
        p.wake = []
        band = self.e.band_of(p)
        if band and band["leader"] == p.id and band["state"] in ("marching", "fighting") and p.satiety > 4:
            return self.intent("lead the raid", [{"do": "wait", "hours": 1}])      # a leader holds with the band
        # standing in for a person with a mind of their own while they think (c74): only what is obvious and their
        # daily work; offers, leading, raiding, trading, pledging and children are theirs to choose
        own = p.mind == "llm"
        if p.held:
            return self.captive(p, own)
        for choose in ((self.danger, self.guard, self.hunger, self.frailty, self.night, self.keep_promise, self.unload, self.serve) if own else
                       (self.answer, self.danger, self.guard, self.talk.converse, self.hunger, self.frailty, self.night, self.keep_promise,
                        self.unload, self.serve, self.captor, self.ransom_goal, self.rite)):
            got = choose(p)
            if got:
                return got
        if not p.adult(w.tick):
            return self.child(p)
        if not p.vocation:
            p.vocation = self.pick_vocation(p)
        late = self.w.season() == "autumn" or (self.w.season() == "summer" and self.w.day() % 10 >= 5)
        goals = [(self.home_goal, 1.0), (self.winter_goal, 1.0), (self.store_food_goal, 2.2 if late else 0.8),
                 (self.farm_goal, 2.5 if self.ripe_field(p) or self.field_to_sow(p) else 0.8), (self.herd_goal, 1.6 if self.keeps_beasts(p) else 0.6), (self.social_goal, 0.3 + 0.5 * p.traits["sociability"]),
                 (self.craft_goal, 0.4 + 0.6 * p.traits["industry"]), (self.advance_goal, (0.2 + 0.8 * p.traits["curiosity"]) * (2 if p.traits.get("learning") in METAL else 1)),
                 (self.lead_goal, 0.1 + p.traits["ambition"] * 0.6), (self.trade_goal, 0.5),
                 (self.legacy_goal, 0.1 + 0.3 * p.traits["ambition"]), (self.tally_goal, 0.4), (self.deed_goal, 0.6),
                 (self.upkeep_goal, 1.2 + p.traits["industry"]), (self.letters_goal, 0.15 + 0.5 * p.traits["curiosity"]),
                 (self.school_goal, 0.2 + 0.4 * p.traits["sociability"]), (self.want_goal, 0.3),
                 (self.merchant_goal, 3.0 if p.vocation == "trader" else 0.0),
                 (self.raid_goal, self.raid_weight(p))]
        if own:
            goals = [g for g in goals if g[0] not in (self.lead_goal, self.raid_goal, self.merchant_goal, self.social_goal,
                                                      self.legacy_goal, self.school_goal, self.letters_goal, self.trade_goal,
                                                      self.want_goal, self.deed_goal, self.tally_goal)]
        # a weighted draw without replacement: each goal comes first in proportion to its weight, so
        # the rarer concerns of a life (beasts, leading, trade) get their turn and are not always
        # crowded out by the ones that always have something to do
        order = sorted((g for g in goals if g[1] > 0), key=lambda g: math.log(1 - w.rng.random()) / g[1], reverse=True)
        for goal, _ in order:
            got = goal(p)
            if got:
                return self.talk.remark(p, got)
        return self.forage(p)

    def intent(self, goal, plan, say=None, to=None, most=8):
        out = {"goal": goal, "plan": [s for s in plan if s][:most]}
        if say:
            out["say"], out["to"] = say, to
        return out

    # ================= what cannot wait =================
    def answer(self, p):
        """Offers made to this bot: weigh and answer each; and invitations into a group."""
        w = self.w
        offers = [x for x in w.offers.values() if x["to"] == p.id]
        if not offers:
            if p.adult(w.tick) and len(p.groups) < 1:
                for g in w.groups.values():
                    if g.dissolved is None and p.id in g.invited and p.id not in g.members:
                        r = p.rel.get(str(g.leader), {})
                        if r.get("kin") or r.get("trust", 0) + 0.3 * p.traits["sociability"] >= 0.15:
                            return self.intent(f"join {g.name}", [{"do": "join", "group": g.name}],
                                               w.rng.choice(["I'll stand with you.", "Count me in.", None]),
                                               w.people[g.leader].name if g.leader in w.people else None)
            return None
        plan = []
        for x in offers[:3]:
            o = w.people.get(x["from"])
            ok = o is not None and self.worth_it(p, o, x)
            plan.append({"do": "accept" if ok else "refuse", "offer": x["id"]})
        say = self.line("thanks") if plan and plan[0]["do"] == "accept" and w.rng.random() < 0.3 else None
        return self.intent("answer offers", plan, say)

    def worth_it(self, p, o, x):
        w = self.w
        trust = p.rel.get(str(o.id), {}).get("trust", 0)
        kin = bool(p.rel.get(str(o.id), {}).get("kin"))
        if x["kind"] == "pledge":
            return p.partner is None and not kin and trust >= 0.0 and w.rng.random() < 0.4 + 0.5 * p.traits["sociability"]
        if x["kind"] == "child":
            return (p.partner == o.id or trust > 0.6) and p.satiety >= 12 and not p.pregnant and self.has_home(p)
        if x["kind"] in ("fealty", "homage"):
            vas, lord = w.groups.get(x.get("vassal")), w.groups.get(x.get("lord"))
            if not vas or not lord:
                return False
            if x["kind"] == "fealty":           # a group would swear to mine: tribute and men, for protection
                return trust >= -0.3
            # homage asked of my group: given to the strong, or in need, by those who do not hate them; and to one
            # whose people have lately raided mine, by those not too proud to bend (submission, c75)
            strong = len(lord.members) + sum(len(h.members) for h in self.e.sworn_to(lord)) >= 2 * len(vas.members)
            need = p.satiety <= 8 or self.w.year_at(p.x, p.y) in ("lean", "hard")
            if strong and self.raided_by(p, o):
                return w.rng.random() < 0.8 - 0.5 * p.traits["boldness"]
            return trust >= -0.2 and (strong or need) and w.rng.random() < 0.6 + 0.3 * (1 - p.traits["boldness"])
        if x["kind"] == "tenancy":
            # a field to work for a share: taken by those with none of their own who can farm; a field of mine
            # asked for: let when it lies idle, for a third or more (c83)
            f = w.buildings.get(x.get("field"))
            if not f or self.e.can_try(p, "farming") and x.get("tenant") == p.id:
                return False
            if x.get("tenant") == p.id:
                return not self.fields(p) and self.has_seed(p) and x.get("share", 1) <= 0.5 and trust >= -0.3
            return not f.crop and not f.inv and x.get("share", 0) >= 0.3 and trust >= 0
        if x["kind"] == "peace":
            # peace is welcome, save to a bold and hungry people facing a weak one, or to those who hate the asker
            g1, g2 = (w.groups.get(i) for i in x.get("groups", (None, None)))
            if not g1 or not g2:
                return False
            size = lambda h: len(h.members) + sum(len(k.members) for k in self.e.sworn_to(h))
            need = p.satiety <= 8 or w.year_at(p.x, p.y) in ("lean", "hard")
            if p.traits["boldness"] > 0.7 and need and size(g1) < 0.5 * size(g2) and not x["give"]:
                return False
            return trust >= -0.6 or bool(x["give"]) or self.raided_by(p, o)
        value = lambda g: sum(I.info(k)["worth"] * n * (1.5 if I.info(k).get("food") and p.satiety < 10 else 1) for k, n in g.items())
        gain = value(x["give"]) + 0.6 * value(x["promise_give"]) * (0.5 + trust)
        cost = value(x["get"]) + value(x["promise_get"])
        if x["hire_days"]:
            cost += 4 * x["hire_days"] * (1.2 - p.traits["industry"] * 0.5)
        if x["serve_days"]:
            gain += 4 * x["serve_days"]
        if x.get("teach") and p.skill(x["teach"]) < 0.3:
            gain += 10 + 20 * p.traits["curiosity"]
        if x.get("learn"):
            cost += 3                                   # a lesson's hours
        if any(p.inv.get(k, 0) < n for k, n in x["get"].items()):
            return False
        # the starving asking for a little food, from one who has plenty: a kindness
        if o.satiety <= 4 and food_worth(p.inv) >= 10 and all(I.info(k).get("food") for k in x["get"]) and \
                value(x["get"]) <= 6 and w.rng.random() < 0.3 + p.traits["generosity"]:
            return True
        return gain + 3 * trust + (2 if kin else 0) + 2 * p.traits["generosity"] >= cost

    def danger(self, p):
        w = self.w
        foes = [o for o in w.near(p.x, p.y, 3) if p.rel.get(str(o.id), {}).get("trust", 0) < -0.5 and o.act and o.act.get("do") == "attack"
                and o.act.get("to") == p.id]
        if not foes:
            return None
        o = foes[0]
        if p.traits["boldness"] > 0.5 and p.health > 4:
            return self.intent(f"fight back against {o.name}", [{"do": "attack", "to": o.name}], self.line("angry"), o.name)
        home = w.buildings.get(p.home)
        if home:
            return self.intent("flee home", [{"do": "go", "x": home.x, "y": home.y}, {"do": "rest", "hours": 4}])
        return None

    def guard(self, p):
        """Someone taking what is one's own, close by: warn them off; if they keep at it, the bold strike."""
        w = self.w
        if not p.adult(w.tick) or p.health <= 4:
            return None
        for e in reversed(p.ledger[-8:]):
            if w.tick - e[0] > 3 or e[2] not in ("robbed", "took_crop"):
                continue
            o = w.people.get(e[1])
            if not o or not o.alive or dist(p.x, p.y, o.x, o.y) > 6:
                continue
            warned = [x for x in p.ledger[-30:] if x[1] == o.id and x[2] == "warned" and w.tick - x[0] <= 3 * TPD]
            if not warned:
                p.ledger.append([w.tick, o.id, "warned", f"you warned {o.name} off"])
                return self.intent(f"stop {o.name} taking what is mine", [{"do": "go", "to": o.name}],
                                   f"{o.name}, that is mine. Leave it, or answer for it.", o.name)
            if not any(e[0] > x[0] for x in warned):
                return None                     # warned already; only a fresh theft after the warning is answered
            struck = any(x[1] == o.id and x[2] == "attacked_them" and w.tick - x[0] <= 2 * TPD for x in p.ledger[-30:])
            if struck:
                return None                     # one blow answers a theft; no more than that
            if p.traits["boldness"] > 0.4 and p.health >= o.health and o.satiety > 4 and w.rng.random() < 0.5:
                return self.intent(f"make {o.name} pay for stealing", [{"do": "attack", "to": o.name}], self.line("angry"), o.name)
            return None
        return None

    def hunger(self, p):
        if p.satiety >= 10 or food_worth(p.inv) >= 4:
            return None
        plan = self.food_plan(p)
        if not plan:
            return None
        # hungry beside someone with food to spare: ask
        w = self.w
        fed = [o for o in w.near(p.x, p.y, 3) if o.id != p.id and food_worth(o.inv) >= 10]
        if fed and p.satiety <= 6 and w.rng.random() < 0.3 + 0.4 * p.traits["sociability"]:
            o = fed[0]
            return self.intent("find food", plan, w.rng.choice([f"{o.name}, could you spare a little food?",
                                                                 "I'm so hungry. Has anyone food to spare?"]), o.name)
        return self.intent("find food", plan)

    def food_plan(self, p):
        w, e, pl = self.w, self.e, self.planner
        store = next((b for b in w.buildings_within(p.x, p.y, 20) if b.done
                      and "store" in BUILDINGS[b.kind]["roles"] and food_worth(b.inv) >= 3
                      and (b.owner in (p.id, p.partner) or w.may_use(p, b))), None)
        if store:
            return [{"do": "take", "x": store.x, "y": store.y, "n": 6}, {"do": "eat"}]
        opts = []
        for item in ("berries", "nuts", "honey", "grain"):
            spot = e.find(p, item)
            if spot:
                # a source others are already working is worth less: count them against what it holds
                d = w.deposits.get(key(*spot))
                left = d["left"] if d else 20
                crowd = len([o for o in w.near(spot[0], spot[1], 3) if o.act and o.act.get("do") == "gather"])
                opts.append((dist(p.x, p.y, *spot) + 4 * crowd - min(6, left / 3), [{"do": "gather", "item": item, "n": 8}, {"do": "eat"}]))
        pen = next((b for b in w.owned(p.id) if b.inv.get("milk")), None)
        if pen:
            opts.append((dist(p.x, p.y, pen.x, pen.y), [{"do": "take", "item": "milk", "x": pen.x, "y": pen.y}, {"do": "eat"}]))
        herds = e.herds_of(p)
        if herds:
            hunters = len([o for o in w.near(herds[0]["x"], herds[0]["y"], 2) if o.act and o.act.get("do") == "hunt"])
            opts.append((dist(p.x, p.y, herds[0]["x"], herds[0]["y"]) - 4 * hunters + 3, [{"do": "hunt", "animal": herds[0]["kind"]}, {"do": "eat"}]))
        if e.water_near(p) or any(w.t(x, y) == "~" for x, y in w.beside(p.x, p.y, 6)):
            fishers = len([o for o in w.near(p.x, p.y, 6) if o.act and o.act.get("do") == "fish"])
            opts.append((4 + fishers - 3 * (I.best_tool(p.inv, "fish")[1] > 1), [{"do": "fish", "hours": 5}, {"do": "eat"}]))
        # the starving reap a stranger's ripe field, knowing it will be seen and remembered
        if p.satiety <= 3:
            fields = [b for b in w.buildings_within(p.x, p.y, 10) if b.done and "farm" in BUILDINGS[b.kind]["roles"] and b.inv.get("grain")
                      and not w.may_use(p, b) and dist(p.x, p.y, b.x, b.y) <= 10]
            if fields:
                b = min(fields, key=lambda b: dist(p.x, p.y, b.x, b.y))
                opts.append((dist(p.x, p.y, b.x, b.y) + 5 - 4 * (1 - p.traits["generosity"]),
                             [{"do": "gather", "item": "grain", "n": 6, "x": b.x, "y": b.y}, {"do": "eat"}]))
        # the desperate, bold and none too scrupulous may help themselves from a stranger's store
        if p.satiety <= 3 and p.traits["boldness"] > 0.6 and p.traits["generosity"] < 0.4:
            for b in w.buildings_within(p.x, p.y, 8):
                if (b.done and b.owner not in (p.id, p.partner) and "store" in BUILDINGS[b.kind]["roles"] and food_worth(b.inv) >= 6
                        and dist(p.x, p.y, b.x, b.y) <= 8 and not p.rel.get(str(b.owner), {}).get("kin")):
                    watchers = len(w.near(b.x, b.y, 4))
                    opts.append((dist(p.x, p.y, b.x, b.y) + 3 * watchers + 2, [{"do": "take", "x": b.x, "y": b.y, "n": 4}, {"do": "eat"}]))
                    break
        if opts:
            return min(opts, key=lambda o: o[0])[1]
        # nothing known: look further afield, away from where one stands
        a = w.rng.random() * 6.283
        x = max(0, min(w.w - 1, p.x + int(10 * math.cos(a))))
        y = max(0, min(w.h - 1, p.y + int(10 * math.sin(a))))
        return [{"do": "go", "x": x, "y": y}, {"do": "gather", "item": "berries", "n": 6}] if e.find(p, "berries") is None else \
            [{"do": "gather", "item": "berries", "n": 6}]

    def unload(self, p):
        """Hands too full: put the heaviest things that are not food or tools into one's store."""
        w = self.w
        if p.load() < 0.8 * p.capacity(w.tick):
            return None
        store = self.store_of(p)
        if not store or dist(p.x, p.y, store.x, store.y) > 15:
            return None
        # what the plan in hand, or the craft one is learning, still needs stays in hand
        needed = {s.get("item") for s in (p.intent or {}).get("plan") or []}
        for r in recipes_for(p.traits.get("learning") or ""):
            needed |= set(r["ins"])
        # what is put away: things neither food nor worn, and of tools, every one past the first (bots who made
        # canoes to trade carried three or four, loads full)
        spare = {k: p.inv[k] - (1 if I.info(k).get("tool") else 0) for k in p.inv
                 if not I.info(k).get("food") and not I.info(k).get("wear") and k not in needed}
        heavy = sorted((k for k, n in spare.items() if n > 0), key=lambda k: -I.info(k).get("w", 0.5) * spare[k])[:3]
        if not heavy:
            return None
        return self.intent("put things away", [{"do": "put", "item": k, "n": spare[k], "x": store.x, "y": store.y} for k in heavy])

    def keep_promise(self, p):
        """A promise coming due: get the goods and bring them (it is kept when one stands beside them
        holding what was promised)."""
        w = self.w
        due = sorted((pr for pr in w.promises if not pr["done"] and pr["by"] == p.id and pr["due"] - w.tick <= TPD * 3),
                     key=lambda pr: pr["due"])
        for pr in due:
            o = w.people.get(pr["to"])
            if not o or not o.alive:
                continue
            steps = []
            for k, n in pr["goods"].items():
                sub = self.planner.get(p, k, n + (4 if I.info(k).get("food") and p.inv.get(k, 0) < n else 0))   # some is eaten on the way
                if sub is None:
                    break
                steps += sub
            else:
                if len(steps) <= 4:
                    return self.intent(f"keep my promise to {o.name}", steps + [{"do": "give", "to": o.name, "item": k, "n": n}
                                                                               for k, n in pr["goods"].items()])
        return None

    def frailty(self, p):
        if p.health >= 5 and not p.sick:
            return None
        home = self.w.buildings.get(p.home)
        plan = [{"do": "go", "x": home.x, "y": home.y}] if home and dist(p.x, p.y, home.x, home.y) > 1 else []
        if p.inv.get("poultice") and p.sick:
            plan.append({"do": "eat", "item": "poultice"})
        plan.append({"do": "rest", "hours": 8})
        return self.intent("rest and mend", plan)

    def night(self, p):
        if not self.w.is_night():
            return None
        home = self.w.buildings.get(p.home)
        if home and self.w.may_use(p, home) and dist(p.x, p.y, home.x, home.y) > 0:
            return self.intent("home for the night", [{"do": "go", "x": home.x, "y": home.y}, {"do": "sleep", "hours": 3}])
        return self.intent("sleep", [{"do": "sleep", "hours": 3}])

    # ================= children =================
    def child(self, p):
        w = self.w
        parents = [w.people.get(i) for i in p.parents]
        parents = [x for x in parents if x and x.alive]
        age = p.age(w.tick)
        if age < 5:
            # beside a parent (wolves take whoever is alone at night or in winter: 13 of world2's 39 wolf
            # deaths were children)
            close = 1 if w.is_night() or w.season() == "winter" else 2
            if parents and dist(p.x, p.y, parents[0].x, parents[0].y) > close:
                return self.intent("stay with family", [{"do": "follow", "to": parents[0].name, "hours": 6}])
            return self.intent("play", [{"do": "wait", "hours": 4}])
        # wolves take those alone at night and in winter: keep near a grown-up then, a parent or anyone
        if w.is_night() or w.season() == "winter":
            near = parents or sorted((o for o in w.near(p.x, p.y, 15) if o.adult(w.tick) and o.alive),
                                     key=lambda o: (-p.rel.get(str(o.id), {}).get("trust", 0), dist(p.x, p.y, o.x, o.y)))
            if near and dist(p.x, p.y, near[0].x, near[0].y) > 1:
                return self.intent("keep close", [{"do": "follow", "to": near[0].name, "hours": 4}])
        # a school near by: sit there by day to learn from whoever teaches (c61)
        if 6 <= age < 14 and w.season() != "winter" and w.rng.random() < 0.3:
            school = self.e.building_near(p, lambda b: "school" in BUILDINGS[b.kind]["roles"], r=12, usable=False)
            if school:
                return self.intent("go to school", [{"do": "go", "x": school.x, "y": school.y}, {"do": "wait", "hours": 4}])
        # arms full: hand the most of what is carried to a parent, else the family's store, else set it down
        if self.e.room(p, "wood") < 2:
            heavy = max((k for k in p.inv if not I.info(k).get("food")), key=lambda k: p.inv[k] * I.info(k).get("w", 1), default=None)
            if heavy:
                store = next((b for b in w.owned(parents[0].id) if "store" in BUILDINGS[b.kind]["roles"] and b.done), None) \
                    if parents else None
                if parents:
                    step = {"do": "give", "to": parents[0].name, "item": heavy, "n": p.inv[heavy]}
                elif store:
                    step = {"do": "put", "item": heavy, "x": store.x, "y": store.y}
                else:
                    step = {"do": "drop", "item": heavy, "n": p.inv[heavy]}
                return self.intent("unburden", [step])
        store = next((b for b in w.owned(parents[0].id) if "store" in BUILDINGS[b.kind]["roles"] and b.done), None) if parents else None
        # help with what the family runs short of; with nothing wanted, play
        can = [k for k in self.lacking(p, store) if k in ("berries", "fibre", "wood", "reeds") and self.e.find(p, k, far=False)]
        plan = [{"do": "gather", "item": can[0], "n": 4}] if can else [{"do": "wait", "hours": 3}]
        if store and can and can[0] != "berries":
            plan.append({"do": "put", "item": can[0], "x": store.x, "y": store.y})
        if age >= 9 and w.rng.random() < 0.3:
            known = sorted(((s, c) for c, s in p.skills.items() if c in CRAFTS), reverse=True)
            if known:
                steps = self.planner.practise(p, known[0][1])
                if steps and len(steps) <= 4:
                    plan = steps
        return self.intent("help the family", plan)

    # ================= a life's goals =================
    def has_home(self, p):
        h = self.w.buildings.get(p.home)
        return bool(h and h.done and h.owner in (p.id, p.partner))

    def home_goal(self, p):
        w = self.w
        if self.has_home(p):
            home = w.buildings[p.home]
            better = "house" if home.kind == "shelter" and not self.e.can_try(p, "carpentry") and p.traits["industry"] > 0.4 else None
            if better and w.rng.random() < 0.3:
                steps = self.planner.build(p, better)
                if steps and len(steps) <= 6:
                    return self.intent("a better home", steps)
            return None
        # a partner's or parent's home will do until one has one's own
        for pid in [p.partner] + p.parents:
            o = w.people.get(pid) if pid else None
            h = w.buildings.get(o.home) if o and o.home else None
            # a partner's own home is one's own; a parent's will do only while young
            if h and ((p.partner == o.id and h.owner in (p.id, o.id)) or (p.age(w.tick) < 20 and pid in p.parents)):
                p.home = o.home
                return None
        # an empty shelter near, whose owner died with no heir: claim it before building one
        if self.empty_near(p, "shelter", 15):
            return self.intent("a home", [{"do": "claim", "kind": self.empty_near(p, "shelter", 15).kind}])
        steps = self.planner.build(p, "shelter")
        return self.intent("a home", steps) if steps else None

    def empty_near(self, p, role, r):
        """The nearest empty building (owner dead, no heir) with this role, within r steps."""
        w = self.w
        cands = [b for b in w.buildings.values() if role in BUILDINGS[b.kind]["roles"] and w.empty(b)
                 and dist(p.x, p.y, b.x, b.y) <= r]
        return min(cands, key=lambda b: dist(p.x, p.y, b.x, b.y)) if cands else None

    def failed_lately(self, p, item, steps=None):
        """Whether a plan for item came to nothing these last days, or needs what one could not get
        lately (hides, when the hunts fail): try something else for now."""
        lately = [r for r in self.e.refused.get(p.id, []) if self.w.tick - r[0] < TPD * 3]
        if any(r[1].get("item") == item for r in lately):
            return True
        short = set()
        for r in lately:
            m = re.search(r"you need \d+ ([a-z ]+?)(?: or |$)", r[2] if len(r) > 2 else "")
            if m:
                short.add(m.group(1).strip().replace(" ", "_"))
        if not short:
            return False
        need = set()
        for r in recipes_making(item):
            need |= set(r["ins"])
        return bool(need & short)

    def winter_goal(self, p):
        w = self.w
        if w.season() not in ("summer", "autumn") or I.warmth(p.inv) >= 3:
            return None
        for item in WARM:
            if p.inv.get(item) or self.failed_lately(p, item):
                continue
            slot = I.WEARABLE[item][0]
            if any(I.WEARABLE.get(k, ("", 0))[0] == slot for k in p.inv):
                continue
            steps = self.planner.get(p, item, 1)
            if steps and len(steps) <= 5:
                return self.intent(f"warm clothes for winter: {I.pretty(item)}", steps)
        return None

    def store_of(self, p):
        """One's biggest store (a shelter keeps a little; a store keeps a winter's food)."""
        mine = [b for b in self.w.owned(p.id) if b.done and "store" in BUILDINGS[b.kind]["roles"]]
        return max(mine, key=lambda b: BUILDINGS[b.kind]["roles"]["store"]["capacity"], default=None)

    def store_food_goal(self, p):
        w = self.w
        store = self.store_of(p)
        if not store or BUILDINGS[store.kind]["roles"]["store"]["capacity"] < 30:
            if not self.has_home(p):
                return None
            steps = self.planner.build(p, "store")
            return self.intent("a store", steps) if steps else None
        # a winter is 10 days at 3 a day: lay by for the household (self, partner, young children)
        kids = [c for c in p.children if w.people.get(c) and w.people[c].alive and not w.people[c].adult(w.tick)]
        partner_shares = p.partner and w.people.get(p.partner) and w.people[p.partner].alive and \
            self.store_of(w.people[p.partner]) in (None, store)
        heads = 1 + len(kids) + (1 if partner_shares else 0)
        want = 25 * heads if w.season() in ("summer", "autumn") else 8 * heads
        if food_worth(store.inv) >= min(want, 0.8 * BUILDINGS[store.kind]["roles"]["store"]["capacity"]):
            return None
        if p.satiety < 10:
            return None                     # hungry, one would only eat it on the way
        keep = [k for k in p.inv if I.info(k).get("food") and I.info(k).get("spoil", 1) < 1 / 500]
        if keep and dist(p.x, p.y, store.x, store.y) < 20:
            return self.intent("lay food by", [{"do": "put", "item": keep[0], "x": store.x, "y": store.y}])
        # food that keeps: grain, smoked meat, dried berries, nuts
        for item in ("grain", "smoked_meat", "nuts", "smoked_fish") + (("dried_berries",) if p.satiety >= 15 else ()):
            steps = self.planner.get(p, item, 12)
            if steps and len(steps) <= 4:
                return self.intent("food for the store", steps + [{"do": "put", "item": item, "x": store.x, "y": store.y}])
        return None

    def fields(self, p):
        """The fields one works: one's own and one's partner's not let to a tenant, and those one rents (c83)."""
        w = self.w
        own = [b for q in (p.id, p.partner) if q is not None for b in w.owned(q)
               if b.kind == "farm" and (not w.tenancies or w.tenant_of(b) is None)]
        if w.tenancies:
            own += [w.buildings[t["field"]] for t in w.tenancies
                    if not t["done"] and t["tenant"] == p.id and t["field"] in w.buildings]
        return own

    @staticmethod
    def has_seed(p):
        return bool(p.inv.get("seeds") or p.inv.get("grain", 0) >= 2)

    def ripe_field(self, p):
        return any(b.crop and b.crop.get("ripe") and b.inv for b in self.fields(p))

    def field_to_sow(self, p):
        if self.w.season() == "winter" or not (p.inv.get("seeds") or p.inv.get("grain", 0) >= 2):
            return False
        return any(b.done and not b.crop and not b.inv for b in self.fields(p))

    def let_field(self, p, empty, seed):
        """A field lying idle at sowing time, with no seed to sow it or more fields than one sows: let it to a
        neighbour without land of their own, for a share of each harvest (c83)."""
        w = self.w
        if not empty or w.season() not in ("spring", "summer") or (seed and len(empty) < 2) or w.rng.random() > 0.3:
            return None
        b = empty[-1]
        if w.tenancies and w.tenancy(b):
            return None
        for o in w.near(p.x, p.y, 6):
            if o.id == p.id or not o.adult(w.tick) or o.mind == "llm" and w.rng.random() < 0.5 or self.fields(o) \
                    or p.rel.get(str(o.id), {}).get("trust", 0) < -0.1 or o.id == p.partner or not self.has_seed(o):
                continue
            share = "half" if p.traits["generosity"] < 0.3 else "third"
            return self.intent("let a field", [{"do": "propose", "to": o.name, "kind": "tenancy", "x": b.x, "y": b.y,
                                                "share": share, "days": 20}],
                               w.rng.choice([f"Work my field for {share if share == 'half' else 'a third'} of the harvest?", None]), o.name)
        return None

    def farm_goal(self, p):
        w, e = self.w, self.e
        if e.can_try(p, "farming"):
            return None
        farms = self.fields(p)
        ripe = [b for b in farms if b.done and b.inv.get("grain") or b.inv.get("flax")]
        if ripe:
            b = ripe[0]
            what = "grain" if b.inv.get("grain") else "flax"
            store = self.store_of(p)
            return self.intent("the harvest", [{"do": "gather", "item": what, "n": 60}]
                               + ([{"do": "put", "item": what, "x": store.x, "y": store.y}] if store else []))
        if w.season() == "winter":
            return None
        seed = "seeds" if p.inv.get("seeds") else ("grain" if p.inv.get("grain", 0) >= 2 else None)
        empty = [b for b in farms if b.done and not b.crop and not b.inv]
        let = self.let_field(p, [b for b in empty if b.owner == p.id], seed)
        if let:
            return let
        if seed and empty:
            return self.intent("sow", [{"do": "plant", "item": seed, "x": empty[0].x, "y": empty[0].y}])
        if seed and len(farms) < 1 + int(p.traits["industry"] * 3) and p.skill("farming") > 0.05 or (seed and not farms):
            field = self.empty_near(p, "farm", 10)
            if field:
                return self.intent("a field", [{"do": "claim", "x": field.x, "y": field.y}, {"do": "plant", "item": seed}])
            steps = self.planner.build(p, "farm")
            if steps:
                return self.intent("a field", steps + [{"do": "plant", "item": seed}])
        if not seed and w.season() in ("summer", "autumn") and p.traits["industry"] > 0.5:
            return self.intent("seed for next year", [{"do": "gather", "item": "fibre", "n": 15}])
        return None

    def tally_goal(self, p):
        """A store robbed by someone unknown, and pottery known: write a tally and keep it in the store,
        so the next who takes from it is known (c50)."""
        w, e = self.w, self.e
        st = self.store_of(p)
        if not st or st.owner != p.id or e.can_try(p, "writing"):
            return None
        if any(str(k).startswith("tablet:") for k in st.inv):
            return None
        robbed = any("you do not know who" in text for _, text in p.events[-30:])
        if not robbed and w.rng.random() > 0.03:
            return None
        get, ready = self.tablet(p)
        if get is None:
            return None
        return self.intent("a tally for my store", get + ([{"do": "go", "x": st.x, "y": st.y},
                                                           {"do": "write", "text": f"The tally of {p.name}'s store", "x": st.x, "y": st.y}] if ready else []))

    def tablet(self, p):
        """Steps to a tablet in hand, and whether it will be in hand at their end: a tablet fired in a kiln is
        taken out on a later plan (one does not stand idle while it fires)."""
        if p.inv.get("tablet"):
            return [], True
        get = self.planner.get(p, "tablet", 1)
        if get is None or len(get) > 4:
            return None, False
        fired = any(s.get("do") == "craft" and s.get("item") == "tablet" for s in get)
        return get, not fired

    def deed_goal(self, p):
        """A promise owed to one and not yet written, with writing within reach: write it down, so it stands
        past its day and can be passed on (C2)."""
        w, e = self.w, self.e
        if e.can_try(p, "writing") and p.skill("writing") < 0.1:
            return None
        owed = [pr for pr in w.promises if not pr["done"] and pr["to"] == p.id and not pr.get("deed")
                and pr["due"] - w.tick > TPD]
        o = w.people.get(owed[0]["by"]) if owed else None
        if not o or not o.alive:
            return None
        get, ready = self.tablet(p)
        if get is None:
            return None
        return self.intent(f"write down {o.name}'s promise", get + ([{"do": "write", "promise": o.name}] if ready else []))

    def worn(self, p, owner, r=12):
        """Buildings of owner's (or owner's partner's) within r of p, worn to half or less, the most worn first."""
        w = self.w
        mine = (owner.id, owner.partner)
        own = sorted({b.id: b for m in mine if m is not None for b in w.owned(m)}.values(), key=lambda b: b.id)
        out = [b for b in own if b.done and b.hp <= BUILDINGS[b.kind]["hp"] * 0.5
               and dist(p.x, p.y, b.x, b.y) <= r]
        return sorted(out, key=lambda b: b.hp / BUILDINGS[b.kind]["hp"])

    def mend_steps(self, p, b):
        stuff = mend_stuff(b)
        get = [] if p.inv.get(stuff) else self.planner.get(p, stuff, 1)
        if get is None or len(get) > 3:
            return None
        return get + [{"do": "mend", "x": b.x, "y": b.y}]

    def upkeep_goal(self, p):
        """Mend what is one's own and worn near where one lives (c59: buildings weather and fall unless
        mended); with more worn than one can keep up and food to spare, hire a neighbour to mend."""
        w = self.w
        if not p.adult(w.tick):
            return None
        worn = self.worn(p, p)
        if not worn:
            return None
        if len(worn) >= 4 and not any(not s["done"] and p.id in (s["master"], s["servant"]) for s in w.services):
            hire = self.hire_mender(p, len(worn))
            if hire:
                return hire
        for b in worn[:3]:
            steps = self.mend_steps(p, b)
            if steps:
                return self.intent(f"mend my {b.kind}", steps)
        return None

    def hire_mender(self, p, n):
        w = self.w
        foods = sorted((k for k in p.inv if I.info(k).get("food") and p.inv[k] >= 6), key=lambda k: -I.info(k)["food"])
        store = self.store_of(p)
        if not foods or food_worth(p.inv) + (food_worth(store.inv) if store else 0) < 30:
            return None
        busy = {s["servant"] for s in w.services if not s["done"]} | {s["master"] for s in w.services if not s["done"]}
        cands = [o for o in w.near(p.x, p.y, 6) if o.id != p.id and o.mind == "bot" and o.adult(w.tick) and o.id not in busy
                 and food_worth(o.inv) < 8 and p.rel.get(str(o.id), {}).get("trust", 0) > -0.3]
        if not cands:
            return None
        o = min(cands, key=lambda o: food_worth(o.inv))
        return self.intent(f"hire {o.name} to mend", [{"do": "propose", "to": o.name, "hire_days": 1, "give": {foods[0]: 6},
                                                       "text": f"A day mending my buildings ({n} are worn) for 6 {I.pretty(foods[0])}?"}])

    def serve(self, p):
        """In someone's service: mend the master's worn buildings, else help finish their building, else bring
        wood and stone to their store. (Bots hire only to mend, c59: hiring for building cost 2.3% of the
        living in bot worlds, c56.)"""
        w = self.w
        s = next((s for s in w.services if not s["done"] and s["servant"] == p.id), None)
        m = w.people.get(s["master"]) if s else None
        if not m or not m.alive or not p.adult(w.tick):
            return None
        for b in self.worn(p, m, r=20)[:3]:             # the master's worn buildings first: the work of upkeep
            steps = self.mend_steps(p, b)
            if steps:
                return self.intent(f"work for {m.name}: mend", steps)
        site = next((b for b in w.owned(m.id) if not b.done), None)
        if site:
            return self.intent(f"work for {m.name}", [{"do": "build", "kind": site.kind, "x": site.x, "y": site.y}])
        store = self.store_of(m)
        if not store:
            return None
        what = "stone" if w.rng.random() < 0.3 and self.e.find(p, "stone") else "wood"
        return self.intent(f"work for {m.name}", [{"do": "gather", "item": what, "n": 8},
                                                   {"do": "put", "item": what, "x": store.x, "y": store.y}])

    def market_goal(self, p, g):
        """A leader whose people post trades at several stores near home raises a market among them, so all
        that is offered there is known to whoever comes (C5)."""
        w, e = self.w, self.e
        home = w.buildings.get(p.home)
        if not home or len(g.members) < 3 or w.rng.random() > 0.2:
            return None
        if any("market" in BUILDINGS[m.kind]["roles"] and dist(m.x, m.y, home.x, home.y) <= 10
               for m in w.buildings.values()):                 # one there already, built or going up
            return None
        trading = [b for b in w.buildings.values() if b.trade and dist(b.x, b.y, home.x, home.y) <= 4]
        if len(trading) < 3:
            return None
        steps = self.planner.build(p, "market")
        if not steps or len(steps) > 12:                # planks and stone take a while: a long errand (c61)
            return None
        # beside the trading stores: within 2 of as many as can be
        spot = max(((x, y) for x, y in w.beside(home.x, home.y, 3) if not e.site_ok(p, "market", x, y)),
                   key=lambda t: sum(1 for b in trading if dist(t[0], t[1], b.x, b.y) <= 2), default=None)
        if spot:
            steps[-1] = dict(steps[-1], x=spot[0], y=spot[1])
        return self.intent(f"a market for {g.name}", steps, most=14)

    def law_goal(self, p, g):
        """A leader of a few households gives them a law, written down when a tablet can be had (C2:
        unwritten, it dies with its maker)."""
        w, e = self.w, self.e
        if len(g.members) < 3 or w.rng.random() > 0.15:
            return None
        unwritten = [l for l in g.laws if not l[2]]
        if g.laws and not unwritten:
            return None
        can = not e.can_try(p, "writing") or p.skill("writing") >= 0.1
        get, ready = self.tablet(p) if can else (None, False)
        if unwritten and (get is None or (not ready and not get)):
            return None                         # a law already given, and no way to write it down
        text = unwritten[0][1] if unwritten else LAWS[w.rng.randrange(len(LAWS))]
        if get and not ready:
            return self.intent(f"a tablet for {g.name}'s law", get)        # fired first; the law on a later day
        return self.intent(f"a law for {g.name}", (get or []) + [{"do": "make_law", "group": g.name, "text": text}])

    def keeps_beasts(self, p):
        return any(b.animals for b in self.w.owned(p.id))

    def herd_goal(self, p):
        w, e = self.w, self.e
        if e.can_try(p, "herding"):
            return None
        pens = [b for b in w.owned(p.id) if "pen" in BUILDINGS[b.kind]["roles"]]
        for b in pens:
            if b.done and (b.inv.get("milk") or b.inv.get("wool")):
                what = "milk" if b.inv.get("milk") else "wool"
                return self.intent("tend the flock", [{"do": "take", "item": what, "x": b.x, "y": b.y}])
            grazed = any(w.t(x, y) in ".," for x, y in [(b.x, b.y)] + list(w.beside(b.x, b.y)))
            eats = sum(TAME[k]["eats"] * n for k, n in b.animals.items())
            fodder = b.inv.get("hay", 0) + b.inv.get("grain", 0)
            if b.done and b.animals and w.season() in ("summer", "autumn") and fodder < eats * (11 if grazed else 20):
                return self.intent("hay for winter", [{"do": "gather", "item": "hay", "n": 15}, {"do": "put", "item": "hay", "x": b.x, "y": b.y}])
            if b.done and b.animals and (w.season() == "winter" or not grazed) and fodder < eats * 3:
                steps = self.planner.get(p, "grain", eats * 4)
                if steps is not None and len(steps) <= 2:
                    return self.intent("feed the beasts", steps + [{"do": "put", "item": "grain", "x": b.x, "y": b.y}])
        # a full pen: a breeding pair for kin or a friend near with an empty pen of their own
        for b in pens:
            cap = BUILDINGS[b.kind]["roles"]["pen"]["capacity"]
            kind, n = max(b.animals.items(), key=lambda kv: kv[1]) if b.animals else (None, 0)
            if kind and n >= 4 and sum(b.animals.values()) >= cap - 1:
                for o in w.near(p.x, p.y, self.e.sight(p)):
                    if o.id == p.id or o.id == p.partner or not o.adult(w.tick):
                        continue
                    close = p.rel.get(str(o.id), {})
                    if not (close.get("kin") or close.get("trust", 0) >= 0.4):
                        continue
                    their = self.e.pen_of(o, room=True)
                    if their and not their.animals:
                        return self.intent("young for kin", [{"do": "give", "to": o.name, "item": kind, "n": 2}])
        if p.skill("herding") < 0.05 and p.traits["curiosity"] + p.traits["industry"] < 0.5:
            return None
        tamable = [h for h in e.herds_of(p) if WILD[h["kind"]].get("tame") and WILD[h["kind"]]["tame"][0] != "horse"]
        if not tamable:
            # tracks a little further off, as taming itself looks for them
            tamable = [h for h in w.herds if h["n"] > 0 and WILD[h["kind"]].get("tame") and WILD[h["kind"]]["tame"][0] != "horse"
                       and dist(p.x, p.y, h["x"], h["y"]) <= 20]
        if not tamable:
            return None
        if not pens:
            steps = self.planner.build(p, "pen")
            return self.intent("a pen", steps) if steps and len(steps) <= 6 else None
        b = pens[0]
        fodder = b.inv.get("hay", 0) + b.inv.get("grain", 0)
        if w.season() == "winter" and fodder < 10 * (sum(TAME[k]["eats"] * n for k, n in b.animals.items()) + 2):
            return None                                 # no taking in beasts one cannot feed till spring
        if b.done and sum(b.animals.values()) < 6:
            rope = [] if p.inv.get("rope") else self.planner.get(p, "rope", 1)
            if rope is None:
                return None                             # no rope to be had: no leading a beast home
            kept = next(iter(b.animals), None)          # a pair breeds: tame more of what one keeps
            h = next((h for h in tamable if WILD[h["kind"]]["tame"][0] == kept), tamable[0])
            return self.intent("tame beasts", rope + [{"do": "tame", "animal": h["kind"]}])
        return None

    PLACE_START = {"T": ("Oak", "Ash", "Elm", "Holly"), "h": ("Stone", "Crag", "High", "Grey"), "^": ("Crag", "Stone"),
                   "~": ("Brook", "Mere", "Wade"), "m": ("Reed", "Fen", "Moss"), ".": ("Green", "Long", "Fair", "Wide"),
                   ",": ("Green", "Barley", "Fair"), "s": ("Sand", "Shell")}
    PLACE_END = ("stead", "ford", "holm", "ley", "wick", "ham", "by", "field", "hollow", "well")

    def place_name(self, x, y):
        """A name from the lie of the land around (x, y): its most common ground, water near if any."""
        w = self.w
        from collections import Counter
        ground = Counter(w.t(i, j) for i, j in w.beside(x, y, 3))
        kind = "~" if ground.get("~") else ground.most_common(1)[0][0]
        taken = {pl[2] for pl in w.places}
        for _ in range(12):
            name = w.rng.choice(self.PLACE_START.get(kind, self.PLACE_START["."])) + w.rng.choice(self.PLACE_END)
            if name not in taken:
                return name
        return name + " " + str(len(w.places) + 1)

    def pick_vocation(self, p):
        if p.traits["sociability"] > 0.6 and p.traits["ambition"] > 0.55 and p.traits["boldness"] > 0.4 and self.w.rng.random() < 0.35:
            return "trader"                     # a calling of roads and bargains, not of a craft (c70)
        best, score = "", -1
        for v, (craft, _, _) in VOCATIONS.items():
            s = p.skill(craft) + 0.3 * self.w.rng.random()
            if not self.e.can_try(p, craft):
                s += 0.2
            if s > score:
                best, score = v, s
        return best

    def craft_goal(self, p):
        """Make what one's vocation makes, keep a little, and put the rest up for trade."""
        w = self.w
        v = VOCATIONS.get(p.vocation)
        if not v:
            return None
        craft, goods, _ = v
        if self.e.can_try(p, craft):
            return None
        store = self.store_of(p)
        stock = sum(store.inv.get(k, 0) for k in goods) if store else 0
        if stock >= 6:
            return None
        for item in w.rng.sample(goods, len(goods)):
            if self.failed_lately(p, item):
                continue
            steps = self.planner.get(p, item, p.inv.get(item, 0) + 1)
            if steps and len(steps) <= 6:
                plan = steps
                if store:
                    plan = plan + [{"do": "put", "item": item, "x": store.x, "y": store.y}]
                    if not any(item in t["give"] for t in store.trade):
                        price = max(1, round(I.ITEMS[item]["worth"] / 2))
                        plan.append({"do": "post", "x": store.x, "y": store.y, "give": {item: 1}, "get": {"grain": price}})
                return self.intent(f"my craft: {I.pretty(item)}", plan)
        return None

    def advance_goal(self, p):
        """Reach for crafts beyond one's own: the next that one could learn."""
        w, e = self.w, self.e
        mine = max((CRAFTS[c]["era"] for c, s in p.skills.items() if c in CRAFTS and s >= 0.3), default=0)
        cur = p.traits.get("learning")
        if cur and p.skill(cur) < 0.3 and not e.can_try(p, cur):
            steps = self.planner.practise(p, cur)
            if steps and len(steps) <= (10 if CRAFTS[cur]["era"] >= 2 else 8):
                return self.intent(f"learn {cur.replace('_', ' ')}", steps)
        if cur and p.skill(cur) >= 0.3:
            # able now: a curious or ambitious one may make it their living
            v = next((v for v, (c, _, _) in VOCATIONS.items() if c == cur), None)
            if v and w.rng.random() < 0.3 + 0.5 * p.traits["curiosity"]:
                p.vocation = v
            p.traits.pop("learning", None)
        cands = []
        for c, v in CRAFTS.items():
            if p.skill(c) >= 0.3 or e.can_try(p, c) or v["era"] > mine + 1:
                continue
            # the newest within reach first, and among those the ones that open the most others; the next step in
            # one's own line as much as a new age (a smelter to alloying and casting: c63)
            line = any(p.skill(pre) >= 0.3 and CRAFTS[pre]["era"] >= 2 for pre in v["pre"])
            cands.append((-v["era"] - 0.1 * UNLOCKS.get(c, 0) - 0.8 * w.rng.random() - (1.2 if line else 0), c))
        cands.sort()
        cands = [(None, None, c) for _, c in cands]
        for _, _, c in cands[:4]:
            if CRAFTS[c].get("practice") and not recipes_for(c):
                continue
            steps = self.planner.practise(p, c)
            if steps and len(steps) <= (10 if CRAFTS[c]["era"] >= 2 else 8):   # metal takes a long road
                p.traits["learning"] = c
                return self.intent(f"learn {c.replace('_', ' ')}", steps)
        # or ask someone able to teach one
        for o in w.near(p.x, p.y, 6):
            for c, s in o.skills.items():
                if c in CRAFTS and s >= 0.5 and p.skill(c) < 0.2 and not e.can_try(p, c):
                    gift = next((k for k in ("smoked_meat", "grain", "berries") if p.inv.get(k, 0) >= 3), None)
                    later = {} if gift else {"promise_give": {"grain": 4}, "due_days": 6}
                    return self.intent(f"learn {c} from {o.name}", [{"do": "propose", "to": o.name, "learn": c, **later,
                                                                      "give": {gift: 3} if gift else {},
                                                                      "text": f"Teach me {c.replace('_', ' ')}?"}])
        return None

    def social_goal(self, p):
        w, e = self.w, self.e
        near = [o for o in w.near(p.x, p.y, 5) if o.id != p.id]
        # feed hungry kin, from what one carries or one's store
        store = self.store_of(p)
        for o in near:
            r = p.rel.get(str(o.id), {})
            if not r.get("kin") or o.satiety >= 6 or w.rng.random() > p.traits["generosity"] + 0.4:
                continue
            if food_worth(p.inv) >= 6:
                food = next(k for k in p.inv if I.info(k).get("food"))
                return self.intent(f"feed {o.name}", [{"do": "give", "to": o.name, "item": food, "n": 3}])
            if store and food_worth(store.inv) >= 12:
                food = max((k for k in store.inv if I.info(k).get("food")), key=lambda k: store.inv[k])
                return self.intent(f"feed {o.name}", [{"do": "take", "item": food, "n": 4, "x": store.x, "y": store.y},
                                                      {"do": "give", "to": o.name, "item": food, "n": 4}])
        # teach one's children and kin what one knows well
        for o in near:
            r = p.rel.get(str(o.id), {})
            if r.get("kin") or r.get("trust", 0) > 0.5:
                for c, s in p.skills.items():
                    if c in CRAFTS and s >= 0.5 and o.skill(c) < 0.3 and not e.can_try(o, c) and w.rng.random() < 0.15:
                        return self.intent(f"teach {o.name}", [{"do": "teach", "to": o.name, "craft": c}], self.line("teach"), o.name)
        if not p.adult(w.tick):
            return None
        # a partner, and children
        if p.partner is None and p.age(w.tick) >= 17:
            cands = [o for o in near if o.partner is None and o.adult(w.tick) and not p.rel.get(str(o.id), {}).get("kin")
                     and p.rel.get(str(o.id), {}).get("trust", 0) >= 0.0 and abs(o.age(w.tick) - p.age(w.tick)) < 15]
            if cands and w.rng.random() < 0.3 + 0.4 * p.traits["sociability"]:
                o = max(cands, key=lambda o: p.rel.get(str(o.id), {}).get("trust", 0))
                return self.intent(f"pledge with {o.name}", [{"do": "propose", "to": o.name, "kind": "pledge", "text": "Will you be my partner?"}])
        partner = w.people.get(p.partner) if p.partner else None
        if partner and partner.alive and self.has_home(p) and p.satiety >= 14 and not p.pregnant and not partner.pregnant:
            kids = [c for c in p.children if w.people.get(c) and w.people[c].alive and not w.people[c].adult(w.tick)]
            if len(kids) < 2 + int(p.traits["sociability"] * 3) and w.rng.random() < 0.35 and dist(p.x, p.y, partner.x, partner.y) <= 8:
                return self.intent("a child", [{"do": "propose", "to": partner.name, "kind": "child"}])
        # a friendly word now and then
        if near and w.rng.random() < 0.05 * (1 + p.traits["sociability"]):
            o = w.rng.choice(near)
            return self.intent("greet", [{"do": "wait", "hours": 1}], self.line("greet"), o.name)
        return None

    def raid_weight(self, p):
        """How much a raid is on a leader's mind (c73): only the bold who lead; more when hungry, in a lean or hard
        year, or among a people for whom taking from strangers by daring is no shame."""
        from ..content.peoples import PEOPLES
        w = self.w
        if p.traits["boldness"] < 0.5 or not p.adult(w.tick) or not any(
                w.groups.get(g) and w.groups[g].leader == p.id for g in p.groups):
            return 0.0
        need = p.satiety <= 8 or w.year_at(p.x, p.y) in ("lean", "hard")
        honour = PEOPLES.get(p.people, {}).get("customs", {}).get("raid_honour", False)
        return 0.15 + (0.8 if need else 0) + (0.5 if honour else 0)

    def raid_goal(self, p, g=None):
        """A raid, by reckoning (c72): a bold leader with fighters near, driven by hunger, a lean or hard year, a people
        that holds raiding strangers no shame, or rare daring, falls on a rich store of strangers known to them where
        fewer stand to defend it than they bring."""
        from ..content.peoples import PEOPLES
        w, e = self.w, self.e
        if p.traits["boldness"] < 0.5 or e.band_of(p):
            return None
        honour = PEOPLES.get(p.people, {}).get("customs", {}).get("raid_honour", False)
        need = p.satiety <= 8 or w.year_at(p.x, p.y) in ("lean", "hard")
        if not (need or honour or p.traits["ambition"] > 0.7):
            return None
        mine = e.followers(p)
        fighters = [w.people[i] for i in mine if w.people[i].adult(w.tick) and w.people[i].health > 5
                    and dist(p.x, p.y, w.people[i].x, w.people[i].y) <= 20]
        if len(fighters) < 3:
            return None
        ours = set(mine) | {p.id}
        best = None
        for b in w.buildings_within(p.x, p.y, 45):
            if not b.done or "store" not in BUILDINGS[b.kind]["roles"] or b.owner in ours or b.owner < 0:
                continue
            d = dist(p.x, p.y, b.x, b.y)
            if d < 6 or (key(b.x, b.y) not in p.known and d > 15):
                continue
            beaten = p.known.get(f"beaten@{b.x} {b.y}")
            if beaten and w.tick - beaten[2] < 2 * TPY // 4:
                continue                            # beaten there lately: not again so soon
            o = w.people.get(b.owner)
            if not o or p.rel.get(str(o.id), {}).get("kin") or food_worth(b.inv) < 15:
                continue
            if e.same_realm(p, o) or (e.peace_between(p, o) and w.rng.random() > 0.05):
                continue                            # not one's own lord's people; a sworn peace is rarely broken (c75)
            held = len(e.defenders_at(b.x, b.y, ours))
            if len(fighters) + 1 < 1.4 * max(1, held):
                continue
            score = food_worth(b.inv) / (d + 5) * (1.5 if o.people and o.people != p.people else 1) * (1.5 if p.feel.get(o.people, 0) < 0 else 1)
            if best is None or score > best[0]:
                best = (score, b)
        if not best:
            return None
        b = best[1]
        o = w.people.get(b.owner)
        take = bool(honour and o and o.people != p.people) or (o and p.feel.get(o.people, 0) < -0.2)
        # the spoils: the grasping take them all, most take half, the open-handed let each keep their own (c81)
        gen, amb = p.traits.get("generosity", 0.5), p.traits.get("ambition", 0.5)
        share = "each" if gen > 0.6 else "mine" if gen < 0.25 and amb > 0.5 else "half"
        return self.intent(f"raid ({b.x},{b.y})", [{"do": "muster", "hours": 2},
                                                   {"do": "raid", "x": b.x, "y": b.y, "take": take, "share": share}],
                           self.w.rng.choice(["To arms! We ride for their stores.", "Gather, all of you: there is grain to be had.", None]))

    # ================= rites (c79) =================
    def rite(self, p):
        """One's people's rite today: most go, the sociable more, unless hungry or far."""
        w = self.w
        r = w.rites.get(p.people or "")
        if not r or r.get("done") or r["day"] != w.day() or not p.adult(w.tick) or w.hour() >= 7:
            return None
        if (p.intent or {}).get("rite") == r["day"] or p.satiety <= 5 or not 3 < dist(p.x, p.y, r["x"], r["y"]) <= 25:
            return None
        if w.rng.random() > 0.45 + 0.45 * p.traits["sociability"]:
            return None
        out = self.intent(f"keep {r['name']}", [{"do": "go", "x": r["x"], "y": r["y"]}, {"do": "wait", "hours": max(1, 8 - w.hour())}])
        out["rite"] = r["day"]
        return out

    # ================= captives (c76) =================
    def captive(self, p, own):
        """One held: buy one's own freedom if one carries the price, slip away at night if bold, else bide."""
        w = self.w
        if not own:
            if all(p.inv.get(k, 0) >= n for k, n in p.held["price"].items()):
                return self.intent("buy my freedom", [{"do": "ransom", "who": p.name}])
            if w.is_night() and w.rng.random() < 0.06 * p.traits["boldness"]:
                return self.intent("slip away", [{"do": "escape"}])
        return self.intent("bide", [{"do": "wait", "hours": 2}])

    def captor(self, p):
        """One holding captives lets them go after a season unransomed: feeding them costs more than they will fetch."""
        w = self.w
        for qid in w.holding.get(p.id, ()):
            q = w.people.get(qid)
            if q and q.held and w.tick - q.held["since"] > DPS * TPD:
                return self.intent(f"let {q.name} go", [{"do": "release", "who": q.name}])
        return None

    def ransom_goal(self, p):
        """Kin, or the leader of one's group, held captive: pay what is asked, if one has it or has it in store."""
        w = self.w
        if not w.holding or not p.adult(w.tick):
            return None
        for cid, held in w.holding.items():
            for qid in held:
                q = w.people.get(qid)
                if not q or not q.held:
                    continue
                r = p.rel.get(str(qid), {})
                leads = any(w.groups.get(g) and w.groups[g].leader == p.id for g in q.groups)
                if not (r.get("kin") in ("child", "parent") or p.partner == qid or (r.get("kin") and r.get("trust", 0) > 0.3) or leads):
                    continue
                cap = w.people.get(cid)
                if not cap or dist(p.x, p.y, cap.x, cap.y) > 40:
                    continue
                plan = []
                for k, n in q.held["price"].items():
                    short = n - p.inv.get(k, 0)
                    if short > 0:
                        st = self.e.building_near(p, lambda b, k=k, short=short: b.done and b.owner in (p.id, p.partner)
                                                  and b.inv.get(k, 0) >= short, r=20)
                        if not st:
                            plan = None
                            break
                        plan.append({"do": "take", "item": k, "n": short, "x": st.x, "y": st.y})
                if plan is None:
                    continue
                return self.intent(f"ransom {q.name}", plan + [{"do": "ransom", "who": q.name}])
        return None

    def raided_by(self, p, o, days=40):
        """Whether o's people (o's realm) raided p's home within the last days (c75)."""
        w, e = self.w, self.e
        since = w.tick - days * TPD
        theirs = {h.id for h in e.realms(o)}
        for t, who, kind, _ in reversed(p.ledger):
            if t < since:
                break
            if kind in ("raided", "robbed") and who in w.people and (who == o.id or theirs & {h.id for h in e.realms(w.people[who])}):
                return True
        return False

    def peace_goal(self, p, g):
        """A leader whose people were raided seeks peace with the raiders' head, bringing a gift if they can spare one;
        one sworn to a lord who did not protect them goes their own way (c75)."""
        w, e = self.w, self.e
        if g.parent:
            lord = w.groups.get(g.parent)
            head = w.people.get(lord.leader) if lord else None
            if head and p.rel.get(str(head.id), {}).get("trust", 0) < -0.35 and w.rng.random() < 0.3:
                return self.intent(f"leave {lord.name}", [{"do": "renounce", "group": g.name}])
        if w.rng.random() > 0.2:
            return None
        since = w.tick - 40 * TPD
        for t, who, kind, _ in reversed(p.ledger):
            if t < since:
                break
            if kind not in ("raided", "robbed") or who not in w.people:
                continue
            r = w.people[who]
            tops = [h for h in e.realms(r) if not h.parent]
            head = w.people.get(tops[0].leader) if tops else None
            if not head or not head.alive or head.id == p.id or e.peace_between(p, head) or e.same_realm(p, head):
                continue
            if dist(p.x, p.y, head.x, head.y) > 30:
                continue
            gift = {k: 2} if (k := next((k for k in ("grain", "flour", "cheese", "dried_fish", "meat") if p.inv.get(k, 0) >= 4), None)) else {}
            if dist(p.x, p.y, head.x, head.y) > 10:
                # far: one of one's people carries the words (c84)
                env = next((w.people[i] for i in e.followers(p) if w.people[i].adult(w.tick) and not w.people[i].held
                            and dist(p.x, p.y, w.people[i].x, w.people[i].y) <= 3 and not e.errand_of(w.people[i])), None)
                if env:
                    return self.intent(f"make peace with {head.name}", [{"do": "send", "to": head.name, "who": env.name, "kind": "peace",
                                                                         "give": gift, "text": "Let there be no more raiding between us."}])
            return self.intent(f"make peace with {head.name}", [{"do": "go", "to": head.name},
                                                                 {"do": "propose", "to": head.name, "kind": "peace", "give": gift,
                                                                  "text": "Let there be no more raiding between us."}])
        return None

    def fealty_goal(self, p, g):
        """Lords and sworn men (c71): an ambitious leader of a strong group asks homage of a weaker one's leader near,
        for a little grain a season; a leader of a small group in hunger or a hard year swears to a strong one near."""
        w, e = self.w, self.e
        if w.rng.random() > 0.15:
            return None
        size = lambda h: len(h.members) + sum(len(x.members) for x in e.sworn_to(h))
        others = []
        for o in w.near(p.x, p.y, 15):
            if o.id == p.id:
                continue
            h = e.group_of(o, None, lead=True)
            if h and h.id != g.id and not e.liege_chain(h, g.id) and not e.liege_chain(g, h.id):
                others.append((o, h))
        for o, h in others:
            if not h.parent and size(g) >= 2 * size(h) and p.traits["ambition"] > 0.6:
                return self.intent(f"ask homage of {h.name}", [{"do": "propose", "to": o.name, "kind": "homage",
                                                                 "get": {"grain": 2}, "text": "Swear to us, and none will touch you."}])
        need = p.satiety <= 8 or w.year_at(p.x, p.y) in ("lean", "hard")
        if not g.parent and need:
            for o, h in sorted(others, key=lambda t: -size(t[1])):
                if size(h) >= 2 * size(g) and p.rel.get(str(o.id), {}).get("trust", 0) >= 0:
                    return self.intent(f"swear to {h.name}", [{"do": "propose", "to": o.name, "kind": "fealty",
                                                                "give": {"grain": 2}, "text": "Stand by us in hard times."}])
        return None

    def order_goal(self, p):
        """A leader with people near sets them to work now and then (grand world, Phase 1.4): to reap one's ripe
        field, to gather what the household runs short of, or to mend what is worn."""
        w, e = self.w, self.e
        mine = e.followers(p)
        near = [w.people[i] for i in mine if dist(p.x, p.y, w.people[i].x, w.people[i].y) <= 20 and w.people[i].adult(w.tick)]
        if len(near) < 2 or w.rng.random() > 0.25:
            return None
        if self.ripe_field(p):
            task = {"do": "gather", "item": "grain", "n": 12}
        else:
            store = self.store_of(p)
            short = [k for k in self.lacking(p, store) if k != "berries" and e.find(p, k)]
            worn = self.worn(p, p, r=15)
            if worn and w.rng.random() < 0.5:
                task = {"do": "mend", "x": worn[0].x, "y": worn[0].y}
            elif short:
                task = {"do": "gather", "item": short[0], "n": 8}
            else:
                return None
        return self.intent("set my people to work", [{"do": "order", "to": "all", "task": task, "days": 1}])

    def lead_goal(self, p):
        w = self.w
        if not p.adult(w.tick):
            return None
        mine = [w.groups[g] for g in p.groups if w.groups.get(g) and w.groups[g].leader == p.id]
        peace = self.peace_goal(p, mine[0]) if mine and mine[0].dissolved is None else None
        if peace or p.traits["ambition"] < 0.6:
            return peace
        if not mine:
            if p.groups or w.rng.random() > 0.25:
                return None
            name = f"{p.name}'s people"
            return self.intent("found a household", [{"do": "found_group", "name": name,
                                                      "rules": group_rules(w.rng, p.traits, p.name)}])
        g = mine[0]
        # the place one's people live, named once they are a few households (C3: a geography of their own)
        home = w.buildings.get(p.home)
        if home and len(g.members) >= 3 and dist(p.x, p.y, home.x, home.y) <= 2 and w.rng.random() < 0.3 \
                and not any(dist(home.x, home.y, pl[0], pl[1]) <= 8 for pl in w.places):
            return self.intent("name our place", [{"do": "name_place", "name": self.place_name(home.x, home.y)}])
        # a common store: once the group is a few households, modest dues into a treasury
        if not g.treasury and len(g.members) >= 3 and w.rng.random() < 0.3:
            store = self.store_of(p)
            if store and BUILDINGS[store.kind]["roles"]["store"]["capacity"] >= 30:
                return self.intent(f"a common store for {g.name}", [{"do": "set_dues", "group": g.name, "give": {"grain": 2},
                                                                     "x": store.x, "y": store.y}])
        order = self.order_goal(p)
        if order:
            return order
        bond = self.fealty_goal(p, g)
        if bond:
            return bond
        law = self.law_goal(p, g)
        if law:
            return law
        market = self.market_goal(p, g)
        if market:
            return market
        for o in w.near(p.x, p.y, 6):
            if o.id not in g.members and o.id not in g.invited and p.rel.get(str(o.id), {}).get("trust", 0) > 0.3:
                return self.intent(f"invite {o.name}", [{"do": "invite", "to": o.name, "group": g.name}])
        return None

    def letters_goal(self, p):
        """One who has written before keeps a record of their store now and then: the practice that makes a reader
        and writer at length (literacy, the door to books, schools and the learned crafts: c61)."""
        w, e = self.w, self.e
        if not p.adult(w.tick) or p.skill("writing") < 0.4 or p.skill("literacy") >= 0.3:
            return None
        if w.tick - p.traits.get("wrote", -10 ** 6) < TPD * 20:       # a record every other season
            return None
        store = self.store_of(p)
        if not store:
            return None
        steps = self.planner.get(p, "tablet", 1)
        p.traits["wrote"] = w.tick
        if steps is None or len(steps) > 1:             # a tablet to hand (carried, kept, or pressed from clay held)
            return None
        held = ", ".join(f"{n} {I.pretty(k)}" for k, n in sorted(store.inv.items(), key=lambda kv: -kv[1])[:3]) or "nothing yet"
        text = f"Year {w.year() + 1}, {w.season()}: the store of {p.name} holds {held}."
        return self.intent("keep a record", steps + [{"do": "write", "text": text, "x": store.x, "y": store.y}])

    def school_goal(self, p):
        """Teach at a school near by, to whoever sits there to learn; or, reading and writing and leading a people,
        raise one where there is none (c61)."""
        w, e = self.w, self.e
        if not p.adult(w.tick) or w.is_night():
            return None
        school = e.building_near(p, lambda b: "school" in BUILDINGS[b.kind]["roles"], r=12, usable=False)
        if school:
            mine = sorted(((s, c) for c, s in p.skills.items() if c in CRAFTS and s >= 0.5), reverse=True)
            for s, c in mine[:4]:
                learner = next((q for q in w.near(school.x, school.y, 2) if q.id != p.id and q.skill(c) < s - 0.3
                                and q.age(w.tick) >= 6), None)
                if learner:
                    return self.intent(f"teach {c.replace('_', ' ')} at the school",
                                       [{"do": "go", "x": school.x, "y": school.y}, {"do": "teach", "to": learner.name, "craft": c}])
            return None
        lead = any(w.groups.get(g) and w.groups[g].leader == p.id and len(w.groups[g].members) >= 3 for g in p.groups)
        if not (lead or p.traits["ambition"] >= 0.6) or p.skill("literacy") < 0.3 or w.rng.random() > 0.3:
            return None
        steps = self.planner.build(p, "school")
        if steps and len(steps) <= 16:
            return self.intent("raise a school", steps, most=16)
        return None

    def legacy_goal(self, p):
        """Raise a cairn with carved words: for the kin one has lost, for one's people, or for oneself;
        about once a year at most."""
        w = self.w
        if not p.adult(w.tick) or w.season() == "winter":
            return None
        mine = [b for b in w.owned(p.id) if "monument" in BUILDINGS[b.kind]["roles"]]
        if any(w.tick - b.built < TPY for b in mine):
            return None
        kin = {"parent": "mother or father", "child": "child", "partner": "partner"}
        lost = [(w.people[int(i)], r.get("kin")) for i, r in p.rel.items() if r.get("kin") in kin and int(i) in w.people
                and not w.people[int(i)].alive and w.tick - (w.people[int(i)].died or 0) < TPY]
        lead = next((w.groups[g] for g in p.groups if w.groups.get(g) and w.groups[g].leader == p.id), None)
        if lost:
            o, rel = lost[0]
            name, text = f"{o.name}'s cairn", f"Here we remember {o.name}, {kin[rel]} of {p.name}."
        elif lead and w.rng.random() < 0.5:
            year = w.year() + 1
            name, text = lead.name, w.rng.choice([
                f"Here {lead.name} made their home, in the year {year}.",
                f"{lead.name}, led by {p.name}, raised this stone.",
                f"{lead.name} keeps its word: {(lead.rules or '').split('.')[0]}.",
                f"{len(lead.members)} households of {lead.name} stood here together in the year {year}."])[:200]
        elif p.traits["ambition"] > 0.6 and w.rng.random() < 0.3:
            name, text = f"{p.name}'s stone", w.rng.choice([f"{p.name} lived here and worked this land.",
                                                             f"{p.name} raised this stone. Remember me.",
                                                             f"Here {p.name} made a home."])
        else:
            return None
        steps = self.planner.build(p, "cairn")
        if not steps or len(steps) > 4:
            return None
        steps[-1].update(name=name, text=text)
        return self.intent(f"raise a cairn: {name}", steps)

    def trade_goal(self, p):
        """Buy a tool one lacks at a store that posts it, with what one has."""
        w = self.w
        # what is posted at the stores beside a market one knows is known to one too (C5)
        markets = [m for m in w.buildings.values() if m.done and "market" in BUILDINGS[m.kind]["roles"]
                   and (key(m.x, m.y) in p.known or dist(p.x, p.y, m.x, m.y) <= 8)]
        for b in w.buildings.values():
            if not b.trade or b.owner == p.id:
                continue
            if key(b.x, b.y) not in p.known and not any(dist(m.x, m.y, b.x, b.y) <= 2 for m in markets):
                continue
            for t in b.trade:
                item = next(iter(t["give"]))
                if p.inv.get(item) or not b.inv.get(item):
                    continue
                info = I.ITEMS[item]
                want = (info.get("tool") and not any(I.best_tool(p.inv, u)[0] for u in info["tool"])) or \
                    (item in WARM and I.warmth(p.inv) < 3) or (info.get("food") and p.satiety < 12)
                if not want:
                    continue
                # earn the price first if one lacks it
                pay = []
                for k, n in t["get"].items():
                    sub = self.planner.get(p, k, n)
                    if sub is None:
                        pay = None
                        break
                    pay += sub
                if pay is not None and len(pay) <= 3:
                    return self.intent(f"buy {I.pretty(item)}", pay + [{"do": "trade", "x": b.x, "y": b.y, "item": item}])
        return None

    def lacking(self, p, store):
        """What a household runs short of (carried and in its store, against STOCK), in a random order; berries
        when one carries little food. Nothing is gathered for the pile (grand world, Phase 1.1)."""
        w = self.w
        out = [k for k, n in STOCK.items() if p.inv.get(k, 0) + (store.inv.get(k, 0) if store else 0) < n]
        if food_worth(p.inv) < 6:
            out.append("berries")
        w.rng.shuffle(out)
        return out

    def want_goal(self, p):
        """A household with grain to spare that lacks a tool for its work, or warm clothes, posts at its store that it
        will give grain for one (c70): a buyer, so that what is made far off has somewhere to go."""
        w = self.w
        store = self.store_of(p)
        if not store or store.inv.get("grain", 0) < 25 or len(store.trade) >= 4:
            return None
        v = VOCATIONS.get(p.vocation)
        wants = []
        if v:
            wants += [k for k in v[1] if I.ITEMS.get(k, {}).get("tool") and not p.inv.get(k)][:1]
        if I.warmth(p.inv) < 3:
            wants += [k for k in ("wool_cloak", "fur_coat", "cloak") if not p.inv.get(k)][:1]
        for item in wants:
            if any(item in t["get"] or item in t["give"] for t in store.trade):
                continue                            # wanted already, or one's own store sells it
            price = max(2, round(I.ITEMS[item]["worth"]))
            return self.intent(f"buy {I.pretty(item)} at my store", [{"do": "post", "x": store.x, "y": store.y,
                                                                         "give": {"grain": price}, "get": {item: 1}}])
        return None

    def merchant_goal(self, p):
        """A trader carries what one store sells cheap to one that buys it dear (c70): bought for grain where it is
        posted for sale, sold for grain where a store posts that it wants it, if the gain is a third or more and the
        way not too long. The goods move; the ways they move on wear into trails."""
        w = self.w
        if p.vocation != "trader" or not p.adult(w.tick):
            return None
        known = lambda b: key(b.x, b.y) in p.known or dist(p.x, p.y, b.x, b.y) <= 8
        sells, buys = {}, {}
        for b in w.buildings.values():
            if not b.trade or b.owner == p.id or not known(b):
                continue
            for t in b.trade:
                if len(t["give"]) == 1 and len(t["get"]) == 1:
                    (gk, gn), (tk, tn) = next(iter(t["give"].items())), next(iter(t["get"].items()))
                    if tk == "grain" and gk != "grain" and b.inv.get(gk, 0) >= gn:
                        sells.setdefault(gk, []).append((tn / gn, b))          # grain a unit, to buy here
                    elif gk == "grain" and tk != "grain" and b.inv.get("grain", 0) >= gn:
                        buys.setdefault(tk, []).append((gn / tn, b))           # grain a unit, paid here
        best = None
        for item, ss in sells.items():
            for pb, bb in buys.get(item, []):
                for ps, sb in ss:
                    if sb.owner == bb.owner:
                        continue                    # not back to the hand it came from
                    gain = (pb - ps) / max(0.5, ps)
                    trip = dist(p.x, p.y, sb.x, sb.y) + dist(sb.x, sb.y, bb.x, bb.y)
                    if gain >= 0.3 and trip <= 90 and (best is None or gain > best[0]):
                        best = (gain, item, ps, sb, bb)
        if not best:
            return None
        _, item, ps, sb, bb = best
        grain = p.inv.get("grain", 0)
        store = self.store_of(p)
        fetch = []
        if grain < ps * 2 and store and store.inv.get("grain", 0) >= ps * 2:
            fetch = [{"do": "take", "item": "grain", "n": int(min(store.inv["grain"], ps * 6)), "x": store.x, "y": store.y}]
            grain += int(min(store.inv["grain"], ps * 6))
        n = int(min(6, grain // max(1, ps), sb.inv.get(item, 0)))
        if n < 1:
            return None
        return self.intent(f"carry {I.pretty(item)} to sell", fetch + [{"do": "trade", "x": sb.x, "y": sb.y, "item": item, "n": n},
                                                                       {"do": "trade", "x": bb.x, "y": bb.y, "item": "grain", "n": n}])

    def forage(self, p):
        w = self.w
        store = self.store_of(p)
        item = next((k for k in self.lacking(p, store) if self.e.find(p, k)), None)
        if not item:
            return self.intent("rest", [{"do": "wait", "hours": 3}])      # nothing wanted: the day is one's own
        plan = [{"do": "gather", "item": item, "n": 6}]
        if store and item != "berries":
            plan.append({"do": "put", "item": item, "x": store.x, "y": store.y})
        return self.intent("gather", plan)

    def line(self, kind):
        return self.w.rng.choice(LINES[kind])
