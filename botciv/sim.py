"""Run a world with rule-based minds. Used for tuning and tests."""
from .engine import Engine
from .minds.bots import SimpleBot, ReciprocityBot, PlannerBot, RaiderBot, MixedBot


def make_bot(kind, engine):
    return {"simple": SimpleBot, "reciprocity": ReciprocityBot, "planner": PlannerBot, "raider": RaiderBot, "mixed": MixedBot}[kind](engine)


def run_bots(world, ticks, kind="simple", log=None, stats_every=None):
    e = Engine(world, log)
    bot = make_bot(kind, e)
    calls = 0
    series = []
    for _ in range(ticks):
        asked = e.tick(bot.decide)
        calls += len(asked)
        if stats_every and world.tick % stats_every == 0:
            series.append((world.tick, len(world.living())))
    return e, calls, series
