#!/usr/bin/env python3
"""Explicit execution gate for the source-conditional DEVELOPMENT comparison.

The parent-owned admission record is external to this implementation. This
runner cannot create or grant it, and the default train.py entry remains
fail-closed. No CLI option can select another record or change the frozen run.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import train

HERE = Path(__file__).resolve().parent
ROOT = train.ROOT
ADMISSION_PATH = ROOT / "outputs/light_source_ranking_v1_20261006/execution_admission_v1/EXECUTION_ADMISSION.json"
RUN_ROOT = ROOT / "outputs/light_source_ranking_v1_20261006/trainer_runs"
ADMISSION_SCHEMA = "light_source_ranking_execution_admission_v1"
ADMISSION_SCOPE = "SOURCE_CONDITIONAL_DEVELOPMENT"
AUTHORIZATION_BASIS = (
    "Parent implementation review under the user-authorized DEVELOPMENT goal; "
    "this does not admit actor-visible or psychological validity."
)
RECORD_KEYS = {"schema", "scope", "training_authorized", "actor_forecast", "runtime_policy",
               "formal_test", "psychological_validity", "authorization_basis",
               "parent_implementation_review", "pins"}


def build_execution_pins() -> dict[str, Any]:
    """Build immutable expected pins from the reviewed source and frozen spec."""
    source_files = ("train.py", "test_train.py", "fit_source.py", "test_execution_admission.py")
    hashes = {}
    for name in source_files:
        path = HERE / name
        if not path.is_file():
            raise FileNotFoundError(f"required reviewed source/test missing: {path}")
        hashes[name] = train.sha256_file(path)
    return {
        "input_sha256": train.EXPECTED_INPUT_SHA256,
        "projected_sha256": train.EXPECTED_PROJECTED_SHA256,
        "protocol_sha256": train.EXPECTED_PROTOCOL_SHA256,
        "builder_sha256": train.EXPECTED_BUILDER_SHA256,
        "cohort_key_digest": train.EXPECTED_COHORT_DIGEST,
        "source_key_digest": train.EXPECTED_SOURCE_KEY_DIGEST,
        "row_count": train.EXPECTED_ROWS,
        "split_counts": {name: {"rows": counts[0], "episodes": counts[1]}
                          for name, counts in train.EXPECTED_SPLITS.items()},
        "split_rule": "bucket=int(SHA256(trajectory_id UTF-8).hexdigest()[:8],16)%10; 0-6=train; 7-8=validation; 9=excluded",
        "conditions": list(train.CONDITIONS),
        "seeds": list(train.SEEDS),
        "dimensions": dict(train.DIMENSIONS),
        "config": train.frozen_training_config(),
        "source_sha256": hashes,
    }


def verify_execution_admission_bytes(raw_bytes: bytes,
                                    expected_pins: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate record structure and exact pins; expected_pins exists for tests only."""
    try:
        record = json.loads(raw_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("execution admission must be valid UTF-8 JSON") from exc
    if not isinstance(record, dict) or set(record) != RECORD_KEYS:
        raise ValueError("execution admission keys/schema mismatch")
    fixed = {
        "schema": ADMISSION_SCHEMA,
        "scope": ADMISSION_SCOPE,
        "training_authorized": True,
        "actor_forecast": False,
        "runtime_policy": False,
        "formal_test": False,
        "psychological_validity": False,
        "authorization_basis": AUTHORIZATION_BASIS,
        "parent_implementation_review": True,
    }
    for key, value in fixed.items():
        if type(record.get(key)) is not type(value) or record.get(key) != value:
            raise PermissionError(f"execution admission {key} does not match its required value")
    pins = build_execution_pins() if expected_pins is None else expected_pins
    if not isinstance(record.get("pins"), dict) or record["pins"] != pins:
        raise PermissionError("execution admission pins differ from current source/data/protocol/config")
    return record


def read_execution_admission() -> tuple[dict[str, Any], bytes]:
    """Read only the single parent-owned gate path and retain its exact bytes."""
    current = ADMISSION_PATH
    while current != ROOT:
        if current.is_symlink():
            raise PermissionError(f"execution admission path may not traverse a symlink: {current}")
        current = current.parent
    raw = ADMISSION_PATH.read_bytes()
    record = verify_execution_admission_bytes(raw)
    return record, raw


def run_admitted_execution(out: Path | None = None) -> dict[str, Any]:
    """Validate the sole gate and frozen inputs, then start one exclusive run."""
    record, admission_bytes = read_execution_admission()
    if out is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = RUN_ROOT / f"source_conditional_dev_{stamp}"
    out = train.validate_new_output_path(Path(out))
    if RUN_ROOT.resolve() not in out.resolve().parents:
        raise ValueError("development run output must be a new child of the fixed trainer run root")

    # Read each bound input once; parse and later snapshot these same bytes.
    import project_inputs
    source_bytes = project_inputs.SOURCE.read_bytes()
    projected_bytes = train.PROJECTED_PATH.read_bytes()
    if train.sha256_bytes(source_bytes) != record["pins"]["input_sha256"]:
        raise ValueError("upstream source bytes changed after execution admission validation")
    if train.sha256_bytes(projected_bytes) != record["pins"]["projected_sha256"]:
        raise ValueError("projected input bytes changed after execution admission validation")
    # Reject paths and data before feature extraction or any artifact creation.
    train.validate_new_output_path(out)
    return train.run_experiment(
        None, out,
        run_kind=ADMISSION_SCOPE,
        seeds=train.SEEDS,
        max_epochs=train.MAX_EPOCHS,
        bootstrap_replicates=train.BOOTSTRAP_REPLICATES,
        execution_admission_snapshot=admission_bytes,
        projected_input_snapshot=projected_bytes,
        source_input_snapshot=source_bytes,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=None,
                        help="optional new run directory under outputs/; never reused")
    args = parser.parse_args(argv)
    import torch
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    report = run_admitted_execution(args.out)
    print(json.dumps({"run_kind": report["run_kind"], "real_source_loaded": report["real_source_loaded"],
                      "output": str(args.out.absolute()) if args.out else "default run root"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
