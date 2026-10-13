"""Opt-in actor callback for persistent station commitments over P3 local HTN."""

from copy import deepcopy
from collections.abc import Mapping
import json

from tools.native_platform_v0.p3.agency import get_value, observe_actor, record, set_value
from tools.native_platform_v0.p3.planning import plan_actor_task, thaw

from .goals import ACTIVE, TERMINAL, arbitrate, refresh_commitment

DECISION_SCHEMA = "ongoing-station-actor-decision-v1"
_STATION_CATEGORY = "native_p5"


def _station_get(actor, key, default=None):
    return actor.attributes.get(key, category=_STATION_CATEGORY, default=default)


def _station_set(actor, key, value):
    actor.attributes.add(key, value, category=_STATION_CATEGORY)


def _projection_value(projection, key, fallback=None):
    if projection is None:
        return fallback
    if isinstance(projection, Mapping):
        return projection.get(key, fallback)
    return getattr(projection, key, fallback)


def _projection_identity(projection):
    if projection is None:
        return None
    station_id = _projection_value(projection, "station_id")
    version = _projection_value(projection, "version")
    digest = _projection_value(projection, "bundle_hash",
                               _projection_value(projection, "source_sha256"))
    if station_id is None or version is None or not isinstance(digest, str):
        return None
    return f"{station_id}:{version}:{digest[:12]}"


def _has_pending_for_commitment(pending, commitment_id):
    if not isinstance(pending, Mapping):
        return False
    task = pending.get("ongoing_task")
    return isinstance(task, Mapping) and str(task.get("commitment_id")) == str(commitment_id)


def _projection_requires_handover(projection):
    """Fail closed when the current AuthorBundle requires this note's handover."""
    constraints = _projection_value(projection, "constraints", ()) or ()
    for row in constraints:
        source = row.get("source_constraint", {})
        if source.get("hard") is not True:
            continue
        if (source.get("kind") == "event_by_deadline"
                and source.get("event") == "note_handed_over"
                and source.get("filters", {}).get("item") == "note"
                and source.get("minimum", 1) >= 1):
            return True
        if (source.get("kind") == "event_order"
                and source.get("before", {}).get("event") == "note_handed_over"
                and source.get("before", {}).get("filters", {}).get("item") == "note"
                and source.get("after", {}).get("event") == "note_archived"
                and source.get("after", {}).get("filters", {}).get("item") == "note"):
            return True
    return False


def _repair_before_storage_constraint(projection):
    """Find only the registered hard repair-before-storage source constraint."""
    for row in _projection_value(projection, "constraints", ()) or ():
        source = row.get("source_constraint", {})
        if source.get("hard") is not True or source.get("kind") != "event_order":
            continue
        before, after = source.get("before", {}), source.get("after", {})
        if (before.get("event") == "station_passage_repaired"
                and before.get("filters") == {"actor": "B", "tool": "station_tool",
                                               "exit": "pickup_to_side_south"}
                and after.get("event") == "station_supply_stored"
                and after.get("filters") == {"actor": "A", "item": "courier_supply",
                                              "storage": "station_storage"}):
            return row
    return None


def _locally_knows_repair_witness(actor, view, order):
    """Use the actor's exact local exit observation, retaining only witnessed proof."""
    observation = view.get("observation", {})
    for target in observation.get("station_repair_targets", ()):
        receipt = target.get("last_repair_receipt")
        if (target.get("alias") == "pickup_to_side_south"
                and target.get("key") == "south"
                and target.get("traversable") is True
                and isinstance(receipt, Mapping)
                and receipt.get("outcome") == "SETTLED"
                and receipt.get("actor_alias") == "B"
                and type(receipt.get("completed_minute")) is int
                and isinstance(receipt.get("receipt_id"), str)):
            _station_set(actor, "p5_station_repair_witness", {
                "constraint_id": order.get("constraint_id"),
                "receipt_id": receipt["receipt_id"],
                "target_id": target.get("id"),
                "completed_minute": receipt["completed_minute"],
                "outcome": "SETTLED",
            })
            return True
    witness = _station_get(actor, "p5_station_repair_witness")
    return (isinstance(witness, Mapping)
            and witness.get("constraint_id") == order.get("constraint_id")
            and witness.get("outcome") == "SETTLED"
            and isinstance(witness.get("receipt_id"), str)
            and type(witness.get("completed_minute")) is int)


def _repair_before_storage_constraint(projection):
    """Return a registered hard station order, if the author requires it."""
    constraints = _projection_value(projection, "constraints", ()) or ()
    for row in constraints:
        source = row.get("source_constraint", {})
        if source.get("hard") is not True or source.get("kind") != "event_order":
            continue
        before, after = source.get("before", {}), source.get("after", {})
        if (before.get("event") == "station_passage_repaired"
                and before.get("filters") == {"actor": "B", "tool": "station_tool",
                                               "exit": "pickup_to_side_south"}
                and after.get("event") == "station_supply_stored"
                and after.get("filters") == {"actor": "A", "item": "courier_supply",
                                              "storage": "station_storage"}):
            return row
    return None


def _locally_knows_repair_witness(actor, view, order):
    observation = view.get("observation", {})
    for target in observation.get("station_repair_targets", ()):
        receipt = target.get("last_repair_receipt")
        if (target.get("alias") == "pickup_to_side_south"
                and target.get("key") == "south"
                and target.get("traversable") is True
                and isinstance(receipt, Mapping)
                and receipt.get("outcome") == "SETTLED"
                and receipt.get("actor_alias") == "B"
                and type(receipt.get("completed_minute")) is int
                and receipt.get("receipt_id")):
            _station_set(actor, "p5_station_repair_witness", {
                "constraint_id": order.get("constraint_id"),
                "receipt_id": receipt["receipt_id"],
                "target_id": target.get("id"),
                "completed_minute": receipt["completed_minute"],
                "observed_minute": observation.get("clock_minute"),
                "outcome": "SETTLED",
            })
            return True
    witness = _station_get(actor, "p5_station_repair_witness")
    return (isinstance(witness, Mapping)
            and witness.get("constraint_id") == order.get("constraint_id")
            and witness.get("outcome") == "SETTLED"
            and isinstance(witness.get("receipt_id"), str)
            and type(witness.get("completed_minute")) is int)


