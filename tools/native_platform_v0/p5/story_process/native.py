"""Evennia-world adapter for opt-in, sealed-prefix story-process planning.

The controller records task proposals only. World effects remain owned by
native actor callbacks and the P3 typed ledger.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy

from .model import bind_note_id, bind_scene, load_request, story_event_registry, validate_future_edit


def _attr(obj, key, default=None, category="native_p3"):
    return obj.attributes.get(key, category=category, default=default)


def _set(obj, key, value, category="native_p5"):
    obj.attributes.add(key, value, category=category)


def _load_story_meta(service, pickup):
    """Normalize Evennia saver containers before mutating detached metadata."""
    stored = service._plain_json(_attr(pickup, "p5_story_meta", category="native_p5", default={}))
    return deepcopy(dict(stored)) if isinstance(stored, Mapping) else {}


def initialize_story_process(pickup, raw_request, scene_id, strategy="gtpyhop"):
    """Validate and store an opt-in request; legacy reset never calls this."""
    request = load_request(raw_request, allow_template=True)
    request = bind_scene(request, scene_id)
    if strategy not in {"gtpyhop", "event_driven"}:
        raise ValueError("story_strategy must be gtpyhop or event_driven")
    _set(pickup, "p5_story_request", deepcopy(dict(request.raw)))
    _set(pickup, "p5_story_strategy", strategy)
    _set(pickup, "p5_story_meta", {"controller_decisions": [], "pending_task_requests": [],
                                   "receipts": [], "real_verdicts": [],
                                   "next_request_id": 1, "controller_authored_npc_commands": 0,
                                   "controller_authored_npc_task_requests": 0})
    return request


def _response(ledger, rows, scene_id, note_id, through_minute):
    from tools.native_platform_v0.p5.world import _verified_social_responses
    verified = {row.get("event_id") for row in _verified_social_responses(ledger, rows, scene_id)}
    for row in sorted(ledger, key=lambda item: (int(item.get("minute", -1)),
                                                int(item.get("sequence", -1)))):
        args = row.get("typed_args", {})
        if (row.get("event_id") in verified and row.get("event_type") == "SOCIAL_RESPONSE" and row.get("sealed") is True
                and int(row.get("minute", -1)) <= through_minute
                and args.get("decision") in {"accepted", "rejected"}
                and args.get("note_id") == note_id
                and args.get("native_commit_status") == "settled"
                and args.get("physical_receipt", {}).get("status") == "settled"):
            return {"outcome": args["decision"], "event_id": row["event_id"],
                    "minute": int(row["minute"]), "note_id": note_id}
    return None


def _actor_row(actor, note_id, response, minute):
    alias = _attr(actor, "p5_actor_alias", category="native_p5")
    task = _attr(actor, "p5_story_task", category="native_p5")
    item_ids = [int(obj.id) for obj in actor.contents]
    item_ids.extend(int(obj.id) for obj in (actor.location.contents if actor.location else [])
                    if obj.access(actor, "view", default=True))
    policy = _attr(actor, "p5_story_postresponse_policy", {}, category="native_p5")
    disposition_key = {"A": "A_archive", "B": "B_archive"}.get(alias)
    disposition = (policy.get(response["outcome"], {}).get(disposition_key)
                   if response and disposition_key else None)
    willingness = (disposition != "UNWILLING" and
                   not (isinstance(task, Mapping) and task.get("status") == "REJECTED"))
    if disposition == "LOCAL_CHOICE":
        deadline = int(_attr(actor, "p5_story_deadline", 24, category="native_p5"))
        willingness = (deadline - minute >= 2 and
                       _attr(actor, "status", "RUNNING") != "PAUSED")
    active_task = (None if not isinstance(task, Mapping) else
                   {key: deepcopy(task.get(key)) for key in
                    ("request_id", "task_kind", "item_id", "destination_id", "status")})
    return {"present": actor.location is not None, "can_receive_note": True,
            "willing_to_archive": bool(willingness),
            "locally_observed_item_ids": item_ids,
            "active_task": active_task,
            "task_status": (task.get("status") if isinstance(task, Mapping) else "IDLE")}


def build_sealed_state(scene_id, minute):
    """Build the planner's strictly scoped view from the sealed ledger frontier."""
    from tools.native_platform_v0.p5 import service

    pickup, rows = service._scene_objects(scene_id)
    raw = _attr(pickup, "p5_story_request", category="native_p5")
    if not isinstance(raw, Mapping):
        return None
    request = load_request(service._plain_json(raw))
    if request.scenario_id != scene_id:
        raise ValueError("stored story-process request has the wrong scene")
    ledger = [row for row in _attr(pickup, "p4_ledger", default=[])
              if row.get("sealed") is True and int(row.get("minute", -1)) <= minute]
    note = next((obj for obj in rows if _attr(obj, "p4_note_request_id") is not None
                 and (request.objective.get("note_id") is None
                      or int(obj.id) == request.objective["note_id"])), None)
    if note is None:
        return None
    note_id = int(note.id)
    if request.objective.get("note_id") is None:
        created_event = next((row for row in ledger if row.get("event_type") == "SOCIAL_REQUEST"
                              and row.get("sealed") is True
                              and row.get("typed_args", {}).get("note_id") == note_id
                              and row.get("typed_args", {}).get("physical_receipt", {}).get("status") == "settled"
                              and row.get("typed_args", {}).get("physical_receipt", {}).get("recipient_inventory_actor_id") ==
                              row.get("typed_args", {}).get("recipient_actor_id")), None)
        if created_event is None:
            return None
        request = bind_note_id(request, note_id)
        _set(pickup, "p5_story_request", deepcopy(dict(request.raw)))
    response = _response(ledger, rows, scene_id, note_id, minute)
    actors = {str(_attr(obj, "p5_actor_alias", category="native_p5")): obj
              for obj in rows if _attr(obj, "p5_actor_alias", category="native_p5") in {"A", "B"}}
    actor_rows = {alias: _actor_row(actor, note_id, response, minute) for alias, actor in actors.items()}
    holder = next((alias for alias, actor in actors.items()
                   if any(int(item.id) == note_id for item in actor.contents)), None)
    rooms = {int(obj.id): obj for obj in rows if obj.__class__.__name__ == "Room"}
    archive = next((obj for obj in rooms.values()
                    if _attr(obj, "p5_story_archive", category="native_p5") is True), None)
    if archive is None:
        # The destination is an existing generated room. Registration is
        # explicit in scene attrs, never inferred from a room name.
        archive = next((obj for obj in rooms.values()
                        if int(obj.id) == int(_attr(pickup, "p5_side_room_id", category="native_p5"))), None)
    if archive is None:
        raise ValueError("P5 story archive room is not registered")
    from tools.native_platform_v0.p5 import world
    from tools.native_platform_v0.p5.bundle import DEFAULT_ENTITIES
    typed_trace = world.serialize_typed_trace(world.build_typed_trace(
        scene_id, service._bundle_for(pickup), DEFAULT_ENTITIES, through_minute=minute))
    events = []
    for row in ledger:
        args = row.get("typed_args", {})
        if row.get("event_type") == "SOCIAL_RESPONSE" and args.get("note_id") == note_id:
            outcome = args.get("decision")
            if outcome in {"accepted", "rejected"} and args.get("native_commit_status") == "settled":
                events.append({"event_id": row["event_id"], "event_type": "p5_note_response",
                               "version": "1", "provenance": "committed_ledger",
                               "time": int(row["minute"]), "sequence": int(row["sequence"]),
                               "args": {"actor": {"entity_type": "Actor", "stable_id": "A", "label": "A"},
                                        "recipient": {"entity_type": "Actor", "stable_id": "B", "label": "B"},
                                        "item": {"entity_type": "Item", "stable_id": str(note_id), "label": "Love note"},
                                        "response": outcome}})
    actor_by_id = {int(actor.id): alias for alias, actor in actors.items()}
    receipt_index = {str(receipt.get("receipt_id")): receipt for actor in actors.values()
                     for receipt in _attr(actor, "p5_story_receipts", category="native_p5", default=[])
                     if isinstance(receipt, Mapping)}
    for row in ledger:
        args = row.get("typed_args", {})
        receipt = receipt_index.get(str(row.get("receipt_id")))
        if (not isinstance(receipt, Mapping) or receipt.get("settled") is not True
                or str(receipt.get("item_id")) != str(note_id)):
            continue
        if row.get("event_type") == "P5_STORY_NOTE_HANDED_OVER":
            if (receipt.get("kind") != "give" or args.get("item_id") != note_id
                    or args.get("after_holder_id") != receipt.get("recipient_id")):
                continue
            actor_alias = receipt.get("actor_alias")
            recipient_alias = actor_by_id.get(int(receipt.get("recipient_id", -1)))
            if actor_alias not in {"A", "B"} or recipient_alias not in {"A", "B"}:
                continue
            events.append({"event_id": row["event_id"], "event_type": "p5_note_handed_over",
                           "version": "1", "provenance": "committed_ledger",
                           "time": int(row["minute"]), "sequence": int(row["sequence"]),
                           "args": {"actor": {"entity_type": "Actor", "stable_id": actor_alias, "label": actor_alias},
                                    "recipient": {"entity_type": "Actor", "stable_id": recipient_alias, "label": recipient_alias},
                                    "item": {"entity_type": "Item", "stable_id": str(note_id), "label": "Love note"}}})
        elif row.get("event_type") == "P5_STORY_NOTE_ARCHIVED":
            if (receipt.get("kind") != "drop" or args.get("item_id") != note_id
                    or args.get("after_location_id") != receipt.get("after_item_room_id")):
                continue
            actor_alias = receipt.get("actor_alias")
            if actor_alias not in {"A", "B"}:
                continue
            events.append({"event_id": row["event_id"], "event_type": "p5_note_archived",
                           "version": "1", "provenance": "committed_ledger",
                           "time": int(row["minute"]), "sequence": int(row["sequence"]),
                           "args": {"actor": {"entity_type": "Actor", "stable_id": actor_alias, "label": actor_alias},
                                    "item": {"entity_type": "Item", "stable_id": str(note_id), "label": "Love note"}}})
    registry = story_event_registry()
    return {"scenario_id": scene_id, "sealed_minute": minute,
            "horizon": int(_attr(pickup, "p5_horizon", category="native_p5")),
            "request_id": request.request_id, "request_version": request.version,
            "response": response,
            "note": {"item_id": note_id,
                     "location_id": int(note.location.id) if note.location else None,
                     "holder_alias": holder},
            "actors": actor_rows,
            "destinations": _registered_destinations(scene_id, actors, archive),
            "task_grant": deepcopy(dict(request.task_control_grant)),
            "current_obligations": [deepcopy(task) for task in
                                    (_attr(actor, "p5_story_task", category="native_p5") for actor in actors.values())
                                    if isinstance(task, Mapping)],
            "typed_trace": {"events": events, "native_trace": typed_trace},
            "event_registry": registry}


