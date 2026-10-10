import copy
import unittest
from tools.trajectory_constraints_v0.types import StableEntity

from tools.native_platform_v0.p5.bundle import load_bundle
from tools.native_platform_v0.p5.planning import NO_OP, plan


def raw_goal(kind="event_by_deadline", *, event="delivery_settled", filters=None,
             observable=None, args=None, deadline=20, hard=True):
    if kind == "event_by_deadline":
        goal = {"id": "g", "kind": kind, "event": event, "filters": filters or {"actor": "A", "item": "courier_supply"},
                "start": 0, "deadline": deadline, "hard": hard}
    else:
        goal = {"id": "g", "kind": kind, "observable": observable, "args": args,
                "value": True, "start": 0, "deadline": deadline, "hard": hard}
    return {"schema": "native-author-bundle-v1", "bundle_id": "planner", "version": 1, "source": "test",
            "constraints": [goal], "branches": [],
            "permissions": {"world_opportunities": ["open_main_passage", "open_side_passage"],
                            "force_npc_response": False, "max_opportunities": 1, "cost_budget": 2}}


def state(*, now=0, deadline_horizon=24, main_open=False, main_available=True, main_cost=1,
          main_minutes=2, spent=0, verdict="PENDING"):
    return {"now": now, "horizon": deadline_horizon,
            "routes": [{"id": "main_passage", "opportunity_id": "open_main_passage", "open": main_open,
                        "available": main_available, "cost": main_cost, "min_minutes": main_minutes, "resource": None},
                       {"id": "side_passage", "opportunity_id": "open_side_passage", "open": False,
                        "available": True, "cost": 1, "min_minutes": 3, "resource": None}],
            "spent_cost": spent, "opportunities_used": 0,
            "verdicts": [{"constraint_id": "g", "status": verdict}], "physical_budget": 2}


