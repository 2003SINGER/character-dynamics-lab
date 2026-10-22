"""One persistent multi-actor process controller with versioned author goals."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

from .contracts import ContractError, finite_number, json_safe, nonempty, uid
from .process_planning import (_decode_fact, _fact_key, plan_fact_goals,
                               validate_process_observations)

_AUTHOR_STATE_SELECTORS = {
    "survey_completed": 1,
    "report_delivered": 2,
    "report_known": 2,
    "known_report_from": 3,
    "hired_follower": 2,
    "rally_completed": 2,
}
_AUTHOR_EVENT_SELECTORS = {
    "g1_survey_completed", "g1_report_delivered", "g1_rally_completed",
    "native_recruit_job_observed",
}


def _validate_actor_goals(actor_uids: set[int], goal_specs: object) -> list[dict[str, Any]]:
    if not isinstance(goal_specs, Sequence) or isinstance(goal_specs, (str, bytes)):
        raise ContractError("goal_specs must be an array")
    result = []
    seen: set[str] = set()
    for spec in goal_specs:
        if not isinstance(spec, Mapping) or set(spec) - {"goal_id", "actor_uid", "goals", "ordered_groups", "source"}:
            raise ContractError("actor goal spec has unsupported fields")
        goal_id = nonempty(spec.get("goal_id"), "goal_id")
        actor_uid = uid(spec.get("actor_uid"), "goal actor_uid")
        if actor_uid not in actor_uids:
            raise ContractError("goal actor_uid must belong to this session")
        if goal_id in seen:
            raise ContractError("goal_id must be unique")
        seen.add(goal_id)
        goals = spec.get("goals")
        if not isinstance(goals, Sequence) or isinstance(goals, (str, bytes)):
            raise ContractError("actor goal goals must be an array")
        for fact in goals:
            _fact_key(fact, "actor goal fact")
        ordered_groups = spec.get("ordered_groups", [])
        if not isinstance(ordered_groups, Sequence) or isinstance(ordered_groups, (str, bytes)):
            raise ContractError("ordered_groups must be an array")
        clean_groups = []
        for group in ordered_groups:
            if not isinstance(group, Sequence) or isinstance(group, (str, bytes)):
                raise ContractError("ordered goal group must be an array")
            for fact in group:
                _fact_key(fact, "ordered actor goal fact")
            clean_groups.append(json_safe(group))
        source = spec.get("source", "ACTOR")
        if source != "ACTOR":
            raise ContractError("role-owned goal specs must have source ACTOR")
        result.append({"goal_id": goal_id, "actor_uid": actor_uid,
                       "goals": json_safe(goals), "ordered_groups": clean_groups,
                       "source": "ACTOR"})
    return result


def new_process_session(actor_uids: Sequence[int], *,
                        goal_specs: Sequence[Mapping[str, Any]] = (),
                        director_enabled: bool = True) -> dict[str, Any]:
    if not isinstance(actor_uids, Sequence) or isinstance(actor_uids, (str, bytes)) or not actor_uids:
        raise ContractError("actor_uids must be a non-empty array")
    clean_uids = [uid(value, "actor_uid") for value in actor_uids]
    if len(set(clean_uids)) != len(clean_uids):
        raise ContractError("actor_uids must be unique")
    if type(director_enabled) is not bool:
        raise ContractError("director_enabled must be a boolean")
    goals = _validate_actor_goals(set(clean_uids), goal_specs)
    return {
        "schema": "character_dynamics_online_process_v0",
        "actor_uids": clean_uids,
        "director_enabled": director_enabled,
        "actor_goal_specs": goals,
        "author_obligations": {},
        "plans": {},
        "inflight_by_actor": {},
        "native_history": [],
        "native_receipt_ids": [],
        "native_effect_ids": [],
        "decision_sequence": 0,
        "observation_ids": {},
        "history": [],
    }


def _event_facts(node: Mapping[str, Any]) -> dict[str, Any]:
    return {"predicate": f"event:{node['event']}", "args": json_safe(node.get("args", []))}


def _validate_event(node: object, label: str) -> dict[str, Any]:
    if not isinstance(node, Mapping) or set(node) - {"event", "args"} or "event" not in node:
        raise ContractError(f"{label} must contain event and optional args")
    event = nonempty(node["event"], f"{label}.event")
    if event not in _AUTHOR_EVENT_SELECTORS:
        raise ContractError("unsupported author event selector")
    args = node.get("args", [])
    if not isinstance(args, Sequence) or isinstance(args, (str, bytes)):
        raise ContractError(f"{label}.args must be an array")
    return {"event": event, "args": json_safe(args)}


def _validate_ast(ast: object) -> dict[str, Any]:
    if not isinstance(ast, Mapping) or not isinstance(ast.get("op"), str):
        raise ContractError("author AST node must be an object with op")
    op = ast["op"]
    if op == "and":
        if set(ast) != {"op", "children"}:
            raise ContractError("and AST requires exactly op and children")
        children = ast["children"]
        if not isinstance(children, Sequence) or isinstance(children, (str, bytes)) or not children:
            raise ContractError("and.children must be a non-empty array")
        return {"op": op, "children": [_validate_ast(child) for child in children]}
    if op == "or":
        if set(ast) != {"op", "children"}:
            raise ContractError("or AST requires exactly op and children")
        children = ast["children"]
        if not isinstance(children, Sequence) or isinstance(children, (str, bytes)) or not children:
            raise ContractError("or.children must be a non-empty array")
        return {"op": op, "children": [_validate_ast(child) for child in children]}
    if op == "state":
        if set(ast) != {"op", "predicate", "args"}:
            raise ContractError("state AST requires predicate and args")
        fact = {"predicate": nonempty(ast["predicate"], "state.predicate"),
                "args": json_safe(ast["args"])}
        if not isinstance(fact["args"], list):
            raise ContractError("state.args must be an array")
        if (_AUTHOR_STATE_SELECTORS.get(fact["predicate"]) is None
                or len(fact["args"]) != _AUTHOR_STATE_SELECTORS[fact["predicate"]]):
            raise ContractError("unsupported author state selector or argument arity")
        _fact_key(fact, "author state goal")
        return {"op": op, **fact}
    if op == "event_before":
        if set(ast) != {"op", "first", "second"}:
            raise ContractError("event_before AST requires first and second events")
        return {"op": op, "first": _validate_event(ast["first"], "event_before.first"),
                "second": _validate_event(ast["second"], "event_before.second")}
    if op == "deadline":
        if set(ast) != {"op", "event", "at"}:
            raise ContractError("deadline AST requires event and absolute at")
        if not finite_number(ast["at"]) or ast["at"] < 0:
            raise ContractError("deadline.at must be an absolute non-negative game time")
        return {"op": op, "event": _validate_event(ast["event"], "deadline.event"),
                "at": float(ast["at"])}
    raise ContractError(f"unsupported author AST op: {op}")


def _ast_to_plan(ast: Mapping[str, Any],
                 native_history: Sequence[Mapping[str, Any]] = (), *,
                 now: float | None = None, world_facts: set[str] | None = None,
                 coverage: float | None = None) -> tuple[list[dict[str, Any]], list[list[dict[str, Any]]]]:
    if ast["op"] == "state":
        return [{"predicate": ast["predicate"], "args": ast["args"]}], []
    if ast["op"] == "deadline":
        return [_event_facts(ast["event"])], []
    if ast["op"] == "event_before":
        first, second = _event_facts(ast["first"]), _event_facts(ast["second"])
        first_times = _event_times(ast["first"], native_history)
        second_times = _event_times(ast["second"], native_history)
        # An already witnessed second endpoint cannot be repaired by issuing
        # the first action afterward. Keep the obligation in monitoring, but
        # do not generate a plan that silently violates the order.
        if second_times and (not first_times or min(second_times) <= min(first_times)):
            return [], []
        if first_times:
            return [second], []
        return [], [[first, second]]
    if ast["op"] == "or":
        # OR is a choice, not a conjunction. Preserve every disjunct in the
        # monitor, but refine only the first still-possible branch. Expired
        # branches are never sent to DIRECTOR as future work.
        verdicts = [_monitor_ast(child, world_facts=world_facts or set(),
                                 native_history=native_history,
                                 now=0.0 if now is None else now,
                                 coverage=coverage) for child in ast["children"]]
        if any(item["status"] == "SATISFIED" for item in verdicts):
            return [], []
        for child, verdict in zip(ast["children"], verdicts):
            if verdict.get("feasibility") == "EXPIRED" or verdict["status"] == "VIOLATED":
                continue
            return _ast_to_plan(child, native_history, now=now,
                                world_facts=world_facts, coverage=coverage)
        return [], []
    goals: list[dict[str, Any]] = []
    groups: list[list[dict[str, Any]]] = []
    for child in ast["children"]:
        child_goals, child_groups = _ast_to_plan(child, native_history, now=now,
                                                world_facts=world_facts, coverage=coverage)
        goals.extend(child_goals)
        groups.extend(child_groups)
    return goals, _merge_ordered_groups(groups)


def _merge_ordered_groups(groups: Sequence[Sequence[Mapping[str, Any]]]) -> list[list[dict[str, Any]]]:
    """Merge event_before pairs into one deterministic DAG linearization."""
    edges: dict[str, set[str]] = {}
    descriptors: dict[str, dict[str, Any]] = {}
    indegree: dict[str, int] = {}
    for group in groups:
        keys = [_fact_key(fact, "ordered event fact") for fact in group]
        for key, fact in zip(keys, group):
            descriptors[key] = json_safe(fact)
            indegree.setdefault(key, 0)
        for left, right in zip(keys, keys[1:]):
            children = edges.setdefault(left, set())
            if right not in children:
                children.add(right)
                indegree[right] = indegree.get(right, 0) + 1
    ready = sorted(key for key, degree in indegree.items() if degree == 0)
    ordered: list[str] = []
    while ready:
        key = ready.pop(0)
        ordered.append(key)
        for child in sorted(edges.get(key, ())):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
                ready.sort()
    if len(ordered) != len(indegree):
        # The controller's cross-obligation conflict checker will report the
        # typed conflict. Returning no misleading order prevents fake SAT.
        return []
    return [[descriptors[key] for key in ordered]] if ordered else []


def _collect_ast_nodes(ast: Mapping[str, Any], op: str) -> list[Mapping[str, Any]]:
    if ast["op"] == op:
        return [ast]
    if ast["op"] in ("and", "or"):
        return [item for child in ast["children"] for item in _collect_ast_nodes(child, op)]
    return []


def _active_ast_nodes(ast: Mapping[str, Any], op: str, *, world_facts: set[str],
                      native_history: Sequence[Mapping[str, Any]], now: float,
                      coverage: float | None) -> list[Mapping[str, Any]]:
    """Collect nodes on the active Boolean path; OR contributes one viable branch."""
    if ast["op"] == op:
        return [ast]
    if ast["op"] == "and":
        return [node for child in ast["children"]
                for node in _active_ast_nodes(child, op, world_facts=world_facts,
                                               native_history=native_history, now=now,
                                               coverage=coverage)]
    if ast["op"] == "or":
        verdicts = [_monitor_ast(child, world_facts=world_facts,
                                 native_history=native_history, now=now,
                                 coverage=coverage) for child in ast["children"]]
        if any(item["status"] == "SATISFIED" for item in verdicts):
            return []
        for child, verdict in zip(ast["children"], verdicts):
            if verdict.get("feasibility") != "EXPIRED" and verdict["status"] != "VIOLATED":
                return _active_ast_nodes(child, op, world_facts=world_facts,
                                         native_history=native_history, now=now,
                                         coverage=coverage)
    return []


def _event_order_edges(ast: Mapping[str, Any], *, world_facts: set[str] | None = None,
                       native_history: Sequence[Mapping[str, Any]] = (), now: float = 0.0,
                       coverage: float | None = None) -> list[tuple[str, str]]:
    def event_identity(event: Mapping[str, Any]) -> str:
        return json.dumps([event["event"], event.get("args", [])], sort_keys=True,
                          separators=(",", ":"), ensure_ascii=False)
    edges = [(event_identity(node["first"]), event_identity(node["second"]))
             for node in _active_ast_nodes(ast, "event_before", world_facts=world_facts or set(),
                                            native_history=native_history, now=now,
                                            coverage=coverage)]
    return edges


def _has_order_cycle(obligations: Sequence[Mapping[str, Any]], *,
                     world_facts: set[str] | None = None,
                     native_history: Sequence[Mapping[str, Any]] = (), now: float = 0.0,
                     coverage: float | None = None) -> bool:
    graph: dict[str, set[str]] = {}
    for item in obligations:
        for left, right in _event_order_edges(
                item["ast"], world_facts=world_facts, native_history=native_history,
                now=now, coverage=coverage):
            graph.setdefault(left, set()).add(right)
            graph.setdefault(right, set())
    visiting: set[str] = set()
    visited: set[str] = set()
    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(visit(child) for child in graph.get(node, ())):
            return True
        visiting.remove(node)
        visited.add(node)
        return False
    return any(visit(node) for node in graph if node not in visited)


def _fact_present(fact: Mapping[str, Any], fact_set: set[str]) -> bool:
    return _fact_key(fact, "monitor fact") in fact_set


def _event_times(event: Mapping[str, Any], history: Sequence[Mapping[str, Any]]) -> list[float]:
    key = _fact_key(_event_facts(event), "event fact")
    return sorted(float(row["game_time"]) for row in history
                  if row.get("matched") is True and key in row.get("facts", []))


def _monitor_ast(ast: Mapping[str, Any], *, world_facts: set[str],
                 native_history: Sequence[Mapping[str, Any]], now: float,
                 coverage: float | None) -> dict[str, Any]:
    op = ast["op"]
    if op == "and":
        rows = [_monitor_ast(child, world_facts=world_facts, native_history=native_history,
                             now=now, coverage=coverage) for child in ast["children"]]
        status = ("VIOLATED" if any(row["status"] == "VIOLATED" for row in rows) else
                  "SATISFIED" if all(row["status"] == "SATISFIED" for row in rows) else
                  "UNKNOWN" if any(row["status"] == "UNKNOWN" for row in rows) else "PENDING")
        feasibility = ("EXPIRED" if any(row.get("feasibility") == "EXPIRED" for row in rows) else
                       "SATISFIED" if status == "SATISFIED" else "UNCERTAIN")
        return {"status": status, "feasibility": feasibility, "children": rows}
    if op == "or":
        rows = [_monitor_ast(child, world_facts=world_facts, native_history=native_history,
                             now=now, coverage=coverage) for child in ast["children"]]
        if any(row["status"] == "SATISFIED" for row in rows):
            status = "SATISFIED"
        elif any(row["status"] in ("PENDING", "UNKNOWN") for row in rows):
            status = "UNKNOWN" if any(row["status"] == "UNKNOWN" for row in rows) else "PENDING"
        else:
            status = "VIOLATED"
        feasibility = ("SATISFIED" if status == "SATISFIED" else
                       "UNCERTAIN" if any(row.get("feasibility") != "EXPIRED"
                                          for row in rows) else "EXPIRED")
        return {"status": status, "feasibility": feasibility, "children": rows}
    if op == "state":
        fact = {"predicate": ast["predicate"], "args": ast["args"]}
        if _fact_present(fact, world_facts):
            return {"status": "SATISFIED", "witness": fact}
        # Author monitor receives explicit world facts but never assumes an
        # omitted state is false.
        if now >= 0:
            return {"status": "UNKNOWN", "reason": "state predicate is not witnessed by author-monitor evidence"}
    if op == "event_before":
        left = _event_times(ast["first"], native_history)
        right = _event_times(ast["second"], native_history)
        if left and right:
            if min(left) < min(right):
                return {"status": "SATISFIED", "first_at": min(left), "second_at": min(right)}
            if coverage is not None and coverage >= min(right):
                return {"status": "VIOLATED", "reason": "second event preceded first under complete native event coverage"}
            return {"status": "UNKNOWN", "reason": "event order conflicts with the first observed timestamps; coverage is incomplete"}
        if right and not left:
            if coverage is not None and coverage >= min(right):
                return {"status": "VIOLATED", "reason": "second event preceded first under complete native event coverage"}
            return {"status": "UNKNOWN", "reason": "second event is observed but earlier event coverage is incomplete"}
        return {"status": "PENDING", "first_at": min(left) if left else None,
                "second_at": min(right) if right else None}
    if op == "deadline":
        times = _event_times(ast["event"], native_history)
        if any(value <= ast["at"] for value in times):
            return {"status": "SATISFIED", "event_at": min(value for value in times if value <= ast["at"]),
                    "deadline": ast["at"], "feasibility": "SATISFIED"}
        if now <= ast["at"]:
            return {"status": "PENDING", "deadline": ast["at"],
                    "feasibility": "UNCERTAIN",
                    "reason": "remaining time is known but action duration is not modeled in game seconds"}
        # Once absolute time is strictly beyond the deadline, the event can no
        # longer satisfy this version regardless of event-log coverage. A late
        # witness does not retroactively meet the deadline.
        late_times = [value for value in times if value > ast["at"]]
        complete = coverage is not None and coverage >= ast["at"]
        if complete:
            return {"status": "VIOLATED", "deadline": ast["at"],
                    "feasibility": "EXPIRED",
                    "late_witness_at": min(late_times) if late_times else None,
                    "reason": "complete event coverage reached deadline without a timely witness"}
        return {"status": "UNKNOWN", "deadline": ast["at"],
                "feasibility": "EXPIRED",
                "late_witness_at": min(late_times) if late_times else None,
                "reason": "deadline passed; future completion is impossible, but historical coverage is incomplete"}
    return {"status": "UNKNOWN", "reason": "unsupported monitor node"}


def _validate_command(command: object, session: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(command, Mapping) or set(command) != {"op", "goal_id", "version", "actor_uid", "ast"}:
        raise ContractError("author command requires op, goal_id, version, actor_uid, ast")
    op = command["op"]
    if op not in ("append", "edit"):
        raise ContractError("author command op must be append or edit")
    goal_id = nonempty(command["goal_id"], "goal_id")
    actor_uid = uid(command["actor_uid"], "author goal actor_uid")
    if actor_uid not in session["actor_uids"]:
        raise ContractError("author goal actor_uid must belong to this process session")
    existing = session["author_obligations"].get(goal_id)
    if op == "append" and existing is not None:
        raise ContractError("append cannot replace an existing goal_id")
    if op == "edit" and existing is None:
        raise ContractError("edit requires an existing goal_id")
    version = command["version"]
    expected = 1 if existing is None else existing["versions"][-1]["version"] + 1
    if type(version) is not int or version != expected:
        raise ContractError(f"version must be next immutable version ({expected})")
    if existing is not None and existing["actor_uid"] != actor_uid:
        raise ContractError("edit cannot change obligation actor_uid")
    ast = _validate_ast(command["ast"])
    if existing is not None:
        prior_deadlines = sorted(node["at"] for node in _collect_ast_nodes(existing["versions"][-1]["ast"], "deadline"))
        next_deadlines = sorted(node["at"] for node in _collect_ast_nodes(ast, "deadline"))
        if prior_deadlines != next_deadlines:
            raise ContractError("this process API preserves absolute deadline values across goal edits")
    return {"op": op, "goal_id": goal_id, "version": version,
            "actor_uid": actor_uid, "ast": ast, "source": "AUTHOR"}


def _apply_commands(session: dict[str, Any], commands: Sequence[object], now: float,
                    world_facts: set[str], coverage: float | None) -> list[dict[str, Any]]:
    if len(commands) > 1:
        raise ContractError("at most one author command may apply in a controller cycle")
    applied = []
    for raw in commands:
        command = _validate_command(raw, session)
        record = session["author_obligations"].get(command["goal_id"])
        if record is None:
            record = {"goal_id": command["goal_id"], "actor_uid": command["actor_uid"], "versions": []}
            session["author_obligations"][command["goal_id"]] = record
        elif record["versions"]:
            prior = record["versions"][-1]
            prior["closed_at"] = now
            prior["lifecycle"] = "SUPERSEDED"
            prior["closed_verdict"] = _monitor_ast(
                prior["ast"], world_facts=world_facts,
                native_history=session["native_history"], now=now, coverage=coverage)
            old_plan_key = f"{command['actor_uid']}:DIRECTOR:{command['goal_id']}:v{prior['version']}"
            old_plan = session["plans"].get(old_plan_key)
            if old_plan is not None:
                for node in old_plan["nodes"]:
                    if node["status"] == "planned":
                        node["status"] = "invalidated"
                        node["invalidated_reason"] = "author goal edited; executed prefix and pending request retained"
        version = {"version": command["version"], "ast": command["ast"],
                   "source": "AUTHOR", "effective_at": now}
        record["versions"].append(version)
        applied.append({key: command[key] for key in ("op", "goal_id", "version", "actor_uid", "source")})
    return applied


def _fact_state(actor: Mapping[str, Any], fact_key: str) -> bool | None:
    if fact_key in actor["facts"]:
        return True
    if fact_key in actor["unknown_facts"]:
        return None
    return False


def _gate_snapshot(actor: Mapping[str, Any], keys: Sequence[str]) -> list[list[Any]]:
    return [[key, _fact_state(actor, key)] for key in sorted(set(keys))]


def _apply_feedback(session: dict[str, Any], feedback: Sequence[object],
                    actors: Mapping[int, Mapping[str, Any]]) -> list[dict[str, Any]]:
    applied = []
    for row in feedback:
        if not isinstance(row, Mapping):
            raise ContractError("feedback must be an array of objects")
        if row.get("event") == "g1_action_dispatch_accepted":
            accepted_fields = {"event", "request_id", "actor_uid", "node_id", "game_time"}
            if set(row) != accepted_fields:
                raise ContractError("dispatch acceptance receipt has unsupported fields")
            actor_uid = uid(row["actor_uid"], "feedback.actor_uid")
            if actor_uid not in session["actor_uids"] or not finite_number(row["game_time"]) or row["game_time"] < 0:
                raise ContractError("dispatch acceptance must identify a session actor and absolute game time")
            inflight = session["inflight_by_actor"].get(str(actor_uid))
            matched = bool(inflight and inflight["request_id"] == row["request_id"]
                           and inflight["node_id"] == row["node_id"])
            applied.append({"request_id": row["request_id"], "actor_uid": actor_uid,
                            "event": row["event"], "matched": matched})
            if matched:
                inflight["dispatch_status"] = "ACCEPTED"
                plan = session["plans"].get(inflight["plan_key"])
                if plan is not None:
                    node = next((item for item in plan["nodes"] if item["node_id"] == row["node_id"]), None)
                    if node is not None:
                        node["dispatch_status"] = "ACCEPTED"
                        node["accepted_at"] = float(row["game_time"])
            continue
        if row.get("event") not in ("g1_action_settled", "g1_action_failed", "native_request_terminal"):
            raise ContractError("feedback event must be dispatch acceptance, G1 settlement/failure, or native terminal")
        required = {"event", "request_id", "actor_uid", "node_id", "action", "args", "game_time", "effects"}
        optional = {"reason", "source", "goal_id", "author_version", "provenance",
                    "event_id", "effect_ids"}
        if set(row) - (required | optional) or not required.issubset(row):
            raise ContractError("feedback fields do not match the typed settlement receipt")
        actor_uid = uid(row["actor_uid"], "feedback.actor_uid")
        if actor_uid not in session["actor_uids"]:
            raise ContractError("feedback actor_uid is outside this session")
        if not isinstance(row["request_id"], str) or not row["request_id"]:
            raise ContractError("feedback request_id must be non-empty")
        if not isinstance(row["node_id"], str) or not row["node_id"]:
            raise ContractError("feedback node_id must be non-empty")
        if not finite_number(row["game_time"]) or row["game_time"] < 0:
            raise ContractError("feedback game_time must be absolute and finite")
        effects = row["effects"]
        if not isinstance(effects, Sequence) or isinstance(effects, (str, bytes)):
            raise ContractError("feedback effects must be an array")
        fact_keys = []
        for effect in effects:
            if not isinstance(effect, Mapping) or set(effect) != {"predicate", "args"}:
                raise ContractError("feedback effects must be canonical fact descriptors")
            fact_keys.append(_fact_key(effect, "feedback effect"))
        effect_ids = row.get("effect_ids")
        if effect_ids is not None:
            if (not isinstance(effect_ids, Sequence) or isinstance(effect_ids, (str, bytes))
                    or len(effect_ids) != len(fact_keys)
                    or any(not isinstance(value, str) or not value for value in effect_ids)):
                raise ContractError("effect_ids must be a parallel array of non-empty trusted native IDs")
            fresh_facts = []
            for effect_id, fact_key in zip(effect_ids, fact_keys):
                if effect_id not in session["native_effect_ids"]:
                    session["native_effect_ids"].append(effect_id)
                    fresh_facts.append(fact_key)
            fact_keys = fresh_facts
        receipt_key = row.get("event_id")
        if receipt_key is not None and (not isinstance(receipt_key, str) or not receipt_key):
            raise ContractError("event_id must be a non-empty trusted native identifier")
        if receipt_key is None:
            # Deterministic fallback keeps replayed identical terminals
            # idempotent when the native format has no event id yet.
            receipt_key = hashlib.sha256(json.dumps(
                json_safe({key: row[key] for key in sorted(row)}), sort_keys=True,
                separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
        if receipt_key in session["native_receipt_ids"]:
            applied.append({"request_id": row["request_id"], "actor_uid": actor_uid,
                            "event": row["event"], "matched": False, "duplicate": True,
                            "receipt_id": receipt_key})
            continue
        session["native_receipt_ids"].append(receipt_key)
        inflight = session["inflight_by_actor"].get(str(actor_uid))
        matched = bool(inflight and inflight.get("request_id") == row["request_id"]
                       and inflight.get("node_id") == row["node_id"]
                       and inflight.get("primitive") == row["action"]
                       and inflight.get("args") == row["args"]
                       and (row.get("source") is None or row.get("source") == inflight["source"])
                       and (row.get("goal_id") is None or row.get("goal_id") == inflight["goal_id"])
                       and (row.get("author_version") is None
                            or row.get("author_version") == inflight.get("author_version")))
        applied.append({"request_id": row["request_id"], "actor_uid": actor_uid,
                        "event": row["event"], "matched": matched})
        # All real native effect evidence remains append-only even if it does
        # not match a currently pending request; it cannot clear unrelated work.
        session["native_history"].append({"game_time": float(row["game_time"]),
                                          "facts": fact_keys,
                                          "receipt": json_safe(row),
                                          "matched": matched,
                                          "receipt_id": receipt_key})
        if not matched:
            continue
        # Add author-monitorable event facts only for a fully correlated,
        # successful native terminal. Predictions, accepts, failures, and
        # mismatched receipts cannot manufacture process-order witnesses.
        if row["event"] == "g1_action_settled" and isinstance(row["args"], Mapping):
            args = row["args"]
            event_descriptor = None
            if row["action"] == "survey_marker" and isinstance(args.get("marker_id"), str):
                event_descriptors = [
                    {"predicate": "event:g1_survey_completed",
                     "args": [args["marker_id"]]},
                    {"predicate": "event:g1_survey_completed",
                     "args": [actor_uid, args["marker_id"]]},
                ]
            elif row["action"] == "deliver_report" and isinstance(args.get("marker_id"), str) \
                    and type(args.get("receiver_uid")) is int:
                event_descriptors = [
                    {"predicate": "event:g1_report_delivered",
                     "args": [args["marker_id"], args["receiver_uid"]]},
                    {"predicate": "event:g1_report_delivered",
                     "args": [actor_uid, args["marker_id"], args["receiver_uid"]]},
                ]
            elif row["action"] == "rally_marker" and isinstance(args.get("marker_id"), str) \
                    and type(args.get("follower_uid")) is int:
                event_descriptors = [
                    {"predicate": "event:g1_rally_completed",
                     "args": [args["marker_id"], args["follower_uid"]]},
                    {"predicate": "event:g1_rally_completed",
                     "args": [actor_uid, args["marker_id"], args["follower_uid"]]},
                ]
            elif row["action"] == "RecruitMember" and type(args.get("target_uid")) is int:
                event_descriptors = [{"predicate": "event:native_recruit_job_observed",
                                      "args": [actor_uid, args["target_uid"]]}]
            else:
                event_descriptors = []
            for event_descriptor in event_descriptors:
                event_key = _fact_key(event_descriptor, "correlated native event")
                if event_key not in fact_keys:
                    fact_keys.append(event_key)
        plan = session["plans"].get(inflight["plan_key"])
        if plan is not None:
            node = next((item for item in plan["nodes"] if item["node_id"] == row["node_id"]), None)
            if node is not None:
                if row["event"] == "g1_action_settled":
                    node["status"] = "executed"
                    node["settled_at"] = float(row["game_time"])
                    node["receipt"] = json_safe(row)
                else:
                    node["status"] = "retry_blocked"
                    node["retry_reason"] = row.get("reason", "native action failed")
                    node["retry_blocked_at"] = float(row["game_time"])
                    node["retry_gate_snapshot"] = _gate_snapshot(
                        actors[actor_uid], inflight.get("retry_gate_keys", []))
                    node["retry_count"] = int(node.get("retry_count", 0)) + 1
                    node.setdefault("attempt_history", []).append({
                        "request_id": row["request_id"], "game_time": float(row["game_time"]),
                        "reason": node["retry_reason"]})
                    _invalidate_descendants(plan["nodes"], node["node_id"], "dependency action failed")
        session["inflight_by_actor"].pop(str(actor_uid), None)
    return applied


def _invalidate_descendants(nodes: list[dict[str, Any]], node_id: str, reason: str) -> None:
    invalid = {node_id}
    changed = True
    while changed:
        changed = False
        for node in nodes:
            if node["status"] in ("executed", "invalidated"):
                continue
            if invalid.intersection(node.get("dependencies", [])):
                node["status"] = "invalidated"
                node["invalidated_reason"] = reason
                invalid.add(node["node_id"])
                changed = True


def _node_id(actor_uid: int, plan_key: str, step: Mapping[str, Any], ordinal: int,
             generation: int) -> str:
    raw = json.dumps([actor_uid, plan_key, step["primitive"], step["args"], ordinal, generation],
                     sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def _make_plan(session: dict[str, Any], actor: dict[str, Any], *, plan_key: str,
               goal_id: str, source: str, goal_source: str, author_version: int | None,
               goals: Sequence[Mapping[str, Any]], ordered_groups: Sequence[Sequence[Mapping[str, Any]]],
               old_plan: dict[str, Any] | None) -> dict[str, Any]:
    result = plan_fact_goals(actor, goals, ordered_groups=ordered_groups)
    generation = int((old_plan or {}).get("generation", 0))
    old_nodes = list((old_plan or {}).get("nodes", []))
    reusable = [node for node in old_nodes if node["status"] in
                ("executed", "pending", "retry_blocked")]
    # Never rewrite an accepted in-flight operation. It remains the first
    # unresolved node while the planner repairs only its suffix.
    pending = next((node for node in reusable if node["status"] == "pending"), None)
    new_steps = result.get("steps", []) if result.get("status") == "PLANNED" else []
    if pending is not None:
        # The in-flight primitive is already owned by the native runtime. A
        # fresh prediction may still include it because its effect is not yet
        # observed; retain the original node and refine only what follows it.
        for index, step in enumerate(new_steps):
            if step["primitive"] == pending["primitive"] and step["args"] == pending["args"]:
                new_steps = new_steps[:index] + new_steps[index + 1:]
                break
    nodes: list[dict[str, Any]] = [node for node in old_nodes if node["status"] == "executed"]
    if pending is not None:
        nodes.append(pending)
    offset = len(nodes)
    prior_effect_node: dict[str, str] = {}
    for old in nodes:
        for effect in old.get("effects", []):
            prior_effect_node[_fact_key(effect, "node effect")] = old["node_id"]
    for ordinal, step in enumerate(new_steps):
        signature = (step["primitive"], json.dumps(step["args"], sort_keys=True, separators=(",", ":")))
        existing = next((node for node in reusable
                         if (node["primitive"], json.dumps(node["args"], sort_keys=True,
                                                            separators=(",", ":"))) == signature
                         and node not in nodes), None)
        dispatch_preconditions = step.get("dispatch_preconditions", [])
        retry_status = "planned"
        if existing is not None and existing.get("status") == "retry_blocked":
            gate_keys = [_fact_key(item, "retry gate") for item in
                         list(step["preconditions"]) + list(dispatch_preconditions)]
            if _gate_snapshot(actor, gate_keys) == existing.get("retry_gate_snapshot"):
                retry_status = "retry_blocked"
        dependencies = [prior_effect_node[key] for key in
                        (_fact_key(item, "step precondition") for item in step["preconditions"])
                        if key in prior_effect_node]
        node = {
            "node_id": existing["node_id"] if existing else _node_id(actor["actor_uid"], plan_key, step, ordinal, generation),
            "status": retry_status, "primitive": step["primitive"], "args": step["args"],
            "preconditions": step["preconditions"],
            "dispatch_preconditions": dispatch_preconditions, "effects": step["effects"],
            "dependencies": sorted(set(dependencies)),
            "goal_id": goal_id, "source": source, "goal_source": goal_source,
            "author_version": author_version,
            "provenance": step["provenance"], "estimated_cost": step["estimated_cost"],
        }
        if existing is not None:
            for field in ("retry_count", "attempt_history", "retry_reason", "retry_blocked_at",
                          "retry_gate_snapshot"):
                if field in existing:
                    node[field] = json_safe(existing[field])
        if retry_status == "planned":
            node.pop("retry_gate_snapshot", None)
            node.pop("retry_reason", None)
        nodes.append(node)
        for effect in step["effects"]:
            prior_effect_node[_fact_key(effect, "step effect")] = node["node_id"]
    retained_ids = {node["node_id"] for node in nodes}
    for old in old_nodes:
        if old["status"] not in ("executed", "invalidated") and old["node_id"] not in retained_ids:
            old["status"] = "invalidated"
            old["invalidated_reason"] = "unexecuted suffix changed by observation or goal edit"
            nodes.append(old)
    if result.get("status") != "PLANNED":
        generation += 1
    return {"plan_key": plan_key, "actor_uid": actor["actor_uid"], "goal_id": goal_id,
            "source": source, "goal_source": goal_source,
            "author_version": author_version, "generation": generation,
            "status": result.get("status"), "reason": result.get("reason"),
            "planner": result.get("planner"), "goal_facts": result.get("goal_facts", list(goals)),
            "nodes": nodes}


def step_process(session: Mapping[str, Any], observations: Mapping[str, Any], *, game_time: float,
                 author_commands: Sequence[object] = (), feedback: Sequence[object] = (),
                 director_hint: Mapping[str, Any] | None = None,
                 request_budget_remaining: int | None = None) -> dict[str, Any]:
    """Consume fresh per-actor views and receipts, then propose ready primitives.

    ``world_facts`` is deliberately excluded from every actor's HTN state.
    It is used only by the AUTHOR monitor and optional director ordering.
    """
    state = json_safe(session)
    if state.get("schema") != "character_dynamics_online_process_v0":
        raise ContractError("unsupported process session schema")
    if not finite_number(game_time) or game_time < 0:
        raise ContractError("game_time must be absolute and finite")
    if (request_budget_remaining is not None
            and (type(request_budget_remaining) is not int or request_budget_remaining < 0)):
        raise ContractError("request_budget_remaining must be a non-negative integer or None")
    now = float(game_time)
    actors = validate_process_observations(observations, now)
    if set(actors) != set(state["actor_uids"]):
        raise ContractError("one fresh actor observation is required for every session actor")
    for actor_uid, actor in actors.items():
        previous = state["observation_ids"].get(str(actor_uid))
        if previous == actor["observation_id"]:
            raise ContractError("each actor decision must consume fresh observations")
    world_true = {_fact_key({"predicate": fact["predicate"], "args": fact["args"]}, "world fact")
                  for fact in observations["world_facts"] if fact["value"] is True}
    coverage = observations["event_coverage_through"]
    feedback_applied = _apply_feedback(state, feedback, actors)
    commands = _apply_commands(state, author_commands, now, world_true,
                                float(coverage) if coverage is not None else None)
    obligations = []
    for record in state["author_obligations"].values():
        version = record["versions"][-1]
        verdict = _monitor_ast(version["ast"], world_facts=world_true,
                               native_history=state["native_history"], now=now,
                               coverage=float(coverage) if coverage is not None else None)
        obligations.append({"goal_id": record["goal_id"], "actor_uid": record["actor_uid"],
                            "version": version["version"], "ast": version["ast"],
                            "effective_at": version["effective_at"], "source": "AUTHOR",
                            "verdict": verdict})
    active_obligations = [item for item in obligations
                          if item["verdict"].get("feasibility") != "EXPIRED"
                          and item["verdict"]["status"] not in ("VIOLATED", "SATISFIED")]
    author_order_guards = []
    for item in active_obligations:
        for order_node in _active_ast_nodes(
                item["ast"], "event_before", world_facts=world_true,
                native_history=state["native_history"], now=now,
                coverage=float(coverage) if coverage is not None else None):
            author_order_guards.append({
                "goal_id": item["goal_id"],
                "first": _event_facts(order_node["first"]),
                "second": _event_facts(order_node["second"]),
            })
    hint = director_hint or {}
    if not isinstance(hint, Mapping) or set(hint) - {"goal_order"}:
        raise ContractError("director_hint may only order known goal ids")
    goal_order = hint.get("goal_order", []) if state["director_enabled"] else []
    if not isinstance(goal_order, Sequence) or isinstance(goal_order, (str, bytes)):
        raise ContractError("director_hint.goal_order must be an array")
    rank = {value: i for i, value in enumerate(goal_order) if isinstance(value, str)}

    work_specs = [{**item, "source": "ACTOR", "goal_source": "ACTOR", "author_version": None}
                  for item in state["actor_goal_specs"]]
    for item in obligations:
        if (item["verdict"].get("feasibility") == "EXPIRED"
                or item["verdict"]["status"] in ("VIOLATED", "SATISFIED")):
            if item["verdict"].get("feasibility") == "EXPIRED":
                expired_key = (f"{item['actor_uid']}:DIRECTOR:{item['goal_id']}"
                               f":v{item['version']}")
                expired_plan = state["plans"].get(expired_key)
                if expired_plan is not None:
                    for node in expired_plan["nodes"]:
                        if node["status"] in ("planned", "retry_blocked"):
                            node["status"] = "invalidated"
                            node["invalidated_reason"] = "absolute author deadline expired"
                    expired_plan["status"] = "EXPIRED"
                    expired_plan["reason"] = "absolute author deadline expired; any pending native request is retained"
            continue
        goals, groups = _ast_to_plan(
            item["ast"], state["native_history"], now=now, world_facts=world_true,
            coverage=float(coverage) if coverage is not None else None)
        work_specs.append({"goal_id": item["goal_id"], "actor_uid": item["actor_uid"],
                           "goals": goals, "ordered_groups": groups, "source": "DIRECTOR",
                           "goal_source": "AUTHOR",
                           "author_version": item["version"]})
    order_conflict = _has_order_cycle(
        active_obligations, world_facts=world_true, native_history=state["native_history"],
        now=now, coverage=float(coverage) if coverage is not None else None)
    work_specs.sort(key=lambda item: (0 if item["goal_source"] == "AUTHOR" else 1,
                                      rank.get(item["goal_id"], len(rank)), item["goal_id"]))

    plans: dict[str, Any] = state["plans"]
    requests: list[dict[str, Any]] = []
    blocked: list[dict[str, Any]] = []
    for item in obligations:
        if item["verdict"].get("feasibility") == "EXPIRED":
            blocked.append({"code": "AUTHOR_GOAL_EXPIRED", "actor_uid": item["actor_uid"],
                            "goal_id": item["goal_id"], "source": "AUTHOR",
                            "reason": item["verdict"].get("reason", "absolute deadline expired"),
                            "verdict": item["verdict"]})
    plan_summaries = []
    # Each actor has at most one pending request, while independent actors may
    # progress concurrently through this single shared process controller.
    for spec in work_specs:
        actor_uid = spec["actor_uid"]
        actor = actors[actor_uid]
        if order_conflict and spec["goal_source"] == "AUTHOR":
            blocked.append({"code": "AUTHOR_CONSTRAINT_CONFLICT", "actor_uid": actor_uid,
                            "goal_id": spec["goal_id"],
                            "reason": "active author event_before constraints contain a cycle"})
            continue
        plan_key = (f"{actor_uid}:{spec['source']}:{spec['goal_id']}"
                    + (f":v{spec['author_version']}" if spec["goal_source"] == "AUTHOR" else ""))
        old_plan = plans.get(plan_key)
        plan = _make_plan(state, actor, plan_key=plan_key, goal_id=spec["goal_id"],
                          source=spec["source"], author_version=spec["author_version"],
                          goal_source=spec["goal_source"],
                          goals=spec["goals"], ordered_groups=spec.get("ordered_groups", []),
                          old_plan=old_plan)
        plans[plan_key] = plan
        inflight = state["inflight_by_actor"].get(str(actor_uid))
        if inflight is not None:
            blocked.append({"code": "ACTION_IN_FLIGHT", "actor_uid": actor_uid,
                            "request_id": inflight["request_id"], "node_id": inflight["node_id"],
                            "reason": "native operation remains pending until correlated terminal receipt"})
            plan_summaries.append({"plan_key": plan_key, "status": plan["status"],
                                   "nodes": plan["nodes"], "planner": plan["planner"]})
            continue
        trusted_event_facts = {
            fact_key
            for row in state["native_history"] if row.get("matched") is True
            for fact_key in row.get("facts", [])
        }
        status_by_node = {node["node_id"]: node["status"] for node in plan["nodes"]}
        pending_node = None
        for candidate in plan["nodes"]:
            if candidate["status"] == "retry_blocked":
                blocked.append({"code": "ACTION_RETRY_WAIT", "actor_uid": actor_uid,
                                "goal_id": spec["goal_id"], "node_id": candidate["node_id"],
                                "reason": candidate.get("retry_reason"),
                                "wait_for": "a change in this action's logical or dispatch preconditions"})
                continue
            if candidate["status"] != "planned":
                continue
            unresolved_dependencies = [node_id for node_id in candidate.get("dependencies", [])
                                       if status_by_node.get(node_id) != "executed"]
            if unresolved_dependencies:
                blocked.append({"code": "AWAITING_DEPENDENCY", "actor_uid": actor_uid,
                                "goal_id": spec["goal_id"], "node_id": candidate["node_id"],
                                "dependencies": unresolved_dependencies,
                                "reason": "causal predecessor has not settled"})
                continue
            preconditions = [_fact_key(fact, "request precondition")
                             for fact in candidate["preconditions"]]
            if not set(preconditions).issubset(actor["facts"]):
                blocked.append({"code": "AWAITING_ACTOR_OBSERVATION", "actor_uid": actor_uid,
                                "goal_id": spec["goal_id"], "node_id": candidate["node_id"],
                                "reason": "planned preconditions are not confirmed in this actor view"})
                continue
            dispatch_preconditions = [_fact_key(fact, "dispatch precondition")
                                      for fact in candidate.get("dispatch_preconditions", [])]
            if not set(dispatch_preconditions).issubset(actor["facts"]):
                blocked.append({"code": "DISPATCH_PRECONDITION_PENDING", "actor_uid": actor_uid,
                                "goal_id": spec["goal_id"], "node_id": candidate["node_id"],
                                "preconditions": [
                                    _decode_fact(key) for key in dispatch_preconditions
                                    if key not in actor["facts"]],
                                "reason": "future-plannable action is not currently dispatchable"})
                continue
            receiver_uid = candidate.get("args", {}).get("receiver_uid") \
                if candidate["primitive"] == "deliver_report" and isinstance(candidate.get("args"), Mapping) else None
            if receiver_uid is not None:
                busy_receiver = state["inflight_by_actor"].get(str(receiver_uid))
                competing_delivery = any(
                    int(other_actor) != actor_uid
                    and other.get("primitive") == "deliver_report"
                    and other.get("args", {}).get("receiver_uid") == receiver_uid
                    for other_actor, other in state["inflight_by_actor"].items()
                    if str(other_actor).lstrip("-").isdigit())
                if busy_receiver is not None or competing_delivery:
                    blocked.append({"code": "RECEIVER_RESOURCE_IN_FLIGHT", "actor_uid": actor_uid,
                                    "goal_id": spec["goal_id"], "node_id": candidate["node_id"],
                                    "receiver_uid": receiver_uid,
                                    "receiver_request_id": busy_receiver.get("request_id") if busy_receiver else None,
                                    "receiver_primitive": busy_receiver.get("primitive") if busy_receiver else None,
                                    "reason": "the receiver or another request to it is still in flight"})
                    continue
            node_effects = {_fact_key(fact, "request effect") for fact in candidate["effects"]}
            order_wait = None
            for guard in author_order_guards:
                first_key = _fact_key(guard["first"], "author order first event")
                second_key = _fact_key(guard["second"], "author order second event")
                if second_key in node_effects and first_key not in trusted_event_facts:
                    order_wait = {"goal_id": guard["goal_id"],
                                  "first": guard["first"], "second": guard["second"],
                                  "same_action": first_key in node_effects}
                    break
            if order_wait is not None:
                blocked.append({"code": "AUTHOR_ORDER_PENDING", "actor_uid": actor_uid,
                                "goal_id": spec["goal_id"], "node_id": candidate["node_id"],
                                "author_goal_id": order_wait["goal_id"],
                                "first_event": order_wait["first"], "second_event": order_wait["second"],
                                "same_action_cannot_satisfy_strict_order": order_wait["same_action"],
                                "reason": "a correlated native witness for the required first event is missing"})
                continue
            pending_node = candidate
            break
        if pending_node is None:
            if plan["status"] not in ("SATISFIED", "PLANNED"):
                blocked.append({"code": plan["status"], "actor_uid": actor_uid,
                                "goal_id": spec["goal_id"], "source": spec["source"],
                                "reason": plan.get("reason")})
            plan_summaries.append({"plan_key": plan_key, "status": plan["status"],
                                   "nodes": plan["nodes"], "planner": plan["planner"]})
            continue
        if request_budget_remaining is not None and len(requests) >= request_budget_remaining:
            blocked.append({"code": "REQUEST_BUDGET_EXHAUSTED", "actor_uid": actor_uid,
                            "goal_id": spec["goal_id"], "node_id": pending_node["node_id"],
                            "reason": "proposal withheld before creating in-flight state"})
            plan_summaries.append({"plan_key": plan_key, "status": plan["status"],
                                   "nodes": plan["nodes"], "planner": plan["planner"]})
            continue
        request_seq = int(state["decision_sequence"]) + len(requests) + 1
        request_id = hashlib.sha256(
            f"{actor_uid}:{plan_key}:{pending_node['node_id']}:{request_seq}:{now:.6f}".encode()).hexdigest()[:20]
        pending_node["status"] = "pending"
        pending_node["request_id"] = request_id
        pending_node["requested_at"] = now
        retry_gate_keys = [_fact_key(fact, "retry gate") for fact in
                           list(pending_node["preconditions"])
                           + list(pending_node.get("dispatch_preconditions", []))]
        pending_node["attempt_history"] = list(pending_node.get("attempt_history", [])) + [{
            "request_id": request_id, "game_time": now}]
        request = {"request_id": request_id, "actor_uid": actor_uid,
                   "node_id": pending_node["node_id"], "primitive": pending_node["primitive"],
                   "args": json_safe(pending_node["args"]), "source": spec["source"],
                   "goal_id": spec["goal_id"], "author_version": spec["author_version"],
                   "goal_source": spec["goal_source"],
                   "dependencies": pending_node["dependencies"],
                   "provenance": pending_node["provenance"], "observed_time": now,
                   "rule_version": "recon-v1", "ttl_seconds": 120.0}
        requests.append(request)
        state["inflight_by_actor"][str(actor_uid)] = {"request_id": request_id,
                                                       "node_id": pending_node["node_id"],
                                                       "plan_key": plan_key,
                                                       "created_at": now,
                                                       "source": spec["source"],
                                                       "goal_id": spec["goal_id"],
                                                       "author_version": spec["author_version"],
                                                       "primitive": pending_node["primitive"],
                                                       "args": pending_node["args"],
                                                       "retry_gate_keys": retry_gate_keys}
        plan_summaries.append({"plan_key": plan_key, "status": plan["status"],
                               "nodes": plan["nodes"], "planner": plan["planner"]})

    author_status = []
    for record in state["author_obligations"].values():
        versions = []
        for version in record["versions"]:
            # Superseded versions freeze their verdict at edit time and are
            # never re-evaluated against later events or coverage.
            if version.get("lifecycle") == "SUPERSEDED":
                verdict = version["closed_verdict"]
            else:
                verdict = _monitor_ast(version["ast"], world_facts=world_true,
                                       native_history=state["native_history"], now=now,
                                       coverage=float(coverage) if coverage is not None else None)
                version["closed_verdict"] = verdict
            versions.append({"version": version["version"], "lifecycle": version.get("lifecycle", "ACTIVE"),
                             **version["closed_verdict"]})
        active = versions[-1]
        author_status.append({"goal_id": record["goal_id"], "actor_uid": record["actor_uid"],
                              "active_version": active["version"], "status": active["status"],
                              "versions": versions})
    for actor_uid, actor in actors.items():
        state["observation_ids"][str(actor_uid)] = actor["observation_id"]
    state["decision_sequence"] = int(state["decision_sequence"]) + 1
    decision = {"sequence": state["decision_sequence"], "game_time": now,
                "sources": {"native": "NATIVE", "actor_goals": "ACTOR",
                            "author_goals": "AUTHOR", "coordination": "DIRECTOR"},
                "director_enabled": state["director_enabled"],
                "author_commands_applied": commands, "feedback_applied": feedback_applied,
                "author_obligations": author_status, "plans": plan_summaries,
                "requests": requests, "blocked": blocked,
                "world_facts_used_only_for_author_monitor": True,
                "predictions_are_not_settlements": True}
    state["history"].append(json_safe(decision))
    return {"session": json_safe(state), "decision": json_safe(decision)}
