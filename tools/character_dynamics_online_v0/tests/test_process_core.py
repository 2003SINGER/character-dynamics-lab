from __future__ import annotations

import unittest

from tools.character_dynamics_online_v0 import new_process_session, step_process
from tools.character_dynamics_online_v0.process_planning import (
    plan_fact_goals, validate_process_observations,
)
from tools.character_dynamics_online_v0.process_runner import (
    LEADER_UID, SCOUT_UID, _author_demo_schedule, build_observations,
)


PROVENANCE = {"source": "registered-g1-model", "rule_version": "recon-v1"}


def fact(predicate, *args, value=True):
    return {"predicate": predicate, "args": list(args), "value": value}


def action(primitive, args, preconditions, effects, cost=1.0, dispatch_preconditions=()):
    return {"primitive": primitive, "args": args, "preconditions": preconditions,
            "dispatch_preconditions": list(dispatch_preconditions),
            "effects": effects, "estimated_cost": cost, "provenance": PROVENANCE}


def observations(now, actor_rows, world_facts=(), coverage=None):
    return {"schema": "character_dynamics_g1_observation_v0", "game_time": now,
            "actors": actor_rows, "world_facts": list(world_facts),
            "event_coverage_through": coverage}


def actor(uid, observation_id, facts, action_models):
    return {"actor_uid": uid, "observation_id": observation_id,
            "facts": facts, "action_models": action_models}


def settlement(request, when, effects, *, event_id="evt-1", node_id=None,
               actor_uid=None, request_id=None):
    return {"event": "g1_action_settled", "request_id": request_id or request["request_id"],
            "actor_uid": actor_uid if actor_uid is not None else request["actor_uid"],
            "node_id": node_id or request["node_id"], "action": request["primitive"],
            "args": request["args"], "game_time": when, "effects": effects,
            "source": request["source"], "goal_id": request["goal_id"],
            "author_version": request["author_version"], "event_id": event_id}


