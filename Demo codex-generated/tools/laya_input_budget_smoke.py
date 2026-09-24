"""Model-free guard regression using the same sequence/tokenizer contract as Laya."""

import json
import hashlib
import re
import sys
import tempfile
import threading
import types
from pathlib import Path
from unittest.mock import patch

import laya_typed_proxy as proxy
from laya_typed_proxy import (
    Bridge,
    LEGACY_PROMPT_VERSION,
    LEGACY_PROTOCOL_VERSION,
    PROMPT_VERSION,
    PROTOCOL_VERSION,
    PROXY_SOURCE_SHA256,
    live_cassette_provenance,
    proxy_identity,
    legacy_replay_hash,
    predict_without_truncation,
    request_hash,
    versioned_request,
)


class Tokenizer:
    mask_token = "[MASK]"
    mask_token_id = 3
    cls_token_id = 1
    sep_token_id = 2
    pad_token_id = 0

    def __init__(self):
        self.vocabulary = {"[CLS]": self.cls_token_id, "[SEP]": self.sep_token_id,
                           "[MASK]": self.mask_token_id}

    def __call__(self, text, add_special_tokens=False):
        # A deterministic lexical tokenizer: punctuation and quoted strings are
        # separate units, while JSON formatting whitespace still consumes tokens.
        pattern = r'\s+|[{}\[\],:]|"(?:[^"\\]|\\.)*"|[^\s{}\[\],:]+'
        ids = []
        for token in re.findall(pattern, text):
            if token not in self.vocabulary:
                self.vocabulary[token] = len(self.vocabulary) + 10
            ids.append(self.vocabulary[token])
        return {"input_ids": ids}


