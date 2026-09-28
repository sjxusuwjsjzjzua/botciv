"""Detectors: name patterns in the event log, each with the event ids that prove it.

The variety count (how many distinct pattern kinds appeared) is the measure
of whether the world is open-ended or has collapsed into one way of living.
"""
from collections import defaultdict

BOND_WINDOW = 60        # hours: a gift, deal or joint hunt makes a bond this recent
FEUD_WINDOW = 120


def detect(events, world=None):
    found = []
    evs = [e for e in events if e.get("kind") != "frame"]
    names = {}
    if world is not None:
        names = {a.id: a.name for a in world.agents.values()}

    def nm(i):
        return names.get(i, f"#{i}")

    bonds = defaultdict(list)          # (a, b) unordered -> [(t, id)]
    members = defaultdict(set)         # group id -> member ids (as the log shows)
    group_of = defaultdict(set)        # agent -> groups
    group_name = {}
    attacks = defaultdict(list)        # unordered pair -> [(t, id)]
    deals_by = defaultdict(list)
    starving = []
    teach_chain = defaultdict(list)    # recipe -> [(t, from, to, id)]

    def bond(a, b, t, i):
        if a is not None and b is not None and a != b:
            bonds[frozenset((a, b))].append((t, i))

    def bonded(a, b, t):
        return [i for (t0, i) in bonds.get(frozenset((a, b)), []) if 0 <= t - t0 <= BOND_WINDOW]

    for e in evs:
        k, t, i, a, b = e["kind"], e["t"], e["id"], e.get("a"), e.get("b")
        if k in ("give", "teach"):
            bond(a, b, t, i)
        elif k == "deal":
            bond(a, b, t, i)
            deals_by[a].append((t, b, i))
            deals_by[b].append((t, a, i))
        elif k == "hunt":
            hs = e.get("hunters", [])
            for x in hs:
                for y in hs:
                    if x < y:
                        bond(x, y, t, i)
        elif k == "group_found":
            members[e["group"]] = {a}
            group_of[a].add(e["group"])
            group_name[e["group"]] = e["text"].split(" founded the group ", 1)[-1].split(". Rules:")[0]
        elif k == "join":
            members[e["group"]].add(a)
            group_of[a].add(e["group"])
            for m in members[e["group"]]:
                bond(a, m, t, i)
        elif k in ("leave", "expel"):
            who = a if k == "leave" else b
            members[e["group"]].discard(who)
            group_of[who].discard(e["group"])
            if k == "expel":
                found.append({"kind": "law", "t": t, "ids": [i],
                              "text": f"{nm(who)} was cast out of {group_name.get(e['group'], 'a group')}"})
        if k in ("attack", "steal", "steal_fail", "promise_broken"):
            shared = [g for g in group_of[a] & group_of[b]] if a and b else []
            prior = bonded(a, b, t)
            if prior or shared:
                what = {"attack": "attacked", "steal": "stole from", "steal_fail": "tried to rob",
                        "promise_broken": "broke a promise to"}[k]
                why = "a fellow member" if shared else "someone they had recently traded, hunted or shared with"
                found.append({"kind": "betrayal", "t": t, "ids": [i] + prior[-3:],
                              "text": f"{nm(a)} {what} {nm(b)}, {why}"})
        if k == "attack":
            key = frozenset((a, b))
            attacks[key].append((t, i))
            recent = [x for x in attacks[key] if t - x[0] <= FEUD_WINDOW]
            if len(recent) == 3:
                found.append({"kind": "feud", "t": t, "ids": [x[1] for x in recent],
                              "text": f"{nm(a)} and {nm(b)} have come to blows again and again"})
            ga, gb = group_of[a], group_of[b]
            if ga and gb and not (ga & gb):
                for g1 in ga:
                    for g2 in gb:
                        key2 = ("war", min(g1, g2), max(g1, g2))
                        attacks[key2].append((t, i))
                        if len(attacks[key2]) == 3:
                            found.append({"kind": "war", "t": t, "ids": [x[1] for x in attacks[key2]],
                                          "text": f"{group_name.get(g1, 'a group')} and {group_name.get(g2, 'a group')} are fighting"})
        if k == "deal":
            for who in (a, b):
                partners = {p for (_, p, _) in deals_by[who]}
                if len(deals_by[who]) == 4 and len(partners) >= 2:
                    found.append({"kind": "market", "t": t, "ids": [x[2] for x in deals_by[who]],
                                  "text": f"{nm(who)} trades regularly, with {len(partners)} partners"})
        if k == "craft" and e.get("first"):
            found.append({"kind": "innovation", "t": t, "ids": [i], "text": e["text"].replace(" made a ", " first made a ")})
        if k == "lost_knowledge":
            found.append({"kind": "lost_knowledge", "t": t, "ids": [i], "text": e["text"]})
        if k == "teach":
            teach_chain[e.get("pair")].append((t, a, b, i))
            chain = teach_chain[e.get("pair")]
            if len(chain) >= 2 and any(c[2] == a for c in chain[:-1]):
                found.append({"kind": "tradition", "t": t, "ids": [c[3] for c in chain][-3:],
                              "text": f"knowledge of {e.get('item')} is being handed down: {nm(a)} passed on what they were taught"})
        if k == "death" and e.get("cause") == "starved":
            starving.append((t, i))
            recent = [x for x in starving if t - x[0] <= 120]
            if len(recent) == 3:
                found.append({"kind": "famine", "t": t, "ids": [x[1] for x in recent], "text": "people are starving"})
        if k == "story":
            origin = e.get("origin")
            if origin and origin != nm(a):
                found.append({"kind": "tradition", "t": t, "ids": [i], "text": f"{nm(a)} retold a story first told by {origin}"})
            else:
                found.append({"kind": "storytelling", "t": t, "ids": [i], "text": e["text"][:200]})
        if k in ("burial", "build") and (k == "burial" or e.get("what") == "monument"):
            found.append({"kind": "memorial", "t": t, "ids": [i], "text": e["text"]})
        if k == "name_place":
            found.append({"kind": "naming", "t": t, "ids": [i], "text": e["text"]})
        if k == "deed":
            found.append({"kind": "custom", "t": t, "ids": [i], "text": e["text"]})
        if k == "vote_result" and e.get("passed"):
            found.append({"kind": "self_rule", "t": t, "ids": [i], "text": e["text"]})
        if k == "mark" and any(w in e.get("words", "").lower() for w in ("law", "rule", "forbid", "must", "belongs", "ours", "keep out", "do not")):
            found.append({"kind": "claim_or_law", "t": t, "ids": [i], "text": e["text"]})
    # alliances: groups that reached 3+ members and lasted
    firsts = {}
    for e in evs:
        if e["kind"] in ("group_found", "join"):
            g = e["group"]
            firsts.setdefault(g, e["t"])
    last_t = evs[-1]["t"] if evs else 0
    for g, m in members.items():
        if len(m) >= 3 and last_t - firsts.get(g, last_t) >= 50:
            found.append({"kind": "alliance", "t": last_t, "ids": [],
                          "text": f"{group_name.get(g, 'a group')} holds together: {', '.join(nm(x) for x in sorted(m))}"})
    # culture: someone knows a story whose first teller died before they were born
    if world is not None:
        by_name = {x.name: x for x in world.agents.values()}
        for x in world.living():
            for origin, text, first, teller in x.lore:
                o = by_name.get(origin)
                if o and not o.alive and o.died is not None and o.died < x.born:
                    found.append({"kind": "culture", "t": world.tick, "ids": [],
                                  "text": f"{x.name} knows a story from {origin}, who died before {x.name} was born: \"{text[:120]}\""})
    found.sort(key=lambda f: f["t"])
    return found


def variety(found, events):
    kinds = {f["kind"] for f in found}
    verbs = {e.get("verb") or e["kind"] for e in events if e.get("kind") not in ("frame", "fail")}
    return {"patterns": sorted(kinds), "pattern_count": len(kinds), "event_kinds": len(verbs)}
