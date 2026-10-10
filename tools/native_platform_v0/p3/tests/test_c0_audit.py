import unittest

from tools.native_platform_v0.p3.c0_audit import check_delivery, check_no_delivery


def goal(choice, tick, planner=None):
    return {"kind": "goal_choice", "choice": choice,
            "candidates": [choice], "activity_profile": {"profile": "delivery_patrol_v0"},
            "view": {"observation": {"room_id": 1, "exits": [], "visible_items": []}},
            "planner": planner or {}}


class C0AuditTests(unittest.TestCase):
    def delivery_response(self, *, settled=True, patrol_after=False):
        drop = {"receipt_id": "drop-1", "kind": "drop", "item_id": 10,
                "after_item_room_id": 2, "settled": settled, "dispatch_succeeded": settled}
        log = [goal("deliver_supply", 1, {"implementation": "gtpyhop-core-2.0.2"}),
               {"kind": "execution_settlement", "status": "SETTLED" if settled else "WORLD_VALIDATION_REJECTED",
                "receipt": drop}]
        receipts = [
            {"receipt_id": "get-1", "kind": "get", "item_id": 10, "settled": True,
             "dispatch_succeeded": True},
            {"receipt_id": "move-1", "kind": "move", "item_id": 10, "settled": True,
             "dispatch_succeeded": True, "goal": "deliver_supply", "after_room_id": 2},
            drop,
        ]
        if patrol_after:
            log.append(goal("patrol", 4))
            receipts.append({"receipt_id": "patrol-1", "kind": "move", "settled": True,
                             "dispatch_succeeded": True, "goal": "patrol", "after_room_id": 1})
        actor = {"p3_control_role": "courier", "activity_profile": "delivery_patrol_v0",
                 "delivery_task": True, "task_item_id": 10, "task_destination_id": 2,
                 "native_receipts": receipts, "log": log}
        callback_count = 20 if patrol_after else 12
        return {"scenario": "C0-after-delivery" if patrol_after else "C0-delivery-priority",
                "controller_interventions": 0,
                "callback_limit": callback_count,
                "callbacks": [{"step": {"scene_id": "scene-a"}} for _ in range(callback_count)],
                "trace": {"scene_id": "scene-a", "objects": [{"id": 9, "location_id": 2,
                             "attributes": actor}]}}

    def test_delivery_requires_actual_settled_drop_receipt(self):
        response = self.delivery_response(settled=False)
        with self.assertRaisesRegex(ValueError, "settled native drop"):
            check_delivery(response, after=False)

    def test_delivery_priority_accepts_native_planner_and_matching_drop(self):
        scene_ids, summary = check_delivery(self.delivery_response(), after=False)
        self.assertEqual(scene_ids, ["scene-a"])
        self.assertEqual(summary["settled_drop_receipts"], 1)

    def test_after_delivery_requires_same_run_patrol_selection_and_real_move(self):
        response = self.delivery_response(patrol_after=True)
        scene_ids, summary = check_delivery(response, after=True)
        self.assertEqual(scene_ids, ["scene-a"])
        self.assertEqual(summary["settled_patrol_moves"], 1)
        response["trace"]["objects"][0]["attributes"]["native_receipts"] = [
            receipt for receipt in response["trace"]["objects"][0]["attributes"]["native_receipts"]
            if receipt.get("goal") != "patrol"
        ]
        with self.assertRaisesRegex(ValueError, "no settled patrol movement"):
            check_delivery(response, after=True)

    def test_no_delivery_requires_nonretrying_real_negative_control(self):
        def scene(scene_id, role, *, locked=False):
            move_receipt = {"receipt_id": f"move-{scene_id}", "kind": "move", "goal": "patrol",
                            "settled": not locked, "dispatch_succeeded": not locked,
                            "before_room_id": 1, "after_room_id": 2 if not locked else 1,
                            "submitted_command": "east"}
            log = [goal("patrol", 1),
                   {"kind": "primitive_intent", "pending_action": {"intent": {"operator": "move"}}},
                   {"kind": "execution_settlement", "status": "WORLD_VALIDATION_REJECTED" if locked else "SETTLED",
                    "receipt": move_receipt}]
            attrs = {"p3_control_role": "courier", "task_item_id": None, "task_item_dbref": None,
                     "native_receipts": [] if locked else [move_receipt], "log": log}
            callback_count = 10 if locked else 12
            return {"role": role, "configuration": {"delivery_task": False,
                                                       "patrol_exit_locked": locked},
                    "callbacks": [{} for _ in range(callback_count)],
                    "trace": {"scene_id": scene_id, "objects": [{"id": 1,
                               "location_id": 2 if not locked else 1, "attributes": attrs}]}}

        response = {"scenario": "C0-no-delivery", "controller_interventions": 0,
                    "scenes": [scene("scene-a", "no_delivery_primary"),
                               scene("scene-b", "locked_exit_negative_control", locked=True)]}
        scene_ids, summary = check_no_delivery(response)
        self.assertEqual(scene_ids, ["scene-a", "scene-b"])
        self.assertEqual(summary["locked_exit_move_retries"], 0)
        response["scenes"][1]["trace"]["objects"][0]["attributes"]["log"].append(
            {"kind": "primitive_intent", "pending_action": {"intent": {"operator": "move"}}})
        with self.assertRaisesRegex(ValueError, "retried"):
            check_no_delivery(response)


if __name__ == "__main__":
    unittest.main()
