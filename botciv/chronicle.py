"""The daily chronicle: a short history of each finished world-day.

One model call per day with notable events. Every sentence must cite event
ids from that day; a checker drops any sentence citing an unknown id or
naming a person who appears in none of its cited events. So the chronicle
cannot drift into fiction about the world.
"""
import glob
import json
import os
import re

from .log import read

NOTABLE = {"death", "birth", "arrive", "group_found", "join", "leave", "expel", "deal", "promise_kept",
           "promise_broken", "steal", "steal_fail", "attack", "attack_miss", "craft", "teach", "build", "destroyed",
           "mark", "vote_call", "vote_result", "conceive", "leader", "drought", "storm", "blight", "say", "whisper",
           "give", "hunt", "invite", "refuse", "propose", "smash", "take_store", "ask_child", "plant", "ripe",
           "world_begins", "group_end", "hire", "service_end", "service_left", "dismiss", "post", "trade", "make", "sick", "mend", "claim"}

SCHEMA = {"type": "OBJECT", "properties": {
    "title": {"type": "STRING"},
    "sentences": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": {
        "text": {"type": "STRING"}, "cites": {"type": "ARRAY", "items": {"type": "INTEGER"}}},
        "required": ["text", "cites"]}}},
    "required": ["title", "sentences"]}

PROMPT = """You keep the chronicle of a small band of people living on a patch of land. Below are the recorded events of day {day} ({season}, year {year}), one per line, each with its number.

Write a short, plain history of the day: at most {n} sentences, the way a chronicler would, choosing what mattered (conflict, alliances, promises kept or broken, births, deaths, discoveries, things said that reveal intentions). Do not invent anything. Each sentence must cite the numbers of the events it rests on, and must only name people who appear in those cited events. Give the day a short title.

Earlier chronicle, for continuity:
{earlier}

Events:
{events}"""


def load_events(world_dir):
    evs = []
    for p in sorted(glob.glob(os.path.join(world_dir, "log", "events-*.jsonl.gz"))):
        evs.extend(e for e in read(p) if e.get("kind") not in ("frame", "census"))
    return evs


def check(sentences, by_id, names):
    kept, dropped = [], 0
    for s in sentences:
        text = str(s.get("text", "")).strip()
        cites = [c for c in s.get("cites", []) if isinstance(c, int)]
        if not text or not cites or any(c not in by_id for c in cites):
            dropped += 1
            continue
        cited_text = " ".join(by_id[c]["text"] for c in cites)
        named = {n for n in names if re.search(rf"\b{re.escape(n)}\b", text)}
        if any(not re.search(rf"\b{re.escape(n)}\b", cited_text) for n in named):
            dropped += 1
            continue
        kept.append({"text": text, "cites": cites})
    return kept, dropped


def write_days(world_dir, world, gateway, max_days=6, model=None):
    path = os.path.join(world_dir, "chronicle.jsonl")
    done = []
    if os.path.exists(path):
        with open(path) as f:
            done = [json.loads(l) for l in f if l.strip()]
    last = max((c["day"] for c in done), default=0)
    tpd = world.tpd()
    today = world.tick // tpd + 1
    events = load_events(world_dir)
    names = sorted({a.name for a in world.agents.values()}, key=len, reverse=True)
    written = 0
    for day in range(last + 1, today):
        if written >= max_days:
            break
        evs = [e for e in events if (e["t"] // tpd) + 1 == day and e["kind"] in NOTABLE]
        if not evs:
            continue
        if len(evs) > 120:
            talk = [e for e in evs if e["kind"] in ("say", "whisper")]
            rest = [e for e in evs if e["kind"] not in ("say", "whisper")]
            evs = sorted(rest[:90] + talk[:: max(1, len(talk) // 30)][:30], key=lambda e: e["id"])
        by_id = {e["id"]: e for e in evs}
        d0 = day - 1
        dps = world.cfg["world"]["days_per_season"]
        season = ["spring", "summer", "autumn", "winter"][(d0 // dps) % 4]
        earlier = "\n".join(f"Day {c['day']}: {c['text']}" for c in done[-3:]) or "(none: this is the beginning)"
        prompt = PROMPT.format(day=day, season=season, year=d0 // (dps * 4) + 1, n=min(10, 3 + len(evs) // 8),
                               earlier=earlier, events="\n".join(f"[{e['id']}] {e['text']}" for e in evs))
        out, meta = gateway.generate(prompt, SCHEMA, prefer=model, temperature=0.7)
        if not out:
            break
        kept, dropped = check(out.get("sentences", []), by_id, names)
        entry = {"day": day, "season": season, "title": str(out.get("title", ""))[:80],
                 "text": " ".join(s["text"] for s in kept), "sentences": kept, "dropped": dropped,
                 "model": meta.get("model")}
        done.append(entry)
        with open(path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        written += 1
    return written
