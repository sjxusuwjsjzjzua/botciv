"""Advance a civ world for a while and save it.

    python -m civ.run --dir world2 --new --people 200 --ai 60 --minutes 60 --models ollama:gemma4:26b
    python -m civ.run --dir w --new --people 120 --bots --ticks 960        # bots only, no model

The directory holds state.json.gz (the whole world) and log/: events, decisions and frames
(where everyone was each hour, and once a day the land) as gzipped JSON lines, one file each
per run. last_run.md says what happened."""
import argparse
import gzip
import json
import os
import time
from collections import Counter
from datetime import datetime, timezone

from .content import BUILDINGS, CRAFTS
from .engine import Engine
from .gen import generate
from .minds.bot import BotMind
from .prompt import RULES_VERSION
from .world import World, TPD, TPY


class GzLog:
    def __init__(self, path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        self.f = gzip.open(path, "at", encoding="utf-8")
        self.events = []            # the most recent, for the summary

    def write(self, ev):
        self.f.write(json.dumps(ev, ensure_ascii=False, separators=(",", ":")) + "\n")
        self.events.append(ev)
        if len(self.events) > 4000:
            del self.events[:2000]

    def close(self):
        self.f.close()


class NullLog:
    """Keeps no file: the most recent events only, for the summary (a long run with --no-frames)."""
    def __init__(self):
        self.events = []

    def write(self, ev):
        self.events.append(ev)
        if len(self.events) > 4000:
            del self.events[:2000]

    def close(self):
        pass


def load(d):
    p = os.path.join(d, "state.json.gz")
    if not os.path.exists(p):
        return None
    with gzip.open(p, "rt", encoding="utf-8") as f:
        return World.from_dict(json.load(f))


def save(w, d):
    p = os.path.join(d, "state.json.gz")
    tmp = p + ".tmp"
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(w.to_dict(), f, separators=(",", ":"))
    os.replace(tmp, p)


def act_detail(w, a):
    """What an act is about, for the viewer's animations: the item gathered or made, the kind built, the
    person followed or struck, the animal hunted ("" if nothing)."""
    if not a:
        return ""
    if a.get("do") == "craft" and a.get("recipe") is not None:
        from .content import RECIPES
        return RECIPES[a["recipe"]]["out"]
    if a.get("do") == "build" and a.get("bid") in w.buildings:
        return w.buildings[a["bid"]].kind
    if a.get("do") == "hunt":
        h = next((h for h in w.herds if h["id"] == a.get("herd")), None)
        return h["kind"] if h else ""
    v = a.get("item") or a.get("kind") or a.get("to") or ""
    return v if isinstance(v, (str, int)) else ""


def frame(w):
    # each person: [id, x, y, health, fullness, verb, detail] (append-only, as land below)
    return {"t": w.tick, "p": [[p.id, p.x, p.y, int(p.health), int(p.satiety), (p.act or {}).get("do", "rest" if p.rest else ""),
                                act_detail(w, p.act)] for p in w.living()],
            "h": [[h["id"], h["kind"], h["x"], h["y"], h["n"]] for h in w.herds],
            "k": [[k["id"], k["x"], k["y"], k["n"]] for k in w.packs]}


def land(w):
    """Once a day, for the viewer: buildings, deposits, piles, and each person's things and skills."""
    # v2 (append-only: readers index these lists by position, so fields are only ever added at the end):
    # buildings add [sown, ripe_at, ripe] of a crop, then how far built (0-1); people add their goal; groups as they stand
    return {"t": w.tick, "kind": "land", "v": 2,
            "b": [[b.id, b.kind, b.x, b.y, b.owner, int(b.done), b.hp, b.inv, b.animals, bool(b.process), b.crop and b.crop.get("what"),
                   b.access, [b.crop.get("sown"), b.crop.get("ripe_at"), bool(b.crop.get("ripe"))] if b.crop else None,
                   1 if b.done else round(min(1.0, b.progress / max(1, BUILDINGS[b.kind]["hours"])), 2)]
                  for b in w.buildings.values()],
            "gr": [[g.id, g.name, g.leader, g.members, g.decide, g.dues, g.treasury, g.laws[-4:], g.founded, g.dissolved, g.rules]
                   for g in w.groups.values() if g.dissolved is None or w.tick - g.dissolved < TPY],
            "d": [[k, d["kind"], d["left"]] for k, d in w.deposits.items()],
            "g": w.piles, "r": sorted(w.roads),
            "people": {str(p.id): [p.inv, {c: round(s, 2) for c, s in p.skills.items() if c in CRAFTS and s > 0}, p.home, p.partner, p.groups,
                                   str((p.intent or {}).get("goal", ""))[:100]]
                       for p in w.living()}}


def summary(w, events, started, stats):
    k = Counter(e["kind"] for e in events if e["t"] >= started)
    deaths = Counter(e.get("cause", "?").split(" by ")[0] for e in events if e["kind"] == "death" and e["t"] >= started)
    top = {}
    for p in w.living():
        for c, s in p.skills.items():
            if c in CRAFTS:
                top[c] = max(top.get(c, 0), s)
    era = max((CRAFTS[c]["era"] for c, s in top.items() if s >= 0.3), default=0)
    L = [f"## civ: {w.when()} of {w.season()}, year {w.year() + 1}",
         f"Advanced {w.tick - started} hours. {len(w.living())} people ({sum(1 for p in w.living() if p.mind == 'llm')} with minds of their own). "
         f"Era {era}. Rules {RULES_VERSION}.",
         f"Decisions: {stats.get('calls', 0)} answered, {stats.get('fails', 0)} failed, {stats.get('fallbacks', 0)} fallbacks, "
         f"{stats.get('slow', 0)} too slow to wait for, {stats.get('stopgaps', 0)} stopgaps while waiting, "
         f"{stats.get('promoted', 0)} took up minds of their own, {stats.get('spent', 0)} asks found every model spent; stopped because: {stats.get('stop')}.",
         f"Births {k['birth']}, deaths {dict(deaths)}; built {k['build']}, made {k['made']}, taught {k['teach']}, "
         f"deals {k['deal']}, trades {k['trade']}, tamed {k['tame']}, groups {k['group']}, attacks {k['attack']}, thefts {k['steal']}.",
         "", "### Said and done"]
    notable = ("monument", "birth", "death", "pledge", "group", "law", "first", "skill", "craft_lost", "teach", "deal", "attack", "say", "write", "book")
    for e in [e for e in events if e["kind"] in notable and e["t"] >= started][-40:]:
        L.append(f"- [{w.when(e['t'])}] {e['text']}")
    return "\n".join(L)


def set_minds(w, n):
    """How many of the living think with a model: the land keeps that many (keep_minds tops it up when one
    dies); any beyond it go on living as bot people, those who have thought longest kept."""
    w.cfg["ai"] = n
    minds = sorted((p for p in w.living() if p.mind == "llm"), key=lambda p: (p.born, p.id))
    for p in minds[n:]:
        p.mind = "bot"
        p.intent = None


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="world2")
    ap.add_argument("--new", action="store_true")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--size", type=int, default=96)
    ap.add_argument("--people", type=int, default=200)
    ap.add_argument("--ai", type=int, default=0)
    ap.add_argument("--bands", type=int, default=0)
    ap.add_argument("--minutes", type=float, default=30)
    ap.add_argument("--ticks", type=int, default=10 ** 9)
    ap.add_argument("--models", default="ollama:gemma4:26b")
    ap.add_argument("--parallel", type=int, default=8)
    ap.add_argument("--bots", action="store_true", help="no model: every mind is a bot")
    ap.add_argument("--minds", type=int, default=None, help="how many think with a model (an existing world too: the rest go on as bots)")
    ap.add_argument("--no-frames", action="store_true", help="write no frames or event logs (a long, fast run; see --history)")
    ap.add_argument("--history", default="", help="append one census line a season to this file (civ/census.py)")
    a = ap.parse_args(argv)
    os.makedirs(a.dir, exist_ok=True)
    w = None if a.new else load(a.dir)
    if w is None:
        w = generate({"seed": a.seed, "width": a.size, "height": a.size, "people": a.people, "ai": 0 if a.bots else a.ai,
                      "bands": a.bands or max(4, a.people // 16)})
    if a.minds is not None:
        set_minds(w, a.minds)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    if a.no_frames:
        events, frames, minds_log = NullLog(), NullLog(), NullLog()
    else:
        events = GzLog(os.path.join(a.dir, "log", f"events-{stamp}.jsonl.gz"))
        frames = GzLog(os.path.join(a.dir, "log", f"frames-{stamp}.jsonl.gz"))
        minds_log = GzLog(os.path.join(a.dir, "log", f"minds-{stamp}.jsonl.gz"))
    census, known = None, set()
    if a.history:
        from .census import Census, append as add_line
        census = Census(events)
        known = {c for p in w.living() for c, v in p.skills.items() if c in CRAFTS and v >= 0.3}
    e = Engine(w, census or events)
    bots = BotMind(e)
    llm = None
    if not a.bots and (w.cfg.get("ai") or any(p.mind == "llm" for p in w.living())):
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from botciv.gateway import Gateway
        from .minds.llm import LLMMind
        from botciv import run as v1
        auto = a.models.strip() == "auto"
        models = v1.DEFAULT_MODELS[:] if auto else [m.strip() for m in a.models.split(",") if m.strip()]
        gw = Gateway(models, quota_path=os.path.join(a.dir, "quota.json"))
        if auto:
            # the free tiers: Flash-Lite, every Gemma big enough, Groq's chat models; each its own allowance
            v1.discover(gw)
            v1.discover_groq(gw)
            print("models:", ", ".join(gw.models))
        llm = LLMMind(e, gw, minds_log, parallel=a.parallel)
        llm.deadline = time.time() + a.minutes * 60

    def decide(people):
        out = bots.decide([p for p in people if p.mind == "bot" or a.bots])
        if llm:
            out.update(llm.decide([p for p in people if p.mind == "llm"]))
        return out

    started = w.tick
    frames.write(land(w))                   # every piece opens with the day as it stands, for the viewer
    end = time.time() + a.minutes * 60
    stop = "time limit"
    try:
        for _ in range(a.ticks):
            if time.time() > end:
                break
            if not w.living():
                stop = "everyone is dead"
                break
            if llm and (llm.silent() or (llm.fails >= 40 and llm.fails > 0.5 * max(1, llm.calls))):
                # the minds are not answering (or every model is spent): stop rather than let the bots
                # carry the land on alone; the next piece looks again
                stop = "the models are spent for now" if llm.spent and llm.silent() else "the model is not answering"
                break
            e.tick(decide)
            if census and w.tick % (TPY // 4) == 0:
                add_line(a.history, census.line(w, known))
            if not a.no_frames:
                frames.write(frame(w))
            if w.hour() == 0:
                if not a.no_frames:
                    frames.write(land(w))
                save(w, a.dir)
        else:
            stop = "tick limit"
    finally:
        if llm:
            llm.close()
        save(w, a.dir)
        for f in (events, frames, minds_log):
            f.close()
    if llm and hasattr(llm.gw, "save"):
        llm.gw.save()                       # what each model spent today, for the next piece
    stats = {"stop": stop, **({"calls": llm.calls, "fails": llm.fails, "fallbacks": llm.fallbacks, "slow": llm.slow,
                                "spent": llm.spent,
                                "stopgaps": llm.stopgaps, "promoted": llm.promoted, "reflexes": llm.reflexes} if llm else {})}
    text = summary(w, events.events, started, stats)
    with open(os.path.join(a.dir, "last_run.md"), "w") as f:
        f.write(text + "\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
