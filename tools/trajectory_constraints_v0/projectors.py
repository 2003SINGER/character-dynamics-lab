"""Pure projectors over synthetic input records; these are contract fixtures only."""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Any, Mapping


@dataclass(frozen=True)
class Projected:
    value: Any
    known: bool
    reason: str
    provenance: tuple[str, ...] = ()


def task_progress(snapshot: Mapping[str, Any]) -> Projected:
    """No silent clamping: require target>0 and 0<=done<=target."""
    done, target = snapshot.get("effort_done"), snapshot.get("effort_target")
    if done is None or target is None: return Projected(None, False, "task fields missing")
    done, target = Fraction(str(done)), Fraction(str(target))
    if target <= 0 or done < 0 or done > target:
        return Projected(None, False, "invalid task progress invariant")
    return Projected(done / target, True, "defined task progress fraction", ("effort_done", "effort_target"))


def world_holding(snapshot: Mapping[str, Any], actor_id: str, item_id: str) -> Projected:
    holds = snapshot.get("world_holds")
    if holds is None: return Projected(None, False, "world holding relation missing")
    return Projected((actor_id, item_id) in holds, True, "world holding fact", ("world_holds",))


def actor_belief(snapshot: Mapping[str, Any], actor_id: str, proposition: str) -> Projected:
    beliefs = snapshot.get("actor_beliefs", {}).get(actor_id)
    if beliefs is None or proposition not in beliefs: return Projected(None, False, "actor belief missing")
    return Projected(beliefs[proposition], True, "actor-scoped belief", (f"actor_beliefs[{actor_id}]",))


def factive_observer_knows(snapshot: Mapping[str, Any], actor_id: str, proposition: str) -> Projected:
    """Known requires belief + W truth + legal delivery/initial-evidence provenance."""
    belief = actor_belief(snapshot, actor_id, proposition)
    if not belief.known: return Projected(None, False, "actor belief unavailable")
    if belief.value is not True: return Projected(False, True, "actor explicitly does not believe proposition")
    truth = snapshot.get("world_truth", {}).get(proposition)
    if truth is None: return Projected(None, False, "world truth missing")
    if truth is not True: return Projected(False, True, "belief conflicts with world truth")
    evidence_map=snapshot.get("legal_evidence")
    if evidence_map is None or actor_id not in evidence_map:
        return Projected(None,False,"evidence provenance unavailable")
    legal = set(evidence_map[actor_id])
    if proposition not in legal: return Projected(False, True, "provenance record has no legal delivered observation or initial evidence")
    return Projected(True, True, "factive knowledge with legal provenance", (f"belief:{actor_id}:{proposition}", f"world_truth:{proposition}", f"legal_evidence:{actor_id}"))
