"""Model-free acceptance for same-world Laya evaluation and cassette replay."""

import json
import pathlib
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading

from laya_typed_proxy import (CHECKPOINT, CHECKPOINT_REVISION, PROMPT_VERSION,
                              PROTOCOL_VERSION, request_hash, versioned_request)
from long_horizon_eval import proxy_identity

PROXY_SOURCE_SHA256 = proxy_identity(pathlib.Path(__file__).with_name("laya_typed_proxy.py"))["proxy_source_sha256"]


class Handler(socketserver.StreamRequestHandler):
    cassette = None
    lock = threading.Lock()
    seen = set()
    request_count = 0
    connection_count = 0

    def setup(self):
        super().setup()
        with self.lock:
            type(self).connection_count += 1

    def handle(self):
        for line in self.rfile:
            self.handle_one(line)

    def handle_one(self, line):
        raw_request = json.loads(line)
        with self.lock:
            type(self).request_count += 1
        if raw_request == {"operation": "identity"}:
            response = {"model": CHECKPOINT, "checkpoint_revision": CHECKPOINT_REVISION,
                        "protocol_version": PROTOCOL_VERSION, "prompt_version": PROMPT_VERSION,
                        "proxy_source_sha256": PROXY_SOURCE_SHA256}
            self.wfile.write((json.dumps(response) + "\n").encode())
            return
        request = versioned_request(raw_request)
        key = request_hash(request)
        if request.get("operation") == "soft_reconsideration":
            row = {"type": "laya_noul_soft_reconsideration", "request_hash": key,
                   "request": request, "probability": 1.0,
                   "model": CHECKPOINT, "checkpoint_revision": CHECKPOINT_REVISION,
                   "prompt_version": PROMPT_VERSION, "protocol_version": PROTOCOL_VERSION,
                   "proxy_source_sha256": PROXY_SOURCE_SHA256,
                   "laya_version": "stand-in"}
            response = {"model": CHECKPOINT, "request_hash": key, "probability": "1"}
        elif request.get("operation") == "commitment_choice":
            options = request["options"]
            if options not in (["continue", "abandon"], ["continue", "suspend", "abandon"],
                               ["resume", "suspend", "abandon"]):
                raise SystemExit("invalid typed commitment surface")
            probabilities = {name: float(index == 0) for index, name in enumerate(options)}
            row = {"type": "laya_commitment_choice", "request_hash": key,
                   "request": request, "probabilities": probabilities,
                   "model": CHECKPOINT, "checkpoint_revision": CHECKPOINT_REVISION,
                   "prompt_version": PROMPT_VERSION, "protocol_version": PROTOCOL_VERSION,
                   "proxy_source_sha256": PROXY_SOURCE_SHA256,
                   "laya_version": "stand-in"}
            response = {"model": CHECKPOINT, "request_hash": key,
                        "weights": ",".join(f"{name}={value:g}" for name, value in probabilities.items())}
        elif request.get("operation") == "appraisal_scores":
            scores = {name: float(4 if name in {"goal_progress", "positive_outcome"} else 0)
                      for name in ("goal_progress", "goal_obstruction", "stimulation", "uncertainty",
                                   "positive_outcome", "negative_outcome", "control_restored")}
            row = {"type": "laya_appraisal_scores", "request_hash": key,
                   "request": request, "scores": scores,
                   "model": CHECKPOINT, "checkpoint_revision": CHECKPOINT_REVISION,
                   "prompt_version": PROMPT_VERSION, "protocol_version": PROTOCOL_VERSION,
                   "proxy_source_sha256": PROXY_SOURCE_SHA256,
                   "laya_version": "stand-in"}
            response = {"model": CHECKPOINT, "request_hash": key,
                        "scores": ",".join(f"{name}={value:g}" for name, value in scores.items())}
        else:
            candidates = request["candidates"]
            probabilities = {item["action"]: float(index == len(candidates) - 1)
                             for index, item in enumerate(candidates)}
            row = {"type": "laya_typed_choice", "request_hash": key,
                   "request": request, "probabilities": probabilities,
                   "model": CHECKPOINT, "checkpoint_revision": CHECKPOINT_REVISION,
                   "prompt_version": PROMPT_VERSION, "protocol_version": PROTOCOL_VERSION,
                   "proxy_source_sha256": PROXY_SOURCE_SHA256,
                   "laya_version": "stand-in"}
            response = {"model": CHECKPOINT, "request_hash": key,
                        "weights": ",".join(f"{name}={value:g}" for name, value in probabilities.items())}
        with self.lock:
            if key not in self.seen:
                with self.cassette.open("a") as handle:
                    handle.write(json.dumps(row, separators=(",", ":")) + "\n")
                self.seen.add(key)
        self.wfile.write((json.dumps(response) + "\n").encode())


class LoopbackServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: laya_long_horizon_pipeline_smoke.py BINARY")
    binary = pathlib.Path(sys.argv[1]).resolve()
    evaluator = pathlib.Path(__file__).with_name("long_horizon_eval.py")
    with tempfile.TemporaryDirectory(prefix="laya-life-smoke-") as directory:
        root = pathlib.Path(directory)
        cassette = root / "live-cassette.jsonl"
        Handler.cassette = cassette
        Handler.seen = set()
        Handler.request_count = 0
        Handler.connection_count = 0
        with LoopbackServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            output = root / "paired"
            try:
                with socket.socket() as probe:
                    probe.settimeout(2)
                    probe.connect(server.server_address)
                    probe.sendall(b'{"operation":"identity"}\n')
                    if not json.loads(probe.makefile().readline()).get("proxy_source_sha256"):
                        raise RuntimeError("stand-in loopback server identity readiness check failed")
                subprocess.run([sys.executable, str(evaluator), str(binary), str(output),
                                "--days", "7", "--cases", "1", "--policy", "laya",
                                "--laya-port", str(server.server_address[1]),
                                "--laya-cassette", str(cassette)], check=True, timeout=900)
            except BaseException as error:
                raise RuntimeError(
                    f"live Laya loopback failed after {Handler.request_count} requests; "
                    f"server_thread_alive={thread.is_alive()}, listener={server.server_address}: {error}"
                ) from error
            soft_trace = root / "soft-gate.jsonl"
            subprocess.run([str(binary), "1000", "5000", "7", "balanced",
                            str(soft_trace), "boundaries", "--laya-port",
                            str(server.server_address[1]), "--laya-soft-gate"],
                           check=True, timeout=900)
            soft_rows = [json.loads(line) for line in soft_trace.read_text().splitlines()]
            if not any(row.get("model_soft_reconsideration", {}).get("requested")
                       for row in soft_rows if row.get("type") == "boundary"
                       and row.get("model_soft_reconsideration")):
                raise SystemExit("typed noul did not open a soft decision gate")
            if not any("model_soft_reconsideration" in row.get("gate_reasons", [])
                       for row in soft_rows if row.get("type") == "boundary"):
                raise SystemExit("soft gate reason was not traced")
            full_trace = root / "typed-xi.jsonl"
            subprocess.run([str(binary), "1000", "5000", "7", "balanced",
                            str(full_trace), "boundaries", "--laya-port",
                            str(server.server_address[1]), "--laya-commitment",
                            "--laya-appraisal"], check=True, timeout=900)
            full_rows = [json.loads(line) for line in full_trace.read_text().splitlines()]
            boundaries = [row for row in full_rows if row["type"] == "boundary"]
            if full_rows[0]["dynamics_model"] != "demo-living-v1+laya-typed-xi":
                raise SystemExit("full typed mode did not select its distinct Dynamics model")
            if not any(row["typed_commitment_decision"] and
                       row["typed_commitment_decision"]["probabilities"] for row in boundaries):
                raise SystemExit("typed commitment was not applied and traced")
            if not any(row["typed_appraisal"] and len(row["typed_appraisal"]["scores"]) == 7
                       for row in boundaries):
                raise SystemExit("seven-channel typed appraisal was not applied and traced")
            if Handler.request_count <= Handler.connection_count:
                raise SystemExit("high-volume Laya smoke did not reuse persistent connections")
            server.shutdown()
            thread.join(timeout=5)
        manifest = json.loads((output / "manifest.json").read_text())
        analysis = json.loads((output / "analysis.json").read_text())
        if manifest["policy_id"] != "laya-typed-policy-v0" or len(manifest["runs"]) != 8:
            raise SystemExit("Laya manifest did not cover eight paired profiles")
        if analysis["policy_id"] != "laya-typed-policy-v0" or len(analysis["history_fork_summary"]) != 6:
            raise SystemExit("Laya fork analysis did not use the typed policy")
        if not (output / "laya_typed_probabilities.jsonl").is_file():
            raise SystemExit("Laya probability cassette was not retained")
        if len((output / "history_fork_samples.jsonl").read_text().splitlines()) != 8 * 2 * 3:
            raise SystemExit("Laya fork samples are incomplete")
        rule_output = root / "rule"
        subprocess.run([sys.executable, str(evaluator), str(binary), str(rule_output),
                        "--days", "7", "--cases", "1"], check=True, timeout=900)
        compare = pathlib.Path(__file__).with_name("paired_policy_compare.py")
        comparison = root / "comparison"
        subprocess.run([sys.executable, str(compare), str(rule_output), str(output),
                        str(comparison)], check=True, timeout=900)
        paired = json.loads((comparison / "analysis.json").read_text())
        if not paired["same_world_verified"] or paired["actor_pairs"] != 8:
            raise SystemExit("Rule/Laya comparison did not prove eight same-world pairs")
    print(f"laya_long_horizon_pipeline_smoke: PASS "
          f"({Handler.request_count} requests over {Handler.connection_count} loopback connections)")


if __name__ == "__main__":
    main()
