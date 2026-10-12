"""Causal, finite Sabre domain for registered P5 courier/story actions.

Sabre actions are counterfactual candidate steps. Only registered P5 author
opportunities are dispatchable; A/B remain autonomous GTPyhop/Ensemble actors.
"""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any

from tools.planner_p0_v0.sabre_baseline.runner import parse_native_output
from .model import PlannerSnapshot

ROOT = Path(__file__).resolve().parents[2]
JAVA = ROOT / "_local_data/planner_p0_v0/jdk/jdk-17.0.20.1+1/Contents/Home/bin/java"
CLASSPATH = ROOT / "_local_data/planner_p0_v0/sabre/bin"
SEARCH_LIMITS = {"revision": "primitive-domain-r2",
                 "revision_reason": "r1 hit the inherited 200-node cap in 29ms (604 generated), before its 5s native time limit",
                 "method": "bf", "cost": "t", "heuristic": "h+",
                 "epistemic_limit": 1, "max_visited": 10000,
                 "max_generated": 100000, "time_limit_ms": 5000,
                 # This adapter searches primitive causal sequences, not the
                 # legacy two-step route selector. Keep the cap fixed.
                 "author_limit": 24, "character_limit": 16,
                 "heap_min": "64m", "heap_max": "1g", "stack_size": "8m"}
ROUTE_ACTION = {"main_passage": "open_main_passage", "side_passage": "open_side_passage"}
EVENTS = {"p5_delivery_settled": "delivery", "p5_note_response": "response"}
ITEM_ENTITIES = {"courier_supply": "Supply", "resident_parcel": "Parcel", "note": "Note"}


def _name(token: str) -> str:
    aliases = {"pickup": "Pickup", "side": "Side", "porch": "Porch"}
    if token in aliases:
        return aliases[token]
    match = re.fullmatch(r"room_(\d+)", token)
    if match:
        return f"Room{match.group(1)}"
    raise ValueError(f"unregistered P5 room token {token!r}")


def _safe(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_]", "_", value)


def _req_goal(clause_id: str, source_json: str, task_bindings: dict[str, tuple[str, str, str]],
              *, route_open: dict[str, bool], now: int) -> tuple[str | None, str | None]:
    """Map one registered AuthorBundle hard constraint into a Sabre condition."""
    source = json.loads(source_json)
    kind = source.get("kind")
    if kind == "event_by_deadline":
        event = source.get("event")
        filters = source.get("filters", {})
        if event == "delivery_settled":
            actor, item = filters.get("actor"), filters.get("item")
            if actor not in task_bindings or item != task_bindings[actor][0]:
                return None, "delivery event is not the actor's existing bound item"
            if source.get("min_count", 1) != 1 or source.get("max_count") not in (None, 1):
                return None, "delivery event count outside once-only native task support"
            flag = f"delivered({actor}, {ITEM_ENTITIES[item]})"
            time = f"delivery_time({actor}, {ITEM_ENTITIES[item]})"
        elif event == "note_response":
            if (filters.get("actor", "A") != "A" or filters.get("recipient", "B") != "B"
                    or filters.get("item", "note") != "note"):
                return None, "note response filter is outside the registered A-to-B social binding"
            if source.get("min_count", 1) != 1 or source.get("max_count") not in (None, 1):
                return None, "note response event count outside once-only native social support"
            response = filters.get("response")
            if response not in (None, "accepted", "rejected"):
                return None, "unregistered note response value"
            flag = ("response_recorded()" if response is None else
                    f"(response_recorded() & response_value() == {'Accepted' if response == 'accepted' else 'Rejected'})")
            time = "response_time()"
        else:
            return None, "unregistered P5 event"
        return f"({flag} & window_{_safe(clause_id)}())", None
    if kind == "event_order":
        before, after = source.get("before", {}), source.get("after", {})
        bfilters, afilters = before.get("filters", {}), after.get("filters", {})
        actor, item = bfilters.get("actor"), bfilters.get("item")
        if (before.get("event") != "delivery_settled" or after.get("event") != "note_response"
                or actor not in task_bindings or item != task_bindings[actor][0]
                or afilters.get("actor", "A") != "A" or afilters.get("recipient", "B") != "B"):
            return None, "only the registered bound-delivery-before-A-to-B-note-response order is projected"
        if source.get("order") == "PHYSICAL_TIME":
            event = f"delivery_time({actor}, {ITEM_ENTITIES[item]})"
            response_filter = afilters.get("response")
            if response_filter not in (None, "accepted", "rejected"):
                return None, "unregistered note-response filter in event order"
            response_value = ("" if response_filter is None else
                              f" & response_value() == {'Accepted' if response_filter == 'accepted' else 'Rejected'}")
            return f"(delivered({actor}, {ITEM_ENTITIES[item]}) & response_recorded() & delivery_time({actor}, {ITEM_ENTITIES[item]}) < response_time() & window_{_safe(clause_id)}(){response_value})", None
        return None, "unknown event-order mode"
    if kind == "state_by_deadline":
        if source.get("observable") != "route_open":
            return None, "non-route state projection is not registered in integration-v1"
        route = source.get("args", {}).get("route")
        desired = source.get("value")
        if route not in route_open or desired is not True:
            return None, "route-close target has no native close action"
        if route_open[route]:
            return f"window_{_safe(clause_id)}()", None
        return f"route_open_{route}() & window_{_safe(clause_id)}()", None
    return None, "unregistered hard constraint kind"


