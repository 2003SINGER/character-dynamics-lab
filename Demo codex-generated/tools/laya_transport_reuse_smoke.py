"""Verify the persistent client detects a stopped session and reconnects at a reused port."""

import json
import socketserver
import subprocess
import sys
import threading


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def make_handler(received, first_request_event=None, close_after_first=False):
    class Handler(socketserver.StreamRequestHandler):
        def handle(self):
            for line in self.rfile:
                request = json.loads(line)
                received.append(request)
                self.wfile.write((json.dumps({
                    "model": "convaiinnovations/laya-typed-decisions",
                    "weights": "idle=1", "request_hash": "transport-smoke"}) + "\n").encode())
                if first_request_event:
                    first_request_event.set()
                if close_after_first:
                    return
    return Handler


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: laya_transport_reuse_smoke.py BINARY")
    first_requests = []
    second_requests = []
    first_done = threading.Event()
    first = Server(("127.0.0.1", 0), make_handler(first_requests, first_done, True))
    port = first.server_address[1]
    first_thread = threading.Thread(target=first.serve_forever, daemon=True)
    first_thread.start()
    process = subprocess.Popen([sys.argv[1], str(port)], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True)
    try:
        if not first_done.wait(10):
            raise RuntimeError("first Laya request did not arrive")
        first.shutdown()
        first_thread.join(timeout=5)
        first.server_close()
        second = Server(("127.0.0.1", port), make_handler(second_requests))
        second_thread = threading.Thread(target=second.serve_forever, daemon=True)
        second_thread.start()
        stdout, stderr = process.communicate(timeout=10)
        second.shutdown()
        second_thread.join(timeout=5)
        second.server_close()
        if process.returncode:
            raise RuntimeError(stderr.strip() or f"client exited {process.returncode}; {stdout}")
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        if first.fileno() != -1:
            first.server_close()
    if len(first_requests) != 1 or len(second_requests) != 1:
        raise SystemExit(f"expected one request per proxy session, got {len(first_requests)} and {len(second_requests)}")
    print("laya transport reuse smoke: PASS (same-port proxy restart detected; no blind request retry)")


if __name__ == "__main__":
    main()
