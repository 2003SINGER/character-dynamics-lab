import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools.native_platform_v0.p5.bundle import load_bundle
from tools.native_platform_v0.p5.mature_methods.method_adapters import snapshot_from_native
from tools.native_platform_v0.p5.mature_methods.narrative_methods import plan_high_level
from tools.native_platform_v0.p5.mature_methods.narrative_methods import _support_method
from tools.native_platform_v0.p5.mature_methods.orchestrator import advance_from_sealed


def raw_bundle():
    return {
        "schema": "native-author-bundle-v1", "bundle_id": "mature-methods-test",
        "version": 1, "source": "unit-test",
        "constraints": [
            {"id": "deliver-A", "kind": "event_by_deadline", "event": "delivery_settled",
             "filters": {"actor": "A", "item": "courier_supply"},
             "start": 0, "deadline": 12, "hard": True},
            {"id": "deliver-B", "kind": "event_by_deadline", "event": "delivery_settled",
             "filters": {"actor": "B", "item": "resident_parcel"},
             "start": 0, "deadline": 12, "hard": True},
            {"id": "note-response", "kind": "event_by_deadline", "event": "note_response",
             "filters": {"actor": "A", "recipient": "B", "item": "note", "response": "rejected"},
             "start": 0, "deadline": 12, "hard": True},
            {"id": "A-before-note", "kind": "event_order",
             "before": {"event": "delivery_settled", "filters": {"actor": "A", "item": "courier_supply"}},
             "after": {"event": "note_response", "filters": {"actor": "A", "recipient": "B", "item": "note"}},
             "order": "PHYSICAL_TIME", "start": 0, "deadline": 12, "hard": True},
        ],
        "branches": [],
        "permissions": {"world_opportunities": ["open_main_passage", "open_side_passage"],
                        "force_npc_response": False, "max_opportunities": 1, "cost_budget": 2},
    }


def native_evidence(bundle, *, now=0, state_override=None, typed_events=None,
                    supply_location=101):
    from tools.native_platform_v0.p5.mature_methods.method_adapters import _canonical_sha
    verdicts = [{"constraint_id": goal.constraint_id, "status": "PENDING", "hard": goal.hard}
                for goal in bundle.goals]
    state = state_override or {
        "now": now, "horizon": 12,
        "routes": [
            {"id": "main_passage", "opportunity_id": "open_main_passage", "open": False,
             "available": True, "cost": 1, "min_minutes": 2, "resource": None},
            {"id": "side_passage", "opportunity_id": "open_side_passage", "open": False,
             "available": True, "cost": 1, "min_minutes": 3, "resource": None}],
        "spent_cost": 0, "opportunities_used": 0,
        "verdicts": [{"constraint_id": row["constraint_id"], "status": row["status"]}
                     for row in verdicts], "physical_budget": 2}
    typed_trace = {"events": typed_events or [], "events_sealed_through": str(now),
                   "value_frontiers": {"v": str(now)}}
    binding = {"schema": "p5-planner-scene-binding-v1", "scene_id": "scene-test",
               "source": "native_platform_v0.p5.service._planner_scene_binding",
               "room_roles": {"pickup": 101, "side": 102, "porch": 103},
               "task_bindings": {
                   "A": {"actor_id": 301, "item_alias": "courier_supply", "item_id": 201,
                         "destination_id": 103, "source": "existing_scene_actor_binding"},
                   "B": {"actor_id": 302, "item_alias": "resident_parcel", "item_id": 202,
                         "destination_id": 103, "source": "existing_scene_actor_binding"}}}
    return {
        "evidence_schema": "p5-live-trace-v1", "source": "native_platform_v0.p5.service._evidence",
        "prefix_status": "SEALED_COMPLETE", "bundle_identity": {"bundle_id": bundle.bundle_id,
                                                                  "version": bundle.version,
                                                                  "sha256": _canonical_sha(bundle.raw)},
        "scene_id": "scene-test", "now": now, "horizon": 12,
        "complete_through": {"events": now, "values": now}, "run_status": "INCOMPLETE",
        "verdicts": {"constraints": verdicts}, "typed_trace": typed_trace,
        "ledger": [],
        "actor_evidence": [{"actor_alias": "A", "actor_id": 301, "pending_action": None,
                             "native_receipts": []},
                            {"actor_alias": "B", "actor_id": 302, "pending_action": None,
                             "native_receipts": []}],
        "world_snapshots": [{"minute": minute, "routes": {"main_passage": False,
                                                                 "side_passage": False},
                             "holders": {"courier_supply": {"A": False, "B": False},
                                         "resident_parcel": {"A": False, "B": False}},
                             "item_locations": {"courier_supply": supply_location,
                                                "resident_parcel": 101}}
                            for minute in range(now + 1)],
        "world_capability_projection": binding,
        "planning_view": {"schema": "p5-native-planning-view-v1",
                          "source": "native_platform_v0.p5.service._director_planning_view",
                          "scene_id": "scene-test", "based_on_minute": now,
                          "bundle_identity": {"bundle_id": bundle.bundle_id, "version": bundle.version,
                                              "sha256": _canonical_sha(bundle.raw)},
                          "frontiers": {"events_through": now, "values_through": now},
                          "state": state},
    }


class MatureMethodTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import gtpyhop  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("requires existing pinned GTPyhop runtime")

    def setUp(self):
        self.bundle = load_bundle(raw_bundle())

    def _plan(self, evidence=None):
        snapshot = snapshot_from_native(self.bundle, evidence or native_evidence(self.bundle))
        return snapshot, plan_high_level(self.bundle, snapshot)

    def test_real_gtpyhop_method_attempts_and_native_waits_are_not_goal_success(self):
        snapshot, result = self._plan()
        self.assertTrue(result["gtpyhop_search_trace"])
        self.assertTrue(result["method_attempts"])
        self.assertIn(result["method_trace"][0]["method_id"],
                      {"existing_path", "open_main", "open_side", "blocked"})
        self.assertTrue(any(row["selected_by_p5_director"] for row in result["method_attempts"]))
        self.assertEqual([row["method_id"] for row in result["method_attempts"]],
                         ["existing_path", "open_main", "open_side", "blocked"])
        self.assertEqual(result["director_plan"]["selected_action"],
                         result["control_proposal"]["selected_action"])
        self.assertEqual(result["control_proposal_status"], "PROPOSAL_AVAILABLE")
        self.assertEqual(result["goal_monitor_status"], "PENDING_OR_INDETERMINATE")
        self.assertFalse(result["author_goals_satisfied_by_meta_plan"])
        self.assertFalse(result["native_execution_occurred"])
        self.assertEqual({row["actor"] for row in result["obligations"]
                          if row.get("kind") == "delivery"}, {"A", "B"})

    def test_event_order_defers_until_only_the_declared_A_delivery_event(self):
        _, result = self._plan()
        order = next(row for row in result["obligations"] if row["constraint_id"] == "A-before-note")
        self.assertEqual(order["status"], "DEFERRED_UNTIL_REQUIRED_NATIVE_EVENT")
        self.assertEqual(order["required_before_event"]["filters"],
                         {"actor": "A", "item": "courier_supply"})
        self.assertEqual(order["depends_on_native_event_ids"], [])
        self.assertNotIn("B", repr(order["required_before_event"]))

    def test_A_receipt_witness_is_matched_by_native_stable_entity_ids(self):
        before_goal = self.bundle.goals[-1].constraint.before_filter
        actor_id = before_goal["actor"].stable_id
        item_id = before_goal["item"].stable_id
        event = {"event_id": "native-delivery-A", "event_type": "p5_delivery_settled",
                 "version": "1", "provenance": "committed_ledger",
                 "args": {"actor": {"entity_type": "Actor", "stable_id": actor_id},
                          "item": {"entity_type": "Item", "stable_id": item_id}}}
        evidence = native_evidence(self.bundle, typed_events=[event])
        _, result = self._plan(evidence)
        order = next(row for row in result["obligations"] if row["constraint_id"] == "A-before-note")
        self.assertEqual(order["status"], "WAITING_FOR_NATIVE_SOCIAL_EVENT")
        self.assertEqual(order["depends_on_native_event_ids"], ["native-delivery-A"])
        self.assertNotIn("deliver-B", order["depends_on_native_event_ids"])

    def test_wrong_actor_or_item_does_not_satisfy_order_dependency(self):
        event = {"event_id": "wrong-delivery", "event_type": "p5_delivery_settled",
                 "version": "1", "provenance": "committed_ledger",
                 "args": {"actor": {"entity_type": "Actor", "stable_id": "B"},
                          "item": {"entity_type": "Item", "stable_id": "resident_parcel"}}}
        _, result = self._plan(native_evidence(self.bundle, typed_events=[event]))
        order = next(row for row in result["obligations"] if row["constraint_id"] == "A-before-note")
        self.assertEqual(order["status"], "DEFERRED_UNTIL_REQUIRED_NATIVE_EVENT")

    def test_item_stolen_blocks_A_without_erasing_B_obligation(self):
        _, result = self._plan(native_evidence(self.bundle, supply_location=999))
        delivery_a = next(row for row in result["obligations"]
                          if row.get("kind") == "delivery" and row.get("actor") == "A")
        delivery_b = next(row for row in result["obligations"]
                          if row.get("kind") == "delivery" and row.get("actor") == "B")
        self.assertEqual(delivery_a["status"], "WAITING_FOR_ITEM_AVAILABILITY")
        self.assertEqual(delivery_b["status"], "WAITING_FOR_NATIVE_RECEIPT")

    def test_native_world_projection_adapter_rejects_wrong_frontier(self):
        evidence = native_evidence(self.bundle)
        evidence["planning_view"]["frontiers"]["values_through"] = 1
        with self.assertRaisesRegex(ValueError, "current sealed frontier"):
            snapshot_from_native(self.bundle, evidence)

    def test_readonly_projection_matches_original_director_state_contract(self):
        from tools.native_platform_v0.p5 import service

        class Attributes:
            def __init__(self, values):
                self.values = values
            def get(self, key, category=None, default=None):
                return self.values.get((category, key), default)

        pickup = SimpleNamespace(attributes=Attributes({
            ("native_p5", "p5_horizon"): 12,
            ("native_p5", "p5_spent_cost"): 1,
            ("native_p5", "p5_opportunities_used"): 1}))
        actor_a = SimpleNamespace(attributes=Attributes({
            ("native_p3", "activity_profile"): service.world.PROFILE,
            ("native_p5", "p5_actor_alias"): "A"}))
        actor_b = SimpleNamespace(attributes=Attributes({
            ("native_p3", "activity_profile"): service.world.PROFILE,
            ("native_p5", "p5_actor_alias"): "B"}))
        route_rows = [{"id": "main_passage", "open": False, "cost": 1},
                      {"id": "side_passage", "open": True, "cost": 1}]
        verdicts = {"constraints": [{"constraint_id": "deliver-A", "status": "PENDING"}]}
        with (patch.object(service, "_scene_objects", return_value=(pickup, [pickup, actor_a, actor_b])),
              patch.object(service, "_current_verdicts", return_value=(verdicts, {"trace": "t"})) as evaluate,
              patch.object(service.world, "route_rows", return_value=route_rows),
              patch.object(service.world, "serialize_typed_trace", return_value={"typed": "trace"})):
            view = service._director_planning_view("scene-test", self.bundle, now=4,
                                                   verdicts_through_minute=3)
        evaluate.assert_called_once_with("scene-test", self.bundle, through_minute=3)
        # This is the exact dictionary the pre-extraction _director constructed.
        self.assertEqual(view["state"], {
            "now": 4, "horizon": 12, "routes": route_rows,
            "spent_cost": 1, "opportunities_used": 1,
            "verdicts": [{"constraint_id": "deliver-A", "status": "PENDING"}],
            "physical_budget": 2})

        with (patch.object(service, "_scene_objects", return_value=(pickup, [pickup, actor_a, actor_b])),
              patch("tools.native_platform_v0.p3.p4_world.clock_for_actor", return_value={"now": 4}),
              patch("tools.native_platform_v0.p3.p4_world.append_event"),
              patch.object(service, "_director_planning_view", return_value={"state": view["state"]}) as projection,
              patch.object(service, "plan", return_value={"selected_action": "NO_OP"}) as p5_plan):
            result = service._director("scene-test", self.bundle, enabled=True)
        projection.assert_called_once_with("scene-test", self.bundle, now=4,
                                           verdicts_through_minute=3)
        p5_plan.assert_called_once_with(self.bundle, view["state"])
        self.assertEqual(result["authorized_view"], view["state"])

    def test_absent_response_filter_remains_valid_for_either_native_decision(self):
        raw = raw_bundle()
        raw["constraints"][2]["filters"].pop("response")
        bundle = load_bundle(raw)
        result = plan_high_level(bundle, snapshot_from_native(bundle, native_evidence(bundle)))
        note_wait = next(row for row in result["obligations"]
                         if row.get("constraint_id") == "note-response")
        self.assertEqual(note_wait["status"], "WAITING_FOR_NATIVE_SOCIAL_EVENT")
        self.assertTrue(note_wait["response_is_native_and_may_be_accept_or_reject"])

    def test_partial_hard_delivery_filter_is_residual_not_keyerror(self):
        raw = raw_bundle()
        raw["constraints"][0]["filters"].pop("actor")
        bundle = load_bundle(raw)
        result = plan_high_level(bundle, snapshot_from_native(bundle, native_evidence(bundle)))
        residual = next(row for row in result["obligations"]
                        if row.get("constraint_id") == "deliver-A")
        self.assertEqual(residual["status"], "UNBOUND_RESIDUAL")

    def test_unsupported_hard_social_role_or_item_is_residual(self):
        raw = raw_bundle()
        raw["constraints"][2]["filters"]["recipient"] = "A"
        bundle = load_bundle(raw)
        result = plan_high_level(bundle, snapshot_from_native(bundle, native_evidence(bundle)))
        residual = next(row for row in result["obligations"]
                        if row.get("constraint_id") == "note-response")
        self.assertEqual(residual["status"], "UNBOUND_RESIDUAL")

    def test_actor_domain_registration_is_restored_and_p3_plan_next_is_unchanged(self):
        import gtpyhop.main as main
        from tools.native_platform_v0.p3.planning import plan_next

        local_view = {"observation": {"task_item": {"id": "supply"},
                                      "task_destination": 3,
                                      "known_exits": {"1": [2], "2": [3], "3": []},
                                      "known_traversability": {}, "item_location": 1,
                                      "item_held": False, "room_id": 1, "exits": [
                                          {"key": "east", "destination_id": 2},
                                          {"key": "north", "destination_id": 3}],
                                      "delivered": False},
                      "clock": {"now": 0}, "deadline": 12, "contract": {"c": 0, "p": 0}}
        current_domain = main.current_domain
        before = plan_next(local_view, "deliver_supply")
        plan_high_level(self.bundle, snapshot_from_native(self.bundle, native_evidence(self.bundle)))
        self.assertIs(main.current_domain, current_domain)
        after = plan_next(local_view, "deliver_supply")
        self.assertEqual(before, after)

    def test_item_loss_and_recovery_replan_only_actor_A_and_motion_is_telemetry(self):
        from tools.native_platform_v0.p5.mature_methods.orchestrator import advance_from_sealed

        before_evidence = native_evidence(self.bundle, now=0, supply_location=101)
        before = snapshot_from_native(self.bundle, before_evidence)
        prior = plan_high_level(self.bundle, before)
        lost_evidence = native_evidence(self.bundle, now=1, supply_location=999)
        lost_evidence["actor_evidence"][0]["pending_action"] = {
            "operation_id": "move-1", "status": "planned", "planned_at_tick": 1,
            "intent": {"operator": "move", "exit_key": "east"}}
        lost = snapshot_from_native(self.bundle, lost_evidence)
        loss = advance_from_sealed(prior, before, lost)
        self.assertEqual(loss["status"], "REPLAN_REQUIRED")
        self.assertEqual(loss["changed_actor_aliases"], ["A"])
        self.assertTrue(any(row["kind"] == "BOUND_TASK_ITEM_AVAILABILITY_CHANGED"
                            for row in loss["reasons"]))
        self.assertTrue(any(row.get("constraint_id") == "deliver-B" and row.get("preserved_unaffected")
                            for row in loss["retained_obligations"]))

        restored_evidence = native_evidence(self.bundle, now=2, supply_location=101)
        restored = snapshot_from_native(self.bundle, restored_evidence)
        recovery = advance_from_sealed(prior, lost, restored)
        self.assertEqual(recovery["status"], "REPLAN_REQUIRED")
        self.assertTrue(any(row["kind"] == "BOUND_TASK_ITEM_AVAILABILITY_CHANGED"
                            for row in recovery["reasons"]))

        moving_evidence = native_evidence(self.bundle, now=1, supply_location=101)
        moving_evidence["actor_evidence"][0]["pending_action"] = lost_evidence["actor_evidence"][0]["pending_action"]
        moving = snapshot_from_native(self.bundle, moving_evidence)
        telemetry = advance_from_sealed(prior, before, moving)
        self.assertEqual(telemetry["status"], "WAITING_NO_RELEVANT_CHANGE")
        self.assertFalse(telemetry["replan_count_triggered"])
        self.assertFalse(telemetry["pending_progress_telemetry"]["A"]["replan_trigger"])

    def test_actual_s4_final24_violations_are_blocked_not_existing_path(self):
        # Compact source-derived replay of S4's immutable native final snapshot.
        # Full source: runs/S4-no-permission-safety-negative-20261012T083657Z-820e5d/
        # mature_methods/snapshot-minute-024.json, SHA-256 cd7a099e4b2a1f1b0bff47c1492c1b8239c772f469151b5ec09e5958da06de39.
        actual_s4 = SimpleNamespace(
            scene_id="20261012083709-c849e5",
            now=24,
            director_plan={
                "selected_action": "NO_OP",
                "candidates": [
                    {"candidate_id": "path:no-op", "route_id": None, "action": "NO_OP",
                     "feasible": True, "supported_hard_constraints": []},
                    {"candidate_id": "path:main_passage", "route_id": "main_passage",
                     "action": "open_main_passage", "opportunity_id": "open_main_passage",
                     "feasible": False, "supported_hard_constraints": []},
                    {"candidate_id": "path:side_passage", "route_id": "side_passage",
                     "action": "open_side_passage", "opportunity_id": "open_side_passage",
                     "feasible": False, "supported_hard_constraints": []},
                ],
            },
            verdicts=[
                {"constraint_id": name, "hard": True, "status": "VIOLATED"}
                for name in ("courier-delivery", "resident-delivery", "native-note-response",
                             "A-delivery-before-note")
            ],
        )
        self.assertEqual(_support_method(actual_s4), ("blocked", None))

    def test_terminal_all_satisfied_and_other_candidate_labels_match_prepatch_behavior(self):
        def snap(selected, verdicts, candidates=()):
            return SimpleNamespace(director_plan={"selected_action": selected,
                                                   "candidates": list(candidates)},
                                   verdicts=verdicts)

        satisfied = [{"hard": True, "status": "SATISFIED"}]
        pending = [{"hard": True, "status": "PENDING"}]
        main = {"route_id": "main_passage", "action": "open_main_passage",
                "opportunity_id": "open_main_passage", "feasible": True}
        side = {"route_id": "side_passage", "action": "open_side_passage",
                "opportunity_id": "open_side_passage", "feasible": True}
        existing = {"route_id": "main_passage", "action": "NO_OP", "feasible": True,
                    "supported_hard_constraints": ["deliver-A"]}
        self.assertEqual(_support_method(snap("NO_OP", satisfied)), ("existing_path", None))
        self.assertEqual(_support_method(snap("NO_OP", pending)), ("blocked", None))
        self.assertEqual(_support_method(snap("NO_OP", satisfied, [existing])),
                         ("existing_path", existing))
        self.assertEqual(_support_method(snap("open_main_passage", pending, [main])),
                         ("open_main", main))
        self.assertEqual(_support_method(snap("open_side_passage", pending, [side])),
                         ("open_side", side))
        self.assertEqual(_support_method(snap("NO_OP", [])), ("blocked", None))


if __name__ == "__main__":
    unittest.main()
