"""Model-free typed-X/I contract test over loopback; never reads World."""

import json
import socketserver
import subprocess
import sys
import threading

from laya_typed_proxy import CHECKPOINT, request_hash


class Handler(socketserver.StreamRequestHandler):
    seen = []

    def handle(self):
        request = json.loads(self.rfile.readline())
        if request["candidates"] or "world" in request or "effort_target" in request:
            raise ValueError("semantic adapter leaked W or A^O mutation")
        self.seen.append(request)
        operation = request["operation"]
        if operation == "commitment_choice":
            options = request["options"]
            prior = request["state"]["commitment"]
            if prior == "none":
                selected = "continue"
            elif prior == "active":
                selected = "suspend"
            else:
                selected = "resume"
            probabilities = {name: int(name == selected) for name in options}
            response = {"model": CHECKPOINT, "request_hash": request_hash(request),
                        "weights": ",".join(f"{name}={value}" for name, value in probabilities.items())}
        elif operation == "appraisal_scores":
            scores = {name: 4 if name == "positive_outcome" else 0 for name in
                      ("goal_progress", "goal_obstruction", "stimulation", "uncertainty",
                       "positive_outcome", "negative_outcome", "control_restored")}
            response = {"model": CHECKPOINT, "request_hash": request_hash(request),
                        "scores": ",".join(f"{name}={value}" for name, value in scores.items())}
        else:
            raise ValueError("unexpected semantic operation")
        self.wfile.write((json.dumps(response) + "\n").encode())


class LoopbackServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: laya_semantic_contract_smoke.py BINARY")
    with LoopbackServer(("127.0.0.1", 0), Handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        subprocess.run([sys.argv[1], str(server.server_address[1])], check=True, timeout=20)
        server.shutdown()
        thread.join(timeout=5)
    if [row["operation"] for row in Handler.seen].count("commitment_choice") != 3:
        raise SystemExit("expected three typed commitment transitions")
    if [row["operation"] for row in Handler.seen].count("appraisal_scores") != 1:
        raise SystemExit("expected one seven-channel typed appraisal")
    print("laya_semantic_contract_smoke: PASS")


if __name__ == "__main__":
    main()
