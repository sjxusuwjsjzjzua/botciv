"""civ: the world runs, bots live, the language-model path works with a stand-in model, prompts
stay within budget and never speak of simulations."""
import json
import os
import random
import re
import time
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.minds.bot import BotMind
from civ.minds.llm import LLMMind
from civ.prompt import build_prompt
from civ.world import World, TPD, Building, dist
from civ.content import TERRAIN, DEPOSITS, WILD, BUILDINGS


class FakeGateway:
    """Answers like a model would, after a moment."""
    def __init__(self, delay=0.01, bad=0.0):
        self.delay, self.bad, self.n = delay, bad, 0

    def generate(self, prompt, schema, **kw):
        time.sleep(self.delay)
        self.n += 1
        if random.random() < self.bad:
            return None, {"error": "bad"}
        return {"thought": "I should gather food and wood.", "goal": "provide for myself",
                "plan": [{"do": "gather", "item": "wild grain", "n": 6}, {"do": "gather", "item": "wood", "n": 4},
                         {"do": "build", "kind": "shelter"}], "say": "Good day to you.", "memory": "Build a shelter soon."}, \
               {"model": "fake", "s": self.delay, "in": len(prompt) // 4, "out": 60}


def small(ai=0, people=30, seed=4):
    return generate({"seed": seed, "people": people, "width": 44, "height": 44, "bands": 3, "ai": ai})


class CivWorld(unittest.TestCase):
    def test_saves_and_loads(self):
        w = small()
        e = Engine(w)
        m = BotMind(e)
        for _ in range(TPD * 3):
            e.tick(m.decide)
        again = World.from_dict(json.loads(json.dumps(w.to_dict())))
        self.assertEqual(len(again.living()), len(w.living()))
        self.assertEqual(again.tick, w.tick)

    def test_bots_live_a_season(self):
        w = small(people=40)
        e = Engine(w)
        m = BotMind(e)
        for _ in range(TPD * 10):
            e.tick(m.decide)
        self.assertGreater(len(w.living()), 30)
        self.assertTrue(any(b.done for b in w.buildings.values()))

    def test_llm_minds_answer_and_the_world_goes_on(self):
        w = small(ai=5)
        e = Engine(w)
        bots = BotMind(e)
        llm = LLMMind(e, FakeGateway(), parallel=5)

        def decide(ps):
            out = bots.decide([p for p in ps if p.mind == "bot"])
            out.update(llm.decide([p for p in ps if p.mind == "llm"]))
            return out
        for _ in range(TPD * 2):
            e.tick(decide)
        llm.close()
        ai = [p for p in w.living() if p.mind == "llm"]
        self.assertEqual(len(ai), 5)
        self.assertGreaterEqual(llm.calls, 5)
        self.assertEqual(llm.fails, 0)
        self.assertTrue(any(p.memory == "Build a shelter soon." for p in ai))

    def test_failing_model_falls_back_to_a_bot(self):
        w = small(ai=3)
        e = Engine(w)
        llm = LLMMind(e, FakeGateway(bad=1.0), parallel=3)
        for _ in range(TPD):
            e.tick(lambda ps: llm.decide([p for p in ps if p.mind == "llm"]))
        llm.close()
        self.assertGreater(llm.fallbacks, 0)

    def test_prompt_budget_and_words(self):
        w = small(ai=5, people=40)
        e = Engine(w)
        m = BotMind(e)
        for _ in range(TPD * 6):
            e.tick(m.decide)
        for p in w.living()[:20]:
            text = build_prompt(e, p)
            self.assertLess(len(text), 12000, p.name)          # c47: about 4,000 tokens at most (it was 15,000 characters)
            self.assertIsNone(re.search(r"\b(simulat\w*|agents?|game|turns?|ticks?|bots?|llm|language model)\b", text, re.I),
                              re.findall(r"\b(simulat\w*|agents?|game|turns?|ticks?|bots?|llm|language model)\b", text, re.I)[:3])

    def test_local_models_are_not_paced_like_the_api(self):
        from botciv.gateway import limits_for
        self.assertEqual(limits_for("ollama:gemma4:26b")["rpm"], 100000)
        self.assertEqual(limits_for("gemma-4-31b-it")["rpm"], 28)

    def test_the_land_keeps_its_minds_while_they_answer(self):
        w = small(ai=4)
        e = Engine(w)
        llm = LLMMind(e, FakeGateway(), parallel=2)
        for p in [p for p in w.living() if p.mind == "llm"][:2]:
            e.die(p, "died of old age")
        llm.keep_minds()                                # the model has not shown it answers yet
        self.assertEqual(sum(1 for p in w.living() if p.mind == "llm"), 2)
        llm.calls = 30
        llm.keep_minds()
        llm.close()
        self.assertEqual(sum(1 for p in w.living() if p.mind == "llm"), 4)

    def test_a_slow_model_neither_starves_its_people_nor_floods_the_server(self):
        w = small(ai=12, people=30)
        e = Engine(w)
        bots = BotMind(e)
        llm = LLMMind(e, FakeGateway(delay=0.1), parallel=2, patience=0.05)

        def decide(ps):
            out = bots.decide([p for p in ps if p.mind == "bot"])
            out.update(llm.decide([p for p in ps if p.mind == "llm"]))
            self.assertLessEqual(len(llm.pending), llm.in_flight)
            return out
        for _ in range(TPD * 4):
            e.tick(decide)
        llm.close()
        self.assertGreater(llm.stopgaps, 0)
        self.assertGreater(llm.calls, 8)                # a whole day ahead of an answer, the world waits
        self.assertEqual(sum(1 for p in w.people.values() if p.mind == "llm" and not p.alive), 0)

    def test_asking_to_learn_gets_a_lesson(self):
        w = small()
        e = Engine(w)
        a, b = w.living()[0], w.living()[1]
        b.x, b.y = a.x, a.y
        b.skills["pottery"], a.skills["pottery"] = 0.8, 0.0
        e.start(a, {"do": "propose", "to": b.name, "learn": "pottery"})
        x = next(x for x in w.offers.values() if x["from"] == a.id)
        self.assertIn(f"{b.name} teaches {a.name} pottery", e.offer_text(x, None))
        self.assertTrue(e.start(b, {"do": "accept", "offer": x["id"]})[0])
        for _ in range(8):
            e.run_person(b)
            e.run_person(a)
        self.assertGreaterEqual(a.skill("pottery"), 0.3)

    def test_people_whose_minds_forget_food_do_not_starve(self):
        class Forgetful(FakeGateway):
            def generate(self, prompt, schema, **kw):
                ans, meta = super().generate(prompt, schema, **kw)
                ans["plan"] = [{"do": "gather", "item": "wood", "n": 30}, {"do": "gather", "item": "stone", "n": 30}]
                return ans, meta
        w = small(ai=10, people=30)
        e = Engine(w)
        bots = BotMind(e)
        llm = LLMMind(e, Forgetful(delay=0.005), parallel=4)

        def decide(ps):
            out = bots.decide([p for p in ps if p.mind == "bot"])
            out.update(llm.decide([p for p in ps if p.mind == "llm"]))
            return out
        for _ in range(TPD * 12):
            e.tick(decide)
        llm.close()
        self.assertGreater(llm.reflexes, 0)
        self.assertEqual([p.name for p in w.people.values() if p.cause == "starved"], [])

    def test_take_walks_to_a_pile_further_off(self):
        w = small()
        e = Engine(w)
        p = w.living()[0]
        spot = next((x, y) for x, y in w.beside(p.x, p.y, 3) if w.passable(x, y) and not w.building_at(x, y)
                    and max(abs(x - p.x), abs(y - p.y)) == 3)
        w.piles[f"{spot[0]},{spot[1]}"] = {"bone": 2}
        ok, why = e.start(p, {"do": "take", "item": "bone", "x": spot[0], "y": spot[1]})
        self.assertTrue(ok, why)
        for _ in range(12):
            if p.act:
                e.run_person(p)
        self.assertEqual(p.inv.get("bone"), 2)

    def test_striking_a_known_thief_is_just_and_kin_remember_a_killing(self):
        w = small()
        e = Engine(w)
        p, o, x, k = [q for q in w.living() if q.adult(w.tick)][:4]
        for q, dx in ((p, 0), (o, 1), (x, 2), (k, 30)):
            w.place(q, p.x + dx if q is not p else p.x, p.y)
        # o robbed p; x, a friend of p, sees p strike o: no grudge against p
        e.trust(p, o, -0.3, ("robbed", f"{o.name} took 3 grain from your store"))
        e.trust(x, p, 0.3)
        e.start(p, {"do": "attack", "to": o.name})
        e.run_person(p)
        self.assertFalse(any(q[2] == "saw_attack" and q[1] == p.id for q in x.ledger))
        self.assertIn("took 3 grain from your store", build_prompt(e, p))
        # a killing: the dead one's kin hold it against the killer
        e.rel(k, o)["kin"] = "brother"
        if o.alive:
            e.die(o, "killed", by=p)
        self.assertTrue(e.wrong_known(k, p))
        # a stranger striking without cause is held against them
        y = next(q for q in w.living() if q.adult(w.tick) and q not in (p, x, k))
        w.place(y, x.x + 1, x.y)
        e.start(y, {"do": "attack", "to": x.name})
        e.run_person(y)
        self.assertTrue(any(q[2] == "saw_attack" and q[1] == y.id for q in p.ledger))

    def test_a_bot_warns_off_one_who_robs_it_then_may_strike(self):
        w = small()
        e = Engine(w)
        p, o = [q for q in w.living() if q.adult(w.tick)][:2]
        w.place(o, p.x + 1, p.y)
        p.traits["boldness"] = 1.0
        p.health = o.health = 10
        e.trust(p, o, -0.3, ("robbed", f"{o.name} took 3 grain from your store"))
        m = BotMind(e)
        got = m.guard(p)
        self.assertIn("mine", got["say"])
        self.assertIsNone(m.guard(p))               # the same theft is not answered twice
        w.tick += 1
        e.trust(p, o, -0.3, ("robbed", f"{o.name} took 2 grain from your store"))
        hits = 0
        for _ in range(20):
            got = m.guard(p)
            hits += bool(got and got["plan"][0]["do"] == "attack")
        self.assertGreater(hits, 0)

    def test_post_walks_to_ones_store_and_fishing_is_planned_only_where_it_pays(self):
        w = small()
        e = Engine(w)
        p = w.living()[0]
        x, y = next((x, y) for x, y in w.beside(p.x, p.y, 6) if dist(p.x, p.y, x, y) >= 4 and w.passable(x, y)
                    and not w.building_at(x, y))
        st = Building(id=w.new_id(), kind="store", x=x, y=y, owner=p.id, done=True)
        w.buildings[st.id] = st
        w.at[f"{x},{y}"] = st.id
        ok, why = e.start(p, {"do": "post", "x": x, "y": y, "give": {"pot": 1}, "get": {"grain": 3}})
        self.assertTrue(ok, why)
        for _ in range(20):
            if p.act:
                e.run_person(p)
        self.assertEqual(st.trade, [{"give": {"pot": 1}, "get": {"grain": 3}}])
        from civ.plan import Planner
        pl = Planner(e)
        p.inv = {}
        got = pl.get(p, "fish", 2, 0, set())
        self.assertIsNone(got)                       # bare hands: a day's fishing is unlikely to bring two
        p.inv["net"] = 1
        got = pl.get(p, "fish", 2, 0, set())
        if got is not None:
            self.assertLessEqual(got[0]["hours"], 12)

    def test_forgiving_steps_hunt_for_hide_and_any_game_and_wood_for_a_fire(self):
        w = small()
        e = Engine(w)
        p = next(q for q in w.living() if q.adult(w.tick) and e.herds_of(q))
        ok, why = e.start(p, {"do": "gather", "item": "hide", "n": 2})
        self.assertTrue(ok, why)
        self.assertEqual((p.act["do"], p.act.get("keep")), ("hunt", "hide"))
        p.act = None
        kinds = {h["kind"] for h in e.herds_of(p)}
        other = next((k for k in ("aurochs", "boar", "deer", "horse", "wild_goat", "sheep") if k not in kinds), None)
        if other:
            ok, why = e.start(p, {"do": "hunt", "animal": other})
            self.assertTrue(ok, why)

    def test_a_hunt_where_the_game_is_hunted_out_says_where_herds_are_left(self):
        w = small()
        e = Engine(w)
        p = next(q for q in w.living() if q.adult(w.tick))
        p.known = {k: v for k, v in p.known.items() if not k.startswith("herd")}
        far = w.herds[0]
        w.herds = [far]
        east = p.x + 30 < w.w                    # 30 steps off, beyond tracks, whichever side has room
        far["x"], far["y"] = (p.x + 30 if east else p.x - 30), p.y
        ok, why = e.start(p, {"do": "hunt", "animal": far["kind"]})
        self.assertFalse(ok)
        self.assertIn("hunted out", why)
        self.assertIn("east" if east else "west", why)
        w.herds = []
        ok, why = e.start(p, {"do": "hunt"})
        self.assertIn("gone from the land", why)

    def test_the_daily_snapshot_keeps_groups_goals_and_crops_for_the_viewer(self):
        from civ.run import land
        from civ.world import Group
        w = small()
        e = Engine(w)
        p = w.living()[0]
        g = Group(id=w.new_id(), name="Hearth", founder=p.id, leader=p.id, members=[p.id], dissolved=w.tick)
        w.groups[g.id] = g
        p.intent = {"goal": "lay food by", "plan": []}
        snap = json.loads(json.dumps(land(w)))
        self.assertEqual(snap["v"], 2)
        self.assertEqual(snap["gr"][0][1], "Hearth")
        self.assertEqual(snap["people"][str(p.id)][5], "lay food by")

    def test_drop_sets_down_what_is_carried_and_is_quiet_about_what_is_not(self):
        w = small()
        e = Engine(w)
        p = w.living()[0]
        p.inv = {"wood": 3}
        ok, why = e.start(p, {"do": "drop", "item": "wood", "n": 2})
        self.assertTrue(ok, why)
        self.assertEqual(p.inv.get("wood"), 1)
        ok, why = e.start(p, {"do": "drop", "item": "bone"})
        self.assertTrue(ok, why)

    def test_a_full_store_of_ones_own_takes_the_rest_beside_it(self):
        w = small()
        e = Engine(w)
        p = w.living()[0]
        st = Building(id=w.new_id(), kind="shelter", x=p.x + 1, y=p.y, owner=p.id, done=True, inv={"stone": 15})
        w.buildings[st.id] = st
        w.at[f"{st.x},{st.y}"] = st.id
        p.inv = {"wood": 4}
        ok, why = e.start(p, {"do": "put", "item": "wood", "x": st.x, "y": st.y})
        self.assertTrue(ok, why)
        for _ in range(5):
            if p.act:
                e.run_person(p)
        self.assertFalse(p.inv.get("wood"))
        self.assertEqual(w.piles.get(f"{st.x},{st.y}", {}).get("wood"), 4)

    def test_a_cairn_carries_its_words_to_those_who_pass(self):
        w = small()
        e = Engine(w)
        p, o = w.living()[0], w.living()[1]
        p.inv["stone"] = 4
        ok, why = e.start(p, {"do": "build", "kind": "cairn", "name": "Mother's cairn", "text": "Here we remember her."})
        self.assertTrue(ok, why)
        for _ in range(12):
            if p.act:
                e.run_person(p)
        b = next(b for b in w.buildings.values() if b.kind == "cairn")
        self.assertTrue(b.done)
        self.assertEqual(b.text, "Here we remember her.")
        w.place(o, b.x + 1, b.y)
        self.assertIn('carved: "Here we remember her."', build_prompt(e, o))
        self.assertTrue(any(x["kind"] == "monument" for x in e.log.events))

    def test_an_answer_without_a_plan_goes_on_with_the_old_one(self):
        class Talker(FakeGateway):
            def generate(self, prompt, schema, **kw):
                ans, meta = super().generate(prompt, schema, **kw)
                assert "Your plan, still to do: gather clay 5; craft pot" in prompt
                return {"thought": "Answer and keep at it.", "goal": "pottery", "say": "Gladly."}, meta
        w = small(ai=1)
        e = Engine(w)
        p = next(q for q in w.living() if q.mind == "llm")
        p.intent = {"goal": "pottery", "plan": [{"do": "gather", "item": "clay", "n": 5}, {"do": "craft", "item": "pot"}]}
        p.wake = ["Someone spoke to you"]
        llm = LLMMind(e, Talker(), parallel=1, max_lag=0)
        out = {}
        for _ in range(20):
            out = llm.decide([p])
            if out:
                break
            time.sleep(0.02)
        llm.close()
        e.adopt(p, out[p.id])
        self.assertEqual([s["do"] for s in p.intent["plan"]], ["gather", "craft"])

    def test_wolves_leave_alone_one_inside_a_shelter(self):
        from civ.world import Building, TPD
        w = small()
        e = Engine(w)
        p = next(q for q in w.living() if q.adult(w.tick))
        far = next((x, y) for y in range(w.h) for x in range(w.w) if w.passable(x, y) and dist(x, y, p.x, p.y) > 15)
        for o in w.living():
            if o is not p:
                w.place(o, *far)
        b = Building(id=w.new_id(), kind="shelter", x=p.x, y=p.y, owner=p.id, done=True)
        w.buildings[b.id] = b
        w.at[f"{p.x},{p.y}"] = b.id
        w.packs = [{"id": 1, "x": p.x + 1, "y": p.y, "n": 4, "hunger": 5}]
        w.tick = (w.tick // TPD) * TPD + TPD - 2      # night, an hour the wolves move in
        self.assertTrue(w.is_night())
        self.assertIsNone(e.hearth_near(p))
        h = p.health
        for _ in range(40):
            e.wolves()
        self.assertEqual(p.health, h)
        del w.at[f"{p.x},{p.y}"], w.buildings[b.id]  # out in the open, the same night: bitten
        for _ in range(40):
            e.wolves()
        self.assertLess(p.health, h)

    def test_slaughtering_a_wild_beast_one_does_not_keep_hunts_it(self):
        w = small()
        e = Engine(w)
        p = next(q for q in w.living() if q.adult(w.tick) and e.herds_of(q))
        kind = e.herds_of(p)[0]["kind"]
        ok, why = e.start(p, {"do": "slaughter", "animal": kind})
        self.assertTrue(ok, why)
        self.assertEqual(p.act["do"], "hunt")
        p.act = None
        ok, why = e.start(p, {"do": "slaughter", "animal": "pig"})
        self.assertFalse(ok)
        self.assertIn("you keep no pig", why)

    def test_sowing_with_no_seed_carried_fetches_it_from_ones_store(self):
        from civ.world import Building
        w = small()
        e = Engine(w)
        p = next(q for q in w.living() if q.adult(w.tick))
        p.inv.pop("seeds", None); p.inv.pop("grain", None)
        free = [(x, y) for x, y in w.beside(p.x, p.y, 3) if w.passable(x, y) and not w.building_at(x, y)]
        for kind, (x, y), inv in (("store", free[0], {"grain": 6}), ("farm", free[1], {})):
            b = Building(id=w.new_id(), kind=kind, x=x, y=y, owner=p.id, done=True, inv=inv)
            w.buildings[b.id] = b
            w.at[f"{x},{y}"] = b.id
        p.intent = {"goal": "sow", "plan": []}
        self.assertNotEqual(w.season(), "winter")
        ok, why = e.start(p, {"do": "plant", "item": "grain"})
        self.assertTrue(ok, why)
        self.assertEqual(p.act["do"], "take")
        self.assertEqual(p.intent["plan"][0]["do"], "plant")
        self.assertTrue(p.intent["plan"][0]["fetched"])

    def test_gathering_grain_leaves_a_strangers_field_alone(self):
        from civ.world import Building
        w = small()
        e = Engine(w)
        p, o = w.living()[0], w.living()[1]
        x, y = next((x, y) for x, y in w.beside(p.x, p.y) if w.passable(x, y) and not w.building_at(x, y))
        b = Building(id=w.new_id(), kind="farm", x=x, y=y, owner=o.id, done=True, inv={"grain": 20})
        w.buildings[b.id] = b
        w.at[f"{x},{y}"] = b.id
        self.assertNotEqual(e.find(p, "grain", far=False), (x, y))
        ok, why = e.start(p, {"do": "gather", "item": "grain", "x": x, "y": y})     # named: meant
        self.assertTrue(ok, why)
        self.assertEqual(p.act["spot"], [x, y])

    def test_stone_is_never_sought_in_the_heart_of_a_mountain(self):
        # c42: world2's most refused step was "no way to the stone at (41, 48)", a mountain tile ringed by mountain
        w = small()
        e = Engine(w)
        w.terrain = ["." * w.w for _ in range(w.h)]
        for y in range(33, 38):
            w.terrain[y] = w.terrain[y][:33] + "^" * 5 + w.terrain[y][38:]
        p = w.living()[0]
        p.x, p.y = 30, 30
        x, y = e.find(p, "stone")
        self.assertTrue(any(w.passable(i, j) for i, j in w.beside(x, y)), (x, y))
        self.assertNotEqual((x, y), (35, 35))
        # far beyond the usual search: the refusal says where the nearest reachable stone is, and that spot can be walked to
        p.x, p.y = 2, 2
        ok, why = e.start(p, {"do": "gather", "item": "stone"})
        self.assertFalse(ok)
        self.assertIn("steps away", why)
        fx, fy = map(int, why.split("at (")[1].split(")")[0].split(", "))
        self.assertTrue(any(w.passable(i, j) for i, j in w.beside(fx, fy)))
        ok, why = e.start(p, {"do": "gather", "item": "stone", "x": fx, "y": fy})
        self.assertTrue(ok, why)

    def test_a_long_run_keeps_a_census_a_season_and_no_logs(self):
        # the long land (botworld.yml): no frames or event logs in the fast part, one census line a season
        import tempfile
        from civ import run as runner
        from civ.world import TPY
        d = tempfile.mkdtemp()
        hist = os.path.join(d, "history.jsonl")
        runner.main(["--dir", d, "--new", "--bots", "--people", "30", "--size", "44", "--seed", "4",
                     "--no-frames", "--history", hist, "--ticks", str(TPY // 2), "--minutes", "5"])
        self.assertFalse(os.path.exists(os.path.join(d, "log")))
        with open(hist) as f:
            lines = [json.loads(x) for x in f]
        self.assertEqual(len(lines), 2)
        self.assertEqual({"alive", "births", "deaths", "era", "able", "firsts", "buildings", "gini"} - set(lines[-1]), set())
        self.assertGreater(lines[-1]["alive"], 20)
        from civ.site import history
        self.assertEqual(len(history(d)), 2)

    def test_a_go_step_with_x_and_no_y_does_not_break_the_prompt(self):
        # 2026-10-03: a model wrote {"do": "go", "x": 5}; building the next prompt crashed every piece
        from civ.prompt import build_prompt, step_text
        self.assertEqual(step_text({"do": "go", "x": 5}), "go")
        w = small()
        e = Engine(w)
        p = w.living()[0]
        p.intent = {"goal": "", "plan": [{"do": "go", "x": 5}]}
        self.assertTrue(build_prompt(e, p))         # no KeyError

    def test_dues_fill_a_common_store_members_may_use(self):
        from civ.world import Building, Group, TPD
        w = small()
        e = Engine(w)
        lead, mem = [q for q in w.living() if q.adult(w.tick)][:2]
        g = Group(id=w.new_id(), name="Hearth", founder=lead.id, leader=lead.id, members=[lead.id, mem.id])
        w.groups[g.id] = g
        lead.groups.append(g.id)
        mem.groups.append(g.id)
        st = Building(id=w.new_id(), kind="store", x=lead.x, y=lead.y + 1, owner=lead.id, done=True)
        w.buildings[st.id] = st
        w.at[f"{st.x},{st.y}"] = st.id
        mine = Building(id=w.new_id(), kind="store", x=mem.x + 1, y=mem.y, owner=mem.id, done=True, inv={"grain": 5})
        w.buildings[mine.id] = mine
        w.at[f"{mine.x},{mine.y}"] = mine.id
        lead.inv["grain"] = 4
        ok, why = e.start(lead, {"do": "set_dues", "group": "Hearth", "give": [{"item": "grain", "qty": 2}], "x": st.x, "y": st.y})
        self.assertTrue(ok, why)
        self.assertEqual(st.owner, -g.id)
        self.assertTrue(w.may_use(mem, st))
        while not (w.hour() == 0 and w.day() % 10 == 0):
            w.tick += 1
        e.society_tick()
        self.assertEqual(st.inv.get("grain"), 4)          # the leader from hand, the member from their store
        self.assertEqual(mine.inv.get("grain"), 3)

    def test_map_symbols_are_unique(self):
        syms = list(TERRAIN) + [v["sym"] for k, v in DEPOSITS.items() if k != "bog_iron"] + [v["sym"] for v in WILD.values()] + \
            [v["sym"] for v in BUILDINGS.values()]
        self.assertEqual(len(syms), len(set(syms)))


if __name__ == "__main__":
    unittest.main()
