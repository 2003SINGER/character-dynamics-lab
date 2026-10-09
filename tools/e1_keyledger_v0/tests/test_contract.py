import copy
import unittest

from tools.e1_keyledger_v0.executor import Executor
from tools.e1_keyledger_v0.fixtures import initial_checkpoint
from tools.e1_keyledger_v0.monitor_bridge import MonitorContractError, validate_e1_evidence
from tools.e1_keyledger_v0.monitor_bridge import evaluate_goal
from tools.e1_keyledger_v0.planner import restore_budget, snapshot_budget, uniform_cost_search
from tools.e1_keyledger_v0.policy import actor_view, choose_b
from tools.e1_keyledger_v0.runner import run_case


def run_one(executor, action):
    receipt = executor.execute(action)
    if receipt.get("status") != "SUCCESS":
        raise AssertionError(receipt)
    return receipt


class E1ContractTests(unittest.TestCase):
    def test_request_receipt_projects_only_after_success(self):
        cp = initial_checkpoint("unknown", "PAY", 8)
        executor = Executor(cp)
        action = choose_b(actor_view(cp, "B"))
        receipt = run_one(executor, action)
        out = executor.checkpoint()
        self.assertTrue(out["W"]["request_used"])
        self.assertTrue(out["O"]["B"]["request_sent"])
        self.assertEqual(out["O"]["B"]["request_sent_provenance"]["event_id"], receipt["event_ids"][0])
        self.assertEqual(receipt["producer_version"], "e1-keyledger-adapter-v0")
        self.assertTrue(validate_e1_evidence(out))
        # A pre-start retry cannot change request bits or provenance.
        rejected = executor.start(action)
        after = executor.checkpoint()
        self.assertFalse(rejected["accepted"])
        self.assertEqual(after["W"]["request_used"], out["W"]["request_used"])
        self.assertEqual(after["O"]["B"]["request_sent_provenance"],
                         out["O"]["B"]["request_sent_provenance"])

    def test_b_self_chooser_accepts_then_exchanges(self):
        executor = Executor(initial_checkpoint("unknown", "PAY", 8))
        cp = executor.checkpoint()
        run_one(executor, choose_b(actor_view(cp, "B")))
        cp = executor.checkpoint()
        run_one(executor, {"operator": "offer_loan", "actor": "A",
                           "args": {"target": "B", "payment": "payment"}})
        cp = executor.checkpoint()
        reply = choose_b(actor_view(cp, "B"))
        self.assertEqual(reply["operator"], "choose_accept")
        run_one(executor, reply)
        cp = executor.checkpoint()
        exchange = choose_b(actor_view(cp, "B"))
        self.assertEqual(exchange["operator"], "accept_loan")
        run_one(executor, exchange)
        self.assertEqual(executor.checkpoint()["W"]["holders"]["payment"], "B")

    def test_tool_policy_declines_until_real_return_then_accepts(self):
        first = Executor(initial_checkpoint("known", "TOOL", 10))
        cp = first.checkpoint()
        run_one(first, choose_b(actor_view(cp, "B")))
        cp = first.checkpoint()
        run_one(first, {"operator": "offer_loan", "actor": "A",
                        "args": {"target": "B", "payment": "payment"}})
        reply = choose_b(actor_view(first.checkpoint(), "B"))
        self.assertEqual(reply["operator"], "choose_decline")

        second = Executor(initial_checkpoint("known", "TOOL", 10))
        cp = second.checkpoint()
        run_one(second, choose_b(actor_view(cp, "B")))
        run_one(second, {"operator": "return_tool", "actor": "A",
                         "args": {"target": "B", "item": "toolB"}})
        run_one(second, {"operator": "offer_loan", "actor": "A",
                         "args": {"target": "B", "payment": "payment"}})
        self.assertEqual(choose_b(actor_view(second.checkpoint(), "B"))["operator"], "choose_accept")

    def test_keep_policy_rejects_offer(self):
        executor = Executor(initial_checkpoint("known", "KEEP", 10))
        run_one(executor, choose_b(actor_view(executor.checkpoint(), "B")))
        run_one(executor, {"operator": "offer_loan", "actor": "A",
                           "args": {"target": "B", "payment": "payment"}})
        self.assertEqual(choose_b(actor_view(executor.checkpoint(), "B"))["operator"], "choose_decline")

    def test_unknown_illegal_bindings_and_a_cannot_force_exchange(self):
        executor = Executor(initial_checkpoint("unknown", "PAY", 8))
        run_one(executor, choose_b(actor_view(executor.checkpoint(), "B")))
        before = executor.checkpoint()
        bad_offer = executor.start({"operator": "offer_loan", "actor": "A",
                                    "args": {"target": "B", "payment": "payment", "key_id": "key1"}})
        after = executor.checkpoint()
        self.assertFalse(bad_offer["accepted"])
        self.assertEqual(after["clock"], before["clock"])
        self.assertEqual(after["W"], before["W"])
        self.assertNotIn("key1", after["O"]["A"]["known_entities"])

        # Prepare an offer, then ensure A cannot issue the B-owned exchange,
        # and cannot settle after B has declined either.
        run_one(executor, {"operator": "offer_loan", "actor": "A",
                           "args": {"target": "B", "payment": "payment"}})
        cp = executor.checkpoint()
        before_holders = copy.deepcopy(cp["W"]["holders"])
        unauthorized = executor.start({"operator": "accept_loan", "actor": "A",
            "args": {"actor": "A", "item": "key1", "payment": "payment",
                     "offer_id": cp["W"]["offer_session"]["offer_id"]}})
        self.assertFalse(unauthorized["accepted"])
        self.assertEqual(executor.checkpoint()["W"]["holders"], before_holders)

        keep = Executor(initial_checkpoint("known", "KEEP", 10))
        run_one(keep, choose_b(actor_view(keep.checkpoint(), "B")))
        run_one(keep, {"operator": "offer_loan", "actor": "A",
                       "args": {"target": "B", "payment": "payment"}})
        run_one(keep, choose_b(actor_view(keep.checkpoint(), "B")))
        declined = keep.checkpoint()
        holders = copy.deepcopy(declined["W"]["holders"])
        post_decline = keep.start({"operator": "accept_loan", "actor": "B",
            "args": {"actor": "A", "item": "key1", "payment": "payment",
                     "offer_id": declined["W"]["offer_session"]["offer_id"]}})
        self.assertFalse(post_decline["accepted"])
        self.assertEqual(keep.checkpoint()["W"]["holders"], holders)

    def test_request_event_does_not_mutate_source_checkpoint(self):
        original = initial_checkpoint("known", "PAY", 8)
        executor = Executor(original)
        run_one(executor, choose_b(actor_view(original, "B")))
        self.assertFalse(original["W"]["request_used"])
        self.assertFalse(original["O"]["B"]["request_sent"])

    def test_seal_cannot_claim_future_request_event(self):
        executor = Executor(initial_checkpoint("known", "PAY", 8))
        run_one(executor, choose_b(actor_view(executor.checkpoint(), "B")))
        corrupt = executor.checkpoint()
        next(s for s in corrupt["seals"] if s["sealed_through"] == 2)["sequence_frontier"] = 1
        with self.assertRaises(MonitorContractError):
            validate_e1_evidence(corrupt)

    def test_unknown_plan_keeps_future_key_symbolic(self):
        cp = initial_checkpoint("unknown", "PAY", 8)
        executor = Executor(cp)
        run_one(executor, choose_b(actor_view(cp, "B")))
        view = actor_view(executor.checkpoint(), "A")
        plan = uniform_cost_search(view)
        self.assertEqual(plan["selected_action"]["operator"], "offer_loan")
        symbols = [step for step in plan["forecast_plan"] if step["operator"] == "unlock"]
        self.assertTrue(symbols)
        self.assertEqual(symbols[0]["args"]["item"]["symbol"], "LoanKey")
        self.assertNotIn("key1", view["observation"]["known_entities"])
        self.assertFalse(plan["unresolved_bindings_dispatchable"])

    def test_hidden_state_does_not_change_actor_proposals(self):
        base = initial_checkpoint("unknown", "PAY", 8)
        alt = copy.deepcopy(base)
        alt["W"]["request_used"] = True
        view_a = actor_view(base, "A")
        view_a_alt = actor_view(alt, "A")
        self.assertEqual(view_a, view_a_alt)
        self.assertEqual(uniform_cost_search(view_a)["selected_action"],
                         uniform_cost_search(view_a_alt)["selected_action"])
        view_b = actor_view(base, "B")
        view_b_alt = actor_view(alt, "B")
        self.assertEqual(choose_b(view_b), choose_b(view_b_alt))
        alt = copy.deepcopy(base)
        alt["O"]["B"]["known_entities"].append("hidden-extra")
        self.assertEqual(actor_view(base, "A"), actor_view(alt, "A"))

    def test_holding_without_acquisition_event_is_not_goal(self):
        cp = initial_checkpoint("known", "PAY", 8)
        cp["W"]["holders"]["ledger"] = "A"
        self.assertEqual(evaluate_goal(cp)["status"], "PENDING")

    def test_actor_view_rejects_forged_unsealed_goal_event(self):
        cp = initial_checkpoint("known", "PAY", 8)
        cp["O"]["A"]["known_events"] = [{"event_id": "fake", "event_type": "ledger_acquired",
            "time": 2, "sequence": 99, "producer_version": "e0-keyledger-executor-v0",
            "typed_args": {"event": "ledger_acquired", "actor": "A", "item": "ledger"}}]
        with self.assertRaises(ValueError):
            actor_view(cp, "A")

    def test_monitor_rejects_unsealed_or_mismatched_request(self):
        executor = Executor(initial_checkpoint("known", "PAY", 8))
        cp = executor.checkpoint()
        run_one(executor, choose_b(actor_view(cp, "B")))
        corrupt = executor.checkpoint()
        corrupt["seals"] = [s for s in corrupt["seals"] if s["sealed_through"] != 3]
        with self.assertRaises(MonitorContractError):
            validate_e1_evidence(corrupt)
        corrupt = executor.checkpoint()
        request = next(r for r in corrupt["receipts"] if r["producer_version"] == "e1-keyledger-adapter-v0")
        request["intent"]["args"]["item"] = "fake"
        with self.assertRaises(MonitorContractError):
            validate_e1_evidence(corrupt)

    def test_monitor_rejects_cross_producer_duplicate_sequence(self):
        executor = Executor(initial_checkpoint("known", "PAY", 8))
        cp = executor.checkpoint()
        run_one(executor, choose_b(actor_view(cp, "B")))
        corrupt = executor.checkpoint()
        corrupt["events"][-1]["sequence"] = corrupt["events"][0]["sequence"]
        with self.assertRaises(MonitorContractError):
            validate_e1_evidence(corrupt)

    def test_monitor_rejects_cross_producer_receipt_alias_and_missing_effect(self):
        executor = Executor(initial_checkpoint("known", "PAY", 8))
        cp = executor.checkpoint()
        run_one(executor, choose_b(actor_view(cp, "B")))
        corrupt = executor.checkpoint()
        e1 = next(r for r in corrupt["receipts"] if r["producer_version"] == "e1-keyledger-adapter-v0")
        e1["receipt_id"] = corrupt["receipts"][0]["receipt_id"]
        with self.assertRaises(MonitorContractError):
            validate_e1_evidence(corrupt)
        corrupt = executor.checkpoint()
        e1 = next(r for r in corrupt["receipts"] if r["producer_version"] == "e1-keyledger-adapter-v0")
        e1["delta_w"] = {}
        with self.assertRaises(MonitorContractError):
            validate_e1_evidence(corrupt)

    def test_budget_cap_is_incomplete(self):
        cp = initial_checkpoint("known", "PAY", 8)
        executor = Executor(cp)
        run_one(executor, choose_b(actor_view(cp, "B")))
        result = uniform_cost_search(actor_view(executor.checkpoint(), "A"), max_expansions=1)
        self.assertEqual(result["solve_status"], "BUDGET")
        self.assertFalse(result["complete"])

    def test_budget_checkpoint_restore_carries_usage_without_clock_timestamp(self):
        budget = restore_budget({"expansions": 17, "generated": 25, "elapsed_seconds": 0.25,
                                 "max_expansions": 10000, "wall_seconds": 2.0})
        restored = snapshot_budget(budget)
        self.assertEqual(restored["expansions"], 17)
        self.assertEqual(restored["generated"], 25)
        self.assertGreaterEqual(restored["elapsed_seconds"], 0.25)
        self.assertNotIn("started", restored)

    def test_run_case_cap_one_is_reported_as_incomplete(self):
        result = run_case(initial_checkpoint("known", "PAY", 8), max_expansions=1, wall_seconds=2.0)
        self.assertEqual(result["status"], "INCOMPLETE_BUDGET")
        self.assertEqual(result["oracle_checks"]["world"], "INCOMPLETE_BUDGET")
        self.assertEqual(result["oracles"]["world"]["solve_status"], "BUDGET")

    def test_actor_planning_budget_and_assumptions_round_trip(self):
        executor = Executor(initial_checkpoint("unknown", "PAY", 8))
        executor.record_actor_planning(budget={"expansions": 3, "generated": 5,
            "elapsed_seconds": 0.2, "max_expansions": 10000, "wall_seconds": 2.0},
            assumption={"text": "public contract"})
        checkpoint = executor.checkpoint()
        self.assertEqual(checkpoint["actor_planning"]["budget"]["expansions"], 3)
        fork = Executor(checkpoint)
        fork.record_actor_planning(binding={"symbol": "LoanKey(offer-x)", "actual_id": "key1"})
        self.assertEqual(executor.checkpoint()["actor_planning"]["late_binding_map"], {})

    def test_holder_fact_alone_does_not_shortcut_planner_goal(self):
        cp = initial_checkpoint("known", "PAY", 8)
        view = actor_view(cp, "A")
        view["observation"]["known_facts"].append("ledger_held_by_A")
        plan = uniform_cost_search(view)
        self.assertFalse(plan["solve_status"] == "SOLVED" and
                         plan["earliest_completion_time"] == 2 and not plan["forecast_plan"])

    def test_fork_isolation_and_symbolic_action_rejection(self):
        executor = Executor(initial_checkpoint("unknown", "PAY", 8))
        fork = executor.checkpoint()
        fork["W"]["holders"]["key1"] = "A"
        self.assertEqual(executor.checkpoint()["W"]["holders"]["key1"], "B")
        bad = executor.start({"operator": "unlock", "actor": "A",
                              "args": {"item": {"symbol": "LoanKey", "offer_id": "offer-x"}}})
        self.assertFalse(bad["accepted"])
        self.assertEqual(executor.checkpoint()["clock"]["now"], 2)
        self.assertFalse(executor.checkpoint()["W"]["archive_open"])


if __name__ == "__main__":
    unittest.main()
