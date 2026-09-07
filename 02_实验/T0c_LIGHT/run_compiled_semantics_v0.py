#!/usr/bin/env python3
"""LIGHT dev diagnostic using Character Dynamics replay_core.

At prediction t:
- current O_t and current candidate strings may be used;
- human actions only through t-1 may update persistent S;
- A*_t is used only after candidate features/probabilities exist, to score p(A*).
"""
from __future__ import annotations
import argparse, hashlib, json, math, re, statistics, subprocess, sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Replay"))
from scene_snapshot_v0 import compile_light_step

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
STOP = {"a","an","the","to","from","at","in","on","with","of","for","into","onto",
        "my","your","his","her","their","this","that","up","down","over","under"}
FEATURES = (
    "goal_progress","stimulation","recovery","hunger_relief","bathroom_relief",
    "short_term_reward","environment_control"
)

def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def iter_records(path: Path):
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        for line in text.splitlines():
            if line.strip():
                yield json.loads(line)
        return
    if isinstance(data, list):
        yield from data
    elif isinstance(data, dict):
        yield data
    else:
        raise ValueError("Replay input must be JSON object/list or JSONL")

def words(value) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    return TOKEN_RE.findall(value.casefold())

def zero_semantics():
    return {key: 0.0 for key in FEATURES}

def compile_candidate(action, context, rules):
    tokens = words(action)
    first = tokens[0] if tokens else ""
    feat = {key: float(rules["default_features"].get(key, 0.0))
            for key in FEATURES}
    matched = None
    for group in rules["groups"]:
        if first in group["verbs"]:
            matched = group["name"]
            for key, value in group.get("features", {}).items():
                if key in feat:
                    feat[key] = max(feat[key], float(value))

    context_words = set(words(context))
    content = [w for w in tokens[1:] if w not in STOP]
    feat["context_relevance"] = (
        len(set(content) & context_words) / len(set(content))
        if content else 0.0
    )
    return feat, matched

def compile_candidate_scene_aware(action, snapshot, rules):
    """v1 diagnostic: bind candidate target through canonical SceneSnapshot."""
    feat, matched = compile_candidate(action, snapshot.get("actor_observation"), rules)
    tokens = words(action)
    target = set(w for w in tokens[1:] if w not in STOP)
    entities = snapshot.get("entities") or []
    scene_labels = [str(x.get("label", "")) for x in entities]
    scene_words = set(words(scene_labels))
    obs_words = set(words(snapshot.get("actor_observation")))
    inventory_words = set(words([p.get("entity", "") for p in snapshot.get("possessions") or []]))
    matched_scene = bool(target) and bool(target & scene_words)
    visible = bool(target) and target.issubset(obs_words)
    carried = bool(target) and target.issubset(inventory_words)
    bias = 0.0
    if target and not matched_scene:
        bias -= 0.35
    if visible:
        feat["context_relevance"] = max(feat["context_relevance"], 1.0)
        bias += 0.08
    if carried and tokens and tokens[0] in {"get", "take", "steal"}:
        feat["goal_progress"] *= 0.25
        bias -= 0.12
    target_entity_id = next((x.get("id") for x in entities if target & set(words(x.get("label")))), None)
    return feat, matched, bias, {
        "target_entity_id": target_entity_id,
        "target_in_scene": matched_scene,
        "target_visible_in_O": visible,
        "target_in_inventory": carried,
        "affordance_source": "source_candidate_only" if snapshot.get("source_candidates") else "none",
        "scene_bias": bias,
    }

def source_action_semantics(action, context, rules):
    feat, _ = compile_candidate(action, context, rules)
    return {key: feat[key] for key in FEATURES}

def gold_index(candidates, action):
    target = str(action).strip()
    exact = [i for i, c in enumerate(candidates) if str(c).strip() == target]
    if len(exact) == 1:
        return exact[0]
    folded = target.casefold()
    hits = [i for i, c in enumerate(candidates)
            if str(c).strip().casefold() == folded]
    return hits[0] if len(hits) == 1 else None

