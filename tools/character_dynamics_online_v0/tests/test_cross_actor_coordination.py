from __future__ import annotations

import unittest

from tools.character_dynamics_online_v0.process_controller import (
    new_process_session, step_process,
)
from tools.character_dynamics_online_v0.process_runner import (
    LEADER_UID, SCOUT_UID, _actor_goal_specs, build_observations,
)
from tools.character_dynamics_online_v0.tests.test_process_core import (
    action as core_action, actor as core_actor, fact as core_fact,
    observations as core_observations,
)


FOLLOWER_UID = 450


def g1_view(actor_uid: int, now: float, *, marker_id: str,
            own_reports=(), known_reports=(), deliveries=()):
    other = LEADER_UID if actor_uid == SCOUT_UID else SCOUT_UID
    nearby = [{"uid": other, "wpos": [0.0, 0.0, 0.0], "distance": 3.0,
               "alive": True, "loaded": True, "hired_by_uid": None}]
    if actor_uid == LEADER_UID:
        nearby.append({"uid": FOLLOWER_UID, "wpos": [0.0, 0.0, 0.0],
                       "distance": 3.0, "alive": True, "loaded": True,
                       "hired_by_uid": LEADER_UID})
    return {"event": "g1_actor_view", "schema_version": 1,
            "rule_version": "recon-v1", "time": now, "actor_uid": actor_uid,
            "wpos": [0.0, 0.0, 0.0], "role": "pirate", "job": None,
            "mode": "simulated", "current_site": "camp", "home_site": "camp",
            "markers": [{"marker_id": marker_id, "label": marker_id,
                         "kind": "camp", "wpos": [1.0, 0.0, 0.0],
                         "arrival_radius": 4.0, "survey_seconds": 2.0}],
            "own_reports": list(own_reports), "known_reports": list(known_reports),
            "own_report_deliveries": list(deliveries), "completed_rallies": [],
            "nearby": nearby, "active_lease": None,
            "_runner_observation_id": f"{actor_uid}:{now}"}


def views(now, marker_id, *, scout_reports=(), leader_reports=(), deliveries=(),
          world_facts=()):
    return build_observations({
        SCOUT_UID: g1_view(SCOUT_UID, now, marker_id=marker_id,
                           own_reports=scout_reports),
        LEADER_UID: g1_view(LEADER_UID, now, marker_id=marker_id,
                            known_reports=leader_reports, deliveries=deliveries),
    }, None, FOLLOWER_UID, world_facts=world_facts)


def author_rally(marker_id: str, deadline: float = 100.0):
    return {"op": "append", "goal_id": "author-rally", "version": 1,
            "actor_uid": LEADER_UID, "ast": {"op": "deadline",
            "event": {"event": "g1_rally_completed",
                      "args": [LEADER_UID, marker_id, FOLLOWER_UID]},
            "at": deadline}}


def rally_actor_goal(marker_id: str):
    return [{"goal_id": "leader-rally", "actor_uid": LEADER_UID,
             "source": "ACTOR", "goals": [
                 {"predicate": "rally_completed", "args": [marker_id, FOLLOWER_UID]}]}]


