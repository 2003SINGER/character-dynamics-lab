"""Isolated P0 scene and commands; all mutations run inside Evennia."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import secrets
from typing import Any
from twisted.internet import defer

from evennia.commands.command import Command
from evennia.commands.cmdset import CmdSet

from .semantics import ACTORS, HORIZON, ROOMS, ROUTES, WEATHER_AT, initial_state

CAT = "planner_p0"


def _value(obj, key, default=None):
    return obj.attributes.get(key, category=CAT, default=default)


def _put(obj, key, value):
    obj.attributes.add(key, deepcopy(value), category=CAT)


def _scene_id(scene_id: Any) -> str:
    import re
    if not isinstance(scene_id, str) or not re.fullmatch(r"p0_[0-9]{14}_[0-9a-f]{8}", scene_id):
        raise ValueError("scene_id must be an exact generated P0 identifier")
    return scene_id


def _objects(scene_id):
    from evennia.objects.models import ObjectDB
    scene_id = _scene_id(scene_id)
    rows = list(ObjectDB.objects.get_by_attribute(key="p0_scene_id", category=CAT, value=scene_id))
    if not rows:
        raise ValueError("unknown or expired P0 scene")
    return rows


def _roles(objects):
    return {str(_value(obj, "p0_role")): obj for obj in objects if _value(obj, "p0_role")}


def _root(objects):
    root = next((obj for obj in objects if _value(obj, "p0_role") == "world"), None)
    if root is None:
        raise ValueError("P0 world-state owner is missing")
    return root


def create_scene(owner_account_id: int, seed: int = 0):
    """Create a fresh, independent three-room scene with direct joint control."""
    if type(seed) is not int or not 0 <= seed <= 2**31 - 1:
        raise ValueError("seed must be an integer in [0, 2147483647]")
    from evennia import create_object
    from typeclasses.characters import Character
    from typeclasses.exits import Exit
    from typeclasses.rooms import Room

    scene_id = "p0_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "_" + secrets.token_hex(4)
    state = initial_state()
    state["scene_id"] = scene_id
    state["seed"] = seed
    state["actors"] = {}
    junction = create_object(Room, key=f"P0 Junction {scene_id}")
    passage = create_object(Room, key=f"P0 Covered Passage {scene_id}")
    inn = create_object(Room, key=f"P0 Inn {scene_id}")
    rooms = {"junction": junction, "side_passage": passage, "inn": inn}
    for alias, room in rooms.items():
        _put(room, "p0_scene_id", scene_id)
        _put(room, "p0_room_alias", alias)
        _put(room, "p0_weather", "clear")
        room.attributes.add("p0_scene_id", scene_id, category=CAT)
    exits = {}
    for name, (source, destination) in {
            "main": ("junction", "inn"), "side": ("junction", "side_passage"),
            "passage_inn": ("side_passage", "inn")}.items():
        exit_obj = create_object(Exit, key=name, location=rooms[source], destination=rooms[destination],
                                 attributes=[("p0_scene_id", scene_id, CAT),
                                             ("p0_route", name, CAT)])
        exits[name] = exit_obj
    root = create_object(Room, key=f"P0 World Ledger {scene_id}", attributes=[
        ("p0_scene_id", scene_id, CAT), ("p0_role", "world", CAT),
        ("p0_state", state, CAT), ("p0_ledger", [], CAT),
        ("p0_clock", {"now": 0, "deadline": HORIZON, "unit": "hour", "step_hours": 1}, CAT),
        ("p0_weather", "clear", CAT), ("p0_route_ids", {name: int(obj.id) for name, obj in exits.items()}, CAT),
        ("p0_room_ids", {name: int(obj.id) for name, obj in rooms.items()}, CAT),
        ("owner_account_id", owner_account_id, CAT),
        ("p0_seed", seed, CAT), ("p0_control_mode", "explicit_joint_orchestration", CAT),
    ])
    role_ids = {}
    for role in ("A", "B", "testplayer"):
        actor = create_object(Character, key=f"P0 {role} {scene_id}", location=junction,
                              attributes=[("p0_scene_id", scene_id, CAT), ("p0_role", role, CAT),
                                          ("owner_account_id", owner_account_id, CAT),
                                          ("p0_control_mode", "explicit_joint_orchestration", CAT),
                                          ("p0_known_weather", [], CAT), ("p0_last_command", None, CAT)])
        actor.cmdset.add(P0CmdSet, persistent=True)
        role_ids[role] = {"id": int(actor.id), "dbref": str(actor.dbref)}
        state["actors"][role] = {"room": "junction", "known_weather": []}
    _put(root, "p0_state", state)
    append_event(root, "SCENE_CREATED", {"state": snapshot(scene_id, owner_account_id),
                                          "control_mode": "explicit_joint_orchestration",
                                          "seed": seed})
    return {"scene_id": scene_id, "rooms": {name: {"id": int(obj.id), "dbref": str(obj.dbref)}
                                                for name, obj in rooms.items()},
            "roles": role_ids, "exits": {name: {"id": int(obj.id), "key": obj.key,
                                                   "source": _value(obj.location, "p0_room_alias"),
                                                   "destination": _value(obj.destination, "p0_room_alias")}
                                           for name, obj in exits.items()},
            "seed": seed, "deadline": HORIZON, "control_mode": "explicit_joint_orchestration"}


def _validate_scene(objects, account_id):
    root = _root(objects)
    if _value(root, "owner_account_id") != account_id:
        raise PermissionError("P0 scene owner mismatch")
    roles = _roles(objects)
    if set(ACTORS) - set(roles):
        raise ValueError("P0 scene is missing a registered role")
    return root, roles


def snapshot(scene_id: str, account_id: int) -> dict[str, Any]:
    objects = _objects(scene_id)
    root, roles = _validate_scene(objects, account_id)
    state = deepcopy(_value(root, "p0_state"))
    room_ids = _value(root, "p0_room_ids")
    for role, actor in roles.items():
        if role not in ACTORS:
            continue
        room = next((alias for alias, ident in room_ids.items()
                     if actor.location and int(actor.location.id) == int(ident)), None)
        state["actors"][role] = {"room": room,
                                 "known_weather": list(_value(actor, "p0_known_weather", [])),
                                 "last_command": deepcopy(_value(actor, "p0_last_command"))}
    state["weather"] = str(_value(root, "p0_weather", "clear"))
    state["now"] = int(_value(root, "p0_clock")["now"])
    state["deadline"] = int(_value(root, "p0_clock")["deadline"])
    state["open_routes"] = sorted(name for name, ident in _value(root, "p0_route_ids").items()
                                   if next(obj for obj in objects if int(obj.id) == int(ident))
                                   .access(roles["testplayer"], "traverse", default=True))
    state["met"] = _value(root, "p0_met", False) is True
    state["sealed_prefix_hour"] = _value(root, "p0_sealed_prefix_hour")
    return state


def append_event(root, event_type: str, fields: dict[str, Any]):
    ledger = list(_value(root, "p0_ledger", []))
    row = {"sequence": len(ledger) + 1, "event_id": f"{_value(root, 'p0_scene_id')}:{len(ledger)+1}",
           "event_type": event_type, "time": int(_value(root, "p0_clock")["now"]),
           "fields": deepcopy(fields)}
    ledger.append(deepcopy(row))
    _put(root, "p0_ledger", ledger)
    return deepcopy(row)


def _advance(objects):
    root = _root(objects)
    clock = dict(_value(root, "p0_clock"))
    before = int(clock["now"])
    if before >= int(clock["deadline"]):
        return {"before": before, "after": before, "weather_changed": False}
    clock["now"] = before + 1
    _put(root, "p0_clock", clock)
    changed = before < WEATHER_AT <= clock["now"] and _value(root, "p0_weather") != "storm"
    if changed:
        _put(root, "p0_weather", "storm")
        _, rooms = _validate_scene(objects, _value(root, "owner_account_id"))
        room_ids = _value(root, "p0_room_ids")
        from evennia.objects.models import ObjectDB
        for room_id in room_ids.values():
            room = ObjectDB.objects.get(id=int(room_id))
            _put(room, "p0_weather", "storm")
        append_event(root, "WEATHER_CHANGED", {"from": "clear", "to": "storm",
                                                "trigger_hour": WEATHER_AT,
                                                "source": "server_world_rule"})
    result = {"before": before, "after": clock["now"], "weather_changed": changed,
              "weather": _value(root, "p0_weather")}
    append_event(root, "TIME_ADVANCED", {**result, "unit": "hour", "step_hours": 1,
                                         "source": "server_clock"})
    if clock["now"] == WEATHER_AT and _value(root, "p0_sealed_prefix_hour") is None:
        current = snapshot(_value(root, "p0_scene_id"), _value(root, "owner_account_id"))
        _put(root, "p0_sealed_prefix", deepcopy(current))
        _put(root, "p0_sealed_prefix_hour", WEATHER_AT)
        append_event(root, "PREFIX_SEALED", {"hour": WEATHER_AT,
                                              "snapshot": deepcopy(current),
                                              "source": "server_world_rule"})
    return result


def _actor(objects, role):
    actor = _roles(objects).get(role)
    if actor is None or role not in ACTORS:
        raise ValueError("role must be A, B, or testplayer in this generated scene")
    return actor


@defer.inlineCallbacks
def apply_planner_action(scene_id: str, account_id: int, request_id: str,
                         action: dict[str, Any], predicted_post: dict[str, Any] | None = None):
    """Execute one requested world action, always advance one hour, then read back."""
    from evennia.objects.models import ObjectDB
    from .semantics import action_precondition, validate_action

    action = validate_action(action)
    before = snapshot(scene_id, account_id)
    root = _root(_objects(scene_id))
    append_event(root, "PLANNER_REQUEST", {"request_id": request_id, "action": action,
                                            "predicted_post": deepcopy(predicted_post),
                                            "pre": deepcopy(before), "status": "PROPOSED"})
    ok, reason = action_precondition(before, action)
    actor = _actor(_objects(scene_id), action.get("actor", "A")) if action["kind"] != "meet" else _actor(_objects(scene_id), "A")
    command = None
    native_blocked_attempt = False
    reason_before_command = reason
    ledger_before = len(_value(root, "p0_ledger", []))
    if ok:
        if action["kind"] == "wait":
            command = "p0-wait"
        elif action["kind"] == "observe_weather":
            command = "look"
        elif action["kind"] == "move":
            route = next(name for name, endpoints in ROUTES.items()
                         if endpoints == (action["from"], action["to"]))
            exits = _value(root, "p0_route_ids")
            edge = ObjectDB.objects.get(id=int(exits[route]))
            native_blocked_attempt = not edge.access(actor, "traverse", default=True)
            command = edge.key
            if native_blocked_attempt:
                ok, reason = False, "native_exit_traverse_denied"
        elif action["kind"] == "meet":
            command = "p0-meet"
    elif action["kind"] == "move" and reason == "route_blocked":
        # Attempt the actual generated Exit so rejection is native evidence, not adapter-only.
        route = next(name for name, endpoints in ROUTES.items()
                     if endpoints == (action["from"], action["to"]))
        exits = _value(root, "p0_route_ids")
        edge = ObjectDB.objects.get(id=int(exits[route]))
        if actor.location and edge.location and int(actor.location.id) == int(edge.location.id):
            command = edge.key
            native_blocked_attempt = True
    if command is not None:
        yield defer.maybeDeferred(actor.execute_cmd, command)
        if native_blocked_attempt:
            current = snapshot(scene_id, account_id)
            if current["actors"][action["actor"]]["room"] == action.get("from"):
                reason = "native_exit_traverse_denied"
            else:
                reason = "native_exit_lock_mismatch"
        if action["kind"] == "observe_weather":
            # Weather is observable only through an actual room and a real look command.
            state_after_look = snapshot(scene_id, account_id)
            if state_after_look["actors"][action["actor"]]["room"] == "junction":
                weather = str(_value(actor.location, "p0_weather", "clear"))
                known = list(_value(actor, "p0_known_weather", []))
                if weather not in known:
                    known.append(weather)
                _put(actor, "p0_known_weather", known)
                _put(actor, "p0_observation_receipt", {
                    "room": "junction", "weather": weather,
                    "world_hour": int(_value(root, "p0_clock")["now"]),
                    "source": "native_look_and_room_attribute_readback"})
                append_event(root, "WEATHER_OBSERVED", {
                    "actor": action["actor"], "room": "junction", "weather": weather,
                    "source": "native_look_and_room_attribute_readback"})
                ok, reason = True, ""
            else:
                ok, reason = False, "weather_not_visible_here"
    post_action = snapshot(scene_id, account_id)
    command_events = list(_value(root, "p0_ledger", []))[ledger_before:]
    settled = _action_settled(action, post_action, command,
                              any(e["event_type"] == "MEET_WORLD_EVENT" for e in command_events))
    if command is not None and ok and not settled:
        ok, reason = False, "native_command_not_settled"
    tick = _advance(_objects(scene_id))
    after = snapshot(scene_id, account_id)
    deltas = _state_deltas(before, after)
    row = append_event(root, "ACTION_SETTLED", {
        "request_id": request_id, "action": action, "command": command,
        "accepted": bool(ok), "reason": reason, "precondition_reason": reason_before_command,
        "settled": settled,
        "pre": deepcopy(before), "post_action": deepcopy(post_action), "post": deepcopy(after),
        "deltas": deltas, "predicted_post": deepcopy(predicted_post),
        "prediction_matches": _predicted_matches(predicted_post, after), "clock": tick,
        "author_goal_witness": _goal_witness(after),
        "evidence": "native_evennia_command_and_post_readback" if command else "executor_rejection",
    })
    defer.returnValue({"scene_id": scene_id, "request_id": request_id, "action": action,
            "accepted": bool(ok), "reason": reason, "precondition_reason": reason_before_command,
            "settled": settled,
            "pre": before, "post_action": post_action, "post": after,
            "deltas": deltas, "predicted_post": deepcopy(predicted_post),
            "prediction_matches": _predicted_matches(predicted_post, after), "clock": tick,
            "author_goal_witness": _goal_witness(after),
            "ledger_sequence": row["sequence"]})


def _predicted_matches(predicted, actual):
    if predicted is None:
        return None
    keys = {"now", "weather", "actors", "open_routes", "met"}
    if any(predicted.get(key) != actual.get(key)
           for key in keys - {"actors"} if key in predicted):
        return False
    if "actors" in predicted:
        roles = set(predicted["actors"]) | set(actual.get("actors", {}))
        for role in roles:
            want, got = predicted["actors"].get(role, {}), actual.get("actors", {}).get(role, {})
            if (want.get("room"), want.get("known_weather")) != (
                    got.get("room"), got.get("known_weather")):
                return False
    return True


def _state_deltas(before, after):
    changes = {}
    for key in ("now", "weather", "open_routes", "met", "actors"):
        before_value, after_value = before.get(key), after.get(key)
        if key == "actors":
            project = lambda rows: {role: {"room": value.get("room"),
                                           "known_weather": value.get("known_weather", [])}
                                    for role, value in rows.items()}
            before_value, after_value = project(before_value or {}), project(after_value or {})
        if before_value != after_value:
            changes[key] = {"before": deepcopy(before_value), "after": deepcopy(after_value)}
    return changes


def _action_settled(action, post_action, command, meet_event):
    if action["kind"] == "move":
        return command is not None and post_action["actors"][action["actor"]]["room"] == action["to"]
    if action["kind"] == "meet":
        return (command is not None and meet_event and
                post_action["actors"]["A"]["room"] == "inn" and
                post_action["actors"]["B"]["room"] == "inn")
    if action["kind"] == "observe_weather":
        return (command == "look" and
                post_action["weather"] in post_action["actors"][action["actor"]]["known_weather"])
    return (command == "p0-wait" and
            post_action["actors"][action["actor"]]["last_command"] ==
            {"kind": "wait", "role": action["actor"]})


def _goal_witness(state):
    return bool(state["weather"] == "storm" and "storm" in state["actors"]["B"]["known_weather"] and
                state["actors"]["A"]["room"] == "inn" and state["actors"]["B"]["room"] == "inn" and
                state["met"] is True and state["now"] <= state["deadline"])


@defer.inlineCallbacks
def inject_block(scene_id: str, account_id: int, route: str, request_id: str):
    """Use the testplayer's P0 command to lock a registered route at hour 2."""
    if route not in ("main", "side", "all"):
        raise ValueError("route must be main, side, or all")
    objects = _objects(scene_id)
    root = _root(objects)
    roles = _roles(objects)
    player = _actor(objects, "testplayer")
    before = snapshot(scene_id, account_id)
    if before["now"] != WEATHER_AT or before["sealed_prefix_hour"] != WEATHER_AT:
        raise ValueError("testplayer may block only after the hour-2 prefix has been sealed")
    if before["actors"]["testplayer"]["room"] != "junction":
        raise ValueError("testplayer must be at the junction to block routes")
    append_event(root, "PLAYER_BLOCK_REQUEST", {"request_id": request_id, "route": route,
                                                 "pre": deepcopy(before), "source": "testplayer_p0_command"})
    yield defer.maybeDeferred(player.execute_cmd, f"p0-block {route}")
    after_command = snapshot(scene_id, account_id)
    tick = _advance(_objects(scene_id))
    after = snapshot(scene_id, account_id)
    blocked = ["main", "side", "passage_inn"] if route == "all" else [route]
    settled = all(name not in after_command["open_routes"] for name in blocked)
    row = append_event(root, "PLAYER_BLOCK_SETTLED", {
        "request_id": request_id, "route": route, "pre": deepcopy(before),
        "post_action": deepcopy(after_command), "post": deepcopy(after),
        "deltas": _state_deltas(before, after), "settled": settled,
        "clock": tick, "evidence": "player_execute_cmd_exit_lock_and_readback"})
    defer.returnValue({"scene_id": scene_id, "request_id": request_id, "route": route,
            "settled": settled, "pre": before, "post_action": after_command,
            "post": after, "clock": tick, "ledger_sequence": row["sequence"]})


