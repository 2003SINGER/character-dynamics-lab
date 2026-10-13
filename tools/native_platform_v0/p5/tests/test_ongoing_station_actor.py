import unittest
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch

from tools.native_platform_v0.p3.agency import _dispatch_pending
from tools.native_platform_v0.p3.planning import thaw
from tools.native_platform_v0.p3.planning import plan_actor_task
from tools.native_platform_v0.p5.ongoing_station.goals import arbitrate, refresh_commitment
from tools.native_platform_v0.p5.ongoing_station.actor import (
    _local_signature, _self_offers, _still_authorized, advance_actor,
)


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


def tool_view(room_id=1, *, holder=None, tool_room=1, tool_id=55):
    view = local_view(room_id=room_id, held=False, item_room=1)
    view["observation"]["station_tools"] = [{
        "id": tool_id, "room_id": tool_room, "visible": True,
        "held_by_actor_id": holder, "lease_status": "FREE" if holder is None else "BUSY",
    }]
    view["observation"]["station_supplies"] = [{
        "id": 10, "room_id": 1, "visible": True,
        "held_by_actor_id": None, "inspection_status": "UNINSPECTED",
    }]
    view["observation"]["station_storages"] = [{
        "id": 90, "room_id": 2, "visible": True,
    }]
    view["observation"]["station_repair_targets"] = [{
        "id": "south-exit", "room_id": 1, "key": "south",
        "destination_id": 3, "traversable": False,
    }]
    view["observation"]["known_exits"] = {1: [2], 2: [1]}
    view["observation"]["exits"] = ([{"key": "east", "destination_id": 2}] if room_id == 1 else
                                     [{"key": "west", "destination_id": 1}])
    return view


