"""Narrow Ensemble-to-Evennia social adapter for the P3-B native loop.

This module is import-safe outside Evennia.  It does not load or modify the
pinned Ensemble source; proposals go through the existing JSONL runner.
"""

from __future__ import annotations

import hashlib
import random
import secrets
from typing import Any, Mapping


SUPPORTED_ACTIONS = {"writeLoveNoteReject", "kissFail"}


def _get(value: Any, *keys: str, default: Any = None) -> Any:
    for key in keys:
        if isinstance(value, Mapping) and key in value:
            return value[key]
        if hasattr(value, key):
            return getattr(value, key)
        attrs = getattr(value, "attributes", None)
        if attrs is not None:
            for category in ("ensemble_bridge", "native_social"):
                try:
                    found = attrs.get(key, category=category, default=None)
                except (AttributeError, TypeError):
                    found = None
                if found is not None:
                    return found
    return default


def _native_client(shared_state: Mapping[str, Any]):
    client = shared_state.get("ensemble_client")
    if client is not None:
        return client
    # The bridge imports Evennia only when a live proposal is requested.  This
    # keeps offline unit tests and the native loop's module discovery import-safe.
    try:
        from evennia_bridge import _client
    except ImportError:
        try:
            from tools.native_platform_v0.bridge.evennia_bridge import _client
        except ImportError as err:
            raise RuntimeError("native Ensemble runner is unavailable") from err
    return _client()


def _seeded_index(seed: Any, event_id: str, count: int) -> int:
    material = f"{seed!r}|{event_id}".encode("utf-8")
    stable_seed = int.from_bytes(hashlib.sha256(material).digest()[:8], "big")
    return random.Random(stable_seed).randrange(count)


def propose_social(actor, local_view, shared_state, seed):
    """Ask native Ensemble for candidates and select a native-ranked terminal action.

    Expected local-view keys: `target` (or `visible_target`), `target_visible`,
    `room_id`, and optionally `source_event_id`.
    Actor and target expose `ensemble_character_id` (or `native_role`) with
    values from the pinned example cast.  The runner applies supplied facts to
    its persistent shared record at proposal time, so this adapter always sends
    an empty fact batch.  Actor-local observations never enter that record.
    """
    if not isinstance(local_view, Mapping) or not isinstance(shared_state, Mapping):
        return {"ok": False, "status": "UNAVAILABLE", "error": "local_view and shared_state must be mappings"}
    target = local_view.get("target", local_view.get("visible_target"))
    if target is None or local_view.get("target_visible", True) is not True:
        return {"ok": False, "status": "NO_CANDIDATE", "error": "no currently visible social target"}
    actor_role = _get(actor, "ensemble_character_id", "native_role")
    target_role = _get(target, "ensemble_character_id", "native_role")
    if not actor_role or not target_role or actor_role == target_role:
        return {"ok": False, "status": "NO_CANDIDATE", "error": "actor and visible target need distinct pinned-cast roles"}
    actor_id = _get(actor, "id", "dbref", default=str(actor_role))
    target_id = _get(target, "id", "dbref", default=str(target_role))
    room_id = local_view.get("room_id", _get(actor, "location_id"))
    if room_id is None:
        return {"ok": False, "status": "NO_CANDIDATE", "error": "local observation has no room identity"}
    event_id = local_view.get("source_event_id") or f"native-social:{actor_id}:{target_id}:{secrets.token_urlsafe(12)}"
    try:
        client = _native_client(shared_state)
        result = client.request({
            "op": "propose", "eventId": event_id,
            "actor": str(actor_role), "responder": str(target_role),
            "facts": [],
        })
    except Exception as err:
        return {"ok": False, "status": "UNAVAILABLE", "error": str(err), "event_id": event_id}
    if not result.get("ok"):
        return {"ok": False, "status": "NO_CANDIDATE", "error": result.get("error", "native proposal rejected"), "event_id": event_id}

    actions = list(result.get("actions", []))
    if not actions:
        return {"ok": False, "status": "NO_CANDIDATE", "error": "native proposal has no supported Evennia action", "event_id": event_id,
                "native_action_names": []}
    try:
        weights = [float(a["weight"]) for a in actions]
    except (KeyError, TypeError, ValueError):
        return {"ok": False, "status": "NO_CANDIDATE", "error": "native candidate is missing a numeric weight", "event_id": event_id}
    best_weight = max(weights)
    native_winning_tie = [a for a, weight in zip(actions, weights) if weight == best_weight]
    executable_winners = [a for a in native_winning_tie if a.get("name") in SUPPORTED_ACTIONS]
    selection = {
        "rule": "max_native_weight_then_seeded_tie_among_supported_winners",
        "native_candidate_names": [a.get("name") for a in actions],
        "native_candidate_weights": {a.get("name"): float(a["weight"]) for a in actions},
        "native_winning_tie_names": [a.get("name") for a in native_winning_tie],
        "supported_winning_tie_names": [a.get("name") for a in executable_winners],
        "unsupported_native_winners": [a.get("name") for a in native_winning_tie if a.get("name") not in SUPPORTED_ACTIONS],
        "seed": seed,
    }
    if not executable_winners:
        return {"ok": False, "status": "UNSUPPORTED_NATIVE_ACTION",
                "error": "highest-weight native action is not executable by this Evennia adapter",
                "event_id": event_id, "native_weight": best_weight, "selection": selection}
    index = _seeded_index(seed, event_id, len(executable_winners))
    chosen = executable_winners[index]
    selection = {
        **selection,
        "selected_index": index,
        "selected_name": chosen["name"],
    }
    return {
        "ok": True, "status": "PROPOSED", "event_id": event_id,
        "proposal_id": result["proposalId"], "record_revision": result.get("recordRevision"),
        "actor_id": actor_id, "target_id": target_id, "actor_role": actor_role,
        "target_role": target_role, "observed_room_id": room_id,
        "action_name": chosen["name"], "native_weight": float(chosen["weight"]),
        "native_salience": chosen.get("salience"), "native_action": chosen,
        "native_volitions": result.get("volitions", []), "selection": selection,
        "observed_evidence": {
            "target_visible": True,
            "room_id": room_id,
            "actor_local_facts_projected_to_shared_record": 0,
            "native_volition_record_scope": "shared source history plus previously committed Ensemble effects",
            "global_shared_record_copied_into_actor_O": False,
            "actor_private_observation_injected_into_Ensemble": False,
        },
        "source_event": {"event_id": event_id, "kind": "native-social-proposal", "actor_id": actor_id,
                         "target_id": target_id, "room_id": room_id},
    }