class _P0Command(Command):
    locks = "cmd:all()"
    help_category = "P0 Shared World"

    def _identity(self):
        scene_id = _value(self.caller, "p0_scene_id")
        role = _value(self.caller, "p0_role")
        if role not in ACTORS or not scene_id:
            self.caller.msg("This command is only available to a generated P0 role.")
            return None
        return scene_id, role


class CmdP0Wait(_P0Command):
    key = "p0-wait"
    def func(self):
        if self.args.strip():
            self.caller.msg("p0-wait takes no arguments.")
            return
        identity = self._identity()
        if identity:
            _put(self.caller, "p0_last_command", {"kind": "wait", "role": identity[1]})
            self.caller.msg("You wait.")


class CmdP0Meet(_P0Command):
    key = "p0-meet"
    def func(self):
        identity = self._identity()
        if not identity or identity[1] != "A":
            self.caller.msg("Only role A can issue the registered joint meet action.")
            return
        objects = _objects(identity[0])
        root, roles = _validate_scene(objects, _value(self.caller, "owner_account_id"))
        now = snapshot(identity[0], _value(self.caller, "owner_account_id"))
        valid = now["actors"]["A"]["room"] == "inn" and now["actors"]["B"]["room"] == "inn"
        if not valid:
            self.caller.msg("A and B are not together at the inn.")
            return
        qualifies = now["weather"] == "storm" and "storm" in now["actors"]["B"]["known_weather"]
        _put(root, "p0_met", bool(_value(root, "p0_met", False) or qualifies))
        append_event(root, "MEET_WORLD_EVENT", {
            "actors": ["A", "B"], "settled": True, "qualifying_witness": qualifies,
            "author_witness_latched": bool(_value(root, "p0_met", False)),
            "weather": now["weather"], "B_knows_weather": "storm" in now["actors"]["B"]["known_weather"],
            "condition": "same_inn_during_storm_after_B_observed"})
        self.caller.msg("A and B meet at the inn.")


