"""Audit one P4-0 run against exact-scene read-only Evennia DB evidence.

The PASS status means the submitted ledger/trace/DB receipts are internally
consistent. The TypedIR verdict is reported separately and may be VIOLATED or
INDETERMINATE; this auditor does not turn a scenario outcome into a method claim.
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

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.native_platform_v0.p3.p4_monitor import (
    LEDGER_PRODUCER, author_constraint, choose_director, evaluate_author_constraint,
)
from tools.native_platform_v0.p3.p4_runner import RUNS_DIR


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_json(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"{path}: expected JSON object")
    return document


def _rows(response: dict[str, Any], event_type: str | None = None) -> list[dict[str, Any]]:
    rows = response.get("ledger")
    require(isinstance(rows, list), "P4 ledger must be an array")
    return [row for row in rows if event_type is None or row.get("event_type") == event_type]


def _object_by_id(trace: dict[str, Any], object_id: int) -> dict[str, Any]:
    found = [row for row in trace.get("objects", []) if row.get("id") == object_id]
    require(len(found) == 1, f"expected exactly one trace object #{object_id}")
    return found[0]


def _validate_ledger(response: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    require(response.get("schema") == "native-p4-run-v1", "unexpected P4 response schema")
    ledger = _rows(response)
    require(response.get("timeline") == ledger, "timeline is not an exact copy of the append-only ledger")
    ids: set[str] = set()
    sequence_keys: set[tuple[int, int]] = set()
    previous = (-1, -1)
    for row in ledger:
        require(isinstance(row, dict), "P4 ledger contains a non-object row")
        require(row.get("event_version") == 1 and row.get("producer_version") == LEDGER_PRODUCER,
                "P4 ledger row does not match the pinned server producer/version")
        event_id, minute, sequence = row.get("event_id"), row.get("minute"), row.get("sequence")
        require(isinstance(event_id, str) and bool(event_id) and type(minute) is int
                and type(sequence) is int and 0 <= minute <= config["deadline_minutes"]
                and sequence > 0, "P4 ledger event identity/time/sequence is malformed")
        key = (minute, sequence)
        require(event_id not in ids and key not in sequence_keys and key > previous,
                "P4 ledger event IDs or event order keys are duplicate/reordered")
        require(isinstance(row.get("typed_args"), dict) and type(row.get("sealed")) is bool,
                "P4 ledger row lacks typed payload/seal state")
        ids.add(event_id); sequence_keys.add(key); previous = key

    clock = response.get("clock", {})
    seal = response.get("ledger_sealed_through", {})
    deadline = config["deadline_minutes"]
    require(clock == {"now": deadline, "unit": "simulated-minute", "step_minutes": 1,
                      "deadline": deadline, "sealed": True,
                      "source": "server_owned_pickup.p4_clock"},
            "clock is not the server-owned final simulated-minute clock")
    require(isinstance(seal, dict) and seal.get("closed") is True
            and seal.get("minute") == deadline
            and seal.get("sequence") == (ledger[-1]["sequence"] if ledger else 0),
            "ledger completeness seal does not cover its final deadline prefix")
    return {"ledger_events": len(ledger),
            "unsealed_rows": sum(row.get("sealed") is not True for row in ledger),
            "deadline_minutes": deadline}


def _validate_scene_and_callbacks(response: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    created = response.get("created_scene", {})
    require(created.get("activity_profile") == "p4_story_v0"
            and created.get("mode") == "b" and created.get("drive_mode") == "manual",
            "P4 scene profile/mode/drive mismatch")
    require(created.get("initial_clock") == {"now": 0, "unit": "simulated-minute",
            "step_minutes": 1, "deadline": config["deadline_minutes"]},
            "P4 initial server clock does not match frozen deadline")
    expected_closed = config["case"] != "open"
    require(created.get("initial_east_closed") is expected_closed
            and config.get("initial_east_closed") is expected_closed,
            "initial passage state differs from fixed case")
    roles = created.get("roles", {})
    require(set(roles) == {"courier", "resident", "player"}, "P4 scene must have exactly two NPCs and one test player")
    role_ids = {role: item.get("id") for role, item in roles.items()}
    require(all(type(value) is int and value > 0 for value in role_ids.values())
            and len(set(role_ids.values())) == 3, "P4 role IDs are invalid or collide")
    require(roles["courier"].get("ensemble_role") == "hero"
            and roles["resident"].get("ensemble_role") == "love", "P4 Ensemble role binding changed")
    items = created.get("items", {})
    require(set(items) == {"courier_supply", "resident_parcel"}
            and all(type(row.get("id")) is int and row.get("key") for row in items.values()),
            "P4 scene must preserve the two original assigned parcels")
    require(response.get("callbacks_completed") is True
            and response.get("controller_authored_npc_commands") == 0,
            "run is incomplete or test controller directly commanded an NPC")

    callbacks = _rows(response, "NPC_CALLBACK")
    deadline = config["deadline_minutes"]
    require(len(callbacks) == deadline * 2,
            "P4 did not record one callback per NPC for every simulated minute")
    expected = {(minute, role) for minute in range(1, deadline + 1)
                for role in ("courier", "resident")}
    seen: set[tuple[int, str]] = set()
    for row in callbacks:
        args = row["typed_args"]
        role = args.get("role")
        require(role in {"courier", "resident"} and args.get("actor_id") == role_ids[role],
                "NPC callback actor identity/role mismatch")
        require(args.get("callback_index") == row["minute"]
                and args.get("awaited") is True,
                "NPC callback not awaited or minute index is inconsistent")
        pair = (row["minute"], role)
        require(pair not in seen, "duplicate NPC callback for one actor/minute")
        seen.add(pair)
        before, after = args.get("before", {}), args.get("after", {})
        require(isinstance(before.get("inventory_ids"), list)
                and isinstance(after.get("inventory_ids"), list),
                "NPC callback omits native before/after state")
        local = args.get("local_decision_events", [])
        require(isinstance(local, list), "NPC callback local events are malformed")
        for event in local:
            if isinstance(event, dict) and event.get("kind") == "goal_choice":
                require(event.get("activity_profile", {}).get("profile") == "p4_story_v0",
                        "P4 NPC callback used a different actor profile")
                view = event.get("view", {}).get("observation", {})
                require("all_objects" not in view and "global_world" not in view,
                        "actor-local planner input contains a global-world projection")
    require(seen == expected, "callback schedule has a missing or extra actor/minute")
    return {"scene_id": created.get("scene_id"), "actor_callbacks": len(callbacks),
            "role_ids": role_ids, "item_ids": {key: row["id"] for key, row in items.items()}}


def _validate_director(response: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    decisions = _rows(response, "DIRECTOR_DECISION")
    opens = _rows(response, "AUTHOR_WORLD_EVENT")
    require(len(decisions) == config["deadline_minutes"],
            "fixed director must make one bounded selection per simulated minute")
    open_events = []
    for row in decisions:
        args = row["typed_args"]
        view = args.get("authorized_view")
        expected = choose_director(view, config["director_enabled"])
        require(args.get("enabled") is config["director_enabled"]
                and args.get("candidate_actions") == expected["candidates"]
                and args.get("action") == expected["action"]
                and args.get("reason") == expected["reason"],
                "director decision is inconsistent with its fixed public-view rule")
        if args.get("action") == "OPEN_PASSAGE":
            open_events.append(row)
    require(len(open_events) <= 1 and len(opens) == len(open_events),
            "author world effect count differs from authorized one-shot passage action")
    for event in opens:
        args = event["typed_args"]
        match = next((row for row in open_events if row["minute"] == event["minute"]
                      and row["sequence"] < event["sequence"]), None)
        require(match is not None and args.get("action") == "OPEN_PASSAGE"
                and args.get("settled") is True
                and args.get("before") == {"east_closed": True, "opportunity_used": False}
                and args.get("after") == {"east_closed": False, "opportunity_used": True}
                and args.get("west_exit_unchanged") is True
                and args.get("state_scope") == ["generated_east_exit.traverse", "p4_opportunity_used"],
                "author action changed state outside its one permitted exit-lock opportunity")
    if not config["director_enabled"]:
        require(not opens, "director-off arm changed author-controlled world state")
    return {"director_decisions": len(decisions), "settled_author_actions": len(opens)}


def _validate_interventions(response: dict[str, Any], config: dict[str, Any], item_ids: dict[str, int]) -> list[tuple]:
    rows = _rows(response, "PLAYER_INTERVENTION")
    case = config["case"]
    expected_ops = [] if case == "open" else ["get"]
    if case in {"blocked-return", "short-deadline"}:
        expected_ops.append("drop")
    require(len(rows) == len(expected_ops), "player intervention count differs from frozen case")
    summary = []
    expected_minute = {"get": 1, "drop": 6}
    for row, operation in zip(rows, expected_ops):
        args = row["typed_args"]
        expected_item = item_ids["courier_supply"]
        receipt = args.get("command_receipt", {})
        require(row["minute"] == expected_minute[operation]
                and args.get("actor_role") == "player"
                and args.get("operation") == operation
                and args.get("item_id") == expected_item
                and args.get("settled") is True
                and receipt.get("intervention_kind") == "native-player-command"
                and receipt.get("settled") is True,
                "player intervention did not settle the only authorized external world action")
        summary.append((row["minute"], operation, "courier_supply"))
    return summary


def _validate_social_and_author_goal(response: dict[str, Any], run: dict[str, Any], db: dict[str, Any],
                                     scene_summary: dict[str, Any]) -> dict[str, Any]:
    ledger = response["ledger"]
    role_ids = scene_summary["role_ids"]
    request_rows = [row for row in ledger if row["event_type"] == "SOCIAL_REQUEST"
                    and row.get("typed_args", {}).get("physical_receipt", {}).get("status") == "settled"]
    response_rows = [row for row in ledger if row["event_type"] == "SOCIAL_RESPONSE"
                     and row.get("typed_args", {}).get("decision") in {"accepted", "rejected"}
                     and row.get("typed_args", {}).get("native_commit_status") == "settled"]
    commits = _rows(response, "SOCIAL_COMMIT")
    require(len(request_rows) <= 1 and len(response_rows) <= 1 and len(commits) <= 1,
            "P4 scene contains duplicate physical note requests/responses/commits")

    actors = response.get("trace", {}).get("objects", [])
    courier = _object_by_id(response["trace"], role_ids["courier"])
    resident = _object_by_id(response["trace"], role_ids["resident"])
    courier_attrs = courier.get("attributes", {})
    resident_attrs = resident.get("attributes", {})
    initial_items = scene_summary["item_ids"]
    for role, actor, item_name in (("courier", courier_attrs, "courier_supply"),
                                    ("resident", resident_attrs, "resident_parcel")):
        require(actor.get("activity_profile") == "p4_story_v0"
                and actor.get("delivery_task") is True
                and actor.get("task_item_id") == initial_items[item_name],
                f"{role} original authored delivery contract was changed")
    # The native-social decision is private to the resident callback. It may be
    # exported for audit but must not appear in the courier actor's own log.
    require(not any("native_volitions" in json.dumps(row, ensure_ascii=False)
                    for row in courier_attrs.get("log", [])),
            "resident private native volitions leaked into courier actor log")

    verdict = evaluate_author_constraint(
        ledger, now=response["clock"]["now"],
        deadline=response["configuration"]["deadline_minutes"],
        ledger_sealed_through=response.get("ledger_sealed_through"),
        scene_roles={"courier": role_ids["courier"], "resident": role_ids["resident"]},
    )
    interaction = None
    if response_rows:
        settled = response_rows[0]
        args = settled["typed_args"]
        request = next((row for row in request_rows
                        if row["typed_args"].get("request_id") == args.get("request_id")
                        and row["typed_args"].get("note_id") == args.get("note_id")), None)
        commit = next((row for row in commits
                       if row["typed_args"].get("request_id") == args.get("request_id")
                       and row["typed_args"].get("note_id") == args.get("note_id")
                       and row["typed_args"].get("action_name") == args.get("selected_action")), None)
        callback = next((row for row in _rows(response, "NPC_CALLBACK")
                         if row["typed_args"].get("role") == "resident"
                         and row["typed_args"].get("actor_id") == role_ids["resident"]
                         and row["minute"] == settled["minute"]
                         and any(event.get("kind") == "p4_social_response"
                                 and event.get("request_id") == args.get("request_id")
                                 and event.get("note_id") == args.get("note_id")
                                 and event.get("action_name") == args.get("selected_action")
                                 and event.get("native_volitions") == args.get("native_volitions")
                                 and event.get("native_candidates") == args.get("native_candidates")
                                 for event in row["typed_args"].get("local_decision_events", []))), None)
        require(request is not None and callback is not None and commit is not None,
                "response is not joined to the same physical request, B-owned native callback, and native commit")
        require(request["sequence"] < settled["sequence"] < commit["sequence"]
                and settled["minute"] >= request["minute"]
                and settled["minute"] == commit["minute"],
                "request/response/commit ledger order is invalid")
        require(args.get("initiator_actor_id") == role_ids["courier"]
                and args.get("responder_actor_id") == role_ids["resident"]
                and args.get("responder_role") == "love"
                and args.get("decision") in {"accepted", "rejected"}
                and args.get("selected_action") in {"writeLoveNoteAccept", "writeLoveNoteReject"},
                "native response is not the real A-to-B accepted/refused family action")
        require((args["decision"] == "accepted") == (args["selected_action"] == "writeLoveNoteAccept"),
                "native selection and committed response polarity disagree")
        physical = args.get("physical_receipt", {})
        require(physical.get("status") == "settled"
                and physical.get("same_note_id") == args.get("note_id")
                and physical.get("actor_id") == role_ids["resident"]
                and physical.get("before_location_id") == role_ids["resident"]
                and physical.get("after_location_id") == role_ids["resident"],
                "response did not physically settle on the same note in B's inventory")
        note = next((row for row in actors
                     if row.get("id") == args.get("note_id")), None)
        require(note is not None and note.get("location_id") == role_ids["resident"]
                and note.get("attributes", {}).get("p4_note_status") == args["decision"]
                and note.get("attributes", {}).get("p4_note_action") == args["selected_action"],
                "actual Evennia note state does not match the sealed response")
        interaction = {"decision": args["decision"], "selected_action": args["selected_action"],
                       "note_id": args["note_id"], "request_id": args["request_id"],
                       "native_response_and_commit_joined": True,
                       "resident_callback_minute": callback["minute"]}

    # Match the sealed run objects to the separate query-only ORM export.
    scene_id = response["created_scene"]["scene_id"]
    require(db.get("schema") == "native-p3-db-evidence-v1"
            and db.get("source") == "initialized Evennia Django ORM; SQLite query_only enabled"
            and db.get("selection", {}).get("scene_ids") == [scene_id],
            "P4 database export is not a query-only allowlist of this exact scene")
    scenes = [scene for scene in db.get("scenes", []) if scene.get("scene_id") == scene_id]
    require(len(scenes) == 1, "P4 scene missing or duplicated in DB evidence")
    db_rows = {row.get("id"): row for row in scenes[0].get("objects", [])}
    require(set(db_rows) == {row.get("id") for row in actors},
            "trace and persisted ORM scene object sets differ")
    for row in actors:
        persisted = db_rows[row["id"]]
        require(persisted.get("key") == row.get("key")
                and (persisted.get("location") or {}).get("id") == row.get("location_id"),
                "trace and persisted object identity/location differ")
        persisted_attrs = persisted.get("attributes", {}).get("native_p3", {})
        for key, value in row.get("attributes", {}).items():
            require(persisted_attrs.get(key) == value,
                    f"trace and persisted DB attribute {key!r} differ")
    pickup_attrs = db_rows[response["created_scene"]["rooms"]["pickup"]["id"]]["attributes"]["native_p3"]
    raw_clock = {key: response["clock"][key]
                 for key in ("now", "unit", "step_minutes", "deadline")}
    require(pickup_attrs.get("p4_ledger") == ledger
            and pickup_attrs.get("p4_ledger_seal") == response.get("ledger_sealed_through")
            and pickup_attrs.get("p4_clock") == raw_clock,
            "ledger/clock/seal response does not match independent persisted DB readback")
    return {"typedir_author_constraint": verdict,
            "settled_note_interaction": interaction,
            "sealed_successful_response_count": len(response_rows),
            "persisted_scene_objects_checked": len(db_rows)}


def audit_one(run: dict[str, Any], db: dict[str, Any]) -> dict[str, Any]:
    require(run.get("schema") == "native-p4-run-artifact-v1", "unexpected P4 run artifact schema")
    require(run.get("response", {}).get("run_status") == "COMPLETE",
            "run is INCOMPLETE; preserve as a diagnostic and do not grade it")
    manifest = run.get("manifest", {})
    require(isinstance(manifest.get("source_sha256"), dict)
            and manifest.get("source_snapshot_sha256"), "P4 source manifest missing")
    config = run.get("configuration", {})
    response = run.get("response", {})
    expected_cases = {"open", "blocked-return", "blocked-held", "short-deadline"}
    require(config.get("case") in expected_cases
            and type(config.get("director_enabled")) is bool
            and config.get("seed") in {20261010, 20261011}, "P4 run configuration outside frozen matrix")
    require(response.get("configuration", {}).get("case") == config["case"]
            and response["configuration"].get("director_enabled") is config["director_enabled"]
            and response["configuration"].get("seed") == config["seed"],
            "runner configuration does not match native response")
    expected_deadline = 6 if config["case"] == "short-deadline" else 24
    require(response["configuration"].get("deadline_minutes") == expected_deadline,
            "case deadline differs from fixed 6/24 minute protocol")
    ledger_summary = _validate_ledger(response, response["configuration"])
    scene_summary = _validate_scene_and_callbacks(response, response["configuration"])
    director_summary = _validate_director(response, response["configuration"])
    interventions = _validate_interventions(response, response["configuration"], scene_summary["item_ids"])
    social_summary = _validate_social_and_author_goal(response, run, db, scene_summary)
    return {"case": config["case"], "director_enabled": config["director_enabled"],
            "seed": config["seed"], **ledger_summary, **scene_summary, **director_summary,
            "player_interventions": interventions, **social_summary}


def _normalized_initial(run: dict[str, Any]) -> dict[str, Any]:
    response = run["response"]
    config = dict(response["configuration"])
    config.pop("director_enabled", None)
    created = response["created_scene"]
    roles = created["roles"]
    return {"configuration": config,
            "scene": {"mode": created["mode"], "case": created.get("case"),
                      "activity_profile": created["activity_profile"],
                      "drive_mode": created["drive_mode"], "initial_clock": created["initial_clock"],
                      "initial_east_closed": created["initial_east_closed"],
                      "ensemble_roles": {role: roles[role].get("ensemble_role")
                                         for role in ("courier", "resident")},
                      "roles": sorted(roles), "items": sorted(created["items"]),
                      "initial_west_exit": created.get("initial_west_exit")},
            "source_manifest": created.get("ensemble_source_manifest"),
            "manifest_source_sha256": run.get("manifest", {}).get("source_sha256")}


def audit_pair(run_a: dict[str, Any], run_b: dict[str, Any]) -> dict[str, Any]:
    ca, cb = run_a["configuration"], run_b["configuration"]
    require(ca["case"] == cb["case"] and ca["seed"] == cb["seed"]
            and ca["director_enabled"] is not cb["director_enabled"],
            "paired audit requires one case/seed with only director_enabled flipped")
    require(_normalized_initial(run_a) == _normalized_initial(run_b),
            "paired actors/tasks/initial config differ beyond director_enabled")
    def schedule(run):
        response = run["response"]
        items = response["created_scene"]["items"]
        names = {value["id"]: key for key, value in items.items()}
        return [(row["minute"], row["typed_args"].get("actor_role"),
                 row["typed_args"].get("label"),
                 row["typed_args"].get("operation"), names.get(row["typed_args"].get("item_id")))
                for row in response["ledger"] if row["event_type"] == "PLAYER_INTERVENTION"]
    schedule_a, schedule_b = schedule(run_a), schedule(run_b)
    require(schedule_a == schedule_b, "paired player intervention timing/target differs")
    return {"paired": True, "case": ca["case"], "seed": ca["seed"],
            "replication_type": "paired_development_replication_not_random_sample",
            "only_author_arm_changed": "director_enabled", "normalized_player_schedule": schedule_a}


def write_audit(document: dict[str, Any], runs_dir: Path = RUNS_DIR) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for _ in range(8):
        path = runs_dir / f"p4-audit-{stamp}-{secrets.token_hex(3)}.json"
        try:
            with path.open("x", encoding="utf-8") as handle:
                json.dump(document, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            return path
        except FileExistsError:
            continue
    raise FileExistsError("could not allocate unique P4 audit filename")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--paired-run", type=Path)
    parser.add_argument("--paired-db", type=Path)
    args = parser.parse_args(argv)
    if bool(args.paired_run) != bool(args.paired_db):
        parser.error("--paired-run and --paired-db must be provided together")
    paths = [("run", args.run), ("db", args.db)]
    if args.paired_run:
        paths.extend([("paired_run", args.paired_run), ("paired_db", args.paired_db)])
    inputs = []
    for label, path in paths:
        inputs.append({label: path.name, f"{label}_sha256":
                       hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None})
    pair_summary = None
    try:
        run = read_json(args.run); db = read_json(args.db)
        summary = audit_one(run, db)
        if args.paired_run:
            paired_run = read_json(args.paired_run); paired_db = read_json(args.paired_db)
            paired_summary = audit_one(paired_run, paired_db)
            pair_summary = audit_pair(run, paired_run)
            summary["paired_arm"] = paired_summary
        status = "PASS"
        reason = None
    except Exception as err:
        summary = {}
        status = "INDETERMINATE"
        reason = f"{type(err).__name__}: {err}"
    document = {"schema": "native-p4-audit-v1", "created_at": datetime.now(timezone.utc).isoformat(),
                "status": status, "reason": reason,
                "scope": "bounded P4-0 ledger, actor, author-effect, and exact-scene DB consistency",
                "summary": summary, "paired_comparison": pair_summary, "inputs": inputs}
    output = write_audit(document)
    print(json.dumps({"status": status, "audit": str(output), "reason": reason,
                      "summary": document["summary"], "paired_comparison": pair_summary},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
