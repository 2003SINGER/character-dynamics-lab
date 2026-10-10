"""Audit one bounded C1a recovery trace against exact-scene SQLite readback."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from tools.native_platform_v0.p3.c1a_runner import RUNS_DIR


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_json(path):
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected object")
    return value


def _actor(response):
    rows = [row for row in response["trace"]["objects"]
            if row.get("attributes", {}).get("p3_control_role") == "courier"]
    require(len(rows) == 1, "trace must contain one courier")
    return rows[0]


def _timeline(response):
    rows = response.get("timeline", [])
    return ([row for row in rows if row.get("kind") == "npc_callback"],
            [row for row in rows if row.get("kind") == "player_intervention"])


def _event_index(log, target):
    for index, event in enumerate(log):
        if event is target:
            return index
    target_at = target.get("at")
    if target_at is not None:
        matches = [index for index, event in enumerate(log)
                   if event.get("kind") == target.get("kind") and event.get("at") == target_at]
        if matches:
            return matches[0]
    matches = [index for index, event in enumerate(log) if event == target]
    if matches:
        return matches[-1]
    raise ValueError("timeline event is absent from the actor's append-only log")


def audit_trace(response, scenario):
    require(response.get("schema") == "native-p3-c1a-run-v1", "unexpected response schema")
    require(response.get("scenario") == scenario, "scenario mismatch")
    require(response.get("activity_profile") == "delivery_patrol_recovery_v0", "recovery profile missing")
    require(response.get("controller_authored_npc_commands") == 0, "controller directly commanded NPC")
    require(response.get("completion_scope") == "bounded_callbacks_only_not_semantic_acceptance",
            "runner overstates bounded callback completion")
    callback_limit = 12 if scenario == "C1a-blocked-switch" else 16
    callbacks, interventions = _timeline(response)
    require(response.get("callback_count") == callback_limit and len(callbacks) == callback_limit,
            "wrong bounded callback count")
    actor_row = _actor(response)
    actor = actor_row["attributes"]
    require(actor.get("activity_profile") == "delivery_patrol_recovery_v0"
            and actor.get("delivery_task") is True and actor.get("goal") == "deliver_supply",
            "authored delivery contract not retained")
    item_id = actor.get("task_item_id")
    pickup_id = response["created_scene"]["rooms"]["pickup"]["id"]
    require(item_id is not None, "assigned parcel missing")
    goals = [event for event in actor.get("log", []) if event.get("kind") == "goal_choice"]
    require(goals, "missing goal-choice evidence")
    for event in goals:
        view = event.get("view", {})
        observation = view.get("observation", {})
        contract = view.get("goal_contract", {})
        require(event.get("activity_profile", {}).get("profile") == "delivery_patrol_recovery_v0",
                "goal event missing recovery profile")
        require(str(contract.get("item_id")) == str(item_id)
                and contract.get("destination_id") == actor.get("task_destination_id"),
                "goal event changed the authored delivery contract")
        require(isinstance(observation.get("room_id"), int)
                and isinstance(observation.get("visible_items"), list),
                "goal event missing local room/item observation")
        require("all_objects" not in observation and "global_world" not in view,
                "planner input includes global world projection")

    initial = next((event for event in goals
                    if event.get("view", {}).get("observation", {}).get("room_id") == pickup_id), None)
    require(initial is not None and initial.get("choice") == "deliver_supply"
            and initial.get("goal", {}).get("delivery_status") == "ACTIVE",
            "initial decision did not choose delivery")
    initial_view = initial["view"]["observation"]
    require(any(str(row.get("id")) == str(item_id) for row in initial_view.get("visible_items", [])),
            "initial get was not based on visible parcel")
    require(initial.get("planner", {}).get("implementation") == "gtpyhop-core-2.0.2"
            and initial.get("planner", {}).get("intent", {}).get("operator") == "get",
            "initial decision did not use GTPyhop get proposal")

    player_gets = [entry for entry in interventions
                   if entry.get("command_receipt", {}).get("operation") == "get"]
    require(len(player_gets) == 1 and player_gets[0].get("label") == "player_steals_assigned_supply",
            "missing single native player theft command")
    player_get = player_gets[0]["command_receipt"]
    require(player_get.get("intervention_kind") == "native-player-command"
            and player_get.get("settled") is True and player_get.get("item_id") == item_id,
            "player theft did not settle in Evennia")
    stale = [event for event in actor.get("log", [])
             if event.get("kind") == "execution_settlement"
             and event.get("receipt", {}).get("kind") == "get"
             and event.get("receipt", {}).get("settled") is False]
    require(len(stale) == 1, "expected one failed stale native get")
    failure = stale[0]
    failed_receipt = failure["receipt"]
    require(failure.get("status") == "WORLD_VALIDATION_REJECTED"
            and failed_receipt.get("dispatch_succeeded") is True
            and failed_receipt.get("submitted_command") == f"get {initial_view['task_item']['key']}"
            and failed_receipt.get("item_id") == item_id,
            "stale get was not submitted as the previously observed native command and rejected by Evennia")
    after_failure = [event for event in goals
                     if _event_index(actor["log"], event) > _event_index(actor["log"], failure)]
    require(any(event.get("choice") == "patrol" for event in after_failure),
            "actor did not autonomously switch to patrol after stale get")
    require(all(event.get("choice") != "deliver_supply"
                for event in after_failure
                if event.get("goal", {}).get("delivery_status") == "SUSPENDED_LOCAL_ITEM_UNAVAILABLE"),
            "delivery retried while locally unavailable")
    moves = [receipt for receipt in actor.get("native_receipts", [])
             if receipt.get("kind") == "move" and receipt.get("goal") == "patrol"
             and receipt.get("settled") is True]
    require(moves, "actor never settled a patrol move")

    if scenario == "C1a-blocked-switch":
        require(not [receipt for receipt in actor.get("native_receipts", [])
                     if receipt.get("kind") in {"get", "drop"}],
                "blocked-switch unexpectedly recovered or delivered")
        return {"scenario": scenario, "scene_id": response["trace"]["scene_id"],
                "stale_native_get_rejected": True, "settled_patrol_moves": len(moves),
                "delivery_contract_retained": True}

    player_drops = [entry for entry in interventions
                    if entry.get("command_receipt", {}).get("operation") == "drop"]
    require(len(player_drops) == 1
            and player_drops[0].get("label") == "player_returns_supply_to_original_room",
            "missing single native player return command")
    returned = player_drops[0]["command_receipt"]
    require(returned.get("intervention_kind") == "native-player-command"
            and returned.get("settled") is True and returned.get("item_location_id") == pickup_id,
            "player return did not settle in original room")
    negative = next((entry for entry in response.get("timeline", [])
                     if entry.get("kind") == "away_room_negative_observation"), None)
    require(negative is not None, "missing away-room negative observation")
    observed = negative.get("observation", {}).get("local_observation", {}).get("observation", {})
    away_actor = negative.get("snapshot", {}).get("actor", {})
    require(away_actor.get("room_id") != pickup_id and observed.get("room_id") == away_actor.get("room_id"),
            "negative observation was not made while actor was away")
    require(not any(str(row.get("id")) == str(item_id) for row in observed.get("visible_items", []))
            and observed.get("item_held") is False and observed.get("item_location") is None,
            "away-room observation leaked the returned parcel")
    neg_callback = next((entry for entry in callbacks if entry.get("callback_index") == 5), None)
    neg_choices = [event for event in (neg_callback or {}).get("new_log_events", [])
                   if event.get("kind") == "goal_choice"]
    require(len(neg_choices) == 1 and neg_choices[0].get("choice") == "patrol"
            and neg_choices[0].get("goal", {}).get("delivery_status") == "SUSPENDED_LOCAL_ITEM_UNAVAILABLE",
            "the first legal decision after away-room observation resumed too early")
    negative_log_index = _event_index(actor["log"], neg_choices[0])
    resumed = next((event for event in goals
                    if event.get("choice") == "deliver_supply"
                    and event.get("goal", {}).get("delivery_status") == "ACTIVE"
                    and _event_index(actor["log"], event) > negative_log_index
                    and any(str(row.get("id")) == str(item_id)
                            for row in event.get("view", {}).get("observation", {}).get("visible_items", []))), None)
    require(resumed is not None,
            "delivery did not resume only after a subsequent visible local observation")
    require(resumed.get("planner", {}).get("implementation") == "gtpyhop-core-2.0.2",
            "recovered delivery bypassed GTPyhop")
    successful = [receipt for receipt in actor.get("native_receipts", [])
                  if receipt.get("goal") == "deliver_supply"
                  and receipt.get("kind") in {"get", "move", "drop"}]
    require([receipt.get("kind") for receipt in successful] == ["get", "move", "drop"]
            and all(receipt.get("settled") is True and receipt.get("dispatch_succeeded") is True
                    for receipt in successful)
            and len({receipt.get("receipt_id") for receipt in successful}) == 3,
            "recovered task lacks exactly one settled get/move/drop sequence")
    return {"scenario": scenario, "scene_id": response["trace"]["scene_id"],
            "stale_native_get_rejected": True, "away_room_negative_control": True,
            "resume_after_local_visibility": True,
            "settled_delivery_receipts": [row["kind"] for row in successful]}


def audit_db(document, response, summary):
    require(document.get("schema") == "native-p3-db-evidence-v1"
            and document.get("source") == "initialized Evennia Django ORM; SQLite query_only enabled",
            "not a read-only initialized Evennia DB export")
    scene_id = response["trace"]["scene_id"]
    require(document.get("selection", {}).get("scene_ids") == [scene_id],
            "C1a export must name exactly this generated scene")
    scene = next((row for row in document.get("scenes", []) if row.get("scene_id") == scene_id), None)
    require(scene is not None, "scene missing from DB export")
    rows = scene.get("objects", [])
    by_id = {row.get("id"): row for row in rows}
    actor = _actor(response)
    actor_db = by_id.get(actor["id"])
    require(actor_db is not None, "courier missing in persisted DB")
    attrs = actor["attributes"]
    dbattrs = actor_db.get("attributes", {}).get("native_p3", {})
    require(dbattrs.get("native_receipts", []) == attrs.get("native_receipts", []),
            "trace and persisted native receipts differ")
    for key in ("log", "task_item_id", "task_item_key", "task_item_dbref",
                "task_destination_id", "task_destination_dbref", "activity_profile", "delivery_task"):
        require(dbattrs.get(key) == attrs.get(key),
                f"trace and persisted task/log field {key!r} differ")
    require(actor_db.get("location", {}).get("id") == actor.get("location_id"),
            "trace and persisted courier locations differ")
    parcel = by_id.get(attrs.get("task_item_id"))
    require(parcel is not None, "assigned parcel missing in DB scene")
    if summary["scenario"] == "C1a-observed-resume":
        require(parcel.get("location", {}).get("id") == attrs.get("task_destination_id"),
                "recovered parcel is not persisted at destination")
    else:
        player = next((row for row in rows
                       if row.get("attributes", {}).get("native_p3", {}).get("p3_control_role") == "player"), None)
        require(player is not None and parcel.get("location", {}).get("id") == player["id"],
                "blocked parcel is not persisted in the generated player's inventory")
    require(all(row.get("attributes", {}).get("native_p3", {}).get("p3_scene_id") == scene_id
                for row in rows), "DB export includes objects outside the generated scene")
    return len(rows)


def audit(run_path, db_path):
    run = read_json(run_path)
    require(run.get("schema") == "native-p3-c1a-run-artifact-v1", "unexpected run artifact schema")
    manifest = run.get("manifest", {})
    require(manifest.get("source_sha256") and manifest.get("source_snapshot_sha256"),
            "missing exact working-tree source manifest")
    response = run.get("response", {})
    scenario = run.get("configuration", {}).get("scenario")
    require(scenario in {"C1a-blocked-switch", "C1a-observed-resume"}, "unknown C1a scenario")
    summary = audit_trace(response, scenario)
    db_count = audit_db(read_json(db_path), response, summary)
    return {"status": "PASS", "scope": "bounded C1a development case and independent exact-scene ORM readback",
            "semantic_acceptance": summary, "db_scene_objects_checked": db_count,
            "inputs": {"run": {"file": run_path.name,
                               "sha256": hashlib.sha256(run_path.read_bytes()).hexdigest()},
                       "db": {"file": db_path.name,
                              "sha256": hashlib.sha256(db_path.read_bytes()).hexdigest()}}}


def write_audit(document, runs_dir=RUNS_DIR):
    runs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for _ in range(8):
        path = runs_dir / f"p3-c1a-audit-{stamp}-{secrets.token_hex(3)}.json"
        try:
            with path.open("x", encoding="utf-8") as handle:
                json.dump(document, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            return path
        except FileExistsError:
            continue
    raise FileExistsError("could not allocate unique C1a audit output")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = audit(args.run, args.db)
        path = write_audit(result, args.run.parent)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "PASS", "audit": str(path),
                      "scenario": result["semantic_acceptance"]["scenario"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
