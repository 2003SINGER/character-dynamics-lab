"""Portable unit tests for public_review_inventory.py; no project data is edited."""

from __future__ import annotations

import contextlib
import gzip
import hashlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any


MODULE_PATH = Path(__file__).with_name("public_review_inventory.py")
SPEC = importlib.util.spec_from_file_location("public_review_inventory", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
inventory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(inventory)


class PublicReviewInventoryTests(unittest.TestCase):
    def test_cache_and_compiled_paths_are_excluded(self) -> None:
        for path in (
            "outputs/run/__pycache__/module.cpython-312.pyc",
            "outputs/.DS_Store",
            "outputs/run/.experiment.lock",
            "outputs/build/CMakeFiles/target.dir/file.o",
            "outputs/run/libthing.dylib",
        ):
            with self.subTest(path=path):
                self.assertEqual(inventory.path_exclusion(path)[0], "exclude")

    def test_dataset_inputs_and_originals_are_excluded(self) -> None:
        for path in (
            "outputs/external_assets_2026-09-06/LIGHT/light_full.replay.jsonl",
            "outputs/foo/source_input.jsonl",
            "outputs/light_prediction_admission_20261006/review_24.jsonl",
            "outputs/opera_t0d_2026-09-06/terra_candidate_spike_v0/blind_input.json",
            "outputs/clubfloyd_command_v0/verified_command_dev_slice.jsonl",
        ):
            with self.subTest(path=path):
                self.assertEqual(inventory.path_exclusion(path)[0], "exclude")
        self.assertEqual(
            inventory.path_exclusion("outputs/literature_sources/2007.pdf")[0],
            "exclude",
        )
        self.assertIsNone(
            inventory.path_exclusion("outputs/clubfloyd_command_v0/verified_command_dev_slice.manifest.json")
        )
        self.assertIsNone(
            inventory.path_exclusion("outputs/public_result_projections_20261007_v2/light_prediction_admission_20261006/review_24.jsonl")
        )

    def test_dataset_text_fields_are_held_for_projection_but_synthetic_cassettes_are_not(self) -> None:
        source_trace = b'{"source_O":"text","candidate_set_factual":["text"]}'
        self.assertEqual(
            inventory.source_text_field_hits(Path("trace.jsonl"), source_trace),
            {"source_o", "candidate_set_factual"},
        )
        self.assertEqual(
            inventory.source_text_field_hits(Path("trainer_synthetic/input.jsonl"), b'{"recorded_support":["fixture"]}'),
            set(),
        )
        self.assertIsNone(inventory.path_exclusion("outputs/laya_runs/generated_replay.jsonl"))
        self.assertEqual(
            inventory.path_exclusion("outputs/experiments/LIGHT_transition_v0/transition.trace.jsonl")[0],
            "excluded_source_text_requires_projection",
        )
        self.assertEqual(
            inventory.path_exclusion("outputs/T0c_LIGHT_batch4/LIGHT_counterfactual_remove.trace.jsonl")[0],
            "excluded_source_text_requires_projection",
        )
        self.assertEqual(
            inventory.path_exclusion("outputs/opera_t0d_2026-09-08/terra_candidate_spike_v1/candidate_artifact.json")[0],
            "excluded_source_text_requires_projection",
        )
        self.assertEqual(
            inventory.path_exclusion("outputs/public_result_projections_20261007/T0c_LIGHT_batch4/result.trace.jsonl")[0],
            "exclude",
        )
        self.assertIsNone(
            inventory.path_exclusion("outputs/public_result_projections_20261007_v2/opera_t0d_2026-09-08/candidate_artifact.json")
        )

    def test_secrets_report_only_types_and_counts(self) -> None:
        fixture = b"api_key=sk-proj-EXAMPLE_NOT_A_REAL_SECRET_123456"
        matches = inventory.scan_secret_types(fixture)
        self.assertEqual(matches["openai_style_key"], 1)
        self.assertEqual(matches["credential_assignment"], 1)
        with tempfile.TemporaryDirectory(dir=inventory.ROOT) as tmp:
            path = Path(tmp) / "result.json"
            path.write_bytes(fixture)
            row = inventory.classify(path, None)
        self.assertEqual(row["status"], "exclude-review")
        self.assertNotIn("EXAMPLE_NOT_A_REAL_SECRET", row["reason"])

    def test_empty_credential_configuration_is_not_a_secret(self) -> None:
        config = b'{"api_key":null,"access_token":"","password":null}'
        self.assertEqual(inventory.scan_secret_types(config), {})
        with tempfile.TemporaryDirectory(dir=inventory.ROOT) as tmp:
            path = Path(tmp) / "config.json"
            path.write_bytes(config)
            row = inventory.classify(path, None)
        self.assertEqual(row["status"], "publish")

    def test_gzip_payload_is_scanned_after_bounded_decompression(self) -> None:
        with tempfile.TemporaryDirectory(dir=inventory.ROOT) as tmp:
            safe = Path(tmp) / "synthetic-cassette.jsonl.gz"
            with gzip.open(safe, "wb") as stream:
                stream.write(b'{"prompt":"synthetic","raw_answer":"ok"}\n')
            safe_row = inventory.classify(safe, None)
            self.assertEqual(safe_row["status"], "publish")
            self.assertEqual(safe_row["sha256"], hashlib.sha256(safe.read_bytes()).hexdigest())

            secret = Path(tmp) / "synthetic-secret.jsonl.gz"
            with gzip.open(secret, "wb") as stream:
                stream.write(b'{"api_key":"sk-proj-EXAMPLE_NOT_A_REAL_SECRET_123456"}\n')
            secret_row = inventory.classify(secret, None)
            self.assertEqual(secret_row["status"], "exclude-review")
            self.assertNotIn("EXAMPLE_NOT_A_REAL_SECRET", secret_row["reason"])

    def test_small_checkpoint_is_retained_and_large_file_is_excluded_without_hash(self) -> None:
        with tempfile.TemporaryDirectory(dir=inventory.ROOT) as tmp:
            small = Path(tmp) / "weights.pt"
            small.write_bytes(b"small synthetic checkpoint\0")
            small_row = inventory.classify(small, None)
            self.assertEqual(small_row["status"], "publish")
            self.assertIn("checkpoint retained", small_row["reason"])
            self.assertRegex(small_row["sha256"], r"^[0-9a-f]{64}$")

            large = Path(tmp) / "oversize.csv"
            with large.open("wb") as stream:
                stream.truncate(inventory.MAX_BYTES + 1)
            large_row = inventory.classify(large, None)
            self.assertEqual(large_row["status"], "exclude")
            self.assertIsNone(large_row["sha256"])

            boundary = Path(tmp) / "exactly_20mib.csv"
            with boundary.open("wb") as stream:
                stream.truncate(inventory.MAX_BYTES)
            boundary_row = inventory.classify(boundary, None)
            self.assertEqual(boundary_row["status"], "exclude")
            self.assertIsNone(boundary_row["sha256"])

    def test_symlinks_are_not_followed(self) -> None:
        with tempfile.TemporaryDirectory(dir=inventory.ROOT) as tmp:
            target = Path(tmp) / "target.txt"
            link = Path(tmp) / "link.txt"
            target.write_text("sample", encoding="utf-8")
            link.symlink_to(target.name)
            row = inventory.classify(link, None)
        self.assertEqual(row["status"], "exclude-review")
        self.assertIsNone(row["sha256"])

    def test_check_detects_mutated_published_bytes(self) -> None:
        with tempfile.TemporaryDirectory(dir=inventory.ROOT) as tmp:
            directory = Path(tmp)
            artifact = directory / "result.json"
            artifact.write_bytes(b"original")
            relative = artifact.relative_to(inventory.ROOT).as_posix()
            manifest_path = directory / "manifest.json"
            manifest: dict[str, Any] = {
                "schema_version": inventory.SCHEMA_VERSION,
                "candidate_roots": [],
                "size_limit_bytes": inventory.MAX_BYTES,
                "files": [{
                    "path": relative,
                    "bytes": artifact.stat().st_size,
                    "sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
                    "status": "publish",
                    "reason": "test fixture",
                }],
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            artifact.write_bytes(b"mutated")
            with contextlib.redirect_stderr(io.StringIO()):
                result = inventory.check_manifest(manifest_path)
        self.assertEqual(result, 1)

    def test_check_rejects_outside_manifest_and_duplicate_paths(self) -> None:
        with tempfile.TemporaryDirectory() as outside:
            with contextlib.redirect_stderr(io.StringIO()):
                result = inventory.check_manifest(Path(outside) / "missing.json")
        self.assertEqual(result, 2)
        with tempfile.TemporaryDirectory(dir=inventory.ROOT) as tmp:
            manifest_path = Path(tmp) / "manifest.json"
            row = {"path": "outputs/x", "bytes": 0, "sha256": None, "status": "exclude", "reason": "x"}
            manifest_path.write_text(json.dumps({"schema_version": 1, "files": [row, row]}), encoding="utf-8")
            with contextlib.redirect_stderr(io.StringIO()):
                result = inventory.check_manifest(manifest_path)
        self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()
