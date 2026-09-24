"""Historical Qwen single-action socket contract, not a Laya model test.

This smoke deliberately uses a tiny loopback-only stand-in rather than an LLM.
It proves that the C++ runtime sends only O/S/P plus eligible A^O, receives one
eligible action, and records policy provenance in a real free-run trace.
"""
import hashlib
import json
import pathlib
import socketserver
import subprocess
import sys
import tempfile
import threading


def canonical_hash(request):
    body = dict(request)
    body.pop("request_id", None)
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


class Handler(socketserver.StreamRequestHandler):
    requests = []

    def handle(self):
        for line in self.rfile:
            request = json.loads(line)
            self.requests.append(request)
            candidates = request["candidates"]
            response = {"action": candidates[0]["action"], "request_hash": canonical_hash(request)}
            self.wfile.write((json.dumps(response) + "\n").encode())


class LoopbackServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def fail(message):
    raise SystemExit(f"Laya loopback smoke failed: {message}")


def main():
    if len(sys.argv) != 2:
        fail("usage: laya_policy_loopback_smoke.py FREE_RUN_BINARY")
    binary = pathlib.Path(sys.argv[1]).resolve()
    with LoopbackServer(("127.0.0.1", 0), Handler) as server, tempfile.TemporaryDirectory() as directory:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        trace = pathlib.Path(directory) / "qwen-loopback.json"
        completed = subprocess.run(
            [str(binary), "17", "101", str(trace), "balanced", "--qwen-port", str(server.server_address[1])],
            text=True, capture_output=True, timeout=30,
        )
        server.shutdown()
        thread.join(timeout=5)
        if completed.returncode != 0:
            fail(completed.stderr.strip() or f"free run exited {completed.returncode}")
        rows = json.loads(trace.read_text())
    if not Handler.requests:
        fail("C++ runtime did not request a policy choice")
    required = {"timestamp", "profile", "personality", "state", "observation", "candidates"}
    for request in Handler.requests:
        if set(request) - required - {"request_id"}:
            fail("request exposes data outside the policy contract")
        if "world" in request or "probability" in json.dumps(request["candidates"]):
            fail("request leaked World or rule-policy probabilities")
        if not request["candidates"]:
            fail("request has no eligible candidate")
    decisions = [row for row in rows if row["policy_evaluated"]]
    if not decisions or any(row["policy_id"] != "qwen-action-policy-v0" for row in decisions):
        fail("trace does not attribute decisions to QwenActionPolicyV0")
    for row in decisions:
        eligible = {candidate["action"] for candidate in row["candidates"] if candidate["eligible"] and candidate["probability"] > 0}
        if row["selected_action"] not in eligible:
            fail("Laya selected an action outside trace A^O")
        if "hash=" not in row["policy_selection_provenance"]:
            fail("trace omits local request provenance")
    print(f"laya policy loopback smoke passed: {len(decisions)} policy decisions")


if __name__ == "__main__":
    main()
