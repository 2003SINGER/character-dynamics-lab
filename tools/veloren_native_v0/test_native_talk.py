"""File-only integration tests for native_talk.py; never launch Veloren."""

import json
import pathlib
import select
import subprocess
import sys
import tempfile
import time
import unittest


SCRIPT = pathlib.Path(__file__).with_name("native_talk.py")


class NativeTalkCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="veloren-native-cli-")
        self.root = pathlib.Path(self.temp.name)
        self.requests = self.root / "requests.jsonl"
        self.events = self.root / "events.jsonl"

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args):
        return subprocess.run(
            [sys.executable, str(SCRIPT), *map(str, args)],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_rejects_invalid_ttl_and_self_target_without_appending(self):
        base = (
            "request", "--requests", self.requests,
            "--source", "unit-test", "--request-id", "invalid",
            "--npc-uid", "10", "--target-uid", "11",
        )
        for ttl in ("0", "60.1", "nan"):
            with self.subTest(ttl=ttl):
                result = self.run_cli(*base, "--ttl", ttl)
                self.assertEqual(result.returncode, 2)
                self.assertIn("TTL must", result.stderr)
        self.assertFalse(self.requests.exists())

        result = self.run_cli(
            "request", "--requests", self.requests,
            "--source", "unit-test", "--request-id", "self-target",
            "--npc-uid", "10", "--target-uid", "10", "--ttl", "5",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("must differ", result.stderr)
        self.assertFalse(self.requests.exists())

    def test_appends_typed_request_and_cancel_lines(self):
        request = self.run_cli(
            "request", "--requests", self.requests,
            "--source", "unit-test", "--request-id", "r-1",
            "--npc-uid", "10", "--target-uid", "20", "--ttl", "5",
        )
        self.assertEqual(request.returncode, 0, request.stderr)
        self.assertIn("not server-accepted", request.stdout)

        cancel = self.run_cli(
            "cancel", "--requests", self.requests, "--request-id", "r-1",
        )
        self.assertEqual(cancel.returncode, 0, cancel.stderr)

        records = [json.loads(line) for line in self.requests.read_text().splitlines()]
        self.assertEqual(records[0], {
            "request_id": "r-1", "npc_uid": 10, "source": "unit-test",
            "ttl": 5.0, "kind": "TalkToNpc", "target_uid": 20,
        })
        self.assertEqual(records[1], {"cancel_request_id": "r-1"})

    def test_events_filters_by_request_id(self):
        self.events.write_text("\n".join((
            json.dumps({"event": "request_accepted", "request_id": "other"}),
            json.dumps({"event": "native_speech_emitted", "request_id": "r-1"}),
        )) + "\n")
        result = self.run_cli(
            "events", "--events", self.events, "--request-id", "r-1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "event": "native_speech_emitted", "request_id": "r-1",
        })

    def test_follow_waits_for_newline_when_row_is_appended_in_parts(self):
        self.events.write_text("")
        proc = subprocess.Popen(
            [sys.executable, str(SCRIPT), "events", "--events", str(self.events),
             "--request-id", "r-2", "--follow"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
        try:
            time.sleep(0.3)
            with self.events.open("a", encoding="utf-8") as stream:
                stream.write('{"event":"native_speech_')
                stream.flush()
            ready, _, _ = select.select([proc.stdout], [], [], 0.4)
            self.assertFalse(ready, "a partial JSONL row must not be emitted")

            with self.events.open("a", encoding="utf-8") as stream:
                stream.write('emitted","request_id":"r-2"}\n')
                stream.flush()
            ready, _, _ = select.select([proc.stdout], [], [], 3.0)
            self.assertTrue(ready, "completed JSONL row was not emitted")
            self.assertEqual(json.loads(proc.stdout.readline()), {
                "event": "native_speech_emitted", "request_id": "r-2",
            })
        finally:
            proc.terminate()
            proc.wait(timeout=3)
            proc.stdout.close()
            proc.stderr.close()

    def test_non_follow_labels_unterminated_tail_incomplete(self):
        self.events.write_text('{"request_id":"unfinished"')
        result = self.run_cli("events", "--events", self.events)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {
            "event": "incomplete_line", "raw": '{"request_id":"unfinished"',
        })


if __name__ == "__main__":
    unittest.main(verbosity=2)
