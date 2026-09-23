"""Model-free wire contract for actual Laya typed probability integration."""

import json
import pathlib
import socketserver
import subprocess
import sys
import tempfile
import threading


class Handler(socketserver.StreamRequestHandler):
    requests = []

    def handle(self):
        request = json.loads(self.rfile.readline())
        self.requests.append(request)
        candidates = request["candidates"]
        # One-hot on the last option proves C++ samples typed π, not rule π or
        # simply the first/argmax action supplied by the old Qwen bridge.
        weights = ",".join(f"{candidate['action']}={int(index == len(candidates)-1)}"
                           for index, candidate in enumerate(candidates))
        response = {"model": "convaiinnovations/laya-typed-decisions",
                    "weights": weights, "request_hash": "stand-in"}
        self.wfile.write((json.dumps(response) + "\n").encode())


class LoopbackServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: laya_typed_policy_loopback_smoke.py FREE_RUN_BINARY")
    with LoopbackServer(("127.0.0.1", 0), Handler) as server, tempfile.TemporaryDirectory() as directory:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        trace = pathlib.Path(directory) / "typed-trace.json"
        result = subprocess.run(
            [sys.argv[1], "17", "101", str(trace), "balanced", "--laya-port", str(server.server_address[1])],
            text=True, capture_output=True, timeout=45,
        )
        server.shutdown()
        thread.join(timeout=5)
        if result.returncode:
            raise SystemExit(result.stderr or f"free run failed: {result.returncode}")
        rows = json.loads(trace.read_text())
    decisions = [row for row in rows if row["policy_evaluated"]]
    if not decisions or len(decisions) != len(Handler.requests):
        raise SystemExit("typed policy did not receive one request per decision")
    for request, row in zip(Handler.requests, decisions):
        if set(request) - {"request_id", "timestamp", "profile", "personality", "state", "observation", "candidates"}:
            raise SystemExit("typed request leaked outside O/S/P/I/A^O")
        if "world" in request or any("probability" in c for c in request["candidates"]):
            raise SystemExit("typed request leaked World or rule π")
        expected = request["candidates"][-1]["action"]
        if row["policy_id"] != "laya-typed-policy-v0" or row["selected_action"] != expected:
            raise SystemExit("C++ did not sample the supplied typed distribution")
        distribution = {c["action"]: c["probability"] for c in row["candidates"] if c["eligible"]}
        if distribution.get(expected) != 1.0 or any(value != 0.0 for action, value in distribution.items() if action != expected):
            raise SystemExit("trace does not preserve the sampled Laya distribution")
    print(f"laya typed policy loopback smoke passed: {len(decisions)} decisions")


if __name__ == "__main__":
    main()
