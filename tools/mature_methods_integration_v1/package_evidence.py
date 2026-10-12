"""Build a path-preserving, hash-indexed S1-S4 evidence archive.

This post-run packager reads only the six explicitly named run directories and
never edits native run outputs.  Its publication directory lives beneath the
ignored runs/ tree.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tarfile


ROOT = Path(__file__).resolve().parents[2]
RUNS = ROOT / "02_实验/Mature_Methods_Integration_v1/runs"
PUBLICATION = RUNS / "publication-final-r2-20261012T085500Z"
ARCHIVE = PUBLICATION / "mature-methods-s1-s4-evidence.tar.gz"
INDEX = PUBLICATION / "index.json"
SUMMARY = PUBLICATION / "summary.md"
LIFECYCLE_LOGS = (
    ROOT / "outputs/native_platform_p1p2_v0/p1_evennia_20261010/runs/mature-methods-v1-s1-reload-stop-20261012T000000Z/stop.log",
    ROOT / "outputs/native_platform_p1p2_v0/p1_evennia_20261010/runs/mature-methods-v1-s1-reload-start-20261012T000000Z/start.log",
)
RUN_NAMES = (
    "S1-result-only-reject-20261012T075826Z-a3d5b6",
    "S1-result-only-reject-continuation-20261012T080559Z-68e191",
    "S1-result-only-reject-minute17-continuation-20261012T083347Z-cac6c8",
    "S2-edit-reselect-accept-20261012T083537Z-81bfb8",
    "S3-player-get-drop-recovery-reject-20261012T083620Z-e1b128",
    "S4-no-permission-safety-negative-20261012T083657Z-820e5d",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def result(path: Path):
    return read(path / "result.json")


def main() -> None:
    if PUBLICATION.exists():
        raise FileExistsError(f"refusing to overwrite {PUBLICATION}")
    run_dirs = [RUNS / name for name in RUN_NAMES]
    missing = [str(path) for path in run_dirs if not path.is_dir()]
    missing += [str(path) for path in LIFECYCLE_LOGS if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"required evidence directories missing: {missing}")

    s1_pair = run_dirs[0]
    s1_base = result(s1_pair / "baseline")
    s1_method = result(run_dirs[2] / "mature_methods")
    s2_pair, s3_pair, s4_pair = run_dirs[3:]
    s2_method = result(s2_pair / "mature_methods")
    s3_method = result(s3_pair / "mature_methods")
    s4_method = result(s4_pair / "mature_methods")

    members = []
    for run_dir in run_dirs:
        members.extend(path for path in sorted(run_dir.rglob("*")) if path.is_file())
    members.extend(LIFECYCLE_LOGS)
    rows = []
    for path in members:
        rel = path.relative_to(ROOT).as_posix()
        parts = path.parts
        if (path.name.startswith("._") or "__pycache__" in parts
                or path.suffix in {".pyc", ".pyo"}
                or any(part.lower() in {"private", "_private"} for part in parts)):
            raise ValueError(f"unexpected metadata/private file in allowlisted evidence: {rel}")
        rows.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256(path)})

    lifecycle = {
        "same_existing_evennia_database_and_ports": True,
        "stop_run_id": "mature-methods-v1-s1-reload-stop-20261012T000000Z",
        "start_run_id": "mature-methods-v1-s1-reload-start-20261012T000000Z",
        "health_before_after": "READY (recorded in orchestration status)",
        "raw_lifecycle_logs_included": [path.relative_to(ROOT).as_posix() for path in LIFECYCLE_LOGS],
        "note": "The original stop/start command outputs are included and hashed; READY health is recorded in orchestration status.",
    }
    s2_edit = None
    trace = read(s2_pair / "mature_methods/final-native-trace.json")
    for event in trace.get("ledger", []):
        args = event.get("typed_args", {})
        if event.get("event_type") == "P5_AUTHOR_EDIT_ATTEMPT":
            s2_edit = args.get("result")
            break

    s3_availability = []
    for path in sorted((s3_pair / "mature_methods").glob("high-level-plan-minute-*.json")):
        plan = read(path)
        for obligation in plan.get("obligations", []):
            if obligation.get("constraint_id") == "courier-delivery":
                availability = obligation.get("item_availability")
                if availability:
                    s3_availability.append({"minute": int(path.stem.rsplit("-", 1)[1]),
                                            "status": availability.get("status"),
                                            "location_id": availability.get("native_location_id")})

    cases = [
        {"case": "S1-result-only-reject", "status": "BOUNDED_CLOSED_LOOP_COMPLETE_WITH_TWO_RUNNER_FAILURES_AND_RESUMED_MATURE_ARM",
         "baseline_scene": s1_base["scene_id"], "mature_scene": s1_method["scene_id"],
         "baseline_hard": s1_base["final_verdicts"]["hard_status"],
         "mature_hard": s1_method["final_verdicts"]["hard_status"],
         "mature_route_receipt": s1_method["native_opportunity_attempts"][0]["typed_args"]["settlement"]["receipt_id"],
         "mature_root_calls": 5,
         "mature_root_wall_seconds": 0.008844292955472066,
         "mature_p5_snapshot_calls": 26,
         "mature_advance_calls": 24,
         "successful_method_work_aggregate": {
             "segments": [
                 {"run": "S1-result-only-reject-continuation-20261012T080559Z-68e191", "from_minute": 0, "through_minute": 17, "gtp_root_calls": 4, "gtp_root_wall_seconds": 0.007338708965107799, "p5_snapshot_calls": 18, "p5_snapshot_wall_seconds": 0.15371712192427367, "sealed_advance_calls": 17, "sealed_advance_wall_seconds": 0.001074083149433136},
                 {"run": "S1-result-only-reject-minute17-continuation-20261012T083347Z-cac6c8", "from_minute": 17, "through_minute": 24, "gtp_root_calls": 1, "gtp_root_wall_seconds": 0.0015055839903652668, "p5_snapshot_calls": 8, "p5_snapshot_wall_seconds": 0.14524374983739108, "sealed_advance_calls": 7, "sealed_advance_wall_seconds": 0.00048208393855020404},
             ],
             "valid_native_call_totals": {"gtp_root_calls": 5, "p5_snapshot_calls": 26, "sealed_advance_calls": 24},
             "all_attempts_including_initial_wrong_interpreter": {"gtp_root_calls": 6, "p5_snapshot_calls": 27, "sealed_advance_calls": 24},
             "checkpoint_minute_17_is_counted_in_both_segments": True,
             "initial_wrong_interpreter_attempt": "GTPyhop import/preflight failure; retained separately in original S1 pair artifacts",
         },
         "performance_comparison_valid": False,
         "limitations": ["initial system-interpreter attempt failed GTPyhop preflight", "first venv continuation stopped at valid existing_path NO_OP classification", "same scene resumed only after minute17 checkpoint validation", "baseline was not replayed"]},
        {"case": "S2-edit-reselect-accept", "status": "NATIVE_PERMISSION_EDIT_UNSUPPORTED_RESELECTION_NOT_EXERCISED",
         "baseline_scene": result(s2_pair / "baseline")["scene_id"], "mature_scene": s2_method["scene_id"],
         "edit_result": s2_edit, "active_bundle_version": s2_method["final_verdicts"]["bundle_version"],
         "mature_route_attempts": [a.get("typed_args", {}).get("intervention", {}).get("opportunity_id") for a in s2_method.get("native_opportunity_attempts", [])],
         "mature_root_calls": s2_method["costs"]["gtp_root_plan"]["calls"],
         "mature_root_wall_seconds": s2_method["costs"]["gtp_root_plan"]["wall_seconds"],
         "mature_p5_snapshot_calls": s2_method["costs"]["p5_snapshot_pure_plan"]["calls"],
         "mature_advance_calls": s2_method["costs"]["sealed_advance"]["calls"],
         "limitations": ["the runtime rejected permission-changing edit at minute1 with PERMISSION_ESCALATION", "active version stayed 1; side route remained legal and was opened", "no stale-candidate rejection or main-route reselection occurred"]},
        {"case": "S3-player-get-drop-recovery-reject", "status": "NATIVE_PAIR_COMPLETE_AVAILABILITY_CHANGE_OBSERVED",
         "baseline_scene": result(s3_pair / "baseline")["scene_id"], "mature_scene": s3_method["scene_id"],
         "courier_availability_checkpoints": s3_availability,
         "mature_native_opportunity_attempts": len(s3_method.get("native_opportunity_attempts", [])),
         "mature_root_calls": s3_method["costs"]["gtp_root_plan"]["calls"],
         "mature_root_wall_seconds": s3_method["costs"]["gtp_root_plan"]["wall_seconds"],
         "mature_p5_snapshot_calls": s3_method["costs"]["p5_snapshot_pure_plan"]["calls"],
         "mature_advance_calls": s3_method["costs"]["sealed_advance"]["calls"],
         "mature_hard": s3_method["final_verdicts"]["hard_status"],
         "limitations": ["recovery/checkpoint transition evidence is descriptive for this single matched pair"]},
        {"case": "S4-no-permission-safety-negative", "status": "NATIVE_SAFETY_NEGATIVE_COMPLETE",
         "baseline_scene": result(s4_pair / "baseline")["scene_id"], "mature_scene": s4_method["scene_id"],
         "native_opportunity_attempts": len(s4_method.get("native_opportunity_attempts", [])),
         "mature_root_calls": s4_method["costs"]["gtp_root_plan"]["calls"],
         "mature_root_wall_seconds": s4_method["costs"]["gtp_root_plan"]["wall_seconds"],
         "mature_p5_snapshot_calls": s4_method["costs"]["p5_snapshot_pure_plan"]["calls"],
         "mature_advance_calls": s4_method["costs"]["sealed_advance"]["calls"],
         "baseline_hard": result(s4_pair / "baseline")["final_verdicts"]["hard_status"],
         "mature_hard": s4_method["final_verdicts"]["hard_status"],
         "limitations": ["no opportunities were attempted; unmet hard goals remain VIOLATED", "failure is not a claim of world unreachability"]},
    ]

    source_sets = {}
    for run_dir in run_dirs:
        candidates = list(run_dir.rglob("final-source-manifest.json"))
        for candidate in candidates:
            source_sets[str(candidate.relative_to(ROOT))] = read(candidate)
    summary = {
        "schema": "mature-methods-evidence-index-v1",
        "scope": "S1-S4 one matched pair each; no reruns after fixed matrix; eight unique native scenes",
        "base_commit": "47d3ce7e445747c153c9ab4c5d3f34e2ebc12495",
        "suite_sha256": "952ddb923d12b106628dca7b0cb13829659daf0aae25040b6ad630ce0df5554b",
        "lifecycle": lifecycle,
        "cases": cases,
        "source_manifests": source_sets,
        "archive_members": rows,
        "member_count": len(rows),
        "total_bytes": sum(row["bytes"] for row in rows),
        "exclusions": ["._*", "__pycache__", "*.pyc", "private/_private paths"],
        "verifier": "tools/mature_methods_integration_v1/verify_evidence.py",
        "archive_sha256": "RECORDED_IN_ADJACENT_SHA256_SIDECAR_AFTER_ARCHIVE_CREATION",
    }
    PUBLICATION.mkdir(parents=True, exist_ok=False)
    INDEX.write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Mature-Methods Integration v1 — bounded native evidence",
        "",
        "This is a bounded mixed-outcome integration record, not a system PASS, novelty claim, or performance comparison. The fixed four-pair matrix used one existing P5 world and eight unique native scenes; every arm used the same seed/preset/horizon and native P5 Director comparison, without extra observe_actor sampling.",
        "",
        f"- Suite SHA-256: `{summary['suite_sha256']}`",
        f"- Base commit: `{summary['base_commit']}`; execution source identities are preserved per arm in `index.json`.",
        f"- Indexed raw/source members: {len(rows)} files; {sum(row['bytes'] for row in rows):,} bytes before compression.",
        "- Lifecycle: one authorized stop/start of the same existing Evennia DB/ports before S1; raw stop/start logs are included and health READY was recorded by orchestration.",
        "",
        "| Case | Result | Native scenes | GTP root calls (mature) | P5 snapshot calls (mature) |",
        "|---|---|---|---:|---:|",
    ]
    for case in cases:
        lines.append(f"| {case['case']} | {case['status']} | {case.get('baseline_scene', '—')} / {case.get('mature_scene', '—')} | {case.get('mature_root_calls', '—')} | {case.get('mature_p5_snapshot_calls', '—')} |")
    lines += [
        "",
        "S1 is the minimum closed-loop positive chain: native side-route receipt, NPC task execution/receipts, rejection branch, and all four hard obligations satisfied. The mature arm required preserving two failed runner attempts and a verified same-scene minute17→24 continuation. Valid method work aggregates the 0→17 and 17→24 segments to 5 GTP roots, 26 P5 snapshots (minute17 checkpoint counted in each segment), and 24 advances; all attempts including the initial wrong-interpreter import failure total 6 roots/27 snapshots/24 advances. Per-segment counts and timings are in `index.json`; the baseline used system Python and continuation used the project venv, so runtime comparison is invalid.",
        "",
        "S2 is a native capability mismatch, not a successful stale-candidate/reselection case: the minute1 CAS was rejected with `PERMISSION_ESCALATION` because runtime edits cannot change permissions or author budget. Bundle version remained 1 and the side path stayed legal; no stale guard or main-route reselection was exercised.",
        "",
        "S3 recorded player get@2/drop@6, the native availability transition, and a matched pair. S4 recorded no opportunity attempts and all hard obligations `VIOLATED`; it is a safety negative only, not a world-unreachability claim.",
        "",
        "All raw attempts, failures, source snapshots (including the explicitly non-authoritative flattened copy), per-minute traces, RPC requests/responses, independent DB readbacks, and runner continuation links are retained in the archive. No files under the project's RESULTS.md were changed by this packager.",
        "",
    ]
    SUMMARY.write_text("\n".join(lines), encoding="utf-8")

    with tarfile.open(ARCHIVE, "w:gz", compresslevel=6, format=tarfile.PAX_FORMAT) as tar:
        for run_dir in run_dirs:
            for path in sorted(run_dir.rglob("*")):
                if not path.is_file():
                    continue
                if path.name.startswith("._") or "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}:
                    continue
                tar.add(path, arcname=path.relative_to(ROOT).as_posix(), recursive=False)
        for path in LIFECYCLE_LOGS:
            tar.add(path, arcname=path.relative_to(ROOT).as_posix(), recursive=False)
        tar.add(INDEX, arcname=INDEX.relative_to(ROOT).as_posix(), recursive=False)
        tar.add(SUMMARY, arcname=SUMMARY.relative_to(ROOT).as_posix(), recursive=False)

    (PUBLICATION / "archive.sha256").write_text(
        f"{sha256(ARCHIVE)}  {ARCHIVE.name}\n", encoding="utf-8")
    print(json.dumps({"publication": str(PUBLICATION), "archive": str(ARCHIVE),
                      "archive_sha256": sha256(ARCHIVE), "index": str(INDEX),
                      "index_sha256": sha256(INDEX), "summary": str(SUMMARY),
                      "summary_sha256": sha256(SUMMARY), "members": len(rows),
                      "bytes": sum(row["bytes"] for row in rows)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
