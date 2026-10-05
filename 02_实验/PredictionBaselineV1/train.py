#!/usr/bin/env python3
"""Development-only conditional behavioral-cloning baseline for LIGHT.

Drafting this file does not authorize training. See README.md for the frozen
protocol and review gate.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import platform
import random
import re
import resource
import sys
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import torch
from torch import nn
from torch.nn.utils.rnn import pack_padded_sequence

HERE = Path(__file__).resolve().parent
DEFAULT_INPUT = HERE.parent / "T0c_LIGHT" / "light_actor_local_full_v0.jsonl"
EXPECTED_ROWS = 13_463
SEEDS = (7, 19, 31)
CONDITIONS = ("o_only", "last_action", "last2", "fixed_mean",
              "learned_mean", "learned_last2", "gru")
O_DIM = 256
CAND_DIM = 256
PAIR_DIM = O_DIM + CAND_DIM
STATE_DIM = 16
READOUT_HIDDEN = 32
BATCH_SIZE = 32
MAX_EPOCHS = 15
LEARNING_RATE = 1e-3
BOOTSTRAP_REPLICATES = 2_000
BOOTSTRAP_SEED = 20_261_006
TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def stable_int(text: str, size: int = 8) -> int:
    return int.from_bytes(hashlib.blake2b(text.encode("utf-8"), digest_size=size,
                                         person=b"PredBaseV1").digest(), "big")


def bucket_for_episode(trajectory_id: str) -> int:
    return int(hashlib.sha256(trajectory_id.encode("utf-8")).hexdigest()[:8], 16) % 10


def split_name(bucket: int) -> str:
    return "train" if bucket < 7 else ("validation" if bucket < 9 else "excluded_bucket9")


def signed_hash_vector(text: str, dimension: int) -> np.ndarray:
    """Signed unigram+bigram counts; no fitted or target-derived vocabulary."""
    tokens = TOKEN_RE.findall(str(text or "").casefold())
    features = ["u:" + token for token in tokens]
    features.extend("b:" + a + chr(31) + b for a, b in zip(tokens, tokens[1:]))
    vector = np.zeros(dimension, dtype=np.float32)
    for feature in features:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=16,
                                 person=b"PredHashV1").digest()
        vector[int.from_bytes(digest[:8], "big") % dimension] += 1.0 if digest[8] & 1 else -1.0
    norm = float(np.linalg.norm(vector))
    if norm:
        vector /= norm
    return vector


def pair_vector(pair: dict[str, Any]) -> np.ndarray:
    return np.concatenate((signed_hash_vector(str(pair.get("O") or ""), O_DIM),
                           signed_hash_vector(str(pair.get("A") or ""), CAND_DIM)))


def fixed_projection() -> np.ndarray:
    """Deterministic signed 512->16 projection shared by fixed-state controls."""
    matrix = np.empty((PAIR_DIM, STATE_DIM), dtype=np.float32)
    scale = 1.0 / math.sqrt(PAIR_DIM)
    for i in range(PAIR_DIM):
        for j in range(STATE_DIM):
            bit = hashlib.blake2b(f"{i}:{j}".encode(), digest_size=1,
                                  person=b"ProjV1").digest()[0] & 1
            matrix[i, j] = scale if bit else -scale
    return matrix


FIXED_PROJECTION = fixed_projection()


def fixed_ordered_last2_projection() -> np.ndarray:
    matrix = np.empty((PAIR_DIM * 2, STATE_DIM), dtype=np.float32)
    scale = 1.0 / math.sqrt(PAIR_DIM * 2)
    for i in range(PAIR_DIM * 2):
        for j in range(STATE_DIM):
            bit = hashlib.blake2b(f"ordered:{i}:{j}".encode(), digest_size=1,
                                  person=b"ProjV1").digest()[0] & 1
            matrix[i, j] = scale if bit else -scale
    return matrix


FIXED_ORDERED_LAST2_PROJECTION = fixed_ordered_last2_projection()


def ordered_last2_vector(ex: "Example") -> np.ndarray:
    """Older-to-newer 1024-vector, left-zero-padded for a one-pair prefix."""
    tail = ex.history_vectors[-2:]
    if len(tail) == 1:
        tail = np.concatenate((np.zeros((1, PAIR_DIM), dtype=np.float32), tail), axis=0)
    return tail.reshape(PAIR_DIM * 2)


@dataclass
class Example:
    row: dict[str, Any]
    trajectory_id: str
    actor: str
    bucket: int
    prior_pairs: list[dict[str, Any]]
    history_vectors: np.ndarray
    candidates: list[str]
    gold_index: int | None
    support_miss: bool
    normalized_gold_ambiguity: bool
    o_vec: np.ndarray
    candidate_vecs: np.ndarray

    @property
    def depth(self) -> int:
        return len(self.prior_pairs)


def norm_action(value: Any) -> str:
    return str(value or "").strip().casefold()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        for line_no, line in enumerate(stream, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSON at {path}:{line_no}: {exc}") from exc
            if not isinstance(value, dict):
                raise ValueError(f"expected object at {path}:{line_no}")
            rows.append(value)
    return rows


def reconstruct_examples(rows: list[dict[str, Any]]) -> list[Example]:
    """Rebuild actor-local prefixes from the existing flattened full surface.

    The first target's previous_* pair is the initial legal input. Each target's
    current O/A enters only later rows; no current target gold enters its logits.
    """
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    episode_bucket: dict[str, int] = {}
    for row in rows:
        raw_tid, raw_actor = row.get("trajectory_id"), row.get("actor")
        if not isinstance(raw_tid, str) or not raw_tid.strip() or \
                not isinstance(raw_actor, str) or not raw_actor.strip():
            raise ValueError("trajectory_id and actor must be non-empty grouping metadata")
        tid, actor = raw_tid, raw_actor
        bucket = bucket_for_episode(tid)
        if tid in episode_bucket and episode_bucket[tid] != bucket:
            raise AssertionError("episode assigned to multiple split buckets")
        episode_bucket[tid] = bucket
        groups[(tid, actor)].append(row)

    examples: list[Example] = []
    seen: set[tuple[str, str, int]] = set()
    for (tid, actor), actor_rows in sorted(groups.items()):
        actor_rows.sort(key=lambda r: int(r["target_step_index"]))
        prefix: list[dict[str, Any]] = []
        previous_target_index: int | None = None
        for row in actor_rows:
            target_index = int(row["target_step_index"])
            key = (tid, actor, target_index)
            if key in seen:
                raise ValueError(f"duplicate actor-local target: {key}")
            seen.add(key)
            if not prefix:
                initial_a = row.get("previous_source_action_A_star")
                if not norm_action(initial_a):
                    raise ValueError(f"missing initial previous action for {key}")
                initial_step = int(row["previous_same_actor_t"])
                if initial_step >= target_index:
                    raise ValueError(f"initial history is not strictly prior for {key}")
                prefix.append({"O": row.get("previous_source_O"), "A": initial_a,
                               "step_index": initial_step})
            else:
                last = prefix[-1]
                if (row.get("previous_source_O") != last["O"] or
                        row.get("previous_source_action_A_star") != last["A"]):
                    raise ValueError(f"flattened previous pair mismatch for {key}")
                if int(row["previous_same_actor_t"]) != previous_target_index:
                    raise ValueError(f"previous target index mismatch for {key}")
            if any(int(pair["step_index"]) >= target_index for pair in prefix):
                raise ValueError(f"future/current row entered history for {key}")
            if int(row.get("actor_history_depth", len(prefix))) != len(prefix):
                raise ValueError(f"history depth mismatch for {key}")

            raw_candidates = row.get("candidate_set_factual")
            candidates = [str(c) for c in raw_candidates] if isinstance(raw_candidates, list) else []
            gold = row.get("source_action_A_star")
            matches = [i for i, c in enumerate(candidates) if norm_action(c) == norm_action(gold)]
            gold_index = matches[0] if len(matches) == 1 else None
            target_absent = len(matches) == 0
            normalized_ambiguity = len(matches) > 1
            candidate_vecs = (np.stack([signed_hash_vector(c, CAND_DIM) for c in candidates])
                              if candidates else np.zeros((0, CAND_DIM), dtype=np.float32))
            history = np.stack([pair_vector(pair) for pair in prefix])
            examples.append(Example(
                row=row, trajectory_id=tid, actor=actor, bucket=bucket_for_episode(tid),
                prior_pairs=copy.deepcopy(prefix), history_vectors=history,
                candidates=candidates, gold_index=gold_index, support_miss=target_absent,
                normalized_gold_ambiguity=normalized_ambiguity,
                o_vec=signed_hash_vector(str(row.get("source_O") or ""), O_DIM),
                candidate_vecs=candidate_vecs))

            # Teacher-forced history updates after prediction, for this actor only.
            prefix.append({"O": row.get("source_O"), "A": gold, "step_index": target_index})
            previous_target_index = target_index
    return examples


class CandidateScorer(nn.Module):
    def __init__(self, condition: str):
        super().__init__()
        self.condition = condition
        # Construct the shared readout first so its seed-wise initialization is
        # the same in every condition; recurrent/mean encoder has separate params.
        self.readout = nn.Sequential(
            nn.Linear(O_DIM + STATE_DIM + CAND_DIM, READOUT_HIDDEN),
            nn.Tanh(),
            nn.Linear(READOUT_HIDDEN, 1))
        self.encoder = None
        if condition == "gru":
            self.encoder = nn.GRU(PAIR_DIM, STATE_DIM, batch_first=True)
        elif condition == "learned_mean":
            self.encoder = nn.Linear(PAIR_DIM, STATE_DIM)
        elif condition == "learned_last2":
            self.encoder = nn.Linear(PAIR_DIM * 2, STATE_DIM)

    def state_batch(self, examples: list[Example], device: torch.device) -> torch.Tensor:
        if self.condition == "o_only":
            return torch.zeros((len(examples), STATE_DIM), dtype=torch.float32, device=device)
        if self.condition == "last_action":
            inputs = []
            for ex in examples:
                action = signed_hash_vector(str(ex.prior_pairs[-1].get("A") or ""), CAND_DIM)
                inputs.append(np.concatenate((np.zeros(O_DIM, dtype=np.float32), action)))
            source = torch.as_tensor(np.stack(inputs), dtype=torch.float32, device=device)
            return source @ torch.as_tensor(FIXED_PROJECTION, device=device)
        if self.condition in ("last2", "learned_last2"):
            source = torch.as_tensor(np.stack([ordered_last2_vector(ex) for ex in examples]),
                                     dtype=torch.float32, device=device)
            if self.condition == "last2":
                return source @ torch.as_tensor(FIXED_ORDERED_LAST2_PROJECTION, device=device)
            return torch.tanh(self.encoder(source))
        means = [ex.history_vectors.mean(axis=0) for ex in examples]
        source = torch.as_tensor(np.stack(means), dtype=torch.float32, device=device)
        if self.condition == "fixed_mean":
            return source @ torch.as_tensor(FIXED_PROJECTION, device=device)
        if self.condition == "learned_mean":
            return torch.tanh(self.encoder(source))
        if self.condition != "gru":
            raise ValueError(f"unknown condition: {self.condition}")
        seqs = [ex.history_vectors for ex in examples]
        lengths = torch.tensor([len(seq) for seq in seqs], dtype=torch.long)
        padded = np.zeros((len(seqs), int(lengths.max()), PAIR_DIM), dtype=np.float32)
        for i, seq in enumerate(seqs):
            padded[i, :len(seq)] = seq
        packed = pack_padded_sequence(torch.as_tensor(padded, device=device), lengths,
                                      batch_first=True, enforce_sorted=False)
        _, hidden = self.encoder(packed)
        return hidden[-1]

    def logits_batch(self, examples: list[Example], device: torch.device,
                     forced_states: torch.Tensor | None = None) -> tuple[torch.Tensor, list[int]]:
        counts = [len(ex.candidates) for ex in examples]
        if any(n == 0 for n in counts):
            raise ValueError("empty-candidate rows must be excluded and counted")
        states = forced_states if forced_states is not None else self.state_batch(examples, device)
        row_ids = torch.repeat_interleave(torch.arange(len(examples), device=device),
                                          torch.tensor(counts, device=device))
        o = torch.as_tensor(np.stack([ex.o_vec for ex in examples]),
                            dtype=torch.float32, device=device)
        cand = torch.as_tensor(np.concatenate([ex.candidate_vecs for ex in examples]),
                               dtype=torch.float32, device=device)
        features = torch.cat((o[row_ids], states[row_ids], cand), dim=1)
        return self.readout(features).squeeze(1), counts


def row_losses(logits: torch.Tensor, counts: list[int], gold_indices: list[int]) -> list[torch.Tensor]:
    losses = []
    for scores, gold in zip(torch.split(logits, counts), gold_indices):
        losses.append(nn.functional.cross_entropy(scores.unsqueeze(0),
                                                   torch.tensor([gold], device=logits.device)))
    return losses


def prediction_inputs(ex: Example) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return inference-only inputs; target labels are intentionally absent."""
    return ex.o_vec.copy(), ex.candidate_vecs.copy(), ex.history_vectors.copy()


