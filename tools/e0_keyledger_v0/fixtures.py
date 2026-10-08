"""The 14 frozen E0-KeyLedger-v0 input fixtures."""

from copy import deepcopy

CASE_IDS = (
    "E0-P01", "E0-N01", "E0-B01", "E0-B02", "E0-B03", "E0-H01",
    "E0-N02", "E0-H02", "E0-X01", "E0-X02", "E0-P02", "E0-U01",
    "E0-C01", "E0-F01",
)
ENTITY_IDS = ("A", "B", "PLAYER", "key0", "key1", "ledger", "payment", "toolB", "ARCHIVE", "ENTRANCE")
PRODUCER_VERSION = "e0-keyledger-executor-v0"


def initial_checkpoint(case_id="E0-P01", *, deadline=None, reply_pin=None, unlock_duration=None):
    if case_id not in CASE_IDS:
        raise ValueError("unknown E0 fixture: " + str(case_id))
    default_deadline = 7 if case_id == "E0-B01" else 6 if case_id == "E0-B02" else 10
    if deadline is None:
        deadline = default_deadline
    if reply_pin is None:
        reply_pin = "DECLINE" if case_id in ("E0-N01", "E0-N02") else "ACCEPT"
    if case_id == "E0-N02" and reply_pin != "DECLINE":
        raise ValueError("E0-N02 freezes BReplyPin=DECLINE")
    if case_id == "E0-N01" and reply_pin != "DECLINE":
        raise ValueError("E0-N01 freezes BReplyPin=DECLINE")
    if case_id != "E0-P01" and case_id not in ("E0-N01", "E0-N02") and reply_pin != "ACCEPT":
        raise ValueError("only E0-P01 supports the D_joint reply condition")
    if unlock_duration is None:
        unlock_duration = 3 if case_id == "E0-P02" else 1
    if deadline != default_deadline:
        raise ValueError("deadline override is outside the frozen fixture pins")
    if case_id == "E0-P02":
        if unlock_duration != 3:
            raise ValueError("E0-P02 freezes unlock duration=3")
    elif unlock_duration != 1:
        raise ValueError("duration override is outside the frozen fixture pins")
    if reply_pin not in ("ACCEPT", "DECLINE", "JOINT"):
        raise ValueError("reply_pin must be ACCEPT, DECLINE, or JOINT")
    if not isinstance(deadline, int) or isinstance(deadline, bool) or not 2 <= deadline <= 10:
        raise ValueError("deadline must be an integer in [2,10]")
    if not isinstance(unlock_duration, int) or isinstance(unlock_duration, bool) or unlock_duration not in (1, 3):
        raise ValueError("unlock_duration must be 1 or 3")

    holders = {"key0": None, "key1": "B", "ledger": "ARCHIVE", "payment": "A", "toolB": "A"}
    intact = {"key0": False, "key1": True, "ledger": True}
    destroyed = {"key0": True, "key1": False, "ledger": False}
    oa = {"known_entities": ["A", "B", "ARCHIVE", "ENTRANCE", "key0", "ledger", "payment", "toolB"],
          "known_facts": ["key0_destroyed", "archive_closed", "ledger_in_archive", "payment_held_by_A", "toolB_held_by_A"]}
    ob = {"known_entities": ["A", "B", "ARCHIVE", "ENTRANCE", "key0", "key1", "ledger", "toolB"],
          "known_facts": ["key0_destroyed", "key1_held_by_B", "archive_closed", "ledger_in_archive", "toolB_held_by_A"]}
    if case_id == "E0-N02":
        holders["key1"] = None
        intact["key1"] = False
        destroyed["key1"] = True
        ob["known_facts"] = [fact for fact in ob["known_facts"] if fact != "key1_held_by_B"]
        ob["known_facts"].append("key1_destroyed")
    if case_id == "E0-H02":
        holders["ledger"] = "A"
        oa["known_facts"] = [fact for fact in oa["known_facts"] if fact != "ledger_in_archive"]
        ob["known_facts"] = [fact for fact in ob["known_facts"] if fact != "ledger_in_archive"]
        oa["known_facts"].append("ledger_held_by_A")
        ob["known_facts"].append("ledger_held_by_A")
    checkpoint = {
        "fixture_id": case_id,
        "schema_version": "e0-checkpoint-v0",
        "protocol_version": "E0-KeyLedger-v0",
        "domain": {"entities": list(ENTITY_IDS), "producer_version": PRODUCER_VERSION},
        "config_pins": {"deadline": deadline, "reply": reply_pin, "unlock_duration": unlock_duration},
        "clock": {"now": 2},
        "W": {
            "t": 2, "locations": {"A": "ENTRANCE", "B": "ENTRANCE"},
            "holders": holders,
            "beneficial_owners": {"key0": "PLAYER", "key1": "B", "ledger": "ARCHIVE", "payment": "A", "toolB": "B"},
            "intact": intact, "destroyed": destroyed, "archive_open": False,
            "offer_session": {"status": "NONE", "offer_id": None, "terms": None, "reply_time": None},
            "action_used_bits": {"offer_loan": False, "reply": False, "accept_loan": False,
                                 "return_tool": False, "unlock": False, "take_ledger": False},
            "running_action": None, "reservations": [],
        },
        "O": {"A": oa, "B": ob},
        "action_history": [], "minute_history": [], "outcome_history": [], "events": [], "receipts": [],
        "seals": [], "monitor": {"status": "PENDING", "witness_event_id": None,
                                  "coverage_complete_through": 2, "reason": "NO_WITNESS"},
        "next_ids": {"action": 1, "event": 1, "sequence": 1, "receipt": 1},
    }
    # The destroy of key0 is already committed input history before t=2.
    initial_event = {"event_id": "event-000000", "event_type": "key_destroyed", "time": 1, "sequence": 0,
                                 "producer_version": PRODUCER_VERSION,
                                    "typed_args": {"event": "key_destroyed", "actor": "PLAYER", "item": "key0"}}
    checkpoint["events"].append(initial_event)
    checkpoint["receipts"].append({"receipt_id": "receipt-000000", "action_id": "action-000000",
                                    "producer_version": PRODUCER_VERSION, "intent": {"operator": "destroy_key", "actor": "PLAYER", "args": {"item": "key0"}},
                                    "accepted": True, "start_time": 0, "end_time": 1,
                                    "status": "SUCCESS", "outcome": "DESTROYED", "event_ids": ["event-000000"],
                                    "event_payloads": [initial_event],
                                    "delta_w": {"destroyed.key0": [False, True], "intact.key0": [True, False]},
                                    "delta_o": {"A": {"known_entities": {"added": [], "removed": []},
                                                       "known_facts": {"added": ["key0_destroyed"], "removed": []}},
                                                "B": {"known_entities": {"added": [], "removed": []},
                                                       "known_facts": {"added": ["key0_destroyed"], "removed": []}}}})
    checkpoint["action_history"].append({"action_id": "action-000000", "receipt_id": "receipt-000000",
        "time": 0, "intent": {"operator": "destroy_key", "actor": "PLAYER", "args": {"item": "key0"}},
        "status": "SUCCESS"})
    checkpoint["outcome_history"].append({"receipt_id": "receipt-000000", "time": 1,
        "outcome": "DESTROYED", "event_ids": ["event-000000"]})
    sequence_frontier = 0
    if case_id == "E0-N02":
        key1_event = {"event_id": "event-000001", "event_type": "key_destroyed", "time": 1, "sequence": 1,
                      "producer_version": PRODUCER_VERSION,
                      "typed_args": {"event": "key_destroyed", "actor": "PLAYER", "item": "key1"}}
        checkpoint["events"].append(key1_event)
        checkpoint["receipts"].append({"receipt_id": "receipt-000001", "action_id": "action-000001",
            "producer_version": PRODUCER_VERSION,
            "intent": {"operator": "destroy_key", "actor": "PLAYER", "args": {"item": "key1"}},
            "accepted": True, "start_time": 0, "end_time": 1, "status": "SUCCESS",
            "outcome": "DESTROYED", "event_ids": ["event-000001"], "event_payloads": [key1_event],
            "delta_w": {"holders.key1": ["B", None], "destroyed.key1": [False, True], "intact.key1": [True, False]},
            "delta_o": {"A": {"known_entities": {"added": [], "removed": []},
                               "known_facts": {"added": [], "removed": []}},
                        "B": {"known_entities": {"added": [], "removed": []},
                               "known_facts": {"added": ["key1_destroyed"], "removed": ["key1_held_by_B"]}}}})
        checkpoint["action_history"].append({"action_id": "action-000001", "receipt_id": "receipt-000001",
            "time": 0, "intent": {"operator": "destroy_key", "actor": "PLAYER", "args": {"item": "key1"}},
            "status": "SUCCESS"})
        checkpoint["outcome_history"].append({"receipt_id": "receipt-000001", "time": 1,
            "outcome": "DESTROYED", "event_ids": ["event-000001"]})
        checkpoint["next_ids"].update({"action": 2, "event": 2, "sequence": 2, "receipt": 2})
        sequence_frontier = 1
    checkpoint["seals"].append({"sealed_through": 1, "producer_version": PRODUCER_VERSION,
                                "sequence_frontier": sequence_frontier})
    checkpoint["seals"].append({"sealed_through": 2, "producer_version": PRODUCER_VERSION,
                                "sequence_frontier": sequence_frontier})
    if case_id == "E0-B03":
        # Frozen t=5 checkpoint is obtained by three real idle/no-control boundaries.
        from .executor import Executor, intent
        runner = Executor(checkpoint)
        for _ in range(3):
            runner.execute(intent("idle"))
        checkpoint = runner.checkpoint()
    return deepcopy(checkpoint)
