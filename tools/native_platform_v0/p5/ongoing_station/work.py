"""Native, clocked station work for the opt-in P5 ongoing-station profile.

This module owns only the small physical work protocol: one registered tool,
one exclusive lease, two registered tasks, and receipts derived from verified
Evennia before/after state. Planning never calls these effect functions.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from functools import wraps


CONTENT_VERSION = 1
TOOL_ALIAS = "shared_station_tool"
STORAGE_ALIAS = "station_storage"
REPAIR_EXIT_ALIAS = "pickup_to_side_south"
TASK_DURATIONS = {"inspect_supply": 2, "repair_passage": 3}
EVENT_TYPES = {
    "inspect_supply": "P5_STATION_SUPPLY_INSPECTED",
    "repair_passage": "P5_STATION_PASSAGE_REPAIRED",
    "store_supply": "P5_STATION_SUPPLY_STORED",
    "tool_lend": "P5_STATION_TOOL_LOANED",
    "tool_return": "P5_STATION_TOOL_RETURNED",
}


def _get(obj, key, default=None, category="native_p5"):
    return obj.attributes.get(key, category=category, default=default)


def _set(obj, key, value, category="native_p5"):
    obj.attributes.add(key, value, category=category)


def _append_receipt(actor, row):
    receipts = list(_get(actor, "station_work_receipts", [], category="native_p5"))
    if not any(old.get("receipt_id") == row.get("receipt_id") for old in receipts):
        receipts.append(deepcopy(row))
        _set(actor, "station_work_receipts", receipts)


def _atomic(function):
    """Keep lease/world/ledger transitions in one DB transaction in Evennia."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        try:
            from django.db import transaction
            from django.conf import settings
        except ImportError:  # pure unit tests need not initialize Django
            return function(*args, **kwargs)
        if not settings.configured:
            return function(*args, **kwargs)
        with transaction.atomic():
            return function(*args, **kwargs)
    return wrapped


def append_event(actor, event_type, event_id, args, receipt_id):
    from tools.native_platform_v0.p3.p4_world import append_event as append_ledger_event

    return append_ledger_event(actor, {"event_type": event_type, "event_id": event_id,
                                      "typed_args": deepcopy(dict(args)),
                                      "receipt_id": receipt_id, "sealed": True})


def initialize_content(pickup, destination, side, supply, tool, storage, repair_exit):
    """Register the concrete opt-in station fixtures without changing old scenes."""
    for obj in (tool, storage, supply, repair_exit):
        if _get(obj, "p3_scene_id", category="native_p3") != _get(pickup, "p3_scene_id", category="native_p3"):
            raise ValueError("station content objects must belong to the same generated scene")
    if tool.location != pickup or storage.location != destination or supply.location != pickup:
        raise ValueError("station tool, storage, and initial supply locations are not the registered fixture")
    if repair_exit.location != pickup or repair_exit.destination != side or repair_exit.key != "south":
        raise ValueError("repair target must be the registered Pickup-to-Side south exit")
    _set(tool, "p5_station_tool", True)
    _set(tool, "p5_item_alias", TOOL_ALIAS)
    _set(tool, "p5_station_workbench_room_id", int(pickup.id))
    _set(tool, "p5_station_tool_lease", {"status": "FREE", "lease_id": None,
                                         "actor_id": None, "commitment_id": None,
                                         "task_kind": None, "started_minute": None,
                                         "due_minute": None})
    _set(tool, "p5_station_active_loan", None)
    _set(storage, "p5_station_storage", True)
    _set(storage, "p5_item_alias", STORAGE_ALIAS)
    _set(supply, "p5_supply_inspection_status", "UNINSPECTED")
    _set(repair_exit, "p5_repair_target", True)
    _set(repair_exit, "p5_exit_alias", REPAIR_EXIT_ALIAS)
    _set(pickup, "p5_station_content_v1", {
        "version": CONTENT_VERSION, "tool_id": int(tool.id), "storage_id": int(storage.id),
        "supply_id": int(supply.id), "repair_exit_id": int(repair_exit.id),
        "repair_exit_alias": REPAIR_EXIT_ALIAS,
    })
    return deepcopy(_get(pickup, "p5_station_content_v1"))


