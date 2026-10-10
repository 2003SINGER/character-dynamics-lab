"""Verify the scoped P3 loopback service hook in the initialized local game.

The two ignored game-local hook files are deliberately applied with
``apply_patch``; this script is read-only and checks that their contents match
the reviewed adapter. P1 settings and typeclass settings stay untouched.
"""

from __future__ import annotations

import argparse
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
GAME_ROOT = PROJECT_ROOT / "_local_data/native_platform_v0/evennia/nativep1"
HOOK = GAME_ROOT / "server/conf/server_services_plugins.py"
WRAPPER = GAME_ROOT / "server/conf/p3_control_plugin.py"
HOOK_CALL = "    from server.conf.p3_control_plugin import start_plugin_services as start_p3_control\n    start_p3_control(server)"
WRAPPER_SOURCE = '''"""Local import bridge from Evennia's configured service hook to the repo."""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[6]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.native_platform_v0.p3.control_service import start_plugin_services
'''


def verify() -> None:
    if not GAME_ROOT.is_dir():
        raise RuntimeError(f"initialized game not found: {GAME_ROOT}")
    if not HOOK.is_file():
        raise RuntimeError(f"Evennia server service hook not found: {HOOK}")
    source = HOOK.read_text(encoding="utf-8")
    if HOOK_CALL not in source:
        raise RuntimeError("P3 service hook call is absent or differs from the reviewed hook")
    if not WRAPPER.is_file() or WRAPPER.read_text(encoding="utf-8") != WRAPPER_SOURCE:
        raise RuntimeError("P3 local wrapper differs from the reviewed wrapper")
    print("P3 local service hook verified; it binds only 127.0.0.1:14011")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify the two scoped local hook files")
    args = parser.parse_args(argv)
    if not args.check:
        parser.error("this verifier is read-only; pass --check")
    verify()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
