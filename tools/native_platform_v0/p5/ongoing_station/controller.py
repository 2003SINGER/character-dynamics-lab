"""Minute-boundary coordinator for the opt-in ongoing station.

The controller only compiles author constraints and publishes future actor
offers. It never executes an action or edits a sealed world prefix.
"""
from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping

from . import native


def initialize(pickup, actors, raw_profile):
    profile = native.initialize_station(pickup, actors, raw_profile)
    if profile is not None and getattr(profile, "game_content", None) == "station_work_v1":
        _store_station_entities(pickup, (pickup, *tuple(_scene_rows_for_actors(actors))))
    return profile


def _scene_rows_for_actors(actors):
    """Resolve only the generated scene bound to the supplied actors."""
    if not actors:
        return ()
    from tools.native_platform_v0.p5.world import scene_objects
    scene_id = next(iter(actors.values())).attributes.get("p3_scene_id", category="native_p3")
    return scene_objects(str(scene_id))[1]


def _station_entities(rows):
    """Bind registered station aliases to exact generated Evennia identities."""
    from tools.native_platform_v0.p5.bundle import DEFAULT_ENTITIES
    from tools.trajectory_constraints_v0.types import StableEntity
    entities = dict(DEFAULT_ENTITIES)
    by_id = {int(obj.id): obj for obj in rows if getattr(obj, "id", None) is not None}
    pickup = next((obj for obj in rows
                   if obj.attributes.get("p5_station_content_v1", category="native_p5") is not None), None)
    if pickup is None:
        return entities
    content = pickup.attributes.get("p5_station_content_v1", category="native_p5", default={})
    aliases = {"station_tool": ("tool_id", "Item"),
               "station_storage": ("storage_id", "Item"),
               "courier_supply": ("supply_id", "Item"),
               "pickup": (None, "Room"),
               "pickup_to_side_south": ("repair_exit_id", "Exit")}
    for alias, (key, entity_type) in aliases.items():
        obj = pickup if key is None else by_id.get(content.get(key))
        if obj is None:
            raise ValueError(f"registered station alias {alias!r} has no exact scene object")
        entities[alias] = StableEntity(entity_type, str(int(obj.id)), str(obj.key))
    return entities


def _store_station_entities(pickup, rows):
    entities = _station_entities(rows)
    pickup.attributes.add("p5_station_entities", {
        alias: {"entity_type": value.entity_type, "stable_id": value.stable_id,
                "display_name": value.display_name}
        for alias, value in entities.items()
    }, category="native_p5")
    return entities


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
    alias = str(service._attr(actor, "p5_actor_alias", category="native_p5"))
    # Existing timed work is a separate actor/tool commitment, never a second
    # P3 pending action. Exactly one due check is made per existing callback.
    active_work = service._attr(actor, "p5_station_work", category="native_p5")
    if isinstance(active_work, Mapping) and active_work.get("status") == "IN_PROGRESS":
        from .work import advance_work
        return advance_work(actor, now_minute=minute)
    from tools.native_platform_v0.p3.p4_social import step_social
    if step_social(actor):
        from tools.native_platform_v0.p3.agency import record
        record(actor, {"sim_minute": minute, "kind": "ongoing_station_social_callback_consumed",
                       "source": "native_p4_social", "goal_arbitration_deferred": True})
        return {"status": "SOCIAL_CALLBACK_CONSUMED", "minute": minute}
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
    if profile.game_content == "station_work_v1":
        projection = native.active_projection(pickup, entities=_station_entities(rows))
        return _station_work_author_offers(scene_id, int(minute), pickup, rows,
                                           profile, projection, ledger)
    if note_id is None:
        entities = (_station_entities(rows)
                    if service._attr(pickup, "p5_station_content_v1", category="native_p5") is not None
                    else None)
        projection = native.active_projection(pickup, entities=entities)
        return _projection_view(projection, profile), []
    from tools.native_platform_v0.p5.bundle import DEFAULT_ENTITIES
    from tools.trajectory_constraints_v0.types import StableEntity
    entities = dict(DEFAULT_ENTITIES)
    note_obj = next((obj for obj in rows if int(getattr(obj, "id", -1)) == note_id), None)
    if note_obj is None:
        return None, []
    entities["note"] = StableEntity("Item", str(note_id), str(note_obj.key))
    if service._attr(pickup, "p5_station_content_v1", category="native_p5") is not None:
        entities = _station_entities(rows)
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


