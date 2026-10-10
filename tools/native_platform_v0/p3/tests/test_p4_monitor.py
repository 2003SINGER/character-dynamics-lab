from __future__ import annotations

import copy
import unittest

from tools.native_platform_v0.p3.p4_monitor import (
    AUTHOR_DEADLINE, LEDGER_PRODUCER, author_constraint, choose_director,
    evaluate_author_constraint,
)


class P4DirectorMonitorTests(unittest.TestCase):
    def view(self, **overrides):
        result = {"now": 4, "deadline": 24, "door_closed": True,
                  "opportunity_used": False, "goal_witness_present": False}
        result.update(overrides)
        return result

    def response(self, *, decision="accepted", responder=202, sealed=True, **overrides):
        row = {
            "event_type": "SOCIAL_RESPONSE", "event_version": 1,
            "event_id": "ledger-response-1", "minute": 8, "sequence": 12,
            "producer_version": LEDGER_PRODUCER, "sealed": sealed,
            "typed_args": {
                "request_id": "request-1", "initiator_role": "hero",
                "initiator_actor_id": 101, "recipient_role": "love",
                "recipient_actor_id": 202, "responder_role": "love",
                "responder_actor_id": responder, "note_id": 77,
                "note_dbref": "#77", "decision": decision,
                "native_volitions": [{"category": "affinity", "weight": 10}],
                "native_candidates": ["accept_note", "reject_note"],
                "selected_action": "writeLoveNoteAccept" if decision == "accepted" else "writeLoveNoteReject",
                "physical_receipt": {"status": "settled", "receipt_id": "physical-response-1", "actor_id": 202,
                                     "before_location_id": 202, "after_location_id": 202,
                                     "action_name": "writeLoveNoteAccept" if decision == "accepted"
                                     else "writeLoveNoteReject", "same_note_id": 77},
                "native_commit_status": "settled", "native_commit_receipt_id": "commit-1",
                "source_event_id": "request-event-1",
            },
        }
        row.update(overrides)
        return row

    def evaluate(self, ledger):
        return evaluate_author_constraint(
            ledger, now=24, deadline=24,
            ledger_sealed_through={"minute": 24, "sequence": 40, "closed": True},
            scene_roles={"courier": 101, "resident": 202},
        )

    def request(self):
        return {
            "event_type": "SOCIAL_REQUEST", "event_version": 1,
            "event_id": "request-event-1", "minute": 7, "sequence": 11,
            "producer_version": LEDGER_PRODUCER, "sealed": True,
            "typed_args": {
                "request_id": "request-1", "initiator_role": "hero",
                "initiator_actor_id": 101, "recipient_role": "love",
                "recipient_actor_id": 202, "note_id": 77,
                "note_dbref": "#77", "note_key": "note",
                "source_event_id": "proposal-1", "native_intent": {"weight": 10},
                "physical_receipt": {"status": "settled", "before_location_id": 1,
                                     "after_location_id": 202, "recipient_inventory_actor_id": 202},
            },
        }

    def commit(self, decision="accepted", sequence=13, event_id="commit-1"):
        action = "writeLoveNoteAccept" if decision == "accepted" else "writeLoveNoteReject"
        return {"event_type": "SOCIAL_COMMIT", "event_version": 1,
                "event_id": event_id, "minute": 8, "sequence": sequence,
                "producer_version": LEDGER_PRODUCER, "sealed": True,
                "typed_args": {"request_id": "request-1", "note_id": 77,
                               "action_name": action,
                               "settlement_receipt_id": "physical-response-1"}}

    def test_fixed_opportunity_rule_and_no_private_view_fields(self):
        selected = choose_director(self.view(), True)
        self.assertEqual(selected["action"], "OPEN_PASSAGE")
        self.assertEqual(selected["candidates"], ["OPEN_PASSAGE", "NO_OP"])
        self.assertEqual(choose_director(self.view(), False)["action"], "NO_OP")
        self.assertEqual(choose_director(self.view(opportunity_used=True), True)["action"], "NO_OP")
        self.assertEqual(choose_director(self.view(goal_witness_present=True), True)["action"], "NO_OP")
        self.assertEqual(choose_director(self.view(door_closed=False), True)["action"], "NO_OP")
        with self.assertRaises(ValueError):
            choose_director(self.view(resident_private_O={"trust": 1}), True)

    def test_constraint_uses_existing_typedir_event_count_and_accept_or_refusal(self):
        constraint = author_constraint(AUTHOR_DEADLINE)
        self.assertEqual(type(constraint).__name__, "EventCount")
        for decision in ("accepted", "rejected"):
            with self.subTest(decision=decision):
                result = self.evaluate([self.request(), self.response(decision=decision),
                                        self.commit(decision=decision)])
                self.assertEqual(result["verdict"], "SATISFIED")

    def test_proposal_or_unsettled_fake_response_never_witnesses(self):
        proposal = {"event_type": "SOCIAL_REQUEST", "event_version": 1,
                    "event_id": "proposal-1", "minute": 8, "sequence": 11,
                    "producer_version": LEDGER_PRODUCER, "sealed": True,
                    "typed_args": {"intent": "write_love_note"}}
        self.assertEqual(self.evaluate([proposal])["verdict"], "VIOLATED")
        unsettled = self.response()
        unsettled["typed_args"]["physical_receipt"] = {"status": "rejected"}
        self.assertEqual(self.evaluate([self.request(), unsettled, self.commit()])["verdict"], "VIOLATED")

    def test_wrong_B_response_duplicate_and_unsealed_ledger_are_not_passes(self):
        wrong_b = self.response(responder="fake-B")
        self.assertEqual(self.evaluate([self.request(), wrong_b, self.commit()])["verdict"], "VIOLATED")
        duplicate = self.response()
        duplicate2 = copy.deepcopy(duplicate)
        duplicate2["event_id"] = "ledger-response-2"
        duplicate2["sequence"] = 13
        duplicate2["typed_args"]["native_commit_receipt_id"] = "commit-2"
        commit2 = self.commit(event_id="commit-2", sequence=15)
        self.assertEqual(self.evaluate([self.request(), duplicate, duplicate2,
                                        self.commit(sequence=14), commit2])["verdict"], "VIOLATED")
        unsealed = self.evaluate([self.request(), self.response(sealed=False), self.commit()])
        self.assertEqual(unsealed["verdict"], "INDETERMINATE")

    def test_duplicate_event_identity_and_mutated_producer_are_rejected(self):
        row = self.response()
        duplicate = copy.deepcopy(row)
        duplicate["sequence"] = 13
        self.assertEqual(self.evaluate([row, duplicate])["verdict"], "INDETERMINATE")
        bad_source = self.response(producer_version="planner-proposal")
        self.assertEqual(self.evaluate([bad_source])["verdict"], "INDETERMINATE")

    def test_monitor_never_returns_world_write_or_director_mutation(self):
        result = choose_director(self.view(), True)
        self.assertEqual(set(result), {"action", "candidates", "reason"})
        self.assertNotIn("state", result)
        self.assertNotIn("door_closed", result)


if __name__ == "__main__":
    unittest.main()
