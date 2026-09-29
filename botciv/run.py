"""Advance a persistent world until the call budget or the time limit runs out.

    python -m botciv.run --dir world --minutes 40 --max-calls 150

The directory holds state.json (the whole world), quota.json (what the gateway
has learned about limits), and log/ with one gzipped events file and one
decisions file per run. Prompts go to a separate file that is not committed.
"""
import argparse
import gzip
import json
import os
import re
import time
from collections import Counter
from datetime import datetime, timezone

from . import config, realized
from .engine import Engine
from .chronicle import write_days
from .gateway import Gateway, OutOfBudget, model_size
from .log import Log
from .minds.gemini import GeminiMind
from .prompt import RULES_VERSION
from .sim import make_bot
from .world import World

# Flash-Lite minds are each person's home; every Gemma the key can reach joins the
# pool (with --models auto), each with its own allowance, and takes whatever calls
# the home models have no room for.
DEFAULT_MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemma-4-31b-it"]
MIN_GEMMA_B = 4             # smaller Gemma models are left out of the pool


# Other text models the free tier may allow a few calls a day each. One that
# allows none is refused on its first call and skipped for the day.
GEMINI_TEXT = re.compile(r"^gemini-\d+(\.\d+)?-(flash|flash-lite|pro)(-preview)?$")


def discover(gw):
    """Add every Gemma of at least MIN_GEMMA_B billion parameters and every plain
    Gemini text model the key can list; each has its own allowance."""
    try:
        names = gw.list_models()
    except Exception as ex:           # listing is a convenience; the defaults still run
        print("could not list models:", type(ex).__name__)
        return []
    gemma = sorted((n for n in names if n.startswith("gemma-") and model_size(n) >= MIN_GEMMA_B
                    and not any(x in n for x in ("embed", "vision", "audio"))),
                   key=lambda n: -model_size(n))
    gemini = sorted(n for n in names if GEMINI_TEXT.match(n))
    gw.add_models(gemma + gemini)
    return gemma + gemini


# Groq's free tier, if a key is set: plain chat models only (the pool wants quick JSON, not reasoning).
GROQ_WANTED = ["llama-3.3-70b-versatile", "meta-llama/llama-4-scout-17b-16e-instruct", "llama-3.1-8b-instant"]


def discover_groq(gw):
    if not gw.groq_key:
        return []
    try:
        names = set(gw.list_groq())
    except Exception as ex:
        print("could not list Groq models:", type(ex).__name__)
        return []
    found = ["groq:" + n for n in GROQ_WANTED if n in names]
    gw.add_models(found)
    return found


class MindLog:
    def __init__(self, decisions_path, prompts_path=None):
        self.d = Log(decisions_path)
        self.p = Log(prompts_path) if prompts_path else None
        self.n = 0

    def write(self, rec, prompt=None):
        self.n += 1
        rec["n"] = self.n
        self.d.write(rec)
        if self.p is not None and prompt is not None:
            self.p.write({"n": self.n, "t": rec["t"], "agent": rec["agent"], "prompt": prompt})

    def close(self):
        self.d.close()
        if self.p:
            self.p.close()


def save_state(w, path):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(w.to_dict(), f, separators=(",", ":"))
    os.replace(tmp, path)


def load_or_create(path, cfg_path, seed=None):
    if os.path.exists(path):
        with open(path) as f:
            w = World.from_dict(json.load(f))
        for a in w.agents.values():
            if a.wants == "to see what lies beyond this land":     # there is no beyond
                a.wants = "to know every corner of the land"
            if not a.wants:
                import random
                from .names import make_want
                a.wants = make_want(random.Random(w.seed * 1000 + a.id))
        return w, False
    over = {"world": {"seed": seed}} if seed is not None else None
    w = World(config.load(cfg_path, over)).generate()
    return w, True


def assign_models(w, models):
    """Each person gets a home mind among the fast models; slow ones are only fallbacks."""
    home = [m for m in models if "gemma" not in m and not m.startswith("groq:")] or models
    for a in w.agents.values():
        if a.alive and a.mind == "gemini" and (not a.model or a.model not in home):
            a.model = home[a.id % len(home)]


