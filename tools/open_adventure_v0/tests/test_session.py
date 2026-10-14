from __future__ import annotations

import base64
import json
import os
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import subprocess
from tools.open_adventure_v0.session import OpenAdventureSession
from tools.open_adventure_v0.session import StepResult, replay
from tools.open_adventure_v0.session import StepResult, replay
from tools.open_adventure_v0.smoke_policy import choose_recovery


FAKE_GAME = r'''import os, sys
def prompt(text):
    os.write(1, text.encode() + b"\r\n> ")
prompt("fake startup")
while True:
    line = sys.stdin.readline()
    if not line:
        break
    command = line.strip()
    if command == "quit":
        prompt("confirm quit")
    elif command == "yes":
        os.write(1, b"closed\r\n")
        break
    else:
        prompt("feedback:" + command)
'''

BLOCKING_GAME = r'''import os, sys
os.write(1, b"partial output")
sys.stdin.readline()
'''

FAILING_GAME = r'''import os, sys
os.write(1, b"initial\r\n> ")
line = sys.stdin.readline()
os.write(1, b"terminal error text")
sys.exit(2)
'''


class OnlineSessionTests(unittest.TestCase):
    def fake_game(self, code: str):
        real_popen = subprocess.Popen

        def spawn_fake(_argv, **kwargs):
            return real_popen([sys.executable, "-u", "-c", code], **kwargs)

        return patch.multiple(
            "tools.open_adventure_v0.session.runner",
            source_snapshot=lambda _root: {"fixture": "pinned-source-mock"},
            verify_upstream_identity=lambda _snapshot: None,
            file_sha256=lambda _path: ("fixture-binary-hash", None),
        ), patch("tools.open_adventure_v0.session.subprocess.Popen", side_effect=spawn_fake)

    def make_session(self, root: Path, *, timeout: float = 1.0):
        return OpenAdventureSession(game_root=root, runs_root=root / "runs", timeout=timeout)

    def test_native_boundaries_observe_logging_and_close(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source_patch, popen_patch = self.fake_game(FAKE_GAME)
            with source_patch, popen_patch:
                session = self.make_session(root)
                initial = session.reset({"purpose": "contract test"})
                self._check_interaction(session, initial)

    def test_live_prompt_close_reaps_isolated_child(self):
        with tempfile.TemporaryDirectory() as temp:
            source_patch, popen_patch = self.fake_game(FAKE_GAME)
            with source_patch, popen_patch:
                session = self.make_session(Path(temp))
                session.reset()
                process = session._process
                self.assertIsNotNone(process)
                self.assertEqual(os.getsid(process.pid), process.pid)
                status = session.close()
                self.assertTrue(status["terminated"])
                self.assertIsNotNone(process.poll())

    def _check_interaction(self, session, initial):
        self.assertTrue(initial.endswith("> "))
        self.assertEqual(session.observe(), initial)

        result = session.step("n", controller="test-policy", decision_source="startup")
        self.assertTrue(result.input_boundary_reached)
        self.assertIn("feedback:n", result.observation)
        self.assertEqual(result.sent_bytes, b"n\n")
        self.assertEqual(session.observe(), result.observation)

        quit_result = session.step("quit", controller="test-policy", decision_source="close")
        self.assertTrue(quit_result.input_boundary_reached)
        self.assertIn("confirm quit", quit_result.observation)
        yes_result = session.step("yes", controller="test-policy", decision_source="close")
        self.assertTrue(yes_result.terminated)
        self.assertEqual(yes_result.exit_code, 0)
        self.assertIsNone(yes_result.error)
        cached_final = session.observe()
        before_observe = session.log_path.read_text()
        self.assertEqual(session.observe(), cached_final)
        self.assertEqual(session.log_path.read_text(), before_observe)
        session.close()
        self.assertEqual(session.observe(), cached_final)

        log = [json.loads(line) for line in session.log_path.read_text().splitlines()]
        steps = [row for row in log if row["event"] == "step"]
        self.assertEqual([row["sequence"] for row in steps], [1, 2, 3])
        self.assertEqual(steps[0]["controller"], "test-policy")
        self.assertEqual(base64.b64decode(steps[0]["sent_bytes_b64"]), b"n\n")
        self.assertEqual(base64.b64decode(steps[0]["intended_bytes_b64"]), b"n\n")
        self.assertEqual(base64.b64decode(steps[0]["raw_output_b64"]), result.raw_output)
        self.assertIn("fake startup", steps[0]["before_observation"])

    def test_one_line_boundary_rejects_control_characters(self):
        with tempfile.TemporaryDirectory() as temp:
            source_patch, popen_patch = self.fake_game(FAKE_GAME)
            with source_patch, popen_patch:
                session = self.make_session(Path(temp))
                session.reset()
                for invalid in ("look\nquit", "look\r", "look\x00here", "look\x7f", "x" * 1024):
                    with self.subTest(invalid=repr(invalid)):
                        with self.assertRaises(ValueError):
                            session.step(invalid, controller="test", decision_source="invalid")
                result = session.step("look", controller="test", decision_source="valid")
                self.assertTrue(result.input_boundary_reached)
                session.close()

    def test_timeout_retains_partial_output_and_close_reaps_child(self):
        with tempfile.TemporaryDirectory() as temp:
            source_patch, popen_patch = self.fake_game(BLOCKING_GAME)
            with source_patch, popen_patch:
                session = self.make_session(Path(temp), timeout=0.1)
                with patch.object(session, "_read_to_prompt", side_effect=[
                    (b"fake startup\r\n> ", True, None, False),
                    (b"partial output", False, "timeout after 0.1s", True),
                ]):
                    initial = session.reset()
                    self.assertIn("fake startup", initial)
                    # The transport times out with partial bytes just as the child
                    # exits 0. That exit must not promote partial text to a cache.
                    with patch.object(session._process, "poll", side_effect=[None, 0]):
                        result = session.step("look", controller="test", decision_source="timeout")
                    self.assertTrue(result.timed_out)
                    self.assertTrue(result.terminated)
                    self.assertEqual(result.exit_code, 0)
                    self.assertEqual(result.raw_output, b"partial output")
                    self.assertEqual(session.observe(), initial)
                    with self.assertRaises(RuntimeError):
                        session.step("look", controller="test", decision_source="after-timeout")
                session.close()
                records = [json.loads(line) for line in session.log_path.read_text().splitlines()]
                step_row = next(row for row in records if row["event"] == "step")
                raw = base64.b64decode(step_row["raw_output_b64"])
                self.assertEqual(raw, b"partial output")
                self.assertTrue(step_row["timed_out"])
                self.assertIsNotNone(session._process.poll())

    def test_visible_text_feedback_selects_distinct_actions(self):
        rejected = "You are already carrying it!"
        unrelated = "The room is empty."
        self.assertEqual(choose_recovery(rejected), "drop lamp")
        self.assertEqual(choose_recovery(unrelated), "inventory")

    def test_nonzero_exit_keeps_final_partial_bytes_and_status(self):
        with tempfile.TemporaryDirectory() as temp:
            source_patch, popen_patch = self.fake_game(FAILING_GAME)
            with source_patch, popen_patch:
                session = self.make_session(Path(temp))
                session.reset()
                result = session.step("fail", controller="test", decision_source="exit")
                self.assertTrue(result.terminated)
                self.assertEqual(result.exit_code, 2)
                self.assertIn(b"terminal error text", result.raw_output)
                self.assertIn("status 2", result.error)
                session.close()

    def test_short_write_records_actual_prefix_and_breaks_session(self):
        with tempfile.TemporaryDirectory() as temp:
            source_patch, popen_patch = self.fake_game(FAKE_GAME)
            with source_patch, popen_patch:
                session = self.make_session(Path(temp))
                session.reset()
                with patch("tools.open_adventure_v0.session.os.write", return_value=1):
                    result = session.step("look", controller="test", decision_source="short-write")
                self.assertEqual(result.intended_bytes, b"look\n")
                self.assertEqual(result.sent_bytes, b"l")
                self.assertIn("short PTY write", result.error)
                with self.assertRaises(RuntimeError):
                    session.step("again", controller="test", decision_source="after-error")
                session.close()
                row = next(json.loads(line) for line in session.log_path.read_text().splitlines()
                           if '"event": "step"' in line)
                self.assertEqual(base64.b64decode(row["sent_bytes_b64"]), b"l")

    def test_replay_completion_rejects_timed_out_exit_and_empty_failed_reset(self):
        class FakeSession:
            episode_id = "mock-episode"
            run_dir = Path("mock-run")
            _raw_observation = b"\r\n> "
            _initial_input_boundary = True
            _initial_timed_out = False
            _initial_error = None

            def __init__(self, result=None, *, reset_failed=False):
                self.result = result
                self.reset_failed = reset_failed
                self.calls = []

            def reset(self):
                if self.reset_failed:
                    self._initial_input_boundary = False
                    self._initial_error = "timeout before startup prompt"
                    self._raw_observation = b"partial startup"
                    return ""
                return "startup prompt"

            def step(self, command, *, controller, decision_source):
                self.calls.append((command, controller, decision_source))
                return self.result

            def close(self):
                return None

        intended = b"yes\n"
        timed_out_exit = StepResult(
            "mock-episode", 1, "yes", intended, intended, "quit prompt",
            b"partial final text", "partial final text", False, True, 0, True, None,
        )
        fake = FakeSession(timed_out_exit)
        with patch("tools.open_adventure_v0.session.OpenAdventureSession",
                   return_value=fake):
            result = replay([{"command": "yes", "controller": "smoke-policy",
                              "decision_source": "selected after rejection"}])
            self.assertFalse(result["interactions_completed"])
            self.assertEqual(fake.calls[0][1], "replay")
            self.assertIn("original controller=smoke-policy", fake.calls[0][2])

        with patch("tools.open_adventure_v0.session.OpenAdventureSession",
                   return_value=FakeSession(reset_failed=True)):
            result = replay([])
            self.assertFalse(result["interactions_completed"])


if __name__ == "__main__":
    unittest.main()
