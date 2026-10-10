"""Narrow P5 orchestration over Evennia W, actor callbacks, and TypedIR.

Only generated P5 scenes are accepted. The director can propose one registered
route opportunity; the world adapter rechecks its active bundle permission and
the physical budget before changing a native exit lock.
"""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
from copy import deepcopy
from functools import wraps
from types import SimpleNamespace

from .bundle import BundleError, BundleStore, load_bundle
from .monitor import evaluate_bundle
from .planning import NO_OP, plan
from . import world


SOCIAL_PRESETS = {"native_default_reject_v0", "hero_intelligence_30_v0"}
MAX_HORIZON = 24


def _inline_callbacks(function):
    """Delay the Twisted import until a native-server operation is invoked."""
    @wraps(function)
    def wrapped(*args, **kwargs):
        from twisted.internet import defer
        return defer.inlineCallbacks(function)(*args, **kwargs)
    return wrapped


def _attr(obj, key, default=None, category="native_p3"):
    return obj.attributes.get(key, category=category, default=default)


def _set(obj, key, value, category="native_p5"):
    obj.attributes.add(key, value, category=category)


def _entities():
    from .bundle import DEFAULT_ENTITIES
    return dict(DEFAULT_ENTITIES)


def _scene_objects(scene_id):
    return world.scene_objects(scene_id)


def _bundle_for(pickup):
    raw = _attr(pickup, "p5_active_bundle", category="native_p5")
    entities = _attr(pickup, "p5_entities", category="native_p5")
    if not isinstance(raw, Mapping) or not isinstance(entities, Mapping):
        raise ValueError("P5 scene lacks its active author bundle or entity catalog")
    # Evennia persists nested attributes as _SaverDict/_SaverList. Normalize
    # recursively without relaxing the strict JSON loader's type checks.
    return load_bundle(_plain_json(raw), entities=_plain_json(entities))


def _stable_entities():
    return {alias: {"entity_type": value.entity_type, "stable_id": value.stable_id,
                    "display_name": value.display_name}
            for alias, value in _entities().items()}


