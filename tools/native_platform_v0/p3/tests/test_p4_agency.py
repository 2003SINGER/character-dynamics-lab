import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from tools.native_platform_v0.p3.agency import P3AutonomyScript, _dispatch_pending, observe_actor
from tools.native_platform_v0.p3.p4_agency import choose_goal, make_decision, step_actor
from tools.native_platform_v0.p3.planning import plan_next


class Attrs:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def get(self, key, category=None, default=None):
        return self.values.get((category, key), default)

    def add(self, key, value, category=None):
        self.values[(category, key)] = value


class Room:
    def __init__(self, ident):
        self.id = ident
        self.dbref = f"#{ident}"
        self.contents = []
        self.exits = []


class Exit:
    def __init__(self, key, source, destination, traversable):
        self.id = destination.id + 100
        self.dbref = f"#{self.id}"
        self.key = key
        self.location = source
        self.destination = destination
        self.traversable = traversable

    def access(self, actor, access_type, default=False):
        return self.traversable if access_type == "traverse" else True


class Thing:
    def __init__(self, ident, key, location=None, visible=True):
        self.id = ident
        self.dbref = f"#{ident}"
        self.key = key
        self.location = location
        self.contents = []
        self.visible = visible

    def access(self, actor, access_type, default=False):
        return self.visible


class Actor(Thing):
    def __init__(self, ident, role, location, attrs=None):
        super().__init__(ident, role, location)
        self.attributes = Attrs(attrs)
        self.ndb = SimpleNamespace(p3_pending_operation_id=None)
        location.contents.append(self)
        self.commands = []

    def execute_cmd(self, command):
        self.commands.append(command)


def local_view(*, item_location=1, held=False, visible=True, traversable=True, receipt=False):
    receipts = ([{"kind": "drop", "settled": True, "item_id": 10,
                  "after_item_room_id": 2}] if receipt else [])
    visible_items = ([{"id": 10, "key": "Parcel", "room_id": 1}] if visible else [])
    return {
        "actor_id": 9,
        "activity_contract": {"profile": "p4_story_v0", "delivery_task": True},
        "goal_contract": {"goal": "deliver_supply", "item_id": 10, "destination_id": 2},
        "observation": {
            "room_id": 1,
            "inventory": ([{"id": 10, "key": "Parcel"}] if held else []),
            "visible_items": visible_items,
            "task_item": {"id": 10, "key": "Parcel"},
            "task_destination": 2,
            "item_location": item_location,
            "item_held": held,
            "delivered": False,
            "own_delivery_receipts": receipts,
            "known_exits": {1: [2], 2: [1]},
            "known_traversability": {1: {2: traversable}, 2: {1: traversable}},
            "exits": [{"key": "east", "destination_id": 2, "traversable": traversable}],
            "witnessed": [],
            "retained_witnesses": [],
        },
    }


