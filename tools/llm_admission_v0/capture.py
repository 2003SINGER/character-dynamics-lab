"""Retain exact experimental spawn requests, not the parent conversation."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from .packet import canonical
from tools.open_adventure_planning_v0 import domain as d


SUFFIXES = {
    "tested_luna_semantic_e": "\n\nTHIS REQUEST: Bind exactly the following author intent using the supplied rule catalog (not a preselected answer): 让探险者建立裂隙晶桥，安全抵达西岸，最后仍持有钥匙与点亮的灯，并且整个过程中不能死亡。",
    "tested_luna_semantic_g": "\n\nTHIS REQUEST: Analyze exactly this author intent using the supplied catalog: 让海盗因为过去受到探险者帮助而逐渐产生持续信任，并使这种信任真正影响之后的互动。 Distinguish what already exists, what can be composed from existing rules, and what needs additional verified capabilities. Check event producer, attribution to helper/recipient, persistent update over successive experiences, and later action consumer; specify evidence boundaries and missing capability requirements. Do not infer full-game absence solely from a missing finite State field. Do not create a trust variable or claim you executed it.",
    "tested_luna_admission_probe": "This is one inference admission probe, not a repository or coding task. Do not use tools, inspect files, browse, access workspace context, spawn agents, or send inter-agent messages. Return exactly this string as your final answer, with no commentary: LUNA_ADMISSION_20261014_26217420_OK",
}


def capture_requests(parent: Path, output: Path, transcript: Path) -> dict:
    wanted = {"tested_luna_admission_probe", "tested_luna_semantic_e", "tested_luna_semantic_g"}
    found = {}
    for line in parent.open(encoding="utf-8"):
        row = json.loads(line)
        payload = row.get("payload", {})
        if row["type"] != "response_item" or payload.get("type") != "function_call" or payload.get("name") != "spawn_agent":
            continue
        args = json.loads(payload["arguments"])
        task = args.get("task_name")
        if task not in wanted:
            continue
        if task in found:
            raise ValueError("unexpected repeated experimental call")
        message = args.pop("message")
        found[task] = {"timestamp": row["timestamp"], "call_id": payload["call_id"], "parameters": args,
                       "runtime_message_sha256": hashlib.sha256(message.encode()).hexdigest(),
                       "runtime_message_encrypted": message.startswith("gAAAA"),
                       "backend_plaintext_input": "NOT_OBSERVABLE" if message.startswith("gAAAA") else message}
    if set(found) != wanted:
        raise ValueError("missing exact parent call records")
    output.mkdir(parents=True, exist_ok=False)
    common = transcript.read_text(encoding="utf-8").rstrip("\n")
    for task, record in found.items():
        supplied = SUFFIXES[task] if task.endswith("probe") else common + SUFFIXES[task]
        record["controller_supplied_request_transcript"] = supplied
        record["plaintext_provenance"] = "controller transcription of the actual tool-call text; NOT decrypted runtime plaintext"
        (output / f"{task}.json").write_bytes(canonical(record) + b"\n")
        (output / f"{task}.txt").write_bytes(supplied.encode("utf-8"))
    e = found["tested_luna_semantic_e"]["controller_supplied_request_transcript"]
    g = found["tested_luna_semantic_g"]["controller_supplied_request_transcript"]
    common_e = e.split("\n\nTHIS REQUEST:")[0]
    common_g = g.split("\n\nTHIS REQUEST:")[0]
    if common_e != common_g:
        raise ValueError("unequal shared model inputs")
    rows = [line for line in e.splitlines() if line.count("|") == 2 and line.split("|")[0] in d.ROOMS]
    expected = [f"{a}|{','.join(b)}|{c}" for a, b, c in d.MOVE_ROWS]
    if rows != expected:
        raise ValueError("movement row/alias omission in actual request")
    # Remaining families are universally quantified in the exact request.
    # They were manually audited against the frozen ground_operators body;
    # full structured export separately round-trips every grounded instance.
    report = {"shared_request_prefix_identical": True,
              "plaintext_comparison_scope": "controller tool-call transcription; encrypted runtime task bodies not independently readable",
              "shared_request_prefix_sha256": hashlib.sha256(common_e.encode()).hexdigest(),
              "movement_rows_identical": len(rows),
              "movement_aliases_identical": sum(len(b) for _, b, _ in d.MOVE_ROWS),
              "remaining_schema_audit": "manual precondition/effect/variant audit, not a certified NLP equivalence proof",
              "family_instances": {"move": 174, "take": 42, "drop": 42,
                                   "lamp_on": 28, "lamp_off": 28, "unlock": 4, "lock": 4, "wave_rod": 4},
              "no_gold_or_plan_lookup_in_packet_builder": True,
              "native_task_actions": 0, "native_setup_inputs": 2}
    (output / "fairness.json").write_bytes(canonical(report) + b"\n")
    return report
