import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import runner  # noqa: E402


class NativeOutputTests(unittest.TestCase):
    def test_success_plan_and_numeric_fields(self):
        parsed = runner.parse_native_output(
            "Result: Success!\n"
            "  utility achieved: 1\n"
            "  nodes visited:    1,234\n"
            "  nodes generated:  2,345\n"
            "  time:             0.5s\n"
            "move(A, Home, Inn)\n"
            "| explanation only\n"
            "goal(at(A) == Inn)\n"
        )
        self.assertEqual(parsed["status"], "SUCCESS")
        self.assertEqual(parsed["nodes_visited"], 1234)
        self.assertEqual(parsed["nodes_generated"], 2345)
        self.assertEqual(parsed["elapsed_native_ms"], 500)
        self.assertEqual(parsed["plan_actions"], ["move(A, Home, Inn)"])

    def test_budget_error_and_no_solution_are_distinct(self):
        self.assertEqual(
            runner.parse_native_output("Result: Search limit reached")["status"],
            "BUDGET_LIMIT",
        )
        self.assertEqual(
            runner.parse_native_output("Result: No solution exists")["status"],
            "NATIVE_NO_SOLUTION",
        )
        self.assertEqual(
            runner.parse_native_output("", "NoClassDefFoundError: missing")["status"],
            "NATIVE_STARTUP_ERROR",
        )
        self.assertEqual(
            runner.parse_native_output("Error: null")["status"], "NATIVE_ERROR"
        )

    def test_unrecognized_composite_duration_is_not_coerced(self):
        parsed = runner.parse_native_output("Result: Search limit reached\n  time: 1m 4s")
        self.assertEqual(parsed["elapsed_native_text"], "1m 4s")
        self.assertIsNone(parsed["elapsed_native_ms"])
        self.assertIsNotNone(parsed["elapsed_native_parse_warning"])


class RunnerFilesystemTests(unittest.TestCase):
    def test_slug_rejects_path_traversal(self):
        completed = subprocess.run(
            [sys.executable, str(HERE / "runner.py"), "--problem", "missing.txt", "--run-id", "../escape"],
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("run-id must be", completed.stderr)

    def test_output_is_recorded_and_existing_run_is_not_overwritten(self):
        evidence_root = runner.EVIDENCE_ROOT
        evidence_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="runner-test-", dir=evidence_root) as temp:
            root = Path(temp)
            problem = root / "problem.txt"
            problem.write_text("sample\n")
            fake_java = root / "fake-java"
            fake_java.write_text(
                "#!/usr/bin/env python3\n"
                "print('Result: Success!')\n"
                "print('  utility achieved: 1')\n"
                "print('  nodes visited: 1')\n"
                "print('  nodes generated: 1')\n"
                "print('  time: 1ms')\n"
                "print('meet(A, Inn)')\n"
            )
            fake_java.chmod(0o755)
            classpath = root / "classes"
            classpath.mkdir()
            output = root / "evidence"
            output.mkdir()
            command = [
                sys.executable,
                str(HERE / "runner.py"),
                "--problem",
                str(problem),
                "--run-id",
                "unit-run",
                "--output-root",
                str(output),
                "--java",
                str(fake_java),
                "--classpath",
                str(classpath),
            ]
            first = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            run_dir = output / "unit-run"
            self.assertTrue((run_dir / "stdout.log").is_file())
            self.assertTrue((run_dir / "stderr.log").is_file())
            self.assertTrue((run_dir / "config.json").is_file())
            record = json.loads((run_dir / "result.json").read_text())
            self.assertEqual(record["status"], "SUCCESS")
            self.assertEqual(record["plan_actions"], ["meet(A, Inn)"])
            config = json.loads((run_dir / "config.json").read_text())
            self.assertIn("-Xss1m", config["command"])
            second = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(second.returncode, 2)
            self.assertIn("refusing to overwrite", second.stderr)


if __name__ == "__main__":
    unittest.main()
