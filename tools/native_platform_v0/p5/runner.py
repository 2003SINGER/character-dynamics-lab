"""Run external P5 bundles through the authenticated local Evennia service.

This client records evidence; it does not score semantic success. World actions
remain server-side, and the optional DB export uses the separate read-only
Django/SQLite exporter after the scene run has completed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
RUNS_DIR = PROJECT_ROOT / "02_实验/Native_Platform_P5_v0/runs"
EVENNIA_PYTHON = PROJECT_ROOT / "_local_data/native_platform_v0/evennia/venv/bin/python"
SOURCE_FILES = (
    "tools/native_platform_v0/p5/runner.py",
    "tools/native_platform_v0/p5/audit.py",
    "tools/native_platform_v0/p5/bundle.py",
    "tools/native_platform_v0/p5/monitor.py",
    "tools/native_platform_v0/p5/planning.py",
    "tools/native_platform_v0/p5/world.py",
    "tools/native_platform_v0/p5/agency.py",
    "tools/native_platform_v0/p5/service.py",
    "tools/native_platform_v0/p3/control_service.py",
    "tools/native_platform_v0/p3/export_evidence.py",
    "tools/native_platform_v0/p3/mcp_stdio.py",
    "tools/native_platform_v0/p3/scene.py",
    "tools/native_platform_v0/p3/agency.py",
    "tools/native_platform_v0/p3/p4_world.py",
    "tools/native_platform_v0/p3/p4_agency.py",
    "tools/native_platform_v0/p3/p4_social.py",
    "tools/native_platform_v0/ensemble/runner.mjs",
    "tools/trajectory_constraints_v0/trace.py",
)
PRESETS = {"native_default_reject_v0", "hero_intelligence_30_v0"}
SUITE_SCHEMA = "native-p5-run-suite-v1"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def request_hashes(bundle_manifest: dict[str, Any]) -> dict[str, Any]:
    return {"bundle_sha256": bundle_manifest["bundle_sha256"],
            "edit_bundle_sha256": [row["sha256"] for row in bundle_manifest["edit_bundles"]]}


def source_manifest() -> dict[str, Any]:
    hashes = {name: sha256_bytes((PROJECT_ROOT / name).read_bytes())
              if (PROJECT_ROOT / name).is_file() else "missing"
              for name in SOURCE_FILES}
    packed = json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()
    revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT,
                              text=True, capture_output=True, check=False)
    return {"git_revision": revision.stdout.strip() if revision.returncode == 0 else None,
            "hash_scope": "SHA-256 of working-tree source bytes; git_revision is base commit only",
            "source_sha256": hashes,
            "source_snapshot_sha256": sha256_bytes(packed)}


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot load JSON input {path.name}: {type(exc).__name__}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"JSON input {path.name} must contain an object")
    return value


def load_suite(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    suite = load_json(path)
    if suite.get("schema") != SUITE_SCHEMA or not isinstance(suite.get("runs"), list):
        raise ValueError(f"suite must use {SUITE_SCHEMA} and contain runs[]")
    rows = suite["runs"]
    ids = [row.get("id") for row in rows if isinstance(row, dict)]
    if len(ids) != len(rows) or any(not isinstance(item, str) or not item for item in ids):
        raise ValueError("every run row requires a nonempty string id")
    if len(ids) != len(set(ids)):
        raise ValueError("run ids must be unique")
    return suite, rows


def _bundle_from_row(row: dict[str, Any], suite_path: Path) -> tuple[dict[str, Any], str]:
    bundle_path = Path(row.get("bundle", ""))
    if not bundle_path.is_absolute():
        bundle_path = suite_path.parent / bundle_path
    raw = bundle_path.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("bundle JSON root must be an object")
    return data, sha256_bytes(raw)


def _normalize_run(row: dict[str, Any], suite_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if row.get("initial_social_preset") not in PRESETS:
        raise ValueError(f"run {row.get('id')!r} has an unsupported native social preset")
    horizon = row.get("horizon")
    if type(horizon) is not int or not 1 <= horizon <= 24:
        raise ValueError("horizon must be an integer from 1 to 24")
    if type(row.get("director_enabled")) is not bool:
        raise ValueError("director_enabled must be boolean")
    seed = row.get("seed", 20261010)
    if type(seed) is not int or not 0 <= seed <= 2**31 - 1:
        raise ValueError("seed must be a nonnegative 31-bit integer")
    bundle, bundle_sha = _bundle_from_row(row, suite_path)
    edits, edit_hashes = [], []
    for edit in row.get("edits", []):
        if not isinstance(edit, dict) or type(edit.get("at")) is not int or type(edit.get("expected_version")) is not int:
            raise ValueError("each edit requires integer at and expected_version")
        candidate_path = Path(edit.get("bundle", ""))
        if not candidate_path.is_absolute():
            candidate_path = suite_path.parent / candidate_path
        candidate_bytes = candidate_path.read_bytes()
        candidate = json.loads(candidate_bytes.decode("utf-8"))
        if not isinstance(candidate, dict):
            raise ValueError("edited bundle JSON root must be an object")
        edit_hashes.append({"at": edit["at"], "expected_version": edit["expected_version"],
                            "sha256": sha256_bytes(candidate_bytes), "bundle": candidate})
        edits.append({"at": edit["at"], "expected_version": edit["expected_version"],
                      "raw_bundle": candidate})
    request = {"bundle": bundle,
               "initial_social_preset": row["initial_social_preset"],
               "horizon": horizon,
               "interventions": row.get("interventions", []),
               "edits": edits,
               "director_enabled": row["director_enabled"],
               "seed": seed,
               "shared_supply": row.get("shared_supply", False)}
    if "initial_main_open" in row:
        if type(row["initial_main_open"]) is not bool:
            raise ValueError("initial_main_open must be boolean")
        request["initial_main_open"] = row["initial_main_open"]
    if type(request["shared_supply"]) is not bool:
        raise ValueError("shared_supply must be boolean")
    return request, {"bundle": bundle, "bundle_sha256": bundle_sha,
                     "edit_bundles": edit_hashes}


def write_run(document: dict[str, Any], runs_dir: Path = RUNS_DIR) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    case_id = document["configuration"]["id"]
    slug = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in case_id)[:70]
    for _ in range(8):
        path = runs_dir / f"p5-{slug}-{timestamp}-{secrets.token_hex(3)}.json"
        try:
            with path.open("x", encoding="utf-8") as handle:
                json.dump(document, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            return path
        except FileExistsError:
            continue
    raise FileExistsError("could not allocate a unique P5 evidence filename")


def export_db_evidence(scene_id: str) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Read the committed Evennia DB through the separate, read-only exporter."""
    command = [str(EVENNIA_PYTHON), "-m", "tools.native_platform_v0.p3.export_evidence",
               "--p5", "--scene-id", scene_id]
    completed = subprocess.run(command, cwd=PROJECT_ROOT, text=True,
                               capture_output=True, timeout=120, check=False)
    result = {"command": command[1:], "exit_code": completed.returncode,
              "stdout_tail": completed.stdout[-2000:], "stderr_tail": completed.stderr[-2000:]}
    if completed.returncode != 0:
        return None, result
    try:
        export_result = json.loads(completed.stdout.strip().splitlines()[-1])
        output_path = Path(export_result["path"])
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path
        raw = output_path.read_bytes()
        result.update({"artifact_path": str(output_path), "artifact_sha256": sha256_bytes(raw)})
        evidence = json.loads(raw.decode("utf-8"))
    except (IndexError, OSError, json.JSONDecodeError):
        return None, {**result, "parse_error": "exporter output was not a readable JSON artifact"}
    return evidence, result


