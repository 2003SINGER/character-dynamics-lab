import unittest

from e0_keyledger_v0.runner import run_case


class RunnerContractTests(unittest.TestCase):
    def test_c01_test_pass_is_separate_from_budget_search_status(self):
        result = run_case("E0-C01")
        self.assertEqual(result["fixture_test_result"], "PASS", result["errors"])
        self.assertEqual(result["search_result"]["solve_status"], "BUDGET")
        self.assertEqual(result["oracle_result"]["solve_status"], "BUDGET")
        self.assertFalse(result["oracle_result"]["complete"])
        self.assertFalse(result["oracle_result"]["exhausted"])

    def test_x01_has_valid_match_and_detects_both_prediction_mutations(self):
        result = run_case("E0-X01")
        self.assertEqual(result["fixture_test_result"], "PASS", result["errors"])
        evidence = result["evidence"]
        self.assertEqual(evidence["illegal_binding"]["status"], "INVALID_BINDING")
        self.assertEqual(evidence["valid_prediction"]["status"], "MATCH")
        self.assertEqual(evidence["offer_disclosure_mutation"]["status"], "PREDICTION_MISMATCH")
        self.assertEqual(evidence["unlock_ledger_mutation"]["status"], "PREDICTION_MISMATCH")

    def test_p02_checks_every_boundary_and_reservation(self):
        result = run_case("E0-P02")
        self.assertEqual(result["fixture_test_result"], "PASS", result["errors"])
        self.assertEqual([row["time"] for row in result["evidence"]["minute_boundaries"]], [6, 7, 8])

    def test_h02_keeps_state_and_event_outcomes_distinct(self):
        result = run_case("E0-H02")
        self.assertEqual(result["fixture_test_result"], "PASS", result["errors"])
        self.assertEqual(result["evidence"]["holding_at_10"]["status"], "SATISFIED")
        self.assertEqual(result["evidence"]["goal_monitor"]["status"], "VIOLATED")


if __name__ == "__main__":
    unittest.main()
