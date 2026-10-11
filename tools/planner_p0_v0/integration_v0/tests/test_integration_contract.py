"""Offline tests for Sabre projection, typed monitoring, and result boundaries."""
import unittest

from tools.planner_p0_v0.integration_v0.monitor import (
    classify_native_step, classify_planner_result, evaluate_native_trace,
)
from tools.planner_p0_v0.integration_v0.sabre_export import render_problem, _delivery_costs


def snapshot(*, mode="direct", now=0, main=True, weather="clear", pending=None,
             task=None, holder=None, known_b=()):
    rooms = {"junction": 101, "side_passage": 102, "inn": 103}
    actors = {
        "A": {"room_id": 101, "inventory_ids": [], "known_weather": [],
              "own_goal": "deliver_shelter", "active_task": task,
              "local_view": {"observation": {
                  "room_id": 101, "task_item": {"id": "501", "key": "shelter_kit"} if task else None,
                  "task_destination": 103 if task else None,
                  "known_exits": {"101": [103, 102], "102": [101, 103], "103": [101, 102]},
                  "known_traversability": {},
                  "exits": [{"key": "main", "destination_id": 103, "traversable": main}],
                  "item_location": 101, "item_held": holder == "A", "delivered": False}}},
        "B": {"room_id": 101, "inventory_ids": [], "known_weather": list(known_b),
              "own_goal": None, "active_task": None},
        "player": {"room_id": 101, "inventory_ids": [], "known_weather": [],
                    "own_goal": None, "active_task": None},
    }
    routes = [
        {"id": "main", "edges": [
            {"from": "junction", "to": "inn", "traversable": main},
            {"from": "inn", "to": "junction", "traversable": main}]},
        {"id": "side", "edges": [
            {"from": "junction", "to": "side_passage", "traversable": True},
            {"from": "side_passage", "to": "junction", "traversable": True},
            {"from": "side_passage", "to": "inn", "traversable": True},
            {"from": "inn", "to": "side_passage", "traversable": True}]},
    ]
    return {"schema": "planner-p0-integration-v0", "scene_id": "fixture", "mode": mode,
            "clock": {"now": now, "deadline": 24, "unit": "minute"},
            "weather": weather, "pending_cloud": pending, "rooms": rooms,
            "actors": actors, "items": {"shelter_kit": {
                "id": 501, "location_id": 102 if holder else 101, "holder_role": holder}},
            "routes": routes, "ledger_frontier": 0, "sealed_through": now}


def row(seq, kind, source, minute, args, *, actor=None):
    return {"sequence": seq, "event_id": f"scene:{seq}", "minute": minute,
            "event_type": kind, "source": source, "driver": "direct_driver",
            "request_id": f"req-{seq}", "actor": actor, "action": None,
            "accepted": True, "settled": True, "code": None,
            "receipt_id": f"receipt-{seq}", "typed_args": args}


def trace(events, *, now=8, frontier=None, sealed=None):
    return {"scene_id": "scene", "snapshot": {"clock": {"now": now}},
            "events": events, "ledger_frontier": len(events) if frontier is None else frontier,
            "sealed_through": now if sealed is None else sealed}


