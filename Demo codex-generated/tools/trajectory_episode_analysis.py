"""Read frozen compact traces; measure repeated-task response, not only totals."""
import argparse
import collections
import gzip
import json
import pathlib
import statistics

from long_horizon_eval import PROFILES, classifier

START = 480
DAY = 1440
STUDY = {"study_focused", "study_halfhearted", "study_at_computer"}


def average(values):
    return statistics.mean(values) if values else None


def episode_rows(trace, expected_days):
    with gzip.open(trace, "rt") as handle:
        rows = (json.loads(line) for line in handle)
        metadata = next(rows)
        assert metadata["type"] == "run" and metadata["days"] == expected_days
        cycle = metadata["life_tape_cycle_days"] * DAY
        episodes = [{"episode": i, "first_study_latency_minutes": None,
                     "completion_latency_minutes": None,
                     "study_starts": 0, "study_by_day_minutes": [0, 0, 0],
                     "commitment_active_minutes": 0,
                     "commitment_suspended_minutes": 0}
                    for i in range(expected_days * DAY // cycle)]
        previous_commitment = "none"
        daily_study_minutes = 0
        for frame in rows:
            if frame["type"] == "daily":
                daily_study_minutes += frame["study_minutes"]
                continue
            if frame["type"] != "boundary":
                continue
            end = frame["timestamp"]
            begin = end - frame["elapsed_minutes"]
            if end > START + expected_days * DAY:
                raise AssertionError("boundary beyond requested horizon")
            # World and scheduler split at every task assignment and every
            # daily checkpoint; nonetheless intersect explicitly so a later
            # change to max integration step cannot misattribute minutes.
            position = begin
            while position < end:
                episode = (position - START) // cycle
                if episode < 0 or episode >= len(episodes):
                    break
                assigned = START + episode * cycle
                phase = min(2, (position - assigned) // DAY)
                segment_end = min(end, assigned + (phase + 1) * DAY,
                                  assigned + cycle)
                minutes = segment_end - position
                if minutes <= 0:
                    raise AssertionError("non-progressing task interval")
                item = episodes[episode]
                if frame["running_action_before"] in STUDY:
                    item["study_by_day_minutes"][phase] += minutes
                if previous_commitment == "active":
                    item["commitment_active_minutes"] += minutes
                elif previous_commitment == "suspended":
                    item["commitment_suspended_minutes"] += minutes
                position = segment_end
            episode = (end - START) // cycle
            if 0 <= episode < len(episodes):
                item = episodes[episode]
                latency = end - (START + episode * cycle)
                if (frame["selected_action"] in STUDY
                        and frame["replacement_validation_performed"]
                        and frame["replacement_validation_accepted"]):
                    item["study_starts"] += 1
                    if item["first_study_latency_minutes"] is None:
                        item["first_study_latency_minutes"] = latency
                if frame["task_completed"]:
                    if item["completion_latency_minutes"] is not None:
                        raise AssertionError("same task completed twice")
                    item["completion_latency_minutes"] = latency
            previous_commitment = frame["state"]["commitment"]
        if sum(sum(item["study_by_day_minutes"]) for item in episodes) != daily_study_minutes:
            raise AssertionError("episode study minutes differ from canonical daily totals")
        return metadata, episodes


def summarize(episodes):
    first = [row["first_study_latency_minutes"] for row in episodes
             if row["first_study_latency_minutes"] is not None]
    completed = [row["completion_latency_minutes"] for row in episodes
                 if row["completion_latency_minutes"] is not None]
    return {"episodes": len(episodes),
            "first_study_latency_mean_minutes": average(first),
            "first_study_latency_p90_minutes": sorted(first)[int((len(first)-1)*0.9)] if first else None,
            "completion_latency_mean_minutes": average(completed),
            "completion_rate": len(completed) / len(episodes),
            "study_starts_mean": average([row["study_starts"] for row in episodes]),
            "study_by_day_mean_minutes": [average([row["study_by_day_minutes"][i]
                                                     for row in episodes]) for i in range(3)],
            "commitment_active_mean_minutes": average(
                [row["commitment_active_minutes"] for row in episodes]),
            "commitment_suspended_mean_minutes": average(
                [row["commitment_suspended_minutes"] for row in episodes])}


def features(summary):
    return [summary["first_study_latency_mean_minutes"] or 0,
            summary["first_study_latency_p90_minutes"] or 0,
            summary["completion_latency_mean_minutes"] or 0,
            summary["study_starts_mean"] * 30,
            *summary["study_by_day_mean_minutes"],
            summary["commitment_active_mean_minutes"],
            summary["commitment_suspended_mean_minutes"]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", type=pathlib.Path)
    args = parser.parse_args()
    root = args.experiment
    manifest = json.loads((root / "manifest.json").read_text())
    days = manifest["days"]
    if days % manifest["life_tape_cycle_days"]:
        raise ValueError("episode analysis needs a whole number of task cycles")
    actor_runs = [run for run in manifest["runs"] if "profile" in run]
    if len(actor_runs) != manifest["cases"] * len(PROFILES):
        raise AssertionError("incomplete paired profile block")
    episodes_out = []
    case_rows = []
    for run in actor_runs:
        metadata, episodes = episode_rows(root / run["trace"], days)
        if metadata["profile_id"] != run["profile"] or metadata["personality"] != run["personality"]:
            raise AssertionError("profile provenance differs from frozen manifest")
        for row in episodes:
            episodes_out.append({"case": run["case"], "profile": run["profile"], **row})
        case_rows.append({"case": run["case"], "profile": run["profile"],
                          **summarize(episodes)})
    (root / "episode_rows.jsonl").write_text(
        "\n".join(json.dumps(row, separators=(",", ":")) for row in episodes_out) + "\n")
    profile_summary = []
    for profile in PROFILES:
        rows = [row for row in case_rows if row["profile"] == profile]
        profile_summary.append({"profile": profile, "cases": len(rows),
                                "first_study_latency_mean_minutes": average(
                                    [row["first_study_latency_mean_minutes"] for row in rows]),
                                "completion_latency_mean_minutes": average(
                                    [row["completion_latency_mean_minutes"] for row in rows]),
                                "completion_rate": average([row["completion_rate"] for row in rows]),
                                "study_starts_mean": average([row["study_starts_mean"] for row in rows]),
                                "study_by_day_mean_minutes": [average(
                                    [row["study_by_day_mean_minutes"][i] for row in rows]) for i in range(3)],
                                "commitment_active_mean_minutes": average(
                                    [row["commitment_active_mean_minutes"] for row in rows]),
                                "commitment_suspended_mean_minutes": average(
                                    [row["commitment_suspended_mean_minutes"] for row in rows])})
    records = [{"case": row["case"], "profile": row["profile"],
                "features": features(row)} for row in case_rows]
    analysis = {"source_git_revision": manifest["git_revision"], "days": days,
                "case_rows": case_rows, "profile_summary": profile_summary,
                "episode_feature_classifier": classifier(records)}
    (root / "episode_analysis.json").write_text(json.dumps(analysis, indent=2) + "\n")
    lines = [f"# Repeated-task trajectory analysis — {days} days", "",
             "For each three-day task: latency from assignment to first accepted study start, "
             "latency to actual completion, study time in successive 24h windows, and "
             "time spent in Active/Suspended commitment. Means below are across the paired "
             "world tapes; episode rows retain every individual task.", "",
             "| Profile | First study (h) | Completion (h) | Study day 1/2/3 (min) | Active commitment (h/task) |",
             "|---|---:|---:|---:|---:|"]
    for row in profile_summary:
        phases = "/".join(f"{value:.0f}" for value in row["study_by_day_mean_minutes"])
        lines.append(f"| {row['profile']} | {row['first_study_latency_mean_minutes']/60:.2f} | "
                     f"{row['completion_latency_mean_minutes']/60:.2f} | {phases} | "
                     f"{row['commitment_active_mean_minutes']/60:.2f} |")
    score = analysis["episode_feature_classifier"]
    if score:
        lines += ["", f"Leave-one-world-tape-out identification using only these episode-response "
                  f"features: {score['correct']}/{score['total']} = {score['accuracy']:.1%}; "
                  "eight-way chance is 12.5%. This remains a within-Demo diagnostic, not "
                  "evidence of human personality validity."]
    (root / "EPISODE_REPORT.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
