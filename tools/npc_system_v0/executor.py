"""Versioned application actions; reuse E0/E1 clock/start/settlement path.

Director/player actions use the same serial token and consume one minute.
No history rollback, direct NPC control, or private-state mutation operator.
"""
from copy import deepcopy

from tools.e0_keyledger_v0.fixtures import PRODUCER_VERSION as E0
from tools.e0_keyledger_v0.executor import Executor as E0Executor
from tools.e1_keyledger_v0.fixtures import E1_PRODUCER_VERSION as E1
from tools.e1_keyledger_v0.executor import Executor as E1Executor, scheduled_actor
from tools.e1_keyledger_v0.monitor_bridge import validate_e1_evidence
from tools.e1_keyledger_v0.policy import actor_view as e1_actor_view
from .model import consume_boundary

VERSION = "npc-system-executor-v0"
OPS = {"publish_incentive", "destroy_key1", "rest", "work"}
EVENTS = {"publish_incentive": "incentive_published", "destroy_key1": "player_key_destroyed",
          "rest": "actor_rested", "work": "actor_worked"}


def intent(op, actor, **args):
    return {"operator": op, "actor": actor, "args": args}


def slot(cp):
    return cp.get("application_slot", select_next_slot(cp))


def select_next_slot(cp):
    normal = scheduled_actor(cp)
    if (normal == "A" and cp["characters"]["A"]["commitment"]["status"] in ("COMPLETED", "SUSPENDED")):
        return "A" if cp["clock"]["now"] % 2 == 0 else "B"
    return normal


def base_view(cp):
    copy = deepcopy(cp)
    copy["events"] = [e for e in cp["events"] if e.get("producer_version") != VERSION]
    copy["receipts"] = [r for r in cp["receipts"] if r.get("producer_version") != VERSION]
    return copy


def _valid_app(cp, action, finishing=False):
    op, who, args = action.get("operator"), action.get("actor"), action.get("args")
    if op not in OPS or not isinstance(args, dict):
        return False
    w = cp["W"]
    if op == "publish_incentive":
        return (who == "DIRECTOR" and args == {"bonus": 2} and w["director_resources"] >= 2
                and not w["bonus_used"] and w["offer_session"]["status"] == "NONE"
                and w["intact"]["key1"] and not w["destroyed"]["key1"])
    if op == "destroy_key1":
        return (who == "PLAYER" and args == {"item": "key1"} and w["intact"]["key1"]
                and not w["destroyed"]["key1"] and not w["archive_open"])
    return (who in ("A", "B") and args == {} and (finishing or who == slot(cp)))


