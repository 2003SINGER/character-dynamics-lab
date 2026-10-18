from __future__ import annotations

import unittest

from tools.character_dynamics_online_v0 import new_session, step


def actor_view(time: float, candidates=(101, 102), hired=(), leader_uid=476):
    return {
        "event": "native_recruit_actor_view", "version": 1,
        "time": time, "npc_uid": leader_uid, "mode": "simulated",
        "role": {"kind": "civilised", "profession": "pirate", "is_leader": True},
        "job": None, "home_site_id": "opaque-home", "current_site_id": "opaque-home",
        "faction_id": None,
        "leader_at_home": True,
        "native_recruit_population_guard": True,
        "native_recruit_raid_site_available": True,
        "eligible_recruits": [{"npc_uid": uid, "mode": "simulated", "distance_3d": 8.0 + i}
                              for i, uid in enumerate(candidates)],
        "hired_members": [{"npc_uid": uid, "mode": "simulated", "distance_3d": 9.0}
                           for uid in hired],
        "hired_member_count": len(hired),
    }


def command(op, goal_id, version, target, deadline=20.0):
    return {"op": op, "goal_id": goal_id, "version": version,
            "target_uid": target, "hired_by_uid": 476, "deadline": deadline}


def evidence(target, time, *, source="native-monitor", request_id=None):
    row = {"event": "native_recruit_job_observed", "target_uid": target,
           "leader_uid": 476, "hired_by_uid": 476,
           "game_time": time, "source_id": source, "job": "Hired"}
    if request_id is not None:
        row["request_id"] = request_id
    return row


def terminal(request_id, target, outcome="hired_observed"):
    return {"event": "native_recruit_terminal", "request_id": request_id,
            "leader_uid": 476, "target_uid": target, "outcome": outcome}


