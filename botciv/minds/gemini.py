"""A language-model mind. Each agent is asked alone; nothing another agent
knows ever enters its prompt."""
from concurrent.futures import ThreadPoolExecutor

from ..gateway import OutOfBudget
from ..prompt import build_prompt, response_schema, available_verbs, RULES_VERSION
from .bots import ReciprocityBot


class GeminiMind:
    name = "gemini"

    def __init__(self, engine, gateway, log=None, parallel=6, max_failures=2):
        self.e = engine
        self.gw = gateway
        self.log = log
        self.parallel = parallel
        self.max_failures = max_failures
        self.fallback = ReciprocityBot(engine)
        self.bot_decisions = 0
        self.model_decisions = 0

    def ask(self, a):
        prompt = build_prompt(self.e, a)
        schema = response_schema(available_verbs(self.e, a))
        out, meta = self.gw.generate(prompt, schema, prefer=a.model or None)
        return a, prompt, out, meta

    def decide(self, agents):
        w = self.e.w
        results = {}
        with ThreadPoolExecutor(self.parallel) as ex:
            futs = [ex.submit(self.ask, a) for a in agents]
            done = []
            for f in futs:
                try:
                    done.append(f.result())
                except OutOfBudget:
                    for g in futs:
                        g.cancel()
                    raise
        for a, prompt, out, meta in done:
            a.calls += 1
            rec = {"t": w.tick, "agent": a.id, "name": a.name, "rules": RULES_VERSION, "meta": meta,
                   "wake": list(a.wake)}
            if out is not None:
                a.failures = 0
                if not a.model:
                    a.model = meta.get("model", "")
                results[a.id] = out
                self.model_decisions += 1
                rec["out"] = out
            else:
                a.failures += 1
                if a.failures > self.max_failures:
                    results[a.id] = self.fallback.one(a)
                    rec["bot"] = results[a.id]
                    self.bot_decisions += 1
                else:
                    results[a.id] = {"retry": True}
                    rec["retry"] = True
            if self.log:
                self.log.write(rec, prompt)
        return results