def run_row(row: dict[str, Any], suite_path: Path, *, call_rpc=None,
            runs_dir: Path = RUNS_DIR, export_db: bool = True) -> tuple[dict[str, Any], Path]:
    from tools.native_platform_v0.p3.mcp_stdio import rpc_call
    call_rpc = call_rpc or rpc_call
    request, bundle_manifest = _normalize_run(row, suite_path)
    transport_error = None
    try:
        response = call_rpc("run_p5_scenario", request)
        if not isinstance(response, dict):
            raise ValueError("run_p5_scenario response must be a JSON object")
    except Exception as exc:
        # Keep a durable failure artifact even when RPC rejects the request or
        # times out; do not mislabel an absent response as a semantic negative.
        response = {"ok": False, "run_status": "INCOMPLETE", "scene": {},
                    "error": {"type": type(exc).__name__}}
        transport_error = {"type": type(exc).__name__, "message": str(exc)[:500]}
    scene = response.get("scene", {})
    scene_id = scene.get("scene_id") if isinstance(scene, dict) else None
    db_evidence, db_export = (None, {"status": "NOT_REQUESTED"})
    if export_db and transport_error is None and isinstance(scene_id, str) and scene_id:
        db_evidence, db_export = export_db_evidence(scene_id)
    document = {"schema": "native-p5-run-artifact-v1",
                "recorded_at": datetime.now(timezone.utc).isoformat(),
                "configuration": {key: value for key, value in row.items() if key != "bundle"},
                "request": {**{key: value for key, value in request.items() if key not in {"bundle", "edits"}},
                            **request_hashes(bundle_manifest)},
                "manifest": {"source": source_manifest(), **bundle_manifest,
                             "edit_bundles": bundle_manifest["edit_bundles"]},
                "response": response,
                "transport_error": transport_error,
                "db_export": db_export,
                "db_evidence": db_evidence}
    path = write_run(document, runs_dir)
    return document, path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, required=True, help="external P5 run-suite JSON")
    parser.add_argument("--run-id", help="run only this exact suite row")
    parser.add_argument("--no-db-export", action="store_true", help="skip the separate persisted-DB readback")
    args = parser.parse_args(argv)
    try:
        suite_path = args.suite.resolve()
        suite, rows = load_suite(suite_path)
        if args.run_id:
            rows = [row for row in rows if row["id"] == args.run_id]
            if not rows:
                raise ValueError(f"unknown run id {args.run_id!r}")
        results = []
        for row in rows:
            document, path = run_row(row, suite_path, export_db=not args.no_db_export)
            response = document["response"]
            results.append({"id": row["id"], "path": str(path),
                            "run_status": response.get("run_status", "INCOMPLETE"),
                            "scene_id": response.get("scene", {}).get("scene_id"),
                            "db_readback": document["db_evidence"] is not None})
        print(json.dumps({"suite_id": suite.get("suite_id"), "runs": results}, ensure_ascii=False))
        return 0 if all(item["run_status"] == "COMPLETE" for item in results) else 2
    except Exception as exc:
        parser.error(f"P5 runner stopped before a complete record: {type(exc).__name__}: {exc}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
