"""Audit same-world RulePolicy vs actual LayaTypedPolicy Demo experiments."""

import argparse
import gzip
import json
import pathlib
import statistics

from long_horizon_eval import BEHAVIOR_FIELDS, MINUTE_FIELDS

METRICS = MINUTE_FIELDS + ["task_completions", "decision_count"] + BEHAVIOR_FIELDS


def load_experiment(root, expected_policy):
    manifest = json.loads((root / "manifest.json").read_text())
    analysis = json.loads((root / "analysis.json").read_text())
    if manifest["policy_id"] != expected_policy or analysis["policy_id"] != expected_policy:
        raise ValueError(f"{root} is not a {expected_policy} experiment")
    runs = {(row["case"], row["profile"]): row for row in manifest["runs"]
            if "profile" in row}
    return manifest, analysis, runs


def read_trace(root, run):
    metadata = None
    tape = []
    with gzip.open(root / run["trace"], "rt") as handle:
        for line in handle:
            row = json.loads(line)
            if row["type"] == "run":
                metadata = row
            elif row["type"] == "boundary":
                tape.extend((row["timestamp"], event) for event in row["world_events"])
    if metadata is None:
        raise ValueError(f"missing run metadata: {run['trace']}")
    return metadata, tape


def compare(rule_root, laya_root):
    rule_manifest, rule_analysis, rule_runs = load_experiment(rule_root, "rule-policy-v0")
    laya_manifest, laya_analysis, laya_runs = load_experiment(laya_root, "laya-typed-policy-v0")
    for field in ("days", "cases", "git_revision", "executable_sha256", "scenario_seed_formula",
                  "policy_seed_formula", "life_tape_cycle_days"):
        if rule_manifest[field] != laya_manifest[field]:
            raise ValueError(f"unpaired experiment manifest field: {field}")
    if set(rule_runs) != set(laya_runs):
        raise ValueError("Rule and Laya profile/case keys differ")
    deltas = []
    for key in sorted(rule_runs):
        rule, laya = rule_runs[key], laya_runs[key]
        for field in ("scenario_seed", "policy_seed", "personality", "initial_state"):
            if rule[field] != laya[field]:
                raise ValueError(f"case={key} differs before policy on {field}")
        rule_metadata, rule_tape = read_trace(rule_root, rule)
        laya_metadata, laya_tape = read_trace(laya_root, laya)
        for field in ("scenario_seed", "policy_seed", "profile_id", "personality",
                      "days", "dynamics_model", "life_tape_cycle_days",
                      "initial_task_effort_target", "initial_task_deadline", "initial_state"):
            if rule_metadata[field] != laya_metadata[field]:
                raise ValueError(f"case={key} trace metadata differs on {field}")
        if rule_tape != laya_tape:
            raise ValueError(f"case={key} external World tape diverged")
        rule_metrics = next(row for row in rule_analysis["paired_case_metrics"]
                            if (row["case"], row["profile"]) == key)
        laya_metrics = next(row for row in laya_analysis["paired_case_metrics"]
                            if (row["case"], row["profile"]) == key)
        deltas.append({"case": key[0], "profile": key[1],
                       "rule_sha256": rule["sha256"], "laya_sha256": laya["sha256"],
                       "delta_laya_minus_rule": {field: laya_metrics[field] - rule_metrics[field]
                                                 for field in METRICS}})
    fork_rule = {(row["branch"], row["horizon_minutes"]): row
                 for row in rule_analysis["history_fork_summary"]}
    fork_laya = {(row["branch"], row["horizon_minutes"]): row
                 for row in laya_analysis["history_fork_summary"]}
    if set(fork_rule) != set(fork_laya):
        raise ValueError("Rule/Laya history fork slices differ")
    fork_deltas = []
    for key in sorted(fork_rule):
        a, b = fork_rule[key], fork_laya[key]
        fields = ("mean_immediate_pi_js", "immediate_top1_change_rate",
                  "mean_abs_study_gap_minutes", "mean_abs_task_effort_gap")
        fork_deltas.append({"branch": key[0], "horizon_minutes": key[1],
                            "delta_laya_minus_rule": {field: b[field] - a[field] for field in fields}})
    return {
        "comparison": "RulePolicyV0 vs actual LayaTypedPolicyV0",
        "laya_checkpoint_revision": laya_manifest.get("laya_checkpoint_revision", "unrecorded"),
        "laya_prompt_version": laya_manifest.get("laya_prompt_version", "unrecorded"),
        "same_world_verified": True,
        "only_policy_changed": True,
        "days": rule_manifest["days"],
        "cases": rule_manifest["cases"],
        "actor_pairs": len(deltas),
        "paired_case_deltas": deltas,
        "overall_delta_laya_minus_rule": {field: statistics.mean(
            row["delta_laya_minus_rule"][field] for row in deltas) for field in METRICS},
        "personality_classifier": {
            "rule": rule_analysis["personality_classifier"],
            "laya": laya_analysis["personality_classifier"],
        },
        "history_fork_deltas": fork_deltas,
        "limits": (
            "Same synthetic one-room tape and seeded policy sampling. "
            "The Laya checkpoint was trained on other synthetic workflows; "
            "this is not human-character validity or calibrated probability evidence."
        ),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("rule_output", type=pathlib.Path)
    parser.add_argument("laya_output", type=pathlib.Path)
    parser.add_argument("comparison_output", type=pathlib.Path)
    args = parser.parse_args()
    if args.comparison_output.exists() and any(args.comparison_output.iterdir()):
        parser.error("comparison output directory must be empty")
    result = compare(args.rule_output, args.laya_output)
    args.comparison_output.mkdir(parents=True, exist_ok=True)
    (args.comparison_output / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = [f"# Paired policy comparison — {result['days']} days", "",
             f"{result['actor_pairs']} actor pairs; same World tape, initial W/O/S/I, "
             "P, RNG seed and Dynamics verified. Only policy changes.", "",
             "| Metric | Laya − Rule |", "|---|---:|"]
    for field, value in result["overall_delta_laya_minus_rule"].items():
        lines.append(f"| {field} | {value:+.3f} |")
    lines += ["", "## History fork delta", "",
              "| Branch | Horizon | Δ immediate π JS | Δ top-1 change rate | Δ study gap min |",
              "|---|---:|---:|---:|---:|"]
    for row in result["history_fork_deltas"]:
        delta = row["delta_laya_minus_rule"]
        lines.append(f"| {row['branch']} | {row['horizon_minutes']//60}h | "
                     f"{delta['mean_immediate_pi_js']:+.4f} | "
                     f"{delta['immediate_top1_change_rate']:+.3f} | "
                     f"{delta['mean_abs_study_gap_minutes']:+.1f} |")
    lines += ["", result["limits"], ""]
    (args.comparison_output / "REPORT.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
