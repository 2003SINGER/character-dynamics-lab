"""Actor-local ongoing goal and commitment arbitration for the station profile.

This is an explicit, project-specific priority rule, not a BDI implementation or
psychological score. Every completion transition requires a settled native receipt.
"""

from copy import deepcopy

ACTIVE = {"ACCEPTED", "IN_PROGRESS", "SUSPENDED"}
TERMINAL = {"SETTLED", "DECLINED", "EXPIRED", "CANCELLED_STALE"}


def matching_receipts(commitment, receipts):
    item_id = commitment.get("item_id")
    kind = commitment.get("task_kind")
    matched = []
    baseline = set(str(value) for value in commitment.get("receipt_frontier", ()))
    commitment_id = commitment.get("commitment_id")
    for row in receipts:
        if row.get("settled") is not True:
            continue
        receipt_id = row.get("receipt_id")
        if receipt_id is None or str(receipt_id) in baseline:
            continue
        # Every persistent actor goal owns its own task-instance receipts.
        # Matching only item/kind/destination lets an unrelated later action
        # accidentally settle a repeated or edited task for the same item.
        receipt_commitment_id = row.get("ongoing_commitment_id")
        if (commitment_id is None or receipt_commitment_id is None
                or str(receipt_commitment_id) != str(commitment_id)):
            continue
        if item_id is not None and str(row.get("item_id")) != str(item_id):
            continue
        operator = row.get("kind")
        if kind in ("deliver_supply", "archive_note", "return_stock") and operator == "drop":
            if row.get("after_item_room_id") == commitment.get("destination_id"):
                matched.append(row)
        elif kind == "handover_note" and operator == "give":
            if str(row.get("recipient_id")) == str(commitment.get("recipient_id")):
                matched.append(row)
        elif kind == "routine_route" and operator == "move":
            if commitment.get("route_waypoints"):
                # A route is one durable multi-leg commitment. Only its own
                # settled receipts can advance the ordered waypoint frontier.
                if str(row.get("ongoing_commitment_id")) != str(commitment.get("commitment_id")):
                    continue
                matched.append(row)
            elif row.get("after_room_id") == commitment.get("destination_id"):
                matched.append(row)
    return matched


def refresh_commitment(commitment, receipts, now_minute):
    """Return a copied row with only evidence-supported lifecycle transitions."""
    row = deepcopy(commitment)
    if row.get("status") in TERMINAL:
        return row
    matched = matching_receipts(row, receipts)
    deadline = row.get("deadline_minute")
    if deadline is not None:
        # P5 native receipts carry the simulated action minute. If a receipt
        # lacks that stamp, use the current sealed minute conservatively.
        matched = [receipt for receipt in matched
                   if receipt.get("sim_minute", now_minute) <= deadline]
    if row.get("task_kind") == "routine_route" and row.get("route_waypoints"):
        waypoints = list(row["route_waypoints"])
        progress = list(row.get("waypoint_receipts", [None] * len(waypoints)))
        if len(progress) != len(waypoints):
            progress = [None] * len(waypoints)
        previous_room = row.get("route_origin_id")
        for index, waypoint in enumerate(waypoints):
            if progress[index] is not None:
                previous_room = waypoint
                continue
            candidate = next((receipt for receipt in matched
                              if receipt.get("receipt_id") not in progress
                              and receipt.get("after_room_id") == waypoint
                              and (previous_room is None
                                   or receipt.get("before_room_id") == previous_room)), None)
            if candidate is None:
                break
            progress[index] = candidate.get("receipt_id")
            previous_room = waypoint
        row["waypoint_receipts"] = progress
        row["receipt_ids"] = list(dict.fromkeys(
            [*row.get("receipt_ids", []), *(value for value in progress if value is not None)]))
        if all(value is not None for value in progress):
            row["status"] = "SETTLED"
            row["reason"] = "all ordered route waypoints have matching commitment receipts"
        elif deadline is not None and now_minute > deadline:
            row["status"] = "EXPIRED"
            row["reason"] = "deadline passed before all ordered route receipts settled"
    elif matched:
        row["status"] = "SETTLED"
        row["receipt_ids"] = list(dict.fromkeys(
            [*row.get("receipt_ids", []), *(item.get("receipt_id") for item in matched
                                             if item.get("receipt_id"))]))
        row["reason"] = "settled native receipt matches this exact commitment"
    elif deadline is not None and now_minute > deadline:
        row["status"] = "EXPIRED"
        row["reason"] = "deadline passed without a matching settled receipt"
    elif row.get("status") == "ACCEPTED":
        row["status"] = "IN_PROGRESS"
        row["reason"] = row.get("reason") or "accepted commitment retained pending its first native action"
    row["updated_minute"] = now_minute
    return row