def _station_work_author_offers(scene_id, minute, pickup, rows, profile, projection, ledger):
    """Build a sealed planner input and publish only the next authorized work task.

    This is a thin AuthorBundle adapter: it does not observe actors or mutate
    world state. The planner receives the last persisted actor-local P3 views,
    native commitments/pending actions, exact registered station objects, and
    receipt-authenticated TypedIR events.
    """
    from tools.native_platform_v0.p5 import service
    from tools.native_platform_v0.p5.story_process.planning import plan_station_work_order

    if projection is None:
        return _projection_view(None, profile), []
    entities = _station_entities(rows)
    content = service._plain_json(service._attr(
        pickup, "p5_station_content_v1", category="native_p5", default={}))
    by_id = {int(obj.id): obj for obj in rows if getattr(obj, "id", None) is not None}
    tool = by_id.get(content.get("tool_id"))
    storage = by_id.get(content.get("storage_id"))
    if tool is None or storage is None:
        raise ValueError("station-work author projection lacks registered tool/storage objects")
    actors = {str(service._attr(obj, "p5_actor_alias", category="native_p5")): obj
              for obj in rows if service._attr(obj, "p5_actor_alias", category="native_p5") in {"A", "B"}}
    if set(actors) != {"A", "B"}:
        raise ValueError("station-work author planning requires the registered A/B actors")
    lease = service._plain_json(service._attr(tool, "p5_station_tool_lease",
                                               category="native_p5", default={}))
    active_tool_lease = None
    local_actors = {}
    for alias, actor in actors.items():
        decisions = [row for row in service._plain_json(service._attr(actor, "log", default=[]))
                     if row.get("kind") == "ongoing_station_decision"
                     and type(row.get("minute")) is int and row.get("minute") <= minute]
        latest = decisions[-1] if decisions else None
        local_view = latest.get("view") if isinstance(latest, Mapping) else None
        pending = service._plain_json(service._attr(actor, "pending_action", category="native_p3"))
        if local_view is None:
            # No observe_actor fallback: an absent persisted local view means
            # the adapter cannot honestly construct planner input yet.
            return _projection_view(projection, profile), []
        actor_commitments = service._plain_json(service._attr(
            actor, "ongoing_commitments", category="native_p5", default=[]))
        actor_receipts = service._plain_json(service._attr(actor, "native_receipts", default=[]))
        planner_commitments, matched_lease = _station_planner_commitments(
            actor, actor_commitments, actor_receipts, lease, tool_id=int(tool.id),
            actor_alias=alias,
            active_work=service._plain_json(service._attr(
                actor, "p5_station_work", category="native_p5", default=None)))
        if matched_lease is not None:
            if active_tool_lease is not None and active_tool_lease != matched_lease:
                raise ValueError("more than one actor claims the registered station tool lease")
            active_tool_lease = matched_lease
        local_actors[alias] = {
            "local_view": local_view,
            "commitments": planner_commitments,
            "pending_action": pending,
        }
    holder = next((alias for alias, actor in actors.items() if tool in actor.contents), None)
    station_tool = {"id": int(tool.id),
                    "room_id": int(tool.location.id) if tool.location else None,
                    "holder_alias": holder,
                    "lease_status": lease.get("status", "UNKNOWN")}
    if type(lease.get("due_minute")) is int:
        station_tool["due_minute"] = lease["due_minute"]
    workbench_id = service._attr(tool, "p5_station_workbench_room_id", category="native_p5")
    if type(workbench_id) is not int:
        raise ValueError("registered station tool is missing its exact workbench room ID")
    constraints = [_safe(dict(row)) for row in projection.constraints]
    grants = {row["constraint_id"]:
              f"{profile.station_id}:{row['constraint_id']}:fixed-native-grant"
              for row in constraints}
    typed_events = _station_work_typed_events(ledger, rows, actors, service)
    sealed_state = {
        "sealed_minute": int(minute), "horizon": int(profile.horizon),
        "station_id": profile.station_id,
        "projection_id": f"{projection.station_id}:{projection.version}:{projection.source_sha256[:12]}",
        "grant_id": next(iter(grants.values()), None), "grant_ids": grants,
        "constraint_id": constraints[0]["constraint_id"] if constraints else None,
        "station_content": {"tool_id": int(content["tool_id"]),
            "storage_id": int(content["storage_id"]), "supply_id": int(content["supply_id"]),
            "repair_exit_id": int(content["repair_exit_id"]),
            "workbench_room_id": workbench_id, "storage_room_id": int(storage.location.id)},
        "station_tool": station_tool, "active_tool_lease": active_tool_lease,
        "actors": local_actors, "constraints": constraints,
        "typed_trace": {"events": typed_events},
    }
    strategy = service._attr(pickup, "p5_ongoing_station_strategy",
                             category="native_p5", default="gtpyhop")
    decision = plan_station_work_order(sealed_state, strategy=strategy)
    offers = _station_work_offers_from_decision(
        decision, projection, profile, sealed_state, minute)
    meta = native.meta_for(pickup)
    # A literal author offer can be deferred while the actor finishes an
    # already-running local commitment. Keep that same proposal visible at
    # later boundaries only while its exact source projection/grant/core and
    # absolute deadline remain current. This is not a queue or a new task:
    # actor arbitration still decides whether to accept it.
    offers = _retain_deferred_station_offers(
        meta.get("task_offers", []), offers, projection, profile, minute,
        actors, content, typed_events)
    controller_rows = list(meta.get("controller_decisions", []))
    for constraint in projection.constraints:
        constraint_id = constraint["constraint_id"]
        controller_rows.append({"minute": minute, "constraint_id": constraint_id,
            "station_id": projection.station_id, "source_bundle_id": projection.bundle_id,
            "source_version": projection.version, "source_sha256": projection.source_sha256,
            "decision": _safe({**decision, "grant_id": grants.get(constraint_id)}),
            "offer_ids": [row["offer_id"] for row in offers
                          if constraint_id in row.get("required_constraint_ids", [])]})
    meta["controller_decisions"] = controller_rows
    meta["task_offers"] = offers
    native._store_meta(pickup, meta)
    return _projection_view(projection, profile), offers


