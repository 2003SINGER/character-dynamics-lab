#!/usr/bin/env python3
"""Single-event remove counterfactual for LIGHT dev replay.

For each chosen target prediction t, factual uses all previous human actions.
Counterfactual removes exactly one previous action at remove_t while keeping:
- source trajectory and current O/candidates,
- semantic rules,
- initial state/personality,
- scorer,
- all other previous actions.
Outputs Delta-S, Delta-p(A*), and Delta-NLL.
"""
from __future__ import annotations
import argparse, importlib.util, json, subprocess
from pathlib import Path

def load_runner(path: Path):
    spec = importlib.util.spec_from_file_location("light_runner", path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod

def build_protocol_with_removal(rec, rules, runner, remove_t: int):
    lines = [f"RESET\t{rec['trajectory_id']}"]
    previous = runner.zero_semantics()
    meta = {}

    for step in rec.get("steps", []):
        t = int(step["t"])
        action = step.get("source_action_A_star")
        current_history = (
            runner.source_action_semantics(action, step.get("source_O"), rules)
            if action is not None else runner.zero_semantics()
        )

        candidates = step.get("candidate_set_factual")
        if isinstance(candidates, list) and candidates and action is not None:
            gold = runner.gold_index(candidates, action)
            if gold is not None:
                compiled = [
                    runner.compile_candidate(c, step.get("source_O"), rules)[0]
                    for c in candidates
                ]
                history = previous
                lines.append(
                    "STEP\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}".format(
                        rec["trajectory_id"], t,
                        history["goal_progress"], history["stimulation"],
                        history["recovery"], history["short_term_reward"],
                        history["environment_control"], len(candidates), gold
                    )
                )
                for feat in compiled:
                    lines.append(
                        "C\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t0".format(
                            feat["goal_progress"], feat["stimulation"], feat["recovery"],
                            feat["hunger_relief"], feat["bathroom_relief"],
                            feat["short_term_reward"], feat["environment_control"],
                            feat["context_relevance"]
                        )
                    )
                meta[t] = {
                    "source_action_A_star": action,
                    "candidate_set_factual": candidates,
                    "gold_index": gold,
                }

        # Remove the selected action only from future state history.
        previous = runner.zero_semantics() if t == remove_t else current_history

    return "\n".join(lines) + "\n", meta

def state_delta(a: dict, b: dict):
    return {k: b[k] - a[k] for k in a}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("replay", type=Path)
    ap.add_argument("core_exe", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--rules", type=Path, required=True)
    ap.add_argument("--runner", type=Path, required=True)
    ap.add_argument("--max-trajectories", type=int, default=20)
    args = ap.parse_args()

    runner = load_runner(args.runner)
    rules = json.loads(args.rules.read_text(encoding="utf-8"))
    rows = []
    trajectories = 0

    for rec in runner.iter_records(args.replay):
        if rec.get("source_dataset") != "LIGHT":
            continue
        if rec.get("source_episode_context", {}).get("quarantine"):
            continue
        trajectories += 1

        # Find scored action steps and remove the immediately preceding source
        # action for each eligible target.
        steps = [s for s in rec.get("steps", [])
                 if s.get("source_action_A_star") is not None]
        if len(steps) < 2:
            if trajectories >= args.max_trajectories:
                break
            continue

        factual_protocol, factual_meta, _ = runner.protocol_for([rec], rules, True)
        factual = runner.run_core(args.core_exe, factual_protocol)

        for idx in range(1, len(steps)):
            remove_t = int(steps[idx-1]["t"])
            target_t = int(steps[idx]["t"])
            key = (str(rec["trajectory_id"]), target_t)
            if key not in factual:
                continue

            cf_protocol, cf_meta = build_protocol_with_removal(
                rec, rules, runner, remove_t
            )
            counter = runner.run_core(args.core_exe, cf_protocol)
            if key not in counter:
                continue

            f = factual[key]
            c = counter[key]
            rows.append({
                "trajectory_id": rec["trajectory_id"],
                "remove_t": remove_t,
                "target_t": target_t,
                "removed_action": steps[idx-1].get("source_action_A_star"),
                "target_A_star": steps[idx].get("source_action_A_star"),
                "factual": f,
                "counterfactual_remove": c,
                "delta_state_counter_minus_factual":
                    state_delta(f["state_at_decision"], c["state_at_decision"]),
                "delta_gold_probability_counter_minus_factual":
                    c["gold_probability"] - f["gold_probability"],
                "delta_nll_counter_minus_factual":
                    c["nll"] - f["nll"],
                "intervention": "remove exactly one previous human-action semantic update",
            })

        if trajectories >= args.max_trajectories:
            break

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                for row in rows),
        encoding="utf-8"
    )
    print(json.dumps({
        "trajectory_count": trajectories,
        "counterfactual_pairs": len(rows),
        "output": str(args.output),
    }, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