def render_problem(snapshot: PlannerSnapshot, *, deadline: int | None = None) -> str:
    """Render actor-level causal actions and bundle-derived hard goals.

    The action-level path uses local O (`known_path(actor,...)`) separately
    from generated W capability edges (`possible_path(...)`). Exploration is an
    explicit actor-consenting move that converts only a traversed edge into O.
    """
    if not isinstance(snapshot, PlannerSnapshot):
        raise TypeError("render_problem requires a validated integration-v1 snapshot")
    horizon = snapshot.horizon if deadline is None else deadline
    if type(horizon) is not int or not snapshot.minute <= horizon <= snapshot.horizon:
        raise ValueError("deadline must be an integer within the remaining P5 horizon")
    role_tokens = dict(snapshot.scene_room_roles)
    room_roles = {token: role for role, token in role_tokens.items()}
    all_tokens = set(role_tokens.values())
    all_tokens.update(room for _, room in snapshot.actor_rooms)
    all_tokens.update(source for _, source, _ in snapshot.known_exits)
    all_tokens.update(target for _, _, target in snapshot.known_exits)
    all_tokens.update(source for _, source, target, _, _ in snapshot.world_route_edges)
    all_tokens.update(target for _, source, target, _, _ in snapshot.world_route_edges)
    place_entities = sorted({_name(token) for token in all_tokens})
    task_bindings = {actor: (item, item_id, destination)
                     for actor, item, item_id, destination in snapshot.task_bindings}
    item_entities = ITEM_ENTITIES
    route_open = dict(snapshot.route_open)
    route_cost = dict(snapshot.route_cost)
    if set(route_cost) != {"main_passage", "side_passage"} or any(
            type(cost) is not int or cost < 0 for cost in route_cost.values()):
        raise ValueError("snapshot must carry exact registered route costs")
    supported_goals, hard_residuals = [], []
    hard_goal_sources = {}
    statuses = dict(snapshot.constraint_statuses)
    actor_rooms = dict(snapshot.actor_rooms)
    for clause_id, kind, start, end, source in snapshot.hard_requirements:
        if statuses.get(clause_id) == "SATISFIED":
            supported_goals.append((clause_id, "already_witnessed()"))
            continue
        source_data = json.loads(source)
        if (source_data.get("kind") == "event_by_deadline"
                and source_data.get("event") == "note_response"
                and (not snapshot.social_target_visible or actor_rooms.get("A") != actor_rooms.get("B"))):
            hard_residuals.append(f"{clause_id}: conditional native request requires A-visible, co-located B in current actor-local O")
            continue
        condition, residual = _req_goal(clause_id, source, task_bindings, route_open=route_open,
                                       now=snapshot.minute)
        if statuses.get(clause_id) == "VIOLATED" and snapshot.minute > end:
            condition = None
            residual = "native TypedIR reports the hard window irrecoverably violated"
        if condition is None:
            hard_residuals.append(f"{clause_id}: {residual}")
        else:
            supported_goals.append((clause_id, condition))
            hard_goal_sources[clause_id] = json.loads(source)
    residuals = list(snapshot.projection_residuals) + hard_residuals
    projection_blockers = hard_residuals + [reason for reason in snapshot.projection_residuals
                                             if not reason.startswith("soft constraint ")]
    # Complete action sequence is searched by Sabre; unsupported obligations
    # stay visible and are not promoted into another author's target.
    goal_condition = " & ".join(f"goal_{_safe(clause_id)}()" for clause_id, _ in supported_goals)
    if not supported_goals:
        goal_condition = "no_hard_goal()"

    lines = [
        "type character;", "entity A : character;", "entity B : character;",
        "type place;", *(f"entity {value} : place;" for value in place_entities),
        "type item;", "entity Supply : item;", "entity Parcel : item;", "entity Note : item;",
        "type response;", "entity Accepted : response;", "entity Rejected : response;", "",
        "property now() : number;", "property horizon() : number;",
        "property at(character : character) : place;",
        "property possible_path(from : place, to : place) : boolean;",
        "property known_path(actor : character, from : place, to : place) : boolean;",
        "property bound_item(actor : character, item : item) : boolean;",
        "property task_destination(actor : character, place : place) : boolean;",
        "property item_at(item : item, place : place) : boolean;",
        "property held_by(item : item, actor : character) : boolean;",
        "property known_item_at(actor : character, item : item, place : place) : boolean;",
        "property delivered(actor : character, item : item) : boolean;",
        "property delivery_time(actor : character, item : item) : number;",
        "property delivery_sequence(actor : character, item : item) : number;",
        "property note_attempted() : boolean;", "property note_requested() : boolean;",
        "property social_target_visible() : boolean;", "property response_recorded() : boolean;",
        "property response_value() : response;", "property response_time() : number;",
        "property response_sequence() : number;", "property event_sequence() : number;",
        "property route_open_time_main_passage() : number;",
        "property route_open_time_side_passage() : number;",
        "property actor_next(character : character) : number;",
        "property actor_ready(character : character) : boolean;",
        "property opportunity_count() : number;",
        "property spent_cost() : number;", "property route_open_main_passage() : boolean;",
        "property route_open_side_passage() : boolean;", "property no_hard_goal() : boolean;",
        "property projection_complete() : boolean;",
        "property already_witnessed() : boolean;",
    ]
    lines.extend(f"property goal_{_safe(clause_id)}() : boolean;" for clause_id, _ in supported_goals)
    lines.extend(f"property window_start_{_safe(clause_id)}() : boolean;" for clause_id, _ in supported_goals)
    lines.extend(f"property window_ordered_{_safe(clause_id)}() : boolean;"
                 for clause_id, _ in supported_goals
                 if hard_goal_sources.get(clause_id, {}).get("kind") == "event_order")
    lines.extend(f"property window_{_safe(clause_id)}() : boolean;" for clause_id, _ in supported_goals)
    prior_sequence = max((row[5] for row in snapshot.witnessed_events), default=0)
    lines.extend(["", f"now() = {snapshot.minute};", f"horizon() = {horizon};",
                  f"opportunity_count() = {snapshot.opportunity_count};",
                  f"spent_cost() = {snapshot.spent_cost};", f"event_sequence() = {prior_sequence};"])
    for actor in ("A", "B"):
        lines.append(f"actor_next({actor}) = {snapshot.minute + 2};")
    for actor, ready in snapshot.actor_ready:
        if ready:
            lines.append(f"actor_ready({actor});")
    for route, is_open in snapshot.route_open:
        if is_open:
            lines.append(f"route_open_{route}();")
            lines.append(f"route_open_time_{route}() = {snapshot.minute};")
    for actor, room in snapshot.actor_rooms:
        lines.append(f"at({actor}) = {_name(room)};")
    for actor, item, item_id, destination in snapshot.task_bindings:
        lines.extend([f"bound_item({actor}, {item_entities[item]});",
                      f"task_destination({actor}, {_name(destination)});"])
    for route, source, target, changed, traversable in snapshot.world_route_edges:
        if traversable:
            lines.append(f"possible_path({_name(source)}, {_name(target)});")
    for actor, source, target in snapshot.known_exits:
        lines.append(f"known_path({actor}, {_name(source)}, {_name(target)});")
    for item, location in snapshot.world_item_location:
        if location is not None:
            lines.append(f"item_at({item_entities[item]}, {_name(location)});")
    for item, actor in snapshot.world_holders:
        if actor is not None:
            lines.append(f"held_by({item_entities[item]}, {actor});")
    if snapshot.social_target_visible:
        lines.append("social_target_visible();")
    for actor, item, location, held in snapshot.known_task_item_locations:
        if location is not None:
            lines.append(f"known_item_at({actor}, {item_entities[item]}, {_name(location)});")
        if held:
            lines.append(f"held_by({item_entities[item]}, {actor});")
    # Prior settled events are initialized with their real absolute event time
    # and event sequence; this prevents a completed goal being reset to a plan.
    for event_type, actor, item, response, minute, sequence in snapshot.witnessed_events:
        if event_type == "p5_delivery_settled" and actor in {"A", "B"}:
            binding = task_bindings.get(actor)
            if binding and item == binding[0]:
                entity = item_entities[item]
                lines.extend([f"delivered({actor}, {entity});",
                              f"delivery_time({actor}, {entity}) = {minute};",
                              f"delivery_sequence({actor}, {entity}) = {sequence};"])
        elif event_type == "p5_note_response" and actor == "A" and item == "note":
            lines.extend(["note_attempted();", "note_requested();", "response_recorded();",
                          f"response_value() = {'Accepted' if response == 'accepted' else 'Rejected'};",
                          f"response_time() = {minute};", f"response_sequence() = {sequence};"])
    if not supported_goals:
        lines.append("no_hard_goal();")
    else:
        for clause_id, _ in supported_goals:
            if statuses.get(clause_id) == "SATISFIED":
                lines.append(f"goal_{_safe(clause_id)}();")
    if not projection_blockers:
        lines.append("projection_complete();")
    if dict(snapshot.route_available).get("main_passage"):
        cost = route_cost["main_passage"]
        lines.extend(["", "action open_main_passage() {", "\tprecondition:",
                      f"\t\t!route_open_main_passage() & now() == {snapshot.minute} & now() + 1 <= horizon() & opportunity_count() < {snapshot.opportunity_limit} & spent_cost() + {cost} <= {snapshot.cost_budget};",
                      f"\teffect: route_open_main_passage() & route_open_time_main_passage() = now() + 1 & opportunity_count() = opportunity_count() + 1 & spent_cost() = spent_cost() + {cost} & now() = now() + 1" +
                      "".join(f" & possible_path({_name(source)}, {_name(target)})"
                              for route, source, target, changed, _ in snapshot.world_route_edges
                              if route == "main_passage" and changed) + ";",
                      "};"])
    if dict(snapshot.route_available).get("side_passage"):
        cost = route_cost["side_passage"]
        lines.extend(["", "action open_side_passage() {", "\tprecondition:",
                      f"\t\t!route_open_side_passage() & now() == {snapshot.minute} & now() + 1 <= horizon() & opportunity_count() < {snapshot.opportunity_limit} & spent_cost() + {cost} <= {snapshot.cost_budget};",
                      f"\teffect: route_open_side_passage() & route_open_time_side_passage() = now() + 1 & opportunity_count() = opportunity_count() + 1 & spent_cost() = spent_cost() + {cost} & now() = now() + 1" +
                      "".join(f" & possible_path({_name(source)}, {_name(target)})"
                              for route, source, target, changed, _ in snapshot.world_route_edges
                              if route == "side_passage" and changed) + ";",
                      "};"])
    # Ground only scene-bound actor/edge combinations. The previous generic
    # actor×place×place schemas created a large irrelevant event tree before
    # Sabre's configured node/time budgets begin.
    directed_pairs = sorted({(source, target) for _, source, target, _, _ in snapshot.world_route_edges})
    for actor in ("A", "B"):
        for source, target in directed_pairs:
            suffix = f"{actor}_{_name(source)}_{_name(target)}"
            lines.extend(["", f"action explore_{suffix}() {{", "\tprecondition:",
                          f"\t\tactor_ready({actor}) & at({actor}) == {_name(source)} & possible_path({_name(source)}, {_name(target)}) & !known_path({actor}, {_name(source)}, {_name(target)}) & now() <= actor_next({actor});",
                          f"\teffect: at({actor}) = {_name(target)} & known_path({actor}, {_name(source)}, {_name(target)}) & now() = actor_next({actor}) & actor_next({actor}) = actor_next({actor}) + 2;",
                          f"\tconsenting: {actor};", "};", "",
                          f"action move_{suffix}() {{", "\tprecondition:",
                          f"\t\tactor_ready({actor}) & at({actor}) == {_name(source)} & possible_path({_name(source)}, {_name(target)}) & known_path({actor}, {_name(source)}, {_name(target)}) & now() <= actor_next({actor});",
                          f"\teffect: at({actor}) = {_name(target)} & now() = actor_next({actor}) & actor_next({actor}) = actor_next({actor}) + 2;",
                          f"\tconsenting: {actor};", "};"])
    known_task_by_actor = {actor: (item, location, held)
                           for actor, item, location, held in snapshot.known_task_item_locations}
    for actor, item, _, _destination in snapshot.task_bindings:
        item_entity = item_entities[item]
        location = known_task_by_actor.get(actor, (item, None, False))[1]
        if location is None or known_task_by_actor.get(actor, (item, None, False))[2]:
            continue
        lines.extend(["", f"action get_item_{actor}() {{", "\tprecondition:",
                      f"\t\tactor_ready({actor}) & bound_item({actor}, {item_entity}) & !delivered({actor}, {item_entity}) & at({actor}) == {_name(location)} & item_at({item_entity}, {_name(location)}) & known_item_at({actor}, {item_entity}, {_name(location)}) & now() <= actor_next({actor});",
                      f"\teffect: held_by({item_entity}, {actor}) & !item_at({item_entity}, {_name(location)}) & now() = actor_next({actor}) & actor_next({actor}) = actor_next({actor}) + 2;",
                      f"\tconsenting: {actor};", "};"])
    for actor, item, _, _destination in snapshot.task_bindings:
        item_entity = item_entities[item]
        action_name = f"drop_item_{actor}"
        lines.extend(["", f"action {action_name}() {{", "\tprecondition:",
                      f"\t\tactor_ready({actor}) & bound_item({actor}, {item_entity}) & !delivered({actor}, {item_entity}) & task_destination({actor}, {_name(_destination)}) & at({actor}) == {_name(_destination)} & held_by({item_entity}, {actor}) & now() <= actor_next({actor});",
                      f"\teffect: item_at({item_entity}, {_name(_destination)}) & !held_by({item_entity}, {actor}) & delivered({actor}, {item_entity}) & delivery_time({actor}, {item_entity}) = actor_next({actor}) & delivery_sequence({actor}, {item_entity}) = event_sequence() + 1 & event_sequence() = event_sequence() + 1 & now() = actor_next({actor}) & actor_next({actor}) = actor_next({actor}) + 2;",
                      f"\tconsenting: {actor};", "};"])
    lines.extend(["",
                  "action request_note() {", "\tprecondition:",
                  "\t\tdelivered(A, Supply) & social_target_visible() & at(A) == at(B) & !note_attempted() & now() < horizon();",
                  "\teffect: note_attempted() & note_requested() & held_by(Note, B) & now() = now() + 1 & event_sequence() = event_sequence() + 1;", "};", "",
                  "action respond_note(value : response) {", "\tprecondition:",
                  "\t\tnote_requested() & held_by(Note, B) & !response_recorded() & now() <= horizon();",
                  "\teffect: response_recorded() & response_value() = value & response_time() = now() & response_sequence() = event_sequence() + 1 & event_sequence() = event_sequence() + 1;",
                  "};"])
    # Window checks are staged into two actions so the pinned Sabre numeric
    # simplifier never receives paired bounds on the same fluent. Event facts
    # and their timestamps are once-only/immutable before the second check.
    for clause_id, condition in supported_goals:
        if statuses.get(clause_id) == "SATISFIED":
            continue
        marker = _safe(clause_id)
        source = hard_goal_sources[clause_id]
        kind = source.get("kind")
        if kind == "event_by_deadline" and source.get("event") == "delivery_settled":
            actor, item = source["filters"].get("actor"), source["filters"].get("item")
            time = f"delivery_time({actor}, {item_entities[item]})"
            event_flag = f"delivered({actor}, {item_entities[item]})"
            final_filter = event_flag
        elif kind == "event_by_deadline":
            response = source.get("filters", {}).get("response")
            time = "response_time()"
            event_flag = "response_recorded()"
            final_filter = event_flag
            if response in {"accepted", "rejected"}:
                expected = "Accepted" if response == "accepted" else "Rejected"
                final_filter += f" & response_value() == {expected}"
        elif kind == "event_order":
            actor, item = source["before"]["filters"]["actor"], source["before"]["filters"]["item"]
            time = f"delivery_time({actor}, {item_entities[item]})"
            event_flag = f"delivered({actor}, {item_entities[item]})"
            final_filter = f"response_recorded() & {time} < response_time()"
            response = source["after"].get("filters", {}).get("response")
            if response in {"accepted", "rejected"}:
                final_filter += f" & response_value() == {'Accepted' if response == 'accepted' else 'Rejected'}"
        else:
            route = source.get("args", {}).get("route")
            time = f"route_open_time_{route}()"
            event_flag = f"route_open_{route}()"
            final_filter = event_flag
        lines.extend(["", f"action check_window_start_{marker}() {{", "\tprecondition:",
                      f"\t\t{event_flag} & !window_start_{marker}() & {time} >= {source['start']};",
                      f"\teffect: window_start_{marker}();", "};", ""])
        if kind == "event_order":
            response_filter = ""
            if response in {"accepted", "rejected"}:
                response_filter = f" & response_value() == {'Accepted' if response == 'accepted' else 'Rejected'}"
            lines.extend([f"action check_window_order_{marker}() {{", "\tprecondition:",
                          f"\t\twindow_start_{marker}() & !window_ordered_{marker}() & {final_filter};",
                          f"\teffect: window_ordered_{marker}();", "};", "",
                          f"action check_window_end_{marker}() {{", "\tprecondition:",
                          f"\t\twindow_ordered_{marker}() & !goal_{marker}() & response_recorded() & response_time() <= {source['deadline']}{response_filter};",
                          f"\teffect: window_{marker}() & goal_{marker}();", "};"])
        else:
            lines.extend([f"action check_window_end_{marker}() {{", "\tprecondition:",
                          f"\t\twindow_start_{marker}() & !goal_{marker}() & {final_filter} & {time} <= {source['deadline']};",
                          f"\teffect: window_{marker}() & goal_{marker}();", "};"])
    if not supported_goals:
        utility = "if(projection_complete() & no_hard_goal()) 1 else 0"
    else:
        utility = f"if(projection_complete() & {' & '.join(f'goal_{_safe(cid)}()' for cid, _ in supported_goals)}) 1 else 0"
    lines.extend(["", f"utility(): {utility};", "utility(A): if(delivered(A, Supply)) 1 else 0;",
                  "utility(B): if(delivered(B, Supply)) 1 elseif(delivered(B, Parcel)) 1 else 0;", "",
                  "/* Planner Adapter Integration v1. Sabre searches registered",
                  "   move/get/drop/request/conditional-response causal actions.",
                  "   Existing-task actions remain consenting character plans, not",
                  "   controller assignments. W possible_path is separate from each",
                  "   character's known_path. Callback-derived 2-minute actor primitive",
                  "   cadence is a conditional forecast. The note request/response",
                  "   are conditional native-social branches, not NPC commands or",
                  "   response guarantees. Only route operations",
                  "   are native-dispatchable; all other effects require later receipts. */"])
    for reason in residuals:
        lines.append(f"/* PROJECTION_RESIDUAL: {reason.replace('*/', '* /').replace(chr(10), ' ')} */")
    return "\n".join(lines) + "\n"


