"""Pure bounded contract shared by native executor and offline tests."""
import hashlib
import json

CAT = "planner_p0_integration_v0"
SCHEMA = "planner-p0-integration-v0"
MODES = {"free", "conditional", "direct"}
ROOMS = ("junction", "side_passage", "inn")
ROUTE_EDGES = {"main": (("junction", "inn"), ("inn", "junction")),
               "side": (("junction", "side_passage"), ("side_passage", "junction"),
                        ("side_passage", "inn"), ("inn", "side_passage"))}
HORIZON = 24
ACTION_FIELDS = {
    "wait": {"kind", "actor"}, "move": {"kind", "actor", "from", "to"},
    "get": {"kind", "actor", "item"}, "drop": {"kind", "actor", "item", "to"},
    "look": {"kind", "actor"}, "meet": {"kind", "actors"},
    "cloud_seed": {"kind"}, "open_route": {"kind", "route"},
    "offer_task": {"kind", "actor", "task"}, "dispatch_task": {"kind", "actor", "task"},
}
PRIMITIVES = {"wait", "move", "get", "drop", "look", "meet"}
AUTHOR_ACTIONS = {"cloud_seed", "open_route", "offer_task", "dispatch_task"}

def validate_action(action):
    if not isinstance(action, dict) or action.get("kind") not in ACTION_FIELDS:
        raise ValueError("action kind is not registered")
    kind = action["kind"]
    if set(action) != ACTION_FIELDS[kind]:
        raise ValueError(f"{kind} requires exactly {sorted(ACTION_FIELDS[kind])}")
    if kind in {"wait", "move", "get", "drop", "look"} and action["actor"] not in ("A", "B"):
        raise ValueError("actor must be A or B")
    if kind == "move" and (action["from"] not in ROOMS or action["to"] not in ROOMS):
        raise ValueError("move endpoints must be registered room aliases")
    if kind == "get" and action["item"] != "shelter_kit":
        raise ValueError("only shelter_kit is registered")
    if kind == "drop" and (action["item"] != "shelter_kit" or action["to"] != "inn"):
        raise ValueError("drop must settle shelter_kit at inn")
    if kind == "meet" and action["actors"] != ["A", "B"]:
        raise ValueError("meet is the registered A/B joint action")
    if kind == "open_route" and action["route"] not in ROUTE_EDGES:
        raise ValueError("route must be main or side")
    if kind in {"offer_task", "dispatch_task"} and (action["actor"] != "A" or action["task"] != "deliver_shelter"):
        raise ValueError("only A's deliver_shelter task is registered")
    return json.loads(json.dumps(action))

def request_fingerprint(driver, action):
    return hashlib.sha256(json.dumps([driver, action], sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def authorization(mode, driver, action):
    if action["kind"] in AUTHOR_ACTIONS:
        allowed = mode == "direct" or (mode == "conditional" and action["kind"] != "dispatch_task")
        return "" if allowed and driver == "author" else "ACL_DENIED"
    if driver == "trusted_driver": return "" if mode == "conditional" else "ACL_DENIED"
    if driver == "direct_driver": return "" if mode == "direct" else "ACL_DENIED"
    return "ACL_DENIED"

def precondition(state, action):
    kind, now = action["kind"], state["clock"]["now"]
    if now >= HORIZON: return "ILLEGAL_ACTION"
    if kind == "cloud_seed":
        return "" if state["weather"] == "clear" and state["pending_cloud"] is None and now <= 22 else "ILLEGAL_ACTION"
    if kind in {"move", "get", "drop", "wait", "look", "meet"}:
        if kind in {"wait", "look", "move", "get", "drop"}:
            role, actor = action["actor"], state["actors"][action["actor"]]
        if kind == "move":
            if actor["room"] != action["from"]: return "ILLEGAL_ACTION"
            if (action["from"], action["to"]) not in [e for edges in ROUTE_EDGES.values() for e in edges]: return "ILLEGAL_ACTION"
        elif kind == "get":
            task = state.get("task")
            if not task or task.get("actor") != role or task.get("status") not in {"accepted", "active", "blocked"}: return "ILLEGAL_ACTION"
            if state["item"].get("holder") == role: return "ILLEGAL_ACTION"
        elif kind == "drop":
            task = state.get("task")
            if not task or task.get("actor") != role or task.get("status") not in {"accepted", "active", "blocked"} or actor["room"] != "inn" or state["item"].get("holder") != role: return "ILLEGAL_ACTION"
        elif kind == "meet":
            if state["actors"]["A"]["room"] != "inn" or state["actors"]["B"]["room"] != "inn": return "ILLEGAL_ACTION"
        return ""
    if kind == "open_route":
        route = next((r for r in state["routes"] if r["id"] == action["route"]), None)
        return "" if route and any(not e["traversable"] for e in route["edges"]) else "ILLEGAL_ACTION"
    if kind == "offer_task": return "" if state.get("task") is None else "ILLEGAL_ACTION"
    if kind == "dispatch_task": return "" if state.get("task") is None else "ILLEGAL_ACTION"
    return "ILLEGAL_ACTION"
