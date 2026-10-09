"""Independent finite executor for E0-KeyLedger-v0."""

from copy import deepcopy

from .fixtures import PRODUCER_VERSION

OPERATORS = ("offer_loan", "choose_accept", "choose_decline", "accept_loan", "return_tool", "unlock", "take_ledger", "idle")
_CHECKPOINT_ATOMIC_TYPES = (str, int, float, bool, type(None))


def _checkpoint_copy(value, memo=None):
    """Copy JSON-shaped checkpoint containers while preserving deepcopy memo semantics."""
    if memo is None:
        memo = {}
    value_type = type(value)
    if value_type in _CHECKPOINT_ATOMIC_TYPES:
        return value
    if value_type is dict:
        identity = id(value)
        if identity in memo:
            return memo[identity]
        copied = {}
        memo[identity] = copied
        for key, item in value.items():
            copied_key = key if type(key) in _CHECKPOINT_ATOMIC_TYPES else _checkpoint_copy(key, memo)
            copied_value = item if type(item) in _CHECKPOINT_ATOMIC_TYPES else _checkpoint_copy(item, memo)
            copied[copied_key] = copied_value
        return copied
    if value_type is list:
        identity = id(value)
        if identity in memo:
            return memo[identity]
        copied = []
        memo[identity] = copied
        copied.extend(item if type(item) in _CHECKPOINT_ATOMIC_TYPES else _checkpoint_copy(item, memo)
                      for item in value)
        return copied
    # Keep stdlib behavior for tuples, subclasses, and any future non-JSON values;
    # sharing the memo preserves aliases between fallback objects and copied containers.
    return deepcopy(value, memo)


def intent(operator, **typed_args):
    return {"operator": operator, "actor": _actor(operator) if isinstance(operator, str) else None,
            "args": deepcopy(typed_args)}


def _actor(operator):
    return {"offer_loan": "A", "choose_accept": "B", "choose_decline": "B", "accept_loan": "B",
            "return_tool": "A", "unlock": "A", "take_ledger": "A", "idle": "WorldStep"}.get(operator)


def _same_place(w):
    return w["locations"]["A"] == w["locations"]["B"] == "ENTRANCE"


def _valid(checkpoint, action):
    op, actor, args = action.get("operator"), action.get("actor"), action.get("args", {})
    if not isinstance(op, str) or op not in OPERATORS or actor != _actor(op) or not isinstance(args, dict):
        return False, "INVALID_TYPED_INTENT"
    w = checkpoint["W"]
    s = w["offer_session"]
    if op == "idle":
        return args == {}, "" if args == {} else "INVALID_TYPED_INTENT"
    if op == "offer_loan":
        ok = (not w["action_used_bits"]["offer_loan"] and args == {"target": "B", "payment": "payment"}
              and _same_place(w) and w["holders"]["payment"] == "A"
              and "payment" in checkpoint["O"]["A"]["known_entities"])
    elif op in ("choose_accept", "choose_decline"):
        reply = "ACCEPT" if op == "choose_accept" else "DECLINE"
        pin = checkpoint["config_pins"]["reply"]
        ok = (s["status"] == "OFFERED" and not w["action_used_bits"]["reply"]
              and args == {"offer_id": s["offer_id"]} and s["offer_id"] in checkpoint["O"]["B"]["known_entities"]
              and (pin == "JOINT" or pin == reply))
        if reply == "ACCEPT":
            ok = (ok and w["holders"]["key1"] == "B" and w["beneficial_owners"]["key1"] == "B"
                  and w["intact"]["key1"] and not w["destroyed"]["key1"])
    elif op == "accept_loan":
        ok = (s["status"] == "ACCEPTED" and not w["action_used_bits"]["accept_loan"]
              and args == {"actor": "A", "item": "key1", "payment": "payment", "offer_id": s["offer_id"]}
              and _same_place(w) and w["holders"]["key1"] == "B" and w["intact"]["key1"]
              and not w["destroyed"]["key1"] and w["holders"]["payment"] == "A"
              and w["beneficial_owners"]["key1"] == "B" and w["beneficial_owners"]["payment"] == "A"
              and "key1" in checkpoint["O"]["B"]["known_entities"]
              and "payment" in checkpoint["O"]["B"]["known_entities"])
    elif op == "return_tool":
        ok = (not w["action_used_bits"]["return_tool"] and args == {"target": "B", "item": "toolB"}
              and _same_place(w) and w["holders"]["toolB"] == "A"
              and "toolB" in checkpoint["O"]["A"]["known_entities"])
    elif op == "unlock":
        ok = (not w["action_used_bits"]["unlock"] and args == {"item": "key1"} and _same_place(w)
              and "key1" in checkpoint["O"]["A"]["known_entities"] and w["holders"]["key1"] == "A"
              and w["intact"]["key1"] and not w["destroyed"]["key1"] and not w["archive_open"])
    else:  # take_ledger
        ok = (not w["action_used_bits"]["take_ledger"] and args == {"item": "ledger"} and _same_place(w)
              and w["archive_open"] and w["holders"]["ledger"] == "ARCHIVE" and not w["destroyed"]["ledger"]
              and "ledger" in checkpoint["O"]["A"]["known_entities"])
    return (bool(ok), "" if ok else "PRECONDITION_FAILED")


