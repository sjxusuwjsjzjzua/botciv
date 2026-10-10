"""c83: tenancy: a field worked for a share of each harvest, the share brought to the owner's store as it is reaped."""
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.minds.bot import BotMind
from civ.prompt import build_prompt
from civ.society import share_part, share_text
from civ.world import Building, TPD


class C83(unittest.TestCase):
    def setUp(self):
        self.w = w = generate({"seed": 6, "people": 16, "width": 40, "height": 40, "bands": 1, "ai": 0})
        self.e = Engine(w)
        adults = [p for p in w.living() if p.adult(w.tick)]
        self.lord, self.ten = adults[0], next(p for p in adults[1:] if p.id != adults[0].partner)
        x, y = self.lord.x, self.lord.y
        for q in (self.lord, self.ten):
            w.place(q, x, y)
            q.inv, q.act, q.intent, q.satiety = {}, None, {"goal": "", "plan": []}, 16
        self.field = Building(id=w.new_id(), kind="farm", x=x + 1, y=y, owner=self.lord.id, done=True)
        self.store = Building(id=w.new_id(), kind="store", x=x, y=y + 1, owner=self.lord.id, done=True)
        for b in (self.field, self.store):
            w.buildings[b.id] = b
            w.at[f"{b.x},{b.y}"] = b.id

    def let(self, share="third"):
        ok, why = self.e.start(self.lord, {"do": "propose", "to": self.ten.name, "kind": "tenancy", "x": self.field.x,
                                           "y": self.field.y, "share": share, "days": 20})
        self.assertTrue(ok, why)
        oid = next(i for i, x in self.w.offers.items() if x["to"] == self.ten.id)
        ok, why = self.e.start(self.ten, {"do": "accept", "offer": oid})
        self.assertTrue(ok, why)
        return self.w.tenancies[-1]

    def test_the_tenant_may_use_the_field_and_its_owner_is_paid_as_it_is_reaped(self):
        self.assertFalse(self.w.may_use(self.ten, self.field))
        t = self.let()
        self.assertTrue(self.w.may_use(self.ten, self.field))
        self.field.inv = {"grain": 30}
        self.field.crop = {"what": "grain", "ripe": True, "yield": 30, "by": self.ten.id}
        self.ten.inv["grain"] = 9
        self.e.tenant_reaped(self.ten, self.field, "grain", 9)
        self.assertEqual(self.store.inv.get("grain"), 3)
        self.assertEqual(self.ten.inv.get("grain"), 6)
        self.assertEqual(t["paid"], 3)
        self.assertTrue(any(e["kind"] == "tenancy" for e in self.e.log.events))

    def test_what_finds_no_room_is_owed_and_becomes_a_promise_at_the_end(self):
        t = self.let("half")
        self.store.inv = {"stone": 1000}                # full
        self.ten.inv = {"grain": 10}
        self.e.tenant_reaped(self.ten, self.field, "grain", 10)
        self.assertEqual(self.ten.inv["grain"], 10)
        self.w.tick = t["until"]
        self.e.society_tick()
        self.assertTrue(t["done"])
        pr = self.w.promises[-1]
        self.assertEqual((pr["by"], pr["to"], pr["goods"]), (self.ten.id, self.lord.id, {"grain": 5}))

    def test_the_owner_reaping_what_the_tenant_sowed_is_a_wrong(self):
        self.let()
        self.field.inv = {"grain": 20}
        self.field.crop = {"what": "grain", "ripe": True, "yield": 20, "by": self.ten.id}
        self.lord.act = {"do": "gather", "item": "grain", "want": 5, "got": 0, "left": 4, "spot": [self.field.x, self.field.y], "theirs": False}
        self.e.do_gather(self.lord, self.lord.act)
        self.assertTrue(any(e[2] == "took_crop" for e in self.ten.ledger))

    def test_both_see_it(self):
        self.let()
        self.assertIn(f"You work {self.lord.name}'s field at ({self.field.x},{self.field.y}), a third", build_prompt(self.e, self.ten))
        self.assertIn(f"{self.ten.name} works your field", build_prompt(self.e, self.lord))

    def test_only_a_field_of_either(self):
        other = Building(id=self.w.new_id(), kind="farm", x=self.field.x, y=self.field.y + 3, owner=-99, done=True)
        self.w.buildings[other.id] = other
        self.w.at[f"{other.x},{other.y}"] = other.id
        ok, why = self.e.start(self.lord, {"do": "propose", "to": self.ten.name, "kind": "tenancy", "x": other.x, "y": other.y})
        self.assertFalse(ok)

    def test_shares_as_written(self):
        self.assertEqual([round(share_part(v), 2) for v in ("third", "a half", "1/4", 0.25, "25%", 40, None, "lots")],
                         [0.33, 0.5, 0.25, 0.25, 0.25, 0.4, 0.33, 0.33])
        self.assertEqual(share_text(1 / 3), "a third")

    def test_bots_work_the_field_they_rent_and_not_the_one_they_let(self):
        bot = BotMind(self.e)
        self.assertEqual(bot.fields(self.lord), [self.field])
        self.let()
        self.assertEqual(bot.fields(self.ten), [self.field])
        self.assertEqual(bot.fields(self.lord), [])
        x = {"kind": "tenancy", "field": self.field.id, "tenant": self.ten.id, "share": 1 / 3}
        self.assertFalse(bot.worth_it(self.ten, self.lord, x))      # has a field now



class Shape(unittest.TestCase):
    def test_the_verb_comes_first_and_every_field_is_ordered(self):
        from civ.prompt import SCHEMA, STEP
        self.assertEqual(STEP["propertyOrdering"][:4], ["do", "to", "who", "task"])
        self.assertEqual(sorted(STEP["propertyOrdering"]), sorted(STEP["properties"]))
        self.assertEqual(sorted(SCHEMA["propertyOrdering"]), sorted(SCHEMA["properties"]))

    def test_a_place_at_nought_nought_is_no_place(self):
        from civ.minds.llm import LLMMind
        got = LLMMind.intent({"thought": "t", "goal": "g", "plan": [{"do": "order", "to": "all", "x": 0, "y": 0},
                                                                      {"do": "go", "x": 0, "y": 5}]})
        self.assertEqual(got["plan"][0], {"do": "order", "to": "all"})
        self.assertEqual(got["plan"][1], {"do": "go", "x": 0, "y": 5})


if __name__ == "__main__":
    unittest.main()
