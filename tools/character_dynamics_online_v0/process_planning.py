"""Shared multi-actor HTN refinement over adapter-projected facts/actions.

The planner predicts only in a disposable GTPyhop state. The online controller
advances persistent progress only after correlated execution feedback.
"""
from __future__ import annotations

import json
import os
import threading
from collections.abc import Mapping, Sequence
from contextlib import redirect_stdout
from io import StringIO
from itertools import permutations
from typing import Any

from .contracts import ContractError, finite_number, json_safe, nonempty

_LOCK = threading.RLock()


def _fact_key(value: object, label: str) -> str:
    if not isinstance(value, Mapping) or set(value) != {"predicate", "args"}:
        raise ContractError(f"{label} must contain predicate and args")
    predicate = nonempty(value["predicate"], f"{label}.predicate")
    args = value["args"]
    if not isinstance(args, Sequence) or isinstance(args, (str, bytes)):
        raise ContractError(f"{label}.args must be an array")
    try:
        return json.dumps([predicate, json_safe(list(args))], sort_keys=True,
                          separators=(",", ":"), ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{label} is not JSON-safe") from exc


def _decode_fact(key: str) -> dict[str, Any]:
    predicate, args = json.loads(key)
    return {"predicate": predicate, "args": args}


def validate_process_observations(observations: object, game_time: float) -> dict[int, dict[str, Any]]:
    if not isinstance(observations, Mapping) or set(observations) != {
            "schema", "game_time", "actors", "world_facts", "event_coverage_through"}:
        raise ContractError("observations must match character_dynamics_g1_observation_v0")
    if observations["schema"] != "character_dynamics_g1_observation_v0":
        raise ContractError("unsupported G1 observation schema")
    if (not finite_number(observations["game_time"])
            or float(observations["game_time"]) != float(game_time)):
        raise ContractError("observation game_time must equal the decision game_time")
    actors = observations["actors"]
    if not isinstance(actors, Sequence) or isinstance(actors, (str, bytes)):
        raise ContractError("observations.actors must be an array")
    decoded: dict[int, dict[str, Any]] = {}
    for row in actors:
        if not isinstance(row, Mapping) or set(row) != {
                "actor_uid", "observation_id", "facts", "action_models"}:
            raise ContractError("each actor observation needs actor_uid, observation_id, facts, action_models")
        actor_uid = row["actor_uid"]
        if type(actor_uid) is not int or actor_uid < 0 or actor_uid in decoded:
            raise ContractError("actor_uid must be unique and non-negative")
        observation_id = nonempty(row["observation_id"], "actor observation_id")
        facts = row["facts"]
        if not isinstance(facts, Sequence) or isinstance(facts, (str, bytes)):
            raise ContractError("actor facts must be an array")
        true_facts: set[str] = set()
        unknown_facts: set[str] = set()
        for fact in facts:
            if not isinstance(fact, Mapping) or set(fact) != {"predicate", "args", "value"}:
                raise ContractError("observed facts need predicate, args, and tri-state value")
            key = _fact_key({"predicate": fact["predicate"], "args": fact["args"]}, "actor fact")
            if fact["value"] is True:
                true_facts.add(key)
            elif fact["value"] is None:
                unknown_facts.add(key)
            elif fact["value"] is not False:
                raise ContractError("fact value must be true, false, or null for unknown")
        catalog = row["action_models"]
        if not isinstance(catalog, Sequence) or isinstance(catalog, (str, bytes)):
            raise ContractError("action_models must be an array")
        clean_catalog: dict[str, dict[str, Any]] = {}
        for action in catalog:
            if not isinstance(action, Mapping) or set(action) - {
                    "primitive", "args", "preconditions", "dispatch_preconditions",
                    "effects", "estimated_cost", "provenance"} or not {
                    "primitive", "args", "preconditions", "effects", "estimated_cost", "provenance"}.issubset(action):
                raise ContractError("action model needs primitive, args, preconditions, effects, estimated_cost, provenance, and optional dispatch_preconditions")
            primitive = nonempty(action["primitive"], "primitive")
            args = json_safe(action["args"])
            if not isinstance(args, (list, dict)):
                raise ContractError("primitive args must be a JSON array or object")
            preconditions = action["preconditions"]
            dispatch_preconditions = action.get("dispatch_preconditions", [])
            effects = action["effects"]
            if not isinstance(preconditions, Sequence) or isinstance(preconditions, (str, bytes)):
                raise ContractError("primitive preconditions must be an array")
            if not isinstance(dispatch_preconditions, Sequence) or isinstance(dispatch_preconditions, (str, bytes)):
                raise ContractError("dispatch_preconditions must be an array")
            if not isinstance(effects, Sequence) or isinstance(effects, (str, bytes)) or not effects:
                raise ContractError("primitive effects must be a non-empty array")
            if not finite_number(action["estimated_cost"]) or action["estimated_cost"] < 0:
                raise ContractError("estimated_cost must be finite and non-negative")
            if not isinstance(action["provenance"], Mapping):
                raise ContractError("primitive provenance must be an object")
            pre_keys = tuple(_fact_key(fact, "primitive precondition") for fact in preconditions)
            dispatch_pre_keys = tuple(_fact_key(fact, "primitive dispatch precondition")
                                      for fact in dispatch_preconditions)
            effect_keys = tuple(_fact_key(fact, "primitive effect") for fact in effects)
            key = json.dumps([primitive, args], sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            if key in clean_catalog:
                raise ContractError("duplicate primitive descriptor")
            clean_catalog[key] = {"key": key, "primitive": primitive, "args": args,
                                  "preconditions": pre_keys, "effects": effect_keys,
                                  "dispatch_preconditions": dispatch_pre_keys,
                                  "estimated_cost": float(action["estimated_cost"]),
                                  "provenance": json_safe(action["provenance"])}
        decoded[actor_uid] = {"actor_uid": actor_uid, "observation_id": observation_id,
                              "facts": true_facts, "unknown_facts": unknown_facts,
                              "catalog": clean_catalog}
    world_facts = observations["world_facts"]
    if not isinstance(world_facts, Sequence) or isinstance(world_facts, (str, bytes)):
        raise ContractError("world_facts must be an array")
    for fact in world_facts:
        if not isinstance(fact, Mapping) or set(fact) != {"predicate", "args", "value"}:
            raise ContractError("world facts need predicate, args, and tri-state value")
        if fact["value"] not in (True, False, None):
            raise ContractError("world fact value must be tri-state")
        _fact_key({"predicate": fact["predicate"], "args": fact["args"]}, "world fact")
    coverage = observations["event_coverage_through"]
    if coverage is not None and (not finite_number(coverage) or coverage < 0 or coverage > game_time):
        raise ContractError("event_coverage_through must be within current absolute game time")
    return decoded


def plan_fact_goals(actor: dict[str, Any], goals: Sequence[Mapping[str, Any]], *,
                    ordered_groups: Sequence[Sequence[Mapping[str, Any]]] = (),
                    timeout_ms: int = 250) -> dict[str, Any]:
    """Use GTPyhop to refine typed facts into a multi-step primitive plan."""
    # Build a disposable catalog. Event-order constraints become preconditions
    # of every producer for each strict successor, so recursive refinement
    # cannot satisfy an authored A-before-B edge by producing B first while
    # trying to achieve A.
    catalog: dict[str, dict[str, Any]] = {}
    order_preconditions: dict[str, set[str]] = {}
    for group in ordered_groups:
        keys = [_fact_key(goal, "ordered goal fact") for goal in group]
        for first, second in zip(keys, keys[1:]):
            order_preconditions.setdefault(second, set()).add(first)
    for key, source_action in actor["catalog"].items():
        action = dict(source_action)
        extra = {before for effect in action["effects"]
                 for before in order_preconditions.get(effect, ())}
        action["preconditions"] = tuple(sorted(set(action["preconditions"]) | extra))
        catalog[key] = action
    facts = set(actor["facts"])
    goal_keys = tuple(_fact_key(goal, "goal fact") for goal in goals)
    ordered_keys = [tuple(_fact_key(goal, "ordered goal fact") for goal in group)
                    for group in ordered_groups]
    if not goal_keys and not any(ordered_keys):
        return {"status": "SATISFIED", "steps": [], "planner": "gtpyhop-core-2.0.2"}
    producers: dict[str, list[str]] = {}
    for action_key, action in catalog.items():
        for effect in action["effects"]:
            producers.setdefault(effect, []).append(action_key)
    for options in producers.values():
        options.sort(key=lambda key: (catalog[key]["estimated_cost"], key))
    os.environ.setdefault("GTPYHOP_QUIET", "true")
    try:
        import gtpyhop as g
        import gtpyhop.main as main
    except ImportError as exc:
        raise RuntimeError("process HTN requires local gtpyhop-core==2.0.2") from exc

    class State:
        pass

    state = g.State("character-dynamics-process-v0")
    state.facts = tuple(sorted(facts))
    state.catalog = catalog
    state.producers = producers

    def apply_primitive(current, action_key):
        action = current.catalog.get(action_key)
        if action is None or not set(action["preconditions"]).issubset(set(current.facts)):
            return False
        current.facts = tuple(sorted(set(current.facts) | set(action["effects"])))
        return current

    def producer_method(action_key):
        def method(current, fact_key, path):
            if fact_key in set(current.facts):
                return []
            if fact_key in path or action_key not in current.producers.get(fact_key, []):
                return None
            return [("prepare_primitive", action_key, path + (fact_key,))]
        return method

    def satisfy_fact(current, fact_key, path):
        # A task-method return list is a sequence in GTPyhop, not an OR-list.
        # Each producer is therefore registered as its own backtracking method.
        return [] if fact_key in set(current.facts) else None

    def prepare_primitive(current, action_key, path):
        action = current.catalog.get(action_key)
        if action is None:
            return None
        tasks = [("satisfy_fact", fact_key, path) for fact_key in action["preconditions"]
                 if fact_key not in set(current.facts)]
        tasks.append(("apply_primitive", action_key))
        return tasks

    def achieve_all(current, fact_keys):
        missing = [key for key in fact_keys if key not in set(current.facts)]
        if not missing:
            return []
        # Logical conjunction has no authored order. Try cheaper first-step
        # choices first, leaving GTPyhop to backtrack if a dependency conflicts.
        cost = {fact: min((current.catalog[key]["estimated_cost"]
                           for key in current.producers.get(fact, [])), default=float("inf"))
                for fact in missing}
        ordered = sorted(missing, key=lambda fact: (cost[fact], fact))
        return [("satisfy_fact", fact, ()) for fact in ordered]

    def achieve_ordered(current, fact_keys):
        return [("satisfy_fact", fact, ()) for fact in fact_keys]

    with _LOCK, redirect_stdout(StringIO()):
        previous = main.current_domain
        try:
            domain = g.Domain("character-dynamics-process-v0")
            g.declare_actions(apply_primitive)
            g.declare_task_methods("achieve_all", achieve_all)
            g.declare_task_methods("achieve_ordered", achieve_ordered)
            methods = [producer_method(key) for key in
                       sorted({key for options in producers.values() for key in options})]
            g.declare_task_methods("satisfy_fact", satisfy_fact, *methods)
            g.declare_task_methods("prepare_primitive", prepare_primitive)
            with g.PlannerSession(domain=domain, strategy="iterative_dfs_backtracking",
                                  verbose=0, structured_logging=False) as planner:
                # Explicit author ordering constraints precede unordered AND
                # goals, so a state goal cannot accidentally plan the second
                # event before the event_before first endpoint.
                tasks = [("achieve_ordered", group) for group in ordered_keys if group]
                if goal_keys:
                    tasks.append(("achieve_all", goal_keys))
                result = planner.find_plan(state, tasks, timeout_ms=timeout_ms)
        finally:
            main.current_domain = previous
    if not result.success:
        unknown = [_decode_fact(key) for key in goal_keys
                   if key in actor["unknown_facts"]]
        timed_out = bool(result.error and "timeout" in result.error.casefold())
        return {"status": ("PLANNING_BUDGET_EXHAUSTED" if timed_out else
                            "UNKNOWN" if unknown else "BLOCKED"),
                "reason": (result.error if timed_out else
                           "goal facts are unknown in this actor view" if unknown else
                           "GTPyhop found no applicable primitive refinement"),
                "unknown_goals": unknown,
                "planner": "gtpyhop-core-2.0.2", "planner_error": result.error,
                "planner_stats": result.stats}
    steps: list[dict[str, Any]] = []
    for task, *args in result.plan:
        if task != "apply_primitive" or not args:
            return {"status": "BLOCKED", "reason": "unsupported GTPyhop plan node",
                    "planner": "gtpyhop-core-2.0.2"}
        action = catalog[args[0]]
        steps.append({"primitive": action["primitive"], "args": action["args"],
                      "preconditions": [_decode_fact(key) for key in action["preconditions"]],
                      "dispatch_preconditions": [_decode_fact(key) for key in action["dispatch_preconditions"]],
                      "effects": [_decode_fact(key) for key in action["effects"]],
                      "estimated_cost": action["estimated_cost"],
                      "provenance": action["provenance"], "catalog_key": args[0]})
    return {"status": "PLANNED", "steps": steps,
            "planner": "gtpyhop-core-2.0.2", "task": "achieve_all",
                "goal_facts": [_decode_fact(key) for key in goal_keys],
                "ordered_groups": [[_decode_fact(key) for key in group]
                                   for group in ordered_keys]}
