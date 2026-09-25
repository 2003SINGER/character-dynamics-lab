"""Loopback-only bridge to the actual Laya typed-decisions checkpoint.

 C++ sends observed O, S, P/I and hard-admissible O-known A^O. Laya returns raw typed-choice
probabilities; C++ owns normalization and seeded sampling. There is no remote
inference endpoint or hidden-World input.
"""

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import pathlib
import socketserver
import threading
from urllib.parse import quote, unquote

os.environ.setdefault("USE_TF", "0")
CHECKPOINT = "convaiinnovations/laya-typed-decisions"
CHECKPOINT_REVISION = "f9ab0b228f0fc0f14d873dbc99038f135c2da1b2"
PROMPT_VERSION = "character-dynamics-laya-typed-v4.3"
PROTOCOL_VERSION = "laya-typed-v4"
LEGACY_PROTOCOL_VERSION = "laya-typed-v1"
LEGACY_PROMPT_VERSION = "character-dynamics-laya-typed-v1"
PROXY_SOURCE_SHA256 = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()


def proxy_identity():
    return {
        "model": CHECKPOINT,
        "checkpoint_revision": CHECKPOINT_REVISION,
        "protocol_version": PROTOCOL_VERSION,
        "prompt_version": PROMPT_VERSION,
        "proxy_source_sha256": PROXY_SOURCE_SHA256,
    }


def live_cassette_provenance(token_budget):
    return {**proxy_identity(), "token_budget": token_budget}


def request_hash(request):
    body = dict(request)
    body.pop("request_id", None)
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def versioned_request(request):
    """Return the request identity used by v2 cassettes and live memoization."""
    body = dict(request)
    body["protocol_version"] = PROTOCOL_VERSION
    body["prompt_version"] = PROMPT_VERSION
    return body


def legacy_replay_hash(request):
    """v1 compatibility is only consulted by an explicit offline replay."""
    body = dict(request)
    body.pop("protocol_version", None)
    body.pop("prompt_version", None)
    return request_hash(body)


def observation_fact_key(fact):
    """Accept compact v4 tuples and historical dict-shaped fixtures."""
    if isinstance(fact, (list, tuple)) and fact:
        return fact[0]
    if isinstance(fact, dict):
        return fact.get("key", "")
    return ""


def policy_instructions():
    """Keep the model-facing contract and real-tokenizer audits on one source."""
    return (
        "Schema/action table. p=[procrast,self_control,rest_pref,stimulation,task_anxiety,screen_strain,need_response,action_noise]; "
        "s=[boredom,fatigue,task_pressure,satisfaction,hunger,bathroom_urge,anxiety,screen_strain,commitment,task_id,reason,started_at,purchase_urge,suspended_count]. "
        "Choose listed target+minutes from O/S/P and actor facts; no hidden W."
    )


