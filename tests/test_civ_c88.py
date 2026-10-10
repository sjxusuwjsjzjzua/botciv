"""c88: the war leader's view (their band's heart and food, what stands where they march) and the trader's view
(the trades posted at stores they know)."""
import unittest

from civ.engine import Engine
from civ.gen import generate
from civ.prompt import build_prompt
from civ.world import Building, Group


class C88(unittest.TestCase):
    def setUp(self):
        self.w = w = generate({"seed": 6, "people": 16, "width": 60, "height": 60, "bands": 1, "ai": 0})
        self.e = Engine(w)
        self.ad = [p for p in w.living() if p.adult(w.tick)]

    def test_the_war_leader_sees_the_band_and_the_place(self):
        w, lead, men = self.w, self.ad[0], self.ad[1:4]
        g = Group(id=w.new_id(), name="Hall", founder=lead.id, leader=lead.id, members=[lead.id] + [m.id for m in men])
        w.groups[g.id] = g
        for q in [lead] + men:
            q.groups = [g.id]
            w.place(q, 10, 10)
            q.rel[str(lead.id)] = {"trust": 0.6}
            q.inv = {"grain": 4}
        w.bands[1] = {"id": 1, "leader": lead.id, "members": [m.id for m in men], "target": [30, 30], "home": [10, 10],
                      "state": "marching", "since": 0, "fought": 0, "start_power": 0}
        for m in men:
            m.intent = {"band": 1, "plan": [], "goal": ""}
        text = build_prompt(self.e, lead)
        self.assertIn("They are eager", text)
        self.assertIn("would stand against you", text)
        self.assertNotIn("They are eager", build_prompt(self.e, men[0]))

    def test_the_trader_sees_posted_trades(self):
        w, t, o = self.w, self.ad[0], self.ad[1]
        t.vocation = "trader"
        st = Building(id=w.new_id(), kind="store", x=t.x + 2, y=t.y, owner=o.id, done=True)
        st.trade = [{"give": {"dried_berries": 1}, "get": {"grain": 1}}]
        st.inv = {"dried_berries": 3}
        w.buildings[st.id] = st
        text = build_prompt(self.e, t)
        self.assertIn("Trades posted that you know of", text)
        self.assertIn(f"store at ({st.x},{st.y}), 2 steps: gives", text)
        t.vocation = "farmer"
        self.assertNotIn("Trades posted that you know of", build_prompt(self.e, t))


if __name__ == "__main__":
    unittest.main()