def summary(w, log_events, stats, started_tick):
    log_events = [ev for ev in log_events if ev["kind"] != "frame"]
    kinds = Counter(ev["kind"] for ev in log_events)
    L = [f"## botciv: {w.when()} of {w.season()}, year {w.year() + 1}",
         f"Advanced {w.tick - started_tick} hours of world time. Population {len(w.living())}.",
         f"Calls: {stats['calls']} ok by model {stats['by_model']}, bot fallbacks {stats['bots']}, "
         f"retries {stats['retries']}, stopped because: {stats['stop']}.", ""]
    notable = ("death", "birth", "arrive", "group_found", "join", "leave", "expel", "deal", "promise_kept",
               "promise_broken", "steal", "steal_fail", "attack", "craft", "teach", "build", "destroyed",
               "mark", "vote_result", "conceive", "leader", "drought", "storm", "blight")
    L.append("### What happened")
    shown = 0
    for ev in log_events:
        if ev["kind"] in notable and not (ev["kind"] == "craft" and not ev.get("discovery")):
            L.append(f"- [{w.when(ev['t'])}] {ev['text']}")
            shown += 1
            if shown >= 80:
                L.append("- ...")
                break
    says = [ev for ev in log_events if ev["kind"] in ("say", "whisper")]
    if says:
        L.append("\n### Some of what was said")
        step = max(1, len(says) // 15)
        for ev in says[::step][:15]:
            L.append(f"- [{w.when(ev['t'])}] {ev['text']}")
    L.append("\n### Counts\n" + ", ".join(f"{k} {v}" for k, v in kinds.most_common()))
    L.append("\n### People")
    for a in sorted(w.living(), key=lambda a: a.id):
        L.append(f"- **{a.name}** ({a.model or a.mind}) health {a.health}, fullness {a.satiety}, at ({a.x},{a.y}); "
                 f"carries {sum(a.inventory.values())} things; notes: {a.memory[:160]!r}")
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default="world")
    ap.add_argument("--config", default=None)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--minutes", type=float, default=40)
    ap.add_argument("--max-calls", type=int, default=150)
    ap.add_argument("--max-ticks", type=int, default=100000)
    ap.add_argument("--models", default=",".join(DEFAULT_MODELS),
                    help="comma-separated; 'auto' adds every Gemma the key can reach to the defaults")
    ap.add_argument("--mind", default="gemini", help="gemini | simple | reciprocity")
    ap.add_argument("--parallel", type=int, default=10)
    ap.add_argument("--new", action="store_true", help="start a new world even if one exists")
    ap.add_argument("--prompts", action="store_true", help="also save full prompts (not committed)")
    args = ap.parse_args(argv)

    os.makedirs(os.path.join(args.dir, "log"), exist_ok=True)
    state_path = os.path.join(args.dir, "state.json")
    if args.new and os.path.exists(state_path):
        os.replace(state_path, state_path + f".ended-{int(time.time())}")
    w, fresh = load_or_create(state_path, args.config, args.seed)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    events = Log(os.path.join(args.dir, "log", f"events-{stamp}.jsonl.gz"))
    minds_log = MindLog(os.path.join(args.dir, "log", f"minds-{stamp}.jsonl.gz"),
                        os.path.join(args.dir, "prompts", f"prompts-{stamp}.jsonl.gz") if args.prompts else None)
    e = Engine(w, events)
    started = w.tick
    if fresh:
        e.event("world_begins", f"A new world begins (seed {w.seed}, rules {RULES_VERSION})", seed=w.seed)
    for key, who in realized.apply(e):           # ideas this version made real, credited once
        print(f"idea made real: {key}, first known by {who}")
    auto = args.models.strip() == "auto"
    models = DEFAULT_MODELS[:] if auto else [m.strip() for m in args.models.split(",") if m.strip()]
    stats = {"calls": 0, "by_model": {}, "bots": 0, "retries": 0, "stop": "tick limit"}
    if args.mind == "gemini":
        # a few calls beyond the world's budget are kept for the chronicle
        gw = Gateway(models, quota_path=os.path.join(args.dir, "quota.json"), max_calls=args.max_calls + 6)
        if auto:
            found = discover(gw) + discover_groq(gw)
            print("models:", ", ".join(gw.models), f"({len(found)} found by listing)")
        assign_models(w, models)
        mind = GeminiMind(e, gw, minds_log, parallel=args.parallel)
        mind.deadline = time.time() + args.minutes * 60
    else:
        gw = None
        mind = make_bot(args.mind, e)
    deadline = time.time() + args.minutes * 60
    try:
        for _ in range(args.max_ticks):
            if time.time() > deadline:
                stats["stop"] = "time limit"
                break
            if gw and gw.calls >= args.max_calls:
                stats["stop"] = "this run's call budget is spent"
                break
            if not w.living():
                e.arrival()
            try:
                e.tick(mind.decide)
            except OutOfBudget as ex:
                stats["stop"] = str(ex)
                break
            if w.tick % 24 == 0:
                save_state(w, state_path)
                if gw:
                    gw.save()
    finally:
        if hasattr(mind, "close"):
            mind.close()
        save_state(w, state_path)
        events.close()
        minds_log.close()
        if gw:
            gw.stopped = False                     # the minds are done; the chronicle may still call
            try:
                # one call a day of the world; enough per piece to keep up with a fast world
                stats["chronicle_days"] = write_days(args.dir, w, gw, max_days=24)
            except OutOfBudget:
                pass
            except Exception as ex:   # the chronicle must never lose a run
                print("chronicle failed:", type(ex).__name__, ex)
            gw.save()
            for m in gw.models:
                stats["by_model"][m] = gw.today(m)["ok"]
            stats["calls"] = sum(stats["by_model"].values())
            stats["bots"] = mind.bot_decisions
            stats["retries"] = gw.errors
    text = summary(w, events.recent, stats, started)
    print(text)
    with open(os.path.join(args.dir, "last_run.md"), "w") as f:
        f.write(text + "\n")
    out = os.environ.get("GITHUB_STEP_SUMMARY")
    if out:
        with open(out, "a") as f:
            f.write(text + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
