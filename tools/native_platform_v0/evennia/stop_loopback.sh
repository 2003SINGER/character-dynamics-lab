#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
LOCAL="$ROOT/_local_data/native_platform_v0/evennia"
VENV="$LOCAL/venv"
GAME="$LOCAL/nativep1"
RUN_ID="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
if [[ ! "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ || "$RUN_ID" == "." || "$RUN_ID" == ".." ]]; then
    printf 'Invalid RUN_ID: %s\n' "$RUN_ID" >&2
    exit 2
fi
OUT="$ROOT/outputs/native_platform_p1p2_v0/p1_evennia_20261010/runs/$RUN_ID"

mkdir -p "$(dirname "$OUT")"
mkdir "$OUT"
cd "$GAME"
PATH="$VENV/bin:$PATH" "$VENV/bin/evennia" stop 2>&1 | tee "$OUT/stop.log"
