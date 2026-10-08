"""Focused acceptance checks for the independent E0 finite-domain oracle."""

import unittest
from copy import deepcopy

from tools.e0_keyledger_v0.executor import Executor, intent
from tools.e0_keyledger_v0.fixtures import initial_checkpoint
from tools.e0_keyledger_v0.oracle import (
    _apply, _candidate_intents, _eligible, _intent, _target_event, solve,
)


class OracleAcceptanceTests(unittest.TestCase):
    def solve_case(self, case_id, **kwargs):
        checkpoint = initial_checkpoint(case_id)
        return solve(checkpoint, **kwargs)

    def assert_search_status_is_honest(self, result, reachable):
        if result["complete"]:
            self.assertTrue(result["exhausted"])
            self.assertEqual(result["solve_status"],
                             "POSSIBLE_IN_WORLD" if reachable else "PROVEN_UNREACHABLE_IN_FINITE_DOMAIN")
        else:
            self.assertFalse(result["exhausted"])
            self.assertEqual(result["solve_status"], "BUDGET")
            self.assertIn(result["termination_reason"], ("STATE_CAP", "WALL_TIMEOUT"))

    def test_normal_accept_goal_is_at_t7(self):
        result = self.solve_case("E0-P01")
        self.assertTrue(result["goal_found"])
        self.assertEqual(result["earliest_completion_time"], 7)
        self.assertEqual(result["shortest_duration_minutes"], 5)
        self.assert_search_status_is_honest(result, reachable=True)

    def test_deadline_seven_includes_t7_event(self):
        result = self.solve_case("E0-B01")
        self.assertTrue(result["goal_found"])
        self.assertEqual(result["earliest_completion_time"], 7)
        self.assert_search_status_is_honest(result, reachable=True)

    def test_joint_reply_has_accept_path(self):
        checkpoint = initial_checkpoint("E0-P01", reply_pin="JOINT")
        result = solve(checkpoint)
        self.assertTrue(result["goal_found"])
        self.assertEqual(result["earliest_completion_time"], 7)
        self.assertIn("choose_accept", [step["operator"] for step in result["goal_path"]])
        self.assert_search_status_is_honest(result, reachable=True)

    def test_decline_pin_has_no_goal(self):
        result = self.solve_case("E0-N01")
        self.assertFalse(result["goal_found"])
        self.assertIsNone(result["earliest_completion_time"])
        self.assert_search_status_is_honest(result, reachable=False)

    def test_deadline_six_has_no_goal(self):
        result = self.solve_case("E0-B02")
        self.assertFalse(result["goal_found"])
        self.assert_search_status_is_honest(result, reachable=False)

    def test_t5_checkpoint_includes_right_endpoint_t10(self):
        checkpoint = initial_checkpoint("E0-B03")
        self.assertEqual(checkpoint["clock"]["now"], 5)
        result = solve(checkpoint)
        self.assertTrue(result["goal_found"])
        self.assertEqual(result["earliest_completion_time"], 10)
        self.assertEqual(result["shortest_duration_minutes"], 5)
        self.assertEqual(len(result["goal_path"]), 5)
        self.assert_search_status_is_honest(result, reachable=True)

    def test_three_minute_unlock_keeps_forced_boundaries(self):
        result = self.solve_case("E0-P02")
        self.assertTrue(result["goal_found"])
        self.assertEqual(result["earliest_completion_time"], 9)
        ops = [step["operator"] for step in result["goal_path"]]
        self.assertEqual(ops, ["offer_loan", "choose_accept", "accept_loan", "unlock",
                               "idle", "idle", "take_ledger"])
        self.assertEqual(result["goal_path"][3]["start_time"], 5)
        self.assertEqual(result["goal_path"][3]["end_time"], 6)
        self.assert_search_status_is_honest(result, reachable=True)

    def test_oracle_resumes_mid_unlock_and_executor_replays_path(self):
        runner = Executor(initial_checkpoint("E0-P02"))
        runner.execute(intent("offer_loan", target="B", payment="payment"))
        offer_id = runner.checkpoint()["W"]["offer_session"]["offer_id"]
        runner.execute(intent("choose_accept", offer_id=offer_id))
        runner.execute(intent("accept_loan", actor="A", item="key1", payment="payment",
                              offer_id=offer_id))
        runner.start(intent("unlock", item="key1"))
        runner.advance_minute()
        mid_unlock = runner.checkpoint()
        self.assertEqual(mid_unlock["clock"]["now"], 6)
        self.assertEqual(mid_unlock["W"]["running_action"]["elapsed"], 1)
        running_id = mid_unlock["W"]["running_action"]["id"]
        running_receipt_id = mid_unlock["W"]["running_action"]["receipt_id"]
        receipt_count = len(mid_unlock["receipts"])

        oracle_boundary = _apply(mid_unlock, _intent("idle", "WorldStep"), deadline=10)
        oracle_boundary = _apply(oracle_boundary, _intent("idle", "WorldStep"), deadline=10)
        self.assertEqual(len(oracle_boundary["receipts"]), receipt_count)
        settled_receipts = [receipt for receipt in oracle_boundary["receipts"]
                            if receipt["receipt_id"] == running_receipt_id]
        self.assertEqual(len(settled_receipts), 1)
        self.assertEqual(settled_receipts[0]["status"], "SUCCESS")
        self.assertIsNone(oracle_boundary["W"]["running_action"])

        result = solve(mid_unlock)
        self.assertTrue(result["goal_found"])
        self.assertEqual(result["earliest_completion_time"], 9)
        self.assertEqual([step["operator"] for step in result["goal_path"]],
                         ["idle", "idle", "take_ledger"])
        self.assert_search_status_is_honest(result, reachable=True)

        replay = Executor(deepcopy(mid_unlock))
        first = result["goal_path"][0]
        replay.execute(intent(first["operator"], **first["args"]))
        after_first = replay.checkpoint()
        self.assertEqual(after_first["W"]["running_action"]["id"], running_id)
        self.assertEqual(after_first["W"]["running_action"]["elapsed"], 2)
        for step in result["goal_path"][1:]:
            replay.execute(intent(step["operator"], **step["args"]))
        final = replay.checkpoint()
        self.assertEqual(final["clock"]["now"], 9)
        self.assertEqual(final["W"]["holders"]["ledger"], "A")
        self.assertTrue(any(event.get("event_type") == "ledger_acquired"
                            and event.get("time") == 9 for event in final["events"]))
        self.assertEqual(mid_unlock["clock"]["now"], 6)
        self.assertEqual(mid_unlock["W"]["running_action"]["elapsed"], 1)

    def test_key1_tombstone_has_no_goal(self):
        result = self.solve_case("E0-N02")
        self.assertFalse(result["goal_found"])
        self.assert_search_status_is_honest(result, reachable=False)

        joint_checkpoint = initial_checkpoint("E0-N02")
        joint_checkpoint["config_pins"]["reply"] = "JOINT"
        joint = solve(joint_checkpoint)
        self.assertFalse(joint["goal_found"])
        self.assert_search_status_is_honest(joint, reachable=False)

    def test_initial_holding_is_not_goal_event(self):
        checkpoint = initial_checkpoint("E0-H02")
        self.assertEqual(checkpoint["W"]["holders"]["ledger"], "A")
        self.assertFalse(any(event.get("typed_args", {}).get("event") == "ledger_acquired"
                             for event in checkpoint["events"]))
        result = solve(checkpoint)
        self.assertFalse(result["goal_found"])
        self.assert_search_status_is_honest(result, reachable=False)

    def test_goal_shaped_event_without_take_receipt_is_not_a_witness(self):
        checkpoint = initial_checkpoint("E0-C01")
        checkpoint["events"].append({
            "event_id": "event-forged",
            "event_type": "ledger_acquired",
            "time": 2,
            "sequence": 1,
            "producer_version": checkpoint["domain"]["producer_version"],
            "typed_args": {"event": "ledger_acquired", "actor": "A", "item": "ledger"},
        })
        result = solve(checkpoint, max_expansions=1)
        self.assertFalse(result["goal_found"])

    def test_witness_requires_exact_receipt_payload_and_contiguous_seal(self):
        checkpoint = initial_checkpoint("E0-C01")
        event = {
            "event_id": "event-test",
            "event_type": "ledger_acquired",
            "time": 2,
            "sequence": 1,
            "producer_version": checkpoint["domain"]["producer_version"],
            "typed_args": {"event": "ledger_acquired", "actor": "A", "item": "ledger"},
        }
        receipt = {
            "receipt_id": "receipt-test", "action_id": "action-test",
            "producer_version": checkpoint["domain"]["producer_version"],
            "intent": {"operator": "take_ledger", "actor": "A", "args": {"item": "ledger"}},
            "accepted": True, "start_time": 1, "end_time": 2, "status": "SUCCESS",
            "event_ids": [event["event_id"]], "event_payloads": [deepcopy(event)],
        }
        checkpoint["events"].append(event)
        checkpoint["receipts"].append(receipt)
        checkpoint["action_history"].append({
            "action_id": "action-test", "receipt_id": "receipt-test", "time": 1,
            "intent": deepcopy(receipt["intent"]), "status": "SUCCESS",
        })
        del checkpoint["seals"][-1]
        self.assertIsNone(_target_event(checkpoint, 10))
        checkpoint["seals"].append({
            "sealed_through": 2, "producer_version": checkpoint["domain"]["producer_version"],
            "sequence_frontier": 1,
        })
        self.assertEqual(_target_event(checkpoint, 10), event)
        receipt["event_payloads"][0]["typed_args"]["item"] = "other"
        self.assertIsNone(_target_event(checkpoint, 10))

    def test_information_knowledge_and_copresence_are_preconditions(self):
        checkpoint = initial_checkpoint("E0-P01")
        offer = _intent("offer_loan", "A", target="B", payment="payment")
        self.assertTrue(_eligible(checkpoint, offer))
        offered_projection = _apply(checkpoint, offer, deadline=10)
        offer_id = offered_projection["W"]["offer_session"]["offer_id"]
        for actor in ("A", "B"):
            self.assertIn(offer_id, offered_projection["O"][actor]["known_entities"])
            self.assertIn("payment", offered_projection["O"][actor]["known_entities"])
        no_payment_knowledge = deepcopy(checkpoint)
        no_payment_knowledge["O"]["A"]["known_entities"].remove("payment")
        self.assertFalse(_eligible(no_payment_knowledge, offer))

        offer_id = "offer-000001"
        offered = deepcopy(checkpoint)
        offered["W"]["offer_session"].update({"status": "OFFERED", "offer_id": offer_id})
        offered["W"]["action_used_bits"]["offer_loan"] = True
        offered["config_pins"]["reply"] = "JOINT"
        decline = _intent("choose_decline", "B", offer_id=offer_id)
        self.assertFalse(_eligible(offered, decline))
        offered["O"]["B"]["known_entities"].append(offer_id)
        self.assertTrue(_eligible(offered, decline))

        no_tool_knowledge = deepcopy(checkpoint)
        no_tool_knowledge["O"]["A"]["known_entities"].remove("toolB")
        self.assertFalse(_eligible(no_tool_knowledge,
                                   _intent("return_tool", "A", target="B", item="toolB")))
        no_receiver_tool_knowledge = deepcopy(checkpoint)
        no_receiver_tool_knowledge["O"]["B"]["known_entities"].remove("toolB")
        self.assertFalse(_eligible(no_receiver_tool_knowledge,
                                   _intent("return_tool", "A", target="B", item="toolB")))

        ready_to_unlock = deepcopy(checkpoint)
        ready_to_unlock["W"]["holders"]["key1"] = "A"
        ready_to_unlock["O"]["A"]["known_entities"].append("key1")
        ready_to_unlock["W"]["locations"]["B"] = "ELSEWHERE"
        self.assertFalse(_eligible(ready_to_unlock, _intent("unlock", "A", item="key1")))

        ready_to_take = deepcopy(checkpoint)
        ready_to_take["W"]["archive_open"] = True
        ready_to_take["W"]["locations"]["B"] = "ELSEWHERE"
        self.assertFalse(_eligible(ready_to_take, _intent("take_ledger", "A", item="ledger")))

        no_ledger_knowledge = deepcopy(checkpoint)
        no_ledger_knowledge["W"]["archive_open"] = True
        no_ledger_knowledge["O"]["A"]["known_entities"].remove("ledger")
        self.assertFalse(_eligible(no_ledger_knowledge, _intent("take_ledger", "A", item="ledger")))

        bad_payment_owner = deepcopy(checkpoint)
        bad_payment_owner["W"]["offer_session"].update({"status": "ACCEPTED", "offer_id": "offer-000001"})
        bad_payment_owner["W"]["action_used_bits"].update({"offer_loan": True, "reply": True})
        bad_payment_owner["W"]["beneficial_owners"]["payment"] = "B"
        bad_payment_owner["O"]["A"]["known_entities"].extend(["key1", "offer-000001"])
        bad_payment_owner["O"]["B"]["known_entities"].extend(["payment", "offer-000001"])
        self.assertFalse(_eligible(bad_payment_owner,
                                   _intent("accept_loan", "B", actor="A", item="key1",
                                           payment="payment", offer_id="offer-000001")))

    def test_transcribed_settlement_events_have_frozen_signatures(self):
        checkpoint = initial_checkpoint("E0-P01")
        for operator in ("offer_loan", "choose_accept", "accept_loan", "unlock", "take_ledger"):
            action = next(candidate for candidate in _candidate_intents(checkpoint)
                          if candidate["operator"] == operator)
            checkpoint = _apply(checkpoint, action, deadline=10)
        events = checkpoint["events"][1:]
        self.assertEqual([event["event_type"] for event in events], [
            "loan_reply_accepted", "loan_exchanged", "archive_unlocked", "ledger_acquired",
        ])
        self.assertEqual(events[0]["typed_args"], {
            "event": "loan_reply_accepted", "actor": "B", "offer_id": "offer-000001", "item": "key1",
        })
        self.assertEqual(events[1]["typed_args"], {
            "event": "loan_exchanged", "actor": "B", "item": "key1",
            "payment": "payment", "offer_id": "offer-000001",
        })
        self.assertEqual(events[2]["typed_args"], {
            "event": "archive_unlocked", "actor": "A", "item": "ARCHIVE", "key": "key1",
        })
        for receipt in checkpoint["receipts"]:
            if receipt["event_ids"]:
                event_index = next(i for i, event in enumerate(checkpoint["events"])
                                   if event["event_id"] == receipt["event_ids"][0])
                self.assertEqual(receipt["event_payloads"], [checkpoint["events"][event_index]])

        decline_state = initial_checkpoint("E0-N01")
        offer = next(candidate for candidate in _candidate_intents(decline_state)
                     if candidate["operator"] == "offer_loan")
        decline_state = _apply(decline_state, offer, deadline=10)
        decline = next(candidate for candidate in _candidate_intents(decline_state)
                       if candidate["operator"] == "choose_decline")
        decline_state = _apply(decline_state, decline, deadline=10)
        self.assertEqual(decline_state["events"][-1]["typed_args"], {
            "event": "loan_reply_declined", "actor": "B", "offer_id": "offer-000001",
        })

    def test_future_minutes_do_not_fill_a_missing_seal_prefix(self):
        checkpoint = initial_checkpoint("E0-U01")
        checkpoint["seals"] = []
        checkpoint["monitor"] = {
            "status": "INDETERMINATE", "witness_event_id": None,
            "coverage_complete_through": 0, "reason": "MISSING_PAST_COVERAGE",
        }
        advanced = _apply(checkpoint, _intent("idle", "WorldStep"), deadline=10)
        self.assertEqual(advanced["seals"], [])
        self.assertEqual(advanced["monitor"]["coverage_complete_through"], 0)
        self.assertEqual(advanced["monitor"]["status"], "INDETERMINATE")

    def test_cap_one_counts_start_and_preserves_frontier(self):
        checkpoint = initial_checkpoint("E0-C01")
        result = solve(checkpoint, max_expansions=1, timeout_seconds=2.0)
        self.assertEqual(result["expansions"], 1)
        self.assertEqual(result["solve_status"], "BUDGET")
        self.assertEqual(result["termination_reason"], "STATE_CAP")
        self.assertFalse(result["complete"])
        self.assertFalse(result["exhausted"])
        self.assertGreater(result["frontier"], 0)


if __name__ == "__main__":
    unittest.main()
