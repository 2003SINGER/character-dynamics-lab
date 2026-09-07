from __future__ import annotations

import unittest

from candidate_generation_v1 import generate_action_candidates, support_diagnostic
from theory_s_v1 import TheoryPersonality, TheoryState, score_candidates


def snapshot():
    return {
        "actor": "person",
        "entities": [
            {"id": "o1", "label": "a lantern", "kind": "object", "facts": {}},
            {"id": "o2", "label": "a bed", "kind": "object", "facts": {}},
            {"id": "a1", "label": "a person", "kind": "agent", "facts": {}},
            {"id": "a2", "label": "a fairy", "kind": "agent", "facts": {}},
        ],
        "source_candidates": ["a forbidden source action"],
    }


class MechanismSanityTests(unittest.TestCase):
  def test_generator_never_reads_source_candidates(self):
    class NoAStar(dict):
        def get(self, key, default=None):
            assert key != "source_candidates"
            return super().get(key, default)

    s = NoAStar(snapshot())
    generated = generate_action_candidates(s)
    self.assertEqual(len(generated), 4)
    self.assertTrue(all("forbidden" not in item["action"] for item in generated))


  def test_support_check_is_posthoc(self):
    generated = generate_action_candidates(snapshot())
    diagnostic = support_diagnostic(generated, snapshot()["source_candidates"])
    self.assertFalse(diagnostic["source_candidates_used_for_generation"])
    self.assertEqual(diagnostic["generated_count"], 4)


  def test_s_intervention_preserves_support_and_changes_distribution(self):
    generated_before = generate_action_candidates(snapshot())
    generated_after = generate_action_candidates(snapshot())
    generated = generated_before
    before = score_candidates(generated, TheoryState(0.20, 0.80, 0.10), TheoryPersonality())
    after = score_candidates(generated, TheoryState(0.85, 0.15, 0.85), TheoryPersonality())
    self.assertEqual([x["action_id"] for x in generated_before], [x["action_id"] for x in generated_after])
    self.assertTrue(any(abs(a["probability"] - b["probability"]) > 1e-6 for a, b in zip(before, after)))


if __name__ == "__main__":
    unittest.main()
