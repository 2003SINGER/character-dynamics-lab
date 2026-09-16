"""Create a descriptive V0/V1 diagnostic comparison; not research evidence."""
import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V0 = ROOT / "demo/living_dynamics_v0/batch_48h_v0"
V1 = ROOT / "demo/living_dynamics_v1/batch_48h_v1"
def rows(path):
    with (path / "profile_summary.csv").open(newline="") as f: return list(csv.DictReader(f))
def avg(rs, key): return sum(float(r[key]) for r in rs) / len(rs)
v0, v1 = rows(V0), rows(V1)
def bathroom_mean(path):
    with (path / "actor_summary.csv").open(newline="") as f: rs=list(csv.DictReader(f))
    return sum(float(r["bathroom_count"])/2 for r in rs)/len(rs)
keys = ["meals_day_mean", "bathroom_day_mean", "study_hours_day_mean", "leisure_hours_day_mean", "sleep_hours_day_mean", "task_completion_rate", "task_completion_time_p10", "task_completion_time_p90", "switches_day_mean"]
lines = ["# DEMO LIVING V0 → V1 COMPARISON", "", "Application engineering diagnostics only; this does not establish psychological realism.", "", "| Metric | V0 mean across profiles | V1 mean across profiles |", "|---|---:|---:|"]
for k in keys:
    if k == "bathroom_day_mean":
        lines.append(f"| {k} | {bathroom_mean(V0):.3f} | {bathroom_mean(V1):.3f} |")
        continue
    a = [r for r in v0 if r[k] not in ("", "None")]; b = [r for r in v1 if r[k] not in ("", "None")]
    if k.startswith("task_completion_time"):
        av = sum(float(r[k]) for r in a) / len(a) if a else 0; bv = sum(float(r[k]) for r in b) / len(b) if b else 0
    else: av, bv = avg(a,k), avg(b,k)
    lines.append(f"| {k} | {av:.3f} | {bv:.3f} |")
for name, path in (("V0", V0), ("V1", V1)):
    agg=json.loads((path/"aggregate.json").read_text())
    lines += ["", f"## {name} diagnostics", "", "```json", json.dumps(agg["diagnostic_counts"], indent=2), "```", "", f"Switching: {json.dumps(agg['switching_distribution'])}"]
(V1 / "V0_V1_COMPARISON.md").write_text("\n".join(lines) + "\n")
