#!/usr/bin/env python3
"""Posthoc LIGHT action/state consistency diagnostic; not source admission.

Uses the recorded action as an event description, so this is not label-independent
forward replay. It checks narrow state patterns and same-actor neighbor snapshots;
it cannot prove serializer timing or what a partner was shown.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import pickle
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PICKLE = ROOT / "outputs/external_assets_2026-09-06/LIGHT/light_data.pkl"
VIEW = ROOT / "02_实验/T0c_LIGHT/light_actor_local_full_v0.jsonl"
OUTPUT = ROOT / "outputs/light_source_contract_20261006/run_v1/timing_consistency.json"
PICKLE_SHA = "7c83cf49818586db9999ea67a4a6ad087afbd91c26ed629a9f00e21d0b84058f"
VIEW_SHA = "e6f214b91ed644b60543cf442fdae4255ff177d26a25fccd750ab5c7381ba195"
VIEW_ROWS = 13_463
FIELDS = ("action", "context", "available_actions", "character", "speech", "emote",
          "room_objects", "room_agents", "carrying", "wearing", "wielding")
POSSESSIONS = ("carrying", "wearing", "wielding")
FAMILIES = {"get", "drop", "wear", "remove"}
MOVEMENT_VERBS = {"go", "move", "enter", "leave", "walk", "travel", "exit"}
ARTICLES = {"a", "an", "the"}
EPISODE_ID = re.compile(r"^light::episode-(\d+)$")


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def surface(value: Any) -> str:
    """Casefold, collapse whitespace, strip at most two leading articles."""
    words = value.casefold().split() if isinstance(value, str) else []
    for _ in range(2):
        if words and words[0] in ARTICLES:
            words.pop(0)
        else:
            break
    return " ".join(words)


def actor(value: Any) -> str:
    return " ".join(value.casefold().split()) if isinstance(value, str) else ""


def parse(action: Any) -> tuple[str | None, str | None, str | None]:
    if not isinstance(action, str) or not action.strip():
        return None, None, "empty_or_nonstring_action"
    parts = action.strip().split(None, 1)
    family = parts[0].casefold()
    if family not in FAMILIES:
        return None, None, "unsupported_action_family"
    if len(parts) == 1 or not surface(parts[1]):
        return family, None, "missing_target_surface"
    if family == "get" and re.search(r"\s+from\s+", parts[1], re.I):
        return family, None, "unsupported_command_relation"
    return family, parts[1], None


def validate_episode(ep: dict[str, Any]) -> int:
    lengths = {k: len(ep[k]) for k in FIELDS if k in ep and isinstance(ep[k], (list, tuple))}
    if len(lengths) != len(FIELDS) or len(set(lengths.values())) != 1:
        raise ValueError(f"missing, non-sequence, or misaligned per-turn arrays: {lengths}")
    return next(iter(lengths.values()))


def _items(value: Any) -> list[str] | None:
    return list(value) if isinstance(value, (list, tuple)) and all(isinstance(x, str) for x in value) else None


def classify(ep: dict[str, Any], t: int, family: str, target_surface: str) -> dict[str, Any]:
    target = surface(target_surface)
    raw = {field: _items(ep[field][t]) for field in ("room_objects", *POSSESSIONS)}
    if any(values is None for values in raw.values()):
        return {"class": "malformed_state_arrays"}
    counts = {field: sum(surface(x) == target for x in values) for field, values in raw.items()}
    # Mirror historical desc_to_nodes substring risk as exclusion only, never binding.
    alias_risks = sorted({surface(x) for values in raw.values() for x in values
                          if surface(x) != target and target in surface(x) + "s"})
    if alias_risks:
        return {"class": "ambiguous_alias_risk", "counts": counts,
                "other_labels_containing_target": alias_risks}
    room, carry, worn, wielded = (counts[k] for k in ("room_objects", *POSSESSIONS))
    total = room + carry + worn + wielded
    if total > 1:
        return {"class": "ambiguous_duplicate_surface", "counts": counts}
    before, after = False, False
    if family == "get":
        before, after = room == 1 and total == 1, room == 0 and carry + worn + wielded == 1
    elif family == "drop":
        before, after = carry == 1 and room == 0, carry == 0 and room == 1
    elif family == "wear":
        before, after = carry == 1 and worn == 0, carry == 0 and worn == 1
    elif family == "remove":
        before, after = carry == 0 and worn + wielded == 1, carry == 1 and worn + wielded == 0
    label = "before_consistent" if before else "after_consistent" if after else "no_exact_state_pattern"
    return {"class": label, "counts": counts}


def _same_actor(ep: dict[str, Any], t: int, step: int) -> int | None:
    who = actor(ep["character"][t])
    i = t + step
    while who and 0 <= i < len(ep["action"]):
        if actor(ep["character"][i]) == who:
            return i
        i += step
    return None


def _commands_between(ep: dict[str, Any], a: int, b: int) -> list[dict[str, Any]]:
    return [{"raw_turn_index": i, "actor": ep["character"][i], "action": ep["action"][i]}
            for i in range(a + 1, b) if isinstance(ep["action"][i], str) and ep["action"][i].strip()]


def neighbors(ep: dict[str, Any], t: int, family: str, target: str,
              current: str) -> dict[str, Any]:
    out: dict[str, Any] = {}
    prev, nxt = _same_actor(ep, t, -1), _same_actor(ep, t, 1)
    for side, anchor in (("previous", prev), ("next", nxt)):
        if anchor is None:
            out[f"{side}_status"] = "no_same_actor_snapshot"
            continue
        between = _commands_between(ep, anchor, t) if side == "previous" else _commands_between(ep, t, anchor)
        command = ep["action"][anchor]
        state = classify(ep, anchor, family, target)
        out[f"{side}_raw_turn"] = anchor
        out[f"{side}_snapshot_action"] = command
        out[f"{side}_snapshot_state"] = state["class"]
        out[f"{side}_intervening_commands"] = between
        if between:
            status = "excluded_intervening_physical_commands"
        elif side == "previous" and command and str(command).strip():
            status = "excluded_previous_snapshot_has_physical_command"
        elif side == "next" and command and str(command).strip():
            status = "excluded_next_snapshot_has_physical_command"
        elif state["class"].startswith("ambiguous"):
            status = "anchor_ambiguous"
        elif side == "previous" and state["class"] != "before_consistent":
            status = "anchor_not_before_consistent"
        elif side == "next" and current != "before_consistent":
            status = "current_not_before_consistent"
        elif side == "previous" and current == "after_consistent":
            status = "pre_to_current_post_consistent"
        elif side == "next" and state["class"] == "after_consistent":
            status = "current_pre_to_next_post_consistent"
        else:
            status = "no_expected_pre_to_post_transition"
        out[f"{side}_status"] = status
    return out


def diagnose_event(ep: dict[str, Any], t: int) -> dict[str, Any]:
    family, target, reason = parse(ep["action"][t])
    if reason:
        return {"included": False, "family": family, "reason": reason}
    assert family and target
    state = classify(ep, t, family, target)
    return {"included": True, "family": family, "target_surface": target,
            "current_state": state,
            "neighbors": neighbors(ep, t, family, target, state["class"])}


def verify_cohort(episodes: list[dict[str, Any]], raw: bytes) -> tuple[set[tuple[int, int]], dict[tuple[int, int], int]]:
    keys: set[tuple[int, int]] = set()
    lines: dict[tuple[int, int], int] = {}
    for line_no, line in enumerate(raw.decode("utf-8").splitlines(), 1):
        row = json.loads(line)
        match = EPISODE_ID.fullmatch(row.get("trajectory_id", ""))
        if not match:
            raise ValueError(f"invalid trajectory id at frozen view line {line_no}")
        ei = int(match.group(1))
        physical = [i for i, a in enumerate(episodes[ei]["action"]) if isinstance(a, str) and a.strip()]
        index = row.get("target_step_index")
        if not isinstance(index, int) or not 0 <= index < len(physical):
            raise ValueError(f"invalid physical target index at frozen view line {line_no}")
        t = physical[index]
        ep = episodes[ei]
        if (row.get("source_action_A_star") != ep["action"][t] or row.get("source_O") != ep["context"][t]
                or row.get("candidate_set_factual") != ep["available_actions"][t]
                or actor(row.get("actor")) != actor(ep["character"][t])):
            raise ValueError(f"frozen view join mismatch at line {line_no}")
        key = (ei, t)
        if key in keys:
            raise ValueError(f"duplicate cohort key at line {line_no}")
        keys.add(key)
        lines[key] = line_no
    if len(keys) != VIEW_ROWS:
        raise ValueError(f"expected {VIEW_ROWS} cohort rows; found {len(keys)}")
    return keys, lines


def _example(ep: dict[str, Any], ei: int, t: int, event: dict[str, Any], line: int | None) -> dict[str, Any]:
    refs = event.get("neighbors", {})
    turns = list(dict.fromkeys(x for x in (refs.get("previous_raw_turn"), t,
                                           refs.get("next_raw_turn")) if x is not None))
    snapshots = [{"raw_turn_index": i, "actor": ep["character"][i], "action": ep["action"][i],
                  "room_objects": ep["room_objects"][i], "carrying": ep["carrying"][i],
                  "wearing": ep["wearing"][i], "wielding": ep["wielding"][i],
                  "context": ep["context"][i],
                  "available_actions_reread_only": ep["available_actions"][i]} for i in turns]
    return {"episode_index": ei, "raw_turn_index": t, "actor": ep["character"][t],
            "frozen_view_line": line, "diagnostic": event, "snapshots": snapshots}


def _example_category(event: dict[str, Any]) -> str:
    if not event["included"]:
        return "excluded:" + event["reason"]
    n = event["neighbors"]
    if n["next_status"] == "current_pre_to_next_post_consistent":
        return "isolated_current_pre_to_next_post"
    if n["previous_status"] == "pre_to_current_post_consistent":
        return "isolated_previous_pre_to_current_post"
    return event["current_state"]["class"]


def run(episodes: list[dict[str, Any]], cohort: set[tuple[int, int]],
        lines: dict[tuple[int, int], int]) -> dict[str, Any]:
    scopes = {name: {"physical_targets": 0, "families": collections.Counter(),
                     "states": collections.Counter(), "neighbors": collections.Counter(),
                     "movement_verbs": collections.Counter(),
                     "examples": collections.defaultdict(list)}
              for name in ("all_source", "frozen_target_cohort")}
    for ei, ep in enumerate(episodes):
        validate_episode(ep)
        for t, action_value in enumerate(ep["action"]):
            if not isinstance(action_value, str) or not action_value.strip():
                continue
            event = diagnose_event(ep, t)
            keys = ["all_source"] + (["frozen_target_cohort"] if (ei, t) in cohort else [])
            state = event["current_state"]["class"] if event["included"] else "excluded:" + event["reason"]
            for name in keys:
                s = scopes[name]
                s["physical_targets"] += 1
                first_verb = action_value.strip().split(None, 1)[0].casefold()
                if first_verb in MOVEMENT_VERBS:
                    s["movement_verbs"][first_verb] += 1
                family = event["family"] or "unsupported"
                s["families"][family] += 1
                s["states"][state] += 1
                if event["included"]:
                    for side in ("previous", "next"):
                        s["neighbors"][side + ":" + event["neighbors"][side + "_status"]] += 1
                example_key = _example_category(event)
                if len(s["examples"][example_key]) < 2:
                    s["examples"][example_key].append(_example(ep, ei, t, event, lines.get((ei, t))))
    return {name: {"physical_targets": s["physical_targets"],
                   "family_counts": dict(sorted(s["families"].items())),
                   "current_state_counts": dict(sorted(s["states"].items())),
                   "same_actor_neighbor_counts": dict(sorted(s["neighbors"].items())),
                   "movement_like_first_token_counts": dict(sorted(s["movement_verbs"].items())),
                   "examples": dict(sorted(s["examples"].items()))}
            for name, s in scopes.items()}


def structural_counts(episodes: list[dict[str, Any]]) -> dict[str, Any]:
    turns = sum(len(ep["action"]) for ep in episodes)
    wearing = sum(bool(ep["wearing"][t]) for ep in episodes for t in range(len(ep["action"])))
    wielding = sum(bool(ep["wielding"][t]) for ep in episodes for t in range(len(ep["action"])))
    ctx_wearing = sum("wearing " in str(ep["context"][t] or "").casefold()
                      for ep in episodes for t in range(len(ep["action"])))
    ctx_wielding = sum("wielding " in str(ep["context"][t] or "").casefold()
                       for ep in episodes for t in range(len(ep["action"])))
    remove = empty_remove = 0
    for ep in episodes:
        for t, a in enumerate(ep["action"]):
            family, _, _ = parse(a)
            if family == "remove":
                remove += 1
                empty_remove += all(not ep[k][t] for k in POSSESSIONS)
    return {"raw_turns": turns, "nonempty_wearing_snapshots": wearing,
            "nonempty_wielding_snapshots": wielding,
            "context_literal_wearing_mentions": ctx_wearing,
            "context_literal_wielding_mentions": ctx_wielding,
            "remove_actions": remove,
            "remove_actions_with_all_possession_arrays_empty": empty_remove,
            "context_interpretation": "Literal substring counts only; they do not validate or refute dedicated per-turn arrays."}


def synthetic_episode(actions: list[Any], characters: list[Any], room: list[Any],
                      carrying: list[Any], wearing: list[Any] | None = None,
                      wielding: list[Any] | None = None) -> dict[str, Any]:
    n = len(actions)
    return {"action": actions, "character": characters,
            "context": [f"context-{i}" for i in range(n)],
            "available_actions": [["synthetic"] for _ in range(n)],
            "speech": [None] * n, "emote": [None] * n,
            "room_objects": room, "room_agents": [[] for _ in range(n)],
            "carrying": carrying,
            "wearing": wearing if wearing is not None else [[] for _ in range(n)],
            "wielding": wielding if wielding is not None else [[] for _ in range(n)]}


def output_path_guard(path: Path, inputs: tuple[Path, ...]) -> None:
    resolved = path.resolve()
    if any(resolved == source.resolve() or resolved in source.resolve().parents for source in inputs):
        raise ValueError(f"output equals or contains an input: {resolved}")
    if path.exists():
        raise FileExistsError(f"refusing existing output: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT,
                        help="exclusive JSON output; existing paths are refused")
    args = parser.parse_args()
    output_path_guard(args.output, (PICKLE, VIEW))
    pb, vb = PICKLE.read_bytes(), VIEW.read_bytes()
    psha, vsha = sha(pb), sha(vb)
    if psha != PICKLE_SHA:
        raise SystemExit(f"refusing to unpickle unexpected pickle SHA-256: {psha}")
    if vsha != VIEW_SHA:
        raise SystemExit(f"unexpected frozen-view SHA-256: {vsha}")
    episodes = pickle.loads(pb)  # only after exact source hash check
    if not isinstance(episodes, list) or not all(isinstance(ep, dict) for ep in episodes):
        raise ValueError("pinned source root/episode schema mismatch")
    physical_count = sum(sum(isinstance(a, str) and bool(a.strip()) for a in ep.get("action", []))
                         for ep in episodes)
    if len(episodes) != 10_268 or physical_count != 25_001:
        raise ValueError(f"pinned source inventory drifted: episodes={len(episodes)} physical={physical_count}")
    cohort, lines = verify_cohort(episodes, vb)
    result = {"schema": "light_snapshot_timing_consistency_v1",
              "claim_boundary": "Posthoc recorded-action consistency only; not label-independent replay, source-admission, serializer timing proof, or partner-visible-history proof.",
              "admission": {"training_authorized": False, "source_contract_admitted": False},
              "source": {"pickle_sha256": psha, "episodes": len(episodes),
                         "physical_targets": sum(sum(isinstance(a, str) and bool(a.strip()) for a in ep["action"])
                                                  for ep in episodes),
                         "schema_fields": sorted(episodes[0].keys())},
              "frozen_target_view": {"sha256": vsha, "rows_join_verified": len(cohort)},
              "method": {"recorded_action_role": "Posthoc event description defining expected state relation; not independent timing evidence.",
                         "families": sorted(FAMILIES),
                         "normalization": "Casefold + whitespace collapse + at most two leading a/an/the tokens; no binding by substring, plural, synonym, or stemming.",
                         "alias_risk_exclusion": "Exclude when target is a substring of another recorded room/possession label plus 's', reflecting historical desc_to_nodes risk; never use this to bind an entity. Other aliases/object IDs remain unknown.",
                         "multiplicity": "Preserved; multiple exact appearances or alias risk remain ambiguous.",
                         "neighbor_rule": "Same actor only. Previous anchor must have no physical command; any command between anchors excludes. Next anchor and turns between must have no physical command.",
                         "available_actions": "Read for raw examples only, never used in timing predicate.",
                         "partner_result": "Pickle has raw action and state arrays but no graph_copy; exact partner-facing result cannot be identified from this probe.",
                         "context_limit": "Context text is retained in examples but not parsed as a state oracle.",
                         "excluded": ["support/gold membership as timing evidence", "model outputs", "forward replay"]},
              "scopes": run(episodes, cohort, lines),
              "raw_structure_counts": structural_counts(episodes),
              "audit_tool_sha256": sha(Path(__file__).read_bytes()),
              "test_file_sha256": sha(Path(__file__).with_name("test_audit_light_snapshot_timing_v1.py").read_bytes())}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({"pickle_sha256": psha, "view_sha256": vsha,
                      "all_source": result["scopes"]["all_source"]["physical_targets"],
                      "cohort": result["scopes"]["frozen_target_cohort"]["physical_targets"],
                      "output": str(args.output)}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
