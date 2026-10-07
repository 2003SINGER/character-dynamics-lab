import json
from pathlib import Path
import tempfile
import unittest

from export_player_timeline import (
    coursework_percentage, export_bundle, export_trace, standalone_html, write_outputs,
)


def run_records(*, policy="utility", case="alarm_active", alarm="silent", action_after=None,
                task_facts=(), world_event_id="alarm-rings", provenance="normal"):
    facts = [
        {"key": "room.alarm", "value": alarm, "status": "known"},
        {"key": "message.unread_count", "value": "0", "status": "known"},
        *task_facts,
    ]
    before = {"action": "study_focused", "target": "desk", "started_at_total_minutes": 525,
              "elapsed_minutes": 0, "planned_minutes": 35, "status": "running"}
    after = action_after or {"action": "study_focused", "target": "desk", "started_at_total_minutes": 525,
                             "elapsed_minutes": 15, "planned_minutes": 35, "status": "running"}
    records = [
        {"kind": "header", "protocol": "npc-continuity-paired-trace-v1", "policy": policy,
         "case": case, "world_seed": 0, "policy_seed": 17, "model_id": "SECRET-MODEL",
         "scenario_setup": {"private_condition": "SECRET-CONDITION"}},
        {"kind": "initial_state", "minute": 525,
         "observation": {"clock_total_minutes": 525, "clock_time": "08:45", "facts": facts},
         "running_action": before,
         "task_world": {"effort_done": 7.7, "private": "SECRET-WORLD"},
         "actor_history": {"episodes": [{"private": "SECRET-HISTORY"}]}},
        {"kind": "boundary", "index": 0,
         "interval": {"from_total_minutes": 525, "at_total_minutes": 540, "elapsed_minutes": 15,
                      "ownership": "interval_before_boundary_then_events_at_at_total_minutes"},
         "policy_evaluated": True, "gate_reasons": ["SECRET-GATE"],
         "running_before": before, "running_after": after,
         "selected_action": "SECRET-SELECTED", "selected_target": "SECRET-TARGET",
         "world_events": [{"id": world_event_id, "description": "SECRET-W-EVENT"}],
         "observation_deltas": [{"key": "room.alarm", "value": alarm, "status": "known",
                                 "source": "SECRET-PROVENANCE"}],
         "observation_facts": facts,
         "selection_input": {"request_json": "SECRET-LLM-INPUT", "candidates": ["SECRET-CANDIDATE"]},
         "policy_provenance": provenance,
         "pre_policy_outcome": {"provenance": "SECRET-OUTCOME"},
         "task_world_after": {"effort_done": 7.7}},
        {"kind": "termination", "reason": "horizon", "minute": 540,
         "policy_calls": 9, "boundaries": 1},
    ]
    return [json.dumps(record) for record in records]