def invoke_sabre(problem_path: str | Path, *, timeout_s: float = 30.0) -> dict[str, Any]:
    problem = Path(problem_path).resolve()
    if not problem.is_file() or not JAVA.is_file() or not CLASSPATH.is_dir():
        return {"status": "SABRE_UNAVAILABLE", "problem_path": str(problem),
                "error": "integration problem, Java runtime, or Sabre classpath is missing"}
    command = [str(JAVA), f"-Xms{SEARCH_LIMITS['heap_min']}", f"-Xmx{SEARCH_LIMITS['heap_max']}",
               f"-Xss{SEARCH_LIMITS['stack_size']}", "-Duser.language=en", "-Duser.country=US",
               "-Duser.timezone=UTC", "-cp", str(CLASSPATH), "edu.uky.cs.nil.sabre.Main", "-v",
               "-p", str(problem), "-m", SEARCH_LIMITS["method"], "-c", SEARCH_LIMITS["cost"],
               "-h", SEARCH_LIMITS["heuristic"], "-el", str(SEARCH_LIMITS["epistemic_limit"]),
               "-vl", str(SEARCH_LIMITS["max_visited"]), "-gl", str(SEARCH_LIMITS["max_generated"]),
               "-tl", str(SEARCH_LIMITS["time_limit_ms"]), "-atl", str(SEARCH_LIMITS["author_limit"]),
               "-ctl", str(SEARCH_LIMITS["character_limit"])]
    try:
        completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                                   timeout=timeout_s, check=False)
    except subprocess.TimeoutExpired as exc:
        return {"status": "PROCESS_TIMEOUT", "command": command,
                "stdout": exc.stdout or "", "stderr": exc.stderr or ""}
    parsed = parse_native_output(completed.stdout, completed.stderr)
    return {**parsed, "command": command, "returncode": completed.returncode,
            "stdout": completed.stdout, "stderr": completed.stderr}


