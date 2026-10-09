#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
SOURCE="$ROOT/tools/native_platform_v0/evennia"
LOCAL="$ROOT/_local_data/native_platform_v0/evennia"
VENV="$LOCAL/venv"
GAME="$LOCAL/nativep1"
RUN_ID="${RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
if [[ ! "$RUN_ID" =~ ^[A-Za-z0-9._-]+$ || "$RUN_ID" == "." || "$RUN_ID" == ".." ]]; then
    printf 'Invalid RUN_ID: %s\n' "$RUN_ID" >&2
    exit 2
fi
OUT="$ROOT/outputs/native_platform_p1p2_v0/p1_evennia_20261010/runs/$RUN_ID"

mkdir -p "$LOCAL" "$(dirname "$OUT")"
mkdir "$OUT"
exec > >(tee "$OUT/bootstrap.log") 2>&1

if [[ ! -x "$VENV/bin/python" ]]; then
    python3.12 -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install -r "$SOURCE/requirements.lock"

if [[ ! -d "$GAME" ]]; then
    (cd "$LOCAL" && "$VENV/bin/evennia" --init nativep1)
fi

cp "$SOURCE/loopback_settings.py" "$GAME/typeclasses/native_platform_settings.py"
cp "$SOURCE/evadventure_ai_ticker.py" "$GAME/typeclasses/evadventure_ai_ticker.py"
"$VENV/bin/python" - "$GAME/server/conf/settings.py" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
text = path.read_text()
line = "from typeclasses.native_platform_settings import *"
if line not in text:
    marker = 'SERVERNAME = "nativep1"\n'
    if marker not in text:
        raise SystemExit("Expected nativep1 SERVERNAME setting not found")
    text = text.replace(marker, marker + "\n# Local loopback settings overlay.\n" + line + "\n", 1)
    path.write_text(text)
PY

(cd "$GAME" && PATH="$VENV/bin:$PATH" "$VENV/bin/evennia" migrate)
printf 'Bootstrap complete. Game scaffold: %s\n' "$GAME"
