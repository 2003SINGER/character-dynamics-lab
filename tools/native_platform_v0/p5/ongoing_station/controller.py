"""Minute-boundary coordinator for the opt-in ongoing station.

The controller only compiles author constraints and publishes future actor
offers. It never executes an action or edits a sealed world prefix.
"""
from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping

from . import native


def initialize(pickup, actors, raw_profile):
    return native.initialize_station(pickup, actors, raw_profile)


def actor_callback(actor):
    """Run one station decision through the shared P3 native dispatcher."""
    from tools.native_platform_v0.p5 import service
    from tools.native_platform_v0.p3.agency import _dispatch_pending
    from tools.native_platform_v0.p5.world import scene_objects

    scene_id = service._attr(actor, "p3_scene_id")
    pickup, _rows = scene_objects(scene_id)
    minute = int(service._attr(pickup, "p4_clock", category="native_p3")["now"])
    meta = native.meta_for(pickup)
    projection = meta.get("published_projection")
    offers = meta.get("task_offers", [])
    from tools.native_platform_v0.p3.p4_social import step_social
    if step_social(actor):
        from tools.native_platform_v0.p3.agency import record
        record(actor, {"sim_minute": minute, "kind": "ongoing_station_social_callback_consumed",
                       "source": "native_p4_social", "goal_arbitration_deferred": True})
        return {"status": "SOCIAL_CALLBACK_CONSUMED", "minute": minute}
    alias = str(service._attr(actor, "p5_actor_alias", category="native_p5"))
    actor_offers = [row for row in offers if row.get("actor_alias") == alias]
    from .actor import advance_actor
    decision = advance_actor(actor, projection, actor_offers, minute)
    if decision.get("intent") is None or service._attr(actor, "pending_action", category="native_p3") is not None:
        return decision
    commitment = decision.get("commitment") or {}
    pending = {"status": "planned", "view": decision["view"],
               "goal": {"choice": commitment.get("goal_id"), "goal": commitment.get("task_kind")},
               "intent": decision["intent"], "ongoing_task": commitment}
    service._set(actor, "pending_action", pending, category="native_p3")
    return _dispatch_pending(actor, pending)


def publish_after_seal(scene_id, minute):
    """Publish only a decision over the just-sealed prefix for next callbacks."""
    from tools.native_platform_v0.p5 import service
    from tools.native_platform_v0.p5.world import scene_objects

    pickup, _rows = scene_objects(scene_id)
    profile = native.profile_for(pickup)
    projection, offers = author_offers(scene_id, minute)
    # author_offers persists its controller decision; reload to avoid clobbering
    # those append-only rows with a stale SaverDict snapshot.
    meta = native.meta_for(pickup)
    meta["published_projection"] = _safe(projection) if projection else None
    meta["task_offers"] = _safe(offers)
    meta["published_at_minute"] = int(minute)
    service._set(pickup, "p5_ongoing_station_meta", meta, category="native_p5")
    return {"published_at_minute": int(minute), "offer_count": len(offers),
            "projection_id": (f"{projection['station_id']}:{projection['version']}:{projection['bundle_hash'][:12]}"
                              if projection and projection.get("bundle_hash") else None)}


def _note_binding(rows, ledger, minute):
    for row in ledger:
        args = row.get("typed_args", {})
        receipt = args.get("physical_receipt", {})
        note_id = args.get("note_id")
        request_id = args.get("request_id")
        if (type(note_id) is int and note_id > 0 and isinstance(request_id, str) and request_id
                and row.get("event_type") == "SOCIAL_REQUEST" and row.get("sealed") is True
                and int(row.get("minute", -1)) <= minute
                and receipt.get("status") == "settled"
                and receipt.get("after_location_id") == args.get("recipient_actor_id")
                and receipt.get("recipient_inventory_actor_id") == args.get("recipient_actor_id")
                and args.get("initiator_actor_id") is not None
                and args.get("recipient_actor_id") is not None):
            note = next((obj for obj in rows if int(getattr(obj, "id", -1)) == note_id), None)
            if (note is not None
                    and str(note.attributes.get("p4_note_request_id", category="native_p3")) == str(request_id)):
                return note_id
    return None


def _scene_id(rows):
    for obj in rows:
        value = obj.attributes.get("p5_scene_id", category="native_p3")
        if value is None:
            value = obj.attributes.get("p5_scene_id", category="native_p5")
        if value:
            return str(value)
    return None


def _sealed_response(ledger, rows, note_id, minute):
    from tools.native_platform_v0.p5.world import _verified_social_responses

    verified = {row.get("event_id") for row in _verified_social_responses(ledger, rows,
                                                                            _scene_id(rows))}
    return next((row for row in ledger
                 if row.get("event_type") == "SOCIAL_RESPONSE" and row.get("sealed") is True
                 and row.get("event_id") in verified and int(row.get("minute", -1)) <= minute
                 and row.get("typed_args", {}).get("note_id") == note_id
                 and row.get("typed_args", {}).get("decision") in {"accepted", "rejected"}
                 and row.get("typed_args", {}).get("physical_receipt", {}).get("status") == "settled"), None)


