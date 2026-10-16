#!/usr/bin/env python3
"""Append Veloren native TalkToNpc requests and inspect its JSONL events.

This utility only reads/writes the explicitly supplied JSONL files. It does
not start Veloren, alter saves, infer NPCs, or treat an emitted event as proof
that a recipient accepted speech.
"""

import argparse
import json
import sys
import time
from pathlib import Path


def append_record(path: str, record: dict) -> None:
    encoded = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
    with Path(path).open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(encoded + "\n")
        stream.flush()
    print(f"appended (not server-accepted): {encoded}")


def read_events(path: str, request_id: str | None, follow: bool) -> int:
    event_path = Path(path)
    try:
        stream = event_path.open("r", encoding="utf-8")
    except OSError as exc:
        print(f"cannot open events file: {exc}", file=sys.stderr)
        return 2

    with stream:
        pending = ""
        while True:
            chunk = stream.readline()
            if chunk:
                pending += chunk
                while "\n" in pending:
                    line, pending = pending.split("\n", 1)
                    try:
                        record = json.loads(line)
                    except json.JSONDecodeError:
                        print(json.dumps({"event": "unparsed_line", "raw": line}), flush=True)
                        continue
                    if request_id is None or record.get("request_id") == request_id:
                        print(json.dumps(record, ensure_ascii=False, separators=(",", ":")), flush=True)
                continue
            if not chunk:
                if not follow:
                    if pending:
                        print(json.dumps({"event": "incomplete_line", "raw": pending}), flush=True)
                    return 0
                time.sleep(0.25)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    request = commands.add_parser("request", help="append one TalkToNpc request")
    request.add_argument("--requests", required=True, help="explicit request JSONL path")
    request.add_argument("--source", required=True)
    request.add_argument("--request-id", required=True)
    request.add_argument("--npc-uid", required=True, type=int)
    request.add_argument("--target-uid", required=True, type=int)
    request.add_argument("--ttl", required=True, type=float, help="seconds; server accepts 0.1–60")

    cancel = commands.add_parser("cancel", help="append a cancellation request")
    cancel.add_argument("--requests", required=True, help="explicit request JSONL path")
    cancel.add_argument("--request-id", required=True)

    events = commands.add_parser("events", help="print JSONL events without interpreting success")
    events.add_argument("--events", required=True, help="explicit events JSONL path")
    events.add_argument("--request-id", help="only print records with this request ID")
    events.add_argument("--follow", action="store_true", help="continue waiting for appended events")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.command == "request":
        if not 0.1 <= args.ttl <= 60.0:
            print("TTL must be between 0.1 and 60 seconds", file=sys.stderr)
            return 2
        if not args.source or len(args.source.encode("utf-8")) > 128:
            print("source must be non-empty and at most 128 UTF-8 bytes", file=sys.stderr)
            return 2
        if not args.request_id or len(args.request_id.encode("utf-8")) > 128:
            print("request ID must be non-empty and at most 128 UTF-8 bytes", file=sys.stderr)
            return 2
        if args.npc_uid < 0 or args.target_uid < 0:
            print("NPC UIDs must be non-negative integers", file=sys.stderr)
            return 2
        if args.npc_uid == args.target_uid:
            print("NPC and target UIDs must differ", file=sys.stderr)
            return 2
        append_record(args.requests, {
            "request_id": args.request_id,
            "npc_uid": args.npc_uid,
            "source": args.source,
            "ttl": args.ttl,
            "kind": "TalkToNpc",
            "target_uid": args.target_uid,
        })
        return 0
    if args.command == "cancel":
        if not args.request_id or len(args.request_id.encode("utf-8")) > 128:
            print("request ID must be non-empty and at most 128 UTF-8 bytes", file=sys.stderr)
            return 2
        append_record(args.requests, {"cancel_request_id": args.request_id})
        return 0
    return read_events(args.events, args.request_id, args.follow)


if __name__ == "__main__":
    raise SystemExit(main())
