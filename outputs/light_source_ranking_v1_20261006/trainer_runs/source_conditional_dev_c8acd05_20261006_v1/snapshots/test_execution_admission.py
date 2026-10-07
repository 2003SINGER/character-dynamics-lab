#!/usr/bin/env python3
"""Synthetic-only adversarial tests for the separate SourceRankingV1 execution gate."""
from __future__ import annotations

import copy
import hashlib
import inspect
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import fit_source
import project_inputs
import train


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def independent_execution_pins() -> dict:
    """Rebuild the pin contract from literals and file bytes, not the pin builder."""
    source_names = ("train.py", "test_train.py", "fit_source.py", "test_execution_admission.py")
    return {
        "input_sha256": "b414f176bf7c6d0e1f47536bab8c251ae7d39ead5b40550310127294f74e5646",
        "projected_sha256": "2d839c62ddf2194b1968fe5b22913db9950aa10bd3647fe2179745b6b4efcef5",
        "protocol_sha256": "5318bffe1f417e6ceb5dc5284fbcbb011808117f775d1225f66d61195528e3cf",
        "builder_sha256": "9c1850e38320ef459b38cc2740cbec6ff948036f8f564c9567f18aebbedc42d4",
        "cohort_key_digest": "3a059162d09e2a8b126c468d9d73d6fa60d582e88d52475350e49b88a20ac1bd",
        "source_key_digest": "905653a6b3125d3136e47aec8eb21125ca4beab0a19c5d11e159d70b1c3827f7",
        "row_count": 13_463,
        "split_counts": {"train": {"rows": 9_530, "episodes": 3_490},
                         "validation": {"rows": 2_717, "episodes": 986},
                         "excluded_bucket9": {"rows": 1_216, "episodes": 468}},
        "split_rule": "bucket=int(SHA256(trajectory_id UTF-8).hexdigest()[:8],16)%10; 0-6=train; 7-8=validation; 9=excluded",
        "conditions": ["context_only", "last2_core", "pooled_core", "gru_core", "gru_no_context",
                       "gru_no_dialogue", "gru_no_persona", "gru_plus_partner_raw_commands", "uniform"],
        "seeds": [7, 19, 31],
        "dimensions": {"persona": 256, "context": 256, "candidate": 256, "history_turn": 453,
                        "speech": 256, "action": 128, "emote": 64, "role": 2, "presence": 3, "state": 16},
        "config": {"batch_size": 32, "max_epochs": 15, "learning_rate": 0.001, "optimizer": "Adam",
                   "weight_decay": 0.0, "scheduler": None, "dropout": 0.0,
                   "bootstrap_replicates": 2_000, "bootstrap_seed": 104_729,
                   "device": "cpu", "torch_threads": 1, "deterministic_algorithms": True},
        "source_sha256": {name: sha256((HERE / name).read_bytes()) for name in source_names},
    }


def admission_record(pins: dict) -> dict:
    return {
        "schema": "light_source_ranking_execution_admission_v1",
        "scope": "SOURCE_CONDITIONAL_DEVELOPMENT",
        "training_authorized": True,
        "actor_forecast": False,
        "runtime_policy": False,
        "formal_test": False,
        "psychological_validity": False,
        "authorization_basis": (
            "Parent implementation review under the user-authorized DEVELOPMENT goal; "
            "this does not admit actor-visible or psychological validity."
        ),
        "parent_implementation_review": True,
        "pins": copy.deepcopy(pins),
    }


