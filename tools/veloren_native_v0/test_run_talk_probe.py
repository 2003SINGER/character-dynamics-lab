"""Unit tests for the file-only TalkToNpc probe; never launch Veloren."""

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import run_talk_probe as probe


class TalkProbeTests(unittest.TestCase):
    def baseline(self, uid, position, game_time=10.0, behavior="Behavior { SPEAK }"):
        return {
            "event": "native_npc_baseline",
            "npc_uid": uid,
            "mode": "loaded",
            "alive": True,
            "external_lease_active": False,
            "time": game_time,
            "actual_world_state": {
                "ecs_position": position,
                "agent_behavior": behavior,
                "agent_allowed_to_speak": True,
            },
        }

    def samples(self, first, second, wall=None):
        now = time.monotonic() if wall is None else wall
        return {
            445: {"row": first, "wall": now},
            465: {"row": second, "wall": now},
        }

    def test_fresh_pair_uses_loaded_speakers_and_three_dimensional_distance(self):
        now = time.monotonic()
        latest = 10.5
        samples = self.samples(
            self.baseline(445, [0.0, 0.0, 0.0], 10.0),
            self.baseline(465, [1.0, 0.0, 7.9], 10.5),
            now,
        )
        self.assertTrue(probe.baseline_is_fresh_pair(samples, now, latest, 445, 465))
        samples[465]["row"]["actual_world_state"]["ecs_position"][2] = 8.1
        self.assertFalse(probe.baseline_is_fresh_pair(samples, now, latest, 445, 465))

    def test_pair_rejects_stale_or_non_speaking_baseline(self):
        now = time.monotonic()
        samples = self.samples(
            self.baseline(445, [0.0, 0.0, 0.0]),
            self.baseline(465, [1.0, 0.0, 0.0], behavior="Behavior { MOVE }"),
            now,
        )
        samples[465]["row"]["actual_world_state"]["agent_allowed_to_speak"] = False
        self.assertFalse(probe.baseline_is_fresh_pair(samples, now, 10.0, 445, 465))
        samples[445]["wall"] = now - probe.PAIR_MAX_WALL_AGE - 0.01
        self.assertFalse(probe.baseline_is_fresh_pair(samples, now, 10.0, 445, 465))

    def test_pair_requires_alive_allowed_speech_and_no_sender_lease(self):
        now = time.monotonic()
        samples = self.samples(
            self.baseline(445, [0.0, 0.0, 0.0]),
            self.baseline(465, [1.0, 0.0, 0.0]),
            now,
        )
        self.assertTrue(probe.baseline_is_fresh_pair(samples, now, 10.0, 445, 465))
        samples[445]["row"]["external_lease_active"] = True
        self.assertFalse(probe.baseline_is_fresh_pair(samples, now, 10.0, 445, 465))
        samples[445]["row"]["external_lease_active"] = False
        samples[465]["row"]["alive"] = False
        self.assertFalse(probe.baseline_is_fresh_pair(samples, now, 10.0, 445, 465))

    def test_catalog_pair_order_uses_live_3d_distance_then_uid_and_preference(self):
        now = time.monotonic()
        rows = [
            self.baseline(445, [0.0, 0.0, 0.0]),
            self.baseline(465, [1.0, 0.0, 0.0]),
            self.baseline(400, [0.0, 0.0, 0.0]),
            self.baseline(500, [0.0, 0.0, 4.0]),
            self.baseline(401, [0.0, 0.0, 0.0]),
            self.baseline(501, [0.0, 0.0, 4.0]),
        ]
        samples = {row["npc_uid"]: {"row": row, "wall": now} for row in rows}
        candidate_pairs = {(445, 465), (400, 500), (401, 501)}
        stable_since = {pair: now - probe.STABLE_SECONDS - 0.1 for pair in candidate_pairs}
        ordered = probe.ordered_eligible_pairs(
            samples, candidate_pairs, (445, 465), now, 10.0, stable_since)
        self.assertEqual(ordered[0], (445, 465))
        fallback = probe.ordered_eligible_pairs(
            samples, candidate_pairs - {(445, 465)}, (445, 465), now, 10.0, stable_since)
        self.assertEqual(fallback, [(400, 500), (401, 501)])

    def test_catalog_candidates_are_normalized_and_only_loaded_talk_pairs_used(self):
        row = {
            "event": "native_npc_catalog",
            "loaded_talkable_pairs_sample": [
                {"from": {"npc_uid": 465}, "to": {"npc_uid": 445}},
                {"from": {"npc_uid": 900}, "to": {"npc_uid": 900}},
            ],
            "simulated_pair_hints_sample": [
                {"from": {"npc_uid": 100}, "to": {"npc_uid": 101}},
            ],
        }
        self.assertEqual(probe.catalog_pairs_from_event(row), {(445, 465)})

    def test_positive_request_ids_are_unique_and_hard_capped_at_six(self):
        ids = [probe.positive_request_id("trial", attempt, 6) for attempt in range(1, 7)]
        self.assertEqual(len(set(ids)), 6)
        self.assertEqual(ids[-1], "trial-006")
        with self.assertRaises(ValueError):
            probe.positive_request_id("trial", 7, 6)
        with self.assertRaises(ValueError):
            probe.positive_request_id("trial", 1, 7)

    def test_cancel_control_is_one_os_write_and_contains_two_complete_lines(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "requests.jsonl"
            path.write_bytes(b"")
            rows = [
                {"request_id": "negative", "kind": "TalkToNpc"},
                {"cancel_request_id": "negative"},
            ]
            real_write = probe.os.write
            with mock.patch("run_talk_probe.os.write", wraps=real_write) as write:
                payload, written = probe.append_records_once(path, rows, 0)
            self.assertEqual(write.call_count, 1)
            self.assertEqual(written, len(payload))
            self.assertEqual([json.loads(line) for line in path.read_bytes().splitlines()], rows)

    def test_input_alone_is_not_cancel_or_positive_feedback(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "requests.jsonl"
            path.write_text('{"request_id":"positive"}\n')
            self.assertFalse(probe.cancel_is_clean([], "negative")[0])
            self.assertEqual(probe.positive_complete([], "positive"), (False, False))

    def test_cancel_control_requires_exact_pre_action_terminal(self):
        event = {"event": "native_brain_action_terminal", "request_id": "negative",
                 "outcome": "cancelled_before_native_action"}
        self.assertEqual(probe.cancel_is_clean([event], "negative"),
                         (True, "cancelled_before_native_action"))
        event["outcome"] = "cancelled"
        self.assertFalse(probe.cancel_is_clean([event], "negative")[0])

    def test_cancel_control_rejects_correlated_handoff(self):
        events = [{"event": "native_action_handoff", "request_id": "negative"}]
        self.assertFalse(probe.cancel_is_clean(events, "negative")[0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
