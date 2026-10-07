#!/usr/bin/env python3
"""Audit the frozen one-day v4.3 exact-HEAD gate artifacts."""
import collections
import hashlib
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
EXPECTED_MODEL = "convaiinnovations/laya-typed-decisions"
EXPECTED_REV = "f9ab0b228f0fc0f14d873dbc99038f135c2da1b2"
EXPECTED_PROXY = "0b6c9b8c4e05119d13b0544be9890580eff7aba1d621387a08a72916f8fab74e"
EXPECTED_PROMPT = "character-dynamics-laya-typed-v4.3"
EXPECTED_PROTOCOL = "laya-typed-v4"


def load_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def audit_arm(name):
    arm = ROOT / name
    cassette = load_jsonl(arm / "live-cassette.jsonl")
    trace = load_jsonl(arm / "live-trace.jsonl")
    request_rows = []
    violations = []
    for n, row in enumerate(cassette, 1):
        q = row["request"]
        tb = row["token_budget"]
        obs = {x[0]: x[1:] for x in q["observation"]}
        t = int(q["timestamp"])
        day, minute = divmod(t, 1440)
        clock_expected = f"Day {day + 1} {minute // 60:02d}:{minute % 60:02d}"
        clock = obs.get("clock.time", [None, None])
        total = obs.get("clock.total_minutes", [None, None])
        clock_ok = clock == [clock_expected, "k"] and total == [str(t), "k"]
        candidates = q["candidates"]
        actions = [c["action"] for c in candidates]
        probs = row["probabilities"]
        raw = row["raw_answer"]
        runtime_action = next((r.get("selected_action") for r in trace
                               if r.get("type") == "boundary" and r.get("policy_evaluated")
                               and int(r.get("timestamp", -1)) == t), "")
        prob_sum = sum(float(v) for v in probs.values())
        prob_ok = (set(actions) == set(probs) and len(actions) == len(set(actions))
                   and all(math.isfinite(float(v)) and 0 <= float(v) <= 1 for v in probs.values())
                   and abs(prob_sum - 1.0) <= 0.003 and raw.get("type") == "choice"
                   and raw.get("choice") in set(actions)
                   and set(raw.get("probabilities", {})) == set(actions))
        duration_ok = all(isinstance(c.get("planned_minutes"), (int, float))
                          and c["planned_minutes"] > 0 for c in candidates)
        observation_ok = all(len(fact) == 3 and fact[2] in {"k", "s"} for fact in q["observation"])
        targets_ok = all(not c["target"] or obs.get("object." + c["target"], [None, None])[0] == "present"
                         and obs.get("object." + c["target"], [None, None])[1] == "k" for c in candidates)
        sampled_support_ok = runtime_action in actions and float(probs.get(runtime_action, 0)) > 0
        state_margin = min(tb["state_budgets"]) - tb["state_tokens"]
        input_margin = tb["max_len"] - tb["max_input_tokens"]
        head_margins = [b - h for b, h in zip(tb["head_budgets"], tb["question_head_tokens"])]
        head_margin = min(head_margins)
        token_ok = (state_margin >= 0 and input_margin >= 0 and head_margin >= 0
                    and all(n <= 48 for group in tb["option_tokens"] for n in group))
        h1 = q["recent_history"]["episodes"]
        events = q["recent_history"]["observed_events"]
        summary = q["recent_factual_summary"]
        h1_starts = [int(e[2]) for e in h1]
        observation_keys = set(obs)
        h1_ok = (len(h1) <= 16 and h1_starts == sorted(h1_starts)
                 and all(0 <= t - (int(e[2]) + int(e[3])) <= 12 * 60 for e in h1)
                 and all(len(e) >= 6 and e[0] and int(e[3]) >= 0 and int(e[4]) > 0
                         and e[5] in {"s", "i", "r"} for e in h1)
                 and all(e[5] != "r" or int(e[3]) == 0 for e in h1)
                 and len(events) <= 2 and all(0 <= t - int(e[0]) <= 12 * 60 and e[1] in observation_keys
                                              for e in events))
        if name == "no_history":
            h1_ok = h1_ok and not h1 and not events and not summary["actions"] and summary["last_sleep"] is None
        history_facts_ok = True
        if name == "history":
            totals = {a[0]: int(a[1]) for a in summary["actions"]}
            for action in set(e[0] for e in h1):
                h1_minutes = sum(int(e[3]) for e in h1 if e[0] == action and e[5] != "r")
                if totals.get(action, 0) < h1_minutes:
                    history_facts_ok = False
                accepted = [e for e in h1 if e[0] == action and e[5] != "r"]
                h2_row = next((a for a in summary["actions"] if a[0] == action), None)
                if accepted and h2_row is not None:
                    latest_end = max(int(e[2]) + int(e[3]) for e in accepted)
                    if int(h2_row[2]) != t - latest_end:
                        history_facts_ok = False
            sleeps = [e for e in h1 if e[0] == "sleep_at_bed" and e[5] != "r"]
            if sleeps:
                latest = max(sleeps, key=lambda e: int(e[2]) + int(e[3]))
                history_facts_ok = history_facts_ok and summary["last_sleep"] == [int(latest[3]), int(latest[2]) + int(latest[3])]
        allowed_request_keys = {"request_id", "timestamp", "profile", "personality", "state", "running_action",
                                "recent_history", "recent_factual_summary", "observation", "candidates",
                                "protocol_version", "prompt_version"}
        boundary_ok = (set(q) == allowed_request_keys
                       and all(set(c) == {"action", "target", "planned_minutes"} for c in candidates)
                       and "world" not in q and "rule" not in q and "rule_activation" not in q)
        identity_ok = (row["model"] == EXPECTED_MODEL and row["checkpoint_revision"] == EXPECTED_REV
                       and row["proxy_source_sha256"] == EXPECTED_PROXY
                       and row["protocol_version"] == EXPECTED_PROTOCOL and row["prompt_version"] == EXPECTED_PROMPT
                       and row["type"] == "laya_typed_choice")
        checks = {"clock": clock_ok, "O_visibility": observation_ok and targets_ok,
                  "pi_and_candidates": prob_ok, "durations": duration_ok,
                  "runtime_sample_support": sampled_support_ok,
                  "tokens": token_ok, "history_window": h1_ok, "history_summary": history_facts_ok,
                  "boundary": boundary_ok, "identity_result_type": identity_ok}
        for label, ok in checks.items():
            if not ok:
                violations.append(f"{name} request {n}: {label}")
        request_rows.append({"arm": name, "request": q["request_id"], "timestamp": t,
                             "clock": clock[0], "clock_ok": clock_ok,
                             "candidate_count": len(candidates),
                             "candidates_json": json.dumps(candidates, separators=(",", ":")),
                             "planned_duration_min": min(c["planned_minutes"] for c in candidates),
                             "planned_duration_max": max(c["planned_minutes"] for c in candidates),
                             "raw_pi_sum": round(prob_sum, 8),
                             "raw_pi_json": json.dumps(probs, sort_keys=True, separators=(",", ":")),
                             "raw_answer_choice": raw.get("choice"),
                             "runtime_sampled_action": runtime_action,
                             "state_tokens": tb["state_tokens"], "state_budget": min(tb["state_budgets"]),
                             "state_margin": state_margin, "full_input_tokens": tb["max_input_tokens"],
                             "full_input_limit": tb["max_len"], "full_input_margin": input_margin,
                             "question_head_tokens": max(tb["question_head_tokens"]),
                             "question_head_margin": head_margin, "H1_episodes": len(h1),
                             "H2_action_types": len(summary["actions"]),
                             "all_checks_pass": all(checks.values())})
    boundaries = [r for r in trace if r.get("type") == "boundary"]
    decisions = [r for r in boundaries if r.get("policy_evaluated")]
    selected = [r.get("selected_action") for r in decisions if r.get("selected_action")]
    daily = next(r for r in trace if r.get("type") == "daily")
    run = next(r for r in trace if r.get("type") == "run")
    sleep_running = sum(int(r.get("elapsed_minutes", 0)) for r in boundaries
                        if r.get("running_action_before") == "sleep_at_bed")
    rest_running = sum(int(r.get("elapsed_minutes", 0)) for r in boundaries
                       if r.get("running_action_before") == "rest_at_bed")
    study_running = sum(int(r.get("elapsed_minutes", 0)) for r in boundaries
                        if r.get("running_action_before") in {"study_focused", "study_halfhearted", "study_at_computer"})
    switches = sum(a != b for a, b in zip(selected, selected[1:]))
    initial_state = next((r.get("state") for r in boundaries if r.get("state")), None)
    final_state = daily["state"]
    states = [r["state"] for r in boundaries if isinstance(r.get("state"), dict)] + [final_state]
    need_ranges = {key: [min(float(s[key]) for s in states), max(float(s[key]) for s in states)]
                   for key in ("hunger", "bathroom_urge", "fatigue", "screen_strain", "anxiety", "task_pressure")}
    arm_requests = [r for r in request_rows if r["arm"] == name]
    trace_hash = sha(arm / "live-trace.jsonl")
    replay_hash = sha(arm / "replay-trace.jsonl")
    trace_identical = (arm / "live-trace.jsonl").read_bytes() == (arm / "replay-trace.jsonl").read_bytes()
    if not trace_identical:
        violations.append(f"{name}: live/replay trace mismatch")
    behavior = {"profile": run["profile_id"], "scenario_seed": run["scenario_seed"],
                "policy_seed": run["policy_seed"], "days": run["days"],
                "boundaries": len(boundaries), "policy_decisions": len(decisions),
                "action_counts": dict(collections.Counter(selected)), "distinct_actions": len(set(selected)),
                "consecutive_switches": switches, "switch_rate": round(switches / max(1, len(selected) - 1), 4),
                "sleep_summary_minutes": daily.get("sleep_minutes"), "sleep_running_minutes": sleep_running,
                "rest_summary_minutes": daily.get("rest_minutes"), "rest_running_minutes": rest_running,
                "study_summary_minutes": daily.get("study_minutes"), "study_running_minutes": study_running,
                "leisure_minutes": daily.get("leisure_minutes"), "idle_minutes": daily.get("idle_minutes"),
                "bodily_minutes": daily.get("bodily_minutes"), "task_completions": daily.get("task_completions"),
                "task_assignments": daily.get("task_assignments"), "task_effort": daily.get("task_effort"),
                "task_effort_target": daily.get("task_effort_target"),
                "runtime_rejections": sum(len(r.get("runtime_rejections", [])) for r in boundaries),
                "raw_answer_choice_matches_runtime_sample": sum(
                    r["raw_answer_choice"] == r["runtime_sampled_action"] for r in arm_requests),
                "raw_answer_choice_differs_from_runtime_sample": sum(
                    r["raw_answer_choice"] != r["runtime_sampled_action"] for r in arm_requests),
                "min_state_margin": min(r["state_margin"] for r in arm_requests),
                "min_full_input_margin": min(r["full_input_margin"] for r in arm_requests),
                "min_question_head_margin": min(r["question_head_margin"] for r in arm_requests),
                "initial_state": run["initial_state"], "need_ranges": need_ranges,
                "selected_action_rows": [{"timestamp": r["timestamp"], "action": r.get("selected_action"),
                                          "target": r.get("selected_target"),
                                          "running_before": r.get("running_action_before"),
                                          "started_at": r.get("running_action_started_at"),
                                          "pre_rejections": r.get("runtime_rejections", [])} for r in decisions],
                "final_state": final_state, "trace_lines": len(trace),
                "trace_sha256": trace_hash, "replay_sha256": replay_hash,
                "trace_byte_identical": trace_identical,
                "cassette_rows": len(cassette), "cassette_sha256": sha(arm / "live-cassette.jsonl")}
    return behavior, request_rows, violations


