"""Run a bounded integration demo or a development-only condition matrix."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess
from importlib.metadata import version

from trajectory_constraints_v0.ast import ast_from_json, ast_to_json
from . import VERSION
from .author import requirements
from .model import MODELS, initial_checkpoint
from .system import System


def build_case(planner="goap", model="context", policy="KEEP", director=True,
               resources=2, stress=.35, player_at=None, deadline=10, forecast_steps=16):
    system = System(initial_checkpoint(policy, stress=stress, resources=resources), MODELS[model](),
                    planner, director, requirements(deadline), forecast_steps=forecast_steps)
    return system, player_at


CASES = {
    "keep-director-goap": {},
    "keep-director-htn": {"planner": "htn"},
    "keep-no-director": {"director": False},
    "pay-no-director": {"director": False, "policy": "PAY"},
    "player-destruction": {"player_at": 3},
    "no-director-resources": {"resources": 0},
    "deadline-8": {"deadline": 8},
    "forecast-budget": {"forecast_steps": 0},
    "monotone-model": {"model": "monotone"},
    "overload-state": {"stress": .95, "policy": "PAY", "director": False},
}


def summarize(result):
    return {"author_verdicts": result["author_verdicts"],
            "actions": [[s["start_time"], s["end_time"], s["intent"]["actor"],
                         s["intent"]["operator"], s["receipt"]["status"]] for s in result["trace"]],
            "final_characters": result["checkpoint"]["characters"],
            "world_tasks": result["checkpoint"]["world_tasks"],
            "director_resources": result["checkpoint"]["W"]["director_resources"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", action="store_true")
    parser.add_argument("--planner", choices=("goap", "htn"), default="goap")
    parser.add_argument("--model", choices=tuple(MODELS), default="context")
    parser.add_argument("--policy", choices=("PAY", "TOOL", "KEEP"), default="KEEP")
    parser.add_argument("--no-director", action="store_true")
    parser.add_argument("--player-at", type=int)
    parser.add_argument("--author-json", type=Path, help="TypedIR AST JSON constraints grouped in named levels")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    out = args.out or Path("outputs") / VERSION / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    out.mkdir(parents=True, exist_ok=False)
    summary = {}
    configs = CASES if args.suite else {"custom": {"planner": args.planner, "model": args.model,
              "policy": args.policy, "director": not args.no_director, "player_at": args.player_at}}
    try:
        for name, config in configs.items():
            system, player_at = build_case(**config)
            author_bundle = None
            if args.author_json is not None:
                document = json.loads(args.author_json.read_text(encoding="utf-8-sig"))
                constraints = tuple(ast_from_json(c) for level in document["levels"] for c in level["constraints"])
                system = System(system.executor.checkpoint(), system.model, system.planner,
                                system.director, constraints, system.max_expansions, system.forecast_steps)
                author_bundle = document
            result = system.run(player_at)
            result["provenance"] = "synthetic_diagnostic"
            result["author_bundle"] = author_bundle
            result["author_requirements"] = ast_to_json(system.constraints)
            (out / (name + ".json")).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            summary[name] = summarize(result)
        (out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        repo_root = Path(__file__).resolve().parents[2]
        sources = {p.relative_to(repo_root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in Path(__file__).parent.rglob("*.py")}
        manifest = {"version": VERSION, "source_git_revision": subprocess.check_output(
                        ["git", "rev-parse", "HEAD"], text=True).strip(),
                    "source_sha256": sources, "conditions": configs, "development_only": True,
                    "source_git_dirty": bool(subprocess.check_output(["git", "status", "--porcelain"]).strip()),
                    "dependencies": {name: version(name) for name in ("gtpyhop-core", "psutil")},
                    "e1_finite_executor_not_cpp_native": True, "python": __import__("sys").version,
                    "author_requirements": ast_to_json(system.constraints),
                    "formal_test_or_psychological_validation": False}
        (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as exc:
        (out / "error.json").write_text(json.dumps({"error": repr(exc)}, indent=2), encoding="utf-8")
        raise
    print(json.dumps({"output": str(out.resolve()), "cases": len(summary),
                      "ledger_event": {k: next((v["status"] for v in s["author_verdicts"] if v["id"] == "ledger-event"), "not specified")
                                       for k, s in summary.items()}}, ensure_ascii=True))


if __name__ == "__main__":
    main()