def install_test_laya_contract():
    common = types.ModuleType("laya.common")

    def render_options(question):
        return [key if value is None or value == "" else f"{key}: {value}"
                for key, value in question.get("crit", {}).items()]

    def build_sequence(tokenizer, state, question, max_len, head_max_len):
        # Mirror laya.common.build_sequence, including its silent head and
        # option clipping, so the guard test detects those failure modes.
        options = render_options(question)
        head = tokenizer(f"{question['t']} question: {question['ins']}",
                         add_special_tokens=False)["input_ids"]
        option_ids = [[tokenizer.mask_token_id] + tokenizer(
            " " + option.replace(tokenizer.mask_token, " "), add_special_tokens=False)["input_ids"][:48]
            for option in options]
        option_budget = head_max_len - sum(len(option) for option in option_ids)
        if option_budget < 16:
            per = max(4, (head_max_len - 16) // max(1, len(option_ids)))
            option_ids = [option[:per] for option in option_ids]
            option_budget = head_max_len - sum(len(option) for option in option_ids)
        head = head[:max(8, option_budget)]
        ids = [tokenizer.cls_token_id] + head + [tokenizer.sep_token_id]
        markers = []
        for option in option_ids:
            markers.append(len(ids))
            ids.extend(option)
        ids.append(tokenizer.sep_token_id)
        state_text = state if isinstance(state, str) else json.dumps(state, ensure_ascii=False)
        state_ids = tokenizer(state_text, add_special_tokens=False)["input_ids"]
        room = max(0, max_len - len(ids) - 1)
        ids.extend(state_ids[:room])
        ids.append(tokenizer.sep_token_id)
        return ids[:max_len], [marker for marker in markers if marker < max_len]

    common.render_options = render_options
    common.build_sequence = build_sequence
    laya = types.ModuleType("laya")
    laya.__path__ = []
    sys.modules["laya"] = laya
    sys.modules["laya.common"] = common


class Agent:
    def __init__(self):
        self.tok = Tokenizer()
        self.cfg = {"max_len": 1024, "head_max_len": 192}
        self.predict_state = None
        self.prediction_calls = 0

    def _check_question(self, _question_id, _question):
        pass

    def _to_internal(self, question):
        return {"t": question["type"], "ins": question["instructions"],
                "crit": question["criteria"]}

    def predict(self, state, _questions):
        self.prediction_calls += 1
        self.predict_state = state
        return {"answers": {"decision": {"ok": True}}}


def main():
    install_test_laya_contract()
    if PROXY_SOURCE_SHA256 != hashlib.sha256(Path(proxy.__file__).read_bytes()).hexdigest():
        raise SystemExit("proxy source identity is not the current source-file SHA-256")
    question = {"decision": {"type": "choice", "instructions": "Choose using the supplied options.",
                              "criteria": {"yes": "yes", "no": "no"}}}
    from laya.common import build_sequence
    empty, _ = build_sequence(Tokenizer(), "", {
        "t": question["decision"]["type"], "ins": question["decision"]["instructions"],
        "crit": question["decision"]["criteria"]}, 1024, 192)
    state_budget = 1024 - len(empty)
    state = None
    for count in range(1, 1200):
        candidate_state = {"known_or_stale_observations": ["x"] * count}
        expanded_candidate = json.dumps(candidate_state, ensure_ascii=False)
        compact_candidate = json.dumps(candidate_state, ensure_ascii=False, separators=(",", ":"))
        expanded_count = len(Tokenizer()(expanded_candidate, add_special_tokens=False)["input_ids"])
        compact_count = len(Tokenizer()(compact_candidate, add_special_tokens=False)["input_ids"])
        if expanded_count > state_budget >= compact_count:
            state = candidate_state
            break
    if state is None:
        raise SystemExit(f"could not find synthetic state straddling exact budget {state_budget}")
    expanded = json.dumps(state, ensure_ascii=False)
    compact = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
    tokenizer = Tokenizer()
    expanded_tokens = len(tokenizer(expanded, add_special_tokens=False)["input_ids"])
    compact_tokens = len(tokenizer(compact, add_special_tokens=False)["input_ids"])
    if not (expanded_tokens > state_budget and compact_tokens <= state_budget):
        raise SystemExit(f"synthetic fixture did not straddle budget: expanded={expanded_tokens}, compact={compact_tokens}, budget={state_budget}")

    agent = Agent()
    _answer, audit = predict_without_truncation(agent, state, question)
    if agent.predict_state != compact or audit["state_tokens"] != compact_tokens:
        raise SystemExit("guard did not pass the compact full state string to Laya")
    if audit["state_tokens"] > min(audit["state_budgets"]):
        raise SystemExit("guard admitted a state that exceeds the exact tokenizer budget")
    if audit["max_input_tokens"] != audit["state_tokens"] + (1024 - audit["state_budgets"][0]):
        raise SystemExit("audit input token count does not match the complete state and question prefix")

    max_candidates = {"next_action": {"type": "choice", "instructions": "Choose one action using only O, S, P and commitment. Use its target and duration.",
        "criteria": {name: f"{target} {duration}m" for name, target, duration in [
            ("use_phone", "phone", 25), ("shop_on_phone", "phone", 20),
            ("use_computer", "computer", 30), ("study_at_computer", "computer", 35),
            ("study_focused", "desk", 35), ("study_halfhearted", "desk", 35),
            ("rest_at_bed", "bed", 60), ("sleep_at_bed", "bed", 480),
            ("go_to_bathroom", "door", 15), ("get_meal", "door", 35),
            ("turn_light_on", "light", 1), ("turn_light_off", "light", 1),
            ("turn_off_alarm", "alarm", 1), ("open_curtain", "window", 1),
            ("close_curtain", "window", 1), ("idle", "here", 10)]}}}
    wide_agent = Agent()
    _, wide_audit = predict_without_truncation(wide_agent, {"state": "ok"}, max_candidates)
    if (len(wide_audit["option_tokens"][0]) != 16
            or max(wide_audit["option_tokens"][0]) > 48
            or wide_audit["question_head_tokens"][0]
               + sum(1 + size for size in wide_audit["option_tokens"][0]) > wide_audit["head_max_len"]):
        raise SystemExit("maximum Laya candidate surface did not fit complete question head")

    too_many_options = {"decision": {"type": "choice", "instructions": "choose",
        "criteria": {f"option_{index}": "long " * 60 for index in range(16)}}}
    option_agent = Agent()
    try:
        predict_without_truncation(option_agent, {"x": 1}, too_many_options)
    except ValueError as error:
        if "48-token limit" not in str(error):
            raise
    else:
        raise SystemExit("overlong Laya options were not rejected before predict")
    if option_agent.prediction_calls:
        raise SystemExit("overlong Laya options reached agent.predict")

    clipped_instructions = {"decision": {"type": "choice",
        "instructions": "extra " * 300, "criteria": {"sleep_at_bed": "bed 480m"}}}
    instruction_agent = Agent()
    try:
        predict_without_truncation(instruction_agent, {"x": 1}, clipped_instructions)
    except ValueError as error:
        if "instructions exceed complete question head budget" not in str(error):
            raise
    else:
        raise SystemExit("overlong Laya instructions were not rejected before predict")
    if instruction_agent.prediction_calls:
        raise SystemExit("overlong Laya instructions reached agent.predict")

    too_long = {"known_or_stale_observations": ["x"] * 500}
    try:
        predict_without_truncation(agent, too_long, question)
    except ValueError as error:
        if "exceeds model input budget" not in str(error):
            raise
    else:
        raise SystemExit("over-budget state was not rejected")
    if agent.prediction_calls != 1:
        raise SystemExit("over-budget state reached agent.predict")

    request = {"timestamp": 1, "state": {"x": 1}}
    if request_hash(versioned_request(request)) == legacy_replay_hash(request):
        raise SystemExit("v1 and v2 request hashes were not isolated")
    current_request = versioned_request(request)
    if (current_request["protocol_version"] != PROTOCOL_VERSION
            or current_request["prompt_version"] != PROMPT_VERSION):
        raise SystemExit("v2 protocol or prompt version missing from request identity")
    original_prompt = proxy.PROMPT_VERSION
    try:
        proxy.PROMPT_VERSION = original_prompt + "-changed"
        if request_hash(versioned_request(request)) == request_hash(current_request):
            raise SystemExit("prompt change did not change v2 request identity")
    finally:
        proxy.PROMPT_VERSION = original_prompt
    old_row = {"request_hash": legacy_replay_hash(request),
               "model": proxy.CHECKPOINT,
               "protocol_version": LEGACY_PROTOCOL_VERSION,
               "prompt_version": LEGACY_PROMPT_VERSION}
    replay_bridge = Bridge.__new__(Bridge)
    replay_bridge.replay_enabled = True
    replay_bridge.allow_v1_replay = False
    if replay_bridge._replay_row({old_row["request_hash"]: old_row}, current_request,
                                 request_hash(current_request)) is not None:
        raise SystemExit("default replay unexpectedly accepted a v1 cassette entry")
    replay_bridge.allow_v1_replay = True
    if replay_bridge._replay_row({old_row["request_hash"]: old_row}, current_request,
                                 request_hash(current_request)) is not old_row:
        raise SystemExit("explicit --allow-v1-replay did not permit v1 cassette compatibility")
    v2_row = {"request_hash": request_hash(current_request), **proxy_identity()}
    replay_bridge.allow_v1_replay = False
    if replay_bridge._replay_row({v2_row["request_hash"]: v2_row}, current_request,
                                 v2_row["request_hash"]) is not v2_row:
        raise SystemExit("normal v2 cassette replay failed")

    stale_source_row = {**v2_row, "proxy_source_sha256": "0" * 64}
    if replay_bridge._replay_row({stale_source_row["request_hash"]: stale_source_row}, current_request,
                                 stale_source_row["request_hash"]) is not None:
        raise SystemExit("v2 cassette from a different proxy source was accepted")

    identity_bridge = Bridge.__new__(Bridge)
    identity = identity_bridge.choose({"operation": "identity"})
    if identity != proxy_identity() or set(identity) != {
            "model", "checkpoint_revision", "protocol_version", "prompt_version", "proxy_source_sha256"}:
        raise SystemExit("identity operation did not return the canonical proxy identity")

    test_responses = {
        "next_action": {"answers": {"next_action": {"probabilities": {"wait": 1.0}}}},
        "reconsider": {"answers": {"reconsider": {"noul": 0.25}}},
        "commitment": {"answers": {"commitment": {"probabilities": {"continue": 1.0}}}},
    }

    def fake_predict(_agent, _state, questions):
        if set(questions) == {"commitment"}:
            options = questions["commitment"]["criteria"]
            probabilities = {name: 1.0 / len(options) for name in options}
            return {"answers": {"commitment": {"probabilities": probabilities}}}, {"state_tokens": 4}
        if set(questions) == {"goal_progress", "goal_obstruction", "stimulation", "uncertainty",
                              "positive_outcome", "negative_outcome", "control_restored"}:
            return {"answers": {name: {"score": 1} for name in questions}}, {"state_tokens": 4}
        question_id = next(iter(questions))
        return test_responses[question_id], {"state_tokens": 4}

    base = {"timestamp": 1, "profile": "test", "personality": {}, "state": {},
            "observation": [], "candidates": [{"action": "wait", "target": "", "reason": "test",
                                               "planned_minutes": 2}]}
    soft = {**base, "candidates": [], "operation": "soft_reconsideration",
            "running_action": {"action": "wait", "target": "", "elapsed_minutes": 1,
                               "planned_minutes": 2}}
    semantic_base = {**base, "candidates": [], "observation_deltas": [], "last_self_action": {}}
    commitment = {**semantic_base, "operation": "commitment_choice", "options": ["continue", "abandon"]}
    appraisal = {**semantic_base, "operation": "appraisal_scores", "options": []}

    with tempfile.TemporaryDirectory() as directory, \
            patch.object(proxy, "predict_without_truncation", side_effect=fake_predict), \
            patch.object(proxy.importlib.metadata, "version", return_value="test"):
        live_cases = [
            ("policy", base, "laya_typed_choice"),
            ("soft", soft, "laya_noul_soft_reconsideration"),
            ("commitment", commitment, "laya_commitment_choice"),
            ("appraisal", appraisal, "laya_appraisal_scores"),
        ]
        for name, request_row, expected_type in live_cases:
            cassette = Path(directory) / f"{name}.jsonl"
            live_bridge = Bridge.__new__(Bridge)
            live_bridge.cassette = cassette
            live_bridge.replay_enabled = False
            live_bridge.allow_v1_replay = False
            live_bridge.lock = threading.Lock()
            live_bridge.replay = {}
            live_bridge.memo = {}
            live_bridge.soft_replay = {}
            live_bridge.soft_memo = {}
            live_bridge.semantic_replay = {}
            live_bridge.semantic_memo = {}
            live_bridge.agent = object()
            live_bridge.choose(request_row)
            row = json.loads(cassette.read_text().splitlines()[0])
            if row["type"] != expected_type or row.get("proxy_source_sha256") != PROXY_SOURCE_SHA256:
                raise SystemExit(f"{name} live cassette row omitted the running proxy source hash")
            if row["proxy_source_sha256"] != live_cassette_provenance(row["token_budget"])["proxy_source_sha256"]:
                raise SystemExit(f"{name} live cassette source hash differs from canonical identity")
    print(f"laya_input_budget_smoke: PASS (expanded={expanded_tokens}, compact={compact_tokens}, state_budget={state_budget}, max_options=16)")


if __name__ == "__main__":
    main()