def _live_room_id(obj):
    location = _get(obj, "location")
    if location is not None:
        return _get(location, "id", "dbref")
    return _get(obj, "location_id", "room_id")


def _event_exists(actor, event_id):
    attrs = _get(actor, "attributes")
    if attrs is None:
        return False
    try:
        events = attrs.get("native_social_events", category="native_social", default=[])
        return any(event.get("event_id") == event_id for event in events)
    except (AttributeError, TypeError):
        return False


def _record_event(actor, target, event):
    attrs = _get(actor, "attributes")
    if attrs is None:
        # Injectable host callback for deterministic tests or non-Evennia hosts.
        recorder = _get(actor, "record_social_event")
        if callable(recorder):
            recorder(event)
            return
        raise RuntimeError("Evennia event receipt storage is unavailable")
    current = list(attrs.get("native_social_events", category="native_social", default=[]))
    current.append(event)
    attrs.add("native_social_events", current, category="native_social")
    target_attrs = _get(target, "attributes")
    if target_attrs is not None:
        received = list(target_attrs.get("native_social_events", category="native_social", default=[]))
        received.append(dict(event))
        target_attrs.add("native_social_events", received, category="native_social")


def _create_note(actor, target, proposal):
    creator = _get(actor, "create_social_note")
    if callable(creator):
        return creator(target, proposal)
    from evennia.objects.objects import DefaultObject
    from evennia.utils.create import create_object
    note = create_object(
        DefaultObject, key=f"Love note for {_get(target, 'key', default='recipient')}",
        location=_get(actor, "location"),
        attributes=[("native_social_event_id", proposal["event_id"], "native_social"),
                    ("native_social_action", proposal["action_name"], "native_social")],
    )
    if not note.move_to(target, quiet=True) or _get(_get(note, "location"), "id", "dbref") != _get(target, "id", "dbref"):
        note.delete()
        return None
    return note


def _msg(obj, text):
    send = _get(obj, "msg")
    if callable(send):
        send(text)