def apply_story_decision(scene_id, sealed_state, decision):
    """Store valid proposals as future actor requests; never mutate game state."""
    from tools.native_platform_v0.p5 import service

    pickup, rows = service._scene_objects(scene_id)
    request = load_request(service._plain_json(
        _attr(pickup, "p5_story_request", category="native_p5")))
    if (not isinstance(decision, Mapping) or decision.get("schema") != "story-process-decision-v1"
            or decision.get("sealed_minute") != sealed_state.get("sealed_minute")
            or decision.get("target_version") != request.version):
        raise ValueError("story-process decision is stale or malformed")
    requests = decision.get("task_requests", [])
    if not isinstance(requests, list):
        raise ValueError("story-process task_requests must be a list")
    if request.control["mode"] == "locked_fragment" and decision.get("status") != "LOCKED_ABORTED":
        fragment = request.locked_fragment
        destinations = sealed_state["destinations"]
        expected = [(row["actor_alias"], row["task_kind"], request.objective["note_id"],
                     destinations[row["destination_ref"]]["id"], "LOCKED_FRAGMENT")
                    for row in fragment["sequence"]]
        actual = [(row.get("actor_alias"), row.get("task_kind"), row.get("item_id"),
                   row.get("destination_id"), row.get("control_source"))
                  for row in requests if isinstance(row, Mapping)]
        if actual != expected:
            raise ValueError("locked-fragment task proposals differ from the immutable authored sequence")
    aliases = {str(_attr(obj, "p5_actor_alias", category="native_p5")): obj
               for obj in rows if _attr(obj, "p5_actor_alias", category="native_p5") in {"A", "B"}}
    meta = _load_story_meta(service, pickup)
    queued = []
    for row in requests:
        expected_source = ("AUTHORED" if request.control["mode"] == "direct" else
                           "LOCKED_FRAGMENT" if request.control["mode"] == "locked_fragment" else "PLANNER")
        if (not isinstance(row, Mapping) or row.get("actor_alias") not in aliases
                or row.get("task_kind") not in {"handover_note", "archive_note"}
                or row.get("grant_id") != request.task_control_grant["grant_id"]
                or row.get("control_source") != expected_source
                or request.control["mode"] == "zero"
                or row.get("item_id") != sealed_state.get("note", {}).get("item_id")):
            raise ValueError("story-process task request exceeds exact native episode grant")
        source_method = row.get("source_method_id")
        if request.control["mode"] != "locked_fragment" and source_method not in request.control["allowed_methods"]:
            raise ValueError("story-process proposal names a method outside the authored method scope")
        if request.control["mode"] == "locked_fragment" and source_method != "locked_fragment":
            raise ValueError("locked-fragment proposals cannot replace the immutable core")
        target = next((value["id"] for value in sealed_state["destinations"].values()
                       if value["id"] == row.get("destination_id")), None)
        if target is None or row.get("actor_alias") not in request.task_control_grant["actor_aliases"]:
            raise ValueError("story-process task request names an unregistered destination or actor")
        rendezvous_id = row.get("rendezvous_destination_id")
        is_a_return_archive = (source_method == "return_then_file_by_A"
                               and row.get("actor_alias") == "A"
                               and row.get("task_kind") == "archive_note")
        if is_a_return_archive:
            if (rendezvous_id != sealed_state["destinations"]["handover"]["id"]
                    or row.get("destination_id") != sealed_state["destinations"]["archive"]["id"]):
                raise ValueError("A return/archive offer must rendezvous only at the registered handover destination")
        elif rendezvous_id is not None:
            raise ValueError("rendezvous_destination_id is only valid on A's return_then_file_by_A archive task")
        actor = aliases[row["actor_alias"]]
        current = _attr(actor, "p5_story_task", category="native_p5")
        if isinstance(current, Mapping) and current.get("status") not in {"SETTLED", "REJECTED", "BLOCKED"}:
            continue
        current_offer = _attr(actor, "p5_story_offer", category="native_p5")
        if isinstance(current_offer, Mapping) and current_offer.get("request_id") == row.get("request_id"):
            continue
        offer = deepcopy(dict(row))
        offer["proposal_status"] = "OFFERED_TO_ACTOR"
        offer["deadline_minute"] = int(request.objective["by_minute"])
        offer["response_outcome"] = sealed_state["response"]["outcome"]
        offer["response_event_id"] = sealed_state["response"]["event_id"]
        if offer["task_kind"] == "handover_note":
            offer["recipient_id"] = int(aliases["A"].id)
        _set(actor, "p5_story_offer", offer)
        queued.append(offer)
    meta["task_offers"] = queued
    meta["controller_authored_npc_task_requests"] = int(
        meta.get("controller_authored_npc_task_requests", 0)) + sum(
            1 for offer in queued if offer.get("control_source") == "AUTHORED")
    meta.setdefault("controller_decisions", []).append(deepcopy(dict(decision)))
    if decision.get("status") == "LOCKED_ABORTED":
        fragment = request.locked_fragment or {}
        meta.setdefault("controller_events", []).append({
            "event_id": f"{request.request_id}:v{request.version}:locked-abort:{sealed_state['sealed_minute']}",
            "event_type": "P5_STORY_LOCKED_FRAGMENT_ABORTED",
            "sealed": True,
            "sealed_frontier_minute": sealed_state["sealed_minute"],
            "provenance": "native_controller_metadata_not_world_ledger",
            "reason": deepcopy(decision.get("outstanding_obligations", [])),
            "immutable_sequence_sha256": fragment.get("sequence_sha256"),
            "request_version": request.version,
            "effects_applied": False})
    _set(pickup, "p5_story_meta", meta)
    meta["controller_decisions"][-1]["queued_task_requests"] = deepcopy(queued)
    _set(pickup, "p5_story_meta", meta)
    return {"queued_task_requests": queued, "effects_claimed": False,
            "controller_events": (deepcopy(meta.get("controller_events", []))[-1:]
                                  if decision.get("status") == "LOCKED_ABORTED" else [])}