def protocol_for(selected, rules, stateful: bool, scene_aware: bool = False):
    lines = []
    meta = {}
    counts = Counter()

    for rec in selected:
        tid = str(rec["trajectory_id"])
        lines.append(f"RESET\t{tid}")
        previous = zero_semantics()

        for step in rec.get("steps", []):
            snapshot = compile_light_step(rec, step) if scene_aware else None
            action = step.get("source_action_A_star")
            if action is not None and scene_aware:
                current_history = compile_candidate_scene_aware(action, snapshot, rules)[0]
            else:
                current_history = (source_action_semantics(action, step.get("source_O"), rules)
                                   if action is not None else zero_semantics())

            candidates = step.get("candidate_set_factual")
            if not isinstance(candidates, list) or not candidates or action is None:
                counts["skip_missing_candidate_or_action"] += 1
                if stateful and action is not None:
                    lines.append("UPDATE\t{}\t{}\t{}\t{}\t{}\t{}".format(
                        tid, current_history["goal_progress"], current_history["stimulation"],
                        current_history["recovery"], current_history["short_term_reward"],
                        current_history["environment_control"]))
                previous = current_history
                continue

            gold = gold_index(candidates, action)
            if gold is None:
                counts["skip_gold_not_unique_in_candidates"] += 1
                if stateful and action is not None:
                    lines.append("UPDATE\t{}\t{}\t{}\t{}\t{}\t{}".format(
                        tid, current_history["goal_progress"], current_history["stimulation"],
                        current_history["recovery"], current_history["short_term_reward"],
                        current_history["environment_control"]))
                previous = current_history
                continue

            compiled = []
            groups = []
            biases = []
            scene_bindings = []
            for candidate in candidates:
                if scene_aware:
                    feat, group, bias, scene_flags = compile_candidate_scene_aware(candidate, snapshot, rules)
                else:
                    feat, group = compile_candidate(candidate, step.get("source_O"), rules)
                    bias, scene_flags = 0.0, {}
                compiled.append(feat)
                groups.append(group)
                biases.append(bias)
                scene_bindings.append(scene_flags)
                counts["candidate_total"] += 1
                if group is None:
                    tok = words(candidate)
                    counts[f"unmapped::{tok[0] if tok else '<empty>'}"] += 1
                else:
                    counts["candidate_semantic_mapped"] += 1

            history = previous if stateful else zero_semantics()
            t = int(step["t"])
            lines.append(
                "PREDICT\t{}\t{}\t{}".format(
                    tid, t, len(candidates)
                )
            )
            for feat, bias in zip(compiled, biases):
                lines.append(
                    "C\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}".format(
                        feat["goal_progress"],
                        feat["stimulation"],
                        feat["recovery"],
                        feat["hunger_relief"],
                        feat["bathroom_relief"],
                        feat["short_term_reward"],
                        feat["environment_control"],
                        feat["context_relevance"],
                        bias,
                    )
                )

            if stateful and action is not None:
                lines.append("UPDATE\t{}\t{}\t{}\t{}\t{}\t{}".format(
                    tid, current_history["goal_progress"],
                    current_history["stimulation"], current_history["recovery"],
                    current_history["short_term_reward"],
                    current_history["environment_control"]))

            meta[(tid, t)] = {
                "trajectory_id": tid,
                "t": t,
                "source_record_id": rec.get("source_record_id"),
                "source_O": step.get("source_O"),
                "source_action_A_star": action,
                "candidate_set_factual": candidates,
                "gold_index": gold,
                "candidate_semantics": compiled,
                "candidate_semantic_groups": groups,
                "latest_update_semantics": dict(current_history),
                "scene_aware": scene_aware,
                "candidate_scene_bindings": scene_bindings if scene_aware else None,
            }
            previous = current_history
            counts["scored_steps"] += 1

    return "\n".join(lines) + "\n", meta, counts

def run_core(executable: Path, protocol: str):
    proc = subprocess.run([str(executable)], input=protocol, text=True,
                          capture_output=True, check=True)
    result = {}
    for line in proc.stdout.splitlines():
        if not line.startswith("RESULT\t"):
            continue
        f = line.split("\t")
        if len(f) != 13:
            raise RuntimeError(f"unexpected RESULT field count: {len(f)}")
        probs = [float(x) for x in f[12].split(",")] if f[12] else []
        result[(f[1], int(f[2]))] = {
            "state_at_decision": {
                "boredom": float(f[3]), "fatigue": float(f[4]), "task_pressure": float(f[5]),
                "satisfaction": float(f[6]), "hunger": float(f[7]), "bathroom_urge": float(f[8]),
                "anxiety": float(f[9]), "screen_strain": float(f[10]), "purchase_urge": float(f[11]),
            },
            "candidate_probabilities": probs,
        }
    return result

def score_results(raw, meta):
    out = {}
    for key, item in raw.items():
        gold = meta[key]["gold_index"]
        probs = item["candidate_probabilities"]
        p = probs[gold]
        rank = 1 + sum(x > p + 1e-12 for x in probs)
        out[key] = dict(item, gold_probability=p, nll=-math.log(max(p, 1e-300)), rank=rank)
    return out

def git_meta():
    try:
        revision = subprocess.check_output(["git","rev-parse","HEAD"], text=True).strip()
        dirty = bool(subprocess.check_output(["git","status","--porcelain"], text=True).strip())
        return revision, dirty
    except Exception:
        return "unknown", None

