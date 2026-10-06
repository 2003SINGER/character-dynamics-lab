#!/usr/bin/env python3
"""Frozen source-conditional candidate ranker; real fitting remains gated.

This module has no authorization switch. Its real-data entrypoint always stops
while the pinned projection says training is unauthorized. `--synthetic` runs
only tiny generated data and writes an explicitly synthetic artifact bundle.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import platform
import random
import re
import resource
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence

import numpy as np
import torch
from torch import nn

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONTRACT_DIR = ROOT / "outputs/light_source_ranking_v1_20261006/contract_v1"
PROJECTED_PATH = CONTRACT_DIR / "projected_inputs.jsonl"
DEFAULT_RUN_ROOT = ROOT / "outputs/light_source_ranking_v1_20261006/trainer_runs"
EXPECTED_ROWS = 13_463
EXPECTED_SPLITS = {"train": (9_530, 3_490), "validation": (2_717, 986), "excluded_bucket9": (1_216, 468)}
EXPECTED_COHORT_DIGEST = "3a059162d09e2a8b126c468d9d73d6fa60d582e88d52475350e49b88a20ac1bd"
EXPECTED_SOURCE_KEY_DIGEST = "905653a6b3125d3136e47aec8eb21125ca4beab0a19c5d11e159d70b1c3827f7"
EXPECTED_PROJECTED_SHA256 = "2d839c62ddf2194b1968fe5b22913db9950aa10bd3647fe2179745b6b4efcef5"
EXPECTED_INPUT_SHA256 = "b414f176bf7c6d0e1f47536bab8c251ae7d39ead5b40550310127294f74e5646"
EXPECTED_PROTOCOL_SHA256 = "5318bffe1f417e6ceb5dc5284fbcbb011808117f775d1225f66d61195528e3cf"
EXPECTED_BUILDER_SHA256 = "9c1850e38320ef459b38cc2740cbec6ff948036f8f564c9567f18aebbedc42d4"
EXPECTED_TEST_SHA256 = "748504e2167aa09c9b972cf1d8cc0d30b4abc01ad767ce814aaa318c63edc966"
SEEDS = (7, 19, 31)
CONDITIONS = ("context_only", "last2_core", "pooled_core", "gru_core", "gru_no_context",
              "gru_no_dialogue", "gru_no_persona", "gru_plus_partner_raw_commands", "uniform")
DIMENSIONS = {"persona": 256, "context": 256, "candidate": 256,
              "history_turn": 453, "speech": 256, "action": 128, "emote": 64,
              "role": 2, "presence": 3, "state": 16}
BATCH_SIZE, MAX_EPOCHS, LEARNING_RATE = 32, 15, 0.001
BOOTSTRAP_REPLICATES, BOOTSTRAP_SEED = 2_000, 104_729
TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)


def frozen_training_config() -> dict[str, Any]:
    return {"batch_size": BATCH_SIZE, "max_epochs": MAX_EPOCHS, "learning_rate": LEARNING_RATE,
            "optimizer": "Adam", "weight_decay": 0.0, "scheduler": None, "dropout": 0.0,
            "bootstrap_replicates": BOOTSTRAP_REPLICATES, "bootstrap_seed": BOOTSTRAP_SEED,
            "device": "cpu", "torch_threads": 1, "deterministic_algorithms": True}


def validate_new_output_path(path: Path) -> Path:
    path = Path(path).absolute()
    outputs_root = (ROOT / "outputs").resolve()
    if path.exists() or path.is_symlink():
        raise FileExistsError(f"refusing existing output: {path}")
    if outputs_root not in path.resolve().parents:
        raise ValueError("run output must be under ROOT/outputs")
    for parent in (path, *path.parents):
        if parent == ROOT or parent == outputs_root:
            break
        if parent.is_symlink():
            raise ValueError(f"symlink output path forbidden: {parent}")
    return path


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def signed_hash_vector(text: str | None, dimension: int) -> np.ndarray:
    """PredictionBaselineV1-compatible signed unigram/bigram hashing."""
    if dimension <= 0:
        raise ValueError("dimension must be positive")
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


def episode_bucket(trajectory_id: str) -> int:
    return int(hashlib.sha256(trajectory_id.encode("utf-8")).hexdigest()[:8], 16) % 10


def split_name(bucket: int) -> str:
    return "train" if bucket < 7 else "validation" if bucket < 9 else "excluded_bucket9"


def _presence(value: str | None) -> float:
    return float(isinstance(value, str) and bool(value.strip()))


class FeatureEncoder:
    """Pure feature-only encoder. It calls the projected-schema allowlist first."""

    def features(self, projected_row: dict[str, Any], condition: str) -> dict[str, np.ndarray]:
        if condition not in CONDITIONS:
            raise ValueError(f"unknown condition: {condition}")
        # This helper deliberately extracts no supervision/provenance/admission fields.
        from project_inputs import features as projected_features
        view = "diagnostic_plus_partner_raw_commands" if condition == "gru_plus_partner_raw_commands" else "core"
        allowed = projected_features(projected_row, view=view, include_context=True)
        persona = signed_hash_vector(allowed["self_persona"], 256)
        context_text = "" if condition == "gru_no_context" else allowed["recorded_environment_snapshot"]
        context = signed_hash_vector(context_text, 256)
        if condition == "gru_no_persona":
            persona.fill(0)
        turns: list[np.ndarray] = []
        for group in allowed["history"]:
            speech = group["speech"]
            action = group["action"]
            emote = group["emote"]
            if condition == "gru_no_dialogue":
                speech = emote = None
            role = np.asarray([float(group["role"] == "self"), float(group["role"] == "partner")], dtype=np.float32)
            pieces = (signed_hash_vector(speech, 256), signed_hash_vector(action, 128),
                      signed_hash_vector(emote, 64), role,
                      np.asarray([_presence(speech), _presence(action), _presence(emote)], dtype=np.float32))
            turn = np.concatenate(pieces).astype(np.float32, copy=False)
            if turn.shape != (453,):
                raise AssertionError(f"history turn shape {turn.shape} != (453,)")
            turns.append(turn)
        history = np.stack(turns) if turns else np.zeros((0, 453), dtype=np.float32)
        candidates = (np.stack([signed_hash_vector(c, 256) for c in allowed["recorded_support"]])
                      if allowed["recorded_support"] else np.zeros((0, 256), dtype=np.float32))
        return {"persona": persona.astype(np.float32, copy=False),
                "context": context.astype(np.float32, copy=False),
                "history": history.astype(np.float32, copy=False),
                "candidates": candidates.astype(np.float32, copy=False)}


@dataclass(frozen=True)
class Example:
    features: dict[str, np.ndarray]
    trajectory_id: str
    actor: str
    bucket: int
    support: tuple[str, ...]
    gold_index: int | None
    eligibility: str
    source_row: int
    history_refs: tuple[str, ...] = ()
    history_channel_counts: dict[str, Any] | None = None
    history_refs_complete: bool = False

    @property
    def split(self) -> str:
        return split_name(self.bucket)


def label_eligibility(gold: Any, support: Any) -> tuple[str, int | None]:
    if not isinstance(support, list) or not support or any(not isinstance(x, str) or not x.strip() for x in support):
        return ("bad_support", None)
    if not isinstance(gold, str) or not gold.strip():
        return ("missing_target", None)
    norm = lambda s: s.strip().casefold()
    matches = [i for i, candidate in enumerate(support) if norm(candidate) == norm(gold)]
    if len(matches) == 1:
        return ("unique", matches[0])
    if not matches:
        return ("absent_target", None)
    return ("ambiguous_target", None)


def build_examples(projected_rows: Sequence[dict[str, Any]], conditions: Iterable[str] = CONDITIONS) -> dict[str, list[Example]]:
    """Join feature tensors and audited metadata; labels never enter encoder."""
    encoder = FeatureEncoder()
    requested = tuple(conditions)
    result = {c: [] for c in requested}
    seen: set[tuple[str, int, str]] = set()
    for row_index, row in enumerate(projected_rows, 1):
        # Validate/model-extract before the separate supervision/provenance read.
        encoded = {c: encoder.features(row, c) for c in requested}
        supervision = row.get("supervision")
        provenance = row.get("provenance")
        if not isinstance(supervision, dict) or not isinstance(provenance, dict):
            raise ValueError(f"row {row_index}: supervision/provenance object missing")
        tid, actor = provenance.get("trajectory_id"), provenance.get("actor")
        if not isinstance(tid, str) or not tid or not isinstance(actor, str) or not actor:
            raise ValueError(f"row {row_index}: invalid split/group metadata")
        bucket = episode_bucket(tid)
        if provenance.get("split_bucket") != bucket or provenance.get("split") != split_name(bucket):
            raise ValueError(f"row {row_index}: episode split metadata mismatch")
        key = (tid, provenance.get("target_physical_index"), actor.casefold())
        if key in seen:
            raise ValueError(f"row {row_index}: duplicate source row key")
        seen.add(key)
        support = row["candidate_surface"]["recorded_support"]
        status, gold_index = label_eligibility(supervision.get("recorded_action"), support)
        for condition in requested:
            refs = provenance.get("payload_history_turn_refs", [])
            raw_history = row["history_views"]["core"]
            if "target_raw_turn_index" in provenance:
                target_raw = provenance["target_raw_turn_index"]
                if not isinstance(refs, list) or len(refs) != len(raw_history):
                    raise ValueError(f"row {row_index}: history refs do not align to turns")
                raw_indices = []
                for group, ref in zip(raw_history, refs):
                    if not isinstance(ref, dict) or ref.get("role") != group["role"]:
                        raise ValueError(f"row {row_index}: history ref role mismatch")
                    raw_index = ref.get("raw_turn_index")
                    if type(raw_index) is not int or raw_index >= target_raw:
                        raise ValueError(f"row {row_index}: history ref is not strictly prior")
                    raw_indices.append(raw_index)
                if raw_indices != sorted(set(raw_indices)):
                    raise ValueError(f"row {row_index}: history refs are not ordered")
            history_refs = tuple(ref.get("source_ref", "") for ref in refs if isinstance(ref, dict))
            channel_counts = {}
            for view, groups in row["history_views"].items():
                channel_counts[view] = {}
                for role in ("self", "partner"):
                    channel_counts[view][role] = {}
                    for channel in ("speech", "action", "emote"):
                        selected = [g for g in groups if g["role"] == role]
                        channel_counts[view][role][channel] = {
                            "present": sum(g[channel] is not None for g in selected),
                            "null": sum(g[channel] is None for g in selected),
                            "refs": [refs[j].get("source_ref", "") for j, g in enumerate(groups)
                                     if g["role"] == role and g[channel] is not None and j < len(refs)]}
            result[condition].append(Example(encoded[condition], tid, actor, bucket,
                                              tuple(support), gold_index, status, row_index, history_refs, channel_counts,
                                              len(refs) == len(raw_history)))
    return result


class RankingModel(nn.Module):
    """One condition's specified state encoder plus the shared candidate head."""

    def __init__(self, condition: str):
        super().__init__()
        if condition not in CONDITIONS:
            raise ValueError(f"unknown condition: {condition}")
        self.condition = condition
        # Initialize the common candidate head first so a fixed seed starts
        # every learned condition from identical scorer weights.
        self.head = None if condition == "uniform" else nn.Sequential(nn.Linear(784, 32), nn.Tanh(), nn.Linear(32, 1))
        self.pool_phi = self.pool_rho = self.gru = self.last2 = None
        if condition in ("gru_core", "gru_no_context", "gru_no_dialogue", "gru_no_persona",
                         "gru_plus_partner_raw_commands"):
            self.gru = nn.GRU(input_size=453, hidden_size=16, batch_first=True)
        elif condition == "pooled_core":
            self.pool_phi = nn.Sequential(nn.Linear(453, 32), nn.Tanh(), nn.Linear(32, 32), nn.Tanh())
            self.pool_rho = nn.Sequential(nn.Linear(33, 16), nn.Tanh())
        elif condition == "last2_core":
            self.last2 = nn.Sequential(nn.Linear(906, 16), nn.Tanh())

    def encode_state(self, history: torch.Tensor) -> torch.Tensor:
        if history.ndim != 2 or history.shape[1] != 453:
            raise ValueError("history must have shape (n_turns,453)")
        n = history.shape[0]
        if self.condition in ("context_only", "uniform"):
            return history.new_zeros(16)
        if self.condition == "last2_core":
            tail = history[-2:]
            if n == 0:
                tail = history.new_zeros((2, 453))
            elif n == 1:
                tail = torch.cat((history.new_zeros((1, 453)), tail), dim=0)
            return self.last2(tail.reshape(906))
        if self.condition == "pooled_core":
            pooled = self.pool_phi(history).sum(dim=0) if n else history.new_zeros(32)
            return self.pool_rho(torch.cat((pooled, history.new_tensor([math.log1p(n)]))))
        if self.gru is not None:
            if n == 0:
                return history.new_zeros(16)
            # Explicit zero state. torch GRU default is zeros; pass it to make contract visible.
            h0 = history.new_zeros((1, 1, 16))
            _, h = self.gru(history.unsqueeze(0), h0)
            return h[-1, 0]
        raise ValueError("uniform has no learned state encoder")

    def logits(self, features: dict[str, np.ndarray] | dict[str, torch.Tensor]) -> torch.Tensor:
        if self.condition == "uniform":
            raise ValueError("uniform condition has no learned logits")
        persona = _as_tensor(features["persona"])
        context = _as_tensor(features["context"])
        history = _as_tensor(features["history"])
        candidates = _as_tensor(features["candidates"])
        if persona.shape != (256,) or context.shape != (256,) or candidates.ndim != 2 or candidates.shape[1] != 256:
            raise ValueError("feature shape contract violated")
        state = self.encode_state(history)
        static = torch.cat((persona, context))
        repeated = static.unsqueeze(0).expand(candidates.shape[0], -1)
        states = state.unsqueeze(0).expand(candidates.shape[0], -1)
        return self.head(torch.cat((repeated, states, candidates), dim=1)).squeeze(-1)