class PlayerTimelineExportTests(unittest.TestCase):
    def test_payload_is_whitelist_only_and_keeps_interval_ownership(self):
        action_after = {"action": "turn_off_alarm", "target": "alarm",
                        "started_at_total_minutes": 540, "elapsed_minutes": 0,
                        "planned_minutes": 1, "status": "running"}
        payload = export_trace(run_records(action_after=action_after), "clip-01")
        self.assertEqual(set(payload), {"clip_id", "frames"})
        initial, boundary = payload["frames"]
        self.assertEqual(initial["running_action"]["action"], "study_focused")
        self.assertEqual(boundary["interval"]["from_minute"], 525)
        self.assertEqual(boundary["interval"]["to_minute"], 540)
        self.assertEqual(boundary["interval"]["running_action"]["action"], "study_focused")
        self.assertEqual(boundary["interval"]["running_action"]["elapsed_end_minutes"], 15)
        self.assertEqual(boundary["running_action"]["action"], "turn_off_alarm")
        encoded = json.dumps(payload, ensure_ascii=False)
        for forbidden in ("SECRET-", "utility", "alarm_active", "policy", "world_seed", "selected_action",
                          "selection_input", "history", "candidate", "provenance", "gate", "task_world"):
            self.assertNotIn(forbidden, encoded)

    def test_condition_policy_and_provenance_identity_do_not_change_same_visible_payload(self):
        common = run_records()
        other_identity = run_records(policy="history-llm", case="quiet_active",
                                     world_event_id="different-private-world-event",
                                     provenance="different-model-provenance")
        self.assertEqual(export_trace(common), export_trace(other_identity))

    def test_unknown_and_hidden_world_events_produce_no_player_cue_or_state(self):
        rows = [json.loads(line) for line in run_records(alarm="ringing")]
        rows[1]["observation"]["facts"] = [{"key": "room.alarm", "value": "SECRET-HIDDEN", "status": "unknown"}]
        rows[2]["world_events"] = [{"id": "SECRET-UNOBSERVED-EVENT", "description": "SECRET"}]
        rows[2]["observation_facts"] = [{"key": "room.alarm", "value": "SECRET-HIDDEN", "status": "unknown"}]
        rows[2]["observation_deltas"] = [
            {"key": "room.alarm", "value": "SECRET-HIDDEN", "status": "unknown"},
            {"key": "secret.hidden_fact", "value": "SECRET", "status": "known"},
        ]
        payload = export_trace([json.dumps(row) for row in rows])
        self.assertEqual(payload["frames"][0]["visible_state"], {})
        self.assertEqual(payload["frames"][1]["visible_state"], {})
        self.assertEqual(payload["frames"][1]["cues"], [])
        self.assertNotIn("SECRET", json.dumps(payload))

    def test_player_cues_come_from_changed_known_o_deltas_not_world_event_labels(self):
        rows = [json.loads(line) for line in run_records(alarm="ringing", world_event_id="private-event-name")]
        rows[1]["observation"]["facts"][0]["value"] = "silent"
        rows[2]["observation_facts"][0]["value"] = "ringing"
        payload = export_trace([json.dumps(row) for row in rows])
        self.assertEqual(payload["frames"][1]["cues"], [{"minute": 540, "text": "闹钟响了。"}])
        self.assertNotIn("private-event-name", json.dumps(payload))

        rows[2]["observation_deltas"] = []
        without_o_delta = export_trace([json.dumps(row) for row in rows])
        self.assertEqual(without_o_delta["frames"][1]["cues"], [])

        rows = [json.loads(line) for line in run_records()]
        rows[2]["observation_facts"].append(
            {"key": "message.unread_count", "value": "1", "status": "known"})
        rows[2]["observation_deltas"].append(
            {"key": "message.unread_count", "value": "1", "status": "known"})
        message_payload = export_trace([json.dumps(row) for row in rows])
        self.assertEqual(message_payload["frames"][1]["cues"][-1],
                         {"minute": 540, "text": "未读消息：1 条。"})

    def test_public_task_progress_requires_known_o_facts(self):
        known = [
            {"key": "task.coursework.status", "value": "active", "status": "known"},
            {"key": "task.coursework.effort", "value": "7.7", "status": "known"},
            {"key": "task.coursework.effort_target", "value": "8.0", "status": "known"},
        ]
        payload = export_trace(run_records(task_facts=known))
        self.assertEqual(payload["frames"][0]["visible_state"]["coursework_progress"], 0.9625)
        stale = [{"key": fact["key"], "value": fact["value"], "status": "stale"} for fact in known]
        hidden_payload = export_trace(run_records(task_facts=stale))
        self.assertNotIn("coursework_progress", hidden_payload["frames"][0]["visible_state"])

    def test_near_complete_active_task_never_renders_as_completed(self):
        percentage = coursework_percentage({
            "coursework_status": "active",
            "coursework_progress": 7.962369 / 8.0,
        })
        self.assertEqual(percentage, 99.5)
        self.assertEqual(coursework_percentage({
            "coursework_status": "active", "coursework_progress": 0.998,
        }), 99.8)
        self.assertEqual(coursework_percentage({
            "coursework_status": "active", "coursework_progress": 0.999999,
        }), 99.9)
        self.assertEqual(coursework_percentage({
            "coursework_status": "active", "coursework_progress": 1.0,
        }), 99.9)
        self.assertEqual(coursework_percentage({
            "coursework_status": "completed", "coursework_progress": 1.0,
        }), 100.0)
        template = Path(__file__).with_name("viewer.html").read_text(encoding="utf-8")
        self.assertIn("Math.floor(state.coursework_progress * 1000) / 10", template)
        self.assertIn("Math.min(99.9", template)
        self.assertIn("Active · 进行中", template)
        self.assertIn("Completed · 已完成", template)

    def test_interval_contract_and_action_names_are_validated(self):
        rows = [json.loads(line) for line in run_records()]
        rows[2]["interval"]["elapsed_minutes"] = 14
        with self.assertRaisesRegex(ValueError, "inconsistent elapsed"):
            export_trace([json.dumps(row) for row in rows])
        rows = [json.loads(line) for line in run_records()]
        rows[2]["running_before"]["action"] = "SECRET-ACTION"
        with self.assertRaisesRegex(ValueError, "known action"):
            export_trace([json.dumps(row) for row in rows])

    def test_default_room_targets_accept_only_real_scene_ids(self):
        targets = ["desk", "computer", "bed", "phone", "door", "light", "alarm", "window"]
        actions = ["study_focused", "study_at_computer", "sleep_at_bed", "use_phone",
                   "get_meal", "turn_light_on", "turn_off_alarm", "open_curtain"]
        for target, action in zip(targets, actions):
            after = {"action": action, "target": target, "started_at_total_minutes": 540,
                     "elapsed_minutes": 0, "planned_minutes": 1, "status": "running"}
            payload = export_trace(run_records(action_after=after))
            self.assertEqual(payload["frames"][1]["running_action"]["target"], target)

    def test_bundle_has_anonymous_clip_selector_without_pair_labels(self):
        payload = export_bundle([
            ("clip-a1", run_records(policy="utility", case="alarm_active")),
            ("clip-b2", run_records(policy="history-llm", case="near_completion_alarm")),
        ])
        self.assertEqual([clip["clip_id"] for clip in payload["clips"]], ["clip-a1", "clip-b2"])
        encoded = json.dumps(payload)
        for forbidden in ("alarm_active", "near_completion_alarm", "utility", "history-llm"):
            self.assertNotIn(forbidden, encoded)

    def test_standalone_html_embeds_only_escaped_player_payload(self):
        payload = export_bundle([("clip-a1", run_records())])
        template = '<script id="player-data" type="application/json">__PLAYER_SAFE_JSON__</script>'
        result = standalone_html(payload, template)
        self.assertIn('"clip_id":"clip-a1"', result)
        self.assertNotIn("SECRET-", result)
        self.assertIn("\\u003c", standalone_html({"clips": [], "user_text": "</script>"}, template))

    def test_outputs_refuse_to_overwrite_existing_files(self):
        payload = export_bundle([("clip-a1", run_records())])
        with tempfile.TemporaryDirectory() as directory:
            json_path = Path(directory) / "player.json"
            html_path = Path(directory) / "player.html"
            write_outputs(payload, json_path, html_path)
            before = json_path.read_text(encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "refusing to overwrite"):
                write_outputs({"clips": []}, json_path, html_path)
            self.assertEqual(json_path.read_text(encoding="utf-8"), before)


if __name__ == "__main__":
    unittest.main()
