"""Focused offline regressions for the opt-in shared-tool work lifecycle."""
from __future__ import annotations

import unittest
from unittest.mock import patch
from collections.abc import Mapping, Sequence

from tools.native_platform_v0.p5.ongoing_station import work


class Attrs:
    def __init__(self, initial=None):
        self.values = dict(initial or {})

    def get(self, key, category=None, default=None):
        if category is None:
            return self.values.get(key, default)
        return self.values.get((category, key), default)

    def add(self, key, value, category=None):
        self.values[(category, key)] = value


class Room:
    def __init__(self, ident):
        self.id = ident
        self.attributes = Attrs({("native_p3", "p3_scene_id"): "s"})
        self.contents = []
        self.exits = []


class Obj:
    def __init__(self, ident, location=None, key="item", attrs=None):
        self.id, self.location, self.key = ident, location, key
        self.attributes = Attrs(attrs)
        self.contents = []
        self.locks = self.Locks(self)
        if location is not None:
            location.contents.append(self)

    @property
    def destination(self):
        return getattr(self, "_destination", None)

    @destination.setter
    def destination(self, value):
        self._destination = value

    def access(self, actor, access_type, default=True):
        return self.attributes.get("traversable", default=default)

    class Locks:
        def __init__(self, obj):
            self.obj = obj

        def add(self, lock):
            if lock == "traverse:true()":
                self.obj.attributes.values["traversable"] = True

    def move_to(self, destination, quiet=True):
        if self.location is not None and self in self.location.contents:
            self.location.contents.remove(self)
        self.location = destination
        destination.contents.append(self)
        return True


class Actor(Obj):
    def __init__(self, ident, location, attrs=None):
        super().__init__(ident, location, "actor", attrs)
        self.contents = []


