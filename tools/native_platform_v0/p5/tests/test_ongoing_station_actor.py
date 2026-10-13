import unittest
from types import SimpleNamespace
from unittest.mock import patch

from tools.native_platform_v0.p3.agency import _dispatch_pending
from tools.native_platform_v0.p3.planning import thaw
from tools.native_platform_v0.p3.planning import plan_actor_task
from tools.native_platform_v0.p5.ongoing_station.goals import arbitrate, refresh_commitment
from tools.native_platform_v0.p5.ongoing_station.actor import advance_actor, _local_signature


def local_view(room_id=1, held=False, item_room=1):
    return {
        "actor_id": 9,
        "activity_contract": {"profile": "ongoing_station_v1"},
        "goal_contract": {"goal": "deliver_supply", "item_id": 10,
                           "destination_id": 2, "source": "scenario-authored-task"},
        "observation": {
            "room_id": room_id,
            "inventory": [{"id": 10, "key": "Supply"}] if held else [],
            "visible_items": [] if held else ([{"id": 10, "key": "Supply", "room_id": item_room}]
                                                if item_room == room_id else []),
            "task_item": {"id": 10, "key": "Supply"}, "task_destination": 2,
            "item_location": None if held else item_room, "item_held": held,
            "delivered": False, "own_delivery_receipts": [],
            "known_exits": {1: [2], 2: [1]},
            "exits": ([{"key": "east", "destination_id": 2}] if room_id == 1 else
                      [{"key": "west", "destination_id": 1}]),
            "retained_witnesses": [],
        },
    }


class Attrs:
    def __init__(self):
        self.values = {}

    def get(self, key, category=None, default=None):
        return self.values.get((category, key), default)

    def add(self, key, value, category=None):
        self.values[(category, key)] = value


class Actor:
    id = 9

    def __init__(self):
        self.attributes = Attrs()


class Room:
    id = 2

    def __init__(self):
        self.contents = []


class Thing:
    def __init__(self, ident, key, location):
        self.id, self.key, self.location = ident, key, location
        self.dbref = f"#{ident}"
        self.contents = []

    def access(self, actor, access_type, default=False):
        return True


class GivingActor(Thing):
    def __init__(self, ident, location, recipient, item):
        super().__init__(ident, "A", location)
        self.attributes = Attrs()
        self.ndb = SimpleNamespace(p3_pending_operation_id=None)
        self.contents.append(item)
        location.contents.extend([self, recipient])

    def execute_cmd(self, command):
        self.attributes.add("submitted_command", command, category="native_p3")
        item = self.contents.pop()
        recipient = next(row for row in self.location.contents if row.id == 22)
        recipient.contents.append(item)


