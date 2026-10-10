"""P5-only world adapters over generated Evennia scenes and the P4 ledger.

Evennia remains the sole authority for object location, exit locks, and native
action settlement. This module may inspect only the explicitly marked scene;
it does not create symbolic effects for the HTN or Ensemble.
"""

from __future__ import annotations

from collections.abc import Mapping


PROFILE = "p5_story_v0"
P5_INITIAL_PHYSICAL_BUDGET = 2
ROUTE_ACTIONS = {
    "open_main_passage": ("main_passage", 2),
    "open_side_passage": ("side_passage", 1),
}


def _attr(obj, key, default=None, category="native_p3"):
    return obj.attributes.get(key, category=category, default=default)


def _set(obj, key, value, category="native_p5"):
    obj.attributes.add(key, value, category=category)


def scene_objects(scene_id):
    """Resolve only the exact P3 scene allowlist and require a P5 owner marker."""
    from tools.native_platform_v0.p3.p4_world import pickup_for_scene

    pickup, rows = pickup_for_scene(scene_id)
    if _attr(pickup, "p5_scene_id") != scene_id:
        raise ValueError("scene is not marked as a generated P5 scene")
    return pickup, rows


def assert_p5_actor(actor):
    if _attr(actor, "activity_profile") != PROFILE:
        raise ValueError("P5 operation requires a p5_story_v0 actor")
    scene_id = _attr(actor, "scene_id")
    scene_objects(scene_id)
    return scene_id


def _exit(scene_id, room, key, destination):
    return next((edge for edge in room.exits
                 if edge.key == key and edge.destination and edge.destination.id == destination.id
                 and _attr(edge, "p3_scene_id") == scene_id
                 and _attr(edge, "p5_route_id", category="native_p5") is not None), None)


def route_edges(scene_id, route_id):
    """Return the generated, route-tagged directed exits, never global exits."""
    pickup, rows = scene_objects(scene_id)
    destination_id = _attr(pickup, "p4_destination_id")
    destination = next((obj for obj in rows if obj.id == destination_id), None)
    side_id = _attr(pickup, "p5_side_room_id", category="native_p5")
    side = next((obj for obj in rows if obj.id == side_id), None)
    if destination is None:
        raise ValueError("P5 destination room is missing from the generated scene")
    if route_id == "main_passage":
        edge = _exit(scene_id, pickup, "east", destination)
        edges = [edge] if edge is not None else []
    elif route_id == "side_passage":
        if side is None:
            raise ValueError("P5 side room is missing from the generated scene")
        edges = [
            _exit(scene_id, pickup, "south", side),
            _exit(scene_id, side, "north", pickup),
            _exit(scene_id, side, "east", destination),
            _exit(scene_id, destination, "south", side),
        ]
    else:
        raise ValueError("unknown P5 route id")
    if not edges or any(edge is None for edge in edges):
        raise ValueError(f"generated P5 route {route_id} is incomplete")
    return edges


def route_open(scene_id, route_id, actor):
    assert_p5_actor(actor)
    return all(bool(edge.access(actor, "traverse", default=True))
               for edge in route_edges(scene_id, route_id))


def route_rows(scene_id, actor, bundle):
    """Build the finite symbolic planner input from current authorized W state."""
    assert_p5_actor(actor)
    permissions = getattr(bundle, "permissions", {})
    if not isinstance(permissions, Mapping):
        raise TypeError("author bundle permissions must be a mapping")
    allowed = set(permissions.get("world_opportunities", ()))
    max_opportunities = int(permissions.get("max_opportunities", 0))
    cost_budget = int(permissions.get("cost_budget", 0))
    pickup, _ = scene_objects(_attr(actor, "scene_id"))
    used = int(_attr(pickup, "p5_opportunities_used", category="native_p5", default=0))
    spent = int(_attr(pickup, "p5_spent_cost", category="native_p5", default=0))
    route_data = (
        ("main_passage", "open_main_passage", 2, 2),
        ("side_passage", "open_side_passage", 1, 3),
    )
    rows = []
    for route_id, opportunity_id, cost, min_minutes in route_data:
        opened = route_open(_attr(actor, "scene_id"), route_id, actor)
        available = (not opened and opportunity_id in allowed and used < max_opportunities
                     and spent + cost <= min(cost_budget, P5_INITIAL_PHYSICAL_BUDGET))
        rows.append({"id": route_id, "opportunity_id": opportunity_id, "open": opened,
                     "available": available, "cost": cost, "min_minutes": min_minutes,
                     "resource": None})
    return rows