all_requests = []
summaries = {}
violations = []
for arm in ("no_history", "history"):
    summary, requests, issues = audit_arm(arm)
    summaries[arm] = summary
    all_requests.extend(requests)
    violations.extend(issues)

rule_rows = load_jsonl(ROOT / "rule/trace.jsonl")
rule_boundaries = [r for r in rule_rows if r.get("type") == "boundary"]
rule_daily = next(r for r in rule_rows if r.get("type") == "daily")
rule_decisions = [r for r in rule_boundaries if r.get("policy_evaluated")]
rule_selected = [r.get("selected_action") for r in rule_decisions if r.get("selected_action")]
rule_sleep = sum(int(r.get("elapsed_minutes", 0)) for r in rule_boundaries
                 if r.get("running_action_before") == "sleep_at_bed")
summaries["rule"] = {"boundaries": len(rule_boundaries), "policy_decisions": len(rule_decisions),
                      "action_counts": dict(collections.Counter(rule_selected)),
                      "sleep_summary_minutes": rule_daily.get("sleep_minutes"), "sleep_running_minutes": rule_sleep,
                      "rest_minutes": rule_daily.get("rest_minutes"), "study_minutes": rule_daily.get("study_minutes"),
                      "task_completions": rule_daily.get("task_completions"),
                      "task_assignments": rule_daily.get("task_assignments"), "task_effort": rule_daily.get("task_effort"),
                      "task_effort_target": rule_daily.get("task_effort_target"),
                      "runtime_rejections": sum(len(r.get("runtime_rejections", [])) for r in rule_boundaries),
                      "trace_lines": len(rule_rows), "trace_sha256": sha(ROOT / "rule/trace.jsonl")}

with (ROOT / "REQUEST_AUDIT.tsv").open("w") as f:
    fields = list(all_requests[0])
    f.write("\t".join(fields) + "\n")
    for row in all_requests:
        f.write("\t".join(str(row[k]) for k in fields) + "\n")

result = {"summaries": summaries, "request_audit_rows": len(all_requests),
          "request_checks_all_pass": all(r["all_checks_pass"] for r in all_requests),
          "violations": violations}
(ROOT / "audit.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n")
print(json.dumps(result, indent=2, ensure_ascii=False))
if violations:
    sys.exit(1)