def policy_model_state(request):
    """Losslessly compact the model-facing state; the raw request stays in cassette."""
    personality_keys = ["procrastination", "self_control", "rest_preference", "stimulation_seeking",
                        "task_anxiety_sensitivity", "screen_strain_sensitivity", "need_response", "action_noise"]
    state_keys = ["boredom", "fatigue", "task_pressure", "satisfaction", "hunger", "bathroom_urge",
                  "anxiety", "screen_strain", "commitment", "commitment_task_id", "commitment_reason",
                  "commitment_started_at_total_minutes", "purchase_urge", "commitment_suspended_decision_points"]
    history = request["recent_history"]
    factual = request["recent_factual_summary"]
    names = []
    for episode in history["episodes"]:
        if episode[0] not in names:
            names.append(episode[0])
    for action in factual["actions"]:
        if action[0] not in names:
            names.append(action[0])
    action_ids = {name: index for index, name in enumerate(names)}
    def encode_rows(rows):
        encoded = []
        for row in rows:
            fields = []
            for value in row:
                if isinstance(value, str):
                    escaped = quote(value, safe="-._~")
                    fields.append("~" + escaped if not value or escaped != value or value.startswith("~") else value)
                else:
                    fields.append(json.dumps(value))
            encoded.append(" ".join(fields))
        return "\n".join(encoded)

    if any(any(character.isspace() for character in name) for name in names):
        raise ValueError("action names containing whitespace cannot be projected losslessly")
    episode_rows = [[action_ids[item[0]], *item[1:]] for item in history["episodes"]]
    previous_start = None
    for row in episode_rows:
        start = row[2]
        row[2] = start if previous_start is None else start - previous_start
        previous_start = start
    episodes = ";".join(encode_rows(episode_rows).splitlines())
    totals = ";".join(encode_rows([[action_ids[item[0]], *item[1:]] for item in factual["actions"]]).splitlines())
    running = request["running_action"]
    if running is not None:
        running = [running["action"], running["target"], running["started_at_total_minutes"],
                   running["elapsed_minutes"], running["planned_minutes"]]
    statuses = "".join(fact[2] for fact in request["observation"])
    status_runs = []
    for status in statuses:
        if status_runs and status_runs[-1][1] == status:
            status_runs[-1][0] += 1
        else:
            status_runs.append([1, status])
    statuses = "".join(f"{count}{status}" for count, status in status_runs)
    return {
        "t": request["timestamp"],
        "id": request["profile"],
        "legend": "O=[key,value],status count+code k=known/s=stale;h.r=[action,target,start,elapsed,planned];h.a=action names;H1 h.e=[action#,target,startΔ(first absolute),actual,planned,outcome,task?];~=empty/percent-text;s=settled,d=task_done,i=interrupted,r=rejected;h.v=[minute,key,value];H2 h.f=[48h,rows=[action#,minutes,last_end_age],sleep=[minutes,end]].",
        "p": " ".join(json.dumps(request["personality"][key]) for key in personality_keys),
        "s": [request["state"][key] for key in state_keys],
        "o": [[fact[:2] for fact in request["observation"]],
              statuses],
        "h": {
            "r": running,
            "a": " ".join(names),
            "e": episodes,
            "v": history["observed_events"],
            "f": [factual["window_h"], totals, factual["last_sleep"]],
        },
    }


def expand_policy_model_state(model_state):
    """Decode the compact model projection for a value-level round-trip contract."""
    history = model_state["h"]
    names = history["a"].split(" ") if history["a"] else []
    def decode_rows(encoded, numeric_columns):
        rows = []
        for line in encoded.split(";"):
            if not line:
                continue
            row = []
            for index, value in enumerate(line.split(" ")):
                if value.startswith("~"):
                    row.append(unquote(value[1:]))
                elif index in numeric_columns:
                    row.append(json.loads(value))
                else:
                    row.append(value)
            rows.append(row)
        return rows

    decoded_episode_rows = decode_rows(history["e"], {0, 2, 3, 4})
    previous_start = None
    for row in decoded_episode_rows:
        row[2] = row[2] if previous_start is None else previous_start + row[2]
        previous_start = row[2]
    episodes = [[names[item[0]], *item[1:]] for item in decoded_episode_rows]
    totals = [[names[item[0]], *item[1:]] for item in decode_rows(history["f"][1], {0, 1, 2})]
    running = history["r"]
    if running is not None:
        running = dict(zip(("action", "target", "start", "elapsed", "planned"), running))
        running["started_at_total_minutes"] = running.pop("start")
        running["elapsed_minutes"] = running.pop("elapsed")
        running["planned_minutes"] = running.pop("planned")
    statuses = _expand_status_runs(model_state["o"][1])
    if len(statuses) != len(model_state["o"][0]):
        raise ValueError("observation status run count does not match O facts")
    return {
        "timestamp": model_state["t"],
        "profile": model_state["id"],
        "personality": dict(zip(("procrastination", "self_control", "rest_preference", "stimulation_seeking",
                                 "task_anxiety_sensitivity", "screen_strain_sensitivity", "need_response", "action_noise"),
                                [json.loads(value) for value in model_state["p"].split()])),
        "state": dict(zip(("boredom", "fatigue", "task_pressure", "satisfaction", "hunger", "bathroom_urge",
                           "anxiety", "screen_strain", "commitment", "commitment_task_id", "commitment_reason",
                           "commitment_started_at_total_minutes", "purchase_urge", "commitment_suspended_decision_points"),
                          model_state["s"])),
        "observation": [[pair[0], pair[1], status]
                        for pair, status in zip(model_state["o"][0], statuses)],
        "running_action": running,
        "recent_history": {"episodes": episodes, "observed_events": history["v"]},
        "recent_factual_summary": {"window_h": history["f"][0], "actions": totals,
                                    "last_sleep": history["f"][2]},
    }


