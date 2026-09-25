"""Audit a captured v4 request with the checkpoint's actual tokenizer, without inference."""

import json
import pathlib
import sys

from transformers import AutoTokenizer
from laya_typed_proxy import (predict_without_truncation, policy_instructions,
                              policy_model_state, PROMPT_VERSION, PROTOCOL_VERSION)


class TokenizerOnlyAgent:
    def __init__(self, checkpoint_dir):
        with (pathlib.Path(checkpoint_dir) / "rl_agent_config.json").open() as handle:
            self.cfg = json.load(handle)
        self.tok = AutoTokenizer.from_pretrained(pathlib.Path(checkpoint_dir) / "tokenizer")

    @staticmethod
    def _to_internal(question):
        from laya.agent import Agent
        return Agent._to_internal(question)

    @staticmethod
    def _check_question(question_id, question):
        from laya.agent import Agent
        return Agent._check_question(question_id, question)

    @staticmethod
    def predict(_state, _questions):
        return {"answers": {}}


def main():
    if len(sys.argv) not in (3, 4, 5) or (len(sys.argv) >= 4 and sys.argv[3] != "--stress"):
        raise SystemExit("usage: laya_v4_token_margin_audit.py REQUEST.json|CASSETTE.jsonl CHECKPOINT_DIR [--stress V3_CASSETTE.jsonl]")
    source_text = pathlib.Path(sys.argv[1]).read_text()
    try:
        request = json.loads(source_text)
    except json.JSONDecodeError:
        request = json.loads(source_text.splitlines()[-1])
    request = request.get("request", request)
    stress = len(sys.argv) >= 4
    if stress:
        if len(sys.argv) != 5:
            raise SystemExit("--stress requires the captured v3 cassette with the real 22-fact O surface")
        v3_requests = []
        for line in pathlib.Path(sys.argv[4]).read_text().splitlines():
            try:
                captured = json.loads(line).get("request", {})
            except json.JSONDecodeError:
                continue
            if len(captured.get("observation", [])) >= 22:
                v3_requests.append(captured)
        if not v3_requests:
            raise SystemExit("v3 cassette contains no request with at least 22 O facts")
        observed = max(v3_requests, key=lambda row: sum(
            len(str(fact.get("key", ""))) + len(str(fact.get("value", "")))
            for fact in row["observation"]
        ))
        if len(observed["observation"]) != 22:
            raise SystemExit("expected the captured v3 maximum of exactly 22 O facts")
        # O, state, time, and events come from one real request. Keep the
        # captured v4 candidate set and build a legal 12-hour chronological
        # history that ends at the current nonempty action.
        names = ["study_focused", "use_computer", "study_halfhearted", "shop_on_phone",
                 "study_at_computer", "get_meal", "go_to_bathroom", "sleep_at_bed",
                 "rest_at_bed", "turn_light_off", "use_phone", "turn_off_alarm", "open_curtain"]
        outcomes = [
            ("sleep_at_bed", "bed", 1279, 350, 480, "i"),
            ("rest_at_bed", "bed", 1629, 35, 60, "i"),
            ("use_phone", "phone", 1664, 25, 25, "s"),
            ("use_computer", "computer", 1689, 30, 30, "s"),
            ("study_focused", "desk", 1719, 35, 35, "s", "coursework"),
            ("study_halfhearted", "desk", 1754, 20, 35, "i", "coursework"),
            ("get_meal", "door", 1774, 35, 35, "s"),
            ("go_to_bathroom", "door", 1809, 10, 15, "i"),
            ("turn_light_off", "light", 1819, 1, 1, "s"),
            ("turn_off_alarm", "alarm", 1820, 1, 1, "s"),
            ("shop_on_phone", "phone", 1821, 0, 20, "r"),
            ("open_curtain", "window", 1821, 1, 1, "s"),
            ("sleep_at_bed", "bed", 1822, 30, 480, "i"),
            ("rest_at_bed", "bed", 1852, 15, 60, "i"),
            ("use_computer", "computer", 1867, 0, 30, "r"),
            ("study_at_computer", "computer", 1867, 0, 35, "r"),
        ]
        request["timestamp"] = observed["timestamp"]
        request["profile"] = observed.get("profile", request["profile"])
        request["personality"] = observed.get("personality", request["personality"])
        request["state"].update(observed.get("state", {}))
        request["state"].setdefault("commitment", "none")
        request["state"].setdefault("commitment_task_id", "")
        request["state"].setdefault("commitment_reason", "")
        request["state"].setdefault("commitment_started_at_total_minutes", 0)
        request["state"].setdefault("purchase_urge", 0)
        request["state"].setdefault("commitment_suspended_decision_points", 0)
        request["observation"] = [
            [fact["key"], fact["value"], {"known": "k", "stale": "s"}.get(fact["status"], "u")]
            for fact in observed["observation"]
        ]
        request["running_action"] = {
            "action": "study_focused", "target": "desk", "started_at_total_minutes": 1867,
            "elapsed_minutes": observed["timestamp"] - 1867, "planned_minutes": 35,
        }
        request["recent_history"]["episodes"] = [list(row) for row in outcomes]
        request["recent_history"]["observed_events"] = [
            [observed["timestamp"], fact["key"], fact["value"]]
            for fact in observed.get("observation_deltas", [])[:2]
        ]
        if len(request["recent_history"]["observed_events"]) != 2:
            raise SystemExit("captured v3 maximum-O request has fewer than two observed events")
        clock_total = next((value for key, value, _status in request["observation"]
                            if key == "clock.total_minutes"), None)
        previous_end = None
        for episode in outcomes:
            action, _target, start, actual, planned, result, *_task = episode
            if start < request["timestamp"] - 12 * 60 or start + actual > request["timestamp"]:
                raise SystemExit("stress H1 episode falls outside the actor-visible 12-hour/current-time window")
            if previous_end is not None and start < previous_end:
                raise SystemExit("stress H1 episodes overlap or are out of chronological order")
            if actual > planned or (result == "r" and actual != 0):
                raise SystemExit("stress H1 contains an impossible rejected/planned duration")
            previous_end = start + actual
        if (str(clock_total) != str(request["timestamp"])
                or request["running_action"]["started_at_total_minutes"]
                   + request["running_action"]["elapsed_minutes"] != request["timestamp"]
                or any(event[0] > request["timestamp"] for event in request["recent_history"]["observed_events"])
                or not any(len(row) == 7 for row in outcomes)):
            raise SystemExit("stress clock, RunningAction, event time, or task-tag evidence is inconsistent")
        accepted = [row for row in outcomes if row[5] != "r"]
        actions = []
        for index, name in enumerate(names):
            episodes = [row for row in accepted if row[0] == name]
            minutes = sum(row[3] for row in episodes)
            if episodes:
                end_ago = observed["timestamp"] - max(row[2] + row[3] for row in episodes)
            else:
                minutes, end_ago = 10 + index, 900 + index * 10
            actions.append([name, minutes, end_ago])
        request["recent_factual_summary"]["actions"] = actions
        latest_sleep = max((row for row in accepted if row[0] == "sleep_at_bed"),
                           key=lambda row: row[2] + row[3])
        request["recent_factual_summary"]["last_sleep"] = [
            latest_sleep[3], latest_sleep[2] + latest_sleep[3]]
        for name, minutes, end_ago in actions:
            episodes = [row for row in accepted if row[0] == name]
            if episodes:
                expected_age = observed["timestamp"] - max(row[2] + row[3] for row in episodes)
                if minutes < sum(row[3] for row in episodes) or end_ago != expected_age:
                    raise SystemExit(f"H2 contradicts accepted H1 episodes for {name}")
            elif minutes <= 0 or not 720 < end_ago <= 48 * 60:
                raise SystemExit(f"H2-only action lacks a plausible older 48h episode: {name}")
        if request["recent_factual_summary"]["last_sleep"] != [
                latest_sleep[3], latest_sleep[2] + latest_sleep[3]]:
            raise SystemExit("last_sleep does not match the latest accepted sleep episode")
        if (len(request["observation"]) != 22 or request.get("running_action") is None
                or len(request.get("candidates", [])) != 13
                or len(request["recent_history"]["episodes"]) != 16
                or len(request["recent_history"]["observed_events"]) != 2
                or len(request["recent_factual_summary"]["actions"]) != 13):
            raise SystemExit("joint stress fixture must contain 22 O facts, RunningAction, 13 candidates, "
                             "16 episodes, 2 events, and 13 H2 action types")
    if "recent_history" not in request or "recent_factual_summary" not in request:
        raise SystemExit("request is not a history-bearing v4 policy request")
    criteria = {
        candidate["action"]: f"{candidate.get('target') or 'here'} {candidate['planned_minutes']}m"
        for candidate in request["candidates"]
    }
    state = policy_model_state(request)
    instructions = policy_instructions()
    agent = TokenizerOnlyAgent(sys.argv[2])
    try:
        _, audit = predict_without_truncation(agent, state, {
            "next_action": {"type": "choice", "instructions": instructions, "criteria": criteria}
        })
    except ValueError as error:
        print(json.dumps({"prompt_version": PROMPT_VERSION, "error": str(error)}, sort_keys=True))
        raise SystemExit(2)
    def tokens(value):
        compact = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return len(agent.tok(compact, add_special_tokens=False)["input_ids"])
    history = state["h"]
    sections = {
        "legend": tokens(state["legend"]),
        "time_profile_personality_state": tokens({key: state[key] for key in ("t", "id", "p", "s")}),
        "observation": tokens(state["o"]),
        "running_action": tokens(history["r"]),
        "action_codebook": tokens(history["a"]),
        "H1_episodes": tokens(history["e"]),
        "H1_events": tokens(history["v"]),
        "H2_summary": tokens(history["f"]),
        "schema_profile_time_and_structure": audit["state_tokens"] - sum((
            tokens(state["o"]), tokens({"p": state["p"], "s": state["s"]}),
            tokens(history["r"]), tokens(history["a"]), tokens(history["e"]),
            tokens(history["v"]), tokens(history["f"]),
        )),
    }
    head_margin = min(audit["head_budgets"][i] - audit["question_head_tokens"][i]
                      for i in range(len(audit["head_budgets"])))
    state_margin = min(audit["state_budgets"]) - audit["state_tokens"]
    if min(audit["candidate_counts"]) >= 13 and head_margin < 13:
        raise SystemExit(f"13-option initial-context head margin below 13 tokens: {head_margin}")
    if state_margin < 20:
        raise SystemExit(f"state token margin below 20 tokens: {state_margin}")
    print(json.dumps({
        "protocol_version": PROTOCOL_VERSION,
        "prompt_version": PROMPT_VERSION,
        "state_tokens": audit["state_tokens"],
        "state_budget": min(audit["state_budgets"]),
        "state_margin": min(audit["state_budgets"]) - audit["state_tokens"],
        "head_margin": head_margin,
        "max_input_tokens": audit["max_input_tokens"],
        "max_len": audit["max_len"],
        "question_head_tokens": audit["question_head_tokens"],
        "head_max_len": audit["head_max_len"],
        "option_mask_tokens": audit["option_mask_tokens"],
        "head_budgets": audit["head_budgets"],
        "candidate_counts": audit["candidate_counts"],
        "instruction_tokens": audit["instruction_tokens"],
        "option_tokens": audit["option_tokens"],
        "state_sections_tokens_nonadditive": sections,
        "stress_fixture": stress,
        "fixture_counts": ({
            "O_facts": len(request["observation"]),
            "H1_episodes": len(request["recent_history"]["episodes"]),
            "H1_observed_events": len(request["recent_history"]["observed_events"]),
            "H2_action_types": len(request["recent_factual_summary"]["actions"]),
            "candidates": len(request["candidates"]),
            "running_action": request["running_action"] is not None,
        } if stress else None),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
