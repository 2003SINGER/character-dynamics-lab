import unittest
from copy import deepcopy

from e0_keyledger_v0.executor import Executor, intent
from e0_keyledger_v0.fixtures import initial_checkpoint
from e0_keyledger_v0.monitor_bridge import evaluate_goal
from e0_keyledger_v0.runner import _audit_transition, _forecast_transition


class ExecutorBoundaryTests(unittest.TestCase):
    def test_u01_canonical_checkpoint_and_monitor_bridge_agree(self):
        checkpoint = initial_checkpoint("E0-U01")
        self.assertEqual([seal["sealed_through"] for seal in checkpoint["seals"]], [1, 2])
        self.assertEqual(checkpoint["monitor"]["status"], "PENDING")
        self.assertEqual(evaluate_goal(checkpoint)["status"], checkpoint["monitor"]["status"])

        evidence_copy = deepcopy(checkpoint)
        evidence_copy["seals"] = []
        self.assertEqual(evaluate_goal(evidence_copy)["status"], "INDETERMINATE")
        self.assertEqual([seal["sealed_through"] for seal in checkpoint["seals"]], [1, 2])

    def test_malformed_idle_is_rejected_without_world_change(self):
        executor = Executor(initial_checkpoint("E0-P01"))
        before = executor.checkpoint()["W"]
        receipt = executor.start({"operator": "idle", "actor": "A", "args": {"extra": "bad"}})
        self.assertFalse(receipt["accepted"])
        self.assertEqual(receipt["status"], "REJECTED")
        self.assertEqual(receipt["outcome"], "INVALID_TYPED_INTENT")
        self.assertEqual(executor.checkpoint()["W"], before)

    def test_valid_idle_forecast_matches_explicit_empty_observation_delta(self):
        before = initial_checkpoint("E0-H02")
        action = intent("idle")
        receipt, after, prediction = _forecast_transition(before, action)
        self.assertEqual(receipt["status"], "SUCCESS")
        self.assertEqual(receipt["delta_o"], {
            who: {field: {"added": [], "removed": []}
                  for field in ("known_entities", "known_facts")}
            for who in ("A", "B")
        })
        audit = _audit_transition(before, after, receipt, prediction)
        self.assertEqual(audit["status"], "MATCH", audit)

    def test_settlement_revalidates_resources_and_releases_reservation(self):
        executor = Executor(initial_checkpoint("E0-P02"))
        offer = executor.execute(intent("offer_loan", target="B", payment="payment"))
        self.assertEqual(offer["status"], "SUCCESS")
        offer_id = executor.checkpoint()["W"]["offer_session"]["offer_id"]
        self.assertEqual(executor.execute(intent("choose_accept", offer_id=offer_id))["status"], "SUCCESS")
        self.assertEqual(executor.execute(intent("accept_loan", actor="A", item="key1",
                                                 payment="payment", offer_id=offer_id))["status"], "SUCCESS")
        started = executor.start(intent("unlock", item="key1"))
        self.assertTrue(started["accepted"])
        started_checkpoint = executor.checkpoint()
        running = started_checkpoint["W"]["running_action"]
        self.assertEqual(running["id"], started["action_id"])
        self.assertEqual(started_checkpoint["W"]["reservations"][0]["action_id"], started["action_id"])

        # Simulate a world-side resource change after start but before settlement.
        executor._c["W"]["holders"]["key1"] = None
        executor._c["W"]["destroyed"]["key1"] = True
        executor._c["W"]["intact"]["key1"] = False
        executor.advance_minute()
        executor.advance_minute()
        checkpoint = executor.advance_minute()
        receipt = next(row for row in checkpoint["receipts"] if row["receipt_id"] == started["receipt_id"])

        self.assertEqual(receipt["status"], "INTERRUPTED")
        self.assertEqual(receipt["outcome"], "INTERRUPTED_NO_EFFECT")
        self.assertEqual(receipt["delta_w"], {})
        self.assertEqual(receipt["event_ids"], [])
        self.assertFalse(checkpoint["W"]["archive_open"])
        self.assertFalse(checkpoint["W"]["action_used_bits"]["unlock"])
        self.assertIsNone(checkpoint["W"]["running_action"])
        self.assertEqual(checkpoint["W"]["reservations"], [])


if __name__ == "__main__":
    unittest.main()
