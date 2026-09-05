#!/usr/bin/env python3
"""Export a deterministic, provenance-preserving SOTOPIA-π development slice.

The input Redis database must already be loaded by a local Redis Stack server.
This script never mutates Redis. It uses redis-cli JSON.GET because the source
dump stores records as RedisJSON values.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


EPISODE_PREFIX = ":sotopia.database.logs.EpisodeLog:"
AGENT_PREFIX = ":sotopia.database.persistent_profile.AgentProfile:"
ENV_PREFIX = ":sotopia.database.persistent_profile.EnvironmentProfile:"


def cli(redis_cli: str, port: int, *arguments: str) -> str:
    completed = subprocess.run(
        [redis_cli, "-p", str(port), "--raw", *arguments],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def json_value(redis_cli: str, port: int, key: str) -> dict[str, Any]:
    raw = cli(redis_cli, port, "JSON.GET", key)
    if not raw:
        raise ValueError(f"JSON.GET returned no value for {key}")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError(f"{key} did not decode to an object")
    return value


def stable_episode_keys(redis_cli: str, port: int, count: int) -> list[str]:
    keys = [
        key
        for key in cli(redis_cli, port, "--scan", "--pattern", f"*{EPISODE_PREFIX}*").splitlines()
        if key.startswith(EPISODE_PREFIX)
    ]
    if len(keys) < count:
        raise ValueError(f"only found {len(keys)} episode keys; need {count}")
    return sorted(keys, key=lambda key: (hashlib.sha256(key.encode()).hexdigest(), key))[:count]


def actor_action_count(episode: dict[str, Any], agent_names: set[str]) -> int:
    """Count non-idle actor-to-environment records without interpreting language."""
    count = 0
    for turn in episode.get("messages", []):
        if not isinstance(turn, list):
            continue
        for record in turn:
            if not isinstance(record, list) or len(record) < 3:
                continue
            sender, receiver, content = record[:3]
            if sender in agent_names and receiver == "Environment" and content != "did nothing":
                count += 1
    return count


def actor_action_surface_labels(episode: dict[str, Any], agent_names: set[str]) -> Counter[str]:
    """Expose the dataset's action surface without pretending it is an ontology."""
    labels: Counter[str] = Counter()
    for turn in episode.get("messages", []):
        if not isinstance(turn, list):
            continue
        for record in turn:
            if not isinstance(record, list) or len(record) < 3:
                continue
            sender, receiver, content = record[:3]
            if sender not in agent_names or receiver != "Environment" or not isinstance(content, str):
                continue
            labels[content if content == "did nothing" else content.split(":", 1)[0]] += 1
    return labels


def initial_information_boundary(
    episode: dict[str, Any], agent_names: set[str]
) -> dict[str, bool]:
    """Check only the explicit initial prompts; never infer hidden knowledge."""
    messages = episode.get("messages", [])
    if not messages or not isinstance(messages[0], list):
        return {"self_goal_visible_for_all": False, "other_goal_masked_for_all": False}

    initial_context: dict[str, str] = {}
    for record in messages[0]:
        if (
            isinstance(record, list)
            and len(record) >= 3
            and record[0] == "Environment"
            and record[1] in agent_names
            and isinstance(record[2], str)
        ):
            initial_context[record[1]] = record[2]

    self_goal_visible = True
    other_goal_masked = True
    for actor in agent_names:
        context = initial_context.get(actor, "")
        self_goal_visible &= f"{actor}'s goal:" in context and f"{actor}'s goal: Unknown" not in context
        other_names = agent_names - {actor}
        other_goal_masked &= all(f"{other}'s goal: Unknown" in context for other in other_names)
    return {
        "self_goal_visible_for_all": self_goal_visible,
        "other_goal_masked_for_all": other_goal_masked,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--redis-cli", required=True)
    parser.add_argument("--port", type=int, default=16380)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--count", type=int, default=30)
    parser.add_argument("--raw-sha256", required=True)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    environment_keys: set[str] = set()
    agent_keys: set[str] = set()
    action_surface_labels: Counter[str] = Counter()

    for episode_key in stable_episode_keys(args.redis_cli, args.port, args.count):
        episode = json_value(args.redis_cli, args.port, episode_key)
        agent_ids = episode.get("agents")
        environment_id = episode.get("environment")
        messages = episode.get("messages")
        if not isinstance(agent_ids, list) or len(agent_ids) != 2:
            raise ValueError(f"{episode_key} does not name exactly two agents")
        if not isinstance(environment_id, str) or not isinstance(messages, list):
            raise ValueError(f"{episode_key} lacks environment or ordered messages")

        agent_documents = [
            json_value(args.redis_cli, args.port, f"{AGENT_PREFIX}{agent_id}") for agent_id in agent_ids
        ]
        environment_document = json_value(
            args.redis_cli, args.port, f"{ENV_PREFIX}{environment_id}"
        )
        agent_names = {
            " ".join(
                part for part in (agent.get("first_name"), agent.get("last_name")) if isinstance(part, str)
            ).strip()
            for agent in agent_documents
        }
        agent_names.discard("")
        action_surface_labels.update(actor_action_surface_labels(episode, agent_names))

        records.append(
            {
                "source": {
                    "dataset": "cmu-lti/sotopia-pi",
                    "dataset_license": "CC-BY-SA-4.0",
                    "raw_rdb_sha256": args.raw_sha256,
                    "source_episode_key": episode_key,
                    "episode_provenance": "unknown_within_dump; do not label human",
                },
                "episode": episode,
                "environment": environment_document,
                "agents": agent_documents,
                "diagnostics": {
                    "agent_count": len(agent_documents),
                    "message_turn_count": len(messages),
                    "non_idle_actor_action_count": actor_action_count(episode, agent_names),
                    "initial_information_boundary": initial_information_boundary(episode, agent_names),
                },
            }
        )
        environment_keys.add(f"{ENV_PREFIX}{environment_id}")
        agent_keys.update(f"{AGENT_PREFIX}{agent_id}" for agent_id in agent_ids)

    output = args.out_dir / "episodes.jsonl"
    with output.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    manifest = {
        "purpose": "T0b data-format and information-boundary feasibility pilot; not a model result",
        "dataset": "cmu-lti/sotopia-pi",
        "dataset_license": "CC-BY-SA-4.0",
        "sample_method": "lowest SHA-256 rank of EpisodeLog Redis key; deterministic, not stratified",
        "raw_rdb_sha256": args.raw_sha256,
        "episode_count": len(records),
        "unique_agent_profiles": len(agent_keys),
        "unique_environment_profiles": len(environment_keys),
        "message_turn_count": [record["diagnostics"]["message_turn_count"] for record in records],
        "non_idle_actor_action_count": [
            record["diagnostics"]["non_idle_actor_action_count"] for record in records
        ],
        "actor_action_surface_labels": dict(sorted(action_surface_labels.items())),
        "initial_self_goal_visible_episode_count": sum(
            record["diagnostics"]["initial_information_boundary"]["self_goal_visible_for_all"]
            for record in records
        ),
        "initial_other_goal_masked_episode_count": sum(
            record["diagnostics"]["initial_information_boundary"]["other_goal_masked_for_all"]
            for record in records
        ),
        "provenance_boundary": "episode-level human/expert/self-play source is not encoded in the exported EpisodeLog; all records remain unknown.",
    }
    (args.out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
