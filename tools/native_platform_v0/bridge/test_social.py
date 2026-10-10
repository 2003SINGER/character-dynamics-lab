"""Focused tests for native-candidate selection and Evennia social settlement."""

import unittest

from social import execute_social, propose_social


class Attributes:
    def __init__(self):
        self.values = {}

    def get(self, key, category=None, default=None):
        return self.values.get((category, key), default)

    def add(self, key, value, category=None):
        self.values[(category, key)] = value


class LiveObject:
    def __init__(self, object_id, role, room_id):
        self.id = object_id
        self.ensemble_character_id = role
        self.location_id = room_id
        self.attributes = Attributes()
        self.messages = []
        self.created_notes = []

    def msg(self, text):
        self.messages.append(text)

    def create_social_note(self, target, proposal):
        note = LiveObject(f"note:{proposal['event_id']}", "item", self.location_id)
        note.location_id = target.id
        self.created_notes.append(note)
        return note


class FakeClient:
    def __init__(self, actions):
        self.actions = actions
        self.calls = []

    def request(self, payload):
        self.calls.append(payload)
        if payload["op"] == "propose":
            self.proposed_facts = payload["facts"]
            return {"ok": True, "proposalId": "p1:event-1", "recordRevision": 4,
                    "actions": self.actions, "volitions": [{"weight": 20}]}
        if payload["op"] == "authorize":
            return {"ok": True}
        if payload["op"] == "commit":
            return {"ok": True, "socialRecord": [{"action": payload["actionName"]}],
                    "trace": {"doActionCalled": True, "triggerCalled": True, "nextStepCalled": True}}
        raise AssertionError(payload)

    def settlement_proof(self, proposal_id, event_id, action_name, receipt_id):
        return "test-proof"


def candidate(name, weight, **extra):
    return {"name": name, "weight": weight, "salience": weight,
            "isAccept": False, "failMessage": f"native:{name}", **extra}


class NativeCandidateSelectionTests(unittest.TestCase):
    def setUp(self):
        self.actor = LiveObject("#1", "hero", 7)
        self.target = LiveObject("#2", "love", 7)
        self.client = FakeClient([
            candidate("writeLoveNoteReject", 20),
            candidate("kissFail", 20),
        ])
        self.view = {"target": self.target, "target_visible": True, "room_id": 7,
                     "observed_ensemble_facts": [{"category": "trait", "type": "anyone", "first": "hero", "value": True}]}

    def test_selects_only_returned_supported_candidates_and_records_native_tie(self):
        selected_names = set()
        for seed in range(64):
            self.view["source_event_id"] = f"event-{seed}"
            result = propose_social(self.actor, self.view, {"ensemble_client": self.client}, seed)
            self.assertTrue(result["ok"])
            self.assertIn(result["action_name"], {"writeLoveNoteReject", "kissFail"})
            self.assertEqual(result["native_weight"], 20)
            self.assertEqual(result["selection"]["native_candidate_names"], ["writeLoveNoteReject", "kissFail"])
            self.assertEqual(result["selection"]["rule"], "max_native_weight_then_seeded_tie_among_supported_winners")
            self.assertEqual(result["selection"]["selected_name"], result["action_name"])
            selected_names.add(result["action_name"])
        self.assertEqual(selected_names, {"writeLoveNoteReject", "kissFail"})

    def test_keeps_actor_local_observation_out_of_shared_ensemble_record(self):
        self.view["observed_ensemble_facts"] = [{"category": "trait", "type": "anyone", "first": "hero", "value": True}]
        shared = {"ensemble_client": self.client, "global_social_record": [{"secret": "not local knowledge"}]}
        result = propose_social(self.actor, self.view, shared, 3)
        self.assertTrue(result["ok"])
        self.assertEqual(self.client.proposed_facts, [])
        self.assertFalse(result["observed_evidence"]["global_shared_record_copied_into_actor_O"])
        self.assertFalse(result["observed_evidence"]["actor_private_observation_injected_into_Ensemble"])

    def test_higher_native_weight_wins_before_seeded_tie_break(self):
        self.client.actions = [candidate("writeLoveNoteReject", 8), candidate("kissFail", 21)]
        self.view["source_event_id"] = "weighted-event"
        result = propose_social(self.actor, self.view, {"ensemble_client": self.client}, 0)
        self.assertEqual(result["action_name"], "kissFail")
        self.assertEqual(result["native_weight"], 21)
        self.assertEqual(result["selection"]["native_winning_tie_names"], ["kissFail"])

    def test_unsupported_higher_native_candidate_blocks_lower_supported_fallback(self):
        self.client.actions = [candidate("writeLoveNoteReject", 20), candidate("writeLoveNoteAccept", 99)]
        self.view["source_event_id"] = "unsupported-top"
        result = propose_social(self.actor, self.view, {"ensemble_client": self.client}, 0)
        self.assertEqual(result["status"], "UNSUPPORTED_NATIVE_ACTION")
        self.assertEqual(result["native_weight"], 99)
        self.assertEqual(result["selection"]["native_winning_tie_names"], ["writeLoveNoteAccept"])
        self.assertEqual(result["selection"]["unsupported_native_winners"], ["writeLoveNoteAccept"])

    def test_supported_candidate_can_be_selected_only_within_equal_native_winning_tie(self):
        self.client.actions = [candidate("writeLoveNoteReject", 99), candidate("writeLoveNoteAccept", 99)]
        self.view["source_event_id"] = "mixed-top-tie"
        result = propose_social(self.actor, self.view, {"ensemble_client": self.client}, 0)
        self.assertTrue(result["ok"])
        self.assertEqual(result["native_weight"], 99)
        self.assertEqual(result["selection"]["native_winning_tie_names"], ["writeLoveNoteReject", "writeLoveNoteAccept"])
        self.assertEqual(result["selection"]["supported_winning_tie_names"], ["writeLoveNoteReject"])
        self.assertEqual(result["selection"]["unsupported_native_winners"], ["writeLoveNoteAccept"])

    def test_requires_currently_visible_target(self):
        self.view["target_visible"] = False
        result = propose_social(self.actor, self.view, {"ensemble_client": self.client}, 3)
        self.assertEqual(result["status"], "NO_CANDIDATE")
        self.assertEqual(self.client.calls, [])


