"""Model-free acceptance for same-world Laya evaluation and cassette replay."""

import json
import pathlib
import socketserver
import subprocess
import sys
import tempfile
import threading

from laya_typed_proxy import CHECKPOINT, request_hash


class Handler(socketserver.StreamRequestHandler):
    cassette = None
    lock = threading.Lock()

    def handle(self):
        request = json.loads(self.rfile.readline())
        candidates = request["candidates"]
        probabilities = {item["action"]: float(index == len(candidates) - 1)
                         for index, item in enumerate(candidates)}
        key = request_hash(request)
        row = {"type": "laya_typed_choice", "request_hash": key,
               "request": request, "probabilities": probabilities,
               "model": CHECKPOINT, "laya_version": "stand-in"}
        with self.lock:
            with self.cassette.open("a") as handle:
                handle.write(json.dumps(row, separators=(",", ":")) + "\n")
        response = {"model": CHECKPOINT, "request_hash": key,
                    "weights": ",".join(f"{name}={value:g}" for name, value in probabilities.items())}
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
        with LoopbackServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            output = root / "paired"
            subprocess.run([sys.executable, str(evaluator), str(binary), str(output),
                            "--days", "7", "--cases", "1", "--policy", "laya",
                            "--laya-port", str(server.server_address[1]),
                            "--laya-cassette", str(cassette)], check=True, timeout=120)
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
                        "--days", "7", "--cases", "1"], check=True, timeout=120)
        compare = pathlib.Path(__file__).with_name("paired_policy_compare.py")
        comparison = root / "comparison"
        subprocess.run([sys.executable, str(compare), str(rule_output), str(output),
                        str(comparison)], check=True, timeout=120)
        paired = json.loads((comparison / "analysis.json").read_text())
        if not paired["same_world_verified"] or paired["actor_pairs"] != 8:
            raise SystemExit("Rule/Laya comparison did not prove eight same-world pairs")
    print("laya_long_horizon_pipeline_smoke: PASS")


if __name__ == "__main__":
    main()
