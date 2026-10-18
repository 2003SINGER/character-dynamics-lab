"""One-step GTPyhop HTN refinement over the current actor-local recruit view."""
from __future__ import annotations

import os
import threading
from contextlib import redirect_stdout
from io import StringIO
from typing import Any

from .contracts import ContractError, uid, validate_actor_view

_LOCK = threading.RLock()


def choose_recruit_target(actor_view: dict[str, Any], *, target_uid: int | None = None,
                          candidate_order: list[int] | None = None) -> dict[str, Any]:
    """Return a single legal next RecruitMember request proposal.

    The returned choice is a proposal, never a predicted settlement. One
    candidate is sufficient; native eligibility remains authoritative.
    """
    try:
        view = validate_actor_view(actor_view)
    except ContractError as exc:
        return {"status": "INVALID_VIEW", "reason": str(exc), "target_uid": None}
    leader = view["npc_uid"]
    if view["job"] is not None:
        return {"status": "BLOCKED", "reason": "leader has a native Job", "target_uid": None}
    if view["leader_at_home"] is not True or view["home_site_id"] != view["current_site_id"]:
        return {"status": "BLOCKED", "reason": "leader is not currently at its home site", "target_uid": None}
    if not view["native_recruit_population_guard"]:
        return {"status": "BLOCKED", "reason": "native population guard is false (requires more than three eligible home pirates)", "target_uid": None}
    if not view["native_recruit_raid_site_available"]:
        return {"status": "BLOCKED", "reason": "native raid-site availability guard is false", "target_uid": None}

    eligible = {row["npc_uid"]: row for row in view["eligible_recruits"]}
    if target_uid is not None:
        uid(target_uid, "target_uid")
        if target_uid not in eligible:
            return {"status": "BLOCKED", "reason": "requested target is not in the current actor-local eligible set", "target_uid": None,
                    "eligible_candidate_uids": sorted(eligible)}
        ordered_uids = [target_uid]
    else:
        rank = {uid(value, "candidate_order") : i for i, value in enumerate(candidate_order or [])}
        ordered_uids = sorted(eligible, key=lambda candidate: (
            rank.get(candidate, len(rank)),
            eligible[candidate]["distance_3d"], candidate))
    if not ordered_uids:
        return {"status": "BLOCKED", "reason": "no currently eligible actor-local recruit candidates", "target_uid": None}

    # Keep candidate sequencing in the existing mature HTN engine. The domain
    # here only refines the symbolic next-goal to one eligible native action.
    os.environ.setdefault("GTPYHOP_QUIET", "true")
    try:
        import gtpyhop as g
        import gtpyhop.main as main
    except ImportError as exc:
        raise RuntimeError("online HTN requires local gtpyhop-core==2.0.2") from exc

    class State:
        pass

    state = g.State("character-dynamics-online-recruitment")
    state.eligible = tuple(ordered_uids)
    state.selected_uid = None

    def propose_native_request(current, candidate):
        if candidate not in current.eligible:
            return False
        current.selected_uid = candidate
        return current

    def refine_recruit_goal(current):
        if not current.eligible:
            return None
        return [("choose_existing_eligible_candidate",)]

    def candidate_method(candidate):
        def method(current):
            if candidate not in current.eligible:
                return None
            return [("propose_native_request", candidate)]
        return method

    with _LOCK, redirect_stdout(StringIO()):
        previous = main.current_domain
        try:
            domain = g.Domain("character-dynamics-online-v0")
            g.declare_actions(propose_native_request)
            g.declare_task_methods("pursue_party_goal", refine_recruit_goal)
            g.declare_task_methods("choose_existing_eligible_candidate",
                                   *(candidate_method(candidate) for candidate in ordered_uids))
            with g.PlannerSession(domain=domain, strategy="iterative_dfs_backtracking",
                                  verbose=0, structured_logging=False) as session:
                result = session.find_plan(state, [("pursue_party_goal",)], timeout_ms=250)
        finally:
            main.current_domain = previous
    if not result.success or not result.plan:
        return {"status": "BLOCKED", "reason": "HTN found no applicable candidate refinement", "target_uid": None}
    if len(result.plan) != 1 or result.plan[0][0] != "propose_native_request":
        return {"status": "BLOCKED", "reason": "HTN returned an unsupported refinement", "target_uid": None}
    selected = int(result.plan[0][1])
    return {"status": "PROPOSED", "reason": "one-step GTPyhop refinement from current ActorView",
            "target_uid": selected, "eligible_candidate_uids": ordered_uids,
            "planner": "gtpyhop-core-2.0.2", "native_settlement": "not asserted",
            "domain": "character-dynamics-online-v0",
            "top_level_task": "pursue_party_goal",
            "refinement": {"method_task": "choose_existing_eligible_candidate",
                           "primitive_action": "propose_native_request",
                           "target_uid": selected}}