class EvenniaSettlementTests(unittest.TestCase):
    def setUp(self):
        self.actor = LiveObject("#1", "hero", 7)
        self.target = LiveObject("#2", "love", 7)

    def proposal(self, action):
        native = candidate(action, 20)
        return {"ok": True, "status": "PROPOSED", "event_id": f"event-{action}",
                "proposal_id": f"p1:event-{action}", "actor_id": "#1", "target_id": "#2",
                "observed_room_id": 7, "action_name": action, "native_weight": 20,
                "native_action": native}

    def test_world_rejection_has_no_item_receipt_or_native_commit(self):
        client = FakeClient([])
        proposal = self.proposal("writeLoveNoteReject")
        self.target.location_id = 8
        result = execute_social(client, proposal, {"actor": self.actor, "target": self.target})
        self.assertEqual(result["status"], "WORLD_VALIDATION_REJECTED")
        self.assertFalse(result["receipt_created"])
        self.assertFalse(result["ensemble_commit_called"])
        self.assertEqual(self.actor.created_notes, [])
        self.assertEqual(client.calls, [])

    def test_note_candidate_causes_real_transfer_receipt_then_native_commit(self):
        client = FakeClient([])
        proposal = self.proposal("writeLoveNoteReject")
        result = execute_social(client, proposal, {"actor": self.actor, "target": self.target})
        self.assertTrue(result["ok"])
        self.assertEqual(result["world_effect"], "note delivered to target inventory")
        self.assertEqual(len(self.actor.created_notes), 1)
        self.assertEqual(self.actor.attributes.get("native_social_events", category="native_social")[0]["event_id"], proposal["event_id"])
        self.assertEqual([call["op"] for call in client.calls], ["authorize", "commit"])
        self.assertEqual(client.calls[-1]["actionName"], "writeLoveNoteReject")

    def test_kiss_failure_has_typed_event_receipt_and_commits_exact_candidate(self):
        client = FakeClient([])
        proposal = self.proposal("kissFail")
        result = execute_social(client, proposal, {"actor": self.actor, "target": self.target})
        self.assertTrue(result["ok"])
        self.assertEqual(result["world_effect"], "rejected attempt recorded; no physical transfer")
        self.assertEqual(result["action_name"], "kissFail")
        self.assertEqual(client.calls[-1]["actionName"], "kissFail")
        self.assertEqual(self.actor.attributes.get("native_social_events", category="native_social")[0]["outcome"], "rejected")


if __name__ == "__main__":
    unittest.main()
