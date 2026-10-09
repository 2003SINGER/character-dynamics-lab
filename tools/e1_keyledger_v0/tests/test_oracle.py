"""Hand-derived contract checks for the independent E1 finite oracles."""

from copy import deepcopy
import unittest

from tools.e1_keyledger_v0.fixtures import primary_conditions, initial_checkpoint
from tools.e1_keyledger_v0.executor import Executor
from tools.e1_keyledger_v0.oracle import (
    _initial, _key, _policy_accept, _policy_wants_exchange,
    _policy_wants_request, solve,
)


class E1OracleTests(unittest.TestCase):
    def test_twelve_hand_derived_cases(self):
        for checkpoint in primary_conditions():
            with self.subTest(case=checkpoint["fixture_id"]):
                world = solve(checkpoint, "world")
                fixed = solve(checkpoint, "fixed_b")
                policy = checkpoint["config_pins"]["e1"]["policy"]
                deadline = checkpoint["config_pins"]["deadline"]
                self.assertEqual(world["solve_status"], "SOLVED")
                self.assertTrue(world["complete"])
                self.assertEqual(world["earliest_completion_time"], 8)
                self.assertEqual(world["path"][0]["operator"], "request_tool")
                self.assertEqual(world["path"][0]["start_time"], 2)
                self.assertEqual(world["path"][0]["end_time"], 3)

                if policy == "PAY":
                    self.assertEqual(fixed["solve_status"], "SOLVED")
                    self.assertEqual(fixed["earliest_completion_time"], 8)
                elif policy == "TOOL" and deadline == 10:
                    self.assertEqual(fixed["solve_status"], "SOLVED")
                    self.assertEqual(fixed["earliest_completion_time"], 9)
                    ops = [step["operator"] for step in fixed["path"]]
                    self.assertEqual(ops, ["request_tool", "return_tool", "offer_loan",
                                           "choose_accept", "accept_loan", "unlock", "take_ledger"])
                else:
                    self.assertEqual(fixed["solve_status"], "PROVEN_UNREACHABLE_IN_FINITE_DOMAIN")
                    self.assertTrue(fixed["complete"])
                    self.assertTrue(fixed["exhausted"])
                    self.assertIsNone(fixed["earliest_completion_time"])

    def test_initial_b_slot_is_not_skipped(self):
        result = solve(initial_checkpoint("unknown", "PAY", 8), "world")
        self.assertEqual(result["earliest_completion_time"], 8)
        self.assertEqual(result["path"][0]["operator"], "request_tool")
        self.assertEqual(result["path"][0]["start_time"], 2)
        self.assertNotEqual(result["earliest_completion_time"], 7)

    def test_returning_tool_changes_tool_policy_before_offer(self):
        result = solve(initial_checkpoint("known", "TOOL", 10), "fixed_b")
        self.assertEqual(result["earliest_completion_time"], 9)
        ops = [step["operator"] for step in result["path"]]
        self.assertLess(ops.index("return_tool"), ops.index("offer_loan"))
        self.assertIn("choose_accept", ops)

    def test_solved_oracle_paths_replay_through_e1_executor(self):
        for checkpoint in primary_conditions():
            for mode in ("world", "fixed_b"):
                result = solve(checkpoint, mode)
                if result["solve_status"] != "SOLVED":
                    continue
                with self.subTest(case=checkpoint["fixture_id"], mode=mode):
                    runner = Executor(deepcopy(checkpoint))
                    for step in result["path"]:
                        ack = runner.execute({key: step[key] for key in ("operator", "actor", "args")})
                        self.assertTrue(ack["accepted"], ack)
                        self.assertEqual(ack["status"], "SUCCESS")
                    final = runner.checkpoint()
                    witnesses = [event for event in final["events"]
                                 if event.get("event_type") == "ledger_acquired"
                                 and event.get("typed_args", {}).get("actor") == "A"
                                 and event.get("typed_args", {}).get("item") == "ledger"]
                    self.assertEqual(len(witnesses), 1)
                    self.assertEqual(witnesses[0]["time"], result["earliest_completion_time"])

    def test_fixed_b_proposal_uses_observation_not_hidden_world(self):
        checkpoint = initial_checkpoint("known", "PAY", 10)
        checkpoint["W"]["offer_session"].update({
            "status": "OFFERED", "offer_id": "offer-000001", "terms": {"payment": "payment"}})
        checkpoint["O"]["B"]["known_entities"].append("offer-000001")
        checkpoint["O"]["B"]["known_entities"].append("payment")
        checkpoint["O"]["B"]["known_facts"].append("offer_visible")
        checkpoint["O"]["B"]["known_facts"].append("reply_accept_visible")
        checkpoint["W"]["offer_session"]["status"] = "ACCEPTED"
        checkpoint["W"]["request_used"] = False
        baseline = _initial(checkpoint)
        changed_world = deepcopy(checkpoint)
        changed_world["W"]["request_used"] = True
        changed_world["W"]["holders"]["key1"] = None
        changed_world["W"]["intact"]["key1"] = False
        changed_world["W"]["destroyed"]["key1"] = True
        hidden = _initial(changed_world)
        pins = checkpoint["config_pins"]["e1"]
        self.assertTrue(_policy_accept(baseline, pins))
        self.assertEqual(_policy_accept(baseline, pins), _policy_accept(hidden, pins))
        public_pins = checkpoint["O"]["B"]["public_contract"]
        self.assertTrue(_policy_wants_exchange(baseline, public_pins))
        self.assertEqual(_policy_wants_exchange(baseline, public_pins),
                         _policy_wants_exchange(hidden, public_pins))
        self.assertEqual(_policy_wants_request(baseline), _policy_wants_request(hidden))

    def test_world_request_bit_and_actor_receipt_are_distinct_in_state_key(self):
        checkpoint = initial_checkpoint("known", "PAY", 8)
        base = _initial(checkpoint)
        world_only = deepcopy(checkpoint)
        world_only["W"]["request_used"] = True
        self.assertNotEqual(_key(base), _key(_initial(world_only)))
        observation_only = deepcopy(checkpoint)
        observation_only["O"]["B"]["request_sent"] = True
        observation_only["O"]["B"]["request_sent_provenance"] = {
            "kind": "settlement_receipt", "event_id": "event-x", "time": 3, "actor": "B"}
        self.assertNotEqual(_key(base), _key(_initial(observation_only)))
        self.assertNotEqual(_key(_initial(world_only)), _key(_initial(observation_only)))

    def test_key1_tombstone_is_finitely_unreachable(self):
        checkpoint = initial_checkpoint("known", "PAY", 10)
        w, ob = checkpoint["W"], checkpoint["O"]["B"]
        w["holders"]["key1"] = None
        w["intact"]["key1"] = False
        w["destroyed"]["key1"] = True
        ob["known_entities"] = [item for item in ob["known_entities"] if item != "key1"]
        ob["known_facts"] = [fact for fact in ob["known_facts"] if fact != "key1_held_by_B"]
        ob["known_facts"].append("key1_destroyed")
        for mode in ("world", "fixed_b"):
            result = solve(checkpoint, mode)
            self.assertEqual(result["solve_status"], "PROVEN_UNREACHABLE_IN_FINITE_DOMAIN")
            self.assertTrue(result["exhausted"])

    def test_initial_holder_without_acquisition_event_is_not_goal(self):
        checkpoint = initial_checkpoint("known", "PAY", 10)
        checkpoint["W"]["holders"]["ledger"] = "A"
        self.assertFalse(any(event.get("event_type") == "ledger_acquired"
                             for event in checkpoint["events"]))
        for mode in ("world", "fixed_b"):
            result = solve(checkpoint, mode)
            self.assertNotEqual(result["solve_status"], "SOLVED")
            self.assertEqual(result["solve_status"], "PROVEN_UNREACHABLE_IN_FINITE_DOMAIN")

    def test_expansion_cap_reports_incomplete_budget(self):
        result = solve(initial_checkpoint("unknown", "PAY", 10), "world", max_expansions=1)
        self.assertEqual(result["solve_status"], "BUDGET")
        self.assertFalse(result["complete"])
        self.assertFalse(result["exhausted"])
        self.assertEqual(result["termination_reason"], "EXPANSION_CAP")

    def _executed_goal_checkpoint(self):
        runner = Executor(initial_checkpoint("known", "PAY", 10))

        def execute(operator, controller, **args):
            return runner.execute({"operator": operator, "actor": controller, "args": args})

        execute("request_tool", "B", target="A", item="toolB")
        execute("offer_loan", "A", target="B", payment="payment")
        offer_id = runner.checkpoint()["W"]["offer_session"]["offer_id"]
        execute("choose_accept", "B", offer_id=offer_id)
        execute("accept_loan", "B", actor="A", item="key1", payment="payment", offer_id=offer_id)
        execute("unlock", "A", item="key1")
        execute("take_ledger", "A", item="ledger")
        return runner.checkpoint()

    def test_executor_receipt_and_holder_delta_are_required_goal_evidence(self):
        checkpoint = self._executed_goal_checkpoint()
        result = solve(checkpoint, "world")
        self.assertEqual(result["solve_status"], "SOLVED")
        self.assertEqual(result["termination_reason"], "GOAL_AT_INITIAL_CHECKPOINT")
        event = next(e for e in checkpoint["events"] if e["event_type"] == "ledger_acquired")
        receipt = next(r for r in checkpoint["receipts"] if event["event_id"] in r["event_ids"])
        self.assertEqual(receipt["delta_w"]["holders"][0]["ledger"], "ARCHIVE")
        self.assertEqual(receipt["delta_w"]["holders"][1]["ledger"], "A")

        missing_delta = deepcopy(checkpoint)
        bad_receipt = next(r for r in missing_delta["receipts"]
                           if event["event_id"] in r["event_ids"])
        del bad_receipt["delta_w"]["holders"]
        self.assertNotEqual(solve(missing_delta, "world")["solve_status"], "SOLVED")

        forged_delta = deepcopy(checkpoint)
        bad_receipt = next(r for r in forged_delta["receipts"]
                           if event["event_id"] in r["event_ids"])
        bad_receipt["delta_w"]["holders"][0]["ledger"] = "A"
        self.assertNotEqual(solve(forged_delta, "world")["solve_status"], "SOLVED")


if __name__ == "__main__":
    unittest.main()
