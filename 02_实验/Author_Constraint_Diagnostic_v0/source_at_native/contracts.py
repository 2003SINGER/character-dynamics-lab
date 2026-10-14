"""Experiment-local provenance/temporal records; no new world database."""
from __future__ import annotations

from dataclasses import dataclass, replace, asdict
import json
from pathlib import Path


@dataclass(frozen=True)
class Constraint:
    id: str
    source: str
    strength: str
    temporal: str
    condition: tuple[str, ...]
    evidence_source: str
    status: str = "PENDING"
    plan_id: str | None = None
    revoke_when: str | None = None
    witness_sequences: tuple[int, ...] = ()

    def __post_init__(self):
        if self.source not in {"AUTHOR", "PLANNER", "GAME"}:
            raise ValueError("unregistered source")
        if self.strength not in {"MUST", "PLAN_DEPENDENCY", "SOFT"}:
            raise ValueError("unregistered strength")
        if self.temporal not in {"AT_END", "EVENTUALLY", "ALWAYS", "BEFORE"}:
            raise ValueError("unregistered temporal semantics")
        if self.source == "PLANNER" and not self.plan_id:
            raise ValueError("planner dependency must identify a plan")


def author_constraints() -> tuple[Constraint, ...]:
    rows = []
    for name, atom in (("arrive-west", ("at", "player", "WESTBANK")),
                       ("keys", ("carrying", "keys")),
                       ("lamp", ("carrying", "lamp")), ("lamp-on", ("lamp_on",))):
        rows.append(Constraint("author-" + name, "AUTHOR", "MUST", "AT_END", atom,
                               "fresh complete native look/inventory and lamp feedback"))
    rows.extend((
        Constraint("author-build-bridge", "AUTHOR", "MUST", "EVENTUALLY",
                   ("bridge_created",), "native wave rod feedback: bridge now spans"),
        Constraint("author-build-before-arrival", "AUTHOR", "MUST", "BEFORE",
                   ("bridge_created", "arrive_west"), "strict native step sequence"),
        Constraint("author-no-death", "AUTHOR", "MUST", "ALWAYS",
                   ("no_death_ever",), "entire complete native interval"),
    ))
    return tuple(rows)


def plan_dependencies(plan_id: str, plan) -> tuple[Constraint, ...]:
    # Dependency comes from the actual search result, not a hand-written path.
    return tuple(Constraint(f"dependency-{i}-{k}", "PLANNER", "PLAN_DEPENDENCY",
                            "BEFORE", atom, op.source, plan_id=plan_id,
                            revoke_when="unexecuted consuming action withdrawn with this plan")
                 for i, op in enumerate(plan) for k, atom in enumerate(op.preconditions))


def retire_plan(records: tuple[Constraint, ...], plan_id: str) -> tuple[Constraint, ...]:
    # Completed evidence, author obligations and native laws are never deleted.
    return tuple(replace(row, status="CANCELLED")
                 if row.source == "PLANNER" and row.plan_id == plan_id
                 and row.status == "PENDING" and not row.witness_sequences else row
                 for row in records)


def obligation_phase(*, capability: bool, monitor: bool, ended: bool, verdict: str) -> dict:
    if not capability:
        return {"binding": "UNSUPPORTED_CAPABILITY", "verification": "UNKNOWN"}
    if not monitor:
        return {"binding": "BOUND_BUT_UNVERIFIABLE", "verification": "UNKNOWN"}
    return {"binding": "BOUND", "verification": verdict if ended or verdict == "FAIL" else "PENDING"}


def native_plan_lifecycle(trace: Path, temporal: dict) -> dict:
    # Provenance bookkeeping only. This never supplies facts to the author
    # monitor or claims that every modeled precondition is native truth.
    from tools.open_adventure_planning_v0.domain import OPERATORS
    with trace.open(encoding="utf-8") as stream:
        rows = [json.loads(line) for line in stream]
    lookup = {(op.name, op.args, op.command): op for op in OPERATORS}
    successful = {r["step_sequence"] for r in rows if r.get("event") == "reconciliation"
                  and r.get("status") not in {"INCOMPLETE", "UNMODELED_EVENT"}}
    records = author_constraints()
    previous, replacements = None, []
    for row in rows:
        if row.get("event") != "decision":
            continue
        plan_id = row["plan_hash"]
        if previous is not None:
            records = retire_plan(records, previous)
            replacements.append({"retired_plan": previous, "replacement_plan": plan_id,
                                 "only_unexecuted_planner_dependencies_retired": True})
        plan = tuple(lookup[(p["operator"], tuple(p["args"]), p["command"])] for p in row["predicted_plan"])
        deps = plan_dependencies(plan_id, plan)
        # Avoid duplicate dependency IDs across successively shortened plans.
        deps = tuple(replace(r, id=plan_id[:12] + "-" + r.id) for r in deps)
        if row["step_sequence"] in successful:
            deps = tuple(replace(r, status="PASS", witness_sequences=(row["step_sequence"],))
                         if r.id.endswith(tuple(f"dependency-0-{k}" for k in range(len(plan[0].preconditions)))) else r
                         for r in deps)
        records += deps
        previous = plan_id
    if previous:
        records = retire_plan(records, previous)
    statuses = temporal.get("obligations", {})
    witnesses = {
        "author-build-bridge": tuple(temporal.get("bridge_created_sequences", [])),
        "author-build-before-arrival": tuple(temporal.get("bridge_created_sequences", [])[:1] + temporal.get("west_arrival_sequences", [])[:1]),
        "author-arrive-west": tuple(temporal.get("west_arrival_sequences", [])[-1:]),
        "author-keys": (temporal["last_inventory"]["sequence"],) if temporal.get("last_inventory") else (),
        "author-lamp": (temporal["last_inventory"]["sequence"],) if temporal.get("last_inventory") else (),
        "author-lamp-on": (temporal["lamp_feedback_sequence"],) if temporal.get("lamp_feedback_sequence") is not None else (),
        "author-no-death": tuple(temporal.get("complete_native_sequences", [])),
    }
    records = tuple(replace(r, status=statuses.get(r.id, "UNKNOWN"), witness_sequences=witnesses.get(r.id, ()))
                    if r.source == "AUTHOR" else r for r in records)
    return {"records": [asdict(r) for r in records], "replacements": replacements,
            "author_obligation_ids_preserved": [r.id for r in records if r.source == "AUTHOR"],
            "historical_consumer_sequences_preserved": sorted({s for r in records for s in r.witness_sequences}),
            "planner_PASS_scope": "modeled dependency with native consumer accepted by frozen B0 reconciliation; not an independent proof of every native precondition",
            "author_monitor_reads_this_file": False}
