"""Autonomous actors plus restricted world planning, one executor-owned clock."""
from copy import deepcopy
import hashlib
import json

from tools.e1_keyledger_v0.policy import choose_b
from tools.e1_keyledger_v0.executor import scheduled_actor
from .author import monitor, requirements
from .executor import Executor, _valid_app, intent, slot
from .model import actor_view, goal_choice, transition
from .planners import propose
from trajectory_constraints_v0.compiler import compile_constraint
from .author import registry


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode()).hexdigest()


def actor_decision(cp, model, planner="goap", max_expansions=1000):
    who = slot(cp)
    if who == "CONTINUE":
        return intent("idle", "WorldStep"), {"reason": "running action owns the serial token"}
    view = actor_view(cp, who)
    goal = goal_choice(view, model)
    meta = {"actor": who, "view_hash": digest(view), "goal": goal,
            "S": deepcopy(view["character"]["S"]), "model": model.version, "planner": planner}
    if goal["goal"] == "recover":
        transition(cp["characters"][who], "SUSPENDED", cp["clock"]["now"], "own overload appraisal")
        return intent("rest", who), meta
    if who == "B":
        selected = choose_b(view) if scheduled_actor(cp) == "B" else intent("idle", "B")
        if selected["operator"] != "idle":
            # Own request/negotiation is not an author goal and cannot be prescribed by A.
            meta["reason"] = "own public-contract goal arbitration"
            return selected, meta
        return intent("work", who), meta
    if goal["goal"] != "committed_task":
        if cp["characters"][who]["commitment"]["status"] != "COMPLETED":
            transition(cp["characters"][who], "SUSPENDED", cp["clock"]["now"], "own context response")
        return intent("work", who), meta
    planned = propose(view, planner, max_expansions=max_expansions)
    meta["proposal"] = planned
    selected = planned["selected_action"]
    if selected is not None and selected["operator"] != "idle":
        transition(cp["characters"][who], "ACTIVE", cp["clock"]["now"], "own viable plan")
        return selected, meta
    transition(cp["characters"][who], "SUSPENDED", cp["clock"]["now"], planned["solve_status"])
    return intent("work", who), meta


def _score(verdicts):
    hard = [v for v in verdicts if v["hard"]]
    return (sum(v["status"] == "SATISFIED" for v in hard),
            -sum(v["status"] == "VIOLATED" for v in hard))


