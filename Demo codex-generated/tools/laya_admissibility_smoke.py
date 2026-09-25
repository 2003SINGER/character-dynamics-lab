"""Exercise a Rule-soft-filtered but hard-admissible sleep through real C++ Laya selection."""

import json
import pathlib
import socketserver
import subprocess
import sys
import threading


class Handler(socketserver.StreamRequestHandler):
    request = None

    def handle(self):
        request = json.loads(self.rfile.readline())
        Handler.request = request
        if request.get("timestamp") != 8573:
            raise AssertionError("Laya request timestamp differs from scheduler boundary")
        facts = {item[0]: item[1] for item in request["observation"]}
        if facts.get("clock.time") != "Day 6 22:53" or facts.get("clock.total_minutes") != "8573":
            raise AssertionError("formatted and numeric O clocks disagree")
        sleeps = [item for item in request["candidates"] if item["action"] == "sleep_at_bed"]
        if len(sleeps) != 1 or sleeps[0].get("target") != "bed" or sleeps[0].get("planned_minutes") != 480:
            raise AssertionError("Laya did not receive O-known sleep target and duration")
        if "world" in request or any("probability" in item for item in request["candidates"]):
            raise AssertionError("request leaked World or Rule probability")
        weights = ",".join(f"{item['action']}={1 if item['action'] == 'sleep_at_bed' else 0}"
                            for item in request["candidates"])
        response = {"model": "convaiinnovations/laya-typed-decisions",
                    "weights": weights, "request_hash": "admissibility-smoke"}
        self.wfile.write((json.dumps(response) + "\n").encode())


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: laya_admissibility_smoke.py BINARY")
    with Server(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        result = subprocess.run([sys.argv[1], str(server.server_address[1])],
                                text=True, capture_output=True, timeout=30)
        server.shutdown()
        thread.join(timeout=5)
    if result.returncode:
        raise SystemExit(result.stderr or f"admissibility smoke failed: {result.returncode}")
    if Handler.request is None:
        raise SystemExit("C++ policy did not make a Laya request")
    print("laya admissibility smoke: PASS (soft-pruned sleep selected; 480-minute action started)")


if __name__ == "__main__":
    main()