def _still_authorized(commitment, projection):
    """Whether this same author-task suffix remains permitted by the new source."""
    constraints = _projection_value(projection, "constraints", ()) or ()
    constraint = next((row for row in constraints
                       if row.get("constraint_id") == commitment.get("constraint_id")), None)
    if constraint is None:
        return False
    control = constraint.get("control", {})
    method = commitment.get("source_method_id")
    actor_alias = commitment.get("actor_alias")
    task_kind = commitment.get("task_kind")
    if control.get("mode") == "locked_fragment":
        fragment = constraint.get("locked_fragment") or {}
        index = commitment.get("locked_sequence_index")
        sequence = fragment.get("sequence", ())
        if (method != "locked_fragment"
                or commitment.get("locked_fragment_hash") != fragment.get("sequence_sha256")
                or type(index) is not int or not 0 <= index < len(sequence)):
            return False
        locked_task = sequence[index]
        if (locked_task.get("actor_alias") != actor_alias
                or locked_task.get("task_kind") != task_kind):
            return False
        item_ref = locked_task.get("item_ref")
        if item_ref == "objective.note":
            return str(commitment.get("item_alias", "note")) == "note"
        if item_ref is not None and str(commitment.get("item_alias")) != str(item_ref):
            return False
        tool_ref = locked_task.get("tool_ref")
        if tool_ref is not None and str(commitment.get("tool_alias")) != str(tool_ref):
            return False
        target_ref = locked_task.get("target_ref")
        if target_ref is not None and str(commitment.get("target_alias")) != str(target_ref):
            return False
        destination_ref = locked_task.get("destination_ref")
        return (destination_ref is None
                or str(commitment.get("destination_alias")) == str(destination_ref))
    if method not in control.get("allowed_methods", ()):
        return False
    file_actor = control.get("file_actor")
    if task_kind == "archive_note":
        if file_actor is not None and actor_alias != file_actor:
            return False
        if method == "file_by_B":
            return actor_alias == "B" and not _projection_requires_handover(projection)
        if method == "return_then_file_by_A":
            return actor_alias == "A"
        return False
    if task_kind == "handover_note":
        return (method == "return_then_file_by_A" and file_actor in (None, "A")
                and actor_alias == "B"
                and commitment.get("recipient_alias") == "A")
    if task_kind in {"inspect_supply", "repair_passage", "store_item"}:
        role = {"inspect_supply": "A", "repair_passage": "B", "store_item": "A"}[task_kind]
        expected_method = ({"inspect_then_repair", "repair_then_inspect"}
                           if task_kind in {"inspect_supply", "repair_passage"}
                           else {"inspect_then_repair", "repair_then_inspect"})
        return (method in control.get("allowed_methods", ()) and method in expected_method
                and actor_alias == role)
    return False


def _same_author_task(commitment, offer):
    fields = ("constraint_id", "source_method_id", "actor_alias", "task_kind", "item_id",
              "destination_id", "recipient_id", "recipient_alias", "rendezvous_destination_id",
              "tool_id", "target_id", "storage_destination_id", "item_alias", "tool_alias",
              "target_alias", "destination_alias", "locked_fragment_hash", "locked_sequence_index")
    return commitment.get("source") == "AUTHOR" and offer.get("source") == "AUTHOR" \
        and all(commitment.get(key) == offer.get(key) for key in fields)


def _lawful_locked_offer(offer, actor_alias, projection):
    """Validate a locked offer against the active projected core, not its claims."""
    if not (offer.get("source") == "AUTHOR"
            and offer.get("control_source") == "LOCKED_FRAGMENT"
            and offer.get("source_method_id") == "locked_fragment"
            and offer.get("actor_alias") == actor_alias
            and isinstance(offer.get("constraint_id"), str) and bool(offer.get("constraint_id"))
            and isinstance(offer.get("grant_id"), str) and bool(offer.get("grant_id"))
            and isinstance(offer.get("projection_id"), str)
            and isinstance(offer.get("locked_fragment_hash"), str)
            and len(offer["locked_fragment_hash"]) == 64
            and type(offer.get("locked_sequence_index")) is int
            and offer["locked_sequence_index"] >= 0):
        return False
    projection_id = _projection_identity(projection)
    if projection_id is None or offer.get("projection_id") != projection_id:
        return False
    constraint = next((row for row in (_projection_value(projection, "constraints", ()) or ())
                       if row.get("constraint_id") == offer.get("constraint_id")), None)
    if constraint is None or constraint.get("control", {}).get("mode") != "locked_fragment":
        return False
    fragment = constraint.get("locked_fragment") or {}
    sequence = fragment.get("sequence", ())
    index = offer["locked_sequence_index"]
    if (fragment.get("sequence_sha256") != offer.get("locked_fragment_hash")
            or not 0 <= index < len(sequence)):
        return False
    row = sequence[index]
    if row.get("actor_alias") != actor_alias or row.get("task_kind") != offer.get("task_kind"):
        return False
    aliases = (("item_ref", "item_alias"), ("tool_ref", "tool_alias"),
               ("target_ref", "target_alias"), ("destination_ref", "destination_alias"))
    for ref_key, alias_key in aliases:
        expected = row.get(ref_key)
        if ref_key == "item_ref" and expected == "objective.note":
            expected = "note"
        if expected is not None and str(offer.get(alias_key)) != str(expected):
            return False
    station_id = _projection_value(projection, "station_id")
    return offer.get("grant_id") == (
        f"{station_id}:{offer['constraint_id']}:fixed-native-grant")


def _same_task_semantics(left, right):
    if left.get("task_kind") != right.get("task_kind"):
        return False
    kind = left.get("task_kind")
    fields = {
        "inspect_supply": ("item_id", "tool_id", "target_id", "storage_destination_id"),
        "repair_passage": ("tool_id", "target_id"),
        "store_item": ("item_id", "storage_destination_id"),
        "lend_tool": ("tool_id", "recipient_id", "recipient_alias"),
        "return_tool": ("tool_id", "recipient_id", "recipient_alias"),
    }.get(kind, ("item_id", "tool_id", "target_id", "destination_id", "recipient_id"))
    return all(left.get(key) == right.get(key) for key in fields)


def _local_signature(view):
    observation = view.get("observation", {})
    evidence = {
        "room_id": observation.get("room_id"),
        "exits": observation.get("exits", []),
        "known_exits": observation.get("known_exits", {}),
        "known_traversability": observation.get("known_traversability", {}),
        "inventory_ids": sorted(str(row.get("id")) for row in observation.get("inventory", [])),
        "visible_items": sorted((str(row.get("id")), row.get("room_id"))
                                for row in observation.get("visible_items", [])),
        "retained_witnesses": sorted((str(row.get("id")), row.get("room_id"))
                                      for row in observation.get("retained_witnesses", [])),
        "item_location": observation.get("item_location"),
        # Station work and witnessed loan facts are part of local O. A lease
        # release, inspection, repair, or witnessed return can make a suspended
        # goal retryable even when the actor and ordinary inventory did not move.
        "station_tools": observation.get("station_tools", []),
        "station_supplies": observation.get("station_supplies", []),
        "station_repair_targets": observation.get("station_repair_targets", []),
        "station_storages": observation.get("station_storages", []),
        "station_loan_request": observation.get("station_loan_request"),
        "known_tool_events": observation.get("known_tool_events", []),
    }
    return json.dumps(evidence, sort_keys=True, separators=(",", ":"), default=str)


