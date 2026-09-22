"""End-to-end same-world, replay, axis, and history-fork acceptance smoke."""
import json
import pathlib
import subprocess
import sys
import tempfile


def main() -> None:
    executable = pathlib.Path(sys.argv[1]).resolve()
    evaluator = pathlib.Path(__file__).with_name("long_horizon_eval.py")
    with tempfile.TemporaryDirectory(prefix="character-life-smoke-") as folder:
        output = pathlib.Path(folder) / "paired"
        subprocess.run([sys.executable, str(evaluator), str(executable), str(output),
                        "--days", "7", "--cases", "1", "--axes"], check=True)
        manifest = json.loads((output / "manifest.json").read_text())
        analysis = json.loads((output / "analysis.json").read_text())
        assert len(manifest["runs"]) == 8 + 8 * 3
        assert manifest["deterministic_rerun_count"] == len(manifest["runs"])
        assert len(analysis["profile_summary"]) == 8
        assert len(analysis["history_fork_summary"]) == 6
        assert len(analysis["axis_interventions"]) == 8
        assert len((output / "history_fork_samples.jsonl").read_text().splitlines()) == 8 * 2 * 3
        assert len({row["sha256"] for row in manifest["runs"][:8]}) > 1
    print("long_horizon_pipeline_smoke: PASS")


if __name__ == "__main__":
    main()
