from __future__ import annotations

import unittest

from candidate_generation_v1 import _possessions, generate_action_candidates, support_diagnostic
from theory_s_v1 import TheoryPersonality, TheoryState, score_candidates


def snapshot():
    return {"actor": "person", "entities": [
        {"id": "o1", "label": "a lantern", "kind": "object", "type": "lantern", "facts": {}},
        {"id": "o2", "label": "a bed", "kind": "object", "facts": {}},
        {"id": "a1", "label": "a person", "kind": "agent", "facts": {}},
        {"id": "a2", "label": "a fairy", "kind": "agent", "facts": {}},
    ], "possessions": [{"id": "p1", "label": "a red brick", "facts": {}}],
        "source_candidates": ["a forbidden source action"]}


class MechanismSanityTests(unittest.TestCase):
    def test_generator_never_reads_source_candidates(self):
        class NoAStar(dict):
            def get(self, key, default=None):
                assert key not in {"source_candidates", "source_action_A_star", "candidate_set_factual"}
                return super().get(key, default)
        generated = generate_action_candidates(NoAStar(snapshot()))
        self.assertTrue(generated)
        self.assertTrue(all("forbidden" not in item["action"] for item in generated))

    def test_records_are_auditable_and_possession_is_not_cleared(self):
        generated = generate_action_candidates(snapshot())
        families = {x["semantic_family"] for x in generated}
        self.assertTrue({"inspect", "social_communication", "social_contact", "physical_conflict", "release", "transfer"} <= families)
        self.assertTrue(all(x["rule_id"] and x["supporting_evidence"] is not None for x in generated))
        self.assertTrue(any(x["action"].startswith("drop red brick") for x in generated))
        self.assertTrue(any(x["action"].startswith("give red brick to fairy") for x in generated))

    def test_wearing_and_wielding_relations_are_not_recast_as_carrying(self):
        scene = snapshot()
        scene["possessions"] = [
            {"id": "coat", "label": "a coat", "possession_relation": "wearing",
             "facts": {"wearable": True}},
            {"id": "sword", "label": "a sword", "possession_relation": "wielding",
             "facts": {"wieldable": True}},
            {"id": "cloak", "label": "a cloak", "possession_relation": "carrying",
             "facts": {"wearable": True}},
        ]
        scene["wearing"] = [{"id": "coat", "label": "a coat", "facts": {"wearable": True}}]
        scene["wielding"] = [{"id": "sword", "label": "a sword", "facts": {"wieldable": True}}]
        generated = generate_action_candidates(scene)
        actions = {x["action"] for x in generated}
        self.assertNotIn("drop coat", actions)
        self.assertNotIn("give coat to fairy", actions)
        self.assertNotIn("drop sword", actions)
        self.assertNotIn("give sword to fairy", actions)
        self.assertIn("wear cloak", actions)
        equipped = [x for x in generated if x["action"] in {"drop coat", "give coat to fairy", "drop sword", "give sword to fairy"}]
        self.assertFalse(equipped)
        relations = {e.get("possession_relation") for e in _possessions(scene)
                     if e.get("id") in {"coat", "sword"}}
        self.assertIn("wearing", relations)
        self.assertIn("wielding", relations)

    def test_unknown_portability_does_not_generate_take(self):
        generated = generate_action_candidates(snapshot())
        self.assertFalse(any(x["action"].startswith("take ") for x in generated))
        diagnostic = support_diagnostic(generated, ["get lantern"], snapshot())
        self.assertEqual(diagnostic["support_rows"][0]["miss_reason"], "hidden/unknown fact")

    def test_support_check_is_posthoc_and_keeps_miss_reason(self):
        generated = generate_action_candidates(snapshot())
        diagnostic = support_diagnostic(generated, ["a forbidden source action", "put fairy on bed"], snapshot())
        self.assertFalse(diagnostic["source_candidates_used_for_generation"])
        self.assertEqual(diagnostic["miss_reason_counts"]["ontology"], 2)

    def test_s_intervention_preserves_support_and_changes_distribution(self):
        generated = generate_action_candidates(snapshot())
        before = score_candidates(generated, TheoryState(0.20, 0.80, 0.10), TheoryPersonality())
        after = score_candidates(generated, TheoryState(0.85, 0.15, 0.85), TheoryPersonality())
        self.assertEqual([x["action_id"] for x in before], [x["action_id"] for x in after])
        self.assertTrue(any(abs(a["probability"] - b["probability"]) > 1e-6 for a, b in zip(before, after)))

    def test_p_and_s_change_scores_but_not_support(self):
        generated = generate_action_candidates(snapshot())
        base_ids = [x["action_id"] for x in generated]
        p_low = TheoryPersonality(stimulation_seeking=0.15)
        p_high = TheoryPersonality(stimulation_seeking=0.85)
        p_before = score_candidates(generated, TheoryState(), p_low)
        p_after = score_candidates(generated, TheoryState(), p_high)
        s_before = score_candidates(generated, TheoryState(engagement=0.15), TheoryPersonality())
        s_after = score_candidates(generated, TheoryState(engagement=0.85), TheoryPersonality())
        self.assertEqual(base_ids, [x["action_id"] for x in p_before])
        self.assertEqual(base_ids, [x["action_id"] for x in p_after])
        self.assertEqual(base_ids, [x["action_id"] for x in s_before])
        self.assertEqual(base_ids, [x["action_id"] for x in s_after])
        self.assertTrue(any(abs(a["probability"] - b["probability"]) > 1e-6 for a, b in zip(p_before, p_after)))
        self.assertTrue(any(abs(a["probability"] - b["probability"]) > 1e-6 for a, b in zip(s_before, s_after)))


if __name__ == "__main__":
    unittest.main()