@_atomic
def request_tool_loan(player, *, tool_id, lender_alias, borrower_alias, due_minute):
    """Record one real, co-present player request; never seed an NPC task/history."""
    from tools.native_platform_v0.p3.agency import get_value, set_value
    from tools.native_platform_v0.p5 import service

    def reject(reason):
        result = {"status": "WORLD_VALIDATION_REJECTED", "settled": False,
                  "reason": reason, "request": None}
        _set(player, "p5_station_last_loan_request_result", result)
        return deepcopy(result)

    if (_get(player, "p3_control_role", category="native_p3") != "player"
            or _get(player, "p5_station_profile_enabled") is not True):
        return reject("registered_generated_player_required")
    scene_id = _get(player, "p3_scene_id", category="native_p3")
    if not isinstance(scene_id, str) or not scene_id:
        return reject("generated_station_scene_required")
    pickup, rows = service._scene_objects(scene_id)
    content = _get(pickup, "p5_station_content_v1")
    if not isinstance(content, Mapping) or type(tool_id) is not int \
            or tool_id != content.get("tool_id"):
        return reject("exact_registered_station_tool_required")
    if lender_alias != "A" or borrower_alias != "B":
        return reject("registered_A_lender_and_B_borrower_required")
    actors = {str(_get(obj, "p5_actor_alias")): obj for obj in rows
              if _get(obj, "p5_actor_alias") in {"A", "B"}}
    lender, borrower = actors.get("A"), actors.get("B")
    tool = next((obj for obj in rows if int(obj.id) == tool_id), None)
    if lender is None or borrower is None or tool is None \
            or _get(tool, "p5_station_tool") is not True:
        return reject("registered_lender_borrower_or_tool_missing")
    room = getattr(player, "location", None)
    if (room is None or room != pickup or lender.location != room or borrower.location != room
            or player not in room.contents or lender not in room.contents or borrower not in room.contents):
        return reject("player_lender_borrower_must_be_co_present_at_workbench")
    if not lender.access(player, "view", default=True) or not borrower.access(player, "view", default=True):
        return reject("both_registered_actors_must_be_locally_witnessable")
    holder_alias = None
    if tool.location == room and tool not in room.contents:
        return reject("tool_location_is_not_a_grounded_workbench_item")
    if tool.location == lender and tool in lender.contents:
        holder_alias = "A"
    elif tool.location != room or tool not in room.contents:
        return reject("exact_tool_must_be_grounded_or_held_by_registered_lender")
    lease = _get(tool, "p5_station_tool_lease", {})
    active_loan = _get(tool, "p5_station_active_loan")
    if lease.get("status") != "FREE" or lease.get("lease_id") is not None:
        return reject("shared_tool_is_not_free")
    if isinstance(active_loan, Mapping) and active_loan.get("status") == "OUT":
        return reject("shared_tool_already_has_an_active_loan")
    if type(due_minute) is not int:
        return reject("absolute_due_minute_must_be_an_integer")
    # The generated player is an intervention source, not a P4 story actor;
    # read the one scene-owned P4 clock rather than asking clock_for_actor()
    # to grant the player actor-clock access.
    clock = _get(pickup, "p4_clock", category="native_p3")
    if (not isinstance(clock, Mapping) or type(clock.get("now")) is not int
            or type(clock.get("deadline")) is not int):
        return reject("server_owned_scene_p4_clock_is_missing_or_invalid")
    now, deadline = clock["now"], clock["deadline"]
    if not now < due_minute <= deadline:
        return reject("due_minute_must_be_after_now_and_within_native_deadline")

    request_no = int(_get(pickup, "p5_station_loan_request_counter", 0)) + 1
    _set(pickup, "p5_station_loan_request_counter", request_no)
    request = {"request_id": f"station-loan-request:{scene_id}:{request_no}",
               "lender_alias": "A", "borrower_alias": "B",
               "lender_id": int(lender.id), "borrower_id": int(borrower.id),
               "tool_id": int(tool.id), "tool_holder_alias": holder_alias,
               "due_minute": due_minute, "requested_minute": now,
               "requester_actor_id": int(player.id), "requester_room_id": int(room.id),
               "witnessed_by_aliases": ["A", "B"], "status": "REQUESTED",
               "settled": True, "provenance": "native_player_station_request_command"}
    # A single current request is actor-local witnessed information. Replacing
    # it does not erase physical loan/return receipts or fabricate prior history.
    for actor in (lender, borrower):
        _set(actor, "p5_station_loan_request", deepcopy(request))
    receipt_id = request["request_id"]
    receipt = {"receipt_id": receipt_id, "kind": "station_loan_request",
               "actor_id": int(player.id), "actor_alias": "player", "tool_id": int(tool.id),
               "lender_id": int(lender.id), "borrower_id": int(borrower.id),
               "lender_alias": "A", "borrower_alias": "B", "due_minute": due_minute,
               "sim_minute": now, "room_id": int(room.id), "settled": True,
               "provenance": "native_player_station_request_command"}
    receipts = list(get_value(player, "native_receipts", []))
    receipts.append(receipt)
    set_value(player, "native_receipts", receipts)
    result = {"status": "REQUESTED", "settled": True, "request": deepcopy(request),
              "receipt": deepcopy(receipt)}
    _set(player, "p5_station_last_loan_request_result", result)
    return deepcopy(result)


