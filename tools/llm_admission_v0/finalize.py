"""Offline report from already-completed calls. Never initiates inference."""
from __future__ import annotations

import json
from .binding import parse_candidate, validate_e
from .packet import canonical, OUT


def finalize() -> dict:
    e_raw = (OUT / "calls/e/response.raw.txt").read_text(encoding="utf-8")
    e_candidate = parse_candidate(e_raw)
    validation = validate_e(e_candidate)
    # Compile for inspection only. Admission failure cannot reach UCS/native.
    validation["search_execution"] = "NOT_RUN_BINDING_REJECTED"
    validation["native_execution"] = "NOT_RUN_BINDING_REJECTED"
    validation["interpretation_note"] = (
        "Model explicitly mentions bridge in bindings but treats it as intermediate, "
        "not a final predicate. Fixed acceptance demands final bridge. Model "
        "also preserves no_death as both monitor obligation and hard residual. "
        "This is an interface/temporal-interpretation mismatch, not proof of "
        "general inability to understand a bridge or survival requirement.")
    (OUT / "e_validation.json").write_bytes(canonical(validation) + b"\n")
    g = parse_candidate((OUT / "calls/g/response.raw.txt").read_text(encoding="utf-8"))
    audit = {
        "reviewer": "parent controller qualitative review; not independent human rating",
        "schema_parse": "PASS", "executable_goal": g.get("goal"),
        "producer_attribution": "identified absent verified help producer and helper/recipient attribution",
        "persistent_update": "identified absent verified cross-experience trust update",
        "later_consumer": "identified absent verified trust-dependent later interaction",
        "evidence_scope": "explicitly avoids concluding full-game absence from finite predicate vocabulary",
        "hardness": "kept unresolved requirements hard; no invented executable trust state",
        "existing_mechanisms": "described native encounter progress/treasure/lamp and seen reset",
        "composition": "did not propose a native composition implementing lasting trust",
        "limitations": ["single disclosed-audit development example", "not an independent source discovery",
                        "missing_capabilities entries are strings, despite prompt requesting objects; format deviation retained",
                        "proposal is mechanism requirement decomposition, not an implemented algorithm"],
        "result": "USEFUL_GAP_ANALYSIS_WITH_FORMAT_DEVIATION",
    }
    (OUT / "g_review.json").write_bytes(canonical(audit) + b"\n")
    result = {"calls": {"probe": 1, "formal_e": 1, "formal_g": 1, "retries": 0},
              "model": "gpt-6-luna", "classification": "AGENT_CONFOUNDED",
              "e_binding": validation["status"], "g": audit["result"],
              "native_task_episodes": 0, "setup_inputs": 2,
              "search": "NOT_RUN_BINDING_REJECTED", "milestone": "READY_FOR_INDEPENDENT_REVIEW",
              "stop": "no model retry, no game-rule adjustment, no B1/B2 comparison"}
    (OUT / "outcome.json").write_bytes(canonical(result) + b"\n")
    return result


if __name__ == "__main__":
    print(json.dumps(finalize(), ensure_ascii=False, indent=2))
