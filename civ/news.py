"""News and renown (grand world, docs/grand.md Phase 6): the land is bigger than anyone's sight, so word of what
matters must travel, and it travels only with people.

A notable thing (a raid, a battle, fealty sworn or broken, a lord's death, a hard year, a first craft, a monument,
a law) becomes a piece of news where it happened; those who saw it know it. When people spend time together each
passes the other the newest word they lack, as told by them; so word crosses the land as fast as people walk it and
no faster, and fades as it ages. Renown is how many have heard of someone."""
from .world import dist, TPD, TPY

NEWS = {"raid", "plunder", "repelled", "fealty", "renounce", "tribute_unpaid", "year", "first", "monument", "law",
        "place", "group", "trader"}
DEEDS = {"raid", "plunder", "repelled", "fealty", "renounce", "first", "monument", "law", "place", "group"}
KEEP = 30                   # pieces of news one carries, the newest
FRESH = 60 * TPD            # word older than this is not passed on


class News:
    def make_news(self, ev):
        """A notable event becomes news where it happened, known at once to those who saw it."""
        w = self.w
        kind = ev["kind"]
        if kind == "death":
            dead = w.people.get(ev["who"][0]) if ev["who"] else None
            leads = dead and any(w.groups.get(g) and w.groups[g].leader == dead.id for g in dead.groups)
            if not (dead and (leads or str(ev.get("cause", "")).startswith("killed by"))):
                return
        elif kind not in NEWS:
            return
        who = [w.people[i] for i in ev["who"] if i in w.people]
        if ev.get("x") is not None and ev.get("y") is not None:
            x, y = ev["x"], ev["y"]
        elif who:
            x, y = who[0].x, who[0].y
        else:
            return
        nid = str(ev["id"])
        w.news[nid] = {"t": ev["t"], "text": ev["text"], "x": x, "y": y, "kind": kind, "who": ev["who"]}
        for o in w.near(x, y, 5):
            self.hear(o, nid, 0)

    def hear(self, p, nid, by):
        """p comes to know a piece of news (by: who told them, 0 if they saw it); those it names grow in renown."""
        w = self.w
        if nid in p.news or nid not in w.news:
            return False
        p.news[nid] = [w.tick, by]
        if len(p.news) > KEEP:
            for k in sorted(p.news, key=lambda k: p.news[k][0])[:len(p.news) - KEEP]:
                del p.news[k]
        if w.news[nid]["kind"] in DEEDS:            # renown is for deeds, not for dying or a bad year
            for i in w.news[nid]["who"][:3]:
                q = w.people.get(i)
                if q and q.id != p.id:
                    q.renown += 1
        return True

    def news_day(self):
        """Word goes round: people beside each other each pass on the newest word the other lacks (two pieces a
        day), as told by them; old news is let go."""
        w = self.w
        for k in [k for k, v in w.news.items() if w.tick - v["t"] > TPY]:
            del w.news[k]
        # who is much spoken of: the top tenth by renown, and the top fiftieth known far and wide
        fame = sorted((q.renown for q in w.living() if q.renown > 0), reverse=True)
        w.fame = (fame[len(fame) // 10] if len(fame) >= 10 else 10 ** 9, fame[len(fame) // 50] if len(fame) >= 50 else 10 ** 9)
        for p in w.living():
            if not p.news or not p.adult(w.tick):
                continue
            fresh = sorted((k for k, v in p.news.items() if k in w.news and w.tick - w.news[k]["t"] <= FRESH),
                           key=lambda k: -w.news[k]["t"])
            if not fresh:
                continue
            for o in w.near(p.x, p.y, 2):
                if o.id == p.id or o.rel.get(str(p.id), {}).get("trust", 0) < -0.3:
                    continue
                told = 0
                for k in fresh:
                    if self.hear(o, k, p.id):
                        told += 1
                        if told >= 2:
                            break


def news_text(e, p, most=4):
    """Word reaching one: the newest pieces one has heard or seen these last weeks, not one's own doings."""
    w = e.w
    items = sorted((k for k in p.news if k in w.news and p.id not in w.news[k]["who"] and w.tick - p.news[k][0] <= 40 * TPD),
                   key=lambda k: -w.news[k]["t"])[:most]
    if not items:
        return []
    out = ["Word reaching you:"]
    for k in items:
        n, (_, by) = w.news[k], p.news[k]
        teller = w.people.get(by)
        far = dist(p.x, p.y, n["x"], n["y"])
        out.append(f"- {n['text']} ({w.when(n['t'])}, {far} steps off; " + (f"as told by {teller.name})" if teller else "you saw it)"))
    return out
