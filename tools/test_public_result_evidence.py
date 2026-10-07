import json
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import project_public_result_evidence as projection


class PublicResultProjectionTests(unittest.TestCase):
    def test_nested_source_text_removed_but_numeric_results_and_safe_labels_remain(self):
        source = {
            "source_record_id": "record-opaque-7",
            "trajectory_id": "trajectory-opaque-2",
            "semantic_rules_version": "rules-v3",
            "candidate_semantic_groups": ["recovery", "goal_progress"],
            "candidate_probabilities": {"a": 0.75, "b": 0.25},
            "nll": 0.287682072,
            "state_at_decision": {"satisfaction": 0.4, "fatigue": 0.2},
            "source_O": "PRIVATE SOURCE OBSERVATION MUST NOT LEAK",
            "source_action_A_star": "PRIVATE SOURCE ACTION MUST NOT LEAK",
            "candidate_set_factual": [{"text": "CANDIDATE RAW TEXT MUST NOT LEAK", "probability": 1.0}],
            "previous_action": "PREVIOUS SOURCE ACTION MUST NOT LEAK",
            "candidate_scene_bindings": [{"scene": {"description": "SCENE RAW TEXT MUST NOT LEAK"}, "target_visible_in_O": True}],
            "X": {"free_text": "NESTED X TEXT MUST NOT LEAK", "transition_events": [{"kind": "update", "t": 3}]},
            "unclassified_label": "UNKNOWN STRING MUST NOT LEAK",
        }
        counts = Counter()
        result = projection.project_value(source, counts=counts)
        encoded = json.dumps(result, ensure_ascii=False)
        for secret in ("PRIVATE SOURCE", "CANDIDATE RAW", "PREVIOUS SOURCE", "SCENE RAW", "NESTED X", "UNKNOWN STRING"):
            self.assertNotIn(secret, encoded)
        self.assertEqual(result["candidate_probabilities"], [
            {"ordinal": 0, "value": 0.75}, {"ordinal": 1, "value": 0.25},
        ])
        self.assertEqual(result["nll"], 0.287682072)
        self.assertEqual(result["state_at_decision"], {"satisfaction": 0.4, "fatigue": 0.2})
        self.assertEqual(result["candidate_semantic_groups"], ["recovery", "goal_progress"])
        self.assertEqual(result["source_record_id"], "record-opaque-7")
        self.assertGreater(counts["source_O"], 0)

    def test_jsonl_projection_keeps_row_count_and_records_removed_keys(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "source.jsonl"
            path.write_text("\n".join([
                json.dumps({"trajectory_id": "t1", "source_O": "raw one", "nll": 0.1}),
                json.dumps({"trajectory_id": "t2", "previous_action": "raw two", "rank": 2}),
            ]) + "\n", encoding="utf-8")
            data, rows, removed = projection.project_file(path)
            projected = [json.loads(line) for line in data.decode().splitlines()]
            self.assertEqual(rows, 2)
            self.assertEqual(len(projected), 2)
            self.assertEqual([row["trajectory_id"] for row in projected], ["t1", "t2"])
            self.assertEqual([row.get("nll", row.get("rank")) for row in projected], [0.1, 2])
            self.assertEqual(removed["source_O"], 1)
            self.assertEqual(removed["previous_action"], 1)

    def test_prediction_validation_losses_keep_loss_map_and_ids_but_drop_source_action(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "validation_row_losses.jsonl"
            path.write_text(json.dumps({
                "actor": "source_actor_name",
                "actor_history_depth": 4,
                "candidate_count": 7,
                "exact_previous_pair": True,
                "losses_nats": {"fixed_mean_seed19": 0.43, "gru_seed19": 0.78,
                                "RAW CONDITION LABEL": 0.91},
                "normalized_gold_ambiguity": False,
                "source_action_A_star": "SOURCE ACTION TEXT MUST NOT LEAK",
                "target_absent_from_normalized_support": False,
                "target_step_index": 12,
                "trajectory_id": "trajectory-opaque",
            }) + "\n", encoding="utf-8")
            data, rows, _ = projection.project_file(path)
            result = json.loads(data.decode().splitlines()[0])
            encoded = json.dumps(result)
            self.assertEqual(rows, 1)
            self.assertNotIn("SOURCE ACTION TEXT", encoded)
            self.assertNotIn("source_actor_name", encoded)
            self.assertEqual(result["trajectory_id"], "trajectory-opaque")
            self.assertFalse(result["normalized_gold_ambiguity"])
            self.assertFalse(result["target_absent_from_normalized_support"])
            self.assertEqual(result["losses_nats"]["fixed_mean_seed19"], 0.43)
            self.assertEqual(result["losses_nats"]["gru_seed19"], 0.78)
            self.assertEqual(result["losses_nats"]["unknown_map_entries"], [
                {"ordinal": 2, "value": 0.91},
            ])

    def test_dynamic_probability_map_keys_are_suppressed_without_reordering_values(self):
        counts = Counter()
        result = projection.project_value(
            {"candidate_probabilities": {"RAW SOURCE CANDIDATE A": 0.6, "RAW SOURCE CANDIDATE B": 0.4}},
            counts=counts,
        )
        encoded = json.dumps(result)
        self.assertNotIn("RAW SOURCE CANDIDATE", encoded)
        self.assertEqual(result["candidate_probabilities"], [
            {"ordinal": 0, "value": 0.6}, {"ordinal": 1, "value": 0.4},
        ])
        self.assertEqual(counts["candidate_probabilities::<map-key>"], 2)

    def test_unknown_dynamic_map_uses_ordinals_and_does_not_leak_key_in_manifest_counts(self):
        counts = Counter()
        result = projection.project_value(
            {"metrics": {"RAW SOURCE CANDIDATE AS KEY": 0.7, "ANOTHER SOURCE KEY": 0.3}},
            counts=counts,
        )
        encoded = json.dumps(result) + json.dumps(counts)
        self.assertNotIn("RAW SOURCE CANDIDATE", encoded)
        self.assertNotIn("ANOTHER SOURCE KEY", encoded)
        self.assertEqual(result["metrics"], [
            {"ordinal": 0, "value": 0.7}, {"ordinal": 1, "value": 0.3},
        ])

    def test_mixed_schema_and_unknown_numeric_child_keys_are_safe(self):
        counts = Counter()
        result = projection.project_value(
            {"metrics": {"nll": 0.2, "SOURCE LONG PROSE KEY": 0.8}},
            counts=counts,
        )
        encoded = json.dumps(result) + json.dumps(counts)
        self.assertNotIn("SOURCE LONG PROSE KEY", encoded)
        self.assertEqual(result["metrics"]["nll"], 0.2)
        self.assertEqual(result["metrics"]["unknown_map_entries"], [
            {"ordinal": 1, "value": 0.8},
        ])

    def test_existing_identical_output_is_accepted_but_different_output_is_refused(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "projection.json"
            expected = b'{"safe":1}\n'
            path.write_bytes(expected)
            projection._write_new_or_identical({path: expected})
            with self.assertRaisesRegex(projection.ProjectionError, "refusing to overwrite"):
                projection._write_new_or_identical({path: b'{"safe":2}\n'})

    def test_scene_snapshot_is_explicitly_excluded_from_discovery(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            experiment = root / "outputs/experiments/LIGHT_case"
            experiment.mkdir(parents=True)
            (experiment / "sample.trace.jsonl").write_text('{"nll":0.1}\n', encoding="utf-8")
            (experiment / "LIGHT_scene_snapshot_v0.jsonl").write_text('{"description":"raw"}\n', encoding="utf-8")
            prediction_root = root / "outputs/prediction_baseline_v1_20261006"
            for run in ("run_v1", "reproduction_seed7_v1"):
                run_root = prediction_root / run
                run_root.mkdir(parents=True)
                (run_root / "validation_row_losses.jsonl").write_text('{"losses_nats":{}}\n', encoding="utf-8")
            with patch.object(projection, "REPO_ROOT", root):
                sources, excluded = projection.discover_inputs()
                self.assertEqual(len(sources), 3)
                self.assertEqual(sum(p.name == "validation_row_losses.jsonl" for p in sources), 2)
                self.assertEqual([p.name for p in excluded], ["LIGHT_scene_snapshot_v0.jsonl"])

    def test_check_without_local_sources_uses_manifest_hashes_and_rows(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "outputs/experiments/LIGHT_case/sample.trace.jsonl"
            source.parent.mkdir(parents=True)
            source.write_text('{"trajectory_id":"t1","nll":0.2,"source_O":"raw"}\n', encoding="utf-8")
            with patch.object(projection, "REPO_ROOT", root):
                outputs, _ = projection.build_bundle()
                projection._write_new_or_identical(outputs)
                source.unlink()
                # No source is now available; output bytes/hashes and row counts remain checkable.
                result = projection.check_bundle()
                self.assertFalse(result["source_oracle_available"])
                self.assertEqual(result["checked_outputs"], 1)

    def test_manifest_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / projection.OUTPUT_ROOT
            out.mkdir(parents=True)
            manifest = {
                "schema": projection.SCHEMA,
                "sources": [{"sourcepath": "outputs/experiments/LIGHT_x/file.jsonl",
                             "outputpath": "outputs/public_result_projections_20261007_v2/../../escape.jsonl",
                             "output_sha256": "0" * 64, "rows": 0}],
            }
            (out / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            with patch.object(projection, "REPO_ROOT", root):
                with self.assertRaisesRegex(projection.ProjectionError, "escapes output root"):
                    projection.check_bundle()


if __name__ == "__main__":
    unittest.main()
