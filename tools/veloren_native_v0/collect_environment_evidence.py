#!/usr/bin/env python3
"""Collect allowlisted Veloren environment evidence with local-path redaction.

Reads only fixed log, world-metadata, and startup-settings paths. Excludes game
binaries, assets, profiles, databases, maps, RTSim data, and download attempts.
Refuses to overwrite its unique output directory.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "_local_data/external_games/veloren_0_18_0"
DEST = ROOT / "02_实验/Veloren_Vertical_Slice_v0/evidence/native_environment_20261016"
RUNS = SOURCE / "evidence/native_runs"
USERDATA = SOURCE / "userdata"
WORLD = USERDATA / "native-app-a-20261016T113700Z/singleplayer_worlds/world-2026-10-16-19_40_34_666"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sanitized(data: bytes) -> bytes:
    text = data.decode("utf-8")
    text = text.replace(str(ROOT), "<PROJECT_ROOT>").replace("/Users/2003singer", "<USER_HOME>")
    text = re.sub(r"/Users/[^/\s\"']+", "<USER_HOME>", text)
    return text.encode("utf-8")


def main() -> None:
    if DEST.exists():
        raise SystemExit(f"Refusing to overwrite {DEST}")
    sources = [
        (RUNS / "20261016T112205Z-version.record.json", "native_runs/version.record.json", True),
        (RUNS / "20261016T112205Z-version.stdout.log", "native_runs/version.stdout.log", False),
        (RUNS / "20261016T112205Z-version.stderr.log", "native_runs/version.stderr.log", False),
        (RUNS / "native-a-20261016T112300Z/client.stdout.log", "native_runs/native-a/client.stdout.log", True),
        (RUNS / "native-a-20261016T112300Z/client.stderr.log", "native_runs/native-a/client.stderr.log", True),
        (RUNS / "native-app-a-20261016T113700Z/client.stdout.log", "native_runs/native-app-a/client.stdout.log", True),
        (RUNS / "native-app-a-20261016T113700Z/client.stderr.log", "native_runs/native-app-a/client.stderr.log", True),
        (WORLD / "meta.ron", "userdata/world/meta.ron", False),
        (USERDATA / "native-app-a-20261016T113700Z/voxygen/settings.ron", "userdata/native-app-a/voxygen/settings.ron", True),
    ]
    missing = [str(src) for src, _, _ in sources if not src.is_file()]
    if missing:
        raise SystemExit("Missing allowlisted files: " + "; ".join(missing))
    DEST.mkdir(parents=True)
    entries = []
    for src, rel, redact in sources:
        raw = src.read_bytes()
        out = sanitized(raw) if redact else raw
        target = DEST / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(out)
        entries.append({"path": rel, "source_relpath": src.relative_to(ROOT).as_posix(),
                        "source_bytes": len(raw), "source_sha256": digest(raw),
                        "output_bytes": len(out), "output_sha256": digest(out),
                        "redacted_local_paths": redact and raw != out})
    shots = []
    for src in USERDATA.rglob("*"):
        if src.is_file() and src.suffix.lower() in {".png", ".jpg", ".jpeg"} and "screenshot" in src.name.lower():
            rel = f"userdata/screenshots/{src.name}"
            raw = src.read_bytes()
            target = DEST / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
            entries.append({"path": rel, "source_relpath": src.relative_to(ROOT).as_posix(),
                            "source_bytes": len(raw), "source_sha256": digest(raw),
                            "output_bytes": len(raw), "output_sha256": digest(raw), "redacted_local_paths": False})
            shots.append(rel)
    manifest = {
        "date": "2026-10-16",
        "scope": "environment preparation only; no NPC baseline or control-loop result",
        "official_artifact": {"bytes": 404762532,
            "sha256": "4fbd5cf1794e149ec9bad38dcbf34d1a9b4e1eda428e8be0a28f12eacec29afc",
            "binary_sha256": "70572f61dbde6395f3bb737d0031ebb5c1907e0567cf82b2a33d77481b24ec28",
            "build_commit": "1d12f35edd6cdbfc1fb921c167cdd7beeeffe248",
            "source": "official GitLab v0.18.0 artifact; not GitHub tag b2f1060",
            "app_wrapper": "binary copy with linked assets; signature and quarantine unchanged"},
        "interpretation": {"version_probe": "exit -9; stdout and stderr are 0 bytes; cause unknown",
            "native_a": "native launch evidence", "native_app_a": "app wrapper launch and single-player world generation evidence",
            "npc_baseline": "NOT_ESTABLISHED", "current_game_process": "not running; reason unknown",
            "screenshots_found": shots, "screenshot_note": "No native F4 screenshot found in Veloren userdata." if not shots else "Native screenshots copied."},
        "files": entries,
        "excluded": ["account profile", "database/WAL/SHM", "map.bin", "RTSim data", "binaries", "assets", "source", "download_attempts"]}
    (DEST / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
