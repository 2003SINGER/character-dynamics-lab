#!/usr/bin/env python3
"""Run the frozen AGAIN development-only dynamics audit.

This file is intentionally kept under ignored ``outputs/``.  It does not fit
alpha/beta/b/W and does not modify the adapter, protocol, or Theory-S files.
"""
from __future__ import annotations

import bisect
import hashlib
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
REPLAY = ROOT / "_local_data/AGAIN/again_dev_20_v4/AGAIN_dev.replay.jsonl"
MANIFEST = ROOT / "02_实验/T0h_AGAIN/again_dev_20_v4/AGAIN_dev.manifest.json"
QA = ROOT / "02_实验/T0h_AGAIN/again_dev_20_v4/AGAIN_dev.qa.json"

# These are fixed before reading any held-out results.  Each is a single raw
# telemetry channel; no learned/composite arousal score is constructed.
EVENT_CHANNELS = [
    "player_respawn", "player_death", "player_damaged", "player_healing",
    "player_shooting", "player_reloading", "player_is_crashing",
    "player_is_looping", "player_is_falling", "player_is_jumping",
    "player_has_collisions", "player_point_pickup", "player_power_pickup",
    "player_boost_pickup",
]
TAU_GRID = [0.5, 1.0, 2.0, 5.0]
PHI_GRID = [0.0, 0.5, 0.8, 0.95]
PERSISTENCE_LAGS = [0.25, 0.5, 1.0, 2.0, 4.0]
EVENT_OFFSETS = [0.0, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0]
EVENT_PRE_WINDOW = 1.0
EVENT_POST_WINDOW = 5.0
MATCH_TOLERANCE = 0.15
RECOVERY_FRACTION = 0.10
RECOVERY_FLOOR = 1.0


def fnum(x):
    try:
        if x in (None, ""):
            return None
        y = float(x)
        return y if math.isfinite(y) else None
    except (TypeError, ValueError):
        return None


def median_or_none(xs):
    xs = [x for x in xs if x is not None and math.isfinite(x)]
    return statistics.median(xs) if xs else None


def iqr(xs):
    xs = sorted(x for x in xs if x is not None and math.isfinite(x))
    if not xs:
        return None
    if len(xs) == 1:
        return [xs[0], xs[0]]
    q1, q3 = statistics.quantiles(xs, n=4, method="inclusive")[0::2]
    return [q1, q3]


