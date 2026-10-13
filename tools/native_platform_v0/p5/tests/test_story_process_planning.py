import copy
import hashlib
import json
import unittest

from tools.native_platform_v0.p5.story_process.model import (
    bind_note_id, bind_scene, default_actor_postresponse, load_request,
    story_event_registry, validate_future_edit,
)
from tools.native_platform_v0.p5.story_process.planning import plan_story_process

def raw_request(*, mode="process", note_id=None, file_actor=None, methods=None, version=1,
                scenario_id="native-story-test", deadline=24):
    return {
        "schema": "story-process-request-v1", "request_id": "archive-note", "version": version,
        "scenario_id": scenario_id,
        "objective": {"kind": "archive_same_note_after_response", "note_id": note_id,
                      "by_minute": deadline, "deadline_basis": "absolute_scenario_minute",
                      "response_event_type": "p5_note_response",
                      "archive_event_type": "p5_note_archived"},
        "control": {"mode": mode, "file_actor": file_actor,
                    "allowed_methods": methods or ["file_by_B", "return_then_file_by_A"],
                    "source": "AUTHORED" if mode == "direct" else "SYSTEM"},
        "actor_postresponse": default_actor_postresponse(),
        "task_control_grant": {"grant_id": "grant-story-test", "scenario_id": scenario_id,
                               "actor_aliases": ["A", "B"],
                               "task_kinds": ["handover_note", "archive_note"],
                               "valid_until_minute": 24},
        "edit_policy": {"editable_future_fields": ["control.file_actor", "control.allowed_methods"],
                        "settled_fields_immutable": True, "grant_immutable": True},
        "locked_fragment": None,
    }


def registry_with_story_events():
    return story_event_registry()


def sealed_state(request, *, now=17, outcome="accepted", holder="B", a_present=True,
                 b_present=True, b_willing=True, a_willing=True, archive_minutes=4,
                 handover_minutes=2, task_status_a="IDLE", task_status_b="IDLE",
                 remaining_a=0, remaining_b=0):
    note_id = request.objective["note_id"]
    events = []
    response = None
    if outcome:
        response = {"outcome": outcome, "event_id": "response-17", "minute": 17, "note_id": note_id}
        events.append({"event_id": "response-17", "event_type": "p5_note_response", "version": "1",
                       "provenance": "committed_ledger", "time": 17, "sequence": 1,
                       "args": {"actor": "A", "recipient": "B", "item": "note", "response": outcome}})
    return {
        "scenario_id": request.scenario_id, "sealed_minute": now, "horizon": 24,
        "request_id": request.request_id, "request_version": request.version,
        "response": response,
        "note": {"item_id": note_id, "location_id": 501, "holder_alias": holder},
        "actors": {
            "A": {"present": a_present, "can_receive_note": True, "willing_to_archive": a_willing,
                  "locally_observed_item_ids": [note_id], "active_task": None, "task_status": task_status_a,
                  "remaining_work_minutes": remaining_a},
            "B": {"present": b_present, "can_receive_note": True, "willing_to_archive": b_willing,
                  "locally_observed_item_ids": [note_id], "active_task": None, "task_status": task_status_b,
                  "remaining_work_minutes": remaining_b},
        },
        "destinations": {
            "archive": {"id": 601, "reachable_by": ["A", "B"], "estimated_minutes": archive_minutes,
                        "estimated_minutes_by_actor": {"A": archive_minutes, "B": archive_minutes}},
            "handover": {"id": 602, "reachable_by": ["A", "B"], "estimated_minutes": handover_minutes,
                         "estimated_minutes_by_actor": {"A": handover_minutes, "B": handover_minutes}},
        },
        "task_grant": copy.deepcopy(dict(request.task_control_grant)),
        "current_obligations": [{"kind": "preserve-existing-delivery", "status": "WAITING"}],
        "typed_trace": {"events": events},
        "event_registry": registry_with_story_events(),
    }


class StoryProcessModelTests(unittest.TestCase):
    def test_unbound_native_note_can_be_bound_once_after_creation(self):
        request = load_request(raw_request(scenario_id=None), allow_template=True)
        request = bind_scene(request, "real-scene-id")
        bound = bind_note_id(request, 777)
        self.assertIsNone(request.objective["note_id"])
        self.assertEqual(bound.objective["note_id"], 777)
        with self.assertRaises(ValueError):
            bind_note_id(bound, 778)

    def test_direct_control_requires_authored_provenance(self):
        raw = raw_request(mode="direct")
        raw["control"]["source"] = "SYSTEM"
        with self.assertRaises(ValueError):
            load_request(raw)

    def test_future_edits_cannot_change_grant_or_goal_or_rebind_item(self):
        request = bind_note_id(load_request(raw_request()), 777)
        edited = raw_request(note_id=777, version=2, file_actor="A")
        validate_future_edit(request, edited)
        edited["task_control_grant"]["valid_until_minute"] = 25
        with self.assertRaises(ValueError):
            validate_future_edit(request, edited)

    def test_locked_sequence_hash_is_pinned(self):
        raw = raw_request(mode="locked_fragment")
        sequence = [{"actor_alias": "B", "task_kind": "archive_note", "item_ref": "objective.note",
                     "destination_ref": "archive"}]
        raw["locked_fragment"] = {"sequence": sequence,
                                  "sequence_sha256": hashlib.sha256(json.dumps(sequence, sort_keys=True,
                                                                               separators=(",", ":")).encode()).hexdigest(),
                                  "entry_guard": {"response_required": True, "note_holder_alias": "B"},
                                  "abort_policy": "ABORT_LOCKED_CORE"}
        self.assertEqual(load_request(raw).locked_fragment["sequence"], sequence)
        raw["locked_fragment"]["sequence"][0]["actor_alias"] = "A"
        with self.assertRaises(ValueError):
            load_request(raw)