def _retain_deferred_station_offers(previous, current, projection, profile,
                                    minute, actors, content, typed_events):
    """Retain only still-authorized deferred literal station tasks.

    The actor's append-only history is the evidence that this exact offer was
    deferred. Current actor commitments and receipt-authenticated TypedIR
    events prevent resurrecting accepted or completed work.
    """
    from tools.native_platform_v0.p5 import service

    if not isinstance(previous, list) or not previous:
        return current
    projection_id = f"{projection.station_id}:{projection.version}:{projection.source_sha256[:12]}"
    constraints = {row["constraint_id"]: row for row in projection.constraints}
    histories = []
    commitments = []
    for alias, actor in actors.items():
        histories.extend(service._plain_json(service._attr(
            actor, "ongoing_goal_history", category="native_p5", default=[])))
        commitments.extend(service._plain_json(service._attr(
            actor, "ongoing_commitments", category="native_p5", default=[])))
    deferred_ids = {row.get("offer_id") for row in histories
                    if row.get("event") == "AUTHOR_OFFER_DEFERRED" and row.get("offer_id")}
    existing_ids = {row.get("offer_id") for row in current if row.get("offer_id")}
    prior_offers = {row.get("offer_id"): row for row in previous
                    if isinstance(row, Mapping) and row.get("offer_id")}
    retained = []
    for offer_id in deferred_ids - existing_ids:
        offer = prior_offers.get(offer_id)
        constraint = (constraints.get(offer.get("constraint_id"))
                      if isinstance(offer, Mapping) else None)
        expected_grant = (f"{profile.station_id}:{offer.get('constraint_id')}:fixed-native-grant"
                          if isinstance(offer, Mapping) else None)
        if _deferred_literal_offer_is_current(
                offer, constraint, projection_id, expected_grant, minute,
                deferred_ids, commitments, typed_events, content):
            retained.append(dict(offer))
    return [*current, *retained]


def _deferred_literal_offer_is_current(offer, constraint, projection_id, grant_id,
                                      minute, deferred_ids, commitments,
                                      typed_events, content):
    if not isinstance(offer, Mapping) or offer.get("source") != "AUTHOR":
        return False
    offer_id = offer.get("offer_id")
    if (offer_id not in deferred_ids or offer.get("control_source") != "LOCKED_FRAGMENT"
            or offer.get("projection_id") != projection_id
            or offer.get("grant_id") != grant_id
            or type(offer.get("deadline_minute")) is not int
            or offer["deadline_minute"] < minute
            or not isinstance(constraint, Mapping)):
        return False
    fragment = constraint.get("locked_fragment") or {}
    sequence = fragment.get("sequence", [])
    index = offer.get("locked_sequence_index")
    if (constraint.get("control", {}).get("mode") != "locked_fragment"
            or offer.get("locked_fragment_hash") != fragment.get("sequence_sha256")
            or type(index) is not int or not 0 <= index < len(sequence)):
        return False
    kind = offer.get("task_kind")
    exact_refs = {
        "inspect_supply": {"item_ref": "courier_supply", "tool_ref": "station_tool",
                           "destination_ref": "station_storage"},
        "repair_passage": {"tool_ref": "station_tool", "target_ref": "pickup_to_side_south"},
        "store_item": {"item_ref": "courier_supply", "destination_ref": "station_storage"},
    }.get(kind)
    row = sequence[index]
    if (exact_refs is None or row.get("actor_alias") != offer.get("actor_alias")
            or row.get("task_kind") != kind
            or any(row.get(key) != value for key, value in exact_refs.items())):
        return False
    if any(commitment.get("source_offer_id") == offer_id
           or commitment.get("commitment_id") == offer_id for commitment in commitments):
        return False
    event_type, arg_name, content_key = {
        "inspect_supply": ("p5_station_supply_inspected", "item", "supply_id"),
        "repair_passage": ("p5_station_passage_repaired", "exit", "repair_exit_id"),
        "store_item": ("p5_station_supply_stored", "item", "supply_id"),
    }[kind]
    expected_id = str(content.get(content_key))
    for event in typed_events:
        if event.get("event_type") != event_type or event.get("provenance") != "committed_ledger":
            continue
        value = event.get("args", {}).get(arg_name)
        stable_id = value.get("stable_id") if isinstance(value, Mapping) else value
        if stable_id is not None and str(stable_id) == expected_id:
            return False
    return True