def _expand_status_runs(encoded):
    import re

    runs = re.findall(r"(\d+)([A-Za-z])", encoded)
    if "".join(count + code for count, code in runs) != encoded:
        raise ValueError("invalid observation status runs")
    return "".join(code * int(count) for count, code in runs)


def _token_ids(tokenizer, text):
    encoded = tokenizer(text, add_special_tokens=False)
    ids = encoded["input_ids"]
    if ids and isinstance(ids[0], list):
        if len(ids) != 1:
            raise ValueError("Laya tokenizer returned an unexpected batched sequence")
        ids = ids[0]
    return list(ids)


def predict_without_truncation(agent, state, questions):
    """Compact state and prove the actual Laya sequence contains every input token."""
    compact_state = json.dumps(state, ensure_ascii=False, separators=(",", ":"))
    try:
        from laya.common import build_sequence, render_options
        tokenizer = agent.tok
        max_len = int(agent.cfg["max_len"])
        head_max_len = int(agent.cfg["head_max_len"])
        mask_token = tokenizer.mask_token
        if not mask_token or tokenizer.mask_token_id is None or tokenizer.cls_token_id is None \
                or tokenizer.sep_token_id is None:
            raise ValueError("Laya tokenizer is missing required special tokens")
        clean_state = compact_state.replace(mask_token, " ")
        state_ids = _token_ids(tokenizer, clean_state)
        budgets = []
        actual_lengths = []
        head_lengths = []
        instruction_lengths = []
        option_lengths = []
        for question_id, question in questions.items():
            agent._check_question(question_id, question)
            internal = agent._to_internal(question)
            empty_sequence, _ = build_sequence(tokenizer, "", internal, max_len, head_max_len)
            instructions = str(internal["ins"]).replace(mask_token, " ")
            head_ids = _token_ids(tokenizer, f"{internal['t']} question: {instructions}")
            rendered_options = render_options(internal)
            if not rendered_options:
                raise ValueError("Laya question has no rendered options")
            option_token_ids = [
                _token_ids(tokenizer, " " + option.replace(mask_token, " "))
                for option in rendered_options
            ]
            if any(len(tokens) > 48 for tokens in option_token_ids):
                raise ValueError("Laya option exceeds build_sequence 48-token limit")
            option_ids = [[tokenizer.mask_token_id, *tokens] for tokens in option_token_ids]
            option_head_cost = sum(len(tokens) for tokens in option_ids)
            head_budget = head_max_len - option_head_cost
            expected_head_tokens = len(head_ids) + option_head_cost + 4
            estimated_state_budget = max_len - expected_head_tokens
            if head_budget < 16:
                raise ValueError(
                    "Laya options exceed complete question head budget: "
                    f"candidate_count={len(rendered_options)}, instruction_tokens={len(head_ids)}, "
                    f"option_tokens={[len(tokens) for tokens in option_token_ids]}, "
                    f"option_mask_tokens={option_head_cost}, head_budget={head_budget}, "
                    f"state_tokens={len(state_ids)}, estimated_state_budget={estimated_state_budget}, "
                    f"head_max_len={head_max_len}, max_len={max_len}"
                )
            if len(head_ids) > max(8, head_budget):
                raise ValueError(
                    "Laya instructions exceed complete question head budget: "
                    f"candidate_count={len(rendered_options)}, instruction_tokens={len(head_ids)}, "
                    f"option_tokens={[len(tokens) for tokens in option_token_ids]}, "
                    f"option_mask_tokens={option_head_cost}, head_budget={head_budget}, "
                    f"state_tokens={len(state_ids)}, estimated_state_budget={estimated_state_budget}, "
                    f"head_max_len={head_max_len}, max_len={max_len}"
                )

            expected_empty = [tokenizer.cls_token_id, *head_ids, tokenizer.sep_token_id]
            expected_markers = []
            for tokens in option_ids:
                expected_markers.append(len(expected_empty))
                expected_empty.extend(tokens)
            expected_empty.extend([tokenizer.sep_token_id, tokenizer.sep_token_id])
            if list(empty_sequence) != expected_empty:
                raise ValueError("Laya build_sequence truncated or changed question instructions/options")
            # The empty sequence includes the final SEP, which is also the
            # separator reserved after the full state in the populated input.
            budget = max_len - len(empty_sequence)
            if len(state_ids) > budget:
                raise ValueError(
                    "Laya state exceeds model input budget: "
                    f"state_tokens={len(state_ids)}, state_budget={budget}, max_len={max_len}"
                )
            actual_sequence, actual_markers = build_sequence(
                tokenizer, compact_state, internal, max_len, head_max_len)
            if list(actual_markers) != expected_markers:
                raise ValueError("Laya build_sequence omitted or moved an option marker")
            expected_actual = expected_empty[:-1] + state_ids + [tokenizer.sep_token_id]
            if list(actual_sequence) != expected_actual:
                raise ValueError("Laya build_sequence truncated or changed compact state tokens")

            budgets.append(budget)
            actual_lengths.append(len(empty_sequence) - 1 + len(state_ids) + 1)
            head_lengths.append(len(head_ids))
            instruction_lengths.append(len(_token_ids(tokenizer, instructions)))
            option_lengths.append([len(tokens) for tokens in option_token_ids])
    except Exception as error:
        raise ValueError(f"cannot verify Laya input token budget: {error}") from error
    if not budgets or any(budget < 0 for budget in budgets):
        raise ValueError("cannot verify Laya input token budget for empty/invalid questions")
    if any(len(state_ids) > budget for budget in budgets):
        raise ValueError(
            "Laya state exceeds model input budget: "
            f"state_tokens={len(state_ids)}, min_state_budget={min(budgets)}, max_len={max_len}"
        )
    answer = agent.predict(compact_state, questions)
    audit = {
        "state_tokens": len(state_ids),
        "state_budgets": budgets,
        "input_tokens": actual_lengths,
        "max_input_tokens": max(actual_lengths),
        "max_len": max_len,
        "head_max_len": head_max_len,
        "question_head_tokens": head_lengths,
        "option_mask_tokens": [sum(length + 1 for length in lengths) for lengths in option_lengths],
        "head_budgets": [head_max_len - sum(length + 1 for length in lengths) for lengths in option_lengths],
        "candidate_counts": [len(lengths) for lengths in option_lengths],
        "instruction_tokens": instruction_lengths,
        "option_tokens": option_lengths,
    }
    return answer, audit