def _self_offers(actor, view, now_minute, receipts, commitments=()):
    contract = view.get("goal_contract", {})
    observation = view.get("observation", {})
    task_kind = contract.get("goal")
    if task_kind not in {"deliver_supply", "archive_note", "handover_note"}:
        task_kind = "deliver_supply" if contract.get("item_id") is not None else None
    offer_rows = []
    station_bindings = observation.get("station_task_bindings", ())
    station_content_active = bool(station_bindings)
    tools = observation.get("station_tools", ())
    supplies = observation.get("station_supplies", ())
    repair_targets = observation.get("station_repair_targets", ())
    storages = observation.get("station_storages", ())
    for binding in station_bindings:
        kind = binding.get("task_kind")
        if kind == "inspect_supply":
            tool = next((row for row in tools if row.get("id") == binding.get("tool_id")), None)
            supply = next((row for row in supplies if row.get("id") == binding.get("item_id")), None)
            if not (tool and supply and tool.get("lease_status") == "FREE"
                    and tool.get("room_id") == binding.get("target_room_id")
                    and supply.get("room_id") == binding.get("target_room_id")
                    and supply.get("inspection_status") != "APPROVED"):
                continue
        elif kind == "repair_passage":
            tool = next((row for row in tools if row.get("id") == binding.get("tool_id")), None)
            target = next((row for row in repair_targets if row.get("id") == binding.get("target_id")), None)
            if not (tool and target and tool.get("lease_status") == "FREE"
                    and tool.get("room_id") == binding.get("target_room_id")
                    and target.get("room_id") == binding.get("target_room_id")
                    and target.get("traversable") is False):
                continue
        elif kind == "store_item":
            prior_inspection = next((row for row in receipts
                                     if row.get("task_kind") == "inspect_supply"
                                     and row.get("settled") is True and row.get("outcome") == "SETTLED"
                                     and row.get("item_id") == binding.get("item_id")
                                     and row.get("effect", {}).get("after_status") == "APPROVED"), None)
            supply = next((row for row in supplies if row.get("id") == binding.get("item_id")), None)
            if not prior_inspection:
                continue
        else:
            continue
        offer = {**deepcopy(dict(binding)), "source": "SELF",
                 "goal_id": f"self-goal:{actor.id}:{kind}",
                 "offer_id": f"self:{actor.id}:{kind}:{binding.get('item_id', binding.get('target_id'))}",
                 "destination_id": binding.get("storage_destination_id"),
                 "source_offer_id": None, "constraint_id": None,
                 "prerequisites": []}
        if kind == "store_item" and prior_inspection:
            offer["prerequisites"] = [prior_inspection.get("receipt_id")]
            offer["last_known_item_room"] = prior_inspection.get("work_room_id")
        if not any(row.get("offer_id") == offer["offer_id"]
                   or row.get("source_offer_id") == offer["offer_id"] for row in commitments):
            offer_rows.append(offer)
    own_alias = _station_get(actor, "p5_actor_alias")
    request = observation.get("station_loan_request")
    if (isinstance(request, Mapping) and request.get("settled") is True
            and request.get("lender_alias") == own_alias
            and request.get("lender_id") == int(actor.id)
            and request.get("borrower_alias") in {"A", "B"}
            and type(request.get("tool_id")) is int
            and type(request.get("due_minute")) is int
            and type(request.get("requested_minute")) is int):
        tool = next((row for row in tools if row.get("id") == request.get("tool_id")), None)
        borrower = next((row for row in observation.get("station_peers", ())
                         if row.get("alias") == request.get("borrower_alias")
                         and row.get("id") == request.get("borrower_id")), None)
        offer_id = f"self:{actor.id}:lend_tool:{request.get('request_id')}"
        if (tool is not None and borrower is not None and tool.get("lease_status") == "FREE"
                and (tool.get("room_id") == observation.get("room_id")
                     or tool.get("held_by_actor_id") == int(actor.id))
                and not any(row.get("offer_id") == offer_id
                            or row.get("source_offer_id") == offer_id for row in commitments)):
            offer_rows.append({"offer_id": offer_id, "source": "SELF",
                               "goal_id": f"self-goal:{actor.id}:lend_tool:{request['request_id']}",
                               "task_kind": "lend_tool", "tool_id": int(request["tool_id"]),
                               "item_id": int(request["tool_id"]),
                               "recipient_id": int(request["borrower_id"]),
                               "recipient_alias": request["borrower_alias"],
                               "recipient_room_id": int(request["requester_room_id"]),
                               "due_minute": int(request["due_minute"]),
                               "loan_request_id": request["request_id"],
                               "requester_actor_id": int(request["requester_actor_id"]),
                               "requested_minute": int(request["requested_minute"]),
                               "deadline_minute": None, "prerequisites": [],
                               "constraint_id": None})
    for tool in tools:
        loan = tool.get("loan") or {}
        if (tool.get("held_by_actor_id") != int(actor.id)
                or loan.get("status") != "OUT"
                or loan.get("borrower_alias") != own_alias):
            continue
        lender = next((row for row in observation.get("station_peers", ())
                       if row.get("visible") is True
                       and row.get("alias") == loan.get("lender_alias")
                       and row.get("room_id") == observation.get("room_id")), None)
        if lender is None:
            continue
        offer_id = f"self:{actor.id}:return_tool:{loan.get('loan_id')}"
        if any(row.get("offer_id") == offer_id or row.get("source_offer_id") == offer_id
               for row in commitments):
            continue
        offer_rows.append({"offer_id": offer_id, "source": "SELF",
                           "goal_id": f"self-goal:{actor.id}:return_tool:{loan.get('loan_id')}",
                           "task_kind": "return_tool", "item_id": tool.get("id"),
                           "tool_id": tool.get("id"), "recipient_id": lender.get("id"),
                           "recipient_alias": loan.get("lender_alias"),
                           "recipient_room_id": lender.get("room_id"),
                           "due_minute": loan.get("due_minute"), "deadline_minute": None,
                           "constraint_id": None,
                           "prerequisites": [loan.get("loan_receipt_id")]})
    matching_drop = any(row.get("source") == "SELF" and row.get("status") == "SETTLED"
                        and row.get("task_kind") == task_kind
                        and str(row.get("item_id")) == str(contract.get("item_id"))
                        and row.get("destination_id") == contract.get("destination_id")
                        for row in commitments)
    matching_drop = matching_drop or any(
        row.get("settled") is True and row.get("kind") == "drop"
        and row.get("ongoing_task_kind") == task_kind
        and str(row.get("item_id")) == str(contract.get("item_id"))
        and row.get("after_item_room_id") == contract.get("destination_id")
        for row in receipts)
    if (not station_content_active and task_kind and not matching_drop
            and contract.get("item_id") is not None):
        offer_rows.append({
            "offer_id": f"self:{actor.id}:{task_kind}:{contract['item_id']}:{contract.get('destination_id')}",
            "source": "SELF", "goal_id": f"self-goal:{actor.id}:{task_kind}",
            "task_kind": task_kind, "item_id": contract.get("item_id"),
            "destination_id": contract.get("destination_id"),
            "recipient_id": contract.get("recipient_id"),
            "deadline_minute": None, "prerequisites": [], "constraint_id": None,
            "item_key": view.get("observation", {}).get("task_item", {}).get("key"),
            "last_known_item_room": view.get("observation", {}).get("item_location"),
        })
    # Reverse logistics is grounded only in this actor's own completed delivery
    # and its matching, settled get receipt. The source room is not a generic
    # storage location; it is the room this actor actually observed the item in.
    own_deliveries = [] if station_content_active else [row for row in receipts
                      if row.get("settled") is True and row.get("kind") == "drop"
                      and row.get("ongoing_task_kind") == "deliver_supply"
                      and row.get("ongoing_commitment_id") is not None]
    for delivery in reversed(own_deliveries):
        item_id = delivery.get("item_id")
        commitment_id = delivery.get("ongoing_commitment_id")
        source_get = next((row for row in receipts
                           if row.get("settled") is True and row.get("kind") == "get"
                           and str(row.get("item_id")) == str(item_id)
                           and str(row.get("ongoing_commitment_id")) == str(commitment_id)
                           and isinstance(row.get("before_item_room_id"), int)), None)
        if source_get is None or item_id is None:
            continue
        source_room = source_get["before_item_room_id"]
        delivered_room = delivery.get("after_item_room_id")
        if source_room == delivered_room:
            continue
        locally_present = any(str(row.get("id")) == str(item_id)
                              for row in (observation.get("inventory", [])
                                          + observation.get("visible_items", [])))
        locally_remembered = any(str(row.get("id")) == str(item_id)
                                 and row.get("room_id") == delivered_room
                                 for row in observation.get("retained_witnesses", []))
        if not (locally_present or locally_remembered):
            continue
        offer_id = (f"self:{actor.id}:return_stock:{item_id}:"
                    f"{delivery.get('receipt_id')}")
        if any(row.get("offer_id") == offer_id
               or (row.get("source_offer_id") == offer_id)
               for row in commitments):
            continue
        offer_rows.append({
            "offer_id": offer_id, "source": "SELF",
            "goal_id": f"self-goal:{actor.id}:return_stock:{delivery.get('receipt_id')}",
            "task_kind": "return_stock", "item_id": item_id,
            "destination_id": source_room, "recipient_id": None,
            "deadline_minute": None, "prerequisites": [delivery.get("receipt_id"),
                                                          source_get.get("receipt_id")],
            "constraint_id": None,
            "item_key": view.get("observation", {}).get("task_item", {}).get("key"),
            "last_known_item_room": observation.get("item_location") or delivered_room,
            "source_delivery_receipt_id": delivery.get("receipt_id"),
            "source_get_receipt_id": source_get.get("receipt_id"),
        })
    previous_move = next((row for row in reversed(receipts)
                          if row.get("settled") is True and row.get("kind") == "move"
                          and row.get("before_room_id") is not None
                          and row.get("after_room_id") is not None), None)
    current = view.get("observation", {}).get("room_id")
    target = previous_move.get("before_room_id") if previous_move and previous_move.get("after_room_id") == current else None
    if target is None:
        exits = sorted(view.get("observation", {}).get("exits", ()),
                       key=lambda row: (str(row.get("key", "")).casefold(),
                                        int(row.get("destination_id", -1))))
        target = next((row.get("destination_id") for row in exits
                       if row.get("destination_id") is not None and row.get("destination_id") != current), None)
    if target is not None and target != current:
        route_no = int(_station_get(actor, "ongoing_route_sequence", 0))
        waypoints = [target, current]
        offer_rows.append({
            "offer_id": f"self:{actor.id}:routine_route:{route_no}:{target}",
            "source": "SELF", "goal_id": f"self-goal:{actor.id}:routine_route:{route_no}",
            "task_kind": "routine_route", "item_id": None,
            "destination_id": target, "recipient_id": None,
            "route_origin_id": current, "route_waypoints": waypoints,
            "waypoint_receipts": [None, None],
            "deadline_minute": None, "prerequisites": [], "constraint_id": None,
            "item_key": None, "last_known_item_room": None,
        })
    return offer_rows


