"""Live-server fixture for the temporary Evennia command bridge.

Import and call ``run(me)`` from Evennia's in-game ``@py`` context. This must
run inside the live server process so object caches, command handlers, and the
database all refer to the same Evennia world state.
"""

import json
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(Path(__file__).resolve().parent))


def run(admin):
    """Create isolated plain Character/Room fixtures and execute real commands."""
    from evennia.objects.models import ObjectDB
    from evennia.utils.dbserialize import deserialize
    from evennia.utils.create import create_object
    from typeclasses.characters import Character
    from typeclasses.rooms import Room
    from evennia_bridge import install_test_commands

    run_id = uuid.uuid4().hex[:10]
    room = create_object(Room, key=f"Ensemble Bridge Fixture {run_id}")
    away = create_object(Room, key=f"Ensemble Bridge Away {run_id}")
    hero = create_object(Character, key=f"Bridge Hero {run_id}", location=room)
    love = create_object(Character, key=f"Bridge Love {run_id}", location=room)
    hero.attributes.add("ensemble_character_id", "hero", category="ensemble_bridge")
    love.attributes.add("ensemble_character_id", "love", category="ensemble_bridge")
    install_test_commands(hero)

    records = []

    def command(cmd):
        hero.execute_cmd(cmd)
        result = hero.ndb.ensemble_bridge_last
        return {"command": cmd, "result": result}

    propose_cmd = f"ensemble-propose #{love.id}"
    stale_proposal = command(propose_cmd)["result"]
    assert stale_proposal["ok"], stale_proposal
    before_notes = len(love.contents)
    assert love.move_to(away, quiet=True), "fixture target move for stale-location rejection failed"
    stale_cmd = f"ensemble-settle {stale_proposal['proposalId']}"
    stale_result = command(stale_cmd)["result"]
    assert not stale_result["ok"] and "left the proposal room" in stale_result["error"], stale_result
    assert stale_result["receiptCreated"] is False
    assert len(love.contents) == before_notes
    records.append({
        "case": "stale-location-world-rejection",
        "proposal": {"command": propose_cmd, "result": stale_proposal},
        "targetMovedTo": away.dbref,
        "settlement": {"command": stale_cmd, "result": stale_result},
        "noteCountBeforeAfter": [before_notes, len(love.contents)],
    })

    assert love.move_to(room, quiet=True), "restore target to fixture room failed"
    proposal_record = command(propose_cmd)
    proposal = proposal_record["result"]
    assert proposal["ok"], proposal
    settle_cmd = f"ensemble-settle {proposal['proposalId']}"
    pending_snapshot = dict(install_test_commands.__globals__["_pending"][proposal["proposalId"]])
    success_record = command(settle_cmd)
    success = success_record["result"]
    assert success["ok"], success
    receipt = success["settlementReceiptId"]
    note = ObjectDB.objects.get(id=int(receipt.lstrip("#")))
    assert note.location.id == love.id
    assert note.attributes.get("bridge_event_id", category="ensemble_bridge") == success["eventId"]
    records.append({
        "case": "real-note-delivery-then-Ensemble-commit",
        "proposal": proposal_record, "settlement": success_record,
        "actor": {"dbref": hero.dbref, "roleAttribute": "hero", "location": room.dbref},
        "target": {"dbref": love.dbref, "roleAttribute": "love", "location": room.dbref},
        "receipt": {"dbref": note.dbref, "location": note.location.dbref, "key": note.key},
        "sourceEventLedger": deserialize(hero.attributes.get("ensemble_bridge_events", category="ensemble_bridge", default=[])),
    })

    count_after_success = len(love.contents)
    duplicate_record = command(settle_cmd)
    duplicate = duplicate_record["result"]
    assert duplicate["ok"] and duplicate["duplicate"] is True, duplicate
    assert len(love.contents) == count_after_success
    records.append({
        "case": "duplicate-feedback-deduped",
        "settlement": duplicate_record,
        "noteCountBeforeAfter": [count_after_success, len(love.contents)],
    })

    bridge_state = install_test_commands.__globals__
    cached_success = bridge_state["_completed"].pop(proposal["proposalId"])
    bridge_state["_pending"][proposal["proposalId"]] = pending_snapshot
    cachegap_record = command(settle_cmd)
    cachegap = cachegap_record["result"]
    assert cachegap["ok"] and cachegap["settlementReceiptId"] == receipt, cachegap
    assert cachegap["ensemble"]["trace"]["doActionCalled"] is False, cachegap
    assert len(love.contents) == count_after_success
    assert bridge_state["_completed"][proposal["proposalId"]]["settlementReceiptId"] == receipt
    records.append({
        "case": "commit-succeeded-bridge-cache-gap-recovery",
        "settlement": cachegap_record,
        "cachedResultWasEvicted": bool(cached_success),
        "noteCountBeforeAfter": [count_after_success, len(love.contents)],
        "reusedReceipt": receipt,
    })

    log = {
        "status": "PASS", "execution": "called from in-game @py on the running nativep1 server",
        "fixtureTypeclasses": ["typeclasses.rooms.Room", "typeclasses.characters.Character"],
        "officialAiFsmCalled": False,
        "fixture": {"room": room.dbref, "awayRoom": away.dbref, "actor": hero.dbref, "target": love.dbref},
        "commands": records,
        "meaning": {
            "sourceEvent": "the actual ensemble-propose Evennia command request is appended to an Evennia Attribute ledger",
            "projection": "only stored hero/love role metadata is projected; room location is used for validation and does not imply emotion",
            "worldValidation": "same-room validation gates physical note delivery; stale location yields no receipt and no Ensemble commit",
            "socialResponse": "writeLoveNoteReject is the example narrative rejection after valid note delivery, distinct from world validation rejection",
            "ownership": "Evennia owns room membership and the delivered note object; Ensemble owns only social-record effects",
        },
    }
    admin.attributes.add("ensemble_bridge_rawlog", log, category="ensemble_bridge")
    return log


def run_json(admin):
    from evennia.utils.dbserialize import deserialize
    return json.dumps(deserialize(run(admin)), indent=2, ensure_ascii=False)