def work_receipt_id(scene_id, action_id, suffix):
    return f"station-work:{scene_id}:{action_id}:{suffix}"


def next_action_id(actor, commitment_id, now_minute):
    """Mint a replayable unique physical attempt id without changing the goal id."""
    if type(now_minute) is not int or not isinstance(commitment_id, str) or not commitment_id:
        raise ValueError("station work attempt requires an exact commitment and P4 minute")
    counter = int(_get(actor, "p5_station_work_attempt_counter", 0)) + 1
    _set(actor, "p5_station_work_attempt_counter", counter)
    scene_id = str(_get(actor, "p3_scene_id", category="native_p3") or "unbound")
    return f"station-attempt:{scene_id}:{int(actor.id)}:{now_minute}:{counter}:{commitment_id}"


def _reject_start(actor, task, reason, scene_id):
    """Record an actual native validation rejection with an explicit zero delta."""
    from tools.native_platform_v0.p3.p4_world import clock_for_actor
    minute = int(clock_for_actor(actor)["now"])
    action_id = str(task.get("action_id") or task.get("commitment_id") or "unbound")
    receipt_id = f"station-work-reject:{scene_id}:{actor.id}:{action_id}:{minute}:{reason}"
    receipt = {"receipt_id": receipt_id, "action_id": action_id,
               "commitment_id": task.get("commitment_id"), "task_kind": task.get("task_kind"),
               "actor_id": int(actor.id), "actor_alias": _get(actor, "p5_actor_alias"),
               "tool_id": task.get("tool_id"), "target_id": task.get("target_id"),
               "attempted_minute": minute, "outcome": "WORLD_VALIDATION_REJECTED",
               "settled": False, "reason": reason, "world_delta": None}
    _append_receipt(actor, receipt)
    append_event(actor, "P5_STATION_WORK_START_REJECTED", receipt_id,
                 {**receipt, "attempted_minute": minute}, receipt_id)
    return {"ok": False, "status": "WORLD_VALIDATION_REJECTED",
            "reason": reason, "receipt": deepcopy(receipt)}


