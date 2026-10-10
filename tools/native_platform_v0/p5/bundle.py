"""Strict JSON Author Bundle adapter over the existing trajectory TypedIR."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import json
from pathlib import Path
import threading
from types import MappingProxyType
from typing import Any, Mapping

from tools.trajectory_constraints_v0.ast import (
    Anchor, AnchorKind, Compare, CompareValue, Constraint, EventCount, EventOrder,
    StrictOrder, TemporalConstraint, TemporalOp, Window,
)
from tools.trajectory_constraints_v0.compiler import CompileResult, compile_constraint
from tools.trajectory_constraints_v0.types import (
    Owner, Registry, RegistryEntry, StableEntity, TimeMode, TypeSpec, ValueKind,
    ValueRef,
)

SCHEMA = "native-author-bundle-v1"
P5_WORLD_VERSION = "p5-world-v1"
P5_LEDGER_VERSION = "1"
P5_INITIAL_PHYSICAL_BUDGET = 2
MAX_DEADLINE = 24
WORLD_OPPORTUNITIES = frozenset({"open_main_passage", "open_side_passage"})
ROUTE_IDS = frozenset({"main_passage", "side_passage"})
NOTE_RESPONSES = frozenset({"accepted", "rejected"})


class BundleError(ValueError):
    """Stable machine-readable validation or optimistic-concurrency failure."""

    def __init__(self, code: str, message: str, *, details: Mapping[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.details = dict(details or {})


class VersionConflict(BundleError):
    def __init__(self, expected: int, actual: int):
        super().__init__("VERSION_CONFLICT", "author bundle version changed before commit",
                         details={"expected_version": expected, "actual_version": actual})


@dataclass(frozen=True)
class CompiledGoal:
    constraint_id: str
    kind: str
    hard: bool
    start: int
    deadline: int
    constraint: Constraint
    compile_result: CompileResult
    source: Mapping[str, Any]


@dataclass(frozen=True)
class StoryBranch:
    branch_id: str
    response: str
    storylet_id: str
    text: str


@dataclass(frozen=True)
class AuthorBundle:
    bundle_id: str
    version: int
    source: str
    goals: tuple[CompiledGoal, ...]
    branches: tuple[StoryBranch, ...]
    permissions: Mapping[str, Any]
    raw: Mapping[str, Any]
    entities: Mapping[str, StableEntity]

    @property
    def constraints(self) -> tuple[Constraint, ...]:
        return tuple(goal.constraint for goal in self.goals)


def p5_registry() -> Registry:
    """Return the closed P5 event/state registry; no evaluator code is bundle-defined."""
    return Registry((
        RegistryEntry("p5_note_response", P5_LEDGER_VERSION, Owner.LEDGER, "NoteResponse",
                      {"actor": "Actor", "recipient": "Actor", "item": "Item", "response": "str"},
                      TypeSpec(ValueKind.EVENT), "ledger_event_v1", ("p4_sealed_social_ledger",), TimeMode.EVENT),
        RegistryEntry("p5_delivery_settled", P5_LEDGER_VERSION, Owner.LEDGER, "DeliverySettled",
                      {"actor": "Actor", "item": "Item"}, TypeSpec(ValueKind.EVENT),
                      "ledger_event_v1", ("native_settled_drop_receipts",), TimeMode.EVENT),
        RegistryEntry("p5_holding", P5_WORLD_VERSION, Owner.WORLD, "Holding",
                      {"actor": "Actor", "item": "Item"}, TypeSpec(ValueKind.BOOL),
                      "registered_field_v1", ("W.holders",), TimeMode.PIECEWISE_CONSTANT),
        RegistryEntry("p5_route_open", P5_WORLD_VERSION, Owner.WORLD, "RouteOpen",
                      {"route": "str"}, TypeSpec(ValueKind.BOOL),
                      "registered_field_v1", ("W.routes",), TimeMode.PIECEWISE_CONSTANT),
    ))


DEFAULT_ENTITIES: Mapping[str, StableEntity] = MappingProxyType({
    "A": StableEntity("Actor", "A", "Courier"),
    "B": StableEntity("Actor", "B", "Resident"),
    "note": StableEntity("Item", "note", "Note"),
    "courier_supply": StableEntity("Item", "courier_supply", "Courier supply"),
    "resident_parcel": StableEntity("Item", "resident_parcel", "Resident parcel"),
})


def _fail(code: str, message: str, **details: Any) -> None:
    raise BundleError(code, message, details=details)


def _keys(value: Any, required: set[str], optional: set[str], where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        _fail("INVALID_SCHEMA", f"{where} must be a JSON object", path=where)
    missing, extra = required - set(value), set(value) - required - optional
    if missing or extra:
        _fail("INVALID_SCHEMA", f"{where} has missing or unknown keys", path=where,
              missing=sorted(missing), unknown=sorted(extra))
    return value


def _identifier(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value or len(value) > 128:
        _fail("INVALID_SCHEMA", f"{where} must be a nonempty stable string identifier", path=where)
    return value


def _int(value: Any, where: str, low: int = 0, high: int = MAX_DEADLINE) -> int:
    if type(value) is not int or not low <= value <= high:
        _fail("INVALID_SCHEMA", f"{where} must be an integer in [{low}, {high}]", path=where)
    return value


def _json_source(raw_or_path: Any) -> dict[str, Any]:
    if isinstance(raw_or_path, Mapping):
        return dict(raw_or_path)
    try:
        if isinstance(raw_or_path, Path):
            source = raw_or_path.read_text(encoding="utf-8")
        elif isinstance(raw_or_path, str):
            if raw_or_path.lstrip().startswith("{"):
                source = raw_or_path
            else:
                candidate = Path(raw_or_path)
                source = candidate.read_text(encoding="utf-8") if "\n" not in raw_or_path and candidate.is_file() else raw_or_path
        else:
            _fail("INVALID_INPUT", "bundle input must be a mapping, JSON string, or path")
        def no_duplicates(pairs):
            result = {}
            for key, value in pairs:
                if key in result:
                    raise ValueError(f"duplicate JSON key: {key}")
                result[key] = value
            return result
        data = json.loads(source, object_pairs_hook=no_duplicates)
    except BundleError:
        raise
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        _fail("INVALID_JSON", f"could not parse author bundle JSON: {type(exc).__name__}")
    if not isinstance(data, dict):
        _fail("INVALID_SCHEMA", "bundle root must be a JSON object")
    return data


def _entity_catalog(entities: Mapping[str, Any] | None) -> dict[str, StableEntity]:
    if entities is None:
        return dict(DEFAULT_ENTITIES)
    if not isinstance(entities, Mapping):
        _fail("INVALID_ENTITIES", "entities must map stable aliases to StableEntity records")
    result = {}
    for alias, value in entities.items():
        alias = _identifier(alias, "entities.alias")
        if isinstance(value, StableEntity):
            entity = value
        elif isinstance(value, Mapping) and set(value) <= {"entity_type", "stable_id", "display_name", "deleted"}:
            try:
                entity = StableEntity(value["entity_type"], value["stable_id"],
                                      value.get("display_name", ""), value.get("deleted", False))
            except (KeyError, TypeError, ValueError) as exc:
                _fail("INVALID_ENTITIES", f"invalid stable entity for alias {alias!r}")
        else:
            _fail("INVALID_ENTITIES", f"entity alias {alias!r} must resolve to a stable entity")
        if entity.deleted or not entity.stable_id or not entity.entity_type:
            _fail("INVALID_ENTITIES", f"entity alias {alias!r} is deleted or lacks stable identity")
        result[alias] = entity
    return result


def _entity(entities: Mapping[str, StableEntity], alias: Any, expected: str, where: str) -> StableEntity:
    if not isinstance(alias, str) or alias not in entities:
        _fail("UNKNOWN_ENTITY", f"{where} references an unregistered stable entity alias", path=where,
              alias=alias)
    value = entities[alias]
    if value.entity_type != expected:
        _fail("ENTITY_TYPE_MISMATCH", f"{where} requires a {expected} entity", path=where,
              expected=expected, actual=value.entity_type)
    return value


def _filter_args(event: str, filters: Any, entities: Mapping[str, StableEntity], where: str) -> dict[str, Any]:
    if not isinstance(filters, dict):
        _fail("INVALID_SCHEMA", f"{where}.filters must be an object", path=where)
    schemas = {
        "note_response": {"actor": "Actor", "recipient": "Actor", "item": "Item", "response": "str"},
        "delivery_settled": {"actor": "Actor", "item": "Item"},
    }
    schema = schemas[event]
    extra = set(filters) - set(schema)
    if extra:
        _fail("UNKNOWN_EVENT_ARGUMENT", f"{where} has unregistered event filter(s)",
              path=where, unknown=sorted(extra))
    args = {}
    for key, value in filters.items():
        expected = schema[key]
        if expected in ("Actor", "Item"):
            args[key] = _entity(entities, value, expected, f"{where}.filters.{key}")
        elif expected == "str":
            if not isinstance(value, str):
                _fail("INVALID_SCHEMA", f"{where}.filters.{key} must be a string")
            if event == "note_response" and value not in NOTE_RESPONSES:
                _fail("UNKNOWN_EVENT_VALUE", f"unsupported note response value {value!r}")
            args[key] = value
    return args


def _window(data: Mapping[str, Any], where: str) -> tuple[int, int]:
    start = _int(data["start"], f"{where}.start")
    deadline = _int(data["deadline"], f"{where}.deadline")
    if deadline < start:
        _fail("INVALID_WINDOW", f"{where} deadline precedes start")
    return start, deadline


def _parse_goal(raw: Any, registry: Registry, entities: Mapping[str, StableEntity]) -> CompiledGoal:
    if not isinstance(raw, dict):
        _fail("INVALID_SCHEMA", "constraint entries must be objects")
    goal_id = _identifier(raw.get("id"), "constraint.id")
    kind = raw.get("kind")
    if type(raw.get("hard")) is not bool:
        _fail("INVALID_SCHEMA", f"constraint {goal_id} requires boolean hard")
    hard = raw["hard"]
    if kind == "event_by_deadline":
        data = _keys(raw, {"id", "kind", "event", "filters", "start", "deadline", "hard"},
                     {"min_count", "max_count"}, f"constraints.{goal_id}")
        event = data["event"]
        if not isinstance(event, str) or event not in {"note_response", "delivery_settled"}:
            _fail("SEMANTIC_GAP", f"event {event!r} is not registered in P5", constraint_id=goal_id)
        start, deadline = _window(data, f"constraints.{goal_id}")
        minimum = _int(data.get("min_count", 1), f"constraints.{goal_id}.min_count", 0, 1000)
        maximum = data.get("max_count")
        if maximum is not None:
            maximum = _int(maximum, f"constraints.{goal_id}.max_count", minimum, 1000)
        args = _filter_args(event, data["filters"], entities, f"constraints.{goal_id}")
        node = EventCount(goal_id, "p5_note_response" if event == "note_response" else "p5_delivery_settled",
                          P5_LEDGER_VERSION, Window(Fraction(start), Fraction(deadline)),
                          minimum=minimum, maximum=maximum, event_filter=args,
                          anchor=Anchor(AnchorKind.SCENARIO_START), hard=hard)
    elif kind == "event_order":
        data = _keys(raw, {"id", "kind", "before", "after", "order", "start", "deadline", "hard"},
                     set(), f"constraints.{goal_id}")
        start, deadline = _window(data, f"constraints.{goal_id}")
        before = _event_selector(data["before"], entities, f"constraints.{goal_id}.before")
        after = _event_selector(data["after"], entities, f"constraints.{goal_id}.after")
        try:
            order = StrictOrder(data["order"])
        except (ValueError, TypeError):
            _fail("INVALID_SCHEMA", f"constraint {goal_id} order must be EVENT_KEY or PHYSICAL_TIME")
        node = EventOrder(goal_id, before[0], P5_LEDGER_VERSION, after[0], P5_LEDGER_VERSION,
                          order, Window(Fraction(start), Fraction(deadline)),
                          anchor=Anchor(AnchorKind.SCENARIO_START), before_filter=before[1],
                          after_filter=after[1], hard=hard)
    elif kind == "state_by_deadline":
        data = _keys(raw, {"id", "kind", "observable", "args", "value", "start", "deadline", "hard"},
                     set(), f"constraints.{goal_id}")
        start, deadline = _window(data, f"constraints.{goal_id}")
        if type(data["value"]) is not bool:
            _fail("INVALID_SCHEMA", f"constraint {goal_id} state value must be boolean")
        observable = data["observable"]
        if observable == "holding":
            args_raw = _keys(data["args"], {"actor", "item"}, set(), f"constraints.{goal_id}.args")
            args = {"actor": _entity(entities, args_raw["actor"], "Actor", "args.actor"),
                    "item": _entity(entities, args_raw["item"], "Item", "args.item")}
            observable_id = "p5_holding"
        elif observable == "route_open":
            args_raw = _keys(data["args"], {"route"}, set(), f"constraints.{goal_id}.args")
            route = args_raw["route"]
            if not isinstance(route, str) or route not in ROUTE_IDS:
                _fail("SEMANTIC_GAP", f"route {route!r} has no registered state projector")
            args = {"route": route}
            observable_id = "p5_route_open"
        else:
            _fail("SEMANTIC_GAP", f"state observable {observable!r} has no registered evaluator",
                  constraint_id=goal_id)
        ref = ValueRef(observable_id, P5_WORLD_VERSION, args, Owner.WORLD)
        node = TemporalConstraint(goal_id, TemporalOp.EVENTUALLY,
                                  CompareValue(ref, Compare.EQ, data["value"]),
                                  Window(Fraction(start), Fraction(deadline)),
                                  Anchor(AnchorKind.SCENARIO_START), hard=hard)
    else:
        _fail("SEMANTIC_GAP", f"constraint kind {kind!r} is not registered in P5",
              constraint_id=goal_id)
    try:
        compiled = compile_constraint(node, registry)
    except (KeyError, TypeError, ValueError) as exc:
        _fail("TYPEDIR_COMPILE_ERROR", f"constraint {goal_id} failed TypedIR validation: {exc}",
              constraint_id=goal_id)
    return CompiledGoal(goal_id, kind, hard, start, deadline, node, compiled,
                        MappingProxyType(dict(raw)))


def _event_selector(raw: Any, entities: Mapping[str, StableEntity], where: str):
    data = _keys(raw, {"event", "filters"}, set(), where)
    event = data["event"]
    if not isinstance(event, str) or event not in {"note_response", "delivery_settled"}:
        _fail("SEMANTIC_GAP", f"event {event!r} is not registered in P5", path=where)
    return ("p5_note_response" if event == "note_response" else "p5_delivery_settled",
            _filter_args(event, data["filters"], entities, where))


def _parse_branches(raw: Any) -> tuple[StoryBranch, ...]:
    if not isinstance(raw, list):
        _fail("INVALID_SCHEMA", "branches must be an array")
    result, branch_ids, storylet_ids = [], set(), set()
    for index, entry in enumerate(raw):
        where = f"branches[{index}]"
        data = _keys(entry, {"id", "when", "storylet"}, set(), where)
        branch_id = _identifier(data["id"], f"{where}.id")
        if branch_id in branch_ids:
            _fail("DUPLICATE_ID", f"duplicate branch id {branch_id!r}")
        branch_ids.add(branch_id)
        when = _keys(data["when"], {"event", "response"}, set(), f"{where}.when")
        if (when["event"] != "note_response" or not isinstance(when["response"], str)
                or when["response"] not in NOTE_RESPONSES):
            _fail("SEMANTIC_GAP", "branch guards only support actual accepted/rejected note_response events",
                  branch_id=branch_id)
        storylet = _keys(data["storylet"], {"id", "text"}, set(), f"{where}.storylet")
        storylet_id = _identifier(storylet["id"], f"{where}.storylet.id")
        if storylet_id in storylet_ids:
            _fail("DUPLICATE_ID", f"duplicate storylet id {storylet_id!r}")
        storylet_ids.add(storylet_id)
        if not isinstance(storylet["text"], str) or not storylet["text"].strip():
            _fail("INVALID_SCHEMA", f"{where}.storylet.text must be nonempty text")
        result.append(StoryBranch(branch_id, when["response"], storylet_id, storylet["text"]))
    return tuple(result)


def _parse_permissions(raw: Any, physical_budget: int) -> Mapping[str, Any]:
    data = _keys(raw, {"world_opportunities", "force_npc_response", "max_opportunities", "cost_budget"},
                 set(), "permissions")
    opportunities = data["world_opportunities"]
    if (not isinstance(opportunities, list)
            or any(not isinstance(op, str) for op in opportunities)
            or len(opportunities) != len(set(opportunities))
            or any(op not in WORLD_OPPORTUNITIES for op in opportunities)):
        _fail("PERMISSION_DENIED", "world_opportunities must be a unique subset of the registered passage actions")
    if data["force_npc_response"] is not False:
        _fail("PERMISSION_DENIED", "P5 does not authorize forced NPC responses")
    if _int(data["max_opportunities"], "permissions.max_opportunities", 0, 1) != 1:
        _fail("PERMISSION_DENIED", "P5 permits at most one world opportunity")
    budget = _int(data["cost_budget"], "permissions.cost_budget", 0, physical_budget)
    return MappingProxyType({"world_opportunities": tuple(opportunities),
                             "force_npc_response": False, "max_opportunities": 1,
                             "cost_budget": budget})


def _freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze_json(val) for key, val in value.items()})
    if isinstance(value, list):
        return tuple(_freeze_json(val) for val in value)
    return value


def load_bundle(raw_or_path: Any, registry: Registry | None = None,
                entities: Mapping[str, Any] | None = None, *,
                physical_budget: int = P5_INITIAL_PHYSICAL_BUDGET) -> AuthorBundle:
    """Parse a closed JSON package and compile only its registered TypedIR subset."""
    data = _json_source(raw_or_path)
    data = _keys(data, {"schema", "bundle_id", "version", "source", "constraints", "branches", "permissions"},
                 set(), "bundle")
    if data["schema"] != SCHEMA:
        _fail("UNSUPPORTED_BUNDLE_VERSION", f"schema must be {SCHEMA!r}")
    bundle_id = _identifier(data["bundle_id"], "bundle_id")
    version = _int(data["version"], "version", 1, 2**31 - 1)
    source = _identifier(data["source"], "source")
    if type(physical_budget) is not int or not 0 <= physical_budget <= P5_INITIAL_PHYSICAL_BUDGET:
        _fail("INVALID_BUDGET", f"physical_budget must be in [0, {P5_INITIAL_PHYSICAL_BUDGET}]")
    catalog = _entity_catalog(entities)
    registry = registry or p5_registry()
    if not isinstance(data["constraints"], list):
        _fail("INVALID_SCHEMA", "constraints must be an array")
    goals = tuple(_parse_goal(raw, registry, catalog) for raw in data["constraints"])
    goal_ids = [goal.constraint_id for goal in goals]
    if len(goal_ids) != len(set(goal_ids)):
        _fail("DUPLICATE_ID", "constraint IDs must be unique")
    branches = _parse_branches(data["branches"])
    permissions = _parse_permissions(data["permissions"], physical_budget)
    return AuthorBundle(bundle_id, version, source, goals, branches, permissions, _freeze_json(data),
                        MappingProxyType(dict(catalog)))


def _goal_signature(goal: CompiledGoal) -> str:
    return json.dumps(dict(goal.source), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class BundleStore:
    """In-memory atomic CAS for one active bundle; verdict archives remain service-owned."""
    def __init__(self, current: AuthorBundle, *, registry: Registry | None = None,
                 entities: Mapping[str, Any] | None = None,
                 physical_budget: int = P5_INITIAL_PHYSICAL_BUDGET):
        self._current = current
        self._registry = registry or p5_registry()
        self._entities = entities
        self._physical_budget = physical_budget
        self._lock = threading.RLock()

    @property
    def current(self) -> AuthorBundle:
        with self._lock:
            return self._current

    def replace(self, raw_or_path: Any, expected_version: int, *, now: int,
                completed_constraint_ids: set[str] | frozenset[str] = frozenset(),
                evidence_constraint_ids: set[str] | frozenset[str] = frozenset()) -> AuthorBundle:
        """Validate outside state mutation, then CAS+future-only checks under one lock."""
        if type(expected_version) is not int or type(now) is not int or now < 0:
            _fail("INVALID_EDIT", "expected_version and nonnegative now must be integers")
        with self._lock:
            current = self._current
            if expected_version != current.version:
                raise VersionConflict(expected_version, current.version)
        candidate = load_bundle(raw_or_path, self._registry, self._entities,
                                physical_budget=self._physical_budget)
        with self._lock:
            current = self._current
            if expected_version != current.version:
                raise VersionConflict(expected_version, current.version)
            if candidate.bundle_id != current.bundle_id or candidate.version != current.version + 1:
                _fail("INVALID_VERSION", "edit must preserve bundle_id and increment version exactly once",
                      current_bundle_id=current.bundle_id, candidate_bundle_id=candidate.bundle_id,
                      current_version=current.version, candidate_version=candidate.version)
            if dict(candidate.permissions) != dict(current.permissions):
                _fail("PERMISSION_ESCALATION", "runtime edits cannot change permissions or replenish author budget")
            old = {goal.constraint_id: goal for goal in current.goals}
            new = {goal.constraint_id: goal for goal in candidate.goals}
            protected = set(completed_constraint_ids) | set(evidence_constraint_ids)
            for goal_id, prior in old.items():
                updated = new.get(goal_id)
                same = updated is not None and _goal_signature(updated) == _goal_signature(prior)
                if same:
                    continue
                if goal_id in protected or prior.deadline <= now:
                    _fail("HISTORICAL_CONSTRAINT_IMMUTABLE",
                          f"constraint {goal_id!r} has settled evidence or a closed window",
                          constraint_id=goal_id, now=now)
                if updated is None:
                    continue
                # Existing unfinished requirements may have begun at scenario start.
                # Their prior-version verdict stays archived by the world service.
                if updated.deadline <= now:
                    _fail("HISTORICAL_CONSTRAINT_IMMUTABLE",
                          f"edited constraint {goal_id!r} must remain in the future",
                          constraint_id=goal_id, now=now)
            for goal_id, added in new.items():
                if goal_id not in old and added.start < now:
                    _fail("RETROACTIVE_CONSTRAINT", f"new constraint {goal_id!r} must start at or after now",
                          constraint_id=goal_id, now=now, start=added.start)
            self._current = candidate
            return candidate
