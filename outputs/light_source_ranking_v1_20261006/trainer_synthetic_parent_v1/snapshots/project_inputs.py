#!/usr/bin/env python3
"""Project pinned before-turn records into a non-training source-ranking contract."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "outputs/light_before_turn_20261006/run_v1/before_turn_candidates.jsonl"
OUTPUT = ROOT / "outputs/light_source_ranking_v1_20261006/contract_v1"
INPUT_SHA256 = "b414f176bf7c6d0e1f47536bab8c251ae7d39ead5b40550310127294f74e5646"
SCHEMA = "light_before_turn_feasibility_v1"
CHANNELS = ("speech", "action", "emote")
RECORD_KEYS = {"schema", "candidate_model_payload", "candidate_surface", "supervision",
               "source_history_holdback", "admission", "provenance"}
PAYLOAD_KEYS = {"self_persona", "prior_interaction_history", "recorded_environment_snapshot"}
HISTORY_KEYS = {"role", "speech", "action", "emote"}
PROVENANCE_KEYS = {"trajectory_id", "episode_index", "actor", "target_raw_turn_index",
                   "target_physical_index", "target_source_ref", "split_bucket", "split",
                   "prior_same_actor_physical_turns", "payload_history_turn_refs",
                   "self_persona_agent_index", "self_persona_matched_name",
                   "self_persona_source_ref", "source_fields", "model_must_not_read"}
REF_KEYS = {"raw_turn_index", "physical_index", "role", "speaker", "source_ref"}
ADMISSION_KEYS = {"overall", "training_authorized", "self_persona", "prior_self_speech", "prior_self_action",
                  "prior_self_emote", "prior_partner_speech", "prior_partner_emote", "prior_partner_action",
                  "recorded_environment_snapshot", "recorded_support", "time_safe_does_not_imply_information_authorized", "not_claimed"}
HOLDBACK_KEYS = {"partner_persona", "all_descriptions", "future_turns", "same_turn_speech_action_emote"}
OUT_SCHEMA = "light_source_ranking_input_contract_v1"
CONTRACT = {"schema": OUT_SCHEMA, "task": "DEVELOPMENT_SOURCE_CONDITIONAL_COMMAND_RANKING",
            "input_features": ["self_persona", "recorded_environment_snapshot", "history_views.core",
                               "history_views.diagnostic_plus_partner_raw_commands", "recorded_support"],
            "supervision_only": ["recorded_action"], "training_authorized": False,
            "actor_forecast_admitted": False, "paper0_admission": False,
            "no_current_context": "source covariate ablation only; not a temporal permission proof"}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _exact_keys(value: Any, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise ValueError(f"{label} keys/schema mismatch")


def _split(trajectory_id: str) -> tuple[int, str]:
    bucket = int(hashlib.sha256(trajectory_id.encode()).hexdigest()[:8], 16) % 10
    return bucket, "train" if bucket < 7 else "validation" if bucket < 9 else "excluded_bucket9"


def _text_or_null(value: Any, label: str, *, nonempty: bool = False) -> None:
    if value is not None and (not isinstance(value, str) or (nonempty and not value.strip())):
        raise ValueError(f"{label} must be {'nonempty ' if nonempty else ''}string or null")


def validate_record(r: Any, line_no: int) -> None:
    _exact_keys(r, RECORD_KEYS, f"line {line_no} record")
    if r["schema"] != SCHEMA:
        raise ValueError(f"line {line_no}: unexpected upstream schema")
    p, surf, sup, prov = (r["candidate_model_payload"], r["candidate_surface"],
                          r["supervision"], r["provenance"])
    _exact_keys(p, PAYLOAD_KEYS, f"line {line_no} payload")
    _exact_keys(surf, {"recorded_support"}, f"line {line_no} surface")
    _exact_keys(sup, {"recorded_action", "admission"}, f"line {line_no} supervision")
    _exact_keys(prov, PROVENANCE_KEYS, f"line {line_no} provenance")
    if not isinstance(p["self_persona"], str) or not p["self_persona"].strip() or not isinstance(p["recorded_environment_snapshot"], str) or not p["recorded_environment_snapshot"].strip():
        raise ValueError(f"line {line_no}: invalid permitted feature strings")
    support = surf["recorded_support"]
    if not isinstance(support, list) or any(not isinstance(x, str) or not x.strip() for x in support):
        raise ValueError(f"line {line_no}: support must be a list of strings")
    if not isinstance(sup["recorded_action"], str) or not sup["recorded_action"].strip():
        raise ValueError(f"line {line_no}: gold must be a nonempty string")
    if sup["admission"] != "SOURCE_LABEL_NOT_INPUT":
        raise ValueError(f"line {line_no}: unexpected supervision admission")
    if not isinstance(r["admission"], dict) or r["admission"].get("training_authorized") is not False:
        raise ValueError(f"line {line_no}: training must remain unauthorized")
    _exact_keys(r["admission"], ADMISSION_KEYS, f"line {line_no} admission")
    _exact_keys(r["source_history_holdback"], HOLDBACK_KEYS, f"line {line_no} holdback")
    traj, actor = prov["trajectory_id"], prov["actor"]
    if not isinstance(traj, str) or not traj or not isinstance(actor, str) or not actor:
        raise ValueError(f"line {line_no}: invalid source key strings")
    bucket, split = _split(traj)
    if prov["split_bucket"] != bucket or prov["split"] != split:
        raise ValueError(f"line {line_no}: split/hash mismatch")
    if any(type(prov[k]) is not int or prov[k] < 0 for k in ("episode_index", "target_raw_turn_index", "target_physical_index")):
        raise ValueError(f"line {line_no}: invalid target indices")
    _exact_keys(prov["source_fields"], {"recorded_environment_snapshot", "recorded_support", "recorded_action"}, f"line {line_no} source fields")
    history, refs = p["prior_interaction_history"], prov["payload_history_turn_refs"]
    if not isinstance(history, list) or not isinstance(refs, list) or len(history) != len(refs):
        raise ValueError(f"line {line_no}: history/reference misalignment")
    last = -1
    for i, (group, ref) in enumerate(zip(history, refs)):
        _exact_keys(group, HISTORY_KEYS, f"line {line_no} history[{i}]")
        _exact_keys(ref, REF_KEYS, f"line {line_no} ref[{i}]")
        if group["role"] not in ("self", "partner") or ref["role"] != group["role"]:
            raise ValueError(f"line {line_no}: invalid/misaligned role")
        for c in CHANNELS:
            _text_or_null(group[c], f"line {line_no} {c}")
        turn = ref["raw_turn_index"]
        if type(turn) is not int or turn < 0 or turn <= last or turn >= prov["target_raw_turn_index"]:
            raise ValueError(f"line {line_no}: refs must be strictly increasing and prior")
        last = turn
        if not isinstance(ref["speaker"], str) or not ref["speaker"].strip() or not isinstance(ref["source_ref"], str):
            raise ValueError(f"line {line_no}: invalid ref strings")
        if (group["role"] == "self") != (ref["speaker"].casefold() == actor.casefold()):
            raise ValueError(f"line {line_no}: role does not match actor/speaker")
        if ref["physical_index"] is not None and (type(ref["physical_index"]) is not int or ref["physical_index"] < 0):
            raise ValueError(f"line {line_no}: invalid physical reference")
        if ref["source_ref"] != f"episode:{prov['episode_index']}:turn:{turn}":
            raise ValueError(f"line {line_no}: source reference mismatch")
        for channel in CHANNELS:
            if group[channel] == "":
                raise ValueError(f"line {line_no}: empty channel string")


def features(record: dict[str, Any], view: str = "core", include_context: bool = True) -> dict[str, Any]:
    """Only model-facing entry; `include_context=False` is a covariate ablation."""
    if view not in ("core", "diagnostic_plus_partner_raw_commands"):
        raise ValueError(f"unknown view: {view}")
    _exact_keys(record, {"schema", "static_condition", "history_views", "candidate_surface", "supervision", "provenance", "admission"}, "projected row")
    if record["schema"] != OUT_SCHEMA: raise ValueError("unexpected projected schema")
    static = record["static_condition"]
    _exact_keys(static, {"self_persona", "recorded_environment_snapshot"}, "static condition")
    views = record["history_views"]
    _exact_keys(views, {"core", "diagnostic_plus_partner_raw_commands"}, "history views")
    history = views[view]
    if not isinstance(history, list): raise ValueError("selected history view must be a list")
    clean = []
    for group in history:
        _exact_keys(group, HISTORY_KEYS, "selected history group")
        if group["role"] not in ("self", "partner"):
            raise ValueError("selected history role must be self or partner")
        for channel in CHANNELS:
            if group[channel] is not None and (not isinstance(group[channel], str) or not group[channel].strip()):
                raise ValueError(f"selected history {channel} must be nonempty string or null")
        if view == "core" and group["role"] == "partner" and group["action"] is not None:
            raise ValueError("core view must not contain partner raw commands")
        clean.append({k: group[k] for k in ("role", "speech", "action", "emote")})
    surface = record["candidate_surface"]
    _exact_keys(surface, {"recorded_support"}, "candidate surface")
    if not isinstance(static["self_persona"], str) or not static["self_persona"].strip():
        raise ValueError("self_persona must be a nonempty string")
    if not isinstance(static["recorded_environment_snapshot"], str) or not static["recorded_environment_snapshot"].strip():
        raise ValueError("recorded_environment_snapshot must be a nonempty string")
    if not isinstance(surface["recorded_support"], list) or any(not isinstance(x, str) or not x.strip() for x in surface["recorded_support"]):
        raise ValueError("recorded_support must be a list of nonempty strings")
    out = {"self_persona": static["self_persona"], "history": clean,
           "recorded_support": list(surface["recorded_support"]), "view": view}
    if include_context:
        out["recorded_environment_snapshot"] = static["recorded_environment_snapshot"]
    return out


def _eligibility(gold: Any, support: list[str]) -> str:
    if not isinstance(gold, str) or not gold.strip() or not support or any(not isinstance(x, str) or not x.strip() for x in support):
        return "missing_or_invalid"
    norm = lambda s: s.strip().casefold()
    n = sum(norm(x) == norm(gold) for x in support)
    return "unique" if n == 1 else "absent" if n == 0 else "ambiguous"


def project_record(r: dict[str, Any], line_no: int = 1, input_sha: str = INPUT_SHA256) -> dict[str, Any]:
    """Pure one-row projection, also used by synthetic contract tests."""
    if input_sha != INPUT_SHA256: raise ValueError("pinned input SHA-256 mismatch")
    validate_record(r, line_no)
    p, prov = r["candidate_model_payload"], r["provenance"]
    core, diagnostic = [], []
    for group in p["prior_interaction_history"]:
        diagnostic.append(dict(group))
        core.append({**group, **({"action": None} if group["role"] == "partner" else {})})
    return {"schema": OUT_SCHEMA,
            "static_condition": {"self_persona": p["self_persona"],
                                 "recorded_environment_snapshot": p["recorded_environment_snapshot"]},
            "history_views": {"core": core, "diagnostic_plus_partner_raw_commands": diagnostic},
            "candidate_surface": {"recorded_support": list(r["candidate_surface"]["recorded_support"])},
            "supervision": {"recorded_action": r["supervision"]["recorded_action"]},
            "provenance": {"source_row_line": line_no, "source_input_sha256": INPUT_SHA256, **prov},
            "admission": {"training_authorized": False, "actor_forecast_admitted": False,
                          "warning": "DEVELOPMENT_SOURCE_CONDITIONAL_COMMAND_RANKING; Paper-0 remains NOT ADMITTED"}}


def project_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    projected, seen = [], set()
    for line_no, r in enumerate(records, 1):
        row = project_record(r, line_no)
        p = row["provenance"]
        key = (p["trajectory_id"], p["target_physical_index"], p["actor"].casefold())
        if key in seen: raise ValueError(f"duplicate source row key at line {line_no}")
        seen.add(key); projected.append(row)
    return projected


def _safe_paths(source: Path, output: Path) -> tuple[Path, Path]:
    source = source.absolute(); output = output.absolute()
    outputs_root = ROOT / "outputs"
    if source != ROOT and ROOT not in source.parents:
        raise ValueError("source must be under ROOT")
    if output != outputs_root and outputs_root not in output.parents:
        raise ValueError("output must be under ROOT/outputs")
    checked = [source, *(p for p in source.parents if p == ROOT or ROOT in p.parents)]
    checked.extend([outputs_root, *(p for p in output.parents if p == outputs_root or outputs_root in p.parents), output])
    for path in checked:
        if path.is_symlink():
            raise ValueError(f"symlink path forbidden: {path}")
    src_real, out_real = source.resolve(), output.resolve()
    if src_real == out_real or src_real in out_real.parents or out_real in src_real.parents:
        raise ValueError("source/output paths overlap")
    root_out = outputs_root.resolve()
    if out_real != root_out and root_out not in out_real.parents:
        raise ValueError("output must be under ROOT/outputs")
    if output.exists():
        raise FileExistsError(f"refusing existing output: {output}")
    return src_real, output


def project_bytes(data: bytes, source_sha: str = INPUT_SHA256) -> tuple[bytes, dict[str, Any]]:
    if source_sha != INPUT_SHA256 or sha256_bytes(data) != INPUT_SHA256:
        raise ValueError("pinned input SHA-256 mismatch")
    records = []
    for line_no, raw in enumerate(data.decode("utf-8").splitlines(), 1):
        if not raw.strip():
            raise ValueError(f"blank line {line_no}")
        records.append(json.loads(raw))
    records = project_records(records)
    if len(records) != 13463:
        raise ValueError(f"cohort row count changed: {len(records)}")
    output = b"".join(json.dumps(x, ensure_ascii=False, separators=(",", ":")).encode() + b"\n" for x in records)
    summary: dict[str, Any] = {}
    for split in ("train", "validation", "excluded_bucket9"):
        subset = [x for x in records if x["provenance"]["split"] == split]
        summary[split] = {"rows": len(subset), "episodes": len({x["provenance"]["trajectory_id"] for x in subset}),
            "groups": sum(len(x["history_views"]["core"]) for x in subset),
                          "history_depth_distribution": {str(depth): sum(len(x["history_views"]["core"]) == depth for x in subset)
                                                          for depth in sorted({len(x["history_views"]["core"]) for x in subset})},
                          "actor_trajectories": len({(x["provenance"]["trajectory_id"], x["provenance"]["actor"]) for x in subset}),
                          "channel_items": {view: {role: {c: {"present": sum(g["role"] == role and g[c] is not None for x in subset for g in x["history_views"][view]),
                                                              "null": sum(g["role"] == role and g[c] is None for x in subset for g in x["history_views"][view])}
                                                        for c in CHANNELS} for role in ("self", "partner")}
                                            for view in ("core", "diagnostic_plus_partner_raw_commands")}}
    eligibility: dict[str, dict[str, int]] = {}
    for split in summary:
        sub = [x for x in records if x["provenance"]["split"] == split]
        eligibility[split] = {k: sum(_eligibility(x["supervision"]["recorded_action"], x["candidate_surface"]["recorded_support"]) == k for x in sub)
                              for k in ("unique", "absent", "ambiguous", "missing_or_invalid")}
    key_digest = lambda vals: sha256_bytes("\n".join(sorted(vals)).encode())
    meta = {"rows": len(records), "splits": summary, "supervision_eligibility": eligibility,
            "cohort_key_digest": key_digest([f"{x['provenance']['trajectory_id']}|{x['provenance']['target_physical_index']}|{x['provenance']['actor'].casefold()}" for x in records]),
            "source_key_digest": key_digest([x["provenance"]["target_source_ref"] for x in records]),
            "input_sha256": INPUT_SHA256, "output_sha256": sha256_bytes(output),
            "contract_sha256": sha256_bytes(json.dumps(CONTRACT, ensure_ascii=False, sort_keys=True,
                                                         separators=(",", ":")).encode())}
    return output, meta


def run(source: Path = SOURCE, output: Path = OUTPUT) -> dict[str, Any]:
    source, output = _safe_paths(source, output)
    data = source.read_bytes()
    payload, meta = project_bytes(data)
    output.mkdir(parents=True, exist_ok=False)
    out_file = output / "projected_inputs.jsonl"
    with out_file.open("xb") as f: f.write(payload)
    snapshots = {"protocol_snapshot.md": Path(__file__).with_name("README.md").read_bytes(),
                 "project_inputs_snapshot.py": Path(__file__).read_bytes(),
                 "test_project_inputs_snapshot.py": Path(__file__).with_name("test_project_inputs.py").read_bytes()}
    snapshot_hashes = {}
    for name, content in snapshots.items():
        with (output / name).open("xb") as f: f.write(content)
        snapshot_hashes[name] = sha256_bytes(content)
    manifest = {"schema": "light_source_ranking_manifest_v1", **meta,
                "protocol_sha256": snapshot_hashes["protocol_snapshot.md"],
                "code_sha256": snapshot_hashes["project_inputs_snapshot.py"],
                "test_sha256": snapshot_hashes["test_project_inputs_snapshot.py"],
                "contract": CONTRACT,
                "training_authorized": False, "actor_forecast_admitted": False,
                "output_files_sha256": {out_file.name: meta["output_sha256"], **snapshot_hashes}}
    with (output / "manifest.json").open("x", encoding="utf-8") as f: json.dump(manifest, f, indent=2, sort_keys=True); f.write("\n")
    return manifest


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument("--source", type=Path, default=SOURCE); ap.add_argument("--output", type=Path, default=OUTPUT)
    a = ap.parse_args()
    try: print(json.dumps(run(a.source, a.output), sort_keys=True)); return 0
    except (OSError, ValueError, UnicodeError, json.JSONDecodeError) as e: print(f"projection failed: {e}", file=sys.stderr); return 1


if __name__ == "__main__": raise SystemExit(main())
