"""Actor-owned acceptance and native execution of one story task at a time."""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy


def _get(actor, key, default=None):
    return actor.attributes.get(key, category="native_p5", default=default)


def _put(actor, key, value):
    actor.attributes.add(key, value, category="native_p5")


def _local_choice_accepts(actor, task, now, item):
    """Task-triggered local choice: defer the first archive offer once.

    This is an explicit episode policy, not a claim about romantic intent or a
    minute-triggered script. Subsequent offers use the actor's local deadline,
    pending-action, and exact-item observations.
    """
    history = list(_get(actor, "p5_story_local_choice_history", []))
    request_id = str(task["request_id"])
    if task.get("task_kind") == "archive_note" and not any(
            row.get("kind") == "first_archive_deferral" for row in history if isinstance(row, Mapping)):
        history.append({"kind": "first_archive_deferral", "request_id": request_id,
                        "minute": int(now), "reason": "episode_local_choice_defers_first_archive_offer"})
        _put(actor, "p5_story_local_choice_history", history)
        return False, "episode_local_choice_defers_first_archive_offer"
    has_time = int(task.get("deadline_minute", 24)) - now >= 2
    not_busy = actor.attributes.get("pending_action", category="native_p3") is None
    return (has_time and not_busy and item is not None,
            None if has_time and not_busy and item is not None else
            "local_choice_time_pending_action_or_exact_item_condition_failed")


def _local_item(actor, item_id):
    local = list(actor.contents) + (list(actor.location.contents) if actor.location else [])
    return next((obj for obj in local if int(obj.id) == item_id
                 and obj.access(actor, "view", default=True)), None)


def _known_edges(actor):
    known = deepcopy(_get(actor, "p5_story_known_exits", {}))
    if actor.location:
        known[str(int(actor.location.id))] = [
            {"key": str(edge.key), "destination_id": int(edge.destination.id),
             "traversable": bool(edge.access(actor, "traverse", default=True))}
            for edge in actor.location.exits if edge.destination]
        _put(actor, "p5_story_known_exits", known)
    return known


def _next_exit(actor, target_id):
    known = _known_edges(actor)
    if actor.location is None:
        return None
    start = int(actor.location.id)
    graph = {int(room): [int(row["destination_id"]) for row in edges
                         if row.get("traversable") is True]
             for room, edges in known.items()}
    queue, seen = [(start, [])], {start}
    path = None
    while queue:
        room, prefix = queue.pop(0)
        if room == target_id:
            path = prefix
            break
        for destination in graph.get(room, ()):
            if destination not in seen:
                seen.add(destination)
                queue.append((destination, prefix + [destination]))
    if not path:
        return None
    return next((edge for edge in actor.location.exits if edge.destination
                 and int(edge.destination.id) == path[0]
                 and edge.access(actor, "traverse", default=True)), None)


def _append(actor, event_type, event_id, args, receipt_id=None):
    from tools.native_platform_v0.p3.p4_world import append_event
    scene_id = actor.attributes.get("scene_id", category="native_p3")
    return append_event(scene_id, {"event_type": event_type, "event_id": event_id,
                                   "typed_args": args, "sealed": True,
                                   "receipt_id": receipt_id})


def _add_receipt(actor, task, operation, command, item, before_room, before_item_location,
                 before_inventory, settled, *, recipient=None, story_event=None,
                 action_destination_id=None):
    rows = list(actor.attributes.get("native_receipts", category="native_p3", default=[]))
    receipt_id = f"p5-story:{actor.id}:{task['request_id']}:{len(rows)}"
    after_room = int(actor.location.id) if actor.location else None
    after_inventory = sorted(int(obj.id) for obj in actor.contents)
    item_location = int(item.location.id) if item and item.location else None
    receipt = {"receipt_id": receipt_id, "kind": operation, "actor_dbref": str(actor.dbref),
               "actor_alias": actor.attributes.get("p5_actor_alias", category="native_p5"),
               "item_id": int(item.id) if item is not None else None, "before_room_id": before_room,
               "after_room_id": after_room, "before_inventory_ids": before_inventory,
               "after_inventory_ids": after_inventory, "before_item_room_id": before_item_location,
               "after_item_room_id": item_location,
               "recipient_id": int(recipient.id) if recipient else None,
               "destination_id": task.get("destination_id"),
               "action_destination_id": action_destination_id,
               "submitted_command": command,
               "settled": bool(settled), "provenance": "native_actor_command"}
    rows.append(receipt)
    actor.attributes.add("native_receipts", rows, category="native_p3")
    story_receipts = list(_get(actor, "p5_story_receipts", []))
    story_receipts.append(receipt)
    _put(actor, "p5_story_receipts", story_receipts)
    if story_event and settled:
        alias = actor.attributes.get("p5_actor_alias", category="native_p5")
        _append(actor, story_event, receipt_id,
                {"actor_alias": alias, "recipient_alias": (
                    recipient.attributes.get("p5_actor_alias", category="native_p5") if recipient else None),
                 "item_id": int(item.id), "receipt_id": receipt_id,
                 "before_holder_id": before_item_location if operation == "give" else None,
                 "after_holder_id": int(recipient.id) if operation == "give" else None,
                 "before_location_id": before_room, "after_location_id": item_location,
                 "destination_id": task.get("destination_id")}, receipt_id=receipt_id)
    return receipt