@_atomic
def start_work(actor, task, *, now_minute, scene_id):
    """Atomically acquire the existing tool for a clocked task; no work effect yet."""
    if not isinstance(task, Mapping) or task.get("task_kind") not in TASK_DURATIONS:
        return _reject_start(actor, task if isinstance(task, Mapping) else {},
                             "unsupported_station_work_task", scene_id)
    kind = task["task_kind"]
    if (type(now_minute) is not int or type(task.get("duration_minutes")) is not int
            or task["duration_minutes"] != TASK_DURATIONS[kind]):
        return _reject_start(actor, task, "work_duration_does_not_match_registered_content", scene_id)
    from tools.native_platform_v0.p3.p4_world import clock_for_actor
    if now_minute != int(clock_for_actor(actor)["now"]):
        return _reject_start(actor, task, "work_start_must_use_current_p4_minute", scene_id)
    pending = _get(actor, "pending_action", category="native_p3")
    pending_task = pending.get("ongoing_task", {}) if isinstance(pending, Mapping) else {}
    if (not isinstance(pending, Mapping) or pending.get("intent", {}).get("operator") != "use_tool"
            or str(pending_task.get("commitment_id")) != str(task.get("commitment_id"))
            or str(pending_task.get("task_kind")) != kind):
        return _reject_start(actor, task, "matching_planned_native_action_is_required", scene_id)
    commitments = _get(actor, "ongoing_commitments", [], category="native_p5")
    commitment = next((row for row in commitments
                       if str(row.get("commitment_id")) == str(task.get("commitment_id"))), None)
    if (not isinstance(commitment, Mapping)
            or commitment.get("status") not in {"ACCEPTED", "IN_PROGRESS"}
            or commitment.get("task_kind") != kind
            or commitment.get("tool_id") != task.get("tool_id")
            or commitment.get("target_id") != task.get("target_id")
            or commitment.get("grant_id") != task.get("grant_id")
            or commitment.get("source") != task.get("source")):
        return _reject_start(actor, task, "persisted_actor_commitment_does_not_authorize_work", scene_id)
    if task.get("tool_id") is None or int(task["tool_id"]) <= 0:
        return _reject_start(actor, task, "exact_registered_tool_id_required", scene_id)
    from tools.native_platform_v0.p5 import service
    pickup, rows = service._scene_objects(scene_id)
    content = _get(pickup, "p5_station_content_v1")
    if not isinstance(content, Mapping) or int(content.get("tool_id", -1)) != int(task["tool_id"]):
        return _reject_start(actor, task, "tool_is_not_registered_for_this_station", scene_id)
    tool = next((obj for obj in rows if int(obj.id) == int(task["tool_id"])), None)
    if tool is None or _get(tool, "p5_station_tool") is not True:
        return _reject_start(actor, task, "registered_tool_not_found", scene_id)
    if _get(actor, "p5_station_work") is not None:
        return _reject_start(actor, task, "actor_already_has_station_work", scene_id)
    if actor.location is None or tool.location != actor.location or tool in actor.contents:
        return _reject_start(actor, task, "tool_must_be_locally_present_at_its_workbench", scene_id)
    if type(task.get("target_room_id")) is int and task["target_room_id"] != int(actor.location.id):
        return _reject_start(actor, task, "task_workbench_does_not_match_actor_local_room", scene_id)
    lease = deepcopy(_get(tool, "p5_station_tool_lease", {}))
    if lease.get("status") != "FREE" or lease.get("lease_id") is not None:
        return _reject_start(actor, task, "shared_tool_capacity_one_is_occupied", scene_id)
    actor_alias = str(_get(actor, "p5_actor_alias"))
    target_id = task.get("target_id")
    if kind == "inspect_supply":
        if (target_id != content["supply_id"] or actor.location.id != pickup.id
                or int(task.get("item_id", -1)) != content["supply_id"]):
            return _reject_start(actor, task, "inspection_target_is_not_the_registered_local_supply", scene_id)
        target = next((obj for obj in rows if int(obj.id) == int(target_id)), None)
        if target is None or target.location != actor.location or _get(target, "p5_supply_inspection_status") == "APPROVED":
            return _reject_start(actor, task, "supply_is_not_inspectable_in_actor_local_room", scene_id)
    else:
        if target_id != content["repair_exit_id"] or actor.location.id != pickup.id:
            return _reject_start(actor, task, "repair_target_is_not_the_registered_local_exit", scene_id)
        target = next((obj for obj in rows if int(obj.id) == int(target_id)), None)
        if target is None or target.access(actor, "traverse", default=True):
            return _reject_start(actor, task, "registered_passage_is_missing_or_already_traversable", scene_id)

    action_id = str(task.get("action_id") or task.get("commitment_id") or "")
    if not action_id:
        return _reject_start(actor, task, "native_action_identity_required", scene_id)
    due_minute = now_minute + TASK_DURATIONS[kind]
    if type(task.get("deadline_minute")) is int and due_minute > task["deadline_minute"]:
        return _reject_start(actor, task, "task_deadline_precedes_native_work_completion", scene_id)
    if due_minute > int(clock_for_actor(actor)["deadline"]):
        return _reject_start(actor, task, "scenario_deadline_precedes_native_work_completion", scene_id)
    lease_id = f"{scene_id}:{action_id}:{int(tool.id)}"
    work = {"status": "IN_PROGRESS", "action_id": action_id,
            "commitment_id": str(task.get("commitment_id") or action_id),
            "task_kind": kind, "actor_alias": actor_alias, "actor_id": int(actor.id),
            "tool_id": int(tool.id), "target_id": int(target.id),
            "item_id": int(task["item_id"]) if task.get("item_id") is not None else None,
            "storage_destination_id": task.get("storage_destination_id"),
            "work_room_id": int(actor.location.id), "lease_id": lease_id,
            "started_minute": now_minute, "due_minute": due_minute,
            "duration_minutes": TASK_DURATIONS[kind], "deadline_minute": task.get("deadline_minute")}
    lease.update({"status": "BUSY", "lease_id": lease_id, "actor_id": int(actor.id),
                  "commitment_id": work["commitment_id"], "task_kind": kind,
                  "started_minute": now_minute, "due_minute": due_minute})
    _set(tool, "p5_station_tool_lease", lease)
    _set(actor, "p5_station_work", work)
    start_id = work_receipt_id(scene_id, action_id, "start")
    append_event(actor, "P5_STATION_WORK_STARTED", start_id,
                 {"actor_alias": actor_alias, "actor_id": int(actor.id), "tool_id": int(tool.id),
                  "target_id": int(target.id), "item_id": work["item_id"], "task_kind": kind,
                  "commitment_id": work["commitment_id"], "action_id": action_id,
                  "lease_id": lease_id, "started_minute": now_minute, "due_minute": due_minute,
                  "duration_minutes": TASK_DURATIONS[kind]}, start_id)
    return {"ok": True, "status": "IN_PROGRESS", "work": deepcopy(work), "start_receipt_id": start_id}


