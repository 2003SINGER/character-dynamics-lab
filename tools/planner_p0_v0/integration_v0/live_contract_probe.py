"""Small, non-overwriting live probe for mode/task/idempotency/cloud contracts.

The script talks only to the existing authenticated loopback RPC. It does not
start or stop the server. Do not run it without explicit coordination.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import secrets
import sys

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.native_platform_v0.p3.mcp_stdio import rpc_call

EVIDENCE = ROOT / "02_实验/Planner_P0_Integration_v0/live-contract-probes"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _unwrap(response: dict, key: str):
    return response.get(key, response)


def _snapshot(call_rpc, scene_id):
    return _unwrap(call_rpc("snapshot_p0_integration_v0", {"scene_id": scene_id}), "snapshot")


def _trace(call_rpc, scene_id):
    return _unwrap(call_rpc("get_p0_integration_trace_v0", {"scene_id": scene_id}), "trace")


def _prefix_check(prior: dict | None, current: dict, label: str, checks: list):
    if prior is not None:
        old = prior.get("events", [])
        now = current.get("events", [])
        if now[:len(old)] != old:
            raise AssertionError(f"ledger ceased to be append-only at {label}")
        checks.append({"check": "ledger_append_only", "at": label,
                       "prior_events": len(old), "current_events": len(now), "pass": True})


def _capture(call_rpc, scene_id, prior, label, checks, checkpoints):
    current = _trace(call_rpc, scene_id)
    _prefix_check(prior, current, label, checks)
    checkpoints.append({"label": label, "trace": current,
                        "snapshot": _snapshot(call_rpc, scene_id)})
    return current


def _step(call_rpc, scene_id, req, driver, action):
    return call_rpc("step_p0_integration_v0", {"scene_id": scene_id,
                    "request_id": req, "driver": driver, "action": action})


def run_probe(*, call_rpc=None, output_root: Path | None = None) -> dict:
    call_rpc = call_rpc or rpc_call
    output_root = output_root or EVIDENCE
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"contract-{stamp}-{secrets.token_hex(4)}"
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    source_paths = [Path(__file__), Path(__file__).with_name("native_world.py"),
                    Path(__file__).with_name("contract.py"),
                    ROOT / "tools/native_platform_v0/p3/control_service.py",
                    ROOT / "tools/native_platform_v0/p3/mcp_stdio.py"]
    config = {"schema": "planner-p0-live-contract-probe-v0", "run_id": run_id,
              "created_at_utc": datetime.now(timezone.utc).isoformat(),
              "scenes": ["conditional accept_task=false", "direct accept_task=false"],
              "actions": ["conditional offer refusal", "conditional dispatch ACL denial",
                          "direct author-forced task dispatch", "native GET", "idempotent replay",
                          "same request id with altered payload", "seed then wait to storm",
                          "dissipate after storm must not reverse weather"],
              "does_not_start_server": True}
    source_hashes = {str(p.relative_to(ROOT)): _sha(p) for p in source_paths}
    record = {"schema": config["schema"], "run_id": run_id, "status": "INCOMPLETE",
              "checks": [], "scenes": {}, "failures": []}
    (run_dir / "config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    (run_dir / "sourcehash.json").write_text(json.dumps(source_hashes, indent=2) + "\n", encoding="utf-8")

    def assert_check(condition, name, details=None):
        row = {"check": name, "pass": bool(condition), "details": details or {}}
        record["checks"].append(row)
        if not condition:
            raise AssertionError(f"{name} failed: {details or {}}")

    try:
        # Conditional fixture: A's fixed own-goal is incompatible, so the real offer declines.
        made = _unwrap(call_rpc("reset_p0_integration_v0", {
            "mode": "conditional", "seed": 0, "accept_task": False}), "scene")
        sid = made["scene_id"]
        scene_record = {"scene_id": sid, "mode": "conditional", "checkpoints": []}
        record["scenes"]["conditional"] = scene_record
        previous = _capture(call_rpc, sid, None, "conditional_created", record["checks"], scene_record["checkpoints"])
        offer = _step(call_rpc, sid, f"{run_id}-cond-offer", "author",
                      {"kind": "offer_task", "actor": "A", "task": "deliver_shelter"})
        after_offer = _capture(call_rpc, sid, previous, "conditional_offer", record["checks"], scene_record["checkpoints"])
        previous = after_offer
        assert_check(offer.get("code") == "TASK_REFUSED" and offer.get("settled") is True,
                     "conditional_offer_refused_with_receipt", {"code": offer.get("code"), "settled": offer.get("settled")})
        assert_check(after_offer["snapshot"].get("task") is None,
                     "refused_offer_does_not_bind_task")
        clock_before_acl = after_offer["snapshot"]["clock"]["now"]
        count_before_acl = len(after_offer["events"])
        denied = _step(call_rpc, sid, f"{run_id}-cond-dispatch-denied", "author",
                       {"kind": "dispatch_task", "actor": "A", "task": "deliver_shelter"})
        after_acl = _capture(call_rpc, sid, previous, "conditional_dispatch_acl", record["checks"], scene_record["checkpoints"])
        previous = after_acl
        assert_check(denied.get("code") == "ACL_DENIED" and
                     after_acl["snapshot"]["clock"]["now"] == clock_before_acl,
                     "conditional_dispatch_denied_without_clock_tick",
                     {"code": denied.get("code"), "clock_before": clock_before_acl,
                      "clock_after": after_acl["snapshot"]["clock"]["now"]})
        assert_check(len(after_acl["events"]) == count_before_acl + 1,
                     "acl_denial_has_only_result_event",
                     {"prior_events": count_before_acl, "after_events": len(after_acl["events"])})

        # Direct fixture: force-bind explicitly as author, then prove a native item transition.
        made = _unwrap(call_rpc("reset_p0_integration_v0", {
            "mode": "direct", "seed": 0, "accept_task": False}), "scene")
        sid = made["scene_id"]
        scene_record = {"scene_id": sid, "mode": "direct", "checkpoints": []}
        record["scenes"]["direct"] = scene_record
        previous = _capture(call_rpc, sid, None, "direct_created", record["checks"], scene_record["checkpoints"])
        dispatch_req = f"{run_id}-direct-dispatch"
        dispatch_action = {"kind": "dispatch_task", "actor": "A", "task": "deliver_shelter"}
        dispatched = _step(call_rpc, sid, dispatch_req, "author", dispatch_action)
        after_dispatch = _capture(call_rpc, sid, previous, "direct_dispatch", record["checks"], scene_record["checkpoints"])
        previous = after_dispatch
        task = after_dispatch["snapshot"].get("task") or {}
        assert_check(dispatched.get("settled") is True and task.get("status") == "active" and
                     task.get("decision_source") == "author_forced_dispatch",
                     "direct_dispatch_is_author_forced_not_consent",
                     {"response": {k: dispatched.get(k) for k in ("accepted", "settled", "code")},
                      "task": task})

        get_action = {"kind": "get", "actor": "A", "item": "shelter_kit"}
        get_req = f"{run_id}-direct-get"
        get_result = _step(call_rpc, sid, get_req, "direct_driver", get_action)
        after_get = _capture(call_rpc, sid, previous, "direct_native_get", record["checks"], scene_record["checkpoints"])
        previous = after_get
        assert_check(get_result.get("settled") is True and
                     after_get["snapshot"]["items"]["shelter_kit"]["holder_role"] == "A" and
                     (after_get["snapshot"].get("task") or {}).get("held") is True,
                     "native_get_transition_and_receipt", {"code": get_result.get("code"), "receipt_id": get_result.get("receipt_id")})

        before_replay = after_get["snapshot"]
        replay = _step(call_rpc, sid, get_req, "direct_driver", get_action)
        after_replay = _capture(call_rpc, sid, previous, "same_payload_replay", record["checks"], scene_record["checkpoints"])
        previous = after_replay
        assert_check(replay == get_result and after_replay["snapshot"]["clock"] == before_replay["clock"] and
                     after_replay["events"] == after_get["events"],
                     "same_request_replay_is_noop")

        mismatch_error = None
        try:
            _step(call_rpc, sid, get_req, "direct_driver", {"kind": "wait", "actor": "A"})
        except Exception as exc:
            mismatch_error = type(exc).__name__
        after_mismatch = _capture(call_rpc, sid, previous, "different_payload_same_id", record["checks"], scene_record["checkpoints"])
        previous = after_mismatch
        assert_check(mismatch_error is not None and after_mismatch["snapshot"]["clock"] == before_replay["clock"] and
                     after_mismatch["events"] == after_replay["events"],
                     "different_payload_same_id_rejected_without_mutation", {"error_type": mismatch_error})

        seeded = _step(call_rpc, sid, f"{run_id}-cloud-seed", "author", {"kind": "cloud_seed"})
        after_seed = _capture(call_rpc, sid, previous, "cloud_seeded", record["checks"], scene_record["checkpoints"])
        previous = after_seed
        assert_check(seeded.get("settled") is True and after_seed["snapshot"]["weather"] == "clear" and
                     after_seed["snapshot"]["pending_cloud"] is not None,
                     "seed_creates_pending_process_not_immediate_storm")
        for i in range(2):
            waited = _step(call_rpc, sid, f"{run_id}-storm-wait-{i}", "direct_driver",
                           {"kind": "wait", "actor": "A"})
            next_trace = _capture(call_rpc, sid, previous, f"storm_wait_{i}", record["checks"], scene_record["checkpoints"])
            assert_check(waited.get("settled") is True, f"storm_wait_{i}_native_settled")
            previous = next_trace
        assert_check(previous["snapshot"]["weather"] == "storm" and
                     previous["snapshot"]["pending_cloud"] is None,
                     "server_clock_triggered_storm")
        mutation = call_rpc("inject_p0_integration_mutation_v0", {
            "scene_id": sid, "request_id": f"{run_id}-dissipate-after-storm",
            "kind": "dissipate_cloud"})
        after_dissipate = _capture(call_rpc, sid, previous, "dissipate_after_storm", record["checks"], scene_record["checkpoints"])
        assert_check(mutation.get("settled") is False and after_dissipate["snapshot"]["weather"] == "storm",
                     "dissipation_cannot_reverse_settled_storm",
                     {"mutation_code": mutation.get("code"), "weather": after_dissipate["snapshot"]["weather"]})
        record["status"] = "PASS"
    except Exception as exc:
        record["status"] = "FAIL"
        record["failure"] = {"type": type(exc).__name__, "message": str(exc)[:1600]}
    finally:
        record["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        (run_dir / "probe.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        (run_dir / "run.json").write_text(json.dumps({"run_id": run_id, "status": record["status"],
            "probe": "probe.json", "config": "config.json", "sourcehash": "sourcehash.json",
            "checks_passed": sum(bool(x.get("pass")) for x in record["checks"]),
            "checks_total": len(record["checks"]), "failure": record.get("failure")},
            ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"run_id": run_id, "run_dir": str(run_dir), "status": record["status"],
            "checks_passed": sum(bool(x.get("pass")) for x in record["checks"]),
            "checks_total": len(record["checks"]), "failure": record.get("failure")}


if __name__ == "__main__":
    result = run_probe()
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