def summarize(rows):
    if not rows:
        return {"scored_steps": 0}
    sf = [r["stateful"]["nll"] for r in rows]
    nh = [r["no_history"]["nll"] for r in rows]
    un = [math.log(len(r["candidate_set_factual"])) for r in rows]
    ranks = [r["stateful"]["rank"] for r in rows]
    return {
        "scored_steps": len(rows),
        "stateful_mean_nll": statistics.fmean(sf),
        "stateful_mean_nll_bits": statistics.fmean(sf) / math.log(2),
        "no_history_mean_nll": statistics.fmean(nh),
        "uniform_mean_nll": statistics.fmean(un),
        "mean_no_history_minus_stateful_nll":
            statistics.fmean(b - a for a, b in zip(sf, nh)),
        "stateful_top1_accuracy": sum(r == 1 for r in ranks) / len(ranks),
        "stateful_mrr": statistics.fmean(1.0 / r for r in ranks),
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("replay", type=Path)
    ap.add_argument("core_exe", type=Path)
    ap.add_argument("output_dir", type=Path)
    ap.add_argument("--rules", type=Path,
                    default=Path(__file__).with_name("compiled_semantics_v0.json"))
    ap.add_argument("--max-trajectories", type=int, default=50)
    ap.add_argument("--scene-aware", action="store_true")
    args = ap.parse_args()

    rules = json.loads(args.rules.read_text(encoding="utf-8"))
    selected = []
    quarantined_seen = 0
    for rec in iter_records(args.replay):
        if rec.get("source_dataset") != "LIGHT":
            continue
        if rec.get("source_episode_context", {}).get("quarantine"):
            quarantined_seen += 1
            continue
        selected.append(rec)
        if len(selected) >= args.max_trajectories:
            break
    if not selected:
        raise SystemExit("no non-quarantined LIGHT trajectories selected")

    stateful_protocol, meta, counts = protocol_for(selected, rules, True, args.scene_aware)
    nohist_protocol, meta_nh, _ = protocol_for(selected, rules, False, args.scene_aware)
    if set(meta) != set(meta_nh):
        raise RuntimeError("stateful/no-history scored-step sets differ")

    stateful = score_results(run_core(args.core_exe, stateful_protocol), meta)
    nohist = score_results(run_core(args.core_exe, nohist_protocol), meta_nh)
    if set(meta) != set(stateful) or set(meta) != set(nohist):
        raise RuntimeError("replay_core results do not match protocol step keys")

    rows = []
    for key, source in meta.items():
        row = dict(source)
        row["semantic_rules_version"] = rules["version"] + ("+scene-aware-v1" if args.scene_aware else "")
        row["stateful"] = stateful[key]
        row["no_history"] = nohist[key]
        row["uniform_nll"] = math.log(len(row["candidate_set_factual"]))
        row["paired_no_history_minus_stateful_nll"] = (
            row["no_history"]["nll"] - row["stateful"]["nll"]
        )
        rows.append(row)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    trace = args.output_dir / "LIGHT_compiled_semantics_v0.trace.jsonl"
    trace.write_text(
        "".join(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
                for row in rows),
        encoding="utf-8"
    )

    summary = summarize(rows)
    summary["semantic_candidate_coverage"] = (
        counts["candidate_semantic_mapped"] / counts["candidate_total"]
        if counts["candidate_total"] else None
    )
    summary["quarantined_trajectories_seen_before_limit"] = quarantined_seen
    summary["skips"] = {k:v for k,v in counts.items() if k.startswith("skip_")}
    summary["top_unmapped_first_tokens"] = [
        {"token": k.split("::",1)[1], "count": v}
        for k,v in counts.most_common()
        if k.startswith("unmapped::")
    ][:30]
    (args.output_dir / "LIGHT_compiled_semantics_v0.summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    revision, dirty = git_meta()
    core_version = subprocess.check_output(
        [str(args.core_exe), "--version"], text=True
    ).strip()
    manifest = {
        "schema_version": "character_dynamics_experiment_manifest_v0",
        "purpose": "LIGHT dev diagnostic: ReplayRecord -> fixed semantics -> X -> U -> S -> source candidate scorer -> A* NLL",
        "research_status": "dev_diagnostic_only_not_semantic_admission",
        "git_revision": revision,
        "git_worktree_dirty": dirty,
        "source_replay": str(args.replay),
        "source_replay_sha256": sha256(args.replay),
        "semantic_rules": str(args.rules),
        "semantic_rules_sha256": sha256(args.rules),
        "semantic_rules_version": rules["version"] + ("+scene-aware-v1" if args.scene_aware else ""),
        "semantic_frontend": "scene-aware-v1" if args.scene_aware else "verb-only-v0",
        "replay_core_version": core_version,
        "selected_trajectory_count": len(selected),
        "max_trajectories": args.max_trajectories,
        "trace_sha256": sha256(trace),
        "information_rule": "At prediction t, state may use human actions only through t-1; A*_t is held out until scoring.",
        "candidate_rule": "Every current candidate is featurized without reference to which candidate is A*; source candidate_set_factual is not relabelled A^O.",
        "conditions": ["stateful","no_history","uniform"],
    }
    (args.output_dir / "LIGHT_compiled_semantics_v0.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )

    print(json.dumps({"summary": summary, "manifest": manifest},
                     ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