def author_offers(scene_id, minute):
    """Run the existing high-level method search and queue only future offers."""
    from tools.native_platform_v0.p5 import service

    pickup, rows = service._scene_objects(scene_id)
    ledger = [service._plain_json(row) for row in service._attr(pickup, "p4_ledger", default=[])
              if row.get("sealed") is True and int(row.get("minute", -1)) <= minute]
    note_id = _note_binding(rows, ledger, minute)
    response = _sealed_response(ledger, rows, note_id, minute) if note_id else None
    profile = native.profile_for(pickup)
    if profile is None or profile.author is None:
        return {"station_id": profile.station_id, "version": profile.version,
                "bundle_hash": service._attr(pickup, "p5_ongoing_station_meta", category="native_p5", default={}).get("source_sha256"),
                "constraints": []}, []
    if note_id is None:
        projection = native.active_projection(pickup)
        return _projection_view(projection, profile), []
    from tools.native_platform_v0.p5.bundle import DEFAULT_ENTITIES
    from tools.trajectory_constraints_v0.types import StableEntity
    entities = dict(DEFAULT_ENTITIES)
    note_obj = next((obj for obj in rows if int(getattr(obj, "id", -1)) == note_id), None)
    if note_obj is None:
        return None, []
    entities["note"] = StableEntity("Item", str(note_id), str(note_obj.key))
    projection = native.active_projection(pickup, entities=entities)
    if projection is None or response is None:
        return _projection_view(projection, profile), []
    from tools.native_platform_v0.p5.story_process.model import default_actor_postresponse, load_request
    from tools.native_platform_v0.p5.ongoing_station.model import derive_story_requirements
    from tools.native_platform_v0.p5.story_process.planning import plan_story_process
    actor_objects = {str(service._attr(obj, "p5_actor_alias", category="native_p5")): obj
                     for obj in rows if service._attr(obj, "p5_actor_alias", category="native_p5") in {"A", "B"}}
    actor_local = {alias: _actor_local_row(actor, note_id, service) for alias, actor in actor_objects.items()}
    from tools.native_platform_v0.p5.story_process.native import _registered_destinations
    archive_room = next((obj for obj in rows
                         if service._attr(obj, "p5_story_archive", category="native_p5") is True), None)
    if archive_room is None:
        archive_id = service._attr(pickup, "p5_station_archive_room_id", category="native_p5")
        archive_room = next((obj for obj in rows if int(obj.id) == int(archive_id)), None) if archive_id else None
    if archive_room is None:
        raise ValueError("active station author constraint has no registered archive destination")
    destinations = _registered_destinations(scene_id, actor_objects, archive_room)
    offers = []
    meta = native.meta_for(pickup)
    selected_methods = dict(meta.get("selected_methods", {}))
    projection_id = f"{projection.station_id}:{projection.version}:{projection.source_sha256[:12]}"
    locked_process_constraints = [
        row for row in projection.constraints
        if row["control"].get("mode") == "locked_fragment"
        and ((row["source_constraint"].get("kind") == "event_by_deadline"
              and row["source_constraint"].get("event") == "note_archived"
              and row["source_constraint"].get("filters", {}).get("item") == "note")
             or (row["source_constraint"].get("kind") == "event_order"
                 and row["source_constraint"].get("before", {}).get("event") == "note_response"
                 and row["source_constraint"].get("before", {}).get("filters", {}).get("item") == "note"
                 and row["source_constraint"].get("after", {}).get("event") == "note_archived"
                 and row["source_constraint"].get("after", {}).get("filters", {}).get("item") == "note"))
    ]
    locked_method = next((_locked_core_method(row["locked_fragment"])
                          for row in locked_process_constraints), None)
    locked_runtime = {}
    sealed_typed_events = _typed_events(scene_id, note_id, minute, ledger,
                                         actor_objects, service, all_rows=rows)
    for locked_constraint in locked_process_constraints:
        locked_request = load_request(_runtime_request(
            profile, projection, locked_constraint, locked_constraint["control"],
            scene_id, note_id))
        locked_runtime[locked_constraint["constraint_id"]] = {
            "request": locked_request,
            "prefix_count": _locked_prefix_count(
                locked_request, sealed_typed_events, note_id,
                locked_constraint["constraint_id"]),
        }
    ordered_constraints = sorted(projection.constraints, key=lambda row: (
        0 if row["source_constraint"].get("kind") == "event_by_deadline" else 1,
        row["constraint_id"]))
    combined_lock_compatible = None
    for constraint in ordered_constraints:
        source = constraint["source_constraint"]
        archive_goal = (source.get("kind") == "event_by_deadline"
                        and source.get("event") == "note_archived"
                        and source.get("filters", {}).get("item") == "note")
        locked_process = constraint in locked_process_constraints
        if not archive_goal and not locked_process:
            continue
        binding = constraint["control"]
        deadline = int(source["deadline"])
        raw = _runtime_request(profile, projection, constraint, binding, scene_id, note_id)
        request = load_request(raw)
        story_requirements = (derive_story_requirements(projection, constraint, note_id)
                              if archive_goal else None)
        state = {"scenario_id": scene_id, "sealed_minute": minute,
                 "horizon": min(profile.horizon, 24), "request_id": request.request_id,
                 "request_version": request.version, "response": _response_projection(response, note_id),
                 "note": _note_state(note_obj, actor_objects), "actors": actor_local,
                 "destinations": destinations, "task_grant": dict(request.task_control_grant),
                 "current_obligations": _current_obligations(actor_objects, service),
                 "typed_trace": {"events": _typed_events(scene_id, note_id, minute, ledger,
                                                            actor_objects, service, all_rows=rows)},
                 "event_registry": request_registry()}
        strategy = service._attr(pickup, "p5_ongoing_station_strategy", category="native_p5", default="gtpyhop")
        decision = plan_story_process(request, state, strategy=strategy,
                                      required_story_events=story_requirements)
        if archive_goal and locked_method and not locked_process:
            locked_binding = next(row for row in locked_process_constraints
                                  if _locked_core_method(row["locked_fragment"]) == locked_method)
            runtime = locked_runtime[locked_binding["constraint_id"]]
            prior = selected_methods.get(constraint["constraint_id"])
            if isinstance(prior, Mapping):
                prior_method = prior.get("method_id")
                prior_is_current = (prior.get("version") == projection.version
                                    and prior.get("bundle_hash") == projection.source_sha256)
            else:
                prior_method, prior_is_current = prior, False
            control_still_allows_return = (
                locked_method in binding["allowed_methods"]
                and binding.get("file_actor") in (None, "A"))
            archive_minutes = int(destinations["archive"].get("estimated_minutes", 0))
            remaining_deadline_fits = minute + archive_minutes <= deadline
            verified_continuation = (
                runtime["prefix_count"] > 0 and prior_is_current
                and prior_method == locked_method and control_still_allows_return
                and remaining_deadline_fits)
            decision, compatible = _apply_locked_method_intersection(
                decision, locked_binding, locked_method,
                verified_prefix_count=runtime["prefix_count"],
                verified_continuation=verified_continuation)
            combined_lock_compatible = compatible is not None
        if locked_process:
            events = sealed_typed_events
            locked_tasks = decision.get("task_requests", [])
            runtime = locked_runtime[constraint["constraint_id"]]
            prefix_count = runtime["prefix_count"]
            next_locked = _next_locked_task(
                request, locked_tasks, events, note_id, constraint["constraint_id"],
                destinations=destinations, prefix_count=prefix_count)
            if combined_lock_compatible is False:
                task_rows = []
            elif decision.get("status") == "LOCKED_ABORTED" and prefix_count == 0:
                task_rows = []
            elif decision.get("status") == "LOCKED_ABORTED" and prefix_count > 0:
                # The original entry guard was consumed by the authenticated
                # prefix. Preserve the planner result but publish only the
                # exact remaining locked suffix from this adapter.
                task_rows = [next_locked] if next_locked else []
                decision = dict(decision, planner_status=decision.get("status"),
                                adapter_status=("CONTINUE_VERIFIED_LOCKED_SUFFIX"
                                                if next_locked else "LOCKED_PREFIX_COMPLETE"),
                                verified_locked_prefix_count=prefix_count,
                                verified_locked_prefix_event_ids=[
                                    event.get("event_id") for event in events
                                    if event.get("native_constraint_id") == constraint["constraint_id"]
                                    and event.get("native_control_source") == "LOCKED_FRAGMENT"])
            elif decision.get("status") == "LOCKED_CONSTRAINT_CONFLICT":
                task_rows = []
            else:
                task_rows = [next_locked] if next_locked else []
                if task_rows and task_rows[0].get("task_kind") == "handover_note":
                    task_rows[0] = dict(task_rows[0], recipient_alias="A",
                                        recipient_id=_recipient_id(task_rows[0], "A", actor_objects))
            prior_method = "locked_fragment"
        else:
            prior = selected_methods.get(constraint["constraint_id"])
            prior_method = prior.get("method_id") if isinstance(prior, Mapping) else prior
        if not locked_process:
            chosen_method = decision.get("selected_method")
            if chosen_method:
                prior_method = chosen_method
                selected_methods[constraint["constraint_id"]] = {
                    "method_id": chosen_method, "version": projection.version,
                    "bundle_hash": projection.source_sha256,
                    "selected_minute": int(minute),
                }
            # A decomposition can contain both handover and archive. Publish
            # only its first primitive until its give receipt is sealed.
            selected = next((row for row in decision.get("task_requests", [])
                             if row.get("source_method_id") == prior_method), None)
            if selected is not None and not (archive_goal and locked_method):
                task_rows = [selected]
                if selected["task_kind"] == "handover_note":
                    selected = dict(selected, recipient_alias="A",
                                    recipient_id=_recipient_id(selected, "A", actor_objects))
                    task_rows = [selected]
            elif prior_method == "return_then_file_by_A" and not (archive_goal and locked_method):
                typed_events = _typed_events(scene_id, note_id, minute, ledger, actor_objects,
                                             service, all_rows=rows)
                handover_requirement = story_requirements.get("required_handover") if story_requirements else None
                handed_over = _verified_handover_in_window(
                    typed_events, note_id, handover_requirement)
                continuation = _continuation_archive_task(
                    request, constraint, note_id, destinations, prior_method, handed_over,
                    required_story_events=story_requirements)
                task_rows = [continuation] if continuation else []
            else:
                task_rows = []
        for row in task_rows:
            task_actor = row["actor_alias"]
            recipient_id = row.get("recipient_id")
            if row["task_kind"] == "handover_note":
                recipient_alias = row.get("recipient_alias")
                bound_recipient = _recipient_id(row, recipient_alias, actor_objects)
                if recipient_id != bound_recipient:
                    raise ValueError("handover recipient binding is absent, self-directed, or stale")
            handover_req = (story_requirements or {}).get("required_handover")
            task_deadline = (handover_req["deadline_minute"]
                             if row["task_kind"] == "handover_note" and handover_req else deadline)
            task_start = (handover_req["start_minute"]
                          if row["task_kind"] == "handover_note" and handover_req
                          else (story_requirements or {}).get("archive_start_minute", 0))
            offers.append({"offer_id": row["request_id"], "source": "AUTHOR",
                           "goal_id": constraint["constraint_id"],
                           "task_kind": row["task_kind"], "item_id": row["item_id"],
                           "destination_id": row["destination_id"],
                           "recipient_id": recipient_id,
                           "deadline_minute": task_deadline, "earliest_terminal_minute": task_start,
                           "prerequisites": list(row["prerequisites"]),
                           "required_constraint_ids": list(row.get("required_constraint_ids", [])),
                           "required_story_event_types": list(row.get("required_story_event_types", [])),
                           "required_story_deadline_minute": row.get("required_story_deadline_minute"),
                           "constraint_id": constraint["constraint_id"], "item_key": note_obj.key,
                           "source_method_id": row["source_method_id"],
                           "control_source": row["control_source"], "grant_id": row["grant_id"],
                           "actor_alias": task_actor, "recipient_alias": row.get("recipient_alias"),
                           "rendezvous_destination_id": row.get("rendezvous_destination_id"),
                           "projection_id": projection_id,
                           "locked_fragment_hash": constraint.get("locked_fragment", {}).get("sequence_sha256")
                                                   if constraint.get("locked_fragment") else None,
                           "locked_sequence_index": (int(row["request_id"].rsplit(":", 1)[-1])
                                                     if row.get("source_method_id") == "locked_fragment" else None),
                           "entry_guard": constraint.get("locked_fragment", {}).get("entry_guard")
                                          if constraint.get("locked_fragment") else None})
        decision = dict(decision, selected_method=prior_method,
                        continuation_after_verified_handover=bool(task_rows and
                            task_rows[0].get("task_kind") == "archive_note" and
                            task_rows[0].get("source_method_id") == "return_then_file_by_A"))
        _save_controller_decision(pickup, constraint, projection, decision, minute, offers)
    meta = native.meta_for(pickup)
    meta["selected_methods"] = selected_methods
    native._store_meta(pickup, meta)
    return _projection_view(projection, profile), offers


