from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import contextlib
import io
import json
import sys

import subprocess

from tools.open_adventure_v0.runner import (
    PINNED_COMMIT,
    acceptance_checks,
    parse_commands,
    run_episode,
    verify_upstream_identity,
)


class RunnerTests(unittest.TestCase):
    def test_transcript_requires_native_start_answer(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "commands.txt"
            path.write_text("# fixed seed\nno\nseed 123\nquit\nyes\n", encoding="utf-8")
            commands, _ = parse_commands(path)
            self.assertEqual(commands, ["no", "seed 123", "quit", "yes"])

    def test_transcript_gets_native_quit_exchange_appended(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "commands.txt"
            path.write_text("n\nseed 123\nlook\n", encoding="utf-8")
            commands, _ = parse_commands(path)
            self.assertEqual(commands[-2:], ["quit", "yes"])

    def test_wrapper_capture_matches_direct_replay(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / "fake-adventure"
            binary.write_text("#!/bin/sh\ncat\n", encoding="utf-8")
            binary.chmod(0o755)
            result, stdout, stderr, replay_stdout, replay_stderr = run_episode(
                binary, ["no", "quit", "yes"]
            )
            self.assertEqual(result["exit_code"], 0)
            self.assertTrue(result["stdout_matches_direct_replay"])
            self.assertEqual(stdout, b"no\nquit\nyes\n")
            self.assertEqual(stderr, b"")
            self.assertEqual(replay_stdout, stdout)
            self.assertEqual(replay_stderr, stderr)

    def test_acceptance_rejects_any_replay_or_integrity_mismatch(self) -> None:
        baseline = {
            "exit_code": 0, "direct_replay_exit_code": 0,
            "timed_out": False, "direct_replay_timed_out": False,
            "stdout_matches_direct_replay": True, "stderr_matches_direct_replay": True,
        }
        self.assertTrue(all(acceptance_checks(baseline, True, True).values()))
        for key, value in (
            ("exit_code", 1), ("direct_replay_exit_code", 2),
            ("timed_out", True), ("direct_replay_timed_out", True),
            ("stdout_matches_direct_replay", False),
            ("stderr_matches_direct_replay", False),
        ):
            with self.subTest(failed_check=key):
                execution = {**baseline, key: value}
                self.assertFalse(all(acceptance_checks(execution, True, True).values()))
        self.assertFalse(all(acceptance_checks(baseline, False, True).values()))
        self.assertFalse(all(acceptance_checks(baseline, True, False).values()))

    def test_timeout_preserves_partial_stdout_and_stderr(self) -> None:
        timeout = subprocess.TimeoutExpired(["game", "-o"], 60,
                                            output=b"partial out", stderr=b"partial err")
        completed = subprocess.CompletedProcess(["game", "-o"], 0,
                                                stdout=b"full out", stderr=b"full err")
        with patch("tools.open_adventure_v0.runner.subprocess.run",
                   side_effect=[timeout, completed]):
            result, stdout, stderr, replay_stdout, replay_stderr = run_episode(
                Path("/tmp/game"), ["no", "quit", "yes"]
            )
        self.assertTrue(result["timed_out"])
        self.assertEqual(result["exit_code"], None)
        self.assertEqual(stdout, b"partial out")
        self.assertEqual(stderr, b"partial err")
        self.assertEqual(result["direct_replay_exit_code"], 0)
        self.assertEqual(replay_stdout, b"full out")
        self.assertEqual(replay_stderr, b"full err")

    def test_only_exact_tagged_commit_is_accepted(self) -> None:
        verify_upstream_identity({"git_revision": PINNED_COMMIT,
                                  "git_describe_tag": "1.22",
                                  "tracked_worktree_clean": True})
        with self.assertRaisesRegex(ValueError, "unsupported upstream revision"):
            verify_upstream_identity({"git_revision": "0" * 40,
                                      "git_describe_tag": "1.22",
                                      "tracked_worktree_clean": True})
        with self.assertRaisesRegex(ValueError, "expected exact upstream tag"):
            verify_upstream_identity({"git_revision": PINNED_COMMIT,
                                      "git_describe_tag": "other",
                                      "tracked_worktree_clean": True})
        with self.assertRaisesRegex(ValueError, "local modifications"):
            verify_upstream_identity({"git_revision": PINNED_COMMIT,
                                      "git_describe_tag": "1.22",
                                      "tracked_worktree_clean": False})

    def test_binary_hash_missing_is_reportable(self) -> None:
        from tools.open_adventure_v0.runner import file_sha256

        digest, error = file_sha256(Path("/definitely/not/an/open-adventure-binary"))
        self.assertIsNone(digest)
        self.assertIn("FileNotFoundError", error)

    def test_main_persists_failed_episode_evidence_before_returning_failure(self) -> None:
        from tools.open_adventure_v0 import runner

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            transcript = root / "commands.txt"
            transcript.write_text("no\nseed 123\n", encoding="utf-8")
            runs = root / "runs"
            game_root = root / "no-upstream-checkout"
            binary = root / "no-game-binary"

            def failed_episode(binary: Path, commands: list[str]):
                allocated = list(runs.iterdir())
                self.assertEqual(len(allocated), 1)
                self.assertEqual((allocated[0] / "input.txt").read_text(),
                                 "no\nseed 123\n")
                result = {
                    "argv": [str(binary), "-o"], "exit_code": None,
                    "timed_out": True, "error": "TimeoutExpired after 60 seconds",
                    "direct_replay_exit_code": 1, "direct_replay_timed_out": False,
                    "direct_replay_error": None,
                    "stdout_matches_direct_replay": False,
                    "stderr_matches_direct_replay": False,
                    "stdin_sha256": "input-hash", "stdout_sha256": "partial-hash",
                    "stderr_sha256": "stderr-hash", "direct_replay_stdout_sha256": "other",
                    "direct_replay_stderr_sha256": "other-stderr",
                }
                return (result, b"partial native stdout", b"partial native stderr",
                        b"direct replay stdout", b"direct replay stderr")

            pinned_snapshot = {"git_revision": PINNED_COMMIT,
                               "git_describe_tag": "1.22",
                               "tracked_worktree_clean": True,
                               "tracked_file_sha256": {}, "snapshot_sha256": "source-hash"}
            argv = ["runner.py", "--commands", str(transcript), "--id", "timeout-test",
                    "--game-root", str(game_root), "--binary", str(binary),
                    "--runs", str(runs)]
            output = io.StringIO()
            with patch.object(sys, "argv", argv), patch.object(runner, "run_episode",
                                                                 side_effect=failed_episode), \
                    patch.object(runner, "source_snapshot", return_value=pinned_snapshot), \
                    patch.object(runner, "file_sha256", return_value=("binary-hash", None)), \
                    contextlib.redirect_stdout(output):
                self.assertEqual(runner.main(), 1)

            run_dir = next(runs.iterdir())
            self.assertEqual((run_dir / "stdout.txt").read_bytes(), b"partial native stdout")
            self.assertEqual((run_dir / "stderr.txt").read_bytes(), b"partial native stderr")
            self.assertEqual((run_dir / "direct_replay_stdout.txt").read_bytes(),
                             b"direct replay stdout")
            self.assertEqual((run_dir / "direct_replay_stderr.txt").read_bytes(),
                             b"direct replay stderr")
            self.assertIn("TimeoutExpired", (run_dir / "errors.txt").read_text())
            record = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
            self.assertFalse(record["acceptance"]["passed"])
            self.assertFalse(record["acceptance"]["checks"]["direct_replay_exit_zero"])


if __name__ == "__main__":
    unittest.main()
