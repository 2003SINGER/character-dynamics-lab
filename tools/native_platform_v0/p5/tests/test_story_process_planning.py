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
                 handover_minutes=2, task_status_a="IDLE", task_status_b="IDLE"):
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
                  "locally_observed_item_ids": [note_id], "active_task": None, "task_status": task_status_a},
            "B": {"present": b_present, "can_receive_note": True, "willing_to_archive": b_willing,
                  "locally_observed_item_ids": [note_id], "active_task": None, "task_status": task_status_b},
        },
        "destinations": {
            "archive": {"id": 601, "reachable_by": ["A", "B"], "estimated_minutes": archive_minutes},
            "handover": {"id": 602, "reachable_by": ["A", "B"], "estimated_minutes": handover_minutes},
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


if __name__ == "__main__":
    unittest.main()