def _commitment_from_offer(offer, now_minute, receipts):
    return {
        "commitment_id": offer.get("offer_id"), "source": offer.get("source"),
        "goal_id": offer.get("goal_id"), "status": "ACCEPTED",
        "task_kind": offer.get("task_kind"), "item_id": offer.get("item_id"),
        "destination_id": offer.get("destination_id"),
        "recipient_id": offer.get("recipient_id"),
        "deadline_minute": offer.get("deadline_minute"),
        "earliest_terminal_minute": offer.get("earliest_terminal_minute"),
        "required_story_deadline_minute": offer.get("required_story_deadline_minute"),
        "accepted_minute": now_minute, "updated_minute": now_minute,
        "reason": "accepted from actor-local feasible candidate set",
        "receipt_ids": [], "source_offer_id": offer.get("offer_id"),
        "item_key": offer.get("item_key"),
        "route_origin_id": offer.get("route_origin_id"),
        "route_waypoints": deepcopy(offer.get("route_waypoints")),
        "waypoint_receipts": deepcopy(offer.get("waypoint_receipts")),
        "source_method_id": offer.get("source_method_id"),
        "control_source": offer.get("control_source"),
        "grant_id": offer.get("grant_id"),
        "projection_id": offer.get("projection_id"),
        "constraint_id": offer.get("constraint_id"),
        "actor_alias": offer.get("actor_alias"),
        "recipient_alias": offer.get("recipient_alias"),
        "recipient_room_id": offer.get("recipient_room_id"),
        "item_alias": offer.get("item_alias"), "tool_alias": offer.get("tool_alias"),
        "target_alias": offer.get("target_alias"),
        "destination_alias": offer.get("destination_alias"),
        "rendezvous_destination_id": offer.get("rendezvous_destination_id"),
        "entry_guard": deepcopy(offer.get("entry_guard")),
        "locked_fragment_hash": offer.get("locked_fragment_hash"),
        "locked_sequence_index": offer.get("locked_sequence_index"),
        "accepted_projection_id": offer.get("projection_id"),
        "last_known_item_room": offer.get("last_known_item_room"),
        "prerequisites": deepcopy(offer.get("prerequisites", [])),
        "source_delivery_receipt_id": offer.get("source_delivery_receipt_id"),
        "source_get_receipt_id": offer.get("source_get_receipt_id"),
        "tool_id": offer.get("tool_id"), "target_id": offer.get("target_id"),
        "target_room_id": offer.get("target_room_id"),
        "storage_destination_id": offer.get("storage_destination_id"),
        "storage_room_id": offer.get("storage_room_id"),
        "duration_minutes": offer.get("duration_minutes"),
        "due_minute": offer.get("due_minute"),
        "loan_request_id": offer.get("loan_request_id"),
        "requester_actor_id": offer.get("requester_actor_id"),
        "requested_minute": offer.get("requested_minute"),
        "process_id": offer.get("process_id"), "method_id": offer.get("method_id"),
        "recipient_alias": offer.get("recipient_alias"),
        "item_alias": offer.get("item_alias"),
        "receipt_frontier": [row.get("receipt_id") for row in receipts
                             if row.get("receipt_id") is not None],
    }


