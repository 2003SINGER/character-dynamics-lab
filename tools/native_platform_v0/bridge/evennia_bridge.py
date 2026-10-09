"""Narrow Evennia command adapter for the pinned Lovers and Rivals Ensemble probe.

This is a separate test command. It does not import or call EvAdventure AIHandler.
"""

from __future__ import annotations

import json
import hashlib
import hmac
import os
import secrets
import shutil
import subprocess
import threading
from pathlib import Path

from evennia.commands.command import Command
from evennia.commands.cmdset import CmdSet
from evennia.objects.objects import DefaultObject
from evennia.utils.create import create_object
from evennia.objects.models import ObjectDB

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNNER = PROJECT_ROOT / "tools/native_platform_v0/ensemble/runner.mjs"
NODE = os.environ.get("ENSEMBLE_NODE") or shutil.which("node") or "/opt/homebrew/bin/node"
_lock = threading.RLock()
_engine = None
_pending = {}
_completed = {}


def _append_source_event(actor, event):
    events = list(actor.attributes.get("ensemble_bridge_events", category="ensemble_bridge", default=[]))
    events.append(event)
    actor.attributes.add("ensemble_bridge_events", events, category="ensemble_bridge")


def _write_receipt_journal(actor, entry):
    entries = list(actor.attributes.get("ensemble_bridge_receipts", category="ensemble_bridge", default=[]))
    entries = [old for old in entries if old.get("proposalId") != entry["proposalId"]]
    entries.append(entry)
    actor.attributes.add("ensemble_bridge_receipts", entries, category="ensemble_bridge")


