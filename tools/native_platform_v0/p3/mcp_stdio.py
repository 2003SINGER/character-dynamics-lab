"""Small MCP stdio adapter for the private loopback P3 control service.

Only the MCP initialize/list/call surface is implemented. Game mutations stay
inside the Evennia server process and are never performed by this client.
"""

from __future__ import annotations

import json
import subprocess
import socket
import sys
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[3]
TOKEN_PATH = PROJECT_ROOT / "_local_data/native_platform_v0/p3/control.token"
HOST = "127.0.0.1"
PORT = 14011
MAX_LINE = 64 * 1024
SOCKET_TIMEOUT = 30
SUPPORTED_PROTOCOLS = {"2025-06-18", "2025-11-25"}

TOOLS = [
    {"name": "start_world", "description": "Start the existing local Evennia game using its scoped CLI wrapper.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "stop_world", "description": "Stop only the local Evennia instance using its scoped CLI wrapper.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "health", "description": "Check the authenticated local P3 control service.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
    {"name": "reset_scenario", "description": "Create a fresh isolated P3 scene in manual or timer drive; never resets the world.",
     "inputSchema": {"type": "object", "properties": {
         "mode": {"type": "string", "enum": ["a", "b"]},
         "seed": {"type": "integer", "minimum": 0, "maximum": 2147483647},
         "drive_mode": {"type": "string", "enum": ["manual", "timer"]},
         "interval": {"type": "integer", "minimum": 2, "maximum": 30},
         "activity_profile": {"type": "string", "enum": ["legacy_delivery_v0", "delivery_patrol_v0",
                                                                "delivery_patrol_recovery_v0"]},
         "delivery_task": {"type": "boolean"}, "patrol_exit_locked": {"type": "boolean"}},
         "additionalProperties": False}},
    {"name": "pause_scenario", "description": "Pause only generated P3 actors in the named scene; preserve state and logs.",
     "inputSchema": {"type": "object", "properties": {
         "scene_id": {"type": "string", "pattern": "^[A-Za-z0-9_-]{1,80}$"}},
         "required": ["scene_id"], "additionalProperties": False}},
    {"name": "step_world", "description": "Advance generated P3 actors through real manual script callbacks.",
     "inputSchema": {"type": "object", "properties": {
         "scene_id": {"type": "string", "pattern": "^[A-Za-z0-9_-]{1,80}$"},
         "rounds": {"type": "integer", "minimum": 1, "maximum": 50}},
         "required": ["scene_id"], "additionalProperties": False}},
    {"name": "inject_action", "description": "Issue one whitelisted real Evennia command to a generated scene role.",
     "inputSchema": {"type": "object", "properties": {
         "scene_id": {"type": "string", "pattern": "^[A-Za-z0-9_-]{1,80}$"},
         "actor_role": {"type": "string", "enum": ["player", "courier", "resident"]},
         "operation": {"type": "string", "enum": ["move", "get", "drop", "look", "inventory", "say"]},
         "direction": {"type": "string", "enum": ["east", "west"]},
         "item_id": {"type": "integer", "minimum": 1},
         "text": {"type": "string", "minLength": 1, "maxLength": 300}},
         "required": ["scene_id", "actor_role", "operation"], "additionalProperties": False}},
    {"name": "observe_actor", "description": "Return one generated actor's local observation only.",
     "inputSchema": {"type": "object", "properties": {
         "scene_id": {"type": "string", "pattern": "^[A-Za-z0-9_-]{1,80}$"},
         "actor_role": {"type": "string", "enum": ["player", "courier", "resident"]}},
         "required": ["scene_id", "actor_role"], "additionalProperties": False}},
    {"name": "get_trace", "description": "Read full live logs and bounded generated-scene P3/social evidence.",
     "inputSchema": {"type": "object", "properties": {
         "scene_id": {"type": "string", "pattern": "^[A-Za-z0-9_-]{1,80}$"}},
         "required": ["scene_id"], "additionalProperties": False}},
    {"name": "run_scenario", "description": "Run one bounded autonomous P3 scenario with explicit test interventions.",
     "inputSchema": {"type": "object", "properties": {
         "scenario": {"type": "string", "enum": ["Aclean", "Asteal-return", "Bclean", "Bsteal-resident-parcel"]},
         "seed": {"type": "integer", "minimum": 0, "maximum": 2147483647}},
         "required": ["scenario"], "additionalProperties": False}},
    {"name": "run_c0_scenario", "description": "Run exactly one bounded P3-C0 development case with no authored in-run commands.",
     "inputSchema": {"type": "object", "properties": {
         "scenario": {"type": "string", "enum": ["C0-no-delivery", "C0-delivery-priority", "C0-after-delivery"]},
         "seed": {"type": "integer", "minimum": 0, "maximum": 2147483647}},
         "required": ["scenario"], "additionalProperties": False}},
    {"name": "run_c1a_scenario", "description": "Run one of exactly two bounded native recovery development cases.",
     "inputSchema": {"type": "object", "properties": {
         "scenario": {"type": "string", "enum": ["C1a-blocked-switch", "C1a-observed-resume"]},
         "seed": {"type": "integer", "minimum": 0, "maximum": 2147483647}},
         "required": ["scenario"], "additionalProperties": False}},
    {"name": "run_p4_scenario", "description": "Run one bounded P4-0 native two-NPC scenario; returns a recorded development trace, not an acceptance verdict.",
     "inputSchema": {"type": "object", "properties": {
         "case": {"type": "string", "enum": ["open", "blocked-return", "blocked-held", "short-deadline"]},
         "director_enabled": {"type": "boolean"},
         "seed": {"type": "integer", "enum": [20261010, 20261011]}},
         "required": ["case", "director_enabled", "seed"], "additionalProperties": False}},
    {"name": "reset_p5_scenario", "description": "Create one isolated P5 scene from a validated external author bundle; no global world reset.",
     "inputSchema": {"type": "object", "properties": {
         "bundle": {"type": "object"},
         "initial_social_preset": {"type": "string", "enum": ["native_default_reject_v0", "hero_intelligence_30_v0"]},
         "horizon": {"type": "integer", "minimum": 1, "maximum": 24},
         "seed": {"type": "integer", "minimum": 0, "maximum": 2147483647},
         "director_enabled": {"type": "boolean"},
         "shared_supply": {"type": "boolean"},
         "initial_main_open": {"type": "boolean"}},
         "required": ["bundle"], "additionalProperties": False}},
    {"name": "run_p5_scenario", "description": "Run a bounded P5 bundle through native server callbacks and return raw evidence, not a semantic verdict.",
     "inputSchema": {"type": "object", "properties": {
         "bundle": {"type": "object"},
         "initial_social_preset": {"type": "string", "enum": ["native_default_reject_v0", "hero_intelligence_30_v0"]},
         "horizon": {"type": "integer", "minimum": 1, "maximum": 24},
         "interventions": {"type": "array", "items": {"type": "object"}},
         "edits": {"type": "array", "items": {"type": "object"}},
         "director_enabled": {"type": "boolean"},
         "seed": {"type": "integer", "minimum": 0, "maximum": 2147483647},
         "shared_supply": {"type": "boolean"},
         "initial_main_open": {"type": "boolean"}},
         "required": ["bundle", "initial_social_preset", "horizon"], "additionalProperties": False}},
    {"name": "edit_author_bundle", "description": "Attempt one version-checked P5 author-bundle edit on a named generated scene.",
     "inputSchema": {"type": "object", "properties": {
         "scene_id": {"type": "string", "pattern": "^[A-Za-z0-9_-]{1,80}$"},
         "raw_bundle": {"type": "object"},
         "expected_version": {"type": "integer", "minimum": 1}},
         "required": ["scene_id", "raw_bundle", "expected_version"], "additionalProperties": False}},
]
TOOL_BY_NAME = {tool["name"]: tool for tool in TOOLS}


def rpc_call(operation: str, args: dict[str, Any]) -> Any:
    if operation in ("start_world", "stop_world"):
        if args:
            raise ValueError(f"{operation} takes no arguments")
        script = PROJECT_ROOT / "tools/native_platform_v0/evennia" / (
            "start_loopback.sh" if operation == "start_world" else "stop_loopback.sh")
        completed = subprocess.run(["bash", str(script)], cwd=PROJECT_ROOT, text=True,
                                   stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   timeout=120, check=False)
        # CLI output is bounded and stripped of ANSI controls before returning.
        output = completed.stdout[-4000:]
        return {"status": "STARTED" if operation == "start_world" and completed.returncode == 0 else
                           "STOPPED" if operation == "stop_world" and completed.returncode == 0 else "FAILED",
                "exit_code": completed.returncode, "output_tail": output}
    token = TOKEN_PATH.read_text(encoding="utf-8").strip()
    if len(token) < 32:
        raise RuntimeError("local P3 token is invalid")
    request = json.dumps({"token": token, "request_id": "mcp-1", "op": operation,
                          "args": args}, separators=(",", ":")).encode("utf-8") + b"\n"
    with socket.create_connection((HOST, PORT), timeout=SOCKET_TIMEOUT) as connection:
        connection.settimeout(SOCKET_TIMEOUT)
        connection.sendall(request)
        chunks = bytearray()
        while len(chunks) <= 16 * 1024 * 1024:
            part = connection.recv(65536)
            if not part:
                break
            chunks.extend(part)
            if b"\n" in part:
                break
    if len(chunks) > 16 * 1024 * 1024 or b"\n" not in chunks:
        raise RuntimeError("local P3 control response exceeded bounds or was incomplete")
    response = json.loads(bytes(chunks).split(b"\n", 1)[0].decode("utf-8"))
    if not response.get("ok"):
        raise RuntimeError(f"P3 control rejected operation ({response.get('error_type', 'control error')})")
    return response.get("result")


def handle_message(message: dict[str, Any], call_rpc: Callable[[str, dict[str, Any]], Any] = rpc_call):
    if not isinstance(message, dict):
        return None
    method = message.get("method")
    request_id = message.get("id")
    has_id = "id" in message
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": request_id, "result": {}}
    if method == "initialize":
        params = message.get("params") or {}
        requested_version = params.get("protocolVersion")
        version = requested_version if requested_version in SUPPORTED_PROTOCOLS else "2025-06-18"
        return {"jsonrpc": "2.0", "id": request_id, "result": {
            "protocolVersion": version,
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "native-p3-local-control", "version": "0.1.0"}}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = message.get("params") or {}
        name = params.get("name")
        arguments = params.get("arguments", {})
        if name not in TOOL_BY_NAME or not isinstance(arguments, dict):
            error = {"code": -32602, "message": "unknown tool or arguments must be an object"}
            return {"jsonrpc": "2.0", "id": request_id, "error": error} if has_id else None
        try:
            result = call_rpc(name, arguments)
            content = [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}]
            return {"jsonrpc": "2.0", "id": request_id, "result": {"content": content,
                    "structuredContent": result, "isError": False}}
        except Exception as exc:
            return {"jsonrpc": "2.0", "id": request_id, "result": {
                "content": [{"type": "text", "text": f"P3 control failed: {type(exc).__name__}"}],
                "isError": True}}
    if has_id:
        return {"jsonrpc": "2.0", "id": request_id,
                "error": {"code": -32601, "message": "method not found"}}
    return None


def main() -> int:
    for raw in sys.stdin.buffer:
        if len(raw) > MAX_LINE:
            # JSON-RPC parse error, with no details from the oversized payload.
            response = {"jsonrpc": "2.0", "id": None,
                        "error": {"code": -32700, "message": "message exceeds size limit"}}
        else:
            try:
                message = json.loads(raw.decode("utf-8"))
                response = handle_message(message)
            except Exception:
                response = {"jsonrpc": "2.0", "id": None,
                            "error": {"code": -32700, "message": "invalid JSON-RPC message"}}
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False, separators=(",", ":")) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