def advance_actor(actor, station_projection, offers, now_minute):
    """Advance one actor's goal/commitment state and propose one shared P3 HTN intent.

    ``station_projection`` must already be derived from the unique author source;
    it is used only as source/version provenance, never to inspect hidden world state.
    This callback does not dispatch an action or settle a goal.
    """
    view = observe_actor(actor)
    # Evennia SaverList/SaverDict values must be detached recursively before
    # mutation; shallow list copies can silently discard nested attribute edits.
    receipts = thaw(get_value(actor, "native_receipts", []))
    receipts.extend(thaw(_station_get(actor, "station_work_receipts", [])))
    commitments = thaw(_station_get(actor, "ongoing_commitments", []))
    history = thaw(_station_get(actor, "ongoing_goal_history", []))
    offers = thaw(offers or [])
    pending = get_value(actor, "pending_action")
    old_commitments = deepcopy(commitments)
    refreshed = [refresh_commitment(row, receipts, now_minute) for row in commitments]
    commitments = refreshed
    current_projection_id = _projection_identity(station_projection)
    if current_projection_id is not None:
        for row in commitments:
            if (row.get("source") == "AUTHOR" and row.get("status") in ACTIVE
                    and row.get("projection_id") is not None
                    and row.get("projection_id") != current_projection_id):
                old_projection_id = row.get("projection_id")
                if _still_authorized(row, station_projection):
                    current_offer = next((offer for offer in offers
                                          if _same_author_task(row, offer)), None)
                    row.setdefault("accepted_projection_id", old_projection_id)
                    row["superseded_projection_id"] = old_projection_id
                    row["projection_id"] = current_projection_id
                    row["authorized_projection_id"] = current_projection_id
                    prior_window = (row.get("deadline_minute"),
                                    row.get("earliest_terminal_minute"),
                                    row.get("required_story_deadline_minute"))
                    if current_offer is not None:
                        row["deadline_minute"] = current_offer.get("deadline_minute")
                        row["earliest_terminal_minute"] = current_offer.get("earliest_terminal_minute")
                        row["required_story_deadline_minute"] = current_offer.get(
                            "required_story_deadline_minute")
                    row["updated_minute"] = now_minute
                    row["reason"] = "same author task suffix remains authorized after source edit"
                    history.append({"minute": now_minute, "event": "COMMITMENT_REAUTHORIZED",
                                    "commitment_id": row.get("commitment_id"),
                                    "constraint_id": row.get("constraint_id"),
                                    "source_method_id": row.get("source_method_id"),
                                    "superseded_projection_id": old_projection_id,
                                    "authorized_projection_id": current_projection_id,
                                    "prior_terminal_window": list(prior_window),
                                    "current_terminal_window": [row.get("deadline_minute"),
                                                                row.get("earliest_terminal_minute"),
                                                                row.get("required_story_deadline_minute")],
                                    "evidence_receipt_ids": list(row.get("receipt_ids", []))})
                elif not _has_pending_for_commitment(pending, row.get("commitment_id")):
                    row["status"] = "CANCELLED_STALE"
                    row["updated_minute"] = now_minute
                    row["stale_projection_id"] = old_projection_id
                    row["cancellation_projection_id"] = current_projection_id
                    row["reason"] = "unexecuted author task suffix is no longer permitted by the active source"
    observation = view.get("observation", {})
    request = observation.get("station_loan_request")
    own_alias = _station_get(actor, "p5_actor_alias")
    active_commitment = next((row for row in commitments
                              if row.get("status") in {"ACCEPTED", "IN_PROGRESS"}), None)
    if (not pending and active_commitment is None and isinstance(request, Mapping)
            and request.get("settled") is True and request.get("borrower_alias") == own_alias
            and request.get("borrower_id") == int(actor.id)
            and type(request.get("due_minute")) is int
            and now_minute <= request["due_minute"]
            and request.get("requester_room_id") == observation.get("room_id")):
        history.append({"minute": now_minute, "event": "BORROW_REQUEST_WAIT",
                        "request_id": request.get("request_id"),
                        "lender_alias": request.get("lender_alias"),
                        "due_minute": request.get("due_minute"),
                        "reason": "actor locally witnessed a co-present request for this tool"})
        _station_set(actor, "ongoing_commitments", commitments)
        _station_set(actor, "ongoing_goal_history", history)
        decision = {"schema": DECISION_SCHEMA, "actor_id": actor.id, "minute": now_minute,
                    "author_source": {"station_id": _projection_value(station_projection, "station_id"),
                                      "version": _projection_value(station_projection, "version"),
                                      "bundle_hash": _projection_value(
                                          station_projection, "bundle_hash",
                                          _projection_value(station_projection, "source_sha256"))},
                    "goal_candidates": [], "selected_goal": None, "disposition": "WAIT",
                    "rationale": "waiting at the witnessed request room through the requested due minute",
                    "commitment": None, "planner": None, "intent": None,
                    "view": thaw(view), "pending_action_preserved": False}
        record(actor, {"kind": "ongoing_station_decision", **decision})
        return decision
    visible_or_held = {str(row.get("id")) for row in
                       (list(observation.get("inventory", ())) + list(observation.get("visible_items", ())))}
    retained = {str(row.get("id")) for row in observation.get("retained_witnesses", ())
                if isinstance(row.get("room_id"), int)}
    for row in commitments:
        if row.get("item_id") is not None:
            # A task's location binding is learned only from this actor's P3 O,
            # never copied from a controller's global object lookup.
            local_item_room = observation.get("item_location")
            if local_item_room is not None:
                row["last_known_item_room"] = local_item_room
        if row.get("status") in {"ACCEPTED", "IN_PROGRESS"} and row.get("item_id") is not None \
                and str(row["item_id"]) not in visible_or_held | retained:
            row["status"] = "SUSPENDED"
            row["reason"] = "assigned item is unavailable in current actor-local observation/history"
            row["updated_minute"] = now_minute

    # Every settled routine receipt creates the next real route candidate from
    # the prior locally witnessed room; sequence advances only on receipt.
    for prior, current in zip(old_commitments, commitments):
        if prior.get("status") in ACTIVE and current.get("status") == "SETTLED" \
                and current.get("task_kind") == "routine_route":
            _station_set(actor, "ongoing_route_sequence",
                         int(_station_get(actor, "ongoing_route_sequence", 0)) + 1)

    local_signature = _local_signature(view)
    suspended = [row for row in commitments if row.get("status") == "SUSPENDED"]
    retryable_suspended_ids = {str(row.get("commitment_id")) for row in suspended
                               if row.get("suspended_observation") != local_signature}
    candidates = list(offers) + _self_offers(actor, view, now_minute, receipts, commitments)
    repair_order = _repair_before_storage_constraint(station_projection)
    repair_witnessed = bool(repair_order and _locally_knows_repair_witness(actor, view, repair_order))
    if repair_order and not repair_witnessed:
        # A new SELF storage commitment may not race a hard authored repair
        # prerequisite. Existing commitments are retained and their terminal
        # store primitive is guarded below; movement/get preparation is intact.
        candidates = [row for row in candidates if not (
            row.get("source") == "SELF" and row.get("task_kind") == "store_item")]
    repair_order = _repair_before_storage_constraint(station_projection)
    if repair_order and not _locally_knows_repair_witness(actor, view, repair_order):
        # Do not accept a fresh SELF storage task that could race the authored
        # physical prerequisite. Existing accepted work is preserved; its
        # terminal store primitive is separately guarded below.
        candidates = [row for row in candidates if not (
            row.get("source") == "SELF" and row.get("task_kind") == "store_item")]
    actor_alias = _station_get(actor, "p5_actor_alias")
    safe_candidates = []
    for candidate in candidates:
        if candidate.get("control_source") == "LOCKED_FRAGMENT":
            if not _lawful_locked_offer(candidate, actor_alias, station_projection):
                history.append({"minute": now_minute, "event": "LOCKED_OFFER_REJECTED",
                                "offer_id": candidate.get("offer_id"),
                                "reason": "locked proposal lacks exact actor/source/grant/projection/core identity"})
                continue
            candidate["_authorized_locked_fragment"] = True
        safe_candidates.append(candidate)
    candidates = safe_candidates
    # A lender's choice is grounded only in that lender's receipt-time witnessed
    # return history. Missing history is uncertainty, not permission inferred
    # from the global ledger or the borrower's current position.
    known_returns = observation.get("known_tool_events", ())
    locally_authorized_offers = []
    for candidate in candidates:
        if candidate.get("task_kind") != "lend_tool":
            locally_authorized_offers.append(candidate)
            continue
        local_tool = next((row for row in observation.get("station_tools", ())
                           if str(row.get("id")) == str(candidate.get("tool_id"))), None)
        if isinstance(local_tool, Mapping) and (local_tool.get("loan") or {}).get("status") == "OUT":
            history.append({"minute": now_minute, "event": "TOOL_LOAN_OFFER_DEFERRED",
                            "offer_id": candidate.get("offer_id"),
                            "reason": "the exact tool is already out on a locally observed loan"})
            continue
        matching_history = [row for row in known_returns
                            if row.get("settled") is True
                            and str(row.get("tool_id")) == str(candidate.get("tool_id"))
                            and str(row.get("borrower_alias")) == str(candidate.get("recipient_alias"))
                            and row.get("event_type") in {"p5_station_tool_loaned",
                                                           "p5_station_tool_returned"}]
        latest = max(matching_history,
                     key=lambda row: int(row.get("witnessed_minute", -1)), default=None)
        if latest is None:
            # A first loan may establish the history; capacity-one physical
            # custody and a due time bound this provisional policy.
            due_minute = candidate.get("due_minute")
            if (type(due_minute) is int and due_minute >= now_minute
                    and (candidate.get("deadline_minute") is None
                         or due_minute <= candidate["deadline_minute"])):
                locally_authorized_offers.append(candidate)
                history.append({"minute": now_minute, "event": "TOOL_LOAN_OFFER_PROVISIONAL",
                                "offer_id": candidate.get("offer_id"),
                                "reason": "no prior locally witnessed matching loan history; allow one bounded first loan",
                                "due_minute": due_minute})
            else:
                history.append({"minute": now_minute, "event": "TOOL_LOAN_OFFER_DEFERRED",
                                "offer_id": candidate.get("offer_id"),
                                "reason": "first loan has no valid future due minute"})
        elif latest.get("event_type") == "p5_station_tool_returned" and latest.get("outcome") == "ON_TIME":
            locally_authorized_offers.append(candidate)
        else:
            history.append({"minute": now_minute, "event": "TOOL_LOAN_OFFER_DEFERRED",
                            "offer_id": candidate.get("offer_id"),
                            "reason": ("last locally witnessed matching loan return was late"
                                       if latest.get("event_type") == "p5_station_tool_returned"
                                       else "a prior matching loan remains unresolved in local receipt history"),
                            "witnessed_event_id": latest.get("event_id") if latest else None,
                            "witnessed_receipt_id": latest.get("receipt_id") if latest else None})
    candidates = locally_authorized_offers
    # At an actor-free boundary, a currently authorized locked suffix may take
    # the slot from a matching, not-yet-dispatched SELF commitment. Physical
    # work and existing P3 pending actions are never interrupted. The SELF
    # commitment and its receipt frontier remain historical and resumable; the
    # locked task gets a distinct AUTHOR commitment/receipt identity.
    yielded_self_ids = []
    active_work = _station_get(actor, "p5_station_work")
    if not pending and not (isinstance(active_work, Mapping)
                            and active_work.get("status") == "IN_PROGRESS"):
        locked_offers = [row for row in candidates
                         if row.get("_authorized_locked_fragment") is True]
        for locked_offer in locked_offers:
            for commitment_row in commitments:
                if (commitment_row.get("source") == "SELF"
                        and commitment_row.get("status") in {"ACCEPTED", "IN_PROGRESS"}
                        and _same_task_semantics(commitment_row, locked_offer)):
                    commitment_row["status"] = "SUSPENDED"
                    commitment_row["updated_minute"] = now_minute
                    commitment_row["reason"] = "yielded at a free boundary to a matching authorized locked author task"
                    commitment_row["suspended_observation"] = _local_signature(view)
                    yielded_self_ids.append(commitment_row.get("commitment_id"))
                    history.append({"minute": now_minute,
                                    "event": "SELF_COMMITMENT_YIELDED_TO_LOCKED_AUTHOR",
                                    "self_commitment_id": commitment_row.get("commitment_id"),
                                    "offer_id": locked_offer.get("offer_id"),
                                    "constraint_id": locked_offer.get("constraint_id"),
                                    "grant_id": locked_offer.get("grant_id"),
                                    "locked_fragment_hash": locked_offer.get("locked_fragment_hash"),
                                    "locked_sequence_index": locked_offer.get("locked_sequence_index"),
                                    "preserved_receipt_ids": list(commitment_row.get("receipt_ids", []))})
    coalesced_ids = set()
    for candidate in candidates:
        prior = next((row for row in commitments
                      if row.get("status") in ACTIVE and _same_author_task(row, candidate)), None)
        if prior is not None:
            coalesced_ids.add(id(candidate))
            offer_id = candidate.get("offer_id")
            if offer_id and prior.get("replacement_offer_id") != offer_id \
                    and prior.get("source_offer_id") != offer_id:
                prior["replacement_offer_id"] = offer_id
                history.append({"minute": now_minute, "event": "AUTHOR_OFFER_COALESCED",
                                "offer_id": offer_id,
                                "commitment_id": prior.get("commitment_id"),
                                "constraint_id": prior.get("constraint_id"),
                                "source_method_id": prior.get("source_method_id"),
                                "evidence_receipt_ids": list(prior.get("receipt_ids", []))})
    suspended_offer_ids = {str(row.get("source_offer_id") or row.get("commitment_id"))
                           for row in suspended}
    suspended_by_offer = {str(row.get("source_offer_id") or row.get("commitment_id")): row
                          for row in suspended}
    terminal_by_offer = {str(row.get("source_offer_id") or row.get("commitment_id")): row
                         for row in commitments if row.get("status") in TERMINAL}
    for candidate in candidates:
        prior = terminal_by_offer.get(str(candidate.get("offer_id")))
        if prior is not None:
            history.append({"minute": now_minute, "event": "TERMINAL_OFFER_IGNORED",
                            "offer_id": candidate.get("offer_id"),
                            "prior_commitment_id": prior.get("commitment_id"),
                            "prior_status": prior.get("status"),
                            "evidence_receipt_ids": list(prior.get("receipt_ids", []))})
        prior_suspended = suspended_by_offer.get(str(candidate.get("offer_id")))
        if candidate.get("source") == "AUTHOR" and prior_suspended is not None \
                and prior_suspended.get("suspended_observation") == local_signature:
            history.append({"minute": now_minute, "event": "AUTHOR_OFFER_DEFERRED",
                            "offer_id": candidate.get("offer_id"),
                            "blocking_commitment_id": prior_suspended.get("commitment_id"),
                            "blocking_commitment_status": "SUSPENDED",
                            "reason": "same task decomposition remains suspended until local evidence changes",
                            "evidence_receipt_ids": list(prior_suspended.get("receipt_ids", []))})
    # A resumed commitment keeps its original identity and progress; do not
    # recreate it from a duplicate offer row for the same task request.
    candidates = [row for row in candidates
                  if id(row) not in coalesced_ids
                  and str(row.get("offer_id")) not in suspended_offer_ids
                  and str(row.get("offer_id")) not in terminal_by_offer]
    # Do not repeatedly retry an unchanged failed decomposition. A changed
    # actor-local observation makes the same durable commitment eligible again.
    blocked_self_ids = {str(row.get("commitment_id")) for row in suspended
                        if row.get("suspended_observation") == local_signature}
    candidates = [row for row in candidates
                  if not (row.get("source") == "SELF" and str(row.get("offer_id")) in blocked_self_ids)]
    # A suspended commitment remains durable but competes again only after local
    # evidence changes; it does not monopolize the execution slot.
    candidates.extend({**row, "offer_id": row.get("source_offer_id") or row.get("commitment_id"),
                       "source": row.get("source"), "goal_id": row.get("goal_id")}
                      for row in commitments if row.get("status") == "SUSPENDED"
                      and str(row.get("commitment_id")) in retryable_suspended_ids)
    arbitration = arbitrate(candidates, commitments, view, now_minute, busy=bool(pending))
    for deferred in arbitration.get("deferred_offers", ()):
        history.append({"minute": now_minute, "event": "AUTHOR_OFFER_DEFERRED",
                        "offer_id": deferred.get("offer_id"),
                        "blocking_commitment_id": deferred.get("blocking_commitment_id"),
                        "blocking_commitment_status": deferred.get("blocking_commitment_status"),
                        "blocking_task_kind": deferred.get("blocking_task_kind"),
                        "blocking_route_waypoints": deferred.get("blocking_route_waypoints"),
                        "blocking_waypoint_receipts": deferred.get("blocking_waypoint_receipts", []),
                        "reason": deferred.get("reason"),
                        "evidence_receipt_ids": deferred.get("evidence_receipt_ids", [])})
    for candidate in arbitration.get("candidates", ()):
        if candidate.get("eligible") is False and any(
                offer.get("offer_id") == candidate.get("offer_id") and offer.get("source") == "AUTHOR"
                for offer in offers or ()):
            history.append({"minute": now_minute, "event": "AUTHOR_OFFER_DEFERRED",
                            "offer_id": candidate.get("offer_id"), "reason": candidate.get("reason"),
                            "evidence_receipt_ids": []})
    selected = arbitration.get("selected")
    commitment = None
    if selected and selected.get("commitment_id"):
        commitment = next((row for row in commitments
                           if row.get("commitment_id") == selected.get("commitment_id")
                           and row.get("status") in ACTIVE), None)
    if selected and commitment is None:
        local_offer = dict(selected)
        local_offer["last_known_item_room"] = observation.get("item_location")
        commitment = _commitment_from_offer(local_offer, now_minute, receipts)
        commitments.append(commitment)
        if selected.get("_authorized_locked_fragment") is True and yielded_self_ids:
            commitment["yielded_self_commitment_ids"] = list(yielded_self_ids)
        history.append({"minute": now_minute, "event": "COMMITMENT_ACCEPTED",
                        "commitment_id": commitment["commitment_id"],
                        "source": commitment["source"], "reason": arbitration.get("reason"),
                        "source_method_id": commitment.get("source_method_id"),
                        "control_source": commitment.get("control_source"),
                        "grant_id": commitment.get("grant_id"),
                        "projection_id": commitment.get("projection_id"),
                        "constraint_id": commitment.get("constraint_id"),
                        "route_waypoints": deepcopy(commitment.get("route_waypoints")),
                        "evidence_receipt_ids": []})

    planner = None
    intent = None
    disposition = arbitration.get("disposition", "WAIT")
    rationale = arbitration.get("reason", "no feasible candidate")
    if commitment:
        if pending:
            disposition = "CONTINUE"
            rationale = "preserve existing native pending action and actor commitment"
        else:
            task = {**commitment, "goal_id": commitment.get("goal_id"),
                    "task_kind": commitment.get("task_kind"),
                    "item_id": commitment.get("item_id"),
                    "destination_id": commitment.get("destination_id"),
                    "recipient_id": commitment.get("recipient_id")}
            planner = plan_actor_task(view, task)
            intent = planner.get("intent")
            earliest_terminal = commitment.get("earliest_terminal_minute")
            terminal_operator = ((commitment.get("task_kind") == "archive_note"
                                  and intent is not None and intent.get("operator") == "drop")
                                 or (commitment.get("task_kind") == "handover_note"
                                     and intent is not None and intent.get("operator") == "give"))
            if (repair_order and commitment.get("task_kind") == "store_item"
                    and intent is not None and intent.get("operator") == "store_item"
                    and not _locally_knows_repair_witness(actor, view, repair_order)):
                intent = None
                commitment["status"] = "IN_PROGRESS"
                commitment["updated_minute"] = now_minute
                commitment["reason"] = "waiting for actor-local witness of the registered repair prerequisite"
                disposition = "WAIT"
                rationale = "repair-before-storage prerequisite is not yet locally witnessed"
                history.append({"minute": now_minute,
                                "event": "STORE_WAITING_FOR_LOCAL_REPAIR_WITNESS",
                                "commitment_id": commitment.get("commitment_id"),
                                "constraint_id": repair_order.get("constraint_id"),
                                "evidence_receipt_ids": list(commitment.get("receipt_ids", []))})
            if (repair_order and commitment.get("task_kind") == "store_item"
                    and intent is not None and intent.get("operator") == "store_item"
                    and not _locally_knows_repair_witness(actor, view, repair_order)):
                intent = None
                commitment["status"] = "IN_PROGRESS"
                commitment["updated_minute"] = now_minute
                commitment["reason"] = "waiting for actor-local witness of the registered repair prerequisite"
                disposition = "WAIT"
                rationale = "repair-before-storage prerequisite is not yet locally witnessed"
                history.append({"minute": now_minute, "event": "STORE_WAITING_FOR_LOCAL_REPAIR_WITNESS",
                                "commitment_id": commitment.get("commitment_id"),
                                "constraint_id": repair_order.get("constraint_id"),
                                "evidence_receipt_ids": list(commitment.get("receipt_ids", []))})
            if (terminal_operator and type(earliest_terminal) is int
                    and now_minute < earliest_terminal):
                # Preserve the task and any route/get progress. Only the
                # authored terminal event is gated; preparation can proceed.
                intent = None
                commitment["status"] = "IN_PROGRESS"
                commitment["updated_minute"] = now_minute
                commitment["reason"] = "waiting for authored earliest terminal-event minute"
                disposition = "WAIT"
                rationale = "earliest terminal-event window has not opened"
                history.append({"minute": now_minute,
                                "event": "COMMITMENT_WAITING_FOR_TERMINAL_WINDOW",
                                "commitment_id": commitment.get("commitment_id"),
                                "earliest_terminal_minute": earliest_terminal,
                                "evidence_receipt_ids": list(commitment.get("receipt_ids", []))})
            if intent is not None and commitment.get("status") in {"ACCEPTED", "SUSPENDED"}:
                commitment["status"] = "IN_PROGRESS"
                commitment["updated_minute"] = now_minute
                history.append({"minute": now_minute, "event": "COMMITMENT_IN_PROGRESS",
                                "commitment_id": commitment["commitment_id"],
                                "reason": "shared P3 HTN proposed or resumed first primitive",
                                "evidence_receipt_ids": []})
            elif planner.get("status") in {"NO_PLAN", "BLOCKED", "BUDGET"}:
                commitment["status"] = "SUSPENDED"
                commitment["updated_minute"] = now_minute
                commitment["reason"] = planner.get("reason")
                commitment["suspended_observation"] = local_signature
                disposition = "DEFERRED"
                rationale = planner.get("reason", "current local plan unavailable")

    for before, after in zip(old_commitments, commitments):
        if before.get("status") != after.get("status"):
            if after.get("status") == "SETTLED":
                history.append({"minute": now_minute, "event": "COMMITMENT_SETTLED",
                                "commitment_id": after.get("commitment_id"),
                                "reason": after.get("reason"),
                                "evidence_receipt_ids": list(after.get("receipt_ids", []))})
            elif after.get("status") in {"EXPIRED", "SUSPENDED", "CANCELLED_STALE"}:
                history.append({"minute": now_minute, "event": f"COMMITMENT_{after['status']}",
                                "commitment_id": after.get("commitment_id"),
                                "reason": after.get("reason"),
                                "stale_projection_id": after.get("stale_projection_id"),
                                "cancellation_projection_id": after.get("cancellation_projection_id"),
                                "evidence_receipt_ids": list(after.get("receipt_ids", []))})

    # Do not drop historical commitments; rows are updated in place by identity.
    _station_set(actor, "ongoing_commitments", commitments)
    _station_set(actor, "ongoing_goal_history", history)
    decision = {
        "schema": DECISION_SCHEMA, "actor_id": actor.id, "minute": now_minute,
        "author_source": {"station_id": _projection_value(station_projection, "station_id"),
                          "version": _projection_value(station_projection, "version"),
                          "bundle_hash": _projection_value(
                              station_projection, "bundle_hash",
                              _projection_value(station_projection, "source_sha256"))},
        "goal_candidates": arbitration.get("candidates", []),
        "selected_goal": commitment.get("commitment_id") if commitment else None,
        "disposition": disposition, "rationale": rationale,
        "commitment": deepcopy(commitment), "planner": planner, "intent": intent,
        "view": thaw(view), "pending_action_preserved": bool(pending),
    }
    record(actor, {"kind": "ongoing_station_decision", **decision})
    return decision
