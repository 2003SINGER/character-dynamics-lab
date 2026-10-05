#!/usr/bin/env python3
"""Adversarial synthetic contract tests for SourceRankingV1; never reads real rows."""
from __future__ import annotations

import copy
import dataclasses
import hashlib
import importlib.util
import math
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

import numpy as np
import torch


HERE = Path(__file__).resolve().parent
TRAIN_PATH = HERE / "train.py"
SPEC = importlib.util.spec_from_file_location("light_source_ranking_train_v1", TRAIN_PATH)
assert SPEC and SPEC.loader
trainer = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = trainer
SPEC.loader.exec_module(trainer)
_ROW_COUNTER: dict[str, int] = {}


def episode_for_bucket(bucket: int, prefix: str) -> str:
    for i in range(100_000):
        candidate = f"{prefix}-{i}"
        got = int(hashlib.sha256(candidate.encode("utf-8")).hexdigest()[:8], 16) % 10
        if got == bucket:
            return candidate
    raise AssertionError(f"could not find episode for bucket {bucket}")


def group(role: str, speech=None, action=None, emote=None):
    return {"role": role, "speech": speech, "action": action, "emote": emote}


def projected_row(trajectory_id: str, *, target="open chest", support=None,
                  history=None, partner_command="secret partner command", physical_index=None):
    if support is None:
        support = ["open chest", "leave room", "wait"]
    if history is None:
        history = [group("self", "I see a door", "look around", "curious"),
                   group("partner", "There is a key", None, "smiles")]
    diagnostic = copy.deepcopy(history)
    partner_turn = next((g for g in diagnostic if g["role"] == "partner"), None)
    if partner_turn is not None:
        partner_turn["action"] = partner_command
    if physical_index is None:
        physical_index = _ROW_COUNTER.get(trajectory_id, 0)
        _ROW_COUNTER[trajectory_id] = physical_index + 1
    bucket = int(hashlib.sha256(trajectory_id.encode()).hexdigest()[:8], 16) % 10
    return {
        "schema": "light_source_ranking_input_contract_v1",
        "static_condition": {"self_persona": "careful explorer", "recorded_environment_snapshot": "small room"},
        "history_views": {"core": copy.deepcopy(history),
                          "diagnostic_plus_partner_raw_commands": diagnostic},
        "candidate_surface": {"recorded_support": list(support)},
        "supervision": {"recorded_action": target},
        "provenance": {"trajectory_id": trajectory_id, "actor": "alice", "split_bucket":
                       bucket, "split": trainer.split_name(bucket), "target_raw_turn_index": 99,
                       "target_physical_index": physical_index, "source_ref": f"synthetic:{trajectory_id}:{physical_index}",
                       "target_source_ref": f"synthetic:{trajectory_id}:{physical_index}",
                       "payload_history_turn_refs": [
                           {"raw_turn_index": 10 + i * 10, "physical_index": i,
                            "role": item["role"], "speaker": "alice" if item["role"] == "self" else "partner",
                            "source_ref": f"episode:{trajectory_id}:turn:{10 + i * 10}"}
                           for i, item in enumerate(history)]},
        "admission": {"training_authorized": False, "actor_forecast_admitted": False},
    }


def independent_signed_hash(text: str | None, dimension: int) -> np.ndarray:
    """Protocol oracle intentionally reimplemented here, independent of trainer."""
    import re
    token_re = re.compile(r"\w+", flags=re.UNICODE)
    tokens = token_re.findall(str(text or "").casefold())
    features = ["u:" + t for t in tokens]
    features.extend("b:" + a + chr(31) + b for a, b in zip(tokens, tokens[1:]))
    out = np.zeros(dimension, dtype=np.float32)
    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=16,
                                 person=b"PredHashV1").digest()
        out[int.from_bytes(digest[:8], "big") % dimension] += 1.0 if digest[8] & 1 else -1.0
    norm = float(np.linalg.norm(out))
    if norm:
        out /= norm
    return out


class SourceRankingTrainerContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # This ignored output root may be absent on a fresh CI checkout.
        (trainer.ROOT / "outputs").mkdir(exist_ok=True)

    def setUp(self):
        self.train_id = episode_for_bucket(2, "synthetic-train")
        self.train_id2 = episode_for_bucket(3, "synthetic-train-second")
        self.val_id = episode_for_bucket(8, "synthetic-val")
        self.val_id2 = episode_for_bucket(7, "synthetic-val-second")
        self.excluded_id = episode_for_bucket(9, "synthetic-excluded")

    def features(self, row, condition="gru_core"):
        return trainer.FeatureEncoder().features(row, condition)

    def examples(self, rows, condition="gru_core"):
        return trainer.build_examples(rows, conditions=(condition,))[condition]

    def test_project_root_and_frozen_digests_are_pinned(self):
        expected_root = HERE.parents[1]
        self.assertEqual(trainer.ROOT.resolve(), expected_root.resolve())
        for name in ("EXPECTED_COHORT_DIGEST", "EXPECTED_PROJECTED_SHA256",
                     "EXPECTED_INPUT_SHA256", "EXPECTED_PROTOCOL_SHA256",
                     "EXPECTED_BUILDER_SHA256", "EXPECTED_TEST_SHA256"):
            digest = getattr(trainer, name)
            self.assertRegex(digest, r"^[0-9a-f]{64}$", name)

    def test_hash_dimensions_unicode_tokens_normalization_and_masks(self):
        text = "Élan_under-score café café"
        expected = independent_signed_hash(text, 256)
        np.testing.assert_array_equal(trainer.signed_hash_vector(text, 256), expected)
        np.testing.assert_array_equal(trainer.signed_hash_vector(None, 64), np.zeros(64, np.float32))
        np.testing.assert_array_equal(trainer.signed_hash_vector("!!!", 64), np.zeros(64, np.float32))
        self.assertAlmostEqual(float(np.linalg.norm(expected)), 1.0, places=6)
        np.testing.assert_array_equal(trainer.signed_hash_vector(text, 256),
                                      trainer.signed_hash_vector(text.upper(), 256))
        row = projected_row(self.train_id)
        encoded = self.features(row)
        self.assertEqual({k: v.shape for k, v in encoded.items()}, {
            "persona": (256,), "context": (256,), "history": (2, 453), "candidates": (3, 256)})
        for value in encoded.values():
            self.assertEqual(value.dtype, np.float32)
        np.testing.assert_array_equal(encoded["persona"], independent_signed_hash("careful explorer", 256))
        np.testing.assert_array_equal(encoded["context"], independent_signed_hash("small room", 256))
        np.testing.assert_array_equal(encoded["candidates"][0], independent_signed_hash("open chest", 256))
        first = encoded["history"][0]
        np.testing.assert_array_equal(first[:256], independent_signed_hash("I see a door", 256))
        np.testing.assert_array_equal(first[256:384], independent_signed_hash("look around", 128))
        np.testing.assert_array_equal(first[384:448], independent_signed_hash("curious", 64))
        np.testing.assert_array_equal(first[448:], np.asarray([1, 0, 1, 1, 1], np.float32))

    def test_metadata_and_gold_mutations_cannot_change_any_feature_or_logits(self):
        row = projected_row(self.train_id)
        altered = copy.deepcopy(row)
        altered["supervision"]["recorded_action"] = "leave room"
        altered["provenance"].update({"trajectory_id": self.val_id, "actor": "mallory",
                                      "target_raw_turn_index": -1, "target_physical_index": 999,
                                      "split_bucket": 7, "split": "validation", "source_ref": "evil"})
        altered["admission"] = {"training_authorized": True, "actor_forecast_admitted": True,
                                "extra_private": "must never be read"}
        a, b = self.features(row), self.features(altered)
        for key in a:
            np.testing.assert_array_equal(a[key], b[key], err_msg=key)
        torch.manual_seed(41)
        model = trainer.RankingModel("gru_core").eval()
        torch.testing.assert_close(model.logits(a), model.logits(b), rtol=0, atol=0)
        # A real allowed-channel positive control prevents a vacuous all-zero encoder.
        allowed_change = copy.deepcopy(row)
        allowed_change["history_views"]["core"][0]["speech"] = "a genuinely different prior utterance"
        self.assertFalse(np.array_equal(self.features(row)["history"],
                                        self.features(allowed_change)["history"]))

    def test_channel_isolation_and_permitted_channel_positive_controls(self):
        row = projected_row(self.train_id)
        base = self.features(row, "gru_core")
        plus = self.features(row, "gru_plus_partner_raw_commands")
        self.assertTrue(np.all(base["history"][1, 256:384] == 0))
        self.assertFalse(np.array_equal(base["history"][1], plus["history"][1]))
        self.assertTrue(np.array_equal(base["history"][0], plus["history"][0]))
        for condition in trainer.CONDITIONS:
            encoded = self.features(row, condition)
            np.testing.assert_array_equal(encoded["candidates"], base["candidates"], err_msg=condition)
            if condition != "gru_no_persona":
                np.testing.assert_array_equal(encoded["persona"], base["persona"], err_msg=condition)
            if condition != "gru_no_context":
                np.testing.assert_array_equal(encoded["context"], base["context"], err_msg=condition)
        cases = [
            ("self_persona", "another persona", "persona"),
            ("recorded_environment_snapshot", "another recorded scene", "context"),
        ]
        for source_key, new_text, tensor_key in cases:
            changed = copy.deepcopy(row)
            changed["static_condition"][source_key] = new_text
            self.assertFalse(np.array_equal(base[tensor_key], self.features(changed)[tensor_key]), source_key)
        for channel, text in (("speech", "new allowed speech"), ("action", "new allowed command"),
                              ("emote", "new allowed emote")):
            changed = copy.deepcopy(row)
            changed["history_views"]["core"][0][channel] = text
            self.assertFalse(np.array_equal(base["history"][0], self.features(changed)["history"][0]), channel)

    def test_named_masks_preserve_turn_slots_and_zero_mask_presence(self):
        row = projected_row(self.train_id)
        core = self.features(row, "gru_core")["history"]
        no_dialogue = self.features(row, "gru_no_dialogue")["history"]
        self.assertEqual(no_dialogue.shape, core.shape)
        np.testing.assert_array_equal(no_dialogue[:, :256], 0)
        np.testing.assert_array_equal(no_dialogue[:, 384:448], 0)
        # Speech and emote masks must be masked with their text to avoid a presence side channel.
        np.testing.assert_array_equal(no_dialogue[:, 450], 0)
        np.testing.assert_array_equal(no_dialogue[:, 452], 0)
        np.testing.assert_array_equal(no_dialogue[:, 256:384], core[:, 256:384])
        np.testing.assert_array_equal(no_dialogue[:, 448:450], core[:, 448:450])
        np.testing.assert_array_equal(no_dialogue[:, 451], core[:, 451])
        # A fully empty but valid prior turn remains represented with its role and slot.
        empty_row = projected_row(self.train_id, history=[group("partner")])
        empty_turn = self.features(empty_row)["history"]
        self.assertEqual(empty_turn.shape, (1, 453))
        np.testing.assert_array_equal(empty_turn[0, :448], 0)
        np.testing.assert_array_equal(empty_turn[0, 448:], np.asarray([0, 1, 0, 0, 0], np.float32))
        context_only = self.features(row, "context_only")
        self.assertEqual(context_only["history"].shape, core.shape,
                         "context-only must retain source group depth for stratified reporting")
        model = trainer.RankingModel("context_only")
        state = model.encode_state(torch.as_tensor(context_only["history"]))
        torch.testing.assert_close(state, torch.zeros(16), rtol=0, atol=0)
        no_context = self.features(row, "gru_no_context")
        np.testing.assert_array_equal(no_context["context"], np.zeros(256, np.float32))
        no_persona = self.features(row, "gru_no_persona")
        np.testing.assert_array_equal(no_persona["persona"], np.zeros(256, np.float32))

    def test_episode_split_bucket9_exclusion_and_no_split_crossing(self):
        rows = [projected_row(self.train_id), projected_row(self.val_id), projected_row(self.excluded_id)]
        examples = self.examples(rows)
        self.assertEqual([e.bucket for e in examples], [2, 8, 9])
        self.assertEqual([e.split for e in examples], ["train", "validation", "excluded_bucket9"])
        self.assertEqual(trainer.episode_bucket(self.train_id),
                         int(hashlib.sha256(self.train_id.encode("utf-8")).hexdigest()[:8], 16) % 10)
        metrics = trainer.ranking_metrics(None, [examples[-1]])
        self.assertEqual(metrics["n"], 0, "bucket 9 is excluded from scoring, not a test set")
        self.assertIsNone(metrics["nll"])
        split_rows = trainer.split_examples(examples)
        self.assertEqual([len(split_rows[k]) for k in ("train", "validation", "excluded_bucket9")], [1, 1, 1])
        crossed = projected_row(self.train_id)
        crossed["provenance"]["split"] = "validation"
        with self.assertRaises(ValueError):
            self.examples([crossed])

    def test_support_matching_preserves_order_spaces_and_flags_duplicates(self):
        valid = projected_row(self.train_id, target="  OPEN CHEST  ",
                              support=["open chest", "open  chest", "leave room"])
        absent_internal_space = projected_row(self.train_id, target="open  chest",
                                              support=["open chest", "leave room"])
        ambiguous = projected_row(self.train_id, target="Bone", support=["Bone", "bone", "wait"])
        absent = projected_row(self.train_id, target="not listed", support=["a", "b"])
        bad_support = projected_row(self.train_id, target="a", support=[])
        built = self.examples([valid, absent_internal_space, ambiguous, absent, bad_support])
        self.assertEqual((built[0].eligibility, built[0].gold_index), ("unique", 0))
        self.assertEqual(built[0].support, ("open chest", "open  chest", "leave room"))
        self.assertEqual((built[1].eligibility, built[1].gold_index), ("absent_target", None))
        self.assertEqual((built[2].eligibility, built[2].gold_index), ("ambiguous_target", None))
        self.assertEqual(built[2].support, ("Bone", "bone", "wait"))
        self.assertEqual((built[3].eligibility, built[3].gold_index), ("absent_target", None))
        self.assertEqual((built[4].eligibility, built[4].gold_index), ("bad_support", None))
        np.testing.assert_array_equal(built[4].features["candidates"], np.zeros((0, 256), np.float32))
        self.assertEqual(built[1].support, ("open chest", "leave room"), "gold must never be injected")

    def test_pool_is_permutation_invariant_gru_is_order_sensitive_and_last2_leftpads(self):
        row = projected_row(self.train_id, history=[group("self", "red key", "take key", "smiles"),
                                                    group("partner", "blue door", None, "frowns")])
        feature = self.features(row, "gru_core")
        h = torch.tensor(feature["history"])
        reversed_h = torch.flip(h, dims=(0,))
        torch.manual_seed(71)
        pooled = trainer.RankingModel("pooled_core").eval()
        pool_a, pool_b = pooled.encode_state(h), pooled.encode_state(reversed_h)
        torch.testing.assert_close(pool_a, pool_b, rtol=0, atol=1e-6)
        torch.manual_seed(73)
        gru = trainer.RankingModel("gru_core").eval()
        ordered_a, ordered_b = gru.encode_state(h), gru.encode_state(reversed_h)
        self.assertGreater(float(torch.max(torch.abs(ordered_a - ordered_b)).detach()), 1e-7)
        one = torch.tensor(self.features(projected_row(self.train_id,
            history=[group("self", "only turn", "wait", None)]))["history"])
        torch.manual_seed(79)
        last2_model = trainer.RankingModel("last2_core").eval()
        actual = last2_model.encode_state(one)
        expected = last2_model.last2(torch.cat((torch.zeros((1, 453)), one), 0).reshape(906))
        torch.testing.assert_close(actual, expected, rtol=0, atol=0)
        self.assertEqual(trainer.DIMENSIONS["history_turn"], 453)

    def test_ranking_metrics_use_nll_top1_mrr_and_candidate_order_for_ties(self):
        first = self.examples([projected_row(self.train_id, target="b", support=["a", "b", "c"])])[0]
        # uniform assigns equal mass; stable source-list order puts label index 1 at rank two.
        metrics = trainer.ranking_metrics(None, [first])
        self.assertEqual(metrics["n"], 1)
        self.assertEqual(metrics["row_ranks"], [2])
        self.assertEqual(metrics["top1_accuracy"], 0.0)
        self.assertEqual(metrics["mrr"], 0.5)
        self.assertAlmostEqual(metrics["nll"], math.log(3), places=6)
        # A strictly larger earlier score beats the gold, while equal later scores do not.
        class FixedModel:
            def eval(self): return self
            def logits(self, _features): return torch.tensor([2.0, 1.0, 1.0])
        later = self.examples([projected_row(self.train_id, target="c", support=["a", "b", "c"])])[0]
        tied = trainer.ranking_metrics(FixedModel(), [later])
        self.assertEqual(tied["row_ranks"], [3])
        # Reordering otherwise-identical support scores must change rank only through source order.
        permuted = self.examples([projected_row(self.train_id2, target="c",
                                                support=["c", "a", "b"])])[0]
        moved = trainer.ranking_metrics(FixedModel(), [permuted])
        self.assertEqual(moved["row_ranks"], [1])

    def test_best_checkpoint_restores_earliest_actual_deep_copied_state(self):
        self.assertEqual(trainer.select_best_checkpoint([2.0, 1.0, 1.0, 4.0]), 2)
        with self.assertRaises(ValueError):
            trainer.select_best_checkpoint([1.0, float("nan")])
        train = self.examples([projected_row(self.train_id, target="open chest")])
        val = self.examples([projected_row(self.val_id, target="leave room")])
        model = trainer.RankingModel("gru_core")
        seen = []
        original_nll = trainer._nll
        def scripted_nll(model_arg, examples):
            # Both epochs tie; select the earliest and restore its cloned state.
            seen.append({k: v.detach().clone() for k, v in model_arg.state_dict().items()})
            return 0.25
        trainer._nll = scripted_nll
        try:
            fitted = trainer.train_one(model, train, val, seed=83, max_epochs=2)
        finally:
            trainer._nll = original_nll
        self.assertEqual(fitted["best_epoch"], 1)
        for key, expected in seen[0].items():
            torch.testing.assert_close(fitted["model"].state_dict()[key], expected, rtol=0, atol=0)
        self.assertTrue(any(not torch.equal(seen[0][key], seen[1][key]) for key in seen[0]),
                        "optimizer epochs should produce distinct checkpoint candidates")
        # Mutating the returned/current model cannot mutate the saved snapshot held by test.
        saved = {k: v.clone() for k, v in fitted["model"].state_dict().items()}
        with torch.no_grad():
            next(fitted["model"].parameters()).add_(5)
        for key, expected in saved.items():
            if not torch.equal(fitted["model"].state_dict()[key], expected):
                break
        else:
            self.fail("model mutation did not exercise checkpoint independence")

    def test_train_one_enforces_splits_and_validation_is_inference_only(self):
        train = self.examples([projected_row(self.train_id, support=["open chest", "train option"]),
                               projected_row(self.train_id2, support=["open chest", "train option"])])
        val = self.examples([projected_row(self.val_id, support=["open chest", "validation option"]),
                             projected_row(self.val_id2, support=["open chest", "validation option"])])
        # Ensure the helper's generated IDs actually hash into the intended partitions.
        train = [e for e in train if e.split == "train"]
        val = [e for e in val if e.split == "validation"]
        model = trainer.RankingModel("gru_core")
        train_candidates = {e.features["candidates"].tobytes() for e in train}
        val_candidates = {e.features["candidates"].tobytes() for e in val}
        grad_inputs, no_grad_inputs = [], []
        original_logits = model.logits
        def tracked_logits(features):
            key = features["candidates"].tobytes()
            (grad_inputs if torch.is_grad_enabled() else no_grad_inputs).append(key)
            return original_logits(features)
        model.logits = tracked_logits
        trainer.train_one(model, train, val, seed=89, max_epochs=1)
        self.assertTrue(grad_inputs)
        self.assertTrue(all(x in train_candidates for x in grad_inputs))
        self.assertTrue(no_grad_inputs)
        self.assertTrue(all(x in val_candidates for x in no_grad_inputs))
        with self.assertRaises(ValueError):
            trainer.train_one(trainer.RankingModel("gru_core"), val, train, seed=89, max_epochs=1)
        excluded = self.examples([projected_row(self.excluded_id)])
        with self.assertRaises(ValueError):
            trainer.train_one(trainer.RankingModel("gru_core"), excluded, val, seed=89, max_epochs=1)

    def test_seeded_fit_repeats_identically_and_uniform_has_no_trainable_parameters(self):
        train = self.examples([projected_row(self.train_id, target="open chest"),
                               projected_row(self.train_id2, target="leave room")])
        val = self.examples([projected_row(self.val_id, target="leave room")])
        train = [e for e in train if e.split == "train"]
        val = [e for e in val if e.split == "validation"]
        a = trainer.fit_condition(train + val, "gru_core", seed=97)
        b = trainer.fit_condition(train + val, "gru_core", seed=97)
        self.assertEqual(a["best_epoch"], b["best_epoch"])
        self.assertEqual(a["validation_nll_by_epoch"], b["validation_nll_by_epoch"])
        for key, value in a["model"].state_dict().items():
            torch.testing.assert_close(value, b["model"].state_dict()[key], rtol=0, atol=0)
        uniform = trainer.RankingModel("uniform")
        self.assertEqual(trainer.trainable_parameter_count(uniform), 0)
        metrics = trainer.ranking_metrics(None, val)
        self.assertTrue(all(math.isclose(x, math.log(len(e.support)), abs_tol=1e-6)
                            for x, e in zip(metrics["row_losses"], val)))

    def test_episode_bootstrap_matches_independent_row_weighted_cluster_oracle(self):
        # Unequal cluster sizes separate row-weighted from equal-episode weighting.
        rows = []
        third_id = episode_for_bucket(8, "bootstrap-third")
        for tid, ds in ((self.val_id, [0.0]), (self.val_id2, [2.0]),
                        (third_id, [10.0, 10.0, 10.0, 10.0])):
            for i, delta in enumerate(ds):
                row = projected_row(tid, target="open chest")
                ex = self.examples([row])[0]
                ex = trainer.Example(ex.features, ex.trajectory_id, ex.actor, ex.bucket, ex.support,
                                     ex.gold_index, ex.eligibility, source_row=len(rows) + 1)
                rows.append((ex, delta))
        left = [x[0] for x in rows]
        right = copy.deepcopy(left)
        left_losses = [delta for _, delta in rows]
        right_losses = [0.0] * len(rows)
        replicates, seed = 31, 104729
        result = trainer.paired_episode_bootstrap(left, right, left_losses, right_losses,
                                                 replicates=replicates, seed=seed)
        self.assertAlmostEqual(result["mean_delta_nll"], 7.0, places=12)
        ids = sorted({e.trajectory_id for e in left})
        episode_values = {tid: [d for e, d in rows if e.trajectory_id == tid] for tid in ids}
        rng = np.random.default_rng(seed)
        draws = []
        for _ in range(replicates):
            sampled = rng.integers(0, len(ids), size=len(ids))
            values = [d for ix in sampled for d in episode_values[ids[ix]]]
            draws.append(float(np.mean(values)))
        expected = np.quantile(np.asarray(draws), [0.025, 0.975])
        np.testing.assert_allclose(result["ci95"], expected, rtol=0, atol=1e-12)

    def test_pinned_manifest_verification_and_real_fitting_are_closed(self):
        self.assertFalse(callable(getattr(trainer, "set_training_authorized", None)))
        with mock.patch.object(trainer, "verify_pinned_input",
                               return_value=([], {"training_authorized": False})):
            with mock.patch.object(trainer, "fit_condition", side_effect=AssertionError("must not fit")):
                with self.assertRaisesRegex(PermissionError, "training_authorized=false"):
                    trainer.run_real_data_fail_closed()

    def test_fake_pinned_contract_checks_hashes_without_real_cohort(self):
        import json
        row = projected_row(self.train_id, physical_index=0)
        row["provenance"]["target_source_ref"] = "fake-source-ref"
        payload = (json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n").encode()
        projected_sha = hashlib.sha256(payload).hexdigest()
        cohort_digest = hashlib.sha256(
            f"{self.train_id}|0|alice".encode()).hexdigest()
        source_digest = hashlib.sha256(b"fake-source-ref").hexdigest()
        with tempfile.TemporaryDirectory(dir=trainer.ROOT / "outputs") as temp:
            contract = Path(temp)
            projected_path = contract / "projected_inputs.jsonl"
            manifest_path = contract / "manifest.json"
            fake_source = contract / "synthetic_source.jsonl"
            source_bytes = b"synthetic upstream bytes only\n"
            fake_source.write_bytes(source_bytes)
            source_sha = hashlib.sha256(source_bytes).hexdigest()
            projected_path.write_bytes(payload)
            snapshots = {
                "protocol_snapshot.md": (HERE / "README.md").read_bytes(),
                "project_inputs_snapshot.py": (HERE / "project_inputs.py").read_bytes(),
                "test_project_inputs_snapshot.py": (HERE / "test_project_inputs.py").read_bytes(),
            }
            for name, content in snapshots.items():
                (contract / name).write_bytes(content)
            snapshot_hashes = {name: hashlib.sha256(content).hexdigest()
                               for name, content in snapshots.items()}
            fake_manifest = {"input_sha256": source_sha, "output_sha256": projected_sha,
                             "protocol_sha256": snapshot_hashes["protocol_snapshot.md"],
                             "code_sha256": snapshot_hashes["project_inputs_snapshot.py"],
                             "test_sha256": snapshot_hashes["test_project_inputs_snapshot.py"],
                             "rows": 1, "cohort_key_digest": cohort_digest,
                             "source_key_digest": source_digest,
                             "training_authorized": False}
            manifest_path.write_text(json.dumps(fake_manifest), encoding="utf-8")
            patches = {
                "CONTRACT_DIR": contract,
                "PROJECTED_PATH": projected_path,
                "EXPECTED_INPUT_SHA256": source_sha,
                "EXPECTED_PROJECTED_SHA256": projected_sha,
                "EXPECTED_PROTOCOL_SHA256": snapshot_hashes["protocol_snapshot.md"],
                "EXPECTED_BUILDER_SHA256": snapshot_hashes["project_inputs_snapshot.py"],
                "EXPECTED_TEST_SHA256": snapshot_hashes["test_project_inputs_snapshot.py"],
                "EXPECTED_ROWS": 1,
                "EXPECTED_COHORT_DIGEST": cohort_digest,
                "EXPECTED_SOURCE_KEY_DIGEST": source_digest,
                "EXPECTED_SPLITS": {"train": (1, 1), "validation": (0, 0), "excluded_bucket9": (0, 0)},
            }
            import project_inputs
            with mock.patch.multiple(trainer, **patches), mock.patch.object(project_inputs, "SOURCE", fake_source):
                valid_rows, manifest = trainer.verify_pinned_input()
                self.assertEqual(len(valid_rows), 1)
                self.assertIs(manifest["training_authorized"], False)
                # Manifest pins are checked before reading rows; malformed input is a hard failure.
                fake_manifest["input_sha256"] = "b" * 64
                manifest_path.write_text(json.dumps(fake_manifest), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "input_sha256 mismatch"):
                    trainer.verify_pinned_input()
                fake_manifest["input_sha256"] = source_sha
                manifest_path.write_text(json.dumps(fake_manifest), encoding="utf-8")
                projected_path.write_bytes(payload + b" ")
                with self.assertRaisesRegex(ValueError, "projected input artifact hash mismatch"):
                    trainer.verify_pinned_input()
                projected_path.write_bytes(payload)
                (contract / "protocol_snapshot.md").write_bytes(b"tampered")
                with self.assertRaisesRegex(ValueError, "snapshot hash mismatch"):
                    trainer.verify_pinned_input()

    def test_synthetic_cli_writes_all_conditions_and_refuses_existing_output(self):
        with tempfile.TemporaryDirectory(dir=trainer.ROOT / "outputs") as temp:
            out = Path(temp) / "synthetic-run"
            cmd = [sys.executable, str(TRAIN_PATH), "--synthetic", "--out", str(out)]
            result = subprocess.run(cmd, text=True, capture_output=True, timeout=180)
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            report_path = out / "report.json"
            self.assertTrue(report_path.is_file())
            report = __import__("json").loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(report.get("run_kind"), "SYNTHETIC_CONTRACT_ONLY")
            self.assertFalse(report.get("research_evidence"))
            self.assertEqual(set(report["conditions"]), set(trainer.CONDITIONS))
            for condition in trainer.CONDITIONS:
                for seed in trainer.SEEDS:
                    runs = report["conditions"][condition]
                    item = next(x for x in runs if x["seed"] == seed)
                    if condition == "uniform":
                        self.assertIsNone(item["checkpoint_file"])
                    else:
                        self.assertTrue((out / item["checkpoint_file"]).is_file())
                    self.assertTrue((out / item["prediction_file"]).is_file())
            # Independently rebuild the seed-average paired bootstrap from saved validation losses.
            def averaged_validation_losses(condition):
                by_row, by_episode = {}, {}
                for run in report["conditions"][condition]:
                    path = out / run["prediction_file"]
                    for line in path.read_text(encoding="utf-8").splitlines():
                        prediction = __import__("json").loads(line)
                        if prediction["split"] == "validation":
                            by_row.setdefault(prediction["source_row"], []).append(prediction["nll"])
                            by_episode[prediction["source_row"]] = prediction["trajectory_id"]
                return {row: float(np.mean(values)) for row, values in by_row.items()}, by_episode
            left, left_episode = averaged_validation_losses("gru_core")
            right, _ = averaged_validation_losses("context_only")
            self.assertEqual(set(left), set(right))
            pairs = [(left_episode[row], left[row] - right[row]) for row in sorted(left)]
            comparison = report["paired_comparisons"]["gru_core_vs_context_only"]
            self.assertAlmostEqual(comparison["mean_delta_nll"],
                                   float(np.mean([delta for _, delta in pairs])), places=12)
            grouped = {}
            for episode, delta in pairs:
                grouped.setdefault(episode, []).append(delta)
            episode_ids = sorted(grouped)
            rng = np.random.default_rng(trainer.BOOTSTRAP_SEED)
            draws = []
            for _ in range(trainer.BOOTSTRAP_REPLICATES):
                selected = rng.integers(0, len(episode_ids), size=len(episode_ids))
                sample = [delta for index in selected for delta in grouped[episode_ids[index]]]
                draws.append(float(np.mean(sample)))
            expected_ci = np.quantile(np.asarray(draws), [0.025, 0.975])
            np.testing.assert_allclose(comparison["ci95"], expected_ci, rtol=0, atol=1e-12)
            marker = report_path.read_bytes()
            again = subprocess.run(cmd, text=True, capture_output=True, timeout=30)
            self.assertNotEqual(again.returncode, 0)
            self.assertEqual(report_path.read_bytes(), marker)

    def test_every_learned_condition_updates_parameters_and_lowers_train_nll(self):
        rows = []
        for i in range(8):
            positive = i % 2 == 0
            tid = episode_for_bucket(2, f"learning-train-{i}")
            gold = "choose red" if positive else "choose blue"
            rows.append(projected_row(
                tid, target=gold, support=["choose red", "choose blue"],
                history=[group("self", "red signal" if positive else "blue signal",
                               "inspect red" if positive else "inspect blue", None)]))
        val_rows = []
        for i in range(2):
            positive = i == 0
            tid = episode_for_bucket(8, f"learning-val-{i}")
            gold = "choose red" if positive else "choose blue"
            val_rows.append(projected_row(
                tid, target=gold, support=["choose red", "choose blue"],
                history=[group("self", "red signal" if positive else "blue signal",
                               "inspect red" if positive else "inspect blue", None)]))
        for condition in (c for c in trainer.CONDITIONS if c != "uniform"):
            train_examples = trainer.build_examples(rows, conditions=(condition,))[condition]
            val_examples = trainer.build_examples(val_rows, conditions=(condition,))[condition]
            torch.manual_seed(103)
            initial_model = trainer.RankingModel(condition)
            initial_loss = trainer._nll(initial_model, train_examples)
            fitted = trainer.fit_condition(train_examples + val_examples, condition, seed=103)
            final_loss = trainer._nll(fitted["model"], train_examples)
            self.assertLess(final_loss, initial_loss - 1e-6, condition)
            self.assertGreater(fitted["trainable_parameters"], 0, condition)
            grads = {name: p.grad for name, p in fitted["model"].named_parameters()}
            self.assertTrue(any(g is not None and torch.count_nonzero(g).item() for g in grads.values()), condition)
            if condition == "gru_core":
                self.assertTrue(any("gru" in name and g is not None and torch.count_nonzero(g).item()
                                    for name, g in grads.items()))
                self.assertTrue(any("head" in name and g is not None and torch.count_nonzero(g).item()
                                    for name, g in grads.items()))
            if condition == "pooled_core":
                for component in ("pool_phi", "pool_rho", "head"):
                    self.assertTrue(any(component in name and g is not None and torch.count_nonzero(g).item()
                                        for name, g in grads.items()), component)
            if condition == "last2_core":
                self.assertTrue(any("last2" in name and g is not None and torch.count_nonzero(g).item()
                                    for name, g in grads.items()))

    def test_new_output_rejects_symlink_ancestor_and_does_not_touch_target(self):
        with tempfile.TemporaryDirectory(dir=trainer.ROOT / "outputs") as temp:
            root = Path(temp)
            actual = root / "actual"
            actual.mkdir()
            marker = actual / "marker.txt"
            marker.write_text("preserve exactly", encoding="utf-8")
            digest = hashlib.sha256(marker.read_bytes()).hexdigest()
            link = root / "in-root-link"
            link.symlink_to(actual, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink"):
                trainer.run_experiment({}, link / "new-run", run_kind="SYNTHETIC_CONTRACT_ONLY",
                                       input_snapshot=b"[]\n")
            self.assertEqual(hashlib.sha256(marker.read_bytes()).hexdigest(), digest)
            broken = root / "broken-link"
            broken.symlink_to(root / "no-such-target", target_is_directory=True)
            with self.assertRaises((ValueError, FileExistsError)):
                trainer.run_experiment({}, broken, run_kind="SYNTHETIC_CONTRACT_ONLY",
                                       input_snapshot=b"[]\n")
            self.assertEqual(hashlib.sha256(marker.read_bytes()).hexdigest(), digest)
            with self.assertRaises(FileExistsError):
                trainer.run_experiment({}, actual, run_kind="SYNTHETIC_CONTRACT_ONLY",
                                       input_snapshot=b"[]\n")
            self.assertEqual(hashlib.sha256(marker.read_bytes()).hexdigest(), digest)
            outside = trainer.ROOT / "outputs" / ".." / "test_train_outside_outputs"
            with self.assertRaisesRegex(ValueError, "under ROOT/outputs"):
                trainer.run_experiment({}, outside, run_kind="SYNTHETIC_CONTRACT_ONLY",
                                       input_snapshot=b"[]\n")

    def test_run_preflight_rejects_condition_cohort_or_order_mismatch_before_output(self):
        rows = [projected_row(self.train_id, physical_index=501),
                projected_row(self.val_id, physical_index=502)]
        baseline = trainer.build_examples(rows)
        cases = {}
        missing = {k: list(v) for k, v in baseline.items()}
        missing["gru_core"].pop()
        cases["missing_row"] = missing
        reordered = {k: list(v) for k, v in baseline.items()}
        reordered["pooled_core"] = list(reversed(reordered["pooled_core"]))
        cases["reordered_rows"] = reordered
        changed = {k: list(v) for k, v in baseline.items()}
        changed["last2_core"][0] = dataclasses.replace(changed["last2_core"][0],
                                                       eligibility="ambiguous_target", gold_index=None)
        cases["eligibility_changed"] = changed
        with tempfile.TemporaryDirectory(dir=trainer.ROOT / "outputs") as temp:
            for name, by_condition in cases.items():
                out = Path(temp) / name
                with mock.patch.object(trainer, "fit_condition",
                                       side_effect=AssertionError("preflight must precede fitting")):
                    with self.assertRaisesRegex(ValueError, "cohort|align|condition|row|eligibility"):
                        trainer.run_experiment(by_condition, out,
                                               run_kind="SYNTHETIC_CONTRACT_ONLY",
                                               input_snapshot=b"synthetic rows only\n")
                self.assertFalse(out.exists(), f"preflight wrote output for {name}")

    def test_dataset_channel_counts_separate_views_roles_prefix_occurrences_and_unique_refs(self):
        history = [group("self", "same self speech", "same self command", "same self emote"),
                   group("partner", "same partner speech", None, "same partner emote")]
        first = projected_row(self.train_id, history=history, physical_index=21)
        second = projected_row(self.train_id, history=history, physical_index=22)
        examples = self.examples([first, second])
        report = trainer.dataset_report(examples)
        channels = report["train"]["history_channel_occurrences_and_unique_refs"]
        self_record = channels["core"]["self"]
        partner_core = channels["core"]["partner"]
        partner_diag = channels["diagnostic_plus_partner_raw_commands"]["partner"]
        self.assertEqual(self_record["speech"]["present_event_occurrences_in_prefixes"], 2)
        self.assertEqual(self_record["speech"]["unique_event_ids"], 1)
        self.assertEqual(self_record["action"]["unique_event_ids"], 1)
        self.assertEqual(partner_core["action"]["present_event_occurrences_in_prefixes"], 0)
        self.assertEqual(partner_core["action"]["null_event_occurrences_in_prefixes"], 2)
        self.assertEqual(partner_core["action"]["unique_event_ids"], 0)
        self.assertEqual(partner_diag["action"]["present_event_occurrences_in_prefixes"], 2)
        self.assertEqual(partner_diag["action"]["unique_event_ids"], 1)
        self.assertEqual(report["excluded_bucket9"]["scored_rows"], 0)
        no_refs = projected_row(self.train_id2, history=[group("self", "speech", None, None)])
        no_refs["provenance"].pop("payload_history_turn_refs")
        no_refs["provenance"].pop("target_raw_turn_index")
        # Missing reference identity is unknown, not evidence of zero unique events.
        unknown = self.examples([no_refs])
        detail = trainer.dataset_report(unknown)["train"][
            "history_channel_occurrences_and_unique_refs"]["core"]["self"]["speech"]
        self.assertIsNone(detail["unique_event_ids"])
        self.assertTrue(detail["unique_event_ids_unavailable_reason"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