def request_registry():
    from tools.native_platform_v0.p5.story_process.model import story_event_registry
    return story_event_registry()


def _recipient_id(task, recipient_alias, actor_objects):
    """Bind a handover to the other registered actor, never to the giver."""
    actor_alias = task.get("actor_alias")
    recipient = actor_objects.get(recipient_alias)
    if (actor_alias not in actor_objects or recipient is None
            or actor_alias == recipient_alias):
        raise ValueError("handover recipient must be a present actor distinct from giver")
    recipient_id = int(recipient.id)
    if task.get("recipient_id") not in (None, recipient_id):
        raise ValueError("handover recipient binding does not match registered recipient")
    return recipient_id


def _is_b_to_a_handover(event, note_id):
    args = event.get("args", {})
    return (event.get("event_type") == "p5_note_handed_over"
            and args.get("actor", {}).get("stable_id") == "B"
            and args.get("recipient", {}).get("stable_id") == "A"
            and args.get("item", {}).get("stable_id") == str(note_id))


def _verified_handover_in_window(typed_events, note_id, requirement):
    """Require exact authenticated same-note B→A evidence inside authored window."""
    for event in typed_events or ():
        if not _is_b_to_a_handover(event, note_id):
            continue
        minute = event.get("time")
        if type(minute) is not int:
            continue
        if requirement is None or requirement["start_minute"] <= minute <= requirement["deadline_minute"]:
            return True
    return False


def _locked_core_method(fragment):
    if not isinstance(fragment, Mapping):
        return None
    sequence = fragment.get("sequence", [])
    signature = [(row.get("actor_alias"), row.get("task_kind")) for row in sequence]
    if signature == [("B", "archive_note")]:
        return "file_by_B"
    if signature == [("B", "handover_note"), ("A", "archive_note")]:
        return "return_then_file_by_A"
    return None


def _apply_locked_method_intersection(decision, locked_constraint, required_method, *,
                                      verified_prefix_count=0, verified_continuation=False):
    """Keep result-method search, but restrict execution to the independent lock core."""
    compatible = next((row for row in decision.get("method_plans", [])
                       if row.get("method_id") == required_method and row.get("feasible")), None)
    continuation = bool(verified_continuation and verified_prefix_count > 0)
    updated = dict(decision, combined_locked_core={
        "constraint_id": locked_constraint["constraint_id"],
        "required_method": required_method,
        "compatible_method_feasible": compatible is not None,
        "verified_prefix_count": int(verified_prefix_count),
        "continuation_from_verified_prefix": continuation,
        "source": "independent_same_bundle_locked_binding",
    })
    if compatible or continuation:
        updated["search_selected_method"] = updated.get("selected_method")
        updated["selected_method"] = required_method
        updated["execution_constrained_by_locked_binding"] = True
        if continuation and compatible is None:
            updated["adapter_status"] = "CONTINUE_VERIFIED_LOCKED_SUFFIX"
            updated["planner_status"] = updated.get("status")
            updated["continuation_method_source"] = "current_source_version_selected_method_and_verified_locked_prefix"
    else:
        updated["selected_method"] = None
        updated["task_requests"] = []
        updated["status"] = "LOCKED_CONSTRAINT_CONFLICT"
    return updated, compatible if compatible is not None else ({"verified_prefix_continuation": True}
                                                               if continuation else None)


