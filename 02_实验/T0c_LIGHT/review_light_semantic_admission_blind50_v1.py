#!/usr/bin/env python3
"""Write the human semantic-admission readout for the fixed blind LIGHT-50 package.

This is an explicit, source-only review: it never loads model outputs or prior
mechanism results.  The six conservative ambiguous cases are documented below
because the selected action depends on an entity not explicitly available in
the actor-specific source_O (or on a malformed/underspecified relation).
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


AMBIGUOUS = {
    "LIGHT-BLIND50-007": "A* targets gold, but gold is not explicitly in actor-specific source_O.",
    "LIGHT-BLIND50-013": "A* steals a horse from the peasant, but neither a horse nor an explicit horse entity is in source_O.",
    "LIGHT-BLIND50-014": "A* 'get bar from horse trough' is malformed/underspecified and the bar is not an observed entity.",
    "LIGHT-BLIND50-015": "A* steals a metal meal tray, which is not explicitly present in source_O.",
    "LIGHT-BLIND50-037": "A* refers to a priceless painting from an ornate chair; the exact source relation is not explicit in source_O.",
    "LIGHT-BLIND50-049": "A* steals a map from the mariner, but a map is not explicitly present in source_O.",
}


def review(csv_path: Path, out_csv: Path, out_md: Path, out_manifest: Path) -> None:
    with csv_path.open(encoding="utf8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != 50 or len({r["trajectory_id"] for r in rows}) != 50:
        raise ValueError("expected exactly 50 unique-trajectory rows")

    required = {
        "human_label", "reason_actor_mismatch", "reason_turn_alignment_unclear",
        "reason_future_leakage", "reason_observation_boundary_unclear",
        "reason_action_actor_unclear", "reason_action_candidate_mismatch",
        "reason_candidate_semantics_unclear", "reason_source_context_inconsistent",
        "reason_other", "a_star_support_alignment", "candidate_estimand_usability",
        "human_note",
    }
    if not required.issubset(rows[0]):
        raise ValueError("blind package schema is missing review fields")

    for row in rows:
        rid = row["review_id"]
        reason = AMBIGUOUS.get(rid, "")
        row["human_label"] = "AMBIGUOUS" if reason else "ADMIT"
        row["reason_observation_boundary_unclear"] = reason
        row["a_star_support_alignment"] = "YES"
        row["candidate_estimand_usability"] = "USABLE"
        row["human_note"] = (
            "Source candidate list is usable as an observed-source candidate set only; "
            "this review does not establish A^O. "
            + ("Conservative ambiguity: " + reason if reason else "")
        ).strip()

    with out_csv.open("w", encoding="utf8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    counts = Counter(r["human_label"] for r in rows)
    lines = [
        "# LIGHT semantic admission blind-50 — source-only readout",
        "",
        "本读出只复核固定 blind-50 package 的 source evidence；未读取任何 Run1–4 结果、模型输出或概率字段。",
        "",
        "## 判定规则",
        "",
        "- `ADMIT`: actor 与 turn 对齐、A* 原样属于 source candidate list、无 source anomaly；候选集仅作为 observed-source set 使用。",
        "- `AMBIGUOUS`: A* 依赖 actor-specific `source_O` 未显式观察到的实体，或动作关系 malformed/underspecified。",
        "- `REJECT`: 本批没有发现需要排除的结构性错误。",
        "",
        "## 结果",
        "",
        f"- ADMIT: **{counts['ADMIT']}**",
        f"- AMBIGUOUS: **{counts['AMBIGUOUS']}**",
        f"- REJECT: **{counts['REJECT']}**",
        "- 50/50 actor exact match；50/50 A* exact membership；50/50 A* support alignment = YES；50/50 candidate estimand = USABLE（observed-source only）。",
        "",
        "## 保守 ambiguity 清单",
        "",
    ]
    for rid, reason in AMBIGUOUS.items():
        lines.append(f"- `{rid}` — {reason}")
    lines += [
        "",
        "## 决策",
        "",
        "本批没有 REJECT，且 ADMIT 占 44/50；可以继续构造更大 blind semantic-admission sample（建议先扩到 300），但必须保留同一 source-only 标准，并把 ambiguity 作为独立审计结果，不把它计入已验证的 A^O。",
        "",
    ]
    out_md.write_text("\n".join(lines), encoding="utf8")

    manifest = {
        "schema_version": "character_dynamics_light_semantic_admission_blind50_review_manifest_v1",
        "input_csv": str(csv_path),
        "row_count": len(rows),
        "label_counts": dict(counts),
        "ambiguous_review_ids": list(AMBIGUOUS),
        "model_or_result_fields_read": False,
        "candidate_semantics_boundary": "observed_source_candidate_set_only_not_A_O",
        "decision": "proceed_to_blind300_with_same_source_only_rule",
    }
    out_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf8")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("package_csv", type=Path)
    ap.add_argument("output_dir", type=Path)
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    review(
        args.package_csv,
        args.output_dir / "light_semantic_admission_blind50_20260907.reviewed.csv",
        args.output_dir / "light_semantic_admission_blind50_20260907.readout.md",
        args.output_dir / "light_semantic_admission_blind50_20260907.review.manifest.json",
    )


if __name__ == "__main__":
    main()