def _as_tensor(value: Any) -> torch.Tensor:
    if isinstance(value, torch.Tensor):
        return value.to(dtype=torch.float32, device="cpu")
    return torch.as_tensor(value, dtype=torch.float32, device="cpu")


def trainable_parameter_count(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


def select_best_checkpoint(epoch_nlls: Sequence[float]) -> int:
    """Return one-based earliest epoch attaining the lowest finite validation NLL."""
    if not epoch_nlls or any(not math.isfinite(float(x)) for x in epoch_nlls):
        raise ValueError("checkpoint NLLs must be a nonempty finite sequence")
    return min(range(len(epoch_nlls)), key=lambda i: (float(epoch_nlls[i]), i)) + 1


def _eligible(examples: Sequence[Example]) -> list[Example]:
    return [e for e in examples if e.eligibility == "unique" and e.gold_index is not None and e.split != "excluded_bucket9"]


def _nll(model: RankingModel, examples: Sequence[Example]) -> float | None:
    eligible = _eligible(examples)
    if not eligible:
        return None
    losses = []
    model.eval()
    with torch.no_grad():
        for e in eligible:
            logits = model.logits(e.features)
            losses.append(float(nn.functional.cross_entropy(logits.unsqueeze(0), torch.tensor([e.gold_index]))))
    return float(np.mean(losses))


def train_one(model: RankingModel, train_rows: Sequence[Example], validation_rows: Sequence[Example],
              seed: int, max_epochs: int = MAX_EPOCHS,
              progress_callback: Callable[[dict[str, Any]], None] | None = None,
              checkpoint_callback: Callable[[int, dict[str, torch.Tensor]], None] | None = None) -> dict[str, Any]:
    if any(e.split != "train" for e in train_rows):
        raise ValueError("training loader received a non-train episode")
    if any(e.split != "validation" for e in validation_rows):
        raise ValueError("validation loader received a non-validation episode")
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    if not _eligible(train_rows) or not _eligible(validation_rows):
        raise ValueError("train and validation must each include eligible rows")
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE, weight_decay=0.0)
    best_state = None
    epoch_nlls: list[float] = []
    epoch_log: list[dict[str, float | int]] = []
    started = time.perf_counter()
    rows = _eligible(train_rows)
    for _epoch in range(max_epochs):
        model.train()
        permutation = np.random.permutation(len(rows)).tolist()
        train_loss_sum, train_row_count, gradient_norms = 0.0, 0, []
        for start in range(0, len(permutation), BATCH_SIZE):
            batch = [rows[i] for i in permutation[start:start + BATCH_SIZE]]
            optimizer.zero_grad(set_to_none=True)
            losses = [nn.functional.cross_entropy(model.logits(e.features).unsqueeze(0),
                                                   torch.tensor([e.gold_index])) for e in batch]
            batch_loss = torch.stack(losses).mean()
            train_loss_sum += float(batch_loss.detach()) * len(batch)
            train_row_count += len(batch)
            batch_loss.backward()
            squared_norm = sum(float(torch.sum(p.grad.detach() ** 2))
                               for p in model.parameters() if p.grad is not None)
            gradient_norms.append(math.sqrt(squared_norm))
            optimizer.step()
        val_nll = _nll(model, validation_rows)
        assert val_nll is not None
        epoch_nlls.append(val_nll)
        epoch_log.append({"epoch": _epoch + 1, "mean_train_nll": train_loss_sum / train_row_count,
                          "mean_validation_nll": val_nll,
                          "mean_preclip_gradient_norm": float(np.mean(gradient_norms))})
        if progress_callback is not None:
            progress_callback(epoch_log[-1])
        is_new_best = best_state is None or val_nll < min(epoch_nlls[:-1])
        if is_new_best:
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            if checkpoint_callback is not None:
                checkpoint_callback(_epoch + 1, best_state)
    best_epoch = select_best_checkpoint(epoch_nlls)
    model.load_state_dict(best_state)
    return {"model": model, "best_epoch": best_epoch, "validation_nll_by_epoch": epoch_nlls,
            "epoch_log": epoch_log,
            "validation_nll": epoch_nlls[best_epoch - 1], "trainable_parameters": trainable_parameter_count(model),
            "training_seconds": time.perf_counter() - started}


