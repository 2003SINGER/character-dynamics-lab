import unittest
from collections import UserDict, UserList
from types import SimpleNamespace
from unittest.mock import patch

from tools.native_platform_v0.p3.agency import (P3AutonomyScript, _dispatch_pending, _settle_pending,
                                                choose_goal, make_decision, observe_actor)
from tools.native_platform_v0.p3.planning import freeze, plan_next, plan_patrol, thaw


class Attrs:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, key, category=None, default=None):
        return self.values.get((category, key), default)

    def add(self, key, value, category=None):
        self.values[(category, key)] = value


class Room:
    def __init__(self, ident, dbref):
        self.id, self.dbref = ident, dbref
        self.contents, self.exits = [], []


class Thing:
    def __init__(self, ident, key, location=None, visible=True):
        self.id, self.key, self.location = ident, key, location
        self.dbref = f"#{ident}"
        self.contents = []
        self.visible = visible

    def access(self, accessing_obj, access_type, default=False):
        return self.visible


class Exit(Thing):
    def __init__(self, key, source, destination):
        super().__init__(destination.id + 100, key, source)
        self.destination = destination


class Actor(Thing):
    def __init__(self, ident, location, attrs):
        super().__init__(ident, "Courier", location)
        self.attributes = Attrs(attrs)
        location.contents.append(self)


def view(room_id=1, item_room=1, item_held=False, exits=None):
    return {
        "actor_id": 9,
        "activity_contract": {"profile": "legacy_delivery_v0", "delivery_task": True},
        "goal_contract": {"goal": "deliver_supply", "item_id": 10,
                           "destination_id": 2, "source": "scenario-authored-task"},
        "observation": {
            "room_id": room_id,
            "inventory": [{"id": 10, "key": "Supply"}] if item_held else [],
            "visible_items": [],
            "task_item": {"id": 10, "key": "Supply"},
            "task_destination": 2,
            "item_location": item_room,
            "item_held": item_held,
            "delivered": False,
            "own_delivery_receipts": [],
            "known_exits": {1: [2], 2: [1]},
            "exits": exits if exits is not None else ([{"key": "east", "destination_id": 2}] if room_id == 1 else
                                                        [{"key": "west", "destination_id": 1}]),
            "witnessed": [],
            "retained_witnesses": [],
        },
    }


