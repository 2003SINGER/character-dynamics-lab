import unittest
import json

from tools.native_platform_v0.p5.bundle import load_bundle, p5_registry
from tools.native_platform_v0.p5.monitor import evaluate_bundle
from tools.trajectory_constraints_v0.trace import Event, Trace
from tools.trajectory_constraints_v0.types import StableEntity


def bundle():
    return load_bundle({
        "schema": "native-author-bundle-v1", "bundle_id": "monitor", "version": 1, "source": "test",
        "constraints": [{"id": "reply", "kind": "event_by_deadline", "event": "note_response",
                         "filters": {"actor": "A", "recipient": "B", "item": "note", "response": "rejected"},
                         "start": 0, "deadline": 6, "hard": True}],
        "branches": [{"id": "reject", "when": {"event": "note_response", "response": "rejected"},
                       "storylet": {"id": "declined", "text": "The answer is no."}}],
        "permissions": {"world_opportunities": ["open_main_passage"], "force_npc_response": False,
                         "max_opportunities": 1, "cost_budget": 1},
    })


class MonitorTests(unittest.TestCase):
    def test_real_sealed_rejection_is_witness_and_storylet_is_content_only(self):
        trace = Trace(now=6)
        trace.add_event(Event("reply-1", "p5_note_response", 5, 3,
                              {"actor": StableEntity("Actor", "A"),
                               "recipient": StableEntity("Actor", "B"),
                               "item": StableEntity("Item", "note"), "response": "rejected"}))
        trace.finalize_events()
        result = evaluate_bundle(bundle(), trace, p5_registry())
        json.dumps(result)
        self.assertEqual(result["hard_status"], "SATISFIED")
        self.assertEqual(result["branches"][0]["status"], "ELIGIBLE")
        self.assertEqual(result["branches"][0]["event_id"], "reply-1")
        self.assertFalse(result["storylets_execute_world_effects"])

    def test_proposal_like_event_cannot_witness_and_open_ledger_is_indeterminate(self):
        trace = Trace(now=6)
        trace.add_event(Event("proposal", "p5_note_response", 5, 1,
                              {"actor": StableEntity("Actor", "A"),
                               "recipient": StableEntity("Actor", "B"),
                               "item": StableEntity("Item", "note"), "response": "rejected"},
                              provenance="delivered_observation"))
        # The TypedIR monitor itself rejects a non-ledger event selector before
        # it can become a witness. Missing evidence remains uncertain.
        with self.assertRaises(ValueError):
            evaluate_bundle(bundle(), trace)
        empty = Trace(now=6)
        result = evaluate_bundle(bundle(), empty)
        self.assertEqual(result["hard_status"], "INDETERMINATE")
        self.assertEqual(result["branches"][0]["status"], "WAITING")

    def test_absence_only_becomes_violated_after_complete_through_deadline(self):
        trace = Trace(now=4)
        trace.finalize_events()
        self.assertEqual(evaluate_bundle(bundle(), trace)["hard_status"], "PENDING")
        trace = Trace(now=6)
        trace.finalize_events()
        self.assertEqual(evaluate_bundle(bundle(), trace)["hard_status"], "VIOLATED")


if __name__ == "__main__":
    unittest.main()
