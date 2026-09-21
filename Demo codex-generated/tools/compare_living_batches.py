"""Write a compact, reproducible comparison of two DemoLiving V1 batches."""
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
    old_manifest = json.loads((before / "manifest.json").read_text())
    new_manifest = json.loads((after / "manifest.json").read_text())
    old_diag = json.loads((before / "aggregate.json").read_text())["diagnostic_counts"]
    new_diag = json.loads((after / "aggregate.json").read_text())["diagnostic_counts"]
    fields = ("fatigue_mean", "anxiety_mean", "satisfaction_mean", "task_pressure_mean",
              "study_minutes", "sleep_minutes", "meal_count", "bathroom_count")
    lines = [
        "# DemoLivingV1 batch comparison",
        "",
        "Application/demo engineering comparison only. Same 128 actors, profiles, scenario seeds, policy seeds, world setup and action set; not research evidence or a claim of realism.",
        f"Before artifact: `{old_manifest['artifact_id']}` at `{old_manifest['git_revision'][:7]}`.",
        f"After artifact: `{new_manifest['artifact_id']}` at `{new_manifest['git_revision'][:7]}`.",
        "",
        "| Metric | Before | After |",
        "|---|---:|---:|",
    ]
    for field in fields:
        lines.append(f"| `{field}` mean | {mean(old_rows, field):.4f} | {mean(new_rows, field):.4f} |")
    lines += ["", "## Diagnostics", ""]
    keys = sorted(set(old_diag) | set(new_diag))
    lines += ["| Flag | Before actors | After actors |", "|---|---:|---:|"]
    lines += [f"| `{key}` | {old_diag.get(key, 0)} | {new_diag.get(key, 0)} |" for key in keys]
    lines += [
        "",
        "## Interpretation boundary",
        "",
        "This comparison records a mechanism-repair checkpoint, not a fitted behavioral target. The after batch uses the current event and continuous audit semantics; any historical diagnostic whose definition changed must be read as contextual rather than a calibrated delta.",
        "",
    ]
    output.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main(*sys.argv[1:4])
