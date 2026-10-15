"""Extract only permitted semantic-run evidence from a local agent transcript.

Full agent transcripts contain private harness instructions and are NOT copied.
This is a controller-side provenance extraction, not a bare-model attestation.
"""
import argparse
import hashlib
import json
from pathlib import Path

from .run import write


def collect(transcript: Path, destination: Path):
    records = [json.loads(line) for line in transcript.read_text().splitlines()]
    messages = [r["payload"] for r in records if r["type"] == "response_item"
                and r["payload"].get("type") == "message"
                and r["payload"].get("role") == "assistant"]
    if len(messages) != 1:
        raise ValueError("expected exactly one final semantic response")
    content = messages[0]["content"]
    raw = "".join(c["text"] for c in content if c.get("type") in {"output_text", "text"})
    candidate = json.loads(raw)
    calls = [r["payload"] for r in records if r["type"] == "response_item"
             and r["payload"].get("type") in {"custom_tool_call", "function_call"}]
    contexts = [r["payload"] for r in records if r["type"] == "turn_context"]
    destination.mkdir(parents=True, exist_ok=False)
    (destination / "response.raw.txt").write_text(raw)
    write(destination / "candidate.json", candidate)
    write(destination / "provenance.json", {
        "requested_model": "gpt-6-luna", "observed_turn_models": sorted({c.get("model", "UNKNOWN") for c in contexts}),
        "classification": "AGENT_CONFOUNDED", "semantic_agent_episodes": 1,
        "private_harness_and_workspace_access": "not technically disabled; observed calls exported separately",
        "transcript_sha256": hashlib.sha256(transcript.read_bytes()).hexdigest(),
        "response_sha256": hashlib.sha256(raw.encode()).hexdigest(),
        "raw_response_extraction": "exact decoded assistant final content; no JSON repair or atom addition",
        "task_message": "controller request retained separately; full server plaintext/harness not published",
        "tool_calls": [{"type": c["type"], "name": c.get("name"), "input": c.get("input", c.get("arguments"))} for c in calls],
        "not_claimed": ["bare-model benchmark", "formal B1/B2", "hidden prompts disabled", "general author-language competence"],
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("transcript", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    collect(args.transcript, args.destination)