class P3ActorLoopTests(unittest.TestCase):
    def test_local_view_freezes_evennia_style_mapping_and_sequence_protocols(self):
        local = UserDict({"receipt": UserDict({"items": UserList([1, 2])})})
        frozen = freeze(local)
        self.assertEqual(frozen["receipt"]["items"], (1, 2))
        with self.assertRaises(TypeError):
            frozen["receipt"]["new"] = "mutation"
        with self.assertRaises(AttributeError):
            frozen["receipt"]["items"].append(3)
        self.assertEqual(thaw(frozen), {"receipt": {"items": [1, 2]}})

    def test_htn_proposes_only_next_local_primitive(self):
        result = plan_next(view(), "deliver_supply")
        self.assertEqual(result["status"], "SOLVED")
        self.assertEqual(result["intent"], {"operator": "get", "item_id": "10"})
        carried = plan_next(view(room_id=1, item_room=None, item_held=True), "deliver_supply")
        self.assertEqual(carried["intent"], {"operator": "move", "exit_key": "east", "destination_id": 2})
        self.assertTrue(carried["prediction_only"])

    def test_patrol_planner_uses_only_visible_exits_and_waits_when_none(self):
        patrol_view = view()
        patrol_view["observation"]["exits"] = [
            {"key": "west", "destination_id": 3},
            {"key": "east", "destination_id": 2},
        ]
        result = plan_patrol(patrol_view)
        self.assertEqual(result["intent"], {"operator": "move", "exit_key": "east", "destination_id": 2})
        waiting = plan_patrol(patrol_view, rejected_exits=[("east", 2), ("west", 3)])
        self.assertIsNone(waiting["intent"])
        self.assertEqual(waiting["status"], "WAIT")
        no_exits = plan_patrol({"observation": {"exits": []}})
        self.assertIsNone(no_exits["intent"])
        self.assertEqual(no_exits["reason"], "no currently visible exits")

    def test_delivery_priority_and_persistent_own_receipt_choose_patrol(self):
        active = view()
        active["activity_contract"] = {"profile": "delivery_patrol_v0", "delivery_task": True}
        choice = choose_goal(active)
        self.assertEqual(choice["candidates"], ["deliver_supply", "patrol"])
        self.assertEqual(choice["choice"], "deliver_supply")

        blocked = view(item_room=None)
        blocked["activity_contract"] = {"profile": "delivery_patrol_v0", "delivery_task": True}
        self.assertEqual(choose_goal(blocked)["choice"], "deliver_supply")
        self.assertIsNone(plan_next(blocked, "deliver_supply")["intent"])

        completed = view(room_id=2, item_room=None)
        completed["activity_contract"] = {"profile": "delivery_patrol_v0", "delivery_task": True}
        completed["observation"]["own_delivery_receipts"] = [
            {"kind": "drop", "settled": True, "item_id": 10, "after_item_room_id": 2}
        ]
        self.assertEqual(choose_goal(completed)["choice"], "patrol")

        no_task = view()
        no_task["activity_contract"] = {"profile": "delivery_patrol_v0", "delivery_task": False}
        no_task["goal_contract"]["item_id"] = None
        self.assertEqual(choose_goal(no_task)["choice"], "patrol")

    def test_recovery_profile_suspends_only_for_local_item_absence_and_resumes_on_sighting(self):
        missing = view(item_room=None)
        missing["activity_contract"] = {"profile": "delivery_patrol_recovery_v0", "delivery_task": True}
        missing["observation"]["retained_witnesses"] = [
            {"room_id": None, "status": "not_visible_after_rejected_get"}
        ]
        suspended = choose_goal(missing)
        self.assertEqual(suspended["choice"], "patrol")
        self.assertEqual(suspended["delivery_status"], "SUSPENDED_LOCAL_ITEM_UNAVAILABLE")
        self.assertEqual(suspended["inputs"]["local_evidence"]["retained_item_location"], None)

        # A world-side return that is not in this actor's current O changes
        # nothing: no global query or controller resume signal is represented.
        still_unobserved = choose_goal(missing)
        self.assertEqual(still_unobserved["choice"], "patrol")

        visible_again = view(item_room=1)
        visible_again["activity_contract"] = {
            "profile": "delivery_patrol_recovery_v0", "delivery_task": True
        }
        visible_again["observation"]["visible_items"] = [{"id": 10, "key": "Supply", "room_id": 1}]
        resumed = choose_goal(visible_again)
        self.assertEqual(resumed["choice"], "deliver_supply")
        self.assertEqual(resumed["delivery_status"], "ACTIVE")
        actor = Thing(9, "Courier")
        actor.attributes = Attrs()
        actor.location = Room(1, "#1")
        with patch("tools.native_platform_v0.p3.agency.observe_actor", return_value=freeze(visible_again)):
            resumed_decision = make_decision(actor)
        self.assertEqual(resumed_decision["planner"]["status"], "SOLVED")
        self.assertEqual(resumed_decision["intent"]["operator"], "get")

    def test_rejected_get_suspends_from_updated_witness_and_keeps_failure_receipt(self):
        room = Room(1, "#1")
        destination = Room(2, "#2")
        room.exits.append(Exit("east", room, destination))
        item = Thing(10, "Supply", room)
        room.contents.append(item)
        actor = Actor(9, room, {
            ("native_p3", "activity_profile"): "delivery_patrol_recovery_v0",
            ("native_p3", "delivery_task"): True,
            ("native_p3", "task_item_id"): 10,
            ("native_p3", "task_destination_id"): 2,
            ("native_p3", "task_item_key"): "Supply",
            ("native_p3", "goal"): "deliver_supply",
            ("native_p3", "witnessed"): {"edges": {}, "objects": {}},
            ("native_p3", "native_receipts"): [],
            ("native_p3", "log"): [],
        })
        planned = make_decision(actor)
        self.assertEqual(planned["intent"]["operator"], "get")
        pending = {"goal": planned["goal"], "intent": planned["intent"],
                   "view": thaw(planned["view"]), "submitted_command": "get Supply"}
        room.contents.remove(item)  # player takes it after planning
        _settle_pending(actor, pending, 1, [], 1, "WORLD_VALIDATION_REJECTED",
                        "assigned item is not visible in the actor's current room",
                        dispatch_succeeded=False)
        outcome = actor.attributes.get("last_outcome", category="native_p3")
        self.assertFalse(outcome["receipt"]["settled"])
        self.assertEqual(outcome["status"], "WORLD_VALIDATION_REJECTED")
        self.assertEqual(actor.attributes.get("native_receipts", category="native_p3"), [])
        next_decision = make_decision(actor)
        self.assertEqual(next_decision["goal"]["choice"], "patrol")
        self.assertEqual(next_decision["goal"]["delivery_status"], "SUSPENDED_LOCAL_ITEM_UNAVAILABLE")

    def test_recovery_does_not_fallback_for_invalid_binding_no_plan_or_budget(self):
        invalid = view(item_room=None)
        invalid["activity_contract"] = {
            "profile": "delivery_patrol_recovery_v0", "delivery_task": True
        }
        invalid["goal_contract"]["item_id"] = None
        invalid["observation"]["task_item"]["id"] = None
        invalid_choice = choose_goal(invalid)
        self.assertEqual(invalid_choice["choice"], "deliver_supply")
        self.assertEqual(invalid_choice["delivery_status"], "INVALID_BINDING")

        available = view(item_room=1)
        available["activity_contract"] = {
            "profile": "delivery_patrol_recovery_v0", "delivery_task": True
        }
        for planner_status in ("NO_PLAN", "BUDGET"):
            with self.subTest(planner_status=planner_status), patch(
                    "tools.native_platform_v0.p3.agency.plan_next",
                    return_value={"status": planner_status, "reason": "planner test", "intent": None}):
                actor = Thing(9, "Courier")
                actor.attributes = Attrs()
                actor.location = Room(1, "#1")
                from tools.native_platform_v0.p3.agency import set_value
                set_value(actor, "activity_profile", "delivery_patrol_recovery_v0")
                set_value(actor, "delivery_task", True)
                set_value(actor, "task_item_id", 10)
                set_value(actor, "task_destination_id", 2)
                set_value(actor, "goal", "deliver_supply")
                with patch("tools.native_platform_v0.p3.agency.observe_actor", return_value=freeze(available)):
                    decision = make_decision(actor)
                self.assertEqual(decision["goal"]["choice"], "deliver_supply")
                self.assertEqual(decision["goal"]["delivery_status"], "ACTIVE")
                self.assertIsNone(decision["intent"])
                self.assertEqual(decision["planner"]["status"], planner_status)

    def test_completed_recovery_delivery_receipt_remains_complete_after_patrol(self):
        completed = view(room_id=1, item_room=None)
        completed["activity_contract"] = {
            "profile": "delivery_patrol_recovery_v0", "delivery_task": True
        }
        completed["observation"]["own_delivery_receipts"] = [
            {"kind": "drop", "settled": True, "item_id": 10, "after_item_room_id": 2}
        ]
        selection = choose_goal(completed)
        self.assertEqual(selection["choice"], "patrol")
        self.assertEqual(selection["delivery_status"], "SETTLED")

    def test_recovery_profile_native_get_submits_observed_key_for_missing_item(self):
        room = Room(1, "#1")
        destination = Room(2, "#2")
        room.exits.append(Exit("east", room, destination))
        actor = Actor(9, room, {})
        actor.ndb = SimpleNamespace(p3_pending_operation_id=None)
        local = view(item_room=1)
        local["activity_contract"] = {
            "profile": "delivery_patrol_recovery_v0", "delivery_task": True
        }
        local["observation"]["visible_items"] = [{"id": 10, "key": "Supply", "room_id": 1}]
        pending = {"status": "planned", "operation_id": "op1", "intent": {"operator": "get", "item_id": "10"},
                   "goal": {"choice": "deliver_supply"}, "view": local}
        commands = []
        actor.execute_cmd = lambda command: commands.append(command)
        _dispatch_pending(actor, pending)
        self.assertEqual(commands, ["get Supply"])
        outcome = actor.attributes.get("last_outcome", category="native_p3")
        self.assertEqual(outcome["status"], "WORLD_VALIDATION_REJECTED")
        self.assertFalse(outcome["receipt"]["settled"])
        self.assertTrue(outcome["receipt"]["dispatch_succeeded"])
        self.assertEqual(outcome["receipt"]["submitted_command"], "get Supply")

    def test_recovery_get_refuses_same_key_different_id(self):
        room = Room(1, "#1")
        wrong = Thing(11, "Supply", room)
        room.contents.append(wrong)
        actor = Actor(9, room, {})
        actor.ndb = SimpleNamespace(p3_pending_operation_id=None)
        local = view(item_room=1)
        local["activity_contract"] = {
            "profile": "delivery_patrol_recovery_v0", "delivery_task": True
        }
        local["observation"]["visible_items"] = [{"id": 10, "key": "Supply", "room_id": 1}]
        pending = {"status": "planned", "operation_id": "op2", "intent": {"operator": "get", "item_id": "10"},
                   "goal": {"choice": "deliver_supply"}, "view": local}
        commands = []
        actor.execute_cmd = lambda command: commands.append(command)
        _dispatch_pending(actor, pending)
        self.assertEqual(commands, [])
        outcome = actor.attributes.get("last_outcome", category="native_p3")
        self.assertEqual(outcome["status"], "WORLD_VALIDATION_REJECTED")
        self.assertIn("same-key", outcome["detail"])

    def test_rejected_patrol_move_records_native_command_and_waits_without_retry(self):
        room = Room(1, "#1")
        destination = Room(2, "#2")
        room.exits.append(Exit("east", room, destination))
        actor = Actor(9, room, {
            ("native_p3", "activity_profile"): "delivery_patrol_v0",
            ("native_p3", "delivery_task"): False,
            ("native_p3", "goal"): "deliver_supply",
            ("native_p3", "task_item_id"): None,
            ("native_p3", "task_destination_id"): 2,
            ("native_p3", "status"): "RUNNING",
            ("native_p3", "tick_count"): 0,
            ("native_p3", "log"): [],
            ("native_p3", "native_receipts"): [],
            ("native_p3", "witnessed"): {"edges": {}, "objects": {}},
        })
        decision = make_decision(actor)
        self.assertEqual(decision["goal"]["choice"], "patrol")
        self.assertEqual(decision["intent"]["operator"], "move")
        pending = {"goal": decision["goal"], "intent": decision["intent"],
                   "view": thaw(decision["view"]), "submitted_command": "east"}
        _settle_pending(actor, pending, 1, [], None, None, None, dispatch_succeeded=True)
        outcome = actor.attributes.get("last_outcome", category="native_p3")
        self.assertEqual(outcome["receipt"]["submitted_command"], "east")
        self.assertFalse(outcome["receipt"]["settled"])
        self.assertIn("observed world state did not show the expected move transition", outcome["detail"])
        self.assertEqual(actor.attributes.get("native_receipts", category="native_p3"), [])
        waiting = make_decision(actor)
        self.assertIsNone(waiting["intent"])
        self.assertEqual(waiting["planner"]["status"], "WAIT")
        self.assertEqual(actor.attributes.get("patrol_rejected_state", category="native_p3")["rejected"], [["east", 2]])

    def test_no_task_script_records_choice_and_settles_one_move_command(self):
        room = Room(1, "#1")
        destination = Room(2, "#2")
        room.exits.append(Exit("east", room, destination))
        actor = Actor(9, room, {
            ("native_p3", "activity_profile"): "delivery_patrol_v0",
            ("native_p3", "delivery_task"): False,
            ("native_p3", "goal"): "deliver_supply",
            ("native_p3", "task_item_id"): None,
            ("native_p3", "task_destination_id"): 2,
            ("native_p3", "status"): "RUNNING",
            ("native_p3", "tick_count"): 0,
            ("native_p3", "log"): [],
            ("native_p3", "native_receipts"): [],
            ("native_p3", "witnessed"): {"edges": {}, "objects": {}},
        })
        actor.ndb = SimpleNamespace(p3_pending_operation_id=None)

        def move(command):
            self.assertEqual(command, "east")
            room.contents.remove(actor)
            destination.contents.append(actor)
            actor.location = destination
            return None

        actor.execute_cmd = move
        script = P3AutonomyScript()
        script.obj = actor
        script.at_repeat()  # choose and persist; do not execute in the same callback
        choice = next(event for event in actor.attributes.get("log", category="native_p3")
                      if event.get("kind") == "goal_choice")
        self.assertEqual(choice["inputs"]["delivery_task"], False)
        self.assertEqual(choice["candidates"], ["patrol"])
        self.assertEqual(choice["rule"], "delivery_before_patrol_v0")
        self.assertEqual(choice["choice"], "patrol")
        script.at_repeat()  # the persisted move is submitted and settled
        receipts = actor.attributes.get("native_receipts", category="native_p3")
        self.assertEqual(actor.location.id, 2)
        self.assertEqual(len(receipts), 1)
        self.assertEqual(receipts[0]["kind"], "move")
        self.assertEqual(receipts[0]["submitted_command"], "east")
        self.assertTrue(receipts[0]["settled"])

    def test_observer_does_not_leak_hidden_local_item_or_stale_location(self):
        room = Room(1, "#1")
        hidden = Thing(10, "Supply", room, visible=False)
        room.contents.append(hidden)
        actor = Actor(9, room, {
            ("native_p3", "task_item_id"): 10,
            ("native_p3", "task_destination_id"): 2,
            ("native_p3", "task_item_key"): "Supply",
            ("native_p3", "witnessed"): {"edges": {}, "objects": {"10": {"room_id": 1, "key": "Supply"}}},
            ("native_p3", "goal"): "deliver_supply",
        })
        observed = observe_actor(actor)
        self.assertEqual(observed["observation"]["visible_items"], ())
        self.assertIsNone(observed["observation"]["item_location"])
        self.assertEqual(observed["observation"]["retained_witnesses"][0]["status"],
                         "not_visible_in_last_seen_room")

    def test_failed_drop_cannot_use_coincidental_destination_state_as_receipt(self):
        room = Room(2, "#2")
        item = Thing(10, "Supply", room)
        room.contents.append(item)
        actor = Actor(9, room, {
            ("native_p3", "tick_count"): 4,
            ("native_p3", "log"): [],
            ("native_p3", "pending_action"): {"status": "executing"},
        })
        pending = {"intent": {"operator": "drop", "item_id": 10, "room_id": 2},
                   "view": {"goal_contract": {"item_id": 10}}}
        _settle_pending(actor, pending, 2, [], 2, "WORLD_VALIDATION_REJECTED",
                        "native command did not dispatch", dispatch_succeeded=False)
        outcome = actor.attributes.get("last_outcome", category="native_p3")
        self.assertEqual(outcome["status"], "WORLD_VALIDATION_REJECTED")
        self.assertFalse(outcome["receipt"]["settled"])
        self.assertFalse(outcome["receipt"]["dispatch_succeeded"])

    def test_native_script_callback_persists_one_htn_intent_without_executing_it(self):
        room = Room(1, "#1")
        destination = Room(2, "#2")
        room.exits.append(Exit("east", room, destination))
        item = Thing(10, "Supply", room)
        room.contents.append(item)
        actor = Actor(9, room, {
            ("native_p3", "task_item_id"): 10,
            ("native_p3", "task_destination_id"): 2,
            ("native_p3", "task_item_key"): "Supply",
            ("native_p3", "goal"): "deliver_supply",
            ("native_p3", "status"): "RUNNING",
            ("native_p3", "tick_count"): 0,
            ("native_p3", "log"): [],
            ("native_p3", "witnessed"): {"edges": {}, "objects": {}},
            ("native_p3", "native_receipts"): [],
        })
        script = P3AutonomyScript()
        script.obj = actor
        script.at_repeat()
        pending = actor.attributes.get("pending_action", category="native_p3")
        self.assertEqual(actor.attributes.get("tick_count", category="native_p3"), 1)
        self.assertEqual(pending["status"], "planned")
        self.assertEqual(pending["intent"], {"operator": "get", "item_id": "10"})
        self.assertEqual(actor.attributes.get("last_outcome", category="native_p3"), None)

    def test_manual_fixture_script_is_persistent_but_has_no_timer(self):
        actor = Thing(9, "Courier")
        actor.attributes = Attrs({
            ("native_p3", "drive_mode"): "manual",
            ("native_p3", "interval_seconds"): 4,
        })
        script = P3AutonomyScript()
        script.obj = actor
        script.key = None
        script.at_script_creation()
        self.assertEqual(script.interval, 0)
        self.assertTrue(script.persistent)

    def test_pending_social_settlement_is_a_separate_real_script_callback(self):
        room = Room(1, "#1")
        actor = Actor(9, room, {
            ("native_p3", "status"): "ACTOR_DELIVERY_SETTLED",
            ("native_p3", "tick_count"): 2,
            ("native_p3", "log"): [],
            ("native_p3", "pending_action"): None,
            ("native_p3", "pending_social"): {"status": "planned", "proposal": {"proposal_id": "p"}},
        })
        script = P3AutonomyScript()
        script.obj = actor
        with patch("tools.native_platform_v0.p3.agency._settle_social_pending") as settle, \
                patch("tools.native_platform_v0.p3.agency.make_decision") as decide:
            script.at_repeat()
        settle.assert_called_once_with(actor, actor.attributes.get("pending_social", category="native_p3"))
        decide.assert_not_called()

    def test_social_outcome_does_not_create_courier_delivery_receipt(self):
        local = view()
        local["observation"]["social_result"] = {"status": "SETTLED", "action_name": "writeLoveNoteReject"}
        self.assertEqual(choose_goal(local)["status"], "ACTIVE")

    def test_goal_state_distinguishes_external_visibility_from_actor_receipt(self):
        external = view()
        external["observation"]["delivered"] = True
        self.assertEqual(choose_goal(external)["status"], "WORLD_GOAL_SATISFIED_EXTERNAL")
        own = view()
        own["observation"]["own_delivery_receipts"] = [
            {"kind": "drop", "settled": True, "item_id": 10, "after_item_room_id": 2}
        ]
        self.assertEqual(choose_goal(own)["status"], "ACTOR_DELIVERY_SETTLED")


if __name__ == "__main__":
    unittest.main()
