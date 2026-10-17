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
            445: {"row": first, "wall": now, "history": [{"row": first, "wall": now}]},
            465: {"row": second, "wall": now, "history": [{"row": second, "wall": now}]},
        }

    def history_samples(self, previous_distance=4.0, latest_distance=4.5,
                        previous_time=10.0, latest_time=11.0, wall=None):
        now = time.monotonic() if wall is None else wall
        histories = {
            445: [self.baseline(445, [0.0, 0.0, 0.0], previous_time),
                  self.baseline(445, [0.0, 0.0, 0.0], latest_time)],
            465: [self.baseline(465, [previous_distance, 0.0, 0.0], previous_time),
                  self.baseline(465, [latest_distance, 0.0, 0.0], latest_time)],
        }
        return {uid: {"history": [{"row": row, "wall": now} for row in rows],
                      "row": rows[-1], "wall": now}
                for uid, rows in histories.items()}

    def test_fresh_pair_uses_loaded_speakers_and_three_dimensional_distance(self):
        now = time.monotonic()
        samples = self.history_samples(previous_distance=5.0, latest_distance=4.8, wall=now)
        self.assertTrue(probe.baseline_is_fresh_pair(samples, now, 11.0, 445, 465))
        samples = self.history_samples(previous_distance=5.5, latest_distance=5.1, wall=now)
        self.assertFalse(probe.baseline_is_fresh_pair(samples, now, 11.0, 445, 465))

    def test_pair_requires_two_independent_advancing_samples_and_rejects_fast_separation(self):
        now = time.monotonic()
        only_one = self.history_samples(wall=now)
        for item in only_one.values():
            item["history"] = item["history"][-1:]
        self.assertFalse(probe.baseline_is_fresh_pair(only_one, now, 11.0, 445, 465))
        fast = self.history_samples(previous_distance=3.0, latest_distance=4.0,
                                    previous_time=10.0, latest_time=11.0, wall=now)
        self.assertFalse(probe.baseline_is_fresh_pair(fast, now, 11.0, 445, 465))

    def test_latest_two_rows_must_both_be_loaded_and_time_synchronized(self):
        now = time.monotonic()
        simulated_previous = self.history_samples(wall=now)
        simulated_previous[445]["history"][0]["row"]["mode"] = "simulated"
        simulated_previous[445]["history"][0]["row"]["actual_world_state"] = None
        self.assertFalse(probe.baseline_is_fresh_pair(
            simulated_previous, now, 11.0, 445, 465))
        skewed = self.history_samples(wall=now)
        skewed[465]["history"][0]["row"]["time"] += 0.2
        self.assertFalse(probe.baseline_is_fresh_pair(skewed, now, 11.0, 445, 465))

    def test_repolling_old_event_does_not_create_a_second_independent_sample(self):
        with tempfile.TemporaryDirectory() as temp:
            events = Path(temp) / "events.jsonl"
            args = type("Args", (), {"events": str(events)})()
            event_state = {"offset": 0, "pending": b""}
            samples = {}
            candidates = {"pairs": set()}
            latest = {"game_time": float("-inf")}
            first_rows = [self.baseline(445, [0.0, 0.0, 0.0], 10.0),
                          self.baseline(465, [1.0, 0.0, 0.0], 10.0)]
            events.write_text("".join(json.dumps(row) + "\n" for row in first_rows))
            probe.read_observation_rows(args, event_state, samples, candidates, latest)
            probe.read_observation_rows(args, event_state, samples, candidates, latest)
            now = time.monotonic()
            self.assertFalse(probe.baseline_is_fresh_pair(samples, now, 10.0, 445, 465))

    def test_no_input_prefix_requires_three_distinct_game_times_over_two_wall_seconds(self):
        self.assertFalse(probe.baseline_prefix_ready({10.0: 1.0, 11.0: 2.0}))
        self.assertFalse(probe.baseline_prefix_ready({10.0: 1.0, 11.0: 1.5, 12.0: 2.0}))
        self.assertTrue(probe.baseline_prefix_ready({10.0: 1.0, 11.0: 2.1, 12.0: 3.0}))

    def test_pair_rejects_stale_or_non_speaking_baseline(self):
        now = time.monotonic()
        samples = self.history_samples(wall=now)
        samples[465]["history"][-1]["row"]["actual_world_state"]["agent_behavior"] = "Behavior { MOVE }"
        samples[465]["row"]["actual_world_state"]["agent_allowed_to_speak"] = False
        self.assertFalse(probe.baseline_is_fresh_pair(samples, now, 10.0, 445, 465))
        samples[445]["history"][-1]["wall"] = now - probe.PAIR_MAX_WALL_AGE - 0.01
        self.assertFalse(probe.baseline_is_fresh_pair(samples, now, 10.0, 445, 465))

    def test_pair_requires_alive_allowed_speech_and_no_sender_lease(self):
        now = time.monotonic()
        samples = self.history_samples(wall=now)
        self.assertTrue(probe.baseline_is_fresh_pair(samples, now, 10.0, 445, 465))
        samples[445]["history"][-1]["row"]["external_lease_active"] = True
        self.assertFalse(probe.baseline_is_fresh_pair(samples, now, 10.0, 445, 465))
        samples[445]["history"][-1]["row"]["external_lease_active"] = False
        samples[465]["history"][-1]["row"]["alive"] = False
        self.assertFalse(probe.baseline_is_fresh_pair(samples, now, 10.0, 445, 465))

    def test_catalog_pair_order_uses_live_3d_distance_then_uid_and_preference(self):
        now = time.monotonic()
        samples = {}
        for pair in ((445, 465), (400, 500), (401, 501)):
            distance = {445: 1.0, 465: 1.0, 400: 3.0, 500: 3.0, 401: 3.0, 501: 3.0}[pair[0]]
            for uid, d in ((pair[0], 0.0), (pair[1], distance)):
                rows = [self.baseline(uid, [d, 0.0, 0.0], 10.0),
                        self.baseline(uid, [d, 0.0, 0.0], 11.0)]
                samples[uid] = {"row": rows[-1], "wall": now,
                                "history": [{"row": row, "wall": now} for row in rows]}
        candidate_pairs = {(445, 465), (400, 500), (401, 501)}
        ordered = probe.ordered_eligible_pairs(
            samples, candidate_pairs, (445, 465), now, 11.0)
        self.assertEqual(ordered[0], (445, 465))
        fallback = probe.ordered_eligible_pairs(
            samples, candidate_pairs - {(445, 465)}, (445, 465), now, 11.0)
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
                         (True, "CANCEL_PASS"))
        event["outcome"] = "cancelled"
        self.assertEqual(probe.cancel_is_clean([event], "negative")[1],
                         "CANCEL_INCORRECT_RESULT")

    def test_cancel_admission_rejection_is_independent_of_positive_attempts(self):
        rejected = {"event": "request_rejected", "request_id": "negative",
                    "reason": "pair_not_live_loaded_civilised_nearby"}
        self.assertEqual(probe.cancel_is_clean([rejected], "negative"),
                         (False, "CANCEL_REJECTED_AT_ADMISSION"))

    def test_request_rejected_ends_wait_immediately(self):
        with tempfile.TemporaryDirectory() as temp:
            events = Path(temp) / "events.jsonl"
            rejection = {"event": "request_rejected", "request_id": "r1",
                         "reason": "pair_not_live_loaded_civilised_nearby"}
            events.write_text(json.dumps(rejection) + "\n")
            args = type("Args", (), {"events": str(events)})()
            result = probe.collect_request_events(
                args, "r1", {"offset": 0, "pending": b""}, {}, {"pairs": set()},
                {"game_time": float("-inf")}, time.monotonic() + 10)
            self.assertEqual(result, [rejection])

    def test_request_rejected_for_another_id_does_not_end_current_wait(self):
        with tempfile.TemporaryDirectory() as temp:
            events = Path(temp) / "events.jsonl"
            rejection = {"event": "request_rejected", "request_id": "other",
                         "reason": "unrelated"}
            events.write_text(json.dumps(rejection) + "\n")
            args = type("Args", (), {"events": str(events)})()
            with mock.patch("run_talk_probe.time.monotonic", side_effect=[0.0, 0.0, 10.0]), \
                 mock.patch("run_talk_probe.time.sleep"):
                result = probe.collect_request_events(
                    args, "r1", {"offset": 0, "pending": b""}, {}, {"pairs": set()},
                    {"game_time": float("-inf")}, 1.0)
            self.assertEqual(result, [])

    def test_cancel_control_rejects_correlated_handoff(self):
        events = [{"event": "native_action_handoff", "request_id": "negative"}]
        self.assertFalse(probe.cancel_is_clean(events, "negative")[0])

    def test_cancel_control_classifies_any_later_correlated_effect_as_incorrect(self):
        events = [
            {"event": "native_brain_action_terminal", "request_id": "negative",
             "outcome": "cancelled_before_native_action"},
            {"event": "native_speech_emitted", "request_id": "negative"},
        ]
        self.assertEqual(probe.cancel_is_clean(events, "negative"),
                         (False, "CANCEL_INCORRECT_RESULT"))

    def test_cancel_rejection_plus_same_id_effect_is_integrity_error(self):
        events = [
            {"event": "request_rejected", "request_id": "negative"},
            {"event": "native_action_handoff", "request_id": "negative"},
        ]
        self.assertEqual(probe.cancel_is_clean(events, "negative"),
                         (False, "CANCEL_INCORRECT_RESULT"))

    def test_positive_chain_requires_accepted_and_exact_same_id_path(self):
        rows = [
            {"event": "request_accepted", "request_id": "r1"},
            {"event": "native_talk_branch", "request_id": "r1"},
            {"event": "native_brain_action_terminal", "request_id": "r1",
             "outcome": "native_intent_queued"},
            {"event": "native_action_handoff", "request_id": "r1",
             "action": "Say", "destination": "agent_queue"},
            {"event": "native_speech_emitted", "request_id": "r1"},
        ]
        self.assertTrue(probe.positive_chain_complete(rows, "r1", True))
        self.assertFalse(probe.positive_chain_complete(rows[1:], "r1", True))
        self.assertFalse(probe.positive_chain_complete(rows, "r2", True))


if __name__ == "__main__":
    unittest.main(verbosity=2)