def _plain_json(value):
    if isinstance(value, Mapping):
        return {str(key): _plain_json(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_plain_json(item) for item in value]
    return value


def _current_verdicts(scene_id, bundle, *, through_minute=None):
    trace = world.build_typed_trace(scene_id, bundle, _entities(), through_minute=through_minute)
    return evaluate_bundle(bundle, trace), trace


def _pending_identity(actor):
    pending = _attr(actor, "pending_action")
    if not isinstance(pending, Mapping):
        return None
    # Preserve the complete pending record (including operation_id,
    # planned_at_tick, and full intent). This records identity, not a claim of
    # durable multi-tick execution progress.
    return _plain_json(deepcopy(pending))


def _ledger_prefix(pickup, before_minute):
    rows = list(_attr(pickup, "p4_ledger", default=[]))
    # Full JSON rows make prefix equality sensitive to typed_args/provenance
    # edits, not merely event headers.
    return [_plain_json(deepcopy(row)) for row in rows
            if int(row.get("minute", -1)) < before_minute]


def reset_p5_scenario(*, owner, bundle, initial_social_preset="native_default_reject_v0",
                      horizon=24, seed=0, director_enabled=True, shared_supply=False,
                      initial_main_open=True):
    """Create a fresh P5 scene without reusing or overwriting any generated objects."""
    if initial_social_preset not in SOCIAL_PRESETS:
        raise ValueError("initial_social_preset is not a registered native preset")
    if type(horizon) is not int or not 1 <= horizon <= MAX_HORIZON:
        raise ValueError("P5 horizon must be an integer in [1,24]")
    if type(seed) is not int or not 0 <= seed <= 2**31 - 1:
        raise ValueError("P5 seed must be an integer in [0,2147483647]")
    if type(director_enabled) is not bool or type(shared_supply) is not bool or type(initial_main_open) is not bool:
        raise ValueError("P5 director, shared_supply, and initial_main_open must be booleans")
    entities = _stable_entities()
    try:
        # Validate external author input before importing Evennia factories or
        # creating any world objects, while preserving the public error code.
        active = load_bundle(bundle, entities=entities)
    except BundleError as exc:
        return {"ok": False, "scene_created": False,
                "error": {"code": exc.code, "details": dict(exc.details)}}
    from evennia import create_object
    from typeclasses.characters import Character
    from typeclasses.exits import Exit
    from typeclasses.rooms import Room
    from tools.native_platform_v0.p3.scene import create_scene

    scene = create_scene(SimpleNamespace(account=owner), mode="b", seed=seed, drive_mode="manual",
                         interval=4, activity_profile="p4_story_v0", delivery_task=True,
                         p4_east_closed=not initial_main_open, p4_deadline=24)
    scene_id = scene["scene_id"]
    pickup, destination = scene["pickup"], scene["destination"]
    p4_clock = dict(_attr(pickup, "p4_clock"))
    p4_clock["deadline"] = horizon
    pickup.attributes.add("p4_clock", p4_clock, category="native_p3")
    actors = {"A": scene["courier"], "B": scene["resident"]}
    player = create_object(Character, key=f"P5 Fixture Player {scene_id}", location=pickup,
                           attributes=[("p3_scene_id", scene_id, "native_p3"),
                                       ("p3_control_role", "player", "native_p3"),
                                       ("owner_account_id", owner.id, "native_p3"),
                                       ("drive_mode", "manual", "native_p3"),
                                       ("log", [], "native_p3"),
                                       ("native_receipts", [], "native_p3")])
    side = create_object(Room, key=f"P5 Side Room {scene_id}",
                         attributes=[("p3_scene_id", scene_id, "native_p3")])
    # The direct route is inherited from the P4 fixture; P5 adds a second,
    # longer physical route through this generated third room.
    side_in = create_object(Exit, key="south", location=pickup, destination=side,
                            locks="traverse:false()",
                            attributes=[("p3_scene_id", scene_id, "native_p3"),
                                        ("p5_route_id", "side_passage", "native_p5")])
    side_back = create_object(Exit, key="north", location=side, destination=pickup,
                              locks="traverse:false()",
                              attributes=[("p3_scene_id", scene_id, "native_p3"),
                                          ("p5_route_id", "side_passage", "native_p5")])
    side_to_dest = create_object(Exit, key="east", location=side, destination=destination,
                                 locks="traverse:false()",
                                 attributes=[("p3_scene_id", scene_id, "native_p3"),
                                             ("p5_route_id", "side_passage", "native_p5")])
    dest_to_side = create_object(Exit, key="south", location=destination, destination=side,
                                 locks="traverse:false()",
                                 attributes=[("p3_scene_id", scene_id, "native_p3"),
                                             ("p5_route_id", "side_passage", "native_p5")])
    main_edges = [edge for room in (pickup, destination) for edge in room.exits
                  if edge.key in ("east", "west") and edge.destination in (pickup, destination)
                  and _attr(edge, "p3_scene_id") == scene_id]
    for edge in main_edges:
        _set(edge, "p5_route_id", "main_passage")
    items = {"courier_supply": scene["supply"], "resident_parcel": scene["return_parcel"]}
    if shared_supply:
        # Both delivery contracts now reference one actual object. The fixture's
        # resident parcel remains an unrelated generated object and is excluded
        # from either task binding.
        item = scene["supply"]
        actors["B"].attributes.add("task_item_id", item.id, category="native_p3")
        actors["B"].attributes.add("task_item_key", item.key, category="native_p3")
        actors["B"].attributes.add("task_item_dbref", item.dbref, category="native_p3")
        actors["B"].attributes.add("p3_role", "assigned_supply", category="native_p3")
        _set(item, "p5_item_alias", "courier_supply")
        _set(scene["return_parcel"], "p5_item_alias", "resident_parcel")
    else:
        _set(scene["supply"], "p5_item_alias", "courier_supply")
        _set(scene["return_parcel"], "p5_item_alias", "resident_parcel")
    _set(pickup, "p5_scene_id", scene_id, category="native_p3")
    _set(pickup, "p5_side_room_id", int(side.id))
    _set(pickup, "p5_active_bundle", _plain_json(active.raw))
    _set(pickup, "p5_entities", entities)
    _set(pickup, "p5_bundle_archive", [])
    _set(pickup, "p5_spent_cost", 0)
    _set(pickup, "p5_opportunities_used", 0)
    _set(pickup, "p5_event_coverage_minute", 0)
    _set(pickup, "p5_snapshot_coverage_minute", 0)
    _set(pickup, "p5_completed_minutes", [0])
    _set(pickup, "p5_director_enabled", director_enabled)
    _set(pickup, "p5_horizon", horizon)
    _set(pickup, "p5_shared_supply", shared_supply)
    for room in (pickup, destination, side):
        _set(room, "p5_scene_id", scene_id)
    for edge in main_edges:
        _set(edge, "p5_route_id", "main_passage")
    for edge in (side_in, side_back, side_to_dest, dest_to_side):
        _set(edge, "p5_route_id", "side_passage")
    for alias, actor in actors.items():
        actor.attributes.add("activity_profile", "p5_story_v0", category="native_p3")
        _set(actor, "p5_actor_alias", alias)
        _set(actor, "p5_task_item_alias", "courier_supply" if alias == "A" else
             ("courier_supply" if shared_supply else "resident_parcel"))
        _set(actor, "p5_native_social_preset", initial_social_preset, category="native_p3")
        _set(actor, "p5_social_target_alias", "B" if alias == "A" else "A")
        _set(actor, "p5_delivery_task", True)
    _set(scene["supply"], "p5_item_alias", "courier_supply")
    _set(scene["return_parcel"], "p5_item_alias", "resident_parcel")
    _set(pickup, "p5_world_snapshots", [])
    world.capture_snapshot(scene_id, 0)
    # Mark initial time as a complete, immutable snapshot, not as actor evidence.
    _set(pickup, "p5_snapshot_coverage_minute", 0)
    return {"scene_id": scene_id, "seed": seed, "horizon": horizon, "now": 0,
            "preset": initial_social_preset, "director_enabled": director_enabled,
            "shared_supply": shared_supply,
            "rooms": {"origin": int(pickup.id), "destination": int(destination.id), "side": int(side.id)},
            "actors": {alias: {"id": int(actor.id), "dbref": str(actor.dbref)}
                       for alias, actor in actors.items()},
            "player": {"id": int(player.id), "dbref": str(player.dbref)},
            "items": {alias: {"id": int(item.id), "dbref": str(item.dbref)}
                      for alias, item in items.items() if item is not None},
            "active_bundle": {"bundle_id": active.bundle_id, "version": active.version},
            "pending_actions": {alias: None for alias in actors}}


def edit_author_bundle(scene_id, raw_bundle, expected_version):
    pickup, rows = _scene_objects(scene_id)
    active = _bundle_for(pickup)
    before = {str(_attr(obj, "p5_actor_alias", category="native_p5")): _pending_identity(obj)
              for obj in rows if _attr(obj, "activity_profile") == world.PROFILE}
    before_verdicts, _ = _current_verdicts(scene_id, active)
    completed = {row["constraint_id"] for row in before_verdicts["constraints"]
                 if row["status"] == "SATISFIED"}
    evidence = {row["constraint_id"] for row in before_verdicts["constraints"]
                if row.get("witness") is not None}
    now = int(_attr(pickup, "p4_clock")["now"])
    prior_prefix = _ledger_prefix(pickup, now)
    store = BundleStore(active, entities=_entities())
    try:
        candidate = store.replace(raw_bundle, expected_version, now=now,
                                  completed_constraint_ids=completed,
                                  evidence_constraint_ids=evidence)
    except BundleError as exc:
        return {"ok": False, "error": {"code": exc.code, "message": str(exc),
                                        "details": exc.details},
                "active_bundle": {"bundle_id": active.bundle_id, "version": active.version},
                "now": now,
                "ledger_prefix_before": deepcopy(prior_prefix),
                "ledger_prefix_after": deepcopy(_ledger_prefix(pickup, now)),
                "prefix_event_ids_before": [row["event_id"] for row in prior_prefix],
                "prefix_event_ids_after": [row["event_id"] for row in _ledger_prefix(pickup, now)],
                "historical_prefix_preserved": prior_prefix == _ledger_prefix(pickup, now),
                "pending_actions_before": before,
                "pending_actions_after": {str(_attr(obj, "p5_actor_alias", category="native_p5")): _pending_identity(obj)
                                           for obj in rows if _attr(obj, "activity_profile") == world.PROFILE},
                "pending_identity_preserved": before == {
                    str(_attr(obj, "p5_actor_alias", category="native_p5")): _pending_identity(obj)
                    for obj in rows if _attr(obj, "activity_profile") == world.PROFILE}}
    archive = list(_attr(pickup, "p5_bundle_archive", category="native_p5", default=[]))
    archive.append({"bundle_id": active.bundle_id, "version": active.version,
                    "now": now, "verdicts": before_verdicts})
    _set(pickup, "p5_bundle_archive", archive)
    _set(pickup, "p5_active_bundle", _plain_json(candidate.raw))
    later_prefix = _ledger_prefix(pickup, now)
    after = {str(_attr(obj, "p5_actor_alias", category="native_p5")): _pending_identity(obj)
             for obj in rows if _attr(obj, "activity_profile") == world.PROFILE}
    return {"ok": True, "active_bundle": {"bundle_id": candidate.bundle_id,
                                             "version": candidate.version},
            "now": now, "archive": {"prior_version": active.version,
                                     "prior_verdicts": before_verdicts},
            "ledger_prefix_before": deepcopy(prior_prefix),
            "ledger_prefix_after": deepcopy(later_prefix),
            "prefix_event_ids_before": [row["event_id"] for row in prior_prefix],
            "prefix_event_ids_after": [row["event_id"] for row in later_prefix],
            "historical_prefix_preserved": prior_prefix == later_prefix,
            "pending_actions_before": before, "pending_actions_after": after,
            "pending_identity_preserved": before == after}


def _director(scene_id, bundle, *, enabled):
    from tools.native_platform_v0.p3.p4_world import append_event, clock_for_actor

    pickup, rows = _scene_objects(scene_id)
    actors = {str(_attr(obj, "p5_actor_alias", category="native_p5")): obj
              for obj in rows if _attr(obj, "activity_profile") == world.PROFILE}
    clock = clock_for_actor(actors["A"])
    # The current round has advanced the server clock but its two actor
    # callbacks have not yet completed. Decisions use only the previous sealed
    # prefix, never a fabricated observation at this minute.
    trace_result, trace = _current_verdicts(scene_id, bundle,
                                            through_minute=max(0, int(clock["now"]) - 1))
    state = {"now": int(clock["now"]), "horizon": int(_attr(pickup, "p5_horizon", category="native_p5")),
             "routes": world.route_rows(scene_id, actors["A"], bundle),
             "spent_cost": int(_attr(pickup, "p5_spent_cost", category="native_p5", default=0)),
             "opportunities_used": int(_attr(pickup, "p5_opportunities_used", category="native_p5", default=0)),
             "verdicts": [{"constraint_id": row["constraint_id"], "status": row["status"]}
                          for row in trace_result["constraints"]],
             "physical_budget": 2}
    proposal = plan(bundle, state)
    action = proposal["selected_action"] if enabled else NO_OP
    director_id = f"p5:{_attr(pickup, 'scenario_seed', default=0)}:{clock['now']}:director:v{bundle.version}"
    append_event(scene_id, {"event_type": "P5_DIRECTOR_DECISION", "event_id": director_id,
                            "typed_args": {"bundle_id": bundle.bundle_id, "bundle_version": bundle.version,
                                           "enabled": enabled, "selected_action": action,
                                           "plan": proposal}, "sealed": True})
    settlement = None
    if action != NO_OP:
        settlement = world.activate_opportunity(scene_id, actors["A"], action, bundle,
                                                expected_version=bundle.version)
        append_event(scene_id, {"event_type": "P5_OPPORTUNITY_ATTEMPT",
                                "event_id": f"{director_id}:world",
                                "typed_args": settlement, "sealed": True,
                                "receipt_id": settlement.get("receipt_id")})
    return {"plan": proposal, "selected_action": action, "settlement": settlement,
            "bundle_version": bundle.version, "authorized_view": state}


def _snapshot_actor(actor):
    return {"actor_alias": _attr(actor, "p5_actor_alias", category="native_p5"),
            "actor_id": int(actor.id), "room_id": int(actor.location.id) if actor.location else None,
            "inventory_ids": sorted(int(obj.id) for obj in actor.contents),
            "task_item_id": _attr(actor, "task_item_id"),
            "task_destination_id": _attr(actor, "task_destination_id"),
            "status": _attr(actor, "status"), "pending_action": deepcopy(_attr(actor, "pending_action")),
            "native_receipts": list(_attr(actor, "native_receipts", default=[])),
            "log": list(_attr(actor, "log", default=[]))}


def _complete_minute(scene_id, minute):
    pickup, rows = _scene_objects(scene_id)
    from tools.native_platform_v0.p3.p4_world import append_event

    aliases = {str(_attr(obj, "p5_actor_alias", category="native_p5")): obj
               for obj in rows if _attr(obj, "activity_profile") == world.PROFILE}
    if set(aliases) != {"A", "B"}:
        raise ValueError("P5 minute cannot complete without both actor callbacks")
    snapshots = world.capture_snapshot(scene_id, minute)
    callback_event_ids = [f"p5:{_attr(pickup, 'scenario_seed', default=0)}:{alias}:{minute}:callback"
                          for alias in ("A", "B")]
    for alias, actor in aliases.items():
        callback_id = f"p5:{_attr(pickup, 'scenario_seed', default=0)}:{alias}:{minute}:callback"
        append_event(scene_id, {"event_type": "P5_NPC_CALLBACK", "event_id": callback_id,
                                "typed_args": {"actor_alias": alias, "actor_id": int(actor.id),
                                               "room_id_after": int(actor.location.id) if actor.location else None,
                                               "receipts_after": len(_attr(actor, "native_receipts", default=[]))},
                                "sealed": True})
    snapshot_event_id = f"p5:{_attr(pickup, 'scenario_seed', default=0)}:{minute}:snapshot"
    append_event(scene_id, {"event_type": "P5_WORLD_SNAPSHOT", "event_id": snapshot_event_id,
                            "typed_args": {"minute": minute, "callback_event_ids": callback_event_ids,
                                           "snapshot": snapshots}, "sealed": True})
    completed = list(_attr(pickup, "p5_completed_minutes", category="native_p5", default=[]))
    if minute != (max(completed) + 1 if completed else 0):
        raise ValueError("P5 completed-minute frontier must advance consecutively")
    completed.append(minute)
    _set(pickup, "p5_completed_minutes", completed)
    _set(pickup, "p5_snapshot_coverage_minute", minute)
    ledger = list(_attr(pickup, "p4_ledger", default=[]))
    unsealed = [row.get("event_id") for row in ledger
                if int(row.get("minute", -1)) == minute and row.get("sealed") is not True]
    if not unsealed:
        _set(pickup, "p5_event_coverage_minute", minute)
    event_frontier = int(_attr(pickup, "p5_event_coverage_minute", category="native_p5", default=0))
    return {"minute": minute, "completed": True, "event_complete": not unsealed,
            "unsealed_event_ids": unsealed, "snapshot": snapshots,
            "callback_event_ids": callback_event_ids,
            "trace_frontier": {"events_through": event_frontier, "values_through": minute}}


@_inline_callbacks
def _apply_intervention(scene_id, row, bundle):
    from twisted.internet import defer
    if not isinstance(row, Mapping):
        raise ValueError("P5 intervention row must be an object")
    if row.get("kind") == "author_opportunity":
        if set(row) != {"at", "kind", "operation", "opportunity_id"}:
            raise ValueError("author intervention rows require at/kind/operation/opportunity_id")
        action = row["opportunity_id"]
        if row["operation"] != "open_passage" or action not in world.ROUTE_ACTIONS:
            raise ValueError("unsupported P5 author intervention or route action")
        actor = next(obj for obj in _scene_objects(scene_id)[1]
                     if _attr(obj, "p5_actor_alias", category="native_p5") == "A")
        result = world.activate_opportunity(scene_id, actor, action, bundle,
                                           expected_version=bundle.version)
        provenance = "author_opportunity"
        command_receipt = None
    elif row.get("kind") == "player_command":
        if set(row) != {"at", "kind", "operation", "item_alias"}:
            raise ValueError("player interventions require at/kind/operation/item_alias")
        operation, item_alias = row["operation"], row["item_alias"]
        if operation not in {"get", "drop"} or item_alias not in {"courier_supply", "resident_parcel"}:
            raise ValueError("P5 player intervention supports only get/drop of a named generated item")
        _, rows = _scene_objects(scene_id)
        player = next((obj for obj in rows if _attr(obj, "p3_control_role") == "player"), None)
        item = next((obj for obj in rows if _attr(obj, "p5_item_alias", category="native_p5") == item_alias), None)
        if player is None or item is None:
            raise ValueError("P5 generated player or intervention item is missing")
        command = f"{operation} {item.key}"
        before_location = int(item.location.id) if item.location else None
        before_inventory = [int(obj.id) for obj in player.contents]
        yield defer.maybeDeferred(player.execute_cmd, command)
        after_location = int(item.location.id) if item.location else None
        after_inventory = [int(obj.id) for obj in player.contents]
        settled = (item in player.contents if operation == "get" else
                   item.location and player.location and item.location.id == player.location.id
                   and item not in player.contents)
        command_receipt = {"actor_id": int(player.id), "actor_alias": "player",
                           "operation": operation, "submitted_command": command,
                           "item_id": int(item.id), "before_location_id": before_location,
                           "after_location_id": after_location,
                           "before_inventory_ids": before_inventory,
                           "after_inventory_ids": after_inventory, "settled": bool(settled),
                           "provenance": "native_player_command"}
        result = {"settled": bool(settled), "status": "SETTLED" if settled else "WORLD_VALIDATION_REJECTED",
                  "receipt": command_receipt}
        provenance = "player_native_command"
    else:
        raise ValueError("unknown P5 intervention kind")
    pickup, _ = _scene_objects(scene_id)
    from tools.native_platform_v0.p3.p4_world import append_event
    append_event(scene_id, {"event_type": "P5_INTERVENTION",
                            "event_id": f"p5:{_attr(pickup, 'scenario_seed', default=0)}:{row['at']}:intervention:{provenance}",
                            "typed_args": {"kind": provenance, "intervention": dict(row),
                                           "settlement": result, "command_receipt": command_receipt,
                                           "bundle_version": bundle.version}, "sealed": True})
    defer.returnValue(result)


def _round_deferred(scene_id, intervention=None, edit=None):
    from twisted.internet import defer

    @defer.inlineCallbacks
    def execute():
        from tools.native_platform_v0.p3.p4_world import advance_clock, append_event
        from tools.native_platform_v0.p5.agency import step_actor
        from twisted.internet import defer as d

        pickup, rows = _scene_objects(scene_id)
        clock = advance_clock(scene_id)
        minute = int(clock["now"])
        edit_result = None
        if edit is not None:
            if not isinstance(edit, Mapping) or set(edit) != {"at", "raw_bundle", "expected_version"}:
                raise ValueError("P5 edit rows require exactly at/raw_bundle/expected_version")
            edit_result = edit_author_bundle(scene_id, edit["raw_bundle"], edit["expected_version"])
            append_event(scene_id, {"event_type": "P5_AUTHOR_EDIT_ATTEMPT",
                                    "event_id": f"p5:{_attr(pickup, 'scenario_seed', default=0)}:{minute}:edit:{edit['expected_version']}",
                                    "typed_args": {"expected_version": edit["expected_version"],
                                                   "result": edit_result}, "sealed": True})
        bundle = _bundle_for(pickup)
        intervention_result = (yield _apply_intervention(scene_id, intervention, bundle)
                               if intervention is not None else None)
        enabled = _attr(pickup, "p5_director_enabled", category="native_p5") is True
        director = _director(scene_id, bundle, enabled=enabled)
        actors = {str(_attr(obj, "p5_actor_alias", category="native_p5")): obj
                  for obj in rows if _attr(obj, "activity_profile") == world.PROFILE}
        actor_rows = []
        for alias in ("A", "B"):
            actor = actors[alias]
            log_before = list(_attr(actor, "log", default=[]))
            receipt_before = list(_attr(actor, "native_receipts", default=[]))
            callback_result = yield d.maybeDeferred(step_actor, actor)
            log_after = list(_attr(actor, "log", default=[]))
            receipt_after = list(_attr(actor, "native_receipts", default=[]))
            actor_rows.append({"actor_alias": alias, "callback_result_type": type(callback_result).__name__,
                               "local_decisions": log_after[len(log_before):],
                               "native_receipts": receipt_after[len(receipt_before):],
                               "snapshot": _snapshot_actor(actor)})
        completed = _complete_minute(scene_id, minute)
        bundle = _bundle_for(pickup)
        verdicts, trace = _current_verdicts(scene_id, bundle)
        defer.returnValue({"minute": minute, "edits": [edit_result] if edit_result else [],
                           "interventions": [] if intervention_result is None else [intervention_result],
                           "director": director, "actor_steps": actor_rows,
                           "snapshot": completed["snapshot"], "minute_complete": True,
                           "event_complete": completed["event_complete"],
                           "unsealed_event_ids": completed["unsealed_event_ids"],
                           "trace_frontier": completed["trace_frontier"],
                           "verdicts": verdicts, "typed_trace": world.serialize_typed_trace(trace)})
    return execute()


def _evidence(scene_id, bundle):
    pickup, rows = _scene_objects(scene_id)
    verdicts, trace = _current_verdicts(scene_id, bundle)
    actors = [obj for obj in rows if _attr(obj, "activity_profile") == world.PROFILE]
    now = int(_attr(pickup, "p4_clock")["now"])
    frontier = min(int(_attr(pickup, "p5_event_coverage_minute", category="native_p5", default=0)),
                   int(_attr(pickup, "p5_snapshot_coverage_minute", category="native_p5", default=0)))
    reasons = []
    if now != int(_attr(pickup, "p5_horizon", category="native_p5")):
        reasons.append("horizon_not_reached")
    if frontier < int(_attr(pickup, "p5_horizon", category="native_p5")):
        reasons.append("sealed_prefix_short_of_horizon")
    for actor in actors:
        alias = _attr(actor, "p5_actor_alias", category="native_p5")
        if _attr(actor, "status") == "ERROR":
            reasons.append(f"actor_{alias}_error")
        pending = _attr(actor, "pending_action")
        if isinstance(pending, Mapping) and pending.get("status") == "executing":
            reasons.append(f"actor_{alias}_execution_in_doubt")
        if _attr(actor, "p4_social_status") in {"UNAVAILABLE", "SOCIAL_SETTLEMENT_PENDING",
                                                 "WORLD_SETTLEMENT_PENDING", "UNSUPPORTED_NATIVE_ACTION",
                                                 "STALE_NATIVE_PROPOSAL", "WORLD_VALIDATION_REJECTED"}:
            reasons.append(f"actor_{alias}_social_{_attr(actor, 'p4_social_status')}")
    return {"scene_id": scene_id, "now": now,
            "complete_through": {"events": int(_attr(pickup, "p5_event_coverage_minute", category="native_p5", default=0)),
                                  "values": int(_attr(pickup, "p5_snapshot_coverage_minute", category="native_p5", default=0))},
            "run_status": "COMPLETE" if not reasons else "INCOMPLETE",
            "incomplete_reasons": reasons,
            "pending_future_nonexecuted": {
                _attr(actor, "p5_actor_alias", category="native_p5"): _pending_identity(actor)
                for actor in actors if isinstance(_attr(actor, "pending_action"), Mapping)
                and _attr(actor, "pending_action").get("status") == "planned"},
            "controller_authored_npc_commands": 0,
            "verdicts": verdicts, "typed_trace": world.serialize_typed_trace(trace),
            "ledger": list(_attr(pickup, "p4_ledger", default=[])),
            "world_snapshots": list(_attr(pickup, "p5_world_snapshots", category="native_p5", default=[])),
            "actor_evidence": [_snapshot_actor(obj) for obj in rows
                               if _attr(obj, "activity_profile") == world.PROFILE]}


def get_trace(scene_id):
    pickup, _ = _scene_objects(scene_id)
    return _evidence(scene_id, _bundle_for(pickup))


def step_world(scene_id, rounds=1, *, interventions=(), edits=()):
    from twisted.internet import defer

    if type(rounds) is not int or not 1 <= rounds <= 50:
        raise ValueError("P5 rounds must be an integer in [1,50]")
    interventions = list(interventions)
    edits = list(edits)
    @defer.inlineCallbacks
    def execute():
        results = []
        for _ in range(rounds):
            pickup, _rows = _scene_objects(scene_id)
            now = int(_attr(pickup, "p4_clock")["now"])
            horizon = int(_attr(pickup, "p5_horizon", category="native_p5"))
            if now >= horizon:
                raise ValueError("P5 scenario has reached its authored horizon")
            next_minute = now + 1
            edit_rows = [row for row in edits if row.get("at") == next_minute]
            intervention_rows = [row for row in interventions if row.get("at") == next_minute]
            if len(edit_rows) > 1 or len(intervention_rows) > 1:
                raise ValueError("at most one P5 bundle edit and intervention may occur per minute")
            row = yield _round_deferred(scene_id,
                                        intervention_rows[0] if intervention_rows else None,
                                        edit_rows[0] if edit_rows else None)
            results.append(row)
        pickup, _rows = _scene_objects(scene_id)
        active = _bundle_for(pickup)
        defer.returnValue({"scene_id": scene_id, "rounds": results, "final": _evidence(scene_id, active),
                           "incomplete_reason": None})
    return execute()


def run_p5_scenario(*, owner, bundle, initial_social_preset, horizon, interventions=(), edits=(),
                    director_enabled=True, seed=0, shared_supply=False, initial_main_open=True):
    from twisted.internet import defer

    created = reset_p5_scenario(owner=owner, bundle=bundle,
                                initial_social_preset=initial_social_preset, horizon=horizon,
                                seed=seed, director_enabled=director_enabled,
                                shared_supply=shared_supply, initial_main_open=initial_main_open)
    if isinstance(created, Mapping) and created.get("ok") is False:
        return dict(created)
    @defer.inlineCallbacks
    def execute():
        run = yield step_world(created["scene_id"], rounds=horizon,
                               interventions=interventions, edits=edits)
        defer.returnValue({"ok": True, "scene": created, **run,
                           "run_status": run["final"]["run_status"],
                           "controller_authored_npc_commands": 0})
    return execute()


__all__ = ["reset_p5_scenario", "edit_author_bundle", "step_world", "get_trace", "run_p5_scenario"]