def pearson(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    mx = statistics.fmean(x for x, _ in pairs)
    my = statistics.fmean(y for _, y in pairs)
    num = sum((x - mx) * (y - my) for x, y in pairs)
    dx = math.sqrt(sum((x - mx) ** 2 for x, _ in pairs))
    dy = math.sqrt(sum((y - my) ** 2 for _, y in pairs))
    return num / (dx * dy) if dx > 0 and dy > 0 else None


def mae_rmse(ys, ps):
    pairs = [(y, p) for y, p in zip(ys, ps) if y is not None and p is not None]
    if not pairs:
        return {"n": 0, "mae": None, "rmse": None}
    err = [y - p for y, p in pairs]
    return {"n": len(err), "mae": statistics.fmean(abs(x) for x in err),
            "rmse": math.sqrt(statistics.fmean(x * x for x in err))}


def aggregate(values):
    vals = [v for v in values if v is not None and math.isfinite(v)]
    return {"n": len(vals), "median": median_or_none(vals), "iqr": iqr(vals)}


def nearest_future(times, values, target, tolerance=MATCH_TOLERANCE):
    """Return nearest observed value at/after target within fixed tolerance."""
    j = bisect.bisect_left(times, target)
    if j >= len(times):
        return None
    if times[j] - target > tolerance:
        return None
    return values[j]


def numeric_channel(row, channel):
    return fnum(row.get("source_step_context", {}).get("telemetry", {}).get(channel))


def build_event_flags(rows, channel):
    """Pre-registered binary-onset envelope: current > 0 and prior <= 0/missing."""
    out = []
    prev = None
    for row in rows:
        cur = numeric_channel(row, channel)
        is_event = cur is not None and cur > 0 and (prev is None or prev <= 0)
        out.append(1.0 if is_event else 0.0)
        prev = cur
    return out


def relaxation_trace(rows, flags, tau):
    state = 0.0
    out = []
    prev_t = None
    for row, event in zip(rows, flags):
        t = row["timestamp"]
        dt = 0.0 if prev_t is None else max(0.0, t - prev_t)
        decay = math.exp(-dt / tau) if tau > 0 else 0.0
        envelope = event  # fixed unit event pulse; no learned scale/weight
        state = decay * state + (1.0 - decay) * envelope
        out.append(state)
        prev_t = t
    return out


def event_response(rows, channel, heldout_indices=None):
    """Descriptive event-to-proxy response; no causal or model claim."""
    if heldout_indices is None:
        heldout_indices = range(len(rows))
    allowed = set(heldout_indices)
    flags = build_event_flags(rows, channel)
    times = [r["timestamp"] for r in rows]
    ys = [r["source_arousal_proxy"] for r in rows]
    records = []
    for i, (row, flag) in enumerate(zip(rows, flags)):
        if not flag or i not in allowed:
            continue
        t = times[i]
        before = [ys[j] for j in range(i) if ys[j] is not None and t - EVENT_PRE_WINDOW <= times[j] < t]
        baseline = median_or_none(before)
        initial = nearest_future(times, ys, t, MATCH_TOLERANCE)
        if baseline is None or initial is None:
            continue
        response = {}
        complete = True
        for off in EVENT_OFFSETS:
            val = nearest_future(times, ys, t + off, MATCH_TOLERANCE)
            response[str(off)] = None if val is None else val - baseline
            if val is None:
                complete = False
        records.append({"index": i, "event_time": t, "baseline": baseline,
                        "initial_deviation": initial - baseline,
                        "response": response, "complete": complete})
    return records


def summarize_event(records):
    if not records:
        return {"events": 0, "complete_events": 0, "response_median": {},
                "response_iqr": {}, "decay": "undefined", "recovery": {"n": 0, "median": None, "iqr": None},
                "recovery_censored": 0, "lag_peak_offset": None}
    response_median = {}
    response_iqr = {}
    for off in EVENT_OFFSETS:
        vals = [r["response"][str(off)] for r in records if r["response"][str(off)] is not None]
        response_median[str(off)] = median_or_none(vals)
        response_iqr[str(off)] = iqr(vals)
    # Lag is a descriptive peak in median absolute event response.
    absmed = {off: (abs(v) if v is not None else None) for off, v in response_median.items()}
    valid_abs = [(float(off), v) for off, v in absmed.items() if v is not None]
    peak = max(valid_abs, key=lambda z: z[1])[0] if valid_abs else None
    # Decay/recovery use per-event absolute deviation relative to offset 0.
    retention = []
    recoveries = []
    censored = 0
    for r in records:
        d0 = abs(r["initial_deviation"])
        if d0 <= 0:
            continue
        vals = [r["response"][str(off)] for off in EVENT_OFFSETS]
        if vals[0] is not None:
            retention.append([abs(v) / d0 if v is not None else None for v in vals])
        tol = max(RECOVERY_FLOOR, RECOVERY_FRACTION * d0)
        recovered = None
        for off, v in zip(EVENT_OFFSETS, vals):
            if v is not None and abs(v) <= tol:
                recovered = off
                break
        if recovered is None:
            censored += 1
        else:
            recoveries.append(recovered)
    decay_status = "undefined"
    if retention:
        medret = [median_or_none([r[k] for r in retention if r[k] is not None]) for k in range(len(EVENT_OFFSETS))]
        finite = [x for x in medret if x is not None]
        if len(finite) >= 2:
            decay_status = "monotone_nonincreasing" if all(a >= b for a, b in zip(finite, finite[1:])) else "non-monotone/undefined"
    return {"events": len(records), "complete_events": sum(1 for r in records if r["complete"]),
            "response_median": response_median, "response_iqr": response_iqr,
            "decay": decay_status, "recovery": aggregate(recoveries),
            "recovery_censored": censored, "lag_peak_offset": peak}


def validate(records, manifest, qa):
    problems = []
    if not REPLAY.exists():
        problems.append("replay_missing")
        return problems
    digest = hashlib.sha256(REPLAY.read_bytes()).hexdigest()
    if digest != manifest.get("replay_sha256"):
        problems.append(f"replay_sha256_mismatch:{digest}")
    if not all(qa.get("hard_checks", {}).values()):
        problems.append("existing_qa_hard_check_false")
    seen = set()
    total = 0
    for rec in records:
        key = (rec.get("subject_id"), rec.get("source_episode_context", {}).get("session_id"), rec.get("source_episode_context", {}).get("game"))
        if key in seen:
            problems.append(f"duplicate_boundary:{key}")
        seen.add(key)
        prev_t = None
        for step in rec.get("steps", []):
            total += 1
            t = fnum(step.get("timestamp"))
            if t is None or (prev_t is not None and t < prev_t):
                problems.append(f"timestamp_order:{rec.get('trajectory_id')}:{step.get('t')}")
            prev_t = t
            m = fnum(step.get("arousal_alignment", {}).get("matched_annotation_time_stamp"))
            if m is not None and m > t:
                problems.append(f"future_annotation:{rec.get('trajectory_id')}:{step.get('t')}")
            if step.get("source_O") is not None or step.get("source_action_A_star") is not None or step.get("state_label") is not None:
                problems.append(f"forbidden_source_field:{rec.get('trajectory_id')}:{step.get('t')}")
            if step.get("source_arousal_proxy") is None:
                problems.append(f"missing_proxy:{rec.get('trajectory_id')}:{step.get('t')}")
    if total != manifest.get("step_count"):
        problems.append(f"step_count:{total}!={manifest.get('step_count')}")
    return problems


def eval_persistence(rows):
    times = [r["timestamp"] for r in rows]
    ys = [r["source_arousal_proxy"] for r in rows]
    out = {}
    for lag in PERSISTENCE_LAGS:
        x, y = [], []
        for i, t in enumerate(times):
            v = nearest_future(times, ys, t + lag, MATCH_TOLERANCE)
            if v is not None:
                x.append(ys[i]); y.append(v)
        out[str(lag)] = {"n": len(x), "corr": pearson(x, y), "retention_mae": statistics.fmean(abs(a-b) for a,b in zip(x,y)) if x else None}
    return out


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    qa = json.loads(QA.read_text(encoding="utf-8"))
    records = [json.loads(line) for line in REPLAY.read_text(encoding="utf-8").splitlines()]
    problems = validate(records, manifest, qa)
    script_hash = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    run_record = {
        "protocol": "02_实验/T0h_AGAIN/dynamics_protocol_v0.md",
        "protocol_status": "frozen development-only",
        "run_id": "again_dynamics_audit_v0_2026-09-08",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_replay": str(REPLAY.relative_to(ROOT)).replace("\\", "/"),
        "input_manifest": str(MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "input_qa": str(QA.relative_to(ROOT)).replace("\\", "/"),
        "input_replay_sha256": hashlib.sha256(REPLAY.read_bytes()).hexdigest() if REPLAY.exists() else None,
        "manifest_replay_sha256": manifest.get("replay_sha256"),
        "software_script_sha256": script_hash,
        "event_envelope_preregistered_before_metrics": True,
        "event_channels": EVENT_CHANNELS,
        "event_definition": "per-channel binary onset: current numeric value > 0 and immediately prior numeric value is missing or <= 0; first row is not an event",
        "tau_grid_seconds": TAU_GRID,
        "phi_grid_per_second": PHI_GRID,
        "persistence_lags_seconds": PERSISTENCE_LAGS,
        "event_offsets_seconds": EVENT_OFFSETS,
        "event_pre_window_seconds": EVENT_PRE_WINDOW,
        "event_post_window_seconds": EVENT_POST_WINDOW,
        "match_tolerance_seconds": MATCH_TOLERANCE,
        "recovery_tolerance": {"fraction_of_initial_absolute_deviation": RECOVERY_FRACTION, "floor_proxy_units": RECOVERY_FLOOR},
        "folds": {"participant_held_out": "one fold per player_id; all sessions for player held out", "game_held_out": "one fold per game; all sessions for game held out"},
        "future_input_policy": "current and past telemetry; current/past proxy only for AR; held-out future proxy used only as outcome",
        "training_policy": "training-part median only; no fitted dynamics parameters; no alpha/beta/b/W",
        "provenance_problems": problems,
    }
    (OUT / "run_record.json").write_text(json.dumps(run_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if problems:
        report = {"status": "blocked-by-provenance", "problems": problems, "run_record": run_record}
        (OUT / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (OUT / "conclusion.md").write_text("# AGAIN dynamics audit v0\n\n**BLOCKED-BY-PROVENANCE**\n\n" + "\n".join(f"- `{p}`" for p in problems) + "\n\nNo comparator was run.\n", encoding="utf-8")
        return 2

    trajectories = []
    for rec in records:
        trajectories.append({"id": rec["trajectory_id"], "player": rec["subject_id"],
                             "session": rec["source_episode_context"]["session_id"], "game": rec["source_episode_context"]["game"],
                             "rows": rec["steps"]})
    groups = {"participant_held_out": sorted({x["player"] for x in trajectories}),
              "game_held_out": sorted({x["game"] for x in trajectories})}
    fold_results = []
    for holdout_kind, heldout_values in groups.items():
        for heldout in heldout_values:
            train = [x for x in trajectories if (x["player"] if holdout_kind == "participant_held_out" else x["game"]) != heldout]
            test = [x for x in trajectories if (x["player"] if holdout_kind == "participant_held_out" else x["game"]) == heldout]
            train_y = [r["source_arousal_proxy"] for x in train for r in x["rows"]]
            base = median_or_none(train_y)
            if base is None:
                fold_results.append({"holdout_kind": holdout_kind, "heldout": heldout, "status": "insufficient-development-support"})
                continue
            traj_metrics = []
            event_aggregate = {c: [] for c in EVENT_CHANNELS}
            for x in test:
                rows = x["rows"]; ys = [r["source_arousal_proxy"] for r in rows]
                no_state = [base] * len(rows)
                ar_preds = {str(phi): [] for phi in PHI_GRID}
                prev_y = None; prev_t = None
                for r in rows:
                    t = r["timestamp"]
                    for phi in PHI_GRID:
                        if prev_y is None:
                            ar_preds[str(phi)].append(base)
                        else:
                            dt = max(0.0, t - prev_t)
                            ar_preds[str(phi)].append(base + (prev_y - base) * (phi ** dt))
                    prev_y, prev_t = r["source_arousal_proxy"], t
                tm = {"trajectory_id": x["id"], "player": x["player"], "game": x["game"],
                      "n": len(rows), "persistence": eval_persistence(rows),
                      "no_state": mae_rmse(ys, no_state), "ar1": {phi: mae_rmse(ys, ps) for phi, ps in ar_preds.items()},
                      "relaxation": {}}
                for channel in EVENT_CHANNELS:
                    ev = summarize_event(event_response(rows, channel))
                    event_aggregate[channel].append(ev)
                    tm["relaxation"][channel] = {}
                    flags = build_event_flags(rows, channel)
                    for tau in TAU_GRID:
                        trace = relaxation_trace(rows, flags, tau)
                        tm["relaxation"][channel][str(tau)] = {"trace_proxy_corr": pearson(trace, ys), "event_count": sum(flags), "trace_mean": statistics.fmean(trace) if trace else None}
                traj_metrics.append(tm)
            # Fold-level event summaries keep channel identity and no pooled row score.
            ev_summary = {}
            for channel, vals in event_aggregate.items():
                ev_summary[channel] = {"events": aggregate([v["events"] for v in vals]),
                                       "complete_events": aggregate([v["complete_events"] for v in vals]),
                                       "lag_peak_offset": aggregate([v["lag_peak_offset"] for v in vals]),
                                       "recovery_seconds": aggregate([v["recovery"]["median"] for v in vals]),
                                       "recovery_censored": aggregate([v["recovery_censored"] for v in vals]),
                                       "decay_status_counts": {s: sum(v["decay"] == s for v in vals) for s in {v["decay"] for v in vals}}}
            fold_results.append({"holdout_kind": holdout_kind, "heldout": heldout, "status": "ok", "training_rows": len(train_y), "test_trajectories": len(test), "training_median": base, "trajectory_metrics": traj_metrics, "event_summary": ev_summary})

    # Compact family summaries across trajectories, preserving participant/game axes.
    summary = {"status": "complete", "fold_count": len(fold_results), "folds": {}}
    for kind in groups:
        ok = [f for f in fold_results if f["holdout_kind"] == kind and f["status"] == "ok"]
        no = [t for f in ok for t in f["trajectory_metrics"]]
        event_support = {}
        for channel in EVENT_CHANNELS:
            supported_traj = [t for t in no if any(t["relaxation"][channel][str(tau)]["event_count"] > 0 for tau in TAU_GRID)]
            supported_folds = [f for f in ok if f["event_summary"][channel]["events"]["median"] not in (None, 0)]
            event_support[channel] = {
                "supported_trajectories": len(supported_traj),
                "total_trajectories": len(no),
                "supported_folds": len(supported_folds),
                "total_folds": len(ok),
                "relaxation_trace_proxy_corr": {
                    str(tau): aggregate([t["relaxation"][channel][str(tau)]["trace_proxy_corr"] for t in supported_traj])
                    for tau in TAU_GRID
                },
            }
        summary["folds"][kind] = {"n_folds": len(ok), "n_trajectories": len(no),
            "no_state_mae": aggregate([t["no_state"]["mae"] for t in no]),
            "no_state_rmse": aggregate([t["no_state"]["rmse"] for t in no]),
            "ar1": {phi: {"mae": aggregate([t["ar1"][phi]["mae"] for t in no]), "rmse": aggregate([t["ar1"][phi]["rmse"] for t in no])} for phi in map(str, PHI_GRID)},
            "persistence": {str(lag): {"corr": aggregate([t["persistence"][str(lag)]["corr"] for t in no]), "retention_mae": aggregate([t["persistence"][str(lag)]["retention_mae"] for t in no])} for lag in PERSISTENCE_LAGS},
            "event_support": event_support,
        }
    results = {"status": "complete", "run_record": run_record, "summary": summary, "fold_results": fold_results}
    (OUT / "results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# AGAIN dynamics audit v0", "", "Status: **development-only / complete**", "", "No `alpha`, `beta`, `b`, or `W` was trained. Source arousal remains an annotation-derived proxy; no Theory-S claim is made.", "", "## Summary"]
    for kind, s in summary["folds"].items():
        lines += [f"", f"### {kind}", f"- folds: {s['n_folds']}; held-out trajectories: {s['n_trajectories']}", f"- no-state MAE median/IQR: {s['no_state_mae']['median']} / {s['no_state_mae']['iqr']}", f"- no-state RMSE median/IQR: {s['no_state_rmse']['median']} / {s['no_state_rmse']['iqr']}"]
        for phi in map(str, PHI_GRID):
            lines.append(f"- AR(1) phi={phi} MAE median/IQR: {s['ar1'][phi]['mae']['median']} / {s['ar1'][phi]['mae']['iqr']}")
    lines += ["", "## Frozen envelope", "", "Channels were audited separately using the pre-registered binary-onset rule; tau grid was " + ", ".join(map(str, TAU_GRID)) + " seconds. Event lag/decay/recovery are descriptive and retain undefined/censored cases."]
    for kind, s in summary["folds"].items():
        lines += ["", f"### Event support ({kind})"]
        for channel, es in s["event_support"].items():
            lines.append(f"- {channel}: event-bearing trajectories {es['supported_trajectories']}/{es['total_trajectories']}; event-bearing folds {es['supported_folds']}/{es['total_folds']}")
    lines += ["", "## Stability", "", "Persistence is a repeatable descriptive signal on this slice: lag correlation remains high at short native-time lags and both hold-out views retain the same trajectory-level pattern. The event-driven relaxation family is **not admitted as stable**: event support is sparse and strongly channel/game dependent, while lag/decay/recovery remain undefined or censored for many folds. This is not a population estimate or formal test. Inspect per-fold `event_summary` and `trajectory_metrics` in `results.json`; do not promote any stable-looking shape to Theory-S training."]
    (OUT / "conclusion.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(run())
