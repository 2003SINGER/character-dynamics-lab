"""Audit a captured v4 request with the checkpoint's actual tokenizer, without inference."""

import json
import pathlib
import sys

from transformers import AutoTokenizer
from laya_typed_proxy import predict_without_truncation


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
    state = {
        "time": request["timestamp"],
        "personality": request["personality"],
        "subjective_state_and_commitment": request["state"],
        "known_or_stale_observations": request["observation"],
        "actor_local_temporal_context": {
            "running_action": request["running_action"],
            "recent_history": request["recent_history"],
            "recent_factual_summary": request["recent_factual_summary"],
        },
    }
    instructions = (
        "Choose one supplied action using only O, S, P, commitment and the actor-local factual recent history. "
        "Use its target and duration; do not invent actions or infer hidden World facts."
    )
    agent = TokenizerOnlyAgent(sys.argv[2])
    _, audit = predict_without_truncation(agent, state, {
        "next_action": {"type": "choice", "instructions": instructions, "criteria": criteria}
    })
    print(json.dumps({
        "protocol_version": "laya-typed-v4",
        "state_tokens": audit["state_tokens"],
        "state_budget": min(audit["state_budgets"]),
        "state_margin": min(audit["state_budgets"]) - audit["state_tokens"],
        "max_input_tokens": audit["max_input_tokens"],
        "max_len": audit["max_len"],
        "question_head_tokens": audit["question_head_tokens"],
        "head_max_len": audit["head_max_len"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
