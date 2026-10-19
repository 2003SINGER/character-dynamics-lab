from __future__ import annotations

import unittest

from tools.character_dynamics_online_v0.process_controller import (
    new_process_session, step_process,
)
from tools.character_dynamics_online_v0.process_runner import (
    DEFAULT_ACTORS, LEADER_UID, SCOUT_UID, _actor_goal_specs, build_observations,
    _author_demo_schedule, author_monitor_world_facts, build_process_environment, g1_feedback,
    g1_request_payload, loaded_process_readiness, normalize_registered_g1_receipt,
    process_completion_satisfied, project_actor_view,
    recruit_pair_feedback,
)


def g1_view(actor_uid: int, time: float, *, own_reports=(), known_reports=(),
            hired_by_uid=None):
    nearby = []
    other = LEADER_UID if actor_uid == SCOUT_UID else SCOUT_UID
    nearby.append({"uid": other, "wpos": [0.0, 0.0, 0.0], "distance": 5.0,
                   "alive": True, "loaded": True, "hired_by_uid": hired_by_uid})
    return {"event": "g1_actor_view", "schema_version": 1, "rule_version": "recon-v1",
            "time": time, "actor_uid": actor_uid, "wpos": [0.0, 0.0, 0.0],
            "role": "pirate", "job": None, "mode": "simulated",
            "current_site": "camp", "home_site": "camp",
            "markers": [
                {"marker_id": "marker-a", "label": "A", "kind": "camp",
                 "wpos": [1.0, 0.0], "arrival_radius": 4.0, "survey_seconds": 2.0},
                {"marker_id": "marker-b", "label": "B", "kind": "camp",
                 "wpos": [2.0, 0.0], "arrival_radius": 4.0, "survey_seconds": 2.0},
            ], "own_reports": list(own_reports), "known_reports": list(known_reports),
            "nearby": nearby, "active_lease": None}


def recruit_view(time: float):
    return {"event": "native_recruit_actor_view", "version": 1, "time": time,
            "npc_uid": LEADER_UID, "mode": "simulated",
            "role": {"kind": "civilised", "profession": "pirate", "is_leader": True},
            "job": None, "home_site_id": "camp", "current_site_id": "camp",
            "faction_id": None, "leader_at_home": True,
            "native_recruit_population_guard": True,
            "native_recruit_raid_site_available": True,
            "eligible_recruits": [{"npc_uid": 450, "mode": "simulated", "distance_3d": 5.0},
                                   {"npc_uid": SCOUT_UID, "mode": "simulated", "distance_3d": 4.0}],
            "hired_members": [], "hired_member_count": 0}


