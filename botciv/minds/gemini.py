"""A language-model mind. Each agent is asked alone; nothing another agent
knows ever enters its prompt.

Asking does not hold the world still for long. Each hour the mind waits up to
`patience` seconds for answers; a person whose answer is slower keeps doing
what they were doing and their decision applies when it arrives, but no answer
may fall more than `max_lag` hours behind: then the world waits for it. So one
slow model does not idle the others, and a slow thinker never misses more than
a few hours. Prompts are built here, between hours, never in a worker thread
while the world moves.
"""
import time
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

from ..gateway import OutOfBudget
from ..prompt import build_prompt, response_schema, available_verbs, RULES_VERSION
from .bots import ReciprocityBot


class GeminiMind:
    name = "gemini"

    def __init__(self, engine, gateway, log=None, parallel=6, max_failures=2, patience=10.0, max_lag=3):
        self.e = engine
        self.gw = gateway
        self.log = log
        self.parallel = parallel
        self.max_failures = max_failures
        self.patience = patience
        self.max_lag = max_lag
        self.fallback = ReciprocityBot(engine)
        self.bot_decisions = 0
        self.model_decisions = 0
        self.ex = ThreadPoolExecutor(parallel)
        self.deadline = None        # when the run must end; a wait for answers past it ends the piece
        self.pending = {}           # agent id -> (future, tick asked, wake reasons then, prompt)

    def ask(self, prompt, schema, prefer):
        return self.gw.generate(prompt, schema, prefer=prefer)

    def decide(self, agents):
        w = self.e.w
        for a in agents:
            if a.id not in self.pending:
                prompt = build_prompt(self.e, a)
                schema = response_schema(available_verbs(self.e, a))
                fut = self.ex.submit(self.ask, prompt, schema, a.model or None)
                self.pending[a.id] = (fut, w.tick, list(a.wake), prompt)
        deadline = time.time() + self.patience
        while self.pending:
            futs = [p[0] for p in self.pending.values()]
            if all(f.done() for f in futs):
                break
            overdue = any(w.tick - t >= self.max_lag for f, t, _, _ in self.pending.values() if not f.done())
            left = deadline - time.time()
            if left <= 0 and not overdue:
                break
            if self.deadline and time.time() > self.deadline:
                self.gw.stop()
                raise OutOfBudget("time limit reached while waiting for answers")
            wait([f for f in futs if not f.done()], timeout=max(0.05, left) if not overdue else 1.0,
                 return_when=FIRST_COMPLETED)
        results = {}
        asking = {a.id: a for a in agents}
        for aid, (fut, t0, wake0, prompt) in list(self.pending.items()):
            if not fut.done():
                if aid in asking:
                    results[aid] = {"pending": True}
                continue
            del self.pending[aid]
            try:
                out, meta = fut.result()
            except OutOfBudget:
                for f, *_ in self.pending.values():
                    f.cancel()
                self.pending.clear()
                raise
            a = w.agents.get(aid)
            if a is None or not a.alive:
                continue
            results[aid] = self.record(a, out, meta, t0, wake0, prompt)
        return results

    def record(self, a, out, meta, t0, wake0, prompt):
        w = self.e.w
        a.calls += 1
        rec = {"t": t0, "agent": a.id, "name": a.name, "rules": RULES_VERSION, "meta": meta, "wake": wake0}
        if w.tick != t0:
            rec["applied"] = w.tick
        if out is not None:
            a.failures = 0
            if not a.model:
                a.model = meta.get("model", "")
            d = dict(out)
            self.model_decisions += 1
            rec["out"] = out
        else:
            a.failures += 1
            if a.failures > self.max_failures:
                d = self.fallback.one(a)
                rec["bot"] = d
                self.bot_decisions += 1
            else:
                d = {"retry": True}
                rec["retry"] = True
        if self.log:
            self.log.write(rec, prompt)
        d["asked"] = {"t": t0, "wake": wake0}
        return d

    def close(self):
        """Wait for answers still out and apply them, so no call is wasted or left
        running when the run ends; the world is saved after this."""
        if hasattr(self.gw, "stop"):
            self.gw.stop()                  # calls still waiting for room give up; answers in flight still land
        for aid, (fut, t0, wake0, prompt) in list(self.pending.items()):
            try:
                out, meta = fut.result()
            except Exception:
                continue
            a = self.e.w.agents.get(aid)
            if a is not None and a.alive:
                self.e.apply_decision(a, self.record(a, out, meta, t0, wake0, prompt))
        self.pending.clear()
        self.ex.shutdown(wait=True, cancel_futures=True)
