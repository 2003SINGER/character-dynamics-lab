"""Extract only this experiment's child-turn evidence, never whole chat logs."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from .packet import canonical


def collect(rollout: Path, task_name: str, output: Path) -> dict:
    with rollout.open(encoding="utf-8") as stream:
        rows = [json.loads(line) for line in stream]
    meta = next(r["payload"] for r in rows if r["type"] == "session_meta")
    if meta.get("agent_path") != task_name:
        raise ValueError("not the designated experimental child")
    turns, requests, finals, calls, fingerprints, usage = [], [], [], [], [], []
    for row in rows:
        payload = row.get("payload", {})
        if row["type"] == "turn_context":
            turns.append({k: payload.get(k) for k in ("turn_id", "model", "effort", "cwd")})
        if row["type"] == "event_msg" and payload.get("type") == "token_count":
            usage.append(payload.get("info"))
        if row["type"] != "response_item":
            continue
        if payload.get("type") in ("function_call", "custom_tool_call", "multi_agent_call"):
            calls.append({k: payload.get(k) for k in ("type", "name", "action", "call_id", "arguments", "input")})
        if payload.get("type") == "message":
            role = payload.get("role")
            content = payload.get("content", [])
            text = "".join(x.get("text", "") for x in content if isinstance(x, dict))
            if role == "user":
                # The desktop injects personal AGENTS/environment as user
                # messages even with fork_turns=none. Never publish that text.
                fingerprints.append({"role": "injected_user_context", "sha256": hashlib.sha256(canonical(content)).hexdigest(),
                                     "characters": len(text)})
            elif role == "assistant" and (payload.get("channel") == "final" or payload.get("phase") == "final_answer"):
                finals.append(text)
            elif role in ("system", "developer"):
                fingerprints.append({"role": role, "sha256": hashlib.sha256(canonical(content)).hexdigest(),
                                     "characters": len(text)})
    models = sorted({t["model"] for t in turns if t.get("model")})
    status = ("INVALID_MODEL_ID" if models != ["gpt-6-luna"]
              else "INVALID_LEAKAGE" if calls
              else "AGENT_CONFOUNDED")
    report = {
        "task_name": task_name, "session_id": meta["id"],
        "runtime": {k: meta.get(k) for k in ("originator", "cli_version", "model_provider", "timestamp")},
        "requested_model": "gpt-6-luna", "requested_fork_turns": "none",
        "model_identity_evidence": "local runtime turn_context, not model self-report",
        "actual_turn_context": turns, "classification": status,
        "tool_disable_control": "NOT_AVAILABLE_IN_SPAWN_SCHEMA",
        "tool_calls_observed": calls,
        "instruction_fingerprints_only": fingerprints,
        "full_system_instruction_contents": "NOT_OBSERVABLE",
        "inherited_environment": "same workspace and tools are available; not a sandbox or bare-model call",
        "experimental_requests": requests, "request_capture": "parent spawn arguments retained separately; child task payload can be encrypted",
        "assistant_final_outputs": finals,
        "token_count_events": usage,
        "token_count_scope": "runtime-reported child events; absent means NOT_AVAILABLE; no dollar-cost estimate",
        "backend_weight_identity": "NOT_OBSERVABLE",
    }
    output.mkdir(parents=True, exist_ok=False)
    (output / "audit.json").write_bytes(canonical(report) + b"\n")
    if len(finals) == 1:
        # Exact unedited final text, without newline normalization/JSON repair.
        (output / "response.raw.txt").write_bytes(finals[0].encode("utf-8"))
    (output / "rollout_reference.json").write_bytes(canonical({
        "session_id": meta["id"], "local_rollout_basename": rollout.name,
        "private_full_rollout_not_published": True,
        "retained": "selected child metadata and experimental user/final messages only"}) + b"\n")
    return report
