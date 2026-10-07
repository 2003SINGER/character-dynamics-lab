"""Synthetic functional contract tests; no real LIGHT training is performed."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import torch


MODULE_PATH = Path(__file__).with_name("train.py")
SPEC = importlib.util.spec_from_file_location("prediction_baseline_v1", MODULE_PATH)
pb = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = pb
SPEC.loader.exec_module(pb)


def episode_id_for_bucket(bucket: int, prefix: str) -> str:
    for i in range(100_000):
        candidate = f"{prefix}-{i}"
        value = int(hashlib.sha256(candidate.encode()).hexdigest()[:8], 16) % 10
        if value == bucket:
            return candidate
    raise AssertionError("failed to find synthetic trajectory id")


def actor_rows(tid: str, actor: str, initial_o: str, initial_a: str,
               current_o: str = "current room", first_gold: str = "open chest",
               future_o: str = "later room", future_gold: str = "leave room"):
    first = {
        "trajectory_id": tid, "actor": actor, "target_step_index": 2,
        "previous_same_actor_t": 0, "previous2_same_actor_t": None,
        "actor_history_depth": 1, "previous_source_O": initial_o,
        "previous_source_action_A_star": initial_a, "source_O": current_o,
        "source_action_A_star": first_gold,
        "candidate_set_factual": ["open chest", "leave room"],
        "exact_previous_pair": False,
    }
    second = {
        "trajectory_id": tid, "actor": actor, "target_step_index": 5,
        "previous_same_actor_t": 2, "previous2_same_actor_t": 0,
        "actor_history_depth": 2, "previous_source_O": current_o,
        "previous_source_action_A_star": first_gold, "source_O": future_o,
        "source_action_A_star": future_gold,
        "candidate_set_factual": ["open chest", "leave room"],
        "exact_previous_pair": False,
    }
    return [first, second]


class PredictionBaselineV1ContractTests(unittest.TestCase):
    def setUp(self):
        self.train_tid = episode_id_for_bucket(2, "train")
        self.val_tid = episode_id_for_bucket(8, "validation")
        self.rows = (
            actor_rows(self.train_tid, "alice", "start room", "look around")
            + actor_rows(self.train_tid, "bob", "cell", "wait")
            + actor_rows(self.val_tid, "alice", "shore", "walk north")
        )

    def test_episode_wide_split_and_frozen_sha256_bucket(self):
        expected = int(hashlib.sha256(self.train_tid.encode()).hexdigest()[:8], 16) % 10
        self.assertEqual(pb.bucket_for_episode(self.train_tid), expected)
        self.assertEqual({pb.bucket_for_episode(r["trajectory_id"]) for r in self.rows
                          if r["trajectory_id"] == self.train_tid}, {expected})
        examples = pb.reconstruct_examples(self.rows)
        self.assertEqual({ex.bucket for ex in examples if ex.trajectory_id == self.train_tid},
                         {expected})
        self.assertEqual(pb.split_name(expected), "train")
        manifest = pb.split_id_manifest(examples)
        self.assertIn(self.train_tid, manifest[str(expected)]["trajectory_ids"])

    def test_rejects_non_string_group_ids_and_nonprior_history(self):
        malformed = actor_rows(self.train_tid, "alice", "start room", "look around")
        malformed[0]["actor"] = {"not": "a string"}
        with self.assertRaises(ValueError):
            pb.reconstruct_examples(malformed)
        malformed = actor_rows(self.train_tid, "alice", "start room", "look around")
        malformed[0]["previous_same_actor_t"] = malformed[0]["target_step_index"]
        with self.assertRaises(ValueError):
            pb.reconstruct_examples(malformed)

    def test_current_gold_does_not_change_inputs_or_logits(self):
        original_rows = actor_rows(self.train_tid, "alice", "start room", "look around")
        changed_rows = copy.deepcopy(original_rows)
        changed_rows[0]["source_action_A_star"] = "leave room"
        # Keep the later target's observed previous-action field consistent with
        # the changed earlier gold. Only the first target's prediction is tested.
        changed_rows[1]["previous_source_action_A_star"] = "leave room"
        first = pb.reconstruct_examples(original_rows)[0]
        altered = pb.reconstruct_examples(changed_rows)[0]
        for left, right in zip(pb.prediction_inputs(first), pb.prediction_inputs(altered)):
            np.testing.assert_array_equal(left, right)
        torch.manual_seed(9)
        model = pb.CandidateScorer("gru").eval()
        left, _ = model.logits_batch([first], torch.device("cpu"))
        right, _ = model.logits_batch([altered], torch.device("cpu"))
        torch.testing.assert_close(left, right, rtol=0, atol=0)

    def test_future_rows_do_not_change_earlier_history_or_prediction(self):
        all_rows = actor_rows(self.train_tid, "alice", "start room", "look around")
        earlier_only = pb.reconstruct_examples(all_rows[:1])[0]
        with_future = pb.reconstruct_examples(all_rows)[0]
        np.testing.assert_array_equal(earlier_only.history_vectors, with_future.history_vectors)
        torch.manual_seed(11)
        model = pb.CandidateScorer("gru").eval()
        a, _ = model.logits_batch([earlier_only], torch.device("cpu"))
        b, _ = model.logits_batch([with_future], torch.device("cpu"))
        torch.testing.assert_close(a, b, rtol=0, atol=0)

    def test_history_resets_across_actor_and_episode(self):
        examples = pb.reconstruct_examples(self.rows)
        alice = next(ex for ex in examples if ex.trajectory_id == self.train_tid
                     and ex.actor == "alice" and ex.depth == 1)
        bob = next(ex for ex in examples if ex.trajectory_id == self.train_tid
                   and ex.actor == "bob" and ex.depth == 1)
        val = next(ex for ex in examples if ex.trajectory_id == self.val_tid
                   and ex.actor == "alice" and ex.depth == 1)
        self.assertEqual(alice.prior_pairs[0]["O"], "start room")
        self.assertEqual(bob.prior_pairs[0]["O"], "cell")
        self.assertEqual(val.prior_pairs[0]["O"], "shore")
        self.assertEqual(alice.depth, 1)
        self.assertEqual(bob.depth, 1)

    def test_candidate_probabilities_sum_to_one(self):
        examples = pb.reconstruct_examples(actor_rows(
            self.train_tid, "alice", "start room", "look around"))
        model = pb.CandidateScorer("o_only")
        probabilities = pb.candidate_probabilities(model, examples[:1])[0]
        self.assertEqual(len(probabilities), 2)
        self.assertAlmostEqual(float(probabilities.sum()), 1.0, places=7)

    def test_gold_outside_recorded_support_is_counted_not_added(self):
        rows = actor_rows(self.train_tid, "alice", "start room", "look around")
        rows[0]["source_action_A_star"] = "unlisted action"
        rows[0]["candidate_set_factual"] = ["open chest", "leave room"]
        example = pb.reconstruct_examples(rows[:1])[0]
        self.assertTrue(example.support_miss)
        self.assertEqual(example.candidates, ["open chest", "leave room"])
        self.assertNotIn("unlisted action", example.candidates)
        self.assertTrue(example.support_miss)
        self.assertFalse(example.normalized_gold_ambiguity)

    def test_normalized_duplicate_is_ambiguity_not_absence_or_support_repair(self):
        row = actor_rows(self.train_tid, "alice", "start room", "look around")[0]
        row["source_action_A_star"] = "Bone"
        row["candidate_set_factual"] = ["Bone", "bone", "leave room"]
        example = pb.reconstruct_examples([row])[0]
        self.assertIsNone(example.gold_index)
        self.assertFalse(example.support_miss)
        self.assertTrue(example.normalized_gold_ambiguity)
        self.assertEqual(example.candidates, ["Bone", "bone", "leave room"])

    def test_ordered_last2_shared_input_and_left_padding(self):
        examples = pb.reconstruct_examples(actor_rows(
            self.train_tid, "alice", "start room", "look around"))
        depth_two = examples[1]
        vector = pb.ordered_last2_vector(depth_two)
        swapped = copy.deepcopy(depth_two)
        swapped.history_vectors = depth_two.history_vectors[::-1].copy()
        swapped.prior_pairs = list(reversed(depth_two.prior_pairs))
        swapped_vector = pb.ordered_last2_vector(swapped)
        self.assertFalse(np.array_equal(vector, swapped_vector))

        for condition in ("last2", "learned_last2"):
            torch.manual_seed(23)
            model = pb.CandidateScorer(condition).eval()
            state_a = model.state_batch([depth_two], torch.device("cpu"))
            state_b = model.state_batch([swapped], torch.device("cpu"))
            self.assertFalse(torch.equal(state_a, state_b))

        depth_one = examples[0]
        left_padded = pb.ordered_last2_vector(depth_one)
        np.testing.assert_array_equal(left_padded[:pb.PAIR_DIM],
                                      np.zeros(pb.PAIR_DIM, dtype=np.float32))
        np.testing.assert_array_equal(left_padded[pb.PAIR_DIM:],
                                      depth_one.history_vectors[0])

    def test_episode_bootstrap_preserves_row_weighted_estimand_and_empty_strata(self):
        rows = []
        for episode, deltas in (("ep-one", [1.0]), ("ep-many", [3.0, 3.0, 3.0])):
            for i, delta in enumerate(deltas):
                rows.append({
                    "trajectory_id": episode, "actor": "a", "target_step_index": i,
                    "losses_nats": {"lhs": delta + 1.0, "rhs": 1.0}})
        keys = {(r["trajectory_id"], r["actor"], r["target_step_index"]) for r in rows}
        result = pb.paired_cluster_bootstrap(rows, "lhs", "rhs", keys, seed_offset=17)
        self.assertAlmostEqual(result["delta_nll_nats_lhs_minus_rhs"], 2.5)
        self.assertEqual(result["rows"], 4)
        self.assertEqual(result["episodes"], 2)
        self.assertEqual(result["estimand"], "row-weighted mean; episode-cluster resampling")
        empty = pb.paired_cluster_bootstrap(rows, "lhs", "rhs", set(), seed_offset=19)
        self.assertIsNone(empty["delta_nll_nats_lhs_minus_rhs"])
        self.assertIsNone(empty["ci95"])
        self.assertEqual(empty["reason"], "no common scored rows")

    def test_train_filter_and_validation_evaluation_have_no_gradients(self):
        examples = pb.reconstruct_examples(self.rows)
        train = pb.eligible(examples, "train")
        validation = pb.eligible(examples, "validation")
        self.assertTrue(train and validation)
        self.assertTrue(all(pb.split_name(ex.bucket) == "train" for ex in train))
        self.assertTrue(all(pb.split_name(ex.bucket) == "validation" for ex in validation))
        model = pb.CandidateScorer("learned_mean")
        optimizer = torch.optim.Adam(model.parameters(), lr=pb.LEARNING_RATE)
        optimizer.zero_grad(set_to_none=True)
        logits, counts = model.logits_batch(train[:1], torch.device("cpu"))
        pb.row_losses(logits, counts, [int(train[0].gold_index)])[0].backward()
        self.assertTrue(all(parameter.grad is not None for parameter in model.parameters()))
        for parameter in model.parameters():
            parameter.grad = None
        pb.mean_nll(model, validation, torch.device("cpu"))
        self.assertTrue(all(parameter.grad is None for parameter in model.parameters()))

    def test_strict_checkpoint_reload_reproduces_logits(self):
        examples = pb.reconstruct_examples(actor_rows(
            self.train_tid, "alice", "start room", "look around"))[:1]
        torch.manual_seed(17)
        model = pb.CandidateScorer("gru").eval()
        expected, _ = model.logits_batch(examples, torch.device("cpu"))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "checkpoint.pt"
            torch.save({"condition": "gru",
                        "state_dict": {k: v.detach().clone()
                                       for k, v in model.state_dict().items()}}, path)
            torch.manual_seed(999)
            restored = pb.CandidateScorer("gru")
            pb.load_checkpoint_strict(restored, path)
            observed, _ = restored.logits_batch(examples, torch.device("cpu"))
        torch.testing.assert_close(expected, observed, rtol=0, atol=0)

    def test_output_directory_creation_refuses_existing_path(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "fresh-run"
            pb.create_output_directory(path)
            self.assertTrue(path.is_dir())
            with self.assertRaises(FileExistsError):
                pb.create_output_directory(path)

    def test_cross_episode_permutation_is_one_to_one_and_depth_matched(self):
        second_val_tid = episode_id_for_bucket(8, "validation-second")
        rows = (actor_rows(self.val_tid, "alice", "shore", "walk north")
                + actor_rows(second_val_tid, "bob", "field", "turn east"))
        val = pb.eligible(pb.reconstruct_examples(rows), "validation")
        states = torch.arange(len(val) * pb.STATE_DIM, dtype=torch.float32).reshape(
            len(val), pb.STATE_DIM)
        shuffled, info = pb.permuted_states(val, states)
        self.assertEqual(info["eligible_rows"], len(val))
        self.assertEqual(info["ineligible_rows"], 0)
        self.assertEqual(len(info["donor_mapping"]), len(val))
        for i, row in enumerate(val):
            donor = next(x for x in info["donor_mapping"]
                         if x["recipient"] == row.trajectory_id + "/" + row.actor + "/" +
                         str(row.row["target_step_index"]))
            self.assertNotEqual(donor["recipient"].split("/")[0],
                                donor["donor"].split("/")[0])
        self.assertEqual(len({tuple(shuffled[i].tolist()) for i in range(len(val))}), len(val))


if __name__ == "__main__":
    unittest.main()
