"""Persist a few labelled offline receipts, never game/search/model calls."""
from __future__ import annotations

import json
from pathlib import Path
from .test_diagnostic import synthetic, receipt
from ..monitor import inspect_rows
from tools.open_adventure_planning_v0.verify import verify_ledger


def emit(output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    variants = {"normal": (synthetic(), True), "vanished_after_crossing": (synthetic(vanish=True), True),
                "unfinished": (synthetic()[:-1], False)}
    ambiguous = synthetic(); ambiguous[2] = receipt(2, "wave rod", "Something glimmers, but the result is unclear.")
    variants["ambiguous_bridge"] = (ambiguous, True)
    missing = synthetic(); missing.pop(2); variants["missing_receipt"] = (missing, True)
    died = synthetic(); died[1] = receipt(1, "on lamp", "Oh dear, you seem to have gotten yourself killed. Reincarnating. Your lamp is now on.")
    variants["died_then_alive"] = (died, True)
    results = {}
    for name, (rows, ended) in variants.items():
        target = output / f"{name}.synthetic.jsonl"
        target.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        results[name] = {"origin": "SYNTHETIC_OFFLINE_ONLY", "native_episodes": 0,
                         "temporal": inspect_rows(rows, ended=ended),
                         "old_E_verifier": verify_ledger(target, "E") if ended else "NOT_APPLICABLE_UNFINISHED"}
    (output / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n")
    return results
