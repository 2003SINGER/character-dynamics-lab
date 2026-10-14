# Luna-in-Codex semantic admission

Bounded development probe, not a model-performance benchmark. [Protocol](../../02_实验/LLM_Admission_v0/PROTOCOL.md), [results and exact outputs](../../02_实验/LLM_Admission_v0/RESULTS.md).

- `packet.py`: exports/round-trips frozen B0 rules and prepares only fresh native setup observations. Already run once; do not overwrite the packet or repeat the setup as a model episode.
- `binding.py`: strict candidate parser, whitelist/provenance validator and actual `Goal` compiler; only an admitted E candidate may call the native controller. This round's E failed admission: no native task run.
- `audit.py`: extracts designated child model/effort/tools/token metadata and verbatim final output; fingerprints automatically injected context instead of publishing private instructions.
- `capture.py`: exact public call parameters and encrypted-body hash from parent runtime; full controller-supplied request transcription separately. Backend plaintext cannot be independently read from the encrypted logs. No claim of cryptographic plaintext equality.
- `finalize.py`: offline result serialization only, never inference or game execution. The checked-in result is this one fixed development round, not a reusable semantic benchmark.

Offline regression:

```sh
python -B -m unittest discover -s tools/llm_admission_v0/tests -v
python -B -m unittest tools.open_adventure_planning_v0.tests.test_baseline tools.open_adventure_v0.tests.test_runner tools.open_adventure_v0.tests.test_session -v
```

CI only runs these offline contracts; it cannot repeat authenticated native Codex model calls. Native `spawn_agent` requests are reproduced as evidence, not an API wrapper. Default B0 behavior/goal map remain intact; only `external_goal`, `external_goal_text` and isolated `runs_root` injection were added to `run_episode`. `goal_id="E"` identifies the frozen evidence verifier, not a lookup replacing the external candidate. Wiring test injects a different goal and captures the exact object received by UCS; no game action occurs in that mocked test.