def validate_evidence(cp):
    """Validate extension receipts globally, then the unchanged E1/E0 evidence."""
    events, receipts = cp["events"], cp["receipts"]
    if len({r["receipt_id"] for r in receipts}) != len(receipts):
        raise ValueError("duplicate receipt identity")
    if len({e["event_id"] for e in events}) != len(events):
        raise ValueError("duplicate event identity")
    prior = (-1, -1)
    claims = {}
    for r in receipts:
        if r.get("producer_version") not in (E0, E1, VERSION):
            raise ValueError("unregistered receipt producer")
        if r.get("producer_version") != VERSION:
            continue
        payloads, ids = r.get("event_payloads", []), r.get("event_ids", [])
        if ids != [e.get("event_id") for e in payloads]:
            raise ValueError("receipt payload identities disagree")
        if r["accepted"] and r["status"] == "SUCCESS":
            op = r["intent"]["operator"]
            who, args = r["intent"].get("actor"), r["intent"].get("args")
            if ((op == "publish_incentive" and (who != "DIRECTOR" or args != {"bonus": 2}))
                    or (op == "destroy_key1" and (who != "PLAYER" or args != {"item": "key1"}))
                    or (op in ("rest", "work") and (who not in ("A", "B") or args != {}))):
                raise ValueError("settlement claims unauthorized typed action")
            if op not in OPS or len(payloads) != 1 or r["end_time"] != r["start_time"] + 1:
                raise ValueError("invalid application settlement")
            e = payloads[0]
            expected = {"event": EVENTS[op], "actor": r["intent"]["actor"], **r["intent"]["args"]}
            if (e["event_type"] != EVENTS[op] or e["typed_args"] != expected
                    or e["time"] != r["end_time"] or e["producer_version"] != VERSION):
                raise ValueError("application event does not match its action settlement")
            delta = r.get("delta_w", {})
            if op == "publish_incentive" and (delta.get("loan_bonus") != [0, 2]
                    or delta.get("bonus_used") != [False, True]
                    or not isinstance(delta.get("director_resources"), list)
                    or delta["director_resources"][0] - delta["director_resources"][1] != 2):
                raise ValueError("incentive lacks authorized resource debit")
            if op == "publish_incentive" and set(delta) != {"loan_bonus", "bonus_used", "director_resources"}:
                raise ValueError("incentive claims unrelated world effects")
            if op == "destroy_key1" and (delta.get("intact.key1") != [True, False]
                    or delta.get("destroyed.key1") != [False, True]):
                raise ValueError("destruction lacks irreversible world delta")
            if op == "destroy_key1" and (set(delta) != {"intact.key1", "destroyed.key1", "holders.key1"}
                                        or delta["holders.key1"][1] is not None):
                raise ValueError("destruction claims unrelated world effects")
            if op in ("rest", "work") and delta:
                raise ValueError("routine may not change world ownership")
        elif payloads:
            raise ValueError("unsuccessful action claims evidence")
        for e in payloads:
            if e["event_id"] in claims:
                raise ValueError("duplicate event receipt claim")
            claims[e["event_id"]] = e
    app_events = {}
    for e in events:
        key = (e["time"], e["sequence"])
        if key <= prior or e["time"] > cp["clock"]["now"] or e["sequence"] >= cp["next_ids"]["sequence"]:
            raise ValueError("invalid append-only event ordering")
        prior = key
        if e.get("producer_version") not in (E0, E1, VERSION):
            raise ValueError("unregistered event producer")
        if e.get("producer_version") == VERSION:
            app_events[e["event_id"]] = e
        if not any(s["sealed_through"] >= e["time"] and s["sequence_frontier"] >= e["sequence"]
                   for s in cp["seals"]):
            raise ValueError("event lacks coverage seal")
    if claims != app_events:
        raise ValueError("application ledger and receipts disagree")
    for s in cp["seals"]:
        if any(e["time"] <= s["sealed_through"] and e["sequence"] > s["sequence_frontier"] for e in events):
            raise ValueError("new event inserted into already sealed history")
    validate_e1_evidence(base_view(cp))
    bonuses = [e for e in app_events.values() if e["event_type"] == "incentive_published"]
    if len(bonuses) > 1:
        raise ValueError("opportunity may not be spent twice")
    expected_bonus = 2 if bonuses else 0
    if (cp["W"]["loan_bonus"] != expected_bonus or cp["W"]["bonus_used"] != bool(bonuses)
            or cp["W"]["director_resources"] != cp["application_config"]["initial_director_resources"] - expected_bonus
            or cp["W"]["director_resources"] < 0):
        raise ValueError("world incentive/resource state disagrees with committed effects")
    if any(e["event_type"] == "player_key_destroyed" for e in app_events.values()):
        if cp["W"]["intact"]["key1"] or not cp["W"]["destroyed"]["key1"] or cp["W"]["holders"]["key1"] is not None:
            raise ValueError("player destruction was rolled back")
    for who in ("A", "B"):
        own = e1_actor_view(cp, who)["observation"]
        delivered_bonus = any(e["event_type"] == "incentive_published" for e in own.get("known_events", []))
        if own.get("loan_bonus") != (2 if delivered_bonus else 0):
            raise ValueError("actor incentive belief lacks delivered receipt evidence")
    return True


