"""Non-overwriting development pack; no automatic inference or episode retry."""
from __future__ import annotations

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from tools.open_adventure_planning_v0.search import SearchLimits
from tools.open_adventure_planning_v0.domain import initial_state
from .contracts import task_spec_from_dict, task_spec_to_dict
from .search import plan_task
from .tasks import STATIC_TASKS, DYNAMIC_CASES, task_by_id, TaskCase

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "02_实验/Author_Obligation_Planning_v0"
BASE = "49895f29605c8a350b27db65ba01ae9e53fe288d"
PROTECTED = ("tools/open_adventure_v0", "tools/open_adventure_planning_v0",
             "tools/llm_admission_v0", "tools/author_constraint_diagnostic_v0",
             "02_实验/LLM_Admission_v0", "02_实验/OpenAdventure_Planning_B0_v0",
             "02_实验/Author_Constraint_Diagnostic_v0", "tools/e0_keyledger_v0")
NATIVE_IDS = ("A1", "A2", "A3", "B1", "C1", "D2", "E2", "G3", "G5", "G6", "G8", "G9", "H1", "H2", "H3", "H4")


def write(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def protected_hashes():
    names = subprocess.check_output(["git", "ls-tree", "-r", "--name-only", "-z", BASE,
                                     "--", *PROTECTED], cwd=ROOT).decode().strip("\0").split("\0")
    hashes = {}
    for name in names:
        data = (ROOT / name).read_bytes()
        if data != subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT):
            raise RuntimeError(f"frozen source/evidence changed: {name}")
        hashes[name] = hashlib.sha256(data).hexdigest()
    return hashes


def prepare(pack: Path):
    pack.mkdir(parents=True, exist_ok=False)
    write(pack / "protected_before.json", protected_hashes())
    tasks = list(STATIC_TASKS) + [case.task for case in DYNAMIC_CASES]
    write(pack / "reference_manifest.json", {
        "protocol": "author-obligation-planning-v0", "base": BASE,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_origin": "manual structured reference, not model output",
        "tasks": [task_spec_to_dict(task) for task in tasks],
        "dynamic": [{"id": c.task.id, "edit_trigger": c.edit_trigger,
                     "requires_native_feedback": c.requires_native_feedback} for c in DYNAMIC_CASES],
        "selected_native": NATIVE_IDS, "search_limits": asdict(SearchLimits()),
    })
    write(pack / "author_texts.json", [{"id": t.id, "text": t.text} for t in tasks])
    source_dir = pack / "source_at_prepare"
    source_dir.mkdir()
    for source in Path(__file__).parent.rglob("*.py"):
        if "__pycache__" not in source.parts:
            target = source_dir / source.relative_to(Path(__file__).parent)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())


def offline(pack: Path, *, bindings: Path | None = None):
    # Candidate admission is exact against an independent finite reference;
    # rejected outputs are retained and never repaired into the reference.
    reference = json.loads((pack / "reference_manifest.json").read_text())["tasks"]
    supplied = reference if bindings is None else json.loads(bindings.read_text())["tasks"]
    ids = [row.get("id") for row in supplied]
    if len(ids) != 32 or len(set(ids)) != 32 or set(ids) != {r["id"] for r in reference}:
        raise ValueError("binding must return exactly the 32 distinct IDs; no silent omission")
    label = "manual_reference" if bindings is None else "luna_candidate"
    directory = pack / label
    directory.mkdir(exist_ok=False)
    rows = []
    for expected in reference:
        raw = next(r for r in supplied if r["id"] == expected["id"])
        record = {"id": expected["id"], "input_origin": label, "raw_candidate": raw}
        try:
            task = task_spec_from_dict(raw)
            # Set comparisons allow harmless ordering only, not lost conditions.
            reference_task = task_spec_from_dict(expected)
            semantic_match = (task == reference_task)
            record["semantic_reference_match"] = semantic_match
            if not semantic_match:
                record.update(status="BINDING_MISMATCH", search="NOT_RUN")
            else:
                case = task_by_id(task.id)
                initial = case.initial if isinstance(case, TaskCase) else initial_state()
                result = plan_task(initial, task, limits=SearchLimits())
                record.update(status=result.status, result=asdict(result),
                              dynamic_scope="initial version only; online edit not yet tested" if isinstance(case, TaskCase) else None)
        except ValueError as exc:
            record.update(status="UNSUPPORTED_BINDING", reason=str(exc), search="NOT_RUN")
        write(directory / f"{expected['id']}.json", record)
        rows.append({k: record[k] for k in ("id", "status", "semantic_reference_match") if k in record})
        print(expected["id"], record["status"], flush=True)
    write(directory / "summary.json", rows)
    return rows


def native(pack: Path):
    from .native import run_episode
    from .verify import verify_native
    directory = pack / "native"
    directory.mkdir(exist_ok=False)
    snapshot = pack / "source_at_native"
    snapshot.mkdir()
    for source in Path(__file__).parent.rglob("*.py"):
        if "__pycache__" not in source.parts:
            target = snapshot / source.relative_to(Path(__file__).parent)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read_bytes())
    results = []
    for task_id in NATIVE_IDS:
        admission = json.loads((pack / "luna_candidate" / f"{task_id}.json").read_text())
        if admission.get("status") != "FOUND":
            record = {"task_id": task_id, "controller_status": "NOT_STARTED",
                      "reason": "candidate binding/search not admitted", "prior_status": admission["status"]}
        else:
            task = task_spec_from_dict(admission["raw_candidate"])
            # Claim survives crashes; there is no catch-and-retry branch.
            write(directory / f"{task_id}.claim.json", {"attempt": 1, "input": admission["raw_candidate"]})
            try:
                record = run_episode(task_id, execute_native=True, external_task=task,
                                     scenario="h4_feedback_delay" if task_id == "H4" else "clean",
                                     runs_root=pack / "native_runs")
                if record.get("native_ledger"):
                    record["independent_verifier"] = verify_native(Path(record["native_ledger"]), record["final_task"])
            except Exception as exc:
                record = {"task_id": task_id, "controller_status": "EXECUTION_ERROR",
                          "error": f"{type(exc).__name__}: {exc}", "retry": False}
        write(directory / f"{task_id}.json", record)
        results.append({"id": task_id, "controller": record["controller_status"],
                        "author": record.get("independent_verifier", {}).get("status", "NOT_RUN")})
        print(results[-1], flush=True)
    write(directory / "summary.json", results)
    after = protected_hashes()
    write(pack / "protected_after.json", after)
    if after != json.loads((pack / "protected_before.json").read_text()):
        raise RuntimeError("protected baseline changed during the pack")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("prepare", "offline", "native"))
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--bindings", type=Path)
    args = parser.parse_args()
    if args.operation == "prepare":
        prepare(args.pack)
    elif args.operation == "offline":
        offline(args.pack, bindings=args.bindings)
    else:
        native(args.pack)


if __name__ == "__main__":
    main()