def decode_plan(actions: list[str], *, native_status: str | None = None) -> dict[str, Any]:
    """Classify the ordered Sabre plan; only registered author ops dispatch."""
    if not isinstance(actions, list) or any(not isinstance(row, str) for row in actions):
        raise TypeError("actions must be a list of Sabre action strings")
    first = actions[0] if actions else None
    dispatch_action = first if first in {"open_main_passage()", "open_side_passage()"} else None
    if native_status is not None and native_status != "PLAN_FOUND_NOT_EXECUTION_EVIDENCE":
        dispatch_action = None
    actor_action_rows = [row for row in actions if row.startswith(("get_item_", "move_", "explore_",
                                                                    "drop_item_", "request_note(", "respond_note("))]
    actor_chain = bool(actor_action_rows)
    actor_steps = []
    for index, action in enumerate(actions):
        if action not in actor_action_rows:
            continue
        actor_match = re.search(r"(?:get_item|drop_item|move|explore)_([AB])(?:_|\()", action)
        actor = actor_match.group(1) if actor_match else ("A" if action.startswith("request_note") else "B")
        actor_steps.append({"index": index, "action": action, "actor": actor,
                            "item": ("Supply" if "Supply" in action or actor == "A" and action.startswith(("get_item_", "drop_item_")) else
                                     "Parcel" if actor == "B" and action.startswith(("get_item_", "drop_item_")) else None),
                            "phase": ("get" if action.startswith("get_item_") else
                                      "move_or_explore" if action.startswith(("move_", "explore_")) else
                                      "delivery" if action.startswith("drop_item_") else
                                      "social_request" if action.startswith("request_note") else "social_response"),
                            "evidence_class": "SABRE_COUNTERFACTUAL_PREDICTION_ONLY",
                            "dispatchable": False})
    evidence_status = "PLAN_FOUND_NOT_EXECUTION_EVIDENCE" if actions else "NO_CANDIDATE"
    if native_status is not None and native_status != "PLAN_FOUND_NOT_EXECUTION_EVIDENCE":
        evidence_status = "NO_CANDIDATE"
    return {"ordered_actions": list(actions), "first_action": first,
            "native_dispatchable": dispatch_action is not None,
            "dispatch_action": dispatch_action,
            "conditional_actor_task_chain": actor_chain,
            "actor_task_steps": actor_steps,
            "handoff_status": "PREDICTION_ONLY_NOT_DISPATCHED",
            "prediction_only_actions": [row for row in actions if row != dispatch_action],
            "evidence_status": evidence_status}