class Executor(E1Executor):
    def __init__(self, checkpoint, model):
        self.model = model
        super().__init__(checkpoint)
        validate_evidence(self._c)

    def start(self, action):
        op = action.get("operator")
        if op == "idle" and self._c["W"]["running_action"] is not None:
            return E0Executor.start(self, action)
        if op not in OPS:
            if op != "idle" and action.get("actor") != slot(self._c):
                return self._reject(action, "WRONG_APPLICATION_SLOT")
            return super().start(action)
        if self._c["W"]["running_action"] is not None:
            return self._reject(action, "SERIAL_TOKEN_BUSY")
        if not _valid_app(self._c, action):
            return self._reject(action, "UNAUTHORIZED_OR_PRECONDITION_FAILED")
        if self._c["clock"]["now"] + 1 > self._c["config_pins"]["deadline"]:
            return self._reject(action, "DEADLINE_EXCEEDED")
        r = self._receipt(action, True, "RUNNING")
        r.update(producer_version=VERSION, duration=1)
        self._c["W"]["running_action"] = {
            "id": r["action_id"], "action_id": r["action_id"], "operator": op,
            "intent": deepcopy(action), "start": self._c["clock"]["now"], "duration": 1,
            "elapsed": 0, "progress": 0, "authority": action["actor"], "receipt_id": r["receipt_id"]}
        return deepcopy(r)

    def _finish(self, running):
        op, action = running["operator"], running["intent"]
        if op not in OPS:
            return super()._finish(running)
        cp, w = self._c, self._c["W"]
        r = next(r for r in cp["receipts"] if r["receipt_id"] == running["receipt_id"])
        if not _valid_app(cp, action, finishing=True):
            r.update(status="INTERRUPTED", outcome="INTERRUPTED_NO_EFFECT", end_time=cp["clock"]["now"])
            w["running_action"] = None
            cp["outcome_history"].append({"receipt_id": r["receipt_id"], "time": cp["clock"]["now"],
                                          "outcome": "INTERRUPTED_NO_EFFECT", "event_ids": []})
            for row in cp["action_history"]:
                if row["receipt_id"] == r["receipt_id"]:
                    row["status"] = "INTERRUPTED"
            return
        before_w, before_o = deepcopy(w), deepcopy(cp["O"])
        if op == "publish_incentive":
            w["director_resources"] -= 2
            w["loan_bonus"], w["bonus_used"] = 2, True
        elif op == "destroy_key1":
            w["destroyed"]["key1"], w["intact"]["key1"], w["holders"]["key1"] = True, False, None
        event = self._event(EVENTS[op], {"actor": action["actor"], **action["args"]})
        event["producer_version"] = VERSION
        visible = ("A", "B") if op in ("publish_incentive", "destroy_key1") else (action["actor"],)
        for who in visible:
            o = cp["O"][who]
            o.setdefault("known_events", []).append(deepcopy(event))
            if op == "publish_incentive":
                o["loan_bonus"] = 2
            elif op == "destroy_key1":
                o["known_facts"] = [f for f in o["known_facts"] if f not in ("key1_held_by_B", "key1_held_by_A")]
                o["known_facts"].append("key1_destroyed")
        if op == "destroy_key1":
            delta = {"intact.key1": [True, False], "destroyed.key1": [False, True],
                     "holders.key1": [before_w["holders"]["key1"], None]}
        else:
            delta = {key: [before_w[key], w[key]] for key in ("director_resources", "loan_bonus", "bonus_used")
                     if before_w[key] != w[key]}
        r.update(status="SUCCESS", outcome="COMPLETED", end_time=cp["clock"]["now"],
                 event_ids=[event["event_id"]], event_payloads=[deepcopy(event)], delta_w=delta,
                 delta_o={who: {"before": before_o[who], "after": deepcopy(cp["O"][who])} for who in visible})
        w["running_action"] = None
        cp["outcome_history"].append({"receipt_id": r["receipt_id"], "time": cp["clock"]["now"],
                                      "outcome": "SETTLED", "event_ids": r["event_ids"]})
        for row in cp["action_history"]:
            if row["receipt_id"] == r["receipt_id"]:
                row["status"] = "SUCCESS"

    def _evaluate_monitor(self):
        validate_evidence(self._c)
        events, receipts = self._c["events"], self._c["receipts"]
        try:
            self._c["events"], self._c["receipts"] = base_view(self._c)["events"], base_view(self._c)["receipts"]
            super()._evaluate_monitor()
        finally:
            self._c["events"], self._c["receipts"] = events, receipts

    def advance_minute(self, started_action_id=None):
        before = self._c["clock"]["now"]
        running = self._c["W"]["running_action"]
        keep_initial_slot = (self._c["scheduler"].get("initial_b_slot_pending")
                             and running is not None and running["authority"] in ("DIRECTOR", "PLAYER"))
        super().advance_minute(started_action_id)
        if keep_initial_slot:
            self._c["scheduler"]["initial_b_slot_pending"] = True
        consume_boundary(self._c, self.model, self._c["clock"]["now"] - before)
        self._c["application_slot"] = select_next_slot(self._c)
        return self.checkpoint()