def legal_intents(checkpoint):
    w, s = checkpoint["W"], checkpoint["W"]["offer_session"]
    if w["running_action"] is not None:
        return [intent("idle")]
    result = []
    def add(op, **args):
        candidate = intent(op, **args)
        if _valid(checkpoint, candidate)[0]:
            result.append(candidate)
    if not w["action_used_bits"]["offer_loan"]:
        add("offer_loan", target="B", payment="payment")
    if s["status"] == "OFFERED":
        add("choose_accept", offer_id=s["offer_id"])
        add("choose_decline", offer_id=s["offer_id"])
    if s["status"] == "ACCEPTED":
        add("accept_loan", actor="A", item="key1", payment="payment", offer_id=s["offer_id"])
    add("return_tool", target="B", item="toolB")
    add("unlock", item="key1")
    add("take_ledger", item="ledger")
    add("idle")
    return result


class Executor:
    def __init__(self, checkpoint):
        self._c = _checkpoint_copy(checkpoint)

    def checkpoint(self):
        return _checkpoint_copy(self._c)

    def _id(self, kind):
        value = self._c["next_ids"][kind]
        self._c["next_ids"][kind] += 1
        return f"{kind}-{value:06d}"

    def _receipt(self, action, accepted, status, reason=None):
        rid = self._id("receipt")
        aid = self._id("action")
        receipt = {"receipt_id": rid, "action_id": aid, "producer_version": PRODUCER_VERSION,
                   "intent": deepcopy(action), "accepted": bool(accepted),
                   "start_time": self._c["clock"]["now"], "end_time": None,
                   "status": "RUNNING" if accepted else "REJECTED", "outcome": reason,
                   "event_ids": [], "event_payloads": [], "delta_w": {}, "delta_o": {}}
        self._c["receipts"].append(receipt)
        self._c["action_history"].append({"action_id": aid, "receipt_id": rid, "time": self._c["clock"]["now"],
                                          "intent": deepcopy(action), "status": status})
        return receipt

    def start(self, action):
        action = deepcopy(action)
        if action.get("operator") == "idle":
            valid, reason = _valid(self._c, action)
            if self._c["clock"]["now"] >= self._c["config_pins"]["deadline"]:
                valid, reason = False, "DEADLINE_EXCEEDED"
            if not valid:
                receipt = self._receipt(action, False, "REJECTED_BEFORE_START", reason)
                receipt["end_time"] = self._c["clock"]["now"]
                self._c["outcome_history"].append({"receipt_id": receipt["receipt_id"],
                    "time": self._c["clock"]["now"], "outcome": "REJECTED_BEFORE_START", "reason": reason})
                return deepcopy(receipt)
            running = self._c["W"]["running_action"]
            return {"receipt_id": running["receipt_id"] if running else None,
                    "action_id": running["id"] if running else None,
                    "producer_version": PRODUCER_VERSION, "intent": action,
                    "accepted": True, "start_time": self._c["clock"]["now"],
                    "end_time": None, "status": "NO_CONTROL_ACK",
                    "outcome": None, "event_ids": [], "delta_w": {}, "delta_o": {}}
        valid, reason = _valid(self._c, action)
        if self._c["W"]["running_action"] is not None:
            valid, reason = False, "SERIAL_TOKEN_BUSY"
        duration = self._c["config_pins"]["unlock_duration"] if action.get("operator") == "unlock" else 1
        if valid and self._c["clock"]["now"] + duration > self._c["config_pins"]["deadline"]:
            valid, reason = False, "DEADLINE_EXCEEDED"
        receipt = self._receipt(action, valid, "RUNNING" if valid else "REJECTED_BEFORE_START", reason or None)
        if not valid:
            receipt["end_time"] = self._c["clock"]["now"]
            self._c["outcome_history"].append({"receipt_id": receipt["receipt_id"], "time": self._c["clock"]["now"], "outcome": "REJECTED_BEFORE_START", "reason": reason})
            return deepcopy(receipt)
        op = action["operator"]
        aid = receipt["action_id"]
        self._c["W"]["running_action"] = {"id": aid, "action_id": aid, "operator": op, "intent": action,
                                           "start": self._c["clock"]["now"], "duration": duration,
                                           "elapsed": 0, "authority": action["actor"], "progress": 0,
                                           "receipt_id": receipt["receipt_id"]}
        if duration > 1:
            self._c["W"]["reservations"] = [{"action_id": aid, "resources": ["key1", "ARCHIVE"]}]
        return deepcopy(receipt)

    def _event(self, name, args):
        event = {"event_id": self._id("event"), "event_type": name, "time": self._c["clock"]["now"],
                 "sequence": self._c["next_ids"]["sequence"], "producer_version": PRODUCER_VERSION,
                 "typed_args": {"event": name, **deepcopy(args)}}
        self._c["next_ids"]["sequence"] += 1
        self._c["events"].append(event)
        return event

    def _project_visible(self, op):
        oa, ob = self._c["O"]["A"], self._c["O"]["B"]
        def replace_fact(observation, old, new):
            observation["known_facts"] = [fact for fact in observation["known_facts"] if fact != old]
            if new not in observation["known_facts"]:
                observation["known_facts"].append(new)
        if op in ("offer_loan", "choose_accept", "choose_decline", "accept_loan", "return_tool", "unlock", "take_ledger"):
            fact = {"offer_loan": "offer_visible", "choose_accept": "reply_accept_visible",
                    "choose_decline": "reply_decline_visible", "accept_loan": "exchange_visible",
                    "return_tool": "tool_return_visible", "unlock": "archive_open", "take_ledger": "ledger_held_by_A"}[op]
            for o in (oa, ob):
                if fact not in o["known_facts"]:
                    o["known_facts"].append(fact)
        if op == "offer_loan":
            offer_id = self._c["W"]["offer_session"]["offer_id"]
            for observation in (oa, ob):
                for entity in ("payment", offer_id):
                    if entity not in observation["known_entities"]:
                        observation["known_entities"].append(entity)
        if op == "choose_accept" and "key1" not in oa["known_entities"]:
            oa["known_entities"].append("key1")
            oa["known_facts"].append("key1_disclosed_by_B")
        if op == "accept_loan":
            for observation in (oa, ob):
                replace_fact(observation, "key1_held_by_B", "key1_held_by_A")
                replace_fact(observation, "payment_held_by_A", "payment_held_by_B")
        elif op == "return_tool":
            for observation in (oa, ob):
                replace_fact(observation, "toolB_held_by_A", "toolB_held_by_B")
        elif op == "unlock":
            for observation in (oa, ob):
                replace_fact(observation, "archive_closed", "archive_open")
        elif op == "take_ledger":
            for observation in (oa, ob):
                replace_fact(observation, "ledger_in_archive", "ledger_held_by_A")

    def _finish(self, running):
        op = running["operator"]
        w = self._c["W"]
        before_w, before_o = deepcopy(w), deepcopy(self._c["O"])
        events = []
        session = w["offer_session"]
        if op != "idle" and not self._settlement_preconditions(running):
            w["running_action"] = None
            w["reservations"] = []
            receipt = next(r for r in self._c["receipts"] if r["receipt_id"] == running["receipt_id"])
            receipt.update({"status": "INTERRUPTED", "outcome": "INTERRUPTED_NO_EFFECT",
                           "end_time": self._c["clock"]["now"]})
            self._c["outcome_history"].append({"receipt_id": receipt["receipt_id"],
                "time": self._c["clock"]["now"], "outcome": "INTERRUPTED_NO_EFFECT", "event_ids": []})
            for row in self._c["action_history"]:
                if row["action_id"] == receipt["action_id"]:
                    row["status"] = "INTERRUPTED"
            return
        if op == "offer_loan":
            offer_id = f"offer-{running['id'].split('-')[-1]}"
            session.update({"status": "OFFERED", "offer_id": offer_id,
                            "terms": {"payment": "payment", "amount": 1, "item": "any disclosed lendable key"}})
        elif op == "choose_accept":
            session.update({"status": "ACCEPTED", "reply_time": self._c["clock"]["now"]})
            events.append(self._event("loan_reply_accepted", {"actor": "B", "offer_id": session["offer_id"], "item": "key1"}))
        elif op == "choose_decline":
            session.update({"status": "DECLINED", "reply_time": self._c["clock"]["now"]})
            events.append(self._event("loan_reply_declined", {"actor": "B", "offer_id": session["offer_id"]}))
        elif op == "accept_loan":
            w["holders"]["key1"], w["holders"]["payment"] = "A", "B"
            w["beneficial_owners"]["payment"] = "B"
            session["status"] = "SETTLED"
            events.append(self._event("loan_exchanged", {"actor": "B", "item": "key1", "payment": "payment", "offer_id": session["offer_id"]}))
        elif op == "return_tool":
            w["holders"]["toolB"] = "B"
            events.append(self._event("tool_returned", {"actor": "A", "item": "toolB"}))
        elif op == "unlock":
            w["archive_open"] = True
            events.append(self._event("archive_unlocked", {"actor": "A", "item": "ARCHIVE", "key": "key1"}))
        elif op == "take_ledger":
            w["holders"]["ledger"] = "A"
            events.append(self._event("ledger_acquired", {"actor": "A", "item": "ledger"}))
        self._project_visible(op)
        bits = w["action_used_bits"]
        if op == "offer_loan":
            bits["offer_loan"] = True
        elif op in ("choose_accept", "choose_decline"):
            bits["reply"] = True
        elif op == "accept_loan":
            bits["accept_loan"] = True
        elif op == "return_tool":
            bits["return_tool"] = True
        elif op == "unlock":
            bits["unlock"] = True
        elif op == "take_ledger":
            bits["take_ledger"] = True
        w["running_action"] = None
        w["reservations"] = []
        receipt = next(r for r in self._c["receipts"] if r["receipt_id"] == running["receipt_id"])
        receipt["status"] = "SUCCESS"
        receipt["outcome"] = "COMPLETED"
        receipt["end_time"] = self._c["clock"]["now"]
        receipt["event_ids"] = [e["event_id"] for e in events]
        receipt["event_payloads"] = deepcopy(events)
        receipt["delta_w"] = {k: deepcopy([before_w[k], w[k]]) for k in w
                               if before_w[k] != w[k] and k not in ("running_action", "reservations")}
        receipt["delta_o"] = {who: {field: {
                                        "added": [x for x in self._c["O"][who][field] if x not in before_o[who][field]],
                                        "removed": [x for x in before_o[who][field] if x not in self._c["O"][who][field]],
                                    } for field in ("known_entities", "known_facts")}
                               for who in ("A", "B")}
        outcome = "NO_CONTROL" if op == "idle" else "SETTLED"
        self._c["outcome_history"].append({"receipt_id": receipt["receipt_id"], "time": self._c["clock"]["now"],
                                           "outcome": outcome, "event_ids": receipt["event_ids"]})
        for row in self._c["action_history"]:
            if row["action_id"] == receipt["action_id"]:
                row["status"] = "SUCCESS"

    def _settlement_preconditions(self, running):
        """Recheck world conditions that can change after action start."""
        op, w = running["operator"], self._c["W"]
        same_place = w["locations"]["A"] == w["locations"]["B"] == "ENTRANCE"
        holders, session = w["holders"], w["offer_session"]
        if op == "offer_loan":
            return same_place and holders["payment"] == "A" and "payment" in self._c["O"]["A"]["known_entities"]
        if op == "choose_accept":
            return (session["status"] == "OFFERED" and session["offer_id"] in self._c["O"]["B"]["known_entities"]
                    and holders["key1"] == "B" and w["beneficial_owners"]["key1"] == "B"
                    and w["intact"]["key1"] and not w["destroyed"]["key1"])
        if op == "choose_decline":
            return session["status"] == "OFFERED" and session["offer_id"] in self._c["O"]["B"]["known_entities"]
        if op == "accept_loan":
            return (session["status"] == "ACCEPTED" and same_place and holders["key1"] == "B"
                    and w["intact"]["key1"] and not w["destroyed"]["key1"] and holders["payment"] == "A"
                    and w["beneficial_owners"]["key1"] == "B" and w["beneficial_owners"]["payment"] == "A"
                    and "key1" in self._c["O"]["B"]["known_entities"]
                    and "payment" in self._c["O"]["B"]["known_entities"])
        if op == "return_tool":
            return same_place and holders["toolB"] == "A" and "toolB" in self._c["O"]["A"]["known_entities"]
        if op == "unlock":
            return (same_place and "key1" in self._c["O"]["A"]["known_entities"]
                    and holders["key1"] == "A" and w["intact"]["key1"]
                    and not w["destroyed"]["key1"] and not w["archive_open"])
        if op == "take_ledger":
            return (same_place and w["archive_open"] and holders["ledger"] == "ARCHIVE"
                    and not w["destroyed"]["ledger"] and "ledger" in self._c["O"]["A"]["known_entities"])
        return False

    def advance_minute(self, started_action_id=None):
        w = self._c["W"]
        if self._c["clock"]["now"] >= self._c["config_pins"]["deadline"]:
            raise ValueError("cannot advance beyond the pinned E0 deadline")
        if w["running_action"] is None:
            if started_action_id is not None:
                raise ValueError("cannot mark a new actor action when no action is running")
            receipt = self._receipt(intent("idle"), True, "RUNNING")
            self._c["minute_history"].append({"from_time": self._c["clock"]["now"],
                "to_time": self._c["clock"]["now"] + 1, "control": "NO_CONTROL",
                "action_id": receipt["action_id"], "running_action_id": None})
            self._c["clock"]["now"] += 1
            w["t"] = self._c["clock"]["now"]
            receipt.update({"status": "SUCCESS", "outcome": "NO_CONTROL",
                            "end_time": self._c["clock"]["now"]})
            receipt["delta_w"] = {"t": [self._c["clock"]["now"] - 1, self._c["clock"]["now"]]}
            receipt["delta_o"] = {who: {field: {"added": [], "removed": []}
                                        for field in ("known_entities", "known_facts")}
                                   for who in ("A", "B")}
            self._c["outcome_history"].append({"receipt_id": receipt["receipt_id"],
                "time": self._c["clock"]["now"], "outcome": "NO_CONTROL", "event_ids": []})
            for row in self._c["action_history"]:
                if row["action_id"] == receipt["action_id"]:
                    row["status"] = "SUCCESS"
        else:
            running = deepcopy(w["running_action"])
            if started_action_id is None and running["operator"] != "idle" and running["elapsed"] == 0:
                started_action_id = running["action_id"]
            first_boundary = started_action_id is not None
            row = {"from_time": self._c["clock"]["now"], "to_time": self._c["clock"]["now"] + 1,
                   "control": "ACTION_START" if first_boundary else "NO_CONTROL",
                   "action_id": started_action_id if first_boundary else None,
                   "running_action_id": running["id"]}
            if first_boundary:
                row["intent"] = deepcopy(running["intent"])
            self._c["minute_history"].append(row)
            self._c["clock"]["now"] += 1
            w["t"] = self._c["clock"]["now"]
            running["elapsed"] += 1
            running["progress"] = running["elapsed"]
            w["running_action"]["elapsed"] = running["elapsed"]
            w["running_action"]["progress"] = running["progress"]
            if running["elapsed"] >= running["duration"]:
                self._finish(running)
        self._c["seals"].append({"sealed_through": self._c["clock"]["now"],
                                 "producer_version": PRODUCER_VERSION,
                                 "sequence_frontier": self._c["next_ids"]["sequence"] - 1})
        self._evaluate_monitor()
        return self.checkpoint()

    def no_control(self):
        return self.advance_minute()

    def execute(self, action):
        if action.get("operator") == "idle":
            ack = self.start(action)
            if not ack["accepted"]:
                return ack
            before = len(self._c["receipts"])
            active_id = self._c["W"]["running_action"]
            self.advance_minute()
            if len(self._c["receipts"]) > before:
                return deepcopy(self._c["receipts"][-1])
            return deepcopy(next(r for r in self._c["receipts"] if r["receipt_id"] == active_id["receipt_id"]))
        receipt = self.start(action)
        if not receipt["accepted"]:
            return receipt
        first_boundary = True
        while self._c["W"]["running_action"] is not None:
            self.advance_minute(started_action_id=receipt["action_id"] if first_boundary else None)
            first_boundary = False
        return deepcopy(next(r for r in self._c["receipts"] if r["receipt_id"] == receipt["receipt_id"]))

    def _evaluate_monitor(self):
        self._validate_ledger_and_seals()
        witness = None
        seals = self._c["seals"]
        for event in self._c["events"]:
            if (event.get("event_type") == "ledger_acquired" and event["typed_args"].get("actor") == "A"
                    and event["typed_args"].get("item") == "ledger"
                    and event["time"] <= self._c["config_pins"]["deadline"]
                    and any(seal["sealed_through"] >= event["time"]
                            and seal["sequence_frontier"] >= event["sequence"] for seal in seals)):
                witness = event
                break
        complete_through = 1
        seal_by_time = {seal["sealed_through"]: seal for seal in seals}
        for minute in range(2, self._c["clock"]["now"] + 1):
            if minute not in seal_by_time:
                break
            complete_through = minute
        if witness is not None and 2 <= witness["time"] <= self._c["config_pins"]["deadline"]:
            self._c["monitor"] = {"status": "SATISFIED", "witness_event_id": witness["event_id"],
                                  "witness_time": witness["time"], "witness_sequence": witness["sequence"],
                                  "coverage_complete_through": complete_through, "reason": "SETTLEMENT_WITNESS"}
        elif self._c["clock"]["now"] >= self._c["config_pins"]["deadline"]:
            complete = complete_through >= self._c["config_pins"]["deadline"]
            status = "VIOLATED" if complete else "INDETERMINATE"
            self._c["monitor"] = {"status": status, "witness_event_id": None,
                                  "coverage_complete_through": complete_through,
                                  "reason": "COMPLETE_NO_WITNESS" if complete else "MISSING_PAST_COVERAGE"}
        else:
            complete = complete_through >= self._c["clock"]["now"]
            status = "PENDING" if complete else "INDETERMINATE"
            self._c["monitor"] = {"status": status, "witness_event_id": None,
                                  "coverage_complete_through": complete_through,
                                  "reason": "NO_WITNESS" if complete else "MISSING_PAST_COVERAGE"}

    def _validate_ledger_and_seals(self):
        allowed_args = {
            "key_destroyed": {"actor", "item"},
            "loan_reply_accepted": {"actor", "offer_id", "item"},
            "loan_reply_declined": {"actor", "offer_id"},
            "loan_exchanged": {"actor", "item", "payment", "offer_id"},
            "tool_returned": {"actor", "item"},
            "archive_unlocked": {"actor", "item", "key"},
            "ledger_acquired": {"actor", "item"},
        }
        receipt_by_event = {}
        for receipt in self._c["receipts"]:
            if receipt.get("producer_version") != PRODUCER_VERSION:
                raise ValueError("CONTRACT_ERROR: receipt producer version mismatch")
            ids = receipt.get("event_ids")
            payloads = receipt.get("event_payloads")
            if not isinstance(ids, list) or not isinstance(payloads, list):
                raise ValueError("CONTRACT_ERROR: malformed receipt event fields")
            if ids != [event.get("event_id") for event in payloads]:
                raise ValueError("CONTRACT_ERROR: receipt event ids/payloads conflict")
            for event in payloads:
                event_id = event.get("event_id")
                if event_id in receipt_by_event:
                    raise ValueError("CONTRACT_ERROR: event belongs to multiple receipts")
                receipt_by_event[event_id] = (receipt, event)
        event_ids, sequences = set(), set()
        # Validate the append-only ledger in its recorded order; never sort malformed
        # evidence into a valid-looking sequence.
        ordered = self._c["events"]
        prior_time, prior_sequence = -1, -1
        for event in ordered:
            event_id, seq, event_time = event.get("event_id"), event.get("sequence"), event.get("time")
            if (not isinstance(event_id, str) or event_id in event_ids
                    or not isinstance(seq, int) or isinstance(seq, bool) or seq < 0 or seq in sequences
                    or not isinstance(event_time, int) or isinstance(event_time, bool) or event_time < 0):
                raise ValueError("CONTRACT_ERROR: malformed or duplicate event identity/time")
            if event_time < prior_time or seq <= prior_sequence:
                raise ValueError("CONTRACT_ERROR: event ledger order is not chronological")
            event_ids.add(event_id)
            sequences.add(seq)
            prior_time = event_time
            prior_sequence = seq
            if event.get("producer_version") != PRODUCER_VERSION:
                raise ValueError("CONTRACT_ERROR: event producer version mismatch")
            event_type, args = event.get("event_type"), event.get("typed_args")
            if (event_type not in allowed_args or not isinstance(args, dict)
                    or args.get("event") != event_type
                    or set(args) != (allowed_args[event_type] | {"event"})
                    or any(not isinstance(value, str) for value in args.values())):
                raise ValueError("CONTRACT_ERROR: malformed event signature")
            pair = receipt_by_event.get(event_id)
            if pair is None or pair[1] != event:
                raise ValueError("CONTRACT_ERROR: event has no matching producer receipt")
            receipt = pair[0]
            if (not receipt.get("accepted") or receipt.get("status") != "SUCCESS"
                    or receipt.get("outcome") not in ("COMPLETED", "DESTROYED")
                    or receipt.get("producer_version") != PRODUCER_VERSION):
                raise ValueError("CONTRACT_ERROR: event receipt is not a successful settlement")
        if event_ids != set(receipt_by_event):
            raise ValueError("CONTRACT_ERROR: receipt references an absent event")
        seals_by_time = {}
        prior_frontier, prior_seal_minute = -1, 0
        for seal in self._c["seals"]:
            minute, frontier = seal.get("sealed_through"), seal.get("sequence_frontier")
            if (seal.get("producer_version") != PRODUCER_VERSION
                    or not isinstance(minute, int) or isinstance(minute, bool)
                    or not isinstance(frontier, int) or isinstance(frontier, bool)
                    or minute in seals_by_time or minute <= prior_seal_minute
                    or minute < 1 or minute > self._c["clock"]["now"] or frontier < prior_frontier):
                raise ValueError("CONTRACT_ERROR: malformed or nonmonotonic coverage seal")
            if any(event["time"] <= minute and event["sequence"] > frontier for event in ordered):
                raise ValueError("CONTRACT_ERROR: seal omits an already settled event")
            if any(event["time"] > minute and event["sequence"] <= frontier for event in ordered):
                raise ValueError("CONTRACT_ERROR: seal covers a future event")
            seals_by_time[minute] = seal
            prior_frontier = frontier
            prior_seal_minute = minute
        # A goal witness must be the precise receipt-backed take settlement, not a state or free-form event.
        for event in ordered:
            if event["event_type"] != "ledger_acquired":
                continue
            receipt = receipt_by_event[event["event_id"]][0]
            if (event["typed_args"] != {"event": "ledger_acquired", "actor": "A", "item": "ledger"}
                    or receipt.get("intent") != {"operator": "take_ledger", "actor": "A", "args": {"item": "ledger"}}
                    or receipt.get("end_time") != event["time"] or receipt.get("event_ids") != [event["event_id"]]
                    or not isinstance(receipt.get("delta_w", {}).get("holders"), list)
                    or receipt["delta_w"]["holders"][0].get("ledger") != "ARCHIVE"
                    or receipt["delta_w"]["holders"][1].get("ledger") != "A"):
                raise ValueError("CONTRACT_ERROR: ledger_acquired event does not match take settlement")
