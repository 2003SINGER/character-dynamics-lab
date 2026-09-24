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
    connections = 0

    def setup(self):
        super().setup()
        type(self).connections += 1

    def handle(self):
        for line in self.rfile:
            request = json.loads(line)
            self.requests.append(request)
            candidates = request["candidates"]
            # One-hot on the last option proves C++ samples typed π, not rule π.
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
        Handler.requests = []
        Handler.connections = 0
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
        facts = {item["key"]: item["value"] for item in request["observation"]}
        total_minutes = int(request["timestamp"])
        expected_clock = f"Day {total_minutes // 1440 + 1} {total_minutes % 1440 // 60:02d}:{total_minutes % 60:02d}"
        if facts.get("clock.total_minutes") != str(total_minutes) or facts.get("clock.time") != expected_clock:
            raise SystemExit("typed request contains inconsistent scheduler-derived clock facts")
        if any(not isinstance(c.get("planned_minutes"), int) or c["planned_minutes"] <= 0
               for c in request["candidates"]):
            raise SystemExit("typed request omitted a positive planned duration")
        if any(not c.get("hard_admissible") or "rule_soft_eligible" not in c for c in row["candidates"]):
            raise SystemExit("Laya candidate trace omitted hard-admissibility / Rule-soft provenance")
        expected = request["candidates"][-1]["action"]
        if row["policy_id"] != "laya-typed-policy-v0" or row["selected_action"] != expected:
            raise SystemExit("C++ did not sample the supplied typed distribution")
        distribution = {c["action"]: c["probability"] for c in row["candidates"] if c["eligible"]}
        if distribution.get(expected) != 1.0 or any(value != 0.0 for action, value in distribution.items() if action != expected):
            raise SystemExit("trace does not preserve the sampled Laya distribution")
    if Handler.connections >= len(Handler.requests):
        raise SystemExit("C++ did not reuse its persistent Laya loopback connection")
    print(f"laya typed policy loopback smoke passed: {len(decisions)} decisions, "
          f"{len(Handler.requests)} requests over {Handler.connections} TCP connection(s)")


if __name__ == "__main__":
    main()