def _station_work_offers_from_decision(decision, projection, profile, sealed, minute):
    """Validate planner proposals against the exact bundle grants and prefix."""
    if not isinstance(decision, Mapping) or decision.get("native_execution_occurred") is not False:
        raise ValueError("station planner must return a non-executing decision object")
    if decision.get("status") != "CONDITIONAL_PLAN":
        return []
    method = decision.get("selected_method")
    plans = [row for row in decision.get("method_plans", [])
             if isinstance(row, Mapping) and row.get("method_id") == method
             and row.get("feasible") is True]
    if len(plans) != 1:
        raise ValueError("station planner selected method must have one feasible candidate record")
    constraints = {row["constraint_id"]: row for row in projection.constraints}
    requests = plans[0].get("task_requests", [])
    if not isinstance(requests, list):
        raise ValueError("station planner task_requests must be an ordered list")
    if not requests:
        return []
    # The planner emits only unsettled tasks, in method dependency order. Still
    # re-check exact receipt evidence here so no later child can be published
    # if an adapter or planner regression returns an incomplete prefix.
    prior_kinds = {"inspect_supply": "p5_station_supply_inspected",
                   "repair_passage": "p5_station_passage_repaired",
                   "store_item": "p5_station_supply_stored"}
    events = sealed["typed_trace"]["events"]
    completed = {kind for kind, event_type in prior_kinds.items()
                 if any(row.get("event_type") == event_type
                        and row.get("provenance") == "committed_ledger"
                        for row in events)}
    task = requests[0]
    kind = task.get("task_kind")
    expected_actor = {"inspect_supply": "A", "repair_passage": "B", "store_item": "A"}.get(kind)
    if expected_actor is None or task.get("actor_alias") != expected_actor:
        raise ValueError("station planner proposed a task outside the registered actor/task map")
    if (kind == "store_item" and "inspect_supply" not in completed):
        return []
    if kind == "store_item" and "repair_passage" not in completed:
        # Both registered methods place storage after the two serialized work
        # tasks. A store proposal cannot jump over the repair dependency.
        return []
    if kind == "repair_passage" and method == "inspect_then_repair" and "inspect_supply" not in completed:
        return []
    if kind == "inspect_supply" and method == "repair_then_inspect" and "repair_passage" not in completed:
        return []
    required_ids = task.get("required_constraint_ids")
    if (not isinstance(required_ids, list) or not required_ids
            or any(cid not in constraints for cid in required_ids)):
        raise ValueError("station planner task lacks exact source constraints")
    constraint_id = task.get("constraint_id")
    if constraint_id not in required_ids or constraint_id not in constraints:
        raise ValueError("station planner task is not bound to one of its exact source constraints")
    source_constraint = constraints[constraint_id]
    binding = source_constraint["control"]
    if any(method not in constraints[cid]["control"].get("allowed_methods", [])
           for cid in required_ids):
        raise ValueError("station planner task method is not authorized by every required constraint")
    expected_ids = {"inspect_supply": sealed["station_content"]["supply_id"],
                     "repair_passage": sealed["station_content"]["repair_exit_id"],
                     "store_item": sealed["station_content"]["supply_id"]}
    if task.get("target_id" if kind == "repair_passage" else "item_id") != expected_ids[kind]:
        raise ValueError("station planner task exact item/target does not match scene registration")
    content = sealed["station_content"]
    if kind in {"inspect_supply", "repair_passage"} and task.get("tool_id") != content["tool_id"]:
        raise ValueError("station planner task does not bind the exact registered shared tool")
    expected_room = (content["workbench_room_id"]
                     if kind in {"inspect_supply", "repair_passage"} else None)
    if task.get("target_room_id") != expected_room:
        raise ValueError("station planner task does not preserve its exact registered target room")
    expected_storage = (content["storage_id"] if kind in {"inspect_supply", "store_item"}
                        else None)
    if task.get("storage_destination_id") != expected_storage:
        raise ValueError("station planner task does not bind its exact storage container")
    expected_storage_room = (content["storage_room_id"]
                             if kind in {"inspect_supply", "store_item"} else None)
    if task.get("storage_room_id") != expected_storage_room:
        raise ValueError("station planner task does not bind its exact storage room")
    locked_hash = task.get("locked_fragment_sha256")
    locked_index = task.get("locked_sequence_index")
    # A locked binding may own a wider event_order constraint than its literal
    # fragment.  For example, a B/repair prerequisite can be required by the
    # locked repair-before-store order while the authored core itself contains
    # only A/store_item.  Only a task that matches a literal sequence row is a
    # LOCKED_FRAGMENT task; prerequisite rows remain ordinary planner proposals.
    fragment = source_constraint.get("locked_fragment") or {}
    sequence = fragment.get("sequence", [])
    lock_exact_refs = {
        "repair_passage": {"tool_ref": "station_tool",
                           "target_ref": "pickup_to_side_south"},
        "inspect_supply": {"item_ref": "courier_supply", "tool_ref": "station_tool",
                           "destination_ref": "station_storage"},
        "store_item": {"item_ref": "courier_supply",
                       "destination_ref": "station_storage"},
    }[kind]

    def is_exact_lock_row(row):
        return (isinstance(row, Mapping)
                and row.get("actor_alias") == expected_actor
                and row.get("task_kind") == kind
                and all(row.get(ref) == alias for ref, alias in lock_exact_refs.items()))

    matching_lock_indices = [index for index, row in enumerate(sequence)
                             if is_exact_lock_row(row)]
    claims_lock = locked_hash is not None or locked_index is not None
    if matching_lock_indices and not claims_lock:
        raise ValueError("station planner omitted literal locked-task provenance")
    if binding.get("mode") == "locked_fragment" and not matching_lock_indices and not claims_lock:
        # The only supported task outside this exact core is the registered B
        # repair prerequisite in the hard repair-before-storage order. Do not
        # let an unrelated row borrow a locked binding's mode/grant and escape
        # literal-core validation.
        source_row = source_constraint.get("source_constraint") or {}
        before = source_row.get("before") or {}
        after = source_row.get("after") or {}
        registered_store_core = any(
            isinstance(row, Mapping) and row.get("actor_alias") == "A"
            and row.get("task_kind") == "store_item"
            and row.get("item_ref") == "courier_supply"
            and row.get("destination_ref") == "station_storage"
            for row in sequence)
        valid_repair_dependency = (
            kind == "repair_passage" and expected_actor == "B"
            and source_row.get("kind") == "event_order"
            and source_row.get("hard") is True
            and source_row.get("order") == "EVENT_KEY"
            and before.get("event") == "station_passage_repaired"
            and before.get("filters") == {"actor": "B", "tool": "station_tool",
                                           "exit": "pickup_to_side_south"}
            and after.get("event") == "station_supply_stored"
            and after.get("filters") == {"actor": "A", "item": "courier_supply",
                                          "storage": "station_storage"}
            and registered_store_core)
        if not valid_repair_dependency:
            raise ValueError("non-core task is not the registered repair-before-store prerequisite")
    locked_mode = claims_lock
    if locked_mode:
        if binding.get("mode") != "locked_fragment":
            raise ValueError("station planner marked a task locked under a non-locked binding")
        fragment = source_constraint.get("locked_fragment") or {}
        sequence = fragment.get("sequence", [])
        if (locked_hash != fragment.get("sequence_sha256") or type(locked_index) is not int
                or not 0 <= locked_index < len(sequence)):
            raise ValueError("station planner locked task lacks exact sequence provenance")
        if locked_index not in matching_lock_indices:
            raise ValueError("station planner locked task differs from the authored exact sequence")
        source_method = "locked_fragment"
        control_source = "LOCKED_FRAGMENT"
    else:
        source_method = method
        control_source = "AUTHORED" if binding.get("mode") == "direct" else "PLANNER"
    offer_id = (f"{projection.station_id}:{projection.version}:{projection.source_sha256[:12]}:"
                f"{constraint_id}:{source_method}:{expected_actor}:{kind}")
    offer = {"offer_id": offer_id, "source": "AUTHOR",
        "goal_id": constraint_id, "task_kind": kind,
        "item_id": task.get("item_id"), "destination_id": task.get("storage_destination_id"),
        "storage_destination_id": task.get("storage_destination_id"),
        "storage_room_id": task.get("storage_room_id"),
        "target_id": task.get("target_id"), "tool_id": task.get("tool_id"),
        "target_room_id": task.get("target_room_id"),
        "duration_minutes": task.get("duration_minutes"),
        "deadline_minute": task.get("deadline_minute"),
        "planned_start_minute": task.get("planned_start_minute"),
        # Preserve the authored event-window start separately from the
        # dispatch boundary; preparation may begin earlier, but the terminal
        # work effect must respect the exact compiled window.
        "earliest_terminal_minute": task.get("earliest_terminal_minute"),
        "estimated_work_start_minute": task.get("estimated_work_start_minute"),
        "estimated_finish_minute": task.get("estimated_finish_minute"),
        "prerequisites": list(task.get("prerequisites", [])),
        "required_constraint_ids": list(required_ids),
        "constraint_id": constraint_id, "source_method_id": source_method,
        "planned_method_id": method, "control_source": control_source,
        "grant_id": task.get("grant_id"), "projection_id": sealed["projection_id"],
        "actor_alias": expected_actor,
        "item_alias": "courier_supply" if kind in {"inspect_supply", "store_item"} else None,
        "tool_alias": ("station_tool" if kind in {"inspect_supply", "repair_passage"}
                       else None),
        "target_alias": ("pickup_to_side_south" if kind == "repair_passage" else
                         "courier_supply" if kind == "inspect_supply" else None),
        "destination_alias": "station_storage" if kind in {"inspect_supply", "store_item"} else None,
        "locked_fragment_hash": locked_hash,
        "locked_sequence_index": locked_index}
    expected_grant = sealed["grant_ids"].get(constraint_id)
    if offer["grant_id"] != expected_grant or not isinstance(expected_grant, str):
        raise ValueError("station planner omitted the exact native task grant")
    return [offer]


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


