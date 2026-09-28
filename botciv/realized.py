"""Ideas the people had that later versions of the world made real.

Each version that makes an idea real adds an entry here. When a world is loaded,
every entry it has not seen yet is credited once: the living person who first
had a matching idea is the first to know it, inside the world, and the event is
logged so the viewer can show whose idea it was. If no one alive had the idea,
it simply becomes possible, to be worked out by whoever tries.
"""
import re

REALIZED = [
    {"key": "smoking", "version": "w9",
     "what": "how to smoke fish and meat and dry berries over a fire, so they keep most of a year",
     "match": r"smok|\bdr(y|ied|ying)\b|preserv|spoil|keep (fish|meat|berr|food)|cure",
     "know": "smoking",
     "tell": "It came to you at last how to do what you once imagined: to smoke fish and meat and dry berries over a fire, so they keep most of a year."},
    {"key": "pledge", "version": "w9",
     "what": "that two people might pledge themselves to each other as partners for life",
     "match": r"propos|partner|marr|\bwed|spouse|family|for life",
     "tell": "You find that what you imagined is so: two people here can pledge themselves to each other as partners for life, sharing what they have."},
]


def first_imaginer(w, pattern):
    """The living person whose matching idea came earliest, with that idea's hour."""
    best = None
    for a in w.living():
        for t, text in a.ideas:
            if re.search(pattern, text.lower()) and (best is None or t < best[1]):
                best = (a, t, text)
    return best


def apply(e):
    """Credit every idea made real since this world last loaded. Returns what was credited."""
    w = e.w
    done = []
    for r in REALIZED:
        if r["key"] in w.realized:
            continue
        w.realized.append(r["key"])
        found = first_imaginer(w, r["match"])
        if not found:
            continue
        a, t, text = found
        if r.get("know") and r["know"] not in a.know:
            a.know.append(r["know"])
        e.tell(a, r["tell"])
        e.wake(a, "something you imagined has come to you")
        e.event("realized", f"{a.name} was the first to know {r['what']}, as they had imagined: “{text}”",
                a, key=r["key"], idea=text, imagined=t)
        done.append((r["key"], a.name))
    return done