class IntegrationContractTests(unittest.TestCase):
    def test_cost_table_is_exact_for_main_and_side_route_and_uses_actor_known_item(self):
        open_main = snapshot(task={"status": "accepted"})
        blocked_main = snapshot(task={"status": "accepted"}, main=False)
        self.assertEqual(_delivery_costs(open_main)["junction"], 3)  # GET + main MOVE + DROP
        self.assertEqual(_delivery_costs(blocked_main)["junction"], 4)  # GET + two side MOVEs + DROP
        blocked_main["actors"]["A"]["local_view"]["observation"]["item_location"] = None
        self.assertIsNone(_delivery_costs(blocked_main)["junction"])

    def test_mode_permission_projection_and_belief_nonleakage(self):
        direct = render_problem(snapshot(mode="direct", weather="storm"))
        conditional = render_problem(snapshot(mode="conditional"))
        free = render_problem(snapshot(mode="free"))
        self.assertIn("character_actions_allowed();", direct)
        self.assertNotIn("consenting:", direct)  # direct is joint control, not NPC consent
        self.assertIn("consenting: A, B;", conditional)
        self.assertNotIn("character_actions_allowed();", free)
        self.assertNotIn("author_actions_allowed();", free)
        self.assertNotIn("knows_storm(B);", direct)  # world storm is not B's observation
        self.assertIn("action dispatch_task()", direct)
        self.assertNotIn("direct_control_allowed();", conditional)
        self.assertNotIn("offerable();", direct)

    def test_numeric_clock_cloud_due_and_macro_trigger_are_explicit(self):
        problem = render_problem(snapshot(mode="direct", pending={"seeded_at": 4, "due_at": 6}, now=5))
        self.assertIn("cloud_due() = 6;", problem)
        self.assertIn("now() >= cloud_due()", problem)
        self.assertIn("cloud_due() = now() + 2", problem)
        self.assertIn("now() = now() + delivery_cost(source)", problem)

    def test_unreachable_macro_has_no_zero_cost_grounding(self):
        s = snapshot(task={"status": "accepted"}, main=False)
        s["actors"]["A"]["local_view"]["observation"]["item_location"] = None
        problem = render_problem(s)
        self.assertNotIn("delivery_feasible(Junction);", problem)
        self.assertNotIn("delivery_cost(Junction) = 0;", problem)
        self.assertIn("delivery_feasible(source)", problem)

    def test_typedir_accepts_only_native_receipts_and_checks_order(self):
        events = [
            row(1, "TASK_OFFER", "authorized_author_action", 0, {"accepted": True}),
            row(2, "WEATHER_OBSERVED", "native_evennia_readback", 2,
                {"actor": "B", "room": "inn", "weather": "storm"}, actor="B"),
            row(3, "DROP_SETTLED", "native_evennia_readback", 3,
                {"actor": "A", "item": "shelter_kit", "room": "inn"}, actor="A"),
            row(4, "MEETING_WITNESS", "native_meet_command", 4,
                {"actors": ["A", "B"], "room": "inn", "weather": "storm",
                 "B_observed_storm": True}, actor="A"),
        ]
        report = evaluate_native_trace(trace(events, now=24))
        self.assertEqual(report["status"], "SATISFIED")
        self.assertNotIn("scene:1", report["projected_receipts"])
        self.assertEqual(len(report["projected_receipts"]), 3)
        reversed_events = [events[0], dict(events[3], minute=2),
                           dict(events[2], minute=3), dict(events[1], minute=4)]
        reversed_events = [dict(e, sequence=i + 1) for i, e in enumerate(reversed_events)]
        ordered = evaluate_native_trace(trace(reversed_events, now=24))
        self.assertEqual(ordered["status"], "VIOLATED")

    def test_partial_or_missing_middle_ledger_row_cannot_prove_absence_or_completion(self):
        events = [row(1, "TASK_OFFER", "authorized_author_action", 0, {}),
                  row(3, "DROP_SETTLED", "native_evennia_readback", 3,
                      {"actor": "A", "item": "shelter_kit", "room": "inn"}, actor="A")]
        report = evaluate_native_trace(trace(events, frontier=3, sealed=8))
        self.assertEqual(report["status"], "INDETERMINATE")
        self.assertFalse(report["complete_ledger_prefix"])
        missing_seal = trace(events[:1], frontier=1, sealed=None)
        missing_seal.pop("sealed_through")
        self.assertEqual(evaluate_native_trace(missing_seal)["status"], "INDETERMINATE")

    def test_search_budget_native_no_plan_and_native_denials_are_distinct(self):
        self.assertEqual(classify_planner_result({"status": "BUDGET_LIMIT"}), "SEARCH_BUDGET")
        self.assertEqual(classify_planner_result({"status": "NATIVE_NO_SOLUTION"}), "NO_PLAN_IN_EXPORTED_DOMAIN")
        self.assertEqual(classify_planner_result({"status": "PROCESS_TIMEOUT"}), "WRAPPER_TIMEOUT")
        self.assertEqual(classify_native_step({"code": "ACL_DENIED"}), "ACL_DENIED")
        self.assertEqual(classify_native_step({"code": "ILLEGAL_ACTION"}), "ILLEGAL_ACTION")
        self.assertEqual(classify_native_step({"code": "EXECUTION_FAILURE"}), "EXECUTION_FAILURE")


if __name__ == "__main__":
    unittest.main()
