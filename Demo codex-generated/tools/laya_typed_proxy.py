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
        if replay:
            for line in replay.read_text().splitlines():
                row = json.loads(line)
                if row.get("type") == "laya_typed_choice":
                    self.replay.setdefault(row["request_hash"], row)
        self.agent = None
        if not replay:
            import laya
            self.agent = laya.load(CHECKPOINT, device=device)

    def choose(self, request):
        if set(request) - {"request_id", "timestamp", "profile", "personality", "state", "observation", "candidates"}:
            raise ValueError("request contains fields outside O/S/P/I/A^O contract")
        candidates = request["candidates"]
        key = request_hash(request)
        if key in self.replay:
            probabilities = verified_probabilities(self.replay[key]["probabilities"], candidates)
            mode = "cassette-replay"
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
                "model": CHECKPOINT,
                "laya_version": importlib.metadata.version("laya"),
            }
            with self.lock:
                self.cassette.parent.mkdir(parents=True, exist_ok=True)
                with self.cassette.open("a") as handle:
                    handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        weights = ",".join(f"{candidate['action']}={probabilities[candidate['action']]:.12g}"
                           for candidate in candidates)
        return {"model": CHECKPOINT, "weights": weights, "request_hash": key, "mode": mode}


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
                          "mode": "replay" if args.replay else "live"}), flush=True)
        service.serve_forever()


if __name__ == "__main__":
    main()