def _finish_effect(actor, work, tool, rows):
    target = next((obj for obj in rows if int(obj.id) == int(work["target_id"])), None)
    if target is None:
        return None, "registered_work_target_disappeared"
    if work["task_kind"] == "inspect_supply":
        if (int(target.id) != work["item_id"] or target.location != actor.location
                or _get(target, "p5_supply_inspection_status") == "APPROVED"):
            return None, "inspection_target_changed_before_completion"
        before = _get(target, "p5_supply_inspection_status", "UNINSPECTED")
        _set(target, "p5_supply_inspection_status", "APPROVED")
        if _get(target, "p5_supply_inspection_status") != "APPROVED":
            return None, "inspection_world_effect_failed_readback"
        return {"item_id": int(target.id), "before_status": before,
                "after_status": "APPROVED"}, None
    if work["task_kind"] == "repair_passage":
        if (target.location != actor.location or target.key != "south"
                or int(target.location.id) != work["work_room_id"]):
            return None, "repair_exit_changed_before_completion"
        before = bool(target.access(actor, "traverse", default=True))
        if before:
            return None, "repair_exit_is_no_longer_in_repair_state"
        target.locks.add("traverse:true()")
        after = bool(target.access(actor, "traverse", default=True))
        if not after:
            return None, "repair_exit_world_effect_failed_readback"
        return {"exit_id": int(target.id), "before_traversable": before,
                "after_traversable": after}, None
    return None, "unsupported_station_work_task"


def _release_matching_lease(tool, work):
    lease = deepcopy(_get(tool, "p5_station_tool_lease", {}))
    if lease.get("lease_id") != work.get("lease_id") or lease.get("commitment_id") != work.get("commitment_id"):
        return False
    _set(tool, "p5_station_tool_lease", {"status": "FREE", "lease_id": None,
                                         "actor_id": None, "commitment_id": None,
                                         "task_kind": None, "started_minute": None,
                                         "due_minute": None})
    return True


