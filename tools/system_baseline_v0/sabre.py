"""Finite Sabre projection for the registered P5 route opportunities only."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from tools.planner_p0_v0.sabre_baseline.runner import parse_native_output
from .model import ACTION_TO_ROUTE, Candidate, NO_OP, PlanningView, make_candidate


ROOT = Path(__file__).resolve().parents[2]
JAVA = ROOT / "_local_data/planner_p0_v0/jdk/jdk-17.0.20.1+1/Contents/Home/bin/java"
CLASSPATH = ROOT / "_local_data/planner_p0_v0/sabre/bin"
SEARCH_LIMITS = {"method": "bf", "cost": "t", "heuristic": "h+",
                 "epistemic_limit": 1, "max_visited": 200,
                 "max_generated": 5000, "time_limit_ms": 5000,
                 "author_limit": 24, "character_limit": 2,
                 "heap_min": "64m", "heap_max": "1g", "stack_size": "1m"}


def render_problem(view: PlanningView) -> str:
    """Render an explicit candidate domain; effects mean proposal, never W settlement."""
    routes = dict(view.route_open)
    targets = dict(view.hard_route_targets)
    remaining = min(view.cost_budget, 2) - view.spent_cost
    opportunity_left = view.opportunities_used < view.max_opportunities
    need = {route: bool(targets.get(route) is True and not routes[route])
            for route in ACTION_TO_ROUTE.values()}
    feasible = {}
    for route, (action, cost) in (("main_passage", ("open_main_passage", 2)),
                                  ("side_passage", ("open_side_passage", 1))):
        feasible[route] = (need[route] and action in view.allowed_world_opportunities
                           and opportunity_left and cost <= remaining)
    lines = [
        "type route;", "entity Main : route;", "entity Side : route;", "",
        "property route_open(route : route) : boolean;",
        "property needs_open(route : route) : boolean;",
        "property permitted(route : route) : boolean;",
        "property affordable(route : route) : boolean;",
        "property selected(route : route) : boolean;",
        "property opportunity_spent() : boolean;",
        "property no_route_goal() : boolean;", "",
    ]
    aliases = {"main_passage": "Main", "side_passage": "Side"}
    for route in aliases:
        alias = aliases[route]
        if routes[route]:
            lines.append(f"route_open({alias});")
        if need[route]:
            lines.append(f"needs_open({alias});")
        if feasible[route]:
            lines.extend([f"permitted({alias});", f"affordable({alias});"])
    if not any(need.values()):
        lines.append("no_route_goal();")
    if not opportunity_left or remaining <= 0:
        lines.append("opportunity_spent();")
    lines.extend([
        "", "action open_route(route : route) {", "\tprecondition:",
        "\t\tneeds_open(route) & permitted(route) & affordable(route) & !opportunity_spent();",
        "\teffect: selected(route) & opportunity_spent();", "};", "",
        "utility(): if(no_route_goal() | ((route_open(Main) | selected(Main) | !needs_open(Main)) & (route_open(Side) | selected(Side) | !needs_open(Side)))) 1 else 0;",
        "", "/* System Baseline v0: route-opening candidate model only.",
        "   selected(route) is a proposed P5 author opportunity, not a world fact.",
        "   The only world effects occur after P5 checks bundle version, permission,",
        "   budget, route state, and sealed trace frontier and returns a native receipt. */",
    ])
    return "\n".join(lines) + "\n"


def invoke_sabre(problem_path: str | Path, *, timeout_s: float = 30.0) -> dict[str, Any]:
    problem = Path(problem_path).resolve()
    if not problem.is_file() or not JAVA.is_file() or not CLASSPATH.is_dir():
        return {"status": "SABRE_UNAVAILABLE", "problem_path": str(problem),
                "error": "local Sabre problem, Java runtime, or classpath is missing"}
    command = [str(JAVA), f"-Xms{SEARCH_LIMITS['heap_min']}", f"-Xmx{SEARCH_LIMITS['heap_max']}",
               f"-Xss{SEARCH_LIMITS['stack_size']}", "-Duser.language=en", "-Duser.country=US",
               "-Duser.timezone=UTC", "-cp", str(CLASSPATH), "edu.uky.cs.nil.sabre.Main", "-v",
               "-p", str(problem), "-m", SEARCH_LIMITS["method"], "-c", SEARCH_LIMITS["cost"],
               "-h", SEARCH_LIMITS["heuristic"], "-el", str(SEARCH_LIMITS["epistemic_limit"]),
               "-vl", str(SEARCH_LIMITS["max_visited"]), "-gl", str(SEARCH_LIMITS["max_generated"]),
               "-tl", str(SEARCH_LIMITS["time_limit_ms"]), "-atl", str(SEARCH_LIMITS["author_limit"]),
               "-ctl", str(SEARCH_LIMITS["character_limit"])]
    try:
        completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True,
                                   timeout=timeout_s, check=False)
    except subprocess.TimeoutExpired as exc:
        return {"status": "PROCESS_TIMEOUT", "command": command,
                "stdout": exc.stdout or "", "stderr": exc.stderr or ""}
    parsed = parse_native_output(completed.stdout, completed.stderr)
    actions = parsed["plan_actions"]
    selected = NO_OP
    if len(actions) == 1 and actions[0].startswith("open_route("):
        route_alias = actions[0][len("open_route("):-1]
        selected = {"Main": "open_main_passage", "Side": "open_side_passage"}.get(route_alias, "INVALID")
    elif actions:
        selected = "INVALID"
    if selected == "INVALID":
        status = "UNBOUND_ACTION"
    elif parsed["status"] == "SUCCESS":
        status = "PLAN_FOUND_NOT_EXECUTION_EVIDENCE"
    elif parsed["status"] == "BUDGET_LIMIT":
        status = "SEARCH_BUDGET"
    elif parsed["status"] == "NATIVE_NO_SOLUTION":
        status = "NO_PLAN_IN_EXPORTED_DOMAIN"
    else:
        status = parsed["status"]
    return {"status": status, "selected_action": selected,
            "native_result": parsed["native_result"],
            "utility_achieved": parsed["utility_achieved"],
            "nodes_visited": parsed["nodes_visited"],
            "nodes_generated": parsed["nodes_generated"],
            "elapsed_native_text": parsed["elapsed_native_text"],
            "plan_actions": actions, "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout, "stderr": completed.stderr}


def candidate_from_result(view: PlanningView, problem: str,
                          result: dict[str, Any]) -> Candidate:
    action = result.get("selected_action", NO_OP)
    return make_candidate(view, action, problem, result, result.get("status", "UNKNOWN"))


__all__ = ["SEARCH_LIMITS", "render_problem", "invoke_sabre", "candidate_from_result"]
