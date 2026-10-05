from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("audit_light_prediction_admission_v1.py")
SPEC = importlib.util.spec_from_file_location("light_admission_audit", MODULE_PATH)
audit = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(audit)


def row(episode: str, actor: str, step: int, *, o: str = "room", gold: str = "wave",
        candidates: list[str] | None = None, prior_o: str = "prior",
        prior_a: str = "look", depth: int = 2, pair: bool = False) -> dict:
    return {
        "trajectory_id": episode,
        "actor": actor,
        "target_step_index": step,
        "source_O": o,
        "source_action_A_star": gold,
        "candidate_set_factual": candidates if candidates is not None else ["wave", "wait"],
        "previous_source_O": o if pair else prior_o,
        "previous_source_action_A_star": gold if pair else prior_a,
        "previous2_source_O": None,
        "previous2_source_action_A_star": None,
        "actor_history_depth": depth,
        "exact_previous_pair": pair,
        "raw_action_repeat": pair,
        "a_star_in_source_candidates": True,
        "previous_a_star_in_current_candidates": prior_a in (candidates or ["wave", "wait"]),
    }


class AdmissionAuditTests(unittest.TestCase):
    def test_split_is_episode_grouped_and_metrics_exclude_bucket9(self):
        eps = {}
        for i in range(100):
            name = f"episode-{i}"
            split, bucket = audit.split_for_episode(name)
            eps.setdefault(name, split)
            self.assertEqual(eps[name], split)
            self.assertEqual(split, "train" if bucket < 7 else "validation" if bucket < 9 else "excluded_bucket9")
        rows = [row("same", "a", 0), row("same", "b", 1), row("other", "a", 0)]
        summary, prepared = audit.analyze_rows(rows)
        self.assertEqual(sum(v["rows"] for v in summary["split_counts"].values()), 3)
        self.assertFalse(summary["shortcut_diagnostics"]["excluded_bucket9_used"])
        self.assertTrue(all(r["_split"] == audit.split_for_episode(r["trajectory_id"])[0] for r in prepared))

    def test_support_ambiguity_and_literal_proxy(self):
        rows = [
            row("e1", "a", 0, o="wave is listed here", candidates=["wave", "wait"]),
            row("e2", "a", 0, gold="wave", candidates=["Wave", " wave "]),
            row("e3", "a", 0, gold="jump", candidates=["wave"]),
            row("e4", "a", 0, candidates=[]),
        ]
        summary, _ = audit.analyze_rows(rows)
        for split in ("train", "validation", "excluded_bucket9"):
            support = summary["support"][split]
            expected = [r for r in rows if audit.split_for_episode(r["trajectory_id"])[0] == split]
            self.assertEqual(support["normalized_gold_ambiguous_rows"], sum(
                len(audit.candidate_info(r)["matches"]) > 1 for r in expected))
        self.assertTrue(all("proxy only" in x["interpretation"] for x in summary["target_text_in_current_O"].values()))
        self.assertTrue(summary["golden_semantic_verifier"] is False)

    def test_shortcut_uses_train_mode_and_validation_out_of_range_miss(self):
        rows = []
        # Find train/validation episode IDs with deterministic protocol buckets.
        train_id = next(f"t{i}" for i in range(1000) if audit.split_for_episode(f"t{i}")[0] == "train")
        val_id = next(f"v{i}" for i in range(1000) if audit.split_for_episode(f"v{i}")[0] == "validation")
        rows.extend([row(train_id, "a", i, candidates=["x", "wave", "y"], gold="wave") for i in range(3)])
        rows.append(row(val_id, "a", 0, candidates=["wave"], gold="wave"))
        summary, _ = audit.analyze_rows(rows)
        diag = summary["shortcut_diagnostics"]
        self.assertEqual(diag["train_majority_position"], 1)
        self.assertEqual(diag["validation_guess_accuracy"]["train_majority_position"]["out_of_range_miss"], 1)
        self.assertEqual(diag["validation_guess_accuracy"]["first_candidate"]["correct"], 1)

    def test_review_sample_is_fixed_and_pending_audit_only(self):
        rows = [row(f"e{i // 2}", f"a{i % 2}", i, depth=1 + i % 3, pair=bool(i % 2)) for i in range(60)]
        _, prepared = audit.analyze_rows(rows)
        _, reversed_prepared = audit.analyze_rows(list(reversed(rows)))
        first = [audit.make_review_record(x) for x in audit.select_review_rows(prepared)]
        second = [audit.make_review_record(x) for x in audit.select_review_rows(reversed_prepared)]
        self.assertEqual(first, second)
        self.assertEqual(len(first), 24)
        self.assertTrue(all(x["review_scope"] == "AUDIT_ONLY" and
                            x["human_admission_status"] == "PENDING" and
                            x["human_semantic_judgment"] == "PENDING" and
                            x["model_output"] == "NOT_AVAILABLE" for x in first))
        self.assertTrue(all(x["split"] != "excluded_bucket9" for x in first))
        self.assertTrue(all(all(k in x for k in ("trajectory_id", "actor", "target_step_index")) for x in first))

    def test_run_audit_exclusive_output_and_unchanged_input(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source = base / "tiny.jsonl"
            source_bytes = (json.dumps(row("tiny", "actor", 0), ensure_ascii=False) + "\n").encode()
            source.write_bytes(source_bytes)
            output = base / "out"
            audit.run_audit(source, output, enforce_cohort=False)
            self.assertEqual(source.read_bytes(), source_bytes)
            snapshot = {p.name: p.read_bytes() for p in output.iterdir()}
            with self.assertRaises(FileExistsError):
                audit.run_audit(source, output, enforce_cohort=False)
            self.assertEqual(snapshot, {p.name: p.read_bytes() for p in output.iterdir()})
            with self.assertRaises(ValueError):
                audit.run_audit(source, source, enforce_cohort=False)
            self.assertEqual(source.read_bytes(), source_bytes)

    def test_wrong_cohort_fails_before_creating_output(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            source = base / "not_the_cohort.jsonl"
            source.write_text(json.dumps(row("tiny", "actor", 0)) + "\n", encoding="utf-8")
            output = base / "must_not_exist"
            with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
                audit.run_audit(source, output, enforce_cohort=True)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
