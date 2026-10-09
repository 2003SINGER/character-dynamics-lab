import unittest
import json
from pathlib import Path
from copy import deepcopy
from unittest.mock import patch

from tools.e1_keyledger_v0.executor import scheduled_actor
from tools.e1_keyledger_v0.policy import choose_b
from tools.npc_system_v0.author import monitor, requirements
from tools.npc_system_v0.executor import Executor, intent, validate_evidence
from tools.npc_system_v0.model import (ContextDriveV0, MonotoneAvoidanceV0, actor_view,
                                     consume_boundary, goal_choice, initial_checkpoint, transition)
from tools.npc_system_v0.planners import propose
from tools.npc_system_v0.system import System, digest
from trajectory_constraints_v0.ast import ast_from_json


class IntegrationTests(unittest.TestCase):
    def system(self, policy="KEEP", planner="goap", director=True, **kwargs):
        return System(initial_checkpoint(policy, **kwargs), ContextDriveV0(), planner, director)

    def status(self, result, name="ledger-event"):
        return next(v["status"] for v in result["author_verdicts"] if v["id"] == name)

    def test_director_only_changes_opportunity_actors_still_decide(self):
        result = self.system().run()
        self.assertEqual(self.status(result), "SATISFIED")
        actions = [r["intent"] for r in result["trace"]]
        self.assertEqual([a["operator"] for a in actions[:7]],
                         ["publish_incentive", "request_tool", "offer_loan", "choose_accept",
                          "accept_loan", "unlock", "take_ledger"])
        self.assertEqual([a["actor"] for a in actions[:7]], ["DIRECTOR", "B", "A", "B", "B", "A", "A"])
        self.assertEqual(result["checkpoint"]["W"]["director_resources"], 0)
        self.assertEqual(result["checkpoint"]["characters"]["A"]["commitment"]["status"], "COMPLETED")
        self.assertTrue(all(v["status"] == "SATISFIED" for v in result["author_verdicts"]))

    def test_htn_is_real_backend_not_goap_alias(self):
        with patch("tools.npc_system_v0.planners.uniform_cost_search", side_effect=AssertionError("GOAP called")):
            result = self.system(planner="htn").run()
        self.assertEqual(self.status(result), "SATISFIED")
        proposals = [r["decision"].get("proposal", {}) for r in result["trace"] if r["decision"]]
        self.assertTrue(any(p.get("implementation") == "GTPyhop-2.0.2" for p in proposals))

    def test_no_director_preserves_own_daily_life(self):
        result = self.system(director=False).run()
        self.assertEqual(self.status(result), "VIOLATED")
        self.assertFalse(result["director_proposals"])
        for who in ("A", "B"):
            self.assertGreater(result["checkpoint"]["characters"][who]["work_units"], 0)
        self.assertTrue(result["checkpoint"]["O"]["B"]["request_sent"])

    def test_pay_policy_does_not_require_director(self):
        result = self.system("PAY", director=False).run()
        self.assertEqual(self.status(result), "SATISFIED")
        self.assertEqual(result["checkpoint"]["characters"]["A"]["commitment"]["started_at"], 2)

    def test_player_history_is_not_rewritten(self):
        system = self.system()
        initial_events = system.executor.checkpoint()["events"]
        result = system.run(player_at=3)
        cp = result["checkpoint"]
        self.assertEqual(self.status(result), "VIOLATED")
        self.assertFalse(cp["W"]["intact"]["key1"])
        self.assertEqual(cp["events"][:len(initial_events)], initial_events)
        self.assertEqual(len([e for e in cp["events"] if e["event_type"] == "player_key_destroyed"]), 1)
        self.assertIsNone(cp["W"]["holders"]["key1"])

    def test_unauthorized_private_state_and_npc_force_rejected(self):
        system = self.system()
        before = system.executor.checkpoint()
        for action in (intent("set_stress", "DIRECTOR", target="A", value=0),
                       intent("choose_accept", "DIRECTOR", offer_id="fake"),
                       intent("publish_incentive", "PLAYER", bonus=2),
                       intent("publish_incentive", "DIRECTOR", bonus=200)):
            receipt = system.executor.start(action)
            self.assertFalse(receipt["accepted"])
        cp = system.executor.checkpoint()
        for key in ("W", "O", "characters", "clock", "events", "seals"):
            self.assertEqual(cp[key], before[key])

    def test_start_does_not_advance_clock_or_apply_effect(self):
        executor = self.system().executor
        receipt = executor.start(intent("publish_incentive", "DIRECTOR", bonus=2))
        self.assertTrue(receipt["accepted"])
        self.assertEqual(executor.checkpoint()["clock"]["now"], 2)
        self.assertEqual(executor.checkpoint()["W"]["loan_bonus"], 0)
        busy = executor.start(intent("rest", "B"))
        self.assertFalse(busy["accepted"])
        executor.advance_minute(receipt["action_id"])
        self.assertEqual(executor.checkpoint()["clock"]["now"], 3)
        self.assertEqual(executor.checkpoint()["W"]["loan_bonus"], 2)

    def test_world_action_keeps_pending_b_slot(self):
        executor = self.system().executor
        executor.execute(intent("publish_incentive", "DIRECTOR", bonus=2))
        self.assertEqual(scheduled_actor(executor.checkpoint()), "B")

    def test_forecast_does_not_mutate_real_world(self):
        system = self.system()
        before = digest(system.executor.checkpoint())
        proposal, record = system.world_proposal()
        self.assertIsNotNone(proposal)
        self.assertEqual(digest(system.executor.checkpoint()), before)
        self.assertTrue(all(e["prediction_only"] for e in record["candidate_evaluations"]))
        self.assertFalse(record["guarantee"])
        self.assertEqual(system.verdicts()[0]["status"], "PENDING")

    def test_forecast_budget_is_not_impossibility(self):
        system = self.system()
        system.forecast_steps = 0
        action, record = system.world_proposal()
        self.assertIsNone(action)
        self.assertEqual(record["status"], "BUDGET_NO_INTERVENTION")
        self.assertTrue(all(e["status"] == "BUDGET" for e in record["candidate_evaluations"]))

    def test_no_resources_no_intervention(self):
        result = self.system(resources=0).run()
        self.assertEqual(self.status(result), "VIOLATED")
        self.assertFalse(any(r["intent"]["actor"] == "DIRECTOR" for r in result["trace"]))

    def test_absolute_author_deadline_does_not_slide(self):
        system = self.system()
        system.constraints = requirements(8)
        original = system.constraints
        result = system.run()
        self.assertEqual(self.status(result), "VIOLATED")
        self.assertEqual(system.constraints, original)
        self.assertEqual(system.constraints[0].window.end, 8)

    def test_actor_view_excludes_hidden_world_other_state_and_author(self):
        cp = initial_checkpoint()
        one = actor_view(cp, "A")
        cp["W"]["locations"]["B"] = "HIDDEN"
        cp["characters"]["B"]["S"]["stress"] = 1
        cp["O"]["B"]["known_facts"].append("secret")
        self.assertEqual(actor_view(cp, "A"), one)
        self.assertNotIn("W", one)

    def test_observed_incentive_changes_own_b_choice(self):
        system = self.system()
        system.execute(intent("publish_incentive", "DIRECTOR", bonus=2))
        system.actor_step()
        system.actor_step()
        cp = system.executor.checkpoint()
        view = actor_view(cp, "B")
        self.assertEqual(choose_b(view)["operator"], "choose_accept")
        unincentivized = deepcopy(view)
        unincentivized["contract"]["c"] += 2
        self.assertEqual(choose_b(unincentivized)["operator"], "choose_decline")

    def test_context_curve_not_monotone_and_overload_recovers(self):
        model = ContextDriveV0()
        choices = []
        for stress in (0, .5, .95):
            view = actor_view(initial_checkpoint("PAY", stress=stress), "A")
            choices.append(goal_choice(view, model)["goal"])
        self.assertEqual(choices, ["daily_work", "committed_task", "recover"])
        result = self.system("PAY", director=False, stress=.95).run()
        self.assertTrue(any(r["intent"]["operator"] == "rest" for r in result["trace"]))
        self.assertEqual(self.status(result), "SATISFIED")

    def test_dynamics_substitution_changes_behavior(self):
        cp = initial_checkpoint("PAY")
        one = System(cp, ContextDriveV0(), director=False).run()
        two = System(cp, MonotoneAvoidanceV0(), director=False).run()
        self.assertEqual(self.status(one), "SATISFIED")
        self.assertEqual(self.status(two), "VIOLATED")

    def test_world_completion_without_own_feedback_keeps_commitment(self):
        cp = initial_checkpoint()
        cp["W"]["holders"]["ledger"] = "A"
        consume_boundary(cp, ContextDriveV0())
        self.assertEqual(cp["world_tasks"]["ledger"]["progress"], 1)
        self.assertEqual(cp["characters"]["A"]["commitment"]["status"], "ACTIVE")

    def test_commitment_started_at_survives_suspend_resume(self):
        char = initial_checkpoint()["characters"]["A"]
        transition(char, "SUSPENDED", 3, "rest")
        transition(char, "ACTIVE", 4, "new viable proposal")
        self.assertEqual(char["commitment"]["started_at"], 2)
        self.assertEqual(len(char["commitment"]["transitions"]), 2)

    def test_budgets_do_not_silently_fallback_to_other_planner(self):
        view = actor_view(initial_checkpoint("PAY"), "A")
        for name in ("goap", "htn"):
            self.assertEqual(propose(view, name, max_expansions=0)["solve_status"], "BUDGET")
        with self.assertRaises(ValueError):
            propose(view, "fictional")

    def test_symbolic_future_binding_cannot_be_dispatched(self):
        view = actor_view(initial_checkpoint("PAY"), "A")
        for name in ("goap", "htn"):
            result = propose(view, name)
            self.assertEqual(result["selected_action"]["operator"], "offer_loan")
            self.assertIsInstance(next(a for a in result["forecast_plan"] if a["operator"] == "unlock")["args"]["item"], dict)
        executor = self.system("PAY").executor
        self.assertFalse(executor.start(intent("unlock", "A", item={"symbol": "LoanKey"}))["accepted"])

    def test_receipt_and_world_tampering_are_rejected(self):
        cp = self.system().run()["checkpoint"]
        variants = []
        changed = deepcopy(cp)
        changed["W"]["director_resources"] = 2
        variants.append(changed)
        changed = deepcopy(cp)
        changed["events"][1]["typed_args"]["bonus"] = 3
        variants.append(changed)
        changed = deepcopy(cp)
        changed["receipts"][1]["intent"]["actor"] = "PLAYER"
        variants.append(changed)
        changed = deepcopy(cp)
        changed["events"].append(deepcopy(changed["events"][-1]))
        variants.append(changed)
        for cp in variants:
            with self.assertRaises(ValueError):
                validate_evidence(cp)

    def test_history_seals_remain_exact_old_prefix(self):
        system = self.system()
        old = system.executor.checkpoint()["seals"]
        system.execute(intent("publish_incentive", "DIRECTOR", bonus=2))
        self.assertEqual(system.executor.checkpoint()["seals"][:len(old)], old)

    def test_appraisal_is_inspectable_and_receipt_linked(self):
        result = self.system("PAY", director=False).run()
        cp = result["checkpoint"]
        observed = {e["event_id"] for e in cp["O"]["A"]["known_events"]}
        for x in cp["characters"]["A"]["X_history"]:
            self.assertTrue(set(x["evidence_ids"]) <= observed)
            self.assertEqual(x["version"], ContextDriveV0.version)

    def test_missing_snapshot_at_author_point_is_unknown_not_satisfied(self):
        system = self.system("PAY", director=False)
        system.run()
        snapshots = [s for s in system.snapshots if s["clock"]["now"] != 8]
        results = monitor(snapshots, requirements(8), ContextDriveV0.version)
        point = next(r for r in results if r["id"] == "final-holding-point")
        self.assertEqual(point["status"], "INDETERMINATE")

    def test_finished_commitment_is_not_reopened_by_daily_rest(self):
        char = initial_checkpoint()["characters"]["A"]
        transition(char, "COMPLETED", 5, "observed completion")
        transition(char, "SUSPENDED", 6, "daily recovery")
        self.assertEqual(char["commitment"]["status"], "COMPLETED")

    def test_long_action_uses_one_clock_and_every_boundary_updates_state(self):
        cp = initial_checkpoint("PAY")
        cp["config_pins"]["unlock_duration"] = 3
        result = System(cp, ContextDriveV0(), director=False).run()
        self.assertEqual(self.status(result), "SATISFIED")
        self.assertEqual([s["clock"]["now"] for s in result["snapshots"]], list(range(2, 11)))
        self.assertTrue(all(s["clock"]["now"] == s["W"]["t"] for s in result["snapshots"]))
        unlock = next(r for r in result["trace"] if r["intent"]["operator"] == "unlock")
        self.assertEqual(unlock["end_time"] - unlock["start_time"], 3)
        self.assertEqual(len(result["checkpoint"]["characters"]["A"]["X_history"]), 8)

    def test_unreceipted_bonus_and_rolled_back_destruction_rejected(self):
        cp = initial_checkpoint()
        cp["O"]["A"]["loan_bonus"] = 2
        with self.assertRaises(ValueError):
            validate_evidence(cp)
        cp = self.system().run(player_at=3)["checkpoint"]
        cp["W"]["intact"]["key1"] = True
        with self.assertRaises(ValueError):
            validate_evidence(cp)

    def test_noop_wins_equal_score_and_incentive_is_not_repeated(self):
        system = self.system("PAY")
        action, _ = system.world_proposal()
        self.assertIsNone(action)
        other = self.system()
        other.execute(intent("publish_incentive", "DIRECTOR", bonus=2))
        self.assertFalse(other.executor.start(intent("publish_incentive", "DIRECTOR", bonus=2))["accepted"])

    def test_author_json_multilevel_bundle_is_executable(self):
        path = Path(__file__).parents[1] / "examples" / "author.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        constraints = [ast_from_json(c) for level in document["levels"] for c in level["constraints"]]
        system = System(initial_checkpoint(), ContextDriveV0(), constraints=constraints)
        result = system.run()
        self.assertEqual(self.status(result), "SATISFIED")
        self.assertTrue(all(v["status"] == "SATISFIED" for v in result["author_verdicts"]))
        with self.assertRaises(ValueError):
            System(initial_checkpoint(), ContextDriveV0(), constraints=[constraints[0], constraints[0]])

    def test_pressure_appraisal_is_an_actual_updater_input(self):
        model = ContextDriveV0()
        state = {"stress": .3, "fatigue": .1}
        x = {"deadline_pressure": 0, "obstruction": False, "recovery": False}
        low = model.update(state, x, 1)
        x["deadline_pressure"] = 1
        high = model.update(state, x, 1)
        self.assertGreater(high["stress"], low["stress"])

    def test_resume_running_action_continues_without_new_action_or_restart(self):
        system = self.system("PAY", director=False)
        for _ in range(4):
            system.actor_step()
        system.executor._c["config_pins"]["unlock_duration"] = 3
        receipt = system.executor.start(intent("unlock", "A", item="key1"))
        self.assertTrue(receipt["accepted"])
        system.executor.advance_minute(receipt["action_id"])
        cp = system.executor.checkpoint()
        resumed = System(cp, ContextDriveV0(), director=False)
        resumed.actor_step()
        after = resumed.executor.checkpoint()
        unlocks = [r for r in after["receipts"] if r["intent"]["operator"] == "unlock"]
        self.assertEqual(len(unlocks), 1)
        self.assertEqual(unlocks[0]["status"], "SUCCESS")
        self.assertEqual([r["control"] for r in after["minute_history"][-2:]], ["NO_CONTROL", "NO_CONTROL"])

    def test_unknown_hard_constraint_forecast_is_not_optimized_as_zero_loss(self):
        original = self.system()
        original.actor_step()
        resumed = System(original.executor.checkpoint(), ContextDriveV0())
        action, record = resumed.world_proposal()
        self.assertIsNone(action)
        self.assertEqual(record["status"], "UNKNOWN_NO_INTERVENTION")
        self.assertTrue(all(e["status"] == "INDETERMINATE" for e in record["candidate_evaluations"]))


if __name__ == "__main__":
    unittest.main()
