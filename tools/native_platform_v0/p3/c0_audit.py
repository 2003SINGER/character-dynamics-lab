"""Narrow semantic audit for the three P3-C0 runs plus SQLite ORM readback."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.native_platform_v0.p3.c0_runner import RUNS_DIR


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a JSON object")
    return value


def log_events(actor: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    return [event for event in actor.get("log", []) if event.get("kind") == kind]


def scene_actor(scene: dict[str, Any]) -> dict[str, Any]:
    rows = [row for row in scene["trace"].get("objects", [])
            if row.get("attributes", {}).get("p3_control_role") == "courier"]
    require(len(rows) == 1, f"{scene.get('role', 'C0')}: expected one generated courier")
    return rows[0]


def settled_receipts(actor: dict[str, Any], kind: str) -> list[dict[str, Any]]:
    attrs = actor.get("attributes", actor)
    return [receipt for receipt in attrs.get("native_receipts", [])
            if receipt.get("kind") == kind and receipt.get("settled") is True
            and receipt.get("dispatch_succeeded") is True]


def _check_local_goal_evidence(actor: dict[str, Any], label: str) -> list[dict[str, Any]]:
    goals = log_events(actor["attributes"], "goal_choice")
    require(goals, f"{label}: no persisted goal-choice evidence")
    for event in goals:
        require(event.get("activity_profile", {}).get("profile") == "delivery_patrol_v0",
                f"{label}: goal choice lacks opt-in activity profile")
        view = event.get("view", {})
        observation = view.get("observation", {})
        require(isinstance(observation.get("room_id"), int), f"{label}: local observation has no room")
        require(isinstance(observation.get("exits"), list), f"{label}: local observation has no visible exits")
        require(isinstance(observation.get("visible_items"), list), f"{label}: local observation has no visible-item projection")
        require("world" not in view and "all_objects" not in observation,
                f"{label}: trace contains a global-world projection in the planner view")
    return goals


def check_no_delivery(response: dict[str, Any]) -> tuple[list[str], dict[str, Any]]:
    require(response.get("scenario") == "C0-no-delivery", "wrong no-delivery run")
    require(response.get("controller_interventions") == 0, "no-delivery case contains controller interventions")
    scenes = response.get("scenes", [])
    require([scene.get("role") for scene in scenes] == ["no_delivery_primary", "locked_exit_negative_control"],
            "no-delivery run must contain the primary and one locked-exit negative-control scene")
    primary, negative = scenes
    require(len(primary.get("callbacks", [])) == 12 and len(negative.get("callbacks", [])) == 10,
            "no-delivery case did not use its bounded 12/10 callback limits")
    require(primary["configuration"].get("delivery_task") is False, "primary scene has a delivery task")
    actor_row = scene_actor(primary)
    actor = actor_row["attributes"]
    require(actor.get("task_item_id") is None and actor.get("task_item_dbref") is None,
            "no-delivery actor has an assigned parcel")
    goals = _check_local_goal_evidence(actor_row, "C0-no-delivery")
    require(all(event.get("choice") == "patrol" and event.get("candidates") == ["patrol"] for event in goals),
            "no-delivery actor did not consistently select patrol")
    moves = settled_receipts(actor_row, "move")
    require(moves, "no-delivery actor has no settled native patrol move")
    require(all(receipt.get("goal") == "patrol" for receipt in moves), "a settled move was not selected as patrol")
    require(not settled_receipts(actor_row, "drop"), "no-delivery actor has a drop receipt")
    require(actor_row.get("location_id") == moves[-1].get("after_room_id"),
            "final live actor location disagrees with the last settled patrol move")

    negative_actor_row = scene_actor(negative)
    negative_actor = negative_actor_row["attributes"]
    require(negative.get("configuration", {}).get("delivery_task") is False
            and negative.get("configuration", {}).get("patrol_exit_locked") is True,
            "negative-control scene lacks its taskless locked-exit configuration")
    negative_goals = _check_local_goal_evidence(negative_actor_row, "C0 locked-exit control")
    require(negative_goals and all(event.get("choice") == "patrol" for event in negative_goals),
            "locked-exit actor did not select patrol")
    rejected = [event for event in log_events(negative_actor, "execution_settlement")
                if event.get("status") == "WORLD_VALIDATION_REJECTED"
                and event.get("receipt", {}).get("settled") is False]
    require(len(rejected) == 1, "locked-exit control must contain exactly one actual rejected movement")
    require(rejected[0].get("receipt", {}).get("kind") == "move"
            and rejected[0].get("receipt", {}).get("submitted_command") in {"east", "west"},
            "locked-exit rejection lacks an actual native movement command")
    reject_receipt = rejected[0]["receipt"]
    require(reject_receipt.get("before_room_id") == reject_receipt.get("after_room_id")
            == negative_actor_row.get("location_id"),
            "locked-exit rejection does not match the unchanged final actor location")
    move_intents = [event for event in log_events(negative_actor, "primitive_intent")
                    if event.get("pending_action", {}).get("intent", {}).get("operator") == "move"]
    require(len(move_intents) == 1, "locked-exit move was retried after its observed rejection")
    require(len(negative.get("callbacks", [])) >= 10, "locked-exit control lacks bounded post-rejection callbacks")
    rejected_index = rejected[0].get("receipt", {}).get("receipt_id")
    require(rejected_index, "locked-exit rejection has no typed receipt ID")
    require(not settled_receipts(negative_actor_row, "move"), "rejected locked-exit move was recorded as settled")
    return [primary["trace"]["scene_id"], negative["trace"]["scene_id"]], {
        "scenario": "C0-no-delivery", "patrol_moves": len(moves),
        "locked_exit_rejections": 1, "locked_exit_move_retries": 0,
        "scene_ids": [primary["trace"]["scene_id"], negative["trace"]["scene_id"]],
    }


def check_delivery(response: dict[str, Any], after: bool) -> tuple[list[str], dict[str, Any]]:
    scenario = "C0-after-delivery" if after else "C0-delivery-priority"
    require(response.get("scenario") == scenario, f"wrong {scenario} run")
    require(response.get("controller_interventions") == 0, f"{scenario}: controller intervention detected")
    trace = response.get("trace", {})
    callbacks = response.get("callbacks", [])
    expected_callbacks = 20 if after else 12
    require(len(callbacks) == expected_callbacks and response.get("callback_limit") == expected_callbacks,
            f"{scenario}: callback count does not match its fixed bounded case")
    require(all(callback.get("step", {}).get("scene_id") == trace.get("scene_id") for callback in callbacks),
            f"{scenario}: callback sequence switched scenes instead of continuing the same instance")
    actor_row = next((row for row in trace.get("objects", [])
                      if row.get("attributes", {}).get("p3_control_role") == "courier"), None)
    require(actor_row is not None, f"{scenario}: missing courier")
    actor = actor_row["attributes"]
    require(actor.get("delivery_task") is True and actor.get("activity_profile") == "delivery_patrol_v0",
            f"{scenario}: wrong activity configuration")
    goals = _check_local_goal_evidence(actor_row, scenario)
    receipts = actor.get("native_receipts", [])
    drops = [receipt for receipt in receipts if receipt.get("kind") == "drop"]
    require(len(drops) == 1 and drops[0].get("settled") is True
            and drops[0].get("dispatch_succeeded") is True,
            f"{scenario}: expected exactly one settled native drop receipt")
    task_id = actor.get("task_item_id")
    destination_id = actor.get("task_destination_id")
    require(task_id is not None and drops[0].get("item_id") == task_id,
            f"{scenario}: drop receipt does not match assigned parcel")
    require(drops[0].get("after_item_room_id") == destination_id,
            f"{scenario}: parcel was not observed at its assigned destination after drop")
    delivery_receipts = [receipt for receipt in receipts if receipt.get("kind") in {"get", "move", "drop"}
                         and (receipt.get("goal") != "patrol" or receipt.get("kind") != "move")]
    require([receipt.get("kind") for receipt in delivery_receipts] == ["get", "move", "drop"],
            f"{scenario}: expected one native get/move/drop delivery sequence before patrol receipts")
    require(all(receipt.get("settled") is True and receipt.get("dispatch_succeeded") is True
                for receipt in delivery_receipts), f"{scenario}: a delivery receipt did not settle")
    require(len({receipt.get("receipt_id") for receipt in delivery_receipts}) == 3,
            f"{scenario}: duplicate delivery receipt IDs")
    drop_index = next((i for i, event in enumerate(actor.get("log", []))
                       if event.get("kind") == "execution_settlement"
                       and event.get("receipt", {}).get("receipt_id") == drops[0].get("receipt_id")), None)
    require(drop_index is not None, f"{scenario}: drop receipt missing from full actor log")
    patrol_after = [event for event in goals if event.get("choice") == "patrol"
                    and actor.get("log", []).index(event) > drop_index]
    # For delivery-priority, patrol is permitted only after the drop. The
    # after-delivery case additionally requires a real settled patrol move.
    patrol_choices = [event for event in goals if event.get("choice") == "patrol"]
    if after:
        require(patrol_choices, "after-delivery actor never selected patrol")
        require(patrol_after, "after-delivery patrol selection did not occur after the settled drop")
        require(len(patrol_after) == len(patrol_choices), "after-delivery has patrol selected before delivery settled")
        require(not [event for event in goals if event.get("choice") == "deliver_supply"
                     and actor.get("log", []).index(event) > drop_index],
                "after-delivery restarted delivery after its settled drop")
        patrol_moves = [receipt for receipt in settled_receipts(actor_row, "move")
                        if receipt.get("goal") == "patrol"]
        require(patrol_moves, "after-delivery actor has no settled patrol movement")
        require(any(event.get("choice") == "deliver_supply" for event in goals),
                "after-delivery trace lacks pre-completion delivery selection")
    else:
        require(all(event.get("choice") == "deliver_supply" for event in goals if event.get("choice") != "patrol")
                and (not patrol_choices or all(event in patrol_after for event in patrol_choices)),
                "delivery did not retain priority until the settled drop")
        require(any("gtpyhop" in str(event.get("planner", {}).get("implementation", "")).casefold()
                    or "gtpyhop" in str(event.get("planner", {}).get("planner", "")).casefold()
                    for event in goals),
                "delivery trace does not show GTPyhop planning")
    return [trace["scene_id"]], {
        "scenario": scenario, "scene_ids": [trace["scene_id"]],
        "settled_drop_receipts": 1, "patrol_selected": bool(patrol_choices),
        "settled_patrol_moves": len([receipt for receipt in settled_receipts(actor_row, "move")
                                     if receipt.get("goal") == "patrol"]),
    }


def check_db(document: dict[str, Any], expected_scene_ids: list[str], summaries: list[dict[str, Any]],
             run_responses: list[dict[str, Any]]) -> int:
    require(document.get("schema") == "native-p3-db-evidence-v1", "unexpected DB evidence schema")
    require(document.get("source") == "initialized Evennia Django ORM; SQLite query_only enabled",
            "DB evidence is not read-only initialized Evennia ORM state")
    scenes = {scene.get("scene_id"): scene for scene in document.get("scenes", [])}
    require(set(expected_scene_ids) <= set(scenes), "DB export omits a scene from the audited run")
    require(set(document.get("selection", {}).get("scene_ids", [])) == set(scenes),
            "DB export rows do not match its explicit scene allowlist")
    expected_actors = {}
    for response in run_responses:
        raw_scenes = response.get("scenes", [])
        traces = [scene.get("trace", {}) for scene in raw_scenes] if raw_scenes else [response.get("trace", {})]
        for trace in traces:
            for row in trace.get("objects", []):
                if row.get("attributes", {}).get("p3_control_role") == "courier":
                    expected_actors[trace["scene_id"]] = row
    checked = 0
    for scene_id, trace_actor in expected_actors.items():
        rows = scenes[scene_id].get("objects", [])
        by_id = {row.get("id"): row for row in rows}
        require(all(row.get("attributes", {}).get("native_p3", {}).get("p3_scene_id") == scene_id
                    for row in rows), f"{scene_id}: persisted scene marker mismatch")
        actor_db = by_id.get(trace_actor.get("id"))
        require(actor_db is not None, f"{scene_id}: actor is missing from independent DB export")
        live_attrs = trace_actor.get("attributes", {})
        db_attrs = actor_db.get("attributes", {}).get("native_p3", {})
        require(db_attrs.get("native_receipts", []) == live_attrs.get("native_receipts", []),
                f"{scene_id}: live trace and persisted receipt lists differ")
        require(actor_db.get("location", {}).get("id") == trace_actor.get("location_id"),
                f"{scene_id}: live trace and persisted actor location differ")
        move_receipts = [receipt for receipt in live_attrs.get("native_receipts", [])
                         if receipt.get("kind") == "move" and receipt.get("settled") is True]
        for previous, following in zip(move_receipts, move_receipts[1:]):
            require(previous.get("after_room_id") == following.get("before_room_id"),
                    f"{scene_id}: sequential settled move receipts do not form a location chain")
        if move_receipts:
            require(move_receipts[-1].get("after_room_id") == actor_db.get("location", {}).get("id"),
                    f"{scene_id}: last settled move does not match persisted actor location")
        if live_attrs.get("delivery_task") is True:
            task_id = live_attrs.get("task_item_id")
            destination_id = live_attrs.get("task_destination_id")
            drops = [receipt for receipt in live_attrs.get("native_receipts", [])
                     if receipt.get("kind") == "drop" and receipt.get("settled") is True]
            if drops:
                parcel = by_id.get(task_id)
                require(parcel is not None, f"{scene_id}: assigned parcel is missing from persisted scene rows")
                require(parcel.get("location", {}).get("id") == destination_id,
                        f"{scene_id}: persisted assigned parcel is not at the task destination")
        checked += 1
    require(checked == len(expected_scene_ids), "DB actor coverage does not match scene allowlist")
    return checked


def audit(run_path: Path, db_path: Path) -> dict[str, Any]:
    run = read_json(run_path)
    require(run.get("schema") in {"native-p3-c0-run-artifact-v1", "native-p3-c0-headless-run-v1"},
            "unexpected C0 runner artifact schema")
    source_hashes = run.get("manifest", {}).get("source_sha256") or run.get("source_sha256")
    source_snapshot = run.get("manifest", {}).get("source_snapshot_sha256")
    require(isinstance(source_hashes, dict) and source_hashes,
            "run artifact lacks working-tree source hashes")
    require(source_snapshot or run.get("source_revision"),
            "run artifact lacks source snapshot or base revision provenance")
    response = run.get("response", {})
    bounded_callbacks_done = response.get("callbacks_completed") is True or response.get("completed") is True
    require(response.get("schema") == "native-p3-c0-run-v1" and bounded_callbacks_done,
            "C0 bounded callback run is incomplete")
    require(response.get("completion_scope") == "bounded_callbacks_only_not_semantic_acceptance",
            "runner overstates callback completion as semantic acceptance")
    scenario = run.get("configuration", {}).get("scenario") or run.get("request", {}).get("scenario")
    require(scenario == response.get("scenario"), "run configuration and response scenario disagree")
    if scenario == "C0-no-delivery":
        scene_ids, summary = check_no_delivery(response)
    elif scenario == "C0-delivery-priority":
        scene_ids, summary = check_delivery(response, after=False)
    elif scenario == "C0-after-delivery":
        scene_ids, summary = check_delivery(response, after=True)
    else:
        raise ValueError("only the exact three named P3-C0 cases are accepted")
    db_checked = check_db(read_json(db_path), scene_ids, [summary], [response])
    return {"status": "PASS", "scope": "one bounded P3-C0 development run plus independent read-only DB readback",
            "semantic_acceptance": summary, "db_actor_rows_checked": db_checked,
            "inputs": {"run": {"file": run_path.name, "sha256": hashlib.sha256(run_path.read_bytes()).hexdigest()},
                       "db": {"file": db_path.name, "sha256": hashlib.sha256(db_path.read_bytes()).hexdigest()}}}


def write_audit(document: dict[str, Any], runs_dir: Path = RUNS_DIR) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for _ in range(8):
        target = runs_dir / f"p3-c0-audit-{timestamp}-{secrets.token_hex(3)}.json"
        try:
            with target.open("x", encoding="utf-8") as handle:
                json.dump(document, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            return target
        except FileExistsError:
            continue
    raise FileExistsError("could not allocate a unique C0 audit output")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True, help="one exact C0 run artifact")
    parser.add_argument("--db", type=Path, required=True, help="matching explicit-scene DB export")
    args = parser.parse_args(argv)
    try:
        result = audit(args.run, args.db)
        output = write_audit(result, args.run.parent)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "PASS", "audit": str(output),
                      "scenario": result["semantic_acceptance"]["scenario"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