def activate_opportunity(scene_id, actor, action, bundle, *, expected_version):
    """Revalidate one author-authorized route operation against the actual W."""
    assert_p5_actor(actor)
    if action not in ROUTE_ACTIONS:
        return {"settled": False, "status": "WORLD_VALIDATION_REJECTED",
                "reason": "unsupported P5 world opportunity"}
    opportunity_id = action
    route_id, cost = ROUTE_ACTIONS[action]
    bundle_version = getattr(bundle, "version", None)
    if str(bundle_version) != str(expected_version):
        return {"settled": False, "status": "STALE_BUNDLE_VERSION",
                "reason": "active author bundle changed before world dispatch"}
    permissions = getattr(bundle, "permissions", {})
    if not isinstance(permissions, Mapping) or opportunity_id not in set(
            permissions.get("world_opportunities", ())):
        return {"settled": False, "status": "PERMISSION_DENIED",
                "reason": "active bundle does not authorize this world opportunity"}
    if permissions.get("force_npc_response", False) is not False:
        return {"settled": False, "status": "PERMISSION_DENIED",
                "reason": "P5 forbids author permissions that force an NPC response"}

    pickup, _ = scene_objects(scene_id)
    spent = int(_attr(pickup, "p5_spent_cost", category="native_p5", default=0))
    used = int(_attr(pickup, "p5_opportunities_used", category="native_p5", default=0))
    max_opportunities = int(permissions.get("max_opportunities", 0))
    cost_budget = min(int(permissions.get("cost_budget", 0)), P5_INITIAL_PHYSICAL_BUDGET)
    edges = route_edges(scene_id, route_id)
    actor_rows = [obj for obj in scene_objects(scene_id)[1]
                  if _attr(obj, "activity_profile") == PROFILE]
    if not actor_rows:
        raise ValueError("P5 scene has no authorized actors")
    authority_actor = actor_rows[0]
    before = [bool(edge.access(authority_actor, "traverse", default=True)) for edge in edges]
    if all(before):
        return {"settled": False, "status": "ALREADY_OPEN",
                "reason": "route is already open in Evennia"}
    if used >= max_opportunities or spent + cost > cost_budget:
        return {"settled": False, "status": "BUDGET_REJECTED",
                "reason": "P5 opportunity count or physical cost budget is exhausted",
                "spent_cost": spent, "cost": cost, "opportunities_used": used}

    for edge in edges:
        edge.locks.add("traverse:true()")
    after = [bool(edge.access(authority_actor, "traverse", default=True)) for edge in edges]
    settled = all(after) and not all(before)
    result = {"settled": settled,
              "status": "SETTLED" if settled else "WORLD_VALIDATION_REJECTED",
              "route_id": route_id, "opportunity_id": opportunity_id,
              "cost": cost, "before_traversable": before, "after_traversable": after,
              "edge_ids": [int(edge.id) for edge in edges],
              "reason": None if settled else "native exit state did not show the requested route activation"}
    if settled:
        _set(pickup, "p5_spent_cost", spent + cost)
        _set(pickup, "p5_opportunities_used", used + 1)
        from tools.native_platform_v0.p3.p4_world import append_event, clock_for_actor

        clock = clock_for_actor(authority_actor)
        result["receipt_id"] = f"p5:route:{scene_id}:{used + 1}:{route_id}"
        result["sim_minute"] = clock["now"]
        append_event(scene_id, {
            "event_type": "P5_OPPORTUNITY_SETTLED",
            "event_id": result["receipt_id"],
            "typed_args": {"route_id": route_id, "opportunity_id": opportunity_id,
                           "cost": cost, "bundle_id": getattr(bundle, "bundle_id", None),
                           "bundle_version": str(bundle_version), "edge_ids": result["edge_ids"],
                           "before_traversable": before, "after_traversable": after},
            "sealed": True, "receipt_id": result["receipt_id"],
        })
    return result


def record_delivery_receipt(actor, receipt):
    """Project only this actor's native settled drop into the shared typed ledger."""
    scene_id = assert_p5_actor(actor)
    if not isinstance(receipt, Mapping) or receipt.get("settled") is not True:
        raise ValueError("P5 delivery projection requires a settled native receipt")
    if receipt.get("kind") != "drop":
        return None
    item_id = _attr(actor, "task_item_id")
    destination_id = _attr(actor, "task_destination_id")
    if (item_id is None or str(receipt.get("item_id")) != str(item_id)
            or receipt.get("after_item_room_id") != destination_id):
        return None
    item_alias = _attr(actor, "p5_task_item_alias", category="native_p5")
    actor_alias = _attr(actor, "p5_actor_alias", category="native_p5")
    if not item_alias or actor_alias not in ("A", "B"):
        raise ValueError("P5 actor/item aliases are missing from the scene contract")
    receipt_id = str(receipt.get("receipt_id"))
    event_id = f"p5:delivery:{scene_id}:{actor_alias}:{receipt_id}"
    from tools.native_platform_v0.p3.p4_world import append_event

    return append_event(actor, {
        "event_type": "p5_delivery_settled",
        "event_id": event_id,
        "typed_args": {"actor": actor_alias, "item": item_alias},
        "sealed": True, "receipt_id": receipt_id,
    })