class ProcessRunnerProjectionTests(unittest.TestCase):
    def test_exact_rust_terminal_args_shapes_settle_all_three_g1_actions(self):
        common = {"request_id": "g1-shape", "actor_uid": SCOUT_UID,
                  "node_id": "node-shape", "source": "ACTOR", "goal_id": "goal-shape",
                  "author_version": None, "game_time": 20.0}
        cases = [
            ({**common, "action": "survey_marker",
              "args": {"marker_id": "marker-a", "report_id": None,
                       "receiver_uid": None, "follower_uid": None},
              "effects": [{"event": "g1_survey_completed", "marker_id": "marker-a",
                           "report_id": "g1:marker-a:433", "continuous_stay_seconds": 2.0}]},
             {**common, "primitive": "survey_marker", "args": {"marker_id": "marker-a"}}),
            ({**common, "action": "deliver_report",
              "args": {"marker_id": "marker-a", "report_id": "report-a",
                       "receiver_uid": LEADER_UID, "follower_uid": None},
              "effects": [{"event": "g1_report_delivered", "marker_id": "marker-a",
                           "report_id": "report-a", "from_uid": SCOUT_UID,
                           "to_uid": LEADER_UID, "native_interaction": "native_speech_emitted",
                           "interaction_request_id": "g1-shape", "speech_emitted_at": 19.0,
                           "distance": 2.0}]},
             {**common, "primitive": "deliver_report",
              "args": {"marker_id": "marker-a", "receiver_uid": LEADER_UID},
              "_late_bound_report_id": "report-a"}),
            ({**common, "actor_uid": LEADER_UID, "action": "rally_marker",
              "args": {"marker_id": "marker-a", "report_id": "report-a",
                       "receiver_uid": None, "follower_uid": 450},
              "effects": [{"event": "g1_rally_completed", "marker_id": "marker-a",
                           "report_id": "report-a", "report_owner_uid": SCOUT_UID,
                           "from_uid": SCOUT_UID, "leader_uid": LEADER_UID,
                           "follower_uid": 450, "leader_hired_follower": True,
                           "leader_knows_report": True}]},
             {**common, "actor_uid": LEADER_UID, "primitive": "rally_marker",
              "args": {"marker_id": "marker-a", "follower_uid": 450},
              "_late_bound_report_id": "report-a"}),
        ]
        for row, request in cases:
            with self.subTest(action=row["action"]):
                result, issue = normalize_registered_g1_receipt(
                    {"event": "g1_action_settled", **row}, {"g1-shape": request})
                self.assertIsNone(issue)
                self.assertEqual(result["event"], "g1_action_settled")

    def test_actual_preflight_survey_row_creates_report_only_from_settlement_effect(self):
        # Minimal synthetic projection of the private preflight2 receipt; no raw row is copied.
        request = {"request_id": "survey-actual-shape", "actor_uid": SCOUT_UID,
                   "node_id": "node-a", "primitive": "survey_marker",
                   "args": {"marker_id": "recon_site_a"}, "source": "ACTOR",
                   "goal_id": "scout-plan", "author_version": None,
                   "observed_time": 8.0, "_late_bound_report_id": None}
        row = {"event": "g1_action_settled", "request_id": request["request_id"],
               "actor_uid": SCOUT_UID, "node_id": "node-a", "action": "survey_marker",
               "source": "ACTOR", "goal_id": "scout-plan", "author_version": None,
               "args": {"marker_id": "recon_site_a", "report_id": None,
                        "receiver_uid": None, "follower_uid": None},
               "game_time": 10.205687750000006,
               "effects": [{"event": "g1_survey_completed", "marker_id": "recon_site_a",
                            "report_id": "g1:recon_site_a:433",
                            "continuous_stay_seconds": 2.021686959000002,
                            "settled_at": 10.205687750000006}]}
        feedback, issue = normalize_registered_g1_receipt(row, {request["request_id"]: request})
        self.assertIsNone(issue)
        self.assertEqual(feedback["effects"], [
            {"predicate": "survey_completed", "args": ["recon_site_a"]},
            {"predicate": "own_report", "args": ["recon_site_a"]}])
        self.assertEqual(feedback["provenance"]["native_args"]["report_id"], None)
        self.assertEqual(feedback["provenance"]["native_effect"]["report_id"],
                         "g1:recon_site_a:433")

    def test_delivery_requires_correlated_native_speech_emission(self):
        request = {"request_id": "delivery-r1", "actor_uid": SCOUT_UID,
                   "node_id": "deliver-node", "primitive": "deliver_report",
                   "args": {"marker_id": "marker-a", "receiver_uid": LEADER_UID},
                   "source": "ACTOR", "goal_id": "scout-delivery", "author_version": None,
                   "observed_time": 10.0, "_late_bound_report_id": "g1:marker-a:433"}
        base = {"event": "g1_action_settled", "request_id": "delivery-r1",
                "actor_uid": SCOUT_UID, "node_id": "deliver-node", "action": "deliver_report",
                "source": "ACTOR", "goal_id": "scout-delivery", "author_version": None,
                "args": {"marker_id": "marker-a", "report_id": "g1:marker-a:433",
                         "receiver_uid": LEADER_UID, "follower_uid": None},
                "game_time": 12.0,
                "effects": [{"event": "g1_report_delivered", "report_id": "g1:marker-a:433",
                             "from_uid": SCOUT_UID, "to_uid": LEADER_UID,
                             "native_interaction": "native_speech_emitted",
                             "interaction_request_id": "delivery-r1", "speech_emitted_at": 11.5,
                             "distance": 2.0}]}
        settled, issue = normalize_registered_g1_receipt(base, {"delivery-r1": request})
        self.assertIsNone(issue)
        self.assertEqual(settled["event"], "g1_action_settled")
        for field, value in (("interaction_request_id", "other-request"),
                             ("speech_emitted_at", 12.1),
                             ("native_interaction", "native_intent_queued")):
            altered = {**base, "effects": [dict(base["effects"][0], **{field: value})]}
            rejected, reason = normalize_registered_g1_receipt(
                altered, {"delivery-r1": request})
            self.assertIsNone(rejected, field)
            self.assertEqual(reason, "delivery_settlement_witness_invalid")

    def test_nonnull_action_irrelevant_native_argument_is_rejected(self):
        request = {"request_id": "g1-survey", "actor_uid": SCOUT_UID,
                   "node_id": "node", "primitive": "survey_marker",
                   "args": {"marker_id": "marker-a"}, "source": "ACTOR",
                   "goal_id": "goal", "author_version": None}
        row = {"event": "g1_action_failed", "request_id": "g1-survey",
               "actor_uid": SCOUT_UID, "node_id": "node", "action": "survey_marker",
               "source": "ACTOR", "goal_id": "goal", "author_version": None,
               "args": {"marker_id": "marker-a", "report_id": None,
                        "receiver_uid": LEADER_UID, "follower_uid": None},
               "game_time": 21.0}
        feedback, issue = normalize_registered_g1_receipt(row, {"g1-survey": request})
        self.assertIsNone(feedback)
        self.assertEqual(issue, "terminal_irrelevant_argument_not_null")

    def test_stable_marker_templates_exist_before_report_id_and_late_bind_is_native(self):
        projected = project_actor_view(g1_view(SCOUT_UID, 10.0))
        deliver = next(row for row in projected["action_models"]
                       if row["primitive"] == "deliver_report"
                       and row["args"] == {"marker_id": "marker-a", "receiver_uid": LEADER_UID})
        self.assertEqual(deliver["preconditions"], [
            {"predicate": "own_report", "args": ["marker-a"]}])
        self.assertNotIn("report_id", deliver["args"])
        self.assertIsInstance(deliver["provenance"], dict)
        self.assertEqual(deliver["dispatch_preconditions"], [
            {"predicate": "receiver_contact", "args": [LEADER_UID]}])
        self.assertTrue(any(fact["predicate"] == "own_report" and fact["value"] is True
                            for fact in project_actor_view(g1_view(SCOUT_UID, 11.0,
                                own_reports=[{"report_id": "native-r-7", "marker_id": "marker-a",
                                              "surveyed_at": 10.0}]))["facts"]))

    def test_delivery_contact_is_actor_local_and_matches_native_xy_radius(self):
        for distance, alive, loaded, expected in (
                (24.0, True, True, True), (24.001, True, True, False),
                (5.0, False, True, False), (5.0, True, False, False)):
            view = g1_view(SCOUT_UID, 10.0)
            view["nearby"][0].update(distance=distance, alive=alive, loaded=loaded)
            projected = project_actor_view(view)
            with self.subTest(distance=distance, alive=alive, loaded=loaded):
                self.assertIn({"predicate": "receiver_contact", "args": [LEADER_UID],
                               "value": expected}, projected["facts"])
        view = g1_view(SCOUT_UID, 10.0)
        view["nearby"] = []
        projected = project_actor_view(view)
        self.assertIn({"predicate": "receiver_contact", "args": [LEADER_UID],
                       "value": False}, projected["facts"])
        self.assertFalse(any(fact["predicate"] == "receiver_contact"
                             for fact in project_actor_view(g1_view(LEADER_UID, 10.0))["facts"]))

    def test_planner_forms_multi_step_scout_plan_without_guessing_report_id(self):
        session = new_process_session(DEFAULT_ACTORS,
                                      goal_specs=_actor_goal_specs(["marker-a", "marker-b"], 450))
        observations = build_observations(
            {SCOUT_UID: g1_view(SCOUT_UID, 10.0), LEADER_UID: g1_view(LEADER_UID, 10.1)},
            recruit_view(10.1), 450)
        first = step_process(session, observations, game_time=observations["game_time"])
        scout_request = next(row for row in first["decision"]["requests"]
                             if row["actor_uid"] == SCOUT_UID)
        self.assertEqual(scout_request["primitive"], "survey_marker")
        scout_plan = next(plan for plan in first["decision"]["plans"]
                          if plan["plan_key"].startswith(f"{SCOUT_UID}:ACTOR:"))
        planned_deliveries = [node for node in scout_plan["nodes"]
                              if node["primitive"] == "deliver_report"]
        self.assertEqual({node["args"]["marker_id"] for node in planned_deliveries},
                         {"marker-a", "marker-b"})
        self.assertTrue(all("report_id" not in node["args"] for node in planned_deliveries))
        terminal = {"event": "g1_action_settled", "request_id": scout_request["request_id"],
                    "actor_uid": SCOUT_UID, "node_id": scout_request["node_id"],
                    "action": "survey_marker", "args": {"marker_id": "marker-a"},
                    "game_time": 12.0,
                    "effects": [{"predicate": "survey_completed", "args": ["marker-a"]},
                                {"predicate": "own_report", "args": ["marker-a"]}],
                    "source": "ACTOR", "goal_id": scout_request["goal_id"],
                    "author_version": None}
        fresh = build_observations(
            {SCOUT_UID: g1_view(SCOUT_UID, 13.0,
                                own_reports=[{"report_id": "native-r-7", "marker_id": "marker-a",
                                              "surveyed_at": 12.0}]),
             LEADER_UID: g1_view(LEADER_UID, 13.1)}, recruit_view(13.1), 450)
        second = step_process(first["session"], fresh, game_time=fresh["game_time"],
                              feedback=[terminal])
        self.assertTrue(any(row["actor_uid"] == SCOUT_UID for row in second["decision"]["requests"]))
        deliver = next(row for row in fresh["actors"][0]["action_models"]
                       if row["primitive"] == "deliver_report"
                       and row["args"] == {"marker_id": "marker-a", "receiver_uid": LEADER_UID})
        payload = g1_request_payload({**deliver, "request_id": "example", "actor_uid": SCOUT_UID,
                                      "node_id": "node", "source": "ACTOR", "goal_id": "goal",
                                      "author_version": None, "observed_time": 13.1},
                                     {SCOUT_UID: g1_view(SCOUT_UID, 13.1,
                                         own_reports=[{"marker_id": "marker-a",
                                                       "report_id": "native-r-7"}])})
        self.assertEqual(payload["action"], "deliver_report")
        self.assertEqual(payload["args"]["report_id"], "native-r-7")

    def test_hire_and_rally_models_are_separate_and_actor_local(self):
        leader = project_actor_view(g1_view(LEADER_UID, 5.0), recruit_view=recruit_view(5.0),
                                    native_follower_uid=450)
        self.assertTrue(any(row["primitive"] == "RecruitMember" for row in leader["action_models"]))
        rally = next(row for row in leader["action_models"]
                     if row["primitive"] == "rally_marker"
                     and row["args"] == {"marker_id": "marker-a", "follower_uid": 450})
        self.assertEqual(rally["preconditions"], [
            {"predicate": "known_report_from", "args": ["marker-a", SCOUT_UID, LEADER_UID]},
            {"predicate": "hired_follower", "args": [LEADER_UID, 450]}])
        self.assertFalse(any(row["primitive"] == "RecruitMember"
                             for row in project_actor_view(g1_view(SCOUT_UID, 5.0))["action_models"]))
        self.assertFalse(any(row["primitive"] == "RecruitMember"
                             for row in leader["action_models"]
                             if row["args"].get("target_uid") == SCOUT_UID))

    def test_rally_cost_uses_each_marker_position_not_last_loop_value(self):
        view = g1_view(LEADER_UID, 5.0)
        view["nearby"].append({"uid": 450, "wpos": [5.0, 0.0, 0.0],
                               "distance": 5.0, "alive": True, "loaded": True,
                               "hired_by_uid": None})
        leader = project_actor_view(view, recruit_view=recruit_view(5.0),
                                    native_follower_uid=450)
        costs = {row["args"]["marker_id"]: row["estimated_cost"]
                 for row in leader["action_models"] if row["primitive"] == "rally_marker"}
        self.assertEqual(costs, {"marker-a": 6.0, "marker-b": 7.0})

    def test_native_marker_xy_costs_are_estimated_without_fake_z(self):
        view = g1_view(SCOUT_UID, 5.0)
        view["wpos"] = [10.0, 20.0, 42.0]
        view["markers"] = [
            {"marker_id": "near", "wpos": [13.0, 24.0], "survey_seconds": 2.0},
            {"marker_id": "far", "wpos": [16.0, 28.0], "survey_seconds": 2.0},
        ]
        projected = project_actor_view(view)
        costs = {row["args"]["marker_id"]: row["estimated_cost"]
                 for row in projected["action_models"]
                 if row["primitive"] == "survey_marker"}
        self.assertEqual(costs, {"near": 7.0, "far": 12.0})

    def test_native_environment_restores_bounded_observer_and_persister(self):
        names = ("native-events.jsonl", "g1-events.jsonl", "g1-requests.jsonl",
                 "recruit-events.jsonl", "recruit-requests.jsonl")
        from pathlib import Path
        paths = {name: Path("/tmp/online-test") / name for name in names}
        runtime = {"observe_npc_uids": [433, 476, 450],
                   "native_persister_npc_uids": [433, 476, 450],
                   "native_persister_view_distance_chunks": 2}
        source = {"assets_path": "/assets"}
        env = build_process_environment(
            {"VELOREN_NATIVE_EVENTS": "wrong", "VELOREN_NATIVE_OBSERVE": "0",
             "VELOREN_NATIVE_REQUESTS": "stale"}, source, runtime, paths,
            Path("/userdata"), DEFAULT_ACTORS, 450)
        self.assertEqual(env["VELOREN_NATIVE_EVENTS"], str(paths["native-events.jsonl"]))
        self.assertEqual(env["VELOREN_NATIVE_OBSERVE"], "1")
        self.assertEqual(env["VELOREN_NATIVE_OBSERVE_UIDS"], "433,476,450")
        self.assertEqual(env["VELOREN_NATIVE_PERSISTER_NPC_UIDS"], "433,476,450")
        self.assertEqual(env["VELOREN_NATIVE_PERSISTER_VIEW_DISTANCE"], "2")
        self.assertEqual(env["VELOREN_NATIVE_MAX_RECORDS"], "20000")
        self.assertEqual(env["VELOREN_NATIVE_MAX_BYTES"], str(64 * 1024 * 1024))
        self.assertEqual(env["VELOREN_NATIVE_MAX_SECONDS"], "720")
        self.assertNotIn("VELOREN_NATIVE_REQUESTS", env)

    def test_rally_requires_report_delivered_by_scout(self):
        leader_view = g1_view(LEADER_UID, 5.0,
                              known_reports=[{"report_id": "report-from-scout",
                                              "marker_id": "marker-a",
                                              "owner_uid": SCOUT_UID}])
        projected = project_actor_view(leader_view, recruit_view=recruit_view(5.0),
                                       native_follower_uid=450)
        self.assertIn({"predicate": "known_report_from",
                       "args": ["marker-a", SCOUT_UID, LEADER_UID], "value": True},
                      projected["facts"])

    def test_recruit_settlement_requires_job_and_terminal_in_either_order(self):
        request_id = "hire-r1"
        request = {"node_id": "hire-node", "actor_uid": LEADER_UID,
                   "primitive": "RecruitMember", "args": {"target_uid": 450},
                   "source": "ACTOR", "goal_id": "leader-hire-native-follower",
                   "author_version": None}
        job = {"request_id": request_id, "time": 21.0,
               "event": "native_recruit_job_observed", "target_uid": 450}
        terminal = {"request_id": request_id, "time": 22.0,
                    "event": "native_recruit_terminal", "leader_uid": LEADER_UID,
                    "target_uid": 450, "outcome": "hired_observed"}

        feedback, issue = recruit_pair_feedback(request_id, request, None, job)
        self.assertIsNone(feedback)
        self.assertIsNone(issue)
        feedback, issue = recruit_pair_feedback(request_id, request, terminal, None)
        self.assertIsNone(feedback)
        self.assertEqual(issue, "awaiting_trusted_job_witness")

        job_first, _ = recruit_pair_feedback(request_id, request, None, job)
        self.assertIsNone(job_first)
        complete, issue = recruit_pair_feedback(request_id, request, terminal, job)
        self.assertIsNone(issue)
        self.assertEqual(complete["event"], "g1_action_settled")
        self.assertEqual(complete["game_time"], 22.0)
        self.assertEqual(complete["provenance"]["native_job_time"], 21.0)
        self.assertEqual(complete["provenance"]["native_terminal_time"], 22.0)

    def test_recruit_failure_terminal_does_not_wait_for_job(self):
        request = {"node_id": "hire-node", "args": {"target_uid": 450},
                   "source": "ACTOR", "goal_id": "leader-hire-native-follower",
                   "author_version": None}
        terminal = {"request_id": "hire-r2", "time": 31.0,
                    "leader_uid": LEADER_UID, "target_uid": 450,
                    "outcome": "expired_after_message"}
        feedback, issue = recruit_pair_feedback("hire-r2", request, terminal, None)
        self.assertIsNone(issue)
        self.assertEqual(feedback["event"], "g1_action_failed")
        self.assertEqual(feedback["reason"], "expired_after_message")

    def test_rally_payload_late_binds_only_scout_owned_report(self):
        request = {"request_id": "rally-r1", "rule_version": "recon-v1",
                   "observed_time": 10.0, "actor_uid": LEADER_UID,
                   "node_id": "rally-node", "primitive": "rally_marker",
                   "args": {"marker_id": "marker-a", "follower_uid": 450},
                   "source": "ACTOR", "goal_id": "leader-rally-at-reported-sites",
                   "author_version": None}
        view = g1_view(LEADER_UID, 10.0, known_reports=[
            {"marker_id": "marker-a", "report_id": "self-report", "owner_uid": LEADER_UID},
            {"marker_id": "marker-a", "report_id": "scout-report", "owner_uid": SCOUT_UID},
        ])
        payload = g1_request_payload(request, {LEADER_UID: view})
        self.assertEqual(payload["args"]["report_id"], "scout-report")

    def test_author_monitor_requires_native_delivery_and_view_corroboration(self):
        report = {"marker_id": "marker-a", "report_id": "r7", "owner_uid": SCOUT_UID}
        self.assertEqual(author_monitor_world_facts({"known_reports": [report]}, set()), [])
        self.assertEqual(author_monitor_world_facts(
            {"known_reports": [report]}, {("marker-a", SCOUT_UID, LEADER_UID, "r7")} ),
            [{"predicate": "known_report_from",
              "args": ["marker-a", SCOUT_UID, LEADER_UID], "value": True}])

    def test_author_schedule_edits_leader_tail_with_fixed_deadline(self):
        schedule = _author_demo_schedule(["marker-a", "marker-b"], 450, 100.0)
        self.assertEqual([row["command"]["op"] for row in schedule], ["append", "append", "edit"])
        g1 = schedule[0]["command"]["ast"]
        self.assertEqual(g1["op"], "and")
        self.assertEqual(g1["children"][0]["args"], ["marker-a", SCOUT_UID, LEADER_UID])
        first, edited = schedule[1]["command"]["ast"], schedule[2]["command"]["ast"]
        self.assertEqual(first["at"], edited["at"])
        self.assertEqual(first["at"], 340.0)
        self.assertEqual(first["event"]["args"], [LEADER_UID, "marker-a", 450])
        self.assertEqual(edited["event"]["args"], [LEADER_UID, "marker-b", 450])

    def test_completion_requires_role_and_author_sat_no_inflight_and_demo_versions(self):
        applied = {("g1-scout-handoff-witness", 1),
                   ("g2-leader-rally-deadline", 1), ("g2-leader-rally-deadline", 2)}
        decision = {"plans": [{"plan_key": f"{uid}:ACTOR:goal", "status": "SATISFIED"}
                              for uid in (SCOUT_UID, LEADER_UID, LEADER_UID)],
                    "author_obligations": [{"status": "SATISFIED"}, {"status": "SATISFIED"}]}
        self.assertTrue(process_completion_satisfied({"inflight_by_actor": {}}, decision, applied))
        self.assertFalse(process_completion_satisfied({"inflight_by_actor": {"476": {}}},
                                                     decision, applied))

    def test_warmup_blocks_simulated_or_stale_views_before_dispatch(self):
        simulated = {SCOUT_UID: g1_view(SCOUT_UID, 5.0),
                     LEADER_UID: g1_view(LEADER_UID, 5.1)}
        ready, reason = loaded_process_readiness(
            simulated, {**recruit_view(5.1), "mode": "loaded"}, 450,
            recruit_view_observed=True, game_time=5.1)
        self.assertFalse(ready)
        self.assertIn("loaded_mode_unconfirmed", reason)

        loaded = {uid: {**g1_view(uid, 5.0 + (0.1 if uid == LEADER_UID else 0.0)),
                        "mode": "loaded"} for uid in DEFAULT_ACTORS}
        leader_recruit = {**recruit_view(5.1), "mode": "loaded"}
        ready, reason = loaded_process_readiness(
            loaded, leader_recruit, 450, recruit_view_observed=True, game_time=5.1)
        self.assertTrue(ready, reason)
        post_warmup_no_longer_eligible = {**leader_recruit, "eligible_recruits": []}
        ready, reason = loaded_process_readiness(
            loaded, post_warmup_no_longer_eligible, 450,
            recruit_view_observed=True, game_time=5.1, warmup_completed=True)
        self.assertTrue(ready, reason)
        ready, reason = loaded_process_readiness(
            loaded, post_warmup_no_longer_eligible, 450,
            recruit_view_observed=True, game_time=5.1, warmup_completed=True,
            native_follower_hired=True)
        self.assertFalse(ready)
        self.assertIn("correlated_hire_not_in_fresh_native_roster", reason)
        hired_roster = {**post_warmup_no_longer_eligible,
                        "hired_members": [{"npc_uid": 450}]}
        ready, reason = loaded_process_readiness(
            loaded, hired_roster, 450, recruit_view_observed=True,
            game_time=5.1, warmup_completed=True, native_follower_hired=True)
        self.assertTrue(ready, reason)
        ready, reason = loaded_process_readiness(
            loaded, leader_recruit, 450, recruit_view_observed=False, game_time=5.1)
        self.assertFalse(ready)
        self.assertEqual(reason, "PRECONDITION_UNKNOWN:leader_recruit_view_not_fresh")

    def test_acceptance_is_not_settlement_and_terminal_requires_effect_shape(self):
        accepted = {"event": "g1_action_accepted", "request_id": "r", "actor_uid": SCOUT_UID,
                    "action": "survey_marker", "node_id": "n", "source": "ACTOR",
                    "goal_id": "g", "author_version": None, "game_time": 3.0}
        normalized = g1_feedback(accepted)
        self.assertEqual(normalized["event"], "g1_action_dispatch_accepted")
        self.assertNotIn("effects", normalized)
        terminal = {"event": "g1_action_settled", "request_id": "r", "actor_uid": SCOUT_UID,
                    "action": "survey_marker", "node_id": "n", "args": {"marker_id": "marker-a"},
                    "source": "ACTOR", "goal_id": "g", "author_version": None,
                    "game_time": 4.0, "effects": []}
        self.assertEqual(g1_feedback(terminal), terminal)


if __name__ == "__main__":
    unittest.main()