def execute_social(client, proposal, current_view):
    """Validate live visibility/location, settle one Evennia effect, then commit Ensemble.

    `current_view` supplies live `actor`, `target`, and optionally `target_visible`.
    A stale proposal fails before any receipt, message, item creation, or Ensemble commit.
    """
    if not proposal or proposal.get("status") != "PROPOSED" or proposal.get("action_name") not in SUPPORTED_ACTIONS:
        return {"ok": False, "status": "INVALID_PROPOSAL", "receipt_created": False, "ensemble_commit_called": False}
    if not isinstance(current_view, Mapping):
        return {"ok": False, "status": "WORLD_VALIDATION_REJECTED", "error": "current_view must provide live actor and target", "receipt_created": False, "ensemble_commit_called": False}
    actor = current_view.get("actor")
    target = current_view.get("target")
    if actor is None or target is None:
        return {"ok": False, "status": "WORLD_VALIDATION_REJECTED", "error": "actor or target no longer exists", "receipt_created": False, "ensemble_commit_called": False}
    if current_view.get("target_visible", True) is not True:
        return {"ok": False, "status": "WORLD_VALIDATION_REJECTED", "error": "target is no longer visible", "receipt_created": False, "ensemble_commit_called": False}
    live_actor_room, live_target_room = _live_room_id(actor), _live_room_id(target)
    expected_room = proposal.get("observed_room_id")
    if live_actor_room is None or live_target_room is None or live_actor_room != live_target_room or live_actor_room != expected_room:
        return {"ok": False, "status": "WORLD_VALIDATION_REJECTED", "error": "actor or target left the observed room", "receipt_created": False, "ensemble_commit_called": False}
    actor_id = _get(actor, "id", "dbref", default=str(_get(actor, "ensemble_character_id", "native_role")))
    target_id = _get(target, "id", "dbref", default=str(_get(target, "ensemble_character_id", "native_role")))
    if str(actor_id) != str(proposal.get("actor_id")) or str(target_id) != str(proposal.get("target_id")):
        return {"ok": False, "status": "WORLD_VALIDATION_REJECTED", "error": "live actor/target identity differs from proposal", "receipt_created": False, "ensemble_commit_called": False}
    if _event_exists(actor, proposal["event_id"]):
        return {"ok": False, "status": "DUPLICATE_EVENT", "error": "Evennia already has a receipt for this event", "receipt_created": True, "ensemble_commit_called": False}

    auth = client.request({"op": "authorize", "proposalId": proposal["proposal_id"], "eventId": proposal["event_id"], "actionName": proposal["action_name"]})
    if not auth.get("ok"):
        return {"ok": False, "status": "WORLD_VALIDATION_REJECTED", "error": auth.get("error"), "receipt_created": False, "ensemble_commit_called": False}
    note = None
    if proposal["action_name"] == "writeLoveNoteReject":
        note = _create_note(actor, target, proposal)
        if note is None:
            return {"ok": False, "status": "WORLD_VALIDATION_REJECTED", "error": "Evennia rejected note delivery", "receipt_created": False, "ensemble_commit_called": False}
    event = {
        "event_id": proposal["event_id"], "proposal_id": proposal["proposal_id"],
        "actor_id": actor_id, "target_id": target_id, "room_id": live_actor_room,
        "action_name": proposal["action_name"], "outcome": "rejected",
        "native_weight": proposal["native_weight"],
        "world_effect": "note delivered to target inventory" if note is not None else "rejected attempt recorded; no physical transfer",
        "receipt_id": _get(note, "dbref", default=proposal["event_id"]),
    }
    try:
        _record_event(actor, target, event)
    except Exception as err:
        return {"ok": False, "status": "WORLD_SETTLEMENT_PENDING", "error": str(err), "receipt_created": note is not None, "ensemble_commit_called": False}
    response_text = proposal["native_action"].get("failMessage", proposal["native_action"].get("displayName", "The action was rejected."))
    _msg(actor, response_text)
    _msg(target, response_text)

    receipt_id = str(event["receipt_id"])
    commit = {
        "op": "commit", "proposalId": proposal["proposal_id"], "eventId": proposal["event_id"],
        "settlementStatus": "settled", "settledActionName": proposal["action_name"],
        "actionName": proposal["action_name"], "settlementReceiptId": receipt_id,
    }
    commit["settlementProof"] = client.settlement_proof(proposal["proposal_id"], proposal["event_id"], proposal["action_name"], receipt_id)
    committed = client.request(commit)
    if not committed.get("ok"):
        return {"ok": False, "status": "SOCIAL_COMMIT_PENDING", "error": committed.get("error"),
                "receipt_created": True, "receipt_id": receipt_id, "ensemble_commit_called": True,
                "world_settlement_preserved": True}
    return {"ok": True, "status": "SETTLED", "event_id": proposal["event_id"],
            "proposal_id": proposal["proposal_id"], "action_name": proposal["action_name"],
            "native_weight": proposal["native_weight"], "receipt_id": receipt_id,
            "world_effect": event["world_effect"], "social_record": committed.get("socialRecord"),
            "ensemble": committed}
