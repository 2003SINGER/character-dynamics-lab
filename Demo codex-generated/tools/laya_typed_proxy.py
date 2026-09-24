"""Loopback-only bridge to the actual Laya typed-decisions checkpoint.

C++ sends observed O, S, P/I and eligible A^O. Laya returns raw typed-choice
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

os.environ.setdefault("USE_TF", "0")
CHECKPOINT = "convaiinnovations/laya-typed-decisions"
CHECKPOINT_REVISION = "f9ab0b228f0fc0f14d873dbc99038f135c2da1b2"
PROMPT_VERSION = "character-dynamics-laya-typed-v1"


def request_hash(request):
    body = dict(request)
    body.pop("request_id", None)
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


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
    def __init__(self, cassette, replay=None, device=None):
        self.cassette = cassette
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
                if row.get("type") == "laya_typed_choice" and row.get("model") == CHECKPOINT:
                    self.memo.setdefault(row["request_hash"], row["probabilities"])
                elif row.get("type") == "laya_noul_soft_reconsideration" and row.get("model") == CHECKPOINT:
                    self.soft_memo.setdefault(row["request_hash"], row["probability"])
                elif row.get("type") in {"laya_commitment_choice", "laya_appraisal_scores"} and row.get("model") == CHECKPOINT:
                    self.semantic_memo.setdefault(row["request_hash"], row)
        self.agent = None
        if not replay:
            import laya
            from huggingface_hub import snapshot_download
            snapshot = snapshot_download(repo_id=CHECKPOINT, revision=CHECKPOINT_REVISION)
            self.agent = laya.load(snapshot, device=device)

    def choose(self, request):
        if request.get("operation") == "soft_reconsideration":
            return self.soft_reconsider(request)
        if request.get("operation") == "commitment_choice":
            return self.commitment_choice(request)
        if request.get("operation") == "appraisal_scores":
            return self.appraisal_scores(request)
        if set(request) - {"request_id", "timestamp", "profile", "personality", "state", "observation", "candidates"}:
            raise ValueError("request contains fields outside O/S/P/I/A^O contract")
        candidates = request["candidates"]
        key = request_hash(request)
        if key in self.replay:
            probabilities = verified_probabilities(self.replay[key]["probabilities"], candidates)
            mode = "cassette-replay"
        elif key in self.memo:
            probabilities = verified_probabilities(self.memo[key], candidates)
            mode = "live-memo"
        else:
            if self.agent is None:
                raise ValueError("cassette has no matching Laya decision")
            state = {
                "time": request["timestamp"],
                "personality": request["personality"],
                "subjective_state_and_commitment": request["state"],
                "known_or_stale_observations": request["observation"],
            }
            criteria = {
                candidate["action"]: (
                    f"Perform {candidate['action']} at {candidate['target'] or 'current location'}. "
                    f"{candidate['reason']}"
                ) for candidate in candidates
            }
            answer = self.agent.predict(state, {
                "next_action": {
                    "type": "choice",
                    "instructions": (
                        "Choose the character's next action using only observed facts, "
                        "subjective state, personality and current commitment. "
                        "Do not infer hidden World state or invent an action."
                    ),
                    "criteria": criteria,
                }
            })["answers"]["next_action"]
            probabilities = verified_probabilities(answer["probabilities"], candidates)
            mode = "local-laya-typed"
            row = {
                "type": "laya_typed_choice",
                "request_hash": key,
                "request": request,
                "probabilities": probabilities,
                "raw_answer": answer,
                "model": CHECKPOINT,
                "checkpoint_revision": CHECKPOINT_REVISION,
                "prompt_version": PROMPT_VERSION,
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
                            "observation", "candidates", "operation", "running_action"}:
            raise ValueError("soft gate request contains fields outside O/S/P/I/RunningAction contract")
        if request["candidates"] or request["operation"] != "soft_reconsideration":
            raise ValueError("soft gate may not change A^O")
        running = request["running_action"]
        if set(running) != {"action", "target", "elapsed_minutes", "planned_minutes"}:
            raise ValueError("invalid RunningAction projection")
        key = request_hash(request)
        if key in self.soft_replay:
            probability = self.soft_replay[key]["probability"]
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
            }
            answer = self.agent.predict(state, {
                "reconsider": {
                    "type": "noul",
                    "instructions": (
                        "Should this character reconsider their current action now? "
                        "Use only observed facts, subjective state, personality, commitment, "
                        "and current action. A true answer only opens a decision opportunity; "
                        "it does not interrupt the action or override physical constraints."
                    ),
                    "criteria": {"true": "reconsider current action", "false": "keep current plan"},
                }
            })["answers"]["reconsider"]
            probability = answer["noul"]
            mode = "local-laya-noul"
            row = {"type": "laya_noul_soft_reconsideration", "request_hash": key,
                   "request": request, "probability": probability, "raw_answer": answer,
                   "model": CHECKPOINT, "checkpoint_revision": CHECKPOINT_REVISION,
                   "prompt_version": PROMPT_VERSION,
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
                            "last_self_action", "options"}:
            raise ValueError("semantic request contains fields outside O/Delta-O/S/P/I contract")
        if request["candidates"]:
            raise ValueError("semantic model may not change A^O")
        return {
            "time": request["timestamp"],
            "personality": request["personality"],
            "subjective_state_and_commitment": request["state"],
            "observation_deltas": request["observation_deltas"],
            "last_self_action": request["last_self_action"],
            "relevant_known_observations": [fact for fact in request["observation"]
                                            if fact["key"].startswith(("task.", "message.", "room."))],
        }

    def commitment_choice(self, request):
        state = self.semantic_state(request)
        options = request["options"]
        if options not in (["continue", "abandon"], ["continue", "suspend", "abandon"],
                           ["resume", "suspend", "abandon"]):
            raise ValueError("invalid commitment option surface")
        key = request_hash(request)
        row = self.semantic_replay.get(key) or self.semantic_memo.get(key)
        if row is None:
            if self.agent is None:
                raise ValueError("cassette has no matching Laya commitment choice")
            answer = self.agent.predict(state, {"commitment": {
                "type": "choice",
                "instructions": (
                    "Given only observed task information, self-action feedback, current commitment, "
                    "subjective state and personality, choose how the actor's task intention changes. "
                    "This is subjective intention, not World task status."
                ),
                "criteria": {name: {
                    "continue": "remain or become actively committed to the observed task",
                    "suspend": "keep the task intention but temporarily pause it",
                    "resume": "reactivate a previously suspended task intention",
                    "abandon": "drop the subjective task intention without changing the World task",
                }[name] for name in options},
            }})["answers"]["commitment"]
            probabilities = {name: float(answer["probabilities"][name]) for name in options}
            row = {"type": "laya_commitment_choice", "request_hash": key, "request": request,
                   "probabilities": probabilities, "raw_answer": answer,
                   "model": CHECKPOINT, "checkpoint_revision": CHECKPOINT_REVISION,
                   "prompt_version": PROMPT_VERSION,
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
                "mode": "cassette-replay" if key in self.semantic_replay else "local-laya-choice"}

    def appraisal_scores(self, request):
        state = self.semantic_state(request)
        if request["options"]:
            raise ValueError("appraisal cannot invent choice options")
        keys = ("goal_progress", "goal_obstruction", "stimulation", "uncertainty",
                "positive_outcome", "negative_outcome", "control_restored")
        key = request_hash(request)
        row = self.semantic_replay.get(key) or self.semantic_memo.get(key)
        if row is None:
            if self.agent is None:
                raise ValueError("cassette has no matching Laya appraisal scores")
            questions = {name: {
                "type": "score", "instructions": f"How much {name.replace('_', ' ')} does the newly observed change mean to this actor?",
                "criteria": ["none", "slight", "moderate", "strong", "very strong"],
            } for name in keys}
            answers = self.agent.predict(state, questions)["answers"]
            scores = {name: float(answers[name]["score"]) for name in keys}
            row = {"type": "laya_appraisal_scores", "request_hash": key, "request": request,
                   "scores": scores, "raw_answers": answers,
                   "model": CHECKPOINT, "checkpoint_revision": CHECKPOINT_REVISION,
                   "prompt_version": PROMPT_VERSION,
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
                "mode": "cassette-replay" if key in self.semantic_replay else "local-laya-score"}


class Handler(socketserver.StreamRequestHandler):
    bridge = None

    def handle(self):
        try:
            response = self.bridge.choose(json.loads(self.rfile.readline()))
        except Exception as error:
            response = {"error": str(error)}
        self.wfile.write((json.dumps(response, separators=(",", ":")) + "\n").encode())


class LoopbackServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cassette", type=pathlib.Path, required=True)
    parser.add_argument("--replay", type=pathlib.Path)
    parser.add_argument("--device", choices=("cpu", "mps", "cuda"))
    parser.add_argument("--port", type=int, default=8743)
    args = parser.parse_args()
    Handler.bridge = Bridge(args.cassette, args.replay, args.device)
    with LoopbackServer(("127.0.0.1", args.port), Handler) as service:
        print(json.dumps({"service": "laya-typed-policy-v0", "bind": "127.0.0.1",
                          "port": service.server_address[1], "model": CHECKPOINT,
                          "checkpoint_revision": CHECKPOINT_REVISION, "prompt_version": PROMPT_VERSION,
                          "mode": "replay" if args.replay else "live"}), flush=True)
        service.serve_forever()


if __name__ == "__main__":
    main()
