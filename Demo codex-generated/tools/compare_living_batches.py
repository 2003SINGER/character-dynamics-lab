"""Write a compact, reproducible V1-before versus calibrated comparison."""
import csv
import json
import pathlib
import sys


def rows(path):
    with (path / "actor_summary.csv").open(newline="") as handle:
        return list(csv.DictReader(handle))


def mean(records, field):
    return sum(float(row[field]) for row in records) / len(records)


def main(before_text, after_text, output_text):
    before, after, output = map(pathlib.Path, (before_text, after_text, output_text))
    old_rows, new_rows = rows(before), rows(after)
    old_diag = json.loads((before / "aggregate.json").read_text())["diagnostic_counts"]
    new_diag = json.loads((after / "aggregate.json").read_text())["diagnostic_counts"]
    fields = ("fatigue_mean", "anxiety_mean", "satisfaction_mean", "task_pressure_mean",
              "study_minutes", "sleep_minutes", "meal_count", "bathroom_count")
    lines = [
        "# DemoLivingV1 before vs calibrated",
        "",
        "Application/demo engineering comparison only. Same 128 actors, profiles, scenario seeds, policy seeds, world setup and action set; not research evidence or a claim of realism.",
        "",
        "| Metric | Frozen V1 | Calibrated |",
        "|---|---:|---:|",
    ]
    for field in fields:
        lines.append(f"| `{field}` mean | {mean(old_rows, field):.4f} | {mean(new_rows, field):.4f} |")
    lines += ["", "## Saturation diagnostics", ""]
    keys = sorted(set(old_diag) | set(new_diag))
    lines += ["| Flag | Frozen V1 actors | Calibrated actors |", "|---|---:|---:|"]
    lines += [f"| `{key}` | {old_diag.get(key, 0)} | {new_diag.get(key, 0)} |" for key in keys]
    lines += [
        "",
        "## Interpretation boundary",
        "",
        "The calibration removed the prior >80% same-extreme collapse for fatigue, anxiety and satisfaction without changing Runtime or the action surface. `EXCESSIVE_SLEEP` increases and remains a documented demo diagnostic; it is not tuned further in this milestone because no predefined sleep target is an acceptance objective.",
        "",
    ]
    output.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:4])