def capture_snapshot(scene_id, minute):
    """Persist one verified P5 W snapshot for TypedIR point projection."""
    from tools.native_platform_v0.p3.p4_world import append_event

    pickup, rows = scene_objects(scene_id)
    if type(minute) is not int or minute < 0:
        raise ValueError("P5 snapshot minute must be a nonnegative integer")
    actors = {str(_attr(obj, "p5_actor_alias", category="native_p5")): obj
              for obj in rows if _attr(obj, "activity_profile") == PROFILE}
    if set(actors) != {"A", "B"}:
        raise ValueError("P5 snapshot requires exactly the A/B generated actors")
    items = {}
    for obj in rows:
        alias = _attr(obj, "p5_item_alias", category="native_p5")
        if alias:
            items[alias] = obj
    for actor in actors.values():
        item_alias = _attr(actor, "p5_task_item_alias", category="native_p5")
        item_id = _attr(actor, "task_item_id")
        if item_alias and item_id is not None:
            physical = next((obj for obj in rows if obj.id == item_id), None)
            if physical is not None:
                items[item_alias] = physical
    # The note alias exists before the physical note is created. Absence is a
    # known false holding value; it is not an inferred social event.
    routes = {route_id: route_open(scene_id, route_id, actors["A"])
              for route_id in ("main_passage", "side_passage")}
    holders = {}
    for alias in ("courier_supply", "resident_parcel", "note"):
        item = items.get(alias)
        item_id = item.id if item else None
        holders[alias] = {actor_alias: bool(item_id is not None and any(
            carried.id == item_id for carried in actor.contents))
            for actor_alias, actor in actors.items()}
    snapshot = {"minute": minute, "routes": routes, "holders": holders,
                "item_locations": {alias: (int(item.location.id) if item and item.location else None)
                                   for alias, item in items.items()}}
    snapshots = list(_attr(pickup, "p5_world_snapshots", category="native_p5", default=[]))
    if snapshots and snapshots[-1].get("minute") == minute:
        snapshots[-1] = snapshot
    elif snapshots and snapshots[-1].get("minute", -1) > minute:
        raise ValueError("P5 world snapshot time cannot move backwards")
    else:
        snapshots.append(snapshot)
    _set(pickup, "p5_world_snapshots", snapshots)
    _set(pickup, "p5_snapshot_coverage_minute", minute)
    return snapshot