def edit_story_request(scene_id, proposed, expected_version):
    """CAS-edit only future method/actor policy; grant and objective are fixed."""
    from tools.native_platform_v0.p5 import service
    pickup, _ = service._scene_objects(scene_id)
    previous = load_request(service._plain_json(
        _attr(pickup, "p5_story_request", category="native_p5")))
    result = {"settled": False, "status": "PERMISSION_ESCALATION"}
    try:
        if expected_version != previous.version:
            return {"settled": False, "status": "VERSION_CONFLICT", "reason": "stale story-process request version"}
        canonical = deepcopy(dict(proposed)) if isinstance(proposed, Mapping) else proposed
        if isinstance(canonical, dict):
            for path, current in (("scenario_id", previous.scenario_id),
                                  ("task_control_grant.scenario_id", previous.scenario_id),
                                  ("objective.note_id", previous.objective["note_id"])):
                if "." in path:
                    parent, key = path.split(".")
                    if canonical.get(parent, {}).get(key) not in (None, current):
                        raise ValueError("edit cannot change the bound scene or exact note identity")
                    canonical.setdefault(parent, {})[key] = current
                else:
                    if canonical.get(path) not in (None, current):
                        raise ValueError("edit cannot change the bound scene or exact note identity")
                    canonical[path] = current
        updated = validate_future_edit(previous, canonical)
        ledger = _attr(pickup, "p4_ledger", default=[])
        if any(row.get("event_type") == "P5_STORY_NOTE_ARCHIVED"
               and row.get("sealed") is True
               and row.get("typed_args", {}).get("item_id") == previous.objective["note_id"]
               for row in ledger):
            raise ValueError("the requested note is already archived; settled objective is immutable")
        meta = _load_story_meta(service, pickup)
        stale_requests = []
        for actor in (obj for obj in service._scene_objects(scene_id)[1]
                      if _attr(obj, "p5_actor_alias", category="native_p5") in {"A", "B"}):
            offer = _attr(actor, "p5_story_offer", category="native_p5")
            if isinstance(offer, Mapping):
                stale_requests.append(offer.get("request_id"))
                _set(actor, "p5_story_offer", None)
        meta.setdefault("stale_future_request_ids", []).extend(stale_requests)
        _set(pickup, "p5_story_meta", meta)
        _set(pickup, "p5_story_request", deepcopy(dict(updated.raw)))
        result = {"settled": True, "status": "UPDATED", "version": updated.version}
    except (ValueError, TypeError) as exc:
        result["reason"] = str(exc)
        if "already archived" in str(exc):
            result["status"] = "SETTLED_IMMUTABLE"
    return result