def ranking_metrics(model: RankingModel | None, examples: Sequence[Example]) -> dict[str, Any]:
    eligible = _eligible(examples)
    if not eligible:
        return {"n": 0, "nll": None, "top1_accuracy": None, "mrr": None, "row_losses": [], "row_ranks": []}
    losses, ranks = [], []
    for e in eligible:
        if model is None:  # uniform probabilities; stable original order resolves equal scores
            logits = torch.zeros(len(e.support), dtype=torch.float32)
        else:
            model.eval()
            with torch.no_grad():
                logits = model.logits(e.features)
        losses.append(float(nn.functional.cross_entropy(logits.unsqueeze(0), torch.tensor([e.gold_index]))))
        gold_score = float(logits[e.gold_index])
        rank = 1 + sum((float(logits[i]) > gold_score) or
                       (float(logits[i]) == gold_score and i < e.gold_index)
                       for i in range(len(e.support)) if i != e.gold_index)
        ranks.append(int(rank))
    return {"n": len(eligible), "nll": float(np.mean(losses)),
            "top1_accuracy": float(np.mean(np.asarray(ranks) == 1)),
            "mrr": float(np.mean(1 / np.asarray(ranks, dtype=np.float64))),
            "row_losses": losses, "row_ranks": ranks}


def paired_episode_bootstrap(left: Sequence[Example], right: Sequence[Example],
                             left_losses: Sequence[float], right_losses: Sequence[float],
                             replicates: int = BOOTSTRAP_REPLICATES,
                             seed: int = BOOTSTRAP_SEED) -> dict[str, Any]:
    """Episode-cluster bootstrap of paired rowwise loss differences (left-right)."""
    if not (len(left) == len(right) == len(left_losses) == len(right_losses)):
        raise ValueError("paired bootstrap inputs must align row for row")
    if any(a.trajectory_id != b.trajectory_id or a.source_row != b.source_row for a, b in zip(left, right)):
        raise ValueError("paired rows are not aligned")
    if not left:
        return {"n": 0, "episodes": 0, "mean_delta_nll": None, "ci95": None, "replicates": replicates}
    grouped: dict[str, list[float]] = {}
    for e, a, b in zip(left, left_losses, right_losses):
        grouped.setdefault(e.trajectory_id, []).append(float(a) - float(b))
    ids = sorted(grouped)
    sums = np.asarray([np.sum(grouped[i]) for i in ids], dtype=np.float64)
    counts = np.asarray([len(grouped[i]) for i in ids], dtype=np.float64)
    rng = np.random.default_rng(seed)
    draws = np.empty(replicates, dtype=np.float64)
    for j in range(replicates):
        sampled = rng.integers(0, len(sums), size=len(sums))
        draws[j] = sums[sampled].sum() / counts[sampled].sum()
    return {"n": len(left), "episodes": len(ids), "mean_delta_nll": float(np.mean([x for vs in grouped.values() for x in vs])),
            "ci95": [float(x) for x in np.quantile(draws, [0.025, 0.975])], "replicates": replicates, "seed": seed}