def projection_status(snapshot: PlannerSnapshot) -> dict[str, Any]:
    """Fail-closed runner gate derived from this renderer's exact projection."""
    if not isinstance(snapshot, PlannerSnapshot):
        raise TypeError("projection_status requires a validated integration-v1 snapshot")
    task_bindings = {actor: (item, item_id, destination)
                     for actor, item, item_id, destination in snapshot.task_bindings}
    statuses = dict(snapshot.constraint_statuses)
    route_open = dict(snapshot.route_open)
    actor_rooms = dict(snapshot.actor_rooms)
    hard_residuals = []
    for clause_id, _kind, _start, end, source in snapshot.hard_requirements:
        if statuses.get(clause_id) == "SATISFIED":
            continue
        source_data = json.loads(source)
        if (source_data.get("kind") == "event_by_deadline"
                and source_data.get("event") == "note_response"
                and (not snapshot.social_target_visible or actor_rooms.get("A") != actor_rooms.get("B"))):
            hard_residuals.append(f"{clause_id}: conditional native request requires A-visible, co-located B in current actor-local O")
            continue
        condition, reason = _req_goal(clause_id, source, task_bindings, route_open=route_open, now=snapshot.minute)
        if condition is None:
            hard_residuals.append(f"{clause_id}: {reason}")
        elif statuses.get(clause_id) == "VIOLATED" and snapshot.minute > end:
            hard_residuals.append(f"{clause_id}: native hard window is irrecoverably violated")
    hard_projection_residuals = [reason for reason in snapshot.projection_residuals
                                 if not reason.startswith("soft constraint ")]
    wait_reasons = [reason for reason in snapshot.projection_residuals
                    if "pending" in reason or "stale" in reason or "observation is missing" in reason]
    return {"dispatchable": not hard_residuals and not hard_projection_residuals and not wait_reasons,
            "hard_residuals": hard_residuals + hard_projection_residuals,
            "informational_residuals": [reason for reason in snapshot.projection_residuals
                                         if reason.startswith("soft constraint ")],
            "wait_reason": wait_reasons or None,
            "bundle_id": snapshot.bundle_id, "bundle_version": snapshot.bundle_version,
            "scene_id": snapshot.scene_id, "minute": snapshot.minute,
            "source_trace_sha256": snapshot.source_trace_sha256,
            "source_bundle_sha256": snapshot.source_bundle_sha256,
            "renderer_version": snapshot.renderer_version}


__all__ = ["SEARCH_LIMITS", "render_problem", "projection_status", "invoke_sabre", "decode_plan"]