def _next_locked_task(request, task_rows, typed_events, note_id, constraint_id=None, *,
                      destinations=None, prefix_count=None):
    """Return only the next locked primitive after an authenticated ordered prefix."""
    fragment = request.locked_fragment
    if not fragment:
        return None
    rows_by_index = {int(row["request_id"].rsplit(":", 1)[-1]): row
                     for row in task_rows if row.get("source_method_id") == "locked_fragment"}
    verified_prefix = (_locked_prefix_count(request, typed_events, note_id, constraint_id)
                       if prefix_count is None else int(prefix_count))
    if verified_prefix >= len(fragment["sequence"]):
        return None
    index = verified_prefix
    locked = fragment["sequence"][index]
    task = rows_by_index.get(index)
    if task is not None:
        return task
    # Locked planner entry guards are intentionally one-time. After an exact
    # native prefix, construct only the next registered suffix primitive from
    # the immutable fragment and current registered destinations.
    if not destinations or locked["destination_ref"] not in destinations:
        return None
    return {"request_id": f"{request.request_id}:v{request.version}:locked:{index}",
            "actor_alias": locked["actor_alias"], "task_kind": locked["task_kind"],
            "item_id": note_id, "destination_id": destinations[locked["destination_ref"]]["id"],
            "item_ref": locked["item_ref"], "destination_ref": locked["destination_ref"],
            "prerequisites": ["exact_locked_sequence", "native_actor_accepts_task"],
            "source_method_id": "locked_fragment", "control_source": "LOCKED_FRAGMENT",
            "grant_id": request.task_control_grant["grant_id"],
            "constraint_id": constraint_id, "locked_fragment_hash": fragment["sequence_sha256"],
            "locked_sequence_index": index}


def _locked_prefix_count(request, typed_events, note_id, constraint_id):
    """Count only consecutive exact steps proven by locked-source native receipts."""
    fragment = request.locked_fragment
    if not fragment:
        return 0
    cursor = None
    count = 0
    for index, locked in enumerate(fragment["sequence"]):
        match = None
        for event in sorted(typed_events, key=lambda row: (row.get("time", -1), row.get("sequence", -1))):
            if not _locked_receipt_matches(event, request, constraint_id, index):
                continue
            if (event.get("args", {}).get("item", {}).get("stable_id") != str(note_id)
                    or event.get("args", {}).get("actor", {}).get("stable_id") != locked["actor_alias"]):
                continue
            if locked["task_kind"] == "handover_note":
                if not _is_b_to_a_handover(event, note_id):
                    continue
            elif event.get("event_type") != "p5_note_archived":
                continue
            key = (int(event.get("time", -1)), int(event.get("sequence", -1)))
            if cursor is not None and key <= cursor:
                continue
            match = event
            break
        if match is None:
            break
        cursor = (int(match["time"]), int(match["sequence"]))
        count += 1
    return count
    return None


def _locked_receipt_matches(event, request, constraint_id, sequence_index):
    """Require the real event's own commitment to prove this exact locked step."""
    fragment = request.locked_fragment or {}
    return (event.get("provenance") == "committed_ledger"
            and bool(event.get("event_id"))
            and event.get("native_control_source") == "LOCKED_FRAGMENT"
            and event.get("native_constraint_id") == constraint_id
            and event.get("native_source_method_id") == "locked_fragment"
            and event.get("native_grant_id") == request.task_control_grant["grant_id"]
            and event.get("native_locked_fragment_hash") == fragment.get("sequence_sha256")
            and event.get("native_locked_sequence_index") == sequence_index)


def _continuation_archive_task(request, constraint, note_id, destinations,
                               prior_method, verified_handover, required_story_events=None):
    """Return the second method step only after exact give evidence exists."""
    control = request.control
    if (not verified_handover or prior_method != "return_then_file_by_A"
            or prior_method not in control["allowed_methods"]
            or control.get("file_actor") not in (None, "A")):
        return None
    archive_id = (f"{request.request_id}:v{request.version}:"
                  "return_then_file_by_A:A:archive_note")
    handover = (required_story_events or {}).get("required_handover")
    return {"request_id": archive_id, "actor_alias": "A", "task_kind": "archive_note",
            "item_id": note_id, "destination_id": destinations["archive"]["id"],
            "recipient_id": None, "deadline_minute": request.objective["by_minute"],
            "earliest_terminal_minute": (required_story_events or {}).get("archive_start_minute", 0),
            "required_story_deadline_minute": (handover or {}).get("deadline_minute"),
            "prerequisites": ["committed_native_handover_receipt_for_exact_note_at_rendezvous",
                              "A_locally_observes_exact_note", "native_actor_accepts_task"],
            "source_method_id": prior_method,
            "control_source": ("AUTHORED" if control["mode"] == "direct" else
                               "LOCKED_FRAGMENT" if control["mode"] == "locked_fragment" else "PLANNER"),
            "grant_id": request.task_control_grant["grant_id"],
            "constraint_id": constraint["constraint_id"],
            "rendezvous_destination_id": destinations["handover"]["id"]}


def _cancel_stale_planned_pending(actor, actor_alias, stale_ids, minute, service):
    """Cancel only an authored plan that has not entered native dispatch."""
    if not stale_ids:
        return None
    from tools.native_platform_v0.p3.agency import record
    pending = service._plain_json(service._attr(
        actor, "pending_action", category="native_p3", default=None))
    task = pending.get("ongoing_task", {}) if isinstance(pending, Mapping) else {}
    source_offer = task.get("source_offer_id", task.get("commitment_id"))
    if (not pending or pending.get("status") != "planned"
            or task.get("source") != "AUTHOR" or source_offer not in stale_ids):
        return None
    commitments = service._plain_json(service._attr(
        actor, "ongoing_commitments", category="native_p5", default=[]))
    history = service._plain_json(service._attr(
        actor, "ongoing_goal_history", category="native_p5", default=[]))
    commitment_id = task.get("commitment_id")
    for commitment in commitments:
        if (commitment.get("commitment_id") == commitment_id
                and commitment.get("status") in {"ACCEPTED", "IN_PROGRESS", "SUSPENDED"}):
            commitment["status"] = "CANCELLED_STALE"
            commitment["updated_minute"] = int(minute)
            commitment["reason"] = "future author task was cancelled before native dispatch by a valid source edit"
    history.append({"minute": int(minute), "event": "COMMITMENT_CANCELLED_STALE",
                    "commitment_id": commitment_id, "source_offer_id": source_offer,
                    "reason": "planned action had not entered native dispatch",
                    "evidence_receipt_ids": []})
    service._set(actor, "ongoing_commitments", commitments, category="native_p5")
    service._set(actor, "ongoing_goal_history", history, category="native_p5")
    service._set(actor, "pending_action", None, category="native_p3")
    record(actor, {"kind": "ongoing_station_stale_offer_cancelled",
                   "minute": int(minute), "commitment_id": commitment_id,
                   "source_offer_id": source_offer, "status": "CANCELLED_STALE"})
    return {"actor_alias": actor_alias, "commitment_id": commitment_id,
            "source_offer_id": source_offer, "status": "CANCELLED_STALE"}