def _verified_social_responses(ledger, rows, scene_id):
    requests = {row.get("typed_args", {}).get("request_id"): row
                for row in ledger if row.get("event_type") == "SOCIAL_REQUEST"
                and row.get("sealed") is True}
    commits = {row.get("typed_args", {}).get("request_id"): row
               for row in ledger if row.get("event_type") == "SOCIAL_COMMIT"
               and row.get("sealed") is True}
    notes = {int(obj.id): obj for obj in rows
             if _attr(obj, "p3_scene_id") == scene_id
             and _attr(obj, "p4_note_request_id") is not None}
    actors = {str(_attr(obj, "p5_actor_alias", category="native_p5")): obj
              for obj in rows if _attr(obj, "activity_profile") == PROFILE}
    valid = []
    for row in ledger:
        if row.get("event_type") != "SOCIAL_RESPONSE" or row.get("sealed") is not True:
            continue
        args = row.get("typed_args", {})
        request_id = args.get("request_id")
        note_id = args.get("note_id")
        note = notes.get(int(note_id)) if isinstance(note_id, int) else None
        physical = args.get("physical_receipt", {})
        request = requests.get(request_id)
        commit = commits.get(request_id)
        if (args.get("decision") not in ("accepted", "rejected")
                or args.get("native_commit_status") != "settled"
                or not isinstance(physical, Mapping) or physical.get("status") != "settled"
                or physical.get("same_note_id") != note_id
                or request is None or commit is None
                or args.get("native_commit_receipt_id") != commit.get("event_id")):
            continue
        response_minute = int(row.get("minute", -1))
        response_sequence = int(row.get("sequence", -1))
        request_order = (int(request.get("minute", -1)), int(request.get("sequence", -1)))
        commit_order = (int(commit.get("minute", -1)), int(commit.get("sequence", -1)))
        request_args = request.get("typed_args", {}) if request else {}
        request_physical = request_args.get("physical_receipt", {})
        initiator = actors.get("A")
        recipient = actors.get("B")
        expected_action = ("writeLoveNoteAccept" if args.get("decision") == "accepted"
                           else "writeLoveNoteReject")
        if (note is None
                or initiator is None or recipient is None
                or request_args.get("note_id") != note_id
                or request_args.get("initiator_actor_id") != initiator.id
                or request_args.get("recipient_actor_id") != recipient.id
                or args.get("initiator_actor_id") != initiator.id
                or args.get("responder_actor_id") != recipient.id
                or request.get("event_id") != args.get("source_event_id")
                or not isinstance(request_physical, Mapping)
                or request_physical.get("status") != "settled"
                or request_physical.get("after_location_id") != recipient.id
                or request_physical.get("recipient_inventory_actor_id") != recipient.id
                or commit.get("typed_args", {}).get("note_id") != note_id
                or commit.get("typed_args", {}).get("settlement_receipt_id") != physical.get("receipt_id")
                or commit.get("typed_args", {}).get("action_name") != expected_action
                or request_order >= (response_minute, response_sequence)
                or commit_order <= (response_minute, response_sequence)
                or args.get("selected_action") != expected_action
                or physical.get("actor_id") != args.get("responder_actor_id")
                or physical.get("before_location_id") != args.get("responder_actor_id")
                or physical.get("after_location_id") != args.get("responder_actor_id")
                or _attr(note, "p4_note_response_event_id") != row.get("event_id")
                or _attr(note, "p4_note_action") != args.get("selected_action")
                or _attr(note, "p4_native_commit_status") != "settled"):
            continue
        valid.append(row)
    return valid


