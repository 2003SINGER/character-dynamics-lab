"""Separate instantaneous history dependence from 6h/24h/72h persistence."""
import argparse
import collections
import gzip
import json
import pathlib
import statistics

STATE_FIELDS = ("boredom", "fatigue", "task_pressure", "satisfaction",
                "hunger", "bathroom_urge", "anxiety", "screen_strain")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", type=pathlib.Path)
    args = parser.parse_args()
    root = args.experiment
    manifest = json.loads((root / "manifest.json").read_text())
    groups = collections.defaultdict(dict)
    for run in manifest["runs"]:
        if "profile" not in run:
            continue
        with gzip.open(root / run["trace"], "rt") as source:
            for line in source:
                if '"type":"fork"' not in line:
                    continue
                frame = json.loads(line)
                key = (run["case"], run["profile"], frame["checkpoint_day"],
                       frame["horizon_minutes"])
                groups[key][frame["branch"]] = frame
    samples = []
    for (case, profile, day, horizon), branches in groups.items():
        if set(branches) != {"correct", "reset", "stale_24h"}:
            raise AssertionError("missing or duplicate history fork branch")
        correct = branches["correct"]
        for branch in ("reset", "stale_24h"):
            other = branches[branch]
            if other["future_world_events"] != correct["future_world_events"]:
                raise AssertionError("counterfactual external tape differs")
            samples.append({"case": case, "profile": profile, "checkpoint_day": day,
                            "horizon_minutes": horizon, "branch": branch,
                            "immediate_pi_js": other["immediate_pi_js"],
                            "immediate_top1_changed": other["immediate_top1_changed"],
                            "abs_study_gap_minutes": abs(other["study_minutes"] - correct["study_minutes"]),
                            "abs_task_effort_gap": abs(other["task_effort"] - correct["task_effort"]),
                            "state_l1": sum(abs(other["state"][field] - correct["state"][field])
                                            for field in STATE_FIELDS),
                            "commitment_changed": other["state"]["commitment"]
                                                  != correct["state"]["commitment"]})
    summary = []
    for day in sorted({row["checkpoint_day"] for row in samples}):
        for branch in ("reset", "stale_24h"):
            for horizon in (360, 1440, 4320):
                rows = [row for row in samples if row["checkpoint_day"] == day
                        and row["branch"] == branch and row["horizon_minutes"] == horizon]
                if len(rows) != manifest["cases"] * 8:
                    raise AssertionError("incomplete paired history fork block")
                summary.append({"checkpoint_day": day, "branch": branch,
                                "horizon_minutes": horizon, "n": len(rows),
                                "mean_immediate_pi_js": statistics.mean(
                                    row["immediate_pi_js"] for row in rows),
                                "immediate_top1_change_rate": statistics.mean(
                                    row["immediate_top1_changed"] for row in rows),
                                "mean_abs_study_gap_minutes": statistics.mean(
                                    row["abs_study_gap_minutes"] for row in rows),
                                "mean_abs_task_effort_gap": statistics.mean(
                                    row["abs_task_effort_gap"] for row in rows),
                                "mean_state_l1": statistics.mean(row["state_l1"] for row in rows),
                                "commitment_change_rate": statistics.mean(
                                    row["commitment_changed"] for row in rows)})
    result = {"source_git_revision": manifest["git_revision"],
              "samples": len(samples), "summary": summary}
    (root / "history_depth_analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    lines = ["# History-fork persistence by checkpoint", "",
             "Each row compares the same actor's actual S/commitment against a neutral reset "
             "or prior-day S/commitment. W/O/P, RunningAction, policy RNG state and future "
             "external event tape are held fixed at the fork. Immediate JS is measured once "
             "at that checkpoint; later gaps are separate trajectories, not a new JS score.", "",
             "| Day | Alternative | Immediate JS | Top-1 changed | 6h/24h/72h absolute study gap (min) | 72h state L1 | 72h commitment changed |",
             "|---:|---|---:|---:|---:|---:|---:|"]
    for day in sorted({row["checkpoint_day"] for row in summary}):
        for branch in ("reset", "stale_24h"):
            rows = [row for row in summary if row["checkpoint_day"] == day
                    and row["branch"] == branch]
            first, _, last = rows
            gaps = "/".join(f"{row['mean_abs_study_gap_minutes']:.1f}" for row in rows)
            lines.append(f"| {day} | {branch} | {first['mean_immediate_pi_js']:.3f} | "
                         f"{first['immediate_top1_change_rate']:.1%} | {gaps} | "
                         f"{last['mean_state_l1']:.3f} | {last['commitment_change_rate']:.1%} |")
    lines += ["", "A cumulative study-time gap at 72h does not alone prove that the current "
              "state remains different; use the 72h state and commitment columns for that "
              "claim. All numbers describe this Demo under its synthetic life tape only.", ""]
    (root / "HISTORY_DEPTH_REPORT.md").write_text("\n".join(lines))


if __name__ == "__main__":
    main()
