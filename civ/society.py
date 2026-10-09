"""Between people: speech, offers (deals, service, pledges, children), promises, posted trades,
who may use what, groups with rules, votes, dues and laws, and writing.

Nothing is enforced but what the engine can see: goods change hands only when both are there,
promises are remembered as kept or broken, written words last on tablets and parchment and can
only be read by those who have learned to."""
import re

from .content import BUILDINGS, CRAFTS
from .content import items as I
from .world import Group, key, dist, TPD
from .acts import norm, num


def goods(v):
    """{item: n} from what a mind wrote ([{item, qty}] or {item: n})."""
    out = {}
    if isinstance(v, dict):
        v = [{"item": k, "qty": n} for k, n in v.items()]
    for e in v or []:
        if isinstance(e, dict):
            k = norm(e.get("item"))
            try:
                n = int(float(e.get("qty", e.get("n", 1))))
            except (TypeError, ValueError):
                n = 1
            if k in I.ITEMS and n > 0:
                out[k] = out.get(k, 0) + min(n, 999)
    return out


def goods_text(g):
    return ", ".join(f"{n} {I.pretty(k)}" for k, n in g.items()) or "nothing"


def craft_of(v):
    c = norm(v) if v else None
    return c if c in CRAFTS else None


class Society:
    # ================= speech =================
    def speak(self, p, text, to=None, wake=True):
        w = self.w
        text = str(text)[:300].strip()
        if not text:
            return
        target = w.by_name(to) if to else None
        heard = []
        near = w.near(p.x, p.y, 4 if not w.is_night() else 2)
        # one speaks one's own tongue, or the tongue of the one spoken to if one knows it
        lang = target.people if target and target.people and p.skill(f"tongue:{target.people}") >= 0.5 else p.people
        for o in near:
            if o.id != p.id:
                to_them = f"{' (to ' + target.name + ')' if target and target.id != o.id else ''}"
                how = self.understood(lang, p, o, near)
                if how is None:
                    # a tongue one does not know: one hears that it is spoken, not what (grand world, Phase 2)
                    from .content.peoples import PEOPLES
                    word = PEOPLES[lang]["tongue"]["word"] if lang in PEOPLES else "a strange tongue"
                    self.tell(o, f"{p.name}{to_them} speaks in {word}; you catch none of it.")
                    if target and target.id == o.id:
                        self.wake(o, f"{p.name} spoke to you in a tongue you do not know")
                    continue
                self.tell(o, f"{p.name}{to_them}: \"{text}\"" + (f" ({how.name} puts it into your tongue)" if how is not True else ""))
                heard.append(o)
                self.heard[o.id] = (self.heard.get(o.id, []) + [(w.tick, p.id, text, bool(target and target.id == o.id))])[-6:]
                if target and target.id == o.id and (wake or o.mind == "bot"):   # a bot's thinking costs nothing
                    self.wake(o, f"{p.name} spoke to you")
        self.event("say", f"{p.name}{' to ' + target.name if target else ''}: \"{text}\"", p, target, said=text)
        return heard

    def understood(self, lang, p, o, near=()):
        """Whether o follows what p says in the tongue of people lang: True if o knows it (or it is no people's),
        else the person beside p who knows it and o's tongue and puts it into o's, else None."""
        if not lang or o.people == lang or o.skill(f"tongue:{lang}") >= 0.5:
            return True
        for x in near:
            if x.id not in (p.id, o.id) and dist(x.x, x.y, p.x, p.y) <= 2 and x.skill(f"tongue:{lang}") >= 0.5 \
                    and (not o.people or x.skill(f"tongue:{o.people}") >= 0.5):
                return x
        return None

    # ================= offers =================
    def start_propose(self, p, a):
        """Offer someone within 6 steps a deal: goods now (give/get), promises (promise_give/promise_get within
        due days), service (hire_days: they work for you; serve_days: you for them), teaching (teach: a craft
        you teach them; learn: a craft they teach you),
        a pledge as partners (kind: pledge), a child together (kind: child), or anything in words (text)."""
        w = self.w
        o = w.by_name(a.get("to") or a.get("target"))
        if not o or o.id == p.id:
            return "propose to whom?"
        if dist(p.x, p.y, o.x, o.y) > 6:
            return f"{o.name} is too far away to hear you"
        kind = str(a.get("kind") or "deal").lower()
        offer = {"id": w.new_id(), "from": p.id, "to": o.id, "kind": kind, "tick": w.tick, "text": str(a.get("text") or "")[:240],
                 "give": goods(a.get("give")), "get": goods(a.get("get")), "promise_give": goods(a.get("promise_give")),
                 "promise_get": goods(a.get("promise_get")), "due": num(a.get("due_days"), 5, 1, 40),
                 "hire_days": num(a.get("hire_days"), 0, 0, 40), "serve_days": num(a.get("serve_days"), 0, 0, 40),
                 "teach": craft_of(a.get("teach")), "learn": craft_of(a.get("learn")),
                 "name": str(a.get("name") or "")[:12]}
        if kind == "child" and not (p.adult(w.tick) and o.adult(w.tick)):
            return "only two grown people can have a child"
        if kind == "pledge" and (p.partner or o.partner):
            return "one of you is already pledged"
        if kind == "fealty":
            # p's group swears to o's, paying what p offers to give each season (c71)
            mine, theirs = self.group_of(p, None, lead=True), self.group_of(o, None, lead=True)
            if not mine or not theirs:
                return "fealty is sworn between the leaders of two groups"
            if mine.id == theirs.id or self.liege_chain(theirs, mine.id):
                return "a group cannot swear to itself or to one sworn to it"
            offer["tribute"] = goods(a.get("give")) or goods(a.get("tribute"))
            offer["give"] = {}
            offer["vassal"], offer["lord"] = mine.id, theirs.id
        if kind == "homage":
            # p asks o's group to swear to p's, paying what p asks (get) each season
            mine, theirs = self.group_of(p, None, lead=True), self.group_of(o, None, lead=True)
            if not mine or not theirs:
                return "homage is asked between the leaders of two groups"
            if mine.id == theirs.id or self.liege_chain(mine, theirs.id):
                return "a group cannot ask homage of itself or of one it is sworn to"
            offer["tribute"] = goods(a.get("get")) or goods(a.get("tribute"))
            offer["get"] = {}
            offer["vassal"], offer["lord"] = theirs.id, mine.id
        for k, n in offer["give"].items():
            if p.inv.get(k, 0) < n:
                return f"you do not have {n} {I.pretty(k)} to give"
        if offer["teach"] and p.skill(offer["teach"]) < 0.3:
            return f"you are not able enough at {offer['teach'].replace('_', ' ')} to teach it"
        if offer["learn"] and o.skill(offer["learn"]) < 0.3:
            return f"{o.name} is not able enough at {offer['learn'].replace('_', ' ')} to teach it"
        # an old offer between the two is replaced
        for oid in [i for i, x in w.offers.items() if x["from"] == p.id and x["to"] == o.id]:
            del w.offers[oid]
        w.offers[offer["id"]] = offer
        self.tell(o, f"{p.name} offers you: {self.offer_text(offer, o)} (offer {offer['id']}; accept or refuse).")
        self.wake(o, f"{p.name} made you an offer")
        self.event("offer", f"{p.name} offered {o.name}: {self.offer_text(offer, None)}", p, o, offer=offer["id"])
        return self.set(p, "wait", left=1)

    def offer_text(self, x, viewer):
        w = self.w
        a, b = w.people.get(x["from"]), w.people.get(x["to"])
        you = lambda q: "you" if q and viewer and q.id == viewer.id else (q.name if q else "someone")
        if x["kind"] == "child":
            return f"{you(a)} and {you(b)} to have a child together" + (f", named {x['name']}" if x["name"] else "")
        if x["kind"] in ("fealty", "homage"):
            vas, lord = w.groups.get(x.get("vassal")), w.groups.get(x.get("lord"))
            return (f"{vas.name if vas else 'a group'} to swear fealty to {lord.name if lord else 'a group'}, paying "
                    f"{goods_text(x.get('tribute') or {})} each autumn, for their protection" + (f" ({x['text']})" if x.get("text") else ""))
        if x["kind"] == "pledge":
            return f"{you(a)} and {you(b)} to pledge {'yourselves' if viewer else 'themselves'} as partners for life"
        bits = []
        if x["give"]:
            bits.append(f"{you(a)} give{'s' if you(a) != 'you' else ''} {goods_text(x['give'])} now")
        if x["get"]:
            bits.append(f"{you(b)} give{'s' if you(b) != 'you' else ''} {goods_text(x['get'])} now")
        if x["promise_give"]:
            bits.append(f"{you(a)} will give {goods_text(x['promise_give'])} within {x['due']} days")
        if x["promise_get"]:
            bits.append(f"{you(b)} will give {goods_text(x['promise_get'])} within {x['due']} days")
        if x["hire_days"]:
            bits.append(f"{you(b)} work{'s' if you(b) != 'you' else ''} for {you(a)} for {x['hire_days']} days")
        if x["serve_days"]:
            bits.append(f"{you(a)} work{'s' if you(a) != 'you' else ''} for {you(b)} for {x['serve_days']} days")
        if x.get("teach"):
            bits.append(f"{you(a)} teach{'es' if you(a) != 'you' else ''} {you(b)} {x['teach'].replace('_', ' ')}")
        if x.get("learn"):
            bits.append(f"{you(b)} teach{'es' if you(b) != 'you' else ''} {you(a)} {x['learn'].replace('_', ' ')}")
        if x["text"]:
            bits.append(f'"{x["text"]}"')
        return "; ".join(bits) or "nothing in particular"

    def start_accept(self, p, a):
        w = self.w
        x = w.offers.get(num(a.get("offer") or a.get("id") or a.get("choice"), 0, 0, 10 ** 9))
        if not x or x["to"] != p.id:
            # the number misremembered: the offer from the one named, or the only one there is
            mine = sorted((x for x in w.offers.values() if x["to"] == p.id), key=lambda x: -x["tick"])
            o = w.by_name(a.get("to") or a.get("from") or a.get("target") or a.get("choice") or "")
            x = next((x for x in mine if o and x["from"] == o.id), None) or (mine[0] if len(mine) == 1 else None)
        if not x:
            return "there is no such offer to you (offers lapse after two days, and a new one from the same person replaces the old)"
        o = w.people.get(x["from"])
        if not o or not o.alive:
            del w.offers[x["id"]]
            return "the one who offered is gone"
        if dist(p.x, p.y, o.x, o.y) > 20:
            return f"{o.name} is too far away now"
        if (x["give"] or x["get"] or x["kind"] == "child" or dist(p.x, p.y, o.x, o.y) > 6) and dist(p.x, p.y, o.x, o.y) > 1:
            # goods change hands face to face; one who has walked on is followed to answer (c52)
            return self.set_kw(p, {"do": "accept", "offer": x["id"], "to": o.id})
        return self.close_offer(p, x)

    def do_accept(self, p, a):
        w = self.w
        x = w.offers.get(a["offer"])
        o = w.people.get(a["to"])
        if not x or not o or not o.alive:
            return "fail", "The offer is gone."
        c = self.chase(p, a, o)
        if c:
            return "go", ""
        if c is None or dist(p.x, p.y, o.x, o.y) > 1:
            return "fail", f"You could not reach {o.name}."
        res = self.close_offer(p, x)
        return ("fail", res) if isinstance(res, str) else ("done", "")

    def close_offer(self, p, x):
        w = self.w
        o = w.people[x["from"]]
        for k, n in x["give"].items():
            if o.inv.get(k, 0) < n:
                return f"{o.name} no longer has {n} {I.pretty(k)}"
        for k, n in x["get"].items():
            if p.inv.get(k, 0) < n:
                return f"you do not have {n} {I.pretty(k)}"
        del w.offers[x["id"]]
        for k, n in x["give"].items():
            I.remove(o.inv, k, n)
            I.add(p.inv, k, n)
        for k, n in x["get"].items():
            I.remove(p.inv, k, n)
            I.add(o.inv, k, n)
        due = w.tick + x["due"] * TPD
        for giver, taker, g in ((o, p, x["promise_give"]), (p, o, x["promise_get"])):
            if g:
                w.promises.append({"by": giver.id, "to": taker.id, "goods": g, "due": due, "done": False, "made": w.tick})
        if x["hire_days"]:
            self.begin_service(o, p, x["hire_days"], x["text"])
        if x["serve_days"]:
            self.begin_service(p, o, x["serve_days"], x["text"])
        # the teacher's next step is the lesson (o offered to teach p, or p agreed to teach o)
        for teacher, learner, craft in ((o, p, x.get("teach")), (p, o, x.get("learn"))):
            if craft and teacher.skill(craft) >= 0.3:
                teacher.intent = teacher.intent or {"goal": "", "plan": []}
                teacher.intent["plan"].insert(0, {"do": "teach", "to": learner.name, "craft": craft})
                if teacher is o and teacher.act and teacher.act.get("do") != "teach":
                    teacher.act = None                  # the lesson comes first; what one was doing can wait
        if x["kind"] == "pledge":
            p.partner, o.partner = o.id, p.id
            self.event("pledge", f"{o.name} and {p.name} pledged themselves as partners", o, p)
        if x["kind"] in ("fealty", "homage"):
            vas, lord = w.groups.get(x["vassal"]), w.groups.get(x["lord"])
            if not vas or not lord or vas.dissolved is not None or lord.dissolved is not None:
                return "one of the groups is no more"
            vas.parent, vas.tribute = lord.id, dict(x.get("tribute") or {})
            self.event("fealty", f"{vas.name} swore fealty to {lord.name}" + (f", {goods_text(vas.tribute)} a season" if vas.tribute else ""),
                       w.people.get(vas.leader), w.people.get(lord.leader), vassal=vas.id, lord=lord.id)
            for m in vas.members:
                q = w.people.get(m)
                if q and q.alive:
                    self.tell(q, f"Your people, {vas.name}, are now sworn to {lord.name}.")
        if x["kind"] == "child":
            carrier = p if w.rng.random() < 0.5 else o
            if carrier.pregnant or min(p.satiety, o.satiety) < 10:
                return "you are not both well enough fed and free for a child now"
            carrier.pregnant = {"due": w.tick + 24, "with": (o if carrier is p else p).id, "name": x["name"]}
            self.event("conceive", f"{o.name} and {p.name} are expecting a child", o, p)
        self.trust(p, o, 0.1, ("deal", f"made a deal with {o.name}"))
        self.trust(o, p, 0.1, ("deal", f"made a deal with {p.name}"))
        self.tell(o, f"{p.name} accepted your offer.")
        self.wake(o, f"{p.name} accepted your offer")
        self.note_price(p.x, p.y, x["give"], x["get"], (p, o))
        self.event("deal", f"{p.name} accepted {o.name}'s offer: {self.offer_text(x, None)}", p, o, give=x["give"], get=x["get"])
        return self.set(p, "wait", left=1)

    def start_refuse(self, p, a):
        w = self.w
        x = w.offers.get(num(a.get("offer") or a.get("id"), 0, 0, 10 ** 9))
        if not x or x["to"] != p.id:
            o = w.by_name(a.get("to") or a.get("from") or a.get("target") or "")
            x = next((x for x in w.offers.values() if x["to"] == p.id and o and x["from"] == o.id), None)
        if not x:
            return self.set(p, "wait", left=1)      # nothing to refuse (it lapsed): no harm done
        w.offers.pop(x["id"], None)
        o = w.people.get(x["from"])
        if o:
            self.tell(o, f"{p.name} refused your offer.")
            self.wake(o, f"{p.name} refused your offer")
        return self.set(p, "wait", left=1)

    # ================= service =================
    def begin_service(self, master, servant, days, terms=""):
        w = self.w
        w.services.append({"master": master.id, "servant": servant.id, "end": w.tick + days * TPD, "done": False,
                           "terms": terms, "log": {}})
        self.event("hire", f"{servant.name} went into {master.name}'s service for {days} days", master, servant)

    # ================= posted trades =================
    def start_post(self, p, a):
        b = self.target_building(p, a, lambda b: b.owner == p.id and "store" in BUILDINGS[b.kind]["roles"])
        if not b:
            return "post a trade at a store of yours (x,y)"
        give, get = goods(a.get("give")), goods(a.get("get"))
        if (give or get) and not (give and get):
            return "a trade needs both what the store gives and what it takes"
        if dist(p.x, p.y, b.x, b.y) > 1:
            # walk there, then post it
            act = {"do": "post", "bid": b.id, "give": give, "get": get}
            if not self.walk(p, act, b.x, b.y, True):
                return "there is no way to that store"
            p.act = act
            return True
        self.post_at(p, b, give, get)
        return self.set(p, "wait", left=1)

    def do_post(self, p, a):
        wk = self.walking(p, a)
        if wk:
            return ("fail", "The way was blocked.") if wk == "fail" else ("go", "")
        b = self.w.buildings.get(a["bid"])
        if not b or b.owner != p.id:
            return "fail", "The store is no longer yours."
        self.post_at(p, b, a["give"], a["get"])
        return "done", "You posted the trade."

    def post_at(self, p, b, give, get):
        if not give and not get:
            b.trade = []
            return
        b.trade = ([t for t in b.trade if t["give"] != give] + [{"give": give, "get": get}])[-4:]   # one price for a thing
        self.event("post", f"{p.name} posted a trade at their {b.kind}: {goods_text(give)} for {goods_text(get)}", p)

    def start_trade(self, p, a):
        w = self.w
        item = norm(a.get("item"))
        b = self.target_building(p, a, lambda b: b.trade and (not item or any(item in t["give"] for t in b.trade)))
        if not b:
            return "you know of no posted trade" + (f" for {item}" if item else "")
        act = {"do": "trade", "bid": b.id, "item": item, "n": num(a.get("n"), 1, 1, 50)}
        if dist(p.x, p.y, b.x, b.y) > 1 and not self.market_reach(p, b) and not self.walk(p, act, b.x, b.y, True):
            return "there is no way there"
        p.act = act
        return True

    def market_reach(self, p, b):
        """A store within 2 steps of a market is traded with from anywhere at that market."""
        w = self.w
        for m in w.buildings.values():
            if m.done and "market" in BUILDINGS[m.kind]["roles"] and dist(m.x, m.y, b.x, b.y) <= 2 and dist(p.x, p.y, m.x, m.y) <= 2:
                return True
        return False

    def do_trade(self, p, a):
        w = self.w
        wk = self.walking(p, a) if not a.get("at_market") else False
        if wk:
            return ("fail", "The way was blocked.") if wk == "fail" else ("go", "")
        b = w.buildings.get(a["bid"])
        if not b or not b.trade:
            return "fail", "There is no trade there now."
        t = next((t for t in b.trade if not a["item"] or a["item"] in t["give"]), b.trade[0])
        done = 0
        for _ in range(a["n"]):
            if not all(p.inv.get(k, 0) >= n for k, n in t["get"].items()):
                break
            if not all(b.inv.get(k, 0) >= n for k, n in t["give"].items()):
                break
            for k, n in t["get"].items():
                I.remove(p.inv, k, n)
                I.add(b.inv, k, n)
            for k, n in t["give"].items():
                I.remove(b.inv, k, n)
                I.add(p.inv, k, n)
            done += 1
        if not done:
            return "done", f"The trade could not be made (it takes {goods_text(t['get'])}; the store must have {goods_text(t['give'])})."
        o = w.people.get(b.owner)
        self.note_price(b.x, b.y, t["give"], t["get"], (p, o))
        if o:
            self.tell(o, f"{p.name} traded at your {b.kind} {done} time{'s' if done > 1 else ''}.")
            self.trust(o, p, 0.02, ("traded_in", f"{p.name} traded at your {b.kind}"))
        self.event("trade", f"{p.name} traded {done}x at {o.name if o else 'a'}'s {b.kind}: {goods_text(t['get'])} for {goods_text(t['give'])}", p, o, times=done,
                   give={k: n * done for k, n in t["give"].items()}, get={k: n * done for k, n in t["get"].items()})
        return "done", f"You traded {done} time{'s' if done > 1 else ''}: {goods_text(t['get'])} for {goods_text(t['give'])} each."

    def start_set_access(self, p, a):
        w = self.w
        b = self.target_building(p, a, lambda b: b.owner == p.id or (b.owner < 0 and w.groups.get(-b.owner) and w.groups[-b.owner].leader == p.id))
        if not b:
            return "you own nothing there"
        who = str(a.get("who") or a.get("text") or "").strip()
        low = who.lower()
        if low in ("me", "owner", "only me", "nobody"):
            b.access, b.allow = "owner", []
        elif low in ("anyone", "everyone", "all", "open"):
            b.access = "anyone"
        else:
            g = next((g for g in w.groups.values() if g.name.lower() == low and g.dissolved is None), None)
            if g:
                b.access = f"group:{g.id}"
            else:
                names = [w.by_name(n.strip()) for n in who.split(",")]
                b.access, b.allow = "list", [x.id for x in names if x]
        return self.set(p, "wait", left=1)

    # ================= prices (grand world, Phase 3) =================
    MONEY = ("grain", "coin")

    def place_name(self, x, y):
        """What people call where (x, y) is: a named place within 10 steps, else the region, else its x,y."""
        w = self.w
        near = min((pl for pl in w.places if dist(x, y, pl[0], pl[1]) <= 10), key=lambda pl: dist(x, y, pl[0], pl[1]), default=None)
        if near:
            return near[2]
        r = w.region_at(x, y)
        return r.get("name") if r and r.get("name") else f"({x},{y})"

    def note_price(self, x, y, give, get, who=()):
        """A trade of one kind of thing for grain or coin fixes a price there (grain a unit), remembered by those who
        made it and those who saw it (c70)."""
        w = self.w
        if len(give) != 1 or len(get) != 1:
            return
        (a, na), (b, nb) = next(iter(give.items())), next(iter(get.items()))
        if a in self.MONEY and b not in self.MONEY:
            item, per = b, na / max(1, nb)
        elif b in self.MONEY and a not in self.MONEY:
            item, per = a, nb / max(1, na)
        else:
            return
        per *= 2 if (a == "coin" or b == "coin") else 1          # a coin is worth about two grain
        place = self.place_name(x, y)
        w.prices.setdefault(place, {})[item] = [round(per, 2), w.tick]
        seen = {o.id: o for o in w.near(x, y, 5)}
        for o in list(who) + list(seen.values()):
            if o and o.alive:
                o.known[f"price:{item}@{place.replace(',', ' ')}"] = ["price", item, w.tick, round(per, 2), place]   # no comma: not a tile

    # ================= orders (grand world, Phase 1.4: the first lords) =================
    ORDERABLE = ("gather", "hunt", "fish", "craft", "build", "mend", "plant", "put", "take", "go", "follow", "fuel")
    MAKES = ("gather", "hunt", "fish", "craft")

    def liege_chain(self, g, target):
        """Whether group g is sworn, directly or through others, to the group with id target."""
        seen = set()
        while g and g.parent and g.parent not in seen:
            if g.parent == target:
                return True
            seen.add(g.parent)
            g = self.w.groups.get(g.parent)
        return False

    def sworn_to(self, g):
        """The living groups sworn to g, directly or through others (c71)."""
        out, todo = [], [g.id]
        while todo:
            gid = todo.pop()
            for h in self.w.groups.values():
                if h.parent == gid and h.dissolved is None and h not in out:
                    out.append(h)
                    todo.append(h.id)
        return out

    def followers(self, p):
        """Who p may order: the members of the groups p leads and of the groups sworn to them (c71), and those in p's
        service."""
        w = self.w
        out = {}
        for gid in p.groups:
            g = w.groups.get(gid)
            if g and g.dissolved is None and g.leader == p.id:
                for m in g.members:
                    out[m] = "member"
                for h in self.sworn_to(g):
                    for m in h.members:
                        out.setdefault(m, "sworn")
        for sv in w.services:
            if not sv["done"] and sv["master"] == p.id:
                out[sv["servant"]] = "servant"
        out.pop(p.id, None)
        return {pid: why for pid, why in out.items() if w.people.get(pid) and w.people[pid].alive}

    def order_task(self, a, p=None):
        """The task an order names: {"task": {step}} or {"task": "gather", "item": ...} (the step's own fields; the verb
        may come as value, action or what, as the people write it). An order naming only a place is read from what
        stands there (world2, c72): a ripe field is reaped, a worn building mended, an unfinished one built, grain
        brought to a store; else they come there."""
        t = a.get("task") or a.get("step") or a.get("value") or a.get("action") or a.get("what")
        if isinstance(t, dict):
            step = dict(t)
        else:
            step = {k: v for k, v in a.items() if k not in ("do", "to", "who", "task", "step", "days", "value", "action", "what")}
            step["do"] = str(t or "").strip().lower()
        step["do"] = str(step.get("do", "")).strip().lower()
        if not step["do"] and step.get("x") is not None and step.get("y") is not None:
            w = self.w
            try:
                b = w.building_at(int(step["x"]), int(step["y"]))
            except (TypeError, ValueError):
                b = None
            roles = BUILDINGS[b.kind]["roles"] if b else {}
            if b and b.done and "farm" in roles and b.crop and b.crop.get("ripe") and b.inv:
                step.update(do="gather", item=b.crop["what"])
            elif b and b.done and b.hp <= BUILDINGS[b.kind]["hp"] * 0.5:
                step["do"] = "mend"
            elif b and not b.done:
                step.update(do="build", kind=b.kind)
            elif b and "store" in roles:
                step.update(do="put", item=step.get("item") or "grain")
            else:
                step["do"] = "go"
        return step

    def task_text(self, step):
        bits = [step["do"]] + [str(step[k]) for k in ("item", "kind", "animal", "n") if step.get(k)]
        if step.get("x") is not None and step.get("y") is not None:
            bits.append(f"at ({step['x']},{step['y']})")
        if step.get("to"):
            bits.append(str(step["to"]))
        return " ".join(bits)

    def obeys(self, o, p, why):
        """Whether a bot does as it is told: by its trust in the one ordering, what it owes them (a member, more
        a servant, less one whose group is sworn to them), kinship, hunger and its own ambition."""
        r = o.rel.get(str(p.id), {})
        score = r.get("trust", 0) + {"servant": 0.6, "member": 0.4}.get(why, 0.25) + (0.2 if r.get("kin") else 0) \
            - (0.3 if o.satiety <= 6 else 0) - 0.2 * o.traits.get("ambition", 0.5)
        return score + 0.2 * self.w.rng.random() >= 0.35

    def ordered_plan(self, p, o, step):
        """The order as the follower's plan: what they gather or make is brought to p's store; what they build is p's."""
        w = self.w
        step = dict(step)
        step["for"] = p.id
        if step["do"] == "gather" and step.get("item") in ("grain", "flax") and step.get("x") is None:
            # reaping for one: one's own ripe field, the nearest
            field = min((b for b in w.owned(p.id) if b.done and b.inv.get(step["item"]) and "farm" in BUILDINGS[b.kind]["roles"]),
                        key=lambda b: dist(p.x, p.y, b.x, b.y), default=None)
            if field:
                step["x"], step["y"] = field.x, field.y
        plan = [step]
        item = step.get("item") or step.get("animal")
        if step["do"] in self.MAKES and item:
            store = next((b for b in w.owned(p.id) if b.done and "store" in BUILDINGS[b.kind]["roles"]), None)
            if store:
                plan.append({"do": "put", "item": "meat" if step["do"] == "hunt" else "fish" if step["do"] == "fish" else item,
                             "x": store.x, "y": store.y, "for": p.id})
        return plan

    def start_order(self, p, a):
        """Tell one of one's people, or all of them near ("all"), to do a task for one; bots obey as they trust and
        owe one, the others choose. What they gather or make is brought to one's store."""
        w = self.w
        mine = self.followers(p)
        if not mine:
            return "you have no one to order: lead a group, or take someone into your service"
        step = self.order_task(a, p)
        if step["do"] not in self.ORDERABLE:
            return "order them to do what? (" + ", ".join(self.ORDERABLE) + ")"
        who = str(a.get("to") or a.get("who") or "all").strip()
        if who.lower() in ("all", "everyone", "everybody", "my people", "us"):
            targets = [w.people[i] for i in mine]
        else:
            o = w.by_name(who)
            if not o or o.id not in mine:
                return f"{who} is not one of your people (" + ", ".join(w.people[i].name for i in list(mine)[:8]) + ")"
            targets = [o]
        near = [o for o in targets if dist(p.x, p.y, o.x, o.y) <= 20 and not (o.adult(w.tick) is False and o.age(w.tick) < 8)]
        if not near:
            return "none of them is near enough to hear you (20 steps)"
        days = num(a.get("days"), 1, 1, 10)
        text = self.task_text(step)
        did, would_not, asked = [], [], []
        for o in near:
            if o.mind == "llm":
                self.tell(o, f"{p.name} orders you to {text}, for them, for {days} day{'s' if days > 1 else ''}.")
                self.wake(o, f"{p.name} ordered you to {text}")
                asked.append(o)
                continue
            if self.obeys(o, p, mine[o.id]):
                o.intent = {"goal": f"{p.name}'s order: {text}", "plan": self.ordered_plan(p, o, step), "routine": True,
                            "orig": self.ordered_plan(p, o, step), "since": w.tick, "until": w.tick + days * TPD,
                            "order": p.id}
                o.act = None
                self.trust(p, o, 0.03)
                did.append(o)
            else:
                self.trust(p, o, -0.1, ("refused_order", f"{o.name} would not do as you told them"))
                would_not.append(o)
        bits = []
        if did:
            bits.append(", ".join(o.name for o in did) + " set to it")
        if would_not:
            bits.append(", ".join(o.name for o in would_not) + " would not")
        if asked:
            bits.append(", ".join(o.name for o in asked) + " heard you")
        self.tell(p, f"You ordered {text}: " + "; ".join(bits) + ".")
        self.event("order", f"{p.name} ordered {text}: " + "; ".join(bits), p, *did, task=text,
                   obeyed=len(did), refused=len(would_not), asked=len(asked), mind=p.mind)
        return self.set(p, "wait", left=1)

    def start_renounce(self, p, a):
        """A leader takes their group out of its fealty (c71); tribute is owed no more, and the lord remembers."""
        w = self.w
        g = self.group_of(p, a.get("group"), lead=True)
        if not g or not g.parent:
            return "you lead no group sworn to another"
        lord = w.groups.get(g.parent)
        g.parent, g.tribute = None, {}
        ll = w.people.get(lord.leader) if lord else None
        if ll and ll.alive:
            self.trust(ll, p, -0.4, ("renounced", f"{p.name} took {g.name} out of fealty to you"))
            self.tell(ll, f"{p.name} has renounced {g.name}'s fealty to {lord.name}.")
            self.wake(ll, f"{p.name} renounced their fealty")
        self.event("renounce", f"{g.name} renounced its fealty to {lord.name if lord else 'its lord'}", p, ll)
        return self.set(p, "wait", left=1)

    def tribute_season(self):
        """Each season sworn groups pay their lords (c71): from the treasury, else the leader's store, else what the
        leader carries, into the lord's treasury or store. A shortfall is a broken promise, and both know it."""
        w = self.w
        for g in list(w.groups.values()):
            if g.dissolved is not None or not g.parent or not g.tribute:
                continue
            lord = w.groups.get(g.parent)
            if not lord or lord.dissolved is not None:
                g.parent, g.tribute = None, {}
                continue
            vl, ll = w.people.get(g.leader), w.people.get(lord.leader)
            if not vl or not ll or not vl.alive or not ll.alive:
                continue
            src = [w.buildings[g.treasury]] if g.treasury in w.buildings else []
            src += [b for b in w.owned(vl.id) if b.done and "store" in BUILDINGS[b.kind]["roles"]]
            dst = w.buildings.get(lord.treasury) or next((b for b in w.owned(ll.id) if b.done and "store" in BUILDINGS[b.kind]["roles"]), None)
            have = lambda k: sum(b.inv.get(k, 0) for b in src) + vl.inv.get(k, 0)
            due = dict(g.tribute)
            if dst is not None and not all(have(k) >= n for k, n in due.items()):
                # short in kind: made up in other food of the same worth, if there is enough (c72)
                worth = sum(I.info(k).get("food", 0) * n or I.info(k).get("worth", 1) * n for k, n in due.items())
                foods = sorted({k for b in src for k in b.inv if I.info(k).get("food") and ":" not in k} |
                               {k for k in vl.inv if I.info(k).get("food")}, key=lambda k: -I.info(k)["food"])
                sub, left = {}, worth
                for k in foods:
                    if left <= 0:
                        break
                    n = min(have(k), -(-left // I.info(k)["food"]))
                    if n > 0:
                        sub[k], left = int(n), left - n * I.info(k)["food"]
                if left <= 0:
                    due = sub
            if dst is None or not all(have(k) >= n for k, n in due.items()):
                self.trust(ll, vl, -0.2, ("tribute_unpaid", f"{g.name} did not pay you its tribute"))
                self.tell(ll, f"{g.name} has not paid the tribute it owes you ({goods_text(g.tribute)}).")
                self.tell(vl, f"{g.name} could not pay its tribute to {lord.name} ({goods_text(g.tribute)}).")
                self.wake(ll, f"{g.name} has not paid you tribute")
                self.event("tribute_unpaid", f"{g.name} did not pay {lord.name} its tribute", vl, ll)
                continue
            for k, n in due.items():
                left = n
                for b in src:
                    left -= I.remove(b.inv, k, left)
                left -= I.remove(vl.inv, k, left)
                I.add(dst.inv, k, n)
            self.trust(ll, vl, 0.05)
            self.tell(ll, f"{g.name} paid you its tribute: {goods_text(due)}, into your {dst.kind}.")
            self.event("tribute", f"{g.name} paid {lord.name} {goods_text(due)}", vl, ll, goods=due)

    # ================= groups =================
    def start_found_group(self, p, a):
        w = self.w
        name = " ".join(str(a.get("name") or "").split())[:40]
        if len(name) < 2:
            return "a group needs a name"
        if any(g.name.lower() == name.lower() and g.dissolved is None for g in w.groups.values()):
            return "there is already a group of that name"
        g = Group(id=w.new_id(), name=name, founder=p.id, leader=p.id, members=[p.id], rules=str(a.get("rules") or "")[:400],
                  decide="vote" if "vote" in str(a.get("decide", "")).lower() else "leader", founded=w.tick)
        w.groups[g.id] = g
        p.groups.append(g.id)
        self.event("group", f"{p.name} founded {name}", p, group=g.id)
        return self.set(p, "wait", left=1)

    def group_of(self, p, name, lead=False):
        for gid in p.groups:
            g = self.w.groups.get(gid)
            if g and g.dissolved is None and (not name or g.name.lower() == str(name).lower()):
                if not lead or g.leader == p.id:
                    return g
        return None

    def start_invite(self, p, a):
        g = self.group_of(p, a.get("group"))
        o = self.w.by_name(a.get("to") or a.get("target"))
        if not g or not o:
            return "invite whom, into which of your groups?"
        if o.id not in g.invited:
            g.invited.append(o.id)
        self.tell(o, f"{p.name} invites you to join {g.name}. Its rules: \"{g.rules}\"")
        self.wake(o, f"{p.name} invited you into {g.name}")
        return self.set(p, "wait", left=1)

    def start_join(self, p, a):
        w = self.w
        g = next((g for g in w.groups.values() if g.name.lower() == str(a.get("group", "")).lower() and g.dissolved is None), None)
        if not g or not (p.id in g.invited or g.join == "open"):
            return "you have not been invited into that group"
        if p.id not in g.members:
            g.members.append(p.id)
            p.groups.append(g.id)
        g.invited = [x for x in g.invited if x != p.id]
        for m in g.members:
            if m != p.id and w.people.get(m):
                self.tell(w.people[m], f"{p.name} joined {g.name}.")
        self.event("join", f"{p.name} joined {g.name}", p, group=g.id)
        return self.set(p, "wait", left=1)

    def start_leave(self, p, a):
        g = self.group_of(p, a.get("group"))
        if not g:
            svc = next((s for s in self.w.services if not s["done"] and s["servant"] == p.id), None)
            if svc:
                svc["done"] = True
                m = self.w.people.get(svc["master"])
                if m:
                    self.trust(m, p, -0.3, ("left_service", f"{p.name} left your service early"))
                    self.tell(m, f"{p.name} left your service early.")
                return self.set(p, "wait", left=1)
            return "leave what?"
        self.remove_member(g, p, f"{p.name} left {g.name}.")
        return self.set(p, "wait", left=1)

    def remove_member(self, g, p, text):
        w = self.w
        g.members = [m for m in g.members if m != p.id]
        p.groups = [x for x in p.groups if x != g.id]
        for m in g.members:
            if w.people.get(m):
                self.tell(w.people[m], text)
        if g.leader == p.id and g.members:
            g.leader = g.members[0]
        if not g.members:
            g.dissolved = w.tick

    def start_expel(self, p, a):
        g = self.group_of(p, a.get("group"), lead=True)
        o = self.w.by_name(a.get("to") or a.get("target"))
        if not g or not o or o.id not in g.members:
            return "only a group's leader can put someone out of it"
        if g.decide == "vote":
            return "in this group that is voted on (call_vote)"
        self.remove_member(g, o, f"{o.name} was put out of {g.name} by {p.name}.")
        self.trust(o, p, -0.3, ("expelled", f"{p.name} put you out of {g.name}"))
        return self.set(p, "wait", left=1)

    def start_call_vote(self, p, a):
        w = self.w
        g = self.group_of(p, a.get("group"))
        if not g:
            return "call a vote in which of your groups?"
        v = {"id": w.new_id(), "group": g.id, "by": p.id, "question": str(a.get("text") or "")[:240],
             "act": str(a.get("act") or "").lower(), "target": a.get("to") or a.get("target"), "value": a.get("value"),
             "yes": [p.id], "no": [], "ends": w.tick + TPD, "done": False}
        w.votes[v["id"]] = v
        for m in g.members:
            o = w.people.get(m)
            if o and o.id != p.id:
                self.tell(o, f"{p.name} calls a vote in {g.name} (vote {v['id']}): \"{v['question']}\"")
                self.wake(o, "a vote was called")
        return self.set(p, "wait", left=1)

    def start_vote(self, p, a):
        v = self.w.votes.get(num(a.get("vote") or a.get("id"), 0, 0, 10 ** 9))
        if not v or v["done"] or p.id not in self.w.groups[v["group"]].members:
            return "there is no such vote open to you"
        yes = str(a.get("choice") or a.get("value") or "").lower() in ("yes", "y", "true", "aye")
        for side in ("yes", "no"):
            if p.id in v[side]:
                v[side].remove(p.id)
        v["yes" if yes else "no"].append(p.id)
        return self.set(p, "wait", left=1)

    def start_set_dues(self, p, a):
        """A leader sets what each member brings each season (give), into a treasury: a store of the
        leader's own, named by its place, that becomes the group's (its members may use it)."""
        w = self.w
        g = self.group_of(p, a.get("group"), lead=True)
        if not g:
            return "only a group's leader can set its dues (or call a vote, act: dues)"
        why = self.found_treasury(p, g, a)
        if why:
            return why
        g.dues = goods(a.get("give") or a.get("get") or a.get("value"))
        msg = f"{g.name}'s dues are now {goods_text(g.dues)} each season, into its store at ({w.buildings[g.treasury].x},{w.buildings[g.treasury].y})."
        for m in g.members:
            o = w.people.get(m)
            if o:
                self.tell(o, msg)
        self.event("law", f"{p.name} set {g.name}'s dues: {goods_text(g.dues) or 'none'}", p, group=g.id)
        return self.set(p, "wait", left=1)

    def found_treasury(self, p, g, a):
        w = self.w
        if g.treasury and w.buildings.get(g.treasury):
            return None
        b = self.target_building(p, a, lambda b: b.done and "store" in BUILDINGS[b.kind]["roles"] and b.owner == p.id)
        if not b:
            return "name a store of yours (x,y) to be the group's treasury"
        b.owner, b.access = -g.id, "members"
        g.treasury = b.id
        return None

    def start_make_law(self, p, a):
        """A leader (or a vote) sets a law for the group; written on a tablet (a tablet in hand and writing
        within reach), it lasts; otherwise it lives in its maker's word and dies with them."""
        w = self.w
        g = self.group_of(p, a.get("group"), lead=True)
        if not g:
            return "only a group's leader can make its law (or call a vote)"
        text = str(a.get("text") or "").strip()[:300]
        if not text:
            return "a law needs words"
        same = next((l for l in g.laws if l[1].strip().lower() == text.lower()), None)
        if same and (same[2] or not p.inv.get("tablet")):
            return f"that is already {g.name}'s law" + ("" if same[2] else " (a tablet in hand would write it down)")
        written = False
        if p.inv.get("tablet") and (p.skill("writing") >= 0.1 or not self.can_try(p, "writing")):
            I.remove(p.inv, "tablet", 1)
            written = True
        if same:
            g.laws.remove(same)                 # the law as it was spoken, now written down
        g.laws.append([w.tick, text, written, p.id])     # unwritten, it dies with its maker
        g.laws = g.laws[-8:]
        for m in g.members:
            o = w.people.get(m)
            if o and o.id != p.id:
                self.tell(o, f"{p.name} set a law for {g.name}: \"{text}\"" + (" (written down)" if written else ""))
        self.event("law", f"{p.name} set a law for {g.name}: \"{text}\"", p, group=g.id, written=written)
        if written:
            self.practise(p, "writing", 0.02)
        return self.set(p, "wait", left=1)

    # ================= writing =================
    def start_write(self, p, a):
        """Write words on a tablet (writing) or parchment with ink (literacy): a letter, a record, a deal.
        With a craft named and mastery of it, on parchment, it is a book that teaches the craft."""
        w = self.w
        text = str(a.get("text") or "").strip()[:400]
        craft = norm(a.get("craft")) if a.get("craft") else None
        if craft:
            if p.skill("literacy") < 0.4 or p.skill(craft) < 0.5:
                return "a book takes reading and writing and good skill in its craft"
            if not p.inv.get("book"):
                return "you need a blank book (bookmaking)"
            I.remove(p.inv, "book", 1)
            I.add(p.inv, "book:" + craft, 1)
            self.practise(p, "literacy", 0.03)
            self.event("book", f"{p.name} wrote a book on {craft.replace('_', ' ')}", p, craft=craft)
            return self.set(p, "wait", left=8)
        pr = None
        if a.get("promise"):
            # a promise written down (C2): it stands past its day, owed to whoever holds the writing
            o = w.by_name(a.get("promise"))
            pr = next((x for x in w.promises if o and not x["done"] and not x.get("deed")
                       and {x["by"], x["to"]} == {p.id, o.id}), None)
            if not pr:
                return f"there is no unwritten promise between you and {a.get('promise')}"
            if not text:
                text = f"{w.people[pr['by']].name} owes {goods_text(pr['goods'])} by day {pr['due'] // TPD + 1}"
        if not text:
            return "write what? (text)"
        if p.inv.get("parchment") and p.inv.get("ink") and p.skill("literacy") >= 0.2:
            on = "parchment"
            I.remove(p.inv, "ink", 1) if w.rng.random() < 0.2 else None
        elif p.inv.get("tablet") and (p.skill("writing") >= 0.1 or not self.can_try(p, "writing")):
            on = "tablet"                       # with pottery known, anyone may try: the first marks are practice
        elif (p.skill("writing") >= 0.1 or not self.can_try(p, "writing")) and not a.get("fetched"):
            # a tablet in one's own store near: fetch it, then write (W1.2)
            st = self.building_near(p, lambda b: b.done and b.inv.get("tablet") and b.owner in (p.id, p.partner), r=15)
            if st:
                if p.intent is not None:
                    p.intent.setdefault("plan", []).insert(0, dict(a, fetched=True))
                return self.start_take(p, {"item": "tablet", "n": 1, "x": st.x, "y": st.y})
            return ("you have no clay tablet to write on: craft tablet (pressed by hand from 2 clay; or 4 fired in a kiln "
                    "from clay 2 and wood 1, by a potter)")
        elif p.skill("writing") < 0.1:
            return f"you cannot write yet: writing {self.can_try(p, 'writing')} (then a clay tablet in hand)"
        else:
            return "writing needs a clay tablet and some skill at writing (or parchment, ink and reading)"
        I.remove(p.inv, on, 1)
        wid = w.new_id()
        w.writings[wid] = {"text": text, "by": p.id, "tick": w.tick, "on": on}
        # written for a store of one's own beside one (a tally): it goes straight in
        st = None
        if a.get("x") is not None and a.get("y") is not None:
            st = self.target_building(p, a, lambda b: b.done and "store" in BUILDINGS[b.kind]["roles"] and b.owner in (p.id, p.partner))
        to = w.people.get(pr["to"]) if pr else None
        if pr and to and to.id != p.id and dist(p.x, p.y, to.x, to.y) <= 1:
            I.add(to.inv, f"{on}:{wid}", 1)     # the one who promised writes it and hands it over
            self.tell(to, f"{p.name} wrote down their promise to you and gave you the {on} ({on}:{wid}).")
        elif st and dist(p.x, p.y, st.x, st.y) <= 1:
            I.add(st.inv, f"{on}:{wid}", 1)
        else:
            I.add(p.inv, f"{on}:{wid}", 1)
        if pr:
            pr["deed"] = f"{on}:{wid}"
            w.writings[wid]["promise"] = True
        self.practise(p, "writing" if on == "tablet" else "literacy", 0.03)
        if on == "tablet" and not self.can_try(p, "literacy") and p.skill("literacy") < 0.3:
            self.practise(p, "literacy", 0.04)          # a good writer comes to read and write at length (c61)
        self.event("write", f"{p.name} wrote: \"{text}\"", p, writing=wid, **({"promise": True} if pr else {}))
        return self.set(p, "wait", left=1)

    def bearer(self, deed):
        """Who holds a writing: in hand, or in a store of theirs (a group's store: its leader)."""
        w = self.w
        for q in w.living():
            if q.inv.get(deed):
                return q
        for b in w.buildings.values():
            if b.inv.get(deed):
                if b.owner and b.owner < 0:
                    g = w.groups.get(-b.owner)
                    q = w.people.get(g.leader) if g else None
                else:
                    q = w.people.get(b.owner)
                return q if q and q.alive else None
        return None

    def can_read(self, p, on):
        return p.skill("literacy" if on == "parchment" else "writing") >= 0.2 or p.skill("literacy") >= 0.2

    # ================= each hour =================
    def society_tick(self):
        w = self.w
        # offers not answered in two days lapse (people with much on their minds answer late)
        for oid in [i for i, x in w.offers.items() if w.tick - x["tick"] > 2 * TPD]:
            del w.offers[oid]
        # promises long settled are let go (the list only grew: a scan of it each hour for every bot, c57)
        if w.tick % TPD == 0 and len(w.promises) > 200:
            w.promises = [pr for pr in w.promises if not pr["done"] or w.tick - pr["due"] < 10 * TPD]
        # promises come due
        for pr in w.promises:
            if pr["done"]:
                continue
            if pr.get("deed"):
                # a written promise is owed to whoever holds the writing; back in the hands of the one who
                # made it, it is settled
                holder = self.bearer(pr["deed"])
                if holder and holder.id == pr["by"]:
                    pr["done"] = True
                    self.tell(holder, "The written promise you made is back in your hands: you owe nothing on it now.")
                    continue
                if holder and holder.id != pr["to"]:
                    pr["to"] = holder.id
            by, to = w.people.get(pr["by"]), w.people.get(pr["to"])
            if not by or not to or not by.alive or not to.alive:
                pr["done"] = True
                continue
            if pr["due"] - w.tick == TPD * 2:
                self.wake(by, f"your promise to {to.name} of {goods_text(pr['goods'])} comes due in two days")
            if all(by.inv.get(k, 0) >= n for k, n in pr["goods"].items()) and dist(by.x, by.y, to.x, to.y) <= 1:
                for k, n in pr["goods"].items():
                    I.remove(by.inv, k, n)
                    I.add(to.inv, k, n)
                pr["done"] = True
                self.trust(to, by, 0.2, ("kept", f"{by.name} kept a promise"))
                self.tell(to, f"{by.name} kept their promise: {goods_text(pr['goods'])}.")
                self.tell(by, f"You kept your promise to {to.name}.")
                self.event("promise_kept", f"{by.name} kept a promise to {to.name}", by, to)
            elif w.tick >= pr["due"]:
                written = pr.get("deed") and pr.get("late", 0) < 3
                if written:
                    # the writing outlasts the day: still owed, ten days on (three times at most)
                    pr["late"] = pr.get("late", 0) + 1
                    pr["due"] = w.tick + 10 * TPD
                else:
                    pr["done"] = True
                self.trust(to, by, -0.4, ("broke", f"{by.name} broke a promise of {goods_text(pr['goods'])}"))
                still = " It is written down: it still stands, ten days more." if written else ""
                self.tell(to, f"{by.name} broke their promise of {goods_text(pr['goods'])}.{still}")
                self.wake(to, f"{by.name} broke a promise")
                self.tell(by, f"You did not keep your promise to {to.name}.{still}")
                self.event("promise_broken", f"{by.name} broke a promise to {to.name}", by, to)
        # service ends
        for s in w.services:
            if not s["done"] and w.tick >= s["end"]:
                s["done"] = True
                m, sv = w.people.get(s["master"]), w.people.get(s["servant"])
                if m and sv:
                    self.trust(m, sv, 0.15, ("served", f"{sv.name} served you as agreed"))
                    self.tell(m, f"{sv.name}'s service to you is done.")
                    self.tell(sv, f"Your service to {m.name} is done.")
        # votes close
        for v in w.votes.values():
            if v["done"] or w.tick < v["ends"]:
                continue
            v["done"] = True
            g = w.groups.get(v["group"])
            if not g:
                continue
            passed = len(v["yes"]) > len(v["no"])
            if passed:
                t = w.by_name(v["target"]) if v["target"] else None
                if v["act"] == "expel" and t and t.id in g.members:
                    self.remove_member(g, t, f"{t.name} was voted out of {g.name}.")
                elif v["act"] == "leader" and t and t.id in g.members:
                    g.leader = t.id
                elif v["act"] == "rules" and v.get("value"):
                    g.rules = str(v["value"])[:400]
                elif v["act"] == "law" and v.get("value"):
                    g.laws.append([w.tick, str(v["value"])[:300], False])
                elif v["act"] == "dues" and g.treasury:
                    m = re.match(r"\s*(\d+)\s+(.+)", str(v.get("value") or ""))
                    if m:
                        g.dues = goods([{"item": m.group(2), "qty": int(m.group(1))}])
            for m in g.members:
                o = w.people.get(m)
                if o:
                    self.tell(o, f"The vote in {g.name} (\"{v['question']}\") {'passed' if passed else 'failed'}, {len(v['yes'])} to {len(v['no'])}.")
        # groups' dues come in at each season's start
        if w.hour() == 0 and w.day() % 10 == 0:
            for g in w.groups.values():
                tr = w.buildings.get(g.treasury) if g.treasury else None
                if g.dissolved is not None or not g.dues or not tr:
                    continue
                for m in g.members:
                    o = w.people.get(m)
                    if not o:
                        continue
                    if not o.alive or not o.adult(w.tick):
                        continue
                    # what one carries first, then one's own store
                    own = [b for b in w.buildings.values() if b.owner == o.id and b.done and "store" in BUILDINGS[b.kind]["roles"]]
                    if all(o.inv.get(k, 0) + sum(b.inv.get(k, 0) for b in own) >= n for k, n in g.dues.items()):
                        for k, n in g.dues.items():
                            left = n - I.remove(o.inv, k, n)
                            for b in own:
                                if left <= 0:
                                    break
                                left -= I.remove(b.inv, k, left)
                            I.add(tr.inv, k, n)
                        self.tell(o, f"You paid {goods_text(g.dues)} in dues to {g.name}.")
                    else:
                        self.tell(o, f"You could not pay {g.name}'s dues of {goods_text(g.dues)}.")
                        ld = w.people.get(g.leader)
                        if ld:
                            self.tell(ld, f"{o.name} did not pay the dues to {g.name}.")