def locked_repair_projection():
    return {
        "station_id": "station", "version": 2,
        "source_sha256": "0123456789ab" + "0" * 52,
        "constraints": [{
            "constraint_id": "repair-order",
            "control": {"mode": "locked_fragment"},
            "locked_fragment": {
                "sequence_sha256": "a" * 64,
                "sequence": [{"actor_alias": "B", "task_kind": "repair_passage",
                              "tool_ref": "station_tool",
                              "target_ref": "pickup_to_side_south"}],
            },
        }],
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
    def test_hard_repair_order_defers_new_self_store_and_gates_only_terminal_store(self):
        actor = Actor()
        actor.attributes.add("p5_actor_alias", "A", category="native_p5")
        view = tool_view()
        view["actor_id"] = actor.id
        view["goal_contract"] = {"goal": None, "item_id": None, "destination_id": None}
        view["observation"]["exits"] = []
        view["observation"]["known_exits"] = {}
        view["observation"]["station_task_bindings"] = [{
            "task_kind": "store_item", "item_id": 10, "storage_destination_id": 90,
            "storage_room_id": 2, "deadline_minute": 24}]
        view["observation"]["station_supplies"][0]["inspection_status"] = "APPROVED"
        projection = {"station_id": "station", "version": 2,
                      "source_sha256": "e" * 64,
                      "constraints": [{"constraint_id": "repair-before-storage",
                                       "source_constraint": {
                                           "kind": "event_order", "hard": True,
                                           "before": {"event": "station_passage_repaired",
                                                      "filters": {"actor": "B", "tool": "station_tool",
                                                                  "exit": "pickup_to_side_south"}},
                                           "after": {"event": "station_supply_stored",
                                                     "filters": {"actor": "A", "item": "courier_supply",
                                                                 "storage": "station_storage"}}}}]}
        inspection = {"receipt_id": "inspect-1", "task_kind": "inspect_supply",
                      "item_id": 10, "settled": True, "outcome": "SETTLED",
                      "effect": {"after_status": "APPROVED"}}
        actor.attributes.add("native_receipts", [inspection], category="native_p3")
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor", return_value=view):
            waiting = advance_actor(actor, projection, [], 5)
        self.assertIsNone(waiting["commitment"], "fresh SELF store must defer until local repair witness")

        commitment = {"commitment_id": "self-store-1", "source_offer_id": "self-store-1",
                      "source": "SELF", "status": "IN_PROGRESS", "goal_id": "store",
                      "task_kind": "store_item", "actor_alias": "A", "item_id": 10,
                      "storage_destination_id": 90, "destination_id": 90,
                      "deadline_minute": 24, "accepted_minute": 4, "updated_minute": 4,
                      "receipt_ids": [], "receipt_frontier": ["inspect-1"]}
        actor.attributes.add("ongoing_commitments", [commitment], category="native_p5")
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor", return_value=view), \
             patch("tools.native_platform_v0.p5.ongoing_station.actor.plan_actor_task",
                   return_value={"status": "SOLVED", "intent": {"operator": "store_item"}, "plan": []}):
            blocked = advance_actor(actor, projection, [], 6)
        self.assertIsNone(blocked["intent"])
        self.assertEqual(blocked["disposition"], "WAIT")
        self.assertEqual(blocked["commitment"]["commitment_id"], "self-store-1")

        view["observation"]["station_repair_targets"][0].update({
            "alias": "pickup_to_side_south", "traversable": True,
            "last_repair_receipt": {"receipt_id": "repair-r1", "outcome": "SETTLED",
                                     "actor_alias": "B", "completed_minute": 7}})
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor", return_value=view), \
             patch("tools.native_platform_v0.p5.ongoing_station.actor.plan_actor_task",
                   return_value={"status": "SOLVED", "intent": {"operator": "store_item"}, "plan": []}):
            ready = advance_actor(actor, projection, [], 8)
        self.assertEqual(ready["intent"]["operator"], "store_item")
        witness = actor.attributes.get("p5_station_repair_witness", category="native_p5")
        self.assertEqual(witness["receipt_id"], "repair-r1")

    def test_station_self_offers_require_local_tool_target_and_real_inspection_receipt(self):
        actor = Actor()
        view = tool_view()
        view["observation"]["station_task_bindings"] = [
            {"task_kind": "inspect_supply", "item_id": 10, "tool_id": 55,
             "target_id": 10, "target_room_id": 1, "storage_destination_id": 90,
             "duration_minutes": 2, "deadline_minute": 24},
            {"task_kind": "repair_passage", "tool_id": 55, "target_id": "south-exit",
             "target_room_id": 1, "duration_minutes": 3, "deadline_minute": 24},
            {"task_kind": "store_item", "item_id": 10, "storage_destination_id": 90,
             "storage_room_id": 2, "deadline_minute": 24},
        ]
        offers = _self_offers(actor, view, 4, [], [])
        kinds = {row["task_kind"] for row in offers}
        self.assertTrue({"inspect_supply", "repair_passage"}.issubset(kinds))
        self.assertTrue({"store_item", "deliver_supply", "return_stock"}.isdisjoint(kinds))
        inspect = next(row for row in offers if row["task_kind"] == "inspect_supply")
        receipt = {"receipt_id": "inspect-r1", "task_kind": "inspect_supply", "item_id": 10,
                   "settled": True, "outcome": "SETTLED", "effect": {"after_status": "APPROVED"}}
        offers = _self_offers(actor, view, 5, [receipt], [])
        self.assertIn("store_item", {row["task_kind"] for row in offers})
        view["observation"]["station_tools"][0]["lease_status"] = "BUSY"
        offers = _self_offers(actor, view, 6, [], [])
        self.assertNotIn("inspect_supply", {row["task_kind"] for row in offers})

    def test_lend_offer_requires_receipt_time_local_on_time_return_history(self):
        actor = Actor()
        view = tool_view()
        view["actor_id"] = actor.id
        view["goal_contract"] = {"goal": None, "item_id": None, "destination_id": None}
        view["observation"]["exits"] = []
        offer = {"offer_id": "lend:1", "source": "AUTHOR", "goal_id": "lend-goal",
                 "task_kind": "lend_tool", "tool_id": 55, "item_id": 55,
                 "recipient_id": 22, "recipient_alias": "B", "recipient_room_id": 1,
                 "due_minute": 12, "deadline_minute": 12, "constraint_id": "loan"}
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor", return_value=view), \
             patch("tools.native_platform_v0.p5.ongoing_station.actor.plan_actor_task",
                   return_value={"status": "SOLVED", "intent": None, "plan": []}):
            first = advance_actor(actor, None, [offer], 5)
        self.assertEqual(first["commitment"]["task_kind"], "lend_tool")
        self.assertTrue(any(row.get("event") == "TOOL_LOAN_OFFER_PROVISIONAL"
                            for row in actor.attributes.get("ongoing_goal_history", category="native_p5", default=[]) or []))

        view["observation"]["known_tool_events"] = [{
            "event_type": "p5_station_tool_returned", "event_id": "station:return-1",
            "receipt_id": "return-1", "loan_id": "loan-1", "tool_id": 55,
            "borrower_alias": "B", "returned_minute": 9, "witnessed_minute": 9, "outcome": "LATE",
            "settled": True, "witnessed_by_actor_id": actor.id,
        }]
        actor2 = Actor()
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor", return_value=view), \
             patch("tools.native_platform_v0.p5.ongoing_station.actor.plan_actor_task",
                   return_value={"status": "SOLVED", "intent": None, "plan": []}):
            advance_actor(actor2, None, [offer], 10)
        commitments = actor2.attributes.get("ongoing_commitments", category="native_p5", default=[]) or []
        self.assertFalse(any(row.get("task_kind") == "lend_tool" for row in commitments))
        self.assertTrue(any(row.get("event") == "TOOL_LOAN_OFFER_DEFERRED"
                            for row in actor2.attributes.get("ongoing_goal_history", category="native_p5", default=[]) or []))

    def test_authorized_locked_suffix_yields_only_matching_undispatched_self_task(self):
        actor = Actor()
        actor.attributes.add("p5_actor_alias", "B", category="native_p5")
        self_id = "self:9:repair_passage:south-exit"
        self_commitment = {"commitment_id": self_id, "source_offer_id": self_id,
                           "source": "SELF", "status": "IN_PROGRESS",
                           "goal_id": "self-repair", "task_kind": "repair_passage",
                           "item_id": None, "tool_id": 55, "target_id": "south-exit",
                           "actor_alias": "B", "receipt_ids": ["prior-self-receipt"],
                           "receipt_frontier": ["prior-self-receipt"]}
        actor.attributes.add("ongoing_commitments", [self_commitment], category="native_p5")
        view = tool_view()
        view["actor_id"] = actor.id
        view["observation"]["station_task_bindings"] = [{
            "task_kind": "repair_passage", "tool_id": 55, "target_id": "south-exit",
            "target_room_id": 1, "duration_minutes": 3, "deadline_minute": 20}]
        projection = locked_repair_projection()
        projection_id = "station:2:0123456789ab"
        locked = {"offer_id": "locked:repair:0", "source": "AUTHOR", "goal_id": "repair",
                  "task_kind": "repair_passage", "tool_id": 55, "target_id": "south-exit",
                  "target_room_id": 1, "target_alias": "pickup_to_side_south",
                  "tool_alias": "station_tool", "actor_alias": "B", "item_id": None,
                  "source_method_id": "locked_fragment", "control_source": "LOCKED_FRAGMENT",
                  "grant_id": "station:repair-order:fixed-native-grant",
                  "constraint_id": "repair-order", "projection_id": projection_id,
                  "locked_fragment_hash": "a" * 64, "locked_sequence_index": 0,
                  "deadline_minute": 20, "duration_minutes": 3}
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor", return_value=view), \
             patch("tools.native_platform_v0.p5.ongoing_station.actor.plan_actor_task",
                   return_value={"status": "SOLVED", "intent": {"operator": "use_tool", "tool_id": 55,
                                                                      "task_kind": "repair_passage",
                                                                      "target_id": "south-exit"}, "plan": []}):
            decision = advance_actor(actor, projection, [locked], 5)
        rows = actor.attributes.get("ongoing_commitments", category="native_p5", default=[])
        prior = next(row for row in rows if row["commitment_id"] == self_id)
        author = next(row for row in rows if row.get("source") == "AUTHOR")
        self.assertEqual(prior["status"], "SUSPENDED")
        self.assertEqual(prior["receipt_ids"], ["prior-self-receipt"])
        self.assertEqual(author["control_source"], "LOCKED_FRAGMENT")
        self.assertEqual(author["receipt_frontier"], [])
        self.assertEqual(decision["commitment"]["commitment_id"], locked["offer_id"])
        self.assertNotEqual(author["commitment_id"], prior["commitment_id"])

    def test_locked_offer_cannot_yield_matching_self_when_pending_or_unproven(self):
        for mutation in ("pending", "missing_grant"):
            with self.subTest(mutation=mutation):
                actor = Actor()
                actor.attributes.add("p5_actor_alias", "B", category="native_p5")
                self_id = "self:9:repair_passage:south-exit"
                actor.attributes.add("ongoing_commitments", [{
                    "commitment_id": self_id, "source_offer_id": self_id, "source": "SELF",
                    "status": "IN_PROGRESS", "goal_id": "self-repair",
                    "task_kind": "repair_passage", "tool_id": 55, "target_id": "south-exit",
                    "actor_alias": "B", "receipt_ids": ["kept"], "receipt_frontier": []}],
                    category="native_p5")
                view = tool_view()
                view["actor_id"] = actor.id
                view["observation"]["station_task_bindings"] = [{
                    "task_kind": "repair_passage", "tool_id": 55, "target_id": "south-exit",
                    "target_room_id": 1, "duration_minutes": 3, "deadline_minute": 20}]
                locked = {"offer_id": "locked:repair:0", "source": "AUTHOR",
                          "goal_id": "repair", "task_kind": "repair_passage", "tool_id": 55,
                          "target_id": "south-exit", "target_room_id": 1,
                          "target_alias": "pickup_to_side_south", "tool_alias": "station_tool",
                          "actor_alias": "B",
                          "item_id": None, "source_method_id": "locked_fragment",
                          "control_source": "LOCKED_FRAGMENT",
                          "grant_id": "station:repair-order:fixed-native-grant",
                          "constraint_id": "repair-order", "projection_id": "station:2:0123456789ab",
                          "locked_fragment_hash": "a" * 64, "locked_sequence_index": 0,
                          "deadline_minute": 20, "duration_minutes": 3}
                if mutation == "missing_grant":
                    locked.pop("grant_id")
                else:
                    actor.attributes.add("pending_action", {"status": "planned",
                        "ongoing_task": {"commitment_id": self_id}}, category="native_p3")
                with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor", return_value=view), \
                     patch("tools.native_platform_v0.p5.ongoing_station.actor.plan_actor_task",
                           return_value={"status": "SOLVED", "intent": None, "plan": []}):
                    projection = locked_repair_projection()
                    decision = advance_actor(actor, projection, [locked], 5)
                rows = actor.attributes.get("ongoing_commitments", category="native_p5", default=[])
                prior = next(row for row in rows if row["commitment_id"] == self_id)
                self.assertEqual(prior["status"], "IN_PROGRESS")
                self.assertEqual(prior["receipt_ids"], ["kept"])
                self.assertFalse(any(row.get("source") == "AUTHOR" for row in rows))
                if mutation == "pending":
                    self.assertTrue(decision["pending_action_preserved"])
                else:
                    self.assertTrue(any(row.get("event") == "LOCKED_OFFER_REJECTED"
                                        for row in actor.attributes.get("ongoing_goal_history",
                                                                        category="native_p5", default=[])))

    def test_suspended_station_work_retries_after_locally_observed_lease_release(self):
        actor = Actor()
        actor.attributes.add("p5_actor_alias", "A", category="native_p5")
        view = tool_view()
        view["actor_id"] = actor.id
        view["observation"]["station_task_bindings"] = [{
            "task_kind": "inspect_supply", "item_id": 10, "tool_id": 55,
            "target_id": 10, "target_room_id": 1, "storage_destination_id": 90,
            "duration_minutes": 3, "deadline_minute": 20,
        }]
        blocked_view = deepcopy(view)
        blocked_view["observation"]["station_tools"][0]["lease_status"] = "BUSY"
        suspended_id = "self:9:inspect_supply:10"
        suspended = {"commitment_id": suspended_id, "source_offer_id": suspended_id,
                     "source": "SELF", "goal_id": "self-goal:inspect",
                     "status": "SUSPENDED", "task_kind": "inspect_supply",
                     "item_id": 10, "tool_id": 55, "target_id": 10,
                     "storage_destination_id": 90, "receipt_ids": ["earlier"],
                     "receipt_frontier": ["earlier"],
                     "suspended_observation": _local_signature(blocked_view)}
        actor.attributes.add("ongoing_commitments", [suspended], category="native_p5")
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor", return_value=view), \
             patch("tools.native_platform_v0.p5.ongoing_station.actor.plan_actor_task",
                   return_value={"status": "SOLVED", "intent": {"operator": "use_tool",
                               "tool_id": 55, "task_kind": "inspect_supply", "target_id": 10},
                                 "plan": []}):
            decision = advance_actor(actor, None, [], 7)
        row = next(row for row in actor.attributes.get("ongoing_commitments",
                                                        category="native_p5", default=[])
                   if row.get("commitment_id") == suspended_id)
        self.assertEqual(decision["selected_goal"], suspended_id)
        self.assertEqual(row["status"], "IN_PROGRESS")
        self.assertEqual(row["receipt_ids"], ["earlier"])

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

    def test_return_stock_uses_same_exact_item_htn_and_original_source(self):
        result = plan_actor_task(local_view(room_id=2, item_room=2), {
            "goal_id": "return-stock-1", "task_kind": "return_stock", "item_id": 10,
            "destination_id": 1, "last_known_item_room": 2,
        })
        self.assertEqual(result["status"], "SOLVED")
        self.assertEqual(result["intent"], {"operator": "get", "item_id": 10})
        self.assertEqual(result["shared_method_domain"], "p3-ongoing-actor-local")

    def test_inspection_and_repair_use_shared_htn_route_get_and_native_start_only(self):
        task = {"goal_id": "inspect-1", "task_kind": "inspect_supply", "item_id": 10,
                "tool_id": 55, "target_id": 10, "target_room_id": 1,
                "storage_destination_id": 1, "duration_minutes": 2, "deadline_minute": 12}
        from_storage = plan_actor_task(tool_view(), task)
        self.assertEqual(from_storage["status"], "SOLVED")
        self.assertEqual(from_storage["intent"], {
            "operator": "use_tool", "tool_id": 55,
            "task_kind": "inspect_supply", "target_id": 10,
        })
        self.assertNotIn({"operator": "get", "item_id": 55}, from_storage["plan"])
        self.assertEqual(from_storage["shared_method_domain"], "p3-ongoing-actor-local")

        repair = plan_actor_task(tool_view(), {
            **task, "goal_id": "repair-1", "task_kind": "repair_passage",
            "target_id": "south-exit", "target_room_id": 1,
        })
        self.assertEqual(repair["intent"]["operator"], "use_tool")
        self.assertEqual(repair["intent"]["target_id"], "south-exit")
        self.assertTrue(repair["prediction_only"])
        self.assertNotIn("work_complete", repr(repair))

        store_view = tool_view()
        store_view["observation"]["station_supplies"][0]["inspection_status"] = "APPROVED"
        store = plan_actor_task(store_view, {
            "goal_id": "store-1", "task_kind": "store_item", "item_id": 10,
            "storage_destination_id": 90, "storage_room_id": 2,
        })
        self.assertEqual(store["intent"], {"operator": "get", "item_id": 10})
        self.assertEqual(store["plan"][-1], {"operator": "store_item", "item_id": 10,
                                             "storage_id": 90})

    def test_work_planner_fails_closed_without_actor_local_tool_observation(self):
        view = local_view()
        result = plan_actor_task(view, {
            "goal_id": "inspect-1", "task_kind": "inspect_supply", "tool_id": 55,
            "target_id": 10, "target_room_id": 2, "storage_destination_id": 1,
            "duration_minutes": 2,
        })
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIsNone(result["intent"])

    def test_return_stock_offer_requires_own_delivery_and_matching_source_get_receipts(self):
        actor = Actor()
        actor.attributes.add("native_receipts", [
            {"receipt_id": "get-1", "kind": "get", "item_id": 10,
             "before_item_room_id": 1, "settled": True,
             "ongoing_task_kind": "deliver_supply", "ongoing_commitment_id": "delivery-1"},
            {"receipt_id": "drop-1", "kind": "drop", "item_id": 10,
             "after_item_room_id": 2, "settled": True,
             "ongoing_task_kind": "deliver_supply", "ongoing_commitment_id": "delivery-1"},
        ], category="native_p3")
        view = local_view(room_id=2, item_room=2)
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor",
                   return_value=view):
            result = advance_actor(actor, None, [], 5)
        self.assertEqual(result["commitment"]["task_kind"], "return_stock")
        self.assertEqual(result["commitment"]["destination_id"], 1)
        self.assertEqual(result["commitment"]["source_get_receipt_id"], "get-1")
        self.assertEqual(result["commitment"]["source_delivery_receipt_id"], "drop-1")

        actor2 = Actor()
        actor2.attributes.add("native_receipts", [
            {"receipt_id": "get-other", "kind": "get", "item_id": 10,
             "before_item_room_id": 1, "settled": True,
             "ongoing_task_kind": "deliver_supply", "ongoing_commitment_id": "other-delivery"},
            {"receipt_id": "drop-1", "kind": "drop", "item_id": 10,
             "after_item_room_id": 2, "settled": True,
             "ongoing_task_kind": "deliver_supply", "ongoing_commitment_id": "delivery-1"},
        ], category="native_p3")
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor",
                   return_value=view):
            result = advance_actor(actor2, None, [], 5)
        rows = actor2.attributes.get("ongoing_commitments", category="native_p5") or []
        self.assertFalse(any(row.get("task_kind") == "return_stock" for row in rows))

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

    def test_witnessed_station_request_becomes_a_provisional_lender_self_offer(self):
        actor = Actor()
        actor.attributes.add("p5_actor_alias", "A", category="native_p5")
        view = tool_view(holder=actor.id)
        view["actor_id"] = actor.id
        view["observation"]["inventory"] = [{"id": 55, "key": "Shared Station Tool"}]
        view["observation"]["visible_items"] = []
        view["observation"]["station_tools"][0].update({"held_by_actor_id": actor.id,
                                                           "lease_status": "FREE"})
        view["observation"]["station_peers"] = [{"id": 11, "alias": "B", "room_id": 1,
                                                   "visible": True}]
        view["observation"]["station_loan_request"] = {
            "request_id": "station-loan-request:s:1", "lender_alias": "A", "borrower_alias": "B",
            "lender_id": actor.id, "borrower_id": 11, "tool_id": 55,
            "due_minute": 8, "requested_minute": 4, "requester_actor_id": 99,
            "requester_room_id": 1, "settled": True,
        }
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor", return_value=view), \
             patch("tools.native_platform_v0.p5.ongoing_station.actor.plan_actor_task",
                   return_value={"status": "SOLVED", "intent": {"operator": "give",
                               "item_id": 55, "recipient_id": 11}, "plan": []}):
            decision = advance_actor(actor, None, [], 4)
        self.assertEqual(decision["commitment"]["task_kind"], "lend_tool")
        self.assertEqual(decision["commitment"]["recipient_id"], 11)
        self.assertEqual(decision["commitment"]["due_minute"], 8)
        self.assertEqual(decision["commitment"]["loan_request_id"], "station-loan-request:s:1")
        self.assertTrue(any(row.get("event") == "TOOL_LOAN_OFFER_PROVISIONAL"
                            for row in actor.attributes.get("ongoing_goal_history",
                                                            category="native_p5", default=[])))

    def test_idle_b_waits_only_on_a_locally_witnessed_current_request(self):
        actor = Actor()
        actor.attributes.add("p5_actor_alias", "B", category="native_p5")
        view = tool_view()
        view["actor_id"] = actor.id
        view["observation"]["station_loan_request"] = {
            "request_id": "station-loan-request:s:1", "lender_alias": "A", "borrower_alias": "B",
            "lender_id": 10, "borrower_id": actor.id, "tool_id": 55,
            "due_minute": 8, "requested_minute": 4, "requester_actor_id": 99,
            "requester_room_id": 1, "settled": True,
        }
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor", return_value=view), \
             patch("tools.native_platform_v0.p5.ongoing_station.actor.plan_actor_task") as planner:
            decision = advance_actor(actor, None, [], 4)
        self.assertEqual(decision["disposition"], "WAIT")
        self.assertEqual(decision["selected_goal"], None)
        planner.assert_not_called()
        self.assertTrue(any(row.get("event") == "BORROW_REQUEST_WAIT"
                            for row in actor.attributes.get("ongoing_goal_history",
                                                            category="native_p5", default=[])))

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
                      "deadline_minute": 24, "earliest_terminal_minute": 5,
                      "receipt_frontier": ["prior"], "receipt_ids": ["prior"]}
        actor.attributes.add("ongoing_commitments", [commitment], category="native_p5")
        offer = {"offer_id": "archive-v2-A", "source": "AUTHOR", "goal_id": "archive-goal",
                 "task_kind": "archive_note", "item_id": 10, "destination_id": 2,
                 "actor_alias": "A", "recipient_alias": None, "recipient_id": None,
                 "constraint_id": "archive-by-note", "source_method_id": "return_then_file_by_A",
                 "control_source": "PLANNER", "projection_id": "station:2:new-source-h",
                 "deadline_minute": 23, "earliest_terminal_minute": 6}
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
        self.assertEqual(row["deadline_minute"], 23)
        self.assertEqual(row["earliest_terminal_minute"], 6)
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

    def test_new_hard_handover_requirement_invalidates_old_file_by_b_author_suffix(self):
        commitment = {"constraint_id": "archive", "source_method_id": "file_by_B",
                      "actor_alias": "B", "task_kind": "archive_note"}
        projection = {"constraints": [{
            "constraint_id": "archive", "control": {
                "mode": "result_only", "allowed_methods": ["file_by_B", "return_then_file_by_A"]},
            "source_constraint": {"kind": "event_by_deadline", "event": "note_handed_over",
                                  "hard": True, "minimum": 1,
                                  "filters": {"item": "note"}}}]}
        self.assertFalse(_still_authorized(commitment, projection))

    def test_archive_waits_for_authored_start_but_can_travel_before_it(self):
        actor = Actor()
        offer = {"offer_id": "archive-window", "source": "AUTHOR",
                 "goal_id": "archive", "task_kind": "archive_note", "item_id": 10,
                 "destination_id": 2, "deadline_minute": 20,
                 "earliest_terminal_minute": 10}
        held_at_origin = local_view(held=True, item_room=None)
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor",
                   return_value=held_at_origin):
            travel = advance_actor(actor, None, [offer], 8)
        self.assertEqual(travel["intent"]["operator"], "move")
        self.assertEqual(travel["commitment"]["deadline_minute"], 20)
        self.assertEqual(travel["commitment"]["earliest_terminal_minute"], 10)

        at_archive = local_view(room_id=2, held=True, item_room=None)
        at_archive["observation"]["exits"] = [{"key": "west", "destination_id": 1}]
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor",
                   return_value=at_archive):
            waiting = advance_actor(actor, None, [], 9)
        self.assertIsNone(waiting["intent"])
        self.assertEqual(waiting["disposition"], "WAIT")
        self.assertEqual(waiting["commitment"]["status"], "IN_PROGRESS")
        self.assertNotIn("suspended_observation", waiting["commitment"])

        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor",
                   return_value=at_archive):
            ready = advance_actor(actor, None, [], 10)
        self.assertEqual(ready["intent"]["operator"], "drop")
        self.assertEqual(ready["commitment"]["status"], "IN_PROGRESS")

    def test_handover_waits_for_its_count_window_without_suspending(self):
        actor = Actor()
        offer = {"offer_id": "handover-window", "source": "AUTHOR",
                 "goal_id": "archive", "task_kind": "handover_note", "item_id": 10,
                 "destination_id": 2, "recipient_id": 22, "recipient_alias": "A",
                 "deadline_minute": 12, "earliest_terminal_minute": 10}
        view = local_view(room_id=2, held=True, item_room=None)
        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor",
                   return_value=view):
            waiting = advance_actor(actor, None, [offer], 9)
        self.assertIsNone(waiting["intent"])
        self.assertEqual(waiting["commitment"]["status"], "IN_PROGRESS")
        self.assertEqual(waiting["commitment"]["deadline_minute"], 12)
        self.assertEqual(waiting["commitment"]["earliest_terminal_minute"], 10)

        with patch("tools.native_platform_v0.p5.ongoing_station.actor.observe_actor",
                   return_value=view):
            ready = advance_actor(actor, None, [], 10)
        self.assertEqual(ready["intent"]["operator"], "give")

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

    def test_station_work_abort_retry_keeps_commitment_but_mints_distinct_attempts(self):
        room = Room()
        recipient = Thing(22, "B", room)
        item = Thing(30, "Shared Station Tool", room)
        actor = GivingActor(9, room, recipient, item)
        actor.attributes.add("p3_scene_id", "retry-scene", category="native_p3")
        pending = {"status": "planned", "view": thaw(local_view()),
                   "goal": {"choice": "repair"},
                   "intent": {"operator": "use_tool", "tool_id": 30,
                              "task_kind": "repair_passage", "target_id": 50},
                   "ongoing_task": {"task_kind": "repair_passage", "commitment_id": "stable-c1",
                                    "tool_id": 30, "target_id": 50, "duration_minutes": 3}}
        captured = []
        with patch("tools.native_platform_v0.p5.ongoing_station.work.start_work",
                   side_effect=lambda _actor, task, **kwargs:
                   (captured.append((dict(task), dict(kwargs))) or {"ok": True})), \
             patch("tools.native_platform_v0.p3.p4_world.clock_for_actor",
                   side_effect=[{"now": 5, "deadline": 24}, {"now": 6, "deadline": 24}]):
            _dispatch_pending(actor, pending)
            _dispatch_pending(actor, pending)
        first, second = captured
        self.assertEqual(first[0]["commitment_id"], second[0]["commitment_id"])
        self.assertEqual(first[0]["commitment_id"], "stable-c1")
        self.assertNotEqual(first[0]["action_id"], second[0]["action_id"])
        self.assertIn(":5:1:stable-c1", first[0]["action_id"])
        self.assertIn(":6:2:stable-c1", second[0]["action_id"])


if __name__ == "__main__":
    unittest.main()
