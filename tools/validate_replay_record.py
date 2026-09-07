"""Small stdlib-only validator for ReplayRecord v0 JSON and JSONL files."""
from __future__ import annotations
import argparse, json, sys
from pathlib import Path

PROVENANCE = {"observed", "annotated", "llm_inferred", "synthetic_diagnostic", "unknown"}

def validate(record: dict, source: str = "record") -> list[str]:
    errors: list[str] = []
    for key in ("trajectory_id", "source_dataset", "split_id", "steps"):
        if key not in record:
            errors.append(f"{source}: missing top-level field {key}")
    if not isinstance(record.get("steps"), list):
        errors.append(f"{source}: steps must be a list")
        return errors
    for i, step in enumerate(record["steps"]):
        if not isinstance(step, dict):
            errors.append(f"{source}: steps[{i}] must be an object")
            continue
        for key in ("t", "source_action_A_star", "provenance"):
            if key not in step:
                errors.append(f"{source}: steps[{i}] missing {key}")
        p = step.get("provenance")
        if p not in PROVENANCE:
            errors.append(f"{source}: steps[{i}] invalid provenance {p!r}")
        field_provenance = step.get("field_provenance", {})
        if not isinstance(field_provenance, dict):
            errors.append(f"{source}: steps[{i}] field_provenance must be an object")
        else:
            for field, detail in field_provenance.items():
                if not isinstance(detail, dict) or detail.get("kind") not in PROVENANCE:
                    errors.append(f"{source}: steps[{i}] invalid field provenance for {field!r}")
            action_detail = field_provenance.get("source_action_A_star", {})
            if isinstance(action_detail, dict) and action_detail.get("kind") == "llm_inferred" and any(
                step.get(k) is True for k in ("action_is_ground_truth", "source_action_is_ground_truth", "human_ground_truth")
            ):
                errors.append(f"{source}: steps[{i}] LLM-inferred action cannot be human ground truth")
        if p == "llm_inferred" and any(step.get(k) is True for k in ("action_is_ground_truth", "source_action_is_ground_truth", "human_ground_truth")):
            errors.append(f"{source}: steps[{i}] LLM-inferred action cannot be human ground truth")
    return errors

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    args = ap.parse_args()
    try:
        text = args.path.read_text(encoding="utf-8")
        try:
            data = json.loads(text)
            records = data if isinstance(data, list) else [data]
        except json.JSONDecodeError:
            records = [json.loads(line) for line in text.splitlines() if line.strip()]
            data = records
    except Exception as exc:
        print(f"FAIL {args.path}: cannot read JSON/JSONL: {exc}")
        return 1
    errors: list[str] = []
    for i, rec in enumerate(records):
        if not isinstance(rec, dict):
            errors.append(f"{args.path}[{i}]: record must be an object")
            continue
        errors.extend(validate(rec, f"{args.path}[{i}]") )
    if not isinstance(data, (dict, list)):
        errors.append(f"{args.path}: root must be an object, list, or JSONL")
    if errors:
        print("\n".join(f"FAIL {e}" for e in errors)); return 1
    print(f"OK {args.path}: {len(records)} ReplayRecord(s)"); return 0

if __name__ == "__main__":
    sys.exit(main())
