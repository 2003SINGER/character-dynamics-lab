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
            "time": game_time,
            "actual_world_state": {
                "ecs_position": position,
                "agent_behavior": behavior,
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
        self.assertFalse(probe.baseline_is_fresh_pair(samples, now, 10.0, 445, 465))
        samples[465]["row"]["actual_world_state"]["agent_behavior"] = "SPEAK"
        samples[445]["wall"] = now - probe.PAIR_MAX_WALL_AGE - 0.01
        self.assertFalse(probe.baseline_is_fresh_pair(samples, now, 10.0, 445, 465))

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
