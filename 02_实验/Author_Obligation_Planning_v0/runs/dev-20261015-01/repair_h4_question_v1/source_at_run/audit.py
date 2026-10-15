"""Read-only evidence audit; never re-runs a search, inference or game."""
import hashlib
import json
from pathlib import Path

from tools.open_adventure_planning_v0.domain import initial_state
from .conflicts import static_conflicts
from .contracts import task_spec_from_dict
from .run import NATIVE_IDS, protected_hashes, write
from .verify import verify_native
from tools.open_adventure_planning_v0.verify import _raw_text


def audit(pack: Path, *, output_name="parent_audit.json"):
    manifest = json.loads((pack / "reference_manifest.json").read_text())
    certificates = {}
    for raw in manifest["tasks"]:
        task = task_spec_from_dict(raw)
        certificates[task.id] = static_conflicts(initial_state(), task)
    checks = []
    summaries = []
    for case in NATIVE_IDS:
        record = json.loads((pack / "native" / f"{case}.json").read_text())
        if not record.get("native_ledger"):
            checks.append({"id": case, "not_started": True, "prior_status": record["prior_status"]})
            continue
        ledger = Path(record["native_ledger"])
        rows = [json.loads(line) for line in ledger.read_text().splitlines()]
        by_seq = {r.get("sequence"): r for r in rows if r.get("event") == "step"}
        current = verify_native(ledger, record["final_task"])
        trace = [json.loads(line) for line in Path(record["decision_trace"]).read_text().splitlines()]
        author_history = record["final_author_history"]
        hashes = []
        for event in author_history:
            row = by_seq[event["sequence"]]
            import base64
            expected = f"native-step-{event['sequence']}-sha256-{hashlib.sha256(base64.b64decode(row['raw_output_b64'])).hexdigest()}"
            hashes.append(event["source_id"] == expected)
        history_agrees = [(e["name"], e["sequence"]) for e in author_history] == [
            (e["name"], e["sequence"]) for e in current["events"]]
        searches = [r for r in trace if r["event"] == "search"]
        start_task = next(r["task"] for r in trace if r["event"] == "episode_start")
        raw_candidate = json.loads((pack / "luna_candidate" / f"{case}.json").read_text())["raw_candidate"]
        edits = [r for r in trace if r["event"] == "author_edit"]
        version_chain = [start_task] + [r["after_task"] for r in edits]
        input_versions = {(r["id"], r["version"]): task_spec_from_dict(r) for r in version_chain}
        active = task_spec_from_dict(start_task)
        version_order_ok = True
        prefix_sources = []
        evidence_prefix_ok = True
        for item in trace:
            if item["event"] == "author_edit":
                version_order_ok &= task_spec_from_dict(item["before_task"]) == active
                revised = task_spec_from_dict(item["after_task"])
                version_order_ok &= revised.id == active.id and revised.version != active.version
                active = revised
            elif item["event"] == "author_history_update":
                prefix_sources = item["history_source_ids"]
            elif item["event"] == "search":
                version_order_ok &= task_spec_from_dict(item["task"]) == active
                evidence_prefix_ok &= item["history_source_ids"] == prefix_sources
        checks.append({
            "id": case, "raw_ledger_sha256": hashlib.sha256(ledger.read_bytes()).hexdigest(),
            "input_is_actual_luna_candidate": task_spec_from_dict(start_task) == task_spec_from_dict(raw_candidate),
            "independent_monitor_recheck_identical": current == record["independent_verifier"],
            "controller_events_equal_independent_raw_events": history_agrees,
            "all_event_source_hashes_match_raw_bytes": all(hashes),
            "every_search_uses_registered_active_author_version": all(
                task_spec_from_dict(r["task"]) == input_versions.get((r["task"]["id"], r["task"]["version"])) for r in searches),
            "no_search_uses_old_version_after_edit": bool(version_order_ok),
            "search_history_is_current_committed_prefix": bool(evidence_prefix_ok),
            "max_observed_expansions": max((r["expansions"] for r in searches), default=0),
            "native_input_cap_respected": record["native_task_inputs_including_h4_and_refresh"] <= 80,
            "raw_sequence_count": len(by_seq), "edit_count": len(edits),
            "source_checks": [r for r in rows if r["event"] == "close_source_check"],
        })
        summaries.append({"id": case, "controller": record["controller_status"],
                          "author": current["status"], "commands": [r["command"] for r in by_seq.values()],
                          "events": current["events"], "native_task_inputs": record["native_task_inputs_including_h4_and_refresh"]})
    before = json.loads((pack / "protected_before.json").read_text())
    result = {"audit_kind": "controller-side independent code/readback; not human replication",
              "static_certificates": certificates, "native_checks": checks, "native_replays": summaries,
              "protected_sources_and_old_evidence_unchanged": before == protected_hashes(),
              "protected_file_count": len(before), "does_not_rerun_search_or_native": True}
    write(pack / output_name, result)
    return result


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("pack", type=Path)
    args = parser.parse_args()
    audit(args.pack)