class OnlineCoreTests(unittest.TestCase):
    def test_director_off_keeps_actor_planner_running_and_can_choose_distinct_uids(self):
        session = new_session(476, director_enabled=False)
        first = step(session, actor_view(1.0), game_time=1.0)
        self.assertEqual(first["decision"]["request"]["source"], "ACTOR")
        self.assertEqual(first["decision"]["planning"]["planner"], "gtpyhop-core-2.0.2")
        self.assertEqual(first["decision"]["planning"]["refinement"]["primitive_action"],
                         "propose_native_request")
        self.assertIn(first["decision"]["request"]["target_uid"], (101, 102))
        second = step(new_session(476, director_enabled=True), actor_view(2.0),
                      game_time=2.0, director_hint={"candidate_order": [102, 101]})
        self.assertEqual(second["decision"]["request"]["target_uid"], 102)

    def test_global_job_evidence_never_leaks_into_actor_goal_view(self):
        session = new_session(476, hire_quota=2)
        result = step(session, actor_view(1.0, candidates=(101,)), game_time=1.0,
                      native_evidence={"events": [evidence(999, 0.5)], "coverage_through": 1.0,
                                       "source_id": "global-monitor"})
        self.assertEqual(result["decision"]["request"]["source"], "ACTOR")
        self.assertEqual(result["decision"]["actor_goal"]["observed_hired_uids"], [])
        self.assertNotIn("native_job_evidence", result["decision"]["actor_goal"])

    def test_author_append_and_edit_change_real_candidate_selection_and_preserve_versions(self):
        session = new_session(476, director_enabled=True)
        first = step(session, actor_view(1.0), game_time=1.0)
        self.assertEqual(first["decision"]["request"]["source"], "ACTOR")
        edited = step(first["session"], actor_view(2.0), game_time=2.0,
                      author_commands=[command("append", "future-member", 1, 101)],
                      feedback=[{"request_id": first["decision"]["request"]["request_id"], "status": "SENT"}])
        self.assertIsNone(edited["decision"]["request"])
        self.assertEqual(edited["decision"]["blocked"]["code"], "NATIVE_REQUEST_IN_FLIGHT")
        self.assertEqual(len(edited["session"]["author_obligations"]["future-member"]["versions"]), 1)
        revised = step(edited["session"], actor_view(3.0), game_time=3.0,
                       author_commands=[command("edit", "future-member", 2, 102)],
                       feedback=[{"request_id": first["decision"]["request"]["request_id"], "status": "SENT"}])
        self.assertEqual(revised["decision"]["blocked"]["code"], "NATIVE_REQUEST_IN_FLIGHT")
        self.assertEqual(revised["session"]["inflight_request"]["target_uid"],
                         first["decision"]["request"]["target_uid"])
        settled = step(revised["session"], actor_view(4.0, candidates=(102,), hired=(101,)), game_time=4.0,
                       native_evidence={"events": [evidence(101, 4.0,
                                                             request_id=first["decision"]["request"]["request_id"])],
                                        "coverage_through": 4.0,
                                        "source_id": "global-monitor"},
                       feedback=[{"request_id": first["decision"]["request"]["request_id"], "status": "SETTLED"}])
        self.assertIsNone(settled["decision"]["request"])
        self.assertTrue(settled["decision"]["blocked"]["native_job_seen"])
        self.assertEqual(settled["decision"]["author_obligations"][0]["status"], "PENDING")
        versions = settled["decision"]["author_obligations"][0]["versions"]
        self.assertEqual([v["status"] for v in versions], ["UNKNOWN", "PENDING"])
        self.assertEqual(versions[0]["lifecycle"], "SUPERSEDED")
        self.assertEqual(versions[0]["closed_at"], 3.0)
        ready = step(settled["session"], actor_view(5.0, candidates=(102,), hired=(101,)), game_time=5.0,
                     feedback=[terminal(first["decision"]["request"]["request_id"],
                                        first["decision"]["request"]["target_uid"])])
        self.assertEqual(ready["decision"]["request"]["source"], "DIRECTOR")
        self.assertEqual(ready["decision"]["request"]["target_uid"], 102)
        self.assertEqual(ready["decision"]["request"]["author_version"], 2)

    def test_prior_local_roster_members_become_unknown_when_out_of_view(self):
        first = step(new_session(476, hire_quota=2),
                     actor_view(1.0, candidates=(102,), hired=(101,)), game_time=1.0)
        self.assertEqual(first["decision"]["actor_goal"]["status"], "PENDING")
        later = step(first["session"], actor_view(2.0, candidates=(102,), hired=()), game_time=2.0)
        self.assertEqual(later["decision"]["actor_goal"]["status"], "PENDING")
        self.assertEqual(later["decision"]["actor_goal"]["observed_hired_uids"], [])
        self.assertEqual(later["decision"]["actor_goal"]["previously_visible_now_unknown_uids"], [101])

    def test_native_settlement_wins_over_prediction(self):
        session = new_session(476, director_enabled=True)
        result = step(session, actor_view(1.0), game_time=1.0,
                      author_commands=[command("append", "job-101", 1, 101)],
                      native_evidence={"events": [evidence(101, 1.0)], "coverage_through": 1.0,
                                       "source_id": "global-monitor"})
        obligation = result["decision"]["author_obligations"][0]
        self.assertEqual(obligation["status"], "SATISFIED")
        # A planner request is never itself a settlement witness.
        no_witness = step(new_session(476, director_enabled=True), actor_view(1.0), game_time=1.0,
                          author_commands=[command("append", "job-101", 1, 101)])
        self.assertEqual(no_witness["decision"]["author_obligations"][0]["status"], "UNKNOWN")

    def test_planner_labeled_receipt_is_not_native_evidence(self):
        result = step(new_session(476, director_enabled=True), actor_view(1.0), game_time=1.0,
                      author_commands=[command("append", "job-101", 1, 101)],
                      native_evidence={"events": [{**evidence(101, 1.0), "source": "PLANNER",
                                                   "prediction_only": True}],
                                       "coverage_through": 1.0, "source_id": "planner-prediction"})
        self.assertEqual(result["decision"]["author_obligations"][0]["status"], "UNKNOWN")

    def test_future_native_event_time_is_not_used_before_current_game_time(self):
        result = step(new_session(476, director_enabled=True), actor_view(1.0), game_time=1.0,
                      author_commands=[command("append", "job-101", 1, 101)],
                      native_evidence={"events": [evidence(101, 3.0)], "coverage_through": 1.0,
                                       "source_id": "native-monitor"})
        self.assertEqual(result["decision"]["author_obligations"][0]["status"], "PENDING")

    def test_late_native_witness_without_complete_deadline_coverage_is_unknown(self):
        session = step(new_session(476, director_enabled=True), actor_view(1.0),
                       game_time=1.0, author_commands=[
                           command("append", "late", 1, 101, deadline=5.0)])
        result = step(session["session"], actor_view(9.0), game_time=9.0,
                      native_evidence={"events": [evidence(101, 8.0)],
                                       "source_id": "native-monitor"})
        status = result["decision"]["author_obligations"][0]
        self.assertEqual(status["status"], "UNKNOWN")
        self.assertIn("late native settlement", status["reason"])
        complete = step(session["session"], actor_view(9.0), game_time=9.0,
                        native_evidence={"events": [evidence(101, 8.0)],
                                         "coverage_through": 5.0,
                                         "source_id": "native-monitor"})
        self.assertEqual(complete["decision"]["author_obligations"][0]["status"], "VIOLATED")

    def test_loaded_msg_native_job_receipt_releases_only_its_matching_request(self):
        initial = step(new_session(476), actor_view(1.0), game_time=1.0)
        request = initial["decision"]["request"]
        native_receipt = {
            "event": "native_recruit_job_observed", "request_id": request["request_id"],
            "source_uid": 476, "leader_uid": 476, "hired_by_uid": 476,
            "job_actor_uid": 476, "target_uid": request["target_uid"],
            "recipient_uid": request["target_uid"], "time": 2.0, "job": "Hired",
        }
        settled = step(initial["session"],
                       actor_view(2.0, candidates=(102,), hired=(request["target_uid"],)),
                       game_time=2.0,
                       native_evidence={"events": [native_receipt], "coverage_through": 2.0,
                                        "source_id": "loaded-msg-monitor"})
        self.assertEqual(settled["session"]["inflight_request"]["request_id"], request["request_id"])
        self.assertTrue(settled["decision"]["blocked"]["native_job_seen"])
        terminal_result = step(settled["session"], actor_view(3.0, candidates=(102,), hired=(request["target_uid"],)),
                               game_time=3.0,
                               feedback=[terminal(request["request_id"], request["target_uid"])])
        self.assertNotEqual(terminal_result["session"]["inflight_request"]["request_id"], request["request_id"])
        self.assertEqual(terminal_result["decision"]["request"]["target_uid"], 102)
        self.assertEqual(terminal_result["decision"]["request"]["source"], "ACTOR")

    def test_absolute_deadline_is_not_reset_and_prior_version_is_immutable(self):
        first = step(new_session(476, director_enabled=True), actor_view(1.0), game_time=1.0,
                     author_commands=[command("append", "deadline", 1, 101, deadline=7.0)])
        second = step(first["session"], actor_view(2.0), game_time=2.0,
                      author_commands=[command("edit", "deadline", 2, 102, deadline=7.0)],
                      native_evidence={"events": [evidence(101, 1.5)], "coverage_through": 2.0,
                                       "source_id": "native-monitor"})
        record = second["session"]["author_obligations"]["deadline"]
        self.assertEqual([v["deadline"] for v in record["versions"]], [7.0, 7.0])
        self.assertEqual([v["effective_at"] for v in record["versions"]], [1.0, 2.0])
        expired = step(second["session"], actor_view(8.0), game_time=8.0,
                       native_evidence={"events": [], "coverage_through": 7.0, "source_id": "global-monitor"})
        self.assertEqual(expired["decision"]["author_obligations"][0]["status"], "VIOLATED")
        witness = step(second["session"], actor_view(3.0), game_time=3.0,
                       native_evidence={"events": [evidence(101, 1.5), evidence(102, 3.0)],
                                        "coverage_through": 3.0, "source_id": "global-monitor"})
        self.assertEqual([v["status"] for v in witness["decision"]["author_obligations"][0]["versions"]],
                         ["SATISFIED", "SATISFIED"])

    def test_absence_without_global_coverage_is_unknown_not_violation(self):
        session = new_session(476, director_enabled=True)
        first = step(session, actor_view(1.0), game_time=1.0,
                     author_commands=[command("append", "future", 1, 101, deadline=2.0)])
        later = step(first["session"], actor_view(9.0), game_time=9.0, native_evidence=None)
        self.assertEqual(later["decision"]["author_obligations"][0]["status"], "UNKNOWN")
        # A local ActorView with no 101 cannot erase its global author record.
        self.assertNotEqual(later["decision"]["author_obligations"][0]["status"], "VIOLATED")

    def test_editor_cannot_cancel_inflight_and_director_hint_cannot_inject_hidden_target(self):
        initial = step(new_session(476, director_enabled=True), actor_view(1.0), game_time=1.0)
        request = initial["decision"]["request"]
        edited = step(initial["session"], actor_view(2.0, candidates=(102,)), game_time=2.0,
                      author_commands=[command("append", "new", 1, 102)],
                      feedback=[{"request_id": request["request_id"], "status": "SENT"}],
                      director_hint={"candidate_order": [999, 102]})
        self.assertIsNone(edited["decision"]["request"])
        self.assertEqual(edited["decision"]["blocked"]["code"], "NATIVE_REQUEST_IN_FLIGHT")
        self.assertEqual(edited["session"]["inflight_request"]["request_id"], request["request_id"])

    def test_native_failure_is_recorded_and_same_unchanged_target_is_not_retried(self):
        first = step(new_session(476), actor_view(1.0), game_time=1.0)
        request = first["decision"]["request"]
        rejected = step(first["session"], actor_view(2.0), game_time=2.0,
                        feedback=[terminal(request["request_id"], request["target_uid"],
                                           outcome="expired_before_native_action")])
        self.assertIsNone(rejected["decision"]["request"])
        self.assertEqual(rejected["decision"]["blocked"]["code"],
                         "NATIVE_TERMINAL_REQUIRES_CHANGED_ACTOR_VIEW")
        self.assertEqual(rejected["session"]["last_native_terminal"]["outcome"],
                         "expired_before_native_action")
        changed = step(rejected["session"], actor_view(3.0, candidates=(102,)), game_time=3.0)
        self.assertEqual(changed["decision"]["request"]["target_uid"], 102)


if __name__ == "__main__":
    unittest.main()