def build_typed_trace(scene_id, bundle, entities, *, through_minute=None):
    """Project only receipt-backed events and complete persisted W snapshots."""
    from fractions import Fraction

    from tools.trajectory_constraints_v0.trace import Event, Point, Trace
    from tools.trajectory_constraints_v0.types import Owner, ValueRef
    from tools.native_platform_v0.p3.p4_world import clock_for_actor

    pickup, rows = scene_objects(scene_id)
    actors = {str(_attr(obj, "p5_actor_alias", category="native_p5")): obj
              for obj in rows if _attr(obj, "activity_profile") == PROFILE}
    if set(actors) != {"A", "B"}:
        raise ValueError("P5 trace projection requires generated A and B actors")
    clock = clock_for_actor(actors["A"])
    current_now = int(clock["now"])
    now = current_now if through_minute is None else through_minute
    if type(now) is not int or not 0 <= now <= current_now:
        raise ValueError("P5 trace requested an invalid sealed-prefix time")
    event_frontier = min(now, int(_attr(pickup, "p5_event_coverage_minute", category="native_p5", default=0)))
    value_frontier = min(now, int(_attr(pickup, "p5_snapshot_coverage_minute", category="native_p5", default=0)))
    ledger = list(_attr(pickup, "p4_ledger", default=[]))
    native_by_id = {str(_attr(actor, "p5_actor_alias", category="native_p5")): list(
        _attr(actor, "native_receipts", default=[])) for actor in actors.values()}
    verified_social = {row.get("event_id") for row in _verified_social_responses(ledger, rows, scene_id)}
    trace = Trace(scenario_start=Fraction(0), now=Fraction(now))

    # A seal is granted only for a contiguous prefix with one completed world
    # snapshot per simulated minute. The controller advances this frontier
    # after the director and both native actor callbacks have settled.
    raw_snapshots = list(_attr(pickup, "p5_world_snapshots", category="native_p5", default=[]))
    by_minute = {int(row.get("minute", -1)): row for row in raw_snapshots}
    expected_minutes = list(range(value_frontier + 1))
    if any(minute not in by_minute for minute in expected_minutes):
        raise ValueError("P5 world trace has a gap in its declared complete snapshot prefix")
    snapshots = [by_minute[minute] for minute in expected_minutes]
    complete_event_minutes = set(range(event_frontier + 1))
    if not complete_event_minutes.issubset(set(_attr(pickup, "p5_completed_minutes", category="native_p5", default=[]))):
        raise ValueError("P5 event trace frontier includes a minute without completed callback evidence")
    if any(row.get("sealed") is not True or row.get("producer_version") != "native-p4-ledger-v1"
           for row in ledger if int(row.get("minute", -1)) <= event_frontier):
        raise ValueError("P5 typed trace cannot seal an unsealed or foreign-producer ledger row")

    for row in sorted(ledger, key=lambda event: (int(event.get("minute", 0)), int(event.get("sequence", 0)))):
        minute = int(row.get("minute", 0))
        if minute > event_frontier:
            continue
        event_type = row.get("event_type")
        args = row.get("typed_args", {})
        projected = None
        if event_type == "p5_delivery_settled":
            actor_alias, item_alias = args.get("actor"), args.get("item")
            if actor_alias not in actors or item_alias not in entities:
                continue
            receipt_id = str(row.get("receipt_id", ""))
            if not any(receipt.get("receipt_id") == receipt_id and receipt.get("settled") is True
                       and receipt.get("kind") == "drop"
                       and str(receipt.get("item_id")) == str(_attr(actors[actor_alias], "task_item_id"))
                       and receipt.get("after_item_room_id") == _attr(actors[actor_alias], "task_destination_id")
                       for receipt in native_by_id[actor_alias]):
                continue
            projected = Event(row["event_id"], "p5_delivery_settled", minute, int(row["sequence"]),
                              {"actor": entities[actor_alias], "item": entities[item_alias]},
                              version="1", provenance="committed_ledger")
        elif event_type == "SOCIAL_RESPONSE" and row.get("event_id") in verified_social:
            decision = args.get("decision")
            if decision not in ("accepted", "rejected"):
                continue
            note_id = args.get("note_id")
            if not isinstance(note_id, int):
                continue
            projected = Event(
                row["event_id"], "p5_note_response", minute, int(row["sequence"]),
                {"actor": entities["A"], "recipient": entities["B"],
                 "item": entities["note"], "response": decision},
                version="1", provenance="committed_ledger")
        if projected is not None:
            trace.add_event(projected)

    if not snapshots or int(snapshots[0].get("minute", -1)) != 0:
        raise ValueError("P5 world trace lacks its complete initial snapshot")
    holding_refs = []
    for actor_alias in ("A", "B"):
        for item_alias in ("courier_supply", "resident_parcel", "note"):
            ref = ValueRef("p5_holding", "p5-world-v1",
                           {"actor": entities[actor_alias], "item": entities[item_alias]}, Owner.WORLD)
            holding_refs.append((ref, actor_alias, item_alias))
    route_refs = [(ValueRef("p5_route_open", "p5-world-v1", {"route": route}, Owner.WORLD), route)
                  for route in ("main_passage", "side_passage")]
    for snapshot in snapshots:
        time = int(snapshot["minute"])
        for ref, actor_alias, item_alias in holding_refs:
            trace.add_point(Point(ref, time, bool(snapshot["holders"].get(item_alias, {}).get(actor_alias, False)),
                                  source="world_snapshot_projector"))
        for ref, route in route_refs:
            trace.add_point(Point(ref, time, bool(snapshot["routes"].get(route, False)),
                                  source="world_snapshot_projector"))
    if event_frontier >= 0:
        trace.seal_events_through(event_frontier)
    for ref, _, _ in holding_refs:
        trace.seal_values_through(ref, value_frontier)
    for ref, _ in route_refs:
        trace.seal_values_through(ref, value_frontier)
    return trace


def serialize_typed_trace(trace):
    """Return a safe compact, identity-preserving audit representation."""
    def entity(value):
        if hasattr(value, "entity_type") and hasattr(value, "stable_id"):
            return {"entity_type": value.entity_type, "stable_id": value.stable_id}
        return value
    unique_refs = []
    seen_refs = set()
    for point in trace.points:
        # ValueRef itself is frozen, but its args mapping is not hashable.
        # dependency_key is the public, stable identity used by Trace too.
        key = point.ref.dependency_key
        if key not in seen_refs:
            seen_refs.add(key)
            unique_refs.append(point.ref)
    return {
        "now": str(trace.now),
        "events_sealed_through": (None if trace.events_sealed_through is None
                                  else str(trace.events_sealed_through)),
        "events": [{"event_id": row.event_id, "event_type": row.event_type,
                    "time": str(row.time), "sequence": row.sequence,
                    "version": row.version, "provenance": row.provenance,
                    "args": {key: entity(value) for key, value in row.args.items()}}
                   for row in trace.events],
        "points": [{"observable_id": row.ref.observable_id, "version": row.ref.version,
                    "args": {key: entity(value) for key, value in row.ref.args.items()},
                    "time": str(row.time), "value": row.value, "source": row.source}
                   for row in trace.points],
        "value_frontiers": {f"{ref.observable_id}@{ref.version}:{index}": str(trace.values_sealed_through(ref))
                             for index, ref in enumerate(unique_refs)},
    }
