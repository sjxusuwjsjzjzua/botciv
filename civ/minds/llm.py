"""People whose choices come from a language model. The world does not wait for them: a person
keeps doing what they were doing while their next choice is being thought out, and the world
holds still only when an answer is more than `max_lag` hours late, and then only for `patience`
seconds for that answer. At most `in_flight` asks are out at once (more would only queue at the
server and come back stale); the urgent go first, then whoever has gone longest without. A person
who is hungry, or idle while waiting their turn, does the obvious thing until the answer comes."""
import time
from concurrent.futures import ThreadPoolExecutor

from ..acts import VERBS
from ..prompt import build_prompt, SCHEMA, RULES_VERSION
from .bot import BotMind

URGENT = ("attacked", "offer", "spoke", "hungry", "died", "broke", "gave you", "taught you", "invited", "vote")


class LLMMind:
    def __init__(self, engine, gateway, log=None, parallel=8, max_lag=2, min_gap=3, patience=240):
        self.e = engine
        self.w = engine.w
        self.gw = gateway
        self.log = log
        self.pool = ThreadPoolExecutor(parallel)
        self.pending = {}           # pid -> (future, tick asked, wake reasons, prompt length)
        self.max_lag = max_lag
        self.min_gap = min_gap
        self.patience = patience    # seconds the world waits for one late answer before giving up on it
        self.bot = BotMind(engine)
        self.deadline = None
        self.calls = self.fails = self.fallbacks = 0
        self.in_flight = 2 * parallel   # asks out at once: more only queue at the server and grow stale
        self.excused = set()            # asks so late the world stopped waiting for them
        self.slow = self.stopgaps = self.promoted = 0

    def ask(self, prompt):
        return self.gw.generate(prompt, SCHEMA, temperature=0.9)

    def decide(self, people):
        w = self.w
        out = {}
        if w.hour() == 0:
            self.keep_minds()
        # who wants to think: the urgent first, then whoever has gone longest without
        want = []
        for p in people:
            if p.mind != "llm" or p.id in self.pending:
                continue
            urgent = any(k in why for why in p.wake for k in URGENT)
            if not urgent and w.tick - p.last_decided < self.min_gap and p.intent is not None:
                continue                            # asked a moment ago: let them be a little
            want.append((not urgent, p.last_decided, p.id, p))
        want.sort(key=lambda t: t[:3])
        room = max(0, self.in_flight - len(self.pending))
        for _, _, _, p in want[:room]:
            prompt = build_prompt(self.e, p)
            self.pending[p.id] = (self.pool.submit(self.ask, prompt), w.tick, list(p.wake), len(prompt), time.time(), len(p.events))
        # those thinking or waiting their turn with nothing to do, or hungry, do the obvious meanwhile
        for _, _, _, p in want[room:]:
            self.stopgap(p, out)
        for pid in self.pending:
            p = w.people.get(pid)
            if p and p.alive and pid not in out:
                self.stopgap(p, out, only_hungry=True)
        # the world waits for answers in flight that have fallen too far behind, each for a while
        while True:
            late = [pid for pid, (f, t0, *_rest) in self.pending.items()
                    if not f.done() and w.tick - t0 >= self.max_lag and pid not in self.excused]
            if not late:
                break
            if self.deadline and time.time() > self.deadline:
                break
            now = time.time()
            for pid in late:
                if now - self.pending[pid][4] > self.patience:
                    self.excused.add(pid)       # this one is very late: go on without it (applied when it comes)
                    self.slow += 1
                    p = w.people.get(pid)
                    if p and p.alive and p.act is None and not (p.intent or {}).get("plan"):
                        self.stopgap(p, out, force=True)
            time.sleep(0.05)
        for pid, (f, t0, wake, n, started, seen) in list(self.pending.items()):
            if not f.done():
                continue
            del self.pending[pid]
            self.excused.discard(pid)
            p = w.people.get(pid)
            if not p or not p.alive:
                continue
            self.calls += 1
            try:
                ans, meta = f.result()
            except Exception as ex:
                ans, meta = None, {"error": f"{type(ex).__name__}: {str(ex)[:100]}"}
            intent = self.intent(ans)
            if intent is None:
                self.fails += 1
                p.failures += 1
                if p.failures >= 2:
                    self.fallbacks += 1
                    intent = self.bot.one(p)
                    intent["fallback"] = True
                else:
                    self.e.wake(p, "think again")
                    continue
            else:
                p.failures = 0
                p.calls += 1
            intent["events_seen"] = min(seen, len(p.events))
            out[pid] = intent
            if self.log:
                self.log.write({"t": t0, "applied": w.tick, "id": pid, "name": p.name, "rules": RULES_VERSION,
                                "model": (meta or {}).get("model"), "s": (meta or {}).get("s"), "tin": (meta or {}).get("in"),
                                "tout": (meta or {}).get("out"), "wake": wake, "chars": n,
                                "thought": (ans or {}).get("thought", "") if ans else "", "goal": intent.get("goal"),
                                "plan": intent.get("plan"), "say": intent.get("say"), "to": intent.get("to"),
                                "fallback": bool(intent.get("fallback")),
                                **({"error": str((meta or {}).get("error"))[:160]} if intent.get("fallback") else {})})
        return out

    def stopgap(self, p, out, only_hungry=False, force=False):
        """While a person waits to think, the obvious: food when hungry, else (when idle) what a
        sensible neighbour would do. Their reasons to think again are kept."""
        idle = p.act is None and not (p.intent or {}).get("plan")
        if p.satiety <= 8 and p.act is None:
            got = self.bot.hunger(p)
        elif (idle and not only_hungry) or force:
            wake = list(p.wake)
            got = self.bot.one(p)
            p.wake = wake                   # the bot's choosing clears them; they are still owed a thought
        else:
            return
        if got:
            got["keep_wake"] = True
            out[p.id] = got
            self.stopgaps += 1

    def keep_minds(self):
        """Keep the land's share of minds of its own while the model answers well: when one dies,
        a grown bot takes up the place, a child of the dead first. A few a day at most."""
        if self.calls < 20 or self.fails > 0.2 * self.calls:
            return
        w = self.w
        want = w.cfg.get("ai", 0)
        have = sum(1 for p in w.living() if p.mind == "llm")
        if have >= want:
            return
        dead = {p.id for p in w.people.values() if not p.alive and p.mind == "llm"}
        cands = [p for p in w.living() if p.mind == "bot" and 16 <= p.age(w.tick) <= 45]
        cands.sort(key=lambda p: (not (set(p.parents) & dead), -len(p.skills), p.id))
        for p in cands[:min(3, want - have)]:
            p.mind = "llm"
            p.failures = 0
            p.wake.append("think again")
            self.promoted += 1

    @staticmethod
    def intent(ans):
        if not isinstance(ans, dict):
            return None
        plan = []
        for s in ans.get("plan") or []:
            if isinstance(s, dict) and str(s.get("do", "")).lower() in VERBS:
                s = {k: v for k, v in s.items() if v not in (None, "", [], {})}
                s["do"] = s["do"].lower()
                plan.append(s)
        if not plan and not ans.get("say"):
            return None
        out = {"goal": str(ans.get("goal", ""))[:200], "plan": plan[:8], "routine": bool(ans.get("routine"))}
        for k in ("say", "to", "memory", "life", "idea", "beliefs"):
            if ans.get(k):
                out[k] = ans[k]
        if not plan:
            out["plan"] = [{"do": "wait", "hours": 1}]
        return out

    def close(self):
        for pid, (f, *_rest) in list(self.pending.items()):
            f.cancel()
        self.pending.clear()
        self.pool.shutdown(wait=False, cancel_futures=True)
