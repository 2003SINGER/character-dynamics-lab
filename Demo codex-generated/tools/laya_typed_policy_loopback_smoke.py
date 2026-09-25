"""Model-free wire contract for actual Laya typed probability integration."""

import json
import os
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
        history_requests = list(Handler.requests)
        history_connections = Handler.connections
    decisions = [row for row in rows if row["policy_evaluated"]]
    if not decisions or len(decisions) != len(Handler.requests):
        raise SystemExit("typed policy did not receive one request per decision")
    for request, row in zip(Handler.requests, decisions):
        if set(request) - {"request_id", "timestamp", "profile", "personality", "state", "observation", "candidates",
                           "running_action", "recent_history", "recent_factual_summary"}:
            raise SystemExit("typed request leaked outside O/S/P/I/A^O")
        if "world" in request or any("probability" in c for c in request["candidates"]):
            raise SystemExit("typed request leaked World or rule π")
        facts = {item[0]: item[1] for item in request["observation"]}
        total_minutes = int(request["timestamp"])
        expected_clock = f"Day {total_minutes // 1440 + 1} {total_minutes % 1440 // 60:02d}:{total_minutes % 60:02d}"
        if facts.get("clock.total_minutes") != str(total_minutes) or facts.get("clock.time") != expected_clock:
            raise SystemExit("typed request contains inconsistent scheduler-derived clock facts")
        if any(not isinstance(c.get("planned_minutes"), int) or c["planned_minutes"] <= 0
               for c in request["candidates"]):
            raise SystemExit("typed request omitted a positive planned duration")
        if "recent_history" not in request or "recent_factual_summary" not in request:
            raise SystemExit("v4 typed request omitted actor-local temporal history")
        if request["recent_factual_summary"].get("window_h") != 48:
            raise SystemExit("v4 factual summary omitted its explicit 48-hour window")
        if "reason" in request["candidates"][0] or "probability" in request["candidates"][0]:
            raise SystemExit("Laya candidate payload leaked Rule preference or probability")
        if "purchase_urge" not in request["state"] or "commitment_started_at_total_minutes" not in request["state"]:
            raise SystemExit("v4 typed request omitted purchase urge or commitment start time")
        if any(not c.get("hard_admissible") or "rule_soft_eligible" not in c for c in row["candidates"]):
            raise SystemExit("Laya candidate trace omitted hard-admissibility / Rule-soft provenance")
        expected = request["candidates"][-1]["action"]
        if row["policy_id"] != "laya-typed-policy-v0" or row["selected_action"] != expected:
            raise SystemExit("C++ did not sample the supplied typed distribution")
        distribution = {c["action"]: c["probability"] for c in row["candidates"] if c["eligible"]}
        if distribution.get(expected) != 1.0 or any(value != 0.0 for action, value in distribution.items() if action != expected):
            raise SystemExit("trace does not preserve the sampled Laya distribution")
    if history_connections >= len(history_requests):
        raise SystemExit("C++ did not reuse its persistent Laya loopback connection")
    dump = os.environ.get("LAYA_V4_REQUEST_DUMP")
    if dump:
        pathlib.Path(dump).write_text(json.dumps(max(history_requests, key=lambda item: len(json.dumps(item))),
                                                ensure_ascii=False))
    with LoopbackServer(("127.0.0.1", 0), Handler) as server, tempfile.TemporaryDirectory() as directory:
        Handler.requests = []
        Handler.connections = 0
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        trace = pathlib.Path(directory) / "no-history-trace.json"
        result = subprocess.run(
            [sys.argv[1], "17", "101", str(trace), "balanced", "--laya-port",
             str(server.server_address[1]), "--laya-no-history"],
            text=True, capture_output=True, timeout=45,
        )
        server.shutdown()
        thread.join(timeout=5)
        if result.returncode:
            raise SystemExit(result.stderr or f"no-history free run failed: {result.returncode}")
        no_history_requests = list(Handler.requests)
    if len(history_requests) != len(no_history_requests):
        raise SystemExit("v4 history and no-history control had different decision counts")
    invariant_keys = {"timestamp", "profile", "personality", "state", "observation", "candidates", "running_action"}
    for with_history, without_history in zip(history_requests, no_history_requests):
        if any(with_history.get(key) != without_history.get(key) for key in invariant_keys):
            raise SystemExit("v4 no-history ablation changed a non-history request field")
        if without_history["recent_history"] != {"episodes": [], "observed_events": []}:
            raise SystemExit("v4 no-history request did not use an empty history object")
        if without_history["recent_factual_summary"].get("actions"):
            raise SystemExit("v4 no-history request retained action summary history")
    if not any(request["recent_history"]["episodes"] for request in history_requests):
        raise SystemExit("v4 request never included a completed actor episode")
    for request in history_requests:
        starts = [episode[2] for episode in request["recent_history"]["episodes"]]
        if starts != sorted(starts):
            raise SystemExit("v4 recent episodes were not in chronological order")
    print(f"laya typed policy loopback smoke passed: {len(decisions)} decisions, "
          f"{len(history_requests)} history requests and a matching no-history control")


if __name__ == "__main__":
    main()
