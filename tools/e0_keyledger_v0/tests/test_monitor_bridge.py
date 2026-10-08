import unittest
from copy import deepcopy

from e0_keyledger_v0.executor import Executor, intent
from e0_keyledger_v0.fixtures import initial_checkpoint
from e0_keyledger_v0.monitor_bridge import (
    MonitorContractError,
    evaluate_goal,
    evaluate_holding_at,
)


class MonitorBridgeTests(unittest.TestCase):
    def test_event_goal_is_pending_then_satisfied_from_receipt_backed_event(self):
        checkpoint = initial_checkpoint("E0-P01")
        self.assertEqual(evaluate_goal(checkpoint)["status"], "PENDING")

        executor = Executor(checkpoint)
        actions = (
            intent("offer_loan", target="B", payment="payment"),
        )
        for action in actions:
            receipt = executor.execute(action)
            self.assertTrue(receipt["accepted"])
            self.assertEqual(receipt["status"], "SUCCESS")
        session = executor.checkpoint()["W"]["offer_session"]["offer_id"]
        for action in (
            intent("choose_accept", offer_id=session),
            intent("accept_loan", actor="A", item="key1", payment="payment", offer_id=session),
            intent("unlock", item="key1"),
            intent("take_ledger", item="ledger"),
        ):
            receipt = executor.execute(action)
            self.assertTrue(receipt["accepted"])
            self.assertEqual(receipt["status"], "SUCCESS")

        result = evaluate_goal(executor.checkpoint())
        self.assertEqual(result["status"], "SATISFIED")
        self.assertEqual(len(result["witness_event_ids"]), 1)

    def test_missing_past_seal_is_indeterminate(self):
        checkpoint = initial_checkpoint("E0-U01")
        self.assertEqual(evaluate_goal(checkpoint)["status"], "PENDING")
        evidence_copy = deepcopy(checkpoint)
        evidence_copy["seals"] = [seal for seal in evidence_copy["seals"] if seal["sealed_through"] < 2]
        result = evaluate_goal(evidence_copy)
        self.assertEqual(result["status"], "INDETERMINATE")
        self.assertIsNone(result["coverage_complete_through"])

        executor = Executor(evidence_copy)
        executor.execute(intent("idle"))
        later = evaluate_goal(executor.checkpoint())
        self.assertEqual(later["status"], "INDETERMINATE")
        self.assertIsNone(later["coverage_complete_through"])

    def test_holding_state_and_event_goal_are_separate(self):
        executor = Executor(initial_checkpoint("E0-H02"))
        while executor.checkpoint()["clock"]["now"] < 10:
            receipt = executor.execute(intent("idle"))
            self.assertTrue(receipt["accepted"])
            self.assertEqual(receipt["status"], "SUCCESS")
        checkpoint = executor.checkpoint()
        self.assertEqual(evaluate_holding_at(checkpoint, at_time=10)["status"], "SATISFIED")
        self.assertEqual(evaluate_goal(checkpoint)["status"], "VIOLATED")

    def test_counterfeit_event_without_receipt_is_rejected(self):
        checkpoint = initial_checkpoint("E0-P01")
        checkpoint["events"].append({
            "event_id": "fake-event",
            "event_type": "ledger_acquired",
            "time": 2,
            "sequence": 1,
            "producer_version": checkpoint["domain"]["producer_version"],
            "typed_args": {"event": "ledger_acquired", "actor": "A", "item": "ledger"},
        })
        with self.assertRaises(MonitorContractError):
            evaluate_goal(checkpoint)

    def test_event_payload_cannot_be_changed_while_reusing_receipt_event_id(self):
        executor = Executor(initial_checkpoint("E0-P01"))
        for action in (intent("offer_loan", target="B", payment="payment"),):
            executor.execute(action)
        offer_id = executor.checkpoint()["W"]["offer_session"]["offer_id"]
        for action in (
            intent("choose_accept", offer_id=offer_id),
            intent("accept_loan", actor="A", item="key1", payment="payment", offer_id=offer_id),
            intent("unlock", item="key1"),
            intent("take_ledger", item="ledger"),
        ):
            executor.execute(action)
        checkpoint = executor.checkpoint()
        target = next(row for row in checkpoint["events"] if row["event_type"] == "ledger_acquired")
        target["typed_args"]["item"] = "payment"
        with self.assertRaises(MonitorContractError):
            evaluate_goal(checkpoint)

    def test_reordered_event_ledger_is_not_sorted_into_validity(self):
        executor = Executor(initial_checkpoint("E0-P01"))
        executor.execute(intent("offer_loan", target="B", payment="payment"))
        offer_id = executor.checkpoint()["W"]["offer_session"]["offer_id"]
        executor.execute(intent("choose_accept", offer_id=offer_id))
        checkpoint = executor.checkpoint()
        checkpoint["events"][-2:] = reversed(checkpoint["events"][-2:])
        with self.assertRaises(MonitorContractError):
            evaluate_goal(checkpoint)

    def test_reordered_seal_ledger_including_pre_horizon_rows_is_rejected(self):
        checkpoint = initial_checkpoint("E0-P01")
        checkpoint["seals"].reverse()
        with self.assertRaises(MonitorContractError):
            evaluate_goal(checkpoint)

    def test_key1_tombstone_prefix_uses_receipt_grounded_item(self):
        checkpoint = initial_checkpoint("E0-N02")
        rows = [row for row in checkpoint["events"] if row["event_type"] == "key_destroyed"]
        if any(row["typed_args"].get("item") == "key1" for row in rows):
            result = evaluate_goal(checkpoint)
            self.assertEqual(result["status"], "PENDING")

    def test_e0_window_uses_t2_as_scenario_start(self):
        executor = Executor(initial_checkpoint("E0-P01"))
        for action in (
            intent("offer_loan", target="B", payment="payment"),
        ):
            executor.execute(action)
        session = executor.checkpoint()["W"]["offer_session"]["offer_id"]
        executor.execute(intent("choose_accept", offer_id=session))
        executor.execute(intent("accept_loan", actor="A", item="key1", payment="payment", offer_id=session))
        executor.execute(intent("unlock", item="key1"))
        executor.execute(intent("take_ledger", item="ledger"))
        result = evaluate_goal(executor.checkpoint(), deadline=7)
        self.assertEqual(result["status"], "SATISFIED")
        self.assertEqual(result["witness_event_ids"], ["event-000004"])


if __name__ == "__main__":
    unittest.main()