def step_story_task(actor):
    """Run one actor-owned task callback; return None when no task is eligible."""
    active = _get(actor, "p5_story_task")
    offer = _get(actor, "p5_story_offer")
    if (not isinstance(offer, Mapping) and
            (not isinstance(active, Mapping) or active.get("status") in {
                "SETTLED", "REJECTED", "BLOCKED", "STALE_CANCELLED"})):
        return None
    from twisted.internet import defer

    @defer.inlineCallbacks
    def execute():
        alias = actor.attributes.get("p5_actor_alias", category="native_p5")
        from tools.native_platform_v0.p3.p4_world import clock_for_actor
        now = int(clock_for_actor(actor)["now"])
        task = dict(active) if isinstance(active, Mapping) else None
        if isinstance(offer, Mapping):
            task = dict(offer)
            item = _local_item(actor, int(task["item_id"]))
            policy = _get(actor, "p5_story_postresponse_policy", {})
            outcome = task.get("response_outcome")
            disposition_key = ({"archive_note": f"{alias}_archive",
                                "handover_note": "B_return"}.get(task.get("task_kind")))
            disposition = policy.get(outcome, {}).get(disposition_key) if disposition_key else None
            if task.get("control_source") == "AUTHORED":
                # Direct mode is explicit author orchestration under the fixed
                # episode grant; it still cannot bypass exact-item or deadline guards.
                accepted = (now <= int(task.get("deadline_minute", 24)) and
                            (task["task_kind"] != "handover_note" or
                             (alias == "B" and item is not None)))
                reason = None if accepted else "direct_task_failed_exact_item_or_deadline_guard"
            elif task.get("control_source") == "LOCKED_FRAGMENT":
                accepted = (now <= int(task.get("deadline_minute", 24)) and
                            task.get("proposal_status") == "OFFERED_TO_ACTOR")
                reason = None if accepted else "locked_fragment_guard_or_deadline_failed"
            elif disposition == "WILLING":
                accepted = (task["task_kind"] != "handover_note" or (alias == "B" and item is not None))
                if task["task_kind"] == "archive_note" and alias == "B":
                    accepted = accepted and item is not None and item.attributes.get(
                        "p4_note_status", category="native_p3") == "accepted"
                reason = None if accepted else "exact_note_not_locally_available_or_response_policy_blocks_task"
            elif disposition == "UNWILLING":
                accepted, reason = False, "authored_local_game_content_declines_this_task"
            elif disposition == "LOCAL_CHOICE":
                accepted, reason = _local_choice_accepts(actor, task, now, item)
            else:
                accepted, reason = False, "story_offer_has_no_registered_local_disposition"
            task = {**dict(task), "status": "ACCEPTED" if accepted else "REJECTED",
                    "accepted_at_minute": now if accepted else None,
                    "rejection_reason": reason}
            _put(actor, "p5_story_task", task)
            _put(actor, "p5_story_offer", None)
            _append(actor, "P5_STORY_TASK_DECISION",
                    f"story-task:{task['request_id']}:decision",
                    {"actor_alias": alias, "request_id": task["request_id"],
                     "task_kind": task["task_kind"], "decision": task["status"],
                     "reason": reason, "item_id": task["item_id"]})
            if not accepted:
                defer.returnValue({"story_task": dict(task), "native_action": None})
        if task is None:
            defer.returnValue(None)
        if task.get("status") not in {"ACCEPTED", "IN_PROGRESS"}:
            defer.returnValue(None)
        item = _local_item(actor, int(task["item_id"]))
        if item is None or item not in actor.contents:
            rendezvous_id = task.get("rendezvous_destination_id")
            if (task.get("task_kind") == "archive_note" and alias == "A"
                    and type(rendezvous_id) is int and actor.location is not None):
                if int(actor.location.id) == rendezvous_id:
                    defer.returnValue({"story_task": dict(task),
                                       "native_action": "WAIT_FOR_GIVE_AT_RENDEZVOUS"})
                edge = _next_exit(actor, rendezvous_id)
                if edge is not None:
                    command = str(edge.key)
                    before_room = int(actor.location.id)
                    before_inventory = sorted(int(obj.id) for obj in actor.contents)
                    task = {**dict(task), "status": "IN_PROGRESS"}
                    _put(actor, "p5_story_task", task)
                    yield defer.maybeDeferred(actor.execute_cmd, command)
                    settled = bool(edge.destination and actor.location
                                   and int(actor.location.id) == int(edge.destination.id))
                    receipt = _add_receipt(
                        actor, task, "move", command, None, before_room, None,
                        before_inventory, settled, action_destination_id=rendezvous_id)
                    defer.returnValue({"story_task": dict(task), "native_action": "move",
                                       "receipt": receipt, "settled": settled})
                task = {**dict(task), "status": "BLOCKED",
                        "block_reason": "no_actor_known_traversable_path_to_registered_rendezvous"}
                _put(actor, "p5_story_task", task)
                _append(actor, "P5_STORY_TASK_FEEDBACK",
                        f"story-task:{task['request_id']}:blocked-rendezvous:{now}",
                        {"actor_alias": alias, "request_id": task["request_id"],
                         "task_kind": task["task_kind"], "status": "BLOCKED",
                         "reason": task["block_reason"], "item_id": task["item_id"]})
                defer.returnValue({"story_task": dict(task), "native_action": None})
            receipts = actor.attributes.get("native_receipts", category="native_p3", default=[])
            assigned_id = actor.attributes.get("task_item_id", category="native_p3")
            destination_id = actor.attributes.get("task_destination_id", category="native_p3")
            delivery_done = any(row.get("settled") is True and row.get("kind") == "drop"
                                and str(row.get("item_id")) == str(assigned_id)
                                and row.get("after_item_room_id") == destination_id for row in receipts)
            defer.returnValue({"story_task": dict(task), "native_action": "WAIT_FOR_EXACT_NOTE",
                               "claim_callback": bool(delivery_done)})
        edge, recipient = None, None
        if task["task_kind"] == "archive_note":
            destination_id = int(task["destination_id"])
            if actor.location is None:
                defer.returnValue({"story_task": dict(task), "native_action": "ACTOR_HAS_NO_LOCATION"})
            if int(actor.location.id) == destination_id:
                operation, command, event_type = "drop", f"drop {item.key}", "P5_STORY_NOTE_ARCHIVED"
            else:
                edge = _next_exit(actor, destination_id)
                if edge is None:
                    task = {**dict(task), "status": "BLOCKED",
                            "block_reason": "no_actor_known_traversable_path_to_archive"}
                    _put(actor, "p5_story_task", task)
                    _append(actor, "P5_STORY_TASK_FEEDBACK",
                            f"story-task:{task['request_id']}:blocked:{now}",
                            {"actor_alias": alias, "request_id": task["request_id"],
                             "task_kind": task["task_kind"], "status": "BLOCKED",
                             "reason": task["block_reason"], "item_id": task["item_id"]})
                    defer.returnValue({"story_task": dict(task), "native_action": None})
                operation, command, event_type = "move", str(edge.key), None
        elif task["task_kind"] == "handover_note":
            recipient_id = task.get("recipient_id")
            recipient = next((obj for obj in (actor.location.contents if actor.location else ())
                              if recipient_id is not None and int(obj.id) == int(recipient_id)
                              and obj.attributes.get("p5_actor_alias", category="native_p5")), None)
            if recipient is None:
                edge = _next_exit(actor, int(task["destination_id"]))
                if edge is not None:
                    operation, command, event_type = "move", str(edge.key), None
                else:
                    task = {**dict(task), "status": "IN_PROGRESS"}
                    receipts = actor.attributes.get("native_receipts", category="native_p3", default=[])
                    assigned_id = actor.attributes.get("task_item_id", category="native_p3")
                    old_dest = actor.attributes.get("task_destination_id", category="native_p3")
                    delivery_done = any(row.get("settled") is True and row.get("kind") == "drop"
                                        and str(row.get("item_id")) == str(assigned_id)
                                        and row.get("after_item_room_id") == old_dest for row in receipts)
                    defer.returnValue({"story_task": task, "native_action": "WAIT_FOR_RECIPIENT_LOCAL_CONTACT",
                                       "claim_callback": bool(delivery_done)})
            else:
                operation, command, event_type = "give", f"give {item.key} = {recipient.key}", "P5_STORY_NOTE_HANDED_OVER"
        else:
            defer.returnValue({"story_task": dict(task), "native_action": "UNSUPPORTED_TASK"})
        before_room = int(actor.location.id) if actor.location else None
        before_item_location = int(item.location.id) if item.location else None
        before_inventory = sorted(int(obj.id) for obj in actor.contents)
        task = {**dict(task), "status": "IN_PROGRESS"}
        _put(actor, "p5_story_task", task)
        yield defer.maybeDeferred(actor.execute_cmd, command)
        if operation == "move":
            settled = bool(edge.destination and actor.location
                           and int(actor.location.id) == int(edge.destination.id))
        elif operation == "drop":
            settled = (item not in actor.contents and item.location is not None
                       and int(item.location.id) == int(task["destination_id"]))
        else:
            settled = (item not in actor.contents and item in recipient.contents
                       and item.location is not None and int(item.location.id) == int(recipient.id))
        receipt = _add_receipt(actor, task, operation, command, item, before_room, before_item_location,
                               before_inventory, settled, recipient=recipient,
                               story_event=event_type)
        if settled and event_type:
            task = {**dict(task), "status": "SETTLED", "settled_at_minute": now,
                    "receipt_id": receipt["receipt_id"]}
            _put(actor, "p5_story_task", task)
        elif not settled:
            task = {**dict(task), "status": "REJECTED",
                    "rejection_reason": "native_command_did_not_settle_exact_item_transition",
                    "receipt_id": receipt["receipt_id"]}
            _put(actor, "p5_story_task", task)
            _append(actor, "P5_STORY_TASK_FEEDBACK",
                    f"story-task:{task['request_id']}:rejected:{now}",
                    {"actor_alias": alias, "request_id": task["request_id"],
                     "task_kind": task["task_kind"], "status": "REJECTED",
                     "reason": task["rejection_reason"], "item_id": task["item_id"],
                     "receipt_id": receipt["receipt_id"]})
        defer.returnValue({"story_task": dict(task), "native_action": operation,
                           "receipt": receipt, "settled": bool(settled)})

    return execute()


