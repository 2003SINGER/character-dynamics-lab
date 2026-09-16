"""Generate deterministic dry-run artifacts for the ResearchDynamicsV1 gate."""
from pathlib import Path
import json
from research_dynamics_v1 import run_intervention, MODEL_ID

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "artifacts"
NAMES = ("zero", "correct_recovery", "permuted", "stale_o", "frozen", "wrong_field")
OUT.mkdir(exist_ok=True)
manifest = {"dynamics_model_id": MODEL_ID, "seed": 20260916, "interventions": []}
for name in NAMES:
    payload = run_intervention(name)
    path = OUT / f"{name}.json"
    path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    manifest["interventions"].append({"name": name, "path": str(path.relative_to(ROOT))})
(OUT / "manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n", encoding="utf-8")
print(json.dumps(manifest, indent=2))
