"""The same initial world and RNG must receive explicit, traceable P."""
import json
import pathlib
import subprocess
import sys
import tempfile

exe = sys.argv[1]
with tempfile.TemporaryDirectory(prefix="personality-wiring-") as directory:
    root = pathlib.Path(directory)
    def run(profile, suffix):
        path = root / f"{profile}-{suffix}.json"
        subprocess.run([exe, "1000", "5000", str(path), profile], check=True)
        return path.read_bytes(), json.loads(path.read_text())

    balanced_bytes, balanced = run("balanced", "a")
    repeated_bytes, _ = run("balanced", "b")
    _, disciplined = run("disciplined", "a")
    assert balanced_bytes == repeated_bytes, "same explicit P and seeds must replay"
    first_a, first_b = balanced[0], disciplined[0]
    assert first_a["profile_id"] == "balanced" and first_b["profile_id"] == "disciplined"
    assert first_a["personality"] != first_b["personality"]
    assert first_a["scenario_seed"] == first_b["scenario_seed"] == 1000
    assert first_a["policy_seed"] == first_b["policy_seed"] == 5000
    for key in ("task.coursework.effort_target", "task.coursework.deadline_at_total_minutes"):
        fact = lambda frame: next(item["value"] for item in frame["observation"]["facts"] if item["key"] == key)
        assert fact(first_a) == fact(first_b), key
    pi = lambda frame: {item["action"]: item["probability"] for item in frame["candidates"]}
    assert pi(first_a) != pi(first_b), "P must reach policy on identical first O/S"
print("personality_wiring_smoke: PASS")