class PlanningTests(unittest.TestCase):
    def test_hard_deadline_is_checked_not_only_global_horizon(self):
        result = plan(load_bundle(raw_goal(deadline=6)), state(deadline_horizon=24, main_minutes=7))
        candidate = next(c for c in result["candidates"] if c["route_id"] == "main_passage")
        self.assertFalse(candidate["feasible"])
        self.assertIn("g", candidate["unmet_hard_constraints"])

    def test_holding_goal_is_not_claimed_supported_by_opening_a_door(self):
        bundle = load_bundle(raw_goal("state_by_deadline", observable="holding",
                                      args={"actor": "A", "item": "courier_supply"}))
        result = plan(bundle, state())
        self.assertEqual(result["selected_action"], NO_OP)
        candidate = next(c for c in result["candidates"] if c["route_id"] == "main_passage")
        self.assertNotIn("g", candidate["supported_hard_constraints"])
        self.assertEqual(candidate["goal_support"][0]["support"], "UNSUPPORTED_BY_THIS_ACTION")

    def test_route_open_goal_selects_only_matching_registered_opportunity(self):
        bundle = load_bundle(raw_goal("state_by_deadline", observable="route_open", args={"route": "main_passage"}))
        result = plan(bundle, state())
        self.assertEqual(result["selected_action"], "open_main_passage")
        main = next(c for c in result["candidates"] if c["route_id"] == "main_passage")
        side = next(c for c in result["candidates"] if c["route_id"] == "side_passage")
        self.assertTrue(main["feasible"])
        self.assertNotIn("g", side["supported_hard_constraints"])

    def test_soft_goal_does_not_gate_a_hard_opportunity(self):
        raw = raw_goal(deadline=20, hard=True)
        soft = raw_goal("state_by_deadline", observable="route_open", args={"route": "side_passage"}, hard=False)
        soft_goal = copy.deepcopy(soft["constraints"][0])
        soft_goal["id"] = "soft-side"
        raw["constraints"].append(soft_goal)
        result = plan(load_bundle(raw), state())
        self.assertEqual(result["selected_action"], "open_side_passage")
        candidate = next(c for c in result["candidates"] if c["route_id"] == "main_passage")
        self.assertEqual(candidate["soft_unmet_penalties"], ["soft-side"])
        self.assertIn("g", candidate["supported_hard_constraints"])

    def test_parallel_resident_delivery_does_not_block_courier_route_opportunity(self):
        raw = raw_goal(deadline=20)
        resident = raw_goal(event="delivery_settled", filters={"actor": "B", "item": "resident_parcel"})
        resident_goal = copy.deepcopy(resident["constraints"][0])
        resident_goal["id"] = "resident-delivery"
        raw["constraints"].append(resident_goal)
        result = plan(load_bundle(raw), state())
        self.assertIn(result["selected_action"], {"open_main_passage", "open_side_passage"})
        candidate = next(c for c in result["candidates"] if c["action"] == result["selected_action"])
        resident_row = next(row for row in candidate["goal_support"]
                            if row["constraint_id"] == "resident-delivery")
        self.assertTrue(resident_row["parallel_unaffected"])
        self.assertNotIn("resident-delivery", candidate["supported_hard_constraints"])

    def test_shared_supply_b_delivery_uses_the_same_parallel_task_boundary(self):
        raw = raw_goal(deadline=20)
        shared_goal = raw_goal(event="delivery_settled", filters={"actor": "B", "item": "courier_supply"})
        row = copy.deepcopy(shared_goal["constraints"][0])
        row["id"] = "shared-supply-B-delivery"
        raw["constraints"].append(row)
        result = plan(load_bundle(raw), state())
        self.assertIn(result["selected_action"], {"open_main_passage", "open_side_passage"})
        selected = next(c for c in result["candidates"] if c["action"] == result["selected_action"])
        shared = next(g for g in selected["goal_support"]
                      if g["constraint_id"] == "shared-supply-B-delivery")
        self.assertEqual(shared["support"], "PARALLEL_NPC_OBLIGATION")
        self.assertNotIn("shared-supply-B-delivery", selected["supported_hard_constraints"])

    def test_opening_route_cannot_repair_violated_goal_or_break_route_must_stay_closed(self):
        closed_raw = raw_goal("state_by_deadline", observable="route_open", args={"route": "main_passage"})
        closed_raw["constraints"][0]["value"] = False
        closed_goal = load_bundle(closed_raw)
        result = plan(closed_goal, state())
        self.assertEqual(result["selected_action"], NO_OP)
        route = next(c for c in result["candidates"] if c["route_id"] == "main_passage")
        self.assertFalse(route["feasible"])

        open_goal = load_bundle(raw_goal("state_by_deadline", observable="route_open",
                                         args={"route": "main_passage"}))
        violated = plan(open_goal, state(verdict="VIOLATED"))
        self.assertEqual(violated["selected_action"], NO_OP)
        self.assertTrue(any(row["code"] == "HARD_EVIDENCE_NOT_ACTIONABLE"
                            for row in violated["diagnostics"]))

    def test_interaction_and_main_route_hard_goal_choose_main_not_side(self):
        raw = raw_goal(event="note_response", filters={"actor": "A", "recipient": "B", "item": "note",
                                                       "response": "rejected"})
        route = raw_goal("state_by_deadline", observable="route_open", args={"route": "main_passage"})
        route_goal = copy.deepcopy(route["constraints"][0])
        route_goal["id"] = "main-open"
        raw["constraints"].append(route_goal)
        result = plan(load_bundle(raw), state())
        self.assertEqual(result["selected_action"], "open_main_passage")
        side = next(c for c in result["candidates"] if c["route_id"] == "side_passage")
        self.assertFalse(side["feasible"])
        self.assertIn("main-open", side["unmet_hard_constraints"])

    def test_conflicting_main_and_side_hard_goals_yield_no_op(self):
        raw = raw_goal("state_by_deadline", observable="route_open", args={"route": "main_passage"})
        side = raw_goal("state_by_deadline", observable="route_open", args={"route": "side_passage"})
        side_goal = copy.deepcopy(side["constraints"][0])
        side_goal["id"] = "side-open"
        raw["constraints"].append(side_goal)
        result = plan(load_bundle(raw), state())
        self.assertEqual(result["selected_action"], NO_OP)
        self.assertTrue(any(row["code"] == "NO_SUPPORTED_HARD_PATH" for row in result["diagnostics"]))

    def test_role_aliases_survive_scene_specific_stable_entity_ids(self):
        raw = raw_goal()
        entities = {"A": StableEntity("Actor", "evennia:actor:101"),
                    "B": StableEntity("Actor", "evennia:actor:202"),
                    "note": StableEntity("Item", "evennia:item:303"),
                    "courier_supply": StableEntity("Item", "evennia:item:404"),
                    "resident_parcel": StableEntity("Item", "evennia:item:505")}
        bundle = load_bundle(raw, entities=entities)
        result = plan(bundle, state())
        self.assertIn(result["selected_action"], {"open_main_passage", "open_side_passage"})

    def test_existing_open_route_is_no_op_preferred_over_spending_on_side_route(self):
        result = plan(load_bundle(raw_goal(event="note_response", filters={
            "actor": "A", "recipient": "B", "item": "note", "response": "rejected"})),
            state(main_open=True))
        self.assertEqual(result["selected_action"], NO_OP)
        main = next(c for c in result["candidates"] if c["route_id"] == "main_passage")
        side = next(c for c in result["candidates"] if c["route_id"] == "side_passage")
        self.assertEqual(main["incremental_cost"], 0)
        self.assertEqual(main["projected_cost"], 0)
        self.assertEqual(side["incremental_cost"], 1)
        self.assertEqual(main["supported_hard_constraints"], ["g"])

    def test_expansion_budget_exhaustion_is_not_reported_complete(self):
        result = plan(load_bundle(raw_goal()), state(), max_expansions=2)
        self.assertEqual(result["status"], "SEARCH_INCOMPLETE")
        self.assertFalse(result["candidate_set_complete"])
        self.assertFalse(result["optimality_claim"])
        self.assertTrue(any(row["code"] == "SEARCH_BUDGET_EXHAUSTED" for row in result["diagnostics"]))

    def test_immediate_main_route_activation_fits_tight_direct_route_deadline(self):
        raw = raw_goal("state_by_deadline", observable="route_open", args={"route": "main_passage"},
                       deadline=2)
        result = plan(load_bundle(raw), state(now=1, deadline_horizon=2, main_minutes=2))
        self.assertEqual(result["selected_action"], "open_main_passage")
        main = next(c for c in result["candidates"] if c["route_id"] == "main_passage")
        support = main["goal_support"][0]
        self.assertEqual(support["opportunity_settlement_lower_bound"], 1)
        self.assertIsNone(support["dependent_task_lower_bound"])
        self.assertTrue(support["deadline_lower_bound_fits"])

    def test_event_order_dependency_is_explicit_and_not_a_generic_route_claim(self):
        raw = raw_goal()
        raw["constraints"] = [{"id": "order", "kind": "event_order",
            "before": {"event": "delivery_settled", "filters": {"actor": "A", "item": "courier_supply"}},
            "after": {"event": "note_response", "filters": {"actor": "A", "recipient": "B", "item": "note"}},
            "order": "PHYSICAL_TIME", "start": 0, "deadline": 20, "hard": True}]
        result = plan(load_bundle(raw), state())
        self.assertEqual(result["selected_action"], "open_main_passage")
        self.assertEqual(result["and_or_graph"]["dependencies"][0]["before"], "p5_delivery_settled")
        raw["constraints"][0]["before"]["event"] = "note_response"
        result = plan(load_bundle(raw), state())
        self.assertEqual(result["selected_action"], NO_OP)

    def test_delivery_is_conditional_not_guaranteed_and_no_action_is_retained(self):
        result = plan(load_bundle(raw_goal()), state())
        self.assertIn(result["selected_action"], {"open_main_passage", "open_side_passage"})
        self.assertTrue(all(not row.get("outcome_guaranteed", True)
                            for candidate in result["candidates"] for row in candidate.get("goal_support", [])))
        self.assertEqual(result["candidates"][0]["action"], NO_OP)
        self.assertFalse(result["prediction_guarantee"])


if __name__ == "__main__":
    unittest.main()
