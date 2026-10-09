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
        for o in w.near(p.x, p.y, 4 if not w.is_night() else 2):
            if o.id != p.id:
                self.tell(o, f"{p.name}{' (to ' + target.name + ')' if target and target.id != o.id else ''}: \"{text}\"")
                heard.append(o)
                self.heard[o.id] = (self.heard.get(o.id, []) + [(w.tick, p.id, text, bool(target and target.id == o.id))])[-6:]
                if target and target.id == o.id and (wake or o.mind == "bot"):   # a bot's thinking costs nothing
                    self.wake(o, f"{p.name} spoke to you")
        self.event("say", f"{p.name}{' to ' + target.name if target else ''}: \"{text}\"", p, target, said=text)
        return heard

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
        self.event("deal", f"{p.name} accepted {o.name}'s offer: {self.offer_text(x, None)}", p, o)
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
        if o:
            self.tell(o, f"{p.name} traded at your {b.kind} {done} time{'s' if done > 1 else ''}.")
            self.trust(o, p, 0.02, ("traded_in", f"{p.name} traded at your {b.kind}"))
        self.event("trade", f"{p.name} traded {done}x at {o.name if o else 'a'}'s {b.kind}: {goods_text(t['get'])} for {goods_text(t['give'])}", p, o, times=done)
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
