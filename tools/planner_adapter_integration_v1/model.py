"""Versioned P5 evidence projection for the integration-v1 Sabre domain.

This module keeps native world facts and actor-local observations in separate
fields. It never upgrades a planner prediction into a receipt or an NPC task
acceptance.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping

from tools.native_platform_v0.p5.bundle import load_bundle
from tools.trajectory_constraints_v0.monitor import Verdict


SCHEMA = "planner-adapter-integration-v1"
TRACE_SCHEMA = "p5-live-trace-v1"
TRACE_SOURCE = "native_platform_v0.p5.service._evidence"
RENDERER_VERSION = "p5-sabre-causal-domain-v1"
REGISTERED_ROUTES = ("main_passage", "side_passage")
REGISTERED_ACTIONS = {"open_main_passage", "open_side_passage"}


def _hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class PlannerSnapshot:
    scene_id: str
    bundle_id: str
    bundle_version: int
    minute: int
    horizon: int
    source_trace_sha256: str
    source_bundle_sha256: str
    renderer_version: str
    route_open: tuple[tuple[str, bool], ...]
    route_available: tuple[tuple[str, bool], ...]
    route_cost: tuple[tuple[str, int], ...]
    spent_cost: int
    opportunity_count: int
    opportunity_limit: int
    cost_budget: int
    actor_roles: tuple[str, ...]
    actor_rooms: tuple[tuple[str, str], ...]
    actor_ready: tuple[tuple[str, bool], ...]
    observation_evidence: tuple[tuple[str, str, int], ...]
    scene_room_roles: tuple[tuple[str, str], ...]
    scene_room_ids: tuple[tuple[str, int], ...]
    world_route_edges: tuple[tuple[str, str, str, bool, bool], ...]
    task_bindings: tuple[tuple[str, str, str, str], ...]
    # These are actor-indexed local O, never copied from global W topology.
    known_exits: tuple[tuple[str, str, str], ...]
    known_task_item_locations: tuple[tuple[str, str, str | None, bool], ...]
    world_item_location: tuple[tuple[str, str | None], ...]
    world_holders: tuple[tuple[str, str | None], ...]
    social_target_visible: bool
    witnessed_events: tuple[tuple[str, str, str, str, int, int], ...]
    known_held_items: tuple[tuple[str, tuple[str, ...]], ...]
    # Registry-backed requirements are represented as a closed, finite set.
    hard_requirements: tuple[tuple[str, str, int, int, str], ...]
    constraint_statuses: tuple[tuple[str, str], ...]
    branches: tuple[tuple[str, str, str], ...]
    projection_residuals: tuple[str, ...]


def build_snapshot(trace: Mapping[str, Any], raw_bundle: Mapping[str, Any], *, scene_id: str,
                   actor_observations: Mapping[str, Mapping[str, Any]] | None = None) -> PlannerSnapshot:
    """Validate a sealed current prefix and project only registered P5 facts.

    The caller must supply the exact active AuthorBundle alongside its native
    trace. This checks provenance envelope and content identity; it is not a
    cryptographic authentication mechanism.
    """
    if not isinstance(trace, Mapping) or not isinstance(raw_bundle, Mapping):
        raise TypeError("trace and raw_bundle must be mappings")
    if trace.get("scene_id") != scene_id or trace.get("evidence_schema") != TRACE_SCHEMA \
            or trace.get("source") != TRACE_SOURCE or trace.get("prefix_status") != "SEALED_COMPLETE":
        raise ValueError("integration-v1 requires a sealed P5 live-evidence prefix")
    now = trace.get("now")
    complete = trace.get("complete_through")
    if type(now) is not int or not isinstance(complete, Mapping) \
            or complete.get("events") != now or complete.get("values") != now:
        raise ValueError("P5 event/value frontiers must equal the current minute")
    bundle = load_bundle(raw_bundle)
    identity = trace.get("bundle_identity")
    if not isinstance(identity, Mapping) or identity.get("bundle_id") != bundle.bundle_id \
            or identity.get("version") != bundle.version:
        raise ValueError("trace verdicts and active bundle identity/version differ")
    world = trace.get("world_snapshots")
    if not isinstance(world, list):
        raise ValueError("missing native world snapshot history")
    current = next((row for row in world if isinstance(row, Mapping) and row.get("minute") == now), None)
    if current is None or not isinstance(current.get("routes"), Mapping):
        raise ValueError("missing world snapshot at sealed frontier")
    routes = current["routes"]
    route_open = tuple((route, routes.get(route)) for route in REGISTERED_ROUTES)
    if any(type(value) is not bool for _, value in route_open):
        raise ValueError("registered route state is incomplete")
    capability = trace.get("world_capability_projection")
    if (not isinstance(capability, Mapping)
            or capability.get("schema") != "p5-planner-scene-binding-v1"
            or capability.get("source") != "native_platform_v0.p5.service._planner_scene_binding"
            or capability.get("scene_id") != scene_id):
        raise ValueError("missing scene-bound P5 world-capability projection")
    room_roles_raw = capability.get("room_roles")
    task_bindings_raw = capability.get("task_bindings")
    route_rows = capability.get("routes")
    if (not isinstance(room_roles_raw, Mapping)
            or set(room_roles_raw) != {"pickup", "side", "porch"}
            or any(type(value) is not int for value in room_roles_raw.values())
            or not isinstance(task_bindings_raw, Mapping)
            or set(task_bindings_raw) != {"A", "B"}
            or not isinstance(route_rows, list)):
        raise ValueError("malformed P5 scene role/task/route capability projection")
    room_alias_by_id = {value: key for key, value in room_roles_raw.items()}
    scene_room_roles = tuple((key, key) for key in room_roles_raw)
    scene_room_ids = tuple((key, value) for key, value in room_roles_raw.items())
    task_bindings = []
    for actor in ("A", "B"):
        row = task_bindings_raw[actor]
        expected_item_alias = "courier_supply" if actor == "A" else "resident_parcel"
        if (not isinstance(row, Mapping) or row.get("source") != "existing_scene_actor_binding"
                or row.get("item_alias") != expected_item_alias
                or type(row.get("item_id")) is not int
                or row.get("destination_id") != room_roles_raw["porch"]):
            raise ValueError(f"invalid existing task binding for actor {actor}")
        destination_alias = room_alias_by_id.get(row["destination_id"])
        if destination_alias is None:
            raise ValueError(f"existing task destination for actor {actor} is outside the registered scene")
        task_bindings.append((actor, row["item_alias"], str(row["item_id"]), destination_alias))
    if len({row[2] for row in task_bindings}) != 2:
        raise ValueError("A/B delivery task aliases must bind distinct native item IDs")
    route_by_id = {row.get("route_id"): row for row in route_rows if isinstance(row, Mapping)}
    if set(route_by_id) != set(REGISTERED_ROUTES):
        raise ValueError("scene capability projection must include exactly the two registered routes")
    world_route_edges = []
    for route in REGISTERED_ROUTES:
        edges = route_by_id[route].get("directed_edges")
        if not isinstance(edges, list) or not edges:
            raise ValueError(f"route {route} has no generated directed edge projection")
        opportunity = "open_main_passage" if route == "main_passage" else "open_side_passage"
        if route_by_id[route].get("opportunity_id") != opportunity:
            raise ValueError(f"route {route} is not bound to its registered author opportunity")
        changed_ids = route_by_id[route].get("changed_edge_ids")
        if not isinstance(changed_ids, list) or any(type(value) is not int for value in changed_ids):
            raise ValueError(f"route {route} changed_edge_ids is malformed")
        actual_ids = {edge.get("exit_id") for edge in edges if isinstance(edge, Mapping)}
        if not set(changed_ids).issubset(actual_ids):
            raise ValueError(f"route {route} author-controlled exits are outside its actual edge set")
        for edge in edges:
            if (not isinstance(edge, Mapping) or type(edge.get("exit_id")) is not int
                    or type(edge.get("from_room_id")) is not int
                    or type(edge.get("to_room_id")) is not int
                    or type(edge.get("changed_by_author_op")) is not bool
                    or type(edge.get("traversable_now")) is not bool):
                raise ValueError(f"route {route} has a malformed directed edge")
            source = room_alias_by_id.get(edge["from_room_id"])
            target = room_alias_by_id.get(edge["to_room_id"])
            if source is None or target is None:
                raise ValueError(f"route {route} edge endpoint is outside the registered scene")
            world_route_edges.append((route, source, target, edge["changed_by_author_op"],
                                      edge["traversable_now"]))
    ledger = trace.get("ledger")
    if not isinstance(ledger, list):
        raise ValueError("missing P5 ledger")
    spent = 0
    opportunity_count = 0
    for row in ledger:
        if not isinstance(row, Mapping) or row.get("sealed") is not True:
            continue
        minute = row.get("minute")
        if type(minute) is not int or minute > now:
            continue
        if row.get("event_type") == "P5_OPPORTUNITY_SETTLED":
            args = row.get("typed_args")
            if not isinstance(args, Mapping) or type(args.get("cost")) is not int:
                raise ValueError("settled opportunity lacks registered cost")
            spent += args["cost"]
            opportunity_count += 1
    permissions = bundle.permissions
    # P5's sealed actor_evidence carries the last p5_goal_choice.view per actor.
    # Use only a view logged at this sealed minute; never derive O from W routes.
    actor_evidence = trace.get("actor_evidence")
    local_views: dict[str, Mapping[str, Any]] = {}
    actor_ids: dict[str, int] = {}
    observation_evidence: dict[str, tuple[str, int]] = {}
    actor_ready = []
    if actor_observations is not None:
        if (not isinstance(actor_observations, Mapping)
                or set(actor_observations) != {"schema", "source", "scene_id", "sampled_at_minute",
                                               "sampling_order", "observations"}
                or actor_observations.get("schema") != "planner-adapter-actor-observation-v1"
                or actor_observations.get("source") != "p3.control_service.observe_actor"
                or actor_observations.get("scene_id") != scene_id
                or actor_observations.get("sampled_at_minute") != now
                or actor_observations.get("sampling_order") != ["A", "B"]
                or not isinstance(actor_observations.get("observations"), Mapping)
                or set(actor_observations["observations"]) != {"A", "B"}):
            raise ValueError("actor_observations must be a current ordered A/B observe_actor envelope")
        expected_roles = {"A": "courier", "B": "resident"}
        for alias, observation in actor_observations["observations"].items():
            if (not isinstance(observation, Mapping)
                    or set(observation) != {"actor_role", "local_observation"}
                    or observation.get("actor_role") != expected_roles[alias]
                    or not isinstance(observation.get("local_observation"), Mapping)):
                raise ValueError(f"invalid current actor observation envelope for {alias}")
            # observe_actor returns the whole native local-view envelope
            # (goal_contract + observation), so preserve its outer structure;
            # the projection below reads both separately.
            local_views[alias] = observation["local_observation"]
            observation_evidence[alias] = (str(actor_observations["source"]), now)
    if isinstance(actor_evidence, list):
        for actor_row in actor_evidence:
            if not isinstance(actor_row, Mapping) or actor_row.get("actor_alias") not in {"A", "B"}:
                continue
            alias = str(actor_row["actor_alias"])
            if type(actor_row.get("actor_id")) is int:
                actor_ids[alias] = actor_row["actor_id"]
            pending = actor_row.get("pending_action")
            actor_ready.append((alias, pending is None))
            logs = actor_row.get("log")
            if not isinstance(logs, list):
                continue
            rows = [row for row in logs if isinstance(row, Mapping)
                    and row.get("kind") == "p5_goal_choice" and type(row.get("sim_minute")) is int
                    and row.get("sim_minute") <= now
                    and isinstance(row.get("view"), Mapping)]
            if rows and str(actor_row["actor_alias"]) not in local_views:
                latest = rows[-1]
                alias = str(actor_row["actor_alias"])
                local_views[alias] = latest["view"]
                observation_evidence[alias] = ("sealed_p5_goal_choice_view", int(latest["sim_minute"]))
    residuals = []
    if {actor for actor, _ in actor_ready} != {"A", "B"}:
        residuals.append("sealed native pending-action state is missing for A and/or B")
    if any(not ready for _, ready in actor_ready):
        residuals.append("native actor intent is pending; reobserve after settlement before projecting another actor action")
    if set(local_views) != {"A", "B"}:
        residuals.append("sealed actor-local observation is missing for A and/or B at current minute")
    for actor, (_, observed_at) in observation_evidence.items():
        if observed_at < now:
            residuals.append(f"actor {actor} local O is stale by {now - observed_at} minute(s); no current O was supplied")
    goals = []
    for goal in bundle.goals:
        if goal.hard:
            goals.append((goal.constraint_id, goal.kind, goal.start, goal.deadline,
                          json.dumps(dict(goal.source), sort_keys=True, separators=(",", ":"))))
        else:
            residuals.append(f"soft constraint {goal.constraint_id} is not optimized")
    branch_rows = tuple((branch.branch_id, branch.response, branch.storylet_id)
                        for branch in bundle.branches)
    horizon = int(trace.get("horizon", 24))
    actor_rooms = []
    known_exit_rows: set[tuple[str, str, str]] = set()
    known_task_locations = []
    held_items = {"A": [], "B": []}
    for actor, view in local_views.items():
        obs = view.get("observation")
        goal_contract = view.get("goal_contract")
        if not isinstance(obs, Mapping):
            residuals.append(f"actor {actor} local view lacks a closed observation")
            continue
        room = obs.get("room_id")
        if type(room) is int:
            if room in room_alias_by_id:
                actor_rooms.append((actor, room_alias_by_id[room]))
            else:
                residuals.append(f"actor {actor} current room is outside the registered P5 scene")
        else:
            residuals.append(f"actor {actor} current room is absent or invalid")
        task = obs.get("task_item")
        task_id = task.get("id") if isinstance(task, Mapping) else None
        task_binding = next(row for row in task_bindings if row[0] == actor)
        task_alias = task_binding[1]
        item_room = obs.get("item_location")
        known_location = room_alias_by_id.get(item_room) if type(item_room) is int else None
        if type(item_room) is int and known_location is None:
            residuals.append(f"actor {actor} local item location is outside the registered P5 scene")
        item_held = obs.get("item_held") is True
        known_task_locations.append((actor, task_alias, known_location, item_held))
        if item_held:
            held_items[actor].append(task_alias)
        for source, destinations in (obs.get("known_exits") or {}).items():
            try:
                source_id = int(source)
                destination_ids = tuple(int(value) for value in destinations)
            except (TypeError, ValueError):
                residuals.append(f"actor {actor} local known_exits has an invalid room ID")
                continue
            if source_id not in room_alias_by_id or any(destination not in room_alias_by_id
                                                       for destination in destination_ids):
                residuals.append(f"actor {actor} local O contains an edge outside the registered P5 scene")
                continue
            source_alias = room_alias_by_id[source_id]
            known_exit_rows.update((actor, source_alias, room_alias_by_id[destination])
                                   for destination in destination_ids)
        destination_id = (goal_contract.get("destination_id") if isinstance(goal_contract, Mapping)
                          else obs.get("task_destination"))
        if (type(task_id) is not int or str(task_id) != task_binding[2]
                or type(destination_id) is not int
                or destination_id != room_roles_raw["porch"]):
            residuals.append(f"actor {actor} local task/item/destination does not match the scene-bound native task identity")
    native_snapshot = next((row for row in reversed(world) if isinstance(row, Mapping)
                            and row.get("minute") == now), {})
    locations = native_snapshot.get("item_locations", {}) if isinstance(native_snapshot, Mapping) else {}
    holders = native_snapshot.get("holders", {}) if isinstance(native_snapshot, Mapping) else {}
    world_item_location = {}
    world_holders = []
    # W item locations are evidence for current physical state only; they do
    # not populate actor-known task locations or route beliefs.
    for alias in ("courier_supply", "resident_parcel", "note"):
        loc = locations.get(alias) if isinstance(locations, Mapping) else None
        world_location = room_alias_by_id.get(loc) if type(loc) is int else None
        holder_rows = holders.get(alias, {}) if isinstance(holders, Mapping) else {}
        held_by = next((actor for actor, value in holder_rows.items() if value is True), None) \
            if isinstance(holder_rows, Mapping) else None
        if held_by not in {None, "A", "B"}:
            residuals.append(f"world item {alias} is held by an unregistered entity")
            held_by = None
        if type(loc) is int and world_location is None and held_by is None:
            residuals.append(f"world item {alias} has a holder/nonfixture location not representable as a scene room")
        world_item_location[alias] = world_location
        world_holders.append((alias, held_by))
    a_view = local_views.get("A", {})
    a_obs = a_view.get("observation") if isinstance(a_view, Mapping) else None
    visible_items = a_obs.get("visible_items") if isinstance(a_obs, Mapping) else None
    social_target_visible = (
        set(actor_ids) == {"A", "B"}
        and isinstance(a_view, Mapping) and a_view.get("actor_id") == actor_ids["A"]
        and isinstance(visible_items, list)
        and any(isinstance(item, Mapping) and item.get("id") == actor_ids["B"]
                for item in visible_items)
    )
    typed = trace.get("typed_trace")
    event_rows = typed.get("events") if isinstance(typed, Mapping) else None
    if not isinstance(event_rows, list):
        raise ValueError("P5 TypedIR event prefix is missing")
    witnessed = []
    for event in event_rows:
        if not isinstance(event, Mapping) or not isinstance(event.get("args"), Mapping):
            continue
        event_type = event.get("event_type")
        if event_type not in {"p5_delivery_settled", "p5_note_response"}:
            continue
        try:
            time_value = int(event.get("time"))
            sequence = int(event.get("sequence"))
        except (TypeError, ValueError):
            raise ValueError("P5 typed event has invalid time/sequence")
        args = event["args"]
        actor = args.get("actor", {}).get("stable_id") if isinstance(args.get("actor"), Mapping) else None
        item = args.get("item", {}).get("stable_id") if isinstance(args.get("item"), Mapping) else None
        response = args.get("response", "")
        if (actor not in {"A", "B"} or not isinstance(item, str)
                or (event_type == "p5_note_response" and response not in {"accepted", "rejected"})):
            raise ValueError("P5 typed event contains an unregistered actor/item/response binding")
        witnessed.append((event_type, actor, item, str(response), time_value, sequence))
    verdicts = trace.get("verdicts")
    verdict_rows = verdicts.get("constraints") if isinstance(verdicts, Mapping) else None
    if not isinstance(verdict_rows, list):
        raise ValueError("P5 verdict constraints are missing")
    constraint_statuses = []
    for row in verdict_rows:
        if (not isinstance(row, Mapping) or not isinstance(row.get("constraint_id"), str)
                or row.get("status") not in {verdict.value for verdict in Verdict}):
            raise ValueError("P5 TypedIR verdict row is malformed")
        constraint_statuses.append((row["constraint_id"], row["status"]))
    goal_ids = {goal.constraint_id for goal in bundle.goals}
    verdict_ids = [row[0] for row in constraint_statuses]
    if len(verdict_ids) != len(set(verdict_ids)) or set(verdict_ids) != goal_ids:
        raise ValueError("TypedIR verdict IDs must uniquely and exactly match the active bundle goals")
    route_cost_rows = {row.get("route_id"): row.get("cost") for row in route_rows
                       if isinstance(row, Mapping)}
    if (set(route_cost_rows) != set(REGISTERED_ROUTES)
            or any(type(value) is not int or value < 0 for value in route_cost_rows.values())):
        raise ValueError("scene capability projection must carry exact registered route costs")
    return PlannerSnapshot(
        scene_id=scene_id, bundle_id=bundle.bundle_id, bundle_version=bundle.version,
        minute=now, horizon=horizon,
        source_trace_sha256=_hash({"trace": trace, "actor_observations": actor_observations}),
        source_bundle_sha256=_hash(raw_bundle), renderer_version=RENDERER_VERSION,
        route_open=route_open,
        route_available=tuple((route,
                               action in set(permissions.get("world_opportunities", ()))
                               and not dict(route_open)[route]
                               and opportunity_count < int(permissions.get("max_opportunities", 0))
                               and spent + route_cost_rows[route] <= min(2, int(permissions.get("cost_budget", 0))))
                              for route, action in (("main_passage", "open_main_passage"),
                                                    ("side_passage", "open_side_passage"))),
        route_cost=tuple((route, route_cost_rows[route]) for route in REGISTERED_ROUTES),
        spent_cost=spent, opportunity_count=opportunity_count,
        opportunity_limit=int(permissions.get("max_opportunities", 0)),
        cost_budget=min(2, int(permissions.get("cost_budget", 0))),
        actor_roles=("A", "B"), actor_rooms=tuple(actor_rooms),
        actor_ready=tuple(sorted(actor_ready)),
        observation_evidence=tuple((actor, source, sample_minute)
                                   for actor, (source, sample_minute) in sorted(observation_evidence.items())),
        scene_room_roles=scene_room_roles, world_route_edges=tuple(world_route_edges),
        scene_room_ids=scene_room_ids,
        task_bindings=tuple(task_bindings),
        known_exits=tuple(sorted(known_exit_rows)),
        known_task_item_locations=tuple(sorted(known_task_locations)),
        world_item_location=tuple(sorted(world_item_location.items())),
        world_holders=tuple(sorted(world_holders)),
        social_target_visible=social_target_visible,
        witnessed_events=tuple(sorted(witnessed, key=lambda row: (row[4], row[5]))),
        known_held_items=tuple((actor, tuple(items)) for actor, items in sorted(held_items.items())),
        hard_requirements=tuple(goals), branches=branch_rows,
        constraint_statuses=tuple(constraint_statuses),
        projection_residuals=tuple(residuals),
    )