@_atomic
def store_supply(actor, *, item_id):
    """Move one inspected registered supply into the real station container."""
    from tools.native_platform_v0.p5 import service
    from tools.native_platform_v0.p3.p4_world import append_event as append_p4_event, clock_for_actor

    scene_id = str(_get(actor, "p3_scene_id", category="native_p3"))
    pickup, rows = service._scene_objects(scene_id)
    content = _get(pickup, "p5_station_content_v1")
    if not isinstance(content, Mapping) or type(item_id) is not int or item_id != content.get("supply_id"):
        return {"settled": False, "reason": "item_is_not_the_registered_station_supply"}
    storage = next((obj for obj in rows if int(obj.id) == int(content["storage_id"])), None)
    item = next((obj for obj in rows if int(obj.id) == item_id), None)
    if storage is None or _get(storage, "p5_station_storage") is not True or item is None:
        return {"settled": False, "reason": "registered_station_storage_or_supply_missing"}
    if actor.location is None or storage.location != actor.location:
        return {"settled": False, "reason": "actor_must_be_co_located_with_registered_storage"}
    if item not in actor.contents:
        return {"settled": False, "reason": "registered_supply_must_be_held_by_actor"}
    if _get(item, "p5_supply_inspection_status") != "APPROVED":
        return {"settled": False, "reason": "supply_has_no_completed_native_inspection"}
    ledger = list(_get(pickup, "p4_ledger", [], category="native_p3"))
    native_receipts = list(_get(actor, "station_work_receipts", [], category="native_p5"))
    inspection_receipts = []
    for candidate in rows:
        if _get(candidate, "p5_actor_alias") not in {"A", "B"}:
            continue
        inspection_receipts.extend(
            row for row in _get(candidate, "station_work_receipts", [], category="native_p5")
            if row.get("task_kind") == "inspect_supply" and row.get("item_id") == item_id
            and row.get("settled") is True and row.get("outcome") == "SETTLED"
            and row.get("effect", {}).get("after_status") == "APPROVED")
    inspected = any(
        row.get("event_type") == "P5_STATION_SUPPLY_INSPECTED"
        and row.get("sealed") is True
        and row.get("receipt_id") == receipt.get("receipt_id")
        and row.get("event_id") == receipt.get("receipt_id")
        and row.get("typed_args", {}).get("receipt_id") == receipt.get("receipt_id")
        and row.get("typed_args", {}).get("actor_id") == int(actor.id)
        and row.get("typed_args", {}).get("item_id") == item_id
        and row.get("typed_args", {}).get("tool_id") == content.get("tool_id")
        and row.get("typed_args", {}).get("outcome") == "SETTLED"
        for receipt in inspection_receipts for row in ledger)
    if not inspected:
        return {"settled": False, "reason": "inspection_status_lacks_native_receipt_witness"}
    before_location = int(item.location.id) if item.location else None
    before_inventory = [int(obj.id) for obj in actor.contents]
    # The move is exposed only through this registered native command and is
    # accepted only after exact inventory/container readback.
    moved = item.move_to(storage, quiet=True)
    after_location = int(item.location.id) if item.location else None
    after_inventory = [int(obj.id) for obj in actor.contents]
    settled = bool(moved and item.location == storage and int(item.id) not in after_inventory)
    minute = int(clock_for_actor(actor)["now"])
    receipt_id = f"station-store:{scene_id}:{actor.id}:{item_id}:{minute}:{len(native_receipts)}"
    pending = _get(actor, "pending_action", category="native_p3")
    ongoing_task = pending.get("ongoing_task", {}) if isinstance(pending, Mapping) else {}
    receipt = {"receipt_id": receipt_id, "operator": "store_item", "kind": "store_item",
               "actor_id": int(actor.id), "actor_alias": _get(actor, "p5_actor_alias"),
               "item_id": item_id, "storage_id": int(storage.id),
               "tool_id": int(content["tool_id"]),
               "before_location_id": before_location, "after_container_id": after_location,
               "before_inventory_ids": before_inventory, "after_inventory_ids": after_inventory,
               "commitment_id": ongoing_task.get("commitment_id"),
               "ongoing_commitment_id": ongoing_task.get("commitment_id"),
               "ongoing_task_kind": "store_item", "sim_minute": minute,
               "settled": settled, "outcome": "SETTLED" if settled else "WORLD_VALIDATION_REJECTED"}
    _append_receipt(actor, receipt)
    if settled:
        append_p4_event(scene_id, {"event_type": "P5_STATION_SUPPLY_STORED", "event_id": receipt_id,
                                   "typed_args": {**receipt, "provenance": "native_evennia_container_readback"},
                                   "receipt_id": receipt_id, "sealed": True})
    return receipt


