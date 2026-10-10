"""P4's two-callback, physical-note social interaction adapter.

The pinned Ensemble engine remains the decision source. Evennia owns the note,
its location/response receipt, and settlement; this module never exposes B's
decision to A and never writes actor-local observations into Ensemble facts.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import select
import shutil
import subprocess
import threading
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNNER = PROJECT_ROOT / "tools/native_platform_v0/ensemble/runner.mjs"
NODE = os.environ.get("ENSEMBLE_NODE") or shutil.which("node") or "/opt/homebrew/bin/node"
MAX_REQUEST_SECONDS = 5.0
P5_PRESET_ENV = "ENSEMBLE_P5_SOCIAL_PRESET"
P5_PRESETS = {
    "native_default_reject_v0": [],
    "hero_intelligence_30_v0": [{
        "category": "attribute", "type": "intelligence", "first": "hero", "value": 30,
    }],
}
_CLIENTS: dict[str, "P4EnsembleClient"] = {}
_CLIENT_LOCK = threading.RLock()
_P4_ACTIONS = {"writeLoveNoteAccept", "writeLoveNoteReject"}


class P4EnsembleClient:
    """One P4-only runner per scene, with bounded JSONL round trips and HMAC."""

    def __init__(self, timeout: float = MAX_REQUEST_SECONDS, p5_preset: str | None = None):
        if p5_preset is not None and p5_preset not in P5_PRESETS:
            raise ValueError("unsupported P5 native social preset")
        self.timeout = min(float(timeout), MAX_REQUEST_SECONDS)
        self.p5_preset = p5_preset
        self.secret = secrets.token_hex(32)
        env = os.environ.copy()
        # A P4 process must remain legacy even if the parent environment happens
        # to contain the P5-only selector.
        env.pop(P5_PRESET_ENV, None)
        if p5_preset is not None:
            env[P5_PRESET_ENV] = p5_preset
        env["ENSEMBLE_BRIDGE_SECRET"] = self.secret
        self.proc = subprocess.Popen(
            [NODE, str(RUNNER)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, bufsize=0, env=env,
        )
        self._buffer = bytearray()
        self._lock = threading.RLock()
        if p5_preset is not None:
            hello = self.request({"op": "hello"})
            if (hello.get("ok") is not True or hello.get("p5Preset") != p5_preset
                    or hello.get("initialStateApplied") is not True
                    or hello.get("initialFacts") != P5_PRESETS[p5_preset]):
                self.invalidate()
                raise RuntimeError("P5 Ensemble runner did not confirm its immutable initial preset")

    def request(self, payload):
        with self._lock:
            if self.proc.poll() is not None or self.proc.stdin is None or self.proc.stdout is None:
                raise RuntimeError("P4 native runner is unavailable")
            encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"
            self.proc.stdin.write(encoded)
            self.proc.stdin.flush()
            import time
            deadline = time.monotonic() + self.timeout
            while b"\n" not in self._buffer:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self.invalidate()
                    raise TimeoutError("P4 native runner exceeded the five-second request limit")
                ready, _, _ = select.select([self.proc.stdout], [], [], remaining)
                if not ready:
                    self.invalidate()
                    raise TimeoutError("P4 native runner exceeded the five-second request limit")
                chunk = os.read(self.proc.stdout.fileno(), 65536)
                if not chunk:
                    raise RuntimeError("P4 native runner exited before responding")
                self._buffer.extend(chunk)
                if len(self._buffer) > 4 * 1024 * 1024:
                    raise RuntimeError("P4 native response exceeded the bounded line size")
            line, _, rest = self._buffer.partition(b"\n")
            self._buffer = bytearray(rest)
            return json.loads(line.decode("utf-8"))

    def invalidate(self):
        if self.proc.poll() is None:
            self.proc.kill()

    def settlement_proof(self, proposal_id, event_id, action_name, receipt_id):
        signed = json.dumps([proposal_id, event_id, action_name, receipt_id], separators=(",", ":"))
        return hmac.new(self.secret.encode(), signed.encode(), hashlib.sha256).hexdigest()


def native_source_manifest():
    """Expose hashes of the public pinned source files, never local cache secrets."""
    root = PROJECT_ROOT / "_local_data/native_platform_v0/ensemble/examples/loversAndRivals"
    files = ["ensemble.js", *(f"data/{name}.json" for name in
              ("schema", "cast", "triggerRules", "volitionRules", "actions", "history"))]
    hashes = {}
    for name in files:
        data = (root / name).read_bytes()
        hashes[name] = hashlib.sha256(data).hexdigest()
    packed = json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()
    return {"source_root": "_local_data/native_platform_v0/ensemble/examples/loversAndRivals",
            "sha256": hashes, "source_snapshot_sha256": hashlib.sha256(packed).hexdigest(),
            "initial_history_mutated": False}


def _value(obj, key, default=None, category="native_p3"):
    return obj.attributes.get(key, category=category, default=default)


def _set(obj, key, value, category="native_p3"):
    obj.attributes.add(key, value, category=category)


def _record(actor, event):
    from tools.native_platform_v0.p3.agency import record

    record(actor, event)


def _client(scene_id, p5_preset=None):
    if p5_preset is not None and p5_preset not in P5_PRESETS:
        raise ValueError("unsupported P5 native social preset")
    with _CLIENT_LOCK:
        client = _CLIENTS.get(scene_id)
        if client is not None and client.p5_preset != p5_preset:
            raise RuntimeError("native social preset cannot change within a scene runner")
        if client is None or client.proc.poll() is not None:
            client = P4EnsembleClient(p5_preset=p5_preset)
            _CLIENTS[scene_id] = client
        return client


def _event_id(seed, role, action):
    # Physical scene IDs/database identifiers do not affect the native choice.
    return f"p4:{seed}:{role}:{action}:episode1"


def _own_delivery_settled(actor):
    item_id = _value(actor, "task_item_id")
    destination_id = _value(actor, "task_destination_id")
    return item_id is not None and destination_id is not None and any(
        row.get("kind") == "drop" and row.get("settled") is True
        and str(row.get("item_id")) == str(item_id)
        and row.get("after_item_room_id") == destination_id
        for row in _value(actor, "native_receipts", [])
    )


def _visible_target(actor):
    target_id = _value(actor, "p3_social_target_id")
    room = actor.location
    if target_id is None or room is None:
        return None
    return next((obj for obj in room.contents if obj.id == target_id and
                 obj.access(actor, "view", default=True)), None)


def _append_scene_event(actor, event_type, event_id, typed_args, *, sealed=True, receipt_id=None):
    from tools.native_platform_v0.p3.p4_world import append_event

    return append_event(actor, {"event_type": event_type, "event_id": event_id,
                                "typed_args": typed_args, "sealed": sealed,
                                "receipt_id": receipt_id})


def _request_note(actor, target, client):
    from evennia.objects.objects import DefaultObject
    from evennia.utils.create import create_object

    seed = _value(actor, "scenario_seed", 0)
    request_id = _event_id(seed, "hero", "note-request")
    request_event_id = _event_id(seed, "hero", "note-source")
    request = client.request({"op": "request_note", "requestId": request_id,
                              "eventId": request_event_id, "actor": "hero", "responder": "love"})
    if not request.get("ok") or request.get("status") != "PROPOSED":
        result = {"status": request.get("status", "UNAVAILABLE"),
                  "error": request.get("error"), "request_id": request_id,
                  "native_intents": request.get("native_intents", [])}
        _set(actor, "p4_social_status", result["status"])
        _record(actor, {"kind": "p4_social_request", "result": result})
        if request.get("status") == "NO_CANDIDATE":
            _append_scene_event(actor, "SOCIAL_REQUEST", request_event_id,
                                {"request_id": request_id, "initiator_role": "hero",
                                 "recipient_role": "love", "status": "NO_CANDIDATE",
                                 "native_intents": request.get("native_intents", [])})
            _set(actor, "p4_social_attempted", True)
        return True

    note = create_object(
        DefaultObject, key=f"Love note for {target.key}", location=actor.location,
        attributes=[("p3_scene_id", _value(actor, "scene_id"), "native_p3"),
                    ("p4_note_request_id", request_id, "native_p3"),
                    ("p4_note_source_event_id", request_event_id, "native_p3"),
                    ("p4_note_status", "written", "native_p3"),
                    ("p4_note_initiator_id", int(actor.id), "native_p3"),
                    ("p4_note_recipient_id", int(target.id), "native_p3")],
    )
    if _value(actor, "activity_profile") == "p5_story_v0":
        note.attributes.add("p5_item_alias", "note", category="native_p5")
    before_location_id = int(note.db_location_id) if note.db_location_id else None
    moved = bool(note.move_to(target, quiet=True))
    settled = moved and note.db_location_id == target.id and note in target.contents
    if not settled:
        _append_scene_event(actor, "SOCIAL_REQUEST", request_event_id,
                            {"request_id": request_id, "initiator_actor_id": int(actor.id),
                             "recipient_actor_id": int(target.id), "note_id": int(note.id),
                             "native_intent": request["native_intent"], "status": "WORLD_SETTLEMENT_PENDING"},
                            sealed=False)
        _set(actor, "p4_social_status", "WORLD_SETTLEMENT_PENDING")
        _record(actor, {"kind": "p4_social_request", "status": "WORLD_SETTLEMENT_PENDING",
                        "request_id": request_id, "note_id": int(note.id)})
        return True

    receipt_id = f"p4-note-delivery:{request_id}:{int(note.id)}"
    args = {"request_id": request_id, "initiator_role": "hero", "initiator_actor_id": int(actor.id),
            "recipient_role": "love", "recipient_actor_id": int(target.id),
            "note_id": int(note.id), "note_dbref": str(note.dbref), "note_key": str(note.key),
            "source_event_id": request_event_id,
            "native_intent": request["native_intent"],
            "physical_receipt": {"status": "settled", "receipt_id": receipt_id,
                                 "before_location_id": before_location_id,
                                 "after_location_id": int(note.db_location_id),
                                 "recipient_inventory_actor_id": int(target.id)}}
    _append_scene_event(actor, "SOCIAL_REQUEST", request_event_id, args,
                        sealed=True, receipt_id=receipt_id)
    _set(actor, "p4_social_attempted", True)
    _set(actor, "p4_social_status", "NOTE_DELIVERED")
    _record(actor, {"kind": "p4_social_request", "status": "NOTE_DELIVERED",
                    "request_id": request_id, "note_id": int(note.id),
                    "native_intent": request["native_intent"],
                    "target_local_and_visible": True})
    return True


def _respond_to_note(actor, note, client):
    from tools.native_platform_v0.p3.p4_world import clock_for_actor

    request_id = _value(note, "p4_note_request_id")
    if not request_id or _value(note, "p4_note_status") != "written":
        return False
    if _value(note, "p4_note_recipient_id") != actor.id or note not in actor.contents:
        return False
    seed = _value(actor, "scenario_seed", 0)
    response_event_id = _event_id(seed, "love", "note-response")
    try:
        response = client.request({"op": "respond_note", "requestId": request_id,
                                   "eventId": response_event_id,
                                   "actor": "hero", "responder": "love"})
    except TimeoutError as err:
        _set(note, "p4_note_status", "response_unavailable")
        result = {"status": "UNAVAILABLE", "decision": "unavailable", "request_id": request_id,
                  "error": str(err)}
        _append_scene_event(actor, "SOCIAL_RESPONSE", response_event_id, result,
                            sealed=result["status"] == "NO_CANDIDATE")
        _set(actor, "p4_social_status", "UNAVAILABLE")
        _record(actor, {"kind": "p4_social_response", "result": result})
        return True
    if not response.get("ok") or response.get("status") != "PROPOSED":
        _set(note, "p4_note_status", "response_unavailable")
        status = response.get("status", "UNAVAILABLE")
        result = {"status": status,
                  "decision": ("no_candidate" if status == "NO_CANDIDATE" else
                               "unsupported" if status == "UNSUPPORTED_NATIVE_ACTION" else "unavailable"),
                  "request_id": request_id, "error": response.get("error"),
                  "responder_volitions": response.get("responderVolitions", []),
                  "native_candidates": response.get("native_candidates", []),
                  "native_winning_tie_names": response.get("native_winning_tie_names", []),
                  "unsupported_native_winners": response.get("unsupported_native_winners", [])}
        complete_native_result = result["status"] in {
            "NO_CANDIDATE", "UNSUPPORTED_NATIVE_ACTION", "STALE_NATIVE_PROPOSAL",
            "WORLD_VALIDATION_REJECTED"
        }
        _append_scene_event(actor, "SOCIAL_RESPONSE", response_event_id, result,
                            sealed=complete_native_result)
        _set(actor, "p4_social_status", result["status"])
        _record(actor, {"kind": "p4_social_response", "result": result})
        return True

    _set(note, "p4_note_status", "responding")

    selected = response.get("selected") or {}
    action_name = selected.get("name")
    if action_name not in _P4_ACTIONS:
        _set(note, "p4_note_status", "response_unsupported")
        result = {"status": "UNSUPPORTED_NATIVE_ACTION", "decision": "unsupported",
                  "request_id": request_id, "native_candidates": response.get("native_candidates", []),
                  "selected_action": action_name}
        _append_scene_event(actor, "SOCIAL_RESPONSE", response_event_id, result, sealed=True)
        _set(actor, "p4_social_status", result["status"])
        _record(actor, {"kind": "p4_social_response", "result": result})
        return True

    auth = client.request({"op": "authorize", "proposalId": response["proposalId"],
                           "eventId": response_event_id, "actionName": action_name})
    if not auth.get("ok"):
        _set(note, "p4_note_status", "response_stale")
        result = {"status": "STALE_NATIVE_PROPOSAL", "decision": "stale",
                  "request_id": request_id, "error": auth.get("error"),
                  "selected_action": action_name}
        _append_scene_event(actor, "SOCIAL_RESPONSE", response_event_id, result, sealed=True)
        _set(actor, "p4_social_status", result["status"])
        _record(actor, {"kind": "p4_social_response", "result": result})
        return True

    if note not in actor.contents or _value(note, "p4_note_status") != "responding":
        _set(note, "p4_note_status", "response_stale")
        result = {"status": "WORLD_VALIDATION_REJECTED", "decision": "stale",
                  "request_id": request_id, "selected_action": action_name,
                  "reason": "the exact requested note is no longer held by its recipient"}
        _append_scene_event(actor, "SOCIAL_RESPONSE", response_event_id, result, sealed=True)
        _set(actor, "p4_social_status", result["status"])
        _record(actor, {"kind": "p4_social_response", "result": result})
        return True

    before_location = int(note.db_location_id) if note.db_location_id else None
    decision = "accepted" if selected.get("isAccept") is True else "rejected"
    # This is the real W-side settlement: the same physical note records the
    # recipient's native action exactly once. Its item remains in B's inventory.
    _set(note, "p4_note_status", decision)
    _set(note, "p4_note_action", action_name)
    _set(note, "p4_note_response_event_id", response_event_id)
    after_location = int(note.db_location_id) if note.db_location_id else None
    world_settled = (note in actor.contents and before_location == actor.id
                     and after_location == actor.id and _value(note, "p4_note_status") == decision)
    if not world_settled:
        _set(note, "p4_note_status", "response_settlement_pending")
        _set(actor, "p4_social_status", "WORLD_SETTLEMENT_PENDING")
        _record(actor, {"kind": "p4_social_response", "status": "WORLD_SETTLEMENT_PENDING",
                        "request_id": request_id, "note_id": int(note.id),
                        "selected_action": action_name})
        return True

    receipt_id = f"p4-note-response:{request_id}:{int(note.id)}"
    commit = {"op": "commit", "proposalId": response["proposalId"], "eventId": response_event_id,
              "settlementStatus": "settled", "settledActionName": action_name,
              "actionName": action_name, "settlementReceiptId": receipt_id}
    commit["settlementProof"] = client.settlement_proof(
        response["proposalId"], response_event_id, action_name, receipt_id)
    try:
        committed = client.request(commit)
    except TimeoutError as err:
        _set(note, "p4_native_commit_status", "pending")
        result = {"status": "SOCIAL_SETTLEMENT_PENDING", "decision": decision,
                  "request_id": request_id, "note_id": int(note.id), "selected_action": action_name,
                  "physical_receipt": {"status": "settled", "receipt_id": receipt_id,
                                       "actor_id": int(actor.id), "before_location_id": before_location,
                                       "after_location_id": after_location},
                  "native_commit_status": "pending", "native_error": str(err)}
        _append_scene_event(actor, "SOCIAL_RESPONSE", response_event_id, result, sealed=False)
        _set(actor, "p4_social_status", result["status"])
        _record(actor, {"kind": "p4_social_response", "result": result})
        return True
    if not committed.get("ok"):
        _set(note, "p4_native_commit_status", "pending")
        result = {"status": "SOCIAL_SETTLEMENT_PENDING", "decision": decision,
                  "request_id": request_id, "note_id": int(note.id), "selected_action": action_name,
                  "physical_receipt": {"status": "settled", "receipt_id": receipt_id,
                                       "actor_id": int(actor.id), "before_location_id": before_location,
                                       "after_location_id": after_location},
                  "native_commit_status": "pending", "native_error": committed.get("error")}
        _append_scene_event(actor, "SOCIAL_RESPONSE", response_event_id, result, sealed=False)
        _set(actor, "p4_social_status", result["status"])
        _record(actor, {"kind": "p4_social_response", "result": result})
        return True

    native_commit_id = f"{response_event_id}:commit"
    physical_receipt = {"status": "settled", "receipt_id": receipt_id,
                        "actor_id": int(actor.id), "before_location_id": before_location,
                        "after_location_id": after_location, "action_name": action_name,
                        "same_note_id": int(note.id)}
    response_args = {"request_id": request_id,
                     "source_event_id": _value(note, "p4_note_source_event_id"),
                     "initiator_role": "hero",
                     "initiator_actor_id": int(_value(note, "p4_note_initiator_id")),
                     "responder_actor_id": int(actor.id), "responder_role": "love",
                     "note_id": int(note.id), "note_dbref": str(note.dbref),
                     "decision": decision, "selected_action": action_name,
                     "native_volitions": response.get("responderVolitions", []),
                     "native_candidates": response.get("native_candidates", []),
                     "social_record_after": committed.get("socialRecord"),
                     "physical_receipt": physical_receipt,
                     "native_commit_status": "settled", "native_commit_receipt_id": native_commit_id}
    _append_scene_event(actor, "SOCIAL_RESPONSE", response_event_id, response_args,
                        sealed=True, receipt_id=receipt_id)
    _append_scene_event(actor, "SOCIAL_COMMIT", native_commit_id,
                        {"request_id": request_id, "note_id": int(note.id),
                         "proposal_id": response["proposalId"], "action_name": action_name,
                         "settlement_receipt_id": receipt_id,
                         "record_revision": committed.get("recordRevision"),
                         "social_record_after": committed.get("socialRecord"),
                         "trace": committed.get("trace")}, sealed=True,
                        receipt_id=native_commit_id)
    _set(note, "p4_native_commit_status", "settled")
    _set(actor, "p4_social_status", "SETTLED_" + decision.upper())
    _set(actor, "p4_social_result", {"request_id": request_id, "note_id": int(note.id),
                                     "decision": decision, "action_name": action_name,
                                     "receipt_id": receipt_id})
    _record(actor, {"kind": "p4_social_response", "status": "SETTLED",
                    "request_id": request_id, "note_id": int(note.id),
                    "decision": decision, "action_name": action_name,
                    "native_weight": selected.get("weight"),
                    "native_volitions": response.get("responderVolitions", []),
                    "native_candidates": response.get("native_candidates", []),
                    "native_commit_trace": committed.get("trace"),
                    "sim_minute": clock_for_actor(actor)["now"]})
    return True


def step_social(actor) -> bool:
    """Consume a P4/P5 actor callback only for a local, supported social transition."""
    profile = _value(actor, "activity_profile")
    if profile not in {"p4_story_v0", "p5_story_v0"}:
        return False
    if _value(actor, "mode") != "b" or _value(actor, "drive_mode") != "manual":
        return False
    p5_preset = _value(actor, "p5_native_social_preset") if profile == "p5_story_v0" else None
    if profile == "p5_story_v0" and p5_preset not in P5_PRESETS:
        raise ValueError("P5 actor is missing a registered immutable native social preset")
    role = actor.attributes.get("ensemble_character_id", category="ensemble_bridge", default=None)
    scene_id = _value(actor, "scene_id")
    if role == "hero":
        if not _own_delivery_settled(actor):
            return False
        target = _visible_target(actor)
        if target is None:
            return False
        if _value(actor, "p4_social_attempted", False):
            return False
        try:
            return _request_note(actor, target, _client(scene_id, p5_preset))
        except TimeoutError as err:
            result = {"status": "UNAVAILABLE", "error": str(err), "reason": "native request timed out"}
            _set(actor, "p4_social_status", "UNAVAILABLE")
            _set(actor, "p4_social_attempted", True)
            _record(actor, {"kind": "p4_social_request", "result": result})
            return True
        except Exception as err:
            result = {"status": "UNAVAILABLE", "error": f"{type(err).__name__}: {err}"}
            _set(actor, "p4_social_status", "UNAVAILABLE")
            _set(actor, "p4_social_attempted", True)
            _record(actor, {"kind": "p4_social_request", "result": result})
            return True
    if role == "love":
        note = next((obj for obj in actor.contents
                     if _value(obj, "p3_scene_id") == scene_id
                     and _value(obj, "p4_note_request_id") is not None
                     and _value(obj, "p4_note_status") == "written"), None)
        if note is None:
            return False
        try:
            return _respond_to_note(actor, note, _client(scene_id, p5_preset))
        except TimeoutError as err:
            _set(note, "p4_note_status", "response_unavailable")
            result = {"status": "UNAVAILABLE", "decision": "unavailable",
                      "request_id": _value(note, "p4_note_request_id"), "error": str(err)}
            _append_scene_event(actor, "SOCIAL_RESPONSE",
                                _event_id(_value(actor, "scenario_seed", 0), "love", "note-response"),
                                result, sealed=False)
            _set(actor, "p4_social_status", "UNAVAILABLE")
            _record(actor, {"kind": "p4_social_response", "result": result})
            return True
        except Exception as err:
            _set(note, "p4_note_status", "response_unavailable")
            result = {"status": "UNAVAILABLE", "decision": "unavailable",
                      "request_id": _value(note, "p4_note_request_id"),
                      "error": f"{type(err).__name__}: {err}"}
            _set(actor, "p4_social_status", "UNAVAILABLE")
            _record(actor, {"kind": "p4_social_response", "result": result})
            return True
    return False
