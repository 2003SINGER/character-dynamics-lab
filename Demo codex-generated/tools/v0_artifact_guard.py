"""Verify that the published V0 diagnostic artifacts remain byte-for-byte frozen."""
import subprocess, sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
prefix = Path("Demo codex-generated/demo/living_dynamics_v0/batch_48h_v0")
paths = subprocess.check_output(["git", "-C", str(root), "ls-tree", "-r", "--name-only", "d262c88", str(prefix)], text=True).splitlines()
for rel in paths:
    current = root / rel
    expected = subprocess.check_output(["git", "-C", str(root), "show", f"d262c88:{rel}"])
    if not current.exists() or current.read_bytes() != expected:
        raise SystemExit(f"V0 artifact changed: {rel}")
print(f"v0 artifact guard: PASS ({len(paths)} files)")
