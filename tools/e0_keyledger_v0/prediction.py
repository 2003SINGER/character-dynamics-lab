"""Executor-external prediction contract and mismatch diagnostics."""

from copy import deepcopy

PREDICTION_FIELDS = ("intent", "preconditions", "post_world", "post_observation", "effects", "events",
                     "checkpoint_id", "frontier_id", "operator_version", "duration_pin", "deadline_pin", "reply_pin", "coverage")
OPERATOR_VERSION = "E0-KeyLedger-v0"
PRODUCER_VERSION = "e0-keyledger-executor-v0"
PRECONDITIONS = {
    "offer_loan": ["W.locations.A", "W.locations.B", "W.holders.payment", "W.action_used_bits.offer_loan", "O.A.known_entities", "config_pins.reply"],
    "choose_accept": ["W.offer_session.status", "W.action_used_bits.reply", "W.holders.key1", "W.beneficial_owners.key1", "W.intact.key1", "W.destroyed.key1", "O.B.known_entities", "config_pins.reply"],
    "choose_decline": ["W.offer_session.status", "W.action_used_bits.reply", "O.B.known_entities", "config_pins.reply"],
    "accept_loan": ["W.offer_session.status", "W.holders.key1", "W.holders.payment", "W.beneficial_owners.key1", "W.beneficial_owners.payment", "W.intact.key1", "W.destroyed.key1", "W.locations.A", "W.locations.B", "O.B.known_entities"],
    "return_tool": ["W.holders.toolB", "W.locations.A", "W.locations.B", "W.action_used_bits.return_tool", "O.A.known_entities"],
    "unlock": ["O.A.known_entities", "W.holders.key1", "W.intact.key1", "W.destroyed.key1", "W.archive_open", "config_pins.unlock_duration"],
    "take_ledger": ["W.archive_open", "W.holders.ledger", "W.destroyed.ledger", "W.action_used_bits.take_ledger", "O.A.known_entities"],
    "idle": ["clock.now", "config_pins.deadline", "W.running_action"],
}
WORLD_COVERAGE = ["W.t", "W.locations", "W.holders", "W.beneficial_owners", "W.intact", "W.destroyed",
                  "W.archive_open", "W.offer_session", "W.action_used_bits", "W.running_action", "W.reservations"]
OBSERVATION_COVERAGE = ["O.A.known_entities", "O.A.known_facts", "O.B.known_entities", "O.B.known_facts"]
EVENT_COVERAGE = ["event.event_type", "event.time", "event.sequence", "event.producer_version", "event.typed_args"]
EFFECT_COVERAGE = {
    "offer_loan": ["W.offer_session", "W.action_used_bits.offer_loan"],
    "choose_accept": ["W.offer_session", "W.action_used_bits.reply"],
    "choose_decline": ["W.offer_session", "W.action_used_bits.reply"],
    "accept_loan": ["W.holders", "W.beneficial_owners", "W.offer_session", "W.action_used_bits.accept_loan"],
    "return_tool": ["W.holders", "W.action_used_bits.return_tool"],
    "unlock": ["W.archive_open", "W.action_used_bits.unlock"],
    "take_ledger": ["W.holders", "W.action_used_bits.take_ledger"],
    "idle": ["W.t", "clock.now"],
}
MANDATORY_COVERAGE = {
    op: sorted(set(PRECONDITIONS[op] + WORLD_COVERAGE + OBSERVATION_COVERAGE + EFFECT_COVERAGE[op] + EVENT_COVERAGE))
    for op in PRECONDITIONS
}


def prediction_record(action, *, preconditions, post_world, post_observation, effects, events,
                      checkpoint_id, frontier_id, duration_pin, deadline_pin, reply_pin, coverage):
    return {"intent": deepcopy(action), "preconditions": deepcopy(preconditions),
            "post_world": deepcopy(post_world), "post_observation": deepcopy(post_observation),
            "effects": deepcopy(effects), "events": deepcopy(events), "checkpoint_id": checkpoint_id,
            "frontier_id": frontier_id, "operator_version": OPERATOR_VERSION,
            "duration_pin": duration_pin, "deadline_pin": deadline_pin, "reply_pin": reply_pin,
            "coverage": deepcopy(coverage)}