def read_jsonl(path: Path, *, payload: bytes | None = None) -> list[dict[str, Any]]:
    rows = []
    if payload is None:
        with path.open(encoding="utf-8") as stream:
            lines = list(stream)
    else:
        lines = payload.decode("utf-8").splitlines(keepends=True)
    for line_no, line in enumerate(lines, 1):
        if not line.strip():
            raise ValueError(f"blank JSONL line {line_no}")
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"line {line_no} must be object")
        rows.append(row)
    return rows


def verify_pinned_input(*, projected_payload: bytes | None = None,
                        source_payload: bytes | None = None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Verify the existing accepted projection and all snapshot/source pins."""
    manifest_path = CONTRACT_DIR / "manifest.json"
    if not PROJECTED_PATH.is_file() or not manifest_path.is_file():
        raise FileNotFoundError(f"pinned contract missing under {CONTRACT_DIR}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {"input_sha256": EXPECTED_INPUT_SHA256, "output_sha256": EXPECTED_PROJECTED_SHA256,
                "protocol_sha256": EXPECTED_PROTOCOL_SHA256, "code_sha256": EXPECTED_BUILDER_SHA256,
                "test_sha256": EXPECTED_TEST_SHA256, "rows": EXPECTED_ROWS}
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(f"pinned manifest {key} mismatch")
    for filename, key in (("protocol_snapshot.md", "protocol_sha256"),
                          ("project_inputs_snapshot.py", "code_sha256"),
                          ("test_project_inputs_snapshot.py", "test_sha256")):
        if sha256_file(CONTRACT_DIR / filename) != manifest[key]:
            raise ValueError(f"pinned snapshot hash mismatch: {filename}")
    payload = PROJECTED_PATH.read_bytes() if projected_payload is None else projected_payload
    if sha256_bytes(payload) != EXPECTED_PROJECTED_SHA256:
        raise ValueError("projected input artifact hash mismatch")
    rows = read_jsonl(PROJECTED_PATH, payload=payload)
    if len(rows) != EXPECTED_ROWS:
        raise ValueError(f"expected {EXPECTED_ROWS} projected rows, got {len(rows)}")
    import project_inputs
    current_pins = {"protocol": sha256_file(HERE / "README.md"),
                    "builder": sha256_file(HERE / "project_inputs.py"),
                    "builder_test": sha256_file(HERE / "test_project_inputs.py")}
    if current_pins != {"protocol": EXPECTED_PROTOCOL_SHA256, "builder": EXPECTED_BUILDER_SHA256,
                        "builder_test": EXPECTED_TEST_SHA256}:
        raise ValueError("current protocol, projection source, or projection test differs from accepted snapshot")
    if project_inputs.SOURCE.is_file() or source_payload is not None:
        actual_source_hash = (sha256_file(project_inputs.SOURCE) if source_payload is None
                              else sha256_bytes(source_payload))
        if actual_source_hash != EXPECTED_INPUT_SHA256:
            raise ValueError("pinned upstream source bytes changed")
    else:
        raise FileNotFoundError(f"pinned upstream source missing: {project_inputs.SOURCE}")
    seen: set[tuple[str, int, str]] = set()
    by_split: dict[str, list[dict[str, Any]]] = {k: [] for k in EXPECTED_SPLITS}
    keys, source_keys = [], []
    for i, row in enumerate(rows, 1):
        # Re-run exact projected-schema allowlist checks for core and diagnostic.
        project_inputs.features(row, "core", True)
        project_inputs.features(row, "diagnostic_plus_partner_raw_commands", True)
        p = row["provenance"]
        if row.get("admission", {}).get("training_authorized") is not False:
            raise ValueError(f"row {i}: training authorization must remain false")
        tid, actor = p["trajectory_id"], p["actor"]
        bucket = episode_bucket(tid)
        if p["split_bucket"] != bucket or p["split"] != split_name(bucket):
            raise ValueError(f"row {i}: frozen episode split mismatch")
        key = (tid, p["target_physical_index"], actor.casefold())
        if key in seen:
            raise ValueError(f"row {i}: duplicate cohort key")
        seen.add(key); keys.append(f"{tid}|{p['target_physical_index']}|{actor.casefold()}")
        source_keys.append(p["target_source_ref"])
        by_split[split_name(bucket)].append(row)
        core, diagnostic = row["history_views"]["core"], row["history_views"]["diagnostic_plus_partner_raw_commands"]
        refs = p.get("payload_history_turn_refs")
        target_raw = p.get("target_raw_turn_index")
        if not isinstance(refs, list) or len(refs) != len(core) or type(target_raw) is not int:
            raise ValueError(f"row {i}: history provenance alignment missing")
        prior_indices = []
        for group, ref in zip(core, refs):
            if not isinstance(ref, dict) or ref.get("role") != group["role"]:
                raise ValueError(f"row {i}: history role/provenance mismatch")
            raw_index = ref.get("raw_turn_index")
            if type(raw_index) is not int or raw_index >= target_raw:
                raise ValueError(f"row {i}: history contains non-prior raw turn")
            prior_indices.append(raw_index)
        if prior_indices != sorted(set(prior_indices)):
            raise ValueError(f"row {i}: history order is not strictly increasing")
        if len(core) != len(diagnostic):
            raise ValueError(f"row {i}: core/diagnostic history length mismatch")
        for c, d in zip(core, diagnostic):
            expected_core = dict(d)
            if d["role"] == "partner":
                expected_core["action"] = None
            if c != expected_core:
                raise ValueError(f"row {i}: core/diagnostic projection mismatch")
    digest = sha256_bytes("\n".join(sorted(keys)).encode())
    if digest != EXPECTED_COHORT_DIGEST:
        raise ValueError("cohort digest mismatch")
    source_digest = sha256_bytes("\n".join(sorted(source_keys)).encode())
    if source_digest != EXPECTED_SOURCE_KEY_DIGEST or manifest.get("source_key_digest") != EXPECTED_SOURCE_KEY_DIGEST:
        raise ValueError("source key digest mismatch")
    for name, (expected_rows, expected_episodes) in EXPECTED_SPLITS.items():
        actual = by_split[name]
        episodes = len({r["provenance"]["trajectory_id"] for r in actual})
        if len(actual) != expected_rows or episodes != expected_episodes:
            raise ValueError(f"{name} row/episode counts mismatch: {len(actual)}/{episodes}")
    if manifest.get("training_authorized") is not False:
        raise ValueError("contract authorization field changed; do not infer permission")
    if manifest.get("cohort_key_digest") != EXPECTED_COHORT_DIGEST:
        raise ValueError("manifest cohort digest mismatch")
    return rows, manifest


def split_examples(examples: Sequence[Example]) -> dict[str, list[Example]]:
    return {name: [e for e in examples if e.split == name]
            for name in ("train", "validation", "excluded_bucket9")}


def dataset_report(examples: Sequence[Example]) -> dict[str, Any]:
    report = {}
    for split in ("train", "validation", "excluded_bucket9"):
        rows = [e for e in examples if e.split == split]
        channel_counts: dict[str, dict[str, dict[str, Any]]] = {}
        for view in ("core", "diagnostic_plus_partner_raw_commands"):
            channel_counts[view] = {}
            for role in ("self", "partner"):
                channel_counts[view][role] = {}
                for channel in ("speech", "action", "emote"):
                    present = nulls = 0
                    unique: set[str] = set()
                    refs_complete = all(e.history_refs_complete for e in rows)
                    for e in rows:
                        detail = (e.history_channel_counts or {}).get(view, {}).get(role, {}).get(channel, {})
                        present += int(detail.get("present", 0)); nulls += int(detail.get("null", 0))
                        unique.update(f"{ref}|{channel}" for ref in detail.get("refs", []) if ref)
                    channel_counts[view][role][channel] = {
                        "present_event_occurrences_in_prefixes": present,
                        "null_event_occurrences_in_prefixes": nulls,
                        "unique_event_ids": len(unique) if refs_complete else None,
                        "unique_event_ids_unavailable_reason": None if refs_complete else "history refs are missing or incomplete"}
        report[split] = {"source_rows": len(rows), "episodes": len({e.trajectory_id for e in rows}),
                         "actor_trajectories": len({(e.trajectory_id, e.actor) for e in rows}),
                         "eligibility": {k: sum(e.eligibility == k for e in rows) for k in
                                         ("unique", "ambiguous_target", "absent_target", "missing_target", "bad_support")},
                         "scoreable_unique_targets": sum(e.eligibility == "unique" for e in rows),
                         "scored_rows": sum(e.eligibility == "unique" for e in rows) if split != "excluded_bucket9" else 0,
                         "history_depth": {str(d): sum(len(e.features["history"]) == d for e in rows)
                                            for d in sorted({len(e.features["history"]) for e in rows})},
                         "history_channel_occurrences_and_unique_refs": channel_counts}
    return report


def _stratum(depth: int) -> str:
    return "1-4" if 1 <= depth <= 4 else "5-8" if 5 <= depth <= 8 else ">=9" if depth >= 9 else "depth_0"


def prediction_records(model: RankingModel | None, examples: Sequence[Example]) -> list[dict[str, Any]]:
    """Raw keyed development predictions; provenance stays beside, never in, tensors."""
    records = []
    for e in _eligible(examples):
        started = time.perf_counter()
        if model is None:
            logits = torch.zeros(len(e.support), dtype=torch.float32)
        else:
            model.eval()
            with torch.no_grad():
                logits = model.logits(e.features)
        elapsed = time.perf_counter() - started
        probs = torch.softmax(logits, dim=0).cpu().tolist()
        order = sorted(range(len(e.support)), key=lambda i: (-float(logits[i]), i))
        nll = float(nn.functional.cross_entropy(logits.unsqueeze(0), torch.tensor([e.gold_index])))
        records.append({"source_row": e.source_row, "trajectory_id": e.trajectory_id,
                        "actor": e.actor, "split": e.split, "prior_group_depth": int(e.features["history"].shape[0]),
                        "gold_candidate_index": e.gold_index, "candidate_count": len(e.support),
                        "probabilities_in_source_order": probs,
                        "gold_rank": order.index(e.gold_index) + 1,
                        "nll": nll,
                        "inference_seconds": elapsed})
    return records


def _jsonl_write_exclusive(path: Path, records: Iterable[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8") as f:
        for row in records:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def _torch_save_exclusive(path: Path, payload: Any) -> None:
    with path.open("xb") as f:
        torch.save(payload, f)
        f.flush()
        os.fsync(f.fileno())


def run_experiment(examples_by_condition: dict[str, list[Example]] | None, out: Path, *,
                   run_kind: str, input_manifest: dict[str, Any] | None = None,
                   seeds: Sequence[int] = SEEDS, max_epochs: int = MAX_EPOCHS,
                   bootstrap_replicates: int = BOOTSTRAP_REPLICATES,
                   input_snapshot: bytes | None = None,
                   execution_admission_snapshot: bytes | None = None,
                   projected_input_snapshot: bytes | None = None,
                   source_input_snapshot: bytes | None = None) -> dict[str, Any]:
    """Complete run/evidence pipeline shared by synthetic and future admitted runs."""
    out = validate_new_output_path(out)
    execution_record = None
    source_snapshots: dict[str, bytes] = {}
    if run_kind == "SYNTHETIC_CONTRACT_ONLY":
        if input_snapshot is None or any(x is not None for x in
                                          (execution_admission_snapshot, projected_input_snapshot, source_input_snapshot)):
            raise ValueError("synthetic runs require only a synthetic input snapshot")
    elif run_kind == "SOURCE_CONDITIONAL_DEVELOPMENT":
        if DEFAULT_RUN_ROOT.resolve() not in out.resolve().parents:
            raise ValueError("development run output must be a new child of the fixed trainer run root")
        if (execution_admission_snapshot is None or projected_input_snapshot is None or
                source_input_snapshot is None or input_snapshot is not None):
            raise PermissionError("development run requires captured admission, projected, and source bytes")
        from fit_source import verify_execution_admission_bytes
        execution_record = verify_execution_admission_bytes(execution_admission_snapshot)
        pins = execution_record["pins"]
        pinned_names = set(pins["source_sha256"])
        required_snapshot_names = {"README.md", "INPUT_REVIEW.md", "project_inputs.py", "test_project_inputs.py"}
        for name in sorted(pinned_names | required_snapshot_names):
            source = HERE / name
            if not source.is_file():
                raise FileNotFoundError(f"execution-pinned source disappeared: {source}")
            source_snapshots[name] = source.read_bytes()
        if not set(pins["source_sha256"]).issubset(source_snapshots):
            raise ValueError("an execution-pinned source snapshot is missing")
        captured_pins = {name: sha256_bytes(source_snapshots[name]) for name in pins["source_sha256"]}
        if captured_pins != pins["source_sha256"]:
            raise ValueError("captured execution source bytes differ from the accepted admission pins")
        if (sha256_bytes(source_snapshots["README.md"]) != EXPECTED_PROTOCOL_SHA256 or
                sha256_bytes(source_snapshots["project_inputs.py"]) != EXPECTED_BUILDER_SHA256 or
                sha256_bytes(source_snapshots["test_project_inputs.py"]) != EXPECTED_TEST_SHA256):
            raise ValueError("captured protocol/builder/projection-test snapshots differ from frozen pins")
        if (sha256_bytes(projected_input_snapshot) != pins["projected_sha256"] or
                sha256_bytes(source_input_snapshot) != pins["input_sha256"]):
            raise ValueError("captured source/projected bytes do not match the accepted execution pins")
        if (tuple(seeds) != SEEDS or max_epochs != MAX_EPOCHS or
                bootstrap_replicates != BOOTSTRAP_REPLICATES or pins["config"] != frozen_training_config() or
                pins["conditions"] != list(CONDITIONS) or pins["seeds"] != list(SEEDS)):
            raise ValueError("development run settings differ from frozen execution configuration")
        # The admitted path always regenerates tensors from the exact bound
        # bytes. Caller-supplied Example objects are never accepted for real runs.
        real_rows, verified_manifest = verify_pinned_input(projected_payload=projected_input_snapshot,
                                                            source_payload=source_input_snapshot)
        if input_manifest is not None and input_manifest != verified_manifest:
            raise ValueError("provided projection manifest is not the verified manifest for captured bytes")
        if (verified_manifest.get("training_authorized") is not False or
                verified_manifest.get("output_sha256") != pins["projected_sha256"] or
                verified_manifest.get("input_sha256") != pins["input_sha256"]):
            raise ValueError("projection admission evidence does not match execution pins")
        input_manifest = verified_manifest
        examples_by_condition = build_examples(real_rows)
    else:
        raise PermissionError("unknown run kind; no authorization fallback is available")
    if examples_by_condition is None or set(examples_by_condition) != set(CONDITIONS):
        raise ValueError("experiment must contain exactly the nine frozen conditions")
    reference = examples_by_condition["gru_core"]
    signature = lambda e: (e.source_row, e.trajectory_id, e.actor, e.bucket, e.support,
                           e.gold_index, e.eligibility, int(e.features["history"].shape[0]))
    expected_signature = [signature(e) for e in reference]
    for condition in CONDITIONS:
        if [signature(e) for e in examples_by_condition[condition]] != expected_signature:
            raise ValueError(f"condition row cohort differs from gru_core: {condition}")
    # These synthetic snapshots do not authorize or load source data. Real-run
    # snapshots were captured and hash-checked before any input parsing/features.
    if execution_record is None:
        for name in ("train.py", "README.md", "INPUT_REVIEW.md", "project_inputs.py", "test_project_inputs.py", "test_train.py"):
            source = HERE / name
            if source.is_file():
                source_snapshots[name] = source.read_bytes()
    if run_kind == "SYNTHETIC_CONTRACT_ONLY" and input_snapshot is None:
        raise ValueError("synthetic run requires serialized input bytes for provenance")
    out.mkdir(parents=True, exist_ok=False)
    snapshot_dir = out / "snapshots"
    snapshot_dir.mkdir(exist_ok=False)
    snapshot_hashes = {}
    for name, payload in source_snapshots.items():
        with (snapshot_dir / name).open("xb") as f:
            f.write(payload)
        snapshot_hashes[name] = sha256_bytes(payload)
    if run_kind == "SYNTHETIC_CONTRACT_ONLY":
        with (snapshot_dir / "synthetic_input.jsonl").open("xb") as f:
            f.write(input_snapshot)
        snapshot_hashes["synthetic_input.jsonl"] = sha256_bytes(input_snapshot)
    else:
        for filename, content in (("projected_input.jsonl", projected_input_snapshot),
                                  ("source_input.jsonl", source_input_snapshot),
                                  ("execution_admission.json", execution_admission_snapshot)):
            with (snapshot_dir / filename).open("xb") as f:
                f.write(content)
            snapshot_hashes[filename] = sha256_bytes(content)
    progress_stream = (out / "progress.jsonl").open("x", encoding="utf-8")
    def progress(event: str, **fields: Any) -> None:
        progress_stream.write(json.dumps({"time_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                          "event": event, **fields}, ensure_ascii=False,
                                         sort_keys=True, separators=(",", ":")) + "\n")
        progress_stream.flush()
        os.fsync(progress_stream.fileno())
    progress("run_started", run_kind=run_kind, run_root=str(out),
             training_authorized=run_kind == "SOURCE_CONDITIONAL_DEVELOPMENT")
    started = time.perf_counter()
    report: dict[str, Any] = {"schema": "light_source_ranking_trainer_run_v1", "run_kind": run_kind,
                              "training_authorized": execution_record is not None,
                              "projection_training_authorized": False,
                              "execution_training_authorized": execution_record is not None,
                              "research_evidence": (False if execution_record is None else "SOURCE_CONDITIONAL_DEVELOPMENT"),
                              "real_source_loaded": execution_record is not None,
                              "claims": ("Synthetic contract run only; no source data or research evidence."
                                         if execution_record is None else
                                         "Development ranking evidence only; no actor-visible, runtime-policy, formal-test, or psychological-validity admission."),
                              "admissions": {"projection_training_authorized": False,
                                             "execution_training_authorized": execution_record is not None,
                                             "actor_forecast": False, "runtime_policy": False,
                                             "formal_test": False, "psychological_validity": False,
                                             "authorization_basis": (execution_record.get("authorization_basis")
                                                                      if execution_record else None)},
                              "dataset": dataset_report(examples_by_condition["gru_core"]),
                              "conditions": {}, "paired_comparisons": {}, "strata": {},
                              "excluded_bucket9": {"trained": False, "scored": False, "metrics": None}}
    predictions_by_condition: dict[str, dict[int, dict[str, dict[int, dict[str, Any]]]]] = {}
    per_condition_cost: dict[str, Any] = {}
    for condition in CONDITIONS:
        condition_examples = examples_by_condition[condition]
        runs = []
        predictions_by_condition[condition] = {}
        for seed in seeds:
            callback = lambda record, c=condition, s=int(seed): progress("epoch_complete", condition=c, seed=s, **record)
            progress_checkpoints: list[str] = []
            def save_progress_checkpoint(epoch: int, state: dict[str, torch.Tensor],
                                         c: str = condition, s: int = int(seed)) -> None:
                name = f"checkpoint_progress_{c}_seed{s}_epoch{epoch}.pt"
                _torch_save_exclusive(out / name, {"condition": c, "seed": s, "epoch": epoch,
                                                   "state_dict": state, "run_kind": run_kind,
                                                   "selected_as_of_epoch": True})
                progress_checkpoints.append(name)
                progress("best_checkpoint_progress_saved", condition=c, seed=s, epoch=epoch,
                         checkpoint=name)
            fitted = fit_condition(condition_examples, condition, int(seed), max_epochs=max_epochs,
                                   progress_callback=callback,
                                   checkpoint_callback=(save_progress_checkpoint if execution_record else None))
            model = fitted["model"]
            per_split = {}
            pred_for_seed: dict[str, dict[int, dict[str, Any]]] = {}
            condition_records = []
            for split in ("train", "validation"):
                subset = [e for e in condition_examples if e.split == split]
                metrics = ranking_metrics(model, subset)
                per_split[split] = {k: v for k, v in metrics.items() if k not in ("row_losses", "row_ranks")}
                records = prediction_records(model, subset)
                condition_records.extend(records)
                pred_for_seed[split] = {r["source_row"]: r for r in records}
            predictions_by_condition[condition][int(seed)] = pred_for_seed
            pred_file = f"predictions_{condition}_seed{seed}.jsonl"
            _jsonl_write_exclusive(out / pred_file, condition_records)
            checkpoint_file = None
            reload_nll = None
            if model is not None:
                checkpoint_file = f"checkpoint_{condition}_seed{seed}.pt"
                ckpt_path = out / checkpoint_file
                _torch_save_exclusive(ckpt_path,
                                      {"condition": condition, "seed": int(seed), "best_epoch": fitted["best_epoch"],
                                       "state_dict": {k: v.detach().cpu().clone() for k, v in model.state_dict().items()},
                                       "run_kind": run_kind})
                progress("checkpoint_written", condition=condition, seed=int(seed), epoch=fitted["best_epoch"],
                         checkpoint=checkpoint_file, bytes=ckpt_path.stat().st_size)
                fresh = RankingModel(condition)
                data = torch.load(ckpt_path, map_location="cpu", weights_only=True)
                fresh.load_state_dict(data["state_dict"], strict=True)
                reload_nll = _nll(fresh, [e for e in condition_examples if e.split == "validation"])
                if not math.isclose(float(reload_nll), float(fitted["validation_nll"]), rel_tol=0, abs_tol=1e-7):
                    raise RuntimeError(f"checkpoint reload prediction mismatch for {condition}/seed{seed}")
                for e in [x for x in condition_examples if x.split == "validation" and x.eligibility == "unique"]:
                    with torch.no_grad():
                        before_logits = fitted["model"].logits(e.features)
                        after_logits = fresh.logits(e.features)
                        before = torch.softmax(before_logits, dim=0)
                        after = torch.softmax(after_logits, dim=0)
                    if not torch.equal(before_logits, after_logits) or not torch.equal(before, after):
                        raise RuntimeError(f"checkpoint reload probabilities differ for {condition}/seed{seed}/row{e.source_row}")
                model = fresh
            run = {"seed": int(seed), "best_epoch": fitted["best_epoch"],
                   "validation_nll_by_epoch": fitted["validation_nll_by_epoch"],
                   "epoch_log": fitted.get("epoch_log", []),
                   "selected_validation_nll": fitted["validation_nll"], "fresh_reload_validation_nll": reload_nll,
                   "trainable_parameters": fitted["trainable_parameters"],
                   "training_seconds": fitted["training_seconds"], "metrics": per_split,
                   "progress_checkpoint_files": progress_checkpoints,
                   "prediction_file": pred_file, "checkpoint_file": checkpoint_file}
            runs.append(run)
            progress("condition_seed_complete", condition=condition, seed=int(seed),
                     best_epoch=fitted["best_epoch"], selected_validation_nll=fitted["validation_nll"])
        report["conditions"][condition] = runs
        records_all = [r for seed in seeds for split in ("train", "validation")
                       for r in predictions_by_condition[condition][int(seed)][split].values()]
        per_condition_cost[condition] = {"prediction_count": len(records_all),
                                         "total_inference_seconds": sum(r["inference_seconds"] for r in records_all),
                                         "mean_inference_seconds_per_row": (float(np.mean([r["inference_seconds"] for r in records_all]))
                                                                            if records_all else None),
                                         "checkpoint_bytes": sum(p.stat().st_size for p in out.glob(f"checkpoint*_{condition}_seed*.pt"))}
    report["cost"] = {"by_condition": per_condition_cost,
                       "total_wall_seconds": time.perf_counter() - started,
                       "process_peak_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss *
                                                     (1024 if sys.platform != "darwin" else 1)),
                       "python": sys.version, "platform": platform.platform(), "numpy": np.__version__,
                       "torch": torch.__version__, "device": "cpu", "torch_threads": torch.get_num_threads(),
                       "deterministic_algorithms": torch.are_deterministic_algorithms_enabled()}
    # Seed-averaged row losses first, then episode-cluster bootstrap on paired rows.
    comparison_pairs = {"gru_core_vs_context_only": ("gru_core", "context_only"),
                        "gru_core_vs_pooled_core": ("gru_core", "pooled_core")}
    for label, (left_name, right_name) in comparison_pairs.items():
        all_seed_rows = [e for e in examples_by_condition[left_name]
                         if e.split in ("train", "validation") and e.eligibility == "unique"]
        # Primary reported inference is validation development only.
        val_rows = [e for e in all_seed_rows if e.split == "validation"]
        left_by_row, right_by_row = {}, {}
        for e in val_rows:
            lvals = [predictions_by_condition[left_name][int(seed)]["validation"][e.source_row]["nll"] for seed in seeds]
            rvals = [predictions_by_condition[right_name][int(seed)]["validation"][e.source_row]["nll"] for seed in seeds]
            left_by_row[e.source_row] = float(np.mean(lvals)); right_by_row[e.source_row] = float(np.mean(rvals))
        paired = paired_episode_bootstrap(val_rows, val_rows,
                                          [left_by_row[e.source_row] for e in val_rows],
                                          [right_by_row[e.source_row] for e in val_rows],
                                          replicates=bootstrap_replicates)
        per_seed = {}
        for seed in seeds:
            l = predictions_by_condition[left_name][int(seed)]["validation"]
            r = predictions_by_condition[right_name][int(seed)]["validation"]
            per_seed[str(seed)] = (float(np.mean([l[e.source_row]["nll"] - r[e.source_row]["nll"] for e in val_rows]))
                                   if val_rows else None)
        report["paired_comparisons"][label] = {**paired, "left": left_name, "right": right_name,
                                                "per_seed_delta_nll": per_seed,
                                                "interpretation": "development interval after validation checkpoint selection"}
    for split in ("train", "validation"):
        rows = [e for e in examples_by_condition["gru_core"] if e.split == split and e.eligibility == "unique"]
        for band in ("1-4", "5-8", ">=9"):
            subset = [e for e in rows if _stratum(len(e.features["history"])) == band]
            report["strata"][f"{split}:{band}"] = {"rows": len(subset),
                "episodes": len({e.trajectory_id for e in subset}), "unstable_sparse": len(subset) < 20,
                "prior_group_depth_not_physical_history": band, "per_condition_seed_average": {}}
            for condition in ("context_only", "last2_core", "pooled_core", "gru_core", "gru_no_context",
                              "gru_no_dialogue", "gru_no_persona", "gru_plus_partner_raw_commands", "uniform"):
                seed_nlls = []
                for seed in seeds:
                    pred = predictions_by_condition[condition][int(seed)][split]
                    seed_nlls.extend(pred[e.source_row]["nll"] for e in subset if e.source_row in pred)
                report["strata"][f"{split}:{band}"]["per_condition_seed_average"][condition] = (
                    float(np.mean(seed_nlls)) if seed_nlls else None)
            report["strata"][f"{split}:{band}"]["paired_primary_comparisons"] = {}
            for label, (left_name, right_name) in comparison_pairs.items():
                left_loss, right_loss = [], []
                per_seed_delta = {}
                for e in subset:
                    lvals = [predictions_by_condition[left_name][int(seed)][split][e.source_row]["nll"]
                             for seed in seeds]
                    rvals = [predictions_by_condition[right_name][int(seed)][split][e.source_row]["nll"]
                             for seed in seeds]
                    left_loss.append(float(np.mean(lvals)))
                    right_loss.append(float(np.mean(rvals)))
                for seed in seeds:
                    lp = predictions_by_condition[left_name][int(seed)][split]
                    rp = predictions_by_condition[right_name][int(seed)][split]
                    diffs = [lp[e.source_row]["nll"] - rp[e.source_row]["nll"] for e in subset
                             if e.source_row in lp and e.source_row in rp]
                    per_seed_delta[str(seed)] = float(np.mean(diffs)) if diffs else None
                interval = paired_episode_bootstrap(subset, subset,
                                                    left_loss, right_loss,
                                                    replicates=bootstrap_replicates)
                report["strata"][f"{split}:{band}"]["paired_primary_comparisons"][label] = {
                    **interval, "per_seed_delta_nll": per_seed_delta,
                    "interpretation": "post-selection development interval"}
        report["strata"][f"{split}:depth_0_unstratified"] = {
            "rows": sum(_stratum(len(e.features["history"])) == "depth_0" for e in rows),
            "reason": "outside predeclared prior-group-depth strata"}
    config = {**frozen_training_config(), "max_epochs": max_epochs,
              "bootstrap_replicates": bootstrap_replicates,
              "conditions": list(CONDITIONS), "seeds": list(seeds),
              "split": "whole-episode SHA256 bucket; 0-6 train, 7-8 validation, 9 excluded"}
    snapshots = {"trainer_source_sha256": snapshot_hashes.get("train.py"),
                 "protocol_sha256": snapshot_hashes.get("README.md"),
                 "input_review_sha256": snapshot_hashes.get("INPUT_REVIEW.md"),
                 "project_inputs_source_sha256": snapshot_hashes.get("project_inputs.py"),
                 "test_source_sha256": snapshot_hashes.get("test_project_inputs.py"),
                 "trainer_test_source_sha256": snapshot_hashes.get("test_train.py"),
                 "execution_runner_sha256": snapshot_hashes.get("fit_source.py"),
                 "execution_guard_test_sha256": snapshot_hashes.get("test_execution_admission.py")}
    if "synthetic_input.jsonl" in snapshot_hashes:
        snapshots["synthetic_input_sha256"] = snapshot_hashes["synthetic_input.jsonl"]
    else:
        snapshots.update({"projected_input_sha256": snapshot_hashes["projected_input.jsonl"],
                          "source_input_sha256": snapshot_hashes["source_input.jsonl"],
                          "execution_admission_sha256": snapshot_hashes["execution_admission.json"]})
    manifest = {"schema": "light_source_ranking_run_provenance_v1", "run_kind": run_kind,
                "training_authorized": execution_record is not None,
                "projection_training_authorized": False,
                "execution_training_authorized": execution_record is not None,
                "actor_forecast": False, "runtime_policy": False, "formal_test": False,
                "psychological_validity": False, "execution_admission": execution_record,
                "input_contract_manifest": input_manifest, "snapshots": snapshots, "config": config,
                "dataset_report_sha256": sha256_bytes(canonical_json(report["dataset"]).encode()),
                "created_by": "train.py", "output_scope": str(out),
                "output_hash_scope_excludes": ["provenance.json"]}
    if execution_record is None:
        with (out / "SYNTHETIC_ONLY.txt").open("x", encoding="utf-8") as f:
            f.write("Synthetic contract exercise only. Not source data or research evidence.\n")
    else:
        with (out / "DEVELOPMENT_ONLY.txt").open("x", encoding="utf-8") as f:
            f.write("Source-conditional DEVELOPMENT ranking only; no actor-visible, runtime-policy, formal-test, or psychological-validity admission.\n")
    progress("analysis_complete", condition_count=len(CONDITIONS), seed_count=len(seeds))
    progress_stream.close()
    report["cost"]["total_wall_seconds"] = time.perf_counter() - started
    _atomic_json(out / "report.json", report)
    if execution_record is None:
        _atomic_json(out / "synthetic_report.json", report)
    output_hashes = {p.relative_to(out).as_posix(): sha256_file(p) for p in out.rglob("*") if p.is_file()}
    manifest["output_files_sha256"] = output_hashes
    _atomic_json(out / "provenance.json", manifest)
    return report


def _seed_everything(seed: int) -> None:
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)


def fit_condition(examples: Sequence[Example], condition: str, seed: int,
                  max_epochs: int = MAX_EPOCHS,
                  progress_callback: Callable[[dict[str, Any]], None] | None = None,
                  checkpoint_callback: Callable[[int, dict[str, torch.Tensor]], None] | None = None) -> dict[str, Any]:
    parts = split_examples(examples)
    train_rows = _eligible(parts["train"])
    val_rows = _eligible(parts["validation"])
    if condition == "uniform":
        return {"model": None, "best_epoch": None, "validation_nll_by_epoch": [],
                "validation_nll": ranking_metrics(None, val_rows)["nll"], "trainable_parameters": 0,
                "training_seconds": 0.0, "seed": seed}
    _seed_everything(seed)
    model = RankingModel(condition)
    result = train_one(model, train_rows, val_rows, seed, max_epochs=max_epochs,
                       progress_callback=progress_callback, checkpoint_callback=checkpoint_callback)
    result["seed"] = seed
    return result


def _atomic_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, sort_keys=True, indent=2)
        f.write("\n")


def write_synthetic_run(out: Path) -> dict[str, Any]:
    """Run a tiny deterministic synthetic contract exercise, never source data."""
    out = out.absolute()
    rows = []
    # Force episodes into train/validation by finding deterministic IDs in desired buckets.
    ids: dict[str, list[str]] = {"train": [], "validation": []}
    i = 0
    while min(map(len, ids.values())) < 4:
        tid = f"synthetic-episode-{i}"
        name = split_name(episode_bucket(tid))
        if name in ids and len(ids[name]) < 4:
            ids[name].append(tid)
        i += 1
    for split, tids in ids.items():
        for j, tid in enumerate(tids):
            rows.append({"schema": "light_source_ranking_input_contract_v1",
                         "static_condition": {"self_persona": "a patient shopkeeper", "recorded_environment_snapshot": f"room {j}"},
                         "history_views": {"core": [{"role": "self", "speech": "hello", "action": None, "emote": None}],
                                           "diagnostic_plus_partner_raw_commands": [{"role": "self", "speech": "hello", "action": None, "emote": None}]},
                         "candidate_surface": {"recorded_support": ["say hello", "wave"]},
                         "supervision": {"recorded_action": "say hello"},
                         "provenance": {"trajectory_id": tid, "actor": f"actor-{j}", "split_bucket": episode_bucket(tid),
                                        "split": split_name(episode_bucket(tid)), "target_physical_index": j, "target_source_ref": f"synthetic:{tid}:{j}"},
                         "admission": {"training_authorized": False}})
    examples_by_condition = build_examples(rows)
    serialized = b"".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")).encode() + b"\n" for row in rows)
    return run_experiment(examples_by_condition, out, run_kind="SYNTHETIC_CONTRACT_ONLY",
                          seeds=SEEDS, max_epochs=MAX_EPOCHS,
                          bootstrap_replicates=BOOTSTRAP_REPLICATES, input_snapshot=serialized)


def run_real_data_fail_closed() -> None:
    rows, manifest = verify_pinned_input()
    if manifest.get("training_authorized") is not True:
        raise PermissionError("real-data fitting is disabled: pinned contract training_authorized=false; no CLI override exists")
    # This branch is deliberately unreachable for the frozen artifact until its
    # governing authorization and protocol are changed and independently admitted.
    raise PermissionError("real-data fitting requires a newly authorized contract and implementation review")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--synthetic", action="store_true", help="run generated synthetic contract data only")
    parser.add_argument("--out", type=Path, default=None, help="new output directory under outputs/")
    args = parser.parse_args(argv)
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    if args.synthetic:
        if args.out is None:
            parser.error("--synthetic requires an explicit new --out directory")
        report = write_synthetic_run(args.out)
        print(json.dumps({"run_kind": report["run_kind"], "output": str(args.out.absolute())}, ensure_ascii=False))
        return 0
    if args.out is not None:
        parser.error("--out is available only with --synthetic; real training has no output/bypass switch")
    run_real_data_fail_closed()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
