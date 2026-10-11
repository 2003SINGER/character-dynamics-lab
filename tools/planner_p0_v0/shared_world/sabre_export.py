"""Emit a bounded Sabre problem from an authoritative P0 world snapshot."""

from __future__ import annotations

from pathlib import Path

from .semantics import HORIZON, ROOMS, ROUTES


def render_problem(state: dict) -> str:
    """Render the current P0 state; knowledge is only a receipt-backed predicate."""
    if type(state.get("now")) is not int or not 0 <= state["now"] <= HORIZON:
        raise ValueError("snapshot clock is outside the registered horizon")
    if state.get("deadline") != HORIZON:
        raise ValueError("P0 deadline is fixed and cannot be reset")
    if set(state.get("actors", {})) != {"A", "B", "testplayer"}:
        raise ValueError("snapshot roles do not match this P0 fixture")
    room_names = {"junction": "Junction", "side_passage": "SidePassage", "inn": "Inn"}
    times = [f"H{i}" for i in range(HORIZON + 1)]
    rows = [
        "type character;", "type place;", "type time;", "type weather;",
        "entity A : character;", "entity B : character;",
        *(f"entity {room_names[room]} : place;" for room in ROOMS),
        *(f"entity {hour} : time;" for hour in times),
        "entity Clear : weather;", "entity Storm : weather;", "",
        "property at(character : character) : place;",
        "property now() : time;", "property weather() : weather;",
        "property path(from : place, to : place) : boolean;",
        "property known_storm(character : character) : boolean;",
        "property met_witness() : boolean;",
        "property next_hour(from : time, to : time) : boolean;", "",
    ]
    rows.extend(f"next_hour({times[i]}, {times[i + 1]});" for i in range(HORIZON))
    rows.extend([f"now() = {times[state['now']]};",
                 f"weather() = {'Storm' if state['weather'] == 'storm' else 'Clear'};"])
    if state.get("met"):
        rows.append("met_witness();")
    for role in ("A", "B"):
        actor = state["actors"][role]
        if actor["room"] not in room_names:
            raise ValueError(f"{role} is not in a registered room")
        rows.append(f"at({role}) = {room_names[actor['room']]};")
        if "storm" in actor.get("known_weather", []):
            rows.append(f"known_storm({role});")
    for route, (source, target) in ROUTES.items():
        if route in state.get("open_routes", []):
            rows.append(f"path({room_names[source]}, {room_names[target]});")
    rows.extend([
        "", "trigger storm_at_hour_two() {", "\tprecondition:",
        "\t\tnow() == H2 & weather() == Clear;", "\teffect:",
        "\t\tweather() = Storm;", "};", "",
        "action wait(character : character, from : time, to : time) {",
        "\tprecondition: now() == from & next_hour(from, to);",
        "\teffect: now() = to;", "\tconsenting: character;", "};",
        "action observe_weather(character : character, from : time, to : time) {",
        "\tprecondition: at(character) == Junction & now() == from & next_hour(from, to);",
        "\teffect: if(weather() == Storm) known_storm(character) & now() = to else now() = to;",
        "\tconsenting: character;", "};",
        "action move(character : character, source : place, destination : place, from : time, to : time) {",
        "\tprecondition: at(character) == source & path(source, destination) & now() == from & next_hour(from, to);",
        "\teffect: at(character) = destination & now() = to;",
        "\tconsenting: character;", "};",
        "action meet(from : time, to : time) {", "\tprecondition:",
        "\t\tat(A) == Inn & at(B) == Inn & now() == from & next_hour(from, to);",
        "\teffect: if(weather() == Storm & known_storm(B)) met_witness() & now() = to else now() = to;",
        "\tconsenting: A, B;", "};",
        "", "utility():",
        "\tif(met_witness() & weather() == Storm & known_storm(B) & at(A) == Inn & at(B) == Inn) 1 else 0;",
        "utility(A): if(met_witness() & weather() == Storm & known_storm(B)) 2 elseif(at(A) == Inn) 1 else 0;",
        "utility(B): if(met_witness() & weather() == Storm & known_storm(B)) 3 elseif(at(B) == Inn & known_storm(B)) 2 elseif(known_storm(B)) 1 else 0;",
        "",
        "/* Narrow projection: known_storm is set only from the P0 observation receipt.",
        "   This is not a general Sabre belief-state model. Physical move/meet legality",
        "   has no storm or knowledge precondition; the author utility does. */",
    ])
    return "\n".join(rows) + "\n"


def export_problem(state: dict, destination: str | Path) -> Path:
    text = render_problem(state)
    out = Path(destination)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    return out