def step_story_aware_actor(actor):
    """Opt-in wrapper that leaves the frozen P5 callback unchanged."""
    from twisted.internet import defer
    from tools.native_platform_v0.p5.agency import step_actor

    pending = actor.attributes.get("pending_action", category="native_p3")
    offer = _get(actor, "p5_story_offer")
    active = _get(actor, "p5_story_task")
    active_slot = (isinstance(active, Mapping) and active.get("status") in {"ACCEPTED", "IN_PROGRESS"})
    if pending or (not isinstance(offer, Mapping) and not active_slot):
        return defer.maybeDeferred(step_actor, actor)

    @defer.inlineCallbacks
    def execute():
        # Let the existing two-callback physical social protocol keep priority.
        try:
            from tools.native_platform_v0.p3.p4_social import step_social
            consumed = yield defer.maybeDeferred(step_social, actor)
            if consumed is True:
                from tools.native_platform_v0.p3.agency import record
                from tools.native_platform_v0.p3.p4_world import clock_for_actor
                clock = clock_for_actor(actor)
                record(actor, {"sim_minute": clock["now"], "deadline": clock["deadline"],
                               "time_unit": clock.get("unit", "simulated-minute"),
                               "kind": "p5_social_callback_consumed"})
                defer.returnValue(None)
        except Exception as exc:
            from tools.native_platform_v0.p3.agency import record, set_value
            set_value(actor, "status", "ERROR")
            record(actor, {"kind": "p5_social_error",
                           "error": f"{type(exc).__name__}: {exc}",
                           "reason": "native social outcome uncertain; no other primitive dispatched"})
            defer.returnValue(None)
        try:
            result = yield defer.maybeDeferred(step_story_task, actor)
            if result is not None and (result.get("native_action") is not None
                                       or result.get("claim_callback") is True
                                       or result.get("story_task", {}).get("status") == "REJECTED"):
                from tools.native_platform_v0.p3.agency import record
                from tools.native_platform_v0.p3.p4_world import clock_for_actor
                clock = clock_for_actor(actor)
                record(actor, {"sim_minute": clock["now"], "deadline": clock["deadline"],
                               "time_unit": clock.get("unit", "simulated-minute"),
                               "kind": "p5_story_task_callback", "result": result})
                defer.returnValue(result)
        except Exception as exc:
            from tools.native_platform_v0.p3.agency import record, set_value
            set_value(actor, "status", "ERROR")
            record(actor, {"kind": "p5_story_task_error",
                           "error": f"{type(exc).__name__}: {exc}",
                           "reason": "story task failure did not authorize a substitute world effect"})
            defer.returnValue(None)
        defer.returnValue((yield defer.maybeDeferred(step_actor, actor)))

    return execute()


__all__ = ["step_story_task", "step_story_aware_actor"]
