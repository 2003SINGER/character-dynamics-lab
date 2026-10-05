from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("audit_light_snapshot_timing_v1.py")
SPEC = importlib.util.spec_from_file_location("light_snapshot_timing", MODULE_PATH)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(audit)


class SnapshotTimingDiagnosticsTests(unittest.TestCase):
    def test_before_state_and_isolated_next_same_actor_transition(self):
        ep = audit.synthetic_episode(["get lantern", None, None], ["Ada", "Bert", "Ada"],
                                    [["a lantern"], ["a lantern"], []], [[], [], ["a lantern"]])
        result = audit.diagnose_event(ep, 0)
        self.assertEqual(result["current_state"]["class"], "before_consistent")
        self.assertEqual(result["neighbors"]["next_status"], "current_pre_to_next_post_consistent")

    def test_after_state_and_isolated_previous_same_actor_transition(self):
        ep = audit.synthetic_episode([None, None, "get lantern"], ["Ada", "Bert", "Ada"],
                                    [["a lantern"], ["a lantern"], []], [[], [], ["a lantern"]])
        result = audit.diagnose_event(ep, 2)
        self.assertEqual(result["current_state"]["class"], "after_consistent")
        self.assertEqual(result["neighbors"]["previous_status"], "pre_to_current_post_consistent")

    def test_duplicate_and_alias_risk_are_ambiguous_not_temporal_matches(self):
        duplicate = audit.synthetic_episode(["get lantern"], ["Ada"], [["a lantern"]], [["lantern"]])
        duplicate_result = audit.diagnose_event(duplicate, 0)
        self.assertEqual(duplicate_result["current_state"]["class"], "ambiguous_duplicate_surface")
        self.assertNotEqual(duplicate_result["neighbors"]["next_status"],
                            "current_pre_to_next_post_consistent")

        alias = audit.synthetic_episode(["drop arrow"], ["Ada"], [["a arrowhead"]], [["an arrow"]])
        alias_result = audit.diagnose_event(alias, 0)
        self.assertEqual(alias_result["current_state"]["class"], "ambiguous_alias_risk")
        self.assertIn("arrowhead", alias_result["current_state"]["other_labels_containing_target"])

    def test_no_match_and_unsupported_relation_remain_excluded(self):
        ep = audit.synthetic_episode(["get lantern", "get lantern from basket"], ["Ada", "Ada"],
                                    [[], []], [[], []])
        self.assertEqual(audit.diagnose_event(ep, 0)["current_state"]["class"], "no_exact_state_pattern")
        relation = audit.diagnose_event(ep, 1)
        self.assertFalse(relation["included"])
        self.assertEqual(relation["reason"], "unsupported_command_relation")

    def test_article_bound_is_explicit_and_wear_family_has_relation_specific_state(self):
        nested = audit.synthetic_episode(["get A copper vase"], ["Ada"],
                                         [["a A copper vase"]], [[]])
        self.assertEqual(audit.diagnose_event(nested, 0)["current_state"]["class"],
                         "before_consistent")
        wear = audit.synthetic_episode(["wear shield"], ["Ada"], [[]], [["a shield"]])
        self.assertEqual(audit.diagnose_event(wear, 0)["current_state"]["class"],
                         "before_consistent")

    def test_drop_and_remove_before_after_relations(self):
        drop_before = audit.synthetic_episode(["drop bone", None, None], ["Ada", "Bert", "Ada"],
                                               [[], [], ["a bone"]], [["a bone"], [], []])
        event = audit.diagnose_event(drop_before, 0)
        self.assertEqual(event["current_state"]["class"], "before_consistent")
        self.assertEqual(event["neighbors"]["next_status"], "current_pre_to_next_post_consistent")

        drop_after = audit.synthetic_episode([None, None, "drop bone"], ["Ada", "Bert", "Ada"],
                                              [[], [], ["a bone"]],
                                              [["a bone"], [], []])
        event = audit.diagnose_event(drop_after, 2)
        self.assertEqual(event["current_state"]["class"], "after_consistent")
        self.assertEqual(event["neighbors"]["previous_status"], "pre_to_current_post_consistent")

        remove_before = audit.synthetic_episode(["remove shield", None, None], ["Ada", "Bert", "Ada"],
                                                 [[], [], []], [[], [], ["a shield"]],
                                                 [["a shield"], [], []])
        event = audit.diagnose_event(remove_before, 0)
        self.assertEqual(event["current_state"]["class"], "before_consistent")
        self.assertEqual(event["neighbors"]["next_status"], "current_pre_to_next_post_consistent")

        remove_after = audit.synthetic_episode([None, None, "remove shield"], ["Ada", "Bert", "Ada"],
                                                [[], [], []], [[], [], ["a shield"]],
                                                [["a shield"], [], []])
        event = audit.diagnose_event(remove_after, 2)
        self.assertEqual(event["current_state"]["class"], "after_consistent")
        self.assertEqual(event["neighbors"]["previous_status"], "pre_to_current_post_consistent")

    def test_context_and_available_actions_do_not_enter_the_state_predicate(self):
        ep = audit.synthetic_episode(["get lantern"], ["Ada"], [["a lantern"]], [[]])
        baseline = audit.diagnose_event(ep, 0)
        ep["context"][0] = "POST ACTION POISON: you carry a lantern"
        ep["available_actions"][0] = ["unrelated action"]
        self.assertEqual(audit.diagnose_event(ep, 0), baseline)

    def test_intervening_partner_command_excludes_same_actor_neighbor_support(self):
        ep = audit.synthetic_episode(["get lantern", "drop rock", None], ["Ada", "Bert", "Ada"],
                                    [["a lantern"], ["a lantern"], []], [[], [], ["a lantern"]])
        result = audit.diagnose_event(ep, 0)
        self.assertEqual(result["neighbors"]["next_status"],
                         "excluded_intervening_physical_commands")
        self.assertEqual(result["neighbors"]["next_intervening_commands"][0]["action"],
                         "drop rock")

    def test_malformed_alignment_and_output_overwrite_or_source_overlap_fail_closed(self):
        ep = audit.synthetic_episode(["get key"], ["Ada"], [["key"]], [[]])
        ep["speech"].append(None)
        with self.assertRaisesRegex(ValueError, "misaligned"):
            audit.validate_episode(ep)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.bin"
            source.write_bytes(b"source")
            existing = root / "existing.json"
            existing.write_text("keep", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                audit.output_path_guard(existing, (source,))
            with self.assertRaises(ValueError):
                audit.output_path_guard(root, (source,))
            self.assertEqual(source.read_bytes(), b"source")


if __name__ == "__main__":
    unittest.main()