def _still_authorized_after_edit(task, constraint, *, destinations=None, actor_ids=None,
                                requires_handover=False):
    if not constraint:
        return False
    control = constraint.get("control", {})
    kind, actor = task.get("task_kind"), task.get("actor_alias")
    method = task.get("source_method_id")
    if control.get("mode") == "locked_fragment":
        fragment = constraint.get("locked_fragment") or {}
        if task.get("locked_fragment_hash") != fragment.get("sequence_sha256"):
            return False
        sequence = fragment.get("sequence", [])
        index = task.get("locked_sequence_index")
        if index is None:
            offer_id = task.get("source_offer_id", task.get("offer_id", ""))
            try:
                index = int(str(offer_id).rsplit(":", 1)[-1])
            except (TypeError, ValueError):
                return False
        return (type(index) is int and 0 <= index < len(sequence)
                and sequence[index].get("actor_alias") == actor
                and sequence[index].get("task_kind") == kind
                and task.get("destination_id") == (destinations or {}).get(
                    sequence[index].get("destination_ref")))
    if method not in control.get("allowed_methods", []):
        return False
    if kind == "archive_note":
        if requires_handover and method == "file_by_B":
            return False
        expected_actor = "B" if method == "file_by_B" else "A"
        allowed = (actor == expected_actor and control.get("file_actor") in (None, actor)
                   and task.get("destination_id") == (destinations or {}).get("archive"))
        if method == "return_then_file_by_A":
            allowed = (allowed and task.get("rendezvous_destination_id")
                       == (destinations or {}).get("handover"))
        return allowed
    if kind == "handover_note":
        return (method == "return_then_file_by_A" and actor == "B"
                and control.get("file_actor") in (None, "A")
                and task.get("recipient_alias") == "A"
                and task.get("recipient_id") == (actor_ids or {}).get("A")
                and task.get("destination_id") == (destinations or {}).get("handover"))
    return False


def _projection_view(projection, profile):
    return {"station_id": profile.station_id, "version": projection.version if projection else profile.version,
            "bundle_id": projection.bundle_id if projection else None,
            "bundle_hash": projection.source_sha256 if projection else None,
            "horizon": profile.horizon,
            "constraints": [dict(row) for row in projection.constraints] if projection else []}


def _runtime_request(profile, projection, constraint, binding, scene_id, note_id):
    from tools.native_platform_v0.p5.story_process.model import default_actor_postresponse
    source = constraint["source_constraint"]
    mode = binding["mode"]
    locked = constraint["locked_fragment"]
    grant_id = f"{profile.station_id}:{constraint['constraint_id']}:fixed-native-grant"
    return {"schema": "story-process-request-v1",
            "request_id": f"{profile.station_id}:{constraint['constraint_id']}",
            "version": projection.version, "scenario_id": scene_id,
            "objective": {"kind": "archive_same_note_after_response", "note_id": note_id,
                          "by_minute": int(source["deadline"]),
                          "deadline_basis": "absolute_scenario_minute",
                          "response_event_type": "p5_note_response",
                          "archive_event_type": "p5_note_archived"},
            "control": {"mode": mode, "file_actor": binding["file_actor"],
                        "allowed_methods": list(binding["allowed_methods"]),
                        "source": binding["source"]},
            "actor_postresponse": default_actor_postresponse(),
            "task_control_grant": {"grant_id": grant_id, "scenario_id": scene_id,
                                    "actor_aliases": ["A", "B"],
                                    "task_kinds": ["handover_note", "archive_note"],
                                    "valid_until_minute": 24},
            "edit_policy": {"editable_future_fields": ["control.file_actor", "control.allowed_methods"],
                            "settled_fields_immutable": True, "grant_immutable": True},
            "locked_fragment": deepcopy(locked)}


def _response_projection(row, note_id):
    if row is None:
        return None
    return {"outcome": row["typed_args"]["decision"], "event_id": row["event_id"],
            "minute": int(row["minute"]), "note_id": note_id}


def _note_state(note, actors):
    holder = next((alias for alias, actor in actors.items() if note in actor.contents), None)
    if holder is None:
        holder = "ROOM" if note.location is not None else None
    return {"item_id": int(note.id), "location_id": int(note.location.id) if note.location else 1,
            "holder_alias": holder}


def _remaining_work_lower_bound(actor, commitment, receipts):
    """Count only locally evidenced, unavoidable task primitives.

    This is a lower bound, not a route-feasibility proof: movement contributes
    at most one primitive when the actor is not already at the destination.
    Unknown item location or malformed route evidence remains unknown.
    """
    task_kind = commitment.get("task_kind")
    commitment_id = commitment.get("commitment_id")
    if not commitment_id:
        return None
    own = [row for row in receipts if row.get("settled") is True
           and str(row.get("ongoing_commitment_id")) == str(commitment_id)
           and row.get("ongoing_task_kind") == task_kind]
    if task_kind == "routine_route":
        waypoints = commitment.get("route_waypoints")
        waypoint_receipts = commitment.get("waypoint_receipts")
        if (not isinstance(waypoints, (list, tuple))
                or not isinstance(waypoint_receipts, (list, tuple))
                or len(waypoints) != len(waypoint_receipts)):
            return None
        # The commitment's waypoint_receipts can lag one callback: the just-
        # settled P3 command is visible in the sealed receipt frontier before
        # the next actor callback copies its ID into that field. Count only an
        # ordered prefix of exact-commitment native move receipts.
        own_moves = [row for row in own if row.get("kind") == "move"
                     and row.get("receipt_id") is not None]
        completed_prefix = 0
        for receipt in own_moves:
            if completed_prefix >= len(waypoints):
                return 0
            if receipt.get("after_room_id") != waypoints[completed_prefix]:
                return None
            completed_prefix += 1
        return len(waypoints) - completed_prefix

    if task_kind not in {"deliver_supply", "return_stock"}:
        return None
    item_id = commitment.get("item_id")
    destination_id = commitment.get("destination_id")
    if type(item_id) is not int or type(destination_id) is not int:
        return None
    completed_drop = any(row.get("kind") == "drop"
                         and str(row.get("item_id")) == str(item_id)
                         and row.get("after_item_room_id") == destination_id
                         for row in own)
    if completed_drop:
        return 0

    inventory = {int(item.id) for item in getattr(actor, "contents", ())
                 if getattr(item, "id", None) is not None}
    local_room_items = getattr(getattr(actor, "location", None), "contents", ())
    visible_here = any(getattr(item, "id", None) == item_id
                       and item.access(actor, "view", default=True)
                       for item in local_room_items)
    # Without the exact item in inventory or visible in this room, navigation
    # to a remembered/global location is not established by this local projection.
    if item_id not in inventory and not visible_here:
        return None
    room_id = getattr(getattr(actor, "location", None), "id", None)
    return (0 if item_id in inventory else 1) + 1 + (0 if room_id == destination_id else 1)


