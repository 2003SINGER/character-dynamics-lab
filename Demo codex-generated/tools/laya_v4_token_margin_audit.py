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
    if len(sys.argv) != 3:
        raise SystemExit("usage: laya_v4_token_margin_audit.py REQUEST.json CHECKPOINT_DIR")
    request = json.loads(pathlib.Path(sys.argv[1]).read_text())
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
        "observation": tokens(state["o"]),
        "personality_and_subjective_state": tokens({"p": state["p"], "s": state["s"]}),
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
    }, sort_keys=True))


if __name__ == "__main__":
    main()
