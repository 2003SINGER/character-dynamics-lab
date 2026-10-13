"""Regression for actor-local routing to a registered station workbench."""
from copy import deepcopy
import unittest

from tools.native_platform_v0.p3.planning import plan_actor_task


def native_b_view_at_destination():
    """Minute-1 B observation plus its settled east-move frontier.

    IDs and task bindings are from the preserved main-GT native failure. The
    actual move receipt records B (#8503) leaving Pickup (#8498) for #8499;
    the next local view therefore has no visible workbench tool row.
    """
    return {"actor_id": 8503, "observation": {
        "room_id": 8499,
        "inventory": [],
        "visible_items": [{"id": 8503, "room_id": 8499}],
        "known_exits": {8498: [8499, 8507], 8499: [8498]},
        "known_traversability": {8498: {8499: True, 8507: False}},
        "exits": [{"key": "west", "destination_id": 8498, "traversable": True}],
        "station_tools": [],
        "station_supplies": [],
        "station_repair_targets": [],
    }}


class P3StationTaskPlanningTests(unittest.TestCase):
    def test_inspect_and_repair_offbench_plan_only_route_then_require_reobservation(self):
        view = native_b_view_at_destination()
        tasks = [
            {"goal_id": "self-inspect", "task_kind": "inspect_supply", "item_id": 8504,
             "tool_id": 8512, "target_id": 8504, "target_room_id": 8498,
             "storage_destination_id": 8513, "duration_minutes": 2, "deadline_minute": 24},
            {"goal_id": "self-repair", "task_kind": "repair_passage", "tool_id": 8512,
             "target_id": 8508, "target_room_id": 8498,
             "duration_minutes": 3, "deadline_minute": 24},
        ]
        for task in tasks:
            with self.subTest(task_kind=task["task_kind"]):
                result = plan_actor_task(view, task)
                self.assertEqual(result["status"], "CONDITIONAL_ROUTE", result)
                self.assertEqual(result["intent"], {
                    "operator": "move", "exit_key": "west", "destination_id": 8498})
                self.assertEqual(result["plan"], [result["intent"]])
                self.assertTrue(result["conditional_terminal_reobservation"])
                self.assertNotIn("use_tool", repr(result["plan"]))

    def test_missing_workbench_tool_remains_blocked_after_arrival(self):
        view = deepcopy(native_b_view_at_destination())
        view["observation"].update({
            "room_id": 8498,
            "exits": [{"key": "east", "destination_id": 8499, "traversable": True},
                      {"key": "south", "destination_id": 8507, "traversable": False}],
        })
        for task in (
            {"goal_id": "self-inspect", "task_kind": "inspect_supply", "item_id": 8504,
             "tool_id": 8512, "target_id": 8504, "target_room_id": 8498,
             "storage_destination_id": 8513, "duration_minutes": 2, "deadline_minute": 24},
            {"goal_id": "self-repair", "task_kind": "repair_passage", "tool_id": 8512,
             "target_id": 8508, "target_room_id": 8498,
             "duration_minutes": 3, "deadline_minute": 24},
        ):
            with self.subTest(task_kind=task["task_kind"]):
                result = plan_actor_task(view, task)
                self.assertEqual(result["status"], "BLOCKED")
                self.assertEqual(result["reason"], "exact tool is not locally visible or held")
                self.assertIsNone(result["intent"])


if __name__ == "__main__":
    unittest.main()
