"""Cheap repository health radar; warnings do not fail the command."""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path

CODE_EXT = {".cpp", ".h", ".py"}
DEFAULT_SKIP = {".git", "outputs", "tmp", "__pycache__"}

def files_under(root: Path):
    for p in root.rglob("*"):
        if any(part in DEFAULT_SKIP for part in p.parts):
            continue
        try:
            if p.is_file():
                yield p
        except OSError as exc:
            print(f"WARN inaccessible path: {p} ({exc})")

def main() -> int:
    ap = argparse.ArgumentParser(); ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1]); ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args(); root = args.root.resolve(); files = list(files_under(root)); warnings = 0
    sized = sorted(((p.stat().st_size, p) for p in files if p.suffix.lower() in CODE_EXT), reverse=True)
    print("Largest code files:")
    for size, p in sized[:args.top]:
        print(f"  {size:>8}  {p.relative_to(root)}")
        if size > 50_000:
            print(f"WARN large code file: {p.relative_to(root)} ({size} bytes)"); warnings += 1
    todo = root / "00_研究设计" / "TODO.md"
    if todo.exists() and todo.stat().st_size > 27_000:
        print(f"WARN TODO.md is {todo.stat().st_size} bytes"); warnings += 1
    hashes: dict[str, list[Path]] = {}
    for p in files:
        if "90_原始材料" not in p.parts or p.suffix.lower() not in {".txt", ".md"}: continue
        digest = hashlib.sha256(p.read_bytes()).hexdigest(); hashes.setdefault(digest, []).append(p)
    for digest, paths in hashes.items():
        if len(paths) > 1:
            print("WARN duplicate content:"); [print(f"  {p.relative_to(root)}") for p in paths]; warnings += 1
    required = {"purpose", "git_revision"}
    for p in files:
        if p.name != "manifest.json": continue
        try: data = json.loads(p.read_text(encoding="utf-8"))
        except Exception: continue
        missing = sorted(required - set(data))
        if missing: print(f"WARN manifest missing {', '.join(missing)}: {p.relative_to(root)}"); warnings += 1
    print(f"Health check completed with {warnings} warning(s); no warning is a failure.")
    return 0

if __name__ == "__main__": raise SystemExit(main())
