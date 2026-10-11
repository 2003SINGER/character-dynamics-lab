#!/usr/bin/env python3
"""Run the unmodified Sabre CLI and preserve its native output and metadata."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_JAVA = (
    REPO_ROOT
    / "_local_data/planner_p0_v0/jdk/jdk-17.0.20.1+1/Contents/Home/bin/java"
)
DEFAULT_CLASSPATH = REPO_ROOT / "_local_data/planner_p0_v0/sabre/bin"
EVIDENCE_ROOT = REPO_ROOT / "02_实验/Planner_P0_v0/sabre_baseline/evidence"
DEFAULT_OUTPUT = EVIDENCE_ROOT


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def parse_native_output(stdout: str, stderr: str = "") -> dict[str, object]:
    result_line = next(
        (line.strip() for line in stdout.splitlines() if line.startswith("Result:")),
        None,
    )
    result_reason = result_line.removeprefix("Result:").strip() if result_line else None
    if result_line and "Success" in result_line:
        status = "SUCCESS"
    elif result_reason and any(
        marker in result_reason.lower()
        for marker in ("search limit", "space limit", "time limit")
    ):
        status = "BUDGET_LIMIT"
    elif result_reason and "no solution exists" in result_reason.lower():
        status = "NATIVE_NO_SOLUTION"
    elif "NoClassDefFoundError" in stdout + stderr:
        status = "NATIVE_STARTUP_ERROR"
    elif "Error:" in stdout or "Error:" in stderr or "ClassNotFoundException" in stdout + stderr:
        status = "NATIVE_ERROR"
    else:
        status = "NATIVE_UNKNOWN"

    lines = stdout.splitlines()
    plan_actions: list[str] = []
    started_plan = False
    for line in lines:
        if not started_plan:
            if line.startswith("Result:"):
                started_plan = True
            continue
        if line.startswith("goal("):
            break
        if line.startswith("|"):
            continue
        candidate = line.strip()
        if re.fullmatch(r"[A-Za-z_][\w-]*\(.*\)", candidate):
            plan_actions.append(candidate)

    def number(pattern: str) -> int | float | None:
        match = re.search(pattern, stdout)
        if not match:
            return None
        value = match.group(1).replace(",", "")
        return float(value) if "." in value else int(value)

    utility = number(r"utility achieved:\s*([-+]?\d[\d,]*(?:\.\d+)?)")
    elapsed_line = re.search(r"^\s*time:\s*(.*?)\s*$", stdout, re.MULTILINE)
    elapsed_ms = None
    elapsed_text = None
    elapsed_warning = None
    if elapsed_line:
        elapsed_text = elapsed_line.group(1)
        elapsed = re.fullmatch(r"(\d+(?:\.\d+)?)\s*(ms|s)", elapsed_text)
        if elapsed:
            elapsed_ms = float(elapsed.group(1)) * (1000 if elapsed.group(2) == "s" else 1)
        else:
            elapsed_warning = "native duration format was not a single number with ms or s"

    return {
        "status": status,
        "native_result": result_reason,
        "utility_achieved": utility,
        "nodes_visited": number(r"nodes visited:\s*([\d,]+)"),
        "nodes_generated": number(r"nodes generated:\s*([\d,]+)"),
        "elapsed_native_text": elapsed_text,
        "elapsed_native_ms": elapsed_ms,
        "elapsed_native_parse_warning": elapsed_warning,
        "plan_actions": plan_actions,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--problem", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--java", type=Path, default=DEFAULT_JAVA)
    parser.add_argument("--classpath", type=Path, default=DEFAULT_CLASSPATH)
    parser.add_argument("--main-class", default="edu.uky.cs.nil.sabre.Main")
    parser.add_argument("--planner-version", default="Sabre v0.8.0")
    parser.add_argument("--method", choices=("bf", "ef", "gf"), default="bf")
    parser.add_argument("--cost", choices=("0", "n", "x", "t"), default="t")
    parser.add_argument("--heuristic", choices=("0", "r", "hmax", "h+", "rp"), default="h+")
    parser.add_argument("--goal-utility", type=float)
    parser.add_argument("--epistemic-limit", type=int, default=1)
    parser.add_argument("--max-visited", type=int, default=200)
    parser.add_argument("--max-generated", type=int, default=0)
    parser.add_argument("--time-limit-ms", type=int, default=5000)
    parser.add_argument("--process-timeout-s", type=float, default=30.0)
    parser.add_argument("--author-limit", type=int)
    parser.add_argument("--character-limit", type=int)
    parser.add_argument("--heap-min", default="64m")
    parser.add_argument("--heap-max", default="1g")
    parser.add_argument("--stack-size", default="1m", help="JVM thread stack, e.g. 1m or 8m")
    args = parser.parse_args()

    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,95}", args.run_id):
        parser.error("run-id must be a 1-96 character slug using letters, digits, '_' or '-'")
    if not re.fullmatch(r"[1-9][0-9]*[kKmMgG]", args.stack_size):
        parser.error("stack-size must be a positive JVM size such as 512k, 1m, or 8m")

    problem = args.problem.resolve()
    java = args.java.resolve()
    classpath = args.classpath.resolve()
    run_dir = (args.output_root / args.run_id).resolve()
    evidence_root = EVIDENCE_ROOT.resolve()
    output_root = args.output_root.resolve()
    if not output_root.is_relative_to(evidence_root):
        parser.error(f"output-root must be inside {evidence_root}")
    if not problem.is_file():
        parser.error(f"problem file does not exist: {problem}")
    if not java.is_file():
        parser.error(f"Java executable does not exist: {java}")
    if not classpath.exists():
        parser.error(f"Sabre classpath does not exist: {classpath}")
    if run_dir.exists():
        parser.error(f"run directory already exists; refusing to overwrite: {run_dir}")

    command = [
        str(java),
        f"-Xms{args.heap_min}",
        f"-Xmx{args.heap_max}",
        f"-Xss{args.stack_size}",
        "-Duser.language=en",
        "-Duser.country=US",
        "-Duser.timezone=UTC",
        "-cp",
        str(classpath),
        args.main_class,
        "-v",
        "-p",
        str(problem),
        "-m",
        args.method,
        "-c",
        args.cost,
        "-h",
        args.heuristic,
        "-el",
        str(args.epistemic_limit),
        "-vl",
        str(args.max_visited),
        "-gl",
        str(args.max_generated),
        "-tl",
        str(args.time_limit_ms),
    ]
    if args.goal_utility is not None:
        command.extend(("-g", str(args.goal_utility)))
    if args.author_limit is not None:
        command.extend(("-atl", str(args.author_limit)))
    if args.character_limit is not None:
        command.extend(("-ctl", str(args.character_limit)))

    run_dir.mkdir(parents=True)
    config = {
        "run_id": args.run_id,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "planner_version": args.planner_version,
        "planner_configuration": {
            "method": args.method,
            "cost_measure": args.cost,
            "heuristic": args.heuristic,
            "goal_utility": args.goal_utility,
            "epistemic_limit": args.epistemic_limit,
        },
        "problem_path": str(problem),
        "problem_sha256": sha256(problem),
        "java_executable": str(java),
        "classpath": str(classpath),
        "command": command,
        "environment": {"LANG": "C", "TZ": "UTC"},
        "java_stack_size": args.stack_size,
        "wrapper_process_timeout_s": args.process_timeout_s,
        "limits": {
            "max_visited": args.max_visited,
            "max_generated": args.max_generated,
            "time_limit_ms": args.time_limit_ms,
            "author_limit": args.author_limit,
            "character_limit": args.character_limit,
            "epistemic_limit": args.epistemic_limit,
        },
    }
    (run_dir / "config.json").write_text(json.dumps(config, indent=2) + "\n")

    environment = os.environ.copy()
    environment.update({"LANG": "C", "TZ": "UTC"})
    process_started = datetime.now(timezone.utc)
    try:
        completed = subprocess.run(
            command,
            cwd=run_dir,
            env=environment,
            capture_output=True,
            text=True,
            check=False,
            timeout=args.process_timeout_s,
        )
        stdout = completed.stdout
        stderr = completed.stderr
        exit_code = completed.returncode
        parsed = parse_native_output(stdout, stderr)
        wrapper_status = None
    except subprocess.TimeoutExpired as error:
        def decode_output(value: str | bytes | None) -> str:
            if value is None:
                return ""
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")
            return value

        stdout = decode_output(error.stdout)
        stderr = decode_output(error.stderr)
        exit_code = None
        parsed = {
            "status": "PROCESS_TIMEOUT",
            "native_result": f"wrapper subprocess exceeded {args.process_timeout_s:g} seconds",
            "utility_achieved": None,
            "nodes_visited": None,
            "nodes_generated": None,
            "elapsed_native_text": None,
            "elapsed_native_ms": None,
            "elapsed_native_parse_warning": None,
            "plan_actions": [],
        }
        wrapper_status = 124
    (run_dir / "stdout.log").write_text(stdout)
    (run_dir / "stderr.log").write_text(stderr)
    record = {
        **parsed,
        "run_id": args.run_id,
        "planner_version": args.planner_version,
        "native_cost_measure": args.cost,
        "java_stack_size": args.stack_size,
        "wrapper_process_timeout_s": args.process_timeout_s,
        "wrapper_started_at_utc": process_started.isoformat(),
        "wrapper_finished_at_utc": datetime.now(timezone.utc).isoformat(),
        "exit_code": exit_code,
        "run_dir": str(run_dir),
        "stdout_path": str(run_dir / "stdout.log"),
        "stderr_path": str(run_dir / "stderr.log"),
    }
    (run_dir / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, separators=(",", ":")))
    return wrapper_status if wrapper_status is not None else exit_code


if __name__ == "__main__":
    raise SystemExit(main())
