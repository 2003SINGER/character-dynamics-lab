"""Capture one real Runtime wire request, then stop before any model call."""

import json
import pathlib
import socketserver
import subprocess
import sys
import tempfile
import threading


class Handler(socketserver.StreamRequestHandler):
    request = None

    def handle(self):
        line = self.rfile.readline()
        if not line:
            return
        type(self).request = json.loads(line)
        self.wfile.write((json.dumps({"error": "diagnostic-stop-after-capture"}) + "\n").encode())


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: laya_capture_first_request.py LONG_HORIZON_BINARY REQUEST_OUT.json")
    binary = pathlib.Path(sys.argv[1]).resolve()
    request_path = pathlib.Path(sys.argv[2]).resolve()
    if request_path.exists():
        raise SystemExit(f"refusing to overwrite {request_path}")
    Handler.request = None
    with tempfile.TemporaryDirectory(prefix="laya-first-request-") as temp_dir:
        trace_path = pathlib.Path(temp_dir) / "aborted-trace.jsonl"
        with Server(("127.0.0.1", 0), Handler) as server:
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            result = subprocess.run(
                [str(binary), "17", "101", "1", "balanced", str(trace_path), "boundaries",
                 "--laya-port", str(server.server_address[1]), "--laya-no-history"],
                capture_output=True, text=True, timeout=30,
            )
            server.shutdown()
            worker.join(timeout=3)
    if Handler.request is None:
        raise SystemExit(f"Runtime did not send a request: {result.stderr}")
    if result.returncode == 0 or "diagnostic-stop-after-capture" not in result.stderr:
        raise SystemExit(f"Runtime did not stop at the intentional diagnostic response: {result.stderr}")
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request_path.write_text(json.dumps(Handler.request, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({
        "captured": str(request_path),
        "timestamp": Handler.request.get("timestamp"),
        "candidate_count": len(Handler.request.get("candidates", [])),
        "candidate_options": [candidate["action"] for candidate in Handler.request.get("candidates", [])],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
