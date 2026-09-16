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
mid = [f for f in deadline if any(e["id"] == "task-deadline" for e in f["world_events"])]
if not mid or not any(f["running_action_after"] and f["running_action_after"]["action"] == "study_focused" and 0 < f["running_action_after"]["elapsed"] < f["running_action_after"]["planned"] for f in mid):
    raise SystemExit("deadline in-action boundary/progress missing")
if not any(f["world"].get("task_status") == "completed" for f in deadline):
    raise SystemExit("deadline completion missing")
if not any(f["attempted_action"] == "use_phone" and f["decision_mode"] == "scripted" and not f["validation"]["accepted"] and f["validation"]["rejection_reason"] == "target_unusable" for f in phone):
    raise SystemExit("phone rejection missing")
if not any(not f["observation"]["use_phone_in_AO"] for f in phone[1:]):
    raise SystemExit("phone constraint did not rebuild A^O")
statuses = [f["state"]["commitment_status"] for f in commitment]
compressed = [s for i, s in enumerate(statuses) if i == 0 or s != statuses[i - 1]]
if compressed != ["active", "suspended", "active", "none"]:
    raise SystemExit("commitment sequence mismatch: " + repr(statuses))
if any(commitment[i]["timestamp"] >= commitment[i + 1]["timestamp"] for i in range(len(commitment) - 1)):
    raise SystemExit("commitment time is not monotonic")
raise SystemExit(0)
