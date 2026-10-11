from copy import deepcopy
import unittest

from tools.planner_p0_v0.shared_world.sabre_export import render_problem
from tools.planner_p0_v0.shared_world.semantics import (
    HORIZON, action_precondition, advance, initial_state, plan_cases, predict_post,
)


class SharedWorldSemanticsTests(unittest.TestCase):
    def test_world_legality_is_separate_from_author_knowledge(self):
        state = initial_state()
        state["now"] = 3
        state["weather"] = "storm"
        move = {"kind": "move", "actor": "A", "from": "junction", "to": "inn"}
        self.assertTrue(action_precondition(state, move)[0])
        state["actors"]["A"]["room"] = "inn"
        state["actors"]["B"]["room"] = "inn"
        self.assertTrue(action_precondition(state, {"kind": "meet", "actors": ["A", "B"]})[0])
        self.assertNotIn("storm", state["actors"]["B"]["known_weather"])

    def test_hour_two_weather_does_not_create_observation(self):
        state = initial_state()
        state["now"] = 1
        tick = advance(state)
        self.assertEqual(tick["after"], 2)
        self.assertTrue(tick["weather_changed"])
        self.assertEqual(state["weather"], "storm")
        self.assertNotIn("storm", state["actors"]["B"]["known_weather"])

    def test_clear_observation_before_hour_two_stays_clear_after_world_tick(self):
        state = initial_state()
        state["now"] = 1
        result = predict_post(state, {"kind": "observe_weather", "actor": "B"})
        self.assertEqual(result["now"], 2)
        self.assertEqual(result["weather"], "storm")
        self.assertIn("clear", result["actors"]["B"]["known_weather"])
        self.assertNotIn("storm", result["actors"]["B"]["known_weather"])

    def test_sunny_meeting_is_legal_but_not_author_success(self):
        state = initial_state()
        state["actors"]["A"]["room"] = "inn"
        state["actors"]["B"]["room"] = "inn"
        action = {"kind": "meet", "actors": ["A", "B"]}
        self.assertTrue(action_precondition(state, action)[0])
        result = predict_post(state, action)
        self.assertFalse(result["met"])
        self.assertEqual(result["weather"], "clear")

    def test_deadline_rejects_even_wait_without_resetting_clock(self):
        state = initial_state()
        state["now"] = HORIZON
        before = deepcopy(state)
        ok, reason = action_precondition(state, {"kind": "wait", "actor": "A"})
        self.assertFalse(ok)
        self.assertEqual(reason, "deadline_reached")
        self.assertEqual(state["now"], before["now"])
        self.assertEqual(state["deadline"], HORIZON)

    def test_export_keeps_receipt_knowledge_and_goal_separate(self):
        state = initial_state()
        text = render_problem(state)
        self.assertNotIn("known_storm(B);", text)
        self.assertIn("known_storm(B) & at(A) == Inn", text)
        self.assertIn("path(Junction, Inn);", text)
        self.assertIn("if(weather() == Storm & known_storm(B)) met_witness()", text)
        self.assertIn("Physical move/meet legality", text)

    def test_hand_cases_include_a_real_side_route_repair(self):
        repair = plan_cases()["mainblockedrepair"]
        self.assertTrue(any(a.get("to") == "side_passage" for a in repair))
        self.assertTrue(any(a.get("to") == "inn" for a in repair))


if __name__ == "__main__":
    unittest.main()