def _station_planner_commitments(actor, commitments, receipts, active_tool_lease, *,
                                 tool_id, actor_alias, active_work):
    """Attach only receipt-backed conditional release estimates to planner rows."""
    result = []
    matched_lease = None
    for source in commitments if isinstance(commitments, list) else []:
        if not isinstance(source, Mapping):
            continue
        row = dict(source)
        if row.get("status") in {"ACCEPTED", "IN_PROGRESS"}:
            commitment_id = row.get("commitment_id")
            lease_matches = bool(
                isinstance(active_tool_lease, Mapping)
                and active_tool_lease.get("status") in {"IN_PROGRESS", "BUSY"}
                and type(active_tool_lease.get("actor_id")) is int
                and active_tool_lease.get("actor_id") == getattr(actor, "id", None)
                and active_tool_lease.get("actor_alias") == actor_alias
                and active_tool_lease.get("commitment_id") == commitment_id
                and active_tool_lease.get("task_kind") == row.get("task_kind")
                and type(active_tool_lease.get("due_minute")) is int
                and type(active_tool_lease.get("tool_id", tool_id)) is int
                and active_tool_lease.get("tool_id", tool_id) == tool_id
                and isinstance(active_work, Mapping)
                and active_work.get("commitment_id") == commitment_id
                and active_work.get("actor_id") == getattr(actor, "id", None)
                and active_work.get("task_kind") == row.get("task_kind")
                and active_work.get("tool_id") == tool_id
                and active_work.get("target_id") == row.get("target_id")
                and active_work.get("due_minute") == active_tool_lease.get("due_minute")
                and row.get("tool_id") == tool_id)
            if lease_matches:
                # This is an exact native lease deadline, not a route estimate.
                row["due_minute"] = active_tool_lease["due_minute"]
                row["release_time_basis"] = "matching_actor_commitment_tool_lease"
                matched_lease = {**dict(active_tool_lease), "actor_alias": actor_alias,
                                 "tool_id": tool_id, "target_id": row.get("target_id")}
            elif (row.get("source") == "SELF"
                  and row.get("task_kind") == "routine_route"):
                remaining = _remaining_work_lower_bound(actor, row, receipts)
                if type(remaining) is int:
                    row["remaining_work_minutes"] = remaining
                    row["release_time_basis"] = "conditional_no_future_failure_estimate"
        result.append(row)
    return result, matched_lease


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
    station_work_events = _station_work_typed_events(ledger, rows, actors, service)
    typed_events.extend(station_work_events)
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
            "station_work": _work_snapshot(pickup, rows, actors, service),
            "station_work_receipts": {alias: service._plain_json(service._attr(
                actor, "station_work_receipts", category="native_p5", default=[])) for alias, actor in actors.items()},
            "station_store_receipts": {alias: service._plain_json(service._attr(
                actor, "station_store_receipts", category="native_p5", default=[])) for alias, actor in actors.items()},
            "execution_authority": "shared_P3_actor_callback_and_native_receipts"}


