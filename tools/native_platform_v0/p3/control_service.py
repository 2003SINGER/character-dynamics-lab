"""Loopback-only Twisted RPC control surface for the native P3 Evennia game."""

from __future__ import annotations

from datetime import datetime, timezone
import hmac
import json
import os
from pathlib import Path
import secrets
from types import SimpleNamespace
from collections.abc import Mapping, Sequence
from typing import Any

from twisted.application import internet
from twisted.internet import defer
from twisted.protocols.basic import LineReceiver
from twisted.internet.protocol import Factory


PROJECT_ROOT = Path(__file__).resolve().parents[3]
PRIVATE_ROOT = PROJECT_ROOT / "_local_data/native_platform_v0/p3"
TOKEN_PATH = PRIVATE_ROOT / "control.token"
HOST = "127.0.0.1"
PORT = 14011
MAX_REQUEST_BYTES = 64 * 1024
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
MAX_SCENES_PER_PROCESS = 16
ROLE_NAMES = {"player", "courier", "resident"}
SCENARIO_NAMES = {"Aclean", "Asteal-return", "Bclean", "Bsteal-resident-parcel"}
C0_SCENARIO_NAMES = {"C0-no-delivery", "C0-delivery-priority", "C0-after-delivery"}
C1A_SCENARIO_NAMES = {"C1a-blocked-switch", "C1a-observed-resume"}
P4_SCENARIO_NAMES = {"open", "blocked-return", "blocked-held", "short-deadline"}
SAFE_P3_KEYS = (
    "p3_scene_id", "p3_control_role", "p3_role", "p3_goal", "goal", "mode", "scenario_seed",
    "activity_profile", "delivery_task", "patrol_exit_locked", "patrol_rejected_state",
    "drive_mode", "interval_seconds",
    "status", "tick_count", "pending_action", "last_outcome", "last_observation",
    "witnessed", "log", "native_receipts", "pending_social", "task_item_id", "task_item_key",
    "task_item_dbref", "task_destination_id", "task_destination_dbref", "resident_id",
    "social_attempted", "social_result", "script_id",
    "p4_clock", "p4_ledger", "p4_timeline", "p4_ledger_sequence", "p4_ledger_seal",
    "p4_opportunity_used", "p4_pickup_id", "p4_destination_id", "p4_east_initially_closed",
    "p4_social_attempted", "p4_social_status", "p4_social_result", "p4_note_request_id",
    "p4_note_source_event_id", "p4_note_status", "p4_note_action", "p4_note_response_event_id",
    "p4_note_initiator_id", "p4_note_recipient_id",
)


def _now():
    return datetime.now(timezone.utc).isoformat()


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_json_safe(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()
                if not any(term in str(key).casefold() for term in
                           ("account", "password", "session", "secret", "hmac", "settings", "token"))}
    if hasattr(value, "id") and value.__class__.__module__.startswith("evennia"):
        return {"id": int(value.id), "dbref": str(value.dbref), "key": str(value.key)}
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return {"unsupported_type": f"{value.__class__.__module__}.{value.__class__.__name__}"}


