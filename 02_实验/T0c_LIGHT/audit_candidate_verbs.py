#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from collections import Counter
from pathlib import Path

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")

def iter_records(path: Path):
    text = path.read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        for line in text.splitlines():
            if line.strip():
                yield json.loads(line)
        return
    if isinstance(data, list):
        yield from data
    elif isinstance(data, dict):
        yield data
    else:
        raise ValueError("Replay input must be JSON object/list or JSONL")

def first_token(value) -> str:
    m = TOKEN_RE.search(str(value).casefold())
    return m.group(0) if m else "<empty>"

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("replay", type=Path)
    ap.add_argument("rules", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--max-trajectories", type=int, default=50)
    args = ap.parse_args()

    rules = json.loads(args.rules.read_text(encoding="utf-8"))
    known = {verb for group in rules["groups"] for verb in group["verbs"]}
    counts = Counter()
    mapped = total = trajectories = 0

    for rec in iter_records(args.replay):
        if rec.get("source_dataset") != "LIGHT":
            continue
        if rec.get("source_episode_context", {}).get("quarantine"):
            continue
        trajectories += 1
        for step in rec.get("steps", []):
            candidates = step.get("candidate_set_factual")
            if not isinstance(candidates, list):
                continue
            for candidate in candidates:
                token = first_token(candidate)
                counts[token] += 1
                total += 1
                mapped += int(token in known)
        if trajectories >= args.max_trajectories:
            break

    result = {
        "trajectory_count": trajectories,
        "candidate_count": total,
        "mapped_candidate_count": mapped,
        "mapped_rate": mapped / total if total else None,
        "first_tokens": [
            {"token": token, "count": count, "mapped": token in known}
            for token, count in counts.most_common()
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
