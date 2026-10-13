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
        return (locked_task.get("actor_alias") == actor_alias
                and locked_task.get("task_kind") == task_kind
                and locked_task.get("item_ref") == "objective.note")
    if method not in control.get("allowed_methods", ()):
        return False
    file_actor = control.get("file_actor")
    if task_kind == "archive_note":
        if file_actor is not None and actor_alias != file_actor:
            return False
        if method == "file_by_B":
            return actor_alias == "B"
        if method == "return_then_file_by_A":
            return actor_alias == "A"
        return False
    if task_kind == "handover_note":
        return (method == "return_then_file_by_A" and file_actor in (None, "A")
                and actor_alias == "B"
                and commitment.get("recipient_alias") == "A")
    return False


def _same_author_task(commitment, offer):
    fields = ("constraint_id", "source_method_id", "actor_alias", "task_kind", "item_id",
              "destination_id", "recipient_id", "recipient_alias", "rendezvous_destination_id",
              "locked_fragment_hash", "locked_sequence_index")
    return commitment.get("source") == "AUTHOR" and offer.get("source") == "AUTHOR" \
        and all(commitment.get(key) == offer.get(key) for key in fields)


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
    }
    return json.dumps(evidence, sort_keys=True, separators=(",", ":"), default=str)


def _self_offers(actor, view, now_minute, receipts, commitments=()):
    contract = view.get("goal_contract", {})
    task_kind = contract.get("goal")
    if task_kind not in {"deliver_supply", "archive_note", "handover_note"}:
        task_kind = "deliver_supply" if contract.get("item_id") is not None else None
    offer_rows = []
    matching_drop = any(row.get("source") == "SELF" and row.get("status") == "SETTLED"
                        and row.get("task_kind") == task_kind
                        and str(row.get("item_id")) == str(contract.get("item_id"))
                        and row.get("destination_id") == contract.get("destination_id")
                        for row in commitments)
    if task_kind and not matching_drop and contract.get("item_id") is not None:
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
        "rendezvous_destination_id": offer.get("rendezvous_destination_id"),
        "entry_guard": deepcopy(offer.get("entry_guard")),
        "locked_fragment_hash": offer.get("locked_fragment_hash"),
        "locked_sequence_index": offer.get("locked_sequence_index"),
        "accepted_projection_id": offer.get("projection_id"),
        "last_known_item_room": offer.get("last_known_item_room"),
        "prerequisites": deepcopy(offer.get("prerequisites", [])),
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
                    row.setdefault("accepted_projection_id", old_projection_id)
                    row["superseded_projection_id"] = old_projection_id
                    row["projection_id"] = current_projection_id
                    row["authorized_projection_id"] = current_projection_id
                    row["updated_minute"] = now_minute
                    row["reason"] = "same author task suffix remains authorized after source edit"
                    history.append({"minute": now_minute, "event": "COMMITMENT_REAUTHORIZED",
                                    "commitment_id": row.get("commitment_id"),
                                    "constraint_id": row.get("constraint_id"),
                                    "source_method_id": row.get("source_method_id"),
                                    "superseded_projection_id": old_projection_id,
                                    "authorized_projection_id": current_projection_id,
                                    "evidence_receipt_ids": list(row.get("receipt_ids", []))})
                elif not _has_pending_for_commitment(pending, row.get("commitment_id")):
                    row["status"] = "CANCELLED_STALE"
                    row["updated_minute"] = now_minute
                    row["stale_projection_id"] = old_projection_id
                    row["cancellation_projection_id"] = current_projection_id
                    row["reason"] = "unexecuted author task suffix is no longer permitted by the active source"
    observation = view.get("observation", {})
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