def _read_or_create_token() -> str:
    PRIVATE_ROOT.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(str(TOKEN_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        mode = TOKEN_PATH.stat().st_mode & 0o777
        if mode & 0o077:
            raise RuntimeError("control token permissions must be owner-only (0600)")
        token = TOKEN_PATH.read_text(encoding="utf-8").strip()
        if len(token) < 32:
            raise RuntimeError("control token file is invalid")
        return token
    token = secrets.token_urlsafe(48)
    try:
        os.write(fd, token.encode("ascii"))
        os.fsync(fd)
    finally:
        os.close(fd)
    return token


def _validate_scene_id(scene_id: Any) -> str:
    import re
    if not isinstance(scene_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", scene_id):
        raise ValueError("scene_id must be an exact generated scene identifier")
    return scene_id


def _reset_options(args: dict[str, Any]) -> tuple[str, int, str, int, str, bool, bool]:
    allowed = {"mode", "seed", "drive_mode", "interval", "activity_profile", "delivery_task",
               "patrol_exit_locked"}
    if set(args) - allowed:
        raise ValueError("reset_scenario contains unsupported fields")
    mode = args.get("mode", "a")
    seed = args.get("seed", 0)
    drive_mode = args.get("drive_mode", "manual")
    interval = args.get("interval", 4)
    profile = args.get("activity_profile", "legacy_delivery_v0")
    delivery_task = args.get("delivery_task", True)
    patrol_exit_locked = args.get("patrol_exit_locked", False)
    if (mode not in ("a", "b") or type(seed) is not int or not (0 <= seed <= 2**31 - 1) or
            drive_mode not in ("manual", "timer") or type(interval) is not int or not 2 <= interval <= 30 or
            profile not in ("legacy_delivery_v0", "delivery_patrol_v0", "delivery_patrol_recovery_v0") or
            type(delivery_task) is not bool or
            type(patrol_exit_locked) is not bool):
        raise ValueError("invalid mode/seed/drive/interval/activity profile/task flag")
    if patrol_exit_locked and (mode != "a" or profile != "delivery_patrol_v0" or delivery_task):
        raise ValueError("patrol_exit_locked is only allowed for the C0 single-actor no-delivery profile")
    if profile == "legacy_delivery_v0" and (delivery_task is not True or patrol_exit_locked):
        raise ValueError("legacy_delivery_v0 preserves a required delivery task and unlocked exits")
    if profile == "delivery_patrol_recovery_v0" and (mode != "a" or not delivery_task or patrol_exit_locked):
        raise ValueError("delivery_patrol_recovery_v0 requires a single actor, assigned task, and unlocked exits")
    return mode, seed, drive_mode, interval, profile, delivery_task, patrol_exit_locked


def _owner_account():
    """Resolve the fixed local fixture account server-side; never return its data."""
    from evennia.accounts.models import AccountDB
    return AccountDB.objects.get(username="p1admin")


def _scene_objects(scene_id: str):
    from evennia.objects.models import ObjectDB
    rows = ObjectDB.objects.get_by_attribute(key="p3_scene_id", category="native_p3", value=scene_id)
    result = []
    for obj in rows.distinct().order_by("id"):
        if obj.attributes.get("p3_scene_id", category="native_p3") == scene_id:
            result.append(obj)
    if not result:
        raise ValueError("unknown or expired generated P3 scene")
    return result


def _actor_for(scene_objects, role: str, account_id: int):
    if role not in ROLE_NAMES:
        raise ValueError("actor_role must be player, courier, or resident")
    for obj in scene_objects:
        if obj.attributes.get("p3_control_role", category="native_p3") != role:
            continue
        if obj.attributes.get("owner_account_id", category="native_p3") != account_id:
            continue
        return obj
    raise ValueError("actor role is not present in this owned generated scene")


def _load_scene(scene_id: str):
    scene_id = _validate_scene_id(scene_id)
    account = _owner_account()
    objects = _scene_objects(scene_id)
    for obj in objects:
        obj.attributes.get("p3_scene_id", category="native_p3")
    return account, objects


def _role_actor_rows(scene_objects, account_id: int):
    rows = {}
    for obj in scene_objects:
        role = obj.attributes.get("p3_control_role", category="native_p3")
        if role in ROLE_NAMES and obj.attributes.get("owner_account_id", category="native_p3") == account_id:
            rows[role] = obj
    return rows


def _actor_snapshot(actor):
    from tools.native_platform_v0.p3.agency import get_value
    return {
        "id": int(actor.id), "dbref": str(actor.dbref), "role": get_value(actor, "p3_control_role"),
        "room_id": int(actor.location.id) if actor.location else None,
        "status": get_value(actor, "status"), "tick_count": get_value(actor, "tick_count", 0),
        "pending_action": _json_safe(get_value(actor, "pending_action")),
        "last_outcome": _json_safe(get_value(actor, "last_outcome")),
    }


class P3Control:
    def __init__(self):
        self.token = _read_or_create_token()
        self.created_scenes = 0

    def dispatch(self, message):
        if not isinstance(message, dict):
            raise ValueError("request must be a JSON object")
        if set(message) - {"token", "request_id", "op", "args"}:
            raise ValueError("request contains unsupported fields")
        supplied = message.get("token")
        if not isinstance(supplied, str) or not hmac.compare_digest(supplied, self.token):
            raise PermissionError("authentication failed")
        op = message.get("op")
        args = message.get("args", {})
        if not isinstance(args, dict):
            raise ValueError("args must be an object")
        handlers = {
            "health": self.health,
            "reset_scenario": self.reset_scenario,
            "pause_scenario": self.pause_scenario,
            "run_c0_scenario": self.run_c0_scenario,
            "run_c1a_scenario": self.run_c1a_scenario,
            "run_p4_scenario": self.run_p4_scenario,
            "step_world": self.step_world,
            "inject_action": self.inject_action,
            "observe_actor": self.observe_actor,
            "get_trace": self.get_trace,
            "run_scenario": self.run_scenario,
        }
        if op not in handlers:
            raise ValueError("unsupported operation")
        return handlers[op](args)

    def health(self, args):
        if args:
            raise ValueError("health takes no arguments")
        return {"status": "READY", "service": "native-p3-control", "bind": f"{HOST}:{PORT}"}

    def reset_scenario(self, args):
        mode, seed, drive_mode, interval, profile, delivery_task, patrol_exit_locked = _reset_options(args)
        if self.created_scenes >= MAX_SCENES_PER_PROCESS:
            raise ValueError("scene creation limit reached for this server process")
        from evennia.utils.create import create_object
        from typeclasses.characters import Character
        from tools.native_platform_v0.p3.scene import create_scene

        account = _owner_account()
        scene = create_scene(SimpleNamespace(account=account), mode=mode, seed=seed,
                             drive_mode=drive_mode, interval=interval, activity_profile=profile,
                             delivery_task=delivery_task, patrol_exit_locked=patrol_exit_locked)
        roles = {"courier": scene["courier"]}
        scene["courier"].attributes.add("p3_control_role", "courier", category="native_p3")
        if mode == "b":
            roles["resident"] = scene["resident"]
            scene["resident"].attributes.add("p3_control_role", "resident", category="native_p3")
        player = create_object(
            Character, key=f"P3 Fixture Player {scene['scene_id']}", location=scene["pickup"],
            attributes=[("p3_scene_id", scene["scene_id"], "native_p3"),
                        ("p3_control_role", "player", "native_p3"),
                        ("owner_account_id", account.id, "native_p3"),
                        ("drive_mode", drive_mode, "native_p3"),
                        ("log", [], "native_p3"),
                        ("native_receipts", [], "native_p3")],
        )
        # The fixed fixture account authenticates this loopback API only. The
        # generated in-world player remains an ordinary unattached Character.
        roles["player"] = player
        scene_objects = _scene_objects(scene["scene_id"])
        self.created_scenes += 1
        return {
            "scene_id": scene["scene_id"], "mode": mode, "seed": seed,
            "drive_mode": drive_mode, "interval": interval,
            "activity_profile": profile, "delivery_task": delivery_task,
            "patrol_exit_locked": patrol_exit_locked,
            "roles": {role: {"id": int(obj.id), "dbref": str(obj.dbref)} for role, obj in roles.items()},
            "rooms": {"pickup": {"id": int(scene["pickup"].id), "dbref": str(scene["pickup"].dbref)},
                      "destination": {"id": int(scene["destination"].id), "dbref": str(scene["destination"].dbref)}},
            "scene_object_count": len(scene_objects), "created_at": _now(),
        }

    def pause_scenario(self, args):
        if set(args) != {"scene_id"}:
            raise ValueError("pause_scenario requires only scene_id")
        scene_id = _validate_scene_id(args["scene_id"])
        account, objects = _load_scene(scene_id)
        from evennia.scripts.models import ScriptDB
        from tools.native_platform_v0.p3.agency import get_value, set_value

        paused = []
        for actor in _role_actor_rows(objects, account.id).values():
            if get_value(actor, "p3_control_role") == "player":
                continue
            script_id = get_value(actor, "script_id")
            script = ScriptDB.objects.filter(id=script_id).first() if script_id else None
            if script:
                script.stop()
            set_value(actor, "status", "PAUSED")
            paused.append(_actor_snapshot(actor))
        if not paused:
            raise ValueError("scene has no owned P3 autonomy actors to pause")
        return {"scene_id": scene_id, "status": "PAUSED", "actors": paused,
                "scope": "generated_scene_roles_only"}

    def _p4_snapshot(self, scene_id):
        account, objects = _load_scene(scene_id)
        actors = _role_actor_rows(objects, account.id)
        pickup = next((obj for obj in objects if obj.attributes.get("p4_clock", category="native_p3", default=None)), None)
        if pickup is None:
            raise ValueError("generated P4 scene has no clock owner")
        actor_rows = {}
        for role in ("courier", "resident", "player"):
            actor = actors.get(role)
            if actor is not None:
                actor_rows[role] = {"id": int(actor.id), "room_id": int(actor.location.id) if actor.location else None,
                                    "inventory_ids": sorted(int(obj.id) for obj in actor.contents)}
        items = {}
        for obj in objects:
            role = obj.attributes.get("p3_role", category="native_p3", default=None)
            if role in ("assigned_supply", "resident_assigned_parcel"):
                name = "courier_supply" if role == "assigned_supply" else "resident_parcel"
                items[name] = {"id": int(obj.id), "location_id": int(obj.db_location_id) if obj.db_location_id else None}
        for obj in objects:
            if obj.attributes.get("p4_note_request_id", category="native_p3", default=None):
                items.setdefault("note", {"id": int(obj.id), "location_id": int(obj.db_location_id) if obj.db_location_id else None,
                                           "status": obj.attributes.get("p4_note_status", category="native_p3", default=None)})
        clock = dict(pickup.attributes.get("p4_clock", category="native_p3"))
        return {"actors": actor_rows, "items": items, "clock": clock,
                "east_closed": bool(__import__("tools.native_platform_v0.p3.p4_world", fromlist=["director_view"])
                                     .director_view(scene_id)["door_closed"]),
                "opportunity_used": pickup.attributes.get("p4_opportunity_used", category="native_p3", default=False) is True}

    def _p4_round_start(self, scene_id):
        from tools.native_platform_v0.p3.p4_monitor import choose_director
        from tools.native_platform_v0.p3.p4_world import advance_clock, append_event, director_view, open_east_passage

        advanced = advance_clock(scene_id)
        view = director_view(scene_id)
        _, objects = _load_scene(scene_id)
        pickup = next(obj for obj in objects if obj.attributes.get("p4_clock", category="native_p3", default=None))
        enabled = pickup.attributes.get("p4_director_enabled", category="native_p3", default=False) is True
        decision = choose_director(view, enabled)
        before = self._p4_snapshot(scene_id)
        director_args = {"authorized_view": view, "enabled": enabled,
                         "candidate_actions": decision["candidates"], "action": decision["action"],
                         "reason": decision["reason"], "before": {"east_closed": before["east_closed"],
                                                                    "opportunity_used": before["opportunity_used"]}}
        append_event(scene_id, {"event_type": "DIRECTOR_DECISION",
                                "event_id": f"p4:{pickup.attributes.get('scenario_seed', category='native_p3', default=0)}:{advanced['now']}:director",
                                "typed_args": director_args, "sealed": True})
        world_result = None
        if decision["action"] == "OPEN_PASSAGE":
            world_result = open_east_passage(scene_id)
            after = self._p4_snapshot(scene_id)
            author_args = {"action": "OPEN_PASSAGE", "settled": world_result["settled"],
                           "east_exit_id": world_result.get("east_exit_id"),
                           "before": {"east_closed": before["east_closed"],
                                      "opportunity_used": before["opportunity_used"]},
                           "after": {"east_closed": after["east_closed"],
                                     "opportunity_used": after["opportunity_used"]},
                           "west_exit_unchanged": world_result.get("west_unchanged") is True,
                           "west_before_traversable": world_result.get("west_before_traversable"),
                           "west_after_traversable": world_result.get("west_after_traversable"),
                           "state_scope": ["generated_east_exit.traverse", "p4_opportunity_used"]}
            append_event(scene_id, {"event_type": "AUTHOR_WORLD_EVENT",
                                    "event_id": f"p4:{pickup.attributes.get('scenario_seed', category='native_p3', default=0)}:{advanced['now']}:open-east",
                                    "typed_args": author_args, "sealed": world_result["settled"],
                                    "receipt_id": f"p4-author-open:{scene_id}:{advanced['now']}" if world_result["settled"] else None})
        return {"clock": advanced, "director": decision, "world_result": world_result}

    @defer.inlineCallbacks
    def _p4_actor_callbacks(self, scene_id, callback_index):
        account, objects = _load_scene(scene_id)
        actors = _role_actor_rows(objects, account.id)
        from tools.native_platform_v0.p3.agency import get_value, step_actor
        from tools.native_platform_v0.p3.p4_world import append_event

        result_rows = []
        for role in ("courier", "resident"):
            actor = actors.get(role)
            if actor is None:
                raise ValueError(f"P4 generated actor {role} is missing")
            before = self._p4_snapshot(scene_id)["actors"][role]
            log_before = list(get_value(actor, "log", []))
            result = yield defer.maybeDeferred(step_actor, actor)
            log_after = list(get_value(actor, "log", []))
            after = self._p4_snapshot(scene_id)["actors"][role]
            new_events = log_after[len(log_before):]
            args = {"role": role, "actor_id": int(actor.id), "callback_index": callback_index,
                    "before": before, "after": after,
                    "local_decision_events": new_events,
                    "callback_result_type": type(result).__name__, "awaited": True}
            clock = self._p4_snapshot(scene_id)["clock"]
            event_id = f"p4:{get_value(actor, 'scenario_seed', 0)}:{role}:{clock['now']}:callback"
            event = append_event(scene_id, {"event_type": "NPC_CALLBACK", "event_id": event_id,
                                            "typed_args": args, "sealed": True})
            result_rows.append({"event": event, "callback_result_type": type(result).__name__})
        defer.returnValue(result_rows)

    @defer.inlineCallbacks
    def step_world(self, args):
        if set(args) - {"scene_id", "rounds"}:
            raise ValueError("step_world accepts only scene_id and rounds")
        scene_id = _validate_scene_id(args.get("scene_id"))
        rounds = args.get("rounds", 1)
        if type(rounds) is not int or not (1 <= rounds <= 50):
            raise ValueError("rounds must be an integer from 1 through 50")
        account, objects = _load_scene(scene_id)
        actors = _role_actor_rows(objects, account.id)
        runners = [actors[role] for role in ("courier", "resident") if role in actors]
        if not runners:
            raise ValueError("scene has no generated P3 autonomy actors")
        from tools.native_platform_v0.p3.agency import get_value, step_actor

        is_p4 = all(get_value(actor, "activity_profile") == "p4_story_v0" for actor in runners)

        results = []
        for round_index in range(rounds):
            if is_p4:
                self._p4_round_start(scene_id)
                results.extend((yield self._p4_actor_callbacks(
                    scene_id, self._p4_snapshot(scene_id)["clock"]["now"])))
            else:
                for actor in runners:
                    if get_value(actor, "drive_mode") != "manual":
                        raise ValueError("step_world requires a manual-drive P3 fixture")
                    result = yield defer.maybeDeferred(step_actor, actor)
                    results.append({"round": round_index + 1, "actor": _actor_snapshot(actor),
                                    "callback_result_type": type(result).__name__})
        defer.returnValue({"scene_id": scene_id, "rounds": rounds, "actor_callbacks": results,
                           "awaited": True})

    def inject_action(self, args):
        allowed = {"scene_id", "actor_role", "operation", "direction", "item_id", "text"}
        if set(args) - allowed:
            raise ValueError("inject_action contains unsupported fields")
        scene_id = _validate_scene_id(args.get("scene_id"))
        role = args.get("actor_role")
        if role not in ROLE_NAMES:
            raise ValueError("actor_role must be a generated player, courier, or resident")
        account, objects = _load_scene(scene_id)
        actor = _actor_for(objects, role, account.id)
        operation = args.get("operation")
        command = None
        expected = None
        item = None
        intervention = "native-player-command" if role == "player" else "test-controller-external-npc-command"
        if operation == "move":
            if set(args) - {"scene_id", "actor_role", "operation", "direction"}:
                raise ValueError("move accepts only a direction")
            direction = args.get("direction")
            if direction not in ("east", "west") or actor.location is None:
                raise ValueError("direction must be an available generated east/west exit")
            edge = next((exit_obj for exit_obj in actor.location.exits
                         if exit_obj.key == direction and exit_obj.destination and
                         exit_obj.attributes.get("p3_scene_id", category="native_p3") == scene_id), None)
            if edge is None:
                raise ValueError("generated exit is not available from the actor's current room")
            command, expected = edge.key, int(edge.destination.id)
        elif operation in ("get", "drop"):
            if set(args) - {"scene_id", "actor_role", "operation", "item_id"}:
                raise ValueError(f"{operation} accepts only item_id")
            item_id = args.get("item_id")
            if type(item_id) is not int:
                raise ValueError("item_id must be an integer in the generated scene")
            item = next((obj for obj in objects if int(obj.id) == item_id), None)
            if item is None or item.attributes.get("p3_role", category="native_p3") not in (
                "assigned_supply", "resident_assigned_parcel", "delivery_destination_marker",
            ):
                raise ValueError("item_id is not a generated P3 scene item")
            if operation == "get":
                if actor.location is None or item.db_location_id != actor.location.id or not item.access(actor, "view", default=True):
                    raise ValueError("item is not visible in the actor's current room")
                command = f"get {item.key}"
                expected = "inventory"
            else:
                if item not in actor.contents:
                    raise ValueError("item is not held by the actor")
                command = f"drop {item.key}"
                expected = int(actor.location.id) if actor.location else None
        elif operation in ("look", "inventory"):
            if set(args) != {"scene_id", "actor_role", "operation"}:
                raise ValueError(f"{operation} takes no extra arguments")
            command = "look" if operation == "look" else "inventory"
        elif operation == "say":
            if set(args) != {"scene_id", "actor_role", "operation", "text"}:
                raise ValueError("say requires only text")
            text = args.get("text")
            if not isinstance(text, str) or not text.strip() or len(text) > 300 or "\n" in text:
                raise ValueError("say text must be 1-300 characters on one line")
            command = f"say {text}"
        else:
            raise ValueError("operation must be move/get/drop/look/inventory/say")

        deferred = defer.maybeDeferred(actor.execute_cmd, command)

        def after_command(_):
            settled = None
            if operation == "move":
                settled = bool(actor.location and actor.location.id == expected)
            elif operation == "get":
                settled = bool(item in actor.contents)
            elif operation == "drop":
                settled = bool(item.location and item.location.id == expected and item not in actor.contents)
            return {"scene_id": scene_id, "actor_role": role, "actor_dbref": str(actor.dbref),
                    "operation": operation, "command": command, "caller_identity": "authenticated-loopback-test-controller",
                    "intervention_kind": intervention, "settled": settled,
                    "actor_room_id": int(actor.location.id) if actor.location else None,
                    "item_id": int(item.id) if item else None,
                    "item_location_id": int(item.db_location_id) if item and item.db_location_id else None}

        deferred.addCallback(after_command)
        return deferred

    def observe_actor(self, args):
        if set(args) != {"scene_id", "actor_role"}:
            raise ValueError("observe_actor requires scene_id and actor_role")
        account, objects = _load_scene(args["scene_id"])
        actor = _actor_for(objects, args["actor_role"], account.id)
        from tools.native_platform_v0.p3.agency import observe_actor
        view = observe_actor(actor)
        return {"scene_id": args["scene_id"], "actor_role": args["actor_role"], "local_observation": _json_safe(view)}

    def get_trace(self, args):
        if set(args) != {"scene_id"}:
            raise ValueError("get_trace requires only scene_id")
        scene_id = _validate_scene_id(args["scene_id"])
        account, objects = _load_scene(scene_id)
        rows = []
        for obj in objects:
            attrs = {}
            for key in SAFE_P3_KEYS:
                value = obj.attributes.get(key, category="native_p3", default=None)
                if value is not None:
                    attrs[key] = _json_safe(value)
            social = obj.attributes.get("native_social_events", category="native_social", default=[])
            if social:
                attrs["native_social_events"] = _json_safe(social)
            rows.append({"id": int(obj.id), "dbref": str(obj.dbref), "key": str(obj.key),
                         "typeclass_path": str(obj.db_typeclass_path),
                         "location_id": int(obj.location.id) if obj.location else None,
                         "exit_destination_id": int(obj.destination.id) if obj.destination else None,
                         "attributes": attrs})
        return {"scene_id": scene_id, "source": "live Evennia object and attribute state",
                "full_logs": True, "account_fields_exported": False, "objects": rows}

    def _c0_actor_trace(self, scene_id):
        trace = self.get_trace({"scene_id": scene_id})
        actor = next((row for row in trace["objects"]
                      if row["attributes"].get("p3_control_role") == "courier"), None)
        if actor is None:
            raise ValueError("generated C0 scene is missing its courier actor")
        attrs = actor["attributes"]
        return {"id": actor["id"], "dbref": actor["dbref"], "room_id": actor["location_id"],
                "status": attrs.get("status"), "tick_count": attrs.get("tick_count", 0),
                "last_outcome": attrs.get("last_outcome"), "pending_action": attrs.get("pending_action"),
                "native_receipts": attrs.get("native_receipts", []), "log_length": len(attrs.get("log", []))}

    @defer.inlineCallbacks
    def _c0_drive_callbacks(self, scene_id, count):
        callbacks = []
        for index in range(count):
            step = yield defer.maybeDeferred(self.step_world, {"scene_id": scene_id, "rounds": 1})
            callbacks.append({"callback_index": index + 1, "step": step,
                              "actor": self._c0_actor_trace(scene_id)})
        defer.returnValue(callbacks)

    @defer.inlineCallbacks
    def run_c0_scenario(self, args):
        if set(args) - {"scenario", "seed"}:
            raise ValueError("run_c0_scenario accepts only scenario and seed")
        scenario = args.get("scenario")
        seed = args.get("seed", 0)
        if scenario not in C0_SCENARIO_NAMES or type(seed) is not int or not 0 <= seed <= 2**31 - 1:
            raise ValueError("scenario must be one of the three C0 cases; seed must be 0..2147483647")
        common = {"mode": "a", "seed": seed, "drive_mode": "manual", "interval": 4,
                  "activity_profile": "delivery_patrol_v0"}
        if scenario == "C0-no-delivery":
            primary_config = {**common, "delivery_task": False, "patrol_exit_locked": False}
            primary_scene = self.reset_scenario(primary_config)
            primary_callbacks = yield self._c0_drive_callbacks(primary_scene["scene_id"], 12)
            negative_config = {**common, "delivery_task": False, "patrol_exit_locked": True}
            negative_scene = self.reset_scenario(negative_config)
            # Tick 1 proposes and tick 2 makes the native rejected move; the
            # next eight callbacks prove the same intent is not retried.
            negative_callbacks = yield self._c0_drive_callbacks(negative_scene["scene_id"], 10)
            defer.returnValue({"schema": "native-p3-c0-run-v1", "scenario": scenario, "seed": seed,
                               "profile": "delivery_patrol_v0", "drive_mode": "manual",
                               "controller_interventions": 0,
                               "scenes": [
                                   {"role": "no_delivery_primary", "configuration": primary_config,
                                    "callbacks": primary_callbacks,
                                    "trace": self.get_trace({"scene_id": primary_scene["scene_id"]})},
                                   {"role": "locked_exit_negative_control", "configuration": negative_config,
                                    "callbacks": negative_callbacks,
                                    "trace": self.get_trace({"scene_id": negative_scene["scene_id"]})},
                               ], "callbacks_completed": True,
                               "completion_scope": "bounded_callbacks_only_not_semantic_acceptance"})

        delivery_task = True
        configuration = {**common, "delivery_task": delivery_task, "patrol_exit_locked": False}
        scene = self.reset_scenario(configuration)
        callback_count = 12 if scenario == "C0-delivery-priority" else 20
        callbacks = yield self._c0_drive_callbacks(scene["scene_id"], callback_count)
        defer.returnValue({"schema": "native-p3-c0-run-v1", "scenario": scenario, "seed": seed,
                           "profile": "delivery_patrol_v0", "drive_mode": "manual",
                           "controller_interventions": 0, "configuration": configuration,
                           "callback_limit": callback_count, "callbacks": callbacks,
                           "trace": self.get_trace({"scene_id": scene["scene_id"]}),
                           "callbacks_completed": True,
                           "completion_scope": "bounded_callbacks_only_not_semantic_acceptance"})

    def _c1a_snapshot(self, scene_id):
        trace = self.get_trace({"scene_id": scene_id})
        actor = next(row for row in trace["objects"]
                     if row["attributes"].get("p3_control_role") == "courier")
        player = next(row for row in trace["objects"]
                      if row["attributes"].get("p3_control_role") == "player")
        item = next(row for row in trace["objects"]
                    if row["attributes"].get("p3_role") == "assigned_supply")
        attrs = actor["attributes"]
        return {"scene_id": scene_id, "actor": {
                    "id": actor["id"], "dbref": actor["dbref"], "room_id": actor["location_id"],
                    "status": attrs.get("status"), "tick_count": attrs.get("tick_count"),
                    "pending_action": attrs.get("pending_action"), "last_outcome": attrs.get("last_outcome"),
                    "task_item_id": attrs.get("task_item_id"),
                    "task_destination_id": attrs.get("task_destination_id"),
                    "native_receipts": attrs.get("native_receipts", []),
                    "last_observation": attrs.get("last_observation"),
                    "witnessed": attrs.get("witnessed", {})},
                "player": {"id": player["id"], "dbref": player["dbref"],
                           "room_id": player["location_id"],
                           "inventory_ids": [row.get("id") for row in trace["objects"]
                                             if row.get("location_id") == player["id"]]},
                "item": {"id": item["id"], "location_id": item["location_id"]}}

    @defer.inlineCallbacks
    def _c1a_callback(self, scene_id, callback_index):
        before = self._c1a_snapshot(scene_id)
        before_trace = self.get_trace({"scene_id": scene_id})
        actor_before = next(row for row in before_trace["objects"]
                            if row["attributes"].get("p3_control_role") == "courier")
        log_start = len(actor_before["attributes"].get("log", []))
        step = yield defer.maybeDeferred(self.step_world, {"scene_id": scene_id, "rounds": 1})
        after_trace = self.get_trace({"scene_id": scene_id})
        actor_after = next(row for row in after_trace["objects"]
                           if row["attributes"].get("p3_control_role") == "courier")
        log = actor_after["attributes"].get("log", [])
        defer.returnValue({"kind": "npc_callback", "callback_index": callback_index,
                           "before": before, "callback": step["actor_callbacks"][0],
                           "after": self._c1a_snapshot(scene_id), "new_log_events": log[log_start:],
                           "local_observation": actor_after["attributes"].get("last_observation"),
                           "callback_log_length_before": log_start,
                           "callback_log_length_after": len(log)})

    def _c1a_player_command(self, scene_id, operation, item_id, label):
        before = self._c1a_snapshot(scene_id)
        result = defer.maybeDeferred(self.inject_action, {
            "scene_id": scene_id, "actor_role": "player", "operation": operation,
            "item_id": item_id,
        })
        def captured(receipt):
            return {"kind": "player_intervention", "label": label,
                    "pre_snapshot": before, "command_receipt": receipt,
                    "post_snapshot": self._c1a_snapshot(scene_id)}
        result.addCallback(captured)
        return result

    @defer.inlineCallbacks
    def run_c1a_scenario(self, args):
        if set(args) - {"scenario", "seed"}:
            raise ValueError("run_c1a_scenario accepts only scenario and seed")
        scenario = args.get("scenario")
        seed = args.get("seed", 0)
        if scenario not in C1A_SCENARIO_NAMES or type(seed) is not int or not 0 <= seed <= 2**31 - 1:
            raise ValueError("scenario must be one of the two C1a cases; seed must be 0..2147483647")
        if self.created_scenes >= MAX_SCENES_PER_PROCESS:
            raise ValueError("scene creation limit reached for this server process")
        config = {"mode": "a", "seed": seed, "drive_mode": "manual", "interval": 4,
                  "activity_profile": "delivery_patrol_recovery_v0", "delivery_task": True,
                  "patrol_exit_locked": False}
        created = self.reset_scenario(config)
        scene_id = created["scene_id"]
        courier_id = created["roles"]["courier"]["id"]
        player_id = created["roles"]["player"]["id"]
        item_id = next(row["id"] for row in self.get_trace({"scene_id": scene_id})["objects"]
                       if row["attributes"].get("p3_role") == "assigned_supply")
        timeline = []

        # First native callback persists a GTPyhop get intent; then the generated
        # ordinary player takes the item through a real Evennia command.
        timeline.append((yield self._c1a_callback(scene_id, 1)))
        steal = yield self._c1a_player_command(scene_id, "get", item_id, "player_steals_assigned_supply")
        timeline.append(steal)
        if steal["command_receipt"].get("settled") is not True:
            raise ValueError("C1a setup intervention failed to settle through the generated player command")

        # Submit the actor's persisted pre-intervention get. The C1a-only native
        # fallback may dispatch the observed exact key, never a global dbref.
        timeline.append((yield self._c1a_callback(scene_id, 2)))
        after_reject = timeline[-1]
        rejection = next((event for event in after_reject["new_log_events"]
                          if event.get("kind") == "execution_settlement"
                          and event.get("receipt", {}).get("kind") == "get"), None)
        if (not rejection or rejection.get("status") != "WORLD_VALIDATION_REJECTED"
                or rejection.get("receipt", {}).get("settled") is not False
                or rejection.get("receipt", {}).get("dispatch_succeeded") is not True
                or rejection.get("receipt", {}).get("submitted_command") !=
                   f"get {after_reject['before']['actor'].get('last_observation', {}).get('observation', {}).get('task_item', {}).get('key')}"):
            raise ValueError("C1a stale get was not submitted as the previously observed native command and rejected by world state")

        timeline.append((yield self._c1a_callback(scene_id, 3)))
        timeline.append((yield self._c1a_callback(scene_id, 4)))
        moved = timeline[-1]["after"]
        pickup_id = created["rooms"]["pickup"]["id"]
        if moved["actor"]["room_id"] == pickup_id:
            raise ValueError("C1a patrol did not leave the original room after the failed get")

        if scenario == "C1a-blocked-switch":
            for index in range(5, 13):
                timeline.append((yield self._c1a_callback(scene_id, index)))
        else:
            # Return the item to the original room while the actor is away, then
            # perform an explicit local observation and one negative-control tick.
            timeline.append((yield self._c1a_player_command(scene_id, "drop", item_id,
                                                            "player_returns_supply_to_original_room")))
            immediate_observation = self.observe_actor({"scene_id": scene_id, "actor_role": "courier"})
            timeline.append({"kind": "away_room_negative_observation", "observation": immediate_observation,
                             "snapshot": self._c1a_snapshot(scene_id)})
            timeline.append((yield self._c1a_callback(scene_id, 5)))
            for index in range(6, 17):
                timeline.append((yield self._c1a_callback(scene_id, index)))

        final_trace = self.get_trace({"scene_id": scene_id})
        defer.returnValue({"schema": "native-p3-c1a-run-v1", "scenario": scenario, "seed": seed,
                           "activity_profile": "delivery_patrol_recovery_v0", "drive_mode": "manual",
                           "configuration": config, "created_scene": created,
                           "callback_count": 12 if scenario == "C1a-blocked-switch" else 16,
                           "timeline": timeline, "trace": final_trace,
                           "callbacks_completed": True,
                           "completion_scope": "bounded_callbacks_only_not_semantic_acceptance",
                           "scene_ids": [scene_id], "controller_authored_npc_commands": 0})

    def _create_p4_scene(self, case, director_enabled, seed, deadline):
        from evennia.utils.create import create_object
        from typeclasses.characters import Character
        from tools.native_platform_v0.p3.scene import create_scene
        from tools.native_platform_v0.p3.p4_social import native_source_manifest

        account = _owner_account()
        initial_east_closed = case != "open"
        scene = create_scene(SimpleNamespace(account=account), mode="b", seed=seed,
                             drive_mode="manual", interval=4, activity_profile="p4_story_v0",
                             delivery_task=True, patrol_exit_locked=False,
                             p4_east_closed=initial_east_closed, p4_deadline=deadline)
        scene_id = scene["scene_id"]
        scene["courier"].attributes.add("p3_control_role", "courier", category="native_p3")
        scene["resident"].attributes.add("p3_control_role", "resident", category="native_p3")
        scene["pickup"].attributes.add("p4_director_enabled", director_enabled, category="native_p3")
        player = create_object(
            Character, key=f"P4 Fixture Player {scene_id}", location=scene["pickup"],
            attributes=[("p3_scene_id", scene_id, "native_p3"),
                        ("p3_control_role", "player", "native_p3"),
                        ("owner_account_id", account.id, "native_p3"),
                        ("drive_mode", "manual", "native_p3"),
                        ("native_receipts", [], "native_p3"), ("log", [], "native_p3")],
        )
        supply, parcel = scene["supply"], scene["return_parcel"]
        return {
            "scene_id": scene_id, "mode": "b", "activity_profile": "p4_story_v0",
            "drive_mode": "manual", "scene": scene,
            "created_scene": {
                "scene_id": scene_id, "mode": "b", "activity_profile": "p4_story_v0",
                "drive_mode": "manual",
                "rooms": {"pickup": {"id": int(scene["pickup"].id), "dbref": str(scene["pickup"].dbref)},
                          "destination": {"id": int(scene["destination"].id), "dbref": str(scene["destination"].dbref)}},
                "roles": {"courier": {"id": int(scene["courier"].id), "dbref": str(scene["courier"].dbref),
                                        "ensemble_role": "hero"},
                          "resident": {"id": int(scene["resident"].id), "dbref": str(scene["resident"].dbref),
                                         "ensemble_role": "love"},
                          "player": {"id": int(player.id), "dbref": str(player.dbref)}},
                "items": {"courier_supply": {"id": int(supply.id), "dbref": str(supply.dbref), "key": str(supply.key)},
                          "resident_parcel": {"id": int(parcel.id), "dbref": str(parcel.dbref), "key": str(parcel.key)}},
                "initial_clock": {"now": 0, "unit": "simulated-minute", "step_minutes": 1,
                                  "deadline": deadline},
                "initial_east_closed": initial_east_closed,
                "ensemble_source_manifest": native_source_manifest(),
            },
        }

    @defer.inlineCallbacks
    def _p4_player_intervention(self, scene_id, operation, item_id, label):
        from tools.native_platform_v0.p3.p4_world import append_event
        before = self._p4_snapshot(scene_id)
        receipt = yield defer.maybeDeferred(self.inject_action, {
            "scene_id": scene_id, "actor_role": "player", "operation": operation,
            "item_id": item_id,
        })
        after = self._p4_snapshot(scene_id)
        seed = next((int(obj.attributes.get("scenario_seed", category="native_p3", default=0))
                     for obj in _scene_objects(scene_id)
                     if obj.attributes.get("p4_clock", category="native_p3", default=None)), 0)
        event_id = f"p4:{seed}:player:{label}"
        args = {"label": label, "actor_role": "player",
                "actor_id": before["actors"]["player"]["id"],
                "operation": operation, "command": receipt.get("command"),
                "caller_identity": receipt.get("caller_identity"),
                "intervention_kind": receipt.get("intervention_kind"),
                "settled": receipt.get("settled"), "item_id": item_id,
                "before": before, "after": after, "command_receipt": receipt}
        event = append_event(scene_id, {"event_type": "PLAYER_INTERVENTION", "event_id": event_id,
                                        "typed_args": args, "sealed": isinstance(receipt, dict),
                                        "receipt_id": receipt.get("receipt_id", f"p4-player:{label}:{item_id}")})
        defer.returnValue({"event": event, "receipt": receipt, "before": before, "after": after})

    @defer.inlineCallbacks
    def run_p4_scenario(self, args):
        if set(args) != {"case", "director_enabled", "seed"}:
            raise ValueError("run_p4_scenario requires exactly case, director_enabled, and seed")
        case, director_enabled, seed = args["case"], args["director_enabled"], args["seed"]
        if (case not in P4_SCENARIO_NAMES or type(director_enabled) is not bool
                or type(seed) is not int or not 0 <= seed <= 2**31 - 1):
            raise ValueError("P4 case, director_enabled, or seed is invalid")
        if self.created_scenes >= MAX_SCENES_PER_PROCESS:
            raise ValueError("scene creation limit reached for this server process")
        deadline = 6 if case == "short-deadline" else 24
        created = self._create_p4_scene(case, director_enabled, seed, deadline)
        scene_id = created["scene_id"]
        self.created_scenes += 1
        scene = created["scene"]
        supply_id = int(scene["supply"].id)
        from tools.native_platform_v0.p3.p4_world import append_event, seal_ledger

        scene_event_args = {"case": case, "director_enabled": director_enabled, "seed": seed,
                            "activity_profile": "p4_story_v0", "drive_mode": "manual",
                            "roles": {"courier": int(scene["courier"].id),
                                      "resident": int(scene["resident"].id)},
                            "task_items": {"courier": int(scene["supply"].id),
                                           "resident": int(scene["return_parcel"].id)},
                            "east_initially_closed": case != "open", "west_modified": False}
        append_event(scene_id, {"event_type": "SCENE_CREATED",
                                "event_id": f"p4:{seed}:scene-created",
                                "typed_args": scene_event_args, "sealed": True})
        timeline = []
        for minute in range(1, deadline + 1):
            start = self._p4_round_start(scene_id)
            timeline.append({"minute": minute, "phase": "director_before_callbacks",
                             "clock": start["clock"], "director": start["director"],
                             "world_result": start["world_result"]})
            if minute == 6 and case in ("blocked-return", "short-deadline"):
                returned = yield self._p4_player_intervention(
                    scene_id, "drop", supply_id, "return_courier_supply")
                timeline.append({"minute": minute, "phase": "player_intervention_before_callbacks",
                                 **returned})
                if returned["receipt"].get("settled") is not True:
                    raise ValueError("P4 return intervention failed to settle through native drop")
            callbacks = yield self._p4_actor_callbacks(scene_id, minute)
            timeline.extend({"minute": minute, "phase": "npc_callback", **row} for row in callbacks)
            if minute == 1 and case != "open":
                stolen = yield self._p4_player_intervention(
                    scene_id, "get", supply_id, "player_takes_courier_supply")
                timeline.append({"minute": minute, "phase": "player_intervention_after_callbacks",
                                 **stolen})
                if stolen["receipt"].get("settled") is not True:
                    raise ValueError("P4 theft intervention failed to settle through native get")
        seal = seal_ledger(scene_id)
        _, objects = _load_scene(scene_id)
        pickup = next(obj for obj in objects if obj.attributes.get("p4_clock", category="native_p3", default=None))
        clock = dict(pickup.attributes.get("p4_clock", category="native_p3"))
        ledger = list(pickup.attributes.get("p4_ledger", category="native_p3", default=[]))
        actual_timeline = list(pickup.attributes.get("p4_timeline", category="native_p3", default=[]))
        final_trace = self.get_trace({"scene_id": scene_id})
        run_reasons = []
        if seal.get("unsealed_event_ids"):
            run_reasons.append("one_or_more_native_or_world_events_are_unsealed")
        if seal.get("missing_records"):
            run_reasons.append("one_or_more_expected_minute_or_actor_callback_records_are_missing")
        if seal.get("actor_failures"):
            run_reasons.extend(seal["actor_failures"])
        run_status = "COMPLETE" if seal.get("closed") is True else "INCOMPLETE"
        defer.returnValue({
            "schema": "native-p4-run-v1",
            "configuration": {"case": case, "director_enabled": director_enabled, "seed": seed,
                               "activity_profile": "p4_story_v0", "drive_mode": "manual",
                               "initial_east_closed": case != "open", "deadline_minutes": deadline,
                               "player_intervention": ("none" if case == "open" else
                                  "get courier supply after minute-1 callbacks" +
                                  ("; drop same supply before minute-6 callbacks"
                                   if case in ("blocked-return", "short-deadline") else "; retain supply"))},
            "created_scene": created["created_scene"],
            "timeline": actual_timeline,
            "trace": final_trace,
            "ledger": ledger,
            "clock": {**clock, "sealed": seal.get("closed") is True,
                      "source": "server_owned_pickup.p4_clock"},
            "ledger_sealed_through": seal,
            "callbacks_completed": True,
            "run_status": run_status,
            "run_reasons": run_reasons,
            "callback_count": deadline * 2,
            "controller_authored_npc_commands": 0,
        })

    @defer.inlineCallbacks
    def run_scenario(self, args):
        if set(args) - {"scenario", "seed"}:
            raise ValueError("run_scenario accepts only scenario and seed")
        scenario = args.get("scenario")
        seed = args.get("seed", 0)
        if scenario not in SCENARIO_NAMES or type(seed) is not int or not (0 <= seed <= 2**31 - 1):
            raise ValueError("scenario must be Aclean, Asteal-return, Bclean, or Bsteal-resident-parcel; seed must be 0..2147483647")
        mode = "b" if scenario.startswith("B") else "a"
        created = self.reset_scenario({"mode": mode, "seed": seed})
        scene_id = created["scene_id"]
        interventions = []

        def role_actor(role):
            account, objects = _load_scene(scene_id)
            return _actor_for(objects, role, account.id)

        def task_item(role):
            actor = role_actor(role)
            item_id = actor.attributes.get("task_item_id", category="native_p3")
            _, objects = _load_scene(scene_id)
            return next(obj for obj in objects if obj.id == item_id)

        if scenario == "Asteal-return":
            from tools.native_platform_v0.p3.agency import step_actor
            yield defer.maybeDeferred(step_actor, role_actor("courier"))  # plan pickup
            supply = task_item("courier")
            result = yield defer.maybeDeferred(self.inject_action, {
                "scene_id": scene_id, "actor_role": "player", "operation": "get", "item_id": int(supply.id),
            })
            interventions.append(result)
            yield defer.maybeDeferred(step_actor, role_actor("courier"))  # stale pickup rejects
            yield defer.maybeDeferred(step_actor, role_actor("courier"))  # reobserve while the parcel is still held
            interventions.append({"phase": "while_parcel_held",
                                  "actor": self.observe_actor({"scene_id": scene_id, "actor_role": "courier"}),
                                  "intervention_kind": "test-controller-observation-only"})
            result = yield defer.maybeDeferred(self.inject_action, {
                "scene_id": scene_id, "actor_role": "player", "operation": "drop", "item_id": int(supply.id),
            })
            interventions.append(result)
        elif scenario == "Bsteal-resident-parcel":
            from tools.native_platform_v0.p3.agency import step_actor
            yield defer.maybeDeferred(step_actor, role_actor("courier"))
            yield defer.maybeDeferred(step_actor, role_actor("resident"))  # both actors plan independently
            parcel = task_item("resident")
            result = yield defer.maybeDeferred(self.inject_action, {
                "scene_id": scene_id, "actor_role": "player", "operation": "get", "item_id": int(parcel.id),
            })
            interventions.append(result)
            yield defer.maybeDeferred(step_actor, role_actor("courier"))
            yield defer.maybeDeferred(step_actor, role_actor("resident"))  # missing parcel rejects
            yield defer.maybeDeferred(step_actor, role_actor("courier"))
            yield defer.maybeDeferred(step_actor, role_actor("resident"))  # must remain blocked before return
            held_trace = self.get_trace({"scene_id": scene_id})
            held_social = [obj["attributes"].get("native_social_events", [])
                           for obj in held_trace["objects"]
                           if obj["attributes"].get("p3_control_role") in ("courier", "resident")]
            interventions.append({"phase": "while_resident_parcel_held",
                                  "resident_actor": self.observe_actor({"scene_id": scene_id,
                                                                        "actor_role": "resident"}),
                                  "social_events_before_return": held_social,
                                  "intervention_kind": "test-controller-observation-only"})
            result = yield defer.maybeDeferred(self.inject_action, {
                "scene_id": scene_id, "actor_role": "player", "operation": "drop", "item_id": int(parcel.id),
            })
            interventions.append(result)

        from tools.native_platform_v0.p3.agency import get_value, step_actor
        actor_roles = ("courier", "resident") if mode == "b" else ("courier",)
        rounds = 0
        while rounds < 40:
            rounds += 1
            for role in actor_roles:
                yield defer.maybeDeferred(step_actor, role_actor(role))
            actors = [role_actor(role) for role in actor_roles]
            tasks_done = all(
                any(row.get("settled") and str(row.get("item_id")) ==
                    str(actor.attributes.get("task_item_id", category="native_p3")) and
                    row.get("after_item_room_id") == actor.attributes.get("task_destination_id", category="native_p3")
                    for row in get_value(actor, "native_receipts", []))
                for actor in actors
            )
            actors_classified = all(get_value(actor, "status") == "ACTOR_DELIVERY_SETTLED"
                                    for actor in actors)
            social_done = mode != "b" or all(get_value(actor, "social_attempted", False) for actor in actors)
            if tasks_done and actors_classified and social_done:
                break
        result = self.get_trace({"scene_id": scene_id})
        defer.returnValue({"scenario": scenario, "scene": created, "rounds_after_intervention": rounds,
                           "interventions": interventions,
                           "completed": tasks_done and actors_classified and social_done,
                           "trace": result})


class P3ControlProtocol(LineReceiver):
    delimiter = b"\n"
    MAX_LENGTH = MAX_REQUEST_BYTES

    def connectionMade(self):
        peer = self.transport.getPeer()
        self.loopback = getattr(peer, "host", None) == HOST

    def lineReceived(self, line):
        if not self.loopback:
            self._reply(None, {"ok": False, "error": "loopback connection required"})
            self.transport.loseConnection()
            return
        try:
            message = json.loads(line.decode("utf-8"))
            request_id = message.get("request_id") if isinstance(message, dict) else None
            operation = message.get("op", "invalid") if isinstance(message, dict) else "invalid"
            pending = defer.maybeDeferred(self.factory.control.dispatch, message)
        except Exception:
            self._reply(None, {"ok": False, "error": "invalid request"})
            return
        pending.addCallbacks(
            lambda result: self._reply(request_id, {"ok": True, "result": _json_safe(result)}),
            lambda failure: self._operation_failed(request_id, operation, failure),
        )

    def _operation_failed(self, request_id, operation, failure):
        from twisted.python import log
        safe_operation = operation if isinstance(operation, str) and operation.isidentifier() else "invalid"
        log.err(failure, f"Native P3 control operation failed: {safe_operation}")
        self._reply(request_id, {"ok": False, "error": "control operation failed",
                                 "error_type": failure.type.__name__})
        return None

    def _reply(self, request_id, response):
        payload = json.dumps({"request_id": request_id, **response}, ensure_ascii=False, separators=(",", ":"))
        encoded = payload.encode("utf-8")
        if len(encoded) > MAX_RESPONSE_BYTES:
            encoded = json.dumps({"request_id": request_id, "ok": False,
                                  "error": "response exceeds the configured size limit"}).encode("utf-8")
        self.sendLine(encoded)


class P3ControlFactory(Factory):
    protocol = P3ControlProtocol

    def __init__(self):
        self.control = P3Control()


def start_plugin_services(app):
    """Evennia Server service plugin entry point; binds only to IPv4 loopback."""
    service = internet.TCPServer(PORT, P3ControlFactory(), interface=HOST)
    service.setName("NativeP3LoopbackControl")
    service.setServiceParent(app)
    print(f"  Native P3 control RPC: {HOST}:{PORT}")
