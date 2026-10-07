#!/usr/bin/env python3
"""Build and check a deterministic publication inventory for review artifacts.

This tool classifies files by explicit path rules and a narrow secret/schema scan.
It never edits, deletes, stages, or redacts candidate files.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
MAX_BYTES = 20 * 1024 * 1024
SCHEMA_VERSION = 1

EXPECTED_ROOTS = (
    "outputs",
    "Demo codex-generated/demo/core_behavior_eval_v0/paired_7d_pipeline_smoke",
    "Demo codex-generated/demo/core_behavior_eval_v0/paired_30d_development",
    "Demo codex-generated/applications/npc_continuity_v0/STAGE3_CHECKPOINT.md",
)

SECRET_PATTERNS: tuple[tuple[str, re.Pattern[bytes]], ...] = (
    ("aws_access_key_id", re.compile(rb"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(rb"\b(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b")),
    ("slack_token", re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("openai_style_key", re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b")),
    ("bearer_credential", re.compile(rb"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{16,}")),
    (
        "credential_assignment",
        re.compile(
            rb"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|client[_-]?secret|"
            rb"password|passwd|secret|credential)\b\s*[\"']?\s*[:=]\s*[\"']?"
            rb"[A-Za-z0-9_./+=:-]{12,}"
        ),
    ),
    ("private_key_block", re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
)

SOURCE_TEXT_KEYS = {
    "source_o",
    "candidate_set_factual",
    "source_action_a_star",
    "recorded_support",
    "blind_input",
    "gold_evaluator_only",
    "source_text",
    "raw_source_text",
}


def relpath(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def path_tokens(path: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", path.lower()) if token}


def path_exclusion(path: str) -> tuple[str, str] | None:
    p = Path(path)
    parts = [part.lower() for part in p.parts]
    name = p.name.lower()
    tokens = path_tokens(path)

    if name == ".ds_store" or name == "thumbs.db" or "__pycache__" in parts:
        return "exclude", "operating-system or Python cache"
    if name == ".experiment.lock" or name.endswith(".experiment.lock"):
        return "exclude", "transient experiment execution lock"
    if p.suffix.lower() in {".pyc", ".pyo", ".o", ".a", ".so", ".dylib", ".bin"}:
        return "exclude", "compiled/cache binary"

    if any(part == ".git" for part in parts):
        return "exclude", "git metadata"
    if any(part == "cmakefiles" for part in parts):
        return "exclude", "build cache"
    if any(part.startswith("build") for part in parts):
        return "exclude", "build output/cache"
    if any(part in {"local_migrations", "external_assets_2026-09-06"} for part in parts):
        return "exclude", "migration backup or third-party dataset archive"
    if any(part == "sotopia_t0b_2026-09-05" for part in parts):
        return "exclude", "dataset/runtime bundle"
    if any(part == "python_packages" for part in parts):
        return "exclude", "vendored package/runtime"
    if any(part in {"source-cache", "source_cache", "source"} for part in parts):
        return "exclude", "source/cache path"
    if "artifact" in parts:
        return "exclude", "artifact cache/path"
    if "raw" in parts or tokens.intersection({"rawdata", "rawdataset", "rawsource"}):
        return "exclude", "raw source/data path"
    if name == ".env" or name.startswith(".env.") or name in {
        ".npmrc", ".pypirc", ".netrc", "id_rsa", "id_ed25519", "credentials", "credentials.json"
    } or any(marker in name for marker in ("credential", "private_key", "secret_key")):
        return "exclude-review", "credential-like filename; inspect without exposing contents"

    if name.lower() in {
        "projected_input.jsonl",
        "projected_inputs.jsonl",
        "source_input.jsonl",
    }:
        return "exclude", "dataset-derived model input"
    if "verified_dev_slice" in name and name.endswith(".jsonl"):
        return "exclude", "dataset-derived development slice"
    if name in {"blind_input.json", "gold_evaluator_only.json"}:
        return "exclude", "dataset input/evaluator-only gold"
    if "verified_command_dev_slice" in name and name.endswith(".jsonl"):
        return "exclude", "dataset-derived verified development slice"
    if (
        any(part.startswith("light_prediction_admission") for part in parts)
        and name == "review_24.jsonl"
        and "public_result_projections_20261007_v2" not in parts
    ):
        return "exclude", "original dataset review fixture; public projection is handled separately"
    if name == "light_scene_snapshot_v0.jsonl":
        return "exclude", "dataset-derived scene snapshot input"
    if "public_result_projections_20261007" in parts and "public_result_projections_20261007_v2" not in parts:
        return "exclude", "superseded, not-yet-reviewed projection version"
    if (
        len(parts) >= 4
        and parts[0] == "outputs"
        and parts[1] == "experiments"
        and any(part.startswith("light") for part in parts[2:-1])
        and name.endswith(".trace.jsonl")
    ) or (
        len(parts) >= 3
        and parts[0] == "outputs"
        and parts[1] == "t0c_light_batch4"
        and name.endswith(".trace.jsonl")
    ):
        return "excluded_source_text_requires_projection", "LIGHT source-derived trace may contain raw observation/action/candidate text"
    if len(parts) >= 3 and parts[0] == "outputs" and parts[1] == "t0c_light_batch4" and "counterfactual_remove" in name and name.endswith(".jsonl"):
        return "excluded_source_text_requires_projection", "LIGHT counterfactual trace may contain raw removed action/target text"
    if (
        "candidate_artifact.json" in name
        and any(part.startswith("opera_t0d_2026-09-08") for part in parts)
        and "public_result_projections_20261007_v2" not in parts
    ):
        return "excluded_source_text_requires_projection", "OPeRA generated candidate includes dataset-derived target text; await public projection"
    if name.lower().endswith(".pdf") and "literature_sources" in parts:
        return "exclude", "downloaded article original; publish the maintained audit instead"
    if "literature_sources" in parts and name in {
        "source_manifest.md",
        "readme.md",
        "provenance.md",
        "manifest.json",
    }:
        return "publish", "literature source provenance note"
    if "literature_sources" in parts:
        return "exclude", "literature source payload; only provenance notes are in scope"
    basename_tokens = path_tokens(name)
    if ("server" in basename_tokens or "proxy" in basename_tokens) and name.endswith(".log"):
        return "exclude", "environment/log_review; inspect for credentials before publishing"
    return None


def walk_candidate_roots() -> tuple[list[Path], list[dict[str, str]]]:
    files: set[Path] = set()
    roots: list[dict[str, str]] = []
    for root_text in EXPECTED_ROOTS:
        root = ROOT / root_text
        if not root.exists():
            roots.append({"path": root_text, "status": "missing"})
            continue
        if root.is_file():
            files.add(root)
            roots.append({"path": root_text, "status": "present_file"})
            continue
        roots.append({"path": root_text, "status": "present_directory"})
        for current, dirs, names in os.walk(root, followlinks=False):
            current_path = Path(current)
            dirs[:] = sorted(
                d for d in dirs if not (current_path / d).is_symlink()
            )
            for name in names:
                path = current_path / name
                if path.is_file() or path.is_symlink():
                    files.add(path)
    return sorted(files, key=relpath), roots


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def scan_secret_types(data: bytes) -> dict[str, int]:
    matches: dict[str, int] = {}
    for kind, pattern in SECRET_PATTERNS:
        count = sum(1 for _ in pattern.finditer(data))
        if count:
            matches[kind] = count
    return matches


def nested_key_hits(value: Any) -> set[str]:
    hits: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            normalized = str(key).strip().lower()
            if normalized in SOURCE_TEXT_KEYS:
                hits.add(normalized)
            hits.update(nested_key_hits(child))
    elif isinstance(value, list):
        for child in value:
            hits.update(nested_key_hits(child))
    return hits


def source_text_field_hits(path: Path, data: bytes) -> set[str]:
    # This directory contains separately reviewed, identifier/numeric-only projections.
    if "public_result_projections_20261007_v2" in path.as_posix():
        return set()
    # Synthetic fixtures are authored test inputs, not excerpts from the datasets.
    if "synthetic" in path.as_posix().lower() or re.search(
        r"(^|/)(test[^/]*|[^/]*_test[^/]*)($|/)", path.as_posix(), re.IGNORECASE
    ):
        return set()
    if path.name.lower().endswith("manifest.json"):
        return set()
    suffix = path.suffix.lower()
    if suffix not in {".json", ".jsonl", ".ndjson"}:
        return set()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return set()
    hits: set[str] = set()
    if suffix in {".jsonl", ".ndjson"}:
        for line in text.splitlines():
            if not line.strip():
                continue
            try:
                hits.update(nested_key_hits(json.loads(line)))
            except json.JSONDecodeError:
                continue
    else:
        try:
            hits.update(nested_key_hits(json.loads(text)))
        except json.JSONDecodeError:
            pass
    return hits


def classify(path: Path, output_path: Path | None) -> dict[str, Any]:
    name = relpath(path)
    if output_path is not None and path.resolve(strict=False) == output_path.resolve(strict=False):
        return {
            "path": name,
            "bytes": path.stat().st_size if path.exists() else None,
            "sha256": None,
            "status": "exclude",
            "reason": "generated inventory manifest is not a candidate artifact",
        }

    if path.is_symlink():
        try:
            size = len(os.readlink(path).encode("utf-8"))
        except OSError:
            size = None
        return {
            "path": name,
            "bytes": size,
            "sha256": None,
            "status": "exclude-review",
            "reason": "symlink target is not followed",
        }

    try:
        size = path.stat().st_size
    except OSError as exc:
        return {"path": name, "bytes": None, "sha256": None, "status": "exclude-review", "reason": f"stat failed: {type(exc).__name__}"}

    if size >= MAX_BYTES:
        return {
            "path": name,
            "bytes": size,
            "sha256": None,
            "status": "exclude",
            "reason": "single-file size is at least 20 MiB; hash intentionally skipped",
        }

    path_rule = path_exclusion(name)
    if path_rule is not None and path_rule[0] in {"exclude", "exclude-review"}:
        status, reason = path_rule
        return {"path": name, "bytes": size, "sha256": sha256_file(path), "status": status, "reason": reason}

    try:
        data = path.read_bytes()
    except OSError as exc:
        return {"path": name, "bytes": size, "sha256": None, "status": "exclude-review", "reason": f"read failed: {type(exc).__name__}"}

    digest = hashlib.sha256(data).hexdigest()
    scan_data = data
    if path.suffix.lower() == ".gz":
        try:
            with gzip.open(path, "rb") as compressed:
                scan_data = compressed.read(MAX_BYTES + 1)
        except (OSError, EOFError):
            return {
                "path": name,
                "bytes": size,
                "sha256": digest,
                "status": "exclude-review",
                "reason": "compressed payload could not be decoded for secret scan",
            }
        if len(scan_data) > MAX_BYTES:
            return {
                "path": name,
                "bytes": size,
                "sha256": digest,
                "status": "exclude-review",
                "reason": "decompressed payload exceeds 20 MiB secret-scan limit",
            }
    secrets = scan_secret_types(scan_data)
    if secrets:
        labels = ", ".join(f"{kind}={count}" for kind, count in sorted(secrets.items()))
        return {
            "path": name,
            "bytes": size,
            "sha256": digest,
            "status": "exclude-review",
            "reason": f"secret scan matched types/counts only: {labels}",
            "secret_matches": secrets,
        }

    if path_rule is not None and path_rule[0] == "excluded_source_text_requires_projection":
        return {
            "path": name,
            "bytes": size,
            "sha256": digest,
            "status": path_rule[0],
            "reason": path_rule[1],
        }

    source_fields = source_text_field_hits(path, scan_data)
    if source_fields:
        labels = ", ".join(sorted(source_fields))
        return {
            "path": name,
            "bytes": size,
            "sha256": digest,
            "status": "excluded_source_text_requires_projection",
            "reason": f"contains dataset/source text fields requiring a public projection: {labels}",
        }

    if path_rule is not None and path_rule[0] == "publish":
        status, reason = path_rule
    elif name.startswith("outputs/_candidate"):
        status, reason = "publish", "unlinked legacy candidate artifact; retained without asserting experiment linkage"
    else:
        status, reason = "publish", "within explicit candidate roots; no exclusion rule or secret/schema hit"

    row: dict[str, Any] = {"path": name, "bytes": size, "sha256": digest, "status": status, "reason": reason}
    if name.startswith("outputs/_candidate"):
        row["label"] = "unlinked legacy"
    if path.suffix.lower() in {".pt", ".pth"}:
        row["reason"] += "; small local experiment checkpoint retained"
    if re.search(r"(^|/)(test[^/]*|[^/]*_test[^/]*)($|/)", name, re.IGNORECASE):
        row["reason"] += "; test/synthetic artifact retained with its status"
    return row


def build_manifest(output_path: Path | None) -> dict[str, Any]:
    files, roots = walk_candidate_roots()
    rows = [classify(path, output_path) for path in files]
    projection_manifest = ROOT / "outputs/public_result_projections_20261007_v2/manifest.json"
    if projection_manifest.is_file():
        projections = json.loads(projection_manifest.read_text(encoding="utf-8"))
        by_source = {entry["sourcepath"]: entry for entry in projections["sources"]}
        for row in rows:
            entry = by_source.get(row["path"])
            if entry is None:
                continue
            if entry["source_sha256"] != row["sha256"]:
                raise ValueError(f"projection source hash mismatch: {row['path']}")
            row["public_projection"] = {
                "path": entry["outputpath"],
                "sha256": entry["output_sha256"],
                "rows": entry["rows"],
            }
    return {
        "schema_version": SCHEMA_VERSION,
        "candidate_roots": roots,
        "size_limit_bytes": MAX_BYTES,
        "files": rows,
    }


def write_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def confined_path(path: Path) -> Path:
    resolved = path.resolve(strict=False)
    if not resolved.is_relative_to(ROOT):
        raise ValueError("path must remain inside the repository root")
    return resolved


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"manifest unreadable: {type(exc).__name__}") from None
    if not isinstance(manifest, dict) or manifest.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported or invalid manifest schema")
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise ValueError("manifest files must be a list")
    seen: set[str] = set()
    required = {"path", "bytes", "sha256", "status", "reason"}
    for row in rows:
        if not isinstance(row, dict) or not required.issubset(row):
            raise ValueError("manifest row is missing required fields")
        raw_path = row["path"]
        if not isinstance(raw_path, str) or not raw_path or Path(raw_path).is_absolute():
            raise ValueError("manifest row path must be nonempty and relative")
        candidate = Path(raw_path)
        if ".." in candidate.parts or "\\" in raw_path:
            raise ValueError("manifest row path contains traversal or noncanonical separators")
        if raw_path in seen:
            raise ValueError(f"duplicate manifest path: {raw_path}")
        seen.add(raw_path)
        if not isinstance(row["status"], str) or not isinstance(row["reason"], str):
            raise ValueError("manifest status and reason must be strings")
        if row["bytes"] is not None and (not isinstance(row["bytes"], int) or row["bytes"] < 0):
            raise ValueError("manifest bytes must be a nonnegative integer or null")
        if row["status"] == "publish":
            if row["bytes"] is None or not isinstance(row["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"]):
                raise ValueError("published manifest rows require bytes and a SHA-256")
            try:
                confined_path(ROOT / candidate)
            except ValueError:
                raise ValueError("published manifest path escapes repository root") from None
    return manifest


def check_manifest(path: Path) -> int:
    try:
        path = confined_path(path)
        manifest = load_manifest(path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    errors: list[str] = []
    for row in manifest.get("files", []):
        if row.get("status") != "publish":
            continue
        artifact = ROOT / row["path"]
        if artifact.is_symlink() or not artifact.is_file():
            errors.append(f"missing published path: {row['path']}")
            continue
        size = artifact.stat().st_size
        digest = sha256_file(artifact)
        if size != row.get("bytes"):
            errors.append(f"byte count changed: {row['path']}")
        if digest != row.get("sha256"):
            errors.append(f"sha256 changed: {row['path']}")
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        print(f"check failed: {len(errors)} issue(s)", file=sys.stderr)
        return 1
    print("check passed: all published paths exist and match bytes/sha256")
    return 0


def stage_list(path: Path) -> int:
    try:
        path = confined_path(path)
        manifest = load_manifest(path)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    for row in manifest.get("files", []):
        if row.get("status") == "publish":
            sys.stdout.buffer.write(row["path"].encode("utf-8") + b"\0")
    return 0


def stats(manifest: dict[str, Any]) -> None:
    counts: dict[str, int] = {}
    bytes_by_status: dict[str, int] = {}
    for row in manifest["files"]:
        status = row["status"]
        counts[status] = counts.get(status, 0) + 1
        bytes_by_status[status] = bytes_by_status.get(status, 0) + int(row.get("bytes") or 0)
    print(f"files={len(manifest['files'])}")
    for status in sorted(counts):
        print(f"{status}: {counts[status]} files, {bytes_by_status[status]} bytes")
    missing = [root["path"] for root in manifest["candidate_roots"] if root["status"] == "missing"]
    if missing:
        print("missing candidate roots: " + ", ".join(missing))


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", metavar="MANIFEST", help="verify all published paths against a manifest")
    mode.add_argument("--stage-list", metavar="MANIFEST", help="print NUL-delimited published paths")
    parser.add_argument("--output", help="write manifest here (default: 02_实验/public_review_inventory_20261007.json)")
    parser.add_argument("--stats", action="store_true", help="print a classification count/byte summary")
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    if args.check:
        return check_manifest((ROOT / args.check).resolve())
    if args.stage_list:
        return stage_list((ROOT / args.stage_list).resolve())
    try:
        output = confined_path(ROOT / args.output) if args.output else ROOT / "02_实验/public_review_inventory_20261007.json"
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    manifest = build_manifest(output)
    write_manifest(output, manifest)
    try:
        shown_output = relpath(output)
    except ValueError:
        shown_output = output.as_posix()
    print(f"wrote {shown_output}")
    if args.stats:
        stats(manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
