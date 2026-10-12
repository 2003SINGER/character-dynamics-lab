"""Strict adapters from sealed P5 evidence to the existing P5 Director input.

The adapter carries the complete symbolic state produced by the native P5
planning boundary. It deliberately does not reconstruct route eligibility,
resource accounting, or NPC facts from a guessed world model.
"""
from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from typing import Any, Mapping

from ..bundle import AuthorBundle
from ..planning import SCHEMA as DIRECTOR_SCHEMA
from ..planning import plan as director_plan


EVIDENCE_SCHEMA = "p5-live-trace-v1"
EVIDENCE_SOURCE = "native_platform_v0.p5.service._evidence"
SNAPSHOT_SCHEMA = "p5-mature-method-snapshot-v1"
STATUSES = {"NOT_ACTIVATED", "PENDING", "SATISFIED", "VIOLATED", "INDETERMINATE"}


@dataclass(frozen=True)
class MatureSnapshot:
    scene_id: str
    now: int
    horizon: int
    bundle_id: str
    bundle_version: int
    bundle_sha256: str
    evidence_sha256: str
    director_state: Mapping[str, Any]
    director_plan: Mapping[str, Any]
    verdicts: tuple[Mapping[str, Any], ...]
    typed_trace: Mapping[str, Any]
    actor_evidence: tuple[Mapping[str, Any], ...]
    ledger: tuple[Mapping[str, Any], ...]
    world_snapshots: tuple[Mapping[str, Any], ...]
    scene_binding: Mapping[str, Any]
    trace_identity: Mapping[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": SNAPSHOT_SCHEMA,
            "scene_id": self.scene_id,
            "now": self.now,
            "horizon": self.horizon,
            "bundle_identity": {"bundle_id": self.bundle_id,
                                "version": self.bundle_version,
                                "sha256": self.bundle_sha256},
            "evidence_sha256": self.evidence_sha256,
            "director_state": _plain(self.director_state),
            "director_plan": _plain(self.director_plan),
            "verdicts": _plain(self.verdicts),
            "typed_trace": _plain(self.typed_trace),
            "actor_evidence": _plain(self.actor_evidence),
            "ledger": _plain(self.ledger),
            "world_snapshots": _plain(self.world_snapshots),
            "scene_binding": _plain(self.scene_binding),
            "trace_identity": _plain(self.trace_identity),
        }


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _canonical_sha(value: Any) -> str:
    raw = json.dumps(_plain(value), sort_keys=True, ensure_ascii=False,
                     separators=(",", ":")).encode("utf-8")
    return sha256(raw).hexdigest()


