from __future__ import annotations

import unittest

from tools.character_dynamics_online_v0 import new_session, step
from tools.character_dynamics_online_v0.runner import (
    LEADER_UID, MAX_REQUESTS, REQUEST_TTL_SECONDS, TRIAL_WALL_CAPS,
    _recruit_payload, classify_outcome, normalize_rejected_feedback,
    parse_author_input,
)
from tools.veloren_native_decision_v1.loaded_msg_pair import LoadedMsgChain


def actor_view(time: float, candidates=(101, 102)):
    return {
        "event": "native_recruit_actor_view", "version": 1,
        "time": time, "npc_uid": LEADER_UID, "mode": "simulated",
        "role": {"kind": "civilised", "profession": "pirate", "is_leader": True},
        "job": None, "home_site_id": "home", "current_site_id": "home",
        "faction_id": None, "leader_at_home": True,
        "native_recruit_population_guard": True,
        "native_recruit_raid_site_available": True,
        "eligible_recruits": [
            {"npc_uid": uid, "mode": "simulated", "distance_3d": 8.0 + i}
            for i, uid in enumerate(candidates)
        ],
        "hired_members": [], "hired_member_count": 0,
    }


class OnlineRunnerSmokeTests(unittest.TestCase):
    def test_current_controller_api_and_exact_native_request_shape(self):
        result = step(new_session(LEADER_UID, director_enabled=True), actor_view(1.0),
                      game_time=1.0)
        request = result["decision"]["request"]
        self.assertEqual(request["source"], "ACTOR")
        payload = _recruit_payload(request, 1.0)
        self.assertEqual(set(payload), {"version", "kind", "request_id", "source",
                                        "leader_uid", "target_uid", "observed_time",
                                        "ttl_seconds"})
        self.assertEqual(payload["source"], "ACTOR")
        self.assertEqual(payload["leader_uid"], LEADER_UID)
        self.assertEqual(payload["ttl_seconds"], REQUEST_TTL_SECONDS)

    def test_native_minimal_reject_is_enriched_only_from_registered_request(self):
        first = step(new_session(LEADER_UID), actor_view(1.0), game_time=1.0)
        decision = first["decision"]
        request = decision["request"]
        payload = _recruit_payload(request, 1.0)
        provenance = LoadedMsgChain(LEADER_UID)
        provenance.register_request(payload)
        raw_reject = {"event": "native_recruit_request_rejected",
                      "request_id": request["request_id"], "time": 1.1,
                      "reason": "busy"}
        feedback = normalize_rejected_feedback(raw_reject, provenance)
        self.assertEqual(raw_reject.keys(), {"event", "request_id", "time", "reason"})
        self.assertEqual(feedback["leader_uid"], LEADER_UID)
        self.assertEqual(feedback["target_uid"], request["target_uid"])
        released = step(first["session"], actor_view(2.0), game_time=2.0,
                        feedback=[feedback])
        self.assertIsNone(released["session"]["inflight_request"])

    def test_unregistered_reject_is_not_promoted_and_native_terminal_shape_releases(self):
        provenance = LoadedMsgChain(LEADER_UID)
        self.assertIsNone(normalize_rejected_feedback(
            {"event": "native_recruit_request_rejected", "request_id": "unknown"}, provenance))

        first = step(new_session(LEADER_UID), actor_view(1.0), game_time=1.0)
        request = first["decision"]["request"]
        terminal = {"event": "native_recruit_terminal", "request_id": request["request_id"],
                    "leader_uid": LEADER_UID, "target_uid": request["target_uid"],
                    "outcome": "expired_before_native_action"}
        released = step(first["session"], actor_view(2.0), game_time=2.0,
                        feedback=[terminal])
        self.assertIsNone(released["session"]["inflight_request"])

    def test_bounded_trial_limits_are_not_expanded(self):
        self.assertEqual(TRIAL_WALL_CAPS,
                         {"NATIVE_ONLY": 60.0, "ACTOR_DIRECTOR_OFF": 120.0,
                          "ACTOR_DIRECTOR_ON": 120.0})
        self.assertEqual(MAX_REQUESTS, 3)
        self.assertEqual(REQUEST_TTL_SECONDS, 60.0)

    def test_native_only_is_baseline_not_a_two_hire_trial(self):
        self.assertEqual(classify_outcome(
            "NATIVE_ONLY", started=True, return_code=0, native_rows=5,
            requests=0, trusted_targets=set(), stop_reason="trial_wall_cap",
            violations=[]), "BASELINE_OBSERVED")
        self.assertEqual(classify_outcome(
            "NATIVE_ONLY", started=True, return_code=0, native_rows=5,
            requests=1, trusted_targets=set(), stop_reason="trial_wall_cap",
            violations=[]), "PARTIAL")

    def test_author_jsonl_accepts_one_structured_row_and_rejects_unknown_source(self):
        row = {"source": "LOCAL_AUTHOR", "issued_at_game_time": 12.4,
               "command": {"op": "append", "goal_id": "g", "version": 1,
                           "target_uid": 101, "hired_by_uid": LEADER_UID,
                           "deadline": 90.0}}
        command, error = parse_author_input(row)
        self.assertIsNone(error)
        self.assertEqual(command, row["command"])
        command, error = parse_author_input({**row, "source": "external-rpc"})
        self.assertIsNone(command)
        self.assertEqual(error, "source_not_allowlisted")


if __name__ == "__main__":
    unittest.main()
