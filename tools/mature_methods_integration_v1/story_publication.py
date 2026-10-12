"""Package an explicitly allowlisted set of native story-process runs.

This small publisher is intentionally separate from the fixed S1-S4 archive
tool. It publishes only run directories supplied by the caller and verifies
the resulting tar against those exact local originals before returning.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import tarfile
from datetime import datetime, timezone
from typing import Any, Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNS_ROOT = PROJECT_ROOT / "02_实验/Mature_Methods_Integration_v1/runs"
DEFAULT_PUBLICATION_ROOT = PROJECT_ROOT / "02_实验/Mature_Methods_Integration_v1/public_evidence"
_EXCLUDED_PARTS = {"private", "_private", "auth", "authentication", "config",
                   "configuration", "db", "database", "__pycache__"}
_EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".sqlite", ".sqlite3", ".db", ".dump",
                      ".pem", ".key", ".p12", ".pfx", ".env"}
_DB_REFERENCE_NAMES = {"db-export-reference.json", "db-readback-summary.json",
                       "failure-db-export-reference.json"}
_SENSITIVE_KEYS = {"api_key", "access_token", "refresh_token", "client_secret",
                   "password", "private_key", "authorization", "database_url"}
_SECRET_PATTERNS = (
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{16,}"),
    re.compile(rb"(?i)\b(?:api[_-]?key|access[_-]?token|refresh[_-]?token|client[_-]?secret|password|database[_-]?url)\s*[:=]\s*[\"']?[^\s\"',}]{8,}"),
)
_STAMP_RE = re.compile(r"^\d{8}T\d{6}Z$")


def _sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_archive_path(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name and not path.is_absolute() and ".." not in path.parts
                and "" not in path.parts and path.as_posix() == name)


def _excluded_reason(path: Path, run_dir: Path) -> str | None:
    relative = path.relative_to(run_dir)
    if path.name.startswith("._"):
        return "AppleDouble metadata"
    if any(part.casefold() in _EXCLUDED_PARTS for part in relative.parts):
        return "private/auth/config/database/cache path"
    if path.suffix.casefold() in _EXCLUDED_SUFFIXES:
        return "credential, database, or bytecode file"
    return None


def _check_content(path: Path) -> None:
    data = path.read_bytes()
    if any(pattern.search(data) for pattern in _SECRET_PATTERNS):
        raise ValueError(f"credential-like material found in allowlisted run file: {path.name}")
    if path.suffix.casefold() == ".json":
        try:
            value = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return

        def visit(node: Any) -> None:
            if isinstance(node, dict):
                for key, child in node.items():
                    normalized = str(key).casefold().replace("-", "_")
                    if normalized in _SENSITIVE_KEYS and child not in (None, "", False):
                        raise ValueError(f"sensitive JSON field {key!r} in {path.name}")
                    visit(child)
            elif isinstance(node, list):
                for child in node:
                    visit(child)
        visit(value)


def _resolve_run_dirs(run_dirs: Iterable[str | Path], runs_root: Path) -> list[Path]:
    allowed_root = runs_root.resolve(strict=True)
    resolved = []
    seen = set()
    for supplied in run_dirs:
        candidate = Path(supplied)
        if candidate.is_symlink():
            raise ValueError(f"run-directory symlinks are not allowed: {candidate}")
        path = candidate.resolve(strict=True)
        if (path.parent != allowed_root or not path.is_dir()
                or not path.name.startswith("story-")):
            raise ValueError(f"each allowlisted run must be a direct story-* child of {allowed_root}: {candidate}")
        if path in seen:
            raise ValueError(f"duplicate run directory in explicit allowlist: {candidate}")
        seen.add(path)
        resolved.append(path)
    if not resolved:
        raise ValueError("at least one explicit --run-dir is required")
    return resolved


def _collect(run_dirs: list[Path], project_root: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]], list[dict[str, Any]]]:
    members = []
    excluded = []
    database_readbacks = []
    seen_names = set()
    for run_dir in run_dirs:
        for current, dirs, files in os.walk(run_dir, topdown=True, followlinks=False):
            current_path = Path(current)
            for dirname in list(dirs):
                directory = current_path / dirname
                if directory.is_symlink():
                    raise ValueError(f"symlink directory in allowlisted run: {directory}")
                reason = _excluded_reason(directory, run_dir)
                if reason:
                    excluded.append({"path": directory.relative_to(project_root).as_posix(), "reason": reason})
                    dirs.remove(dirname)
            for filename in files:
                path = current_path / filename
                if path.is_symlink():
                    raise ValueError(f"symlink file in allowlisted run: {path}")
                if path.name.casefold() in _DB_REFERENCE_NAMES:
                    try:
                        metadata = json.loads(path.read_text(encoding="utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        raise ValueError(f"invalid scoped DB reference metadata: {path.name}") from exc
                    database_readbacks.append({
                        "run_id": run_dir.name,
                        "reference_file": path.relative_to(project_root).as_posix(),
                        "bytes": path.stat().st_size, "sha256": _sha_file(path),
                        "exit_code": metadata.get("exit_code"),
                        "artifact_sha256": metadata.get("artifact_sha256") or metadata.get("export_artifact_sha256"),
                        "scene_id": metadata.get("scene_id"),
                        "event_count": metadata.get("event_count"),
                        "path_omitted": True,
                    })
                    excluded.append({"path": path.relative_to(project_root).as_posix(),
                                     "reason": "scoped DB reference metadata summarized; local artifact path omitted"})
                    continue
                reason = _excluded_reason(path, run_dir)
                if reason:
                    excluded.append({"path": path.relative_to(project_root).as_posix(), "reason": reason})
                    continue
                relative = path.relative_to(project_root).as_posix()
                if not _safe_archive_path(relative):
                    raise ValueError(f"unsafe archive member path: {relative}")
                if relative in seen_names:
                    raise ValueError(f"duplicate archive member path: {relative}")
                _check_content(path)
                seen_names.add(relative)
                members.append({"path": relative, "run_id": run_dir.name,
                                "bytes": path.stat().st_size, "sha256": _sha_file(path),
                                "_source": path})
    members.sort(key=lambda row: row["path"])
    excluded.sort(key=lambda row: row["path"])
    database_readbacks.sort(key=lambda row: (row["run_id"], row["reference_file"]))
    return members, excluded, database_readbacks


def _run_summary(run_dir: Path) -> dict[str, Any]:
    identity_path, summary_path = run_dir / "identity.json", run_dir / "summary.json"
    identity = json.loads(identity_path.read_text(encoding="utf-8")) if identity_path.is_file() else {}
    summary = json.loads(summary_path.read_text(encoding="utf-8")) if summary_path.is_file() else {}
    final = summary.get("final_story_process")
    decision = None
    if isinstance(final, dict):
        decision = {key: final.get(key) for key in ("controller_mode", "status", "selected_method",
                                                     "sealed_minute", "target_version")}
    return {"run_id": run_dir.name,
            "case_id": summary.get("case_id", identity.get("case_id")),
            "strategy": identity.get("strategy", identity.get("story_request_template", {}).get("strategy")),
            "run_status": summary.get("status"), "error_type": (summary.get("error") or {}).get("error_type"),
            "steps_recorded": summary.get("steps_recorded"), "controller_summary": decision}


def verify_archive(archive_path: Path, index: dict[str, Any], project_root: Path) -> dict[str, Any]:
    expected = {row["path"]: row for row in index["members"]}
    observed = {}
    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            if not _safe_archive_path(member.name) or not member.isfile():
                raise ValueError(f"unsafe or non-regular tar member: {member.name}")
            if member.name in observed:
                raise ValueError(f"duplicate tar member: {member.name}")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"could not read tar member: {member.name}")
            payload = stream.read()
            observed[member.name] = {"bytes": len(payload), "sha256": _sha_bytes(payload)}
    if set(observed) != set(expected):
        raise ValueError("tar member set does not exactly match the explicit run-file index")
    for name, row in expected.items():
        archived = observed[name]
        if archived["bytes"] != row["bytes"] or archived["sha256"] != row["sha256"]:
            raise ValueError(f"tar member size/hash differs from its index: {name}")
        original = project_root / name
        if not original.is_file() or original.is_symlink():
            raise ValueError(f"local original is missing or unsafe: {name}")
        if original.stat().st_size != row["bytes"] or _sha_file(original) != row["sha256"]:
            raise ValueError(f"local original changed during publication: {name}")
    return {"status": "VERIFIED", "member_count": len(observed),
            "total_bytes": sum(row["bytes"] for row in expected.values())}


def publish(run_dirs: Iterable[str | Path], *, runs_root: Path = DEFAULT_RUNS_ROOT,
            publication_root: Path = DEFAULT_PUBLICATION_ROOT,
            project_root: Path = PROJECT_ROOT, timestamp: str | None = None) -> dict[str, Any]:
    """Publish one exact set of native run directories without overwriting."""
    timestamp = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if not _STAMP_RE.fullmatch(timestamp):
        raise ValueError("timestamp must use UTC YYYYMMDDTHHMMSSZ form")
    runs = _resolve_run_dirs(run_dirs, runs_root)
    members, excluded, database_readbacks = _collect(runs, project_root.resolve(strict=True))
    if not members:
        raise ValueError("explicit run allowlist contains no publishable files")

    publication = publication_root / f"story-process-v1-{timestamp}"
    publication.mkdir(parents=True, exist_ok=False)
    archive_path = publication / "story-process-v1.tar.gz"
    index = {"schema": "story-process-publication-index-v1",
             "scope": "explicit story run-directory allowlist only",
             "run_directories": [path.name for path in runs],
             "runs": [_run_summary(path) for path in runs],
             "database_readbacks": database_readbacks,
             "members": [{key: value for key, value in row.items() if key != "_source"}
                         for row in members],
             "excluded": excluded,
             "member_count": len(members),
             "total_bytes": sum(row["bytes"] for row in members),
             "exclusions_policy": ["private/_private/auth/config/database paths", "raw DB exports",
                                   "DB reference paths summarized without local path",
                                   "credential/database/bytecode files", "AppleDouble and __pycache__"]}
    with tarfile.open(archive_path, "w:gz", compresslevel=6, format=tarfile.PAX_FORMAT) as archive:
        for row in members:
            archive.add(row["_source"], arcname=row["path"], recursive=False)
    verified = verify_archive(archive_path, index, project_root.resolve(strict=True))
    index["archive"] = {"name": archive_path.name, "bytes": archive_path.stat().st_size,
                        "sha256": _sha_file(archive_path), "verification": verified}
    index_path = publication / "index.json"
    summary_path = publication / "summary.md"
    index_path.write_text(json.dumps(index, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                          encoding="utf-8")
    lines = ["# Story-process native evidence publication", "",
             "This archive contains only the explicitly allowlisted run directories. It is an evidence bundle, not a claim of system completion or method advantage.",
             "", f"- Run directories: {len(runs)}", f"- Indexed files: {verified['member_count']}",
             f"- Raw bytes: {verified['total_bytes']:,}",
             f"- Archive SHA-256: `{index['archive']['sha256']}`", "",
             "| Run | Case | Strategy | Run status | Steps |", "|---|---|---|---|---:|"]
    for row in index["runs"]:
        lines.append(f"| {row['run_id']} | {row.get('case_id') or '—'} | {row.get('strategy') or '—'} | {row.get('run_status') or 'INCOMPLETE'} | {row.get('steps_recorded') if row.get('steps_recorded') is not None else '—'} |")
    lines += ["", "Per-member sizes and SHA-256 hashes, excluded paths, and archive verification are in `index.json`.",
              "The index and this summary are adjacent to, not embedded in, the tarball to avoid self-reference.", ""]
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return {"publication": str(publication), "archive": str(archive_path),
            "index": str(index_path), "summary": str(summary_path), **verified,
            "archive_sha256": index["archive"]["sha256"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", action="append", required=True,
                        help="one exact story-* child directory under the fixed runs root; repeat to add allowlisted runs")
    parser.add_argument("--timestamp", help="publication suffix in UTC YYYYMMDDTHHMMSSZ form")
    args = parser.parse_args(argv)
    result = publish(args.run_dir, timestamp=args.timestamp)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
