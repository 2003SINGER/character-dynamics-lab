"""Explicitly run one frozen Mature-Methods matched pair; never batch implicitly."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .runner import RUNS_DIR, SUITE_PATH, run_matched_pair


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True, help="one exact case_id from frozen suite.json")
    parser.add_argument("--suite", type=Path, default=SUITE_PATH)
    parser.add_argument("--runs-dir", type=Path, default=RUNS_DIR)
    args = parser.parse_args()
    result = run_matched_pair(args.case_id, suite_path=args.suite, runs_dir=args.runs_dir)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, default=str))
    return 0 if all("error_type" not in result.get(arm, {}) for arm in ("baseline", "mature_methods")) else 2


if __name__ == "__main__":
    raise SystemExit(main())
