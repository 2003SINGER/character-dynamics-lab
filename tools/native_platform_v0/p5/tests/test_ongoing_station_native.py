import copy
import unittest
from unittest.mock import patch

from tools.native_platform_v0.p5.ongoing_station.native import (
    initialize_station, meta_for, profile_for,
)
from tools.native_platform_v0.p5.tests.test_ongoing_station_model import profile


class Attributes:
    def __init__(self):
        self.values = {}

    def add(self, key, value, category=None):
        self.values[(category, key)] = value

    def get(self, key, category=None, default=None):
        return self.values.get((category, key), default)


class Obj:
    def __init__(self):
        self.attributes = Attributes()


class OngoingStationNativeTests(unittest.TestCase):
    def test_workload_estimate_uses_only_receipt_and_local_primitive_lower_bounds(self):
        from types import SimpleNamespace
        from tools.native_platform_v0.p5.ongoing_station.controller import _remaining_work_lower_bound

        item = SimpleNamespace(id=71)
        actor = SimpleNamespace(id=10, contents=[item], location=SimpleNamespace(id=1, contents=[]))
        commitment = {"commitment_id": "self-1", "task_kind": "return_stock",
                      "item_id": 71, "destination_id": 3}
        self.assertEqual(_remaining_work_lower_bound(actor, commitment, []), 2)
        self.assertEqual(_remaining_work_lower_bound(actor, commitment, [{
            "receipt_id": "drop-1", "settled": True, "kind": "drop", "item_id": 71,
            "after_item_room_id": 3, "ongoing_commitment_id": "self-1",
            "ongoing_task_kind": "return_stock"}]), 0)

        actor.contents = []
        visible_item = SimpleNamespace(id=71, access=lambda *_args, **_kwargs: True)
        actor.location.contents = [visible_item]
        self.assertEqual(_remaining_work_lower_bound(actor, commitment, []), 3)
        actor.location.contents = []
        self.assertIsNone(_remaining_work_lower_bound(actor, commitment, []))

        route = {"commitment_id": "route-1", "task_kind": "routine_route",
                 "route_waypoints": [2, 1], "waypoint_receipts": ["move-1", None]}
        route_receipts = [{"receipt_id": "move-1", "settled": True, "kind": "move",
                           "after_room_id": 2, "ongoing_commitment_id": "route-1",
                           "ongoing_task_kind": "routine_route"}]
        self.assertEqual(_remaining_work_lower_bound(actor, route, route_receipts), 1)
        route_receipts.append({"receipt_id": "move-2", "settled": True, "kind": "move",
                               "after_room_id": 1, "ongoing_commitment_id": "route-1",
                               "ongoing_task_kind": "routine_route"})
        # The second native receipt is sealed, but waypoint_receipts still
        # contains None until the next actor callback refreshes the commitment.
        self.assertEqual(_remaining_work_lower_bound(actor, route, route_receipts), 0)
        out_of_order = {**route, "waypoint_receipts": [None, "move-2"]}
        self.assertIsNone(_remaining_work_lower_bound(actor, out_of_order, [route_receipts[1]]))

    def test_note_binding_uses_real_social_request_receipt_and_request_bound_note(self):
        from tools.native_platform_v0.p5.ongoing_station.controller import _note_binding

        note = Obj()
        note.id = 71
        note.key = "Love note"
        note.attributes.add("p4_note_request_id", "request-7", category="native_p3")
        ledger = [{"event_type": "SOCIAL_REQUEST", "sealed": True, "minute": 3,
                   "typed_args": {"request_id": "request-7", "note_id": 71,
                       "initiator_actor_id": 10, "recipient_actor_id": 20,
                       "physical_receipt": {"status": "settled", "receipt_id": "receipt-7",
                           "after_location_id": 20, "recipient_inventory_actor_id": 20}}}]
        # The P4 producer records the exact note in typed_args and binds the created
        # note object by p4_note_request_id; its receipt intentionally has no item_id.
        self.assertEqual(_note_binding([note], ledger, 3), 71)
        ledger[0]["typed_args"]["request_id"] = "different-request"
        self.assertIsNone(_note_binding([note], ledger, 3))

    def test_author_verdict_readback_imports_service_and_returns_monitor_results(self):
        from tools.native_platform_v0.p5.ongoing_station.controller import _author_verdicts
        from tools.native_platform_v0.p5.tests.test_ongoing_station_model import author

        note = Obj()
        note.id = 71
        note.key = "Love note"
        verdicts = _author_verdicts("scene-1", Obj(), [note], author(), 71, [], 0)
        self.assertEqual(verdicts["hard_status"], "PENDING")
        self.assertTrue(verdicts["constraints"])

    def test_null_author_profile_initializes_autonomy_state_without_author_goal(self):
        pickup, actor_a, actor_b = Obj(), Obj(), Obj()
        loaded = initialize_station(pickup, {"A": actor_a, "B": actor_b}, profile(horizon=40))
        self.assertEqual(loaded.horizon, 40)
        self.assertEqual(profile_for(pickup).station_id, "station-1")
        self.assertEqual(meta_for(pickup)["author_status"], "ABSENT")
        for actor in (actor_a, actor_b):
            self.assertEqual(actor.attributes.get("ongoing_commitments", category="native_p5"), [])
            self.assertEqual(actor.attributes.get("ongoing_goal_history", category="native_p5"), [])
            self.assertIsNone(actor.attributes.get("ongoing_task_offer", category="native_p5"))

    def test_online_edit_can_add_registered_same_note_handover_pair_future_only(self):
        from tools.native_platform_v0.p5.ongoing_station.model import derive_story_requirements
        from tools.native_platform_v0.p5.ongoing_station.native import active_projection, activate_author, edit_author
        from tools.native_platform_v0.p5.tests.test_ongoing_station_model import author

        author_v1 = author()
        author_v1["bundle"]["constraints"] = author_v1["bundle"]["constraints"][:1]
        author_v1["bindings"] = author_v1["bindings"][:1]
        station = profile(author_v1)
        pickup = Obj()
        initialize_station(pickup, {}, station)
        self.assertTrue(activate_author(pickup, expected_version=1, now=5)["ok"])
        author_v2 = copy.deepcopy(author_v1)
        author_v2["bundle"]["version"] = 2
        author_v2["bundle"]["constraints"].extend([
            {"id": "handover-occurs", "kind": "event_by_deadline", "event": "note_handed_over",
             "filters": {"actor": "B", "recipient": "A", "item": "note"},
             "start": 6, "deadline": 24, "hard": True, "min_count": 1, "max_count": 1},
            {"id": "handover-before-archive", "kind": "event_order",
             "before": {"event": "note_handed_over",
                        "filters": {"actor": "B", "recipient": "A", "item": "note"}},
             "after": {"event": "note_archived", "filters": {"item": "note"}},
             "order": "EVENT_KEY", "start": 6, "deadline": 24, "hard": True},
        ])
        base_binding = author_v2["bindings"][0]
        author_v2["bindings"].extend([
            {**copy.deepcopy(base_binding), "constraint_id": "handover-occurs"},
            {**copy.deepcopy(base_binding), "constraint_id": "handover-before-archive"},
        ])
        updated = edit_author(pickup, author_v2, expected_version=1, now=6)
        self.assertEqual(updated["status"], "UPDATED")
        projection = active_projection(pickup)
        archive = next(row for row in projection.constraints if row["constraint_id"] == "archive-goal")
        required = derive_story_requirements(projection, archive, 71)
        self.assertEqual(required["required_handover"]["start_minute"], 6)
        self.assertEqual(required["required_handover"]["deadline_minute"], 24)

    def test_invalid_station_profile_rejected_before_evennia_or_scene_creation(self):
        from tools.native_platform_v0.p5.service import reset_p5_scenario
        from tools.native_platform_v0.p5.tests.test_p5_bundle import sample

        invalid = profile()
        invalid["extra"] = "must fail closed"
        with patch.dict("sys.modules", {"evennia": None}):
            result = reset_p5_scenario(owner=None, bundle=sample(), ongoing_station=invalid)
        self.assertFalse(result["scene_created"])
        self.assertEqual(result["error"]["code"], "INVALID_ONGOING_STATION")

    def test_controller_request_is_a_strict_projection_of_the_bundle_constraint(self):
        from tools.native_platform_v0.p5.ongoing_station.controller import _runtime_request
        from tools.native_platform_v0.p5.ongoing_station.model import compile_projection, load_profile
        from tools.native_platform_v0.p5.story_process.model import load_request
        from tools.native_platform_v0.p5.tests.test_ongoing_station_model import author

        projection = compile_projection(load_profile(profile(author())))
        constraint = next(row for row in projection.constraints if row["constraint_id"] == "archive-goal")
        raw = _runtime_request(load_profile(profile(author())), projection, constraint,
                               constraint["control"], "scene-1", 71)
        request = load_request(raw)
        self.assertEqual(request.objective["note_id"], 71)
        self.assertEqual(request.objective["by_minute"], 24)
        self.assertEqual(request.control["allowed_methods"], ["file_by_B", "return_then_file_by_A"])

    def test_station_typed_event_requires_matching_physical_native_receipt(self):
        from tools.native_platform_v0.p5.ongoing_station.controller import _typed_events
        from tools.native_platform_v0.p5 import service

        actor_a, actor_b = Obj(), Obj()
        actor_a.id, actor_b.id = 10, 20
        actor_a.contents, actor_b.contents = [], []
        actor_a.attributes.add("native_receipts", [{"receipt_id": "receipt-1", "kind": "drop",
            "settled": True, "item_id": 71, "after_item_room_id": 90,
            "ongoing_commitment_id": "commit-1"}], category="native_p3")
        actor_a.attributes.add("ongoing_commitments", [{"commitment_id": "commit-1",
            "task_kind": "archive_note", "destination_id": 90}], category="native_p5")
        actors = {"A": actor_a, "B": actor_b}
        ledger = [{"event_id": "station-receipt:receipt-1",
                   "event_type": "P5_ONGOING_STATION_NOTE_ARCHIVED", "version": 1,
                   "minute": 1, "sequence": 4,
                   "typed_args": {"receipt_id": "receipt-1", "commitment_id": "commit-1",
                       "actor_alias": "A", "item_id": 71, "settled": True}}]
        events = _typed_events("scene-1", 71, 1, ledger, actors, service, all_rows=[actor_a, actor_b])
        self.assertEqual([row["event_type"] for row in events], ["p5_note_archived"])
        actor_a.attributes.add("native_receipts", [], category="native_p3")
        self.assertEqual(_typed_events("scene-1", 71, 1, ledger, actors, service,
                                       all_rows=[actor_a, actor_b]), [])

    def test_handover_binds_distinct_registered_recipient_and_needs_real_give(self):
        from tools.native_platform_v0.p5.ongoing_station.controller import (
            _is_b_to_a_handover, _recipient_id, _typed_events,
            _verified_handover_in_window,
        )
        from tools.native_platform_v0.p5 import service

        actor_a, actor_b = Obj(), Obj()
        actor_a.id, actor_b.id = 10, 20
        actor_a.contents, actor_b.contents = [], []
        self.assertEqual(_recipient_id({"actor_alias": "B"}, "A", {"A": actor_a, "B": actor_b}), 10)
        with self.assertRaises(ValueError):
            _recipient_id({"actor_alias": "A"}, "A", {"A": actor_a, "B": actor_b})
        actor_b.attributes.add("native_receipts", [{"receipt_id": "give-1", "kind": "give",
            "settled": True, "item_id": 71, "recipient_id": 10,
            "recipient_inventory_ids": [71], "ongoing_commitment_id": "commit-give"}],
            category="native_p3")
        actor_b.attributes.add("ongoing_commitments", [{"commitment_id": "commit-give",
            "task_kind": "handover_note", "destination_id": 90}], category="native_p5")
        ledger = [{"event_id": "station-receipt:give-1",
                   "event_type": "P5_ONGOING_STATION_NOTE_HANDED_OVER", "version": 1,
                   "minute": 2, "sequence": 5,
                   "typed_args": {"receipt_id": "give-1", "commitment_id": "commit-give",
                       "actor_alias": "B", "recipient_alias": "A", "item_id": 71,
                       "settled": True}}]
        events = _typed_events("scene-1", 71, 2, ledger, {"A": actor_a, "B": actor_b},
                               service, all_rows=[actor_a, actor_b])
        self.assertEqual(len(events), 1)
        self.assertTrue(_is_b_to_a_handover(events[0], 71))
        requirement = {"start_minute": 10, "deadline_minute": 20}
        self.assertTrue(_verified_handover_in_window([{**events[0], "time": 12}], 71, requirement))
        self.assertFalse(_verified_handover_in_window(
            [{**events[0], "time": 9}], 71, requirement))
        self.assertFalse(_verified_handover_in_window(
            [{**events[0], "time": 21}], 71, requirement))
        actor_b.attributes.add("native_receipts", [], category="native_p3")
        self.assertEqual(_typed_events("scene-1", 71, 2, ledger, {"A": actor_a, "B": actor_b},
                                       service, all_rows=[actor_a, actor_b]), [])

    def test_return_method_continues_to_A_archive_only_after_verified_give(self):
        from tools.native_platform_v0.p5.ongoing_station.controller import _continuation_archive_task
        from tools.native_platform_v0.p5.ongoing_station.model import compile_projection, load_profile
        from tools.native_platform_v0.p5.ongoing_station.controller import _runtime_request
        from tools.native_platform_v0.p5.story_process.model import load_request
        from tools.native_platform_v0.p5.tests.test_ongoing_station_model import author

        station = load_profile(profile(author()))
        projection = compile_projection(station)
        constraint = next(row for row in projection.constraints if row["constraint_id"] == "archive-goal")
        request = load_request(_runtime_request(station, projection, constraint,
                                                constraint["control"], "scene-1", 71))
        destinations = {"archive": {"id": 90}, "handover": {"id": 80}}
        self.assertIsNone(_continuation_archive_task(
            request, constraint, 71, destinations, "return_then_file_by_A", False))
        task = _continuation_archive_task(
            request, constraint, 71, destinations, "return_then_file_by_A", True)
        self.assertEqual(task["actor_alias"], "A")
        self.assertEqual(task["item_id"], 71)
        self.assertEqual(task["destination_id"], 90)
        self.assertEqual(task["rendezvous_destination_id"], 80)
        self.assertIn("committed_native_handover_receipt_for_exact_note_at_rendezvous",
                      task["prerequisites"])
        self.assertIsNone(_continuation_archive_task(
            request, constraint, 71, destinations, "file_by_B", True))

    def test_edit_cancels_only_planned_stale_author_action_not_executing_action(self):
        from types import SimpleNamespace
        from tools.native_platform_v0.p5.ongoing_station.controller import _cancel_stale_planned_pending

        service = SimpleNamespace(
            _attr=lambda actor, key, category=None, default=None:
                actor.attributes.get(key, category=category, default=default),
            _plain_json=lambda value: value,
            _set=lambda actor, key, value, category=None:
                actor.attributes.add(key, value, category=category),
        )
        for state, expected in (("planned", "CANCELLED_STALE"), ("executing", "IN_PROGRESS")):
            actor = Obj()
            actor.attributes.add("pending_action", {"status": state, "ongoing_task": {
                "source": "AUTHOR", "source_offer_id": "offer-v1",
                "commitment_id": "offer-v1"}}, category="native_p3")
            actor.attributes.add("ongoing_commitments", [{"commitment_id": "offer-v1",
                "source": "AUTHOR", "status": "IN_PROGRESS"}], category="native_p5")
            actor.attributes.add("ongoing_goal_history", [], category="native_p5")
            with patch("tools.native_platform_v0.p3.agency.record") as record:
                result = _cancel_stale_planned_pending(actor, "B", ["offer-v1"], 9, service)
            commitment = actor.attributes.get("ongoing_commitments", category="native_p5")[0]
            self.assertEqual(commitment["status"], expected)
            if state == "planned":
                self.assertEqual(result["status"], "CANCELLED_STALE")
                self.assertIsNone(actor.attributes.get("pending_action", category="native_p3"))
                record.assert_called_once()
                self.assertEqual(actor.attributes.get("ongoing_goal_history", category="native_p5")[-1]["event"],
                                 "COMMITMENT_CANCELLED_STALE")
            else:
                self.assertIsNone(result)
                self.assertEqual(actor.attributes.get("pending_action", category="native_p3")["status"],
                                 "executing")
                record.assert_not_called()

    def test_historical_archive_guard_requires_exact_committed_note_event(self):
        from tools.native_platform_v0.p5.ongoing_station.controller import _has_verified_archive_for_note
        row = {"event_type": "p5_note_archived", "provenance": "committed_ledger",
               "args": {"item": {"entity_type": "Item", "stable_id": "71"}}}
        self.assertTrue(_has_verified_archive_for_note([row], 71))
        self.assertFalse(_has_verified_archive_for_note([row], 72))
        self.assertFalse(_has_verified_archive_for_note([{**row, "provenance": "planned"}], 71))

    def test_locked_core_binding_has_independent_method_and_receipt_gated_sequence(self):
        from types import SimpleNamespace
        from tools.native_platform_v0.p5.ongoing_station.controller import (
            _apply_locked_method_intersection, _locked_core_method, _next_locked_task,
        )

        fragment = {"sequence": [
            {"actor_alias": "B", "task_kind": "handover_note",
             "item_ref": "objective.note", "destination_ref": "handover"},
            {"actor_alias": "A", "task_kind": "archive_note",
             "item_ref": "objective.note", "destination_ref": "archive"},
        ]}
        locked_hash = "sequence-hash-v1"
        request = SimpleNamespace(locked_fragment={**fragment, "sequence_sha256": locked_hash},
                                  task_control_grant={"grant_id": "grant-lock"},
                                  request_id="station:respond-before-archive", version=2)
        rows = [{"request_id": "req:v1:locked:0", "actor_alias": "B",
                 "task_kind": "handover_note", "source_method_id": "locked_fragment"},
                {"request_id": "req:v1:locked:1", "actor_alias": "A",
                 "task_kind": "archive_note", "source_method_id": "locked_fragment"}]
        self.assertEqual(_locked_core_method(fragment), "return_then_file_by_A")
        decision = {"selected_method": "file_by_B", "task_requests": [{"source_method_id": "file_by_B"}],
                    "method_plans": [{"method_id": "file_by_B", "feasible": True},
                                     {"method_id": "return_then_file_by_A", "feasible": True}]}
        binding = {"constraint_id": "locked-order"}
        constrained, compatible = _apply_locked_method_intersection(
            decision, binding, "return_then_file_by_A")
        self.assertIsNotNone(compatible)
        self.assertEqual(constrained["search_selected_method"], "file_by_B")
        self.assertEqual(constrained["selected_method"], "return_then_file_by_A")
        rejected, compatible = _apply_locked_method_intersection(
            {**decision, "method_plans": [{"method_id": "file_by_B", "feasible": True}]},
            binding, "return_then_file_by_A")
        self.assertIsNone(compatible)
        self.assertEqual(rejected["status"], "LOCKED_CONSTRAINT_CONFLICT")
        self.assertEqual(_next_locked_task(request, rows, [], 71, "locked-order"), rows[0])
        give = {"event_id": "event-give", "event_type": "p5_note_handed_over",
            "time": 18, "sequence": 2,
            "provenance": "committed_ledger", "args": {
            "actor": {"stable_id": "B"}, "recipient": {"stable_id": "A"},
            "item": {"stable_id": "71"}}, "native_control_source": "LOCKED_FRAGMENT",
            "native_constraint_id": "locked-order", "native_source_method_id": "locked_fragment",
            "native_grant_id": "grant-lock", "native_locked_fragment_hash": locked_hash,
            "native_locked_sequence_index": 0}
        self.assertEqual(_next_locked_task(request, rows, [give], 71, "locked-order"), rows[1])
        suffix = _next_locked_task(request, [], [give], 71, "locked-order",
                                   destinations={"archive": {"id": 90}, "handover": {"id": 80}})
        self.assertEqual(suffix["actor_alias"], "A")
        self.assertEqual(suffix["task_kind"], "archive_note")
        self.assertEqual(suffix["destination_id"], 90)
        self.assertEqual(suffix["control_source"], "LOCKED_FRAGMENT")
        self.assertEqual(suffix["grant_id"], "grant-lock")
        self.assertEqual(suffix["locked_fragment_hash"], locked_hash)
        self.assertEqual(suffix["locked_sequence_index"], 1)
        unsealed = {**give, "provenance": "planner_proposal"}
        self.assertEqual(_next_locked_task(request, rows, [unsealed], 71, "locked-order"), rows[0])
        # A real same-note give from another author constraint is not evidence
        # that this locked fragment's first sequence step was executed.
        unrelated = {**give, "native_constraint_id": "archive-note-by-horizon"}
        self.assertEqual(_next_locked_task(request, rows, [unrelated], 71, "locked-order"), rows[0])
        archived = {"event_id": "event-archive", "event_type": "p5_note_archived",
            "time": 19, "sequence": 3,
            "provenance": "committed_ledger", "args": {
            "actor": {"stable_id": "A"}, "item": {"stable_id": "71"}},
            "native_control_source": "LOCKED_FRAGMENT", "native_constraint_id": "locked-order",
            "native_source_method_id": "locked_fragment", "native_grant_id": "grant-lock",
            "native_locked_fragment_hash": locked_hash, "native_locked_sequence_index": 1}
        self.assertIsNone(_next_locked_task(request, rows, [give, archived], 71, "locked-order"))

    def test_real_result_search_and_separate_locked_core_conflict_then_alignment(self):
        from tools.native_platform_v0.p5.story_process.model import load_request
        from tools.native_platform_v0.p5.story_process.planning import plan_story_process
        from tools.native_platform_v0.p5.tests.test_story_process_planning import raw_request, sealed_state

        # The actual planner must first select B's feasible result-only method,
        # then report conflict with the independently authored B->A locked core.
        request = load_request(raw_request(mode="result_only", note_id=71, file_actor="B"))
        state = sealed_state(request, outcome="accepted", holder="B")
        searched = plan_story_process(request, state, strategy="gtpyhop")
        locked = {"constraint_id": "respond-before-archive"}
        from tools.native_platform_v0.p5.ongoing_station.controller import _apply_locked_method_intersection
        conflict, compatible = _apply_locked_method_intersection(
            searched, locked, "return_then_file_by_A")
        self.assertIsNone(compatible)
        self.assertEqual(searched["selected_method"], "file_by_B")
        self.assertEqual(conflict["status"], "LOCKED_CONSTRAINT_CONFLICT")
        self.assertEqual(conflict["task_requests"], [])

        # The future edit changes only filer eligibility; the same real method
        # search now permits the locked core without changing the objective.
        edited = load_request(raw_request(mode="result_only", note_id=71,
                                          file_actor="A", version=2))
        state_v2 = sealed_state(edited, outcome="accepted", holder="B")
        searched_v2 = plan_story_process(edited, state_v2, strategy="gtpyhop")
        aligned, compatible = _apply_locked_method_intersection(
            searched_v2, locked, "return_then_file_by_A")
        self.assertIsNotNone(compatible)
        self.assertEqual(aligned["selected_method"], "return_then_file_by_A")
        self.assertTrue(aligned["execution_constrained_by_locked_binding"])

    def test_successful_edit_exposes_new_projection_without_publishing_offers(self):
        from types import SimpleNamespace
        from tools.native_platform_v0.p5.ongoing_station import controller

        pickup, actor_a, actor_b = Obj(), SimpleNamespace(id=11), SimpleNamespace(id=12)
        profile_row = SimpleNamespace(station_id="station-1", version=1, horizon=24)
        projection = SimpleNamespace(station_id="station-1", bundle_id="bundle-1", version=2,
                                     source_sha256="new-hash", constraints=(), bindings={})
        meta = {"task_offers": [], "published_projection": {"version": 1},
                "projection_history": [{"version": 1, "projection_id": "station-1:1:old"}]}
        stored = {}

        def attr(obj, key, category=None, default=None):
            aliases = {id(actor_a): "A", id(actor_b): "B"}
            if key == "p5_actor_alias" and id(obj) in aliases:
                return aliases[id(obj)]
            if key == "p4_note_request_id":
                return None
            if key == "p5_story_archive":
                return False
            return default

        with (patch("tools.native_platform_v0.p5.service._scene_objects",
                    return_value=(pickup, [actor_a, actor_b])),
              patch("tools.native_platform_v0.p5.service._attr", side_effect=attr),
              patch("tools.native_platform_v0.p5.service._plain_json", side_effect=lambda value: value),
              patch.object(controller, "evidence", return_value={"real_verdicts": {}}),
              patch.object(controller.native, "edit_author", return_value={
                  "ok": True, "status": "UPDATED", "version": 2,
                  "stale_projection_ids": ["station-1:1:old"]}),
              patch.object(controller.native, "active_projection", return_value=projection),
              patch.object(controller.native, "profile_for", return_value=profile_row),
              patch.object(controller.native, "meta_for", return_value=meta),
              patch.object(controller.native, "_store_meta",
                           side_effect=lambda _pickup, value: stored.update(value)),
              patch("tools.native_platform_v0.p3.p4_world.append_event")):
            result = controller.record_edit("scene-1", {"author": "source"}, 1, 6)

        self.assertEqual(result["status"], "UPDATED")
        self.assertEqual(stored["published_projection"]["version"], 2)
        self.assertEqual(stored["published_projection"]["bundle_hash"], "new-hash")
        self.assertEqual(stored["task_offers"], [])
        self.assertEqual(result["stale_projection_ids"], ["station-1:1:old"])
        self.assertEqual(result["cancelled_planned_tasks"], [])

    def test_real_locked_planner_abort_after_give_continues_exact_A_suffix(self):
        import hashlib
        import json
        from tools.native_platform_v0.p5.story_process.model import load_request
        from tools.native_platform_v0.p5.story_process.planning import plan_story_process
        from tools.native_platform_v0.p5.tests.test_story_process_planning import raw_request, sealed_state
        from tools.native_platform_v0.p5.ongoing_station.controller import (
            _locked_prefix_count, _next_locked_task,
        )

        sequence = [
            {"actor_alias": "B", "task_kind": "handover_note",
             "item_ref": "objective.note", "destination_ref": "handover"},
            {"actor_alias": "A", "task_kind": "archive_note",
             "item_ref": "objective.note", "destination_ref": "archive"},
        ]
        digest = hashlib.sha256(json.dumps(
            sequence, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        raw = raw_request(mode="locked_fragment", note_id=71, methods=["return_then_file_by_A"])
        raw["locked_fragment"] = {"sequence": sequence, "sequence_sha256": digest,
                                  "entry_guard": {"response_required": True,
                                                  "note_holder_alias": "B"},
                                  "abort_policy": "ABORT_LOCKED_CORE"}
        request = load_request(raw)
        state = sealed_state(request, now=18, outcome="accepted", holder="A")
        give = {"event_id": "native-give-1", "event_type": "p5_note_handed_over",
                "version": "1", "provenance": "committed_ledger", "time": 18,
                "sequence": 2,
                "args": {"actor": {"entity_type": "Actor", "stable_id": "B"},
                         "recipient": {"entity_type": "Actor", "stable_id": "A"},
                         "item": {"entity_type": "Item", "stable_id": "71"}},
                "native_commitment_id": "lock-give-commitment",
                "native_constraint_id": "respond-before-archive",
                "native_control_source": "LOCKED_FRAGMENT",
                "native_source_method_id": "locked_fragment",
                "native_grant_id": request.task_control_grant["grant_id"],
                "native_locked_fragment_hash": digest,
                "native_locked_sequence_index": 0}
        state["typed_trace"]["events"].append(give)
        # The original planner correctly preserves its entry guard and aborts;
        # only the ongoing adapter may continue after authenticating the prefix.
        decision = plan_story_process(request, state, strategy="gtpyhop")
        self.assertEqual(decision["status"], "LOCKED_ABORTED")
        self.assertEqual(decision["task_requests"], [])
        prefix = _locked_prefix_count(request, state["typed_trace"]["events"], 71,
                                      "respond-before-archive")
        self.assertEqual(prefix, 1)
        suffix = _next_locked_task(request, decision["task_requests"],
                                   state["typed_trace"]["events"], 71,
                                   "respond-before-archive",
                                   destinations=state["destinations"], prefix_count=prefix)
        self.assertEqual(suffix["actor_alias"], "A")
        self.assertEqual(suffix["task_kind"], "archive_note")
        self.assertEqual(suffix["item_id"], 71)
        self.assertEqual(suffix["destination_id"], state["destinations"]["archive"]["id"])
        self.assertEqual(suffix["control_source"], "LOCKED_FRAGMENT")
        self.assertEqual(suffix["constraint_id"], "respond-before-archive")
        self.assertEqual(suffix["grant_id"], request.task_control_grant["grant_id"])
        self.assertEqual(suffix["locked_fragment_hash"], digest)
        self.assertEqual(suffix["locked_sequence_index"], 1)
        # The result-only search sees the post-give holder and therefore does
        # not claim the original return method is newly feasible. Continuation
        # is allowed only by the current v2 binding plus the verified prefix.
        result_request = load_request(raw_request(mode="result_only", note_id=71,
                                                  file_actor="A"))
        result_state = sealed_state(result_request, now=18, outcome="accepted", holder="A")
        result_state["typed_trace"]["events"].append(give)
        result_decision = plan_story_process(result_request, result_state, strategy="gtpyhop")
        from tools.native_platform_v0.p5.ongoing_station.controller import _apply_locked_method_intersection
        continued, compatible = _apply_locked_method_intersection(
            result_decision, {"constraint_id": "respond-before-archive"},
            "return_then_file_by_A", verified_prefix_count=prefix,
            verified_continuation=True)
        self.assertIsNotNone(compatible)
        self.assertFalse(continued["combined_locked_core"]["compatible_method_feasible"])
        self.assertTrue(continued["combined_locked_core"]["continuation_from_verified_prefix"])
        self.assertEqual(continued["selected_method"], "return_then_file_by_A")
        self.assertEqual(continued["planner_status"], result_decision["status"])
        self.assertEqual(continued["adapter_status"], "CONTINUE_VERIFIED_LOCKED_SUFFIX")

    def test_future_edit_preserves_still_authorized_task_and_invalidates_affected_method(self):
        from tools.native_platform_v0.p5.ongoing_station.controller import _still_authorized_after_edit

        binding = {"control": {"mode": "result_only", "allowed_methods": [
            "file_by_B", "return_then_file_by_A"], "file_actor": None}, "locked_fragment": None}
        destinations = {"archive": 90, "handover": 80}
        actors = {"A": 10, "B": 20}
        b_archive = {"actor_alias": "B", "task_kind": "archive_note",
                     "source_method_id": "file_by_B", "destination_id": 90}
        self.assertTrue(_still_authorized_after_edit(b_archive, binding,
                                                     destinations=destinations, actor_ids=actors))
        # Adding an authored same-note handover count/order pair changes causal
        # support even if the archive constraint's binding itself is unchanged.
        self.assertFalse(_still_authorized_after_edit(
            b_archive, binding, destinations=destinations, actor_ids=actors,
            requires_handover=True))
        edited_for_a = {**binding, "control": {**binding["control"], "file_actor": "A"}}
        self.assertFalse(_still_authorized_after_edit(b_archive, edited_for_a,
                                                      destinations=destinations, actor_ids=actors))
        give = {"actor_alias": "B", "task_kind": "handover_note",
                "source_method_id": "return_then_file_by_A", "destination_id": 80,
                "recipient_alias": "A", "recipient_id": 10}
        self.assertTrue(_still_authorized_after_edit(give, binding,
                                                     destinations=destinations, actor_ids=actors))
        archive_a = {"actor_alias": "A", "task_kind": "archive_note",
                     "source_method_id": "return_then_file_by_A", "destination_id": 90,
                     "rendezvous_destination_id": 80}
        self.assertTrue(_still_authorized_after_edit(archive_a, binding,
                                                     destinations=destinations, actor_ids=actors))
        self.assertFalse(_still_authorized_after_edit(
            {**archive_a, "rendezvous_destination_id": 81}, binding,
            destinations=destinations, actor_ids=actors))


if __name__ == "__main__":
    unittest.main()
