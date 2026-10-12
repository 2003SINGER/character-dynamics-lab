from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import unittest

from tools.planner_adapter_integration_v1.preflight import _fixture
from tools.planner_adapter_integration_v1.model import build_snapshot
from tools.planner_adapter_integration_v1.sabre import projection_status, render_problem


class SabreProjectionSemanticContracts(unittest.TestCase):
    def setUp(self):
        self.snapshot = _fixture(deadline=24, permissions=True)

    def test_move_requires_world_edge_and_actor_local_knowledge(self):
        problem = render_problem(self.snapshot)
        action = problem.split("action move_A_Pickup_Porch()", 1)[1].split("};", 1)[0]
        self.assertIn("possible_path(Pickup, Porch)", action)
        self.assertIn("known_path(A, Pickup, Porch)", action)
        self.assertNotIn("known_path(B, Pickup, Porch)", action)

    def test_physical_order_is_strict_and_deadline_is_a_separate_stage(self):
        problem = render_problem(self.snapshot)
        start = problem.split("action check_window_start_order()", 1)[1].split("};", 1)[0]
        order = problem.split("action check_window_order_order()", 1)[1].split("};", 1)[0]
        end = problem.split("action check_window_end_order()", 1)[1].split("};", 1)[0]
        self.assertIn("!window_start_order()", start)
        self.assertIn("delivery_time(A, Supply) < response_time()", order)
        self.assertIn("!window_ordered_order()", order)
        self.assertIn("!goal_order()", end)
        self.assertNotIn("response_time() <= 24", order)
        self.assertIn("response_time() <= 24", end)
        self.assertNotIn("delivery_time(A, Supply) <= 24", end)

    def test_unsupported_hard_clause_blocks_complete_projection(self):
        unsupported = ("mystery", "state_by_deadline", 0, 24,
                      json.dumps({"kind": "unregistered_hard_semantics", "hard": True}))
        statuses = self.snapshot.constraint_statuses + (("mystery", "UNRESOLVED"),)
        snapshot = replace(self.snapshot,
                           hard_requirements=self.snapshot.hard_requirements + (unsupported,),
                           constraint_statuses=statuses)
        problem = render_problem(snapshot)
        self.assertNotIn("projection_complete();", problem)
        report = projection_status(snapshot)
        self.assertFalse(report["dispatchable"])
        self.assertTrue(any("unregistered hard constraint" in row
                            for row in report["hard_residuals"]))

    def test_note_is_created_only_by_conditional_successful_request_and_received_by_B(self):
        problem = render_problem(self.snapshot)
        request = problem.split("action request_note()", 1)[1].split("};", 1)[0]
        response = problem.split("action respond_note(value : response)", 1)[1].split("};", 1)[0]
        self.assertIn("social_target_visible()", request)
        self.assertIn("at(A) == at(B)", request)
        self.assertNotIn("held_by(Note, A)", request)
        self.assertIn("note_attempted()", request)
        self.assertIn("held_by(Note, B)", request)
        self.assertIn("held_by(Note, B)", response)
        self.assertIsNone(dict(self.snapshot.world_item_location)["note"])
        self.assertIsNone(dict(self.snapshot.world_holders)["note"])
        self.assertFalse(any("Note" in row for row in projection_status(self.snapshot)["hard_residuals"]))

    def test_note_response_is_unresolved_when_native_request_precondition_is_not_observed(self):
        snapshot = replace(self.snapshot, social_target_visible=False)
        report = projection_status(snapshot)
        self.assertFalse(report["dispatchable"])
        self.assertTrue(any("A-visible, co-located B" in row for row in report["hard_residuals"]))
        self.assertNotIn("projection_complete();", render_problem(snapshot))

    def test_delivery_is_once_only_and_move_cannot_use_closed_world_edge(self):
        problem = render_problem(self.snapshot)
        get_action = problem.split("action get_item_A()", 1)[1].split("};", 1)[0]
        drop_action = problem.split("action drop_item_A()", 1)[1].split("};", 1)[0]
        move_action = problem.split("action move_A_Pickup_Porch()", 1)[1].split("};", 1)[0]
        self.assertIn("!delivered(A, Supply)", get_action)
        self.assertIn("!delivered(A, Supply)", drop_action)
        self.assertIn("possible_path(Pickup, Porch)", move_action)


