"""Land held, not only buildings (grand world, docs/grand.md §6 F, Phase 4; rules c85).

A realm (a group sworn to no one, with the groups sworn to it) holds the land about its members' homes and fields
and about the cairns and monuments its people raised; where claims meet, the nearer holds. The layer is reckoned
each dawn and kept in no file. Using another realm's land without leave (felling, gathering, hunting, sowing,
building) is trespass: its people remember it when one of them sees it. Its head may give leave to a person, a
group or a whole people, and may set a toll at a ford or bridge on its land; those who cross pay it if they carry it,
and one seen slipping past without paying is remembered. Nothing decides that anyone should respect a border."""
from collections import deque

from .content import BUILDINGS
from .content import items as I
from .world import dist, TPD

HOME_REACH = 5          # steps of land a home or a field holds about it
STONE_REACH = 4         # and a cairn or monument
MIN_REALM = 4           # people a realm needs before its land is its own (a household holds no border)
SEEN = 8                # steps within which one of the holders sees a trespass


class Territory:
    # ================= the layer =================
    def top_of(self, g):
        """The group at the head of g's chain of fealty."""
        seen = set()
        while g and g.parent and g.id not in seen:
            seen.add(g.id)
            up = self.w.groups.get(g.parent)
            if not up or up.dissolved is not None:
                break
            g = up
        return g

    def realm_size(self, top):
        return len(top.members) + sum(len(h.members) for h in self.sworn_to(top))

    def reckon_land(self):
        """Who holds each tile: the nearest claim of a realm of MIN_REALM or more (homes, fields, stones)."""
        w = self.w
        held = {}
        tops = {}
        for g in w.groups.values():
            if g.dissolved is None:
                t = self.top_of(g)
                if t and t.dissolved is None:
                    tops.setdefault(t.id, t)
        q = deque()
        for t in tops.values():
            if self.realm_size(t) < MIN_REALM:
                continue
            members = set(t.members)
            for h in self.sworn_to(t):
                members |= set(h.members)
            for pid in members:
                p = w.people.get(pid)
                if not p or not p.alive:
                    continue
                for b in w.owned(pid):
                    roles = BUILDINGS[b.kind]["roles"]
                    if not b.done:
                        continue
                    if "monument" in roles:
                        q.append((b.x, b.y, t.id, STONE_REACH))
                    elif "farm" in roles or b.id == p.home:
                        q.append((b.x, b.y, t.id, HOME_REACH))
        # grown out from every claim at once, a step at a time: the nearer claim takes a tile first
        while q:
            x, y, tid, left = q.popleft()
            i = y * w.w + x
            if i in held:
                continue
            held[i] = tid
            if left <= 0:
                continue
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if 0 <= nx < w.w and 0 <= ny < w.h and ny * w.w + nx not in held:
                    q.append((nx, ny, tid, left - 1))
        w.held = held
        return held

    def holder_at(self, x, y):
        w = self.w
        if getattr(w, "held", None) is None:
            self.reckon_land()
        g = w.groups.get(w.held.get(y * w.w + x)) if w.held else None
        return g if g and g.dissolved is None else None

    def may_use_land(self, p, top):
        """Whether p may use top's land: its own people, its sworn, those at peace with it, those given leave, and
        (unless its head forbids it) those of the head's own people: a people's land is its commons, and borders
        are between peoples."""
        if any(self.top_of(h) is top for h in (self.w.groups.get(i) for i in p.groups) if h and h.dissolved is None):
            return True
        head = self.w.people.get(top.leader)
        if head and p.people == head.people and f"-k:{p.people}" not in (getattr(top, "leave", None) or []):
            return True
        if self.peace_between(p, self.w.people.get(top.leader)) if top.leader in self.w.people else False:
            return True
        leave = getattr(top, "leave", None) or []
        return f"p:{p.id}" in leave or f"k:{p.people}" in leave or any(f"g:{i}" in leave for i in p.groups)

    def keeps_off(self, p, x, y):
        """A bot keeps off the land of a realm it does not trust, unless hungry or the year is hard (c85)."""
        w = self.w
        if p.mind != "bot" or not w.held or p.satiety <= 6:
            return False
        top = self.holder_at(x, y)
        if not top or self.may_use_land(p, top):
            return False
        if w.regions and w.year_at(x, y) == "hard":
            return False
        return p.rel.get(str(top.leader), {}).get("trust", 0) < 0.3

    # ================= trespass =================
    def trespass(self, p, x, y, what):
        """p uses (x, y) for what (felling, hunting...): on another's land without leave, it is remembered by the
        holders who see it (once a day for each)."""
        w = self.w
        top = self.holder_at(x, y)
        if not top or self.may_use_land(p, top):
            return
        day = w.tick // TPD
        seen_key = f"tres{top.id}"
        if p.known.get(seen_key, [None, None, -1])[2] == day:
            return
        members = set(top.members)
        for h in self.sworn_to(top):
            members |= set(h.members)
        eyes = [o for o in w.near(x, y, SEEN) if o.id in members and o.adult(w.tick) and o.id != p.id]
        if not eyes:
            return
        p.known[seen_key] = ["trespass", top.id, day]
        head = w.people.get(top.leader)
        text = f"{p.name} was {what} on {top.name}'s land at ({x},{y}) without leave"
        for o in eyes[:3]:
            self.trust(o, p, -0.03, ("trespass", text))
        if head and head.alive and head not in eyes:
            self.trust(head, p, -0.02, ("trespass", text))
            self.tell(head, f"Word comes: {text}.")
        self.tell(p, f"You are on {top.name}'s land, and {eyes[0].name} saw you {what} here without leave.")
        self.event("trespass", text, p, eyes[0], x=x, y=y, holder=top.id)

    # ================= leave =================
    def start_grant(self, p, a):
        """A realm's head gives leave to use its land: to a person, a group or a whole people (or takes it back)."""
        w = self.w
        g = self.group_of(p, None, lead=True)
        if not g or g.parent:
            return "only the head of a realm sworn to no one gives leave to use its land"
        who = str(a.get("to") or a.get("who") or "").strip()
        take_back = str(a.get("value") or a.get("choice") or "").lower() in ("no", "none", "revoke", "take back", "false")
        o = w.by_name(who)
        h = next((x for x in w.groups.values() if x.dissolved is None and x.name.lower() == who.lower()), None)
        folk = next((k for k in {q.people for q in w.living() if q.people} if who.lower() in (k.lower(), (k + "s").lower())), None)
        tag = f"p:{o.id}" if o else f"g:{h.id}" if h else f"k:{folk}" if folk else None
        if not tag:
            return "give leave to whom? (to: a person, a group, or a people)"
        if not hasattr(g, "leave") or g.leave is None:
            g.leave = []
        if take_back:
            if tag in g.leave:
                g.leave.remove(tag)
            if tag.startswith("k:") and "-" + tag not in g.leave:
                g.leave.append("-" + tag)             # one's own people too may be forbidden
        else:
            if tag not in g.leave:
                g.leave.append(tag)
            if "-" + tag in g.leave:
                g.leave.remove("-" + tag)
        what = o.name if o else h.name if h else folk
        self.tell(p, f"{what} {'no longer has' if take_back else 'has'} leave to use {g.name}'s land.")
        if o:
            self.tell(o, f"{p.name} {'took back your' if take_back else 'gave you'} leave to use {g.name}'s land.")
        self.event("leave", f"{p.name} {'took back' if take_back else 'gave'} {what} leave to use {g.name}'s land", p, o, holder=g.id)
        return self.set(p, "wait", left=1)

    # ================= tolls =================
    def start_toll(self, p, a):
        """Set (or lift, with nothing asked) a toll at a ford or bridge on one's land (x, y)."""
        w = self.w
        g = self.group_of(p, None, lead=True)
        if not g or g.parent:
            return "only the head of a realm sworn to no one sets a toll on its land"
        try:
            x, y = int(a.get("x")), int(a.get("y"))
        except (TypeError, ValueError):
            return "a toll where? (x, y of a ford or bridge on your land)"
        b = w.building_at(x, y) if w.inb(x, y) else None
        if not w.inb(x, y) or not (w.t(x, y) == "s" or (b and b.done and "bridge" in BUILDINGS[b.kind]["roles"])):
            return "a toll is set at a ford (shallows) or a bridge"
        if self.holder_at(x, y) is not g:
            return f"({x},{y}) is not {g.name}'s land"
        from .society import goods, goods_text
        ask = goods(a.get("get") or a.get("give") or a.get("toll"))
        k = f"{x},{y}"
        if not ask:
            w.tolls.pop(k, None)
            self.tell(p, f"You lifted the toll at ({x},{y}).")
            return self.set(p, "wait", left=1)
        w.tolls[k] = {"holder": g.id, "goods": ask, "by": p.id, "since": w.tick, "paid": 0}
        self.tell(p, f"Those who cross at ({x},{y}) now pay {g.name} {goods_text(ask)}.")
        self.event("toll_set", f"{p.name} set a toll of {goods_text(ask)} at ({x},{y})", p, x=x, y=y, holder=g.id)
        return self.set(p, "wait", left=1)

    def crossing(self, p, x, y):
        """p steps onto (x, y): a toll there is paid, if p is not of the realm or given leave."""
        w = self.w
        t = w.tolls.get(f"{x},{y}")
        if not t:
            return
        top = w.groups.get(t["holder"])
        if not top or top.dissolved is not None:
            w.tolls.pop(f"{x},{y}", None)
            return
        if self.may_use_land(p, top) or not p.adult(w.tick):
            return
        day = w.tick // TPD
        if p.known.get(f"toll{x},{y}", [None, None, -1])[2] == day:
            return                                  # paid (or slipped past) today already
        p.known[f"toll{x},{y}"] = ["toll", top.id, day]
        from .society import goods_text
        head = w.people.get(top.leader)
        if all(p.inv.get(k, 0) >= n for k, n in t["goods"].items()) and head:
            dst = w.buildings.get(top.treasury) or next((b for b in w.owned(head.id) if b.done and "store" in BUILDINGS[b.kind]["roles"]), None)
            for k, n in t["goods"].items():
                I.remove(p.inv, k, n)
                I.add(dst.inv if dst else head.inv, k, n)
            t["paid"] += 1
            self.tell(p, f"You paid {top.name}'s toll at ({x},{y}): {goods_text(t['goods'])}.")
            self.event("toll", f"{p.name} paid {top.name}'s toll at ({x},{y})", p, x=x, y=y, holder=top.id, goods=t["goods"])
            return
        members = set(top.members)
        for h in self.sworn_to(top):
            members |= set(h.members)
        eyes = [o for o in w.near(x, y, SEEN) if o.id in members and o.adult(w.tick)]
        self.tell(p, f"You crossed at ({x},{y}) without paying {top.name}'s toll ({goods_text(t['goods'])})"
                     + (f"; {eyes[0].name} saw you." if eyes else "."))
        if eyes:
            text = f"{p.name} crossed at ({x},{y}) without paying {top.name}'s toll"
            for o in eyes[:3]:
                self.trust(o, p, -0.1, ("trespass", text))
            if head and head.alive and head not in eyes:
                self.trust(head, p, -0.1, ("trespass", text))
            self.event("toll_evaded", text, p, eyes[0], x=x, y=y, holder=top.id)
