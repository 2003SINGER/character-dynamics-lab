"""E1 scheduler adapter over the frozen E0 physical executor."""
from copy import deepcopy

from tools.e0_keyledger_v0.executor import Executor as E0Executor, _actor
from .fixtures import E1_PRODUCER_VERSION


def scheduled_actor(cp):
    w = cp["W"]
    if w["running_action"] is not None:
        return "CONTINUE"
    if cp["scheduler"].get("initial_b_slot_pending"):
        return "B"
    status = w["offer_session"]["status"]
    if status in ("OFFERED", "ACCEPTED"):
        return "B"
    return "A"


class Executor(E0Executor):
    """Use E0 mechanics and settlements; add one explicitly versioned request."""
    def __init__(self, checkpoint):
        super().__init__(checkpoint)

    def record_actor_planning(self, *, budget=None, assumption=None, binding=None):
        state = self._c.setdefault("actor_planning", {
            "budget": {"expansions": 0, "generated": 0, "elapsed_seconds": 0.0,
                       "max_expansions": 10000, "wall_seconds": 2.0},
            "assumptions": [], "late_binding_map": {}})
        if budget is not None:
            state["budget"] = deepcopy(budget)
        if assumption is not None and assumption not in state["assumptions"]:
            state["assumptions"].append(deepcopy(assumption))
        if binding is not None:
            state["late_binding_map"][binding["symbol"]] = binding["actual_id"]

    def start(self, action):
        action = deepcopy(action)
        cp = self._c
        actor = scheduled_actor(cp)
        op = action.get("operator")
        expected_actor = "WorldStep" if op == "idle" else "B" if op == "request_tool" else _actor(op)
        if actor == "CONTINUE" or (expected_actor not in (actor, "WorldStep")):
            return self._reject(action, "WRONG_CONTROL_SLOT")
        if op == "request_tool":
            args = action.get("args")
            valid = (action.get("actor") == "B" and args == {"target": "A", "item": "toolB"}
                     and not cp["W"]["request_used"] and not cp["O"]["B"]["request_sent"]
                     and "toolB_held_by_A" in cp["O"]["B"]["known_facts"]
                     and "toolB" in cp["O"]["B"]["known_entities"]
                     and cp["W"]["holders"]["toolB"] == "A"
                     and cp["W"]["beneficial_owners"]["toolB"] == "B"
                     and cp["W"]["locations"]["A"] == cp["W"]["locations"]["B"])
            if not valid:
                return self._reject(action, "PRECONDITION_FAILED")
            if cp["clock"]["now"] + 1 > cp["config_pins"]["deadline"]:
                return self._reject(action, "DEADLINE_EXCEEDED")
            receipt = self._receipt(action, True, "RUNNING")
            receipt["producer_version"] = E1_PRODUCER_VERSION
            receipt["duration"] = 1
            aid = receipt["action_id"]
            cp["W"]["running_action"] = {"id": aid, "action_id": aid, "operator": op,
                "intent": action, "start": cp["clock"]["now"], "duration": 1, "elapsed": 0,
                "progress": 0, "authority": "B", "receipt_id": receipt["receipt_id"]}
            cp["scheduler"]["slot"] = "CONTINUE"
            return deepcopy(receipt)
        if op == "idle":
            action["actor"] = "WorldStep"
        elif action.get("actor") != expected_actor:
            return self._reject(action, "INVALID_TYPED_INTENT")
        return super().start(action)

    def _reject(self, action, reason):
        receipt = self._receipt(action, False, "REJECTED_BEFORE_START", reason)
        receipt["end_time"] = self._c["clock"]["now"]
        self._c["outcome_history"].append({"receipt_id": receipt["receipt_id"],
            "time": self._c["clock"]["now"], "outcome": "REJECTED_BEFORE_START", "reason": reason})
        return deepcopy(receipt)

    def _finish(self, running):
        if running["operator"] != "request_tool":
            super()._finish(running)
            receipt = next((r for r in self._c["receipts"]
                            if r.get("receipt_id") == running["receipt_id"]), None)
            if receipt and receipt.get("status") == "SUCCESS":
                for event in receipt.get("event_payloads", []):
                    for who in ("A", "B"):
                        self._c["O"][who].setdefault("known_events", []).append({
                            "event_id": event["event_id"], "event_type": event["event_type"],
                            "time": event["time"], "sequence": event["sequence"],
                            "producer_version": event["producer_version"],
                            "typed_args": deepcopy(event["typed_args"])})
            return
        cp, w = self._c, self._c["W"]
        receipt = next(r for r in cp["receipts"] if r["receipt_id"] == running["receipt_id"])
        if not self._request_valid(running):
            receipt.update({"status": "INTERRUPTED", "outcome": "INTERRUPTED_NO_EFFECT",
                            "end_time": cp["clock"]["now"]})
            w["running_action"] = None
            cp["outcome_history"].append({"receipt_id": receipt["receipt_id"], "time": cp["clock"]["now"],
                                          "outcome": "INTERRUPTED_NO_EFFECT", "event_ids": []})
            return
        event = {"event_id": self._id("event"), "event_type": "tool_return_requested",
                 "time": cp["clock"]["now"], "sequence": cp["next_ids"]["sequence"],
                 "producer_version": E1_PRODUCER_VERSION,
                 "typed_args": {"event": "tool_return_requested", "actor": "B", "target": "A", "item": "toolB"}}
        cp["next_ids"]["sequence"] += 1
        cp["events"].append(event)
        w["request_used"] = True
        w["running_action"] = None
        cp["O"]["B"]["request_sent"] = True
        cp["O"]["B"]["request_sent_provenance"] = {"kind": "settlement_receipt",
            "event_id": event["event_id"], "time": event["time"], "actor": "B"}
        for who in ("A", "B"):
            if "tool_return_requested" not in cp["O"][who]["known_facts"]:
                cp["O"][who]["known_facts"].append("tool_return_requested")
            cp["O"][who].setdefault("known_events", []).append({
                "event_id": event["event_id"], "event_type": event["event_type"],
                "time": event["time"], "sequence": event["sequence"],
                "producer_version": event["producer_version"], "typed_args": deepcopy(event["typed_args"])})
        receipt.update({"status": "SUCCESS", "outcome": "COMPLETED", "end_time": cp["clock"]["now"],
                        "event_ids": [event["event_id"]], "event_payloads": [deepcopy(event)],
                        "delta_w": {"request_used": [False, True]},
                        "delta_o": {who: {"known_entities": {"added": [], "removed": []},
                                          "known_facts": {"added": ["tool_return_requested"], "removed": []}}
                                    for who in ("A", "B")}})
        cp["outcome_history"].append({"receipt_id": receipt["receipt_id"], "time": cp["clock"]["now"],
                                      "outcome": "SETTLED", "event_ids": [event["event_id"]]})
        cp["action_history"][-1]["status"] = "SUCCESS"

    def _request_valid(self, running):
        cp = self._c
        return (not cp["W"]["request_used"] and cp["W"]["holders"]["toolB"] == "A"
                and cp["W"]["beneficial_owners"]["toolB"] == "B"
                and cp["W"]["locations"]["A"] == cp["W"]["locations"]["B"])

    def _evaluate_monitor(self):
        # Explicit adapter seam: E0 revalidates its entire original ledger;
        # E1 request evidence is validated separately by monitor_bridge.
        from .monitor_bridge import validate_e1_evidence
        validate_e1_evidence(self._c)
        events, receipts = self._c["events"], self._c["receipts"]
        try:
            self._c["events"] = [e for e in events if e.get("producer_version") != E1_PRODUCER_VERSION]
            self._c["receipts"] = [r for r in receipts if r.get("producer_version") != E1_PRODUCER_VERSION]
            super()._evaluate_monitor()
        finally:
            self._c["events"], self._c["receipts"] = events, receipts

    def advance_minute(self, started_action_id=None):
        super().advance_minute(started_action_id)
        if self._c["scheduler"].get("initial_b_slot_pending"):
            self._c["scheduler"]["initial_b_slot_pending"] = False
        self._c["scheduler"]["slot"] = scheduled_actor(self._c)
        return self.checkpoint()