def snapshot_from_native(bundle: AuthorBundle, evidence: Mapping[str, Any]) -> MatureSnapshot:
    """Validate a sealed P5 prefix and run the unchanged P5 Director planner.

    ``planning_view.state`` must be the exact authorized symbolic state made at the
    P5 planning boundary (including native route rows and budget counters). This
    function refuses to derive those fields from an incomplete evidence view.
    """
    if not isinstance(bundle, AuthorBundle):
        raise TypeError("bundle must be a validated P5 AuthorBundle")
    if not isinstance(evidence, Mapping) or evidence.get("evidence_schema") != EVIDENCE_SCHEMA:
        raise ValueError("native evidence schema is missing or unsupported")
    if evidence.get("source") != EVIDENCE_SOURCE:
        raise ValueError("native evidence source marker is missing or unsupported")
    if evidence.get("prefix_status") != "SEALED_COMPLETE":
        raise ValueError("high-level planning requires a SEALED_COMPLETE prefix")
    scene_id, now, horizon = evidence.get("scene_id"), evidence.get("now"), evidence.get("horizon")
    if not isinstance(scene_id, str) or not scene_id:
        raise ValueError("scene identity is required")
    if type(now) is not int or now < 0 or type(horizon) is not int or now > horizon:
        raise ValueError("native minute/horizon is malformed")
    identity = evidence.get("bundle_identity")
    if (not isinstance(identity, Mapping) or identity.get("bundle_id") != bundle.bundle_id
            or type(identity.get("version")) is not int or identity["version"] != bundle.version):
        raise ValueError("native trace and active AuthorBundle identity/version differ")
    frontier = evidence.get("complete_through")
    if (not isinstance(frontier, Mapping) or frontier.get("events") != now
            or frontier.get("values") != now):
        raise ValueError("native prefix frontiers do not match current minute")
    if evidence.get("run_status") not in {"COMPLETE", "INCOMPLETE"}:
        raise ValueError("native run status is malformed")

    planning_view = evidence.get("planning_view")
    if (not isinstance(planning_view, Mapping)
            or planning_view.get("schema") != "p5-native-planning-view-v1"
            or planning_view.get("source") != "native_platform_v0.p5.service._director_planning_view"):
        raise ValueError("native P5 planning view is missing or unsupported")
    planning_identity = planning_view.get("bundle_identity")
    bundle_sha = _canonical_sha(bundle.raw)
    if (planning_view.get("scene_id") != scene_id or planning_view.get("based_on_minute") != now
            or not isinstance(planning_identity, Mapping)
            or planning_identity.get("bundle_id") != bundle.bundle_id
            or planning_identity.get("version") != bundle.version
            or planning_identity.get("sha256") != bundle_sha
            or identity.get("sha256") != bundle_sha):
        raise ValueError("native P5 planning view is bound to another scene/minute/bundle")
    planning_frontier = planning_view.get("frontiers")
    if (not isinstance(planning_frontier, Mapping)
            or planning_frontier.get("events_through") != now
            or planning_frontier.get("values_through") != now):
        raise ValueError("native P5 planning view is not based on the current sealed frontier")
    director_state = planning_view.get("state")
    if not isinstance(director_state, Mapping):
        raise TypeError("planning_view.state must be a mapping")
    if director_state.get("now") != now or director_state.get("horizon") != horizon:
        raise ValueError("Director planning view is from a different minute or horizon")
    expected_state = {"now", "horizon", "routes", "spent_cost", "opportunities_used",
                      "verdicts", "physical_budget"}
    if set(director_state) != expected_state:
        raise ValueError(f"Director planning view must contain exactly {sorted(expected_state)}")

    raw_verdicts = evidence.get("verdicts")
    constraints = raw_verdicts.get("constraints") if isinstance(raw_verdicts, Mapping) else None
    if not isinstance(constraints, list):
        raise ValueError("native TypedIR verdict rows are missing")
    goal_ids = {goal.constraint_id for goal in bundle.goals}
    seen: dict[str, Mapping[str, Any]] = {}
    for row in constraints:
        if (not isinstance(row, Mapping) or row.get("constraint_id") not in goal_ids
                or row.get("status") not in STATUSES or row["constraint_id"] in seen):
            raise ValueError("native TypedIR verdict row is malformed, duplicate, or unbound")
        seen[row["constraint_id"]] = row
    if set(seen) != goal_ids:
        raise ValueError("native TypedIR verdict set does not exactly cover active bundle goals")
    director_verdicts = director_state.get("verdicts")
    if not isinstance(director_verdicts, list):
        raise ValueError("Director verdict input must be a list")
    normalized = {row.get("constraint_id"): row.get("status") for row in director_verdicts
                  if isinstance(row, Mapping)}
    if normalized != {key: row["status"] for key, row in seen.items()}:
        raise ValueError("Director and sealed native TypedIR verdicts differ")

    actors = evidence.get("actor_evidence")
    ledger = evidence.get("ledger")
    world_snapshots = evidence.get("world_snapshots")
    scene_binding = evidence.get("world_capability_projection")
    if (not isinstance(actors, list) or not isinstance(ledger, list)
            or not isinstance(world_snapshots, list) or not isinstance(scene_binding, Mapping)):
        raise ValueError("native actor evidence, ledger, W snapshots, and scene binding are required")
    actor_aliases = [row.get("actor_alias") for row in actors if isinstance(row, Mapping)]
    if sorted(actor_aliases) != ["A", "B"]:
        raise ValueError("snapshot must contain exactly the P5 A/B actor evidence rows")
    actor_rows = {row["actor_alias"]: row for row in actors if isinstance(row, Mapping)}
    if any(type(row.get("actor_id")) is not int for row in actor_rows.values()):
        raise ValueError("native actor IDs are required for task-binding provenance")
    if (scene_binding.get("schema") != "p5-planner-scene-binding-v1"
            or scene_binding.get("source") != "native_platform_v0.p5.service._planner_scene_binding"
            or scene_binding.get("scene_id") != scene_id):
        raise ValueError("native scene capability binding is missing or mismatched")
    room_roles = scene_binding.get("room_roles")
    bindings = scene_binding.get("task_bindings")
    if (not isinstance(room_roles, Mapping) or set(room_roles) != {"pickup", "side", "porch"}
            or any(type(value) is not int for value in room_roles.values())
            or not isinstance(bindings, Mapping) or set(bindings) != {"A", "B"}):
        raise ValueError("native scene room roles or actor task bindings are incomplete")
    for alias, binding in bindings.items():
        expected_item = ("courier_supply" if alias == "A" else "resident_parcel")
        if (not isinstance(binding, Mapping) or binding.get("actor_id") != actor_rows[alias]["actor_id"]
                or binding.get("item_alias") != expected_item
                or type(binding.get("item_id")) is not int
                or binding.get("source") != "existing_scene_actor_binding"
                or binding.get("destination_id") != room_roles["porch"]):
            raise ValueError(f"native task binding for actor {alias} is not the existing registered delivery")
    if (not world_snapshots or any(not isinstance(row, Mapping) for row in world_snapshots)
            or sorted(row.get("minute") for row in world_snapshots) != list(range(now + 1))):
        raise ValueError("native W snapshots must be complete and consecutive through the sealed minute")
    for row in world_snapshots:
        holders = row.get("holders")
        locations = row.get("item_locations")
        if not isinstance(holders, Mapping) or not isinstance(locations, Mapping):
            raise ValueError("native W snapshot lacks holder/location maps")
        for alias, binding in bindings.items():
            item_alias = binding["item_alias"]
            item_holders = holders.get(item_alias)
            if (not isinstance(item_holders, Mapping) or set(item_holders) != {"A", "B"}
                    or any(type(value) is not bool for value in item_holders.values())
                    or item_alias not in locations):
                raise ValueError("native W snapshot omits a bound task item state")
    if not isinstance(evidence.get("typed_trace"), Mapping):
        raise ValueError("serialized TypedIR trace is required")

    plan = director_plan(bundle, director_state)
    if (plan.get("schema") != DIRECTOR_SCHEMA or plan.get("bundle_id") != bundle.bundle_id
            or plan.get("bundle_version") != bundle.version):
        raise ValueError("unchanged P5 Director returned an unbound planning result")
    return MatureSnapshot(
        scene_id=scene_id, now=now, horizon=horizon, bundle_id=bundle.bundle_id,
        bundle_version=bundle.version, bundle_sha256=bundle_sha,
        evidence_sha256=_canonical_sha(evidence), director_state=_plain(director_state),
        director_plan=plan, verdicts=tuple(_plain(row) for row in constraints),
        typed_trace=_plain(evidence["typed_trace"]),
        actor_evidence=tuple(_plain(row) for row in actors), ledger=tuple(_plain(row) for row in ledger),
        world_snapshots=tuple(_plain(row) for row in world_snapshots),
        scene_binding=_plain(scene_binding),
        trace_identity={"scene_id": scene_id, "now": now,
                        "typed_trace_sha256": _canonical_sha(evidence["typed_trace"]),
                        "events_through": frontier["events"], "values_through": frontier["values"]})


__all__ = ["MatureSnapshot", "snapshot_from_native", "SNAPSHOT_SCHEMA"]
