"""Actor-history, hidden-W and Rule-input noninterference wire contract."""

import json
import socketserver
import subprocess
import sys
import threading


class Handler(socketserver.StreamRequestHandler):
    requests = []

    def handle(self):
        for line in self.rfile:
            request = json.loads(line)
            self.requests.append(request)
            probability = 1.0 / len(request["candidates"])
            weights = ",".join(f"{c['action']}={probability}" for c in request["candidates"])
            self.wfile.write((json.dumps({"model": "convaiinnovations/laya-typed-decisions",
                                          "weights": weights, "request_hash": "contract"}) + "\n").encode())


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def without_id(request):
    return {key: value for key, value in request.items() if key != "request_id"}


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: laya_history_projection_contract.py TEST_BINARY")
    Handler.requests = []
    with Server(("127.0.0.1", 0), Handler) as server:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        result = subprocess.run([sys.argv[1], str(server.server_address[1])],
                                capture_output=True, text=True, timeout=10)
        server.shutdown()
        worker.join(timeout=3)
    if result.returncode:
        raise SystemExit(result.stderr or f"test binary failed: {result.returncode}")
    if len(Handler.requests) != 3:
        raise SystemExit(f"expected 3 requests, got {len(Handler.requests)}")
    a, b, c = map(without_id, Handler.requests)
    if a != b:
        raise SystemExit("hidden W / Rule preference perturbation changed the Laya request")
    if a == c:
        raise SystemExit("history-only change did not change the Laya request")
    rest_minutes = {item[0]: item[1] for item in a["recent_factual_summary"]["actions"]}
    if a["recent_factual_summary"].get("window_h") != 48 or rest_minutes.get("rest_at_bed") != 220:
        raise SystemExit("48h summary omitted a long episode's clipped window overlap")
    if any("probability" in candidate or "reason" in candidate or "activation" in candidate
           for candidate in a["candidates"]):
        raise SystemExit("Rule activation/probability/reason leaked into Laya request")
    print("laya history projection contract passed: hidden-W and Rule perturbations invariant; H perturbation visible")


if __name__ == "__main__":
    main()
