"""Validate the bounded P3 native-run evidence bundle and DB readback.

This is a narrow acceptance check for the five named live runs, not a general
evidence-schema validator. It prints only a compact audit summary.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import sys
from typing import Any


EXPECTED = {
    "Aclean",
    "Asteal-return",
    "Bclean",
    "Bsteal-resident-parcel",
    "Bstale-target-negative-control",
    "Aunattended-timer",
    "MCPstdio-live",
}


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected JSON object")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def events(actor: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return [entry for entry in actor.get("log", []) if entry.get("kind") == kind]


def actor_by_role(run: dict[str, Any], role: str) -> dict[str, Any]:
    matches = [
        row for row in run["response"]["trace"]["objects"]
        if row.get("attributes", {}).get("p3_control_role") == role
    ]
    require(len(matches) == 1, f"{run['request']['scenario']}: expected one {role}")
    return matches[0]["attributes"]


def successful_delivery(actor: dict[str, Any], label: str) -> None:
    receipts = actor.get("native_receipts", [])
    require([r.get("kind") for r in receipts] == ["get", "move", "drop"], f"{label}: expected get/move/drop receipts")
    require(all(r.get("settled") is True and r.get("dispatch_succeeded") is True for r in receipts), f"{label}: non-settled delivery receipt")
    require(len({r.get("receipt_id") for r in receipts}) == 3, f"{label}: duplicate delivery receipt IDs")
    require(actor.get("status") == "ACTOR_DELIVERY_SETTLED", f"{label}: actor goal not settled")


def check_run(document: dict[str, Any]) -> dict[str, Any]:
    scenario = document.get("request", {}).get("scenario")
    if scenario == "MCPstdio-live":
        require(document.get("schema") == "native-p3-mcp-live-audit-v1", "unexpected MCP audit schema")
        response = document.get("response", {})
        require(response.get("completed") is True, "MCP stdio audit incomplete")
        messages = response.get("initialize_list_health", [])
        require([m.get("id") for m in messages] == [1, 2, 3], "MCP initialize/list/health sequence missing")
        require(messages[0].get("result", {}).get("protocolVersion") == "2025-06-18", "MCP protocol negotiation mismatch")
        tools = {tool.get("name") for tool in messages[1].get("result", {}).get("tools", [])}
        require({"start_world", "stop_world", "reset_scenario", "pause_scenario", "step_world", "inject_action", "observe_actor", "get_trace", "run_scenario"} <= tools, "MCP tool inventory incomplete")
        health = messages[2].get("result", {}).get("structuredContent", {})
        require(health.get("status") == "READY" and health.get("bind") == "127.0.0.1:14011", "MCP control health not loopback READY")
        require(response.get("registration") == "tested as stdio subprocess; no global Codex MCP registration", "MCP global registration boundary mismatch")
        return {"scenario": scenario, "mcp_stdio": "initialize/list/health verified", "global_registration": False}

    require(document.get("schema") == "native-p3-headless-run-v1", "unexpected run schema")
    response = document["response"]
    require(response.get("completed") is True, f"{scenario}: run incomplete")
    require(response.get("trace", {}).get("source") == "live Evennia object and attribute state", f"{scenario}: not live Evennia readback")
    require(response.get("scene", {}).get("scene_id") == response.get("trace", {}).get("scene_id"), f"{scenario}: scene mismatch")
    require(document.get("source_sha256"), f"{scenario}: missing source hash")
    summary: dict[str, Any] = {"scenario": scenario, "scene_id": response["scene"]["scene_id"]}

    if scenario == "Aclean":
        courier = actor_by_role(document, "courier")
        successful_delivery(courier, scenario)
        summary["courier_receipts"] = [r["kind"] for r in courier["native_receipts"]]
    elif scenario == "Asteal-return":
        courier = actor_by_role(document, "courier")
        rejected = [e for e in events(courier, "execution_settlement") if e.get("status") == "WORLD_VALIDATION_REJECTED"]
        require(rejected and rejected[0].get("receipt", {}).get("settled") is False and rejected[0]["receipt"].get("dispatch_succeeded") is False, "Asteal-return: stale get was not rejected")
        require(events(courier, "blocked"), "Asteal-return: absent item did not block")
        successful_delivery(courier, scenario)
        interventions = response.get("interventions", [])
        held = next((e for e in interventions if e.get("phase") == "while_parcel_held"), None)
        held_observation = (held or {}).get("actor", {}).get("local_observation", {}).get("observation", {})
        require(held_observation.get("item_held") is False and held_observation.get("item_location") is None, "Asteal-return: held parcel leaked into courier local observation")
        require([e.get("operation") for e in interventions if e.get("intervention_kind") == "native-player-command"] == ["get", "drop"], "Asteal-return: expected player get then drop")
        require(all(e.get("settled") is True for e in interventions if e.get("intervention_kind") == "native-player-command"), "Asteal-return: player command not settled")
        summary["stale_get_rejected_then_recovered"] = True
    elif scenario == "Bclean":
        courier, resident = actor_by_role(document, "courier"), actor_by_role(document, "resident")
        successful_delivery(courier, "Bclean courier")
        successful_delivery(resident, "Bclean resident")
        proposals = [e.get("proposal", {}) for e in events(courier, "social_proposal") if e.get("proposal", {}).get("ok")]
        require(proposals, "Bclean: missing social proposal")
        proposal = proposals[-1]
        selection = proposal.get("selection", {})
        require(set(selection.get("native_candidate_names", [])) == {"writeLoveNoteReject", "kissFail"}, "Bclean: native candidate set mismatch")
        require(selection.get("native_candidate_weights") == {"writeLoveNoteReject": 20, "kissFail": 20}, "Bclean: native candidate weights mismatch")
        require(selection.get("selected_name") == "kissFail", "Bclean: seeded candidate was not kissFail")
        outcomes = [e.get("result", {}) for e in events(courier, "social_outcome")]
        settled = [out for out in outcomes if out.get("status") == "SETTLED"]
        require(settled and settled[-1].get("action_name") == "kissFail" and settled[-1].get("ensemble", {}).get("recordRevision") == 1, "Bclean: failed-kiss native commit missing")
        require(any(e.get("result", {}).get("status") == "NO_CANDIDATE" for e in events(resident, "social_outcome")), "Bclean: resident no-candidate baseline missing")
        summary["native_candidates"] = selection["native_candidate_names"]
        summary["selected"] = "kissFail"
        summary["ensemble_revision"] = 1
    elif scenario == "Bsteal-resident-parcel":
        courier, resident = actor_by_role(document, "courier"), actor_by_role(document, "resident")
        successful_delivery(courier, "Bsteal courier")
        successful_delivery(resident, "Bsteal resident")
        no_candidates = [e.get("proposal", {}) for e in events(resident, "social_proposal") if e.get("proposal", {}).get("status") == "NO_CANDIDATE"]
        require(no_candidates and all(not e.get("native_action_names") for e in no_candidates), "Bsteal: resident no-candidate gate missing")
        held = next((e for e in response.get("interventions", []) if e.get("phase") == "while_resident_parcel_held"), None)
        resident_snapshot = (held or {}).get("resident_actor", {}).get("local_observation", {}).get("observation", {})
        require(resident_snapshot.get("item_held") is False and resident_snapshot.get("item_location") is None, "Bsteal: held parcel leaked into resident local observation")
        require((held or {}).get("social_events_before_return") == [[], []], "Bsteal: social action/event lists were not empty while parcel was held")
        require(any(e.get("status") == "WORLD_VALIDATION_REJECTED" and e.get("receipt", {}).get("settled") is False for e in events(resident, "execution_settlement")), "Bsteal: resident stale get was not rejected")
        require(events(resident, "blocked"), "Bsteal: resident did not block while parcel was absent")
        player = [e for e in response.get("interventions", []) if e.get("intervention_kind") == "native-player-command"]
        require(player and player[0].get("settled") is True, "Bsteal: parcel theft intervention missing")
        summary["resident_no_candidate_and_recovery"] = True
        summary["courier_independent_receipts"] = [r["kind"] for r in courier["native_receipts"]]
    elif scenario == "Bstale-target-negative-control":
        courier = actor_by_role(document, "courier")
        successful_delivery(courier, scenario)
        interventions = response.get("interventions", [])
        require(any(e.get("operation") == "move" and e.get("actor_role") == "resident" for e in interventions), "Bstale: target displacement intervention missing")
        social_outcomes = events(courier, "social_outcome")
        rejected = [e.get("result", {}) for e in social_outcomes]
        require(any(r.get("status") == "WORLD_VALIDATION_REJECTED" and r.get("receipt_created") is False and r.get("ensemble_commit_called") is False for r in rejected), "Bstale: unsafe proposal was not rejected without receipt/commit")
        proposal_events = [e.get("proposal", {}) for e in events(courier, "social_proposal")]
        rejected_proposals = [p for p in proposal_events if p.get("status") == "PROPOSED"]
        require(rejected_proposals, "Bstale: missing preceding proposal")
        rejected_event_ids = {rejected_proposals[0].get("event_id")}
        committed_ids = {e.get("event_id") for e in courier.get("native_social_events", [])}
        require(None not in rejected_event_ids and rejected_event_ids.isdisjoint(committed_ids), "Bstale: rejected social attempt was recorded as committed event")
        require(any(e.get("result", {}).get("status") == "SETTLED" for e in social_outcomes), "Bstale: actor did not recover on a later fresh proposal")
        summary["stale_target_rejected_without_commit"] = True
    elif scenario == "Aunattended-timer":
        courier = actor_by_role(document, "courier")
        successful_delivery(courier, scenario)
        scene = response.get("scene", {})
        require(scene.get("drive_mode") == "timer" and scene.get("interval") == 2, "timer run was not configured for bounded timer drive")
        require(not response.get("interventions"), "timer run unexpectedly used controller interventions")
        require(len(events(courier, "timer_tick")) >= 3, "timer run lacks autonomous callbacks")
        satisfied = events(courier, "goal_satisfied_by_local_observation")
        require(satisfied and satisfied[-1].get("status") == "ACTOR_DELIVERY_SETTLED", "timer run did not reach actor-local settled goal")
        summary["timer_callbacks_without_intervention"] = len(events(courier, "timer_tick"))
        summary["own_receipts"] = [r["kind"] for r in courier["native_receipts"]]
    else:
        raise ValueError(f"unexpected scenario {scenario!r}")
    return summary


def check_db(document: dict[str, Any], summaries: list[dict[str, Any]]) -> int:
    require(document.get("schema") == "native-p3-db-evidence-v1", "unexpected DB evidence schema")
    require(document.get("source") == "initialized Evennia Django ORM; SQLite query_only enabled", "DB readback source/guard mismatch")
    scenes = {scene["scene_id"]: scene for scene in document.get("scenes", [])}
    db_summaries = [s for s in summaries if s["scenario"] != "MCPstdio-live"]
    require(set(scenes) == {s["scene_id"] for s in db_summaries}, "DB scenes do not match the explicitly exported native run scenes")
    inspected = 0
    for summary in db_summaries:
        scene = scenes[summary["scene_id"]]
        rows = scene.get("objects", [])
        require(rows, f"{summary['scenario']}: empty DB scene")
        require(all(row.get("attributes", {}).get("native_p3", {}).get("p3_scene_id") == summary["scene_id"] for row in rows), f"{summary['scenario']}: DB scene marker mismatch")
        by_id = {row["id"]: row for row in rows}
        for row in rows:
            attrs = row.get("attributes", {}).get("native_p3", {})
            if attrs.get("p3_control_role") in {"courier", "resident"}:
                item_id = attrs.get("task_item_id")
                if item_id in by_id:
                    item = by_id[item_id]
                    role = attrs["p3_control_role"]
                    if attrs.get("status") in {"PAUSED", "ACTOR_DELIVERY_SETTLED"} and attrs.get("native_receipts"):
                        receipts = attrs["native_receipts"]
                        last = receipts[-1]
                        require(last.get("actor_dbref") == row.get("dbref"), f"{summary['scenario']}: receipt actor does not match DB owner")
                        require(last.get("kind") == "drop" and last.get("settled") is True, f"{summary['scenario']}: paused/settled actor lacks native drop receipt")
                        require(item.get("location", {}).get("id") == attrs.get("task_destination_id"), f"{summary['scenario']}: DB item not at assigned destination")
                inspected += 1
    require(inspected >= 9, "DB readback did not include all tested NPCs")
    return inspected


def audit(run_paths: list[Path], db_path: Path) -> dict[str, Any]:
    runs = [read_json(path) for path in run_paths]
    scenarios = [run.get("request", {}).get("scenario") for run in runs]
    require(len(scenarios) == len(set(scenarios)) and set(scenarios) == EXPECTED, "run bundle must contain exactly the five expected P3 scenarios")
    summaries = [check_run(run) for run in runs]
    db_objects = check_db(read_json(db_path), summaries)
    return {"status": "PASS", "scope": "bounded P3 live native-run receipts and SQLite ORM readback", "runs": summaries, "db_npc_objects_checked": db_objects}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", nargs="+", type=Path, required=True, help="exact seven P3 run/audit JSON paths")
    parser.add_argument("--db", type=Path, required=True, help="matching native-p3-db-evidence-v1 JSON path")
    args = parser.parse_args()
    try:
        result = audit(args.runs, args.db)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 1
    result["inputs"] = {
        "runs": [{"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in args.runs],
        "db": {"file": args.db.name, "sha256": hashlib.sha256(args.db.read_bytes()).hexdigest()},
    }
    audit_dir = args.db.parent
    audit_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for _ in range(8):
        output = audit_dir / f"p3-audit-{stamp}-{secrets.token_hex(3)}.json"
        try:
            with output.open("x", encoding="utf-8") as handle:
                json.dump(result, handle, ensure_ascii=False, separators=(",", ":"))
                handle.write("\n")
            break
        except FileExistsError:
            continue
    else:
        print(json.dumps({"status": "FAIL", "error": "could not allocate unique audit output"}, ensure_ascii=False))
        return 1
    result["audit_file"] = output.name
    # Rewrite the unique audit with its own filename included in the record.
    output.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
