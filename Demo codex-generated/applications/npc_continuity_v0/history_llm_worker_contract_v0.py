"""Pure protocol/journal contracts; mocked completions are never inference evidence."""

import hashlib
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

WORKER = pathlib.Path(__file__).with_name("history_llm_worker_v0.py")
SPEC = importlib.util.spec_from_file_location("history_llm_worker_v0", WORKER)
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


class Response:
    status = 200

    def __init__(self, payload):
        self.payload = json.dumps(payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self, _limit):
        return self.payload


class Opener:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def open(self, _call, timeout):
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class WorkerContract(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="npc-history-llm-contract-")
        self.run_dir = pathlib.Path(self.temp.name)
        self.wrapper = {"policy_request": {"clock_total_minutes": 540,
                                           "actor_history": {"ledger_window": "runtime_pruned_to_48h"}},
                        "candidate_ids": ["c0", "c1"]}

    def tearDown(self):
        self.temp.cleanup()

    def invoke(self, payload=None, error=None):
        opener = Opener(error if error is not None else Response(payload))
        factory = mock.Mock(return_value=opener)
        result = worker.process_request(self.wrapper, self.run_dir, "test-model", 1000,
                                        opener_factory=factory)
        rows = [json.loads(line) for line in (self.run_dir / "history_llm_calls.jsonl").read_text().splitlines()]
        return result, rows[-1], opener, factory

    @staticmethod
    def completion(content, finish="stop", usage=None):
        return {"choices": [{"message": {"content": content}, "finish_reason": finish}],
                "usage": usage or {"prompt_tokens": 123, "completion_tokens": 7}}

    def test_valid_choice_schema_proxy_hash_and_usage(self):
        result, row, opener, factory = self.invoke(self.completion('{"candidate_id":"c1"}'))
        self.assertEqual(result[0], 0)
        fields = result[1].split("\t")
        self.assertEqual(fields[0:2], ["ok", "c1"])
        canonical = json.dumps(row["request"], sort_keys=True, ensure_ascii=False,
                               separators=(",", ":")).encode()
        self.assertEqual(fields[2], hashlib.sha256(canonical).hexdigest())
        self.assertEqual(fields[5:7], ["123", "7"])
        self.assertEqual(row["request_sha256"], fields[2])
        self.assertEqual(row["protocol"], "npc-history-llm-call-v1")
        self.assertEqual(row["prompt_protocol"], "npc-history-llm-prompt-v1")
        self.assertEqual(row["usage"], {"prompt_tokens": 123, "completion_tokens": 7})
        self.assertEqual(opener.calls, 1)
        handlers = factory.call_args.args
        self.assertIsInstance(handlers[0], worker.urllib.request.ProxyHandler)
        self.assertEqual(handlers[0].proxies, {})
        self.assertIsInstance(handlers[1], worker.NoRedirect)
        response_format = row["request"]["response_format"]
        self.assertEqual(set(response_format), {"type", "json_schema"})
        self.assertEqual(response_format["type"], "json_schema")
        self.assertEqual(response_format["json_schema"]["name"], "npc_action_choice")
        self.assertTrue(response_format["json_schema"]["strict"])
        self.assertEqual(response_format["json_schema"]["schema"]["properties"]["candidate_id"]["enum"], ["c0", "c1"])
        self.assertNotIn("schema", response_format,
                         "regression: expected response_format.json_schema.schema")
        system_prompt = row["request"]["messages"][0]["content"]
        self.assertIn("npc-history-llm-prompt-v1", system_prompt)
        self.assertIn('{"candidate_id":"<one supplied candidate id>"}', system_prompt)
        self.assertNotIn("TurnOffAlarm", system_prompt)

    def assert_bad_response(self, payload, stage="response_validation"):
        result, row, opener, _ = self.invoke(payload)
        self.assertEqual(result[0], 1)
        self.assertTrue(result[1].startswith("error\t" + stage + "\t"))
        self.assertEqual(row["stage"], stage)
        self.assertEqual(opener.calls, 1, "worker must not retry malformed model responses")
        return row

    def test_rejects_truncated_response(self):
        self.assert_bad_response(self.completion('{"candidate_id":"c0"}', finish="length"))

    def test_rejects_unknown_candidate_id(self):
        self.assert_bad_response(self.completion('{"candidate_id":"c9"}'))

    def test_rejects_extra_fields_and_invalid_json(self):
        self.assert_bad_response(self.completion('{"candidate_id":"c0","reason":"x"}'))
        self.assert_bad_response(self.completion("not-json"))

    def test_http_context_error_is_logged_without_retry(self):
        error = worker.urllib.error.HTTPError(worker.DEFAULT_ENDPOINT, 400, "context full", {}, None)
        error.read = lambda _limit: b'{"error":"context length exceeded"}'
        result, row, opener, _ = self.invoke(error=error)
        self.assertEqual(result[0], 1)
        self.assertIn("error\thttp\tHttpError", result[1])
        self.assertEqual(row["stage"], "http")
        self.assertEqual(row["response_raw"], '{"error":"context length exceeded"}')
        self.assertEqual(opener.calls, 1)

    def test_timeout_is_logged_without_retry(self):
        result, row, opener, _ = self.invoke(error=TimeoutError("request timed out"))
        self.assertEqual(result[0], 1)
        self.assertIn("error\ttransport\tTimeoutError", result[1])
        self.assertEqual(row["stage"], "transport")
        self.assertEqual(opener.calls, 1)

    def test_external_endpoint_and_redirect_are_not_followed(self):
        result = worker.process_request(self.wrapper, self.run_dir, "m", 1000,
            endpoint="https://example.com/v1/chat/completions")
        self.assertEqual(result[0], 1)
        rows = [json.loads(line) for line in (self.run_dir / "history_llm_calls.jsonl").read_text().splitlines()]
        self.assertEqual(rows[0]["error_type"], "UnsafeEndpoint")
        redirect = worker.urllib.error.HTTPError(worker.DEFAULT_ENDPOINT, 302, "redirect", {}, None)
        redirect.read = lambda _limit: b""
        result, row, opener, factory = self.invoke(error=redirect)
        self.assertEqual(result[0], 1)
        self.assertEqual(row["stage"], "http")
        self.assertEqual(opener.calls, 1)
        self.assertIsInstance(factory.call_args.args[1], worker.NoRedirect)

    def test_real_worker_connection_failure_without_model_server(self):
        run_dir = pathlib.Path(self.temp.name) / "worker-run"
        run_dir.mkdir()
        proc = subprocess.run([sys.executable, str(WORKER), "--run-directory", str(run_dir),
            "--model", "test-only", "--timeout-ms", "1000", "--endpoint",
            "http://127.0.0.1:1/v1/chat/completions"],
            input=json.dumps(self.wrapper).encode(), stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, timeout=10, check=False)
        self.assertEqual(proc.returncode, 1)
        envelope = proc.stdout.decode().strip()
        self.assertTrue(envelope.startswith("error\ttransport\t"))
        rows = [json.loads(line) for line in (run_dir / "history_llm_calls.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["stage"], "transport")
        self.assertEqual(rows[0]["status"], "error")
        self.assertEqual(rows[0]["endpoint"], "http://127.0.0.1:1/v1/chat/completions")


if __name__ == "__main__":
    unittest.main()
