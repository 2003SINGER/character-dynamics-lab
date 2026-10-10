import copy
import unittest

from tools.native_platform_v0.p5.bundle import BundleError, BundleStore, VersionConflict, load_bundle


def sample():
    return {
        "schema": "native-author-bundle-v1", "bundle_id": "story-1", "version": 1,
        "source": "manual", "constraints": [
            {"id": "goal-note", "kind": "event_by_deadline", "event": "note_response",
             "filters": {"actor": "A", "recipient": "B", "item": "note", "response": "rejected"},
             "start": 0, "deadline": 12, "hard": True, "min_count": 1},
        ],
        "branches": [
            {"id": "branch-no", "when": {"event": "note_response", "response": "rejected"},
             "storylet": {"id": "story-no", "text": "A refusal."}},
            {"id": "branch-yes", "when": {"event": "note_response", "response": "accepted"},
             "storylet": {"id": "story-yes", "text": "An acceptance."}},
        ],
        "permissions": {"world_opportunities": ["open_main_passage", "open_side_passage"],
                        "force_npc_response": False, "max_opportunities": 1, "cost_budget": 2},
    }


class BundleTests(unittest.TestCase):
    def test_compiles_registered_event_and_branch_schema(self):
        bundle = load_bundle(sample())
        self.assertEqual(bundle.constraints[0].event_type, "p5_note_response")
        self.assertEqual(len(bundle.branches), 2)

    def test_json_text_with_long_single_line_is_not_treated_as_path(self):
        import json
        bundle = load_bundle(json.dumps(sample()))
        self.assertEqual(bundle.bundle_id, "story-1")

    def test_unknown_semantics_and_malformed_permission_fail_closed(self):
        bad = sample()
        bad["constraints"][0]["event"] = "proposal_text"
        with self.assertRaises(BundleError) as raised:
            load_bundle(bad)
        self.assertEqual(raised.exception.code, "SEMANTIC_GAP")
        bad = sample()
        bad["permissions"]["world_opportunities"] = [{}]
        with self.assertRaises(BundleError):
            load_bundle(bad)

    def test_fixed_physical_budget_cannot_be_expanded(self):
        with self.assertRaises(BundleError) as raised:
            load_bundle(sample(), physical_budget=3)
        self.assertEqual(raised.exception.code, "INVALID_BUDGET")

    def test_cas_and_future_only_updates_are_atomic(self):
        initial = sample()
        store = BundleStore(load_bundle(initial))
        edited = copy.deepcopy(initial)
        edited["version"] = 2
        edited["constraints"][0]["deadline"] = 18
        updated = store.replace(edited, 1, now=5)
        self.assertEqual(updated.version, 2)
        self.assertEqual(updated.goals[0].deadline, 18)
        with self.assertRaises(VersionConflict):
            store.replace(initial, 1, now=5)
        self.assertIs(store.current, updated)

    def test_new_goal_cannot_be_added_retroactively_or_change_closed_goal(self):
        initial = sample()
        store = BundleStore(load_bundle(initial))
        retro = copy.deepcopy(initial)
        retro["version"] = 2
        retro["constraints"].append({"id": "delivery", "kind": "event_by_deadline",
             "event": "delivery_settled", "filters": {"actor": "A", "item": "courier_supply"},
             "start": 0, "deadline": 20, "hard": True})
        with self.assertRaises(BundleError) as raised:
            store.replace(retro, 1, now=5)
        self.assertEqual(raised.exception.code, "RETROACTIVE_CONSTRAINT")
        self.assertEqual(store.current.version, 1)
        changed = copy.deepcopy(initial)
        changed["version"] = 2
        changed["constraints"][0]["deadline"] = 20
        with self.assertRaises(BundleError) as raised:
            store.replace(changed, 1, now=12)
        self.assertEqual(raised.exception.code, "HISTORICAL_CONSTRAINT_IMMUTABLE")
        self.assertEqual(store.current.version, 1)

    def test_completed_goal_cannot_be_rewritten(self):
        initial = sample()
        store = BundleStore(load_bundle(initial))
        changed = copy.deepcopy(initial)
        changed["version"] = 2
        changed["constraints"][0]["deadline"] = 20
        with self.assertRaises(BundleError):
            store.replace(changed, 1, now=5, completed_constraint_ids={"goal-note"})
        self.assertEqual(store.current.version, 1)


if __name__ == "__main__":
    unittest.main()