def _work_snapshot(pickup, rows, actors, service):
    content = service._plain_json(service._attr(pickup, "p5_station_content_v1",
                                               category="native_p5", default={}))
    by_id = {int(obj.id): obj for obj in rows}
    tool = by_id.get(content.get("tool_id")) if content else None
    storage = by_id.get(content.get("storage_id")) if content else None
    supply = by_id.get(content.get("supply_id")) if content else None
    exit_obj = by_id.get(content.get("repair_exit_id")) if content else None
    return {"content_version": content.get("version") if content else None,
            "registered_ids": content or None,
            "tool": ({"id": int(tool.id), "room_id": int(tool.location.id) if tool.location else None,
                      "held_by_actor_id": next((int(actor.id) for actor in actors.values()
                                                 if tool in actor.contents), None),
                      "lease": service._plain_json(service._attr(tool, "p5_station_tool_lease", category="native_p5", default={}))}
                     if tool else None),
            "storage": ({"id": int(storage.id), "room_id": int(storage.location.id) if storage.location else None,
                         "stored_item_ids": sorted(int(obj.id) for obj in storage.contents)} if storage else None),
            "supply": ({"id": int(supply.id), "location_id": int(supply.location.id) if supply.location else None,
                        "inspection_status": service._attr(supply, "p5_supply_inspection_status", category="native_p5")}
                       if supply else None),
            "repair_exit": ({"id": int(exit_obj.id), "source_room_id": int(exit_obj.location.id),
                             "destination_room_id": int(exit_obj.destination.id),
                             "key": exit_obj.key,
                             "traversable": bool(exit_obj.access(next(iter(actors.values())), "traverse", default=True))}
                            if exit_obj and actors else None),
            "active_actor_work": {alias: service._plain_json(service._attr(
                actor, "p5_station_work", category="native_p5", default=None)) for alias, actor in actors.items()}}


