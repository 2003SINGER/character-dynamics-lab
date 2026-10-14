#!/usr/bin/env python3
"""Run a fixed Open Adventure command transcript without interpreting game state."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GAME = PROJECT_ROOT / "_local_data/external_games/open_adventure/upstream"
DEFAULT_RUNS = PROJECT_ROOT / "02_实验/OpenAdventure_Native_v0/runs"
PINNED_COMMIT = "e6160529e70a8c7a06b9a5f190d69aa35c4c62f5"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_sha256(path: Path) -> tuple[str | None, str | None]:
    try:
        return sha256_bytes(path.read_bytes()), None
    except OSError as exc:
        return None, f"{type(exc).__name__}: {exc}"


def source_snapshot(game_root: Path) -> dict[str, Any]:
    tracked = subprocess.run(
        ["git", "ls-files", "-z"], cwd=game_root, capture_output=True, check=True
    ).stdout.split(b"\0")
    files = {}
    for raw_name in tracked:
        if not raw_name:
            continue
        name = raw_name.decode("utf-8")
        files[name] = sha256_bytes((game_root / name).read_bytes())
    packed = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=game_root, text=True,
        capture_output=True, check=True,
    ).stdout.strip()
    describe = subprocess.run(
        ["git", "describe", "--tags", "--exact-match", "HEAD"], cwd=game_root,
        text=True, capture_output=True, check=False,
    )
    clean = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--"], cwd=game_root,
        capture_output=True, check=False,
    ).returncode == 0
    return {"git_revision": revision,
            "git_describe_tag": describe.stdout.strip() if describe.returncode == 0 else None,
            "tracked_worktree_clean": clean,
            "tracked_file_sha256": files,
            "snapshot_sha256": sha256_bytes(packed)}


def verify_upstream_identity(snapshot: dict[str, Any]) -> None:
    if snapshot["git_revision"] != PINNED_COMMIT:
        raise ValueError(
            f"unsupported upstream revision {snapshot['git_revision']}; "
            f"expected pinned {PINNED_COMMIT}"
        )
    if snapshot["git_describe_tag"] != "1.22":
        raise ValueError(
            f"expected exact upstream tag 1.22, got {snapshot['git_describe_tag']!r}"
        )
    if not snapshot["tracked_worktree_clean"]:
        raise ValueError("upstream tracked source has local modifications")


def parse_commands(path: Path) -> tuple[list[str], bytes]:
    raw = path.read_bytes()
    text = raw.decode("utf-8")
    commands = [line.strip() for line in text.splitlines()
                if line.strip() and not line.lstrip().startswith("#")]
    if not commands:
        raise ValueError("command transcript is empty")
    if commands[0].casefold() not in {"n", "no", "y", "yes"}:
        raise ValueError("transcript must answer the game's startup instructions question first")
    if len(commands) < 2 or commands[-1].casefold() != "yes" or commands[-2].casefold() != "quit":
        commands.extend(["quit", "yes"])
    return commands, raw


def run_once(command: list[str], stdin_bytes: bytes, cwd: Path) -> tuple[dict[str, Any], bytes, bytes]:
    try:
        completed = subprocess.run(command, input=stdin_bytes, capture_output=True,
                                   cwd=cwd, check=False, timeout=60)
        return ({"exit_code": completed.returncode, "timed_out": False, "error": None},
                completed.stdout, completed.stderr)
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or b""
        stderr = exc.stderr or b""
        if isinstance(stdout, str):
            stdout = stdout.encode("utf-8", errors="replace")
        if isinstance(stderr, str):
            stderr = stderr.encode("utf-8", errors="replace")
        return ({"exit_code": None, "timed_out": True,
                 "error": f"TimeoutExpired after {exc.timeout} seconds"}, stdout, stderr)
    except OSError as exc:
        return ({"exit_code": None, "timed_out": False,
                 "error": f"{type(exc).__name__}: {exc}"}, b"", str(exc).encode("utf-8"))


def run_episode(binary: Path, commands: list[str]) -> tuple[dict[str, Any], bytes, bytes, bytes, bytes]:
    stdin_bytes = ("\n".join(commands) + "\n").encode("utf-8")
    command = [str(binary), "-o"]
    first, stdout, stderr = run_once(command, stdin_bytes, binary.parent)
    replay, replay_stdout, replay_stderr = run_once(command, stdin_bytes, binary.parent)
    return ({"argv": command, **first,
             "direct_replay_exit_code": replay["exit_code"],
             "direct_replay_timed_out": replay["timed_out"],
             "direct_replay_error": replay["error"],
             "stdout_matches_direct_replay": stdout == replay_stdout,
             "stderr_matches_direct_replay": stderr == replay_stderr,
             "stdin_sha256": sha256_bytes(stdin_bytes),
             "stdout_sha256": sha256_bytes(stdout),
             "stderr_sha256": sha256_bytes(stderr),
             "direct_replay_stdout_sha256": sha256_bytes(replay_stdout),
             "direct_replay_stderr_sha256": sha256_bytes(replay_stderr)},
            stdout, stderr, replay_stdout, replay_stderr)


def acceptance_checks(execution: dict[str, Any], tracked_source_unchanged: bool,
                      binary_unchanged: bool) -> dict[str, bool]:
    return {
        "episode_exit_zero": execution["exit_code"] == 0,
        "direct_replay_exit_zero": execution["direct_replay_exit_code"] == 0,
        "episode_not_timed_out": not execution["timed_out"],
        "direct_replay_not_timed_out": not execution["direct_replay_timed_out"],
        "stdout_matches": execution["stdout_matches_direct_replay"],
        "stderr_matches": execution["stderr_matches_direct_replay"],
        "tracked_source_unchanged": tracked_source_unchanged,
        "binary_unchanged": binary_unchanged,
    }


def allocate_run_dir(root: Path, run_id: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in run_id)[:64]
    for _ in range(8):
        path = root / f"{slug}-{timestamp}-{secrets.token_hex(3)}"
        try:
            path.mkdir()
            return path
        except FileExistsError:
            continue
    raise FileExistsError("could not allocate unique run directory")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--commands", required=True, type=Path,
                        help="UTF-8 transcript, one native game command per line")
    parser.add_argument("--id", required=True, help="short scenario identifier")
    parser.add_argument("--binary", type=Path, default=DEFAULT_GAME / "advent")
    parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME)
    parser.add_argument("--runs", type=Path, default=DEFAULT_RUNS)
    args = parser.parse_args()

    binary = args.binary.resolve()
    game_root = args.game_root.resolve()
    commands, commands_raw = parse_commands(args.commands.resolve())
    run_dir = allocate_run_dir(args.runs.resolve(), args.id)
    (run_dir / "input.txt").write_bytes(commands_raw)
    (run_dir / "execution_stdin.txt").write_text("\n".join(commands) + "\n", encoding="utf-8")

    before = None
    after = None
    result = None
    stdout = b""
    stderr = b""
    replay_stdout = b""
    replay_stderr = b""
    errors = []
    binary_sha_before, binary_hash_error = file_sha256(binary)
    if binary_hash_error:
        errors.append(f"binary hash before run: {binary_hash_error}")
    try:
        before = source_snapshot(game_root)
        verify_upstream_identity(before)
    except (OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
        errors.append(f"preflight: {type(exc).__name__}: {exc}")

    if not errors:
        result, stdout, stderr, replay_stdout, replay_stderr = run_episode(binary, commands)
        for key in ("error", "direct_replay_error"):
            if result[key]:
                errors.append(f"{key}: {result[key]}")
        try:
            after = source_snapshot(game_root)
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            errors.append(f"post-run source snapshot: {type(exc).__name__}: {exc}")
    binary_sha_after, binary_hash_error_after = file_sha256(binary)
    if binary_hash_error_after:
        errors.append(f"binary hash after run: {binary_hash_error_after}")
    (run_dir / "stdout.txt").write_bytes(stdout)
    (run_dir / "stderr.txt").write_bytes(stderr)
    (run_dir / "direct_replay_stdout.txt").write_bytes(replay_stdout)
    (run_dir / "direct_replay_stderr.txt").write_bytes(replay_stderr)
    (run_dir / "errors.txt").write_text("\n".join(errors) + ("\n" if errors else ""),
                                       encoding="utf-8")

    tracked_source_unchanged = (
        before is not None and after is not None and before == after
        and before["tracked_worktree_clean"] and after["tracked_worktree_clean"]
    )
    binary_unchanged = binary_sha_before is not None and binary_sha_before == binary_sha_after
    acceptance = acceptance_checks(result, tracked_source_unchanged, binary_unchanged) \
        if result is not None else {"execution_completed": False}
    document = {
        "schema": "open-adventure-native-run-v0",
        "scenario_id": args.id,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "game": {"name": "Open Adventure", "version": "1.22" if before and before.get("git_revision") == PINNED_COMMIT else None,
                 "pinned_commit": PINNED_COMMIT,
                 "binary_path": str(binary),
                 "binary_sha256_before": binary_sha_before,
                 "binary_sha256_after": binary_sha_after,
                 "license": "BSD-2-Clause", "source_before": before,
                 "source_after": after,
                 "tracked_source_unchanged": tracked_source_unchanged,
                 "binary_unchanged": binary_unchanged},
        "host": {"platform": __import__("platform").platform(),
                 "python": __import__("platform").python_version()},
        "execution": ({**result, "commands": commands,
                       "mode": "one full native episode via stdin; no per-turn hidden state access",
                       "stdout_is_player_visible_game_text": True}
                      if result is not None else None),
        "acceptance": {"passed": bool(acceptance) and all(acceptance.values()),
                       "checks": acceptance},
        "errors": errors,
        "evidence_files": {"input": "input.txt", "execution_stdin": "execution_stdin.txt",
                           "stdout": "stdout.txt", "stderr": "stderr.txt",
                           "direct_replay_stdout": "direct_replay_stdout.txt",
                           "direct_replay_stderr": "direct_replay_stderr.txt",
                           "errors": "errors.txt"},
    }
    (run_dir / "run.json").write_text(json.dumps(document, ensure_ascii=False,
                                                    indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"run_dir": str(run_dir),
                      "exit_code": result["exit_code"] if result else None,
                      "acceptance_passed": document["acceptance"]["passed"],
                      "tracked_source_unchanged": tracked_source_unchanged,
                      "errors": errors}, ensure_ascii=False))
    return 0 if document["acceptance"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
