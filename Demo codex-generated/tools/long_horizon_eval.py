"""Run same-world Demo P comparisons and history forks without huge raw JSON arrays."""
import argparse
import collections
import contextlib
import gzip
import hashlib
import json
import math
import pathlib
import select
import shutil
import statistics
import subprocess
import sys
import tempfile

LAYA_POLICY_ID = "laya-typed-policy-v0"


@contextlib.contextmanager
def laya_replay_server(cassette, scratch):
    bridge = pathlib.Path(__file__).with_name("laya_typed_proxy.py")
    process = subprocess.Popen(
        [sys.executable, str(bridge), "--replay", str(cassette),
         "--cassette", str(scratch / "replay-unused.jsonl"), "--port", "0"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        ready, _, _ = select.select([process.stdout], [], [], 30)
        if not ready:
            raise RuntimeError("Laya cassette replay proxy did not become ready")
        announcement = process.stdout.readline()
        if not announcement:
            raise RuntimeError("Laya cassette replay proxy exited before readiness")
        info = json.loads(announcement)
        if info.get("model") != "convaiinnovations/laya-typed-decisions":
            raise RuntimeError("unexpected Laya replay checkpoint")
        yield info["port"]
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

PROFILES = ["balanced", "disciplined", "procrastinating", "rest_seeking",
            "stimulation_seeking", "anxious", "body_sensitive", "spontaneous"]
AXES = ["procrastination", "self_control", "rest_preference", "stimulation_seeking",
        "task_anxiety_sensitivity", "screen_strain_sensitivity", "need_response", "action_noise"]
MINUTE_FIELDS = ["study_minutes", "leisure_minutes", "rest_minutes", "sleep_minutes",
                 "idle_minutes", "bodily_minutes"]
BEHAVIOR_FIELDS = ["mean_action_bout_minutes", "median_action_bout_minutes",
                   "p90_action_bout_minutes", "commitment_active_minutes_per_day",
                   "commitment_suspended_minutes_per_day", "action_entropy_bits",
                   "switches_per_day", "max_same_action_streak",
                   "repeat_transition_fraction"]


def percentile(values, fraction):
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * fraction
    low = math.floor(position)
    high = math.ceil(position)
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def behavioral_metrics(boundaries, days):
    bouts = collections.defaultdict(int)
    selections = []
    commitment = collections.Counter()
    for frame in boundaries:
        minutes = frame["elapsed_minutes"]
        action = frame["running_action_before"]
        if action is not None:
            bouts[(action, frame["running_action_started_at"])] += minutes
        commitment[frame["commitment_before"]] += minutes
        if frame["selected_action"] is not None:
            selections.append(frame["selected_action"])
    bout_lengths = list(bouts.values())
    counts = collections.Counter(selections)
    entropy = -sum((count / len(selections)) * math.log2(count / len(selections))
                   for count in counts.values()) if selections else 0.0
    transitions = list(zip(selections, selections[1:]))
    switches = sum(left != right for left, right in transitions)
    repeat = len(transitions) - switches
    streak = 0
    longest = 0
    prior = None
    for action in selections:
        streak = streak + 1 if action == prior else 1
        longest = max(longest, streak)
        prior = action
    return {
        "mean_action_bout_minutes": statistics.mean(bout_lengths) if bout_lengths else 0.0,
        "median_action_bout_minutes": percentile(bout_lengths, 0.5),
        "p90_action_bout_minutes": percentile(bout_lengths, 0.9),
        "commitment_active_minutes_per_day": commitment["active"] / days,
        "commitment_suspended_minutes_per_day": commitment["suspended"] / days,
        "action_entropy_bits": entropy,
        "switches_per_day": switches / days,
        "max_same_action_streak": longest,
        "repeat_transition_fraction": repeat / len(transitions) if transitions else 0.0,
        "selected_action_count": len(selections),
        "action_bout_count": len(bout_lengths),
    }


def run_one(exe, root, days, case, profile, axis=None, value=None,
            policy="rule", laya_port=None, laya_cassette=None):
    scenario, policy_seed = 1000 + 17 * case, 5000 + 31 * case
    label = profile if axis is None else f"axis_{axis}_{value:.1f}"
    folder = root / "runs"
    folder.mkdir(parents=True, exist_ok=True)
    raw = folder / f"case_{case:02d}_{label}.jsonl"
    command = [str(exe), str(scenario), str(policy_seed), str(days), profile,
               str(raw), "boundaries"]
    if axis is not None:
        command += [axis, str(value)]
    if policy == "laya":
        command += ["--laya-port", str(laya_port)]
    subprocess.run(command, check=True)
    digest = hashlib.sha256(raw.read_bytes()).hexdigest()
    # The second run is an independent deterministic replay, not a readback of
    # the first trace. Keep neither uncompressed run in the committed artifact.
    with tempfile.TemporaryDirectory(prefix="life-replay-") as temp:
        replay = pathlib.Path(temp) / "replay.jsonl"
        second = command.copy()
        second[5] = str(replay)
        if policy == "laya":
            with laya_replay_server(laya_cassette, pathlib.Path(temp)) as replay_port:
                second[-1] = str(replay_port)
                subprocess.run(second, check=True)
        else:
            subprocess.run(second, check=True)
        if hashlib.sha256(replay.read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"non-deterministic long run: {case} {label}")
    metadata = None
    daily, forks, tape, boundaries = [], [], [], []
    with raw.open() as handle:
        for line in handle:
            frame = json.loads(line)
            kind = frame["type"]
            if kind == "run":
                metadata = frame
            elif kind == "daily":
                daily.append(frame)
            elif kind == "fork":
                forks.append(frame)
            elif kind == "boundary":
                boundaries.append(frame)
                for event in frame["world_events"]:
                    tape.append((frame["timestamp"], event))
    assert metadata and metadata["scenario_seed"] == scenario and metadata["policy_seed"] == policy_seed
    assert metadata["policy_id"] == (LAYA_POLICY_ID if policy == "laya" else "rule-policy-v0")
    assert len(daily) == days and [row["day"] for row in daily] == list(range(1, days + 1))
    assert all(row["profile_id"] == metadata["profile_id"] for row in daily)
    expected = [7, 30, 60, 120, 180] if days >= 180 else sorted({7, days})
    expected = [day for day in expected if day <= days]
    assert len(forks) == len(expected) * 3 * 3, (len(forks), expected)
    compressed = raw.with_suffix(".jsonl.gz")
    with raw.open("rb") as source, compressed.open("wb") as sink:
        with gzip.GzipFile(filename="", mode="wb", fileobj=sink, compresslevel=6, mtime=0) as target:
            shutil.copyfileobj(source, target)
    raw.unlink()
    return {"metadata": metadata, "daily": daily, "forks": forks,
            "tape": tape, "behavior": behavioral_metrics(boundaries, days),
            "sha256": digest, "trace": str(compressed.relative_to(root))}


def means(rows):
    return {key: statistics.mean(row[key] for row in rows) for key in
            MINUTE_FIELDS + ["task_completions", "decision_count"]}


def features(daily):
    aggregates = means(daily)
    pressure = statistics.mean(row["state"]["task_pressure"] for row in daily)
    fatigue = statistics.mean(row["state"]["fatigue"] for row in daily)
    anxiety = statistics.mean(row["state"]["anxiety"] for row in daily)
    early = daily[:max(1, len(daily) // 3)]
    late = daily[-max(1, len(daily) // 3):]
    return [aggregates["study_minutes"], aggregates["leisure_minutes"],
            aggregates["rest_minutes"], aggregates["sleep_minutes"],
            aggregates["task_completions"] * 100, aggregates["decision_count"] * 5,
            pressure * 100, fatigue * 100, anxiety * 100,
            statistics.mean(row["study_minutes"] for row in late)
            - statistics.mean(row["study_minutes"] for row in early)]


def classifier(records):
    """Leave-one-environment-tape-out nearest-centroid diagnostic, no tuning."""
    if len({record["case"] for record in records}) < 3:
        return None
    correct = 0
    matrix = collections.Counter()
    for held_case in sorted({record["case"] for record in records}):
        train = [record for record in records if record["case"] != held_case]
        test = [record for record in records if record["case"] == held_case]
        scale = [max(1.0, statistics.pstdev(record["features"][i] for record in train))
                 for i in range(len(train[0]["features"]))]
        centroids = {}
        for profile in PROFILES:
            members = [record["features"] for record in train if record["profile"] == profile]
            centroids[profile] = [statistics.mean(vector[i] for vector in members)
                                  for i in range(len(scale))]
        for record in test:
            prediction = min(PROFILES, key=lambda profile:
                sum(((a - b) / width) ** 2 for a, b, width in
                    zip(record["features"], centroids[profile], scale)))
            matrix[(record["profile"], prediction)] += 1
            correct += prediction == record["profile"]
    return {"correct": correct, "total": len(records), "accuracy": correct / len(records),
            "chance": 1 / len(PROFILES),
            "confusion": [{"actual": a, "predicted": p, "count": n}
                          for (a, p), n in sorted(matrix.items())]}


def analyze_forks(forks):
    grouped = collections.defaultdict(dict)
    for row in forks:
        key = (row["scenario_seed"], row["profile_id"], row["checkpoint_day"],
               row["horizon_minutes"])
        grouped[key][row["branch"]] = row
    samples = []
    for key, branch in grouped.items():
        if set(branch) != {"correct", "reset", "stale_24h"}:
            raise RuntimeError(f"missing history branch: {key}")
        reference_events = branch["correct"]["future_world_events"]
        for alternative in ("reset", "stale_24h"):
            if branch[alternative]["future_world_events"] != reference_events:
                raise RuntimeError(f"future external tape diverged within history fork: {key}")
        for alternative in ("reset", "stale_24h"):
            source, other = branch["correct"], branch[alternative]
            samples.append({"scenario_seed": key[0], "profile_id": key[1],
                            "checkpoint_day": key[2], "horizon_minutes": key[3],
                            "branch": alternative,
                            "immediate_pi_js": other["immediate_pi_js"],
                            "immediate_top1_changed": other["immediate_top1_changed"],
                            "study_minutes_gap": other["study_minutes"] - source["study_minutes"],
                            "leisure_minutes_gap": other["leisure_minutes"] - source["leisure_minutes"],
                            "task_effort_gap": other["task_effort"] - source["task_effort"],
                            "fatigue_gap": other["state"]["fatigue"] - source["state"]["fatigue"]})
    summary = []
    for branch in ("reset", "stale_24h"):
        for horizon in (360, 1440, 4320):
            rows = [row for row in samples if row["branch"] == branch
                    and row["horizon_minutes"] == horizon]
            summary.append({"branch": branch, "horizon_minutes": horizon,
                            "checkpoints": len(rows),
                            "mean_immediate_pi_js": statistics.mean(row["immediate_pi_js"] for row in rows),
                            "immediate_top1_change_rate": statistics.mean(row["immediate_top1_changed"] for row in rows),
                            "mean_abs_study_gap_minutes": statistics.mean(abs(row["study_minutes_gap"]) for row in rows),
                            "mean_abs_leisure_gap_minutes": statistics.mean(abs(row["leisure_minutes_gap"]) for row in rows),
                            "mean_abs_task_effort_gap": statistics.mean(abs(row["task_effort_gap"]) for row in rows),
                            "mean_abs_fatigue_gap": statistics.mean(abs(row["fatigue_gap"]) for row in rows)})
    return samples, summary


def report(root, days, cases, actors, axes, policy):
    profile_rows = []
    feature_records = []
    all_forks = []
    for case, profile, run in actors:
        day_means = means(run["daily"])
        profile_rows.append({"case": case, "profile": profile, **day_means,
                             **run["behavior"]})
        feature_records.append({"case": case, "profile": profile,
                                "features": features(run["daily"])})
        all_forks.extend(run["forks"])
    profile_summary = []
    for profile in PROFILES:
        rows = [row for row in profile_rows if row["profile"] == profile]
        profile_summary.append({"profile": profile, "cases": len(rows), **{
            field: statistics.mean(row[field] for row in rows)
            for field in MINUTE_FIELDS + ["task_completions", "decision_count"]
                         + BEHAVIOR_FIELDS}})
    fork_samples, fork_summary = analyze_forks(all_forks)
    axis_summary = []
    for axis in AXES:
        variants = [item for item in axes if item[0] == axis]
        if not variants:
            continue
        axis_summary.append({"axis": axis, "values": [{"value": value,
            **means(run["daily"])} for _, value, run in variants]})
    outcome = {"days": days, "cases": cases, "profiles": PROFILES,
               "policy_id": LAYA_POLICY_ID if policy == "laya" else "rule-policy-v0",
               "profile_summary": profile_summary, "paired_case_metrics": profile_rows,
               "overall_behavior": {field: statistics.mean(row[field] for row in profile_rows)
                                    for field in BEHAVIOR_FIELDS},
               "personality_classifier": classifier(feature_records),
               "history_fork_summary": fork_summary, "axis_interventions": axis_summary}
    (root / "analysis.json").write_text(json.dumps(outcome, indent=2) + "\n")
    (root / "history_fork_samples.jsonl").write_text(
        "\n".join(json.dumps(row, separators=(",", ":")) for row in fork_samples) + "\n")
    lines = [f"# Same-world character evaluation — {days} days", "",
             f"Policy: `{outcome['policy_id']}`. Demo engineering evidence only.", "",
             "Demo engineering experiment. Each case gives all eight profiles the same initial W/O/S, "
             "scenario seed, task/event tape and policy RNG seed. Only P changes within a case.",
             "", "## Personality comparison", "",
             "| Profile | Study min/day | Leisure min/day | Rest min/day | Sleep min/day | Tasks completed/day |",
             "|---|---:|---:|---:|---:|---:|"]
    for row in profile_summary:
        lines.append(f"| {row['profile']} | {row['study_minutes']:.1f} | "
                     f"{row['leisure_minutes']:.1f} | {row['rest_minutes']:.1f} | "
                     f"{row['sleep_minutes']:.1f} | {row['task_completions']:.3f} |")
    lines += ["", "## Persistence, commitment and action patterns", "",
              "Action bouts are keyed by RunningAction start time, not boundary count. "
              "Commitment duration is attributed to its pre-boundary status. "
              "Entropy and repeats use selected action starts, without a pathology threshold.", "",
              "| Profile | Mean bout min | P90 bout min | Active I min/day | Suspended I min/day | Entropy bits | Switches/day | Max same-action streak |",
              "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for row in profile_summary:
        lines.append(f"| {row['profile']} | {row['mean_action_bout_minutes']:.1f} | "
                     f"{row['p90_action_bout_minutes']:.1f} | "
                     f"{row['commitment_active_minutes_per_day']:.1f} | "
                     f"{row['commitment_suspended_minutes_per_day']:.1f} | "
                     f"{row['action_entropy_bits']:.3f} | {row['switches_per_day']:.1f} | "
                     f"{row['max_same_action_streak']:.1f} |")
    lines += ["", "## History forks", "",
              "At each checkpoint, W/O/P and the policy RNG position are copied. "
              "Correct, neutral-reset and prior-day S/commitment receive the same future external tape.", "",
              "| Branch | Future | Mean immediate JS | Top-1 changed | Mean absolute study gap | Mean absolute task effort gap |",
              "|---|---:|---:|---:|---:|---:|"]
    for row in fork_summary:
        lines.append(f"| {row['branch']} | {row['horizon_minutes']//60}h | "
                     f"{row['mean_immediate_pi_js']:.4f} | "
                     f"{row['immediate_top1_change_rate']:.1%} | "
                     f"{row['mean_abs_study_gap_minutes']:.1f} min | "
                     f"{row['mean_abs_task_effort_gap']:.3f} |")
    if outcome["personality_classifier"]:
        score = outcome["personality_classifier"]
        lines += ["", "## Unseen-tape profile identification", "",
                  f"Leave-one-tape-out nearest centroid: {score['correct']}/{score['total']} "
                  f"= {score['accuracy']:.1%}; eight-way chance = 12.5%. "
                  "This is a diagnostic, not a calibrated human validity metric."]
    if axis_summary:
        lines += ["", "## Single-axis P interventions", "",
                  "Each row holds all other P dimensions, W and RNG fixed; values are 0.2/0.5/0.8.", ""]
        for row in axis_summary:
            values = row["values"]
            lines.append(f"- `{row['axis']}` study min/day: "
                         + " / ".join(f"{item['study_minutes']:.1f}" for item in values)
                         + "; rest min/day: "
                         + " / ".join(f"{item['rest_minutes']:.1f}" for item in values))
    lines += ["", "## Limits", "",
              "This tape reuses one room and deterministic recurring coursework every three days. "
              "It provides repeated opportunities, interruptions and deadlines, but does not model a full life. "
              "Strong or weak differentiation is a fact about this Demo and tape. "
              "The historical 48h batch was not paired and is not personality evidence.", ""]
    (root / "REPORT.md").write_text("\n".join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("executable", type=pathlib.Path)
    parser.add_argument("output", type=pathlib.Path)
    parser.add_argument("--days", type=int, choices=(7, 30, 90, 180, 365), required=True)
    parser.add_argument("--cases", type=int, default=1)
    parser.add_argument("--axes", action="store_true")
    parser.add_argument("--policy", choices=("rule", "laya"), default="rule")
    parser.add_argument("--laya-port", type=int)
    parser.add_argument("--laya-cassette", type=pathlib.Path)
    args = parser.parse_args()
    if args.cases < 1:
        parser.error("cases must be positive")
    if args.policy == "laya" and (args.laya_port is None or args.laya_cassette is None):
        parser.error("Laya evaluation requires --laya-port and --laya-cassette")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error(f"output directory is not empty: {args.output}")
    repo = pathlib.Path(__file__).resolve().parents[2]
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    binary_sha256 = hashlib.sha256(args.executable.read_bytes()).hexdigest()
    args.output.mkdir(parents=True, exist_ok=True)
    actors, axes, manifest_runs = [], [], []
    for case in range(args.cases):
        reference_tape = None
        reference_initial = None
        for profile in PROFILES:
            run = run_one(args.executable, args.output, args.days, case, profile,
                          policy=args.policy, laya_port=args.laya_port,
                          laya_cassette=args.laya_cassette)
            initial = (run["metadata"]["initial_task_effort_target"],
                       run["metadata"]["initial_task_deadline"])
            if reference_tape is None:
                reference_tape, reference_initial = run["tape"], initial
            if run["tape"] != reference_tape or initial != reference_initial:
                raise RuntimeError(f"external tape or initial task diverged: case={case} profile={profile}")
            actors.append((case, profile, run))
            manifest_runs.append({"case": case, "profile": profile,
                                  "scenario_seed": run["metadata"]["scenario_seed"],
                                  "policy_seed": run["metadata"]["policy_seed"],
                                  "personality": run["metadata"]["personality"],
                                  "initial_state": run["metadata"]["initial_state"],
                                  "behavior": run["behavior"],
                                  "sha256": run["sha256"], "trace": run["trace"]})
    if args.axes:
        axis_reference = next(run for case, profile, run in actors
                              if case == 0 and profile == "balanced")
        for axis in AXES:
            for value in (0.2, 0.5, 0.8):
                run = run_one(args.executable, args.output, args.days, 0,
                              "balanced", axis, value, policy=args.policy,
                              laya_port=args.laya_port, laya_cassette=args.laya_cassette)
                if run["tape"] != axis_reference["tape"] or (
                    run["metadata"]["initial_task_effort_target"],
                    run["metadata"]["initial_task_deadline"]
                ) != (
                    axis_reference["metadata"]["initial_task_effort_target"],
                    axis_reference["metadata"]["initial_task_deadline"]
                ):
                    raise RuntimeError(f"axis intervention changed external tape: {axis}={value}")
                baseline_p = axis_reference["metadata"]["personality"]
                variant_p = run["metadata"]["personality"]
                if any(variant_p[key] != (value if key == axis else baseline_p[key])
                       for key in baseline_p):
                    raise RuntimeError(f"axis intervention changed more than {axis}={value}")
                axes.append((axis, value, run))
                manifest_runs.append({"case": 0, "axis": axis, "value": value,
                                      "scenario_seed": run["metadata"]["scenario_seed"],
                                      "policy_seed": run["metadata"]["policy_seed"],
                                      "personality": run["metadata"]["personality"],
                                      "sha256": run["sha256"], "trace": run["trace"]})
    manifest = {"experiment": "DEMO_CORE_BEHAVIOR_EVAL_V0", "days": args.days,
                "policy_id": LAYA_POLICY_ID if args.policy == "laya" else "rule-policy-v0",
                "git_revision": revision, "executable_sha256": binary_sha256,
                "cases": args.cases, "same_world_within_case": True,
                "deterministic_rerun_count": len(manifest_runs),
                "scenario_seed_formula": "1000 + 17*case",
                "policy_seed_formula": "5000 + 31*case",
                "life_tape_cycle_days": 3, "runs": manifest_runs}
    if args.policy == "laya":
        cassette_copy = args.output / "laya_typed_probabilities.jsonl"
        shutil.copy2(args.laya_cassette, cassette_copy)
        cassette_rows = [json.loads(line) for line in cassette_copy.read_text().splitlines()]
        if not cassette_rows:
            raise RuntimeError("Laya experiment produced no typed model cassette")
        revisions = {row.get("checkpoint_revision", "unrecorded") for row in cassette_rows}
        prompt_versions = {row.get("prompt_version", "unrecorded") for row in cassette_rows}
        if len(revisions) != 1 or len(prompt_versions) != 1:
            raise RuntimeError("Laya cassette mixed checkpoint or prompt versions")
        manifest["laya_checkpoint"] = "convaiinnovations/laya-typed-decisions"
        manifest["laya_checkpoint_revision"] = revisions.pop()
        manifest["laya_prompt_version"] = prompt_versions.pop()
        manifest["laya_cassette_record_count"] = len(cassette_rows)
        manifest["laya_cassette_type_counts"] = dict(collections.Counter(
            row["type"] for row in cassette_rows))
        manifest["laya_cassette_sha256"] = hashlib.sha256(cassette_copy.read_bytes()).hexdigest()
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    report(args.output, args.days, args.cases, actors, axes, args.policy)


if __name__ == "__main__":
    main()