class MultiActorProcessCoreTests(unittest.TestCase):
    def test_delivery_waits_for_receiver_rally_terminal(self):
        delivery = action("deliver_report", {"marker_id": "m", "receiver_uid": 20},
                          [{"predicate": "own_report", "args": ["m"]}],
                          [{"predicate": "report_delivered", "args": ["m", 20]}],
                          dispatch_preconditions=[{"predicate": "receiver_contact", "args": [20]}])
        rally = action("rally_marker", {"marker_id": "m", "follower_uid": 30},
                       [{"predicate": "report_known", "args": ["m", 20]},
                        {"predicate": "hired_follower", "args": [20, 30]}],
                       [{"predicate": "rally_completed", "args": ["m", 30]}])
        session = new_process_session([10, 20], goal_specs=[
            {"goal_id": "a-leader-rally", "actor_uid": 20, "source": "ACTOR",
             "goals": [{"predicate": "rally_completed", "args": ["m", 30]}]},
            {"goal_id": "z-scout-delivery", "actor_uid": 10, "source": "ACTOR",
             "goals": [{"predicate": "report_delivered", "args": ["m", 20]}]}])
        first = step_process(session, observations(1, [
            actor(10, "scout-1", [fact("own_report", "m"), fact("receiver_contact", 20)], [delivery]),
            actor(20, "leader-1", [fact("report_known", "m", 20),
                                     fact("hired_follower", 20, 30)], [rally])]), game_time=1)
        rally_request = next(req for req in first["decision"]["requests"]
                             if req["primitive"] == "rally_marker")
        self.assertEqual(len(first["decision"]["requests"]), 1)
        self.assertTrue(any(row["code"] == "RECEIVER_RESOURCE_IN_FLIGHT"
                            and row["receiver_uid"] == 20 for row in first["decision"]["blocked"]))

        terminal = settlement(rally_request, 2,
                              [{"predicate": "rally_completed", "args": ["m", 30]}],
                              event_id="receiver-rally-settled")
        after = step_process(first["session"], observations(2, [
            actor(10, "scout-2", [fact("own_report", "m"), fact("receiver_contact", 20)], [delivery]),
            actor(20, "leader-2", [fact("report_known", "m", 20),
                                     fact("hired_follower", 20, 30),
                                     fact("rally_completed", "m", 30)], [rally])]),
            game_time=2, feedback=[terminal])
        delivery_request = next((req for req in after["decision"]["requests"]
                                 if req["primitive"] == "deliver_report"), None)
        self.assertIsNotNone(delivery_request, repr(after["decision"]))

    def test_dispatch_gate_wait_retry_and_independent_task_progress(self):
        delivery = action("deliver_report", {"marker_id": "m-a", "receiver_uid": 20},
                          [{"predicate": "own_report", "args": ["m-a"]}],
                          [{"predicate": "report_delivered", "args": ["m-a", 20]}],
                          cost=1, dispatch_preconditions=[
                              {"predicate": "receiver_contact", "args": [20]}])
        side = action("side_task", {}, [{"predicate": "side_ready", "args": [10]}],
                      [{"predicate": "side_done", "args": [10]}], cost=10)
        models = [delivery, side]
        session = new_process_session([10], goal_specs=[
            {"goal_id": "delivery-and-side", "actor_uid": 10, "source": "ACTOR", "goals": [
                {"predicate": "report_delivered", "args": ["m-a", 20]},
                {"predicate": "side_done", "args": [10]}]}])

        first = step_process(session, observations(1, [actor(10, "v1", [
            fact("own_report", "m-a"), fact("receiver_contact", 20),
            fact("side_ready", 10)], models)]), game_time=1)
        delivery_request = first["decision"]["requests"][0]
        self.assertEqual(delivery_request["primitive"], "deliver_report")

        failed = {"event": "g1_action_failed", "request_id": delivery_request["request_id"],
                  "actor_uid": 10, "node_id": delivery_request["node_id"],
                  "action": "deliver_report", "args": delivery_request["args"],
                  "game_time": 2, "reason": "receiver_not_nearby", "effects": [],
                  "source": "ACTOR", "goal_id": "delivery-and-side", "author_version": None,
                  "event_id": "delivery-failed"}
        after_failure = step_process(first["session"], observations(2, [actor(10, "v2", [
            fact("own_report", "m-a"), fact("side_ready", 10)], models)]),
            game_time=2, feedback=[failed])
        # The same unmet dispatch gate does not trigger a fresh delivery attempt;
        # the independent ready node in the same HTN plan can still run.
        self.assertEqual(after_failure["decision"]["requests"][0]["primitive"], "side_task")
        delivery_node = next(node for node in after_failure["decision"]["plans"][0]["nodes"]
                             if node["primitive"] == "deliver_report")
        self.assertEqual(delivery_node["status"], "retry_blocked")

        side_request = after_failure["decision"]["requests"][0]
        side_done = settlement(side_request, 3, [{"predicate": "side_done", "args": [10]}],
                               event_id="side-done")
        still_waiting = step_process(after_failure["session"], observations(3, [actor(10, "v3", [
            fact("own_report", "m-a"), fact("side_ready", 10), fact("side_done", 10)], models)]),
            game_time=3, feedback=[side_done])
        self.assertEqual(still_waiting["decision"]["requests"], [])
        self.assertTrue(any(block["code"] == "ACTION_RETRY_WAIT"
                            for block in still_waiting["decision"]["blocked"]))

        retry = step_process(still_waiting["session"], observations(4, [actor(10, "v4", [
            fact("own_report", "m-a"), fact("receiver_contact", 20),
            fact("side_ready", 10)], models)]), game_time=4)
        self.assertEqual(retry["decision"]["requests"][0]["primitive"], "deliver_report")
        self.assertEqual(retry["decision"]["requests"][0]["node_id"], delivery_request["node_id"])
        self.assertNotEqual(retry["decision"]["requests"][0]["request_id"], delivery_request["request_id"])

    def test_zero_request_budget_does_not_mark_proposal_inflight(self):
        models = [action("make", {}, [], [{"predicate": "done", "args": [1]}])]
        session = new_process_session([1], goal_specs=[
            {"goal_id": "one", "actor_uid": 1, "source": "ACTOR",
             "goals": [{"predicate": "done", "args": [1]}]}])
        result = step_process(session, observations(1, [actor(1, "a", [], models)]),
                              game_time=1, request_budget_remaining=0)
        self.assertEqual(result["decision"]["requests"], [])
        self.assertEqual(result["session"]["inflight_by_actor"], {})
        self.assertTrue(any(row["code"] == "REQUEST_BUDGET_EXHAUSTED"
                            for row in result["decision"]["blocked"]))
        self.assertEqual(result["decision"]["plans"][0]["nodes"][0]["status"], "planned")

    def test_scout_goal_refines_survey_then_delivery_without_report_id(self):
        models = [
            action("survey_marker", {"marker_id": "m-a"}, [
                {"predicate": "at_marker", "args": ["m-a"]}], [
                {"predicate": "survey_completed", "args": ["m-a"]},
                {"predicate": "own_report", "args": ["m-a"]},
                {"predicate": "event:g1_survey_completed", "args": ["m-a"]}]),
            action("survey_marker", {"marker_id": "m-b"}, [
                {"predicate": "at_marker", "args": ["m-b"]}], [
                {"predicate": "survey_completed", "args": ["m-b"]},
                {"predicate": "own_report", "args": ["m-b"]},
                {"predicate": "event:g1_survey_completed", "args": ["m-b"]}], cost=2),
            action("deliver_report", {"marker_id": "m-a", "receiver_uid": 476}, [
                {"predicate": "own_report", "args": ["m-a"]},
                {"predicate": "receiver_nearby", "args": [476]}], [
                {"predicate": "report_delivered", "args": ["m-a", 476]},
                {"predicate": "event:g1_report_delivered", "args": ["m-a", 476]}]),
        ]
        session = new_process_session([510, 476], goal_specs=[
            {"goal_id": "scout-route", "actor_uid": 510, "source": "ACTOR", "goals": [
                {"predicate": "survey_completed", "args": ["m-a"]},
                {"predicate": "survey_completed", "args": ["m-b"]},
                {"predicate": "report_delivered", "args": ["m-a", 476]}]}])
        actor_rows = [actor(510, "scout-1", [fact("at_marker", "m-a"), fact("at_marker", "m-b"),
                                               fact("receiver_nearby", 476)], models),
                      actor(476, "leader-1", [], [])]
        result = step_process(session, observations(1, actor_rows), game_time=1)
        plan = result["decision"]["plans"][0]
        self.assertEqual(plan["planner"], "gtpyhop-core-2.0.2")
        self.assertEqual(len([node for node in plan["nodes"]
                              if node["status"] in ("pending", "planned")]), 3)
        self.assertEqual(result["decision"]["requests"][0]["primitive"], "survey_marker")
        self.assertNotIn("report_id", result["decision"]["requests"][0]["args"])

    def test_leader_waits_for_real_hire_before_rally_dispatch(self):
        models = [
            action("RecruitMember", {"target_uid": 900}, [
                {"predicate": "recruit_eligible", "args": [900]}], [
                {"predicate": "hired_follower", "args": [476, 900]},
                {"predicate": "event:native_recruit_job_observed", "args": [476, 900]}]),
            action("rally_marker", {"marker_id": "m-a", "follower_uid": 900}, [
                {"predicate": "report_known", "args": ["m-a", 476]},
                {"predicate": "hired_follower", "args": [476, 900]},
                {"predicate": "leader_at_marker", "args": ["m-a"]},
                {"predicate": "follower_at_marker", "args": ["m-a", 900]}], [
                {"predicate": "rally_completed", "args": ["m-a", 900]},
                {"predicate": "event:g1_rally_completed", "args": ["m-a", 900]}]),
        ]
        session = new_process_session([476], goal_specs=[
            {"goal_id": "leader-rally", "actor_uid": 476, "source": "ACTOR",
             "goals": [{"predicate": "rally_completed", "args": ["m-a", 900]}]}])
        first_view = actor(476, "leader-1", [fact("report_known", "m-a", 476),
                                              fact("recruit_eligible", 900),
                                              fact("leader_at_marker", "m-a"),
                                              fact("follower_at_marker", "m-a", 900)], models)
        first = step_process(session, observations(1, [first_view]), game_time=1)
        request = first["decision"]["requests"][0]
        self.assertEqual(request["primitive"], "RecruitMember")
        accepted = {"event": "g1_action_dispatch_accepted", "request_id": request["request_id"],
                    "actor_uid": 476, "node_id": request["node_id"], "game_time": 1.1}
        waiting = step_process(first["session"], observations(2, [
            actor(476, "leader-2", first_view["facts"], models)]), game_time=2, feedback=[accepted])
        self.assertEqual(waiting["decision"]["requests"], [])
        self.assertEqual(waiting["session"]["inflight_by_actor"]["476"]["request_id"], request["request_id"])
        receipt = settlement(request, 3, [
            {"predicate": "hired_follower", "args": [476, 900]},
            {"predicate": "event:native_recruit_job_observed", "args": [476, 900]}])
        after = step_process(waiting["session"], observations(3, [
            actor(476, "leader-3", first_view["facts"] + [fact("hired_follower", 476, 900)], models)]),
            game_time=3, feedback=[receipt])
        self.assertEqual(after["decision"]["requests"][0]["primitive"], "rally_marker")

    def test_global_world_facts_never_satisfy_actor_plan(self):
        session = new_process_session([476], goal_specs=[
            {"goal_id": "must-know-report", "actor_uid": 476, "source": "ACTOR",
             "goals": [{"predicate": "report_known", "args": ["remote", 476]}]}])
        row = actor(476, "actor-1", [], [])
        result = step_process(session, observations(1, [row], [fact("report_known", "remote", 476)]),
                              game_time=1)
        self.assertEqual(result["decision"]["requests"], [])
        self.assertEqual(result["decision"]["blocked"][0]["code"], "BLOCKED")
        self.assertNotIn("report_known", repr(result["decision"]["plans"]))

    def test_alternative_producers_are_or_not_an_and_sequence(self):
        models = [action("route_a", {}, [], [{"predicate": "complete", "args": [1]}]),
                  action("route_b", {}, [], [{"predicate": "complete", "args": [1]}])]
        decoded = validate_process_observations(observations(1, [actor(1, "a", [], models)]), 1)[1]
        plan = plan_fact_goals(decoded, [{"predicate": "complete", "args": [1]}])
        self.assertEqual(plan["status"], "PLANNED")
        self.assertEqual(len(plan["steps"]), 1)
        self.assertIn(plan["steps"][0]["primitive"], {"route_a", "route_b"})

    def test_unknown_mismatch_and_duplicate_receipts_do_not_advance_twice(self):
        models = [action("survey_marker", {"marker_id": "m"}, [], [
            {"predicate": "survey_completed", "args": ["m"]}])]
        session = new_process_session([10], goal_specs=[
            {"goal_id": "survey", "actor_uid": 10, "source": "ACTOR",
             "goals": [{"predicate": "survey_completed", "args": ["m"]}]}])
        first = step_process(session, observations(1, [actor(10, "a", [], models)]), game_time=1,
                             author_commands=[{"op": "append", "goal_id": "survey-witness",
                                               "version": 1, "actor_uid": 10,
                                               "ast": {"op": "deadline", "event": {
                                                   "event": "g1_survey_completed", "args": [20, "m"]},
                                                   "at": 10.0}}])
        req = first["decision"]["requests"][0]
        wrong = settlement(req, 2, [{"predicate": "survey_completed", "args": ["m"]}],
                           event_id="wrong-node", node_id="not-the-node")
        mismatched = step_process(first["session"], observations(2, [actor(10, "b", [], models)]),
                                  game_time=2, feedback=[wrong])
        self.assertEqual(mismatched["session"]["inflight_by_actor"]["10"]["request_id"], req["request_id"])
        self.assertEqual(mismatched["decision"]["author_obligations"][0]["status"], "PENDING")
        self.assertNotIn('"event:g1_survey_completed"', repr(mismatched["session"]["native_history"]))
        good = settlement(req, 3, [{"predicate": "survey_completed", "args": ["m"]}], event_id="settled-1")
        settled = step_process(mismatched["session"], observations(3, [
            actor(10, "c", [fact("survey_completed", "m")], models)]), game_time=3, feedback=[good],
            author_commands=[{"op": "append", "goal_id": "survey-witness-by-actor",
                              "version": 1, "actor_uid": 10,
                              "ast": {"op": "deadline", "event": {
                                  "event": "g1_survey_completed", "args": [10, "m"]},
                                  "at": 10.0}}])
        statuses = [row["status"] for row in settled["decision"]["author_obligations"]]
        self.assertEqual(statuses, ["PENDING", "SATISFIED"])
        self.assertIn('["event:g1_survey_completed",[10,"m"]]',
                      settled["session"]["native_history"][1]["facts"])
        replay = step_process(settled["session"], observations(4, [
            actor(10, "d", [fact("survey_completed", "m")], models)]), game_time=4, feedback=[good])
        self.assertEqual(replay["decision"]["feedback_applied"][0]["duplicate"], True)
        self.assertEqual(len(replay["session"]["native_history"]), 2)
        self.assertEqual(len(replay["session"]["native_receipt_ids"]), 2)

    def test_event_order_cycle_blocks_instead_of_overriding_one_obligation(self):
        session = new_process_session([10], goal_specs=[])
        event_a = {"event": "g1_survey_completed", "args": ["m"]}
        event_b = {"event": "g1_report_delivered", "args": ["m", 10]}
        first = step_process(session, observations(1, [actor(10, "a", [], [])]), game_time=1,
                             author_commands=[{"op": "append", "goal_id": "ab", "version": 1,
                                               "actor_uid": 10, "ast": {"op": "event_before",
                                               "first": event_a, "second": event_b}}])
        second = step_process(first["session"], observations(2, [actor(10, "b", [], [])]), game_time=2,
                              author_commands=[{"op": "append", "goal_id": "ba", "version": 1,
                                                "actor_uid": 10, "ast": {"op": "event_before",
                                                "first": event_b, "second": event_a}}])
        self.assertTrue(any(row["code"] == "AUTHOR_CONSTRAINT_CONFLICT"
                            for row in second["decision"]["blocked"]))
        self.assertEqual(len(second["session"]["author_obligations"]), 2)

    def test_composed_event_before_edges_are_topologically_merged(self):
        event_a = {"event": "g1_survey_completed", "args": ["a"]}
        event_b = {"event": "g1_report_delivered", "args": ["b", 10]}
        event_c = {"event": "g1_rally_completed", "args": ["c", 20]}
        models = [action("make_a", {}, [], [{"predicate": "event:g1_survey_completed", "args": ["a"]}]),
                  action("make_b", {}, [], [{"predicate": "event:g1_report_delivered", "args": ["b", 10]}]),
                  action("make_c", {}, [], [{"predicate": "event:g1_rally_completed", "args": ["c", 20]}])]
        ast = {"op": "and", "children": [
            {"op": "event_before", "first": event_a, "second": event_b},
            {"op": "event_before", "first": event_c, "second": event_a}]}
        session = new_process_session([10])
        result = step_process(session, observations(1, [actor(10, "a", [], models)]), game_time=1,
                             author_commands=[{"op": "append", "goal_id": "ordered-chain",
                                               "version": 1, "actor_uid": 10, "ast": ast}])
        plan = result["decision"]["plans"][0]
        self.assertEqual([node["primitive"] for node in plan["nodes"]
                          if node["status"] in ("pending", "planned")], ["make_c", "make_a", "make_b"])
        self.assertEqual(result["decision"]["requests"][0]["primitive"], "make_c")

    def test_action_model_precondition_conflicting_with_authored_order_is_blocked(self):
        event_a = {"predicate": "event:g1_survey_completed", "args": ["a"]}
        event_b = {"predicate": "event:g1_report_delivered", "args": ["b", 10]}
        models = [action("make_a", {}, [event_b], [event_a]),
                  action("make_b", {}, [], [event_b])]
        decoded = validate_process_observations(observations(1, [actor(10, "a", [], models)]), 1)[10]
        plan = plan_fact_goals(decoded, [], ordered_groups=[[event_a, event_b]])
        self.assertEqual(plan["status"], "BLOCKED")
        self.assertEqual(plan.get("steps", []), [])

    def test_author_order_guards_actor_plan_until_other_actor_has_real_first_event(self):
        event_a = {"event": "g1_survey_completed", "args": [10, "m"]}
        event_b = {"event": "g1_rally_completed", "args": [20, "m", 30]}
        actor10_models = [action("survey_marker", {"marker_id": "m"}, [
            {"predicate": "at_marker", "args": ["m"]}], [
            {"predicate": "survey_completed", "args": ["m"]},
            {"predicate": "event:g1_survey_completed", "args": [10, "m"]}])]
        actor20_models = [action("rally_marker", {"marker_id": "m", "follower_uid": 30}, [
            {"predicate": "report_known", "args": ["m", 20]},
            {"predicate": "hired_follower", "args": [20, 30]}], [
            {"predicate": "rally_completed", "args": ["m", 30]},
            {"predicate": "event:g1_rally_completed", "args": [20, "m", 30]}]),
            action("do_side_task", {}, [{"predicate": "side_ready", "args": [20]}], [
                {"predicate": "side_done", "args": [20]}])]
        session = new_process_session([10, 20], goal_specs=[
            {"goal_id": "scout-a", "actor_uid": 10, "source": "ACTOR",
             "goals": [{"predicate": "survey_completed", "args": ["m"]}]},
            {"goal_id": "leader-b", "actor_uid": 20, "source": "ACTOR",
             "goals": [{"predicate": "rally_completed", "args": ["m", 30]}]},
            {"goal_id": "leader-side", "actor_uid": 20, "source": "ACTOR",
             "goals": [{"predicate": "side_done", "args": [20]}]}])
        ast = {"op": "event_before", "first": event_a, "second": event_b}
        first = step_process(session, observations(1, [
            actor(10, "a1", [fact("at_marker", "m")], actor10_models),
            actor(20, "b1", [fact("report_known", "m", 20), fact("hired_follower", 20, 30),
                              fact("side_ready", 20)], actor20_models)]), game_time=1,
            author_commands=[{"op": "append", "goal_id": "cross-actor-order", "version": 1,
                              "actor_uid": 20, "ast": ast}])
        self.assertEqual({row["primitive"] for row in first["decision"]["requests"]},
                         {"survey_marker", "do_side_task"})
        self.assertTrue(any(row["code"] == "AUTHOR_ORDER_PENDING"
                            and row["goal_id"] == "leader-b" for row in first["decision"]["blocked"]))
        survey = next(row for row in first["decision"]["requests"]
                      if row["primitive"] == "survey_marker")
        side_request = next(row for row in first["decision"]["requests"]
                            if row["primitive"] == "do_side_task")
        settled = settlement(survey, 2, [
            {"predicate": "survey_completed", "args": ["m"]}])
        side_settled = settlement(side_request, 2, [
            {"predicate": "side_done", "args": [20]}], event_id="side-settled")
        second = step_process(first["session"], observations(2, [
            actor(10, "a2", [fact("survey_completed", "m")], actor10_models),
            actor(20, "b2", [fact("report_known", "m", 20), fact("hired_follower", 20, 30),
                              fact("side_ready", 20)], actor20_models)]),
            game_time=2, feedback=[settled, side_settled])
        rally = next((row for row in second["decision"]["requests"]
                      if row["primitive"] == "rally_marker"), None)
        self.assertIsNotNone(rally, repr(second["decision"]))
        self.assertEqual(rally["source"], "DIRECTOR")
        self.assertEqual(rally["author_version"], 1)

    def test_real_projection_edits_g2_deadline_to_dispatch_marker_b(self):
        follower_uid = 450

        def views(now, *, scout_reports=()):
            def row(actor_uid, own_reports=(), known_reports=()):
                other_uid = LEADER_UID if actor_uid == SCOUT_UID else SCOUT_UID
                nearby = [{"uid": other_uid, "wpos": [0.0, 0.0, 0.0],
                           "distance": 5.0, "alive": True, "loaded": True,
                           "hired_by_uid": None}]
                if actor_uid == LEADER_UID:
                    nearby.append({"uid": follower_uid, "wpos": [0.0, 0.0, 0.0],
                                   "distance": 5.0, "alive": True, "loaded": True,
                                   "hired_by_uid": LEADER_UID})
                return {
                    "event": "g1_actor_view", "schema_version": 1,
                    "rule_version": "recon-v1", "time": float(now),
                    "actor_uid": actor_uid, "wpos": [0.0, 0.0, 0.0],
                    "role": "pirate", "job": None, "mode": "loaded",
                    "current_site": "camp", "home_site": "camp",
                    "markers": [
                        {"marker_id": "marker-a", "label": "A", "kind": "camp",
                         "wpos": [1.0, 0.0, 0.0], "arrival_radius": 4.0,
                         "survey_seconds": 2.0},
                        {"marker_id": "marker-b", "label": "B", "kind": "camp",
                         "wpos": [4.0, 0.0, 0.0], "arrival_radius": 4.0,
                         "survey_seconds": 2.0},
                    ],
                    "own_reports": list(own_reports),
                    "known_reports": list(known_reports),
                    "own_report_deliveries": [], "completed_rallies": [],
                    "nearby": nearby,
                    "active_lease": None,
                }

            scout_view = row(SCOUT_UID, own_reports=scout_reports)
            leader_view = row(LEADER_UID, known_reports=[{
                "marker_id": "marker-b", "report_id": "scout-report-b",
                "owner_uid": SCOUT_UID,
            }])
            for actor_uid, actor_view in ((SCOUT_UID, scout_view), (LEADER_UID, leader_view)):
                actor_view["_runner_observation_id"] = f"{actor_uid}:{now}"
            fake_global_only = [fact("known_report_from", "marker-a", SCOUT_UID, LEADER_UID)]
            return build_observations({SCOUT_UID: scout_view, LEADER_UID: leader_view},
                                      None, follower_uid, world_facts=fake_global_only)

        session = new_process_session([SCOUT_UID, LEADER_UID], goal_specs=[
            {"goal_id": "scout-surveys-a", "actor_uid": SCOUT_UID, "source": "ACTOR",
             "goals": [{"predicate": "survey_completed", "args": ["marker-a"]}]},
            {"goal_id": "leader-actor-rally-a", "actor_uid": LEADER_UID,
             "source": "ACTOR", "goals": [{"predicate": "rally_completed",
                                               "args": ["marker-a", follower_uid]}]},
        ])
        first_observations = views(10.0)
        first = step_process(session, first_observations, game_time=10.0)
        survey = next(row for row in first["decision"]["requests"]
                      if row["actor_uid"] == SCOUT_UID)
        self.assertEqual(survey["primitive"], "survey_marker")
        self.assertEqual(survey["args"], {"marker_id": "marker-a"})

        receipt = {"event": "g1_action_settled", "request_id": survey["request_id"],
                   "actor_uid": SCOUT_UID, "node_id": survey["node_id"],
                   "action": "survey_marker", "args": {"marker_id": "marker-a"},
                   "game_time": 11.0,
                   "effects": [{"predicate": "survey_completed", "args": ["marker-a"]},
                               {"predicate": "own_report", "args": ["marker-a"]}],
                   "source": "ACTOR", "goal_id": survey["goal_id"],
                   "author_version": None, "event_id": "prefix-survey-a"}
        after_prefix = step_process(first["session"], views(
            11.0, scout_reports=[{"marker_id": "marker-a", "report_id": "scout-report-a",
                                  "surveyed_at": 11.0}]), game_time=11.0, feedback=[receipt])
        prefix_event = '"event:g1_survey_completed"'
        self.assertIn(prefix_event, repr(after_prefix["session"]["native_history"]))

        schedule = _author_demo_schedule(["marker-a", "marker-b"], follower_uid, 10.0)
        own_a = [{"marker_id": "marker-a", "report_id": "scout-report-a",
                  "surveyed_at": 11.0}]
        appended = step_process(after_prefix["session"], views(12.0, scout_reports=own_a), game_time=12.0,
                                author_commands=[schedule[1]["command"]])
        # A global-only report claim cannot make actor A's Rally eligible or leak into its plan.
        self.assertFalse(any(request["source"] == "ACTOR"
                             and request["args"].get("marker_id") == "marker-a"
                             for request in appended["decision"]["requests"]),
                         repr(appended["decision"]["requests"]))
        edited = step_process(appended["session"], views(13.0, scout_reports=own_a), game_time=13.0,
                              author_commands=[schedule[2]["command"]])
        rally = next((request for request in edited["decision"]["requests"]
                      if request["primitive"] == "rally_marker"), None)
        self.assertIsNotNone(rally, repr(edited["decision"]))
        self.assertEqual(rally["source"], "DIRECTOR")
        self.assertEqual(rally["goal_id"], "g2-leader-rally-deadline")
        self.assertEqual(rally["author_version"], 2)
        self.assertEqual(rally["args"], {"marker_id": "marker-b", "follower_uid": follower_uid})
        self.assertIn(prefix_event, repr(edited["session"]["native_history"]))
        deadlines = [node["at"] for version in edited["session"]["author_obligations"][
            "g2-leader-rally-deadline"]["versions"] for node in
            [version["ast"]] if node.get("op") == "deadline"]
        self.assertEqual(deadlines, [250.0, 250.0])
        self.assertTrue(edited["decision"]["world_facts_used_only_for_author_monitor"])


if __name__ == "__main__":
    unittest.main()
