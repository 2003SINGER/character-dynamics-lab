import copy
import unittest

from tools.veloren_native_decision_v1.adapter import RecruitmentController, plan_recruitment


def actor_view(**updates):
    row = {
        "event": "native_recruit_actor_view",
        "version": 1,
        "time": 123.0,
        "npc_uid": 476,
        "mode": "loaded",
        "role": {"kind": "civilised", "profession": "pirate", "is_leader": True},
        "job": None,
        "home_site_id": "SiteId { data: 1 }",
        "current_site_id": "SiteId { data: 1 }",
        "leader_at_home": True,
        "native_recruit_population_guard": True,
        "native_recruit_raid_site_available": True,
        "eligible_recruits": [
            {"npc_uid": 475, "distance_3d": 13.19, "mode": "loaded"},
            {"npc_uid": 433, "distance_3d": 22.15, "mode": "loaded"},
            {"npc_uid": 450, "distance_3d": 23.0, "mode": "loaded"},
        ],
        "hired_members": [],
        "hired_member_count": 0,
    }
    row.update(updates)
    return row


class RecruitmentPlannerTests(unittest.TestCase):
    def test_htn_proposes_only_one_native_high_level_task(self):
        view = actor_view()
        original = copy.deepcopy(view)
        result = plan_recruitment(view)
        self.assertEqual(result["status"], "SOLVED_NEXT_SUBTASK", result)
        self.assertEqual(result["implementation"], "gtpyhop-core-2.0.2")
        self.assertTrue(result["prediction_only"])
        self.assertEqual(result["native_execution"], "not executed")
        self.assertEqual(len(result["plan"]), 1)
        self.assertEqual(result["task"]["kind"], "RecruitMember")
        self.assertEqual(result["task"]["leader_uid"], 476)
        self.assertEqual(result["task"]["target_uid"], 475)
        self.assertEqual(result["task"]["goal"], "nativeparty")
        self.assertEqual(result["task"]["goal_hired_member_count"], 4)
        self.assertEqual(result["task"]["observed_hired_member_count"], 0)
        self.assertEqual(result["task"]["predicted_hired_member_count_after_one_native_task"], 1)
        self.assertFalse(result["overall_goal_satisfied"])
        self.assertEqual(result["residual_goal"]["hired_member_count_at_least"], 4)
        self.assertEqual(view, original)

    def test_candidate_methods_backtrack_past_previously_attempted_uid(self):
        result = plan_recruitment(actor_view(), excluded_target_uids=(475,))
        self.assertEqual(result["status"], "SOLVED_NEXT_SUBTASK", result)
        self.assertEqual(result["task"]["target_uid"], 433)
        self.assertGreaterEqual(result["method_action_visits"], 6)

    def test_requires_at_least_two_untried_native_candidates_to_select(self):
        result = plan_recruitment(actor_view(), excluded_target_uids=(475, 433))
        self.assertEqual(result["status"], "INSUFFICIENT_CHOICES")
        self.assertIsNone(result["task"])

    def test_loaded_candidate_mode_can_be_required_without_rewriting_view(self):
        view = actor_view(eligible_recruits=[
            {"npc_uid": 475, "distance_3d": 13.19, "mode": "loaded"},
            {"npc_uid": 433, "distance_3d": 22.15, "mode": "simulated"},
            {"npc_uid": 450, "distance_3d": 23.0, "mode": "simulated"},
        ])
        result = plan_recruitment(view, require_loaded_candidates=True)
        self.assertEqual(result["status"], "INSUFFICIENT_CHOICES")
        self.assertEqual(view["eligible_recruits"][1]["mode"], "simulated")

    def test_native_population_guard_is_not_replaced_by_python_estimate(self):
        result = plan_recruitment(actor_view(native_recruit_population_guard=False))
        self.assertEqual(result["status"], "NATIVE_GUARD_FALSE")
        self.assertIsNone(result["task"])

    def test_native_raid_site_guard_is_read_not_recomputed_or_randomized(self):
        result = plan_recruitment(actor_view(native_recruit_raid_site_available=False))
        self.assertEqual(result["status"], "NATIVE_GUARD_FALSE")
        self.assertIsNone(result["task"])

    def test_leader_must_be_at_home_site_for_selection(self):
        result = plan_recruitment(actor_view(current_site_id="SiteId { data: 2 }",
                                            leader_at_home=False))
        self.assertEqual(result["status"], "INVALID_VIEW")
        self.assertIn("home site", result["reason"])

    def test_opaque_site_ids_are_diagnostic_and_must_match(self):
        result = plan_recruitment(actor_view(home_site_id="not-an-id"))
        self.assertEqual(result["status"], "INVALID_VIEW")
        self.assertIn("home site", result["reason"])

    def test_goal_satisfaction_uses_only_currently_visible_job_observations(self):
        members = [{"npc_uid": uid, "distance_3d": 2.0, "mode": "loaded"}
                   for uid in (433, 450, 451, 452)]
        result = plan_recruitment(actor_view(hired_members=members, hired_member_count=4))
        self.assertEqual(result["status"], "GOAL_SATISFIED_LOCALLY")
        self.assertEqual(result["observed_hired_member_uids"], [433, 450, 451, 452])

    def test_historical_member_observation_does_not_satisfy_current_goal(self):
        view = actor_view(hired_members=[], hired_member_count=0)
        result = plan_recruitment(view)
        self.assertEqual(result["status"], "SOLVED_NEXT_SUBTASK")
        self.assertEqual(result["task"]["observed_hired_member_count"], 0)

    def test_message_or_inconsistent_count_is_not_a_job_receipt(self):
        result = plan_recruitment(actor_view(hired_members=[], hired_member_count=1))
        self.assertEqual(result["status"], "INVALID_VIEW")
        self.assertIn("array length", result["reason"])

    def test_illegal_role_or_distance_is_rejected(self):
        role_result = plan_recruitment(actor_view(role={"kind": "civilised", "profession": "pirate",
                                                      "is_leader": False}))
        self.assertEqual(role_result["status"], "INVALID_VIEW")
        distance_result = plan_recruitment(actor_view(eligible_recruits=[
            {"npc_uid": 475, "distance_3d": 25.0, "mode": "loaded"},
            {"npc_uid": 433, "distance_3d": 20.0, "mode": "loaded"},
        ]))
        self.assertEqual(distance_result["status"], "INVALID_VIEW")