def _actor_local_row(actor, note_id, service):
    alias = str(service._attr(actor, "p5_actor_alias", category="native_p5"))
    local_items = [int(item.id) for item in actor.contents]
    local_items.extend(int(item.id) for item in (actor.location.contents if actor.location else [])
                       if item.access(actor, "view", default=True))
    commitments = service._plain_json(service._attr(actor, "ongoing_commitments", category="native_p5", default=[]))
    current = next((row for row in reversed(commitments)
                    if row.get("status") in {"ACCEPTED", "IN_PROGRESS", "SUSPENDED"}), None)
    pending = service._attr(actor, "pending_action")
    receipts = service._plain_json(service._attr(actor, "native_receipts", default=[]))
    remaining_work = 0
    if current is not None:
        if current.get("source") == "SELF" and current.get("task_kind") in {
                "routine_route", "deliver_supply", "return_stock"}:
            remaining_work = _remaining_work_lower_bound(actor, current, receipts)
        else:
            remaining_work = None
    status = ("IN_PROGRESS" if pending else
              current["status"] if current and current.get("source") == "AUTHOR" else "IDLE")
    if status == "SUSPENDED":
        status = "BLOCKED"
    active = None
    if current and current.get("task_kind") in {"handover_note", "archive_note"}:
        active = {"request_id": str(current.get("commitment_id")),
                  "task_kind": current["task_kind"], "item_id": current.get("item_id"),
                  "destination_id": current.get("destination_id"),
                  "status": "BLOCKED" if current["status"] == "SUSPENDED" else current["status"]}
    declined = next((row for row in reversed(commitments)
                     if row.get("status") == "DECLINED" and row.get("task_kind") in {"handover_note", "archive_note"}), None)
    if declined:
        active = {"request_id": str(declined.get("commitment_id")),
                  "task_kind": declined["task_kind"], "item_id": declined.get("item_id"),
                  "destination_id": declined.get("destination_id"), "status": "REJECTED"}
        status = "REJECTED"
    return {"present": actor.location is not None, "can_receive_note": actor.location is not None,
            "willing_to_archive": True, "locally_observed_item_ids": sorted(set(local_items)),
            "active_task": active, "task_status": status,
            "remaining_work_minutes": remaining_work}


def _current_obligations(actors, service):
    result = []
    for alias, actor in actors.items():
        commitments = service._plain_json(service._attr(actor, "ongoing_commitments", category="native_p5", default=[]))
        result.extend({"kind": "actor_commitment", "actor_alias": alias, **row} for row in commitments)
        pending = service._plain_json(service._attr(actor, "pending_action"))
        if pending:
            result.append({"kind": "native_pending_action", "actor_alias": alias,
                           "status": pending.get("status"), "operation_id": pending.get("operation_id")})
    return result


def _typed_events(scene_id, note_id, minute, ledger, actors, service, all_rows=None):
    from tools.native_platform_v0.p5.world import _verified_social_responses
    verified = {row.get("event_id") for row in _verified_social_responses(
        ledger, list(all_rows if all_rows is not None else actors.values()), scene_id)}
    events = []
    for row in ledger:
        if row.get("event_id") in verified and row.get("event_type") == "SOCIAL_RESPONSE" \
                and row.get("typed_args", {}).get("note_id") == note_id:
            args = row["typed_args"]
            by_id = {int(actor.id): alias for alias, actor in actors.items()}
            initiator = by_id.get(args.get("initiator_actor_id"))
            responder = by_id.get(args.get("responder_actor_id"))
            if initiator is None or responder is None or (initiator, responder) != ("A", "B"):
                continue
            events.append({"event_id": row["event_id"], "event_type": "p5_note_response",
                           "version": "1", "provenance": "committed_ledger",
                           "time": int(row["minute"]), "sequence": int(row["sequence"]),
                           "args": {"actor": {"entity_type": "Actor", "stable_id": "A", "label": "A"},
                                    "recipient": {"entity_type": "Actor", "stable_id": "B", "label": "B"},
                                    "item": {"entity_type": "Item", "stable_id": str(note_id), "label": "note"},
                                    "response": args.get("decision")}})
    for row in ledger:
        args = row.get("typed_args", {})
        if row.get("event_type") not in {"P5_ONGOING_STATION_NOTE_ARCHIVED", "P5_ONGOING_STATION_NOTE_HANDED_OVER"}:
            continue
        if args.get("item_id") != note_id or args.get("settled") is not True:
            continue
        actor_alias = args.get("actor_alias")
        if actor_alias not in {"A", "B"}:
            continue
        actor_obj = actors.get(actor_alias)
        if actor_obj is None:
            continue
        receipt_id = args.get("receipt_id")
        receipts = service._plain_json(service._attr(actor_obj, "native_receipts", default=[]))
        receipt = next((item for item in receipts if item.get("receipt_id") == receipt_id
                        and item.get("settled") is True
                        and item.get("item_id") == note_id
                        and item.get("ongoing_commitment_id") == args.get("commitment_id")), None)
        commitments = service._plain_json(service._attr(
            actor_obj, "ongoing_commitments", category="native_p5", default=[]))
        commitment = next((item for item in commitments
                           if item.get("commitment_id") == args.get("commitment_id")), None)
        if receipt is None or commitment is None:
            continue
        event_type = "p5_note_archived" if row["event_type"].endswith("ARCHIVED") else "p5_note_handed_over"
        if event_type == "p5_note_archived" and not (
                receipt.get("kind") == "drop" and commitment.get("task_kind") == "archive_note"
                and receipt.get("after_item_room_id") == commitment.get("destination_id")):
            continue
        typed_args = {"actor": {"entity_type": "Actor", "stable_id": actor_alias, "label": actor_alias},
                      "item": {"entity_type": "Item", "stable_id": str(note_id), "label": "note"}}
        if event_type == "p5_note_handed_over":
            recipient_alias = args.get("recipient_alias")
            if recipient_alias not in {"A", "B"}:
                continue
            recipient = actors.get(recipient_alias)
            if (receipt.get("kind") != "give" or commitment.get("task_kind") != "handover_note"
                    or recipient is None or receipt.get("recipient_id") != int(recipient.id)
                    or note_id not in receipt.get("recipient_inventory_ids", [])):
                continue
            typed_args["recipient"] = {"entity_type": "Actor", "stable_id": recipient_alias,
                                       "label": recipient_alias}
        events.append({"event_id": row["event_id"], "event_type": event_type, "version": "1",
                       "provenance": "committed_ledger", "time": int(row["minute"]),
                       "sequence": int(row["sequence"]), "args": typed_args,
                       "native_commitment_id": commitment.get("commitment_id"),
                       "native_constraint_id": commitment.get("constraint_id"),
                       "native_control_source": commitment.get("control_source"),
                       "native_source_method_id": commitment.get("source_method_id"),
                       "native_grant_id": commitment.get("grant_id"),
                       "native_locked_fragment_hash": commitment.get("locked_fragment_hash"),
                       "native_locked_sequence_index": commitment.get("locked_sequence_index")})
    return events


