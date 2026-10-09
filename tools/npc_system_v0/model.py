"""Actor-owned O -> inspectable X -> S -> commitment/goal arbitration.

Both response laws are synthetic application candidates, not psychology.
No actor function takes W, another character's private state, or author intent.
"""
from copy import deepcopy

from tools.e1_keyledger_v0.fixtures import initial_checkpoint as e1_fixture
from tools.e1_keyledger_v0.policy import actor_view as e1_view


def initial_checkpoint(policy="KEEP", stress=.35, fatigue=.15, resources=2):
    if type(resources) is not int or not 0 <= resources <= 100:
        raise ValueError("world resources must be bounded integer credits")
    if not 0 <= stress <= 1 or not 0 <= fatigue <= 1:
        raise ValueError("synthetic state must be in [0,1]")
    cp = e1_fixture("unknown", policy, 10)
    cp["application_version"] = "npc-system-v0"
    cp["application_slot"] = "B"
    cp["application_config"] = {"initial_director_resources": resources}
    cp["W"]["director_resources"] = resources
    cp["W"]["loan_bonus"] = 0
    cp["W"]["bonus_used"] = False
    cp["world_tasks"] = {"ledger": {"progress": 0, "deadline": 10}}
    cp["characters"] = {}
    for who in ("A", "B"):
        cp["O"][who]["loan_bonus"] = 0
        cp["characters"][who] = {
            "S": {"stress": stress, "fatigue": fatigue},
            "P": {"task_value": .6, "rest_threshold": .8},
            "commitment": {"goal": "acquire_ledger" if who == "A" else "recover_tool",
                           "status": "ACTIVE", "started_at": 2, "transitions": []},
            "processed_events": [], "X_history": [], "work_units": 0,
        }
    return cp


def actor_view(cp, who):
    view = e1_view(cp, who)
    view["clock"] = deepcopy(cp["clock"])
    view["deadline"] = cp["config_pins"]["deadline"]
    view["character"] = deepcopy(cp["characters"][who])
    # Published opportunity changes predicted net cost, not B's private P.
    view["contract"]["c"] -= view["observation"].get("loan_bonus", 0)
    view["contract"]["effective_contract_reason"] = "observed public loan incentive"
    return view


class ContextDriveV0:
    version = "synthetic-context-drive-v0"

    def drive(self, stress):
        return 4 * stress * (1 - stress) - .5

    def appraise(self, view, new_events):
        return {"version": self.version, "time": view["clock"]["now"],
                "evidence_ids": [e["event_id"] for e in new_events],
                "deadline_pressure": max(0, 1 - (view["deadline"] - view["clock"]["now"]) / 8),
                "obstruction": any(e["event_type"] in ("player_key_destroyed", "loan_reply_declined")
                                   for e in new_events),
                "recovery": any(e["event_type"] == "actor_rested" for e in new_events),
                "worked": any(e["event_type"] == "actor_worked" for e in new_events)}

    def update(self, state, appraisal, dt):
        return {"stress": round(min(1, max(0, state["stress"] + (.03 + .02 * appraisal["deadline_pressure"]) * dt
                    + .12 * appraisal["obstruction"] - .35 * appraisal["recovery"])), 6),
                "fatigue": round(min(1, max(0, state["fatigue"] + .06 * dt
                    - .4 * appraisal["recovery"])), 6)}


class MonotoneAvoidanceV0(ContextDriveV0):
    version = "synthetic-monotone-avoidance-v0"

    def drive(self, stress):
        return -stress


MODELS = {"context": ContextDriveV0, "monotone": MonotoneAvoidanceV0}


def transition(character, status, now, reason):
    commitment = character["commitment"]
    if commitment["status"] == "COMPLETED" and status != "COMPLETED":
        return
    if commitment["status"] != status:
        commitment["transitions"].append({"from": commitment["status"], "to": status,
                                           "time": now, "reason": reason})
        commitment["status"] = status
    # started_at is deliberately not rewritten on suspend/resume.


def consume_boundary(cp, model, dt=1):
    """Only this application adapter updates actor state after executor feedback."""
    for who in ("A", "B"):
        view = actor_view(cp, who)
        char = cp["characters"][who]
        new = [e for e in view["observation"].get("known_events", [])
               if e["event_id"] not in char["processed_events"]]
        x = model.appraise(view, new)
        char["X_history"].append(x)
        char["S"] = model.update(char["S"], x, dt)
        char["processed_events"].extend(e["event_id"] for e in new)
        if x["worked"]:
            char["work_units"] += 1
        completed = any(e["event_type"] == ("ledger_acquired" if who == "A" else "tool_returned")
                        for e in new)
        if completed:
            transition(char, "COMPLETED", cp["clock"]["now"], "own delivered settlement evidence")
    # Objective progress has a separate owner and is not commitment completion.
    cp["world_tasks"]["ledger"]["progress"] = int(cp["W"]["holders"]["ledger"] == "A")


def goal_choice(view, model):
    char, now = view["character"], view["clock"]["now"]
    s = char["S"]
    if s["fatigue"] >= char["P"]["rest_threshold"] or s["stress"] >= .85:
        return {"goal": "recover", "reason": "overload", "score": s["fatigue"] + s["stress"]}
    if char["commitment"]["status"] == "COMPLETED":
        return {"goal": "daily_work", "reason": "personal routine after observed completion", "score": 1}
    score = char["P"]["task_value"] + model.drive(s["stress"])
    return {"goal": "committed_task" if score >= .4 else "daily_work",
            "reason": "versioned context response", "score": round(score, 6), "time": now}
