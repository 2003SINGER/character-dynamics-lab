import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.native_platform_v0.p5.ongoing_station.audit import (
    _published_controller_tasks, audit_actor_deferral, audit_author_pair,
    audit_resource_negative, audit_t1,
)
from tools.native_platform_v0.p5.ongoing_station.model import load_profile
from tools.native_platform_v0.p5.ongoing_station.replay import build_replay, write_replay_once
from tools.native_platform_v0.p5.ongoing_station.runner import (
    SUITE_PATH, _allocate_run_dir, _compact_step, load_case, run_case,
)


class OngoingStationRunnerTests(unittest.TestCase):
    def test_t1_is_author_null_and_fixed_seed_horizon(self):
        suite, case = load_case("t1-no-author-autonomy", SUITE_PATH)
        self.assertIsNone(suite["common"]["ongoing_station"]["author"])
        self.assertEqual((suite["common"]["seed"], suite["common"]["horizon"]),
                         (20261013, 24))
        self.assertFalse(case["expected"]["npc_commands_from_runner"])
        self.assertFalse(case["expected"]["external_actor_observation"])
        self.assertEqual(set(suite["acceptance_contract"]),
                         {"T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8", "hold_until"})
        self.assertFalse(suite["future_matched_pair_contract"]["not_yet_runnable"])
        self.assertEqual(suite["run_policy"]["max_scenes"], 5)
        profile = load_profile(suite["common"]["ongoing_station"])
        self.assertIsNone(profile.author)
        bundle_path = SUITE_PATH.parent / suite["common"]["bundle"]
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        from tools.native_platform_v0.p5.story_process.model import story_event_registry
        from tools.native_platform_v0.p5.bundle import load_bundle
        self.assertEqual(load_bundle(bundle, registry=story_event_registry()).goals, ())

    def test_matched_author_pair_has_one_strategy_treatment_and_valid_fixed_envelope(self):
        suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
        cases = {row["case_id"]: row for row in suite["cases"]}
        left = cases["t2-t7-author-gtpyhop"]
        right = cases["t2-t7-author-event-driven"]
        self.assertEqual(left["author_file"], right["author_file"])
        self.assertEqual(left["interventions"], right["interventions"])
        self.assertEqual(left["expected"] | {"strategy": None},
                         right["expected"] | {"strategy": None})
        author = json.loads((SUITE_PATH.parent / left["author_file"]).read_text(encoding="utf-8"))
        edited = json.loads((SUITE_PATH.parent / left["edit_author_file"]).read_text(encoding="utf-8"))
        profile = {**suite["common"]["ongoing_station"], "author": author}
        loaded = load_profile(profile)
        self.assertEqual(loaded.author, author)
        from tools.native_platform_v0.p5.ongoing_station.model import compile_projection
        projection = compile_projection(loaded)
        self.assertEqual({row["constraint_id"] for row in projection.constraints},
                         {"archive-note-by-horizon", "respond-before-archive"})
        initial_bindings = {row["constraint_id"]: row for row in author["bindings"]}
        edited_bindings = {row["constraint_id"]: row for row in edited["bindings"]}
        self.assertEqual(initial_bindings["archive-note-by-horizon"]["control"], {
            "mode": "result_only", "file_actor": "B",
            "allowed_methods": ["file_by_B", "return_then_file_by_A"],
            "source": "SYSTEM"})
        self.assertEqual(edited_bindings["archive-note-by-horizon"]["control"]["file_actor"], "A")
        self.assertEqual(initial_bindings["respond-before-archive"]["control"], {
            "mode": "locked_fragment", "file_actor": None,
            "allowed_methods": ["return_then_file_by_A"], "source": "SYSTEM"})
        self.assertEqual(initial_bindings["respond-before-archive"]["locked_fragment"],
                         edited_bindings["respond-before-archive"]["locked_fragment"])
        self.assertEqual(author["bundle"]["constraints"], edited["bundle"]["constraints"])
        self.assertEqual(edited["bundle"]["version"], 2)
        self.assertEqual(author["bundle"]["bundle_id"], edited["bundle"]["bundle_id"])
        t4 = next(row for row in suite["cases"] if row["case_id"] == "t4-live-actor-deferral")
        t6 = next(row for row in suite["cases"] if row["case_id"] == "t6-player-holds-courier-supply")
        self.assertEqual([row["at"] for row in t4["interventions"]], [5, 8])
        self.assertEqual(t4["edit_author_file"], "author-t4-result-only-v2.json")
        t4_v1 = json.loads((SUITE_PATH.parent / t4["author_file"]).read_text(encoding="utf-8"))
        t4_v2 = json.loads((SUITE_PATH.parent / t4["edit_author_file"]).read_text(encoding="utf-8"))
        t4_binding_v1 = next(row for row in t4_v1["bindings"]
                             if row["constraint_id"] == "archive-note-by-horizon")
        t4_binding_v2 = next(row for row in t4_v2["bindings"]
                             if row["constraint_id"] == "archive-note-by-horizon")
        self.assertEqual(t4_binding_v1["control"]["file_actor"], "A")
        self.assertEqual(t4_binding_v2["control"]["file_actor"], "B")
        self.assertEqual(t4_v1["bundle"]["constraints"], t4_v2["bundle"]["constraints"])
        self.assertEqual(t6["interventions"], [
            {"at": 1, "kind": "player_command", "operation": "get",
             "item_alias": "courier_supply"}])
        self.assertEqual(t4["audit"], "actor_deferral")
        self.assertEqual(t6["audit"], "resource_negative")

    def test_run_requires_explicit_execute_and_does_not_contact_rpc(self):
        calls = []
        with self.assertRaises(PermissionError):
            run_case("t1-no-author-autonomy", call_rpc=lambda *args: calls.append(args))
        self.assertEqual(calls, [])

    def test_mixed_author_audit_does_not_claim_lock_selection_for_conflicting_result(self):
        suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
        author = json.loads((SUITE_PATH.parent / "author-pair-v1.json").read_text(encoding="utf-8"))
        decision = {"status": "LOCKED_CONSTRAINT_CONFLICT",
                    "selected_method": None,
                    "decomposition": [{"source_method_id": "file_by_B", "request_id": "result-v1"}],
                    "attempted_methods": [{"method_id": "file_by_B", "feasible": True}],
                    "combined_locked_core": {"constraint_id": "respond-before-archive",
                        "required_method": "return_then_file_by_A",
                        "compatible_method_feasible": False}}
        trace = {"scene_id": "scene1", "ledger": [], "ongoing_station": {
            "controller_decisions": [{"source_version": 1,
                "constraint_id": "archive-note-by-horizon", "decision": decision}]}}
        result = audit_author_pair(trace, {"rooms": {}, "actors": {}}, {}, author,
                                  edit_author=author, activation_minute=5)
        self.assertTrue(result["criteria"]["v1_method_search_and_locked_conflict"])
        self.assertEqual(result["v1_controller_decision_source_path"],
                         "ongoing_station.controller_decisions[0]")
        decision["selected_method"] = "locked_fragment"
        result = audit_author_pair(trace, {"rooms": {}, "actors": {}}, {}, author,
                                  edit_author=author, activation_minute=5)
        self.assertFalse(result["criteria"]["v1_method_search_and_locked_conflict"])

    def test_controller_published_task_audit_uses_exact_persisted_request_ids(self):
        rows = [{"source_version": 2, "constraint_id": "respond-before-archive",
            "minute": 8, "offer_ids": ["locked-v2-1"],
            "decision": {"guards": {"absolute_deadline_minute": 24},
                "decomposition": [
                    {"request_id": "locked-v2-0", "task_kind": "handover_note",
                     "source_method_id": "locked_fragment"},
                    {"request_id": "locked-v2-1", "task_kind": "archive_note",
                     "source_method_id": "locked_fragment"}]}}]
        published = _published_controller_tasks(rows)
        self.assertEqual([row["offer_id"] for row in published], ["locked-v2-1"])
        self.assertEqual(published[0]["task_kind"], "archive_note")
        self.assertEqual(published[0]["constraint_id"], "respond-before-archive")
        self.assertEqual(published[0]["deadline_minute"], 24)
        rows[0]["offer_ids"] = []
        self.assertEqual(_published_controller_tasks(rows), [])

    def test_actor_deferral_audit_requires_real_offer_and_named_live_commitment(self):
        import hashlib
        offer = {"offer_id": "req-1", "constraint_id": "archive-note-by-horizon",
                 "deadline_minute": 24, "actor_alias": "B", "task_kind": "handover_note",
                 "source_method_id": "return_then_file_by_A"}
        blocker = {"commitment_id": "route-A", "source": "SELF", "task_kind": "routine_route",
                   "status": "SETTLED", "route_waypoints": [2, 1]}
        suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
        t4 = next(row for row in suite["cases"] if row["case_id"] == "t4-live-actor-deferral")
        author = json.loads((SUITE_PATH.parent / t4["author_file"]).read_text(encoding="utf-8"))
        edited = json.loads((SUITE_PATH.parent / t4["edit_author_file"]).read_text(encoding="utf-8"))
        digest = hashlib.sha256(json.dumps(edited, sort_keys=True, ensure_ascii=False,
            separators=(",", ":")).encode()).hexdigest()
        trace = {"scene_id": "scene1", "ongoing_station": {
            "author_status": "ACTIVE", "active_author_version": 2,
            "active_author_sha256": digest,
            "activation_events": [{"minute": 5, "typed_args": {"result": {"status": "ACTIVATED"}}}],
            "controller_decisions": [{"source_version": 1,
                "constraint_id": "archive-note-by-horizon", "offer_ids": ["req-1"],
                "decision": {"selected_method": "return_then_file_by_A",
                             "decomposition": [{"request_id": "req-1", **offer}]}},
                {"source_version": 2, "constraint_id": "archive-note-by-horizon",
                 "decision": {"search_selected_method": "file_by_B"}}],
            "stale_offer_ids": [],
            "actor_goal_history": {"B": [
                {"minute": 6, "event": "AUTHOR_OFFER_DEFERRED",
                 "offer_id": "req-1", "blocking_commitment_id": "route-A",
                 "blocking_commitment_status": "IN_PROGRESS", "blocking_task_kind": "routine_route"},
                {"minute": 8, "event": "COMMITMENT_CANCELLED_STALE",
                 "commitment_id": "old-B", "source_offer_id": "req-1"}]},
            "commitments": [blocker, {"commitment_id": "old-B", "source": "AUTHOR",
                "source_method_id": "return_then_file_by_A", "task_kind": "handover_note",
                "actor_alias": "B",
                "source_offer_id": "req-1", "status": "CANCELLED_STALE"}],
            "actor_goal_decisions": [{"minute": 5,
                "commitment": {"source": "SELF", "task_kind": "routine_route"}}]}}
        trace["ledger"] = [{"event_type": "P5_INTERVENTION", "minute": 8,
            "typed_args": {"kind": "ongoing_station_author_edit", "settlement": {
                "status": "UPDATED", "version": 2, "source_sha256": digest,
                "invalidated_offer_ids": ["req-1"]}}}]
        scene = {"rooms": {"origin": 1}, "actors": {"A": {"id": 10}, "B": {"id": 20}}}
        db = {"scenes": [{"scene_id": "scene1", "objects": [
            {"id": 1, "attributes": {"native_p5": {"p5_ongoing_station_author": edited}}},
            {"id": 20,
            "attributes": {"native_p3": {"native_receipts": [{"kind": "move",
                "settled": True, "sim_minute": 6, "receipt_id": "m6",
                "ongoing_commitment_id": "route-A"}]}}}]}]}
        audit = audit_actor_deferral(trace, scene, db, expected_author=author,
            edit_author=edited, activation_minute=5, edit_minute=8)
        self.assertTrue(audit["pass"], json.dumps(audit, sort_keys=True))
        trace["ongoing_station"]["actor_goal_history"]["B"].clear()
        audit = audit_actor_deferral(trace, scene, db, expected_author=author,
            edit_author=edited, activation_minute=5, edit_minute=8)
        self.assertFalse(audit["pass"])

    def test_resource_negative_audit_requires_player_location_and_two_route_receipts(self):
        trace = {"scene_id": "scene1", "ledger": [{"event_type": "P5_INTERVENTION", "minute": 1,
            "typed_args": {"kind": "player_native_command", "command_receipt": {
                "actor_alias": "player", "operation": "get", "item_id": 40,
                "settled": True, "provenance": "native_player_command",
                "after_inventory_ids": [40]}}}], "ongoing_station": {"commitments": [
            {"actor_id": 20, "source": "SELF", "task_kind": "routine_route",
             "commitment_id": "route-B", "status": "SETTLED",
             "route_waypoints": [2, 1],
             "waypoint_receipts": ["b-move-1", "b-move-2"]}]}}
        scene = {"scene_id": "scene1", "actors": {"A": {"id": 10}, "B": {"id": 20}}}
        db = {"scenes": [{"scene_id": "scene1", "objects": [
            {"id": 30, "attributes": {"native_p3": {"p3_control_role": "player"}}},
            {"id": 40, "location": {"id": 30}, "attributes": {"native_p5": {
                "p5_item_alias": "courier_supply"}}},
            {"id": 10, "attributes": {"native_p3": {"task_item_id": 40,
                "native_receipts": []}, "native_p5": {"p5_task_item_alias": "courier_supply"}}},
            {"id": 20, "attributes": {"native_p3": {"native_receipts": [
                {"receipt_id": "b-move-1", "settled": True, "kind": "move", "sim_minute": 6,
                 "ongoing_commitment_id": "route-B", "after_room_id": 2},
                {"receipt_id": "b-move-2", "settled": True, "kind": "move", "sim_minute": 7,
                 "ongoing_commitment_id": "route-B", "after_room_id": 1}]}}},
        ]}]}
        intervention = {"at": 1, "kind": "player_command", "operation": "get",
                        "item_alias": "courier_supply"}
        audit = audit_resource_negative(trace, scene, db, expected_intervention=intervention)
        self.assertTrue(audit["pass"], json.dumps(audit, sort_keys=True))
        db["scenes"][0]["objects"][1]["location"]["id"] = 99
        self.assertFalse(audit_resource_negative(trace, scene, db,
            expected_intervention=intervention)["pass"])

    def test_run_directories_are_non_overwriting_and_publication_compatible(self):
        created = set()
        token = iter(("abc111", "def222"))

        def mkdir(path, mode=0o777, parents=False, exist_ok=False):
            key = str(path)
            if key in created and not exist_ok:
                raise FileExistsError(key)
            created.add(key)

        with patch("pathlib.Path.mkdir", autospec=True, side_effect=mkdir), \
                patch("secrets.token_hex", side_effect=lambda _n: next(token)):
            root = Path("/virtual/runs")
            first = _allocate_run_dir(root, "t1-no-author-autonomy")
            second = _allocate_run_dir(root, "t1-no-author-autonomy")
        self.assertNotEqual(first, second)
        self.assertTrue(first.name.startswith("story-"))

    def test_step_capture_keeps_one_delta_and_rejects_cumulative_shape(self):
        step = {"scene_id": "scene1", "rounds": [{"minute": 1, "actor_steps": [],
                "ongoing_station": {"decisions": []}, "final": {"huge": "trace"}}],
                "final": {"huge": "trace"}}
        compact = _compact_step(step)
        self.assertEqual(compact["round"]["minute"], 1)
        self.assertNotIn("final", compact["round"])
        self.assertEqual(compact["omitted_cumulative_fields"], ["final"])
        with self.assertRaises(RuntimeError):
            _compact_step({"rounds": [{"minute": 1}, {"minute": 2}]})

    def test_t1_audit_uses_exact_scene_database_export_and_post_selection_receipt(self):
        trace = {
            "scene_id": "scene1",
            "ongoing_station": {
                "activation_events": [],
                "actor_goal_decisions": [
                    {"actor_id": 10, "minute": 1, "commitment": {
                        "commitment_id": "self-a", "source": "SELF", "goal_id": "deliver"}},
                    {"actor_id": 10, "minute": 5, "commitment": {
                        "commitment_id": "route-a", "source": "SELF", "goal_id": "routine"}},
                ],
                "commitments": [
                    {"actor_id": 10, "commitment_id": "self-a", "source": "SELF",
                     "goal_id": "deliver", "status": "SETTLED", "updated_minute": 4,
                     "receipt_ids": ["r1"]},
                    {"actor_id": 10, "commitment_id": "route-a", "source": "SELF",
                     "goal_id": "routine", "status": "SETTLED", "updated_minute": 6,
                     "receipt_ids": ["r2"]},
                ],
            },
        }
        scene = {"scene_id": "scene1", "rooms": {"origin": 1},
                 "actors": {"A": {"id": 10}, "B": {"id": 20}}}
        db = {"schema": "native-p3-db-evidence-v1", "scenes": [{"scene_id": "scene1", "objects": [
            {"id": 1, "attributes": {"native_p5": {
                "p5_ongoing_station_profile": {"author": None},
                "p5_ongoing_station_meta": {"author_status": "ABSENT"}}}},
            {"id": 10, "attributes": {"native_p3": {"native_receipts": [
                {"receipt_id": "r1", "settled": True, "ongoing_commitment_id": "self-a"},
                {"receipt_id": "r2", "settled": True, "ongoing_commitment_id": "route-a"}]}}},
            {"id": 20, "attributes": {"native_p3": {"native_receipts": [
                {"receipt_id": "r3", "settled": True, "ongoing_commitment_id": "self-b"}]}}},
        ]}]}
        # A valid actor B record must independently contain both a first and a later
        # distinct settled goal; add the same verified shape for the second role.
        trace["ongoing_station"]["actor_goal_decisions"] += [
            {"actor_id": 20, "minute": 1, "commitment": {
                "commitment_id": "self-b", "source": "SELF", "goal_id": "deliver-b"}},
            {"actor_id": 20, "minute": 8, "commitment": {
                "commitment_id": "route-b", "source": "SELF", "goal_id": "routine-b"}},
        ]
        trace["ongoing_station"]["commitments"] += [
            {"actor_id": 20, "commitment_id": "self-b", "source": "SELF",
             "goal_id": "deliver-b", "status": "SETTLED", "updated_minute": 7,
             "receipt_ids": ["r3"]},
            {"actor_id": 20, "commitment_id": "route-b", "source": "SELF",
             "goal_id": "routine-b", "status": "SETTLED", "updated_minute": 9,
             "receipt_ids": ["r4"]},
        ]
        actor_b = next(row for row in db["scenes"][0]["objects"] if row["id"] == 20)
        actor_b["attributes"]["native_p3"]["native_receipts"].append(
            {"receipt_id": "r4", "settled": True, "ongoing_commitment_id": "route-b"})
        actor_a = next(row for row in db["scenes"][0]["objects"] if row["id"] == 10)
        actor_a["attributes"]["native_p5"] = {"ongoing_commitments": [
            row for row in trace["ongoing_station"]["commitments"] if row["actor_id"] == 10]}
        actor_b["attributes"]["native_p5"] = {"ongoing_commitments": [
            row for row in trace["ongoing_station"]["commitments"] if row["actor_id"] == 20]}
        result = audit_t1(trace, scene, db)
        self.assertTrue(result["pass"], json.dumps(result, sort_keys=True))
        actor_b["attributes"]["native_p5"]["ongoing_commitments"].pop()
        self.assertFalse(audit_t1(trace, scene, db)["pass"])
        actor_b["attributes"]["native_p5"]["ongoing_commitments"].append(
            trace["ongoing_station"]["commitments"][-1])
        trace["ongoing_station"]["activation_event_ids"] = ["activation-1"]
        self.assertFalse(audit_t1(trace, scene, db)["pass"])
        trace["ongoing_station"]["activation_event_ids"] = []
        db["scenes"][0]["scene_id"] = "another-scene"
        self.assertFalse(audit_t1(trace, scene, db)["pass"])

    def test_t1_audit_does_not_certify_plan_without_later_physical_receipt(self):
        trace = {"scene_id": "scene1", "ongoing_station": {
            "activation_events": [], "actor_goal_decisions": [
                {"actor_id": 10, "minute": 1, "commitment": {"source": "SELF", "goal_id": "g1"}},
                {"actor_id": 10, "minute": 4, "commitment": {"source": "SELF", "goal_id": "g2"}},
            ], "commitments": [{"actor_id": 10, "source": "SELF", "goal_id": "g1",
                "status": "SETTLED", "updated_minute": 3, "receipt_ids": ["r1"]}]}}
        db = {"scenes": [{"scene_id": "scene1", "objects": [
            {"id": 10, "attributes": {"native_p3": {"native_receipts": [
                {"receipt_id": "r1", "settled": True}]}}}]}]}
        result = audit_t1(trace, {"rooms": {"origin": 1},
                                  "actors": {"A": {"id": 10}}}, db)
        self.assertFalse(result["pass"])
        self.assertFalse(result["actors"]["A"]["later_distinct_self_goal_selected_and_dispatched_or_pending"])

    def test_replay_is_chronological_and_keeps_source_ids(self):
        trace = {"scene_id": "scene1", "run_status": "COMPLETE", "complete_through": 24,
                 "ledger": [{"minute": 4, "event_id": "e4", "event_type": "P3_RECEIPT"},
                            {"minute": 3, "event_id": "cb3", "event_type": "P5_NPC_CALLBACK",
                             "typed_args": {"actor_alias": "A"}},
                            {"minute": 2, "event_id": "e2", "event_type": "P3_INTENT"}],
                 "ongoing_station": {"actor_goal_decisions": [
                     {"minute": 3, "actor_alias": "A", "decision_id": "d3",
                      "commitment": {"source": "SELF", "goal_id": "g1",
                                     "commitment_id": "route-a", "task_kind": "routine_route",
                                     "route_waypoints": [2, 1],
                                     "waypoint_receipts": ["r1", None]},
                      "disposition": "IN_PROGRESS", "rationale": "local route"}]}}
        replay = build_replay(trace)
        self.assertLess(replay.index("Minute 2"), replay.index("Minute 3"))
        self.assertLess(replay.index("Minute 3"), replay.index("Minute 4"))
        self.assertIn("e2", replay)
        self.assertIn("d3", replay)
        self.assertIn("waypoint_receipts=`['r1', None]`", replay)
        self.assertIn("callback_event=`cb3`", replay)
        self.assertIn("not a claim of total ordering", replay)

    def test_replay_falls_back_to_actor_logs_and_native_receipts(self):
        trace = {"scene_id": "scene1", "ledger": [], "actor_evidence": [{
            "actor_alias": "A", "actor_id": 10,
            "log": [{"kind": "ongoing_station_decision", "actor_id": 10,
                     "minute": 2, "decision_id": "d2", "commitment": {
                         "source": "SELF", "goal_id": "route", "task_kind": "routine_route"},
                     "intent": {"operator": "move"}, "disposition": "IN_PROGRESS",
                     "rationale": "route selected"}],
            "native_receipts": [{"receipt_id": "r3", "sim_minute": 3,
                                 "settled": True, "kind": "move",
                                 "ongoing_commitment_id": "self-route"}],
        }]}
        replay = build_replay(trace)
        self.assertLess(replay.index("Minute 2"), replay.index("Minute 3"))
        self.assertIn("d2", replay)
        self.assertIn("r3", replay)
        self.assertIn("NPC `A`", replay)

    def test_text_artifact_writer_preserves_markdown_and_is_exclusive(self):
        temp_root = Path(__file__).resolve().parents[4]
        with tempfile.TemporaryDirectory(dir=temp_root) as temp:
            path = Path(temp) / "readable-replay.md"
            trace = {"scene_id": "scene1", "ledger": [], "actor_evidence": []}
            write_replay_once(path, trace)
            markdown = path.read_text(encoding="utf-8")
            self.assertEqual(path.read_text(encoding="utf-8"), markdown)
            self.assertTrue(markdown.startswith("# Ongoing Station"))
            self.assertFalse(markdown.startswith('"# Ongoing Station'))
            with self.assertRaises(FileExistsError):
                write_replay_once(path, trace)

    def test_replay_keeps_ledger_sequence_and_moves_boilerplate_to_appendix(self):
        trace = {"scene_id": "s", "ledger": [
            {"minute": 1, "sequence": 3, "event_id": "callback", "event_type": "P5_NPC_CALLBACK"},
            {"minute": 1, "sequence": 1, "event_id": "time", "event_type": "TIME_ADVANCED"},
            {"minute": 1, "sequence": 2, "event_id": "story", "event_type": "P5_NOTE_CREATED"}],
            "actor_evidence": []}
        replay = build_replay(trace)
        self.assertLess(replay.index("`story`"), replay.index("`callback`"))
        self.assertIn("`TIME_ADVANCED`", replay)
        body, appendix = replay.split("## Complete sealed-ledger index", 1)
        self.assertNotIn("TIME_ADVANCED", body)
        self.assertIn("callback", appendix)


if __name__ == "__main__":
    unittest.main()