class StoryProcessPlanningTests(unittest.TestCase):
    def _request(self, **kwargs):
        return bind_note_id(load_request(raw_request(**kwargs)), 777)

    def test_archive_only_author_bundle_reaches_real_method_search_and_task_offers(self):
        from tools.native_platform_v0.p5.ongoing_station.controller import _runtime_request
        from tools.native_platform_v0.p5.ongoing_station.model import (
            compile_projection, derive_story_requirements, load_profile,
        )
        from tools.native_platform_v0.p5.tests.test_ongoing_station_model import author, profile

        authored = author()
        authored["bundle"]["constraints"] = authored["bundle"]["constraints"][:1]
        authored["bindings"] = authored["bindings"][:1]
        station = load_profile(profile(authored))
        projection = compile_projection(station)
        constraint = projection.constraints[0]
        request = load_request(_runtime_request(
            station, projection, constraint, constraint["control"], "archive-only-scene", 777))
        requirements = derive_story_requirements(projection, constraint, 777)
        self.assertIsNone(requirements["required_handover"])

        state = sealed_state(request, now=17, archive_minutes=2, handover_minutes=1)
        result = plan_story_process(request, state, strategy="gtpyhop",
                                    required_story_events=requirements)
        self.assertIn(result["status"], {"TASKS_PROPOSED", "WAITING_OR_BLOCKED"})
        candidate_ids = {row["method_id"] for row in result["method_plans"]}
        self.assertTrue({"file_by_B", "return_then_file_by_A"}.issubset(candidate_ids))
        if result["task_requests"]:
            for task in result["task_requests"]:
                self.assertEqual(task["required_story_event_types"], ["p5_note_archived"])
                self.assertEqual(task["required_constraint_ids"], ["archive-goal"])
                self.assertLessEqual(task["required_story_deadline_minute"], 24)
                if task["task_kind"] == "handover_note":
                    self.assertEqual(task["required_story_deadline_minute"], 24)

    def test_event_driven_comparator_has_same_task_authority_and_candidate_policy(self):
        request = self._request()
        state = sealed_state(request)
        result = plan_story_process(request, state, strategy="event_driven")
        self.assertEqual(result["selected_method"], "file_by_B")
        self.assertEqual(result["task_requests"][0]["item_id"], 777)
        self.assertFalse(result["native_execution_occurred"])
        self.assertFalse(result["world_effects_applied"])
        self.assertEqual(result["outstanding_obligations"][0]["kind"], "preserve-existing-delivery")

    def test_zero_and_locked_modes_with_default_gtpyhop_strategy_have_empty_engine_trace(self):
        zero_request = self._request(mode="zero")
        zero = plan_story_process(zero_request, sealed_state(zero_request))
        self.assertEqual(zero["status"], "NO_CONTROL")
        self.assertEqual(zero["task_requests"], [])
        self.assertEqual(zero["attempted_methods"], [])
        self.assertEqual(zero["gtpyhop_search_trace"], [])

        raw = raw_request(mode="locked_fragment")
        sequence = [{"actor_alias": "B", "task_kind": "archive_note",
                     "item_ref": "objective.note", "destination_ref": "archive"}]
        raw["locked_fragment"] = {
            "sequence": sequence,
            "sequence_sha256": hashlib.sha256(json.dumps(
                sequence, sort_keys=True, separators=(",", ":")).encode()).hexdigest(),
            "entry_guard": {"response_required": True, "note_holder_alias": "B"},
            "abort_policy": "ABORT_LOCKED_CORE",
        }
        locked_request = bind_note_id(load_request(raw), 777)
        locked = plan_story_process(locked_request, sealed_state(locked_request))
        self.assertEqual(locked["status"], "TASKS_PROPOSED")
        self.assertEqual(locked["task_requests"][0]["control_source"], "LOCKED_FRAGMENT")
        self.assertEqual(locked["attempted_methods"], [])
        self.assertEqual(locked["gtpyhop_search_trace"], [])
        self.assertFalse(locked["world_effects_applied"])

    def test_result_only_proposes_but_does_not_accept_or_execute_tasks(self):
        request = self._request(mode="result_only")
        result = plan_story_process(request, sealed_state(request), strategy="event_driven")
        self.assertTrue(result["task_requests"])
        self.assertTrue(result["task_requests_are_proposals"])
        self.assertEqual(result["accepted_task_request_ids"], [])
        self.assertFalse(result["world_effects_applied"])
        self.assertEqual(result["task_requests"][0]["control_source"], "PLANNER")

    def test_result_only_gtn_uses_one_actual_method_even_when_both_are_feasible(self):
        try:
            import gtpyhop  # noqa: F401
        except ImportError:
            self.skipTest("requires the existing pinned GTPyhop environment")
        from tools.native_platform_v0.p5.story_process.planning import _method_preconditions
        request = self._request(mode="result_only")
        state = sealed_state(request, handover_minutes=2, archive_minutes=4)
        self.assertTrue(_method_preconditions("file_by_B", request, state)[0])
        self.assertTrue(_method_preconditions("return_then_file_by_A", request, state)[0])
        result = plan_story_process(request, state, strategy="gtpyhop")
        self.assertEqual(result["selected_method"], "file_by_B")
        self.assertEqual(len(result["task_requests"]), 1)
        self.assertEqual({row["source_method_id"] for row in result["task_requests"]}, {"file_by_B"})
        diagnostics = {row["method_id"]: row
                       for row in result["alternative_guard_diagnostics"]}
        self.assertTrue(diagnostics["file_by_B"]["feasible"])
        self.assertTrue(diagnostics["return_then_file_by_A"]["feasible"])
        self.assertTrue(all(row["diagnostic_only"] and not row["used_to_select_method"]
                            for row in diagnostics.values()))
        # Keep engine callback instrumentation distinct from post-search diagnostics;
        # the engine may invoke alternative callbacks while finding its winning plan.
        self.assertTrue(result["attempted_methods"])
        self.assertTrue(all("diagnostic_only" not in row
                            for row in result["attempted_methods"]))
        # The returned plan still contains only the winning method's decomposition.
        self.assertTrue(result["task_requests_are_proposals"])
        self.assertFalse(result["native_execution_occurred"])

    def test_unknown_response_waits_without_proposing_effectful_tasks(self):
        request = self._request()
        state = sealed_state(request, outcome=None)
        result = plan_story_process(request, state, strategy="event_driven")
        self.assertEqual(result["task_requests"], [])
        self.assertEqual(result["status"], "WAITING_OR_BLOCKED")
        self.assertEqual(result["guards"]["response_event_id"], None)

    def test_new_handover_requirement_changes_method_support_and_monitor_witness(self):
        request = self._request(mode="result_only")
        state = sealed_state(request, now=18, archive_minutes=3, handover_minutes=2)
        required = {"source_bundle_id": "bundle-1", "source_version": 2,
                    "source_sha256": "a" * 64, "archive_constraint_id": "archive-goal",
                    "archive_start_minute": 0, "archive_deadline_minute": 24, "note_id": 777,
                    "required_handover": {
                        "event_count_constraint_id": "handover-occurs",
                        "order_constraint_id": "handover-before-archive",
                        "event_type": "p5_note_handed_over", "actor_alias": "B",
                        "recipient_alias": "A", "before_event_type": "p5_note_archived",
                        "start_minute": 18, "deadline_minute": 24},
                    "residual_constraints": []}
        result = plan_story_process(request, state, strategy="event_driven",
                                    required_story_events=required)
        candidates = {row["method_id"]: row for row in result["method_plans"]}
        self.assertFalse(candidates["file_by_B"]["feasible"])
        self.assertIn("p5_note_handed_over",
                      candidates["file_by_B"]["causal_support"]["missing_required_event_types"])
        self.assertTrue(candidates["return_then_file_by_A"]["feasible"])
        self.assertEqual([row["task_kind"] for row in result["task_requests"]],
                         ["handover_note", "archive_note"])
        self.assertEqual(result["task_requests"][0]["required_story_event_types"],
                         ["p5_note_handed_over", "p5_note_archived"])
        verdicts = {row["constraint_id"]: row["verdicts"]
                    for row in result["typedir_verdicts"]}
        self.assertIn("handover-occurs", verdicts)
        self.assertIn("handover-before-archive", verdicts)

        state["sealed_minute"] = 24
        state["note"]["holder_alias"] = "A"
        state["typed_trace"]["events"].extend([
            {"event_id": "give-1", "event_type": "p5_note_handed_over", "version": "1",
             "provenance": "committed_ledger", "time": 19, "sequence": 2,
             "args": {"actor": "B", "recipient": "A", "item": "note"}},
            {"event_id": "archive-1", "event_type": "p5_note_archived", "version": "1",
             "provenance": "committed_ledger", "time": 21, "sequence": 3,
             "args": {"actor": "A", "item": "note"}},
        ])
        after = plan_story_process(request, state, strategy="event_driven",
                                  required_story_events=required)
        verdicts = {row["constraint_id"]: row["verdicts"]
                    for row in after["typedir_verdicts"]}
        self.assertTrue(all(v["verdict"] == "SATISFIED"
                            for key in ("handover-occurs", "handover-before-archive")
                            for v in verdicts[key]), repr(verdicts))

    def test_handover_window_not_before_start_and_order_deadline_covers_archive(self):
        request = self._request(mode="result_only")
        required = {"source_bundle_id": "bundle-1", "source_version": 2,
                    "source_sha256": "a" * 64, "archive_constraint_id": "archive-goal",
                    "archive_start_minute": 0, "archive_deadline_minute": 24, "note_id": 777,
                    "required_handover": {
                        "event_count_constraint_id": "handover-occurs",
                        "order_constraint_id": "handover-before-archive",
                        "event_type": "p5_note_handed_over", "actor_alias": "B",
                        "recipient_alias": "A", "before_event_type": "p5_note_archived",
                        "start_minute": 18, "deadline_minute": 20},
                    "residual_constraints": []}
        before = plan_story_process(request, sealed_state(request, now=17),
                                    strategy="event_driven", required_story_events=required)
        self.assertEqual(before["task_requests"], [])
        self.assertTrue(any("waiting_for_authored_handover_window_start" in row["preconditions"]
                            for row in before["rejected_methods"]))
        too_late = plan_story_process(request, sealed_state(request, now=18),
                                      strategy="event_driven", required_story_events=required)
        self.assertEqual(too_late["task_requests"], [])
        self.assertTrue(any("absolute_deadline_time_infeasible" in row["preconditions"]
                            for row in too_late["rejected_methods"]))

    def test_unknown_workload_is_temporary_wait_not_permanent_unreachable(self):
        request = self._request()
        state = sealed_state(request, remaining_b=None)
        result = plan_story_process(request, state, strategy="event_driven")
        self.assertEqual(result["task_requests"], [])
        self.assertTrue(any(row["kind"] == "WAITING_FOR_ACTOR_COMMITMENT_FRONTIER"
                            for row in result["outstanding_obligations"]))
        self.assertEqual(result["status"], "WAITING_OR_BLOCKED")

    def test_rejection_routes_to_return_then_A_only_when_native_conditions_and_time_fit(self):
        request = self._request()
        state = sealed_state(request, outcome="rejected")
        result = plan_story_process(request, state, strategy="event_driven")
        self.assertEqual([row["task_kind"] for row in result["task_requests"]],
                         ["handover_note", "archive_note"])
        self.assertEqual([row["actor_alias"] for row in result["task_requests"]], ["B", "A"])
        self.assertEqual(result["selected_method"], "return_then_file_by_A")
        a_archive = result["task_requests"][1]
        self.assertEqual(a_archive["destination_id"], 601)
        self.assertEqual(a_archive["rendezvous_destination_id"],
                         state["destinations"]["handover"]["id"])
        self.assertIn("committed_native_handover_receipt_for_exact_note_at_rendezvous",
                      a_archive["prerequisites"])
        self.assertFalse(result["world_effects_applied"])
        diagnostics = {row["method_id"]: row
                       for row in result["alternative_guard_diagnostics"]}
        self.assertFalse(diagnostics["file_by_B"]["feasible"])
        self.assertTrue(diagnostics["return_then_file_by_A"]["feasible"])

    def test_real_B_task_refusal_replans_to_A_without_rewriting_response_history(self):
        request = self._request(mode="result_only")
        state = sealed_state(request, outcome="accepted")
        state["actors"]["B"]["task_status"] = "REJECTED"
        state["actors"]["B"]["active_task"] = {
            "request_id": "prior-real-request", "task_kind": "archive_note",
            "item_id": 777, "destination_id": 601, "status": "REJECTED"}
        state["current_obligations"].append({"kind": "already-committed-delivery", "status": "SETTLED"})
        result = plan_story_process(request, state, strategy="gtpyhop")
        self.assertEqual(result["selected_method"], "return_then_file_by_A")
        self.assertEqual([row["actor_alias"] for row in result["task_requests"]], ["B", "A"])
        self.assertEqual(result["task_requests"][1]["rendezvous_destination_id"],
                         state["destinations"]["handover"]["id"])
        self.assertEqual(result["guards"]["response_event_id"], "response-17")
        self.assertTrue(any(row.get("request_id") == "prior-real-request"
                            for row in result["outstanding_obligations"]))
        self.assertTrue(any(row.get("kind") == "already-committed-delivery"
                            for row in result["outstanding_obligations"]))

    def test_gtn_no_plan_preserves_in_progress_B_archive_as_pending(self):
        request = self._request(mode="result_only")
        state = sealed_state(request, now=18, outcome="accepted", holder="B")
        state["actors"]["B"]["task_status"] = "IN_PROGRESS"
        state["actors"]["B"]["active_task"] = {
            "request_id": "archive-note:v1:file_by_B:B:archive_note",
            "task_kind": "archive_note", "item_id": 777,
            "destination_id": 601, "status": "IN_PROGRESS"}
        result = plan_story_process(request, state, strategy="gtpyhop")
        self.assertEqual(result["task_requests"], [])
        self.assertEqual(result["selected_method"], None)
        self.assertTrue(any(row.get("kind") == "actor_story_task"
                            and row.get("request_id") == "archive-note:v1:file_by_B:B:archive_note"
                            and row.get("status") == "IN_PROGRESS"
                            and row.get("preserved")
                            for row in result["outstanding_obligations"]))
        self.assertTrue(any(row.get("kind") == "WAITING_FOR_ACTIVE_NATIVE_TASK"
                            for row in result["outstanding_obligations"]))
        archive = next(row for row in result["typedir_verdicts"]
                       if row["constraint_id"] == "story-note-archive-by-deadline")
        self.assertEqual(archive["verdicts"][0]["verdict"], "PENDING")
        self.assertNotIn("unreachable", repr(result["typedir_verdicts"]).lower())
        self.assertNotIn("budget", repr(result["outstanding_obligations"]).lower())

    def test_typedir_ignores_planned_archive_and_checks_actual_filer(self):
        request = self._request(mode="process")
        state = sealed_state(request)
        state["typed_trace"]["events"].append({
            "event_id": "proposal-only", "event_type": "p5_note_archived", "version": "1",
            "provenance": "planning", "time": 18, "sequence": 2,
            "args": {"actor": "A", "item": "note"}})
        result = plan_story_process(request, state, strategy="event_driven")
        archive = next(row for row in result["typedir_verdicts"]
                       if row["constraint_id"] == "story-note-archive-by-deadline")
        self.assertEqual(archive["verdicts"][0]["verdict"], "PENDING")

        actual = sealed_state(request)
        actual["sealed_minute"] = 24
        actual["typed_trace"]["events"].append({
            "event_id": "archive-by-A", "event_type": "p5_note_archived", "version": "1",
            "provenance": "committed_ledger", "time": 18, "sequence": 3,
            "args": {"actor": {"entity_type": "Actor", "stable_id": "A", "label": "A"},
                     "item": {"entity_type": "Item", "stable_id": "777", "label": "note"}}})
        edited_raw = raw_request(mode="process", note_id=777, file_actor="B", version=2,
                                 methods=["file_by_B"])
        updated = validate_future_edit(request, edited_raw)
        actual["request_version"] = updated.version
        actual["task_grant"] = copy.deepcopy(dict(updated.task_control_grant))
        result = plan_story_process(updated, actual, strategy="event_driven")
        archive = next(row for row in result["typedir_verdicts"]
                       if row["constraint_id"] == "story-note-archive-by-deadline")
        self.assertEqual(archive["verdicts"][0]["verdict"], "VIOLATED")

    def test_time_infeasible_return_does_not_hide_preexisting_obligation(self):
        request = self._request()
        state = sealed_state(request, outcome="rejected", archive_minutes=4, handover_minutes=4)
        result = plan_story_process(request, state, strategy="event_driven")
        self.assertEqual(result["task_requests"], [])
        self.assertTrue(any("absolute_deadline_time_infeasible" in row["preconditions"]
                            for row in result["rejected_methods"]))
        self.assertEqual(result["outstanding_obligations"][0]["kind"], "preserve-existing-delivery")

    def test_absolute_deadline_is_not_reset_when_sealed_horizon_reaches_24(self):
        request = bind_note_id(load_request(raw_request(deadline=18)), 777)
        state = sealed_state(request, now=24, outcome="rejected", archive_minutes=1, handover_minutes=1)
        result = plan_story_process(request, state, strategy="event_driven")
        self.assertEqual(result["guards"]["absolute_deadline_minute"], 18)
        self.assertEqual(result["task_requests"], [])
        self.assertIn("VIOLATED", repr(result["typedir_verdicts"]))

    def test_missing_holder_or_actor_blocks_only_dependent_method(self):
        request = self._request()
        state = sealed_state(request, holder="PLAYER")
        result = plan_story_process(request, state, strategy="event_driven")
        self.assertEqual(result["task_requests"], [])
        self.assertTrue(result["rejected_methods"])

    def test_gtn_search_uses_real_alternative_method_decompositions(self):
        try:
            import gtpyhop  # noqa: F401
        except ImportError:
            self.skipTest("requires the existing pinned GTPyhop environment")
        request = self._request()
        result = plan_story_process(request, sealed_state(request), strategy="gtpyhop")
        self.assertTrue(result["gtpyhop_search_trace"])
        self.assertTrue(result["attempted_methods"])
        self.assertEqual(result["task_requests"][0]["source_method_id"], "file_by_B")
        self.assertFalse(result["world_effects_applied"])

    def test_station_work_gtpyhop_enumerates_two_orders_with_shared_tool_and_receipt_constraints(self):
        from tools.native_platform_v0.p5.story_process.planning import plan_station_work_order

        def view(actor_id):
            return {"actor_id": actor_id, "observation": {
                "room_id": 5, "inventory": [],
                "visible_items": [{"id": 3, "room_id": 5}],
                "known_exits": {5: [6], 6: [5]},
                "exits": [{"key": "east", "destination_id": 6}],
                "station_tools": [{"id": 1, "room_id": 5, "visible": True,
                                   "held_by_actor_id": None, "lease_status": "FREE"}],
                "station_supplies": [{"id": 3, "room_id": 5, "visible": True,
                                      "inspection_status": "UNINSPECTED"}],
                "station_repair_targets": [{"id": 4, "room_id": 5, "traversable": False}],
                "station_storages": [{"id": 2, "room_id": 6, "visible": True}],
            }}

        state = {"sealed_minute": 0, "horizon": 24, "station_id": "s1",
                 "projection_id": "projection-1", "constraint_id": "inspect-goal",
                 "grant_id": "s1:inspect-goal:fixed-native-grant",
                 "grant_ids": {"inspect-goal": "s1:inspect-goal:fixed-native-grant"},
                 "station_content": {"tool_id": 1, "storage_id": 2, "supply_id": 3,
                                     "repair_exit_id": 4, "workbench_room_id": 5,
                                     "storage_room_id": 6},
                 "station_tool": {"id": 1, "room_id": 5, "holder_alias": None,
                                  "lease_status": "FREE"},
                 "active_tool_lease": None,
                 "actors": {"A": {"actor_id": 11, "local_view": view(11),
                                   "commitments": [], "pending_action": None},
                            "B": {"actor_id": 12, "local_view": view(12),
                                   "commitments": [], "pending_action": None}},
                 "typed_trace": {"events": []}, "constraints": [
                     {"constraint_id": "inspect-goal", "kind": "event_by_deadline",
                      "source_constraint": {"id": "inspect-goal", "kind": "event_by_deadline",
                                            "event": "station_supply_inspected", "start": 0,
                                            "deadline": 3, "hard": True},
                      "control": {"mode": "result_only",
                                  "allowed_methods": ["inspect_then_repair", "repair_then_inspect"]}},
                     {"constraint_id": "repair-goal", "kind": "event_by_deadline",
                      "source_constraint": {"id": "repair-goal", "kind": "event_by_deadline",
                                            "event": "station_passage_repaired", "start": 0,
                                            "deadline": 7, "hard": True},
                      "control": {"mode": "result_only",
                                  "allowed_methods": ["inspect_then_repair", "repair_then_inspect"]}},
                     {"constraint_id": "store-goal", "kind": "event_by_deadline",
                      "source_constraint": {"id": "store-goal", "kind": "event_by_deadline",
                                            "event": "station_supply_stored", "start": 0,
                                            "deadline": 10, "hard": True},
                      "control": {"mode": "result_only",
                                  "allowed_methods": ["inspect_then_repair", "repair_then_inspect"]}},
                 ]}
        gtn = plan_station_work_order(state)
        event = plan_station_work_order(state, strategy="event_driven")
        candidates = {row["method_id"]: row for row in gtn["method_plans"]}
        self.assertEqual(set(candidates), {"inspect_then_repair", "repair_then_inspect"})
        self.assertTrue(candidates["inspect_then_repair"]["feasible"])
        self.assertFalse(candidates["repair_then_inspect"]["feasible"])
        self.assertEqual(gtn["selected_method"], "inspect_then_repair", repr(gtn))
        self.assertEqual(event["selected_method"], "inspect_then_repair")
        self.assertEqual([row["task_kind"] for row in gtn["task_requests"]],
                         ["inspect_supply", "repair_passage", "store_item"])
        self.assertEqual(gtn["task_requests"][0]["grant_id"], "s1:inspect-goal:fixed-native-grant")
        self.assertEqual(gtn["task_requests"][0]["earliest_terminal_minute"], 0)
        self.assertGreaterEqual(gtn["task_requests"][0]["estimated_work_start_minute"],
                                gtn["task_requests"][0]["planned_start_minute"])
        self.assertEqual(candidates["inspect_then_repair"]["resource_capacity"]["capacity"], 1)
        self.assertFalse(gtn["world_effects_applied"])

    def test_station_work_uses_actual_receipts_to_skip_completed_work(self):
        from tools.native_platform_v0.p5.story_process.planning import plan_station_work_order
        # Start from a no-author candidate state copied from the paired test's
        # same actor-local fixture; the receipt is committed TypedIR evidence.
        state = self._station_state_for_work()
        state["typed_trace"]["events"].append({
            "event_type": "p5_station_supply_inspected", "provenance": "committed_ledger",
            "time": 2, "native_receipt_id": "receipt-inspect-1",
            "native_commitment_id": "commitment-inspect-1",
            "native_task_kind": "inspect_supply",
            "args": {"actor": "A", "item": "3", "tool": "1"}})
        for actor in state["actors"].values():
            actor["local_view"]["observation"]["station_supplies"][0]["inspection_status"] = "APPROVED"
        result = plan_station_work_order(state)
        self.assertTrue(all(row["task_kind"] != "inspect_supply"
                            for row in result["task_requests"]))
        self.assertTrue(any(row["satisfied"]["inspect_supply"] for row in result["method_plans"]))

    def test_active_native_work_uses_exact_lease_due_and_is_not_reproposed(self):
        from tools.native_platform_v0.p5.story_process.planning import plan_station_work_order
        state = self._station_state_for_work()
        state["sealed_minute"] = 2
        state["station_tool"]["lease_status"] = "BUSY"
        state["active_tool_lease"] = {
            "status": "IN_PROGRESS", "commitment_id": "inspect-c1",
            "task_kind": "inspect_supply", "actor_alias": "A", "tool_id": 1,
            "target_id": 3, "started_minute": 1, "due_minute": 3}
        state["actors"]["A"]["commitments"] = [{
            "commitment_id": "inspect-c1", "task_kind": "inspect_supply",
            "status": "IN_PROGRESS", "due_minute": None, "tool_id": 1,
            "target_id": 3}]
        state["actors"]["B"]["local_view"]["observation"]["station_task_bindings"] = [{
            "task_kind": "repair_passage", "tool_id": 1, "target_id": 4,
            "target_room_id": 5}]

        result = plan_station_work_order(state, strategy="event_driven")
        self.assertEqual(result["selected_method"], "inspect_then_repair", repr(result))
        self.assertNotIn("A_active_commitment_release_time_unknown",
                         result["method_plans"][0]["preconditions"])
        self.assertEqual([row["task_kind"] for row in result["task_requests"]], ["store_item"])
        self.assertTrue(any(row["task_kind"] == "repair_passage"
                            for row in result["derived_support_tasks"]))
        inspect_schedule = next(row for row in result["method_plans"][0]["schedule"]
                               if row["task_kind"] == "inspect_supply")
        self.assertEqual(inspect_schedule["finish_minute"], 3)
        self.assertEqual(result["method_plans"][0]["route_estimates"]["inspect_supply"]["source"],
                         "exact_active_native_lease")

    def test_conditional_route_release_is_scoped_and_explicitly_not_a_bound(self):
        from tools.native_platform_v0.p5.story_process.planning import plan_station_work_order
        state = self._station_state_for_work()
        state["actors"]["B"]["commitments"] = [{
            "commitment_id": "route-b1", "task_kind": "routine_route",
            "status": "IN_PROGRESS", "remaining_work_minutes": 2,
            "release_time_basis": "conditional_no_future_failure_estimate"}]
        result = plan_station_work_order(state, strategy="event_driven")
        candidate = next(row for row in result["method_plans"]
                         if row["method_id"] == "inspect_then_repair")
        forecast = next(row for row in candidate["conditional_release_forecasts"]
                        if row["commitment_id"] == "route-b1")
        self.assertEqual(forecast["remaining_work_minutes"], 2)
        self.assertIn("conditional forecast, not a release upper bound", forecast["assumption"])

        # Once B's repair is already evidenced, B's unrelated route no longer
        # blocks the only remaining actor/task (A storing the inspected item).
        completed = self._station_state_for_work()
        completed["sealed_minute"] = 10
        completed["typed_trace"]["events"] = [
            {"event_type": "p5_station_supply_inspected", "provenance": "committed_ledger",
             "time": 3, "native_receipt_id": "ri", "native_commitment_id": "ci",
             "native_task_kind": "inspect_supply",
             "args": {"actor": "A", "item": "3", "tool": "1"}},
            {"event_type": "p5_station_passage_repaired", "provenance": "committed_ledger",
             "time": 7, "native_receipt_id": "rr", "native_commitment_id": "cr",
             "native_task_kind": "repair_passage",
             "args": {"actor": "B", "tool": "1", "exit": "4"}},
        ]
        completed["actors"]["B"]["commitments"] = [{
            "commitment_id": "route-b2", "task_kind": "routine_route",
            "status": "IN_PROGRESS"}]
        completed["actors"]["A"]["local_view"]["observation"]["inventory"] = [{"id": 3}]
        completed["actors"]["A"]["local_view"]["observation"]["station_supplies"] = [{
            "id": 3, "room_id": 5, "visible": True,
            "inspection_status": "APPROVED"}]
        completed["actors"]["A"]["local_view"]["observation"]["visible_items"] = []
        next_result = plan_station_work_order(completed, strategy="event_driven")
        selected = next(row for row in next_result["method_plans"]
                        if row["method_id"] == "inspect_then_repair")
        self.assertNotIn("B_active_commitment_release_time_unknown", selected["preconditions"])
        self.assertTrue(selected["feasible"], repr(selected))
        self.assertEqual([row["task_kind"] for row in next_result["task_requests"]], ["store_item"])

    def test_all_receipt_backed_work_returns_satisfied_prefix_not_new_offer(self):
        from tools.native_platform_v0.p5.story_process.planning import plan_station_work_order
        state = self._station_state_for_work()
        state["sealed_minute"] = 15
        state["typed_trace"]["events"] = [
            {"event_type": "p5_station_supply_inspected", "provenance": "committed_ledger",
             "time": 3, "native_receipt_id": "ri", "native_commitment_id": "ci",
             "native_task_kind": "inspect_supply",
             "args": {"actor": "A", "item": "3", "tool": "1"}},
            {"event_type": "p5_station_passage_repaired", "provenance": "committed_ledger",
             "time": 7, "native_receipt_id": "rr", "native_commitment_id": "cr",
             "native_task_kind": "repair_passage",
             "args": {"actor": "B", "tool": "1", "exit": "4"}},
            {"event_type": "p5_station_supply_stored", "provenance": "committed_ledger",
             "time": 10, "native_receipt_id": "rs", "native_commitment_id": "cs",
             "native_task_kind": "store_item",
             "args": {"actor": "A", "item": "3", "storage": "2"}},
        ]
        result = plan_station_work_order(state)
        self.assertEqual(result["status"], "SATISFIED_PREFIX", repr(result))
        self.assertIsNone(result["selected_method"])
        self.assertEqual(result["task_requests"], [])
        self.assertEqual(result["attempted_methods"], [])

    def test_old_self_store_does_not_retroactively_satisfy_locked_core(self):
        from tools.native_platform_v0.p5.story_process.planning import plan_station_work_order
        state = self._station_state_for_work()
        state["sealed_minute"] = 15
        state["typed_trace"]["events"] = [
            {"event_type": "p5_station_supply_inspected", "provenance": "committed_ledger",
             "time": 3, "native_receipt_id": "ri", "native_commitment_id": "ci",
             "native_task_kind": "inspect_supply",
             "args": {"actor": "A", "item": "3", "tool": "1"}},
            {"event_type": "p5_station_passage_repaired", "provenance": "committed_ledger",
             "time": 7, "native_receipt_id": "rr", "native_commitment_id": "cr",
             "native_task_kind": "repair_passage",
             "args": {"actor": "B", "tool": "1", "exit": "4"}},
            {"event_type": "p5_station_supply_stored", "provenance": "committed_ledger",
             "time": 10, "native_receipt_id": "rs", "native_commitment_id": "cs",
             "native_task_kind": "store_item",
             "args": {"actor": "A", "item": "3", "storage": "2"}},
        ]
        sequence = [{"actor_alias": "A", "task_kind": "store_item",
                     "item_ref": "courier_supply", "destination_ref": "station_storage"}]
        digest = hashlib.sha256(json.dumps(sequence, sort_keys=True,
                                           separators=(",", ":")).encode()).hexdigest()
        state["constraints"] = [{
            "constraint_id": "locked-store", "kind": "event_by_deadline",
            "source_constraint": {"kind": "event_by_deadline",
                "event": "station_supply_stored", "start": 0, "deadline": 20,
                "filters": {"actor": "A", "item": "courier_supply",
                            "storage": "station_storage"}},
            "control": {"mode": "locked_fragment", "file_actor": "A",
                        "allowed_methods": ["inspect_then_repair", "repair_then_inspect"]},
            "locked_fragment": {"sequence": sequence, "sequence_sha256": digest,
                "entry_guard": {"task_grant_required": True,
                                "supply_alias": "courier_supply",
                                "storage_alias": "station_storage",
                                "inspection_receipt_required": True},
                "abort_policy": "ABORT_LOCKED_CORE"},
        }]
        result = plan_station_work_order(state, strategy="event_driven")
        self.assertNotEqual(result["status"], "SATISFIED_PREFIX")
        self.assertEqual(result["task_requests"], [])
        self.assertTrue(any("LOCKED_CORE_EXECUTION_UNWITNESSED" in row["preconditions"]
                            for row in result["method_plans"]))
        state["actors"]["A"]["commitments"] = [{
            "commitment_id": "cs", "task_kind": "store_item", "status": "SETTLED",
            "control_source": "LOCKED_FRAGMENT", "locked_fragment_hash": digest,
            "locked_sequence_index": 0}]
        witnessed = plan_station_work_order(state, strategy="event_driven")
        self.assertEqual(witnessed["status"], "SATISFIED_PREFIX", repr(witnessed))
        self.assertEqual(witnessed["task_requests"], [])

    def test_store_only_locked_core_preserves_separate_repair_order_offer(self):
        from tools.native_platform_v0.p5.story_process.planning import plan_station_work_order

        state = self._station_state_for_work()
        state["sealed_minute"] = 5
        state["typed_trace"]["events"].append({
            "event_type": "p5_station_supply_inspected", "provenance": "committed_ledger",
            "time": 3, "native_receipt_id": "receipt-inspect-1",
            "native_commitment_id": "commitment-inspect-1",
            "native_task_kind": "inspect_supply",
            "args": {"actor": "A", "item": "3", "tool": "1"}})
        for actor in state["actors"].values():
            actor["local_view"]["observation"]["station_supplies"][0]["inspection_status"] = "APPROVED"
        sequence = [{"actor_alias": "A", "task_kind": "store_item",
                     "item_ref": "courier_supply", "destination_ref": "station_storage"}]
        digest = hashlib.sha256(json.dumps(sequence, sort_keys=True,
                                           separators=(",", ":")).encode()).hexdigest()
        fragment = {"sequence": sequence, "sequence_sha256": digest,
                    "entry_guard": {"task_grant_required": True,
                                    "supply_alias": "courier_supply",
                                    "storage_alias": "station_storage",
                                    "inspection_receipt_required": True},
                    "abort_policy": "ABORT_LOCKED_CORE"}
        state["constraints"] = [
            {"constraint_id": "repair-before-storage", "kind": "event_order",
             "source_constraint": {"kind": "event_order", "id": "repair-before-storage",
                 "before": {"event": "station_passage_repaired",
                            "filters": {"actor": "B", "tool": "station_tool",
                                        "exit": "pickup_to_side_south"}},
                 "after": {"event": "station_supply_stored",
                           "filters": {"actor": "A", "item": "courier_supply",
                                       "storage": "station_storage"}},
                 "order": "EVENT_KEY", "start": 0, "deadline": 20, "hard": True},
             "control": {"mode": "locked_fragment", "file_actor": "A",
                         "allowed_methods": ["inspect_then_repair", "repair_then_inspect"]},
             "locked_fragment": copy.deepcopy(fragment)},
            {"constraint_id": "supply-stored-by-horizon", "kind": "event_by_deadline",
             "source_constraint": {"kind": "event_by_deadline", "id": "supply-stored-by-horizon",
                 "event": "station_supply_stored", "filters": {"actor": "A",
                     "item": "courier_supply", "storage": "station_storage"},
                 "start": 0, "deadline": 20, "hard": True},
             "control": {"mode": "result_only", "file_actor": None,
                         "allowed_methods": ["inspect_then_repair", "repair_then_inspect"]}},
        ]
        state["grant_ids"] = {
            "repair-before-storage": "s1:repair-before-storage:fixed-native-grant",
            "supply-stored-by-horizon": "s1:supply-stored-by-horizon:fixed-native-grant"}

        result = plan_station_work_order(state, strategy="event_driven")
        feasible = [row for row in result["method_plans"] if row["feasible"]]
        self.assertTrue(feasible, repr(result))
        selected = feasible[0]
        requests = selected["task_requests"]
        repair = next(row for row in requests if row["task_kind"] == "repair_passage")
        self.assertIn("repair-before-storage", repair["required_constraint_ids"])
        self.assertEqual(repair["control_source"], "PLANNER")
        self.assertNotIn("locked_fragment_sha256", repair)
        self.assertNotIn("locked_sequence_index", repair)
        store = next(row for row in requests if row["task_kind"] == "store_item")
        self.assertEqual(store["control_source"], "LOCKED_FRAGMENT")
        self.assertEqual(store["locked_fragment_sha256"], digest)
        self.assertEqual(store["locked_sequence_index"], 0)
        self.assertEqual(store["constraint_id"], "repair-before-storage")
        self.assertEqual(store["grant_id"], "s1:repair-before-storage:fixed-native-grant")
        self.assertEqual(set(store["required_constraint_ids"]),
                         {"supply-stored-by-horizon", "repair-before-storage"})
        self.assertNotIn("tool_id", store)
        self.assertFalse(result["world_effects_applied"])

        completed = copy.deepcopy(state)
        completed["typed_trace"]["events"].append({
            "event_type": "p5_station_passage_repaired", "provenance": "committed_ledger",
            "time": 4, "native_receipt_id": "receipt-repair-1",
            "native_commitment_id": "commitment-repair-1",
            "native_task_kind": "repair_passage",
            "args": {"actor": "B", "tool": "1", "exit": "4"}})
        # Storage no longer needs the tool after both registered tool tasks
        # have real receipts; a remote/held/busy tool is not a store guard.
        completed["station_tool"] = {"id": 1, "room_id": 99, "holder_alias": "B",
                                     "lease_status": "BUSY"}
        completed["active_tool_lease"] = {"status": "BUSY", "due_minute": 24}
        after_repair = plan_station_work_order(completed, strategy="event_driven")
        feasible_after_repair = [row for row in after_repair["method_plans"] if row["feasible"]]
        self.assertTrue(feasible_after_repair, repr(after_repair))
        self.assertEqual([row["task_kind"] for row in after_repair["task_requests"]], ["store_item"])
        self.assertNotIn("locked_fragment_entry_guard_failed",
                         feasible_after_repair[0]["preconditions"])

    def test_real_store_lock_plan_adapts_prerequisite_as_planner_and_literal_store_as_locked(self):
        from types import SimpleNamespace
        from tools.native_platform_v0.p5.ongoing_station.controller import (
            _station_work_offers_from_decision,
        )
        from tools.native_platform_v0.p5.story_process.planning import plan_station_work_order

        state = self._station_state_for_work()
        state["sealed_minute"] = 5
        state["typed_trace"]["events"] = [{
            "event_type": "p5_station_supply_inspected", "provenance": "committed_ledger",
            "time": 3, "native_receipt_id": "receipt-inspect-1",
            "native_commitment_id": "commitment-inspect-1", "native_task_kind": "inspect_supply",
            "args": {"actor": "A", "item": "3", "tool": "1"}}]
        state["actors"]["A"]["local_view"]["observation"]["inventory"] = [{"id": 3}]
        state["actors"]["A"]["local_view"]["observation"]["station_supplies"] = [{
            "id": 3, "room_id": 5, "visible": True, "inspection_status": "APPROVED"}]
        sequence = [{"actor_alias": "A", "task_kind": "store_item",
                     "item_ref": "courier_supply", "destination_ref": "station_storage"}]
        digest = hashlib.sha256(json.dumps(sequence, sort_keys=True,
            separators=(",", ":")).encode()).hexdigest()
        state["constraints"] = [
            {"constraint_id": "repair-before-storage", "kind": "event_order",
             "source_constraint": {"kind": "event_order", "id": "repair-before-storage",
                 "before": {"event": "station_passage_repaired",
                            "filters": {"actor": "B", "tool": "station_tool",
                                        "exit": "pickup_to_side_south"}},
                 "after": {"event": "station_supply_stored",
                           "filters": {"actor": "A", "item": "courier_supply",
                                       "storage": "station_storage"}},
                 "order": "EVENT_KEY", "start": 0, "deadline": 20, "hard": True},
             "control": {"mode": "locked_fragment", "file_actor": "A",
                         "allowed_methods": ["inspect_then_repair", "repair_then_inspect"]},
             "locked_fragment": {"sequence": sequence, "sequence_sha256": digest,
                 "entry_guard": {"task_grant_required": True,
                                 "supply_alias": "courier_supply",
                                 "storage_alias": "station_storage",
                                 "inspection_receipt_required": True},
                 "abort_policy": "ABORT_LOCKED_CORE"}},
            {"constraint_id": "supply-stored-by-horizon", "kind": "event_by_deadline",
             "source_constraint": {"kind": "event_by_deadline", "id": "supply-stored-by-horizon",
                 "event": "station_supply_stored", "filters": {"actor": "A",
                     "item": "courier_supply", "storage": "station_storage"},
                 "start": 0, "deadline": 20, "hard": True},
             "control": {"mode": "result_only", "file_actor": None,
                         "allowed_methods": ["inspect_then_repair", "repair_then_inspect"]},
             "locked_fragment": None},
        ]
        state["grant_ids"] = {
            "repair-before-storage": "s1:repair-before-storage:fixed-native-grant",
            "supply-stored-by-horizon": "s1:supply-stored-by-horizon:fixed-native-grant"}
        projection = SimpleNamespace(station_id="s1", version=2, source_sha256="a" * 64,
            bundle_id="system-work-episode-v1", constraints=tuple(state["constraints"]))
        profile = SimpleNamespace(station_id="s1", version=1)
        sealed = {"station_id": "s1", "projection_id": "projection-2",
            "grant_ids": dict(state["grant_ids"]), "station_content": {
                "tool_id": 1, "storage_id": 2, "supply_id": 3, "repair_exit_id": 4,
                "workbench_room_id": 5, "storage_room_id": 6},
            "typed_trace": state["typed_trace"]}

        decision = plan_station_work_order(state, strategy="event_driven")
        self.assertEqual(decision["status"], "CONDITIONAL_PLAN", repr(decision))
        plan = next(row for row in decision["method_plans"]
                    if row["method_id"] == decision["selected_method"])
        repair = next(row for row in plan["task_requests"]
                      if row["task_kind"] == "repair_passage")
        self.assertEqual(repair["control_source"], "PLANNER")
        self.assertNotIn("locked_fragment_sha256", repair)
        repair_offer = _station_work_offers_from_decision(
            decision, projection, profile, sealed, 5)
        self.assertEqual(len(repair_offer), 1)
        self.assertEqual(repair_offer[0]["control_source"], "PLANNER")
        self.assertIsNone(repair_offer[0]["locked_fragment_hash"])
        order = projection.constraints[0]["source_constraint"]
        original_before = copy.deepcopy(order["before"])
        order["before"]["filters"]["actor"] = "A"
        with self.assertRaisesRegex(ValueError, "registered repair-before-store prerequisite"):
            _station_work_offers_from_decision(decision, projection, profile, sealed, 5)
        order["before"] = original_before

        state["typed_trace"]["events"].append({
            "event_type": "p5_station_passage_repaired", "provenance": "committed_ledger",
            "time": 7, "native_receipt_id": "receipt-repair-1",
            "native_commitment_id": "commitment-repair-1", "native_task_kind": "repair_passage",
            "args": {"actor": "B", "tool": "1", "exit": "4"}})
        decision = plan_station_work_order(state, strategy="event_driven")
        store = next(row for row in decision["task_requests"]
                     if row["task_kind"] == "store_item")
        self.assertEqual(store["control_source"], "LOCKED_FRAGMENT")
        self.assertEqual(store["locked_fragment_sha256"], digest)
        malformed = copy.deepcopy(decision)
        malformed_plan = next(row for row in malformed["method_plans"]
                              if row["method_id"] == malformed["selected_method"])
        next(row for row in malformed_plan["task_requests"]
             if row["task_kind"] == "store_item").pop("locked_fragment_sha256")
        with self.assertRaisesRegex(ValueError, "lacks exact sequence provenance"):
            _station_work_offers_from_decision(malformed, projection, profile, sealed, 7)
        store_offer = _station_work_offers_from_decision(
            decision, projection, profile, sealed, 7)
        self.assertEqual(len(store_offer), 1)
        self.assertEqual(store_offer[0]["task_kind"], "store_item")
        self.assertEqual(store_offer[0]["control_source"], "LOCKED_FRAGMENT")
        self.assertEqual(store_offer[0]["locked_fragment_hash"], digest)

    def test_station_work_does_not_skip_on_wrong_entity_receipt_or_filter(self):
        from tools.native_platform_v0.p5.story_process.planning import plan_station_work_order
        state = self._station_state_for_work()
        state["typed_trace"]["events"].append({
            "event_type": "p5_station_supply_inspected", "provenance": "committed_ledger",
            "time": 2, "native_receipt_id": "receipt-inspect-wrong-item",
            "native_commitment_id": "commitment-inspect-1",
            "native_task_kind": "inspect_supply",
            "args": {"actor": "A", "item": "999", "tool": "1"}})
        wrong_filter = {
            "constraint_id": "wrong-item-filter", "kind": "event_by_deadline",
            "source_constraint": {"kind": "event_by_deadline",
                "event": "station_supply_inspected", "start": 0, "deadline": 10,
                "filters": {"actor": "A", "item": "some_other_supply"}},
            "control": {"mode": "result_only",
                        "allowed_methods": ["inspect_then_repair", "repair_then_inspect"]}}
        state["constraints"] = [wrong_filter]
        result = plan_station_work_order(state)
        self.assertFalse(result["task_requests"])
        self.assertTrue(all(not row["feasible"] for row in result["method_plans"]))
        self.assertTrue(any(row["task_kind"] == "inspect_supply"
                            for row in result["method_plans"][0]["task_requests"]))

    def test_storage_goal_keeps_repair_as_native_self_support_not_author_requirement(self):
        from tools.native_platform_v0.p5.story_process.planning import plan_station_work_order
        state = self._station_state_for_work()
        state["constraints"] = [{
            "constraint_id": "storage-goal", "kind": "event_by_deadline",
            "source_constraint": {"id": "storage-goal", "kind": "event_by_deadline",
                "event": "station_supply_stored", "start": 0, "deadline": 20,
                "hard": True, "filters": {"actor": "A", "item": "courier_supply",
                                            "storage": "station_storage"}},
            "control": {"mode": "result_only",
                "allowed_methods": ["inspect_then_repair", "repair_then_inspect"]}},
        ]
        state["actors"]["B"]["local_view"]["observation"]["station_task_bindings"] = [{
            "task_kind": "repair_passage", "tool_id": 1, "target_id": 4,
            "target_room_id": 5}]
        result = plan_station_work_order(state)
        self.assertEqual(result["task_requests"][0]["task_kind"], "inspect_supply")
        self.assertEqual([row["task_kind"] for row in result["derived_support_tasks"]],
                         ["repair_passage"])
        support = result["derived_support_tasks"][0]
        self.assertEqual(support["source"], "NATIVE_SELF_GOAL")
        self.assertEqual(support["self_offer_id"], "self:12:repair_passage:4")
        self.assertFalse(support["required_constraint_ids"])

    def _station_state_for_work(self):
        # Kept separate so receipt tests cannot accidentally seed planner state
        # other than the committed event row above.
        observation = {"room_id": 5, "inventory": [],
                       "visible_items": [{"id": 3, "room_id": 5}],
                       "known_exits": {5: [6], 6: [5]},
                       "exits": [{"key": "east", "destination_id": 6}],
                       "station_tools": [{"id": 1, "room_id": 5, "visible": True,
                                          "held_by_actor_id": None, "lease_status": "FREE"}],
                       "station_supplies": [{"id": 3, "room_id": 5, "visible": True,
                                             "inspection_status": "UNINSPECTED"}],
                       "station_repair_targets": [{"id": 4, "room_id": 5, "traversable": False}],
                       "station_storages": [{"id": 2, "room_id": 6, "visible": True}]}
        return {"sealed_minute": 1, "horizon": 24, "station_id": "s1",
                "projection_id": "projection-1", "constraint_id": "inspect-goal",
                "grant_id": "s1:inspect-goal:fixed-native-grant",
                "station_content": {"tool_id": 1, "storage_id": 2, "supply_id": 3,
                                    "repair_exit_id": 4, "workbench_room_id": 5,
                                    "storage_room_id": 6},
                "station_tool": {"id": 1, "room_id": 5, "holder_alias": None,
                                 "lease_status": "FREE"},
                "active_tool_lease": None,
                "actors": {alias: {"actor_id": ident,
                                   "local_view": {"actor_id": ident,
                                                  "observation": copy.deepcopy(observation)},
                                   "commitments": [], "pending_action": None}
                           for alias, ident in (("A", 11), ("B", 12))},
                "typed_trace": {"events": []}, "constraints": []}


if __name__ == "__main__":
    unittest.main()
