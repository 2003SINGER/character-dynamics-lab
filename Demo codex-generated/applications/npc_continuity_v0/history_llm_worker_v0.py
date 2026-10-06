#!/usr/bin/env python3
"""Single-call, loopback-only llama-server transport for the continuity harness."""

import argparse
import hashlib
import json
import pathlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

DEFAULT_ENDPOINT = "http://127.0.0.1:8080/v1/chat/completions"
SYSTEM_PROMPT = (
    "Protocol: npc-history-llm-prompt-v1. Select one action using only the supplied current observation, actor-visible history, "
    "running action, and admissible candidates. Choose an action that sensibly advances "
    "known goals while responding to relevant new events. Prefer coherent continuation "
    "when an event does not warrant interruption; when a known goal is complete, do not "
    "continue pursuing it. Do not invent facts or actions. Select only a supplied candidate_id. "
    "Return only one JSON object with exactly this shape and no surrounding text: "
    "{\"candidate_id\":\"<one supplied candidate id>\"}."
)


def canonical_sha256(value):
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def log_record(run_dir, record):
    with (run_dir / "history_llm_calls.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()


def envelope_ok(candidate_id, request_hash, status, elapsed_ms, usage):
    prompt = usage.get("prompt_tokens", -1) if isinstance(usage, dict) else -1
    completion = usage.get("completion_tokens", -1) if isinstance(usage, dict) else -1
    return "\t".join(("ok", candidate_id, request_hash, str(status), str(elapsed_ms), str(prompt), str(completion)))


def envelope_error(stage, error_type, request_hash):
    return "\t".join(("error", stage, error_type, "", request_hash))


def fail(run_dir, record, stage, error_type, message, request_hash=""):
    record.update({"status": "error", "stage": stage, "error_type": error_type,
                   "error": str(message)[:2000], "request_sha256": request_hash})
    if run_dir.is_dir():
        log_record(run_dir, record)
    return 1, envelope_error(stage, error_type, request_hash)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def process_request(wrapper, run_dir, model_id, timeout_ms, endpoint=DEFAULT_ENDPOINT,
                    opener_factory=urllib.request.build_opener):
    record = {"protocol": "npc-history-llm-call-v1", "prompt_protocol": "npc-history-llm-prompt-v1",
              "endpoint": endpoint, "model": model_id,
              "temperature": 0, "thinking": False, "max_tokens": 96, "timeout_ms": timeout_ms,
              "transport_uses_system_proxy": False, "redirect_policy": "deny"}
    request_hash = ""
    try:
        parsed = urllib.parse.urlparse(endpoint)
        if (parsed.scheme != "http" or parsed.hostname != "127.0.0.1"
                or parsed.path != "/v1/chat/completions" or parsed.query or parsed.fragment):
            return fail(run_dir, record, "endpoint", "UnsafeEndpoint", "loopback llama-server URL required")
        policy_request = wrapper["policy_request"]
        candidate_ids = wrapper["candidate_ids"]
        if (not isinstance(candidate_ids, list) or not candidate_ids
                or len(set(candidate_ids)) != len(candidate_ids)
                or any(not isinstance(item, str) or not item.startswith("c") for item in candidate_ids)):
            return fail(run_dir, record, "request", "InvalidCandidates", "candidate ID list invalid")
        request_body = {
            "model": model_id,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(policy_request, ensure_ascii=False,
                                                            sort_keys=True, separators=(",", ":"))},
            ],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "npc_action_choice",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {"candidate_id": {"type": "string", "enum": candidate_ids}},
                    "required": ["candidate_id"], "additionalProperties": False,
                },
            }},
            "temperature": 0, "max_tokens": 96, "stream": False,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        request_hash = canonical_sha256(request_body)
        record.update({"request_sha256": request_hash, "request": request_body,
                       "candidate_ids": candidate_ids})
        if not run_dir.is_dir():
            return fail(run_dir, record, "journal", "RunDirectoryMissing", "exclusive run directory missing", request_hash)
        body = json.dumps(request_body, ensure_ascii=False, separators=(",", ":")).encode()
        call = urllib.request.Request(endpoint, data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        opener = opener_factory(urllib.request.ProxyHandler({}), NoRedirect())
        started = time.monotonic()
        response_body, http_status = b"", 0
        try:
            with opener.open(call, timeout=timeout_ms / 1000.0) as response:
                http_status = response.status
                response_body = response.read(2_000_001)
                if len(response_body) > 2_000_000:
                    raise ValueError("response exceeded 2MB")
        except urllib.error.HTTPError as error:
            http_status = error.code
            response_body = error.read(2_000_001)
            record["response_raw"] = response_body.decode("utf-8", errors="replace")[:2000000]
            record["elapsed_ms"] = int((time.monotonic() - started) * 1000)
            return fail(run_dir, record, "http", "HttpError", f"HTTP {error.code}", request_hash)
        except Exception as error:
            record["elapsed_ms"] = int((time.monotonic() - started) * 1000)
            return fail(run_dir, record, "transport", type(error).__name__, error, request_hash)
        elapsed = int((time.monotonic() - started) * 1000)
        raw = response_body.decode("utf-8", errors="replace")
        try:
            response = json.loads(raw)
            choice = response["choices"][0]
            if choice.get("finish_reason") == "length":
                raise ValueError("finish_reason=length; structured response truncated")
            if choice.get("finish_reason") != "stop":
                raise ValueError("missing normal stop finish_reason")
            content = choice["message"]["content"]
            if not isinstance(content, str):
                raise ValueError("assistant content is not text")
            selected = json.loads(content)
            if not isinstance(selected, dict) or set(selected) != {"candidate_id"}:
                raise ValueError("choice JSON must contain only candidate_id")
            candidate_id = selected["candidate_id"]
            if not isinstance(candidate_id, str) or candidate_id not in candidate_ids:
                raise ValueError("candidate_id outside hard-admissible IDs")
        except Exception as error:
            record.update({"response_raw": raw[:2000000], "elapsed_ms": elapsed,
                           "http_status": http_status})
            if "response" in locals() and isinstance(response, dict):
                record["usage"] = response.get("usage")
            return fail(run_dir, record, "response_validation", type(error).__name__, error, request_hash)
        usage = response.get("usage", {})
        record.update({"status": "ok", "http_status": http_status, "response": response,
                       "assistant_content": content, "candidate_id": candidate_id,
                       "usage": usage, "elapsed_ms": elapsed})
        log_record(run_dir, record)
        return 0, envelope_ok(candidate_id, request_hash, http_status, elapsed, usage)
    except Exception as error:
        return fail(run_dir, record, "worker", type(error).__name__, error, request_hash)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-directory", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--timeout-ms", type=int, required=True)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    args = parser.parse_args()
    run_dir = pathlib.Path(args.run_directory)
    try:
        raw = sys.stdin.buffer.read(1_000_001)
        if len(raw) > 1_000_000:
            code, envelope = fail(run_dir, {"protocol": "npc-history-llm-call-v1"},
                                  "request", "ContextTooLong", "policy request exceeds 1MB")
        else:
            code, envelope = process_request(json.loads(raw), run_dir, args.model,
                                             args.timeout_ms, args.endpoint)
    except Exception as error:
        code, envelope = fail(run_dir, {"protocol": "npc-history-llm-call-v1", "model": args.model},
                              "request", type(error).__name__, error)
    print(envelope, flush=True)
    return code


if __name__ == "__main__":
    sys.exit(main())
