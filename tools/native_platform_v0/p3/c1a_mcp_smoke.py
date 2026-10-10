"""Exercise the real MCP stdio subprocess with one bounded C0 tool call."""

from __future__ import annotations

from datetime import datetime, timezone
import argparse
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.native_platform_v0.p3.c1a_runner import RUNS_DIR, SOURCE_FILES


MCP_SCRIPT = PROJECT_ROOT / "tools/native_platform_v0/p3/mcp_stdio.py"
SMOKE_SOURCES = tuple(sorted(set(SOURCE_FILES) | {"tools/native_platform_v0/p3/c1a_mcp_smoke.py"}))


def manifest() -> dict:
    hashes = {name: hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest()
              if (PROJECT_ROOT / name).is_file() else "missing" for name in SMOKE_SOURCES}
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT,
                              text=True, capture_output=True, check=False)
    packed = json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"git_revision": revision.stdout.strip() if revision.returncode == 0 else None,
            "hash_scope": "sha256 of actual working-tree source bytes; revision is base commit only",
            "source_sha256": hashes,
            "source_snapshot_sha256": hashlib.sha256(packed).hexdigest()}


def run_smoke(seed: int = 20261010) -> dict:
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                    "clientInfo": {"name": "native-p3-c1a-smoke", "version": "0.1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "run_c0_scenario",
                    "arguments": {"scenario": "C0-delivery-priority", "seed": seed}}},
    ]
    completed = subprocess.run([sys.executable, str(MCP_SCRIPT)], cwd=PROJECT_ROOT,
                               input="".join(json.dumps(row, separators=(",", ":")) + "\n"
                                             for row in requests),
                               text=True, capture_output=True, timeout=180, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"MCP stdio subprocess exited {completed.returncode}")
    try:
        messages = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
    except json.JSONDecodeError as exc:
        raise RuntimeError("MCP stdio subprocess emitted non-JSON stdout") from exc
    if len(messages) != 2 or [message.get("id") for message in messages] != [1, 2]:
        raise RuntimeError("MCP stdio initialize/tool-call response sequence was incomplete")
    initialize, tool_call = messages
    if initialize.get("result", {}).get("protocolVersion") != "2025-06-18":
        raise RuntimeError("MCP stdio protocol negotiation failed")
    result = tool_call.get("result", {})
    if result.get("isError") is not False or not isinstance(result.get("structuredContent"), dict):
        raise RuntimeError("MCP stdio run_c0_scenario tool call failed")
    return {"schema": "native-p3-c1a-mcp-smoke-response-v1", "messages": messages,
            "scenario": "C0-delivery-priority", "seed": seed}


def write_result(document: dict, runs_dir: Path = RUNS_DIR) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for _ in range(8):
        target = runs_dir / f"p3-c1a-mcp-smoke-seed{document['seed']}-{timestamp}-{secrets.token_hex(3)}.json"
        try:
            with target.open("x", encoding="utf-8") as handle:
                json.dump(document, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            return target
        except FileExistsError:
            continue
    raise FileExistsError("could not allocate a unique C1a MCP smoke output")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20261010)
    args = parser.parse_args(argv)
    if not 0 <= args.seed <= 2**31 - 1:
        parser.error("--seed must be in 0..2147483647")
    try:
        response = run_smoke(args.seed)
        document = {"recorded_at": datetime.now(timezone.utc).isoformat(),
                    "manifest": manifest(), "response": response,
                    "scenario": response["scenario"], "seed": response["seed"]}
        output = write_result(document)
    except Exception as exc:
        print(json.dumps({"status": "FAILED", "error_type": type(exc).__name__}, ensure_ascii=False))
        return 1
    print(json.dumps({"status": "RECORDED", "path": str(output),
                      "scenario": response["scenario"], "seed": response["seed"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
