"""Read-only exporter for explicitly allowlisted native P3 Evennia scenes.

Run with the project's isolated Evennia Python. The exporter starts a fresh
Django process, reads the initialized game's persisted ORM state, and writes
only generated scene objects and their bounded P3/social attributes.
"""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import date, datetime, time, timezone
import json
import os
from pathlib import Path
import re
import secrets
import sys
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]
GAME_ROOT = PROJECT_ROOT / "_local_data/native_platform_v0/evennia/nativep1"
VENV_PYTHON = PROJECT_ROOT / "_local_data/native_platform_v0/evennia/venv/bin/python"
RUNS_DIR = PROJECT_ROOT / "02_实验/Native_Platform_P3_v0/runs"
C0_RUNS_DIR = PROJECT_ROOT / "02_实验/Native_Platform_P3_C0_v0/runs"
C1A_RUNS_DIR = PROJECT_ROOT / "02_实验/Native_Platform_P3_C1a_v0/runs"
P4_RUNS_DIR = PROJECT_ROOT / "02_实验/Native_Platform_P4_0_v0/runs"
EXPORTED_CATEGORIES = {"native_p3", "native_social"}
SENSITIVE_KEY_PARTS = (
    "account", "password", "passwd", "session", "secret", "hmac", "credential",
    "settings", "token",
)


def _is_sensitive_key(key: Any) -> bool:
    lowered = str(key).casefold()
    return any(part in lowered for part in SENSITIVE_KEY_PARTS)


