# E0-KeyLedger-v0 code and reproduction

Protocol authority: [`00_研究设计/E0_KeyLedger_Protocol_v0.md`](../../00_研究设计/E0_KeyLedger_Protocol_v0.md). This package owns only its implementation and checks; it does not modify or integrate the frozen C++ Runtime.

Run from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -B -m unittest discover -s tools/e0_keyledger_v0/tests -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=tools python3 -B -m tools.e0_keyledger_v0.runner --case all --run-id <unique-id> --output-root runs/e0_keyledger_v0/development
```

Use `--case E0-P01` for one fixture. The runner refuses to reuse a run ID; it writes each input checkpoint, result, boundary snapshots, search/replay evidence, and errors under the selected output root. Keep development and CI runs distinct from any parent-authorized formal run.

Code ownership: `executor.py` implements settlements; `planner.py` performs h=0 search; `monitor_bridge.py` projects receipt-backed events into the shared trajectory monitor; `prediction.py` validates prediction contracts; `fixtures.py` supplies checkpoints; `runner.py` records per-fixture checks and outputs. `oracle.py` is an independently transcribed finite-state solver and must not import the executor or planner transition model. Unit contracts live under `tests/`.