def _station_work_typed_events(ledger, rows, actors, service):
    by_id = {int(obj.id): obj for obj in rows}
    def entity(entity_type, stable_id, label):
        return {"entity_type": entity_type, "stable_id": str(stable_id), "label": str(label)}
    receipts = []
    for alias, actor in actors.items():
        receipts.extend((alias, row) for row in service._plain_json(service._attr(
            actor, "station_work_receipts", category="native_p5", default=[])))
        receipts.extend((alias, row) for row in service._plain_json(service._attr(
            actor, "station_store_receipts", category="native_p5", default=[])))
        receipts.extend((alias, row) for row in service._plain_json(service._attr(
            actor, "native_receipts", default=[]))
                        if row.get("ongoing_task_kind") in {"lend_tool", "return_tool"})
    raw_by_receipt = {str(row.get("receipt_id")): row for row in ledger
                      if row.get("sealed") is True and row.get("receipt_id")}
    names = {"P5_STATION_SUPPLY_INSPECTED": "p5_station_supply_inspected",
             "P5_STATION_SUPPLY_STORED": "p5_station_supply_stored",
             "P5_STATION_PASSAGE_REPAIRED": "p5_station_passage_repaired",
             "P5_STATION_TOOL_LOANED": "p5_station_tool_loaned",
             "P5_STATION_TOOL_RETURNED": "p5_station_tool_returned"}
    events = []
    for alias, receipt in receipts:
        if receipt.get("settled") is not True or receipt.get("outcome", "SETTLED") != "SETTLED":
            continue
        kind = receipt.get("task_kind", receipt.get("operator"))
        raw_name = ("P5_STATION_SUPPLY_INSPECTED" if kind == "inspect_supply" else
                    "P5_STATION_PASSAGE_REPAIRED" if kind == "repair_passage" else
                    "P5_STATION_SUPPLY_STORED" if kind == "store_item" else
                    "P5_STATION_TOOL_LOANED" if kind == "lend_tool" else
                    "P5_STATION_TOOL_RETURNED" if kind == "return_tool" else None)
        event_name = names.get(raw_name)
        if event_name is None:
            continue
        row = raw_by_receipt.get(str(receipt.get("receipt_id")))
        if (row is None or row.get("event_type") != raw_name
                or row.get("event_id") != (f"station:{receipt.get('receipt_id')}"
                                             if kind in {"lend_tool", "return_tool"}
                                             else receipt.get("receipt_id"))
                or row.get("receipt_id") != receipt.get("receipt_id")):
            continue
        raw_args = row.get("typed_args", {})
        receipt_minute = receipt.get("completed_minute", receipt.get("sim_minute"))
        raw_commitment_id = raw_args.get("commitment_id", raw_args.get("ongoing_commitment_id"))
        receipt_commitment_id = receipt.get("commitment_id", receipt.get("ongoing_commitment_id"))
        if (raw_args.get("receipt_id") != receipt.get("receipt_id")
                or raw_commitment_id != receipt_commitment_id):
            continue
        if kind not in {"lend_tool", "return_tool"} and raw_args.get("actor_alias") != alias:
            continue
        if (type(receipt_minute) is not int or type(row.get("minute")) is not int
                or row.get("minute") != receipt_minute):
            continue
        if kind in {"lend_tool", "return_tool"}:
            if (raw_args.get("tool_id") != receipt.get("item_id")
                    or receipt.get("kind") != "give"
                    or raw_args.get("returned_minute", receipt_minute) != receipt_minute
                    or raw_args.get("outcome") not in ({"SETTLED"} if kind == "lend_tool"
                                                       else {"ON_TIME", "LATE"})):
                continue
        elif (raw_args.get("outcome") != "SETTLED"
              or raw_args.get("target_id") != receipt.get("target_id")
              or raw_args.get("item_id") != receipt.get("item_id")
              or raw_args.get("tool_id") != receipt.get("tool_id")
              or raw_args.get("actor_id") != receipt.get("actor_id")
              or raw_args.get("actor_alias") != receipt.get("actor_alias")):
            continue
        actor_entity = entity("Actor", alias, alias)
        args = {"actor": actor_entity}
        if event_name == "p5_station_supply_inspected":
            item = by_id.get(receipt.get("item_id"))
            tool = by_id.get(receipt.get("tool_id"))
            if (item is None or tool is None or receipt.get("actor_alias") != alias
                    or receipt.get("effect", {}).get("after_status") != "APPROVED"):
                continue
            args.update({"item": entity("Item", item.id, item.key),
                         "tool": entity("Item", tool.id, tool.key)})
        elif event_name == "p5_station_passage_repaired":
            tool = by_id.get(receipt.get("tool_id"))
            exit_obj = by_id.get(receipt.get("target_id"))
            if (tool is None or exit_obj is None or receipt.get("actor_alias") != alias
                    or receipt.get("effect", {}).get("after_traversable") is not True):
                continue
            args.update({"tool": entity("Item", tool.id, tool.key),
                         "exit": entity("Exit", exit_obj.id, exit_obj.key)})
        elif event_name == "p5_station_supply_stored":
            item = by_id.get(receipt.get("item_id"))
            storage = by_id.get(receipt.get("storage_id"))
            if (item is None or storage is None or receipt.get("actor_alias") != alias
                    or receipt.get("after_container_id") != int(storage.id)
                    or receipt.get("tool_id") is None):
                continue
            args.update({"item": entity("Item", item.id, item.key),
                         "storage": entity("Item", storage.id, storage.key)})
        else:
            tool = by_id.get(receipt.get("item_id"))
            if (tool is None or not service._attr(tool, "p5_station_tool", category="native_p5")
                    or receipt.get("kind") != "give"
                    or receipt.get("item_id") != int(tool.id)):
                continue
            recipient_alias = next((peer for peer, peer_obj in actors.items()
                                    if int(peer_obj.id) == int(receipt.get("recipient_id", -1))), None)
            commitment_id = receipt.get("ongoing_commitment_id")
            commitment = next((item for item in service._plain_json(service._attr(
                actors[alias], "ongoing_commitments", category="native_p5", default=[]))
                               if item.get("commitment_id") == commitment_id), None)
            if commitment is None or recipient_alias is None:
                continue
            due = commitment.get("due_minute")
            if (type(due) is not int or not isinstance(raw_args.get("loan_id"), str)
                    or raw_args.get("loan_id") == ""):
                continue
            if event_name == "p5_station_tool_loaned":
                if kind != "lend_tool":
                    continue
                args = {"lender": entity("Actor", alias, alias),
                        "borrower": entity("Actor", recipient_alias, recipient_alias),
                        "tool": entity("Item", tool.id, tool.key),
                        "due_minute": due, "loan_id": raw_args.get("loan_id")}
            else:
                if kind != "return_tool" or not isinstance(raw_args.get("outcome"), str):
                    continue
                args = {"lender": entity("Actor", recipient_alias, recipient_alias),
                        "borrower": entity("Actor", alias, alias),
                        "tool": entity("Item", tool.id, tool.key),
                        "due_minute": due, "returned_minute": int(row["minute"]),
                        "outcome": raw_args["outcome"], "loan_id": raw_args.get("loan_id")}
        events.append({"event_id": row["event_id"], "event_type": event_name, "version": "1",
                       "provenance": "committed_ledger", "time": int(row["minute"]),
                       "sequence": int(row["sequence"]), "args": args,
                       "native_commitment_id": receipt.get("commitment_id"),
                       "native_receipt_id": receipt.get("receipt_id"),
                       "native_task_kind": kind})
    return events


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
        station_profile = native.profile_for(pickup)
        if station_profile is not None and getattr(station_profile, "game_content", None) == "station_work_v1":
            entities = _station_entities(rows)
            if note_obj is not None:
                entities["note"] = StableEntity("Item", str(note_id), str(note_obj.key))
        bundle = load_bundle(service._plain_json(raw_author["bundle"]),
                             registry=story_event_registry(game_content=(getattr(station_profile, "game_content", None)
                                                                        if station_profile else None)),
                             entities=entities)
        trace = Trace(now=Fraction(now))
        for row in sorted(typed_events, key=lambda item: (item["time"], item["sequence"])):
            args = {key: StableEntity(value["entity_type"], value["stable_id"], value.get("label", ""))
                    if isinstance(value, Mapping) and set(value) >= {"entity_type", "stable_id"} else value
                    for key, value in row["args"].items()}
            trace.add_event(Event(row["event_id"], row["event_type"], Fraction(row["time"]),
                                  int(row["sequence"]), args, row["version"], row["provenance"]))
        trace.seal_events_through(Fraction(now))
        return evaluate_bundle(bundle, trace, registry=story_event_registry(
            game_content=(getattr(station_profile, "game_content", None) if station_profile else None)))
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
    profile = native.profile_for(pickup)
    if profile is not None and getattr(profile, "game_content", None) == "station_work_v1":
        entities = _station_entities(rows)
    if note is not None:
        from tools.native_platform_v0.p5.bundle import DEFAULT_ENTITIES
        from tools.trajectory_constraints_v0.types import StableEntity
        entities = dict(entities or DEFAULT_ENTITIES)
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
    profile = native.profile_for(pickup)
    if profile is not None and getattr(profile, "game_content", None) == "station_work_v1":
        entities = _station_entities(rows)
    if note is not None:
        from tools.native_platform_v0.p5.bundle import DEFAULT_ENTITIES
        from tools.trajectory_constraints_v0.types import StableEntity
        entities = dict(entities or DEFAULT_ENTITIES)
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
