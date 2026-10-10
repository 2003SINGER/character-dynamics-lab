"""Record one paired-or-single P4-0 native Evennia scenario without grading it."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.native_platform_v0.p3.mcp_stdio import rpc_call

RUNS_DIR = PROJECT_ROOT / "02_实验/Native_Platform_P4_0_v0/runs"
CASES = ("open", "blocked-return", "blocked-held", "short-deadline")
SOURCE_FILES = (
    "tools/native_platform_v0/p3/p4_runner.py",
    "tools/native_platform_v0/p3/p4_monitor.py",
    "tools/native_platform_v0/p3/p4_audit.py",
    "tools/native_platform_v0/p3/control_service.py",
    "tools/native_platform_v0/p3/scene.py",
    "tools/native_platform_v0/p3/agency.py",
    "tools/native_platform_v0/p3/planning.py",
    "tools/native_platform_v0/p3/commands.py",
    "tools/native_platform_v0/p3/p4_world.py",
    "tools/native_platform_v0/p3/p4_social.py",
    "tools/native_platform_v0/p3/p4_agency.py",
    "tools/native_platform_v0/p3/mcp_stdio.py",
    "tools/native_platform_v0/p3/export_evidence.py",
    "tools/trajectory_constraints_v0/ast.py",
    "tools/trajectory_constraints_v0/compiler.py",
    "tools/trajectory_constraints_v0/monitor.py",
    "tools/trajectory_constraints_v0/trace.py",
    "tools/trajectory_constraints_v0/types.py",
    "tools/native_platform_v0/bridge/social.py",
    "tools/native_platform_v0/ensemble/runner.mjs",
)


def source_manifest() -> dict[str, object]:
    hashes = {
        name: hashlib.sha256((PROJECT_ROOT / name).read_bytes()).hexdigest()
        if (PROJECT_ROOT / name).is_file() else "missing"
        for name in SOURCE_FILES
    }
    packed = json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode("utf-8")
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT,
                              text=True, capture_output=True, check=False)
    return {
        "git_revision": revision.stdout.strip() if revision.returncode == 0 else None,
        "hash_scope": "sha256 of actual working-tree source bytes; revision is base commit only",
        "source_sha256": hashes,
        "source_snapshot_sha256": hashlib.sha256(packed).hexdigest(),
    }


def write_run(document: dict, runs_dir: Path = RUNS_DIR) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    config = document["configuration"]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for _ in range(8):
        target = runs_dir / (f"p4-{config['case']}-director-{config['director_enabled']}-"
                             f"seed{config['seed']}-{timestamp}-{secrets.token_hex(3)}.json")
        try:
            with target.open("x", encoding="utf-8") as handle:
                json.dump(document, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            return target
        except FileExistsError:
            continue
    raise FileExistsError("could not allocate unique P4 evidence filename")


def _mcp_stdio_call(case: str, director_enabled: bool, seed: int) -> tuple[dict[str, Any], dict[str, Any]]:
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                    "clientInfo": {"name": "native-p4-runner", "version": "0.1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "run_p4_scenario", "arguments": {
             "case": case, "director_enabled": director_enabled, "seed": seed}}},
    ]
    encoded = "".join(json.dumps(message, separators=(",", ":")) + "\n" for message in messages)
    completed = subprocess.run(
        [sys.executable, "-m", "tools.native_platform_v0.p3.mcp_stdio"],
        cwd=PROJECT_ROOT, input=encoded, text=True, capture_output=True,
        timeout=120, check=False,
    )
    try:
        replies = [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]
    except json.JSONDecodeError as err:
        raise RuntimeError("MCP stdio returned malformed JSON-RPC") from err
    if completed.returncode != 0 or len(replies) != 2:
        raise RuntimeError("MCP stdio transport did not return initialize and tool-call replies")
    init, tool_call = replies
    if init.get("id") != 1 or tool_call.get("id") != 2:
        raise RuntimeError("MCP stdio reply IDs do not match the request sequence")
    structured = tool_call.get("result", {}).get("structuredContent")
    if tool_call.get("result", {}).get("isError") is not False or not isinstance(structured, dict):
        raise RuntimeError("MCP stdio run_p4_scenario call was rejected")
    return structured, {"kind": "mcp-stdio", "messages": replies,
                        "process_exit_code": completed.returncode,
                        "stderr_tail": completed.stderr[-2000:],
                        "global_registration": False}


def run_one(case: str, director_enabled: bool, seed: int, *, mcp_stdio: bool = False) -> dict:
    request = {"case": case, "director_enabled": director_enabled, "seed": seed}
    if mcp_stdio:
        response, transport = _mcp_stdio_call(**request)
    else:
        response = rpc_call("run_p4_scenario", request)
        transport = {"kind": "authenticated-loopback-rpc"}
    if not isinstance(response, dict):
        raise ValueError("P4 control response must be an object")
    document = {
        "schema": "native-p4-run-artifact-v1",
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "configuration": {"case": case, "director_enabled": director_enabled, "seed": seed},
        "manifest": source_manifest(),
        "transport": transport,
        "response": response,
    }
    path = write_run(document)
    return {"run_status": response.get("run_status", "INCOMPLETE"),
            "artifact_saved": True, "semantic_acceptance": "not_evaluated_by_runner", "path": str(path),
            "case": case, "director_enabled": director_enabled, "seed": seed,
            "scene_id": response.get("created_scene", {}).get("scene_id")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASES, required=True)
    parser.add_argument("--director", choices=("on", "off"), required=True)
    parser.add_argument("--seed", type=int, choices=(20261010, 20261011), default=20261010)
    parser.add_argument("--paired", action="store_true",
                        help="run the same frozen case/seed once with each director arm")
    parser.add_argument("--mcp-stdio", action="store_true",
                        help="call run_p4_scenario through the local MCP stdio subprocess")
    args = parser.parse_args(argv)
    try:
        if args.mcp_stdio and args.paired:
            parser.error("--mcp-stdio is a single-arm transport check; pair the two recorded arm artifacts separately")
        results = [run_one(args.case, enabled, args.seed, mcp_stdio=args.mcp_stdio)
                   for enabled in ((False, True) if args.paired else (args.director == "on",))]
    except Exception as err:
        parser.error(f"P4 run failed before a complete record: {type(err).__name__}: {err}")
    complete = all(item["run_status"] == "COMPLETE" for item in results)
    print(json.dumps({"run_status": "COMPLETE" if complete else "INCOMPLETE",
                      "artifacts_saved": all(item["artifact_saved"] for item in results),
                      "semantic_acceptance": "not_evaluated_by_runner", "runs": results},
                     ensure_ascii=False))
    return 0 if complete else 2


if __name__ == "__main__":
    raise SystemExit(main())