class OngoingStationActorTests(unittest.TestCase):
    def test_shared_task_htn_uses_real_item_for_archive_and_handover(self):
        archive = plan_actor_task(local_view(), {
            "goal_id": "archive-1", "task_kind": "archive_note", "item_id": 10,
            "destination_id": 2, "last_known_item_room": 1,
        })
        self.assertEqual(archive["status"], "SOLVED")
        self.assertEqual(archive["intent"], {"operator": "get", "item_id": 10})
        self.assertEqual(archive["shared_method_domain"], "p3-ongoing-actor-local")

        handover = plan_actor_task(local_view(held=True, item_room=None), {
            "goal_id": "handover-1", "task_kind": "handover_note", "item_id": 10,
            "destination_id": 2, "recipient_id": 22,
        })
        self.assertEqual(handover["status"], "SOLVED")
        self.assertEqual(handover["intent"]["operator"], "move")
        self.assertNotIn("__route_marker__", repr(handover))

        at_handover = plan_actor_task(local_view(room_id=2, held=True, item_room=None), {
            "goal_id": "handover-1", "task_kind": "handover_note", "item_id": 10,
            "destination_id": 2, "recipient_id": 22,
        })
        self.assertEqual(at_handover["intent"], {"operator": "give", "item_id": 10,
                                                  "recipient_id": 22})

    def test_routine_route_is_a_real_route_task_not_an_item_operation(self):
        result = plan_actor_task(local_view(), {
            "goal_id": "route-1", "task_kind": "routine_route", "item_id": None,
            "destination_id": 2,
        })
        self.assertEqual(result["status"], "SOLVED")
        self.assertEqual(result["intent"], {"operator": "move", "exit_key": "east",
                                             "destination_id": 2})
        self.assertTrue(all(step["operator"] == "move" for step in result["plan"]))

    def test_route_commitment_requires_its_own_ordered_round_trip_receipts(self):
        commitment = {"commitment_id": "route-roundtrip", "task_kind": "routine_route",
                      "status": "IN_PROGRESS", "route_origin_id": 1,
                      "route_waypoints": [2, 1], "waypoint_receipts": [None, None],
                      "receipt_frontier": ["old"], "receipt_ids": []}
        unrelated = {"receipt_id": "other", "kind": "move", "settled": True,
                     "before_room_id": 1, "after_room_id": 2,
                     "ongoing_commitment_id": "other-goal"}
        outbound = {"receipt_id": "out", "kind": "move", "settled": True,
                    "before_room_id": 1, "after_room_id": 2,
                    "ongoing_commitment_id": "route-roundtrip"}
        partial = refresh_commitment(commitment, [unrelated, outbound], 5)
        self.assertEqual(partial["status"], "IN_PROGRESS")
        self.assertEqual(partial["waypoint_receipts"], ["out", None])

        inbound = {"receipt_id": "in", "kind": "move", "settled": True,
                   "before_room_id": 2, "after_room_id": 1,
                   "ongoing_commitment_id": "route-roundtrip"}
        complete = refresh_commitment(partial, [unrelated, outbound, inbound], 6)
        self.assertEqual(complete["status"], "SETTLED")
        self.assertEqual(complete["waypoint_receipts"], ["out", "in"])

    def test_receipt_frontier_prevents_old_matching_receipt_from_settling_new_goal(self):
        commitment = {"commitment_id": "route-2", "task_kind": "routine_route",
                      "destination_id": 2, "status": "IN_PROGRESS",
                      "receipt_frontier": ["old-move"]}
        old = {"receipt_id": "old-move", "kind": "move", "settled": True,
               "after_room_id": 2, "ongoing_commitment_id": "route-2"}
        self.assertEqual(refresh_commitment(commitment, [old], 5)["status"], "IN_PROGRESS")
        new = {**old, "receipt_id": "new-move"}
        settled = refresh_commitment(commitment, [old, new], 5)
        self.assertEqual(settled["status"], "SETTLED")
        self.assertEqual(settled["receipt_ids"], ["new-move"])

    def test_nonmatching_task_instance_receipt_cannot_settle_same_item_goal(self):
        commitment = {"commitment_id": "archive-v2", "task_kind": "archive_note",
                      "item_id": 10, "destination_id": 2, "status": "IN_PROGRESS",
                      "receipt_frontier": [], "receipt_ids": []}
        other = {"receipt_id": "other-task-drop", "kind": "drop", "item_id": 10,
                 "after_item_room_id": 2, "settled": True,
                 "ongoing_commitment_id": "archive-v1"}
        self.assertEqual(refresh_commitment(commitment, [other], 5)["status"], "IN_PROGRESS")
        own = {**other, "receipt_id": "this-task-drop", "ongoing_commitment_id": "archive-v2"}
        settled = refresh_commitment(commitment, [other, own], 6)
        self.assertEqual(settled["status"], "SETTLED")
        self.assertEqual(settled["receipt_ids"], ["this-task-drop"])
        unbound = refresh_commitment({**commitment, "commitment_id": None},
                                     [{**other, "ongoing_commitment_id": None}], 6)
        self.assertEqual(unbound["status"], "IN_PROGRESS")

    def test_other_source_drop_cannot_suppress_actor_self_delivery_goal(self):
        actor = Actor()
        actor.attributes.add("native_receipts", [{"receipt_id": "author-drop", "kind": "drop",
            "item_id": 10, "after_item_room_id": 2, "settled": True,
            "ongoing_task_kind": "archive_note", "ongoing_commitment_id": "author-v1"}],
            category="native_p3")
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor",
                   return_value=local_view()):
            result = advance_actor(actor, None, [], 1)
        self.assertEqual(result["commitment"]["task_kind"], "deliver_supply")
        self.assertEqual(result["intent"]["operator"], "get")

    def test_late_exact_task_receipt_does_not_override_absolute_deadline(self):
        commitment = {"commitment_id": "archive-deadline", "task_kind": "archive_note",
                      "item_id": 10, "destination_id": 2, "deadline_minute": 4,
                      "status": "IN_PROGRESS", "receipt_frontier": [], "receipt_ids": []}
        late = {"receipt_id": "late-drop", "kind": "drop", "item_id": 10,
                "after_item_room_id": 2, "settled": True, "sim_minute": 5,
                "ongoing_commitment_id": "archive-deadline"}
        expired = refresh_commitment(commitment, [late], 5)
        self.assertEqual(expired["status"], "EXPIRED")
        self.assertEqual(expired["receipt_ids"], [])

    def test_suspended_author_offer_resumes_same_commitment_not_duplicate(self):
        actor = Actor()
        view = local_view()
        view["goal_contract"]["item_id"] = None
        view["observation"]["exits"] = []
        signature = _local_signature(view)
        offer = {"offer_id": "archive-v1", "source": "AUTHOR", "goal_id": "archive-goal",
                 "task_kind": "archive_note", "item_id": 10, "destination_id": 2,
                 "deadline_minute": 10, "item_key": "Supply"}
        suspended = {"commitment_id": "archive-v1", "source_offer_id": "archive-v1",
                     "source": "AUTHOR", "goal_id": "archive-goal", "status": "SUSPENDED",
                     "task_kind": "archive_note", "item_id": 10, "destination_id": 2,
                     "deadline_minute": 10, "receipt_frontier": [], "receipt_ids": [],
                     "suspended_observation": signature, "reason": "blocked locally"}
        actor.attributes.add("ongoing_commitments", [suspended], category="native_p5")
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor", return_value=view):
            waiting = advance_actor(actor, None, [offer], 5)
        self.assertIsNone(waiting["selected_goal"])
        history = actor.attributes.get("ongoing_goal_history", category="native_p5")
        self.assertTrue(any(row.get("event") == "AUTHOR_OFFER_DEFERRED"
                            and row.get("offer_id") == "archive-v1" for row in history))

        changed = local_view(room_id=2, held=True, item_room=None)
        changed["goal_contract"]["item_id"] = None
        changed["observation"]["exits"] = [{"key": "west", "destination_id": 1}]
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor", return_value=changed):
            resumed = advance_actor(actor, None, [offer], 6)
        self.assertEqual(resumed["selected_goal"], "archive-v1")
        self.assertEqual(sum(row.get("commitment_id") == "archive-v1" for row in
                             actor.attributes.get("ongoing_commitments", category="native_p5")), 1)

    def test_terminal_offer_cannot_recreate_settled_goal(self):
        actor = Actor()
        settled = {"commitment_id": "archive-v1", "source_offer_id": "archive-v1",
                   "source": "AUTHOR", "goal_id": "archive-goal", "status": "SETTLED",
                   "task_kind": "archive_note", "item_id": 10, "destination_id": 2,
                   "receipt_ids": ["archive-receipt"]}
        actor.attributes.add("ongoing_commitments", [settled], category="native_p5")
        offer = {"offer_id": "archive-v1", "source": "AUTHOR", "goal_id": "archive-goal",
                 "task_kind": "archive_note", "item_id": 10, "destination_id": 2}
        view = local_view()
        view["goal_contract"]["item_id"] = None
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor", return_value=view):
            result = advance_actor(actor, None, [offer], 6)
        commitments = actor.attributes.get("ongoing_commitments", category="native_p5")
        self.assertEqual(sum(row.get("commitment_id") == "archive-v1" for row in commitments), 1)
        self.assertNotEqual(result["selected_goal"], "archive-v1")
        history = actor.attributes.get("ongoing_goal_history", category="native_p5")
        self.assertTrue(any(row.get("event") == "TERMINAL_OFFER_IGNORED"
                            and row.get("prior_status") == "SETTLED" for row in history))

    def test_superseded_author_suffix_is_cancelled_without_dispatch(self):
        actor = Actor()
        stale = {"commitment_id": "archive-v1", "source_offer_id": "archive-v1",
                 "source": "AUTHOR", "goal_id": "archive-goal", "status": "ACCEPTED",
                 "task_kind": "archive_note", "item_id": 10, "destination_id": 2,
                 "projection_id": "station:1:oldhashprefix", "receipt_frontier": [],
                 "receipt_ids": []}
        actor.attributes.add("ongoing_commitments", [stale], category="native_p5")
        offer = {"offer_id": "archive-v1", "source": "AUTHOR", "goal_id": "archive-goal",
                 "task_kind": "archive_note", "item_id": 10, "destination_id": 2,
                 "projection_id": "station:1:oldhashprefix"}
        view = local_view()
        view["goal_contract"]["item_id"] = None
        view["observation"]["exits"] = []
        projection = {"station_id": "station", "version": 2, "bundle_hash": "new-source-hash"}
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor", return_value=view):
            result = advance_actor(actor, projection, [offer], 6)
        commitments = actor.attributes.get("ongoing_commitments", category="native_p5")
        cancelled = next(row for row in commitments if row["commitment_id"] == "archive-v1")
        self.assertEqual(cancelled["status"], "CANCELLED_STALE")
        self.assertNotEqual(result["selected_goal"], "archive-v1")
        self.assertIsNone(result["intent"])
        history = actor.attributes.get("ongoing_goal_history", category="native_p5")
        self.assertTrue(any(row.get("event") == "COMMITMENT_CANCELLED_STALE"
                            and row.get("stale_projection_id") == "station:1:oldhashprefix"
                            and row.get("cancellation_projection_id") == "station:2:new-source-h"
                            for row in history))

    def test_superseded_projection_does_not_cancel_dispatched_task(self):
        actor = Actor()
        commitment = {"commitment_id": "archive-v1", "source_offer_id": "archive-v1",
                      "source": "AUTHOR", "goal_id": "archive-goal", "status": "IN_PROGRESS",
                      "task_kind": "archive_note", "item_id": 10, "destination_id": 2,
                      "projection_id": "station:1:oldhashprefix", "receipt_frontier": [],
                      "receipt_ids": []}
        actor.attributes.add("ongoing_commitments", [commitment], category="native_p5")
        actor.attributes.add("pending_action", {"status": "executing", "ongoing_task": commitment},
                             category="native_p3")
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor",
                   return_value=local_view()):
            result = advance_actor(actor, {"station_id": "station", "version": 2,
                                           "bundle_hash": "new-source-hash"}, [], 6)
        self.assertEqual(result["commitment"]["status"], "IN_PROGRESS")
        self.assertTrue(result["pending_action_preserved"])

    def test_future_edit_reauthorizes_same_method_suffix_without_resetting_progress(self):
        actor = Actor()
        commitment = {"commitment_id": "archive-v1-A", "source_offer_id": "archive-v1-A",
                      "source": "AUTHOR", "goal_id": "archive-goal", "status": "IN_PROGRESS",
                      "task_kind": "archive_note", "item_id": 10, "destination_id": 2,
                      "actor_alias": "A", "recipient_alias": None, "recipient_id": None,
                      "constraint_id": "archive-by-note", "source_method_id": "return_then_file_by_A",
                      "projection_id": "station:1:oldhashprefix", "accepted_projection_id": "station:1:oldhashprefix",
                      "receipt_frontier": ["prior"], "receipt_ids": ["prior"]}
        actor.attributes.add("ongoing_commitments", [commitment], category="native_p5")
        offer = {"offer_id": "archive-v2-A", "source": "AUTHOR", "goal_id": "archive-goal",
                 "task_kind": "archive_note", "item_id": 10, "destination_id": 2,
                 "actor_alias": "A", "recipient_alias": None, "recipient_id": None,
                 "constraint_id": "archive-by-note", "source_method_id": "return_then_file_by_A",
                 "control_source": "PLANNER", "projection_id": "station:2:new-source-h"}
        projection = {"station_id": "station", "version": 2, "bundle_hash": "new-source-hash",
                      "constraints": [{"constraint_id": "archive-by-note",
                          "control": {"mode": "process", "file_actor": "A",
                                      "allowed_methods": ["return_then_file_by_A"]}}]}
        view = local_view(room_id=2, held=True, item_room=None)
        view["goal_contract"]["item_id"] = None
        view["observation"]["exits"] = []
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor", return_value=view):
            result = advance_actor(actor, projection, [offer], 6)
        row = next(item for item in actor.attributes.get("ongoing_commitments", category="native_p5")
                   if item["commitment_id"] == "archive-v1-A")
        self.assertEqual(row["status"], "IN_PROGRESS")
        self.assertEqual(row["receipt_frontier"], ["prior"])
        self.assertEqual(row["receipt_ids"], ["prior"])
        self.assertEqual(row["projection_id"], "station:2:new-source-h")
        self.assertEqual(row["accepted_projection_id"], "station:1:oldhashprefix")
        self.assertEqual(row["replacement_offer_id"], "archive-v2-A")
        self.assertEqual(result["selected_goal"], "archive-v1-A")
        self.assertEqual(result["intent"]["operator"], "drop")

    def test_edit_projection_reconciles_unplanned_author_suffix_but_keeps_self_and_locked_progress(self):
        actor = Actor()
        stale_result = {"commitment_id": "archive-v1-B", "source_offer_id": "offer-v1-B",
                        "source": "AUTHOR", "goal_id": "archive-note-by-horizon",
                        "constraint_id": "archive-note-by-horizon", "status": "IN_PROGRESS",
                        "task_kind": "archive_note", "item_id": 71, "destination_id": 50,
                        "actor_alias": "B", "source_method_id": "file_by_B",
                        "control_source": "PLANNER", "projection_id": "station:1:oldhash",
                        "receipt_frontier": ["move-r1"], "receipt_ids": ["move-r1"]}
        locked = {"commitment_id": "locked-v1-B", "source_offer_id": "offer-lock-B",
                  "source": "AUTHOR", "goal_id": "respond-before-archive",
                  "constraint_id": "respond-before-archive", "status": "IN_PROGRESS",
                  "task_kind": "handover_note", "item_id": 71, "destination_id": 2,
                  "actor_alias": "B", "recipient_alias": "A", "recipient_id": 22,
                  "source_method_id": "locked_fragment", "control_source": "LOCKED_FRAGMENT",
                  "grant_id": "lock-grant", "locked_fragment_hash": "lock-hash",
                  "locked_sequence_index": 0, "projection_id": "station:1:oldhash",
                  "receipt_frontier": ["move-lock"], "receipt_ids": ["move-lock"]}
        self_commitment = {"commitment_id": "self-route", "source_offer_id": "self-route",
                           "source": "SELF", "goal_id": "routine_route", "status": "IN_PROGRESS",
                           "task_kind": "routine_route", "item_id": None, "destination_id": 2,
                           "receipt_frontier": ["self-move"], "receipt_ids": ["self-move"]}
        actor.attributes.add("ongoing_commitments", [stale_result, locked, self_commitment],
                             category="native_p5")
        new_projection = {"station_id": "station", "version": 2,
                          "bundle_hash": "newhash", "constraints": [
            {"constraint_id": "archive-note-by-horizon",
             "control": {"mode": "result_only", "file_actor": "A",
                         "allowed_methods": ["file_by_B", "return_then_file_by_A"]}},
            {"constraint_id": "respond-before-archive",
             "control": {"mode": "locked_fragment", "file_actor": None,
                         "allowed_methods": ["return_then_file_by_A"]},
             "locked_fragment": {"sequence_sha256": "lock-hash", "sequence": [
                 {"actor_alias": "B", "task_kind": "handover_note", "item_ref": "objective.note"},
                 {"actor_alias": "A", "task_kind": "archive_note", "item_ref": "objective.note"}]}}
        ]}
        view = local_view(held=True, item_room=None)
        view["goal_contract"]["item_id"] = None
        view["observation"]["inventory"] = [{"id": 71, "key": "Exact note"}]
        view["observation"]["task_item"] = {"id": 71, "key": "Exact note"}
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor", return_value=view):
            advance_actor(actor, new_projection, [], 6)
        commitments = actor.attributes.get("ongoing_commitments", category="native_p5")
        by_id = {row["commitment_id"]: row for row in commitments}
        self.assertEqual(by_id["archive-v1-B"]["status"], "CANCELLED_STALE")
        self.assertEqual(by_id["archive-v1-B"]["receipt_ids"], ["move-r1"])
        self.assertEqual(by_id["locked-v1-B"]["status"], "IN_PROGRESS")
        self.assertEqual(by_id["locked-v1-B"]["projection_id"], "station:2:newhash")
        self.assertEqual(by_id["locked-v1-B"]["receipt_frontier"], ["move-lock"])
        self.assertEqual(by_id["locked-v1-B"]["receipt_ids"], ["move-lock"])
        self.assertEqual(by_id["self-route"]["status"], "IN_PROGRESS")
        self.assertEqual(by_id["self-route"]["receipt_ids"], ["self-move"])

    def test_suspended_commitment_does_not_lock_slot_and_author_deferral_is_explained(self):
        view = local_view(item_room=None)
        suspended = {"commitment_id": "self-old", "source": "SELF", "status": "SUSPENDED",
                     "task_kind": "deliver_supply", "item_id": 10}
        author_offer = {"offer_id": "author-new", "source": "AUTHOR",
                        "task_kind": "routine_route", "destination_id": 2,
                        "deadline_minute": 9}
        result = arbitrate([author_offer], [suspended], view, 4)
        self.assertEqual(result["selected"]["offer_id"], "author-new")
        self.assertEqual(result["disposition"], "ACCEPTED")

        active = {**suspended, "status": "IN_PROGRESS"}
        retained = arbitrate([author_offer], [active], local_view(), 4)
        self.assertEqual(retained["selected"]["commitment_id"], "self-old")
        self.assertEqual(retained["deferred_offers"][0]["offer_id"], "author-new")

    def test_actor_uses_p3_receipt_frontier_then_starts_real_routine_route(self):
        actor = Actor()
        actor.attributes.add("activity_profile", "ongoing_station_v1", category="native_p3")
        actor.attributes.add("task_item_id", 10, category="native_p3")
        actor.attributes.add("task_destination_id", 2, category="native_p3")
        actor.attributes.add("goal", "deliver_supply", category="native_p3")
        actor.attributes.add("native_receipts", [], category="native_p3")
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor",
                   return_value=local_view()):
            first = advance_actor(actor, {"station_id": "s", "version": 1,
                                          "bundle_hash": "hash"}, [], 1)
        self.assertEqual(first["disposition"], "ACCEPTED")
        self.assertEqual(first["intent"]["operator"], "get")
        self.assertEqual(first["commitment"]["status"], "IN_PROGRESS")

        receipt = {"receipt_id": "drop-new", "kind": "drop", "item_id": 10,
                   "after_item_room_id": 2, "settled": True,
                   "ongoing_commitment_id": first["commitment"]["commitment_id"]}
        actor.attributes.add("native_receipts", [receipt], category="native_p3")
        at_destination = local_view(room_id=2, held=False, item_room=None)
        at_destination["observation"]["exits"] = [{"key": "west", "destination_id": 1}]
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor",
                   return_value=at_destination):
            second = advance_actor(actor, {"station_id": "s", "version": 1,
                                           "bundle_hash": "hash"}, [], 2)
        self.assertEqual(second["commitment"]["status"], "IN_PROGRESS")
        self.assertEqual(second["commitment"]["task_kind"], "routine_route")
        self.assertEqual(second["intent"]["operator"], "move")
        self.assertEqual(second["intent"]["destination_id"], 1)
        self.assertEqual(second["commitment"]["route_waypoints"], [1, 2])
        history = actor.attributes.get("ongoing_goal_history", category="native_p5")
        self.assertTrue(any(row["event"] == "COMMITMENT_SETTLED" and
                            row["evidence_receipt_ids"] == ["drop-new"] for row in history))

    def test_author_offer_is_deferred_during_real_first_patrol_leg(self):
        actor = Actor()
        route_id = "self:9:routine_route:0:2"
        commitment = {"commitment_id": route_id, "source": "SELF",
                      "goal_id": "self-goal:9:routine_route:0", "status": "IN_PROGRESS",
                      "task_kind": "routine_route", "item_id": None,
                      "destination_id": 2, "route_origin_id": 1,
                      "route_waypoints": [2, 1], "waypoint_receipts": [None, None],
                      "receipt_frontier": [], "receipt_ids": []}
        actor.attributes.add("ongoing_commitments", [commitment], category="native_p5")
        offer = {"offer_id": "author-archive", "source": "AUTHOR",
                 "task_kind": "archive_note", "item_id": 10, "destination_id": 2,
                 "deadline_minute": 8}
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor",
                   return_value=local_view()):
            result = advance_actor(actor, {"station_id": "s", "version": 1}, [offer], 4)
        self.assertEqual(result["selected_goal"], route_id)
        self.assertEqual(result["disposition"], "CONTINUE")
        self.assertEqual(result["commitment"]["waypoint_receipts"], [None, None])
        history = actor.attributes.get("ongoing_goal_history", category="native_p5")
        deferred = [row for row in history if row.get("event") == "AUTHOR_OFFER_DEFERRED"]
        self.assertEqual(deferred[0]["offer_id"], "author-archive")
        self.assertEqual(deferred[0]["blocking_commitment_id"], route_id)

    def test_suspended_route_waits_for_local_change_then_replans(self):
        actor = Actor()
        same_view = local_view()
        same_view["goal_contract"]["item_id"] = None
        route_id = "self:9:routine_route:0:2"
        commitment = {"commitment_id": route_id, "source_offer_id": route_id,
                      "source": "SELF", "goal_id": "self-goal:9:routine_route:0",
                      "status": "SUSPENDED", "task_kind": "routine_route",
                      "item_id": None, "destination_id": 2, "route_origin_id": 1,
                      "route_waypoints": [2, 1], "waypoint_receipts": [None, None],
                      "receipt_frontier": [], "receipt_ids": [],
                      "suspended_observation": _local_signature(same_view)}
        actor.attributes.add("ongoing_commitments", [commitment], category="native_p5")
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor",
                   return_value=same_view):
            waiting = advance_actor(actor, None, [], 5)
        self.assertIsNone(waiting["planner"])
        self.assertIsNone(waiting["selected_goal"])

        changed_view = local_view()
        changed_view["goal_contract"]["item_id"] = None
        changed_view["observation"]["known_traversability"] = {1: {2: False}}
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor",
                   return_value=changed_view):
            resumed = advance_actor(actor, None, [], 6)
        self.assertEqual(resumed["selected_goal"], route_id)
        self.assertEqual(resumed["planner"]["status"], "NO_PLAN")

    def test_existing_native_pending_action_is_preserved_without_conflicting_intent(self):
        actor = Actor()
        pending = {"status": "executing", "operation_id": "existing-op",
                   "intent": {"operator": "move"}}
        commitment = {"commitment_id": "self-task", "source": "SELF", "goal_id": "self-goal",
                      "status": "IN_PROGRESS", "task_kind": "deliver_supply", "item_id": 10,
                      "destination_id": 2, "recipient_id": None, "deadline_minute": None,
                      "accepted_minute": 1, "updated_minute": 1, "receipt_ids": [],
                      "receipt_frontier": [], "reason": "test", "source_offer_id": "self-task"}
        actor.attributes.add("pending_action", pending, category="native_p3")
        actor.attributes.add("ongoing_commitments", [commitment], category="native_p5")
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor",
                   return_value=local_view()):
            result = advance_actor(actor, {"station_id": "s", "version": 1,
                                           "bundle_hash": "hash"}, [], 2)
        self.assertIsNone(result["intent"])
        self.assertTrue(result["pending_action_preserved"])
        self.assertEqual(actor.attributes.get("pending_action", category="native_p3"), pending)
        self.assertEqual(result["commitment"]["status"], "IN_PROGRESS")

    def test_received_author_offer_is_deferred_with_active_commitment_evidence(self):
        actor = Actor()
        active = {"commitment_id": "self-task", "source": "SELF", "goal_id": "self-goal",
                  "status": "IN_PROGRESS", "task_kind": "deliver_supply", "item_id": 10,
                  "destination_id": 2, "recipient_id": None, "deadline_minute": None,
                  "accepted_minute": 1, "updated_minute": 1, "receipt_ids": [],
                  "receipt_frontier": [], "reason": "existing work", "source_offer_id": "self-task"}
        actor.attributes.add("ongoing_commitments", [active], category="native_p5")
        offer = {"offer_id": "author-new", "source": "AUTHOR", "goal_id": "authored-route",
                 "task_kind": "routine_route", "item_id": None, "destination_id": 2,
                 "recipient_id": None, "deadline_minute": 8}
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor",
                   return_value=local_view()):
            decision = advance_actor(actor, None, [offer], 2)
        self.assertEqual(decision["selected_goal"], "self-task")
        self.assertEqual(decision["intent"]["operator"], "get")
        history = actor.attributes.get("ongoing_goal_history", category="native_p5")
        deferred = next(row for row in history if row["event"] == "AUTHOR_OFFER_DEFERRED")
        self.assertEqual(deferred["offer_id"], "author-new")
        self.assertEqual(deferred["blocking_commitment_id"], "self-task")

    def test_opt_in_give_uses_shared_pending_dispatch_and_native_receipt(self):
        room = Room()
        recipient = Thing(22, "B", room)
        item = Thing(10, "exact note", room)
        actor = GivingActor(9, room, recipient, item)
        view = local_view(room_id=2, held=True, item_room=None)
        pending = {"status": "planned", "view": thaw(view),
                   "goal": {"choice": "handover_note"},
                   "intent": {"operator": "give", "item_id": 10, "recipient_id": 22},
                   "ongoing_task": {"task_kind": "handover_note", "item_id": 10,
                                    "recipient_id": 22}}
        actor.attributes.add("activity_profile", "ongoing_station_v1", category="native_p3")
        actor.attributes.add("pending_action", pending, category="native_p3")
        _dispatch_pending(actor, pending)
        outcome = actor.attributes.get("last_outcome", category="native_p3")
        self.assertEqual(actor.attributes.get("submitted_command", category="native_p3"),
                         "give exact note = B")
        self.assertTrue(outcome["receipt"]["settled"])
        self.assertEqual(outcome["receipt"]["recipient_id"], 22)
        self.assertEqual(outcome["receipt"]["ongoing_task_kind"], "handover_note")


if __name__ == "__main__":
    unittest.main()