def _registered_destinations(scene_id, actors, archive):
    """Return controller-visible W shortest-path lower bounds over native exits."""
    from tools.native_platform_v0.p5.service import _scene_objects
    _, rows = _scene_objects(scene_id)

    def distance(actor, target_id):
        if actor.location is None:
            return None
        queue = [(actor.location, 0)]
        visited = {int(actor.location.id)}
        while queue:
            room, steps = queue.pop(0)
            if int(room.id) == target_id:
                return steps
            for edge in room.exits:
                if not edge.destination or not edge.access(actor, "traverse", default=True):
                    continue
                nxt = edge.destination
                if int(nxt.id) not in visited:
                    visited.add(int(nxt.id))
                    queue.append((nxt, steps + 1))
        return None

    archive_id = int(archive.id)
    archive_routes = {alias: distance(actor, archive_id) for alias, actor in actors.items()}
    a = actors.get("A")
    handover_id = int(a.location.id) if a and a.location else -1
    handover_routes = {alias: distance(actor, handover_id) if handover_id > 0 else None
                       for alias, actor in actors.items()}
    archive_costs = {alias: (steps + 1 if steps is not None else None)
                     for alias, steps in archive_routes.items()}
    handover_costs = {alias: (steps + 1 if steps is not None else None)
                      for alias, steps in handover_routes.items()}
    return {"archive": {"id": archive_id,
                        "reachable_by": sorted(alias for alias, steps in archive_routes.items()
                                                if steps is not None),
                        "estimated_minutes": max((steps for steps in archive_routes.values()
                                                   if steps is not None), default=0) + 1,
                        "estimated_minutes_by_actor": archive_costs},
            "handover": {"id": handover_id,
                         "reachable_by": sorted(alias for alias, steps in handover_routes.items()
                                                 if steps is not None),
                         "estimated_minutes": (handover_routes.get("B") or 0) + 1,
                         "estimated_minutes_by_actor": handover_costs}}


__all__ = ["initialize_story_process", "build_sealed_state", "apply_story_decision", "edit_story_request"]