def verified_probabilities(probabilities, candidates):
    allowed = [candidate["action"] for candidate in candidates]
    if not allowed or len(set(allowed)) != len(allowed) or len(allowed) > 20:
        raise ValueError("invalid or oversized eligible A^O")
    if set(probabilities) != set(allowed):
        raise ValueError("Laya returned probabilities outside eligible A^O")
    numbers = {name: float(probabilities[name]) for name in allowed}
    if any(not math.isfinite(value) or value < 0 or value > 1 for value in numbers.values()):
        raise ValueError("Laya returned invalid probabilities")
    if not 0.5 <= sum(numbers.values()) <= 1.5:
        raise ValueError("Laya returned a non-distribution")
    return numbers


class Bridge:
    def __init__(self, cassette, replay=None, device=None, allow_v1_replay=False):
        self.cassette = cassette
        self.replay_enabled = bool(replay)
        self.allow_v1_replay = bool(replay and allow_v1_replay)
        self.lock = threading.Lock()
        self.replay = {}
        self.memo = {}
        self.soft_replay = {}
        self.soft_memo = {}
        self.semantic_replay = {}
        self.semantic_memo = {}
        if replay:
            for line in replay.read_text().splitlines():
                row = json.loads(line)
                if row.get("type") == "laya_typed_choice":
                    self.replay.setdefault(row["request_hash"], row)
                elif row.get("type") == "laya_noul_soft_reconsideration":
                    self.soft_replay.setdefault(row["request_hash"], row)
                elif row.get("type") in {"laya_commitment_choice", "laya_appraisal_scores"}:
                    self.semantic_replay.setdefault(row["request_hash"], row)
        elif cassette.exists():
            for line in cassette.read_text().splitlines():
                row = json.loads(line)
                if (row.get("type") == "laya_typed_choice" and row.get("model") == CHECKPOINT
                        and row.get("protocol_version") == PROTOCOL_VERSION
                        and row.get("checkpoint_revision") == CHECKPOINT_REVISION
                        and row.get("prompt_version") == PROMPT_VERSION
                        and row.get("proxy_source_sha256") == PROXY_SOURCE_SHA256):
                    self.memo.setdefault(row["request_hash"], row["probabilities"])
                elif (row.get("type") == "laya_noul_soft_reconsideration" and row.get("model") == CHECKPOINT
                        and row.get("protocol_version") == PROTOCOL_VERSION
                        and row.get("checkpoint_revision") == CHECKPOINT_REVISION
                        and row.get("prompt_version") == PROMPT_VERSION
                        and row.get("proxy_source_sha256") == PROXY_SOURCE_SHA256):
                    self.soft_memo.setdefault(row["request_hash"], row["probability"])
                elif (row.get("type") in {"laya_commitment_choice", "laya_appraisal_scores"}
                        and row.get("model") == CHECKPOINT
                        and row.get("protocol_version") == PROTOCOL_VERSION
                        and row.get("checkpoint_revision") == CHECKPOINT_REVISION
                        and row.get("prompt_version") == PROMPT_VERSION
                        and row.get("proxy_source_sha256") == PROXY_SOURCE_SHA256):
                    self.semantic_memo.setdefault(row["request_hash"], row)
        self.agent = None
        if not replay:
            import laya
            from huggingface_hub import snapshot_download
            snapshot = snapshot_download(repo_id=CHECKPOINT, revision=CHECKPOINT_REVISION)
            self.agent = laya.load(snapshot, device=device)

    def choose(self, request):
        if request.get("operation") == "identity":
            if set(request) != {"operation"}:
                raise ValueError("identity request accepts only the operation field")
            return proxy_identity()
        if request.get("operation") == "soft_reconsideration":
            return self.soft_reconsider(request)
        if request.get("operation") == "commitment_choice":
            return self.commitment_choice(request)
        if request.get("operation") == "appraisal_scores":
            return self.appraisal_scores(request)
        if set(request) - {"request_id", "timestamp", "profile", "personality", "state", "observation", "candidates",
                           "running_action", "recent_history", "recent_factual_summary"}:
            raise ValueError("request contains fields outside O/S/P/I/A^O contract")
        if "recent_history" not in request or "recent_factual_summary" not in request:
            raise ValueError("v4 request is missing actor-local history")
        request = versioned_request(request)
        candidates = request["candidates"]
        key = request_hash(request)
        replay_row = self._replay_row(self.replay, request, key)
        if replay_row is not None:
            probabilities = verified_probabilities(replay_row["probabilities"], candidates)
            mode = "cassette-replay"
        elif key in self.memo:
            probabilities = verified_probabilities(self.memo[key], candidates)
            mode = "live-memo"
        else:
            if self.agent is None:
                raise ValueError("cassette has no matching Laya decision")
            state = policy_model_state(request)
            criteria = {}
            for candidate in candidates:
                planned_minutes = candidate.get("planned_minutes")
                if not isinstance(planned_minutes, int) or planned_minutes <= 0:
                    raise ValueError("Laya candidate has no valid planned duration")
                target = candidate.get("target") or "here"
                criteria[candidate["action"]] = f"{target} {planned_minutes}m"
            prediction, token_audit = predict_without_truncation(self.agent, state, {
                "next_action": {
                    "type": "choice",
                    "instructions": policy_instructions(),
                    "criteria": criteria,
                }
            })
            answer = prediction["answers"]["next_action"]
            probabilities = verified_probabilities(answer["probabilities"], candidates)
            mode = "local-laya-typed"
            row = {
                "type": "laya_typed_choice",
                "request_hash": key,
                "request": request,
                "probabilities": probabilities,
                "raw_answer": answer,
                **live_cassette_provenance(token_audit),
                "decoding_config": {"typed_choice": "raw_probs", "sampling": "C++ seeded RNG"},
                "laya_version": importlib.metadata.version("laya"),
            }
            with self.lock:
                self.memo[key] = probabilities
                self.cassette.parent.mkdir(parents=True, exist_ok=True)
                with self.cassette.open("a") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        weights = ",".join(f"{candidate['action']}={probabilities[candidate['action']]:.12g}"
                           for candidate in candidates)
        return {"model": CHECKPOINT, "weights": weights, "request_hash": key, "mode": mode}

    def soft_reconsider(self, request):
        if set(request) - {"request_id", "timestamp", "profile", "personality", "state",
                            "observation", "candidates", "operation", "running_action",
                            "recent_history", "recent_factual_summary"}:
            raise ValueError("soft gate request contains fields outside O/S/P/I/RunningAction contract")
        if request["candidates"] or request["operation"] != "soft_reconsideration":
            raise ValueError("soft gate may not change A^O")
        request = versioned_request(request)
        running = request["running_action"]
        if set(running) != {"action", "target", "elapsed_minutes", "planned_minutes"}:
            raise ValueError("invalid RunningAction projection")
        key = request_hash(request)
        replay_row = self._replay_row(self.soft_replay, request, key)
        if replay_row is not None:
            probability = replay_row["probability"]
            mode = "cassette-replay"
        elif key in self.soft_memo:
            probability = self.soft_memo[key]
            mode = "live-memo"
        else:
            if self.agent is None:
                raise ValueError("cassette has no matching Laya soft gate")
            state = {
                "time": request["timestamp"],
                "personality": request["personality"],
                "subjective_state_and_commitment": request["state"],
                "known_or_stale_observations": request["observation"],
                "running_action": running,
                "actor_local_temporal_context": {
                    "recent_history": request.get("recent_history", {"episodes": [], "observed_events": []}),
                    "recent_factual_summary": request.get("recent_factual_summary", {}),
                },
            }
            prediction, token_audit = predict_without_truncation(self.agent, state, {
                "reconsider": {
                    "type": "noul",
                    "instructions": (
                        "Should this character reconsider their current action now? "
                        "Use only observed facts, subjective state, personality, commitment and actor-local factual recent history, "
                        "and current action. Episode tuples are [action,target,start,actual,planned,result,optional_task], "
                        "with end=start+actual; events are [minute,key,value]. A true answer only opens a decision opportunity; "
                        "it does not interrupt the action or override physical constraints."
                    ),
                    "criteria": {"true": "reconsider current action", "false": "keep current plan"},
                }
            })
            answer = prediction["answers"]["reconsider"]
            probability = answer["noul"]
            mode = "local-laya-noul"
            row = {"type": "laya_noul_soft_reconsideration", "request_hash": key,
                   "request": request, "probability": probability, "raw_answer": answer,
                   **live_cassette_provenance(token_audit),
                   "decoding_config": {"typed_noul": "raw_probability", "sampling": "C++ seeded RNG"},
                   "laya_version": importlib.metadata.version("laya")}
            with self.lock:
                self.soft_memo[key] = probability
                self.cassette.parent.mkdir(parents=True, exist_ok=True)
                with self.cassette.open("a") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        probability = float(probability)
        if not math.isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError("Laya returned invalid soft gate probability")
        return {"model": CHECKPOINT, "probability": f"{probability:.12g}",
                "request_hash": key, "mode": mode}

    @staticmethod
    def semantic_state(request):
        if set(request) - {"request_id", "timestamp", "profile", "personality", "state",
                            "observation", "candidates", "operation", "observation_deltas",
                            "last_self_action", "options", "running_action", "recent_history",
                            "recent_factual_summary"}:
            raise ValueError("semantic request contains fields outside O/Delta-O/S/P/I contract")
        if request["candidates"]:
            raise ValueError("semantic model may not change A^O")
        return {
            "time": request["timestamp"],
            "personality": request["personality"],
            "subjective_state_and_commitment": request["state"],
            "observation_deltas": request["observation_deltas"],
            "last_self_action": request["last_self_action"],
            "actor_local_causal_history": request.get("recent_history", {"episodes": [], "observed_events": []}),
            "relevant_known_observations": [fact for fact in request["observation"]
                                            if observation_fact_key(fact).startswith(("task.", "message.", "room."))],
        }

    def _replay_row(self, rows, request, key):
        row = rows.get(key)
        if row is not None:
            if (row.get("model") == CHECKPOINT
                    and row.get("checkpoint_revision") == CHECKPOINT_REVISION
                    and row.get("protocol_version") == PROTOCOL_VERSION
                    and row.get("prompt_version") == PROMPT_VERSION
                    and row.get("proxy_source_sha256") == PROXY_SOURCE_SHA256):
                return row
            return None
        if not self.replay_enabled or not self.allow_v1_replay:
            return None
        legacy = rows.get(legacy_replay_hash(request))
        if legacy is not None and legacy.get("protocol_version") in (None, LEGACY_PROTOCOL_VERSION):
            if legacy.get("prompt_version") in (None, LEGACY_PROMPT_VERSION):
                return legacy
        return None

    def commitment_choice(self, request):
        state = self.semantic_state(request)
        request = versioned_request(request)
        options = request["options"]
        if options not in (["continue", "abandon"], ["continue", "suspend", "abandon"],
                           ["resume", "suspend", "abandon"]):
            raise ValueError("invalid commitment option surface")
        key = request_hash(request)
        row = self._replay_row(self.semantic_replay, request, key) or self.semantic_memo.get(key)
        if row is None:
            if self.agent is None:
                raise ValueError("cassette has no matching Laya commitment choice")
            prediction, token_audit = predict_without_truncation(self.agent, state, {"commitment": {
                "type": "choice",
                "instructions": (
                    "Given only observed task information, actor-local causal history, self-action feedback, current commitment. "
                    "Episode tuples are [action,target,start,actual,planned,result,optional_task], with end=start+actual; result s/d/i/r means settled/task-done/interrupted/rejected. "
                    "subjective state and personality, choose how the actor's task intention changes. "
                    "This is subjective intention, not World task status."
                ),
                "criteria": {name: {
                    "continue": "remain or become actively committed to the observed task",
                    "suspend": "keep the task intention but temporarily pause it",
                    "resume": "reactivate a previously suspended task intention",
                    "abandon": "drop the subjective task intention without changing the World task",
                }[name] for name in options},
            }})
            answer = prediction["answers"]["commitment"]
            probabilities = {name: float(answer["probabilities"][name]) for name in options}
            row = {"type": "laya_commitment_choice", "request_hash": key, "request": request,
                   "probabilities": probabilities, "raw_answer": answer,
                   **live_cassette_provenance(token_audit),
                   "decoding_config": {"typed_choice": "raw_probs", "sampling": "C++ seeded RNG"},
                   "laya_version": importlib.metadata.version("laya")}
            with self.lock:
                self.semantic_memo[key] = row
                self.cassette.parent.mkdir(parents=True, exist_ok=True)
                with self.cassette.open("a") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        probabilities = row["probabilities"]
        if set(probabilities) != set(options):
            raise ValueError("Laya commitment options mismatch")
        weights = ",".join(f"{name}={float(probabilities[name]):.12g}" for name in options)
        return {"model": CHECKPOINT, "weights": weights, "request_hash": key,
                "mode": "cassette-replay" if self._replay_row(self.semantic_replay, request, key) else "local-laya-choice"}

    def appraisal_scores(self, request):
        state = self.semantic_state(request)
        if request["options"]:
            raise ValueError("appraisal cannot invent choice options")
        request = versioned_request(request)
        keys = ("goal_progress", "goal_obstruction", "stimulation", "uncertainty",
                "positive_outcome", "negative_outcome", "control_restored")
        key = request_hash(request)
        row = self._replay_row(self.semantic_replay, request, key) or self.semantic_memo.get(key)
        if row is None:
            if self.agent is None:
                raise ValueError("cassette has no matching Laya appraisal scores")
            questions = {name: {
                "type": "score", "instructions": f"Using only this actor's short factual causal history (episode tuples [action,target,start,actual,planned,result,task], end=start+actual), how much {name.replace('_', ' ')} does the newly observed change mean to this actor?",
                "criteria": ["none", "slight", "moderate", "strong", "very strong"],
            } for name in keys}
            prediction, token_audit = predict_without_truncation(self.agent, state, questions)
            answers = prediction["answers"]
            scores = {name: float(answers[name]["score"]) for name in keys}
            row = {"type": "laya_appraisal_scores", "request_hash": key, "request": request,
                   "scores": scores, "raw_answers": answers,
                   **live_cassette_provenance(token_audit),
                   "decoding_config": {"typed_score": "expected_ordinal_0_to_4", "sampling": "none"},
                   "laya_version": importlib.metadata.version("laya")}
            with self.lock:
                self.semantic_memo[key] = row
                self.cassette.parent.mkdir(parents=True, exist_ok=True)
                with self.cassette.open("a") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        scores = row["scores"]
        if set(scores) != set(keys):
            raise ValueError("Laya appraisal channel mismatch")
        encoded = ",".join(f"{name}={float(scores[name]):.12g}" for name in keys)
        return {"model": CHECKPOINT, "scores": encoded, "request_hash": key,
                "mode": "cassette-replay" if self._replay_row(self.semantic_replay, request, key) else "local-laya-score"}