@_atomic
def advance_work(actor, *, now_minute):
    """Advance/finish one actor's work using the existing authoritative minute."""
    work = deepcopy(_get(actor, "p5_station_work"))
    if not isinstance(work, Mapping) or work.get("status") != "IN_PROGRESS":
        return None
    from tools.native_platform_v0.p5 import service
    from tools.native_platform_v0.p3.p4_world import clock_for_actor

    authoritative_now = int(clock_for_actor(actor)["now"])
    if type(now_minute) is not int or now_minute != authoritative_now:
        raise ValueError("station work must use the current existing P4 simulated minute")
    pickup, rows = service._scene_objects(str(_get(actor, "p3_scene_id", category="native_p3")))
    tool = next((obj for obj in rows if int(obj.id) == int(work.get("tool_id", -1))), None)
    reason = None
    if tool is None:
        reason = "registered_tool_disappeared"
    elif (tool.location != actor.location or tool.location is None
          or int(tool.location.id) != work.get("work_room_id")):
        reason = "tool_moved_or_actor_left_workbench"
    else:
        lease = _get(tool, "p5_station_tool_lease", {})
        if (lease.get("lease_id") != work.get("lease_id")
                or lease.get("actor_id") != int(actor.id)
                or lease.get("commitment_id") != work.get("commitment_id")):
            reason = "shared_tool_lease_no_longer_belongs_to_work"
    if reason is None and now_minute < int(work["due_minute"]):
        return {"status": "IN_PROGRESS", "now_minute": now_minute,
                "due_minute": int(work["due_minute"]), "work": work}
    if reason is None and type(work.get("deadline_minute")) is int and now_minute > work["deadline_minute"]:
        reason = "task_deadline_passed_before_work_completion"

    effect = None
    if reason is None:
        effect, reason = _finish_effect(actor, work, tool, rows)
    outcome = "SETTLED" if reason is None else "ABORTED"
    released = _release_matching_lease(tool, work) if tool is not None else False
    if outcome == "SETTLED" and not released:
        raise RuntimeError("station work lost its matching lease during atomic settlement")
    _set(actor, "p5_station_work", None)
    receipt_id = work_receipt_id(str(_get(actor, "p3_scene_id", category="native_p3")),
                                 str(work["action_id"]), "finish" if outcome == "SETTLED" else "abort")
    receipt = {"receipt_id": receipt_id, "action_id": work["action_id"],
               "commitment_id": work["commitment_id"], "task_kind": work["task_kind"],
               "ongoing_commitment_id": work["commitment_id"],
               "ongoing_task_kind": work["task_kind"],
               "actor_id": int(actor.id), "actor_alias": work["actor_alias"],
               "tool_id": work["tool_id"], "target_id": work["target_id"],
               "item_id": work["item_id"], "started_minute": work["started_minute"],
               "work_room_id": work["work_room_id"],
               "due_minute": work["due_minute"], "completed_minute": now_minute,
               "duration_minutes": work["duration_minutes"], "outcome": outcome,
               "settled": outcome == "SETTLED", "released_lease": released,
               "abort_reason": reason,
               "effect": effect}
    if (outcome == "SETTLED" and work["task_kind"] == "repair_passage"
            and isinstance(effect, Mapping) and effect.get("after_traversable") is True
            and tool is not None):
        target = next((obj for obj in rows if int(obj.id) == int(work["target_id"])), None)
        if target is not None:
            _set(target, "p5_last_repair_receipt", {
                "receipt_id": receipt_id, "action_id": work["action_id"],
                "commitment_id": work["commitment_id"], "tool_id": work["tool_id"],
                "actor_alias": work["actor_alias"], "completed_minute": now_minute,
                "outcome": outcome,
            })
    _append_receipt(actor, receipt)
    event_type = EVENT_TYPES[work["task_kind"]] if outcome == "SETTLED" else "P5_STATION_WORK_ABORTED"
    args = {"actor_alias": work["actor_alias"], "actor_id": int(actor.id),
            "tool_id": work["tool_id"], "target_id": work["target_id"],
            "item_id": work["item_id"], "task_kind": work["task_kind"],
            "commitment_id": work["commitment_id"], "action_id": work["action_id"],
            "lease_id": work["lease_id"], "receipt_id": receipt_id,
            "started_minute": work["started_minute"], "due_minute": work["due_minute"],
            "completed_minute": now_minute, "outcome": outcome,
            "abort_reason": reason, "effect": effect}
    append_event(actor, event_type, receipt_id, args, receipt_id)
    return {"status": outcome, "receipt": receipt, "released_lease": released}
