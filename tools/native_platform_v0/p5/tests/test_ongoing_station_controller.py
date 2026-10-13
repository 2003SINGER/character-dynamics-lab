from types import SimpleNamespace
import unittest

from tools.native_platform_v0.p5.ongoing_station.controller import (
    _deferred_literal_offer_is_current,
    _station_work_offers_from_decision,
)


class StationWorkAuthorAdapterTests(unittest.TestCase):
    def _deferred_locked_store(self):
        constraint = {
            "constraint_id": "repair-before-storage",
            "control": {"mode": "locked_fragment"},
            "locked_fragment": {"sequence_sha256": "locked-hash", "sequence": [{
                "actor_alias": "A", "task_kind": "store_item",
                "item_ref": "courier_supply", "destination_ref": "station_storage"}]},
        }
        offer = {"offer_id": "offer-store-v1", "source": "AUTHOR",
                 "control_source": "LOCKED_FRAGMENT", "projection_id": "station:1:sourcehash",
                 "constraint_id": "repair-before-storage", "grant_id":
                    "station:repair-before-storage:fixed-native-grant",
                 "locked_fragment_hash": "locked-hash", "locked_sequence_index": 0,
                 "deadline_minute": 24, "actor_alias": "A", "task_kind": "store_item"}
        return offer, constraint

    def test_deferred_literal_offer_is_retained_only_while_exactly_current(self):
        offer, constraint = self._deferred_locked_store()
        args = (offer, constraint, "station:1:sourcehash",
                "station:repair-before-storage:fixed-native-grant", 13,
                {"offer-store-v1"}, [], [], {"supply_id": 30})
        self.assertTrue(_deferred_literal_offer_is_current(*args))
        self.assertFalse(_deferred_literal_offer_is_current(
            offer, constraint, "station:2:newsource", args[3], 13,
            args[5], args[6], args[7], args[8]))
        self.assertFalse(_deferred_literal_offer_is_current(
            offer, constraint, args[2], args[3], 25,
            args[5], args[6], args[7], args[8]))
        self.assertFalse(_deferred_literal_offer_is_current(
            offer, constraint, args[2], args[3], 13,
            args[5], [{"source_offer_id": "offer-store-v1", "status": "ACCEPTED"}],
            args[7], args[8]))
        self.assertFalse(_deferred_literal_offer_is_current(
            offer, constraint, args[2], args[3], 13,
            args[5], args[6], [{"event_type": "p5_station_supply_stored",
                                "provenance": "committed_ledger",
                                "args": {"item": {"stable_id": "30"}}}], args[8]))

    def _inputs(self, *, task_kind="inspect_supply", locked=False):
        event_constraint = {
            "constraint_id": "inspect-goal",
            "control": {"mode": "result_only", "allowed_methods": [
                "inspect_then_repair", "repair_then_inspect"]},
            "locked_fragment": None,
        }
        if locked:
            event_constraint = {
                "constraint_id": "station-lock",
                "control": {"mode": "locked_fragment", "allowed_methods": [
                    "inspect_then_repair", "repair_then_inspect"]},
                "locked_fragment": {"sequence": [{"actor_alias": "A",
                    "task_kind": "inspect_supply", "item_ref": "courier_supply",
                    "tool_ref": "station_tool", "destination_ref": "station_storage"}],
                    "sequence_sha256": "lock-hash"},
            }
        projection = SimpleNamespace(station_id="station-test", version=1,
            source_sha256="a" * 64, bundle_id="bundle-test",
            constraints=(event_constraint,))
        task = {"offer_id": "plan-offer", "source": "PLANNER",
            "source_method_id": ("repair_then_inspect" if task_kind == "repair_passage"
                                  else "inspect_then_repair"),
            "actor_alias": "B" if task_kind == "repair_passage" else "A",
            "task_kind": task_kind, "item_id": 30 if task_kind != "repair_passage" else None,
            "target_id": 31 if task_kind == "repair_passage" else 30,
            "tool_id": 20,
            "storage_destination_id": 40 if task_kind != "repair_passage" else None,
            "storage_room_id": 41 if task_kind != "repair_passage" else None,
            "target_room_id": 42 if task_kind != "store_item" else None,
            "duration_minutes": 2 if task_kind == "inspect_supply" else 1,
            "deadline_minute": 24, "planned_start_minute": 4,
            "earliest_terminal_minute": 7,
            "prerequisites": [], "required_constraint_ids": [event_constraint["constraint_id"]],
            "constraint_id": event_constraint["constraint_id"],
            "grant_id": "station-test:inspect-goal:fixed-native-grant"}
        if locked:
            task.update({"locked_fragment_sha256": "lock-hash", "locked_sequence_index": 0,
                         "constraint_id": "station-lock",
                         "required_constraint_ids": ["station-lock"],
                         "grant_id": "station-test:station-lock:fixed-native-grant"})
        method_id = "repair_then_inspect" if task_kind == "repair_passage" else "inspect_then_repair"
        decision = {"status": "CONDITIONAL_PLAN", "native_execution_occurred": False,
            "selected_method": method_id,
            "method_plans": [{"method_id": method_id, "feasible": True,
                              "task_requests": [task]}]}
        sealed = {"station_id": "station-test", "projection_id": "station-test:1:aaaaaaaaaaaa",
            "grant_ids": {"inspect-goal": "station-test:inspect-goal:fixed-native-grant",
                          "station-lock": "station-test:station-lock:fixed-native-grant"},
            "station_content": {"tool_id": 20, "supply_id": 30, "repair_exit_id": 31,
                                "storage_id": 40, "workbench_room_id": 42,
                                "storage_room_id": 41},
            "typed_trace": {"events": []}}
        return decision, projection, SimpleNamespace(station_id="station-test", version=1), sealed

    def test_author_offer_is_a_bound_proposal_not_execution(self):
        decision, projection, profile, sealed = self._inputs()
        offers = _station_work_offers_from_decision(decision, projection, profile, sealed, 3)
        self.assertEqual(len(offers), 1)
        row = offers[0]
        self.assertEqual(row["source"], "AUTHOR")
        self.assertEqual(row["source_method_id"], "inspect_then_repair")
        self.assertEqual(row["grant_id"], "station-test:inspect-goal:fixed-native-grant")
        self.assertEqual(row["actor_alias"], "A")
        self.assertEqual(row["tool_id"], 20)
        self.assertEqual(row["item_id"], 30)
        self.assertEqual(row["storage_destination_id"], 40)
        self.assertEqual(row["storage_room_id"], 41)
        self.assertEqual(row["target_room_id"], 42)
        self.assertEqual(row["planned_start_minute"], 4)
        self.assertEqual(row["earliest_terminal_minute"], 7)
        self.assertEqual(row["target_alias"], "courier_supply")

    def test_child_task_cannot_skip_unsettled_dependencies(self):
        decision, projection, profile, sealed = self._inputs(task_kind="store_item")
        self.assertEqual(_station_work_offers_from_decision(
            decision, projection, profile, sealed, 8), [])

    def test_locked_offer_preserves_fragment_hash_and_index(self):
        decision, projection, profile, sealed = self._inputs(locked=True)
        projection.constraints[0]["locked_fragment"]["sequence"] = [{
            "actor_alias": "A", "task_kind": "inspect_supply",
            "item_ref": "courier_supply", "tool_ref": "station_tool",
            "destination_ref": "station_storage"}]
        row = _station_work_offers_from_decision(decision, projection, profile, sealed, 3)[0]
        self.assertEqual(row["source_method_id"], "locked_fragment")
        self.assertEqual(row["control_source"], "LOCKED_FRAGMENT")
        self.assertEqual(row["locked_fragment_hash"], "lock-hash")
        self.assertEqual(row["locked_sequence_index"], 0)

    def test_locked_offer_rejects_nonregistered_exact_reference(self):
        decision, projection, profile, sealed = self._inputs(locked=True)
        projection.constraints[0]["locked_fragment"]["sequence"] = [{
            "actor_alias": "A", "task_kind": "inspect_supply",
            "item_ref": "wrong-supply", "tool_ref": "station_tool",
            "destination_ref": "station_storage"}]
        with self.assertRaisesRegex(ValueError, "authored exact sequence"):
            _station_work_offers_from_decision(decision, projection, profile, sealed, 3)

    def test_repair_offer_uses_exit_alias_not_supply_alias(self):
        decision, projection, profile, sealed = self._inputs(task_kind="repair_passage")
        row = _station_work_offers_from_decision(decision, projection, profile, sealed, 3)[0]
        self.assertEqual(row["target_alias"], "pickup_to_side_south")
        self.assertIsNone(row["item_alias"])
        self.assertIsNone(row["storage_destination_id"])

    def test_wrong_exact_grant_fails_closed(self):
        decision, projection, profile, sealed = self._inputs()
        decision["method_plans"][0]["task_requests"][0]["grant_id"] = "wrong"
        with self.assertRaisesRegex(ValueError, "exact native task grant"):
            _station_work_offers_from_decision(decision, projection, profile, sealed, 3)

    def test_unavailable_planner_never_becomes_an_offer(self):
        decision, projection, profile, sealed = self._inputs()
        decision["status"] = "WAIT_OR_UNSATISFIED"
        decision["task_requests"] = []
        self.assertEqual(_station_work_offers_from_decision(
            decision, projection, profile, sealed, 3), [])


if __name__ == "__main__":
    unittest.main()