def candidate_probabilities(model: CandidateScorer, examples: list[Example]) -> list[np.ndarray]:
    model.eval()
    with torch.no_grad():
        logits, counts = model.logits_batch(examples, torch.device("cpu"))
        return [x.softmax(dim=0).cpu().numpy() for x in torch.split(logits, counts)]


def create_output_directory(path: Path) -> None:
    """Atomic exclusive creation of the run directory; never reuse a run."""
    if path.exists():
        raise FileExistsError(f"refusing to reuse or overwrite output directory: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.mkdir(exist_ok=False)


def load_checkpoint_strict(model: CandidateScorer, path: Path) -> dict[str, Any]:
    payload = torch.load(path, map_location="cpu", weights_only=True)
    if payload.get("condition") != model.condition:
        raise ValueError("checkpoint condition does not match model")
    model.load_state_dict(payload["state_dict"], strict=True)
    model.eval()
    return payload


def eligible(examples: Iterable[Example], split: str) -> list[Example]:
    return [ex for ex in examples if split_name(ex.bucket) == split
            and ex.gold_index is not None and bool(ex.candidates)]


def batches(items: list[Example], batch_size: int, rng: random.Random | None = None):
    order = list(range(len(items)))
    if rng:
        rng.shuffle(order)
    for start in range(0, len(order), batch_size):
        yield [items[i] for i in order[start:start + batch_size]]


def mean_nll(model: CandidateScorer, items: list[Example], device: torch.device) -> float:
    model.eval()
    total = 0.0
    with torch.no_grad():
        for batch in batches(items, BATCH_SIZE):
            logits, counts = model.logits_batch(batch, device)
            total += sum(float(x) for x in row_losses(
                logits, counts, [int(ex.gold_index) for ex in batch]))
    return total / len(items) if items else math.nan


def grad_norm(parameters: Iterable[torch.nn.Parameter]) -> float | None:
    grads = [p.grad.detach().norm(2) for p in parameters if p.grad is not None]
    return float(torch.stack(grads).norm(2)) if grads else None


def train_one(condition: str, seed: int, train_items: list[Example],
              val_items: list[Example], output_dir: Path, epoch_stream):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    device = torch.device("cpu")
    model = CandidateScorer(condition).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    best_val, best_epoch, best_state = math.inf, 0, None
    epoch_rows = []
    for epoch in range(1, MAX_EPOCHS + 1):
        model.train()
        train_total = 0.0
        state_norms, readout_norms = [], []
        for batch in batches(train_items, BATCH_SIZE,
                             random.Random(seed * 1000 + epoch)):
            optimizer.zero_grad(set_to_none=True)
            logits, counts = model.logits_batch(batch, device)
            losses = row_losses(logits, counts, [int(ex.gold_index) for ex in batch])
            torch.stack(losses).mean().backward()
            state_norm = grad_norm(model.encoder.parameters()) if model.encoder else None
            readout_norm = grad_norm(model.readout.parameters())
            if state_norm is not None:
                state_norms.append(state_norm)
            if readout_norm is not None:
                readout_norms.append(readout_norm)
            optimizer.step()
            train_total += sum(float(loss.detach()) for loss in losses)
        train_nll = train_total / len(train_items)
        val_nll = mean_nll(model, val_items, device)
        row = {"condition": condition, "seed": seed, "epoch": epoch,
               "train_nll_nats": train_nll, "validation_nll_nats_post_selection_dev": val_nll,
               "mean_batch_state_grad_norm": float(np.mean(state_norms)) if state_norms else None,
               "mean_batch_readout_grad_norm": float(np.mean(readout_norms)) if readout_norms else None,
               "train_rows": len(train_items), "validation_rows": len(val_items)}
        epoch_rows.append(row)
        epoch_stream.write(canonical_json(row) + "\n")
        epoch_stream.flush()
        # Lowest validation NLL; ties keep earliest epoch. This is selection on
        # development validation and its later score is post-selection descriptive.
        if val_nll < best_val:
            best_val, best_epoch = val_nll, epoch
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
    if best_state is None:
        raise RuntimeError("no checkpoint selected")
    model.load_state_dict(best_state, strict=True)
    model.eval()
    checkpoint = {"condition": condition, "seed": seed, "selected_epoch": best_epoch,
                  "selected_validation_nll_nats_post_selection_dev": best_val,
                  "state_dict": best_state,
                  "architecture": {"o_dim": O_DIM, "candidate_dim": CAND_DIM,
                                   "pair_dim": PAIR_DIM, "state_dim": STATE_DIM,
                                   "readout_hidden": READOUT_HIDDEN}}
    ckpt_dir = output_dir / "checkpoints"
    ckpt_dir.mkdir(exist_ok=True)
    ckpt_path = ckpt_dir / f"{condition}_seed{seed}.pt"
    torch.save(checkpoint, ckpt_path)
    selection = {"condition": condition, "seed": seed, "selected_epoch": best_epoch,
                 "selected_validation_nll_nats_post_selection_dev": best_val,
                 "checkpoint": ckpt_path.relative_to(output_dir).as_posix(),
                 "checkpoint_sha256": sha256_file(ckpt_path), "epochs": epoch_rows}
    return model, selection


def state_vectors(model: CandidateScorer, items: list[Example]) -> torch.Tensor:
    model.eval()
    result = []
    with torch.no_grad():
        for batch in batches(items, BATCH_SIZE):
            result.append(model.state_batch(batch, torch.device("cpu")).cpu())
    return torch.cat(result) if result else torch.zeros((0, STATE_DIM))


def predict_losses(model: CandidateScorer, items: list[Example],
                   forced_states: torch.Tensor | None = None) -> dict[tuple[str, str, int], float]:
    result = {}
    offset = 0
    model.eval()
    with torch.no_grad():
        for batch in batches(items, BATCH_SIZE):
            forced = forced_states[offset:offset + len(batch)] if forced_states is not None else None
            logits, counts = model.logits_batch(batch, torch.device("cpu"), forced)
            for ex, loss in zip(batch, row_losses(logits, counts,
                                                   [int(x.gold_index) for x in batch])):
                result[(ex.trajectory_id, ex.actor, int(ex.row["target_step_index"]))] = float(loss)
            offset += len(batch)
    return result


def permuted_states(items: list[Example], actual: torch.Tensor):
    by_depth: dict[int, list[int]] = defaultdict(list)
    for i, ex in enumerate(items):
        by_depth[ex.depth].append(i)
    result = actual.clone()
    donor_by_recipient: dict[int, int] = {}
    ineligible: list[int] = []
    for _, indices in sorted(by_depth.items()):
        ordered = sorted(indices, key=lambda i: (items[i].trajectory_id, items[i].actor,
                                                 int(items[i].row["target_step_index"])))
        chosen = None
        for shift in range(1, len(ordered)):
            donors = ordered[shift:] + ordered[:shift]
            if all(items[r].trajectory_id != items[d].trajectory_id
                   for r, d in zip(ordered, donors)):
                chosen = donors
                break
        if chosen is None:
            ineligible.extend(ordered)
            continue
        for recipient, donor in zip(ordered, chosen):
            result[recipient] = actual[donor]
            donor_by_recipient[recipient] = donor
    mapping = [{"recipient": items[r].trajectory_id + "/" + items[r].actor + "/" +
                str(items[r].row["target_step_index"]),
                "donor": items[d].trajectory_id + "/" + items[d].actor + "/" +
                str(items[d].row["target_step_index"])}
               for r, d in sorted(donor_by_recipient.items())]
    return result, {"eligible_rows": len(donor_by_recipient),
                    "ineligible_rows": len(ineligible),
                    "ineligible_reason": "no same-depth one-to-one cross-episode permutation"
                    if ineligible else None,
                    "donor_mapping": mapping}


def paired_cluster_bootstrap(prediction_rows: list[dict[str, Any]], lhs: str, rhs: str,
                             row_keys: set[tuple[str, str, int]], seed_offset: int):
    by_episode: dict[str, list[float]] = defaultdict(list)
    selected_rows = 0
    for row in prediction_rows:
        key = (row["trajectory_id"], row["actor"], row["target_step_index"])
        if key not in row_keys:
            continue
        a, b = row["losses_nats"].get(lhs), row["losses_nats"].get(rhs)
        if a is None or b is None:
            continue
        by_episode[row["trajectory_id"]].append(float(a) - float(b))
        selected_rows += 1
    episodes = sorted(by_episode)
    if not episodes:
        return {"delta_nll_nats_lhs_minus_rhs": None, "ci95": None,
                "rows": 0, "episodes": 0, "reason": "no common scored rows"}
    episode_sums = np.asarray([sum(by_episode[e]) for e in episodes], dtype=np.float64)
    episode_counts = np.asarray([len(by_episode[e]) for e in episodes], dtype=np.int64)
    point = float(episode_sums.sum() / episode_counts.sum())
    rng = np.random.default_rng(BOOTSTRAP_SEED + seed_offset)
    draws = np.empty(BOOTSTRAP_REPLICATES, dtype=np.float64)
    for b in range(BOOTSTRAP_REPLICATES):
        chosen = rng.integers(0, len(episodes), size=len(episodes))
        numerator = episode_sums[chosen].sum()
        denominator = episode_counts[chosen].sum()
        draws[b] = numerator / denominator
    lo, hi = np.quantile(draws, [0.025, 0.975])
    return {"delta_nll_nats_lhs_minus_rhs": float(point),
            "ci95_episode_cluster_bootstrap": [float(lo), float(hi)],
            "rows": selected_rows, "episodes": len(episodes),
            "estimand": "row-weighted mean; episode-cluster resampling",
            "reason": None}


def write_json_exclusive(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def write_bytes_exclusive(path: Path, content: bytes) -> None:
    with path.open("xb") as stream:
        stream.write(content)


def write_jsonl_exclusive(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(canonical_json(row) + "\n")


def split_report(examples: list[Example]) -> dict[str, Any]:
    result = {}
    for bucket in range(10):
        subset = [ex for ex in examples if ex.bucket == bucket]
        ids = sorted({ex.trajectory_id for ex in subset})
        result[str(bucket)] = {
            "split": split_name(bucket), "episodes": len(ids), "rows": len(subset),
            "actor_trajectory_units": len({(ex.trajectory_id, ex.actor) for ex in subset}),
            "episode_ids_sha256": hashlib.sha256("\n".join(ids).encode()).hexdigest()}
    return result


def split_id_manifest(examples: list[Example]) -> dict[str, Any]:
    manifest = {}
    for bucket in range(10):
        ids = sorted({ex.trajectory_id for ex in examples if ex.bucket == bucket})
        manifest[str(bucket)] = {"split": split_name(bucket), "trajectory_ids": ids}
    return manifest


def count_report(examples: list[Example]) -> dict[str, Any]:
    result = {}
    for split in ("train", "validation", "excluded_bucket9"):
        subset = [ex for ex in examples if split_name(ex.bucket) == split]
        result[split] = {"rows": len(subset),
                         "episodes": len({ex.trajectory_id for ex in subset}),
                         "actor_trajectory_units": len({(ex.trajectory_id, ex.actor) for ex in subset}),
                         "support_miss_rows_target_absent": sum(ex.support_miss for ex in subset),
                         "normalized_gold_ambiguity_rows": sum(ex.normalized_gold_ambiguity
                                                               for ex in subset),
                         "empty_candidate_rows": sum(not ex.candidates for ex in subset),
                         "scored_rows": sum(ex.gold_index is not None and bool(ex.candidates)
                                            for ex in subset)}
    return result


def run(input_path: Path, output_path: Path, seeds: tuple[int, ...] = SEEDS) -> None:
    create_output_directory(output_path)
    started = time.perf_counter()
    snapshot_sources = {
        "protocol_snapshot.md": HERE / "README.md",
        "train_source_snapshot.py": Path(__file__).resolve(),
        "tests_source_snapshot.py": HERE / "test_prediction_baseline_v1.py",
    }
    snapshot_hashes = {}
    for snapshot_name, source_path in snapshot_sources.items():
        source_bytes = source_path.read_bytes()
        write_bytes_exclusive(output_path / snapshot_name, source_bytes)
        snapshot_hashes[snapshot_name] = hashlib.sha256(source_bytes).hexdigest()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    rows = read_jsonl(input_path)
    if input_path.resolve() == DEFAULT_INPUT.resolve() and len(rows) != EXPECTED_ROWS:
        raise ValueError(f"expected {EXPECTED_ROWS} canonical rows; found {len(rows)}")
    examples = reconstruct_examples(rows)
    train_items = eligible(examples, "train")
    val_items = eligible(examples, "validation")
    if not train_items or not val_items:
        raise ValueError("no eligible rows in train or validation split")
    audit_path = input_path.parent / "light_actor_local_history_gate_v0.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.exists() else {}
    config = {
        "status": "all_development_not_untouched_formal_test",
        "validation_metrics_are": "post-selection descriptive development metrics, not independent generalization estimates",
        "input_path": str(input_path), "input_sha256": sha256_file(input_path),
        "input_rows": len(rows), "canonical_expected_rows": EXPECTED_ROWS,
        "upstream_raw_replay_sha256": audit.get("replay_sha256"),
        "upstream_gate_audit_sha256": sha256_file(audit_path) if audit_path.exists() else None,
        "split": {"episode_hash": "int(SHA256(trajectory_id UTF-8).hexdigest()[:8], 16) modulo 10",
                  "train_buckets": "0-6", "validation_buckets": "7-8",
                  "bucket9": "excluded from training and scoring; not untouched test"},
        "features": {"tokenizer": "Unicode word tokens, casefolded, unigrams+adjacent bigrams",
                     "signed_hash": "BLAKE2b deterministic signed counts, L2-normalized",
                     "current_O_dim": O_DIM, "candidate_dim": CAND_DIM,
                     "history_pair_dim": PAIR_DIM, "history_pair": "concat hash(O,256), hash(A,256)",
                     "hidden_dim": STATE_DIM, "readout_hidden": READOUT_HIDDEN,
                     "no_fitted_vocabulary": True, "metadata_features": False},
        "conditions": list(CONDITIONS) + ["uniform"],
        "training": {"cpu": True, "torch_threads": 1, "deterministic_algorithms": True,
                     "seeds": list(seeds), "batch_size": BATCH_SIZE,
                     "max_epochs": MAX_EPOCHS, "optimizer": "Adam",
                     "learning_rate": LEARNING_RATE, "weight_decay": 0,
                     "checkpoint_selection": "lowest validation mean NLL, earliest tie"},
        "reporting": {"validation_role": "post-selection development description only",
                      "strata": ["depth==1", "depth>=2", "depth>=4",
                                 "not exact_previous_pair"],
                      "bootstrap_unit": "episode", "estimand": "row-weighted mean paired delta",
                      "bootstrap_seed": BOOTSTRAP_SEED,
                      "bootstrap_replicates": BOOTSTRAP_REPLICATES,
                      "three_seeds_are_not_population_samples": True},
        "versions": {"python": sys.version, "platform": platform.platform(),
                      "torch": torch.__version__, "numpy": np.__version__},
        "code_sha256": sha256_file(Path(__file__).resolve()),
        "test_code_sha256": sha256_file(HERE / "test_prediction_baseline_v1.py"),
        "protocol_readme_sha256": sha256_file(HERE / "README.md"),
        "source_snapshots_sha256": snapshot_hashes,
        "split_buckets": split_report(examples), "counts": count_report(examples)}
    write_json_exclusive(output_path / "config.json", config)
    write_json_exclusive(output_path / "split_manifest.json", split_id_manifest(examples))

    predictions: dict[tuple[str, str, int], dict[str, Any]] = {}
    selected = []
    with (output_path / "epoch_metrics.jsonl").open("x", encoding="utf-8", newline="\n") as epoch_stream:
        for condition in CONDITIONS:
            for seed in seeds:
                model, selection = train_one(condition, seed, train_items, val_items,
                                              output_path, epoch_stream)
                selected.append(selection)
                losses = predict_losses(model, val_items)
                for ex in val_items:
                    key = (ex.trajectory_id, ex.actor, int(ex.row["target_step_index"]))
                    item = predictions.setdefault(key, {
                        "trajectory_id": ex.trajectory_id, "actor": ex.actor,
                        "target_step_index": int(ex.row["target_step_index"]),
                        "actor_history_depth": ex.depth,
                        "exact_previous_pair": bool(ex.row.get("exact_previous_pair", False)),
                        "candidate_count": len(ex.candidates),
                        "target_absent_from_normalized_support": ex.support_miss,
                        "normalized_gold_ambiguity": ex.normalized_gold_ambiguity,
                        "source_action_A_star": ex.row.get("source_action_A_star"),
                        "losses_nats": {}})
                    item["losses_nats"][f"{condition}_seed{seed}"] = losses[key]
                # Reload into a fresh model, then demand exact deterministic replay.
                fresh_model = CandidateScorer(condition).to(torch.device("cpu"))
                load_checkpoint_strict(fresh_model, output_path / selection["checkpoint"])
                if predict_losses(fresh_model, val_items) != losses:
                    raise RuntimeError(f"checkpoint replay mismatch for {condition}/{seed}")
                model = fresh_model
                if condition == "gru":
                    states = state_vectors(model, val_items)
                    zero_losses = predict_losses(model, val_items, torch.zeros_like(states))
                    shuffled_states, permutation = permuted_states(val_items, states)
                    shuffled_losses = predict_losses(model, val_items, shuffled_states)
                    selection["state_permutation"] = permutation
                    mapped_recipients = {entry["recipient"] for entry in permutation["donor_mapping"]}
                    for i, ex in enumerate(val_items):
                        key = (ex.trajectory_id, ex.actor, int(ex.row["target_step_index"]))
                        predictions[key]["losses_nats"][f"gru_state_zero_seed{seed}"] = zero_losses[key]
                        row_key = key[0] + "/" + key[1] + "/" + str(key[2])
                        predictions[key]["losses_nats"][f"gru_permuted_state_seed{seed}"] = (
                            shuffled_losses[key] if row_key in mapped_recipients else None)

    for ex in val_items:
        key = (ex.trajectory_id, ex.actor, int(ex.row["target_step_index"]))
        predictions[key]["losses_nats"]["uniform"] = math.log(len(ex.candidates))
    pred_rows = [predictions[k] for k in sorted(predictions)]
    write_jsonl_exclusive(output_path / "validation_row_losses.jsonl", pred_rows)
    write_json_exclusive(output_path / "selected_checkpoints.json", selected)

    all_keys = {(r["trajectory_id"], r["actor"], r["target_step_index"]) for r in pred_rows}
    strata = {
        "all": all_keys,
        "depth_eq_1": {(r["trajectory_id"], r["actor"], r["target_step_index"])
                       for r in pred_rows if r["actor_history_depth"] == 1},
        "depth_ge_2": {(r["trajectory_id"], r["actor"], r["target_step_index"])
                       for r in pred_rows if r["actor_history_depth"] >= 2},
        "depth_ge_4": {(r["trajectory_id"], r["actor"], r["target_step_index"])
                       for r in pred_rows if r["actor_history_depth"] >= 4},
        "nontrivial_not_exact_previous_pair": {
            (r["trajectory_id"], r["actor"], r["target_step_index"])
            for r in pred_rows if not r["exact_previous_pair"]}}
    summaries = {}
    for stratum, keys in strata.items():
        selected_rows = [r for r in pred_rows
                         if (r["trajectory_id"], r["actor"], r["target_step_index"]) in keys]
        condition_nll = {}
        for condition in CONDITIONS:
            for seed in seeds:
                key = f"{condition}_seed{seed}"
                condition_nll[key] = float(np.mean([r["losses_nats"][key] for r in selected_rows])) \
                    if selected_rows else None
        for seed in seeds:
            for diagnostic in (f"gru_state_zero_seed{seed}", f"gru_permuted_state_seed{seed}"):
                diagnostic_values = [r["losses_nats"].get(diagnostic) for r in selected_rows]
                diagnostic_values = [value for value in diagnostic_values if value is not None]
                condition_nll[diagnostic] = (float(np.mean(diagnostic_values))
                                             if diagnostic_values else None)
                condition_nll[diagnostic + "_rows"] = len(diagnostic_values)
                condition_nll[diagnostic + "_episodes"] = len({
                    r["trajectory_id"] for r in selected_rows
                    if r["losses_nats"].get(diagnostic) is not None})
        seed_spread = {}
        for condition in CONDITIONS:
            per_seed = [condition_nll[f"{condition}_seed{seed}"] for seed in seeds]
            scored_seeds = [value for value in per_seed if value is not None]
            seed_spread[condition] = {
                "mean_across_repeated_fits": float(np.mean(scored_seeds)) if scored_seeds else None,
                "sd_across_repeated_fits": (float(np.std(scored_seeds, ddof=1))
                                             if len(scored_seeds) > 1 else None),
                "seed_count": len(scored_seeds),
                "reason": "no eligible rows in this stratum" if not scored_seeds else None,
                "interpretation": "descriptive repeated-fit spread; not a population CI"}
        condition_nll["uniform"] = float(np.mean([r["losses_nats"]["uniform"] for r in selected_rows])) \
            if selected_rows else None
        deltas = {}
        for condition in CONDITIONS:
            if condition == "o_only":
                continue
            for seed in seeds:
                lhs, rhs = f"{condition}_seed{seed}", f"o_only_seed{seed}"
                offset = stable_int(stratum + "/" + lhs, 4) % 100_000
                deltas[lhs] = paired_cluster_bootstrap(pred_rows, lhs, rhs, keys, offset)
        for seed in seeds:
            gru_key = f"gru_seed{seed}"
            mean_key = f"learned_mean_seed{seed}"
            deltas[f"gru_seed{seed}_vs_learned_mean_seed{seed}"] = \
                paired_cluster_bootstrap(pred_rows, gru_key, mean_key, keys,
                                         stable_int(stratum + "/gru-vs-learned-mean/" + str(seed), 4))
            zero_key = f"gru_state_zero_seed{seed}"
            deltas[f"gru_seed{seed}_vs_state_zero_seed{seed}"] = \
                paired_cluster_bootstrap(pred_rows, gru_key, zero_key, keys,
                                         stable_int(stratum + "/gru-vs-zero/" + str(seed), 4))
            perm_key = f"gru_permuted_state_seed{seed}"
            perm_keys = {(r["trajectory_id"], r["actor"], r["target_step_index"])
                         for r in pred_rows if (r["trajectory_id"], r["actor"],
                                                r["target_step_index"]) in keys and
                         r["losses_nats"].get(perm_key) is not None}
            deltas[f"gru_seed{seed}_vs_permuted_state_seed{seed}"] = \
                paired_cluster_bootstrap(pred_rows, gru_key, perm_key, perm_keys,
                                         stable_int(stratum + "/gru-vs-permuted/" + str(seed), 4))
            deltas[f"gru_seed{seed}_permutation_intersection_rows"] = len(perm_keys)
        summaries[stratum] = {"rows": len(selected_rows),
                              "episodes": len({r["trajectory_id"] for r in selected_rows}),
                              "post_selection_dev_nll_nats_by_seed": condition_nll,
                              "descriptive_seed_spread": seed_spread,
                              "paired_episode_cluster_deltas_vs_o_only": deltas,
                              "interpretation": "post-selection development description only"}
    write_json_exclusive(output_path / "seed_summaries_and_cluster_bootstrap.json", {
        "status": "post_selection_development_only_not_formal_test",
        "seeds_are_repeated_fits_not_independent_episode_samples": True,
        "seeds_reported": list(seeds), "strata": summaries})

    parameter_counts = {}
    for condition in CONDITIONS:
        model = CandidateScorer(condition)
        parameter_counts[condition] = {
            "trainable_parameters": sum(p.numel() for p in model.parameters() if p.requires_grad),
            "state_encoder_parameters": sum(p.numel() for p in model.encoder.parameters())
            if model.encoder else 0,
            "readout_parameters": sum(p.numel() for p in model.readout.parameters())}
    report = {
        "parameter_counts": parameter_counts,
        "theoretical_retained_16_float_state_bytes": STATE_DIM * 4,
        "inference_prefix_reencoded_per_prediction": True,
        "online_runtime_memory_or_latency_measured": False,
        "elapsed_seconds": time.perf_counter() - started,
        "peak_rss_platform_units": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "peak_rss_units_note": "OS/platform-specific resource.getrusage units; no conversion assumed",
        "checkpoint_bytes": {s["checkpoint"]: (output_path / s["checkpoint"]).stat().st_size
                             for s in selected}}
    write_json_exclusive(output_path / "resource_and_parameter_counts.json", report)
    manifest = {"status": "development_only_not_formal_test", "seeds_reported": list(seeds),
                "input_sha256": config["input_sha256"], "code_sha256": config["code_sha256"],
                "test_code_sha256": config["test_code_sha256"],
                "protocol_readme_sha256": config["protocol_readme_sha256"],
                "output_files_sha256": {
                    p.relative_to(output_path).as_posix(): sha256_file(p)
                    for p in sorted(output_path.rglob("*")) if p.is_file()}}
    write_json_exclusive(output_path / "output_manifest.json", manifest)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT,
                        help="existing actor-local full LIGHT JSONL; raw replay derivation is not performed")
    parser.add_argument("--out", type=Path, required=True,
                        help="new output directory; any existing path is refused")
    parser.add_argument("--reproduction-seed", type=int, choices=SEEDS,
                        help="optional exact one-seed reproduction in a separate new output directory")
    args = parser.parse_args(argv)
    try:
        seeds = (args.reproduction_seed,) if args.reproduction_seed is not None else SEEDS
        run(args.input.expanduser().resolve(), args.out.expanduser().resolve(), seeds)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
