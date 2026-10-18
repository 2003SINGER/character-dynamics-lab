"""Actor-local HTN proposal adapter for the frozen Veloren Recruit v1 view.

This module proposes one native ``RecruitMember`` request. It never executes a
task, mutates game state, or treats a sent message as a completed hire.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from contextlib import redirect_stdout
from dataclasses import dataclass
from io import StringIO
import math
import os
import threading
import time


_LOCK = threading.RLock()
GOAL_HIRED_MEMBERS = 4
MAX_CANDIDATE_DISTANCE = 24.0
NATIVE_NON_HIRE_TERMINALS = {
    "expired_before_native_action", "expired_after_native_action_before_message",
    "expired_after_message", "leader_invalidated", "target_invalidated",
}


@dataclass(frozen=True)
class Candidate:
    uid: int
    distance: float | None
    mode: str


def _finite_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _view_error(view: object) -> str | None:
    if not isinstance(view, Mapping):
        return "ActorView must be a JSON object"
    if view.get("event") != "native_recruit_actor_view" or view.get("version") != 1:
        return "unsupported ActorView event or version"
    if not _finite_number(view.get("time")) or view["time"] < 0:
        return "ActorView time must be finite and non-negative"
    if not isinstance(view.get("npc_uid"), int) or isinstance(view.get("npc_uid"), bool):
        return "leader npc_uid must be an integer"
    if view.get("mode") not in ("loaded", "simulated"):
        return "leader mode must be loaded or simulated"
    role = view.get("role")
    if (not isinstance(role, Mapping) or role.get("kind") != "civilised"
            or role.get("profession") != "pirate" or role.get("is_leader") is not True):
        return "view is not for a civilised Pirate leader"
    job = view.get("job")
    if job is not None and not isinstance(job, Mapping):
        return "leader job must be null or a job object"
    for key in ("home_site_id", "current_site_id"):
        value = view.get(key)
        if not isinstance(value, str) or not value:
            return f"{key} must be a non-empty diagnostic string"
    if not isinstance(view.get("leader_at_home"), bool):
        return "leader_at_home must be a boolean"
    if view["leader_at_home"] is not True or view["home_site_id"] != view["current_site_id"]:
        return "leader must currently be at its home site for this recruitment choice"
    if not isinstance(view.get("native_recruit_population_guard"), bool):
        return "native_recruit_population_guard must be a boolean"
    if not isinstance(view.get("native_recruit_raid_site_available"), bool):
        return "native_recruit_raid_site_available must be a boolean"
    if not isinstance(view.get("eligible_recruits"), Sequence) or isinstance(view.get("eligible_recruits"), (str, bytes)):
        return "eligible_recruits must be an array"
    hired = view.get("hired_members")
    if not isinstance(hired, Sequence) or isinstance(hired, (str, bytes)):
        return "hired_members must be an array"
    if view.get("hired_member_count") != len(hired):
        return "hired_member_count must equal the locally observed hired_members array length"
    return None


def _parse_candidates(rows: Sequence[object], leader_uid: int) -> tuple[list[Candidate], str | None]:
    by_uid: dict[int, Candidate] = {}
    for row in rows:
        if not isinstance(row, Mapping):
            return [], "candidate row must be an object"
        uid = row.get("npc_uid")
        mode = row.get("mode")
        distance = row.get("distance_3d")
        if not isinstance(uid, int) or isinstance(uid, bool) or uid < 0 or uid == leader_uid:
            return [], "candidate npc_uid is invalid or equals the leader"
        if mode not in ("loaded", "simulated"):
            return [], "candidate mode must be loaded or simulated"
        if distance is not None:
            if not _finite_number(distance) or distance < 0 or distance > MAX_CANDIDATE_DISTANCE:
                return [], "candidate distance_3d is outside the native 24m eligibility boundary"
            distance = float(distance)
        candidate = Candidate(uid=uid, distance=distance, mode=mode)
        if uid in by_uid and by_uid[uid] != candidate:
            return [], "duplicate candidate uid has conflicting observations"
        by_uid[uid] = candidate
    return sorted(by_uid.values(), key=lambda row: (
        row.distance if row.distance is not None else math.inf, row.uid
    )), None


def _parse_hired(rows: Sequence[object], leader_uid: int) -> tuple[list[int], str | None]:
    seen: set[int] = set()
    for row in rows:
        if not isinstance(row, Mapping):
            return [], "hired member row must be an object"
        uid = row.get("npc_uid")
        mode = row.get("mode")
        distance = row.get("distance_3d")
        if not isinstance(uid, int) or isinstance(uid, bool) or uid < 0 or uid in (leader_uid,):
            return [], "hired member npc_uid is invalid"
        if mode not in ("loaded", "simulated"):
            return [], "hired member mode must be loaded or simulated"
        if (not _finite_number(distance) or distance < 0
                or distance > MAX_CANDIDATE_DISTANCE):
            return [], "hired member distance_3d is outside the local observation boundary"
        if uid in seen:
            return [], "hired_members contains a duplicate uid"
        seen.add(uid)
    return sorted(seen), None


def plan_recruitment(actor_view: Mapping[str, object], *,
                     excluded_target_uids: Sequence[int] = (),
                     require_loaded_candidates: bool = False,
                     max_visits: int = 128,
                     wall_seconds: float = 0.25) -> dict[str, object]:
    """Return one prediction-only RecruitMember task from one native view.

    Goal progress counts only locally observed ``Job::Hired(leader)`` members
    in this ActorView. Historical observations are intentionally not treated as
    proof that a member remains nearby or employed.
    """
    error = _view_error(actor_view)
    if error:
        return {"status": "INVALID_VIEW", "reason": error, "task": None, "plan": []}
    leader_uid = actor_view["npc_uid"]
    if actor_view["job"] is not None:
        return {"status": "BLOCKED", "reason": "leader currently has a native Job",
                "task": None, "plan": []}
    candidates, error = _parse_candidates(actor_view["eligible_recruits"], leader_uid)
    if error:
        return {"status": "INVALID_VIEW", "reason": error, "task": None, "plan": []}
    hired_uids, error = _parse_hired(actor_view["hired_members"], leader_uid)
    if error:
        return {"status": "INVALID_VIEW", "reason": error, "task": None, "plan": []}
    hired_count = actor_view["hired_member_count"]
    if not isinstance(hired_count, int) or isinstance(hired_count, bool) or hired_count < 0:
        return {"status": "INVALID_VIEW", "reason": "hired_member_count must be a non-negative integer",
                "task": None, "plan": []}
    if hired_count >= GOAL_HIRED_MEMBERS:
        return {"status": "GOAL_SATISFIED_LOCALLY", "reason": "four native hired members are currently visible",
                "task": None, "plan": [], "observed_hired_member_uids": hired_uids,
                "prediction_only": True}
    if actor_view["native_recruit_population_guard"] is not True:
        return {"status": "NATIVE_GUARD_FALSE", "reason": "the existing native population guard is false",
                "task": None, "plan": [], "observed_hired_member_uids": hired_uids,
                "prediction_only": True}
    if actor_view["native_recruit_raid_site_available"] is not True:
        return {"status": "NATIVE_GUARD_FALSE", "reason": "no currently legal native raid site is available",
                "task": None, "plan": [], "observed_hired_member_uids": hired_uids,
                "prediction_only": True}
    excluded = set(excluded_target_uids)
    choices = [candidate for candidate in candidates
               if candidate.uid not in excluded
               and (not require_loaded_candidates or candidate.mode == "loaded")]
    planner_excluded = excluded | {
        candidate.uid for candidate in candidates
        if require_loaded_candidates and candidate.mode != "loaded"
    }
    if len(choices) < 2:
        return {"status": "INSUFFICIENT_CHOICES", "reason": "fewer than two currently eligible untried candidates",
                "task": None, "plan": [], "eligible_candidate_uids": [row.uid for row in choices],
                "observed_hired_member_uids": hired_uids, "prediction_only": True}
    if max_visits <= 0 or wall_seconds <= 0:
        return {"status": "BUDGET", "reason": "planner budget is not positive", "task": None, "plan": []}

    os.environ.setdefault("GTPYHOP_QUIET", "true")
    try:
        import gtpyhop as g
        import gtpyhop.main as main
    except ImportError as exc:
        raise RuntimeError("Recruitment HTN requires the local pinned gtpyhop-core==2.0.2") from exc

    started = time.monotonic()
    visits = 0
    exhausted = False

    def budget() -> bool:
        nonlocal visits, exhausted
        visits += 1
        if visits > max_visits or time.monotonic() - started >= wall_seconds:
            exhausted = True
            return False
        return True

    def predict_recruitment_progress(state, candidate_uid):
        if (not budget() or candidate_uid not in state.eligible
                or candidate_uid in state.excluded or candidate_uid in state.hired_uids
                or state.predicted_hired_count >= state.target_size):
            return False
        state.selected_uid = candidate_uid
        state.predicted_hired_count += 1
        state.eligible = tuple(uid for uid in state.eligible if uid != candidate_uid)
        return state

    def already_enough(state):
        return [] if budget() and state.hired_count >= state.target_size else None

    def recruit_one(state):
        if not budget() or state.hired_count >= state.target_size or not state.population_guard:
            return None
        if sum(uid not in state.excluded for uid in state.eligible) < 2:
            return None
        return [("choose_recruit_candidate",)]

    def candidate_method(candidate_uid):
        def method(state):
            if not budget() or candidate_uid not in state.eligible:
                return None
            return [("predict_recruitment_progress", candidate_uid)]
        return method

    state = g.State("veloren-pirate-recruitment-local")
    state.leader_uid = leader_uid
    state.target_size = GOAL_HIRED_MEMBERS
    state.hired_count = hired_count
    state.population_guard = actor_view["native_recruit_population_guard"]
    state.eligible = tuple(row.uid for row in candidates)
    state.hired_uids = frozenset(hired_uids)
    state.excluded = frozenset(planner_excluded)
    state.selected_uid = None
    state.predicted_hired_count = hired_count
    # Keep excluded candidates in the method frontier. Their primitive
    # precondition fails in the simulated state, letting GTPyhop backtrack to
    # the next observed candidate rather than baking selection into a script.
    methods = [candidate_method(row.uid) for row in candidates]

    with _LOCK, redirect_stdout(StringIO()):
        previous = main.current_domain
        try:
            domain = g.Domain("veloren-native-recruitment-v1")
            g.declare_actions(predict_recruitment_progress)
            g.declare_task_methods("make_one_native_recruitment_progress", already_enough, recruit_one)
            g.declare_task_methods("choose_recruit_candidate", *methods)
            with g.PlannerSession(domain=domain, strategy="iterative_dfs_backtracking", verbose=0,
                                  structured_logging=False) as session:
                result = session.find_plan(
                    state, [("make_one_native_recruitment_progress",)],
                    timeout_ms=max(1, int(wall_seconds * 1000))
                )
        finally:
            main.current_domain = previous

    elapsed = time.monotonic() - started
    if exhausted or elapsed >= wall_seconds:
        return {"status": "BUDGET", "reason": "HTN method/action cap or wall watchdog",
                "task": None, "plan": [], "method_action_visits": visits,
                "elapsed_seconds": elapsed, "prediction_only": True}
    if not result.success or not result.plan:
        return {"status": "NO_PLAN", "reason": "native party task has no applicable HTN decomposition",
                "task": None, "plan": [], "method_action_visits": visits,
                "elapsed_seconds": elapsed, "prediction_only": True}

    if len(result.plan) != 1 or result.plan[0][0] != "predict_recruitment_progress":
        return {"status": "NO_PLAN", "reason": "HTN did not produce the bounded next-task prediction",
                "task": None, "plan": [], "method_action_visits": visits,
                "elapsed_seconds": elapsed, "prediction_only": True}
    target_uid = int(result.plan[0][1])
    task = {"kind": "RecruitMember", "leader_uid": leader_uid,
            "target_uid": target_uid, "observed_time": float(actor_view["time"]),
            "goal": "nativeparty", "goal_hired_member_count": GOAL_HIRED_MEMBERS,
            "observed_hired_member_count": hired_count,
            "predicted_hired_member_count_after_one_native_task": hired_count + 1,
            "residual_goal_required_additional_hires": max(0, GOAL_HIRED_MEMBERS - hired_count - 1),
            "predicted_effect_if_native_hire_is_observed": {"hired_member_count": hired_count + 1,
                                                            "selected_uid_removed_from_unhired_candidates": target_uid},
            "native_receiver_policy": "unmodeled; native server validation and execution remain authoritative"}
    return {"status": "SOLVED_NEXT_SUBTASK", "reason": "one-step actor-local GTPyhop HTN refinement",
            "task": task, "plan": [task], "method_action_visits": visits,
            "elapsed_seconds": elapsed, "implementation": "gtpyhop-core-2.0.2",
            "prediction_only": True, "native_execution": "not executed",
            "overall_goal_satisfied": False, "overall_goal": "nativeparty: four currently visible native Hired members",
            "residual_goal": {"hired_member_count_at_least": GOAL_HIRED_MEMBERS,
                              "additional_hires_after_predicted_task": max(0, GOAL_HIRED_MEMBERS - hired_count - 1)}}


class RecruitmentController:
    """Small event-to-request loop; OFF mode records views without planning."""

    def __init__(self, mode: str, run_id: str, leader_uid: int = 476,
                 ttl_seconds: float = 60.0, planner=plan_recruitment):
        if mode not in ("off", "on"):
            raise ValueError("mode must be 'off' or 'on'")
        if not run_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in run_id):
            raise ValueError("run_id must contain only letters, digits, '-' or '_'")
        if not _finite_number(ttl_seconds) or not 0 < ttl_seconds <= 120:
            raise ValueError("ttl_seconds must be finite and in (0, 120]")
        self.mode = mode
        self.run_id = run_id
        self.leader_uid = leader_uid
        self.ttl_seconds = float(ttl_seconds)
        self.planner = planner
        self.request_count = 0
        self.pending: dict[str, object] | None = None
        self.attempted_target_uids: set[int] = set()
        self.last_observed_hired: dict[int, float] = {}
        self.actual_job_observations: dict[int, float] = {}
        self.request_confirmed_hires: set[tuple[str, int]] = set()
        self.pending_terminal_outcome: str | None = None
        self.pending_started = False
        self.pending_message_sent = False
        self.returned_to_native = False

    def feed(self, row: Mapping[str, object]) -> list[dict[str, object]]:
        """Process one native recruitment event; return records to log/submit."""
        if not isinstance(row, Mapping):
            return [{"event": "controller_input_ignored", "reason": "not a JSON object"}]
        event = row.get("event")
        output: list[dict[str, object]] = []
        if event == "native_recruit_unattributed_hire_observed" and row.get("leader_uid") == self.leader_uid:
            target_uid, observed_time = row.get("target_uid"), row.get("time")
            if isinstance(target_uid, int) and not isinstance(target_uid, bool) and _finite_number(observed_time):
                self.actual_job_observations[target_uid] = float(observed_time)
                output.append({"event": "actual_hired_job_observation", "target_uid": target_uid,
                               "observed_time": float(observed_time), "source_event": event,
                               "attribution": "native_unattributed"})
            return output
        if event == "native_recruit_job_observed" and row.get("leader_uid") == self.leader_uid:
            target_uid, observed_time = row.get("target_uid"), row.get("time")
            if isinstance(target_uid, int) and not isinstance(target_uid, bool) and _finite_number(observed_time):
                self.actual_job_observations[target_uid] = float(observed_time)
                matches_pending = bool(
                    self.pending
                    and row.get("request_id") == self.pending.get("request_id")
                    and target_uid == self.pending.get("target_uid")
                    and self.pending_message_sent
                )
                if matches_pending:
                    self.request_confirmed_hires.add((str(row["request_id"]), target_uid))
                output.append({"event": "actual_hired_job_observation", "target_uid": target_uid,
                               "observed_time": float(observed_time), "source_event": event,
                               "attribution": "matched_recruit_request" if matches_pending else "native_unattributed"})
                if matches_pending:
                    output.append({"event": "inflight_released_by_actual_job_observation",
                                   "request_id": self.pending["request_id"], "target_uid": target_uid,
                                   "awaiting_native_terminal": self.pending_terminal_outcome is None})
                    if self.pending_terminal_outcome == "hired_observed":
                        self.pending = None
                        self.pending_terminal_outcome = None
            return output
        if event == "native_recruit_message_sent":
            matches_pending = bool(
                self.pending and row.get("request_id") == self.pending.get("request_id")
                and row.get("leader_uid") == self.pending.get("leader_uid")
                and row.get("target_uid") == self.pending.get("target_uid")
            )
            if matches_pending and self.pending_started:
                self.pending_message_sent = True
                output.append({"event": "message_sent_not_completion", "request_id": row.get("request_id"),
                               "target_uid": row.get("target_uid"), "source_event": event})
            elif matches_pending:
                output.append({"event": "controller_protocol_violation", "reason": "message_sent_before_started",
                               "request_id": row.get("request_id")})
        elif event in ("native_recruit_request_accepted", "native_recruit_started"):
            matches_pending = bool(
                self.pending and row.get("request_id") == self.pending.get("request_id")
                and row.get("leader_uid") == self.pending.get("leader_uid")
                and row.get("target_uid") == self.pending.get("target_uid")
            )
            if matches_pending:
                if event == "native_recruit_started":
                    self.pending_started = True
                output.append({"event": "native_recruit_progress_observed", "progress": event,
                               "request_id": row.get("request_id"), "target_uid": row.get("target_uid"),
                               "completion": False})
        if event in ("native_recruit_request_rejected", "native_recruit_terminal"):
            request_id = row.get("request_id")
            if event == "native_recruit_request_rejected":
                matches_pending = bool(
                    self.pending and request_id == self.pending.get("request_id")
                    and row.get("leader_uid", self.leader_uid) == self.pending.get("leader_uid")
                    and row.get("target_uid", self.pending.get("target_uid")) == self.pending.get("target_uid")
                )
            else:
                matches_pending = bool(
                    self.pending and request_id == self.pending.get("request_id")
                    and row.get("leader_uid") == self.pending.get("leader_uid")
                    and row.get("target_uid") == self.pending.get("target_uid")
                )
            if matches_pending:
                if event == "native_recruit_terminal":
                    output.append({"event": "native_request_terminal", "request_id": request_id,
                                   "outcome": row.get("outcome")})
                    self.pending_terminal_outcome = row.get("outcome")
                    target_uid = self.pending.get("target_uid")
                    if row.get("outcome") not in NATIVE_NON_HIRE_TERMINALS | {"hired_observed"}:
                        output.append({"event": "controller_protocol_violation",
                                       "reason": "unknown_native_terminal_outcome",
                                       "request_id": request_id})
                    elif row.get("outcome") != "hired_observed":
                        self.pending = None
                        self.pending_terminal_outcome = None
                        self.pending_started = False
                        self.pending_message_sent = False
                    elif not self.pending_message_sent:
                        output.append({"event": "controller_protocol_violation",
                                       "reason": "hired_terminal_without_matching_message_sent",
                                       "request_id": request_id})
                    elif (str(request_id), int(target_uid)) in self.request_confirmed_hires:
                        self.pending = None
                        self.pending_terminal_outcome = None
                        self.pending_started = False
                        self.pending_message_sent = False
                else:
                    output.append({"event": "native_request_rejected", "request_id": request_id,
                                   "reason": row.get("reason")})
                    self.pending = None
                    self.pending_terminal_outcome = None
                    self.pending_started = False
                    self.pending_message_sent = False
            return output
        if event != "native_recruit_actor_view":
            return output

        if row.get("npc_uid") != self.leader_uid:
            return [{"event": "actor_view_ignored", "reason": "leader uid does not match configured actor",
                     "npc_uid": row.get("npc_uid")}]
        member_rows = row.get("hired_members", [])
        if isinstance(member_rows, Sequence) and not isinstance(member_rows, (str, bytes)):
            for member in member_rows:
                if isinstance(member, Mapping) and isinstance(member.get("npc_uid"), int) and _finite_number(row.get("time")):
                    self.last_observed_hired[member["npc_uid"]] = float(row["time"])
        output.append({"event": "native_actor_view_observed", "mode": self.mode,
                       "leader_uid": self.leader_uid, "observed_time": row.get("time"),
                       "currently_visible_hired_member_count": row.get("hired_member_count"),
                       "last_observed_hired": dict(self.last_observed_hired)})
        if self.mode == "off":
            return output
        if self.returned_to_native:
            return output
        if row.get("hired_member_count", 0) >= GOAL_HIRED_MEMBERS:
            self.returned_to_native = True
            output.append({"event": "planner_control_returned_to_native", "reason": "four hired members currently visible",
                           "observed_time": row.get("time"), "no_end_hire_sent": True})
            return output
        if self.pending is not None:
            return output
        if self.request_count >= 8:
            output.append({"event": "request_budget_exhausted", "maximum_requests": 8})
            return output
        result = self.planner(row, excluded_target_uids=tuple(self.attempted_target_uids),
                              require_loaded_candidates=True)
        output.append({"event": "planner_proposal", "status": result.get("status"),
                       "reason": result.get("reason"), "prediction_only": result.get("prediction_only", True),
                       "proposal": result.get("task")})
        if result.get("status") != "SOLVED_NEXT_SUBTASK" or not isinstance(result.get("task"), Mapping):
            return output

        task = result["task"]
        target_uid = int(task["target_uid"])
        self.attempted_target_uids.add(target_uid)
        self.request_count += 1
        request = {"version": 1, "kind": "RecruitMember",
                   "request_id": f"{self.run_id}-recruit-{self.request_count:02d}",
                   "source": "character-dynamics-htn-v1", "leader_uid": self.leader_uid,
                   "target_uid": target_uid, "observed_time": float(row["time"]),
                   "ttl_seconds": self.ttl_seconds}
        self.pending = request
        self.pending_terminal_outcome = None
        self.pending_started = False
        self.pending_message_sent = False
        output.append({"event": "native_request_proposed", "request": request,
                       "prediction_only_until_appended": True})
        return output

