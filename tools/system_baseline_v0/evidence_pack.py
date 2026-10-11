"""Create and verify a compressed, hash-indexed copy of new System Baseline runs."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import secrets
import tarfile
from typing import Any

from .runner import RUNS_DIR


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = ROOT / "02_实验/System_Baseline_v0/public_evidence"


def _digest(path: Path) -> str:
    value = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def _manifest(source: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(source.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"symlinks are not accepted in evidence input: {path}")
        if path.is_file():
            rows.append({"path": path.relative_to(source).as_posix(),
                         "size_bytes": path.stat().st_size,
                         "sha256": _digest(path)})
    if not rows:
        raise ValueError("evidence source directory is empty")
    return rows


def _source_index(source: Path) -> dict[str, Any]:
    runs = []
    baseline = None
    source_versions: dict[str, set[str]] = {}
    for result_path in sorted(source.glob("*/result.json")):
        result = json.loads(result_path.read_text(encoding="utf-8"))
        identity = result.get("source_identity", {})
        if identity.get("source_sha256"):
            hashes = identity["source_sha256"]
            baseline = baseline or identity.get("baseline_git_commit")
        else:
            case_path = result_path.parent / "case.json"
            case = json.loads(case_path.read_text(encoding="utf-8")) if case_path.is_file() else {}
            hashes = case.get("source_sha256", {})
            baseline = baseline or case.get("baseline_git_commit")
        if hashes:
            runs.append({"run_id": result_path.parent.name,
                         "baseline_git_commit": baseline,
                         "source_sha256": hashes})
            for path, digest in hashes.items():
                source_versions.setdefault(path, set()).add(digest)
    current_hashes = {path: sorted(digests) for path, digests in sorted(source_versions.items())}
    current_matches = {path: {digest: _digest(ROOT / path) == digest
                              for digest in digests}
                       for path, digests in current_hashes.items()
                       if (ROOT / path).is_file()}
    return {"baseline_git_commit": baseline,
            "shared_source_sha256": current_hashes,
            "current_worktree_matches_recorded": current_matches,
            "per_run": runs}


def pack(source: Path = RUNS_DIR, output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    source, output = source.resolve(), output.resolve()
    if not source.is_dir():
        raise FileNotFoundError(source)
    files = _manifest(source)
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    stem = f"system-baseline-runs-{stamp}-{secrets.token_hex(3)}"
    archive = output / f"{stem}.tar.gz"
    with tarfile.open(archive, "w:gz", compresslevel=9) as handle:
        for row in files:
            handle.add(source / row["path"], arcname=f"runs/{row['path']}", recursive=False)

    expected = {f"runs/{row['path']}": row for row in files}
    seen = set()
    with tarfile.open(archive, "r:gz") as handle:
        for member in handle:
            if not member.isfile() or member.name not in expected:
                raise ValueError(f"unexpected archive member: {member.name}")
            stream = handle.extractfile(member)
            if stream is None:
                raise ValueError(f"unreadable archive member: {member.name}")
            digest = sha256()
            size = 0
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
                size += len(block)
            record = expected[member.name]
            if size != record["size_bytes"] or digest.hexdigest() != record["sha256"]:
                raise ValueError(f"round-trip hash mismatch: {member.name}")
            seen.add(member.name)
    if seen != set(expected):
        raise ValueError("archive round-trip omitted one or more source artifacts")

    manifest = {"schema": "system-baseline-evidence-pack-v1",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "source_directory": str(source),
                "archive": archive.name,
                "archive_sha256": _digest(archive),
                "roundtrip_verified": True,
                "file_count": len(files),
                "uncompressed_bytes": sum(row["size_bytes"] for row in files),
                "source_hash_index": _source_index(source),
                "files": files}
    manifest_path = output / f"{stem}.manifest.json"
    with manifest_path.open("x", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return {"archive": str(archive), "manifest": str(manifest_path),
            "archive_sha256": manifest["archive_sha256"],
            "file_count": len(files), "uncompressed_bytes": manifest["uncompressed_bytes"],
            "roundtrip_verified": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=RUNS_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(pack(args.source, args.output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
