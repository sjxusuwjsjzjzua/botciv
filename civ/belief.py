"""Belief (grand world, docs/grand.md section 6J, Phase 6): faith as a social technology. What anyone believes is
theirs; the engine keeps only the days and the places.

Each people keeps a rite on a day of its festival season (content/peoples.py), at a shrine or temple of its own
near its head's home, or else at the head's home. Word of the day goes round the people at dawn. Those of the
people who come (or anyone, as a guest) and are there through the afternoon have kept it: they trust one another
and their host more, and food in the store there is shared out as a feast. Nothing makes anyone go."""
from .content import BUILDINGS
from .content import items as I
from .content.peoples import PEOPLES
from .world import dist, DPS, TPD

GATHER = (3, 8)                 # the hours of the day when those at the rite are counted (morning to evening)
NEAR = 3                        # how close to the place one stands to be at the rite
FEAST = 1                       # food shared to each who came, if the store there has it


class Belief:
    def rite_site(self, k):
        """Where a people keeps its rite: a shrine or temple of one of its own near its head's home, else that home."""
        w = self.w
        heads = [w.people[g.leader] for g in w.groups.values() if g.dissolved is None and g.parent is None
                 and g.leader in w.people and w.people[g.leader].alive and w.people[g.leader].people == k]
        if not heads:
            return None, None
        head = max(heads, key=lambda p: sum(len(g.members) for g in w.groups.values() if g.leader == p.id and g.dissolved is None))
        home = w.buildings.get(head.home)
        hx, hy = (home.x, home.y) if home else (head.x, head.y)
        best = None
        for b in w.buildings_within(hx, hy, 15):
            o = w.people.get(b.owner)
            if b.done and "gathering" in BUILDINGS[b.kind]["roles"] and o and o.people == k:
                d = dist(hx, hy, b.x, b.y) - (10 if b.kind == "temple" else 0)
                if best is None or d < best[0]:
                    best = (d, b)
        if best:
            return best[1], head
        return home, head

    def rites_dawn(self):
        """A people whose rite falls today is told where it is kept."""
        w = self.w
        w.rites = {k: v for k, v in w.rites.items() if v.get("day") == w.day()}
        season, day = w.season(), w.day() % DPS
        for k in w.peoples:
            d = PEOPLES.get(k, {})
            if d.get("festival") != season or not d.get("rite") or d["rite"][1] != day or k in w.rites:
                continue
            site, head = self.rite_site(k)
            if not head:
                continue
            x, y = (site.x, site.y) if site else (head.x, head.y)
            w.rites[k] = {"x": x, "y": y, "day": w.day(), "came": [], "host": head.id, "site": site.id if site else None,
                          "name": d["rite"][0]}
            for p in w.living():
                if p.people == k and p.adult(w.tick) and dist(p.x, p.y, x, y) <= 30:
                    self.tell(p, f"Today is {d['rite'][0]}: your people gather at ({x},{y}) until evening.")

    def rites_hour(self):
        """Those at the rite are counted; at evening it ends: those who kept it are bound closer, and a feast is shared."""
        w = self.w
        if not w.rites:
            return
        h = w.hour()
        for k, r in list(w.rites.items()):
            if r.get("done") or r["day"] != w.day():
                continue
            if GATHER[0] <= h < GATHER[1]:
                came = set(r["came"])
                for q in w.near(r["x"], r["y"], NEAR):
                    if q.adult(w.tick) and not q.held:
                        came.add(q.id)
                r["came"] = sorted(came)
            elif h >= GATHER[1]:
                r["done"] = True
                self.end_rite(k, r)

    def end_rite(self, k, r):
        w = self.w
        came = [w.people[i] for i in r["came"] if i in w.people and w.people[i].alive]
        host = w.people.get(r["host"])
        if len(came) < 3:
            return
        fed = 0
        site = w.buildings.get(r.get("site")) if r.get("site") else None
        store = site if site and site.inv else (w.buildings.get(host.home) if host else None)
        for q in came:
            if store and store.inv:
                k2 = next((i for i in sorted(store.inv) if I.info(i).get("food") and store.inv[i] >= FEAST), None)
                if k2:
                    I.remove(store.inv, k2, FEAST)
                    q.satiety = min(20, q.satiety + I.info(k2)["food"] * FEAST)
                    fed += 1
        bond = 0.06 if fed >= len(came) // 2 else 0.04
        for q in came:
            others = [o for o in came if o.id != q.id]
            for o in w.rng.sample(others, min(12, len(others))):
                self.trust(q, o, bond)
            if host and host.id != q.id:
                self.trust(q, host, bond)
        self.event("festival", f"{len(came)} kept {r['name']} at ({r['x']},{r['y']})" + (f", {host.name} hosting" if host else "")
                   + (f"; {fed} shared the feast" if fed else ""), *([host] if host else []), x=r["x"], y=r["y"], n=len(came))


def rite_text(e, p):
    """One's people's rite: when it falls, and where, as it nears (c79)."""
    w = e.w
    d = PEOPLES.get(p.people or "", {})
    if not d.get("rite"):
        return []
    name, day = d["rite"]
    r = w.rites.get(p.people)
    if r and r["day"] == w.day() and not r.get("done"):
        return [f"Today is {name}: your people gather at ({r['x']},{r['y']}) until evening."]
    seasons = ["spring", "summer", "autumn", "winter"]
    now = w.day()
    start = now - now % (DPS * 4) + seasons.index(d["festival"]) * DPS + day
    if start < now:
        start += DPS * 4
    if start - now <= 5:
        return [f"{name}, your people's rite, is in {start - now} day{'s' if start - now != 1 else ''}."]
    return []