class NativeSnapshotObservationContracts(unittest.TestCase):
    @staticmethod
    def _trace(*, actor_logs=None, item_location=101, note_holder=None):
        root = Path(__file__).resolve().parents[3]
        raw = json.loads((root / "tools/planner_adapter_integration_v1/cases/wide24.json")
                         .read_text(encoding="utf-8"))
        goals = [row["id"] for row in raw["constraints"]]
        actor_views = {
            "A": {"actor_id": 301, "goal_contract": {"destination_id": 103}, "observation": {
                "room_id": 101, "task_item": {"id": 201}, "task_destination": 103,
                "item_location": 101, "item_held": False,
                "visible_items": [{"id": 302}],
                "known_exits": {"101": [102]}}},
            "B": {"actor_id": 302, "goal_contract": {"destination_id": 103}, "observation": {
                "room_id": 101, "task_item": {"id": 202}, "task_destination": 103,
                "item_location": 101, "item_held": False,
                "known_exits": {"101": [103]}}},
        }
        capability = {"schema": "p5-planner-scene-binding-v1",
                      "source": "native_platform_v0.p5.service._planner_scene_binding",
                      "scene_id": "scene-contract", "room_roles": {
                          "pickup": 101, "side": 102, "porch": 103},
                      "task_bindings": {
                          "A": {"item_alias": "courier_supply", "item_id": 201,
                                "destination_id": 103, "source": "existing_scene_actor_binding"},
                          "B": {"item_alias": "resident_parcel", "item_id": 202,
                                "destination_id": 103, "source": "existing_scene_actor_binding"}},
                      "routes": [
                          {"route_id": "main_passage", "opportunity_id": "open_main_passage",
                           "cost": 2, "changed_edge_ids": [501], "directed_edges": [
                               {"exit_id": 501, "from_room_id": 101, "to_room_id": 103,
                                "changed_by_author_op": True, "traversable_now": False}]},
                          {"route_id": "side_passage", "opportunity_id": "open_side_passage",
                           "cost": 1, "changed_edge_ids": [502], "directed_edges": [
                               {"exit_id": 502, "from_room_id": 101, "to_room_id": 102,
                                "changed_by_author_op": True, "traversable_now": True},
                               {"exit_id": 503, "from_room_id": 102, "to_room_id": 103,
                                "changed_by_author_op": True, "traversable_now": True}]},
                      ]}
        trace = {"scene_id": "scene-contract", "source": "native_platform_v0.p5.service._evidence",
                 "evidence_schema": "p5-live-trace-v1", "prefix_status": "SEALED_COMPLETE",
                 "bundle_identity": {"bundle_id": raw["bundle_id"], "version": raw["version"]},
                 "now": 0, "horizon": 24, "complete_through": {"events": 0, "values": 0},
                 "world_snapshots": [{"minute": 0, "routes": {"main_passage": False,
                                    "side_passage": False},
                                      "item_locations": {"courier_supply": item_location,
                                                         "resident_parcel": 101,
                                                         "note": None},
                                      "holders": {"note": {note_holder: True} if note_holder else {}}}],
                 "world_capability_projection": capability, "ledger": [],
                 "typed_trace": {"events": []},
                 "verdicts": {"constraints": [{"constraint_id": goal, "status": "PENDING"}
                                                for goal in goals]},
            "actor_evidence": [{"actor_alias": alias, "actor_id": 301 if alias == "A" else 302,
                                "pending_action": None,
                                     "log": (actor_logs or {}).get(alias, [])}
                                    for alias in ("A", "B")]}
        observations = {"schema": "planner-adapter-actor-observation-v1",
                        "source": "p3.control_service.observe_actor", "scene_id": "scene-contract",
                        "sampled_at_minute": 0, "sampling_order": ["A", "B"],
                        "observations": {alias: {"actor_role": "courier" if alias == "A" else "resident",
                                                "local_observation": view}
                                         for alias, view in actor_views.items()}}
        return raw, trace, observations, actor_views

    def test_actor_O_is_symmetric_but_not_shared_between_actors(self):
        raw, trace, observations, _ = self._trace()
        snapshot = build_snapshot(trace, raw, scene_id="scene-contract", actor_observations=observations)
        exits = set(snapshot.known_exits)
        self.assertIn(("A", "pickup", "side"), exits)
        self.assertIn(("B", "pickup", "porch"), exits)
        self.assertNotIn(("A", "pickup", "porch"), exits)
        self.assertNotIn(("B", "pickup", "side"), exits)

    def test_stale_local_O_remains_wait_not_world_knowledge(self):
        raw, trace, _, views = self._trace()
        trace["actor_evidence"] = [
            {"actor_alias": alias, "pending_action": None,
             "log": [{"kind": "p5_goal_choice", "sim_minute": -1, "view": view}]}
            for alias, view in views.items()]
        snapshot = build_snapshot(trace, raw, scene_id="scene-contract")
        report = projection_status(snapshot)
        self.assertFalse(report["dispatchable"])
        self.assertTrue(any("stale" in row for row in report["wait_reason"]))

    def test_player_held_item_does_not_become_a_registered_room(self):
        raw, trace, observations, _ = self._trace(item_location=999, note_holder=None)
        snapshot = build_snapshot(trace, raw, scene_id="scene-contract", actor_observations=observations)
        self.assertIsNone(dict(snapshot.world_item_location)["courier_supply"])
        self.assertTrue(any("holder/nonfixture location" in row
                            for row in snapshot.projection_residuals))

    def test_committed_native_minute_zero_capture_facts_are_not_reclassified_as_synthetic(self):
        root = Path(__file__).resolve().parents[3]
        evidence = json.loads((Path(__file__).parent / "fixtures/native-minute0-capture-facts.json")
                              .read_text(encoding="utf-8"))
        self.assertEqual(evidence["evidence_class"],
                         "EXTRACTED_NATIVE_CAPTURE_FACTS_NOT_A_RUN_ARTIFACT")
        self.assertEqual(evidence["source"]["run_id"],
                         "real-source-snapshot-pilot-20261012T024000Z-61417a")
        self.assertEqual(evidence["source"]["trace_sha256"],
                         "bde19618ded24c6268eaad06baaada10b20162816a976cea77e406d2ce7d6388")
        self.assertEqual(evidence["source"]["actor_observations_sha256"],
                         "b76078c2804d5d437a534487a9999aaafe22d79aab02052ea1884358b9c4c5eb")
        self.assertEqual(evidence["minute"], 0)
        self.assertEqual(set(evidence["verdict_statuses"]), {"PENDING"})
        self.assertNotIn("note", evidence["world_snapshot"]["item_locations"])
        self.assertEqual(evidence["world_snapshot"]["holders"]["note"], {"A": False, "B": False})
        self.assertIn(evidence["actor_ids"]["B"], evidence["actor_a_visible_item_ids"])

    def test_native_request_source_creates_note_after_success_and_moves_it_to_recipient(self):
        root = Path(__file__).resolve().parents[3]
        source = (root / "tools/native_platform_v0/p3/p4_social.py").read_text(encoding="utf-8")
        request_body = source.split("def _request_note(actor, target, client):", 1)[1].split(
            "def _respond_to_note(actor, note, client):", 1)[0]
        self.assertIn('request.get("status") != "PROPOSED"', request_body)
        self.assertIn("note = create_object(", request_body)
        self.assertIn("location=actor.location", request_body)
        self.assertIn("note.move_to(target, quiet=True)", request_body)
        self.assertIn('"target_local_and_visible": True', request_body)


if __name__ == "__main__":
    unittest.main()
