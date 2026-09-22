"""Strictly local bridge from DemoLayaPolicyV0 to llama-server.

The companion C++ policy sends O/S/P plus eligible A^O over loopback only.
This bridge talks only to http://127.0.0.1:8080/v1, records a local cassette,
and supports cassette replay. It deliberately has no remote endpoint option.
"""
import argparse
import hashlib
import json
import pathlib
import re
import socketserver
import threading
import urllib.request


def request_hash(request):
    body = dict(request); body.pop("request_id", None)
    return hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def extract_action(content, allowed):
    matches = re.findall(r'"action"\s*:\s*"([a-z_]+)"', content)
    if matches and matches[-1] in allowed:
        return matches[-1]
    found = [item for item in allowed if re.search(rf"\b{re.escape(item)}\b", content)]
    if len(found) == 1:
        return found[0]
    raise ValueError("local model did not select one eligible action")


class Bridge:
    def __init__(self, model, cassette, replay):
        self.model, self.cassette, self.lock = model, cassette, threading.Lock()
        self.replay = {}
        if replay:
            for line in replay.read_text().splitlines():
                row = json.loads(line)
                if row.get("type") == "laya_decision": self.replay.setdefault(row["request_hash"], row)

    def choose(self, request):
        key, allowed = request_hash(request), {item["action"] for item in request["candidates"]}
        if not allowed: raise ValueError("no eligible candidates")
        if key in self.replay:
            action = self.replay[key]["action"]
            if action not in allowed: raise ValueError("cassette action outside current A^O")
            return {"action": action, "request_hash": key, "mode": "cassette-replay"}
        messages = [
            {"role": "system", "content": "You are LayaPolicyV0. Select exactly one supplied eligible action. You see only O, S, P and candidates. Never invent actions or world facts. Return JSON only: {\"action\":\"candidate\",\"rationale\":\"short\"}."},
            {"role": "user", "content": json.dumps({"time": request.get("timestamp"), "personality": request["personality"], "state": request["state"], "observation": request["observation"], "eligible_candidates": request["candidates"]}, ensure_ascii=False, separators=(",", ":"))},
        ]
        # Qwen3 otherwise spends the small bounded completion budget in its
        # reasoning channel and can return an empty visible action.
        payload = json.dumps({"model": self.model, "messages": messages,
                              "chat_template_kwargs": {"enable_thinking": False},
                              "temperature": 0, "max_tokens": 80, "stream": False}).encode()
        call = urllib.request.Request("http://127.0.0.1:8080/v1/chat/completions", data=payload, headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(call, timeout=90) as response:
            content = json.loads(response.read())["choices"][0]["message"]["content"]
        action = extract_action(content, allowed)
        row = {"type": "laya_decision", "request_hash": key, "request": request, "action": action,
               "model": self.model, "temperature": 0, "response_sha256": hashlib.sha256(content.encode()).hexdigest()}
        with self.lock:
            self.cassette.parent.mkdir(parents=True, exist_ok=True)
            with self.cassette.open("a") as handle: handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
        return {"action": action, "request_hash": key, "mode": "local-qwen"}


class Handler(socketserver.StreamRequestHandler):
    bridge = None
    def handle(self):
        try:
            request = json.loads(self.rfile.readline())
            response = self.bridge.choose(request)
        except Exception as error:
            response = {"error": str(error)}
        self.wfile.write((json.dumps(response) + "\n").encode())


class LoopbackServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--cassette", type=pathlib.Path, required=True)
    parser.add_argument("--replay", type=pathlib.Path)
    parser.add_argument("--port", type=int, default=8742)
    args = parser.parse_args()
    Handler.bridge = Bridge(args.model, args.cassette, args.replay)
    service = LoopbackServer(("127.0.0.1", args.port), Handler)
    print(json.dumps({"service": "laya-policy-proxy-v0", "bind": "127.0.0.1", "port": args.port, "model": args.model, "replay": bool(args.replay)}), flush=True)
    service.serve_forever()


if __name__ == "__main__": main()