def validate_binding(action, observation, registry=None):
    """Reject unknown grounded bindings before dispatch; executor receives only ActionIntent."""
    op, args = action.get("operator"), action.get("args", {})
    if not isinstance(args, dict):
        return {"status": "INVALID_BINDING", "dispatch": False, "reason": "ARGS_NOT_OBJECT"}
    if op == "offer_loan" and any(key in args for key in ("item", "key", "key_id")):
        return {"status": "INVALID_BINDING", "dispatch": False, "reason": "OFFER_MUST_NOT_BIND_KEY_ID"}
    known = set(observation.get("known_entities", []))
    allowed = set(registry) if registry is not None else None
    for key in ("item", "payment"):
        value = args.get(key)
        if value is not None and (not isinstance(value, str) or (allowed is not None and value not in allowed)):
            return {"status": "INVALID_BINDING", "dispatch": False, "reason": "ENTITY_NOT_IN_REGISTRY"}
        if value is not None and key == "item" and value not in known:
            return {"status": "INVALID_BINDING", "dispatch": False, "reason": "ENTITY_NOT_KNOWN_TO_ACTOR"}
    return {"status": "VALID_BINDING", "dispatch": True}


def _get_path(root, path):
    value = root
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(path)
        value = value[part]
    return value


def audit_prediction(prediction, receipt, actual_delta_w, actual_delta_o, *, actual_world=None,
                     actual_observation=None, before_world=None, before_observation=None,
                     actual_events=None, checkpoint_id=None, frontier_id=None, config_pins=None,
                     required_coverage=None):
    missing = [field for field in PREDICTION_FIELDS if field not in prediction]
    if missing or prediction.get("operator_version") != OPERATOR_VERSION:
        return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": missing,
                "reason": "MISSING_FIELDS_OR_VERSION"}
    required_inputs = {"actual_world": actual_world, "actual_observation": actual_observation,
                       "before_world": before_world, "before_observation": before_observation,
                       "actual_events": actual_events, "checkpoint_id": checkpoint_id,
                       "frontier_id": frontier_id, "config_pins": config_pins}
    absent_inputs = [name for name, value in required_inputs.items() if value is None]
    if absent_inputs:
        return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": absent_inputs,
                "reason": "MISSING_AUDIT_EVIDENCE"}
    action = prediction["intent"]
    op = action.get("operator") if isinstance(action, dict) else None
    if op not in PRECONDITIONS:
        return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": [], "reason": "UNKNOWN_OPERATOR_VERSION"}
    if prediction["intent"] != receipt.get("intent"):
        return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": [], "reason": "RECEIPT_INTENT_MISMATCH"}
    if (prediction["checkpoint_id"] != checkpoint_id or prediction["frontier_id"] != frontier_id
            or prediction["deadline_pin"] != config_pins.get("deadline")
            or prediction["reply_pin"] != config_pins.get("reply")
            or prediction["duration_pin"] != config_pins.get("unlock_duration")):
        return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": [], "reason": "FRONTIER_OR_PIN_MISMATCH"}
    if receipt.get("producer_version") != PRODUCER_VERSION or not receipt.get("receipt_id"):
        return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": [], "reason": "INVALID_EXECUTOR_RECEIPT"}
    status = receipt.get("status")
    if (status not in ("SUCCESS", "REJECTED", "INTERRUPTED")
            or (status == "REJECTED" and receipt.get("accepted") is not False)
            or (status in ("SUCCESS", "INTERRUPTED") and receipt.get("accepted") is not True)):
        return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": [], "reason": "INVALID_RECEIPT_STATUS"}
    if receipt.get("delta_w") != actual_delta_w or receipt.get("delta_o") != actual_delta_o:
        return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": [], "reason": "RECEIPT_DELTA_CONFLICT"}
    coverage = prediction.get("coverage")
    if isinstance(coverage, list):
        coverage_items = coverage
    elif isinstance(coverage, dict):
        if any(not isinstance(items, list) for items in coverage.values()):
            return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": ["coverage"], "reason": "INVALID_COVERAGE"}
        coverage_items = [item for items in coverage.values() for item in items]
    else:
        return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": ["coverage"], "reason": "INVALID_COVERAGE"}
    if any(not isinstance(item, str) or not item for item in coverage_items):
        return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": ["coverage"], "reason": "INVALID_COVERAGE"}
    required = set(MANDATORY_COVERAGE[op])
    if required_coverage is not None:
        required |= set(required_coverage)
    provided = set(coverage_items)
    absent = sorted(required - provided)
    unknown_coverage = sorted(provided - set(MANDATORY_COVERAGE[op]))
    if absent or unknown_coverage:
        return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": absent,
                "unexpected_coverage": unknown_coverage, "reason": "INCOMPLETE_OR_UNKNOWN_COVERAGE"}
    if not isinstance(prediction["preconditions"], dict) or not isinstance(prediction["effects"], dict):
        return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": [], "reason": "INVALID_TYPED_PREDICTION"}
    if not isinstance(prediction["events"], list) or not isinstance(prediction["post_world"], dict) or not isinstance(prediction["post_observation"], dict):
        return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": [], "reason": "INVALID_TYPED_PREDICTION"}
    try:
        precondition_mismatches = []
        for path, expected in prediction["preconditions"].items():
            actual_value = receipt.get("start_time") if path == "clock.now" else _get_path(
                {"W": before_world, "O": before_observation, "config_pins": config_pins}, path)
            if actual_value != expected:
                precondition_mismatches.append(path)
    except KeyError as exc:
        return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": [str(exc)], "reason": "UNKNOWN_PRECONDITION_FIELD"}
    if set(prediction["preconditions"]) != set(PRECONDITIONS[op]):
        return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": sorted(set(PRECONDITIONS[op]) - set(prediction["preconditions"])),
                "reason": "PRECONDITION_COVERAGE_MISMATCH"}
    expected_signatures = prediction["events"]
    receipt_event_ids = receipt.get("event_ids", [])
    if not isinstance(receipt_event_ids, list):
        return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": [], "reason": "INVALID_RECEIPT_EVENT_IDS"}
    selected_events = [event for event in actual_events if event.get("event_id") in receipt_event_ids]
    if {event.get("event_id") for event in selected_events} != set(receipt_event_ids):
        return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": [], "reason": "RECEIPT_EVENT_LEDGER_CONFLICT"}
    actual_signatures = [{"event_type": event.get("event_type"), "time": event.get("time"),
                          "sequence": event.get("sequence"), "producer_version": event.get("producer_version"),
                          "typed_args": deepcopy(event.get("typed_args"))} for event in selected_events]
    receipt_payloads = receipt.get("event_payloads")
    if not isinstance(receipt_payloads, list) or receipt_payloads != selected_events:
        return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": [], "reason": "RECEIPT_EVENT_PAYLOAD_CONFLICT"}
    if any(event.get("producer_version") != PRODUCER_VERSION for event in selected_events):
        return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": [], "reason": "EVENT_PRODUCER_VERSION_MISMATCH"}
    if (receipt.get("status") in ("SUCCESS", "INTERRUPTED")
            and [event.get("event_id") for event in selected_events] != receipt.get("event_ids", [])):
        return {"status": "PREDICTION_CONTRACT_ERROR", "missing_fields": [], "reason": "RECEIPT_EVENT_LEDGER_CONFLICT"}
    expected = {"world": prediction["post_world"], "observation": prediction["post_observation"],
                "effects": prediction["effects"], "events": expected_signatures}
    actual = {"world": deepcopy(actual_delta_w), "observation": deepcopy(actual_delta_o),
              "post_world": deepcopy(actual_world), "post_observation": deepcopy(actual_observation),
              "events": actual_signatures, "receipt": deepcopy(receipt)}
    mismatches = []
    if precondition_mismatches:
        mismatches.append("PRECONDITIONS:" + ",".join(precondition_mismatches))
    if prediction["post_world"] != actual_world:
        mismatches.append("POST_WORLD")
    if prediction["post_observation"] != actual_observation:
        mismatches.append("POST_OBSERVATION")
    expected_delta_o = {}
    for who in ("A", "B"):
        old, new = before_observation[who], prediction["post_observation"][who]
        expected_delta_o[who] = {field: {
            "added": [x for x in new[field] if x not in old[field]],
            "removed": [x for x in old[field] if x not in new[field]],
        } for field in ("known_entities", "known_facts")}
    if expected_delta_o != actual_delta_o:
        mismatches.append("OBSERVATION_PROJECTION")
    if prediction["effects"] != actual_delta_w:
        mismatches.append("WORLD_EFFECTS")
    if expected_signatures != actual_signatures:
        mismatches.append("EVENTS")
    if prediction.get("predicted_delta_o") is not None and prediction["predicted_delta_o"] != actual_delta_o:
        mismatches.append("OBSERVATION_PROJECTION")
    return {"status": "PREDICTION_MISMATCH" if mismatches else "MATCH",
            "mismatches": mismatches, "expected": expected, "actual": actual}