def evidence(scene_id, now):
    """Readback of profile ownership, actor commitments, offers and real receipts."""
    from tools.native_platform_v0.p5 import service
    from tools.native_platform_v0.p5.world import scene_objects

    pickup, rows = scene_objects(scene_id)
    profile = native.profile_for(pickup)
    if profile is None:
        return None
    meta = native.meta_for(pickup)
    actors = {str(service._attr(obj, "p5_actor_alias", category="native_p5")): obj
              for obj in rows if service._attr(obj, "p5_actor_alias", category="native_p5") in {"A", "B"}}
    raw_author = service._attr(pickup, "p5_ongoing_station_author", category="native_p5")
    ledger = service._plain_json(service._attr(pickup, "p4_ledger", default=[]))
    note_id = _note_binding(rows, ledger, now)
    typed_events = _typed_events(scene_id, note_id, now,
                                 ledger,
                                 actors, service, all_rows=rows) if note_id is not None else []
    verdicts = _author_verdicts(scene_id, pickup, rows, raw_author, note_id, typed_events, now)
    commitments = []
    decisions = []
    for alias, actor in actors.items():
        actor_commitments = service._plain_json(service._attr(
            actor, "ongoing_commitments", category="native_p5", default=[]))
        commitments.extend({"actor_id": int(actor.id), "actor_alias": alias, **row}
                           for row in actor_commitments)
        actor_log = service._plain_json(service._attr(actor, "log", default=[]))
        decisions.extend({"actor_alias": alias, **row} for row in actor_log
                         if row.get("kind") == "ongoing_station_decision")
    activation_events = [row for row in ledger if row.get("event_type") == "P5_ONGOING_STATION_ACTIVATION"]
    return {"schema": "ongoing-station-native-evidence-v1",
            "station_id": profile.station_id, "profile_version": profile.version,
            "horizon": profile.horizon, "author_status": meta.get("author_status"),
            "source_sha256": meta.get("source_sha256"), "active_author_version": meta.get("active_author_version"),
            "active_author_sha256": native._digest(raw_author) if raw_author else None,
            "projection_history": meta.get("projection_history", []),
            "activation_event_ids": meta.get("activation_event_ids", []),
            "activation_events": activation_events,
            "controller_decisions": meta.get("controller_decisions", []),
            "actor_goal_decisions": decisions,
            "actor_decisions": decisions,
            "commitments": commitments,
            "pending_offers": meta.get("task_offers", []),
            "stale_projection_ids": meta.get("stale_projection_ids", []),
            "stale_offer_ids": meta.get("stale_offer_ids", []),
            "actor_commitments": {alias: service._plain_json(service._attr(
                actor, "ongoing_commitments", category="native_p5", default=[])) for alias, actor in actors.items()},
            "actor_goal_history": {alias: service._plain_json(service._attr(
                actor, "ongoing_goal_history", category="native_p5", default=[])) for alias, actor in actors.items()},
            "native_receipts": {alias: [row for row in service._plain_json(service._attr(
                actor, "native_receipts", default=[])) if row.get("ongoing_task_kind")] for alias, actor in actors.items()},
            "bound_note_id": note_id, "typed_events": typed_events, "real_verdicts": verdicts,
            "execution_authority": "shared_P3_actor_callback_and_native_receipts"}


def _author_verdicts(scene_id, pickup, rows, raw_author, note_id, typed_events, now):
    if not raw_author:
        return []
    try:
        from tools.native_platform_v0.p5 import service
        from tools.native_platform_v0.p5.bundle import DEFAULT_ENTITIES, load_bundle
        from tools.native_platform_v0.p5.monitor import evaluate_bundle
        from tools.native_platform_v0.p5.story_process.model import story_event_registry
        from tools.trajectory_constraints_v0.trace import Event, Trace
        from tools.trajectory_constraints_v0.types import StableEntity
        from fractions import Fraction
        note_obj = next((obj for obj in rows if note_id is not None and int(obj.id) == note_id), None)
        entities = dict(DEFAULT_ENTITIES)
        if note_obj is not None:
            entities["note"] = StableEntity("Item", str(note_id), str(note_obj.key))
        bundle = load_bundle(service._plain_json(raw_author["bundle"]),
                             registry=story_event_registry(), entities=entities)
        trace = Trace(now=Fraction(now))
        for row in sorted(typed_events, key=lambda item: (item["time"], item["sequence"])):
            args = {key: StableEntity(value["entity_type"], value["stable_id"], value.get("label", ""))
                    if isinstance(value, Mapping) and set(value) >= {"entity_type", "stable_id"} else value
                    for key, value in row["args"].items()}
            trace.add_event(Event(row["event_id"], row["event_type"], Fraction(row["time"]),
                                  int(row["sequence"]), args, row["version"], row["provenance"]))
        trace.seal_events_through(Fraction(now))
        return evaluate_bundle(bundle, trace, registry=story_event_registry())
    except Exception as exc:
        return [{"status": "INDETERMINATE", "reason": f"typed station readback failed: {type(exc).__name__}: {exc}"}]


def _save_controller_decision(pickup, constraint, projection, decision, minute, offers):
    meta = native.meta_for(pickup)
    rows = list(meta.get("controller_decisions", []))
    rows.append({"minute": minute, "constraint_id": constraint["constraint_id"],
                 "station_id": projection.station_id, "source_bundle_id": projection.bundle_id,
                 "source_version": projection.version, "source_sha256": projection.source_sha256,
                 "decision": _safe(decision), "offer_ids": [row["offer_id"] for row in offers]})
    meta["controller_decisions"] = rows
    meta["task_offers"] = list(offers)
    pickup.attributes.add("p5_ongoing_station_meta", meta, category="native_p5")


def _safe(value):
    if isinstance(value, Mapping):
        return {str(k): _safe(v) for k, v in value.items() if k != "event_registry"}
    if isinstance(value, (list, tuple)):
        return [_safe(v) for v in value]
    if hasattr(value, "to_json"):
        return value.to_json()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def record_activation(scene_id, expected_version, minute):
    from tools.native_platform_v0.p5 import service
    from tools.native_platform_v0.p3.p4_world import append_event

    pickup, rows = service._scene_objects(scene_id)
    note = next((obj for obj in rows if service._attr(obj, "p4_note_request_id") is not None), None)
    entities = None
    if note is not None:
        from tools.native_platform_v0.p5.bundle import DEFAULT_ENTITIES
        from tools.trajectory_constraints_v0.types import StableEntity
        entities = dict(DEFAULT_ENTITIES)
        entities["note"] = StableEntity("Item", str(note.id), str(note.key))
    result = native.activate_author(pickup, expected_version=expected_version, now=minute,
                                    entities=entities)
    if result.get("ok") is True:
        meta = native.meta_for(pickup)
        event_id = f"station:{scene_id}:{minute}:activate:{expected_version}"
        meta["activation_event_ids"] = list(meta.get("activation_event_ids", [])) + [event_id]
        native._store_meta(pickup, meta)
    append_event(scene_id, {"event_type": "P5_ONGOING_STATION_ACTIVATION",
                            "event_id": f"station:{scene_id}:{minute}:activate:{expected_version}",
                            "typed_args": {"result": result, "expected_version": expected_version},
                            "sealed": True})
    return result


