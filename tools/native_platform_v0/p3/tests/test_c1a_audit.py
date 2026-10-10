import unittest

from tools.native_platform_v0.p3.c1a_audit import audit_db, audit_trace


def goal(choice, room, status):
    return {"kind": "goal_choice", "choice": choice,
            "activity_profile": {"profile": "delivery_patrol_recovery_v0"},
            "goal": {"delivery_status": status, "delivery_reason": "local evidence"},
            "view": {"observation": {
                "room_id": room, "visible_items": [{"id": 12, "key": "Supply"}] if room == 1 else [],
                "item_held": False, "item_location": 1 if room == 1 else None,
                "task_item": {"id": 12, "key": "Supply"}},
                "goal_contract": {"item_id": 12, "destination_id": 2}},
            "planner": {"implementation": "gtpyhop-core-2.0.2",
                        "intent": {"operator": "get"}}}


class C1aAuditTests(unittest.TestCase):
    def blocked_fixture(self, *, dispatch_succeeded=True):
        initial = goal("deliver_supply", 1, "ACTIVE")
        failure = {"kind": "execution_settlement", "status": "WORLD_VALIDATION_REJECTED",
                   "receipt": {"kind": "get", "item_id": 12, "submitted_command": "get Supply",
                               "dispatch_succeeded": dispatch_succeeded, "settled": False}}
        suspended = goal("patrol", 1, "SUSPENDED_LOCAL_ITEM_UNAVAILABLE")
        actor = {"id": 21, "location_id": 2, "attributes": {
            "p3_control_role": "courier", "activity_profile": "delivery_patrol_recovery_v0",
            "delivery_task": True, "goal": "deliver_supply", "task_item_id": 12,
            "task_destination_id": 2, "native_receipts": [
                {"kind": "move", "goal": "patrol", "settled": True}],
            "log": [initial, failure, suspended]}}
        callbacks = [{"kind": "npc_callback", "callback_index": i,
                      "callback": {"role": "courier"}} for i in range(1, 13)]
        intervention = {"kind": "player_intervention", "label": "player_steals_assigned_supply",
                        "command_receipt": {"operation": "get", "intervention_kind": "native-player-command",
                                            "settled": True, "item_id": 12}}
        response = {"schema": "native-p3-c1a-run-v1", "scenario": "C1a-blocked-switch",
                    "activity_profile": "delivery_patrol_recovery_v0",
                    "controller_authored_npc_commands": 0,
                    "completion_scope": "bounded_callbacks_only_not_semantic_acceptance",
                    "callback_count": 12, "created_scene": {"rooms": {"pickup": {"id": 1}}},
                    "timeline": callbacks + [intervention],
                    "trace": {"scene_id": "scene-c1a", "objects": [actor]}}
        return response

    def test_blocked_case_requires_real_world_rejection_of_submitted_native_get(self):
        self.assertTrue(audit_trace(self.blocked_fixture(), "C1a-blocked-switch")
                        ["stale_native_get_rejected"])

    def test_blocked_case_rejects_pre_dispatch_shortcut(self):
        with self.assertRaisesRegex(ValueError, "rejected by Evennia"):
            audit_trace(self.blocked_fixture(dispatch_succeeded=False), "C1a-blocked-switch")

    def resumed_fixture(self):
        initial = goal("deliver_supply", 1, "ACTIVE")
        failure = {"kind": "execution_settlement", "status": "WORLD_VALIDATION_REJECTED",
                   "receipt": {"kind": "get", "item_id": 12, "submitted_command": "get Supply",
                               "dispatch_succeeded": True, "settled": False}}
        unavailable = goal("patrol", 2, "SUSPENDED_LOCAL_ITEM_UNAVAILABLE")
        newly_visible = goal("deliver_supply", 1, "ACTIVE")
        patrol_move = {"receipt_id": "patrol-1", "kind": "move", "goal": "patrol",
                       "settled": True}
        delivery = [
            {"receipt_id": "get-1", "kind": "get", "goal": "deliver_supply",
             "settled": True, "dispatch_succeeded": True},
            {"receipt_id": "move-1", "kind": "move", "goal": "deliver_supply",
             "settled": True, "dispatch_succeeded": True},
            {"receipt_id": "drop-1", "kind": "drop", "goal": "deliver_supply",
             "item_id": 12, "after_item_room_id": 2, "settled": True,
             "dispatch_succeeded": True},
        ]
        actor_attrs = {"p3_control_role": "courier",
                       "activity_profile": "delivery_patrol_recovery_v0", "delivery_task": True,
                       "goal": "deliver_supply", "task_item_id": 12, "task_item_key": "Supply",
                       "task_item_dbref": "#12", "task_destination_id": 2,
                       "task_destination_dbref": "#2",
                       "native_receipts": [patrol_move] + delivery,
                       "log": [initial, failure, unavailable, newly_visible],
                       "p3_scene_id": "scene-c1a"}
        callback_rows = []
        for index in range(1, 17):
            events = [unavailable] if index == 5 else []
            callback_rows.append({"kind": "npc_callback", "callback_index": index,
                                  "callback": {"role": "courier"}, "new_log_events": events})
        intervention_rows = [
            {"kind": "player_intervention", "label": "player_steals_assigned_supply",
             "command_receipt": {"operation": "get", "intervention_kind": "native-player-command",
                                 "settled": True, "item_id": 12}},
            {"kind": "player_intervention", "label": "player_returns_supply_to_original_room",
             "command_receipt": {"operation": "drop", "intervention_kind": "native-player-command",
                                 "settled": True, "item_id": 12, "item_location_id": 1}},
        ]
        neg_view = {"room_id": 2, "visible_items": [], "item_held": False, "item_location": None}
        negative = {"kind": "away_room_negative_observation",
                    "observation": {"local_observation": {"observation": neg_view}},
                    "snapshot": {"actor": {"room_id": 2}}}
        response = {"schema": "native-p3-c1a-run-v1", "scenario": "C1a-observed-resume",
                    "activity_profile": "delivery_patrol_recovery_v0",
                    "controller_authored_npc_commands": 0,
                    "completion_scope": "bounded_callbacks_only_not_semantic_acceptance",
                    "callback_count": 16, "created_scene": {"rooms": {"pickup": {"id": 1}}},
                    "timeline": [*callback_rows, *intervention_rows, negative],
                    "trace": {"scene_id": "scene-c1a",
                              "objects": [{"id": 21, "location_id": 2, "attributes": actor_attrs}]}}
        return response

    def test_resume_requires_post_negative_control_visibility(self):
        response = self.resumed_fixture()
        summary = audit_trace(response, "C1a-observed-resume")
        self.assertTrue(summary["resume_after_local_visibility"])

    def test_resume_cannot_reuse_initial_visibility_or_hide_new_item(self):
        response = self.resumed_fixture()
        actor = response["trace"]["objects"][0]["attributes"]
        # Move the only active/visible candidate ahead of the negative-control choice.
        resume = actor["log"].pop()
        actor["log"].insert(2, resume)
        with self.assertRaisesRegex(ValueError, "subsequent visible"):
            audit_trace(response, "C1a-observed-resume")

        response = self.resumed_fixture()
        actor = response["trace"]["objects"][0]["attributes"]
        actor["log"][-1]["view"]["observation"]["visible_items"] = []
        with self.assertRaisesRegex(ValueError, "subsequent visible"):
            audit_trace(response, "C1a-observed-resume")

    def test_missing_failure_and_changed_task_contract_are_rejected(self):
        response = self.resumed_fixture()
        actor = response["trace"]["objects"][0]["attributes"]
        actor["log"] = [event for event in actor["log"] if event.get("kind") != "execution_settlement"]
        with self.assertRaisesRegex(ValueError, "failed stale native get"):
            audit_trace(response, "C1a-observed-resume")

        response = self.resumed_fixture()
        actor = response["trace"]["objects"][0]["attributes"]
        actor["task_item_id"] = 99
        with self.assertRaisesRegex(ValueError, "changed the authored"):
            audit_trace(response, "C1a-observed-resume")

    def test_db_readback_must_preserve_task_and_full_log(self):
        response = self.resumed_fixture()
        summary = audit_trace(response, "C1a-observed-resume")
        actor = response["trace"]["objects"][0]
        actor_attrs = actor["attributes"]
        db_actor = {"id": actor["id"], "location": {"id": 2},
                    "attributes": {"native_p3": dict(actor_attrs)}}
        rows = [
            {"id": 1, "attributes": {"native_p3": {"p3_scene_id": "scene-c1a"}},
             "location": None},
            {"id": 2, "attributes": {"native_p3": {"p3_scene_id": "scene-c1a"}},
             "location": None},
            db_actor,
            {"id": 12, "location": {"id": 2},
             "attributes": {"native_p3": {"p3_scene_id": "scene-c1a"}}},
            {"id": 22, "location": {"id": 1},
             "attributes": {"native_p3": {"p3_scene_id": "scene-c1a",
                                            "p3_control_role": "player"}}},
        ]
        db_doc = {"schema": "native-p3-db-evidence-v1",
                  "source": "initialized Evennia Django ORM; SQLite query_only enabled",
                  "selection": {"scene_ids": ["scene-c1a"]},
                  "scenes": [{"scene_id": "scene-c1a", "objects": rows}]}
        self.assertEqual(audit_db(db_doc, response, summary), 5)
        rows[2]["attributes"]["native_p3"]["log"] = []
        with self.assertRaisesRegex(ValueError, "log"):
            audit_db(db_doc, response, summary)


if __name__ == "__main__":
    unittest.main()