class RecruitmentControllerTests(unittest.TestCase):
    def test_off_records_views_and_never_calls_planner(self):
        def forbidden_planner(*args, **kwargs):
            raise AssertionError("OFF mode must not invoke the planner")
        controller = RecruitmentController("off", "off-trial", planner=forbidden_planner)
        rows = controller.feed(actor_view())
        self.assertEqual(rows[0]["event"], "native_actor_view_observed")
        self.assertEqual(rows[0]["mode"], "off")
        self.assertEqual(controller.request_count, 0)
        self.assertIsNone(controller.pending)

    def test_on_sends_one_request_and_message_sent_is_not_completion(self):
        controller = RecruitmentController("on", "on-trial")
        rows = controller.feed(actor_view())
        request_row = next(row for row in rows if row["event"] == "native_request_proposed")
        request = request_row["request"]
        self.assertEqual(request["kind"], "RecruitMember")
        self.assertEqual(request["target_uid"], 475)
        self.assertEqual(request["ttl_seconds"], 60.0)
        controller.feed({"event": "native_recruit_started", "request_id": request["request_id"],
                         "leader_uid": 476, "target_uid": 475})
        sent = controller.feed({"event": "native_recruit_message_sent", "request_id": request["request_id"],
                                "leader_uid": 476, "target_uid": 475})
        self.assertEqual(sent[0]["event"], "message_sent_not_completion")
        self.assertIsNotNone(controller.pending)
        self.assertEqual(controller.actual_job_observations, {})
        repeated = controller.feed(actor_view(time=124.0))
        self.assertFalse(any(row["event"] == "native_request_proposed" for row in repeated))

    def test_job_receipt_is_the_only_event_that_updates_hire_history(self):
        controller = RecruitmentController("on", "receipt-trial")
        controller.feed(actor_view())
        controller.feed({"event": "native_recruit_started", "request_id": "receipt-trial-recruit-01",
                         "leader_uid": 476, "target_uid": 475})
        controller.feed({"event": "native_recruit_message_sent", "request_id": "x", "target_uid": 475,
                         "time": 124.0})
        controller.feed({"event": "native_recruit_message_sent", "request_id": "receipt-trial-recruit-01",
                         "leader_uid": 476, "target_uid": 475, "time": 124.5})
        self.assertEqual(controller.actual_job_observations, {})
        rows = controller.feed({"event": "native_recruit_job_observed", "request_id": "receipt-trial-recruit-01",
                                "leader_uid": 476, "target_uid": 475, "time": 125.0})
        self.assertEqual(rows[0]["event"], "actual_hired_job_observation")
        self.assertEqual(controller.actual_job_observations, {475: 125.0})
        self.assertIsNotNone(controller.pending)
        controller.feed({"event": "native_recruit_terminal", "request_id": "receipt-trial-recruit-01",
                         "leader_uid": 476, "target_uid": 475, "time": 126.0,
                         "outcome": "hired_observed"})
        self.assertIsNone(controller.pending)

    def test_hire_observation_is_not_request_completion_until_matching_terminal(self):
        controller = RecruitmentController("on", "ordered-trial")
        controller.feed(actor_view())
        request_id = controller.pending["request_id"]
        controller.feed({"event": "native_recruit_started", "request_id": request_id,
                         "leader_uid": 476, "target_uid": 475})
        controller.feed({"event": "native_recruit_message_sent", "request_id": request_id,
                         "leader_uid": 476, "target_uid": 475})
        job = {"event": "native_recruit_job_observed", "request_id": request_id,
               "leader_uid": 476, "target_uid": 475, "time": 124.0}
        controller.feed(job)
        self.assertIsNotNone(controller.pending)
        terminal = {"event": "native_recruit_terminal", "request_id": request_id,
                    "leader_uid": 476, "target_uid": 475, "time": 125.0,
                    "outcome": "hired_observed"}
        controller.feed(terminal)
        self.assertIsNone(controller.pending)
        self.assertEqual(controller.actual_job_observations, {475: 124.0})

    def test_matching_terminal_before_job_observation_waits_for_real_job_fact(self):
        controller = RecruitmentController("on", "reverse-trial")
        controller.feed(actor_view())
        request_id = controller.pending["request_id"]
        controller.feed({"event": "native_recruit_started", "request_id": request_id,
                         "leader_uid": 476, "target_uid": 475})
        controller.feed({"event": "native_recruit_message_sent", "request_id": request_id,
                         "leader_uid": 476, "target_uid": 475})
        controller.feed({"event": "native_recruit_terminal", "request_id": request_id,
                         "leader_uid": 476, "target_uid": 475, "time": 124.0,
                         "outcome": "hired_observed"})
        self.assertIsNotNone(controller.pending)
        controller.feed({"event": "native_recruit_job_observed", "request_id": request_id,
                         "leader_uid": 476, "target_uid": 475, "time": 125.0})
        self.assertIsNone(controller.pending)

    def test_unattributed_hire_is_recorded_but_does_not_settle_inflight_request(self):
        controller = RecruitmentController("on", "unattributed-trial")
        controller.feed(actor_view())
        rows = controller.feed({"event": "native_recruit_job_observed", "request_id": "other-request",
                                "leader_uid": 476, "target_uid": 475, "time": 124.0})
        self.assertEqual(rows[0]["attribution"], "native_unattributed")
        self.assertEqual(controller.actual_job_observations, {475: 124.0})
        self.assertIsNotNone(controller.pending)

    def test_mismatched_terminal_target_cannot_release_pending(self):
        controller = RecruitmentController("on", "mismatch-trial")
        controller.feed(actor_view())
        request_id = controller.pending["request_id"]
        controller.feed({"event": "native_recruit_terminal", "request_id": request_id,
                         "leader_uid": 476, "target_uid": 433, "time": 124.0,
                         "outcome": "expired_after_message"})
        self.assertIsNotNone(controller.pending)

    def test_hired_terminal_without_native_message_and_job_chain_is_not_success(self):
        controller = RecruitmentController("on", "incomplete-chain-trial")
        controller.feed(actor_view())
        request_id = controller.pending["request_id"]
        rows = controller.feed({"event": "native_recruit_terminal", "request_id": request_id,
                                "leader_uid": 476, "target_uid": 475, "time": 124.0,
                                "outcome": "hired_observed"})
        self.assertTrue(any(row["event"] == "controller_protocol_violation" for row in rows))
        self.assertIsNotNone(controller.pending)
        self.assertEqual(controller.actual_job_observations, {})

    def test_failed_terminal_redirects_to_next_candidate_not_same_target(self):
        controller = RecruitmentController("on", "redirect-trial")
        first = controller.feed(actor_view())
        request = next(row["request"] for row in first if row["event"] == "native_request_proposed")
        controller.feed({"event": "native_recruit_terminal", "request_id": request["request_id"],
                         "leader_uid": 476, "target_uid": 475, "time": 124.0,
                         "outcome": "expired_after_message"})
        second = controller.feed(actor_view(time=125.0))
        next_request = next(row["request"] for row in second if row["event"] == "native_request_proposed")
        self.assertEqual(next_request["target_uid"], 433)
        self.assertNotEqual(next_request["request_id"], request["request_id"])

    def test_request_rejection_uses_unique_request_id_and_releases_pending(self):
        controller = RecruitmentController("on", "reject-trial")
        controller.feed(actor_view())
        request_id = controller.pending["request_id"]
        rows = controller.feed({"event": "native_recruit_request_rejected",
                                "request_id": request_id, "time": 124.0,
                                "reason": "native_guard"})
        self.assertEqual(rows[0]["event"], "native_request_rejected")
        self.assertIsNone(controller.pending)

    def test_mismatched_request_rejection_does_not_release_pending(self):
        controller = RecruitmentController("on", "reject-mismatch-trial")
        controller.feed(actor_view())
        controller.feed({"event": "native_recruit_request_rejected",
                         "request_id": "another-request", "time": 124.0,
                         "reason": "native_guard"})
        self.assertIsNotNone(controller.pending)

    def test_rejection_optional_uid_echo_must_match_when_present(self):
        controller = RecruitmentController("on", "reject-uid-mismatch-trial")
        controller.feed(actor_view())
        request_id = controller.pending["request_id"]
        controller.feed({"event": "native_recruit_request_rejected", "request_id": request_id,
                         "leader_uid": 476, "target_uid": 433, "time": 124.0,
                         "reason": "native_guard"})
        self.assertIsNotNone(controller.pending)

    def test_natural_hire_without_request_is_recorded_unattributed(self):
        controller = RecruitmentController("on", "natural-hire-trial")
        controller.feed(actor_view())
        rows = controller.feed({"event": "native_recruit_unattributed_hire_observed",
                                "leader_uid": 476, "target_uid": 433, "time": 124.0})
        self.assertEqual(rows[0]["attribution"], "native_unattributed")
        self.assertEqual(controller.actual_job_observations, {433: 124.0})
        self.assertIsNotNone(controller.pending)

    def test_four_currently_visible_hires_returns_control_without_end_hire(self):
        controller = RecruitmentController("on", "handoff-trial")
        controller.feed(actor_view())
        members = [{"npc_uid": uid, "distance_3d": 1.0, "mode": "loaded"}
                   for uid in (433, 450, 451, 452)]
        rows = controller.feed(actor_view(time=130.0, hired_members=members, hired_member_count=4))
        handoff = next(row for row in rows if row["event"] == "planner_control_returned_to_native")
        self.assertTrue(handoff["no_end_hire_sent"])
        self.assertIsNotNone(controller.pending)  # do not invent a cancellation/EndHire operation
        self.assertFalse(any(row["event"] == "native_request_proposed" for row in rows))


if __name__ == "__main__":
    unittest.main()