class EnsembleProcess:
    """One persistent JSONL Node engine process for this Evennia server process."""

    def __init__(self):
        self.secret = secrets.token_hex(32)
        env = os.environ.copy()
        env["ENSEMBLE_BRIDGE_SECRET"] = self.secret
        self.proc = subprocess.Popen(
            [NODE, str(RUNNER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, bufsize=1, env=env,
        )

    def request(self, payload):
        line = json.dumps(payload, separators=(",", ":"))
        self.proc.stdin.write(line + "\n")
        self.proc.stdin.flush()
        response = self.proc.stdout.readline()
        if not response:
            error = self.proc.stderr.read()
            raise RuntimeError(f"Ensemble runner exited before responding: {error}")
        return json.loads(response)

    def settlement_proof(self, proposal_id, event_id, action_name, receipt_id):
        signed = json.dumps([proposal_id, event_id, action_name, receipt_id], separators=(",", ":"))
        return hmac.new(self.secret.encode(), signed.encode(), hashlib.sha256).hexdigest()


def _client():
    global _engine
    if _engine is None or _engine.proc.poll() is not None:
        _engine = EnsembleProcess()
    return _engine


def _role_facts(actor, target):
    role_names = {"hero": "named hero", "love": "named love", "rival": "named rival"}
    facts = []
    for obj in (actor, target):
        role = obj.attributes.get("ensemble_character_id", category="ensemble_bridge")
        if role not in role_names:
            raise ValueError(f"{obj.key}#{obj.id} lacks an allowed ensemble_character_id role")
        facts.extend([
            {"category": "trait", "type": role_names[role], "first": role, "value": True},
            {"category": "trait", "type": "anyone", "first": role, "value": True},
        ])
        # Optional predicates remain game-object data. The Node adapter completes
        # batch prevalidation against the original schema before writes; engine writes are not transactional.
        facts.extend(obj.attributes.get("ensemble_facts", category="ensemble_bridge", default=[]))
    return facts


def _world_valid(actor, target, expected_location_id):
    live_actor = ObjectDB.objects.filter(id=actor.id).first()
    live_target = ObjectDB.objects.filter(id=target.id).first()
    return bool(
        live_actor and live_target and live_actor.location and live_target.location
        and live_actor.db_location_id == expected_location_id
        and live_target.db_location_id == expected_location_id
        and live_actor.db_location_id == live_target.db_location_id
    )


def prepare_interaction(actor, target):
    """Project real fixture-object role facts and return the original engine proposal."""
    if actor.id == target.id or not actor.location or actor.location.id != target.location.id:
        raise ValueError("world validation rejected proposal: actor and target must share a live room")
    actor_role = actor.attributes.get("ensemble_character_id", category="ensemble_bridge")
    target_role = target.attributes.get("ensemble_character_id", category="ensemble_bridge")
    if (actor_role, target_role) != ("hero", "love"):
        raise ValueError("this bounded bridge probe accepts the example hero → love cast binding only")
    event_id = f"evennia:{actor.id}:{target.id}:{secrets.token_urlsafe(12)}"
    room_id = actor.location.id
    source_event = {
        "eventId": event_id, "kind": "ensemble-propose-command",
        "actorDbref": actor.dbref, "targetDbref": target.dbref,
        "actorLocationDbref": actor.location.dbref, "targetLocationDbref": target.location.dbref,
        "projectedRoles": [actor_role, target_role],
        "projectionBoundary": "command plus stored object role metadata only; location does not imply emotion",
    }
    _append_source_event(actor, source_event)
    payload = {
        "op": "propose", "eventId": event_id, "actor": actor_role, "responder": target_role,
        "facts": _role_facts(actor, target),
    }
    with _lock:
        result = _client().request(payload)
    if not result.get("ok"):
        raise ValueError(f"Ensemble proposal rejected: {result.get('error')}")
    action = next((candidate for candidate in result["actions"] if candidate["name"] == "writeLoveNoteReject"), None)
    if action is None:
        raise ValueError("Ensemble did not propose the bounded writeLoveNoteReject interaction")
    proposal_id = result["proposalId"]
    _pending[proposal_id] = {
        "actor": actor, "target": target, "actor_id": actor.id, "target_id": target.id,
        "event_id": event_id, "room_id": room_id, "action_name": action["name"],
        "proposal": result, "source_event": source_event,
    }
    return result


def _commit_existing_receipt(proposal_id, pending, note):
    proposer, target = pending["actor"], pending["target"]
    receipt_id = note.dbref
    _write_receipt_journal(proposer, {
        "proposalId": proposal_id, "eventId": pending["event_id"],
        "receiptId": receipt_id, "phase": "world_settled_social_commit_pending",
    })
    authorized = _client().request({
        "op": "authorize", "proposalId": proposal_id, "eventId": pending["event_id"],
        "actionName": pending["action_name"],
    })
    if not authorized.get("ok"):
        return {
            "ok": False, "status": "SOCIAL_COMMIT_PENDING", "error": authorized.get("error"),
            "proposalId": proposal_id, "settlementReceiptId": receipt_id,
            "noteDbref": note.dbref, "worldSettlementPreserved": True,
            "retryWillReuseReceipt": True,
        }
    client = _client()
    commit_payload = {
        "op": "commit", "proposalId": proposal_id, "eventId": pending["event_id"],
        "settlementStatus": "settled", "settledActionName": pending["action_name"],
        "actionName": pending["action_name"], "settlementReceiptId": receipt_id,
    }
    commit_payload["settlementProof"] = client.settlement_proof(
        proposal_id, pending["event_id"], pending["action_name"], receipt_id,
    )
    committed = client.request(commit_payload)
    if not committed.get("ok"):
        return {
            "ok": False, "status": "SOCIAL_COMMIT_PENDING", "error": committed.get("error"),
            "proposalId": proposal_id, "settlementReceiptId": receipt_id,
            "noteDbref": note.dbref, "worldSettlementPreserved": True,
            "retryWillReuseReceipt": True,
        }
    _write_receipt_journal(proposer, {
        "proposalId": proposal_id, "eventId": pending["event_id"],
        "receiptId": receipt_id, "phase": "committed",
    })
    proposer.msg(f"The note was delivered to {target.key}. The example's social response is rejection.")
    target.msg(f"You receive a love note from {proposer.key}; the example's social response is rejection.")
    result = {
        "ok": True, "proposalId": proposal_id, "eventId": pending["event_id"],
        "actorId": proposer.id, "settlementReceiptId": receipt_id, "noteDbref": note.dbref,
        "socialOutcome": "writeLoveNoteReject", "worldEffect": "note moved into target inventory",
        "ensemble": committed,
    }
    _completed[proposal_id] = result
    _pending.pop(proposal_id, None)
    return result


def settle_interaction(proposal_id, caller=None):
    """Validate proposer identity and live room before one actual delivery."""
    with _lock:
        if proposal_id in _completed:
            if caller and _completed[proposal_id]["actorId"] != caller.id:
                return {"ok": False, "error": "only the proposing actor may settle this proposal"}
            return {
                "ok": True, "duplicate": True, "cachedResult": _completed[proposal_id],
                "currentOperation": {"noteCreated": False, "ensembleCommitCalled": False},
            }
        pending = _pending.get(proposal_id)
        if not pending:
            return {"ok": False, "error": "unknown or already expired proposalId"}
        proposer, target = pending["actor"], pending["target"]
        if caller and pending["actor_id"] != caller.id:
            return {"ok": False, "error": "only the proposing actor may settle this proposal"}
        existing = next((obj for obj in target.contents if obj.attributes.get("bridge_proposal_id", category="ensemble_bridge") == proposal_id), None)
        if existing:
            return _commit_existing_receipt(proposal_id, pending, existing)
        if not _world_valid(proposer, target, pending["room_id"]):
            return {"ok": False, "error": "world validation rejected settlement: actor or target left the proposal room", "proposalId": proposal_id, "receiptCreated": False, "ensembleCommitCalled": False}
        authorized = _client().request({
            "op": "authorize", "proposalId": proposal_id, "eventId": pending["event_id"],
            "actionName": pending["action_name"],
        })
        if not authorized.get("ok"):
            return {"ok": False, "error": authorized.get("error"), "proposalId": proposal_id, "receiptCreated": False, "ensembleCommitCalled": False}

        note = create_object(
            DefaultObject, key=f"Love note for {target.key}", location=proposer.location,
            attributes=[
                ("bridge_proposal_id", proposal_id, "ensemble_bridge"),
                ("bridge_event_id", pending["event_id"], "ensemble_bridge"),
                ("bridge_from_dbref", proposer.dbref, "ensemble_bridge"),
                ("bridge_to_dbref", target.dbref, "ensemble_bridge"),
                ("world_effect", "letter physically delivered to target inventory", "ensemble_bridge"),
            ],
        )
        if not note.move_to(target, quiet=True) or not note.location or note.location.id != target.id:
            temp_dbref = note.dbref
            note.delete()
            _write_receipt_journal(proposer, {"proposalId": proposal_id, "eventId": pending["event_id"], "phase": "world_transfer_failed", "temporaryNoteDbref": temp_dbref})
            return {"ok": False, "status": "WORLD_VALIDATION_REJECTED", "error": "world rejected the item transfer", "proposalId": proposal_id, "temporaryNoteCreated": temp_dbref, "temporaryNoteDeleted": True, "physicalCreationWasAttempted": True, "ensembleCommitCalled": False}
        return _commit_existing_receipt(proposal_id, pending, note)


class EnsembleBridgeTestCmdSet(CmdSet):
    """Temporary command set installed only on a dedicated bridge fixture actor."""

    key = "EnsembleBridgeTestCmdSet"
    priority = 110
    mergetype = "Union"

    def at_cmdset_creation(self):
        self.add(CmdEnsemblePropose())
        self.add(CmdEnsembleSettle())


class CmdEnsemblePropose(Command):
    """Temporary test command: ask Ensemble for a social interaction proposal."""

    key = "ensemble-propose"
    locks = "cmd:all()"
    help_category = "Native platform probe"

    def func(self):
        target = self.caller.search(self.args.strip(), global_search=True, use_dbref=True) if self.args.strip() else None
        if not target:
            self.caller.ndb.ensemble_bridge_last = {"ok": False, "error": "target not found"}
            self.caller.msg("Target not found.")
            return
        try:
            result = prepare_interaction(self.caller, target)
        except Exception as err:
            result = {"ok": False, "error": str(err)}
        self.caller.ndb.ensemble_bridge_last = result
        self.caller.msg(json.dumps(result, ensure_ascii=False))


class CmdEnsembleSettle(Command):
    """Temporary test command: settle a proposal after current-world validation."""

    key = "ensemble-settle"
    locks = "cmd:all()"
    help_category = "Native platform probe"

    def func(self):
        result = settle_interaction(self.args.strip(), caller=self.caller)
        self.caller.ndb.ensemble_bridge_last = result
        self.caller.msg(json.dumps(result, ensure_ascii=False))


def install_test_commands(actor):
    """Attach only these two probe commands temporarily to a separate fixture actor."""
    actor.cmdset.add(EnsembleBridgeTestCmdSet(), persistent=False)