def arbitrate(offers, commitments, local_view, now_minute, busy=False):
    """Choose an eligible offer without discarding an active commitment.

    Existing active work has priority. An author offer is accepted only if it is
    feasible under actor-local availability and deadline; otherwise it remains a
    DEFERRED proposal with the concrete conflict recorded.
    """
    active = next((row for row in commitments
                   if row.get("status") in {"ACCEPTED", "IN_PROGRESS"}), None)
    if active:
        deferred = [{"offer_id": row.get("offer_id"), "reason": "actor retains an existing commitment",
                     "blocking_commitment_id": active.get("commitment_id"),
                     "blocking_commitment_status": active.get("status"),
                     "blocking_task_kind": active.get("task_kind"),
                     "blocking_route_waypoints": deepcopy(active.get("route_waypoints")),
                     "blocking_waypoint_receipts": deepcopy(active.get("waypoint_receipts", [])),
                     "evidence_receipt_ids": list(active.get("receipt_ids", []))}
                    for row in offers if row.get("source") == "AUTHOR"]
        return {"selected": active, "disposition": "CONTINUE", "reason": "retain existing actor commitment",
                "deferred_offers": deferred}

    observation = local_view["observation"]
    inventory = {str(row.get("id")) for row in observation.get("inventory", ())}
    visible = {str(row.get("id")) for row in observation.get("visible_items", ())}
    candidates = []
    rejected = []
    for offer in offers:
        reasons = []
        if not isinstance(offer.get("offer_id"), str) or not offer.get("offer_id"):
            reasons.append("task offer identity is missing")
        if offer.get("task_kind") not in {"deliver_supply", "archive_note", "handover_note",
                                           "routine_route", "return_stock"}:
            reasons.append("unsupported task kind")
        if offer.get("task_kind") != "routine_route":
            if offer.get("item_id") is None:
                reasons.append("exact item binding missing")
            elif str(offer["item_id"]) not in inventory | visible:
                # Item may be locally retained at a witnessed room, but not by
                # looking up global world state.
                remembered = any(str(row.get("id")) == str(offer["item_id"])
                                 and isinstance(row.get("room_id"), int)
                                 for row in observation.get("retained_witnesses", ()))
                if not remembered:
                    reasons.append("item unavailable in actor-local observation/history")
        if offer.get("task_kind") in {"archive_note", "handover_note", "deliver_supply",
                                      "return_stock"} and offer.get("destination_id") is None:
            reasons.append("destination binding missing")
        if offer.get("task_kind") == "handover_note" and offer.get("recipient_id") is None:
            reasons.append("recipient binding missing")
        deadline = offer.get("deadline_minute")
        if deadline is not None and deadline < now_minute:
            reasons.append("deadline already passed")
        if busy:
            reasons.append("actor has an unresolved native pending action")
        if reasons:
            rejected.append({"offer_id": offer.get("offer_id"), "eligible": False,
                             "reason": "; ".join(reasons)})
        else:
            candidates.append(offer)

    if not candidates:
        return {"selected": None, "disposition": "WAIT", "reason": "no locally feasible offer",
                "candidates": rejected}

    # Stable, explainable ordering: earliest deadline, then an already assigned
    # item task before discretionary routine activity, then SELF before AUTHOR
    # only for equal class/deadline, then stable offer id. No hidden utility score.
    infinity = 2**63 - 1
    action_task_priority = {"deliver_supply": 0, "archive_note": 0,
                            "handover_note": 0, "return_stock": 0,
                            "routine_route": 1}
    selected = min(candidates, key=lambda row: (
        row.get("deadline_minute") if row.get("deadline_minute") is not None else infinity,
        action_task_priority.get(row.get("task_kind"), 2),
        0 if row.get("source") == "SELF" else 1,
        str(row.get("offer_id", ""))))
    return {"selected": selected, "disposition": "ACCEPTED",
            "reason": "feasible offer selected by deadline then stable source/id ordering",
            "candidates": [{"offer_id": row.get("offer_id"), "eligible": True}
                           for row in candidates] + rejected}
