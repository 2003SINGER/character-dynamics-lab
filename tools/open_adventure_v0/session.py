#!/usr/bin/env python3
"""Small PTY session adapter for the unmodified Open Adventure 1.22 game."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import base64
import errno
import hashlib
import json
import os
from pathlib import Path
import pty
import secrets
import select
import subprocess
import termios
import time
from typing import Any, Sequence
import uuid

from tools.open_adventure_v0 import runner


INPUT_BOUNDARY = b"\r\n> "
ADAPTER_VERSION = "open-adventure-online-p1-v0"


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _visible(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def _json_line(path: Path, value: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def _allocate_dir(root: Path, episode_id: str) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    slug = "".join(c if c.isalnum() or c in "-_." else "-" for c in episode_id)[:48]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for _ in range(8):
        path = root / f"{slug}-{stamp}-{secrets.token_hex(3)}"
        try:
            path.mkdir()
            return path
        except FileExistsError:
            continue
    raise FileExistsError("could not allocate unique episode directory")


@dataclass(frozen=True)
class StepResult:
    episode_id: str
    sequence: int
    command: str
    intended_bytes: bytes
    sent_bytes: bytes
    before_observation: str
    raw_output: bytes
    observation: str
    input_boundary_reached: bool
    terminated: bool
    exit_code: int | None
    timed_out: bool
    error: str | None


class OpenAdventureSession:
    """One native game process; prompt completion is not interpreted as a world tick."""

    def __init__(self, *, binary: Path = runner.DEFAULT_GAME / "advent",
                 game_root: Path = runner.DEFAULT_GAME,
                 runs_root: Path = runner.PROJECT_ROOT / "02_实验/OpenAdventure_Online_P1_v0/runs",
                 timeout: float = 20.0):
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self.binary = Path(binary).resolve()
        self.game_root = Path(game_root).resolve()
        self.runs_root = Path(runs_root)
        self.timeout = timeout
        self.command = [str(self.binary)]
        self.episode_id = uuid.uuid4().hex
        self.run_dir: Path | None = None
        self.log_path: Path | None = None
        self._process: subprocess.Popen[bytes] | None = None
        self._master: int | None = None
        self._observation = ""
        self._raw_observation = b""
        self._sequence = 0
        self._started = False
        self._closed = False
        self._broken = False
        self._source_before: dict[str, Any] | None = None
        self._binary_sha_before: str | None = None
        self._initial_input_boundary = False
        self._initial_timed_out = False
        self._initial_error: str | None = None

    def reset(self, config: dict[str, Any] | None = None) -> str:
        if self._started:
            raise RuntimeError("session can only be reset once; create a new session")
        config = dict(config or {})
        self.episode_id = str(config.get("episode_id") or self.episode_id)
        self.run_dir = _allocate_dir(self.runs_root, self.episode_id)
        self.log_path = self.run_dir / "events.jsonl"
        try:
            base_revision = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=runner.PROJECT_ROOT,
                capture_output=True, text=True, check=True,
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            base_revision = None
        adapter_sha256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        self._write_manifest({"event": "reset_requested", "episode_id": self.episode_id,
                              "created_at_utc": datetime.now(timezone.utc).isoformat(),
                              "adapter_version": ADAPTER_VERSION,
                              "adapter_source_sha256": adapter_sha256,
                              "repository_base_revision": base_revision,
                              "config": config,
                              "game": {"binary": str(self.binary)},
                              "transport": {"argv": self.command, "term": "dumb",
                                             "native_boundary_bytes_b64": _b64(INPUT_BOUNDARY),
                                             "boundary_meaning": "game requested input"}})
        try:
            self._source_before = runner.source_snapshot(self.game_root)
            runner.verify_upstream_identity(self._source_before)
            digest, error = runner.file_sha256(self.binary)
            if error:
                raise OSError(error)
            self._binary_sha_before = digest
            master, slave = pty.openpty()
            # Keep libedit on the ordinary line editor path without a terminal UI mode.
            attrs = termios.tcgetattr(slave)
            attrs[3] &= ~termios.ECHO
            termios.tcsetattr(slave, termios.TCSANOW, attrs)
            env = os.environ.copy()
            env["TERM"] = "dumb"
            self._process = subprocess.Popen(
                self.command, cwd=self.game_root, stdin=slave, stdout=slave,
                stderr=slave, env=env, close_fds=True, bufsize=0,
                start_new_session=True,
            )
            os.close(slave)
            slave = None
            self._master = master
            os.set_blocking(master, False)
            self._started = True
        except Exception as exc:
            if self._process and self._process.poll() is None:
                self._process.terminate()
                try:
                    self._process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self._process.kill()
                    self._process.wait(timeout=2)
            if "master" in locals():
                os.close(master)
            if "slave" in locals() and slave is not None:
                os.close(slave)
            self._broken = True
            self._write_manifest({"event": "reset_error",
                                  "error": f"{type(exc).__name__}: {exc}"})
            raise
        self._write_manifest({"event": "reset", "episode_id": self.episode_id,
                              "game": {"binary_sha256_before": self._binary_sha_before,
                                       "source_before": self._source_before}})
        raw, boundary, error, timed_out = self._read_to_prompt()
        self._initial_input_boundary = boundary
        self._initial_timed_out = timed_out
        self._initial_error = error
        initial_complete = boundary or (self._process.poll() is not None and not timed_out)
        if initial_complete:
            self._raw_observation = raw
            self._observation = _visible(raw)
        _json_line(self.log_path, {"event": "initial_observation", "raw_b64": _b64(raw),
                                   "observation": self._observation,
                                   "input_boundary_reached": boundary,
                                   "terminated": self._process.poll() is not None,
                                   "exit_code": self._process.poll(),
                                   "complete": initial_complete,
                                   "timed_out": timed_out, "error": error})
        if not boundary:
            self._broken = True
        return self._observation

    def observe(self) -> str:
        if not self._started:
            raise RuntimeError("session has no recorded observation yet")
        return self._observation

    def step(self, command: str, *, controller: str, decision_source: str) -> StepResult:
        self._require_live()
        if not isinstance(command, str) or not command.strip():
            raise ValueError("command must be a non-empty string")
        if any(ord(char) < 32 or ord(char) == 127 for char in command):
            raise ValueError("command must contain one line and no control characters")
        intended = command.encode("utf-8") + b"\n"
        if len(intended) > 1024:
            raise ValueError("command exceeds the 1024-byte native input limit")
        before = self._observation
        try:
            assert self._master is not None
            written = os.write(self._master, intended)
            sent = intended[:written]
            if written != len(intended):
                raw, boundary, timed_out = b"", False, False
                error = f"short PTY write: {written}/{len(intended)} bytes"
            else:
                raw, boundary, error, timed_out = self._read_to_prompt()
        except OSError as exc:
            sent = b""
            raw, boundary, timed_out = b"", False, False
            error = f"{type(exc).__name__}: {exc}"
        self._sequence += 1
        proc = self._process
        code = proc.poll() if proc else None
        if proc and code is None and not boundary and not timed_out:
            try:
                code = proc.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                pass
        terminated = code is not None
        result = StepResult(self.episode_id, self._sequence, command, intended, sent, before,
                            raw, _visible(raw), boundary, terminated, code,
                            timed_out, error)
        assert self.log_path is not None
        _json_line(self.log_path, {
            "event": "step", "episode_id": self.episode_id,
            "sequence": self._sequence, "command": command,
            "controller": controller, "decision_source": decision_source,
            "before_observation": before,
            "intended_bytes_b64": _b64(intended), "sent_bytes_b64": _b64(sent),
            "raw_output_b64": _b64(raw), "observation": result.observation,
            "input_boundary_reached": boundary, "terminated": terminated,
            "exit_code": code, "timed_out": timed_out, "error": error,
        })
        if boundary or (terminated and not timed_out):
            self._raw_observation = raw
            self._observation = result.observation
        if not boundary:
            self._broken = True
        return result

    def close(self) -> dict[str, Any]:
        if self._closed:
            return {"terminated": True, "exit_code": self._process.poll() if self._process else None}
        proc = self._process
        error = None
        if proc and proc.poll() is None:
            proc.terminate()
            try:
                code = proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                code = proc.wait(timeout=2)
                error = "process required kill after terminate timeout"
        else:
            code = proc.poll() if proc else None
        if self._master is not None:
            os.close(self._master)
            self._master = None
        self._closed = True
        status = {"event": "close", "terminated": bool(proc and proc.poll() is not None),
                  "exit_code": code, "error": error,
                  "closed_at_utc": datetime.now(timezone.utc).isoformat()}
        if self.log_path:
            _json_line(self.log_path, status)
            after = self._source_after_snapshot()
            binary_after = self._binary_sha_after()
            self._write_manifest({"event": "close_source_check",
                                  "source_after": after,
                                  "tracked_source_unchanged": bool(
                                      after and after.get("unchanged_from_reset")),
                                  "binary_sha256_after": binary_after,
                                  "binary_unchanged": (
                                      self._binary_sha_before is not None
                                      and binary_after == self._binary_sha_before)})
        return status

    def _read_to_prompt(self) -> tuple[bytes, bool, str | None, bool]:
        assert self._master is not None and self._process is not None
        data = bytearray()
        deadline = time.monotonic() + self.timeout
        while True:
            if data.endswith(INPUT_BOUNDARY):
                return bytes(data), True, None, False
            if self._process.poll() is not None:
                try:
                    chunk = os.read(self._master, 4096)
                except OSError as exc:
                    if exc.errno == errno.EIO:
                        code = self._process.poll()
                        error = None if code == 0 else f"process exited with status {code} before native prompt"
                        return bytes(data), False, error, False
                    if exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                        code = self._process.poll()
                        error = None if code == 0 else f"process exited with status {code} before native prompt"
                        return bytes(data), False, error, False
                    return bytes(data), False, f"{type(exc).__name__}: {exc}", False
                if chunk:
                    data.extend(chunk)
                    continue
                code = self._process.poll()
                error = None if code == 0 else f"process exited with status {code} before native prompt"
                return bytes(data), False, error, False
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return bytes(data), False, f"timeout after {self.timeout:g}s", True
            ready, _, _ = select.select([self._master], [], [], remaining)
            if not ready:
                continue
            try:
                chunk = os.read(self._master, 4096)
            except OSError as exc:
                if exc.errno == errno.EIO:
                    try:
                        code = self._process.wait(timeout=0.2)
                    except subprocess.TimeoutExpired:
                        code = None
                    error = (None if code == 0 else
                             f"PTY closed before native prompt; process status {code}")
                    return bytes(data), False, error, False
                return bytes(data), False, f"{type(exc).__name__}: {exc}", False
            if not chunk:
                try:
                    code = self._process.wait(timeout=0.2)
                except subprocess.TimeoutExpired:
                    code = None
                error = (None if code == 0 else
                         f"PTY reached EOF before native prompt; process status {code}")
                return bytes(data), False, error, False
            data.extend(chunk)

    def _require_live(self) -> None:
        if not self._started or self._closed or self._broken or not self._process:
            raise RuntimeError("session is not at a usable native input boundary")
        if self._process.poll() is not None:
            raise RuntimeError("game process has terminated")

    def _write_manifest(self, row: dict[str, Any]) -> None:
        assert self.log_path is not None
        _json_line(self.log_path, row)

    def _source_after_snapshot(self) -> dict[str, Any] | None:
        try:
            after = runner.source_snapshot(self.game_root)
            after["unchanged_from_reset"] = after == self._source_before
            return after
        except (OSError, subprocess.SubprocessError, ValueError) as exc:
            return {"error": f"{type(exc).__name__}: {exc}"}

    def _binary_sha_after(self) -> str | None:
        digest, _ = runner.file_sha256(self.binary)
        return digest


def replay(commands: Sequence[dict[str, str] | str], *,
           binary: Path = runner.DEFAULT_GAME / "advent",
           game_root: Path = runner.DEFAULT_GAME,
           runs_root: Path = runner.PROJECT_ROOT / "02_实验/OpenAdventure_Online_P1_v0/runs",
           timeout: float = 20.0) -> dict[str, Any]:
    """Replay explicit native inputs in a fresh process and compare per-step output bytes."""
    session = OpenAdventureSession(binary=binary, game_root=game_root,
                                   runs_root=runs_root, timeout=timeout)
    initial = session.reset()
    initial_raw = session._raw_observation
    results: list[StepResult] = []
    try:
        for item in commands:
            if isinstance(item, str):
                command, controller, source = item, "replay", "recorded command sequence"
            else:
                command = item["command"]
                controller = "replay"
                source = ("recorded input; original controller="
                          f"{item.get('controller', 'unknown')}; original decision source="
                          f"{item.get('decision_source', 'unknown')}")
            result = session.step(command, controller=controller, decision_source=source)
            results.append(result)
            if not result.input_boundary_reached:
                break
        initial_ok = (session._initial_input_boundary
                      and not session._initial_timed_out
                      and session._initial_error is None)
        rows_ok = all(not row.timed_out and row.error is None
                      and row.sent_bytes == row.intended_bytes
                      for row in results)
        final_clean_exit = bool(results and results[-1].terminated
                                and results[-1].exit_code == 0
                                and not results[-1].timed_out
                                and results[-1].error is None
                                and results[-1].sent_bytes == results[-1].intended_bytes)
        all_prior_boundaries = all(row.input_boundary_reached for row in results[:-1])
        if final_clean_exit:
            completed = (initial_ok and len(results) == len(commands) and rows_ok
                         and all_prior_boundaries)
        else:
            completed = (initial_ok and len(results) == len(commands) and rows_ok
                         and all(row.input_boundary_reached for row in results))
        return {"episode_id": session.episode_id, "run_dir": str(session.run_dir),
                "initial_observation": initial,
                "initial_observation_raw_b64": _b64(initial_raw),
                "step_outputs_b64": [_b64(row.raw_output) for row in results],
                "interactions_completed": completed,
                "last_process_termination": (results[-1].terminated if results else False),
                "exit_codes": [row.exit_code for row in results]}
    finally:
        session.close()