class CmdP0Block(_P0Command):
    key = "p0-block"
    def func(self):
        identity = self._identity()
        route = self.args.strip().lower()
        if not identity or identity[1] != "testplayer" or route not in ("main", "side", "all"):
            self.caller.msg("Usage: p0-block main|side|all (testplayer only).")
            return
        objects = _objects(identity[0])
        root, _ = _validate_scene(objects, _value(self.caller, "owner_account_id"))
        clock = _value(root, "p0_clock")
        if int(clock["now"]) != WEATHER_AT or _value(root, "p0_sealed_prefix_hour") != WEATHER_AT:
            self.caller.msg("Routes can be blocked only after the hour-2 prefix is sealed.")
            return
        if _value(self.caller.location, "p0_room_alias") != "junction":
            self.caller.msg("The testplayer must stand at the junction to block a route.")
            return
        route_ids = _value(root, "p0_route_ids")
        names = list(route_ids) if route == "all" else [route]
        from evennia.objects.models import ObjectDB
        for name in names:
            exit_obj = ObjectDB.objects.get(id=int(route_ids[name]))
            exit_obj.locks.add("traverse:false()")
        state = deepcopy(_value(root, "p0_state"))
        state["open_routes"] = [name for name, ident in route_ids.items()
                                if ObjectDB.objects.get(id=int(ident)).access(self.caller, "traverse", default=True)]
        _put(root, "p0_state", state)
        append_event(root, "ROUTE_BLOCKED", {"route": route, "routes": names,
                                             "actor": "testplayer", "hour": WEATHER_AT,
                                             "source": "in_world_command", "sealed_prefix_unchanged": True})
        self.caller.msg(f"Route blocked: {route}.")


class P0CmdSet(CmdSet):
    key = "P0 shared-world commands"
    def at_cmdset_creation(self):
        self.add(CmdP0Wait())
        self.add(CmdP0Meet())
        self.add(CmdP0Block())


def trace(scene_id: str, account_id: int):
    objects = _objects(scene_id)
    root, _ = _validate_scene(objects, account_id)
    return {"scene_id": _scene_id(scene_id), "source": "live Evennia P0 room, Exit, actor and server ledger readback",
            "snapshot": snapshot(scene_id, account_id), "ledger": deepcopy(_value(root, "p0_ledger", [])),
            "sealed_prefix": deepcopy(_value(root, "p0_sealed_prefix")),
            "control_mode": _value(root, "p0_control_mode"), "account_fields_exported": False}
