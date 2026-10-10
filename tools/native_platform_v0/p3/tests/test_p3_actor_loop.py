import unittest
from collections import UserDict, UserList
from unittest.mock import patch

from tools.native_platform_v0.p3.agency import (P3AutonomyScript, _settle_pending,
                                                choose_goal, observe_actor)
from tools.native_platform_v0.p3.planning import freeze, plan_next, thaw


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