def record_edit(scene_id, raw_author, expected_version, minute):
    from tools.native_platform_v0.p5 import service
    from tools.native_platform_v0.p3.p4_world import append_event

    pickup, rows = service._scene_objects(scene_id)
    note = next((obj for obj in rows if service._attr(obj, "p4_note_request_id") is not None), None)
    entities = None
    if note is not None:
        from tools.native_platform_v0.p5.bundle import DEFAULT_ENTITIES
        from tools.trajectory_constraints_v0.types import StableEntity
        entities = dict(DEFAULT_ENTITIES)
        entities["note"] = StableEntity("Item", str(note.id), str(note.key))
    prior = evidence(scene_id, int(minute))
    prior_verdicts = (prior or {}).get("real_verdicts", {})
    constraint_rows = (prior_verdicts.get("constraints", [])
                       if isinstance(prior_verdicts, Mapping) else [])
    completed = {row["constraint_id"] for row in constraint_rows if row.get("status") == "SATISFIED"}
    evidenced = {row["constraint_id"] for row in constraint_rows if row.get("witness") is not None}
    try:
        proposed = native.validate_author(raw_author)
        proposed_handover = any(row.get("kind") == "event_by_deadline"
                                and row.get("event") == "note_handed_over"
                                and row.get("filters", {}).get("item") == "note"
                                for row in proposed["bundle"]["constraints"])
    except (TypeError, ValueError):
        # Let the canonical edit validator return its ordinary malformed-input
        # response; this preflight only adds the historical-event guard.
        proposed_handover = False
    prior_typed = (prior or {}).get("typed_events", [])
    if proposed_handover and note is not None and _has_verified_archive_for_note(prior_typed, int(note.id)):
        result = {"ok": False, "status": "HISTORICAL_CONSTRAINT_IMMUTABLE",
                  "reason": "same-note archive is already a committed native event; a later handover cannot be added retroactively"}
    else:
        result = native.edit_author(pickup, raw_author, expected_version=expected_version,
                                    now=minute, completed_ids=completed,
                                    evidenced_ids=evidenced, entities=entities)
    if result.get("ok") is True:
        new_projection = native.active_projection(pickup, entities=entities)
        new_constraints = {row["constraint_id"]: row for row in new_projection.constraints} if new_projection else {}
        required_handover = bool(new_projection and any(
            row.get("source_constraint", {}).get("kind") == "event_by_deadline"
            and row.get("source_constraint", {}).get("event") == "note_handed_over"
            for row in new_projection.constraints))
        meta = native.meta_for(pickup)
        current_offers = list(meta.get("task_offers", []))
        stale_ids = [row.get("offer_id") for row in current_offers
                     if row.get("source") == "AUTHOR" and row.get("offer_id")]
        stale_projection_ids = set(result.get("stale_projection_ids", []))
        actor_objects = {str(service._attr(obj, "p5_actor_alias", category="native_p5")): obj
                         for obj in rows
                         if service._attr(obj, "p5_actor_alias", category="native_p5") in {"A", "B"}}
        actor_ids = {alias: int(obj.id) for alias, obj in actor_objects.items()}
        archive_room = next((obj for obj in rows
                             if service._attr(obj, "p5_story_archive", category="native_p5") is True), None)
        if archive_room is None:
            archive_id = service._attr(pickup, "p5_station_archive_room_id", category="native_p5")
            archive_room = next((obj for obj in rows if archive_id and int(obj.id) == int(archive_id)), None)
        destination_ids = {}
        if archive_room is not None:
            from tools.native_platform_v0.p5.story_process.native import _registered_destinations
            raw_destinations = _registered_destinations(scene_id, actor_objects, archive_room)
            destination_ids = {key: value["id"] for key, value in raw_destinations.items()}
        invalidated_ids = {
            row["offer_id"] for row in current_offers
            if row.get("source") == "AUTHOR" and row.get("offer_id")
            and not _still_authorized_after_edit(
                row, new_constraints.get(row.get("constraint_id")),
                destinations=destination_ids, actor_ids=actor_ids,
                requires_handover=required_handover)
        }
        for obj in rows:
            alias = str(service._attr(obj, "p5_actor_alias", category="native_p5"))
            if alias not in {"A", "B"}:
                continue
            commitments = service._plain_json(service._attr(
                obj, "ongoing_commitments", category="native_p5", default=[]))
            for commitment in commitments:
                if (commitment.get("source") != "AUTHOR"
                        or commitment.get("status") not in {"ACCEPTED", "IN_PROGRESS", "SUSPENDED"}
                        or commitment.get("projection_id") not in stale_projection_ids):
                    continue
                candidate = {**commitment, "actor_alias": commitment.get("actor_alias", alias)}
                if not _still_authorized_after_edit(
                        candidate, new_constraints.get(commitment.get("constraint_id")),
                        destinations=destination_ids, actor_ids=actor_ids,
                        requires_handover=required_handover):
                    source_offer = commitment.get("source_offer_id", commitment.get("commitment_id"))
                    if source_offer:
                        invalidated_ids.add(source_offer)
        meta["stale_offer_ids"] = list(meta.get("stale_offer_ids", [])) + stale_ids
        meta["task_offers"] = [row for row in current_offers if row.get("source") != "AUTHOR"]
        # Let actor callbacks reconcile existing author commitments against
        # the newly accepted source at this boundary. This is projection-only:
        # no new author offers become eligible until the post-seal publish.
        active_profile = native.profile_for(pickup)
        meta["published_projection"] = (_safe(_projection_view(new_projection, active_profile))
                                        if new_projection is not None and active_profile is not None
                                        else None)
        meta["published_at_minute"] = int(minute)
        native._store_meta(pickup, meta)
        cancelled_pending = []
        if invalidated_ids:
            for obj in rows:
                alias = str(service._attr(obj, "p5_actor_alias", category="native_p5"))
                if alias not in {"A", "B"}:
                    continue
                cancelled = _cancel_stale_planned_pending(obj, alias, sorted(invalidated_ids), minute, service)
                if cancelled:
                    cancelled_pending.append(cancelled)
        result["cancelled_planned_tasks"] = cancelled_pending
        result["stale_offer_ids"] = stale_ids
        result["invalidated_offer_ids"] = sorted(invalidated_ids)
    append_event(scene_id, {"event_type": "P5_ONGOING_STATION_AUTHOR_EDIT",
                            "event_id": f"station:{scene_id}:{minute}:edit:{expected_version}",
                            "typed_args": {"result": result, "expected_version": expected_version},
                            "sealed": True})
    return result


def _has_verified_archive_for_note(typed_events, note_id):
    """Evidence input is already filtered to real native receipts by _typed_events."""
    for row in typed_events or ():
        if not isinstance(row, Mapping) or row.get("event_type") != "p5_note_archived" \
                or row.get("provenance") != "committed_ledger":
            continue
        item = row.get("args", {}).get("item")
        item_id = item.get("stable_id") if isinstance(item, Mapping) else item
        if str(item_id) == str(note_id):
            return True
    return False


__all__ = ["initialize", "actor_callback", "publish_after_seal", "author_offers",
           "record_activation", "record_edit"]
