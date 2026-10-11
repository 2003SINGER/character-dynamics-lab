"""Pure, bounded semantics for the native P0 shared-world fixture."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


SCENE_ID = "planner_p0_shared_world_v0"
ROOMS = ("junction", "side_passage", "inn")
ROUTES = {"main": ("junction", "inn"), "side": ("junction", "side_passage"),
          "passage_inn": ("side_passage", "inn")}
ACTORS = ("A", "B", "testplayer")
HORIZON = 48
WEATHER_AT = 2


def initial_state() -> dict[str, Any]:
    """Create a detached fixture state; server object IDs are bound at runtime."""
    return {"scene_id": SCENE_ID, "now": 0, "deadline": HORIZON, "weather": "clear",
            "actors": {role: {"room": "junction", "known_weather": []} for role in ACTORS},
            "open_routes": list(ROUTES), "met": False, "sealed_prefix_hour": None}


def snapshot(state: dict[str, Any]) -> dict[str, Any]:
    """Return a detached pre/post evidence snapshot."""
    return deepcopy(state)


def validate_action(action: Any) -> dict[str, Any]:
    if not isinstance(action, dict) or action.get("kind") not in {
            "wait", "observe_weather", "move", "meet"}:
        raise ValueError("action must be wait, observe_weather, move, or meet")
    kind = action["kind"]
    expected = {"wait": {"kind", "actor"}, "observe_weather": {"kind", "actor"},
                "move": {"kind", "actor", "from", "to"}, "meet": {"kind", "actors"}}[kind]
    if set(action) != expected:
        raise ValueError(f"{kind} has an invalid field set")
    if kind in ("wait", "observe_weather", "move") and action["actor"] not in ("A", "B"):
        raise ValueError("actor must be A or B")
    if kind == "move" and (action["from"] not in ROOMS or action["to"] not in ROOMS):
        raise ValueError("move endpoints must be registered room aliases")
    if kind == "meet" and action["actors"] != ["A", "B"]:
        raise ValueError("meet is the registered A/B joint action")
    return deepcopy(action)


def action_precondition(state: dict[str, Any], action: dict[str, Any]) -> tuple[bool, str]:
    """Check the fixed author/executor conditions without mutating the state."""
    action = validate_action(action)
    kind = action["kind"]
    if state["now"] >= state["deadline"]:
        return False, "deadline_reached"
    if kind == "wait":
        return True, ""
    if kind == "observe_weather":
        return (state["actors"][action["actor"]]["room"] == "junction",
                "weather_not_visible_here")
    if kind == "move":
        actor = action["actor"]
        if state["actors"][actor]["room"] != action["from"]:
            return False, "from_room_mismatch"
        route = next((name for name, endpoints in ROUTES.items()
                      if endpoints == (action["from"], action["to"])), None)
        if route is None:
            return False, "no_registered_exit"
        if route not in state["open_routes"]:
            return False, "route_blocked"
        return True, ""
    if kind == "meet":
        if state["actors"]["A"]["room"] != "inn" or state["actors"]["B"]["room"] != "inn":
            return False, "both_must_be_in_inn"
        return True, ""
    raise AssertionError(kind)


def advance(state: dict[str, Any]) -> dict[str, Any]:
    """Advance exactly one hour; weather is an authoritative world transition."""
    before = state["now"]
    state["now"] = min(state["deadline"], before + 1)
    changed = before < WEATHER_AT <= state["now"] and state["weather"] != "storm"
    if changed:
        state["weather"] = "storm"
    return {"before": before, "after": state["now"], "weather_changed": changed,
            "weather": state["weather"]}


def predict_post(state: dict[str, Any], action: dict[str, Any]) -> dict[str, Any]:
    """Predict one native tick without treating planner-requested effects as settled."""
    action = validate_action(action)
    predicted = snapshot(state)
    allowed, _ = action_precondition(predicted, action)
    pre_weather = predicted["weather"]
    if allowed and action["kind"] == "move":
        predicted["actors"][action["actor"]]["room"] = action["to"]
    elif allowed and action["kind"] == "observe_weather":
        known = predicted["actors"][action["actor"]]["known_weather"]
        if pre_weather not in known:
            known.append(pre_weather)
    elif allowed and action["kind"] == "meet":
        if (pre_weather == "storm" and
                "storm" in predicted["actors"]["B"]["known_weather"]):
            predicted["met"] = True
    advance(predicted)
    return predicted


def plan_cases() -> dict[str, list[dict[str, Any]]]:
    """Small hand-checkable action lists; these are fixture controls, not a planner."""
    def move(actor, source, dest):
        return {"kind": "move", "actor": actor, "from": source, "to": dest}
    def observe(actor):
        return {"kind": "observe_weather", "actor": actor}
    def wait(actor):
        return {"kind": "wait", "actor": actor}
    meet = {"kind": "meet", "actors": ["A", "B"]}
    clean = [wait("A"), wait("A"), observe("B"), move("A", "junction", "inn"),
             move("B", "junction", "side_passage"), move("B", "side_passage", "inn"), meet]
    repair = [wait("A"), wait("A"), observe("B"),
              move("A", "junction", "inn"),
              move("A", "junction", "side_passage"),
              move("A", "side_passage", "inn"),
              move("B", "junction", "side_passage"),
              move("B", "side_passage", "inn"), meet]
    negative = [wait("A"), wait("A"), observe("B"),
                move("A", "junction", "inn"), move("B", "junction", "side_passage"),
                move("B", "side_passage", "inn"), meet]
    return {"clean": clean, "mainblockedrepair": repair, "allblockednegative": negative}
