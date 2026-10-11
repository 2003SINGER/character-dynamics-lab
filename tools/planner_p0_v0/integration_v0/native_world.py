"""Bounded native Evennia executor for the isolated Planner P0 integration.

This module deliberately does not modify the older P0 shared-world fixture or
P5.  All world writes occur inside the running Evennia process.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import re
import secrets
from typing import Any

from twisted.internet import defer
from evennia.commands.command import Command
from evennia.commands.cmdset import CmdSet

from .contract import (CAT, SCHEMA, MODES, ROOMS, ROUTE_EDGES, HORIZON,
                       PRIMITIVES, AUTHOR_ACTIONS, validate_action,
                       request_fingerprint, authorization as _authorization,
                       precondition as _precondition)


def _get(obj, key, default=None):
    return obj.attributes.get(key, category=CAT, default=default)


def _put(obj, key, value):
    obj.attributes.add(key, deepcopy(value), category=CAT)


def _scene_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"p0i_[0-9]{14}_[0-9a-f]{8}", value):
        raise ValueError("scene_id must be an exact generated P0 integration identifier")
    return value


def _objects(scene_id):
    from evennia.objects.models import ObjectDB
    sid = _scene_id(scene_id)
    rows = list(ObjectDB.objects.get_by_attribute(key="p0i_scene_id", category=CAT, value=sid))
    if not rows:
        raise ValueError("unknown P0 integration scene")
    return rows


def _root(rows):
    root = next((obj for obj in rows if _get(obj, "role") == "world"), None)
    if root is None:
        raise ValueError("P0 integration world owner is missing")
    return root


def _roles(rows):
    return {str(_get(obj, "role")): obj for obj in rows if _get(obj, "role")}


def _validate(rows, account_id):
    root, roles = _root(rows), _roles(rows)
    if _get(root, "owner_account_id") != account_id:
        raise PermissionError("P0 integration scene owner mismatch")
    if not {"A", "B", "player", "world"}.issubset(roles):
        raise ValueError("P0 integration scene role binding is incomplete")
    return root, roles


def _append(root, event_type, *, source, driver=None, request_id=None, actor=None,
            action=None, accepted=None, settled=None, code=None, receipt_id=None,
            typed_args=None, details=None, minute=None):
    rows = list(_get(root, "ledger", []))
    sequence = len(rows) + 1
    row = {"sequence": sequence, "event_id": f"{_get(root, 'scene_id')}:{sequence}",
           "minute": int(_get(root, "clock")["now"] if minute is None else minute),
           "event_type": event_type,
           "source": source, "driver": driver, "request_id": request_id,
           "actor": actor, "action": deepcopy(action), "accepted": accepted,
           "settled": settled, "code": code, "receipt_id": receipt_id,
           "typed_args": deepcopy(typed_args or {}), "details": deepcopy(details or {})}
    rows.append(deepcopy(row))
    _put(root, "ledger", rows)
    return row


def create_scene(owner_account_id: int, mode="free", seed=0, accept_task=True):
    if mode not in MODES:
        raise ValueError("mode must be free, conditional, or direct")
    if type(seed) is not int or not 0 <= seed <= 2**31 - 1:
        raise ValueError("seed must be an integer in [0,2147483647]")
    if type(accept_task) is not bool:
        raise ValueError("accept_task must be boolean")
    from evennia import create_object
    from typeclasses.characters import Character
    from typeclasses.exits import Exit
    from typeclasses.objects import Object
    from typeclasses.rooms import Room

    sid = "p0i_" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "_" + secrets.token_hex(4)
    rooms = {alias: create_object(Room, key=f"P0I {alias} {sid}") for alias in ROOMS}
    for alias, room in rooms.items():
        _put(room, "p0i_scene_id", sid); _put(room, "scene_id", sid); _put(room, "room_alias", alias); _put(room, "weather", "clear")
    exit_rows = {}
    for route, edges in ROUTE_EDGES.items():
        for index, (source, destination) in enumerate(edges):
            key = {("junction", "inn"): "main", ("inn", "junction"): "west",
                   ("junction", "side_passage"): "side", ("side_passage", "junction"): "back",
                   ("side_passage", "inn"): "inn", ("inn", "side_passage"): "porch"}[(source, destination)]
            edge = create_object(Exit, key=key, location=rooms[source], destination=rooms[destination],
                                 attributes=[("p0i_scene_id", sid, CAT), ("route", route, CAT)])
            exit_rows[f"{source}:{destination}"] = edge
    root = create_object(Room, key=f"P0I World {sid}", attributes=[
        ("p0i_scene_id", sid, CAT), ("role", "world", CAT), ("scene_id", sid, CAT),
        ("owner_account_id", owner_account_id, CAT), ("mode", mode, CAT), ("seed", seed, CAT),
        ("clock", {"now": 0, "deadline": HORIZON, "unit": "minute", "step_minutes": 1}, CAT),
        ("weather", "clear", CAT), ("pending_cloud", None, CAT), ("ledger", [], CAT),
        ("requests", {}, CAT), ("room_ids", {k: int(v.id) for k, v in rooms.items()}, CAT),
        ("route_exit_ids", {k: int(v.id) for k, v in exit_rows.items()}, CAT),
        ("static_edges", {str(int(room.id)): sorted({int(rooms[dst].id)
                         for edges in ROUTE_EDGES.values() for src, dst in edges if src == alias})
                         for alias, room in rooms.items()}, CAT),
        ("item_id", None, CAT), ("task", None, CAT), ("seed", seed, CAT)])
    actors = {}
    for role in ("A", "B", "player"):
        actor = create_object(Character, key=f"P0I {role} {sid}", location=rooms["junction"],
                              attributes=[("p0i_scene_id", sid, CAT), ("role", role, CAT),
                                          ("owner_account_id", owner_account_id, CAT),
                                          ("known_weather", [], CAT), ("known_closed_edges", [], CAT),
                                          ("known_item_location", int(rooms["junction"].id), CAT),
                                          ("own_goal", ("deliver_shelter" if accept_task else "other") if role == "A" else None, CAT),
                                          ("last_command", None, CAT), ("native_receipts", [], CAT)])
        actor.cmdset.add(P0IntegrationCmdSet, persistent=True)
        actors[role] = actor
    item = create_object(Object, key=f"shelter_kit {sid}", location=rooms["junction"],
                         attributes=[("p0i_scene_id", sid, CAT), ("item_alias", "shelter_kit", CAT)])
    _put(root, "item_id", int(item.id))
    _append(root, "SCENE_CREATED", source="server", details={"mode": mode, "seed": seed})
    return {"scene_id": sid, "schema": SCHEMA, "mode": mode,
            "rooms": {k: {"id": int(v.id), "dbref": str(v.dbref)} for k, v in rooms.items()},
            "actors": {k: {"id": int(v.id), "dbref": str(v.dbref)} for k, v in actors.items()},
            "item": {"id": int(item.id), "dbref": str(item.dbref), "alias": "shelter_kit"},
            "clock": {"now": 0, "deadline": HORIZON, "unit": "minute"}, "mode": mode,
            "accept_task": accept_task}


def _local_view(actor, root, roles, room_ids, item):
    room_id = int(actor.location.id) if actor.location else None
    visible_edges = []
    known_closed = set(tuple(x) for x in _get(actor, "known_closed_edges", []))
    known_graph = {str(k): list(v) for k, v in _get(actor, "known_exits", {}).items()}
    known_trav = deepcopy(_get(actor, "known_traversability", {}))
    if actor.location:
        for edge in actor.location.exits:
            if edge.destination is None or _get(edge, "p0i_scene_id") != _get(root, "scene_id"):
                continue
            dest = int(edge.destination.id)
            open_now = bool(edge.access(actor, "traverse", default=True))
            visible_edges.append({"key": edge.key, "destination_id": dest, "traversable": open_now})
    task = _get(root, "task")
    task_active = bool(task and task.get("actor") == _get(actor, "role") and
                       task.get("status") in {"accepted", "active", "blocked"})
    # Public static topology; prune only edges this actor personally observed closed.
    static = _get(root, "static_edges")
    potential = {str(src): [int(dst) for dst in dsts
                            if (int(src), int(dst)) not in known_closed]
                for src, dsts in static.items()}
    visible_items = [int(obj.id) for obj in actor.location.contents
                     if _get(obj, "p0i_scene_id") == _get(root, "scene_id") and
                     _get(obj, "item_alias") == "shelter_kit"] if actor.location else []
    held = any(int(obj.id) == item.id for obj in actor.contents)
    known_item = _get(actor, "known_item_location")
    if held:
        known_item = None
    task = _get(root, "task")
    delivered = bool(task and task.get("status") == "settled")
    return {"observation": {"room_id": room_id,
            "task_item": ({"id": str(item.id), "key": item.key} if task_active else None),
            "task_destination": int(room_ids["inn"]) if task_active else None,
            "known_exits": potential,
            "known_traversability": known_trav, "exits": visible_edges,
            "item_location": known_item, "item_held": held, "delivered": delivered,
            "visible_items": [{"id": str(i)} for i in visible_items]}}


def _record_local_observation(actor, root):
    """Persist only what this actor can currently see after a native action."""
    if not actor.location:
        return
    room_id = int(actor.location.id)
    known_graph = deepcopy(_get(actor, "known_exits", {}))
    known_trav = deepcopy(_get(actor, "known_traversability", {}))
    closed = {tuple(row) for row in _get(actor, "known_closed_edges", [])}
    known_graph.setdefault(str(room_id), [])
    known_trav.setdefault(str(room_id), {})
    for edge in actor.location.exits:
        if edge.destination is None or _get(edge, "p0i_scene_id") != _get(root, "scene_id"):
            continue
        dest = int(edge.destination.id)
        if dest not in known_graph[str(room_id)]:
            known_graph[str(room_id)].append(dest)
        traversable = bool(edge.access(actor, "traverse", default=True))
        known_trav[str(room_id)][str(dest)] = traversable
        if traversable:
            closed.discard((room_id, dest))
        else:
            closed.add((room_id, dest))
    _put(actor, "known_exits", known_graph)
    _put(actor, "known_traversability", known_trav)
    _put(actor, "known_closed_edges", [list(row) for row in sorted(closed)])
    item_id = int(_get(root, "item_id"))
    visible = any(int(obj.id) == item_id for obj in actor.location.contents)
    held = any(int(obj.id) == item_id for obj in actor.contents)
    if visible:
        _put(actor, "known_item_location", room_id)
    elif held:
        _put(actor, "known_item_location", None)
    elif _get(actor, "known_item_location") == room_id:
        # A locally witnessed item was not where expected; preserve no guessed location.
        _put(actor, "known_item_location", None)


def snapshot(scene_id: str, account_id: int):
    from evennia.objects.models import ObjectDB
    rows = _objects(scene_id); root, roles = _validate(rows, account_id)
    room_ids = _get(root, "room_ids")
    item = ObjectDB.objects.get(id=int(_get(root, "item_id")))
    actor_rows = {}
    for role in ("A", "B", "player"):
        actor = roles[role]
        inventory = [int(obj.id) for obj in actor.contents if _get(obj, "p0i_scene_id") == scene_id]
        local = _local_view(actor, root, roles, room_ids, item) if role in ("A", "B") else None
        actor_room = next((alias for alias, ident in room_ids.items()
                           if actor.location and int(actor.location.id) == int(ident)), None)
        actor_rows[role] = {"room_id": int(actor.location.id) if actor.location else None,
                            "room": actor_room,
                            "inventory_ids": inventory,
                            "known_weather": list(_get(actor, "known_weather", [])),
                            "own_goal": _get(actor, "own_goal"),
                            "active_task": deepcopy(_get(root, "task")) if role == "A" else None,
                            "local_view": local}
    routes = []
    for route, edges in ROUTE_EDGES.items():
        edge_rows = []
        for source, destination in edges:
            edge = next((x for x in rows if _get(x, "route") == route and x.location and
                         _get(x.location, "room_alias") == source and x.destination and
                         _get(x.destination, "room_alias") == destination), None)
            # room aliases are stored in the integration category
            if edge is None:
                edge = next((x for x in rows if _get(x, "route") == route and x.location and
                             _get(x.location, "room_alias") == source and x.destination and
                             _get(x.destination, "room_alias") == destination), None)
            if edge is not None:
                edge_rows.append({"from": source, "to": destination, "exit_id": int(edge.id),
                                  "traversable": bool(edge.access(roles["player"], "traverse", default=True))})
        routes.append({"id": route, "edges": edge_rows})
    clock = deepcopy(_get(root, "clock"))
    ledger = _get(root, "ledger", [])
    open_edges = []
    for route, edges in ROUTE_EDGES.items():
        for source, destination in edges:
            edge = next((x for x in rows if _get(x, "route") == route and x.location and
                         _get(x.location, "room_alias") == source and x.destination and
                         _get(x.destination, "room_alias") == destination), None)
            if edge and edge.access(roles["player"], "traverse", default=True):
                open_edges.append((source, destination))
    item_location = next((alias for alias, ident in room_ids.items()
                          if item.location and int(item.location.id) == int(ident)), None)
    holder = next((r for r in ("A", "B", "player")
                   if any(x.id == item.id for x in roles[r].contents)), None)
    return {"schema": SCHEMA, "scene_id": scene_id, "mode": _get(root, "mode"), "clock": clock,
            "weather": _get(root, "weather"), "pending_cloud": deepcopy(_get(root, "pending_cloud")),
            "rooms": deepcopy(room_ids), "actors": actor_rows,
            "items": {"shelter_kit": {"id": int(item.id),
                      "location_id": int(item.location.id) if item.location else None,
                      "holder_role": next((r for r in ("A", "B", "player")
                                           if any(x.id == item.id for x in roles[r].contents)), None)}},
            "routes": routes, "open_edges": open_edges,
            "item": {"location": item_location, "holder": holder},
            "task": deepcopy(_get(root, "task")),
            "ledger_frontier": len(ledger),
            "sealed_through": int(clock["now"])}


def _advance(root):
    clock = deepcopy(_get(root, "clock")); before = clock["now"]
    if before >= clock["deadline"]:
        return {"before": before, "after": before, "unit": "minute"}
    clock["now"] += 1; _put(root, "clock", clock)
    pending = _get(root, "pending_cloud")
    changed = bool(pending and clock["now"] >= pending["due_at"])
    if changed:
        _put(root, "pending_cloud", None); _put(root, "weather", "storm")
        for room_id in _get(root, "room_ids").values():
            from evennia.objects.models import ObjectDB
            _put(ObjectDB.objects.get(id=int(room_id)), "weather", "storm")
        _append(root, "WEATHER_CHANGED", source="server_world_rule",
                details={"from": "clear", "to": "storm", "seeded_at": pending["seeded_at"]})
    _append(root, "TIME_ADVANCED", source="server_clock",
            details={"before": before, "after": clock["now"], "unit": "minute"})
    return {"before": before, "after": clock["now"], "weather_changed": changed,
            "weather": _get(root, "weather"), "unit": "minute"}


@defer.inlineCallbacks
def step(scene_id, account_id, request_id, driver, action):
    if not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", request_id):
        raise ValueError("request_id must be a bounded identifier")
    if driver not in {"trusted_driver", "direct_driver", "author"}:
        raise ValueError("driver is not registered")
    action = validate_action(action)
    fp = request_fingerprint(driver, action)
    rows = _objects(scene_id); root, roles = _validate(rows, account_id)
    requests = deepcopy(_get(root, "requests", {}))
    if request_id in requests:
        if requests[request_id]["fingerprint"] != fp:
            raise ValueError("request_id was reused with a different payload")
        defer.returnValue(deepcopy(requests[request_id]["response"]))
    state = snapshot(scene_id, account_id)
    code = _authorization(state["mode"], driver, action)
    if code == "ACL_DENIED":
        _append(root, "ACTION_RESULT", source="permission_boundary", driver=driver,
                request_id=request_id, action=action, accepted=False, settled=False,
                code=code, details={"pre": state, "post": state})
        response = {"schema": SCHEMA, "scene_id": scene_id, "request_id": request_id,
                    "driver": driver, "action": action, "status": "REJECTED",
                    "code": code, "accepted": False, "settled": False,
                    "receipt_id": None, "pre": deepcopy(state),
                    "post_action": deepcopy(state), "post": deepcopy(state),
                    "clock": {"before": state["clock"]["now"],
                              "after": state["clock"]["now"], "unit": "minute"}}
        requests[request_id] = {"fingerprint": fp, "response": deepcopy(response)}
        _put(root, "requests", requests)
        defer.returnValue(response)
    if not code:
        code = _precondition(state, action)
    pre = deepcopy(state)
    command = None; actor = None; event_type = None; details = {}
    accepted = not bool(code); settled = False; receipt_id = None; typed_args = {}
    if accepted:
        kind = action["kind"]
        if kind in PRIMITIVES:
            role = action.get("actor", "A")
            actor = roles[role]
            command = {"wait": "p0i-wait", "look": "look", "meet": "p0i-meet",
                       "move": None, "get": None, "drop": None}[kind]
            if kind in {"get", "drop"}:
                from evennia.objects.models import ObjectDB
                command = f"{kind} {ObjectDB.objects.get(id=int(_get(root, 'item_id'))).key}"
            if kind == "move":
                edge = next((e for e in actor.location.exits if e.destination and
                             _get(e, "p0i_scene_id") == scene_id and
                             _get(e.destination, "room_alias") == action["to"]), None)
                if edge is None or _get(actor.location, "room_alias") != action["from"]:
                    accepted = False; code = "ILLEGAL_ACTION"
                else:
                    command = edge.key
            if accepted:
                _put(root, "current_request_id", request_id)
                _put(root, "current_driver", driver)
                _put(actor, "last_command", None)
                try:
                    yield defer.maybeDeferred(actor.execute_cmd, command)
                except Exception as exc:
                    accepted = False; code = "EXECUTION_FAILURE"
                    details["command_exception"] = type(exc).__name__
                _put(root, "current_request_id", None)
                _put(root, "current_driver", None)
                _record_local_observation(actor, root)
                post_action = snapshot(scene_id, account_id)
                if accepted and kind == "look":
                    room_alias = next(k for k, v in post_action["rooms"].items()
                                      if int(v) == int(actor.location.id))
                    weather = _get(actor.location, "weather", "clear")
                    known = list(_get(actor, "known_weather", []))
                    if weather not in known: known.append(weather)
                    _put(actor, "known_weather", known)
                    _put(actor, "last_weather_receipt", {"room": room_alias, "weather": weather,
                           "minute": pre["clock"]["now"], "source": "native_look_and_room_readback"})
                    event_type = "WEATHER_OBSERVED"; settled = True
                    typed_args = {"actor": role, "room": room_alias, "weather": weather}
                elif accepted and kind == "meet":
                    settled = (_get(roles["A"], "last_command") ==
                               {"kind": "meet", "actors": ["A", "B"]} and
                               all(post_action["actors"][r]["room"] == "inn" for r in ("A", "B")))
                    event_type = "MEET_SETTLED" if settled else "MEET_ATTEMPT"
                    typed_args = {"actors": ["A", "B"], "room": "inn"}
                    if settled:
                        task = _get(root, "task") or {}
                        observed = _get(roles["B"], "last_weather_receipt", {})
                        qualifies = (task.get("status") == "settled" and pre["weather"] == "storm" and
                                     observed.get("weather") == "storm" and
                                     int(observed.get("minute", HORIZON)) < pre["clock"]["now"])
                        if qualifies and not _get(root, "meeting_witness", False):
                            _put(root, "meeting_witness", True)
                            _append(root, "MEETING_WITNESS", source="native_meet_command",
                                    driver=driver, request_id=request_id, actor="A", action=action,
                                    accepted=True, settled=True,
                                    receipt_id=f"p0i:{scene_id}:{request_id}:witness",
                                    typed_args={**typed_args, "weather": "storm", "B_observed_storm": True},
                                    minute=pre["clock"]["now"])
                elif accepted and kind == "wait":
                    settled = _get(actor, "last_command") == {"kind": "wait", "role": role}
                    event_type = "WAIT_SETTLED"
                elif accepted and kind == "move":
                    settled = actor.location and _get(actor.location, "room_alias") == action["to"]
                    event_type = "MOVE_SETTLED"
                elif accepted and kind == "get":
                    item_id = int(_get(root, "item_id"))
                    was_held = pre["item"].get("holder") == role
                    was_here = pre["item"].get("location") == pre["actors"][role]["room"]
                    settled = (not was_held and was_here and any(int(x.id) == item_id for x in actor.contents))
                    event_type = "GET_SETTLED"
                elif accepted and kind == "drop":
                    item_id = int(_get(root, "item_id"))
                    from evennia.objects.models import ObjectDB
                    obj = ObjectDB.objects.get(id=item_id)
                    settled = (pre["item"].get("holder") == role and obj.location and
                               _get(obj.location, "room_alias") == "inn" and
                               not any(int(x.id) == item_id for x in actor.contents))
                    event_type = "DROP_SETTLED"
                    if settled: typed_args = {"actor": role, "item": "shelter_kit", "room": "inn"}
                if settled:
                    receipt_id = f"p0i:{scene_id}:{request_id}"
                    _append(root, event_type, source="native_evennia_readback", driver=driver,
                            request_id=request_id, actor=role, action=action, accepted=True,
                            settled=True, receipt_id=receipt_id, typed_args=typed_args)
                    rec = {"receipt_id": receipt_id, "kind": kind, "settled": True,
                           "actor": role, "item_id": _get(root, "item_id") if kind in {"get", "drop"} else None,
                           "minute": pre["clock"]["now"], "driver": driver}
                    receipts = list(_get(actor, "native_receipts", [])); receipts.append(rec)
                    _put(actor, "native_receipts", receipts)
                    task = deepcopy(_get(root, "task"))
                    if task and task.get("actor") == role and task.get("status") in {"accepted", "active", "blocked"} and kind in {"move", "get", "drop"}:
                        task.setdefault("item_progress", []).append(receipt_id)
                        task["progress_seq"] += 1
                        if kind == "get": task["held"] = True
                        if kind == "drop": task.update({"held": False, "status": "settled"})
                        _put(root, "task", task)
                else:
                    accepted = False; code = "EXECUTION_FAILURE"
        elif kind == "cloud_seed":
            now = int(pre["clock"]["now"])
            _put(root, "pending_cloud", {"seeded_at": now, "due_at": now + 2})
            event_type = "CLOUD_SEEDED"; settled = True
            receipt_id = f"p0i:{scene_id}:{request_id}"
        elif kind == "open_route":
            route = action["route"]
            for edge in rows:
                if _get(edge, "route") == route:
                    edge.locks.add("traverse:true()")
            if any(not edge.access(roles["player"], "traverse", default=True)
                   for edge in rows if _get(edge, "route") == route):
                accepted = False; code = "EXECUTION_FAILURE"
            else:
                settled = True; event_type = "ROUTE_OPENED"; typed_args = {"route": route}
                receipt_id = f"p0i:{scene_id}:{request_id}"
        elif kind in {"offer_task", "dispatch_task"}:
            own_goal = _get(roles["A"], "own_goal")
            task_id = f"task:{scene_id}:1"
            accepted_offer = kind == "dispatch_task" or own_goal == "deliver_shelter"
            event_type = "TASK_DISPATCH" if kind == "dispatch_task" else "TASK_OFFER"
            settled = True; receipt_id = f"p0i:{kind}:{scene_id}:1"
            typed_args = {"actor": "A", "task": "deliver_shelter",
                          "decision": "author_forced" if kind == "dispatch_task" else ("accepted" if accepted_offer else "refused")}
            details = {"own_goal": own_goal,
                       "decision_source": "author_forced_dispatch" if kind == "dispatch_task" else "fixed_own_goal"}
            if accepted_offer:
                _put(root, "task", {"task_id": task_id, "kind": "deliver_shelter", "actor": "A",
                    "item_id": int(_get(root, "item_id")), "goal_room": "inn", "status": "active",
                    "own_goal": own_goal, "held": False, "item_progress": [], "progress_seq": 0,
                    "decision_source": details["decision_source"]})
            else:
                accepted = False; code = "TASK_REFUSED"
    if action["kind"] == "look" and settled:
        post_action = snapshot(scene_id, account_id)
    if event_type and action["kind"] in AUTHOR_ACTIONS and settled:
        _append(root, event_type, source="authorized_author_action", driver=driver,
                request_id=request_id, action=action, accepted=bool(accepted), settled=True,
                code=code or None, receipt_id=receipt_id, typed_args=typed_args,
                details=details, minute=pre["clock"]["now"])
    post_action = snapshot(scene_id, account_id)
    clock_result = _advance(root)
    post = snapshot(scene_id, account_id)
    if accepted and not settled and not code:
        accepted = False; code = "EXECUTION_FAILURE"
    result = {"schema": SCHEMA, "scene_id": scene_id, "request_id": request_id,
              "driver": driver, "action": action,
              "status": "SETTLED" if accepted and settled else "REJECTED",
              "code": code or None, "accepted": bool(accepted), "settled": bool(settled),
              "receipt_id": receipt_id if settled else None, "pre": pre,
              "post_action": post_action, "post": post, "clock": clock_result}
    _append(root, "ACTION_RESULT", source="control_executor", driver=driver,
            request_id=request_id, action=action, accepted=accepted, settled=settled,
            code=code or None, receipt_id=result["receipt_id"],
            details={"clock": clock_result, "pre": pre, "post_action": post_action, "post": post,
                     **details})
    requests[request_id] = {"fingerprint": fp, "response": deepcopy(result)}
    _put(root, "requests", requests)
    defer.returnValue(result)


@defer.inlineCallbacks
def inject_mutation(scene_id, account_id, request_id, kind, route=None):
    if not isinstance(request_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{1,80}", request_id):
        raise ValueError("request_id must be a bounded identifier")
    if kind not in {"block_route", "dissipate_cloud"}:
        raise ValueError("mutation kind is not registered")
    if (kind == "block_route" and route not in ROUTE_EDGES) or (kind == "dissipate_cloud" and route is not None):
        raise ValueError("mutation has invalid route fields")
    rows = _objects(scene_id); root, roles = _validate(rows, account_id)
    fp = request_fingerprint("player", {"kind": kind, "route": route})
    requests = deepcopy(_get(root, "requests", {}))
    if request_id in requests:
        if requests[request_id]["fingerprint"] != fp:
            raise ValueError("request_id was reused with a different payload")
        defer.returnValue(deepcopy(requests[request_id]["response"]))
    player = roles["player"]
    before = snapshot(scene_id, account_id)
    _put(root, "current_request_id", request_id)
    if kind == "block_route":
        yield defer.maybeDeferred(player.execute_cmd, f"p0i-block {route}")
    else:
        yield defer.maybeDeferred(player.execute_cmd, "p0i-dissipate")
    _put(root, "current_request_id", None)
    after = snapshot(scene_id, account_id)
    if kind == "block_route":
        before_edges = [e["traversable"] for r in before["routes"] if r["id"] == route for e in r["edges"]]
        after_edges = [e["traversable"] for r in after["routes"] if r["id"] == route for e in r["edges"]]
        settled = any(before_edges) and not any(after_edges)
    else:
        settled = before["pending_cloud"] is not None and after["pending_cloud"] is None
    code = None if settled else "ILLEGAL_ACTION"
    row = _append(root, "MUTATION_RESULT", source="player_command", driver="player",
                  request_id=request_id, actor="player", accepted=settled, settled=settled,
                  code=code, details={"kind": kind, "route": route, "pre": before, "post": after})
    response = {"scene_id": scene_id, "request_id": request_id, "kind": kind, "route": route,
                "status": "SETTLED" if settled else "REJECTED", "code": code,
                "settled": settled, "pre": before, "post": after, "event_id": row["event_id"]}
    requests[request_id] = {"fingerprint": fp, "response": deepcopy(response)}
    _put(root, "requests", requests)
    defer.returnValue(response)


def trace(scene_id, account_id):
    rows = _objects(scene_id); root, _ = _validate(rows, account_id)
    return {"schema": SCHEMA, "scene_id": scene_id, "snapshot": snapshot(scene_id, account_id),
            "events": deepcopy(_get(root, "ledger", [])),
            "ledger_frontier": len(_get(root, "ledger", [])),
            "sealed_through": int(_get(root, "clock")["now"])}


class _P0ICmd(Command):
    locks = "cmd:all()"
    def _bound(self):
        sid, role = _get(self.caller, "p0i_scene_id"), _get(self.caller, "role")
        if not sid or role not in {"A", "B", "player"}:
            self.caller.msg("This command is only available to a generated integration role.")
            return None
        return sid, role


class CmdWait(_P0ICmd):
    key = "p0i-wait"
    def func(self):
        if self.args.strip(): return
        bound = self._bound()
        if bound: _put(self.caller, "last_command", {"kind": "wait", "role": bound[1]})


class CmdMeet(_P0ICmd):
    key = "p0i-meet"
    def func(self):
        bound = self._bound()
        if not bound or bound[1] != "A": return
        rows = _objects(bound[0]); root, roles = _validate(rows, _get(self.caller, "owner_account_id"))
        inn = int(_get(root, "room_ids")["inn"])
        if any(not a.location or int(a.location.id) != inn for a in (roles["A"], roles["B"])): return
        _put(self.caller, "last_command", {"kind": "meet", "actors": ["A", "B"]})


class CmdBlock(_P0ICmd):
    key = "p0i-block"
    def func(self):
        bound = self._bound(); route = self.args.strip()
        if (not bound or bound[1] != "player" or route not in ROUTE_EDGES or
                _get(self.caller.location, "room_alias") != "junction"): return
        rows = _objects(bound[0]); root, _ = _validate(rows, _get(self.caller, "owner_account_id"))
        edges = [e for e in rows if _get(e, "route") == route]
        changed = [e for e in edges if e.access(self.caller, "traverse", default=True)]
        for edge in changed: edge.locks.add("traverse:false()")
        if not changed: return
        _append(root, "ROUTE_BLOCKED", source="player_command", actor="player",
                request_id=_get(root, "current_request_id"),
                details={"route": route, "exit_ids": [int(e.id) for e in changed]})


class CmdDissipate(_P0ICmd):
    key = "p0i-dissipate"
    def func(self):
        bound = self._bound()
        if not bound or bound[1] != "player": return
        rows = _objects(bound[0]); root, _ = _validate(rows, _get(self.caller, "owner_account_id"))
        pending = _get(root, "pending_cloud")
        if pending:
            _put(root, "pending_cloud", None)
            _append(root, "CLOUD_DISSIPATED", source="player_command", actor="player",
                    request_id=_get(root, "current_request_id"),
                    details={"seeded_at": pending["seeded_at"], "storm_unchanged": _get(root, "weather")})


class P0IntegrationCmdSet(CmdSet):
    key = "P0 Integration commands"
    def at_cmdset_creation(self):
        for command in (CmdWait, CmdMeet, CmdBlock, CmdDissipate):
            self.add(command())
