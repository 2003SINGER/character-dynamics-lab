"""Independent read-only database and receipt audit of a saved native run."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[3]
DB = ROOT / "_local_data/native_platform_v0/evennia/nativep1/server/evennia.db3"


def audit(run_dir: Path) -> dict:
    data = json.loads((run_dir / "run.json").read_text())
    trace = data.get("native_trace", data.get("partial_trace"))
    if not trace:
        raise ValueError("run has no native trace")
    snapshot, events = trace["snapshot"], trace["events"]
    checks = {}
    checks["complete_sequence"] = [e["sequence"] for e in events] == list(range(1, len(events) + 1))
    checks["nondecreasing_event_time"] = all(a["minute"] <= b["minute"] for a, b in zip(events, events[1:]))
    checks["time_sealed"] = trace["sealed_through"] == snapshot["clock"]["now"]
    checks["frontier_matches"] = trace["ledger_frontier"] == len(events)
    checks["unique_events"] = len({e["event_id"] for e in events}) == len(events)
    settled = [e for e in events if e.get("settled") and e.get("accepted")]
    counts = {name: sum(e["event_type"] == name for e in settled) for name in
              ("GET_SETTLED", "DROP_SETTLED", "MEETING_WITNESS", "CLOUD_SEEDED", "CLOUD_DISSIPATED")}
    checks["no_repeat_pickup_delivery_witness"] = all(counts[n] <= 1 for n in
              ("GET_SETTLED", "DROP_SETTLED", "MEETING_WITNESS"))
    roles = data["scene"]["actors"]
    object_ids = {name: row["id"] for name, row in roles.items()}
    object_ids["shelter_kit"] = snapshot["items"]["shelter_kit"]["id"]
    connection = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    connection.execute("PRAGMA query_only=ON")
    rows = {}
    try:
        for name, ident in object_ids.items():
            row = connection.execute("SELECT id, db_key, db_location_id FROM objects_objectdb WHERE id=?", (ident,)).fetchone()
            if row is None:
                raise ValueError(f"missing database object {name}")
            rows[name] = {"id": row[0], "key": row[1], "location_id": row[2]}
    finally:
        connection.close()
    checks["actor_database_readback"] = all(rows[r]["location_id"] == snapshot["actors"][r]["room_id"] for r in ("A", "B", "player"))
    checks["item_database_readback"] = rows["shelter_kit"]["location_id"] == snapshot["items"]["shelter_kit"]["location_id"]
    checks["scene_identity"] = all(data["scene"]["scene_id"] in row["key"] for row in rows.values())
    if data["status"] == "COMPLETED":
        checks["native_goal_positions"] = all(rows[r]["location_id"] == snapshot["rooms"]["inn"] for r in ("A", "B", "shelter_kit"))
        checks["one_real_delivery_and_meeting"] = counts["DROP_SETTLED"] == counts["MEETING_WITNESS"] == 1
    result = {"run_id": data["run_id"], "audit": "parent_readonly_sqlite_and_native_ledger",
              "database_mode": "read-only/query-only", "checks": checks, "counts": counts,
              "database_objects": rows, "pass": all(checks.values())}
    target = run_dir / "parent-readback.json"
    with target.open("x") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_dir", type=Path)
    result = audit(parser.parse_args().run_dir)
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["pass"] else 2)