class CrossActorCoordinationTests(unittest.TestCase):
    def test_missing_producer_view_does_not_release_authored_delivery_receiver(self):
        marker = "marker-b"
        session = new_process_session([SCOUT_UID, LEADER_UID],
                                      goal_specs=rally_actor_goal(marker))
        initial = views(10.0, marker, scout_reports=[{
            "marker_id": marker, "report_id": "native-report-b", "surveyed_at": 9.0}])
        first = step_process(session, initial, game_time=10.0,
                             author_commands=[author_rally(marker)])
        authored_delivery = next(row for row in first["decision"]["requests"]
                                 if row["actor_uid"] == SCOUT_UID
                                 and row["primitive"] == "deliver_report")
        actor_plan_key = f"{LEADER_UID}:ACTOR:leader-rally"
        self.assertIn(actor_plan_key, first["session"]["plans"])
        actor_plan_nodes = first["session"]["plans"][actor_plan_key]["nodes"]

        # The producer has no new view. The receiver's fresh view now makes
        # its ACTOR rally dispatchable, but the correlated authored delivery
        # still reserves that receiver until its terminal arrives.
        partial = views(11.0, marker)
        partial["actors"] = [row for row in partial["actors"]
                             if row["actor_uid"] == LEADER_UID]
        waiting = step_process(first["session"], partial, game_time=11.0,
                               available_actor_uids=[LEADER_UID])
        self.assertFalse(any(row["actor_uid"] == LEADER_UID
                             and row["primitive"] == "rally_marker"
                             for row in waiting["decision"]["requests"]))
        self.assertIn("AUTHOR_RECEIVER_RESERVED",
                      [row["code"] for row in waiting["decision"]["blocked"]])
        self.assertEqual(waiting["session"]["inflight_by_actor"][str(SCOUT_UID)]["request_id"],
                         authored_delivery["request_id"])
        self.assertEqual(waiting["session"]["plans"][actor_plan_key]["nodes"], actor_plan_nodes)

    def test_missing_leader_report_selects_real_scout_delivery_and_records_dependency(self):
        marker = "marker-b"
        observations = views(10.0, marker, scout_reports=[{
            "marker_id": marker, "report_id": "native-report-b", "surveyed_at": 9.0}])
        session = new_process_session([SCOUT_UID, LEADER_UID],
                                      goal_specs=rally_actor_goal(marker))
        result = step_process(session, observations, game_time=10.0,
                              author_commands=[author_rally(marker)])

        requests = result["decision"]["requests"]
        delivery = next(row for row in requests if row["primitive"] == "deliver_report")
        self.assertEqual(delivery["actor_uid"], SCOUT_UID)
        self.assertEqual(delivery["source"], "DIRECTOR")
        self.assertEqual(delivery["goal_id"], "author-rally")
        self.assertEqual(delivery["args"]["marker_id"], marker)
        self.assertEqual(delivery["args"]["receiver_uid"], LEADER_UID)
        self.assertFalse(any(row["primitive"] == "rally_marker" for row in requests))

        coordination = result["decision"]["author_coordination"]
        dependency = next(row for row in coordination["dependencies"]
                          if row["goal_id"] == "author-rally")
        self.assertEqual(dependency["consumer_actor_uid"], LEADER_UID)
        self.assertEqual(dependency["producer_actor_uid"], SCOUT_UID)
        self.assertEqual(dependency["fact"], {"predicate": "known_report_from",
                                               "args": [marker, SCOUT_UID, LEADER_UID]})
        repeated = step_process(result["session"], views(
            10.5, marker, scout_reports=[{"marker_id": marker,
                                          "report_id": "native-report-b",
                                          "surveyed_at": 9.0}]), game_time=10.5)
        self.assertFalse(any(row["primitive"] == "deliver_report"
                             and row["actor_uid"] == SCOUT_UID
                             for row in repeated["decision"]["requests"]))
        settled_delivery = {"event": "g1_action_settled",
                            "request_id": delivery["request_id"],
                            "actor_uid": delivery["actor_uid"],
                            "node_id": delivery["node_id"],
                            "action": delivery["primitive"], "args": delivery["args"],
                            "game_time": 11.0, "source": delivery["source"],
                            "goal_id": delivery["goal_id"],
                            "author_version": delivery["author_version"],
                            "event_id": "delivered-marker-b",
                            "effects": [
                                {"predicate": "report_delivered", "args": [marker, LEADER_UID]},
                                {"predicate": "report_known", "args": [marker, LEADER_UID]},
                                {"predicate": "event:g1_report_delivered",
                                 "args": [SCOUT_UID, marker, LEADER_UID]}]}
        post_delivery = step_process(repeated["session"], views(
            11.0, marker,
            scout_reports=[{"marker_id": marker, "report_id": "native-report-b",
                            "surveyed_at": 9.0}],
            leader_reports=[{"marker_id": marker, "report_id": "native-report-b",
                             "owner_uid": SCOUT_UID}],
            deliveries=[{"marker_id": marker, "report_id": "native-report-b",
                         "from_uid": SCOUT_UID,
                         "to_uid": LEADER_UID}]),
            game_time=11.0, feedback=[settled_delivery])
        rally = next(row for row in post_delivery["decision"]["requests"]
                     if row["primitive"] == "rally_marker")
        self.assertEqual(rally["actor_uid"], LEADER_UID)
        self.assertEqual(rally["args"]["marker_id"], marker)

    def test_world_monitor_fact_and_scout_prediction_do_not_make_leader_know_report(self):
        marker = "marker-a"
        session = new_process_session([SCOUT_UID, LEADER_UID],
                                      goal_specs=rally_actor_goal(marker))
        fake_world = [{"predicate": "known_report_from",
                       "args": [marker, SCOUT_UID, LEADER_UID], "value": True}]
        result = step_process(session, views(10.0, marker, scout_reports=[{
            "marker_id": marker, "report_id": "native-report-a", "surveyed_at": 9.0}],
            world_facts=fake_world), game_time=10.0,
            author_commands=[author_rally(marker)])
        self.assertFalse(any(row["primitive"] == "rally_marker"
                             and row["actor_uid"] == LEADER_UID
                             for row in result["decision"]["requests"]))

    def test_delivery_receipt_without_receiver_observation_waits_for_consumer_knowledge(self):
        marker = "marker-a"
        first = step_process(new_process_session([SCOUT_UID, LEADER_UID],
            goal_specs=rally_actor_goal(marker)),
            views(10.0, marker, scout_reports=[{"marker_id": marker,
                "report_id": "native-report-a", "surveyed_at": 9.0}]),
            game_time=10.0, author_commands=[author_rally(marker)])
        delivery = next(row for row in first["decision"]["requests"]
                        if row["primitive"] == "deliver_report")
        receipt = {"event": "g1_action_settled", "request_id": delivery["request_id"],
                   "actor_uid": delivery["actor_uid"], "node_id": delivery["node_id"],
                   "action": delivery["primitive"], "args": delivery["args"],
                   "game_time": 11.0, "effects": [
                       {"predicate": "report_delivered", "args": [marker, LEADER_UID]},
                       {"predicate": "known_report_from",
                        "args": [marker, SCOUT_UID, LEADER_UID]}],
                   "source": delivery["source"], "goal_id": delivery["goal_id"],
                   "author_version": delivery["author_version"],
                   "event_id": "delivery-without-fresh-leader-view"}
        # The receipt establishes a native delivery event, but the new leader
        # observation still contains no receiver-local knowledge.
        waiting = step_process(first["session"], views(11.0, marker, scout_reports=[{
            "marker_id": marker, "report_id": "native-report-a", "surveyed_at": 9.0}]),
            game_time=11.0, feedback=[receipt])
        self.assertFalse(any(row["primitive"] in {"deliver_report", "rally_marker"}
                             for row in waiting["decision"]["requests"]))

    def test_two_marker_author_requirements_share_one_producer_plan(self):
        markers = ["marker-a", "marker-b"]
        session = new_process_session([SCOUT_UID, LEADER_UID], goal_specs=[])
        scout = g1_view(SCOUT_UID, 10.0, marker_id=markers[0], own_reports=[
            {"marker_id": marker, "report_id": f"report-{marker}", "surveyed_at": 9.0}
            for marker in markers])
        leader = g1_view(LEADER_UID, 10.0, marker_id=markers[0])
        for marker in markers[1:]:
            template = {"marker_id": marker, "label": marker, "kind": "camp",
                        "wpos": [2.0, 0.0, 0.0], "arrival_radius": 4.0,
                        "survey_seconds": 2.0}
            scout["markers"].append(dict(template))
            leader["markers"].append(dict(template))
        goals = [
            {"op": "deadline", "event": {"event": "g1_rally_completed",
                "args": [LEADER_UID, marker, FOLLOWER_UID]}, "at": 100.0}
            for marker in markers]
        command = {"op": "append", "goal_id": "rally-both", "version": 1,
                   "actor_uid": LEADER_UID, "ast": {"op": "and", "children": goals}}
        observations = build_observations({SCOUT_UID: scout, LEADER_UID: leader},
                                          None, FOLLOWER_UID)
        result = step_process(session, observations, game_time=10.0,
                              author_commands=[command])
        dependencies = result["decision"]["author_coordination"]["dependencies"]
        self.assertEqual({item["fact"]["args"][0] for item in dependencies}, set(markers))
        scout_plans = [plan for plan in result["decision"]["plans"]
                       if plan["plan_key"].startswith(f"{SCOUT_UID}:DIRECTOR:rally-both:v1")]
        self.assertEqual(len(scout_plans), 1)
        delivery_nodes = [node for node in scout_plans[0]["nodes"]
                          if node["primitive"] == "deliver_report"]
        self.assertEqual({node["args"]["marker_id"] for node in delivery_nodes}, set(markers))

    def test_edit_preserves_v1_inflight_invalidates_its_tail_and_expires_v2(self):
        markers = ["marker-a", "marker-b", "marker-c", "marker-d"]
        scout = g1_view(SCOUT_UID, 10.0, marker_id=markers[0], own_reports=[
            {"marker_id": marker, "report_id": f"report-{marker}", "surveyed_at": 9.0}
            for marker in markers[:3]])
        leader = g1_view(LEADER_UID, 10.0, marker_id=markers[0])
        for index, marker in enumerate(markers[1:], start=1):
            template = {"marker_id": marker, "label": marker, "kind": "camp",
                        "wpos": [float(index + 1), 0.0, 0.0],
                        "arrival_radius": 4.0, "survey_seconds": 2.0}
            scout["markers"].append(dict(template))
            leader["markers"].append(dict(template))
        session = new_process_session([SCOUT_UID, LEADER_UID], goal_specs=[{
            "goal_id": "scout-still-has-work", "actor_uid": SCOUT_UID,
            "source": "ACTOR", "goals": [
                {"predicate": "survey_completed", "args": [markers[3]]}]}])
        initial_observations = build_observations(
            {SCOUT_UID: scout, LEADER_UID: leader}, None, FOLLOWER_UID)
        v1 = {"op": "append", "goal_id": "author-rally", "version": 1,
              "actor_uid": LEADER_UID, "ast": {"op": "and", "children": [
                  {"op": "deadline", "event": {"event": "g1_rally_completed",
                   "args": [LEADER_UID, marker, FOLLOWER_UID]}, "at": 12.0}
                  for marker in markers[1:3]]}}
        first = step_process(session, initial_observations, game_time=10.0,
                             author_commands=[v1])
        original = next(row for row in first["decision"]["requests"]
                        if row["primitive"] == "deliver_report")
        self.assertEqual(original["args"]["marker_id"], markers[1])
        self.assertEqual(original["author_version"], 1)

        scout_edit = g1_view(SCOUT_UID, 11.0, marker_id=markers[0], own_reports=[
            {"marker_id": marker, "report_id": f"report-{marker}", "surveyed_at": 9.0}
            for marker in markers[:3]])
        leader_edit = g1_view(LEADER_UID, 11.0, marker_id=markers[0])
        scout_edit["markers"].extend(dict(row) for row in scout["markers"][1:])
        leader_edit["markers"].extend(dict(row) for row in leader["markers"][1:])
        edit_observations = build_observations(
            {SCOUT_UID: scout_edit, LEADER_UID: leader_edit}, None, FOLLOWER_UID)
        edit = {"op": "edit", "goal_id": "author-rally", "version": 2,
                "actor_uid": LEADER_UID, "ast": {"op": "and", "children": [
                    {"op": "deadline", "event": {"event": "g1_rally_completed",
                     "args": [LEADER_UID, marker, FOLLOWER_UID]}, "at": 12.0}
                    for marker in (markers[0], markers[2])]}}
        edited = step_process(first["session"], edit_observations, game_time=11.0,
                              author_commands=[edit])
        inflight = edited["session"]["inflight_by_actor"][str(SCOUT_UID)]
        self.assertEqual(inflight["request_id"], original["request_id"])
        self.assertEqual(inflight["node_id"], original["node_id"])
        self.assertEqual(len(edited["session"]["history"]),
                         len(first["session"]["history"]) + 1)
        self.assertFalse(any(row["primitive"] == "deliver_report"
                             and row["args"]["marker_id"] == markers[0]
                             for row in edited["decision"]["requests"]))
        old_key = f"{LEADER_UID}:DIRECTOR:author-rally:v1"
        old_plan = edited["session"]["plans"][old_key]
        producer_key = f"{SCOUT_UID}:DIRECTOR:author-rally:v1"
        old_producer_plan = edited["session"]["plans"][producer_key]
        self.assertTrue(any(node["primitive"] == "deliver_report"
                            and node["args"]["marker_id"] == markers[1]
                            and node["status"] == "pending"
                            for node in old_producer_plan["nodes"]),
                        repr(old_producer_plan))
        self.assertTrue(any(node["primitive"] == "deliver_report"
                            and node["args"]["marker_id"] == markers[2]
                            and node["status"] == "invalidated"
                            for node in old_producer_plan["nodes"]))
        self.assertFalse(any(node["primitive"] == "rally_marker"
                             and node["status"] in {"planned", "requested", "in_flight"}
                             for node in old_plan["nodes"]))

        settled = {"event": "g1_action_settled", "request_id": original["request_id"],
                   "actor_uid": original["actor_uid"], "node_id": original["node_id"],
                   "action": original["primitive"], "args": original["args"],
                   "game_time": 13.0,
                   "effects": [{"predicate": "report_delivered",
                                "args": [markers[1], LEADER_UID]},
                               {"predicate": "known_report_from",
                                "args": [markers[1], SCOUT_UID, LEADER_UID]},
                               {"predicate": "event:g1_report_delivered",
                                "args": [SCOUT_UID, markers[1], LEADER_UID]}],
                   "source": original["source"], "goal_id": original["goal_id"],
                   "author_version": original["author_version"],
                   "event_id": "v1-delivery-settled-after-edit"}
        scout_final = g1_view(SCOUT_UID, 101.0, marker_id=markers[0], own_reports=[
            {"marker_id": marker, "report_id": f"report-{marker}", "surveyed_at": 9.0}
            for marker in markers[:3]])
        leader_final = g1_view(LEADER_UID, 101.0, marker_id=markers[0], known_reports=[{
            "marker_id": markers[1], "report_id": f"report-{markers[1]}",
            "owner_uid": SCOUT_UID}], deliveries=[{
            "marker_id": markers[1], "report_id": f"report-{markers[1]}",
            "from_uid": SCOUT_UID, "to_uid": LEADER_UID}])
        scout_final["markers"].extend(dict(row) for row in scout["markers"][1:])
        leader_final["markers"].extend(dict(row) for row in leader["markers"][1:])
        final_observations = build_observations(
            {SCOUT_UID: scout_final, LEADER_UID: leader_final}, None, FOLLOWER_UID)
        after_deadline = step_process(edited["session"], final_observations,
                                      game_time=101.0, feedback=[dict(settled, game_time=101.0)])
        self.assertTrue(any(row.get("receipt", {}).get("event_id") ==
                            "v1-delivery-settled-after-edit"
                            for row in after_deadline["session"]["native_history"]))
        self.assertFalse(any(row["primitive"] == "deliver_report"
                             and row["args"]["marker_id"] == markers[0]
                             and row["author_version"] == 2
                             for row in after_deadline["decision"]["requests"]))
        self.assertTrue(any(row["code"] == "AUTHOR_GOAL_EXPIRED"
                            and row["goal_id"] == "author-rally"
                            for row in after_deadline["decision"]["blocked"]))
        actor_request = next(row for row in after_deadline["decision"]["requests"]
                             if row["source"] == "ACTOR")
        self.assertEqual(actor_request["primitive"], "survey_marker")
        self.assertEqual(actor_request["args"]["marker_id"], markers[3])

    def test_two_pending_reports_replan_to_requested_actor_action_on_next_tick(self):
        goals = [
            {"goal_id": "scout-a", "actor_uid": SCOUT_UID, "source": "ACTOR",
             "goals": [{"predicate": "survey_completed", "args": ["marker-a"]}]},
            {"goal_id": "scout-b", "actor_uid": SCOUT_UID, "source": "ACTOR",
             "goals": [{"predicate": "survey_completed", "args": ["marker-b"]}]},
        ]
        session = new_process_session([SCOUT_UID, LEADER_UID], goal_specs=goals)
        # Runner projection contains the real two marker models, avoiding a synthetic action.
        scout = g1_view(SCOUT_UID, 10.0, marker_id="marker-a")
        scout["markers"].append({"marker_id": "marker-b", "label": "B", "kind": "camp",
                                 "wpos": [2.0, 0.0, 0.0], "arrival_radius": 4.0,
                                 "survey_seconds": 2.0})
        leader = g1_view(LEADER_UID, 10.0, marker_id="marker-a")
        leader["markers"].append(dict(scout["markers"][1]))
        observation = build_observations({SCOUT_UID: scout, LEADER_UID: leader},
                                         None, FOLLOWER_UID)
        first = step_process(session, observation, game_time=10.0)
        first_survey = next(row for row in first["decision"]["requests"]
                            if row["actor_uid"] == SCOUT_UID)
        self.assertEqual(first_survey["primitive"], "survey_marker")
        self.assertEqual(first_survey["args"]["marker_id"], "marker-a")
        receipt = {"event": "g1_action_settled", "request_id": first_survey["request_id"],
                   "actor_uid": SCOUT_UID, "node_id": first_survey["node_id"],
                   "action": "survey_marker", "args": first_survey["args"],
                   "game_time": 10.5, "effects": [
                       {"predicate": "survey_completed", "args": ["marker-a"]}],
                   "source": "ACTOR", "goal_id": first_survey["goal_id"],
                   "author_version": None, "event_id": "survey-a-settled"}
        # The actor observation settles A; the next still-pending task is B.
        scout_fresh = g1_view(SCOUT_UID, 11.0, marker_id="marker-a")
        leader_fresh = g1_view(LEADER_UID, 11.0, marker_id="marker-a")
        scout_fresh["markers"].append(dict(scout["markers"][1]))
        leader_fresh["markers"].append(dict(leader["markers"][1]))
        fresh = build_observations({SCOUT_UID: scout_fresh, LEADER_UID: leader_fresh},
                                   None, FOLLOWER_UID)
        for row in fresh["actors"]:
            row["observation_id"] = f"{row['actor_uid']}:11"
            if row["actor_uid"] == SCOUT_UID:
                row["facts"].append({"predicate": "survey_completed",
                                     "args": ["marker-a"], "value": True})
        second = step_process(first["session"], fresh, game_time=11.0, feedback=[receipt])
        next_rows = [row for row in second["decision"]["requests"]
                     if row["actor_uid"] == SCOUT_UID]
        self.assertTrue(next_rows, repr(second["decision"]))
        next_action = next_rows[0]
        self.assertEqual(next_action["primitive"], "survey_marker")
        self.assertEqual(next_action["args"]["marker_id"], "marker-b")

    def test_author_goal_changes_real_delivery_choice_with_director_enabled(self):
        markers = ("marker-a", "marker-b")
        scout = g1_view(SCOUT_UID, 10.0, marker_id=markers[0], own_reports=[
            {"marker_id": marker, "report_id": f"report-{marker}",
             "surveyed_at": 9.0} for marker in markers])
        leader = g1_view(LEADER_UID, 10.0, marker_id=markers[0])
        template = {"marker_id": markers[1], "label": markers[1], "kind": "camp",
                    "wpos": [2.0, 0.0, 0.0], "arrival_radius": 4.0,
                    "survey_seconds": 2.0}
        scout["markers"].append(dict(template))
        leader["markers"].append(dict(template))
        observations = build_observations(
            {SCOUT_UID: scout, LEADER_UID: leader}, None, FOLLOWER_UID)
        actor_goals = _actor_goal_specs(markers, FOLLOWER_UID)
        command = author_rally(markers[1])
        off = step_process(new_process_session(
            [SCOUT_UID, LEADER_UID], goal_specs=actor_goals,
            director_enabled=False), observations, game_time=10.0,
            author_commands=[command])
        on = step_process(new_process_session(
            [SCOUT_UID, LEADER_UID], goal_specs=actor_goals,
            director_enabled=True), observations, game_time=10.0,
            author_commands=[command])
        off_request = next(row for row in off["decision"]["requests"]
                           if row["actor_uid"] == SCOUT_UID)
        on_request = next(row for row in on["decision"]["requests"]
                          if row["actor_uid"] == SCOUT_UID)
        self.assertEqual((off_request["source"], off_request["primitive"],
                          off_request["args"]["marker_id"]),
                         ("ACTOR", "deliver_report", markers[0]))
        self.assertEqual((on_request["source"], on_request["primitive"],
                          on_request["args"]["marker_id"]),
                         ("DIRECTOR", "deliver_report", markers[1]))

    def test_director_disabled_preserves_actor_progress_without_author_dispatch(self):
        marker = "marker-b"
        session = new_process_session([SCOUT_UID, LEADER_UID],
            goal_specs=[{"goal_id": "scout-survey", "actor_uid": SCOUT_UID,
                         "source": "ACTOR", "goals": [
                             {"predicate": "survey_completed", "args": [marker]}]}],
            director_enabled=False)
        observations = views(10.0, marker)
        result = step_process(session, observations, game_time=10.0,
                              author_commands=[author_rally(marker)])
        self.assertTrue(any(row["source"] == "ACTOR" and row["actor_uid"] == SCOUT_UID
                            for row in result["decision"]["requests"]))
        self.assertFalse(any(row["source"] in {"AUTHOR", "DIRECTOR"}
                             for row in result["decision"]["requests"]))
        self.assertEqual(result["decision"]["author_coordination"], {"dependencies": []})

    def test_speech_failure_cooldown_edges_and_real_contact_gate(self):
        delivery = core_action("deliver_report", {"marker_id": "marker-a",
                                                  "receiver_uid": 20},
            [{"predicate": "own_report", "args": ["marker-a"]}],
            [{"predicate": "report_delivered", "args": ["marker-a", 20]},
             {"predicate": "event:g1_report_delivered", "args": [10, "marker-a", 20]}],
            dispatch_preconditions=[{"predicate": "receiver_contact", "args": [20]}])
        session = new_process_session([10], goal_specs=[{
            "goal_id": "deliver-a", "actor_uid": 10, "source": "ACTOR",
            "goals": [{"predicate": "report_delivered", "args": ["marker-a", 20]}]}])

        def obs(now, contact, observation_id=None):
            facts = [core_fact("own_report", "marker-a")]
            if contact:
                facts.append(core_fact("receiver_contact", 20))
            return core_observations(now, [core_actor(10, observation_id or f"obs-{now}",
                                                       facts, [delivery])])

        first = step_process(session, obs(1.0, True), game_time=1.0)
        initial = first["decision"]["requests"][0]
        self.assertEqual(initial["primitive"], "deliver_report")
        failed = {"event": "g1_action_failed", "request_id": initial["request_id"],
                  "actor_uid": 10, "node_id": initial["node_id"],
                  "action": initial["primitive"], "args": initial["args"],
                  "game_time": 2.0, "reason": "native_talk_completed_without_speech",
                  "effects": [], "source": initial["source"],
                  "goal_id": initial["goal_id"], "author_version": initial["author_version"],
                  "event_id": "speech-missing-1"}
        after_failure = step_process(first["session"], obs(2.0, True), game_time=2.0,
                                     feedback=[failed])

        at_149 = step_process(after_failure["session"], obs(16.9, True), game_time=16.9)
        self.assertFalse(at_149["decision"]["requests"])
        self.assertTrue(any(row["code"] == "ACTION_RETRY_COOLDOWN"
                            for row in at_149["decision"]["blocked"]),
                        repr(at_149["decision"]))

        at_15_without_contact = step_process(at_149["session"], obs(17.0, False),
                                             game_time=17.0)
        self.assertFalse(at_15_without_contact["decision"]["requests"])
        self.assertFalse(any(row["code"] == "ACTION_RETRY_COOLDOWN"
                             for row in at_15_without_contact["decision"]["blocked"]))

        at_15_with_contact = step_process(at_15_without_contact["session"],
                                          obs(17.0, True, "obs-17.0-contact-restored"),
                                          game_time=17.0)
        second_attempt = at_15_with_contact["decision"]["requests"][0]
        self.assertEqual(second_attempt["primitive"], "deliver_report")
        self.assertEqual(second_attempt["source"], "ACTOR")
        failed_again = {"event": "g1_action_failed", "request_id": second_attempt["request_id"],
                        "actor_uid": 10, "node_id": second_attempt["node_id"],
                        "action": second_attempt["primitive"], "args": second_attempt["args"],
                        "game_time": 18.0, "reason": "native_talk_completed_without_speech",
                        "effects": [], "source": second_attempt["source"],
                        "goal_id": second_attempt["goal_id"],
                        "author_version": second_attempt["author_version"],
                        "event_id": "speech-missing-2"}
        after_second_failure = step_process(at_15_with_contact["session"], obs(18.0, True),
                                            game_time=18.0, feedback=[failed_again])
        author_delivery = {"op": "append", "goal_id": "author-delivery", "version": 1,
                           "actor_uid": 10, "ast": {"op": "deadline",
                           "event": {"event": "g1_report_delivered",
                                     "args": [10, "marker-a", 20]}, "at": 100.0}}
        third_tick = step_process(after_second_failure["session"],
                                  obs(33.0, True, "obs-33-author"), game_time=33.0,
                                  author_commands=[author_delivery])
        third_attempt = next(row for row in third_tick["decision"]["requests"]
                             if row["primitive"] == "deliver_report")
        self.assertEqual(third_attempt["source"], "DIRECTOR")
        failed_third = {"event": "g1_action_failed", "request_id": third_attempt["request_id"],
                        "actor_uid": 10, "node_id": third_attempt["node_id"],
                        "action": third_attempt["primitive"], "args": third_attempt["args"],
                        "game_time": 34.0, "reason": "receiver_not_nearby", "effects": [],
                        "source": third_attempt["source"], "goal_id": third_attempt["goal_id"],
                        "author_version": third_attempt["author_version"],
                        "event_id": "third-attempt-failed"}
        after_third_failure = step_process(third_tick["session"], obs(34.0, False),
                                           game_time=34.0, feedback=[failed_third])
        fourth = step_process(after_third_failure["session"], obs(35.0, True), game_time=35.0)
        self.assertFalse(fourth["decision"]["requests"])
        self.assertTrue(any(row["code"] == "ACTION_RETRY_LIMIT"
                            for row in fourth["decision"]["blocked"]))


if __name__ == "__main__":
    unittest.main()