class System:
    def __init__(self, cp, model, planner="goap", director=True, constraints=None,
                 max_expansions=1000, forecast_steps=16):
        self.executor = Executor(cp, model)
        self.model, self.planner, self.director = model, planner, director
        self.constraints = tuple(requirements() if constraints is None else constraints)
        if not self.constraints or len({c.constraint_id for c in self.constraints}) != len(self.constraints):
            raise ValueError("author constraints require unique nonempty identities")
        for constraint in self.constraints:
            compile_constraint(constraint, registry(model.version))
        self.max_expansions, self.forecast_steps = max_expansions, forecast_steps
        self.snapshots = [self.executor.checkpoint()]
        self.log, self.director_log = [], []

    def verdicts(self):
        return monitor(self.snapshots, self.constraints, self.model.version)

    def execute(self, action, metadata=None):
        before = self.executor.checkpoint()
        receipt = self.executor.start(action)
        if receipt["accepted"]:
            first = True
            if action["operator"] == "idle" and before["W"]["running_action"] is None:
                self.executor.advance_minute()
                self.snapshots.append(self.executor.checkpoint())
            else:
                while self.executor.checkpoint()["W"]["running_action"] is not None:
                    self.executor.advance_minute(receipt["action_id"] if first and action["operator"] != "idle" else None)
                    self.snapshots.append(self.executor.checkpoint())
                    first = False
            if receipt.get("receipt_id"):
                receipt = next(r for r in self.executor.checkpoint()["receipts"]
                               if r["receipt_id"] == receipt["receipt_id"])
            elif len(self.executor.checkpoint()["receipts"]) > len(before["receipts"]):
                receipt = self.executor.checkpoint()["receipts"][-1]
        self.log.append({"start_time": before["clock"]["now"],
                         "end_time": self.executor.checkpoint()["clock"]["now"],
                         "intent": deepcopy(action), "receipt": deepcopy(receipt),
                         "decision": deepcopy(metadata), "verdicts": self.verdicts()})
        return receipt

    def actor_step(self):
        # Arbitration writes only actor-owned commitment, not world or history.
        action, metadata = actor_decision(self.executor._c, self.model, self.planner, self.max_expansions)
        receipt = self.execute(action, metadata)
        if not receipt["accepted"]:
            self.execute(intent("idle", "WorldStep"), {"reason": "rejected intent; reconsider at next boundary"})
        return receipt

    def world_proposal(self):
        """Candidate rollouts are isolated guesses, never actual receipts/witnesses."""
        cp = self.executor.checkpoint()
        original = digest(cp)
        candidates = [None]
        opportunity = intent("publish_incentive", "DIRECTOR", bonus=2)
        if _valid_app(cp, opportunity):
            candidates.append(opportunity)
        evaluations = []
        for candidate in candidates:
            fork = System(cp, self.model, self.planner, False, self.constraints,
                          self.max_expansions, self.forecast_steps)
            fork.snapshots = deepcopy(self.snapshots)
            if candidate is not None:
                fork.execute(candidate, {"kind": "prediction_only"})
            steps = 0
            while fork.executor.checkpoint()["clock"]["now"] < 10 and steps < self.forecast_steps:
                fork.actor_step()
                steps += 1
            complete = fork.executor.checkpoint()["clock"]["now"] == 10
            results = fork.verdicts()
            unknown = any(v["hard"] and v["status"] not in ("SATISFIED", "VIOLATED") for v in results)
            usable = complete and not unknown
            evaluations.append({"candidate": candidate, "status": ("FORECAST" if usable else
                                "INDETERMINATE" if complete else "BUDGET"),
                                "prediction_only": True, "score": _score(results) if usable else None,
                                "verdicts": results, "rollout_steps": steps})
        if digest(self.executor.checkpoint()) != original:
            raise AssertionError("forecast mutated real checkpoint")
        available = [e for e in evaluations if e["status"] == "FORECAST"]
        # Retain NO_OP on equal score: fewer interventions, less cost.
        best = max(available, key=lambda e: e["score"]) if available else None
        action = best["candidate"] if best else None
        decision = {"time": cp["clock"]["now"], "committed_prefix_hash": digest(cp["events"]),
                    "candidate_evaluations": evaluations, "selected": action,
                    "status": ("BOUNDED_FORECAST_SELECTION" if available else
                               "UNKNOWN_NO_INTERVENTION" if any(e["status"] == "INDETERMINATE" for e in evaluations)
                               else "BUDGET_NO_INTERVENTION"),
                    "derived_subgoal": "make a voluntary loan attractive via public opportunity" if action else None,
                    "guarantee": False, "retractable": True,
                    "forecast_assumptions": ["fixed disclosed B utility policy",
                                             "same actor dynamics/planner",
                                             "no unannounced future player input"]}
        self.director_log.append(decision)
        return action, decision

    def run(self, player_at=None):
        player_done = False
        while self.executor.checkpoint()["clock"]["now"] < 10:
            now = self.executor.checkpoint()["clock"]["now"]
            if player_at is not None and not player_done and now >= player_at:
                self.execute(intent("destroy_key1", "PLAYER", item="key1"), {"source": "scheduled player input"})
                player_done = True
                continue
            if self.director:
                action, metadata = self.world_proposal()
                if action is not None:
                    self.execute(action, metadata)
                    continue
            self.actor_step()
        return {"development_only": True, "application": "npc-system-v0", "planner": self.planner,
                "model": self.model.version, "director": self.director,
                "author_verdicts": self.verdicts(), "checkpoint": self.executor.checkpoint(),
                "trace": self.log, "director_proposals": self.director_log,
                "snapshots": self.snapshots, "guarantee_or_player_evidence": False}