def record_bytes(record: dict) -> bytes:
    return (json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def synthetic_projected_row(trajectory_id: str, physical_index: int, label: str,
                            *, partner_command: str = "raw partner command") -> dict:
    bucket = train.episode_bucket(trajectory_id)
    diag = [
        {"role": "self", "speech": f"self clue {label}", "action": f"inspect {label}", "emote": None},
        {"role": "partner", "speech": f"partner clue {label}", "action": partner_command, "emote": "nods"},
    ]
    core = [copy.deepcopy(g) for g in diag]
    core[1]["action"] = None
    refs = []
    for index, group in enumerate(core):
        raw_index = 10 + index * 10
        refs.append({"raw_turn_index": raw_index, "physical_index": index,
                     "role": group["role"], "speaker": "actor" if group["role"] == "self" else "partner",
                     "source_ref": f"episode:{trajectory_id}:turn:{raw_index}"})
    return {
        "schema": "light_source_ranking_input_contract_v1",
        "static_condition": {"self_persona": f"actor prefers {label}",
                             "recorded_environment_snapshot": f"room supports {label}"},
        "history_views": {"core": core, "diagnostic_plus_partner_raw_commands": diag},
        "candidate_surface": {"recorded_support": ["choose red", "choose blue"]},
        "supervision": {"recorded_action": f"choose {label}"},
        "provenance": {"trajectory_id": trajectory_id, "actor": "actor", "split_bucket": bucket,
                       "split": train.split_name(bucket), "target_raw_turn_index": 99,
                       "target_physical_index": physical_index,
                       "target_source_ref": f"synthetic-source:{trajectory_id}:{physical_index}",
                       "payload_history_turn_refs": refs},
        "admission": {"training_authorized": False, "actor_forecast_admitted": False,
                      "warning": "synthetic fixture only"},
    }


def find_episode(bucket: int, prefix: str) -> str:
    for i in range(100_000):
        value = f"{prefix}-{i}"
        if train.episode_bucket(value) == bucket:
            return value
    raise AssertionError(f"could not construct synthetic bucket {bucket}")


class ExecutionAdmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (train.ROOT / "outputs").mkdir(exist_ok=True)
        train.DEFAULT_RUN_ROOT.mkdir(parents=True, exist_ok=True)

    def setUp(self):
        self.expected_pins = independent_execution_pins()
        self.record = admission_record(self.expected_pins)
        self.raw = record_bytes(self.record)

    def test_independent_pins_match_builder_and_freeze_full_scope(self):
        expected = independent_execution_pins()
        observed = fit_source.build_execution_pins()
        self.assertEqual(observed, expected)
        self.assertEqual(set(observed["source_sha256"]),
                         {"train.py", "test_train.py", "fit_source.py", "test_execution_admission.py"})
        self.assertEqual(observed["conditions"], list(train.CONDITIONS))
        self.assertEqual(observed["seeds"], [7, 19, 31])
        self.assertEqual(observed["config"]["max_epochs"], 15)
        self.assertEqual(observed["config"]["bootstrap_replicates"], 2_000)
        self.assertEqual(observed["config"]["bootstrap_seed"], 104_729)
        self.assertEqual(observed["split_counts"], expected["split_counts"])

    def test_gate_requires_exact_authorization_scope_and_no_semantic_upgrade(self):
        accepted = fit_source.verify_execution_admission_bytes(self.raw, self.expected_pins)
        self.assertEqual(accepted, self.record)
        self.assertEqual(fit_source.RECORD_KEYS, set(self.record))
        self.assertIs(accepted["training_authorized"], True)
        for key in ("actor_forecast", "runtime_policy", "formal_test", "psychological_validity"):
            self.assertIs(accepted[key], False, key)
        for key, value in (("training_authorized", False), ("actor_forecast", True),
                           ("runtime_policy", True), ("formal_test", True),
                           ("psychological_validity", True), ("parent_implementation_review", False),
                           ("scope", "ACTOR_VISIBLE_FORECAST"), ("schema", "wrong"),
                           ("authorization_basis", "unreviewed")):
            changed = copy.deepcopy(self.record)
            changed[key] = value
            with self.subTest(field=key), self.assertRaises((ValueError, PermissionError)):
                fit_source.verify_execution_admission_bytes(record_bytes(changed), self.expected_pins)
        for changed in (dict(self.record, unexpected=True),
                        {k: v for k, v in self.record.items() if k != "pins"}):
            with self.assertRaises(ValueError):
                fit_source.verify_execution_admission_bytes(record_bytes(changed), self.expected_pins)
        for bad in (b"", b"{", b"\xff\xfe"):
            with self.assertRaises(ValueError):
                fit_source.verify_execution_admission_bytes(bad, self.expected_pins)

    def test_every_data_code_and_configuration_pin_is_fail_closed(self):
        pin_mutations = [
            ("input_sha256", "0" * 64), ("projected_sha256", "1" * 64),
            ("protocol_sha256", "2" * 64), ("builder_sha256", "3" * 64),
            ("cohort_key_digest", "4" * 64), ("source_key_digest", "5" * 64),
            ("row_count", 13_462), ("split_rule", "row-wise split"),
            ("split_counts", {"train": {"rows": 1, "episodes": 1}}),
            ("conditions", list(reversed(self.expected_pins["conditions"]))),
            ("seeds", [7, 19, 32]), ("dimensions", {**self.expected_pins["dimensions"], "state": 15}),
            ("config", {**self.expected_pins["config"], "max_epochs": 14}),
            ("source_sha256", {**self.expected_pins["source_sha256"], "train.py": "0" * 64}),
        ]
        for key, value in pin_mutations:
            changed = copy.deepcopy(self.record)
            changed["pins"][key] = value
            with self.subTest(pin=key), self.assertRaises(PermissionError):
                fit_source.verify_execution_admission_bytes(record_bytes(changed), self.expected_pins)
        for source_name in self.expected_pins["source_sha256"]:
            changed = copy.deepcopy(self.record)
            changed["pins"]["source_sha256"][source_name] = "f" * 64
            with self.subTest(source=source_name), self.assertRaises(PermissionError):
                fit_source.verify_execution_admission_bytes(record_bytes(changed), self.expected_pins)

    def test_production_reader_is_single_path_and_runner_has_no_grant_switch(self):
        self.assertEqual(set(inspect.signature(fit_source.run_admitted_execution).parameters), {"out"})
        self.assertEqual(set(inspect.signature(fit_source.read_execution_admission).parameters), set())
        self.assertEqual(fit_source.ADMISSION_PATH.name, "EXECUTION_ADMISSION.json")
        self.assertEqual(fit_source.RUN_ROOT, train.DEFAULT_RUN_ROOT)
        self.assertFalse(callable(getattr(fit_source, "set_execution_authorized", None)))
        with self.assertRaises(SystemExit):
            fit_source.main(["--admission", "/tmp/alternate.json"])
        with tempfile.TemporaryDirectory(dir=train.DEFAULT_RUN_ROOT) as temp:
            missing = Path(temp) / "not-created.json"
            out = Path(temp) / "should-not-exist"
            with mock.patch.object(fit_source, "ADMISSION_PATH", missing):
                with mock.patch.object(train, "verify_pinned_input", side_effect=AssertionError("read gate first")):
                    with mock.patch.object(train, "fit_condition", side_effect=AssertionError("must not fit")):
                        with self.assertRaises(FileNotFoundError):
                            fit_source.run_admitted_execution(out)
            self.assertFalse(out.exists())

    def test_bad_fixed_gate_refuses_before_source_reads_fit_or_output(self):
        with tempfile.TemporaryDirectory(dir=train.DEFAULT_RUN_ROOT) as temp:
            root = Path(temp)
            missing_record = copy.deepcopy(self.record)
            missing_record["pins"]["input_sha256"] = "0" * 64
            bad_path = root / "bad.json"
            bad_path.write_bytes(record_bytes(missing_record))
            out = root / "must-not-exist"
            with mock.patch.object(fit_source, "ADMISSION_PATH", bad_path):
                with mock.patch.object(project_inputs, "SOURCE", mock.Mock(read_bytes=mock.Mock(side_effect=AssertionError("source read before gate")))):
                    with mock.patch.object(train, "verify_pinned_input", side_effect=AssertionError("verify after gate only")):
                        with mock.patch.object(train, "fit_condition", side_effect=AssertionError("must not fit")):
                            with self.assertRaises(PermissionError):
                                fit_source.run_admitted_execution(out)
            self.assertFalse(out.exists())

    def test_input_hash_snapshot_and_row_guard_fail_before_fit_or_output(self):
        rows, projected_bytes, source_bytes, fake_pins, fake_manifest = self.synthetic_pinned_fixture()
        # Gate is independently well-formed and pins the fixture byte-for-byte.
        fake_gate = admission_record(fake_pins)
        self.assertEqual(fit_source.verify_execution_admission_bytes(record_bytes(fake_gate), fake_pins), fake_gate)
        with tempfile.TemporaryDirectory(dir=train.DEFAULT_RUN_ROOT) as temp:
            root = Path(temp)
            mutated_output = root / "bad-projected-hash"
            with mock.patch.object(fit_source, "build_execution_pins", return_value=fake_pins):
                with mock.patch.object(train, "verify_pinned_input", side_effect=AssertionError("bad hash must fail first")):
                    with mock.patch.object(train, "fit_condition", side_effect=AssertionError("must not fit")):
                        with self.assertRaisesRegex(ValueError, "captured source/projected bytes"):
                            train.run_experiment(None, mutated_output, run_kind=fit_source.ADMISSION_SCOPE,
                                seeds=train.SEEDS, max_epochs=train.MAX_EPOCHS,
                                bootstrap_replicates=train.BOOTSTRAP_REPLICATES,
                                execution_admission_snapshot=record_bytes(fake_gate),
                                projected_input_snapshot=projected_bytes + b"altered",
                                source_input_snapshot=source_bytes)
            self.assertFalse(mutated_output.exists())
            mismatched_manifest = dict(fake_manifest, output_sha256="0" * 64)
            manifest_output = root / "bad-verified-manifest"
            with mock.patch.object(fit_source, "build_execution_pins", return_value=fake_pins):
                with mock.patch.object(train, "verify_pinned_input", return_value=(rows, mismatched_manifest)):
                    with mock.patch.object(train, "fit_condition", side_effect=AssertionError("bad manifest must fail before fitting")):
                        with self.assertRaisesRegex(ValueError, "projection admission evidence"):
                            train.run_experiment(None, manifest_output, run_kind=fit_source.ADMISSION_SCOPE,
                                seeds=train.SEEDS, max_epochs=train.MAX_EPOCHS,
                                bootstrap_replicates=train.BOOTSTRAP_REPLICATES,
                                execution_admission_snapshot=record_bytes(fake_gate),
                                projected_input_snapshot=projected_bytes,
                                source_input_snapshot=source_bytes)
            self.assertFalse(manifest_output.exists())
            # Correct source snapshots cannot authorize caller-injected examples or altered labels;
            # the shared path rebuilds tensors/targets from verified projected bytes itself.
            poison_examples = {condition: [] for condition in train.CONDITIONS}
            runner_out = root / "source-bytes-bound-run"
            with mock.patch.object(fit_source, "build_execution_pins", return_value=fake_pins):
                with mock.patch.object(train, "verify_pinned_input", return_value=(rows, fake_manifest)) as verifier:
                    with mock.patch.object(train, "build_examples", wraps=train.build_examples) as rebuild:
                        with mock.patch.object(train, "fit_condition", wraps=train.fit_condition) as fit:
                            report = train.run_experiment(
                                poison_examples, runner_out, run_kind=fit_source.ADMISSION_SCOPE,
                                seeds=train.SEEDS, max_epochs=train.MAX_EPOCHS,
                                bootstrap_replicates=train.BOOTSTRAP_REPLICATES,
                                execution_admission_snapshot=record_bytes(fake_gate),
                                projected_input_snapshot=projected_bytes,
                                source_input_snapshot=source_bytes)
            verifier.assert_called_once_with(projected_payload=projected_bytes, source_payload=source_bytes)
            rebuild.assert_called_once_with(rows)
            self.assertGreater(fit.call_count, 0)
            self.assertEqual(report["dataset"]["train"]["source_rows"], 4)
            self.assertEqual(report["dataset"]["validation"]["source_rows"], 4)
            self.assertEqual(report["dataset"]["excluded_bucket9"]["source_rows"], 1)
            self.assertEqual(report["dataset"]["excluded_bucket9"]["scored_rows"], 0)

    def test_fake_authorized_execution_uses_shared_pipeline_and_snapshots_live_progress(self):
        rows, projected_bytes, source_bytes, fake_pins, fake_manifest = self.synthetic_pinned_fixture()
        fake_gate = admission_record(fake_pins)
        raw_gate = record_bytes(fake_gate)
        with tempfile.TemporaryDirectory(dir=fit_source.RUN_ROOT) as temp:
            root = Path(temp)
            admission_path = root / "fake-parent-record.json"
            admission_path.write_bytes(raw_gate)
            source_path = root / "fake-upstream.jsonl"
            projected_path = root / "fake-projected.jsonl"
            source_path.write_bytes(source_bytes)
            projected_path.write_bytes(projected_bytes)
            output = root / "fake-development-run"
            with mock.patch.object(fit_source, "ADMISSION_PATH", admission_path), \
                 mock.patch.object(fit_source, "build_execution_pins", return_value=fake_pins), \
                 mock.patch.object(fit_source, "PROJECTED_PATH", projected_path, create=True), \
                 mock.patch.object(train, "PROJECTED_PATH", projected_path), \
                 mock.patch.object(project_inputs, "SOURCE", source_path), \
                 mock.patch.object(train, "verify_pinned_input", return_value=(rows, fake_manifest)) as verifier:
                report = fit_source.run_admitted_execution(output)
            verifier.assert_called_once()
            self.assertEqual(report["run_kind"], fit_source.ADMISSION_SCOPE)
            self.assertTrue(report["real_source_loaded"], "runner entered explicit fake-admission path")
            self.assertIs(report["training_authorized"], True)
            self.assertEqual(report["admissions"], {
                "projection_training_authorized": False, "execution_training_authorized": True,
                "actor_forecast": False, "runtime_policy": False, "formal_test": False,
                "psychological_validity": False, "authorization_basis": fake_gate["authorization_basis"]})
            self.assertEqual(report["dataset"]["train"]["source_rows"], 4)
            self.assertEqual(report["dataset"]["validation"]["source_rows"], 4)
            self.assertEqual(report["dataset"]["excluded_bucket9"]["scored_rows"], 0)
            self.assertEqual(report["excluded_bucket9"], {"trained": False, "scored": False, "metrics": None})
            self.assertTrue((output / "DEVELOPMENT_ONLY.txt").is_file())
            self.assertFalse((output / "synthetic_report.json").exists())
            stored = json.loads((output / "provenance.json").read_text(encoding="utf-8"))
            self.assertIs(stored["training_authorized"], True)
            self.assertIs(stored["projection_training_authorized"], False)
            self.assertIs(stored["execution_training_authorized"], True)
            self.assertIs(stored["actor_forecast"], False)
            self.assertIs(stored["psychological_validity"], False)
            snapshots = output / "snapshots"
            self.assertEqual((snapshots / "execution_admission.json").read_bytes(), raw_gate)
            self.assertEqual((snapshots / "projected_input.jsonl").read_bytes(), projected_bytes)
            self.assertEqual((snapshots / "source_input.jsonl").read_bytes(), source_bytes)
            for name, digest in fake_pins["source_sha256"].items():
                self.assertEqual(sha256((snapshots / name).read_bytes()), digest, name)
            for name, digest in (("README.md", fake_pins["protocol_sha256"]),
                                 ("project_inputs.py", fake_pins["builder_sha256"]),
                                 ("test_project_inputs.py", train.EXPECTED_TEST_SHA256)):
                self.assertEqual(sha256((snapshots / name).read_bytes()), digest, name)
            self.assertTrue((snapshots / "INPUT_REVIEW.md").is_file())
            progress = [json.loads(line) for line in (output / "progress.jsonl").read_text(encoding="utf-8").splitlines()]
            self.assertEqual(progress[0]["event"], "run_started")
            self.assertTrue(any(item["event"] == "epoch_complete" for item in progress))
            self.assertTrue(any(item["event"] == "checkpoint_written" for item in progress))
            self.assertEqual(sum(item["event"] == "epoch_complete" for item in progress), 8 * 3 * 15)
            predictions = list(output.glob("predictions_*.jsonl"))
            self.assertEqual(len(predictions), len(train.CONDITIONS) * len(train.SEEDS))
            scored = [json.loads(line) for path in predictions for line in path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(scored), 8 * len(train.CONDITIONS) * len(train.SEEDS))
            self.assertTrue(all(row["split"] in ("train", "validation") for row in scored))
            source_excluded = next(row["provenance"]["trajectory_id"] for row in rows
                                   if row["provenance"]["split"] == "excluded_bucket9")
            self.assertNotIn(source_excluded, {row["trajectory_id"] for row in scored})
            for relative, digest in stored["output_files_sha256"].items():
                self.assertEqual(sha256((output / relative).read_bytes()), digest, relative)

    def test_admitted_output_paths_still_refuse_existing_symlink_and_outside(self):
        _, projected_bytes, source_bytes, fake_pins, _ = self.synthetic_pinned_fixture()
        raw_gate = record_bytes(admission_record(fake_pins))
        with tempfile.TemporaryDirectory(dir=train.DEFAULT_RUN_ROOT) as temp:
            root = Path(temp)
            gate = root / "valid-gate.json"
            gate.write_bytes(raw_gate)
            actual = root / "target"
            actual.mkdir()
            marker = actual / "marker"
            marker.write_text("preserve", encoding="utf-8")
            link = root / "in-root-link"
            link.symlink_to(actual, target_is_directory=True)
            source_path = root / "source.jsonl"
            projected_path = root / "projected.jsonl"
            source_path.write_bytes(source_bytes)
            projected_path.write_bytes(projected_bytes)
            shared = (mock.patch.object(fit_source, "ADMISSION_PATH", gate),
                      mock.patch.object(fit_source, "build_execution_pins", return_value=fake_pins),
                      mock.patch.object(fit_source, "PROJECTED_PATH", projected_path, create=True),
                      mock.patch.object(train, "PROJECTED_PATH", projected_path),
                      mock.patch.object(project_inputs, "SOURCE", source_path))
            with shared[0], shared[1], shared[2], shared[3], shared[4]:
                for path, error in ((actual, FileExistsError), (link / "new-run", ValueError),
                                    (train.ROOT / "outside_execution_outputs", ValueError)):
                    with self.subTest(path=str(path)), mock.patch.object(train, "verify_pinned_input", side_effect=AssertionError("path must fail first")):
                        with self.assertRaises(error):
                            fit_source.run_admitted_execution(path)
            self.assertEqual(marker.read_text(encoding="utf-8"), "preserve")
            self.assertEqual(list(actual.iterdir()), [marker])

    def synthetic_pinned_fixture(self):
        rows = []
        for i in range(4):
            rows.append(synthetic_projected_row(find_episode(2, f"fake-train-{i}"), i, "red" if i % 2 == 0 else "blue"))
            rows.append(synthetic_projected_row(find_episode(8, f"fake-validation-{i}"), i, "red" if i % 2 == 0 else "blue"))
        rows.append(synthetic_projected_row(find_episode(9, "fake-excluded"), 0, "red"))
        projected_bytes = b"".join(record_bytes(row) for row in rows)
        source_bytes = b"synthetic fake source bytes; no LIGHT corpus\n"
        base = fit_source.build_execution_pins()
        pins = copy.deepcopy(base)
        keys = [f"{r['provenance']['trajectory_id']}|{r['provenance']['target_physical_index']}|{r['provenance']['actor'].casefold()}" for r in rows]
        source_keys = [r["provenance"]["target_source_ref"] for r in rows]
        pins.update({"input_sha256": sha256(source_bytes), "projected_sha256": sha256(projected_bytes),
                     "cohort_key_digest": sha256("\n".join(sorted(keys)).encode()),
                     "source_key_digest": sha256("\n".join(sorted(source_keys)).encode()), "row_count": len(rows),
                     "split_counts": {"train": {"rows": 4, "episodes": 4},
                                      "validation": {"rows": 4, "episodes": 4},
                                      "excluded_bucket9": {"rows": 1, "episodes": 1}}})
        manifest = {"training_authorized": False, "input_sha256": pins["input_sha256"],
                    "output_sha256": pins["projected_sha256"], "source_key_digest": pins["source_key_digest"],
                    "cohort_key_digest": pins["cohort_key_digest"]}
        return rows, projected_bytes, source_bytes, pins, manifest


if __name__ == "__main__":
    unittest.main(verbosity=2)