class Handler(socketserver.StreamRequestHandler):
    bridge = None

    def handle(self):
        for line in self.rfile:
            try:
                response = self.bridge.choose(json.loads(line))
            except Exception as error:
                response = {"error": str(error)}
            self.wfile.write((json.dumps(response, separators=(",", ":")) + "\n").encode())


class LoopbackServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cassette", type=pathlib.Path, required=True)
    parser.add_argument("--replay", type=pathlib.Path)
    parser.add_argument("--allow-v1-replay", action="store_true",
                        help="explicitly allow legacy v1 cassette hash fallback during offline replay")
    parser.add_argument("--device", choices=("cpu", "mps", "cuda"))
    parser.add_argument("--port", type=int, default=8743)
    args = parser.parse_args()
    if args.allow_v1_replay and not args.replay:
        parser.error("--allow-v1-replay requires --replay")
    Handler.bridge = Bridge(args.cassette, args.replay, args.device, args.allow_v1_replay)
    with LoopbackServer(("127.0.0.1", args.port), Handler) as service:
        print(json.dumps({"service": "laya-typed-policy-v0", "bind": "127.0.0.1",
                          "port": service.server_address[1], **proxy_identity(),
                          "mode": "replay" if args.replay else "live"}), flush=True)
        service.serve_forever()


if __name__ == "__main__":
    main()