class P4AgencyTests(unittest.TestCase):
    def test_goal_suspension_and_resume_are_derived_from_actor_local_item_evidence(self):
        missing = local_view(item_location=None, visible=False)
        self.assertEqual(choose_goal(missing)["delivery_status"], "SUSPENDED_LOCAL_ITEM_UNAVAILABLE")
        self.assertEqual(choose_goal(missing)["choice"], "patrol")

        # A return elsewhere in W is deliberately absent from O and cannot resume the task.
        self.assertEqual(choose_goal(missing)["choice"], "patrol")

        returned_visible = local_view(item_location=1, visible=True)
        self.assertEqual(choose_goal(returned_visible)["choice"], "deliver_supply")
        from tools.native_platform_v0.p3.planning import freeze

        with patch("tools.native_platform_v0.p3.p4_agency.make_decision_view",
                   return_value=freeze(returned_visible)):
            resumed = make_decision(Thing(9, "Hero"))
        self.assertEqual(resumed["planner"]["status"], "SOLVED")
        self.assertEqual(resumed["intent"]["operator"], "get")

    def test_own_settled_drop_receipt_keeps_delivery_complete_and_selects_patrol(self):
        view = local_view(item_location=None, visible=False, receipt=True)
        selected = choose_goal(view)
        self.assertEqual(selected["delivery_status"], "SETTLED")
        self.assertEqual(selected["choice"], "patrol")

    def test_planner_filters_closed_local_door_only_when_requested(self):
        view = local_view(item_location=None, held=True, traversable=False)
        self.assertEqual(plan_next(view, "deliver_supply")["intent"]["operator"], "move")
        filtered = plan_next(view, "deliver_supply", respect_local_traversability=True)
        self.assertEqual(filtered["status"], "NO_PLAN")
        open_door = local_view(item_location=None, held=True, traversable=True)
        resumed = plan_next(open_door, "deliver_supply", respect_local_traversability=True)
        self.assertEqual(resumed["intent"], {"operator": "move", "exit_key": "east", "destination_id": 2})

    def test_observer_records_only_currently_visible_exit_traversability_for_p4(self):
        room, destination = Room(1), Room(2)
        room.exits.append(Exit("east", room, destination, traversable=False))
        actor = Actor(9, "Hero", room, {
            ("native_p3", "activity_profile"): "p4_story_v0",
            ("native_p3", "task_item_id"): 10,
            ("native_p3", "task_destination_id"): 2,
            ("native_p3", "task_item_key"): "Parcel",
            ("native_p3", "goal"): "deliver_supply",
            ("native_p3", "witnessed"): {"edges": {}, "objects": {}},
        })
        observed = observe_actor(actor)
        self.assertEqual(observed["observation"]["exits"][0]["traversable"], False)
        self.assertEqual(observed["observation"]["known_traversability"], {1: {2: False}})
        self.assertIsNone(observed["observation"]["item_location"])

    def test_social_callback_consumption_prevents_other_primitive_dispatch(self):
        actor = Actor(9, "Hero", Room(1), {
            ("native_p3", "activity_profile"): "p4_story_v0",
            ("native_p3", "status"): "RUNNING",
            ("native_p3", "tick_count"): 0,
            ("native_p3", "log"): [],
        })
        social_module = ModuleType("tools.native_platform_v0.p3.p4_social")
        social_module.step_social = lambda who: True
        with patch("tools.native_platform_v0.p3.p4_agency._clock_fields", return_value={"sim_minute": 2, "deadline": 24}), \
                patch.dict("sys.modules", {social_module.__name__: social_module}), \
                patch("tools.native_platform_v0.p3.p4_agency.make_decision") as decide:
            step_actor(actor)
        decide.assert_not_called()
        self.assertEqual(actor.attributes.get("pending_action", category="native_p3"), None)
        log = actor.attributes.get("log", category="native_p3", default=[])
        self.assertTrue(any(row.get("kind") == "p4_social_callback_consumed" for row in log))

    def test_p4_stale_get_reaches_native_local_command_and_settles_as_rejected(self):
        room = Room(1)
        actor = Actor(9, "Hero", room, {
            ("native_p3", "activity_profile"): "p4_story_v0",
            ("native_p3", "tick_count"): 3,
            ("native_p3", "log"): [],
            ("native_p3", "witnessed"): {"edges": {}, "objects": {"10": {
                "room_id": 1, "key": "Parcel", "status": "seen"}}},
        })
        pending = {
            "status": "planned", "operation_id": "p4:9:3",
            "intent": {"operator": "get"},
            "goal": {"choice": "deliver_supply"},
            "view": {
                "activity_contract": {"profile": "p4_story_v0"},
                "goal_contract": {"item_id": 10},
                "observation": {
                    "visible_items": [{"id": 10, "key": "Parcel"}],
                    "task_item": {"id": 10, "key": "Parcel"},
                },
            },
        }
        clock_module = ModuleType("tools.native_platform_v0.p3.p4_world")
        clock_module.clock_for_actor = lambda who: {"now": 5, "deadline": 24, "unit": "simulated-minute"}
        with patch.dict("sys.modules", {clock_module.__name__: clock_module}):
            _dispatch_pending(actor, pending)

        self.assertEqual(actor.commands, ["get Parcel"])
        outcome = actor.attributes.get("last_outcome", category="native_p3")
        self.assertEqual(outcome["status"], "WORLD_VALIDATION_REJECTED")
        self.assertFalse(outcome["receipt"]["settled"])
        self.assertTrue(outcome["receipt"]["dispatch_succeeded"])
        self.assertEqual(outcome["receipt"]["sim_minute"], 5)
        self.assertEqual(outcome["receipt"]["submitted_command"], "get Parcel")

    def test_non_p4_profile_keeps_existing_script_path(self):
        actor = Thing(9, "Courier")
        actor.attributes = Attrs({
            ("native_p3", "activity_profile"): "delivery_patrol_recovery_v0",
            ("native_p3", "status"): "RUNNING",
            ("native_p3", "tick_count"): 0,
            ("native_p3", "log"): [],
        })
        script = P3AutonomyScript()
        script.obj = actor
        with patch("tools.native_platform_v0.p3.agency.make_decision",
                   return_value={"view": {"activity_contract": {"profile": "delivery_patrol_recovery_v0"}},
                                 "goal": {"status": "NO_TASK", "reason": "test", "inputs": {},
                                          "candidates": [], "rule": "test", "choice": None},
                                 "planner": None, "intent": None}), \
                patch("tools.native_platform_v0.p3.p4_agency.step_actor") as p4_step:
            script.at_repeat()
        p4_step.assert_not_called()


if __name__ == "__main__":
    unittest.main()
