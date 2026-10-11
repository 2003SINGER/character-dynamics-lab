"""A small, explicit author binding for the fixed Planner P0 fixture.

This is not a language parser. Callers must supply a versioned binding whose
clauses are in the allowlisted subset below; unsupported hard clauses remain
residual and prevent a SATISFIED compilation result.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
from typing import Any

from tools.planner_p0_v0.baseline_gate_v0.sabre_export import render_problem as render_atomic
from tools.planner_p0_v0.integration_v0.monitor import (
    EVENT_VERSION, build_typed_trace, integration_registry,
)
from tools.trajectory_constraints_v0.ast import EventCount, EventOrder, StrictOrder, Window
from tools.trajectory_constraints_v0.monitor import evaluate as evaluate_constraint


BINDING_VERSION = "p0-author-binding-v0.1"
SCENARIO_SCHEMA = "planner-p0-integration-v0"
REGISTERED_ABILITIES = frozenset({
    "look", "move", "wait", "cloud_seed", "dispatch_task", "offer_task",
    "deliver_shelter", "meet",
})

# Pinned committed raw records are regression fixtures. SHA-256 detects fixture
# drift; it does not authenticate a live native producer or defend against a
# coordinated edit to both this allowlist and repository history.
PINNED_RUNS = {
    "direct-clean-A": (
        "02_实验/Planner_P0_Baseline_Gate_v0/runs/p0bg-direct-clean-A-20261011T115534Z-4f5c03/run.json",
        "e2abcf6effc5a017ba712f9de7edc63fa583efa3568e85c2f479f2387f2cc577"),
    "direct-clean-B": (
        "02_实验/Planner_P0_Baseline_Gate_v0/runs/p0bg-direct-clean-B-20261011T115555Z-5a94b4/run.json",
        "50bd47e3b25e42e93302339692d886416935680332d1030b4849642aaf788998"),
    "high-causal-replan-A": (
        "02_实验/Planner_P0_Baseline_Gate_v0/runs/p0bg-high-causal-replan-A-20261011T115706Z-3fda2c/run.json",
        "4624139a40c744a1155a61f40304b91c61a313f43971221af1ae2cd31f4e4879"),
    "high-causal-replan-B": (
        "02_实验/Planner_P0_Baseline_Gate_v0/runs/p0bg-high-causal-replan-B-20261011T115825Z-b779d4/run.json",
        "d10f00372ff6d58503861dc57e23ec8d059ffc7d8d105940167df1281b97699e"),
    "route-repair-A": (
        "02_实验/Planner_P0_Baseline_Gate_v0/runs/p0bg-route-repair-A-20261011T115612Z-14caf8/run.json",
        "fd648cd22afb214006c097c8aa5173ff810233c5b0f4169116ebda62b19b5699"),
    "route-repair-B": (
        "02_实验/Planner_P0_Baseline_Gate_v0/runs/p0bg-route-repair-B-20261011T115633Z-c85e0a/run.json",
        "65dcf73fa6cb261b647b0c49b8f72bea32e43c12844504ca354dd74c80776751"),
}


@dataclass(frozen=True)
class AuthorClause:
    clause_id: str
    kind: str
    hard: bool = True
    # Source/actor/event fields are resolved only through this fixture's
    # registry roles. A caller cannot inject a new event name or game ability.
    event: str | None = None
    before: str | None = None
    after: str | None = None
    actor: str | None = None


@dataclass(frozen=True)
class AuthorBinding:
    binding_id: str
    version: str
    source_text: str
    deadline_minute: int
    clauses: tuple[AuthorClause, ...]
    derived_subgoals: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    residual_obligations: tuple[str, ...] = ()


@dataclass(frozen=True)
class Compilation:
    binding_id: str
    binding_version: str
    binding_digest: str
    compile_record: "CompileRecord"
    status: str
    sabre_problem: str | None
    constraints: tuple[Any, ...]
    residual_obligations: tuple[str, ...]
    hard_residual_obligations: tuple[str, ...]
    soft_unscored_obligations: tuple[str, ...]
    derived_subgoals: tuple[str, ...]
    assumptions: tuple[str, ...]
    projection_map: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class CompileRecord:
    binding: AuthorBinding
    fixture_id: str
    fixture_sha256: str
    role_to_entity_ids: tuple[tuple[str, int], ...]
    renderer_source: str
    renderer_source_sha256: str
    monitor_source: str
    monitor_source_sha256: str
    semantic_boundary: str


def _binding_digest(binding: AuthorBinding) -> str:
    payload = {
        "binding_id": binding.binding_id, "version": binding.version,
        "source_text": binding.source_text, "deadline_minute": binding.deadline_minute,
        "clauses": [c.__dict__ for c in binding.clauses],
        "derived_subgoals": binding.derived_subgoals,
        "assumptions": binding.assumptions,
        "residual_obligations": binding.residual_obligations,
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                            ensure_ascii=False).encode("utf-8")).hexdigest()


def _source_digest(repo_root: Path, relative: str) -> str:
    return sha256((repo_root / relative).read_bytes()).hexdigest()


def _compile_record(root: Path, binding: AuthorBinding, evidence: dict) -> CompileRecord:
    snapshot, scene = evidence["initial_snapshot"], evidence["scene_identity"]
    pairs = []
    for role, entity_id in snapshot["rooms"].items():
        pairs.append((f"room:{role}", int(entity_id)))
    for role, entity in scene["actors"].items():
        pairs.append((f"actor:{role}", int(entity["id"])))
    pairs.append(("item:shelter_kit", int(scene["item"]["id"])))
    renderer = "tools/planner_p0_v0/baseline_gate_v0/sabre_export.py"
    monitor = "tools/planner_p0_v0/integration_v0/monitor.py"
    return CompileRecord(
        binding=binding, fixture_id=evidence["fixture_id"],
        fixture_sha256=evidence["sha256"], role_to_entity_ids=tuple(pairs),
        renderer_source=renderer, renderer_source_sha256=_source_digest(root, renderer),
        monitor_source=monitor, monitor_source_sha256=_source_digest(root, monitor),
        semantic_boundary=("hand-authored Sabre candidate abstraction; native action/ledger semantics "
                           "remain owned by P0 integration and checked only by pinned TypedIR evidence"))


def _validate_binding(binding: AuthorBinding) -> None:
    if not isinstance(binding, AuthorBinding):
        raise TypeError("binding must be an AuthorBinding")
    if (not isinstance(binding.binding_id, str) or not binding.binding_id
            or not isinstance(binding.version, str) or not binding.version
            or not isinstance(binding.source_text, str) or not binding.source_text
            or type(binding.deadline_minute) is not int
            or not 0 <= binding.deadline_minute <= 24
            or not isinstance(binding.clauses, tuple)
            or not all(isinstance(c, AuthorClause) for c in binding.clauses)
            or not isinstance(binding.derived_subgoals, tuple)
            or not all(isinstance(x, str) for x in binding.derived_subgoals)
            or not isinstance(binding.assumptions, tuple)
            or not all(isinstance(x, str) for x in binding.assumptions)
            or not isinstance(binding.residual_obligations, tuple)):
        raise ValueError("INVALID_BINDING_SCHEMA: malformed closed P0 binding")
    if not all(isinstance(x, str) for x in binding.residual_obligations):
        raise ValueError("INVALID_BINDING_SCHEMA: residual obligations must be strings")
    ids = [c.clause_id for c in binding.clauses]
    if (not binding.clauses or any(not isinstance(i, str) or not i for i in ids)
            or len(set(ids)) != len(ids)):
        raise ValueError("INVALID_BINDING_SCHEMA: clause IDs must be nonempty and unique")
    for clause in binding.clauses:
        if (type(clause.hard) is not bool
                or not isinstance(clause.kind, str) or not clause.kind
                or any(v is not None and not isinstance(v, str)
                       for v in (clause.event, clause.before, clause.after, clause.actor))):
            raise ValueError("INVALID_BINDING_SCHEMA: hard and kind have fixed types")


def p0_author_binding(deadline_minute: int = 24) -> AuthorBinding:
    """Return the concrete, human-bound P0 request used in this pilot."""
    if type(deadline_minute) is not int or not 0 <= deadline_minute <= 24:
        raise ValueError("P0 absolute deadline must be an integer minute in [0, 24]")
    return AuthorBinding(
        binding_id="p0-deliver-observe-meet",
        version=BINDING_VERSION,
        source_text=("A delivers the shelter kit; B observes the storm; both meet "
                     "after delivery and B's observation, within the scenario deadline."),
        deadline_minute=deadline_minute,
        clauses=(
            AuthorClause("deliver-once", "event_once", event="p0_delivery", actor="A"),
            AuthorClause("observe-once", "event_once", event="p0_storm_observation", actor="B"),
            AuthorClause("meeting-once", "event_once", event="p0_meeting_witness"),
            AuthorClause("delivery-before-meeting", "before", before="p0_delivery", after="p0_meeting_witness"),
            AuthorClause("observation-before-meeting", "before", before="p0_storm_observation", after="p0_meeting_witness"),
        ),
        derived_subgoals=("deliver shelter kit to Inn", "B learns storm via look", "meet at Inn"),
        assumptions=("P0 role aliases resolve to the current authorized snapshot IDs",
                     "native settled event minute is the pre-action minute"),
    )


def _validate_snapshot(snapshot: dict, scene_identity: dict | None, binding: AuthorBinding,
                       requested_abilities: tuple[str, ...]) -> None:
    if not isinstance(snapshot, dict) or snapshot.get("schema") != SCENARIO_SCHEMA:
        raise ValueError("UNBOUND: snapshot is not the registered P0 integration schema")
    _validate_binding(binding)
    if binding.version != BINDING_VERSION:
        raise ValueError("STALE_BINDING_VERSION: unsupported binding version")
    if type(binding.deadline_minute) is not int or not 0 <= binding.deadline_minute <= 24:
        raise ValueError("UNBOUND: deadline is outside the registered absolute-minute horizon")
    if snapshot.get("mode") != "direct":
        raise PermissionError("UNAUTHORIZED_BINDING: this prototype is limited to direct-control fixtures")
    if (not isinstance(requested_abilities, tuple)
            or not all(isinstance(a, str) for a in requested_abilities)
            or len(set(requested_abilities)) != len(requested_abilities)):
        raise ValueError("INVALID_AUTHORITY_BINDING: abilities must be a unique tuple of registered names")
    if not isinstance(scene_identity, dict) or scene_identity.get("scene_id") != snapshot.get("scene_id"):
        raise ValueError("UNBOUND: native scene identity is required to resolve role aliases")
    if scene_identity.get("schema") != SCENARIO_SCHEMA or scene_identity.get("mode") != snapshot.get("mode"):
        raise ValueError("UNBOUND: scene schema or mode differs from snapshot")
    rooms = snapshot.get("rooms", {})
    actors = snapshot.get("actors", {})
    items = snapshot.get("items", {})
    if set(rooms) != {"junction", "side_passage", "inn"}:
        raise ValueError("UNBOUND: room role registry does not match P0")
    if set(actors) != {"A", "B", "player"} or set(items) != {"shelter_kit"}:
        raise ValueError("UNBOUND: actor/item role registry does not match P0")
    scene_rooms, scene_actors, scene_item = (scene_identity.get("rooms", {}),
                                             scene_identity.get("actors", {}),
                                             scene_identity.get("item", {}))
    def entity_id(row):
        return row.get("id") if isinstance(row, dict) else row
    room_ids = {k: entity_id(v) for k, v in rooms.items()}
    bound_room_ids = {k: entity_id(v) for k, v in scene_rooms.items()}
    actor_ids = {k: entity_id(v) for k, v in scene_actors.items()}
    if (room_ids != bound_room_ids or set(actor_ids) != {"A", "B", "player"}
            or any(type(v) is not int or v <= 0 for v in room_ids.values())
            or any(type(v) is not int or v <= 0 for v in actor_ids.values())
            or len(set(actor_ids.values())) != len(actor_ids)
            or len(set(room_ids.values())) != len(room_ids)
            or entity_id(items["shelter_kit"]) != entity_id(scene_item)
            or type(entity_id(scene_item)) is not int
            or scene_item.get("alias") != "shelter_kit"):
        raise ValueError("UNBOUND: role-to-live-scene entity ID binding failed")
    unknown = set(requested_abilities) - REGISTERED_ABILITIES
    if unknown:
        raise PermissionError(f"UNREGISTERED_ABILITY: {sorted(unknown)}")
    if (snapshot.get("clock", {}).get("now") != 0 or snapshot.get("weather") != "clear"
            or snapshot.get("pending_cloud") is not None
            or any(a.get("active_task") is not None or "storm" in a.get("known_weather", [])
                   for a in actors.values())
            or items["shelter_kit"].get("holder_role") is not None):
        raise ValueError("UNBOUND_PREFIX: planning counters require the clean initial state")


def _typed_constraints(binding: AuthorBinding) -> tuple[tuple[Any, ...], tuple[str, ...], tuple[str, ...], tuple[tuple[str, str], ...]]:
    registry = integration_registry()
    window = Window(Fraction(0), Fraction(binding.deadline_minute), True, True)
    counts = {
        "p0_delivery": ("A", {"actor": "A", "item": "shelter_kit", "room": "inn"}),
        "p0_storm_observation": ("B", {"actor": "B", "weather": "storm"}),
        "p0_meeting_witness": (None, {"weather": "storm", "B_observed_storm": True}),
    }
    built, hard_residual, soft_residual, mapping = [], list(binding.residual_obligations), [], []
    for clause in binding.clauses:
        if not clause.hard:
            # Soft assessment has no planner/monitor score semantics in this v0.
            soft_residual.append(f"{clause.clause_id}: soft clause has no registered evaluator")
            continue
        if clause.kind == "event_once" and (clause.before is not None or clause.after is not None):
            reason = f"{clause.clause_id}: event_once cannot contain before/after fields"
            hard_residual.append(reason)
            mapping.append((clause.clause_id, f"Sabre:residual; TypedIR:residual; residual:{reason}"))
        elif clause.kind == "event_once" and clause.event in counts:
            expected_actor, filt = counts[clause.event]
            if clause.actor not in (None, expected_actor):
                hard_residual.append(f"{clause.clause_id}: actor does not match registered event binding")
                mapping.append((clause.clause_id,
                                "Sabre:residual; TypedIR:residual; authority/time: unresolved; "
                                "residual:actor does not match registered event binding"))
                continue
            registry.resolve(clause.event, EVENT_VERSION)
            built.append(EventCount(clause.clause_id, clause.event, EVENT_VERSION, window,
                                    minimum=1, maximum=1, event_filter=filt))
            planner_term = {
                "p0_delivery": "delivery_count() == 1",
                "p0_storm_observation": "storm_observation_count(B) == 1",
                "p0_meeting_witness": "meeting_count() == 1",
            }[clause.event]
            mapping.append((clause.clause_id,
                            f"Sabre:{planner_term}; TypedIR:EventCount({clause.event}, exact=1); "
                            "authority: registered P0 action + committed native event; "
                            "time: pre-action minute in absolute [0, deadline]; "
                            "assumption: fresh empty P0 event prefix"))
        elif (clause.kind == "before" and (clause.event is not None or clause.actor is not None)):
            reason = f"{clause.clause_id}: before cannot contain event/actor fields"
            hard_residual.append(reason)
            mapping.append((clause.clause_id, f"Sabre:residual; TypedIR:residual; residual:{reason}"))
        elif (clause.kind == "before" and (clause.before, clause.after) in {
              ("p0_delivery", "p0_meeting_witness"),
              ("p0_storm_observation", "p0_meeting_witness")}):
            registry.resolve(clause.before, EVENT_VERSION)
            registry.resolve(clause.after, EVENT_VERSION)
            _, before_filter = counts[clause.before]
            _, after_filter = counts[clause.after]
            # EventOrder is the existing existential DISTINCT_PAIR monitor.
            built.append(EventOrder(clause.clause_id, clause.before, EVENT_VERSION,
                                    clause.after, EVENT_VERSION, StrictOrder.EVENT_KEY,
                                    window, before_filter=before_filter,
                                    after_filter=after_filter))
            planner_pair = {
                ("p0_delivery", "p0_meeting_witness"): "delivery_time() < meeting_time()",
                ("p0_storm_observation", "p0_meeting_witness"): "observation_time(B) < meeting_time()",
            }[(clause.before, clause.after)]
            mapping.append((clause.clause_id,
                            f"Sabre:meeting guard {planner_pair}; "
                            "TypedIR:EventOrder(EXISTS_DISTINCT_PAIR, EVENT_KEY); "
                            "authority: registered P0 actions + committed native events; "
                            "time: event pre-action minute; assumption: serial one-minute P0 actions"))
        else:
            reason = f"{clause.clause_id}: unsupported hard clause {clause.kind!r}"
            hard_residual.append(reason)
            mapping.append((clause.clause_id,
                            f"Sabre:residual; TypedIR:residual; authority/time: unresolved; residual:{reason}"))
    return tuple(built), tuple(hard_residual), tuple(soft_residual), tuple(mapping)


def compile_binding(binding: AuthorBinding | None = None, *, repo_root: str | Path | None = None,
                    fixture_id: str | None = None) -> Compilation:
    binding = binding or p0_author_binding()
    if fixture_id is None:
        raise ValueError("UNVERIFIED_INPUT: compile only from the six pinned committed P0 fixtures")
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[3]
    evidence = load_pinned_native_trace(root, fixture_id)
    snapshot, scene_identity = evidence["initial_snapshot"], evidence["scene_identity"]
    compile_record = _compile_record(root, binding, evidence)
    # This fixed author binding requires these registered abilities. The
    # caller cannot weaken the permission check by supplying a shorter list.
    _validate_snapshot(snapshot, scene_identity, binding, ("look", "dispatch_task", "meet"))
    constraints, hard_residual, soft_residual, mapping = _typed_constraints(binding)
    residual = hard_residual + soft_residual
    if hard_residual:
        return Compilation(binding.binding_id, binding.version, _binding_digest(binding), compile_record,
                           "PARTIAL_UNRESOLVED", None,
                           constraints, residual, hard_residual, soft_residual, binding.derived_subgoals,
                           binding.assumptions, mapping)

    # Start from the existing A atomic renderer, then install only the guards
    # implied by the bound clauses. Native meeting feasibility (world storm,
    # delivery, actor positions, observed storm) remains an environmental fact.
    problem = render_atomic(snapshot, "A")
    deadline = binding.deadline_minute
    property_anchor = "property met_witness() : boolean;"
    tracking = ("property delivery_count() : number;\n"
                "property delivery_time() : number;\n"
                "property storm_observation_count(character : character) : number;\n"
                "property observation_time(character : character) : number;\n"
                "property meeting_count() : number;\n"
                "property meeting_time() : number;")
    if problem.count(property_anchor) != 1:
        raise ValueError("P0 typed fluent declarations changed; refusing incomplete projection")
    problem = problem.replace(property_anchor, property_anchor + "\n" + tracking, 1)
    init_anchor = f"now() = {snapshot['clock']['now']};"
    init_tracking = ("delivery_count() = 0;\n"
                     "delivery_time() = -1;\n"
                     "storm_observation_count(A) = 0;\n"
                     "storm_observation_count(B) = 0;\n"
                     "observation_time(A) = -1;\n"
                     "observation_time(B) = -1;\n"
                     "meeting_count() = 0;\n"
                     "meeting_time() = -1;")
    if problem.count(init_anchor) != 1:
        raise ValueError("P0 initial clock anchor changed; refusing incomplete projection")
    problem = problem.replace(init_anchor, init_anchor + "\n" + init_tracking, 1)

    # Counters make exact-once event requirements explicit in the candidate
    # model; they are planning bookkeeping, never native-world state.
    drop_old = "!shelter_delivered() & now() < 24;"
    drop_new = "!shelter_delivered() & delivery_count() == 0 & now() < 24;"
    if drop_old not in problem:
        raise ValueError("P0 DROP guard changed; refusing incomplete projection")
    problem = problem.replace(drop_old, drop_new, 1)
    drop_effect = "!kit_held(A) & shelter_delivered() & now() = now() + 1;"
    drop_effect_new = ("!kit_held(A) & shelter_delivered() & delivery_count() = delivery_count() + 1 & "
                       "delivery_time() = now() & now() = now() + 1;")
    if problem.count(drop_effect) != 1:
        raise ValueError("P0 DROP effect changed; refusing incomplete projection")
    problem = problem.replace(drop_effect, drop_effect_new, 1)

    # baseline_gate already adds !knows_storm(actor); add the deadline and count guard.
    look_anchor = "!knows_storm(actor) & now() < 24;"
    if problem.count(look_anchor) != 1:
        raise ValueError("P0 look guard changed; refusing incomplete projection")
    problem = problem.replace(look_anchor,
                              "!knows_storm(actor) & storm_observation_count(actor) == 0 & now() < 24;", 1)
    look_effect = "if(weather() == Storm) knows_storm(actor) & now() = now() + 1 else now() = now() + 1;"
    look_effect_new = ("if(weather() == Storm) knows_storm(actor) & "
                       "storm_observation_count(actor) = storm_observation_count(actor) + 1 & "
                       "observation_time(actor) = now() & now() = now() + 1 else now() = now() + 1;")
    if problem.count(look_effect) != 1:
        raise ValueError("P0 look effect changed; refusing incomplete projection")
    problem = problem.replace(look_effect, look_effect_new, 1)

    meeting_guard = "at(A) == Inn & at(B) == Inn & !met_witness() & now() < 24;"
    meeting_requirements = []
    supported_orders = {(c.before, c.after) for c in binding.clauses
                        if c.hard and c.kind == "before"}
    if ("p0_delivery", "p0_meeting_witness") in supported_orders:
        meeting_requirements.append("delivery_count() == 1 & delivery_time() < now()")
    if ("p0_storm_observation", "p0_meeting_witness") in supported_orders:
        meeting_requirements.append("storm_observation_count(B) == 1 & observation_time(B) < now()")
    meeting_requirements.append("meeting_count() == 0")
    meeting_guard_new = meeting_guard.replace("!met_witness()", "!met_witness() & " + " & ".join(meeting_requirements))
    if problem.count(meeting_guard) != 1:
        raise ValueError("P0 meeting guard changed; refusing incomplete projection")
    problem = problem.replace(meeting_guard, meeting_guard_new, 1)
    meet_effect = "met_witness() & now() = now() + 1 else now() = now() + 1;"
    meet_effect_new = ("met_witness() & meeting_count() = meeting_count() + 1 & "
                       "meeting_time() = now() & now() = now() + 1 else now() = now() + 1;")
    if problem.count(meet_effect) != 1:
        raise ValueError("P0 meeting effect changed; refusing incomplete projection")
    problem = problem.replace(meet_effect, meet_effect_new, 1)

    # Apply the closed absolute deadline to every native action precondition,
    # while preserving the native 24-minute maximum. Settlement at t == T is
    # allowed because receipts carry the pre-action minute.
    problem = problem.replace("now() < 24;", f"now() <= {deadline} & now() < 24;")
    # Keep the native storm-seed due cap and also respect the author window.
    problem = problem.replace("now() <= 22;", f"now() <= 22 & now() <= {deadline};")

    # Only hard event-existence clauses become conjunctive planner goals.
    goal_terms = []
    for clause in binding.clauses:
        if not clause.hard:
            continue
        term = {"p0_delivery": "delivery_count() == 1",
                "p0_storm_observation": "storm_observation_count(B) == 1",
                "p0_meeting_witness": "meeting_count() == 1"}.get(clause.event)
        if clause.kind == "event_once" and term and term not in goal_terms:
            goal_terms.append(term)
    if not goal_terms:
        return Compilation(binding.binding_id, binding.version, _binding_digest(binding), compile_record,
                           "PARTIAL_UNRESOLVED", None,
                           constraints, ("no supported hard planner goal",),
                           ("no supported hard planner goal",), soft_residual,
                           binding.derived_subgoals, binding.assumptions, mapping)
    utility = "utility(): if(" + " & ".join(goal_terms) + ") 1 else 0;"
    # Keep actor-local utilities for diagnostics; they do not define author success.
    old_utility = next((line for line in problem.splitlines() if line.startswith("utility():")), None)
    if old_utility is None:
        raise ValueError("P0 utility anchor missing")
    problem = problem.replace(old_utility, utility, 1)
    return Compilation(binding.binding_id, binding.version, _binding_digest(binding), compile_record,
                       "COMPILED_WITH_SOFT_RESIDUAL" if soft_residual else "COMPILED", problem,
                       constraints, residual, (), soft_residual, binding.derived_subgoals,
                       binding.assumptions, mapping)


def plan_binding_metadata(compilation: Compilation) -> dict:
    """Fields that an executor must carry unchanged with a candidate plan."""
    return {"binding_id": compilation.binding_id,
            "binding_version": compilation.binding_version,
            "binding_digest": compilation.binding_digest,
            "fixture_id": compilation.compile_record.fixture_id,
            "fixture_sha256": compilation.compile_record.fixture_sha256}


def assert_plan_binding_current(plan: dict, active: AuthorBinding,
                                compilation: Compilation) -> None:
    """Reject stale plan content or a plan compiled from another pinned scene."""
    if not isinstance(plan, dict) or plan.get("binding_id") != active.binding_id:
        raise ValueError("UNBOUND_PLAN: plan does not name the active author binding")
    if plan.get("binding_version") != active.version:
        raise ValueError("STALE_BINDING_VERSION: recompile before dispatch")
    if plan.get("binding_digest") != _binding_digest(active):
        raise ValueError("STALE_BINDING_CONTENT: recompile before dispatch")
    if (compilation.binding_id != active.binding_id
            or compilation.binding_version != active.version
            or compilation.binding_digest != _binding_digest(active)):
        raise ValueError("STALE_COMPILATION: active binding changed")
    if (plan.get("fixture_id") != compilation.compile_record.fixture_id
            or plan.get("fixture_sha256") != compilation.compile_record.fixture_sha256):
        raise ValueError("STALE_SCENE_BINDING: recompile against the active scene")


def classify_candidate_result(result: dict, compilation: Compilation) -> str:
    """Keep translation failure, search budget, and no-plan meanings distinct."""
    if compilation.status == "PARTIAL_UNRESOLVED":
        return "UNBOUND_OR_RESIDUAL"
    status = result.get("status") if isinstance(result, dict) else None
    if status == "BUDGET_LIMIT":
        return "SEARCH_BUDGET"
    if status == "NATIVE_NO_SOLUTION":
        return "NO_PLAN_IN_EXPORTED_DOMAIN"
    if status == "SUCCESS":
        return "PLAN_FOUND_NOT_EXECUTION_EVIDENCE"
    if status == "PROCESS_TIMEOUT":
        return "WRAPPER_TIMEOUT"
    return "PLANNER_ERROR_OR_UNKNOWN"


def load_pinned_native_trace(repo_root: str | Path, fixture_id: str) -> dict:
    """Load one immutable committed P0 run after digest and identity checks.

    This establishes fixture integrity relative to this source allowlist only;
    it is not cryptographic authentication of the original native server.
    """
    if fixture_id not in PINNED_RUNS:
        raise ValueError("UNKNOWN_FIXTURE: only six committed P0 runs are allowed")
    relative, expected = PINNED_RUNS[fixture_id]
    raw = (Path(repo_root) / relative).read_bytes()
    observed = sha256(raw).hexdigest()
    if observed != expected:
        raise ValueError("FIXTURE_DIGEST_MISMATCH: receipt evidence is indeterminate")
    document = json.loads(raw)
    case, variant = fixture_id.rsplit("-", 1)
    if document.get("case") != case or document.get("variant") != variant:
        raise ValueError("FIXTURE_ID_MISMATCH: receipt evidence is indeterminate")
    if document.get("status") != "COMPLETED":
        raise ValueError("FIXTURE_NOT_COMPLETED: receipt evidence is indeterminate")
    trace = document.get("native_trace")
    if not isinstance(trace, dict) or trace.get("schema") != SCENARIO_SCHEMA:
        # Existing committed records may use the integration trace schema; only
        # the fixed digest and embedded complete-prefix checks qualify them.
        if not isinstance(trace, dict) or not isinstance(trace.get("events"), list):
            raise ValueError("FIXTURE_TRACE_MISSING: receipt evidence is indeterminate")
    if not isinstance(document.get("initial_snapshot"), dict) or not isinstance(document.get("scene"), dict):
        raise ValueError("FIXTURE_BINDING_METADATA_MISSING: evidence is indeterminate")
    return {"fixture_id": fixture_id, "sha256": observed,
            "trust_scope": "pinned committed fixture bytes; producer identity not authenticated",
            "trace": trace, "initial_snapshot": document.get("initial_snapshot"),
            "scene_identity": document.get("scene")}


def evaluate_binding(binding: AuthorBinding, compilation: Compilation, *, repo_root: str | Path | None = None,
                     fixture_id: str | None = None) -> dict:
    """Evaluate this compilation's own TypedIR projection on a pinned raw run.

    The consumer reloads and re-hashes the raw bytes; a caller cannot replace a
    nested trace mapping while retaining a previously returned digest.
    """
    if fixture_id is None:
        return {"status": "INDETERMINATE", "reason": "NO_PINNED_NATIVE_EVIDENCE",
                "soft_status": "UNSCORED", "constraints": []}
    root = Path(repo_root) if repo_root is not None else Path(__file__).resolve().parents[3]
    evidence = load_pinned_native_trace(root, fixture_id)
    if (compilation.binding_id != binding.binding_id
            or compilation.binding_version != binding.version
            or compilation.binding_digest != _binding_digest(binding)
            or compilation.compile_record.binding != binding
            or compilation.compile_record.fixture_id != fixture_id
            or compilation.compile_record.fixture_sha256 != evidence["sha256"]):
        raise ValueError("STALE_COMPILATION: active binding content differs from compiled projections")
    trace_data = evidence["trace"]
    trace = build_typed_trace(trace_data)
    registry = integration_registry()
    rows = []
    for constraint in compilation.constraints:
        for result in evaluate_constraint(constraint, trace, registry):
            rows.append({"constraint_id": result.constraint_id,
                         "status": result.verdict.value, "reason": result.reason,
                         "witness": list(result.witness) if isinstance(result.witness, tuple) else result.witness})
    statuses = {r["status"] for r in rows}
    prefix, sealed, now = trace_data.get("events"), trace_data.get("sealed_through"), trace_data.get("snapshot", {}).get("clock", {}).get("now")
    frontier = trace_data.get("ledger_frontier")
    complete = (type(now) is int and type(sealed) is int and sealed >= now
                and type(frontier) is int and frontier == len(prefix)
                and [r.get("sequence") for r in prefix if isinstance(r, dict)] == list(range(1, frontier + 1)))
    if "VIOLATED" in statuses:
        status = "VIOLATED"
    elif compilation.hard_residual_obligations or not complete or not rows:
        status = "INDETERMINATE"
    elif "INDETERMINATE" in statuses:
        status = "INDETERMINATE"
    elif "PENDING" in statuses or "NOT_ACTIVATED" in statuses:
        status = "PENDING"
    else:
        status = "SATISFIED"
    return {"status": status, "fixture_id": fixture_id,
            "fixture_sha256": evidence["sha256"],
            "trust_scope": evidence["trust_scope"],
            "complete_ledger_prefix": complete, "constraints": rows,
            "hard_residual_obligations": list(compilation.hard_residual_obligations),
            "soft_unscored_obligations": list(compilation.soft_unscored_obligations),
            "soft_status": "UNSCORED" if compilation.soft_unscored_obligations else "NOT_REQUESTED"}