def json_safe(value: Any) -> Any:
    """Convert ordinary Evennia attribute data to JSON without object reprs."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): json_safe(item) for key, item in value.items() if not _is_sensitive_key(key)}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [json_safe(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return [json_safe(item) for item in sorted(value, key=lambda item: str(item))]
    # Evennia ObjectDB values can appear inside a pickled Attribute. Export a
    # compact reference only; never call repr() on an arbitrary model object.
    object_id = getattr(value, "id", None)
    if object_id is not None and value.__class__.__module__.startswith("evennia"):
        return {
            "object_id": int(object_id),
            "dbref": str(getattr(value, "dbref", f"#{object_id}")),
            "key": str(getattr(value, "key", "")),
        }
    return {"unsupported_value_type": f"{value.__class__.__module__}.{value.__class__.__name__}"}


def _scene_queryset(ObjectDB, scene_id: str):
    # `get_by_attribute` constrains the owner model, key, category, and exact
    # pickled value in Django's DB query. No global object/account export occurs.
    return ObjectDB.objects.get_by_attribute(
        key="p3_scene_id", category="native_p3", value=scene_id,
    ).distinct().order_by("id")


def _persisted_attributes(obj) -> dict[str, dict[str, Any]]:
    """Read allowed categories through the ORM relation, bypassing AttributeHandler caches."""
    result: dict[str, dict[str, Any]] = {category: {} for category in EXPORTED_CATEGORIES}
    rows = obj.db_attributes.filter(
        db_model="objectdb", db_attrtype__isnull=True,
        db_category__in=EXPORTED_CATEGORIES,
    ).order_by("db_category", "db_key", "id")
    for row in rows:
        key = str(row.db_key)
        if _is_sensitive_key(key):
            continue
        result[str(row.db_category)][key] = json_safe(row.value)
    return {category: values for category, values in result.items() if values}


def _object_row(obj, attributes: dict[str, dict[str, Any]], scene_object_ids: set[int]) -> dict[str, Any]:
    room_id = getattr(obj, "db_location_id", None)
    room_in_scene = room_id in scene_object_ids if room_id is not None else False
    destination_id = getattr(obj, "db_destination_id", None)
    return {
        "id": int(obj.id),
        "dbref": str(obj.dbref),
        "key": str(obj.db_key),
        "typeclass_path": str(obj.db_typeclass_path),
        "location": None if room_id is None else {
            "id": int(room_id), "dbref": f"#{room_id}", "in_allowlisted_scene": room_in_scene,
        },
        "exit_destination": None if destination_id is None else {
            "id": int(destination_id), "dbref": f"#{destination_id}",
            "in_allowlisted_scene": destination_id in scene_object_ids,
        },
        "attributes": attributes,
    }


def collect_scenes(scene_ids: list[str]) -> dict[str, Any]:
    """Query persisted Evennia state for the exact requested scene IDs."""
    if not GAME_ROOT.is_dir():
        raise RuntimeError(f"initialized Evennia game directory not found: {GAME_ROOT}")
    if not (GAME_ROOT / "server/evennia.db3").is_file():
        raise RuntimeError(f"initialized Evennia database not found: {GAME_ROOT / 'server/evennia.db3'}")

    os.chdir(GAME_ROOT)
    sys.path.insert(0, str(GAME_ROOT))
    os.environ["DJANGO_SETTINGS_MODULE"] = "server.conf.settings"
    import django
    django.setup()

    from django.db import connection
    from evennia.objects.models import ObjectDB

    if connection.vendor != "sqlite":
        raise RuntimeError(f"read-only guard supports the initialized SQLite game DB; got {connection.vendor}")
    connection.ensure_connection()
    # SQLite enforces read-only SQL for this exporter connection after setup.
    with connection.cursor() as cursor:
        cursor.execute("PRAGMA query_only = ON")

    exported = []
    for scene_id in scene_ids:
        objects = list(_scene_queryset(ObjectDB, scene_id))
        exact_objects = []
        for obj in objects:
            marker = obj.db_attributes.filter(
                db_model="objectdb", db_attrtype__isnull=True,
                db_key="p3_scene_id", db_category="native_p3",
            ).first()
            if marker is not None and marker.value == scene_id:
                exact_objects.append(obj)
        if not exact_objects:
            raise ValueError(f"no persisted generated objects found for explicit P3 scene ID {scene_id!r}")

        object_ids = {int(obj.id) for obj in exact_objects}
        rows = []
        for obj in exact_objects:
            attrs = _persisted_attributes(obj)
            rows.append(_object_row(obj, attrs, object_ids))
        exported.append({"scene_id": scene_id, "objects": rows})

    return {
        "schema": "native-p3-db-evidence-v1",
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "source": "initialized Evennia Django ORM; SQLite query_only enabled",
        "selection": {"mode": "explicit_scene_id_allowlist", "scene_ids": list(scene_ids)},
        "included_categories": sorted(EXPORTED_CATEGORIES),
        "sensitive_fields": "account/session/password/settings/credential/token/HMAC-like keys omitted",
        "logs": "full persisted lists retained; no tail truncation",
        "scenes": exported,
    }


def _validate_scene_ids(values: list[str]) -> list[str]:
    if not values:
        raise ValueError("at least one --scene-id is required")
    if len(set(values)) != len(values):
        raise ValueError("duplicate --scene-id values are not allowed")
    for value in values:
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", value):
            raise ValueError(f"invalid scene ID {value!r}; use an exact safe scene ID, not a path or wildcard")
    return values


def write_unique_export(document: dict[str, Any], runs_dir: Path = RUNS_DIR) -> Path:
    runs_dir.mkdir(parents=True, exist_ok=True)
    scene_token = "-".join(document["selection"]["scene_ids"])
    if len(scene_token) > 100:
        scene_token = f"{len(document['selection']['scene_ids'])}-scenes"
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for _ in range(8):
        output = runs_dir / f"p3-db-evidence-{scene_token}-{timestamp}-{secrets.token_hex(3)}.json"
        try:
            with output.open("x", encoding="utf-8") as handle:
                json.dump(document, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            return output
        except FileExistsError:
            continue
    raise FileExistsError("could not allocate a fresh evidence filename after eight attempts")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scene-id", action="append", required=True,
        help="exact P3 scene ID to export; repeat for an explicit allowlist",
    )
    parser.add_argument(
        "--c0", action="store_true",
        help="write the export under the separate Native_Platform_P3_C0_v0/runs directory",
    )
    parser.add_argument(
        "--c1a", action="store_true",
        help="write the export under the separate Native_Platform_P3_C1a_v0/runs directory",
    )
    parser.add_argument(
        "--p4", action="store_true",
        help="write the export under the separate Native_Platform_P4_0_v0/runs directory",
    )
    args = parser.parse_args(argv)
    try:
        if sum((args.c0, args.c1a, args.p4)) > 1:
            raise ValueError("--c0, --c1a, and --p4 are mutually exclusive")
        scene_ids = _validate_scene_ids(args.scene_id)
        document = collect_scenes(scene_ids)
        output_dir = (P4_RUNS_DIR if args.p4 else C1A_RUNS_DIR if args.c1a
                      else C0_RUNS_DIR if args.c0 else RUNS_DIR)
        output = write_unique_export(document, output_dir)
    except Exception as err:
        parser.error(str(err))
    print(json.dumps({"status": "EXPORTED", "path": str(output), "scene_ids": scene_ids,
                      "object_count": sum(len(scene["objects"]) for scene in document["scenes"])}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
