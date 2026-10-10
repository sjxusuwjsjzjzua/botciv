"""Bands, raids and battles (grand world, docs/grand.md Phase 5): violence made collective, as history made it.

A leader musters their people (members, the sworn, servants) into a band; each comes or stays home as they owe and
trust the leader, and as bold or hungry as they are. The band goes where its leader goes. At a place where others
live, those who live there stand together, the more readily behind a wall; the fight is reckoned hour by hour as a
whole (numbers, arms, armour, skill, health), until one side breaks: raiders who win take what the stores there
hold and carry it home, raiders who lose flee. Everything is remembered by those it was done to and those who saw;
nothing decides that anyone should raid or how a raid should go but the people and the reckoning."""
from .content import BUILDINGS
from .content import items as I
from .world import dist, key, TPD


def power(q):
    """What one brings to a fight: body, arms, armour, skill, and how whole one is."""
    return (1 + q.strength + I.best(q.inv, "weapon")[0] + I.best(q.inv, "armour")[0] + 2 * q.skill("fight")) * max(0.2, q.health / 10)


class War:
    # ================= the band =================
    def band_of(self, p):
        for b in self.w.bands.values():
            if p.id == b["leader"] or p.id in b["members"]:
                return b
        return None

    def start_muster(self, p, a):
        """Call one's people to one: a band to raid or to defend. Bots come as they owe and trust one and as bold or
        hungry as they are; people with minds of their own are called and choose (join_band)."""
        w = self.w
        mine = self.followers(p)
        if not mine:
            return "you have no people to call: lead a group, or take people into your service"
        band = self.band_of(p)
        if band and band["leader"] != p.id:
            return "you are in another's band"
        if not band:
            band = {"id": w.new_id(), "leader": p.id, "members": [], "target": None, "home": [p.x, p.y], "state": "gathering",
                    "since": w.tick, "fought": 0, "start_power": 0}
            w.bands[band["id"]] = band
        came, stayed, called = [], [], []
        for pid, why in mine.items():
            o = w.people[pid]
            if not o.adult(w.tick) or pid in band["members"] or dist(p.x, p.y, o.x, o.y) > 25 or self.band_of(o):
                continue
            if o.mind == "llm":
                self.tell(o, f"{p.name} calls you to their band (join_band: {p.name}).")
                self.wake(o, f"{p.name} calls you to their band")
                called.append(o)
                continue
            r = o.rel.get(str(p.id), {})
            score = r.get("trust", 0) + {"servant": 0.5, "member": 0.35}.get(why, 0.2) + 0.4 * o.traits.get("boldness", 0.5) \
                + (0.2 if o.satiety <= 8 else 0) - (0.4 if o.health <= 5 else 0)
            if score + 0.2 * w.rng.random() >= 0.55:
                self.join(band, o)
                came.append(o)
            else:
                stayed.append(o)
                self.trust(p, o, -0.05)
        bits = ([", ".join(o.name for o in came) + " came"] if came else []) + ([", ".join(o.name for o in stayed) + " stayed home"] if stayed else []) \
            + ([", ".join(o.name for o in called) + " heard the call"] if called else [])
        self.tell(p, f"You called your people: " + ("; ".join(bits) or "no one was near") + f". Your band is {len(band['members']) + 1} strong.")
        self.event("muster", f"{p.name} mustered a band of {len(band['members']) + 1}", p, *came, size=len(band["members"]) + 1, mind=p.mind)
        return self.set(p, "wait", left=num_hours(a.get("hours")))

    def join(self, band, o):
        band["members"].append(o.id)
        lead = self.w.people[band["leader"]]
        o.intent = {"goal": f"in {lead.name}'s band", "plan": [], "routine": False, "since": self.w.tick, "band": band["id"]}
        o.act = {"do": "follow", "to": lead.id, "left": 24}

    def start_join_band(self, p, a):
        w = self.w
        lead = w.by_name(a.get("to") or a.get("leader"))
        band = self.band_of(lead) if lead else None
        if not band or band["leader"] != lead.id:
            return "there is no band of theirs to join"
        if dist(p.x, p.y, lead.x, lead.y) > 25:
            return f"{lead.name} is too far away"
        self.join(band, p)
        self.tell(lead, f"{p.name} joined your band.")
        return True

    def start_disband(self, p, a):
        band = self.band_of(p)
        if not band or band["leader"] != p.id:
            return "you lead no band"
        self.end_band(band, "disbanded")
        return self.set(p, "wait", left=1)

    def end_band(self, band, why):
        w = self.w
        for m in band["members"]:
            o = w.people.get(m)
            if o and o.alive and (o.intent or {}).get("band") == band["id"]:
                o.intent, o.act = None, None
                self.tell(o, f"The band went home ({why}).")
        w.bands.pop(band["id"], None)

    def start_raid(self, p, a):
        """Lead one's band to a place to take what is stored there (x,y)."""
        w = self.w
        band = self.band_of(p)
        if not band or band["leader"] != p.id:
            return "muster a band first"
        if not band["members"]:
            return "your band is only you: muster your people first"
        try:
            x, y = int(a.get("x")), int(a.get("y"))
        except (TypeError, ValueError):
            return "raid where? (x, y)"
        if not w.inb(x, y):
            return "raid where? (x, y)"
        band["target"], band["state"], band["home"] = [x, y], "marching", [p.x, p.y]
        band["take"] = bool(a.get("take") or a.get("captives"))
        band["share"] = share_of(a.get("share"))
        act = {"do": "go"}
        if not self.walk(p, act, x, y, True):
            return f"there is no way to ({x},{y})"
        p.act = act
        self.event("raid_out", f"{p.name} led a band of {len(band['members']) + 1} toward ({x},{y})", p, x=x, y=y, mind=p.mind)
        return True

    # ================= peace (c75) =================
    def chain(self, g):
        """A group and the lords above it."""
        out, seen = [], set()
        while g and g.id not in seen:
            out.append(g)
            seen.add(g.id)
            g = self.w.groups.get(g.parent) if g.parent else None
        return out

    def realms(self, p):
        """The groups p belongs to, with their lords."""
        w = self.w
        return [h for gid in p.groups if w.groups.get(gid) and w.groups[gid].dissolved is None for h in self.chain(w.groups[gid])]

    def peace_between(self, p, o):
        """The peace sworn between p's people (or their lords) and o's, if one holds: (theirs, ours) groups, or None."""
        theirs = {h.id: h for h in self.realms(o)}
        for h in self.realms(p):
            for k, until in h.peace.items():
                if until > self.w.tick and int(k) in theirs:
                    return h, theirs[int(k)]
        return None

    def same_realm(self, p, o):
        """Whether p and o answer, in the end, to the same lord."""
        top = lambda q: {self.chain(self.w.groups[gid])[-1].id for gid in q.groups if self.w.groups.get(gid) and self.w.groups[gid].dissolved is None}
        return bool(top(p) & top(o))

    def break_peace(self, lead, h, k, wronged):
        """A raid on those one is sworn to keep the peace with: the peace is ended, those wronged hate the oath-breaker,
        and even one's own people trust one less (c75)."""
        w = self.w
        h.peace.pop(str(k.id), None)
        k.peace.pop(str(h.id), None)
        for q in {q.id: q for q in wronged if q.id != lead.id}.values():
            self.trust(q, lead, -0.3, ("broke_peace", f"{lead.name} broke the peace between {h.name} and {k.name}"))
        for m in self.followers(lead):
            q = w.people.get(m)
            if q and q.alive:
                self.trust(q, lead, -0.1)
        self.event("broke_peace", f"{lead.name} broke the peace between {h.name} and {k.name}", lead, x=lead.x, y=lead.y)

    def weariness(self, band, won, fallen=()):
        """A band comes home: those who followed trust their leader more for spoils, less for a beating; the kin of
        the fallen blame the one who led them out (c75)."""
        w = self.w
        lead = w.people.get(band["leader"])
        if not lead or not lead.alive:
            return
        for m in band["members"]:
            q = w.people.get(m)
            if q and q.alive:
                # a win (c81): a little for the win itself, the rest as one keeps one's share at home (divide)
                self.trust(q, lead, (0.04 if band.get("share") != "each" or str(m) in band.get("spoils", {}) else 0.1)
                           if won else -0.12)
        for d in fallen:
            for k, r in d.rel.items():
                q = w.people.get(int(k))
                if r.get("kin") and q and q.alive and q.id != lead.id:
                    self.trust(q, lead, -0.3, ("lost_kin", f"{d.name} fell in {lead.name}'s raid"))

    # ================= the division of spoils (c81) =================
    def divide(self, band, lead):
        """Home again, the spoils are divided as the leader said when they led the band out: each keeps what they
        carried ("each"), or half ("half") or all ("mine") of it comes to the leader's store, or to the leader's own
        hands when the store is full. Those who followed trust the leader as they kept their share."""
        w = self.w
        keep = {"each": 1.0, "half": 0.5, "mine": 0.0}[band.get("share") or "each"]
        stores = [b for b in w.owned(lead.id) if b.done and "store" in BUILDINGS[b.kind]["roles"]
                  and dist(b.x, b.y, *band["home"]) <= 8]
        brought = {}
        for m, got in band.get("spoils", {}).items():
            q = w.people.get(int(m))
            if not q or not q.alive or int(m) not in band["members"]:
                continue
            gave = {}
            for k, n in got.items():
                n = min(q.inv.get(k, 0), int(round(n * (1 - keep))))
                for b in stores + [None]:           # the leader's stores, then the leader's own hands
                    if b:
                        free = BUILDINGS[b.kind]["roles"]["store"].get("capacity", 30) - I.weight(b.inv)
                        c = min(n, int(free / max(0.01, I.info(k)["w"])))
                    else:
                        c = min(n, max(0, int(self.room(lead, k))))
                    if c > 0:
                        I.remove(q.inv, k, c)
                        I.add(b.inv if b else lead.inv, k, c)
                        gave[k] = gave.get(k, 0) + c
                        n -= c
                    if n <= 0:
                        break                       # what finds no room the follower keeps
            kept = 1 - sum(gave.values()) / max(1, sum(got.values()))
            if kept < 0.25:
                self.trust(q, lead, 0.06 * kept - 0.06, ("took_spoils", f"{lead.name} took the spoils you carried home"))
            else:
                self.trust(q, lead, 0.06 * kept)
            for k, n in gave.items():
                brought[k] = brought.get(k, 0) + n
            if gave:
                self.tell(q, f"You gave {lead.name} " + ", ".join(f"{n} {I.pretty(k)}" for k, n in gave.items())
                          + " of what you carried home, as they said.")
        if band.get("spoils"):
            what = ", ".join(f"{n} {I.pretty(k)}" for k, n in sorted(brought.items(), key=lambda kv: -kv[1])[:5])
            self.tell(lead, f"Your band divided the spoils: " + (f"{what} came to you." if what else "each kept what they carried."))
            self.event("spoils", f"{lead.name}'s band divided the spoils" + (f": {what} to {lead.name}" if what else ", each keeping their own"),
                       lead, share=band.get("share") or "each", goods=brought, mind=lead.mind)

    # ================= captives and ransom (c76) =================
    def price_of(self, q):
        """What custom asks for one held: more for a leader, an heir, the able."""
        leads = any(self.w.groups.get(g) and self.w.groups[g].leader == q.id for g in q.groups)
        return {"grain": 30 if leads else 12 + 4 * int(q.skill("fight") > 0.3)}

    def seize(self, lead, beaten, n):
        """The winners of a raid carry off the weakest of those who stood against them, to be ransomed (§13: hostages
        and ransom only)."""
        w = self.w
        for q in sorted(beaten, key=lambda q: q.health)[:n]:
            q.held = {"by": lead.id, "since": w.tick, "price": self.price_of(q)}
            q.intent, q.act = {"goal": f"held by {lead.name}", "plan": []}, {"do": "follow", "to": lead.id, "left": 24}
            self.tell(q, f"{lead.name}'s band has taken you captive. They ask {I.describe(q.held['price'])} for you.")
            self.wake(q, f"taken captive by {lead.name}")
            self.trust(q, lead, -0.5, ("taken", f"{lead.name} took you captive"))
            for k, r in q.rel.items():
                o = w.people.get(int(k))
                if o and o.alive and (r.get("kin") or any(g in o.groups for g in q.groups)) and o.id != lead.id:
                    self.trust(o, lead, -0.3, ("taken", f"{lead.name} took {q.name} captive"))
                    self.tell(o, f"{lead.name} has taken {q.name} captive and asks {I.describe(q.held['price'])} "
                                 f"(ransom: to {lead.name}, who {q.name}).")
                    if r.get("kin"):
                        self.wake(o, f"{q.name} was taken captive")
            self.event("captive", f"{lead.name} took {q.name} captive", lead, q, x=q.x, y=q.y)

    def held_by(self, p):
        return [q for q in self.w.living() if q.held and q.held["by"] == p.id]

    def free(self, q, why, kind):
        w = self.w
        by = w.people.get(q.held["by"]) if q.held else None
        q.held = None
        q.intent, q.act = None, None
        self.tell(q, f"You are free ({why}).")
        self.event(kind, f"{q.name} {why}", q, *([by] if by else []), x=q.x, y=q.y)

    def start_ransom(self, p, a):
        """Pay what is asked for one held, to their captor, face to face: they go free."""
        w = self.w
        q = w.by_name(a.get("who") or a.get("captive") or a.get("for"))
        if not q or not q.held:
            return "ransom whom? (who: one held captive)"
        cap = w.people.get(q.held["by"])
        if not cap or not cap.alive:
            return f"{q.name} is held by no one now"
        if dist(p.x, p.y, cap.x, cap.y) > 1 and p.id != q.id:
            return self.set_kw(p, {"do": "ransom", "who": q.id, "to": cap.id})
        return self.pay_ransom(p, q, cap)

    def do_ransom(self, p, a):
        w = self.w
        q, cap = w.people.get(a["who"]), w.people.get(a["to"])
        if not q or not q.held or not cap or not cap.alive:
            return "fail", "There is no one to ransom now."
        c = self.chase(p, a, cap)
        if c:
            return "go", ""
        if c is None or dist(p.x, p.y, cap.x, cap.y) > 1:
            return "fail", f"You could not reach {cap.name}."
        res = self.pay_ransom(p, q, cap)
        return ("fail", res) if isinstance(res, str) else ("done", "")

    def pay_ransom(self, p, q, cap):
        price = q.held["price"]
        for k, n in price.items():
            if p.inv.get(k, 0) < n:
                return f"the ransom is {I.describe(price)}; you do not carry it"
        for k, n in price.items():
            I.remove(p.inv, k, n)
            I.add(cap.inv, k, n)
        self.tell(cap, f"{p.name} paid {I.describe(price)} for {q.name}, who goes free.")
        if p.id != q.id:
            self.trust(q, p, 0.4, ("ransomed", f"{p.name} paid your ransom"))
        self.free(q, f"was ransomed from {cap.name} by {p.name}" if p.id != q.id else f"bought freedom from {cap.name}", "ransomed")
        return self.set(p, "wait", left=1)

    def start_release(self, p, a):
        """Let one of those one holds go, freely."""
        q = self.w.by_name(a.get("who") or a.get("to") or a.get("captive"))
        if not q or not q.held or q.held["by"] != p.id:
            return "you hold no one by that name"
        self.trust(q, p, 0.2)
        self.free(q, f"was let go by {p.name}", "released")
        return self.set(p, "wait", left=1)

    def start_escape(self, p, a):
        """Try to slip away from one's captors: easier at night, when they are few or far, for the bold."""
        w = self.w
        if not p.held:
            return "you are not held"
        cap = w.people.get(p.held["by"])
        watch = sum(1 for o in w.near(p.x, p.y, 3) if o.id != p.id and cap and (o.id == cap.id or self.band_of(o) is self.band_of(cap)))
        chance = 0.15 + (0.25 if w.is_night() else 0) + 0.2 * p.traits.get("boldness", 0.5) - 0.06 * watch
        if w.rng.random() < max(0.05, chance):
            home = w.buildings.get(p.home)
            self.free(p, f"escaped from {cap.name if cap else 'captivity'}", "escaped")
            act = {"do": "go"}
            if home and self.walk(p, act, home.x, home.y, True):
                p.act = act
            return True
        p.health -= 1
        if cap:
            self.trust(cap, p, -0.2)
            self.tell(cap, f"{p.name} tried to escape and was caught.")
        self.tell(p, "You tried to slip away, and were caught.")
        return self.set(p, "wait", left=2)

    def feed_captive(self, q, cap):
        """A captive is fed from their captor's food, carried or in store: the cost of holding one (c79)."""
        w = self.w
        for inv in [cap.inv] + [b.inv for b in w.owned(cap.id) if b.done and b.inv and "store" in BUILDINGS[b.kind]["roles"]]:
            k = next((k for k in sorted(inv, key=lambda k: I.info(k).get("food", 0)) if I.info(k).get("food") and inv[k] >= 1), None)
            if k:
                I.remove(inv, k, 1)
                q.satiety = min(20, q.satiety + I.info(k)["food"])
                return True
        return False

    def held_hour(self):
        """Captives stay with their captors; a captive whose captor is gone is free."""
        w = self.w
        w.holding = {}
        for q in w.living():
            if not q.held:
                continue
            cap = w.people.get(q.held["by"])
            if not cap or not cap.alive:
                self.free(q, "is free, their captor gone", "released")
                continue
            w.holding.setdefault(cap.id, []).append(q.id)
            if q.satiety <= 8 and not any(I.info(k).get("food") for k in q.inv) and not self.feed_captive(q, cap):
                if q.satiety <= 2:
                    self.free(q, f"was let go by {cap.name}, who had nothing to feed them", "released")
                    continue
            if q.act is None or q.act.get("do") not in ("follow", "eat", "rest", "sleep", "wait", "ransom"):
                q.act = {"do": "follow", "to": cap.id, "left": 24}

    # ================= each hour =================
    def bands_tick(self):
        w = self.w
        self.held_hour()
        for band in list(w.bands.values()):
            lead = w.people.get(band["leader"])
            if not lead or not lead.alive:
                self.end_band(band, "its leader fell")
                continue
            band["members"] = [m for m in band["members"] if w.people.get(m) and w.people[m].alive
                               and (w.people[m].intent or {}).get("band") == band["id"]]
            for m in band["members"]:                    # keep up with the leader
                o = w.people[m]
                if o.act is None or o.act.get("do") != "follow":
                    o.act = {"do": "follow", "to": lead.id, "left": 24}
            if band["state"] == "marching" and band["target"] and dist(lead.x, lead.y, *band["target"]) <= 3:
                # the band gathers before it strikes: most of it close, or after a few hours' wait (c73)
                close = sum(1 for m in band["members"] if dist(w.people[m].x, w.people[m].y, lead.x, lead.y) <= 3)
                if close < 0.7 * len(band["members"]) and band.get("waited", 0) < 6:
                    band["waited"] = band.get("waited", 0) + 1
                    continue
                band["state"], band["fought"] = "fighting", 0
                band["start_power"] = sum(power(w.people[m]) for m in band["members"]) + power(lead)
                self.alarm(band)
            if band["state"] == "fighting":
                self.battle_hour(band)
            elif band["state"] == "returning" and dist(lead.x, lead.y, *band["home"]) <= 2:
                self.divide(band, lead)
                self.end_band(band, "home again")
            elif band["state"] == "gathering" and w.tick - band["since"] > 2 * TPD:
                self.end_band(band, "it went nowhere")

    def defenders(self, band):
        x, y = band["target"]
        return self.defenders_at(x, y, set(band["members"]) | {band["leader"]})

    def defenders_at(self, x, y, ids=()):
        """Those who stand for a place: grown people there (within 4 steps) or whose home is beside it (within 5), not
        of the raiders. A raid falls on a homestead, not on the whole land around it (c73)."""
        w = self.w
        out = []
        for q in w.near(x, y, 8):
            if q.id in ids or q.held or not q.adult(w.tick) or q.health <= 2:
                continue
            home = w.buildings.get(q.home)
            if dist(q.x, q.y, x, y) <= 4 or (home and dist(home.x, home.y, x, y) <= 5):
                out.append(q)
        return out

    def alarm(self, band):
        w = self.w
        lead = w.people[band["leader"]]
        x, y = band["target"]
        held = self.defenders(band)
        owners = [w.people[b.owner] for b in w.buildings_within(x, y, 4) if b.owner in w.people]
        for o in owners + held:
            pk = self.peace_between(lead, o)
            if pk:
                self.break_peace(lead, *pk, held + owners)
        for q in held:
            self.tell(q, f"A band of {len(band['members']) + 1} under {lead.name} has come upon your home!")
            self.wake(q, f"raiders under {lead.name} are here")
        self.rally(band, held + owners)
        self.event("raid", f"{lead.name}'s band of {len(band['members']) + 1} fell upon ({band['target'][0]},{band['target'][1]})",
                   lead, x=band["target"][0], y=band["target"][1], size=len(band["members"]) + 1)

    def rally(self, band, attacked):
        """The alarm goes round (c77): grown people within a short run (8 steps) who share a group, a lord, or kinship with
        those attacked hear it; bots come running as bold and loyal as they are; people with minds of their own are
        told and choose. Those who come stand with the place once they are there."""
        w = self.w
        x, y = band["target"]
        lead = w.people[band["leader"]]
        ours = set(band["members"]) | {band["leader"]}
        realms = {h.id for q in attacked for h in self.realms(q)}
        kin = {int(k) for q in attacked for k, r in q.rel.items() if r.get("kin")}
        there = {q.id for q in attacked}
        came = 0
        for q in w.near(x, y, 8):                    # about an hour a step: farther would come too late
            if q.id in ours or q.id in there or q.held or not q.adult(w.tick) or q.health <= 5 or self.band_of(q):
                continue
            if not (q.id in kin or realms & {h.id for h in self.realms(q)}):
                continue
            if q.mind == "llm":
                self.tell(q, f"Raiders under {lead.name} have fallen on ({x},{y}), where your own are!")
                self.wake(q, f"raiders at ({x},{y})")
                continue
            if 0.3 + 0.6 * q.traits.get("boldness", 0.5) + (0.3 if q.id in kin else 0) < w.rng.random() + 0.3:
                continue
            act = {"do": "go"}
            if self.walk(q, act, x, y, True):
                q.act, q.intent = act, {"goal": f"stand against {lead.name}'s raiders", "plan": [{"do": "wait", "hours": 3}]}
                came += 1
        if came:
            self.event("rally", f"{came} came running to stand against {lead.name}'s band at ({x},{y})", lead, x=x, y=y, n=came)

    def battle_hour(self, band):
        """An hour of fighting, reckoned as a whole: each side strikes in proportion to its strength against the
        other's; a side that has lost too much breaks (c72)."""
        w = self.w
        lead = w.people[band["leader"]]
        x, y = band["target"]
        raiders = [w.people[m] for m in band["members"] if dist(w.people[m].x, w.people[m].y, x, y) <= 5] + [lead]
        held = self.defenders(band)
        wall = any(b.done and "wall" in BUILDINGS[b.kind]["roles"] for b in w.buildings_within(x, y, 4))
        A = sum(power(q) for q in raiders)
        D = sum(power(q) for q in held) * (1.6 if wall else 1.0)
        band["fought"] += 1
        if D <= 0.6 * A or not held:
            return self.plunder(band, raiders, held)
        for side, other, strength, against in ((raiders, held, A, D), (held, raiders, D, A)):
            chance = 0.4 * against / (A + D)
            for q in side:
                if q.alive and w.rng.random() < chance:
                    foe = w.rng.choice([o for o in other if o.alive] or [None])
                    dmg = w.rng.randint(2, 4)
                    q.health -= dmg
                    self.tell(q, f"You were struck in the fighting (lost {dmg} health).")
                    if foe:
                        self.trust(q, foe, -0.4, ("attacked", f"{foe.name} struck you in a fight"))
                    if q.health <= 0:
                        self.die(q, "killed", by=foe)
                        if side is raiders:
                            band.setdefault("fallen", []).append(q.id)
        A2 = sum(power(q) for q in raiders if q.alive)
        D2 = sum(power(q) for q in held if q.alive) * (1.6 if wall else 1.0)
        if band["fought"] >= 4 and A2 > D2:
            return self.plunder(band, raiders, held)
        if A2 < 0.5 * band["start_power"] or A2 < 0.5 * D2 or band["fought"] >= 4:
            band["state"] = "returning"
            act = {"do": "go"}
            if lead.alive and self.walk(lead, act, *band["home"], True):
                lead.act = act
            for q in held:
                for r in raiders:
                    self.trust(q, r, -0.3, ("raided", f"{r.name} came raiding with {lead.name}"))
            self.event("repelled", f"{lead.name}'s band was driven off from ({x},{y})", lead, *held[:6], x=x, y=y)
            self.weariness(band, False, [w.people[i] for i in band.get("fallen", []) if i in w.people])
            self.unprotected(x, y, held, lead, False)
            if lead.alive:
                lead.known[f"beaten@{x} {y}"] = ["beaten", f"{x},{y}", w.tick]     # not there again soon
            self.tell(lead, "Your band is beaten back: you turn for home.")
            return
        if D2 <= 0.6 * A2:
            return self.plunder(band, raiders, held)

    def plunder(self, band, raiders, held):
        """The place is the raiders': each takes from the stores there what they can carry, food and metal first."""
        w = self.w
        lead = w.people[band["leader"]]
        x, y = band["target"]
        took = {}
        stores = [b for b in w.buildings_within(x, y, 4) if b.done and b.inv and "store" in BUILDINGS[b.kind]["roles"]]
        best = lambda k: (-(I.info(k).get("food", 0) > 0) * 2 - ("bronze" in k or "iron" in k or "copper" in k or k == "coin"), -I.info(k).get("worth", 1))
        for r in [q for q in raiders if q.alive]:
            for b in stores:
                for k in sorted(list(b.inv), key=best):
                    if ":" in k or not (I.info(k).get("food") or I.info(k).get("worth", 1) >= 2):
                        continue                    # food, and what is worth carrying off; not wood and clay
                    n = min(b.inv.get(k, 0), max(0, self.room(r, k)))
                    if n > 0:
                        I.remove(b.inv, k, n)
                        I.add(r.inv, k, n)
                        took[k] = took.get(k, 0) + n
                        if r.id != lead.id:
                            got = band.setdefault("spoils", {}).setdefault(str(r.id), {})
                            got[k] = got.get(k, 0) + n
                        o = w.people.get(b.owner)
                        if o:
                            self.trust(o, r, -0.5, ("robbed", f"{r.name} took {n} {I.pretty(k)} from your {b.kind} in {lead.name}'s raid"))
        for q in held:
            for r in raiders:
                self.trust(q, r, -0.3, ("raided", f"{r.name} came raiding with {lead.name}"))
        band["state"] = "returning"
        act = {"do": "go"}
        if self.walk(lead, act, *band["home"], True):
            lead.act = act
        what = ", ".join(f"{n} {I.pretty(k)}" for k, n in sorted(took.items(), key=lambda kv: -kv[1])[:5]) or "little"
        self.tell(lead, f"The place is yours: your band took {what}. You turn for home.")
        self.event("plunder", f"{lead.name}'s band took {what} at ({x},{y})", lead, *raiders[:6], x=x, y=y, goods=took)
        self.weariness(band, True, [w.people[i] for i in band.get("fallen", []) if i in w.people])
        self.unprotected(x, y, held, lead, True)
        if band.get("take") and lead.alive:
            self.seize(lead, [q for q in held if q.alive and not q.held], max(1, len(raiders) // 3))

    def unprotected(self, x, y, held, raider, lost):
        """Lords are judged by whether they protect: a sworn group whose home is raided looks to its lord's people; if
        none stood with them and the place was lost, its leader trusts the lord less; if they stood and held, more
        (c75)."""
        w = self.w
        seen = set()
        for b in w.buildings_within(x, y, 4):
            o = w.people.get(b.owner)
            if not o:
                continue
            for gid in o.groups:
                g = w.groups.get(gid)
                if not g or g.dissolved is not None or not g.parent or g.id in seen:
                    continue
                seen.add(g.id)
                lord = w.groups.get(g.parent)
                head, vas = w.people.get(lord.leader) if lord else None, w.people.get(g.leader)
                if not head or not vas or not vas.alive or self.chain(g)[-1] in self.realms(raider):
                    continue
                helped = any(q.id not in g.members and lord in self.realms(q) for q in held)
                if lost and not helped:
                    self.trust(vas, head, -0.25, ("unprotected", f"{lord.name} did not stand with {g.name} when {raider.name} raided"))
                elif helped:
                    self.trust(vas, head, 0.15, ("protected", f"{lord.name}'s people stood with {g.name} against {raider.name}"))


def share_of(v):
    """How a raid's spoils are divided at home (c81), as the leader writes it."""
    v = str(v or "").strip().lower()
    if v in ("mine", "all", "me", "leader", "my store", "to me", "all to me"):
        return "mine"
    if v in ("half", "halves", "half to me"):
        return "half"
    return "each"


def num_hours(v, d=3):
    try:
        return max(1, min(12, int(v)))
    except (TypeError, ValueError):
        return d