class StationWorkTests(unittest.TestCase):
    def setUp(self):
        self.pickup = Room(1)
        self.destination = Room(2)
        self.side = Room(3)
        self.actor = Actor(10, self.pickup, {("native_p5", "p5_actor_alias"): "A",
                                             ("native_p3", "p3_scene_id"): "s"})
        self.supply = Obj(20, self.pickup, "supply", {("native_p3", "p3_scene_id"): "s"})
        self.tool = Obj(30, self.pickup, "tool", {("native_p3", "p3_scene_id"): "s"})
        self.storage = Obj(40, self.destination, "storage", {("native_p3", "p3_scene_id"): "s"})
        self.exit = Obj(50, self.pickup, "south", {("native_p3", "p3_scene_id"): "s",
                                                    "traversable": False})
        self.exit.destination = self.side
        self.rows = [self.pickup, self.destination, self.side, self.actor,
                     self.supply, self.tool, self.storage, self.exit]
        work.initialize_content(self.pickup, self.destination, self.side, self.supply,
                                self.tool, self.storage, self.exit)
        self.now = 4
        self.ledger = []

    def _append_event(self, actor_or_scene, event):
        row = {**event, "minute": self.now, "sequence": len(self.ledger) + 1,
               "sealed": event.get("sealed", True)}
        self.ledger.append(row)
        return row

    def _patch_world(self):
        return (
            patch("tools.native_platform_v0.p5.service._scene_objects",
                  return_value=(self.pickup, self.rows)),
            patch("tools.native_platform_v0.p3.p4_world.clock_for_actor",
                  side_effect=lambda _actor: {"now": self.now, "deadline": 24}),
            patch("tools.native_platform_v0.p3.p4_world.append_event", side_effect=self._append_event),
        )

    def _authorize(self, actor, task):
        actor.attributes.add("pending_action", {"intent": {"operator": "use_tool"},
                                                  "ongoing_task": dict(task)}, category="native_p3")
        actor.attributes.add("ongoing_commitments", [{**task, "status": "ACCEPTED"}],
                             category="native_p5")

    def test_work_waits_until_due_then_emits_one_receipt_and_effect(self):
        patches = self._patch_world()
        for item in patches:
            item.start()
        try:
            task = {"task_kind": "inspect_supply", "commitment_id": "c1", "tool_id": 30,
                    "target_id": 20, "target_room_id": 1, "item_id": 20,
                    "duration_minutes": 2, "deadline_minute": 10, "grant_id": "g1",
                    "source": "SELF"}
            self._authorize(self.actor, task)
            started = work.start_work(self.actor, task, now_minute=4, scene_id="s")
            self.assertTrue(started["ok"])
            self.assertEqual(self.tool.attributes.get("p5_station_tool_lease", category="native_p5")["status"], "BUSY")
            self.now = 5
            waiting = work.advance_work(self.actor, now_minute=5)
            self.assertEqual(waiting["status"], "IN_PROGRESS")
            self.assertEqual(self.supply.attributes.get("p5_supply_inspection_status", category="native_p5"), "UNINSPECTED")
            self.now = 6
            finished = work.advance_work(self.actor, now_minute=6)
            self.assertEqual(finished["status"], "SETTLED")
            self.assertTrue(finished["released_lease"])
            self.assertEqual(self.supply.attributes.get("p5_supply_inspection_status", category="native_p5"), "APPROVED")
            receipts = self.actor.attributes.get("station_work_receipts", category="native_p5")
            self.assertEqual(len(receipts), 1)
            self.assertEqual(receipts[0]["started_minute"], 4)
            self.assertEqual(receipts[0]["completed_minute"], 6)
            self.assertEqual(self.tool.attributes.get("p5_station_tool_lease", category="native_p5")["status"], "FREE")
            self.assertIsNone(work.advance_work(self.actor, now_minute=6))
            self.assertEqual(len(self.actor.attributes.get("station_work_receipts", category="native_p5")), 1)
        finally:
            for item in patches:
                item.stop()

    def test_tool_take_during_work_aborts_and_releases_only_matching_lease(self):
        patches = self._patch_world()
        for item in patches:
            item.start()
        try:
            task = {"task_kind": "repair_passage", "commitment_id": "repair-1", "tool_id": 30,
                    "target_id": 50, "target_room_id": 1, "duration_minutes": 3,
                    "deadline_minute": 12, "grant_id": "g1", "source": "SELF"}
            self._authorize(self.actor, task)
            self.assertTrue(work.start_work(self.actor, task, now_minute=4, scene_id="s")["ok"])
            player = Actor(99, self.pickup)
            self.tool.move_to(player)
            self.now = 5
            result = work.advance_work(self.actor, now_minute=5)
            self.assertEqual(result["status"], "ABORTED")
            self.assertEqual(result["receipt"]["abort_reason"], "tool_moved_or_actor_left_workbench")
            self.assertFalse(self.exit.access(self.actor, "traverse", default=False))
            self.assertIsNone(result["receipt"]["effect"])
            self.assertEqual(self.tool.attributes.get("p5_station_tool_lease", category="native_p5")["status"], "FREE")
        finally:
            for item in patches:
                item.stop()

    def test_stale_callback_does_not_clear_a_new_lease(self):
        patches = self._patch_world()
        for item in patches:
            item.start()
        try:
            task = {"task_kind": "repair_passage", "commitment_id": "old", "tool_id": 30,
                    "target_id": 50, "target_room_id": 1, "duration_minutes": 3,
                    "deadline_minute": 12, "grant_id": "g1", "source": "SELF"}
            self._authorize(self.actor, task)
            work.start_work(self.actor, task, now_minute=4, scene_id="s")
            self.tool.attributes.add("p5_station_tool_lease", {
                "status": "BUSY", "lease_id": "new-lease", "actor_id": 11,
                "commitment_id": "new", "task_kind": "repair_passage",
                "started_minute": 5, "due_minute": 8}, category="native_p5")
            self.now = 5
            result = work.advance_work(self.actor, now_minute=5)
            self.assertEqual(result["status"], "ABORTED")
            self.assertFalse(result["released_lease"])
            self.assertEqual(self.tool.attributes.get("p5_station_tool_lease", category="native_p5")["lease_id"], "new-lease")
        finally:
            for item in patches:
                item.stop()

    def test_start_uses_current_clock_and_rejects_second_actor_capacity(self):
        patches = self._patch_world()
        for item in patches:
            item.start()
        try:
            task = {"task_kind": "repair_passage", "commitment_id": "repair-1", "tool_id": 30,
                    "target_id": 50, "target_room_id": 1, "duration_minutes": 3,
                    "deadline_minute": 12, "grant_id": "g1", "source": "SELF"}
            self._authorize(self.actor, task)
            rejected = work.start_work(self.actor, task, now_minute=5, scene_id="s")
            self.assertEqual(rejected["reason"], "work_start_must_use_current_p4_minute")
            self.assertEqual(rejected["receipt"]["outcome"], "WORLD_VALIDATION_REJECTED")
            self.assertIsNone(rejected["receipt"]["world_delta"])
            self.assertTrue(any(row.get("event_type") == "P5_STATION_WORK_START_REJECTED"
                                for row in self.ledger))
            self.assertTrue(work.start_work(self.actor, task, now_minute=4, scene_id="s")["ok"])
            other = Actor(11, self.pickup, {("native_p5", "p5_actor_alias"): "B",
                                             ("native_p3", "p3_scene_id"): "s"})
            second = {**task, "commitment_id": "repair-2", "source": "SELF"}
            self._authorize(other, second)
            self.assertEqual(work.start_work(other, second, now_minute=4, scene_id="s")["reason"],
                             "shared_tool_capacity_one_is_occupied")
        finally:
            for item in patches:
                item.stop()

    def test_player_loan_request_uses_scene_clock_not_actor_clock(self):
        # Players are valid intervention sources but are not P4 story actors.
        # The operation must use the existing scene-owned clock and produce a
        # receipt without asking clock_for_actor(player).
        self.pickup.attributes.add("p4_clock", {"now": 1, "deadline": 24},
                                   category="native_p3")
        self.actor.attributes.add("p5_actor_alias", "A", category="native_p5")
        borrower = Actor(11, self.pickup, {("native_p5", "p5_actor_alias"): "B",
                                           ("native_p3", "p3_scene_id"): "s"})
        player = Actor(99, self.pickup, {("native_p3", "p3_control_role"): "player",
                                         ("native_p3", "p3_scene_id"): "s",
                                         ("native_p5", "p5_station_profile_enabled"): True})
        self.rows.extend((borrower, player))
        with patch("tools.native_platform_v0.p5.service._scene_objects",
                   return_value=(self.pickup, self.rows)), \
             patch("tools.native_platform_v0.p3.p4_world.clock_for_actor",
                   side_effect=AssertionError("player must not use actor clock access")):
            result = work.request_tool_loan(player, tool_id=30, lender_alias="A",
                                            borrower_alias="B", due_minute=3)
        self.assertEqual(result["status"], "REQUESTED")
        self.assertTrue(result["settled"])
        self.assertEqual(result["request"]["requested_minute"], 1)
        self.assertEqual(result["receipt"]["due_minute"], 3)
        self.assertEqual(result["receipt"]["sim_minute"], 1)
        for witness in (self.actor, borrower):
            local_request = witness.attributes.get("p5_station_loan_request", category="native_p5")
            self.assertEqual(local_request["request_id"], result["request"]["request_id"])

    def test_player_loan_request_rejects_due_after_scene_clock_deadline(self):
        self.pickup.attributes.add("p4_clock", {"now": 1, "deadline": 4},
                                   category="native_p3")
        self.actor.attributes.add("p5_actor_alias", "A", category="native_p5")
        borrower = Actor(11, self.pickup, {("native_p5", "p5_actor_alias"): "B",
                                           ("native_p3", "p3_scene_id"): "s"})
        player = Actor(99, self.pickup, {("native_p3", "p3_control_role"): "player",
                                         ("native_p3", "p3_scene_id"): "s",
                                         ("native_p5", "p5_station_profile_enabled"): True})
        self.rows.extend((borrower, player))
        with patch("tools.native_platform_v0.p5.service._scene_objects",
                   return_value=(self.pickup, self.rows)), \
             patch("tools.native_platform_v0.p3.p4_world.clock_for_actor",
                   side_effect=AssertionError("player must not use actor clock access")):
            result = work.request_tool_loan(player, tool_id=30, lender_alias="A",
                                            borrower_alias="B", due_minute=5)
        self.assertEqual(result["status"], "WORLD_VALIDATION_REJECTED")
        self.assertEqual(result["reason"], "due_minute_must_be_after_now_and_within_native_deadline")
        self.assertIsNone(result["request"])

    def test_store_requires_receipt_backed_inspection_and_real_container_move(self):
        patches = self._patch_world()
        for item in patches:
            item.start()
        try:
            self.actor.move_to(self.destination)
            self.supply.move_to(self.actor)
            self.storage.attributes.add("p5_station_storage", True, category="native_p5")
            rejected = work.store_supply(self.actor, item_id=20)
            self.assertFalse(rejected["settled"])
            self.assertEqual(rejected["reason"], "supply_has_no_completed_native_inspection")
            self.supply.attributes.add("p5_supply_inspection_status", "APPROVED", category="native_p5")
            self.assertFalse(work.store_supply(self.actor, item_id=20)["settled"])
            self.assertEqual(work.store_supply(self.actor, item_id=21)["reason"],
                             "item_is_not_the_registered_station_supply")
        finally:
            for item in patches:
                item.stop()

    def test_store_moves_only_receipt_inspected_supply_into_registered_container(self):
        patches = self._patch_world()
        for item in patches:
            item.start()
        try:
            self.actor.move_to(self.destination)
            self.supply.move_to(self.actor)
            inspect_receipt = {"receipt_id": "inspect-r1", "task_kind": "inspect_supply",
                               "actor_id": 10, "actor_alias": "A", "item_id": 20,
                               "tool_id": 30, "commitment_id": "inspect-c1", "settled": True,
                               "outcome": "SETTLED", "effect": {"after_status": "APPROVED"}}
            self.actor.attributes.add("station_work_receipts", [inspect_receipt], category="native_p5")
            self.supply.attributes.add("p5_supply_inspection_status", "APPROVED", category="native_p5")
            self.pickup.attributes.add("p4_ledger", [{"event_type": "P5_STATION_SUPPLY_INSPECTED",
                "event_id": "inspect-r1", "receipt_id": "inspect-r1", "minute": 4, "sequence": 1,
                "sealed": True, "typed_args": {"receipt_id": "inspect-r1", "actor_id": 10,
                    "item_id": 20, "tool_id": 30, "outcome": "SETTLED"}}], category="native_p3")
            self.actor.attributes.add("pending_action", {"ongoing_task": {"commitment_id": "store-c1"}},
                                       category="native_p3")
            result = work.store_supply(self.actor, item_id=20)
            self.assertTrue(result["settled"])
            self.assertEqual(result["after_container_id"], 40)
            self.assertIs(self.supply.location, self.storage)
            self.assertIn(20, result["before_inventory_ids"])
            self.assertNotIn(20, result["after_inventory_ids"])
            self.assertEqual(result["commitment_id"], "store-c1")
        finally:
            for item in patches:
                item.stop()

    def test_player_request_is_current_local_evidence_not_an_npc_commitment_or_loan(self):
        self.pickup.attributes.add("p4_clock", {"now": 4, "deadline": 24},
                                   category="native_p3")
        player = Actor(99, self.pickup, {("native_p3", "p3_scene_id"): "s",
                                         ("native_p3", "p3_control_role"): "player",
                                         ("native_p5", "p5_station_profile_enabled"): True,
                                         ("native_p3", "native_receipts"): []})
        borrower = Actor(11, self.pickup, {("native_p3", "p3_scene_id"): "s",
                                          ("native_p5", "p5_actor_alias"): "B"})
        self.actor.attributes.add("p5_station_profile_enabled", True, category="native_p5")
        self.actor.attributes.add("p5_actor_alias", "A", category="native_p5")
        self.rows.extend([player, borrower])
        patches = self._patch_world()
        for item in patches:
            item.start()
        try:
            result = work.request_tool_loan(player, tool_id=30, lender_alias="A",
                                            borrower_alias="B", due_minute=8)
            self.assertTrue(result["settled"])
            request = result["request"]
            self.assertEqual(request["requested_minute"], 4)
            self.assertEqual(request["tool_holder_alias"], None)
            self.assertEqual(self.actor.attributes.get("p5_station_loan_request", category="native_p5"),
                             request)
            self.assertEqual(borrower.attributes.get("p5_station_loan_request", category="native_p5"),
                             request)
            self.assertEqual(len(player.attributes.get("native_receipts", category="native_p3")), 1)
            self.assertEqual(player.attributes.get("ongoing_commitments", category="native_p5"), None)
            self.assertIsNone(self.tool.attributes.get("p5_station_active_loan", category="native_p5"))
            rejected = work.request_tool_loan(player, tool_id=30, lender_alias="A",
                                              borrower_alias="B", due_minute=4)
            self.assertFalse(rejected["settled"])
            self.assertEqual(rejected["reason"], "due_minute_must_be_after_now_and_within_native_deadline")
            self.assertEqual(self.actor.attributes.get("p5_station_loan_request", category="native_p5"),
                             request)
            self.tool.move_to(self.actor)
            held_request = work.request_tool_loan(player, tool_id=30, lender_alias="A",
                                                  borrower_alias="B", due_minute=9)
            self.assertTrue(held_request["settled"])
            self.assertEqual(held_request["request"]["tool_holder_alias"], "A")
        finally:
            for item in patches:
                item.stop()

    def test_successful_repair_emits_exact_receipt_visible_on_registered_exit(self):
        patches = self._patch_world()
        for item in patches:
            item.start()
        try:
            task = {"task_kind": "repair_passage", "commitment_id": "repair-1", "tool_id": 30,
                    "target_id": 50, "target_room_id": 1, "duration_minutes": 3,
                    "deadline_minute": 12, "grant_id": "g1", "source": "SELF"}
            self._authorize(self.actor, task)
            started = work.start_work(self.actor, task, now_minute=4, scene_id="s")
            self.assertTrue(started["ok"])
            self.now = 7
            result = work.advance_work(self.actor, now_minute=7)
            self.assertEqual(result["status"], "SETTLED")
            self.assertTrue(self.exit.access(self.actor, "traverse", default=False))
            witness = self.exit.attributes.get("p5_last_repair_receipt", category="native_p5")
            self.assertEqual(witness["receipt_id"], result["receipt"]["receipt_id"])
            self.assertEqual(witness["actor_alias"], "A")
            self.assertEqual(witness["outcome"], "SETTLED")
        finally:
            for item in patches:
                item.stop()

    def test_typed_work_projection_rejects_a_mismatched_committed_event(self):
        patches = self._patch_world()
        for item in patches:
            item.start()
        try:
            task = {"task_kind": "inspect_supply", "commitment_id": "c1", "tool_id": 30,
                    "target_id": 20, "target_room_id": 1, "item_id": 20,
                    "duration_minutes": 2, "deadline_minute": 10, "grant_id": "g1",
                    "source": "SELF"}
            self._authorize(self.actor, task)
            work.start_work(self.actor, task, now_minute=4, scene_id="s")
            self.now = 6
            work.advance_work(self.actor, now_minute=6)
            from tools.native_platform_v0.p5.ongoing_station.controller import _station_work_typed_events

            class Service:
                @staticmethod
                def _plain_json(value):
                    if isinstance(value, Mapping):
                        return {key: Service._plain_json(item) for key, item in value.items()}
                    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
                        return [Service._plain_json(item) for item in value]
                    return value

                @staticmethod
                def _attr(obj, key, default=None, category="native_p3"):
                    return obj.attributes.get(key, category=category, default=default)

            events = _station_work_typed_events(self.ledger, self.rows, {"A": self.actor}, Service())
            self.assertEqual([row["event_type"] for row in events], ["p5_station_supply_inspected"])
            bad_ledger = [{**self.ledger[0], "typed_args": {
                **self.ledger[0]["typed_args"], "target_id": 999}}]
            self.assertEqual(_station_work_typed_events(bad_ledger, self.rows,
                                                        {"A": self.actor}, Service()), [])
        finally:
            for item in patches:
                item.stop()


if __name__ == "__main__":
    unittest.main()
