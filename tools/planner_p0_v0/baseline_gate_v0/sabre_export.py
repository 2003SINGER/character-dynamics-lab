"""Baseline-gate domains derived from the frozen integration-v0 projection."""
from __future__ import annotations

from pathlib import Path

from tools.planner_p0_v0.integration_v0.sabre_export import render_problem as _frozen_render


def render_problem(snapshot: dict, variant: str) -> str:
    if variant not in {"A", "B"}:
        raise ValueError("variant must be A (atomic) or B (existing HTN macro)")
    text = _frozen_render(snapshot)
    # Shared once-only monitor alignment: both variants must encode the same
    # one-observation/one-witness conditions without changing native rules.
    look_start = text.index("action look(actor : character) {")
    look_end = text.index("\n};", look_start) + len("\n};")
    look_block = text[look_start:look_end]
    look_pre = "character_actions_allowed() & now() < 24;"
    if look_block.count(look_pre) != 1:
        raise ValueError("frozen look action changed; inspect before reuse")
    text = text[:look_start] + look_block.replace(
        look_pre, "character_actions_allowed() & !knows_storm(actor) & now() < 24;", 1) + text[look_end:]
    meet_pre = "character_actions_allowed() & at(A) == Inn & at(B) == Inn & now() < 24;"
    if text.count(meet_pre) != 1:
        raise ValueError("frozen meet precondition changed; inspect before reuse")
    text = text.replace(meet_pre,
                        "character_actions_allowed() & at(A) == Inn & at(B) == Inn & !met_witness() & now() < 24;", 1)
    if variant == "B":
        macro_effect = "effect: shelter_delivered() & at(A) = Inn & now() = now() + delivery_cost(source);"
        if text.count(macro_effect) != 1:
            raise ValueError("frozen delivery macro effect changed; inspect before reuse")
        return text.replace(macro_effect,
                            "effect: !kit_held(A) & shelter_delivered() & at(A) = Inn & now() = now() + delivery_cost(source);", 1)

    # A receives only the GET/MOVE/DROP decomposition that B's existing HTN
    # executes. The rest of the symbolic model is byte-for-byte shared.
    if text.count("property kit_held(character : character) : boolean;") != 1:
        raise ValueError("frozen Sabre domain changed; inspect before reusing this adapter")
    text = text.replace("property kit_held(character : character) : boolean;",
                        "property kit_held(character : character) : boolean;\n"
                        "property kit_at(place : place) : boolean;", 1)

    actor = snapshot["actors"]["A"]
    local = actor.get("local_view", {}).get("observation", {})
    item = snapshot["items"]["shelter_kit"]
    known_item_room = local.get("item_location")
    held_by_a = item.get("holder_role") == "A"
    if not held_by_a and known_item_room is not None and not (
            (actor.get("active_task") or {}).get("status") == "settled"):
        aliases = {v: k for k, v in snapshot["rooms"].items()}
        alias = aliases.get(known_item_room)
        if alias not in {"junction", "side_passage", "inn"}:
            raise ValueError("A local item knowledge points outside the fixture")
        item_alias = {"junction": "Junction", "side_passage": "SidePassage", "inn": "Inn"}[alias]
        fact = f"kit_at({item_alias});\n"
        anchor = "weather() = "
        start = text.index(";", text.index(anchor)) + 1
        text = text[:start + 1] + "\n" + fact + text[start + 1:]

    macro = '''action deliver_shelter(source : place) {
	precondition:
		character_actions_allowed() & delivery_feasible(source) & at(A) == source & task_bound() & !shelter_delivered() & now() + delivery_cost(source) <= 24;
	effect: shelter_delivered() & at(A) = Inn & now() = now() + delivery_cost(source);
};
'''
    if text.count(macro) != 1:
        raise ValueError("frozen Sabre macro differs; refusing a partial transformation")
    atomics = '''action get_shelter_kit(source : place) {
	precondition:
		character_actions_allowed() & task_bound() & at(A) == source & kit_at(source) & !kit_held(A) & now() < 24;
	effect: !kit_at(source) & kit_held(A) & now() = now() + 1;
};

action drop_shelter_kit() {
	precondition:
		character_actions_allowed() & task_bound() & at(A) == Inn & kit_held(A) & !shelter_delivered() & now() < 24;
	effect: !kit_held(A) & shelter_delivered() & now() = now() + 1;
};
'''
    text = text.replace(macro, atomics)
    if "action deliver_shelter(" in text or "action get_shelter_kit(" not in text:
        raise ValueError("atomic domain transformation failed verification")
    return text


def export_problem(snapshot: dict, variant: str, destination: str | Path) -> Path:
    out = Path(destination)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_problem(snapshot, variant), encoding="utf-8")
    return out
