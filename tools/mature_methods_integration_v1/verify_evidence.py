"""Verify a Mature-Methods evidence archive against its index and source files."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import tarfile
from typing import Any
from pathlib import PurePosixPath


ROOT = Path(__file__).resolve().parents[2]


def digest(stream) -> str:
    value = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        value.update(block)
    return value.hexdigest()


def verify(publication: Path, *, check_originals: bool = False) -> dict[str, Any]:
    publication = publication.resolve()
    index_path = publication / "index.json"
    archive = publication / "mature-methods-s1-s4-evidence.tar.gz"
    summary_path = publication / "summary.md"
    sidecar = publication / "archive.sha256"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    errors = []
    sidecar_fields = sidecar.read_text(encoding="utf-8").split()
    if len(sidecar_fields) != 2 or sidecar_fields[1] != archive.name:
        errors.append("archive.sha256 must contain exactly the archive digest and filename")
        expected_archive_hash = sidecar_fields[0] if sidecar_fields else ""
    else:
        expected_archive_hash = sidecar_fields[0]
    with archive.open("rb") as stream:
        archive_hash = digest(stream)
    if archive_hash != expected_archive_hash:
        errors.append("archive SHA-256 does not match archive.sha256")
    indexed = {row["path"]: row for row in index["archive_members"]}
    if len(indexed) != len(index.get("archive_members", [])):
        errors.append("index contains duplicate archive member paths")
    with tarfile.open(archive, "r:gz") as tar:
        tar_members = tar.getmembers()
        members = {member.name: member for member in tar_members if member.isfile()}
        if len(members) != len(tar_members):
            errors.append("archive contains non-file or duplicate members")
        for name in members:
            if (name.startswith("/") or "../" in name or "/._" in name
                    or "/__pycache__/" in name or name.endswith((".pyc", ".pyo"))
                    or "/_private/" in name):
                errors.append(f"forbidden archive member: {name}")
        missing = sorted(set(indexed) - set(members))
        if missing:
            errors.append(f"{len(missing)} indexed members are missing from archive")
        expected_prefix = ("02_实验", "Mature_Methods_Integration_v1", "runs")

        def embedded_publication_file(name: str, basename: str) -> bool:
            member_path = PurePosixPath(name)
            return (member_path.name == basename and len(member_path.parts) == 5
                    and member_path.parts[:3] == expected_prefix
                    and re.fullmatch(r"publication-final-r2-\d{8}T\d{6}Z", member_path.parts[3]) is not None)

        embedded_indexes = [name for name in members if embedded_publication_file(name, "index.json")]
        embedded_summaries = [name for name in members if embedded_publication_file(name, "summary.md")]
        embedded_dirs = {PurePosixPath(name).parts[3]
                         for name in embedded_indexes + embedded_summaries}
        if len(embedded_dirs) != 1 or len(embedded_indexes) != 1 or len(embedded_summaries) != 1:
            errors.append("archive must contain exactly one r2 publication index and summary pair")
        else:
            embedded_index, embedded_summary = embedded_indexes[0], embedded_summaries[0]
            if PurePosixPath(embedded_index).parent != PurePosixPath(embedded_summary).parent:
                errors.append("embedded index and summary are not siblings")
            for name, external in ((embedded_index, index_path), (embedded_summary, summary_path)):
                stream = tar.extractfile(members[name])
                if stream is None or stream.read() != external.read_bytes():
                    errors.append(f"embedded publication file differs from relocated external file: {name}")
            allowed_extras = {embedded_index, embedded_summary}
            extra_raw = sorted(set(members) - set(indexed) - allowed_extras)
            if extra_raw:
                errors.append(f"unexpected non-indexed archive members: {extra_raw[:5]}")
        for name, row in indexed.items():
            member = members.get(name)
            if member is None:
                continue
            archive_stream = tar.extractfile(member)
            if archive_stream is None or digest(archive_stream) != row["sha256"]:
                errors.append(f"archive member hash mismatch: {name}")
                continue
            if member.size != row.get("bytes"):
                errors.append(f"archive member size mismatch: {name}")
            if check_originals:
                original = ROOT / name
                if not original.is_file() or original.stat().st_size != row["bytes"]:
                    errors.append(f"original file missing or size changed: {name}")
                    continue
                with original.open("rb") as stream:
                    original_hash = digest(stream)
                if original_hash != row["sha256"]:
                    errors.append(f"original file hash mismatch: {name}")
    return {"publication": str(publication), "indexed_members": len(indexed),
            "archive_sha256": expected_archive_hash, "errors": errors,
            "check_originals": check_originals,
            "status": "VERIFIED" if not errors else "FAILED"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("publication", type=Path)
    parser.add_argument("--check-originals", action="store_true",
                        help="also compare each archived member with its original path under this repository")
    args = parser.parse_args()
    result = verify(args.publication, check_originals=args.check_originals)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "VERIFIED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
