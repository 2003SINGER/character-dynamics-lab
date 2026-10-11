"""Execute the small predeclared M1 case matrix against the current local P5 service."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import secrets
from typing import Any

from .runner import RUNS_DIR, run_case, run_stale_edit_negative


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SUITE = Path(__file__).resolve().parent / "cases/suite.json"


def load_suite(path: Path = DEFAULT_SUITE) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    suite = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(suite, dict) or suite.get("schema") != "system-baseline-p5-cases-v1":
        raise ValueError("unknown System Baseline suite schema")
    rows = suite.get("cases")
    if not isinstance(rows, list) or not rows:
        raise ValueError("suite requires a nonempty fixed case list")
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("suite rows must be objects")
        item = dict(row)
        for key in ("bundle",):
            candidate = Path(item[key])
            item[key] = str((path.parent / candidate).resolve()) if not candidate.is_absolute() else str(candidate)
        edit = item.get("scheduled_edit")
        if isinstance(edit, dict) and "bundle" in edit:
            edit = dict(edit)
            candidate = Path(edit["bundle"])
            edit["bundle"] = str((path.parent / candidate).resolve()) if not candidate.is_absolute() else str(candidate)
            item["scheduled_edit"] = edit
        normalized.append(item)
    return suite, normalized


def run_suite(path: Path = DEFAULT_SUITE, *, output_parent: Path = RUNS_DIR) -> dict[str, Any]:
    suite, cases = load_suite(path)
    results = [run_case(case, output_parent=output_parent) for case in cases]
    stale = suite.get("stale_negative")
    if isinstance(stale, dict):
        stale_paths = {key: str((path.parent / value).resolve())
                       for key, value in stale.items()}
        results.append(run_stale_edit_negative(
            bundle_path=stale_paths["bundle"],
            edited_bundle_path=stale_paths["edited_bundle"],
            output_parent=output_parent))
    summary = {"schema": "system-baseline-run-summary-v1",
               "recorded_at": datetime.now(timezone.utc).isoformat(),
               "suite_path": str(path.resolve()), "suite_sha256": __import__("hashlib").sha256(
                   path.read_bytes()).hexdigest(), "source_cases": suite.get("purpose"),
               "results": results}
    output_parent.mkdir(parents=True, exist_ok=True)
    path_out = output_parent / f"suite-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}-{secrets.token_hex(3)}.json"
    with path_out.open("x", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    summary["summary_path"] = str(path_out)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=DEFAULT_SUITE)
    parser.add_argument("--output-parent", type=Path, default=RUNS_DIR)
    args = parser.parse_args()
    result = run_suite(args.suite, output_parent=args.output_parent)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if all(row.get("status") == "DEVELOPMENT_RUN_RECORDED" for row in result["results"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
