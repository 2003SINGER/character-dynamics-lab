import json
import sys

paths = sys.argv[1:]
if len(paths) != 3:
    raise SystemExit("expected deadline phone commitment traces")
traces = [json.load(open(p, encoding="utf-8")) for p in paths]
for frames in traces:
    if not frames or len({f["policy_seed"] for f in frames}) != 1:
        raise SystemExit("seed consistency failure")
    for f in frames:
        d = f["decision"]
        if d["gate"] and not isinstance(d["reasons"], list):
            raise SystemExit("gate reason failure")
deadline, phone, commitment = traces
if not any(f["world"].get("task_status") == "completed" for f in deadline):
    raise SystemExit("deadline completion missing")
if not any(f["attempted_action"] == "use_phone" and not f["validation"]["accepted"] for f in phone):
    raise SystemExit("phone rejection missing")
if not any(not f["observation"]["use_phone_in_AO"] for f in phone[1:]):
    raise SystemExit("phone constraint did not rebuild A^O")
statuses = [f["state"]["commitment_status"] for f in commitment]
for expected in ("active", "suspended", "active", "none"):
    if expected not in statuses:
        raise SystemExit("commitment transition missing: " + expected)
raise SystemExit(0)
